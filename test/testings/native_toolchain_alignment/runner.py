"""
Pytest runner for native toolchain semantic alignment.

This module drives one shared semantic fixture through a generated C-family
runtime, a case-specific C harness, a concrete native toolchain profile, and a
Python-side public-observation assertion pass. The runner is opt-in only and is
used by template-side ``native_toolchain`` pytest files.

The module contains:

* :class:`NativeToolchainExecutionError` - Wrapper for native build, run, and
  analysis failures.
* :func:`run_native_toolchain_case` - Execute one case/profile/template tuple.
* :func:`assert_observations_match_case` - Compare harness observations with the
  shared public fixture expectations.

Example::

    >>> from test.testings.simulate_semantics import load_semantic_case
    >>> from test.testings.native_toolchain_alignment.profiles import get_profile
    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> profile = get_profile("linux-gcc-o2")
    >>> profile.name
    'linux-gcc-o2'
"""

import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template
from test.testings import simulate_semantics
from test.testings.native_toolchain_alignment.harness import (
    render_cmake_project,
    render_harness,
)
from test.testings.native_toolchain_alignment.profiles import (
    BUILD_MODE_ANALYZE_ONLY,
    BUILD_MODE_CMAKE_RUN,
    BUILD_MODE_COMPILE_ONLY,
    BUILD_MODE_CROSS_QEMU_RUN,
    BUILD_MODE_SELF_HOSTED_COMPILE,
    ToolchainMissingError,
    ToolchainProfile,
    ensure_required_tools,
)
from test.testings.native_toolchain_alignment.report import (
    NativeCommandRecord,
    NativeToolchainResult,
    read_observations_jsonl,
    validate_result_data,
    write_json_file,
)
from test.testings.simulate_semantics import SemanticCase


class NativeToolchainExecutionError(AssertionError):
    """
    Raised when a native toolchain case cannot satisfy fixture expectations.

    :param args: Error message arguments accepted by :class:`AssertionError`.
    :type args: object

    Example::

        >>> "case" in str(NativeToolchainExecutionError("case failed"))
        True
    """


class _StateView:
    def __init__(self, path: Optional[str]):
        self.path = tuple(path.split(".")) if path is not None else None


class _ObservationRuntime:
    def __init__(self, observation: Mapping[str, Any]):
        self._observation = observation

    @property
    def vars(self) -> Mapping[str, Any]:
        """
        Return the public variable snapshot from one native observation.

        :return: Mapping from variable name to observed value.
        :rtype: typing.Mapping[str, typing.Any]

        Example::

            >>> _ObservationRuntime({"vars": {"counter": 1}, "is_ended": False, "current_state": None}).vars
            {'counter': 1}
        """
        return self._observation["vars"]

    @property
    def is_ended(self) -> bool:
        """
        Return whether the native runtime reported terminal completion.

        :return: ``True`` when the observation represents an ended machine.
        :rtype: bool

        Example::

            >>> _ObservationRuntime({"vars": {}, "is_ended": True, "current_state": None}).is_ended
            True
        """
        return bool(self._observation["is_ended"])

    @property
    def current_state(self) -> Optional[_StateView]:
        """
        Return the observed active state path as a lightweight state view.

        :return: State view for active machines, or ``None`` for ended machines.
        :rtype: _StateView or None

        Example::

            >>> runtime = _ObservationRuntime({"vars": {}, "is_ended": False, "current_state": "Root.A"})
            >>> runtime.current_state.path
            ('Root', 'A')
        """
        if self.is_ended or self._observation["current_state"] is None:
            return None
        return _StateView(self._observation["current_state"])


def _template_utils(template_name: str):
    if template_name in ("c", "cpp"):
        from test.template.c import _utils as template_utils
    elif template_name in ("c_poll", "cpp_poll"):
        from test.template.c_poll import _utils as template_utils
    else:
        raise ValueError("unsupported native toolchain template: %r" % template_name)
    return template_utils


def _case_artifact_dir(
    root_dir: str, template_name: str, profile_name: str, case_id: str
) -> str:
    return os.path.join(os.path.abspath(root_dir), template_name, profile_name, case_id)


