import click

import elkplot


@click.group()
def cli():
    ...


@cli.command()
def zero():
    elkplot.Device().zero_position()


@cli.command()
def home():
    elkplot.Device().home()


@cli.command()
def up():
    elkplot.Device().pen_up()


@cli.command()
def down():
    elkplot.Device().pen_down()


@cli.command()
def on():
    elkplot.Device().enable_motors()


@cli.command()
def off():
    elkplot.Device().disable_motors()


@cli.command()
@click.argument("dx", type=float)
@click.argument("dy", type=float)
def move(dx: float, dy: float):
    elkplot.Device().move(dx, dy)


@cli.command()
@click.argument("x", type=float)
@click.argument("y", type=float)
def goto(x: float, y: float):
    elkplot.Device().goto(x, y)


@cli.group()
def calibrate():
    ...


@calibrate.command()
@click.argument("width", type=float)
@click.argument("height", type=float)
@click.argument("margin", type=float)
def pen_lift(width: float, height: float, margin: float):
    device = elkplot.Device()
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


@calibrate.command()
@click.argument("width", type=float)
@click.argument("height", type=float)
@click.argument("margin", type=float)
def speed(width: float, height: float, margin: float):
    device = elkplot.Device()
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


if __name__ == "__main__":
    cli()
