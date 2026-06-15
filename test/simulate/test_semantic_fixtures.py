import os

import pytest
import yaml

from test.testings.simulate_semantics import (
    SemanticCaseError,
    iter_semantic_cases,
    load_semantic_case,
    run_cli_command_case,
    run_simulation_case,
    validate_pure_shared_fixture_boundary,
)


@pytest.mark.unittest
def test_all_semantic_fixtures_load():
    cases = iter_semantic_cases()

    assert len(cases) >= 139
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
    expected_failure_cases = [case for case in cases if "expected_failure" in case.data]
    generated_handler_cases = [
        case for case in generated_cases if case.data.get("handlers")
    ]

    assert len(cases) >= 139
    assert len(generated_cases) >= 90
    assert expected_failure_cases == []
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
        if case.data.get("model_build"):
            continue
        for step in case.data.get("steps") or []:
            expect = step.get("expect_initial") or step.get("expect") or {}
            if "ended" in expect:
                covered.add("ended")
            if "stack" in expect:
                covered.add("stack")
            if "state" in expect:
                covered.add("current_state")
            if any(
                field in expect
                for field in ("vars", "vars_exact", "vars_keys", "vars_absent")
            ):
                covered.add("vars")
            if any(
                field in expect
                for field in ("history", "history_length", "history_tail")
            ):
                covered.add("history")
            if step.get("cycle") not in (None, {}) and "events" in step.get(
                "cycle", {}
            ):
                covered.add("events")
            if "cycle_result" in expect:
                covered.add("cycle_result")
            if "raises" in expect:
                covered.add("exception")
            if "handler_calls" in expect:
                covered.add("context")

    assert {
        "stack",
        "ended",
        "current_state",
        "vars",
        "history",
        "events",
        "cycle_result",
        "exception",
        "context",
    }.issubset(covered)


@pytest.mark.unittest
def test_generated_alignment_constructor_outcome_helper_covers_three_modes():
    from test.testings import simulate_semantics
    from test.testings.simulate_semantics import SemanticCase

    case = SemanticCase(
        data={
            "id": "constructor_outcome_helper",
            "runners": ["simulation", "generated_python_alignment"],
        },
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
    assert "initial" in case.data["origin"]["assertion_types"]
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
        "cycle_result_history_stable_leaf",
        "cycle_result_history_event_transition",
        "cycle_result_event_accounting",
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
def test_simulation_semantic_fixture(case, caplog):
    run_simulation_case(case, caplog=caplog)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    [case for case in iter_semantic_cases(runners=["cli_command"])],
    ids=lambda case: case.id,
)
def test_cli_command_semantic_fixture(case):
    run_cli_command_case(case)


