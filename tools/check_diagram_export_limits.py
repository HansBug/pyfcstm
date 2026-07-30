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

    :param text: Python source text.
    :type text: str
    :param names: Constant names to find.
    :type names: collections.abc.Iterable[str]
    :return: The constants that were found, by name.
    :rtype: dict[str, int]

    Example::

        >>> read_python_constants("MAX_EXPORT_SCALE = 4\\n", ["MAX_EXPORT_SCALE"])
        {'MAX_EXPORT_SCALE': 4}
    """
    found = {}
    for name in names:
        match = re.search(r"^%s\s*=\s*(\d+)\s*$" % re.escape(name), text, re.M)
        if match is not None:
            found[name] = int(match.group(1))
    return found


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
    python_names = [pair[0] for pair in SHARED_LIMITS]
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
    if problems:
        raise SystemExit(
            "diagram export limits disagree:\n  " + "\n  ".join(problems)
        )
    print(
        "diagram export limits: %d constants agree across both export paths"
        % len(SHARED_LIMITS)
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
