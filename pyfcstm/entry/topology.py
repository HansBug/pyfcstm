"""
Top-level CLI entry for topological verification.

This module registers a ``topology`` Click group with three subcommands
mapping 1:1 to :mod:`pyfcstm.topology`:

* ``pyfcstm topology reach`` - section 3.4 reachability.
* ``pyfcstm topology finite`` - section 3.5 finiteness.
* ``pyfcstm topology inevitable`` - section 3.6 inevitability.

All three commands share the same machine-loading and output-formatting
plumbing. Exit codes:

* ``0`` - property holds.
* ``1`` - property violated (counterexample reported).
* ``2`` - usage / input error (e.g. unknown state path, malformed DSL).

The module contains:

* :func:`_add_topology_subcommand` - Decorator that mounts the
  ``topology`` group on the top-level CLI.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional

import click

from ..dsl import parse_with_grammar_entry
from ..model import State, StateMachine, parse_dsl_node_to_state_machine
from ..topology import (
    FinitenessResult,
    InevitabilityResult,
    ReachabilityResult,
    build_topology_graph,
    check_finiteness,
    check_inevitability,
    check_reachability,
    format_node,
)
from ..utils import auto_decode
from .base import CONTEXT_SETTINGS, ClickErrorException

__all__ = [
    "_add_topology_subcommand",
]


def _load_state_machine(input_code_file: str) -> StateMachine:
    """
    Load and parse one DSL file into a state machine model.

    :param input_code_file: Path to the input ``.fcstm`` file.
    :type input_code_file: str
    :return: Parsed state machine model.
    :rtype: StateMachine
    :raises pyfcstm.entry.base.ClickErrorException: If the input file
        cannot be read or parsed.
    """
    input_path = pathlib.Path(input_code_file)
    try:
        code = auto_decode(input_path.read_bytes())
    except FileNotFoundError:
        raise ClickErrorException("Input file {!r} not found".format(input_code_file))
    except OSError as err:
        raise ClickErrorException(
            "Failed to read input file {!r}: {}".format(input_code_file, err)
        )
    try:
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
    except Exception as err:  # pragma: no cover - error surface depends on parser
        raise ClickErrorException("Failed to parse DSL: {}".format(err))
    return parse_dsl_node_to_state_machine(ast_node)


def _resolve_state(state_machine: StateMachine, raw_path: str, option_name: str) -> State:
    """
    Resolve a dotted state path string to a :class:`State` object.

    :param state_machine: Parsed state machine.
    :type state_machine: StateMachine
    :param raw_path: Dotted path such as ``"Root.System.Active"``.
    :type raw_path: str
    :param option_name: CLI flag name used in error messages.
    :type option_name: str
    :return: Resolved :class:`State`.
    :rtype: State
    :raises pyfcstm.entry.base.ClickErrorException: If the path cannot be
        resolved.
    """
    try:
        return state_machine.resolve_state(raw_path.strip())
    except (LookupError, ValueError) as err:
        raise ClickErrorException(
            "Failed to resolve {opt}={value!r}. Provide a full state path "
            "such as 'Root.System.Active'.".format(opt=option_name, value=raw_path)
        )


def _print_reach_text(result: ReachabilityResult) -> None:
    """
    Pretty-print a :class:`ReachabilityResult` to stdout in text mode.

    :param result: Verdict produced by :func:`pyfcstm.topology.check_reachability`.
    :type result: ReachabilityResult
    """
    source_txt = ".".join(result.source.path) if result.source is not None else "?"
    target_txt = ".".join(result.target.path) if result.target is not None else "?"
    if result.reachable:
        click.secho(
            "[reachable] target {tgt!r} reachable from source {src!r}.".format(
                src=source_txt, tgt=target_txt
            ),
            fg='green',
        )
        click.echo("  witness: " + result.format_witness())
    else:
        click.secho(
            "[unreachable] target {tgt!r} NOT reachable from source {src!r}.".format(
                src=source_txt, tgt=target_txt
            ),
            fg='red',
        )
        if result.unreach_leaves:
            click.echo(
                "  unreachable leaves ({n}):".format(n=len(result.unreach_leaves))
            )
            for leaf in result.unreach_leaves:
                click.echo("    - " + ".".join(leaf.path))


def _reach_to_dict(result: ReachabilityResult) -> Dict[str, Any]:
    """
    Serialize a :class:`ReachabilityResult` into a JSON-friendly dict.

    :param result: Verdict.
    :type result: ReachabilityResult
    :return: JSON-serializable dictionary.
    :rtype: Dict[str, Any]
    """
    return {
        "verdict": "reachable" if result.reachable else "unreachable",
        "reachable": result.reachable,
        "source": ".".join(result.source.path) if result.source is not None else None,
        "target": ".".join(result.target.path) if result.target is not None else None,
        "witness_path": [format_node(n) for n in (result.witness_path or ())],
        "unreach_leaves": [".".join(l.path) for l in result.unreach_leaves],
    }


def _print_finite_text(result: FinitenessResult) -> None:
    """
    Pretty-print a :class:`FinitenessResult` to stdout in text mode.

    :param result: Verdict produced by :func:`pyfcstm.topology.check_finiteness`.
    :type result: FinitenessResult
    """
    source_txt = ".".join(result.source.path) if result.source is not None else "?"
    if result.finite:
        click.secho(
            "[finite] every macro path from {src!r} reaches [*].".format(src=source_txt),
            fg='green',
        )
        return
    click.secho(
        "[infinite] {n} leaf(s) reachable from {src!r} cannot reach [*].".format(
            n=result.violating_node_count, src=source_txt
        ),
        fg='red',
    )
    if result.counterexample is not None:
        click.echo("  counterexample: " + result.counterexample.format())


def _finite_to_dict(result: FinitenessResult) -> Dict[str, Any]:
    """
    Serialize a :class:`FinitenessResult` into a JSON-friendly dict.

    :param result: Verdict.
    :type result: FinitenessResult
    :return: JSON-serializable dictionary.
    :rtype: Dict[str, Any]
    """
    cex = result.counterexample
    cex_payload: Optional[Dict[str, Any]] = None
    if cex is not None:
        cex_payload = {
            "kind": cex.kind,
            "prefix": [".".join(s.path) for s in cex.prefix],
            "cycle": [".".join(s.path) for s in cex.cycle],
            "deadlock_leaf": (
                ".".join(cex.deadlock_leaf.path)
                if cex.deadlock_leaf is not None else None
            ),
            "text": cex.format(),
        }
    return {
        "verdict": "finite" if result.finite else "infinite",
        "finite": result.finite,
        "source": ".".join(result.source.path) if result.source is not None else None,
        "violating_node_count": result.violating_node_count,
        "counterexample": cex_payload,
    }


def _print_inev_text(result: InevitabilityResult) -> None:
    """
    Pretty-print an :class:`InevitabilityResult` to stdout in text mode.

    :param result: Verdict produced by :func:`pyfcstm.topology.check_inevitability`.
    :type result: InevitabilityResult
    """
    source_txt = ".".join(result.source.path) if result.source is not None else "?"
    target_txt = ".".join(result.target.path) if result.target is not None else "?"
    if result.inevitable:
        click.secho(
            "[inevitable] every macro path from {src!r} passes through {tgt!r}.".format(
                src=source_txt, tgt=target_txt
            ),
            fg='green',
        )
        return
    click.secho(
        "[avoidable] some macro path from {src!r} avoids {tgt!r}.".format(
            src=source_txt, tgt=target_txt
        ),
        fg='red',
    )
    if result.counterexample is not None:
        click.echo(
            "  counterexample ({kind}): {text}".format(
                kind=result.counterexample.kind,
                text=result.counterexample.format(),
            )
        )


def _inev_to_dict(result: InevitabilityResult) -> Dict[str, Any]:
    """
    Serialize an :class:`InevitabilityResult` into a JSON-friendly dict.

    :param result: Verdict.
    :type result: InevitabilityResult
    :return: JSON-serializable dictionary.
    :rtype: Dict[str, Any]
    """
    cex = result.counterexample
    cex_payload: Optional[Dict[str, Any]] = None
    if cex is not None:
        cex_payload = {
            "kind": cex.kind,
            "prefix": [".".join(s.path) for s in cex.prefix],
            "cycle": [".".join(s.path) for s in cex.cycle],
            "terminal": (
                format_node(cex.terminal) if cex.terminal is not None else None
            ),
            "text": cex.format(),
        }
    return {
        "verdict": "inevitable" if result.inevitable else "avoidable",
        "inevitable": result.inevitable,
        "source": ".".join(result.source.path) if result.source is not None else None,
        "target": ".".join(result.target.path) if result.target is not None else None,
        "counterexample": cex_payload,
    }


def _emit_warnings(graph_warnings: Any) -> None:
    """
    Print graph-construction warnings to stderr (if any).

    :param graph_warnings: ``TopologyGraph.warnings`` tuple.
    :type graph_warnings: Tuple[str, ...]
    """
    for w in graph_warnings or ():
        click.secho("warning: " + w, fg='yellow', err=True)


def _exit(ctx: click.Context, code: int) -> None:
    """
    Exit the active Click context with *code*.

    :param ctx: Active Click context.
    :type ctx: click.Context
    :param code: POSIX exit code.
    :type code: int
    """
    ctx.exit(code)


def _add_topology_subcommand(cli: click.Group) -> click.Group:
    """
    Mount the ``topology`` group + its three subcommands onto *cli*.

    :param cli: Top-level Click group.
    :type cli: click.Group
    :return: The mutated group, for decorator chaining.
    :rtype: click.Group
    """

    @cli.group(
        'topology',
        help='Pure-topological verification (reachability, finiteness, inevitability).',
        context_settings=CONTEXT_SETTINGS,
    )
    def topology() -> None:
        """Topological verification group."""
        pass

    @topology.command(
        'reach',
        help='Check whether TARGET is reachable from SOURCE in the macro graph.',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i', '--input-code', 'input_code_file', type=str, required=True,
        help='Input DSL file path.',
    )
    @click.option(
        '-t', '--target', 'target', type=str, required=True,
        help='Target state full path (e.g. Root.System.Active).',
    )
    @click.option(
        '-s', '--source', 'source', type=str, default=None,
        help='Source state full path. Defaults to the root init chain.',
    )
    @click.option(
        '--format', 'output_format', type=click.Choice(['text', 'json']),
        default='text', show_default=True, help='Output format.',
    )
    @click.pass_context
    def reach(ctx: click.Context, input_code_file: str, target: str,
              source: Optional[str], output_format: str) -> None:
        sm = _load_state_machine(input_code_file)
        target_state = _resolve_state(sm, target, '--target')
        source_state = _resolve_state(sm, source, '--source') if source else None
        graph = build_topology_graph(sm)
        result = check_reachability(sm, target=target_state, source=source_state, graph=graph)
        if output_format == 'json':
            click.echo(json.dumps(_reach_to_dict(result), ensure_ascii=False, indent=2))
        else:
            _print_reach_text(result)
            _emit_warnings(graph.warnings)
        _exit(ctx, 0 if result.reachable else 1)

    @topology.command(
        'finite',
        help='Check whether every macro path from SOURCE reaches [*].',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i', '--input-code', 'input_code_file', type=str, required=True,
        help='Input DSL file path.',
    )
    @click.option(
        '-s', '--source', 'source', type=str, default=None,
        help='Source state full path. Defaults to the root init chain.',
    )
    @click.option(
        '--format', 'output_format', type=click.Choice(['text', 'json']),
        default='text', show_default=True, help='Output format.',
    )
    @click.pass_context
    def finite(ctx: click.Context, input_code_file: str,
               source: Optional[str], output_format: str) -> None:
        sm = _load_state_machine(input_code_file)
        source_state = _resolve_state(sm, source, '--source') if source else None
        graph = build_topology_graph(sm)
        result = check_finiteness(sm, source=source_state, graph=graph)
        if output_format == 'json':
            click.echo(json.dumps(_finite_to_dict(result), ensure_ascii=False, indent=2))
        else:
            _print_finite_text(result)
            _emit_warnings(graph.warnings)
        _exit(ctx, 0 if result.finite else 1)

    @topology.command(
        'inevitable',
        help='Check whether TARGET is on every maximal macro path from SOURCE.',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i', '--input-code', 'input_code_file', type=str, required=True,
        help='Input DSL file path.',
    )
    @click.option(
        '-t', '--target', 'target', type=str, required=True,
        help='Target state full path.',
    )
    @click.option(
        '-s', '--source', 'source', type=str, default=None,
        help='Source state full path. Defaults to the root init chain.',
    )
    @click.option(
        '--format', 'output_format', type=click.Choice(['text', 'json']),
        default='text', show_default=True, help='Output format.',
    )
    @click.pass_context
    def inevitable(ctx: click.Context, input_code_file: str, target: str,
                   source: Optional[str], output_format: str) -> None:
        sm = _load_state_machine(input_code_file)
        target_state = _resolve_state(sm, target, '--target')
        source_state = _resolve_state(sm, source, '--source') if source else None
        graph = build_topology_graph(sm)
        result = check_inevitability(sm, target=target_state, source=source_state, graph=graph)
        if output_format == 'json':
            click.echo(json.dumps(_inev_to_dict(result), ensure_ascii=False, indent=2))
        else:
            _print_inev_text(result)
            _emit_warnings(graph.warnings)
        _exit(ctx, 0 if result.inevitable else 1)

    return cli
