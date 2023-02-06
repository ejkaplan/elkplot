from __future__ import division

from itertools import chain

import shapely
from pyglet import window, gl, app
from pyglet.graphics import Batch, Group

colors = [
    (0, 0, 255, 255),  # blue
    (255, 0, 0, 255),  # red
    (0, 82, 33, 255),  # dark green
    (255, 123, 0, 255),  # orange
    (8, 142, 149, 255),  # aqua
    (255, 0, 255, 255),  # fuchsia
    (158, 253, 56, 255),  # lime
    (206, 81, 113, 255),  # hot pink
]


def batch_drawings(layers: list[shapely.MultiLineString], height: float,
                   dpi: float) -> Batch:
    assert len(layers) <= len(colors)
    batch = Batch()
    for i, drawing in enumerate(layers):
        color = colors[i]
        path: shapely.LineString
        for path in shapely.get_parts(layers):
            grp = Group()
            screen_coords = [(dpi * x, dpi * (height - y)) for x, y in path.coords]
            vertices = path[0] + tuple(chain(*screen_coords)) + screen_coords[-1]
            batch.add(len(vertices) // 2, gl.GL_LINE_STRIP, grp, ('v2f', vertices),
                      ('c4B', color * (len(vertices) // 2)))
    return batch


def render_gl(drawings: list[shapely.MultiLineString], width: float, height: float, dpi=128):
    batch = batch_drawings(drawings, height, dpi)
    config = gl.Config(sample_buffers=1, samples=8, double_buffer=True)
    win = window.Window(int(width * dpi), int(height * dpi), "plot preview",
                        config=config)

    @win.event
    def on_draw():
        gl.glEnable(gl.GL_LINE_SMOOTH)
        win.clear()
        batch.draw()

    app.run()
