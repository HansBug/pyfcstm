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


@pytest.mark.unittest
def test_an_input_fact_is_proved_equivalent_to_the_member_it_restates() -> None:
    """``core_binding`` names a check, so the check has to happen.

    Before this the label was written onto every input unconditionally, which is
    the trust marker the contract forbids: the node claimed an equivalence nobody
    established.  Both directions are refuted separately -- a fact implied by its
    group but not implying it would let the proof rest on less than the model
    requires, and the reverse on more.
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

    binding = [
        check
        for check in result.feasibility.refinement_checks
        if check.name == "core_binding"
    ]
    assert len(binding) == 1, [c.name for c in result.feasibility.refinement_checks]
    assert binding[0].status == "complete"
    assert binding[0].reason is None, "a completed binding has nothing to explain"


@pytest.mark.unittest
def test_a_definedness_conflict_reaches_the_proof_tier() -> None:
    """The published vocabulary and the rule vocabulary have to meet, per shape.

    A core states ``definedness_condition``; the rule reads ``definedness_guard``.
    Both names are right for their side, and the missing piece was the translation
    between them -- without it the rule was unreachable from any real query while
    its own tests passed on hand-written premises.
    """
    explanation = _explain(
        'init state("Root.A") where x == 0;\n'
        'assume at 0: var("x") / var("x") > 0;\n'
        'check reach <= 1: active("Root.A");\n'
    )

    assert explanation.achieved_mode == "proof"
    assert explanation.proof.nodes[-1].rule_id == "definedness_failure"


@pytest.mark.unittest
def test_a_member_no_fact_was_read_from_blocks_publication() -> None:
    """Coverage is judged against the core, not against what could be translated.

    A member whose fact has no reading is absent from the builder's inputs
    entirely.  Judging coverage on those inputs would let a proof close over a core
    it never saw all of, and publish ``subset_minimal`` while a member took no part.
    """
    from pyfcstm.bmc.explanation import BmcConstraintRef, BmcCoreItem
    from pyfcstm.bmc.proof import build_domain_proof, proof_facts_for_core
    from pyfcstm.bmc.provenance import BmcSourceRef
    from pyfcstm.bmc.solver import _SolveBudget

    def member(stable_id, category, fact, role, text):
        reference = BmcConstraintRef(
            stable_id,
            "assumptions",
            category,
            BmcSourceRef("generated", None, None),
            text,
        )
        return BmcCoreItem(reference, role, None, False, fact, text, False)

    items = (
        member(
            "assumption.0000",
            "assumption.frame",
            {
                "kind": "variable_comparison",
                "variable": "x",
                "frame": 0,
                "operator": "eq",
                "value": 1,
            },
            "assumption",
            "x == 1",
        ),
        member(
            "assumption.0001",
            "assumption.frame",
            {
                "kind": "variable_comparison",
                "variable": "x",
                "frame": 0,
                "operator": "eq",
                "value": 2,
            },
            "assumption",
            "x == 2",
        ),
        # ``ne`` restricts nothing any rule can intersect, so no fact is read from
        # it and it is invisible to the builder's own inputs.
        member(
            "assumption.0002",
            "assumption.frame",
            {
                "kind": "variable_comparison",
                "variable": "y",
                "frame": 0,
                "operator": "ne",
                "value": 3,
            },
            "assumption",
            "y != 3",
        ),
    )

    proof, record = build_domain_proof(
        "assumptions_component",
        proof_facts_for_core(items),
        _SolveBudget(None),
        member_ids=[item.constraint.stable_id for item in items],
    )

    assert proof is None
    assert "every core member" in (record.reason or "")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "states", [8, 33, 129], ids=["small", "past-the-old-limit", "large"]
)
def test_a_wide_state_domain_still_reaches_a_proof(states) -> None:
    """The application limit is a backstop, and it has to stay one.

    Candidates were offered to the checker without matching the tags a rule reads,
    so four rules concluding ``false`` each spent n(n-1) checks on premises they
    could never take.  A frame with 32 legal states exhausted the limit before the
    one rule that could close it was proposed even once -- a completely ordinary
    model size, failing in a place no reader could predict.
    """
    from pyfcstm.bmc.proof import build_domain_proof
    from pyfcstm.bmc.solver import _SolveBudget

    inputs = (
        (
            "domain.0000",
            {"kind": "state_domain", "frame": 0, "states": list(range(states))},
        ),
    ) + tuple(
        (
            "assumption.%04d" % index,
            {"kind": "state_exclusion", "frame": 0, "state": index},
        )
        for index in range(states)
    )

    proof, record = build_domain_proof(
        "assumptions_component", inputs, _SolveBudget(None)
    )

    assert proof is not None, record.reason
    assert proof.nodes[-1].rule_id == "state_domain_exhaustion"
