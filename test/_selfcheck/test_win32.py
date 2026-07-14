"""Platform-neutral tests for Windows cleanup helper no-op paths."""

import pytest


def _ctypes_for_native_seam(monkeypatch):
    """Provide ctypes scalar aliases when Python 3.7 cannot import wintypes."""
    import ctypes
    from types import SimpleNamespace

    try:
        from ctypes import wintypes
    except ValueError:
        # Python 3.7 on POSIX raises while importing ctypes.wintypes because
        # VARIANT_BOOL is unavailable; the public helper only needs scalar ABI
        # aliases for this deterministic native-call seam test.
        wintypes = SimpleNamespace(
            BOOL=ctypes.c_int,
            DWORD=ctypes.c_uint32,
            HANDLE=ctypes.c_void_p,
            LPCWSTR=ctypes.c_wchar_p,
            UINT=ctypes.c_uint,
            WORD=ctypes.c_uint16,
        )
        monkeypatch.setattr(ctypes, "wintypes", wintypes, raising=False)
    return ctypes


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
    assert format_ntstatus(None) is None


@pytest.mark.unittest
def test_job_handle_native_termination_failure_is_typed(monkeypatch):
    """A failed native termination call becomes ``JobAssignmentError``."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Kernel:
        class Terminate:
            def __call__(self, handle, exit_code):
                del handle, exit_code
                return 0

    kernel = Kernel()
    kernel.TerminateJobObject = kernel.Terminate()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    with pytest.raises(win32.JobAssignmentError):
        win32.JobHandle(7, False).terminate()


@pytest.mark.unittest
def test_kill_on_close_configuration_reports_api_result(monkeypatch):
    """The Win32 helper exposes success and explicit-fallback outcomes."""
    _ctypes_for_native_seam(monkeypatch)
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
    ctypes = _ctypes_for_native_seam(monkeypatch)
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
    from ctypes import wintypes

    assert kernel.CreateJobObjectW.restype is wintypes.HANDLE
    assert kernel.OpenProcess.restype is wintypes.HANDLE
    assert kernel.AssignProcessToJobObject.restype is wintypes.BOOL
    assert kernel.CloseHandle.restype is wintypes.BOOL
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

    error_kernel = Kernel(True)
    error_kernel.SetInformationJobObject = lambda *args: (_ for _ in ()).throw(
        OSError("unsupported")
    )
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=error_kernel), raising=False
    )
    error_job = win32.attach_process(SimpleNamespace(pid=9))
    assert error_job.kill_on_close is False
    error_job.close()


@pytest.mark.unittest
def test_assign_failure_closes_created_job_handle(monkeypatch):
    """A failed assignment closes both native handles before raising."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
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
def test_native_oserror_closes_job_handle_before_wrapping(monkeypatch):
    """An OSError after job creation closes the owned handle exactly once."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result

    class Kernel:
        CreateJobObjectW = Call(101)
        OpenProcess = Call(202)
        AssignProcessToJobObject = Call(OSError("assign"))
        CloseHandle = Call(1)

    kernel = Kernel()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    with pytest.raises(win32.JobAssignmentError, match="assign"):
        win32.attach_process(SimpleNamespace(pid=7))
    assert len(kernel.CloseHandle.calls) == 2


@pytest.mark.unittest
def test_native_setup_errors_are_wrapped_as_job_assignment_errors(monkeypatch):
    """Unexpected ctypes setup failures do not escape the Win32 seam."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
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


@pytest.mark.unittest
@pytest.mark.parametrize("failure", ["create", "open"])
def test_job_creation_failures_close_or_report_native_handles(monkeypatch, failure):
    """Create/Open failures through the public attach API stay typed."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
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
        def __init__(self):
            self.CreateJobObjectW = Call(0 if failure == "create" else 101)
            self.OpenProcess = Call(0 if failure == "open" else 202)
            self.AssignProcessToJobObject = Call(1)
            self.CloseHandle = Call(1)

    kernel = Kernel()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    with pytest.raises(win32.JobAssignmentError):
        win32.attach_process(SimpleNamespace(pid=7))
    if failure == "open":
        assert len(kernel.CloseHandle.calls) == 2


@pytest.mark.unittest
def test_win7_console_fallback_translates_known_ansi_roles(monkeypatch):
    """A non-VT Windows console receives text plus native color attributes."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result=1):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    class GetInfo(Call):
        def __call__(self, handle, pointer):
            self.calls.append((handle, pointer))
            pointer._obj.wAttributes = 7
            return 1

    class Kernel:
        GetStdHandle = Call(101)
        GetConsoleScreenBufferInfo = GetInfo()
        SetConsoleTextAttribute = Call(1)

    kernel = Kernel()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    stream = io.StringIO()
    assert win32.write_console_ansi("\x1b[32mPASS\x1b[0m\n", stream) is True
    assert stream.getvalue() == "PASS\n"
    attributes = [call[1] for call in kernel.SetConsoleTextAttribute.calls]
    assert 0x000A in attributes
    assert attributes[-1] == 7


