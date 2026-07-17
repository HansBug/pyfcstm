"""BMC-core alignment tests over the shared semantic fixture corpus."""

from __future__ import annotations

import json
import re
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
    compile_bmc_property,
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
_SAFE_BARE_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FBMCQ_RESERVED_VAR_NAMES = {
    "init",
    "cold",
    "terminated",
    "state",
    "where",
    "havoc",
    "assume",
    "always",
    "at",
    "event",
    "events",
    "cardinality",
    "any",
    "at_most_one",
    "check",
    "reach",
    "forbid",
    "invariant",
    "must_reach",
    "exists_always",
    "response",
    "cover",
    "trigger",
    "within",
    "var",
    "cycle",
    "active",
    "case",
    "called",
    "call_count",
    "current",
    "null",
    "action",
    "step",
    "stage",
    "role",
    "active_leaf",
    "named_ref",
    "pi",
    "E",
    "tau",
    "and",
    "or",
    "not",
    "implies",
    "iff",
    "xor",
    "true",
    "false",
    "True",
    "False",
    "TRUE",
    "FALSE",
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


def _var_reference(name: str) -> str:
    if _SAFE_BARE_VAR_RE.fullmatch(name) and name not in _FBMCQ_RESERVED_VAR_NAMES:
        return name
    return "var(%s)" % json.dumps(name, ensure_ascii=False)


def _havoc_reference(name: str) -> str:
    if _SAFE_BARE_VAR_RE.fullmatch(name) and name not in _FBMCQ_RESERVED_VAR_NAMES:
        return name
    return json.dumps(name, ensure_ascii=False)


def _initial_predicate(initial_vars: Mapping[str, Any]) -> str:
    return " && ".join(
        "%s == %s" % (_var_reference(name), _value_literal(value))
        for name, value in sorted(initial_vars.items())
    )


def _initial_havoc_clause(model, initial_vars: Mapping[str, Any]) -> str:
    if not initial_vars:
        return ""
    model_variables = set(model.defines)
    initial_variable_names = set(initial_vars)
    if initial_variable_names == model_variables:
        return " havoc *"
    refs = ", ".join(_havoc_reference(name) for name in sorted(initial_variable_names))
    return " havoc { %s }" % refs


def _query_text_for_case(
    case, model, bound: int, check_clause: str = "check reach <= {bound}: terminated();"
) -> str:
    initial = case.data.get("initial") or {}
    lines = []
    initial_vars = initial.get("vars") or {}
    where = _initial_predicate(initial_vars) if initial_vars else ""
    havoc = _initial_havoc_clause(model, initial_vars)
    if initial.get("state") is not None:
        target = json.dumps(initial["state"], ensure_ascii=False)
        line = "init state(%s)" % target
        line += havoc
        if where:
            line += " where " + where
        lines.append(line + ";")
    elif where:
        lines.append("init cold%s where %s;" % (havoc, where))
    lines.append(check_clause.format(bound=max(1, bound)))
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


def _expected_handler_call_value(item: Mapping[str, Any], field_name: str) -> Any:
    defaults = {
        "active_leaf": item.get("state"),
        "call_stage": item.get("stage"),
        "abstract_target": item.get("action"),
        "named_ref": None,
    }
    return item.get(field_name, defaults.get(field_name))


def _expect_handler_record(core, record, expected: Mapping[str, Any]) -> z3.BoolRef:
    terms = [
        z3.BoolVal(record.action_name == expected.get("action")),
        z3.BoolVal(record.state_path == expected.get("state")),
        z3.BoolVal(record.stage == expected.get("stage")),
        z3.BoolVal(
            record.active_leaf_path
            == _expected_handler_call_value(expected, "active_leaf")
        ),
        z3.BoolVal(
            record.stage == _expected_handler_call_value(expected, "call_stage")
        ),
        z3.BoolVal(
            record.action_name
            == _expected_handler_call_value(expected, "abstract_target")
        ),
        z3.BoolVal(
            record.named_ref == _expected_handler_call_value(expected, "named_ref")
        ),
    ]
    expected_vars = expected.get("vars") or {}
    variable_names = {var.name for var in core.context.domain.variables}
    if set(expected_vars) != variable_names:
        return z3.BoolVal(False)
    for name, value in sorted(expected_vars.items()):
        try:
            snapshot_value = record.snapshot[name]
        except KeyError as err:
            raise BmcBuildError(
                "BMC call record is missing snapshot variable %r." % name
            ) from err
        terms.append(snapshot_value == value)
    return z3.And(*terms)


def _expect_handler_calls(
    core, frame_index: int, expected_calls: Sequence[Mapping[str, Any]]
) -> z3.BoolRef:
    expected = tuple(dict(item) for item in expected_calls)
    total = z3.IntVal(0)
    selected_prefix = z3.IntVal(0)
    ordered_terms = []
    for step in core.steps[:frame_index]:
        for relation in step.case_relations:
            relation_call_count = len(relation.call_records)
            for local_index, record in enumerate(relation.call_records):
                choices = [
                    z3.And(
                        selected_prefix + local_index == expected_index,
                        _expect_handler_record(core, record, expected_item),
                    )
                    for expected_index, expected_item in enumerate(expected)
                ]
                ordered_terms.append(
                    z3.Implies(
                        relation.selector,
                        z3.Or(*choices) if choices else z3.BoolVal(False),
                    )
                )
            selected_count = z3.If(
                relation.selector,
                z3.IntVal(relation_call_count),
                z3.IntVal(0),
            )
            total = total + selected_count
            selected_prefix = selected_prefix + selected_count
    return z3.And(total == len(expected), *ordered_terms)


def _handler_step_selector(frame_index: int) -> str:
    if frame_index <= 0:
        return "-1"
    if frame_index == 1:
        return "0"
    return "0..%d" % (frame_index - 1)


def _handler_var_predicate(values: Mapping[str, Any]) -> str:
    return " && ".join(
        "%s == %s" % (_var_reference(name), _value_literal(value))
        for name, value in sorted(values.items())
    )


def _handler_call_filter_query(item: Mapping[str, Any], step_selector: str) -> str:
    args = [
        json.dumps(item["action"], ensure_ascii=False),
        "step=%s" % step_selector,
        "state=%s" % json.dumps(item["state"], ensure_ascii=False),
        "stage=%s" % json.dumps(item["stage"], ensure_ascii=False),
        "active_leaf=%s"
        % json.dumps(
            _expected_handler_call_value(item, "active_leaf"), ensure_ascii=False
        ),
    ]
    named_ref = _expected_handler_call_value(item, "named_ref")
    if named_ref is None:
        args.append("named_ref=null")
    else:
        args.append("named_ref=%s" % json.dumps(named_ref, ensure_ascii=False))
    where = _handler_var_predicate(item.get("vars") or {})
    if where:
        args.append("where %s" % where)
    return ", ".join(args)


def _expect_handler_calls_query(
    frame_index: int, expected_calls: Sequence[Mapping[str, Any]]
) -> str:
    step_selector = _handler_step_selector(frame_index)
    terms = ["call_count(step=%s) == %d" % (step_selector, len(expected_calls))]
    grouped = {}
    for item in expected_calls:
        filter_text = _handler_call_filter_query(item, step_selector)
        grouped[filter_text] = grouped.get(filter_text, 0) + 1
    for filter_text, count in sorted(grouped.items()):
        terms.append("call_count(%s) == %d" % (filter_text, count))
    return " && ".join(terms)


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
        "delta",
        "handler_calls",
    }
    observed_public_fields = 0
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d]" % index
        expect = step.get("expect") or {}
        start_frame_index = frame_index
        frame_index += _effective_cycle_count(step, case.id, case.yaml_path, field_path)
        try:
            if "handler_calls" in expect and "handler_calls" not in ignored:
                observed_public_fields += 1
                constraints.append(
                    _expect_handler_calls(core, frame_index, expect["handler_calls"])
                )
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
            if "delta" in expect and "delta" not in ignored:
                observed_public_fields += 1
                for step_index in range(start_frame_index, frame_index):
                    constraints.append(
                        core.symbols.delta_flag(step_index)
                        == z3.BoolVal(expect["delta"])
                    )
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


