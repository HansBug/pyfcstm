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

from fractions import Fraction

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
def test_division_is_checked_against_the_encoder_not_against_a_guess() -> None:
    """Division was pinned to a semantics the encoder does not have.

    The claim used to be that Python floors while "the encoded semantics truncate
    toward zero", and the encoder was never asked.  It divides two ways, neither of
    them truncation: an ``int`` variable lowers onto Z3's integer division, which is
    Euclidean, and a ``float`` variable lowers onto Z3's reals, which divide exactly.

    Which of the two applies is not recoverable from the published operands.  A
    ``float`` variable states an integral value as an integer -- a query asking
    ``var("x") == -7`` about a real variable produces exactly that -- so two integer
    operands say nothing about the declaration behind them.  Where the two semantics
    agree the answer is the same either way and is published; where they part ways,
    publishing one would be a guess about a declaration the checker cannot see, and no
    claimed value is accepted.
    """

    def application(left, operand, claimed):
        return RuleApplication(
            "arithmetic_evaluation",
            (
                _equality(value=left),
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator="div",
                    operand=operand,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=claimed),
        )

    # Integer operands whose quotient is the same under both readings: published, and
    # a neighbour is refused.
    for left, operand, agreed in ((8, 2, 4), (-8, 2, -4), (6, 3, 2), (-6, -3, 2)):
        assert check_rule(application(left, operand, agreed)) is True, (left, operand)
        assert check_rule(application(left, operand, agreed + 1)) is False

    # Integer operands where the readings part ways.  ``-7 / 2`` is ``-4`` for an
    # integer variable and ``-3.5`` for a real one, so neither is asserted.
    for left, operand in ((7, 2), (-7, 2), (7, -2), (-7, -2)):
        for claimed in (3, -3, 4, -4, 3.5, -3.5):
            assert check_rule(application(left, operand, claimed)) is False, (
                left,
                operand,
                claimed,
            )

    # A float operand names the sort, so reals divide exactly.
    assert check_rule(application(7.5, 2, 3.75)) is True
    assert check_rule(application(7.5, 2, 3.0)) is False, "truncation is not the model"
    assert check_rule(application(-7.0, 2, -3.5)) is True

    # An exact quotient with no finite decimal form, and one beyond every float, are
    # refused rather than rounded: no published number is the one the encoding holds.
    assert check_rule(application(1.0, 3, 0.3333333333333333)) is False
    assert check_rule(application(1.0, 3, 0.0)) is False
    assert check_rule(application(1e308, 1e-308, 1e308)) is False
    assert check_rule(application(1e308, 1e-308, 0.0)) is False


@pytest.mark.unittest
@pytest.mark.parametrize("operator", ["add", "sub", "mul"])
def test_real_arithmetic_publishes_what_the_encoder_holds(operator) -> None:
    """The other three operators answer to the encoder too, not to IEEE754.

    Division was reconciled with the encoder and the module docstring was rewritten to
    say arithmetic follows it -- and ``add``, ``sub`` and ``mul`` stayed on Python's
    floats, so the sentence was false for three operators out of four.  ``0.1 + 0.2``
    is ``3/10`` in the encoding and ``0.30000000000000004`` in a double, and the
    published proof said the latter under ``verification_status`` ``verified``.

    Deciding between the simulator and the encoder was not required after all: the
    quotient path had already established the shape -- compute exactly, publish only
    a value the decimal form reads back as, otherwise decline the step -- and these
    three reuse it.
    """
    exact = {
        "add": (Fraction(1, 10) + Fraction(2, 10), 0.1, 0.2),
        "sub": (Fraction(3, 10) - Fraction(1, 10), 0.3, 0.1),
        "mul": (Fraction(1, 10) * Fraction(3, 1), 0.1, 3),
    }[operator]
    encoded, left, operand = exact
    ieee = {"add": 0.1 + 0.2, "sub": 0.3 - 0.1, "mul": 0.1 * 3}[operator]
    assert float(encoded) != ieee, "the fixture has to exercise the disagreement"

    def application(claimed):
        return RuleApplication(
            "arithmetic_evaluation",
            (
                _equality(value=left),
                _fact(
                    "arithmetic_expression",
                    variable="x",
                    frame=0,
                    operator=operator,
                    operand=operand,
                    target_frame=1,
                ),
            ),
            _equality(frame=1, value=claimed),
        )

    assert check_rule(application(float(encoded))) is True
    assert check_rule(application(ieee)) is False


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


