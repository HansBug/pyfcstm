"""Tests for the topological unreachable-transition diagnostic."""

from dataclasses import replace
from textwrap import dedent

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

from ._schema_check import assert_all_diags_match_schema


pytestmark = pytest.mark.unittest


def _inspect(source: str):
    ast = parse_with_grammar_entry(dedent(source), 'state_machine_dsl')
    return inspect_model(parse_dsl_node_to_state_machine(ast))


def _inspect_legacy_combo(source: str):
    ast = parse_with_grammar_entry(dedent(source), 'state_machine_dsl')
    machine = parse_dsl_node_to_state_machine(ast)
    for state in machine.walk_states():
        for transition in state.transitions:
            if not transition.combo_origin_refs:
                continue
            transition.combo_origin_refs = tuple(
                replace(
                    ref,
                    source_path=None,
                    selection_owner_path=None,
                    target_path=None,
                )
                for ref in transition.combo_origin_refs
            )
    return inspect_model(machine)


def _unreachable_transitions(report):
    return [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.code == 'W_UNREACHABLE_TRANSITION'
    ]


def test_reports_transition_from_unreachable_source_with_transition_refs():
    report = _inspect(
        '''
        state Root {
            state Reachable;
            state Orphan;
            state Done;
            [*] -> Reachable;
            Orphan -> Done;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.span is not None
    assert diagnostic.refs == {
        'reason': 'source_unreachable',
        'verification_scope': 'topological_only',
        'from_path': 'Root.Orphan',
        'to_path': 'Root.Done',
        'source_state_path': 'Root.Orphan',
        'selection_owner_path': None,
        'source_path': None,
        'transition_index': 1,
        'forced_origin': None,
        'combo_origin_ids': [],
    }
    assert_all_diags_match_schema(diagnostics, context='unreachable-transition')


def test_reachable_source_is_not_reported():
    report = _inspect(
        '''
        state Root {
            state Active;
            state Done;
            [*] -> Active;
            Active -> Done;
        }
        '''
    )

    assert _unreachable_transitions(report) == []


def test_nested_initial_selection_uses_unreachable_composite_owner():
    report = _inspect(
        '''
        state Root {
            state Active;
            state Orphan {
                state Child;
                [*] -> Child;
            }
            [*] -> Active;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs == {
        'reason': 'source_unreachable',
        'verification_scope': 'topological_only',
        'from_path': '[*]',
        'to_path': 'Root.Orphan.Child',
        'source_state_path': None,
        'selection_owner_path': 'Root.Orphan',
        'source_path': None,
        'transition_index': 1,
        'forced_origin': None,
        'combo_origin_ids': [],
    }


def test_literal_false_guard_stays_separate_from_topological_finding():
    report = _inspect(
        '''
        state Root {
            state Active;
            state Done;
            [*] -> Active;
            Active -> Done : if [false];
        }
        '''
    )

    assert _unreachable_transitions(report) == []
    assert [d.code for d in report.diagnostics].count('W_GUARD_CONST_FALSE') == 1


def test_event_trigger_does_not_affect_source_topology_finding():
    report = _inspect(
        '''
        state Root {
            event External;
            state Active;
            state Orphan;
            state Done;
            [*] -> Active;
            Orphan -> Done : External;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['from_path'] == 'Root.Orphan'


def test_combo_relays_emit_one_authored_transition_finding():
    report = _inspect(
        '''
        state Root {
            state Orphan;
            state Done;
            [*] -> Done;
            Orphan -> Done :: E1 + E2;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['from_path'] == 'Root.Orphan'
    assert diagnostics[0].refs['to_path'] == 'Root.Done'
    assert diagnostics[0].refs['transition_index'] is None
    assert len(diagnostics[0].refs['combo_origin_ids']) == 1


def test_combo_exit_uses_exit_endpoint_for_authored_transition():
    report = _inspect(
        '''
        state Root {
            state Active;
            state Orphan;
            [*] -> Active;
            Orphan -> [*] :: E1 + E2;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['from_path'] == 'Root.Orphan'
    assert diagnostics[0].refs['to_path'] == '[*]'


@pytest.mark.parametrize(
    ('source', 'from_path', 'to_path', 'selection_owner_path'),
    [
        (
            '''
            state Root {
                state Orphan;
                state Done;
                [*] -> Done;
                Orphan -> Done :: E1 + E2;
            }
            ''',
            'Root.Orphan',
            'Root.Done',
            None,
        ),
        (
            '''
            state Root {
                state Orphan {
                    state Child;
                    [*] -> Child :: E1 + E2;
                }
                state Done;
                [*] -> Done;
            }
            ''',
            '[*]',
            'Root.Orphan.Child',
            'Root.Orphan',
        ),
        (
            '''
            state Root {
                state Orphan;
                state Active;
                [*] -> Active;
                Orphan -> [*] :: E1 + E2;
            }
            ''',
            'Root.Orphan',
            '[*]',
            None,
        ),
    ],
    ids=['normal', 'initial', 'exit'],
)
def test_legacy_combo_provenance_recovers_authored_endpoints(
        source, from_path, to_path, selection_owner_path,
):
    diagnostics = _unreachable_transitions(_inspect_legacy_combo(source))

    assert len(diagnostics) == 1
    assert diagnostics[0].refs['from_path'] == from_path
    assert diagnostics[0].refs['to_path'] == to_path
    assert diagnostics[0].refs['selection_owner_path'] == selection_owner_path


def test_shared_combo_prefix_keeps_each_authored_origin_separate():
    report = _inspect(
        '''
        state Root {
            state Orphan;
            state Done;
            state Other;
            [*] -> Done;
            Orphan -> Done :: E1 + E2;
            Orphan -> Other :: E1 + E3;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 2
    assert {diagnostic.refs['to_path'] for diagnostic in diagnostics} == {
        'Root.Done',
        'Root.Other',
    }
    assert {diagnostic.span.line for diagnostic in diagnostics} == {7, 8}
    assert {
        diagnostic.refs['combo_origin_ids'][0]
        for diagnostic in diagnostics
    } == {
        'Root:Orphan->Done::: E1 + E2',
        'Root:Orphan->Other::: E1 + E3',
    }


def test_forced_partial_expansion_reports_the_concrete_unreachable_source():
    report = _inspect(
        '''
        state Root {
            state Group {
                state Reach;
                state Lost;
                state Done;
                [*] -> Reach;
                !* -> Done :: Panic;
            }
            [*] -> Group;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.message.startswith('Generated forced transition expansion')
    assert diagnostic.refs['from_path'] == 'Root.Group.Lost'
    assert diagnostic.refs['source_state_path'] == 'Root.Group.Lost'
    assert diagnostic.refs['forced_origin'] == '! * -> Done :: Panic;'


def test_combo_effect_origin_keeps_right_associative_expression_and_array_spacing():
    report = _inspect(
        '''
        def int x = 0;
        state Root {
            state Orphan;
            state Done;
            [*] -> Done;
            Orphan -> Done :: E1 + E2 effect {
                x = 2 ** 3 ** 4;
                x = 1;
            }
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['combo_origin_ids'] == [
        'Root:Orphan->Done::: E1 + E2:effect=["x = 2 ** 3 ** 4;", "x = 1;"]',
    ]


def test_solver_dead_guard_stays_out_of_topological_finding():
    report = inspect_model(
        parse_dsl_node_to_state_machine(
            parse_with_grammar_entry(
                dedent(
                    '''
                    def int x = 0;
                    state Root {
                        state Active;
                        state Done;
                        [*] -> Active;
                        Active -> Done : if [x > 1 && x < 0];
                    }
                    '''
                ),
                'state_machine_dsl',
            )
        ),
        enable_verify=True,
        max_complexity_tier='smt_linear',
    )

    assert _unreachable_transitions(report) == []
    assert any(d.code == 'W_DEAD_GUARD' for d in report.diagnostics)


def test_enable_verify_does_not_duplicate_static_transition_finding():
    report = _inspect(
        '''
        state Root {
            state Active;
            state Orphan;
            state Done;
            [*] -> Active;
            Orphan -> Done;
        }
        '''
    )
    verified = inspect_model(
        parse_dsl_node_to_state_machine(
            parse_with_grammar_entry(
                dedent(
                    '''
                    state Root {
                        state Active;
                        state Orphan;
                        state Done;
                        [*] -> Active;
                        Orphan -> Done;
                    }
                    '''
                ),
                'state_machine_dsl',
            )
        ),
        enable_verify=True,
    )

    assert len(_unreachable_transitions(report)) == 1
    assert len(_unreachable_transitions(verified)) == 1
    assert_all_diags_match_schema(
        _unreachable_transitions(verified),
        context='unreachable-transition-verify',
    )


def test_code_contract_is_static_and_transition_scoped():
    spec = CODE_REGISTRY['W_UNREACHABLE_TRANSITION']
    assert spec.capability == 'pure_static'
    assert spec.emit_tier == 'static_pipeline'
    assert spec.span_object == 'transition'
    assert spec.refs_schema['reason'].enum == ('source_unreachable',)
    assert spec.refs_schema['verification_scope'].enum == ('topological_only',)


def test_combo_endpoint_metadata_does_not_reserve_pseudo_state_names():
    report = _inspect(
        '''
        state Root {
            state __init__;
            state __exit__;
            state Done;
            [*] -> Done;
            __init__ -> __exit__ :: E1 + E2;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['from_path'] == 'Root.__init__'
    assert diagnostics[0].refs['to_path'] == 'Root.__exit__'