def _relative(path: Optional[str], root: str) -> Optional[str]:
    if path is None:
        return None
    return os.path.relpath(path, root).replace(os.sep, "/")


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _tool_stem(argv: Sequence[str]) -> str:
    if not argv:
        return ""
    return os.path.splitext(os.path.basename(argv[0]))[0].lower()


def _run_command(
    stage: str,
    argv: Sequence[str],
    cwd: str,
    logs_dir: str,
    artifact_root: str,
    commands: List[NativeCommandRecord],
    timeout: int,
    env: Optional[Mapping[str, str]] = None,
) -> subprocess.CompletedProcess:
    start = time.time()
    stdout_path = os.path.join(logs_dir, "%s.stdout.txt" % stage)
    stderr_path = os.path.join(logs_dir, "%s.stderr.txt" % stage)
    timed_out = False
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)
    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired as err:
        # TimeoutExpired: subprocess.run raises it when the configured command
        # timeout expires; the timeout itself is an expected native-profile
        # outcome and is converted into a structured command record.
        timed_out = True
        stdout = err.stdout or ""
        stderr = err.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        completed = subprocess.CompletedProcess(list(argv), None, stdout, stderr)
    duration = time.time() - start
    _write_text(stdout_path, completed.stdout or "")
    _write_text(stderr_path, completed.stderr or "")
    commands.append(
        NativeCommandRecord(
            stage=stage,
            argv=list(argv),
            cwd=cwd,
            returncode=completed.returncode,
            duration_seconds=duration,
            stdout_path=_relative(stdout_path, artifact_root),
            stderr_path=_relative(stderr_path, artifact_root),
            timed_out=timed_out,
        )
    )
    return completed


def _version_text(
    argv: Sequence[str],
    logs_dir: str,
    artifact_root: str,
    commands: List[NativeCommandRecord],
    timeout: int,
) -> Optional[str]:
    if not argv:
        return None
    if shutil.which(argv[0]) is None:
        return None
    executable = _tool_stem(argv)
    version_flag = "/?" if executable in {"cl", "clang-cl"} else "--version"
    completed = _run_command(
        "version",
        list(argv) + [version_flag],
        artifact_root,
        logs_dir,
        artifact_root,
        commands,
        timeout,
    )
    output = (completed.stdout or completed.stderr or "").strip()
    return output.splitlines()[0] if output else None


def _write_result(artifact_dir: str, result: NativeToolchainResult) -> Dict[str, Any]:
    data = result.to_dict()
    validate_result_data(data)
    write_json_file(os.path.join(artifact_dir, "result.json"), data)
    write_json_file(os.path.join(artifact_dir, "commands.json"), data["commands"])
    return data


def _artifact_paths(
    observations_path: Optional[str] = None, analysis_report_path: Optional[str] = None
) -> Sequence[str]:
    paths = [
        "generated",
        "harness",
        "build",
        "logs",
        "commands.json",
        "result.json",
    ]
    if observations_path is not None:
        paths.append(observations_path)
    if analysis_report_path is not None:
        paths.append(analysis_report_path)
    return paths


def _result_payload(
    case: SemanticCase,
    template_name: str,
    profile: ToolchainProfile,
    status: str,
    classification: str,
    message: str,
    commands: Sequence[NativeCommandRecord],
    returncode: Optional[int] = None,
    duration_seconds: float = 0.0,
    compiler_version: Optional[str] = None,
    primary_tool_version: Optional[str] = None,
    run_attempted: bool = False,
    observations_path: Optional[str] = None,
    analysis_report_path: Optional[str] = None,
) -> NativeToolchainResult:
    return NativeToolchainResult(
        case_id=case.id,
        template_name=template_name,
        profile_name=profile.name,
        build_mode=profile.build_mode,
        compiler=profile.compiler,
        compiler_version=compiler_version,
        primary_tool=profile.primary_tool,
        primary_tool_version=primary_tool_version,
        optimization=profile.optimization,
        status=status,
        classification=classification,
        message=message,
        returncode=returncode,
        duration_seconds=duration_seconds,
        commands=commands,
        artifact_paths=_artifact_paths(observations_path, analysis_report_path),
        run_attempted=run_attempted,
        observations_path=observations_path,
        analysis_ruleset=profile.analysis_ruleset,
        analysis_report_path=analysis_report_path,
        report_only=profile.report_only,
    )


