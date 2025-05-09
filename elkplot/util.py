from typing import Optional
import warnings

import shapely

from elkplot import sizes, Device, flatten_geometry, render
from elkplot.device import axidraw_available


class AxidrawNotFoundError(IOError): ...


class DrawingOutOfBoundsError(Exception): ...


def draw(
    drawing: shapely.Geometry | list[shapely.Geometry],
    width: float = sizes.A3[0],
    height: float = sizes.A3[1],
    layer_labels: Optional[list[str]] = None,
    preview: bool = True,
    preview_dpi: float = 64,
    plot: bool = True,
    retrace: int = 1,
    device: Optional[Device] = None,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    layer_colors: Optional[list[tuple[int, int, int]]] = None,
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
        bg_color: The color of the background on which the preview is rendered (r, g, b)
        layer_colors: A list of colors for each layer - good for previewing pen colors. Each color given as (r,g,b)
    """
    if isinstance(drawing, shapely.GeometryCollection):
        layers = [flatten_geometry(layer) for layer in shapely.get_parts(drawing)]
    elif isinstance(drawing, list):
        layers = [flatten_geometry(layer) for layer in drawing]
    else:
        layers = [flatten_geometry(drawing)]
    if layer_labels is None:
        layer_labels = [f"Layer #{i}" for i in range(len(layers))]
    else:
        assert len(layer_labels) == len(layers)

    min_x = min([layer.bounds[0] for layer in layers])
    min_y = min([layer.bounds[1] for layer in layers])
    max_x = max([layer.bounds[2] for layer in layers])
    max_y = max([layer.bounds[3] for layer in layers])
    out_of_bounds = min_x < 0 or min_y < 0 or max_x > width or max_y > height
    if out_of_bounds:
        warnings.warn("THIS DRAWING GOES OUT OF BOUNDS!")

    if preview:
        render(
            layers,
            width,
            height,
            preview_dpi,
            bg_color=bg_color,
            layer_colors=layer_colors,
        )
    if not plot:
        return
    min_x = min([layer.bounds[0] for layer in layers])
    min_y = min([layer.bounds[1] for layer in layers])
    max_x = max([layer.bounds[2] for layer in layers])
    max_y = max([layer.bounds[3] for layer in layers])
    if out_of_bounds:
        raise DrawingOutOfBoundsError(
            f"Drawing has bounds ({min_x}, {min_y}) to ({max_x}, {max_y}), which extends outside the plottable bounds (0, 0) to ({width}, {height})"
        )
    if not axidraw_available():
        raise AxidrawNotFoundError(
            "Unable to communicate with device. Is the USB cable plugged in?"
        )
    device = Device() if device is None else device
    if not device.powered_on():
        raise AxidrawNotFoundError(
            "Motors do not have power. Is the AxiDraw plugged in and turned on?"
        )
    device.zero_position()
    device.enable_motors()
    device.pen_up()
    for layer, label in zip(layers, layer_labels):
        input(f"Press enter when you're ready to draw {label}")
        for _ in range(retrace):
            device.run_layer(layer, label)
    device.disable_motors()
