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


def flatten_geometry(geom: GeometryT) -> shapely.MultiLineString:
    """
    Given any arbitrary shapely Geometry, flattens it down to a single MultiLineString that will be rendered as a
    single color-pass if sent to the plotter. Also converts Polygons to their outlines - if you want to render a filled
    in Polygon, use the `shade` function.
    Args:
        geom: The geometry to be flattened down. Most often this will be a GeometryCollection or a MultiPolygon.

    Returns:
        The flattened geometry
    """
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
    Calculate the width and height of the bounding box of a shapely geometry.
    Args:
        geom: The shapely Geometry object to be measured

    Returns:
        width in inches
        height in inches

    """
    x_min, y_min, x_max, y_max = geom.bounds
    return (x_max - x_min) * UNITS.inch, (y_max - y_min) * UNITS.inch


def up_length(drawing: shapely.MultiLineString) -> pint.Quantity:
    """
    Calculate the total distance travelled by the pen while not in contact with the page.
    This can be improved by merging and/or reordering the paths using the `optimize` function.
    Args:
        drawing: A single layer of plotter art

    Returns:
        The total pen-up distance in inches

    """
    distance = 0
    origin = shapely.points((0, 0))
    pen_position = origin
    for path in shapely.get_parts(drawing):
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
    Scales a drawing up or down to perfectly fit into a given bounding box.
    Args:
        drawing: The shapely geometry to rescale
        width: The width of the bounding box in inches (or any other unit if you pass in a `pint.Quantity`.)
        height: The height of the bounding box in inches (or any other unit if you pass in a `pint.Quantity`.)
        padding: How much space to leave empty on all sides in inches (or any other unit if you pass in a `pint.Quantity`.)
            [default=0]

    Returns:
        A copy of the drawing having been rescaled and moved such that the new upper-left corner of the bounding
        box (including the padding) is at the origin

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
    Fits a drawing into a bounding box of a given width and height, but unlike `scale_to_fit` also rotates the shape to
    make it take up as much of that area as possible
    Args:
        drawing: The shapely geometry to rescale
        width: The width of the bounding box in inches (or any other unit if you pass in a `pint.Quantity`.)
        height: The height of the bounding box in inches (or any other unit if you pass in a `pint.Quantity`.)
        padding: How much space to leave empty on all sides in inches (or any other unit if you pass in a `pint.Quantity`.)
        increment: The gap between different rotation angles attempted in radians. (smaller value gives better results,
            but larger values run faster.)

    Returns:
        A copy of the drawing having been rotated, rescaled, and moved such that the new upper-left corner of the
            bounding box (including the padding) is at the origin

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


@UNITS.wraps(None, (None, "inch", "inch", "inch", "inch", None), False)
def center(
    drawing: GeometryT,
    width: float,
    height: float,
    x: float = 0,
    y: float = 0,
) -> GeometryT:
    """
    Return a copy of a drawing that has been translated (but not scaled) to the center point of a given rectangle
    Args:
        drawing: The drawing to translate
        width: The width of the rectangle in inches (or any other unit if you pass in a `pint.Quantity`.)
        height: The height of the rectangle in inches (or any other unit if you pass in a `pint.Quantity`.)
        x: x-coordinate of the upper-left corner of the rectangle in inches (or any other unit if you pass in a `pint.Quantity`.)
        y: y-coordinate of the upper-left corner of the rectangle in inches (or any other unit if you pass in a `pint.Quantity`.)

    Returns:
        A copy of the drawing having been translated to the center of the rectangle
    """
    x_min, y_min, x_max, y_max = drawing.bounds
    center_point = shapely.Point((x_min + x_max) / 2, (y_min + y_max) / 2)
    dx, dy = x + width / 2 - center_point.x, y + height / 2 - center_point.y
    return affinity.translate(drawing, dx, dy)


def _weld(a: shapely.LineString, b: shapely.LineString) -> shapely.LineString:
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
    paths = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    n_paths = len(paths)
    paths = shapely.MultiLineString(paths)
    if n_paths < 2:
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


def _sort_paths(
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
                _sort_paths(layer, pbar)
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
            path = _weld(path, extension)
        out.append(path)
    while len(line_index) > 0:
        i = line_index.next_available_id()
        out.append(line_index.pop(i))
    return shapely.MultiLineString(out)


@UNITS.wraps(None, (None, "inch", None), False)
def _join_paths(
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
                _join_paths(layer, tolerance, pbar=pbar)
                for layer in tqdm(
                    layers,
                    desc="Joining Layers",
                    disable=not pbar,
                )
            ]
        )
    return geometry


def _reloop_paths_single(
    geometry: shapely.MultiLineString, pbar: bool = True
) -> shapely.MultiLineString:
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


def _reloop_paths(
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
                _reloop_paths(layer, pbar)
                for layer in tqdm(layers, desc="Relooping Layers", disable=not pbar)
            ]
        )
    return geometry


@UNITS.wraps(None, (None, "inch", None), False)
def _delete_short_paths_single(
    geometry: shapely.MultiLineString, min_length: float, pbar: bool = True
) -> shapely.MultiLineString:
    parts = shapely.get_parts(geometry).tolist()
    return shapely.MultiLineString(
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
def _delete_short_paths(
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
                _delete_short_paths(layer, min_length, pbar)
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
    """
    Optimize a shapely geometry for plotting by combining paths, re-ordering paths, and/or deleting short paths.
    Always merges paths whose ends are closer together than a given tolerance.
    Can also randomize the starting point for closed loops to help hide the dots that appear at the moment the pen hits
    the page.
    Args:
        geometry: The shapely geometry to be optimized. Usually this is either a `MultiLineString` or a
            `GeometryCollection` depending on if you are optimizing a single layer or a multi-layer plot.
        tolerance: The largest gap that should be merged/the longest line that should be deleted in inches (or any other unit if you pass in a `pint.Quantity`.)
        sort: Should the paths be re-ordered to minimize pen-up travel distance?
        reloop: Should closed loop paths have their starting point randomized?
        delete_small: Should paths shorter than `tolerance` be deleted?
        pbar: Should progress bars be displayed to keep the user updated on the progress of the process?

    Returns:
        The optimized geometry

    """
    if reloop:
        geometry = _reloop_paths(geometry)
    geometry = _join_paths(geometry, tolerance, pbar)
    if delete_small:
        geometry = _delete_short_paths(geometry, tolerance, pbar)
    if sort:
        geometry = _sort_paths(geometry, pbar)
    return geometry


@UNITS.wraps(None, (None, "rad", "inch", None), False)
def shade(
    polygon: shapely.Polygon | shapely.MultiPolygon,
    angle: float,
    spacing: float,
    offset: float = 0.5,
) -> shapely.MultiLineString:
    """
    Fill in a shapely Polygon or MultiPolygon with parallel lines so that the plotter will fill in the shape with lines.
    Args:
        polygon: The shape to be filled in
        angle: The angle at which the parallel lines should travel in radians (or any other unit if you pass in a `pint.Quantity`.)
        spacing: The gap between parallel lines in inches (or any other unit if you pass in a `pint.Quantity`.)
        offset: How much should the parallel lines be shifted up or down as a percentage of the spacing?

    Returns:
        The MultiLineString of the shaded lines. (NOTE: Does not include the outline.)

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
    """
    Calculate the pen down distance, pen up distance, and number of discrete paths (requiring penlifts between) in a given drawing.
    Args:
        drawing:

    Returns:
        A `DrawingMetrics` object containing fields for `pen_down_dist`, `pen_up_dist`, and `path_count`

    """
    mls = flatten_geometry(drawing)
    return DrawingMetrics(
        mls.length * UNITS.inch, up_length(mls), shapely.get_num_geometries(mls)
    )
