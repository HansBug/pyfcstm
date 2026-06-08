import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import parse_expr_node_to_expr
from pyfcstm.render import create_env, render_expr_node, create_expr_render_template


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

    @pytest.mark.parametrize(
        'lang_style, expr_text, expected',
        [
            ('dsl', 'true => false', 'True => False'),
            ('c', 'true => false', '((!(0x1)) || (0x0))'),
            ('cpp', 'true => false', '((!(true)) || (false))'),
            ('java', 'true => false', '((!(true)) || (false))'),
            ('js', 'true => false', '((!(true)) || (false))'),
            ('ts', 'true => false', '((!(true)) || (false))'),
            ('rust', 'true => false', '((!(true)) || (false))'),
            ('go', 'true => false', '((!(true)) || (false))'),
            ('python', 'true => false', '((not (True)) or (False))'),
            ('dsl', 'true xor false', 'True xor False'),
            ('c', 'true xor false', '((0x1) != (0x0))'),
            ('cpp', 'true xor false', '((true) != (false))'),
            ('java', 'true xor false', '((true) != (false))'),
            ('js', 'true xor false', '((true) != (false))'),
            ('ts', 'true xor false', '((true) != (false))'),
            ('rust', 'true xor false', '((true) != (false))'),
            ('go', 'true xor false', '((true) != (false))'),
            ('python', 'true xor false', '((True) != (False))'),
            ('dsl', 'true iff false', 'True iff False'),
            ('c', 'true iff false', '((0x1) == (0x0))'),
            ('cpp', 'true iff false', '((true) == (false))'),
            ('java', 'true iff false', '((true) == (false))'),
            ('js', 'true iff false', '((true) == (false))'),
            ('ts', 'true iff false', '((true) == (false))'),
            ('rust', 'true iff false', '((true) == (false))'),
            ('go', 'true iff false', '((true) == (false))'),
            ('python', 'true iff false', '((True) == (False))'),
        ],
    )
    def test_render_expr_node_for_condition_logical_operators(
        self, lang_style, expr_text, expected, new_env
    ):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='generic_expression')
        result = render_expr_node(ast_node, lang_style=lang_style, env=new_env)
        assert result == expected

    @pytest.mark.parametrize(
        'lang_style',
        ['c', 'cpp', 'java', 'js', 'ts', 'rust', 'go', 'python'],
    )
    def test_non_dsl_styles_do_not_leak_condition_logical_operators(
        self, lang_style, new_env
    ):
        ast_node = parse_with_grammar_entry(
            '(true => false) xor (false iff true)',
            entry_name='generic_expression',
        )
        result = render_expr_node(ast_node, lang_style=lang_style, env=new_env)

        assert '=>' not in result
        assert ' xor ' not in result
        assert ' iff ' not in result

    @pytest.mark.parametrize('lang_style', ['dsl', 'c', 'cpp', 'java', 'js', 'ts', 'rust', 'go', 'python'])
    def test_condition_logical_operator_templates_are_operator_specific(self, lang_style):
        templates = create_expr_render_template(lang_style)

        assert 'BinaryOp(=>)' in templates
        assert 'BinaryOp(xor)' in templates
        assert 'BinaryOp(iff)' in templates
        assert 'BinaryOp(^)' not in templates

    @pytest.mark.parametrize(
        'expr_text, expected',
        [
            ('true iff false == false', '(((True) == (False))) == False'),
            ('true iff false != true', '(((True) == (False))) != True'),
            ('false => true && false', '((not (False)) or (True and False))'),
            ('(false => true) && false', '(((not (False)) or (True))) and False'),
            ('!true == false', '(not True) == False'),
            ('((true) ? false : true) == false', '(False if True else True) == False'),
        ],
    )
    def test_python_condition_logical_rendering_keeps_parent_expression_semantics(
        self, expr_text, expected, new_env
    ):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='generic_expression')
        result = render_expr_node(ast_node, lang_style='python', env=new_env)

        assert result == expected
        assert eval(result) == eval(expected)

    @pytest.mark.parametrize(
        'expr_text',
        [
            'a > 0 iff b > 0 == c > 0',
            'a > 0 == b > 0 iff c > 0',
            'a > 0 xor b > 0 == c > 0',
            'a > 0 != b > 0 xor c > 0',
        ],
    )
    def test_python_condition_logical_rendering_matches_model_for_comparison_chains(
        self, expr_text, new_env
    ):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='generic_expression')
        result = render_expr_node(ast_node, lang_style='python', env=new_env)
        model_expr = parse_expr_node_to_expr(ast_node)

        for a in (-1, 1):
            for b in (-1, 1):
                for c in (-1, 1):
                    scope = {'a': a, 'b': b, 'c': c}
                    assert eval(result, {}, scope) == model_expr(**scope)

    @pytest.mark.parametrize('lang_style', ['dsl', 'c', 'cpp', 'java', 'js', 'ts', 'rust', 'go', 'python'])
    def test_numeric_caret_renderer_remains_bitwise_xor(self, lang_style, new_env):
        ast_node = parse_with_grammar_entry('x ^ y', entry_name='generic_expression')
        result = render_expr_node(ast_node, lang_style=lang_style, env=new_env)

        assert result == 'x ^ y'

    @pytest.mark.parametrize('expr_text', ['true => false', 'true xor false', 'true iff false'])
    def test_infer_expr_type_for_condition_logical_operators(self, expr_text):
        from pyfcstm.render.expr import _infer_expr_type

        ast_node = parse_with_grammar_entry(expr_text, entry_name='generic_expression')

        assert _infer_expr_type(ast_node) == 'int'


