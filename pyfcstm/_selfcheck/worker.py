"""Run one statically registered callback in a hidden one-shot worker.

The worker waits for its nonce-bound GO gate, executes exactly one callback,
and emits at most one structured result frame. It never schedules other checks
or recursively starts another worker.
"""

import faulthandler
import os
import sys
import traceback
from typing import Any, Mapping, Optional

from . import registry
from .model import CheckOutcome
from .protocol import WORKER_SCHEMA
from .protocol import build_start_gate
from .protocol import encode_result_frame
from .protocol import is_valid_nonce


OUTPUT_LIMIT = 8 * 1024 * 1024


class _OutputLimitExceeded(OSError):
    """Signal that one worker output stream crossed its physical quota."""


class _OutputBudget:
    """Bound writes to stdout/stderr while preserving the original descriptor."""

    def __init__(self, write, limit: int):
        """Create a byte budget backed by the original ``os.write``."""
        self._write = write
        self._limit = limit
        self._used = {1: 0, 2: 0}

    def write(self, descriptor: int, data: bytes) -> int:
        """Write within the descriptor quota or raise on overflow."""
        if descriptor not in self._used:
            return self._write(descriptor, data)
        remaining = self._limit - self._used[descriptor]
        if remaining <= 0:
            raise _OutputLimitExceeded("worker output quota exceeded")
        if len(data) > remaining:
            written = self._write(descriptor, data[:remaining])
            self._used[descriptor] += max(0, written)
            raise _OutputLimitExceeded("worker output quota exceeded")
        written = self._write(descriptor, data)
        self._used[descriptor] += max(0, written)
        return written


class _LimitedBinary:
    """Binary stream facade used by the worker's text output wrappers."""

    def __init__(self, stream, budget: _OutputBudget, descriptor: int):
        """Wrap a binary stream with a descriptor-specific byte budget."""
        self._stream = stream
        self._budget = budget
        self._descriptor = descriptor

    def write(self, data):
        """Write bytes through the descriptor quota."""
        return self._budget.write(self._descriptor, bytes(data))

    def flush(self):
        """Flush the wrapped stream when it exposes a flush operation."""
        flush = getattr(self._stream, "flush", None)
        if flush is not None:
            return flush()
        return None

    def fileno(self):
        """Return the original descriptor number."""
        return self._stream.fileno()

    def __getattr__(self, name):
        return getattr(self._stream, name)


class _LimitedText:
    """Text stream facade that routes encoded bytes through a quota."""

    def __init__(self, stream, budget: _OutputBudget, descriptor: int):
        """Wrap a text stream while preserving its encoding and error policy."""
        self._stream = stream
        self.buffer = _LimitedBinary(stream, budget, descriptor)
        self.encoding = getattr(stream, "encoding", None) or "utf-8"
        self.errors = getattr(stream, "errors", None) or "backslashreplace"

    def write(self, text):
        """Encode and write text, returning the normal character count."""
        self.buffer.write(str(text).encode(self.encoding, self.errors))
        return len(text)

    def flush(self):
        """Flush the limited binary facade."""
        return self.buffer.flush()

    def fileno(self):
        """Return the original descriptor number."""
        return self._stream.fileno()

    def isatty(self):
        """Preserve terminal detection for callbacks that inspect stdout."""
        return bool(getattr(self._stream, "isatty", lambda: False)())

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _install_output_limiters():
    """Install temporary cross-platform Python output limits for one callback."""
    original_write = os.write
    original_streams = (sys.stdout, sys.stderr)
    budget = _OutputBudget(original_write, OUTPUT_LIMIT)

    def limited_write(descriptor, data):
        return budget.write(descriptor, data)

    os.write = limited_write
    for descriptor, name in ((1, "stdout"), (2, "stderr")):
        stream = getattr(sys, name, None)
        if stream is not None:
            setattr(sys, name, _LimitedText(stream, budget, descriptor))
    return original_write, original_streams


def _restore_output_limiters(state) -> None:
    """Restore process-global output objects after a direct worker invocation."""
    original_write, original_streams = state
    os.write = original_write
    sys.stdout, sys.stderr = original_streams


