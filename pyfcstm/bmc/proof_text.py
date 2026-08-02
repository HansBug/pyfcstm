"""
The natural-language reading of a proof graph.

The prose is the graph in order, not a second account of it.  Every node becomes one
step, every step names the node it reads, and the order is the graph's own -- so a
reader following the sentences is following the dependencies, and anything the text
claims can be traced to a node that a checker agreed with.

The module contains:
* :func:`linearize_proof` - one reasoning step per proof node, in canonical order

The vocabulary is deliberately narrow.  A reader is owed the terms the model is
written in -- frames, states, variables, transitions, assumptions -- and owes nothing
to the encoding: no ``D_N``, no activation literal, no clause, no source group, no
solver tactic.  A generated rule is described by what it says about the model rather
than by what it is called internally, so "frame 1 may hold two states" rather than a
numbered clause.

.. note::
   The closing sentence reports that no execution exists and that the property was
   therefore not evaluated.  An empty scenario and a violated property are different
   findings, and writing the first as the second reports a result nobody computed.

Example::

    >>> from pyfcstm.bmc.proof import build_domain_proof
    >>> from pyfcstm.bmc.solver import _SolveBudget
    >>> inputs = (
    ...     ("assumption.0000",
    ...      {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0}),
    ...     ("assumption.0001",
    ...      {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 1}),
    ... )
    >>> proof, _ = build_domain_proof("assumptions_component", inputs, _SolveBudget(None))
    >>> linearize_proof(proof)[-1].kind
    'conflict'
"""

from typing import Any, List, Mapping, Optional, Tuple

from .explanation import (
    BmcConflictProof,
    BmcReasoningStep,
    _fact_sentence,
    _state_display,
)

__all__ = ["linearize_proof"]

#: How each rule introduces the fact it produced.
#:
#: Phrased as what the model does rather than what the rule is called: a reader
#: recognizes "the transition therefore" without knowing the catalog.  Each phrase
#: is a sentence opening that the produced fact completes.
_RULE_OPENINGS = {
    "transition_assignment": "The transition therefore means that",
    "arithmetic_evaluation": "Starting from that value, the step therefore leaves",
    "equality_substitution": "Substituting that value, the step therefore reads",
}

#: How each contradiction closes, in the model's own terms.
_CLOSING_PHRASES = {
    "incompatible_equalities": ("one value cannot be two things at once"),
    "interval_intersection": ("no value lies within every bound required here"),
    "state_domain_exhaustion": ("the frame has no state left to be in"),
    "definedness_failure": (
        "the operation cannot stay defined on the value required here"
    ),
    "boolean_complement": ("the same requirement is both demanded and ruled out"),
}


def _clause(fact: Mapping[str, Any], names: Optional[Mapping[int, str]] = None) -> str:
    """Return the fact as a clause that can follow "therefore".

    The same content as :func:`_fact_sentence` without the leading frame phrase, so
    a derived step reads as one sentence rather than two glued together.
    """
    kind = fact.get("kind")
    if kind == "variable_equality":
        if fact.get("state_slot"):
            return "the state at frame %s to be %s" % (
                fact.get("frame"),
                _state_display(fact.get("value"), names),
            )
        return "%s equal to %s at frame %s" % (
            fact.get("variable"),
            fact.get("value"),
            fact.get("frame"),
        )
    if kind == "arithmetic_expression":
        return "%s changed by %s between frame %s and frame %s" % (
            fact.get("variable"),
            fact.get("operand"),
            fact.get("frame"),
            fact.get("target_frame"),
        )
    sentence = _fact_sentence(fact, names)
    return sentence[0].lower() + sentence[1:].rstrip(".")


def _derived_sentence(
    rule_id: str, fact: Mapping[str, Any], names: Optional[Mapping[int, str]] = None
) -> str:
    """Return the sentence for a step that produced a new fact.

    The contract's three-part shape puts the rule in the middle: the facts above, the
    rule that used them, then what it gives.  ``therefore`` is what marks the join,
    and the fact arrives as a clause so the whole reads as one sentence.
    """
    opening = _RULE_OPENINGS.get(rule_id, "The model therefore requires")
    return "%s %s." % (opening, _clause(fact, names))


#: What the closing sentence calls the requirements, by the scope it closed on.
#:
#: Naming a stage the core does not contain tells the reader to go look at a file
#: that had nothing to do with the conflict.  ``two_values`` is the case that
#: showed it: its query carries no ``init`` clause at all, yet the sentence used
#: to say "these initialization and query requirements".
#:
#: Only the scopes a proof currently closes on are listed.  Every initialization
#: conflict tried so far degrades to a formal explanation before a proof is built,
#: so an entry for ``initialization_*`` would describe prose nothing emits, and a
#: test for it would have no public path to drive.  The fallback covers them
#: without naming a stage; the day a proof closes on that side, this table is where
#: the wording goes.
_CLOSING_SUBJECTS = {
    "assumptions_component": "these query requirements",
    "assumptions_domain": "these query requirements",
    "assumptions_prefix": "these initialization and query requirements",
}


