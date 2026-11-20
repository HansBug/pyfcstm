"""State bodies choose ordinary children or ordered regions at parse time."""

import pytest

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.dsl.error import GrammarParseError

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('statement', [
    'state Child;', 'import "child.fcstm" as Child;', '[*] -> R;',
    'A -> B;', 'A -> [*];', '!A -> B;', '! * -> [*];', '[H] -> A;',
])
@pytest.mark.parametrize('before', [False, True])
def test_parallel_owner_rejects_ordinary_child_structure(statement, before):
    region = 'region R { state A; [*] -> A; }'
    body = '%s %s' % ((statement, region) if before else (region, statement))
    with pytest.raises(GrammarParseError):
        parse_state_machine_dsl('state Root { %s }' % body)


def test_parallel_owner_retains_interleaved_actions_events_and_region_order():
    source = '''state Root named "Owner" {
        enter setup {} event start;
        region Second { state A; [*] -> A; }
        during before init {} >> during before sample {} ;
        region First { state B; [*] -> B; }
        during after finish {} >> during after observe {} exit cleanup {}
    }'''
    node = parse_state_machine_dsl(source)
    owner = node.root_state
    assert [item.name for item in owner.regions] == ['Second', 'First']
    assert [item.name for item in owner.enters] == ['setup']
    assert [item.name for item in owner.durings] == ['init', 'finish']
    assert [item.name for item in owner.during_aspects] == ['sample', 'observe']
    assert [item.name for item in owner.exits] == ['cleanup']
    assert [item.name for item in owner.events] == ['start']
    assert owner.substates == owner.imports == owner.transitions == []
    assert parse_state_machine_dsl(str(node)) == node


def test_nested_parallel_states_keep_the_intervening_state():
    node = parse_state_machine_dsl('''state Root {
        region Outer { state Child { region Inner { state Leaf; [*] -> Leaf; } }
            [*] -> Child;
        }
    }''')
    assert node.root_state.regions[0].substates[0].regions[0].name == 'Inner'
    assert parse_state_machine_dsl(str(node)) == node


def test_region_cannot_directly_contain_another_region():
    with pytest.raises(GrammarParseError):
        parse_state_machine_dsl('state Root { region Outer { region Inner {} } }')
