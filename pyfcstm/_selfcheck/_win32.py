"""Small ctypes helpers for Windows worker cleanup.

The module is importable on every platform; Windows-only calls are resolved
only when :data:`os.name` is ``"nt"``.
"""

import os
import re
import sys
from typing import Optional


class JobAssignmentError(RuntimeError):
    """Raised when a worker cannot be assigned to a Windows Job Object.

    Example::

        >>> isinstance(JobAssignmentError("unavailable"), RuntimeError)
        True
    """


_NTSTATUS_NAMES = {
    0xC0000005: "ACCESS_VIOLATION",
    0xC000001D: "ILLEGAL_INSTRUCTION",
    0xC0000094: "INTEGER_DIVIDE_BY_ZERO",
    0xC0000095: "INTEGER_OVERFLOW",
    0xC00000FD: "STACK_OVERFLOW",
}


def format_ntstatus(return_code: Optional[int]) -> Optional[str]:
    """
    Format a Windows process exit code as an unsigned NTSTATUS diagnostic.

    :param return_code: Process return code, defaults to ``None``.
    :type return_code: Optional[int], optional
    :return: Hexadecimal status and symbolic name when known, otherwise ``None``.
    :rtype: Optional[str]

    Example::

        >>> format_ntstatus(0xC0000005)
        '0xC0000005 (ACCESS_VIOLATION)'
    """
    if return_code is None:
        return None
    value = int(return_code) & 0xFFFFFFFF
    if value < 0xC0000000:
        return None
    name = _NTSTATUS_NAMES.get(value)
    return "0x{:08X}{}".format(value, " (" + name + ")" if name else "")


# ``AssignProcessToJobObject`` requires both PROCESS_TERMINATE and
# PROCESS_SET_QUOTA access on the process handle.
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100
_ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")
_ANSI_ATTRIBUTES = {
    "31": 0x000C,
    "32": 0x000A,
    "33": 0x000E,
    "36": 0x000B,
    "1;32": 0x000A,
    "1;33": 0x000E,
    "1;97;41": 0x00CF,
}


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
            from ctypes import wintypes

            terminate = ctypes.windll.kernel32.TerminateJobObject
            terminate.argtypes = [wintypes.HANDLE, wintypes.UINT]
            terminate.restype = wintypes.BOOL
            if not terminate(self.handle, exit_code):
                raise JobAssignmentError("TerminateJobObject failed")

    def close(self) -> None:
        """Close the native handle."""
        if self.handle and os.name == "nt":
            import ctypes
            from ctypes import wintypes

            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            close_handle(self.handle)
        self.handle = None


def attach_process(process) -> Optional[JobHandle]:
    """Create and assign a Job Object for *process* on Windows.

    :param process: Spawned worker exposing a numeric ``pid`` attribute.
    :type process: subprocess.Popen
    :return: Assigned Job Object wrapper, or ``None`` outside Windows.
    :rtype: Optional[JobHandle]
    :raises JobAssignmentError: If Windows containment cannot be established.

    Example::

        >>> if os.name != "nt":
        ...     assert attach_process(None) is None
    """
    if os.name != "nt":
        return None
    import ctypes

    handle = None
    process_handle = None
    try:
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise JobAssignmentError("CreateJobObject failed")
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
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


def write_console_ansi(text: str, stream=None) -> bool:
    """Write the self-check ANSI roles through Windows console attributes.

    This fallback is used by Windows 7 consoles that do not support virtual
    terminal sequences. Only the color roles emitted by the self-check human
    renderer are translated; unknown sequences restore the original attribute.

    :param text: Human report containing ANSI SGR sequences.
    :type text: str
    :param stream: Text stream to receive non-control text, defaults to stdout.
    :type stream: object, optional
    :return: Whether the complete report was written through a console handle.
    :rtype: bool

    Example::

        >>> write_console_ansi("plain") if os.name == "nt" else False
        False
    """
    if os.name != "nt":
        return False
    import ctypes

    try:
        from ctypes import wintypes

        class _Coord(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class _SmallRect(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        class _ConsoleScreenBufferInfo(ctypes.Structure):
            _fields_ = [
                ("dwSize", _Coord),
                ("dwCursorPosition", _Coord),
                ("wAttributes", wintypes.WORD),
                ("srWindow", _SmallRect),
                ("dwMaximumWindowSize", _Coord),
            ]

        kernel32 = ctypes.windll.kernel32
        get_handle = kernel32.GetStdHandle
        get_handle.argtypes = [wintypes.DWORD]
        get_handle.restype = wintypes.HANDLE
        get_info = kernel32.GetConsoleScreenBufferInfo
        get_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ConsoleScreenBufferInfo),
        ]
        get_info.restype = wintypes.BOOL
        set_attribute = kernel32.SetConsoleTextAttribute
        set_attribute.argtypes = [wintypes.HANDLE, wintypes.WORD]
        set_attribute.restype = wintypes.BOOL
        handle = get_handle(-11)
        info = _ConsoleScreenBufferInfo()
        if not handle or not get_info(handle, ctypes.byref(info)):
            return False
        original = int(info.wAttributes)
        target = stream if stream is not None else sys.stdout
        segments = []
        position = 0
        for match in _ANSI_RE.finditer(text):
            code = match.group(1)
            attribute = original if code in ("", "0") else _ANSI_ATTRIBUTES.get(code)
            if attribute is None:
                return False
            segments.append((text[position : match.start()], attribute))
            position = match.end()
        segments.append((text[position:], None))

        # Validate every requested role before writing. A stable native failure
        # can then fall back to one complete plain report instead of duplicating
        # a partially colored prefix.
        for _, attribute in segments:
            if attribute is not None and not set_attribute(handle, attribute):
                set_attribute(handle, original)
                return False
        if not set_attribute(handle, original):
            return False

        for segment, attribute in segments:
            target.write(segment)
            if attribute is not None:
                set_attribute(handle, attribute)
        set_attribute(handle, original)
        target.flush()
        return True
    except (
        AttributeError,
        ImportError,
        OSError,
        TypeError,
        ValueError,
        ctypes.ArgumentError,
    ):
        return False
