import pytest
import shapely

from elkplot import draw, scale_to_fit, center, Font, FUTURAL, sizes, join_paths
from test import config


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_draw(squares, triangles):
    f = Font(FUTURAL, 300)
    text = center(f.text("TEST!"), *sizes.LETTER)
    layers = [squares, triangles]
    layers = [layer.difference(text.buffer(0.1)) for layer in layers]
    layers.append(text)
    drawing = shapely.geometrycollections(layers)
    drawing = scale_to_fit(drawing, *sizes.LETTER, 0.5)
    drawing = join_paths(drawing, 0.01, 1)
    drawing = center(drawing, *sizes.LETTER)
    draw(drawing, *sizes.LETTER, preview_dpi=64, plot=False)
