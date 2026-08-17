"""Tests for the aggregated unreachable-transition diagnostic."""

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


def _unreachable_transitions(report):
    return [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.code == 'W_UNREACHABLE_TRANSITION'
    ]


def test_reports_source_unreachable_reason_once_per_authored_transition():
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
        'from_path': 'Root.Orphan',
        'to_path': 'Root.Done',
        'transition_index': 1,
        'reasons': ['unreachable_source_state'],
        'source_path': None,
        'source_state_path': 'Root.Orphan',
        'selection_owner_path': None,
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


def test_reports_only_unreachable_leaf_states_under_an_unreachable_composite():
    report = _inspect(
        '''
        state Root {
            state Live;
            state Orphan {
                state Child;
                [*] -> Child;
            }
            [*] -> Live;
        }
        '''
    )

    unreachable = [
        diagnostic.refs['state_path']
        for diagnostic in report.diagnostics
        if diagnostic.code == 'W_UNREACHABLE_STATE'
    ]
    assert unreachable == ['Root.Orphan.Child']
    assert report.structure_statistics.unreachable_leaf_states == 1


def test_guard_reason_is_aggregated_and_kept_separate_from_topology():
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

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['reasons'] == ['guard_false']


def test_combo_diagnostic_uses_authored_endpoints():
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
    assert diagnostics[0].refs['reasons'] == ['unreachable_source_state']


def test_exit_combo_diagnostic_keeps_exit_endpoint():
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


def test_partial_forced_expansion_is_aggregated_once_per_authored_transition():
    report = _inspect(
        '''
        state Root {
            state Live;
            state OrphanA;
            state OrphanB;
            state Done;
            [*] -> Live;
            !* -> Done :: Panic;
        }
        '''
    )

    diagnostics = _unreachable_transitions(report)
    assert len(diagnostics) == 1
    assert diagnostics[0].refs['forced_origin'] == '! * -> Done :: Panic;'
    assert diagnostics[0].refs['source_state_path'] in {
        'Root.OrphanA', 'Root.OrphanB',
    }


def test_code_contract_is_aggregated_and_transition_scoped():
    spec = CODE_REGISTRY['W_UNREACHABLE_TRANSITION']
    assert spec.capability == 'pure_static'
    assert spec.emit_tier == 'static_pipeline'
    assert spec.span_object == 'transition'
    assert spec.refs_schema['reasons'].item_enum == (
        'unreachable_source_state',
        'unreachable_event_consumer',
        'forced_never_expands',
        'guard_false',
        'shadowed',
        'redundant',
    )
