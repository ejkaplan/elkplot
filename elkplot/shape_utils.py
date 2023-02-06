from typing import TypeVar

import numpy as np
import shapely
import shapely.affinity as affinity
import shapely.ops

from elkplot.spatial import PathGraph, greedy_walk

GeometryT = TypeVar("GeometryT", bound=shapely.Geometry)


def geom_to_multilinestring(geom: shapely.Geometry) -> shapely.MultiLineString:
    if isinstance(geom, shapely.MultiLineString):
        return geom
    if isinstance(geom, (shapely.LineString, shapely.LinearRing)):
        return shapely.multilinestrings([geom])
    elif isinstance(geom, (shapely.Polygon, shapely.MultiPolygon)):
        return shapely.multilinestrings(geom.boundary)
    elif isinstance(geom, shapely.GeometryCollection):
        parts = [
            geom_to_multilinestring(sub_geom) for sub_geom in shapely.get_parts(geom)
        ]
        return shapely.union_all(parts)
    return shapely.MultiLineString()


def size(geom: shapely.Geometry) -> tuple[float, float]:
    x_min, y_min, x_max, y_max = geom.bounds
    return x_max - x_min, y_max - y_min


def up_length(lines: shapely.MultiLineString) -> float:
    distance = 0
    origin = shapely.points((0, 0))
    pen_position = origin
    for path in shapely.get_parts(lines):
        path_start, path_end = shapely.points(path.coords[0]), shapely.points(
            path.coords[-1]
        )
        distance += shapely.distance(pen_position, path_start)
        pen_position = path_end
    return distance


def sort_paths(lines: shapely.MultiLineString) -> shapely.MultiLineString:
    path_graph = PathGraph(lines)
    path_order = list(greedy_walk(path_graph))
    return path_graph.get_route_from_solution(path_order)


def scale_to_fit(
    drawing: GeometryT,
    width: float,
    height: float,
    padding: float = 0,
    origin: tuple[float, float] | str = "center",
) -> GeometryT:
    width -= padding * 2
    height -= padding * 2
    w, h = size(drawing)
    if w == 0:
        scale = height / h
    elif h == 0:
        scale = width / w
    else:
        scale = min(width / w, height / h)
    return affinity.scale(drawing, scale, scale, origin=origin)


def rotate_and_scale_to_fit(
    drawing: GeometryT,
    width: float,
    height: float,
    padding: float = 0,
    origin: tuple[float, float] | str = "center",
    increment: float = 0.02,
) -> GeometryT:
    width -= padding * 2
    height -= padding * 2
    desired_ratio = width / height
    best_geom, best_error = None, float("inf")
    for angle in np.arange(0, np.pi, increment):
        rotated = affinity.rotate(drawing, angle, origin, True)
        w, h = size(rotated)
        ratio = w / h
        error = np.abs(ratio - desired_ratio) / desired_ratio
        if error < best_error:
            best_geom, best_error = rotated, error
    return scale_to_fit(best_geom, width, height, origin=origin)


def join_paths(
    lines: shapely.MultiLineString, tolerance: float
) -> shapely.MultiLineString:
    new_order = sort_paths(lines)
    parts = list(shapely.get_parts(new_order))
    out_lines = []
    while len(parts) >= 2:
        a = parts.pop(0)
        b = parts[0]
        a_end = shapely.Point(a.coords[-1])
        b_start = shapely.Point(b.coords[0])
        if a_end.distance(b_start) <= tolerance:
            new_line = shapely.linestrings(list(a.coords) + b.coords[1:])
            parts[0] = new_line
        else:
            out_lines.append(a)
    out_lines += parts
    return shapely.multilinestrings(out_lines)


def shade(
    polygon: shapely.Polygon, angle: float, spacing: float
) -> shapely.MultiLineString:
    polygon = affinity.rotate(
        polygon, -angle, use_radians=True, origin=polygon.centroid
    )
    x0, y0, x1, y1 = polygon.bounds
    shading = shapely.MultiLineString(
        [[(x0, y), (x1, y)] for y in np.arange(y0 + 0.5 * spacing, y1, spacing)]
    )
    shading = polygon.intersection(shading)
    return affinity.rotate(shading, angle, use_radians=True, origin=polygon.centroid)
