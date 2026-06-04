import os

import pytest
import yaml

from test.testings.simulate_semantics import (
    SemanticCaseError,
    iter_semantic_cases,
    load_semantic_case,
    run_cli_command_case,
    run_simulation_case,
)


@pytest.mark.unittest
def test_all_semantic_fixtures_load():
    cases = iter_semantic_cases()

    assert len(cases) >= 84
    assert {case.id for case in cases}


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


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["mutate", "message"],
    [
        (lambda data: data.update({"unexpected": True}), "unknown top-level fields"),
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
                _set_generated_alignment(data)
                or data.update(
                    {"handlers": [{"action": "Root.Init", "behavior": "record_call"}]}
                )
            ),
            "handlers are only supported by simulation-only cases",
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
            lambda data: _set_model_build_expectation(data, {"type": "UnknownError"}),
            "model_build.expect.raises.type is unknown",
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
                or data["steps"][0]["expect"].update({"cycle_count": 1})
            ),
            "cycle_count is not allowed for generated alignment",
        ),
        (
            lambda data: (
                _set_generated_alignment(data)
                or data["steps"][0]["expect"].update({"warnings": {"count": 0}})
            ),
            "fields are not allowed for generated alignment",
        ),
        (
            lambda data: data["steps"][0]["expect"].update({"warnings": {"count": -1}}),
            "warnings.count must be a non-negative integer",
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
            r"cycle.events\[0\] must be a string or event-like descriptor",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update(
                {"events": [{"event_like": "Root.A.Go", "extra": True}]}
            ),
            r"cycle.events\[0\] event descriptor must contain only event_like",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update(
                {"events": [{"unknown": "Root.A.Go"}]}
            ),
            r"cycle.events\[0\] event descriptor must contain only event_like",
        ),
        (
            lambda data: data["steps"][0]["cycle"].update(
                {"events": [{"event_like": 12}]}
            ),
            r"cycle.events\[0\].event_like must be a string",
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
def test_semantic_fixture_schema_reports_case_id_and_path(tmp_path):
    data = _valid_case_data()
    data["steps"][0]["expect"]["stack"] = [{"path": ["Root"], "mode": "bad"}]
    yaml_path = _write_fixture(tmp_path, data)

    with pytest.raises(SemanticCaseError) as exc_info:
        load_semantic_case(yaml_path)

    message = str(exc_info.value)
    assert "bad" in message
    assert os.path.abspath(yaml_path) in message
