import pytest
import shapely
from _pytest.fixtures import fixture

from elkplot.renderer import render_gl
from test import config


@fixture
def square() -> shapely.MultiLineString:
    return shapely.multilinestrings([[(1, 1), (1, 2), (2, 2), (2, 1), (1, 1)]])


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_render(square):
    render_gl([square], 5, 5)
