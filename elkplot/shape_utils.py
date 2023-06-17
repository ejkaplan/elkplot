from dataclasses import dataclass
from typing import TypeVar, Optional

import numpy as np
import pint
import shapely
import shapely.affinity as affinity
import shapely.ops
from rtree import Index
from tqdm import tqdm

from elkplot.sizes import UNITS

GeometryT = TypeVar("GeometryT", bound=shapely.Geometry)


def flatten_geometry(geom: shapely.Geometry) -> shapely.MultiLineString:
    if isinstance(geom, shapely.MultiLineString):
        return geom
    if isinstance(geom, (shapely.LineString, shapely.LinearRing)):
        return shapely.multilinestrings([geom])
    elif isinstance(geom, shapely.Polygon):
        shapes = [geom.exterior] + list(geom.interiors)
        return shapely.union_all([flatten_geometry(shape) for shape in shapes])
    elif isinstance(geom, (shapely.GeometryCollection, shapely.MultiPolygon)):
        parts = [flatten_geometry(sub_geom) for sub_geom in shapely.get_parts(geom)]
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
    w, h = (dim.magnitude for dim in size(drawing))
    if w == 0:
        scale = (height - padding * 2) / h
    elif h == 0:
        scale = (width - padding * 2) / w
    else:
        scale = min((width - padding * 2) / w, (height - padding * 2) / h)
    return center(affinity.scale(drawing, scale, scale), width, height)


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
    desired_ratio = (width - padding * 2) / (height - padding * 2)
    best_geom, best_error = None, float("inf")
    for angle in np.arange(0, np.pi, increment):
        rotated = affinity.rotate(drawing, angle, use_radians=True)
        w, h = size(rotated)
        ratio = w / h
        error = np.abs(ratio - desired_ratio) / desired_ratio
        if error < best_error:
            best_geom, best_error = rotated, error
    return scale_to_fit(best_geom, width, height, padding)


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
        try:
            idx = next(self.index.nearest(p))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[idx].coords[0])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, False
        try:
            idx = next(self.r_index.nearest(p))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[idx].coords[-1])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, True
        return None, False

    def find_nearest(self, p: tuple[float, float]) -> tuple[int, bool]:
        try:
            f_idx = next(self.index.nearest(p))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[f_idx].coords[0])
        fdist = shapely.Point(p).distance(point)
        try:
            r_idx = next(self.r_index.nearest(p))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[r_idx].coords[-1])
        rdist = shapely.Point(p).distance(point)
        if fdist < rdist:
            return f_idx, False
        else:
            return r_idx, True

    def pop(self, idx: int) -> shapely.LineString:
        self.index.delete(idx, self.lines[idx].coords[0] * 2)
        self.r_index.delete(idx, self.lines[idx].coords[-1] * 2)
        self.length -= 1
        return self.lines[idx]

    def next_available_id(self) -> int:
        return next(self.index.nearest((0, 0)))

    def __len__(self):
        return self.length


def _sort_paths_single(
    paths: shapely.MultiLineString, pbar: bool = True
) -> shapely.MultiLineString:
    """
    Re-order the LineStrings in a MultiLineString to reduce the pen-up travel distance.
    Does not guarantee optimality, but usually improves plot times significantly.
    Does NOT change the actual drawn image.
    :param lines: The line drawing to optimize
    :return: The re-ordered MultiLineString
    """
    paths = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    if len(paths) < 2:
        return paths
    line_index = LineIndex(paths)
    out = []
    bar = tqdm(
        total=len(line_index), desc="Sorting Paths", disable=not pbar, leave=False
    )
    pos = (0, 0)
    while len(line_index) > 0:
        bar.update(1)
        idx, reverse = line_index.find_nearest(pos)
        next_line = line_index.pop(idx)
        if reverse:
            next_line = shapely.ops.substring(next_line, 1, 0, normalized=True)
        out.append(next_line)
        pos = next_line.coords[-1]
    return shapely.MultiLineString(out)


def sort_paths(
    geometry: shapely.Geometry, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiPolygon):
        return _sort_paths_single(geometry.boundary, pbar=pbar)
    if isinstance(geometry, shapely.MultiLineString):
        return _sort_paths_single(geometry, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                sort_paths(layer, pbar)
                for layer in tqdm(
                    layers,
                    desc="Sorting Layers",
                    disable=not pbar,
                )
            ]
        )
    else:
        return geometry


