"""Run the docstring examples of the public diagram API.

The ``Example::`` blocks are the first thing a reader copies, so an example
that does not run is a defect in the public surface rather than a cosmetic
issue. Three of them once passed ``DiagramData`` where the renderer expects
``{"diagram": ...}``, which raised ``DiagramRenderError`` for anyone who
followed the method's own documentation while the class docstring two hundred
lines above showed the correct shape.

Exception examples are written with the bare class name, matching the
convention used across this repository, so ``IGNORE_EXCEPTION_DETAIL`` is
enabled; everything else is executed exactly as printed.

This is a maintenance command rather than a unit test: the examples drive the
real renderer, which is far slower than the rest of the suite and needs built
assets. Run it with ``make diagram_docstring_check`` after touching a
docstring in the diagram package.
"""

import doctest
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = (
    "pyfcstm.diagram",
    "pyfcstm.diagram.api",
    "pyfcstm.diagram.engine",
    "pyfcstm.entry.diagram",
)

OPTION_FLAGS = (
    doctest.ELLIPSIS | doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE
)


def main() -> None:
    """
    Execute every diagram docstring example and fail on the first bad one.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If any example fails or raises.
    """
    attempted = 0
    failed = 0
    for name in MODULES:
        module = importlib.import_module(name)
        result = doctest.testmod(module, optionflags=OPTION_FLAGS, verbose=False)
        attempted += result.attempted
        failed += result.failed
    if failed:
        raise SystemExit(
            "%d of %d diagram docstring examples failed; the output above shows "
            "each one" % (failed, attempted)
        )
    if attempted == 0:
        raise SystemExit(
            "no diagram docstring examples were collected, which means this "
            "check is no longer looking at anything"
        )
    print("diagram docstring examples: %d ran, all passed" % attempted)


if __name__ == "__main__":
    main()
