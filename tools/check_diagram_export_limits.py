"""
Keep the export size limits identical on the Python and browser paths.

The same product limits are enforced twice, once in ``pyfcstm/diagram/engine.py``
for the synchronous export and once in ``editors/jsfcstm/src/diagram/export`` for
the browser download.  Neither side can check the other: the Python tests are not
allowed to read the jsfcstm tree and the jsfcstm tests are not allowed to read
the Python one, which is the boundary that keeps either suite runnable when the
other is absent.  This maintenance command sits outside both and compares them.

Drift here is quiet.  Two paths with different caps both export successfully; the
only symptom is that the same request is refused in one and accepted in the
other, which nothing in either suite would notice.

Run it directly, or through ``make diagram_assets_verify``::

    $ python tools/check_diagram_export_limits.py
    diagram export limits: 3 constants agree across both export paths
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, Iterable

ROOT = Path(__file__).resolve().parent.parent
PYTHON_SOURCE = ROOT / "pyfcstm" / "diagram" / "engine.py"
TYPESCRIPT_SOURCE = ROOT / "editors" / "jsfcstm" / "src" / "diagram" / "export" / "index.ts"

#: Product limits that must hold identically on both export paths, as
#: ``(python name, typescript name)``.  A limit that exists on only one side
#: belongs in this file's failure output, not in a comment somewhere.
SHARED_LIMITS = (
    ("MAX_EXPORT_SCALE", "EXPORT_MAX_SCALE"),
    ("MAX_EXPORT_EDGE_PX", "EXPORT_MAX_EDGE_PX"),
    ("MAX_EXPORT_PIXELS", "EXPORT_MAX_PIXELS"),
)

#: Limits enforced only on the Python export path, because only it weighs the
#: encoded bytes it produced.  Listed here so their absence from the browser side
#: is a recorded decision rather than something a reader has to infer from the
#: comparison table being short.
PYTHON_ONLY_LIMITS = (
    "MAX_EXPORT_PNG_BYTES",
    "MAX_EXPORT_TEXT_BYTES",
)

#: Host capability limits, which exist only in the browser path because only a
#: browser has them.  Each must stay above the product limit that shadows it, so
#: the refusal fires before the clamp and the clamp never changes an outcome the
#: refusal already allowed.
CAPABILITY_ORDERING = (
    ("EXPORT_MAX_EDGE_PX", "RASTER_MAX_SIDE"),
    ("EXPORT_MAX_PIXELS", "RASTER_MAX_AREA"),
)


def read_python_constants(text: str, names: Iterable[str]) -> Dict[str, int]:
    """
    Read module-level integer constants from Python source.

    The module is parsed rather than searched, and the *last* assignment wins,
    because that is the one that takes effect.  A regular expression taking the
    first match would report the documented value while a later line quietly
    doubled it.

    :param text: Python source text.
    :type text: str
    :param names: Constant names to find.
    :type names: collections.abc.Iterable[str]
    :return: The constants that were found, by name.
    :rtype: dict[str, int]

    Example::

        >>> read_python_constants("MAX_EXPORT_SCALE = 4\\n", ["MAX_EXPORT_SCALE"])
        {'MAX_EXPORT_SCALE': 4}
        >>> read_python_constants(
        ...     "A = 1\\nA = 2\\n", ["A"]
        ... )
        {'A': 2}
    """
    wanted = set(names)
    found = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # SyntaxError: the file under comparison is not valid Python, which is a
        # different problem and one every other gate will also report.
        return found
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id not in wanted:
                continue
            value = _literal_int(node.value, found)
            if value is not None:
                found[target.id] = value
    return found


def _literal_int(node, resolved: Dict[str, int]):
    """
    Evaluate an integer constant expression, including simple derivations.

    A limit may be written as another limit times a factor, which is how a derived
    figure is kept from drifting away from the number it derives from.

    :param node: Expression node from the assignment.
    :type node: ast.AST
    :param resolved: Constants already read, for name references.
    :type resolved: dict[str, int]
    :return: The integer value, or ``None`` if it is not an integer expression.
    :rtype: int or None

    Example::

        >>> import ast
        >>> _literal_int(ast.parse("4", mode="eval").body, {})
        4
    """
    if isinstance(node, ast.Num) and isinstance(node.n, int):
        return node.n
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        return resolved.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add)):
        left = _literal_int(node.left, resolved)
        right = _literal_int(node.right, resolved)
        if left is None or right is None:
            return None
        return left * right if isinstance(node.op, ast.Mult) else left + right
    return None


def read_typescript_constants(text: str, names: Iterable[str]) -> Dict[str, int]:
    """
    Read exported integer constants from TypeScript source.

    :param text: TypeScript source text.
    :type text: str
    :param names: Constant names to find.
    :type names: collections.abc.Iterable[str]
    :return: The constants that were found, by name.
    :rtype: dict[str, int]

    Example::

        >>> read_typescript_constants(
        ...     "export const EXPORT_MAX_SCALE = 4;\\n", ["EXPORT_MAX_SCALE"]
        ... )
        {'EXPORT_MAX_SCALE': 4}
    """
    found = {}
    for name in names:
        match = re.search(
            r"^export const %s\s*=\s*(\d+)\s*;\s*$" % re.escape(name), text, re.M
        )
        if match is not None:
            found[name] = int(match.group(1))
    return found


def compare(python_text: str, typescript_text: str) -> None:
    """
    Report every disagreement between the two export paths.

    :param python_text: Python source text.
    :type python_text: str
    :param typescript_text: TypeScript source text.
    :type typescript_text: str
    :return: ``None``.
    :rtype: None
    :raises SystemExit: If a constant is missing on either side, the two sides
        disagree, or a product limit is not stricter than the host limit it
        shadows.
    """
    python_names = [pair[0] for pair in SHARED_LIMITS] + list(PYTHON_ONLY_LIMITS)
    typescript_names = [pair[1] for pair in SHARED_LIMITS] + [
        pair[1] for pair in CAPABILITY_ORDERING
    ]
    python_values = read_python_constants(python_text, python_names)
    typescript_values = read_typescript_constants(typescript_text, typescript_names)

    problems = []
    for python_name, typescript_name in SHARED_LIMITS:
        if python_name not in python_values:
            problems.append("%s is missing from the Python export path" % python_name)
            continue
        if typescript_name not in typescript_values:
            problems.append(
                "%s is missing from the browser export path" % typescript_name
            )
            continue
        if python_values[python_name] != typescript_values[typescript_name]:
            problems.append(
                "%s is %d in Python but %s is %d in the browser path"
                % (
                    python_name,
                    python_values[python_name],
                    typescript_name,
                    typescript_values[typescript_name],
                )
            )
    for product_name, host_name in CAPABILITY_ORDERING:
        if product_name not in typescript_values or host_name not in typescript_values:
            problems.append(
                "cannot compare %s against %s; one of them is missing"
                % (product_name, host_name)
            )
            continue
        if typescript_values[product_name] >= typescript_values[host_name]:
            problems.append(
                "%s (%d) must stay below %s (%d), or the refusal stops firing "
                "before the clamp"
                % (
                    product_name,
                    typescript_values[product_name],
                    host_name,
                    typescript_values[host_name],
                )
            )
    for name in PYTHON_ONLY_LIMITS:
        if name not in python_values:
            problems.append(
                "%s is documented as a Python-only limit but is not there" % name
            )
    if problems:
        raise SystemExit(
            "diagram export limits disagree:\n  " + "\n  ".join(problems)
        )
    print(
        "diagram export limits: %d shared constants agree, %d Python-only limits "
        "present" % (len(SHARED_LIMITS), len(PYTHON_ONLY_LIMITS))
    )


def _self_check() -> None:
    """
    Prove this comparison reports the drift it exists to catch.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If the comparison accepts drift or rejects agreement.
    """
    good_python = "\n".join("%s = %d" % (name, value) for name, value in (
        ("MAX_EXPORT_SCALE", 4),
        ("MAX_EXPORT_EDGE_PX", 16384),
        ("MAX_EXPORT_PIXELS", 16777216),
        ("MAX_EXPORT_PNG_BYTES", 33554432),
        ("MAX_EXPORT_TEXT_BYTES", 67108864),
    ))
    good_ts = "\n".join("export const %s = %d;" % (name, value) for name, value in (
        ("EXPORT_MAX_SCALE", 4),
        ("EXPORT_MAX_EDGE_PX", 16384),
        ("EXPORT_MAX_PIXELS", 16777216),
        ("RASTER_MAX_SIDE", 32767),
        ("RASTER_MAX_AREA", 268435456),
    ))
    compare(good_python, good_ts)

    cases = (
        (
            "a raised browser limit",
            good_python,
            good_ts.replace("EXPORT_MAX_EDGE_PX = 16384", "EXPORT_MAX_EDGE_PX = 20000"),
        ),
        (
            "a raised Python limit",
            good_python.replace("MAX_EXPORT_PIXELS = 16777216", "MAX_EXPORT_PIXELS = 99999999"),
            good_ts,
        ),
        (
            "a product limit above its host limit",
            good_python.replace("MAX_EXPORT_EDGE_PX = 16384", "MAX_EXPORT_EDGE_PX = 40000"),
            good_ts.replace("EXPORT_MAX_EDGE_PX = 16384", "EXPORT_MAX_EDGE_PX = 40000"),
        ),
        ("a deleted Python limit", good_python.replace("MAX_EXPORT_SCALE = 4", ""), good_ts),
        (
            # A later assignment is the one that takes effect, and a reader that
            # took the first match reported the documented value while the runtime
            # used a doubled one.
            "a limit redefined further down the module",
            good_python + "\nMAX_EXPORT_EDGE_PX = 32768\n",
            good_ts,
        ),
        (
            "a Python-only limit that went missing",
            good_python.replace("MAX_EXPORT_PNG_BYTES = 33554432", ""),
            good_ts,
        ),
        (
            "a deleted browser limit",
            good_python,
            good_ts.replace("export const EXPORT_MAX_SCALE = 4;", ""),
        ),
    )
    for label, python_text, typescript_text in cases:
        try:
            compare(python_text, typescript_text)
        except SystemExit:
            continue
        raise SystemExit("the comparison accepted %s" % label)
    print("diagram export limits: self-check passed")


def main(argv=None) -> int:
    """
    Compare the two export paths, or run this command's own self-check.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int

    Example::

        $ python tools/check_diagram_export_limits.py --check
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="run this command's own self-check"
    )
    arguments = parser.parse_args(argv)
    if arguments.check:
        _self_check()
        return 0
    compare(
        PYTHON_SOURCE.read_text(encoding="utf-8"),
        TYPESCRIPT_SOURCE.read_text(encoding="utf-8"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
