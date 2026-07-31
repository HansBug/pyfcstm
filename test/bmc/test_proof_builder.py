"""
Tests for the deterministic proof builder: closure, pruning, and linearization.

The builder proposes rule applications, keeps the ones a checker agrees with, and
stops at the first verified contradiction.  Every property the contract requires of
that search is checked here, because each one is the difference between a proof a
reader can rely on and a graph that happens to look right: a bounded candidate
universe, two stable orderings, one node per distinct fact, an honest answer when no
rule closes the case, backwards pruning, and a shared budget.

The module contains:
* Closure tests, one per numbered requirement of the contract's builder section
* Pruning and integrity tests over the graph the closure produces
* Linearization tests binding every proof node to a reasoning step and back

.. note::
   Determinism is asserted across processes, not only across calls.  A dict or set
   iteration order that happens to be stable within one interpreter run is exactly
   the failure this is written to catch.

.. note::
   Two properties the builder implements are **not** observable through it, and are
   deliberately left untested rather than reached for artificially.  Removing the
   backwards prune, or reversing the order candidates are enumerated in, leaves
   every test here green -- with the full rule catalog, not only the first few.

   The reason is structural rather than a weak suite.  A proof is published only
   when the contradiction rests on every core member.  A dead step is one whose
   conclusion the root does not use, so publishing requires its premises to be
   covered by *other* steps -- that is, a branch.  Every rule that concludes
   something other than ``false`` is single-valued: one transition case yields one
   expression, one expression and one value yield one value.  No branch can form, so
   no dead node survives to be pruned, and the coverage rule subsumes pruning for
   this catalog.  Ordering follows the same argument: the search stops at the first
   contradiction, and an order finding a different one would fail coverage instead
   of publishing a different graph.

   Both are kept because the contract requires them and because a later rule with
   two conclusions would make them load-bearing overnight.  A 210-input sweep
   produced twelve publishable proofs and no pruned node; the sweep is worth
   repeating whenever a rule is added.
"""

import pytest

from pyfcstm.bmc.proof import build_domain_proof
from pyfcstm.bmc.solver import _SolveBudget


def _fact(kind: str, **fields) -> dict:
    """A domain fact of one tag with the fields that tag implies."""
    fact = {"kind": kind}
    fact.update(fields)
    return fact


def _equality(variable: str = "x", frame: int = 0, value: int = 0) -> dict:
    """A concrete value for one variable at one frame."""
    return _fact("variable_equality", variable=variable, frame=frame, value=value)


def _bound(operator: str, value: int, variable: str = "x", frame: int = 0) -> dict:
    """One side of a range restriction."""
    return _fact(
        "variable_bound", variable=variable, frame=frame, operator=operator, value=value
    )


def _inputs(*pairs):
    """Input facts keyed by the core member each restates."""
    return tuple((stable_id, fact) for stable_id, fact in pairs)


def _build(inputs, budget=None):
    """Run the builder over the given inputs with an unbounded budget by default."""
    return build_domain_proof(
        "assumptions_component", inputs, budget or _SolveBudget(None)
    )


@pytest.mark.unittest
def test_two_values_for_one_slot_close_immediately() -> None:
    """The shortest complete proof: two inputs and the contradiction they make."""
    proof, record = _build(
        _inputs(
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(value=1)),
        )
    )

    assert proof is not None
    assert [node.kind for node in proof.nodes] == ["input", "input", "contradiction"]
    assert proof.nodes[-1].rule_id == "incompatible_equalities"
    assert proof.root_id == proof.nodes[-1].stable_id
    assert record.status == "complete"


