import numpy as np
import pytest
import shapely
from shapely import affinity

from elkplot import draw, scale_to_fit, center, Font, FUTURAL, sizes, join_paths
from test import config

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


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_draw():
    f = Font(FUTURAL, 300)
    text = center(f.text("TEST!"), *sizes.LETTER)
    layers = [random_squares(*sizes.LETTER, 20), random_triangles(*sizes.LETTER, 20)]
    layers = [layer.difference(text.buffer(0.1)) for layer in layers]
    layers.append(text)
    layers = [join_paths(layer, 0.01) for layer in layers]
    drawing = shapely.geometrycollections(layers)
    drawing = scale_to_fit(drawing, *sizes.LETTER, 0.5)
    drawing = center(drawing, *sizes.LETTER)
    draw(drawing, preview_size=sizes.LETTER, preview_dpi=64)
