"""
Run the repository doctest gate and enforce the known-failure ratchet.

This repo-local tool executes ``pytest --doctest-modules`` over the production
package and compares the resulting node-id sets against a checked-in
known-failure ledger. It is intentionally outside the ``pytest -m unittest``
suite: the gate validates that packaged docstrings tell the truth, which is a
documentation-correctness contract rather than a unit-test contract.

The module contains:

* :class:`DoctestGateError` - Raised when the gate cannot produce a verdict
* :func:`require_installed_distribution` - Reject a bare checkout early
* :func:`require_usable_run` - Reject a pytest run that enumerated nothing
* :func:`load_ledger` - Parse the known-failure ledger file
* :func:`normalize_scope` - Make in-repository absolute scope paths relative
* :func:`filter_ledger_to_scope` - Restrict the ledger to the current scope
* :func:`select_changed_scope` - Reduce a changed-file list to gate paths
* :func:`classify_outcome` - Three-way comparison driving the ratchet
* :func:`build_pytest_command` - Build the pytest argv for one gate run
* :func:`main` - Command-line entry point

.. note::
   The ratchet compares node-id sets instead of trusting pytest exit codes.
   A ledger entry that no longer matches any collected node is a hard error,
   because pytest silently ignores unmatched ``--deselect`` arguments and would
   otherwise turn a renamed docstring into a false green.

Example::

    $ python tools/run_doctests.py --check
    $ python tools/run_doctests.py
    $ python tools/run_doctests.py --scope pyfcstm/bmc --scope pyfcstm/verify
    $ python tools/run_doctests.py --changed-files /tmp/changed.txt
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from shlex import quote as shlex_quote
from typing import Dict, List, Optional, Sequence

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SCOPE = ("pyfcstm",)
DEFAULT_LEDGER = os.path.join("tools", "doctest_known_failures.txt")

#: Option flags shared with ``sphinx.ext.doctest`` defaults so a docstring that
#: passes this gate also passes the Sphinx ``doctest`` builder.
DEFAULT_OPTION_FLAGS = (
    "ELLIPSIS",
    "IGNORE_EXCEPTION_DETAIL",
    "DONT_ACCEPT_TRUE_FOR_1",
)


class DoctestGateError(Exception):
    """
    Raised when the doctest gate cannot produce a trustworthy verdict.

    This covers unreadable ledger files, malformed plugin output, a pytest
    subprocess that failed before writing its outcome file, and pytest
    arguments that would silently corrupt the ratchet comparison.
    """


#: ``pytest-xdist`` collects items inside worker processes, so the controller
#: process running :mod:`tools.doctest_plugin` records an empty collected set
#: and reports every ledger entry as stale. The whole gate takes a couple of
#: seconds, so the fix is to reject parallelism rather than merge worker files.
_REJECTED_PYTEST_ARGS = ("-n", "--numprocesses", "--dist")


def reject_unsupported_pytest_args(pytest_args: Sequence[str]) -> None:
    """
    Reject pytest passthrough arguments the ratchet cannot support.

    :param pytest_args: Extra pytest arguments requested by the caller.
    :type pytest_args: collections.abc.Sequence[str]
    :return: ``None``.
    :rtype: None
    :raises DoctestGateError: If a rejected argument is present.

    Example::

        >>> reject_unsupported_pytest_args(['--tb=long'])
        >>> reject_unsupported_pytest_args(['-n', '4'])
        Traceback (most recent call last):
            ...
        DoctestGateError: doctest gate does not support pytest-xdist ('-n'); ...
    """
    for argument in pytest_args:
        head = argument.split("=", 1)[0]
        if head in _REJECTED_PYTEST_ARGS:
            raise DoctestGateError(
                "doctest gate does not support pytest-xdist ({0!r}); the "
                "ratchet needs a single collecting process and the whole "
                "gate runs in seconds".format(head)
            )


def require_installed_distribution(name: str = "pyfcstm") -> None:
    """
    Fail early when the package under documentation is not installed.

    Some docstrings document behavior that only exists in an installed
    distribution. ``pyfcstm.highlight.pygments_lexer`` is the concrete case: its
    examples call ``get_lexer_by_name("fcstm")``, which Pygments resolves through
    the ``pygments.lexers`` entry point declared in ``setup.py``. A bare checkout
    can import the package but registers no entry point, so those examples raise
    ``ClassNotFound`` and the gate reports failures no reader would ever see.

    :param name: Distribution name to look for, defaults to ``'pyfcstm'``.
    :type name: str, optional
    :return: ``None``.
    :rtype: None
    :raises DoctestGateError: If the distribution is not installed.

    Example::

        >>> require_installed_distribution()
        >>> require_installed_distribution('no-such-distribution-xyz')
        Traceback (most recent call last):
            ...
        DoctestGateError: no-such-distribution-xyz is not installed ...
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        # Python 3.7 ships no importlib.metadata. The gate itself runs on 3.11,
        # and this probe only improves an error message, so skip it there.
        return
    try:
        version(name)
    except PackageNotFoundError:
        raise DoctestGateError(
            "{0} is not installed in this environment, so docstrings that rely "
            "on entry points (the Pygments 'fcstm' lexer) fail for a reason no "
            "reader would hit. Run `pip install -e .` and retry.".format(name)
        )


