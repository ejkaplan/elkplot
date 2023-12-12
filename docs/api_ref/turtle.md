# Turtle Graphics 🐢

## Explanation & Example

ElkPlot includes a recreation of [Logo's](https://en.wikipedia.org/wiki/Logo_(programming_language)) turtle graphics. This is intended as a quick and easy way for learners to start making art without having to go too deep on the Python programming language. (Yet)

Getting started is super easy - just make a turtle and give it some instructions. You can name your turtle whatever you like - I decided to name mine [Gamera](https://en.wikipedia.org/wiki/Gamera).

```python
import elkplot

def main():
    w, h = elkplot.sizes.LETTER

    # the turtle starts at (0, 0) facing right
    gamera = elkplot.Turtle(use_degrees=True)

    # draw the left eye
    gamera.turn_right(90)
    gamera.forward(2)
    gamera.raise_pen()

    # draw the right eye
    gamera.goto(2, 0)
    gamera.lower_pen()
    gamera.forward(2)
    gamera.raise_pen()

    # draw the mouth
    gamera.goto(-1.5, 2.5)
    gamera.lower_pen()
    gamera.turn_left(45)
    gamera.forward(1.5)
    gamera.turn_left(45)
    gamera.forward(3)
    gamera.turn_left(45)
    gamera.forward(1.5)

    # render the drawing, center it on a letter size sheet, and draw
    d = gamera.drawing() 
    d = elkplot.center(d, w, h)
    elkplot.draw(d, w, h, plot=False)


if __name__ == "__main__":
    main()

```

![Turtle Plot Preivew](turtle_preview.png)

## Checkpoint!

You can use a checkpoint context to return to your current position and rotation upon exiting the context. The following tree fractal uses checkpoints to return to the base of a branch once finishing drawing that branch.

```python
import elkplot


def tree(
    angle: float, length: float, shrink: float, depth: int, turtle: elkplot.Turtle
) -> None:
    if depth <= 0:
        return
    turtle.forward(length)
    with turtle.checkpoint():
        turtle.turn(-angle)
        tree(angle, shrink * length, shrink, depth - 1, turtle)
    with turtle.checkpoint():
        turtle.turn(angle)
        tree(angle, shrink * length, shrink, depth - 1, turtle)


def main():
    w, h, margin = 8, 8, 0.5
    turtle = elkplot.Turtle(use_degrees=True)
    turtle.turn_left(90)
    tree(20, 1, 0.8, 10, turtle)
    drawing = turtle.drawing()
    drawing = elkplot.scale_to_fit(drawing, w, h, margin)
    elkplot.draw(drawing, w, h, plot=False)


if __name__ == "__main__":
    main()

```

![Turtle Tree Fractal](turtle_tree_fractal.png)

## Full Reference

:::elkplot.turtle
