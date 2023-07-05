ElkPlot assumes that you are creating your plotter art using the [Shapely](https://shapely.readthedocs.io/en/stable/manual.html) Python library. This documentation assumes that you are already comfortable/familiar with Shapely. ElkPlot primarily deals with `LineString`, `MultiLineString`, and `GeometryCollection`, so you should try to compose your art in terms of these types.

- A `LineString` will be plotted as a single stroke of the pen - the plotter will go to the first coordinate in the `LineString`, put the pen down, and then travel to each subsequent coordinate until it reaches the end of the `LineString` at which point the pen will be lifted again. (A `LinearRing` will be plotted as though it were a LineString with the first coordinate duplicated at the end.)
- A `MultiLineString` will be plotted as multiple discrete strokes. The plotter draws each `LineString` contained within in the order that they are given, lifting the pen between each `LineString` in order to travel to the next.
- A `GeometryCollection` will be treated as multiple passes with multiple pens. If you have a drawing that uses two colors, you should compose a `MultiLineString` containing all the lines to be drawn in the first color, and a second `MultiLineString` containing all the lines to be drawn in the second color. Then create a `GeometryCollection` containing both.

```Python
import shapely

first_color = shapely.MultiLineString([...])
second_color = shapely.MultiLineString([...])
drawing = shapely.GeometryCollection([first_color, second_color])
```

## Helpful Functions for Creating Plottable Shapely Geometry

The following functions can be imported directly from _elkplot_ and help manipulate Shapely geometry in specific ways that are useful for plotting.

::: elkplot.shape_utils
            