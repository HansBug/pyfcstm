"""
Tests for the verifiable domain proof DAG types and their published gates.

The proof tier is delivered in stages.  This module covers the first one: the
frozen shapes from the contract's Public API section, the canonical mappings they
serialize to, and the semantic gate that the structural schema cannot express.
The builder itself lands later, so nothing here constructs a proof from a query --
these are the shapes a builder will have to produce and a consumer may rely on.

The module contains:
* Transcription guards over the frozen proof vocabularies and field orders
* Canonical-mapping tests for :class:`pyfcstm.bmc.explanation.BmcProofNode` and
  :class:`pyfcstm.bmc.explanation.BmcConflictProof`
* Graph and cross-array invariant tests for the published constructor

.. note::
   The vocabularies below are transcribed from the contract by hand on purpose.
   Deriving them from the implementation would make the guard agree with whatever
   the code happens to say, which is the failure it exists to catch.
"""

import pytest

from pyfcstm.bmc.explanation import (
    BmcConflictProof,
    BmcConstraintRef,
    BmcCoreItem,
    BmcProofNode,
)
from pyfcstm.bmc.provenance import BmcSourceRef


def _ref(stable_id: str, category: str = "assumption.frame") -> BmcConstraintRef:
    """A published constraint reference with the fields a core item needs."""
    return BmcConstraintRef(
        stable_id,
        "assumptions",
        category,
        BmcSourceRef("fbmcq", "q.fbmcq", None),
        stable_id,
        frames=(0,),
        refs={"frame": 0},
    )


def _item(stable_id: str, variable: str = "x", value: int = 0) -> BmcCoreItem:
    """A published core member carrying a whole comparison fact."""
    return BmcCoreItem(
        _ref(stable_id),
        "assumption",
        None,
        False,
        {
            "kind": "variable_comparison",
            "variable": variable,
            "frame": 0,
            "operator": "eq",
            "value": value,
        },
        "At frame 0, the query requires %s to equal %s." % (variable, value),
        True,
    )


def _input_node(stable_id: str, item_id: str, value: int) -> BmcProofNode:
    """An input node bound to one core member, as ``source_fact`` produces."""
    return BmcProofNode(
        stable_id,
        "input",
        "source_fact",
        (),
        {"kind": "variable_equality", "variable": "x", "frame": 0, "value": value},
        (item_id,),
        "The query requires x to equal %s initially." % value,
        "core_binding",
    )


def _false_node(stable_id: str, premises, item_ids) -> BmcProofNode:
    """The contradiction node every complete proof ends on."""
    return BmcProofNode(
        stable_id,
        "contradiction",
        "incompatible_equalities",
        tuple(premises),
        {"kind": "false"},
        tuple(item_ids),
        "The initial value of x cannot be both 0 and 1.",
        "rule_checker",
    )


def _proof(nodes, root_id: str = "proof.false") -> BmcConflictProof:
    """A published proof over the given nodes."""
    return BmcConflictProof(
        "assumptions_component",
        root_id,
        tuple(nodes),
        "subset_minimal",
        "dependency_pruned",
        "verified",
    )


@pytest.mark.unittest
def test_the_proof_vocabularies_are_transcribed_from_the_contract() -> None:
    """The frozen literals are copied, not derived from what the code says.

    Rewriting a frozen vocabulary from understanding rather than from the text has
    already produced a self-consistent, fully green mistake once in this series.
    The values below are transcribed by hand, so a rename or a reordering in the
    implementation fails here rather than passing quietly.
    """
    from pyfcstm.bmc import explanation as module

    assert module._PROOF_NODE_KINDS == ("input", "derived", "contradiction")
    assert module._PROOF_RULE_IDS == (
        "source_fact",
        "transition_assignment",
        "equality_substitution",
        "arithmetic_evaluation",
        "interval_intersection",
        "state_domain_exhaustion",
        "definedness_failure",
        "incompatible_equalities",
        "boolean_complement",
    )
    assert module._PROOF_VERIFICATION_METHODS == (
        "core_binding",
        "rule_checker",
        "solver_entailment",
    )
    assert module._PROOF_INPUT_MINIMALITIES == ("subset_minimal",)
    assert module._PROOF_GRAPH_MINIMALITIES == ("dependency_pruned",)
    assert module._PROOF_VERIFICATION_STATUSES == ("verified",)


