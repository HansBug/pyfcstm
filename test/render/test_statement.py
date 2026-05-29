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


@pytest.mark.unittest
class TestRenderStatementBranches:
    """
    Targeted coverage for ``pyfcstm.render.statement`` helpers that aren't
    triggered by the canonical end-to-end render tests above. Every entry
    goes through public ``render_stmt_node`` / ``render_stmt_nodes`` so
    we don't poke at private helpers gratuitously.
    """

    def test_render_stmt_node_with_preexisting_env(self):
        from pyfcstm.render import render_stmt_node
        env = create_env()
        stmts = parse_with_grammar_entry(
            'counter = counter + 1;',
            entry_name="operational_statement_set",
        )
        rendered = render_stmt_node(
            stmts[0],
            lang_style='python',
            env=env,
            state_vars=['counter'],
        )
        assert 'counter' in rendered

    def test_render_stmt_nodes_unknown_style_raises(self):
        stmts = parse_with_grammar_entry(
            'tmp = 1;', entry_name="operational_statement_set",
        )
        with pytest.raises(KeyError, match='not_a_real_lang'):
            render_stmt_nodes(stmts, lang_style='not_a_real_lang')

    def test_render_stmt_node_rejects_non_statement_objects(self):
        from pyfcstm.render import render_stmt_node

        class _NotAStatement:
            pass

        with pytest.raises(TypeError, match='Unsupported'):
            render_stmt_node(_NotAStatement(), lang_style='dsl')

    def test_render_stmt_node_dsl_style_rejects_unknown_ast_subclass(self):
        # The dsl/c/cpp/... branch raises TypeError when given a node that
        # passes _coerce_statement_node (so it's an OperationalStatement)
        # but is neither OperationAssignment nor OperationIf. We synthesize
        # a minimal subclass to exercise this branch.
        from pyfcstm.dsl import node as dsl_nodes
        from pyfcstm.render import render_stmt_node

        class _UnknownStatement(dsl_nodes.OperationalStatement):
            pass

        with pytest.raises(TypeError, match='Unsupported'):
            render_stmt_node(_UnknownStatement(), lang_style='c')

    def test_render_stmt_node_python_style_rejects_unknown_ast_subclass(self):
        from pyfcstm.dsl import node as dsl_nodes
        from pyfcstm.render import render_stmt_node

        class _UnknownStatement(dsl_nodes.OperationalStatement):
            pass

        with pytest.raises(TypeError, match='Unsupported'):
            render_stmt_node(_UnknownStatement(), lang_style='python')

    def test_render_stmt_node_unknown_base_lang_raises_key_error(self):
        # Reaching the final KeyError in _render_statement_impl requires
        # templates['base_lang'] to be a value outside the supported set.
        # Build a custom style with an exotic base_lang via ext_configs.
        from pyfcstm.render import render_stmt_node
        stmts = parse_with_grammar_entry(
            'counter = counter + 1;',
            entry_name="operational_statement_set",
        )
        with pytest.raises(KeyError, match='Unsupported statement rendering style'):
            render_stmt_node(
                stmts[0],
                lang_style='python',
                ext_configs={'base_lang': 'imaginary_lang'},
            )

    def test_render_stmt_nodes_dsl_style_elif_chain(self):
        # The dsl/c/cpp/... shared branch in _render_statement_impl has its
        # own elif handler (lines 669-682). Drive it through the c style.
        stmts = parse_with_grammar_entry(
            """
        if [counter > 0] {
            counter = 1;
        } else if [counter < 0] {
            counter = -1;
        } else {
            counter = 0;
        }
        """,
            entry_name="operational_statement_set",
        )
        rendered = render_stmt_nodes(stmts, lang_style='c', state_vars=['counter'])
        assert 'else if' in rendered

    def test_render_stmt_nodes_python_style_elif_chain(self):
        stmts = parse_with_grammar_entry(
            """
        if [counter > 0] {
            counter = 1;
        } else if [counter < 0] {
            counter = -1;
        } else {
            counter = 0;
        }
        """,
            entry_name="operational_statement_set",
        )
        rendered = render_stmt_nodes(stmts, lang_style='python', state_vars=['counter'])
        assert 'elif' in rendered

    def test_render_stmt_nodes_python_style_empty_if_body_emits_pass(self):
        stmts = parse_with_grammar_entry(
            """
        if [counter > 0] {
            counter = 1;
        }
        """,
            entry_name="operational_statement_set",
        )
        if_stmt = stmts[0]
        if_stmt.branches[0].statements = []
        rendered = render_stmt_nodes([if_stmt], lang_style='python', state_vars=['counter'])
        assert 'pass' in rendered

    def test_render_stmt_nodes_var_types_with_typed_object(self):
        class _TypeHolder:
            type = 'float'

        stmts = parse_with_grammar_entry(
            'temp_v = counter / 2.0;',
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
                "var_types={'counter': obj}) }}"
            ).render(stmts=stmts, obj=_TypeHolder())
        assert 'temp_v' in rendered

    def test_render_stmt_nodes_var_types_with_other_object(self):
        stmts = parse_with_grammar_entry(
            'counter = counter + 1;',
            entry_name="operational_statement_set",
        )
        rendered = render_stmt_nodes(
            stmts,
            lang_style='python',
            state_vars=['counter'],
            var_types={'counter': 42},
        )
        assert 'counter' in rendered

    def test_render_stmt_nodes_temp_declaration_fallback_type(self):
        # Assigning from a free unknown name yields ``inferred_type=None``
        # so the renderer falls back to ``temp_type_fallback``.
        stmts = parse_with_grammar_entry(
            'temp_v = unknown_name;',
            entry_name="operational_statement_set",
        )
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write(
                    "stmt_styles:\n"
                    "  fallback_python:\n"
                    "    base_lang: python\n"
                    "    declare_temp: '{{ temp_type }} {{ name }};'\n"
                    "    temp_type_aliases: {}\n"
                    "    temp_type_fallback: var\n"
                    "    assign: '{{ target }} = {{ expr }};'\n"
                )
            renderer = StateMachineCodeRenderer(template_dir)
            rendered = renderer.env.from_string(
                "{{ stmts | stmts_render(style='fallback_python') }}"
            ).render(stmts=stmts)
        assert 'var temp_v;' in rendered

    def test_render_stmt_nodes_temp_declaration_no_type_skipped(self):
        stmts = parse_with_grammar_entry(
            'temp_v = counter + 1;',
            entry_name="operational_statement_set",
        )
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, 'config.yaml'), 'w') as f:
                f.write(
                    "stmt_styles:\n"
                    "  no_decl_python:\n"
                    "    base_lang: python\n"
                    "    declare_temp: '{{ temp_type }} {{ name }};'\n"
                    "    temp_type_aliases: {}\n"
                    "    assign: '{{ target }} = {{ expr }};'\n"
                )
            renderer = StateMachineCodeRenderer(template_dir)
            rendered = renderer.env.from_string(
                "{{ stmts | stmts_render(style='no_decl_python', "
                "state_vars=['counter'], var_types={'counter': 'opaque'}) }}"
            ).render(stmts=stmts)
        assert 'temp_v' in rendered

    def test_render_stmt_nodes_resolve_name_passthrough(self):
        stmts = parse_with_grammar_entry(
            'foo = bar + 1;',
            entry_name="operational_statement_set",
        )
        rendered = render_stmt_nodes(stmts, lang_style='dsl')
        assert 'bar' in rendered

    @pytest.mark.parametrize(
        'src, expected_temp_type',
        [
            # Float literal -> float
            ('t = 3.14;', 'double'),
            # Constant pi -> float
            ('t = pi;', 'double'),
            # Hex int -> int
            ('t = 0xFF;', 'int'),
            # UFunc sin -> float
            ('t = sin(1);', 'double'),
            # UFunc ceil -> int
            ('t = ceil(3.14);', 'int'),
            # UFunc abs of float -> float
            ('t = abs(3.14);', 'double'),
            # Paren -> follow inner
            ('t = (3.14);', 'double'),
            # Unary -3.14 -> float
            ('t = -3.14;', 'double'),
            # BinaryOp shift -> int
            ('t = 1 << 2;', 'int'),
            # BinaryOp division -> float
            ('t = 1 / 2;', 'double'),
            # BinaryOp + int + float -> float (merge)
            ('t = 1 + 3.14;', 'double'),
            # Conditional with int arms -> int (merge)
            ('t = (1 > 0) ? 1 : 2;', 'int'),
            # Conditional with float arms -> float (merge)
            ('t = (1 > 0) ? 1.0 : 2.0;', 'double'),
        ],
    )
    def test_render_stmt_nodes_temp_type_inference(self, src, expected_temp_type):
        # Drive every _infer_expr_type branch through the typed_python
        # style which surfaces the inferred type in the temp declaration.
        stmts = parse_with_grammar_entry(src, entry_name='operational_statement_set')
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
                "{{ stmts | stmts_render(style='typed_python') }}"
            ).render(stmts=stmts)
        assert f'{expected_temp_type} t;' in rendered, rendered

    def test_render_stmt_nodes_temp_type_inference_with_typed_name(self):
        # Drive the Name -> known_types.get(name) path: assigning from a
        # typed state var pushes that type onto the new temp.
        stmts = parse_with_grammar_entry(
            't = ratio;',  # ratio has known type 'float'
            entry_name='operational_statement_set',
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
                "{{ stmts | stmts_render(style='typed_python', state_vars=['ratio'], "
                "var_types={'ratio': 'float'}) }}"
            ).render(stmts=stmts)
        assert 'double t;' in rendered
