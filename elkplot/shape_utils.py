from dataclasses import dataclass
from typing import TypeVar, Optional

import numpy as np
import pint
import shapely
import shapely.affinity as affinity
import shapely.ops
from tqdm import tqdm

from elkplot.sizes import UNITS
from elkplot.spatial import PathGraph, greedy_walk, PathIndex, reverse_path

GeometryT = TypeVar("GeometryT", bound=shapely.Geometry)


def _geom_to_multilinestring(geom: shapely.Geometry) -> shapely.MultiLineString:
    if isinstance(geom, shapely.MultiLineString):
        return geom
    if isinstance(geom, (shapely.LineString, shapely.LinearRing)):
        return shapely.multilinestrings([geom])
    elif isinstance(geom, (shapely.Polygon, shapely.MultiPolygon)):
        return _geom_to_multilinestring(geom.boundary)
    elif isinstance(geom, shapely.GeometryCollection):
        parts = [
            _geom_to_multilinestring(sub_geom) for sub_geom in shapely.get_parts(geom)
        ]
        return shapely.union_all(parts)
    return shapely.MultiLineString()


def size(geom: GeometryT) -> tuple[pint.Quantity, pint.Quantity]:
    """
    Return the width and height in inches of a shapely geometry.
    :param geom: The geometry to measure
    :return: (width, height)
    """
    x_min, y_min, x_max, y_max = geom.bounds
    return (x_max - x_min) * UNITS.inch, (y_max - y_min) * UNITS.inch


def up_length(lines: shapely.MultiLineString) -> pint.Quantity:
    """
    Calculate the total distance traveled by the pen while it is lifted, moving between shapes.
    If you want to know the pen-down distance, call `geometry.length`.
    To rearrange the draw order to reduce this distance, call `sort_paths(geometry)`
    :param lines: The line drawing to measure
    :return: The pen-up distance in inches
    """
    distance = 0
    origin = shapely.points((0, 0))
    pen_position = origin
    for path in shapely.get_parts(lines):
        path_start, path_end = shapely.points(path.coords[0]), shapely.points(
            path.coords[-1]
        )
        distance += shapely.distance(pen_position, path_start)
        pen_position = path_end
    return distance * UNITS.inch


def _sort_paths_single(
    lines: shapely.MultiLineString, label: Optional[int] = None, pbar: bool = True
) -> shapely.MultiLineString:
    """
    Re-order the LineStrings in a MultiLineString to reduce the pen-up travel distance.
    Does not guarantee optimality, but usually improves plot times significantly.
    Does NOT change the actual drawn image.
    :param lines: The line drawing to optimize
    :return: The re-ordered MultiLineString
    """
    path_graph = PathGraph(lines)
    path_order = list(greedy_walk(path_graph, label, pbar))
    return path_graph.get_route_from_solution(path_order)


