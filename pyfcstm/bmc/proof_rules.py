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
   Arithmetic is evaluated under the encoder's semantics, which is what the proof is
   about, and that holds for every operator rather than for division alone.  Reals are
   computed exactly and published only when a decimal represents them; a quotient whose
   operands do not settle whether the variable is an integer or a real is declined
   rather than guessed.

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
from fractions import Fraction
from typing import Any, Callable, Dict, Mapping, Tuple

__all__ = [
    "PROOF_RULES",
    "UNREACHABLE_RULE_IDS",
    "reachable_rule_ids",
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


def _transformed(source: Mapping[str, Any], **changes: Any) -> Dict[str, Any]:
    """Return the source fact with only the named fields changed.

    Building an expected conclusion by listing the fields to carry is what let three
    rounds of the same defect through: a field the list forgot was a field both the
    proposer and the checker dropped, so comparing them agreed and the fact quietly
    lost part of itself.  A rule that carries its premise forward says what it
    *changes* instead, and everything it does not mention comes along.

    A field is removed by passing ``None`` for it, which a rule does deliberately --
    substitution drops the operand's name because it has just replaced it.

    :param source: The fact being carried forward.
    :type source: Mapping[str, object]
    :param changes: Fields to set, or to drop when the value is ``None``.
    :type changes: object
    :return: The transformed fact.
    :rtype: Dict[str, object]

    Example::

        >>> _transformed({"kind": "a", "x": 1}, kind="b")
        {'kind': 'b', 'x': 1}
        >>> _transformed({"kind": "a", "x": 1}, x=None)
        {'kind': 'a'}
    """
    result = dict(source)
    for key, value in changes.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result


def _only(fact: Mapping[str, Any], allowed) -> bool:
    """Report whether a fact carries nothing outside the fields a rule understands.

    A rule that consumes a fact into a different shape cannot carry unknown fields
    forward, so it has to refuse them rather than drop them silently.  Otherwise a
    field added to the vocabulary later would disappear at exactly the step that
    changes what the fact is about.

    :param fact: The fact to inspect.
    :type fact: Mapping[str, object]
    :param allowed: The fields this rule knows how to consume.
    :type allowed: Iterable[str]
    :return: ``True`` when the fact carries no others.
    :rtype: bool

    Example::

        >>> _only({"kind": "a", "x": 1}, ("kind", "x"))
        True
        >>> _only({"kind": "a", "surprise": 1}, ("kind", "x"))
        False
    """
    return set(fact) <= set(allowed)


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


#: The operators whose answer is exact in Z3, keyed by the published operator name.
#:
#: Written as functions so the real and integer paths differ only in what they are
#: handed -- two ``Fraction`` values or two ``int`` values -- rather than in a second
#: copy of the operator table.
_EXACT_OPERATORS = {
    "add": lambda left, right: left + right,
    "sub": lambda left, right: left - right,
    "mul": lambda left, right: left * right,
}


def _publishable(exact: Fraction):
    """Return an exact value as a published number, or ``None`` when it is not one.

    A published fact carries a JSON number, which is a decimal.  Most rationals have no
    finite decimal form, and reporting the nearest one would put a value in the proof
    that the encoding does not hold -- so a value is published only when its decimal
    form reads back as the same rational.

    The test is deliberately about the decimal text rather than about the float: a
    binary fraction that a float represents exactly can still have a shortest ``repr``
    shorter than its exact expansion, and this refuses those too.  It is the stricter
    of the two readings, and the safe one, because refusing costs a step while
    publishing a number the encoding does not hold costs the proof its meaning.

    :param exact: The exact value the encoder holds.
    :type exact: fractions.Fraction
    :return: The value as a float, or ``None`` when no exact decimal represents it.

    Example::

        >>> _publishable(Fraction(3, 10))
        0.3
        >>> _publishable(Fraction(1, 3)) is None
        True
    """
    try:
        published = float(exact)
    except OverflowError:
        # A rational larger than every float.  The query language accepts ``1e308``
        # and a model may divide by ``1e-308``, so this is reachable input rather
        # than a hypothetical, and raising would put an exception into a search whose
        # only failure channel is ``None``.
        return None
    if Fraction(repr(published)) != exact:
        return None
    return published


def _evaluate(operator: str, left: Any, right: Any):
    """Apply one arithmetic operator under the model's semantics.

    The encoder is the reference, because it is what the reference says a proof is
    about, and it was for a long time simply not asked.  Division truncated toward
    zero on the stated grounds that truncation is "what the encoded semantics do";
    the other three operators used Python's operators on whatever the fact carried.
    Neither matches.  Z3 adds, subtracts and multiplies reals exactly, and divides
    two integers Euclidean-style and two reals exactly, so ``0.1 + 0.2`` is ``3/10``
    where a double reaches ``0.30000000000000004``, and ``-7 / 2`` is ``-4`` where
    truncation reaches ``-3``.

    Reals therefore go through ``Fraction`` and are published only when their decimal
    form reads back as the same rational; the alternative is a step stating a value
    the encoding does not hold, which is what the published proof used to do under
    ``verification_status`` ``verified``.  Two integers add, subtract and multiply
    exactly in Python already, so those need no detour.

    Division with two integer operands is the one case with no answer here.  A
    ``float`` variable states an integral value as an integer -- a query asking
    ``var("x") == -7`` about a real variable produces exactly that -- so the operands
    do not say which sort is behind them, and the two readings differ.  Where they
    agree the shared answer is published; where they do not, the step is declined
    rather than guessed, and the explanation stays at formal depth.

    :param operator: The operator name carried by the expression fact.
    :type operator: str
    :param left: Left operand.
    :param right: Right operand.
    :return: The value, or ``None`` when the operator is unknown, undefined here,
        exact but not representable as a published number, or a quotient whose sort
        the operands do not settle.

    Example::

        >>> _evaluate("add", 0.1, 0.2)
        0.3
        >>> _evaluate("div", 7.5, 2)
        3.75
        >>> _evaluate("div", 1.0, 3) is None
        True
        >>> _evaluate("div", -7, 2) is None
        True
        >>> _evaluate("div", -8, 2)
        -4
    """
    real = isinstance(left, float) or isinstance(right, float)
    if operator in _EXACT_OPERATORS:
        if not real:
            # Two integers add, subtract and multiply exactly in Python and in Z3
            # alike, so there is nothing to reconcile.
            return _EXACT_OPERATORS[operator](left, right)
        return _publishable(
            _EXACT_OPERATORS[operator](Fraction(str(left)), Fraction(str(right)))
        )
    if operator == "div":
        if right == 0:
            # Definedness is a separate rule's subject; this one has no value to
            # report, and returning a guess would let a step past that check.
            return None
        exact = _exact_quotient(left, right)
        if real:
            return exact
        # Two integer operands do not say whether the variable they describe is one.
        # A ``float`` variable publishes an integral value as an integer -- a query
        # asking ``var("x") == -7`` about a real variable produces exactly that -- so
        # the sort is not recoverable here, and the two semantics part ways: Z3
        # divides two integers Euclidean-style and two reals exactly.  Where they
        # agree the answer is the same either way and can be published; where they do
        # not, publishing one would be a guess about a declaration this function
        # cannot see, so the rule declines and the explanation stays at formal depth.
        euclidean = left // right if right > 0 else -(left // -right)
        return euclidean if exact == euclidean else None
    return None


def _exact_quotient(left: Any, right: Any):
    """Return a real quotient as a published number, or ``None`` when it is not one.

    Z3 divides reals exactly, so the quotient is a rational.  A published fact carries
    a JSON number, which is a decimal, and most rationals have no finite decimal form.
    Reporting the nearest one would put a value in the proof that the encoding does
    not hold -- so the quotient is computed exactly and published only when its
    decimal form reads back as the same rational.

    :param left: Numerator, as published.
    :param right: Denominator, as published.
    :return: The quotient as a float, or ``None`` when no exact decimal represents it.

    Example::

        >>> _exact_quotient(7.5, 2)
        3.75
        >>> _exact_quotient(1.0, 3) is None
        True
    """
    try:
        return _publishable(Fraction(str(left)) / Fraction(str(right)))
    except (ValueError, ZeroDivisionError):
        # ValueError: an operand whose text is not a number, which a fact should not
        # carry and this refuses rather than guesses at.  ZeroDivisionError: a zero
        # denominator the caller's own check did not see, such as ``0.0``.  A quotient
        # too large for a float is refused inside ``_publishable``, which is where
        # every "no published number represents this" answer now lives.
        return None


def _carried_value(value_fact: Mapping[str, Any], expression: Mapping[str, Any]):
    """Return the value an expression carries, or ``None`` when it carries none yet.

    Two sides ask this question -- the rule checker below, and the proof search's
    proposal side in :mod:`pyfcstm.bmc.proof` -- and they have to ask it the same
    way.  They did not.  The checker refused an operand still standing as a symbol;
    the proposal handed one straight to :func:`_evaluate`, which added ``None`` to a
    number and raised out of a search whose only failure channel is ``None``.  One
    function is what makes the two agree by construction rather than by review.

    :param value_fact: The equality supplying the left operand's value.
    :type value_fact: Mapping[str, Any]
    :param expression: The arithmetic expression fact to evaluate.
    :type expression: Mapping[str, Any]
    :return: The value, or ``None`` when no step can produce one here.

    Example::

        >>> _carried_value({"value": 1}, {"operator": "add", "operand": 2})
        3
        >>> _carried_value(
        ...     {"value": 1}, {"operator": "add", "operand_variable": "y"}
        ... ) is None
        True
    """
    if expression.get("operand_variable"):
        # An operand still standing as a symbol has no value to evaluate; the
        # substitution step has to run first, and it is the rule that supplies one.
        return None
    return _evaluate(
        expression.get("operator"), value_fact.get("value"), expression.get("operand")
    )


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
    result = _carried_value(value_fact, expression)
    if result is None:
        return False
    if not _only(expression, _EVALUABLE_EXPRESSION_FIELDS):
        # This rule consumes the expression into a different shape, so it cannot
        # carry a field forward the way the two rules above do.  A field it does not
        # recognize is refused rather than dropped: dropping one silently is what
        # this catalog spent three rounds doing.
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


#: What an expression may say when its value is read off.
#:
#: Everything here is consumed into the resulting equality.  A field outside the set
#: means the expression says something this rule does not know how to carry, so it
#: declines rather than quietly leaving it behind.
_EVALUABLE_EXPRESSION_FIELDS = frozenset(
    {"kind", "variable", "frame", "target_frame", "operator", "operand", "state_slot"}
)

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


def _case_condition_entailment(application: RuleApplication) -> bool:
    """A case whose condition the solver discharged, and nothing else changed.

    This is the one rule in the catalog whose side condition a predicate cannot
    settle.  A case's assignment holds *where the case applies*, so discharging the
    condition means showing the core members entail it -- a question about
    constraints the checker never sees.  The split is therefore deliberate: this
    predicate settles the part that is syntax, and the solver settles the
    entailment, which is why a node carrying this rule records
    ``solver_entailment`` rather than ``rule_checker``.

    Refusing an already-unconditional premise is not pedantry.  Such a step would
    conclude what its own premise says, and the dependency pruning that keeps the
    graph honest cannot tell that apart from a step that carried weight.

    :param application: The step to check.
    :type application: RuleApplication
    :return: ``True`` when the conclusion is the premise with its condition
        emptied and every other field untouched.
    :rtype: bool
    """
    premises = application.premises
    if len(premises) != 1:
        return False
    case = premises[0]
    if case.get("kind") != "transition_case":
        return False
    condition = case.get("condition")
    if not isinstance(condition, tuple) or not condition:
        return False
    # The key goes, not just its contents.  ``_only`` reads keys, so an empty tuple
    # left behind is still a field the evaluation rule does not recognize -- and it
    # refuses an unrecognized field rather than dropping it, which is the behaviour
    # that keeps a fact from quietly losing part of itself.
    return _exactly(application.conclusion, _transformed(case, condition=None))


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
    # The case is carried forward as an expression; everything it says about the
    # step -- including an operand still standing as a symbol -- comes along.
    expected = _transformed(case, kind="arithmetic_expression")
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
    # The operand's name is dropped because this step has just replaced it; every
    # other thing the expression says is unchanged.
    expected = _transformed(
        expression, operand=value.get("value"), operand_variable=None
    )
    return _exactly(application.conclusion, expected)


#: Rules no query can reach today, and why each one waits.
#:
#: A closed catalog a consumer has to accept includes rules nothing produces a
#: premise for.  Which ones is a user-facing fact and the kind that goes stale
#: quietly, so it is declared here and checked against the closure below rather than
#: left for a reader to work out.  Membership is not a judgement about the rule: a
#: listed rule is implemented and tested from its own premises, and waits only on a
#: premise no published fact carries yet.
#:
#: It is empty, and that is the state the closure has to keep agreeing with.  The
#: three arithmetic rules were listed here for one shared cause -- a case publishes
#: its assignment, but the assignment holds only where the case applies, and nothing
#: discharged that condition from the members establishing it.
#: ``case_condition_entailment`` discharges it, so the chain has a starting point and
#: they left together, as the note here said they would.
#:
#: An empty list makes the paired self-check weaker in one direction and it must not
#: be read as a stronger claim than it is: nothing here can be stale, but the closure
#: it is compared against is only as wide as the fact kinds it is seeded with.  That
#: seed is the part to keep honest -- it had already lost a whole encoder family
#: once, and the agreement stayed green because both sides were computed from the
#: same short reading.
UNREACHABLE_RULE_IDS: Tuple[str, ...] = ()

#: The one rule that seeds a graph rather than deriving within it.
#:
#: ``source_fact`` states a core member's own fact, so it has no ``kind`` premise to
#: wait for and takes no part in the closure below.  It is excluded by name rather
#: than by a property of its premise tuple: a rule that happened to declare no
#: premises would then be silently excluded too, and the closure would report a
#: reachability it never established.
CLOSURE_EXCLUDED_RULE_IDS = ("source_fact",)


def reachable_rule_ids(available_kinds) -> Tuple[str, ...]:
    """Return the rules a graph can reach from the fact kinds it can read.

    The fixpoint is the honest question to ask of a rule catalog: a rule runs when
    every premise kind it declares is available, and running it makes its conclusion
    available in turn.  Asking only "is each premise kind published" would call a rule
    reachable whose premise no rule and no translation ever produces.

    The seed is what the caller can actually read, not what the vocabulary lists.
    Passing the whole vocabulary answers a different question -- what the catalog
    could do -- and the difference is the point: three rules of this catalog are
    reachable in that weaker sense and unreachable in this one.

    :param available_kinds: Fact kinds a graph can read as input.
    :type available_kinds: Iterable[str]
    :return: Reachable rule ids, sorted, excluding the input-node rule.
    :rtype: Tuple[str, ...]

    Example::

        >>> reachable_rule_ids(("variable_equality",))
        ('incompatible_equalities',)
        >>> reachable_rule_ids(())
        ()
    """
    candidates = {
        rule_id: rule
        for rule_id, rule in PROOF_RULES.items()
        if rule_id not in CLOSURE_EXCLUDED_RULE_IDS
    }
    available = set(available_kinds)
    reached: Dict[str, bool] = {}
    while True:
        fired = [
            rule_id
            for rule_id, rule in sorted(candidates.items())
            if rule_id not in reached
            and all(kind in available for kind in rule.premise_kinds if kind)
        ]
        if not fired:
            return tuple(sorted(reached))
        for rule_id in fired:
            reached[rule_id] = True
            available.add(candidates[rule_id].conclusion_kind)


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
        # One premise, like ``source_fact`` has none: the arity a rule declares is
        # whatever its premises are, and a case carries its own condition, so
        # nothing else has to be matched to discharge it.
        ProofRule(
            "case_condition_entailment",
            ("transition_case",),
            "transition_case",
            _case_condition_entailment,
        ),
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
