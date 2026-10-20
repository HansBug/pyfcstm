"""Guard invariance needs a satisfiable evaluation domain before a refutation."""

import pytest
import z3

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.solver import UnsatConstraint, UnsatQuery
from pyfcstm.solver.domain import translate_expr_domain
from pyfcstm.solver.expr import create_z3_vars_from_models
from pyfcstm.solver.proof import explain_unsat
from pyfcstm.verify import dead_guard, guard_tautology

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('guard,dead,tautology', [
    ('x>1 && x<0', 'unsat', 'sat'),
    ('x<0 || x>=0', 'sat', 'unsat'),
    ('x>0', 'sat', 'sat'),
    ('1/0>0', 'undecidable_skip', 'undecidable_skip'),
    ('x==0 || 1/x>0', 'sat', 'sat'),
])
def test_actual_guard_domain_distinguishes_invariance_from_undefinedness(guard, dead, tautology):
    model = load_state_machine_from_text(
        'def int x=0; state Root { state A; state B; [*]->A; A->B: if [%s]; }' % guard)
    transition = next(item for state in model.walk_states() for item in state.transitions
                      if item.guard is not None)
    variables = tuple(model.defines.values())
    assert dead_guard(transition, variables).kind == dead
    assert guard_tautology(transition, variables).kind == tautology
    lowered = translate_expr_domain(transition.guard, create_z3_vars_from_models(model))
    assert lowered.failure is None
    domain = z3.And(*(item.constraint for item in lowered.definedness_constraints))
    # Undefined evaluation is not a proof of either truth value of the guard.
    domain_report = explain_unsat(UnsatQuery('domain', (UnsatConstraint('definedness', (domain,)),)))
    assert domain_report.solver_status == ('unsat' if dead == 'undecidable_skip' else 'sat')
    if dead == 'undecidable_skip':
        return
    for predicate, expected in ((lowered.z3_expr, dead), (z3.Not(lowered.z3_expr), tautology)):
        report = explain_unsat(UnsatQuery('guard', (
            UnsatConstraint('definedness', (domain,)), UnsatConstraint('predicate', (predicate,)),
        )))
        assert report.solver_status == expected
        if expected == 'unsat':
            assert report.input_check == 'passed'
            assert report.scope_check == 'passed'
            assert report.reading_status == 'complete'
            assert report.gaps == ()


@pytest.mark.parametrize('context_status', ['consistent', 'inconsistent'])
def test_context_must_be_consistent_before_claiming_conditional_guard_invariance(context_status):
    x = z3.Int('x')
    context = z3.And(x >= 0, x < 0) if context_status == 'inconsistent' else x >= 0
    premise = UnsatConstraint('context', (context,))
    baseline = explain_unsat(UnsatQuery('context', (premise,)))
    assert baseline.solver_status == ('unsat' if context_status == 'inconsistent' else 'sat')
    report = explain_unsat(UnsatQuery('guard', (premise, UnsatConstraint('negated_guard', (x + 1 <= 0,)))))
    assert report.solver_status == 'unsat'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    # The same UNSAT result needs the separate SAT-context check above to mean invariance.
