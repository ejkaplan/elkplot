from typing import Union
from xml.dom import minidom

import numpy as np
import shapely
from svg.path import parse_path, Line, CubicBezier, Close, QuadraticBezier


def complex_tuple(n: complex) -> tuple[float, float]:
    return n.real, n.imag


def svg_line_parse(line: Union[Line, Close]) -> list[tuple[float, float]]:
    return [complex_tuple(line.start), complex_tuple(line.end)]


def cubic_bezier_eval(nodes: np.ndarray, t: np.ndarray) -> np.ndarray:
    return (
        (1 - t) ** 3 * nodes[:, [0]]
        + 3 * (1 - t) ** 2 * t * nodes[:, [1]]
        + 3 * (1 - t) * t**2 * nodes[:, [2]]
        + t**3 * nodes[:, [3]]
    )


def quadratic_bezier_eval(nodes: np.ndarray, t: np.ndarray) -> np.ndarray:
    return (
        (1 - t) ** 2 * nodes[:, [0]]
        + 2 * (1 - t) * t * nodes[:, [1]]
        + t**2 * nodes[:, [2]]
    )


def svg_cubic_bezier_parse(
    bezier: CubicBezier, n: int = 128
) -> list[tuple[float, float]]:
    nodes = [
        complex_tuple(p)
        for p in (bezier.start, bezier.control1, bezier.control2, bezier.end)
    ]
    points = cubic_bezier_eval(np.array(nodes).T, np.linspace(0, 1, n))
    return [tuple(p) for p in points.T]


def svg_quadratic_bezier_parse(
    bezier: QuadraticBezier, n: int = 128
) -> list[tuple[float, float]]:
    nodes = [complex_tuple(p) for p in (bezier.start, bezier.control, bezier.end)]
    points = quadratic_bezier_eval(np.array(nodes).T, np.linspace(0, 1, n))
    return [tuple(p) for p in points.T]


def load_svg(path: str) -> shapely.GeometryCollection:
    """
    Import an SVG into shapely geometry
    :param path: The path on your system to the .svg file
    :return: A GeometryCollection containing the linestrings and polygons from the svg
    """
    with open(path) as f:
        doc = minidom.parse(f)
    paths = [
        parse_path(path.getAttribute("d")) for path in doc.getElementsByTagName("path")
    ]
    doc.unlink()
    shapes: list[shapely.LineString | shapely.Polygon] = []
    for path in paths:
        polygon = False
        path_points: list[tuple[float, float]] = []
        edge: list[tuple[float, float]] = []
        holes: list[list[tuple[float, float]]] = []
        for elem in path:
            if isinstance(elem, Line):
                path_points.extend(svg_line_parse(elem))
            elif isinstance(elem, CubicBezier):
                path_points.extend(svg_cubic_bezier_parse(elem))
            elif isinstance(elem, QuadraticBezier):
                path_points.extend(svg_quadratic_bezier_parse(elem))
            elif isinstance(elem, Close):
                polygon = True
                path_points.extend(svg_line_parse(elem))
                if edge:
                    holes.append(path_points)
                else:
                    edge = path_points
                path_points = []
        if polygon:
            shapes.append(shapely.Polygon(edge, holes))
        else:
            shapes.append(shapely.LineString(path_points))
    return shapely.geometrycollections(shapes)
