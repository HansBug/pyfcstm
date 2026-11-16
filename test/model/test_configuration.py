"""Immutable model-bound configurations preserve ordered parallel positions."""

import json
from dataclasses import FrozenInstanceError

import pytest

from pyfcstm.model import Configuration, load_state_machine_from_text

pytestmark = pytest.mark.unittest


@pytest.fixture
def machine():
    return load_state_machine_from_text('''state Root {
        state Idle;
        state Group { state Leaf; [*] -> Leaf; }
        state Job {
            region A {
                state Working;
                pseudo state Gate;
                state Nested {
                    region Inner { state Working; [*] -> Working; }
                    region Other { state Working; [*] -> Working; }
                }
                [*] -> Working;
            }
            region B { state Working; [*] -> Working; }
        }
        [*] -> Idle;
    }''')


@pytest.mark.parametrize('text,leaves', [
    ('Root.Idle', ['Root.Idle']),
    ('Root.Group.Leaf', ['Root.Group.Leaf']),
    ('Root.Job{A: Working, B: Working}', ['Root.Job.A.Working', 'Root.Job.B.Working']),
    ('Root.Job{A: [*], B: Working}', ['Root.Job.B.Working']),
    ('Root.Job{A: Nested{Inner: [*], Other: Working}, B: Working}',
     ['Root.Job.A.Nested.Other.Working', 'Root.Job.B.Working']),
])
def test_configuration_text_json_value_roundtrip(machine, text, leaves):
    config = Configuration.parse(machine, text)
    assert str(config) == text
    assert ['.'.join(state.path) for state in config.leaves] == leaves
    assert config.mode == 'stable'
    assert Configuration.parse(machine, str(config)) == config
    assert Configuration.from_dict(machine, json.loads(json.dumps(config.to_dict()))) == config
    assert hash(Configuration.from_dict(machine, config.to_dict())) == hash(config)
    assert config.is_active('Root')
    assert not config.is_active('Root.Job.A.Gate')
    with pytest.raises(FrozenInstanceError):
        config.mode = 'transient'


def test_configuration_json_shape_and_snapshot_independence(machine):
    config = Configuration.parse(machine, 'Root.Job{A: [*], B: Working}')
    expected = {'mode': 'stable', 'state': 'Root.Job', 'regions': [
        {'name': 'A', 'configuration': None},
        {'name': 'B', 'configuration': {'state': 'Root.Job.B.Working', 'regions': []}},
    ]}
    assert config.to_dict() == expected
    clone = Configuration.from_dict(machine, expected)
    expected['regions'][0]['name'] = 'Changed'
    assert clone == config
    exported = config.to_dict()
    exported['regions'].clear()
    assert len(config.to_dict()['regions']) == 2


def test_configuration_state_and_region_queries(machine):
    config = Configuration.parse(machine, 'Root.Job{A: Nested{Inner: [*], Other: Working}, B: [*]}')
    assert config.is_active('Root.Job')
    assert config.is_active(('Root', 'Job', 'A', 'Nested'))
    assert config.is_active('Root.Job.A.Nested.Other.Working')
    assert not config.is_active('Root.Idle')
    assert not config.is_active('Root.Job.A.Working')
    assert config.region_status('Root.Job.A') == 'live'
    assert config.region_status('Root.Job.B') == 'done'
    assert config.region_status('Root.Job.A.Nested.Inner') == 'done'
    assert config.region_status('Root.Job.A.Nested.Other') == 'live'
    assert Configuration.parse(machine, 'Root.Idle').region_status('Root.Job.A') == 'inactive'
    with pytest.raises(ValueError, match='State'):
        config.is_active('Root.Job.A')
    with pytest.raises(ValueError, match='Region'):
        config.region_status('Root.Job')
    with pytest.raises(ValueError, match='Unknown'):
        config.is_active('Root.Unknown')


def test_pending_owner_and_transient_snapshots_are_explicit(machine):
    pending = Configuration.parse(machine, 'Root.Job', mode='initialization')
    assert pending.mode == 'initialization'
    assert not pending.leaves
    assert pending.is_active('Root.Job')
    assert pending.region_status('Root.Job.A') == 'pending'
    assert pending.region_status('Root.Job.A.Nested.Inner') == 'inactive'
    assert Configuration.from_dict(machine, pending.to_dict()) == pending
    transient = Configuration.parse(machine, 'Root.Job{A: [*], B: [*]}', mode='transient')
    assert transient.mode == 'transient'
    assert not transient.leaves
    assert transient.region_status('Root.Job.A') == 'done'
    assert transient.is_active('Root.Job')
    partial = Configuration.parse(machine, 'Root.Job{A: Gate}', mode='transient')
    assert partial.region_status('Root.Job.B') == 'pending'
    assert partial.is_active('Root.Job.A.Gate')
    assert Configuration.parse(machine, 'Root.Group', mode='initialization').is_active('Root.Group')


def test_region_input_order_is_normalized_to_model_order(machine):
    config = Configuration.parse(machine, ' Root . Job { B : Working , A : Working } ')
    assert str(config) == 'Root.Job{A: Working, B: Working}'
    assert [state.path[-2] for state in config.leaves] == ['A', 'B']


@pytest.mark.parametrize('text', [
    '', 'Unknown', 'Root.Unknown', 'Root..Idle', 'Root.Idle extra',
    'Root.Idle{}', 'Root.Job', 'Root.Group', 'Root.Job.A', 'Root.Job.A.Working',
    'Root.Job{A: Working}', 'Root.Job{C: Working, B: Working}',
    'Root.Job{A: Working, A: Working, B: Working}',
    'Root.Job{A: Missing, B: Working}',
    'Root.Job{A: Gate, B: Working}',
    'Root.Job{A: [*], B: [*]}',
    'Root.Job{A: Nested{Inner: [*], Other: [*]}, B: Working}',
    'Root.Job{A: Nested, B: Working}',
    'Root.Job{A: Nested.Inner.Working, B: Working}',
    'Root.Job{A: Working, B: Working,}', 'Root.Job{A Working}',
    'Root.Job{A: Working, B: Working', 'Root.Job{A: [*], B: Working}}',
])
def test_invalid_stable_configuration_is_rejected(machine, text):
    with pytest.raises(ValueError):
        Configuration.parse(machine, text)


@pytest.mark.parametrize('mode,text', [
    ('invalid', 'Root.Idle'), ('initialization', 'Root.Idle'),
    ('initialization', 'Root.Job{A: Working, B: Working}'),
])
def test_mode_contract_is_validated(machine, mode, text):
    with pytest.raises(ValueError):
        Configuration.parse(machine, text, mode=mode)


@pytest.mark.parametrize('data', [
    None, [], {}, {'state': 'Root.Idle', 'unknown': True},
    {'state': 1}, {'state': 'Root.Job', 'regions': {}},
    {'state': 'Root.Job', 'regions': [None]},
    {'state': 'Root.Job', 'regions': [{'name': 'A'}]},
    {'state': 'Root.Job', 'regions': [{'name': 1, 'configuration': None}]},
    {'state': 'Root.Job', 'regions': [{'name': 'A', 'configuration': None, 'extra': 1}]},
    {'state': 'Root.Job', 'regions': [
        {'name': 'A', 'configuration': {'state': 'Root.Idle'}},
        {'name': 'B', 'configuration': None}]},
])
def test_invalid_json_configuration_is_rejected(machine, data):
    with pytest.raises((TypeError, ValueError)):
        Configuration.from_dict(machine, data)


def test_non_text_configuration_is_rejected(machine):
    with pytest.raises(TypeError, match='string'):
        Configuration.parse(machine, None)
