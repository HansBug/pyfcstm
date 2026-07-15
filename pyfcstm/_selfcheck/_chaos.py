"""Private deterministic fault scenarios for self-check process tests.

The scenarios are reachable only through static worker keys registered by the
self-check package.  They are not a public plug-in mechanism and are never
selected by normal profiles.
"""

import os
import subprocess
import sys
import time

from .model import CheckOutcome
from .protocol import FRAME_PREFIX


def hang() -> CheckOutcome:
    """Keep the worker alive until the supervisor's timeout cleanup runs."""
    while True:
        time.sleep(1.0)


def crash() -> CheckOutcome:
    """Terminate the worker without emitting a result envelope."""
    os._exit(37)


def grandchild() -> CheckOutcome:
    """Leave a sleeping child behind while the worker itself remains blocked."""
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid_path = os.environ.get("PYFCSTM_SELFCHECK_CHAOS_CHILD_PID")
    if pid_path:
        with open(pid_path, "w", encoding="ascii") as stream:
            stream.write(str(child.pid))
    return hang()


def large_output() -> CheckOutcome:
    """Write beyond the physical output spool limit before returning."""
    os.write(1, b"x" * (8 * 1024 * 1024))
    os.write(1, b"x")
    return CheckOutcome("PASS", "large output scenario completed")


def invalid_frame() -> CheckOutcome:
    """Write a malformed result frame before the worker emits its real frame."""
    os.write(1, FRAME_PREFIX + b"not-json\n")
    return CheckOutcome("PASS", "invalid frame scenario completed")


__all__ = ["crash", "grandchild", "hang", "invalid_frame", "large_output"]
