"""Platform-neutral tests for Windows cleanup helper no-op paths."""

import pytest


@pytest.mark.unittest
def test_job_handle_without_native_handle_is_safe():
    """Non-Windows test environments can exercise the no-handle cleanup path."""
    from pyfcstm._selfcheck._win32 import JobHandle

    job = JobHandle(None, False)
    job.terminate()
    job.close()
    assert job.handle is None


@pytest.mark.unittest
def test_attach_process_is_noop_outside_windows():
    """The helper does not import ctypes on POSIX."""
    import os

    if os.name == "nt":
        pytest.skip("Windows uses the Job Object path instead of the no-op path.")
    from pyfcstm._selfcheck._win32 import attach_process

    assert attach_process(None) is None


@pytest.mark.unittest
def test_ntstatus_format_is_unsigned_and_symbolic():
    """Known Windows crash codes retain their hex and symbolic diagnostics."""
    from pyfcstm._selfcheck._win32 import format_ntstatus

    assert format_ntstatus(0xC0000005) == "0xC0000005 (ACCESS_VIOLATION)"
    assert format_ntstatus(-1073741819) == "0xC0000005 (ACCESS_VIOLATION)"
    assert format_ntstatus(7) is None


@pytest.mark.unittest
def test_kill_on_close_configuration_reports_api_result():
    """The Win32 helper exposes success and explicit-fallback outcomes."""
    try:
        __import__("ctypes.wintypes")
    except ValueError as err:
        # Python 3.7 POSIX cannot load the Windows VARIANT_BOOL ctypes type.
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))
    from pyfcstm._selfcheck._win32 import _enable_kill_on_close

    class Setter:
        def __init__(self, result):
            self.result = result

        def __call__(self, *args):
            del args
            return self.result

    class Kernel:
        def __init__(self, result):
            self.SetInformationJobObject = Setter(result)

    assert _enable_kill_on_close(Kernel(1), object()) is True
    assert _enable_kill_on_close(Kernel(0), object()) is False


@pytest.mark.unittest
def test_windows_job_handle_and_attach_paths_use_native_calls(monkeypatch):
    """Fake Win32 calls exercise termination, assignment, and fallback modes."""
    try:
        __import__("ctypes.wintypes")
    except ValueError as err:
        # Python 3.7 POSIX cannot load the Windows VARIANT_BOOL ctypes type.
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))
    import ctypes
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    class Kernel:
        def __init__(self, kill_on_close):
            self.CreateJobObjectW = Call(101)
            self.OpenProcess = Call(202)
            self.AssignProcessToJobObject = Call(1)
            self.SetInformationJobObject = Call(1 if kill_on_close else 0)
            self.TerminateJobObject = Call(1)
            self.CloseHandle = Call(1)

    kernel = Kernel(True)
    # Replace the module seam instead of mutating the process-global ``os.name``;
    # pytest itself still needs to construct POSIX paths while reporting errors.
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    job = win32.attach_process(SimpleNamespace(pid=7))
    assert job.kill_on_close is True
    assert kernel.OpenProcess.calls[0][0] == 0x0001 | 0x0100
    job.terminate(4)
    job.close()
    assert kernel.AssignProcessToJobObject.calls

    fallback_kernel = Kernel(False)
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=fallback_kernel), raising=False
    )
    fallback = win32.attach_process(SimpleNamespace(pid=8))
    fallback.terminate(9)
    assert fallback.kill_on_close is False
    fallback.close()
    assert fallback_kernel.TerminateJobObject.calls


@pytest.mark.unittest
def test_assign_failure_closes_created_job_handle(monkeypatch):
    """A failed assignment closes both native handles before raising."""
    try:
        __import__("ctypes.wintypes")
    except ValueError as err:
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))
    import ctypes
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    class Kernel:
        CreateJobObjectW = Call(101)
        OpenProcess = Call(202)
        AssignProcessToJobObject = Call(0)
        CloseHandle = Call(1)

    kernel = Kernel()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    with pytest.raises(win32.JobAssignmentError):
        win32.attach_process(SimpleNamespace(pid=7))
    assert len(kernel.CloseHandle.calls) == 2


@pytest.mark.unittest
def test_native_setup_errors_are_wrapped_as_job_assignment_errors(monkeypatch):
    """Unexpected ctypes setup failures do not escape the Win32 seam."""
    try:
        __import__("ctypes.wintypes")
    except ValueError as err:
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))
    import ctypes
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class CreateJob:
        restype = None

        def __call__(self, *args):
            del args
            raise OSError("native setup")

    class Kernel:
        CreateJobObjectW = CreateJob()

    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=Kernel()), raising=False
    )
    with pytest.raises(win32.JobAssignmentError, match="native setup"):
        win32.attach_process(SimpleNamespace(pid=7))
