"""Unit tests for literal-only diagnostic constant folding."""

import math

import pytest

from pyfcstm.diagnostics.analyzers import (
    fold_condition_expression,
    fold_numeric_expression,
)
from pyfcstm.model.expr import parse_expr_from_string


def _num(text):
    return parse_expr_from_string(text, mode='numeric')


def _cond(text):
    return parse_expr_from_string(text, mode='logical')


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('1 + 2 * 3', 7),
        ('(0x0F & 10) | 1', 11),
        ('8 >> 1', 4),
        ('5 ^ 3', 6),
        ('(1 > 0) ? 10 : 20', 10),
        ('(1 < 0) ? 10 : 20', 20),
        ('+5', 5),
        ('-(2 ** 3)', -8),
        ('5 / 2', 2.5),
        ('7 % 4', 3),
        ('-7 % 4', 1),
        ('0xFFFFFFFF & 0xFFFFFFFF', 4294967295),
        ('(1 << 40) >> 8', 4294967296),
        ('2.0 ** 3', 8.0),
        ('2 ** 3.0', 8.0),
    ],
)
def test_fold_numeric_literal_only_expressions(text, expected):
    assert fold_numeric_expression(_num(text)) == expected


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('(1 + 2) == 3', True),
        ('(0x0F & 0xF0) != 0', False),
        ('1 < 2', True),
        ('1 <= 1', True),
        ('2 > 1', True),
        ('2 >= 2', True),
        ('true == false', False),
        ('true != false', True),
        ('(1 > 0) ? false : true', False),
        ('(1 < 0) ? false : true', True),
        ('!(2 < 1) && true', True),
        ('false || true', True),
        ('9007199254740993 == 9007199254740992', False),
    ],
)
def test_fold_condition_literal_only_expressions(text, expected):
    assert fold_condition_expression(_cond(text)) is expected


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'mode'),
    [
        ('counter + 1', 'numeric'),
        ('sin(0)', 'numeric'),
        ('1 << -1', 'numeric'),
        ('1 / 0', 'numeric'),
        ('1 % 0', 'numeric'),
        ('1.0 & 1', 'numeric'),
        ('(1.0 + 0) & 1', 'numeric'),
        ('(2 / 2) & 1', 'numeric'),
        ('1 << 2048', 'numeric'),
        ('9007199254740991 + 1', 'numeric'),
        ('10 ** 10000', 'numeric'),
        ('(1.0 & 1) == 1', 'logical'),
        ('((1.0 + 0) & 1) == 1', 'logical'),
        ('((2 / 2) & 1) == 1', 'logical'),
        ('(1 << 2048) == 0', 'logical'),
        ('(9007199254740992 + 1) == 9007199254740993', 'logical'),
        ('(2 ** 53) == 9007199254740992', 'logical'),
        ('counter > 0', 'logical'),
        ('(counter > 0) ? 1 : 2', 'numeric'),
        ('(counter > 0) ? false : true', 'logical'),
        ('(1 / 0) == 0', 'logical'),
        ('1.5 & 1', 'numeric'),
        ('(-1) ** 0.5', 'numeric'),
    ],
)
def test_unsupported_or_runtime_dependent_expressions_do_not_fold(text, mode):
    expr = parse_expr_from_string(text, mode=mode)
    if mode == 'numeric':
        assert fold_numeric_expression(expr) is None
    else:
        assert fold_condition_expression(expr) is None


@pytest.mark.unittest
def test_float_equality_uses_tolerance():
    assert fold_condition_expression(_cond('(0.1 + 0.2) == 0.3')) is True
    assert math.isclose(fold_numeric_expression(_num('0.1 + 0.2')), 0.3)


@pytest.mark.unittest
def test_collect_const_fold_warnings_none_machine():
    from pyfcstm.diagnostics.analyzers import collect_const_fold_warnings

    assert collect_const_fold_warnings(None) == []


@pytest.mark.unittest
def test_design_health_helper_keeps_minimal_const_false_fallback_without_machine():
    from pyfcstm.diagnostics import ModelMetrics, TransitionInfo
    from pyfcstm.diagnostics.analyzers import collect_design_health_warnings

    diagnostics = collect_design_health_warnings(
        states=[],
        transitions=[
            TransitionInfo(
                from_path='Root.Idle',
                to_path='Root.Active',
                event=None,
                event_scope=None,
                guard='1 == 2',
                effect=None,
                effect_self_assigns=tuple(),
                is_forced=False,
                forced_origin=None,
            )
        ],
        variables=[],
        events=[],
        actions=[],
        forced_transitions=[],
        metrics=ModelMetrics(
            n_states_leaf=0,
            n_states_composite=0,
            n_states_pseudo=0,
            max_hierarchy_depth=0,
            n_transitions_normal=1,
            n_transitions_forced=0,
            n_events=0,
            n_variables=0,
            var_to_leaf_ratio=0.0,
            aspect_coverage={},
            abstract_action_inventory=tuple(),
        ),
        reachability_graph={},
    )

    assert [diagnostic.code for diagnostic in diagnostics] == ['W_GUARD_CONST_FALSE']


@pytest.mark.unittest
def test_guard_const_message_uses_dsl_endpoint_labels():
    from pyfcstm.diagnostics import inspect_model
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine

    source = """
    state Root {
        state Idle;
        [*] -> Idle : if [true];
        Idle -> [*] : if [false];
    }
    """
    ast = parse_with_grammar_entry(source, 'state_machine_dsl')
    diagnostics = inspect_model(parse_dsl_node_to_state_machine(ast)).diagnostics
    guard_messages = [
        diagnostic.message
        for diagnostic in diagnostics
        if diagnostic.code in {'W_GUARD_CONST_TRUE', 'W_GUARD_CONST_FALSE'}
    ]
    assert "Transition '[*]' -> 'Idle'" in guard_messages[0]
    assert "Transition 'Idle' -> '[*]'" in guard_messages[1]
    assert all('INIT_STATE' not in message and 'EXIT_STATE' not in message for message in guard_messages)
