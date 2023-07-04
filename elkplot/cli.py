import click

import elkplot
from elkplot.calibrate import _calibrate_penlift, _calibrate_speed
from elkplot.device import _load_config


@click.group()
def cli():
    ...


@cli.command()
def zero():
    elkplot.Device().zero_position()


@cli.command()
def home():
    """Return the pen to (0, 0)"""
    elkplot.Device().home()


@cli.command()
def up():
    """Lift the pen off the page"""
    elkplot.Device().pen_up()


@cli.command()
def down():
    """Bring the pen down onto the page"""
    elkplot.Device().pen_down()


@cli.command()
def on():
    """Enable the AxiDraw's motors"""
    elkplot.Device().enable_motors()


@cli.command()
def off():
    """Disable the AxiDraw's motors"""
    elkplot.Device().disable_motors()


@cli.command()
@click.argument("dx", type=float)
@click.argument("dy", type=float)
def move(dx: float, dy: float):
    """Offset the pen's current position. Positive numbers move further away from home in both axes. Add a double hyphen
    (--) before the arguments if you need to give negative arguments."""
    elkplot.Device().move(dx, dy)


@cli.command()
@click.argument("x", type=float)
@click.argument("y", type=float)
def goto(x: float, y: float):
    """Move the pen directly to the point (x, y)"""
    elkplot.Device().goto(x, y)


# @cli.command()
# def pen_list():
#     """List the names of all pens that have been configured so far."""
#     config = _load_config()
#     names = ["-" + name for name in config.keys() if name not in {"DEFAULT", "DEVICE"}]
#     click.echo("\n".join(names))
#
#
# @cli.group()
# def calibrate():
#     ...
#
#
# @calibrate.command()
# @click.argument("width", type=float)
# @click.argument("height", type=float)
# @click.argument("margin", type=float)
# @click.argument("pen", type=str)
# def penlift(width: float, height: float, margin: float, pen: str):
#     """Set the pen up and pen down heights for the current pen"""
#     _calibrate_penlift(width, height, margin, pen)
#
#
# @calibrate.command()
# @click.argument("width", type=float)
# @click.argument("height", type=float)
# @click.argument("margin", type=float)
# @click.argument("pen", type=str)
# def speed(width: float, height: float, margin: float, pen: str):
#     """Set the maximum movement speed for the current pen. (Some pens need to go slower to get ink on the page)"""
#     _calibrate_speed(width, height, margin, pen)


if __name__ == "__main__":
    cli()
