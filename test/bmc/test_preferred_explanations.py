"""Public contracts for preference-guided infeasibility explanations."""

from dataclasses import replace
import json

import pytest
import z3
from click.testing import CliRunner

from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.bmc.engine import BmcOptions
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.bmc.infeasibility import (
    CoreExtraction, minimize_source_core, partition_tracked_groups,
)
from pyfcstm.bmc.solver import _SolveBudget
from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.bmc import build_bmc_output
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

MODEL = 'def int x = 0; def int y = 0; state Root;'
QUERY = (
    'init cold where y == 0; '
    'assume at 0: y >= 1; assume at 1: x >= 1; '
    'check reach <= 2: true;'
)
OPTIONS = dict(infeasibility_explanation='formal',
               explanation_preference='editable', feedback_timeout_ms=10000)


def formula(query=QUERY, slicing=False):
    return compile_bmc_query(load_state_machine_from_text(MODEL), query,
                             options=BmcOptions(cone_slicing=slicing))


def check_groups(groups):
    solver = z3.Solver()
    solver.add(*[expr for group in groups for expr in group.expressions])
    return solver.check()


def assert_minimal(groups):
    assert check_groups(groups) == z3.unsat
    for group in groups:
        assert check_groups([g for g in groups if g.stable_id != group.stable_id]) == z3.sat


@pytest.mark.parametrize('profile', ['default', 'logic', 'tactic'])
@pytest.mark.parametrize('slicing', [False, True])
@pytest.mark.parametrize('mode', ['formal', 'proof'])
def test_preference_selects_initial_conditions_without_changing_scope(profile, slicing, mode):
    compiled = formula(slicing=slicing)
    result = solve_bmc_property(compiled, **dict(OPTIONS, infeasibility_explanation=mode),
                                solver_profile=profile)
    explanation = result.feasibility.explanation
    assert result.outcome == 'scenario_infeasible'
    assert explanation.classification == 'assumptions_prefix_conflict'
    ids = {item.constraint.stable_id for item in explanation.core.items}
    assert ids == {'initial.where', 'assumption.0000.frame.0000'}
    groups = partition_tracked_groups(compiled.core).groups_for(explanation.core.scope)
    assert_minimal([g for g in groups if g.stable_id in ids])
    assert explanation.core.subset_minimality == 'proven'
    assert result.to_canonical()['explanation_preference'] == {
        'strategy': 'editable', 'status': 'complete', 'reason': None,
    }
    if mode == 'proof':
        assert explanation.achieved_mode == 'formal'
        assert explanation.status == 'partial'
        assert 'no rule' in explanation.reason


def test_preference_can_select_members_absent_from_a_valid_raw_core():
    compiled = formula()
    scope = 'assumptions_prefix'
    groups = partition_tracked_groups(compiled.core).groups_for(scope)
    # This is another real, independently checked MUS of the same public query.
    alternative = tuple(g for g in groups if g.stable_id in {
        'transition.step.0000', 'initial.target', 'initial.variable.x',
        'assumption.0001.frame.0001',
    })
    assert_minimal(alternative)
    selected = minimize_source_core(compiled.core, CoreExtraction(alternative),
                                    _SolveBudget(10000), preference_scope=scope)
    assert {g.stable_id for g in selected.groups} == {
        'initial.where', 'assumption.0000.frame.0000',
    }
    assert_minimal(selected.groups)
    assert selected.subset_minimality == 'proven'


def test_preference_keeps_environment_self_conflict_scope():
    result = solve_bmc_property(formula(
        'assume at 0: x > 1; assume at 0: x < 0; check reach <= 2: true;'
    ), **OPTIONS)
    explanation = result.feasibility.explanation
    assert explanation.classification == 'assumptions_self_conflict'
    assert explanation.core.scope == 'assumptions_component'
    assert all(i.constraint.stage == 'assumptions' for i in explanation.core.items)


def test_preference_is_not_applicable_to_feasible_scenario():
    result = solve_bmc_property(formula('check reach <= 2: true;'), **OPTIONS)
    assert result.to_canonical()['explanation_preference']['status'] == 'not_applicable'
    assert result.feasibility.explanation is None


def test_disabled_preference_does_not_change_core_or_add_metadata():
    compiled = formula()
    default = solve_bmc_property(compiled, infeasibility_explanation='formal')
    disabled = solve_bmc_property(compiled, infeasibility_explanation='formal',
                                  explanation_preference='none')
    assert 'explanation_preference' not in disabled.to_canonical()
    assert default.feasibility.explanation.core == disabled.feasibility.explanation.core