@pytest.mark.unittest
class TestGoStyleTypeInference:
    """
    Drive the Go expression style so that ``_infer_expr_type`` and the
    ``go_expr_type`` / ``go_abs_expr`` helper paths are exercised through
    real templates. Each case targets a distinct branch.
    """

    @pytest.mark.parametrize(
        'expr_text, expected_substr',
        [
            # abs(int) -> int(math.Abs(float64(...)))
            ('abs(-5)', 'int(math.Abs'),
            # abs(float-via-Float) -> float math.Abs without int cast
            ('abs(3.14)', 'math.Abs'),
            # abs(hex-int literal) routes through HexInt -> 'int' branch
            ('abs(0xFF)', 'int(math.Abs'),
            # Conditional with float arms -> go_expr_type returns float64
            ('(1 > 0) ? 1.5 : 2.5', 'float64'),
            # Conditional with int arms -> go_expr_type returns int
            ('(1 > 0) ? 1 : -1', 'int'),
            # Boolean condition arms (int + int via boolean coercion)
            ('(1 > 0) ? True : False', 'int'),
            # tau -> Float branch -> float type inferred
            ('abs(tau)', 'math.Abs'),
            # Constant 'pi' is float; ceil over pi -> int branch
            ('ceil(pi)', 'int(math.Ceil'),
            # Unary '!' op -> 'int' branch (wrap in ternary so it appears
            # in numeric context, since '!' is a logical operator and the
            # grammar rejects ``abs(!true)`` directly).
            ('((!true) ? 0 : 1)', 'int'),
            # Unary other -> recurses
            ('abs(-3.14)', 'math.Abs'),
            # Binary with shift '<<' -> int branch
            ('abs(1 << 2)', 'int(math.Abs'),
            # Binary with comparison '==' -> int branch
            ('abs((1 == 1) ? 0 : 0)', 'int(math.Abs'),
            # Binary with division -> float branch
            ('abs(1 / 2)', 'math.Abs'),
            # Paren passthrough
            ('abs((1 + 2))', 'int(math.Abs'),
            # round/floor/trunc/int over float -> int branch
            ('round(3.14)', 'int(math.Round'),
            ('floor(3.14)', 'int(math.Floor'),
            ('trunc(3.14)', 'int(math.Trunc'),
            # abs over Name -> _infer_expr_type returns None -> go_abs_expr
            # falls through to the float branch
            ('abs(some_var)', 'math.Abs'),
            # sin over Name -> non-int float UFunc branch
            ('sin(x_var)', 'math.Sin'),
            # Binary '+' over two Name nodes wrapped in a ternary -> both
            # inferred None -> _merge_numeric_types returns None ->
            # default branch
            ('((a_var + b_var) > 0) ? 1 : 0', 'int'),
            # Constant 'pi' alone (Constant float branch)
            ('(pi > 0) ? 1.0 : 2.0', 'float64'),
            # abs(sin(x)) -> abs branch with UFunc child returning 'float'
            ('abs(sin(x_var))', 'math.Abs'),
            # abs of binary op with two Names -> _merge_numeric_types(None,None)
            ('abs(a_var + b_var)', 'math.Abs'),
            # ceil(int) -> floor/ceil/round/int/trunc -> int branch
            ('ceil(1)', 'int(math.Ceil'),
            # sin(int) -> UFunc default 'float' branch
            ('sin(1)', 'math.Sin'),
            # abs() over a shift binary op exercises BinaryOp shift branch
            ('abs(1 << 3)', 'int(math.Abs'),
            # abs(ceil(...)) -> ceil child reports 'int' via UFunc int-set
            ('abs(ceil(3.14))', 'int(math.Abs'),
            # abs(abs(x)) -> outer abs reads the inner abs UFunc child via
            # _infer_expr_type, hitting the UFunc('abs') recursive branch.
            ('abs(abs(x_var))', 'math.Abs'),
        ],
    )
    def test_go_style_expression_inference(self, expr_text, expected_substr, new_env):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='generic_expression')
        result = render_expr_node(ast_node, lang_style='go', env=new_env)
        assert expected_substr in result, f'expected {expected_substr!r} in {result!r}'

    def test_create_base_env_with_preexisting_env(self):
        """``_create_base_env`` accepts an existing env and seeds it
        without replacing the user's existing globals."""
        import jinja2
        from pyfcstm.render.expr import _create_base_env

        env = jinja2.Environment()
        env.globals['custom_marker'] = 'pre-existing'
        out = _create_base_env(env)
        assert out is env
        assert env.globals['custom_marker'] == 'pre-existing'
        assert callable(env.globals['expr_infer_type'])
        assert callable(env.globals['go_expr_type'])
        assert callable(env.globals['go_abs_expr'])

    def test_create_base_env_without_env_creates_new(self):
        from pyfcstm.render.expr import _create_base_env

        env = _create_base_env()
        assert callable(env.globals['expr_infer_type'])
        assert callable(env.globals['go_expr_type'])
        assert callable(env.globals['go_abs_expr'])