#: The fact kinds a published proof can actually read as an input node's own fact.
#:
#: Three conditions at once, and the third is the one that took a measurement to
#: find: the kind has to be publishable, its fact has to be re-encodable so the
#: binding can hold, and it has to be consumable without a condition standing in the
#: way.  ``transition_case`` meets the first two and fails the third -- it always
#: carries the condition its case is selected under, and the rule that evaluates an
#: arithmetic expression refuses one carrying a field it does not recognize.  Seeding
#: the closure with it answers a different question (what the catalog could do) and
#: reports 8 of 8 where 5 of 8 is the truth.
def _seed_kinds():
    """Return the kinds a closure over the catalog may start from.

    Taken from production rather than transcribed.  Reading one encoder table by
    hand is what made this seed too small: ``transition_case`` is registered in the
    unit-bound family, the seed named only the ordinary one, and the closure then
    reported three rules unreachable for a cause that was not theirs -- while the
    registry it is compared against agreed, because both had been derived from the
    same short reading.
    """
    from pyfcstm.bmc.infeasibility import encodable_fact_kinds

    return frozenset(encodable_fact_kinds())


@pytest.mark.unittest
def test_the_closure_and_the_unreachable_registry_agree() -> None:
    """The self-check the contract asks for, in the direction that is automatable.

    A closed catalog a consumer has to accept includes rules nothing reaches, and
    which ones is a user-facing fact.  Computing it from the rules' own premise kinds
    and comparing against the declared list is what stops the list going stale in
    either direction: a rule that becomes reachable and stays listed, or one that
    goes dark and is not.
    """
    from pyfcstm.bmc.proof_rules import (
        CLOSURE_EXCLUDED_RULE_IDS,
        PROOF_RULES,
        UNREACHABLE_RULE_IDS,
        reachable_rule_ids,
    )

    counted = set(PROOF_RULES) - set(CLOSURE_EXCLUDED_RULE_IDS)
    reached = set(reachable_rule_ids(_seed_kinds()))

    assert counted - reached == set(UNREACHABLE_RULE_IDS)
    assert reached & set(UNREACHABLE_RULE_IDS) == set()


@pytest.mark.unittest
def test_the_closure_excludes_the_input_rule_by_name_and_nothing_else() -> None:
    """The exclusion set is pinned, because a wider one would hide a real gap.

    ``source_fact`` seeds a graph rather than deriving within it, so it has no
    premise kind to wait for.  Excluding it by a property of its premise tuple would
    also exclude any rule that came to declare none, and the closure would then
    report a reachability it never established.  Pinning the set literally is what
    makes a new member of it a deliberate act.
    """
    from pyfcstm.bmc.proof_rules import CLOSURE_EXCLUDED_RULE_IDS

    assert CLOSURE_EXCLUDED_RULE_IDS == ("source_fact",)


@pytest.mark.unittest
@pytest.mark.parametrize("dropped", sorted(_seed_kinds()))
def test_removing_any_fact_source_changes_what_the_closure_reaches(
    dropped: str,
) -> None:
    """Every seed kind is load-bearing, so the self-check can fail.

    A self-check that cannot fail reports nothing.  The contract asks for this
    direction by name: deleting any fact source has to turn it red.  A seed whose
    removal changed nothing would mean the closure never depended on it, and the
    agreement above would hold for a reason other than the one it claims.
    """
    from pyfcstm.bmc.proof_rules import reachable_rule_ids

    full = set(reachable_rule_ids(_seed_kinds()))
    without = set(reachable_rule_ids(_seed_kinds() - {dropped}))

    assert without < full, "%s reaches nothing the others do not" % dropped


