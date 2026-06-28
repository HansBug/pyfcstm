"""
Run selected built-in template pytest suites.

This repo-local tool expands template suite names into concrete pytest paths or
node ids for local maintenance workflows. It deliberately lives under
``tools`` rather than the public :mod:`pyfcstm` package because suite selection
is CI and maintainer policy, not runtime functionality.

The module contains:

* :func:`build_template_pytest_command` - Build a pytest command for selected
  suites.
* :func:`main` - Command-line entry point for local template suite runs.

Example::

    $ PYFCSTM_TEMPLATE_SUITES=python python tools/run_template_suites.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from typing import Callable, Iterable, List, Mapping, MutableMapping, Optional, Sequence

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.package_templates import package_templates  # noqa: E402
from tools.template_suites import (  # noqa: E402
    DYNAMIC_SUITES,
    FIXED_SUITES,
    LEGAL_INPUT_SUITES,
    TemplateSuiteDetectionError,
    _expand_suite_token,
    detect_template_suites,
)

_TEMPLATE_CORE_TARGETS = (
    "test/template/test_template.py",
    "test/template/test_template_structure.py",
    "test/template/test_c_family_helper_scope.py",
    "test/template/test_cpp_wrapper_harness_guard.py",
    "test/template/test_native_semantic_alignment_framework.py",
)
_CPP_WRAPPER_SMOKE_TARGETS = (
    "test/template/cpp/test_cpp_wrapper.py",
    "test/template/cpp_poll/test_cpp_poll_wrapper.py",
)
_REPRESENTATIVE_CASE_IDS = (
    "design_basic_simple_transition",
    "design_composite_state",
    "event_path_mixed_formats_full",
    "hot_start_leaf_state",
    "hot_start_composite_waits_for_initial_event",
    "if_blocks_during_nested_true_branch",
    "temporary_variables_are_block_local",
    "abstract_hook_ref_context_reports_callsite_metadata",
    "design_pseudo_chain_multiple",
    "transition_into_composite_skips_unstable_initial_candidate",
)
_REPRESENTATIVE_ALIGNMENT_FUNCTIONS = (
    "test/template/c/test_semantic_fixture_alignment.py::"
    "test_generated_c_alignment_semantic_fixture",
    "test/template/c_poll/test_semantic_fixture_alignment.py::"
    "test_generated_c_poll_alignment_semantic_fixture",
    "test/template/cpp/test_semantic_fixture_alignment.py::"
    "test_generated_cpp_alignment_semantic_fixture",
    "test/template/cpp_poll/test_semantic_fixture_alignment.py::"
    "test_generated_cpp_poll_alignment_semantic_fixture",
)
_REPRESENTATIVE_ALIGNMENT_TARGETS = tuple(
    "{function}[{case_id}]".format(function=function, case_id=case_id)
    for function in _REPRESENTATIVE_ALIGNMENT_FUNCTIONS
    for case_id in _REPRESENTATIVE_CASE_IDS
)
_NATIVE_TOOLCHAIN_TARGETS_BY_SUITE = {
    "c": ("test/template/c/test_native_toolchain_alignment.py",),
    "c_poll": ("test/template/c_poll/test_native_toolchain_alignment.py",),
    "cpp": ("test/template/cpp/test_native_toolchain_alignment.py",),
    "cpp_poll": ("test/template/cpp_poll/test_native_toolchain_alignment.py",),
}
_SUITE_TARGETS = {
    "template_core": _TEMPLATE_CORE_TARGETS,
    "python": ("test/template/python",),
    "c": (
        "test/template/c/test_runtime.py",
        "test/template/c/test_semantic_fixture_alignment.py",
    ),
    "c_poll": (
        "test/template/c_poll/test_runtime.py",
        "test/template/c_poll/test_semantic_fixture_alignment.py",
    ),
    "cpp": (
        "test/template/cpp/test_cpp_wrapper.py",
        "test/template/cpp/test_semantic_fixture_alignment.py",
    ),
    "cpp_poll": (
        "test/template/cpp_poll/test_cpp_poll_wrapper.py",
        "test/template/cpp_poll/test_semantic_fixture_alignment.py",
    ),
}
_DEFAULT_SUITES = ("template_core", "python")
_SCHEMA_VERSION = "template-suite-runner/v1"
_ENABLE_VALUES = {"1", "true", "yes", "on"}


class TemplateSuiteRunnerError(ValueError):
    """
    Report invalid input for the template suite runner.

    :param message: Human-readable validation failure.
    :type message: str

    Example::

        >>> TemplateSuiteRunnerError("bad suite").args[0]
        'bad suite'
    """


def _repo_root() -> str:
    """
    Return the absolute repository root for this tools module.

    :return: Absolute repository root path.
    :rtype: str

    Example::

        >>> os.path.isdir(os.path.join(_repo_root(), 'tools'))
        True
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _read_changed_files(path: Optional[str]) -> List[str]:
    """
    Read newline-delimited changed files for detector-backed selection.

    :param path: Optional file path. ``None`` means no changed files.
    :type path: str, optional
    :return: Changed file paths.
    :rtype: list[str]
    :raises OSError: If ``path`` is provided but cannot be read.
    :raises UnicodeError: If ``path`` is not valid UTF-8 text.

    Example::

        >>> _read_changed_files(None)
        []
    """
    if path is None:
        return []
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def _read_message(path: Optional[str]) -> str:
    """
    Read an optional commit or local message file.

    :param path: Optional message path. ``None`` means empty message.
    :type path: str, optional
    :return: Message text.
    :rtype: str
    :raises OSError: If ``path`` is provided but cannot be read.
    :raises UnicodeError: If ``path`` is not valid UTF-8 text.

    Example::

        >>> _read_message(None)
        ''
    """
    if path is None:
        return ""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _ordered_targets(targets: Iterable[str]) -> List[str]:
    """
    Return unique pytest targets while preserving first occurrence order.

    :param targets: Pytest target strings.
    :type targets: collections.abc.Iterable[str]
    :return: Ordered unique targets.
    :rtype: list[str]

    Example::

        >>> _ordered_targets(['a', 'b', 'a'])
        ['a', 'b']
    """
    result = []
    seen = set()
    for target in targets:
        if target in seen:
            continue
        result.append(target)
        seen.add(target)
    return result


