"""
Change the package version everywhere it is written, or check that it agrees.

The version is written by hand in a few places besides
``pyfcstm/config/meta.py``: the docstring example of that module, the version
test, and the self-check tests that compare the startup header. Missing one of
them only fails much later, in CI or in a release build, so this tool owns the
complete list. Each entry names the exact text it expects; a bump fails without
writing anything when an entry no longer matches the expected number of times,
which is how the list is kept honest when the code around it changes.

Other occurrences of the same number are deliberately left alone: a deprecation
recorded as ``deprecated_in: '0.7.0'`` or a dependency pin such as
``mini-racer>=0.7.0`` is a fact about history or about another package, not the
version of this one.

The release notes are not rewritten. A bump checks that both
``docs/source/release_notes.rst`` and ``docs/source/release_notes_zh.rst`` start
with a section for the new version and reports it when they do not, so the notes
are written by a person rather than generated.

This is a repository maintenance tool, not part of the ``pyfcstm`` package.

Example::

    $ python tools/bump_version.py --check
    $ python tools/bump_version.py 0.7.1
"""
import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "pyfcstm" / "config" / "meta.py"
RELEASE_NOTES = (
    ROOT / "docs" / "source" / "release_notes.rst",
    ROOT / "docs" / "source" / "release_notes_zh.rst",
)

# (file, template, expected count). ``{version}`` is replaced by the version.
LOCATIONS = (
    ("pyfcstm/config/meta.py", "__VERSION__: str = '{version}'", 1),
    ("pyfcstm/config/meta.py", "    >>> meta.__VERSION__\n    '{version}'", 1),
    ("test/config/test_meta.py", 'assert __VERSION__ == "{version}"', 1),
    ("test/_selfcheck/test_bootstrap.py", "pyfcstm self-check {version}", 2),
    ("test/_selfcheck/test_report.py", "pyfcstm self-check {version}", 1),
    ("test/_selfcheck/test_supervisor.py", "pyfcstm self-check {version}", 1),
)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def current_version() -> str:
    """
    Read the version that ``pyfcstm/config/meta.py`` declares.

    :return: The declared version, for example ``'0.7.0'``.
    :rtype: str
    :raises SystemExit: If the declaration cannot be found.
    """
    match = re.search(r"^__VERSION__: str = '([^']+)'$", META.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit("cannot find __VERSION__ in {}".format(META))
    return match.group(1)


def find_mismatches(version: str) -> List[str]:
    """
    List the owned locations that do not carry ``version`` as expected.

    :param version: Version every location should carry.
    :type version: str
    :return: One message per location whose text occurs a different number of times.
    :rtype: list[str]
    """
    problems = []
    for name, template, expected in LOCATIONS:
        text = (ROOT / name).read_text(encoding="utf-8")
        found = text.count(template.format(version=version))
        if found != expected:
            problems.append(
                "{}: expected {} x {!r}, found {}".format(name, expected, template.format(version=version), found)
            )
    return problems


def find_missing_notes(version: str) -> List[str]:
    """
    List the release-note files whose first section is not ``v<version>``.

    :param version: Version whose section should come first.
    :type version: str
    :return: One message per release-note file that lacks the section.
    :rtype: list[str]
    """
    problems = []
    heading = "v{}".format(version)
    for path in RELEASE_NOTES:
        lines = path.read_text(encoding="utf-8").splitlines()
        sections = [lines[i - 1] for i in range(1, len(lines)) if lines[i] and set(lines[i]) == {"-"} and lines[i - 1].strip()]
        if not sections or sections[0] != heading:
            problems.append("{}: the first section is {!r}, expected {!r}".format(
                path.relative_to(ROOT), sections[0] if sections else None, heading
            ))
    return problems


def bump(old: str, new: str) -> List[Tuple[str, int]]:
    """
    Replace ``old`` by ``new`` in every owned location, writing only if all match.

    :param old: Current version.
    :type old: str
    :param new: New version.
    :type new: str
    :return: The changed files with the number of replacements in each.
    :rtype: list[tuple[str, int]]
    :raises SystemExit: If any owned location does not carry ``old`` as expected.
    """
    problems = find_mismatches(old)
    if problems:
        raise SystemExit("refusing to bump, the owned locations do not agree:\n  " + "\n  ".join(problems))
    contents = {}
    for name, template, expected in LOCATIONS:
        text = contents.get(name, (ROOT / name).read_text(encoding="utf-8"))
        contents[name] = text.replace(template.format(version=old), template.format(version=new))
    changed = []
    for name, text in contents.items():
        path = ROOT / name
        count = sum(expected for owner, _, expected in LOCATIONS if owner == name)
        with open(path, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        changed.append((name, count))
    return changed


def main(argv: List[str]) -> int:
    """
    Run the tool and return its exit status.

    :param argv: Command-line arguments without the program name.
    :type argv: list[str]
    :return: ``0`` on success, ``1`` when a check finds a problem.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    parser.add_argument("version", nargs="?", help="new version, for example 0.7.1")
    parser.add_argument("--check", action="store_true", help="only check that every owned location agrees")
    args = parser.parse_args(argv)
    old = current_version()
    if args.check or args.version is None:
        problems = find_mismatches(old)
        for item in problems:
            print("ERROR:", item)
        if not problems:
            print("version {} is written consistently in {} locations".format(old, len(LOCATIONS)))
        return 1 if problems else 0
    if not VERSION_PATTERN.match(args.version):
        raise SystemExit("version must look like 1.2.3: {}".format(args.version))
    if args.version == old:
        raise SystemExit("the version is already {}".format(old))
    for name, count in bump(old, args.version):
        print("{}: {} replacement(s)".format(name, count))
    problems = find_mismatches(args.version)
    for item in problems:
        print("ERROR:", item)
    for item in find_missing_notes(args.version):
        print("TODO:", item)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
