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
from pyfcstm.model import load_state_machine_from_file, load_state_machine_from_text

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
def test_an_exhausted_budget_never_publishes_a_proof() -> None:
    """Running out of time degrades the depth rather than guessing at one.

    Which depth it degrades *to* is the host clock's business: a fast machine gets
    through classification and publishes a formal artifact, a slow one may not get
    that far and publishes nothing at all.  Both are honest, and pinning either
    would be pinning the runner.  What must hold on every machine is that a run
    which ran out of budget carries no proof and says why.
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
        timeout_ms=8,
    )

    explanation = result.feasibility.explanation
    if explanation is None:
        # The budget went before the optional work started.  Nothing was published,
        # which is the strongest form of "no proof".
        return
    assert explanation.proof is None
    assert explanation.achieved_mode in ("formal", "none")
    assert explanation.reason


@pytest.mark.unittest
def test_the_published_payload_passes_the_published_schema() -> None:
    """A consumer validates against the schema, so a real proof run has to pass it."""
    import json

    # ``jsonschema`` is a development convenience rather than a declared test
    # dependency -- it needs Python 3.8 while this package supports 3.7 -- so the
    # repository's convention is to skip the schema checks where it is absent.
    jsonschema = pytest.importorskip("jsonschema")

    explanation = _explain(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n'
    )
    schema = json.load(
        open("docs/source/reference/bmc_results/bmc_cli.schema.json", encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(
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
def test_an_assignment_a_transition_makes_binds_to_the_requirement_it_states() -> None:
    """A step relation's assignment is now bindable, one requirement at a time.

    Two of the catalog's rules speak about a transition, and both were unreachable
    while the step relation published no content: a premise no query can produce is
    a rule that passes its own tests and never runs.  The member now publishes the
    assignment it makes, and the binding proves that reading equivalent to exactly
    one requirement of the group -- which is what ``core_binding`` reaching
    ``complete`` here reports.  Before, the member was ``structural_constraint``,
    no encoder existed for it, and this phase ended ``unknown``.

    The discharge has since landed, and this is the test that recorded the boundary
    before it did: a published case was conditional, the rule that evaluates an
    expression refused one carrying a condition, and the chain waited.  The note here
    said that when the discharge arrived ``proof_construction`` would become
    ``complete`` and the last two assertions would be what changed.  They are the two
    below, and they now assert the reached depth rather than the refusal -- kept
    rather than deleted, because the earlier assertions about the binding are the
    same either way and a test that only ever passed under the old behaviour would
    have taken them with it.

    ``case_condition_entailment`` discharges the condition against the members that
    establish it, verified by the solver rather than by the rule checker, and the
    chain closes through ``transition_assignment`` into the arithmetic rules.
    """
    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0;\n'
        'assume at 1: var("x") == 5;\n'
        'check reach <= 1: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )

    ledger = {check.name: check for check in result.feasibility.refinement_checks}
    assert ledger["core_binding"].status == "complete"
    assert ledger["core_binding"].reason is None
    explanation = result.feasibility.explanation
    assert any(
        item.normalized_fact.get("kind") == "transition_case"
        for item in explanation.core.items
    ), [item.normalized_fact.get("kind") for item in explanation.core.items]
    assert explanation.achieved_mode == "proof"
    assert "case_condition_entailment" in {
        node.rule_id for node in explanation.proof.nodes
    }


@pytest.mark.unittest
def test_an_event_opposition_reaches_the_proof_tier() -> None:
    """The rule that closes over a proposition and its complement, end to end.

    This was verified on the command line before it was verified by a test, which is
    the same gap in the other direction from the usual one: a suite can be green while
    production is wrong, and production can be right along a path no test walks.  The
    binding branch a proposition takes -- its subject is the group's own boolean, not a
    frame symbol -- ran only under the CLI until this existed, so a regression in it
    would have gone unreported.

    Form one rather than form two: an event assumption encodes to a single boolean, so
    the fact and its group are equivalent in both directions and none of the
    conjunctive-unit machinery is involved.
    """
    machine = load_state_machine_from_text(
        "def int a = 0;\nstate Root { state A; state B; [*]->A; A->B :: Go; B->[*]; }",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'assume event("Root.A.Go", 0) == true;\n'
        'assume event("Root.A.Go", 0) == false;\n'
        'check reach <= 2: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.proof.nodes[-1].rule_id == "boolean_complement"
    assert [node.verification_method for node in explanation.proof.nodes] == [
        "core_binding",
        "core_binding",
        "rule_checker",
    ], [node.verification_method for node in explanation.proof.nodes]
    identities = {
        node.conclusion.get("identity")
        for node in explanation.proof.nodes
        if node.kind == "input"
    }
    assert identities == {"Root.A.Go@0"}, identities


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


@pytest.mark.unittest
@pytest.mark.parametrize(
    "operation, translated",
    [("division", True), ("sqrt", False)],
    ids=["a-divisor-excludes-one-value", "a-square-root-excludes-a-half-line"],
)
def test_only_the_definedness_shape_the_rule_reads_is_translated(
    operation, translated
) -> None:
    """A rule's premise shape decides what may be handed to it.

    ``definedness_failure`` reads a guard as one forbidden value, which is what a
    divisor's domain is.  A square root's is ``operand >= 0`` -- a half-line, not a
    point -- and writing it as "forbidden: 0" produces a fact that is neither
    implied by its group nor implies it.  The binding check refuses that in both
    directions, so nothing unsound could be published either way; not translating
    it reaches the same refusal before a solver is asked and records the reason.
    """
    from pyfcstm.bmc.explanation import BmcConstraintRef, BmcCoreItem
    from pyfcstm.bmc.proof import proof_facts_for_core
    from pyfcstm.bmc.provenance import BmcSourceRef

    reference = BmcConstraintRef(
        "definedness.0000",
        "assumptions",
        "definedness",
        BmcSourceRef("generated", None, None),
        "guard",
    )
    item = BmcCoreItem(
        reference,
        "definedness",
        None,
        False,
        {
            "kind": "definedness_condition",
            "frame": 0,
            "operation": operation,
            "variable": "x",
        },
        "guard",
        False,
    )

    facts = proof_facts_for_core((item,))

    assert bool(facts) is translated


@pytest.mark.unittest
def test_a_fact_weaker_than_its_group_is_refused_in_both_directions() -> None:
    """The binding check is what makes a translation safe to add, so it is pinned.

    ``x >= 0`` and ``x != 0`` imply each other in neither direction, which is what
    a wrong translation of a square root's domain would look like.  Asserting the
    refusal here means a translation added later cannot quietly rely on the check
    being lenient.
    """
    import z3

    symbol = z3.Int("F_0_x_abcdef")
    group, weaker = symbol >= 0, symbol != 0

    for claim in (z3.And(group, z3.Not(weaker)), z3.And(weaker, z3.Not(group))):
        solver = z3.Solver()
        solver.add(claim)
        assert str(solver.check()) == "sat", "neither direction may hold"


@pytest.mark.unittest
def test_an_exhausted_state_domain_reaches_the_proof_tier_from_a_query() -> None:
    """The rule was reachable from the builder and not from a query.

    Its facts are about a frame's state slot, and the binding check had encoders
    only for the value-carrying tags -- so a real query produced a complete formal
    artifact and then degraded at the gate, one step before the search that would
    have closed it.  A 129-state builder case says nothing about that: it hands the
    builder its inputs directly and never passes the gate at all.
    """
    machine = load_state_machine_from_text(
        "state Root { state A; state B; [*] -> A; }", "machine.fcstm"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A");\n'
        'assume at 1: !active("Root.A");\n'
        'assume at 1: !active("Root.B");\n'
        "assume at 1: !terminated();\n"
        'check reach <= 1: active("Root.A");\n',
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation

    assert explanation.achieved_mode == "proof", explanation.reason
    assert explanation.proof.nodes[-1].rule_id == "state_domain_exhaustion"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "name",
    ["x", "v" * 100],
    ids=["a-short-name", "a-name-past-the-encoder-truncation"],
)
def test_a_long_variable_name_still_reaches_the_proof_tier(name) -> None:
    """A symbol's body is truncated, so its name cannot be read back from it.

    The binding resolved names off the symbol alone while the published facts were
    resolved against the declarations, and past the truncation width the two stopped
    agreeing -- an ordinary long identifier lost proof depth for a reason nothing in
    the query could suggest.
    """
    machine = load_state_machine_from_text(
        "def int %s = 0; state Root;" % name, "machine.fcstm"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root") havoc *;\n'
        'assume at 0: var("%s") == 1;\n'
        'assume at 0: var("%s") == 2;\n'
        'check reach <= 1: active("Root");\n' % (name, name),
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation

    assert explanation.achieved_mode == "proof", explanation.reason
    assert explanation.proof.verification_status == "verified"


@pytest.mark.unittest
def test_a_binding_that_runs_out_of_time_is_reported_as_a_timeout() -> None:
    """A timeout and an undecidable shape call for opposite responses.

    One says raise the budget and try again; the other says the shape is not one the
    solver can decide, so retrying wastes it.  The two were swapped -- a run that
    ran out of time advised against retrying.  Both words are legal in the published
    ledger, so nothing structural caught it.

    An exhausted budget is produced the way a real one is exhausted, by a deadline
    that has passed, rather than by standing in for the check.
    """
    import time

    from pyfcstm.bmc.infeasibility import check_core_bindings
    from pyfcstm.bmc.solver import _SolveBudget

    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    facts = (
        (
            "assumption.0000.frame.0000",
            {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 1},
        ),
    )

    spent = _SolveBudget(1)
    spent.deadline = time.monotonic() - 1.0

    held, record, _ = check_core_bindings(core, facts, spent)

    assert held is False
    assert record.status == "timeout", record.reason


@pytest.mark.unittest
def test_nothing_to_bind_is_reported_as_unestablished_rather_than_complete() -> None:
    """Nothing bound means nothing may rest on a binding, and that is not an error.

    Reporting a completed phase for zero checks was wrong twice: a consumer reading
    ``complete`` would believe equivalences were established, and the published
    ledger refuses a completed check that carries a reason -- so the query that
    reached this raised out of the solve chain instead of degrading.

    The query that reached it no longer does: two positive state requirements
    translate now, which is the point of the change beside this one.  What the branch
    protects is unchanged, so it is asserted where the branch lives, over a real core
    whose facts were all filtered out.
    """
    from pyfcstm.bmc.infeasibility import check_core_bindings
    from pyfcstm.bmc.solver import _SolveBudget

    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 1: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)

    held, record, _ = check_core_bindings(core, (), _SolveBudget(None))

    assert held is False, "an empty binding establishes nothing"
    assert record.status == "unknown"
    assert record.reason, "the published ledger requires a reason for this status"


@pytest.mark.unittest
def test_the_whole_published_envelope_validates_at_proof_depth() -> None:
    """The schema applies to the payload a consumer receives, not to a fragment.

    An earlier test validated the explanation object alone and passed while the
    envelope around it did not: the ledger names this tier adds were registered in
    the runtime vocabulary and not in the published enum, so every real
    ``--json --explain-infeasibility proof`` run was rejected by the schema shipped
    beside it.
    """
    import json

    # ``jsonschema`` is a development convenience rather than a declared test
    # dependency -- it needs Python 3.8 while this package supports 3.7 -- so the
    # repository's convention is to skip the schema checks where it is absent.
    jsonschema = pytest.importorskip("jsonschema")

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
    assert result.feasibility.explanation.proof is not None, "the run must reach proof"

    schema = json.load(
        open("docs/source/reference/bmc_results/bmc_cli.schema.json", encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/currentResult", "$defs": schema["$defs"]}
    )

    errors = [error.message for error in validator.iter_errors(result.to_canonical())]

    assert errors == []


@pytest.mark.unittest
def test_two_states_required_at_one_frame_reach_the_proof_tier() -> None:
    """A frame holds one state, so two requirements on it cannot both hold.

    This is the mutual-exclusion question a reviewer of a controller actually asks --
    can it be purging and heating at once -- and the answer was reaching ``formal``
    only.  A positive state requirement normalizes losslessly (``3 == F_1_state``),
    so there was nothing standing between it and a checked proof except a missing
    translation.
    """
    machine = load_state_machine_from_text(
        "state Root { state A; state B; state C; [*] -> A; A -> B; A -> C; }",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A");\n'
        'assume at 1: active("Root.B");\n'
        'assume at 1: active("Root.C");\n'
        'check reach <= 1: active("Root.A");\n',
        query_source_path="query.fbmcq",
    )

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation

    assert explanation.achieved_mode == "proof", explanation.reason
    assert explanation.proof.nodes[-1].rule_id == "incompatible_equalities"
    assert explanation.proof.verification_status == "verified"


@pytest.mark.unittest
def test_a_core_holding_a_structural_member_cannot_reach_the_proof_tier() -> None:
    """Some cores are unreachable at proof depth by contract, not by omission.

    A ``structural_constraint`` fact carries an identity and a category and no
    content -- that is what the tag is for.  An input node's conclusion must *be* its
    member's fact, and ``core_binding`` must prove that fact equivalent to the source
    group in both directions.  A contentless fact cannot be equivalent to a macro-step
    relation, so a core holding one degrades however many recognizers are added.

    The effect below assigns *two* variables, which is what makes its step keep the
    structural tag: the reading a step publishes is one assignment, and a step that
    makes two has no single one to name.  Declining is the honest answer there --
    publishing either assignment as though it were the step's reading would hide the
    other.  A step that makes exactly one assignment does get a content reading, so
    that shape is pinned in ``test_provenance`` instead of here.

    The transition chain below is the shape this matters for, and it is worth pinning
    rather than leaving as an apparent gap: the ``formal`` tier answers the question
    the query asks -- the prefix forces the counter to one -- and the proof tier says
    honestly that it cannot certify each step of it.
    """
    machine = load_state_machine_from_text(
        "def int retries = 0;\n"
        "def int spare = 0;\n"
        "state Root { state Igniting; state Purge; [*] -> Igniting;\n"
        "    Igniting -> Purge effect { retries = retries + 1; spare = spare + 2; }; }",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.Igniting") where retries == 0;\n'
        'assume at 1: var("retries") == 0;\n'
        'check reach <= 1: active("Root.Purge");\n',
        query_source_path="query.fbmcq",
    )

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation

    assert explanation.achieved_mode == "formal"
    assert explanation.proof is None
    assert explanation.reason
    # The formal answer is the one the engineer asked for, so it must survive.
    assert explanation.narrative.derivation_status == "complete"
    assert any(
        "retries to equal 1" in step.text
        for step in explanation.narrative.reasoning_steps
    ), [step.text for step in explanation.narrative.reasoning_steps]
    assert any(
        item.normalized_fact.get("kind") == "structural_constraint"
        for item in explanation.core.items
    ), "the shape this pins needs a structural member"


@pytest.mark.unittest
def test_the_published_proof_names_states_the_way_the_query_did() -> None:
    """The author wrote a path; the reading they get back has to use it.

    Nothing in the model says ``1``, so a proof that concludes about state 1 is
    asking the reader to learn the encoding in order to read their own result.  The
    names are on the domain the core already carries, so this is about handing them
    to the reading rather than about discovering them.
    """
    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        'assume at 1: active("Root.A");\n'
        'assume at 1: active("Root.B");\n'
        'check reach <= 1: active("Root.B");\n',
        query_source_path="query.fbmcq",
    )

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )

    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof", explanation.reason
    text = " ".join(step.text for step in explanation.narrative.reasoning_steps)
    assert "Root.A" in text and "Root.B" in text, text
    assert "must equal 1" not in text and "must equal 2" not in text, text


@pytest.mark.unittest
def test_a_variable_whose_name_starts_like_the_state_slot_stays_its_own_slot() -> None:
    """The frame's state slot is one symbol, not a family of them.

    Variable symbols are spelled ``F_<frame>_<name>_<digest>`` and the state slot is
    spelled ``F_<frame>_state``, so a model variable named ``state_x`` produces a
    symbol the state slot's name is a prefix of, and this pins that such a model
    still proves.  Which fact is about the slot is settled by its ``state_slot``
    flag rather than by any spelling, so a lookalike name is not what separates
    them -- but a prefix-matching resolver would still bind the wrong symbol, which
    is what this case would catch.

    What keeps the two apart is not only the identity comparison in the resolver: the
    candidate symbols are sorted first, and the exact name is the shortest of its
    prefix family, so it is found before any sibling regardless of how the comparison
    is spelled.  Replacing the comparison with a prefix test leaves this green, which
    is why the docstring does not claim to pin the comparison.
    """
    machine = load_state_machine_from_text(
        "def int state_x = 0;\n"
        "state Root {\n"
        "    state A;\n"
        "    state B;\n"
        "    [*] -> A;\n"
        "    A -> B;\n"
        "}\n",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'assume at 1: active("Root.A");\n'
        'assume at 1: active("Root.B");\n'
        'check reach <= 1: var("state_x") == 0;\n',
        query_source_path="query.fbmcq",
    )

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )

    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof", explanation.reason
    text = " ".join(step.text for step in explanation.narrative.reasoning_steps)
    assert "Root.A" in text and "Root.B" in text, text
    assert "state_x" not in text, text


@pytest.mark.unittest
def test_a_model_variable_named_like_the_state_slot_keeps_its_own_reading(
    tmp_path,
) -> None:
    """A variable a model calls ``state`` is a variable, not the frame's state slot.

    The slot needed a subject so the rules could compare it, and the first spelling
    chosen was ``state`` on the reasoning that the grammar reserves the word.  It
    does not reserve it everywhere: ``STATE`` is a keyword in the lexer's default
    mode only, and an import mapping renames through a mode whose identifier rule
    admits any name.  So a model can declare ``state``, and its requirement was then
    routed to the slot's symbol, failed to bind, and lost a proof this query used to
    get.

    The subject's spelling is not what makes the two readings separable -- a model
    can declare that name too, through the target-template rule.  The ``state_slot``
    flag is, and this case holds the variable's reading to itself.
    """
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        "def int w = 0;\n"
        "state WorkerRoot {\n"
        "    state Idle;\n"
        "    state Done;\n"
        "    [*] -> Idle;\n"
        "    Idle -> Done;\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        "state Root {\n"
        "    state Host {\n"
        '        import "./worker.fcstm" as Worker { def w -> state; };\n'
        "        [*] -> Worker;\n"
        "    }\n"
        "    [*] -> Host;\n"
        "}\n",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    context = BmcEngine(model).prepare(
        'assume at 0: var("state") == 1;\n'
        'assume at 0: var("state") == 2;\n'
        'check reach <= 1: active("Root.Host.Worker.Done");\n',
        query_source_path="query.fbmcq",
    )

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )

    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof", explanation.reason
    text = " ".join(step.text for step in explanation.narrative.reasoning_steps)
    assert "state must equal 1" in text, text
    assert "the state must be" not in text, text


@pytest.mark.unittest
def test_a_variable_spelled_like_the_slot_and_a_state_read_as_themselves(
    tmp_path,
) -> None:
    """One model, both subjects, each read as what it is.

    A model can declare a variable named exactly what the slot calls itself.  Two
    arguments for why it could not were both wrong -- ``state`` is a keyword only in
    the lexer's default mode, so an import mapping renames past it, and ``$state``
    is reachable too because the target template rule admits ``$`` and
    ``def x_* -> *$state;`` with an empty capture renders it exactly.

    Rather than defend the name, identity moved off it: the fact carries a flag, and
    the slot comparison, the binding and the reading all consult that instead.  So
    this model needs no special handling -- its variable's requirements read as a
    variable, its state requirements read as states, and both reach the proof tier.
    """
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        "def int x_ = 0;\n"
        "state WorkerRoot {\n"
        "    state Idle;\n"
        "    state Done;\n"
        "    [*] -> Idle;\n"
        "    Idle -> Done;\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        "state Root {\n"
        "    state Host {\n"
        '        import "./worker.fcstm" as Worker { def x_* -> *$state; };\n'
        "        [*] -> Worker;\n"
        "    }\n"
        "    [*] -> Host;\n"
        "}\n",
        encoding="utf-8",
    )
    model = load_state_machine_from_file(main)

    def read(query: str) -> str:
        context = BmcEngine(model).prepare(query, query_source_path="query.fbmcq")
        result = solve_bmc_property(
            compile_bmc_property(build_bmc_core_formula(context)),
            infeasibility_explanation="proof",
        )
        explanation = result.feasibility.explanation
        assert explanation.achieved_mode == "proof", explanation.reason
        return " ".join(step.text for step in explanation.narrative.reasoning_steps)

    as_variable = read(
        'assume at 0: var("$state") == 1;\n'
        'assume at 0: var("$state") == 2;\n'
        'check reach <= 1: active("Root.Host.Worker.Done");\n'
    )
    assert "$state must equal 1" in as_variable, as_variable
    assert "the state must be" not in as_variable, as_variable

    as_state = read(
        'assume at 1: active("Root.Host.Worker.Idle");\n'
        'assume at 1: active("Root.Host.Worker.Done");\n'
        'check reach <= 1: active("Root.Host.Worker.Done");\n'
    )
    assert "the state must be Root.Host.Worker.Idle" in as_state, as_state
    assert "must equal" not in as_state, as_state


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query",
    [
        'assume at 0: var("x") == 1;\nassume at 0: var("x") == 2;\ncheck reach <= 1: active("Root.B");\n',
        'assume at 0: var("x") >= 5;\nassume at 0: var("x") <= 3;\ncheck reach <= 1: active("Root.B");\n',
        'assume at 1: active("Root.A");\nassume at 1: active("Root.B");\ncheck reach <= 1: active("Root.B");\n',
    ],
    ids=["two-values", "empty-interval", "two-states"],
)
def test_an_input_node_restates_one_member_and_says_so(query) -> None:
    """An input node stands for exactly one core member, and says it was checked both ways.

    The contract puts two separate requirements on input nodes: each binds to one
    minimal core item, and each is established by re-encoding the fact and refuting
    ``group => fact`` *and* ``fact => group``.  ``core_binding`` is the word for that
    pair of checks; ``solver_entailment`` belongs to derived and root steps, where a
    conclusion follows from premises rather than restating a source.

    Both were crossed once by a reading that summarised several members at once and
    was established in the consequence direction only.  It was sound and it published
    a shorter narrative than the tier it replaced -- the initial state lost its own
    sentence, and the closing line stopped naming the values it was about.  So the
    strictness is not ceremony: one member per node is what keeps every member's own
    reading in the report.
    """
    machine = load_state_machine_from_text(_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")

    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof", explanation.reason

    inputs = [node for node in explanation.proof.nodes if node.kind == "input"]
    assert inputs
    for node in inputs:
        assert node.verification_method == "core_binding", node.stable_id
        assert len(node.item_ids) == 1, (node.stable_id, node.item_ids)
    for node in explanation.proof.nodes:
        if node.kind != "input":
            assert node.verification_method in ("rule_checker", "solver_entailment")


#: A machine whose step relation reads as one case, so a proof can use it.
#:
#: Two transitions leave ``A`` and only the first assigns, which is what lets the
#: step group publish a readable case rather than degrading to a structural
#: constraint.  The second is unreachable in the encoding -- an unguarded transition
#: declared first takes priority -- and that is exactly why the case's condition is
#: the state alone: nothing else has to hold for the assignment to.
_CASE_MODEL = """
def int x = 0;