def _write_fixture(tmp_path, data, fcstm="state Root { state A; [*] -> A; }"):
    yaml_path = tmp_path / ("%s.yaml" % data.get("id", "bad"))
    fcstm_name = data.get("source", {}).get("fcstm", "bad.fcstm")
    (tmp_path / fcstm_name).write_text(fcstm, encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return str(yaml_path)


def _valid_case_data():
    return {
        "schema_version": 1,
        "id": "bad",
        "title": "Bad fixture used by schema tests",
        "source": {"fcstm": "bad.fcstm"},
        "origin": {"files": ["test/example.py::test_example"]},
        "categories": ["runtime"],
        "runners": ["simulation"],
        "initial": {"state": None, "vars": None},
        "steps": [
            {
                "cycle": {},
                "expect": {
                    "state": ["Root", "A"],
                    "ended": False,
                    "return": None,
                },
            },
        ],
    }


def _set_expected_raises(data, raises):
    data["steps"][0]["expect"].pop("return", None)
    data["steps"][0]["expect"]["raises"] = raises


def _set_cli_expectation(data, expect):
    data["categories"] = ["cli"]
    data["runners"] = ["cli_command"]
    data.pop("steps", None)
    data["commands"] = [{"input": "help", "expect": expect}]


def _set_generated_alignment(data):
    data["runners"] = ["simulation", "generated_python_alignment"]


def _set_model_build_expectation(data, raises):
    data.pop("steps", None)
    data["model_build"] = {"expect": {"raises": raises}}


def _pure_shared_case_data():
    """Return the minimal valid fixture shape for pure shared boundary tests."""
    data = _valid_case_data()
    data["boundary"] = "pure_shared"
    data["runners"] = ["simulation", "generated_python_alignment"]
    data["steps"][0]["expect"].pop("return", None)
    data["steps"][0]["expect"]["cycle_result"] = {"value": None}
    return data


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["mutate", "message"],
    [
        (lambda data: data.update({"unexpected": True}), "unknown top-level fields"),
        (lambda data: data.update({"boundary": "legacy"}), "unknown boundary"),
        (lambda data: data["source"].pop("fcstm"), "source.fcstm is required"),
        (
            lambda data: data.update({"commands": []}),
            "exactly one of model_build, steps, or commands is required",
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
            "handlers\\[0\\].exception is only allowed for raise_error",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "raise_error",
                            "exception": {"type": "KeyError"},
                        }
                    ]
                }
            ),
            "handlers\\[0\\].exception.type is invalid",
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
            "handlers\\[0\\].write must be a mapping",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "record_var_write_attempt",
                            "write": {"name": "x", "value": 1, "extra": True},
                        }
                    ]
                }
            ),
            "handlers\\[0\\].write has unknown fields",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "record_var_write_attempt",
                            "write": {"value": 1},
                        }
                    ]
                }
            ),
            "handlers\\[0\\].write.name is required",
        ),
        (
            lambda data: (
                data.update({"runners": ["cli_command"]})
                or data.update(
                    {"handlers": [{"action": "Root.Init", "behavior": "record_call"}]}
                )
            ),
            "handlers require the simulation runner",
        ),
        (
            lambda data: data.update({"runtime_options": {"unknown": "value"}}),
            "runtime_options has unknown fields",
        ),
        (
            lambda data: data.update(
                {"runtime_options": {"abstract_error_mode": "unknown"}}
            ),
            "runtime_options.abstract_error_mode is invalid",
        ),
        (
            lambda data: (
                _set_generated_alignment(data)
                or data.update({"runtime_options": {"abstract_error_mode": "log"}})
            ),
            "runtime_options are only supported by simulation-only cases",
        ),
        (
            lambda data: data.update({"expected_failure": {"reason": "known bug"}}),
            "expected_failure is reserved",
        ),
        (lambda data: data.update({"runners": ["unknown"]}), "unknown runners"),
        (
            lambda data: data.update({"runners": ["generated_python_alignment"]}),
            "generated_python_alignment requires the simulation runner",
        ),
        (
            lambda data: _set_model_build_expectation(data, {"type": "UnknownError"}),
            "model_build.expect.raises.type is unknown",
        ),
        (
            lambda data: _set_model_build_expectation(
                data, {"type": "SimulationRuntimeDfsError"}
            ),
            "model_build.expect.raises.type must be ModelValidationError",
        ),
        (
            lambda data: (
                _set_model_build_expectation(data, {"type": "ModelValidationError"})
                or data.update(
                    {"runners": ["simulation", "generated_python_alignment"]}
                )
            ),
            "model_build is only supported by simulation-only cases",
        ),
        (
            lambda data: (
                _set_model_build_expectation(data, {"type": "ModelValidationError"})
                or data.update({"runners": ["cli_command"]})
            ),
            "model_build is only supported by simulation-only cases",
        ),
        (
            lambda data: (
                _set_model_build_expectation(data, {"type": "ModelValidationError"})
                or data.update({"steps": []})
            ),
            "exactly one of model_build, steps, or commands is required",
        ),
        (
            lambda data: data.update({"model_build": {"expect": {"return": None}}}),
            "model_build.expect has unknown fields",
        ),
        (
            lambda data: data["initial"].update({"unexpected": True}),
            "initial has unknown fields",
        ),
        (
            lambda data: data["initial"].update(
                {
                    "state": "Root.A",
                    "vars": {},
                    "expect": {"return": None},
                }
            ),
            "initial.expect has unknown fields",
        ),
        (
            lambda data: (
                data["initial"].pop("state")
                or data["initial"].update(
                    {
                        "vars": {},
                        "expect": {"raises": {"type": "ValueError"}},
                    }
                )
            ),
            "initial.expect requires initial.state",
        ),
        (
            lambda data: (
                data["initial"].pop("vars")
                or data["initial"].update(
                    {
                        "state": "Root.A",
                        "expect": {"raises": {"type": "ValueError"}},
                    }
                )
            ),
            "initial.expect requires initial.vars",
        ),
        (
            lambda data: data["initial"].update(
                {"expect": {"raises": {"type": "UnknownError"}}}
            ),
            "initial.expect.raises.type is unknown",
        ),
        (
            lambda data: data["initial"].update(
                {
                    "state": "Root.A",
                    "vars": {},
                    "expect": {"raises": {"type": "UnknownError"}},
                }
            ),
            "initial.expect.raises.type is unknown",
        ),
        (
            lambda data: (
                _set_cli_expectation(data, {"output_contains": ["Commands"]})
                or data.update(
                    {
                        "initial": {
                            "state": "Root.A",
                            "vars": {},
                            "expect": {"raises": {"type": "ValueError"}},
                        }
                    }
                )
            ),
            "initial.expect is not supported for cli_command cases",
        ),
        (
            lambda data: data["initial"].update(
                {
                    "state": "Root.A",
                    "vars": {},
                    "expect": {"raises": {"type": "ValueError"}},
                }
            ),
            "initial.expect.raises cases require empty steps",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"unknown_expect": True}),
            "unknown fields",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"raises": {"type": "UnknownError"}}
                )
            ),
            "raises.type is unknown",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"stack": [{"path": ["Root"], "mode": "bad"}]}
            ),
            "mode is invalid",
        ),
        (lambda data: data.update({"categories": ["unknown"]}), "unknown categories"),
        (
            lambda data: data["steps"][0].update({"expect_initial": {"return": None}}),
            "unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars": {"x": 1}, "vars_exact": {"x": 2}}
            ),
            "vars and vars_exact conflict",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"vars_keys": ["tmp"], "vars_absent": ["tmp"]}
            ),
            "vars_keys and vars_absent overlap",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"raises": {"type": "ValueError"}}
            ),
            "cannot combine raises and return",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"cycle_result": {"value": None}}
            ),
            "cannot combine return and cycle_result",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {
                        "raises": {"type": "ValueError"},
                        "cycle_result": {"value": None},
                    }
                )
            ),
            "cannot combine raises and cycle_result",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update({"cycle_result": None})
            ),
            "cycle_result must be a mapping",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update({"cycle_result": {}})
            ),
            "cycle_result.value is required",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"cycle_result": {"value": None, "extra": []}}
                )
            ),
            "cycle_result has unknown fields",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {
                        "cycle_result": {
                            "value": None,
                            "input_events": "Root.A.Go",
                        }
                    }
                )
            ),
            "cycle_result.input_events must be a list of strings",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"raises": {"type": "ValueError", "cause_type": 1}}
                )
            ),
            "raises.cause_type must be a string",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"raises": {"type": "ValueError", "cause_match": 1}}
                )
            ),
            "raises.cause_match must be a string",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"raises": {"type": "ValueError", "cause_match_kind": "bad"}}
                )
            ),
            "raises.cause_match_kind is invalid",
        ),
        (
            lambda data: (
                data["steps"][0]["expect"].pop("return")
                or data["steps"][0]["expect"].update(
                    {"raises": {"type": "ValueError", "cause_match_kind": "regex"}}
                )
            ),
            "raises.cause_match_kind requires cause_match",
        ),
        (
            lambda data: (
                _set_generated_alignment(data)
                or data["steps"][0]["expect"].update({"warnings": {"count": 0}})
            ),
            "fields are not allowed for generated alignment",
        ),
        (
            lambda data: (
                _set_generated_alignment(data)
                or data["steps"][0]["expect"].update({"anonymous_warning_count": 0})
            ),
            "fields are not allowed for generated alignment",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"anonymous_warning_count": -1}
            ),
            "anonymous_warning_count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"warnings": {"count": -1}}),
            "warnings.count must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history_length": -1}),
            "history_length must be a non-negative integer",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history": {}}),
            "history must be a list",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {
                    "history_tail": [
                        {"cycle": "1", "state": "Root.A", "vars": {}, "events": []}
                    ]
                }
            ),
            "history_tail\\[0\\].cycle must be an integer",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {
                    "history_tail": [
                        {
                            "cycle": 1,
                            "state": "Root.A",
                            "vars": {},
                            "events": "Root.A.Go",
                        }
                    ]
                }
            ),
            "history_tail\\[0\\].events must be a list of strings",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"history_tail": [{"unknown": True}]}
            ),
            "history_tail\\[0\\] has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"history_tail": [{"cycle": 1, "state": "Root.A", "events": []}]}
            ),
            "history_tail\\[0\\] missing fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"warnings": {"contains": {"message": "x"}}}
            ),
            "warnings.contains must be a list",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"warnings": {"contains": [{"category": "UserWarning"}]}}
            ),
            "warnings.contains\\[0\\].message is required",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"warnings": {"contains": [{"message": "x", "category": "Warning"}]}}
            ),
            "warnings.contains\\[0\\].category is invalid",
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
                            "write_attempt": {
                                "name": "x",
                                "value": 1,
                                "succeeded": "no",
                            },
                        }
                    ]
                }
            ),
            "write_attempt.succeeded must be a boolean",
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
                            "active_leaf": "Root",
                        }
                    ]
                }
            ),
            "handler_calls\\[0\\].active_leaf must be a list",
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
                            "abstract_target": 7,
                        }
                    ]
                }
            ),
            "handler_calls\\[0\\].abstract_target must be a string or null",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"error_state": "true"}),
            "error_state must be a boolean",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"error_info": {"message": "boom", "match_kind": "glob"}}
            ),
            "error_info.match_kind is invalid",
        ),
        (
            lambda data: (
                _set_generated_alignment(data)
                or data["steps"][0]["expect"].update({"error_state": False})
            ),
            "fields are not allowed for generated alignment",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"abstract_handler_errors": [{"message": "boom", "match_kind": "glob"}]}
            ),
            "abstract_handler_errors\\[0\\].match_kind is invalid",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"abstract_handler_errors": [{"match_kind": "regex"}]}
            ),
            "abstract_handler_errors\\[0\\].match_kind requires message",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"logs": {"contains": [{"match": "old"}]}}
            ),
            "must use match_kind",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"state": "Root.A"}),
            "state must be a list",
        ),
        (
            lambda data: data.update({"initial": {"state": ["Root", "A"]}}),
            "initial.state must be a string",
        ),
        (
            lambda data: data["origin"].update({"extra": "x"}),
            "origin has unknown fields",
        ),
        (
            lambda data: data["source"].update({"extra": "x"}),
            "source has unknown fields",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update({"eventz": []}),
            "cycle has unknown fields",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": 12}),
            "cycle must be a mapping, string, or null",
        ),
        (
            lambda data: data["steps"][0].update({"cycle": []}),
            "cycle must be a mapping, string, or null",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update({"events": "Root.A.Go"}),
            "cycle.events must be a list or null",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update({"events": [7]}),
            r"cycle.events\[0\] must be a string or event descriptor",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update(
                {"events": [{"event": "Root.A.Go", "extra": True}]}
            ),
            r"cycle.events\[0\] event descriptor must contain only event",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update(
                {"events": [{"unknown": "Root.A.Go"}]}
            ),
            r"cycle.events\[0\] event descriptor must contain only event",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update({"events": [{"event": 12}]}),
            r"cycle.events\[0\].event must be a string",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"logs": {"containz": []}}),
            "logs has unknown fields",
        ),
        (
            lambda data: _set_expected_raises(
                data, {"type": "ValueError", "matc": "typo"}
            ),
            "raises has unknown fields",
        ),
        (
            lambda data: _set_cli_expectation(data, {"output_contains": "Commands"}),
            "output_contains must be a list of strings",
        ),
        (
            lambda data: _set_cli_expectation(data, {"should_exit": "false"}),
            "should_exit must be a boolean",
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
def test_pure_shared_fixture_boundary_accepts_public_observations(tmp_path):
    data = _pure_shared_case_data()
    data["handlers"] = [{"action": "Root.Init", "behavior": "record_call"}]
    data["steps"][0]["expect"]["handler_calls"] = []
    yaml_path = _write_fixture(tmp_path, data)

    load_semantic_case(yaml_path)
    validate_pure_shared_fixture_boundary(data, yaml_path)


@pytest.mark.unittest
def test_pure_shared_fixture_boundary_marker_enforces_loader_gate(tmp_path):
    data = _pure_shared_case_data()
    data["steps"][0]["expect"]["stack"] = [{"path": ["Root", "A"], "mode": "active"}]
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match="forbidden expectation fields"):
        load_semantic_case(yaml_path)


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["mutate", "message"],
    [
        (
            lambda data: data["steps"][0].update({"expect": {}}),
            "expect requires public observation fields",
        ),
        (
            lambda data: data.update({"steps": [{"expect_initial": {}}]}),
            "expect_initial requires public observation fields",
        ),
    ],
)
def test_pure_shared_fixture_boundary_marker_rejects_empty_observations(
    tmp_path, mutate, message
):
    data = _pure_shared_case_data()
    mutate(data)
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match=message):
        load_semantic_case(yaml_path)


