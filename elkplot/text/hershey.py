from __future__ import division

import itertools
from string import printable

import shapely
import shapely.affinity as affinity

from elkplot.shape_utils import size
from .hershey_fonts import *

# Taken with modifications from https://github.com/fogleman/axi

HersheyFont = list[tuple[float, float, list[list[tuple[float, float]]]]]


def text(
    string: str, font: HersheyFont = FUTURAL, spacing: float = 0, extra: float = 0
) -> shapely.MultiLineString:
    results = []
    x = 0
    for ch in string:
        index = ord(ch) - 32
        if index < 0 or index >= 96:
            x += spacing
            continue
        lt, rt, coords = font[index]
        for path in coords:
            path = [(x + i - lt, j) for i, j in path]
            if path:
                results.append(shapely.linestrings(path))
        x += rt - lt + spacing
        if index == 0:
            x += extra
    return shapely.union_all(results)


def word_wrap(string: str, width: float, measure_func) -> list[str]:
    result = []
    for line in string.split("\n"):
        fields = itertools.groupby(line, lambda x: x.isspace())
        fields = ["".join(g) for _, g in fields]
        if len(fields) % 2 == 1:
            fields.append("")
        x = ""
        for a, b in zip(fields[::2], fields[1::2]):
            w, _ = measure_func(x + a)
            if w > width:
                if x == "":
                    result.append(a)
                    continue
                else:
                    result.append(x)
                    x = ""
            x += a + b
        if x != "":
            result.append(x)
    result = [x.strip() for x in result]
    return result


class Font:
    def __init__(self, font: HersheyFont, point_size: float):
        self.font = font
        self.max_height = size(text(printable, font))[1]
        self.scale = ((point_size / 72) / self.max_height).magnitude

    def text(self, string: str) -> shapely.MultiLineString:
        t = text(string, self.font)
        t = affinity.scale(t, self.scale, self.scale, origin=(0, 0))
        return t

    def justify_text(self, string: str, width: float) -> shapely.MultiLineString:
        t = self.text(string)
        w, h = size(t)
        spaces = string.count(" ")
        if spaces == 0 or w >= width:
            return t
        e = ((width - w) / spaces) / self.scale
        t = text(string, self.font, extra=e)
        t = affinity.scale(t, self.scale, self.scale, origin=(0, 0))
        t = t.scale(self.scale)
        return t

    def measure(self, string: str):
        t = self.text(string)
        return size(t)

    def wrap(
        self,
        string: str,
        width: float,
        line_spacing: float = 1,
        align: float = 0,
        justify: bool = False,
    ) -> shapely.MultiLineString:
        lines = word_wrap(string, width, self.measure)
        line_shapes = [self.text(line) for line in lines]
        max_width = max(size(t)[0] for t in line_shapes)
        if justify:
            jds = [self.justify_text(line, max_width) for line in lines]
            line_shapes = jds[:-1] + [line_shapes[-1]]
        spacing = line_spacing * self.max_height * self.scale
        result = shapely.MultiLineString()
        y = 0
        for line_shape in line_shapes:
            w, h = size(line_shape)
            if align == 0:
                x = 0
            elif align == 1:
                x = max_width - w
            else:
                x = max_width / 2 - w / 2
            line_shape = affinity.translate(line_shape, x, y)
            result = result.union(line_shape)
            y += spacing
        return result
