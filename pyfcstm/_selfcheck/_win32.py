"""Small ctypes helpers for Windows worker cleanup.

The module is importable on every platform; Windows-only calls are resolved
only when :data:`os.name` is ``"nt"``.
"""

import os
from typing import Optional


class JobAssignmentError(RuntimeError):
    """Raised when a worker cannot be assigned to a Windows Job Object."""


# ``AssignProcessToJobObject`` requires both PROCESS_TERMINATE and
# PROCESS_SET_QUOTA access on the process handle.
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


class JobHandle:
    """
    Best-effort Job Object wrapper with explicit termination fallback.

    :param handle: Native Windows Job Object handle.
    :type handle: object
    :param kill_on_close: Whether the kernel kill-on-close flag was enabled.
    :type kill_on_close: bool

    Example::

        >>> JobHandle(None, False).kill_on_close
        False
    """

    def __init__(self, handle, kill_on_close: bool):
        """Initialize a Job Object wrapper."""
        self.handle = handle
        self.kill_on_close = kill_on_close

    def terminate(self, exit_code: int = 1) -> None:
        """Terminate every process currently assigned to the job."""
        if self.handle and os.name == "nt":
            import ctypes

            if not ctypes.windll.kernel32.TerminateJobObject(self.handle, exit_code):
                raise JobAssignmentError("TerminateJobObject failed")

    def close(self) -> None:
        """Close the native handle."""
        if self.handle and os.name == "nt":
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self.handle)
        self.handle = None


def attach_process(process) -> Optional[JobHandle]:
    """Create and assign a Job Object for *process* on Windows."""
    if os.name != "nt":
        return None
    import ctypes

    handle = None
    process_handle = None
    try:
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise JobAssignmentError("CreateJobObject failed")
        process_handle = kernel32.OpenProcess(
            _PROCESS_TERMINATE | _PROCESS_SET_QUOTA, False, process.pid
        )
        if not process_handle:
            raise JobAssignmentError("OpenProcess failed")
        if not kernel32.AssignProcessToJobObject(handle, process_handle):
            error = ctypes.get_last_error()
            raise JobAssignmentError(
                "AssignProcessToJobObject failed: {}".format(error)
            )
        kill_on_close = _enable_kill_on_close(kernel32, handle)
        job = JobHandle(handle, kill_on_close=kill_on_close)
        handle = None
        return job
    except JobAssignmentError:
        # The job handle is owned by this function until JobHandle takes it.
        if handle is not None:
            kernel32.CloseHandle(handle)
        raise
    except (
        AttributeError,
        ImportError,
        OSError,
        TypeError,
        ValueError,
        ctypes.ArgumentError,
    ) as err:
        # ctypes setup and native calls are normalized before the supervisor sees them.
        if handle is not None:
            kernel32.CloseHandle(handle)
        raise JobAssignmentError(
            "Windows Job Object setup raised {}: {}".format(type(err).__name__, err)
        )
    finally:
        if process_handle is not None:
            kernel32.CloseHandle(process_handle)


def _enable_kill_on_close(kernel32, handle) -> bool:
    """Enable ``KILL_ON_JOB_CLOSE`` when the target Windows exposes it.

    The explicit :meth:`JobHandle.terminate` path remains the compatibility
    fallback for Windows 7 or restricted/nested Job Object environments.
    """
    import ctypes
    from ctypes import wintypes

    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    information = _ExtendedLimitInformation()
    information.BasicLimitInformation.LimitFlags = 0x00002000
    try:
        setter = kernel32.SetInformationJobObject
        setter.restype = wintypes.BOOL
        setter.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        return bool(
            setter(
                handle,
                9,
                ctypes.byref(information),
                ctypes.sizeof(information),
            )
        )
    except (AttributeError, OSError, TypeError, ValueError, ctypes.ArgumentError):
        # Older Windows or a restricted API surface uses explicit termination.
        return False