@pytest.mark.unittest
def test_pure_shared_fixture_boundary_rejects_legacy_return_field(tmp_path):
    data = _pure_shared_case_data()
    data["steps"][0]["expect"]["return"] = None
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match="forbidden expectation fields"):
        validate_pure_shared_fixture_boundary(data, yaml_path)


@pytest.mark.unittest
def test_pure_shared_fixture_boundary_does_not_gate_existing_corpus():
    cases = list(iter_semantic_cases())
    legacy_fields = {
        field
        for case in cases
        for step in case.data.get("steps") or []
        for expect in (step.get("expect_initial"), step.get("expect"))
        if isinstance(expect, dict)
        for field in expect
        if field in {"stack", "cycle_count", "return", "history", "history_tail"}
    }

    assert cases
    assert legacy_fields


@pytest.mark.unittest
def test_pure_shared_fixture_boundary_would_reject_existing_legacy_cases():
    cases = list(iter_semantic_cases())
    rejected_case_ids = set()

    for case in cases:
        try:
            validate_pure_shared_fixture_boundary(case.data, case.yaml_path)
        except SemanticCaseError:
            rejected_case_ids.add(case.id)

    assert cases
    assert rejected_case_ids


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["mutate", "message"],
    [
        (
            lambda data: data.update({"runners": ["simulation"]}),
            "requires runners",
        ),
        (
            lambda data: _set_cli_expectation(data, {"output_contains": ["Commands"]}),
            "cannot use cli_command runner",
        ),
        (
            lambda data: data.update(
                {"runtime_options": {"abstract_error_mode": "log"}}
            ),
            "forbidden top-level fields",
        ),
        (
            lambda data: _set_model_build_expectation(
                data, {"type": "ModelValidationError"}
            ),
            "forbidden top-level fields",
        ),
        (
            lambda data: data.update(
                {"commands": [{"input": "help", "expect": {"output_contains": []}}]}
            ),
            "forbidden top-level fields",
        ),
        (
            lambda data: data.update({"expected_failure": {"reason": "legacy bug"}}),
            "forbidden top-level fields",
        ),
        (
            lambda data: data["initial"].update(
                {"expect": {"raises": {"type": "ValueError"}}}
            ),
            "initial.expect diagnostics",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"stack": []}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"brief_stack": []}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"cycle_count": 1}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"return": None}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history": []}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history_length": 0}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"history_tail": []}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"warnings": {"count": 0}}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"logs": {"contains": [{"level": "INFO", "message": "x"}]}}
            ),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"abstract_handler_errors": []}
            ),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"error_state": False}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"error_info": None}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0]["expect"].update(
                {"anonymous_warning_count": 0}
            ),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0].update({"expect_initial": {"return": None}}),
            "forbidden expectation fields",
        ),
        (
            lambda data: data["steps"][0].update({"expect": {}}),
            "expect requires public observation fields",
        ),
        (
            lambda data: data["steps"][0].update({"expect_initial": {}}),
            "expect_initial requires public observation fields",
        ),
        (
            lambda data: data.update({"steps": []}),
            "requires non-empty steps",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"handler_calls": []}),
            "handler_calls requires top-level handlers",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [],
                    "steps": [
                        {
                            "cycle": {},
                            "expect": {
                                "state": ["Root", "A"],
                                "handler_calls": [],
                                "cycle_result": {"value": None},
                            },
                        }
                    ],
                }
            ),
            "handler_calls requires top-level handlers",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {"action": "Root.Init", "behavior": "raise_error"}
                    ]
                }
            ),
            "only allows handlers",
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
            "only allows handlers",
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
            "does not allow handlers\\[0\\].exception",
        ),
        (
            lambda data: data.update(
                {
                    "handlers": [
                        {
                            "action": "Root.Init",
                            "behavior": "record_call",
                            "write": {"name": "x", "value": 1},
                        }
                    ]
                }
            ),
            "does not allow handlers\\[0\\].write",
        ),
    ],
)
def test_pure_shared_fixture_boundary_rejects_non_shared_surfaces(
    tmp_path, mutate, message
):
    data = _pure_shared_case_data()
    mutate(data)
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError, match=message):
        validate_pure_shared_fixture_boundary(data, yaml_path)


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