@pytest.mark.parametrize('options', [
    {'explanation_preference': 'unknown'},
    {'explanation_preference': True},
    {'explanation_preference': []},
    {'explanation_preference': 'editable', 'feedback_timeout_ms': 10},
    {'explanation_preference': 'editable', 'infeasibility_explanation': 'formal'},
    {'feedback_timeout_ms': 10},
    dict(OPTIONS, feedback_timeout_ms=0),
    dict(OPTIONS, feedback_timeout_ms=-1),
    dict(OPTIONS, feedback_timeout_ms=True),
    dict(OPTIONS, feedback_timeout_ms=1.5),
])
def test_public_api_rejects_invalid_preference_and_budget(options):
    with pytest.raises(BmcBuildError):
        solve_bmc_property(formula(), **options)


def test_result_rejects_invalid_preference():
    result = solve_bmc_property(formula())
    with pytest.raises(BmcBuildError, match='explanation_preference'):
        replace(result, explanation_preference='invalid')


def test_cli_preferred_explanation_and_invalid_combination(tmp_path):
    model_path = tmp_path / 'machine.fcstm'
    query_path = tmp_path / 'query.fbmcq'
    model_path.write_text(MODEL, encoding='utf-8')
    query_path.write_text(QUERY, encoding='utf-8')
    args = ['bmc', '-i', str(model_path), '-q', str(query_path), '--json',
            '--explanation-preference', 'editable', '--feedback-timeout-ms', '10000']
    invalid = CliRunner().invoke(pyfcstmcli, args)
    assert invalid.exit_code != 0
    assert 'explain' in invalid.output
    valid = CliRunner().invoke(pyfcstmcli, args + ['--explain-infeasibility', 'formal'])
    assert valid.exception is None or isinstance(valid.exception, SystemExit)
    payload = json.loads(valid.output)
    assert payload['result']['explanation_preference']['status'] == 'complete'
    text, code = build_bmc_output(str(model_path), str(query_path), json_output=True, **OPTIONS)
    assert code == valid.exit_code
    assert json.loads(text)['result']['explanation_preference']['status'] == 'complete'


def test_preferred_equalities_rebuild_a_verified_proof():
    result = solve_bmc_property(formula(QUERY.replace('y >= 1', 'y == 1')),
                               **dict(OPTIONS, infeasibility_explanation='proof'))
    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == 'proof'
    assert explanation.proof.verification_status == 'verified'
    ids = {item.constraint.stable_id for item in explanation.core.items}
    assert ids == {'initial.where', 'assumption.0000.frame.0000'}
    assert {name for node in explanation.proof.nodes for name in node.item_ids} == ids


@pytest.mark.parametrize('failure_at', ['deletion', 'recheck', 'acceptance'])
@pytest.mark.parametrize('reason', ['incomplete arithmetic', 'timeout'])
def test_unknown_or_timeout_never_proves_preferred_minimality(monkeypatch, failure_at, reason):
    compiled = formula()
    scope = 'assumptions_prefix'
    groups = partition_tracked_groups(compiled.core).groups_for(scope)
    raw = tuple(g for g in groups if g.stable_id in {
        'initial.variable.y', 'assumption.0000.frame.0000',
    })
    failure_check = {'deletion': 1, 'recheck': len(groups) + 1,
                     'acceptance': len(groups) + 2}[failure_at]
    real_check = z3.Solver.check
    calls = []

    def checked(solver, *args):
        calls.append(None)
        if len(calls) == failure_check:
            return z3.unknown
        return real_check(solver, *args)

    with monkeypatch.context() as patch:
        patch.setattr(z3.Solver, 'check', checked)
        patch.setattr(z3.Solver, 'reason_unknown', lambda solver: reason)
        selected = minimize_source_core(compiled.core, CoreExtraction(raw),
                                        _SolveBudget(10000), preference_scope=scope)
    assert selected.status == ('timeout' if reason == 'timeout' else 'unknown')
    assert selected.subset_minimality == 'not_proven'
    assert check_groups(selected.groups) == z3.unsat