def _write_stream_all(stream, data) -> None:
    """Write all bytes/text or report a diagnostic-channel short write."""
    offset = 0
    while offset < len(data):
        written = stream.write(data[offset:])
        if not isinstance(written, int) or written <= 0 or written > len(data) - offset:
            raise OSError("worker output short write")
        offset += written


def _write_fd_all(descriptor: int, data: bytes) -> None:
    """Write all bytes to a worker descriptor."""
    offset = 0
    while offset < len(data):
        written = os.write(descriptor, data[offset:])
        if not isinstance(written, int) or written <= 0 or written > len(data) - offset:
            raise OSError("worker descriptor short write")
        offset += written


def _read_start_gate(nonce: str) -> Optional[str]:
    """Read one exact nonce-bound GO frame from worker stdin."""
    expected = build_start_gate(nonce)
    try:
        received = sys.stdin.buffer.read(len(expected) + 1)
    except (AttributeError, OSError, ValueError) as err:
        # Redirected stdin can lack a binary buffer, native reads can fail, and
        # closed streams reject reads with ValueError.
        return "start_gate_read:{}".format(type(err).__name__)
    if received == expected:
        return None
    if received.startswith(expected):
        return "start_gate_trailing_data"
    return "start_gate_mismatch"


def _write_frame(mode: str, result_file: Optional[str], frame: bytes) -> Optional[str]:
    """Write one result frame through the selected transport."""
    try:
        if mode == "file":
            if not result_file:
                return "missing_result_file"
            flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0)
            descriptor = os.open(result_file, flags)
            try:
                _write_fd_all(descriptor, frame)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        else:
            _write_stream_all(sys.stdout.buffer, frame)
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


def _execute_worker_callback(worker):
    """Run one callback under a temporary bounded output facade."""
    state = _install_output_limiters()
    try:
        try:
            outcome = worker()
            if not isinstance(outcome, CheckOutcome):
                raise TypeError("self-check worker must return CheckOutcome")
            return outcome, 0
        except _OutputLimitExceeded:
            return (
                CheckOutcome(
                    "ERROR",
                    "worker output capture limit exceeded",
                    reason="output_capture_limit",
                ),
                1,
            )
        except SystemExit as err:
            return_code = err.code if isinstance(err.code, int) else 1
            return _exception_outcome("worker raised SystemExit", "worker_system_exit"), return_code
        except KeyboardInterrupt:
            return _exception_outcome("worker interrupted", "worker_interrupted"), 130
        except BaseException as err:
            # Registered checks may raise any ordinary Exception; non-runtime
            # control sentinels remain visible instead of being swallowed.
            if not isinstance(err, Exception):
                raise
            return (
                _exception_outcome(
                    "worker exception: {}".format(err), "worker_exception"
                ),
                1,
            )
    finally:
        _restore_output_limiters(state)


def _emit_outcome(
    check_id: str,
    nonce: str,
    result_mode: str,
    result_file: Optional[str],
    outcome: CheckOutcome,
    return_code: int,
) -> int:
    """Encode and write one outcome, returning a stable worker exit code."""
    try:
        frame = encode_result_frame(_envelope(check_id, nonce, outcome, return_code))
    except ValueError as err:
        if str(err) != "envelope_too_large":
            # encode_result_frame has one documented size failure; unexpected
            # value errors must remain visible to the worker supervisor.
            raise
        outcome = CheckOutcome(
            "ERROR",
            "worker result exceeded the protocol envelope limit",
            reason="result_envelope_too_large",
            expected="encoded result at most 8 MiB",
            observed=(
                "summary_chars={} evidence_chars={} exception_chars={}".format(
                    len(outcome.summary or ""),
                    len(outcome.evidence or ""),
                    len(outcome.exception or ""),
                )
            ),
            remediation="inspect the bounded worker stdout/stderr diagnostics",
        )
        return_code = 1
        frame = encode_result_frame(_envelope(check_id, nonce, outcome, return_code))
    write_error = _write_frame(result_mode, result_file, frame)
    if write_error is None:
        return return_code
    try:
        _write_fd_all(2, (write_error + "\n").encode("ascii", "backslashreplace"))
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

    outcome, return_code = _execute_worker_callback(worker)
    return _emit_outcome(
        check_id, nonce, result_mode, result_file, outcome, return_code
    )
