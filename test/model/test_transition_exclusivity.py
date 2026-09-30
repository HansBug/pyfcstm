"""Public transition objects reject simultaneous event and guard fields."""

from copy import deepcopy
from dataclasses import replace

import pytest

from pyfcstm.dsl import node as ast
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import Boolean, Event, Transition

pytestmark = pytest.mark.unittest


@pytest.fixture(params=["model", "ast", "forced"])
def transition_case(request):
    if request.param == "model":
        return (Transition, {"effects": []}, "event", "guard",
                Event("Go", ("Root",)), Boolean(False))
    cls = ast.TransitionDefinition if request.param == "ast" else ast.ForceTransitionDefinition
    options = {"post_operations": []} if request.param == "ast" else {}
    return cls, options, "event_id", "condition_expr", ast.ChainID(["Go"]), ast.Boolean("false")


def test_constructor_rejects_event_and_guard(transition_case):
    cls, options, event_field, guard_field, event, guard = transition_case
    with pytest.raises(ValueError, match="mutually exclusive"):
        cls("A", "B", **{event_field: event, guard_field: guard}, **options)


def test_assignment_rejects_conflict_without_changing_transition(transition_case):
    cls, options, event_field, guard_field, event, guard = transition_case
    transition = cls("A", "B", **{event_field: event, guard_field: None}, **options)
    original = deepcopy(transition)
    with pytest.raises(ValueError, match="mutually exclusive"):
        setattr(transition, guard_field, guard)
    assert transition == original

    setattr(transition, event_field, None)
    setattr(transition, guard_field, guard)
    original = deepcopy(transition)
    with pytest.raises(ValueError, match="mutually exclusive"):
        setattr(transition, event_field, event)
    assert transition == original


def test_legal_transitions_can_be_copied_replaced_and_cleared(transition_case):
    cls, options, event_field, guard_field, event, guard = transition_case
    for event_value, guard_value in ((None, None), (event, None), (None, guard)):
        transition = cls("A", "B", **{event_field: event_value, guard_field: guard_value}, **options)
        assert deepcopy(transition) == transition
        assert replace(transition, to_state="C").to_state == "C"
        setattr(transition, event_field, None)
        setattr(transition, guard_field, None)
        assert getattr(transition, event_field) is None
        assert getattr(transition, guard_field) is None


@pytest.mark.parametrize("suffix", [": if [x > 0]", ": [x > 0]", ":: Go + [x > 0]"])
def test_guard_alias_and_combo_ast_still_round_trip(suffix):
    source = "state Root { state A; state B; [*] -> A; A -> B %s; }" % suffix
    node = parse_with_grammar_entry(source, "state_definition")
    restored = parse_with_grammar_entry(str(node), "state_definition")
    assert str(restored) == str(node)
    assert "x > 0" in str(restored)
    if "Go" in suffix:
        assert len(restored.transitions[-1].combo_trigger.terms) == 2
