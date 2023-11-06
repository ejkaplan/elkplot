from typing import Optional
import shapely
import shapely.ops
from rtree.index import Index
from tqdm import tqdm

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
            idx = next(self.index.nearest(p, 1))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[idx].coords[0])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, False
        try:
            idx = next(self.r_index.nearest(p, 1))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[idx].coords[-1])
        dist = shapely.Point(p).distance(point)
        if dist <= tolerance:
            return idx, True
        return None, False

    def find_nearest(self, p: tuple[float, float]) -> tuple[Optional[int], bool]:
        try:
            f_idx = next(self.index.nearest(p, 1))
        except StopIteration:
            return None, False
        point = shapely.Point(self.lines[f_idx].coords[0])
        fdist = shapely.Point(p).distance(point)
        try:
            r_idx = next(self.r_index.nearest(p, 1))
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
        return next(self.index.nearest((0, 0), 1))

    def __len__(self):
        return self.length


def _sort_paths_single(
    paths: shapely.MultiLineString, pbar: bool = True
) -> shapely.MultiLineString:
    path_list = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    n_paths = len(paths)
    paths = shapely.MultiLineString(path_list)
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
    paths_list = [path for path in shapely.get_parts(paths) if shapely.length(path) > 0]
    if len(paths_list) < 2:
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