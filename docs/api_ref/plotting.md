# Plotting and Previewing

Most of the time, plotting is as simple as sending an appropriate shapely object to the `draw` function. See [Making Art](making_art.md) for more on how to create appropriate shapely geometry, but you are *strongly* encouraged to call `scale_to_fit()` and `optimize()` before plotting to make sure that your plot is the correct size for your page and the lines will be drawn in an order that doesn't waste a bunch of time with the pen in the air.

::: elkplot.util
    options:
        members:
            - draw

## Managing the AxiDraw

The `draw` function above takes an optional Device as input. The device contains all the settings for how the AxiDraw
actually goes about the business of plotting. This code was largely borrowed from [the axi python library](https://github.com/fogleman/axi) by Michael Fogleman. Generally speaking, I only pass Device objects to the draw function, but it also contains functions for directly controlling the AxiDraw.

A common use case is slowing down the AxiDraw for pens that don't leave behind enough ink at the current speed. That would look something like this:

```python
import shapely
import elkplot

drawing = shapely.MultiLineString([...])
device = elkplot.Device(max_velocity=2)
elkplot.draw(drawing, device=device)
```

::: elkplot.device
    options:
        members:
            - Device