state Root {
    state A;
    state B;

    [*] -> A;
    A -> A effect { x = x + 1; };
    A -> B;
}
"""


def _explain_case_model(query: str, mode: str = "proof", **kwargs):
    """Run one query against the readable-case machine and return the explanation."""
    machine = load_state_machine_from_text(_CASE_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation=mode,
        **kwargs,
    )
    return result.feasibility


@pytest.mark.unittest
def test_a_discharged_case_carries_the_arithmetic_chain_to_a_contradiction() -> None:
    """The whole chain, end to end, over a query a user can write.

    Three rules waited on this one.  A case states what it assigns *where the case
    applies*, and until the condition could be discharged the assignment was
    unusable: the evaluation rule refuses an expression carrying a condition, so the
    chain had no second step and ``transition_assignment``,
    ``arithmetic_evaluation`` and ``equality_substitution`` were unreachable by any
    query at all.  Two of the three fire in the chain below; the third needs an
    operand that is still a name, which this machine's literal ``+ 1`` cannot
    produce, so it has a fixture of its own further down.  The discharge is a solver
    step rather than a rule check because
    the members that establish the condition include one no reader can see -- the
    step relation that puts the machine in the state, which publishes as a
    structural constraint.
    """
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    explanation = feasibility.explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert explanation.proof.verification_status == "verified"
    assert [node.rule_id for node in explanation.proof.nodes] == [
        "source_fact",
        "source_fact",
        "source_fact",
        "case_condition_entailment",
        "transition_assignment",
        "arithmetic_evaluation",
        "incompatible_equalities",
    ]
    discharge = next(
        node
        for node in explanation.proof.nodes
        if node.rule_id == "case_condition_entailment"
    )
    assert discharge.kind == "derived"
    assert discharge.verification_method == "solver_entailment"
    assert "condition" not in discharge.conclusion


@pytest.mark.unittest
def test_a_discharge_cites_only_members_of_the_published_core() -> None:
    """The entailment names where the condition came from, and stays inside the core.

    A node citing something outside the core would break the subset-minimality the
    proof claims for its own leaves: the reader is told these members and no others
    carry the contradiction.  The citation is also the only place the condition's
    origin is visible, so it has to be the members that actually establish it rather
    than every member that happened to be present.
    """
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    explanation = feasibility.explanation
    members = {item.constraint.stable_id for item in explanation.core.items}
    discharge = next(
        node
        for node in explanation.proof.nodes
        if node.rule_id == "case_condition_entailment"
    )

    assert set(discharge.item_ids) <= members
    assert "transition.step.0000" in discharge.item_ids
    assert "initial.target" in discharge.item_ids


@pytest.mark.unittest
def test_the_ledger_reports_the_discharge_phase_that_ran() -> None:
    """A phase a caller pays for is a phase they can see in the ledger."""
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    names = [check.name for check in feasibility.refinement_checks]

    assert "case_condition" in names
    assert names.index("case_condition") < names.index("proof_construction")


@pytest.mark.unittest
def test_a_case_input_publishes_the_requirement_it_was_bound_against() -> None:
    """An input bound against one requirement says so, and says which one.

    A step relation holds one requirement per case, and a case fact restates exactly
    one of them -- it cannot imply the whole group, so the binding check proves it
    equivalent to a single unit and records which.  Publishing ``core_binding`` for
    such an input claims the group's whole equivalence, which is not what was
    checked; the reader is told "the transition relation" and left to find the part
    that mattered.  The binding check's own comment promised the attribution would
    travel with the node, and the orchestration dropped it on the floor.
    """
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    inputs = [
        node for node in feasibility.explanation.proof.nodes if node.kind == "input"
    ]
    cases = [node for node in inputs if node.conclusion["kind"] == "transition_case"]
    assumptions = [
        node for node in inputs if node.conclusion["kind"] == "variable_equality"
    ]

    assert cases, "the fixture is meant to publish a case input"
    for node in cases:
        assert node.verification_method == "core_binding_unit"
        assert node.unit_count is not None and node.unit_count >= 1
        assert 0 <= node.unit_index < node.unit_count
    # A whole-group binding is still published as one: the distinction is the point.
    for node in assumptions:
        assert node.verification_method == "core_binding"
        assert node.unit_index is None
        assert node.unit_count is None


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("mode", "expected_mode"),
    [("formal", "formal"), ("proof", "proof")],
)
def test_a_tier_is_attempted_only_when_it_was_asked_for(mode, expected_mode) -> None:
    """Depth is what the caller requested, never more.

    A caller who asks for a formal explanation is asking for a cheaper artifact, and
    the published contract refuses one deeper than the request.  So the proof tier
    has to be gated on the request, not only on whether the formal artifact is solid
    enough to carry a proof: this core is solid but its narrative falls short, so the
    complete-formal return does not fire, and an ungated deeper tier picked the query
    up on its way past and delivered proof depth to a formal request -- rejected by
    the delivery check as an exception rather than an explanation.
    """
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n',
        mode=mode,
    )
    explanation = feasibility.explanation

    assert explanation.requested_mode == mode
    assert explanation.achieved_mode == expected_mode


#: A machine that adds a variable rather than a literal, so the operand is a name.
#:
#: The distinction is the whole subject of ``equality_substitution``: an expression
#: whose operand still stands as a symbol has no value to evaluate, and that rule is
#: what supplies one.  Reaching it needs an assignment whose right-hand side names a
#: second variable, which the literal-operand machine above cannot produce.
_OPERAND_VARIABLE_MODEL = """
def int x = 0;
def int y = 2;

