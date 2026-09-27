"""Public exact-query and fixed-background conflict-core behavior."""

import pytest
import z3

import pyfcstm.solver as solver


pytestmark = pytest.mark.unittest


def test_named_groups_keep_sources_and_find_the_minimal_conflict():
    """Dropping either the update or its goal would lose the contradiction."""
    x, y, noise = z3.Ints('x y noise')
    source = {'file': 'rules.txt', 'line': 3}
    groups = (
        solver.UnsatConstraint('initial', (x >= 0,), source),
        solver.UnsatConstraint('update', (y == x + 1,)),
        solver.UnsatConstraint('goal', (y < 0,)),
        solver.UnsatConstraint('noise', (noise >= 0,)),
    )
    query = solver.UnsatQuery('increment', groups)
    report = solver.explain_unsat_core(query)
    assert report.query is query
    assert report.query.constraints[0].source is source
    assert report.solver_status == 'unsat'
    assert report.core_check == 'verified'
    assert report.core_ids == ('goal', 'initial', 'update')
    assert report.subset_minimality == 'proven'
    assert not report.background_conflict
    assert report.stop_reason is None


def test_fixed_background_is_present_in_every_deletion_check():
    x = z3.Int('x')
    query = solver.UnsatQuery('background', (
        solver.UnsatConstraint('goal', (x < 0,)),
        solver.UnsatConstraint('noise', (x < 100,)),
    ), background=(solver.UnsatConstraint('domain', (x >= 0,)),))
    report = solver.explain_unsat_core(query)
    assert report.core_ids == ('goal',)
    assert report.subset_minimality == 'proven'
    assert report.core_check == 'verified'


def test_background_contradiction_has_a_verified_empty_core():
    query = solver.UnsatQuery('background', (), background=(
        solver.UnsatConstraint('impossible', (z3.BoolVal(False),)),
    ))
    report = solver.explain_unsat_core(query)
    assert report.solver_status == 'unsat'
    assert report.core_ids == ()
    assert report.background_conflict
    assert report.subset_minimality == 'proven'


@pytest.mark.parametrize('has_true', [False, True])
def test_satisfiable_query_has_no_core(has_true):
    groups = (solver.UnsatConstraint('true', (z3.BoolVal(True),)),) if has_true else ()
    report = solver.explain_unsat_core(solver.UnsatQuery('sat', groups))
    assert report.solver_status == 'sat'
    assert report.core_ids is None
    assert not report.background_conflict


def test_groups_are_atomic_and_explicit_duplicate_occurrences_are_preserved():
    x = z3.Int('x')
    query = solver.UnsatQuery('duplicates', (
        solver.UnsatConstraint('first', (x >= 0, x <= 10)),
        solver.UnsatConstraint('second', (x >= 0, x <= 10)),
        solver.UnsatConstraint('goal', (x < 0,)),
    ))
    report = solver.explain_unsat_core(
        query, selected_ids=('second', 'goal'), minimize=False,
    )
    assert report.core_ids == ('goal', 'second')
    assert report.subset_minimality == 'not_proven'
    selected = solver.explain_unsat_core(query, selected_ids=('second',))
    assert selected.solver_status == 'unsat'
    assert selected.core_check == 'sat'
    assert selected.core_ids is None
    assert solver.explain_unsat_core(query).core_check == 'verified'


def test_explicit_empty_selection_checks_only_the_background():
    query = solver.UnsatQuery('selection', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    ))
    report = solver.explain_unsat_core(query, selected_ids=())
    assert report.solver_status == 'unsat'
    assert report.core_ids is None
    assert report.core_check == 'sat'


def test_nondefault_context_is_used_for_all_core_checks():
    context = z3.Context()
    x = z3.Int('x', ctx=context)
    query = solver.UnsatQuery('context', (
        solver.UnsatConstraint('lower', (x > 3,)),
        solver.UnsatConstraint('upper', (x < 2,)),
    ))
    assert solver.explain_unsat_core(query).core_ids == ('lower', 'upper')


@pytest.mark.parametrize('identifier,expressions,error', [
    ('', (True,), ValueError),
    (3, (True,), TypeError),
    ('empty', (), ValueError),
    ('python-bool', (True,), TypeError),
    ('integer', (1,), TypeError),
])
def test_invalid_constraint_input_is_rejected(identifier, expressions, error):
    with pytest.raises(error):
        solver.UnsatConstraint(identifier, expressions)


def test_mixed_contexts_are_rejected_within_and_between_groups():
    left = z3.Bool('left')
    right = z3.Bool('right', ctx=z3.Context())
    with pytest.raises(ValueError, match='context'):
        solver.UnsatConstraint('mixed', (left, right))
    with pytest.raises(ValueError, match='context'):
        solver.UnsatQuery('mixed', (solver.UnsatConstraint('left', (left,)),),
                          (solver.UnsatConstraint('right', (right,)),))


@pytest.mark.parametrize('identifier,error', [('', ValueError), (42, TypeError)])
def test_invalid_query_identifier_is_rejected(identifier, error):
    with pytest.raises(error):
        solver.UnsatQuery(identifier, ())


