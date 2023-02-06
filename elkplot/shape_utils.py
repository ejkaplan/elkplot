from typing import Optional

import shapely
import shapely.ops
import shapely.affinity as affinity

from elkplot.spatial import PathGraph, greedy_walk


def geom_to_multilinestring(geom: shapely.Geometry) -> shapely.MultiLineString:
    lines = shapely.MultiLineString()
    if isinstance(
            geom, (shapely.LineString, shapely.LinearRing, shapely.MultiLineString)
    ):
        lines = lines.union(geom)
    elif isinstance(geom, (shapely.Polygon, shapely.MultiPolygon)):
        lines = lines.union(geom.boundary)
    elif isinstance(geom, shapely.GeometryCollection):
        for sub_geom in shapely.get_parts(
                geom
        ):  # Replace with iteration if too expensive
            lines = lines.union(geom_to_multilinestring(sub_geom))
    return lines


def size(geom: shapely.Geometry) -> tuple[float, float]:
    x_min, y_min, x_max, y_max = geom.bounds
    return x_max - x_min, y_max - y_min


def up_length(drawing: shapely.MultiLineString) -> float:
    distance = 0
    origin = shapely.points((0, 0))
    pen_position = origin
    for path in shapely.get_parts(drawing):
        path_start, path_end = shapely.points(path.coords[0]), shapely.points(
            path.coords[-1]
        )
        distance += shapely.distance(pen_position, path_start)
        pen_position = path_end
    return distance


def sort_paths(drawing: shapely.MultiLineString) -> shapely.MultiLineString:
    path_graph = PathGraph(drawing)
    path_order = list(greedy_walk(path_graph))
    return path_graph.get_route_from_solution(path_order)


def rotate_to_fit(layers: list[shapely.MultiLineString], width: float, height: float, step: float = 0.05,origin: tuple[float, float] | str,use_radians: bool = True) -> Optional[list[shapely.MultiLineString]]:
    combined = shapely.union_all(layers)
    for angle = np.arange(0, np.pi, step):
        rotated = affinity.rotate(combined, angle, origin=origin)
        w, h = size(rotated)
        if w <= width and h <= height:
            return [affity.rotate(layer, angle, origin=origin) for layer in layers]
    return None
