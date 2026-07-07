"""BMC-core alignment tests over the shared semantic fixture corpus."""

from __future__ import annotations

import json
from typing import Any, Iterable, List, Mapping, Sequence, Tuple

import pytest
import z3

from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
)
from pyfcstm.simulate import SimulationRuntime
from test.bmc.semantic_fixture_policy import (
    NUMERIC_UNSUPPORTED_CASES,
    BMC_CORE_FIXTURE_LEDGER_CASES,
    CONSTRUCTOR_DIAGNOSTIC_EXCLUDE_CASES,
    TEMPORARY_BMC_CORE_EXCLUDE_CASES,
    policy_by_case,
    policy_for_case,
)
from test.testings.simulate_semantics import (
    BMC_CORE_RUNNER,
    SemanticCaseError,
    _cycle_input_for_step,
    _effective_cycle_count,
    _register_fixture_handlers,
    _simulation_kwargs,
    build_state_machine_from_case,
    is_runner_excluded,
    iter_semantic_cases,
)


pytestmark = pytest.mark.filterwarnings(
    "ignore:Bitwise AND.*limited support:UserWarning"
)


_SUPPORTED_POLICY_MODES = {
    "hard_pass",
    "partial",
    "expected_unsupported",
    "temporary_exclude",
    "long_term_exclude",
}


class _StaticFalseExpectation(Exception):
    """Internal marker for fixture expectations that are statically false."""


def _solver(*constraints: z3.ExprRef) -> z3.Solver:
    solver = z3.Solver()
    solver.add(*constraints)
    return solver


def _value_literal(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BmcBuildError(
            "semantic fixture initial value is not numeric for BMC-core query: %r"
            % (value,)
        )
    return repr(value)


def _initial_predicate(initial_vars: Mapping[str, Any]) -> str:
    return " && ".join(
        "%s == %s" % (name, _value_literal(value))
        for name, value in sorted(initial_vars.items())
    )


def _query_text_for_case(case, bound: int) -> str:
    initial = case.data.get("initial") or {}
    lines = []
    initial_vars = initial.get("vars") or {}
    where = _initial_predicate(initial_vars) if initial_vars else ""
    if initial.get("state") is not None:
        target = json.dumps(initial["state"], ensure_ascii=False)
        line = "init state(%s)" % target
        if where:
            line += " where " + where
        lines.append(line + ";")
    elif where:
        lines.append("init cold where %s;" % where)
    lines.append("check reach <= %d: terminated();" % max(1, bound))
    return "\n".join(lines)


def _event_constraints(core, step_index: int, selected_events: Iterable[str]):
    selected = set(selected_events)
    return tuple(
        core.symbols.event_input(step_index, event.path)
        if event.path in selected
        else z3.Not(core.symbols.event_input(step_index, event.path))
        for event in core.context.domain.events
    )


def _collect_runtime_trace(case) -> Tuple[int, Tuple[Tuple[str, ...], ...]]:
    model = build_state_machine_from_case(case)
    runtime = SimulationRuntime(model, **_simulation_kwargs(case))
    _register_fixture_handlers(runtime, case)
    event_inputs: List[Tuple[str, ...]] = []
    frame_index = 0
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d]" % index
        expect = step.get("expect") or {}
        if "raises" in expect:
            raise BmcBuildError(
                "%s has step exception expectations; it must be excluded or handled "
                "by a future BMC step-error runner." % case.id
            )
        cycle_count = _effective_cycle_count(step, case.id, case.yaml_path, field_path)
        cycle_input = _cycle_input_for_step(step, case.id, case.yaml_path, field_path)
        for _ in range(cycle_count):
            result = runtime.cycle(cycle_input)
            event_inputs.append(tuple(result.input_events))
            frame_index += 1
    return frame_index, tuple(event_inputs)


def _expect_state(core, frame_index: int, state_path: Any) -> z3.BoolRef:
    if state_path is None:
        return z3.BoolVal(True)
    state_id = core.context.domain.state_path_to_id(state_path)
    if state_path == ".".join(core.context.model.root_state.path):
        return z3.Or(
            core.symbols.frame_state(frame_index) == z3.IntVal(state_id),
            core.symbols.frame_state(frame_index) == z3.IntVal(STATE_INIT_ID),
        )
    return core.symbols.frame_state(frame_index) == z3.IntVal(state_id)


def _expect_ended(core, frame_index: int, ended: bool) -> z3.BoolRef:
    expr = core.symbols.frame_state(frame_index) == z3.IntVal(STATE_TERMINATE_ID)
    return expr if ended else z3.Not(expr)


def _expect_vars(core, frame_index: int, values: Mapping[str, Any]) -> z3.BoolRef:
    return z3.And(
        *[
            core.symbols.frame_var(frame_index, name) == value
            for name, value in sorted(values.items())
        ]
    )


def _expect_vars_exact(core, frame_index: int, values: Mapping[str, Any]) -> z3.BoolRef:
    variable_names = {var.name for var in core.context.domain.variables}
    if set(values) != variable_names:
        raise _StaticFalseExpectation
    return _expect_vars(core, frame_index, values)


def _expect_vars_keys(core, names: Sequence[str]) -> z3.BoolRef:
    variable_names = {var.name for var in core.context.domain.variables}
    if set(names) != variable_names:
        raise _StaticFalseExpectation
    return z3.BoolVal(True)


def _expect_vars_absent(core, names: Sequence[str]) -> z3.BoolRef:
    variable_names = {var.name for var in core.context.domain.variables}
    if variable_names.intersection(names):
        raise _StaticFalseExpectation
    return z3.BoolVal(True)


