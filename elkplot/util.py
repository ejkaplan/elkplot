from typing import Optional

import shapely

from elkplot.device import Device, axidraw_available
from elkplot import render, geom_to_multilinestring, sizes


def draw(
    drawing: shapely.Geometry,
    preview: bool = True,
    preview_size: tuple[float, float] = sizes.A3,
    preview_dpi: float = 128,
    layer_labels: Optional[list[str]] = None,
    device: Optional[Device] = None,
) -> None:
    if isinstance(drawing, shapely.GeometryCollection):
        layers = [
            geom_to_multilinestring(layer) for layer in shapely.get_parts(drawing)
        ]
    else:
        layers = [geom_to_multilinestring(drawing)]
    if layer_labels is None:
        layer_labels = [f"Layer #{i}" for i in range(len(layers))]
    else:
        assert len(layer_labels) == len(layers)
    if preview:
        render(layers, *preview_size, preview_dpi)
    if not axidraw_available():
        return
    device = Device() if device is None else device
    device.enable_motors()
    for layer, label in zip(layers, layer_labels):
        input(f"Press enter when you're ready to draw {label}")
        device.run_layer(layer, label)
    device.disable_motors()
