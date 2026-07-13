"""Hidden worker entry point for isolated self-check execution."""

import faulthandler
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from typing import Any, Mapping, Optional

from . import registry
from .protocol import WORKER_SCHEMA
from .protocol import build_start_gate
from .protocol import encode_result_frame
from .protocol import is_valid_nonce


START_GATE_TIMEOUT = 2.0
_TEST_MODE_ENV = "PYFCSTM_SELFCHECK_TEST_MODE"
_TEST_HOOK_ENV = "PYFCSTM_SELFCHECK_TEST_HOOK"


def _read_start_gate(nonce: str, timeout: float = START_GATE_TIMEOUT) -> Optional[str]:
    """Read and validate one exact GO frame from worker stdin."""
    expected = build_start_gate(nonce)
    result = queue.Queue(maxsize=1)

    def read_gate() -> None:
        try:
            received = sys.stdin.buffer.readline(len(expected) + 1)
            if received == expected:
                trailing = sys.stdin.buffer.read(1)
                if trailing:
                    result.put("start_gate_trailing_data")
                    return
        except (AttributeError, OSError, ValueError) as err:
            # Closed or invalid stdin is a protocol-level startup failure.
            result.put("start_gate_read:{}".format(type(err).__name__))
            return
        result.put(None if received == expected else "start_gate_mismatch")

    reader = threading.Thread(
        target=read_gate, name="selfcheck-start-gate", daemon=True
    )
    reader.start()
    reader.join(timeout=max(0.0, timeout))
    if reader.is_alive():
        return "start_gate_timeout"
    try:
        return result.get_nowait()
    except queue.Empty:
        return "start_gate_read:missing_result"


def _write_frame(mode: str, result_file: Optional[str], frame: bytes) -> Optional[str]:
    """Write one frame through the selected result transport."""
    try:
        if mode == "file":
            if not result_file:
                return "missing_result_file"
            flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0)
            descriptor = os.open(result_file, flags)
            try:
                os.write(descriptor, frame)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return None
        output = sys.stdout.buffer
        output.write(frame)
        output.flush()
        return None
    except (AttributeError, OSError, ValueError) as err:
        # Pipe/file failures are observable protocol diagnostics, never silent PASS.
        return "result_write:{}".format(type(err).__name__)


def _envelope(
    check_id: str,
    nonce: str,
    status: str,
    summary: str = "",
    details: str = "",
    return_code: int = 0,
    reason: Optional[str] = None,
):
    return {
        "schema": WORKER_SCHEMA,
        "check_id": check_id,
        "nonce": nonce,
        "status": status,
        "summary": summary,
        "details": details,
        "return_code": return_code,
        "reason": reason,
    }


