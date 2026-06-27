"""
Provide probe entry points for numeric render-semantics research.

The lightweight ``env`` mode records local environment data without running
native workloads. The C-family smoke modes compile and execute small programs
whose expressions are rendered from the repository's R0
``render_mapping.json`` snapshot, so the probe follows the same renderer and
template facts that later exhaustive harnesses will use.

The module contains:

* :func:`build_environment_report` - Collect lightweight local environment data.
* :func:`build_c_family_smoke_report` - Run C or C++ smoke cases from R0 mapping.
* :func:`validate_probe_summary` - Validate the lightweight probe-summary contract.
* :func:`main` - Command-line entry point with ``env``, ``c-smoke`` and
  ``cpp-smoke`` modes.

Example::

    >>> from tools.numeric_render_probe import build_environment_report
    >>> report = build_environment_report('.')
    >>> report['native_runner_enabled']
    False
"""

from __future__ import annotations

import argparse
import json
import os
import platform

import jinja2
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

_REPO_ROOT_FOR_SCRIPT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_SCRIPT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_SCRIPT))

_JSON_OBJECT = Dict[str, Any]
_RESEARCH_PATH = "research/numeric-render-semantics"
_DEFAULT_MAPPING_PATH = "%s/results/snapshots/render_mapping.json" % _RESEARCH_PATH
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
    :param ext_configs: Template expression overrides from R0 mapping.
    :type ext_configs: Mapping[str, str]
    :param mapping_sources: Mapping paths that justify the render path.
    :type mapping_sources: Tuple[str, ...]

    Example::

        >>> path = RenderPath('builtin_c_style', 'c', 'c', 'c', {}, ('builtin_expr_styles.styles.c',))
        >>> path.compile_language
        'c'
    """

    path_id: str
    language: str
    compile_language: str
    lang_style: str
    ext_configs: Mapping[str, str]
    mapping_sources: Tuple[str, ...]


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
    if os.path.basename(path).startswith("python"):
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
    mapping = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        raise ValueError("Render mapping must be a JSON object: %s" % resolved)
    return mapping


def _risk_cases() -> List[NumericSmokeCase]:
    """
    Return the C-family numeric risk cases covered by PR-2.

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
            RenderPath(
                "builtin_c_style",
                "c",
                "c",
                "c",
                {},
                ("builtin_expr_styles.styles.c",),
            ),
            RenderPath(
                "template_c_core",
                "c",
                "c",
                "c",
                _template_expr_overrides(mapping, "c"),
                ("templates.c.expr_styles.c_scope_expr",),
            ),
            RenderPath(
                "template_c_poll_core",
                "c",
                "c",
                "c",
                _template_expr_overrides(mapping, "c_poll"),
                ("templates.c_poll.expr_styles.c_scope_expr",),
            ),
        ]
    if mode == "cpp-smoke":
        return [
            RenderPath(
                "builtin_cpp_style",
                "cpp",
                "cpp",
                "cpp",
                {},
                ("cxx_paths.builtin_cpp_style", "builtin_expr_styles.styles.cpp"),
            ),
            RenderPath(
                "template_cpp_c_core",
                "cpp",
                "c",
                "c",
                _template_expr_overrides(mapping, "cpp"),
                (
                    "cxx_paths.template_generated_paths[cpp]",
                    "templates.cpp.expr_styles.c_scope_expr",
                ),
            ),
            RenderPath(
                "template_cpp_poll_c_core",
                "cpp",
                "c",
                "c",
                _template_expr_overrides(mapping, "cpp_poll"),
                (
                    "cxx_paths.template_generated_paths[cpp_poll]",
                    "templates.cpp_poll.expr_styles.c_scope_expr",
                ),
            ),
        ]
    raise ValueError("Unsupported C-family smoke mode: %s" % mode)


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
        >>> path = RenderPath('builtin_c_style', 'c', 'c', 'c', {}, ('builtin_expr_styles.styles.c',))
        >>> _render_case_expression(case, path)
        'pow(A, B)'
    """
    from pyfcstm.model.expr import parse_expr_from_string
    from pyfcstm.render.expr import render_expr_node
    from pyfcstm.utils import to_c_identifier

    env = jinja2.Environment()
    env.filters["to_c_identifier"] = to_c_identifier
    env.globals["to_c_identifier"] = to_c_identifier
    expr = parse_expr_from_string(case.fcstm_expression, mode="numeric")
    return render_expr_node(
        expr.to_ast_node(),
        lang_style=render_path.lang_style,
        ext_configs=dict(render_path.ext_configs),
        env=env,
    )


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
        >>> path = RenderPath('builtin_c_style', 'c', 'c', 'c', {}, ('builtin_expr_styles.styles.c',))
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
    Validate the lightweight probe-summary contract used by PR-2.

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
    render_paths = _render_paths_for_mode(mode, mapping)
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
            "source_mapping_sha256": mapping["mapping_sha256"],
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
                    "mapping_sources": list(path.mapping_sources),
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
        choices=["env", "c-smoke", "cpp-smoke"],
        help="Probe mode: 'env', 'c-smoke', or 'cpp-smoke'.",
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
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


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
        report = build_environment_report(args.repo_root)
    else:
        report = build_c_family_smoke_report(
            args.mode,
            repo_root=args.repo_root,
            mapping_path=args.mapping,
            work_dir=args.work_dir,
            timeout=args.timeout,
        )
    _write_or_print(report, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
