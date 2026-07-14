"""Fault-producing subprocess used only by self-check process tests."""

import argparse
import os
import subprocess
import sys
import time

from pyfcstm._selfcheck.model import CheckOutcome
from pyfcstm._selfcheck.protocol import (
    WORKER_SCHEMA,
    build_start_gate,
    encode_result_frame,
)


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--result-mode", choices=("file", "stdout"), required=True)
    parser.add_argument("--result-file")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--child-pid-file")
    return parser


def _frame(options, nonce=None, status="PASS"):
    outcome = CheckOutcome(status, "fixture {}".format(options.scenario))
    return encode_result_frame(
        {
            "schema": WORKER_SCHEMA,
            "check_id": options.check_id,
            "nonce": nonce or options.nonce,
            "status": outcome.status,
            "summary": outcome.summary,
            "reason": outcome.reason,
            "expected": outcome.expected,
            "observed": outcome.observed,
            "evidence": outcome.evidence,
            "remediation": outcome.remediation,
            "exception": outcome.exception,
            "return_code": 0,
        }
    )


def _write(options, data):
    if options.result_mode == "file":
        with open(options.result_file, "ab") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def _spawn_child(options):
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if options.child_pid_file:
        with open(options.child_pid_file, "w", encoding="ascii") as stream:
            stream.write(str(child.pid))
            stream.flush()


def main():
    options = _parser().parse_args()
    if sys.stdin.buffer.read() != build_start_gate(options.nonce):
        return 3

    scenario = options.scenario
    if scenario == "crash":
        os._exit(37)
    if scenario == "abort":
        os.abort()
    if scenario == "hang":
        while True:
            time.sleep(1.0)
    if scenario in ("spawn_hang", "crash_spawn"):
        _spawn_child(options)
        if scenario == "crash_spawn":
            os._exit(37)
        while True:
            time.sleep(1.0)
    if scenario == "huge_stderr":
        os.write(2, b"x" * (2 * 1024 * 1024 + 4096))
    if scenario == "huge_stdout":
        sys.stdout.buffer.write(b"x" * (2 * 1024 * 1024 + 4096))
        sys.stdout.buffer.flush()
    if scenario == "invalid_utf8":
        os.write(2, b"diagnostic-\xff-\xfe\n")
    if scenario == "no_result":
        return 0
    if scenario == "exit3_no_frame":
        return 3
    if scenario == "malformed":
        _write(options, b"not-a-self-check-frame\n")
        return 0

    frame = _frame(
        options,
        nonce="f" * 32 if scenario == "wrong_nonce" else None,
        status="ERROR" if scenario == "error" else "PASS",
    )
    if scenario == "truncated":
        _write(options, frame[:-1])
        return 3
    _write(options, frame)
    if scenario == "duplicate":
        _write(options, frame)
    if scenario == "nonzero_envelope":
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
