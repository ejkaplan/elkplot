import platform
from typing import Optional

import shapely
import winsound

from elkplot.device import Device, _axidraw_available
from elkplot import render, _geom_to_multilinestring, sizes


class AxidrawNotFoundError(IOError):
    ...


def draw(
    drawing: shapely.Geometry | list[shapely.Geometry],
    preview: bool = True,
    paper_size: tuple[float, float] = sizes.A3,
    preview_dpi: float = 128,
    layer_labels: Optional[list[str]] = None,
    pen: str = "DEFAULT",
    device: Optional[Device] = None,
    plot: bool = True,
    beep: bool = True
) -> None:
    """
    Sends a shapely geometry to the plotter for plotting. Can also render a preview to the screen ahead of plotting.
    If given a multi-layered plot, user will be prompted to press enter between layers to give time to change pens.
    May fail if the computer falls asleep between layers, so set your power settings accordingly.
    :param drawing: Shapely geometry to draw. If this is a list of geometries, each element will be treated as a
    separate layer. If this is a GeometryCollection, each part will be treated as a separate layer. All other geometries
    will be plotted as a single layer.
    :param preview: Should a preview of the plot be rendered to the screen before plotting begins?
    :param paper_size: Size of the paper as a tuple of the form (inches wide, inches high). Defaults to A3 paper size
    :param preview_dpi: Preview render size in DPI (screen-pixels per plot-inch)
    :param layer_labels: Optional labels for each layer, announced while operator is swapping pens
    :param pen: Which pen configuration to use for drawing. Use the CLI to configure pen lift and speed settings
    :param device: Which connected axidraw to use. If no input provided, it'll figure it out on its own
    :param plot: Should the drawing be plotted?
    :param beep: Should the computer beep to alert you to change pens? Only works on windows.
    :return:
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
        render(layers, *paper_size, preview_dpi)
    if not plot:
        return
    if not _axidraw_available():
        raise AxidrawNotFoundError()
    device = Device(pen) if device is None else device
    device.enable_motors()
    for layer, label in zip(layers, layer_labels):
        if beep and platform.system() == 'Windows':
            winsound.Beep(1000, 500)
        input(f"Press enter when you're ready to draw {label}")
        device.run_layer(layer, label)
    device.disable_motors()
