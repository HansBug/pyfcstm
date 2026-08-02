"""
Tests for the domain rule catalog and its deterministic checker.

A proof step is only publishable when a checker has agreed with it, so each rule
is tested from both sides: the application it accepts, and the four ways a caller
can get it wrong.  The four negatives are the same for every rule -- a premise the
rule does not take, a conclusion that does not follow, a premise about another
frame, and one about another subject -- because those are the mistakes a builder
actually makes when it widens a match.

The module contains:
* A transcription of the frozen rule table's premise and conclusion shapes
* Positive and four-way negative cases for every rule the catalog carries
* Tests that the checker refuses to answer for a rule it does not know

.. note::
   The catalog is deliberately incomplete at this stage.  Tests here enumerate the
   rules the catalog reports, so a rule added later joins the matrix without anyone
   editing a list.
"""

import pytest

from pyfcstm.bmc.proof_rules import (
    PROOF_RULES,
    RuleApplication,
    check_rule,
)


def _fact(kind: str, **fields) -> dict:
    """A domain fact of one tag with the fields that tag implies."""
    fact = {"kind": kind}
    fact.update(fields)
    return fact


def _equality(variable: str = "x", frame: int = 0, value: int = 0) -> dict:
    """The fact shape every rule below reads or produces."""
    return _fact("variable_equality", variable=variable, frame=frame, value=value)


@pytest.mark.unittest
def test_the_catalog_reports_every_rule_it_carries() -> None:
    """The catalog is the single list a builder dispatches on.

    Rules are added over several stages, so this asserts the shape of the mapping
    rather than a fixed set: every entry names a rule the published vocabulary
    knows, and every entry can answer for itself.
    """
    from pyfcstm.bmc.explanation import _PROOF_RULE_IDS

    assert PROOF_RULES, "the catalog cannot be empty once a rule exists"
    for rule_id, rule in PROOF_RULES.items():
        assert rule_id in _PROOF_RULE_IDS, "%r is not a published rule id" % rule_id
        assert rule.rule_id == rule_id
        assert rule.premise_kinds, "%r must declare what it reads" % rule_id
        assert rule.conclusion_kind, "%r must declare what it produces" % rule_id


@pytest.mark.unittest
def test_an_unknown_rule_is_refused_rather_than_assumed_sound() -> None:
    """A step naming a rule nobody implements cannot be checked, so it is refused.

    Returning "unchecked" here would put an unverifiable step in a proof the
    contract says carries no holes.
    """
    with pytest.raises(KeyError):
        check_rule(RuleApplication("modus_ponens", (_equality(),), _fact("false")))


@pytest.mark.unittest
def test_incompatible_equalities_closes_on_two_values_for_one_slot() -> None:
    """Two different values for one variable at one frame cannot both hold."""
    application = RuleApplication(
        "incompatible_equalities",
        (_equality(value=0), _equality(value=1)),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises, conclusion, why",
    [
        (
            (_equality(value=0),),
            _fact("false"),
            "one value contradicts nothing",
        ),
        (
            (_equality(value=0), _equality(value=1)),
            _equality(value=0),
            "the rule concludes false and nothing else",
        ),
        (
            (_equality(value=0), _equality(frame=1, value=1)),
            _fact("false"),
            "values at different frames may differ freely",
        ),
        (
            (_equality(value=0), _equality(variable="y", value=1)),
            _fact("false"),
            "values of different variables may differ freely",
        ),
    ],
    ids=[
        "a-premise-the-rule-does-not-take",
        "a-conclusion-that-does-not-follow",
        "premises-about-another-frame",
        "premises-about-another-subject",
    ],
)
def test_incompatible_equalities_refuses_the_four_ways_it_can_be_misapplied(
    premises, conclusion, why
) -> None:
    """The four negatives every rule needs, spelled out once.

    Two of them are the reason this rule cannot be widened: equal values at
    *different* frames or on *different* variables are the ordinary case, and a
    checker that let them through would publish a contradiction where none exists.
    """
    assert (
        check_rule(RuleApplication("incompatible_equalities", premises, conclusion))
        is False
    ), why