def _failure_result(
    case: SemanticCase,
    template_name: str,
    profile: ToolchainProfile,
    classification: str,
    message: str,
    commands: Sequence[NativeCommandRecord],
    artifact_dir: str,
    returncode: Optional[int] = None,
    duration_seconds: float = 0.0,
    compiler_version: Optional[str] = None,
    primary_tool_version: Optional[str] = None,
    run_attempted: bool = False,
    observations_path: Optional[str] = None,
    analysis_report_path: Optional[str] = None,
) -> Dict[str, Any]:
    result = _result_payload(
        case,
        template_name,
        profile,
        "failed",
        classification,
        message,
        commands,
        returncode,
        duration_seconds,
        compiler_version,
        primary_tool_version,
        run_attempted,
        observations_path,
        analysis_report_path,
    )
    _write_result(artifact_dir, result)
    raise NativeToolchainExecutionError(
        message + "\nresult.json: " + os.path.join(artifact_dir, "result.json")
    )


def _assert_expected_exception_from_observation(
    observation: Mapping[str, Any],
    expect: Mapping[str, Any],
    case: SemanticCase,
    field_path: str,
    template_name: str,
) -> None:
    message = observation.get("last_error")
    assert message, "%s %s expected native error" % (case.id, field_path)
    template_utils = _template_utils(template_name)
    error, cause = template_utils._runtime_exception_from_message(message)
    if cause is not None:
        try:
            raise error from cause
        except type(error) as err:
            # type(error): _runtime_exception_from_message builds the precise
            # template-side exception class expected for this public diagnostic.
            simulate_semantics._assert_exception(err, expect, case, field_path)
    else:
        simulate_semantics._assert_exception(error, expect, case, field_path)


def assert_observations_match_case(
    template_name: str, case: SemanticCase, observations: Sequence[Mapping[str, Any]]
) -> None:
    """
    Compare native harness observations with a shared semantic fixture.

    :param template_name: Template name used to map native runtime diagnostics.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param observations: Parsed ``observations.jsonl`` records.
    :type observations: typing.Sequence[typing.Mapping[str, typing.Any]]
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If observations differ from fixture expectations.

    Example::

        >>> case = simulate_semantics.load_semantic_case("design_basic_simple_transition")
        >>> try:
        ...     assert_observations_match_case("c", case, [])
        ... except AssertionError as err:
        ...     "observation count mismatch" in str(err)
        True
    """
    initial_expect = simulate_semantics._initial_constructor_expect(case)
    init_observations = [item for item in observations if item.get("phase") == "init"]
    if initial_expect is not None:
        assert len(init_observations) == 1, (
            "%s initial observation count mismatch: %d != 1"
            % (case.id, len(init_observations))
        )
        _assert_expected_exception_from_observation(
            init_observations[0],
            initial_expect,
            case,
            "initial.expect.raises",
            template_name,
        )
        return
    assert not init_observations, (
        "%s produced unexpected initial error observations: %r"
        % (
            case.id,
            init_observations,
        )
    )

    steps = case.data.get("steps") or []
    step_observations = [item for item in observations if item.get("phase") == "step"]
    assert len(step_observations) == len(steps), (
        "%s observation count mismatch: %d != %d"
        % (case.id, len(step_observations), len(steps))
    )
    for index, step in enumerate(steps):
        observation = step_observations[index]
        expect = step.get("expect") or {}
        field_path = "steps[%d].expect" % index
        if "raises" in expect:
            _assert_expected_exception_from_observation(
                observation,
                expect,
                case,
                field_path + ".raises",
                template_name,
            )
        else:
            assert observation.get("last_error") in (None, ""), (
                "%s step %d expected no native runtime error, got last_error=%r"
                % (case.id, index, observation.get("last_error"))
            )
            api_return = observation.get("api_return")
            if api_return is not None:
                assert api_return == 1, (
                    "%s step %d expected successful native API return, got %r"
                    % (case.id, index, api_return)
                )
        runtime = _ObservationRuntime(observation)
        simulate_semantics._assert_runtime_expectation(
            runtime,
            expect,
            case,
            field_path,
            handler_calls=observation.get("handler_calls", []),
        )


