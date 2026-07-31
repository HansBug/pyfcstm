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
from typing import Any, Callable, Dict, Mapping, Tuple

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


def _slot(fact: Mapping[str, Any]) -> Tuple[Any, Any, bool]:
    """Return the variable and frame a fact is about.

    Every side condition below starts here.  Two facts on different slots say
    nothing about each other, so comparing their values would manufacture a
    contradiction between unrelated requirements.

    :param fact: A domain fact.
    :type fact: Mapping[str, object]
    :return: The subject, the frame, and whether the subject is a frame's state
        slot rather than a declared variable.  The flag is part of the identity:
        a model may declare a variable spelled like the slot, and the two are
        different things at the same frame.
    :rtype: Tuple[object, object, bool]

    Example::

        >>> _slot({"kind": "variable_equality", "variable": "x", "frame": 0})
        ('x', 0, False)
    """
    return fact.get("variable"), fact.get("frame"), bool(fact.get("state_slot"))


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
    variable, frame, _ = slots.pop()
    return variable is not None and frame is not None


def _carry_subject(
    conclusion: Dict[str, Any], source: Mapping[str, Any]
) -> Dict[str, Any]:
    """Carry the subject's kind from the fact a conclusion is derived from.

    A frame's state and a variable can wear the same name -- a model may declare one
    spelled like the slot -- so the subject's kind rides on a flag.  A variable omits
    the field rather than writing ``False``, so there is one spelling of "not a
    state slot" for every consumer instead of two.

    :param conclusion: The conclusion being built.
    :type conclusion: Dict[str, object]
    :param source: The fact whose subject it inherits.
    :type source: Mapping[str, object]
    :return: The same mapping, with the flag set when the source carries it.
    :rtype: Dict[str, object]

    Example::

        >>> _carry_subject({"variable": "x"}, {"state_slot": True})
        {'variable': 'x', 'state_slot': True}
    """
    if source.get("state_slot"):
        conclusion["state_slot"] = True
    return conclusion


def _exactly(conclusion: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    """Report whether a conclusion is exactly what its premises determine.

    Comparing the whole mapping rather than a list of keys is the point.  Each rule
    used to name the fields it cared about, and a field left off that list was a
    field the checker did not recompute: first ``state_slot``, which let a
    derivation change what it was talking about, then ``operand_variable``, which
    let one invent a symbol its premises never mentioned.  Both were the same
    defect, and patching the list twice would have invited a third.

    A conclusion is what the premises say it is, no more and no less, so anything
    extra is as wrong as anything missing.

    :param conclusion: What the application claims.
    :type conclusion: Mapping[str, object]
    :param expected: What the premises determine.
    :type expected: Mapping[str, object]
    :return: ``True`` when the two are the same mapping.
    :rtype: bool

    Example::

        >>> _exactly({"kind": "false"}, {"kind": "false"})
        True
        >>> _exactly({"kind": "false", "extra": 1}, {"kind": "false"})
        False
        >>> _exactly({"state_slot": 1}, {"state_slot": True})
        False
    """
    left, right = dict(conclusion), dict(expected)
    if left.keys() != right.keys():
        return False
    for key, value in left.items():
        other = right[key]
        # ``1 == True`` in Python, so plain equality would accept ``"state_slot": 1``
        # where the published schema pins ``true``.  The two gates have to agree on
        # what the field holds, and the looser one is the one that decides.
        if isinstance(value, bool) != isinstance(other, bool):
            return False
        if value != other:
            return False
    return True


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
    if _slot(value_fact) != _slot(expression):
        return False
    if expression.get("operand_variable"):
        # An operand still standing as a symbol has no value to evaluate; the
        # substitution step has to run first.  Reaching ``_evaluate`` with it would
        # add ``None`` to a number and raise out of a predicate that answers yes or
        # no.
        return False
    result = _evaluate(
        expression.get("operator"), value_fact.get("value"), expression.get("operand")
    )
    if result is None:
        return False
    expected = _carry_subject(
        {
            "kind": "variable_equality",
            "variable": expression.get("variable"),
            "frame": expression.get("target_frame"),
            "value": result,
        },
        expression,
    )
    return _exactly(application.conclusion, expected)


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
    if not _same_slot((guard, value)):
        # The same predicate the other rules use.  Accepting a half-named slot here
        # while ``incompatible_equalities`` refuses one is two gates answering the
        # same question differently, and the looser one decides.
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
    if _slot(value) != _slot(case):
        return False
    expected = _carry_subject(
        {
            "kind": "arithmetic_expression",
            "variable": case.get("variable"),
            "frame": case.get("frame"),
            "target_frame": case.get("target_frame"),
            "operator": case.get("operator"),
            "operand": case.get("operand"),
        },
        case,
    )
    return _exactly(application.conclusion, expected)


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
    if value.get("state_slot"):
        # An operand is a variable the expression reads.  A frame's state is not a
        # value an expression can be written over, so a slot standing in for one is
        # a substitution into a statement the model never made.
        return False
    expected = _carry_subject(
        {
            "kind": "arithmetic_expression",
            "variable": expression.get("variable"),
            "frame": expression.get("frame"),
            "target_frame": expression.get("target_frame"),
            "operator": expression.get("operator"),
            "operand": value.get("value"),
        },
        expression,
    )
    return _exactly(application.conclusion, expected)


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
