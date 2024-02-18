from typing import Optional
import warnings

import shapely

import elkplot


class AxidrawNotFoundError(IOError):
    ...


class DrawingOutOfBoundsError(Exception):
    ...


@elkplot.UNITS.wraps(
    None, (None, "inch", "inch", None, None, None, None, None, None), False
)
def draw(
    drawing: shapely.Geometry | list[shapely.Geometry],
    width: float = elkplot.sizes.A3[0],
    height: float = elkplot.sizes.A3[1],
    layer_labels: Optional[list[str]] = None,
    preview: bool = True,
    preview_dpi: float = 64,
    plot: bool = True,
    retrace: int = 1,
    device: Optional[elkplot.Device] = None,
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
    if isinstance(drawing, shapely.GeometryCollection):
        layers = [
            elkplot.flatten_geometry(layer) for layer in shapely.get_parts(drawing)
        ]
    elif isinstance(drawing, list):
        layers = [elkplot.flatten_geometry(layer) for layer in drawing]
    else:
        layers = [elkplot.flatten_geometry(drawing)]
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
        elkplot.render(layers, width, height, preview_dpi)
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
    if not elkplot.device.axidraw_available():
        raise AxidrawNotFoundError()
    device = elkplot.Device() if device is None else device
    device.zero_position()
    device.enable_motors()
    for layer, label in zip(layers, layer_labels):
        input(f"Press enter when you're ready to draw {label}")
        for _ in range(retrace):
            device.run_layer(layer, label)
    device.disable_motors()