def run_worker(arguments: Mapping[str, Any]) -> int:
    """
    Execute a statically registered worker after the GO handshake.

    :param arguments: Validated worker options as a mapping.
    :type arguments: Mapping[str, Any]
    :return: Worker process return code. Envelope status remains authoritative.
    :rtype: int
    """
    check_id = str(arguments["check_id"])
    worker_key = str(arguments["worker_key"])
    nonce = str(arguments["nonce"])
    result_mode = str(arguments["result_mode"])
    result_file = arguments.get("result_file")
    if not is_valid_nonce(nonce):
        return 3
    try:
        faulthandler.enable(file=sys.stderr, all_threads=True)
    except (OSError, RuntimeError, ValueError):
        # Embedded or restricted stderr streams can reject faulthandler; protocol output remains valid.
        pass

    start_error = _read_start_gate(nonce)
    if start_error is not None:
        frame = encode_result_frame(
            _envelope(
                check_id,
                nonce,
                "ERROR",
                reason=start_error,
                details=start_error,
                return_code=3,
            )
        )
        _write_frame(result_mode, result_file, frame)
        return 3

    injected_mode = arguments.get("test_mode")
    if injected_mode is None:
        # The production hidden CLI has no test-mode argument.  The parent
        # supervisor uses a nonce-bound environment hook only for test fault
        # injection; stale user environments are discarded before dispatch.
        hook_nonce = os.environ.pop(_TEST_HOOK_ENV, None)
        candidate_mode = os.environ.pop(_TEST_MODE_ENV, None)
        if hook_nonce == nonce:
            injected_mode = candidate_mode
            if injected_mode is not None:
                # Keep the nonce-authorized test mode visible to the registry
                # callback; the child process boundary prevents production
                # environment leakage.
                os.environ[_TEST_MODE_ENV] = str(injected_mode)
    else:
        # Direct in-process tests may still pass the private mapping value.
        os.environ.pop(_TEST_HOOK_ENV, None)
        os.environ[_TEST_MODE_ENV] = str(injected_mode)
    if injected_mode == "crash":
        os._exit(37)
    if injected_mode == "crash_spawn":
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        child_pid_file = os.environ.get("PYFCSTM_SELFCHECK_CHILD_PID_FILE")
        if child_pid_file:
            with open(child_pid_file, "w", encoding="ascii") as stream:
                stream.write(str(child.pid))
                stream.flush()
        os._exit(37)
    if injected_mode == "abort":
        os.abort()
    if injected_mode == "huge_output":
        os.write(2, b"x" * (2 * 1024 * 1024 + 4096))
    if injected_mode == "huge_stdout":
        sys.stdout.buffer.write(b"x" * (2 * 1024 * 1024 + 4096) + b"\n")
        sys.stdout.buffer.flush()
    if injected_mode == "invalid_utf8":
        os.write(2, b"diagnostic-\xff-\xfe\n")
    if injected_mode == "spawn":
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        child_pid_file = os.environ.get("PYFCSTM_SELFCHECK_CHILD_PID_FILE")
        if child_pid_file:
            with open(child_pid_file, "w", encoding="ascii") as stream:
                stream.write(str(child.pid))
                stream.flush()
        while True:
            time.sleep(1.0)
    if injected_mode == "hang":
        while True:
            time.sleep(1.0)

    try:
        worker = registry.get_worker(worker_key)
    except KeyError:
        frame = encode_result_frame(
            _envelope(
                check_id,
                nonce,
                "ERROR",
                summary="unknown worker key",
                reason="unknown_worker",
                return_code=3,
            )
        )
        _write_frame(result_mode, result_file, frame)
        return 3

    try:
        if injected_mode == "system_exit":
            raise SystemExit(7)
        if injected_mode == "keyboard_interrupt":
            raise KeyboardInterrupt()
        summary = str(worker())
    except SystemExit as err:
        code = err.code if isinstance(err.code, int) else 1
        frame = encode_result_frame(
            _envelope(
                check_id,
                nonce,
                "ERROR",
                summary="worker raised SystemExit",
                details=traceback.format_exc(),
                reason="worker_system_exit",
                return_code=code,
            )
        )
        write_error = _write_frame(result_mode, result_file, frame)
        return code if write_error is None else 3
    except KeyboardInterrupt:
        frame = encode_result_frame(
            _envelope(
                check_id,
                nonce,
                "ERROR",
                summary="worker interrupted",
                details=traceback.format_exc(),
                reason="worker_interrupted",
                return_code=130,
            )
        )
        write_error = _write_frame(result_mode, result_file, frame)
        return 130 if write_error is None else 3
    except BaseException as err:
        if not isinstance(err, Exception):
            raise
        # Registered check callbacks may raise any ordinary Exception subclass;
        # every such callback failure is deliberately serialized at this worker
        # boundary, while non-Exception control sentinels remain visible.
        frame = encode_result_frame(
            _envelope(
                check_id,
                nonce,
                "ERROR",
                summary="worker exception: {}".format(err),
                details=traceback.format_exc(),
                reason="worker_exception",
                return_code=1,
            )
        )
        write_error = _write_frame(result_mode, result_file, frame)
        return 1 if write_error is None else 3

    if summary.startswith("__SELFCHECK_WARN__:"):
        summary = summary.split(":", 1)[1]
        status = "WARN"
    else:
        status = "PASS"
    frame_nonce = "f" * 32 if injected_mode == "wrong_nonce" else nonce
    frame = encode_result_frame(
        _envelope(check_id, frame_nonce, status, summary=summary, return_code=0)
    )
    if injected_mode == "no_result":
        return 0
    if injected_mode == "truncated":
        truncated = frame[:-1]
        if result_mode == "file" and result_file:
            with open(result_file, "ab") as stream:
                stream.write(truncated)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            sys.stdout.buffer.write(truncated)
            sys.stdout.buffer.flush()
        return 3
    if injected_mode == "malformed":
        malformed = b"not-a-self-check-frame\n"
        if result_mode == "file" and result_file:
            with open(result_file, "ab") as stream:
                stream.write(malformed)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            sys.stdout.buffer.write(malformed)
            sys.stdout.buffer.flush()
        return 0
    write_error = _write_frame(result_mode, result_file, frame)
    if write_error is None and injected_mode == "duplicate":
        write_error = _write_frame(result_mode, result_file, frame)
    if write_error is not None:
        return 3
    if injected_mode == "nonzero_envelope":
        return 7
    return 0
