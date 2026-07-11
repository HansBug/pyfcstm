"""BMC witness replay alignment over shared semantic fixtures."""

from __future__ import annotations

import json
from typing import Iterable, List, Sequence, Tuple

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import (
    BmcRuntimeFrame,
    BmcRuntimeStep,
    BmcRuntimeTrace,
    BmcWitnessCallRecord,
    _HandlerCallRecorder,
    _abstract_call_role_resolver,
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


def _bmc_presence_cycle_input(cycle_input):
    """Project a fixture cycle input onto ordered Boolean event presence."""
    if isinstance(cycle_input, list):
        return list(dict.fromkeys(cycle_input))
    return cycle_input


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


def collect_simulation_trace_for_bmc_fixture(
    case,
) -> Tuple[BmcRuntimeTrace, Tuple[Tuple[str, ...], ...]]:
    """Collect a macro-observable SimulationRuntime trace for one fixture."""
    model = build_state_machine_from_case(case)
    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(model, **_simulation_kwargs(case))
    _register_fixture_handlers(runtime, case)
    recorder = _HandlerCallRecorder(_abstract_call_role_resolver(model))
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
        cycle_input = _bmc_presence_cycle_input(
            _cycle_input_for_step(step, case.id, case.yaml_path, field_path)
        )
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
    """Hard-pass fixture traces are exact prefixes of decoded BMC replays."""
    expected_trace, event_inputs = collect_simulation_trace_for_bmc_fixture(case)
    assert all(len(inputs) == len(set(inputs)) for inputs in event_inputs)
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
    fixture_prefix = BmcRuntimeTrace(
        replay.runtime_trace.frames[: len(expected_trace.frames)],
        replay.runtime_trace.steps[: len(expected_trace.steps)],
    )
    assert fixture_prefix.to_canonical() == expected_trace.to_canonical()


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
    zero_step_ids = set()
    for case in _hard_pass_cases():
        cycle_count = 0
        for index, step in enumerate(case.data.get("steps") or []):
            cycle_count += _effective_cycle_count(
                step,
                case.id,
                case.yaml_path,
                "steps[%d]" % index,
            )
        if cycle_count == 0:
            zero_step_ids.add(case.id)
    assert zero_step_ids == {"persistent_initial_vars_override_skips_initializer"}


def test_duplicate_event_fixture_uses_boolean_presence_without_exclusion() -> None:
    """The duplicate-input fixture keeps coverage after presence projection."""
    case = next(
        item
        for item in iter_semantic_cases()
        if item.id == "event_duplicate_inputs_preserve_public_state"
    )
    raw_cycle_input = _cycle_input_for_step(
        case.data["steps"][1],
        case.id,
        case.yaml_path,
        "steps[1]",
    )
    assert raw_cycle_input == [
        "Root.A.Tick",
        "Root.A.Noise",
        "Root.A.Tick",
    ]
    assert policy_for_case(case.id).mode == "hard_pass"
    assert is_runner_excluded(case, BMC_CORE_RUNNER) is False

    expected_trace, event_inputs = collect_simulation_trace_for_bmc_fixture(case)

    assert event_inputs == ((), ("Root.A.Tick", "Root.A.Noise"))
    assert expected_trace.steps[1].to_canonical() == {
        "index": 1,
        "input_events": ["Root.A.Tick", "Root.A.Noise"],
        "consumed_events": ["Root.A.Tick"],
        "unconsumed_events": ["Root.A.Noise"],
        "abstract_calls": [],
    }

    model = build_state_machine_from_case(case)
    query = _query_with_fixture_events(case, model, len(event_inputs), event_inputs)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query))
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"

    witness = decode_bmc_witness(formula, result.model)
    replay = replay_bmc_witness(model, witness)

    assert witness.steps[1].input_event_paths == ("Root.A.Tick", "Root.A.Noise")
    assert [item.to_canonical() for item in witness.steps[1].input_events] == [
        {
            "path": "Root.A.Tick",
            "reason": "explicit_true_assumption",
            "model_value": True,
        },
        {
            "path": "Root.A.Noise",
            "reason": "explicit_true_assumption",
            "model_value": True,
        },
    ]
    assert witness.steps[1].consumed_events == ("Root.A.Tick",)
    assert witness.steps[1].unconsumed_events == ("Root.A.Noise",)
    assert replay.ok is True
    assert replay.runtime_trace.to_canonical() == expected_trace.to_canonical()
