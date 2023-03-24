from typing import Optional

import shapely

import elkplot
from elkplot import render, _geom_to_multilinestring, sizes, UNITS
from elkplot.device import Device, _axidraw_available


class AxidrawNotFoundError(IOError):
    ...


@UNITS.wraps(None, (None, "inch", "inch", None, None, None, None, None, None), False)
def draw(
    drawing: shapely.Geometry | list[shapely.Geometry],
    width: float = sizes.A3[0],
    height: float = sizes.A3[1],
    layer_labels: Optional[list[str]] = None,
    pen: str = "DEFAULT",
    preview: bool = True,
    preview_dpi: float = 128,
    plot: bool = True,
    device: Optional[Device] = None,
) -> None:
    """
    Sends a shapely geometry to the plotter for plotting. Can also render a preview to the screen ahead of plotting.
    If given a multi-layered plot, user will be prompted to press enter between layers to give time to change pens.
    May fail if the computer falls asleep between layers, so set your power settings accordingly.
    :param drawing: Shapely geometry to draw. If this is a list of geometries, each element will be treated as a
    separate layer. If this is a GeometryCollection, each part will be treated as a separate layer. All other geometries
    will be plotted as a single layer.
    :param width: page width in inches
    :param height: page height in inches
    :param layer_labels: Optional labels for each layer, announced while operator is swapping pens
    :param pen: Which pen configuration to use for drawing. Use the CLI to configure pen lift and speed settings
    :param preview: Should a preview of the plot be rendered to the screen before plotting begins?
    :param preview_dpi: Preview render size in DPI (screen-pixels per plot-inch)
    :param plot: Should the drawing be plotted?
    :param device: Which connected axidraw to use. If no input provided, it'll figure it out on its own
    """
    if isinstance(drawing, shapely.GeometryCollection):
        layers = [
            _geom_to_multilinestring(layer) for layer in shapely.get_parts(drawing)
        ]
    elif isinstance(drawing, list):
        layers = [_geom_to_multilinestring(layer) for layer in drawing]
    else:
        layers = [_geom_to_multilinestring(drawing)]
    if layer_labels is None:
        layer_labels = [f"Layer #{i}" for i in range(len(layers))]
    else:
        assert len(layer_labels) == len(layers)
    if preview:
        render(layers, width, height, preview_dpi)
    if not plot:
        return
    if not _axidraw_available():
        raise AxidrawNotFoundError()
    device = Device(pen) if device is None else device
    device.enable_motors()
    for layer, label in zip(layers, layer_labels):
        input(f"Press enter when you're ready to draw {label}")
        device.run_layer(layer, label)
    device.disable_motors()
