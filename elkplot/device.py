import multiprocessing as mp
import time
from configparser import ConfigParser
from math import modf
from pathlib import Path

import shapely
from serial import Serial
from serial.tools.list_ports import comports
from tqdm import tqdm

import elkplot
from .planner import Planner, Plan

# Taken with modifications from https://github.com/fogleman/axi


CONFIG_FILEPATH = Path(__file__).parent / "axidraw.ini"


def axidraw_available() -> bool:
    config = _load_config()
    vid_pid = config["DEVICE"]["vid_pid"].upper()
    ports = [port for port in comports() if vid_pid in port[2]]
    return len(ports) > 0


def _find_port():
    # TODO: More elegant axidraw selection
    config = _load_config()
    vid_pid = config["DEVICE"]["vid_pid"].upper()
    ports = [port for port in comports() if vid_pid in port[2]]
    if len(ports) == 0:
        return None
    elif len(ports) == 1:
        return ports[0][0]
    else:
        print("Which axidraw to use?")
        for i, port in enumerate(ports):
            n0 = port[2].index("SER=") + 4
            n1 = port[2].index("LOCATION") - 1
            print(f"{i}) {port[2][n0:n1]}")
        idx = int(input())
        return ports[idx][0]


def _load_config() -> ConfigParser:
    config = ConfigParser()
    config.read(CONFIG_FILEPATH)
    return config


def plan_layer_proc(
    queue: mp.Queue,
    layer: list[list[tuple[float, float]]],
    jog_planner: Planner,
    draw_planner: Planner,
):
    origin = (0, 0)
    position = origin
    for coord_list in layer:
        path_linestring = shapely.LineString(coord_list)
        # Move into position (jogging because pen is up)
        jog = shapely.LineString([position, coord_list[0]])
        plan = jog_planner.plan(list(jog.coords))
        queue.put((plan, jog.length))
        # Run the actual line (no jog, because pen is down)
        plan = draw_planner.plan(coord_list)
        queue.put((plan, path_linestring.length))
        position = coord_list[-1]
    queue.put(("DONE", 0))


