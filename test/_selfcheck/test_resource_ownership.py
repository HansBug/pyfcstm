"""Resources acquired by the self-check runner survive no interrupt unreleased."""

import glob
import os
import shutil
import subprocess
import sys
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
    _reap(pids)


def _wait_for_new_children(baseline, timeout=5.0):
    """Wait until no child outside *baseline* is left, returning any that are.

    Compared against a baseline rather than asserting the process has no
    children at all: under ``pytest -n`` this worker also hosts multiprocessing
    helpers belonging to other tests, and "this process has no children" is not
    a property of the code under test.

    SIGKILL delivery and reaping are both asynchronous, so a child killed a
    moment ago can still be listed as a zombie. Only a bounded wait tells that
    apart from a child that was never released.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = [pid for pid in _child_pids(os.getpid()) if pid not in baseline]
        _reap(remaining)
        remaining = [pid for pid in _child_pids(os.getpid()) if pid not in baseline]
        if not remaining or time.monotonic() >= deadline:
            return remaining
        time.sleep(0.05)


def _reap(pids):
    """Collect the given children, and only those.

    Never ``waitpid(-1)``: this process also owns subprocesses belonging to
    other tests and to :mod:`multiprocessing`, and reaping one of those makes
    its real owner see ``ChildProcessError``, which :class:`subprocess.Popen`
    swallows and reports as ``returncode = 0``. A genuine non-zero exit
    elsewhere would then read as success.
    """
    for pid in pids:
        try:
            os.waitpid(pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            # Already reaped by its owner, or never ours to begin with.
            pass


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
    baseline = set(_child_pids(os.getpid()))
    with pytest.raises(KeyboardInterrupt):
        with registry_module._bounded_popen(
            _sleeper(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as child:
            assert child.poll() is None
            raise KeyboardInterrupt("interrupted while the child is running")
    assert _wait_for_new_children(baseline) == []


@requires_proc
def test_run_subprocess_bounded_leaves_no_orphan_at_any_injection_point():
    """No line of the bounded runner leaves a live or unreaped child behind."""
    baseline = set(_child_pids(os.getpid()))
    report = inject_per_line(
        registry_module._run_subprocess_bounded,
        lambda: registry_module._run_subprocess_bounded(_sleeper(), timeout=0.3),
        lambda: {pid for pid in _child_pids(os.getpid()) if pid not in baseline},
        _kill_and_reap_pids,
        must_reach=("_bounded_popen(", "process.poll()", "_read_bounded_process_file("),
    )
    assert not report.body_windows, report.describe()
    assert _wait_for_new_children(baseline) == []


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
    baseline = set(_child_pids(os.getpid()))
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
    assert _wait_for_new_children(baseline) == []


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
    baseline = set(_child_pids(os.getpid()))

    def use_tree():
        with process_module._worker_tree(
            _sleeper(), _worker_popen_kwargs(), os.name == "posix", 0.5
        ):
            pass

    report = inject_per_line(
        process_module._worker_tree,
        use_tree,
        lambda: {pid for pid in _child_pids(os.getpid()) if pid not in baseline},
        _kill_and_reap_pids,
        must_reach=("_spawn_worker_process(", "yield tree", "owner.terminate()"),
    )
    assert not report.body_windows, report.describe()
    assert _wait_for_new_children(baseline) == []


@requires_proc
def test_run_check_process_releases_everything_at_any_injection_point(private_tmpdir):
    """No line of the supervisor entry point strands a resource.

    This is the composition a user actually interrupts, and the per-manager
    sweeps above cannot see a resource the entry point acquires between them.
    It spawns one real worker per injection point, so it is the most expensive
    test in this file -- about 25 seconds for 74 points -- which is affordable
    only because most points abort the run before the worker does any work.
    """
    from pyfcstm._selfcheck.model import CheckSpec

    baseline = set(_child_pids(os.getpid()))
    spec = CheckSpec("artifact.self_dispatch", "self_dispatch")

    def residue():
        leftovers = {
            path for path in glob.glob(os.path.join(private_tmpdir, _SESSION_GLOB))
        }
        leftovers.update(
            "pid:%d" % pid
            for pid in _child_pids(os.getpid())
            if pid not in baseline
        )
        return leftovers

    def release(items):
        _kill_and_reap_pids(
            [int(item.split(":", 1)[1]) for item in items if item.startswith("pid:")]
        )
        for item in items:
            if not item.startswith("pid:"):
                shutil.rmtree(item, ignore_errors=True)

    report = inject_per_line(
        process_module.run_check_process,
        lambda: process_module.run_check_process(spec, 6.0),
        residue,
        release,
        must_reach=("_session_transport()", "_worker_tree(", "process.communicate("),
    )
    assert not report.body_windows, report.describe()
    assert _wait_for_new_children(baseline) == []