@pytest.mark.unittest
@pytest.mark.parametrize(
    "dropped, goes_dark",
    [
        ("transition_case", "case_condition_entailment"),
        ("proposition", "boolean_complement"),
        ("state_exclusion", "state_domain_exhaustion"),
    ],
)
def test_a_reachability_regression_breaks_the_agreement(
    dropped: str, goes_dark: str
) -> None:
    """The other direction the contract names, restated for an empty registry.

    While the registry had entries, this direction was tested by removing one and
    requiring the agreement to break.  An empty registry has nothing to remove, and
    deleting the test with the entries would have retired a gate rather than
    satisfying it -- the stale state it guards is still reachable, only from the
    other side: a fact source disappears, a rule goes dark, and an empty registry
    keeps saying nothing is.

    The witnesses are written out rather than derived so that a change to the seed
    cannot quietly empty this test too.

    :param dropped: The fact kind removed from the closure's seed.
    :type dropped: str
    :param goes_dark: The rule that must lose its only premise source with it.
    :type goes_dark: str
    """
    from pyfcstm.bmc.proof_rules import (
        CLOSURE_EXCLUDED_RULE_IDS,
        PROOF_RULES,
        UNREACHABLE_RULE_IDS,
        reachable_rule_ids,
    )

    seed = _seed_kinds()
    assert dropped in seed, "the witness names a kind no binding encodes"
    counted = set(PROOF_RULES) - set(CLOSURE_EXCLUDED_RULE_IDS)
    reached = set(reachable_rule_ids(seed - {dropped}))

    assert goes_dark not in reached, "%s survived without %s" % (goes_dark, dropped)
    assert counted - reached != set(UNREACHABLE_RULE_IDS)


def _discharged_case(**overrides) -> dict:
    """The same case with its condition discharged: the key is gone, not emptied.

    ``arithmetic_evaluation`` reads keys rather than values, and refuses a field it
    does not recognize rather than dropping it, so a condition left behind as an
    empty tuple still stops the chain one step later.
    """
    case = _conditional_case(**overrides)
    case.pop("condition", None)
    return case


def _conditional_case(**overrides) -> dict:
    """A transition case whose assignment holds only where its condition does."""
    fields = {
        "variable": "x",
        "frame": 1,
        "target_frame": 2,
        "operator": "add",
        "operand": 1,
        "condition": (_fact("state_membership", frame=1, state=1, excluded=False),),
    }
    fields.update(overrides)
    return _fact("transition_case", **fields)


@pytest.mark.unittest
def test_case_condition_entailment_empties_the_condition_and_nothing_else() -> None:
    """The one thing this rule is allowed to change is the condition.

    The rule exists because an assignment guarded by a condition is not an
    assignment: ``x`` increases by one *where this case applies*, and a step that
    forgets the second half proves something the model does not promise.  Its
    conclusion is therefore the same case with the condition discharged -- every
    other field travels unchanged, and the checker is what makes that a fact
    rather than an intention.
    """
    application = RuleApplication(
        "case_condition_entailment",
        (_conditional_case(),),
        _discharged_case(),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "conclusion, why",
    [
        (_conditional_case(), "the condition survives, so nothing was discharged"),
        (_discharged_case(operand=2), "the operand was rewritten"),
        (_discharged_case(variable="y"), "the subject was rewritten"),
        (_discharged_case(target_frame=3), "the step was widened"),
    ],
)
def test_case_condition_entailment_refuses_a_rewritten_conclusion(
    conclusion, why
) -> None:
    """A discharged condition is not a licence to change the assignment.

    :param conclusion: The conclusion the checker must refuse.
    :type conclusion: dict
    :param why: What the caller got wrong, for the failure message.
    :type why: str
    """
    application = RuleApplication(
        "case_condition_entailment", (_conditional_case(),), conclusion
    )

    assert check_rule(application) is False, why


@pytest.mark.unittest
def test_case_condition_entailment_refuses_a_case_with_nothing_to_discharge() -> None:
    """An unconditional case is already what the rule produces.

    Accepting it would put a node in the graph that establishes what its own
    premise says, which the dependency pruning cannot tell from a real step.
    """
    application = RuleApplication(
        "case_condition_entailment",
        (_discharged_case(),),
        _discharged_case(),
    )

    assert check_rule(application) is False


