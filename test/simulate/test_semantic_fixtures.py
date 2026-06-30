import os

import pytest
import yaml

from test.testings.simulate_semantics import (
    SemanticCaseError,
    iter_semantic_cases,
    load_semantic_case,
    run_simulation_case,
    validate_shared_fixture_contract,
)


@pytest.mark.unittest
def test_all_semantic_fixtures_load():
    cases = iter_semantic_cases()

    assert len(cases) >= 140
    assert {case.id for case in cases}


@pytest.mark.unittest
def test_generated_alignment_fixture_baseline_counts():
    """
    Guard generated-alignment fixture coverage baselines.

    The checks are intentionally lower-bound and identity based: they prevent
    silently dropping the semantic harness inputs while allowing later template
    repairs to add more fixtures.
    """
    cases = iter_semantic_cases()
    generated_cases = [
        case for case in cases if "generated_python_alignment" in case.runners
    ]
    generated_handler_cases = [
        case for case in generated_cases if case.data.get("handlers")
    ]

    assert len(cases) >= 140
    assert len(generated_cases) >= 90
    assert {case.id for case in generated_handler_cases} >= {
        "failed_initial_cycle_skips_abstract_handler_callbacks",
        "ref_abstract_handler_reports_calling_state",
    }


@pytest.mark.unittest
def test_generated_alignment_cases_share_the_simulation_fixture_corpus():
    """
    Guard simulator and generated-runtime alignment against fixture drift.

    Generated Python alignment is a runner adapter over the shared semantic
    corpus, not a separate fixture system. Every generated-alignment case must
    also be executable by the simulator runner so both sides consume the same
    DSL, handlers, cycle inputs, and expectation shape.
    """
    generated_cases = iter_semantic_cases(runners=["generated_python_alignment"])

    assert generated_cases
    assert all("simulation" in case.runners for case in generated_cases)


@pytest.mark.unittest
def test_generated_alignment_regression_fixtures_remain_shared():
    """
    Guard simulator/generated-runtime alignment coverage against drift.

    The fixture ids below are the stable behavior-facing regression set that
    covers composite entry ordering, pseudo validation, hot starts, persistent
    value normalization, abstract hook context, generated naming, expression
    rendering, packaged-template smoke, and documented event path inputs.
    """
    required_case_ids = {
        "composite_initial_guard_uses_enter_state_before_plain_before",
        "composite_initial_guard_with_effect_runs_before_plain_before",
        "forced_pseudo_candidate_skips_unstable_branch",
        "pseudo_candidate_skips_unstable_branch",
        "pseudo_self_loop_step_limit_raises_dfs_error",
        "hot_start_composite_waits_for_initial_event",
        "hot_start_evented_initial_matches_cold_suffix",
        "hot_start_deep_evented_initial_waits_for_event",
        "hot_start_rejects_overdeep_leaf_stack",
        "persistent_default_int_initializer_normalizes_integer_float",
        "persistent_int_writeback_normalizes_integer_float",
        "persistent_initial_vars_override_skips_initializer",
        "hot_start_initial_vars_override_skips_int_initializer",
        "abstract_hook_ref_context_reports_callsite_metadata",
        "ref_abstract_handler_reports_calling_state",
        "lifecycle_ref_chain_resolves_long_acyclic_chain",
        "similar_state_paths_keep_actions_distinct",
        "sign_function_handles_all_signs",
        "sign_function_controls_guard_transition",
        "sign_function_updates_during_action",
        "sign_function_aligns_aspect_guard_effect_math",
        "sign_function_preserves_complex_action_precedence",
        "event_path_absolute",
        "event_path_parent_relative",
        "event_path_mixed_formats_full",
        "combo_transition_trigger_cross_layer_exit_alignment",
        "combo_transition_trigger_duplicate_event_alignment",
        "combo_transition_trigger_exit_guard_mutation_alignment",
        "combo_transition_trigger_guard_pseudo_aspect_alignment",
        "combo_transition_trigger_entry_fallback_alignment",
        "combo_transition_trigger_exit_continuation_rollback_alignment",
        "combo_transition_trigger_exit_fallback_alignment",
        "combo_transition_trigger_fence_prefix_guard_alignment",
        "combo_transition_trigger_identical_priority_alignment",
        "combo_transition_trigger_lifecycle_alignment",
        "combo_transition_trigger_pseudo_aspect_alignment",
        "combo_transition_trigger_root_exit_alignment",
        "combo_transition_trigger_prefix_order_alignment",
        "combo_transition_trigger_priority_scope_alignment",
        "combo_transition_trigger_rollback_alignment",
        "combo_transition_trigger_template_alignment",
        "combo_transition_trigger_unstable_predecessor_alignment",
    }
    cases = {case.id: case for case in iter_semantic_cases()}

    assert required_case_ids <= set(cases)
    for case_id in required_case_ids:
        assert cases[case_id].runners == (
            "simulation",
            "generated_python_alignment",
        )
        assert cases[case_id].data.get("origin", {}).get("files")