state Root {
    state A;
    state B;

    [*] -> A;
    A -> A effect { x = x + y; };
    A -> B;
}
"""


def _explain_operand_variable_model(query: str, **kwargs):
    """Run one query against the variable-operand machine and return the outcome."""
    machine = load_state_machine_from_text(_OPERAND_VARIABLE_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
        **kwargs,
    )
    return result.feasibility


@pytest.mark.unittest
def test_an_operand_still_named_does_not_raise_out_of_the_search() -> None:
    """A proposal and its checker have to read an operand the same way.

    The checker refused an expression whose operand still stands as a symbol, and
    said in its own comment what would happen otherwise: ``_evaluate`` would add
    ``None`` to a number.  The proposal did not make the same refusal, so the search
    built that call itself and raised out of a public solve -- not a degraded
    explanation, an exception.  The two sides now ask one shared question.

    What the crash was hiding is the substitution step itself: it is the only rule
    that can turn a named operand into a value, so it stood behind the raise and no
    query reached it.  The chain below is where it fires.
    """
    feasibility = _explain_operand_variable_model(
        'assume at 1: var("x") == 0;\n'
        'assume at 1: var("y") == 2;\n'
        'assume at 2: var("x") == 1;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    explanation = feasibility.explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert explanation.proof.verification_status == "verified"
    assert [node.rule_id for node in explanation.proof.nodes] == [
        "source_fact",
        "source_fact",
        "source_fact",
        "source_fact",
        "case_condition_entailment",
        "transition_assignment",
        "equality_substitution",
        "arithmetic_evaluation",
        "incompatible_equalities",
    ]
    substitution = next(
        node
        for node in explanation.proof.nodes
        if node.rule_id == "equality_substitution"
    )
    assert "operand_variable" not in substitution.conclusion
    assert substitution.conclusion["operand"] == 2


#: A machine whose case applies only under a guard, so its condition is not free.
#:
#: The guard is what makes the second transition reachable: with ``x >= 2`` the
#: self-loop cannot fire and the machine leaves ``A``, so neither the state at the
#: next frame nor the guard is settled by the prefix alone.  A case here carries a
#: two-member condition and the core does not force it.
_GUARDED_CASE_MODEL = """
def int x = 0;

