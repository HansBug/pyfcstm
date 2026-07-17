"""Command-line bounded model checking for FCSTM models.

This module composes the public BMC pipeline into the ``pyfcstm bmc`` command.
It keeps query compilation, solving, witness decoding, and runtime replay
explicit while providing stable human and JSON process contracts.

The normative ``bmc-cli/v1`` JSON Schema is published as a download from the
`BMC result protocol reference
<https://pyfcstm.readthedocs.io/en/latest/reference/bmc_results/index.html>`_
rather than shipped as a runtime package resource.

Module map:

.. list-table::
   :header-rows: 1

   * - Entry
     - Purpose
   * - :func:`build_bmc_output`
     - Run one model/query pair and return report text plus its exit status.
   * - :func:`write_bmc_output`
     - Atomically replace an output file with a completed report.
   * - :func:`_add_bmc_subcommand`
     - Register the ``bmc`` command on a Click group.

Examples::

    >>> import os
    >>> from tempfile import TemporaryDirectory
    >>> with TemporaryDirectory() as td:
    ...     model_path = os.path.join(td, "machine.fcstm")
    ...     query_path = os.path.join(td, "property.fbmcq")
    ...     with open(model_path, "w", encoding="utf-8") as f:
    ...         _ = f.write("state Root;")
    ...     with open(query_path, "w", encoding="utf-8") as f:
    ...         _ = f.write('check reach <= 1: active("Root");')
    ...     report, exit_code = build_bmc_output(model_path, query_path)
    >>> exit_code
    0
    >>> report.startswith("BMC reach <= 1: PROPERTY HOLDS")
    True
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

import click

from .base import CONTEXT_SETTINGS, ClickErrorException, command_wrap

if TYPE_CHECKING:  # pragma: no cover - static imports are never executed.
    from ..bmc import (
        BmcPropertyFormula,
        BmcReplayResult,
        BmcSolveResult,
        BmcWitnessTrace,
    )
from ..dsl import GrammarParseError
from ..model import StateMachine, load_state_machine_from_file
from ..utils import ModelValidationError, auto_decode


class _BmcCliInternalError(RuntimeError):
    """Mark an internal BMC failure that must retain its traceback."""


def _parse_bmc_query(*args, **kwargs):
    """Load and call the BMC query parser only when BMC is requested."""
    from ..bmc import parse_bmc_query as implementation

    return implementation(*args, **kwargs)


def _compile_bmc_query(*args, **kwargs):
    """Load and call the BMC compiler only when BMC is requested."""
    from ..bmc import compile_bmc_query as implementation

    return implementation(*args, **kwargs)


def _solve_bmc_property(*args, **kwargs):
    """Load and call the BMC solver only when BMC is requested."""
    from ..bmc import solve_bmc_property as implementation

    return implementation(*args, **kwargs)


def _decode_bmc_witness(*args, **kwargs):
    """Load and call the BMC decoder only when a SAT witness exists."""
    from ..bmc import decode_bmc_witness as implementation

    return implementation(*args, **kwargs)


def _decode_bmc_result_trace(*args, **kwargs):
    """Load and call the role-aware result decoder for a selected model."""
    from ..bmc import decode_bmc_result_trace as implementation

    return implementation(*args, **kwargs)


def _replay_bmc_witness(*args, **kwargs):
    """Load and call BMC runtime replay only when a SAT witness exists."""
    from ..bmc import replay_bmc_witness as implementation

    return implementation(*args, **kwargs)


@dataclass(frozen=True)
class _BmcExecution:
    formula: BmcPropertyFormula
    result: BmcSolveResult
    witness: Optional[BmcWitnessTrace]
    replay: Optional[BmcReplayResult]
    exit_code: int


def _read_query_file(query_file: str) -> str:
    try:
        return auto_decode(pathlib.Path(query_file).read_bytes())
    except FileNotFoundError:
        # Path.read_bytes raises FileNotFoundError when the requested query does
        # not exist; present it as a controlled CLI input failure.
        raise ClickErrorException("Query file not found: %s" % query_file)
    except UnicodeDecodeError as err:
        # auto_decode raises UnicodeDecodeError when no supported decoding can
        # decode the query bytes.
        raise ClickErrorException("Failed to decode BMC query file: %s" % err)
    except OSError as err:
        # Path.read_bytes raises other OSError subclasses for permission and
        # filesystem failures.
        raise ClickErrorException("Failed to read BMC query file: %s" % err)


def _load_model(input_code_file: str) -> StateMachine:
    try:
        return load_state_machine_from_file(input_code_file)
    except FileNotFoundError:
        # load_state_machine_from_file raises FileNotFoundError for a missing
        # primary FCSTM input.
        raise ClickErrorException("Input DSL file not found: %s" % input_code_file)
    except UnicodeDecodeError as err:
        # The import-aware loader raises UnicodeDecodeError for undecodable
        # primary or imported model files.
        raise ClickErrorException("Failed to decode FCSTM model: %s" % err)
    except GrammarParseError as err:
        # The FCSTM parser raises GrammarParseError for source syntax errors.
        raise ClickErrorException("Failed to parse FCSTM model: %s" % err)
    except ModelValidationError as err:
        # Model construction raises ModelValidationError for semantic model
        # errors after parsing.
        raise ClickErrorException("Invalid FCSTM model: %s" % err)
    except OSError as err:
        # The loader raises OSError subclasses for primary/imported file access
        # failures other than a missing primary input.
        raise ClickErrorException("Failed to read FCSTM model: %s" % err)


def _compile_query(
    model: StateMachine,
    query_text: str,
    max_bound: Optional[int],
) -> BmcPropertyFormula:
    from ..bmc import (
        BmcError,
        BmcOptions,
        BmcQueryParseError,
        InvalidBmcQuery,
        UnsupportedBmcQuery,
    )

    options = BmcOptions(max_bound=max_bound) if max_bound is not None else None
    try:
        query = _parse_bmc_query(query_text)
    except (BmcQueryParseError, InvalidBmcQuery) as err:
        # BmcQueryParseError: parse_bmc_query rejects malformed FBMCQ text;
        # InvalidBmcQuery: parsed query objects reject invalid source structure.
        raise ClickErrorException("Failed to compile BMC query: %s" % err)
    if max_bound is not None and query.property.bound > max_bound:
        raise ClickErrorException(
            "Failed to compile BMC query: max_bound policy rejected "
            "query_bound=%d with max_bound=%d." % (query.property.bound, max_bound)
        )
    try:
        return _compile_bmc_query(model, query, options=options)
    except (BmcQueryParseError, InvalidBmcQuery, UnsupportedBmcQuery) as err:
        # BmcQueryParseError: a delegated parser rejects source text;
        # InvalidBmcQuery: model-aware binding rejects user query references;
        # UnsupportedBmcQuery: lowering rejects a valid unsupported construct.
        raise ClickErrorException("Failed to compile BMC query: %s" % err)
    except BmcError as err:
        # Remaining BmcError classes originate in domain, encoding, relation,
        # property, or other construction invariants after user validation.
        raise _BmcCliInternalError(str(err)) from err


def _execute_bmc(
    input_code_file: str,
    query_file: str,
    timeout_ms: Optional[int],
    max_bound: Optional[int],
) -> _BmcExecution:
    from ..bmc import BmcBuildError

    model = _load_model(input_code_file)
    query_text = _read_query_file(query_file)
    formula = _compile_query(model, query_text, max_bound)
    try:
        result = _solve_bmc_property(formula, timeout_ms=timeout_ms)
    except BmcBuildError as err:
        # solve_bmc_property receives validated CLI arguments and a compiled
        # formula, so a build failure here is an internal implementation error.
        raise _BmcCliInternalError(str(err)) from err

    witness = None
    replay = None
    if result.status == "sat":
        try:
            witness = _decode_bmc_result_trace(result, source="primary")
            replay = _replay_bmc_witness(model, witness, abstract_handlers=None)
        except BmcBuildError as err:
            # A SAT model produced by this formula should always decode and
            # replay with the fixed public arguments used here. Failures retain
            # their traceback instead of becoming controlled input errors.
            raise _BmcCliInternalError(str(err)) from err
    elif result.incomplete_status == "sat":
        try:
            witness = _decode_bmc_result_trace(result, source="incomplete_suffix")
            replay = _replay_bmc_witness(model, witness, abstract_handlers=None)
        except BmcBuildError as err:
            # A SAT suffix model must satisfy the same decoder and replay
            # invariants as a primary model, while retaining its detached role.
            raise _BmcCliInternalError(str(err)) from err

    if replay is not None and not replay.ok:
        exit_code = 4
    elif result.incomplete or result.property_satisfied is None:
        exit_code = 3
    elif result.property_satisfied:
        exit_code = 0
    else:
        exit_code = 1
    return _BmcExecution(formula, result, witness, replay, exit_code)


def _property_payload(formula: BmcPropertyFormula) -> dict:
    return {
        "kind": formula.kind,
        "polarity": formula.polarity,
        "bound": formula.bound,
        "case_label": formula.case_label,
        "response_window": formula.response_window,
    }


def _human_verdict(execution: _BmcExecution) -> str:
    if execution.replay is not None and not execution.replay.ok:
        return "REPLAY MISMATCH; PROPERTY VERDICT UNTRUSTED"
    if execution.result.outcome == "scenario_infeasible":
        return "SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED"
    if execution.result.incomplete:
        return "PROPERTY INCONCLUSIVE"
    if execution.result.property_satisfied is None:
        return "PROPERTY INCONCLUSIVE"
    if execution.result.property_satisfied:
        return "PROPERTY HOLDS"
    return "PROPERTY DOES NOT HOLD"


def _human_outcome(execution: _BmcExecution) -> str:
    if execution.replay is not None and not execution.replay.ok:
        return (
            "The solver trace could not be reproduced by the runtime; "
            "treat this as an implementation defect."
        )
    messages = {
        "witness_found": "A satisfying execution was found within the bound.",
        "no_witness": (
            "No execution satisfying the reach objective was found within the bound."
        ),
        "property_satisfied": "No counterexample was found within the bound.",
        "property_violated": (
            "A counterexample violating the bounded property was found."
        ),
        "incomplete": "The visible horizon cannot decide every response window.",
        "scenario_infeasible": (
            "The admissible scenario is infeasible; the property was not evaluated."
        ),
        "feasibility_timeout": (
            "The scenario feasibility checks timed out before a property verdict."
        ),
        "feasibility_unknown": (
            "The scenario feasibility checks were inconclusive before a property verdict."
        ),
        "timeout": "The solver timed out before producing a conclusive result.",
        "unknown": "The solver could not produce a conclusive result.",
    }
    return messages[execution.result.outcome]


def _human_frame_label(witness: BmcWitnessTrace, frame_index: int) -> str:
    frame = witness.frames[frame_index]
    if frame.state is not None:
        return frame.state
    if frame.sentinel is not None:
        return frame.sentinel
    return "unknown"


def _human_compact_values(values: Tuple[str, ...]) -> str:
    visible = values[:3]
    text = ",".join(visible)
    if len(values) > len(visible):
        text += ",+%d more" % (len(values) - len(visible))
    return text


def _human_trace(execution: _BmcExecution) -> Tuple[str, ...]:
    witness = execution.witness
    if witness is None:
        return ()
    lines = ["Trace"]
    for step in witness.steps:
        details = [step.case_kind]
        event_paths = tuple(item.path for item in step.input_events)
        call_names = tuple(item.action_name for item in step.abstract_calls)
        if event_paths:
            details.append("events=%s" % _human_compact_values(event_paths))
        if call_names:
            details.append("calls=%s" % _human_compact_values(call_names))
        lines.append(
            "  %d: %s -> %s [%s]"
            % (
                step.index,
                _human_frame_label(witness, step.source_frame),
                _human_frame_label(witness, step.target_frame),
                "; ".join(details),
            )
        )
    return tuple(lines)


def _human_diagnostics(execution: _BmcExecution) -> Tuple[str, ...]:
    result = execution.result
    lines = ["Solver: %s in %.3f ms" % (result.status.upper(), result.elapsed_ms)]
    if result.timeout_ms is not None:
        lines.append(
            "Timeout: %d ms shared by all solver checks in this invocation"
            % result.timeout_ms
        )
    if result.incomplete_status is not None:
        lines.append("Horizon check: %s" % result.incomplete_status.upper())
    if result.reason is not None:
        lines.append("Solver reason: %s" % result.reason)
    if result.incomplete_reason is not None:
        lines.append("Horizon reason: %s" % result.incomplete_reason)
    feasibility = result.feasibility
    if feasibility is not None:
        lines.append(
            "Feasibility: kernel=%s, initialization=%s, assumptions=%s"
            % (
                feasibility.kernel.status or "not_checked",
                feasibility.initialization.status or "not_checked",
                feasibility.assumptions.status or "not_checked",
            )
        )
        if feasibility.infeasible_stage is not None:
            lines.append("Infeasible stage: %s" % feasibility.infeasible_stage)
    for item in result.diagnostics:
        if item.startswith("incomplete_elapsed_ms="):
            lines.append("Horizon solve time: %s ms" % item.partition("=")[2])
        else:
            lines.append("Diagnostic: %s" % item)

    if execution.replay is not None:
        witness = execution.witness
        if witness is None:
            raise _BmcCliInternalError(
                "Replay result exists without its decoded witness."
            )
        if execution.replay.ok:
            lines.append(
                "Replay: verified (%d frames, %d %s)."
                % (
                    len(witness.frames),
                    len(witness.steps),
                    "step" if len(witness.steps) == 1 else "steps",
                )
            )
        else:
            lines.append(
                "Replay: FAILED (%d mismatches)." % len(execution.replay.mismatches)
            )
            lines.extend(
                "Mismatch %s: %s" % (item.path, item.message)
                for item in execution.replay.mismatches
            )
    return tuple(lines)


def _human_report(execution: _BmcExecution) -> str:
    formula = execution.formula
    sections = [
        "BMC %s <= %d: %s\n%s"
        % (
            formula.kind,
            formula.bound,
            _human_verdict(execution),
            _human_outcome(execution),
        ),
        "\n".join(_human_diagnostics(execution)),
    ]
    trace = _human_trace(execution)
    if trace:
        sections.append("\n".join(trace))
    sections.append(
        "This is a bounded result over at most %d %s; it does not "
        "establish behavior beyond that bound.\n"
        "Use --json for the complete witness, replay trace, and stable "
        "machine-readable diagnostics."
        % (
            formula.bound,
            "macro-step" if formula.bound == 1 else "macro-steps",
        )
    )
    return "\n\n".join(sections) + "\n"


def _colorize_human_report(text: str) -> str:
    lines = text.splitlines()
    if "PROPERTY HOLDS" in lines[0]:
        lines[0] = click.style(lines[0], fg="green", bold=True)
    elif "PROPERTY INCONCLUSIVE" in lines[0]:
        lines[0] = click.style(lines[0], fg="yellow", bold=True)
    else:
        lines[0] = click.style(lines[0], fg="red", bold=True)
    for index, line in enumerate(lines):
        if line == "Trace":
            lines[index] = click.style(line, fg="cyan", bold=True)
        elif line.startswith("Solver:") or line.startswith("Replay:"):
            label, separator, value = line.partition(":")
            lines[index] = click.style(label + separator, fg="cyan", bold=True) + value
        elif line.startswith("This is a bounded result"):
            lines[index] = click.style(line, fg="yellow")
    return "\n".join(lines) + "\n"


def _resolve_bmc_color_enabled(
    color_mode: str,
    *,
    json_output: bool,
    output_file: Optional[str],
) -> bool:
    if json_output or output_file is not None or color_mode == "never":
        return False
    if color_mode == "always":
        return True
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return bool(sys.stdout.isatty())


def _json_report(
    execution: _BmcExecution,
    input_code_file: str,
    query_file: str,
) -> str:
    payload = {
        "schema_version": "bmc-cli/v1",
        "input": {
            "model_path": input_code_file,
            "query_path": query_file,
        },
        "property": _property_payload(execution.formula),
        "result": execution.result.to_canonical(),
        "witness": (
            execution.witness.to_canonical() if execution.witness is not None else None
        ),
        "replay": (
            execution.replay.to_canonical() if execution.replay is not None else None
        ),
        "exit_code": execution.exit_code,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def build_bmc_output(
    input_code_file: str,
    query_file: str,
    *,
    json_output: bool = False,
    timeout_ms: Optional[int] = None,
    max_bound: Optional[int] = None,
) -> Tuple[str, int]:
    """Run one bounded query and build its complete CLI report.

    :param input_code_file: FCSTM model file path.
    :type input_code_file: str
    :param query_file: FBMCQ query file path.
    :type query_file: str
    :param json_output: Whether to emit ``bmc-cli/v1`` JSON, defaults to
        ``False``. Its normative JSON Schema is linked from the `BMC result
        protocol reference
        <https://pyfcstm.readthedocs.io/en/latest/reference/bmc_results/index.html>`_.
    :type json_output: bool, optional
    :param timeout_ms: Optional total Z3 budget in milliseconds shared by all
        staged checks, defaults to ``None``.
    :type timeout_ms: int, optional
    :param max_bound: Maximum accepted query bound, defaults to ``None``.
    :type max_bound: int, optional
    :return: Completed report text and matching process exit status.
    :rtype: Tuple[str, int]
    :raises pyfcstm.entry.base.ClickErrorException: If model/query input is
        invalid or unsupported.
    :raises RuntimeError: If solving, witness decoding, or replay encounters an
        internal consistency failure.

    Examples::

        >>> # See the module example for a complete temporary-file invocation.
        >>> callable(build_bmc_output)
        True
    """
    execution = _execute_bmc(
        input_code_file,
        query_file,
        timeout_ms,
        max_bound,
    )
    if json_output:
        text = _json_report(execution, input_code_file, query_file)
    else:
        text = _human_report(execution)
    return text, execution.exit_code


def write_bmc_output(output_file: str, text: str) -> None:
    """Atomically replace one output file with a completed BMC report.

    The temporary file is created beside the target so :func:`os.replace`
    remains an atomic same-filesystem operation. Parent directories are not
    created.

    :param output_file: Destination file path.
    :type output_file: str
    :param text: Complete UTF-8 report text.
    :type text: str
    :return: ``None``.
    :rtype: None
    :raises OSError: If temporary-file creation, writing, synchronization, or
        replacement fails.
    :raises UnicodeError: If ``text`` cannot be encoded as UTF-8.

    Examples::

        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     path = os.path.join(td, "result.txt")
        ...     write_bmc_output(path, "ok\\n")
        ...     open(path, encoding="utf-8").read()
        'ok\\n'
    """
    target = pathlib.Path(output_file)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".%s." % target.name,
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, str(target))
    except (OSError, UnicodeError) as err:
        # os.fdopen/write/fsync/replace can fail for filesystem or encoding
        # reasons. Preserve the original target and report cleanup failures.
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            # os.replace already removed the temporary path.
            pass
        except OSError as cleanup_err:
            # A failed cleanup is observable and must not be silently lost.
            raise OSError(
                "%s; additionally failed to remove temporary file %s: %s"
                % (err, temporary_name, cleanup_err)
            ) from err
        raise


@command_wrap()
def _run_bmc_command(
    input_code_file: str,
    query_file: str,
    output_file: Optional[str],
    json_output: bool,
    timeout_ms: Optional[int],
    max_bound: Optional[int],
    color_mode: str,
) -> int:
    """Build and publish one report behind the CLI exception boundary."""
    text, exit_code = build_bmc_output(
        input_code_file,
        query_file,
        json_output=json_output,
        timeout_ms=timeout_ms,
        max_bound=max_bound,
    )
    if output_file is None:
        color_enabled = _resolve_bmc_color_enabled(
            color_mode,
            json_output=json_output,
            output_file=output_file,
        )
        if color_enabled:
            text = _colorize_human_report(text)
        click.echo(text, nl=False, color=color_enabled)
    else:
        try:
            write_bmc_output(output_file, text)
        except (OSError, UnicodeError) as err:
            # Atomic report creation raises OSError/UnicodeError for
            # filesystem and UTF-8 encoding failures.
            raise ClickErrorException(
                "Failed to write BMC output file %s: %s" % (output_file, err)
            )
    return exit_code


def _add_bmc_subcommand(cli: click.Group) -> click.Group:
    """Register the ``bmc`` subcommand on a Click group.

    :param cli: Click group that receives the command.
    :type cli: click.Group
    :return: The same group with ``bmc`` registered.
    :rtype: click.Group

    Examples::

        >>> app = click.Group()
        >>> _add_bmc_subcommand(app) is app
        True
        >>> "bmc" in app.commands
        True
    """

    @cli.command(
        "bmc",
        help="Run a bounded model checking query and replay SAT witnesses.",
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        "-i",
        "--input-code",
        "input_code_file",
        type=str,
        required=True,
        help="Input FCSTM model file.",
    )
    @click.option(
        "-q",
        "--query-file",
        type=str,
        required=True,
        help="Input FBMCQ query file.",
    )
    @click.option(
        "-o",
        "--output",
        "output_file",
        type=str,
        default=None,
        help="Output file; defaults to stdout.",
    )
    @click.option(
        "--json",
        "json_output",
        is_flag=True,
        help="Emit the stable bmc-cli/v1 JSON envelope.",
    )
    @click.option(
        "--timeout-ms",
        type=click.IntRange(min=1),
        default=None,
        help="Total Z3 timeout budget shared by all staged checks in milliseconds.",
    )
    @click.option(
        "--max-bound",
        type=click.IntRange(min=1),
        default=None,
        help="Reject queries whose bound exceeds this value.",
    )
    @click.option(
        "--color",
        "color_mode",
        type=click.Choice(("auto", "always", "never"), case_sensitive=True),
        default="auto",
        show_default=True,
        help="Control ANSI color for human terminal output.",
    )
    @click.pass_context
    def bmc_command(
        ctx: click.Context,
        input_code_file: str,
        query_file: str,
        output_file: Optional[str],
        json_output: bool,
        timeout_ms: Optional[int],
        max_bound: Optional[int],
        color_mode: str,
    ) -> None:
        """Run a bounded model checking query.

        :param ctx: Active Click command context.
        :type ctx: click.Context
        :param input_code_file: FCSTM model file path.
        :type input_code_file: str
        :param query_file: FBMCQ query file path.
        :type query_file: str
        :param output_file: Optional output path.
        :type output_file: str, optional
        :param json_output: Whether to emit JSON.
        :type json_output: bool
        :param timeout_ms: Optional total solver budget shared by all checks.
        :type timeout_ms: int, optional
        :param max_bound: Maximum accepted query bound.
        :type max_bound: int, optional
        :param color_mode: ANSI color mode for human terminal output.
        :type color_mode: str
        :return: ``None``.
        :rtype: None

        Examples::

            $ pyfcstm bmc -i machine.fcstm -q property.fbmcq
            $ pyfcstm bmc -i machine.fcstm -q property.fbmcq --json -o result.json
        """
        exit_code = _run_bmc_command(
            input_code_file,
            query_file,
            output_file,
            json_output,
            timeout_ms,
            max_bound,
            color_mode,
        )
        ctx.exit(exit_code)

    return cli


__all__ = ["build_bmc_output", "write_bmc_output"]
