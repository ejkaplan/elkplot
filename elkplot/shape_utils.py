import shapely
import shapely.ops

from elkplot.spatial import PathGraph, greedy_walk


def geom_to_multilinestring(geom: shapely.Geometry) -> shapely.MultiLineString:
    lines = shapely.MultiLineString()
    if isinstance(geom, (shapely.LineString, shapely.LinearRing, shapely.MultiLineString)):
        lines = lines.union(geom)
    elif isinstance(geom, (shapely.Polygon, shapely.MultiPolygon)):
        lines = lines.union(geom.boundary)
    elif isinstance(geom, shapely.GeometryCollection):
        for sub_geom in shapely.get_parts(geom):  # Replace with iteration if too expensive
            lines = lines.union(geom_to_multilinestring(sub_geom))
    return lines


def size(geom: shapely.Geometry) -> tuple[float, float]:
    x_min, y_min, x_max, y_max = geom.bounds
    return x_max - x_min, y_max - y_min


def pen_up_distance(drawing: shapely.MultiLineString) -> float:
    distance = 0
    origin = shapely.points((0,0))
    pen_position = origin
    for path in shapely.get_parts(drawing):
        path_start, path_end = shapely.points(path.coords[0]), shapely.points(path.coords[-1])
        distance += shapely.distance(pen_position, path_start)
        pen_position = path_end
    return distance


def sort_paths(drawing: shapely.MultiLineString) -> shapely.MultiLineString:
    path_graph = PathGraph(drawing)
    path_order = list(greedy_walk(path_graph))
    return path_graph.get_route_from_solution(path_order)
