"""
Report handlers opened while a resource is already held.

From CPython 3.11 a nested ``try:`` line compiles to a ``NOP`` that no
``co_exceptiontable`` entry covers, so entering an inner ``try`` while holding a
resource escapes the outer handler and the owner's ``finally`` does not run at
all. The same source is safe on 3.7-3.10, which is why this is checked
structurally rather than only by the interrupt-injection tests under
[test/](../test): those observe nothing on the half of the supported range where
the shape is harmless, and they skip entirely on Windows and macOS because they
need ``/proc/self/fd``.

The command lives outside the pytest suite deliberately. It scans production
source text to prove a property about the implementation, which the "Public API
And Normal-Path Test Boundary" section of ``CLAUDE.md`` excludes from the unit
suite and directs to a maintenance command, exactly as
``tools/check_test_boundary.py`` is.

The roster is discovered, not listed: any function that calls an acquisition
primitive is audited. A hand-maintained list cannot fail for a site added after
it was written, which is the failure mode this guard exists to prevent.

Example::

    $ python tools/check_resource_ownership.py
    $ python tools/check_resource_ownership.py --check
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import List, NamedTuple

#: Calls that hand back something needing an explicit release. Attribute access
#: is matched on the final name, so ``os.open`` and ``tempfile.mkstemp`` match
#: whatever alias the module imported them under.
ACQUISITION_PRIMITIVES = frozenset(
    {
        "Popen",
        "TemporaryDirectory",
        "TemporaryFile",
        "NamedTemporaryFile",
        "mkdtemp",
        "mkstemp",
        "fdopen",
        "open",
        "socket",
    }
)

#: Generated parsers are produced by ANTLR and exempt, as in the exception policy.
EXEMPT_DIRECTORIES = ("dsl/grammar", "bmc/grammar")


class Finding(NamedTuple):
    """
    One handler entered while the enclosing handler already holds a resource.

    :param path: Repository-relative path of the offending file.
    :type path: str
    :param line: Line of the inner ``try``.
    :type line: int
    :param function: Name of the function the inner ``try`` sits in.
    :type function: str
    :param held: Acquisition calls the outer ``try`` made before that line.
    :type held: tuple
    """

    path: str
    line: int
    function: str
    held: tuple

    def describe(self) -> str:
        """
        Render this finding as one reviewer-readable line.

        :return: The rendered line.
        :rtype: str
        """
        return "{}:{}: {} enters a handler while holding {}".format(
            self.path, self.line, self.function, ", ".join(self.held)
        )


def repository_root() -> Path:
    """
    Return the repository root, derived from this file's location.

    :return: Absolute path of the repository root.
    :rtype: pathlib.Path
    """
    return Path(__file__).resolve().parent.parent


def _called_name(node: ast.Call):
    """Return the final name of a call target, or ``None`` for a computed one."""
    target = node.func
    return getattr(target, "attr", None) or getattr(target, "id", None)


def _with_owned_calls(scope: ast.AST) -> set:
    """Return the call nodes a ``with`` statement owns; those need no handler."""
    owned = set()
    for node in ast.walk(scope):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                owned.update(
                    inner
                    for inner in ast.walk(item.context_expr)
                    if isinstance(inner, ast.Call)
                )
    return owned


def _acquisitions_held_at(scope: ast.AST, inner: ast.Try) -> tuple:
    """Return acquisitions live in ``scope`` when ``inner`` is entered.

    Scoped to the whole enclosing function rather than the outer handler's body:
    the worst shape is a resource acquired *before* the outer ``try`` and then
    held across an inner one, which a body-only scan cannot see.

    Two exclusions keep it honest. A call ``with`` owns is already released by
    the statement that made it, and a call inside ``inner`` itself is acquired
    after entry, not held across it.
    """
    inside_inner = {node for node in ast.walk(inner)}
    owned_by_with = _with_owned_calls(scope)
    found = []
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call) or node in inside_inner:
            continue
        if node in owned_by_with or node.lineno >= inner.lineno:
            continue
        name = _called_name(node)
        if name in ACQUISITION_PRIMITIVES:
            found.append("{}() at line {}".format(name, node.lineno))
    return tuple(found)


def scan_source(source: str, path: str) -> List[Finding]:
    """
    Report every handler in ``source`` opened while a resource is held.

    :param source: Python source text.
    :type source: str
    :param path: Label used in the findings.
    :type path: str
    :return: Findings, in source order.
    :rtype: list
    :raises SyntaxError: If ``source`` does not parse.
    """
    tree = ast.parse(source)
    scopes = {}
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(parent):
                scopes.setdefault(child, parent)
    findings = []
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.Try):
            continue
        # Only the outer handler's *body* keeps a resource live across an inner
        # handler; its own except/finally clauses are the release path, where an
        # interrupt is the unavoidable in-cleanup case rather than this defect.
        for statement in outer.body:
            for node in ast.walk(statement):
                if not isinstance(node, ast.Try) or node is outer:
                    continue
                scope = scopes.get(node, tree)
                held = _acquisitions_held_at(scope, node)
                if held:
                    findings.append(
                        Finding(
                            path=path,
                            line=node.lineno,
                            function=getattr(scope, "name", "<module>"),
                            held=held,
                        )
                    )
    return sorted(findings, key=lambda finding: (finding.path, finding.line))


def scan_tree(root: Path) -> List[Finding]:
    """
    Scan every non-generated module under ``pyfcstm``.

    :param root: Repository root.
    :type root: pathlib.Path
    :return: Findings across the package.
    :rtype: list
    """
    findings = []
    package = root / "pyfcstm"
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if any(part in relative for part in EXEMPT_DIRECTORIES):
            continue
        findings.extend(scan_source(path.read_text(encoding="utf-8"), relative))
    return findings


#: A shape the scanner must reject, so that a green run means something.
_PLANTED_VIOLATION = '''
import tempfile


def writer(path):
    handle = None
    try:
        handle = tempfile.NamedTemporaryFile(dir=path)
        try:
            handle.write(b"payload")
        except OSError:
            pass
    finally:
        if handle is not None:
            handle.close()
'''

#: The same function with the inner handler sunk out, which must pass.
_PLANTED_CLEAN = '''
import tempfile


def _write(handle):
    try:
        handle.write(b"payload")
    except OSError:
        pass


def writer(path):
    handle = None
    try:
        handle = tempfile.NamedTemporaryFile(dir=path)
        _write(handle)
    finally:
        if handle is not None:
            handle.close()
'''


def self_check() -> int:
    """
    Prove the scanner can fail, then prove it does not fire on the clean shape.

    :return: ``0`` when both halves behave, ``1`` otherwise.
    :rtype: int
    """
    violations = scan_source(_PLANTED_VIOLATION, "<planted>")
    if len(violations) != 1:
        print(
            "resource ownership self-check FAILED: planted violation produced "
            "{} findings, expected 1".format(len(violations))
        )
        return 1
    clean = scan_source(_PLANTED_CLEAN, "<planted-clean>")
    if clean:
        print(
            "resource ownership self-check FAILED: clean shape produced "
            "{} findings, expected 0".format(len(clean))
        )
        return 1
    print("resource ownership self-check passed")
    return 0


def run_check(root: Path) -> int:
    """
    Scan the package and report any handler opened while holding a resource.

    :param root: Repository root to scan.
    :type root: pathlib.Path
    :return: ``0`` when the package is clean, ``1`` otherwise.
    :rtype: int
    """
    findings = scan_tree(root)
    if not findings:
        print("resource ownership check passed: no violations found")
        return 0
    print("resource ownership check FAILED: {} violation(s)".format(len(findings)))
    for finding in findings:
        print("  " + finding.describe())
    print(
        "  see rule 7 of the Exception Handling Policy in CLAUDE.md: use `with` "
        "for the outer ownership, or sink the inner handler into its own function"
    )
    return 1


def main(argv=None) -> int:
    """
    Command-line entry point.

    :param argv: Argument vector, defaults to ``None`` for ``sys.argv``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="Report handlers opened while a resource is already held."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repository_root()),
        help="Repository root to scan. Defaults to the parent of this tools directory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the scanner's own positive and negative controls and exit.",
    )
    args = parser.parse_args(argv)
    if args.check:
        return self_check()
    return run_check(Path(args.repo_root).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
