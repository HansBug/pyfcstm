import os.path

import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import create_env, StateMachineCodeRenderer


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
