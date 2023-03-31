from dataclasses import dataclass
from typing import TypeVar, Optional

import numpy as np
import pint
import shapely
import shapely.affinity as affinity
import shapely.ops
from rtree import Index
from tqdm import tqdm

import elkplot
from elkplot.sizes import UNITS
from elkplot.spatial import PathGraph, greedy_walk

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
    lines: shapely.MultiLineString, pbar: bool = True
) -> shapely.MultiLineString:
    """
    Re-order the LineStrings in a MultiLineString to reduce the pen-up travel distance.
    Does not guarantee optimality, but usually improves plot times significantly.
    Does NOT change the actual drawn image.
    :param lines: The line drawing to optimize
    :return: The re-ordered MultiLineString
    """
    path_graph = PathGraph(lines)
    path_order = list(greedy_walk(path_graph, pbar))
    optimized_path = path_graph.get_route_from_solution(path_order)
    return min([lines, optimized_path], key=lambda x: elkplot.up_length(x))


def sort_paths(
    geometry: shapely.Geometry, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _sort_paths_single(geometry, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                _sort_paths_single(layer, pbar)
                for i, layer in tqdm(
                    enumerate(layers),
                    desc="Sorting Layers",
                    disable=not pbar,
                    total=len(layers),
                )
            ]
        )
    else:
        raise TypeError()


@UNITS.wraps(None, (None, "inch", "inch", "inch"), False)
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


@UNITS.wraps(None, (None, "inch", "inch", "inch", "rad"), False)
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


@UNITS.wraps(None, (None, "inch", "inch", None), False)
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
    a_coords, b_coords = list(a.coords), list(b.coords)
    if a_coords[-1] == b_coords[0]:
        a_coords = a_coords[:-1]
    return shapely.LineString(a_coords + b_coords)


class LineIndex:
    def __init__(self, lines: shapely.MultiLineString):
        self.lines: list[shapely.LineString] = [
            line for line in shapely.get_parts(lines) if shapely.length(line) > 0
        ]
        self.length = len(self.lines)
        self.index = Index()
        self.r_index = Index()
        for i, line in enumerate(self.lines):
            self.index.insert(i, 2 * line.coords[0])
            self.r_index.insert(i, 2 * line.coords[-1])

    def find_nearest_within(
        self, p: tuple[float, float], tolerance: float
    ) -> tuple[Optional[int], bool]:
        idx = next(self.index.nearest(p))
        point = shapely.Point(self.lines[idx].coords[0])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, False
        idx = next(self.r_index.nearest(p))
        point = shapely.Point(self.lines[idx].coords[-1])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, True
        return None, False

    def pop(self, idx: int) -> shapely.LineString:
        self.index.delete(idx, self.lines[idx].coords[0] * 2)
        self.r_index.delete(idx, self.lines[idx].coords[-1] * 2)
        self.length -= 1
        return self.lines[idx]

    def next_available_id(self) -> int:
        return next(self.index.nearest((0, 0)))

    def __len__(self):
        return self.length


def _join_paths_single(
    paths: shapely.MultiLineString, tolerance: float, pbar: bool = True
) -> shapely.MultiLineString:
    paths = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    if len(paths) < 2:
        return paths
    line_index = LineIndex(paths)
    out = []
    bar = tqdm(total=len(line_index), desc="Joining Paths", disable=not pbar)
    while len(line_index) > 1:
        path = line_index.pop(line_index.next_available_id())
        bar.update(1)
        while True:
            idx, reverse = line_index.find_nearest_within(path.coords[-1], tolerance)
            if idx is None:
                idx, reverse = line_index.find_nearest_within(path.coords[0], tolerance)
                if idx is None:
                    break
                path = shapely.ops.substring(path, 1, 0, normalized=True)
            extension = line_index.pop(idx)
            bar.update(1)
            if reverse:
                extension = shapely.ops.substring(extension, 1, 0, normalized=True)
            path = weld(path, extension)
        out.append(path)
    while len(line_index) > 0:
        out.append(line_index.pop(0))
    return shapely.MultiLineString(out)


@UNITS.wraps(None, (None, "inch", None), False)
def join_paths(
    geometry: shapely.Geometry, tolerance: float, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _join_paths_single(geometry, tolerance, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                _join_paths_single(layer, tolerance, pbar=pbar)
                for i, layer in tqdm(
                    enumerate(layers),
                    desc="Joining Layers",
                    disable=not pbar,
                    total=len(layers),
                )
            ]
        )
    else:
        raise TypeError()


@UNITS.wraps(None, (None, "inch", None, None), False)
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


@UNITS.wraps(None, (None, "rad", "inch", None), False)
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
class DrawingMetrics:
    pen_down_dist: pint.Quantity
    pen_up_dist: pint.Quantity
    path_count: int

    def __str__(self) -> str:
        return f"{self.path_count} paths, pen down: {self.pen_down_dist:,.2f}, pen up: {self.pen_up_dist:,.2f}"


def metrics(drawing: shapely.Geometry) -> DrawingMetrics:
    mls = _geom_to_multilinestring(drawing)
    return DrawingMetrics(
        mls.length * UNITS.inch, up_length(mls), shapely.get_num_geometries(mls)
    )
