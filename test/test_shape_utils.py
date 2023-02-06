import shapely
from hypothesis import given

from elkplot.shape_utils import up_length, sort_paths
from test.strategies import multilinestrings


@given(drawing=multilinestrings)
def test_sort_paths(drawing: shapely.MultiLineString):
    unoptimized_penup_dist = up_length(drawing)
    optimized_drawing = sort_paths(drawing)
    optimized_penup_dist = up_length(optimized_drawing)
    assert 0 < optimized_penup_dist <= unoptimized_penup_dist
