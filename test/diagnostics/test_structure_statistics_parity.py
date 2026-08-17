"""Full authored-structure statistics contract fixtures for pyfcstm.

The matching jsfcstm fixture lives under ``editors/jsfcstm/test``.  The two
files are kept byte-identical by ``make inspect_structure_parity_check`` while
each test remains inside its own language boundary.
"""

import json
from pathlib import Path

import pytest

from pyfcstm.diagnostics import StructureStatisticsPolicy, inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine


_FIXTURE_PATH = Path(__file__).with_name("fixtures") / "structure_statistics_parity.json"
_CASES = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
pytestmark = pytest.mark.unittest


def _build_machine(source: str):
    ast = parse_with_grammar_entry(source, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.parametrize("case", _CASES, ids=[item["name"] for item in _CASES])
def test_structure_statistics_matches_canonical_fixture(case):
    machine = _build_machine(case["dsl"])
    policy_data = case["policy"]
    policy = (
        StructureStatisticsPolicy(**policy_data)
        if policy_data is not None
        else None
    )
    report = inspect_model(machine, structure_statistics_policy=policy)
    assert report.to_json()["structure_statistics"] == case["expected"]
