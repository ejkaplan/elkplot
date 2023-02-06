import shapely
from hypothesis import given

from elkplot.shape_utils import pen_up_distance, sort_paths
from test.generators import multilinestrings


@given(drawing=multilinestrings)
def test_sort_paths(drawing: shapely.MultiLineString):
    unoptimized_penup_dist = pen_up_distance(drawing)
    optimized_drawing = sort_paths(drawing)
    optimized_penup_dist = pen_up_distance(optimized_drawing)
    assert 0 < optimized_penup_dist <= unoptimized_penup_dist
