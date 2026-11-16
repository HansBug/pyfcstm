"""Active-state queries are condition atoms, never numeric function calls."""

import pytest

from pyfcstm.dsl import parse_condition, parse_with_grammar_entry
from pyfcstm.dsl import node as nodes
from pyfcstm.dsl.error import GrammarParseError

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('literal,path', [
    ('"/Root.Motor.Running"', '/Root.Motor.Running'),
    ("'Ready'", 'Ready'), ('""', ''),
    (r'"quote\"slash\\tab\t"', 'quote"slash\\tab\t'),
    (r'"\u72b6\x41\101"', '状AA'),
    ('"\U0001f680"', '\U0001f680'),
    (r'"\ud800"', '\ud800'),
])
def test_active_query_literal_and_source_span(literal, path):
    condition = parse_condition('\n  active(%s)' % literal)
    assert isinstance(condition.expr, nodes.ActiveStateQuery)
    assert condition.expr.path == path
    assert (condition.expr._span.line, condition.expr._span.column) == (2, 3)
    assert parse_condition(str(condition)) == condition


@pytest.mark.parametrize('expression', [
    'active("A")', '!active("A")', 'not active("A")', '(active("A"))',
    'active("A") && active("B") || False', 'active("A") xor True',
    'active("A") implies active("B")', 'active("A") iff active("B")',
    'active("A") == False', '(active("A")) ? active("B") : True',
    'value > 0 && active("A")',
])
def test_condition_operators_round_trip(expression):
    condition = parse_condition(expression)
    assert parse_condition(str(condition)) == condition


def test_active_query_precedence():
    expression = parse_condition('!active("A") && active("B") || active("C")').expr
    assert expression.op == '||'
    assert expression.expr1.op == '&&'
    assert expression.expr1.expr1.op == '!'
    assert expression.expr1.expr1.expr.path == 'A'
    assert expression.expr1.expr2.path == 'B'
    assert expression.expr2.path == 'C'


@pytest.mark.parametrize('statement', [
    '[*] -> A : if [active("B")];',
    'A -> B : if [active("A")];',
    'A -> B :: go + [active("A")];',
    '! A -> B : if [active("A")];',
    'during { if [active("A")] { value = 1; } else if [active("B")] {} }',
    'enter { value = (active("A")) ? 1 : 0; }',
    'A -> B effect { if [active("A")] {} }',
    '>> during after { if [active("A")] {} }',
])
def test_active_query_in_condition_positions(statement):
    program = parse_with_grammar_entry('state Root { state A; state B; %s }' % statement,
                                     'state_machine_dsl')
    assert parse_with_grammar_entry(str(program), 'state_machine_dsl') == program


@pytest.mark.parametrize('expression', [
    'active()', 'active(A)', 'active(1)', 'active("A", "B")',
    'active("A") + 1 > 0', 'active("A") > 0', 'active("A"',
])
def test_invalid_active_query(expression):
    with pytest.raises(GrammarParseError):
        parse_condition(expression)


def test_active_query_cannot_initialize_a_variable():
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry('def int value = (active("A")) ? 1 : 0;', 'def_assignment')
