import numpy as np
import shapely

import elkplot


@elkplot.UNITS.wraps(None, ("inch", "inch", "inch", None), False)
def concentric_circles(
    x: float, y: float, radius: float, n: int
) -> shapely.MultiLineString:
    center = shapely.Point(x, y)
    circles = [center.buffer(r).exterior for r in np.linspace(0, radius, n + 1)[1:]]
    return shapely.union_all(circles)


def main():
    size = 20 * elkplot.UNITS.cm, 20 * elkplot.UNITS.cm
    margin = 0.5 * elkplot.UNITS.inch

    left_circles = concentric_circles(
        x=-1, y=0, radius=2, n=10
    )
    right_circles = concentric_circles(
        x=1, y=0, radius=2, n=15
    )
    top_circles = concentric_circles(
        x=0, y=np.sqrt(3), radius=2, n=20
    )

    circles = shapely.GeometryCollection([left_circles, right_circles, top_circles])
    circles = elkplot.scale_to_fit(circles, *size, margin)
    elkplot.draw(circles, *size, plot=False)


if __name__ == "__main__":
    main()