@pytest.mark.unittest
def test_semantic_fixture_assertion_families_are_executable():
    cases = iter_semantic_cases(runners=["simulation"])
    covered = set()
    for case in cases:
        for step in case.data.get("steps") or []:
            expect = step.get("expect") or {}
            if "ended" in expect:
                covered.add("ended")
            if "state" in expect:
                covered.add("current_state")
            if any(
                field in expect
                for field in ("vars", "vars_exact", "vars_keys", "vars_absent")
            ):
                covered.add("vars")
            cycle_count = step.get("cycle_count", 1)
            cycle_input = step.get("cycle", [])
            if cycle_count > 0 and cycle_input:
                covered.add("events")
            if "raises" in expect:
                covered.add("exception")
            if "handler_calls" in expect:
                covered.add("context")
        initial_expect = (case.data.get("initial") or {}).get("expect") or {}
        if "raises" in initial_expect:
            covered.add("constructor_exception")

    assert {
        "ended",
        "current_state",
        "vars",
        "events",
        "exception",
        "context",
        "constructor_exception",
    }.issubset(covered)


@pytest.mark.unittest
def test_generated_alignment_constructor_outcome_helper_covers_three_modes():
    from test.testings import simulate_semantics
    from test.testings.simulate_semantics import SemanticCase

    case = SemanticCase(
        data={"title": "constructor outcome helper"},
        yaml_path="/tmp/constructor_outcome_helper.yaml",
        fcstm_path="/tmp/constructor_outcome_helper.fcstm",
        dsl_code="state Root { state A; [*] -> A; }",
    )
    expect = {
        "raises": {
            "type": "ValueError",
            "match": "boom",
            "match_kind": "substring",
        }
    }

    simulate_semantics._assert_aligned_constructor_outcome(
        case, None, object(), None, object(), None
    )
    simulate_semantics._assert_aligned_constructor_outcome(
        case, expect, None, ValueError("boom"), None, ValueError("boom")
    )
    simulate_semantics._assert_aligned_constructor_outcome(
        case,
        expect,
        None,
        ValueError("simulation boom details"),
        None,
        ValueError("generated boom details"),
    )
    simulation_runtime, simulation_err = simulate_semantics._capture_construction(
        lambda: (_ for _ in ()).throw(
            simulate_semantics.SimulationRuntimeDfsError("dfs")
        )
    )
    assert simulation_runtime is None
    assert isinstance(simulation_err, simulate_semantics.SimulationRuntimeDfsError)

    generated_dfs_error = type("SimulationRuntimeDfsError", (RuntimeError,), {})
    generated_runtime, generated_err = simulate_semantics._capture_construction(
        lambda: (_ for _ in ()).throw(generated_dfs_error("generated dfs"))
    )
    assert generated_runtime is None
    assert type(generated_err).__name__ == "SimulationRuntimeDfsError"

    with pytest.raises(AssertionError, match="constructor one-sided mismatch"):
        simulate_semantics._assert_aligned_constructor_outcome(
            case, None, object(), None, None, ValueError("boom")
        )
    with pytest.raises(AssertionError, match="constructor failed unexpectedly"):
        simulate_semantics._assert_aligned_constructor_outcome(
            case, None, None, ValueError("boom"), None, ValueError("boom")
        )
    with pytest.raises(AssertionError, match="expected constructor failure"):
        simulate_semantics._assert_aligned_constructor_outcome(
            case, expect, object(), None, object(), None
        )


@pytest.mark.unittest
def test_initial_vars_override_fixture_runs_generated_alignment_contract():
    case = load_semantic_case("persistent_initial_vars_override_skips_initializer")

    assert case.runners == ("simulation", "generated_python_alignment")
    assert case.data["initial"]["state"] == "Root.A"
    assert case.data["initial"]["vars"] == {"recovered": 5.0}
    assert "hot_start" in case.data["categories"]
    assert "template_alignment" in case.data["categories"]


