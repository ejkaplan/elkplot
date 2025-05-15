"""
Recreates drawings in the style of "Schotter" by Georg Nees.
"""

# wheeeeeeeeeeee

import random

import numpy as np
import shapely
from shapely import affinity

import elkplot
import elkplot.easing


def schotter(rows: int, cols: int, rng: np.random.Generator) -> shapely.MultiLineString:
    # The affine transformation functions create transformed copies, so we only need to create the square once.
    square = shapely.LinearRing([(0, 0), (0, 1), (1, 1), (1, 0)])

    shapes = []
    for c in range(cols):
        # Easing in lets us introduce the randomness slowly at the top of the page and ramp up
        p = elkplot.easing.ease_in_sine(c / cols)
        for r in range(rows):
            # At most (p=1) we will allow the squares to offset by 1 inch in both directions
            x_offset, y_offset = p * rng.uniform(-1, 1, 2)
            cell = affinity.translate(square, c + x_offset, r + y_offset)
            # At full randomness (p=1), any orientation of the square is equally likely
            theta = p * random.uniform(-np.pi / 2, np.pi / 2)
            cell = affinity.rotate(cell, theta, use_radians=True)
            shapes.append(cell)
    return shapely.union_all(shapes)


def main():
    rng = np.random.default_rng(0)
    size = 15 * elkplot.UNITS.inch, 8 * elkplot.UNITS.inch
    drawing = schotter(10, 20, rng)
    drawing = elkplot.scale_to_fit(drawing, *size, 0.5 * elkplot.UNITS.inch)
    print(elkplot.metrics(drawing))
    drawing = elkplot.optimize(drawing, 0.01)
    print(elkplot.metrics(drawing))
    elkplot.draw(drawing, *size, plot=False, preview_dpi=80)


if __name__ == "__main__":
    main()
