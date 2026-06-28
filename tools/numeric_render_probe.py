"""
Provide probe entry points for numeric render-semantics research.

The lightweight ``env`` mode records local environment data without running
native workloads. The C-family smoke modes compile and execute small programs
whose expressions are rendered from the repository's R0
``render_mapping.json`` snapshot, so the probe follows the same renderer and
template facts that later exhaustive harnesses will use. Shared JSON, mapping,
and command-dispatch helpers are mode-neutral. The Python/Z3 baseline,
Java/Rust native smoke, and C/C++ to Z3 alignment modes join the same runner
without replacing the C-family modes. Smoke case identifiers are render-path
scoped; cross-artifact semantic joins should prefer the rendered FCSTM operator
and source expression, or a future explicit semantic identifier, while
render-path fields distinguish target-language outputs for the same semantic
expression.

The module contains:

* :func:`build_environment_report` - Collect lightweight local environment data.
* :func:`build_c_family_smoke_report` - Run C or C++ smoke cases from R0 mapping.
* :func:`build_python_z3_baseline` - Build the Python/Z3 capability baseline.
* :func:`check_python_z3_baseline` - Validate the generated or committed baseline.
* :func:`build_java_rust_smoke_report` - Build Java/Rust native smoke facts.
* :func:`check_java_rust_smoke` - Validate Java/Rust smoke contract invariants.
* :func:`build_c_cpp_z3_alignment` - Build the C/C++ to Z3 alignment snapshot.
* :func:`check_c_cpp_z3_alignment` - Validate the committed alignment snapshot.
* :func:`validate_probe_summary` - Validate the lightweight probe-summary contract.
* :func:`_stable_json` - Serialize research artifacts consistently.
* :func:`main` - Command-line entry point with ``env``, ``c-smoke``,
  ``cpp-smoke``, ``python-z3-baseline``, ``java-smoke``, ``rust-smoke``,
  ``java-rust-smoke`` and ``c-cpp-z3-alignment`` modes.

Example::

    >>> from tools.numeric_render_probe import build_environment_report
    >>> report = build_environment_report('.')
    >>> report['native_runner_enabled']
    False
    >>> from tools.numeric_render_probe import build_python_z3_baseline
    >>> baseline = build_python_z3_baseline('.')
    >>> baseline['language']
    'python-z3'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import jinja2

_REPO_ROOT_FOR_SCRIPT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_SCRIPT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_SCRIPT))

import z3  # noqa: E402

from pyfcstm.dsl.error import GrammarParseError  # noqa: E402
from pyfcstm.dsl import node as dsl_nodes  # noqa: E402
from pyfcstm.model.expr import parse_expr_from_string  # noqa: E402
from pyfcstm.render.expr import render_expr_node  # noqa: E402
from pyfcstm.render.render import StateMachineCodeRenderer  # noqa: E402
from pyfcstm.solver.expr import python_round_to_z3  # noqa: E402
from pyfcstm.utils import add_settings_for_env  # noqa: E402
from tools.numeric_render_mapping import build_render_mapping  # noqa: E402

_JSON_OBJECT = Dict[str, Any]
_RESEARCH_PATH = "research/numeric-render-semantics"
_DEFAULT_MAPPING_PATH = "%s/results/snapshots/render_mapping.json" % _RESEARCH_PATH
_PYTHON_Z3_BASELINE_SNAPSHOT = (
    "%s/results/snapshots/python_z3_baseline.json" % _RESEARCH_PATH
)
_PYTHON_Z3_BASELINE_SCHEMA = "%s/schemas/python_z3_baseline.schema.json" % (
    _RESEARCH_PATH
)
_C_CPP_Z3_ALIGNMENT_SNAPSHOT = (
    "%s/results/snapshots/c_cpp_z3_alignment.json" % _RESEARCH_PATH
)
_C_CPP_Z3_ALIGNMENT_SCHEMA = "%s/schemas/c_cpp_z3_alignment.schema.json" % (
    _RESEARCH_PATH
)
_JAVA_RUST_SMOKE_SNAPSHOT = "%s/results/snapshots/java_rust_smoke.json" % (
    _RESEARCH_PATH
)
_JAVA_RUST_SMOKE_SNAPSHOT_SHA256 = _JAVA_RUST_SMOKE_SNAPSHOT + ".sha256"
_JAVA_RUST_SMOKE_SCHEMA = "%s/schemas/java_rust_smoke.schema.json" % (_RESEARCH_PATH)
_NATIVE_ONLY_REASON = "no_java_or_rust_template_in_current_repository"
_JAVA_RUST_MODES = {"java-smoke", "rust-smoke", "java-rust-smoke"}
_NATIVE_SUMMARY_STATUSES = {
    "passed",
    "unavailable",
    "completed_with_findings",
    "completed",
    "skipped",
    "invalid",
}
_NATIVE_CASE_STATUS_OUTCOMES = {
    "passed": "observed",
    "compile_failed": "compile_failed",
    "runtime_failed": "runtime_trap",
    "skipped": "unavailable",
    "unavailable": "unavailable",
}
_JAVA_NON_PASSING_CASE_IDS = {
    "division_by_zero_exception",
    "math_add_exact_overflow",
    "math_multiply_exact_overflow",
    "math_sign_missing",
}
_RUST_ALWAYS_PASSING_CASE_IDS = {
    "cast_i32_to_i8",
    "checked_add_overflow",
    "overflowing_add_overflow",
    "plain_i32_bitwise_and",
    "plain_i32_division",
    "plain_i32_remainder",
    "powf_promotes_f64",
    "round_cast_i64",
    "saturating_add_overflow",
    "wrapping_add_overflow",
}
_RUST_PROFILE_SENSITIVE_TRAP_CASE_IDS = {
    "plain_i32_add_overflow",
    "plain_i32_shift_invalid",
    "plain_i32_unary_minus_min",
}
_RUST_OVERFLOW_CHECKED_PROFILES = {"debug", "overflow-checks-on"}
_RUST_OVERFLOW_UNCHECKED_PROFILES = {"release", "overflow-checks-off"}
_RUST_ALWAYS_RUNTIME_FAILED_CASE_IDS = {"plain_i32_division_by_zero"}
_RUST_ALWAYS_COMPILE_FAILED_CASE_IDS = {"float_sign_renderer_missing"}
_COMMANDS = [
    "python",
    "git",
    "cc",
    "c99",
    "gcc",
    "clang",
    "c++",
    "g++",
    "clang++",
    "java",
    "javac",
    "rustc",
    "cargo",
    "go",
    "node",
    "npm",
    "tsc",
    "z3",
]
_C_SANITIZER_FLAGS = [
    "-fsanitize=undefined,signed-integer-overflow,shift,integer-divide-by-zero",
    "-fno-sanitize-recover=all",
]
_CPP_SANITIZER_FLAGS = [
    "-fsanitize=undefined,signed-integer-overflow,shift,integer-divide-by-zero",
    "-fno-sanitize-recover=all",
]
_Z3_SORTS = ["Int", "Real", "BitVec", "FP"]
_Z3_SUPPORT_LEVELS = {"exact", "approximate", "uninterpreted", "unsupported"}
_RISK_LEVELS = {"low", "medium", "high", "unknown"}
_C_CPP_ALIGNMENT_OUTCOMES = {
    "exact",
    "exact_with_obligations",
    "profile_dependent",
    "unsupported",
    "compile_failed",
    "runtime_trap",
    "ub",
}
_C_CPP_ALIGNMENT_RENDER_PATHS = [
    "builtin_c_style",
    "template_c_core",
    "template_c_poll_core",
    "builtin_cpp_style",
    "template_cpp_c_core",
    "template_cpp_poll_c_core",
]
_C_CPP_ALIGNMENT_REQUIRED_SHIFT_OBLIGATIONS = {
    "valid_shift_count",
    "non_negative_shift_count",
    "no_signed_left_shift_ub",
    "signed_right_shift_profile",
}
_UFUNC_NAMES = [
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "asinh",
    "acosh",
    "atanh",
    "sqrt",
    "cbrt",
    "sign",
    "exp",
    "log",
    "log10",
    "log2",
    "log1p",
    "abs",
    "ceil",
    "floor",
    "round",
    "trunc",
]


@dataclass(frozen=True)
class NumericSmokeCase:
    """
    Describe one FCSTM numeric expression smoke case.

    :param case_id: Stable case identifier used in JSON output.
    :type case_id: str
    :param operator: Operator or function family covered by the case.
    :type operator: str
    :param fcstm_expression: FCSTM numeric expression to render.
    :type fcstm_expression: str
    :param a_value: Value assigned to variable ``A``.
    :type a_value: int
    :param b_value: Value assigned to variable ``B``.
    :type b_value: int
    :param expects_undefined_behavior: Whether sanitizer failure is expected to
        be informative for the case.
    :type expects_undefined_behavior: bool

    Example::

        >>> case = NumericSmokeCase('pow', '**', 'A ** B', 3, 2)
        >>> case.operator
        '**'
    """

    case_id: str
    operator: str
    fcstm_expression: str
    a_value: int
    b_value: int
    expects_undefined_behavior: bool = False


@dataclass(frozen=True)
class RenderPath:
    """
    Describe one render path extracted from ``render_mapping.json``.

    :param path_id: Stable render-path identifier used in case ids.
    :type path_id: str
    :param language: Summary language, such as ``"c"`` or ``"cpp"``.
    :type language: str
    :param compile_language: Compiler family used for the generated smoke file.
    :type compile_language: str
    :param lang_style: Built-in renderer style to use.
    :type lang_style: str
    :param expression_core_language: Renderer core language used to build
        ``render_templates``.
    :type expression_core_language: str
    :param ext_configs: Template expression overrides from R0 mapping.
    :type ext_configs: Mapping[str, str]
    :param render_templates: Fully merged expression templates read from the
        mapping snapshot.
    :type render_templates: Mapping[str, str]
    :param mapping_sources: Mapping paths that justify the render path.
    :type mapping_sources: Tuple[str, ...]
    :param template_name: Optional built-in template name represented by this path.
    :type template_name: Optional[str]
    :param wrapper_language: Optional wrapper language for generated template
        paths that reuse a core language.
    :type wrapper_language: Optional[str]

    Example::

        >>> path = RenderPath(
        ...     'builtin_c_style', 'c', 'c', 'c', 'c', {},
        ...     {'Name': '{{ node.name }}'}, ('builtin_expr_styles.styles.c',),
        ... )
        >>> path.compile_language
        'c'
    """

    path_id: str
    language: str
    compile_language: str
    lang_style: str
    expression_core_language: str
    ext_configs: Mapping[str, str]
    render_templates: Mapping[str, str]
    mapping_sources: Tuple[str, ...]
    template_name: Optional[str] = None
    wrapper_language: Optional[str] = None


@dataclass(frozen=True)
class NativeSmokeCase:
    """
    Describe one Java or Rust native smoke case.

    Java and Rust templates do not exist in the current repository, so these
    cases are native runner facts that preserve the shared join-key shape used
    by C-family smoke reports and the Python/Z3 baseline.

    :param case_id: Stable language-local case identifier.
    :type case_id: str
    :param language: Target language, either ``"java"`` or ``"rust"``.
    :type language: str
    :param operator: FCSTM operator or function family represented by the case.
    :type operator: str
    :param fcstm_expression: Closest FCSTM expression for cross-artifact joins.
    :type fcstm_expression: str
    :param render_expression: Native expression text used by the smoke program.
    :type render_expression: str
    :param native_api_family: Native semantic family, such as ``"plain-int32"``
        or ``"checked"``.
    :type native_api_family: str
    :param source_note_ids: Official-source note ids supporting the case.
    :type source_note_ids: Tuple[str, ...]
    :param declarations: Target-language declarations emitted before the
        expression.
    :type declarations: str
    :param a_value: Value passed as FCSTM-like variable ``A``.
    :type a_value: Union[int, float]
    :param b_value: Value passed as FCSTM-like variable ``B``.
    :type b_value: Union[int, float]
    :param profile: Primary profile for Java cases, defaults to ``None`` for
        Rust cases that expand across multiple profiles.
    :type profile: Optional[str], optional

    Example::

        >>> case = NativeSmokeCase(
        ...     'add_overflow', 'java', '+', 'A + B', 'a + b',
        ...     'plain-int32', ('jls-integer-overflow',), 'int a = 1; int b = 2;'
        ... )
        >>> case.operator
        '+'
    """

    case_id: str
    language: str
    operator: str
    fcstm_expression: str
    render_expression: str
    native_api_family: str
    source_note_ids: Tuple[str, ...]
    declarations: str
    a_value: Union[int, float] = 0
    b_value: Union[int, float] = 0
    profile: Optional[str] = None


def _command_version(path: str) -> Optional[str]:
    """
    Return a short version string for an executable when available.

    :param path: Executable path.
    :type path: str
    :return: First version-output line or ``None``.
    :rtype: Optional[str]

    Example::

        >>> version = _command_version(sys.executable)
        >>> version is None or isinstance(version, str)
        True
    """
    args = [path, "--version"]
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=5,
            check=False,
        )
    except OSError:
        # OSError: the executable disappeared or cannot be started after
        # shutil.which located it; record absence instead of failing env mode.
        return None
    except subprocess.TimeoutExpired:
        # TimeoutExpired: version probes are best-effort and must not hang the
        # lightweight environment stub.
        return None
    output = result.stdout.strip().splitlines()
    return output[0] if output else None


def _stable_json(value: Any) -> str:
    """
    Serialize a research artifact as stable, human-readable JSON.

    :param value: JSON-compatible value.
    :type value: Any
    :return: Stable JSON text ending in a newline.
    :rtype: str

    Example::

        >>> _stable_json({'b': 1, 'a': 2}).splitlines()[1]
        '  "a": 2,'
    """
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _read_json(path: Union[str, Path]) -> _JSON_OBJECT:
    """
    Read a JSON object from disk.

    :param path: JSON file path.
    :type path: Union[str, pathlib.Path]
    :return: Parsed JSON object.
    :rtype: Dict[str, Any]
    :raises ValueError: If the file does not contain a JSON object.
    :raises json.JSONDecodeError: If the JSON text is invalid.
    :raises OSError: If the file cannot be read.

    Example::

        >>> import tempfile
        >>> p = Path(tempfile.gettempdir()) / 'pyfcstm-json-object-example.json'
        >>> _ = p.write_text('{"ok": true}', encoding='utf-8')
        >>> _read_json(p)['ok']
        True
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object")
    return data


