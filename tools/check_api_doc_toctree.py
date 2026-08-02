"""
Validate that generated API documentation lists every module it should.

``auto_rst.py`` builds a package's ``index.rst`` toctree by listing the package
directory, so the toctree is only correct while the generated page is newer than
every module beside it.  ``make rst_auto`` decides that from the Makefile's
prerequisites, and a package index that names only ``__init__.py`` will happily
report itself up to date after a new module lands -- leaving the module's own
generated page in the tree with nothing linking to it.  Sphinx then reports
``document isn't included in any toctree`` for a page nobody edited.

The checker looks at both halves of that:

* the **outcome** -- every module and subpackage appears in its package's
  toctree, and every toctree entry has a module behind it;
* the **mechanism** -- ``make`` treats a package index as out of date when a
  module beside it changes, which is what keeps the outcome true over time.

The mechanism half runs ``make --dry-run --what-if``, so it needs no probe file
and leaves the working tree untouched.

This is a maintenance command, not a unit test: it reads the Makefile and drives
``make``, both of which the pytest boundary rules keep out of ``test/``.

Example::

    $ python tools/check_api_doc_toctree.py --check
    API documentation toctrees list every module.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Set

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the package sources live, relative to the repository root.
_SOURCE_PACKAGE = Path("pyfcstm")

#: Where ``auto_rst.py`` writes the generated pages.
_DOC_ROOT = Path("docs/source/api_doc")

#: The module ``auto_rst.py`` excludes by name rather than by shape.
#:
#: Build metadata is generated at package time, so it has nothing stable to
#: document.  ``print_package_toctree`` names the file directly.
_EXCLUDED_MODULE_FILE = "build_info.py"

#: The modules whose change the mechanism check pretends to have just made.
#:
#: Any module beside a package index would do.  Two are used rather than one
#: because the rule they exercise is a pattern rule: a change that fixes it for
#: a top-level package can still miss a nested one, and a single probe would
#: pass while half the tree stayed broken.  ``pyfcstm/bmc/`` is the package that
#: most recently gained modules; ``pyfcstm/entry/simulate/`` is nested.
_PROBE_MODULES = (
    Path("pyfcstm/bmc/proof.py"),
    Path("pyfcstm/entry/simulate/repl.py"),
)


class ToctreeCheckFailure(RuntimeError):
    """Raised when the generated API documentation and the sources disagree."""


def _module_pages(package: Path) -> Set[str]:
    """Return the page names ``auto_rst.py`` puts in a package's toctree.

    Mirrors ``print_package_toctree``: a module joins the toctree when it is a
    ``.py`` file that is neither dunder nor private, and is not the generated
    build metadata.  A subdirectory joins whenever it is a package, private or
    not -- the underscore rule is applied to modules only, so ``_selfcheck``
    still gets a listed index page.

    :param package: Absolute path to a package directory.
    :type package: pathlib.Path
    :return: Toctree entries the package's ``index.rst`` must contain.
    :rtype: Set[str]
    """
    expected: Set[str] = set()
    for child in sorted(package.iterdir()):
        if child.is_dir():
            if (child / "__init__.py").exists():
                expected.add("%s/index" % child.name)
            continue
        if child.suffix != ".py":
            continue
        if child.name == _EXCLUDED_MODULE_FILE:
            continue
        if child.stem.startswith("_"):
            continue
        expected.add(child.stem)
    return expected


def _toctree_entries(page: Path) -> Set[str]:
    """Return the entries listed in a generated page's toctrees.

    :param page: Absolute path to a generated ``index.rst``.
    :type page: pathlib.Path
    :return: Entry names, without the leading indentation.
    :rtype: Set[str]
    """
    entries: Set[str] = set()
    inside = False
    for line in page.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(".. toctree::"):
            inside = True
            continue
        if not inside:
            continue
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            inside = False
            continue
        stripped = line.strip()
        if stripped.startswith(":"):
            continue
        entries.add(stripped)
    return entries


def _packages() -> List[Path]:
    """Return every package whose index page owns a toctree.

    The root package is excluded: its children are listed by
    ``auto_rst_top_index.py`` in the language-specific ``api_doc_en.rst`` and
    ``api_doc_zh.rst`` landing pages, so ``api_doc/index.rst`` carries only the
    root module's own documentation and has no toctree to compare against.

    :return: Absolute paths to package directories, shallowest first.
    :rtype: List[pathlib.Path]
    """
    root = _REPO_ROOT / _SOURCE_PACKAGE
    return [
        path.parent for path in sorted(root.rglob("__init__.py")) if path.parent != root
    ]


def _landing_pages() -> List[Path]:
    """Return the language landing pages that list the root package's children.

    :return: Absolute paths to the generated landing pages that exist.
    :rtype: List[pathlib.Path]
    """
    source = _REPO_ROOT / "docs/source"
    return [
        source / name
        for name in ("api_doc_en.rst", "api_doc_zh.rst")
        if (source / name).exists()
    ]


def _check_toctrees() -> List[str]:
    """Compare every package's sources against its generated toctree.

    :return: One message per disagreement, empty when the pages are complete.
    :rtype: List[str]
    """
    problems: List[str] = []
    for package in _packages():
        relative = package.relative_to(_REPO_ROOT / _SOURCE_PACKAGE)
        page = _REPO_ROOT / _DOC_ROOT / relative / "index.rst"
        if not page.exists():
            problems.append(
                "%s has no generated index page; run make rst_auto."
                % (_SOURCE_PACKAGE / relative).as_posix()
            )
            continue
        expected = _module_pages(package)
        listed = _toctree_entries(page)
        for missing in sorted(expected - listed):
            problems.append(
                "%s does not list %s, so that page is orphaned in the toctree."
                % (page.relative_to(_REPO_ROOT).as_posix(), missing)
            )
        for extra in sorted(listed - expected):
            problems.append(
                "%s lists %s, which has no module behind it."
                % (page.relative_to(_REPO_ROOT).as_posix(), extra)
            )

    # The root package's children live on the language landing pages rather than
    # in a toctree of their own, and a new subpackage is as easy to lose there.
    # A package whose generated index declares itself an orphan is deliberately
    # outside the public tree, so the landing pages are right to omit it.  The
    # marker is read from the page rather than matched against a package name,
    # so the two stay in step when auto_rst.py changes which package it is.
    source_root = _REPO_ROOT / _SOURCE_PACKAGE
    required = set()
    for package in _packages():
        if package.parent != source_root:
            continue
        page = _REPO_ROOT / _DOC_ROOT / package.name / "index.rst"
        if page.exists() and ":orphan:" in page.read_text(encoding="utf-8"):
            continue
        required.add("api_doc/%s/index" % package.name)
    for landing in _landing_pages():
        listed = _toctree_entries(landing)
        for missing in sorted(required - listed):
            problems.append(
                "%s does not list %s, so that package is unreachable."
                % (landing.relative_to(_REPO_ROOT).as_posix(), missing)
            )
    return problems


def _make_targets(probe: Optional[Path] = None) -> str:
    """Return what ``make rst_auto`` would do, optionally after a pretend edit.

    ``--dry-run`` and ``--what-if`` both leave the working tree alone, so this
    can be asked twice without changing anything between the answers.

    :param probe: Repository-relative path to pretend was just modified,
        defaults to ``None`` for the plain question
    :type probe: pathlib.Path, optional
    :return: The commands ``make`` reported, or an empty string on failure.
    :rtype: str
    """
    command = ["make", "--dry-run"]
    if probe is not None:
        command.append("--what-if=%s" % probe.as_posix())
    command.append("rst_auto")
    completed = subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def _check_rebuild_rule() -> List[str]:
    """Confirm a package index is rebuilt when a module beside it changes.

    The outcome check above can be satisfied by hand, or by a full rebuild that
    happened for an unrelated reason.  This one asks whether the build system
    will keep it satisfied: a package index that does not depend on its modules
    goes stale silently, and the next module to land is orphaned again.

    The pretend edit only answers the question when the index is otherwise up to
    date.  Every package index also lists ``Makefile`` and ``auto_rst.py`` among
    its prerequisites, so editing either one makes all of them stale and the
    probe would appear to succeed no matter what it depends on.  That is not a
    hypothetical: it is what happened the first time this check was mutated to
    confirm it fails when the dependency is removed.  So the plain question is
    asked first, and a dirty baseline is reported as inconclusive rather than
    silently read as a pass.

    :return: One message per probe whose dependency is missing or unprovable,
        empty otherwise.
    :rtype: List[str]
    """
    problems: List[str] = []
    baseline = _make_targets()
    for probe in _PROBE_MODULES:
        if not (_REPO_ROOT / probe).exists():
            problems.append(
                "%s no longer exists, so the rebuild rule cannot be checked; "
                "point _PROBE_MODULES at another module beside a package index."
                % probe.as_posix()
            )
            continue
        package_index = (
            _DOC_ROOT / probe.parent.relative_to(_SOURCE_PACKAGE) / "index.rst"
        ).as_posix()
        if package_index in baseline:
            problems.append(
                "%s is already out of date before the pretend edit, so the "
                "rebuild rule cannot be proved either way.  Run make rst_auto and "
                "commit any regenerated pages, then check again.  In a fresh "
                "checkout or worktree this says nothing about the content: git "
                "writes files in no particular order, so a generated page can land "
                "with an older timestamp than its source and make calls it stale.  "
                "There, make rst_auto refreshes the timestamps and reports no diff."
                % package_index
            )
            continue
        if package_index in _make_targets(probe):
            continue
        problems.append(
            "Changing %s does not make %s out of date, so a new module beside "
            "it would be generated without entering the toctree.  The package "
            "index rule needs the package's modules as prerequisites."
            % (probe.as_posix(), package_index)
        )
    return problems


def _self_check() -> None:
    """Confirm the checker's own reading of the sources still works.

    :return: ``None``.
    :rtype: None
    :raises ToctreeCheckFailure: If the checker cannot see the tree it audits.
    """
    packages = _packages()
    if len(packages) < 2:
        raise ToctreeCheckFailure(
            "Found %d package under %s; the checker expects the source tree."
            % (len(packages), _SOURCE_PACKAGE.as_posix())
        )
    landing = _landing_pages()
    if not landing:
        raise ToctreeCheckFailure(
            "Neither api_doc_en.rst nor api_doc_zh.rst exists; run "
            "make rst_auto before checking toctrees."
        )
    # Reading one real toctree proves the parser works against the generated
    # shape rather than against an assumed one.
    for page in landing:
        if not _toctree_entries(page):
            raise ToctreeCheckFailure(
                "%s has no toctree entries, so the parser is not reading it."
                % page.relative_to(_REPO_ROOT).as_posix()
            )


def check() -> None:
    """Validate the generated API documentation against the sources.

    :return: ``None``.
    :rtype: None
    :raises ToctreeCheckFailure: If a module is orphaned or the rebuild rule
        would let the next one become orphaned.
    """
    problems = _check_toctrees() + _check_rebuild_rule()
    if problems:
        raise ToctreeCheckFailure("\n".join("- %s" % item for item in problems))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the checker from the command line.

    :param argv: Argument list, defaults to ``None`` for ``sys.argv[1:]``
    :type argv: Sequence[str], optional
    :return: ``0`` when the documentation is complete, ``1`` otherwise.
    :rtype: int

    Example::

        $ python tools/check_api_doc_toctree.py --check
        API documentation toctrees list every module.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)
    if not args.check and not args.self_check:
        parser.error("Pass --check, --self-check, or both.")
    if args.self_check:
        try:
            _self_check()
        except ToctreeCheckFailure as err:
            # The tree the checker audits is not the tree it was written for.
            print("API documentation toctree self-check failed:\n%s" % err)
            return 1
        print("API documentation toctree checker reads the source tree.")
    if args.check:
        try:
            check()
        except ToctreeCheckFailure as err:
            # A module is orphaned, or the build rule would orphan the next one.
            print("API documentation toctrees are out of date:\n%s" % err)
            return 1
        print("API documentation toctrees list every module.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
