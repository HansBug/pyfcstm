import itertools

import pytest

from pyfcstm.dsl import (
    parse_condition,
    GrammarParseError,
    SyntaxFailError,
)
from pyfcstm.dsl.node import *


_COND_PRIORITY_OPERATORS = (
    "==",
    "!=",
    "iff",
    "&&",
    "and",
    "xor",
    "||",
    "or",
    "=>",
    "implies",
)

_COND_PRIORITY = {
    "==": 50,
    "!=": 50,
    "iff": 50,
    "&&": 40,
    "and": 40,
    "xor": 30,
    "||": 20,
    "or": 20,
    "=>": 10,
    "implies": 10,
}

_COND_RIGHT_ASSOC = {"=>", "implies"}

_COND_CANONICAL_OP = {
    "and": "&&",
    "or": "||",
    "implies": "=>",
}

_COND_ATOM_NAMES = tuple("abcdefghijklmnopqrstuvwxyz")

_NUM_COMPARE_OPERATORS = ("<", ">", "<=", ">=", "==", "!=")

_NUMERIC_OPERAND_SHAPES = (
    "name",
    "integer",
    "paren_name",
    "unary_name",
    "bitwise_pair",
    "paren_bitwise_pair",
    "bitwise_chain",
)

_NUMERIC_CARET_BOUNDARY_SHAPES = (
    "name",
    "bitwise_pair",
    "paren_bitwise_pair",
    "bitwise_chain",
)


def _cond_atom(name):
    return BinaryOp(expr1=Name(name=name), op=">", expr2=Integer(raw="0"))


def _canonical_cond_op(op):
    return _COND_CANONICAL_OP.get(op, op)


def _expected_cond_chain(operators, names=None):
    if names is None:
        names = _COND_ATOM_NAMES[: len(operators) + 1]
    values = [_cond_atom(names[0])]
    ops = []

    def reduce_once():
        op = ops.pop()
        right = values.pop()
        left = values.pop()
        values.append(BinaryOp(left, _canonical_cond_op(op), right))

    for op, value in zip(operators, (_cond_atom(name) for name in names[1:])):
        while ops:
            top = ops[-1]
            incoming_precedence = _COND_PRIORITY[op]
            top_precedence = _COND_PRIORITY[top]
            if op in _COND_RIGHT_ASSOC:
                should_reduce = incoming_precedence < top_precedence
            else:
                should_reduce = incoming_precedence <= top_precedence
            if not should_reduce:
                break
            reduce_once()
        ops.append(op)
        values.append(value)

    while ops:
        reduce_once()

    assert len(values) == 1
    return values[0]


def _condition_chain_text(operators, names=None):
    if names is None:
        names = _COND_ATOM_NAMES[: len(operators) + 1]
    parts = [f"{names[0]} > 0"]
    for op, name in zip(operators, names[1:]):
        parts.append(op)
        parts.append(f"{name} > 0")
    return " ".join(parts)


def _cond_chain_names(offset, operators):
    return _COND_ATOM_NAMES[offset : offset + len(operators) + 1]


def _condition_ternary_text(cond_ops, true_ops, false_ops):
    cond_text = _condition_chain_text(cond_ops, _cond_chain_names(0, cond_ops))
    true_text = _condition_chain_text(true_ops, _cond_chain_names(8, true_ops))
    false_text = _condition_chain_text(false_ops, _cond_chain_names(16, false_ops))
    return f"({cond_text}) ? {true_text} : {false_text}"


def _expected_condition_ternary(cond_ops, true_ops, false_ops):
    return ConditionalOp(
        cond=_expected_cond_chain(cond_ops, _cond_chain_names(0, cond_ops)),
        value_true=_expected_cond_chain(true_ops, _cond_chain_names(8, true_ops)),
        value_false=_expected_cond_chain(false_ops, _cond_chain_names(16, false_ops)),
    )


def _simple_ternary_expr():
    return ConditionalOp(
        cond=_cond_atom("a"),
        value_true=_cond_atom("b"),
        value_false=_cond_atom("c"),
    )


def _name_expr(name):
    return Name(name=name)


def _binary_expr(left, op, right):
    return BinaryOp(expr1=left, op=op, expr2=right)


def _numeric_operand(shape, names, raw="1"):
    if shape == "name":
        return names[0], _name_expr(names[0])
    elif shape == "integer":
        return raw, Integer(raw=raw)
    elif shape == "paren_name":
        return f"({names[0]})", Paren(expr=_name_expr(names[0]))
    elif shape == "unary_name":
        return f"-{names[0]}", UnaryOp(op="-", expr=_name_expr(names[0]))
    elif shape == "bitwise_pair":
        return (
            f"{names[0]} ^ {names[1]}",
            _binary_expr(_name_expr(names[0]), "^", _name_expr(names[1])),
        )
    elif shape == "paren_bitwise_pair":
        return (
            f"({names[0]} ^ {names[1]})",
            Paren(expr=_binary_expr(_name_expr(names[0]), "^", _name_expr(names[1]))),
        )
    elif shape == "bitwise_chain":
        return (
            f"{names[0]} ^ {names[1]} ^ {names[2]}",
            _binary_expr(
                _binary_expr(_name_expr(names[0]), "^", _name_expr(names[1])),
                "^",
                _name_expr(names[2]),
            ),
        )
    else:
        raise ValueError(f"Unknown numeric operand shape: {shape!r}")


def _numeric_comparison_text_and_expr(
    op,
    left_shape="bitwise_pair",
    right_shape="bitwise_pair",
    left_names=("a", "b", "c"),
    right_names=("d", "e", "f"),
    left_raw="1",
    right_raw="2",
):
    left_text, left_expr = _numeric_operand(left_shape, left_names, left_raw)
    right_text, right_expr = _numeric_operand(right_shape, right_names, right_raw)
    return (
        f"{left_text} {op} {right_text}",
        _binary_expr(left_expr, op, right_expr),
    )


def _two_numeric_comparisons_text_and_expr(
    left_op,
    right_op,
    left_left_shape,
    left_right_shape,
    right_left_shape,
    right_right_shape,
):
    left_text, left_expr = _numeric_comparison_text_and_expr(
        left_op,
        left_left_shape,
        left_right_shape,
        left_names=("a", "b", "c"),
        right_names=("d", "e", "f"),
        left_raw="1",
        right_raw="2",
    )
    right_text, right_expr = _numeric_comparison_text_and_expr(
        right_op,
        right_left_shape,
        right_right_shape,
        left_names=("g", "h", "i"),
        right_names=("j", "k", "l"),
        left_raw="3",
        right_raw="4",
    )
    return left_text, left_expr, right_text, right_expr


