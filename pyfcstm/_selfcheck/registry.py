"""Declare the static self-check inventory and built-in callbacks.

Worker keys map only to callables defined by the package. The hidden worker
does not accept module paths, source text, or third-party plug-ins.
"""

from typing import Callable, Dict, Tuple

from .model import CheckOutcome, CheckSpec


Worker = Callable[[], CheckOutcome]
_WORKERS: Dict[str, Worker] = {}


def _artifact_self_dispatch() -> CheckOutcome:
    """Confirm the worker can import the package without recursing into the CLI."""
    import pyfcstm

    if not getattr(pyfcstm, "__version__", None):
        raise RuntimeError("package version is unavailable")
    return CheckOutcome(
        "PASS", "worker imported pyfcstm and stopped at the hidden dispatch"
    )


def _runtime_metadata() -> CheckOutcome:
    """Validate cheap runtime metadata without crossing a process boundary."""
    import platform
    import sys

    from pyfcstm.config.meta import __VERSION__

    if not __VERSION__:
        raise RuntimeError("package version is unavailable")
    summary = "pyfcstm {} on Python {} ({})".format(
        __VERSION__, platform.python_version(), sys.platform
    )
    return CheckOutcome(
        "PASS",
        summary,
        expected="package and Python runtime metadata are available",
        observed=summary,
    )


_WORKERS["self_dispatch"] = _artifact_self_dispatch
_WORKERS["runtime_metadata"] = _runtime_metadata


def get_worker(worker_key: str) -> Worker:
    """
    Return a statically registered worker.

    :param worker_key: Static worker key.
    :type worker_key: str
    :return: Registered callable.
    :rtype: Worker
    :raises KeyError: If the key is not registered.

    Example::

        >>> callable(get_worker("runtime_metadata"))
        True
    """
    return _WORKERS[worker_key]


def selected_specs(profile: str) -> Tuple[CheckSpec, ...]:
    """
    Return checks implemented by the current registry for *profile*.

    :param profile: Requested profile name.
    :type profile: str
    :return: Stable check specifications.
    :rtype: Tuple[CheckSpec, ...]

    Example::

        >>> [spec.check_id for spec in selected_specs("default")]
        ['runtime.metadata', 'artifact.self_dispatch']
    """
    del profile
    return (
        CheckSpec(
            "runtime.metadata",
            "runtime_metadata",
            title="runtime metadata",
            required=True,
            execution="local",
        ),
        CheckSpec(
            "artifact.self_dispatch",
            "self_dispatch",
            title="isolated self-dispatch",
            required=True,
            prerequisites=("runtime.metadata",),
            execution="worker",
        ),
    )