state Root {
    state A;
    state B;

    [*] -> A;
    A -> A : if [x < 2] effect { x = x + 1; };
    A -> B;
}
"""


@pytest.mark.unittest
@pytest.mark.parametrize(
    "assumptions, expected_mode",
    [
        # The core here keeps a step whose relation has no readable assignment, and
        # no citation covers it, so the contradiction cannot rest on every member.
        (
            'assume at 2: var("x") == 1;\nassume at 3: var("x") == 0;\n',
            "formal",
        ),
        # This core's members are all either readable or reachable by a citation, so
        # the guard stops being what holds the depth back.
        ('assume at 3: var("x") == 5;\n', "proof"),
    ],
    ids=["an_unreadable_step_in_the_core", "every_member_accounted_for"],
)
@pytest.mark.unittest
def test_a_guarded_case_holds_the_depth_back_only_while_a_member_is_unaccounted_for(
    assumptions: str, expected_mode: str
) -> None:
    """What a guard costs, separated from what an unreadable member costs.

    This asserted that a guarded case leaves the artifact at ``formal``, for both
    queries, and the reason it gave was the guard: a guard leaves the state at the next
    frame and the guard's own value unsettled, so ``transition_assignment`` never gets a
    value fact at the case's frame.  The first half of that survived the catalog gaining
    a rule that supplies exactly such a value by entailment; the attribution did not.
    The guard was never what held the second query back on its own.

    The two cores differ in something else, and that is what decides the depth.  The
    first keeps a step relation with no readable assignment and no citation reaching it,
    so the coverage requirement refuses the proof -- the honest outcome, and the same
    boundary a reader meets whenever a core member has no account.  In the second every
    member is either read or cited, and the chain closes.

    Both ids assert the published condition count as well, because a fixture that
    stopped publishing a guarded condition would test neither thing.

    :param assumptions: The query's assumption lines.
    :type assumptions: str
    :param expected_mode: The depth this core is expected to reach.
    :type expected_mode: str
    """
    machine = load_state_machine_from_text(_GUARDED_CASE_MODEL, "machine.fcstm")
    context = BmcEngine(machine).prepare(
        assumptions + 'check reach <= 3: active("Root.A");\n',
        query_source_path="query.fbmcq",
    )
    feasibility = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    ).feasibility
    explanation = feasibility.explanation

    published = [item.normalized_fact or {} for item in explanation.core.items]
    conditions = [
        len(fact.get("condition") or ())
        for fact in published
        if fact.get("kind") == "transition_case"
    ]

    assert conditions and all(count >= 2 for count in conditions), (
        "the fixture must publish a case whose condition names both the state and "
        "the guard, or it is not testing the refusal"
    )
    assert explanation.achieved_mode == expected_mode

    if expected_mode == "formal":
        assert explanation.proof is None
        assert {fact.get("kind") for fact in published} & {"structural_constraint"}, (
            "this id exists for the core that keeps a member no fact was read from"
        )
    else:
        assert explanation.proof is not None
        assert explanation.proof.verification_status == "verified"


@pytest.mark.unittest
def test_a_published_condition_only_names_readings_the_discharge_shares() -> None:
    """Publication and the discharge read a condition the same two ways.

    The discharge refuses a condition slot it cannot encode, and that guard is never
    reached -- not because the shape is rare but because publication already declined
    it: a conjunct neither a state equality nor a variable comparison makes the whole
    case fall back to ``structural_constraint``.  The agreement is what makes the
    guard a property rather than a coincidence, so it is asserted here rather than
    left to the two functions happening to stay in step.

    Written as an assertion over what a real query publishes, because that is where
    the two readings meet.  Forging a condition to reach the guard would prove the
    guard runs, which was never in doubt, and not the thing that matters.
    """
    feasibility = _explain_case_model(
        'assume at 2: var("x") == 1;\n'
        'assume at 3: var("x") == 0;\n'
        'check reach <= 3: active("Root.A");\n'
    )
    conditions = [
        member
        for item in feasibility.explanation.core.items
        for member in ((item.normalized_fact or {}).get("condition") or ())
    ]

    assert conditions, "the fixture must publish at least one condition"
    assert {member.get("kind") for member in conditions} <= {
        "state_membership",
        "variable_comparison",
    }


#: The model from the motivating issue, whose update lives in a ``during`` action.
#:
#: Every fixture above puts its assignment on a transition's ``effect``.  This one is
#: how the issue's own reporter wrote it -- the state carries a ``during`` block, and
#: the event-triggered entry plus the unconditional exit give the step relations a
#: different shape.  Both are ordinary FCSTM, and only the first shape was ever
#: exercised, which is how a reachability claim came to rest on the easier one.
_DURING_ACTION_MODEL = """
def int retries = 0;