@pytest.mark.unittest
def test_the_proof_dataclasses_carry_the_frozen_field_order() -> None:
    """Field order is part of the published shape, so it is pinned as written.

    Canonical mappings are emitted in field order, so a reordering here would move
    keys in every published payload without any test noticing.
    """
    import dataclasses

    assert [field.name for field in dataclasses.fields(BmcProofNode)] == [
        "stable_id",
        "kind",
        "rule_id",
        "premise_ids",
        "conclusion",
        "item_ids",
        "human_text",
        "verification_method",
    ]
    assert [field.name for field in dataclasses.fields(BmcConflictProof)] == [
        "scope",
        "root_id",
        "nodes",
        "input_minimality",
        "graph_minimality",
        "verification_status",
    ]


@pytest.mark.unittest
@pytest.mark.parametrize(
    "field, value",
    [
        ("kind", "premise"),
        ("rule_id", "modus_ponens"),
        ("verification_method", "trust"),
    ],
    ids=["an-unknown-node-kind", "an-unknown-rule", "an-unknown-verification-method"],
)
def test_a_node_outside_the_frozen_vocabulary_is_refused(field, value) -> None:
    """The vocabularies are closed, so anything outside them cannot be published.

    ``trust`` is the one worth naming: the contract forbids hole, trust and opaque
    solver steps in a public complete proof, and the refusal has to happen where
    the value enters rather than at presentation time.
    """
    kwargs = {
        "stable_id": "proof.input.0000",
        "kind": "input",
        "rule_id": "source_fact",
        "premise_ids": (),
        "conclusion": {"kind": "variable_equality"},
        "item_ids": ("assumption.0000",),
        "human_text": "text",
        "verification_method": "core_binding",
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        BmcProofNode(**kwargs)


@pytest.mark.unittest
def test_a_node_publishes_its_canonical_mapping_in_field_order() -> None:
    """A consumer reads the mapping, so its keys and order are the contract."""
    node = _input_node("proof.input.0000", "assumption.0000", 0)

    canonical = node.to_canonical()

    assert list(canonical) == [
        "stable_id",
        "kind",
        "rule_id",
        "premise_ids",
        "conclusion",
        "item_ids",
        "human_text",
        "verification_method",
    ]
    assert canonical["premise_ids"] == []
    assert canonical["conclusion"] == {
        "kind": "variable_equality",
        "variable": "x",
        "frame": 0,
        "value": 0,
    }


@pytest.mark.unittest
def test_a_proof_publishes_its_canonical_mapping_in_field_order() -> None:
    """The proof mapping nests its nodes rather than restating their ids."""
    proof = _proof(
        (
            _input_node("proof.input.0000", "assumption.0000", 0),
            _input_node("proof.input.0001", "assumption.0001", 1),
            _false_node(
                "proof.false",
                ("proof.input.0000", "proof.input.0001"),
                ("assumption.0000", "assumption.0001"),
            ),
        )
    )

    canonical = proof.to_canonical()

    assert list(canonical) == [
        "scope",
        "root_id",
        "nodes",
        "input_minimality",
        "graph_minimality",
        "verification_status",
    ]
    assert [node["stable_id"] for node in canonical["nodes"]] == [
        "proof.input.0000",
        "proof.input.0001",
        "proof.false",
    ]


@pytest.mark.unittest
def test_a_proof_needs_nodes_to_be_a_proof() -> None:
    """An empty graph proves nothing, and its root names a node that is absent."""
    with pytest.raises(ValueError):
        _proof(())


@pytest.mark.unittest
def test_a_premise_must_name_an_earlier_node() -> None:
    """``nodes`` is the canonical topological order, so premises look backwards.

    This is the graph half of the semantic gate: the structural schema can check
    that ``premise_ids`` holds strings, and cannot check that a string names a node
    at all, let alone an earlier one.
    """
    forward = (
        _false_node("proof.false", ("proof.input.0000",), ("assumption.0000",)),
        _input_node("proof.input.0000", "assumption.0000", 0),
    )

    with pytest.raises(ValueError):
        _proof(forward)


@pytest.mark.unittest
def test_a_premise_naming_no_node_is_refused() -> None:
    """The payload the contract names: every field is well typed and the id is not there."""
    with pytest.raises(ValueError):
        _proof(
            (
                _input_node("proof.input.0000", "assumption.0000", 0),
                _false_node("proof.false", ("missing",), ("assumption.0000",)),
            )
        )


@pytest.mark.unittest
def test_two_nodes_cannot_share_a_stable_id() -> None:
    """Ids identify nodes across the payload, so a repeat makes references ambiguous."""
    with pytest.raises(ValueError):
        _proof(
            (
                _input_node("proof.input.0000", "assumption.0000", 0),
                _input_node("proof.input.0000", "assumption.0001", 1),
                _false_node("proof.false", ("proof.input.0000",), ("assumption.0000",)),
            )
        )


@pytest.mark.unittest
def test_the_root_must_name_the_single_contradiction() -> None:
    """A proof closes on one false root, and ``root_id`` has to be it."""
    nodes = (
        _input_node("proof.input.0000", "assumption.0000", 0),
        _false_node("proof.false", ("proof.input.0000",), ("assumption.0000",)),
    )

    with pytest.raises(ValueError):
        _proof(nodes, root_id="proof.input.0000")


@pytest.mark.unittest
def test_every_node_must_reach_the_root() -> None:
    """A node the conclusion does not rest on is a dead step, which pruning removes.

    Reachability is the invariant no structural schema can express, and publishing
    a proof that carries an unused step claims the step took part.
    """
    nodes = (
        _input_node("proof.input.0000", "assumption.0000", 0),
        _input_node("proof.input.0001", "assumption.0001", 1),
        _false_node("proof.false", ("proof.input.0000",), ("assumption.0000",)),
    )

    with pytest.raises(ValueError):
        _proof(nodes)


@pytest.mark.unittest
def test_a_root_conclusion_must_be_false() -> None:
    """The root says no execution exists, which is one fixed conclusion shape."""
    node = BmcProofNode(
        "proof.false",
        "contradiction",
        "incompatible_equalities",
        (),
        {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
        ("assumption.0000",),
        "text",
        "rule_checker",
    )

    with pytest.raises(ValueError):
        _proof((node,))


@pytest.mark.unittest
@pytest.mark.parametrize(
    "mutate, why",
    [
        (
            lambda payload: payload["nodes"][-1].update(premise_ids=["missing"]),
            "a premise naming no node",
        ),
        (
            lambda payload: payload["nodes"].reverse(),
            "premises pointing forwards",
        ),
        (
            lambda payload: payload.update(root_id="proof.input.0000"),
            "a root that is not the false node",
        ),
        (
            lambda payload: payload["nodes"].insert(
                0,
                {
                    "stable_id": "proof.spare",
                    "kind": "input",
                    "rule_id": "source_fact",
                    "premise_ids": [],
                    "conclusion": {"kind": "variable_equality"},
                    "item_ids": ["assumption.9999"],
                    "human_text": "a step nothing uses",
                    "verification_method": "core_binding",
                },
            ),
            "a node that reaches no root",
        ),
    ],
    ids=[
        "a-premise-naming-no-node",
        "premises-pointing-forwards",
        "a-root-that-is-not-the-false-node",
        "a-node-that-reaches-no-root",
    ],
)
def test_the_schema_accepts_graph_shapes_only_the_constructor_can_refuse(
    mutate, why
) -> None:
    """The semantic-gate split, pinned in both directions at once.

    The contract names these as an exception because the published schema is a
    structural gate and these are relations: whether a string names a member,
    whether that member came earlier, and whether a graph is connected.  Asserting
    only that the constructor refuses would leave the other half unstated -- if the
    schema grew a rule that caught one of these, the exception would be stale and
    nothing would say so.
    """
    import json

    from jsonschema import Draft202012Validator

    schema = json.load(
        open("docs/source/reference/bmc_results/bmc_cli.schema.json", encoding="utf-8")
    )
    validator = Draft202012Validator(
        {"$ref": "#/$defs/conflictProof", "$defs": schema["$defs"]}
    )

    payload = _proof(
        (
            _input_node("proof.input.0000", "assumption.0000", 0),
            _false_node("proof.false", ("proof.input.0000",), ("assumption.0000",)),
        )
    ).to_canonical()
    assert list(validator.iter_errors(payload)) == [], "the honest payload must pass"

    mutate(payload)

    assert list(validator.iter_errors(payload)) == [], (
        "the schema is expected to accept %s; if it now refuses it, this shape is "
        "no longer a semantic-gate exception and the contract should say so" % why
    )
    with pytest.raises(ValueError):
        BmcConflictProof(
            payload["scope"],
            payload["root_id"],
            tuple(
                BmcProofNode(
                    node["stable_id"],
                    node["kind"],
                    node["rule_id"],
                    tuple(node["premise_ids"]),
                    node["conclusion"],
                    tuple(node["item_ids"]),
                    node["human_text"],
                    node["verification_method"],
                )
                for node in payload["nodes"]
            ),
            payload["input_minimality"],
            payload["graph_minimality"],
            payload["verification_status"],
        )