def _expect_state_query(state_path: Any) -> str:
    if state_path is None:
        return "true"
    return "active(%s)" % json.dumps(state_path, ensure_ascii=False)


def _expect_ended_query(ended: bool) -> str:
    return "terminated()" if ended else "!terminated()"


def _expect_vars_query(values: Mapping[str, Any]) -> str:
    items = [
        "%s == %s" % (_var_reference(name), _value_literal(value))
        for name, value in sorted(values.items())
    ]
    return " && ".join(items) if items else "true"


def _expectation_query_predicate(case, ignored_fields: Sequence[str]) -> str:
    ignored = set(ignored_fields)
    frame_index = 0
    frame_clauses = []
    observed_public_fields = 0
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d]" % index
        expect = step.get("expect") or {}
        frame_index += _effective_cycle_count(step, case.id, case.yaml_path, field_path)
        terms = []
        if "state" in expect:
            observed_public_fields += 1
            terms.append(_expect_state_query(expect["state"]))
        if "ended" in expect:
            observed_public_fields += 1
            terms.append(_expect_ended_query(expect["ended"]))
        if "vars" in expect:
            observed_public_fields += 1
            terms.append(_expect_vars_query(expect["vars"]))
        if "vars_exact" in expect:
            observed_public_fields += 1
            terms.append(_expect_vars_query(expect["vars_exact"]))
        if "handler_calls" in expect and "handler_calls" not in ignored:
            observed_public_fields += 1
            terms.append(
                _expect_handler_calls_query(frame_index, expect["handler_calls"])
            )
        if terms:
            frame_clauses.append(
                "(cycle != %d || (%s))" % (frame_index, " && ".join(terms))
            )
    if observed_public_fields == 0:
        raise BmcBuildError(
            "%s has no public state/ended/vars expectation for BMC property alignment."
            % case.id
        )
    return " && ".join(frame_clauses) if frame_clauses else "true"