def _expectation_expr(core, case, ignored_fields: Sequence[str]) -> z3.BoolRef:
    ignored = set(ignored_fields)
    constraints = []
    frame_index = 0
    public_fields = {
        "state",
        "vars",
        "vars_exact",
        "vars_keys",
        "vars_absent",
        "ended",
    }
    observed_public_fields = 0
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d]" % index
        expect = step.get("expect") or {}
        if "handler_calls" in expect and "handler_calls" not in ignored:
            raise BmcBuildError(
                "%s %s handler_calls need an explicit partial BMC policy."
                % (case.id, field_path)
            )
        frame_index += _effective_cycle_count(step, case.id, case.yaml_path, field_path)
        try:
            if "state" in expect:
                observed_public_fields += 1
                constraints.append(_expect_state(core, frame_index, expect["state"]))
            if "ended" in expect:
                observed_public_fields += 1
                constraints.append(_expect_ended(core, frame_index, expect["ended"]))
            if "vars" in expect:
                observed_public_fields += 1
                constraints.append(_expect_vars(core, frame_index, expect["vars"]))
            if "vars_exact" in expect:
                observed_public_fields += 1
                constraints.append(
                    _expect_vars_exact(core, frame_index, expect["vars_exact"])
                )
            if "vars_keys" in expect:
                observed_public_fields += 1
                constraints.append(_expect_vars_keys(core, expect["vars_keys"]))
            if "vars_absent" in expect:
                observed_public_fields += 1
                constraints.append(_expect_vars_absent(core, expect["vars_absent"]))
        except _StaticFalseExpectation:
            constraints.append(z3.BoolVal(False))
        unknown_unignored = (set(expect) - public_fields - ignored) - {"raises"}
        if unknown_unignored:
            raise BmcBuildError(
                "%s %s has unsupported BMC expectation fields: %r"
                % (case.id, field_path, sorted(unknown_unignored))
            )
    if observed_public_fields == 0:
        raise BmcBuildError(
            "%s has no public state/ended/vars expectation for BMC-core alignment."
            % case.id
        )
    return z3.And(*constraints) if constraints else z3.BoolVal(True)


def _assert_semantic_fixture_matches_bmc_core(case, ignored_fields: Sequence[str]):
    bound, selected_events_by_step = _collect_runtime_trace(case)
    model = build_state_machine_from_case(case)
    query_text = _query_text_for_case(case, bound)
    core = build_bmc_core_formula(BmcEngine(model).prepare(query_text))
    event_constraints = []
    for step_index, selected_events in enumerate(selected_events_by_step):
        event_constraints.extend(_event_constraints(core, step_index, selected_events))
    expectation = _expectation_expr(core, case, ignored_fields)

    assert _solver(core.core, *event_constraints).check() == z3.sat
    assert _solver(core.core, *event_constraints, expectation).check() == z3.sat
    assert (
        _solver(core.core, *event_constraints, z3.Not(expectation)).check() == z3.unsat
    )


def _assert_expected_unsupported(case) -> None:
    bound = sum(
        _effective_cycle_count(step, case.id, case.yaml_path, "steps[%d]" % index)
        for index, step in enumerate(case.data.get("steps") or [])
    )
    model = build_state_machine_from_case(case)
    query_text = _query_text_for_case(case, bound)
    with pytest.raises(UnsupportedBmcQuery, match="unsupported_bmc_core"):
        build_bmc_core_formula(BmcEngine(model).prepare(query_text))


@pytest.mark.unittest
def test_bmc_semantic_fixture_policy_covers_known_gap_inventory() -> None:
    cases = {case.id: case for case in iter_semantic_cases()}
    assert len(cases) >= 165
    assert BMC_CORE_FIXTURE_LEDGER_CASES <= set(cases)
    assert len(BMC_CORE_FIXTURE_LEDGER_CASES) == 43

    excluded_in_yaml = {
        case.id for case in cases.values() if is_runner_excluded(case, BMC_CORE_RUNNER)
    }
    assert (
        excluded_in_yaml
        == TEMPORARY_BMC_CORE_EXCLUDE_CASES | CONSTRUCTOR_DIAGNOSTIC_EXCLUDE_CASES
    )
    assert not (NUMERIC_UNSUPPORTED_CASES & excluded_in_yaml)

    policy_map = policy_by_case(BMC_CORE_FIXTURE_LEDGER_CASES)
    assert set(policy_map) == BMC_CORE_FIXTURE_LEDGER_CASES

    for case_id in BMC_CORE_FIXTURE_LEDGER_CASES:
        policy = policy_for_case(case_id)
        assert policy.mode in _SUPPORTED_POLICY_MODES
        assert policy.reason

    with pytest.raises(SemanticCaseError, match="unknown runner for exclusion check"):
        is_runner_excluded(next(iter(cases.values())), "unknown_runner")


@pytest.mark.unittest
@pytest.mark.parametrize("case", iter_semantic_cases(), ids=lambda case: case.id)
def test_bmc_core_matches_semantic_fixture_public_observations(case) -> None:
    policy = policy_for_case(case.id)
    if is_runner_excluded(case, BMC_CORE_RUNNER):
        pytest.skip("%s: %s" % (policy.bucket, policy.reason))
    if policy.mode == "expected_unsupported":
        _assert_expected_unsupported(case)
        return
    _assert_semantic_fixture_matches_bmc_core(case, policy.ignored_expect_fields)
