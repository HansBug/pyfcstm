"""Reader-visible operations and conditions retain their actual meaning."""

import pytest

from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.bmc.explanation import human_text_for_fact
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    "operator,phrase,value",
    [("/", "x@2 == x@1/2", 4), ("-", "x@2 == x@1 - 2", 6), ("+", "x@2 == x@1 + 2", 10)],
)
def test_proof_steps_name_the_arithmetic_operation(operator, phrase, value, text_aligner):
    model = load_state_machine_from_text(
        """
def int x = 8;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> A effect { x = x %s 2; };
    A -> B;
}
"""
        % operator
    )
    formula = compile_bmc_query(
        model,
        """
assume at 1: x == 8;
assume at 2: x == 99;
check reach <= 3: active("Root.A");
""",
    )
    result = solve_bmc_property(formula, infeasibility_explanation="proof")
    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof"
    readings = [step.text for step in explanation.narrative.reasoning_steps]
    text_aligner.assert_equal(
        expect="\n".join([
            "8 == x@1",
            "Implies(And(1 == state[1], True), %s)" % phrase,
            "99 == x@2",
            "Therefore %s." % phrase,
            "Therefore %s." % phrase,
            "Starting from that value, the step therefore leaves x equal to %s at frame 2." % value,
            "Therefore one value cannot be two things at once. No execution satisfies these initialization requirements, transition requirements, and query requirements, and the property was not evaluated.",
        ]),
        actual="\n".join(readings),
    )


def test_symbolic_operand_is_named_before_substitution_in_proof(text_aligner):
    model = load_state_machine_from_text("""
def int x = 0;
def int y = 2;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> A effect { x = x + y; };
    A -> B;
}
""")
    result = solve_bmc_property(
        compile_bmc_query(
            model,
            """
assume at 1: x == 0;
assume at 1: y == 2;
assume at 2: x == 1;
check reach <= 3: active("Root.A");
""",
        ),
        infeasibility_explanation="proof",
    )
    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == "proof"
    readings = [step.text for step in explanation.narrative.reasoning_steps]
    text_aligner.assert_equal(expect="""
0 == x@1
2 == y@1
Implies(And(1 == state[1], True), x@2 == x@1 + y@1)
1 == x@2
Therefore x@2 == x@1 + y@1.
Therefore x@2 == x@1 + y@1.
Therefore x@2 == x@1 + 2.
Starting from that value, the step therefore leaves x equal to 2 at frame 2.
Therefore one value cannot be two things at once. No execution satisfies these initialization requirements, transition requirements, and query requirements, and the property was not evaluated.
""".strip(), actual="\n".join(readings))


@pytest.mark.parametrize("holds,phrase", [(True, "to hold"), (False, "to not hold")])
def test_condition_does_not_hide_event_identity_or_polarity(holds, phrase):
    fact = dict(
        kind="transition_case",
        variable="x",
        frame=2,
        target_frame=3,
        operation="add",
        operand=2,
        condition=[
            dict(kind="proposition", identity="Root.Confirm at step 2", holds=holds),
        ],
    )
    text = human_text_for_fact("transition_rule", fact)
    assert text == (
        "Between frame 2 and frame 3, the transition requires assignment to x@3 "
        "(operation=add, source=x@2, operand=2) where Root.Confirm at step 2 is required %s." % phrase
    )


def test_multiplication_is_named_in_checked_domain_proof(text_aligner):
    from pyfcstm.bmc.proof import build_domain_proof
    from pyfcstm.bmc.proof_text import linearize_proof
    from pyfcstm.bmc.solver import _SolveBudget

    inputs = (
        (
            "initial.variable.x",
            dict(kind="variable_equality", variable="x", frame=0, value=3),
        ),
        (
            "transition.step.0000",
            dict(
                kind="transition_case",
                variable="x",
                frame=0,
                target_frame=1,
                operator="mul",
                operand=2,
            ),
        ),
        (
            "assumption.0000",
            dict(kind="variable_equality", variable="x", frame=1, value=99),
        ),
    )
    proof, record = build_domain_proof("assumptions_prefix", inputs, _SolveBudget(None))
    assert proof is not None, record.reason
    text = "\n".join(step.text for step in linearize_proof(proof))
    # Standalone proof facts have no original SMT expression or source binding.
    # Preserve the operation metadata instead of reconstructing a display formula.
    text_aligner.assert_equal(expect="""
At frame 0, x must equal 3.
Between frame 0 and frame 1, assignment to x@1 (operation=mul, source=x@0, operand=2).
At frame 1, x must equal 99.
The transition therefore means that assignment to x@1 (operation=mul, source=x@0, operand=2) between frame 0 and frame 1.
Starting from that value, the step therefore leaves x equal to 6 at frame 1.
Therefore one value cannot be two things at once. No execution satisfies these requirements, and the property was not evaluated.
""".strip(), actual=text)


@pytest.mark.parametrize("condition", [{"kind": "proposition"}, {"kind": "opaque"}])
def test_unexpanded_conditions_remain_visible_without_invented_identity(condition):
    fact = dict(
        kind="transition_case",
        variable="x",
        frame=2,
        target_frame=3,
        operation="add",
        operand=2,
        condition=[condition],
    )
    text = human_text_for_fact("transition_rule", fact)
    assert text == (
        "Between frame 2 and frame 3, the transition requires assignment to x@3 "
        "(operation=add, source=x@2, operand=2) where a %s requirement." % condition["kind"]
    )


def test_fact_only_assignment_keeps_symbolic_operand_without_inventing_formula():
    fact = dict(kind='transition_case', variable='x', frame=1, target_frame=2,
                operation='mod', operand_variable='y', condition=[])
    text = human_text_for_fact('transition_rule', fact)
    assert text == (
        'Between frame 1 and frame 2, the transition requires assignment to x@2 '
        '(operation=mod, source=x@1, operand=y@1).'
    )


def test_fact_only_assignment_with_missing_operand_does_not_invent_a_value():
    fact = dict(kind='transition_case', variable='x', frame=1, target_frame=2,
                operation='add', condition=[])
    text = human_text_for_fact('transition_rule', fact)
    assert text == 'A transition rule constrains this scenario without a reduced domain fact.'