def _assert_semantic_fixture_matches_bmc_core(case, ignored_fields: Sequence[str]):
    bound, selected_events_by_step = _collect_runtime_trace(case)
    model = build_state_machine_from_case(case)
    query_text = _query_text_for_case(case, model, bound)
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

    property_predicate = _expectation_query_predicate(case, ignored_fields)
    property_query_text = _query_text_for_case(
        case,
        model,
        bound,
        check_clause="check invariant <= {bound}: %s;" % property_predicate,
    )
    property_core = build_bmc_core_formula(
        BmcEngine(model).prepare(property_query_text)
    )
    property_event_constraints = []
    for step_index, selected_events in enumerate(selected_events_by_step):
        property_event_constraints.extend(
            _event_constraints(property_core, step_index, selected_events)
        )
    objective = compile_bmc_property(property_core)
    assert (
        _solver(objective.solve_formula, *property_event_constraints).check()
        == z3.unsat
    )


def _assert_expected_unsupported(case) -> None:
    bound = sum(
        _effective_cycle_count(step, case.id, case.yaml_path, "steps[%d]" % index)
        for index, step in enumerate(case.data.get("steps") or [])
    )
    model = build_state_machine_from_case(case)
    query_text = _query_text_for_case(case, model, bound)
    with pytest.raises(UnsupportedBmcQuery, match="unsupported_bmc_core"):
        build_bmc_core_formula(BmcEngine(model).prepare(query_text))


@pytest.mark.unittest
def test_bmc_semantic_fixture_policy_covers_known_gap_inventory() -> None:
    cases = {case.id: case for case in iter_semantic_cases()}
    assert len(cases) >= 165
    assert BMC_CORE_FIXTURE_LEDGER_CASES <= set(cases)
    assert len(BMC_CORE_FIXTURE_LEDGER_CASES) == 40

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
    mode_counts = {
        mode: sum(1 for item in cases.values() if policy_for_case(item.id).mode == mode)
        for mode in _SUPPORTED_POLICY_MODES
    }
    assert mode_counts == {
        "hard_pass": 148,
        "partial": 0,
        "expected_unsupported": 3,
        "temporary_exclude": 10,
        "long_term_exclude": 4,
    }

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
