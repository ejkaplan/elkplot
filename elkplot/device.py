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


def _axidraw_available() -> bool:
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


class Device:
    def __init__(self, pen: str = "DEFAULT"):
        config = _load_config()
        self.timeslice_ms = int(config["DEVICE"]["timeslice_ms"])
        self.microstepping_mode = int(config["DEVICE"]["microstepping_mode"])
        self.step_divider = 2 ** (self.microstepping_mode - 1)
        self.steps_per_unit = 2032 / self.step_divider
        self.steps_per_mm = 80 / self.step_divider
        self.vid_pid = str(config["DEVICE"]["vid_pid"])
        self.pen_lift_pin = str(config["DEVICE"]["pen_lift_pin"])
        self.brushless = bool(int(config["DEVICE"]["brushless"]))
        self.pen = pen

        if pen not in config:
            pen = "DEFAULT"

        self.pen_up_position = float(config[pen]["pen_up_position"])
        self.pen_up_speed = float(config[pen]["pen_up_speed"])
        self.pen_up_delay = int(config[pen]["pen_up_delay"])
        self.pen_down_position = float(config[pen]["pen_down_position"])
        self.pen_down_speed = float(config[pen]["pen_down_speed"])
        self.pen_down_delay = int(config[pen]["pen_down_delay"])
        self.acceleration = float(config[pen]["acceleration"])
        self.max_velocity = float(config[pen]["max_velocity"])
        self.corner_factor = float(config[pen]["corner_factor"])
        self.jog_acceleration = float(config[pen]["jog_acceleration"])
        self.jog_max_velocity = float(config[pen]["jog_max_velocity"])

        self.error = (0, 0)  # accumulated step error

        port = _find_port()
        if port is None:
            raise IOError("Could not connect to AxiDraw over USB")
        self.serial = Serial(port, timeout=1)
        self.configure()

    def write_settings(self):
        config = _load_config()
        if not config.has_section(self.pen):
            config.add_section(self.pen)
        config[self.pen]["pen_up_position"] = str(self.pen_up_position)
        config[self.pen]["pen_up_speed"] = str(self.pen_up_speed)
        config[self.pen]["pen_up_delay"] = str(self.pen_up_delay)
        config[self.pen]["pen_down_position"] = str(self.pen_down_position)
        config[self.pen]["pen_down_speed"] = str(self.pen_down_speed)
        config[self.pen]["pen_down_delay"] = str(self.pen_down_delay)
        config[self.pen]["acceleration"] = str(self.acceleration)
        config[self.pen]["max_velocity"] = str(self.max_velocity)
        config[self.pen]["corner_factor"] = str(self.corner_factor)
        config[self.pen]["jog_acceleration"] = str(self.jog_acceleration)
        config[self.pen]["jog_max_velocity"] = str(self.jog_max_velocity)
        with open(CONFIG_FILEPATH, "w") as configfile:
            config.write(configfile)

    def configure(self):
        servo_max = 12600 if self.brushless else 27831  # Up at "100%" position.
        servo_min = 5400 if not self.brushless else 9855  # Down at "0%" position

        pen_up_position = self.pen_up_position / 100
        pen_up_position = int(servo_min + (servo_max - servo_min) * pen_up_position)
        pen_down_position = self.pen_down_position / 100
        pen_down_position = int(servo_min + (servo_max - servo_min) * pen_down_position)
        self.command("SC", 4, pen_up_position)
        self.command("SC", 5, pen_down_position)
        self.command("SC", 11, int(self.pen_up_speed * 5))
        self.command("SC", 12, int(self.pen_down_speed * 5))

    def close(self):
        self.serial.close()

    def make_planner(self, jog: bool = False) -> Planner:
        a = self.acceleration if not jog else self.jog_acceleration
        vmax = self.max_velocity if not jog else self.jog_max_velocity
        cf = self.corner_factor
        return Planner(a, vmax, cf)

    def readline(self) -> str:
        return self.serial.readline().decode("utf-8").strip()

    def command(self, *args) -> str:
        line = ",".join(map(str, args))
        self.serial.write((line + "\r").encode("utf-8"))
        return self.readline()

    # higher level functions
    def move(self, dx: float, dy: float):
        self.run_path(shapely.linestrings([(0, 0), (dx, dy)]))

    def goto(self, x: float, y: float, jog=True):
        # TODO: jog if pen up
        px, py = self.read_position()
        self.run_path(shapely.linestrings([(px, py), (x, y)]), jog=jog)

    def home(self):
        self.goto(0, 0, True)

    # misc commands
    def version(self):
        return self.command("V")

    # motor functions
    def enable_motors(self):
        m = self.microstepping_mode
        return self.command("EM", m, m)

    def disable_motors(self):
        return self.command("EM", 0, 0)

    def motor_status(self):
        return self.command("QM")

    def zero_position(self):
        return self.command("CS")

    def read_position(self):
        response = self.command("QS")
        self.readline()
        a, b = map(float, response.split(","))
        a /= self.steps_per_unit
        b /= self.steps_per_unit
        y = (a - b) / 2
        x = y + b
        return x, y

    def stepper_move(self, duration: float, a, b):
        return self.command("XM", duration, a, b)

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
        planner = self.make_planner(jog)
        plan = planner.plan(list(path.coords))
        if draw:
            self.pen_down()
            self.run_plan(plan)
            self.pen_up()
        else:
            self.run_plan(plan)

    def run_layer(self, drawing: shapely.MultiLineString, label: str = None):
        self.pen_up()
        origin = shapely.Point(0, 0)
        position = origin
        bar = tqdm(total=drawing.length + elkplot.up_length(drawing).m, desc=label)
        path: shapely.LineString
        for path in shapely.get_parts(drawing):
            jog = shapely.LineString([position, shapely.Point(path.coords[0])])
            self.run_path(jog, jog=True)
            bar.update(jog.length)
            self.run_path(path, draw=True)
            position = path.coords[-1]
            bar.update(path.length)
        bar.close()
        self.run_path(shapely.LineString([position, origin]), jog=True)

    def plan_drawing(self, drawing: shapely.MultiLineString):
        result = []
        planner = self.make_planner()
        for path in shapely.get_parts(drawing):
            result.append(planner.plan(path))
        return result

    # pen functions
    def pen_up(self):
        return self.command("SP", 1, self.pen_up_delay, self.pen_lift_pin)

    def pen_down(self):
        return self.command("SP", 0, self.pen_down_delay, self.pen_lift_pin)