#: pytest exit codes from which a ratchet verdict can be derived: everything
#: passed, or some tests failed. Interruption (2), internal error (3) and usage
#: error (4) all leave the recorded node-id sets incomplete, which would
#: otherwise read as "the whole ledger went stale".
_VERDICT_EXIT_CODES = (0, 1)

#: pytest's exit code for "the paths resolved but held nothing to run". It is a
#: mistake for an explicit scope and an ordinary outcome for a changed-file list
#: naming only modules without examples, so the two cases are told apart.
_NOTHING_COLLECTED_EXIT_CODE = 5


def require_usable_run(
        pytest_status: int,
        collected: Sequence[str],
        allow_empty: bool = False,
) -> bool:
    """
    Decide whether a pytest run can support a ratchet verdict.

    Ignoring pytest's exit code makes a mistyped or renamed scope report success:
    pytest exits 4 without collecting anything, the plugin records empty sets, and
    the three-way comparison then finds no unexpected failure. The gate would
    print ``0 doctest(s) collected`` and exit 0 -- the exact silent pass this
    design exists to prevent.

    Collecting nothing is not always a mistake though. A pull request may touch
    only modules that carry no examples, and 33 of the 161 modules under
    ``pyfcstm`` are in that category, so ``--changed-files`` passes
    ``allow_empty=True`` and gets a clean skip instead of a failure.

    :param pytest_status: Exit code returned by the pytest subprocess.
    :type pytest_status: int
    :param collected: Doctest node ids the plugin recorded.
    :type collected: collections.abc.Sequence[str]
    :param allow_empty: Whether an empty collection is an acceptable outcome,
        defaults to ``False``.
    :type allow_empty: bool, optional
    :return: ``True`` when there are node-id sets to compare, ``False`` when the
        run legitimately collected nothing.
    :rtype: bool
    :raises DoctestGateError: If the run cannot support a verdict.

    Example::

        >>> require_usable_run(0, ['a.py::a'])
        True
        >>> require_usable_run(1, ['a.py::a'])
        True
        >>> require_usable_run(5, [], allow_empty=True)
        False
        >>> require_usable_run(5, [])
        Traceback (most recent call last):
            ...
        DoctestGateError: pytest collected no doctest at all ...
        >>> require_usable_run(4, [], allow_empty=True)
        Traceback (most recent call last):
            ...
        DoctestGateError: pytest exited 4 ...
    """
    if pytest_status == _NOTHING_COLLECTED_EXIT_CODE and not collected:
        if allow_empty:
            return False
        raise DoctestGateError(
            "pytest collected no doctest at all. A scope that matches nothing "
            "is a mistake, not a clean run; check the paths passed to --scope."
        )
    if pytest_status not in _VERDICT_EXIT_CODES:
        raise DoctestGateError(
            "pytest exited {0} rather than 0 or 1, so the collected and failed "
            "node-id sets are incomplete and no ratchet verdict can be derived. "
            "Exit 4 usually means a requested path does not exist.".format(
                pytest_status,
            )
        )
    if not collected:
        raise DoctestGateError(
            "pytest reported success but collected no doctest, so the recorded "
            "node-id sets cannot be trusted."
        )
    return True