@pytest.mark.unittest
def test_arithmetic_evaluation_produces_the_value_the_operands_determine() -> None:
    """The one rule here that yields a new fact rather than a contradiction.

    Everything downstream -- multi-hop graphs, transitive item ids, a derived node
    a later step consumes -- needs a rule that concludes something other than
    ``false``, which is why this one is in the first batch.
    """
    application = RuleApplication(
        "arithmetic_evaluation",
        (
            _equality(value=0),
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="add",
                operand=1,
                target_frame=1,
            ),
        ),
        _equality(frame=1, value=1),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises, conclusion",
    [
        (
            (
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=1),
        ),
        (
            (
                _equality(value=0),
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=2),
        ),
        (
            (
                _equality(frame=5, value=0),
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=1),
        ),
        (
            (
                _equality(variable="y", value=0),
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="add",
                    operand=1,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=1),
        ),
    ],
    ids=[
        "a-premise-the-rule-does-not-take",
        "a-conclusion-that-does-not-follow",
        "premises-about-another-frame",
        "premises-about-another-subject",
    ],
)
def test_arithmetic_evaluation_refuses_the_four_ways_it_can_be_misapplied(
    premises, conclusion
) -> None:
    """Without the operand's value the target is unknown, and 0 + 1 is not 2."""
    assert (
        check_rule(RuleApplication("arithmetic_evaluation", premises, conclusion))
        is False
    )


@pytest.mark.unittest
def test_arithmetic_evaluation_uses_the_model_semantics_for_integer_division() -> None:
    """Integer division is the case where guessing in Python gets it wrong.

    The contract requires the current model semantics rather than a Python
    evaluation, and the two disagree on negative operands: Python floors toward
    negative infinity while the encoded semantics truncate toward zero.  Pinning
    the disagreement is what keeps the checker honest about which one it uses.
    """
    truncating = RuleApplication(
        "arithmetic_evaluation",
        (
            _equality(value=-7),
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="div",
                operand=2,
                target_frame=1,
            ),
        ),
        _equality(frame=1, value=-3),
    )
    flooring = RuleApplication(
        "arithmetic_evaluation",
        (
            _equality(value=-7),
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="div",
                operand=2,
                target_frame=1,
            ),
        ),
        _equality(frame=1, value=-4),
    )

    assert check_rule(truncating) is True
    assert check_rule(flooring) is False, "-7 // 2 is Python's answer, not the model's"


@pytest.mark.unittest
def test_interval_intersection_closes_on_bounds_that_cross() -> None:
    """A lower bound above an upper bound leaves no value."""
    application = RuleApplication(
        "interval_intersection",
        (
            _fact("variable_bound", variable="x", frame=0, operator="ge", value=5),
            _fact("variable_bound", variable="x", frame=0, operator="le", value=3),
        ),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "lower, upper, empty",
    [
        (("ge", 5), ("le", 3), True),
        (("ge", 5), ("le", 5), False),
        (("gt", 5), ("le", 5), True),
        (("ge", 5), ("lt", 5), True),
        (("gt", 5), ("lt", 6), True),
    ],
    ids=[
        "the-bounds-cross",
        "a-single-point-survives",
        "an-open-lower-bound-excludes-it",
        "an-open-upper-bound-excludes-it",
        "no-integer-lies-strictly-between",
    ],
)
def test_interval_intersection_decides_emptiness_on_the_endpoints(
    lower, upper, empty
) -> None:
    """Whether the endpoints are included is the whole question for this rule.

    The last case is the one a real-number reading gets wrong: 5 < x < 6 has
    solutions over the reals and none over the integers, and these facts are about
    an integer variable.
    """
    application = RuleApplication(
        "interval_intersection",
        (
            _fact(
                "variable_bound",
                variable="x",
                frame=0,
                operator=lower[0],
                value=lower[1],
            ),
            _fact(
                "variable_bound",
                variable="x",
                frame=0,
                operator=upper[0],
                value=upper[1],
            ),
        ),
        _fact("false"),
    )

    assert check_rule(application) is empty


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises",
    [
        (_fact("variable_bound", variable="x", frame=0, operator="ge", value=5),),
        (
            _fact("variable_bound", variable="x", frame=0, operator="ge", value=5),
            _fact("variable_bound", variable="x", frame=1, operator="le", value=3),
        ),
        (
            _fact("variable_bound", variable="x", frame=0, operator="ge", value=5),
            _fact("variable_bound", variable="y", frame=0, operator="le", value=3),
        ),
    ],
    ids=[
        "a-premise-the-rule-does-not-take",
        "premises-about-another-frame",
        "premises-about-another-subject",
    ],
)
def test_interval_intersection_refuses_bounds_it_cannot_intersect(premises) -> None:
    """Bounds on different slots constrain different things and never cross."""
    assert (
        check_rule(RuleApplication("interval_intersection", premises, _fact("false")))
        is False
    )


