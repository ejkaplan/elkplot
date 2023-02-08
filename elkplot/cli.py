import click

import elkplot
from elkplot.calibrate import calibrate_penlift, calibrate_speed


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
def penlift(width: float, height: float, margin: float):
    calibrate_penlift(width, height, margin)


@calibrate.command()
@click.argument("width", type=float)
@click.argument("height", type=float)
@click.argument("margin", type=float)
def speed(width: float, height: float, margin: float):
    calibrate_speed(width, height, margin)


if __name__ == "__main__":
    cli()