@pytest.mark.unittest
def test_generated_alignment_handler_metadata_mapping_is_available():
    case = load_semantic_case("ref_abstract_handler_reports_calling_state")
    call = case.data["steps"][0]["expect"]["handler_calls"][0]

    assert "generated_python_alignment" in case.runners
    assert case.data["handlers"] == [
        {"action": "Root.Library.Shared", "behavior": "record_call"}
    ]
    assert {
        "action": "Root.Library.Shared",
        "state": "Root.A",
        "stage": "enter",
        "vars": {},
    }.items() <= call.items()


@pytest.mark.unittest
def test_semantic_fixture_origin_files_cover_existing_simulate_tests():
    expected_files = {
        "test_abstract_handlers.py",
        "test_cli_init.py",
        "test_completer_init.py",
        "test_decorators.py",
        "test_event_inputs.py",
        "test_handler_decorator.py",
        "test_hot_start.py",
        "test_hot_start_edge_cases.py",
        "test_semantic_fixtures.py",
        "test_utils.py",
    }
    actual_files = {
        name
        for name in os.listdir(os.path.dirname(__file__))
        if name.startswith("test_") and name.endswith(".py")
    }
    assert expected_files.issubset(actual_files)

    representative_cases = {
        "stable_leaf_cycle_updates_public_state",
        "event_transition_updates_public_state",
        "event_duplicate_inputs_preserve_public_state",
        "expression_error_preserves_runtime_snapshot",
        "abstract_handler_context_metadata",
    }
    cases = [case for case in iter_semantic_cases() if case.id in representative_cases]
    assert {case.id for case in cases} == representative_cases
    origin_files = {
        origin
        for case in cases
        for origin in case.data.get("origin", {}).get("files", [])
    }
    assert origin_files == {
        "test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture"
    }


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    [case for case in iter_semantic_cases(runners=["simulation"])],
    ids=lambda case: case.id,
)
def test_simulation_semantic_fixture(case):
    run_simulation_case(case)