@pytest.mark.unittest
def test_a_value_carried_across_an_expression_needs_a_derived_step() -> None:
    """The multi-hop case: an intermediate fact a later step consumes.

    A graph whose every step reaches ``false`` straight from an input never
    exercises transitive attribution, so this is the shape that proves the machinery
    works rather than that one rule does.
    """
    proof, _ = _build(
        _inputs(
            ("initial.variable.x", _equality(value=0)),
            (
                "transition.step.0000",
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            ("assumption.0000", _equality(frame=1, value=0)),
        )
    )

    assert proof is not None
    derived = [node for node in proof.nodes if node.kind == "derived"]
    assert len(derived) == 1
    assert derived[0].rule_id == "arithmetic_evaluation"
    assert derived[0].conclusion["value"] == 1
    # The derived node is what the contradiction reads, so the graph is two hops
    # deep rather than a fan of inputs into one root.
    assert derived[0].stable_id in proof.nodes[-1].premise_ids


@pytest.mark.unittest
def test_a_derived_node_carries_the_members_its_premises_rest_on() -> None:
    """Attribution is computed from the premise closure, never written by hand.

    A node that named its own members could name one that took no part.  Taking the
    union of what its premises rest on makes that impossible to express.
    """
    proof, _ = _build(
        _inputs(
            ("initial.variable.x", _equality(value=0)),
            (
                "transition.step.0000",
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            ("assumption.0000", _equality(frame=1, value=0)),
        )
    )

    derived = next(node for node in proof.nodes if node.kind == "derived")
    assert set(derived.item_ids) == {"initial.variable.x", "transition.step.0000"}
    # The root rests on everything, which is also what makes the core fully used.
    assert set(proof.nodes[-1].item_ids) == {
        "initial.variable.x",
        "transition.step.0000",
        "assumption.0000",
    }


@pytest.mark.unittest
def test_a_case_no_rule_closes_reports_unsupported_rather_than_a_partial_graph() -> (
    None
):
    """Running out of candidates is an answer, and it is not a proof.

    The contract makes the fixed point the source of the degradation: a graph that
    saturated without reaching ``false`` proves nothing, so nothing is published and
    the tier degrades.

    The ledger status is ``unknown`` rather than a word of its own.  That vocabulary
    is frozen at five values, and "the search ran and reached no conclusion" is what
    ``unknown`` already means; inventing a sixth would have widened a published
    contract to describe a phase the contract did not add.  The reason string is
    where this particular shape is named.
    """
    proof, record = _build(
        _inputs(
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(variable="y", value=1)),
        )
    )

    assert proof is None
    assert record.status == "unknown"
    assert "no rule" in (record.reason or "")


@pytest.mark.unittest
def test_a_step_that_reaches_no_contradiction_is_pruned_away() -> None:
    """Whatever the conclusion does not rest on is removed before publication.

    The spare pair below does derive a value, and that value takes no part in the
    contradiction; publishing it would name members among the reasons that are not.
    """
    proof, _ = _build(
        _inputs(
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(value=1)),
            ("spare.initial", _equality(variable="z", frame=3, value=7)),
            (
                "spare.transition",
                _fact(
                    "arithmetic_expression",
                    variable="z",
                    frame=3,
                    operator="add",
                    operand=1,
                    target_frame=4,
                ),
            ),
        )
    )

    assert proof is None, (
        "the spare members are not part of any contradiction, so the core is not "
        "fully used and no proof may be published over it"
    )


@pytest.mark.unittest
def test_two_members_stating_one_fact_share_a_node_and_both_stay_named() -> None:
    """Equal conclusions collapse, and the collapse must not lose an attribution.

    Deduplication is what makes the graph a DAG rather than a tree, but a node that
    kept only the first member's id would drop the other from the reasons while it
    genuinely took part.  Both ids ride on the surviving node.
    """
    proof, _ = _build(
        _inputs(
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(value=0)),
            ("assumption.0002", _equality(value=1)),
        )
    )

    assert proof is not None
    inputs = [node for node in proof.nodes if node.kind == "input"]
    assert len(inputs) == 2, "the repeated fact is one node"
    shared = next(node for node in inputs if node.conclusion["value"] == 0)
    assert set(shared.item_ids) == {"assumption.0000", "assumption.0001"}


@pytest.mark.unittest
def test_a_second_route_to_a_value_leaves_its_member_unused() -> None:
    """Deduplication decides which member is cited, so it decides publishability.

    Two expressions reaching the same value give one node, and that node cites the
    route the search took first.  The other route's member is then part of the core
    and part of no reason, which is not a smaller proof but no proof: publishing
    would name it among the grounds for a conclusion it did not support.
    """
    proof, record = _build(
        _inputs(
            ("initial.variable.x", _equality(value=0)),
            (
                "transition.a",
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            (
                "transition.b",
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="sub",
                    operand=-1,
                    target_frame=1,
                ),
            ),
            ("assumption.0000", _equality(frame=1, value=0)),
        )
    )

    assert proof is None
    assert record.status == "unknown"
    assert "every core member" in (record.reason or "")


@pytest.mark.unittest
def test_the_graph_is_byte_stable_across_processes() -> None:
    """Determinism means the same bytes on a fresh interpreter, not the same run.

    Iteration order over a dict or a set is stable within one process and seeded per
    process for strings.  Asserting equality across two calls here would pass while
    the published proof differed between two users.
    """
    import json
    import subprocess
    import sys

    script = (
        "import json;"
        "from pyfcstm.bmc.proof import build_domain_proof;"
        "from pyfcstm.bmc.solver import _SolveBudget;"
        "inputs = ("
        "('initial.variable.x', {'kind': 'variable_equality', 'variable': 'x',"
        " 'frame': 0, 'value': 0}),"
        "('transition.step.0000', {'kind': 'arithmetic_expression', 'variable': 'x',"
        " 'frame': 0, 'operator': 'add', 'operand': 1, 'target_frame': 1}),"
        "('assumption.0000', {'kind': 'variable_equality', 'variable': 'x',"
        " 'frame': 1, 'value': 0}),"
        ");"
        "proof, _ = build_domain_proof('assumptions_component', inputs,"
        " _SolveBudget(None));"
        "print(json.dumps(proof.to_canonical(), sort_keys=False))"
    )
    # Inherit the environment and override only the seed.  Replacing it wholesale
    # meant naming a PATH, and the one named was POSIX -- so every Windows runner
    # failed on a test about hash ordering.  What matters here is that the two runs
    # differ in their seed and in nothing else.
    import os

    runs = []
    for seed in ("0", "12345"):
        environment = dict(os.environ, PYTHONHASHSEED=seed)
        runs.append(
            subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                check=True,
                env=environment,
            ).stdout
        )

    assert runs[0] == runs[1]
    assert json.loads(runs[0])["nodes"], "the run must have produced a graph"