def expand_template_suite_targets(suites: Sequence[str]) -> List[str]:
    """
    Expand selected suites into pytest path or node targets.

    :param suites: Concrete suite names selected by the detector or runner.
    :type suites: collections.abc.Sequence[str]
    :return: Ordered pytest targets for those suites.
    :rtype: list[str]
    :raises TemplateSuiteRunnerError: If a suite is unsupported by the runner.

    Example::

        >>> expand_template_suite_targets(['template_core'])[:1]
        ['test/template/test_template.py']
    """
    targets = []
    for suite in suites:
        if suite == "default":
            targets.extend(expand_template_suite_targets(_DEFAULT_SUITES))
            targets.extend(_CPP_WRAPPER_SMOKE_TARGETS)
        elif suite == "template_representative":
            targets.extend(_REPRESENTATIVE_ALIGNMENT_TARGETS)
        elif suite in _SUITE_TARGETS:
            targets.extend(_SUITE_TARGETS[suite])
        else:
            raise TemplateSuiteRunnerError(
                "unsupported template runner suite: {0}".format(suite)
            )
    return _ordered_targets(targets)


def expand_template_pytest_targets(
    selected_suites: Sequence[str],
    run_native_toolchain: bool = False,
) -> List[str]:
    """
    Expand selected suites into the exact pytest targets for one run.

    :param selected_suites: Concrete suite names selected by the detector or
        runner.
    :type selected_suites: collections.abc.Sequence[str]
    :param run_native_toolchain: Whether to add native toolchain alignment
        targets for selected C-family suites, defaults to ``False``.
    :type run_native_toolchain: bool, optional
    :return: Ordered pytest targets for the requested run.
    :rtype: list[str]
    :raises TemplateSuiteRunnerError: If no pytest target is selected or
        native toolchain tests are requested without a C-family suite.

    Example::

        >>> expand_template_pytest_targets(['python'])
        ['test/template/python']
    """
    targets = expand_template_suite_targets(selected_suites)
    native_targets = []
    if run_native_toolchain:
        for suite in selected_suites:
            native_targets.extend(_NATIVE_TOOLCHAIN_TARGETS_BY_SUITE.get(suite, ()))
        if not native_targets:
            raise TemplateSuiteRunnerError(
                "native toolchain opt-in requires at least one selected "
                "C-family suite: c, c_poll, cpp, or cpp_poll"
            )
        targets.extend(native_targets)
        targets = _ordered_targets(targets)
    if not targets:
        raise TemplateSuiteRunnerError("no template pytest targets selected")
    return targets


