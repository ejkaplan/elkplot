from __future__ import annotations

from dataclasses import dataclass
import dataclasses
import shapely
import numpy as np

DEG_TO_RAD = np.pi / 180
RAD_TO_DEG = 180 / np.pi


@dataclass(frozen=True)
class TurtleState:
    position: shapely.Point
    heading: float
    pen_down: bool


class TurtleCheckpoint:
    def __init__(self, turtle: Turtle) -> None:
        self.turtle = turtle

    def __enter__(self) -> None:
        self.turtle.push()

    def __exit__(self, *args) -> None:
        self.turtle.pop()


class Turtle:
    def __init__(
        self, x: float = 0, y: float = 0, heading: float = 0, use_degrees=False
    ) -> None:
        """Create a new turtle!

        Args:
            x (float, optional): x-coordinate of the turtle's starting position. Defaults to 0.
            y (float, optional): y-coordinate of the turtle's starting position. Defaults to 0.
            heading (float, optional): Direction the turtle is pointing. Defaults to 0.
            use_degrees (bool, optional): Should angles be given in radians or degrees? Defaults to False.
        """
        self._state = TurtleState(shapely.Point(x, y), heading, True)
        self._stack: list[TurtleState] = []
        self._current_line: list[shapely.Point] = [self.position]
        self._lines: list[shapely.LineString] = []
        self._use_degrees = use_degrees

    @property
    def heading(self) -> float:
        """
        Returns:
            float: Which way is the turtle facing?
        """
        if self._use_degrees:
            return self._state.heading * RAD_TO_DEG
        return self._state.heading

    @property
    def heading_rad(self) -> float:
        return self._state.heading

    @property
    def position(self) -> shapely.Point:
        """
        Returns:
            shapely.Point: Where is the turtle right now?
        """
        return self._state.position

    @property
    def x(self) -> float:
        """
        Returns:
            float: The turtle's x-coordinate
        """
        return self._state.position.x

    @property
    def y(self) -> float:
        """
        Returns:
            float: The turtle's y-coordinate
        """
        return self._state.position.y

    @property
    def pen_down(self) -> bool:
        """
        Returns:
            bool: Is the turtle drawing currently
        """
        return self._state.pen_down

    def forward(self, distance: float) -> Turtle:
        """Move the turtle forward by some distance. You can also move the turtle
        backwards by calling this function with a negative input

        Args:
            distance (float): The distance to move forward

        Returns:
            Turtle: Return self so that commands can be chained
        """
        dx, dy = distance * np.cos(self.heading_rad), distance * np.sin(
            self.heading_rad
        )
        return self.goto(self.x + dx, self.y + dy)

    def backward(self, distance: float) -> Turtle:
        """Move the turtle backward by some distance.

        Args:
            distance (float): The distance to move backward

        Returns:
            Turtle: Return self so that commands can be chained
        """
        return self.forward(-distance)

    def turn(self, angle: float) -> Turtle:
        """Rotate clockwise by some angle. To rotate counterclockwise, pass a negative angle.

        Args:
            angle (float): The angle by which to rotate

        Returns:
            Turtle: Return self so that commands can be chained
        """
        return self.turn_right(angle)

    def turn_right(self, angle: float) -> Turtle:
        """Rotate clockwise by some angle. (This is an alias for turn)

        Args:
            angle (float): The angle by which to rotate

        Returns:
            Turtle: Return self so that commands can be chained
        """
        new_heading = self.heading_rad + angle * (
            DEG_TO_RAD if self._use_degrees else 1
        )
        self._state = dataclasses.replace(self._state, heading=new_heading)
        return self

    def turn_left(self, angle: float) -> Turtle:
        """Rotate anti-clockwise by some angle.

        Args:
            angle (float): The angle by which to rotate

        Returns:
            Turtle: Return self so that commands can be chained
        """
        return self.turn_right(-angle)
    
    def set_heading(self, angle: float) -> Turtle:
        """
        Turns the turtle in place to directly face a particular direction

        Args:
            angle (float): The new heading, where 0 is facing right.

        Returns:
            Turtle: Return self so that commands can be chained.
        """
        new_heading = angle * (
            DEG_TO_RAD if self._use_degrees else 1
        )
        self._state = dataclasses.replace(self._state, heading=new_heading)
        return self

    def goto(self, x: float, y: float) -> Turtle:
        """Move the turtle directly to a given coordinate

        Args:
            x (float): The x-coordinate of the point to which to go
            y (float): The y-coordinate of the point to which to go

        Returns:
            Turtle: Return self so that commands can be chained
        """
        new_pos = shapely.Point(x, y)
        if self.pen_down:
            self._current_line.append(new_pos)
        self._state = dataclasses.replace(self._state, position=new_pos)
        return self

    def raise_pen(self) -> Turtle:
        """Lift the pen so that lines are not created when the turtle moves

        Returns:
            Turtle: Return self so that commands can be chained
        """
        if len(self._current_line) > 1:
            self._lines.append(shapely.LineString(self._current_line))
        self._current_line = [self.position]
        self._state = dataclasses.replace(self._state, pen_down=False)
        return self

    def lower_pen(self) -> Turtle:
        """Lower the pen so that lines are created when the turtle moves

        Returns:
            Turtle: Return self so that commands can be chained
        """
        self._current_line = [self.position]
        self._state = dataclasses.replace(self._state, pen_down=True)
        return self

    def push(self) -> Turtle:
        """Push the turtle's current state (position & angle) onto a stack
        so that the turtle can revert to that position later

        Returns:
            Turtle: Return self so that commands can be chained
        """
        self._stack.append(self._state)
        return self

    def pop(self) -> Turtle:
        """Pop the top state from the stack and revert the turtle to that state.
        New lines are not created by the turtle jumping back to this old state.

        Returns:
            Turtle: Return self so that commands can be chained
        """
        self.raise_pen()
        self._state = self._stack.pop()
        if self.pen_down:
            self._current_line = [self.position]
        return self

    def drawing(self) -> shapely.MultiLineString:
        """Turn the paths drawn by the turtle into a shapely geometry so that it
        can be further modified or plotted.

        Returns:
            shapely.MultiLineString: The MultiLineString composed from all the lines the turtle drew.
        """
        if self.pen_down:
            self.raise_pen()
            self.lower_pen()
        return shapely.MultiLineString(self._lines)

    def checkpoint(self) -> TurtleCheckpoint:
        """Allows for pushing and popping as part of a context using the `with` keyword."""
        return TurtleCheckpoint(self)