def _join_paths_single(
    paths: shapely.MultiLineString, tolerance: float, pbar: bool = True
) -> shapely.MultiLineString:
    paths = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    if len(paths) < 2:
        return paths
    line_index = LineIndex(paths)
    out = []
    bar = tqdm(
        total=len(line_index), desc="Joining Paths", disable=not pbar, leave=False
    )
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
        i = line_index.next_available_id()
        out.append(line_index.pop(i))
    return shapely.MultiLineString(out)


@UNITS.wraps(None, (None, "inch", None), False)
def join_paths(
    geometry: shapely.Geometry, tolerance: float, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiPolygon):
        return _join_paths_single(geometry.boundary, tolerance, pbar=pbar)
    elif isinstance(geometry, shapely.MultiLineString):
        return _join_paths_single(geometry, tolerance, pbar=pbar)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                join_paths(layer, tolerance, pbar=pbar)
                for layer in tqdm(
                    layers,
                    desc="Joining Layers",
                    disable=not pbar,
                )
            ]
        )
    return geometry


def _reloop_paths_single(geometry: shapely.MultiLineString, pbar: bool=True) -> shapely.MultiLineString:
    rng = np.random.default_rng()
    lines = []
    parts = shapely.get_parts(geometry).tolist()
    for linestring in tqdm(
        parts, desc="Relooping Paths", leave=False, disable=not pbar
    ):
        coordinates = list(linestring.coords)
        if coordinates[0] == coordinates[-1]:
            coordinates = coordinates[:-1]
            reloop_index = rng.integers(len(coordinates), endpoint=False)
            new_coordinates = (
                coordinates[reloop_index:]
                + coordinates[:reloop_index]
                + [coordinates[reloop_index]]
            )
            lines.append(shapely.LineString(new_coordinates))
        else:
            lines.append(linestring)
    return shapely.union_all(lines)


def reloop_paths(
    geometry: shapely.Geometry, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiPolygon):
        return _reloop_paths_single(geometry.boundary)
    elif isinstance(geometry, shapely.MultiLineString):
        return _reloop_paths_single(geometry)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                reloop_paths(layer, pbar)
                for layer in tqdm(layers, desc="Relooping Layers", disable=not pbar)
            ]
        )
    return geometry


@UNITS.wraps(None, (None, "inch", None), False)
def _delete_short_paths_single(
    geometry: shapely.MultiLineString, min_length: float, pbar: bool = True
) -> shapely.MultiLineString:
    parts = shapely.get_parts(geometry).tolist()
    return shapely.union_all(
        [
            line
            for line in tqdm(
                parts,
                desc="Deleting Short Paths (Layer)",
                leave=False,
                disable=not pbar,
            )
            if line.length >= min_length
        ]
    )


@UNITS.wraps(None, (None, "inch", None), False)
def delete_short_paths(
    geometry: shapely.Geometry, min_length: float, pbar: bool = True
) -> shapely.MultiLineString | shapely.GeometryCollection:
    if isinstance(geometry, shapely.MultiPolygon):
        return _delete_short_paths_single(geometry.boundary, min_length)
    elif isinstance(geometry, shapely.MultiLineString):
        return _delete_short_paths_single(geometry, min_length)
    elif isinstance(geometry, shapely.GeometryCollection):
        layers = shapely.get_parts(geometry).tolist()
        return shapely.GeometryCollection(
            [
                delete_short_paths(layer, min_length, pbar)
                for layer in tqdm(layers, desc="Deleting Short Paths", disable=not pbar)
            ]
        )
    return geometry


@UNITS.wraps(None, (None, "inch", None, None, None, None), False)
def optimize(
    geometry: shapely.Geometry,
    tolerance: float = 0,
    sort: bool = True,
    reloop: bool = True,
    delete_small: bool = True,
    pbar: bool = True,
) -> shapely.Geometry:
    if reloop:
        geometry = reloop_paths(geometry)
    geometry = join_paths(geometry, tolerance, pbar)
    if delete_small:
        geometry = delete_short_paths(geometry, tolerance, pbar)
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
    mls = flatten_geometry(drawing)
    return DrawingMetrics(
        mls.length * UNITS.inch, up_length(mls), shapely.get_num_geometries(mls)
    )
