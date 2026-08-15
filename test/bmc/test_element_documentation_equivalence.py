"""BMC equivalence tests for FCSTM owner documentation metadata."""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import (
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def test_documentation_does_not_change_bmc_result_witness_or_replay():
    """Owner documentation is metadata and cannot change BMC semantics."""
    documented = """/* root docs */
state Root {
    /* active state docs */
    state Active;
    /* initial transition docs */
    [*] -> Active;
}
"""
    plain = """state Root {
    state Active;
    [*] -> Active;
}
"""
    query = 'check reach <= 1: active("Root.Active");'

    def run(source):
        machine = load_state_machine_from_text(source)
        context = BmcEngine(machine).prepare(query)
        formula = compile_bmc_property(build_bmc_core_formula(context))
        result = solve_bmc_property(formula)
        assert result.status == "sat"
        witness = decode_bmc_witness(formula, result.model)
        replay = replay_bmc_witness(machine, witness)
        assert replay.ok
        return result.to_canonical(), witness.to_canonical(), replay.to_canonical()

    documented_result, documented_witness, documented_replay = run(documented)
    plain_result, plain_witness, plain_replay = run(plain)

    # Solver wall-clock measurements are intentionally non-semantic.
    for result in (documented_result, plain_result):
        result["elapsed_ms"] = None
        result["total_elapsed_ms"] = None
    assert documented_result == plain_result
    assert documented_witness == plain_witness
    assert documented_replay == plain_replay
