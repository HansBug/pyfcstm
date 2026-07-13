"""Static self-check registry and the PR-2 artifact probe."""

from typing import Callable, Dict, Tuple

from .model import CheckSpec


Worker = Callable[[], object]
_WORKERS: Dict[str, Worker] = {}


def _artifact_self_dispatch() -> str:
    """Confirm the worker can import the package without recursing into the CLI."""
    import pyfcstm
    import os
    import time

    mode = os.environ.get("PYFCSTM_SELFCHECK_TEST_MODE")
    if mode == "hang":
        while True:
            time.sleep(1.0)
    if mode == "fail":
        raise RuntimeError("injected self-check failure")
    if mode == "warn":
        return "__SELFCHECK_WARN__:injected warning"

    if not getattr(pyfcstm, "__version__", None):
        raise RuntimeError("package version is unavailable")
    return "worker imported pyfcstm and stopped at the hidden dispatch"


_WORKERS["self_dispatch"] = _artifact_self_dispatch


def register_test_override(worker_key: str, worker: Worker) -> None:
    """
    Register a test-only callable without exposing production CLI parsing.

    :param worker_key: Temporary registry key.
    :type worker_key: str
    :param worker: Zero-argument callable used by a test.
    :type worker: Worker
    :return: ``None``.
    :rtype: None
    """
    _WORKERS[worker_key] = worker


def get_worker(worker_key: str) -> Worker:
    """
    Return a statically registered worker.

    :param worker_key: Static worker key.
    :type worker_key: str
    :return: Registered callable.
    :rtype: Worker
    :raises KeyError: If the key is not registered.
    """
    return _WORKERS[worker_key]


def selected_specs(profile: str) -> Tuple[CheckSpec, ...]:
    """
    Return checks implemented by the current registry for *profile*.

    :param profile: Requested profile name.
    :type profile: str
    :return: Stable check specifications.
    :rtype: Tuple[CheckSpec, ...]
    """
    del profile
    return (CheckSpec("artifact.self_dispatch", "self_dispatch", required=True),)
