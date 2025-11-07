import pytest

from pyfcstm.dsl import parse_operation, GrammarParseError, SyntaxFailError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLOperation:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                "a := 5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(name="a", expr=Integer(raw="5"))
                    ]
                ),
            ),
            (
                "variable := 3.14;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="variable", expr=Float(raw="3.14")
                        )
                    ]
                ),
            ),
            (
                "x := pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="x", expr=Constant(raw="pi")
                        )
                    ]
                ),
            ),
            (
                "y := E;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="y", expr=Constant(raw="E")
                        )
                    ]
                ),
            ),
            (
                "y := e;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(name="y", expr=Name(name="e"))
                    ]
                ),
            ),
            (
                "z := tau;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="z", expr=Constant(raw="tau")
                        )
                    ]
                ),
            ),
            (
                "a := +5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a", expr=UnaryOp(op="+", expr=Integer(raw="5"))
                        )
                    ]
                ),
            ),
            (
                "b := -10;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="b", expr=UnaryOp(op="-", expr=Integer(raw="10"))
                        )
                    ]
                ),
            ),
            (
                "c := -(5);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="c",
                            expr=UnaryOp(op="-", expr=Paren(expr=Integer(raw="5"))),
                        )
                    ]
                ),
            ),
            (
                "result := 5 + 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=Integer(raw="5"), op="+", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "diff := 10 - 5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="diff",
                            expr=BinaryOp(
                                expr1=Integer(raw="10"), op="-", expr2=Integer(raw="5")
                            ),
                        )
                    ]
                ),
            ),
            (
                "product := 4 * 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="product",
                            expr=BinaryOp(
                                expr1=Integer(raw="4"), op="*", expr2=Integer(raw="2")
                            ),
                        )
                    ]
                ),
            ),
            (
                "quotient := 10 / 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="quotient",
                            expr=BinaryOp(
                                expr1=Integer(raw="10"), op="/", expr2=Integer(raw="2")
                            ),
                        )
                    ]
                ),
            ),
            (
                "remainder := 10 % 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="remainder",
                            expr=BinaryOp(
                                expr1=Integer(raw="10"), op="%", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "power := 2 ** 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="power",
                            expr=BinaryOp(
                                expr1=Integer(raw="2"), op="**", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "complex_power := 2 ** 3 ** 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="complex_power",
                            expr=BinaryOp(
                                expr1=Integer(raw="2"),
                                op="**",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="3"),
                                    op="**",
                                    expr2=Integer(raw="2"),
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "shift_left := 1 << 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="shift_left",
                            expr=BinaryOp(
                                expr1=Integer(raw="1"), op="<<", expr2=Integer(raw="2")
                            ),
                        )
                    ]
                ),
            ),
            (
                "shift_right := 8 >> 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="shift_right",
                            expr=BinaryOp(
                                expr1=Integer(raw="8"), op=">>", expr2=Integer(raw="2")
                            ),
                        )
                    ]
                ),
            ),
            (
                "bitwise_and := 5 & 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="bitwise_and",
                            expr=BinaryOp(
                                expr1=Integer(raw="5"), op="&", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "bitwise_or := 5 | 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="bitwise_or",
                            expr=BinaryOp(
                                expr1=Integer(raw="5"), op="|", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "bitwise_xor := 5 ^ 3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="bitwise_xor",
                            expr=BinaryOp(
                                expr1=Integer(raw="5"), op="^", expr2=Integer(raw="3")
                            ),
                        )
                    ]
                ),
            ),
            (
                "sine := sin(pi / 2);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="sine",
                            expr=UFunc(
                                func="sin",
                                expr=BinaryOp(
                                    expr1=Constant(raw="pi"),
                                    op="/",
                                    expr2=Integer(raw="2"),
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "logarithm := log(100);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="logarithm",
                            expr=UFunc(func="log", expr=Integer(raw="100")),
                        )
                    ]
                ),
            ),
            (
                "absolute := abs(-5);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="absolute",
                            expr=UFunc(
                                func="abs", expr=UnaryOp(op="-", expr=Integer(raw="5"))
                            ),
                        )
                    ]
                ),
            ),
            (
                "rounded := round(3.7);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="rounded",
                            expr=UFunc(func="round", expr=Float(raw="3.7")),
                        )
                    ]
                ),
            ),
            (
                "a := 5; b := a;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a", expr=Integer(raw="5")
                        ),
                        OperationalDeprecatedAssignment(name="b", expr=Name(name="a")),
                    ]
                ),
            ),
            (
                "x := 10; y := x + 5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="x", expr=Integer(raw="10")
                        ),
                        OperationalDeprecatedAssignment(
                            name="y",
                            expr=BinaryOp(
                                expr1=Name(name="x"), op="+", expr2=Integer(raw="5")
                            ),
                        ),
                    ]
                ),
            ),
            (
                "result := 2 + 3 * 4;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=Integer(raw="2"),
                                op="+",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="3"),
                                    op="*",
                                    expr2=Integer(raw="4"),
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "result := (2 + 3) * 4;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="2"),
                                        op="+",
                                        expr2=Integer(raw="3"),
                                    )
                                ),
                                op="*",
                                expr2=Integer(raw="4"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "complex := 2 * 3 + 4 * 5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="complex",
                            expr=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=Integer(raw="2"),
                                    op="*",
                                    expr2=Integer(raw="3"),
                                ),
                                op="+",
                                expr2=BinaryOp(
                                    expr1=Integer(raw="4"),
                                    op="*",
                                    expr2=Integer(raw="5"),
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "mixed := 2 ** 3 * 4 + 5 / 2 - 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="mixed",
                            expr=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=BinaryOp(
                                        expr1=BinaryOp(
                                            expr1=Integer(raw="2"),
                                            op="**",
                                            expr2=Integer(raw="3"),
                                        ),
                                        op="*",
                                        expr2=Integer(raw="4"),
                                    ),
                                    op="+",
                                    expr2=BinaryOp(
                                        expr1=Integer(raw="5"),
                                        op="/",
                                        expr2=Integer(raw="2"),
                                    ),
                                ),
                                op="-",
                                expr2=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "bitwise_mix := (5 & 3) | (2 << 1);",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="bitwise_mix",
                            expr=BinaryOp(
                                expr1=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="5"),
                                        op="&",
                                        expr2=Integer(raw="3"),
                                    )
                                ),
                                op="|",
                                expr2=Paren(
                                    expr=BinaryOp(
                                        expr1=Integer(raw="2"),
                                        op="<<",
                                        expr2=Integer(raw="1"),
                                    )
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "nested := ((2 + 3) * (4 - 1)) / 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="nested",
                            expr=BinaryOp(
                                expr1=Paren(
                                    expr=BinaryOp(
                                        expr1=Paren(
                                            expr=BinaryOp(
                                                expr1=Integer(raw="2"),
                                                op="+",
                                                expr2=Integer(raw="3"),
                                            )
                                        ),
                                        op="*",
                                        expr2=Paren(
                                            expr=BinaryOp(
                                                expr1=Integer(raw="4"),
                                                op="-",
                                                expr2=Integer(raw="1"),
                                            )
                                        ),
                                    )
                                ),
                                op="/",
                                expr2=Integer(raw="2"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "func_nest := sin(cos(pi));",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="func_nest",
                            expr=UFunc(
                                func="sin",
                                expr=UFunc(func="cos", expr=Constant(raw="pi")),
                            ),
                        )
                    ]
                ),
            ),
            (
                "complex_func := log(abs(sin(pi) + 5));",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="complex_func",
                            expr=UFunc(
                                func="log",
                                expr=UFunc(
                                    func="abs",
                                    expr=BinaryOp(
                                        expr1=UFunc(
                                            func="sin", expr=Constant(raw="pi")
                                        ),
                                        op="+",
                                        expr2=Integer(raw="5"),
                                    ),
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "\n    a := 5;\n    b := a * 2;\n    c := a + b;\n    ",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a", expr=Integer(raw="5")
                        ),
                        OperationalDeprecatedAssignment(
                            name="b",
                            expr=BinaryOp(
                                expr1=Name(name="a"), op="*", expr2=Integer(raw="2")
                            ),
                        ),
                        OperationalDeprecatedAssignment(
                            name="c",
                            expr=BinaryOp(
                                expr1=Name(name="a"), op="+", expr2=Name(name="b")
                            ),
                        ),
                    ]
                ),
            ),
            (
                "complex_expr := 2 ** (3 + 1) * sin(pi/2) / log(E**2) + 5 & 7 | 2;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="complex_expr",
                            expr=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=BinaryOp(
                                        expr1=BinaryOp(
                                            expr1=BinaryOp(
                                                expr1=BinaryOp(
                                                    expr1=Integer(raw="2"),
                                                    op="**",
                                                    expr2=Paren(
                                                        expr=BinaryOp(
                                                            expr1=Integer(raw="3"),
                                                            op="+",
                                                            expr2=Integer(raw="1"),
                                                        )
                                                    ),
                                                ),
                                                op="*",
                                                expr2=UFunc(
                                                    func="sin",
                                                    expr=BinaryOp(
                                                        expr1=Constant(raw="pi"),
                                                        op="/",
                                                        expr2=Integer(raw="2"),
                                                    ),
                                                ),
                                            ),
                                            op="/",
                                            expr2=UFunc(
                                                func="log",
                                                expr=BinaryOp(
                                                    expr1=Constant(raw="E"),
                                                    op="**",
                                                    expr2=Integer(raw="2"),
                                                ),
                                            ),
                                        ),
                                        op="+",
                                        expr2=Integer(raw="5"),
                                    ),
                                    op="&",
                                    expr2=Integer(raw="7"),
                                ),
                                op="|",
                                expr2=Integer(raw="2"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "float_val := 1.234;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="float_val", expr=Float(raw="1.234")
                        )
                    ]
                ),
            ),
            (
                "scientific := 1.2e3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="scientific", expr=Float(raw="1.2e3")
                        )
                    ]
                ),
            ),
            (
                "scientific_neg := 1.2e-3;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="scientific_neg", expr=Float(raw="1.2e-3")
                        )
                    ]
                ),
            ),
            (
                "float_no_int := .5;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="float_no_int", expr=Float(raw=".5")
                        )
                    ]
                ),
            ),
            (
                "\n    a := 5;\n    b := 10;\n    c := a ** 2 + b ** 2;\n    d := sqrt(c);\n    result := sin(d / 10) * cos(pi/4) + log(a * b);\n    ",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a", expr=Integer(raw="5")
                        ),
                        OperationalDeprecatedAssignment(
                            name="b", expr=Integer(raw="10")
                        ),
                        OperationalDeprecatedAssignment(
                            name="c",
                            expr=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=Name(name="a"),
                                    op="**",
                                    expr2=Integer(raw="2"),
                                ),
                                op="+",
                                expr2=BinaryOp(
                                    expr1=Name(name="b"),
                                    op="**",
                                    expr2=Integer(raw="2"),
                                ),
                            ),
                        ),
                        OperationalDeprecatedAssignment(
                            name="d", expr=UFunc(func="sqrt", expr=Name(name="c"))
                        ),
                        OperationalDeprecatedAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=BinaryOp(
                                    expr1=UFunc(
                                        func="sin",
                                        expr=BinaryOp(
                                            expr1=Name(name="d"),
                                            op="/",
                                            expr2=Integer(raw="10"),
                                        ),
                                    ),
                                    op="*",
                                    expr2=UFunc(
                                        func="cos",
                                        expr=BinaryOp(
                                            expr1=Constant(raw="pi"),
                                            op="/",
                                            expr2=Integer(raw="4"),
                                        ),
                                    ),
                                ),
                                op="+",
                                expr2=UFunc(
                                    func="log",
                                    expr=BinaryOp(
                                        expr1=Name(name="a"),
                                        op="*",
                                        expr2=Name(name="b"),
                                    ),
                                ),
                            ),
                        ),
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (true) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="true"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (False) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=Boolean(raw="false"),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Integer(raw="1"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? pi : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=Constant(raw="pi"),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Integer(raw="1"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : pi;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=Constant(raw="pi"),
                            ),
                        )
                    ]
                ),
            ),
            (
                "a := (x >=0) ? x + 1 : x + 1;",
                Operation(
                    stats=[
                        OperationalDeprecatedAssignment(
                            name="a",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="x"),
                                    op=">=",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                                value_false=BinaryOp(
                                    expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                                ),
                            ),
                        )
                    ]
                ),
            ),
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_operation(input_text) == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            ("a := 5;", "a := 5;"),
            ("variable := 3.14;", "variable := 3.14;"),
            ("x := pi;", "x := pi;"),
            ("y := E;", "y := E;"),
            ("y := e;", "y := e;"),
            ("z := tau;", "z := tau;"),
            ("a := +5;", "a := +5;"),
            ("b := -10;", "b := -10;"),
            ("c := -(5);", "c := -(5);"),
            ("result := 5 + 3;", "result := 5 + 3;"),
            ("diff := 10 - 5;", "diff := 10 - 5;"),
            ("product := 4 * 2;", "product := 4 * 2;"),
            ("quotient := 10 / 2;", "quotient := 10 / 2;"),
            ("remainder := 10 % 3;", "remainder := 10 % 3;"),
            ("power := 2 ** 3;", "power := 2 ** 3;"),
            ("complex_power := 2 ** 3 ** 2;", "complex_power := 2 ** 3 ** 2;"),
            ("shift_left := 1 << 2;", "shift_left := 1 << 2;"),
            ("shift_right := 8 >> 2;", "shift_right := 8 >> 2;"),
            ("bitwise_and := 5 & 3;", "bitwise_and := 5 & 3;"),
            ("bitwise_or := 5 | 3;", "bitwise_or := 5 | 3;"),
            ("bitwise_xor := 5 ^ 3;", "bitwise_xor := 5 ^ 3;"),
            ("sine := sin(pi / 2);", "sine := sin(pi / 2);"),
            ("logarithm := log(100);", "logarithm := log(100);"),
            ("absolute := abs(-5);", "absolute := abs(-5);"),
            ("rounded := round(3.7);", "rounded := round(3.7);"),
            ("a := 5; b := a;", "a := 5;\nb := a;"),
            ("x := 10; y := x + 5;", "x := 10;\ny := x + 5;"),
            ("result := 2 + 3 * 4;", "result := 2 + 3 * 4;"),
            ("result := (2 + 3) * 4;", "result := (2 + 3) * 4;"),
            ("complex := 2 * 3 + 4 * 5;", "complex := 2 * 3 + 4 * 5;"),
            ("mixed := 2 ** 3 * 4 + 5 / 2 - 1;", "mixed := 2 ** 3 * 4 + 5 / 2 - 1;"),
            (
                "bitwise_mix := (5 & 3) | (2 << 1);",
                "bitwise_mix := (5 & 3) | (2 << 1);",
            ),
            (
                "nested := ((2 + 3) * (4 - 1)) / 2;",
                "nested := ((2 + 3) * (4 - 1)) / 2;",
            ),
            ("func_nest := sin(cos(pi));", "func_nest := sin(cos(pi));"),
            (
                "complex_func := log(abs(sin(pi) + 5));",
                "complex_func := log(abs(sin(pi) + 5));",
            ),
            (
                "\n    a := 5;\n    b := a * 2;\n    c := a + b;\n    ",
                "a := 5;\nb := a * 2;\nc := a + b;",
            ),
            (
                "complex_expr := 2 ** (3 + 1) * sin(pi/2) / log(E**2) + 5 & 7 | 2;",
                "complex_expr := 2 ** (3 + 1) * sin(pi / 2) / log(E ** 2) + 5 & 7 | 2;",
            ),
            ("float_val := 1.234;", "float_val := 1.234;"),
            ("scientific := 1.2e3;", "scientific := 1.2e3;"),
            ("scientific_neg := 1.2e-3;", "scientific_neg := 1.2e-3;"),
            ("float_no_int := .5;", "float_no_int := .5;"),
            (
                "\n    a := 5;\n    b := 10;\n    c := a ** 2 + b ** 2;\n    d := sqrt(c);\n    result := sin(d / 10) * cos(pi/4) + log(a * b);\n    ",
                "a := 5;\nb := 10;\nc := a ** 2 + b ** 2;\nd := sqrt(c);\nresult := sin(d / 10) * cos(pi / 4) + log(a * b);",
            ),
            ("a := (true) ? 1 : 1;", "a := (True) ? 1 : 1;"),
            ("a := (true) ? 1 : pi;", "a := (True) ? 1 : pi;"),
            ("a := (true) ? 1 : x + 1;", "a := (True) ? 1 : x + 1;"),
            ("a := (true) ? pi : 1;", "a := (True) ? pi : 1;"),
            ("a := (true) ? pi : pi;", "a := (True) ? pi : pi;"),
            ("a := (true) ? pi : x + 1;", "a := (True) ? pi : x + 1;"),
            ("a := (true) ? x + 1 : 1;", "a := (True) ? x + 1 : 1;"),
            ("a := (true) ? x + 1 : pi;", "a := (True) ? x + 1 : pi;"),
            ("a := (true) ? x + 1 : x + 1;", "a := (True) ? x + 1 : x + 1;"),
            ("a := (False) ? 1 : 1;", "a := (False) ? 1 : 1;"),
            ("a := (False) ? 1 : pi;", "a := (False) ? 1 : pi;"),
            ("a := (False) ? 1 : x + 1;", "a := (False) ? 1 : x + 1;"),
            ("a := (False) ? pi : 1;", "a := (False) ? pi : 1;"),
            ("a := (False) ? pi : pi;", "a := (False) ? pi : pi;"),
            ("a := (False) ? pi : x + 1;", "a := (False) ? pi : x + 1;"),
            ("a := (False) ? x + 1 : 1;", "a := (False) ? x + 1 : 1;"),
            ("a := (False) ? x + 1 : pi;", "a := (False) ? x + 1 : pi;"),
            ("a := (False) ? x + 1 : x + 1;", "a := (False) ? x + 1 : x + 1;"),
            ("a := (x >=0) ? 1 : 1;", "a := (x >= 0) ? 1 : 1;"),
            ("a := (x >=0) ? 1 : pi;", "a := (x >= 0) ? 1 : pi;"),
            ("a := (x >=0) ? 1 : x + 1;", "a := (x >= 0) ? 1 : x + 1;"),
            ("a := (x >=0) ? pi : 1;", "a := (x >= 0) ? pi : 1;"),
            ("a := (x >=0) ? pi : pi;", "a := (x >= 0) ? pi : pi;"),
            ("a := (x >=0) ? pi : x + 1;", "a := (x >= 0) ? pi : x + 1;"),
            ("a := (x >=0) ? x + 1 : 1;", "a := (x >= 0) ? x + 1 : 1;"),
            ("a := (x >=0) ? x + 1 : pi;", "a := (x >= 0) ? x + 1 : pi;"),
            ("a := (x >=0) ? x + 1 : x + 1;", "a := (x >= 0) ? x + 1 : x + 1;"),
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expected_str,
            str(parse_operation(input_text)),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            ("a := 5",),
            ("a = 5;",),
            ("a := ;",),
            ("a := 5 +;",),
            ("a := 5 +* 3;",),
            ("a := 5 ** ;",),
            ("a := (5 + 3;",),
            ("a := 5 + 3);",),
            ("a := ((5 + 3);",),
            ("a := sin;",),
            ("a := sin(;",),
            ("a := sin);",),
            ("a := sin();",),
            ("a := foo(5);",),
            ("1a := 5;",),
            ("a-b := 5;",),
            ("a := true;",),
            ("b := false;",),
            ("a := 5 > 3;",),
            ("b := a == 5;",),
            ("a := 5 && 3;",),
            ("b := 5 || 3;",),
            ("a := !5;",),
            ("b := not 5;",),
            ("a := 5; b",),
            (":= 5;",),
            ("a = 5;",),
            ("a := @5;",),
            ("a := 5 + / 3;",),
            ("a := 5 <<< 2;",),
            ("b := 5 >>>> 2;",),
            ("a := sin(cos);",),
            ("b := sin(cos();",),
            ("a := 5; b = 10;",),
            ("a := 5; + 3;",),
            ("a := 5..3;",),
            ("b := .;",),
            ("c := 1e;",),
            ("a := 5; /* 后面应该没有任何内容 */ extra content",),
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_operation(input_text)

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