def _render_generated_template(
    template_name: str, case: SemanticCase, generated_dir: str
) -> None:
    model = simulate_semantics.build_state_machine_from_case(case)
    extract_root = os.path.join(os.path.dirname(generated_dir), "template-src")
    template_dir = extract_template(template_name, extract_root)
    StateMachineCodeRenderer(template_dir).render(model=model, output_dir=generated_dir)


def _prepare_artifacts(
    template_name: str, case: SemanticCase, artifact_dir: str
) -> None:
    generated_dir = os.path.join(artifact_dir, "generated")
    harness_dir = os.path.join(artifact_dir, "harness")
    _render_generated_template(template_name, case, generated_dir)
    context = render_harness(
        template_name, case, os.path.join(harness_dir, "harness.c")
    )
    render_cmake_project(context, os.path.join(harness_dir, "CMakeLists.txt"))
    for name in ("machine.c", "machine.h", "README.md", "README_zh.md"):
        src = os.path.join(generated_dir, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(harness_dir, name))


def _cmake_configure_args(
    profile: ToolchainProfile, harness_dir: str, build_dir: str
) -> List[str]:
    args = ["cmake", "-S", harness_dir, "-B", build_dir]
    if profile.cmake_generator is not None:
        args.extend(["-G", profile.cmake_generator])
    args.extend(
        [
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_C_COMPILER=%s" % profile.cc[0],
            "-DCMAKE_CXX_COMPILER=%s" % profile.cxx[0],
            "-DPYFCSTM_NATIVE_C_FLAGS=%s" % " ".join(profile.c_flags),
            "-DPYFCSTM_NATIVE_CXX_FLAGS=%s" % " ".join(profile.cxx_flags),
            "-DPYFCSTM_NATIVE_LINK_FLAGS=%s" % " ".join(profile.link_flags),
        ]
    )
    args.extend(profile.cmake_args)
    return args


