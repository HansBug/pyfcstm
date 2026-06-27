"""
Probe numeric render-semantics research artifacts.

This module provides lightweight, repository-local probe entry points for the
numeric render-semantics research track.  The environment mode records local
runtime/toolchain inventory without compiling or executing native target code.
The Python/Z3 baseline mode records the current Python render/runtime facts and
Z3 encoding capability boundaries used by later exhaustive and summary work.

The module contains:

* :func:`build_environment_report` - Collect lightweight local environment data.
* :func:`build_python_z3_baseline` - Build the Python/Z3 capability baseline.
* :func:`check_python_z3_baseline` - Validate the generated or committed baseline.
* :func:`main` - Command-line entry point for research probe modes.

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
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

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
from tools.numeric_render_mapping import build_render_mapping  # noqa: E402

_JSON_OBJECT = Dict[str, Any]
_RESEARCH_PATH = Path("research/numeric-render-semantics")
_RENDER_MAPPING_SNAPSHOT = _RESEARCH_PATH / "results/snapshots/render_mapping.json"
_PYTHON_Z3_BASELINE_SNAPSHOT = (
    _RESEARCH_PATH / "results/snapshots/python_z3_baseline.json"
)
_PYTHON_Z3_BASELINE_SCHEMA = _RESEARCH_PATH / "schemas/python_z3_baseline.schema.json"
_COMMANDS = [
    "python",
    "git",
    "cc",
    "gcc",
    "g++",
    "clang",
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
_Z3_SORTS = ["Int", "Real", "BitVec", "FP"]
_Z3_SUPPORT_LEVELS = {"exact", "approximate", "uninterpreted", "unsupported"}
_RISK_LEVELS = {"low", "medium", "high", "unknown"}
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


def _repo_relative(path: Union[str, Path], repo_root: Union[str, Path]) -> str:
    """
    Return a stable repository-relative path string.

    :param path: Path to relativize.
    :type path: Union[str, pathlib.Path]
    :param repo_root: Repository root path.
    :type repo_root: Union[str, pathlib.Path]
    :return: POSIX-style repository-relative path.
    :rtype: str

    Example::

        >>> _repo_relative('tools/numeric_render_probe.py', '.')
        'tools/numeric_render_probe.py'
    """
    root = Path(repo_root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    return target.resolve().relative_to(root).as_posix()


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
            "research_path": "research/numeric-render-semantics",
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
            "Native runners are intentionally deferred to dedicated probe work.",
        ],
    }


def _stable_json(value: Any) -> str:
    """
    Serialize a value as stable, human-readable JSON.

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
        rendered = renderer.env.globals["expr_render"](
            expr.to_ast_node(), style=style
        )
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


