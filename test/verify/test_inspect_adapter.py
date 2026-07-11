from typing import cast

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.verify import (
    REGISTRY,
    AlgorithmResult,
    InspectRunResult,
    InspectAccessForbiddenError,
    eligible_for_inspect,
    iter_inspect_eligible,
    run_inspect_algorithms,
)
from pyfcstm.verify.taxonomy import (
    CallCountScaling,
    ComplexityTier,
    VerifyAlgorithmMeta,
)


pytestmark = pytest.mark.unittest


def _machine(source="state Root;"):
    ast = parse_with_grammar_entry(source, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def _meta(**overrides):
    values = {
        "name": "custom",
        "description": "custom algorithm",
        "closedness": "closed",
        "complexity_tier": "structural",
        "smt_logic": None,
        "formula_size_scaling": "none",
        "call_count_scaling": "one",
        "incremental": False,
        "fallback_unknown_risk": "none",
        "recommended_tactic": None,
        "quantifier_alternation_depth": 0,
        "max_bitwidth": None,
        "theory_combination": (),
        "verification_scope": "topological_only",
        "dominant_dim": ("states",),
        "diagnostic_codes": (),
        "impl": None,
    }
    values.update(overrides)
    return VerifyAlgorithmMeta(**values)


def test_structural_closed_algorithm_is_eligible_by_default():
    assert eligible_for_inspect(REGISTRY["topological_reachable_set"]) is True


def test_smt_linear_requires_opt_in_complexity_tier():
    assert eligible_for_inspect(REGISTRY["dead_guard"]) is False
    assert (
        eligible_for_inspect(
            REGISTRY["dead_guard"],
            max_complexity_tier="smt_linear",
        )
        is True
    )
    assert (
        eligible_for_inspect(
            REGISTRY["enter_postcondition_implies_during_precondition"],
            max_complexity_tier="smt_linear",
        )
        is True
    )


def test_queried_algorithms_are_never_eligible():
    queried_structural = _meta(closedness="queried", complexity_tier="structural")
    assert eligible_for_inspect(queried_structural) is False


def test_unknown_max_complexity_tier_is_forbidden():
    with pytest.raises(InspectAccessForbiddenError, match="unknown inspect complexity"):
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_complexity_tier=cast(ComplexityTier, "unknown_tier"),
        )


def test_call_count_limit_blocks_more_expensive_closed_algorithm():
    assert (
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_call_count_scaling="one",
        )
        is False
    )
    assert (
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_call_count_scaling="linear_in_states",
        )
        is True
    )


def test_call_count_scaling_outside_inspect_order_is_not_eligible():
    unknown_scaling = _meta(
        call_count_scaling=cast(CallCountScaling, "unknown_scaling")
    )
    assert (
        eligible_for_inspect(
            unknown_scaling,
            max_complexity_tier="smt_undecidable_heuristic",
            max_call_count_scaling="vars_times_transitions",
        )
        is False
    )


def test_invalid_inspect_limits_raise_instead_of_disabling_all_algorithms():
    for invalid_tier in ("smt_lienar", None):
        with pytest.raises(InspectAccessForbiddenError):
            eligible_for_inspect(
                REGISTRY["topological_reachable_set"],
                max_complexity_tier=cast(ComplexityTier, invalid_tier),
            )

    for invalid_call_count in (
        "linear_in_transition",
        "unknown_scaling",
        None,
    ):
        with pytest.raises(InspectAccessForbiddenError):
            eligible_for_inspect(
                REGISTRY["topological_reachable_set"],
                max_call_count_scaling=cast(CallCountScaling, invalid_call_count),
            )


def test_nonlinear_and_undecidable_tier_boundaries_have_no_extra_algorithms():
    expected = tuple(
        meta.name for meta in iter_inspect_eligible(max_complexity_tier="smt_linear")
    )
    for tier in ("smt_nonlinear_decidable", "smt_undecidable_heuristic"):
        assert (
            tuple(meta.name for meta in iter_inspect_eligible(max_complexity_tier=tier))
            == expected
        )