@pytest.mark.unittest
def test_win7_console_fallback_preflights_attributes_before_output(monkeypatch):
    """A native color failure leaves the stream untouched for plain fallback."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result=1):
            self.result = result

        def __call__(self, *args):
            del args
            return self.result

    class GetInfo(Call):
        def __call__(self, handle, pointer):
            del handle
            pointer._obj.wAttributes = 7
            return 1

    class SetAttribute:
        def __init__(self):
            self.calls = 0

        def __call__(self, handle, attribute):
            del handle, attribute
            self.calls += 1
            return 0 if self.calls == 2 else 1

    class Kernel:
        GetStdHandle = Call(101)
        GetConsoleScreenBufferInfo = GetInfo()
        SetConsoleTextAttribute = SetAttribute()

    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=Kernel()), raising=False
    )
    stream = io.StringIO()
    assert win32.write_console_ansi("\x1b[32mPASS\x1b[0m\n", stream) is False
    assert stream.getvalue() == ""


@pytest.mark.unittest
def test_win7_console_fallback_rejects_failed_console_probe(monkeypatch):
    """A failed screen-buffer probe does not write a partial report."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class Call:
        def __init__(self, result):
            self.result = result

        def __call__(self, *args):
            del args
            return self.result

    class GetInfo(Call):
        def __call__(self, handle, pointer):
            del handle, pointer
            return 0

    kernel = SimpleNamespace(
        GetStdHandle=Call(101),
        GetConsoleScreenBufferInfo=GetInfo(0),
        SetConsoleTextAttribute=Call(1),
    )
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    stream = io.StringIO()
    assert win32.write_console_ansi("plain", stream) is False
    assert stream.getvalue() == ""


@pytest.mark.unittest
def test_win7_console_fallback_reports_restore_failure(monkeypatch):
    """A failed attribute restore returns false before writing text."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class GetInfo:
        def __call__(self, handle, pointer):
            del handle
            pointer._obj.wAttributes = 7
            return 1

    class SetAttribute:
        def __init__(self):
            self.calls = 0

        def __call__(self, handle, attribute):
            del handle, attribute
            self.calls += 1
            return 0 if self.calls == 2 else 1

    setter = SetAttribute()
    kernel = SimpleNamespace(
        GetStdHandle=lambda value: 101,
        GetConsoleScreenBufferInfo=GetInfo(),
        SetConsoleTextAttribute=setter,
    )
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    stream = io.StringIO()
    assert win32.write_console_ansi("\x1b[32mPASS\x1b[0m", stream) is False
    assert stream.getvalue() == ""


@pytest.mark.unittest
def test_win7_console_fallback_reports_final_restore_failure(monkeypatch):
    """A final native attribute restore failure is reported before output."""
    ctypes = _ctypes_for_native_seam(monkeypatch)
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    class GetInfo:
        def __call__(self, handle, pointer):
            del handle
            pointer._obj.wAttributes = 7
            return 1

    class SetAttribute:
        def __init__(self):
            self.calls = 0

        def __call__(self, handle, attribute):
            del handle, attribute
            self.calls += 1
            return self.calls != 3

    setter = SetAttribute()
    kernel = SimpleNamespace(
        GetStdHandle=lambda value: 101,
        GetConsoleScreenBufferInfo=GetInfo(),
        SetConsoleTextAttribute=setter,
    )
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    stream = io.StringIO()
    assert win32.write_console_ansi("\x1b[32mPASS\x1b[0m", stream) is False
    assert stream.getvalue() == ""


@pytest.mark.unittest
def test_console_fallback_rejects_unknown_roles_and_native_exceptions(monkeypatch):
    """Unknown ANSI roles and ctypes failures return plain-fallback control."""
    import io
    from types import SimpleNamespace

    import pyfcstm._selfcheck._win32 as win32

    assert win32.write_console_ansi("plain", io.StringIO()) is False
    ctypes = _ctypes_for_native_seam(monkeypatch)

    class Call:
        def __init__(self, result=1):
            self.result = result

        def __call__(self, *args):
            del args
            return self.result

    class GetInfo(Call):
        def __call__(self, handle, pointer):
            del handle
            pointer._obj.wAttributes = 7
            return 1

    class Kernel:
        GetStdHandle = Call(101)
        GetConsoleScreenBufferInfo = GetInfo()
        SetConsoleTextAttribute = Call(1)

    kernel = Kernel()
    monkeypatch.setattr(win32, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    assert win32.write_console_ansi("\x1b[99munknown", io.StringIO()) is False

    class BrokenKernel(Kernel):
        GetStdHandle = Call(101)
        GetConsoleScreenBufferInfo = GetInfo()
        SetConsoleTextAttribute = Call(1)

    broken = BrokenKernel()
    broken.GetStdHandle = lambda *args: (_ for _ in ()).throw(OSError("console"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=broken), raising=False
    )
    assert win32.write_console_ansi("plain", io.StringIO()) is False
