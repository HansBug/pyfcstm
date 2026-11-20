"""Ordered region declarations remain data-only, round-trippable AST nodes."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl import node as nodes
from pyfcstm.dsl.error import GrammarParseError

pytestmark = pytest.mark.unittest


def test_ordered_regions_and_nested_states():
    source = '''state Root {
        /* motor region */
        region Motor {
            state Running {
                region Inner { state Idle; [*] -> Idle; }
            }
            event stop;
            [*] -> Running;
            Running -> [*] :: stop;
            ! * -> [*] : if [True];
            >> during before prepare { value = 1; }
            >> during after abstract observe;
            >> during before reuse ref /Root.prepare;
            ;
        }
        region Sensor { state Ready; [*] -> Ready; }
    }'''
    program = parse_with_grammar_entry(source, 'state_machine_dsl')
    root = program.root_state
    assert root.substates == []
    assert [region.name for region in root.regions] == ['Motor', 'Sensor']
    motor = root.regions[0]
    assert isinstance(motor, nodes.RegionDefinition)
    assert not isinstance(motor, nodes.StateDefinition)
    assert motor.doc == 'motor region'
    assert motor._span.line == 3
    assert motor._span.column == 9
    assert motor.substates[0].regions[0].name == 'Inner'
    assert [event.name for event in motor.events] == ['stop']
    assert len(motor.transitions) == 2
    assert len(motor.force_transitions) == 1
    assert [type(action) for action in motor.during_aspects] == [
        nodes.DuringAspectOperations, nodes.DuringAspectAbstractFunction,
        nodes.DuringAspectRefFunction,
    ]
    assert parse_with_grammar_entry(str(program), 'state_machine_dsl') == program
    assert str(program).index('region Motor') < str(program).index('region Sensor')
    stripped = program.without_docs()
    assert stripped.root_state.regions[0].doc is None
    assert program.root_state.regions[0].doc == 'motor region'
    assert parse_with_grammar_entry(str(stripped), 'state_machine_dsl') == stripped


@pytest.mark.parametrize('body', ['', ';', 'state A;', 'region R {}'])
def test_empty_syntax_defers_model_validity_checks(body):
    program = parse_with_grammar_entry('state Root { %s }' % body, 'state_machine_dsl')
    assert parse_with_grammar_entry(str(program), 'state_machine_dsl') == program


def test_region_programmatic_defaults_and_single_region():
    region = nodes.RegionDefinition('Only')
    assert region.substates == region.transitions == region.force_transitions == []
    assert region.events == region.during_aspects == []
    assert str(region) == 'region Only {\n}'
    state = nodes.StateDefinition('Root', regions=[region])
    assert parse_with_grammar_entry(str(state), 'state_definition') == state
    assert state.without_docs(recursive=False).regions[0] is region


@pytest.mark.parametrize('statement', [
    'enter {}', 'during {}', 'during before {}', 'exit {}',
    'def int value = 0;', 'region Inner {}', 'import "child.fcstm" as Child;',
    '[H] -> A;',
])
def test_region_rejects_statements_outside_its_scope(statement):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry('state Root { region R { %s } }' % statement,
                                 'state_machine_dsl')


@pytest.mark.parametrize('source', [
    'region R {}', 'state Root { region {} }', 'state Root { region R; }',
    'state Root { pseudo region R {} }', 'state Root { region R named "R" {} }',
    'state Root { region R { state A; }',
])
def test_malformed_region_declarations(source):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry(source, 'state_machine_dsl')
