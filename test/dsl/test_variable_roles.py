"""Role declaration syntax, reserved words, source spans, and AST exports."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.dsl.node import (
    BinaryOp,
    Constant,
    DefAssignment,
    Float,
    HexInt,
    Integer,
    Paren,
    UnaryOp,
    UFunc,
)
from pyfcstm.utils.validate import Span
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
        (VariableRole.INPUT_DYNAMIC, "input", None),
        (VariableRole.INPUT_STATIC, "param", Integer("1")),
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


@pytest.mark.parametrize(
    "role,prefix,expr",
    [
        (VariableRole.INPUT_DYNAMIC, "input", None),
        (VariableRole.INPUT_STATIC, "param", Integer("1")),
    ],
)
def test_declaration_positional_fields_end_with_span(role, prefix, expr):
    span = Span(line=2, column=3)
    node = DefAssignment("value", "int", expr, None, role, prefix, span)
    assert node.role is role
    assert node.spelling == prefix
    assert node._span is span
    assert str(node).startswith(prefix + " int value")


@pytest.mark.parametrize(
    "prefix,role",
    [
        ("def", VariableRole.CONTROL),
        ("control", VariableRole.CONTROL),
        ("input", VariableRole.INPUT_DYNAMIC),
        ("input dynamic", VariableRole.INPUT_DYNAMIC),
        ("param", VariableRole.INPUT_STATIC),
        ("input static", VariableRole.INPUT_STATIC),
        ("output", VariableRole.OUTPUT),
    ],
)
class TestDSLVariableDeclaration:
    @pytest.mark.parametrize(
        "type_name,initializer,expression",
        [
            ("int", "", None),
            ("float", "", None),
            ("int", " = 42", Integer(raw="42")),
            ("int", " = 0x2a", HexInt(raw="0x2a")),
            ("float", " = 1.25e-3", Float(raw="1.25e-3")),
            ("float", " = pi", Constant(raw="pi")),
            ("float", " = sin(pi)", UFunc(func="sin", expr=Constant(raw="pi"))),
            ("int", " = -2", UnaryOp(op="-", expr=Integer(raw="2"))),
            (
                "int",
                " = 1 + 2 * 3",
                BinaryOp(
                    expr1=Integer(raw="1"),
                    op="+",
                    expr2=BinaryOp(
                        expr1=Integer(raw="2"), op="*", expr2=Integer(raw="3")
                    ),
                ),
            ),
            (
                "int",
                " = (1 + 2) * 3",
                BinaryOp(
                    expr1=Paren(
                        expr=BinaryOp(
                            expr1=Integer(raw="1"), op="+", expr2=Integer(raw="2")
                        )
                    ),
                    op="*",
                    expr2=Integer(raw="3"),
                ),
            ),
        ],
    )
    @pytest.mark.parametrize("doc", [None, "measured value"])
    def test_positive_cases(
        self, prefix, role, type_name, initializer, expression, doc
    ):
        # Syntax accepts optional initializers for every role. Model validation
        # separately rejects a dynamic initializer or a missing required value.
        source = ("/* measured value */\n" if doc else "") + "%s %s value%s;" % (
            prefix,
            type_name,
            initializer,
        )
        expected = DefAssignment(
            name="value",
            type=type_name,
            expr=expression,
            doc=doc,
            role=role,
            spelling=prefix,
        )
        actual = parse_with_grammar_entry(source, entry_name="def_assignment")
        assert actual == expected
        assert actual.spelling == expected.spelling

    @pytest.mark.parametrize(
        "declaration",
        [
            "value = 1;",  # Missing type.
            "bool value = True;",  # Unsupported type.
            "int = 1;",  # Missing name.
            "int value",  # Missing terminator.
            "int value 1;",  # Missing assignment operator.
            "int value := 1;",  # Operation syntax is not a declaration.
            "int value = ;",  # Missing initializer expression.
            "int value = 1 + ;",  # Missing operand.
            "int value = other;",  # Initializers are name-free.
            "int value = 1 + other;",  # Nested variable references are forbidden.
            "int value = 1 > 0;",  # Comparisons are not initializer syntax.
            "int value = True && False;",  # Boolean expressions are not initializers.
            "int value = (1 > 0) ? 1 : 0;",  # Conditional initializers are unsupported.
            "float value = sin();",  # A unary function requires an argument.
            "float value = sin(1, 2);",  # A unary function takes only one argument.
            'float value = "text";',  # Only numeric expressions are accepted.
            "int value = 1, second = 2;",  # One name per declaration.
            "int value = 1; state Extra;",  # The declaration entry consumes all input.
        ],
    )
    def test_negative_cases(self, prefix, role, declaration):
        with pytest.raises(GrammarParseError) as error:
            parse_with_grammar_entry(
                prefix + " " + declaration, entry_name="def_assignment"
            )
        assert error.value.errors
