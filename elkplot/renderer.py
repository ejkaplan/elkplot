from __future__ import division

from itertools import chain

import numpy as np
import pint
import shapely
from pyglet import window, gl, app
from pyglet.graphics import Batch, Group

from elkplot.sizes import UNITS

COLORS = [
    (0, 0, 255, 255),  # blue
    (255, 0, 0, 255),  # red
    (0, 82, 33, 255),  # dark green
    (255, 123, 0, 255),  # orange
    (8, 142, 149, 255),  # aqua
    (255, 0, 255, 255),  # fuchsia
    (158, 253, 56, 255),  # lime
    (206, 81, 113, 255),  # hot pink
]


def _random_color(rng: np.random.Generator) -> tuple[int, int, int, int]:
    return tuple((*rng.integers(0, 256, 3), 255))


def _batch_drawings(
    layers: list[shapely.MultiLineString], height: float, dpi: float
) -> Batch:
    rng = np.random.default_rng()
    my_colors = COLORS + [_random_color(rng) for _ in range(len(layers) - len(COLORS))]
    batch = Batch()
    for i, layer in enumerate(layers):
        color = my_colors[i]
        path: shapely.LineString
        for path in shapely.get_parts(layer):
            grp = Group()
            screen_coords = [(dpi * x, dpi * (height - y)) for x, y in path.coords]
            vertices = (
                screen_coords[0] + tuple(chain(*screen_coords)) + screen_coords[-1]
            )
            batch.add(
                len(vertices) // 2,
                gl.GL_LINE_STRIP,
                grp,
                ("v2f", vertices),
                ("c4B", color * (len(vertices) // 2)),
            )
    return batch


@UNITS.wraps(None, (None, "inch", "inch", None), False)
def render(
    drawings: list[shapely.MultiLineString],
    width: float | pint.Quantity,
    height: float | pint.Quantity,
    dpi: float = 128,
) -> None:
    """
    NOTE: You will probably not want to call this directly and instead use elkplot.draw
    Displays a preview of what the plotter will draw. Each layer is rendered in a different color. The first 8 layers'
    colors have been chosen with maximum distinguishability in mind. If (for some reason) you need more than 8 layers,
    subsequent layers' colors are chosen randomly and no guarantees are made about legibility.
    :param drawings: A list of MultiLineStrings, one per layer to be drawn
    :param width: The width of the page (in inches)
    :param height: The height of the page (in inches)
    :param dpi: How large would you like the preview shown in screen pixels per plotter-inch
    :return:
    """
    if isinstance(width, pint.Quantity):
        width = width.to('inch').magnitude
    if isinstance(height, pint.Quantity):
        height = height.to('inch').magnitude
    batch = _batch_drawings(drawings, height, dpi)
    config = gl.Config(sample_buffers=1, samples=8, double_buffer=True)
    win = window.Window(
        int(width * dpi), int(height * dpi), "plot preview", config=config
    )

    @win.event
    def on_draw():
        gl.glEnable(gl.GL_LINE_SMOOTH)
        win.clear()
        batch.draw()

    app.run()