@pytest.mark.unittest
class TestDSLCondition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            ("true", Condition(expr=Boolean(raw="true"))),
            ("false", Condition(expr=Boolean(raw="false"))),
            ("True", Condition(expr=Boolean(raw="true"))),
            ("FALSE", Condition(expr=Boolean(raw="false"))),
            (
                "1 < 2",
                Condition(
                    expr=BinaryOp(
                        expr1=Integer(raw="1"), op="<", expr2=Integer(raw="2")
                    )
                ),
            ),
            (
                "3.14 > 2",
                Condition(
                    expr=BinaryOp(
                        expr1=Float(raw="3.14"), op=">", expr2=Integer(raw="2")
                    )
                ),
            ),
            (
                "5 <= 10",
                Condition(
                    expr=BinaryOp(
                        expr1=Integer(raw="5"), op="<=", expr2=Integer(raw="10")
                    )
                ),
            ),
            (
                "7.5 >= 7",
                Condition(
                    expr=BinaryOp(
                        expr1=Float(raw="7.5"), op=">=", expr2=Integer(raw="7")
                    )
                ),
            ),
            (
                "42 == 42",
                Condition(
                    expr=BinaryOp(
                        expr1=Integer(raw="42"), op="==", expr2=Integer(raw="42")
                    )
                ),
            ),
            (
                "3.14 != 3",
                Condition(
                    expr=BinaryOp(
                        expr1=Float(raw="3.14"), op="!=", expr2=Integer(raw="3")
                    )
                ),
            ),
            ("(true)", Condition(expr=Paren(expr=Boolean(raw="true")))),
            (
                "(1 < 2)",
                Condition(
                    expr=Paren(
                        expr=BinaryOp(
                            expr1=Integer(raw="1"), op="<", expr2=Integer(raw="2")
                        )
                    )
                ),
            ),
            ("((true))", Condition(expr=Paren(expr=Paren(expr=Boolean(raw="true"))))),
            ("!true", Condition(expr=UnaryOp(op="!", expr=Boolean(raw="true")))),
            ("not false", Condition(expr=UnaryOp(op="!", expr=Boolean(raw="false")))),
            (
                "!(1 < 2)",
                Condition(
                    expr=UnaryOp(
                        op="!",
                        expr=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="1"), op="<", expr2=Integer(raw="2")
                            )
                        ),
                    )
                ),
            ),
            (
                "not(3 > 4)",
                Condition(
                    expr=UnaryOp(
                        op="!",
                        expr=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="3"), op=">", expr2=Integer(raw="4")
                            )
                        ),
                    )
                ),
            ),
            (
                "true && true",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"), op="&&", expr2=Boolean(raw="true")
                    )
                ),
            ),
            (
                "false and true",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="false"), op="&&", expr2=Boolean(raw="true")
                    )
                ),
            ),
            (
                "(1 < 2) && (3 > 4)",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="1"), op="<", expr2=Integer(raw="2")
                            )
                        ),
                        op="&&",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="3"), op=">", expr2=Integer(raw="4")
                            )
                        ),
                    )
                ),
            ),
            (
                "true && false && true",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Boolean(raw="true"),
                            op="&&",
                            expr2=Boolean(raw="false"),
                        ),
                        op="&&",
                        expr2=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "true || false",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"), op="||", expr2=Boolean(raw="false")
                    )
                ),
            ),
            (
                "false or true",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="false"), op="||", expr2=Boolean(raw="true")
                    )
                ),
            ),
            (
                "(1 < 2) || (3 > 4)",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="1"), op="<", expr2=Integer(raw="2")
                            )
                        ),
                        op="||",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=Integer(raw="3"), op=">", expr2=Integer(raw="4")
                            )
                        ),
                    )
                ),
            ),
            (
                "false || false || true",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Boolean(raw="false"),
                            op="||",
                            expr2=Boolean(raw="false"),
                        ),
                        op="||",
                        expr2=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "true && false || true",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Boolean(raw="true"),
                            op="&&",
                            expr2=Boolean(raw="false"),
                        ),
                        op="||",
                        expr2=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "false || true && true",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="false"),
                        op="||",
                        expr2=BinaryOp(
                            expr1=Boolean(raw="true"),
                            op="&&",
                            expr2=Boolean(raw="true"),
                        ),
                    )
                ),
            ),
            (
                "true || false && false",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"),
                        op="||",
                        expr2=BinaryOp(
                            expr1=Boolean(raw="false"),
                            op="&&",
                            expr2=Boolean(raw="false"),
                        ),
                    )
                ),
            ),
            (
                "(true || false) && false",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Boolean(raw="true"),
                                op="||",
                                expr2=Boolean(raw="false"),
                            )
                        ),
                        op="&&",
                        expr2=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "!(true && false) || true",
                Condition(
                    expr=BinaryOp(
                        expr1=UnaryOp(
                            op="!",
                            expr=Paren(
                                expr=BinaryOp(
                                    expr1=Boolean(raw="true"),
                                    op="&&",
                                    expr2=Boolean(raw="false"),
                                )
                            ),
                        ),
                        op="||",
                        expr2=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "1 + 2 < 4",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"), op="+", expr2=Integer(raw="2")
                        ),
                        op="<",
                        expr2=Integer(raw="4"),
                    )
                ),
            ),
            (
                "3 * 4 > 10",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="3"), op="*", expr2=Integer(raw="4")
                        ),
                        op=">",
                        expr2=Integer(raw="10"),
                    )
                ),
            ),
            (
                "5 - 2 <= 3",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="5"), op="-", expr2=Integer(raw="2")
                        ),
                        op="<=",
                        expr2=Integer(raw="3"),
                    )
                ),
            ),
            (
                "10 / 2 >= 4",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="10"), op="/", expr2=Integer(raw="2")
                        ),
                        op=">=",
                        expr2=Integer(raw="4"),
                    )
                ),
            ),
            (
                "2 ** 3 == 8",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="2"), op="**", expr2=Integer(raw="3")
                        ),
                        op="==",
                        expr2=Integer(raw="8"),
                    )
                ),
            ),
            (
                "7 % 3 != 2",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="7"), op="%", expr2=Integer(raw="3")
                        ),
                        op="!=",
                        expr2=Integer(raw="2"),
                    )
                ),
            ),
            (
                "1 + 2 * 3 < 10",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"),
                            op="+",
                            expr2=BinaryOp(
                                expr1=Integer(raw="2"), op="*", expr2=Integer(raw="3")
                            ),
                        ),
                        op="<",
                        expr2=Integer(raw="10"),
                    )
                ),
            ),
            (
                "(1 + 2) * 3 > 5",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="1"),
                                    op="+",
                                    expr2=Integer(raw="2"),
                                )
                            ),
                            op="*",
                            expr2=Integer(raw="3"),
                        ),
                        op=">",
                        expr2=Integer(raw="5"),
                    )
                ),
            ),
            (
                "2 ** 3 + 1 == 9",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=BinaryOp(
                                expr1=Integer(raw="2"), op="**", expr2=Integer(raw="3")
                            ),
                            op="+",
                            expr2=Integer(raw="1"),
                        ),
                        op="==",
                        expr2=Integer(raw="9"),
                    )
                ),
            ),
            (
                "10 - 5 / 2.5 == 8",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="10"),
                            op="-",
                            expr2=BinaryOp(
                                expr1=Integer(raw="5"), op="/", expr2=Float(raw="2.5")
                            ),
                        ),
                        op="==",
                        expr2=Integer(raw="8"),
                    )
                ),
            ),
            (
                "+1 < 2",
                Condition(
                    expr=BinaryOp(
                        expr1=UnaryOp(op="+", expr=Integer(raw="1")),
                        op="<",
                        expr2=Integer(raw="2"),
                    )
                ),
            ),
            (
                "-1 > -2",
                Condition(
                    expr=BinaryOp(
                        expr1=UnaryOp(op="-", expr=Integer(raw="1")),
                        op=">",
                        expr2=UnaryOp(op="-", expr=Integer(raw="2")),
                    )
                ),
            ),
            (
                "-(1 + 2) < 0",
                Condition(
                    expr=BinaryOp(
                        expr1=UnaryOp(
                            op="-",
                            expr=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="1"),
                                    op="+",
                                    expr2=Integer(raw="2"),
                                )
                            ),
                        ),
                        op="<",
                        expr2=Integer(raw="0"),
                    )
                ),
            ),
            (
                "1 << 2 == 4",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"), op="<<", expr2=Integer(raw="2")
                        ),
                        op="==",
                        expr2=Integer(raw="4"),
                    )
                ),
            ),
            (
                "8 >> 1 == 4",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="8"), op=">>", expr2=Integer(raw="1")
                        ),
                        op="==",
                        expr2=Integer(raw="4"),
                    )
                ),
            ),
            (
                "5 & 3 == 1",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="5"), op="&", expr2=Integer(raw="3")
                        ),
                        op="==",
                        expr2=Integer(raw="1"),
                    )
                ),
            ),
            (
                "5 | 3 == 7",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="5"), op="|", expr2=Integer(raw="3")
                        ),
                        op="==",
                        expr2=Integer(raw="7"),
                    )
                ),
            ),
            (
                "5 ^ 3 == 6",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="5"), op="^", expr2=Integer(raw="3")
                        ),
                        op="==",
                        expr2=Integer(raw="6"),
                    )
                ),
            ),
            (
                "pi > 3",
                Condition(
                    expr=BinaryOp(
                        expr1=Constant(raw="pi"), op=">", expr2=Integer(raw="3")
                    )
                ),
            ),
            (
                "E < 3",
                Condition(
                    expr=BinaryOp(
                        expr1=Constant(raw="E"), op="<", expr2=Integer(raw="3")
                    )
                ),
            ),
            (
                "tau > 6",
                Condition(
                    expr=BinaryOp(
                        expr1=Constant(raw="tau"), op=">", expr2=Integer(raw="6")
                    )
                ),
            ),
            (
                "sin(0) == 0",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(func="sin", expr=Integer(raw="0")),
                        op="==",
                        expr2=Integer(raw="0"),
                    )
                ),
            ),
            (
                "cos(0) == 1",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(func="cos", expr=Integer(raw="0")),
                        op="==",
                        expr2=Integer(raw="1"),
                    )
                ),
            ),
            (
                "sqrt(4) == 2",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(func="sqrt", expr=Integer(raw="4")),
                        op="==",
                        expr2=Integer(raw="2"),
                    )
                ),
            ),
            (
                "log(1) == 0",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(func="log", expr=Integer(raw="1")),
                        op="==",
                        expr2=Integer(raw="0"),
                    )
                ),
            ),
            (
                "sin(pi/2) > cos(pi)",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(
                            func="sin",
                            expr=BinaryOp(
                                expr1=Constant(raw="pi"), op="/", expr2=Integer(raw="2")
                            ),
                        ),
                        op=">",
                        expr2=UFunc(func="cos", expr=Constant(raw="pi")),
                    )
                ),
            ),
            (
                "sqrt(1 + 4) == 2 + 1",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(
                            func="sqrt",
                            expr=BinaryOp(
                                expr1=Integer(raw="1"), op="+", expr2=Integer(raw="4")
                            ),
                        ),
                        op="==",
                        expr2=BinaryOp(
                            expr1=Integer(raw="2"), op="+", expr2=Integer(raw="1")
                        ),
                    )
                ),
            ),
            (
                "abs(-1) == 1",
                Condition(
                    expr=BinaryOp(
                        expr1=UFunc(
                            func="abs", expr=UnaryOp(op="-", expr=Integer(raw="1"))
                        ),
                        op="==",
                        expr2=Integer(raw="1"),
                    )
                ),
            ),
            (
                "(1 < 2) && (3 <= 4) || !(5 > 6)",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="1"),
                                    op="<",
                                    expr2=Integer(raw="2"),
                                )
                            ),
                            op="&&",
                            expr2=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="3"),
                                    op="<=",
                                    expr2=Integer(raw="4"),
                                )
                            ),
                        ),
                        op="||",
                        expr2=UnaryOp(
                            op="!",
                            expr=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="5"),
                                    op=">",
                                    expr2=Integer(raw="6"),
                                )
                            ),
                        ),
                    )
                ),
            ),
            (
                "sin(pi/2) > 0 && cos(pi) < 0 || sqrt(4) == 2",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=BinaryOp(
                                expr1=UFunc(
                                    func="sin",
                                    expr=BinaryOp(
                                        expr1=Constant(raw="pi"),
                                        op="/",
                                        expr2=Integer(raw="2"),
                                    ),
                                ),
                                op=">",
                                expr2=Integer(raw="0"),
                            ),
                            op="&&",
                            expr2=BinaryOp(
                                expr1=UFunc(func="cos", expr=Constant(raw="pi")),
                                op="<",
                                expr2=Integer(raw="0"),
                            ),
                        ),
                        op="||",
                        expr2=BinaryOp(
                            expr1=UFunc(func="sqrt", expr=Integer(raw="4")),
                            op="==",
                            expr2=Integer(raw="2"),
                        ),
                    )
                ),
            ),
            (
                "true && (false || (1 < 2) && (3 > 4))",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"),
                        op="&&",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=Boolean(raw="false"),
                                op="||",
                                expr2=BinaryOp(
                                    expr1=Paren(
                                        expr=BinaryOp(
                                            expr1=Integer(raw="1"),
                                            op="<",
                                            expr2=Integer(raw="2"),
                                        )
                                    ),
                                    op="&&",
                                    expr2=Paren(
                                        expr=BinaryOp(
                                            expr1=Integer(raw="3"),
                                            op=">",
                                            expr2=Integer(raw="4"),
                                        )
                                    ),
                                ),
                            )
                        ),
                    )
                ),
            ),
            (
                "2 ** 2 ** 2 == 16",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="2"),
                            op="**",
                            expr2=BinaryOp(
                                expr1=Integer(raw="2"), op="**", expr2=Integer(raw="2")
                            ),
                        ),
                        op="==",
                        expr2=Integer(raw="16"),
                    )
                ),
            ),
            (
                "2 ** 3 ** 2 == 512",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="2"),
                            op="**",
                            expr2=BinaryOp(
                                expr1=Integer(raw="3"), op="**", expr2=Integer(raw="2")
                            ),
                        ),
                        op="==",
                        expr2=Integer(raw="512"),
                    )
                ),
            ),
            (
                "1 + 2 * 3 ** 2 == 19",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"),
                            op="+",
                            expr2=BinaryOp(
                                expr1=Integer(raw="2"),
                                op="*",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="3"),
                                    op="**",
                                    expr2=Integer(raw="2"),
                                ),
                            ),
                        ),
                        op="==",
                        expr2=Integer(raw="19"),
                    )
                ),
            ),
            (
                "1 << 2 + 3 == 32",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"),
                            op="<<",
                            expr2=BinaryOp(
                                expr1=Integer(raw="2"), op="+", expr2=Integer(raw="3")
                            ),
                        ),
                        op="==",
                        expr2=Integer(raw="32"),
                    )
                ),
            ),
            (
                "(1 << 2) + 3 == 7",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Paren(
                                expr=BinaryOp(
                                    expr1=Integer(raw="1"),
                                    op="<<",
                                    expr2=Integer(raw="2"),
                                )
                            ),
                            op="+",
                            expr2=Integer(raw="3"),
                        ),
                        op="==",
                        expr2=Integer(raw="7"),
                    )
                ),
            ),
            (
                "1 + 2 * 3 > 4 && 5 - 6 / 3 < 4",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=BinaryOp(
                                expr1=Integer(raw="1"),
                                op="+",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="2"),
                                    op="*",
                                    expr2=Integer(raw="3"),
                                ),
                            ),
                            op=">",
                            expr2=Integer(raw="4"),
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=BinaryOp(
                                expr1=Integer(raw="5"),
                                op="-",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="6"),
                                    op="/",
                                    expr2=Integer(raw="3"),
                                ),
                            ),
                            op="<",
                            expr2=Integer(raw="4"),
                        ),
                    )
                ),
            ),
            (
                "((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="1"),
                                        op="<",
                                        expr2=Integer(raw="2"),
                                    )
                                ),
                                op="&&",
                                expr2=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="3"),
                                        op=">",
                                        expr2=Integer(raw="4"),
                                    )
                                ),
                            )
                        ),
                        op="||",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=UnaryOp(
                                    op="!",
                                    expr=Paren(
                                        expr=BinaryOp(
                                            expr1=Integer(raw="5"),
                                            op="==",
                                            expr2=Integer(raw="5"),
                                        )
                                    ),
                                ),
                                op="&&",
                                expr2=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="6"),
                                        op="!=",
                                        expr2=Integer(raw="7"),
                                    )
                                ),
                            )
                        ),
                    )
                ),
            ),
            (
                "sin(pi/2) * cos(0) > sqrt(4) / 2 && log(E) == 1",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=BinaryOp(
                                expr1=UFunc(
                                    func="sin",
                                    expr=BinaryOp(
                                        expr1=Constant(raw="pi"),
                                        op="/",
                                        expr2=Integer(raw="2"),
                                    ),
                                ),
                                op="*",
                                expr2=UFunc(func="cos", expr=Integer(raw="0")),
                            ),
                            op=">",
                            expr2=BinaryOp(
                                expr1=UFunc(func="sqrt", expr=Integer(raw="4")),
                                op="/",
                                expr2=Integer(raw="2"),
                            ),
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=UFunc(func="log", expr=Constant(raw="E")),
                            op="==",
                            expr2=Integer(raw="1"),
                        ),
                    )
                ),
            ),
            (
                "true && false || true && !(false || true && false)",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Boolean(raw="true"),
                            op="&&",
                            expr2=Boolean(raw="false"),
                        ),
                        op="||",
                        expr2=BinaryOp(
                            expr1=Boolean(raw="true"),
                            op="&&",
                            expr2=UnaryOp(
                                op="!",
                                expr=Paren(
                                    expr=BinaryOp(
                                        expr1=Boolean(raw="false"),
                                        op="||",
                                        expr2=BinaryOp(
                                            expr1=Boolean(raw="true"),
                                            op="&&",
                                            expr2=Boolean(raw="false"),
                                        ),
                                    )
                                ),
                            ),
                        ),
                    )
                ),
            ),
            (
                "1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Integer(raw="1"),
                            op="+",
                            expr2=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=Integer(raw="2"),
                                    op="*",
                                    expr2=BinaryOp(
                                        expr1=Integer(raw="3"),
                                        op="**",
                                        expr2=Integer(raw="2"),
                                    ),
                                ),
                                op="/",
                                expr2=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="4"),
                                        op="%",
                                        expr2=Integer(raw="3"),
                                    )
                                ),
                            ),
                        ),
                        op=">=",
                        expr2=BinaryOp(
                            expr1=BinaryOp(
                                expr1=Integer(raw="10"), op="-", expr2=Integer(raw="5")
                            ),
                            op="<<",
                            expr2=Integer(raw="1"),
                        ),
                    )
                ),
            ),
            (
                "x < 5",
                Condition(
                    expr=BinaryOp(expr1=Name(name="x"), op="<", expr2=Integer(raw="5"))
                ),
            ),
            (
                "foo == bar",
                Condition(
                    expr=BinaryOp(
                        expr1=Name(name="foo"), op="==", expr2=Name(name="bar")
                    )
                ),
            ),
            (
                "a + b < c",
                Condition(
                    expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="a"), op="+", expr2=Name(name="b")
                        ),
                        op="<",
                        expr2=Name(name="c"),
                    )
                ),
            ),
            (
                "!!true",
                Condition(
                    expr=UnaryOp(op="!", expr=UnaryOp(op="!", expr=Boolean(raw="true")))
                ),
            ),
            (
                "not!false",
                Condition(
                    expr=UnaryOp(
                        op="!", expr=UnaryOp(op="!", expr=Boolean(raw="false"))
                    )
                ),
            ),
            (
                "TRUE and FALSE",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"), op="&&", expr2=Boolean(raw="false")
                    )
                ),
            ),
            (
                "True and False",
                Condition(
                    expr=BinaryOp(
                        expr1=Boolean(raw="true"), op="&&", expr2=Boolean(raw="false")
                    )
                ),
            ),
            (
                "e < 3",
                Condition(
                    expr=BinaryOp(expr1=Name(name="e"), op="<", expr2=Integer(raw="3"))
                ),
            ),
            (
                "(true) ? true : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(true) ? true : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(true) ? true : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="true"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(true) ? False : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(true) ? False : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(true) ? False : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=Boolean(raw="false"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(true) ? x >=0 : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(true) ? x >=0 : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(true) ? x >=0 : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="true"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(False) ? true : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(False) ? true : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(False) ? true : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="true"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(False) ? False : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(False) ? False : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(False) ? False : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=Boolean(raw="false"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(False) ? x >=0 : true",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(False) ? x >=0 : False",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(False) ? x >=0 : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=Boolean(raw="false"),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(x >=0) ? true : true",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(x >=0) ? true : False",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(x >=0) ? true : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="true"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(x >=0) ? False : true",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(x >=0) ? False : False",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="false"),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(x >=0) ? False : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=Boolean(raw="false"),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(x >=0) ? x >=0 : true",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="true"),
                    )
                ),
            ),
            (
                "(x >=0) ? x >=0 : False",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=Boolean(raw="false"),
                    )
                ),
            ),
            (
                "(x >=0) ? x >=0 : x >=0",
                Condition(
                    expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_true=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                        value_false=BinaryOp(
                            expr1=Name(name="x"), op=">=", expr2=Integer(raw="0")
                        ),
                    )
                ),
            ),
            (
                "(a >1)== (a < 1)",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Name(name="a"), op=">", expr2=Integer(raw="1")
                            )
                        ),
                        op="==",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=Name(name="a"), op="<", expr2=Integer(raw="1")
                            )
                        ),
                    )
                ),
            ),
            # comparison between boolean expressions
            (
                "(a > 1)!= (a<1)",
                Condition(
                    expr=BinaryOp(
                        expr1=Paren(
                            expr=BinaryOp(
                                expr1=Name(name="a"), op=">", expr2=Integer(raw="1")
                            )
                        ),
                        op="!=",
                        expr2=Paren(
                            expr=BinaryOp(
                                expr1=Name(name="a"), op="<", expr2=Integer(raw="1")
                            )
                        ),
                    )
                ),
            ),
            # comparison between boolean expressions
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_condition(input_text) == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            ("true", "True"),
            ("false", "False"),
            ("True", "True"),
            ("FALSE", "False"),
            ("1 < 2", "1 < 2"),
            ("3.14 > 2", "3.14 > 2"),
            ("5 <= 10", "5 <= 10"),
            ("7.5 >= 7", "7.5 >= 7"),
            ("42 == 42", "42 == 42"),
            ("3.14 != 3", "3.14 != 3"),
            ("(true)", "(True)"),
            ("(1 < 2)", "(1 < 2)"),
            ("((true))", "((True))"),
            ("!true", "!True"),
            ("not false", "!False"),
            ("!(1 < 2)", "!(1 < 2)"),
            ("not(3 > 4)", "!(3 > 4)"),
            ("true && true", "True && True"),
            ("false and true", "False && True"),
            ("(1 < 2) && (3 > 4)", "(1 < 2) && (3 > 4)"),
            ("true && false && true", "True && False && True"),
            ("true || false", "True || False"),
            ("false or true", "False || True"),
            ("(1 < 2) || (3 > 4)", "(1 < 2) || (3 > 4)"),
            ("false || false || true", "False || False || True"),
            ("true && false || true", "True && False || True"),
            ("false || true && true", "False || True && True"),
            ("true || false && false", "True || False && False"),
            ("(true || false) && false", "(True || False) && False"),
            ("!(true && false) || true", "!(True && False) || True"),
            ("1 + 2 < 4", "1 + 2 < 4"),
            ("3 * 4 > 10", "3 * 4 > 10"),
            ("5 - 2 <= 3", "5 - 2 <= 3"),
            ("10 / 2 >= 4", "10 / 2 >= 4"),
            ("2 ** 3 == 8", "2 ** 3 == 8"),
            ("7 % 3 != 2", "7 % 3 != 2"),
            ("1 + 2 * 3 < 10", "1 + 2 * 3 < 10"),
            ("(1 + 2) * 3 > 5", "(1 + 2) * 3 > 5"),
            ("2 ** 3 + 1 == 9", "2 ** 3 + 1 == 9"),
            ("10 - 5 / 2.5 == 8", "10 - 5 / 2.5 == 8"),
            ("+1 < 2", "+1 < 2"),
            ("-1 > -2", "-1 > -2"),
            ("-(1 + 2) < 0", "-(1 + 2) < 0"),
            ("1 << 2 == 4", "1 << 2 == 4"),
            ("8 >> 1 == 4", "8 >> 1 == 4"),
            ("5 & 3 == 1", "5 & 3 == 1"),
            ("5 | 3 == 7", "5 | 3 == 7"),
            ("5 ^ 3 == 6", "5 ^ 3 == 6"),
            ("pi > 3", "pi > 3"),
            ("E < 3", "E < 3"),
            ("tau > 6", "tau > 6"),
            ("sin(0) == 0", "sin(0) == 0"),
            ("cos(0) == 1", "cos(0) == 1"),
            ("sqrt(4) == 2", "sqrt(4) == 2"),
            ("log(1) == 0", "log(1) == 0"),
            ("sin(pi/2) > cos(pi)", "sin(pi / 2) > cos(pi)"),
            ("sqrt(1 + 4) == 2 + 1", "sqrt(1 + 4) == 2 + 1"),
            ("abs(-1) == 1", "abs(-1) == 1"),
            ("(1 < 2) && (3 <= 4) || !(5 > 6)", "(1 < 2) && (3 <= 4) || !(5 > 6)"),
            (
                "sin(pi/2) > 0 && cos(pi) < 0 || sqrt(4) == 2",
                "sin(pi / 2) > 0 && cos(pi) < 0 || sqrt(4) == 2",
            ),
            (
                "true && (false || (1 < 2) && (3 > 4))",
                "True && (False || (1 < 2) && (3 > 4))",
            ),
            ("2 ** 2 ** 2 == 16", "2 ** 2 ** 2 == 16"),
            ("2 ** 3 ** 2 == 512", "2 ** 3 ** 2 == 512"),
            ("1 + 2 * 3 ** 2 == 19", "1 + 2 * 3 ** 2 == 19"),
            ("1 << 2 + 3 == 32", "1 << 2 + 3 == 32"),
            ("(1 << 2) + 3 == 7", "(1 << 2) + 3 == 7"),
            ("1 + 2 * 3 > 4 && 5 - 6 / 3 < 4", "1 + 2 * 3 > 4 && 5 - 6 / 3 < 4"),
            (
                "((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))",
                "((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))",
            ),
            (
                "sin(pi/2) * cos(0) > sqrt(4) / 2 && log(E) == 1",
                "sin(pi / 2) * cos(0) > sqrt(4) / 2 && log(E) == 1",
            ),
            (
                "true && false || true && !(false || true && false)",
                "True && False || True && !(False || True && False)",
            ),
            (
                "1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1",
                "1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1",
            ),
            ("x < 5", "x < 5"),
            ("foo == bar", "foo == bar"),
            ("a + b < c", "a + b < c"),
            ("!!true", "!!True"),
            ("not!false", "!!False"),
            ("TRUE and FALSE", "True && False"),
            ("True and False", "True && False"),
            ("e<3", "e < 3"),
            ("(true) ? true : true", "(True) ? True : True"),
            ("(true) ? true : False", "(True) ? True : False"),
            ("(true) ? true : x >=0", "(True) ? True : x >= 0"),
            ("(true) ? False : true", "(True) ? False : True"),
            ("(true) ? False : False", "(True) ? False : False"),
            ("(true) ? False : x >=0", "(True) ? False : x >= 0"),
            ("(true) ? x >=0 : true", "(True) ? x >= 0 : True"),
            ("(true) ? x >=0 : False", "(True) ? x >= 0 : False"),
            ("(true) ? x >=0 : x >=0", "(True) ? x >= 0 : x >= 0"),
            ("(False) ? true : true", "(False) ? True : True"),
            ("(False) ? true : False", "(False) ? True : False"),
            ("(False) ? true : x >=0", "(False) ? True : x >= 0"),
            ("(False) ? False : true", "(False) ? False : True"),
            ("(False) ? False : False", "(False) ? False : False"),
            ("(False) ? False : x >=0", "(False) ? False : x >= 0"),
            ("(False) ? x >=0 : true", "(False) ? x >= 0 : True"),
            ("(False) ? x >=0 : False", "(False) ? x >= 0 : False"),
            ("(False) ? x >=0 : x >=0", "(False) ? x >= 0 : x >= 0"),
            ("(x >=0) ? true : true", "(x >= 0) ? True : True"),
            ("(x >=0) ? true : False", "(x >= 0) ? True : False"),
            ("(x >=0) ? true : x >=0", "(x >= 0) ? True : x >= 0"),
            ("(x >=0) ? False : true", "(x >= 0) ? False : True"),
            ("(x >=0) ? False : False", "(x >= 0) ? False : False"),
            ("(x >=0) ? False : x >=0", "(x >= 0) ? False : x >= 0"),
            ("(x >=0) ? x >=0 : true", "(x >= 0) ? x >= 0 : True"),
            ("(x >=0) ? x >=0 : False", "(x >= 0) ? x >= 0 : False"),
            ("(x >=0) ? x >=0 : x >=0", "(x >= 0) ? x >= 0 : x >= 0"),
            (
                "(a >1)== (a < 1)",
                "(a > 1) == (a < 1)",
            ),  # comparison between boolean expressions
            (
                "(a > 1)!= (a<1)",
                "(a > 1) != (a < 1)",
            ),  # comparison between boolean expressions
            ("true => false", "True => False"),
            ("true implies false", "True => False"),
            ("true xor false", "True xor False"),
            ("true iff false", "True iff False"),
            ("a > 0 && b > 0 => c > 0", "a > 0 && b > 0 => c > 0"),
            ("a > 0 || b > 0 => c > 0", "a > 0 || b > 0 => c > 0"),
            (
                "a > 0 && b > 0 xor c > 0",
                "a > 0 && b > 0 xor c > 0",
            ),
            (
                "a > 0 xor b > 0 || c > 0",
                "a > 0 xor b > 0 || c > 0",
            ),
            (
                "a > 0 iff b > 0 && c > 0",
                "a > 0 iff b > 0 && c > 0",
            ),
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str):
        assert str(parse_condition(input_text)) == expected_str

    def test_cond_logical_operator_ast_canonicalization(self):
        assert parse_condition("true => false") == Condition(
            expr=BinaryOp(
                expr1=Boolean(raw="true"), op="=>", expr2=Boolean(raw="false")
            )
        )
        assert parse_condition("true implies false") == Condition(
            expr=BinaryOp(
                expr1=Boolean(raw="true"), op="=>", expr2=Boolean(raw="false")
            )
        )
        assert parse_condition("true xor false") == Condition(
            expr=BinaryOp(
                expr1=Boolean(raw="true"), op="xor", expr2=Boolean(raw="false")
            )
        )
        assert parse_condition("true iff false") == Condition(
            expr=BinaryOp(
                expr1=Boolean(raw="true"), op="iff", expr2=Boolean(raw="false")
            )
        )

    def test_cond_xor_keeps_numeric_bitwise_xor_separate(self):
        assert parse_condition("(a > 0) xor (b > 0)") == Condition(
            expr=BinaryOp(
                expr1=Paren(
                    expr=BinaryOp(
                        expr1=Name(name="a"), op=">", expr2=Integer(raw="0")
                    )
                ),
                op="xor",
                expr2=Paren(
                    expr=BinaryOp(
                        expr1=Name(name="b"), op=">", expr2=Integer(raw="0")
                    )
                ),
            )
        )
        assert parse_condition("5 ^ 3 == 6") == Condition(
            expr=BinaryOp(
                expr1=BinaryOp(expr1=Integer(raw="5"), op="^", expr2=Integer(raw="3")),
                op="==",
                expr2=Integer(raw="6"),
            )
        )

    @pytest.mark.parametrize(
        ["op", "left_shape", "right_shape"],
        itertools.product(
            _NUM_COMPARE_OPERATORS,
            _NUMERIC_OPERAND_SHAPES,
            _NUMERIC_OPERAND_SHAPES,
        ),
        ids=lambda item: item,
    )
    def test_numeric_comparison_accepts_bitwise_caret_in_all_operand_shapes(
        self, op, left_shape, right_shape
    ):
        input_text, expected = _numeric_comparison_text_and_expr(
            op, left_shape, right_shape
        )
        assert parse_condition(input_text) == Condition(expr=expected)

    @pytest.mark.parametrize(
        [
            "left_op",
            "right_op",
            "left_left_shape",
            "left_right_shape",
            "right_left_shape",
            "right_right_shape",
        ],
        itertools.product(
            _NUM_COMPARE_OPERATORS,
            _NUM_COMPARE_OPERATORS,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
        ),
        ids=lambda item: item,
    )
    def test_cond_keyword_xor_separates_numeric_caret_comparisons_exhaustively(
        self,
        left_op,
        right_op,
        left_left_shape,
        left_right_shape,
        right_left_shape,
        right_right_shape,
    ):
        left_text, left_expr, right_text, right_expr = (
            _two_numeric_comparisons_text_and_expr(
                left_op,
                right_op,
                left_left_shape,
                left_right_shape,
                right_left_shape,
                right_right_shape,
            )
        )

        assert parse_condition(f"{left_text} xor {right_text}") == Condition(
            expr=_binary_expr(left_expr, "xor", right_expr)
        )

    @pytest.mark.parametrize(
        [
            "left_op",
            "right_op",
            "left_left_shape",
            "left_right_shape",
            "right_left_shape",
            "right_right_shape",
        ],
        itertools.product(
            _NUM_COMPARE_OPERATORS,
            _NUM_COMPARE_OPERATORS,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
            _NUMERIC_CARET_BOUNDARY_SHAPES,
        ),
        ids=lambda item: item,
    )
    def test_parenthesized_cond_caret_between_numeric_caret_comparisons_is_rejected(
        self,
        left_op,
        right_op,
        left_left_shape,
        left_right_shape,
        right_left_shape,
        right_right_shape,
    ):
        left_text, left_expr, right_text, right_expr = (
            _two_numeric_comparisons_text_and_expr(
                left_op,
                right_op,
                left_left_shape,
                left_right_shape,
                right_left_shape,
                right_right_shape,
            )
        )

        with pytest.raises(GrammarParseError) as ei:
            parse_condition(f"({left_text}) ^ ({right_text})")

        assert any(isinstance(error, SyntaxFailError) for error in ei.value.errors)

    @pytest.mark.parametrize(
        ["left_op", "right_op"],
        itertools.product(_NUM_COMPARE_OPERATORS, _NUM_COMPARE_OPERATORS),
        ids=lambda item: item,
    )
    def test_unparenthesized_caret_between_numeric_caret_comparisons_is_rejected(
        self, left_op, right_op
    ):
        input_text = f"a {left_op} b ^ c ^ d {right_op} e"
        with pytest.raises(GrammarParseError) as ei:
            parse_condition(input_text)

        assert any(isinstance(error, SyntaxFailError) for error in ei.value.errors)

    def test_cond_logical_operator_precedence_and_right_associativity(self):
        assert parse_condition("a > 0 => b > 0 => c > 0") == Condition(
            expr=BinaryOp(
                expr1=BinaryOp(expr1=Name(name="a"), op=">", expr2=Integer(raw="0")),
                op="=>",
                expr2=BinaryOp(
                    expr1=BinaryOp(
                        expr1=Name(name="b"), op=">", expr2=Integer(raw="0")
                    ),
                    op="=>",
                    expr2=BinaryOp(
                        expr1=Name(name="c"), op=">", expr2=Integer(raw="0")
                    ),
                ),
            )
        )
        assert parse_condition("a > 0 && b > 0 xor c > 0") == Condition(
            expr=BinaryOp(
                expr1=BinaryOp(
                    expr1=BinaryOp(
                        expr1=Name(name="a"), op=">", expr2=Integer(raw="0")
                    ),
                    op="&&",
                    expr2=BinaryOp(
                        expr1=Name(name="b"), op=">", expr2=Integer(raw="0")
                    ),
                ),
                op="xor",
                expr2=BinaryOp(expr1=Name(name="c"), op=">", expr2=Integer(raw="0")),
            )
        )
        assert parse_condition("a > 0 xor b > 0 || c > 0") == Condition(
            expr=BinaryOp(
                expr1=BinaryOp(
                    expr1=BinaryOp(
                        expr1=Name(name="a"), op=">", expr2=Integer(raw="0")
                    ),
                    op="xor",
                    expr2=BinaryOp(
                        expr1=Name(name="b"), op=">", expr2=Integer(raw="0")
                    ),
                ),
                op="||",
                expr2=BinaryOp(expr1=Name(name="c"), op=">", expr2=Integer(raw="0")),
            )
        )
        assert parse_condition("a > 0 iff b > 0 && c > 0") == Condition(
            expr=BinaryOp(
                expr1=BinaryOp(
                    expr1=BinaryOp(
                        expr1=Name(name="a"), op=">", expr2=Integer(raw="0")
                    ),
                    op="iff",
                    expr2=BinaryOp(
                        expr1=Name(name="b"), op=">", expr2=Integer(raw="0")
                    ),
                ),
                op="&&",
                expr2=BinaryOp(expr1=Name(name="c"), op=">", expr2=Integer(raw="0")),
            )
        )

    def test_cond_xor_is_not_a_global_binary_alias(self):
        from pyfcstm.model.expr import BinaryOp as ModelBinaryOp

        assert BinaryOp.__aliases__.get("^") is None
        assert ModelBinaryOp.__aliases__.get("^") is None

    def test_cond_logical_operator_final_acceptance_smoke(self):
        assert str(parse_condition("x > 0 implies y > 0")) == "x > 0 => y > 0"
        assert str(parse_condition("x > 0 => y > 0 => z > 0")) == (
            "x > 0 => y > 0 => z > 0"
        )
        assert str(parse_condition("manual != 0 xor auto != 0")) == (
            "manual != 0 xor auto != 0"
        )
        assert str(parse_condition("open_limit != 0 iff closed_limit == 0")) == (
            "open_limit != 0 iff closed_limit == 0"
        )
        assert str(parse_condition("5 ^ 3 == 6")) == "5 ^ 3 == 6"

        for input_text in (
            "true ^ false",
            "(x > 0) ^ (y > 0)",
            "x > 0 ^ y > 0",
            "x > 0 -> y > 0",
        ):
            with pytest.raises(GrammarParseError):
                parse_condition(input_text)

    @pytest.mark.parametrize(
        ["operators"],
        [
            (operators,)
            for length in range(1, 5)
            for operators in itertools.product(_COND_PRIORITY_OPERATORS, repeat=length)
        ],
        ids=lambda item: "_".join(item),
    )
    def test_cond_logical_operator_precedence_all_short_chains(self, operators):
        assert parse_condition(_condition_chain_text(operators)) == Condition(
            expr=_expected_cond_chain(operators)
        )

    @pytest.mark.parametrize(
        ["cond_op", "true_op", "false_op"],
        itertools.product(
            _COND_PRIORITY_OPERATORS,
            _COND_PRIORITY_OPERATORS,
            _COND_PRIORITY_OPERATORS,
        ),
        ids=lambda item: item,
    )
    def test_cond_ternary_precedence_all_operator_slots(
        self, cond_op, true_op, false_op
    ):
        cond_ops = (cond_op,)
        true_ops = (true_op,)
        false_ops = (false_op,)
        assert parse_condition(
            _condition_ternary_text(cond_ops, true_ops, false_ops)
        ) == Condition(
            expr=_expected_condition_ternary(cond_ops, true_ops, false_ops)
        )

    @pytest.mark.parametrize(
        ["op"],
        [(op,) for op in _COND_PRIORITY_OPERATORS],
        ids=lambda item: item,
    )
    def test_parenthesized_cond_ternary_can_bind_inside_binary_left_operand(self, op):
        assert parse_condition(f"((a > 0) ? b > 0 : c > 0) {op} d > 0") == Condition(
            expr=BinaryOp(
                expr1=Paren(expr=_simple_ternary_expr()),
                op=_canonical_cond_op(op),
                expr2=_cond_atom("d"),
            )
        )

    @pytest.mark.parametrize(
        ["op"],
        [(op,) for op in _COND_PRIORITY_OPERATORS],
        ids=lambda item: item,
    )
    def test_parenthesized_cond_ternary_can_bind_inside_binary_right_operand(self, op):
        assert parse_condition(f"d > 0 {op} ((a > 0) ? b > 0 : c > 0)") == Condition(
            expr=BinaryOp(
                expr1=_cond_atom("d"),
                op=_canonical_cond_op(op),
                expr2=Paren(expr=_simple_ternary_expr()),
            )
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            ("",),
            (";",),
            ("true;",),
            ("1 + ",),
            (" < 2",),
            ("&&",),
            ("||",),
            ("(",),
            (")",),
            ("(true",),
            ("true)",),
            ("((true)",),
            ("(true))",),
            ("1 < < 2",),
            ("1 > > 2",),
            ("true && || false",),
            ("true and or false",),
            ("1 === 2",),
            ("3 !== 4",),
            ("1 && 2",),
            ("true < false",),
            ("true == 1",),
            ("3.14 || 2.71",),
            ("true + false",),
            ("! 1",),
            ("not 2",),
            ("sin",),
            ("sin()",),
            ("sin(,)",),
            ("sin(1,2)",),
            ("unknown(1)",),
            ("PI",),
            ("E",),
            ("TAU",),
            ("pi()",),
            ("1..2",),
            ("3..",),
            (".5.6",),
            ("1e",),
            ("2e+",),
            ("3e++1",),
            ("truee",),
            ("ffalse",),
            ("TRUEE",),
            ("1 +- 2",),
            ("3 */ 4",),
            ("5 <<>> 6",),
            ("7 &| 8",),
            ("1 + (2",),
            ("sin(1",),
            ("1 + sin()",),
            ("1 + * 2",),
            ("1 + ",),
            (" * 3",),
            ("1 && ",),
            (" || true",),
            ("2 ** ** 2",),
            ("** 2",),
            ("2 **",),
            ("1 + 2 == true",),
            ("(1 < 2)) && ((3 > 4)",),
            ("sin(true) == 1",),
            ("log(false) > 0",),
            ("1 # 2",),
            ("true @ false",),
            ("1 $ 2 < 3",),
            ("1 + 2 * / 3",),
            ("(1 < 2) && (3 > ) || (5 == 5)",),
            ("sin(pi/2) * cos() > sqrt(4) / 2",),
            ("true && false || & true",),
            ("x > 0 -> y > 0",),
            ("true xor 1",),
            ("1 => true",),
            ("true iff 1",),
            ("true ^ false",),
            ("(a > 0) ^ (b > 0)",),
            ("a > 0 ^ b > 0",),
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_condition(input_text)

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
