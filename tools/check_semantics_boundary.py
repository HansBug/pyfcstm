"""
Report operator semantics defined outside the operator catalog.

Every FCSTM operator has one meaning, given by :mod:`pyfcstm.semantics.catalog`.
A second table that maps operator tokens to computations -- ``{"+": operator.add,
"/": lambda a, b: a / b}`` -- is a second definition that can drift from the
catalog, which is how the simulator, the solver and the generated runtimes once
disagreed about division and modulo.  This scan finds such tables.

A table is reported when it is a dict literal with at least three arithmetic or
bitwise operator tokens as keys and callables (lambdas, names or attributes) as
values.  Tables whose values are strings are rendering templates for a target
language, which are allowed: they say how to spell an operation, not what it
means.

Usage::

    python tools/check_semantics_boundary.py --check
    python tools/check_semantics_boundary.py --selfcheck

``--selfcheck`` scans planted sources to prove the scan can fail.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = _ROOT / "pyfcstm"
#: The catalog is the one place allowed to define operator semantics; the
#: generated grammar files are produced by ANTLR.
_ALLOWED = (
    _PACKAGE / "semantics",
    _PACKAGE / "dsl" / "grammar",
    _PACKAGE / "bmc" / "grammar",
)
_OPERATOR_TOKENS = {"+", "-", "*", "/", "%", "**", "<<", ">>", "&", "^", "|"}
_MINIMUM_TOKENS = 3


def _is_callable_value(node: ast.AST) -> bool:
    return isinstance(node, (ast.Lambda, ast.Name, ast.Attribute))


def _token(node: ast.AST):
    # ast.Constant from Python 3.8; ast.Str on 3.7.
    value = getattr(node, "value", getattr(node, "s", None))
    return value if isinstance(value, str) else None


def scan_source(source: str, filename: str) -> List[Tuple[str, int]]:
    """Return ``(filename, line)`` of every operator-semantics table in ``source``."""
    found = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if not isinstance(node, ast.Dict):
            continue
        tokens = [
            _token(key)
            for key, value in zip(node.keys, node.values)
            if key is not None
            and _token(key) in _OPERATOR_TOKENS
            and _is_callable_value(value)
        ]
        if len(set(tokens)) >= _MINIMUM_TOKENS:
            found.append((filename, node.lineno))
    return found


def _package_files() -> Iterator[Path]:
    for path in sorted(_PACKAGE.rglob("*.py")):
        if not any(allowed in path.parents for allowed in _ALLOWED):
            yield path


def check() -> int:
    """Scan the package and report every table found outside the catalog."""
    violations = []
    for path in _package_files():
        violations.extend(
            scan_source(path.read_text(encoding="utf-8"), str(path.relative_to(_ROOT)))
        )
    for filename, line in violations:
        print(
            "%s:%d: operator semantics defined outside pyfcstm.semantics.catalog"
            % (filename, line)
        )
    if violations:
        return 1
    print(
        "semantics boundary check passed: operator semantics live only in the catalog"
    )
    return 0


_PLANTED_VIOLATIONS = (
    "import operator\n_OPS = {'+': operator.add, '-': operator.sub, '/': operator.truediv}\n",
    "_OPS = {'%': lambda a, b: a % b, '**': pow, '<<': lambda a, b: a << b}\n",
)
_PLANTED_ALLOWED = (
    "_STYLE = {'+': '{} + {}', '-': '{} - {}', '/': '{} / {}'}\n",
    "_OPS = {'+': operator.add, '-': operator.sub}\n",
    "_NAMES = {'add': operator.add, 'sub': operator.sub, 'mul': operator.mul}\n",
)


def selfcheck() -> int:
    """Prove the scan reports planted tables and accepts rendering tables."""
    failures = [
        source for source in _PLANTED_VIOLATIONS if not scan_source(source, "<planted>")
    ] + [source for source in _PLANTED_ALLOWED if scan_source(source, "<planted>")]
    for source in failures:
        print("selfcheck misclassified: %r" % source)
    if failures:
        return 1
    print("semantics boundary selfcheck passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Scan the package.")
    mode.add_argument("--selfcheck", action="store_true", help="Scan planted sources.")
    args = parser.parse_args()
    return check() if args.check else selfcheck()


if __name__ == "__main__":
    sys.exit(main())