def _write_payload(output_path: Union[str, Path], payload: Mapping[str, Any]) -> None:
    """
    Write a JSON payload to disk with parent directories created.

    :param output_path: Destination path.
    :type output_path: Union[str, pathlib.Path]
    :param payload: JSON-compatible payload.
    :type payload: Mapping[str, Any]
    :return: ``None``.
    :rtype: None

    Example::

        >>> import tempfile
        >>> path = Path(tempfile.gettempdir()) / 'pyfcstm-probe-write-example.json'
        >>> _write_payload(path, {'ok': True})
        >>> '"ok": true' in path.read_text(encoding='utf-8')
        True
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8")


def _payload_sha256(payload: Any) -> str:
    """
    Return the SHA-256 digest for a stable JSON payload.

    :param payload: JSON-compatible payload.
    :type payload: Any
    :return: Lowercase SHA-256 digest.
    :rtype: str

    Example::

        >>> _payload_sha256({'b': 1, 'a': 2}) == _payload_sha256({'a': 2, 'b': 1})
        True
    """
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _text_file_sha256(path: Union[str, Path]) -> str:
    """
    Return the SHA-256 digest for LF-normalized UTF-8 file text.

    :param path: Text file path.
    :type path: Union[str, pathlib.Path]
    :return: Lowercase SHA-256 digest.
    :rtype: str
    :raises OSError: If the file cannot be read.
    :raises UnicodeDecodeError: If the file is not valid UTF-8 text.

    Example::

        >>> import tempfile
        >>> path = Path(tempfile.gettempdir()) / 'pyfcstm-probe-sha256-example.txt'
        >>> _ = path.write_text('a\\r\\nb\\n', encoding='utf-8')
        >>> len(_text_file_sha256(path))
        64
    """
    text = Path(path).read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_sha256_sidecar(path: Union[str, Path]) -> str:
    """
    Read a ``sha256sum``-style sidecar file.

    :param path: Sidecar file path.
    :type path: Union[str, pathlib.Path]
    :return: Lowercase SHA-256 digest from the first whitespace-separated
        field.
    :rtype: str
    :raises OSError: If the sidecar cannot be read.
    :raises UnicodeDecodeError: If the sidecar is not valid UTF-8 text.
    :raises ValueError: If the sidecar does not contain a valid digest.

    Example::

        >>> import tempfile
        >>> path = Path(tempfile.gettempdir()) / 'pyfcstm-probe-sha256-sidecar.txt'
        >>> _ = path.write_text('0' * 64 + '  payload.json\\n', encoding='utf-8')
        >>> _read_sha256_sidecar(path) == '0' * 64
        True
    """
    fields = Path(path).read_text(encoding="utf-8").strip().split()
    if not fields:
        raise ValueError("empty sha256 sidecar")
    digest = fields[0]
    if (
        len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
        or digest.lower() != digest
    ):
        raise ValueError("invalid sha256 digest: %r" % digest)
    return digest


def _probe_command(name: str) -> _JSON_OBJECT:
    """
    Probe one optional command without invoking any workload.

    :param name: Command name to locate.
    :type name: str
    :return: Command availability metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> info = _probe_command('python')
        >>> info['name']
        'python'
    """
    path = shutil.which(name)
    return {
        "name": name,
        "path": path,
        "available": path is not None,
        "version": _command_version(path) if path else None,
    }


def build_environment_report(repo_root: Union[str, Path] = ".") -> _JSON_OBJECT:
    """
    Build a lightweight environment report for future probe planning.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: JSON-compatible environment report.
    :rtype: Dict[str, Any]

    Example::

        >>> report = build_environment_report('.')
        >>> report['mode']
        'env'
    """
    root = Path(repo_root).resolve()
    return {
        "schema_version": 1,
        "mode": "env",
        "native_runner_enabled": False,
        "repository": {
            "root": str(root),
            "research_path": _RESEARCH_PATH,
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "resources": {
            "cpu_count": os.cpu_count(),
        },
        "available_commands": [_probe_command(name) for name in _COMMANDS],
        "notes": [
            "Environment mode is inventory-only and does not compile or execute target-language probes.",
            "C-family smoke modes compile tiny programs and keep artifacts in gitignored local output paths.",
        ],
    }


def _as_repo_path(repo_root: Union[str, Path]) -> Path:
    """
    Normalize a repository root path.

    :param repo_root: Repository root path supplied by a caller or CLI.
    :type repo_root: Union[str, pathlib.Path]
    :return: Absolute repository root path.
    :rtype: pathlib.Path

    Example::

        >>> _as_repo_path('.').is_absolute()
        True
    """
    return Path(repo_root).resolve()


def _resolve_mapping_path(repo_root: Path, mapping_path: Union[str, Path]) -> Path:
    """
    Resolve a render-mapping path against the repository root.

    :param repo_root: Absolute repository root.
    :type repo_root: pathlib.Path
    :param mapping_path: Absolute or repository-relative mapping path.
    :type mapping_path: Union[str, pathlib.Path]
    :return: Absolute mapping path.
    :rtype: pathlib.Path

    Example::

        >>> _resolve_mapping_path(Path('.').resolve(), _DEFAULT_MAPPING_PATH).is_absolute()
        True
    """
    path = Path(mapping_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _load_render_mapping(
    repo_root: Path, mapping_path: Union[str, Path]
) -> _JSON_OBJECT:
    """
    Load a render-mapping snapshot.

    :param repo_root: Absolute repository root.
    :type repo_root: pathlib.Path
    :param mapping_path: Absolute or repository-relative mapping path.
    :type mapping_path: Union[str, pathlib.Path]
    :return: Parsed render-mapping snapshot.
    :rtype: Dict[str, Any]
    :raises ValueError: If the snapshot root is not a JSON object.
    :raises json.JSONDecodeError: If the snapshot file is invalid JSON.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> mapping['schema_version']
        1
    """
    resolved = _resolve_mapping_path(repo_root, mapping_path)
    try:
        return _read_json(resolved)
    except ValueError as err:
        # ValueError: _read_json rejects non-object JSON, which is invalid for
        # the render mapping contract and should surface with path context.
        raise ValueError("Render mapping must be a JSON object: %s" % resolved) from err


def _risk_cases() -> List[NumericSmokeCase]:
    """
    Return the C-family numeric risk cases covered by smoke probes.

    :return: Stable smoke-case definitions.
    :rtype: List[NumericSmokeCase]

    Example::

        >>> any(case.case_id == 'cbrt' for case in _risk_cases())
        True
    """
    return [
        NumericSmokeCase("round", "round", "round(A)", -9, 2),
        NumericSmokeCase("abs", "abs", "abs(A)", -9, 2),
        NumericSmokeCase("sign", "sign", "sign(A)", -9, 2),
        NumericSmokeCase("cbrt", "cbrt", "cbrt(A)", -9, 2),
        NumericSmokeCase("pow", "**", "A ** B", 3, 2),
        NumericSmokeCase("signed_left_shift", "<<", "A << B", -9, 2, True),
        NumericSmokeCase("integer_division", "/", "A / B", 7, 2),
        NumericSmokeCase("divide_by_zero", "/", "A / B", 7, 0, True),
    ]


def _template_expr_overrides(
    mapping: Mapping[str, Any], template_name: str, style_name: str = "c_scope_expr"
) -> Mapping[str, str]:
    """
    Return expression overrides for one template style from R0 mapping.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param template_name: Template name under ``templates``.
    :type template_name: str
    :param style_name: Template expression style name, defaults to
        ``"c_scope_expr"``.
    :type style_name: str, optional
    :return: Expression override mapping.
    :rtype: Mapping[str, str]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _template_expr_overrides(mapping, 'c')['Name'].startswith('scope->')
        True
    """
    templates = mapping["templates"]
    style = templates[template_name]["expr_styles"][style_name]
    return dict(style.get("overrides") or {})


def _format_mapping_path(path: Sequence[Union[str, int]]) -> str:
    """
    Format a mapping path for diagnostics.

    :param path: Sequence of string keys and list indexes.
    :type path: Sequence[Union[str, int]]
    :return: Human-readable mapping path.
    :rtype: str

    Example::

        >>> _format_mapping_path(('cxx_paths', 'template_generated_paths', 0))
        'cxx_paths.template_generated_paths[0]'
    """
    parts = []
    for item in path:
        if isinstance(item, int):
            if parts:
                parts[-1] = "%s[%d]" % (parts[-1], item)
            else:
                parts.append("[%d]" % item)
        else:
            parts.append(item)
    return ".".join(parts) if parts else "<root>"


def _mapping_value(
    root: Mapping[str, Any],
    path: Sequence[Union[str, int]],
    expected_type: Optional[Any] = None,
) -> Any:
    """
    Return a nested value from the render-mapping snapshot.

    :param root: Render-mapping root object.
    :type root: Mapping[str, Any]
    :param path: Sequence of dictionary keys and list indexes.
    :type path: Sequence[Union[str, int]]
    :param expected_type: Optional expected Python type or type tuple.
    :type expected_type: Optional[Any], optional
    :return: Nested mapping value.
    :rtype: Any
    :raises ValueError: If a path segment is missing or has the wrong type.

    Example::

        >>> _mapping_value({'a': [{'b': 1}]}, ('a', 0, 'b'))
        1
    """
    current: Any = root
    visited: List[Union[str, int]] = []
    for item in path:
        visited.append(item)
        if isinstance(item, int):
            if not isinstance(current, list) or item >= len(current):
                raise ValueError(
                    "missing mapping path: %s" % _format_mapping_path(visited)
                )
            current = current[item]
        else:
            if not isinstance(current, dict) or item not in current:
                raise ValueError(
                    "missing mapping path: %s" % _format_mapping_path(visited)
                )
            current = current[item]
    if expected_type is not None and not isinstance(current, expected_type):
        raise ValueError(
            "mapping path %s must be %s, got %s"
            % (
                _format_mapping_path(path),
                getattr(expected_type, "__name__", repr(expected_type)),
                type(current).__name__,
            )
        )
    return current


def _string_mapping(
    value: Mapping[str, Any], path: Sequence[Union[str, int]]
) -> Dict[str, str]:
    """
    Validate and copy a string-keyed string mapping.

    :param value: Mapping value to copy.
    :type value: Mapping[str, Any]
    :param path: Source mapping path used for diagnostics.
    :type path: Sequence[Union[str, int]]
    :return: Copied mapping.
    :rtype: Dict[str, str]
    :raises ValueError: If any key or value is not a string.

    Example::

        >>> _string_mapping({'Name': '{{ node.name }}'}, ('x',))
        {'Name': '{{ node.name }}'}
    """
    copied = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError(
                "mapping path %s must contain only string keys and values"
                % _format_mapping_path(path)
            )
        copied[key] = item
    return copied


def _builtin_style_templates(
    mapping: Mapping[str, Any], style_name: str
) -> Dict[str, str]:
    """
    Return built-in expression templates from the mapping snapshot.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param style_name: Built-in expression style name.
    :type style_name: str
    :return: Template mapping for the style.
    :rtype: Dict[str, str]
    :raises ValueError: If the style or its templates are missing.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _builtin_style_templates(mapping, 'c')['BinaryOp(**)'].startswith('pow(')
        True
    """
    path = ("builtin_expr_styles", "styles", style_name, "templates")
    value = _mapping_value(mapping, path, dict)
    return _string_mapping(value, path)


def _merge_expr_templates(
    base_templates: Mapping[str, str], overrides: Mapping[str, str]
) -> Dict[str, str]:
    """
    Merge base expression templates with mapping-provided overrides.

    This mirrors :func:`pyfcstm.render.expr.create_expr_render_template` so a
    generic override such as ``UFunc`` replaces operator-specific built-in
    templates for that family.

    :param base_templates: Base templates from ``builtin_expr_styles``.
    :type base_templates: Mapping[str, str]
    :param overrides: Template-specific override mapping.
    :type overrides: Mapping[str, str]
    :return: Merged expression-template mapping.
    :rtype: Dict[str, str]

    Example::

        >>> _merge_expr_templates({'UFunc(abs)': 'old', 'UFunc': 'base'}, {'UFunc': 'new'})
        {'UFunc': 'new'}
    """
    templates = dict(base_templates)
    ext_configs = dict(overrides)
    for generic_key in ("UFunc", "UnaryOp", "BinaryOp"):
        if generic_key in ext_configs:
            prefix = generic_key + "("
            templates = {
                key: value
                for key, value in templates.items()
                if key != generic_key and not key.startswith(prefix)
            }
    templates.update(ext_configs)
    return templates


def _template_expr_style(
    mapping: Mapping[str, Any], template_name: str, style_name: str = "c_scope_expr"
) -> Mapping[str, Any]:
    """
    Return one template expression style from the mapping snapshot.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param template_name: Built-in template name.
    :type template_name: str
    :param style_name: Expression style name, defaults to ``"c_scope_expr"``.
    :type style_name: str, optional
    :return: Style mapping with ``base_lang`` and ``overrides`` fields.
    :rtype: Mapping[str, Any]
    :raises ValueError: If the style is missing.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _template_expr_style(mapping, 'cpp')['base_lang']
        'c'
    """
    path = ("templates", template_name, "expr_styles", style_name)
    return _mapping_value(mapping, path, dict)


def _template_render_path(
    mapping: Mapping[str, Any],
    path_id: str,
    language: str,
    template_name: str,
    style_name: str = "c_scope_expr",
    cxx_path_index: Optional[int] = None,
    compile_language: Optional[str] = None,
) -> RenderPath:
    """
    Build a template render path from mapping snapshot fields.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param path_id: Stable render-path identifier.
    :type path_id: str
    :param language: Summary language for the path.
    :type language: str
    :param template_name: Built-in template name.
    :type template_name: str
    :param style_name: Template expression style name, defaults to
        ``"c_scope_expr"``.
    :type style_name: str, optional
    :param cxx_path_index: Optional index into
        ``cxx_paths.template_generated_paths`` for C++ wrapper paths.
    :type cxx_path_index: Optional[int], optional
    :param compile_language: Optional compiler family override. C++ wrapper
        paths use this to compile C-style expressions in a C++ translation unit.
    :type compile_language: Optional[str], optional
    :return: Render path using templates derived from mapping data.
    :rtype: RenderPath
    :raises ValueError: If required mapping facts are missing or inconsistent.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _template_render_path(mapping, 'template_c_core', 'c', 'c').compile_language
        'c'
    """
    style = _template_expr_style(mapping, template_name, style_name)
    if cxx_path_index is not None:
        cxx_style_path = (
            "cxx_paths",
            "template_generated_paths",
            cxx_path_index,
            "expr_styles",
            style_name,
        )
        cxx_style = _mapping_value(mapping, cxx_style_path, dict)
        if dict(cxx_style) != dict(style):
            raise ValueError(
                "mapping path %s does not match templates.%s.expr_styles.%s"
                % (_format_mapping_path(cxx_style_path), template_name, style_name)
            )
    base_lang = style.get("base_lang")
    if base_lang not in {"c", "cpp"}:
        raise ValueError(
            "templates.%s.expr_styles.%s.base_lang must be c or cpp, got %r"
            % (template_name, style_name, base_lang)
        )
    overrides_path = (
        "templates",
        template_name,
        "expr_styles",
        style_name,
        "overrides",
    )
    overrides = _string_mapping(
        _mapping_value(mapping, overrides_path, dict), overrides_path
    )
    base_templates = _builtin_style_templates(mapping, str(base_lang))
    sources = [
        "builtin_expr_styles.styles.%s" % base_lang,
        "templates.%s.expr_styles.%s" % (template_name, style_name),
    ]
    if cxx_path_index is not None:
        sources.insert(
            0,
            "cxx_paths.template_generated_paths[%d].expr_styles.%s"
            % (cxx_path_index, style_name),
        )
    return RenderPath(
        path_id,
        language,
        compile_language or str(base_lang),
        str(base_lang),
        str(base_lang),
        overrides,
        _merge_expr_templates(base_templates, overrides),
        tuple(sources),
        template_name=template_name,
        wrapper_language=language if language != base_lang else None,
    )


def _cxx_template_path_index(mapping: Mapping[str, Any], template_name: str) -> int:
    """
    Return the C++ generated-template path index for a template name.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param template_name: Expected template name such as ``"cpp"``.
    :type template_name: str
    :return: Index under ``cxx_paths.template_generated_paths``.
    :rtype: int
    :raises ValueError: If the C++ path is missing.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _cxx_template_path_index(mapping, 'cpp') >= 0
        True
    """
    paths = _mapping_value(mapping, ("cxx_paths", "template_generated_paths"), list)
    for index, item in enumerate(paths):
        if isinstance(item, dict) and item.get("template") == template_name:
            return index
    raise ValueError("missing C++ template path: %s" % template_name)


def _builtin_render_path(
    mapping: Mapping[str, Any], path_id: str, language: str, style_name: str
) -> RenderPath:
    """
    Build a built-in renderer path from mapping snapshot fields.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param path_id: Stable render-path identifier.
    :type path_id: str
    :param language: Summary language for the path.
    :type language: str
    :param style_name: Built-in expression style name.
    :type style_name: str
    :return: Render path using built-in templates from the mapping snapshot.
    :rtype: RenderPath
    :raises ValueError: If required C++ path facts are missing or inconsistent.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> _builtin_render_path(mapping, 'builtin_cpp_style', 'cpp', 'cpp').compile_language
        'cpp'
    """
    templates = _builtin_style_templates(mapping, style_name)
    sources = ["builtin_expr_styles.styles.%s" % style_name]
    if style_name == "cpp":
        cxx_path = _mapping_value(mapping, ("cxx_paths", "builtin_cpp_style"), dict)
        if cxx_path.get("base_lang") != "cpp":
            raise ValueError("cxx_paths.builtin_cpp_style.base_lang must be cpp")
        cxx_templates = _mapping_value(
            mapping, ("cxx_paths", "builtin_cpp_style", "templates"), dict
        )
        if (
            _string_mapping(
                cxx_templates, ("cxx_paths", "builtin_cpp_style", "templates")
            )
            != templates
        ):
            raise ValueError(
                "cxx_paths.builtin_cpp_style.templates does not match "
                "builtin_expr_styles.styles.cpp.templates"
            )
        sources.insert(0, "cxx_paths.builtin_cpp_style")
    return RenderPath(
        path_id,
        language,
        style_name,
        style_name,
        style_name,
        {},
        templates,
        tuple(sources),
    )


def _render_paths_for_mode(mode: str, mapping: Mapping[str, Any]) -> List[RenderPath]:
    """
    Build render paths for a C-family smoke mode from R0 mapping.

    :param mode: Probe mode, either ``"c-smoke"`` or ``"cpp-smoke"``.
    :type mode: str
    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :return: Render paths to probe.
    :rtype: List[RenderPath]
    :raises ValueError: If ``mode`` is not a C-family smoke mode.

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> [path.path_id for path in _render_paths_for_mode('cpp-smoke', mapping)][0]
        'builtin_cpp_style'
    """
    if mode == "c-smoke":
        return [
            _builtin_render_path(mapping, "builtin_c_style", "c", "c"),
            _template_render_path(mapping, "template_c_core", "c", "c"),
            _template_render_path(mapping, "template_c_poll_core", "c", "c_poll"),
        ]
    if mode == "cpp-smoke":
        cpp_index = _cxx_template_path_index(mapping, "cpp")
        cpp_poll_index = _cxx_template_path_index(mapping, "cpp_poll")
        return [
            _builtin_render_path(mapping, "builtin_cpp_style", "cpp", "cpp"),
            _template_render_path(
                mapping,
                "template_cpp_c_core",
                "cpp",
                "cpp",
                cxx_path_index=cpp_index,
                compile_language="cpp",
            ),
            _template_render_path(
                mapping,
                "template_cpp_poll_c_core",
                "cpp",
                "cpp_poll",
                cxx_path_index=cpp_poll_index,
                compile_language="cpp",
            ),
        ]
    raise ValueError("Unsupported C-family smoke mode: %s" % mode)


def _render_native_expr(expr_text: str, lang_style: str) -> str:
    """
    Render a numeric expression with a built-in native language style.

    :param expr_text: FCSTM numeric expression text.
    :type expr_text: str
    :param lang_style: Built-in expression style, such as ``"java"`` or
        ``"rust"``.
    :type lang_style: str
    :return: Rendered expression text.
    :rtype: str

    Example::

        >>> _render_native_expr('A ** B', 'java')
        'Math.pow(A, B)'
    """
    expr = parse_expr_from_string(expr_text, mode="numeric")
    return render_expr_node(expr.to_ast_node(), lang_style=lang_style)


def _official_source_notes(language: str) -> List[_JSON_OBJECT]:
    """
    Return official source notes for Java or Rust smoke probes.

    :param language: ``"java"`` or ``"rust"``.
    :type language: str
    :return: Source-backed notes used by smoke cases.
    :rtype: List[Dict[str, Any]]
    :raises ValueError: If ``language`` is not a supported native smoke
        language.

    Example::

        >>> any(note['id'] == 'jls-integer-overflow' for note in _official_source_notes('java'))
        True
    """
    if language == "java":
        return [
            {
                "id": "jls-integer-overflow",
                "source": "Java Language Specification, Java SE 21, chapter 15",
                "url": "https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html",
                "summary": "Java integer operators use fixed primitive widths; integer overflow wraps silently except where a library method such as Math.*Exact specifies an exception.",
            },
            {
                "id": "jls-div-rem",
                "source": "Java Language Specification, Java SE 21, sections 15.17.2 and 15.17.3",
                "url": "https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.17.2",
                "summary": "Integer division and remainder throw ArithmeticException on zero divisors; remainder has the dividend sign.",
            },
            {
                "id": "jls-shift-mask",
                "source": "Java Language Specification, Java SE 21, section 15.19",
                "url": "https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.19",
                "summary": "Java masks int shift counts to five low bits and long shift counts to six low bits.",
            },
            {
                "id": "jls-narrowing-conversion",
                "source": "Java Language Specification, Java SE 21, section 5.1.3",
                "url": "https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html#jls-5.1.3",
                "summary": "Narrowing primitive conversions may lose high-order bits, precision or range.",
            },
            {
                "id": "java-math-exact",
                "source": "Java SE 21 java.lang.Math API",
                "url": "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Math.html",
                "summary": "Math.*Exact methods provide checked integer arithmetic and throw ArithmeticException on overflow.",
            },
            {
                "id": "java-math-floating",
                "source": "Java SE 21 java.lang.Math API",
                "url": "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Math.html",
                "summary": "Math.pow and Math.round expose floating-point math semantics that differ from pure fixed-width integer arithmetic.",
            },
        ]
    if language == "rust":
        return [
            {
                "id": "rust-reference-overflow",
                "source": "Rust Reference: Expressions / operator overflow",
                "url": "https://doc.rust-lang.org/reference/expressions/operator-expr.html#overflow",
                "summary": "Rust integer overflow checking depends on debug assertions and overflow-checks settings; overflow can panic or wrap depending on profile.",
            },
            {
                "id": "rust-reference-div-rem-shift",
                "source": "Rust Reference: arithmetic and bitwise expressions",
                "url": "https://doc.rust-lang.org/reference/expressions/operator-expr.html",
                "summary": "Division by zero, remainder by zero and invalid shifts are checked error cases; shift and arithmetic behavior is profile-sensitive for overflow.",
            },
            {
                "id": "rust-reference-cast",
                "source": "Rust Reference: type cast expressions",
                "url": "https://doc.rust-lang.org/reference/expressions/operator-expr.html#type-cast-expressions",
                "summary": "Rust numeric casts use explicit `as` conversions with specified integer truncation or float conversion behavior.",
            },
            {
                "id": "rust-std-overflowing-apis",
                "source": "Rust standard library primitive integer methods",
                "url": "https://doc.rust-lang.org/std/primitive.i32.html",
                "summary": "Primitive integer methods expose wrapping_*, checked_*, overflowing_* and saturating_* semantic families.",
            },
            {
                "id": "rust-std-float-methods",
                "source": "Rust standard library primitive f64 methods",
                "url": "https://doc.rust-lang.org/std/primitive.f64.html",
                "summary": "Floating methods such as powf, round and signum use f64 semantics before any explicit integer cast or profile-specific wrapper.",
            },
        ]
    raise ValueError("Unsupported official source language: %s" % language)


def _java_smoke_cases() -> List[NativeSmokeCase]:
    """
    Return the Java native smoke case plan.

    :return: Java smoke cases.
    :rtype: List[NativeSmokeCase]

    Example::

        >>> any(case.case_id == 'math_add_exact_overflow' for case in _java_smoke_cases())
        True
    """
    return [
        NativeSmokeCase(
            "int_add_overflow_wrap",
            "java",
            "+",
            "A + B",
            _render_native_expr("A + B", "java"),
            "plain-int32",
            ("jls-integer-overflow",),
            "int A = Integer.MAX_VALUE;\n        int B = 1;",
            2147483647,
            1,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "int_division_truncates",
            "java",
            "/",
            "A / B",
            _render_native_expr("A / B", "java"),
            "plain-int32",
            ("jls-div-rem",),
            "int A = -7;\n        int B = 2;",
            -7,
            2,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "int_remainder_dividend_sign",
            "java",
            "%",
            "A % B",
            _render_native_expr("A % B", "java"),
            "plain-int32",
            ("jls-div-rem",),
            "int A = -7;\n        int B = 2;",
            -7,
            2,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "division_by_zero_exception",
            "java",
            "/",
            "A / B",
            _render_native_expr("A / B", "java"),
            "plain-int32",
            ("jls-div-rem",),
            "int A = 7;\n        int B = 0;",
            7,
            0,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "bitwise_and_mask",
            "java",
            "&",
            "A & B",
            _render_native_expr("A & B", "java"),
            "plain-int32",
            ("jls-integer-overflow",),
            "int A = 0b1010;\n        int B = 0b1100;",
            10,
            12,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "unary_minus_min_wrap",
            "java",
            "unary-",
            "-A",
            _render_native_expr("-A", "java"),
            "plain-int32",
            ("jls-integer-overflow",),
            "int A = Integer.MIN_VALUE;\n        int B = 0;",
            -2147483648,
            0,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "shift_count_masking",
            "java",
            "<<",
            "A << B",
            _render_native_expr("A << B", "java"),
            "plain-int32",
            ("jls-shift-mask",),
            "int A = 1;\n        int B = 32;",
            1,
            32,
            profile="java-int32",
        ),
        NativeSmokeCase(
            "narrowing_int_to_byte",
            "java",
            "cast",
            "A",
            "(byte) A",
            "narrowing-cast",
            ("jls-narrowing-conversion",),
            "int A = 128;\n        int B = 0;",
            128,
            0,
            profile="java-int8-cast",
        ),
        NativeSmokeCase(
            "math_pow_promotes_double",
            "java",
            "**",
            "A ** B",
            _render_native_expr("A ** B", "java"),
            "math-floating",
            ("java-math-floating",),
            "int A = 3;\n        int B = 2;",
            3,
            2,
            profile="java-double-math",
        ),
        NativeSmokeCase(
            "math_round_half_up",
            "java",
            "round",
            "round(A)",
            "Math.round(A)",
            "math-floating",
            ("java-math-floating",),
            "double A = -2.5;\n        int B = 0;",
            -2.5,
            0,
            profile="java-double-math",
        ),
        NativeSmokeCase(
            "math_add_exact_overflow",
            "java",
            "+",
            "A + B",
            "Math.addExact(A, B)",
            "checked-exact",
            ("java-math-exact",),
            "int A = Integer.MAX_VALUE;\n        int B = 1;",
            2147483647,
            1,
            profile="java-int32-checked",
        ),
        NativeSmokeCase(
            "math_multiply_exact_overflow",
            "java",
            "*",
            "A * B",
            "Math.multiplyExact(A, B)",
            "checked-exact",
            ("java-math-exact",),
            "int A = 1073741824;\n        int B = 2;",
            1073741824,
            2,
            profile="java-int32-checked",
        ),
        NativeSmokeCase(
            "math_sign_missing",
            "java",
            "sign",
            "sign(A)",
            _render_native_expr("sign(A)", "java"),
            "renderer-fallback",
            ("java-math-exact",),
            "int A = -9;\n        int B = 0;",
            -9,
            0,
            profile="java-renderer-fallback",
        ),
    ]


def _rust_smoke_cases() -> List[NativeSmokeCase]:
    """
    Return the Rust native smoke case plan.

    :return: Rust smoke cases.
    :rtype: List[NativeSmokeCase]

    Example::

        >>> any(case.case_id == 'checked_add_overflow' for case in _rust_smoke_cases())
        True
    """
    return [
        NativeSmokeCase(
            "plain_i32_add_overflow",
            "rust",
            "+",
            "A + B",
            _render_native_expr("A + B", "rust"),
            "plain-i32",
            ("rust-reference-overflow",),
            "let A: i32 = opaque_i32(i32::MAX);\n    let B: i32 = opaque_i32(1);",
            2147483647,
            1,
        ),
        NativeSmokeCase(
            "plain_i32_division",
            "rust",
            "/",
            "A / B",
            _render_native_expr("A / B", "rust"),
            "plain-i32",
            ("rust-reference-div-rem-shift",),
            "let A: i32 = opaque_i32(-7);\n    let B: i32 = opaque_i32(2);",
            -7,
            2,
        ),
        NativeSmokeCase(
            "plain_i32_remainder",
            "rust",
            "%",
            "A % B",
            _render_native_expr("A % B", "rust"),
            "plain-i32",
            ("rust-reference-div-rem-shift",),
            "let A: i32 = opaque_i32(-7);\n    let B: i32 = opaque_i32(2);",
            -7,
            2,
        ),
        NativeSmokeCase(
            "plain_i32_division_by_zero",
            "rust",
            "/",
            "A / B",
            _render_native_expr("A / B", "rust"),
            "plain-i32",
            ("rust-reference-div-rem-shift",),
            "let A: i32 = opaque_i32(7);\n    let B: i32 = opaque_i32(0);",
            7,
            0,
        ),
        NativeSmokeCase(
            "plain_i32_bitwise_and",
            "rust",
            "&",
            "A & B",
            _render_native_expr("A & B", "rust"),
            "plain-i32",
            ("rust-reference-div-rem-shift",),
            "let A: i32 = opaque_i32(0b1010);\n    let B: i32 = opaque_i32(0b1100);",
            10,
            12,
        ),
        NativeSmokeCase(
            "plain_i32_unary_minus_min",
            "rust",
            "unary-",
            "-A",
            _render_native_expr("-A", "rust"),
            "plain-i32",
            ("rust-reference-overflow",),
            "let A: i32 = opaque_i32(i32::MIN);\n    let B: i32 = opaque_i32(0);",
            -2147483648,
            0,
        ),
        NativeSmokeCase(
            "plain_i32_shift_invalid",
            "rust",
            "<<",
            "A << B",
            _render_native_expr("A << B", "rust"),
            "plain-i32",
            ("rust-reference-div-rem-shift",),
            "let A: i32 = opaque_i32(1);\n    let B: u32 = opaque_u32(32);",
            1,
            32,
        ),
        NativeSmokeCase(
            "cast_i32_to_i8",
            "rust",
            "cast",
            "A",
            "A as i8",
            "cast",
            ("rust-reference-cast",),
            "let A: i32 = opaque_i32(128);\n    let B: i32 = opaque_i32(0);",
            128,
            0,
        ),
        NativeSmokeCase(
            "powf_promotes_f64",
            "rust",
            "**",
            "A ** B",
            _render_native_expr("A ** B", "rust"),
            "math-floating",
            ("rust-reference-cast", "rust-std-float-methods"),
            "let A: i64 = opaque_i64(3);\n    let B: i64 = opaque_i64(2);",
            3,
            2,
        ),
        NativeSmokeCase(
            "round_cast_i64",
            "rust",
            "round",
            "round(A)",
            _render_native_expr("round(A)", "rust"),
            "math-floating",
            ("rust-reference-cast", "rust-std-float-methods"),
            "let A: i64 = opaque_i64(-2);\n    let B: i64 = opaque_i64(0);",
            -2,
            0,
        ),
        NativeSmokeCase(
            "wrapping_add_overflow",
            "rust",
            "+",
            "A + B",
            "A.wrapping_add(B)",
            "wrapping",
            ("rust-std-overflowing-apis",),
            "let A: i32 = opaque_i32(i32::MAX);\n    let B: i32 = opaque_i32(1);",
            2147483647,
            1,
        ),
        NativeSmokeCase(
            "checked_add_overflow",
            "rust",
            "+",
            "A + B",
            "A.checked_add(B)",
            "checked",
            ("rust-std-overflowing-apis",),
            "let A: i32 = opaque_i32(i32::MAX);\n    let B: i32 = opaque_i32(1);",
            2147483647,
            1,
        ),
        NativeSmokeCase(
            "overflowing_add_overflow",
            "rust",
            "+",
            "A + B",
            "A.overflowing_add(B)",
            "overflowing",
            ("rust-std-overflowing-apis",),
            "let A: i32 = opaque_i32(i32::MAX);\n    let B: i32 = opaque_i32(1);",
            2147483647,
            1,
        ),
        NativeSmokeCase(
            "saturating_add_overflow",
            "rust",
            "+",
            "A + B",
            "A.saturating_add(B)",
            "saturating",
            ("rust-std-overflowing-apis",),
            "let A: i32 = opaque_i32(i32::MAX);\n    let B: i32 = opaque_i32(1);",
            2147483647,
            1,
        ),
        NativeSmokeCase(
            "float_sign_renderer_missing",
            "rust",
            "sign",
            "sign(A)",
            _render_native_expr("sign(A)", "rust"),
            "renderer-fallback",
            ("rust-reference-cast", "rust-std-float-methods"),
            "let A: i64 = opaque_i64(-9);\n    let B: i64 = opaque_i64(0);",
            -9,
            0,
        ),
    ]


def _native_case_base(
    case: NativeSmokeCase,
    profile: str,
    render_path: str,
) -> _JSON_OBJECT:
    """
    Build shared JSON fields for a native smoke case.

    :param case: Native smoke case.
    :type case: NativeSmokeCase
    :param profile: Profile used for the concrete run.
    :type profile: str
    :param render_path: Native render path identifier.
    :type render_path: str
    :return: JSON-compatible base fields.
    :rtype: Dict[str, Any]

    Example::

        >>> case = _java_smoke_cases()[0]
        >>> _native_case_base(case, 'java-int32', 'native_java')['native_only']
        True
        >>> _native_case_base(_java_smoke_cases()[9], 'java-double-math', 'native_java')['inputs']['A']
        -2.5
    """
    return {
        "case_id": "%s:%s" % (profile, case.case_id),
        "semantic_case_id": case.case_id,
        "language": case.language,
        "profile": profile,
        "operator": case.operator,
        "fcstm_expression": case.fcstm_expression,
        "render_path": render_path,
        "render_expression": case.render_expression,
        "native_api_family": case.native_api_family,
        "native_only": True,
        "native_only_reason": _NATIVE_ONLY_REASON,
        "inputs": {"A": case.a_value, "B": case.b_value},
        "source_note_ids": list(case.source_note_ids),
        "status": "unknown",
        "outcome": "unknown",
        "reason": None,
        "commands": {},
    }


def _java_source_for_case(case: NativeSmokeCase) -> str:
    """
    Build Java source for one native smoke case.

    :param case: Java smoke case.
    :type case: NativeSmokeCase
    :return: Java source text.
    :rtype: str

    Example::

        >>> 'class ProbeCase' in _java_source_for_case(_java_smoke_cases()[0])
        True
    """
    return """public final class ProbeCase {
    public static void main(String[] args) {
        %(declarations)s
        try {
            Object result = %(expression)s;
            System.out.println(\"VALUE=\" + String.valueOf(result));
        } catch (RuntimeException err) {
            System.out.println(\"EXCEPTION=\" + err.getClass().getName() + \":\" + err.getMessage());
            System.exit(10);
        }
    }
}
""" % {
        "declarations": case.declarations,
        "expression": case.render_expression,
    }


def _rust_value_expression(case: NativeSmokeCase) -> str:
    """
    Return Rust formatting expression for a case result.

    :param case: Rust smoke case.
    :type case: NativeSmokeCase
    :return: Rust expression that can be formatted with ``{:?}``.
    :rtype: str

    Example::

        >>> _rust_value_expression(_rust_smoke_cases()[0])
        'A + B'
    """
    return case.render_expression


def _rust_source_for_case(case: NativeSmokeCase) -> str:
    """
    Build Rust source for one native smoke case.

    :param case: Rust smoke case.
    :type case: NativeSmokeCase
    :return: Rust source text.
    :rtype: str

    Example::

        >>> 'fn main' in _rust_source_for_case(_rust_smoke_cases()[0])
        True
    """
    return """#![allow(non_snake_case)]
#![allow(unused_variables)]

#[inline(never)]
fn opaque_i32(value: i32) -> i32 {
    std::hint::black_box(value)
}

#[inline(never)]
fn opaque_i64(value: i64) -> i64 {
    std::hint::black_box(value)
}

#[inline(never)]
fn opaque_u32(value: u32) -> u32 {
    std::hint::black_box(value)
}

fn main() {
    %(declarations)s
    let result = %(expression)s;
    println!(\"VALUE={:?}\", result);
}
""" % {
        "declarations": case.declarations,
        "expression": _rust_value_expression(case),
    }


def _java_toolchain() -> _JSON_OBJECT:
    """
    Return Java toolchain metadata.

    :return: Java and ``javac`` availability metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> info = _java_toolchain()
        >>> 'java' in info and 'javac' in info
        True
    """
    return {"java": _probe_command("java"), "javac": _probe_command("javac")}


def _rust_toolchain() -> _JSON_OBJECT:
    """
    Return Rust toolchain metadata.

    :return: ``rustc`` and optional ``cargo`` availability metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> info = _rust_toolchain()
        >>> 'rustc' in info and 'cargo' in info
        True
    """
    return {"rustc": _probe_command("rustc"), "cargo": _probe_command("cargo")}


def _run_java_case(
    case: NativeSmokeCase,
    toolchain: Mapping[str, Any],
    work_dir: Path,
    timeout: int,
) -> _JSON_OBJECT:
    """
    Compile and run one Java smoke case.

    :param case: Java smoke case definition.
    :type case: NativeSmokeCase
    :param toolchain: Java toolchain metadata.
    :type toolchain: Mapping[str, Any]
    :param work_dir: Temporary work directory.
    :type work_dir: pathlib.Path
    :param timeout: Per-command timeout in seconds.
    :type timeout: int
    :return: JSON-compatible case result.
    :rtype: Dict[str, Any]

    Example::

        >>> result = _run_java_case(_java_smoke_cases()[0], {'java': {'available': False}, 'javac': {'available': False}}, Path('.').resolve(), 1)
        >>> result['status']
        'unavailable'
    """
    profile = case.profile or "java-int32"
    result = _native_case_base(case, profile, "native_java")
    if not toolchain.get("java", {}).get("available"):
        result["status"] = "unavailable"
        result["outcome"] = "unavailable"
        result["reason"] = "java_unavailable"
        return result

    case_dir = work_dir / result["case_id"].replace(":", "__")
    case_dir.mkdir(parents=True, exist_ok=True)
    source_path = case_dir / "ProbeCase.java"
    source_path.write_text(_java_source_for_case(case), encoding="utf-8")
    result["source_path"] = str(source_path)
    java_path = str(toolchain["java"]["path"])
    if toolchain.get("javac", {}).get("available"):
        javac_path = str(toolchain["javac"]["path"])
        compile_result = _run_command(
            [javac_path, str(source_path.name)], timeout, case_dir
        )
        result["commands"]["compile"] = compile_result
        if compile_result["timed_out"] or compile_result["returncode"] != 0:
            result["status"] = "compile_failed"
            result["outcome"] = "compile_failed"
            result["reason"] = "javac_failed"
            return result
        run_command = [java_path, "-cp", str(case_dir), "ProbeCase"]
    else:
        result["compile_strategy"] = "java_source_file_launcher"
        run_command = [java_path, str(source_path.name)]
    run_result = _run_command(run_command, timeout, case_dir)
    result["commands"]["run"] = run_result
    if run_result["timed_out"]:
        result["status"] = "runtime_failed"
        result["outcome"] = "runtime_trap"
        result["reason"] = "java_timed_out"
    elif run_result["returncode"] != 0:
        if run_result.get("stdout", "").startswith("EXCEPTION="):
            result["status"] = "runtime_failed"
            result["outcome"] = "runtime_trap"
            result["reason"] = "java_exception_or_nonzero"
        else:
            result["status"] = "compile_failed"
            result["outcome"] = "compile_failed"
            result["reason"] = "java_source_launcher_failed"
    else:
        result["status"] = "passed"
        result["outcome"] = "observed"
    result["stdout"] = run_result.get("stdout", "").strip()
    result["stderr"] = run_result.get("stderr", "").strip()
    return result


def _snapshot_command_result(command: Any) -> Any:
    """
    Normalize command metadata for committed smoke snapshots.

    :param command: Command result or nested JSON-like value.
    :type command: Any
    :return: Snapshot-safe value with local paths removed.
    :rtype: Any

    Example::

        >>> _snapshot_command_result({'args': ['/tmp/case.java'], 'stdout': 'ok'})['args']
        ['<path>']
        >>> _snapshot_command_result({'stdout': 'EXCEPTION=/ by zero'})['stdout']
        'EXCEPTION=/ by zero'
    """
    if isinstance(command, dict):
        normalized = {}
        for key, value in command.items():
            if key == "duration_seconds":
                normalized[key] = "<duration>"
            elif key in {"path", "source_path", "cwd"}:
                normalized[key] = "<path>" if value else value
            else:
                normalized[key] = _snapshot_command_result(value)
        return normalized
    if isinstance(command, list):
        return [
            "<path>" if isinstance(item, str) and "/" in item else item
            for item in command
        ]
    return command


def _snapshot_native_case(case: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Return a native smoke case suitable for committed snapshots.

    :param case: Full local case result.
    :type case: Mapping[str, Any]
    :return: Snapshot case with local path details removed.
    :rtype: Dict[str, Any]

    Example::

        >>> _snapshot_native_case({'case_id': 'x', 'source_path': '/tmp/x'})['source_path']
        '<local>'
    """
    snapshot = json.loads(_stable_json(case))
    if "source_path" in snapshot:
        snapshot["source_path"] = "<local>"
    commands = snapshot.get("commands")
    if isinstance(commands, dict):
        snapshot["commands"] = _snapshot_command_result(commands)
    return snapshot


def _snapshot_toolchain_info(toolchain: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Return snapshot-safe toolchain metadata.

    :param toolchain: Full toolchain metadata.
    :type toolchain: Mapping[str, Any]
    :return: Toolchain metadata with executable paths removed.
    :rtype: Dict[str, Any]

    Example::

        >>> _snapshot_toolchain_info({'java': {'path': '/usr/bin/java'}})['java']['path']
        '<path>'
    """
    snapshot = json.loads(_stable_json(toolchain))
    for item in snapshot.values():
        if isinstance(item, dict) and "path" in item:
            item["path"] = "<path>" if item.get("path") else None
    return snapshot


def _snapshot_native_report(report: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Return a Java or Rust report suitable for committed snapshots.

    :param report: Full Java or Rust smoke report.
    :type report: Mapping[str, Any]
    :return: Snapshot-safe report.
    :rtype: Dict[str, Any]

    Example::

        >>> _snapshot_native_report({'toolchain': {'work_dir': '/tmp'}, 'cases': []})['toolchain']['work_dir']
        '<local>'
    """
    snapshot = json.loads(_stable_json(report))
    toolchain = snapshot.get("toolchain")
    if isinstance(toolchain, dict):
        if "work_dir" in toolchain:
            toolchain["work_dir"] = "<local>"
        if isinstance(toolchain.get("java"), dict):
            toolchain["java"] = _snapshot_toolchain_info(toolchain["java"])
        if isinstance(toolchain.get("rust"), dict):
            toolchain["rust"] = _snapshot_toolchain_info(toolchain["rust"])
    cases = snapshot.get("cases")
    if isinstance(cases, list):
        snapshot["cases"] = [
            _snapshot_native_case(case) if isinstance(case, Mapping) else case
            for case in cases
        ]
    return snapshot


def _rust_profiles() -> List[_JSON_OBJECT]:
    """
    Return Rust profile definitions for smoke runs.

    :return: Rust profile metadata.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> [profile['name'] for profile in _rust_profiles()][0]
        'debug'
    """
    return [
        {
            "name": "debug",
            "flags": ["-C", "opt-level=0"],
            "overflow_checks": "default_debug",
        },
        {
            "name": "release",
            "flags": ["-C", "opt-level=3"],
            "overflow_checks": "default_release",
        },
        {
            "name": "overflow-checks-on",
            "flags": ["-C", "opt-level=3", "-C", "overflow-checks=yes"],
            "overflow_checks": "forced_on",
        },
        {
            "name": "overflow-checks-off",
            "flags": ["-C", "opt-level=0", "-C", "overflow-checks=no"],
            "overflow_checks": "forced_off",
        },
    ]


def _run_rust_case(
    case: NativeSmokeCase,
    profile: Mapping[str, Any],
    toolchain: Mapping[str, Any],
    work_dir: Path,
    timeout: int,
) -> _JSON_OBJECT:
    """
    Compile and run one Rust smoke case under a profile.

    :param case: Rust smoke case definition.
    :type case: NativeSmokeCase
    :param profile: Rust profile metadata.
    :type profile: Mapping[str, Any]
    :param toolchain: Rust toolchain metadata.
    :type toolchain: Mapping[str, Any]
    :param work_dir: Temporary work directory.
    :type work_dir: pathlib.Path
    :param timeout: Per-command timeout in seconds.
    :type timeout: int
    :return: JSON-compatible case result.
    :rtype: Dict[str, Any]

    Example::

        >>> result = _run_rust_case(_rust_smoke_cases()[0], _rust_profiles()[0], {'rustc': {'available': False}}, Path('.').resolve(), 1)
        >>> result['status']
        'unavailable'
    """
    profile_name = str(profile["name"])
    result = _native_case_base(case, profile_name, "native_rust")
    result["overflow_checks"] = profile["overflow_checks"]
    if not toolchain.get("rustc", {}).get("available"):
        result["status"] = "unavailable"
        result["outcome"] = "unavailable"
        result["reason"] = "rustc_unavailable"
        return result

    case_dir = work_dir / result["case_id"].replace(":", "__")
    case_dir.mkdir(parents=True, exist_ok=True)
    source_path = case_dir / "case.rs"
    binary_path = case_dir / "case"
    source_path.write_text(_rust_source_for_case(case), encoding="utf-8")
    result["source_path"] = str(source_path)
    rustc_path = str(toolchain["rustc"]["path"])
    compile_command = [rustc_path, str(source_path), "-o", str(binary_path)] + list(
        profile.get("flags", [])
    )
    compile_result = _run_command(compile_command, timeout, case_dir)
    result["commands"]["compile"] = compile_result
    if compile_result["timed_out"] or compile_result["returncode"] != 0:
        result["status"] = "compile_failed"
        result["outcome"] = "compile_failed"
        result["reason"] = "rustc_failed"
        return result
    run_result = _run_command([str(binary_path)], timeout, case_dir)
    result["commands"]["run"] = run_result
    if run_result["timed_out"]:
        result["status"] = "runtime_failed"
        result["outcome"] = "runtime_trap"
        result["reason"] = "rust_timed_out"
    elif run_result["returncode"] != 0:
        result["status"] = "runtime_failed"
        result["outcome"] = "runtime_trap"
        result["reason"] = "rust_panic_or_nonzero"
    else:
        result["status"] = "passed"
        result["outcome"] = "observed"
    result["stdout"] = run_result.get("stdout", "").strip()
    result["stderr"] = run_result.get("stderr", "").strip()
    return result


def _render_case_expression(case: NumericSmokeCase, render_path: RenderPath) -> str:
    """
    Render a smoke-case expression through the production expression renderer.

    :param case: Smoke case to render.
    :type case: NumericSmokeCase
    :param render_path: Render path from R0 mapping.
    :type render_path: RenderPath
    :return: Target-language expression text.
    :rtype: str

    Example::

        >>> case = NumericSmokeCase('pow', '**', 'A ** B', 3, 2)
        >>> path = RenderPath(
        ...     'builtin_c_style', 'c', 'c', 'c', 'c', {},
        ...     {
        ...         'Name': '{{ node.name }}',
        ...         'BinaryOp(**)': 'pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
        ...     },
        ...     ('builtin_expr_styles.styles.c',),
        ... )
        >>> _render_case_expression(case, path)
        'pow(A, B)'
    """
    from pyfcstm.model.expr import parse_expr_from_string
    from pyfcstm.render.expr import fn_expr_render
    from pyfcstm.utils import to_c_identifier

    env = add_settings_for_env(jinja2.Environment())
    env.filters["to_c_identifier"] = to_c_identifier
    env.globals["to_c_identifier"] = to_c_identifier
    expr = parse_expr_from_string(case.fcstm_expression, mode="numeric")
    render = partial(
        fn_expr_render, templates=dict(render_path.render_templates), env=env
    )
    env.globals["expr_render"] = render
    env.filters["expr_render"] = render
    return render(node=expr.to_ast_node())


def _compiler_candidates(compile_language: str) -> List[str]:
    """
    Return compiler candidates for a compile language.

    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :return: Candidate executable names.
    :rtype: List[str]

    Example::

        >>> 'cc' in _compiler_candidates('c')
        True
    """
    if compile_language == "c":
        return [os.environ.get("CC", ""), "cc", "gcc", "clang", "c99"]
    if compile_language == "cpp":
        return [os.environ.get("CXX", ""), "c++", "g++", "clang++"]
    return []


def _find_compiler(compile_language: str) -> _JSON_OBJECT:
    """
    Find a compiler for one compile language.

    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :return: Compiler metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> info = _find_compiler('c')
        >>> 'available' in info
        True
    """
    checked = []
    for candidate in _compiler_candidates(compile_language):
        if not candidate:
            continue
        checked.append(candidate)
        path = shutil.which(candidate)
        if path:
            return {
                "available": True,
                "name": candidate,
                "path": path,
                "version": _command_version(path),
                "checked": checked,
            }
    return {
        "available": False,
        "name": None,
        "path": None,
        "version": None,
        "checked": checked,
    }


def _run_command(args: Sequence[str], timeout: int, cwd: Path) -> _JSON_OBJECT:
    """
    Run one subprocess command and capture structured diagnostics.

    :param args: Command argument vector.
    :type args: Sequence[str]
    :param timeout: Timeout in seconds.
    :type timeout: int
    :param cwd: Working directory.
    :type cwd: pathlib.Path
    :return: Command result metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> result = _run_command([sys.executable, '--version'], 10, Path('.').resolve())
        >>> result['returncode'] == 0
        True
    """
    started = time.monotonic()
    try:
        result = subprocess.run(
            list(args),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
            check=False,
        )
    except OSError as err:
        # OSError: subprocess could not start the compiler or generated binary;
        # expose this as command metadata instead of hiding the probe outcome.
        return {
            "args": list(args),
            "returncode": None,
            "stdout": "",
            "stderr": str(err),
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 6),
            "start_error": err.__class__.__name__,
        }
    except subprocess.TimeoutExpired as err:
        # TimeoutExpired: native smoke programs must not hang the research
        # command; report the timeout as a runtime/compile diagnostic.
        return {
            "args": list(args),
            "returncode": None,
            "stdout": err.stdout or "",
            "stderr": err.stderr or "",
            "timed_out": True,
            "duration_seconds": round(time.monotonic() - started, 6),
            "start_error": None,
        }
    return {
        "args": list(args),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": False,
        "duration_seconds": round(time.monotonic() - started, 6),
        "start_error": None,
    }


def _base_compile_flags(compile_language: str) -> List[str]:
    """
    Return compile-only flags for one compile language.

    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :return: Compiler flags.
    :rtype: List[str]

    Example::

        >>> '-Wall' in _base_compile_flags('c')
        True
    """
    if compile_language == "c":
        return ["-std=c99", "-Wall", "-Wextra", "-Werror=implicit-function-declaration"]
    return ["-Wall", "-Wextra"]


def _sanitizer_flags(compile_language: str) -> List[str]:
    """
    Return sanitizer flags for one compile language.

    :param compile_language: ``"c`` or ``"cpp"``.
    :type compile_language: str
    :return: Sanitizer flags.
    :rtype: List[str]

    Example::

        >>> _sanitizer_flags('c')[0].startswith('-fsanitize=')
        True
    """
    if compile_language == "c":
        return list(_C_SANITIZER_FLAGS)
    return list(_CPP_SANITIZER_FLAGS)


def _link_flags(compile_language: str) -> List[str]:
    """
    Return linker flags for one compile language.

    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :return: Linker flags.
    :rtype: List[str]

    Example::

        >>> '-lm' in _link_flags('c')
        True
    """
    return ["-lm"]


def _source_for_case(
    expression: str, case: NumericSmokeCase, compile_language: str
) -> str:
    """
    Build a tiny C or C++ source file for one rendered expression.

    :param expression: Rendered expression text.
    :type expression: str
    :param case: Smoke case whose values populate variables.
    :type case: NumericSmokeCase
    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :return: Source code.
    :rtype: str

    Example::

        >>> 'int main' in _source_for_case('A + B', NumericSmokeCase('add', '+', 'A + B', 1, 2), 'c')
        True
    """
    if compile_language == "cpp":
        return (
            """#include <cmath>\n#include <cstdlib>\n#include <iostream>\n\nstruct Scope { long long A; long long B; };\n\nint main() {\n    long long A = %(a)dLL;\n    long long B = %(b)dLL;\n    Scope scope_value = {A, B};\n    Scope *scope = &scope_value;\n    volatile double result = static_cast<double>(%(expr)s);\n    std::cout << result << "\\n";\n    return 0;\n}\n"""
            % {
                "a": case.a_value,
                "b": case.b_value,
                "expr": expression,
            }
        )
    return (
        """#include <math.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n\nstruct Scope { int64_t A; int64_t B; };\n\nint main(void) {\n    int64_t A = %(a)dLL;\n    int64_t B = %(b)dLL;\n    struct Scope scope_value = {A, B};\n    struct Scope *scope = &scope_value;\n    volatile double result = (double)(%(expr)s);\n    printf("%%.17g\\n", result);\n    return 0;\n}\n"""
        % {
            "a": case.a_value,
            "b": case.b_value,
            "expr": expression,
        }
    )


def _compile_and_link(
    compiler: Mapping[str, Any],
    source_path: Path,
    binary_path: Path,
    compile_language: str,
    timeout: int,
    extra_flags: Optional[Iterable[str]] = None,
) -> Tuple[str, _JSON_OBJECT]:
    """
    Compile and link one smoke source file.

    :param compiler: Compiler metadata from :func:`_find_compiler`.
    :type compiler: Mapping[str, Any]
    :param source_path: Source file path.
    :type source_path: pathlib.Path
    :param binary_path: Output binary path.
    :type binary_path: pathlib.Path
    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :param timeout: Command timeout in seconds.
    :type timeout: int
    :param extra_flags: Optional extra compile/link flags.
    :type extra_flags: Optional[Iterable[str]], optional
    :return: Tuple of step status and command metadata.
    :rtype: Tuple[str, Dict[str, Any]]

    Example::

        >>> compiler = _find_compiler('c')
        >>> isinstance(compiler['available'], bool)
        True
    """
    object_path = source_path.with_suffix(".o")
    compiler_path = str(compiler["path"])
    flags = _base_compile_flags(compile_language) + list(extra_flags or [])
    compile_command = (
        [compiler_path] + flags + ["-c", str(source_path), "-o", str(object_path)]
    )
    compile_result = _run_command(compile_command, timeout, source_path.parent)
    commands = {"compile": compile_result}
    if compile_result["timed_out"] or compile_result["returncode"] != 0:
        return "compile_failed", commands
    link_command = (
        [compiler_path, str(object_path), "-o", str(binary_path)]
        + list(extra_flags or [])
        + _link_flags(compile_language)
    )
    link_result = _run_command(link_command, timeout, source_path.parent)
    commands["link"] = link_result
    if link_result["timed_out"] or link_result["returncode"] != 0:
        return "link_failed", commands
    return "linked", commands


def _check_sanitizer_available(
    compiler: Mapping[str, Any], compile_language: str, work_dir: Path, timeout: int
) -> _JSON_OBJECT:
    """
    Check whether the selected compiler accepts the sanitizer flags.

    :param compiler: Compiler metadata from :func:`_find_compiler`.
    :type compiler: Mapping[str, Any]
    :param compile_language: ``"c"`` or ``"cpp"``.
    :type compile_language: str
    :param work_dir: Temporary working directory.
    :type work_dir: pathlib.Path
    :param timeout: Command timeout in seconds.
    :type timeout: int
    :return: Sanitizer availability metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> import tempfile
        >>> compiler = _find_compiler('c')
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     info = ({'available': False} if not compiler['available'] else _check_sanitizer_available(compiler, 'c', Path(tmp), 1))
        >>> 'available' in info
        True
    """
    source_path = work_dir / (
        "sanitizer_check.%s" % ("c" if compile_language == "c" else "cpp")
    )
    binary_path = work_dir / "sanitizer_check"
    if compile_language == "cpp":
        source_path.write_text("int main() { return 0; }\n", encoding="utf-8")
    else:
        source_path.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    status, commands = _compile_and_link(
        compiler,
        source_path,
        binary_path,
        compile_language,
        timeout,
        extra_flags=_sanitizer_flags(compile_language),
    )
    return {
        "available": status == "linked",
        "status": "available" if status == "linked" else "sanitizer_unavailable",
        "flags": _sanitizer_flags(compile_language),
        "commands": commands,
    }


def _run_one_case(
    case: NumericSmokeCase,
    render_path: RenderPath,
    compiler: Mapping[str, Any],
    sanitizer: Mapping[str, Any],
    work_dir: Path,
    timeout: int,
) -> _JSON_OBJECT:
    """
    Compile and run one rendered smoke case.

    :param case: Smoke case definition.
    :type case: NumericSmokeCase
    :param render_path: Render path definition.
    :type render_path: RenderPath
    :param compiler: Compiler metadata for ``render_path.compile_language``.
    :type compiler: Mapping[str, Any]
    :param sanitizer: Sanitizer availability metadata.
    :type sanitizer: Mapping[str, Any]
    :param work_dir: Temporary working directory.
    :type work_dir: pathlib.Path
    :param timeout: Per-command timeout in seconds.
    :type timeout: int
    :return: JSON-compatible case result.
    :rtype: Dict[str, Any]

    Example::

        >>> case = NumericSmokeCase('pow', '**', 'A ** B', 3, 2)
        >>> path = RenderPath(
        ...     'builtin_c_style', 'c', 'c', 'c', 'c', {},
        ...     {
        ...         'Name': '{{ node.name }}',
        ...         'BinaryOp(**)': 'pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
        ...     },
        ...     ('builtin_expr_styles.styles.c',),
        ... )
        >>> result = _run_one_case(case, path, {'available': False}, {'available': False}, Path('.').resolve(), 1)
        >>> result['status']
        'unavailable'
    """
    rendered = _render_case_expression(case, render_path)
    case_id = "%s:%s" % (render_path.path_id, case.case_id)
    result = {
        "case_id": case_id,
        "operator": case.operator,
        "fcstm_expression": case.fcstm_expression,
        "render_expression": rendered,
        "render_path": render_path.path_id,
        "compile_language": render_path.compile_language,
        "mapping_sources": list(render_path.mapping_sources),
        "status": "unknown",
        "reason": None,
        "commands": {},
        "sanitizer": {
            "available": bool(sanitizer.get("available")),
            "status": sanitizer.get("status", "sanitizer_unavailable"),
        },
    }
    if not compiler.get("available"):
        result["status"] = "unavailable"
        result["reason"] = "compiler_unavailable"
        return result

    case_dir = work_dir / case_id.replace(":", "__")
    case_dir.mkdir(parents=True, exist_ok=True)
    suffix = "c" if render_path.compile_language == "c" else "cpp"
    source_path = case_dir / ("case.%s" % suffix)
    binary_path = case_dir / "case"
    source_path.write_text(
        _source_for_case(rendered, case, render_path.compile_language),
        encoding="utf-8",
    )
    result["source_path"] = str(source_path)

    build_status, commands = _compile_and_link(
        compiler,
        source_path,
        binary_path,
        render_path.compile_language,
        timeout,
    )
    result["commands"].update(commands)
    if build_status != "linked":
        result["status"] = build_status
        result["reason"] = build_status
        return result

    run_result = _run_command([str(binary_path)], timeout, case_dir)
    result["commands"]["run"] = run_result
    if run_result["timed_out"] or run_result["returncode"] != 0:
        result["status"] = "runtime_failed"
        result["reason"] = (
            "program_timed_out"
            if run_result["timed_out"]
            else "program_returned_nonzero"
        )
    else:
        result["status"] = "passed"

    if sanitizer.get("available"):
        sanitizer_binary = case_dir / "case_sanitized"
        sanitizer_status, sanitizer_commands = _compile_and_link(
            compiler,
            source_path,
            sanitizer_binary,
            render_path.compile_language,
            timeout,
            extra_flags=_sanitizer_flags(render_path.compile_language),
        )
        sanitizer_result = {
            "available": True,
            "status": sanitizer_status,
            "commands": sanitizer_commands,
        }
        if sanitizer_status == "linked":
            sanitizer_run = _run_command([str(sanitizer_binary)], timeout, case_dir)
            sanitizer_result["commands"]["run"] = sanitizer_run
            if sanitizer_run["timed_out"] or sanitizer_run["returncode"] != 0:
                sanitizer_result["status"] = "sanitizer_failed"
                if result["status"] == "passed":
                    result["status"] = "sanitizer_failed"
                    result["reason"] = "sanitizer_detected_numeric_undefined_behavior"
            else:
                sanitizer_result["status"] = "passed"
        result["sanitizer"] = sanitizer_result
    return result


def validate_probe_summary(summary: Mapping[str, Any]) -> List[str]:
    """
    Validate the lightweight probe-summary contract used by smoke probes.

    The validation intentionally avoids a third-party JSON Schema dependency so
    the research command remains usable in minimal environments.

    :param summary: Probe summary to validate.
    :type summary: Mapping[str, Any]
    :return: Human-readable diagnostics. Empty means valid.
    :rtype: List[str]

    Example::

        >>> errors = validate_probe_summary({'schema_version': 1})
        >>> errors[:4]
        ['missing required key: source_mapping_sha256', 'missing required key: language', 'missing required key: toolchain', 'missing required key: cases']
    """
    errors = []
    required = [
        "schema_version",
        "source_mapping_sha256",
        "language",
        "toolchain",
        "cases",
    ]
    for key in required:
        if key not in summary:
            errors.append("missing required key: %s" % key)
    if summary.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    source_sha = summary.get("source_mapping_sha256")
    if not isinstance(source_sha, str) or len(source_sha) != 64:
        errors.append("source_mapping_sha256 must be a 64-character hex string")
    if not isinstance(summary.get("toolchain"), dict):
        errors.append("toolchain must be a mapping")
    cases = summary.get("cases")
    allowed_statuses = {
        "passed",
        "compile_failed",
        "link_failed",
        "runtime_failed",
        "sanitizer_failed",
        "skipped",
        "unavailable",
        "unknown",
    }
    if not isinstance(cases, list):
        errors.append("cases must be a list")
        return errors
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append("case %d must be a mapping" % index)
            continue
        for key in ["case_id", "render_expression", "status"]:
            if key not in case:
                errors.append("case %d missing required key: %s" % (index, key))
        if case.get("status") not in allowed_statuses:
            errors.append(
                "case %d has invalid status: %r" % (index, case.get("status"))
            )
    return errors


def _native_smoke_schema_path(mode: str) -> str:
    """
    Return the schema path for a Java/Rust smoke mode.

    :param mode: Java/Rust smoke mode.
    :type mode: str
    :return: Repository-relative schema path.
    :rtype: str
    :raises ValueError: If ``mode`` is not a supported Java/Rust smoke mode.

    Example::

        >>> _native_smoke_schema_path('java-rust-smoke').endswith('java_rust_smoke.schema.json')
        True
    """
    if mode not in _JAVA_RUST_MODES:
        raise ValueError("Unsupported Java/Rust smoke mode: %s" % mode)
    return _JAVA_RUST_SMOKE_SCHEMA


def _native_smoke_repository(mapping_file: Path, root: Path, mode: str) -> _JSON_OBJECT:
    """
    Build repository metadata for Java/Rust smoke payloads.

    :param mapping_file: Resolved mapping snapshot path.
    :type mapping_file: pathlib.Path
    :param root: Repository root.
    :type root: pathlib.Path
    :param mode: Java/Rust smoke mode.
    :type mode: str
    :return: Repository metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> repo = _native_smoke_repository(Path('.').resolve() / _DEFAULT_MAPPING_PATH, Path('.').resolve(), 'java-smoke')
        >>> repo['root']
        '.'
    """
    try:
        mapping_snapshot = mapping_file.relative_to(root).as_posix()
    except ValueError:
        # ValueError: caller supplied an absolute mapping path outside the repo;
        # keep it explicit because committed snapshots use repo-relative paths.
        mapping_snapshot = str(mapping_file)
    return {
        "root": ".",
        "render_mapping_snapshot": mapping_snapshot,
        "schema_path": _native_smoke_schema_path(mode),
    }


def _native_smoke_generator(root: Path) -> _JSON_OBJECT:
    """
    Build generator metadata for Java/Rust smoke payloads.

    :param root: Repository root.
    :type root: pathlib.Path
    :return: Generator metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> _native_smoke_generator(Path('.').resolve())['tool']
        'tools/numeric_render_probe.py'
    """
    return {
        "tool": "tools/numeric_render_probe.py",
        "research_path": _RESEARCH_PATH,
        "source_commit": _git_commit(root),
        "source_commit_policy": "Best-effort commit at generation time; schema, mapping digest and case-plan invariants are stable comparison keys.",
        "determinism": "Native tool availability and compiler/runtime results are environment-dependent; --check validates shape and invariants rather than exact stdout.",
    }


def _build_java_smoke_report(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
    work_dir: Optional[Union[str, Path]] = None,
    timeout: int = 10,
) -> _JSON_OBJECT:
    """
    Build a Java native smoke report.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping path, defaults to the committed R0
        snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :param work_dir: Optional directory for temporary compile artifacts.
    :type work_dir: Optional[Union[str, pathlib.Path]], optional
    :param timeout: Per-command timeout in seconds, defaults to ``10``.
    :type timeout: int, optional
    :return: JSON-compatible Java smoke summary.
    :rtype: Dict[str, Any]

    Example::

        >>> report = _build_java_smoke_report(timeout=1)
        >>> report['language']
        'java'
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    mapping_sha = mapping.get("mapping_sha256")
    if not isinstance(mapping_sha, str):
        mapping_sha = ""
    toolchain = _java_toolchain()
    if work_dir is None:
        temp_parent = root / _RESEARCH_PATH / "results" / "local"
        temp_parent.mkdir(parents=True, exist_ok=True)
        temp_context = tempfile.TemporaryDirectory(
            prefix="java-smoke-", dir=str(temp_parent)
        )
        cleanup = temp_context.cleanup
        active_work_dir = Path(temp_context.name)
    else:
        active_work_dir = Path(work_dir).resolve()
        active_work_dir.mkdir(parents=True, exist_ok=True)
        cleanup = None
    try:
        cases = [
            _run_java_case(case, toolchain, active_work_dir, timeout)
            for case in _java_smoke_cases()
        ]
        payload = {
            "schema_version": 1,
            "mode": "java-smoke",
            "language": "java",
            "source_mapping_sha256": mapping_sha,
            "render_mapping_sha256": mapping_sha,
            "summary_status": _summary_status(cases),
            "generator": _native_smoke_generator(root),
            "repository": _native_smoke_repository(mapping_file, root, "java-smoke"),
            "toolchain": {
                "java": toolchain,
                "timeout_seconds": timeout,
                "work_dir": str(active_work_dir),
            },
            "render_paths": [
                {
                    "path_id": "native_java",
                    "language": "java",
                    "kind": "native_only",
                    "native_only_reason": _NATIVE_ONLY_REASON,
                    "mapping_sources": ["builtin_expr_styles.styles.java"],
                }
            ],
            "official_source_notes": _official_source_notes("java"),
            "cases": cases,
        }
        errors = validate_java_rust_smoke(payload, expected_mode="java-smoke")
        if errors:
            payload["summary_status"] = "invalid"
            payload["validation_errors"] = errors
        return payload
    finally:
        if cleanup is not None:
            cleanup()


def _build_rust_smoke_report(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
    work_dir: Optional[Union[str, Path]] = None,
    timeout: int = 10,
) -> _JSON_OBJECT:
    """
    Build a Rust native smoke report.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping path, defaults to the committed R0
        snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :param work_dir: Optional directory for temporary compile artifacts.
    :type work_dir: Optional[Union[str, pathlib.Path]], optional
    :param timeout: Per-command timeout in seconds, defaults to ``10``.
    :type timeout: int, optional
    :return: JSON-compatible Rust smoke summary.
    :rtype: Dict[str, Any]

    Example::

        >>> report = _build_rust_smoke_report(timeout=1)
        >>> report['language']
        'rust'
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    mapping_sha = mapping.get("mapping_sha256")
    if not isinstance(mapping_sha, str):
        mapping_sha = ""
    toolchain = _rust_toolchain()
    if work_dir is None:
        temp_parent = root / _RESEARCH_PATH / "results" / "local"
        temp_parent.mkdir(parents=True, exist_ok=True)
        temp_context = tempfile.TemporaryDirectory(
            prefix="rust-smoke-", dir=str(temp_parent)
        )
        cleanup = temp_context.cleanup
        active_work_dir = Path(temp_context.name)
    else:
        active_work_dir = Path(work_dir).resolve()
        active_work_dir.mkdir(parents=True, exist_ok=True)
        cleanup = None
    try:
        cases = []
        profiles = _rust_profiles()
        for profile in profiles:
            for case in _rust_smoke_cases():
                cases.append(
                    _run_rust_case(case, profile, toolchain, active_work_dir, timeout)
                )
        payload = {
            "schema_version": 1,
            "mode": "rust-smoke",
            "language": "rust",
            "source_mapping_sha256": mapping_sha,
            "render_mapping_sha256": mapping_sha,
            "summary_status": _summary_status(cases),
            "generator": _native_smoke_generator(root),
            "repository": _native_smoke_repository(mapping_file, root, "rust-smoke"),
            "toolchain": {
                "rust": toolchain,
                "profiles": profiles,
                "timeout_seconds": timeout,
                "work_dir": str(active_work_dir),
            },
            "render_paths": [
                {
                    "path_id": "native_rust",
                    "language": "rust",
                    "kind": "native_only",
                    "native_only_reason": _NATIVE_ONLY_REASON,
                    "mapping_sources": ["builtin_expr_styles.styles.rust"],
                }
            ],
            "official_source_notes": _official_source_notes("rust"),
            "cases": cases,
        }
        errors = validate_java_rust_smoke(payload, expected_mode="rust-smoke")
        if errors:
            payload["summary_status"] = "invalid"
            payload["validation_errors"] = errors
        return payload
    finally:
        if cleanup is not None:
            cleanup()


def build_java_rust_smoke_report(
    mode: str,
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
    work_dir: Optional[Union[str, Path]] = None,
    timeout: int = 10,
) -> _JSON_OBJECT:
    """
    Build Java, Rust or aggregate Java/Rust smoke reports.

    :param mode: ``"java-smoke"``, ``"rust-smoke"`` or ``"java-rust-smoke"``.
    :type mode: str
    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping path, defaults to the committed R0
        snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :param work_dir: Optional directory for temporary compile artifacts.
    :type work_dir: Optional[Union[str, pathlib.Path]], optional
    :param timeout: Per-command timeout in seconds, defaults to ``10``.
    :type timeout: int, optional
    :return: JSON-compatible smoke payload.
    :rtype: Dict[str, Any]
    :raises ValueError: If ``mode`` is not a Java/Rust smoke mode.

    Example::

        >>> report = build_java_rust_smoke_report('java-rust-smoke', timeout=1)
        >>> report['mode']
        'java-rust-smoke'
    """
    if mode == "java-smoke":
        return _build_java_smoke_report(repo_root, mapping_path, work_dir, timeout)
    if mode == "rust-smoke":
        return _build_rust_smoke_report(repo_root, mapping_path, work_dir, timeout)
    if mode != "java-rust-smoke":
        raise ValueError("Unsupported Java/Rust smoke mode: %s" % mode)

    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    java_work_dir = None
    rust_work_dir = None
    if work_dir is not None:
        base_work_dir = Path(work_dir).resolve()
        java_work_dir = base_work_dir / "java"
        rust_work_dir = base_work_dir / "rust"
    java_report = _snapshot_native_report(
        _build_java_smoke_report(root, mapping_file, java_work_dir, timeout)
    )
    rust_report = _snapshot_native_report(
        _build_rust_smoke_report(root, mapping_file, rust_work_dir, timeout)
    )
    mapping_sha = java_report.get("source_mapping_sha256", "")
    languages = {"java": java_report, "rust": rust_report}
    cases = list(java_report.get("cases", [])) + list(rust_report.get("cases", []))
    payload = {
        "schema_version": 1,
        "mode": "java-rust-smoke",
        "language": "java-rust",
        "source_mapping_sha256": mapping_sha,
        "render_mapping_sha256": mapping_sha,
        "summary_status": _summary_status(cases),
        "generator": _native_smoke_generator(root),
        "repository": _native_smoke_repository(mapping_file, root, "java-rust-smoke"),
        "toolchain": {
            "java": java_report.get("toolchain", {}).get("java", {}),
            "rust": rust_report.get("toolchain", {}).get("rust", {}),
            "timeout_seconds": timeout,
        },
        "languages": languages,
        "official_source_notes": {
            "java": java_report.get("official_source_notes", []),
            "rust": rust_report.get("official_source_notes", []),
        },
        "cases": cases,
    }
    errors = validate_java_rust_smoke(payload, expected_mode="java-rust-smoke")
    if errors:
        payload["summary_status"] = "invalid"
        payload["validation_errors"] = errors
    return payload


def _required_native_case_ids(language: str) -> List[str]:
    """
    Return expected case ids for a Java or Rust smoke report.

    :param language: ``"java"`` or ``"rust"``.
    :type language: str
    :return: Expected semantic case ids.
    :rtype: List[str]
    :raises ValueError: If ``language`` is not a supported native smoke
        language.

    Example::

        >>> 'shift_count_masking' in _required_native_case_ids('java')
        True
    """
    if language == "java":
        return [case.case_id for case in _java_smoke_cases()]
    if language == "rust":
        return [case.case_id for case in _rust_smoke_cases()]
    raise ValueError("Unsupported native case language: %s" % language)


def _native_case_plan_by_id(language: str) -> Mapping[str, NativeSmokeCase]:
    """
    Return native smoke case plans keyed by semantic case id.

    :param language: ``"java"`` or ``"rust"``.
    :type language: str
    :return: Case plan mapping.
    :rtype: Mapping[str, NativeSmokeCase]
    :raises ValueError: If ``language`` is not a supported native smoke
        language.

    Example::

        >>> _native_case_plan_by_id('java')['math_round_half_up'].a_value
        -2.5
    """
    if language == "java":
        return {case.case_id: case for case in _java_smoke_cases()}
    if language == "rust":
        return {case.case_id: case for case in _rust_smoke_cases()}
    raise ValueError("Unsupported native case language: %s" % language)


def _validate_native_cases(
    cases: Any, language: str, path: str, require_all_profiles: bool = False
) -> List[str]:
    """
    Validate native smoke cases for shared join-key compatibility.

    :param cases: Case list to validate.
    :type cases: Any
    :param language: Expected language.
    :type language: str
    :param path: Human-readable path.
    :type path: str
    :param require_all_profiles: Whether Rust profile coverage must be checked.
    :type require_all_profiles: bool, optional
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_native_cases([], 'java', '$.cases')[:1]
        ['$.cases must be a non-empty list']
        >>> java_cases = [
        ...     _native_case_base(case, case.profile or 'java-int32', 'native_java')
        ...     for case in _java_smoke_cases()
        ... ]
        >>> java_cases[0]['render_path'] = 'native_rust'
        >>> '$.cases[0].render_path must be native_java' in _validate_native_cases(java_cases, 'java', '$.cases')
        True
        >>> java_cases[0]['render_expression'] = ''
        >>> '$.cases[0].render_expression must be a non-empty string' in _validate_native_cases(java_cases, 'java', '$.cases')
        True
        >>> java_cases = [
        ...     _native_case_base(case, case.profile or 'java-int32', 'native_java')
        ...     for case in _java_smoke_cases()
        ... ]
        >>> java_cases[9]['inputs']['A'] = -2
        >>> '$.cases[9].inputs.A must match case plan value -2.5' in _validate_native_cases(java_cases, 'java', '$.cases')
        True
        >>> java_cases[9]['inputs']['C'] = 99
        >>> '$.cases[9].inputs has unexpected keys: C' in _validate_native_cases(java_cases, 'java', '$.cases')
        True
        >>> java_cases = [
        ...     _native_case_base(case, case.profile or 'java-int32', 'native_java')
        ...     for case in _java_smoke_cases()
        ... ]
        >>> java_cases[0]['status'] = 'passed'
        >>> '$.cases[0].passed status requires observed outcome' in _validate_native_cases(java_cases, 'java', '$.cases')
        True
    """
    errors: List[str] = []
    if not isinstance(cases, list) or not cases:
        return ["%s must be a non-empty list" % path]
    required_fields = {
        "case_id",
        "semantic_case_id",
        "operator",
        "fcstm_expression",
        "render_path",
        "render_expression",
        "language",
        "profile",
        "status",
        "outcome",
        "native_only",
        "native_only_reason",
        "native_api_family",
        "source_note_ids",
        "commands",
    }
    shared_join_fields = [
        "case_id",
        "operator",
        "fcstm_expression",
        "render_path",
        "render_expression",
    ]
    expected_render_path = {
        "java": "native_java",
        "rust": "native_rust",
    }[language]
    case_plan = _native_case_plan_by_id(language)
    seen_semantic_ids = set()
    profile_seen: Dict[str, set] = {}
    allowed_statuses = {
        "passed",
        "compile_failed",
        "runtime_failed",
        "skipped",
        "unavailable",
        "unknown",
    }
    allowed_outcomes = {
        "observed",
        "compile_failed",
        "runtime_trap",
        "unavailable",
        "unknown",
    }
    for index, case in enumerate(cases):
        case_path = "%s[%d]" % (path, index)
        if not isinstance(case, Mapping):
            errors.append("%s must be a mapping" % case_path)
            continue
        missing = sorted(required_fields - set(case))
        if missing:
            errors.append(
                "%s missing required fields: %s" % (case_path, ", ".join(missing))
            )
        for field in shared_join_fields:
            if not isinstance(case.get(field), str) or not case.get(field):
                errors.append("%s.%s must be a non-empty string" % (case_path, field))
        semantic_id = case.get("semantic_case_id")
        if not isinstance(semantic_id, str) or not semantic_id:
            errors.append("%s.semantic_case_id must be a non-empty string" % case_path)
            semantic_id = None
        if case.get("language") != language:
            errors.append("%s.language must be %s" % (case_path, language))
        if case.get("render_path") != expected_render_path:
            errors.append(
                "%s.render_path must be %s" % (case_path, expected_render_path)
            )
        if case.get("status") not in allowed_statuses:
            errors.append("%s.status is invalid: %r" % (case_path, case.get("status")))
        if case.get("outcome") not in allowed_outcomes:
            errors.append(
                "%s.outcome is invalid: %r" % (case_path, case.get("outcome"))
            )
        expected_outcome = _NATIVE_CASE_STATUS_OUTCOMES.get(str(case.get("status")))
        if expected_outcome is not None and case.get("outcome") != expected_outcome:
            errors.append(
                "%s.%s status requires %s outcome"
                % (case_path, case.get("status"), expected_outcome)
            )
        if case.get("status") == "passed" and case.get("reason") is not None:
            errors.append("%s.passed status requires null reason" % case_path)
        if case.get("status") in {"compile_failed", "runtime_failed", "unavailable"}:
            if not isinstance(case.get("reason"), str) or not case.get("reason"):
                errors.append(
                    "%s.%s status requires a non-empty reason"
                    % (case_path, case.get("status"))
                )
        if case.get("native_only") is not True:
            errors.append("%s.native_only must be true" % case_path)
        if case.get("native_only_reason") != _NATIVE_ONLY_REASON:
            errors.append("%s.native_only_reason is invalid" % case_path)
        source_ids = case.get("source_note_ids")
        if not isinstance(source_ids, list) or not source_ids:
            errors.append("%s.source_note_ids must be a non-empty list" % case_path)
        if semantic_id is not None:
            plan = case_plan.get(semantic_id)
            if plan is None:
                errors.append("%s.semantic_case_id is not in the case plan" % case_path)
            else:
                expected_profile = plan.profile or str(case.get("profile"))
                if not require_all_profiles and case.get("profile") != expected_profile:
                    errors.append(
                        "%s.profile must match case plan profile %s"
                        % (case_path, expected_profile)
                    )
                expected_case_id = "%s:%s" % (case.get("profile"), semantic_id)
                if case.get("case_id") != expected_case_id:
                    errors.append(
                        "%s.case_id must match profile-scoped id %s"
                        % (case_path, expected_case_id)
                    )
                for field, expected_value in [
                    ("operator", plan.operator),
                    ("fcstm_expression", plan.fcstm_expression),
                    ("render_expression", plan.render_expression),
                    ("native_api_family", plan.native_api_family),
                ]:
                    if case.get(field) != expected_value:
                        errors.append(
                            "%s.%s must match case plan value %r"
                            % (case_path, field, expected_value)
                        )
                if source_ids != list(plan.source_note_ids):
                    errors.append(
                        "%s.source_note_ids must match case plan value %r"
                        % (case_path, list(plan.source_note_ids))
                    )
                inputs = case.get("inputs")
                if not isinstance(inputs, Mapping):
                    errors.append("%s.inputs must be a mapping" % case_path)
                else:
                    allowed_input_keys = {"A", "B"}
                    extra_input_keys = sorted(set(inputs) - allowed_input_keys)
                    if extra_input_keys:
                        errors.append(
                            "%s.inputs has unexpected keys: %s"
                            % (case_path, ", ".join(extra_input_keys))
                        )
                    for key, expected_value in [
                        ("A", plan.a_value),
                        ("B", plan.b_value),
                    ]:
                        if not _json_number_equals(inputs.get(key), expected_value):
                            errors.append(
                                "%s.inputs.%s must match case plan value %r"
                                % (case_path, key, expected_value)
                            )
                commands = case.get("commands")
                if not isinstance(commands, Mapping):
                    errors.append("%s.commands must be a mapping" % case_path)
                else:
                    for command_name, command_result in commands.items():
                        if not isinstance(command_name, str) or not command_name:
                            errors.append(
                                "%s.commands has an invalid command key" % case_path
                            )
                            continue
                        errors.extend(
                            _validate_command_result(
                                command_result,
                                "%s.commands.%s" % (case_path, command_name),
                            )
                        )
                    if case.get("status") == "passed" and "run" not in commands:
                        errors.append(
                            "%s.passed status requires commands.run" % case_path
                        )
                    if case.get("status") == "runtime_failed" and "run" not in commands:
                        errors.append(
                            "%s.runtime_failed status requires commands.run" % case_path
                        )
                    if case.get("status") == "compile_failed" and not commands:
                        errors.append(
                            "%s.compile_failed status requires command diagnostics"
                            % case_path
                        )
                    if case.get("status") == "unavailable" and commands:
                        errors.append(
                            "%s.unavailable status requires empty commands" % case_path
                        )
            seen_semantic_ids.add(semantic_id)
            profile = str(case.get("profile"))
            profile_seen.setdefault(semantic_id, set()).add(profile)
    missing_cases = sorted(set(_required_native_case_ids(language)) - seen_semantic_ids)
    for case_id in missing_cases:
        errors.append("%s missing semantic case: %s" % (path, case_id))
    if require_all_profiles:
        expected_profiles = {profile["name"] for profile in _rust_profiles()}
        for case_id in _required_native_case_ids(language):
            if case_id in missing_cases:
                continue
            actual_profiles = profile_seen.get(case_id, set())
            if actual_profiles != expected_profiles:
                errors.append(
                    "%s semantic case %s must cover Rust profiles %s, got %s"
                    % (
                        path,
                        case_id,
                        sorted(expected_profiles),
                        sorted(actual_profiles),
                    )
                )
    return errors


def _validate_command_result(command: Any, path: str) -> List[str]:
    """
    Validate one captured native command result.

    :param command: Command result payload.
    :type command: Any
    :param path: Human-readable path.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_command_result({'args': [], 'returncode': 0, 'stdout': '', 'stderr': '', 'timed_out': False, 'duration_seconds': '<duration>', 'start_error': None}, '$.commands.run')
        []
        >>> _validate_command_result({}, '$.commands.run')[:1]
        ['$.commands.run missing required fields: args, duration_seconds, returncode, start_error, stderr, stdout, timed_out']
    """
    if not isinstance(command, Mapping):
        return ["%s must be a mapping" % path]
    errors = []
    required_fields = {
        "args",
        "returncode",
        "stdout",
        "stderr",
        "timed_out",
        "duration_seconds",
        "start_error",
    }
    missing = sorted(required_fields - set(command))
    if missing:
        errors.append("%s missing required fields: %s" % (path, ", ".join(missing)))
    args = command.get("args")
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        errors.append("%s.args must be a string array" % path)
    returncode = command.get("returncode")
    if returncode is not None and (
        not isinstance(returncode, int) or isinstance(returncode, bool)
    ):
        errors.append("%s.returncode must be an integer or null" % path)
    for key in ["stdout", "stderr"]:
        if not isinstance(command.get(key), str):
            errors.append("%s.%s must be a string" % (path, key))
    if not isinstance(command.get("timed_out"), bool):
        errors.append("%s.timed_out must be a boolean" % path)
    duration = command.get("duration_seconds")
    if not (
        (isinstance(duration, (int, float)) and not isinstance(duration, bool))
        or isinstance(duration, str)
    ):
        errors.append("%s.duration_seconds must be a number or snapshot string" % path)
    start_error = command.get("start_error")
    if start_error is not None and not isinstance(start_error, str):
        errors.append("%s.start_error must be a string or null" % path)
    return errors


def _validate_native_status_expectation(
    case: Mapping[str, Any], language: str, case_path: str
) -> List[str]:
    """
    Validate known status expectations for environment-independent cases.

    Java source-file launcher behavior is deterministic enough for the current
    native-only snapshot: arithmetic traps and the intentionally unsupported
    ``sign`` renderer fallback must not be rewritten as successful observations.
    Rust source snippets also have deterministic pass/trap/compile-failure
    classes once ``rustc`` is available; profile-sensitive overflow checks are
    keyed by the committed Rust profile names.

    :param case: Native case result.
    :type case: Mapping[str, Any]
    :param language: Expected language.
    :type language: str
    :param case_path: Human-readable path.
    :type case_path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> case = _native_case_base(_java_smoke_cases()[3], 'java-int32', 'native_java')
        >>> case['status'] = 'passed'
        >>> _validate_native_status_expectation(case, 'java', '$.cases[3]')[0]
        '$.cases[3].status must be runtime_failed for Java case division_by_zero_exception'
        >>> rust = _native_case_base(_rust_smoke_cases()[0], 'debug', 'native_rust')
        >>> rust['status'] = 'passed'
        >>> _validate_native_status_expectation(rust, 'rust', '$.cases[0]')[0]
        '$.cases[0].status must be runtime_failed for Rust case debug:plain_i32_add_overflow'
    """
    semantic_id = case.get("semantic_case_id")
    profile = str(case.get("profile"))
    if language == "java":
        if semantic_id == "math_sign_missing":
            expected_status = "compile_failed"
        elif semantic_id in _JAVA_NON_PASSING_CASE_IDS:
            expected_status = "runtime_failed"
        else:
            expected_status = "passed"
    elif language == "rust":
        if semantic_id in _RUST_ALWAYS_COMPILE_FAILED_CASE_IDS:
            expected_status = "compile_failed"
        elif semantic_id in _RUST_ALWAYS_RUNTIME_FAILED_CASE_IDS:
            expected_status = "runtime_failed"
        elif semantic_id in _RUST_PROFILE_SENSITIVE_TRAP_CASE_IDS:
            if profile in _RUST_OVERFLOW_CHECKED_PROFILES:
                expected_status = "runtime_failed"
            elif profile in _RUST_OVERFLOW_UNCHECKED_PROFILES:
                expected_status = "passed"
            else:
                return [
                    "%s.profile is not a known Rust profile for case %s: %r"
                    % (case_path, semantic_id, case.get("profile"))
                ]
        elif semantic_id in _RUST_ALWAYS_PASSING_CASE_IDS:
            expected_status = "passed"
        else:
            return [
                "%s.semantic_case_id has no Rust status expectation: %r"
                % (case_path, semantic_id)
            ]
    else:
        return []
    if case.get("status") != expected_status:
        language_name = "Java" if language == "java" else "Rust"
        expected_case = (
            "%s:%s" % (profile, semantic_id) if language == "rust" else semantic_id
        )
        return [
            "%s.status must be %s for %s case %s"
            % (case_path, expected_status, language_name, expected_case)
        ]
    return []


def _command_result_succeeded(command: Any) -> bool:
    """
    Return whether a captured command result represents a clean success.

    :param command: Command result payload.
    :type command: Any
    :return: Whether the command exited with code ``0`` without timing out or
        failing to start.
    :rtype: bool

    Example::

        >>> _command_result_succeeded({'returncode': 0, 'timed_out': False, 'start_error': None})
        True
        >>> _command_result_succeeded({'returncode': None, 'timed_out': True, 'start_error': None})
        False
    """
    return (
        isinstance(command, Mapping)
        and command.get("returncode") == 0
        and command.get("timed_out") is False
        and command.get("start_error") is None
    )


def _command_result_failed(command: Any) -> bool:
    """
    Return whether a captured command result represents a failure.

    :param command: Command result payload.
    :type command: Any
    :return: Whether the command timed out, failed to start, or exited with a
        non-zero code.
    :rtype: bool

    Example::

        >>> _command_result_failed({'returncode': 1, 'timed_out': False, 'start_error': None})
        True
        >>> _command_result_failed({'returncode': 0, 'timed_out': False, 'start_error': None})
        False
    """
    if not isinstance(command, Mapping):
        return False
    return (
        command.get("timed_out") is True
        or isinstance(command.get("start_error"), str)
        or (
            isinstance(command.get("returncode"), int)
            and command.get("returncode") != 0
        )
    )


def _validate_rust_available_commands(
    case: Mapping[str, Any], case_path: str
) -> List[str]:
    """
    Validate command evidence for a Rust case when ``rustc`` is available.

    :param case: Rust smoke case result.
    :type case: Mapping[str, Any]
    :param case_path: Human-readable path.
    :type case_path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> case = _native_case_base(_rust_smoke_cases()[1], 'debug', 'native_rust')
        >>> case['status'] = 'passed'
        >>> case['commands'] = {'run': {'returncode': 0, 'timed_out': False, 'start_error': None}}
        >>> _validate_rust_available_commands(case, '$.cases[1]')[0]
        '$.cases[1].commands.compile is required when rustc is available'
    """
    commands = case.get("commands")
    if not isinstance(commands, Mapping):
        return []
    errors: List[str] = []
    status = case.get("status")
    compile_result = commands.get("compile")
    run_result = commands.get("run")
    if "compile" not in commands:
        errors.append(
            "%s.commands.compile is required when rustc is available" % case_path
        )
    elif status in {"passed", "runtime_failed"} and not _command_result_succeeded(
        compile_result
    ):
        errors.append(
            "%s.commands.compile must succeed for Rust status %s" % (case_path, status)
        )
    elif status == "compile_failed" and not _command_result_failed(compile_result):
        errors.append(
            "%s.commands.compile must fail for Rust compile_failed status" % case_path
        )
    if status in {"passed", "runtime_failed"}:
        if "run" not in commands:
            errors.append(
                "%s.commands.run is required for Rust status %s" % (case_path, status)
            )
        elif status == "passed" and not _command_result_succeeded(run_result):
            errors.append(
                "%s.commands.run must succeed for Rust passed status" % case_path
            )
        elif status == "runtime_failed" and not _command_result_failed(run_result):
            errors.append(
                "%s.commands.run must fail for Rust runtime_failed status" % case_path
            )
    elif status == "compile_failed" and "run" in commands:
        errors.append(
            "%s.commands.run must be absent for Rust compile_failed status" % case_path
        )
    return errors


def _validate_java_available_commands(
    case: Mapping[str, Any], case_path: str
) -> List[str]:
    """
    Validate command evidence for a Java case when ``java`` is available.

    Java smoke cases may use either ``javac`` plus a class-file run or the Java
    source-file launcher. In the launcher path, a source compilation failure is
    observed as a failed ``run`` command.

    :param case: Java smoke case result.
    :type case: Mapping[str, Any]
    :param case_path: Human-readable path.
    :type case_path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> case = _native_case_base(_java_smoke_cases()[0], 'java-int32', 'native_java')
        >>> case['status'] = 'passed'
        >>> case['commands'] = {'run': {'returncode': 1, 'timed_out': False, 'start_error': None}}
        >>> _validate_java_available_commands(case, '$.cases[0]')[0]
        '$.cases[0].commands.run must succeed for Java passed status'
    """
    commands = case.get("commands")
    if not isinstance(commands, Mapping):
        return []
    errors: List[str] = []
    status = case.get("status")
    compile_result = commands.get("compile")
    run_result = commands.get("run")
    if "compile" in commands and status in {"passed", "runtime_failed"}:
        if not _command_result_succeeded(compile_result):
            errors.append(
                "%s.commands.compile must succeed for Java status %s"
                % (case_path, status)
            )
    if status == "passed":
        if "run" not in commands:
            errors.append(
                "%s.commands.run is required for Java passed status" % case_path
            )
        elif not _command_result_succeeded(run_result):
            errors.append(
                "%s.commands.run must succeed for Java passed status" % case_path
            )
    elif status == "runtime_failed":
        if "run" not in commands:
            errors.append(
                "%s.commands.run is required for Java runtime_failed status" % case_path
            )
        elif not _command_result_failed(run_result):
            errors.append(
                "%s.commands.run must fail for Java runtime_failed status" % case_path
            )
    elif status == "compile_failed":
        compile_failed = "compile" in commands and _command_result_failed(
            compile_result
        )
        source_launcher_failed = "compile" not in commands and _command_result_failed(
            run_result
        )
        if not (compile_failed or source_launcher_failed):
            errors.append(
                "%s.compile_failed status requires a failed Java compile or source-launch command"
                % case_path
            )
    return errors


def _native_tool_available(payload: Mapping[str, Any], language: str) -> Optional[bool]:
    """
    Return native tool availability recorded in a smoke payload.

    :param payload: Java or Rust smoke payload.
    :type payload: Mapping[str, Any]
    :param language: Native language, either ``"java"`` or ``"rust"``.
    :type language: str
    :return: Recorded availability, or ``None`` when metadata is incomplete.
    :rtype: Optional[bool]

    Example::

        >>> _native_tool_available({'toolchain': {'rust': {'rustc': {'available': False}}}}, 'rust')
        False
    """
    executable_name = {"java": "java", "rust": "rustc"}.get(language)
    if executable_name is None:
        return None
    toolchain = payload.get("toolchain")
    if not isinstance(toolchain, Mapping):
        return None
    language_tools = toolchain.get(language)
    if not isinstance(language_tools, Mapping):
        return None
    executable = language_tools.get(executable_name)
    if not isinstance(executable, Mapping):
        return None
    available = executable.get("available")
    if isinstance(available, bool):
        return available
    return None


def _validate_native_toolchain_availability(
    payload: Mapping[str, Any], language: str, path: str
) -> List[str]:
    """
    Validate that native executable availability metadata is explicit.

    The Java/Rust smoke validators use the recorded executable availability to
    decide whether available-case or unavailable-case status invariants must be
    enforced. Missing metadata must therefore be reported as invalid instead of
    silently disabling both validation paths.

    :param payload: Java or Rust smoke payload.
    :type payload: Mapping[str, Any]
    :param language: Native language, either ``"java"`` or ``"rust"``.
    :type language: str
    :param path: Human-readable path to the ``toolchain`` object.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_native_toolchain_availability({'toolchain': {}}, 'java', '$.toolchain')
        ['$.toolchain.java must be a mapping']
        >>> payload = {'toolchain': {'rust': {'rustc': {'available': False}}}}
        >>> _validate_native_toolchain_availability(payload, 'rust', '$.toolchain')
        []
        >>> payload = {'toolchain': {'rust': {'rustc': {'available': 'yes'}}}}
        >>> _validate_native_toolchain_availability(payload, 'rust', '$.toolchain')
        ['$.toolchain.rust.rustc.available must be a boolean']
    """
    executable_name = {"java": "java", "rust": "rustc"}.get(language)
    if executable_name is None:
        return []
    toolchain = payload.get("toolchain")
    if not isinstance(toolchain, Mapping):
        return []
    language_tools = toolchain.get(language)
    if not isinstance(language_tools, Mapping):
        return ["%s.%s must be a mapping" % (path, language)]
    executable = language_tools.get(executable_name)
    if not isinstance(executable, Mapping):
        return ["%s.%s.%s must be a mapping" % (path, language, executable_name)]
    available = executable.get("available")
    if not isinstance(available, bool):
        return [
            "%s.%s.%s.available must be a boolean" % (path, language, executable_name)
        ]
    return []


def _validate_unavailable_native_cases(
    payload: Mapping[str, Any], cases: Any, language: str, path: str
) -> List[str]:
    """
    Validate case statuses when the native executable is unavailable.

    :param payload: Java or Rust smoke payload.
    :type payload: Mapping[str, Any]
    :param cases: Case list from the payload.
    :type cases: Any
    :param language: Native language, either ``"java"`` or ``"rust"``.
    :type language: str
    :param path: Human-readable path.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> payload = {'toolchain': {'rust': {'rustc': {'available': False}}}}
        >>> cases = [_native_case_base(_rust_smoke_cases()[0], 'debug', 'native_rust')]
        >>> cases[0]['status'] = 'passed'
        >>> _validate_unavailable_native_cases(payload, cases, 'rust', '$.cases')[0]
        '$.cases[0].status must be unavailable when rustc is unavailable'
    """
    if _native_tool_available(payload, language) is not False or not isinstance(
        cases, list
    ):
        return []
    executable_name = {"java": "java", "rust": "rustc"}[language]
    expected_reason = "%s_unavailable" % executable_name
    errors = []
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            continue
        case_path = "%s[%d]" % (path, index)
        if case.get("status") != "unavailable":
            errors.append(
                "%s.status must be unavailable when %s is unavailable"
                % (case_path, executable_name)
            )
        if case.get("outcome") != "unavailable":
            errors.append(
                "%s.outcome must be unavailable when %s is unavailable"
                % (case_path, executable_name)
            )
        if case.get("reason") != expected_reason:
            errors.append(
                "%s.reason must be %s when %s is unavailable"
                % (case_path, expected_reason, executable_name)
            )
        commands = case.get("commands")
        if isinstance(commands, Mapping) and commands:
            errors.append(
                "%s.commands must be empty when %s is unavailable"
                % (case_path, executable_name)
            )
    return errors


def _validate_available_native_cases(
    payload: Mapping[str, Any], cases: Any, language: str, path: str
) -> List[str]:
    """
    Validate deterministic case statuses when a native executable is available.

    :param payload: Java or Rust smoke payload.
    :type payload: Mapping[str, Any]
    :param cases: Case list from the payload.
    :type cases: Any
    :param language: Native language, either ``"java"`` or ``"rust"``.
    :type language: str
    :param path: Human-readable path.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> payload = {'toolchain': {'java': {'java': {'available': True}}}}
        >>> cases = [_native_case_base(_java_smoke_cases()[3], 'java-int32', 'native_java')]
        >>> cases[0]['status'] = 'passed'
        >>> _validate_available_native_cases(payload, cases, 'java', '$.cases')[0]
        '$.cases[0].status must be runtime_failed for Java case division_by_zero_exception'
    """
    if _native_tool_available(payload, language) is not True or not isinstance(
        cases, list
    ):
        return []
    errors = []
    for index, case in enumerate(cases):
        if isinstance(case, Mapping):
            errors.extend(
                _validate_native_status_expectation(
                    case, language, "%s[%d]" % (path, index)
                )
            )
            if language == "java":
                errors.extend(
                    _validate_java_available_commands(case, "%s[%d]" % (path, index))
                )
            elif language == "rust":
                errors.extend(
                    _validate_rust_available_commands(case, "%s[%d]" % (path, index))
                )
    return errors


def validate_java_rust_smoke(
    payload: Mapping[str, Any], expected_mode: Optional[str] = None
) -> List[str]:
    """
    Validate Java/Rust smoke payload invariants without repository tests.

    :param payload: Java, Rust or aggregate Java/Rust smoke payload.
    :type payload: Mapping[str, Any]
    :param expected_mode: Optional expected mode.
    :type expected_mode: Optional[str], optional
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> validate_java_rust_smoke({'schema_version': 1}, expected_mode='java-smoke')[:2]
        ['mode must be java-smoke', "mode must be one of ['java-rust-smoke', 'java-smoke', 'rust-smoke']"]
        >>> 'summary_status must be a non-empty string' in validate_java_rust_smoke({'schema_version': 1}, expected_mode='java-smoke')
        True
        >>> payload = _build_java_smoke_report(timeout=1)
        >>> payload['summary_status'] = 'passed'
        >>> any('summary_status must match cases' in error for error in validate_java_rust_smoke(payload, expected_mode='java-smoke'))
        True
        >>> payload = build_java_rust_smoke_report('java-rust-smoke', timeout=1)
        >>> payload['cases'] = list(payload['languages']['java']['cases'])
        >>> 'cases must equal languages.java.cases + languages.rust.cases' in validate_java_rust_smoke(payload, expected_mode='java-rust-smoke')
        True
        >>> payload = build_java_rust_smoke_report('java-rust-smoke', timeout=1)
        >>> payload['toolchain'] = {}
        >>> '$.toolchain.java must be a mapping' in validate_java_rust_smoke(payload, expected_mode='java-rust-smoke')
        True
    """
    errors: List[str] = []
    mode = payload.get("mode")
    summary_status = payload.get("summary_status")
    if expected_mode is not None and mode != expected_mode:
        errors.append("mode must be %s" % expected_mode)
    if mode not in _JAVA_RUST_MODES:
        errors.append("mode must be one of %s" % sorted(_JAVA_RUST_MODES))
    expected_language = {
        "java-smoke": "java",
        "rust-smoke": "rust",
        "java-rust-smoke": "java-rust",
    }.get(str(expected_mode or mode))
    if expected_language and payload.get("language") != expected_language:
        errors.append("language must be %s" % expected_language)
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not isinstance(summary_status, str) or not summary_status:
        errors.append("summary_status must be a non-empty string")
    elif summary_status not in _NATIVE_SUMMARY_STATUSES:
        errors.append("summary_status is invalid: %r" % summary_status)
    for key in ["source_mapping_sha256", "render_mapping_sha256"]:
        value = payload.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            errors.append("%s must be a lowercase 64-character sha256 hex string" % key)
    if payload.get("source_mapping_sha256") != payload.get("render_mapping_sha256"):
        errors.append("source_mapping_sha256 and render_mapping_sha256 must match")
    for key in ["generator", "repository", "toolchain"]:
        if not isinstance(payload.get(key), Mapping):
            errors.append("%s must be a mapping" % key)
    if mode == "java-smoke":
        cases = payload.get("cases")
        errors.extend(
            _validate_native_toolchain_availability(payload, "java", "$.toolchain")
        )
        errors.extend(_validate_native_cases(cases, "java", "$.cases"))
        errors.extend(
            _validate_unavailable_native_cases(payload, cases, "java", "$.cases")
        )
        errors.extend(
            _validate_available_native_cases(payload, cases, "java", "$.cases")
        )
        if isinstance(cases, list) and isinstance(summary_status, str):
            expected_summary = _summary_status(cases)
            if summary_status != expected_summary:
                errors.append(
                    "summary_status must match cases: expected %s, got %s"
                    % (expected_summary, summary_status)
                )
    elif mode == "rust-smoke":
        cases = payload.get("cases")
        errors.extend(
            _validate_native_toolchain_availability(payload, "rust", "$.toolchain")
        )
        errors.extend(
            _validate_native_cases(cases, "rust", "$.cases", require_all_profiles=True)
        )
        errors.extend(
            _validate_unavailable_native_cases(payload, cases, "rust", "$.cases")
        )
        errors.extend(
            _validate_available_native_cases(payload, cases, "rust", "$.cases")
        )
        if isinstance(cases, list) and isinstance(summary_status, str):
            expected_summary = _summary_status(cases)
            if summary_status != expected_summary:
                errors.append(
                    "summary_status must match cases: expected %s, got %s"
                    % (expected_summary, summary_status)
                )
    elif mode == "java-rust-smoke":
        languages = payload.get("languages")
        all_cases = payload.get("cases")
        errors.extend(
            _validate_native_toolchain_availability(payload, "java", "$.toolchain")
        )
        errors.extend(
            _validate_native_toolchain_availability(payload, "rust", "$.toolchain")
        )
        top_java_available = _native_tool_available(payload, "java")
        top_rust_available = _native_tool_available(payload, "rust")
        if not isinstance(languages, Mapping):
            errors.append("languages must be a mapping")
        else:
            java_payload = languages.get("java")
            rust_payload = languages.get("rust")
            if not isinstance(java_payload, Mapping):
                errors.append("languages.java must be a mapping")
            else:
                errors.extend(
                    "languages.java: %s" % error
                    for error in validate_java_rust_smoke(
                        java_payload, expected_mode="java-smoke"
                    )
                )
                nested_java_available = _native_tool_available(java_payload, "java")
                if top_java_available is not None and nested_java_available is not None:
                    if top_java_available != nested_java_available:
                        errors.append(
                            "toolchain.java.java.available must match "
                            "languages.java.toolchain.java.java.available"
                        )
            if not isinstance(rust_payload, Mapping):
                errors.append("languages.rust must be a mapping")
            else:
                errors.extend(
                    "languages.rust: %s" % error
                    for error in validate_java_rust_smoke(
                        rust_payload, expected_mode="rust-smoke"
                    )
                )
                nested_rust_available = _native_tool_available(rust_payload, "rust")
                if top_rust_available is not None and nested_rust_available is not None:
                    if top_rust_available != nested_rust_available:
                        errors.append(
                            "toolchain.rust.rustc.available must match "
                            "languages.rust.toolchain.rust.rustc.available"
                        )
            if isinstance(java_payload, Mapping) and isinstance(rust_payload, Mapping):
                expected_cases = list(java_payload.get("cases", [])) + list(
                    rust_payload.get("cases", [])
                )
                if all_cases != expected_cases:
                    errors.append(
                        "cases must equal languages.java.cases + languages.rust.cases"
                    )
        java_cases = (
            [
                case
                for case in all_cases
                if isinstance(case, Mapping) and case.get("language") == "java"
            ]
            if isinstance(all_cases, list)
            else []
        )
        rust_cases = (
            [
                case
                for case in all_cases
                if isinstance(case, Mapping) and case.get("language") == "rust"
            ]
            if isinstance(all_cases, list)
            else []
        )
        errors.extend(_validate_native_cases(java_cases, "java", "$.cases.java"))
        errors.extend(
            _validate_native_cases(
                rust_cases, "rust", "$.cases.rust", require_all_profiles=True
            )
        )
        errors.extend(
            _validate_unavailable_native_cases(
                payload, java_cases, "java", "$.cases.java"
            )
        )
        errors.extend(
            _validate_available_native_cases(
                payload, java_cases, "java", "$.cases.java"
            )
        )
        errors.extend(
            _validate_unavailable_native_cases(
                payload, rust_cases, "rust", "$.cases.rust"
            )
        )
        errors.extend(
            _validate_available_native_cases(
                payload, rust_cases, "rust", "$.cases.rust"
            )
        )
        if isinstance(all_cases, list) and isinstance(summary_status, str):
            expected_summary = _summary_status(all_cases)
            if summary_status != expected_summary:
                errors.append(
                    "summary_status must match cases: expected %s, got %s"
                    % (expected_summary, summary_status)
                )
    notes = payload.get("official_source_notes")
    if mode in {"java-smoke", "rust-smoke"} and (
        not isinstance(notes, list) or not notes
    ):
        errors.append("official_source_notes must be a non-empty list")
    if mode == "java-rust-smoke":
        if not isinstance(notes, Mapping):
            errors.append("official_source_notes must be a mapping")
        else:
            for language in ["java", "rust"]:
                value = notes.get(language)
                if not isinstance(value, list) or not value:
                    errors.append(
                        "official_source_notes.%s must be a non-empty list" % language
                    )
    return errors


def _summary_status(cases: Sequence[Mapping[str, Any]]) -> str:
    """
    Compute an aggregate status for a probe summary.

    :param cases: Case result mappings.
    :type cases: Sequence[Mapping[str, Any]]
    :return: Aggregate status string.
    :rtype: str

    Example::

        >>> _summary_status([{'status': 'passed'}])
        'passed'
    """
    statuses = {case.get("status") for case in cases}
    if not cases:
        return "skipped"
    if statuses <= {"unavailable"}:
        return "unavailable"
    if statuses <= {"passed"}:
        return "passed"
    if statuses & {
        "compile_failed",
        "link_failed",
        "runtime_failed",
        "sanitizer_failed",
    }:
        return "completed_with_findings"
    return "completed"


def build_c_family_smoke_report(
    mode: str,
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
    work_dir: Optional[Union[str, Path]] = None,
    timeout: int = 10,
) -> _JSON_OBJECT:
    """
    Build and run a C-family smoke probe report.

    :param mode: Smoke mode, either ``"c-smoke"`` or ``"cpp-smoke"``.
    :type mode: str
    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping path, defaults to the committed R0
        snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :param work_dir: Optional directory for temporary compile artifacts.
    :type work_dir: Optional[Union[str, pathlib.Path]], optional
    :param timeout: Per-command timeout in seconds, defaults to ``10``.
    :type timeout: int, optional
    :return: JSON-compatible smoke summary.
    :rtype: Dict[str, Any]

    Example::

        >>> report = build_c_family_smoke_report('c-smoke', timeout=1)
        >>> report['schema_version']
        1
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    source_mapping_sha256 = mapping.get("mapping_sha256")
    if not isinstance(source_mapping_sha256, str):
        source_mapping_sha256 = ""
    try:
        render_paths = _render_paths_for_mode(mode, mapping)
    except ValueError as err:
        # ValueError: _render_paths_for_mode validates the required R0 mapping
        # paths (for example cxx_paths and template expression styles). Invalid
        # mapping input is a structured probe outcome, not an uncaught CLI crash.
        cases = [
            {
                "case_id": "invalid_mapping:%s" % case.case_id,
                "operator": case.operator,
                "fcstm_expression": case.fcstm_expression,
                "render_expression": "",
                "render_path": "invalid_mapping",
                "compile_language": "c" if mode == "c-smoke" else "cpp",
                "mapping_sources": [],
                "status": "skipped",
                "reason": str(err),
                "commands": {},
                "sanitizer": {"available": False, "status": "mapping_invalid"},
            }
            for case in _risk_cases()
        ]
        summary = {
            "schema_version": 1,
            "mode": mode,
            "source_mapping_path": str(mapping_file),
            "source_mapping_sha256": source_mapping_sha256,
            "language": "c" if mode == "c-smoke" else "cpp",
            "summary_status": "invalid",
            "mapping_errors": [str(err)],
            "toolchain": {
                "compilers": {},
                "sanitizers": {},
                "timeout_seconds": timeout,
                "work_dir": "",
            },
            "render_paths": [],
            "cases": cases,
        }
        errors = validate_probe_summary(summary)
        if errors:
            summary["validation_errors"] = errors
        return summary
    compile_languages = sorted({path.compile_language for path in render_paths})
    compilers = {language: _find_compiler(language) for language in compile_languages}

    if work_dir is None:
        temp_parent = root / _RESEARCH_PATH / "results" / "local"
        temp_parent.mkdir(parents=True, exist_ok=True)
        temp_context = tempfile.TemporaryDirectory(
            prefix=mode + "-", dir=str(temp_parent)
        )
        cleanup = temp_context.cleanup
        active_work_dir = Path(temp_context.name)
    else:
        active_work_dir = Path(work_dir).resolve()
        active_work_dir.mkdir(parents=True, exist_ok=True)
        cleanup = None

    try:
        sanitizers = {}
        for language, compiler in compilers.items():
            if compiler.get("available"):
                sanitizer_dir = active_work_dir / ("sanitizer-%s" % language)
                sanitizer_dir.mkdir(parents=True, exist_ok=True)
                sanitizers[language] = _check_sanitizer_available(
                    compiler, language, sanitizer_dir, timeout
                )
            else:
                sanitizers[language] = {
                    "available": False,
                    "status": "compiler_unavailable",
                    "flags": _sanitizer_flags(language),
                    "commands": {},
                }

        cases = []
        for render_path in render_paths:
            compiler = compilers[render_path.compile_language]
            sanitizer = sanitizers[render_path.compile_language]
            for case in _risk_cases():
                cases.append(
                    _run_one_case(
                        case,
                        render_path,
                        compiler,
                        sanitizer,
                        active_work_dir,
                        timeout,
                    )
                )

        summary = {
            "schema_version": 1,
            "mode": mode,
            "source_mapping_path": str(mapping_file),
            "source_mapping_sha256": source_mapping_sha256,
            "language": "c" if mode == "c-smoke" else "cpp",
            "summary_status": _summary_status(cases),
            "toolchain": {
                "compilers": compilers,
                "sanitizers": sanitizers,
                "timeout_seconds": timeout,
                "work_dir": str(active_work_dir),
            },
            "render_paths": [
                {
                    "path_id": path.path_id,
                    "language": path.language,
                    "compile_language": path.compile_language,
                    "lang_style": path.lang_style,
                    "expression_core_language": path.expression_core_language,
                    "mapping_sources": list(path.mapping_sources),
                    "template_name": path.template_name,
                    "wrapper_language": path.wrapper_language,
                }
                for path in render_paths
            ],
            "cases": cases,
        }
        errors = validate_probe_summary(summary)
        if errors:
            summary["summary_status"] = "invalid"
            summary["validation_errors"] = errors
        return summary
    finally:
        if cleanup is not None:
            cleanup()


def _git_output(repo_root: Union[str, Path], args: Sequence[str]) -> Optional[str]:
    """
    Run a short git metadata command and return stripped output.

    :param repo_root: Repository root path.
    :type repo_root: Union[str, pathlib.Path]
    :param args: Git arguments excluding the executable name.
    :type args: Sequence[str]
    :return: Command output or ``None`` when git metadata is unavailable.
    :rtype: Optional[str]

    Example::

        >>> value = _git_output('.', ['rev-parse', '--is-inside-work-tree'])
        >>> value in {'true', None}
        True
    """
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(Path(repo_root).resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=5,
            check=False,
        )
    except OSError:
        # OSError: git is missing or cannot be launched in this environment.
        return None
    except subprocess.TimeoutExpired:
        # TimeoutExpired: repository metadata must not hang research probes.
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_commit(repo_root: Union[str, Path]) -> Optional[str]:
    """
    Return the current repository commit when git metadata is available.

    :param repo_root: Repository root path.
    :type repo_root: Union[str, pathlib.Path]
    :return: Full commit SHA or ``None``.
    :rtype: Optional[str]

    Example::

        >>> commit = _git_commit('.')
        >>> commit is None or len(commit) == 40
        True
    """
    return _git_output(repo_root, ["rev-parse", "HEAD"])


def _python_sign(value: Union[int, float]) -> int:
    """
    Return the Python-rendered FCSTM sign value for one number.

    :param value: Numeric value.
    :type value: Union[int, float]
    :return: ``-1``, ``0`` or ``1``.
    :rtype: int

    Example::

        >>> _python_sign(-2)
        -1
        >>> _python_sign(0.0)
        0
    """
    return int((value > 0) - (value < 0))


def _python_cbrt(value: Union[int, float]) -> float:
    """
    Return the Python renderer's cube-root workaround result.

    :param value: Numeric value.
    :type value: Union[int, float]
    :return: Cube-root approximation preserving the input sign.
    :rtype: float

    Example::

        >>> round(_python_cbrt(-8), 12)
        -2.0
    """
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def _round_to_z3_value(value: str) -> str:
    """
    Evaluate :func:`python_round_to_z3` for one rational input string.

    :param value: Z3 real literal text.
    :type value: str
    :return: Simplified Z3 expression text.
    :rtype: str

    Example::

        >>> _round_to_z3_value('2.5')
        '2'
    """
    expr = python_round_to_z3(z3.RealVal(value))
    return str(z3.simplify(expr))


def _render_python_expr(expr_text: str) -> _JSON_OBJECT:
    """
    Render a numeric expression through the built-in Python style.

    :param expr_text: FCSTM numeric expression text.
    :type expr_text: str
    :return: Render result with parse/render status.
    :rtype: Dict[str, Any]

    Example::

        >>> result = _render_python_expr('sign(A)')
        >>> result['status']
        'rendered'
    """
    try:
        expr = parse_expr_from_string(expr_text, mode="numeric")
        rendered = render_expr_node(expr.to_ast_node(), lang_style="python")
    except (ValueError, TypeError) as err:
        # ValueError/TypeError: model conversion or rendering rejected the
        # expression after parsing; record the failed case for the baseline.
        return {
            "expr": expr_text,
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except GrammarParseError as err:
        # GrammarParseError: parse_expr_from_string rejects expressions that are
        # outside the current numeric grammar, such as unary ``~`` today.
        return {
            "expr": expr_text,
            "status": "parse_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    return {
        "expr": expr_text,
        "status": "rendered",
        "rendered": rendered,
        "ast_type": type(expr.to_ast_node()).__name__,
    }


def _render_template_python_expr(
    renderer: StateMachineCodeRenderer, expr_text: str, style: str
) -> _JSON_OBJECT:
    """
    Render a numeric expression through the packaged Python template renderer.

    :param renderer: Prepared Python template renderer.
    :type renderer: pyfcstm.render.render.StateMachineCodeRenderer
    :param expr_text: FCSTM numeric expression text.
    :type expr_text: str
    :param style: Template expression style name, such as ``'python_expr'``.
    :type style: str
    :return: Render result with style, parse status, and rendered text.
    :rtype: Dict[str, Any]

    Example::

        >>> renderer = StateMachineCodeRenderer('templates/python')
        >>> row = _render_template_python_expr(renderer, 'sign(A)', 'python_scope_expr')
        >>> row['rendered']
        'self._sign(scope["A"])'
    """
    try:
        expr = parse_expr_from_string(expr_text, mode="numeric")
        rendered = renderer.env.globals["expr_render"](expr.to_ast_node(), style=style)
    except GrammarParseError as err:
        # GrammarParseError: parse_expr_from_string rejects expressions outside
        # the current numeric grammar; preserve the failed probe row.
        return {
            "style": style,
            "expr": expr_text,
            "status": "parse_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except (KeyError, ValueError, TypeError) as err:
        # KeyError: the requested renderer style is absent; ValueError/TypeError:
        # model conversion or renderer templates rejected the parsed expression.
        return {
            "style": style,
            "expr": expr_text,
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    return {
        "style": style,
        "expr": expr_text,
        "status": "rendered",
        "rendered": rendered,
        "ast_type": type(expr.to_ast_node()).__name__,
    }


def _render_template_python_assignment(
    renderer: StateMachineCodeRenderer, expr_text: str, style: str = "python_runtime"
) -> _JSON_OBJECT:
    """
    Render a representative assignment through a Python template statement style.

    :param renderer: Prepared Python template renderer.
    :type renderer: pyfcstm.render.render.StateMachineCodeRenderer
    :param expr_text: FCSTM numeric expression assigned to state variable ``A``.
    :type expr_text: str
    :param style: Statement style name, defaults to ``'python_runtime'``.
    :type style: str, optional
    :return: Render result with statement style and rendered text.
    :rtype: Dict[str, Any]

    Example::

        >>> renderer = StateMachineCodeRenderer('templates/python')
        >>> row = _render_template_python_assignment(renderer, 'sign(A)')
        >>> '_s(_v["A"])' in row['rendered']
        True
    """
    try:
        expr = parse_expr_from_string(expr_text, mode="numeric")
        stmt = dsl_nodes.OperationAssignment("A", expr.to_ast_node())
        rendered = renderer.env.globals["stmt_render"](
            stmt,
            style=style,
            state_vars={"A"},
            var_types={"A": "int"},
        )
    except GrammarParseError as err:
        # GrammarParseError: the representative expression is not accepted by
        # the numeric grammar and therefore cannot form an assignment probe.
        return {
            "style": style,
            "sample": "assign_state_var",
            "expr": expr_text,
            "status": "parse_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except (KeyError, ValueError, TypeError) as err:
        # KeyError: the requested statement style is absent; ValueError/TypeError:
        # model conversion or statement rendering rejected the sample.
        return {
            "style": style,
            "sample": "assign_state_var",
            "expr": expr_text,
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    return {
        "style": style,
        "sample": "assign_state_var",
        "target": "A",
        "expr": expr_text,
        "status": "rendered",
        "rendered": rendered,
    }


def _render_template_python_if(
    renderer: StateMachineCodeRenderer,
    condition_text: str,
    body_expr_text: str,
    style: str = "python_runtime",
) -> _JSON_OBJECT:
    """
    Render a representative ``if`` block through a Python statement style.

    :param renderer: Prepared Python template renderer.
    :type renderer: pyfcstm.render.render.StateMachineCodeRenderer
    :param condition_text: FCSTM logical expression for the branch condition.
    :type condition_text: str
    :param body_expr_text: FCSTM numeric expression assigned inside the branch.
    :type body_expr_text: str
    :param style: Statement style name, defaults to ``'python_runtime'``.
    :type style: str, optional
    :return: Render result for the representative branch sample.
    :rtype: Dict[str, Any]

    Example::

        >>> renderer = StateMachineCodeRenderer('templates/python')
        >>> row = _render_template_python_if(renderer, 'sign(A) > 0', 'sign(A)')
        >>> 'if self._evaluate_runtime_expr' in row['rendered']
        True
    """
    try:
        condition = parse_expr_from_string(condition_text, mode="logical")
        body_expr = parse_expr_from_string(body_expr_text, mode="numeric")
        stmt = dsl_nodes.OperationIf(
            [
                dsl_nodes.OperationIfBranch(
                    condition.to_ast_node(),
                    [
                        dsl_nodes.OperationAssignment(
                            "A",
                            body_expr.to_ast_node(),
                        )
                    ],
                )
            ]
        )
        rendered = renderer.env.globals["stmt_render"](
            stmt,
            style=style,
            state_vars={"A"},
            var_types={"A": "int"},
        )
    except GrammarParseError as err:
        # GrammarParseError: either the logical condition or numeric body
        # expression is outside the accepted grammar.
        return {
            "style": style,
            "sample": "if_assign_state_var",
            "condition": condition_text,
            "expr": body_expr_text,
            "status": "parse_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except (KeyError, ValueError, TypeError) as err:
        # KeyError: the requested statement style is absent; ValueError/TypeError:
        # model conversion or statement rendering rejected the if sample.
        return {
            "style": style,
            "sample": "if_assign_state_var",
            "condition": condition_text,
            "expr": body_expr_text,
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    return {
        "style": style,
        "sample": "if_assign_state_var",
        "condition": condition_text,
        "expr": body_expr_text,
        "status": "rendered",
        "rendered": rendered,
    }


def _constant_sample(name: str, value: float) -> _JSON_OBJECT:
    """
    Build one Python constant sample row.

    :param name: Constant name.
    :type name: str
    :param value: Constant value.
    :type value: float
    :return: JSON-compatible constant sample.
    :rtype: Dict[str, Any]

    Example::

        >>> _constant_sample('pi', math.pi)['hex'].startswith('0x1.')
        True
    """
    return {
        "name": name,
        "repr": repr(value),
        "hex": value.hex(),
        "render": _render_python_expr(name),
    }


def _build_python_runtime_samples() -> _JSON_OBJECT:
    """
    Build representative Python runtime behavior samples.

    :return: Python render/runtime sample groups.
    :rtype: Dict[str, Any]

    Example::

        >>> samples = _build_python_runtime_samples()
        >>> samples['round_half_cases'][0]['python_round']
        -2
    """
    round_values = ["-2.5", "-1.5", "-0.5", "0.5", "1.5", "2.5", "3.5"]
    cbrt_values = [-27, -8, -1, 0, 1, 8, 27]
    sign_values = [-3, -0.0, 0, 4.5]
    bitwise_values = [-3, -1, 0, 1, 2]
    return {
        "constants": [
            _constant_sample("pi", math.pi),
            _constant_sample("E", math.e),
            _constant_sample("tau", math.tau),
        ],
        "round_half_cases": [
            {
                "input": value,
                "python_round": round(float(value)),
                "z3_python_round_to_z3": _round_to_z3_value(value),
            }
            for value in round_values
        ],
        "sign_cases": [
            {"input": repr(value), "python_sign": _python_sign(value)}
            for value in sign_values
        ],
        "cbrt_cases": [
            {
                "input": value,
                "python_cbrt_workaround_repr": repr(_python_cbrt(value)),
            }
            for value in cbrt_values
        ],
        "division_modulo_cases": [
            {
                "expression": "-3 / 2",
                "python_value_repr": repr(-3 / 2),
                "note": "Python renderer uses true division for '/' expressions.",
            },
            {
                "expression": "-3 % 2",
                "python_value_repr": repr(-3 % 2),
                "note": "Python modulo keeps the divisor sign.",
            },
        ],
        "bitwise_cases": [
            {"expression": "~%s" % value, "python_value": ~value}
            for value in bitwise_values
        ],
        "shift_cases": [
            {"expression": "1 << 3", "python_value": 1 << 3},
            {"expression": "-8 >> 1", "python_value": -8 >> 1},
        ],
    }


def _support(status: str, strategy: str, note: str) -> _JSON_OBJECT:
    """
    Build one Z3 support descriptor.

    :param status: Support level.
    :type status: str
    :param strategy: Encoding strategy summary.
    :type strategy: str
    :param note: Human-readable caveat.
    :type note: str
    :return: Support descriptor.
    :rtype: Dict[str, Any]

    Example::

        >>> _support('exact', 'native', 'ok')['status']
        'exact'
    """
    return {"status": status, "strategy": strategy, "note": note}


def _z3_probe_case(case_id: str, operation: Callable[[], Any]) -> _JSON_OBJECT:
    """
    Execute one tiny Z3 construction probe and record the result.

    The baseline uses these rows as counterexamples for capability claims. The
    probe deliberately constructs expressions only; it does not call a solver
    or depend on model selection.

    :param case_id: Stable case identifier.
    :type case_id: str
    :param operation: Callable that constructs or simplifies a Z3 expression.
    :type operation: Callable[[], Any]
    :return: JSON-compatible probe result.
    :rtype: Dict[str, Any]

    Example::

        >>> row = _z3_probe_case('int-add', lambda: z3.IntVal(1) + z3.IntVal(2))
        >>> row['status']
        'built'
    """
    try:
        value = operation()
    except TypeError as err:
        # TypeError: Python/z3py operator overloading rejects the requested
        # expression shape, for example ``z3.Int("x") & z3.Int("y")``.
        return {
            "case_id": case_id,
            "status": "type_error",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except z3.Z3Exception as err:
        # Z3Exception: z3py accepted the Python call shape but the underlying
        # Z3 API rejected the expression construction or simplification.
        return {
            "case_id": case_id,
            "status": "z3_error",
            "error_type": type(err).__name__,
            "error": str(err),
        }

    sort = value.sort() if hasattr(value, "sort") else None
    return {
        "case_id": case_id,
        "status": "built",
        "z3_expr": str(value),
        "sort": str(sort) if sort is not None else None,
    }


def _build_z3_representative_samples() -> _JSON_OBJECT:
    """
    Build tiny Z3 construction samples for high-risk capability boundaries.

    :return: Z3 construction samples and native function availability.
    :rtype: Dict[str, Any]

    Example::

        >>> samples = _build_z3_representative_samples()
        >>> samples['int_bitwise_operator_results'][0]['status']
        'type_error'
    """
    int_x = z3.Int("x")
    int_y = z3.Int("y")
    return {
        "int_bitwise_operator_results": [
            _z3_probe_case("int-and", lambda: int_x & int_y),
            _z3_probe_case("int-or", lambda: int_x | int_y),
            _z3_probe_case("int-xor", lambda: int_x ^ int_y),
            _z3_probe_case("int-left-shift", lambda: int_x << z3.IntVal(1)),
            _z3_probe_case("int-right-shift", lambda: int_x >> z3.IntVal(1)),
            _z3_probe_case("int-bitwise-not", lambda: ~int_x),
        ],
        "bitvec_bitwise_operator_results": [
            _z3_probe_case(
                "bitvec-and",
                lambda: z3.simplify(z3.BitVecVal(0b1010, 8) & z3.BitVecVal(0b1100, 8)),
            ),
            _z3_probe_case(
                "bitvec-or",
                lambda: z3.simplify(z3.BitVecVal(0b1010, 8) | z3.BitVecVal(0b1100, 8)),
            ),
            _z3_probe_case(
                "bitvec-xor",
                lambda: z3.simplify(z3.BitVecVal(0b1010, 8) ^ z3.BitVecVal(0b1100, 8)),
            ),
            _z3_probe_case(
                "bitvec-left-shift-wrap",
                lambda: z3.simplify(z3.BitVecVal(0b10000000, 8) << z3.BitVecVal(1, 8)),
            ),
            _z3_probe_case(
                "bitvec-right-shift-signed",
                lambda: z3.simplify(z3.BitVecVal(0b11110000, 8) >> z3.BitVecVal(1, 8)),
            ),
            _z3_probe_case(
                "bitvec-bitwise-not",
                lambda: z3.simplify(~z3.BitVecVal(0, 8)),
            ),
        ],
        "native_function_availability": [
            {"function": "Sqrt", "available": hasattr(z3, "Sqrt")},
            {"function": "Sin", "available": hasattr(z3, "Sin")},
            {"function": "Cos", "available": hasattr(z3, "Cos")},
            {"function": "Exp", "available": hasattr(z3, "Exp")},
            {"function": "Log", "available": hasattr(z3, "Log")},
        ],
        "int_division_modulo_python_mismatch_cases": (
            _build_z3_int_division_modulo_mismatch_cases()
        ),
    }


def _z3_support_for_operator(operator: str) -> Mapping[str, _JSON_OBJECT]:
    """
    Return the Z3 support matrix for one FCSTM operator or function.

    :param operator: FCSTM operator or function name.
    :type operator: str
    :return: Mapping from Z3 sort family to support descriptors.
    :rtype: Mapping[str, Dict[str, Any]]

    Example::

        >>> _z3_support_for_operator('+')['Int']['status']
        'exact'
    """
    exact_int_real = {
        "Int": _support(
            "exact", "native arithmetic", "Exact over mathematical integers."
        ),
        "Real": _support(
            "exact", "native arithmetic", "Exact over mathematical reals."
        ),
        "BitVec": _support(
            "exact",
            "native fixed-width bit-vector arithmetic",
            "Exact for a selected bit width; overflow wraps by BitVec semantics.",
        ),
        "FP": _support(
            "approximate",
            "IEEE-754 floating-point theory",
            "Exact for chosen FP sort and rounding mode, not Python int semantics.",
        ),
    }
    if operator in {"+", "-", "*"}:
        return exact_int_real
    if operator == "/":
        return {
            "Int": _support(
                "approximate",
                "integer division with definedness and Python-compatibility obligations",
                "Z3 Int division is integer-valued and totalized at divisor zero; it is not exact for the Python renderer's true-division baseline.",
            ),
            "Real": _support(
                "exact",
                "real division with definedness obligation",
                "Z3 Real division is totalized at zero; probes must record non-zero obligations.",
            ),
            "BitVec": _support(
                "exact",
                "signed/unsigned operator must be chosen explicitly",
                "BitVec division is width-bound and needs a signedness profile.",
            ),
            "FP": _support(
                "approximate",
                "IEEE-754 division",
                "FP division follows selected rounding/NaN/Inf semantics, not Python integers.",
            ),
        }
    if operator == "%":
        return {
            "Int": _support(
                "approximate",
                "integer modulo with divisor-sign and definedness obligations",
                "Z3 Int modulo is totalized at divisor zero and does not match Python modulo when the divisor is negative.",
            ),
            "Real": _support(
                "unsupported",
                "none",
                "Real modulo is not a native Z3 arithmetic operator.",
            ),
            "BitVec": _support(
                "exact",
                "signed/unsigned remainder operator must be chosen explicitly",
                "BitVec remainder is width-bound and needs a signedness profile.",
            ),
            "FP": _support(
                "unsupported",
                "none",
                "FP remainder is outside current solver helper coverage.",
            ),
        }
    if operator == "**":
        return {
            "Int": _support(
                "approximate",
                "native exponent where accepted by z3py",
                "Nonlinear/exponential constraints can be incomplete or slow.",
            ),
            "Real": _support(
                "approximate",
                "native exponent where accepted by z3py",
                "General real exponentiation is not a stable exact solver baseline.",
            ),
            "BitVec": _support(
                "unsupported",
                "none",
                "No generic FCSTM BitVec power profile is defined.",
            ),
            "FP": _support(
                "unsupported",
                "none",
                "No FP power encoding is used by current solver helpers.",
            ),
        }
    if operator in {"&", "|", "^", "<<", ">>", "~"}:
        return {
            "Int": _support(
                "unsupported",
                "no native Int bitwise operator",
                "The representative construction samples record TypeError for Int bitwise construction; use BitVec for fixed-width bitwise profiles.",
            ),
            "Real": _support(
                "unsupported", "none", "Bitwise operators are not defined over Real."
            ),
            "BitVec": _support(
                "exact",
                "native fixed-width bit-vector operator",
                "Requires explicit width and signedness policy for shifts/division-like operations.",
            ),
            "FP": _support(
                "unsupported",
                "none",
                "Bitwise operators are not defined over FP values.",
            ),
        }
    if operator in {"<", "<=", ">", ">=", "==", "!="}:
        return {
            "Int": _support(
                "exact", "native comparison", "Produces a Bool expression."
            ),
            "Real": _support(
                "exact", "native comparison", "Produces a Bool expression."
            ),
            "BitVec": _support(
                "exact",
                "native comparison with signedness choice for ordering",
                "Equality is direct; ordering needs signed/unsigned policy.",
            ),
            "FP": _support(
                "approximate",
                "IEEE-754 comparison",
                "NaN and signed-zero behavior differ from Python numeric baseline.",
            ),
        }
    if operator in {"abs", "sign", "floor", "ceil", "trunc", "round"}:
        return {
            "Int": _support(
                "exact", "piecewise arithmetic helper", "Exact for Int operands."
            ),
            "Real": _support(
                "exact",
                "piecewise arithmetic helper",
                "Exact for Real arithmetic; round follows Python half-even helper.",
            ),
            "BitVec": _support(
                "unsupported",
                "none",
                "Current solver helper does not encode these over BitVec.",
            ),
            "FP": _support(
                "unsupported",
                "none",
                "Current solver helper does not encode these over FP.",
            ),
        }
    if operator == "sqrt":
        return {
            "Int": _support(
                "approximate",
                "convert to Real and use z3.Sqrt",
                "Exact algebraic support depends on downstream solver fragment.",
            ),
            "Real": _support(
                "approximate",
                "z3.Sqrt",
                "Z3 algebraic support exists, but this is not a Python math.sqrt domain check.",
            ),
            "BitVec": _support(
                "unsupported",
                "none",
                "Current solver helper does not encode sqrt over BitVec.",
            ),
            "FP": _support(
                "unsupported",
                "none",
                "Current solver helper does not encode sqrt over FP.",
            ),
        }
    if operator == "cbrt":
        return {
            sort: _support(
                "unsupported",
                "no current encoding; future work may add uninterpreted or polynomial obligations"
                if sort in {"Int", "Real"}
                else "none",
                "Current solver helper raises NotImplementedError for cbrt.",
            )
            for sort in _Z3_SORTS
        }
    if operator in {
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
    }:
        return {
            sort: _support(
                "unsupported",
                "no current encoding; future work may add uninterpreted or approximation obligations"
                if sort in {"Int", "Real"}
                else "none",
                "Current solver helper raises NotImplementedError for this transcendental function.",
            )
            for sort in _Z3_SORTS
        }
    return {
        sort: _support("unsupported", "none", "No baseline entry is defined.")
        for sort in _Z3_SORTS
    }


def _binary_render_template_key(operator: str) -> str:
    """
    Return the specialized binary-renderer template key for one operator.

    :param operator: FCSTM binary operator.
    :type operator: str
    :return: Specialized ``BinaryOp`` mapping key.
    :rtype: str

    Example::

        >>> _binary_render_template_key('/')
        'BinaryOp(/)'
    """
    return "BinaryOp(%s)" % operator


def _ufunc_render_template_key(function_name: str) -> str:
    """
    Return the specialized UFunc renderer template key.

    :param function_name: FCSTM numeric function name.
    :type function_name: str
    :return: Specialized ``UFunc`` mapping key.
    :rtype: str

    Example::

        >>> _ufunc_render_template_key('round')
        'UFunc(round)'
    """
    return "UFunc(%s)" % function_name


def _append_template_render_path(
    paths: List[_JSON_OBJECT],
    source: str,
    mapping_path: str,
    templates: Mapping[str, Any],
    preferred_key: str,
    fallback_key: str,
) -> None:
    """
    Append a renderer mapping descriptor for one preferred/fallback key pair.

    :param paths: Render path descriptors to extend.
    :type paths: List[Dict[str, Any]]
    :param source: Human-readable mapping source.
    :type source: str
    :param mapping_path: JSON path prefix for diagnostics.
    :type mapping_path: str
    :param templates: Template mapping to read.
    :type templates: Mapping[str, Any]
    :param preferred_key: Specialized template key.
    :type preferred_key: str
    :param fallback_key: Generic fallback template key.
    :type fallback_key: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> rows = []
        >>> _append_template_render_path(rows, 'builtin', '$.templates', {'BinaryOp': '{{ op }}'}, 'BinaryOp(/)', 'BinaryOp')
        >>> rows[0]['status']
        'generic_template'
    """
    if preferred_key in templates:
        paths.append(
            {
                "source": source,
                "mapping_path": "%s.%s" % (mapping_path, preferred_key),
                "template_key": preferred_key,
                "status": "specialized_template",
                "template": templates[preferred_key],
            }
        )
        return
    if fallback_key in templates:
        paths.append(
            {
                "source": source,
                "mapping_path": "%s.%s" % (mapping_path, fallback_key),
                "template_key": fallback_key,
                "status": "generic_template",
                "template": templates[fallback_key],
                "note": "No specialized %s entry exists; the generic renderer emits the AST operator token."
                % preferred_key,
            }
        )
        return
    paths.append(
        {
            "source": source,
            "mapping_path": "%s.%s" % (mapping_path, preferred_key),
            "template_key": preferred_key,
            "status": "missing_template",
            "note": "No specialized or generic render template was present in the R0 mapping.",
        }
    )


def _append_override_render_paths(
    paths: List[_JSON_OBJECT],
    source_prefix: str,
    mapping_path: str,
    styles: Mapping[str, Any],
    preferred_key: str,
    fallback_key: str,
    override_field: str,
) -> None:
    """
    Append template override descriptors from configured render styles.

    :param paths: Render path descriptors to extend.
    :type paths: List[Dict[str, Any]]
    :param source_prefix: Source label prefix.
    :type source_prefix: str
    :param mapping_path: JSON path prefix for diagnostics.
    :type mapping_path: str
    :param styles: Style mapping from the R0 render mapping.
    :type styles: Mapping[str, Any]
    :param preferred_key: Specialized template key.
    :type preferred_key: str
    :param fallback_key: Generic fallback template key.
    :type fallback_key: str
    :param override_field: Style field containing expression overrides.
    :type override_field: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> rows = []
        >>> _append_override_render_paths(rows, 'expr', '$.expr', {'py': {'overrides': {'UFunc(sign)': 's(x)'}}}, 'UFunc(sign)', 'UFunc', 'overrides')
        >>> rows[0]['style']
        'py'
    """
    for style_name in sorted(styles):
        style = styles.get(style_name)
        if not isinstance(style, Mapping):
            continue
        overrides = style.get(override_field)
        if not isinstance(overrides, Mapping):
            continue
        selected_key = None
        if preferred_key in overrides:
            selected_key = preferred_key
            status = "specialized_override"
        elif fallback_key in overrides:
            selected_key = fallback_key
            status = "generic_override"
        else:
            continue
        paths.append(
            {
                "source": "%s.%s" % (source_prefix, style_name),
                "style": style_name,
                "mapping_path": "%s.%s.%s.%s"
                % (mapping_path, style_name, override_field, selected_key),
                "template_key": selected_key,
                "status": status,
                "template": overrides[selected_key],
            }
        )


def _render_paths_for_operator(
    mapping: Mapping[str, Any], operator: str, kind: str
) -> List[_JSON_OBJECT]:
    """
    Return R0 render mapping descriptors for one matrix row.

    :param mapping: R0 render mapping.
    :type mapping: Mapping[str, Any]
    :param operator: FCSTM operator or function name.
    :type operator: str
    :param kind: Operator category.
    :type kind: str
    :return: Render path descriptors.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> rows = _render_paths_for_operator({'builtin_expr_styles': {'styles': {'python': {'templates': {'BinaryOp': '{{ op }}'}}}}}, '/', 'binary_arithmetic')
        >>> rows[0]['template_key']
        'BinaryOp'
    """
    if kind == "ufunc":
        preferred_key = _ufunc_render_template_key(operator)
        fallback_key = "UFunc"
    elif operator == "~":
        preferred_key = "UnaryOp(~)"
        fallback_key = "UnaryOp"
    else:
        preferred_key = _binary_render_template_key(operator)
        fallback_key = "BinaryOp"

    paths: List[_JSON_OBJECT] = []
    builtin_templates = (
        mapping.get("builtin_expr_styles", {})
        .get("styles", {})
        .get("python", {})
        .get("templates", {})
    )
    if not isinstance(builtin_templates, Mapping):
        builtin_templates = {}
    _append_template_render_path(
        paths,
        "builtin_expr_styles.python",
        "$.builtin_expr_styles.styles.python.templates",
        builtin_templates,
        preferred_key,
        fallback_key,
    )

    python_template = mapping.get("templates", {}).get("python", {})
    if isinstance(python_template, Mapping):
        expr_styles = python_template.get("expr_styles", {})
        if isinstance(expr_styles, Mapping):
            _append_override_render_paths(
                paths,
                "templates.python.expr_styles",
                "$.templates.python.expr_styles",
                expr_styles,
                preferred_key,
                fallback_key,
                "overrides",
            )
        stmt_styles = python_template.get("stmt_styles", {})
        if isinstance(stmt_styles, Mapping):
            _append_override_render_paths(
                paths,
                "templates.python.stmt_styles",
                "$.templates.python.stmt_styles",
                stmt_styles,
                preferred_key,
                fallback_key,
                "expr_templates",
            )

    if operator == "~":
        bitwise_note = mapping.get("runtime_semantics_notes", {}).get("bitwise_not")
        if isinstance(bitwise_note, Mapping):
            paths.append(
                {
                    "source": "runtime_semantics_notes.bitwise_not",
                    "mapping_path": "$.runtime_semantics_notes.bitwise_not",
                    "template_key": "~",
                    "status": "parser_rejected",
                    "note": bitwise_note.get(
                        "status",
                        "Current parser grammar does not accept numeric unary '~'.",
                    ),
                }
            )
    return paths


def _z3_case(
    operator: str, kind: str, render_paths: Sequence[_JSON_OBJECT], risk_level: str
) -> _JSON_OBJECT:
    """
    Build one Z3 capability matrix row.

    :param operator: FCSTM operator or function name.
    :type operator: str
    :param kind: Operator category.
    :type kind: str
    :param render_paths: Render-path descriptors.
    :type render_paths: Sequence[Dict[str, Any]]
    :param risk_level: Risk level.
    :type risk_level: str
    :return: Capability matrix row.
    :rtype: Dict[str, Any]

    Example::

        >>> row = _z3_case('+', 'binary', [], 'low')
        >>> row['z3_support']['Int']['status']
        'exact'
    """
    return {
        "fcstm_operator": operator,
        "kind": kind,
        "render_paths": list(render_paths),
        "risk_level": risk_level,
        "z3_support": _z3_support_for_operator(operator),
    }


def _build_z3_int_division_modulo_mismatch_cases() -> List[_JSON_OBJECT]:
    """
    Build counterexamples where Z3 Int arithmetic differs from Python.

    :return: Representative division and modulo mismatch rows.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> rows = _build_z3_int_division_modulo_mismatch_cases()
        >>> any(row['modulo_matches_python'] is False for row in rows)
        True
    """
    cases = []
    for numerator, denominator in [(3, 2), (3, -2), (-3, 2), (-3, -2)]:
        z3_division = z3.simplify(z3.IntVal(numerator) / z3.IntVal(denominator))
        z3_modulo = z3.simplify(z3.IntVal(numerator) % z3.IntVal(denominator))
        python_division = numerator / denominator
        python_modulo = numerator % denominator
        cases.append(
            {
                "numerator": numerator,
                "denominator": denominator,
                "z3_int_division": str(z3_division),
                "python_true_division_repr": repr(python_division),
                "division_matches_python": str(z3_division) == repr(python_division),
                "z3_int_modulo": str(z3_modulo),
                "python_modulo": python_modulo,
                "modulo_matches_python": str(z3_modulo) == str(python_modulo),
            }
        )
    return cases


def _template_path(mapping: Mapping[str, Any], path: Sequence[str]) -> Optional[str]:
    """
    Return a nested string value from the render mapping.

    :param mapping: Render mapping object.
    :type mapping: Mapping[str, Any]
    :param path: Nested key path.
    :type path: Sequence[str]
    :return: String value or ``None``.
    :rtype: Optional[str]

    Example::

        >>> _template_path({'a': {'b': 'c'}}, ['a', 'b'])
        'c'
    """
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def _build_python_render_paths(
    mapping: Mapping[str, Any], repo_root: Union[str, Path]
) -> _JSON_OBJECT:
    """
    Collect Python render-path facts from the R0 mapping.

    :param mapping: R0 render mapping.
    :type mapping: Mapping[str, Any]
    :param repo_root: Repository root path used to load the Python template.
    :type repo_root: Union[str, pathlib.Path]
    :return: Python render path inventory.
    :rtype: Dict[str, Any]

    Example::

        >>> data = _build_python_render_paths({'builtin_expr_styles': {'styles': {}}}, '.')
        >>> 'builtin_python_style' in data
        True
    """
    builtin_templates = (
        mapping.get("builtin_expr_styles", {})
        .get("styles", {})
        .get("python", {})
        .get("templates", {})
    )
    python_template = mapping.get("templates", {}).get("python", {})
    python_renderer = StateMachineCodeRenderer(
        str(Path(repo_root).resolve() / "templates/python")
    )
    rendered_expr_samples = ["sign(A)", "round(A)", "cbrt(A)", "sqrt(A)"]
    return {
        "builtin_python_style": {
            "base_lang": _template_path(
                mapping, ["builtin_expr_styles", "styles", "python", "base_lang"]
            ),
            "templates": {
                key: builtin_templates.get(key)
                for key in [
                    "Name",
                    "Constant",
                    "UnaryOp",
                    "BinaryOp",
                    "BinaryOp(**)",
                    "UFunc(sign)",
                    "UFunc(cbrt)",
                    "UFunc(round)",
                    "UFunc(abs)",
                    "UFunc(sqrt)",
                ]
                if key in builtin_templates
            },
        },
        "template_expr_styles": python_template.get("expr_styles", {}),
        "template_stmt_styles": python_template.get("stmt_styles", {}),
        "representative_rendered_expressions": [
            _render_python_expr(expr)
            for expr in [
                "A + 1",
                "A / 2",
                "A % 2",
                "A << 1",
                "A & 0xff",
                "round(A)",
                "sign(A)",
                "cbrt(A)",
                "sqrt(A)",
                "pi",
                "tau",
                "~A",
            ]
        ],
        "template_rendered_expressions": [
            _render_template_python_expr(python_renderer, expr, style)
            for style in ["python_expr", "python_scope_expr"]
            for expr in rendered_expr_samples
        ],
        "statement_rendered_expressions": [
            _render_template_python_assignment(python_renderer, expr)
            for expr in rendered_expr_samples
        ]
        + [
            _render_template_python_if(
                python_renderer,
                "sign(A) > 0",
                "sign(A)",
            )
        ],
    }


def _build_z3_capability_matrix(mapping: Mapping[str, Any]) -> List[_JSON_OBJECT]:
    """
    Build the Z3 capability matrix for FCSTM numeric operators.

    :param mapping: R0 render mapping.
    :type mapping: Mapping[str, Any]
    :return: Capability matrix rows.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> rows = _build_z3_capability_matrix({})
        >>> any(row['fcstm_operator'] == 'round' for row in rows)
        True
    """
    rows: List[_JSON_OBJECT] = []
    for op in ["+", "-", "*", "/", "%", "**"]:
        rows.append(
            _z3_case(
                op,
                "binary_arithmetic",
                _render_paths_for_operator(mapping, op, "binary_arithmetic"),
                "high" if op in {"/", "%", "**"} else "low",
            )
        )
    for op in ["&", "|", "^", "<<", ">>", "~"]:
        rows.append(
            _z3_case(
                op,
                "bitwise",
                _render_paths_for_operator(mapping, op, "bitwise"),
                "high",
            )
        )
    for op in ["<", "<=", ">", ">=", "==", "!="]:
        rows.append(
            _z3_case(
                op,
                "comparison",
                _render_paths_for_operator(mapping, op, "comparison"),
                "medium",
            )
        )
    for func in _UFUNC_NAMES:
        risk = (
            "high"
            if func not in {"abs", "sign", "floor", "ceil", "trunc", "round"}
            else "medium"
        )
        rows.append(
            _z3_case(
                func,
                "ufunc",
                _render_paths_for_operator(mapping, func, "ufunc"),
                risk,
            )
        )
    return rows


def _python_alignment_cases(
    mapping: Mapping[str, Any], repo_root: Union[str, Path]
) -> List[_JSON_OBJECT]:
    """
    Build Python baseline cases using the shared probe join fields.

    :param mapping: R0 render mapping snapshot.
    :type mapping: Mapping[str, Any]
    :param repo_root: Repository root path used to load the Python template.
    :type repo_root: Union[str, pathlib.Path]
    :return: Render-path scoped Python alignment cases.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> cases = _python_alignment_cases({'builtin_expr_styles': {'styles': {}}}, '.')
        >>> {'case_id', 'operator', 'fcstm_expression', 'render_path', 'render_expression'} <= set(cases[0])
        True
    """
    renderer = StateMachineCodeRenderer(
        str(Path(repo_root).resolve() / "templates/python")
    )
    semantic_cases = [
        ("round", "round", "round(A)"),
        ("abs", "abs", "abs(A)"),
        ("sign", "sign", "sign(A)"),
        ("cbrt", "cbrt", "cbrt(A)"),
        ("pow", "**", "A ** B"),
        ("integer_division", "/", "A / B"),
        ("modulo", "%", "A % B"),
        ("signed_left_shift", "<<", "A << B"),
        ("bitwise_not", "~", "~A"),
    ]
    cases: List[_JSON_OBJECT] = []
    for semantic_id, operator, expression in semantic_cases:
        builtin = _render_python_expr(expression)
        cases.append(
            {
                "case_id": "builtin_python_style:%s" % semantic_id,
                "semantic_case_id": semantic_id,
                "operator": operator,
                "fcstm_expression": expression,
                "render_path": "builtin_python_style",
                "render_expression": builtin.get("rendered", ""),
                "status": builtin.get("status", "unknown"),
                "ast_type": builtin.get("ast_type"),
            }
        )
        for style in ["python_expr", "python_scope_expr"]:
            rendered = _render_template_python_expr(renderer, expression, style)
            cases.append(
                {
                    "case_id": "%s:%s" % (style, semantic_id),
                    "semantic_case_id": semantic_id,
                    "operator": operator,
                    "fcstm_expression": expression,
                    "render_path": "templates.python.expr_styles.%s" % style,
                    "render_expression": rendered.get("rendered", ""),
                    "status": rendered.get("status", "unknown"),
                    "ast_type": rendered.get("ast_type"),
                }
            )
        assignment = _render_template_python_assignment(renderer, expression)
        cases.append(
            {
                "case_id": "python_runtime_assignment:%s" % semantic_id,
                "semantic_case_id": semantic_id,
                "operator": operator,
                "fcstm_expression": expression,
                "render_path": "templates.python.stmt_styles.python_runtime",
                "render_expression": assignment.get("rendered", ""),
                "status": assignment.get("status", "unknown"),
                "sample": assignment.get("sample"),
            }
        )
    return cases


def build_python_z3_baseline(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
) -> _JSON_OBJECT:
    """
    Build the Python/Z3 numeric semantics baseline snapshot.

    The snapshot is intentionally small and deterministic: it records render
    paths, representative Python runtime samples, and Z3 capability levels
    rather than exhaustive model outputs.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path, defaults to the committed
        R0 snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :return: JSON-compatible Python/Z3 baseline payload.
    :rtype: Dict[str, Any]

    Example::

        >>> baseline = build_python_z3_baseline('.')
        >>> baseline['mode']
        'python-z3-baseline'
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    mapping_sha = mapping.get("mapping_sha256")
    if not isinstance(mapping_sha, str):
        mapping_sha = ""
    return {
        "schema_version": 1,
        "mode": "python-z3-baseline",
        "language": "python-z3",
        "source_mapping_sha256": mapping_sha,
        "render_mapping_sha256": mapping_sha,
        "generator": {
            "tool": "tools/numeric_render_probe.py",
            "research_path": _RESEARCH_PATH,
            "source_commit": _git_commit(root),
            "source_commit_policy": "Best-effort commit at generation time; mapping and schema validation are the stable comparison keys.",
            "determinism": "No wall-clock timestamp is stored; concrete Z3 model values are not used as core facts.",
        },
        "repository": {
            "root": ".",
            "render_mapping_snapshot": mapping_file.relative_to(root).as_posix(),
            "schema_path": _PYTHON_Z3_BASELINE_SCHEMA,
        },
        "toolchain": {
            "python": {
                "executable": Path(sys.executable).name,
                "version": sys.version.split()[0],
                "implementation": platform.python_implementation(),
            },
            "z3": {
                "python_package_version": z3.get_version_string(),
                "seed_policy": "Capability rows avoid solver model dependence; future model-valued rows must record a fixed seed.",
            },
        },
        "python_render_paths": _build_python_render_paths(mapping, root),
        "alignment_cases": _python_alignment_cases(mapping, root),
        "python_runtime_samples": _build_python_runtime_samples(),
        "z3_representative_samples": _build_z3_representative_samples(),
        "z3_capability_matrix": _build_z3_capability_matrix(mapping),
        "representative_notes": [
            {
                "topic": "python-infinite-precision",
                "summary": "Python samples are a P3 infinite-precision simulation-compatible baseline, not the fixed-width default profile.",
            },
            {
                "topic": "z3-totalized-division",
                "summary": "Z3 arithmetic division and modulo are total at zero; later solver work must carry definedness obligations.",
            },
            {
                "topic": "transcendental-functions",
                "summary": "Current solver helpers raise NotImplementedError for trigonometric, hyperbolic, logarithmic and exponential functions.",
            },
            {
                "topic": "bitwise-not",
                "summary": "The parser currently rejects '~A' in numeric expressions. The Z3 samples also record TypeError for Int bitwise construction, while BitVec provides fixed-width bitwise operations.",
            },
        ],
    }


def _validate_support_matrix(row: Mapping[str, Any], path: str) -> List[str]:
    """
    Validate one Z3 capability matrix row.

    :param row: Capability row.
    :type row: Mapping[str, Any]
    :param path: Human-readable row path for diagnostics.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_support_matrix({'z3_support': {}}, 'row')
        ['row missing z3_support.Int', 'row missing z3_support.Real', 'row missing z3_support.BitVec', 'row missing z3_support.FP']
    """
    errors = []
    support = row.get("z3_support")
    if not isinstance(support, Mapping):
        return ["%s.z3_support must be a mapping" % path]
    for sort in _Z3_SORTS:
        item = support.get(sort)
        if not isinstance(item, Mapping):
            errors.append("%s missing z3_support.%s" % (path, sort))
            continue
        status = item.get("status")
        if status not in _Z3_SUPPORT_LEVELS:
            errors.append(
                "%s.z3_support.%s has invalid status %r" % (path, sort, status)
            )
        for key in ["strategy", "note"]:
            if not isinstance(item.get(key), str) or not item.get(key):
                errors.append(
                    "%s.z3_support.%s.%s must be a non-empty string" % (path, sort, key)
                )
    return errors


def _json_type_matches(value: Any, type_name: str) -> bool:
    """
    Return whether a Python value satisfies a small JSON Schema type name.

    :param value: JSON-compatible value.
    :type value: Any
    :param type_name: JSON Schema type name.
    :type type_name: str
    :return: Whether the value matches the requested schema type.
    :rtype: bool

    Example::

        >>> _json_type_matches({'ok': True}, 'object')
        True
        >>> _json_type_matches(True, 'integer')
        False
    """
    if type_name == "object":
        return isinstance(value, Mapping)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(
            value, float
        )
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    return False


def _json_number_equals(actual: Any, expected: Union[int, float]) -> bool:
    """
    Return whether a JSON number exactly matches an expected case-plan value.

    Python booleans compare equal to ``0`` and ``1``, but JSON booleans are not
    numeric smoke inputs. This helper keeps case-plan drift checks strict at the
    Python/JSON boundary.

    :param actual: JSON value from a smoke payload.
    :type actual: Any
    :param expected: Expected numeric case-plan value.
    :type expected: Union[int, float]
    :return: Whether ``actual`` is a non-boolean number equal to ``expected``.
    :rtype: bool

    Example::

        >>> _json_number_equals(1, 1)
        True
        >>> _json_number_equals(True, 1)
        False
    """
    if isinstance(actual, bool):
        return False
    if not isinstance(actual, (int, float)):
        return False
    return actual == expected


def _resolve_local_schema_ref(root_schema: Mapping[str, Any], ref: str) -> Any:
    """
    Resolve a local ``#/`` JSON Schema reference.

    :param root_schema: Root schema document.
    :type root_schema: Mapping[str, Any]
    :param ref: Local reference string.
    :type ref: str
    :return: Referenced schema fragment.
    :rtype: Any
    :raises ValueError: If ``ref`` is not a supported local reference.
    :raises KeyError: If the reference path does not exist.

    Example::

        >>> _resolve_local_schema_ref({'$defs': {'x': {'type': 'string'}}}, '#/$defs/x')['type']
        'string'
    """
    if not ref.startswith("#/"):
        raise ValueError("only local JSON Schema references are supported: %s" % ref)
    current: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, Mapping):
            raise KeyError(ref)
        current = current[part]
    return current


def _validate_json_schema_fragment(
    value: Any,
    schema: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    path: str,
) -> List[str]:
    """
    Validate one value against the repository's lightweight schema subset.

    The helper intentionally implements only the JSON Schema keywords used by
    the research artifact schemas: ``$ref``, ``allOf``, ``if`` / ``then``, ``not``,
    ``type``, ``required``, ``properties``, object
    ``additionalProperties``, ``const``, ``enum``, ``pattern``,
    string ``minLength``, object ``minProperties`` / ``maxProperties``,
    ``minItems`` and homogeneous ``items``.

    :param value: JSON-compatible value to validate.
    :type value: Any
    :param schema: Schema fragment.
    :type schema: Mapping[str, Any]
    :param root_schema: Root schema document used for local references.
    :type root_schema: Mapping[str, Any]
    :param path: Human-readable JSON path for diagnostics.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_json_schema_fragment({'a': 1}, {'type': 'object', 'required': ['a']}, {}, '$')
        []
        >>> schema = {
        ...     'if': {'properties': {'kind': {'const': 'x'}}},
        ...     'then': {'required': ['value']},
        ... }
        >>> _validate_json_schema_fragment({'kind': 'x'}, schema, {}, '$')
        ['$.then missing required key value']
        >>> _validate_json_schema_fragment('', {'type': 'string', 'minLength': 1}, {}, '$')
        ['$ must contain at least 1 characters']
        >>> _validate_json_schema_fragment({}, {'type': 'object', 'minProperties': 1}, {}, '$')
        ['$ must contain at least 1 properties']
        >>> _validate_json_schema_fragment({'ok': True}, {'not': {'properties': {'ok': {'const': True}}}}, {}, '$')
        ['$ must not match disallowed schema']
    """
    errors: List[str] = []
    ref = schema.get("$ref")
    if isinstance(ref, str):
        try:
            target = _resolve_local_schema_ref(root_schema, ref)
        except (ValueError, KeyError) as err:
            # ValueError: the schema used an unsupported reference form;
            # KeyError: the local reference path is absent from the schema.
            return ["%s has unresolved schema reference %r: %s" % (path, ref, err)]
        if not isinstance(target, Mapping):
            return ["%s schema reference %r did not resolve to an object" % (path, ref)]
        return _validate_json_schema_fragment(value, target, root_schema, path)

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for index, child_schema in enumerate(all_of):
            if not isinstance(child_schema, Mapping):
                errors.append("%s.allOf[%d] must be a schema object" % (path, index))
                continue
            errors.extend(
                _validate_json_schema_fragment(
                    value,
                    child_schema,
                    root_schema,
                    "%s.allOf[%d]" % (path, index),
                )
            )

    if_schema = schema.get("if")
    then_schema = schema.get("then")
    if isinstance(if_schema, Mapping) and isinstance(then_schema, Mapping):
        condition_errors = _validate_json_schema_fragment(
            value,
            if_schema,
            root_schema,
            "%s.if" % path,
        )
        if not condition_errors:
            errors.extend(
                _validate_json_schema_fragment(
                    value,
                    then_schema,
                    root_schema,
                    "%s.then" % path,
                )
            )

    not_schema = schema.get("not")
    if isinstance(not_schema, Mapping):
        not_errors = _validate_json_schema_fragment(
            value,
            not_schema,
            root_schema,
            "%s.not" % path,
        )
        if not not_errors:
            errors.append("%s must not match disallowed schema" % path)

    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        expected_types = [expected_type]
    elif isinstance(expected_type, list):
        expected_types = [item for item in expected_type if isinstance(item, str)]
    else:
        expected_types = []
    if expected_types and not any(
        _json_type_matches(value, type_name) for type_name in expected_types
    ):
        errors.append("%s must match type %s" % (path, " or ".join(expected_types)))
        return errors

    if "const" in schema and value != schema["const"]:
        errors.append("%s must equal %r" % (path, schema["const"]))
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        errors.append("%s must be one of %r" % (path, enum_values))
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and isinstance(value, str):
        try:
            matched = re.search(pattern, value) is not None
        except re.error as err:
            # re.error: the repository schema contains an invalid regular
            # expression and therefore cannot validate this field.
            errors.append("%s has invalid schema pattern %r: %s" % (path, pattern, err))
        else:
            if not matched:
                errors.append("%s must match pattern %r" % (path, pattern))
    min_length = schema.get("minLength")
    if isinstance(min_length, int) and isinstance(value, str):
        if len(value) < min_length:
            errors.append("%s must contain at least %d characters" % (path, min_length))

    if isinstance(value, Mapping):
        min_properties = schema.get("minProperties")
        if isinstance(min_properties, int) and len(value) < min_properties:
            errors.append(
                "%s must contain at least %d properties" % (path, min_properties)
            )
        max_properties = schema.get("maxProperties")
        if isinstance(max_properties, int) and len(value) > max_properties:
            errors.append(
                "%s must contain at most %d properties" % (path, max_properties)
            )
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    errors.append("%s missing required key %s" % (path, key))
        properties = schema.get("properties")
        if isinstance(properties, Mapping):
            if schema.get("additionalProperties") is False:
                extra_keys = sorted(set(value) - set(properties))
                for key in extra_keys:
                    errors.append("%s has unexpected key %s" % (path, key))
            for key, child_schema in properties.items():
                if key not in value or not isinstance(child_schema, Mapping):
                    continue
                errors.extend(
                    _validate_json_schema_fragment(
                        value[key],
                        child_schema,
                        root_schema,
                        "%s.%s" % (path, key),
                    )
                )
        additional = schema.get("additionalProperties")
        if isinstance(additional, Mapping):
            known_keys = set(properties) if isinstance(properties, Mapping) else set()
            for key, child_value in value.items():
                if key in known_keys:
                    continue
                errors.extend(
                    _validate_json_schema_fragment(
                        child_value,
                        additional,
                        root_schema,
                        "%s.%s" % (path, key),
                    )
                )

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append("%s must contain at least %d items" % (path, min_items))
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                errors.extend(
                    _validate_json_schema_fragment(
                        item,
                        item_schema,
                        root_schema,
                        "%s[%d]" % (path, index),
                    )
                )
    return errors


def _validate_payload_with_schema(
    payload: Mapping[str, Any], schema: Mapping[str, Any]
) -> List[str]:
    """
    Validate a payload against a loaded research artifact schema.

    :param payload: JSON-compatible artifact payload.
    :type payload: Mapping[str, Any]
    :param schema: Loaded JSON Schema document.
    :type schema: Mapping[str, Any]
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_payload_with_schema(
        ...     {'schema_version': 1},
        ...     {'type': 'object', 'required': ['schema_version']},
        ... )
        []
    """
    return _validate_json_schema_fragment(payload, schema, schema, "$")


def validate_python_z3_baseline(payload: Mapping[str, Any]) -> List[str]:
    """
    Validate the Python/Z3 baseline contract without repository tests.

    :param payload: Baseline payload.
    :type payload: Mapping[str, Any]
    :return: Human-readable diagnostics.
    :rtype: List[str]

    Example::

        >>> validate_python_z3_baseline({'schema_version': 1})[:2]
        ['mode must be python-z3-baseline', 'language must be python-z3']
    """
    errors: List[str] = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if payload.get("mode") != "python-z3-baseline":
        errors.append("mode must be python-z3-baseline")
    if payload.get("language") != "python-z3":
        errors.append("language must be python-z3")
    alignment_cases = payload.get("alignment_cases")
    if not isinstance(alignment_cases, list) or not alignment_cases:
        errors.append("alignment_cases must be a non-empty list")
    else:
        required_join_keys = {
            "case_id",
            "operator",
            "fcstm_expression",
            "render_path",
            "render_expression",
        }
        for index, case in enumerate(alignment_cases):
            if not isinstance(case, Mapping):
                errors.append("alignment_cases[%d] must be a mapping" % index)
                continue
            missing = sorted(required_join_keys - set(case))
            if missing:
                errors.append(
                    "alignment_cases[%d] missing shared join fields: %s"
                    % (index, ", ".join(missing))
                )
    for key in ["source_mapping_sha256", "render_mapping_sha256"]:
        value = payload.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            errors.append("%s must be a lowercase 64-character sha256 hex string" % key)
    if payload.get("source_mapping_sha256") != payload.get("render_mapping_sha256"):
        errors.append("source_mapping_sha256 and render_mapping_sha256 must match")

    generator = payload.get("generator")
    if not isinstance(generator, Mapping):
        errors.append("generator must be a mapping")
    else:
        for key in [
            "tool",
            "research_path",
            "source_commit",
            "source_commit_policy",
            "determinism",
        ]:
            if key == "source_commit":
                value = generator.get(key)
                if value is not None and (
                    not isinstance(value, str)
                    or len(value) != 40
                    or any(ch not in "0123456789abcdef" for ch in value)
                ):
                    errors.append("generator.source_commit must be a git SHA or null")
                continue
            if not isinstance(generator.get(key), str) or not generator.get(key):
                errors.append("generator.%s must be a non-empty string" % key)

    repository = payload.get("repository")
    if not isinstance(repository, Mapping):
        errors.append("repository must be a mapping")
    else:
        for key in ["root", "render_mapping_snapshot", "schema_path"]:
            if not isinstance(repository.get(key), str) or not repository.get(key):
                errors.append("repository.%s must be a non-empty string" % key)

    toolchain = payload.get("toolchain")
    if not isinstance(toolchain, Mapping):
        errors.append("toolchain must be a mapping")
    else:
        if not isinstance(toolchain.get("python"), Mapping):
            errors.append("toolchain.python must be a mapping")
        if not isinstance(toolchain.get("z3"), Mapping):
            errors.append("toolchain.z3 must be a mapping")

    render_paths = payload.get("python_render_paths")
    if not isinstance(render_paths, Mapping):
        errors.append("python_render_paths must be a mapping")
    else:
        rendered = render_paths.get("representative_rendered_expressions")
        if not isinstance(rendered, list) or not rendered:
            errors.append(
                "python_render_paths.representative_rendered_expressions must be non-empty"
            )
        else:
            by_expr = {
                item.get("expr"): item for item in rendered if isinstance(item, Mapping)
            }
            for expr in ["round(A)", "sign(A)", "cbrt(A)", "~A"]:
                if expr not in by_expr:
                    errors.append(
                        "missing representative rendered expression: %s" % expr
                    )
            if by_expr.get("~A", {}).get("status") != "parse_failed":
                errors.append(
                    "~A representative expression must record current parse_failed status"
                )
        template_rendered = render_paths.get("template_rendered_expressions")
        if not isinstance(template_rendered, list) or not template_rendered:
            errors.append(
                "python_render_paths.template_rendered_expressions must be non-empty"
            )
        else:
            template_by_key = {
                (item.get("style"), item.get("expr")): item
                for item in template_rendered
                if isinstance(item, Mapping)
            }
            for style in ["python_expr", "python_scope_expr"]:
                for expr in ["sign(A)", "round(A)", "cbrt(A)", "sqrt(A)"]:
                    row = template_by_key.get((style, expr))
                    if row is None:
                        errors.append(
                            "missing template rendered expression: %s %s"
                            % (style, expr)
                        )
                    elif row.get("status") != "rendered":
                        errors.append(
                            "template rendered expression %s %s must render"
                            % (style, expr)
                        )
            sign_expr = template_by_key.get(("python_expr", "sign(A)"), {})
            if sign_expr.get("rendered") != 'self._sign(self._vars["A"])':
                errors.append(
                    'python_expr sign(A) must render through self._sign(self._vars["A"])'
                )
            sign_scope = template_by_key.get(("python_scope_expr", "sign(A)"), {})
            if sign_scope.get("rendered") != 'self._sign(scope["A"])':
                errors.append(
                    'python_scope_expr sign(A) must render through self._sign(scope["A"])'
                )
        statement_rendered = render_paths.get("statement_rendered_expressions")
        if not isinstance(statement_rendered, list) or not statement_rendered:
            errors.append(
                "python_render_paths.statement_rendered_expressions must be non-empty"
            )
        else:
            statement_by_key = {
                (item.get("style"), item.get("sample"), item.get("expr")): item
                for item in statement_rendered
                if isinstance(item, Mapping)
            }
            sign_assignment = statement_by_key.get(
                ("python_runtime", "assign_state_var", "sign(A)"), {}
            )
            sign_rendered = sign_assignment.get("rendered")
            if not isinstance(sign_rendered, str) or '_s(_v["A"])' not in sign_rendered:
                errors.append(
                    'python_runtime sign(A) assignment must render through _s(_v["A"])'
                )
            if not any(
                isinstance(item, Mapping)
                and item.get("style") == "python_runtime"
                and item.get("sample") == "if_assign_state_var"
                and isinstance(item.get("rendered"), str)
                and "if self._evaluate_runtime_expr" in item.get("rendered")
                for item in statement_rendered
            ):
                errors.append(
                    "python_runtime statement samples must include a rendered if-block"
                )

    samples = payload.get("python_runtime_samples")
    if not isinstance(samples, Mapping):
        errors.append("python_runtime_samples must be a mapping")
    else:
        constants = samples.get("constants")
        if not isinstance(constants, list):
            errors.append("python_runtime_samples.constants must be an array")
        else:
            constants_by_name = {
                item.get("name"): item
                for item in constants
                if isinstance(item, Mapping)
            }
            if "E" not in constants_by_name:
                errors.append(
                    "python_runtime_samples.constants must include DSL constant E"
                )
            else:
                e_render = constants_by_name["E"].get("render")
                if not isinstance(e_render, Mapping):
                    errors.append("DSL constant E render metadata must be a mapping")
                elif e_render.get("ast_type") != "Constant":
                    errors.append("DSL constant E must render from a Constant AST node")
        round_cases = samples.get("round_half_cases")
        if not isinstance(round_cases, list) or len(round_cases) < 6:
            errors.append(
                "python_runtime_samples.round_half_cases must include half-even examples"
            )
        else:
            round_by_input = {
                item.get("input"): item
                for item in round_cases
                if isinstance(item, Mapping)
            }
            for value, expected_python, expected_z3 in [
                ("-2.5", -2, "-2"),
                ("0.5", 0, "0"),
                ("2.5", 2, "2"),
            ]:
                row = round_by_input.get(value)
                if row is None:
                    errors.append("missing round half case for %s" % value)
                    continue
                if row.get("python_round") != expected_python:
                    errors.append(
                        "round(%s) must be Python half-even value %r"
                        % (value, expected_python)
                    )
                if row.get("z3_python_round_to_z3") != expected_z3:
                    errors.append(
                        "python_round_to_z3(%s) must simplify to %s"
                        % (value, expected_z3)
                    )
        sign_cases = samples.get("sign_cases")
        if not isinstance(sign_cases, list) or not any(
            item.get("python_sign") == -1
            for item in sign_cases
            if isinstance(item, Mapping)
        ):
            errors.append(
                "python_runtime_samples.sign_cases must include a negative sign example"
            )
        elif not any(
            isinstance(item, Mapping)
            and item.get("input") == "-3"
            and item.get("python_sign") == -1
            for item in sign_cases
        ):
            errors.append("python sign sample for -3 must be -1")
        cbrt_cases = samples.get("cbrt_cases")
        if not isinstance(cbrt_cases, list) or not any(
            str(item.get("input")) == "-8"
            for item in cbrt_cases
            if isinstance(item, Mapping)
        ):
            errors.append("python_runtime_samples.cbrt_cases must include -8")
        shift_cases = samples.get("shift_cases")
        if not isinstance(shift_cases, list) or not any(
            isinstance(item, Mapping)
            and item.get("expression") == "-8 >> 1"
            and item.get("python_value") == -4
            for item in shift_cases
        ):
            errors.append(
                "python_runtime_samples.shift_cases must include -8 >> 1 == -4"
            )

    z3_samples = payload.get("z3_representative_samples")
    if not isinstance(z3_samples, Mapping):
        errors.append("z3_representative_samples must be a mapping")
    else:
        int_bitwise = z3_samples.get("int_bitwise_operator_results")
        if not isinstance(int_bitwise, list) or not int_bitwise:
            errors.append(
                "z3_representative_samples.int_bitwise_operator_results must be non-empty"
            )
        elif not all(
            isinstance(item, Mapping) and item.get("status") == "type_error"
            for item in int_bitwise
        ):
            errors.append("Z3 Int bitwise samples must record current TypeError status")
        bitvec_bitwise = z3_samples.get("bitvec_bitwise_operator_results")
        if not isinstance(bitvec_bitwise, list) or not bitvec_bitwise:
            errors.append(
                "z3_representative_samples.bitvec_bitwise_operator_results must be non-empty"
            )
        elif not all(
            isinstance(item, Mapping) and item.get("status") == "built"
            for item in bitvec_bitwise
        ):
            errors.append("Z3 BitVec bitwise samples must build successfully")
        mismatch_cases = z3_samples.get("int_division_modulo_python_mismatch_cases")
        if not isinstance(mismatch_cases, list) or not mismatch_cases:
            errors.append(
                "z3_representative_samples.int_division_modulo_python_mismatch_cases must be non-empty"
            )
        else:
            if not any(
                isinstance(item, Mapping)
                and item.get("division_matches_python") is False
                for item in mismatch_cases
            ):
                errors.append(
                    "Z3 Int division mismatch cases must include a Python true-division mismatch"
                )
            if not any(
                isinstance(item, Mapping) and item.get("modulo_matches_python") is False
                for item in mismatch_cases
            ):
                errors.append(
                    "Z3 Int modulo mismatch cases must include a negative-divisor mismatch"
                )

    matrix = payload.get("z3_capability_matrix")
    if not isinstance(matrix, list) or not matrix:
        errors.append("z3_capability_matrix must be a non-empty array")
    else:
        rows_by_operator = {
            item.get("fcstm_operator"): item
            for item in matrix
            if isinstance(item, Mapping)
        }
        operators = set(rows_by_operator)
        for required in ["round", "sign", "cbrt", "~", "/", "%"]:
            if required not in operators:
                errors.append("z3_capability_matrix missing operator %s" % required)
        division_row = rows_by_operator.get("/")
        if isinstance(division_row, Mapping):
            division_int = division_row.get("z3_support", {}).get("Int", {})
            if (
                isinstance(division_int, Mapping)
                and division_int.get("status") == "exact"
            ):
                errors.append(
                    "z3_capability_matrix '/' Int support must not be exact for Python true-division baseline"
                )
        modulo_row = rows_by_operator.get("%")
        if isinstance(modulo_row, Mapping):
            modulo_int = modulo_row.get("z3_support", {}).get("Int", {})
            if isinstance(modulo_int, Mapping) and modulo_int.get("status") == "exact":
                errors.append(
                    "z3_capability_matrix '%' Int support must not be exact for Python modulo baseline"
                )
        for unsupported_func in [
            "cbrt",
            "sin",
            "cos",
            "tan",
            "exp",
            "log",
            "log10",
            "log2",
            "log1p",
        ]:
            row = rows_by_operator.get(unsupported_func)
            if not isinstance(row, Mapping):
                continue
            support = row.get("z3_support", {})
            for sort in ["Int", "Real"]:
                item = support.get(sort) if isinstance(support, Mapping) else None
                if isinstance(item, Mapping) and item.get("status") != "unsupported":
                    errors.append(
                        "z3_capability_matrix %s %s support must be unsupported for current solver fact"
                        % (unsupported_func, sort)
                    )
        for index, row in enumerate(matrix):
            if not isinstance(row, Mapping):
                errors.append("z3_capability_matrix[%d] must be a mapping" % index)
                continue
            if not isinstance(row.get("fcstm_operator"), str) or not row.get(
                "fcstm_operator"
            ):
                errors.append(
                    "z3_capability_matrix[%d].fcstm_operator must be a non-empty string"
                    % index
                )
            if row.get("risk_level") not in _RISK_LEVELS:
                errors.append("z3_capability_matrix[%d].risk_level is invalid" % index)
            render_paths = row.get("render_paths")
            if not isinstance(render_paths, list) or not render_paths:
                errors.append(
                    "z3_capability_matrix[%d].render_paths must be non-empty" % index
                )
            errors.extend(
                _validate_support_matrix(row, "z3_capability_matrix[%d]" % index)
            )

    notes = payload.get("representative_notes")
    if not isinstance(notes, list) or not notes:
        errors.append("representative_notes must be a non-empty array")
    return errors


def _baseline_comparison_payload(payload: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Return a deep-copied baseline payload for deterministic comparisons.

    Provenance and environment fields are intentionally ignored because a
    committed snapshot cannot contain its own final commit hash and local
    ``--check`` should remain useful across Python environments.

    :param payload: Baseline payload.
    :type payload: Mapping[str, Any]
    :return: JSON-compatible payload with volatile fields normalized.
    :rtype: Dict[str, Any]

    Example::

        >>> payload = {'generator': {'source_commit': 'a' * 40}, 'toolchain': {'python': {'executable': '/tmp/python'}}, 'x': 1}
        >>> _baseline_comparison_payload(payload)['generator']['source_commit']
        '<ignored>'
        >>> _baseline_comparison_payload(payload)['toolchain']['python']['executable']
        '<ignored>'
    """
    comparable = json.loads(_stable_json(payload))
    generator = comparable.get("generator")
    if isinstance(generator, dict):
        generator["source_commit"] = "<ignored>"
    repository = comparable.get("repository")
    if isinstance(repository, dict):
        repository["render_mapping_snapshot"] = _DEFAULT_MAPPING_PATH
    toolchain = comparable.get("toolchain")
    if isinstance(toolchain, dict):
        python_info = toolchain.get("python")
        if isinstance(python_info, dict):
            for key in ["executable", "version", "implementation"]:
                python_info[key] = "<ignored>"
        z3_info = toolchain.get("z3")
        if isinstance(z3_info, dict):
            z3_info["python_package_version"] = "<ignored>"
    render_paths = comparable.get("python_render_paths")
    if isinstance(render_paths, dict):
        rendered = render_paths.get("representative_rendered_expressions")
        if isinstance(rendered, list):
            for item in rendered:
                if isinstance(item, dict) and item.get("status") != "rendered":
                    item["error"] = "<ignored>"
    z3_samples = comparable.get("z3_representative_samples")
    if isinstance(z3_samples, dict):
        for key in ["int_bitwise_operator_results", "bitvec_bitwise_operator_results"]:
            cases = z3_samples.get(key)
            if not isinstance(cases, list):
                continue
            for item in cases:
                if isinstance(item, dict) and item.get("status") != "built":
                    item["error"] = "<ignored>"
    return comparable


def _first_baseline_difference(
    expected: Any, actual: Any, path: str = "$"
) -> Optional[str]:
    """
    Return the first structural difference between two baseline payloads.

    :param expected: Expected JSON-compatible value.
    :type expected: Any
    :param actual: Actual JSON-compatible value.
    :type actual: Any
    :param path: Diagnostic path, defaults to ``"$"``.
    :type path: str, optional
    :return: First difference diagnostic or ``None``.
    :rtype: Optional[str]

    Example::

        >>> _first_baseline_difference({'a': 1}, {'a': 2})
        '$.a differs: expected 1, got 2'
    """
    if isinstance(expected, dict) and isinstance(actual, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        missing = sorted(expected_keys - actual_keys)
        if missing:
            return "%s missing key %s" % (path, missing[0])
        extra = sorted(actual_keys - expected_keys)
        if extra:
            return "%s has unexpected key %s" % (path, extra[0])
        for key in sorted(expected):
            difference = _first_baseline_difference(
                expected[key], actual[key], "%s.%s" % (path, key)
            )
            if difference:
                return difference
        return None
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return "%s length differs: expected %d, got %d" % (
                path,
                len(expected),
                len(actual),
            )
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            difference = _first_baseline_difference(
                expected_item, actual_item, "%s[%d]" % (path, index)
            )
            if difference:
                return difference
        return None
    if expected != actual:
        return "%s differs: expected %r, got %r" % (path, expected, actual)
    return None


def check_python_z3_baseline(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
) -> _JSON_OBJECT:
    """
    Build and validate the Python/Z3 baseline snapshot contract.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path checked against live drift,
        defaults to the committed R0 snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :return: Check result with ``ok`` and ``errors`` fields.
    :rtype: Dict[str, Any]

    Example::

        >>> result = check_python_z3_baseline('.')
        >>> isinstance(result['ok'], bool)
        True
    """
    root = _as_repo_path(repo_root)
    live = build_python_z3_baseline(root, mapping_path=mapping_path)
    errors = [
        "live baseline: %s" % error for error in validate_python_z3_baseline(live)
    ]
    live_mapping = build_render_mapping(root)
    live_mapping_sha = live_mapping.get("mapping_sha256")
    if live_mapping_sha != live.get("source_mapping_sha256"):
        errors.append(
            "render_mapping snapshot drift: snapshot %r does not match live %r"
            % (live.get("source_mapping_sha256"), live_mapping_sha)
        )
    schema = None
    schema_path = root / _PYTHON_Z3_BASELINE_SCHEMA
    try:
        schema = _read_json(schema_path)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        # OSError: schema cannot be read; JSONDecodeError: invalid JSON;
        # ValueError: top-level schema JSON is not an object.
        errors.append("schema cannot be loaded: %s" % err)
    if schema is not None:
        errors.extend(
            "live schema: %s" % error
            for error in _validate_payload_with_schema(live, schema)
        )
    snapshot_path = root / _PYTHON_Z3_BASELINE_SNAPSHOT
    snapshot_present = snapshot_path.is_file()
    if not snapshot_present:
        errors.append("expected snapshot is missing: %s" % snapshot_path)
    else:
        try:
            snapshot = _read_json(snapshot_path)
        except (OSError, json.JSONDecodeError, ValueError) as err:
            # OSError: snapshot cannot be read; JSONDecodeError: invalid JSON;
            # ValueError: top-level JSON is not an object.
            errors.append("snapshot cannot be loaded: %s" % err)
        else:
            errors.extend(
                "snapshot: %s" % error
                for error in validate_python_z3_baseline(snapshot)
            )
            if schema is not None:
                errors.extend(
                    "snapshot schema: %s" % error
                    for error in _validate_payload_with_schema(snapshot, schema)
                )
            snapshot_difference = _first_baseline_difference(
                _baseline_comparison_payload(live),
                _baseline_comparison_payload(snapshot),
            )
            if snapshot_difference:
                errors.append(
                    "snapshot does not match live baseline: %s" % snapshot_difference
                )
            if snapshot.get("source_mapping_sha256") != live.get(
                "source_mapping_sha256"
            ):
                errors.append(
                    "snapshot source_mapping_sha256 %r does not match live %r"
                    % (
                        snapshot.get("source_mapping_sha256"),
                        live.get("source_mapping_sha256"),
                    )
                )
    return {
        "ok": not errors,
        "errors": errors,
        "schema_version": live["schema_version"],
        "source_mapping_sha256": live["source_mapping_sha256"],
        "snapshot_present": snapshot_present,
        "snapshot_path": _PYTHON_Z3_BASELINE_SNAPSHOT,
    }


def check_java_rust_smoke(
    mode: str,
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
    work_dir: Optional[Union[str, Path]] = None,
    timeout: int = 10,
) -> _JSON_OBJECT:
    """
    Build and validate the Java/Rust smoke contract.

    :param mode: ``"java-smoke"``, ``"rust-smoke"`` or
        ``"java-rust-smoke"``.
    :type mode: str
    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path checked against live
        drift, defaults to the committed R0 snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :param work_dir: Optional directory for temporary compile artifacts.
    :type work_dir: Optional[Union[str, pathlib.Path]], optional
    :param timeout: Per-command timeout in seconds, defaults to ``10``.
    :type timeout: int, optional
    :return: Check result with ``ok``, ``errors`` and snapshot enforcement
        fields.
    :rtype: Dict[str, Any]
    :raises ValueError: If ``mode`` is not a Java/Rust smoke mode.

    Example::

        >>> result = check_java_rust_smoke('java-smoke', '.')
        >>> isinstance(result['ok'], bool)
        True
    """
    if mode not in _JAVA_RUST_MODES:
        raise ValueError("Unsupported Java/Rust smoke mode: %s" % mode)
    root = _as_repo_path(repo_root)
    live = build_java_rust_smoke_report(
        mode, root, mapping_path=mapping_path, work_dir=work_dir, timeout=timeout
    )
    errors = [
        "live smoke: %s" % error
        for error in validate_java_rust_smoke(live, expected_mode=mode)
    ]
    live_mapping = build_render_mapping(root)
    live_mapping_sha = live_mapping.get("mapping_sha256")
    if live_mapping_sha != live.get("source_mapping_sha256"):
        errors.append(
            "render_mapping snapshot drift: snapshot %r does not match live %r"
            % (live.get("source_mapping_sha256"), live_mapping_sha)
        )
    schema = None
    schema_path = root / _JAVA_RUST_SMOKE_SCHEMA
    try:
        schema = _read_json(schema_path)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        # OSError: schema cannot be read; JSONDecodeError: invalid JSON;
        # ValueError: top-level schema JSON is not an object.
        errors.append("schema cannot be loaded: %s" % err)
    if schema is not None:
        errors.extend(
            "live schema: %s" % error
            for error in _validate_payload_with_schema(live, schema)
        )

    snapshot_path = root / _JAVA_RUST_SMOKE_SNAPSHOT
    snapshot_present = snapshot_path.is_file()
    if mode == "java-rust-smoke":
        if not snapshot_present:
            errors.append("expected snapshot is missing: %s" % snapshot_path)
        else:
            snapshot_sidecar = root / _JAVA_RUST_SMOKE_SNAPSHOT_SHA256
            if not snapshot_sidecar.is_file():
                errors.append(
                    "expected snapshot sha256 sidecar is missing: %s" % snapshot_sidecar
                )
            else:
                try:
                    expected_snapshot_sha = _read_sha256_sidecar(snapshot_sidecar)
                    actual_snapshot_sha = _text_file_sha256(snapshot_path)
                except (OSError, UnicodeDecodeError, ValueError) as err:
                    # OSError: snapshot or sidecar cannot be read;
                    # UnicodeDecodeError: committed text is not valid UTF-8;
                    # ValueError: sidecar content is not a sha256 digest.
                    errors.append("snapshot sha256 cannot be verified: %s" % err)
                else:
                    if actual_snapshot_sha != expected_snapshot_sha:
                        errors.append(
                            "snapshot sha256 %r does not match sidecar %r"
                            % (actual_snapshot_sha, expected_snapshot_sha)
                        )
            try:
                snapshot = _read_json(snapshot_path)
            except (OSError, json.JSONDecodeError, ValueError) as err:
                # OSError: snapshot cannot be read; JSONDecodeError: invalid
                # JSON; ValueError: top-level JSON is not an object.
                errors.append("snapshot cannot be loaded: %s" % err)
            else:
                errors.extend(
                    "snapshot: %s" % error
                    for error in validate_java_rust_smoke(
                        snapshot, expected_mode="java-rust-smoke"
                    )
                )
                if schema is not None:
                    errors.extend(
                        "snapshot schema: %s" % error
                        for error in _validate_payload_with_schema(snapshot, schema)
                    )
                if snapshot.get("source_mapping_sha256") != live.get(
                    "source_mapping_sha256"
                ):
                    errors.append(
                        "snapshot source_mapping_sha256 %r does not match live %r"
                        % (
                            snapshot.get("source_mapping_sha256"),
                            live.get("source_mapping_sha256"),
                        )
                    )
    return {
        "ok": not errors,
        "errors": errors,
        "schema_version": live["schema_version"],
        "source_mapping_sha256": live["source_mapping_sha256"],
        "snapshot_present": snapshot_present,
        "snapshot_enforced": mode == "java-rust-smoke",
        "snapshot_path": _JAVA_RUST_SMOKE_SNAPSHOT,
        "mode": mode,
    }


def _alignment_render_paths(mapping: Mapping[str, Any]) -> List[RenderPath]:
    """
    Return all C-family render paths required by the alignment pilot.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :return: C and C++ render paths, including C++ paths that reuse C
        expression templates.
    :rtype: List[RenderPath]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> len(_alignment_render_paths(mapping)) >= 4
        True
    """
    return _render_paths_for_mode("c-smoke", mapping) + _render_paths_for_mode(
        "cpp-smoke", mapping
    )


def _c_family_smoke_facts(
    mode: str,
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
) -> _JSON_OBJECT:
    """
    Build deterministic C-family smoke facts without native compilation.

    The digest produced from this payload is the schema-level smoke-fact input
    for the C/C++ alignment snapshot. Live ``c-smoke`` and ``cpp-smoke`` runs
    may still record compiler outcomes under ``results/local/``, but this
    helper stays toolchain-independent so ``--check`` remains usable on hosts
    without a native C or C++ compiler.

    :param mode: Smoke mode, either ``"c-smoke"`` or ``"cpp-smoke"``.
    :type mode: str
    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path.
    :type mapping_path: Union[str, pathlib.Path], optional
    :return: Deterministic smoke-fact payload.
    :rtype: Dict[str, Any]

    Example::

        >>> facts = _c_family_smoke_facts('c-smoke')
        >>> facts['mode']
        'c-smoke-facts'
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    render_paths = _render_paths_for_mode(mode, mapping)
    cases = []
    for render_path in render_paths:
        for case in _risk_cases():
            rendered = _render_case_expression(case, render_path)
            cases.append(
                {
                    "case_id": "%s:%s" % (render_path.path_id, case.case_id),
                    "semantic_case_id": case.case_id,
                    "operator": case.operator,
                    "fcstm_expression": case.fcstm_expression,
                    "render_path": render_path.path_id,
                    "render_expression": rendered,
                    "mapping_sources": list(render_path.mapping_sources),
                    "expects_undefined_behavior": case.expects_undefined_behavior,
                }
            )
    return {
        "schema_version": 1,
        "mode": "%s-facts" % mode,
        "source_mapping_sha256": mapping.get("mapping_sha256", ""),
        "render_paths": [
            {
                "path_id": path.path_id,
                "language": path.language,
                "compile_language": path.compile_language,
                "lang_style": path.lang_style,
                "expression_core_language": path.expression_core_language,
                "mapping_sources": list(path.mapping_sources),
                "template_name": path.template_name,
                "wrapper_language": path.wrapper_language,
            }
            for path in render_paths
        ],
        "cases": cases,
    }


def _render_contract_expression(
    expr_text: str, render_path: RenderPath
) -> _JSON_OBJECT:
    """
    Render one alignment expression for a C-family render path.

    :param expr_text: FCSTM expression text.
    :type expr_text: str
    :param render_path: Render path used for target-language output.
    :type render_path: RenderPath
    :return: Render result with ``status`` and either ``rendered`` or error
        metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> path = _render_paths_for_mode('c-smoke', mapping)[0]
        >>> _render_contract_expression('A + B', path)['status']
        'rendered'
    """
    from pyfcstm.render.expr import fn_expr_render
    from pyfcstm.utils import to_c_identifier

    env = add_settings_for_env(jinja2.Environment())
    env.filters["to_c_identifier"] = to_c_identifier
    env.globals["to_c_identifier"] = to_c_identifier
    render = partial(
        fn_expr_render, templates=dict(render_path.render_templates), env=env
    )
    env.globals["expr_render"] = render
    env.filters["expr_render"] = render
    try:
        expr = parse_expr_from_string(expr_text, mode="generic")
        rendered = render(node=expr.to_ast_node())
    except GrammarParseError as err:
        # GrammarParseError: current FCSTM grammar rejects this expression
        # shape; the alignment snapshot records that as an unsupported contract row.
        return {
            "status": "parse_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    except (ValueError, TypeError) as err:
        # ValueError: expression conversion rejected the parsed tree; TypeError:
        # renderer/template helpers rejected the AST. Both are alignment facts.
        return {
            "status": "render_failed",
            "error_type": type(err).__name__,
            "error": str(err),
        }
    return {
        "status": "rendered",
        "rendered": rendered,
        "ast_type": type(expr.to_ast_node()).__name__,
    }


def _obligation(kind: str, predicate: str, trigger: str, evidence: str) -> _JSON_OBJECT:
    """
    Build one alignment obligation row.

    :param kind: Stable obligation kind.
    :type kind: str
    :param predicate: Z3-oriented predicate or structured-text condition.
    :type predicate: str
    :param trigger: Scenario that requires the obligation.
    :type trigger: str
    :param evidence: Evidence note for the obligation.
    :type evidence: str
    :return: JSON-compatible obligation.
    :rtype: Dict[str, Any]

    Example::

        >>> _obligation('divisor_nonzero', 'B != 0', 'division', 'C rule')['kind']
        'divisor_nonzero'
    """
    return {
        "kind": kind,
        "predicate": predicate,
        "trigger": trigger,
        "evidence": evidence,
    }


def _counterexample(
    case_id: str,
    values: Mapping[str, Any],
    expected_issue: str,
    reproduction: str,
) -> _JSON_OBJECT:
    """
    Build one compact counterexample row.

    :param case_id: Stable counterexample identifier.
    :type case_id: str
    :param values: Input values for the example.
    :type values: Mapping[str, Any]
    :param expected_issue: Issue demonstrated by the example.
    :type expected_issue: str
    :param reproduction: Short reproduction expression or command.
    :type reproduction: str
    :return: JSON-compatible counterexample.
    :rtype: Dict[str, Any]

    Example::

        >>> _counterexample('div0', {'B': 0}, 'division by zero', 'A / B')['case_id']
        'div0'
    """
    return {
        "case_id": case_id,
        "values": dict(values),
        "expected_issue": expected_issue,
        "reproduction": reproduction,
    }


def _c_cpp_alignment_cases() -> List[_JSON_OBJECT]:
    """
    Return semantic cases covered by the C/C++ alignment pilot.

    :return: Semantic case definitions.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> any(case['operator'] == '~' for case in _c_cpp_alignment_cases())
        True
    """
    return [
        {
            "semantic_case_id": "add",
            "operator": "+",
            "operator_family": "binary_arithmetic",
            "fcstm_expression": "A + B",
        },
        {
            "semantic_case_id": "subtract",
            "operator": "-",
            "operator_family": "binary_arithmetic",
            "fcstm_expression": "A - B",
        },
        {
            "semantic_case_id": "multiply",
            "operator": "*",
            "operator_family": "binary_arithmetic",
            "fcstm_expression": "A * B",
        },
        {
            "semantic_case_id": "divide",
            "operator": "/",
            "operator_family": "binary_arithmetic",
            "fcstm_expression": "A / B",
        },
        {
            "semantic_case_id": "modulo",
            "operator": "%",
            "operator_family": "binary_arithmetic",
            "fcstm_expression": "A % B",
        },
        {
            "semantic_case_id": "unary_minus",
            "operator": "unary-",
            "operator_family": "unary_arithmetic",
            "fcstm_expression": "-A",
        },
        {
            "semantic_case_id": "bitwise_not",
            "operator": "~",
            "operator_family": "bitwise",
            "fcstm_expression": "~A",
        },
        {
            "semantic_case_id": "bitwise_and",
            "operator": "&",
            "operator_family": "bitwise",
            "fcstm_expression": "A & B",
        },
        {
            "semantic_case_id": "bitwise_or",
            "operator": "|",
            "operator_family": "bitwise",
            "fcstm_expression": "A | B",
        },
        {
            "semantic_case_id": "bitwise_xor",
            "operator": "^",
            "operator_family": "bitwise",
            "fcstm_expression": "A ^ B",
        },
        {
            "semantic_case_id": "shift_left",
            "operator": "<<",
            "operator_family": "shift",
            "fcstm_expression": "A << B",
        },
        {
            "semantic_case_id": "shift_right",
            "operator": ">>",
            "operator_family": "shift",
            "fcstm_expression": "A >> B",
        },
        {
            "semantic_case_id": "less_than",
            "operator": "<",
            "operator_family": "comparison",
            "fcstm_expression": "A < B",
        },
        {
            "semantic_case_id": "less_equal",
            "operator": "<=",
            "operator_family": "comparison",
            "fcstm_expression": "A <= B",
        },
        {
            "semantic_case_id": "greater_than",
            "operator": ">",
            "operator_family": "comparison",
            "fcstm_expression": "A > B",
        },
        {
            "semantic_case_id": "greater_equal",
            "operator": ">=",
            "operator_family": "comparison",
            "fcstm_expression": "A >= B",
        },
        {
            "semantic_case_id": "equal",
            "operator": "==",
            "operator_family": "comparison",
            "fcstm_expression": "A == B",
        },
        {
            "semantic_case_id": "not_equal",
            "operator": "!=",
            "operator_family": "comparison",
            "fcstm_expression": "A != B",
        },
        {
            "semantic_case_id": "pow",
            "operator": "pow",
            "operator_family": "math",
            "fcstm_expression": "A ** B",
        },
        {
            "semantic_case_id": "round",
            "operator": "round",
            "operator_family": "math",
            "fcstm_expression": "round(A)",
        },
        {
            "semantic_case_id": "abs",
            "operator": "abs",
            "operator_family": "math",
            "fcstm_expression": "abs(A)",
        },
        {
            "semantic_case_id": "sign",
            "operator": "sign",
            "operator_family": "math",
            "fcstm_expression": "sign(A)",
        },
        {
            "semantic_case_id": "cbrt",
            "operator": "cbrt",
            "operator_family": "math",
            "fcstm_expression": "cbrt(A)",
        },
        {
            "semantic_case_id": "integer_constant",
            "operator": "integer_constant",
            "operator_family": "constant",
            "fcstm_expression": "42",
        },
        {
            "semantic_case_id": "float_constant",
            "operator": "float_constant",
            "operator_family": "constant",
            "fcstm_expression": "3.5",
        },
        {
            "semantic_case_id": "narrowing_writeback",
            "operator": "writeback",
            "operator_family": "writeback",
            "fcstm_expression": "A ** B",
        },
    ]


def _contract_common_evidence(
    render_path: RenderPath, render_result: Mapping[str, Any]
) -> List[_JSON_OBJECT]:
    """
    Build common evidence entries for one alignment row.

    :param render_path: Render path represented by the row.
    :type render_path: RenderPath
    :param render_result: Render result for the row expression.
    :type render_result: Mapping[str, Any]
    :return: Evidence entries.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> path = _render_paths_for_mode('c-smoke', mapping)[0]
        >>> bool(_contract_common_evidence(path, {'status': 'rendered'}))
        True
    """
    evidence = [
        {
            "kind": "render_mapping",
            "source": source,
            "summary": "Render path source recorded in render_mapping.json.",
        }
        for source in render_path.mapping_sources
    ]
    evidence.append(
        {
            "kind": "render_result",
            "source": render_path.path_id,
            "summary": "Expression render status is %s." % render_result.get("status"),
        }
    )
    return evidence


def _alignment_semantics_for_case(
    case: Mapping[str, str], render_path: RenderPath, render_result: Mapping[str, Any]
) -> _JSON_OBJECT:
    """
    Build semantic fields for one C/C++ alignment contract row.

    :param case: Semantic case definition.
    :type case: Mapping[str, str]
    :param render_path: Render path represented by the row.
    :type render_path: RenderPath
    :param render_result: Render result for the row expression.
    :type render_result: Mapping[str, Any]
    :return: Semantic fields merged into the contract row.
    :rtype: Dict[str, Any]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> path = _render_paths_for_mode('c-smoke', mapping)[0]
        >>> data = _alignment_semantics_for_case(_c_cpp_alignment_cases()[0], path, {'status': 'rendered'})
        >>> data['outcome']
        'exact_with_obligations'
    """
    operator_name = case["operator"]
    family = case["operator_family"]
    language_prefix = "C++" if render_path.language == "cpp" else "C"
    if render_result.get("status") != "rendered":
        return {
            "target_semantics": (
                "Current FCSTM parser or renderer rejects this expression before "
                "target-language semantics apply."
            ),
            "definedness": "unsupported_by_current_fcstm_grammar_or_renderer",
            "z3_sort": "unsupported",
            "z3_profile": "unsupported",
            "value_expr": "unsupported",
            "obligations": [],
            "outcome": "unsupported",
            "counterexamples": [
                _counterexample(
                    "%s:%s:parse" % (render_path.path_id, case["semantic_case_id"]),
                    {"expression": case["fcstm_expression"]},
                    str(render_result.get("error_type", "render_failed")),
                    case["fcstm_expression"],
                )
            ],
        }

    if family == "comparison":
        return {
            "target_semantics": "%s relational comparison over promoted operands."
            % language_prefix,
            "definedness": "defined_if_operand_evaluation_is_defined",
            "z3_sort": "Bool",
            "z3_profile": "signed-fixed-width-candidate:int64",
            "value_expr": "signed_bv_compare(%s, A, B)" % operator_name,
            "obligations": [],
            "outcome": "exact",
            "counterexamples": [],
        }
    if family == "constant":
        z3_sort = "BitVec(64)" if operator_name == "integer_constant" else "FP64"
        z3_profile = (
            "signed-fixed-width-candidate:int64"
            if operator_name == "integer_constant"
            else "float-double"
        )
        return {
            "target_semantics": "%s literal rendering for %s."
            % (language_prefix, operator_name),
            "definedness": "defined",
            "z3_sort": z3_sort,
            "z3_profile": z3_profile,
            "value_expr": "literal(%s)" % case["fcstm_expression"],
            "obligations": [],
            "outcome": "exact",
            "counterexamples": [],
        }
    if family == "writeback":
        return {
            "target_semantics": (
                "%s assignment of an expression result back into a generated "
                "signed integer storage slot."
            )
            % language_prefix,
            "definedness": "defined_if_source_expression_and_conversion_are_defined",
            "z3_sort": "BitVec(64)",
            "z3_profile": "promotion-and-writeback:int64",
            "value_expr": "writeback_int64(value_expr(A ** B))",
            "obligations": [
                _obligation(
                    "source_expression_defined",
                    "all source expression obligations hold",
                    "writeback source evaluation",
                    "The alignment contract composes source expression obligations before writeback.",
                ),
                _obligation(
                    "representable_in_target_width",
                    "INT64_MIN <= mathematical_result <= INT64_MAX",
                    "integer writeback",
                    "C/C++ conversion to a signed integer target must not rely on out-of-range behavior.",
                ),
            ],
            "outcome": "exact_with_obligations",
            "counterexamples": [
                _counterexample(
                    "%s:writeback:pow-overflow" % render_path.path_id,
                    {"A": 2, "B": 63, "target": "int64"},
                    "mathematical result is outside signed 64-bit writeback range",
                    "A ** B",
                )
            ],
        }
    if operator_name == "sign":
        return {
            "target_semantics": (
                "%s render path currently emits a sign function call but C and "
                "standard C++ do not provide a portable unary sign math function."
            )
            % language_prefix,
            "definedness": "not_defined_by_portable_c_family_library",
            "z3_sort": "unsupported",
            "z3_profile": "math-library-availability",
            "value_expr": "unsupported",
            "obligations": [],
            "outcome": "compile_failed",
            "counterexamples": [
                _counterexample(
                    "%s:sign:compile" % render_path.path_id,
                    {"A": -9},
                    "portable C/C++ sign function is unavailable",
                    str(render_result.get("rendered", "sign(A)")),
                )
            ],
        }
    if operator_name == "abs":
        return {
            "target_semantics": "%s absolute-value call selected by the render path."
            % language_prefix,
            "definedness": "profile_dependent_overload_and_min_value",
            "z3_sort": "BitVec(64)",
            "z3_profile": "math-overload-and-writeback:int64",
            "value_expr": "if signed(A) < 0 then -A else A",
            "obligations": [
                _obligation(
                    "abs_overload_matches_operand_width",
                    "selected abs overload preserves the operand width",
                    "math overload resolution",
                    "C render paths may emit abs(A), which is not width-neutral for int64 operands.",
                ),
                _obligation(
                    "no_abs_min",
                    "A != INT_MIN(width)",
                    "absolute value of signed minimum",
                    "The negated signed minimum is not representable in the same signed width.",
                ),
            ],
            "outcome": "profile_dependent",
            "counterexamples": [
                _counterexample(
                    "%s:abs:min" % render_path.path_id,
                    {"A": -128, "width": 8},
                    "abs(INT_MIN) is not representable in the same signed width",
                    str(render_result.get("rendered", "abs(A)")),
                )
            ],
        }
    if operator_name in {"pow", "round", "cbrt"}:
        function_name = {"pow": "pow", "round": "round", "cbrt": "cbrt"}[operator_name]
        return {
            "target_semantics": "%s math-library %s evaluation."
            % (language_prefix, function_name),
            "definedness": "defined_if_math_result_is_supported_and_writeback_is_defined",
            "z3_sort": "FP64",
            "z3_profile": "float-double-math",
            "value_expr": "%s_fp64(%s)" % (function_name, case["fcstm_expression"]),
            "obligations": [
                _obligation(
                    "math_function_available",
                    "%s is available in the selected language standard/library"
                    % function_name,
                    "math function call",
                    "C-family smoke probes record compile/link facts for math functions.",
                ),
                _obligation(
                    "finite_float_result",
                    "isFinite(result)",
                    "floating-point math result",
                    "Later writeback or solver profiles must not silently collapse NaN or infinity.",
                ),
            ],
            "outcome": "exact_with_obligations",
            "counterexamples": [],
        }
    if operator_name in {"+", "-", "*"} or operator_name == "unary-":
        predicate = (
            "no_signed_overflow(%s)" % case["fcstm_expression"]
            if operator_name != "unary-"
            else "A != INT_MIN(width)"
        )
        return {
            "target_semantics": "%s signed integer arithmetic over promoted operands."
            % language_prefix,
            "definedness": "defined_if_no_signed_overflow",
            "z3_sort": "BitVec(64)",
            "z3_profile": "signed-fixed-width-candidate:int64",
            "value_expr": "signed_bv_%s(%s)"
            % (case["semantic_case_id"], case["fcstm_expression"]),
            "obligations": [
                _obligation(
                    "no_signed_overflow",
                    predicate,
                    "signed arithmetic",
                    "BitVec wrap is only a candidate value; C/C++ signed overflow is not defined behavior.",
                )
            ],
            "outcome": "exact_with_obligations",
            "counterexamples": [
                _counterexample(
                    "%s:%s:overflow" % (render_path.path_id, case["semantic_case_id"]),
                    {"A": 127, "B": 1, "width": 8},
                    "signed overflow would be required to match BitVec wrap",
                    case["fcstm_expression"],
                )
            ],
        }
    if operator_name in {"/", "%"}:
        return {
            "target_semantics": "%s signed integer %s over promoted operands."
            % (language_prefix, "division" if operator_name == "/" else "remainder"),
            "definedness": "defined_if_divisor_nonzero_and_min_div_minus_one_absent",
            "z3_sort": "BitVec(64)",
            "z3_profile": "signed-fixed-width-candidate:int64",
            "value_expr": ("bvsdiv(A, B)" if operator_name == "/" else "bvsrem(A, B)"),
            "obligations": [
                _obligation(
                    "divisor_nonzero",
                    "B != 0",
                    "division or remainder",
                    "Division by zero is not a defined C/C++ integer operation.",
                ),
                _obligation(
                    "no_min_div_minus_one",
                    "not (A == INT_MIN(width) and B == -1)",
                    "signed division or remainder",
                    "The signed minimum divided by -1 is not representable.",
                ),
            ],
            "outcome": "exact_with_obligations",
            "counterexamples": [
                _counterexample(
                    "%s:%s:div-zero" % (render_path.path_id, case["semantic_case_id"]),
                    {"A": 7, "B": 0},
                    "division by zero",
                    case["fcstm_expression"],
                ),
                _counterexample(
                    "%s:%s:min-div-minus-one"
                    % (render_path.path_id, case["semantic_case_id"]),
                    {"A": -128, "B": -1, "width": 8},
                    "signed minimum divided by -1",
                    case["fcstm_expression"],
                ),
            ],
        }
    if family == "shift":
        obligations = [
            _obligation(
                "valid_shift_count",
                "B < width",
                "shift count",
                "C/C++ shifts require a count smaller than the promoted operand width.",
            ),
            _obligation(
                "non_negative_shift_count",
                "B >= 0",
                "shift count",
                "C/C++ shifts do not define negative shift counts.",
            ),
        ]
        if operator_name == "<<":
            obligations.append(
                _obligation(
                    "no_signed_left_shift_ub",
                    "A >= 0 and left_shift_result_representable(A, B, width)",
                    "signed left shift",
                    "Signed left shift has additional definedness constraints beyond BitVec shift.",
                )
            )
            outcome = "exact_with_obligations"
            value_expr = "bvshl(A, B)"
            counterexamples = [
                _counterexample(
                    "%s:shift-left:negative" % render_path.path_id,
                    {"A": -1, "B": 1, "width": 8},
                    "signed left shift of a negative value is not a portable defined operation",
                    case["fcstm_expression"],
                )
            ]
        else:
            obligations.append(
                _obligation(
                    "signed_right_shift_profile",
                    "profile selects arithmetic or logical right shift for negative lhs",
                    "signed right shift",
                    "Right shift of a negative signed value is implementation-defined/profile-dependent.",
                )
            )
            outcome = "profile_dependent"
            value_expr = "bvashr(A, B) under arithmetic-shift profile"
            counterexamples = [
                _counterexample(
                    "%s:shift-right:negative" % render_path.path_id,
                    {"A": -8, "B": 1, "width": 8},
                    "negative signed right shift depends on implementation profile",
                    case["fcstm_expression"],
                )
            ]
        return {
            "target_semantics": "%s signed integer shift." % language_prefix,
            "definedness": "defined_if_shift_obligations_hold",
            "z3_sort": "BitVec(64)",
            "z3_profile": "signed-fixed-width-candidate:int64",
            "value_expr": value_expr,
            "obligations": obligations,
            "outcome": outcome,
            "counterexamples": counterexamples,
        }
    if family == "bitwise":
        return {
            "target_semantics": "%s signed integer bitwise operation."
            % language_prefix,
            "definedness": "profile_dependent_for_negative_signed_representation",
            "z3_sort": "BitVec(64)",
            "z3_profile": "signed-fixed-width-candidate:int64",
            "value_expr": "bv%s(A, B)"
            % {"&": "and", "|": "or", "^": "xor"}.get(operator_name, "not"),
            "obligations": [
                _obligation(
                    "two_complement_representation_profile",
                    "profile fixes signed representation as two's complement",
                    "signed bitwise operation",
                    "BitVec bitwise operations model representation bits, so signed representation is part of the profile.",
                )
            ],
            "outcome": "profile_dependent",
            "counterexamples": [
                _counterexample(
                    "%s:%s:negative-representation"
                    % (render_path.path_id, case["semantic_case_id"]),
                    {"A": -1, "B": 1},
                    "negative signed operand requires an explicit representation profile",
                    case["fcstm_expression"],
                )
            ],
        }
    return {
        "target_semantics": "%s target semantics not classified yet." % language_prefix,
        "definedness": "unsupported",
        "z3_sort": "unsupported",
        "z3_profile": "unsupported",
        "value_expr": "unsupported",
        "obligations": [],
        "outcome": "unsupported",
        "counterexamples": [
            _counterexample(
                "%s:%s:unclassified" % (render_path.path_id, case["semantic_case_id"]),
                {},
                "alignment case is not classified",
                case["fcstm_expression"],
            )
        ],
    }


def _build_c_cpp_alignment_contracts(mapping: Mapping[str, Any]) -> List[_JSON_OBJECT]:
    """
    Build C/C++ alignment contract rows from mapping render paths.

    :param mapping: Render-mapping snapshot.
    :type mapping: Mapping[str, Any]
    :return: Alignment contract rows.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> mapping = _load_render_mapping(Path('.').resolve(), _DEFAULT_MAPPING_PATH)
        >>> contracts = _build_c_cpp_alignment_contracts(mapping)
        >>> bool(contracts)
        True
    """
    contracts = []
    for render_path in _alignment_render_paths(mapping):
        for case in _c_cpp_alignment_cases():
            render_result = _render_contract_expression(
                case["fcstm_expression"], render_path
            )
            semantics = _alignment_semantics_for_case(case, render_path, render_result)
            rendered = render_result.get("rendered")
            contracts.append(
                {
                    "contract_id": "%s:%s"
                    % (render_path.path_id, case["semantic_case_id"]),
                    "semantic_case_id": case["semantic_case_id"],
                    "render_path": render_path.path_id,
                    "language": render_path.language,
                    "compile_language": render_path.compile_language,
                    "mapping_sources": list(render_path.mapping_sources),
                    "operator": case["operator"],
                    "operator_family": case["operator_family"],
                    "fcstm_expression": case["fcstm_expression"],
                    "render_expression": rendered if isinstance(rendered, str) else "",
                    "render_status": render_result.get("status", "unknown"),
                    "target_semantics": semantics["target_semantics"],
                    "definedness": semantics["definedness"],
                    "z3_sort": semantics["z3_sort"],
                    "z3_profile": semantics["z3_profile"],
                    "value_expr": semantics["value_expr"],
                    "obligations": semantics["obligations"],
                    "outcome": semantics["outcome"],
                    "evidence": _contract_common_evidence(render_path, render_result)
                    + [
                        {
                            "kind": "contract_semantics",
                            "source": case["semantic_case_id"],
                            "summary": semantics["target_semantics"],
                        }
                    ],
                    "counterexamples": semantics["counterexamples"],
                }
            )
    return contracts


def _load_python_z3_baseline_snapshot(repo_root: Path) -> _JSON_OBJECT:
    """
    Load the committed Python/Z3 baseline snapshot.

    :param repo_root: Repository root.
    :type repo_root: pathlib.Path
    :return: Parsed Python/Z3 baseline snapshot.
    :rtype: Dict[str, Any]

    Example::

        >>> baseline = _load_python_z3_baseline_snapshot(Path('.').resolve())
        >>> baseline['mode']
        'python-z3-baseline'
    """
    return _read_json(repo_root / _PYTHON_Z3_BASELINE_SNAPSHOT)


def build_c_cpp_z3_alignment(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
) -> _JSON_OBJECT:
    """
    Build the C/C++ to Z3 alignment contract snapshot.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path, defaults to the committed
        R0 snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :return: JSON-compatible C/C++ alignment payload.
    :rtype: Dict[str, Any]

    Example::

        >>> alignment = build_c_cpp_z3_alignment('.')
        >>> alignment['mode']
        'c-cpp-z3-alignment'
    """
    root = _as_repo_path(repo_root)
    mapping_file = _resolve_mapping_path(root, mapping_path)
    mapping = _load_render_mapping(root, mapping_file)
    mapping_sha = mapping.get("mapping_sha256")
    if not isinstance(mapping_sha, str):
        mapping_sha = ""
    python_baseline = _load_python_z3_baseline_snapshot(root)
    python_baseline_sha = _payload_sha256(_baseline_comparison_payload(python_baseline))
    c_facts = _c_family_smoke_facts("c-smoke", root, mapping_file)
    cpp_facts = _c_family_smoke_facts("cpp-smoke", root, mapping_file)
    contracts = _build_c_cpp_alignment_contracts(mapping)
    return {
        "schema_version": 1,
        "mode": "c-cpp-z3-alignment",
        "languages": ["c", "cpp"],
        "source_mapping_sha256": mapping_sha,
        "render_mapping_sha256": mapping_sha,
        "python_z3_baseline_sha256": python_baseline_sha,
        "c_smoke_facts_sha256": _payload_sha256(c_facts),
        "cpp_smoke_facts_sha256": _payload_sha256(cpp_facts),
        "generator": {
            "tool": "tools/numeric_render_probe.py",
            "research_path": _RESEARCH_PATH,
            "source_commit": _git_commit(root),
            "source_commit_policy": "Best-effort commit at generation time; mapping, baseline and smoke fact digests are the stable comparison keys.",
            "determinism": "No native compiler output, wall-clock timestamp or solver model value is stored in the committed alignment snapshot.",
        },
        "repository": {
            "root": ".",
            "render_mapping_snapshot": mapping_file.relative_to(root).as_posix(),
            "python_z3_baseline_snapshot": _PYTHON_Z3_BASELINE_SNAPSHOT,
            "schema_path": _C_CPP_Z3_ALIGNMENT_SCHEMA,
        },
        "contract_fields": {
            "core_triple": ["value_expr", "obligations", "outcome"],
            "required_fields": [
                "render_path",
                "operator",
                "operator_family",
                "fcstm_expression",
                "target_semantics",
                "definedness",
                "z3_sort",
                "z3_profile",
                "value_expr",
                "obligations",
                "outcome",
                "evidence",
            ],
            "outcome_enum": sorted(_C_CPP_ALIGNMENT_OUTCOMES),
            "shift_obligation_kinds": sorted(
                _C_CPP_ALIGNMENT_REQUIRED_SHIFT_OBLIGATIONS
            ),
        },
        "render_paths": [
            {
                "path_id": path.path_id,
                "language": path.language,
                "compile_language": path.compile_language,
                "lang_style": path.lang_style,
                "expression_core_language": path.expression_core_language,
                "mapping_sources": list(path.mapping_sources),
                "template_name": path.template_name,
                "wrapper_language": path.wrapper_language,
            }
            for path in _alignment_render_paths(mapping)
        ],
        "coverage": {
            "operators": sorted({contract["operator"] for contract in contracts}),
            "operator_families": sorted(
                {contract["operator_family"] for contract in contracts}
            ),
            "render_paths": sorted({contract["render_path"] for contract in contracts}),
            "note": "Each semantic case is expanded across all C-family render paths; unsupported parser/render cases remain explicit contract rows.",
        },
        "contracts": contracts,
        "representative_notes": [
            {
                "topic": "bitvec-is-candidate-not-definedness",
                "summary": "BitVec expressions describe candidate values only; C/C++ signed overflow, invalid shifts and division traps stay in obligations or non-exact outcomes.",
            },
            {
                "topic": "cxx-render-path-split",
                "summary": "The snapshot keeps builtin _CPP_STYLE separate from C++ templates that reuse C expression templates via base_lang: c.",
            },
            {
                "topic": "toolchain-independent-check",
                "summary": "The committed snapshot uses deterministic render and smoke facts; live native smoke output belongs in results/local/.",
            },
        ],
    }


def _validate_alignment_obligation(
    obligation: Mapping[str, Any], path: str
) -> List[str]:
    """
    Validate one C/C++ alignment obligation row.

    :param obligation: Obligation payload.
    :type obligation: Mapping[str, Any]
    :param path: Diagnostic path.
    :type path: str
    :return: Validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_alignment_obligation({'kind': 'x'}, 'o')[:1]
        ['o.predicate must be a non-empty string']
    """
    errors = []
    for key in ["kind", "predicate", "trigger", "evidence"]:
        if not isinstance(obligation.get(key), str) or not obligation.get(key):
            errors.append("%s.%s must be a non-empty string" % (path, key))
    return errors


def validate_c_cpp_z3_alignment(payload: Mapping[str, Any]) -> List[str]:
    """
    Validate the C/C++ to Z3 alignment contract.

    :param payload: Alignment payload.
    :type payload: Mapping[str, Any]
    :return: Human-readable diagnostics.
    :rtype: List[str]

    Example::

        >>> validate_c_cpp_z3_alignment({'schema_version': 1})[:2]
        ['mode must be c-cpp-z3-alignment', 'languages must be [\"c\", \"cpp\"]']
    """
    errors: List[str] = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if payload.get("mode") != "c-cpp-z3-alignment":
        errors.append("mode must be c-cpp-z3-alignment")
    if payload.get("languages") != ["c", "cpp"]:
        errors.append('languages must be ["c", "cpp"]')
    for key in [
        "source_mapping_sha256",
        "render_mapping_sha256",
        "python_z3_baseline_sha256",
        "c_smoke_facts_sha256",
        "cpp_smoke_facts_sha256",
    ]:
        value = payload.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            errors.append("%s must be a lowercase 64-character sha256 hex string" % key)
    if payload.get("source_mapping_sha256") != payload.get("render_mapping_sha256"):
        errors.append("source_mapping_sha256 and render_mapping_sha256 must match")

    fields = payload.get("contract_fields")
    if not isinstance(fields, Mapping):
        errors.append("contract_fields must be a mapping")
    else:
        if fields.get("core_triple") != ["value_expr", "obligations", "outcome"]:
            errors.append("contract_fields.core_triple must name the core triple")
        if set(fields.get("outcome_enum", [])) != _C_CPP_ALIGNMENT_OUTCOMES:
            errors.append(
                "contract_fields.outcome_enum must match the closed outcome enum"
            )
        if set(fields.get("shift_obligation_kinds", [])) != (
            _C_CPP_ALIGNMENT_REQUIRED_SHIFT_OBLIGATIONS
        ):
            errors.append(
                "contract_fields.shift_obligation_kinds must match required shift obligations"
            )

    render_paths = payload.get("render_paths")
    if not isinstance(render_paths, list) or not render_paths:
        errors.append("render_paths must be a non-empty array")
    else:
        render_path_ids = {
            item.get("path_id") for item in render_paths if isinstance(item, Mapping)
        }
        for path_id in _C_CPP_ALIGNMENT_RENDER_PATHS:
            if path_id not in render_path_ids:
                errors.append("render_paths missing %s" % path_id)

    contracts = payload.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        errors.append("contracts must be a non-empty array")
        return errors

    required_contract_keys = {
        "contract_id",
        "semantic_case_id",
        "render_path",
        "operator",
        "operator_family",
        "fcstm_expression",
        "render_expression",
        "render_status",
        "target_semantics",
        "definedness",
        "z3_sort",
        "z3_profile",
        "value_expr",
        "obligations",
        "outcome",
        "evidence",
        "counterexamples",
    }
    expected_cases = {
        str(case["semantic_case_id"]): {
            "operator": str(case["operator"]),
            "operator_family": str(case["operator_family"]),
            "fcstm_expression": str(case["fcstm_expression"]),
        }
        for case in _c_cpp_alignment_cases()
    }
    expected_contract_ids = {
        "%s:%s" % (render_path, semantic_case_id)
        for render_path in _C_CPP_ALIGNMENT_RENDER_PATHS
        for semantic_case_id in expected_cases
    }
    seen_contract_ids: Dict[str, str] = {}
    seen_contract_pairs: Dict[Tuple[str, str], str] = {}
    operators = set()
    families = set()
    contract_render_paths = set()
    for index, contract in enumerate(contracts):
        path = "contracts[%d]" % index
        if not isinstance(contract, Mapping):
            errors.append("%s must be a mapping" % path)
            continue
        missing = sorted(required_contract_keys - set(contract))
        if missing:
            errors.append("%s missing required key %s" % (path, missing[0]))
            continue
        contract_id = contract.get("contract_id")
        semantic_case_id = contract.get("semantic_case_id")
        render_path = contract.get("render_path")
        operator_name = contract.get("operator")
        operators.add(operator_name)
        families.add(contract.get("operator_family"))
        contract_render_paths.add(render_path)
        if isinstance(contract_id, str):
            previous_path = seen_contract_ids.get(contract_id)
            if previous_path is not None:
                errors.append(
                    "%s.contract_id duplicates %s from %s"
                    % (path, contract_id, previous_path)
                )
            else:
                seen_contract_ids[contract_id] = path
        if isinstance(render_path, str) and isinstance(semantic_case_id, str):
            pair_key = (render_path, semantic_case_id)
            previous_path = seen_contract_pairs.get(pair_key)
            if previous_path is not None:
                errors.append(
                    "%s duplicates render_path/semantic_case_id %s:%s from %s"
                    % (path, render_path, semantic_case_id, previous_path)
                )
            else:
                seen_contract_pairs[pair_key] = path
            expected_contract_id = "%s:%s" % pair_key
            if contract_id != expected_contract_id:
                errors.append(
                    "%s.contract_id must equal %s" % (path, expected_contract_id)
                )
        if render_path not in _C_CPP_ALIGNMENT_RENDER_PATHS:
            errors.append("%s.render_path is not a required C-family path" % path)
        expected_case = expected_cases.get(str(semantic_case_id))
        if expected_case is None:
            errors.append("%s.semantic_case_id is not a required alignment case" % path)
        else:
            for key, expected_value in expected_case.items():
                if contract.get(key) != expected_value:
                    errors.append(
                        "%s.%s must be %r for semantic case %s"
                        % (path, key, expected_value, semantic_case_id)
                    )
        if contract.get("outcome") not in _C_CPP_ALIGNMENT_OUTCOMES:
            errors.append(
                "%s.outcome has invalid value %r" % (path, contract.get("outcome"))
            )
        for key in [
            "contract_id",
            "semantic_case_id",
            "render_path",
            "operator",
            "operator_family",
            "fcstm_expression",
            "target_semantics",
            "definedness",
            "z3_sort",
            "z3_profile",
            "value_expr",
        ]:
            if not isinstance(contract.get(key), str) or not contract.get(key):
                errors.append("%s.%s must be a non-empty string" % (path, key))
        obligations = contract.get("obligations")
        obligation_kinds = set()
        if not isinstance(obligations, list):
            errors.append("%s.obligations must be an array" % path)
        else:
            for obligation_index, obligation in enumerate(obligations):
                if not isinstance(obligation, Mapping):
                    errors.append(
                        "%s.obligations[%d] must be a mapping"
                        % (path, obligation_index)
                    )
                    continue
                obligation_kinds.add(obligation.get("kind"))
                errors.extend(
                    _validate_alignment_obligation(
                        obligation, "%s.obligations[%d]" % (path, obligation_index)
                    )
                )
        required_shift_kinds = set()
        if operator_name == "<<":
            required_shift_kinds = {
                "valid_shift_count",
                "non_negative_shift_count",
                "no_signed_left_shift_ub",
            }
        elif operator_name == ">>":
            required_shift_kinds = {
                "valid_shift_count",
                "non_negative_shift_count",
                "signed_right_shift_profile",
            }
        if required_shift_kinds and not required_shift_kinds <= obligation_kinds:
            missing = sorted(required_shift_kinds - obligation_kinds)
            errors.append(
                "%s shift obligations missing: %s" % (path, ", ".join(missing))
            )
        evidence = contract.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append("%s.evidence must be a non-empty array" % path)
        counterexamples = contract.get("counterexamples")
        if not isinstance(counterexamples, list):
            errors.append("%s.counterexamples must be an array" % path)
        elif (
            contract.get("outcome")
            in {
                "profile_dependent",
                "unsupported",
                "compile_failed",
                "runtime_trap",
                "ub",
            }
            and not counterexamples
        ):
            errors.append(
                "%s.%s outcome must include a counterexample"
                % (path, contract.get("outcome"))
            )

    required_operators = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "unary-",
        "~",
        "&",
        "|",
        "^",
        "<<",
        ">>",
        "<",
        "<=",
        ">",
        ">=",
        "==",
        "!=",
        "pow",
        "round",
        "abs",
        "sign",
        "cbrt",
        "integer_constant",
        "float_constant",
        "writeback",
    }
    for operator_name in sorted(required_operators - operators):
        errors.append("contracts missing operator %s" % operator_name)
    for family_name in [
        "binary_arithmetic",
        "unary_arithmetic",
        "bitwise",
        "shift",
        "comparison",
        "math",
        "constant",
        "writeback",
    ]:
        if family_name not in families:
            errors.append("contracts missing operator_family %s" % family_name)
    for path_id in _C_CPP_ALIGNMENT_RENDER_PATHS:
        if path_id not in contract_render_paths:
            errors.append("contracts missing render_path %s" % path_id)
    missing_contract_ids = sorted(expected_contract_ids - set(seen_contract_ids))
    extra_contract_ids = sorted(set(seen_contract_ids) - expected_contract_ids)
    for contract_id in missing_contract_ids:
        errors.append("contracts missing required contract_id %s" % contract_id)
    for contract_id in extra_contract_ids:
        errors.append("contracts contain unexpected contract_id %s" % contract_id)
    return errors


def _c_cpp_alignment_comparison_payload(payload: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Return a deterministic comparison view of an alignment payload.

    :param payload: Alignment payload.
    :type payload: Mapping[str, Any]
    :return: Payload with volatile provenance fields normalized.
    :rtype: Dict[str, Any]

    Example::

        >>> _c_cpp_alignment_comparison_payload({'generator': {'source_commit': 'x'}})['generator']['source_commit']
        '<ignored>'
    """
    comparable = json.loads(_stable_json(payload))
    generator = comparable.get("generator")
    if isinstance(generator, dict):
        generator["source_commit"] = "<ignored>"
    repository = comparable.get("repository")
    if isinstance(repository, dict):
        repository["render_mapping_snapshot"] = _DEFAULT_MAPPING_PATH
    return comparable


def check_c_cpp_z3_alignment(
    repo_root: Union[str, Path] = ".",
    mapping_path: Union[str, Path] = _DEFAULT_MAPPING_PATH,
) -> _JSON_OBJECT:
    """
    Build and validate the committed C/C++ to Z3 alignment snapshot.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :param mapping_path: Render-mapping snapshot path checked against live drift,
        defaults to the committed R0 snapshot.
    :type mapping_path: Union[str, pathlib.Path], optional
    :return: Check result with ``ok`` and ``errors`` fields.
    :rtype: Dict[str, Any]

    Example::

        >>> result = check_c_cpp_z3_alignment('.')
        >>> isinstance(result['ok'], bool)
        True
    """
    root = _as_repo_path(repo_root)
    live = build_c_cpp_z3_alignment(root, mapping_path=mapping_path)
    errors = [
        "live alignment: %s" % error for error in validate_c_cpp_z3_alignment(live)
    ]
    live_mapping = build_render_mapping(root)
    live_mapping_sha = live_mapping.get("mapping_sha256")
    if live_mapping_sha != live.get("source_mapping_sha256"):
        errors.append(
            "render_mapping snapshot drift: snapshot %r does not match live %r"
            % (live.get("source_mapping_sha256"), live_mapping_sha)
        )
    schema = None
    schema_path = root / _C_CPP_Z3_ALIGNMENT_SCHEMA
    try:
        schema = _read_json(schema_path)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        # OSError: schema cannot be read; JSONDecodeError: invalid JSON;
        # ValueError: top-level schema JSON is not an object.
        errors.append("schema cannot be loaded: %s" % err)
    if schema is not None:
        errors.extend(
            "live schema: %s" % error
            for error in _validate_payload_with_schema(live, schema)
        )
    snapshot_path = root / _C_CPP_Z3_ALIGNMENT_SNAPSHOT
    snapshot_present = snapshot_path.is_file()
    if not snapshot_present:
        errors.append("expected snapshot is missing: %s" % snapshot_path)
    else:
        try:
            snapshot = _read_json(snapshot_path)
        except (OSError, json.JSONDecodeError, ValueError) as err:
            # OSError: snapshot cannot be read; JSONDecodeError: invalid JSON;
            # ValueError: top-level JSON is not an object.
            errors.append("snapshot cannot be loaded: %s" % err)
        else:
            errors.extend(
                "snapshot: %s" % error
                for error in validate_c_cpp_z3_alignment(snapshot)
            )
            if schema is not None:
                errors.extend(
                    "snapshot schema: %s" % error
                    for error in _validate_payload_with_schema(snapshot, schema)
                )
            snapshot_difference = _first_baseline_difference(
                _c_cpp_alignment_comparison_payload(live),
                _c_cpp_alignment_comparison_payload(snapshot),
            )
            if snapshot_difference:
                errors.append(
                    "snapshot does not match live alignment: %s" % snapshot_difference
                )
    return {
        "ok": not errors,
        "errors": errors,
        "schema_version": live["schema_version"],
        "source_mapping_sha256": live["source_mapping_sha256"],
        "python_z3_baseline_sha256": live["python_z3_baseline_sha256"],
        "c_smoke_facts_sha256": live["c_smoke_facts_sha256"],
        "cpp_smoke_facts_sha256": live["cpp_smoke_facts_sha256"],
        "snapshot_present": snapshot_present,
        "snapshot_path": _C_CPP_Z3_ALIGNMENT_SNAPSHOT,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the probe command-line argument parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> parser = _build_arg_parser()
        >>> parser.prog
        'numeric_render_probe.py'
    """
    parser = argparse.ArgumentParser(
        prog="numeric_render_probe.py",
        description="Numeric render-semantics probe entry point.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="env",
        choices=[
            "env",
            "c-smoke",
            "cpp-smoke",
            "python-z3-baseline",
            "java-smoke",
            "rust-smoke",
            "java-rust-smoke",
            "c-cpp-z3-alignment",
        ],
        help=(
            "Probe mode. Current modes are 'env', 'c-smoke', 'cpp-smoke', "
            "'python-z3-baseline', 'java-smoke', 'rust-smoke', "
            "'java-rust-smoke' and 'c-cpp-z3-alignment'; later research "
            "PRs should append modes here without replacing existing ones."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to describe, defaults to the current directory.",
    )
    parser.add_argument(
        "--mapping",
        default=_DEFAULT_MAPPING_PATH,
        help=(
            "Render mapping JSON path for smoke modes, defaults to "
            + _DEFAULT_MAPPING_PATH
            + "."
        ),
    )
    parser.add_argument(
        "--work-dir",
        help="Optional directory for smoke compile artifacts.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Per-command timeout in seconds for smoke modes.",
    )
    parser.add_argument(
        "--output",
        help="Destination JSON path. When omitted, JSON is printed to stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the selected probe contract instead of writing the full payload.",
    )
    return parser


def _write_or_print(payload: Mapping[str, Any], output: Optional[str]) -> None:
    """
    Write a JSON payload to a file or standard output.

    :param payload: JSON-compatible payload.
    :type payload: Mapping[str, Any]
    :param output: Optional output file path.
    :type output: Optional[str]
    :return: ``None``.
    :rtype: None

    Example::

        >>> _write_or_print({'ok': True}, None)  # doctest: +ELLIPSIS
        {...
    """
    if output:
        _write_payload(output, payload)
    else:
        print(_stable_json(payload), end="")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Run the probe command-line interface.

    :param argv: Optional argument vector excluding the executable name.
    :type argv: Optional[List[str]], optional
    :return: Process exit status.
    :rtype: int

    Example::

        >>> main(['env', '--output', '/tmp/pyfcstm-probe-env-example.json'])
        0
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.mode == "env":
        if args.check:
            parser.error(
                "--check is supported for python-z3-baseline, java-smoke, "
                "rust-smoke, java-rust-smoke and c-cpp-z3-alignment"
            )
        report = build_environment_report(args.repo_root)
        _write_or_print(report, args.output)
        return 0

    if args.mode in {"c-smoke", "cpp-smoke"}:
        if args.check:
            parser.error(
                "--check is supported for python-z3-baseline, java-smoke, "
                "rust-smoke, java-rust-smoke and c-cpp-z3-alignment"
            )
        report = build_c_family_smoke_report(
            args.mode,
            repo_root=args.repo_root,
            mapping_path=args.mapping,
            work_dir=args.work_dir,
            timeout=args.timeout,
        )
        _write_or_print(report, args.output)
        return 0

    if args.mode == "python-z3-baseline":
        if args.check:
            result = check_python_z3_baseline(args.repo_root, mapping_path=args.mapping)
            _write_or_print(result, args.output)
            return 0 if result["ok"] else 1
        report = build_python_z3_baseline(args.repo_root, mapping_path=args.mapping)
        _write_or_print(report, args.output)
        return 0

    if args.mode in _JAVA_RUST_MODES:
        if args.check:
            result = check_java_rust_smoke(
                args.mode,
                args.repo_root,
                mapping_path=args.mapping,
                work_dir=args.work_dir,
                timeout=args.timeout,
            )
            _write_or_print(result, args.output)
            return 0 if result.get("ok") else 1
        payload = build_java_rust_smoke_report(
            args.mode,
            args.repo_root,
            mapping_path=args.mapping,
            work_dir=args.work_dir,
            timeout=args.timeout,
        )
        _write_or_print(payload, args.output)
        return 0

    if args.mode == "c-cpp-z3-alignment":
        if args.check:
            result = check_c_cpp_z3_alignment(args.repo_root, mapping_path=args.mapping)
            _write_or_print(result, args.output)
            return 0 if result["ok"] else 1
        report = build_c_cpp_z3_alignment(args.repo_root, mapping_path=args.mapping)
        _write_or_print(report, args.output)
        return 0

    parser.error("unsupported mode: %s" % args.mode)
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
