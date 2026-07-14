"""Run one statically registered callback in a hidden one-shot worker.

The worker waits for its nonce-bound GO gate, executes exactly one callback,
and emits at most one structured result frame. It never schedules other checks
or recursively starts another worker.
"""

import faulthandler
import os
import queue
import sys
import threading
import traceback
from typing import Any, Mapping, Optional

from . import registry
from .model import CheckOutcome
from .protocol import WORKER_SCHEMA
from .protocol import build_start_gate
from .protocol import encode_result_frame
from .protocol import is_valid_nonce


START_GATE_TIMEOUT = 2.0


def _read_start_gate(nonce: str, timeout: float = START_GATE_TIMEOUT) -> Optional[str]:
    """Read one exact nonce-bound GO frame from worker stdin."""
    expected = build_start_gate(nonce)
    result = queue.Queue(maxsize=1)

    def read_gate() -> None:
        try:
            received = sys.stdin.buffer.readline(len(expected) + 1)
            if received == expected and sys.stdin.buffer.read(1):
                result.put("start_gate_trailing_data")
                return
        except (AttributeError, OSError, ValueError) as err:
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
    """Write one result frame through the selected transport."""
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
        else:
            sys.stdout.buffer.write(frame)
            sys.stdout.buffer.flush()
        return None
    except (AttributeError, OSError, ValueError) as err:
        return "result_write:{}".format(type(err).__name__)


def _envelope(check_id: str, nonce: str, outcome: CheckOutcome, return_code: int):
    """Build the canonical worker protocol envelope for *outcome*."""
    return {
        "schema": WORKER_SCHEMA,
        "check_id": check_id,
        "nonce": nonce,
        "status": outcome.status,
        "summary": outcome.summary,
        "reason": outcome.reason,
        "expected": outcome.expected,
        "observed": outcome.observed,
        "evidence": outcome.evidence,
        "remediation": outcome.remediation,
        "exception": outcome.exception,
        "return_code": return_code,
    }


def _exception_outcome(summary: str, reason: str) -> CheckOutcome:
    """Return an ``ERROR`` outcome carrying the active traceback."""
    evidence = traceback.format_exc()
    return CheckOutcome(
        "ERROR",
        summary,
        reason=reason,
        evidence=evidence,
        exception=evidence,
    )


def _emit_outcome(
    check_id: str,
    nonce: str,
    result_mode: str,
    result_file: Optional[str],
    outcome: CheckOutcome,
    return_code: int,
) -> int:
    """Encode and write one outcome, returning a stable worker exit code."""
    frame = encode_result_frame(_envelope(check_id, nonce, outcome, return_code))
    write_error = _write_frame(result_mode, result_file, frame)
    if write_error is None:
        return return_code
    try:
        os.write(2, (write_error + "\n").encode("ascii", "backslashreplace"))
    except OSError:
        pass
    return 3


def run_worker(arguments: Mapping[str, Any]) -> int:
    """Execute one statically registered check after the containment gate.

    :param arguments: Validated hidden-worker options.
    :type arguments: Mapping[str, Any]
    :return: Worker process return code; the envelope status is authoritative.
    :rtype: int

    Example::

        >>> options = {
        ...     "check_id": "demo",
        ...     "worker_key": "demo",
        ...     "nonce": "invalid",
        ...     "result_mode": "stdout",
        ... }
        >>> run_worker(options)
        3
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
        # Restricted stderr can reject faulthandler without invalidating the protocol.
        pass

    start_error = _read_start_gate(nonce)
    if start_error is not None:
        return _emit_outcome(
            check_id,
            nonce,
            result_mode,
            result_file,
            CheckOutcome(
                "ERROR", start_error, reason=start_error, evidence=start_error
            ),
            3,
        )

    try:
        worker = registry.get_worker(worker_key)
    except KeyError:
        outcome = CheckOutcome("ERROR", "unknown worker key", reason="unknown_worker")
        return _emit_outcome(check_id, nonce, result_mode, result_file, outcome, 3)

    try:
        outcome = worker()
        if not isinstance(outcome, CheckOutcome):
            raise TypeError("self-check worker must return CheckOutcome")
        return_code = 0
    except SystemExit as err:
        return_code = err.code if isinstance(err.code, int) else 1
        outcome = _exception_outcome("worker raised SystemExit", "worker_system_exit")
    except KeyboardInterrupt:
        return_code = 130
        outcome = _exception_outcome("worker interrupted", "worker_interrupted")
    except BaseException as err:
        # Registered checks may raise any ordinary Exception; non-runtime
        # control sentinels remain visible instead of being swallowed.
        if not isinstance(err, Exception):
            raise
        return_code = 1
        outcome = _exception_outcome(
            "worker exception: {}".format(err), "worker_exception"
        )
    return _emit_outcome(
        check_id, nonce, result_mode, result_file, outcome, return_code
    )