def sort_paths(
    geometry: shapely.Geometry, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _sort_paths_single(geometry, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        return shapely.GeometryCollection(
            [
                _sort_paths_single(layer, i, pbar)
                for i, layer in enumerate(shapely.get_parts(geometry))
            ]
        )
    else:
        raise TypeError()


@UNITS.wraps(None, (None, UNITS.inch, UNITS.inch, UNITS.inch), False)
def scale_to_fit(
    drawing: GeometryT,
    width: float,
    height: float,
    padding: float = 0,
) -> GeometryT:
    """
    Scale up or down a shapely geometry until it barely fits inside a given bounding area.
    Usually used to make sure a drawing doesn't exceed the bounds of the page
    :param drawing: The geometry to resize
    :param width: The width of the bounding area in inches
    :param height: The height of the bounding area in inches
    :param padding: The desired margin between the drawing and the bounding area on all sides
    :return: The resized geometry
    """
    width -= padding * 2
    height -= padding * 2
    w, h = (dim.magnitude for dim in size(drawing))
    if w == 0:
        scale = height / h
    elif h == 0:
        scale = width / w
    else:
        scale = min(width / w, height / h)
    return affinity.scale(drawing, scale, scale)


@UNITS.wraps(None, (None, UNITS.inch, UNITS.inch, UNITS.inch, UNITS.rad), False)
def rotate_and_scale_to_fit(
    drawing: GeometryT,
    width: float,
    height: float,
    padding: float = 0,
    increment: float = 0.02,
) -> GeometryT:
    """
    Scale up or down a shapely geometry until it barely fits inside a given bounding area.
    Usually used to make sure a drawing doesn't exceed the bounds of the page.
    The drawing will be rotated to the orientation that allows it to cover as much of the given area as possible
    :param drawing: The geometry to resize
    :param width: The width of the bounding area in inches
    :param height: The height of the bounding area in inches
    :param padding: The desired margin between the drawing and the bounding area on all sides
    :param increment: The amount by which to increment rotation while searching for the best rotation. Smaller number
        is more accurate, larger number is faster. (default: 0.02 radians)
    :return: The rotated and resized geometry
    """
    width -= padding * 2
    height -= padding * 2
    desired_ratio = width / height
    best_geom, best_error = None, float("inf")
    for angle in np.arange(0, np.pi, increment):
        rotated = affinity.rotate(drawing, angle, use_radians=True)
        w, h = size(rotated)
        ratio = w / h
        error = np.abs(ratio - desired_ratio) / desired_ratio
        if error < best_error:
            best_geom, best_error = rotated, error
    return scale_to_fit(best_geom, width, height)


@UNITS.wraps(None, (None, UNITS.inch, UNITS.inch, None), False)
def center(
    drawing: GeometryT,
    width: float,
    height: float,
    use_centroid=False,
) -> GeometryT:
    """
    Moves a shapely geometry so that its center aligns with the center of a given bounding area
    :param drawing: The geometry to resize
    :param width: The width of the bounding area in inches
    :param height: The height of the bounding area in inches
    :param use_centroid: If True, aligns the centroid of the geometry with the center of the bounding area.
        otherwise aligns the center of the geometry's bounding box with the center of the bounding area
    :return: The centered geometry
    """
    if use_centroid:
        center_point = drawing.centroid
    else:
        xmin, ymin, xmax, ymax = drawing.bounds
        center_point = shapely.Point((xmin + xmax) / 2, (ymin + ymax) / 2)
    dx, dy = width / 2 - center_point.x, height / 2 - center_point.y
    return affinity.translate(drawing, dx, dy)


def weld(a: shapely.LineString, b: shapely.LineString) -> shapely.LineString:
    return shapely.LineString(list(a.coords) + list(b.coords))


@UNITS.wraps(None, (None, UNITS.inch, None, None), False)
def _join_paths_single(
    lines: shapely.MultiLineString,
    tolerance: float,
    layer: Optional[int] = None,
    pbar: bool = True,
) -> shapely.MultiLineString:
    """
    Merges lines in a multilinestring whose endpoints fall within a certain tolerance distance of each other.
    Sorts the lines to minimize penup distance in the process. (So don't call both functions)
    :param lines: The MultiLineString to merge
    :param tolerance: The maximum distance that the endpoints of two LineStrings can be and still get merged into
        one longer LineString
    :return: The merged geometry
    """
    lines = shapely.ops.linemerge(lines)
    if tolerance <= 0:
        return lines
    graph = PathGraph(lines)
    index = PathIndex(graph)
    bar = tqdm(
        total=len(index) // 2,
        desc=f"Joining layer #{layer}" if layer is not None else "Joining",
        disable=not pbar,
    )
    lines = []
    while len(index) > 0:
        idx = index.get_nearest(graph.get_coordinates(graph.ORIGIN))
        index.delete_pair(idx)
        bar.update(1)
        start, end = graph.get_coordinates(idx, end=False), graph.get_coordinates(
            idx, end=True
        )
        path = graph.get_path(idx)
        while True:
            changed = False
            try:
                nearest_start_idx = index.get_nearest(start)
            except StopIteration:
                break
            dist = graph.cost(nearest_start_idx, idx)
            if dist <= tolerance:
                near = reverse_path(graph.get_path(nearest_start_idx))
                path = weld(near, path)
                start = graph.get_coordinates(nearest_start_idx, end=True)
                index.delete_pair(nearest_start_idx)
                bar.update(1)
                changed = True
            try:
                nearest_end_idx = index.get_nearest(end)
            except StopIteration:
                break
            dist = graph.cost(idx, nearest_end_idx)
            if dist <= tolerance:
                near = graph.get_path(nearest_end_idx)
                path = weld(path, near)
                end = graph.get_coordinates(nearest_end_idx, end=False)
                index.delete_pair(nearest_end_idx)
                bar.update(1)
                changed = True
            if not changed:
                break
        lines.append(path)
    return shapely.MultiLineString(lines)


@UNITS.wraps(None, (None, UNITS.inch, None), False)
def join_paths(
    geometry: shapely.Geometry, tolerance: float, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _join_paths_single(geometry, tolerance, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        return shapely.GeometryCollection(
            [
                _join_paths_single(layer, tolerance, i, pbar=pbar)
                for i, layer in enumerate(shapely.get_parts(geometry))
            ]
        )
    else:
        raise TypeError()


def optimize(
    geometry: shapely.Geometry,
    join_tolerance: float = 0,
    sort: bool = True,
    pbar: bool = True,
) -> shapely.Geometry:
    geometry = join_paths(geometry, join_tolerance, pbar)
    if sort:
        geometry = sort_paths(geometry, pbar)
    return geometry


@UNITS.wraps(None, (None, UNITS.rad, UNITS.inch, None), False)
def shade(
    polygon: shapely.Polygon, angle: float, spacing: float, offset: float = 0.5
) -> shapely.MultiLineString:
    """
    Create parallel lines that fill in the body of a Polygon
    :param polygon: The polygon to shade
    :param angle: The angle at which the parallel fill lines should run
    :param spacing: The spacing between two fill lines, measured perpendicular to the lines
    :param offset: The offset of the first line, as a float in [0, 1], a percentage of the spacing
    :return: The fill lines
    """
    polygon = affinity.rotate(
        polygon, -angle, use_radians=True, origin=polygon.centroid
    )
    x0, y0, x1, y1 = polygon.bounds
    shading = shapely.MultiLineString(
        [[(x0, y), (x1, y)] for y in np.arange(y0 + offset * spacing, y1, spacing)]
    )
    shading = polygon.intersection(shading)
    return affinity.rotate(shading, angle, use_radians=True, origin=polygon.centroid)


@dataclass
class DrawingStats:
    pen_down_dist: pint.Quantity
    pen_up_dist: pint.Quantity
    path_count: int


def metrics(drawing: shapely.Geometry) -> DrawingStats:
    mls = _geom_to_multilinestring(drawing)
    return DrawingStats(
        mls.length * UNITS.inch, up_length(mls), shapely.get_num_geometries(mls)
    )