def build_python_z3_baseline(repo_root: Union[str, Path] = ".") -> _JSON_OBJECT:
    """
    Build the Python/Z3 numeric semantics baseline snapshot.

    The snapshot is intentionally small and deterministic: it records render
    paths, representative Python runtime samples, and Z3 capability levels
    rather than exhaustive model outputs.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: JSON-compatible Python/Z3 baseline payload.
    :rtype: Dict[str, Any]

    Example::

        >>> baseline = build_python_z3_baseline('.')
        >>> baseline['mode']
        'python-z3-baseline'
    """
    root = Path(repo_root).resolve()
    mapping = build_render_mapping(root)
    mapping_sha = mapping["mapping_sha256"]
    return {
        "schema_version": 1,
        "mode": "python-z3-baseline",
        "language": "python-z3",
        "source_mapping_sha256": mapping_sha,
        "render_mapping_sha256": mapping_sha,
        "generator": {
            "tool": "tools/numeric_render_probe.py",
            "research_path": _RESEARCH_PATH.as_posix(),
            "source_commit": _git_commit(root),
            "source_commit_policy": "Best-effort commit at generation time; mapping and schema validation are the stable comparison keys.",
            "determinism": "No wall-clock timestamp is stored; concrete Z3 model values are not used as core facts.",
        },
        "repository": {
            "root": ".",
            "render_mapping_snapshot": _RENDER_MAPPING_SNAPSHOT.as_posix(),
            "schema_path": _PYTHON_Z3_BASELINE_SCHEMA.as_posix(),
        },
        "toolchain": {
            "python": {
                "executable": sys.executable,
                "version": sys.version.split()[0],
                "implementation": platform.python_implementation(),
            },
            "z3": {
                "python_package_version": z3.get_version_string(),
                "seed_policy": "Capability rows avoid solver model dependence; future model-valued rows must record a fixed seed.",
            },
        },
        "python_render_paths": _build_python_render_paths(mapping, root),
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
    the research artifact schemas: ``$ref``, ``type``, ``required``,
    ``properties``, object ``additionalProperties``, ``const``, ``enum``,
    ``pattern``, ``minItems`` and homogeneous ``items``.

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

    if isinstance(value, Mapping):
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
                    "python_expr sign(A) must render through self._sign(self._vars[\"A\"])"
                )
            sign_scope = template_by_key.get(("python_scope_expr", "sign(A)"), {})
            if sign_scope.get("rendered") != 'self._sign(scope["A"])':
                errors.append(
                    "python_scope_expr sign(A) must render through self._sign(scope[\"A\"])"
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
                    "python_runtime sign(A) assignment must render through _s(_v[\"A\"])"
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
                item.get("input"): item for item in round_cases if isinstance(item, Mapping)
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
            errors.append("python_runtime_samples.shift_cases must include -8 >> 1 == -4")

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
                isinstance(item, Mapping)
                and item.get("modulo_matches_python") is False
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
            item.get("fcstm_operator"): item for item in matrix if isinstance(item, Mapping)
        }
        operators = set(rows_by_operator)
        for required in ["round", "sign", "cbrt", "~", "/", "%"]:
            if required not in operators:
                errors.append("z3_capability_matrix missing operator %s" % required)
        division_row = rows_by_operator.get("/")
        if isinstance(division_row, Mapping):
            division_int = division_row.get("z3_support", {}).get("Int", {})
            if isinstance(division_int, Mapping) and division_int.get(
                "status"
            ) == "exact":
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


def check_python_z3_baseline(repo_root: Union[str, Path] = ".") -> _JSON_OBJECT:
    """
    Build and validate the Python/Z3 baseline snapshot contract.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: Check result with ``ok`` and ``errors`` fields.
    :rtype: Dict[str, Any]

    Example::

        >>> result = check_python_z3_baseline('.')
        >>> isinstance(result['ok'], bool)
        True
    """
    root = Path(repo_root).resolve()
    live = build_python_z3_baseline(root)
    errors = [
        "live baseline: %s" % error for error in validate_python_z3_baseline(live)
    ]
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
        "snapshot_path": _PYTHON_Z3_BASELINE_SNAPSHOT.as_posix(),
    }


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
        choices=["env", "python-z3-baseline"],
        help="Probe mode. Use 'env' for inventory or 'python-z3-baseline' for Python/Z3 baseline output.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to describe, defaults to the current directory.",
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
            parser.error("--check is currently supported only for python-z3-baseline")
        report = build_environment_report(args.repo_root)
        payload = _stable_json(report)
        if args.output:
            _write_payload(args.output, report)
        else:
            print(payload, end="")
        return 0

    if args.mode == "python-z3-baseline":
        if args.check:
            result = check_python_z3_baseline(args.repo_root)
            payload = _stable_json(result)
            if args.output:
                _write_payload(args.output, result)
            else:
                print(payload, end="")
            return 0 if result["ok"] else 1
        report = build_python_z3_baseline(args.repo_root)
        if args.output:
            _write_payload(args.output, report)
        else:
            print(_stable_json(report), end="")
        return 0

    parser.error("unsupported mode: %s" % args.mode)
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