def test_expired_preference_search_retains_valid_raw_core(monkeypatch):
    import time
    compiled = formula()
    scope = 'assumptions_prefix'
    raw = tuple(g for g in partition_tracked_groups(compiled.core).groups_for(scope)
                if g.stable_id in {'initial.variable.y', 'assumption.0000.frame.0000'})
    clock = [0.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    budget = _SolveBudget(10)
    clock[0] = 1.0
    selected = minimize_source_core(compiled.core, CoreExtraction(raw), budget,
                                    preference_scope=scope)
    assert selected.status == 'timeout'
    assert selected.groups == raw
    assert selected.subset_minimality == 'not_proven'
    assert selected.reduction == 'raw'


@pytest.mark.parametrize('main_timeout,feedback_timeout,expected_aux', [
    (None, 5, 5), (1000, 5, 5), (6, 1000, 3), (None, 2, 2),
])
def test_feedback_deadline_starts_after_localization_and_never_resets(
        monkeypatch, main_timeout, feedback_timeout, expected_aux):
    import time
    compiled = formula()
    clock = [0.0]
    real_check = z3.Solver.check
    calls = []

    def checked(solver, *args):
        calls.append(clock[0])
        verdict = real_check(solver, *args)
        clock[0] += 0.001
        return verdict

    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(z3.Solver, 'check', checked)
    result = solve_bmc_property(compiled, timeout_ms=main_timeout,
                               **dict(OPTIONS, feedback_timeout_ms=feedback_timeout))
    assert result.outcome == 'scenario_infeasible'
    # Three mandatory checks localize this scenario; all optional work shares
    # one deadline. Float rounding can admit the last fractional millisecond.
    assert 3 + expected_aux <= len(calls) <= 4 + expected_aux
    metadata = result.to_canonical()['explanation_preference']
    assert metadata['status'] in {'partial', 'timeout'}
    assert metadata['reason']
    core = result.feasibility.explanation.core
    if core is not None:
        assert core.subset_minimality == 'not_proven'


@pytest.mark.parametrize('slicing', [False, True])
def test_explicit_feedback_budget_also_supports_response_diagnosis(slicing):
    compiled = formula('check response <= 2: trigger x > 10 -> within 1 false;', slicing)
    result = solve_bmc_property(compiled, diagnose_response_trigger=True,
                               feedback_timeout_ms=10000)
    assert result.outcome == 'property_satisfied'
    assert result.trigger_diagnostic_status == 'unsat'
    assert 'explanation_preference' not in result.to_canonical()


def test_both_feedback_requests_run_only_the_applicable_stage():
    compiled = formula(QUERY.replace('check reach <= 2: true;',
                       'check response <= 2: trigger true -> within 1 true;'))
    result = solve_bmc_property(compiled, diagnose_response_trigger=True, **OPTIONS)
    assert result.to_canonical()['explanation_preference']['status'] == 'complete'
    assert result.trigger_diagnostic_reason == 'not_applicable'


def test_explanation_entry_rejects_invalid_preference():
    from pyfcstm.bmc.infeasibility import explain_infeasibility
    with pytest.raises(BmcBuildError, match='explanation_preference'):
        explain_infeasibility(formula().core, 'assumptions', _SolveBudget(10000),
                              explanation_preference='invalid')


def test_interrupt_during_preference_search_propagates(monkeypatch):
    compiled = formula()
    real_check = z3.Solver.check
    calls = []

    def checked(solver, *args):
        calls.append(None)
        if len(calls) == 8:
            raise KeyboardInterrupt
        return real_check(solver, *args)

    monkeypatch.setattr(z3.Solver, 'check', checked)
    with pytest.raises(KeyboardInterrupt):
        solve_bmc_property(compiled, **OPTIONS)


def test_human_cli_reports_preference_without_changing_verdict(tmp_path):
    model = tmp_path / 'machine.fcstm'
    query = tmp_path / 'query.fbmcq'
    model.write_text(MODEL, encoding='utf-8')
    query.write_text(QUERY, encoding='utf-8')
    result = CliRunner().invoke(pyfcstmcli, [
        'bmc', '-i', str(model), '-q', str(query), '--color', 'never',
        '--explain-infeasibility', 'formal', '--explanation-preference', 'editable',
        '--feedback-timeout-ms', '10000',
    ])
    assert 'SCENARIO INFEASIBLE' in result.output
    assert 'Explanation preference: editable (complete).' in result.output


def test_solver_unknown_during_optional_classification_keeps_main_verdict(monkeypatch):
    compiled = formula()
    real_check = z3.Solver.check
    calls = []

    def checked(solver, *args):
        calls.append(None)
        return real_check(solver, *args) if len(calls) <= 3 else z3.unknown

    monkeypatch.setattr(z3.Solver, 'check', checked)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda solver: 'incomplete arithmetic')
    result = solve_bmc_property(compiled, **OPTIONS)
    assert result.outcome == 'scenario_infeasible'
    assert result.to_canonical()['explanation_preference']['status'] == 'unknown'


def test_disabled_preference_adds_no_solver_checks(monkeypatch):
    compiled = formula()
    real_check = z3.Solver.check
    calls = []

    def checked(solver, *args):
        calls.append(None)
        return real_check(solver, *args)

    monkeypatch.setattr(z3.Solver, 'check', checked)
    solve_bmc_property(compiled, infeasibility_explanation='formal')
    original_count = len(calls)
    calls.clear()
    solve_bmc_property(compiled, infeasibility_explanation='formal', explanation_preference='none')
    assert len(calls) == original_count