def test_iter_inspect_eligible_preserves_registry_order():
    assert tuple(meta.name for meta in iter_inspect_eligible()) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "event_emission_to_consumer_reachable",
    )
    assert tuple(
        meta.name for meta in iter_inspect_eligible(max_complexity_tier="smt_linear")
    ) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "event_emission_to_consumer_reachable",
        "dead_guard",
        "guard_tautology",
        "forced_guard_unsat_under_init",
        "effect_no_op_under_guard",
        "effect_contradicts_guard",
        "transition_shadowed_by_predecessor",
        "enter_postcondition_implies_during_precondition",
        "composite_init_guards_incomplete",
    )
    assert tuple(
        meta.name
        for meta in iter_inspect_eligible(
            max_complexity_tier="smt_linear",
            max_call_count_scaling="linear_in_states",
        )
    ) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "composite_init_guards_incomplete",
    )


def test_run_inspect_algorithms_executes_default_eligible_registry_set():
    machine = _machine(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """
    )

    results = run_inspect_algorithms(machine)

    assert isinstance(results, tuple)
    assert all(isinstance(result, InspectRunResult) for result in results)
    assert tuple(result.algorithm_name for result in results) == tuple(
        meta.name for meta in iter_inspect_eligible()
    )
    first = results[0]
    assert first.algorithm_name == "topological_reachable_set"
    assert first.complexity_tier == "structural"
    assert first.smt_logic is None
    assert first.verification_scope == "topological_only"
    assert first.diagnostic_codes == ()
    assert first.result_kind == "sat"
    assert first.reason is None
    assert first.diagnostics == ()
    assert first.raw_result["Root.A"] == ()


def test_highest_inspect_budget_executes_every_builtin_in_registry_order():
    results = run_inspect_algorithms(
        _machine(),
        max_complexity_tier="smt_undecidable_heuristic",
        max_call_count_scaling="vars_times_transitions",
        smt_timeout_ms=1000,
    )

    assert tuple(result.algorithm_name for result in results) == tuple(REGISTRY)
    assert len(results) == 14


def test_run_inspect_algorithms_passes_timeout_only_to_smt_algorithms():
    calls = []

    def structural_impl(machine):
        calls.append(("structural", machine))
        return {"ok": True}

    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        calls.append(("smt", machine, tuple(variables), smt_timeout_ms))
        return AlgorithmResult(
            kind="timeout",
            diagnostics=({"code": "W_FAKE", "data": {"target": "Root"}},),
            reason="forced timeout",
        )

    registry = {
        "structural_demo": _meta(
            name="structural_demo",
            complexity_tier="structural",
            smt_logic=None,
            verification_scope="topological_only",
            diagnostic_codes=("W_STRUCT",),
            impl=structural_impl,
        ),
        "composite_init_guards_incomplete": _meta(
            name="composite_init_guards_incomplete",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("W_FAKE",),
            impl=smt_impl,
        ),
    }
    machine = _machine("def int x = 0; state Root;")

    results = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=250,
        registry=registry,
    )

    assert calls == [
        ("structural", machine),
        ("smt", machine, tuple(machine.defines.values()), 250),
    ]
    assert tuple(result.algorithm_name for result in results) == (
        "structural_demo",
        "composite_init_guards_incomplete",
    )
    smt_result = results[1]
    assert smt_result.result_kind == "timeout"
    assert smt_result.reason == "forced timeout"
    assert smt_result.diagnostics == ({"code": "W_FAKE", "data": {"target": "Root"}},)
    assert smt_result.raw_result == AlgorithmResult(
        kind="timeout",
        diagnostics=({"code": "W_FAKE", "data": {"target": "Root"}},),
        reason="forced timeout",
    )


def test_run_inspect_algorithms_none_timeout_is_preserved_for_smt_algorithms():
    seen = []

    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        seen.append(smt_timeout_ms)
        return AlgorithmResult(kind="unknown", reason="solver said unknown")

    registry = {
        "composite_init_guards_incomplete": _meta(
            name="composite_init_guards_incomplete",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=smt_impl,
        )
    }

    result = run_inspect_algorithms(
        _machine(),
        max_complexity_tier="smt_linear",
        smt_timeout_ms=None,
        registry=registry,
    )[0]

    assert seen == [None]
    assert result.result_kind == "unknown"
    assert result.reason == "solver said unknown"


def test_run_inspect_algorithms_keeps_structural_plain_payloads():
    raw_payload = ("Root", "Root.A")

    def structural_impl(machine):
        return raw_payload

    registry = {
        "structural_demo": _meta(
            name="structural_demo",
            complexity_tier="structural",
            smt_logic=None,
            verification_scope="topological_only",
            impl=structural_impl,
        )
    }

    result = run_inspect_algorithms(_machine(), registry=registry)[0]

    assert result.result_kind == "sat"
    assert result.raw_result is raw_payload


def test_run_inspect_algorithms_rejects_invalid_machine_level_smt_payload():
    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        return "bad"

    registry = {
        "composite_init_guards_incomplete": _meta(
            name="composite_init_guards_incomplete",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=smt_impl,
        )
    }

    with pytest.raises(TypeError, match="unexpected raw result type 'str'"):
        run_inspect_algorithms(
            _machine(),
            max_complexity_tier="smt_linear",
            registry=registry,
        )


def test_run_inspect_algorithms_rejects_invalid_smt_tuple_item():
    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        return (
            AlgorithmResult(
                kind="unsat",
                diagnostics=({"code": "W_FAKE", "data": {"state": "Root"}},),
            ),
            "bad",
        )

    registry = {
        "composite_init_guards_incomplete": _meta(
            name="composite_init_guards_incomplete",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("W_FAKE",),
            impl=smt_impl,
        )
    }

    with pytest.raises(TypeError, match="tuple item 1"):
        run_inspect_algorithms(
            _machine(),
            max_complexity_tier="smt_linear",
            registry=registry,
        )


def test_run_inspect_algorithms_rejects_unknown_smt_dispatch_rule():
    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        return AlgorithmResult(kind="sat")

    registry = {
        "custom_smt": _meta(
            name="custom_smt",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=smt_impl,
        )
    }

    with pytest.raises(ValueError, match="no inspect dispatch rule"):
        run_inspect_algorithms(
            _machine(),
            max_complexity_tier="smt_linear",
            registry=registry,
        )


def test_run_inspect_algorithms_keeps_diagnostics_when_one_element_times_out():
    def first_impl(machine, variables, *, smt_timeout_ms=None):
        return AlgorithmResult(
            kind="unsat",
            diagnostics=({"code": "W_FAKE", "data": {"state": "Root.A"}},),
        )

    def second_impl(machine, variables, *, smt_timeout_ms=None):
        return AlgorithmResult(kind="timeout", reason="second transition timed out")

    calls = [first_impl, second_impl]

    def smt_impl(machine, variables, *, smt_timeout_ms=None):
        return calls.pop(0)(machine, variables, smt_timeout_ms=smt_timeout_ms)

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("W_FAKE",),
            impl=smt_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert result.result_kind == "timeout"
    assert result.reason == "second transition timed out"
    assert result.diagnostics == ({"code": "W_FAKE", "data": {"state": "Root.A"}},)


def test_run_inspect_algorithms_aggregates_definite_transition_findings():
    calls = []

    def smt_impl(transition, variables, *, smt_timeout_ms=None):
        source = str(transition.from_state)
        calls.append(source)
        if source in ("INIT_STATE", "A"):
            return AlgorithmResult(kind="sat")
        return AlgorithmResult(
            kind="unsat",
            diagnostics=({"code": "W_FAKE", "data": {"state": "Root.B"}},),
        )

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("W_FAKE",),
            impl=smt_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B;
            B -> C;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert calls == ["INIT_STATE", "A", "B"]
    assert result.result_kind == "unsat"
    assert result.reason is None
    assert result.diagnostics == ({"code": "W_FAKE", "data": {"state": "Root.B"}},)


def test_run_inspect_algorithms_aggregates_all_unsat_transition_results():
    def smt_impl(transition, variables, *, smt_timeout_ms=None):
        return AlgorithmResult(kind="unsat")

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=smt_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert result.result_kind == "unsat"
    assert result.diagnostics == ()


def test_run_inspect_algorithms_treats_empty_per_element_run_as_no_finding():
    def smt_impl(transition, variables, *, smt_timeout_ms=None):
        raise AssertionError("transition-level algorithm should not run")

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=smt_impl,
        )
    }

    result = run_inspect_algorithms(
        _machine("state Root;"),
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert result.result_kind == "sat"
    assert result.diagnostics == ()
    assert result.raw_result == ()


def test_run_inspect_algorithms_aggregates_unsat_findings_before_sat_diagnostics():
    calls = []

    def smt_impl(transition, variables, *, smt_timeout_ms=None):
        calls.append(str(transition.from_state))
        if len(calls) == 1:
            return AlgorithmResult(
                kind="sat",
                diagnostics=({"code": "I_FAKE", "data": {"state": "Root"}},),
            )
        return AlgorithmResult(
            kind="unsat",
            diagnostics=({"code": "W_FAKE", "data": {"state": "Root.A"}},),
        )

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("I_FAKE", "W_FAKE"),
            impl=smt_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert calls == ["INIT_STATE", "A"]
    assert result.result_kind == "unsat"
    assert result.diagnostics == (
        {"code": "I_FAKE", "data": {"state": "Root"}},
        {"code": "W_FAKE", "data": {"state": "Root.A"}},
    )


def test_run_inspect_algorithms_preserves_sat_diagnostic_kind_without_unsat_findings():
    def smt_impl(transition, variables, *, smt_timeout_ms=None):
        return AlgorithmResult(
            kind="sat",
            diagnostics=({"code": "I_FAKE", "data": {"state": "Root"}},),
        )

    registry = {
        "dead_guard": _meta(
            name="dead_guard",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            diagnostic_codes=("I_FAKE",),
            impl=smt_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        registry=registry,
    )[0]

    assert result.result_kind == "sat"
    assert result.diagnostics == ({"code": "I_FAKE", "data": {"state": "Root"}},)


def test_run_inspect_algorithms_dispatches_leaf_lifecycle_algorithm():
    seen = []

    def lifecycle_impl(state, variables, *, smt_timeout_ms=None):
        seen.append((state.name, tuple(variables), smt_timeout_ms))
        return AlgorithmResult(kind="sat")

    registry = {
        "enter_postcondition_implies_during_precondition": _meta(
            name="enter_postcondition_implies_during_precondition",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            call_count_scaling="linear_in_leaves",
            verification_scope="smt_local",
            impl=lifecycle_impl,
        )
    }
    machine = _machine(
        """
        state Root {
            state A;
            pseudo state Probe;
            [*] -> A;
        }
        """
    )

    result = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=75,
        registry=registry,
    )[0]

    assert seen == [("A", (), 75)]
    assert result.result_kind == "sat"


def test_run_inspect_algorithms_dispatches_machine_level_smt_algorithm():
    seen = []

    def machine_impl(machine, variables, *, smt_timeout_ms=None):
        seen.append(
            (
                machine.root_state.name,
                tuple(variable.name for variable in variables),
                smt_timeout_ms,
            )
        )
        return AlgorithmResult(kind="unknown", reason="machine-level check")

    registry = {
        "composite_init_guards_incomplete": _meta(
            name="composite_init_guards_incomplete",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=machine_impl,
        )
    }

    result = run_inspect_algorithms(
        _machine("def int x = 0; state Root;"),
        max_complexity_tier="smt_linear",
        smt_timeout_ms=125,
        registry=registry,
    )[0]

    assert seen == [("Root", ("x",), 125)]
    assert result.result_kind == "unknown"
    assert result.reason == "machine-level check"


def test_run_inspect_algorithms_skips_missing_impl_without_crashing():
    registry = {
        "missing_demo": _meta(
            name="missing_demo",
            complexity_tier="structural",
            verification_scope="topological_only",
            impl=None,
        )
    }

    result = run_inspect_algorithms(_machine(), registry=registry)[0]

    assert result.algorithm_name == "missing_demo"
    assert result.result_kind == "undecidable_skip"
    assert result.diagnostics == ()
    assert "implementation is not registered" in result.reason
    assert result.raw_result == AlgorithmResult(
        kind="undecidable_skip",
        reason="algorithm implementation is not registered",
    )


def test_run_inspect_algorithms_does_not_execute_excluded_metadata():
    calls = []

    def impl(machine):
        calls.append(machine)
        return {"unexpected": True}

    registry = {
        "queried_demo": _meta(
            name="queried_demo",
            closedness="queried",
            complexity_tier="structural",
            impl=impl,
        ),
        "too_expensive_demo": _meta(
            name="too_expensive_demo",
            complexity_tier="smt_linear",
            smt_logic="QF_LIRA",
            verification_scope="smt_local",
            impl=impl,
        ),
    }

    results = run_inspect_algorithms(_machine(), registry=registry)

    assert results == ()
    assert calls == []


def test_run_inspect_algorithms_rejects_unknown_complexity_limit():
    with pytest.raises(InspectAccessForbiddenError, match="unknown inspect complexity"):
        run_inspect_algorithms(
            _machine(),
            max_complexity_tier=cast(ComplexityTier, "unknown_tier"),
            registry={},
        )
