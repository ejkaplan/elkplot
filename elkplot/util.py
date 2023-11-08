from typing import Optional

import shapely
from tqdm import tqdm
from elkplot import sizes, device
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # We only need this for the type hint, and otherwise we get a circular import.
    from elkplot.drawing import Drawing

from .renderer import render


class AxidrawNotFoundError(IOError):
    ...

class DrawingOutOfBoundsError(Exception):
    ...

def draw(
    drawing: "Drawing",
    width: float = sizes.A3[0],
    height: float = sizes.A3[1],
    layer_labels: Optional[list[str]] = None,
    preview: bool = True,
    preview_dpi: float = 128,
    plot: bool = True,
    retrace: int = 1,
    axidraw: Optional[device.Device] = None,
) -> None:
    """
    Visualize and/or plot a given drawing. Automatically pauses the plotter between layers to allow for changing pens.
    Geometry can be given as a GeometryCollection (which will be treated as a multi-pen drawing), a list of geometries
    (in which case again, each will be treated as a separate pen), or any other shapely Geometry (which will be treated
    as a single layer.

    Args:
        drawing: The shapely geometry to plot.
        width: The width of the page in inches (or any other unit if you pass in a `pint.Quantity`.) Used only for the
            preview.
        height: The height of the page in inches (or any other unit if you pass in a `pint.Quantity`.) Used only for the
            preview.
        layer_labels: An ordered list of labels for each pen-layer. Used only to remind you what pen you should use when
            swapping pens between layers. If excluded, layers will just be numbered.
        preview: Should an on-screen preview of the plot be displayed?
        preview_dpi: How big should the preview be? (Enter the DPI of your monitor to get an actual-size preview.)
        plot: Should the AxiDraw actually plot this? (If `preview` is `True`, plotting will only begin after the preview
            window is closed.)
        retrace: How many times should the AxiDraw draw each line? If this is set to 2, it will draw a whole layer, then
            draw that layer a second time, then either finish or prompt you to change pens.
        device: The AxiDraw config to which the plot should be sent. If excluded, a `Device` with all default settings
            will be used.
    """
    xmin, ymin, xmax, ymax = drawing.bounds
    if xmin < 0 or ymin < 0 or xmax > width or ymax > height:
        raise DrawingOutOfBoundsError("Drawing extends outside the plottable area!")
    layers = [flatten_geometry(layer) for layer in drawing]
    if layer_labels is None:
        layer_labels = [f"Layer #{i}" for i in range(len(layers))]
    else:
        assert len(layer_labels) == len(layers)
    if preview:
        render(layers, width, height, preview_dpi)
    if not plot:
        return
    if not device.axidraw_available():
        raise AxidrawNotFoundError()
    axidraw = device.Device() if axidraw is None else axidraw
    axidraw.zero_position()
    axidraw.enable_motors()
    bar = tqdm(total=drawing.up_length + drawing.down_length)
    for layer, label in zip(layers, layer_labels):
        bar.set_description(f"Drawing Layer {label}")
        input(f"Press enter when you're ready to draw {label}")
        for _ in range(retrace):
            axidraw.run_layer(layer, label, bar)
    bar.close()
    axidraw.disable_motors()


def flatten_geometry(geom: shapely.Geometry) -> shapely.MultiLineString:
    """
    Given any arbitrary shapely Geometry, flattens it down to a single MultiLineString that will be rendered as a
    single color-pass if sent to the plotter. Also converts Polygons to their outlines - if you want to render a filled
    in Polygon, use the `shade` function.
    Args:
        geom: The geometry to be flattened down. Most often this will be a GeometryCollection or a MultiPolygon.

    Returns:
        The flattened geometry
    """
    if isinstance(geom, shapely.MultiLineString):
        return geom
    if isinstance(geom, (shapely.LineString, shapely.LinearRing)):
        return shapely.multilinestrings([geom])
    elif isinstance(geom, shapely.Polygon):
        shapes = [geom.exterior] + list(geom.interiors)
        return shapely.union_all([flatten_geometry(shape) for shape in shapes])
    elif isinstance(geom, (shapely.GeometryCollection, shapely.MultiPolygon)):
        parts = [flatten_geometry(sub_geom) for sub_geom in shapely.get_parts(geom)]
        return shapely.union_all(parts)
    return shapely.MultiLineString()
