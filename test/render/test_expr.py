import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.render import create_env, render_expr_node


@pytest.fixture
def new_env():
    return create_env()


@pytest.mark.unittest
class TestRenderExprNode:
    @pytest.mark.parametrize(
        "expr_text, lang_type, ext_configs, expected_text_result",
        [
            ("1 + 2", "dsl", None, "1 + 2"),
            ("3.14", "c", None, "3.14"),
            ("True", "python", None, "True"),
            ("1 << 2", "dsl", None, "1 << 2"),
            ("sin(pi)", "c", None, "sin(3.141592653589793)"),
            ("2 ** 3", "python", None, "2 ** 3"),
            ("(1 + 2) * 3", "dsl", None, "(1 + 2) * 3"),
            ("0xFF", "c", None, "0xff"),
            ("!true", "c", None, "!0x1"),
            ("not False", "python", None, "not False"),
            ("True", "java", None, "true"),
            ("True", "js", None, "true"),
            ("True", "ts", None, "true"),
            ("True", "rust", None, "true"),
            ("True", "go", None, "true"),
            ("(x > 0) ? 1 : -1", "c", None, "(x > 0) ? 1 : -1"),
            ("(x > 0) ? 1 : -1", "java", None, "x > 0 ? 1 : -1"),
            ("(x > 0) ? 1 : -1", "python", None, "1 if x > 0 else -1"),
            ("(x > 0) ? 1 : -1", "js", None, "(x > 0) ? 1 : -1"),
            ("(x > 0) ? 1 : -1", "ts", None, "(x > 0) ? 1 : -1"),
            ("(x > 0) ? 1 : -1", "rust", None, "(if x > 0 { 1 } else { -1 })"),
            (
                "(x > 0) ? 1 : -1",
                "go",
                None,
                "func() int { if x > 0 { return 1 }; return -1 }()",
            ),
            ("2.5e-3", "dsl", None, "0.0025"),
            ("x & (y | z)", "c", None, "x & (y | z)"),
            ("abs(-5)", "python", None, "abs(-5)"),
            ("sin(x)", "java", None, "Math.sin(x)"),
            ("sin(x)", "js", None, "Math.sin(x)"),
            ("sin(x)", "ts", None, "Math.sin(x)"),
            ("sin(x)", "go", None, "math.Sin(float64(x))"),
            ("3.14 * r ** 2", "dsl", None, "3.14 * r ** 2"),
            ("2 ** 3", "java", None, "Math.pow(2, 3)"),
            ("2 ** 3", "js", None, "Math.pow(2, 3)"),
            ("2 ** 3", "ts", None, "Math.pow(2, 3)"),
            ("2 ** 3", "rust", None, "(2 as f64).powf(3 as f64)"),
            ("2 ** 3", "go", None, "math.Pow(float64(2), float64(3))"),
            ("log2(8)", "c", None, "log2(8)"),
            ("log2(8)", "rust", None, "(8 as f64).log2()"),
            ("abs(-5)", "go", None, "int(math.Abs(float64(-5)))"),
            ("round(3.14159)", "rust", None, "(3.14159 as f64).round() as i64"),
            ("floor(3.14159)", "go", None, "int(math.Floor(float64(3.14159)))"),
            ("x >= 0 && y < 10", "c", None, "x >= 0 && y < 10"),
            ("x >= 0 and y < 10", "python", None, "x >= 0 and y < 10"),
            ("(x|y)>0", "dsl", None, "(x | y) > 0"),
            ("pi", "js", None, "3.141592653589793"),
            ("tau", "java", None, "6.283185307179586"),
            ("tau", "go", None, "6.283185307179586"),
            ("2 + 3 * 4", "dsl", {"Integer": "{{ node.value | int }}"}, "2 + 3 * 4"),
            ("pi", "c", {"Constant": "M_{{ node | str | upper }}"}, "M_PI"),
            ("E", "python", {"Constant": "math.e"}, "math.e"),
            (
                "True",
                "c",
                {"Boolean": "{{ 'true' if node.value else 'false' }}"},
                "true",
            ),
            ("3.14159", "dsl", {"Float": "{{ '%.2f' | format(node.value) }}"}, "3.14"),
            (
                "2 ** 3",
                "c",
                {
                    "BinaryOp(**)": "pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})"
                },
                "pow(2, 3)",
            ),
            (
                "sin(x)",
                "python",
                {"UFunc": "numpy.{{ node.func }}({{ node.expr | expr_render }})"},
                "numpy.sin(x)",
            ),
            (
                "(x < 0) ? -x : x",
                "c",
                {"ConditionalOp": "std::abs({{ node.cond.expr1 | expr_render }})"},
                "std::abs(x)",
            ),
            (
                "(x < 0) ? -x : x",
                "python",
                {"ConditionalOp": "abs({{ node.cond.expr1 | expr_render }})"},
                "abs(x)",
            ),
            ("0xFF", "dsl", {"HexInt": "{{ node.value }}"}, "255"),
            (
                "(1 + 2) * 3",
                "c",
                {"Paren": "[{{ node.expr | expr_render }}]"},
                "[1 + 2] * 3",
            ),
            (
                "-x",
                "dsl",
                {"UnaryOp": "{{ node.op }}({{ node.expr | expr_render }})"},
                "-(x)",
            ),
            (
                "x + y",
                "python",
                {
                    "BinaryOp": "({{ node.expr1 | expr_render }} {{ node.op }} {{ node.expr2 | expr_render }})"
                },
                "(x + y)",
            ),
            (
                "(x > 0) && (y < 0)",
                "c",
                {
                    "BinaryOp(&&)": "{{ node.expr1 | expr_render }} AND {{ node.expr2 | expr_render }}"
                },
                "(x > 0) AND (y < 0)",
            ),
            (
                "(x > 0) || (y < 0)",
                "python",
                {
                    "BinaryOp(||)": "{{ node.expr1 | expr_render }} OR {{ node.expr2 | expr_render }}"
                },
                "(x > 0) OR (y < 0)",
            ),
            (
                "!x > 0",
                "c",
                {"UnaryOp(!)": "not {{ node.expr | expr_render }}"},
                "not x > 0",
            ),
            (
                "2 * pi",
                "dsl",
                {"Constant": "{{ node.value | float }}"},
                "2 * 3.141592653589793",
            ),
            (
                "log(x)",
                "python",
                {"UFunc": "math.log({{ node.expr | expr_render }}, 2)"},
                "math.log(x, 2)",
            ),
            (
                "x ** 0.5",
                "c",
                {"BinaryOp(**)": "sqrt({{ node.expr1 | expr_render }})"},
                "sqrt(x)",
            ),
            (
                "x % 2 == 0",
                "dsl",
                {
                    "BinaryOp(%)": "{{ node.expr1 | expr_render }} mod {{ node.expr2 | expr_render }}"
                },
                "x mod 2 == 0",
            ),
            (
                "x << 2",
                "c",
                {"BinaryOp(<<)": "({{ node.expr1 | expr_render }} * 4)"},
                "(x * 4)",
            ),
            (
                "x >> 1",
                "python",
                {"BinaryOp(>>)": "({{ node.expr1 | expr_render }} // 2)"},
                "(x // 2)",
            ),
            (
                "x & 0xFF",
                "dsl",
                {
                    "BinaryOp(&)": "{{ node.expr1 | expr_render }} AND {{ node.expr2 | expr_render }}"
                },
                "x AND 0xff",
            ),
            (
                "x ^ y",
                "c",
                {
                    "BinaryOp(^)": "{{ node.expr1 | expr_render }} XOR {{ node.expr2 | expr_render }}"
                },
                "x XOR y",
            ),
            (
                "x | 0x0F",
                "python",
                {
                    "BinaryOp(|)": "{{ node.expr1 | expr_render }} OR {{ node.expr2 | expr_render }}"
                },
                "x OR 0xf",
            ),
            (
                "round(3.14159)",
                "dsl",
                {"UFunc": "ROUND({{ node.expr | expr_render }}, 2)"},
                "ROUND(3.14159, 2)",
            ),
            (
                "ceil(x)",
                "c",
                {"UFunc": "(int)({{ node.expr | expr_render }} + 0.5)"},
                "(int)(x + 0.5)",
            ),
            (
                "floor(x)",
                "python",
                {"UFunc": "int({{ node.expr | expr_render }})"},
                "int(x)",
            ),
            (
                "abs(x - y)",
                "dsl",
                {"UFunc": "|{{ node.expr | expr_render }}|"},
                "|x - y|",
            ),
            (
                "x != y",
                "dsl",
                {
                    "BinaryOp(!=)": "{{ node.expr1 | expr_render }} <> {{ node.expr2 | expr_render }}"
                },
                "x <> y",
            ),
            (
                "x == y",
                "c",
                {
                    "BinaryOp(==)": "{{ node.expr1 | expr_render }} equals {{ node.expr2 | expr_render }}"
                },
                "x equals y",
            ),
            (
                "x <= y",
                "python",
                {
                    "BinaryOp(<=)": "{{ node.expr1 | expr_render }} not greater than {{ node.expr2 | expr_render }}"
                },
                "x not greater than y",
            ),
            (
                "x >= y",
                "dsl",
                {
                    "BinaryOp(>=)": "{{ node.expr1 | expr_render }} not less than {{ node.expr2 | expr_render }}"
                },
                "x not less than y",
            ),
            (
                "sin( x + 2)",
                "dsl",
                {"UFunc(sin)": "ss({{ node.expr | expr_render }})"},
                "ss(x + 2)",
            ),
            (
                "(x > 0) ? x + 2 : y",
                "dsl",
                {
                    "BinaryOp(+)": "Add({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})"
                },
                "(x > 0) ? Add(x, 2) : y",
            ),
        ],
    )
    def test_render_expr_node_for_expr(
        self, expr_text, lang_type, ext_configs, expected_text_result, new_env
    ):
        ast_node = parse_with_grammar_entry(expr_text, entry_name="generic_expression")
        result = render_expr_node(
            ast_node, lang_style=lang_type, ext_configs=ext_configs, env=new_env
        )
        assert result == expected_text_result

    @pytest.mark.parametrize(
        "expr_text, lang_type, expected_text_result",
        [
            ("2 ** 3", "c++", "std::pow(2, 3)"),
            ("sin(x)", "javascript", "Math.sin(x)"),
            ("sin(x)", "typescript", "Math.sin(x)"),
            ("sin(x)", "golang", "math.Sin(float64(x))"),
            ("True", "python3", "True"),
        ],
    )
    def test_render_expr_node_supports_common_language_aliases(
        self, expr_text, lang_type, expected_text_result, new_env
    ):
        ast_node = parse_with_grammar_entry(expr_text, entry_name="generic_expression")
        result = render_expr_node(ast_node, lang_style=lang_type, env=new_env)
        assert result == expected_text_result

    @pytest.mark.parametrize(
        "input_value, lang_type, ext_configs, expected_result",
        [
            (42, "dsl", None, "42"),
            (3.14, "c", None, "3.14"),
            (True, "python", None, "True"),
            (False, "c", None, "0x0"),
            (42, "python", {"Integer": "{{ node.value + 1 }}"}, "43"),
            (3.14, "dsl", {"Float": "{{ '%.1f' | format(node.value) }}"}, "3.1"),
            (True, "c", {"Boolean": "{{ 'YES' if node.value else 'NO' }}"}, "YES"),
            ("test", "python", None, "'test'"),
            ([1, 2, 3], "dsl", None, "[1, 2, 3]"),
            ({"a": 1}, "c", None, "{'a': 1}"),
        ],
    )
    def test_render_expr_node_for_literals_and_objects(
        self, input_value, lang_type, ext_configs, expected_result, new_env
    ):
        result = render_expr_node(
            input_value, lang_style=lang_type, ext_configs=ext_configs, env=new_env
        )
        assert result == expected_result
