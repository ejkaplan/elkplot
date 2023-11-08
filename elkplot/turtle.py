from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np
import shapely
from elkplot import sizes

from elkplot.drawing import Drawing


@dataclass(frozen=True)
class TurtleState:
    x: float = 0
    y: float = 0
    heading: float = 0
    pen_down: bool = True


class Turtle:
    def __init__(
        self, x: float = 0, y: float = 0, heading: float = 0, pen_down: bool = True
    ) -> None:
        self.state = TurtleState(x, y, heading, pen_down)
        self._current_path: list[shapely.Point] = [shapely.Point(x, y)]
        self._paths: list[shapely.LineString] = []
        self._stack: list[TurtleState] = []

    @property
    def x(self) -> float:
        return self.state.x

    @property
    def y(self) -> float:
        return self.state.y

    @property
    def heading(self) -> float:
        return self.state.heading

    @property
    def pen_down(self) -> bool:
        return self.state.pen_down

    def forward(self, dist: float) -> Turtle:
        new_x: float = self.x + dist * np.cos(self.heading)
        new_y: float = self.y + dist * np.sin(self.heading)
        return self.goto(new_x, new_y)

    def goto(self, x: float, y: float):
        if self.pen_down:
            self._current_path.append(shapely.Point(x, y))
        self.state = replace(self.state, x=x, y=y)
        return self

    def turn(self, angle: float) -> Turtle:
        self.state = replace(self.state, heading=self.heading + angle)
        return self

    def lower_pen(self) -> Turtle:
        self.state = replace(self.state, pen_down=True)
        return self

    def raise_pen(self) -> Turtle:
        if len(self._current_path) > 1:
            self._paths.append(shapely.LineString(self._current_path))
        self._current_path = [shapely.Point(self.x, self.y)]
        self.state = replace(self.state, pen_down=False)
        return self

    def push(self) -> Turtle:
        self._stack.append(self.state)
        return self

    def pop(self) -> Turtle:
        if self.pen_down:
            self.raise_pen()
        self.state = self._stack.pop()
        return self

    def drawing(self, width: float=sizes.A3[0], height: float=sizes.A3[1]) -> Drawing:
        paths = self._paths.copy()
        if self.pen_down and len(self._current_path) > 1:
            paths.append(shapely.LineString(self._current_path))
        lines = shapely.MultiLineString(paths)
        return Drawing(lines, width=width, height=height)
