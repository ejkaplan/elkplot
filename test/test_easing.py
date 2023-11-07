import inspect
from typing import Callable

import numpy as np
import numpy.typing as npt
import plotly.graph_objects as go
import pytest
from plotly.subplots import make_subplots

import elkplot.easing
from test import config


@pytest.fixture
def easing_functions() -> list[tuple[str, Callable[[npt.ArrayLike], npt.ArrayLike]]]:
    return [f for f in vars(elkplot.easing).items() if inspect.isfunction(f[1])]


@pytest.mark.skipif(config.SKIP_RENDER_TESTS, reason="skipping rendering tests")
def test_easing(
    easing_functions: list[tuple[str, Callable[[npt.ArrayLike], npt.ArrayLike]]]
):
    names, easing_functions = zip(*easing_functions)
    cols = 6  # int(np.ceil(np.sqrt(len(easing_functions))))
    rows = int(np.ceil(len(easing_functions) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=names)

    x = np.linspace(0, 1, 100)

    for i, func in enumerate(easing_functions):
        r = int(i // cols) + 1
        c = int(i % cols) + 1
        fig.add_trace(go.Scatter(x=x, y=func(x), showlegend=False), row=r, col=c)
    fig.show()
