"""
Simulator-only diagnostics migrated out of the shared fixture corpus.

The tests in this module preserve warning, log, rollback, and abstract-handler
diagnostics that are useful for :class:`pyfcstm.simulate.SimulationRuntime` but
are not part of the cross-template shared fixture contract.
"""

import re
import warnings

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from test.testings.simulate_semantics import load_semantic_case


DIAGNOSTIC_SOURCES = {
    "abstract_handler_raise_mode_blocks_later_cycles": """
def int x = 0;

state Root {
    state A {
        during abstract Boom;
        during {
            x = x + 1;
        }
    }

    [*] -> A;
}
""",
    "abstract_handler_warning_rollback_on_raise": """
state Root {
    state Active {
        enter abstract /* anonymous action */;
        enter abstract Fail;
    }

    [*] -> Active;
}
""",
    "failed_cycle_rolls_back_logged_abstract_handler_errors": """
def int x = 0;
state Root {
    pseudo state A {
        during abstract Boom;
    }

    [*] -> A;
}
""",
    "rejected_transition_candidate_defers_anonymous_warning": """
def int x = 0;
state Root {
    state A;

    state Bad {
        enter abstract /* anonymous action */;

        state Done;

        [*] -> Done : if [x < 0];
    }

    state Good {
        during {
            x = -1;
        }
    }

    [*] -> A;
    A -> Bad :: Go;
    A -> Good :: Go;
    Good -> Bad :: TryBad;
}
""",
}

DESIGN_LOG_ASSERTIONS = {
    "design_composite_stuck_in_init_wait": {
        0: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
        1: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
        2: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
    },
    "design_post_child_exit_without_follow_up": {
        0: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
        1: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
        2: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Unable to reach a stoppable state",
                    "match_kind": "substring",
                }
            ]
        },
    },
    "design_explicit_exit_to_root_ends_runtime": {
        3: {
            "contains": [
                {
                    "level": "WARNING",
                    "message": "Runtime already ended, cycle ignored.",
                    "match_kind": "substring",
                }
            ]
        },
    },
}


def _runtime_from_diagnostic_case(case_id, **runtime_kwargs):
    dsl_code = DIAGNOSTIC_SOURCES[case_id]
    return _runtime_from_dsl_code(dsl_code, **runtime_kwargs)


def _runtime_from_dsl_code(dsl_code, **runtime_kwargs):
    ast_node = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    state_machine = parse_dsl_node_to_state_machine(ast_node)
    return SimulationRuntime(state_machine, **runtime_kwargs)


def _recording_raise_boom(calls):
    def handler(ctx):
        calls.append(
            {
                "action": ctx.action_name,
                "state": ctx.get_full_state_path(),
                "stage": ctx.action_stage,
                "vars": dict(ctx.vars),
            }
        )
        raise ValueError("boom")

    return handler


def _assert_root_runtime_snapshot(runtime, expected_vars):
    assert runtime.current_state.path == ("Root",)
    assert dict(runtime.vars) == expected_vars
    assert runtime.is_ended is False


def _assert_error_info(runtime, expected_action, expected_error_type, expected_message):
    assert runtime.error_info is not None
    action_path, error = runtime.error_info
    assert action_path == expected_action
    assert type(error).__name__ == expected_error_type
    assert expected_message in str(error)


def _anonymous_warning_count(runtime):
    return len(runtime._warned_anonymous_abstracts)


def _log_matches(record, expected):
    if expected.get("level") is not None and record.levelname != expected["level"]:
        return False
    message = expected["message"]
    actual = record.getMessage()
    match_kind = expected.get("match_kind", "substring")
    if match_kind == "exact":
        return actual == message
    if match_kind == "substring":
        return message in actual
    if match_kind == "regex":
        return re.search(message, actual) is not None
    raise AssertionError("unsupported log match_kind %r" % match_kind)


def _assert_step_log_contains(records, expected_logs):
    rendered = [
        "%s:%s:%s" % (record.levelname, record.name, record.getMessage())
        for record in records
    ]
    for expected in expected_logs.get("contains", []) or []:
        assert any(_log_matches(record, expected) for record in records), (
            "missing expected log %r in %r" % (expected, rendered)
        )
    for expected in expected_logs.get("not_contains", []) or []:
        assert not any(_log_matches(record, expected) for record in records), (
            "unexpected log %r in %r" % (expected, rendered)
        )


def _run_design_case_and_assert_only_migrated_logs(case_id, step_logs, caplog):
    case = load_semantic_case(case_id)
    runtime = _runtime_from_dsl_code(case.dsl_code)

    for step_index, step in enumerate(case.data.get("steps") or []):
        cycle = step.get("cycle") or {}
        assert cycle == {}, "%s step %d should be an eventless cycle" % (
            case_id,
            step_index,
        )

        caplog.clear()
        with caplog.at_level("DEBUG"):
            runtime.cycle()

        if step_index in step_logs:
            _assert_step_log_contains(caplog.records, step_logs[step_index])


