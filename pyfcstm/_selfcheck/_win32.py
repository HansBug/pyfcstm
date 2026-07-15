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
_MISSING = object()


def _call_with_ctypes_signature(function, argtypes, restype, *arguments):
    """Call one shared ctypes function without leaking signature mutations."""
    previous = tuple(
        getattr(function, name, _MISSING) for name in ("argtypes", "restype")
    )
    try:
        function.argtypes = argtypes
        function.restype = restype
        return function(*arguments)
    finally:
        for name, value in zip(("argtypes", "restype"), previous):
            if value is _MISSING:
                delattr(function, name)
            else:
                setattr(function, name, value)


def _close_handle(kernel32, handle, wintypes):
    """Close one native handle without leaking ctypes signature state."""
    _call_with_ctypes_signature(
        kernel32.CloseHandle, [wintypes.HANDLE], wintypes.BOOL, handle
    )


class JobHandle:
    """
    Best-effort Job Object wrapper with explicit termination fallback.

    :param handle: Native Windows Job Object handle.
    :type handle: object
    Example::

        >>> JobHandle(None).handle is None
        True
    """

    def __init__(self, handle):
        """Initialize a Job Object wrapper."""
        self.handle = handle

    def terminate(self, exit_code: int = 1) -> None:
        """Terminate every process currently assigned to the job."""
        if self.handle and os.name == "nt":
            import ctypes
            from ctypes import wintypes

            terminate = ctypes.windll.kernel32.TerminateJobObject
            if not _call_with_ctypes_signature(
                terminate,
                [wintypes.HANDLE, wintypes.UINT],
                wintypes.BOOL,
                self.handle,
                exit_code,
            ):
                raise JobAssignmentError("TerminateJobObject failed")

    def close(self) -> None:
        """Close the native handle."""
        if self.handle and os.name == "nt":
            import ctypes
            from ctypes import wintypes

            _close_handle(ctypes.windll.kernel32, self.handle, wintypes)
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
        call = _call_with_ctypes_signature
        handle = call(
            kernel32.CreateJobObjectW,
            [ctypes.c_void_p, wintypes.LPCWSTR],
            wintypes.HANDLE,
            None,
            None,
        )
        if not handle:
            raise JobAssignmentError("CreateJobObject failed")
        process_handle = call(
            kernel32.OpenProcess,
            [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD],
            wintypes.HANDLE,
            _PROCESS_TERMINATE | _PROCESS_SET_QUOTA,
            False,
            process.pid,
        )
        if not process_handle:
            raise JobAssignmentError("OpenProcess failed")
        if not call(
            kernel32.AssignProcessToJobObject,
            [wintypes.HANDLE, wintypes.HANDLE],
            wintypes.BOOL,
            handle,
            process_handle,
        ):
            error = ctypes.get_last_error()
            raise JobAssignmentError(
                "AssignProcessToJobObject failed: {}".format(error)
            )
        job = JobHandle(handle)
        handle = None
        return job
    except JobAssignmentError:
        # The job handle is owned by this function until JobHandle takes it.
        if handle is not None:
            _close_handle(kernel32, handle, wintypes)
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
            _close_handle(kernel32, handle, wintypes)
        raise JobAssignmentError(
            "Windows Job Object setup raised {}: {}".format(type(err).__name__, err)
        )
    finally:
        if process_handle is not None:
            _close_handle(kernel32, process_handle, wintypes)


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
        get_info = kernel32.GetConsoleScreenBufferInfo
        get_info_argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ConsoleScreenBufferInfo),
        ]
        set_attribute = kernel32.SetConsoleTextAttribute
        set_attribute_argtypes = [wintypes.HANDLE, wintypes.WORD]
        handle = _call_with_ctypes_signature(
            get_handle, [wintypes.DWORD], wintypes.HANDLE, -11
        )
        info = _ConsoleScreenBufferInfo()
        if not handle or not _call_with_ctypes_signature(
            get_info, get_info_argtypes, wintypes.BOOL, handle, ctypes.byref(info)
        ):
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
            if attribute is not None and not _call_with_ctypes_signature(
                set_attribute,
                set_attribute_argtypes,
                wintypes.BOOL,
                handle,
                attribute,
            ):
                _call_with_ctypes_signature(
                    set_attribute,
                    set_attribute_argtypes,
                    wintypes.BOOL,
                    handle,
                    original,
                )
                return False
        if not _call_with_ctypes_signature(
            set_attribute,
            set_attribute_argtypes,
            wintypes.BOOL,
            handle,
            original,
        ):
            return False

        for segment, attribute in segments:
            target.write(segment)
            if attribute is not None:
                _call_with_ctypes_signature(
                    set_attribute,
                    set_attribute_argtypes,
                    wintypes.BOOL,
                    handle,
                    attribute,
                )
        _call_with_ctypes_signature(
            set_attribute,
            set_attribute_argtypes,
            wintypes.BOOL,
            handle,
            original,
        )
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
