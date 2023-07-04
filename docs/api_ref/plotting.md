## Plotting and Previewing

Most of the time, plotting is as simple as sending an appropriate shapely object to the `draw` function. See [Making Art](making_art.md) for more on how to create appropriate shapely geometry, but you are *strongly* encouraged to call `scale_to_fit()` and `optimize()` before plotting to make sure that your plot is the correct size for your page and the lines will be drawn in an order that doesn't waste a bunch of time with the pen in the air.

::: elkplot.util
    options:
        members:
            - draw

## Managing the AxiDraw

::: elkplot.device
    options:
        members:
            - Device