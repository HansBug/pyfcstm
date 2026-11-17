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
    ('Root.Job{A: [done], B: Working}', ['Root.Job.B.Working']),
    ('Root.Job{A: Nested{Inner: [done], Other: Working}, B: Working}',
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
    config = Configuration.parse(machine, 'Root.Job{A: [done], B: Working}')
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
    config = Configuration.parse(machine, 'Root.Job{A: Nested{Inner: [done], Other: Working}, B: [done]}')
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
    transient = Configuration.parse(machine, 'Root.Job{A: [done], B: [done]}', mode='transient')
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
    'Root.Job{A: [done], B: [done]}',
    'Root.Job{A: Nested{Inner: [done], Other: [done]}, B: Working}',
    'Root.Job{A: Nested, B: Working}',
    'Root.Job{A: Nested.Inner.Working, B: Working}',
    'Root.Job{A: Working, B: Working,}', 'Root.Job{A Working}',
    'Root.Job{A: Working, B: Working', 'Root.Job{A: [done], B: Working}}',
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


@pytest.mark.parametrize('mode,source,canonical,statuses', [
    ('initialization', 'Root.Job', 'Root.Job{A: [init], B: [init]}', ('pending', 'pending')),
    ('initialization', 'Root.Job{B: [init], A: [init]}',
     'Root.Job{A: [init], B: [init]}', ('pending', 'pending')),
    ('transient', 'Root.Job{A: Working}',
     'Root.Job{A: Working, B: [init]}', ('live', 'pending')),
    ('transient', 'Root.Job{B: [init], A: [done]}',
     'Root.Job{A: [done], B: [init]}', ('done', 'pending')),
    ('transient', 'Root.Job{A: [init], B: Working}',
     'Root.Job{A: [init], B: Working}', ('pending', 'live')),
    ('transient', 'Root.Job{A: [done], B: [done]}',
     'Root.Job{A: [done], B: [done]}', ('done', 'done')),
    ('transient', 'Root.Job', 'Root.Job{A: [init], B: [init]}', ('pending', 'pending')),
])
def test_configuration_pending_and_done_text_roundtrip(machine, mode, source, canonical, statuses):
    config = Configuration.parse(machine, source, mode=mode)
    assert str(config) == canonical
    assert (config.region_status('Root.Job.A'), config.region_status('Root.Job.B')) == statuses
    assert Configuration.parse(machine, canonical, mode=mode) == config
    clone = Configuration.from_dict(machine, json.loads(json.dumps(config.to_dict())))
    assert clone == config
    assert hash(clone) == hash(config)
    assert str(clone) == canonical
    assert not config.is_active('Root.Job.A.Nested')


def test_pending_json_omission_is_distinct_from_done_null(machine):
    config = Configuration.parse(machine, 'Root.Job{A: [done], B: [init]}', mode='transient')
    assert config.to_dict() == {
        'mode': 'transient', 'state': 'Root.Job',
        'regions': [{'name': 'A', 'configuration': None}],
    }
    pending = Configuration.parse(machine, 'Root.Job{A: [init], B: [init]}', mode='initialization')
    assert pending.to_dict() == {'mode': 'initialization', 'state': 'Root.Job', 'regions': []}
    assert config.leaves == pending.leaves == ()
    assert config != pending
    assert config.is_active('Root.Job') and pending.is_active('Root.Job')


@pytest.mark.parametrize('source,canonical,inner_status', [
    ('Root.Job{A: Nested{Inner: [done]}, B: [init]}',
     'Root.Job{A: Nested{Inner: [done], Other: [init]}, B: [init]}', 'done'),
    ('Root.Job{A: Nested, B: [done]}',
     'Root.Job{A: Nested{Inner: [init], Other: [init]}, B: [done]}', 'pending'),
])
def test_nested_pending_configuration_preserves_ancestor_activity(machine, source, canonical, inner_status):
    config = Configuration.parse(machine, source, mode='transient')
    assert str(config) == canonical
    assert config.region_status('Root.Job.A') == 'live'
    assert config.region_status('Root.Job.A.Nested.Inner') == inner_status
    assert config.region_status('Root.Job.A.Nested.Other') == 'pending'
    assert config.is_active('Root.Job.A.Nested')
    assert not config.is_active('Root.Job.A.Nested.Inner.Working')
    assert not config.leaves
    assert Configuration.parse(machine, str(config), mode=config.mode) == config
    assert Configuration.from_dict(machine, config.to_dict()) == config


@pytest.mark.parametrize('mode,source', [
    ('stable', 'Root.Idle'),
    ('transient', 'Root.Idle'),
    ('initialization', 'Root.Group'),
    ('initialization', 'Root.Job'),
    ('transient', 'Root.Job{A: [done]}'),
])
def test_configuration_repr_identifies_mode_and_position(machine, mode, source):
    config = Configuration.parse(machine, source, mode=mode)
    assert repr(config) == 'Configuration(mode=%r, position=%r)' % (mode, str(config))
    assert Configuration.parse(machine, str(config), mode=mode) == config


def test_same_position_keeps_distinct_validation_modes(machine):
    stable = Configuration.parse(machine, 'Root.Idle')
    transient = Configuration.parse(machine, 'Root.Idle', mode='transient')
    assert str(stable) == str(transient) == 'Root.Idle'
    assert stable != transient
    assert repr(stable) != repr(transient)


@pytest.mark.parametrize('mode,text,reason', [
    ('stable', 'Root.Job{A: [init], B: Working}', 'pending'),
    ('stable', 'Root.Job{A: Nested{Inner: [init], Other: Working}, B: Working}', 'pending'),
    ('initialization', 'Root.Job{A: [done], B: [init]}', 'whole owner'),
    ('initialization', 'Root.Job{A: Working, B: [init]}', 'whole owner'),
    ('transient', 'Root.Job{A: [init], A: [init]}', 'Duplicate'),
    ('transient', 'Root.Job{A: [init], A: Working}', 'Duplicate'),
    ('transient', 'Root.Job{A: [done], A: [init]}', 'Duplicate'),
    ('transient', 'Root.Job{Unknown: [init]}', 'Unknown region'),
    ('transient', 'Root.Idle{A: [init]}', 'Unknown region'),
])
def test_explicit_pending_does_not_bypass_model_validation(machine, mode, text, reason):
    with pytest.raises(ValueError, match=reason):
        Configuration.parse(machine, text, mode=mode)


@pytest.mark.parametrize('text,line,column', [
    ('', 1, 1),
    ('\n \t', 2, 3),
    ('Root..Job', 1, 6),
    ('Root.Idle extra', 1, 11),
    ('Root.Job{A: [*], B: Working}', 1, 13),
    ('Root.Job{\n  A: Working,\n  B: @\n}', 3, 6),
    ('Root.Job{\n A: Working,\n B: Working', 3, 12),
    ('Root.Job{A: Working B: [done]}', 1, 21),
    ('Root.Job{A Working}', 1, 12),
    ('Root.Job{A: Working,}', 1, 21),
])
def test_configuration_syntax_error_reports_source_position(machine, text, line, column):
    with pytest.raises(ValueError, match=r'line %d, column %d\b' % (line, column)):
        Configuration.parse(machine, text, mode='transient')


@pytest.mark.parametrize('marker', ['[*]', '[INIT]', '[Done]', '[ init ]', '[done', '[init].Working'])
def test_only_complete_lowercase_configuration_markers_are_accepted(machine, marker):
    with pytest.raises(ValueError):
        Configuration.parse(machine, 'Root.Job{A: %s, B: Working}' % marker, mode='transient')


def test_marker_words_remain_state_and_region_identifiers():
    model = load_state_machine_from_text('''state Root {
        region init { state done; [*] -> done; }
        region done { state init; [*] -> init; }
    }''')
    config = Configuration.parse(model, 'Root{init: done, done: init}')
    assert str(config) == 'Root{init: done, done: init}'
    assert [state.name for state in config.leaves] == ['done', 'init']
    assert str(Configuration.parse(model, 'Root{init: [done], done: [init]}', mode='transient')) == \
        'Root{init: [done], done: [init]}'


def test_configuration_accepts_multiline_unicode_whitespace(machine):
    config = Configuration.parse(machine, '\tRoot . Job {\r\n A:\u00a0[done],\vB: Working\f}\n')
    assert str(config) == 'Root.Job{A: [done], B: Working}'


def test_deep_configuration_roundtrips_through_public_model():
    source = 'state Leaf;'
    text = 'Leaf'
    for depth in range(16):
        name = 'Level%d' % depth
        source = 'state %s { region Main { %s [*] -> %s; } }' % (
            name, source, 'Leaf' if depth == 0 else 'Level%d' % (depth - 1))
        text = name + '{Main: ' + text + '}'
    model = load_state_machine_from_text(source)
    config = Configuration.parse(model, text)
    assert str(config) == text
    assert [state.name for state in config.leaves] == ['Leaf']
    assert Configuration.parse(model, str(config)) == config
    assert Configuration.from_dict(model, config.to_dict()) == config
