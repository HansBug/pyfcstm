"""
Top-level entry point for FCSTM diagram rendering.

Pulls together :class:`VisualizeOptions` and the :func:`render_svg` /
:func:`render_png` helpers so callers can do::

    from pyfcstm.visualize import render_svg, render_png, VisualizeOptions
"""
from .options import (
    DetailLevel,
    Direction,
    EventNameFormatPart,
    EventVisualizationMode,
    TransitionEffectMode,
    VisualizeOptions,
)
from .render import render_png, render_svg

__all__ = [
    'DetailLevel',
    'Direction',
    'EventNameFormatPart',
    'EventVisualizationMode',
    'TransitionEffectMode',
    'VisualizeOptions',
    'render_png',
    'render_svg',
]
