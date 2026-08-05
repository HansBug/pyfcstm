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


def _acquisition_calls(scope: ast.AST) -> list:
    """Return the acquisition calls in ``scope`` that no ``with`` already owns."""
    owned_by_with = _with_owned_calls(scope)
    return [
        node
        for node in ast.walk(scope)
        if isinstance(node, ast.Call)
        and node not in owned_by_with
        and _called_name(node) in ACQUISITION_PRIMITIVES
    ]


def _resources_at_risk(scope: ast.AST, inner: ast.Try) -> tuple:
    """Return the acquisitions the outer ``finally`` would fail to release.

    The predicate is derived from measurement, not from intuition, and neither
    obvious form of it is right.

    "Held when the inner ``try`` is entered" misses the shape this guard exists
    for: the three context managers acquired *inside* their inner ``try`` and a
    later line in the same body escaped while holding the result.

    "Anything the function acquires" over-reports the retry idiom, where the
    acquisition is the last statement before ``break`` and nothing afterwards
    holds it -- swept on 3.10/3.11/3.12/3.14, that shape leaks only inside its
    own ``finally``, which no Python version survives.

    What separates them is whether any line still runs while the resource is
    live: an acquisition before the inner ``try``, or one inside it with a
    statement after it.
    """
    inside_inner = {node for node in ast.walk(inner)}
    at_risk = []
    for node in _acquisition_calls(scope):
        label = "{}() at line {}".format(_called_name(node), node.lineno)
        if node not in inside_inner:
            if node.lineno < inner.lineno:
                at_risk.append(label + ", held on entry")
            continue
        # inner.body only: a ``continue`` in the handler runs after the
        # acquisition failed, not while its result is live.
        last = max(
            (
                statement.lineno
                for entry in inner.body
                for statement in ast.walk(entry)
                if _is_statement(statement)
            ),
            default=node.lineno,
        )
        if last > node.lineno:
            at_risk.append(label + ", live for the rest of the handler")
    return tuple(at_risk)


def _is_statement(node: ast.AST) -> bool:
    """Return whether ``node`` is an executable statement with a line number."""
    return isinstance(node, ast.stmt) and not isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    )


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
    # Innermost enclosing function, not the outermost: walking outward-in with
    # setdefault bound every node to the top-level function, so an acquisition in
    # one nested helper read as held by a handler in a sibling helper.
    scopes = {}
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(parent):
                scopes[child] = parent
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
                held = _resources_at_risk(scope, node)
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

#: The shape a held-at-entry predicate scores zero on: acquired *inside* the
#: inner handler, with a statement after it that runs while the result is live.
#: This is what the three context managers in pyfcstm/_selfcheck/process.py did,
#: and it was measured leaking on 3.11, 3.12 and 3.14.
_PLANTED_VIOLATION_INSIDE = '''
import os
import tempfile


def writer(payload):
    directory = None
    try:
        try:
            directory = tempfile.mkdtemp()
            with open(os.path.join(directory, "f"), "wb") as handle:
                handle.write(payload)
        except OSError:
            directory = None
        return directory
    finally:
        pass
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


#: A nested handler entered with nothing held. Real code does this -- the retry
#: loop in ``pyfcstm/diagram/api.py`` opens its descriptor *inside* the inner
#: ``try`` -- and it must not be flagged. Without this case the negative control
#: never exercises the held-resource computation at all, so a scanner mutated to
#: report everything would still pass its own self-check.
_PLANTED_NESTED_BUT_UNHELD = '''
import os


def retry(name, flags):
    handle = -1
    try:
        for _ in range(3):
            try:
                handle = os.open(name, flags)
            except FileExistsError:
                continue
            break
    finally:
        if handle != -1:
            os.close(handle)
'''


#: A floor on file discovery. Without it, mutating ``scan_tree`` to return early
#: -- or pointing it at a directory that does not exist, or exempting the whole
#: package -- leaves the scanner reporting a clean tree and ``--check`` agreeing.
_MINIMUM_SCANNED_MODULES = 40


def _scan_tree_reached(root: Path) -> int:
    """Return how many modules :func:`scan_tree` would actually parse."""
    package = root / "pyfcstm"
    return sum(
        1
        for path in package.rglob("*.py")
        if not any(part in path.relative_to(root).as_posix() for part in EXEMPT_DIRECTORIES)
    )


def self_check() -> int:
    """
    Prove the scanner can fail, then prove it does not fire on the clean shape.

    :return: ``0`` when both halves behave, ``1`` otherwise.
    :rtype: int
    """
    for label, sample in (
        ("held-on-entry", _PLANTED_VIOLATION),
        ("acquired-inside", _PLANTED_VIOLATION_INSIDE),
    ):
        violations = scan_source(sample, "<planted-{}>".format(label))
        if len(violations) != 1:
            print(
                "resource ownership self-check FAILED: planted {} violation "
                "produced {} findings, expected 1".format(label, len(violations))
            )
            return 1
    for label, sample in (
        ("clean", _PLANTED_CLEAN),
        ("nested-but-unheld", _PLANTED_NESTED_BUT_UNHELD),
    ):
        findings = scan_source(sample, "<planted-{}>".format(label))
        if findings:
            print(
                "resource ownership self-check FAILED: {} shape produced "
                "{} findings, expected 0".format(label, len(findings))
            )
            return 1
    reached = _scan_tree_reached(repository_root())
    if reached < _MINIMUM_SCANNED_MODULES:
        print(
            "resource ownership self-check FAILED: file discovery reached {} "
            "modules, expected at least {}".format(reached, _MINIMUM_SCANNED_MODULES)
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
