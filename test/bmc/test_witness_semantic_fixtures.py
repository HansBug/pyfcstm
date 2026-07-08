"""BMC witness replay alignment over shared semantic fixtures."""

from __future__ import annotations

import json
from typing import Iterable, List, Mapping, Sequence, Tuple

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import (
    BmcRuntimeFrame,
    BmcRuntimeStep,
    BmcRuntimeTrace,
    BmcWitnessCallRecord,
    _HandlerCallRecorder,
    _register_recorder,
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from test.bmc.semantic_fixture_policy import policy_for_case
from test.bmc.test_relation_semantic_fixtures import _query_text_for_case
from test.testings.simulate_semantics import (
    BMC_CORE_RUNNER,
    _cycle_input_for_step,
    _effective_cycle_count,
    _register_fixture_handlers,
    _simulation_kwargs,
    build_state_machine_from_case,
    is_runner_excluded,
    iter_semantic_cases,
)


pytestmark = pytest.mark.unittest


def _runtime_state(runtime) -> str:
    if runtime.is_ended:
        return None
    return ".".join(runtime.current_state.path)


def _runtime_frame(runtime, index: int) -> BmcRuntimeFrame:
    return BmcRuntimeFrame(
        index=index,
        state=_runtime_state(runtime),
        terminated=runtime.is_ended,
        vars=dict(runtime.vars),
    )


def _call_value(item: Mapping[str, object], field_name: str):
    defaults = {
        "active_leaf": item.get("state"),
        "call_stage": item.get("stage"),
        "abstract_target": item.get("action"),
        "named_ref": None,
    }
    return item.get(field_name, defaults.get(field_name))


def _fixture_call_record(
    index: int, item: Mapping[str, object]
) -> BmcWitnessCallRecord:
    return BmcWitnessCallRecord(
        ordinal=index,
        action_name=_call_value(item, "abstract_target"),
        stage=_call_value(item, "call_stage"),
        role="runtime_handler",
        state=item["state"],
        active_leaf=_call_value(item, "active_leaf"),
        named_ref=_call_value(item, "named_ref"),
        snapshot=dict(item.get("vars") or {}),
    )


def collect_simulation_trace_for_bmc_fixture(
    case,
) -> Tuple[BmcRuntimeTrace, Tuple[Tuple[str, ...], ...]]:
    """Collect a macro-observable SimulationRuntime trace for one fixture."""
    model = build_state_machine_from_case(case)
    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(model, **_simulation_kwargs(case))
    _register_fixture_handlers(runtime, case)
    recorder = _HandlerCallRecorder()
    _register_recorder(runtime, recorder, None)
    frames: List[BmcRuntimeFrame] = [_runtime_frame(runtime, 0)]
    steps: List[BmcRuntimeStep] = []
    event_inputs: List[Tuple[str, ...]] = []
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d]" % index
        expect = step.get("expect") or {}
        if "raises" in expect:
            raise AssertionError(
                "%s contains runtime exception expectations and must be excluded"
                % case.id
            )
        cycle_count = _effective_cycle_count(step, case.id, case.yaml_path, field_path)
        cycle_input = _cycle_input_for_step(step, case.id, case.yaml_path, field_path)
        for _ in range(cycle_count):
            before = len(recorder.calls)
            result = runtime.cycle(cycle_input)
            new_calls = tuple(
                BmcWitnessCallRecord(
                    ordinal=call_index,
                    action_name=item.action_name,
                    stage=item.stage,
                    role=item.role,
                    state=item.state,
                    active_leaf=item.active_leaf,
                    named_ref=item.named_ref,
                    snapshot=item.snapshot,
                )
                for call_index, item in enumerate(recorder.calls[before:])
            )
            step_index = len(steps)
            event_inputs.append(tuple(result.input_events))
            steps.append(
                BmcRuntimeStep(
                    index=step_index,
                    input_events=result.input_events,
                    consumed_events=result.consumed_events,
                    unconsumed_events=result.unconsumed_events,
                    abstract_calls=new_calls,
                )
            )
            frames.append(_runtime_frame(runtime, len(frames)))
    return BmcRuntimeTrace(tuple(frames), tuple(steps)), tuple(event_inputs)


def _model_event_paths(model) -> Tuple[str, ...]:
    paths = []
    for state in model.walk_states():
        for event in state.events.values():
            paths.append(event.path_name)
    return tuple(paths)


def _event_assumption_lines(
    event_paths: Sequence[str], event_inputs: Sequence[Iterable[str]]
) -> List[str]:
    lines = []
    event_path_set = set(event_paths)
    for step_index, inputs in enumerate(event_inputs):
        selected = set(inputs)
        for path in inputs:
            if path in event_path_set:
                lines.append(
                    "assume event(%s, %d) == true;"
                    % (json.dumps(path, ensure_ascii=False), step_index)
                )
        for path in event_paths:
            if path not in selected:
                lines.append(
                    "assume event(%s, %d) == false;"
                    % (json.dumps(path, ensure_ascii=False), step_index)
                )
    return lines


def _query_with_fixture_events(case, model, bound: int, event_inputs) -> str:
    query = _query_text_for_case(
        case,
        model,
        bound,
        check_clause="check reach <= {bound}: true;",
    )
    lines = [line for line in query.splitlines() if line.strip()]
    check_line = lines[-1]
    prefix = lines[:-1]
    return "\n".join(
        prefix
        + _event_assumption_lines(_model_event_paths(model), event_inputs)
        + [check_line]
    )


def _hard_pass_cases():
    cases = []
    for case in iter_semantic_cases():
        policy = policy_for_case(case.id)
        if policy.mode != "hard_pass":
            continue
        if is_runner_excluded(case, BMC_CORE_RUNNER):
            continue
        cases.append(case)
    return tuple(cases)


@pytest.mark.parametrize("case", _hard_pass_cases(), ids=lambda case: case.id)
def test_bmc_witness_replay_matches_full_semantic_fixture_trace(case) -> None:
    """Hard-pass semantic fixtures replay with full macro-observable parity."""
    expected_trace, event_inputs = collect_simulation_trace_for_bmc_fixture(case)
    model = build_state_machine_from_case(case)
    query = _query_with_fixture_events(case, model, len(event_inputs), event_inputs)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query))
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    witness = decode_bmc_witness(formula, result.model)
    replay = replay_bmc_witness(model, witness)
    assert replay.ok, [item.to_canonical() for item in replay.mismatches]
    if not event_inputs:
        # The current .fbmcq property bound is positive, while a few semantic
        # fixtures assert construction/hot-start state with ``cycle_count: 0``.
        # PR-12 can still verify that witness replay uses the correct public
        # constructor state and variables, but there is no zero-step property
        # witness to compare against yet.
        assert (
            replay.runtime_trace.frames[0].to_canonical()
            == expected_trace.frames[0].to_canonical()
        )
        return
    assert replay.runtime_trace.to_canonical() == expected_trace.to_canonical()


def test_bmc_witness_fixture_runner_keeps_policy_counts_auditable() -> None:
    """Witness replay inherits the BMC-core semantic fixture policy ledger."""
    mode_counts = {}
    for case in iter_semantic_cases():
        policy = policy_for_case(case.id)
        mode_counts[policy.mode] = mode_counts.get(policy.mode, 0) + 1
    assert mode_counts == {
        "hard_pass": 146,
        "expected_unsupported": 3,
        "temporary_exclude": 10,
        "long_term_exclude": 6,
    }
    assert len(_hard_pass_cases()) == 146
