import numpy as np
from elkplot.drawing import Drawing
import shapely


def test_scale():
    d = Drawing([shapely.Point(0, 0).buffer(3)])
    centered = d.centered(8, 10)
    assert centered.center.x == 4
    assert centered.center.y == 5

def test_rotate():
    d = Drawing([shapely.Point(1, 0).buffer(3)])
    rotated = d.rotate(np.pi/2, (0, 0))
    assert rotated.center.x == 0
    assert rotated.center.y == 1
    rotated = d.rotate(np.pi, (0, 0))
    assert rotated.center.x == -1
    assert rotated.center.y == 0
    rotated = d.rotate(3*np.pi/2, (0, 0))
    assert rotated.center.x == 0
    assert rotated.center.y == -1
    rotated = d.rotate(2*np.pi, (0, 0))
    assert rotated.center.x == 1
    assert rotated.center.y == 0