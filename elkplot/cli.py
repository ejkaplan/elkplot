from typing import Optional
import click

import elkplot


@click.group()
def cli(): ...


@cli.command()
def zero():
    """Set the current location as (0, 0)"""
    elkplot.Device().zero_position()


@cli.command()
def home():
    """Return the pen to (0, 0)"""
    elkplot.Device().home()


@cli.command()
@click.argument("height", type=float, required=False)
def up(height: Optional[float] = None):
    """Lift the pen off the page"""
    if height is not None:
        device = elkplot.Device(pen_up_position=height)
    else:
        device = elkplot.Device()
    device.pen_up()


@cli.command()
@click.argument("height", type=float, required=False)
def down(height: Optional[float] = None):
    """Bring the pen down onto the page"""
    if height is not None:
        device = elkplot.Device(pen_down_position=height)
    else:
        device = elkplot.Device()
    device.pen_down()


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


if __name__ == "__main__":
    cli()
