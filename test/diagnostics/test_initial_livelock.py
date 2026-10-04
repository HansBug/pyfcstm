"""Public inspect coverage for closed same-cycle routing loops."""

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

from ._schema_check import assert_all_diags_match_schema

pytestmark = pytest.mark.unittest


def _warnings(source):
    machine = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, 'state_machine_dsl'))
    report = inspect_model(machine)
    return [item for item in report.diagnostics if item.code == 'W_INITIAL_LIVELOCK']


def test_nested_forced_reset_reports_paths_transitions_and_repair():
    warnings = _warnings('''
        state R {
            state A { state B { pseudo state P; [*] -> P; } [*] -> B; }
            state Idle;
            [*] -> Idle;
            Idle -> A :: go;
            !A -> A :: loop;
        }
    ''')
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.severity == 'warning'
    assert warning.span is not None
    assert warning.refs['state_paths'] == ['R.A', 'R.A.B', 'R.A.B.P']
    assert set(warning.refs['transitions']) == {'0', '3', '4', '5', '6'}
    assert 'potential' in warning.message.lower()
    assert 'stoppable' in warning.message.lower()
    assert_all_diags_match_schema(warnings)
    assert CODE_REGISTRY[warning.code].for_llm.recommended_actions


@pytest.mark.parametrize('source', [
    'state R;',
    'state R { state A; [*] -> A; !A -> A :: reset; }',
    'state R { pseudo state P; state A; [*] -> P; P -> P; P -> A; }',
    'state R { pseudo state P; [*] -> P; P -> P; P -> [*]; }',
    'state R { state A { pseudo state P; [*] -> P; P -> [*]; } [*] -> A; A -> [*]; }',
    'state R { state A { state B; [*] -> B; B -> [*]; } [*] -> A; A -> A; }',
])
def test_stoppable_or_terminating_routes_do_not_warn(source):
    assert _warnings(source) == []


@pytest.mark.parametrize('transitions', ['P -> P;', 'P -> Q; Q -> P;'])
def test_closed_pseudo_cycles_warn(transitions):
    warnings = _warnings('state R { pseudo state P; pseudo state Q; [*] -> P; ' + transitions + ' }')
    assert len(warnings) == 1
    assert 'R.P' in warnings[0].refs['state_paths']


@pytest.mark.parametrize('source', [
    'state R { state A; Missing -> A; [*] -> A; }',
    'state R { state A; [*] -> Missing; }',
    'state R { pseudo state P; [*] -> P; P -> Missing; }',
])
def test_partially_built_models_preserve_dangling_errors(source):
    machine, errors = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, 'state_machine_dsl'), collect=True)
    report = inspect_model(machine, model_diagnostics=errors)
    assert 'E_DANGLING_TRANSITION' in {item.code for item in report.diagnostics}
    assert not any(item.code == 'W_INITIAL_LIVELOCK' for item in report.diagnostics)


def test_guarded_escape_suppresses_structural_warning():
    assert _warnings('''
        def int ready = 0;
        state R { pseudo state P; state Done; [*] -> P;
            P -> P; P -> Done : if [ready > 0]; }
    ''') == []


def test_converging_pseudo_routes_are_not_cycles():
    assert _warnings('''
        state R {
            pseudo state P; pseudo state Q; pseudo state S; state Done;
            [*] -> P; P -> Q; P -> S; Q -> S; S -> Done;
        }
    ''') == []