def load_ledger(path: str) -> List[str]:
    """
    Parse a known-failure ledger file into node ids.

    Blank lines and ``#`` comment lines are ignored. Order is preserved so a
    rewritten ledger produces a stable diff.

    :param path: Ledger path relative to the repository root, or absolute.
    :type path: str
    :return: Node ids listed in the ledger, in file order.
    :rtype: List[str]
    :raises DoctestGateError: If the file exists but cannot be read.

    Example::

        >>> import os, tempfile
        >>> handle, name = tempfile.mkstemp(suffix='.txt')
        >>> _ = os.write(handle, b'# comment\\n\\na.py::a.f\\n')
        >>> os.close(handle)
        >>> load_ledger(name)
        ['a.py::a.f']
        >>> os.unlink(name)
    """
    absolute = path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)
    if not os.path.exists(absolute):
        return []
    try:
        with open(absolute, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
    except (OSError, UnicodeDecodeError) as err:
        # OSError: ledger path unreadable or removed mid-run.
        # UnicodeDecodeError: ledger saved with a non-UTF-8 encoding.
        raise DoctestGateError("cannot read ledger {0}: {1}".format(path, err))

    entries: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def node_file(node_id: str) -> str:
    """
    Return the file part of a pytest node id.

    :param node_id: Pytest node id such as ``a/b.py::a.b.f``.
    :type node_id: str
    :return: The path before the first ``::`` separator.
    :rtype: str

    Example::

        >>> node_file('pyfcstm/utils/safe.py::pyfcstm.utils.safe.sequence_safe')
        'pyfcstm/utils/safe.py'
        >>> node_file('pyfcstm/utils/safe.py')
        'pyfcstm/utils/safe.py'
    """
    return node_id.split("::", 1)[0].replace(os.sep, "/")


def normalize_scope(scope: Sequence[str], root: Optional[str] = None) -> List[str]:
    """
    Rewrite scope entries that live under the repository root as relative paths.

    pytest node ids are relative to the rootdir, so an absolute ``--scope``
    collects the same items but matches no ledger entry. Left unnormalized the
    whole in-scope ledger then reads as newly failing. That is a false red rather
    than a false green, but still a wrong verdict.

    :param scope: Paths or node ids requested by the caller.
    :type scope: collections.abc.Sequence[str]
    :param root: Repository root the paths are measured against, defaults to
        this file's repository.
    :type root: str, optional
    :return: Scope entries with in-repository absolute paths made relative.
    :rtype: List[str]

    Example::

        >>> import os
        >>> normalize_scope(['pyfcstm/bmc'], root='/repo')
        ['pyfcstm/bmc']
        >>> normalize_scope([os.path.join('/repo', 'pyfcstm', 'bmc')], root='/repo')
        ['pyfcstm/bmc']
        >>> normalize_scope(['/elsewhere/pkg'], root='/repo')
        ['/elsewhere/pkg']
    """
    base = os.path.abspath(root or _REPO_ROOT)
    normalized: List[str] = []
    for item in scope:
        path, separator, node = item.partition("::")
        if os.path.isabs(path):
            relative = os.path.relpath(os.path.abspath(path), base)
            if not relative.startswith(os.pardir):
                path = relative.replace(os.sep, "/")
        normalized.append(path + separator + node)
    return normalized


def filter_ledger_to_scope(
        ledger: Sequence[str],
        scope: Sequence[str],
) -> List[str]:
    """
    Keep only ledger entries that the current scope can actually collect.

    Without this, narrowing ``--scope`` turns every out-of-scope ledger entry
    into a bogus ``stale`` report, because the run never had a chance to
    collect it. Prefix matching is done per path component, so ``pyfcstm/utils``
    does not match a sibling directory such as ``pyfcstm/utils_extra``.

    :param ledger: Node ids listed in the known-failure ledger.
    :type ledger: collections.abc.Sequence[str]
    :param scope: Paths or node ids passed to pytest for this run.
    :type scope: collections.abc.Sequence[str]
    :return: Ledger entries reachable from ``scope``, in ledger order.
    :rtype: List[str]

    Example::

        >>> led = ['pyfcstm/utils/safe.py::a', 'pyfcstm/bmc/ast.py::b']
        >>> filter_ledger_to_scope(led, ['pyfcstm'])
        ['pyfcstm/utils/safe.py::a', 'pyfcstm/bmc/ast.py::b']
        >>> filter_ledger_to_scope(led, ['pyfcstm/utils'])
        ['pyfcstm/utils/safe.py::a']
        >>> filter_ledger_to_scope(led, ['pyfcstm/utils_extra'])
        []
        >>> filter_ledger_to_scope(led, ['pyfcstm/bmc/ast.py::b'])
        ['pyfcstm/bmc/ast.py::b']
    """
    roots = []
    exact = set()
    for item in scope:
        if "::" in item:
            exact.add(item.replace(os.sep, "/"))
            continue
        roots.append(item.replace(os.sep, "/").rstrip("/"))

    kept = []
    for entry in ledger:
        if entry in exact:
            kept.append(entry)
            continue
        path = node_file(entry)
        for root in roots:
            if path == root or path.startswith(root + "/"):
                kept.append(entry)
                break
    return kept


def select_changed_scope(
        paths: Sequence[str],
        root: Optional[str] = None,
) -> List[str]:
    """
    Reduce a changed-file list to the paths this gate can collect.

    A pull request touches many files the doctest gate has no opinion about
    (tests, workflows, Markdown). Keeping only existing ``pyfcstm/**.py`` paths
    lets a pre-merge run cost a fraction of the full gate while still covering
    every docstring the change could have broken.

    Deleted files are dropped because pytest cannot collect them, and a deleted
    path would otherwise turn every module-removing pull request into a usage
    error.

    :param paths: Changed paths as reported by git, relative to ``root``.
    :type paths: collections.abc.Sequence[str]
    :param root: Directory the paths are resolved against, defaults to the
        repository root. Present so this function stays testable without
        depending on any particular module surviving in the package.
    :type root: str, optional
    :return: Existing ``pyfcstm`` Python paths, de-duplicated in input order.
    :rtype: List[str]

    Example::

        >>> import os, tempfile
        >>> base = tempfile.mkdtemp()
        >>> os.makedirs(os.path.join(base, 'pyfcstm', 'utils'))
        >>> open(os.path.join(base, 'pyfcstm', 'utils', 'text.py'), 'w').close()
        >>> select_changed_scope(['docs/a.rst', 'test/test_a.py'], root=base)
        []
        >>> select_changed_scope(['pyfcstm/missing.py'], root=base)
        []
        >>> select_changed_scope(['pyfcstm/utils/text.py'] * 2, root=base)
        ['pyfcstm/utils/text.py']
    """
    base = root or _REPO_ROOT
    selected: List[str] = []
    seen = set()
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        if not path or not path.endswith(".py"):
            continue
        if path != "pyfcstm" and not path.startswith("pyfcstm/"):
            continue
        if path in seen:
            continue
        if not os.path.exists(os.path.join(base, path)):
            continue
        selected.append(path)
        seen.add(path)
    return selected


def classify_outcome(
        collected: Sequence[str],
        failed: Sequence[str],
        ledger: Sequence[str],
) -> Dict[str, List[str]]:
    """
    Compare one gate run against the known-failure ledger.

    Three conditions block the gate:

    * ``unexpected`` - A node failed but is not in the ledger. This is a new
      documentation regression.
    * ``graduated`` - A ledger node was collected and passed. The ledger must
      shrink, otherwise it silently becomes a permanent exemption list.
    * ``stale`` - A ledger node was not collected at all, so the docstring was
      renamed or deleted without updating the ledger.

    :param collected: Node ids collected by the gate run.
    :type collected: collections.abc.Sequence[str]
    :param failed: Node ids that failed in the gate run.
    :type failed: collections.abc.Sequence[str]
    :param ledger: Node ids listed in the known-failure ledger.
    :type ledger: collections.abc.Sequence[str]
    :return: Sorted node ids keyed by ``unexpected``, ``graduated``, ``stale``.
    :rtype: Dict[str, List[str]]

    Example::

        >>> out = classify_outcome(
        ...     collected=['m.py::a', 'm.py::b', 'm.py::c'],
        ...     failed=['m.py::a', 'm.py::c'],
        ...     ledger=['m.py::a', 'm.py::b', 'm.py::gone'],
        ... )
        >>> out['unexpected']
        ['m.py::c']
        >>> out['graduated']
        ['m.py::b']
        >>> out['stale']
        ['m.py::gone']
    """
    collected_set = set(collected)
    failed_set = set(failed)
    ledger_set = set(ledger)

    return {
        "unexpected": sorted(failed_set - ledger_set),
        "graduated": sorted((ledger_set & collected_set) - failed_set),
        "stale": sorted(ledger_set - collected_set),
    }


def build_pytest_command(
        scope: Sequence[str],
        outcome_file: str,
        option_flags: Sequence[str] = DEFAULT_OPTION_FLAGS,
        pytest_args: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Build the pytest argv for one doctest gate run.

    :param scope: Paths collected with ``--doctest-modules``.
    :type scope: collections.abc.Sequence[str]
    :param outcome_file: Path the plugin writes its node-id JSON to.
    :type outcome_file: str
    :param option_flags: Doctest option flag names, defaults to
        :data:`DEFAULT_OPTION_FLAGS`.
    :type option_flags: collections.abc.Sequence[str], optional
    :param pytest_args: Extra arguments appended verbatim, defaults to ``None``.
    :type pytest_args: collections.abc.Sequence[str], optional
    :return: Command argv beginning with the current interpreter.
    :rtype: List[str]

    Example::

        >>> cmd = build_pytest_command(['pyfcstm'], '/tmp/out.json')
        >>> cmd[1:5]
        ['-m', 'pytest', '--doctest-modules', '-p']
        >>> cmd[5]
        'tools.doctest_plugin'
    """
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--doctest-modules",
        "-p",
        "tools.doctest_plugin",
        "--doctest-outcome-file={0}".format(outcome_file),
        "-o",
        "doctest_optionflags={0}".format(" ".join(option_flags)),
        # The gate reports through the outcome file, so terminal tracebacks are
        # the only human-facing output worth keeping short.
        "--tb=short",
        "-q",
    ]
    command.extend(pytest_args or [])
    command.extend(scope)
    return command


def _read_outcome(path: str) -> Dict[str, List[str]]:
    """
    Read the plugin outcome file.

    :param path: Outcome JSON path written by ``tools.doctest_plugin``.
    :type path: str
    :return: Mapping with ``collected`` and ``failed`` node-id lists.
    :rtype: Dict[str, List[str]]
    :raises DoctestGateError: If the file is missing or not valid JSON.
    """
    if not os.path.exists(path):
        raise DoctestGateError(
            "pytest did not write {0}; the doctest plugin failed to load "
            "or pytest aborted during collection".format(path)
        )
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, UnicodeDecodeError, ValueError) as err:
        # OSError: outcome file unreadable.
        # UnicodeDecodeError: outcome file truncated mid-write.
        # ValueError: json.JSONDecodeError subclass for malformed content.
        raise DoctestGateError("cannot read outcome file {0}: {1}".format(path, err))
    if not isinstance(payload, dict):
        raise DoctestGateError("outcome file {0} is not a JSON object".format(path))
    return {
        "collected": list(payload.get("collected", [])),
        "failed": list(payload.get("failed", [])),
    }


def _write_ledger(path: str, entries: Sequence[str]) -> None:
    """
    Rewrite the known-failure ledger.

    :param path: Ledger path relative to the repository root, or absolute.
    :type path: str
    :param entries: Node ids to record, written sorted.
    :type entries: collections.abc.Sequence[str]
    :return: ``None``.
    :rtype: None
    :raises DoctestGateError: If the ledger cannot be written.
    """
    absolute = path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)
    header = (
        "# Doctest gate known-failure ledger.\n"
        "#\n"
        "# Each line is a pytest node id whose docstring examples are known to\n"
        "# fail. The gate fails when a listed node starts passing (remove the\n"
        "# line), when a listed node disappears (update the line), or when an\n"
        "# unlisted node fails (fix the docstring).\n"
        "#\n"
        "# Regenerate with: python tools/run_doctests.py --update-ledger\n"
        "\n"
    )
    try:
        with open(absolute, "w", encoding="utf-8") as file:
            file.write(header)
            for entry in sorted(entries):
                file.write(entry + "\n")
    except OSError as err:
        # OSError: ledger path not writable.
        raise DoctestGateError("cannot write ledger {0}: {1}".format(path, err))


def run_self_check() -> None:
    """
    Validate the ratchet classification without invoking pytest.

    :return: ``None``.
    :rtype: None
    :raises DoctestGateError: If any self-check expectation fails.
    """
    clean = classify_outcome(
        collected=["m.py::a", "m.py::b"],
        failed=["m.py::a"],
        ledger=["m.py::a"],
    )
    if clean != {"unexpected": [], "graduated": [], "stale": []}:
        raise DoctestGateError("self-check: steady-state ledger must be clean")

    regressed = classify_outcome(
        collected=["m.py::a"], failed=["m.py::a"], ledger=[],
    )
    if regressed["unexpected"] != ["m.py::a"]:
        raise DoctestGateError("self-check: unlisted failure must be unexpected")

    graduated = classify_outcome(
        collected=["m.py::a"], failed=[], ledger=["m.py::a"],
    )
    if graduated["graduated"] != ["m.py::a"]:
        raise DoctestGateError("self-check: newly passing node must graduate")

    stale = classify_outcome(collected=[], failed=[], ledger=["m.py::gone"])
    if stale["stale"] != ["m.py::gone"]:
        raise DoctestGateError("self-check: uncollected ledger node must be stale")

    command = build_pytest_command(["pyfcstm"], "/tmp/out.json")
    if "tools.doctest_plugin" not in command:
        raise DoctestGateError("self-check: gate must load the doctest plugin")
    if command[-1] != "pyfcstm":
        raise DoctestGateError("self-check: scope must be the trailing argument")

    empty = load_ledger(os.path.join(_REPO_ROOT, "no-such-ledger-file.txt"))
    if empty != []:
        raise DoctestGateError("self-check: missing ledger must read as empty")

    led = ["pyfcstm/utils/safe.py::a", "pyfcstm/bmc/ast.py::b"]
    if filter_ledger_to_scope(led, ["pyfcstm"]) != led:
        raise DoctestGateError("self-check: full scope must keep every entry")
    if filter_ledger_to_scope(led, ["pyfcstm/utils"]) != led[:1]:
        raise DoctestGateError("self-check: narrow scope must drop other roots")
    if filter_ledger_to_scope(led, ["pyfcstm/utils_extra"]) != []:
        raise DoctestGateError(
            "self-check: prefix match must respect path component boundaries"
        )
    if filter_ledger_to_scope(led, ["pyfcstm/bmc/ast.py::b"]) != led[1:]:
        raise DoctestGateError("self-check: exact node id scope must be honored")

    # A temporary tree keeps the self-check independent of which modules
    # currently exist in the package.
    sandbox = tempfile.mkdtemp(prefix="pyfcstm-doctest-selfcheck-")
    os.makedirs(os.path.join(sandbox, "pyfcstm", "utils"))
    open(os.path.join(sandbox, "pyfcstm", "utils", "text.py"), "w").close()
    if select_changed_scope(["docs/a.rst", "test/t.py"], root=sandbox) != []:
        raise DoctestGateError("self-check: non-pyfcstm paths must be dropped")
    if select_changed_scope(["pyfcstm/missing.py"], root=sandbox) != []:
        raise DoctestGateError("self-check: missing paths must be dropped")
    dup = ["pyfcstm/utils/text.py", "pyfcstm/utils/text.py"]
    if select_changed_scope(dup, root=sandbox) != ["pyfcstm/utils/text.py"]:
        raise DoctestGateError("self-check: changed paths must be de-duplicated")

    require_installed_distribution()
    try:
        require_installed_distribution("no-such-distribution-xyz")
    except DoctestGateError:
        # DoctestGateError: expected; an absent distribution must be reported.
        pass
    else:
        raise DoctestGateError(
            "self-check: an uninstalled distribution must be reported"
        )

    # Every helper main() reaches for is exercised here, so a missing or renamed
    # one fails --check instead of waiting for the flag that happens to use it.
    if not require_usable_run(0, ["a.py::a"]):
        raise DoctestGateError("self-check: a clean run must have results")
    if not require_usable_run(1, ["a.py::a"]):
        raise DoctestGateError("self-check: a failing run must have results")
    if require_usable_run(5, [], allow_empty=True):
        raise DoctestGateError(
            "self-check: an allowed empty collection must report no results"
        )
    for status, nodes, empty_ok, why in (
        (4, [], False, "a nonexistent scope"),
        (4, [], True, "a nonexistent scope even when empties are allowed"),
        (2, ["a.py::a"], False, "an interrupted run"),
        (5, [], False, "an unexplained empty collection"),
        (0, [], False, "success with nothing collected"),
    ):
        try:
            require_usable_run(status, nodes, allow_empty=empty_ok)
        except DoctestGateError:
            # DoctestGateError: expected; the run cannot support a verdict.
            continue
        raise DoctestGateError(
            "self-check: {0} must not yield a verdict".format(why)
        )

    if normalize_scope(["pyfcstm/bmc"], root="/repo") != ["pyfcstm/bmc"]:
        raise DoctestGateError("self-check: relative scope must pass through")
    inside = os.path.join("/repo", "pyfcstm", "bmc")
    if normalize_scope([inside], root="/repo") != ["pyfcstm/bmc"]:
        raise DoctestGateError("self-check: in-repo absolute scope must relativize")
    if normalize_scope(["/elsewhere/pkg"], root="/repo") != ["/elsewhere/pkg"]:
        raise DoctestGateError("self-check: out-of-repo scope must be left alone")
    node = os.path.join("/repo", "pyfcstm", "a.py") + "::pyfcstm.a.f"
    if normalize_scope([node], root="/repo") != ["pyfcstm/a.py::pyfcstm.a.f"]:
        raise DoctestGateError("self-check: absolute node id must keep its node part")

    reject_unsupported_pytest_args(["--tb=long", "-x"])
    for rejected in (["-n", "4"], ["--numprocesses=auto"], ["--dist=loadscope"]):
        try:
            reject_unsupported_pytest_args(rejected)
        except DoctestGateError:
            # DoctestGateError: expected; xdist arguments must be rejected.
            continue
        raise DoctestGateError(
            "self-check: {0!r} must be rejected".format(rejected)
        )


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Run the repository doctest gate with a known-failure ratchet.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Run the tool self-check and exit.",
    )
    parser.add_argument(
        "--scope", action="append", default=None, metavar="PATH",
        help="Path collected with --doctest-modules; repeatable "
             "(default: {0}).".format(" ".join(DEFAULT_SCOPE)),
    )
    parser.add_argument(
        "--changed-files", default=None, metavar="PATH",
        help="File listing changed paths, one per line. The scope becomes the "
             "existing pyfcstm Python files among them; an empty selection "
             "exits 0 without running pytest.",
    )
    parser.add_argument(
        "--ledger", default=DEFAULT_LEDGER, metavar="PATH",
        help="Known-failure ledger path (default: {0}).".format(DEFAULT_LEDGER),
    )
    parser.add_argument(
        "--no-ledger", action="store_true",
        help="Ignore the ledger and require every doctest to pass.",
    )
    parser.add_argument(
        "--update-ledger", action="store_true",
        help="Rewrite the ledger from the current failures, then exit 0.",
    )
    parser.add_argument(
        "pytest_args", nargs="*", default=[], metavar="PYTEST_ARG",
        help="Extra arguments forwarded to pytest.",
    )
    return parser


def _report(classification: Dict[str, List[str]], ledger_path: str) -> None:
    """
    Print an actionable report for a blocked gate run.

    :param classification: Result of :func:`classify_outcome`.
    :type classification: Dict[str, List[str]]
    :param ledger_path: Ledger path shown in remediation hints.
    :type ledger_path: str
    :return: ``None``.
    :rtype: None
    """
    if classification["unexpected"]:
        sys.stderr.write(
            "\ndoctest gate: {0} new failing docstring(s). Fix the example, or "
            "add a fixture through tools/doctest_plugin.py.\n".format(
                len(classification["unexpected"]),
            )
        )
        for node in classification["unexpected"]:
            sys.stderr.write("  + {0}\n".format(node))
    if classification["graduated"]:
        sys.stderr.write(
            "\ndoctest gate: {0} ledger entr(y/ies) now pass. Delete them from "
            "{1} so the ratchet keeps its progress.\n".format(
                len(classification["graduated"]), ledger_path,
            )
        )
        for node in classification["graduated"]:
            sys.stderr.write("  - {0}\n".format(node))
    if classification["stale"]:
        sys.stderr.write(
            "\ndoctest gate: {0} ledger entr(y/ies) match no collected doctest. "
            "The docstring was renamed or removed; update {1}.\n".format(
                len(classification["stale"]), ledger_path,
            )
        )
        for node in classification["stale"]:
            sys.stderr.write("  ? {0}\n".format(node))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the doctest gate command-line interface.

    :param argv: Optional argument vector without the program name. ``None``
        reads :data:`sys.argv`.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process-style exit code; ``0`` when the gate holds.
    :rtype: int

    Example::

        $ python tools/run_doctests.py --check
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.check:
        try:
            run_self_check()
        except DoctestGateError as err:
            # DoctestGateError: a self-check expectation did not hold.
            parser.exit(2, "run_doctests: {0}\n".format(err))
        sys.stdout.write("doctest gate self-check passed\n")
        return 0

    try:
        reject_unsupported_pytest_args(args.pytest_args)
        require_installed_distribution()
    except DoctestGateError as err:
        # DoctestGateError: caller passed an argument that breaks the ratchet,
        # or the package is not installed and entry-point examples would fail.
        parser.exit(2, "run_doctests: {0}\n".format(err))

    if args.changed_files:
        try:
            with open(args.changed_files, "r", encoding="utf-8") as handle:
                changed = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as err:
            # OSError: the changed-file list is missing or unreadable.
            # UnicodeDecodeError: the list was written with another encoding.
            sys.stderr.write(
                "run_doctests: cannot read {0}: {1}\n".format(
                    args.changed_files, err,
                )
            )
            return 2
        selected = select_changed_scope(changed)
        if not selected:
            sys.stdout.write(
                "doctest gate skipped: no changed pyfcstm Python file to check\n"
            )
            return 0
        scope = tuple(selected)
    elif args.scope:
        scope = tuple(normalize_scope(args.scope))
    else:
        scope = DEFAULT_SCOPE
    outcome_dir = tempfile.mkdtemp(prefix="pyfcstm-doctest-")
    outcome_file = os.path.join(outcome_dir, "outcome.json")
    command = build_pytest_command(scope, outcome_file, pytest_args=args.pytest_args)

    sys.stdout.write(
        "$ {0}\n".format(" ".join(shlex_quote(part) for part in command))
    )
    sys.stdout.flush()
    pytest_status = subprocess.call(command, cwd=_REPO_ROOT)

    try:
        outcome = _read_outcome(outcome_file)
        has_results = require_usable_run(
            pytest_status,
            outcome["collected"],
            allow_empty=bool(args.changed_files),
        )
    except DoctestGateError as err:
        # DoctestGateError: pytest aborted before the plugin could report, or it
        # exited in a way that makes the recorded node-id sets untrustworthy.
        sys.stderr.write("run_doctests: {0}\n".format(err))
        return 2

    if not has_results:
        sys.stdout.write(
            "doctest gate skipped: the changed pyfcstm files carry no docstring "
            "example\n"
        )
        return 0

    if args.update_ledger:
        try:
            _write_ledger(args.ledger, outcome["failed"])
        except DoctestGateError as err:
            # DoctestGateError: ledger path not writable.
            sys.stderr.write("run_doctests: {0}\n".format(err))
            return 2
        sys.stdout.write(
            "doctest gate: ledger rewritten with {0} entr(y/ies) -> {1}\n".format(
                len(outcome["failed"]), args.ledger,
            )
        )
        return 0

    try:
        ledger = [] if args.no_ledger else load_ledger(args.ledger)
    except DoctestGateError as err:
        # DoctestGateError: ledger unreadable.
        sys.stderr.write("run_doctests: {0}\n".format(err))
        return 2

    # Narrowing the scope must not turn out-of-scope ledger entries into
    # bogus "stale" reports; only entries this run could collect are compared.
    scoped_ledger = filter_ledger_to_scope(ledger, scope)
    classification = classify_outcome(
        collected=outcome["collected"],
        failed=outcome["failed"],
        ledger=scoped_ledger,
    )
    blocked = any(classification[key] for key in ("unexpected", "graduated", "stale"))
    if blocked:
        _report(classification, args.ledger)
        return 1

    sys.stdout.write(
        "doctest gate passed: {0} doctest(s) collected, {1} known failure(s) "
        "still ledgered in scope\n".format(
            len(outcome["collected"]), len(scoped_ledger),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
