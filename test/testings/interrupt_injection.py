"""
Per-line interrupt injection for resource-ownership regression tests.

A resource acquired outside the handler that releases it has a window in which
an interrupt leaks it. The window is usually one or two bytecodes wide, so real
signals almost never land in it; :func:`sys.settrace` line events reach every
line and therefore expose the window deterministically.

The harness deliberately separates two kinds of finding:

* **Body windows** — an injection point in ordinary code that leaves a resource
  unreleased. These are the defects worth failing a test over.
* **In-cleanup points** — an injection point inside a ``finally`` body, which
  skips the rest of that cleanup. No Python program can survive this, so these
  are reported separately rather than treated as failures.

Example::

    >>> report = inject_per_line(target_function, lambda: target_function(arg))
    >>> report.body_windows
    []
"""

import ast
import inspect
import os
import shutil
import sys
import tempfile
import textwrap
from typing import Callable, Dict, List, NamedTuple, Optional, Set

__all__ = [
    "InjectionPoint",
    "InjectionReport",
    "cleanup_line_numbers",
    "inject_per_line",
    "open_descriptors",
]


class InjectionPoint(NamedTuple):
    """
    One injection point that left a resource behind.

    :param offset: Line offset from the first line of the traced function.
    :type offset: int
    :param descriptors: Descriptor numbers that stayed open.
    :type descriptors: tuple
    :param residues: Filesystem paths that stayed behind.
    :type residues: tuple
    :param in_cleanup: Whether the injected line sits inside a ``finally`` body.
    :type in_cleanup: bool
    """

    offset: int
    descriptors: tuple
    residues: tuple
    in_cleanup: bool


class InjectionReport(NamedTuple):
    """
    Outcome of one per-line injection sweep.

    :param points_reached: Number of lines that the injection actually reached.
    :type points_reached: int
    :param body_windows: Points in ordinary code that leaked; these are defects.
    :type body_windows: list
    :param in_cleanup: Points inside a ``finally`` body that leaked.
    :type in_cleanup: list
    """

    points_reached: int
    body_windows: List[InjectionPoint]
    in_cleanup: List[InjectionPoint]

    def describe(self) -> str:
        """
        Render the body windows for an assertion message.

        :return: One human-readable line per leaking body window.
        :rtype: str
        """
        return "\n".join(
            "  +{} descriptors={} residues={}".format(
                point.offset, list(point.descriptors), list(point.residues)
            )
            for point in self.body_windows
        )


def open_descriptors() -> Dict[int, str]:
    """
    Map this process's open descriptors to their targets, where observable.

    :return: Descriptor number to link target; empty when ``/proc`` is absent.
    :rtype: dict
    """
    found = {}
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        # Only Linux exposes /proc/self/fd; callers skip on other platforms.
        return found
    for name in names:
        try:
            number = int(name)
            target = os.readlink("/proc/self/fd/" + name)
        except (OSError, ValueError):
            # The scan's own descriptor closes while the listing is walked.
            continue
        if target.startswith("/proc/") and target.endswith("/fd"):
            continue
        found[number] = target
    return found


def cleanup_line_numbers(function: Callable) -> Set[int]:
    """
    Collect the absolute line numbers inside every ``finally`` body of a function.

    :param function: The function whose source should be scanned.
    :type function: collections.abc.Callable
    :return: Absolute line numbers belonging to a ``finally`` body.
    :rtype: set
    """
    source, first = inspect.getsourcelines(function)
    tree = ast.parse(textwrap.dedent("".join(source)))
    inside = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for statement in node.finalbody:
            for element in ast.walk(statement):
                start = getattr(element, "lineno", None)
                if start is None:
                    continue
                end = getattr(element, "end_lineno", None) or start
                inside.update(range(start + first - 1, end + first))
    return inside


