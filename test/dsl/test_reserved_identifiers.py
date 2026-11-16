"""Reserved words cannot become names through ordinary or import syntax."""

import pytest

from pyfcstm.dsl import parse_state_machine_dsl, parse_with_grammar_entry
from pyfcstm.dsl.error import GrammarParseError

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('word', ['region', 'active'])
@pytest.mark.parametrize('entry,template', [
    ('def_assignment', 'def int {word} = 1;'),
    ('state_definition', 'state {word};'),
    ('region_definition', 'region {word} {{}}'),
    ('event_definition', 'event {word};'),
    ('enter_definition', 'enter {word} {{}}'),
    ('exit_definition', 'exit abstract {word};'),
    ('during_definition', 'during {word} ref /Root.run;'),
    ('during_aspect_definition', '>> during before {word} {{}}'),
    ('transition_definition', '[*] -> {word};'),
    ('transition_definition', '{word} -> End :: done;'),
    ('transition_definition', 'Start -> End :: {word};'),
    ('transition_force_definition', '! {word} -> End;'),
    ('history_definition', '[H*] -> Child.{word};'),
    ('chain_id', '/Root.{word}'),
    ('preamble_program', '{word} := 1;'),
    ('operation_program', '{word} := 1;'),
    ('num_expression', '{word} + 1'),
])
def test_reserved_words_are_not_identifiers(word, entry, template):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry(template.format(word=word), entry)


@pytest.mark.parametrize('word', [
    'region', 'active', 'state', 'pseudo', 'enter', 'exit', 'during', 'before',
    'after', 'abstract', 'ref', 'effect', 'if', 'else', 'def', 'var', 'input',
    'control', 'param', 'output', 'event', 'import', 'as', 'named', 'int',
    'float', 'and', 'or', 'not', 'implies', 'iff', 'xor', 'pi', 'E', 'tau',
    'True', 'true', 'TRUE', 'False', 'false', 'FALSE', 'sin', 'log1p',
])
@pytest.mark.parametrize('body', [
    'import "child.fcstm" as {word};',
    'import "child.fcstm" as Child {{ var {word} -> shared; }}',
    'import "child.fcstm" as Child {{ var {{value, {word}}} -> shared; }}',
    'import "child.fcstm" as Child {{ var value -> {word}; }}',
    'import "child.fcstm" as Child {{ event {word} -> /Root.done; }}',
    'import "child.fcstm" as Child {{ event done -> /Root.{word}; }}',
])
def test_import_modes_cannot_turn_reserved_words_into_names(word, body):
    with pytest.raises(GrammarParseError):
        parse_state_machine_dsl('state Root { %s }' % body.format(word=word))


@pytest.mark.parametrize('word', ['ordinary', 'Active', 'Region', 'active_flag', 'region_count'])
def test_identifier_matching_is_case_sensitive_and_whole_word(word):
    source = '''def int %s = 0;
        state Root { state %s; [*] -> %s; event ready;
            import "active-region.fcstm" as Child { var value -> %s; }
        }''' % (word, word, word, word)
    node = parse_state_machine_dsl(source)
    assert node.definitions[0].name == word
    assert node.root_state.substates[0].name == word
    assert parse_state_machine_dsl(str(node)) == node


def test_import_patterns_and_templates_can_contain_keyword_text():
    source = '''state Root { import "child.fcstm" as Child {
        var region_* -> active_$1;
        var *active -> region_${1};
    } }'''
    node = parse_state_machine_dsl(source)
    assert [str(item) for item in node.root_state.imports[0].mappings] == [
        'var region_* -> active_$1;', 'var *active -> region_${1};',
    ]
    assert parse_state_machine_dsl(str(node)) == node
