from pathlib import Path

import pytest
import z3

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import IfBlock, Operation, parse_dsl_node_to_state_machine
from pyfcstm.solver.operation import execute_operations
from pyfcstm.simulate import SimulationRuntime


_SAMPLE_FILE = (
    Path(__file__).resolve().parent / 'testfile' / 'sample_codes' / 'if_nested_temporaries.fcstm'
)


def _load_sample_model():
    ast = parse_with_grammar_entry(
        _SAMPLE_FILE.read_text(encoding='utf-8'),
        'state_machine_dsl',
    )
    return parse_dsl_node_to_state_machine(ast)


def _assert_z3_expr_equal(actual_expr, expected_expr):
    actual_simplified = z3.simplify(actual_expr)
    expected_simplified = z3.simplify(expected_expr)
    assert z3.eq(actual_simplified, expected_simplified), (
        f'Expected Z3 expr {expected_simplified.sexpr()}, '
        f'got {actual_simplified.sexpr()}'
    )


@pytest.mark.unittest
class TestIfNestedTemporariesSample:
    def test_model_exposes_recursive_statement_tree(self):
        model = _load_sample_model()

        active = model.root_state.substates['Active']
        statements = active.on_durings[0].operations

        assert len(statements) == 3
        assert isinstance(statements[0], Operation)
        assert statements[0].var_name == 'tmp'
        assert isinstance(statements[1], IfBlock)
        assert len(statements[1].branches) == 3
        assert isinstance(statements[2], Operation)
        assert statements[2].var_name == 'x'

    @pytest.mark.parametrize(
        ['initial_vars', 'expected_vars'],
        [
            (
                {'x': 4, 'y': 6, 'z': 0, 'flag': 1},
                {'x': 38, 'y': 6, 'z': 23, 'flag': 1},
            ),
            (
                {'x': 4, 'y': 2, 'z': 0, 'flag': 1},
                {'x': 28, 'y': 2, 'z': 13, 'flag': 1},
            ),
            (
                {'x': 4, 'y': 9, 'z': 0, 'flag': 0},
                {'x': 50, 'y': 9, 'z': 25, 'flag': 0},
            ),
            (
                {'x': 2, 'y': 9, 'z': 0, 'flag': 0},
                {'x': 6, 'y': 9, 'z': 3, 'flag': 0},
            ),
        ],
    )
    def test_runtime_executes_sample_during_block(self, initial_vars, expected_vars):
        model = _load_sample_model()
        runtime = SimulationRuntime(
            model,
            initial_state='Root.Active',
            initial_vars=initial_vars,
        )

        runtime.cycle()

        assert runtime.current_state.path == ('Root', 'Active')
        assert runtime.vars == expected_vars

    def test_solver_flattens_nested_if_sample(self):
        model = _load_sample_model()
        statements = model.root_state.substates['Active'].on_durings[0].operations

        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')
        flag = z3.Int('flag')

        new_exprs = execute_operations(
            statements,
            {'x': x, 'y': y, 'z': z, 'flag': flag},
        )

        expected_z = z3.If(
            flag > 0,
            z3.If(y > 5, x + y + 13, x + 11 - y),
            z3.If(x > 3, x + 21, x + 1),
        )
        expected_tmp = z3.If(
            flag > 0,
            x + 11,
            z3.If(x > 3, x + 21, x + 1),
        )
        expected_x = expected_z + expected_tmp

        _assert_z3_expr_equal(new_exprs['z'], expected_z)
        _assert_z3_expr_equal(new_exprs['x'], expected_x)
        _assert_z3_expr_equal(new_exprs['y'], y)
        _assert_z3_expr_equal(new_exprs['flag'], flag)
