"""
Pytest plugin backing the repository docstring example gate.

This module is loaded with ``-p`` by the ``doctest`` Makefile target rather than
being a ``conftest.py``. The repository has no root ``conftest.py``, and adding
one would also apply to ``make unittest``; loading a plugin keeps both behaviours
below scoped to the doctest run alone.

The module contains:

* :func:`_doctest_workdir` - Runs every example in a throwaway working directory
* :func:`_doctest_demo_dsl` - Exposes :data:`DEMO_DSL` to docstring examples

.. note::
   The gate itself is a plain ``pytest --doctest-modules`` invocation. Every
   example must run and produce the output its docstring claims; there is no
   known-failure list, and ``# doctest: +SKIP`` hides a problem rather than
   solving it.
"""

import pytest

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


@pytest.fixture(autouse=True)
def _doctest_workdir(tmp_path, monkeypatch):
    """
    Run each doctest in a throwaway working directory.

    Some docstring examples write files using bare relative paths --
    ``pyfcstm.utils.json`` documents ``obj.to_json("example.json")`` -- and
    without this fixture those files land in the checkout.

    :param tmp_path: Per-test temporary directory fixture.
    :type tmp_path: pathlib.Path
    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: ``None``.
    :rtype: None
    """
    monkeypatch.chdir(tmp_path)


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
