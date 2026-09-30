"""Public model transitions enforce exactly one trigger per edge."""
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace

import pytest

import pyfcstm.model as model
pytestmark = pytest.mark.unittest


def test_trigger_payload_validation_and_freezing():
    assert hasattr(model, 'EventTrigger')
    assert hasattr(model, 'GuardTrigger')
    event = model.Event('Go', ('Root', 'A'))
    trigger = model.EventTrigger(event, 'local')
    assert trigger.event is event
    for scope in (None, 'local', 'chain', 'absolute'):
        assert model.EventTrigger(event, scope).scope == scope
    for payload in (None, 'Go', model.Boolean(True)):
        with pytest.raises(TypeError):
            model.EventTrigger(payload)
    for scope in (1, [], 'unknown'):
        with pytest.raises((TypeError, ValueError)):
            model.EventTrigger(event, scope)
    for payload in (None, True, event):
        with pytest.raises(TypeError):
            model.GuardTrigger(payload)
    guard = model.GuardTrigger(model.Boolean(True))
    with pytest.raises(FrozenInstanceError):
        guard.condition = model.Boolean(False)
    with pytest.raises(FrozenInstanceError):
        trigger.scope = 'chain'


def test_transition_rejects_dual_constructor_and_legacy_assignments():
    with pytest.raises(TypeError):
        model.Transition('A', 'B', event=model.Event('Go', ('Root',)),
                         guard=model.Boolean(False), effects=[])
    assert hasattr(model, 'GuardTrigger')
    trigger = model.GuardTrigger(model.Boolean(False))
    transition = model.Transition('A', 'B', trigger, [])
    for name in ('event', 'guard', 'event_scope'):
        with pytest.raises(AttributeError):
            setattr(transition, name, None)
        assert not hasattr(transition, name)
    for invalid in (True, model.Boolean(True), model.Event('Go', ('Root',)), ()):
        with pytest.raises(TypeError):
            model.Transition('A', 'B', invalid, [])
        with pytest.raises(TypeError):
            transition.trigger = invalid
        assert transition.trigger is trigger


def test_transition_trigger_replacement_copy_and_provenance():
    assert hasattr(model, 'EventTrigger')
    event = model.EventTrigger(model.Event('Go', ('Root',)), 'absolute')
    transition = model.Transition('A', 'B', None, [])
    for trigger in (event, model.GuardTrigger(model.Boolean(False)), None):
        transition.trigger = trigger
        assert copy(transition) == transition
        assert deepcopy(transition) == transition
        assert replace(transition, trigger=trigger) == transition
    transition.doc = 'editable'
    transition._source_path = 'source.fcstm'
    assert transition.doc == 'editable'


def test_combo_guard_remains_a_separate_edge_and_roundtrips():
    machine = model.load_state_machine_from_text('''
        def int x = 0;
        state Root {
            state A; state B;
            [*] -> A;
            A -> B :: Go + [x > 0];
        }
    ''')
    assert hasattr(model, 'EventTrigger')
    edges = [edge for edge in machine.root_state.transitions if edge.combo_origin_refs]
    assert len(edges) == 2
    assert isinstance(edges[0].trigger, model.EventTrigger)
    assert isinstance(edges[1].trigger, model.GuardTrigger)
    event_map = model.collect_event_transitions(machine)
    assert list(event_map) == ['Root.A.Go']
    assert event_map['Root.A.Go'] == [(machine.root_state, edges[0])]
    assert 'x > 0' in str(machine.to_ast_node())
    assert 'x > 0' in machine.to_plantuml()
    restored = model.parse_dsl_node_to_state_machine(machine.to_ast_node())
    assert [type(edge.trigger) for edge in restored.root_state.transitions] == [
        type(edge.trigger) for edge in machine.root_state.transitions]


def test_legacy_positional_guard_cannot_become_effects():
    for guard in (None, model.Boolean(False)):
        with pytest.raises(TypeError):
            model.Transition('A', 'B', None, guard, [])
    transition = model.Transition('A', 'B', None, [])
    with pytest.raises(TypeError):
        transition.effects = model.Boolean(False)
    assert transition.effects == []


@pytest.mark.parametrize('scope', [None, 'local', 'chain', 'absolute'])
def test_event_export_has_concrete_ast_scope(scope):
    transition = model.Transition(
        'A', 'B', model.EventTrigger(model.Event('Go', ('Root', 'A')), scope), []
    )
    node = transition.to_ast_node()
    assert node.trigger.terms[0].event_scope == (scope or 'chain')
    assert 'Go' in str(node)


@pytest.mark.parametrize('owner_path,scope,prefix', [
    (('Root',), 'local', ':'),
    (('Root', 'A'), 'chain', '::'),
    (('Other',), 'local', ':'),
])
def test_export_prefix_matches_resolved_event_path(owner_path, scope, prefix):
    root = model.load_state_machine_from_text('state Root;').root_state
    transition = model.Transition(
        'A', 'B', model.EventTrigger(model.Event('Go', owner_path), scope), []
    )
    transition.parent = root
    assert transition.to_ast_node().trigger.scope_prefix == prefix
