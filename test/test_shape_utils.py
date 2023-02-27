import numpy as np
import pytest
import shapely
from hypothesis import given
from hypothesis.strategies import floats

from elkplot import UNITS
from elkplot.shape_utils import (
    up_length,
    sort_paths,
    scale_to_fit,
    size,
    rotate_and_scale_to_fit,
    join_paths,
    center,
)
from test.conftest import approx_equals
from test.strategies import multilinestrings, layers, linestrings, quantities


@given(drawing=multilinestrings)
def test_sort_paths(drawing: shapely.MultiLineString):
    unoptimized_penup_dist = up_length(drawing)
    optimized_drawing = sort_paths(drawing, tsp_time=1)
    optimized_penup_dist = up_length(optimized_drawing)
    assert optimized_penup_dist <= unoptimized_penup_dist


@given(
    drawing=layers,
    desired_w=quantities(1, 10, 'inch'),
    desired_h=quantities(1, 10, 'inch'),
)
def test_scale_to_fit(
    drawing: shapely.GeometryCollection, desired_w: float, desired_h: float
):
    scaled = scale_to_fit(drawing, desired_w, desired_h)
    w, h = size(scaled)
    assert w < desired_w or approx_equals(w, desired_w, "inch")
    assert h < desired_h or approx_equals(h, desired_h, "inch")
    assert approx_equals(w, desired_w, "inch") or approx_equals(h, desired_h, "inch")


@given(
    drawing=layers,
    desired_w=quantities(1, 10, 'inch'),
    desired_h=quantities(1, 10, 'inch'),
)
def test_rotate_and_scale_to_fit(
    drawing: shapely.GeometryCollection, desired_w: float, desired_h: float
):
    scaled = rotate_and_scale_to_fit(drawing, desired_w, desired_h)
    w, h = size(scaled)
    assert w < desired_w or approx_equals(w, desired_w, "inch")
    assert h < desired_h or approx_equals(h, desired_h, "inch")
    assert approx_equals(w, desired_w, "inch") or approx_equals(h, desired_h, "inch")

    pre_w, pre_h = size(drawing)
    pre_ratio = pre_w / pre_h
    desired_ratio = desired_w / desired_h
    pre_error = np.abs(pre_ratio - desired_ratio) / desired_ratio
    ratio = w / h
    post_error = np.abs(ratio - desired_ratio) / desired_ratio
    assert post_error < pre_error or post_error == pytest.approx(pre_error)


@given(lines=multilinestrings)
def test_join_paths_small_tolerance(lines: shapely.MultiLineString):
    joined = join_paths(lines, 0.01, pbar=False)
    assert len(shapely.get_parts(joined)) <= len(shapely.get_parts(lines))


@given(lines=multilinestrings)
def test_join_paths_big_tolerance(lines: shapely.MultiLineString):
    joined = join_paths(lines, 100, pbar=False)
    assert len(shapely.get_parts(joined)) == 1


def test_join_paths_squares(squares: shapely.MultiLineString):
    joined = join_paths(squares, 0.01, pbar=False)
    assert len(shapely.get_parts(joined)) < len(shapely.get_parts(squares))


@given(lines=linestrings)
def test_center(lines: shapely.LineString):
    size = 20 * UNITS.inch
    centered_bounding = center(lines, size, size)
    xmin, ymin, xmax, ymax = centered_bounding.bounds
    assert (xmin + xmax) / 2 == pytest.approx(10)
    assert (ymin + ymax) / 2 == pytest.approx(10)
    centered_centroid = center(lines, size, size, True)
    assert centered_centroid.centroid.x == pytest.approx(10)
    assert centered_centroid.centroid.y == pytest.approx(10)