def _native_toolchain_enabled(value: Optional[str], cli_enabled: bool) -> bool:
    """
    Return whether native toolchain tests are explicitly enabled.

    :param value: Environment value for ``PYFCSTM_RUN_NATIVE_TOOLCHAIN``.
    :type value: str, optional
    :param cli_enabled: Whether ``--run-native-toolchain`` was passed.
    :type cli_enabled: bool
    :return: ``True`` when native toolchain tests should run.
    :rtype: bool

    Example::

        >>> _native_toolchain_enabled('1', False)
        True
    """
    return cli_enabled or (value or "").strip().lower() in _ENABLE_VALUES


def _reject_runner_owned_pytest_args(pytest_args: Sequence[str]) -> None:
    """
    Reject pytest passthrough arguments that must be runner-owned.

    Native toolchain selection is a two-part contract: the runner must append
    both the native pytest targets and pytest's ``--run-native-toolchain`` flag.
    Allowing the flag through raw pytest passthrough arguments would enable the
    pytest option without adding the native targets, which creates a
    false-green footgun.

    :param pytest_args: Extra pytest arguments requested by the caller.
    :type pytest_args: collections.abc.Sequence[str]
    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteRunnerError: If a runner-owned option is passed
        through as a raw pytest argument.

    Example::

        >>> _reject_runner_owned_pytest_args(['-q'])
        >>> try:
        ...     _reject_runner_owned_pytest_args(['--run-native-toolchain'])
        ... except TemplateSuiteRunnerError as err:
        ...     print(str(err))
        pytest passthrough must not include --run-native-toolchain; use runner --run-native-toolchain or PYFCSTM_RUN_NATIVE_TOOLCHAIN=1
    """
    for argument in pytest_args:
        if argument == "--run-native-toolchain" or argument.startswith(
            "--run-native-toolchain="
        ):
            raise TemplateSuiteRunnerError(
                "pytest passthrough must not include --run-native-toolchain; "
                "use runner --run-native-toolchain or "
                "PYFCSTM_RUN_NATIVE_TOOLCHAIN=1"
            )


def _selected_suites_from_inputs(
    changed_files: Sequence[str],
    message: str,
    event_name: str,
    include_suites: Optional[str],
    skip_suites: Optional[str],
) -> Mapping[str, object]:
    """
    Resolve selected suites through the PR-1 detector semantics.

    :param changed_files: Changed repository paths.
    :type changed_files: collections.abc.Sequence[str]
    :param message: Message text scanned for suite labels.
    :type message: str
    :param event_name: Detector event name.
    :type event_name: str
    :param include_suites: Optional include suite override.
    :type include_suites: str, optional
    :param skip_suites: Optional skip suite override.
    :type skip_suites: str, optional
    :return: Detector result mapping.
    :rtype: collections.abc.Mapping[str, object]
    :raises TemplateSuiteDetectionError: If detector inputs are invalid.

    Example::

        >>> _selected_suites_from_inputs([], '', 'local', 'python', None)['selected_suites']
        ['python']
    """
    return detect_template_suites(
        changed_files=changed_files,
        message=message,
        event_name=event_name,
        include_suites=include_suites,
        skip_suites=skip_suites,
    )


