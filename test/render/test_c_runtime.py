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

    def test_static_negative_shift_count_keeps_generated_c_compileable(self):
        statements = parse_with_grammar_entry(
            """
            counter = 1 << -1;
            """,
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"counter": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        assert "negative shift count" in body
        assert "return ROOT_MACHINE_FAILURE;" in body
        # A negative literal shift count is undefined behaviour in C, and the
        # -Werror command in the generated README rejects it outright, so the
        # expression itself must not reach the generated source.
        assert "<< ((-1))" not in body
        assert "scope->counter = 0;" in body

    def test_int64_min_shift_count_keeps_generated_c_compileable(self):
        statements = parse_with_grammar_entry(
            "counter = 1 << -(+9223372036854775808);",
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"counter": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        assert "negative shift count" in body
        assert "return ROOT_MACHINE_FAILURE;" in body
        assert "9223372036854775808" not in body
        assert "scope->counter = 0;" in body

    def test_sign_folded_negative_shift_counts_are_masked_too(self):
        statements = parse_with_grammar_entry(
            """
            a = 1 << +(-1);
            b = 1 << -(+1);
            c = 1 >> -2;
            """,
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"a": "int", "b": "int", "c": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        assert body.count("negative shift count") == 3
        assert "scope->a = 0;" in body
        assert "scope->b = 0;" in body
        assert "scope->c = 0;" in body
        assert "<<" not in body.split("negative shift count")[-1]

    def test_computed_negative_shift_counts_are_masked_in_action_guard_and_initializer(self):
        action_statements = parse_with_grammar_entry(
            "counter = 1 << (0 | -1); other = 1 >> (0 ^ 0 - 1);",
            entry_name="operational_statement_set",
        )
        action_body = render_c_action_body(
            action_statements,
            {"counter": "int", "other": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )
        assert action_body.count("negative shift count") == 2
        assert "<<" not in action_body
        assert ">>" not in action_body

        guard = parse_with_grammar_entry(
            "counter == (1 << (0 | -1)) and other == (1 >> (0 ^ 0 - 1))",
            entry_name="cond_expression",
        )
        guard_body = render_c_condition_body(
            guard,
            {"counter": "int", "other": "int"},
            "RootMachine",
            "ROOT_MACHINE",
            "transition guard",
        )
        assert guard_body.count("negative shift count") == 2
        assert "<<" not in guard_body
        assert ">>" not in guard_body

        model = _model_from_dsl(
            """
            def int initial = 1 << (0 | -1);
            def int other = 1 >> (0 ^ 0 - 1);
            state Root {
                state A;
                [*] -> A;
            }
            """
        )
        initializer_body = render_c_reset_vars_body(
            model.defines,
            "RootMachine",
            "ROOT_MACHINE",
        )
        assert initializer_body.count("negative shift count") == 2
        assert "<<" not in initializer_body
        assert ">>" not in initializer_body

    def test_dynamic_negative_shift_guard_keeps_runtime_count_check(self):
        statements = parse_with_grammar_entry(
            """
            counter = 1 << offset;
            """,
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"counter": "int", "offset": "int"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        # A count that is only known at runtime keeps the real shift and is
        # protected by the guard rather than replaced by the placeholder.
        assert "if ((scope->offset) < 0)" in body
        assert "negative shift count" in body
        assert "((1) << (scope->offset))" in body

    def test_round_is_emitted_as_nearbyint_for_ties_to_even_and_positive_zero(self):
        statements = parse_with_grammar_entry(
            """
            counter = round(value);
            """,
            entry_name="operational_statement_set",
        )

        body = render_c_action_body(
            statements,
            {"counter": "int", "value": "float"},
            "RootMachine",
            "ROOT_MACHINE",
        )

        # C's round() breaks ties away from zero; the simulator breaks them
        # toward the even neighbour, which nearbyint() does under the default
        # FE_TONEAREST rounding direction.
        assert "(nearbyint(scope->value) + 0.0)" in body
        assert "round(scope->value)" not in body

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


@pytest.mark.unittest
class TestCRuntimeVariableRoles:
    @pytest.fixture
    def role_model(self):
        return _model_from_dsl("""
            input int signal;
            param int gain = 2;
            control int count = 0;
            output int result = 0;
            state Root { state Ready; [*] -> Ready; }
        """)

    def test_action_reads_input_and_parameter_through_getters(self, role_model):
        statements = parse_with_grammar_entry(
            "count = count + 1; result = signal * gain + count;",
            entry_name="operational_statement_set",
        )
        body = render_c_action_body(
            statements, role_model.defines, "RootMachine", "ROOT_MACHINE"
        )
        assert "scope->count = ((scope->count) + (1));" in body
        assert "scope->result = " in body
        assert "RootMachine_get_input_signal(machine)" in body
        assert "RootMachine_get_param_gain(machine)" in body
        assert "scope->signal" not in body
        assert "scope->gain" not in body

    def test_guard_and_division_checks_use_frozen_input(self, role_model):
        expr = parse_with_grammar_entry("gain / signal > count", entry_name="cond_expression")
        body = render_c_condition_body(
            expr, role_model.defines, "RootMachine", "ROOT_MACHINE", "guard"
        )
        assert "RootMachine_get_input_signal(machine)" in body
        assert "RootMachine_get_param_gain(machine)" in body
        assert "scope->count" in body
        assert "scope->signal" not in body
        assert "scope->gain" not in body

    def test_persistent_reset_excludes_inputs_and_parameters(self, role_model):
        body = render_c_reset_vars_body(
            role_model.defines, "RootMachine", "ROOT_MACHINE"
        )
        assert "scope->count = 0;" in body
        assert "scope->result = 0;" in body
        assert "signal" not in body
        assert "gain" not in body


@pytest.mark.unittest
@pytest.mark.parametrize("parameters", [False, True], ids=["persistent", "parameters"])
def test_initializer_options_skip_defaults_in_the_selected_storage(parameters):
    model = _model_from_dsl("""
        input int signal;
        param int gain = 2.0;
        control int count = 1 << 2.0;
        output float result = 0.5;
        state Root;
    """)
    body = render_c_reset_vars_body(
        model.defines, "RootMachine", "ROOT_MACHINE",
        parameters=parameters, initial_options=True,
    )
    if parameters:
        assert "options->parameters_present.gain" in body
        assert "scope->gain = options->parameters.gain;" in body
        assert "non-integer float from variable 'gain' initializer" in body
        assert "scope->count" not in body
        assert "scope->result" not in body
    else:
        assert "options->vars_present.count" in body
        assert "scope->count = options->vars.count;" in body
        assert "unsupported operand type(s) for <<" in body
        assert "scope->result = 0.5;" in body
        assert "scope->gain" not in body
    assert "scope->signal" not in body
    assert body.rstrip().endswith("return ROOT_MACHINE_SUCCESS;")


@pytest.mark.unittest
def test_float_input_writeback_checks_range_before_integer_cast():
    model = _model_from_dsl("""
        input float signal;
        param float gain = 2.0;
        output int result = 0;
        state Root;
    """)
    statements = parse_with_grammar_entry(
        "result = signal * gain;", entry_name="operational_statement_set"
    )
    body = render_c_action_body(statements, model.defines, "RootMachine", "ROOT_MACHINE")
    assert "RootMachine_get_input_signal(machine)" in body
    assert "RootMachine_get_param_gain(machine)" in body
    assert "outside signed 64-bit range" in body
    assert body.index("9223372036854775808.0") < body.index("(PYFCSTM_GENERATED_INT64)")


@pytest.mark.unittest
@pytest.mark.parametrize("name, expected", [
    ("gain", "gain"),
    ("a_b", "a_b"),
    ("a__b", "v_p4_az00005Fz00005Fb"),
    ("gain_", "v_p5_gainz00005F"),
    ("_x", "v_p2_z00005Fx"),
    ("class", "v_p5_class"),
    ("class_", "class_"),
    ("v_p5_class", "v_p10_vz00005Fp5z00005Fclass"),
])
def test_readonly_value_identifiers_preserve_distinct_dsl_names(name, expected):
    from pyfcstm.render.c_runtime import readonly_value_identifier
    assert readonly_value_identifier(name) == expected