def test_preferred_selection_is_repeatable():
    compiled = formula()
    cores = [solve_bmc_property(compiled, **OPTIONS).feasibility.explanation.core
             for _ in range(5)]
    assert all(core == cores[0] for core in cores)


def test_preference_schema_accepts_results_and_rejects_invalid_metadata(tmp_path):
    from copy import deepcopy
    from pathlib import Path
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[2] /
                        'docs/source/reference/bmc_results/bmc_cli.schema.json').read_text())
    validator = jsonschema.Draft202012Validator(schema)
    model = tmp_path / 'machine.fcstm'
    query = tmp_path / 'query.fbmcq'
    model.write_text(MODEL, encoding='utf-8')
    for text in (QUERY, 'check reach <= 2: true;'):
        query.write_text(text, encoding='utf-8')
        report, _ = build_bmc_output(str(model), str(query), json_output=True, **OPTIONS)
        payload = json.loads(report)
        validator.validate(payload)
        for field, value in [('strategy', 'arbitrary'), ('status', 'optimal'),
                             ('reason', 42), ('extra', True)]:
            bad = deepcopy(payload)
            bad['result']['explanation_preference'][field] = value
            assert not validator.is_valid(bad), (field, value)
        for field in ('strategy', 'status', 'reason'):
            bad = deepcopy(payload)
            del bad['result']['explanation_preference'][field]
            assert not validator.is_valid(bad)
        bad = deepcopy(payload)
        bad['result']['explanation_preference']['reason'] = (
            'unexpected' if text == QUERY else None
        )
        assert not validator.is_valid(bad)
        if text != QUERY:
            bad = deepcopy(payload)
            bad['result']['explanation_preference'] = {
                'strategy': 'editable', 'status': 'complete', 'reason': None,
            }
            assert not validator.is_valid(bad)


@pytest.mark.parametrize('profile', ['default', 'logic', 'tactic'])
def test_preferred_core_with_dynamic_input_and_actually_sliced_writes(profile):
    model = load_state_machine_from_text('''
        input int command;
        def int unused = 0;
        state Root { during { unused = unused + 1; } }
    ''')
    compiled = compile_bmc_query(model,
        'assume at 1: command == 1; assume at 1: command == 2; check reach <= 3: true;',
        options=BmcOptions(cone_slicing=True))
    assert compiled.core.cone_slice.dropped_variables == ('unused',)
    result = solve_bmc_property(compiled, **OPTIONS, solver_profile=profile)
    assert result.outcome == 'scenario_infeasible'
    assert result.to_canonical()['explanation_preference']['status'] == 'complete'
    assert result.feasibility.explanation.core.scope == 'assumptions_component'


def test_sliced_sat_replay_fallback_preserves_preference_request(monkeypatch):
    import pyfcstm.bmc.witness as witness
    model = load_state_machine_from_text('''
        def int x = 0; def int unused = 0;
        state Root { enter { x = 1; unused = 2; } }
    ''')
    compiled = compile_bmc_query(model, 'check reach <= 2: x == 1;',
                                 options=BmcOptions(cone_slicing=True))
    assert compiled.core.cone_slice.dropped_variables == ('unused',)

    def reject_candidate(*args):
        raise witness._ConeReplayFailure('replay rejected sliced candidate')

    monkeypatch.setattr(witness, '_fill_cone_trace', reject_candidate)
    result = solve_bmc_property(compiled, **OPTIONS)
    assert result.status == 'sat'
    assert result.to_canonical()['cone_slicing']['fallback'] is True
    assert result.to_canonical()['explanation_preference']['status'] == 'not_applicable'


def test_main_deadline_exhausted_at_localization_prevents_feedback_setup(monkeypatch):
    import time
    compiled = formula()
    real_check = z3.Solver.check
    clock = [0.0]
    calls = []

    def checked(solver, *args):
        calls.append(None)
        verdict = real_check(solver, *args)
        clock[0] += 0.001
        return verdict

    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(z3.Solver, 'check', checked)
    result = solve_bmc_property(compiled, timeout_ms=3, **OPTIONS)
    assert result.outcome == 'scenario_infeasible'
    assert len(calls) == 3
    metadata = result.to_canonical()['explanation_preference']
    assert metadata['status'] == 'timeout'
    assert 'before preference classification' in metadata['reason']


def test_low_level_selection_accepts_explicit_unbounded_budget():
    # The low-level explanation API receives its budget object directly; only
    # the public solve/CLI preference option requires a finite feedback cap.
    from pyfcstm.bmc.infeasibility import explain_infeasibility
    outcome = explain_infeasibility(formula().core, 'assumptions', _SolveBudget(None),
                                    explanation_preference='editable')
    assert outcome.explanation.core.subset_minimality == 'proven'