def _closing_sentence(rule_id: str, scope: str) -> str:
    """Return the sentence that closes the chain.

    It states the scenario is empty and that the property was therefore not
    evaluated -- never that a property failed, which is a different finding entirely.

    The subject is taken from the scope, because that is what decides which stages
    the core can hold.  A prefix conflict is the one that genuinely spans both: the
    assumptions are consistent among themselves and with the frame domain, and only
    the initialized transition prefix rules them out.

    :param rule_id: The rule the contradiction node applied.
    :type rule_id: str
    :param scope: The published core scope the proof closed on.
    :type scope: str
    :return: The closing sentence.
    :rtype: str
    """
    reason = _CLOSING_PHRASES.get(rule_id, "these requirements cannot all hold")
    subject = _CLOSING_SUBJECTS.get(scope, "these requirements")
    return (
        "Therefore %s. No execution satisfies %s, and the property was not "
        "evaluated." % (reason, subject)
    )


def _frame_of(node) -> Any:
    """Return the frame a node's conclusion speaks about, for reader ordering.

    A fact with no frame sorts first: it is about the scenario rather than a point
    in it, so it belongs before the walk through the frames begins.
    """
    frame = node.conclusion.get("frame")
    return frame if isinstance(frame, int) else -1


def _sets_the_scene(node) -> int:
    """Sort the facts that say what is possible ahead of the ones that narrow it.

    Reading four exclusions before learning which states there were to exclude from
    makes the reader hold the list in their head until the answer arrives.  What the
    model allows at a frame is the scene; what the query rules out at it is the
    narrowing, so the scene is set first.

    :param node: A proof node.
    :type node: pyfcstm.bmc.explanation.BmcProofNode
    :return: ``0`` for a fact that states the possibilities, ``1`` otherwise.
    :rtype: int
    """
    return 0 if node.conclusion.get("kind") == "state_domain" else 1


def linearize_proof(
    proof: BmcConflictProof, state_names: Optional[Mapping[int, str]] = None
) -> Tuple[BmcReasoningStep, ...]:
    """Read a proof graph as an ordered chain of reasoning steps.

    One step per node, in the graph's own canonical order, each naming the node it
    reads.  The result is what a narrative publishes at proof depth, so a consumer
    can move between a sentence and the checked step behind it in either direction.

    Facts carry states as the encoding numbers them, because that is what the rules
    compare.  Passing ``state_names`` makes the prose say what the author wrote
    instead; a state the map does not cover keeps its index rather than dropping out
    of the reading.

    :param proof: The verified proof to read.
    :type proof: BmcConflictProof
    :param state_names: What the model calls each state, keyed by encoded index,
        defaults to ``None``
    :type state_names: Mapping[int, str], optional
    :return: The steps, ending on the contradiction.
    :rtype: Tuple[BmcReasoningStep, ...]

    Example::

        >>> from pyfcstm.bmc.proof import build_domain_proof
        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> inputs = (
        ...     ("assumption.0000",
        ...      {"kind": "variable_bound", "variable": "x", "frame": 0,
        ...       "operator": "ge", "value": 5}),
        ...     ("assumption.0001",
        ...      {"kind": "variable_bound", "variable": "x", "frame": 0,
        ...       "operator": "le", "value": 3}),
        ... )
        >>> proof, _ = build_domain_proof(
        ...     "assumptions_component", inputs, _SolveBudget(None)
        ... )
        >>> len(linearize_proof(proof))
        3
    """
    # Facts are presented by the frame they speak about, then by their position in
    # the graph.  The graph's own order is by core stable id, which is right for the
    # machine and arbitrary for a reader: it can open on a frame-1 assumption before
    # the frame-0 initializer that leads to it.  Derived steps keep their graph
    # position, so the dependency order a derivation needs still holds.
    ordered = sorted(
        enumerate(proof.nodes),
        key=lambda pair: (
            (0, _frame_of(pair[1]), _sets_the_scene(pair[1]), pair[0])
            if pair[1].kind == "input"
            else (1, 0, 0, pair[0])
        ),
    )
    steps: List[BmcReasoningStep] = []
    for _, node in ordered:
        if node.kind == "input":
            kind, text = "fact", _fact_sentence(node.conclusion, state_names)
        elif node.kind == "derived":
            kind, text = (
                "derivation",
                _derived_sentence(node.rule_id, node.conclusion, state_names),
            )
        else:
            kind, text = "conflict", _closing_sentence(node.rule_id, proof.scope)
        steps.append(BmcReasoningStep(kind, node.item_ids, (node.stable_id,), text))
    return tuple(steps)