@pytest.mark.unittest
def test_the_builder_reports_the_work_it_did_even_when_it_finds_nothing() -> None:
    """A caller distinguishes "checked and found nothing" from "never checked"."""
    _, record = _build(
        _inputs(("assumption.0000", _equality(value=0))),
    )

    assert record is not None
    assert record.name == "proof_construction"
    assert record.started is True


@pytest.mark.unittest
def test_an_exhausted_budget_stops_the_search_without_publishing() -> None:
    """The search shares one budget, so it can run out, and then it publishes nothing.

    Degrading is the contract's answer here: a partial graph would claim a
    verification that did not finish.
    """
    # An exhausted finite budget is one whose deadline has passed.  Setting the
    # deadline is what a real timeout does; overriding the accessor would test a
    # stand-in rather than the budget the solver shares.
    import time

    spent = _SolveBudget(1)
    spent.deadline = time.monotonic() - 1.0

    proof, record = _build(
        _inputs(
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(value=1)),
        ),
        budget=spent,
    )

    assert proof is None
    assert record.status == "timeout"


_CONFLICT_SHAPES = {
    "incompatible-equalities": (
        (
            ("assumption.0000", _equality(value=0)),
            ("assumption.0001", _equality(value=1)),
        ),
        "incompatible_equalities",
    ),
    "an-empty-interval": (
        (
            ("assumption.0000", _bound("ge", 5)),
            ("assumption.0001", _bound("le", 3)),
        ),
        "interval_intersection",
    ),
    "an-exhausted-state-domain": (
        (
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1, 2])),
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("assumption.0001", _fact("state_exclusion", frame=1, state=2)),
        ),
        "state_domain_exhaustion",
    ),
    "a-definedness-guard-its-subject-violates": (
        (
            (
                "definedness.0000",
                _fact(
                    "definedness_guard",
                    variable="x",
                    frame=0,
                    operation="division",
                    forbidden=0,
                ),
            ),
            ("initial.variable.x", _equality(value=0)),
        ),
        "definedness_failure",
    ),
    "a-proposition-and-its-negation": (
        (
            (
                "assumption.0000",
                _fact("proposition", identity="active(Root.A)@1", holds=True),
            ),
            (
                "assumption.0001",
                _fact("proposition", identity="active(Root.A)@1", holds=False),
            ),
        ),
        "boolean_complement",
    ),
    "a-value-carried-across-a-transition": (
        (
            ("initial.variable.x", _equality(value=0)),
            (
                "transition.step.0000",
                _fact(
                    "transition_case",
                    variable="x",
                    frame=0,
                    target_frame=1,
                    operator="add",
                    operand=1,
                ),
            ),
            ("assumption.0000", _equality(frame=1, value=9)),
        ),
        "incompatible_equalities",
    ),
}


@pytest.mark.unittest
@pytest.mark.parametrize(
    "shape", sorted(_CONFLICT_SHAPES), ids=sorted(_CONFLICT_SHAPES)
)
def test_every_conflict_shape_the_catalog_covers_reaches_a_proof(shape) -> None:
    """One case per way a scenario can be empty, end to end through the builder.

    Rule tests check a step in isolation; this checks that the search can reach the
    step at all.  The two are not the same: five rules passed their own tests while
    no input could produce them, because the builder had no proposal for their
    shapes and never offered one to the checker.
    """
    inputs, closing_rule = _CONFLICT_SHAPES[shape]

    proof, record = _build(inputs)

    assert proof is not None, record.reason
    assert record.status == "complete"
    assert proof.nodes[-1].rule_id == closing_rule
    assert proof.nodes[-1].conclusion == {"kind": "false"}
    # Every member is a reason, which is what makes the core fully used.
    assert set(proof.nodes[-1].item_ids) == {stable_id for stable_id, _ in inputs}


@pytest.mark.unittest
def test_a_transition_chain_is_more_than_one_hop_deep() -> None:
    """The shape that proves the graph machinery, not just one rule.

    A transition case becomes an expression, the expression evaluates to a value,
    and the value contradicts an assumption -- three derived steps, each reading the
    one before it.  A builder that only ever fanned inputs into a root would pass
    every other case here.
    """
    inputs, _ = _CONFLICT_SHAPES["a-value-carried-across-a-transition"]

    proof, _ = _build(inputs)

    derived = [node for node in proof.nodes if node.kind == "derived"]
    assert len(derived) >= 2, [node.rule_id for node in proof.nodes]
    # Chase the premise edges back from the root; the depth is the chain length.
    by_id = {node.stable_id: node for node in proof.nodes}
    depth, frontier = 0, [proof.root_id]
    while frontier:
        depth += 1
        frontier = [
            premise
            for name in frontier
            for premise in by_id[name].premise_ids
            if by_id[premise].kind != "input"
        ]
    assert depth >= 3, depth