def _executable_path(build_dir: str) -> str:
    candidates = [
        os.path.join(build_dir, "native_harness"),
        os.path.join(build_dir, "native_harness.exe"),
        os.path.join(build_dir, "Release", "native_harness.exe"),
        os.path.join(build_dir, "Debug", "native_harness.exe"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[1] if os.name == "nt" else candidates[0]


def _run_compile_command(
    profile: ToolchainProfile,
    stage: str,
    argv: Sequence[str],
    artifact_dir: str,
    logs_dir: str,
    commands: List[NativeCommandRecord],
    output_path: str,
    start: float,
    case: SemanticCase,
    template_name: str,
    compiler_version: Optional[str],
    primary_tool_version: Optional[str],
) -> None:
    completed = _run_command(
        stage,
        argv,
        artifact_dir,
        logs_dir,
        artifact_dir,
        commands,
        profile.timeout_seconds,
    )
    timed_out = commands[-1].timed_out if commands else False
    if completed.returncode != 0:
        _failure_result(
            case,
            template_name,
            profile,
            "compile_timeout" if timed_out else "compile_failure",
            "%s failed for %s/%s" % (stage, template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
        )
    if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
        _failure_result(
            case,
            template_name,
            profile,
            "compile_failure",
            "%s did not produce a non-empty object for %s/%s"
            % (stage, template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
        )


def _run_compile_only_case(
    template_name: str,
    case: SemanticCase,
    profile: ToolchainProfile,
    artifact_dir: str,
    logs_dir: str,
    build_dir: str,
    commands: List[NativeCommandRecord],
    compiler_version: Optional[str],
    primary_tool_version: Optional[str],
    start: float,
) -> Dict[str, Any]:
    include_dir = os.path.join(artifact_dir, "harness")
    if _tool_stem(profile.cc) in {"cl", "clang-cl"}:
        include_flag = "/I" + include_dir

        def c_output(path):
            """Return an MSVC-style output argument for one object file."""
            return ["/Fo" + path]

        cxx_output = c_output
        compile_flag = "/c"
    else:
        include_flag = "-I" + include_dir

        def c_output(path):
            """Return a GCC-style output argument for one object file."""
            return ["-o", path]

        cxx_output = c_output
        compile_flag = "-c"
    compile_items = [
        (
            "compile-machine-c",
            list(profile.cc)
            + list(profile.c_flags)
            + [
                include_flag,
                compile_flag,
                os.path.join(artifact_dir, "harness", "machine.c"),
            ],
            os.path.join(build_dir, "machine.o"),
        ),
        (
            "compile-harness-c",
            list(profile.cc)
            + list(profile.c_flags)
            + [
                include_flag,
                compile_flag,
                os.path.join(artifact_dir, "harness", "harness.c"),
            ],
            os.path.join(build_dir, "harness.o"),
        ),
        (
            "compile-header-cxx",
            list(profile.cxx)
            + list(profile.cxx_flags)
            + [include_flag, compile_flag, "-"],
            os.path.join(build_dir, "cxx_header_probe.o"),
        ),
    ]
    header_probe = '#include "machine.h"\nint main(void) { return 0; }\n'
    for stage, argv, output_path in compile_items:
        argv = list(argv) + c_output(output_path)
        if stage == "compile-header-cxx":
            probe_path = os.path.join(build_dir, "cxx_header_probe.cpp")
            _write_text(probe_path, header_probe)
            argv = (
                list(profile.cxx)
                + list(profile.cxx_flags)
                + [include_flag, compile_flag, probe_path]
                + cxx_output(output_path)
            )
        _run_compile_command(
            profile,
            stage,
            argv,
            artifact_dir,
            logs_dir,
            commands,
            output_path,
            start,
            case,
            template_name,
            compiler_version,
            primary_tool_version,
        )
    result = _result_payload(
        case,
        template_name,
        profile,
        "passed",
        "passed",
        "compile-only passed",
        commands,
        0,
        time.time() - start,
        compiler_version,
        primary_tool_version,
        run_attempted=False,
        observations_path=None,
    )
    return _write_result(artifact_dir, result)


def _analysis_targets(artifact_dir: str) -> List[str]:
    """Return generated and harness source files for static-analysis profiles."""
    targets = []
    for relative_dir in ("generated", "harness"):
        root = os.path.join(artifact_dir, relative_dir)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in sorted(filenames):
                if os.path.splitext(filename)[1].lower() in {".c", ".h"}:
                    targets.append(os.path.join(dirpath, filename))
    return sorted(targets)


def _analysis_argv(profile: ToolchainProfile, artifact_dir: str) -> List[str]:
    args = list(profile.analysis_args)
    targets = _analysis_targets(artifact_dir)
    if "--" not in args:
        return list(profile.analysis_tool) + args + targets
    separator_index = args.index("--")
    return (
        list(profile.analysis_tool)
        + args[:separator_index]
        + targets
        + ["--"]
        + args[separator_index + 1 :]
    )


def _run_analyze_only_case(
    template_name: str,
    case: SemanticCase,
    profile: ToolchainProfile,
    artifact_dir: str,
    logs_dir: str,
    commands: List[NativeCommandRecord],
    primary_tool_version: Optional[str],
    start: float,
) -> Dict[str, Any]:
    report_path = os.path.join(artifact_dir, "analysis-report.txt")
    argv = _analysis_argv(profile, artifact_dir)
    completed = _run_command(
        "analyze",
        argv,
        artifact_dir,
        logs_dir,
        artifact_dir,
        commands,
        profile.timeout_seconds,
    )
    stdout_rel = commands[-1].stdout_path if commands else None
    stderr_rel = commands[-1].stderr_path if commands else None
    report_parts = []
    for rel_path in (stdout_rel, stderr_rel):
        if rel_path is None:
            continue
        path = os.path.join(artifact_dir, rel_path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                report_parts.append(f.read())
    _write_text(report_path, "\n".join(report_parts))
    report_rel = _relative(report_path, artifact_dir)
    timed_out = commands[-1].timed_out if commands else False
    if timed_out or completed.returncode is None:
        _failure_result(
            case,
            template_name,
            profile,
            "analysis_timeout",
            "static analysis timed out for %s/%s" % (template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            primary_tool_version=primary_tool_version,
            analysis_report_path=report_rel,
        )
    if completed.returncode not in (0,):
        _failure_result(
            case,
            template_name,
            profile,
            "analysis_failure",
            "static analysis failed for %s/%s with return code %r"
            % (template_name, case.id, completed.returncode),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            primary_tool_version=primary_tool_version,
            analysis_report_path=report_rel,
        )
    if not os.path.exists(report_path):
        _failure_result(
            case,
            template_name,
            profile,
            "analysis_failure",
            "static analysis report is missing for %s/%s" % (template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            primary_tool_version=primary_tool_version,
            analysis_report_path=report_rel,
        )
    result = _result_payload(
        case,
        template_name,
        profile,
        "passed",
        "analysis_report_only",
        "static analysis report-only profile completed",
        commands,
        completed.returncode,
        time.time() - start,
        compiler_version=None,
        primary_tool_version=primary_tool_version,
        run_attempted=False,
        observations_path=None,
        analysis_report_path=report_rel,
    )
    return _write_result(artifact_dir, result)


def _run_cmake_case(
    template_name: str,
    case: SemanticCase,
    profile: ToolchainProfile,
    artifact_dir: str,
    logs_dir: str,
    build_dir: str,
    harness_dir: str,
    commands: List[NativeCommandRecord],
    compiler_version: Optional[str],
    primary_tool_version: Optional[str],
    start: float,
) -> Dict[str, Any]:
    completed = _run_command(
        "configure",
        _cmake_configure_args(profile, harness_dir, build_dir),
        artifact_dir,
        logs_dir,
        artifact_dir,
        commands,
        profile.timeout_seconds,
    )
    if completed.returncode != 0:
        timed_out = commands[-1].timed_out if commands else False
        _failure_result(
            case,
            template_name,
            profile,
            "configure_timeout" if timed_out else "configure_failure",
            "cmake configure failed for %s/%s" % (template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
        )

    completed = _run_command(
        "build",
        ["cmake", "--build", build_dir, "--config", "Release"],
        artifact_dir,
        logs_dir,
        artifact_dir,
        commands,
        profile.timeout_seconds,
    )
    if completed.returncode != 0:
        timed_out = commands[-1].timed_out if commands else False
        _failure_result(
            case,
            template_name,
            profile,
            "build_timeout" if timed_out else "build_failure",
            "cmake build failed for %s/%s" % (template_name, case.id),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
        )

    exe_path = _executable_path(build_dir)
    observations_path = os.path.join(artifact_dir, "observations.jsonl")
    run_argv = list(profile.run_prefix) + [exe_path, observations_path]
    completed = _run_command(
        "run",
        run_argv,
        artifact_dir,
        logs_dir,
        artifact_dir,
        commands,
        profile.timeout_seconds,
        env=profile.run_environment,
    )
    observations_rel = _relative(observations_path, artifact_dir)
    if completed.returncode != 0:
        timed_out = commands[-1].timed_out if commands else False
        if timed_out:
            classification = "run_timeout"
        elif completed.returncode is not None and completed.returncode > 0:
            classification = "run_failure"
        else:
            classification = "native_crash"
        _failure_result(
            case,
            template_name,
            profile,
            classification,
            "native harness failed for %s/%s with return code %r"
            % (template_name, case.id, completed.returncode),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
            run_attempted=True,
            observations_path=observations_rel,
        )

    observations = read_observations_jsonl(observations_path)
    try:
        assert_observations_match_case(template_name, case, observations)
    except AssertionError as err:
        _failure_result(
            case,
            template_name,
            profile,
            "runtime_mismatch",
            str(err),
            commands,
            artifact_dir,
            completed.returncode,
            time.time() - start,
            compiler_version,
            primary_tool_version,
            run_attempted=True,
            observations_path=observations_rel,
        )

    result = _result_payload(
        case,
        template_name,
        profile,
        "passed",
        "passed",
        "passed",
        commands,
        completed.returncode,
        time.time() - start,
        compiler_version,
        primary_tool_version,
        run_attempted=True,
        observations_path=observations_rel,
    )
    return _write_result(artifact_dir, result)


def run_native_toolchain_case(
    template_name: str,
    case: SemanticCase,
    profile: ToolchainProfile,
    artifact_root: str,
) -> Dict[str, Any]:
    """
    Execute one shared semantic fixture under a native toolchain profile.

    :param template_name: Template name, either ``"c"`` or ``"c_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param profile: Selected native toolchain profile.
    :type profile: test.testings.native_toolchain_alignment.profiles.ToolchainProfile
    :param artifact_root: Root directory for result artifacts.
    :type artifact_root: str
    :return: Parsed ``result.json`` data for a passed case.
    :rtype: dict
    :raises NativeToolchainExecutionError: If profile setup, build, run,
        analysis, or semantic assertion fails.

    Example::

        >>> from test.testings.native_toolchain_alignment.profiles import get_profile
        >>> profile = get_profile("linux-gcc-o2")
        >>> profile.build_mode
        'cmake-run'
    """
    start = time.time()
    artifact_dir = _case_artifact_dir(
        artifact_root, template_name, profile.name, case.id
    )
    logs_dir = os.path.join(artifact_dir, "logs")
    build_dir = os.path.join(artifact_dir, "build")
    harness_dir = os.path.join(artifact_dir, "harness")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)
    commands: List[NativeCommandRecord] = []

    try:
        ensure_required_tools(profile)
    except ToolchainMissingError as err:
        # ToolchainMissingError: ensure_required_tools reports profile binaries
        # that are absent from PATH. Other exceptions indicate a bug in profile
        # validation and should propagate.
        _failure_result(
            case,
            template_name,
            profile,
            "tool_missing",
            "%s" % err,
            commands,
            artifact_dir,
            duration_seconds=time.time() - start,
        )

    _prepare_artifacts(template_name, case, artifact_dir)
    compiler_version = _version_text(
        profile.cc, logs_dir, artifact_dir, commands, profile.timeout_seconds
    )
    if profile.analysis_tool:
        primary_tool_version = _version_text(
            profile.analysis_tool,
            logs_dir,
            artifact_dir,
            commands,
            profile.timeout_seconds,
        )
    else:
        primary_tool_version = compiler_version

    if profile.build_mode in (BUILD_MODE_CMAKE_RUN, BUILD_MODE_CROSS_QEMU_RUN):
        return _run_cmake_case(
            template_name,
            case,
            profile,
            artifact_dir,
            logs_dir,
            build_dir,
            harness_dir,
            commands,
            compiler_version,
            primary_tool_version,
            start,
        )
    if profile.build_mode in (BUILD_MODE_COMPILE_ONLY, BUILD_MODE_SELF_HOSTED_COMPILE):
        return _run_compile_only_case(
            template_name,
            case,
            profile,
            artifact_dir,
            logs_dir,
            build_dir,
            commands,
            compiler_version,
            primary_tool_version,
            start,
        )
    if profile.build_mode == BUILD_MODE_ANALYZE_ONLY:
        return _run_analyze_only_case(
            template_name,
            case,
            profile,
            artifact_dir,
            logs_dir,
            commands,
            primary_tool_version,
            start,
        )
    _failure_result(
        case,
        template_name,
        profile,
        "profile_error",
        "unsupported native toolchain build mode: %s" % profile.build_mode,
        commands,
        artifact_dir,
        duration_seconds=time.time() - start,
        compiler_version=compiler_version,
        primary_tool_version=primary_tool_version,
    )
