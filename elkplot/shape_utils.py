import shapely


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
