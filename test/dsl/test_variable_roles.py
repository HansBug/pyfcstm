"""Role declaration syntax, reserved words, source spans, and AST exports."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.dsl.node import DefAssignment, Integer
from pyfcstm.dsl.role import VariableRole

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    "prefix,role,initializer",
    [
        ("def", "control", " = 1"),
        ("control", "control", " = 1"),
        ("input", "input_dynamic", ""),
        ("input dynamic", "input_dynamic", ""),
        ("param", "input_static", " = 1"),
        ("input static", "input_static", " = 1"),
        ("output", "output", " = 1"),
    ],
)
@pytest.mark.parametrize("type_name", ["int", "float"])
@pytest.mark.parametrize("documented", [False, True])
def test_declaration_ast(prefix, role, initializer, type_name, documented):
    declaration = "%s %s value%s;" % (prefix, type_name, initializer)
    source = ("/* measured value */\n" if documented else "") + declaration
    node = parse_with_grammar_entry(source, "def_assignment")
    assert node.role is VariableRole(role)
    assert node.spelling == prefix
    assert str(node.without_docs()) == declaration
    assert node._span.column == 1
    assert node._span.line == (2 if documented else 1)
    assert (node.expr is None) == (role == "input_dynamic")
    assert parse_with_grammar_entry(str(node), "def_assignment") == node


@pytest.mark.parametrize(
    "word", ["control", "input", "dynamic", "static", "param", "output"]
)
@pytest.mark.parametrize(
    "template",
    [
        "def int %s = 0; state Root;",
        "state %s;",
        "state Root { event %s; }",
        "state Root { enter %s {} }",
    ],
)
def test_role_keywords_are_reserved(word, template):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry(template % word, "state_machine_dsl")


@pytest.mark.parametrize(
    "prefix",
    [
        "sensor",
        "input random",
        "control dynamic",
        "param static",
        "dynamic input",
        "input dynamic static",
        "output static",
    ],
)
def test_unknown_declaration_prefix_rejected_by_grammar(prefix):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry(prefix + " int value = 0;", "def_assignment")


@pytest.mark.parametrize(
    "role,prefix,expr",
    [
        (VariableRole.CONTROL, "def", Integer("1")),
        (VariableRole.INPUT_DYNAMIC, "input dynamic", None),
        (VariableRole.INPUT_STATIC, "input static", Integer("1")),
        (VariableRole.OUTPUT, "output", Integer("1")),
    ],
)
def test_programmatic_ast_default_spelling(role, prefix, expr):
    node = DefAssignment("value", "int", expr, role=role)
    assert str(node).startswith(prefix + " int value")
    assert parse_with_grammar_entry(str(node), "def_assignment") == node


@pytest.mark.parametrize("modifier,initializer", [("dynamic", ""), ("static", " = 1")])
@pytest.mark.parametrize("gap", [" ", "\t", "\n", " // sample\n", " # sample\n"])
def test_input_modifier_accepts_normal_token_separators(modifier, initializer, gap):
    node = parse_with_grammar_entry(
        "input%s%s int value%s;" % (gap, modifier, initializer), "def_assignment"
    )
    assert node.spelling == "input " + modifier
    assert str(node) == "input %s int value%s;" % (modifier, initializer)


@pytest.mark.parametrize(
    "prefix,token_names",
    [
        ("def", ["DEF"]),
        ("control", ["CONTROL"]),
        ("input", ["INPUT"]),
        ("input dynamic", ["INPUT", "DYNAMIC"]),
        ("input static", ["INPUT", "STATIC"]),
        ("param", ["PARAM"]),
        ("output", ["OUTPUT"]),
    ],
)
def test_antlr_declaration_context_and_generic_listener(prefix, token_names):
    from antlr4 import (
        CommonTokenStream,
        InputStream,
        ParseTreeListener,
        ParseTreeWalker,
    )
    from pyfcstm.dsl.grammar import GrammarLexer, GrammarParser

    parser = GrammarParser(
        CommonTokenStream(GrammarLexer(InputStream(prefix + " int value;")))
    )
    definition = parser.def_assignment()
    assert definition.ID().getText() == "value"
    assert definition.ASSIGN() is None
    declaration = definition.variable_declaration()
    assert declaration.getRuleIndex() == GrammarParser.RULE_variable_declaration
    assert [
        getattr(declaration, token)().getText() for token in token_names
    ] == prefix.split()
    # Consumers can walk a concrete syntax tree with a generic ANTLR listener.
    ParseTreeWalker().walk(ParseTreeListener(), declaration)
    assert parser.getNumberOfSyntaxErrors() == 0


def test_invalid_declaration_rule_reports_a_grammar_error():
    from antlr4 import CommonTokenStream, InputStream
    from pyfcstm.dsl.grammar import GrammarLexer, GrammarParser
    from pyfcstm.dsl.error import CollectingErrorListener

    parser = GrammarParser(CommonTokenStream(GrammarLexer(InputStream("sensor"))))
    errors = CollectingErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(errors)
    parser.variable_declaration()
    with pytest.raises(GrammarParseError):
        errors.check_errors()
