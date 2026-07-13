"""Argument parsing for the private self-check supervisor and worker."""

import argparse
from dataclasses import dataclass
from typing import Optional, Sequence


class SelfCheckArgumentError(ValueError):
    """Raised when a self-check or worker argument contract is invalid."""


@dataclass(frozen=True)
class SelfCheckOptions:
    """
    Validated supervisor options.

    :param profile: Selected profile name, defaults to ``'default'``.
    :type profile: str
    :param network: Whether network probes are enabled, defaults to ``False``.
    :type network: bool
    :param output_format: ``human`` or ``json``, defaults to ``'human'``.
    :type output_format: str
    :param report: Optional JSON report path, defaults to ``None``.
    :type report: Optional[str], optional
    :param color: ``auto``, ``always``, or ``never``, defaults to ``'auto'``.
    :type color: str
    :param timeout_scale: Time multiplier, defaults to ``1.0``.
    :type timeout_scale: float
    :param fail_on_warn: Treat required WARN as failure, defaults to ``False``.
    :type fail_on_warn: bool
    :param redact: Redact environment paths, defaults to ``True``.
    :type redact: bool

    Example::

        >>> SelfCheckOptions().profile
        'default'
    """

    profile: str = "default"
    network: bool = False
    output_format: str = "human"
    report: Optional[str] = None
    color: str = "auto"
    timeout_scale: float = 1.0
    fail_on_warn: bool = False
    redact: bool = True


@dataclass(frozen=True)
class WorkerOptions:
    """
    Validated hidden worker protocol options.

    :param check_id: Stable check identifier.
    :type check_id: str
    :param worker_key: Static registry key.
    :type worker_key: str
    :param nonce: 32-character lowercase nonce.
    :type nonce: str
    :param result_mode: ``file`` or ``stdout``.
    :type result_mode: str
    :param result_file: Append-only path for file mode, defaults to ``None``.
    :type result_file: Optional[str], optional
    :param test_mode: Internal test-only fault mode, defaults to ``None``.
    :type test_mode: Optional[str], optional

    Example::

        >>> WorkerOptions("demo", "demo", "0" * 32, "stdout").result_mode
        'stdout'
    """

    check_id: str
    worker_key: str
    nonce: str
    result_mode: str
    result_file: Optional[str] = None
    test_mode: Optional[str] = None


def _build_supervisor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False, prog="pyfcstm --self-check"
    )
    parser.add_argument(
        "--profile", choices=("default", "full", "visualize"), default="default"
    )
    parser.add_argument("--network", action="store_true")
    parser.add_argument(
        "--format", dest="output_format", choices=("human", "json"), default="human"
    )
    parser.add_argument("--report")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    parser.add_argument("--timeout-scale", type=float, default=1.0)
    parser.add_argument("--fail-on-warn", action="store_true")
    parser.add_argument("--no-redact", action="store_true")
    return parser


def _build_worker_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False, prog="pyfcstm worker"
    )
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--worker-key", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--result-mode", choices=("file", "stdout"), required=True)
    parser.add_argument("--result-file")
    parser.add_argument("--test-mode")
    return parser


def _parse(parser: argparse.ArgumentParser, arguments: Sequence[str]):
    """Parse arguments and convert argparse failures to the private error type."""
    try:
        namespace, unknown = parser.parse_known_args(list(arguments))
    except SystemExit as err:
        # argparse uses SystemExit for syntax errors; the bootstrap must return a stable code.
        raise SelfCheckArgumentError("invalid self-check arguments") from err
    if unknown:
        raise SelfCheckArgumentError(
            "unknown self-check arguments: {}".format(" ".join(unknown))
        )
    return namespace


def parse_selfcheck_args(arguments: Sequence[str]) -> SelfCheckOptions:
    """
    Parse and validate public self-check options.

    :param arguments: Arguments after the root ``--self-check`` token.
    :type arguments: Sequence[str]
    :return: Validated supervisor options.
    :rtype: SelfCheckOptions
    :raises SelfCheckArgumentError: If syntax or cross-option validation fails.

    Example::

        >>> parse_selfcheck_args(("--profile", "visualize")).profile
        'visualize'
    """
    namespace = _parse(_build_supervisor_parser(), arguments)
    if not 0.1 <= namespace.timeout_scale <= 100.0:
        raise SelfCheckArgumentError("--timeout-scale must be between 0.1 and 100")
    if namespace.network and namespace.profile != "visualize":
        raise SelfCheckArgumentError("--network requires --profile visualize")
    return SelfCheckOptions(
        profile=namespace.profile,
        network=namespace.network,
        output_format=namespace.output_format,
        report=namespace.report,
        color=namespace.color,
        timeout_scale=namespace.timeout_scale,
        fail_on_warn=namespace.fail_on_warn,
        redact=not namespace.no_redact,
    )


def parse_worker_args(arguments: Sequence[str]) -> WorkerOptions:
    """
    Parse strict hidden-worker protocol options.

    :param arguments: Arguments after the hidden worker dispatch token.
    :type arguments: Sequence[str]
    :return: Validated worker options.
    :rtype: WorkerOptions
    :raises SelfCheckArgumentError: If required fields or mode-specific fields are invalid.

    Example::

        >>> parse_worker_args(("--check-id", "demo", "--worker-key", "demo", "--nonce", "0" * 32, "--result-mode", "stdout")).result_mode
        'stdout'
    """
    namespace = _parse(_build_worker_parser(), arguments)
    if namespace.result_mode == "file" and not namespace.result_file:
        raise SelfCheckArgumentError("file result mode requires --result-file")
    if namespace.result_mode == "stdout" and namespace.result_file is not None:
        raise SelfCheckArgumentError("stdout result mode forbids --result-file")
    return WorkerOptions(
        check_id=namespace.check_id,
        worker_key=namespace.worker_key,
        nonce=namespace.nonce,
        result_mode=namespace.result_mode,
        result_file=namespace.result_file,
        test_mode=namespace.test_mode,
    )
