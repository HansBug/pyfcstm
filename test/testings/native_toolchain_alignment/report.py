"""
JSON report contracts for native toolchain semantic alignment.

This module defines the first-version result, command, and observation schema
used by the native toolchain pytest helper. The schema is intentionally test
local: generated C/C poll artifacts write public observations, and Python-side
pytest code stores command logs and summary results beside the build artifacts.

The module contains:

* :class:`NativeCommandRecord` - One configure, build, run, or version command.
* :class:`NativeToolchainResult` - Serializable summary for one case/profile run.
* :func:`validate_result_data` - Validate the minimal ``result.json`` contract.
* :func:`validate_command_data` - Validate the minimal ``commands.json`` contract.
* :func:`read_observations_jsonl` - Load and validate observation records.

Example::

    >>> command = NativeCommandRecord("version", ["cc", "--version"], "/tmp")
    >>> command.to_dict()["stage"]
    'version'
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

SCHEMA_VERSION = "1"

COMMAND_REQUIRED_FIELDS = {
    "stage",
    "argv",
    "cwd",
    "returncode",
    "duration_seconds",
    "stdout_path",
    "stderr_path",
    "timed_out",
}
RESULT_REQUIRED_FIELDS = {
    "schema_version",
    "case_id",
    "template_name",
    "profile_name",
    "build_mode",
    "compiler",
    "compiler_version",
    "primary_tool",
    "primary_tool_version",
    "optimization",
    "status",
    "classification",
    "message",
    "returncode",
    "duration_seconds",
    "commands",
    "artifact_paths",
    "run_attempted",
    "observations_path",
    "analysis_ruleset",
    "analysis_report_path",
    "report_only",
}
OBSERVATION_REQUIRED_FIELDS = {
    "schema_version",
    "case_id",
    "template_name",
    "phase",
    "step_index",
    "cycle_index",
    "events",
    "current_state",
    "is_ended",
    "vars",
    "handler_calls",
    "last_error",
    "api_return",
}
RESULT_STATUS_VALUES = {"passed", "failed", "error", "skipped"}
RESULT_CLASSIFICATION_VALUES = {
    "passed",
    "profile_error",
    "tool_missing",
    "configure_failure",
    "configure_timeout",
    "compile_failure",
    "compile_timeout",
    "build_failure",
    "build_timeout",
    "run_failure",
    "run_timeout",
    "runtime_mismatch",
    "native_crash",
    "analysis_failure",
    "analysis_timeout",
    "analysis_report_only",
}
COMMAND_STAGE_VALUES = {
    "version",
    "configure",
    "build",
    "run",
    "compile",
    "compile-machine-c",
    "compile-harness-c",
    "compile-header-cxx",
    "analyze",
}
OBSERVATION_PHASE_VALUES = {"init", "step", "error", "finish"}


def _is_string_or_none(value: Any) -> bool:
    return value is None or isinstance(value, str)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int_or_none(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


@dataclass(frozen=True)
class NativeCommandRecord:
    """
    Serializable record for one native toolchain command.

    :param stage: Command stage, such as ``"configure"`` or ``"run"``.
    :type stage: str
    :param argv: Argument-vector form of the command.
    :type argv: typing.Sequence[str]
    :param cwd: Working directory used for the command.
    :type cwd: str
    :param returncode: Process return code, defaults to ``None`` before a
        command has completed.
    :type returncode: int, optional
    :param duration_seconds: Command wall-clock duration in seconds, defaults
        to ``0.0``.
    :type duration_seconds: float, optional
    :param stdout_path: Relative path to stdout log, defaults to ``None``.
    :type stdout_path: str, optional
    :param stderr_path: Relative path to stderr log, defaults to ``None``.
    :type stderr_path: str, optional
    :param timed_out: Whether the command exceeded its timeout, defaults to
        ``False``.
    :type timed_out: bool, optional

    Example::

        >>> record = NativeCommandRecord("build", ["cmake", "--build", "."], "/tmp/build")
        >>> record.to_dict()["argv"][0]
        'cmake'
    """

    stage: str
    argv: Sequence[str]
    cwd: str
    returncode: Optional[int] = None
    duration_seconds: float = 0.0
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this command record to a JSON-serializable dictionary.

        :return: Command fields as a dictionary.
        :rtype: dict

        Example::

            >>> NativeCommandRecord("run", ["./case"], "/tmp").to_dict()["stage"]
            'run'
        """
        data = asdict(self)
        data["argv"] = list(self.argv)
        return data