def _domain(frame: int = 1, states=(1, 2)) -> dict:
    """The legal states one frame may hold."""
    return _fact("state_domain", frame=frame, states=list(states))


def _excluded(state: int, frame: int = 1) -> dict:
    """One state ruled out at one frame."""
    return _fact("state_exclusion", frame=frame, state=state)


@pytest.mark.unittest
def test_state_domain_exhaustion_closes_when_every_legal_state_is_ruled_out() -> None:
    """A frame with no state left to be is a contradiction about that frame."""
    application = RuleApplication(
        "state_domain_exhaustion",
        (_domain(), _excluded(1), _excluded(2)),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises",
    [
        (_domain(), _excluded(1)),
        (_domain(), _excluded(1), _excluded(2), _excluded(9)),
        (_domain(), _excluded(1, frame=2), _excluded(2, frame=2)),
        (_domain(frame=1), _domain(frame=2), _excluded(1), _excluded(2)),
    ],
    ids=[
        "a-state-still-remains",
        "an-exclusion-outside-the-domain",
        "exclusions-about-another-frame",
        "two-domains-leave-the-subject-ambiguous",
    ],
)
def test_state_domain_exhaustion_refuses_what_does_not_empty_the_frame(
    premises,
) -> None:
    """Coverage has to be exact: every legal state ruled out, and nothing else.

    The second case is the one worth naming.  Ruling out a state the frame could
    not hold anyway contributes nothing, and counting it would let the rule close
    on a frame that still has somewhere to be.
    """
    assert (
        check_rule(RuleApplication("state_domain_exhaustion", premises, _fact("false")))
        is False
    )


@pytest.mark.unittest
def test_definedness_failure_closes_when_the_guard_excludes_the_required_value() -> (
    None
):
    """A division whose divisor is pinned to the one value it forbids."""
    application = RuleApplication(
        "definedness_failure",
        (
            _fact(
                "definedness_guard",
                variable="x",
                frame=0,
                operation="division",
                forbidden=0,
            ),
            _equality(value=0),
        ),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises",
    [
        (
            _fact(
                "definedness_guard",
                variable="x",
                frame=0,
                operation="division",
                forbidden=0,
            ),
        ),
        (
            _fact(
                "definedness_guard",
                variable="x",
                frame=0,
                operation="division",
                forbidden=0,
            ),
            _equality(value=1),
        ),
        (
            _fact(
                "definedness_guard",
                variable="x",
                frame=0,
                operation="division",
                forbidden=0,
            ),
            _equality(frame=1, value=0),
        ),
        (
            _fact(
                "definedness_guard",
                variable="x",
                frame=0,
                operation="division",
                forbidden=0,
            ),
            _equality(variable="y", value=0),
        ),
    ],
    ids=[
        "a-premise-the-rule-does-not-take",
        "the-value-is-not-the-forbidden-one",
        "the-value-is-at-another-frame",
        "the-value-is-of-another-subject",
    ],
)
def test_definedness_failure_refuses_a_value_the_guard_permits(premises) -> None:
    """The guard forbids one value at one slot, and only that pairing closes."""
    assert (
        check_rule(RuleApplication("definedness_failure", premises, _fact("false")))
        is False
    )


