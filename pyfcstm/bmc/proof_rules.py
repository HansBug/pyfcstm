"""
The domain rule catalog and the deterministic checker that agrees with it.

A proof step claims that one named rule takes it from some premises to a
conclusion.  This module holds what each rule reads, what it produces, and the
side condition that decides whether a particular application is sound.  Nothing
here builds a proof: a builder proposes applications and this module answers yes
or no, which keeps proposing and checking separable and makes the checker usable
as an oracle in its own right.

The module contains:
* :class:`RuleApplication` - one proposed step, before it is checked
* :class:`ProofRule` - what a rule reads, produces, and requires
* :data:`PROOF_RULES` - the catalog, keyed by the published rule id
* :func:`check_rule` - the deterministic checker

Two properties are load-bearing throughout.  A rule reads *only* its premises, so
a checker cannot reach for context that a reader of the published proof does not
have.  And every side condition compares the slot a fact is about -- its variable
and its frame -- before it compares values, because facts about different slots
constrain different things and never contradict each other.

.. note::
   Arithmetic is evaluated under the model's semantics rather than Python's.  The
   two disagree on integer division of negative operands, and a proof that reported
   Python's answer would be checking a different program than the one being
   verified.

Example::

    >>> application = RuleApplication(
    ...     "incompatible_equalities",
    ...     (
    ...         {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
    ...         {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 1},
    ...     ),
    ...     {"kind": "false"},
    ... )
    >>> check_rule(application)
    True
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Tuple

__all__ = [
    "PROOF_RULES",
    "ProofRule",
    "RuleApplication",
    "check_rule",
]


@dataclass(frozen=True)
class RuleApplication:
    """One proposed proof step, before anything has agreed with it.

    :param rule_id: The published rule this step claims.
    :type rule_id: str
    :param premises: The facts the step reads, in the order the rule expects.
    :type premises: Tuple[Mapping[str, object], ...]
    :param conclusion: The fact the step claims to establish.
    :type conclusion: Mapping[str, object]

    Example::

        >>> application = RuleApplication("interval_intersection", (), {"kind": "false"})
        >>> application.rule_id
        'interval_intersection'
    """

    rule_id: str
    premises: Tuple[Mapping[str, Any], ...]
    conclusion: Mapping[str, Any]


@dataclass(frozen=True)
class ProofRule:
    """One entry of the catalog: what a rule reads, produces, and requires.

    ``premise_kinds`` and ``conclusion_kind`` are the shape a builder matches
    against when it looks for candidate steps; ``side_condition`` is what decides a
    particular application.  Keeping the two apart means a builder can enumerate
    plausible steps cheaply and pay for the check only on the ones that fit.

    :param rule_id: The published rule id.
    :type rule_id: str
    :param premise_kinds: Fact tags this rule reads, without order or multiplicity.
    :type premise_kinds: Tuple[str, ...]
    :param conclusion_kind: Fact tag this rule produces.
    :type conclusion_kind: str
    :param side_condition: Decides one application; returns ``True`` when sound.
    :type side_condition: Callable[[RuleApplication], bool]

    Example::

        >>> PROOF_RULES["incompatible_equalities"].conclusion_kind
        'false'
    """

    rule_id: str
    premise_kinds: Tuple[str, ...]
    conclusion_kind: str
    side_condition: Callable[[RuleApplication], bool]


def _slot(fact: Mapping[str, Any]) -> Tuple[Any, Any]:
    """Return the variable and frame a fact is about.

    Every side condition below starts here.  Two facts on different slots say
    nothing about each other, so comparing their values would manufacture a
    contradiction between unrelated requirements.

    :param fact: A domain fact.
    :type fact: Mapping[str, object]
    :return: The variable and frame, either of which may be absent.
    :rtype: Tuple[object, object]

    Example::

        >>> _slot({"kind": "variable_equality", "variable": "x", "frame": 0})
        ('x', 0)
    """
    return fact.get("variable"), fact.get("frame")


def _same_slot(facts) -> bool:
    """Report whether every fact is about one variable at one frame.

    :param facts: The facts to compare.
    :type facts: Iterable[Mapping[str, object]]
    :return: ``True`` when they share a slot and that slot is fully named.
    :rtype: bool

    Example::

        >>> _same_slot([{"variable": "x", "frame": 0}, {"variable": "x", "frame": 0}])
        True
    """
    slots = {_slot(fact) for fact in facts}
    if len(slots) != 1:
        return False
    variable, frame = slots.pop()
    return variable is not None and frame is not None


def _kinds(facts) -> Tuple[str, ...]:
    """Return the tags of the given facts, in order."""
    return tuple(fact.get("kind") for fact in facts)


def _incompatible_equalities(application: RuleApplication) -> bool:
    """Two concrete values for one slot cannot both hold.

    The side condition is the inequality of the values *after* the slots agree.
    Both halves matter: equal values are no contradiction, and unequal values on
    different slots are the ordinary case.
    """
    premises = application.premises
    if len(premises) != 2 or _kinds(premises) != (
        "variable_equality",
        "variable_equality",
    ):
        return False
    if not _same_slot(premises):
        return False
    if application.conclusion.get("kind") != "false":
        return False
    return premises[0].get("value") != premises[1].get("value")


def _evaluate(operator: str, left: Any, right: Any):
    """Apply one arithmetic operator under the model's semantics.

    Integer division truncates toward zero, which is what the encoded semantics do
    and what Python's ``//`` does not: ``-7 // 2`` is ``-4`` in Python and ``-3``
    here.  Reporting Python's answer would check a different program.

    :param operator: The operator name carried by the expression fact.
    :type operator: str
    :param left: Left operand.
    :param right: Right operand.
    :return: The value, or ``None`` when the operator is unknown or undefined here.

    Example::

        >>> _evaluate("div", -7, 2)
        -3
    """
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    if operator == "mul":
        return left * right
    if operator == "div":
        if right == 0:
            # Definedness is a separate rule's subject; this one has no value to
            # report, and returning a guess would let a step past that check.
            return None
        quotient = abs(left) // abs(right)
        return -quotient if (left < 0) != (right < 0) else quotient
    return None


def _arithmetic_evaluation(application: RuleApplication) -> bool:
    """A value carried across an expression whose operands are all known.

    This is the rule that produces a new fact rather than a contradiction, so it is
    what makes a multi-step graph possible at all: its conclusion is what a later
    step reads.
    """
    premises = application.premises
    if len(premises) != 2:
        return False
    kinds = _kinds(premises)
    if kinds != ("variable_equality", "arithmetic_expression"):
        return False
    value_fact, expression = premises
    if _slot(value_fact) != (
        expression.get("variable"),
        expression.get("frame"),
    ):
        return False
    conclusion = application.conclusion
    if conclusion.get("kind") != "variable_equality":
        return False
    if conclusion.get("variable") != expression.get("variable"):
        return False
    if conclusion.get("frame") != expression.get("target_frame"):
        return False
    result = _evaluate(
        expression.get("operator"), value_fact.get("value"), expression.get("operand")
    )
    if result is None:
        return False
    return conclusion.get("value") == result


#: Bounds that admit values at or beyond their limit.
_CLOSED_OPERATORS = frozenset({"ge", "le"})

#: Which side of the number line each bound operator constrains.
_LOWER_OPERATORS = frozenset({"ge", "gt"})
_UPPER_OPERATORS = frozenset({"le", "lt"})


def _interval_intersection(application: RuleApplication) -> bool:
    """A lower and an upper bound on one slot that leave no value between them.

    Whether the limits are included decides the answer at the endpoint, and over
    the integers a strict pair one apart is empty as well: ``5 < x < 6`` has
    solutions over the reals and none here.
    """
    premises = application.premises
    if len(premises) != 2 or set(_kinds(premises)) != {"variable_bound"}:
        return False
    if not _same_slot(premises):
        return False
    lower = [item for item in premises if item.get("operator") in _LOWER_OPERATORS]
    upper = [item for item in premises if item.get("operator") in _UPPER_OPERATORS]
    if len(lower) != 1 or len(upper) != 1:
        return False
    low, high = lower[0], upper[0]
    low_value, high_value = low.get("value"), high.get("value")
    if not isinstance(low_value, int) or not isinstance(high_value, int):
        return False
    # Tighten each open bound to the first integer it admits, then the emptiness
    # question is a single comparison and the endpoint cases fall out of it.
    if application.conclusion.get("kind") != "false":
        return False
    least = low_value if low.get("operator") in _CLOSED_OPERATORS else low_value + 1
    greatest = (
        high_value if high.get("operator") in _CLOSED_OPERATORS else high_value - 1
    )
    return least > greatest


def _source_fact(application: RuleApplication) -> bool:
    """An input restating one core member reads no premise at all.

    The equivalence between the fact and its source group is established by the
    binding check rather than here: it needs the encoded expressions, which a rule
    checker deliberately does not see.
    """
    return not application.premises and bool(application.conclusion.get("kind"))


def _state_domain_exhaustion(application: RuleApplication) -> bool:
    """A frame whose every legal state has been ruled out has nowhere to be.

    Coverage is exact in both directions.  A state still standing leaves the frame
    somewhere to go, and an exclusion naming a state the frame could not hold anyway
    contributes nothing -- counting it would close the rule on a frame that still has
    an option.
    """
    premises = application.premises
    if application.conclusion.get("kind") != "false":
        return False
    domains = [item for item in premises if item.get("kind") == "state_domain"]
    exclusions = [item for item in premises if item.get("kind") == "state_exclusion"]
    if len(domains) != 1 or not exclusions:
        return False
    if len(domains) + len(exclusions) != len(premises):
        return False
    legal = domains[0]
    frame = legal.get("frame")
    if frame is None:
        return False
    if any(item.get("frame") != frame for item in exclusions):
        return False
    states = legal.get("states")
    if not isinstance(states, (list, tuple)) or not states:
        return False
    ruled_out = {item.get("state") for item in exclusions}
    return ruled_out == set(states)


def _definedness_failure(application: RuleApplication) -> bool:
    """An operation's domain condition against the value its subject is pinned to.

    The guard names one value it forbids at one slot; the contradiction needs the
    subject pinned to exactly that value at exactly that slot.
    """
    premises = application.premises
    if len(premises) != 2 or application.conclusion.get("kind") != "false":
        return False
    guards = [item for item in premises if item.get("kind") == "definedness_guard"]
    values = [item for item in premises if item.get("kind") == "variable_equality"]
    if len(guards) != 1 or len(values) != 1:
        return False
    guard, value = guards[0], values[0]
    if _slot(guard) != _slot(value) or _slot(guard) == (None, None):
        return False
    if not guard.get("operation"):
        return False
    return value.get("value") == guard.get("forbidden")


def _boolean_complement(application: RuleApplication) -> bool:
    """One proposition asserted and denied.

    Identity is compared whole rather than by parts: it already encodes the subject
    and the frame, so a differing frame is a different proposition and no
    contradiction at all.
    """
    premises = application.premises
    if len(premises) != 2 or application.conclusion.get("kind") != "false":
        return False
    if set(_kinds(premises)) != {"proposition"}:
        return False
    identities = {item.get("identity") for item in premises}
    if len(identities) != 1 or None in identities:
        return False
    return {item.get("holds") for item in premises} == {True, False}


def _transition_assignment(application: RuleApplication) -> bool:
    """A selected transition case relating one frame's value to the next.

    A macro-step advances one frame, so a case spanning two is not one step and the
    value it reads has to be the one on the step's own side.
    """
    premises = application.premises
    if len(premises) != 2:
        return False
    cases = [item for item in premises if item.get("kind") == "transition_case"]
    values = [item for item in premises if item.get("kind") == "variable_equality"]
    if len(cases) != 1 or len(values) != 1:
        return False
    case, value = cases[0], values[0]
    frame, target = case.get("frame"), case.get("target_frame")
    if not isinstance(frame, int) or target != frame + 1:
        return False
    if _slot(value) != (case.get("variable"), frame):
        return False
    conclusion = application.conclusion
    if conclusion.get("kind") != "arithmetic_expression":
        return False
    return all(
        conclusion.get(key) == case.get(key)
        for key in ("variable", "frame", "target_frame", "operator", "operand")
    )


def _equality_substitution(application: RuleApplication) -> bool:
    """An expression's symbolic operand replaced by the value that operand holds.

    The value has to be the operand's own, at the expression's own frame; taking one
    from elsewhere would rewrite the expression into a different statement.
    """
    premises = application.premises
    if len(premises) != 2:
        return False
    kinds = _kinds(premises)
    if kinds != ("variable_equality", "arithmetic_expression"):
        return False
    value, expression = premises
    operand_variable = expression.get("operand_variable")
    if not operand_variable:
        return False
    if value.get("variable") != operand_variable:
        return False
    if value.get("frame") != expression.get("frame"):
        return False
    conclusion = application.conclusion
    if conclusion.get("kind") != "arithmetic_expression":
        return False
    if conclusion.get("operand") != value.get("value"):
        return False
    if conclusion.get("operand_variable") is not None:
        return False
    return all(
        conclusion.get(key) == expression.get(key)
        for key in ("variable", "frame", "target_frame", "operator")
    )


#: The domain rules a proof step may cite, keyed by published rule id.
#:
#: A builder dispatches on this mapping: it matches ``premise_kinds`` to find
#: candidate steps cheaply, then pays for ``side_condition`` only on the ones that
#: fit.  The catalog is closed -- a step naming a rule absent here has no published
#: premise shape, conclusion shape or side condition, so nothing could check it and
#: :func:`check_rule` refuses rather than reporting it unverified.
#:
#: :meta hide-value:
PROOF_RULES = {
    rule.rule_id: rule
    for rule in (
        ProofRule("source_fact", ("",), "any", _source_fact),
        ProofRule(
            "arithmetic_evaluation",
            ("variable_equality", "arithmetic_expression"),
            "variable_equality",
            _arithmetic_evaluation,
        ),
        ProofRule(
            "interval_intersection",
            ("variable_bound", "variable_bound"),
            "false",
            _interval_intersection,
        ),
        ProofRule(
            "incompatible_equalities",
            ("variable_equality", "variable_equality"),
            "false",
            _incompatible_equalities,
        ),
        ProofRule(
            "state_domain_exhaustion",
            ("state_domain", "state_exclusion"),
            "false",
            _state_domain_exhaustion,
        ),
        ProofRule(
            "definedness_failure",
            ("definedness_guard", "variable_equality"),
            "false",
            _definedness_failure,
        ),
        ProofRule(
            "boolean_complement",
            ("proposition", "proposition"),
            "false",
            _boolean_complement,
        ),
        ProofRule(
            "transition_assignment",
            ("transition_case", "variable_equality"),
            "arithmetic_expression",
            _transition_assignment,
        ),
        ProofRule(
            "equality_substitution",
            ("variable_equality", "arithmetic_expression"),
            "arithmetic_expression",
            _equality_substitution,
        ),
    )
}


def check_rule(application: RuleApplication) -> bool:
    """Report whether one proposed step is a sound application of its rule.

    :param application: The step to check.
    :type application: RuleApplication
    :return: ``True`` when the rule licenses this conclusion from these premises.
    :rtype: bool
    :raises KeyError: If the step names a rule the catalog does not implement.  An
        unknown rule cannot be checked, and a proof carries no unchecked step, so
        this is refused rather than reported as unverified.

    Example::

        >>> check_rule(RuleApplication(
        ...     "interval_intersection",
        ...     (
        ...         {"kind": "variable_bound", "variable": "x", "frame": 0,
        ...          "operator": "ge", "value": 5},
        ...         {"kind": "variable_bound", "variable": "x", "frame": 0,
        ...          "operator": "le", "value": 3},
        ...     ),
        ...     {"kind": "false"},
        ... ))
        True
    """
    rule = PROOF_RULES[application.rule_id]
    return bool(rule.side_condition(application))