state Uploader {
    event Fail;

    state Idle;
    state Retrying {
        during {
            retries = retries + 1;
        }
    }
    state GaveUp;

    [*] -> Idle;
    Idle -> Retrying :: Fail;
    Retrying -> GaveUp;
}
"""


def _explain_during_model(query: str, mode: str = "proof"):
    """Run one query against the ``during``-action machine and return the outcome."""
    machine = load_state_machine_from_text(_DURING_ACTION_MODEL, "retry.fcstm")
    context = BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation=mode,
    )
    return result.feasibility


@pytest.mark.unittest
def test_an_event_driven_during_action_closes_within_one_step() -> None:
    """The chain closes for an update written as a ``during`` action.

    Every other fixture here puts its assignment on a transition's ``effect``.  This
    model is how the motivating issue's reporter wrote it, and three things kept it
    from closing -- none of them a missing capability.

    The entry step's case condition names the event that triggers it, and the
    condition reader knew two readings, state membership and variable comparison,
    while the event reading it needed already existed one function away in the
    proposition publisher.  The binding side then had to learn the same reading, or
    the fact named a symbol "the group does not mention".  And the step read *two*
    assignments where the publisher requires exactly one: the second is the fallback
    case for "in this state and no transition applies", whose condition reduces to
    ``s == state and not s == state`` and therefore never holds.  A case that cannot
    apply says nothing about the step, so counting it hid the one that does.

    The contradiction here is inside one step, which is the part that now works.  The
    issue's own query puts it a frame later, and that needs something this catalog
    does not have -- see the test below.
    """
    feasibility = _explain_during_model(
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at 1: var("retries") == 0;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n'
    )
    explanation = feasibility.explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert [node.rule_id for node in explanation.proof.nodes] == [
        "source_fact",
        "source_fact",
        "source_fact",
        "case_condition_entailment",
        "transition_assignment",
        "arithmetic_evaluation",
        "incompatible_equalities",
    ]


@pytest.mark.unittest
def test_a_value_a_step_leaves_alone_still_reaches_the_next_frame() -> None:
    """A contradiction spanning a step that only preserves the variable closes.

    This test's subject is the boundary it used to pin.  It asserted that the answer
    degrades here, on the reasoning that the step from frame 1 to frame 2 only carries
    ``retries`` forward, that the published reading declines a requirement saying
    "x becomes x", and that closing it therefore needed a fact kind for "this step
    leaves the variable alone".  The reasoning was right about the reading and wrong
    about the only way out: what the step will not *say* it still *constrains*, and
    a constraint is something the solver tier can be asked about.

    The chain is longer than the frame-1 case by exactly the step it crosses, and the
    citation names that step.  It does not necessarily name the frame's own state
    requirement, which is worth writing down because the first draft of this test
    asserted that it would: the step relation alone does not force the value, so
    something has to select the preserving case, but which members do the selecting is
    whatever the deletion pass keeps.  Here it keeps the initial value and the first
    step rather than the state assumption -- a different set, equally sufficient.  The
    shrink is greedy, not minimum-cardinality, so pinning one particular set would pin
    the deletion order instead of the property.
    """
    query = (
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at %d: var("retries") == 0;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n'
    )
    within_one_step = _explain_during_model(query % 1).explanation
    across_a_step = _explain_during_model(query % 2).explanation

    for reading in (within_one_step, across_a_step):
        assert reading.achieved_mode == "proof"
        assert reading.proof is not None
        assert reading.proof.verification_status == "verified"

    carried = [
        node
        for node in across_a_step.proof.nodes
        if node.rule_id == "preceding_value_entailment"
    ]
    assert len(carried) == 1, "the crossing is expected to take exactly one carry"
    assert carried[0].verification_method == "solver_entailment"
    assert len(across_a_step.proof.nodes) > len(within_one_step.proof.nodes)

    # The step being crossed is what the carry is about, so it is cited whatever else
    # the shrink keeps.  The set is also a strict subset of the core: a carry citing
    # every member would be the vacuous case the consistency guard exists to refuse.
    cited = set(carried[0].item_ids)
    members = {item.constraint.stable_id for item in across_a_step.core.items}

    assert "transition.step.0001" in cited
    assert cited < members


@pytest.mark.unittest
def test_a_published_event_names_the_path_its_author_wrote() -> None:
    """A proposition identity spells the declared path, not the symbol's body.

    The encoder's symbol body replaces a path's dots, so a name recovered from it
    reads ``Uploader_Idle_Fail`` where the author wrote ``Uploader.Idle.Fail``.  The
    domain's own event table is the authority, and this asserts against that table
    rather than against a literal: a published identity whose subject the domain does
    not declare is one the reader cannot look up and a rule cannot match, and the two
    readings of one symbol lived one function apart.
    """
    machine = load_state_machine_from_text(_DURING_ACTION_MODEL, "retry.fcstm")
    context = BmcEngine(machine).prepare(
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at 2: var("retries") == 0;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    declared = {entry["path"] for entry in core.context.domain.to_canonical()["events"]}
    feasibility = solve_bmc_property(
        compile_bmc_property(core), infeasibility_explanation="proof"
    ).feasibility

    published = []
    for item in feasibility.explanation.core.items:
        fact = item.normalized_fact or {}
        candidates = [fact] + list(fact.get("condition") or ())
        published.extend(
            entry["identity"]
            for entry in candidates
            if entry.get("kind") == "proposition"
        )

    assert published, "the query was chosen because its core carries an event"
    for identity in published:
        subject, _, step = identity.rpartition("@")
        assert subject in declared, (
            "published %r names %r, which the domain does not declare; it declares %s"
            % (identity, subject, sorted(declared))
        )
        assert step.isdigit()

    # Membership in the table is not enough on its own: with two events whose paths
    # differ only in where the dots fall, the other one is also declared, so a
    # subject picked wrongly would still pass the loop above.  This names the event
    # the transition under test is triggered by.
    assert {identity.rpartition("@")[0] for identity in published} == {
        "Uploader.Idle.Fail"
    }

    # The other publishing entrance, on the same model.  A bare event assumption is
    # read by a different function from a condition's conjunct, and it already
    # resolved against the table -- which is why nothing here was failing before.
    # Nothing pinned it either, so its passing the table was untested rather than
    # established.
    bare = BmcEngine(machine).prepare(
        'assume event("Uploader.Idle.Fail", 0) == true;\n'
        'assume event("Uploader.Idle.Fail", 0) == false;\n'
        'check reach <= 1: active("Uploader.GaveUp");\n',
        query_source_path="query.fbmcq",
    )
    opposed = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(bare)),
        infeasibility_explanation="proof",
    ).feasibility.explanation

    assert {
        (item.normalized_fact or {}).get("identity")
        for item in opposed.core.items
        if (item.normalized_fact or {}).get("kind") == "proposition"
    } == {"Uploader.Idle.Fail@0"}


#: Two events whose paths differ only in where the dots fall.
#:
#: The encoder's symbol body replaces the dots, so both collapse to one name and a
#: reading that recovers the body cannot tell them apart.  Declaring the second one
#: is the whole difference between the two models below: it takes part in no
#: transition the query mentions.
_COLLIDING_EVENT_MODEL = """
def int x = 0;