def _write_fixture(tmp_path, data, fcstm="state Root { state A; [*] -> A; }"):
    yaml_path = tmp_path / "bad.yaml"
    fcstm_path = tmp_path / "bad.fcstm"
    fcstm_path.write_text(fcstm, encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return str(yaml_path)


def _valid_case_data():
    return {
        "title": "Bad fixture used by schema tests",
        "origin": {"files": ["test/example.py::test_example"]},
        "categories": ["runtime"],
        "steps": [
            {
                "cycle": [],
                "expect": {
                    "state": "Root.A",
                    "ended": False,
                },
            },
        ],
    }


def _set_expected_raises(data, raises):
    data["steps"][0]["expect"]["raises"] = raises


def _shared_case_data():
    """Return the minimal valid fixture shape for current shared contract tests."""
    return _valid_case_data()


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["mutate", "message"],
    [
        (lambda data: data.update({"unexpected": True}), "unknown top-level fields"),
        (lambda data: data.update({"schema_version": 2}), "unknown top-level fields"),
        (lambda data: data.update({"id": "bad"}), "unknown top-level fields"),
        (
            lambda data: data.update({"source": {"fcstm": "bad.fcstm"}}),
            "unknown top-level fields",
        ),
        (lambda data: data.update({"boundary": "shared"}), "unknown top-level fields"),
        (
            lambda data: data.update({"runners": ["simulation"]}),
            "unknown top-level fields",
        ),
        (lambda data: data.update({"commands": []}), "unknown top-level fields"),
        (
            lambda data: data.update(
                {"runtime_options": {"abstract_error_mode": "log"}}
            ),
            "unknown top-level fields",
        ),
        (
            lambda data: data.update(
                {
                    "model_build": {
                        "expect": {"raises": {"type": "ModelValidationError"}}
                    }
                }
            ),
            "unknown top-level fields",
        ),
        (
            lambda data: data.update({"expected_failure": {"reason": "known bug"}}),
            "unknown top-level fields",
        ),
        (
            lambda data: data["origin"].update({"extra": "x"}),
            "origin has unknown fields",
        ),
        (
            lambda data: data["origin"].update({"assertion_types": ["state"]}),
            "origin has unknown fields",
        ),
        (lambda data: data.update({"categories": ["unknown"]}), "unknown categories"),
        (
            lambda data: data.update({"exclude_runners": ["unknown"]}),
            "exclude_runners has unknown runners",
        ),
        (
            lambda data: data.update({"exclude_runners": "simulation"}),
            "exclude_runners must be a non-empty list",
        ),
        (
            lambda data: data.update({"exclude_runners": []}),
            "exclude_runners must be a non-empty list",
        ),
        (
            lambda data: data.update({"exclude_runners": ["simulation", 1]}),
            "exclude_runners must be a list of strings",
        ),
        (
            lambda data: data.update(
                {"exclude_runners": ["generated_python_alignment"] * 2}
            ),
            "exclude_runners has duplicate runners",
        ),
        (
            lambda data: data.update({"exclude_runners": ["simulation"]}),
            "generated_python_alignment requires the simulation runner",
        ),
        (
            lambda data: data.update(
                {"exclude_runners": ["simulation", "generated_python_alignment"]}
            ),
            "exclude_runners cannot remove all default runners",
        ),
        (
            lambda data: data.update({"handlers": "Root.Init"}),
            "handlers must be a list",
        ),
        (
            lambda data: data.update({"handlers": [{"action": "Root.Init"}]}),
            "handlers\\[0\\].behavior is required",
        ),
        (
            lambda data: data.update(
                {"handlers": [{"action": "Root.Init", "behavior": "unknown_behavior"}]}
            ),
            "handlers\\[0\\].behavior is invalid",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "record_call",
                            "exception": {"type": "ValueError"},
                        }
                    ]
                }
            ),
            "handlers\\[0\\] has unknown fields",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "record_var_write_attempt",
                        }
                    ]
                }
            ),
            "handlers\\[0\\].behavior is invalid",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {"action": "Root.Init", "behavior": "record_call", "write": {}}
                    ]
                }
            ),
            "handlers\\[0\\] has unknown fields",
        ),
        (
            lambda data: data.update({"initial": {"unexpected": True}}),
            "initial has unknown fields",
        ),
        (
            lambda data: data.update({"initial": {"state": ["Root", "A"]}}),
            "initial.state must be a dot-separated state path string or null",
        ),
        (
            lambda data: data.update(
                {"initial": {"state": "Root.A", "vars": {}, "expect": {"return": None}}}
            ),
            "initial.expect has unknown fields",
        ),
        (
            lambda data: data.update(
                {"initial": {"vars": {}, "expect": {"raises": {"type": "ValueError"}}}}
            ),
            "initial.expect requires initial.state",
        ),
        (
            lambda data: data.update(
                {
                    "initial": {
                        "state": "Root.A",
                        "expect": {"raises": {"type": "ValueError"}},
                    }
                }
            ),
            "initial.expect requires initial.vars",
        ),
        (
            lambda data: data.update(
                {
                    "initial": {
                        "state": "Root.A",
                        "vars": {},
                        "expect": {"raises": {"type": "UnknownError"}},
                    }
                }
            ),
            "initial.expect.raises.type is unknown",
        ),
        (
            lambda data: data.update(
                {
                    "initial": {
                        "state": "Root.A",
                        "vars": {},
                        "expect": {"raises": {"type": "ValueError"}},
                    }
                }
            ),
            "initial.expect.raises cases require empty steps",
        ),
        (lambda data: data.update({"steps": "bad"}), "steps must be a list"),
        (lambda data: data.update({"steps": []}), "requires non-empty steps"),
        (
            lambda data: data["steps"][0].update({"unknown_step": True}),
            "steps\\[0\\] has unknown fields",
        ),
        (
            lambda data: data["steps"][0].pop("cycle"),
            "steps\\[0\\] must contain cycle or cycle_count",
        ),
        (
            lambda data: data["steps"][0].pop("expect"),
            "steps\\[0\\].expect is required",
        ),
        (
            lambda data: data["steps"][0].update(
                {"expect_initial": {"state": "Root.A"}}
            ),
            "steps\\[0\\] has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"unknown_expect": True}),
            "unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars": {"x": 1}, "vars_exact": {"x": 1}}
            ),
            "vars and vars_exact conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars_exact": {"x": 1}, "vars_keys": ["x"]}
            ),
            "vars_exact and vars_keys conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars_exact": {"x": 1}, "vars_absent": ["tmp"]}
            ),
            "vars_exact and vars_absent conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars_keys": ["tmp"], "vars_absent": ["tmp"]}
            ),
            "vars_keys and vars_absent overlap",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"state": ["Root", "A"]}),
            "state must be a dot-separated state path string or null",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"state": None, "ended": False}
            ),
            "state and ended conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"state": "Root.A", "ended": True}
            ),
            "state and ended conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"ended": "false"}),
            "ended must be a boolean",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"cycle_result": {"value": None}}
            ),
            "unknown fields",
        ),
        (
            lambda data: _set_expected_raises(data, {"type": "UnknownError"}),
            "raises.type is unknown",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "cause_type": 1}
            ),
            "raises.cause_type must be a string",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "cause_match": 1}
            ),
            "raises.cause_match must be a string",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "cause_match_kind": "bad"}
            ),
            "raises.cause_match_kind is invalid",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "cause_match_kind": "regex"}
            ),
            "raises.cause_match_kind requires cause_match",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "matc": "typo"}
            ),
            "raises has unknown fields",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": {}}),
            "cycle: {} is not valid v2",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": None}),
            "cycle: null is not valid v2",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": {"events": ["Root.A.Go"]}}),
            "cycle.events is not valid v2",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": [{"event": "Root.A.Go"}]}),
            r"cycle\[0\] must be a string event path",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": 12}),
            "cycle must be a string event path or a list of string event paths",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": [7]}),
            r"cycle\[0\] must be a string event path",
        ),
        (
            lambda data: data["steps"][0].update({"cycle_count": True}),
            "cycle_count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0].update({"cycle_count": 1.5}),
            "cycle_count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0].update({"cycle_count": "1"}),
            "cycle_count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0].update({"cycle_count": -1}),
            "cycle_count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0].update(
                {"cycle": "Root.A.Go", "cycle_count": 0}
            ),
            "cycle_count: 0 cannot have non-empty cycle",
        ),
        (
            lambda data: (
                data["steps"][0].update({"cycle_count": 0})
                or _set_expected_raises(data, {"type": "ValueError"})
            ),
            "expect.raises requires effective cycle_count == 1",
        ),
        (
            lambda data: (
                data["steps"][0].update({"cycle_count": 2})
                or _set_expected_raises(data, {"type": "ValueError"})
            ),
            "expect.raises requires effective cycle_count == 1",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"handler_calls": {"action": "Root.Init"}}
            ),
            "handler_calls must be a list",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"handler_calls": [{"action": "Root.Init"}]}
            ),
            "handler_calls\\[0\\] missing fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {
                    "handler_calls": [
                        {
                            "action": "Root.Init",
                            "state": "Root",
                            "stage": "enter",
                            "vars": {},
                            "write_attempt": {"name": "x"},
                        }
                    ]
                }
            ),
            "handler_calls\\[0\\] has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {
                    "handler_calls": [
                        {
                            "action": "Root.Init",
                            "state": "Root",
                            "stage": "enter",
                            "vars": {},
                            "active_leaf": ["Root"],
                        }
                    ]
                }
            ),
            "active_leaf must be a dot-separated state path string or null",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"handler_calls": []}),
            "handler_calls requires top-level handlers",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history_tail": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history_length": 0}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"brief_stack": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"cycle_count": 1}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"return": None}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"input_events": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"consumed_events": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"unconsumed_events": []}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"warnings": {"count": 0}}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"logs": {"contains": [{"message": "x"}]}}
            ),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"abstract_handler_errors": []}
            ),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"error_state": False}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"error_info": None}),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"anonymous_warning_count": 0}
            ),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"output_contains": "Commands"}
            ),
            "has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"should_exit": "false"}),
            "has unknown fields",
        ),
    ],
)
def test_semantic_fixture_schema_rejects_invalid_yaml(tmp_path, mutate, message):
    data = _valid_case_data()
    mutate(data)
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match=message):
        load_semantic_case(yaml_path)


