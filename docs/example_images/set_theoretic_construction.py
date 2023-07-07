import numpy as np
import shapely
from shapely import affinity

import elkplot


@elkplot.UNITS.wraps(None, ("inch", "inch", "inch"), False)
def overlapping_star(x: float, y: float, r: float) -> shapely.GeometryCollection:
    triangle = shapely.Polygon(
        [
            (x + r * np.cos(theta), y + r * np.sin(theta))
            for theta in np.linspace(0, 2 * np.pi, 3, endpoint=False)
        ]
    )
    star_poly = triangle.union(
        affinity.rotate(triangle, np.pi, use_radians=True, origin="centroid")
    )
    top_star_ribbon = star_poly.difference(
        affinity.scale(star_poly, 0.95, 0.95, origin="centroid")
    )
    bottom_star_ribbon = affinity.rotate(
        top_star_ribbon, np.pi / 2, use_radians=True, origin="centroid"
    )
    bottom_star_ribbon = bottom_star_ribbon.difference(top_star_ribbon.buffer(0.05))
    return shapely.GeometryCollection(
        [top_star_ribbon.exterior, bottom_star_ribbon.exterior]
    )


def main():
    size = 20 * elkplot.UNITS.cm, 20 * elkplot.UNITS.cm
    margin = 0.5 * elkplot.UNITS.inch

    star = overlapping_star(size[0] / 2, size[1] / 2, min(size) / 2 - margin)

    elkplot.draw(star, *size, plot=False)


if __name__ == "__main__":
    main()
