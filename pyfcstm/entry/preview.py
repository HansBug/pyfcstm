"""
``pyfcstm preview`` subcommand.

Renders a FCSTM DSL document to SVG or PNG using the embedded jsfcstm
+ elkjs + resvg-wasm pipeline. Output format is selected from the file
extension supplied via ``-o``.

Distinct from the existing :mod:`pyfcstm.entry.visualize` subcommand,
which delegates to PlantUML through ``plantumlcli`` and emits stylised
PlantUML diagrams. ``preview`` instead reproduces the same diagram the
VSCode FCSTM extension shows in its preview pane — ELK-laid hierarchical
state diagram with the jsfcstm palette.
"""
from __future__ import annotations

import pathlib
from typing import Optional, Tuple

import click

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..utils import auto_decode

_PREVIEW_EXTENSIONS = {'.svg', '.png'}


def _format_for_output(output_path: pathlib.Path) -> str:
    """
    Pick the renderer format from the output file's extension.

    :param output_path: Output file path.
    :type output_path: pathlib.Path
    :return: ``'svg'`` or ``'png'``.
    :rtype: str
    :raises pyfcstm.entry.base.ClickErrorException: If the extension is
        anything other than ``.svg`` / ``.png``.
    """
    suffix = output_path.suffix.lower()
    if suffix not in _PREVIEW_EXTENSIONS:
        raise ClickErrorException(
            f'Output file must end in .svg or .png, got {output_path.suffix!r}. '
            f'PDF support is tracked separately — see the visualisation issue.'
        )
    return suffix.lstrip('.')


def _parse_kv_pairs(raw_pairs: Tuple[str, ...]) -> dict:
    """
    Convert ``--option key=value`` flags into a jsfcstm options dict.

    Values are interpreted as JSON when possible (so ``true`` → ``True``,
    ``["name","relpath"]`` → list, etc.). Anything that doesn't parse as
    JSON is kept as a plain string.
    """
    import json
    out: dict = {}
    for raw in raw_pairs:
        if '=' not in raw:
            raise ClickErrorException(
                f'Invalid --option value {raw!r}; expected key=value form.'
            )
        key, _, value = raw.partition('=')
        key = key.strip()
        if not key:
            raise ClickErrorException(
                f'Invalid --option value {raw!r}; key is empty.'
            )
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            parsed = value
        out[key] = parsed
    return out


def _build_options(
    direction: Optional[str],
    detail_level: Optional[str],
    extra_options: Tuple[str, ...],
) -> Optional[dict]:
    """Compose a jsfcstm options dict from the explicit CLI flags."""
    opts: dict = {}
    if direction:
        opts['direction'] = direction
    if detail_level:
        opts['detailLevel'] = detail_level
    opts.update(_parse_kv_pairs(extra_options))
    return opts or None


def _add_preview_subcommand(cli: click.Group) -> click.Group:
    """
    Attach the ``preview`` subcommand to a Click CLI group.

    :param cli: The Click group to extend.
    :type cli: click.Group
    :return: The mutated Click group.
    :rtype: click.Group
    """

    @cli.command(
        'preview',
        help='Render a FCSTM DSL file to SVG or PNG using the embedded '
             'jsfcstm + elkjs + resvg pipeline.',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i', '--input', 'input_code_file',
        type=click.Path(exists=True, dir_okay=False, readable=True),
        required=True,
        help='Input FCSTM DSL file.',
    )
    @click.option(
        '-o', '--output', 'output_file',
        type=click.Path(dir_okay=False, writable=True),
        required=True,
        help='Output file path. Format is chosen from the suffix '
             '(.svg or .png).',
    )
    @click.option(
        '-s', '--scale', 'scale',
        type=float, default=2.0, show_default=True,
        help='Raster scale factor (PNG only). 2.0 matches the VSCode '
             'extension Export PNG output.',
    )
    @click.option(
        '-d', '--direction', 'direction',
        type=click.Choice(['UP', 'DOWN', 'LEFT', 'RIGHT',
                           'TB', 'BT', 'LR', 'RL']),
        default=None,
        help='ELK layout direction.',
    )
    @click.option(
        '-l', '--level', 'detail_level',
        type=click.Choice(['minimal', 'normal', 'full']),
        default=None,
        help='Detail-level preset (controls per-state event/action chips).',
    )
    @click.option(
        '--option', 'extra_options',
        multiple=True,
        help='Pass-through jsfcstm option in key=value form. Values are '
             'parsed as JSON when possible. May be repeated.',
    )
    def preview(
        input_code_file: str,
        output_file: str,
        scale: float,
        direction: Optional[str],
        detail_level: Optional[str],
        extra_options: Tuple[str, ...],
    ) -> None:
        """
        Render and write a FCSTM diagram to disk.

        Imports of :mod:`pyfcstm.visualize` happen inside the callback so
        the ``preview`` command can be discovered by ``--help`` even when
        the ``viz`` extras are not installed.
        """
        try:
            from ..visualize import render_png, render_svg
            from ..jsruntime import JsEngineError, JsEngineUnavailableError
        except ImportError as exc:  # pragma: no cover - import guard
            raise ClickErrorException(
                f'pyfcstm.visualize is unavailable: {exc}. '
                f'Install the visualization extras: pip install pyfcstm[viz]'
            )

        out_path = pathlib.Path(output_file)
        fmt = _format_for_output(out_path)

        with open(input_code_file, 'rb') as fh:
            dsl_text = auto_decode(fh.read())

        options = _build_options(direction, detail_level, extra_options)

        try:
            if fmt == 'svg':
                payload: bytes = render_svg(dsl_text, options).encode('utf-8')
            else:
                payload = render_png(dsl_text, options, scale=scale)
        except JsEngineUnavailableError as exc:
            raise ClickErrorException(str(exc))
        except JsEngineError as exc:
            raise ClickErrorException(f'Render pipeline failed: {exc}')

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(payload)
        click.echo(f'Wrote {fmt.upper()} ({len(payload)} bytes) to {out_path}')

    return cli
