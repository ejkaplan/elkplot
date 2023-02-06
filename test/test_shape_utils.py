import numpy as np
import pytest
import shapely
from hypothesis import given
from hypothesis.strategies import floats

from elkplot.shape_utils import (
    up_length,
    sort_paths,
    scale_to_fit,
    size,
    rotate_and_scale_to_fit,
    join_paths,
)
from test.strategies import multilinestrings, layers


@given(drawing=multilinestrings)
def test_sort_paths(drawing: shapely.MultiLineString):
    unoptimized_penup_dist = up_length(drawing)
    optimized_drawing = sort_paths(drawing)
    optimized_penup_dist = up_length(optimized_drawing)
    assert optimized_penup_dist <= unoptimized_penup_dist


@given(
    drawing=layers,
    desired_w=floats(min_value=1, max_value=10),
    desired_h=floats(min_value=1, max_value=10),
)
def test_scale_to_fit(
    drawing: shapely.GeometryCollection, desired_w: float, desired_h: float
):
    scaled = scale_to_fit(drawing, desired_w, desired_h)
    w, h = size(scaled)
    assert w < desired_w or w == pytest.approx(desired_w)
    assert h < desired_h or h == pytest.approx(desired_h)
    assert w == pytest.approx(desired_w) or h == pytest.approx(desired_h)


@given(
    drawing=layers,
    desired_w=floats(min_value=1, max_value=10),
    desired_h=floats(min_value=1, max_value=10),
)
def test_rotate_and_scale_to_fit(
    drawing: shapely.GeometryCollection, desired_w: float, desired_h: float
):
    scaled = rotate_and_scale_to_fit(drawing, desired_w, desired_h)
    w, h = size(scaled)
    assert w < desired_w or w == pytest.approx(desired_w)
    assert h < desired_h or h == pytest.approx(desired_h)
    assert w == pytest.approx(desired_w) or h == pytest.approx(desired_h)

    pre_w, pre_h = size(drawing)
    pre_ratio = pre_w / pre_h
    desired_ratio = desired_w / desired_h
    pre_error = np.abs(pre_ratio - desired_ratio) / desired_ratio
    ratio = w / h
    post_error = np.abs(ratio - desired_ratio) / desired_ratio
    assert post_error < pre_error or post_error == pytest.approx(pre_error)


@given(lines=multilinestrings)
def test_join_paths_small_tolerance(lines: shapely.MultiLineString):
    joined = join_paths(lines, 0.01)
    assert len(shapely.get_parts(joined)) <= len(shapely.get_parts(lines))


@given(lines=multilinestrings)
def test_join_paths_big_tolerance(lines: shapely.MultiLineString):
    joined = join_paths(lines, 100)
    assert len(shapely.get_parts(joined)) == 1