@pytest.mark.unittest
def test_every_rule_in_the_catalog_is_reachable() -> None:
    """The acceptance the contract asks for: no rule a consumer must accept is dark.

    A closed catalog whose premises nothing produces is a promise the tool cannot
    keep, and the registry of unreachable rules is where that gap was recorded
    honestly.  With the condition discharged by ``case_condition_entailment`` the
    registry is empty, and this test is what stops it filling up again unnoticed.
    """
    from pyfcstm.bmc.proof_rules import (
        CLOSURE_EXCLUDED_RULE_IDS,
        UNREACHABLE_RULE_IDS,
        reachable_rule_ids,
    )

    counted = set(PROOF_RULES) - set(CLOSURE_EXCLUDED_RULE_IDS)

    assert UNREACHABLE_RULE_IDS == ()
    assert counted - set(reachable_rule_ids(_seed_kinds())) == set()


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises, why",
    [
        ((), "no premise names a case to discharge"),
        (
            (_conditional_case(), _equality()),
            "a second premise means the rule was matched to something it does not read",
        ),
        ((_equality(),), "a value is not a case, whatever its condition would be"),
        (
            (_fact("arithmetic_expression", variable="x", frame=1, operator="add"),),
            "an expression derived from a case is not the case",
        ),
    ],
)
def test_case_condition_entailment_refuses_premises_it_does_not_read(
    premises, why
) -> None:
    """The two shape guards every rule in the catalog carries, for this one.

    ``premise_kinds`` is what a builder matches on, but a checker that trusted the
    match would agree with a step the builder proposed wrongly -- and the builder is
    the part being checked.  So the arity and the tag are both re-established here,
    and a conclusion is never reached from premises this rule cannot read.

    :param premises: The premises the checker must refuse.
    :type premises: tuple
    :param why: What the caller got wrong, for the failure message.
    :type why: str
    """
    application = RuleApplication(
        "case_condition_entailment", premises, _discharged_case()
    )

    assert check_rule(application) is False, why


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("start", "divisor"),
    [(7.5, 2), (-7.5, 2), (1.0, 4), (5.0, 2), (-1.0, 8)],
)
def test_the_checker_agrees_with_the_simulator_about_a_real_quotient(
    start, divisor
) -> None:
    """Two surfaces, one model, one quotient -- checked against each other.

    The simulator runs the effect and the proof checker re-derives it.  They disagreed
    by a whole quarter: the checker truncated, so ``7.5 / 2`` came back as ``3.0`` from
    a proof whose ``verification_status`` said ``verified`` while ``pyfcstm simulate``
    printed ``3.75``.  Catching that class again is what this is for.

    The divisors below are ones where the two surfaces agree exactly, and that
    agreement is *not* general -- picking five passing values and concluding the
    surfaces always agree is the mistake this docstring exists to not repeat.  The
    checker divides reals exactly, as the encoder does, and the simulator divides them
    in IEEE754; where that loses precision the two part ways by an ulp.  ``0.3 / 0.1``
    is exactly ``3`` and the simulator reaches ``2.9999999999999996``; ``9.9 / 3.3``
    is ``3`` and it reaches ``3.0000000000000004``.

    So division shares the open question that ``add`` and ``mul`` are left out for,
    in one sub-case: the two reference surfaces disagree about real arithmetic in
    general, and which one a proof should follow is a semantics decision.  The proof
    follows the encoder, which is what the reference says it is about.  What is pinned
    here is narrower and still worth pinning: a quotient the two surfaces *do* agree
    on has to come back as that number, not as a truncation of it.
    """
    from pyfcstm.model import load_state_machine_from_text
    from pyfcstm.simulate import SimulationRuntime

    model = (
        "def float x = 0.0;\n"
        "state Root { state A; state B; [*] -> A;\n"
        "  A -> A effect { x = x / %s; }; A -> B; }" % divisor
    )
    runtime = SimulationRuntime(
        load_state_machine_from_text(model, "machine.fcstm"),
        initial_vars={"x": start},
    )
    # The first cycle takes the initial transition into ``A``; the second runs the
    # self-loop, which is the one that divides.
    runtime.cycle()
    runtime.cycle()
    simulated = dict(runtime.vars)["x"]

    application = RuleApplication(
        "arithmetic_evaluation",
        (
            _equality(value=start),
            _fact(
                "arithmetic_expression",
                variable="x",
                frame=0,
                operator="div",
                operand=divisor,
                target_frame=1,
            ),
        ),
        _equality(frame=1, value=simulated),
    )

    assert check_rule(application) is True, (start, divisor, simulated)


