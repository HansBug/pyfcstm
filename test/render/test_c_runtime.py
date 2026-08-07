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


def _host_zero_division_text(compute):
    """Return this interpreter's own ZeroDivisionError text for ``compute``.

    Generated diagnostics must match the simulator's, and the simulator embeds
    the interpreter's wording, which is not stable across the supported range:
    integer modulo by zero reads ``'integer division or modulo by zero'`` up to
    CPython 3.10, ``'integer modulo by zero'`` in 3.11, and ``'division by
    zero'`` in the newest interpreters. Asking the host here rather than
    freezing one phrasing keeps the assertion meaningful on every supported
    version, and still fails if the emitter goes back to a frozen literal.
    """
    try:
        compute()
    except ZeroDivisionError as err:
        # The only expected failure: every caller passes a division or modulo
        # whose operands make it fail with ZeroDivisionError.
        return str(err)
    # Anything else propagates and surfaces the bug.
    raise AssertionError("expected the probe operation to fail on this interpreter")


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

        assert _host_zero_division_text(lambda: 1.0 / 0.0) in body
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

        assert _host_zero_division_text(lambda: 1 % 0) in body
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