def inject_per_line(
    function: Callable,
    invoke: Callable[[], object],
    residues: Optional[Callable[[], Set]] = None,
    release_residues: Optional[Callable[[Set], None]] = None,
) -> InjectionReport:
    """
    Raise :exc:`KeyboardInterrupt` at each line of ``function`` and record leaks.

    Each line is injected in a separate call, so the points are independent.
    Anything left behind is released before the next point runs, keeping the
    measurements from accumulating into one another.

    :param function: The function to trace; its own code object is targeted, so
        interrupts raised in callees are not injected.
    :type function: collections.abc.Callable
    :param invoke: Zero-argument callable that performs one full call.
    :type invoke: collections.abc.Callable
    :param residues: Callable returning the resources that count as residue,
        defaults to ``None`` for descriptor-only checks. Filesystem paths are
        released by default; any other token needs ``release_residues``.
    :type residues: collections.abc.Callable, optional
    :param release_residues: Callable releasing the residues one point leaked,
        defaults to ``None`` for path removal.
    :type release_residues: collections.abc.Callable, optional
    :return: The classified sweep result.
    :rtype: InjectionReport
    """
    # contextlib.contextmanager wraps the generator, and it is the generator's
    # body that acquires and releases; tracing the wrapper would see one line.
    function = getattr(function, "__wrapped__", function)
    code = function.__code__
    in_cleanup = cleanup_line_numbers(function)
    residues = residues or (lambda: set())
    release_residues = release_residues or _remove_paths
    lines = sorted({line for _, _, line in code.co_lines() if line is not None})
    reached = 0
    leaks = []
    for line in lines:
        before_descriptors = open_descriptors()
        before_residues = set(residues())
        fired = _invoke_with_injection(code, invoke, line)
        if not fired:
            continue
        reached += 1
        leaked_descriptors = {
            descriptor: target
            for descriptor, target in open_descriptors().items()
            if descriptor not in before_descriptors
        }
        leaked_residues = set(residues()) - before_residues
        if leaked_descriptors or leaked_residues:
            leaks.append(
                InjectionPoint(
                    offset=line - code.co_firstlineno,
                    descriptors=tuple(sorted(leaked_descriptors)),
                    residues=tuple(sorted(leaked_residues)),
                    in_cleanup=line in in_cleanup,
                )
            )
        _close_descriptors(leaked_descriptors)
        release_residues(leaked_residues)
    return InjectionReport(
        points_reached=reached,
        body_windows=[point for point in leaks if not point.in_cleanup],
        in_cleanup=[point for point in leaks if point.in_cleanup],
    )


def _invoke_with_injection(code, invoke: Callable[[], object], line: int) -> bool:
    """Run ``invoke`` once, raising at ``line`` of ``code``; report whether it fired."""
    fired = []

    def trace_line(frame, event, arg):
        if event == "line" and frame.f_lineno == line and not fired:
            fired.append(True)
            raise KeyboardInterrupt("injected at line {}".format(line))
        return trace_line

    def trace_call(frame, event, arg):
        if event == "call" and frame.f_code is code:
            return trace_line
        return None

    sys.settrace(trace_call)
    try:
        invoke()
    except BaseException:
        # Every injection unwinds the call; the leak check below is the result.
        pass
    finally:
        sys.settrace(None)
    return bool(fired)


def _is_temporary_target(target: str) -> bool:
    """Return whether a descriptor's target is a temporary artifact.

    Releasing an arbitrary descriptor that merely appeared during a traced call
    is not safe: the call may have triggered a lazy import that opened and
    cached something long-lived, and closing that would break every later test
    in the process. Every resource this harness is meant to observe is a
    temporary file, so the release is confined to those.

    :param target: The ``/proc/self/fd`` link target.
    :type target: str
    :return: Whether the descriptor may be closed by the harness.
    :rtype: bool
    """
    if target.endswith(" (deleted)"):
        return True
    root = os.path.realpath(tempfile.gettempdir())
    return os.path.realpath(target).startswith(root + os.sep)


def _close_descriptors(descriptors: Dict[int, str]) -> None:
    """Close the temporary-file descriptors one injection point leaked."""
    for descriptor, target in descriptors.items():
        if not _is_temporary_target(target):
            continue
        try:
            os.close(descriptor)
        except OSError:
            # Already closed by an interpreter-level finalizer.
            pass


def _remove_paths(residues: Set[str]) -> None:
    """Remove the filesystem residue one injection point left behind."""
    for path in residues:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        except OSError:
            # An already-removed path, or one whose parent is gone.
            pass
