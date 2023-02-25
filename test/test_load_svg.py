import pytest
import shapely

from elkplot import load_svg, draw, scale_to_fit, sizes, center
from test import config


@pytest.fixture
def svg_stars() -> shapely.GeometryCollection:
    shape = load_svg("stars.svg")
    shape = scale_to_fit(shape, *sizes.A3)
    shape = center(shape, *sizes.A3)
    return shape


@pytest.fixture
def svg_text() -> shapely.GeometryCollection:
    shape = load_svg("text.svg")
    shape = scale_to_fit(shape, *sizes.A3)
    shape = center(shape, *sizes.A3)
    return shape


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_draw_loaded_svg(svg_stars: shapely.GeometryCollection):
    draw(svg_stars)


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_draw_loaded_svg(svg_text: shapely.GeometryCollection):
    draw(svg_text)