@pytest.mark.unittest
def test_excluded_state_selected_closes_on_a_slot_pinned_to_an_excluded_state() -> None:
    """A frame required to be in the state it also rules out has nowhere to be."""
    application = RuleApplication(
        "excluded_state_selected",
        (
            _fact(
                "variable_equality",
                variable="$state",
                state_slot=True,
                frame=1,
                value=3,
            ),
            _fact("state_exclusion", frame=1, state=3),
        ),
        _fact("false"),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premises",
    [
        # A model variable rather than the frame's state slot.  Without the flag this
        # would close a value contradiction under a sentence about states.
        (
            _fact("variable_equality", variable="x", frame=1, value=3),
            _fact("state_exclusion", frame=1, state=3),
        ),
        # Different frames are different subjects, so neither contradicts the other.
        (
            _fact(
                "variable_equality",
                variable="$state",
                state_slot=True,
                frame=1,
                value=3,
            ),
            _fact("state_exclusion", frame=2, state=3),
        ),
        # The exclusion names a state the slot was not pinned to.
        (
            _fact(
                "variable_equality",
                variable="$state",
                state_slot=True,
                frame=1,
                value=3,
            ),
            _fact("state_exclusion", frame=1, state=4),
        ),
        # Two exclusions and no equality: that shape belongs to the domain rule.
        (
            _fact("state_exclusion", frame=1, state=3),
            _fact("state_exclusion", frame=1, state=4),
        ),
        # A field the rule does not consume.  Dropping it silently would make a
        # vocabulary addition disappear at the step that closes the proof.
        (
            _fact(
                "variable_equality",
                variable="$state",
                state_slot=True,
                frame=1,
                value=3,
                surprise=1,
            ),
            _fact("state_exclusion", frame=1, state=3),
        ),
    ],
    ids=[
        "a_model_variable",
        "different_frames",
        "a_different_state",
        "two_exclusions",
        "an_unconsumed_field",
    ],
)
def test_excluded_state_selected_refuses_anything_else(premises) -> None:
    """Each premise shape that must not close, and why it must not.

    :param premises: The premises the rule is offered.
    :type premises: Tuple[Mapping[str, object], ...]
    """
    assert (
        check_rule(RuleApplication("excluded_state_selected", premises, _fact("false")))
        is False
    )


@pytest.mark.unittest
def test_preceding_value_entailment_moves_the_frame_and_nothing_else() -> None:
    """The same variable at the same value, one frame earlier."""
    application = RuleApplication(
        "preceding_value_entailment",
        (_fact("variable_equality", variable="x", frame=2, value=5),),
        _fact("variable_equality", variable="x", frame=1, value=5),
    )

    assert check_rule(application) is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "premise, conclusion",
    [
        # Frame 0 has no predecessor, so there is no earlier frame to speak about.
        (
            _fact("variable_equality", variable="x", frame=0, value=5),
            _fact("variable_equality", variable="x", frame=-1, value=5),
        ),
        # Two frames back is a second step this premise says nothing about.
        (
            _fact("variable_equality", variable="x", frame=3, value=5),
            _fact("variable_equality", variable="x", frame=1, value=5),
        ),
        # Forwards, which is the direction the citation seam cannot record.
        (
            _fact("variable_equality", variable="x", frame=2, value=5),
            _fact("variable_equality", variable="x", frame=3, value=5),
        ),
        # A different value: letting it move would conclude anything about the
        # earlier frame and call it carried.
        (
            _fact("variable_equality", variable="x", frame=2, value=5),
            _fact("variable_equality", variable="x", frame=1, value=4),
        ),
        # A different variable.
        (
            _fact("variable_equality", variable="x", frame=2, value=5),
            _fact("variable_equality", variable="y", frame=1, value=5),
        ),
        # A bound restricts a range rather than pinning a value.
        (
            _fact("variable_bound", variable="x", frame=2, value=5, operator="lt"),
            _fact("variable_equality", variable="x", frame=1, value=5),
        ),
        # A field the rule does not consume, on either side.
        (
            _fact("variable_equality", variable="x", frame=2, value=5, surprise=1),
            _fact("variable_equality", variable="x", frame=1, value=5),
        ),
        (
            _fact("variable_equality", variable="x", frame=2, value=5),
            _fact("variable_equality", variable="x", frame=1, value=5, surprise=1),
        ),
    ],
    ids=[
        "frame_zero",
        "two_frames_back",
        "forwards",
        "a_different_value",
        "a_different_variable",
        "a_bound",
        "an_unconsumed_field_in_the_premise",
        "an_unconsumed_field_in_the_conclusion",
    ],
)
def test_preceding_value_entailment_refuses_anything_else(premise, conclusion) -> None:
    """Each shape that must not pass the syntax half of this rule.

    The solver settles whether the earlier value was forced; this settles that the
    step is the one the rule describes, and these are the ways it is not.

    :param premise: The premise offered.
    :type premise: Mapping[str, object]
    :param conclusion: The conclusion offered.
    :type conclusion: Mapping[str, object]
    """
    assert (
        check_rule(
            RuleApplication("preceding_value_entailment", (premise,), conclusion)
        )
        is False
    )
