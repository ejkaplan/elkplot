import numpy as np
import shapely
from pytest import fixture
from shapely import affinity

from elkplot import sizes

rng = np.random.default_rng(0)


def random_squares(width: float, height: float, n: int) -> shapely.MultiLineString:
    square = shapely.linestrings([(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)])
    return shapely.union_all(
        [
            affinity.translate(square, rng.uniform(0, width), rng.uniform(0, height))
            for _ in range(n)
        ]
    )


def random_triangles(width: float, height: float, n: int) -> shapely.MultiLineString:
    triangle = shapely.linestrings([(0, -1), (-1, 1), (1, 1), (0, -1)])
    return shapely.union_all(
        [
            affinity.translate(triangle, rng.uniform(0, width), rng.uniform(0, height))
            for _ in range(n)
        ]
    )


@fixture
def squares() -> shapely.MultiLineString:
    return random_squares(*sizes.LETTER, 20)


@fixture
def triangles() -> shapely.MultiLineString:
    return random_triangles(*sizes.LETTER, 20)