state Root {
    state A_B {
        state Idle {
            event Go;
        }
        state Done;

        [*] -> Idle;
        Idle -> Done :: Go effect {
            x = x + 1;
        }
    }
%s
    [*] -> A_B;
}
"""

_UNRELATED_EVENT_DECLARATION = """
    state A {
        state B {
            state Idle {
                event Go;
            }
            [*] -> Idle;
        }
        [*] -> B;
    }
"""


@pytest.mark.unittest
@pytest.mark.parametrize(
    "extra", ["", _UNRELATED_EVENT_DECLARATION], ids=["alone", "with_a_namesake"]
)
def test_an_event_a_query_never_mentions_does_not_change_the_answer(extra: str) -> None:
    """Declaring an unrelated event leaves the proof this query gets untouched.

    The second declaration takes part in no transition the query mentions, so the
    core is the same core and the chain that closes it is the same chain.  What it
    does share is the name the encoder's symbol body collapses to, and a reading
    that recovers a subject from that body rather than from the domain's table would
    file both events under one key -- which is not a wrong sentence in the output but
    a proof that stops closing, because the premise gets filed where the rule does
    not look for it.

    The two ids do different jobs, and only one of them fails on a body reading:
    ``alone`` is the control that this model and query close at all, ``with_a_namesake``
    is the assertion about the collapse.  Neither is decoration -- withholding the
    discharge fails both.
    """
    machine = load_state_machine_from_text(
        _COLLIDING_EVENT_MODEL % extra, "collide.fcstm"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A_B.Idle") where x == 0;\n'
        'assume at 1: active("Root.A_B.Idle");\n'
        'assume event("Root.A_B.Idle.Go", 1) == true;\n'
        'assume at 1: var("x") == 0;\n'
        'assume at 2: var("x") == 0;\n'
        'check reach <= 2: active("Root.A_B.Done");\n',
        query_source_path="query.fbmcq",
    )
    explanation = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="proof",
    ).feasibility.explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert "case_condition_entailment" in {
        node.rule_id for node in explanation.proof.nodes if node.rule_id
    }


#: The four queries the motivation for this catalog work states expectations for.
#:
#: Written out here rather than referenced, because the point of the table is that
#: each shape closes: an arithmetic chain crossing a step, an event opposition, a
#: state opposition, and a same-frame value conflict as the control.
_CLOSING_QUERIES = {
    "an_arithmetic_chain_across_a_step": (
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at 2: var("retries") == 0;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n',
        "preceding_value_entailment",
    ),
    "an_event_demanded_and_ruled_out": (
        'assume event("Uploader.Fail", 0) == true;\n'
        'assume event("Uploader.Fail", 0) == false;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n',
        "boolean_complement",
    ),
    "a_state_demanded_and_ruled_out": (
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at 1: !active("Uploader.Retrying");\n'
        'check reach <= 2: active("Uploader.GaveUp");\n',
        "excluded_state_selected",
    ),
    "one_frame_two_values": (
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 0: var("retries") == 1;\n'
        'check reach <= 2: active("Uploader.GaveUp");\n',
        "incompatible_equalities",
    ),
}


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query, closer",
    list(_CLOSING_QUERIES.values()),
    ids=list(_CLOSING_QUERIES),
)
def test_each_shape_the_catalog_was_extended_for_closes_at_proof_depth(
    query: str, closer: str
) -> None:
    """Every shape reaches a verified proof, and the named rule is what took part.

    Four shapes rather than one, and the rule is asserted rather than only the depth,
    because reaching proof depth by a different route would satisfy the depth check
    while leaving the rule this shape exists for unexercised -- which is the state two
    of these were in before, reported as reachable by a closure analysis that read
    premise kinds without running a query.

    :param query: The query text.
    :type query: str
    :param closer: The rule expected to take part in the chain.
    :type closer: str
    """
    explanation = _explain_during_model(query).explanation

    assert explanation.achieved_mode == "proof"
    assert explanation.status == "complete"
    assert explanation.proof is not None
    assert explanation.proof.verification_status == "verified"
    assert closer in {node.rule_id for node in explanation.proof.nodes if node.rule_id}


@pytest.mark.unittest
def test_no_rule_in_the_catalog_is_left_without_a_query_that_reaches_it() -> None:
    """The catalog has no member that only a closure analysis calls reachable.

    Reachability was once read off ``premise_kinds`` alone, and four rules that the
    reading called reachable were never lit by any query.  The record of which rules a
    real run reaches therefore lives with the runs, not with the analysis: this asserts
    the published set of reachable ids is the whole catalog, and the queries above plus
    the rest of this module are what make it so.
    """
    from pyfcstm.bmc.proof_rules import PROOF_RULES, UNREACHABLE_RULE_IDS

    assert UNREACHABLE_RULE_IDS == ()
    assert len(PROOF_RULES) == 12


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query",
    [pair[0] for pair in _CLOSING_QUERIES.values()],
    ids=list(_CLOSING_QUERIES),
)
def test_a_solver_settled_step_is_re_provable_from_the_members_it_cites(
    query: str,
) -> None:
    """Every solver-settled step still holds when the claim is re-proved from scratch.

    The phase that settles these steps decides two things -- that the cited members
    entail the target, and that they can hold together -- and then the artifact reports
    ``solver_entailment`` and nothing re-asks.  A shrink that stopped one deletion too
    late, or a target encoded against the wrong symbol, would produce a step the
    checker cannot see and the reader has no way to doubt.  So this re-asks both
    questions with a solver of its own, over the members named in the published
    citation and nothing else.

    Satisfiability of the citation is the half that makes the other half mean anything:
    a set that cannot hold entails every target, its own negation included.

    Both kinds of solver-settled step are re-asked, and the second was added after the
    first version skipped it.  A step that discharges a case's condition concludes a
    fact rather than a value, so the value branch below has nothing to check for it --
    and skipping it meant the only claim being re-verified for that step was that its
    citation could hold, which is the weaker half.  The condition it discharged is
    re-encoded from the premise's published facts and refuted against the citation.

    :param query: The query text.
    :type query: str
    """
    import z3

    from pyfcstm.bmc.infeasibility import (
        _binding_symbols,
        _declared_variable_names,
        _encode_condition_member,
        _event_paths_of,
    )

    machine = load_state_machine_from_text(_DURING_ACTION_MODEL, "retry.fcstm")
    core = build_bmc_core_formula(
        BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
    )
    explanation = solve_bmc_property(
        compile_bmc_property(core), infeasibility_explanation="proof"
    ).feasibility.explanation

    assert explanation.proof is not None
    by_id = {node.stable_id: node for node in explanation.proof.nodes}
    claims = {
        group.stable_id: (
            z3.And(*group.expressions) if group.expressions else z3.BoolVal(True)
        )
        for group in core._tracked_groups
    }
    published = [item.constraint.stable_id for item in explanation.core.items]
    symbols = _binding_symbols(
        z3.And(*[claims[stable_id] for stable_id in published if stable_id in claims]),
        _declared_variable_names(core),
        _event_paths_of(core),
    )

    for node in explanation.proof.nodes:
        if node.verification_method != "solver_entailment":
            continue
        cited = [
            claims[stable_id] for stable_id in node.item_ids if stable_id in claims
        ]

        assert cited, "a solver-settled step has to name the members it rests on"
        together = z3.Solver()
        together.add(*cited)

        assert together.check() == z3.sat, (
            "%s cites members that cannot hold together, which entail anything"
            % node.rule_id
        )

        conclusion = dict(node.conclusion or {})
        if conclusion.get("kind") == "transition_case":
            # The claim is that the citation forces the condition this step removed,
            # so the condition is what has to be refuted -- read off the premise,
            # because the conclusion is the case with the key gone.
            premises = [by_id[premise_id] for premise_id in node.premise_ids]

            assert len(premises) == 1, "a discharge reads exactly one case"
            discharged = (dict(premises[0].conclusion or {})).get("condition") or ()

            assert discharged, "a discharge is expected to have removed something"
            encoded = [
                _encode_condition_member(dict(member), symbols) for member in discharged
            ]

            assert all(item is not None for item in encoded), (
                "the condition this step discharged has a member no symbol matches, "
                "so the publishing and binding readings have diverged"
            )
            refuted_condition = z3.Solver()
            refuted_condition.add(*cited, z3.Not(z3.And(*encoded)))

            assert refuted_condition.check() == z3.unsat, (
                "%s discharged a condition its own citation does not force"
                % node.rule_id
            )
            continue
        if conclusion.get("kind") != "variable_equality" or conclusion.get(
            "state_slot"
        ):
            continue
        symbol = symbols.get((conclusion.get("frame"), conclusion.get("variable")))

        assert symbol is not None, "the conclusion names a slot no member mentions"
        refuted = z3.Solver()
        refuted.add(*cited, symbol != conclusion.get("value"))

        assert refuted.check() == z3.unsat, (
            "%s concludes %r, which its own citation does not force"
            % (node.rule_id, conclusion)
        )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query",
    [pair[0] for pair in _CLOSING_QUERIES.values()],
    ids=list(_CLOSING_QUERIES),
)
def test_the_same_query_publishes_the_same_proof_every_time(query: str) -> None:
    """One query, one proof, byte for byte.

    The citation each solver-settled step publishes comes out of a deletion pass over
    the members, so the answer depends on the order they are visited in.  That order is
    the published member order rather than a set's iteration order, and this is what
    holds it that way: a proof that varied between runs would make every artifact a
    reader saved unreproducible, and the variation would show up as a flake somewhere
    far from its cause.

    What this cannot see, stated because the reverse would be assumed: three runs in
    one process share a hash seed, and a set's iteration order is stable within a
    process, so iterating a set of strings somewhere in the chain would produce a proof
    that is identical here and different on the next machine.  Determinism against that
    rests on construction instead -- every place an order is published goes through
    ``sorted``, and the phases iterate sequences rather than sets.  Measured across four
    ``PYTHONHASHSEED`` values in separate processes, the canonical proof was identical
    for both shapes; that measurement is evidence and not a gate, because asserting the
    citation is sorted would pass on these fixtures whether or not ``sorted`` were
    there -- the published member order already happens to be alphabetical.

    :param query: The query text.
    :type query: str
    """
    import json

    shapes = set()
    for _ in range(3):
        machine = load_state_machine_from_text(_DURING_ACTION_MODEL, "retry.fcstm")
        explanation = solve_bmc_property(
            compile_bmc_property(
                build_bmc_core_formula(
                    BmcEngine(machine).prepare(query, query_source_path="query.fbmcq")
                )
            ),
            infeasibility_explanation="proof",
        ).feasibility.explanation

        assert explanation.proof is not None
        shapes.add(
            json.dumps(
                explanation.proof.to_canonical(), sort_keys=True, ensure_ascii=False
            )
        )

    assert len(shapes) == 1, "the proof differed between runs of one query"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "contradicted_frame, bound, expected_mode, expected_carries",
    [(2, 2, "proof", 1), (3, 3, "formal", 0), (4, 4, "formal", 0)],
    ids=["one_step_away", "two_steps_away", "three_steps_away"],
)
def test_a_value_carries_across_one_untouched_step_and_no_further(
    contradicted_frame: int, bound: int, expected_mode: str, expected_carries: int
) -> None:
    """The reach of the carry, pinned on both sides of its own boundary.

    The rule that pins a value at the preceding frame concludes into a derived node,
    and the citation seam records a verdict per member, so that conclusion cannot be
    the premise of a second application: there is no member to record the verdict
    against.  One step closes and two do not, and both halves are asserted here
    because the degradation alone would be satisfied by the rule never firing at all.

    Iterating would mean attributing an entailment to a subtree rather than to a
    member, which is the shape the attribution refuses on purpose.  So this is a
    boundary to know rather than a defect to fix, and it is written down where a
    reader meets it.

    :param contradicted_frame: The frame the contradicted assumption sits at.
    :type contradicted_frame: int
    :param bound: The query's bound.
    :type bound: int
    :param expected_mode: The depth this shape is expected to reach.
    :type expected_mode: str
    :param expected_carries: How many carry steps the proof is expected to hold.
    :type expected_carries: int
    """
    explanation = _explain_during_model(
        'init state("Uploader.Idle") where retries == 0;\n'
        'assume at 1: active("Uploader.Retrying");\n'
        'assume at %d: var("retries") == 0;\n'
        'check reach <= %d: active("Uploader.GaveUp");\n' % (contradicted_frame, bound)
    ).explanation

    assert explanation.achieved_mode == expected_mode
    carried = [
        node
        for node in (explanation.proof.nodes if explanation.proof else ())
        if node.rule_id == "preceding_value_entailment"
    ]

    assert len(carried) == expected_carries
    if expected_mode == "formal":
        assert explanation.proof is None
        assert "no rule in the catalog closes this core" in explanation.reason
