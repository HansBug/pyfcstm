"""Reader-visible operations and conditions retain their actual meaning."""

import pytest

from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.bmc.explanation import human_text_for_fact
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    "operator,phrase",
    [("/", "divides x by 2"), ("-", "subtracts 2 from x"), ("+", "adds 2 to x")],
)
def test_proof_steps_name_the_arithmetic_operation(operator, phrase):
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
    assert any(phrase in text for text in readings), readings
    assert all(
        "changed by" not in text and "changes x by" not in text for text in readings
    )


def test_symbolic_operand_is_named_before_substitution_in_proof():
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
    assert any("adds y to x" in text for text in readings)
    assert all("None" not in text for text in readings)


@pytest.mark.parametrize("holds,phrase", [(True, "to hold"), (False, "not hold")])
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
    assert "Root.Confirm at step 2" in text
    assert phrase in text


def test_multiplication_is_named_in_checked_domain_proof():
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
    assert "multiplies x by 2" in text
    assert "changed by" not in text


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
    assert "a %s requirement" % condition["kind"] in text
    assert "None" not in text
