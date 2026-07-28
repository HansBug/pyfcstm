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
import importlib.util
import re
import sys
from typing import Optional
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


_DOTTED = re.compile(r"\bpyfcstm(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


def _check_dotted_paths(name: str) -> int:
    """
    Reject a docstring example naming a ``pyfcstm`` path that cannot be reached.

    ``IGNORE_EXCEPTION_DETAIL`` lets doctest match an expected exception by
    class alone, and it discards the module prefix along with the message. An
    example can therefore say ``pyfcstm.diagram.errors.DiagramUnavailableError``
    -- a module this package has never had -- and still pass, while the
    rendered API documentation sends the reader to an import that fails. A
    real module carrying a class name that does not exist fails the reader in
    exactly the same way, so the attributes are resolved too.

    The split between module and attribute is found by importing the longest
    prefix that imports, rather than by guessing from capitalisation: a
    lowercase tail is not evidence of a module (``pyfcstm.diagram.api.Diagram``
    has ``to_html``) and an uppercase one is not evidence of an attribute.

    :param name: Importable module whose docstrings are scanned.
    :type name: str
    :return: Number of unreachable dotted paths found.
    :rtype: int
    """
    module = importlib.import_module(name)
    bad = 0
    for test in doctest.DocTestFinder().find(module, name):
        for example in test.examples:
            for candidate in sorted(set(_DOTTED.findall(example.want))):
                problem = _unreachable(candidate)
                if problem is None:
                    continue
                print("%s: example names %s, but %s" % (test.name, candidate, problem))
                bad += 1
    return bad


def _unreachable(candidate: str) -> Optional[str]:
    """
    Explain why ``candidate`` cannot be resolved, or return ``None``.

    :param candidate: Dotted path printed by a docstring example.
    :type candidate: str
    :return: A reason, or ``None`` when the path resolves.
    :rtype: str or None
    """
    parts = candidate.split(".")
    for stop in range(len(parts), 0, -1):
        dotted = ".".join(parts[:stop])
        try:
            found = importlib.util.find_spec(dotted) is not None
        except (ImportError, AttributeError, ValueError, TypeError):
            # ImportError/ModuleNotFoundError: a parent in the path is not a
            # package, which is the answer rather than an error here.
            # AttributeError/ValueError/TypeError: find_spec refuses paths that
            # name an attribute instead of a module.
            found = False
        if not found:
            continue
        target = importlib.import_module(dotted)
        for attribute in parts[stop:]:
            if not hasattr(target, attribute):
                return "%s has no %s" % (dotted, attribute)
            target = getattr(target, attribute)
        return None
    return "%s does not import" % parts[0]


_SELF_CHECK_CASES = (
    # (path, must be reported)
    ("pyfcstm.diagram.engine.DiagramUnavailableError", False),
    ("pyfcstm.diagram.api.Diagram.to_html", False),
    ("pyfcstm.model.StateMachine", False),
    ("pyfcstm.diagram.errors.DiagramUnavailableError", True),
    ("pyfcstm.diagram.engine.ThisClassDoesNotExistAtAll", True),
    ("pyfcstm.diagram.engine.NotReal.DiagramUnavailableError", True),
    ("pyfcstm.nope.Thing", True),
)


def _self_check() -> None:
    """
    Prove the path resolver reports what it claims to and nothing else.

    The first version of this check guessed the module/attribute boundary from
    capitalisation. That flagged the legitimate ``Diagram.to_html`` and waved
    through both a class that does not exist on a real module and a made-up
    segment in the middle of one, which is the whole failure it exists to
    catch. A gate whose own behaviour is unverified is worth very little, so
    the cases that broke it are pinned here.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If any case resolves the wrong way.
    """
    wrong = []
    for candidate, should_report in _SELF_CHECK_CASES:
        reported = _unreachable(candidate) is not None
        if reported != should_report:
            wrong.append(
                "%s: expected %s, got %s"
                % (
                    candidate,
                    "a report" if should_report else "no report",
                    "a report" if reported else "no report",
                )
            )
    if wrong:
        raise SystemExit("path resolver self-check failed:\n  " + "\n  ".join(wrong))
    print("path resolver self-check: %d cases passed" % len(_SELF_CHECK_CASES))


def main() -> None:
    """
    Execute every diagram docstring example and fail on the first bad one.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If any example fails or raises.
    """
    if "--check" in sys.argv[1:]:
        _self_check()
        return
    attempted = 0
    failed = 0
    for name in MODULES:
        module = importlib.import_module(name)
        result = doctest.testmod(module, optionflags=OPTION_FLAGS, verbose=False)
        attempted += result.attempted
        failed += result.failed
    unresolved = sum(_check_dotted_paths(name) for name in MODULES)
    if unresolved:
        raise SystemExit(
            "%d docstring example(s) name a pyfcstm path that does not resolve"
            % unresolved
        )
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