def build_template_pytest_command(
    selected_suites: Sequence[str],
    pytest_args: Optional[Sequence[str]] = None,
    run_native_toolchain: bool = False,
) -> List[str]:
    """
    Build the pytest command for selected template suites.

    :param selected_suites: Concrete suite names to run. ``default`` expands to
        the local lightweight template set.
    :type selected_suites: collections.abc.Sequence[str]
    :param pytest_args: Extra pytest arguments appended after suite targets,
        defaults to ``None``.
    :type pytest_args: collections.abc.Sequence[str], optional
    :param run_native_toolchain: Whether to append explicit native toolchain
        tests and pytest's ``--run-native-toolchain`` flag, defaults to
        ``False``.
    :type run_native_toolchain: bool, optional
    :return: Command argv beginning with ``python -m pytest``.
    :rtype: list[str]
    :raises TemplateSuiteRunnerError: If no pytest target is selected.

    Example::

        >>> build_template_pytest_command(['python'])[1:4]
        ['-m', 'pytest', 'test/template/python']
    """
    pytest_args = list(pytest_args or [])
    _reject_runner_owned_pytest_args(pytest_args)
    targets = expand_template_pytest_targets(
        selected_suites,
        run_native_toolchain=run_native_toolchain,
    )

    command = [sys.executable, "-m", "pytest"]
    command.extend(targets)
    command.extend(["-sv", "-m", "unittest"])
    if run_native_toolchain:
        command.append("--run-native-toolchain")
    command.extend(pytest_args)
    return command


def _format_command(command: Sequence[str]) -> str:
    """
    Return a shell-readable command string for logs and JSON output.

    :param command: Command argv.
    :type command: collections.abc.Sequence[str]
    :return: Quoted command text.
    :rtype: str

    Example::

        >>> _format_command(['python', '-m', 'pytest'])
        'python -m pytest'
    """
    return " ".join(shlex.quote(item) for item in command)


def _package_templates(repo_root: str) -> None:
    """
    Refresh packaged built-in template assets.

    :param repo_root: Absolute repository root.
    :type repo_root: str
    :return: ``None``.
    :rtype: None
    :raises OSError: If packaging cannot write output assets.
    :raises ValueError: If template reuse validation fails.

    Example::

        >>> callable(_package_templates)
        True
    """
    package_templates(
        os.path.join(repo_root, "templates"),
        os.path.join(repo_root, "pyfcstm", "template"),
    )


def _runner_environment(run_native_toolchain: bool) -> MutableMapping[str, str]:
    """
    Build the subprocess environment for pytest execution.

    The runner clears ``SKIP_SLOW_TESTS`` for explicit template suite runs so a
    caller's fast-path environment cannot silently turn selected C-family full
    suites into false-green skips.

    :param run_native_toolchain: Whether native toolchain tests are enabled.
    :type run_native_toolchain: bool
    :return: Environment mapping for the pytest subprocess.
    :rtype: collections.abc.MutableMapping[str, str]

    Example::

        >>> env = _runner_environment(False)
        >>> env.get('SKIP_SLOW_TESTS', '')
        ''
    """
    env = os.environ.copy()
    env["UNITTEST"] = "1"
    env["SKIP_SLOW_TESTS"] = ""
    env.pop("PYFCSTM_TEMPLATE_SUITES", None)
    env.pop("PYFCSTM_SKIP_TEMPLATE_SUITES", None)
    env.pop("PYFCSTM_RUN_NATIVE_TOOLCHAIN", None)
    if run_native_toolchain:
        env["PYFCSTM_RUN_NATIVE_TOOLCHAIN"] = "1"
    return env


