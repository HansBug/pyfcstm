"""Ask Sphinx itself whether the diagram package's references resolve.

``tools/check_diagram_references.py`` compares fully-qualified ``pyfcstm.*`` targets
against what ``api_doc`` registers, which it can do without a build. What it cannot
judge is a name written without its module: which candidates Sphinx tries there
depends on the enclosing class, on the ``refspecific`` flag information fields carry,
and on whether an inventory could resolve it elsewhere. Three attempts at reproducing
that reported live links as dead.

So this asks the resolver. A nitpicky build reports every reference it could not
resolve, bare ones included, and a dotted path broken across lines with it. Run over
the whole tree that is 1700-odd warnings and an exit status of zero -- which is why
saying "a ``-n`` build is the backstop" was not true of anything. This narrows it to
the diagram package's own docstrings and pages, allows the handful of external names
that never resolve here because intersphinx is not configured, and fails on the rest.

What it therefore catches, and the sibling checker does not:

* a misspelled bare member, ``:meth:`to_dictt``` in a class docstring;
* a dotted path broken across lines, ``:rtype: pyfcstm.diagram.`` continuing on the
  next line;
* and the same wrong-module targets the sibling catches, from the other direction.

Run ``make diagram_nitpick_check``. Pass ``--check`` for the self-check, which proves
the classifier keeps the allowed names and reports the rest.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Whose references are judged: the package's own docstrings, and the pages written for
# it. A warning from anywhere else in the tree is somebody else's to answer for.
SCOPE = (
    "pyfcstm/diagram/",
    "pyfcstm/entry/diagram.py",
    "docs/source/api_doc/diagram/",
    "docs/source/api_doc/entry/diagram",
    "docs/source/explanations/visualization/",
    "docs/source/reference/visualization_options/",
    "docs/source/tutorials/visualization/",
    "docs/source/how_to/visualization/",
)

# Names that never resolve in this repository and are not this package's to answer
# for: `optional` is the type-field convention CLAUDE.md sets out, and the rest are
# standard library or third-party names that would need an intersphinx mapping.
ALLOWED = frozenset(
    (
        "optional",
        "os.PathLike",
        "pathlib.Path",
        "json.dumps",
        "hash",
        "dataclasses.replace",
        "collections.abc.Mapping",
        "collections.abc.Iterable",
        "collections.abc.Sequence",
        "matplotlib.pyplot.show",
        "subprocess.Popen",
    )
)

# Sphinx says either "reference target not found: X" or, under a translated locale,
# the same with a localised prefix; the target is what follows the last colon before
# the role tag.
TARGET = re.compile(r"(?:reference target not found|引用目标)[:：]\s*(.+?)\s*\[ref\.")


def unresolved(log: str) -> List[Tuple[str, str]]:
    """
    Pull the source and target out of each unresolved-reference warning.

    :param log: A nitpicky build's output.
    :type log: str
    :return: Pairs of the warning's source location and the target it could not find.
    :rtype: list[tuple[str, str]]
    """
    found = []
    lines = log.splitlines()
    for index, line in enumerate(lines):
        if "WARNING" not in line:
            continue
        # A warning is not always one line: a target that itself contains a newline --
        # a dotted path broken across lines in the source -- puts the `[ref.class]`
        # tag on the next line of the log. Reading a line at a time missed exactly
        # the case this gate was added for, which is the fourth time in this branch
        # that a line-anchored read has hidden something.
        block = [line]
        while "[ref." not in block[-1] and index + len(block) < len(lines):
            following = lines[index + len(block)]
            if "WARNING" in following:
                break
            block.append(following)
        match = TARGET.search(" ".join(block))
        if match is None:
            continue
        found.append((line.split(": WARNING", 1)[0], match.group(1)))
    return found


def in_scope(where: str) -> bool:
    """
    Say whether a warning's source belongs to the diagram package.

    :param where: The location Sphinx printed, a path with optional suffixes.
    :type where: str
    :return: ``True`` when it is one of this package's files.
    :rtype: bool
    """
    normalised = where.replace(str(ROOT) + "/", "")
    return any(part in normalised for part in SCOPE)


def offenders(log: str) -> List[Tuple[str, str]]:
    """
    Return the in-scope unresolved references that are not on the allowed list.

    :param log: A nitpicky build's output.
    :type log: str
    :return: Pairs of location and target.
    :rtype: list[tuple[str, str]]
    """
    return [
        (where, target)
        for where, target in unresolved(log)
        if in_scope(where) and target not in ALLOWED
    ]


def build(language: str, destination: Path) -> str:
    """
    Run a nitpicky HTML build and return everything it printed.

    :param language: ``en`` or ``zh``.
    :type language: str
    :param destination: Where to write the build.
    :type destination: pathlib.Path
    :return: The build's combined output.
    :rtype: str
    :raises SystemExit: If Sphinx itself fails, which is not this gate's finding to
        make but does mean the answer is unknown.
    """
    environment = dict(os.environ)
    environment["NO_CONTENTS_BUILD"] = "1"
    environment["READTHEDOCS_LANGUAGE"] = language
    finished = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-n",
            "-q",
            str(ROOT / "docs" / "source"),
            str(destination),
        ],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3600,
    )
    output = finished.stdout.decode("utf-8", "replace")
    if finished.returncode != 0:
        raise SystemExit(
            "the %s build failed, so nothing can be concluded:\n%s"
            % (language, output[-4000:])
        )
    return output


def _self_check() -> None:
    """
    Prove the classifier keeps what it should and reports what it should.

    :return: ``None``.
    :rtype: None
    """
    log = "\n".join(
        (
            "/repo/pyfcstm/diagram/api.py:docstring of x:3: WARNING: py:meth "
            "reference target not found: to_dictt [ref.meth]",
            # A target with a newline in it, which is what a dotted path broken
            # across lines produces, tag and all on the following line.
            "/repo/pyfcstm/diagram/api.py:docstring of v:5: WARNING: py:class "
            "reference target not found: pyfcstm.diagram.",
            "api.Diagram [ref.class]",
            "/repo/pyfcstm/diagram/api.py:docstring of y:1: WARNING: py:class "
            "reference target not found: os.PathLike [ref.class]",
            "/repo/pyfcstm/bmc/engine.py:docstring of z:2: WARNING: py:class "
            "reference target not found: pyfcstm.model.StateMachine [ref.class]",
            "/repo/docs/source/explanations/visualization/index.rst:9: WARNING: "
            "py:class reference target not found: pyfcstm.diagram.Gone [ref.class]",
            "/repo/pyfcstm/diagram/api.py:docstring of w:4: WARNING: py:class "
            "reference target not found: optional [ref.class]",
            "/repo/docs/source/index.rst:1: WARNING: toctree contains reference to "
            "nonexisting document 'nowhere'",
        )
    )
    seen = sorted(target for _, target in offenders(log))
    wanted = ["pyfcstm.diagram. api.Diagram", "pyfcstm.diagram.Gone", "to_dictt"]
    if seen != wanted:
        raise SystemExit("classifier wrong: %s" % seen)
    # The allowed names, the out-of-scope package and the non-reference warning are
    # all absent from that list, which is the other half of the contract.
    print("diagram nitpick: self-check passed")


def main(argv: Iterable[str]) -> int:
    """
    Report unresolved references in the diagram package, or run the self-check.

    :param argv: Command-line arguments without the program name.
    :type argv: collections.abc.Iterable[str]
    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="run the classifier's self-check and exit"
    )
    parser.add_argument(
        "--language",
        action="append",
        default=None,
        help="a language to build; repeatable, defaults to en and zh",
    )
    arguments = parser.parse_args(list(argv))
    if arguments.check:
        _self_check()
        return 0
    languages: Sequence[str] = arguments.language or ["en", "zh"]
    total = 0
    reported: Set[Tuple[str, str]] = set()
    with tempfile.TemporaryDirectory(prefix="pyfcstm-nitpick-") as raw:
        for language in languages:
            log = build(language, Path(raw) / language)
            for where, target in offenders(log):
                if (where, target) in reported:
                    continue
                reported.add((where, target))
                location = where.replace(str(ROOT) + "/", "")
                sys.stderr.write("%s: %s does not resolve\n" % (location, target))
                total += 1
    if total:
        sys.stderr.write(
            "%d unresolved reference(s) in the diagram package. A reference Sphinx "
            "cannot resolve renders as plain text; point it at the object's own "
            "module, or add it to the allowed list if it is genuinely external.\n"
            % total
        )
        return 1
    print(
        "diagram nitpick: %s build(s), no unresolved reference in the diagram package"
        % len(languages)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
