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
    layer_colors: Optional[list[tuple[int, int, int]]] = None,
) -> None:
    pygame.init()
    win = pygame.display.set_mode((int(dpi * width), int(dpi * height)))
    rng = np.random.default_rng()
    if layer_colors is not None:
        my_colors = layer_colors + [_random_color(rng) for _ in range(len(layers) - len(layer_colors))]
    else:
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
                pygame.draw.aalines(win, color, False, screen_coords)
        pygame.display.flip()
        first_run = False
    pygame.quit()
