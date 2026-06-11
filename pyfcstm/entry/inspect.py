"""Command-line model inspection for FCSTM DSL files.

This module registers the ``inspect`` CLI command. The command reads an FCSTM
DSL file, builds a :class:`pyfcstm.model.StateMachine`, runs
:func:`pyfcstm.diagnostics.inspect_model`, and emits the inspection payload as
stable JSON text.

Module map:

.. list-table::
   :header-rows: 1

   * - Entry
     - Purpose
   * - :func:`build_inspect_json`
     - Build JSON text for one input file and inspect policy.
   * - :func:`_add_inspect_subcommand`
     - Register the ``inspect`` subcommand on a Click group.

Examples::

    >>> import os
    >>> from tempfile import TemporaryDirectory
    >>> with TemporaryDirectory() as td:
    ...     path = os.path.join(td, "demo.fcstm")
    ...     with open(path, "w", encoding="utf-8") as f:
    ...         _ = f.write("state Root;")
    ...     text = build_inspect_json(path)
    >>> '"root_state_path": "Root"' in text
    True
"""

from __future__ import annotations

import json
import pathlib
from typing import Optional

import click

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..diagnostics import inspect_model
from ..dsl import GrammarParseError
from ..model import load_state_machine_from_file
from ..utils import ModelValidationError
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
        unset. ``0`` is forwarded unchanged to the solver layer, which may make
        Z3 return before a non-trivial proof search can complete.
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
        ...         _ = f.write("state Root;")
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


def _add_inspect_subcommand(cli: click.Group) -> click.Group:
    """Add the ``inspect`` subcommand to a Click CLI group.

    The registered command emits :func:`pyfcstm.diagnostics.inspect_model`
    output as JSON text. Verify integration remains disabled by default and is
    enabled only by passing ``--enable-verify``.

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
        help="Inspect a state machine DSL file and emit structured JSON.",
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
        help="Output JSON file, output to stdout when not assigned.",
    )
    @click.option(
        "--enable-verify",
        is_flag=True,
        help="Run inspect-eligible pyfcstm.verify algorithms.",
    )
    @click.option(
        "--max-complexity-tier",
        type=click.Choice(_INSPECT_COMPLEXITY_CHOICES, case_sensitive=True),
        default="structural",
        show_default=True,
        help=(
            "Maximum verify complexity tier accepted by inspect; bmc_search is "
            "parsed only to report a policy error."
        ),
    )
    @click.option(
        "--max-call-count-scaling",
        type=click.Choice(_INSPECT_CALL_COUNT_CHOICES, case_sensitive=True),
        default="linear_in_transitions",
        show_default=True,
        help=(
            "Maximum verify call-count scaling accepted by inspect; "
            "k_unrollings values are parsed only to report a policy error."
        ),
    )
    @click.option(
        "--smt-timeout-ms",
        type=click.IntRange(min=0),
        default=None,
        help=("Optional SMT solver timeout in milliseconds; 0 is forwarded unchanged."),
    )
    def inspect_command(
        input_code_file: str,
        output_file: Optional[str],
        enable_verify: bool,
        max_complexity_tier: str,
        max_call_count_scaling: str,
        smt_timeout_ms: Optional[int],
    ) -> None:
        """Inspect a state machine DSL file and emit JSON.

        :param input_code_file: Path to the file containing state machine DSL
            code.
        :type input_code_file: str
        :param output_file: Path to the output JSON file. If ``None``, output
            is written to stdout.
        :type output_file: Optional[str]
        :param enable_verify: Whether to run inspect-eligible verify
            algorithms.
        :type enable_verify: bool
        :param max_complexity_tier: Maximum verify complexity tier accepted by
            the inspect adapter.
        :type max_complexity_tier: str
        :param max_call_count_scaling: Maximum verify call-count scaling
            accepted by the inspect adapter.
        :type max_call_count_scaling: str
        :param smt_timeout_ms: Optional SMT solver timeout in milliseconds.
            ``None`` leaves the timeout unset, while ``0`` is forwarded
            unchanged to the solver layer.
        :type smt_timeout_ms: Optional[int]
        :return: ``None``. JSON is written to a file or stdout.
        :rtype: None

        Examples::

            $ pyfcstm inspect -i machine.fcstm
            $ pyfcstm inspect -i machine.fcstm --enable-verify --max-complexity-tier smt_linear
        """
        inspect_json = build_inspect_json(
            input_code_file,
            enable_verify=enable_verify,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
            smt_timeout_ms=smt_timeout_ms,
        )
        if output_file is None:
            click.echo(inspect_json, nl=False)
        else:
            try:
                pathlib.Path(output_file).write_text(inspect_json, encoding="utf-8")
            except OSError as err:
                # pathlib.Path.write_text raises OSError subclasses for
                # filesystem failures such as missing parent directories or
                # permission errors.
                raise ClickErrorException(
                    f"Failed to write inspect JSON file {output_file}: {err}"
                )

    return cli
