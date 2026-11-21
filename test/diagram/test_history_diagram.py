"""A diagram of a model that uses history shows the history, not what it was lowered into."""

import json

import pytest

from pyfcstm.model import load_state_machine_from_text

from test.model.test_history_lowering import WASHER

pytestmark = pytest.mark.unittest


def _labels(node):
    found = [(node['qualifiedName'], item['label']) for item in node['transitions']]
    for child in node['children']:
        found.extend(_labels(child))
    return found


def test_the_snapshot_has_no_lowered_variable_gate_or_route():
    data = load_state_machine_from_text(WASHER).diagram().to_dict()
    assert '__hist' not in json.dumps(data)
    assert [item['name'] for item in data['variables']] == [
        'program_entries', 'fill_entries', 'agitate_entries', 'wash_initials',
    ]
    assert data['summary']['variables'] == 4
    # The initial transitions are the ones written, not the lowered routes.
    assert ('Washer.Program', '[*] -> Idle') in _labels(data['rootState'])


def test_an_entry_into_a_history_names_that_history():
    labels = [label for _, label in _labels(load_state_machine_from_text(WASHER).diagram().to_dict()['rootState'])]
    assert 'Paused -> Program Fresh' in labels
    assert 'Paused -> Program.[H] Shallow' in labels
    assert 'Paused -> Program.[H*] Deep' in labels


def test_a_model_with_history_and_a_forced_declaration_shows_both_as_written():
    model = load_state_machine_from_text('''state Root {
    event Pause;
    event Resume;
    [*] -> Work;
    state Work {
        [*] -> A;
        [H] -> A;
        state A;
        state B;
        A -> B;
    }
    state Paused;
    Paused -> Work.[H] :: Resume;
    !Work -> Paused :: Pause;
}''')
    data = model.diagram().to_dict()
    assert '__hist' not in json.dumps(data) and '__forced' not in json.dumps(data)
    forced = [item for item in data['rootState']['transitions'] if item['forced']]
    assert [item['label'] for item in forced] == ['Work -> Paused Pause']
    assert any(label.startswith('Paused -> Work.[H]') for _, label in _labels(data['rootState']))