@pytest.mark.unittest
def test_shared_fixture_accepts_public_observations(tmp_path):
    data = _shared_case_data()
    data["handlers"] = [{"action": "Root.Init", "behavior": "record_call"}]
    data["steps"][0]["expect"]["handler_calls"] = [
        {
            "action": "Root.Init",
            "state": "Root",
            "stage": "enter",
            "vars": {},
            "active_leaf": "Root",
            "call_stage": "enter",
            "abstract_target": "Root.Init",
            "named_ref": None,
        }
    ]
    yaml_path = _write_fixture(tmp_path, data)

    load_semantic_case(yaml_path)
    validate_shared_fixture_contract(data, yaml_path)


@pytest.mark.unittest
def test_shared_fixture_accepts_initial_constructor_observation(tmp_path):
    data = _shared_case_data()
    data["steps"] = []
    data["initial"] = {
        "state": "Root.A",
        "vars": {},
        "expect": {"raises": {"type": "ValueError"}},
    }
    yaml_path = _write_fixture(tmp_path, data)

    load_semantic_case(yaml_path)
    validate_shared_fixture_contract(data, yaml_path)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "field_name",
    [
        "input_events",
        "consumed_events",
        "unconsumed_events",
        "event_accounting",
        "event_ledger",
        "event_log",
    ],
)
def test_shared_fixture_contract_rejects_event_accounting_fields(tmp_path, field_name):
    data = _shared_case_data()
    data["steps"][0]["expect"][field_name] = []
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match="has unknown fields"):
        validate_shared_fixture_contract(data, yaml_path)


