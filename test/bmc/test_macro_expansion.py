"""Macro-step expansion contract tests for FCSTM BMC."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

from pyfcstm.bmc import (
    STATE_DIAGNOSTIC_ID,
    STATE_TERMINATE_ID,
    BmcBuildError,
    InvalidBmcEncoding,
    MacroExpansionOptions,
    build_bmc_domain,
    diagnostic_source,
    expand_macro_step_cases,
    stable_leaf_source,
    terminated_source,
)
from pyfcstm.bmc.macro import BoolTemplate, MacroStepFormal
from pyfcstm.bmc.source import MacroStepSource, source_from_initial_spec
from pyfcstm.bmc.query import InitialSpec
from pyfcstm.model import load_state_machine_from_text


@pytest.fixture()
def simple_domain():
    """Build a minimal model domain used by expansion API tests."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            [*] -> A;
        }
        """
    )
    return build_bmc_domain(model, bound=1)


@pytest.mark.unittest
def test_public_expand_api_exports_exact_names():
    """The BMC root and expand module expose only the macro expansion API."""
    import pyfcstm.bmc as bmc
    import pyfcstm.bmc.expand as expand

    assert "MacroExpansionOptions" in bmc.__all__
    assert "expand_macro_step_cases" in bmc.__all__
    assert set(expand.__all__) == {"MacroExpansionOptions", "expand_macro_step_cases"}
    assert bmc.MacroExpansionOptions is MacroExpansionOptions
    assert bmc.expand_macro_step_cases is expand_macro_step_cases


@pytest.mark.unittest
def test_expand_imports_do_not_load_z3_or_verify_registry():
    """Macro expansion remains solver-independent and verify-registry independent."""
    code = """
import sys
import pyfcstm.bmc.expand
import pyfcstm.bmc as bmc
_ = bmc.expand_macro_step_cases
blocked = [name for name in sys.modules if name == 'z3' or name.startswith('z3.') or name == 'pyfcstm.verify.registry']
if blocked:
    raise SystemExit('blocked imports: ' + ','.join(sorted(blocked)))
"""
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.unittest
def test_sentinel_sources_expand_to_absorb_formals(simple_domain):
    """Terminated and diagnostic source expansion delegates to sentinel absorbs."""
    terminated = expand_macro_step_cases(terminated_source(simple_domain))
    diagnostic = expand_macro_step_cases(diagnostic_source(simple_domain))

    assert isinstance(terminated, MacroStepFormal)
    assert [case.kind for case in terminated.success_cases] == ["absorb"]
    assert terminated.success_cases[0].source_state_id == STATE_TERMINATE_ID
    assert terminated.success_cases[0].target_state_id == STATE_TERMINATE_ID
    assert terminated.delta_cases == ()
    assert [case.kind for case in diagnostic.success_cases] == ["absorb"]
    assert diagnostic.success_cases[0].source_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.success_cases[0].target_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.success_cases[0].is_diagnostic is True


@pytest.mark.unittest
def test_expand_requires_domain_backed_source(simple_domain):
    """Direct sources without a domain fail closed instead of using side channels."""
    direct = MacroStepSource("stable_leaf", "recurrence", 0, "Root.A")

    with pytest.raises(InvalidBmcEncoding, match="domain-backed"):
        expand_macro_step_cases(direct)

    source = stable_leaf_source(simple_domain, "Root.A")
    formal = expand_macro_step_cases(source)
    assert formal.source is source


@pytest.mark.unittest
def test_macro_expansion_options_validate_runtime_caps():
    """Expansion options reject non-positive caps and invalid partition budgets."""
    assert MacroExpansionOptions().max_micro_steps == 1000
    assert MacroExpansionOptions().max_stack_depth == 64
    assert MacroExpansionOptions(verify_partition=False).verify_partition is False

    invalid_options = [
        {"max_micro_steps": 0},
        {"max_stack_depth": 0},
        {"partition_max_assignments": 0},
        {"verify_partition": "yes"},
    ]
    for kwargs in invalid_options:
        with pytest.raises(InvalidBmcEncoding):
            MacroExpansionOptions(**kwargs)


@pytest.mark.unittest
def test_hot_stable_leaf_initial_and_recurrence_have_same_cases(simple_domain):
    """Hot leaf initial sources reuse recurrence stable-leaf macro semantics."""
    initial = source_from_initial_spec(
        simple_domain,
        InitialSpec(mode="state", state_path="Root.A"),
    )
    recurrence = stable_leaf_source(simple_domain, "Root.A", origin="recurrence")

    initial_formal = expand_macro_step_cases(initial)
    recurrence_formal = expand_macro_step_cases(recurrence)

    assert initial.origin == "initial"
    assert recurrence.origin == "recurrence"
    assert initial.to_semantic_canonical(
        include_origin=False
    ) == recurrence.to_semantic_canonical(include_origin=False)
    assert [case.to_canonical() for case in initial_formal.cases] == [
        case.to_canonical() for case in recurrence_formal.cases
    ]


@pytest.mark.unittest
def test_stable_leaf_fallback_executes_during_chain_not_carry_only(simple_domain):
    """Fallback writeback records lifecycle effects rather than no-op carry."""
    source = stable_leaf_source(simple_domain, "Root.A")
    formal = expand_macro_step_cases(source)
    fallback = next(case for case in formal.success_cases if case.kind == "fallback")

    assert fallback.condition.to_canonical() == BoolTemplate.true().to_canonical()
    assert fallback.var_update[0].variable_name == "x"
    assert fallback.var_update[0].is_carry is False
    assert fallback.var_update[0].expression != "pre:x"


@pytest.mark.unittest
def test_event_used_by_fallback_condition_is_reported_as_negative_fallback_use():
    """Fallback metadata includes event reads from negated accepted transitions."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A;
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback = next(case for case in formal.success_cases if case.kind == "fallback")

    assert [event.path for event in fallback.used_events] == ["Root.A.Go"]
    assert [event.polarity for event in fallback.used_events] == ["negative"]
    assert [event.reason for event in fallback.used_events] == ["fallback"]