@pytest.mark.unittest
def test_boolean_complement_closes_on_a_proposition_and_its_negation() -> None:
    """The same requirement asserted and denied cannot both hold."""
    application = RuleApplication(
        "boolean_complement",
        (
            _fact("proposition", identity="active(Root.A)@1", holds=True),
            _fact("proposition", identity="active(Root.A)@1", holds=False),
        ),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises",
    [
        ((_fact("proposition", identity="active(Root.A)@1", holds=True),)),
        (
            _fact("proposition", identity="active(Root.A)@1", holds=True),
            _fact("proposition", identity="active(Root.A)@1", holds=True),
        ),
        (
            _fact("proposition", identity="active(Root.A)@1", holds=True),
            _fact("proposition", identity="active(Root.A)@2", holds=False),
        ),
        (
            _fact("proposition", identity="active(Root.A)@1", holds=True),
            _fact("proposition", identity="active(Root.B)@1", holds=False),
        ),
    ],
    ids=[
        "a-premise-the-rule-does-not-take",
        "the-same-polarity-twice",
        "propositions-about-another-frame",
        "propositions-about-another-subject",
    ],
)
def test_boolean_complement_needs_one_identity_and_two_polarities(premises) -> None:
    """Identity is compared as a whole string, so a different frame is a different
    proposition and no contradiction at all."""
    assert (
        check_rule(RuleApplication("boolean_complement", premises, _fact("false")))
        is False
    )


@pytest.mark.unittest
def test_transition_assignment_carries_a_value_across_one_step() -> None:
    """A selected transition case relating one frame's value to the next."""
    application = RuleApplication(
        "transition_assignment",
        (
            _fact(
                "transition_case",
                variable="x",
                frame=0,
                target_frame=1,
                operator="add",
                operand=1,
            ),
            _equality(value=0),
        ),
        _fact(
            "arithmetic_expression",
            variable="x",
            frame=0,
            operator="add",
            operand=1,
            target_frame=1,
        ),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case_frame, case_target, value_frame, ok",
    [
        (0, 1, 0, True),
        (0, 2, 0, False),
        (0, 1, 1, False),
    ],
    ids=[
        "adjacent-frames",
        "a-step-that-skips-a-frame",
        "a-value-from-the-wrong-side-of-the-step",
    ],
)
def test_transition_assignment_relates_adjacent_frames_only(
    case_frame, case_target, value_frame, ok
) -> None:
    """A macro-step goes to the next frame; a case spanning two is not one step."""
    application = RuleApplication(
        "transition_assignment",
        (
            _fact(
                "transition_case",
                variable="x",
                frame=case_frame,
                target_frame=case_target,
                operator="add",
                operand=1,
            ),
            _equality(frame=value_frame, value=0),
        ),
        _fact(
            "arithmetic_expression",
            variable="x",
            frame=case_frame,
            operator="add",
            operand=1,
            target_frame=case_target,
        ),
    )

    assert check_rule(application) is ok


@pytest.mark.unittest
def test_equality_substitution_rewrites_an_expression_with_a_known_value() -> None:
    """Replacing a subject by its value keeps the expression equivalent."""
    application = RuleApplication(
        "equality_substitution",
        (
            _equality(variable="y", value=3),
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="add",
                operand_variable="y",
                target_frame=1,
            ),
        ),
        _fact(
            "arithmetic_expression",
            variable="x",
            frame=0,
            operator="add",
            operand=3,
            target_frame=1,
        ),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "value_fact, conclusion_operand",
    [
        (_equality(variable="y", value=3), 4),
        (_equality(variable="y", frame=1, value=3), 3),
        (_equality(variable="z", value=3), 3),
    ],
    ids=[
        "a-conclusion-that-does-not-follow",
        "the-value-is-at-another-frame",
        "the-value-is-of-another-subject",
    ],
)
def test_equality_substitution_refuses_a_value_that_is_not_the_operand(
    value_fact, conclusion_operand
) -> None:
    """Sort and frame have to agree, or the substitution changes the meaning."""
    application = RuleApplication(
        "equality_substitution",
        (
            value_fact,
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="add",
                operand_variable="y",
                target_frame=1,
            ),
        ),
        _fact(
            "arithmetic_expression",
            variable="x",
            frame=0,
            operator="add",
            operand=conclusion_operand,
            target_frame=1,
        ),
    )

    assert check_rule(application) is False


