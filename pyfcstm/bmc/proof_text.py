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

from typing import Any, List, Mapping, Tuple

from .explanation import BmcConflictProof, BmcReasoningStep

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


def _state_phrase(states) -> str:
    """Return a reader-facing list of state codes."""
    return ", ".join(str(state) for state in states)


def _fact_sentence(fact: Mapping[str, Any]) -> str:
    """Return the sentence stating one fact in the model's vocabulary.

    :param fact: The fact a node concludes.
    :type fact: Mapping[str, object]
    :return: One sentence.
    :rtype: str

    Example::

        >>> _fact_sentence({"kind": "state_domain", "frame": 1, "states": [1, 2]})
        'At frame 1, the model allows the states 1, 2.'
    """
    kind = fact.get("kind")
    if kind == "variable_equality":
        return "At frame %s, %s must equal %s." % (
            fact.get("frame"),
            fact.get("variable"),
            fact.get("value"),
        )
    if kind == "variable_bound":
        phrase = {
            "ge": "at least",
            "gt": "greater than",
            "le": "at most",
            "lt": "less than",
        }.get(fact.get("operator"), "related to")
        return "At frame %s, %s must be %s %s." % (
            fact.get("frame"),
            fact.get("variable"),
            phrase,
            fact.get("value"),
        )
    if kind == "state_domain":
        return "At frame %s, the model allows the states %s." % (
            fact.get("frame"),
            _state_phrase(fact.get("states") or ()),
        )
    if kind == "state_exclusion":
        return "At frame %s, state %s is ruled out." % (
            fact.get("frame"),
            fact.get("state"),
        )
    if kind == "definedness_guard":
        return "At frame %s, the %s requires %s to differ from %s." % (
            fact.get("frame"),
            fact.get("operation"),
            fact.get("variable"),
            fact.get("forbidden"),
        )
    if kind == "proposition":
        return "At the frame it names, %s is required to %s." % (
            fact.get("identity"),
            "hold" if fact.get("holds") else "not hold",
        )
    if kind == "transition_case":
        return "Between frame %s and frame %s, the transition changes %s by %s." % (
            fact.get("frame"),
            fact.get("target_frame"),
            fact.get("variable"),
            fact.get("operand"),
        )
    if kind == "arithmetic_expression":
        return "Between frame %s and frame %s, %s changes by %s." % (
            fact.get("frame"),
            fact.get("target_frame"),
            fact.get("variable"),
            fact.get("operand"),
        )
    return "A model or query requirement constrains this scenario."


def _clause(fact: Mapping[str, Any]) -> str:
    """Return the fact as a clause that can follow "therefore".

    The same content as :func:`_fact_sentence` without the leading frame phrase, so
    a derived step reads as one sentence rather than two glued together.
    """
    kind = fact.get("kind")
    if kind == "variable_equality":
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
    sentence = _fact_sentence(fact)
    return sentence[0].lower() + sentence[1:].rstrip(".")


def _derived_sentence(rule_id: str, fact: Mapping[str, Any]) -> str:
    """Return the sentence for a step that produced a new fact.

    The contract's three-part shape puts the rule in the middle: the facts above, the
    rule that used them, then what it gives.  ``therefore`` is what marks the join,
    and the fact arrives as a clause so the whole reads as one sentence.
    """
    opening = _RULE_OPENINGS.get(rule_id, "The model therefore requires")
    return "%s %s." % (opening, _clause(fact))


def _closing_sentence(rule_id: str) -> str:
    """Return the sentence that closes the chain.

    It states the scenario is empty and that the property was therefore not
    evaluated -- never that a property failed, which is a different finding entirely.
    """
    reason = _CLOSING_PHRASES.get(rule_id, "these requirements cannot all hold")
    return (
        "Therefore %s. No execution satisfies these initialization and query "
        "requirements, and the property was not evaluated." % reason
    )


def _frame_of(node) -> Any:
    """Return the frame a node's conclusion speaks about, for reader ordering.

    A fact with no frame sorts first: it is about the scenario rather than a point
    in it, so it belongs before the walk through the frames begins.
    """
    frame = node.conclusion.get("frame")
    return frame if isinstance(frame, int) else -1


def linearize_proof(proof: BmcConflictProof) -> Tuple[BmcReasoningStep, ...]:
    """Read a proof graph as an ordered chain of reasoning steps.

    One step per node, in the graph's own canonical order, each naming the node it
    reads.  The result is what a narrative publishes at proof depth, so a consumer
    can move between a sentence and the checked step behind it in either direction.

    :param proof: The verified proof to read.
    :type proof: BmcConflictProof
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
            (0, _frame_of(pair[1]), pair[0])
            if pair[1].kind == "input"
            else (1, 0, pair[0])
        ),
    )
    steps: List[BmcReasoningStep] = []
    for _, node in ordered:
        if node.kind == "input":
            kind, text = "fact", _fact_sentence(node.conclusion)
        elif node.kind == "derived":
            kind, text = "derivation", _derived_sentence(node.rule_id, node.conclusion)
        else:
            kind, text = "conflict", _closing_sentence(node.rule_id)
        steps.append(BmcReasoningStep(kind, node.item_ids, (node.stable_id,), text))
    return tuple(steps)