@pytest.mark.unittest
def test_abstract_handler_raise_mode_blocks_later_cycles():
    """
    Preserve raise-mode abstract handler diagnostics after fixture migration.
    """
    calls = []
    runtime = _runtime_from_diagnostic_case(
        "abstract_handler_raise_mode_blocks_later_cycles",
        abstract_error_mode="raise",
    )
    runtime.register_abstract_handler("Root.A.Boom", _recording_raise_boom(calls))

    with pytest.raises(ValueError, match="boom"):
        runtime.cycle()

    _assert_root_runtime_snapshot(runtime, {"x": 0})
    assert runtime.cycle_count == 0
    assert runtime.is_error_state is True
    _assert_error_info(runtime, "Root.A.Boom", "ValueError", "boom")
    assert calls == [
        {
            "action": "Root.A.Boom",
            "state": "Root.A",
            "stage": "during",
            "vars": {"x": 0},
        }
    ]

    result = runtime.cycle()

    assert result.value is None
    _assert_root_runtime_snapshot(runtime, {"x": 0})
    assert runtime.cycle_count == 0
    assert runtime.is_error_state is True
    assert runtime.error_info is not None
    _assert_error_info(runtime, "Root.A.Boom", "ValueError", "boom")
    assert calls == [
        {
            "action": "Root.A.Boom",
            "state": "Root.A",
            "stage": "during",
            "vars": {"x": 0},
        }
    ]


@pytest.mark.unittest
def test_abstract_handler_warning_rollback_on_raise():
    """
    Preserve warning and rollback diagnostics for failing abstract handlers.
    """
    calls = []
    runtime = _runtime_from_diagnostic_case(
        "abstract_handler_warning_rollback_on_raise",
        abstract_error_mode="raise",
    )
    runtime.register_abstract_handler("Root.Active.Fail", _recording_raise_boom(calls))

    with pytest.warns(UserWarning, match=r"Root\.Active\.<unnamed>"):
        with pytest.raises(ValueError, match="boom"):
            runtime.cycle()

    _assert_root_runtime_snapshot(runtime, {})
    assert runtime.cycle_count == 0
    assert runtime.is_error_state is True
    _assert_error_info(runtime, "Root.Active.Fail", "ValueError", "boom")
    assert runtime.abstract_handler_errors == []
    assert _anonymous_warning_count(runtime) == 0
    assert calls == [
        {
            "action": "Root.Active.Fail",
            "state": "Root.Active",
            "stage": "enter",
            "vars": {},
        }
    ]


@pytest.mark.unittest
def test_failed_cycle_rolls_back_logged_abstract_handler_errors():
    """
    Preserve log-mode abstract handler rollback diagnostics.
    """
    calls = []
    runtime = _runtime_from_diagnostic_case(
        "failed_cycle_rolls_back_logged_abstract_handler_errors",
        abstract_error_mode="log",
    )
    runtime.register_abstract_handler("Root.A.Boom", _recording_raise_boom(calls))

    result = runtime.cycle()

    assert result.value is None
    _assert_root_runtime_snapshot(runtime, {"x": 0})
    assert runtime.cycle_count == 0
    assert runtime.is_error_state is False
    assert runtime.error_info is None
    assert runtime.abstract_handler_errors == []
    assert calls == []


@pytest.mark.unittest
def test_rejected_transition_candidate_defers_anonymous_warning():
    """
    Preserve delayed anonymous warning behavior for rejected transition candidates.
    """
    runtime = _runtime_from_diagnostic_case(
        "rejected_transition_candidate_defers_anonymous_warning"
    )

    result = runtime.cycle()

    assert result.value is None
    assert runtime.current_state.path == ("Root", "A")
    assert dict(runtime.vars) == {"x": 0}
    assert runtime.is_ended is False
    assert runtime.cycle_count == 1

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        result = runtime.cycle(["Root.A.Go"])

    assert records == []
    assert result.value is None
    assert runtime.current_state.path == ("Root", "Good")
    assert dict(runtime.vars) == {"x": -1}
    assert runtime.is_ended is False
    assert runtime.cycle_count == 2

    with pytest.warns(UserWarning, match=r"Root\.Bad\.<unnamed>"):
        result = runtime.cycle(["Root.Good.TryBad"])

    assert result.value is None
    assert runtime.current_state.path == ("Root", "Bad", "Done")
    assert dict(runtime.vars) == {"x": -1}
    assert runtime.is_ended is False
    assert runtime.cycle_count == 3


@pytest.mark.unittest
@pytest.mark.parametrize("case_id", tuple(DESIGN_LOG_ASSERTIONS))
def test_design_case_simulator_logs_preserve_migrated_assertions(case_id, caplog):
    """
    Preserve design-case log diagnostics while shared fixtures keep alignment coverage.
    """
    _run_design_case_and_assert_only_migrated_logs(
        case_id, DESIGN_LOG_ASSERTIONS[case_id], caplog
    )