@pytest.mark.unittest
def test_verify_partition_option_raises_for_budget_too_small():
    """Partition self-check failures surface as build errors, not silent deltas."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A { during { x = x + 1; } }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    source = stable_leaf_source(domain, "Root.A")

    with pytest.raises(BmcBuildError, match="assignment budget"):
        expand_macro_step_cases(
            source,
            MacroExpansionOptions(partition_max_assignments=1),
        )


@pytest.mark.unittest
def test_source_domain_must_preserve_model_back_reference(simple_domain):
    """Expansion fails closed if a hand-built domain has no model snapshot."""
    cloned = type(simple_domain)(
        bound=simple_domain.bound,
        states=simple_domain.states,
        events=simple_domain.events,
        variables=simple_domain.variables,
        frames=simple_domain.frames,
        steps=simple_domain.steps,
        event_inputs=simple_domain.event_inputs,
        initial_state_ids=simple_domain.initial_state_ids,
        stable_state_ids=simple_domain.stable_state_ids,
    )
    source = stable_leaf_source(cloned, "Root.A")

    with pytest.raises(InvalidBmcEncoding, match="state machine model"):
        expand_macro_step_cases(source)


@pytest.mark.unittest
def test_runtime_aligned_safety_caps_fail_closed(simple_domain):
    """Expansion caps raise build errors instead of leaking partial cases."""
    source = stable_leaf_source(simple_domain, "Root.A")

    cap_options = [
        MacroExpansionOptions(max_micro_steps=1),
        MacroExpansionOptions(max_stack_depth=1),
    ]
    for options in cap_options:
        with pytest.raises(BmcBuildError):
            expand_macro_step_cases(source, options)


@pytest.mark.unittest
def test_guarded_if_without_else_keeps_fallback_partition():
    """Runtime no-op branch paths remain explicit fallback cases."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                during {
                    if [x > 0] { x = x + 1; }
                }
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback_cases = [case for case in formal.success_cases if case.kind == "fallback"]

    assert len(fallback_cases) == 2
    by_update = {case.var_update[0].expression: case for case in fallback_cases}
    assert sorted(by_update) == ["pre:x", "pre:x + 1"]
    assert _evaluate_x_only(by_update["pre:x + 1"], x=1) is True
    assert _evaluate_x_only(by_update["pre:x"], x=0) is True


@pytest.mark.unittest
def test_operation_block_temporaries_are_visible_to_later_statements():
    """Block-local temporaries follow runtime scope inside one operation block."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                during {
                    tmp = x + 2;
                    x = tmp * 3;
                }
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback = next(case for case in formal.success_cases if case.kind == "fallback")

    assert fallback.var_update[0].expression == "3 * pre:x + 6"


@pytest.mark.unittest
def test_boolean_connectives_are_expanded_in_case_partition():
    """Boolean equality and implication are expanded into guard atom formulas."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B : if [(x < 0) == (x <= -1)];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    selected = [case for case in formal.cases if _evaluate_x_only(case, x=0)]

    assert len(selected) == 1
    assert selected[0].kind == "transition"
    assert selected[0].target_state_path == "Root.B"


@pytest.mark.unittest
def test_plain_during_before_can_branch_before_child_entry():
    """Composite plain during-before if paths feed child entry semantics."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        def int y = 0;
        state Root {
            state Parent {
                during before {
                    if [x > 0] { y = y + 10; }
                }
                state A { enter { y = y + 1; } }
                [*] -> A;
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(source_from_initial_spec(domain, InitialSpec()))
    cases = [case for case in formal.success_cases if case.kind == "initial"]

    assert len(cases) == 2
    by_update = {case.var_update[1].expression: case for case in cases}
    assert sorted(by_update) == ["pre:y + 1", "pre:y + 11"]
    assert _evaluate_x_only(by_update["pre:y + 11"], x=1) is True
    assert _evaluate_x_only(by_update["pre:y + 1"], x=0) is True


@pytest.mark.unittest
def test_constant_zero_divisor_does_not_crash_expansion():
    """Constant zero divisors remain symbolic instead of crashing expansion."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B : if [x / 0 > 1];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)

    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    assert any(case.kind == "fallback" for case in formal.success_cases)
    assert any(case.kind == "transition" for case in formal.success_cases)


def _evaluate_x_only(case: Any, x: int) -> bool:
    """Evaluate a test case condition with one integer variable.

    :param case: Macro-step case whose condition should be evaluated.
    :type case: pyfcstm.bmc.macro.CycleCase
    :param x: Runtime value for the ``x`` variable.
    :type x: int
    :return: Whether the case condition holds under the test assignment.
    :rtype: bool

    Example::

        >>> from pyfcstm.bmc.macro import BoolTemplate, CycleCase
        >>> case = CycleCase("transition", 0, "Root", 0, "Root", "Root::transition::Root::0", BoolTemplate.true(), ())
        >>> _evaluate_x_only(case, 0)
        True
    """
    values = {}
    for variable in case.condition.variables:
        if variable.startswith("guard:"):
            expr = variable[len("guard:") :].replace("pre:x", "x")
            try:
                values[variable] = bool(eval(expr, {"__builtins__": {}}, {"x": x}))
            except ZeroDivisionError:
                # ZeroDivisionError: this helper may emulate guard atoms that
                # intentionally keep a constant zero divisor symbolic.
                values[variable] = False
        elif variable.startswith("event:"):
            values[variable] = False
    return case.condition.evaluate(values)
