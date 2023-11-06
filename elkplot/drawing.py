from __future__ import annotations

from functools import cached_property
from typing import Optional
import numpy as np
import shapely
import shapely.affinity as affinity

from elkplot import shape_utils
from elkplot.optimization import optimize


class Drawing:
    def __init__(self, layers: Optional[list[shapely.Geometry]] = None) -> None:
        self._layers: list[shapely.Geometry] = [] if layers is None else layers

    @staticmethod
    def from_geometry_collection(gc: shapely.GeometryCollection) -> Drawing:
        return Drawing(list(shapely.get_parts(gc)))

    def __getitem__(self, key: int) -> shapely.Geometry:
        return self._layers[key]

    def __len__(self) -> int:
        return len(self._layers)

    @cached_property
    def geometry_collection(self) -> shapely.GeometryCollection:
        return shapely.GeometryCollection(
            [shape_utils.flatten_geometry(layer) for layer in self._layers]
        )

    @cached_property
    def bounds(
        self,
    ) -> tuple[float, float, float, float]:
        xmin, xmax, ymin, ymax = self.geometry_collection.bounds
        return xmin, xmax, ymin, ymax

    @cached_property
    def size(self) -> tuple[float, float]:
        x_min, y_min, x_max, y_max = self.bounds
        return x_max - x_min, y_max - y_min

    @cached_property
    def up_length(self) -> float:
        distance = 0
        origin = shapely.points((0, 0))
        for layer in shapely.get_parts(self.geometry_collection):
            pen_position = origin
            for path in shapely.get_parts(layer):
                path_start, path_end = (
                    shapely.points(path.coords[0]),
                    shapely.points(path.coords[-1]),
                )
                distance += shapely.distance(pen_position, path_start)
                pen_position = path_end
            distance += shapely.distance(pen_position, origin)
        return distance

    @cached_property
    def down_length(self) -> float:
        distance = 0
        for layer in shapely.get_parts(self.geometry_collection):
            distance += sum([path.length for path in shapely.get_parts(layer)])
        return distance

    def center(
        self, width: float, height: float, x: float = 0, y: float = 0
    ) -> Drawing:
        x_min, y_min, x_max, y_max = self.bounds
        center_point = shapely.Point((x_min + x_max) / 2, (y_min + y_max) / 2)
        dx, dy = x + width / 2 - center_point.x, y + height / 2 - center_point.y
        return Drawing.from_geometry_collection(
            affinity.translate(self.geometry_collection, dx, dy)
        )

    def rotate(self, angle: float, origin: str = "center") -> Drawing:
        return Drawing.from_geometry_collection(
            affinity.rotate(self.geometry_collection, angle, origin, True)
        )

    def scale(
        self, xfact: float = 1.0, yfact: float = 1.0, origin: str = "center"
    ) -> Drawing:
        return Drawing.from_geometry_collection(
            affinity.scale(self.geometry_collection, xfact, yfact, origin=origin)
        )

    def translate(self, xoff: float = 0.0, yoff: float = 0.0) -> Drawing:
        return Drawing.from_geometry_collection(
            affinity.translate(self.geometry_collection, xoff, yoff)
        )

    def scale_to_fit(self, width: float, height: float, padding: float) -> Drawing:
        w, h = self.size
        if w == 0 or width == 0:
            scale = (height - padding * 2) / h
        elif h == 0 or height == 0:
            scale = (width - padding * 2) / w
        else:
            scale = min((width - padding * 2) / w, (height - padding * 2) / h)
        return self.scale(scale, scale).center(width, height)

    def rotate_and_sacle_to_fit(
        self,
        width: float,
        height: float,
        padding: float = 0,
        increment: float = 0.01 * np.pi,
    ):
        desired_ratio = (width - padding * 2) / (height - padding * 2)
        best_geom, best_error = self, float("inf")
        for angle in np.arange(0, np.pi, increment):
            rotated = self.rotate(angle)
            w, h = rotated.size
            ratio = w / h
            error = np.abs(ratio - desired_ratio) / desired_ratio
            if error < best_error:
                best_geom, best_error = rotated, error
        return best_geom.scale_to_fit(width, height, padding)

    def optimize(
        self,
        tolerance: float = 0,
        sort: bool = True,
        reloop: bool = True,
        delete_small: bool = True,
        pbar: bool = True,
    ) -> Drawing:
        return Drawing.from_geometry_collection(
            optimize(
                self.geometry_collection, tolerance, sort, reloop, delete_small, pbar
            )
        )
    
    def add_layer(self, layer: shapely.Geometry) -> Drawing:
        return Drawing(self._layers + [layer])
    
    def stack(self, *drawings: Drawing) -> Drawing:
        all_drawings = (self,) + drawings
        return Drawing.stack_drawings(*all_drawings)
    
    def merge(self, *drawings: Drawing) -> Drawing:
        all_drawings = (self,) + drawings
        return Drawing.layer_wise_merge(*all_drawings)
    
    @staticmethod
    def layer_wise_merge(*drawings: Drawing) -> Drawing:
        out_layers = []
        for i in range(max(len(drawing) for drawing in drawings)):
            actual_layers = [drawing[i] for drawing in drawings if i < len(drawing)]
            out_layers.append(shapely.union_all(actual_layers))
        return Drawing(out_layers)
    
    @staticmethod
    def stack_drawings(*drawings: Drawing) -> Drawing:
        out_layers = []
        for drawing in drawings:
            out_layers += drawing._layers
        return Drawing(out_layers)
        
