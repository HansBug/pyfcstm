import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render.c_runtime import (
    render_c_action_body,
    render_c_condition_body,
    render_c_reset_vars_body,
)


def _model_from_dsl(dsl_code):
    ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast_node)


@pytest.mark.unittest
class TestCRuntimeRendering:
    def test_static_zero_division_initializer_keeps_generated_c_compileable(self):
        model = _model_from_dsl(
            """
            def float recovered = 1.0 / 0.0;
            state Root {
                state A;
                [*] -> A;
            }
            """
        )

        body = render_c_reset_vars_body(model.defines, "RootMachine", "ROOT_MACHINE")

        assert "float division by zero" in body
        assert "return ROOT_MACHINE_FAILURE;" in body
        assert "/ (0.0)" not in body
        assert "scope->recovered = 0.0;" in body

    def test_static_zero_modulo_operation_keeps_generated_c_compileable(self):
        statements = parse_with_grammar_entry(
            """
            counter = counter % 0;
            """,
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"counter": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        assert "integer modulo by zero" in body
        assert "return ROOT_MACHINE_FAILURE;" in body
        assert "% (0)" not in body
        assert "scope->counter = 0;" in body

    def test_dynamic_zero_division_guard_keeps_runtime_denominator_check(self):
        expr = parse_with_grammar_entry(
            "counter / divisor > 0",
            entry_name="cond_expression",
        )

        body = render_c_condition_body(
            expr,
            {"counter": "int", "divisor": "int"},
            "RootMachine",
            "ROOT_MACHINE",
            "transition guard",
        )

        assert "if ((scope->divisor) == 0)" in body
        assert "((double)(scope->counter)) / (scope->divisor)" in body
