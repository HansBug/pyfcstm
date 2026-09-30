"""Inspect reports on history models match the same models written without history."""

import re

import pytest

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

from test.model import test_history_lowering as lowering
from test.model.test_history_lowering import BLOCKED, BLOCKED_INITIALS, WASHER

EVENTED = """
state R {
    state Off;
    state O {
        event Kick;
        state A;
        state B;
        [*] -> A :: Kick;
        [H] -> B;
        A -> B :: Next;
    }
    [*] -> Off;
    Off -> O :: Fresh;
    Off -> O.[H] :: Resume;
    !O -> Off :: Stop;
}
"""

MODELS = {
    "washer": WASHER,
    "blocked-merged": BLOCKED % BLOCKED_INITIALS["merged"],
    "blocked-gated": BLOCKED % BLOCKED_INITIALS["gated"],
    "evented": EVENTED,
}


def _without_history(text):
    """The same model with every history construct written as ordinary entry."""
    text = re.sub(r"^\s*\[H\*?\] -> [\w.]+;\s*$", "", text, flags=re.MULTILINE)
    return re.sub(r"\.\[H\*?\]", "", text)


def _report(text):
    machine, diagnostics = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(text, "state_machine_dsl"), collect=True
    )
    return inspect_model(machine, model_diagnostics=diagnostics)


def _findings(report):
    return sorted(
        (item.code, repr(sorted(item.refs.items())))
        for item in report.diagnostics
        if "HISTORY" not in item.code
    )


@pytest.mark.unittest
@pytest.mark.parametrize("name", sorted(MODELS))
def test_lowering_adds_or_hides_no_inspect_finding(name):
    text = MODELS[name]
    plain = _without_history(text)
    assert "[H" not in plain
    assert _findings(_report(text)) == _findings(_report(plain))


@pytest.mark.unittest
def test_user_unconditional_initials_stay_unconditional_after_lowering():
    report = _report(WASHER)
    states = {state.path: state for state in report.states}
    for path in ("Washer.Program", "Washer.Program.Wash"):
        flags = [item["is_unconditional"] for item in states[path].initial_targets]
        assert flags.count(True) == 1, (path, states[path].initial_targets)


@pytest.mark.unittest
def test_a_conditional_user_initial_still_warns():
    report = _report(BLOCKED % BLOCKED_INITIALS["merged"])
    missing = [
        item.refs["composite_path"]
        for item in report.diagnostics
        if item.code == "W_INITIAL_UNCONDITIONAL_MISSING"
    ]
    assert missing == ["R.O.K"]


@pytest.mark.unittest
def test_history_defaults_make_their_targets_reachable():
    # Without history, R.O.S1 is only named by the ``[H] -> S1`` default and is
    # unreachable; with history it is the shallow default, so the report drops
    # exactly that warning and adds nothing else.
    text = lowering.TestNestedOwners.TEXT
    lowered = _findings(_report(text))
    plain = _findings(_report(_without_history(text)))
    removed = [item for item in plain if item not in lowered]
    assert [code for code, _ in removed] == ["W_UNREACHABLE_STATE"]
    assert "R.O.S1" in removed[0][1]
    assert all(item in plain for item in lowered)


@pytest.mark.unittest
def test_initial_targets_mark_the_edges_lowering_produced():
    report = _report(EVENTED)
    owner = {state.path: state for state in report.states}["R.O"]
    roles = sorted(item.get("history_role", "-") for item in owner.initial_targets)
    assert roles == ["gate", "route", "route"]
    assert not any(item["is_unconditional"] for item in owner.initial_targets)


@pytest.mark.unittest
@pytest.mark.parametrize("name", sorted(MODELS))
def test_history_reports_validate_against_the_shipped_schema(name):
    import json
    from pathlib import Path

    import jsonschema

    import pyfcstm.diagnostics

    payload = _report(MODELS[name]).to_json()
    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name("schema.json").read_text())
    jsonschema.Draft7Validator(schema).validate(payload)
    roles = {
        item.get("history_role")
        for state in payload["states"]
        for item in state["initial_targets"]
    }
    assert roles & {"route", "merged", "gated", "gate"}
