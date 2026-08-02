"""
Tests for the natural-language linearization of a proof graph.

The prose is the graph read in order, not a second account of it.  These tests hold
it to that: every node reaches a step and every step names a node, the order follows
the dependencies, and the vocabulary stays inside what a reader of the model already
knows.

The module contains:
* A verbatim transcription of the contract's forbidden-vocabulary list
* Round-trip tests binding proof nodes to reasoning steps in both directions
* Tests that the closing sentence reports an empty scenario, not a violated property

.. note::
   The forbidden list is transcribed from the contract word for word.  Paraphrasing
   it is not a hypothetical failure: an earlier draft of this stage's plan dropped
   seven of the nine terms and invented five near-synonyms, and nothing would have
   caught that except reading the source.
"""

import pytest

from pyfcstm.bmc.proof import build_domain_proof
from pyfcstm.bmc.proof_text import linearize_proof
from pyfcstm.bmc.solver import _SolveBudget

#: Terms the default proof text may not require a reader to understand.
#:
#: Transcribed from the contract's linearization section, which lists them as
#: ``D_N/T_N/I_0/ENV_N``, activation literal, SMT clause, source group, theory lemma
#: and solver tactic.
_FORBIDDEN_TERMS = (
    "D_N",
    "T_N",
    "I_0",
    "ENV_N",
    "activation literal",
    "SMT clause",
    "source group",
    "theory lemma",
    "solver tactic",
)


def _fact(kind: str, **fields) -> dict:
    """A domain fact of one tag."""
    fact = {"kind": kind}
    fact.update(fields)
    return fact


def _equality(variable: str = "x", frame: int = 0, value: int = 0) -> dict:
    """A concrete value for one variable at one frame."""
    return _fact("variable_equality", variable=variable, frame=frame, value=value)


_CHAIN = (
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
)


def _proof_of(inputs=_CHAIN):
    """Build a proof for the given inputs, failing loudly when none exists."""
    proof, record = build_domain_proof("assumptions_prefix", inputs, _SolveBudget(None))
    assert proof is not None, record.reason
    return proof


@pytest.mark.unittest
def test_every_node_reaches_a_step_and_every_step_names_a_node() -> None:
    """The prose and the graph are one artifact, so neither may outrun the other.

    A step citing no node would be a claim the graph does not support; a node no
    step mentions would be reasoning the reader never sees.  Both directions are
    checked because either alone permits the other failure.
    """
    proof = _proof_of()

    steps = linearize_proof(proof)

    cited = {name for step in steps for name in step.proof_node_ids}
    assert cited == {node.stable_id for node in proof.nodes}
    for step in steps:
        assert step.proof_node_ids, step.text


@pytest.mark.unittest
def test_the_order_follows_the_dependencies() -> None:
    """A step may not arrive before the steps it rests on.

    The graph is already in canonical topological order, so this checks that the
    linearization preserves it rather than sorting by anything of its own.
    """
    proof = _proof_of()

    steps = linearize_proof(proof)

    position = {}
    for index, step in enumerate(steps):
        for name in step.proof_node_ids:
            position.setdefault(name, index)
    by_id = {node.stable_id: node for node in proof.nodes}
    for node in proof.nodes:
        for premise in node.premise_ids:
            assert position[premise] <= position[node.stable_id], (
                premise,
                node.stable_id,
            )
    assert by_id[proof.root_id].stable_id in position


@pytest.mark.unittest
def test_the_closing_step_reports_an_empty_scenario() -> None:
    """A scenario with no execution is not a property that was violated.

    The two are different findings and the contract keeps them apart: the property
    was never evaluated, so saying it failed would report a result nobody computed.
    """
    proof = _proof_of()

    closing = linearize_proof(proof)[-1]

    assert closing.kind == "conflict"
    lowered = closing.text.lower()
    assert "no execution" in lowered
    assert "not evaluated" in lowered
    for wrong in ("violat", "counterexample", "fails"):
        assert wrong not in lowered, closing.text


@pytest.mark.unittest
@pytest.mark.parametrize("term", _FORBIDDEN_TERMS, ids=_FORBIDDEN_TERMS)
def test_the_prose_never_requires_an_encoding_term(term) -> None:
    """The reader is owed the model's vocabulary, not the encoding's.

    Parametrized over the transcribed list so a term added to the contract fails
    here until someone widens the gate, rather than passing inside a single
    assertion nobody rereads.
    """
    proof = _proof_of()

    text = " ".join(step.text for step in linearize_proof(proof))

    assert term not in text, text


@pytest.mark.unittest
def test_a_generated_rule_is_described_in_domain_terms() -> None:
    """A frame's legal states are a modelling fact, not a numbered clause.

    The contract's own example is the shape to avoid: "domain clause 17" tells the
    reader nothing they can act on, while naming the states does.
    """
    proof = _proof_of(
        (
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1, 2])),
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("assumption.0001", _fact("state_exclusion", frame=1, state=2)),
        )
    )

    text = " ".join(step.text for step in linearize_proof(proof))

    assert "clause" not in text.lower()
    assert "frame 1" in text
    assert "state" in text.lower()


@pytest.mark.unittest
def test_each_step_says_which_rule_carried_it() -> None:
    """The middle of the contract's three-part shape: what produced the new fact.

    Facts alone read as a list; naming the step that connects them is what makes it
    a chain the reader can follow.
    """
    proof = _proof_of()

    steps = linearize_proof(proof)

    derived = [step for step in steps if step.kind == "derivation"]
    assert derived, [step.kind for step in steps]
    for step in derived:
        assert "therefore" in step.text.lower(), step.text


