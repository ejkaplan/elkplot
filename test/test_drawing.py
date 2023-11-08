import numpy as np
import pytest
from elkplot.drawing import Drawing
import shapely


def test_scale():
    d = Drawing(shapely.Point(0, 0).buffer(3), width=8, height=10)
    centered = d.fit_to_page()
    assert centered.center.x == pytest.approx(4)
    assert centered.center.y == pytest.approx(5)


def test_rotate():
    d = Drawing(shapely.Point(1, 0).buffer(3))
    rotated = d.rotate(np.pi / 2, (0, 0))
    assert rotated.center.x == 0
    assert rotated.center.y == 1
    rotated = d.rotate(np.pi, (0, 0))
    assert rotated.center.x == -1
    assert rotated.center.y == 0
    rotated = d.rotate(3 * np.pi / 2, (0, 0))
    assert rotated.center.x == 0
    assert rotated.center.y == -1
    rotated = d.rotate(2 * np.pi, (0, 0))
    assert rotated.center.x == 1
    assert rotated.center.y == 0


def test_optimize():
    rng = np.random.default_rng()
    d = Drawing(
        *[
            shapely.union_all(
                [shapely.Point(*rng.uniform(0, 8, 2)).buffer(rng.uniform(1, 3)).exterior]
            )
            for _ in range(20)
        ]
    )
    old_up_dist = d.up_length
    d = d.optimize(pbar=False)
    assert d.up_length < old_up_dist
