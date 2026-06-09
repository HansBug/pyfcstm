"""
Top-level Python renderers for FCSTM state machines.

The pipeline lives in JavaScript (see :mod:`pyfcstm.jsruntime`); this
module is a thin Python facade so callers never have to reach into
``__fcstm_export`` themselves.

Public API:

* :func:`render_svg` — DSL text → SVG ``str``
* :func:`render_png` — DSL text → PNG ``bytes``
"""
from typing import Optional, Union

from ..jsruntime import get_engine
from .options import VisualizeOptions

__all__ = ['render_svg', 'render_png']

_OptionsArg = Optional[Union[VisualizeOptions, dict]]


def _resolve_options(options: _OptionsArg) -> Optional[dict]:
    if options is None:
        return None
    if isinstance(options, VisualizeOptions):
        return options.to_jsfcstm_dict()
    if isinstance(options, dict):
        return options
    raise TypeError(
        f'options must be VisualizeOptions, dict, or None, '
        f'got {type(options).__name__}'
    )


def render_svg(dsl_text: str, options: _OptionsArg = None) -> str:
    """
    Render a FCSTM DSL document to a complete SVG string.

    The output matches the SVG that the VSCode preview's webview
    receives from jsfcstm — same ELK layout, same palette, same
    ``data-fcstm-*`` attributes for downstream tooling.

    :param dsl_text: The DSL source as text.
    :param options: Optional :class:`VisualizeOptions` (or a raw dict
        in jsfcstm's camelCase shape) controlling layout direction,
        detail level, etc.
    :return: A standalone ``<svg>...</svg>`` document.
    :raises pyfcstm.jsruntime.JsEngineError: If the DSL fails to parse
        or jsfcstm reports a pipeline error.

    Example::

        >>> from pyfcstm.visualize import render_svg
        >>> svg = render_svg(open('machine.fcstm').read())
        >>> svg.startswith('<svg')
        True
    """
    raw = get_engine().export('svg', dsl_text, _resolve_options(options), 1.0)
    return raw.decode('utf-8')


def render_png(dsl_text: str, options: _OptionsArg = None,
               scale: float = 2.0) -> bytes:
    """
    Render a FCSTM DSL document to PNG bytes.

    The diagram is laid out exactly as in :func:`render_svg`, then
    rasterised in-process by ``@resvg/resvg-wasm``. Glyphs are drawn
    using a bundled JetBrains Mono Regular face so the output is byte-
    identical across platforms regardless of installed system fonts.

    :param dsl_text: The DSL source as text.
    :param options: Optional :class:`VisualizeOptions` (or a raw dict
        in jsfcstm's camelCase shape) controlling layout direction,
        detail level, etc.
    :param scale: Output scale factor; ``2.0`` (the default) doubles
        the natural SVG size, matching what the VSCode "Export PNG"
        button produces. ``1.0`` gives the natural pixel size.
    :return: PNG file bytes.
    :raises pyfcstm.jsruntime.JsEngineError: If the DSL fails to parse
        or jsfcstm / resvg reports a pipeline error.

    Example::

        >>> from pyfcstm.visualize import render_png
        >>> png = render_png(open('machine.fcstm').read(), scale=2.0)
        >>> open('machine.png', 'wb').write(png)
    """
    if scale <= 0:
        raise ValueError(f'scale must be positive, got {scale!r}')
    return get_engine().export('png', dsl_text, _resolve_options(options),
                               float(scale))