@pytest.mark.unittest
@pytest.mark.parametrize(
    "rule_id, premises, conclusion",
    [
        (
            "arithmetic_evaluation",
            (
                {
                    "kind": "variable_equality",
                    "variable": "$state",
                    "state_slot": True,
                    "frame": 0,
                    "value": 0,
                },
                {
                    "kind": "arithmetic_expression",
                    "variable": "$state",
                    "state_slot": True,
                    "frame": 0,
                    "target_frame": 1,
                    "operator": "add",
                    "operand": 1,
                },
            ),
            {
                "kind": "variable_equality",
                "variable": "$state",
                "frame": 1,
                "value": 1,
            },
        ),
        (
            "transition_assignment",
            (
                {
                    "kind": "transition_case",
                    "variable": "$state",
                    "state_slot": True,
                    "frame": 0,
                    "target_frame": 1,
                    "operator": "add",
                    "operand": 1,
                },
                {
                    "kind": "variable_equality",
                    "variable": "$state",
                    "state_slot": True,
                    "frame": 0,
                    "value": 0,
                },
            ),
            {
                "kind": "arithmetic_expression",
                "variable": "$state",
                "frame": 0,
                "target_frame": 1,
                "operator": "add",
                "operand": 1,
            },
        ),
    ],
    ids=["arithmetic-evaluation", "transition-assignment"],
)
def test_a_derivation_may_not_change_what_its_subject_is(
    rule_id, premises, conclusion
) -> None:
    """Keeping the name while dropping the flag is changing the subject.

    A frame's state and a variable can be spelled alike -- a model may declare one
    named like the slot -- so the flag is what says which a fact is about.  A
    derivation that inherits the name but not the flag hands the next round a fact
    that reads as a variable and came from a state; the rule that refuses two values
    for one slot would then close a contradiction between a state and a variable
    that never disagreed, and the whole graph would still be reported ``verified``.

    The checker recomputes each conclusion field from the premises, so the subject's
    kind is one of the fields it has to recompute.
    """
    assert check_rule(RuleApplication(rule_id, premises, conclusion)) is False

    kept = dict(conclusion)
    kept["state_slot"] = True
    assert check_rule(RuleApplication(rule_id, premises, kept)) is True


@pytest.mark.unittest
def test_a_state_may_not_stand_in_for_an_expression_operand() -> None:
    """An operand is a value the expression reads, and a state is not one.

    Substitution replaces a named operand with the value that operand holds.  A
    frame's state is not something an expression can be written over, so letting a
    slot supply the value would rewrite the expression into a statement the model
    never made.
    """
    application = RuleApplication(
        "equality_substitution",
        (
            {
                "kind": "variable_equality",
                "variable": "n",
                "state_slot": True,
                "frame": 0,
                "value": 2,
            },
            {
                "kind": "arithmetic_expression",
                "variable": "x",
                "frame": 0,
                "target_frame": 1,
                "operator": "add",
                "operand_variable": "n",
            },
        ),
        {
            "kind": "arithmetic_expression",
            "variable": "x",
            "frame": 0,
            "target_frame": 1,
            "operator": "add",
            "operand": 2,
        },
    )

    assert check_rule(application) is False


@pytest.mark.unittest
def test_a_conclusion_may_not_carry_a_field_its_premises_never_mentioned() -> None:
    """A conclusion is what the premises determine, no more and no less.

    Naming the fields to compare means a field left off the list is a field nobody
    recomputes.  That gap has been found twice: first ``state_slot``, letting a
    derivation change what it talked about, then ``operand_variable``, letting one
    invent a symbol its premises never mentioned -- and an invented symbol is what
    the substitution step reads next, so a chain of four accepted applications can
    manufacture a contradiction out of premises that agree.

    Comparing the whole mapping is what closes the class rather than the instance.
    """
    case = {
        "kind": "transition_case",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand": 1,
    }
    value = {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0}
    determined = {
        "kind": "arithmetic_expression",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand": 1,
    }

    assert check_rule(
        RuleApplication("transition_assignment", (case, value), determined)
    )

    invented = dict(determined, operand_variable="y")
    assert (
        check_rule(RuleApplication("transition_assignment", (case, value), invented))
        is False
    )


