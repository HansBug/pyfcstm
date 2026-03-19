import os.path

import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import create_env, StateMachineCodeRenderer, render_stmt_nodes


def _build_if_model():
    ast_node = parse_with_grammar_entry(
        """
    def int counter = 0;
    state Root {
        state A {
            enter {
                if [counter > 0] {
                    counter = counter + 1;
                } else {
                    counter = 0;
                }
            }
        }
        state B;
        [*] -> A;
        A -> B effect {
            if [counter > 0] {
                counter = counter + 1;
            } else {
                counter = 0;
            }
        };
    }
    """,
        entry_name="state_machine_dsl",
    )
    return parse_dsl_node_to_state_machine(ast_node)


@pytest.mark.unittest
class TestRenderOperationStatements:
    def test_operation_stmt_render_for_ast_if_statement(self):
        env = create_env()
        statement = parse_with_grammar_entry(
            """
        if [x > 0] {
            y = x + 1;
        } else {
            y = 0;
        }
        """,
            entry_name="operational_statement_set",
        )[0]

        rendered = env.from_string("{{ stmt | operation_stmt_render }}").render(stmt=statement)

        assert rendered == (
            "if [x > 0] {\n"
            "    y = x + 1;\n"
            "} else {\n"
            "    y = 0;\n"
            "}"
        )

    def test_operation_stmt_render_for_model_if_statement(self):
        env = create_env()
        model = _build_if_model()
        transition = next(
            trans
            for trans in model.root_state.transitions
            if trans.from_state == 'A'
        )
        statement = transition.effects[0]

        rendered = env.from_string("{{ stmt | operation_stmt_render }}").render(stmt=statement)

        assert rendered == (
            "if [counter > 0] {\n"
            "    counter = counter + 1;\n"
            "} else {\n"
            "    counter = 0;\n"
            "}"
        )

    def test_operation_stmts_render_is_available_in_template_renderer(self):
        model = _build_if_model()

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write('{}\n')
            with open(os.path.join(template_dir, 'effect.txt.j2'), 'w') as f:
                f.write(
                    "Enter operations:\n"
                    "{{ model.root_state.substates['A'].on_enters[0].operations | operation_stmts_render }}\n"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)

                with open(os.path.join(output_dir, 'effect.txt'), 'r') as f:
                    rendered = f.read()

        assert rendered == (
            "Enter operations:\n"
            "if [counter > 0] {\n"
            "    counter = counter + 1;\n"
            "} else {\n"
            "    counter = 0;\n"
            "}"
        )

    def test_stmts_render_python_style_distinguishes_state_vars_and_temporaries(self):
        env = create_env()
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        counter = tmp + 2;
        """,
            entry_name="operational_statement_set",
        )

        rendered = env.from_string(
            "{{ stmts | stmts_render(style='python', state_vars=['counter']) }}"
        ).render(stmts=statements)

        assert rendered == (
            'tmp = scope["counter"] + 1\n'
            'scope["counter"] = tmp + 2'
        )

    def test_stmts_render_python_style_supports_nested_if_blocks(self):
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        if [tmp > 0] {
            counter = tmp + 1;
        } else {
            fallback = 0;
            counter = fallback;
        }
        """,
            entry_name="operational_statement_set",
        )

        rendered = render_stmt_nodes(
            statements,
            lang_style='python',
            state_vars=['counter'],
        )

        assert rendered == (
            'tmp = scope["counter"] + 1\n'
            'if tmp > 0:\n'
            '    scope["counter"] = tmp + 1\n'
            'else:\n'
            '    fallback = 0\n'
            '    scope["counter"] = fallback'
        )

    @pytest.mark.parametrize(
        ['lang_style', 'expected'],
        [
            (
                'c',
                "int tmp;\n"
                "tmp = scope->counter + 1;\n"
                "if (tmp > 0) {\n"
                "    scope->counter = tmp + 1;\n"
                "} else {\n"
                "    int fallback;\n"
                "    fallback = 0;\n"
                "    scope->counter = fallback;\n"
                "}",
            ),
            (
                'cpp',
                "int tmp;\n"
                "tmp = scope->counter + 1;\n"
                "if (tmp > 0) {\n"
                "    scope->counter = tmp + 1;\n"
                "} else {\n"
                "    int fallback;\n"
                "    fallback = 0;\n"
                "    scope->counter = fallback;\n"
                "}",
            ),
            (
                'python',
                'tmp = scope["counter"] + 1\n'
                'if tmp > 0:\n'
                '    scope["counter"] = tmp + 1\n'
                'else:\n'
                '    fallback = 0\n'
                '    scope["counter"] = fallback',
            ),
            (
                'java',
                "int tmp;\n"
                "tmp = scope.counter + 1;\n"
                "if (tmp > 0) {\n"
                "    scope.counter = tmp + 1;\n"
                "} else {\n"
                "    int fallback;\n"
                "    fallback = 0;\n"
                "    scope.counter = fallback;\n"
                "}",
            ),
            (
                'js',
                "let tmp;\n"
                "tmp = scope.counter + 1;\n"
                "if (tmp > 0) {\n"
                "    scope.counter = tmp + 1;\n"
                "} else {\n"
                "    let fallback;\n"
                "    fallback = 0;\n"
                "    scope.counter = fallback;\n"
                "}",
            ),
            (
                'ts',
                "let tmp: number;\n"
                "tmp = scope.counter + 1;\n"
                "if (tmp > 0) {\n"
                "    scope.counter = tmp + 1;\n"
                "} else {\n"
                "    let fallback: number;\n"
                "    fallback = 0;\n"
                "    scope.counter = fallback;\n"
                "}",
            ),
            (
                'rust',
                "let mut tmp: i64;\n"
                "tmp = scope.counter + 1;\n"
                "if tmp > 0 {\n"
                "    scope.counter = tmp + 1;\n"
                "} else {\n"
                "    let mut fallback: i64;\n"
                "    fallback = 0;\n"
                "    scope.counter = fallback;\n"
                "}",
            ),
            (
                'go',
                "var tmp int\n"
                "tmp = scope.counter + 1\n"
                "if tmp > 0 {\n"
                "    scope.counter = tmp + 1\n"
                "} else {\n"
                "    var fallback int\n"
                "    fallback = 0\n"
                "    scope.counter = fallback\n"
                "}",
            ),
        ],
    )
    def test_stmts_render_builtin_styles_are_directly_usable_by_default(self, lang_style, expected):
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        if [tmp > 0] {
            counter = tmp + 1;
        } else {
            fallback = 0;
            counter = fallback;
        }
        """,
            entry_name="operational_statement_set",
        )

        rendered = render_stmt_nodes(
            statements,
            lang_style=lang_style,
            state_vars=['counter'],
            var_types={'counter': 'int'},
        )

        assert rendered == expected

    @pytest.mark.parametrize(
        ['lang_style', 'expected'],
        [
            ('c++', "int tmp;\n" "tmp = scope->counter + 1;"),
            ('javascript', "let tmp;\n" "tmp = scope.counter + 1;"),
            ('typescript', "let tmp: number;\n" "tmp = scope.counter + 1;"),
            ('golang', "var tmp int\n" "tmp = scope.counter + 1"),
            ('python3', 'tmp = scope["counter"] + 1'),
        ],
    )
    def test_stmts_render_supports_common_language_aliases(self, lang_style, expected):
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        """,
            entry_name="operational_statement_set",
        )

        rendered = render_stmt_nodes(
            statements,
            lang_style=lang_style,
            state_vars=['counter'],
            var_types={'counter': 'int'},
        )

        assert rendered == expected

    def test_stmts_render_supports_temp_declaration_extension_interface(self):
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        counter = tmp + 2;
        """,
            entry_name="operational_statement_set",
        )

        rendered = render_stmt_nodes(
            statements,
            lang_style='python',
            state_vars=['counter'],
            var_types={'counter': 'int'},
            ext_configs={
                'declare_temp': '{{ temp_type }} {{ name }};',
                'temp_type_aliases': {'int': 'int', 'float': 'double'},
                'assign': '{{ target }} = {{ expr }};',
            },
        )

        assert rendered == (
            "int tmp;\n"
            'tmp = scope["counter"] + 1;\n'
            'scope["counter"] = tmp + 2;'
        )

    def test_stmts_render_is_available_in_template_renderer_with_custom_style(self):
        model = _build_if_model()

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write(
                    "stmt_styles:\n"
                    "  python_scope:\n"
                    "    base_lang: python\n"
                )
            with open(os.path.join(template_dir, 'effect.txt.j2'), 'w') as f:
                f.write(
                    "Enter operations:\n"
                    "{{ model.root_state.substates['A'].on_enters[0].operations "
                    "| stmts_render(style='python_scope', state_vars=model.defines.keys()) }}\n"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)

                with open(os.path.join(output_dir, 'effect.txt'), 'r') as f:
                    rendered = f.read()

        assert rendered == (
            "Enter operations:\n"
            'if scope["counter"] > 0:\n'
            '    scope["counter"] = scope["counter"] + 1\n'
            'else:\n'
            '    scope["counter"] = 0'
        )

    def test_stmts_render_uses_renderer_default_state_vars_when_omitted(self):
        model = _build_if_model()

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write('{}\n')
            with open(os.path.join(template_dir, 'effect.txt.j2'), 'w') as f:
                f.write(
                    "Enter operations:\n"
                    "{{ model.root_state.substates['A'].on_enters[0].operations "
                    "| stmts_render(style='python3') }}\n"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)

                with open(os.path.join(output_dir, 'effect.txt'), 'r') as f:
                    rendered = f.read()

        assert rendered == (
            "Enter operations:\n"
            'if scope["counter"] > 0:\n'
            '    scope["counter"] = scope["counter"] + 1\n'
            'else:\n'
            '    scope["counter"] = 0'
        )

    def test_stmts_render_supports_declared_temp_types_in_template_renderer(self):
        statements = parse_with_grammar_entry(
            """
        tmp = counter + 1;
        counter = tmp + 2;
        """,
            entry_name="operational_statement_set",
        )

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write(
                    "stmt_styles:\n"
                    "  typed_python:\n"
                    "    base_lang: python\n"
                    "    declare_temp: '{{ temp_type }} {{ name }};'\n"
                    "    temp_type_aliases:\n"
                    "      int: int\n"
                    "      float: double\n"
                    "    assign: '{{ target }} = {{ expr }};'\n"
                )

            renderer = StateMachineCodeRenderer(template_dir)
            rendered = renderer.env.from_string(
                "{{ stmts | stmts_render(style='typed_python', state_vars=['counter'], "
                "var_types={'counter': 'int'}) }}"
            ).render(stmts=statements)

        assert rendered == (
            "int tmp;\n"
            'tmp = scope["counter"] + 1;\n'
            'scope["counter"] = tmp + 2;'
        )