def test_query_rejects_foreign_groups_and_duplicate_ids():
    with pytest.raises(TypeError):
        solver.UnsatQuery('bad', (z3.BoolVal(True),))
    group = solver.UnsatConstraint('same', (z3.BoolVal(True),))
    with pytest.raises(ValueError):
        solver.UnsatQuery('bad', (group,), (group,))


@pytest.mark.parametrize('selection,error', [
    ('rule', TypeError), ((1,), TypeError),
    (('missing',), ValueError), (('rule', 'rule'), ValueError),
])
def test_invalid_selection_is_rejected(selection, error):
    query = solver.UnsatQuery('selection', (
        solver.UnsatConstraint('rule', (z3.BoolVal(False),)),
    ))
    with pytest.raises(error):
        solver.explain_unsat_core(query, selected_ids=selection)


def test_query_and_minimization_option_types_are_checked():
    with pytest.raises(TypeError):
        solver.explain_unsat_core('not a query')
    with pytest.raises(TypeError):
        solver.explain_unsat_core(solver.UnsatQuery('empty', ()), minimize=1)


@pytest.mark.parametrize('timeout', [0, -1, True, 1.5, '10'])
def test_invalid_timeout_is_rejected(timeout):
    with pytest.raises(ValueError):
        solver.explain_unsat_core(solver.UnsatQuery('empty', ()), timeout_ms=timeout)


def test_budgeted_core_runs_real_solver_checks():
    query = solver.UnsatQuery('false', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    ))
    report = solver.explain_unsat_core(query, timeout_ms=10000)
    assert report.core_ids == ('false',)
    assert all(check.started for check in report.checks)
    assert all(check.elapsed_ms >= 0 for check in report.checks)


@pytest.mark.parametrize('call,status,core_ids', [
    (3, 'unknown', ('false',)),
    (3, 'timeout', ('false', 'noise')),
    (4, 'unknown', ('false', 'noise')),
    (4, 'timeout', ('false', 'noise')),
    (5, 'unknown', ('false',)),
    (5, 'timeout', ('false',)),
])
def test_inconclusive_deletion_or_acceptance_keeps_a_sound_core(monkeypatch, call, status, core_ids):
    original = z3.Solver.check
    calls = []

    def check(native, *assumptions):
        calls.append(assumptions)
        return z3.unknown if len(calls) == call else original(native, *assumptions)

    monkeypatch.setattr(z3.Solver, 'check', check)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda native: status)
    query = solver.UnsatQuery('deletion', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
        solver.UnsatConstraint('noise', (z3.Bool('noise'),)),
    ))
    result = solver.explain_unsat_core(query, selected_ids=('false', 'noise'))
    assert result.core_ids == core_ids
    assert result.core_check == 'verified'
    assert result.subset_minimality == 'not_proven'
    assert result.reduction == 'partial_minimized'
    assert result.checks[-1].status == status
    assert result.stop_reason == (
        'acceptance check for false did not return sat' if call == 5 else
        ('deletion trial timed out' if status == 'timeout' else 'deletion trial returned unknown'))


@pytest.mark.parametrize('expire_after,reduction', [(2, 'raw'), (4, 'partial_minimized')])
def test_budget_expiry_before_deletion_or_acceptance_preserves_verified_core(monkeypatch, expire_after, reduction):
    import time

    now = [0.0]
    original = z3.Solver.check
    count = [0]

    def check(native, *assumptions):
        result = original(native, *assumptions)
        count[0] += 1
        if count[0] == expire_after:
            now[0] = 1.0
        return result

    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(z3.Solver, 'check', check)
    query = solver.UnsatQuery('budget', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
        solver.UnsatConstraint('noise', (z3.Bool('noise'),)),
    ))
    result = solver.explain_unsat_core(query, selected_ids=('false', 'noise'), timeout_ms=100)
    assert result.reduction == reduction
    assert result.core_check == 'verified'
    assert result.subset_minimality == 'not_proven'
    assert count[0] == expire_after
    assert result.stop_reason == ('budget exhausted before a deletion trial started' if expire_after == 2
                                  else 'acceptance check for false did not return sat')


def test_an_explicit_core_can_shrink_to_empty_when_background_is_inconsistent():
    query = solver.UnsatQuery('background', (
        solver.UnsatConstraint('unused', (z3.Bool('unused'),)),
    ), (solver.UnsatConstraint('fixed', (z3.BoolVal(False),)),))
    result = solver.explain_unsat_core(query, selected_ids=('unused',))
    assert result.core_ids == ()
    assert result.subset_minimality == 'proven'
    assert result.reduction == 'subset_minimal'


def test_expiry_before_extraction_reports_a_check_that_did_not_start(monkeypatch):
    import time

    values = iter((0.0, 1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(values))
    result = solver.explain_unsat_core(solver.UnsatQuery('empty', ()), timeout_ms=100)
    assert result.solver_status == 'timeout'
    assert result.checks[0].started is False
    assert result.stop_reason == 'core extraction did not start: budget exhausted before the probe started'


def test_unknown_without_a_backend_reason_still_has_a_diagnostic(monkeypatch):
    monkeypatch.setattr(z3.Solver, 'check', lambda native, *assumptions: z3.unknown)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda native: '')
    result = solver.explain_unsat_core(solver.UnsatQuery('empty', ()))
    assert result.solver_status == 'unknown'
    assert result.checks[0].reason == 'unknown'