def _collect_targets_exist(repo_root: str, targets: Sequence[str]) -> None:
    """
    Verify that exact pytest node ids can be collected.

    :param repo_root: Absolute repository root.
    :type repo_root: str
    :param targets: Exact pytest targets to collect.
    :type targets: collections.abc.Sequence[str]
    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteRunnerError: If pytest cannot collect the targets.

    Example::

        >>> callable(_collect_targets_exist)
        True
    """
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-m",
        "unittest",
    ]
    command.extend(targets)
    completed = subprocess.run(
        command,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise TemplateSuiteRunnerError(
            "pytest cannot collect representative targets:\n{0}{1}".format(
                completed.stdout, completed.stderr
            )
        )


def _run_with_suite_environment_cleared(func: Callable[[], None]) -> None:
    """
    Run a callable while suite selection environment variables are hidden.

    :param func: Zero-argument callable to execute.
    :type func: typing.Callable[[], None]
    :return: ``None``.
    :rtype: None

    Example::

        >>> _run_with_suite_environment_cleared(lambda: None)
    """
    saved_include = os.environ.pop("PYFCSTM_TEMPLATE_SUITES", None)
    saved_skip = os.environ.pop("PYFCSTM_SKIP_TEMPLATE_SUITES", None)
    try:
        func()
    finally:
        if saved_include is not None:
            os.environ["PYFCSTM_TEMPLATE_SUITES"] = saved_include
        if saved_skip is not None:
            os.environ["PYFCSTM_SKIP_TEMPLATE_SUITES"] = saved_skip


def run_self_check() -> None:
    """
    Run the template suite runner self-check.

    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteRunnerError: If any runner mapping is invalid.
    :raises TemplateSuiteDetectionError: If detector compatibility regresses.

    Example::

        >>> run_self_check()
    """
    _run_with_suite_environment_cleared(_run_self_check_cases)


def _run_self_check_cases() -> None:
    """
    Execute runner self-check cases with suite env vars cleared.

    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteRunnerError: If any runner mapping is invalid.
    :raises TemplateSuiteDetectionError: If detector compatibility regresses.

    Example::

        >>> _run_self_check_cases()
    """
    repo_root = _repo_root()
    for token in LEGAL_INPUT_SUITES:
        expanded = _expand_suite_token(token)
        suites = (token,) if token in FIXED_SUITES else expanded
        if token == "all":
            suites = expanded
        targets = expand_template_suite_targets(suites)
        for target in targets:
            path = target.split("::", 1)[0]
            if not os.path.exists(os.path.join(repo_root, path)):
                raise TemplateSuiteRunnerError(
                    "pytest target path does not exist: {0}".format(path)
                )
    for case_id in _REPRESENTATIVE_CASE_IDS:
        case_path = os.path.join(
            repo_root,
            "test",
            "fixtures",
            "simulate_semantics",
            "cases",
            case_id + ".yaml",
        )
        if not os.path.exists(case_path):
            raise TemplateSuiteRunnerError(
                "representative semantic case does not exist: {0}".format(case_id)
            )
    _collect_targets_exist(repo_root, _REPRESENTATIVE_ALIGNMENT_TARGETS)
    ordinary_targets = expand_template_suite_targets(
        DYNAMIC_SUITES + ("template_core",)
    )
    for target in ordinary_targets:
        if "test_native_toolchain_alignment.py" in target:
            raise TemplateSuiteRunnerError(
                "ordinary template suite selected native toolchain test: {0}".format(
                    target
                )
            )
    default_targets = expand_template_suite_targets(("default",))
    for target in (
        _TEMPLATE_CORE_TARGETS + ("test/template/python",) + _CPP_WRAPPER_SMOKE_TARGETS
    ):
        if target not in default_targets:
            raise TemplateSuiteRunnerError(
                "default suite does not include expected target: {0}".format(target)
            )
    protected_result = _selected_suites_from_inputs(
        ["templates/c/machine.c.j2"], "", "local", None, "c"
    )
    if protected_result["selected_suites"] != ["c", "cpp"]:
        raise TemplateSuiteRunnerError(
            "skip suite removed a protected path-detected suite: {0!r}".format(
                protected_result["selected_suites"]
            )
        )
    manual_skip_result = _selected_suites_from_inputs([], "", "local", "c,cpp", "c")
    if manual_skip_result["selected_suites"] != ["cpp"]:
        raise TemplateSuiteRunnerError(
            "skip suite did not remove only the manual suite: {0!r}".format(
                manual_skip_result["selected_suites"]
            )
        )
    native_command = build_template_pytest_command(["c"], run_native_toolchain=True)
    if "test/template/c/test_native_toolchain_alignment.py" not in native_command:
        raise TemplateSuiteRunnerError(
            "native toolchain opt-in did not include the C native alignment target"
        )
    if "--run-native-toolchain" not in native_command:
        raise TemplateSuiteRunnerError(
            "native toolchain opt-in did not pass pytest's explicit opt-in flag"
        )
    try:
        build_template_pytest_command(["python"], run_native_toolchain=True)
    except TemplateSuiteRunnerError:
        pass
    else:
        raise TemplateSuiteRunnerError(
            "native toolchain opt-in without a C-family suite did not fail"
        )
    try:
        build_template_pytest_command(["c"], pytest_args=["--run-native-toolchain"])
    except TemplateSuiteRunnerError:
        pass
    else:
        raise TemplateSuiteRunnerError(
            "raw pytest native opt-in passthrough did not fail"
        )
    try:
        build_template_pytest_command(
            ["c"],
            pytest_args=["--run-native-toolchain"],
            run_native_toolchain=True,
        )
    except TemplateSuiteRunnerError:
        pass
    else:
        raise TemplateSuiteRunnerError(
            "duplicate raw pytest native opt-in passthrough did not fail"
        )
    try:
        _selected_suites_from_inputs([], "", "local", "java", None)
    except TemplateSuiteDetectionError:
        pass
    else:
        raise TemplateSuiteRunnerError("unknown include suite did not fail")
    try:
        _selected_suites_from_inputs([], "", "local", None, "java")
    except TemplateSuiteDetectionError:
        pass
    else:
        raise TemplateSuiteRunnerError("unknown skip suite did not fail")
    try:
        _selected_suites_from_inputs([], "", "local", "", None)
    except TemplateSuiteDetectionError:
        pass
    else:
        raise TemplateSuiteRunnerError("empty include suite did not fail")
    try:
        _selected_suites_from_inputs([], "", "local", None, "")
    except TemplateSuiteDetectionError:
        pass
    else:
        raise TemplateSuiteRunnerError("empty skip suite did not fail")


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser for the template suite runner.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> _build_parser().prog
        'run_template_suites'
    """
    parser = argparse.ArgumentParser(
        prog="run_template_suites",
        description="Run selected pyfcstm built-in template pytest suites.",
    )
    parser.add_argument("--changed-files", help="Newline-delimited changed files list.")
    parser.add_argument(
        "--commit-message-file", help="Message file to scan for [tpl:*] labels."
    )
    parser.add_argument(
        "--event-name",
        choices=("push", "pull_request", "workflow_dispatch", "local"),
        default="local",
        help="Detector event source, defaults to local.",
    )
    parser.add_argument(
        "--include-suites", help="Comma-separated suite include override."
    )
    parser.add_argument("--skip-suites", help="Comma-separated suite skip override.")
    parser.add_argument(
        "--run-native-toolchain",
        action="store_true",
        help=(
            "Append explicit native toolchain tests for selected C-family "
            "suites and pass pytest opt-in."
        ),
    )
    parser.add_argument(
        "--no-package",
        action="store_true",
        help="Do not refresh packaged built-in templates before running pytest.",
    )
    parser.add_argument(
        "--pytest-args",
        action="append",
        default=[],
        dest="pytest_args_option",
        help="Shell-like pytest arguments appended to the generated command.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the command only."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print JSON details for the selected run."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the repository-tool self-check instead of pytest.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra pytest args. Prefix with -- to separate runner args.",
    )
    return parser


def _split_pytest_arg_texts(texts: Sequence[str]) -> List[str]:
    """
    Split shell-like ``--pytest-args`` values into pytest arguments.

    :param texts: Shell-like argument strings supplied to ``--pytest-args``.
    :type texts: collections.abc.Sequence[str]
    :return: Parsed pytest arguments.
    :rtype: list[str]
    :raises ValueError: If one argument string has invalid shell quoting.

    Example::

        >>> _split_pytest_arg_texts(['-q -k "runtime"'])
        ['-q', '-k', 'runtime']
    """
    values = []
    for text in texts:
        values.extend(shlex.split(text))
    return values


def _clean_pytest_args(args: Sequence[str]) -> List[str]:
    """
    Normalize passthrough pytest arguments.

    :param args: Raw remainder arguments from :mod:`argparse`.
    :type args: collections.abc.Sequence[str]
    :return: Arguments with one leading ``--`` separator removed.
    :rtype: list[str]

    Example::

        >>> _clean_pytest_args(['--', '-q'])
        ['-q']
    """
    values = list(args)
    if values and values[0] == "--":
        return values[1:]
    return values


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the template suite runner command-line interface.

    :param argv: Optional argument vector without the program name. ``None``
        reads :data:`sys.argv`.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process-style exit code.
    :rtype: int

    Example::

        $ python tools/run_template_suites.py --check
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.check:
        try:
            run_self_check()
        except (TemplateSuiteDetectionError, TemplateSuiteRunnerError) as err:
            # TemplateSuiteDetectionError: detector compatibility self-check failed.
            # TemplateSuiteRunnerError: runner mapping self-check failed.
            parser.exit(2, "run_template_suites: {0}\n".format(err))
        sys.stdout.write("template suite runner self-check passed\n")
        return 0

    try:
        changed_files = _read_changed_files(args.changed_files)
        message = _read_message(args.commit_message_file)
    except (OSError, UnicodeError) as err:
        # OSError: optional input files cannot be read.
        # UnicodeError: input files must be UTF-8 text.
        parser.exit(3, "run_template_suites: cannot read input file: {0}\n".format(err))

    include_suites = args.include_suites
    if include_suites is None:
        include_suites = os.environ.get("PYFCSTM_TEMPLATE_SUITES", "default")
    skip_suites = args.skip_suites
    if skip_suites is None:
        skip_suites = os.environ.get("PYFCSTM_SKIP_TEMPLATE_SUITES")

    try:
        detector_result = _selected_suites_from_inputs(
            changed_files=changed_files,
            message=message,
            event_name=args.event_name,
            include_suites=include_suites,
            skip_suites=skip_suites,
        )
        selected_suites = list(detector_result["selected_suites"])
        run_native = _native_toolchain_enabled(
            os.environ.get("PYFCSTM_RUN_NATIVE_TOOLCHAIN"), args.run_native_toolchain
        )
        pytest_args = _split_pytest_arg_texts(args.pytest_args_option)
        pytest_args.extend(_clean_pytest_args(args.pytest_args))
        command = build_template_pytest_command(
            selected_suites,
            pytest_args=pytest_args,
            run_native_toolchain=run_native,
        )
    except (TemplateSuiteDetectionError, TemplateSuiteRunnerError, ValueError) as err:
        # TemplateSuiteDetectionError: PR-1 detector rejected labels/suites/events.
        # TemplateSuiteRunnerError: selected suites cannot be mapped to pytest.
        # ValueError: shlex rejected malformed --pytest-args quoting.
        parser.exit(2, "run_template_suites: {0}\n".format(err))

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "detector": detector_result,
        "selected_suites": selected_suites,
        "command": command,
        "command_text": _format_command(command),
        "target_count": len(
            expand_template_pytest_targets(
                selected_suites,
                run_native_toolchain=run_native,
            )
        ),
        "run_native_toolchain": run_native,
    }
    if args.json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write("template_suites={0}\n".format(",".join(selected_suites)))
        sys.stdout.write("pytest_command={0}\n".format(payload["command_text"]))

    if args.dry_run:
        return 0

    repo_root = _repo_root()
    if not args.no_package:
        try:
            _package_templates(repo_root)
        except (OSError, ValueError) as err:
            # OSError: package output cannot be written.
            # ValueError: package_templates validates template reuse stubs.
            parser.exit(
                4, "run_template_suites: cannot package templates: {0}\n".format(err)
            )

    sys.stdout.flush()
    return subprocess.call(command, cwd=repo_root, env=_runner_environment(run_native))


if __name__ == "__main__":
    raise SystemExit(main())
