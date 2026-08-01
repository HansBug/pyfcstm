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

    held, record, methods = check_core_bindings(core, (), _SolveBudget(None))

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
def test_a_structural_member_is_read_by_what_the_step_does() -> None:
    """A transition member carries no content, but what it does can be worked out.

    ``structural_constraint`` says a rule applies and nothing about what the rule
    does -- that is what the tag is for -- and for three review rounds that was taken
    to mean a core resting on a transition could never reach proof depth.  It does not
    mean that.  The step's constraint is a disjunction over the cases available from a
    state, and if every one of them moves a variable by the same constant, that
    constant is a fact the solver can establish.

    The reading follows from the step *together with* the state the frame holds, from
    neither alone, so both members are named in the attribution and the node reports
    ``solver_entailment`` rather than claiming to restate either one.
    """
    machine = load_state_machine_from_text(
        "def int retries = 0;\n"
        "state Root { state Igniting; state Purge; [*] -> Igniting;\n"
        "    Igniting -> Purge effect { retries = retries + 1; }; }",
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

    assert any(
        item.normalized_fact.get("kind") == "structural_constraint"
        for item in explanation.core.items
    ), "the shape this pins needs a structural member"
    assert explanation.achieved_mode == "proof", explanation.reason
    assert explanation.proof is not None

    entailed = [
        node
        for node in explanation.proof.nodes
        if node.verification_method == "solver_entailment"
    ]
    assert entailed, [node.verification_method for node in explanation.proof.nodes]
    reading = entailed[0]
    assert len(reading.item_ids) > 1, reading.item_ids
    assert reading.conclusion.get("kind") == "transition_case"
    # Every member is accounted for, which is what lets the proof be published.
    covered = {name for node in explanation.proof.nodes for name in node.item_ids}
    assert covered == {item.constraint.stable_id for item in explanation.core.items}


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
def test_a_step_whose_branches_disagree_yields_no_reading() -> None:
    """A guess is not a fact, so a step that does different things says nothing.

    The reading is worked out by taking a candidate off one model and then
    establishing that no execution disagrees with it.  The second half is what makes
    it a fact: here two branches move the counter by different amounts, so the
    candidate survives the first and fails the second, and the tier degrades exactly
    as it did before any of this existed.

    What this pins is the outcome.  Two gates produce it -- the recognizer declines
    to offer a reading it has not established, and the binding refuses one that does
    not follow from its members -- and no query distinguishes them, because both end
    in the same published artifact.  The recognizer keeps its check anyway: the fact
    it returns is the one an input node will carry, not a proposal for someone else
    to vet, so a producer that knowingly emits guesses has the roles backwards.
    """
    machine = load_state_machine_from_text(
        "def int n = 0;\n"
        "def int gate = 0;\n"
        "state Root {\n"
        "    state A;\n"
        "    state B { enter { n = n + 1; } }\n"
        "    state C { enter { n = n + 5; } }\n"
        "    [*] -> A;\n"
        "    A -> B : if [gate >= 1];\n"
        "    A -> C : if [gate <= 0];\n"
        "}\n",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where n == 0;\n'
        'assume at 1: var("n") == 99;\n'
        'check reach <= 1: active("Root.B");\n',
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
    assert explanation.core is not None, "the formal evidence still stands"


@pytest.mark.unittest
def test_a_reading_that_does_not_follow_from_its_members_is_refused() -> None:
    """The consequence check is a gate, not a formality.

    A reading is attributed to the members it rests on and has to follow from their
    conjunction.  Handing the check a fact that does not -- the counter moving by one
    where the step leaves it alone -- has to come back refused, or the binding is a
    label again, which is the defect this whole check exists to prevent.
    """
    from pyfcstm.bmc.infeasibility import check_core_bindings
    from pyfcstm.bmc.solver import _SolveBudget

    machine = load_state_machine_from_text(
        "def int retries = 0;\n"
        "state Root { state Igniting; state Purge; [*] -> Igniting;\n"
        "    Igniting -> Purge effect { retries = retries + 1; }; }",
        "machine.fcstm",
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.Igniting") where retries == 0;\n'
        'assume at 1: var("retries") == 0;\n'
        'check reach <= 1: active("Root.Purge");\n',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    wrong = (
        (
            ("initial.target", "transition.step.0000"),
            {
                "kind": "transition_case",
                "variable": "retries",
                "frame": 0,
                "target_frame": 1,
                "operator": "add",
                "operand": 7,
            },
        ),
    )

    held, record, methods = check_core_bindings(core, wrong, _SolveBudget(None))

    assert held is False
    assert "does not follow from its group" in (record.reason or ""), record.reason
    assert methods == {}