@pytest.mark.unittest
def test_an_operand_still_symbolic_is_refused_rather_than_evaluated() -> None:
    """A symbol has no value, so the step that reads one has to run first.

    Evaluating it anyway means adding ``None`` to a number, which raises out of a
    predicate whose whole contract is to answer yes or no.  Refusing is both the
    right answer and the one the caller can act on.
    """
    application = RuleApplication(
        "arithmetic_evaluation",
        (
            {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
            {
                "kind": "arithmetic_expression",
                "variable": "x",
                "frame": 0,
                "target_frame": 1,
                "operator": "add",
                "operand_variable": "n",
            },
        ),
        {"kind": "variable_equality", "variable": "x", "frame": 1, "value": 0},
    )

    assert check_rule(application) is False


@pytest.mark.unittest
@pytest.mark.parametrize(
    "guard, value",
    [
        (
            {
                "kind": "definedness_guard",
                "operation": "division",
                "variable": "x",
                "forbidden": 0,
            },
            {"kind": "variable_equality", "variable": "x", "value": 0},
        ),
        (
            {
                "kind": "definedness_guard",
                "operation": "division",
                "frame": 0,
                "forbidden": 0,
            },
            {"kind": "variable_equality", "frame": 0, "value": 0},
        ),
    ],
    ids=["no-frame", "no-variable"],
)
def test_a_half_named_slot_closes_nothing(guard, value) -> None:
    """Two gates on the same question have to answer it the same way.

    ``incompatible_equalities`` refuses a slot that is not fully named; this rule
    used to accept one, refusing only when both halves were missing.  A contradiction
    that rests on "some value somewhere" names nothing the reader can act on, and the
    looser of two gates is the one that decides.
    """
    assert (
        check_rule(
            RuleApplication("definedness_failure", (guard, value), {"kind": "false"})
        )
        is False
    )


@pytest.mark.unittest
def test_a_carried_fact_keeps_what_nobody_listed() -> None:
    """Carrying a premise forward means carrying all of it, not a chosen part.

    Three rounds of the same defect came from building the expected conclusion as a
    list of fields to copy.  Fixing the *comparison* did not help, because the
    proposer and the checker were writing the same list: a field both forgot dropped
    out of both, they agreed, and the fact silently lost part of itself.  Here that
    field is ``operand_variable`` -- lose it and an operand still standing as a
    symbol looks like a number the next step is free to evaluate.

    A rule that carries a premise forward now says only what it *changes*.
    """
    case = {
        "kind": "transition_case",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand": 7,
        "operand_variable": "n",
    }
    value = {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0}
    washed = {
        "kind": "arithmetic_expression",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand": 7,
    }

    assert (
        check_rule(RuleApplication("transition_assignment", (case, value), washed))
        is False
    )
    assert check_rule(
        RuleApplication(
            "transition_assignment", (case, value), dict(washed, operand_variable="n")
        )
    )


@pytest.mark.unittest
def test_substitution_drops_the_name_it_just_replaced_and_nothing_else() -> None:
    """The one field this step removes is the one it has answered."""
    expression = {
        "kind": "arithmetic_expression",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand_variable": "n",
    }
    value = {"kind": "variable_equality", "variable": "n", "frame": 0, "value": 3}
    substituted = {
        "kind": "arithmetic_expression",
        "variable": "x",
        "frame": 0,
        "target_frame": 1,
        "operator": "add",
        "operand": 3,
    }

    assert check_rule(
        RuleApplication("equality_substitution", (value, expression), substituted)
    )
    assert (
        check_rule(
            RuleApplication(
                "equality_substitution",
                (value, expression),
                dict(substituted, operand_variable="n"),
            )
        )
        is False
    )


@pytest.mark.unittest
def test_evaluation_refuses_an_expression_it_does_not_fully_understand() -> None:
    """Consuming a fact into another shape cannot carry an unknown field forward.

    The two rules above hand their premise on, so anything new rides along.  This
    one turns an expression into a value and keeps none of it, which means a field
    added to the vocabulary later would disappear exactly where the fact changes
    what it is about.  Refusing is the honest answer.
    """
    application = RuleApplication(
        "arithmetic_evaluation",
        (
            {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
            {
                "kind": "arithmetic_expression",
                "variable": "x",
                "frame": 0,
                "target_frame": 1,
                "operator": "add",
                "operand": 1,
                "surprise": 9,
            },
        ),
        {"kind": "variable_equality", "variable": "x", "frame": 1, "value": 1},
    )

    assert check_rule(application) is False
