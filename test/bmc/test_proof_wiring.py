"""
Tests for the proof tier as it reaches a caller: orchestration and degradation.

Everything below runs a real query through the published solve chain.  The earlier
modules test the proof machinery from its own inputs; this one tests that the
machinery is connected -- that asking for a proof produces one where the rules cover
the case, and produces an honest formal artifact where they do not.

The module contains:
* End-to-end runs at ``proof`` depth over queries the catalog can and cannot close
* Degradation tests: an unsupported shape, an exhausted budget, a weaker request
* Ledger tests, so a caller can tell a phase that ran from one that did not

.. note::
   A proof is only published when the narrative cites its nodes, so these also cover
   the coupling between the two artifacts rather than treating them separately.
"""

import pytest

from pyfcstm.bmc import (
    BmcEngine,
    build_bmc_core_formula,
    compile_bmc_property,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text

_MODEL = """
def int x = 0;

state Root {
    state A;
    state B;

    [*] -> A;
    A -> A effect { x = x + 1; };
    A -> B;
}
"""


def _explain(query: str, mode: str = "proof", **kwargs):
    """Run one query through the published chain and return its explanation."""
    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation=mode,
        **kwargs,
    )
    return result.feasibility.explanation


@pytest.mark.unittest
def test_asking_for_a_proof_over_incompatible_equalities_gets_one() -> None:
    """The shape the contract's own example uses, end to end from a query."""
    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n'
    )

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert explanation.proof is not None
    assert explanation.proof.verification_status == "verified"
    assert explanation.proof.scope == explanation.core.scope


@pytest.mark.unittest
def test_a_published_proof_is_cited_by_the_narrative_beside_it() -> None:
    """The two artifacts are one account, so each has to reach the other.

    A proof no sentence mentions is reasoning the reader never sees; a sentence
    citing no node is a claim the graph does not carry.
    """
    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n'
    )

    cited = {
        name
        for step in explanation.narrative.reasoning_steps
        for name in step.proof_node_ids
    }
    assert cited == {node.stable_id for node in explanation.proof.nodes}
    assert explanation.narrative.derivation_status == "complete"


@pytest.mark.unittest
def test_a_shape_no_rule_covers_degrades_to_the_formal_artifact() -> None:
    """Not closing is an answer, and it keeps everything that did close.

    The formal tier already explains this core; what the proof tier owes is either a
    checked graph or an honest statement that it has none.  Publishing a partial
    graph would claim a verification that did not happen.
    """
    explanation = _explain(
        'assume at 0: var("x") > 5 && var("x") < 3;\n'
        'check reach <= 1: active("Root.A");\n'
    )

    assert explanation.achieved_mode == "formal"
    assert explanation.status == "partial"
    assert explanation.proof is None
    assert explanation.core is not None, "the formal evidence survives"
    assert explanation.reason


@pytest.mark.unittest
def test_asking_for_formal_never_produces_a_proof() -> None:
    """Depth is what the caller asked for, not the most the run could manage."""
    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n',
        mode="formal",
    )

    assert explanation.achieved_mode == "formal"
    assert explanation.status == "complete"
    assert explanation.proof is None


@pytest.mark.unittest
def test_the_ledger_names_the_proof_phase_separately() -> None:
    """A caller distinguishes the phases, so one opaque total will not do.

    The contract asks for proof construction to appear in its own right; folding it
    into a single status would hide which part of the work ran out.
    """
    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )

    names = [check.name for check in result.feasibility.refinement_checks]
    assert "proof_construction" in names


@pytest.mark.unittest
def test_an_exhausted_budget_keeps_the_formal_artifact_and_says_so() -> None:
    """Running out of time degrades the depth; it does not discard the evidence."""
    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n',
        timeout_ms=8,
    )

    assert explanation.proof is None
    assert explanation.achieved_mode in ("formal", "none")
    assert explanation.reason


@pytest.mark.unittest
def test_the_published_payload_passes_the_published_schema() -> None:
    """A consumer validates against the schema, so a real proof run has to pass it."""
    import json

    from jsonschema import Draft202012Validator

    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n'
    )
    schema = json.load(
        open("docs/source/reference/bmc_results/bmc_cli.schema.json", encoding="utf-8")
    )
    validator = Draft202012Validator(
        {"$ref": "#/$defs/infeasibilityExplanation", "$defs": schema["$defs"]}
    )

    errors = [
        error.message for error in validator.iter_errors(explanation.to_canonical())
    ]

    assert errors == []
