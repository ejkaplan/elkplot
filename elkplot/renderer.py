from __future__ import division

from itertools import chain
from typing import Optional

import numpy as np
import shapely
from os import environ

environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

COLORS = [
    (0, 0, 255, 255),  # blue
    (255, 0, 0, 255),  # red
    (0, 82, 33, 255),  # dark green
    (255, 123, 0, 255),  # orange
    (8, 142, 149, 255),  # aqua
    (255, 0, 255, 255),  # fuchsia
    (158, 253, 56, 255),  # lime
    (206, 81, 113, 255),  # hot pink
]


def _random_color(rng: np.random.Generator) -> tuple[int, int, int, int]:
    r, g, b = rng.integers(0, 256, 3)
    return (r, g, b, 255)


def render(
    layers: list[shapely.MultiLineString],
    width: float,
    height: float,
    dpi: float = 64,
    bg_color: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """
    NOTE: You will probably not want to call this directly and instead use elkplot.draw
    Displays a preview of what the plotter will draw. Each layer is rendered in a different color. The first 8 layers'
    colors have been chosen with maximum distinguishability in mind. If (for some reason) you need more than 8 layers,
    subsequent layers' colors are chosen randomly and no guarantees are made about legibility.
    :param drawings: A list of MultiLineStrings, one per layer to be drawn
    :param width: The width of the page (in inches)
    :param height: The height of the page (in inches)
    :param dpi: How large would you like the preview shown in screen pixels per plotter-inch
    :return:
    """
    pygame.init()
    win = pygame.display.set_mode((int(dpi * width), int(dpi * height)))
    rng = np.random.default_rng()
    my_colors = COLORS + [_random_color(rng) for _ in range(len(layers) - len(COLORS))]
    run = True
    first_run = True
    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        if not first_run:
            continue
        win.fill(bg_color)
        for i, layer in enumerate(layers):
            color = my_colors[i]
            path: shapely.LineString
            for path in shapely.get_parts(layer):
                screen_coords = [(dpi * x, dpi * (height - y)) for x, y in path.coords]
                pygame.draw.lines(win, color, False, screen_coords)
        pygame.display.flip()
        first_run = False
    pygame.quit()