class Device:
    def __init__(
        self,
        pen_up_position: float = -50,
        pen_down_position: float = -120,
        pen_up_speed: float = 150,
        pen_down_speed: float = 150,
        pen_up_delay: int = 50,
        pen_down_delay: int = 50,
        acceleration: float = 16,
        max_velocity: float = 4,
        corner_factor: float = 0.001,
        jog_acceleration: float = 16,
        jog_max_velocity: float = 8,
        pen_lift_pin: int = 2,
        brushless: bool = True,
    ):
        """
        Construct a Device object that contains all the settings for the AxiDraw itself. The default values are chosen
        based on what works for me and my AxiDraw with the upgraded brushless penlift motor - you may need to change
        these for your AxiDraw.

        Args:
            pen_up_position: To what level should the pen be lifted? (I found this value by trial and error.)
            pen_down_position: To what level should the pen be lowered? (I found this value by trial and error.)
            pen_up_speed: How fast should the pen be lifted?
            pen_down_speed: How fast should the pen be lowered?
            pen_up_delay: How long (in ms) should the AxiDraw wait after starting to raise the pen before taking the
                next action? (Lower is faster, but can lead to unwanted lines being drawn.)
            pen_down_delay: How long (in ms) should the AxiDraw wait after starting to lower the pen before taking the
                next action? (Lower is faster, but can lead to wanted lines not being drawn.)
            acceleration: How aggressively should the AxiDraw accelerate up to `max_velocity`?
            max_velocity: How fast should the AxiDraw move when traveling at top speed?
            corner_factor: What is the radius of the corner when making a sharp turn? Larger values can
                maintain higher speeds around corners, but will round off sharp edges. Smaller values are more accurate
                to the original drawing but have to slow down more at sharp corners.
            jog_acceleration: How aggressively should the AxiDraw accelerate up to `jog_max_velocity` when moving
                while the pen is lifted?
            jog_max_velocity: How fast should the AxiDraw move when traveling at top speed while the pen is lifted?
            pen_lift_pin: To which pin on the driver board is the penlift motor connected? (Pin 0 is the bottom pin.)
            brushless: Is the connected motor the upgraded brushless motor?
        """
        self.timeslice_ms = 10
        self.microstepping_mode = 1  # Maybe this will need to change someday? 🤷‍♀️
        self.step_divider = 2 ** (self.microstepping_mode - 1)
        self.steps_per_unit = 2032 / self.step_divider
        self.steps_per_mm = 80 / self.step_divider
        self.vid_pid = "04d8:fd92"  # ID common to all AxiDraws
        self.pen_lift_pin = pen_lift_pin
        self.brushless = brushless

        self.pen_up_position = pen_up_position
        self.pen_down_position = pen_down_position
        self.pen_up_speed = pen_up_speed
        self.pen_down_speed = pen_down_speed
        self.pen_up_delay = pen_up_delay
        self.pen_down_delay = pen_down_delay
        self.acceleration = acceleration
        self.max_velocity = max_velocity
        self.corner_factor = corner_factor
        self.jog_acceleration = jog_acceleration
        self.jog_max_velocity = jog_max_velocity

        self.error = (0, 0)  # accumulated step error

        port = _find_port()
        if port is None:
            raise IOError("Could not connect to AxiDraw over USB")
        self.serial = Serial(port, timeout=1)
        self._configure()

    def _configure(self):
        servo_max = 12600 if self.brushless else 27831  # Up at "100%" position.
        servo_min = 5400 if not self.brushless else 9855  # Down at "0%" position

        pen_up_position = self.pen_up_position / 100
        pen_up_position = int(servo_min + (servo_max - servo_min) * pen_up_position)
        pen_down_position = self.pen_down_position / 100
        pen_down_position = int(servo_min + (servo_max - servo_min) * pen_down_position)
        self._command("SC", 4, pen_up_position)
        self._command("SC", 5, pen_down_position)
        self._command("SC", 11, int(self.pen_up_speed * 5))
        self._command("SC", 12, int(self.pen_down_speed * 5))

    def close(self):
        """When you create a Device() object, it monopolizes access to that AxiDraw. Call this to free it up so other
        programs can talk to it again."""
        self.serial.close()

    def _make_planner(self, jog: bool = False) -> Planner:
        a = self.acceleration if not jog else self.jog_acceleration
        vmax = self.max_velocity if not jog else self.jog_max_velocity
        cf = self.corner_factor
        return Planner(a, vmax, cf)

    def _readline(self) -> str:
        return self.serial.readline().decode("utf-8").strip()

    def _command(self, *args) -> str:
        line = ",".join(map(str, args))
        self.serial.write((line + "\r").encode("utf-8"))
        return self._readline()

    # higher level functions
    def move(self, dx: float, dy: float):
        """
        Offset the current pen position.
        Args:
            dx: The offset in the x direction in inches
            dy: The offset in the y direction in inches
        """
        self.run_path(shapely.linestrings([(0, 0), (dx, dy)]))

    def goto(self, x: float, y: float, jog: bool = True):
        """
        Move the pen directly to a given point on the canvas. Points are measured in inches from the origin
        Args:
            x: The x-coordinate of the desired point
            y: The y-coordinate of the desired point
            jog: Should it travel at jog-speed or regular?
        """
        # TODO: jog if pen up
        px, py = self.read_position()
        self.run_path(shapely.linestrings([(px, py), (x, y)]), jog=jog)

    def home(self):
        """Send the pen back to (0, 0)"""
        self.goto(0, 0, True)

    # misc commands
    def version(self):
        return self._command("V")

    # motor functions
    def enable_motors(self):
        """Turn the motors on"""
        m = self.microstepping_mode
        return self._command("EM", m, m)

    def disable_motors(self):
        """Turn the motors off"""
        return self._command("EM", 0, 0)

    def motor_status(self):
        return self._command("QM")

    def zero_position(self):
        """Set the current position of the pen as (0, 0). Called automatically when connecting to the device. For best
        results, always start and end with the motor in home position. If necessary, though, you can disable motors,
        manually reset the pen back home, and call this function."""
        return self._command("CS")

    def read_position(self) -> tuple[float, float]:
        """Get the xy coordinates of the pen"""
        response = self._command("QS")
        self._readline()
        a, b = map(float, response.split(","))
        a /= self.steps_per_unit
        b /= self.steps_per_unit
        y = (a - b) / 2
        x = y + b
        return x, y

    def stepper_move(self, duration: float, a, b):
        return self._command("XM", duration, a, b)

    def wait(self):
        while "1" in self.motor_status():
            time.sleep(0.01)

    def run_plan(self, plan: Plan):
        step_s = self.timeslice_ms / 1000
        t = 0
        while t < plan.t:
            i1 = plan.instant(t)
            i2 = plan.instant(t + step_s)
            d = i2.p.sub(i1.p)
            ex, ey = self.error
            ex, sx = modf(d.x * self.steps_per_unit + ex)
            ey, sy = modf(d.y * self.steps_per_unit + ey)
            self.error = ex, ey
            self.stepper_move(self.timeslice_ms, int(sx), int(sy))
            t += step_s
        # self.wait()

    def run_path(self, path: shapely.LineString, draw: bool = False, jog: bool = False):
        planner = self._make_planner(jog)
        plan = planner.plan(list(path.coords))
        if draw:
            self.pen_down()
            self.run_plan(plan)
            self.pen_up()
        else:
            self.run_plan(plan)

    def run_layer(self, layer: shapely.MultiLineString, label: str = None):
        jog_planner = self._make_planner(True)
        draw_planner = self._make_planner(False)
        queue = mp.Queue()
        layer_coord_list = [list(line.coords) for line in shapely.get_parts(layer)]
        p = mp.Process(
            target=plan_layer_proc,
            args=(queue, layer_coord_list, jog_planner, draw_planner),
        )
        p.start()
        bar = tqdm(total=layer.length + elkplot.up_length(layer).m, desc=label)
        idx = 0
        while True:
            jog_plan, length = queue.get()
            if jog_plan == "DONE":
                break
            if idx % 2 == 0:
                self.pen_up()
            else:
                self.pen_down()
            self.run_plan(jog_plan)
            bar.update(length)
            idx += 1
        bar.close()
        self.pen_up()
        self.home()

    # pen functions
    def pen_up(self):
        """Lift the pen"""
        return self._command("SP", 1, self.pen_up_delay, self.pen_lift_pin)

    def pen_down(self):
        """Lower the pen"""
        return self._command("SP", 0, self.pen_down_delay, self.pen_lift_pin)