@dataclass(frozen=True)
class NativeToolchainResult:
    """
    Serializable result for one native toolchain case execution.

    :param case_id: Shared semantic fixture case id.
    :type case_id: str
    :param template_name: Built-in template name, such as ``"c"`` or
        ``"c_poll"``.
    :type template_name: str
    :param profile_name: Native toolchain profile name.
    :type profile_name: str
    :param build_mode: Build mode, such as ``"cmake-run"``,
        ``"compile-only"``, or ``"analyze-only"``.
    :type build_mode: str
    :param compiler: C compiler command or ``None``.
    :type compiler: str, optional
    :param compiler_version: C compiler version text or ``None``.
    :type compiler_version: str, optional
    :param primary_tool: Main profile tool name.
    :type primary_tool: str
    :param primary_tool_version: Main tool version text or ``None``.
    :type primary_tool_version: str, optional
    :param optimization: Optimization flag such as ``"-O2"``.
    :type optimization: str, optional
    :param status: Result status, such as ``"passed"`` or ``"failed"``.
    :type status: str
    :param classification: Result classification.
    :type classification: str
    :param message: Human-readable result summary.
    :type message: str
    :param returncode: Primary failing return code, defaults to ``None``.
    :type returncode: int, optional
    :param duration_seconds: Total wall-clock duration, defaults to ``0.0``.
    :type duration_seconds: float, optional
    :param commands: Command records for this case.
    :type commands: typing.Sequence[NativeCommandRecord]
    :param artifact_paths: Relative artifact paths.
    :type artifact_paths: typing.Sequence[str]
    :param run_attempted: Whether the compiled executable was run.
    :type run_attempted: bool
    :param observations_path: Relative observation path or ``None``.
    :type observations_path: str, optional
    :param analysis_ruleset: Static-analysis ruleset or ``None``.
    :type analysis_ruleset: str, optional
    :param analysis_report_path: Static-analysis report path or ``None``.
    :type analysis_report_path: str, optional
    :param report_only: Whether the result is report-only.
    :type report_only: bool

    Example::

        >>> result = NativeToolchainResult(
        ...     "demo", "c", "linux-gcc-o2", "cmake-run", "gcc", "gcc 1",
        ...     "gcc", "gcc 1", "-O2", "passed", "passed", "ok",
        ... )
        >>> result.to_dict()["schema_version"]
        '1'
    """

    case_id: str
    template_name: str
    profile_name: str
    build_mode: str
    compiler: Optional[str]
    compiler_version: Optional[str]
    primary_tool: str
    primary_tool_version: Optional[str]
    optimization: Optional[str]
    status: str
    classification: str
    message: str
    returncode: Optional[int] = None
    duration_seconds: float = 0.0
    commands: Sequence[NativeCommandRecord] = field(default_factory=tuple)
    artifact_paths: Sequence[str] = field(default_factory=tuple)
    run_attempted: bool = False
    observations_path: Optional[str] = None
    analysis_ruleset: Optional[str] = None
    analysis_report_path: Optional[str] = None
    report_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this result to the ``result.json`` dictionary shape.

        :return: JSON-serializable result dictionary.
        :rtype: dict

        Example::

            >>> result = NativeToolchainResult(
            ...     "demo", "c", "p", "cmake-run", None, None, "cc", None,
            ...     None, "failed", "profile_error", "bad",
            ... )
            >>> result.to_dict()["classification"]
            'profile_error'
        """
        return {
            "schema_version": SCHEMA_VERSION,
            "case_id": self.case_id,
            "template_name": self.template_name,
            "profile_name": self.profile_name,
            "build_mode": self.build_mode,
            "compiler": self.compiler,
            "compiler_version": self.compiler_version,
            "primary_tool": self.primary_tool,
            "primary_tool_version": self.primary_tool_version,
            "optimization": self.optimization,
            "status": self.status,
            "classification": self.classification,
            "message": self.message,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "commands": [command.to_dict() for command in self.commands],
            "artifact_paths": list(self.artifact_paths),
            "run_attempted": self.run_attempted,
            "observations_path": self.observations_path,
            "analysis_ruleset": self.analysis_ruleset,
            "analysis_report_path": self.analysis_report_path,
            "report_only": self.report_only,
        }


def _missing_fields(
    data: Mapping[str, Any], required_fields: Iterable[str]
) -> List[str]:
    return sorted(set(required_fields) - set(data.keys()))


def validate_command_data(data: Mapping[str, Any]) -> None:
    """
    Validate one command record dictionary.

    :param data: Parsed command mapping.
    :type data: typing.Mapping[str, typing.Any]
    :return: ``None``.
    :rtype: None
    :raises ValueError: If required fields, enum values, or basic types are
        invalid.

    Example::

        >>> record = NativeCommandRecord("version", ["cc", "--version"], "/tmp")
        >>> validate_command_data(record.to_dict())
    """
    missing = _missing_fields(data, COMMAND_REQUIRED_FIELDS)
    if missing:
        raise ValueError("command record missing fields: %r" % missing)
    if data["stage"] not in COMMAND_STAGE_VALUES:
        raise ValueError("command stage is invalid: %r" % data["stage"])
    if not isinstance(data["argv"], list) or not all(
        isinstance(item, str) for item in data["argv"]
    ):
        raise ValueError("command argv must be a list of strings")
    if not isinstance(data["cwd"], str):
        raise ValueError("command cwd must be a string")
    if not _is_int_or_none(data["returncode"]):
        raise ValueError("command returncode must be an int or null")
    if not _is_number(data["duration_seconds"]):
        raise ValueError("command duration_seconds must be numeric")
    if data["stdout_path"] is not None and not isinstance(data["stdout_path"], str):
        raise ValueError("command stdout_path must be a string or null")
    if data["stderr_path"] is not None and not isinstance(data["stderr_path"], str):
        raise ValueError("command stderr_path must be a string or null")
    if not isinstance(data["timed_out"], bool):
        raise ValueError("command timed_out must be bool")


def validate_result_data(data: Mapping[str, Any]) -> None:
    """
    Validate one ``result.json`` dictionary.

    :param data: Parsed result mapping.
    :type data: typing.Mapping[str, typing.Any]
    :return: ``None``.
    :rtype: None
    :raises ValueError: If required fields, enum values, or nested command
        records are invalid.

    Example::

        >>> result = NativeToolchainResult(
        ...     "demo", "c", "p", "cmake-run", None, None, "cc", None,
        ...     None, "failed", "profile_error", "bad",
        ... )
        >>> validate_result_data(result.to_dict())
    """
    missing = _missing_fields(data, RESULT_REQUIRED_FIELDS)
    if missing:
        raise ValueError("result missing fields: %r" % missing)
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("result schema_version must be %r" % SCHEMA_VERSION)
    for key in (
        "case_id",
        "template_name",
        "profile_name",
        "build_mode",
        "primary_tool",
        "status",
        "classification",
        "message",
    ):
        if not isinstance(data[key], str):
            raise ValueError("result %s must be a string" % key)
    for key in (
        "compiler",
        "compiler_version",
        "primary_tool_version",
        "optimization",
        "analysis_ruleset",
        "analysis_report_path",
    ):
        if not _is_string_or_none(data[key]):
            raise ValueError("result %s must be a string or null" % key)
    if not _is_int_or_none(data["returncode"]):
        raise ValueError("result returncode must be an int or null")
    if not _is_number(data["duration_seconds"]):
        raise ValueError("result duration_seconds must be numeric")
    if data["status"] not in RESULT_STATUS_VALUES:
        raise ValueError("result status is invalid: %r" % data["status"])
    if data["classification"] not in RESULT_CLASSIFICATION_VALUES:
        raise ValueError(
            "result classification is invalid: %r" % data["classification"]
        )
    if not isinstance(data["commands"], list):
        raise ValueError("result commands must be a list")
    for command in data["commands"]:
        if not isinstance(command, dict):
            raise ValueError("result commands must contain objects")
        validate_command_data(command)
    if not isinstance(data["artifact_paths"], list):
        raise ValueError("result artifact_paths must be a list")
    if not all(isinstance(path, str) for path in data["artifact_paths"]):
        raise ValueError("result artifact_paths must contain strings")
    if not isinstance(data["run_attempted"], bool):
        raise ValueError("result run_attempted must be bool")
    if data["observations_path"] is not None and not isinstance(
        data["observations_path"], str
    ):
        raise ValueError("result observations_path must be a string or null")
    if not isinstance(data["report_only"], bool):
        raise ValueError("result report_only must be bool")


def validate_observation_data(data: Mapping[str, Any]) -> None:
    """
    Validate one observation JSON object.

    :param data: Parsed observation mapping.
    :type data: typing.Mapping[str, typing.Any]
    :return: ``None``.
    :rtype: None
    :raises ValueError: If required fields or basic types are invalid.

    Example::

        >>> validate_observation_data({
        ...     "schema_version": "1", "case_id": "demo", "template_name": "c",
        ...     "phase": "step", "step_index": 0, "cycle_index": 0,
        ...     "events": [], "current_state": "Root.A", "is_ended": False,
        ...     "vars": {}, "handler_calls": [], "last_error": None,
        ...     "api_return": 1,
        ... })
    """
    missing = _missing_fields(data, OBSERVATION_REQUIRED_FIELDS)
    if missing:
        raise ValueError("observation missing fields: %r" % missing)
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("observation schema_version must be %r" % SCHEMA_VERSION)
    for key in ("case_id", "template_name", "phase"):
        if not isinstance(data[key], str):
            raise ValueError("observation %s must be a string" % key)
    if data["phase"] not in OBSERVATION_PHASE_VALUES:
        raise ValueError("observation phase is invalid: %r" % data["phase"])
    if not _is_int_or_none(data["step_index"]):
        raise ValueError("observation step_index must be an int or null")
    if not _is_int_or_none(data["cycle_index"]):
        raise ValueError("observation cycle_index must be an int or null")
    if not isinstance(data["events"], list):
        raise ValueError("observation events must be a list")
    if not all(isinstance(event, str) for event in data["events"]):
        raise ValueError("observation events must contain strings")
    if not isinstance(data["vars"], dict):
        raise ValueError("observation vars must be an object")
    if not isinstance(data["handler_calls"], list):
        raise ValueError("observation handler_calls must be a list")
    if data["current_state"] is not None and not isinstance(data["current_state"], str):
        raise ValueError("observation current_state must be a string or null")
    if not isinstance(data["is_ended"], bool):
        raise ValueError("observation is_ended must be bool")
    if data["last_error"] is not None and not isinstance(data["last_error"], str):
        raise ValueError("observation last_error must be a string or null")
    if data["api_return"] is not None and not isinstance(data["api_return"], int):
        raise ValueError("observation api_return must be an int or null")


def write_json_file(path: str, data: Any) -> None:
    """
    Write formatted JSON to ``path``.

    :param path: Destination file path.
    :type path: str
    :param data: JSON-serializable data.
    :type data: typing.Any
    :return: ``None``.
    :rtype: None

    Example::

        >>> import tempfile, os, json
        >>> td = tempfile.mkdtemp()
        >>> path = os.path.join(td, "data.json")
        >>> write_json_file(path, {"ok": True})
        >>> json.load(open(path))["ok"]
        True
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def read_observations_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Read and validate an ``observations.jsonl`` file.

    :param path: JSON Lines observation file path.
    :type path: str
    :return: Observation dictionaries in file order.
    :rtype: list
    :raises ValueError: If a line is not a JSON object or violates the
        observation schema.

    Example::

        >>> import tempfile, os, json
        >>> td = tempfile.mkdtemp()
        >>> path = os.path.join(td, "observations.jsonl")
        >>> _ = open(path, "w").write(json.dumps({
        ...     "schema_version": "1", "case_id": "demo", "template_name": "c",
        ...     "phase": "step", "step_index": 0, "cycle_index": 0,
        ...     "events": [], "current_state": "Root.A", "is_ended": False,
        ...     "vars": {}, "handler_calls": [], "last_error": None,
        ...     "api_return": 1,
        ... }) + "\\n")
        >>> read_observations_jsonl(path)[0]["case_id"]
        'demo'
    """
    observations = []
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError("observation line %d must be an object" % line_number)
            validate_observation_data(data)
            observations.append(data)
    return observations