@pytest.mark.unittest
def test_shared_fixture_corpus_uses_public_observation_fields():
    disallowed_top_level_fields = {
        "boundary",
        "id",
        "schema_version",
        "source",
        "runners",
        "model_build",
        "commands",
        "runtime_options",
        "expected_failure",
    }
    disallowed_observation_fields = {
        "stack",
        "brief_stack",
        "cycle_count",
        "return",
        "cycle_result",
        "input_events",
        "consumed_events",
        "unconsumed_events",
        "event_accounting",
        "event_ledger",
        "event_log",
        "history",
        "history_tail",
        "history_length",
        "warnings",
        "logs",
        "abstract_handler_errors",
        "error_state",
        "error_info",
        "anonymous_warning_count",
        "output_contains",
        "output_not_contains",
        "error_contains",
        "should_exit",
    }
    cases = list(iter_semantic_cases())
    top_level_hits = {
        field
        for case in cases
        for field in case.data
        if field in disallowed_top_level_fields
    }
    observation_hits = {
        field
        for case in cases
        for step in case.data.get("steps") or []
        for expect in (step.get("expect"),)
        if isinstance(expect, dict)
        for field in expect
        if field in disallowed_observation_fields
    }
    initial_hits = {
        field
        for case in cases
        for field in ((case.data.get("initial") or {}).get("expect") or {})
        if field in disallowed_observation_fields
    }

    assert cases
    assert top_level_hits == set()
    assert observation_hits == set()
    assert initial_hits == set()
    assert [case.id for case in cases if case.runners == ("simulation",)] == []


@pytest.mark.unittest
def test_shared_fixture_corpus_satisfies_current_contract():
    cases = list(iter_semantic_cases())

    for case in cases:
        validate_shared_fixture_contract(case.data, case.yaml_path)

    assert cases
    assert all("boundary" not in case.data for case in cases)
    assert all("id" not in case.data for case in cases)
    assert all("schema_version" not in case.data for case in cases)
    assert all("source" not in case.data for case in cases)
    assert all("runners" not in case.data for case in cases)
    assert all(
        case.runners == ("simulation", "generated_python_alignment") for case in cases
    )
    assert all("exclude_runners" not in case.data for case in cases)


@pytest.mark.unittest
def test_shared_fixture_uses_exclude_only_runner_selection(tmp_path):
    data = _shared_case_data()
    yaml_path = _write_fixture(tmp_path, data)

    case = load_semantic_case(yaml_path)

    assert case.runners == ("simulation", "generated_python_alignment")


@pytest.mark.unittest
def test_shared_fixture_can_exclude_generated_alignment(tmp_path):
    data = _shared_case_data()
    data["exclude_runners"] = ["generated_python_alignment"]
    yaml_path = _write_fixture(tmp_path, data)

    case = load_semantic_case(yaml_path)

    assert case.runners == ("simulation",)


@pytest.mark.unittest
def test_semantic_fixture_schema_reports_case_id_and_path(tmp_path):
    data = _valid_case_data()
    data["steps"][0]["expect"]["stack"] = [{"path": ["Root"], "mode": "bad"}]
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError) as exc_info:
        load_semantic_case(yaml_path)

    message = str(exc_info.value)
    assert "bad" in message
    assert os.path.abspath(yaml_path) in message
