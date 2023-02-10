from typing import TypeVar

import numpy as np
import shapely
import shapely.affinity as affinity
import shapely.ops

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


def size(geom: GeometryT) -> tuple[float, float]:
    """
    Return the width and height in inches of a shapely geometry.
    :param geom: The geometry to measure
    :return: (width, height)
    """
    x_min, y_min, x_max, y_max = geom.bounds
    return x_max - x_min, y_max - y_min


def up_length(lines: shapely.MultiLineString) -> float:
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
    return distance


def _sort_paths_single(lines: shapely.MultiLineString) -> shapely.MultiLineString:
    """
    Re-order the LineStrings in a MultiLineString to reduce the pen-up travel distance.
    Does not guarantee optimality, but usually improves plot times significantly.
    Does NOT change the actual drawn image.
    :param lines: The line drawing to optimize
    :return: The re-ordered MultiLineString
    """
    path_graph = PathGraph(lines)
    path_order = list(greedy_walk(path_graph))
    return path_graph.get_route_from_solution(path_order)


def sort_paths(
    geometry: shapely.Geometry,
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _sort_paths_single(geometry)
    elif isinstance(geometry, shapely.GeometryCollection):
        return shapely.GeometryCollection(
            [_sort_paths_single(layer) for layer in shapely.get_parts(geometry)]
        )
    else:
        raise TypeError()


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
    w, h = size(drawing)
    if w == 0:
        scale = height / h
    elif h == 0:
        scale = width / w
    else:
        scale = min(width / w, height / h)
    return affinity.scale(drawing, scale, scale)


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


def _join_paths_single(
    lines: shapely.MultiLineString, tolerance: float
) -> shapely.MultiLineString:
    """
    Merges lines in a multilinestring whose endpoints fall within a certain tolerance distance of each other.
    Sorts the lines to minimize penup distance in the process. (So don't call both functions)
    :param lines: The MultiLineString to merge
    :param tolerance: The maximum distance that the endpoints of two LineStrings can be and still get merged into
        one longer LineString
    :return: The merged geometry
    """
    new_order = sort_paths(lines)
    parts = list(shapely.get_parts(new_order))
    out_lines = []
    while len(parts) >= 2:
        a = parts.pop(0)
        b = parts[0]
        a_end = shapely.Point(a.coords[-1])
        b_start = shapely.Point(b.coords[0])
        if a_end.distance(b_start) <= tolerance:
            new_mid = (a.coords[-1][0] + b.coords[0][0]) / 2, (
                a.coords[-1][1] + b.coords[0][1]
            ) / 2
            new_line = shapely.linestrings(list(a.coords) + list(b.coords))
            parts[0] = new_line
        else:
            out_lines.append(a)
    out_lines += parts
    return shapely.multilinestrings(out_lines)


def join_paths(
    geometry: shapely.Geometry, tolerance: float
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiLineString):
        return _join_paths_single(geometry, tolerance)
    elif isinstance(geometry, shapely.GeometryCollection):
        return shapely.GeometryCollection(
            [
                _join_paths_single(layer, tolerance)
                for layer in shapely.get_parts(geometry)
            ]
        )
    else:
        raise TypeError()


def shade(
    polygon: shapely.Polygon, angle: float, spacing: float
) -> shapely.MultiLineString:
    """
    Create parallel lines that fill in the body of a Polygon
    :param polygon: The polygon to shade
    :param angle: The angle at which the parallel fill lines should run
    :param spacing: The spacing between two fill lines, measured perpendicular to the lines
    :return: The fill lines
    """
    polygon = affinity.rotate(
        polygon, -angle, use_radians=True, origin=polygon.centroid
    )
    x0, y0, x1, y1 = polygon.bounds
    shading = shapely.MultiLineString(
        [[(x0, y), (x1, y)] for y in np.arange(y0 + 0.5 * spacing, y1, spacing)]
    )
    shading = polygon.intersection(shading)
    return affinity.rotate(shading, angle, use_radians=True, origin=polygon.centroid)
