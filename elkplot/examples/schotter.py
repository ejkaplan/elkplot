import random

import numpy as np
import shapely
from shapely import affinity

import elkplot
from elkplot.easing import ease_in_sine

"""
Recreates drawings in the style of "Schotter" by Georg Nees.
"""


def schotter(rows: int, cols: int, rng: np.random.Generator) -> shapely.MultiLineString:
    # The affine transformation functions create transformed copies, so we only need to create the square once.
    square = shapely.LinearRing([(0, 0), (0, 1), (1, 1), (1, 0)])

    shapes = []
    for r in range(rows):
        # Easing in lets us introduce the randomness slowly at the top of the page and ramp up
        p = ease_in_sine(r / rows)
        for c in range(cols):
            x_offset, y_offset = p * rng.uniform(-1, 1, 2)
            cell = affinity.translate(square, c + x_offset, r + y_offset)
            theta = random.uniform(-np.pi / 2, np.pi / 2) * p
            cell = affinity.rotate(cell, theta, use_radians=True)
            shapes.append(cell)
    return shapely.union_all(shapes)


def main():
    rng = np.random.default_rng()
    size = 8 * elkplot.UNITS.inch, 15 * elkplot.UNITS.inch
    drawing = schotter(20, 10, rng)
    drawing = elkplot.scale_to_fit(drawing, *size, 0.5 * elkplot.UNITS.inch)
    print(elkplot.metrics(drawing))
    drawing = elkplot.optimize(drawing, 0.01)
    print(elkplot.metrics(drawing))
    elkplot.draw(drawing, *size, plot=False, preview_dpi=80)


if __name__ == "__main__":
    main()
