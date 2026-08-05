"""
Pytest plugin backing the repository doctest entry point.

This module is loaded with ``-p`` by :mod:`tools.run_doctests` instead of being
a ``conftest.py``. The repository has no root ``conftest.py``, and adding one
would also apply to ``make unittest``; loading a plugin keeps every behavior
below scoped to the doctest entry point alone.

The module contains:

* :func:`_doctest_workdir` - Runs every doctest in a throwaway working
  directory so file-writing examples cannot pollute the checkout.
* :func:`pytest_collection_modifyitems` - Records collected doctest node ids.
* :func:`pytest_runtest_logreport` - Records failing doctest node ids.
* :func:`pytest_sessionfinish` - Writes the machine-readable outcome file.

.. note::
   The outcome file exists so the runner never has to parse pytest terminal
   output. A stale ``--deselect`` argument is silently ignored by pytest, so
   the runner compares node-id sets instead of trusting exit codes.
"""

import json
import os
from typing import Dict, List, Set

import pytest

_COLLECTED: List[str] = []
_FAILED: Set[str] = set()

OUTCOME_FILE_OPTION = "--doctest-outcome-file"
OUTCOME_FILE_DEST = "doctest_outcome_file"


def pytest_addoption(parser):
    """
    Register the outcome-file option used by the doctest runner.

    :param parser: pytest option parser.
    :type parser: pytest.Parser
    :return: ``None``.
    :rtype: None
    """
    parser.addoption(
        OUTCOME_FILE_OPTION,
        dest=OUTCOME_FILE_DEST,
        action="store",
        default=None,
        help="Write collected and failed doctest node ids to this JSON file.",
    )


@pytest.fixture(autouse=True)
def _doctest_workdir(tmp_path, monkeypatch):
    """
    Run each doctest in a throwaway working directory.

    Some docstring examples write files using bare relative paths. Without this
    fixture those files land in the checkout and, under parallel execution,
    several workers race for the same name.

    :param tmp_path: Per-test temporary directory fixture.
    :type tmp_path: pathlib.Path
    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: ``None``.
    :rtype: None
    """
    monkeypatch.chdir(tmp_path)


def pytest_collection_modifyitems(config, items):
    """
    Record every collected doctest node id.

    :param config: Active pytest config.
    :type config: pytest.Config
    :param items: Collected pytest items.
    :type items: List[pytest.Item]
    :return: ``None``.
    :rtype: None
    """
    from _pytest.doctest import DoctestItem

    for item in items:
        if isinstance(item, DoctestItem):
            _COLLECTED.append(item.nodeid)


def pytest_runtest_logreport(report):
    """
    Record doctest node ids that failed in any phase.

    :param report: Per-phase test report.
    :type report: pytest.TestReport
    :return: ``None``.
    :rtype: None
    """
    if report.failed:
        _FAILED.add(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    """
    Write collected and failed doctest node ids as JSON.

    :param session: Finished pytest session.
    :type session: pytest.Session
    :param exitstatus: Pytest exit status.
    :type exitstatus: int
    :return: ``None``.
    :rtype: None
    """
    path = session.config.getoption(OUTCOME_FILE_DEST)
    if not path:
        return
    payload: Dict[str, List[str]] = {
        "collected": sorted(set(_COLLECTED)),
        "failed": sorted(_FAILED),
    }
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


#: DSL text shared by the simulation-runtime docstrings. Twenty-two private
#: methods on :class:`pyfcstm.simulate.SimulationRuntime` need a built machine
#: before they can demonstrate anything, and repeating the source in each
#: docstring would add several hundred lines of setup to the rendered API
#: documentation. The root state is named ``System`` so the abstract action paths
#: the examples reference -- ``System.Active.Init`` and ``System.Active.Monitor``
#: -- are the real ones.
DEMO_DSL = """def int counter = 0;

state System {
    [*] -> Active;
    state Active {
        enter abstract Init;
        during abstract Monitor;
    }
    state Idle;
    Active -> Idle :: Start;
}
"""


@pytest.fixture(scope="session", autouse=True)
def _doctest_demo_dsl(doctest_namespace):
    """
    Expose :data:`DEMO_DSL` to docstring examples.

    :param doctest_namespace: Pytest doctest namespace injection fixture.
    :type doctest_namespace: Dict[str, object]
    :return: ``None``.
    :rtype: None
    """
    doctest_namespace["DEMO_DSL"] = DEMO_DSL
