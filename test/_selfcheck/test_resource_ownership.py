"""Resources acquired by the self-check runner survive no interrupt unreleased."""

import glob
import os
import subprocess
import sys
import textwrap
import time
import tempfile

import pytest

from pyfcstm._selfcheck import process as process_module
from pyfcstm._selfcheck import registry as registry_module
from pyfcstm._selfcheck import report as report_module
from pyfcstm._selfcheck import worker as worker_module
from pyfcstm._selfcheck.model import ReportSnapshot
from test.testings.interrupt_injection import inject_per_line, open_descriptors

pytestmark = pytest.mark.unittest

_SESSION_GLOB = "pyfcstm-selfcheck-*"


@pytest.fixture()
def private_tmpdir(tmp_path, monkeypatch):
    """Point ``tempfile`` at a per-test directory for the duration of one test.

    The session directory is created with ``tempfile.mkdtemp`` and no explicit
    ``dir``, so a residue check against the shared temporary directory would see
    any concurrent run -- another xdist worker, another suite, a stray
    ``pyfcstm --self-check`` -- and fail for reasons that have nothing to do with
    the code under test.
    """
    private = tmp_path / "tmp"
    private.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(private))
    return str(private)

requires_proc = pytest.mark.skipif(
    not os.path.isdir("/proc/self/fd"),
    reason="descriptor accounting needs /proc/self/fd",
)


def _children(pid):
    """Return ``(pid, state)`` for every child of *pid*, zombies included."""
    states = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open("/proc/{}/stat".format(entry), "rb") as handle:
                fields = handle.read().rsplit(b")", 1)[1].split()
        except OSError:
            # The child can exit between the listing and this read.
            continue
        if int(fields[1]) == pid:
            states.append((int(entry), fields[0].decode()))
    return states


def _child_pids(pid):
    """Return the pids of every child of *pid*, zombies included."""
    return [child for child, _ in _children(pid)]


def _kill_and_reap_pids(pids):
    """Kill the children one injection point stranded, then collect them."""
    for child in pids:
        try:
            os.kill(child, 9)
        except OSError:
            # The child may have exited between detection and the signal.
            pass
    _reap()


def _wait_for_no_children(pid, timeout=5.0):
    """Wait until *pid* has no children left, returning whatever still remains.

    SIGKILL delivery and reaping are both asynchronous, so a child killed a
    moment ago can still be listed as a zombie. Only a bounded wait can tell
    that apart from a child that was never released.
    """
    deadline = time.monotonic() + timeout
    while True:
        _reap()
        remaining = _child_pids(pid)
        if not remaining or time.monotonic() >= deadline:
            return remaining
        time.sleep(0.05)


