from elkplot import Device


def _calibrate_penlift(width: float, height: float, margin: float, pen: str):
    device = Device(pen)
    corners = [(margin, margin), (width - margin, height - margin)]
    for corner in corners:
        device.goto(*corner)
        print("Calibrating Pen Up Position")
        while True:
            device.pen_up()
            new_up = input(
                f"Input new up position (or nothing to continue). Current={device.pen_up_position} "
            )
            if len(new_up) == 0:
                break
            device.pen_up_position = int(new_up)
            device.configure()
        device.pen_up()
        print("Calibrating Pen Down Position")
        while True:
            device.pen_down()
            new_down = input(
                f"Input new down position (or nothing to continue). Current={device.pen_down_position} "
            )
            if len(new_down) == 0:
                break
            device.pen_down_position = int(new_down)
            device.configure()
        device.pen_up()
    device.home()
    device.write_settings()
    device.disable_motors()


def _calibrate_speed(width: float, height: float, margin: float, pen: str):
    device = Device(pen)
    y = margin
    offset = (height - 2 * margin) / 50
    while y < height - margin:
        device.pen_up()
        device.goto(margin, y)
        device.pen_down()
        device.goto(width - margin, y, jog=False)
        device.pen_up()
        new_speed = input(
            f"Input new speed (or nothing to finish). Current={device.max_velocity} "
        )
        if len(new_speed) == 0:
            break
        device.max_velocity = float(new_speed)
        device.configure()
        y += offset
    device.home()
    device.write_settings()
    device.disable_motors()
