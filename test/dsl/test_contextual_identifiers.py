"""Region and active retain their existing identifier meanings in every scope."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('word', ['region', 'active', 'ordinary'])
@pytest.mark.parametrize('entry,template', [
    ('def_assignment', 'def int {word} = 1;'),
    ('state_definition', 'state {word};'),
    ('state_definition', 'state {word} {{ state Child; [*] -> Child; }}'),
    ('event_definition', 'event {word};'),
    ('enter_definition', 'enter {word} {{ {word} = {word} + 1; }}'),
    ('exit_definition', 'exit abstract {word};'),
    ('during_definition', 'during {word} ref /Root.{word};'),
    ('during_aspect_definition', '>> during before {word} {{}}'),
    ('transition_definition', '[*] -> {word};'),
    ('transition_definition', '{word} -> {word} :: {word};'),
    ('transition_definition', '{word} -> [*] : /Root.{word};'),
    ('transition_force_definition', '! {word} -> {word} :: {word};'),
    ('transition_force_definition', '! {word} -> [*] : {word};'),
    ('history_definition', '[H*] -> {word}.active.region;'),
    ('chain_id', '/{word}.region.active'),
    ('preamble_program', '{word} := 1; {word} = 2;'),
    ('operation_program', '{word} := {word} + 1;'),
    ('num_expression', '{word} + region + active'),
    ('import_statement', 'import "child.fcstm" as {word} {{ var {word} -> {word}; }}'),
    ('import_statement', 'import "child.fcstm" as {word} {{ var {{active, region}} -> {word}; event {word}.active -> /Root.{word}; }}'),
])
def test_contextual_identifier_round_trip(word, entry, template):
    source = template.format(word=word)
    node = parse_with_grammar_entry(source, entry)
    assert parse_with_grammar_entry(str(node), entry) == node
    assert word in str(node)


@pytest.mark.parametrize('word', ['region', 'active'])
def test_contextual_region_names(word):
    program = parse_with_grammar_entry(
        'state active { region %s { state region; [*] -> region; } }' % word,
        'state_machine_dsl',
    )
    assert program.root_state.name == 'active'
    assert program.root_state.regions[0].name == word