def _reap():
    """Collect any already-exited children so counts do not carry over."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def _sleeper():
    """Command for a child that outlives any test unless it is killed."""
    return [sys.executable, "-c", "import time; time.sleep(30)"]


def _worker_popen_kwargs():
    """Spawn arguments matching the ones ``run_check_process`` uses.

    ``start_new_session`` matters: without it the child is not a process-group
    leader, and the POSIX termination path signals a group that does not exist.
    """
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    return kwargs


@requires_proc
def test_bounded_popen_reaps_the_child_when_the_body_is_interrupted():
    """An interrupt inside the ``with`` body still terminates and reaps the child."""
    _reap()
    with pytest.raises(KeyboardInterrupt):
        with registry_module._bounded_popen(
            _sleeper(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as child:
            assert child.poll() is None
            raise KeyboardInterrupt("interrupted while the child is running")
    assert _wait_for_no_children(os.getpid()) == []


@requires_proc
def test_run_subprocess_bounded_leaves_no_orphan_at_any_injection_point():
    """No line of the bounded runner leaves a live or unreaped child behind."""
    _reap()
    report = inject_per_line(
        registry_module._run_subprocess_bounded,
        lambda: registry_module._run_subprocess_bounded(_sleeper(), timeout=0.3),
    )
    assert report.points_reached > 0
    assert not report.body_windows, report.describe()
    assert _wait_for_no_children(os.getpid()) == []


def test_session_transport_removes_its_directory_when_the_body_raises():
    """The session directory and result file do not outlive a failed body."""
    captured = {}
    with pytest.raises(KeyboardInterrupt):
        with process_module._session_transport() as (directory, result_file, mode):
            captured["directory"] = directory
            captured["result_file"] = result_file
            assert mode == "file"
            assert os.path.isdir(directory)
            assert os.path.isfile(result_file)
            raise KeyboardInterrupt("interrupted while the session is open")
    assert not os.path.exists(captured["result_file"])
    assert not os.path.isdir(captured["directory"])


@requires_proc
def test_output_spools_close_when_the_body_raises():
    """Both spool descriptors are released even though the body never returns."""
    before = set(open_descriptors())
    with pytest.raises(KeyboardInterrupt):
        with process_module._output_spools() as (stdout_spool, stderr_spool, error):
            assert error is None
            assert stdout_spool is not None and stderr_spool is not None
            raise KeyboardInterrupt("interrupted while the spools are open")
    assert set(open_descriptors()) - before == set()


def test_output_spools_yield_no_half_created_pair(monkeypatch):
    """A failure on the second spool withdraws the first rather than yielding it."""
    created = []
    real_temporary_file = tempfile.TemporaryFile

    def one_then_fail(*args, **kwargs):
        if created:
            raise OSError("no space left on device")
        spool = real_temporary_file(*args, **kwargs)
        created.append(spool)
        return spool

    monkeypatch.setattr(process_module.tempfile, "TemporaryFile", one_then_fail)
    with process_module._output_spools() as (stdout_spool, stderr_spool, error):
        assert stdout_spool is None
        assert stderr_spool is None
        assert "no space left on device" in error
    assert created[0].closed


@requires_proc
def test_worker_tree_terminates_the_worker_when_the_body_raises():
    """An interrupt in the ``with`` body terminates the spawned worker tree."""
    _reap()
    with pytest.raises(KeyboardInterrupt):
        with process_module._worker_tree(
            _sleeper(),
            _worker_popen_kwargs(),
            os.name == "posix",
            0.5,
        ) as (tree, spawn_error):
            assert spawn_error is None
            assert tree.process.poll() is None
            raise KeyboardInterrupt("interrupted while the worker runs")
    assert _wait_for_no_children(os.getpid()) == []


def test_worker_tree_reports_a_failed_spawn_instead_of_raising():
    """A spawn failure is yielded as data so the caller can classify the check."""
    with process_module._worker_tree(
        [os.path.join(os.sep, "nonexistent", "pyfcstm-worker")], {}, False, 0.5
    ) as (tree, spawn_error):
        assert tree is None
        assert isinstance(spawn_error, OSError)


def test_worker_tree_terminates_only_once():
    """A caller that already terminated the tree gets no second termination."""
    with process_module._worker_tree(
        [sys.executable, "-c", "pass"],
        _worker_popen_kwargs(),
        os.name == "posix",
        0.5,
    ) as (tree, spawn_error):
        assert spawn_error is None
        tree.terminate()
        assert tree.terminate() is None


def test_terminate_accepts_a_tree_that_was_never_spawned():
    """Cleanup reached before the spawn is a clean exit, not an attribute error."""
    assert process_module._terminate(None, None, False, 0.5) is None


@requires_proc
def test_write_frame_leaves_no_descriptor_at_any_injection_point(tmp_path):
    """Neither the frame writer nor its file helper leaks the transport descriptor."""
    target = tmp_path / "result.log"
    target.write_bytes(b"")
    for function, invoke in (
        (
            worker_module._write_frame,
            lambda: worker_module._write_frame("file", str(target), b"payload\n"),
        ),
        (
            worker_module._append_frame_to_file,
            lambda: worker_module._append_frame_to_file(str(target), b"payload\n"),
        ),
    ):
        report = inject_per_line(function, invoke)
        assert report.points_reached > 0
        assert not report.body_windows, "{}:\n{}".format(
            function.__name__, report.describe()
        )


@requires_proc
def test_write_report_leaves_no_descriptor_or_temporary_file(tmp_path):
    """The atomic report writer owns both the descriptor and the temporary path."""
    target = tmp_path / "report.json"
    snapshot = ReportSnapshot((), {}, {})
    report = inject_per_line(
        report_module.write_report,
        lambda: report_module.write_report(str(target), snapshot),
        lambda: {str(path) for path in tmp_path.glob(".pyfcstm-selfcheck-*.tmp")},
    )
    assert report.points_reached > 0
    assert not report.body_windows, report.describe()


@requires_proc
def test_session_transport_leaves_no_directory_at_any_injection_point(private_tmpdir):
    """No line of the session context manager can strand its private directory.

    Covers the case the body-level test cannot reach: an interrupt between
    creating ``result.log`` and binding its name would leave ``_cleanup_session``
    trying to remove a directory it believes is empty.
    """

    def use_transport():
        with process_module._session_transport():
            pass

    report = inject_per_line(
        process_module._session_transport,
        use_transport,
        lambda: set(glob.glob(os.path.join(private_tmpdir, _SESSION_GLOB))),
    )
    assert report.points_reached > 0
    assert not report.body_windows, report.describe()


@requires_proc
def test_output_spools_leave_no_descriptor_at_any_injection_point():
    """No line of the spool context manager can strand a spool descriptor."""

    def use_spools():
        with process_module._output_spools():
            pass

    report = inject_per_line(process_module._output_spools, use_spools)
    assert report.points_reached > 0
    assert not report.body_windows, report.describe()


@requires_proc
def test_worker_tree_leaves_no_child_at_any_injection_point():
    """No line of the worker context manager can strand the spawned child."""
    _reap()

    def use_tree():
        with process_module._worker_tree(
            _sleeper(), _worker_popen_kwargs(), os.name == "posix", 0.5
        ):
            pass

    report = inject_per_line(
        process_module._worker_tree,
        use_tree,
        lambda: set(_child_pids(os.getpid())),
        _kill_and_reap_pids,
    )
    assert report.points_reached > 0
    assert not report.body_windows, report.describe()
    assert _wait_for_no_children(os.getpid()) == []


def test_no_ownership_function_opens_a_handler_while_holding():
    """No resource-owning function nests a ``try`` inside its own ``try``.

    Version-independent on purpose. The runtime consequence only appears from
    CPython 3.11, where the inner ``try:`` compiles to a ``NOP`` that no
    exception-table entry covers and the owner's ``finally`` is skipped
    outright. A suite pinned to 3.10 would never see it, so the shape is
    checked structurally instead of only by injection.
    """
    import ast
    import inspect

    import pyfcstm.entry.bmc as bmc_module
    from pyfcstm import _bootstrap
    from pyfcstm.config import _build_identity

    # Every function this contract covers, across all four subsystems: the ones
    # that own a resource and the failure-tolerant helpers they were split into.
    owners = (
        process_module.run_check_process,
        process_module._session_transport,
        process_module._make_session_directory,
        process_module._create_empty_file,
        process_module._output_spools,
        process_module._make_output_spool,
        process_module._worker_tree,
        process_module._spawn_worker_process,
        process_module._terminate,
        registry_module._bounded_popen,
        registry_module._kill_and_reap,
        registry_module._run_subprocess_bounded,
        report_module.write_report,
        worker_module._write_frame,
        worker_module._append_frame_to_file,
        bmc_module.write_bmc_output,
        _build_identity.write_build_identity_file,
        _build_identity._fsync_directory,
        _bootstrap._emergency_write,
    )
    offenders = []
    for owner in owners:
        function = getattr(owner, "__wrapped__", owner)
        source, first = inspect.getsourcelines(function)
        tree = ast.parse(textwrap.dedent("".join(source)))
        for outer in ast.walk(tree):
            if not isinstance(outer, ast.Try):
                continue
            # Only the outer ``try``'s body holds a resource across an inner
            # handler; its own handlers and ``finally`` are the release path.
            for statement in outer.body:
                for node in ast.walk(statement):
                    if isinstance(node, ast.Try) and node is not outer:
                        offenders.append(
                            "{}:{}".format(function.__name__, node.lineno + first - 1)
                        )
    assert not offenders, "nested try inside an owning try: {}".format(offenders)
