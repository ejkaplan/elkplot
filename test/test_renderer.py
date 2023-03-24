import numpy as np
import pytest
import shapely
from shapely import affinity

from elkplot import sizes, draw, UNITS
from test import config

rng = np.random.default_rng(0)


@UNITS.wraps(None, ("inch", "inch", None))
def random_squares(width: float, height: float, n: int) -> shapely.MultiLineString:
    square = shapely.linestrings([(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)])
    return shapely.union_all(
        [
            affinity.translate(square, rng.uniform(0, width), rng.uniform(0, height))
            for _ in range(n)
        ]
    )


@UNITS.wraps(None, ("inch", "inch", None))
def random_triangles(width: float, height: float, n: int) -> shapely.MultiLineString:
    triangle = shapely.linestrings([(0, -1), (-1, 1), (1, 1), (0, -1)])
    return shapely.union_all(
        [
            affinity.translate(triangle, rng.uniform(0, width), rng.uniform(0, height))
            for _ in range(n)
        ]
    )


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_draw():
    draw(
        [random_squares(*sizes.A3, 20), random_triangles(*sizes.A3, 20)],
        *sizes.A3,
        preview_dpi=64,
        plot=False
    )
