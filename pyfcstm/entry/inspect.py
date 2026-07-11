"""Command-line model inspection for FCSTM DSL files.

This module registers the ``inspect`` CLI command. The command reads an FCSTM
DSL file, builds a :class:`pyfcstm.model.StateMachine`, runs
:func:`pyfcstm.diagnostics.inspect_model`, and emits the inspection payload in
human-readable or full JSON formats from the CLI, while keeping stable
LLM-oriented renderers available through the Python API.

Module map:

.. list-table::
   :header-rows: 1

   * - Entry
     - Purpose
   * - :func:`build_inspect_json`
     - Build full JSON text for one input file and inspect policy.
   * - :func:`build_inspect_output`
     - Build text in the requested inspect output format.
   * - :func:`resolve_inspect_color_enabled`
     - Resolve whether the human inspect renderer should emit ANSI color.
   * - :func:`_add_inspect_subcommand`
     - Register the ``inspect`` subcommand on a Click group.

Examples::

    >>> import os
    >>> from tempfile import TemporaryDirectory
    >>> with TemporaryDirectory() as td:
    ...     path = os.path.join(td, "demo.fcstm")
    ...     with open(path, "w", encoding="utf-8") as f:
    ...         _ = f.write("state Root { state Idle; [*] -> Idle; }")
    ...     text = build_inspect_json(path)
    >>> '"root_state_path": "Root"' in text
    True
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional

import click

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..diagnostics import inspect_model
from ..diagnostics.inspect_render import (
    HumanRenderOptions,
    inspect_output_suffix_warning,
    render_inspect_human,
    render_inspect_llm_json,
    render_inspect_llm_markdown,
)
from ..dsl import GrammarParseError
from ..model import load_state_machine_from_file
from ..utils import ModelValidationError, auto_decode
from ..verify import InspectAccessForbiddenError
from ..verify.taxonomy import (
    CALL_COUNT_SCALING_ORDER,
    COMPLEXITY_TIER_ORDER,
)


_INSPECT_COMPLEXITY_CHOICES = tuple(COMPLEXITY_TIER_ORDER) + ("bmc_search",)
_INSPECT_CALL_COUNT_CHOICES = CALL_COUNT_SCALING_ORDER + (
    "k_unrollings",
    "k_unrollings_times_branching",
)
_INSPECT_OUTPUT_FORMAT_CHOICES = ("human", "json", "llm-json", "llm-md")
_INSPECT_CLI_OUTPUT_FORMAT_CHOICES = ("human", "json")
_INSPECT_COLOR_CHOICES = ("auto", "always", "never")


def _read_inspect_source_text(input_code_file: str) -> str:
    """Read and decode the primary FCSTM source file for renderers.

    The model loader remains responsible for import-aware parsing. This helper
    only provides the top-level source text used to render diagnostic source
    excerpts in human and stable LLM formats.

    :param input_code_file: Path to the primary input FCSTM file.
    :type input_code_file: str
    :return: Decoded source text.
    :rtype: str
    :raises OSError: If the file cannot be read.
    :raises UnicodeDecodeError: If the file cannot be decoded.

    Example::

        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     path = os.path.join(td, "demo.fcstm")
        ...     with open(path, "w", encoding="utf-8") as f:
        ...         _ = f.write("state Root { state Idle; [*] -> Idle; }")
        ...     _read_inspect_source_text(path)
        'state Root { state Idle; [*] -> Idle; }'
    """
    return auto_decode(pathlib.Path(input_code_file).read_bytes())


def _validate_inspect_policy(
    max_complexity_tier: str,
    max_call_count_scaling: str,
) -> None:
    """Validate inspect policy knobs before the CLI reads an input model.

    The Click layer accepts the full taxonomy labels so forbidden labels can
    produce the same domain-specific policy error as the inspect adapter.  The
    CLI must still reject those labels before parsing a user file, even when
    ``--enable-verify`` is not passed.

    :param max_complexity_tier: Maximum verify complexity tier requested by
        the caller.
    :type max_complexity_tier: str
    :param max_call_count_scaling: Maximum verify call-count scaling requested
        by the caller.
    :type max_call_count_scaling: str
    :return: ``None``.
    :rtype: None
    :raises pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: If
        either inspect policy knob is outside the automatic inspect budget.

    Examples::

        >>> _validate_inspect_policy("structural", "linear_in_transitions")
        >>> _validate_inspect_policy("bmc_search", "linear_in_transitions")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: bmc_search algorithms are not allowed in automatic inspect runs
        >>> _validate_inspect_policy("structural", "k_unrollings")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: call-count scaling 'k_unrollings' is not allowed in automatic inspect runs
    """
    if max_complexity_tier == "bmc_search":
        raise InspectAccessForbiddenError(
            "bmc_search algorithms are not allowed in automatic inspect runs"
        )
    if max_complexity_tier not in COMPLEXITY_TIER_ORDER:
        raise InspectAccessForbiddenError(
            "unknown inspect complexity tier: {maximum!r}".format(
                maximum=max_complexity_tier
            )
        )
    if max_call_count_scaling not in _INSPECT_CALL_COUNT_CHOICES:
        raise InspectAccessForbiddenError(
            "unknown inspect call-count scaling: {maximum!r}".format(
                maximum=max_call_count_scaling
            )
        )
    if max_call_count_scaling not in CALL_COUNT_SCALING_ORDER:
        raise InspectAccessForbiddenError(
            "call-count scaling {maximum!r} is not allowed in automatic inspect runs".format(
                maximum=max_call_count_scaling
            )
        )


def resolve_inspect_color_enabled(
    color_mode: str,
    *,
    output_format: str = "human",
    output_file: Optional[str] = None,
    stdout_isatty: Optional[bool] = None,
    no_color: Optional[str] = None,
    term: Optional[str] = None,
) -> bool:
    """Return whether inspect output should include ANSI color.

    Color is a presentation feature for the human format only. Machine formats
    always stay ANSI-free so their JSON or Markdown can be consumed by scripts,
    editors, and LLM pipelines without escape-code cleanup.

    :param color_mode: Requested color mode: ``"auto"``, ``"always"``, or
        ``"never"``.
    :type color_mode: str
    :param output_format: Inspect output format, defaults to ``"human"``.
    :type output_format: str, optional
    :param output_file: Output path supplied to ``-o``. A non-``None`` value
        disables ANSI color even when ``color_mode`` is ``"always"``.
    :type output_file: Optional[str], optional
    :param stdout_isatty: Optional TTY probe result. ``None`` probes
        :data:`sys.stdout`.
    :type stdout_isatty: Optional[bool], optional
    :param no_color: Optional ``NO_COLOR`` value. ``None`` reads from the
        environment; any non-empty value disables auto color.
    :type no_color: Optional[str], optional
    :param term: Optional ``TERM`` value. ``None`` reads from the environment;
        ``"dumb"`` disables auto color.
    :type term: Optional[str], optional
    :return: ``True`` if the human renderer should emit ANSI color.
    :rtype: bool
    :raises ValueError: If ``color_mode`` is unsupported.

    Examples::

        >>> resolve_inspect_color_enabled("never", stdout_isatty=True)
        False
        >>> resolve_inspect_color_enabled("always", stdout_isatty=False)
        True
        >>> resolve_inspect_color_enabled("always", output_format="json", stdout_isatty=True)
        False
        >>> resolve_inspect_color_enabled("auto", stdout_isatty=True, no_color="0")
        False
    """
    if color_mode not in _INSPECT_COLOR_CHOICES:
        raise ValueError(f"unsupported inspect color mode: {color_mode!r}")
    if output_format != "human":
        return False
    if output_file is not None:
        return False
    if color_mode == "never":
        return False
    if color_mode == "always":
        return True

    no_color_value = os.environ.get("NO_COLOR") if no_color is None else no_color
    if no_color_value:
        return False
    term_value = os.environ.get("TERM") if term is None else term
    if term_value == "dumb":
        return False
    if stdout_isatty is None:
        stdout_isatty = sys.stdout.isatty()
    return bool(stdout_isatty)


def build_inspect_json(
    input_code_file: str,
    *,
    enable_verify: bool = False,
    max_complexity_tier: str = "structural",
    max_call_count_scaling: str = "linear_in_transitions",
    smt_timeout_ms: Optional[int] = None,
) -> str:
    """Build stable JSON text for an inspected FCSTM model.

    The helper centralizes the CLI workflow: read and parse the DSL file, build
    the state-machine model, run :func:`pyfcstm.diagnostics.inspect_model`, and
    serialize the JSON-friendly dict returned by :meth:`ModelInspect.to_json`.

    :param input_code_file: Path to the input FCSTM DSL file.
    :type input_code_file: str
    :param enable_verify: Whether to run inspect-eligible verify algorithms.
    :type enable_verify: bool, optional
    :param max_complexity_tier: Maximum verify complexity tier accepted by
        inspect. Forbidden tiers are rejected even when ``enable_verify`` is
        false.
    :type max_complexity_tier: str, optional
    :param max_call_count_scaling: Maximum verify call-count scaling accepted
        by inspect. Forbidden scaling labels are rejected even when
        ``enable_verify`` is false.
    :type max_call_count_scaling: str, optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds for
        SMT-local verify algorithms. ``None`` leaves the solver timeout
        unset. ``0`` is forwarded unchanged to the solver layer and follows Z3
        semantics, where no finite timeout is configured.
    :type smt_timeout_ms: Optional[int], optional
    :return: Pretty-printed JSON inspection report text ending with a newline.
    :rtype: str
    :raises pyfcstm.entry.base.ClickErrorException: If the input file is
        missing, cannot be read, cannot be decoded, fails parsing or model
        validation, or requests a forbidden inspect verify policy.

    Examples::

        >>> import json
        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     path = os.path.join(td, "demo.fcstm")
        ...     with open(path, "w", encoding="utf-8") as f:
        ...         _ = f.write("state Root { state Idle; [*] -> Idle; }")
        ...     payload = json.loads(build_inspect_json(path))
        >>> payload["root_state_path"]
        'Root'
    """
    try:
        _validate_inspect_policy(
            max_complexity_tier,
            max_call_count_scaling,
        )
        machine = load_state_machine_from_file(input_code_file)
        report = inspect_model(
            machine,
            enable_verify=enable_verify,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
            smt_timeout_ms=smt_timeout_ms,
        )
    except FileNotFoundError:
        # load_state_machine_from_file reads the user-provided path; a missing
        # input file should be reported as a controlled CLI error.
        raise ClickErrorException(f"Input DSL file not found: {input_code_file}")
    except UnicodeDecodeError as err:
        # load_state_machine_from_file uses auto_decode, which raises
        # UnicodeDecodeError when none of the supported encodings can decode
        # user-provided input bytes.
        raise ClickErrorException(
            f"Failed to decode input DSL file {input_code_file}: {err}"
        )
    except OSError as err:
        # pathlib.Path.read_bytes inside load_state_machine_from_file raises
        # OSError subclasses for filesystem failures such as permission
        # errors, missing parent components, or directory paths.
        raise ClickErrorException(
            f"Failed to read input DSL file {input_code_file}: {err}"
        )
    except GrammarParseError as err:
        # parse_state_machine_dsl raises GrammarParseError for syntax and
        # lexical failures in user-provided FCSTM text.
        raise ClickErrorException(
            f"Failed to parse input DSL file {input_code_file}: {err}"
        )
    except ModelValidationError as err:
        # parse_dsl_node_to_state_machine raises ModelValidationError for
        # model-level contract violations after a syntactically valid parse.
        raise ClickErrorException(
            f"Invalid state machine model in {input_code_file}: {err}"
        )
    except InspectAccessForbiddenError as err:
        # _validate_inspect_policy and inspect_model reject forbidden automatic
        # inspect verify policies such as BMC search.
        raise ClickErrorException(str(err))

    return (
        json.dumps(
            report.to_json(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def build_inspect_output(
    input_code_file: str,
    *,
    output_format: str = "human",
    color_enabled: bool = False,
    enable_verify: bool = False,
    max_complexity_tier: str = "structural",
    max_call_count_scaling: str = "linear_in_transitions",
    smt_timeout_ms: Optional[int] = None,
) -> str:
    """Build inspect output text in the requested presentation format.

    ``output_format="json"`` delegates to :func:`build_inspect_json` so the
    full JSON contract stays byte-for-byte aligned with the pre-existing
    machine-readable path. Human and stable LLM formats additionally read the
    top-level source file to render source excerpts.

    :param input_code_file: Path to the input FCSTM DSL file.
    :type input_code_file: str
    :param output_format: One of ``"human"``, ``"json"``,
        ``"llm-json"``, or ``"llm-md"``. The CLI exposes only
        ``"human"`` and ``"json"``, while LLM formats remain available to
        Python callers. Defaults to ``"human"``.
    :type output_format: str, optional
    :param color_enabled: Whether the human renderer should emit ANSI color.
        Ignored by machine-readable formats.
    :type color_enabled: bool, optional
    :param enable_verify: Whether to run inspect-eligible verify algorithms.
    :type enable_verify: bool, optional
    :param max_complexity_tier: Maximum verify complexity tier accepted by
        inspect.
    :type max_complexity_tier: str, optional
    :param max_call_count_scaling: Maximum verify call-count scaling accepted
        by inspect.
    :type max_call_count_scaling: str, optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Rendered inspect output ending with a newline.
    :rtype: str
    :raises pyfcstm.entry.base.ClickErrorException: If reading, parsing, model
        validation, or inspect policy validation fails.
    :raises ValueError: If ``output_format`` is not supported.

    Example::

        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     path = os.path.join(td, "demo.fcstm")
        ...     with open(path, "w", encoding="utf-8") as f:
        ...         _ = f.write("state Root { state Idle; [*] -> Idle; }")
        ...     text = build_inspect_output(path)
        >>> "[WARN] FCSTM Inspect Report" in text
        True
    """
    if output_format == "json":
        return build_inspect_json(
            input_code_file,
            enable_verify=enable_verify,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
            smt_timeout_ms=smt_timeout_ms,
        )
    if output_format not in _INSPECT_OUTPUT_FORMAT_CHOICES:
        raise ValueError(f"unsupported inspect output format: {output_format!r}")
    try:
        _validate_inspect_policy(
            max_complexity_tier,
            max_call_count_scaling,
        )
        source_text = _read_inspect_source_text(input_code_file)
        machine = load_state_machine_from_file(input_code_file)
        report = inspect_model(
            machine,
            enable_verify=enable_verify,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
            smt_timeout_ms=smt_timeout_ms,
        )
    except FileNotFoundError:
        # _read_inspect_source_text reads the user-provided path; a missing
        # input file should be reported as a controlled CLI error.
        raise ClickErrorException(f"Input DSL file not found: {input_code_file}")
    except UnicodeDecodeError as err:
        # auto_decode raises UnicodeDecodeError when none of the supported
        # encodings can decode user-provided input bytes.
        raise ClickErrorException(
            f"Failed to decode input DSL file {input_code_file}: {err}"
        )
    except OSError as err:
        # pathlib.Path.read_bytes and the model loader raise OSError
        # subclasses for filesystem failures such as permission errors.
        raise ClickErrorException(
            f"Failed to read input DSL file {input_code_file}: {err}"
        )
    except GrammarParseError as err:
        # parse_state_machine_dsl raises GrammarParseError for syntax and
        # lexical failures in user-provided FCSTM text.
        raise ClickErrorException(
            f"Failed to parse input DSL file {input_code_file}: {err}"
        )
    except ModelValidationError as err:
        # parse_dsl_node_to_state_machine raises ModelValidationError for
        # model-level contract violations after a syntactically valid parse.
        raise ClickErrorException(
            f"Invalid state machine model in {input_code_file}: {err}"
        )
    except InspectAccessForbiddenError as err:
        # _validate_inspect_policy and inspect_model reject forbidden
        # automatic inspect verify policies such as BMC search.
        raise ClickErrorException(str(err))

    if output_format == "human":
        return render_inspect_human(
            report,
            source_text,
            input_path=input_code_file,
            options=HumanRenderOptions(color_enabled=color_enabled),
        )
    if output_format == "llm-json":
        return render_inspect_llm_json(report, source_text, input_path=input_code_file)
    return render_inspect_llm_markdown(report, source_text, input_path=input_code_file)


def _add_inspect_subcommand(cli: click.Group) -> click.Group:
    """Add the ``inspect`` subcommand to a Click CLI group.

    The registered command emits a human-readable report by default and can
    still emit the full :func:`pyfcstm.diagnostics.inspect_model` JSON payload
    when ``--format json`` is selected. LLM-oriented and verify-policy controls
    remain outside the public CLI surface; those renderers are available
    through :func:`build_inspect_output` and :func:`build_inspect_json` for
    internal callers.

    :param cli: The Click group to which the subcommand should be added.
    :type cli: click.Group
    :return: The same CLI group instance with ``inspect`` registered.
    :rtype: click.Group

    Examples::

        >>> import click
        >>> app = click.Group()
        >>> app = _add_inspect_subcommand(app)
        >>> "inspect" in app.commands
        True
    """

    @cli.command(
        "inspect",
        help="Inspect a state machine DSL file and emit a human-readable report by default.",
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        "-i",
        "--input-code",
        "input_code_file",
        type=str,
        required=True,
        help="Input code file of state machine DSL.",
    )
    @click.option(
        "-o",
        "--output",
        "output_file",
        type=str,
        default=None,
        help="Output file, output to stdout when not assigned.",
    )
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(_INSPECT_CLI_OUTPUT_FORMAT_CHOICES, case_sensitive=True),
        default="human",
        show_default=True,
        help="Inspect output format; use json for the full machine-readable report.",
    )
    @click.option(
        "--color",
        "color_mode",
        type=click.Choice(_INSPECT_COLOR_CHOICES, case_sensitive=True),
        default="auto",
        show_default=True,
        help="Control ANSI color for human inspect output only.",
    )
    def inspect_command(
        input_code_file: str,
        output_file: Optional[str],
        output_format: str,
        color_mode: str,
    ) -> None:
        """Inspect a state machine DSL file and emit the selected report format.

        :param input_code_file: Path to the file containing state machine DSL
            code.
        :type input_code_file: str
        :param output_file: Path to the output file. If ``None``, output is
            written to stdout.
        :type output_file: Optional[str]
        :param output_format: Inspect output format.
        :type output_format: str
        :param color_mode: ANSI color mode for human output.
        :type color_mode: str
        :return: ``None``. Inspect output is written to a file or stdout.
        :rtype: None

        Examples::

            $ pyfcstm inspect -i machine.fcstm
            $ pyfcstm inspect -i machine.fcstm --format json
            $ pyfcstm inspect -i machine.fcstm --color always
        """
        color_enabled = resolve_inspect_color_enabled(
            color_mode,
            output_format=output_format,
            output_file=output_file,
        )
        inspect_output = build_inspect_output(
            input_code_file,
            output_format=output_format,
            color_enabled=color_enabled,
        )
        warning = inspect_output_suffix_warning(output_file, output_format)
        if warning is not None:
            click.echo(f"Warning: {warning}", err=True)
        if output_file is None:
            click.echo(inspect_output, nl=False, color=color_enabled)
        else:
            try:
                pathlib.Path(output_file).write_text(inspect_output, encoding="utf-8")
            except OSError as err:
                # pathlib.Path.write_text raises OSError subclasses for
                # filesystem failures such as missing parent directories or
                # permission errors.
                raise ClickErrorException(
                    f"Failed to write inspect output file {output_file}: {err}"
                )

    return cli