@pytest.mark.unittest
def test_the_facts_are_read_in_the_order_the_execution_would_reach_them() -> None:
    """A chain read backwards is a list; read forwards it is a story.

    The graph's own order is by core stable id, which is right for the machine and
    arbitrary for a reader: it can put the frame-1 assumption before the frame-0
    initializer that leads to it.  Facts are presented by the frame they speak
    about, so the prose walks the execution the way it would have run, while the
    dependency order the derivations need is preserved on top of it.
    """
    proof = _proof_of()

    steps = linearize_proof(proof)

    facts = [step for step in steps if step.kind == "fact"]
    frames = []
    for step in facts:
        node = next(
            node for node in proof.nodes if node.stable_id in step.proof_node_ids
        )
        frames.append(node.conclusion.get("frame"))
    assert frames == sorted(frames), frames


@pytest.mark.unittest
def test_a_state_is_read_by_the_name_the_model_gives_it() -> None:
    """A state index is the encoding's name for a state, not the model's.

    The reader wrote ``Root.A``; nothing in the model they wrote says ``1``.  This
    module promises the terms the model is written in, so the promise has to reach
    the state family too -- for a while it reached only variables and frames, and
    the state sentences read like the encoding they came from.
    """
    proof = _proof_of(
        (
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1, 2])),
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("assumption.0001", _fact("state_exclusion", frame=1, state=2)),
        )
    )

    text = " ".join(
        step.text
        for step in linearize_proof(proof, state_names={1: "Root.A", 2: "Root.B"})
    )

    assert "Root.A" in text and "Root.B" in text, text
    assert "state 1" not in text and "states 1, 2" not in text, text


@pytest.mark.unittest
def test_a_required_state_is_read_as_a_state_and_not_as_a_number() -> None:
    """A frame's state slot is compared like a variable but read like a state.

    Normalizing a positive requirement into an equality is what lets the rules
    compare it; rendering that equality verbatim would tell the reader their state
    "must equal 2", which names neither the slot nor the state.
    """
    from pyfcstm.bmc.explanation import _STATE_SLOT_SUBJECT

    def slot(value):
        fact = _equality(variable=_STATE_SLOT_SUBJECT, frame=1, value=value)
        # The subject is a label; the flag is what says this is a frame's state
        # rather than a variable a model happened to spell the same way.
        fact["state_slot"] = True
        return fact

    proof = _proof_of((("assumption.0000", slot(1)), ("assumption.0001", slot(2))))

    text = " ".join(
        step.text
        for step in linearize_proof(proof, state_names={1: "Root.A", 2: "Root.B"})
    )

    assert "Root.A" in text and "Root.B" in text, text
    assert "must equal 1" not in text and "must equal 2" not in text, text


@pytest.mark.unittest
def test_without_names_the_reading_still_works() -> None:
    """The names are an improvement on the prose, not a precondition for having any.

    The parameter is optional because a caller holding a graph but no model still
    deserves a readable chain, and because every existing caller passed none.
    """
    proof = _proof_of(
        (
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1, 2])),
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("assumption.0001", _fact("state_exclusion", frame=1, state=2)),
        )
    )

    text = " ".join(step.text for step in linearize_proof(proof))

    assert "state 1 is ruled out" in text, text


@pytest.mark.unittest
def test_a_state_with_no_name_keeps_its_index() -> None:
    """A partial map may not silently drop the states it does not cover.

    Sentinel and generated states exist in the encoding without being anything the
    author wrote, so a map built from the model can be missing entries.  The index
    is a poor name but it is a true one; omitting the state entirely would lose a
    premise from the reader's view of the chain.
    """
    proof = _proof_of(
        (
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1, 2])),
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("assumption.0001", _fact("state_exclusion", frame=1, state=2)),
        )
    )

    text = " ".join(
        step.text for step in linearize_proof(proof, state_names={1: "Root.A"})
    )

    assert "Root.A" in text, text
    assert "2" in text, text


@pytest.mark.unittest
@pytest.mark.parametrize(
    "names",
    [None, {}, {2: "Root.B"}, {1: None}],
    ids=["no-table", "empty-table", "other-state-only", "entry-present-but-null"],
)
def test_the_two_readings_of_one_state_agree(names) -> None:
    """The proof reading and the core items' human text spell one state one way.

    Both are prose about the same state shown to the same reader, so a table that
    resolves differently between them would put two names on one thing.  Four ways
    of not having a usable name are checked together because they are exactly where
    two separately-written resolvers drift: a null entry is present to ``in`` and
    absent to a ``get`` default, so one resolver read it as a name and rendered
    ``None`` while the other fell back to the index.
    """
    from pyfcstm.bmc.explanation import human_text_for_fact

    proof = _proof_of(
        (
            ("assumption.0000", _fact("state_exclusion", frame=1, state=1)),
            ("domain.frame.0001", _fact("state_domain", frame=1, states=[1])),
        )
    )

    reading = " ".join(step.text for step in linearize_proof(proof, state_names=names))
    formal = human_text_for_fact(
        "assumption",
        {"kind": "state_membership", "frame": 1, "state": 1, "excluded": True},
        state_paths=names,
    )

    spelling = formal.split("state ", 1)[1].rstrip(".")
    assert "state %s is ruled out" % spelling in reading, (reading, formal)
