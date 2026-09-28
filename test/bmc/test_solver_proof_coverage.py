"""Actual BMC formulas remain explainable by the generic proof subsystem."""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat

pytestmark = pytest.mark.unittest


def test_three_event_cardinality_has_a_complete_native_proof():
    """FBMCQ's actual AtMost encoding is covered, including native PB lemmas."""
    model = load_state_machine_from_text('''
state Root {
    event E1;
    event E2;
    event E3;
    state A;
    [*] -> A;
}
''')
    query = '''
init state("Root.A");
assume event("Root.E1", 0) == true;
assume event("Root.E2", 0) == true;
assume events cardinality at_most_one { "Root.E1", "Root.E2", "Root.E3" };
check reach <= 1: active("Root.A");
'''
    core = build_bmc_core_formula(BmcEngine(model).prepare(query))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('events', (
        UnsatConstraint('domain', (core.domain_formula,)),
        UnsatConstraint('initial', (core.initial_formula,)),
        UnsatConstraint('transitions', (core.transition_formula,)),
        UnsatConstraint('environment', (core.environment_formula,)),
        UnsatConstraint('objective', (prop.objective_formula,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert any(node.cardinality is not None for node in report.proof.nodes)


def test_remainder_guard_cannot_reach_target_with_positive_divisor():
    """Exercise definedness, transition implication and FBMCQ source formulas."""
    model = load_state_machine_from_text('''
def int x = 0;
def int d = 1;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B : if [x % d < 0];
}
''')
    query = '''
init state("Root.A");
assume always: var("d") > 0;
check reach <= 1: active("Root.B");
'''
    core = build_bmc_core_formula(BmcEngine(model).prepare(query))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('remainder_guard', (
        UnsatConstraint('domain', (core.domain_formula,)),
        UnsatConstraint('initial', (core.initial_formula,)),
        UnsatConstraint('transitions', (core.transition_formula,)),
        UnsatConstraint('environment', (core.environment_formula,)),
        UnsatConstraint('objective', (prop.objective_formula,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert any(node.inference_kind == 'remainder_lower' for node in report.proof.nodes)


@pytest.mark.parametrize('guard,kind', [('sqrt(x) < 0.0', 'root_nonnegative'),
                                       ('x ** 2 < 0.0', 'even_power')])
def test_root_and_power_guards_cannot_reach_target(guard, kind):
    model = load_state_machine_from_text('''
def float x = 0.0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B : if [%s];
}
''' % guard)
    core = build_bmc_core_formula(BmcEngine(model).prepare('''
init state("Root.A");
assume always: var("x") >= 0.0;
check reach <= 1: active("Root.B");
'''))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('power_guard', (
        UnsatConstraint('domain', (core.domain_formula,)),
        UnsatConstraint('initial', (core.initial_formula,)),
        UnsatConstraint('transitions', (core.transition_formula,)),
        UnsatConstraint('environment', (core.environment_formula,)),
        UnsatConstraint('objective', (prop.objective_formula,)),
    )), timeout_ms=5000)
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert any(node.inference_kind == kind for node in report.proof.nodes)


@pytest.mark.parametrize('declarations,assumptions,objective', [
    ('def int x = 0;', '', 'x * x == 2'),
    ('def int x = 0; def int y = 0;',
     'assume always: var("x") > 1; assume always: var("y") > 1;', 'x * y < 2'),
    ('def int x = 5; def int d = 2;',
     'assume always: var("x") == 5; assume always: var("d") == 2;', 'x / d != 2'),
    ('def int x = -5; def int d = 2;',
     'assume always: var("x") == -5; assume always: var("d") == 2;', 'x / d != -3'),
])
def test_actual_nonlinear_fbmcq_formulas_have_complete_interval_proofs(declarations, assumptions, objective):
    model = load_state_machine_from_text(declarations + ' state Root { state A; [*] -> A; }')
    query = 'init state("Root.A"); %s check reach <= 1: %s;' % (assumptions, objective)
    core = build_bmc_core_formula(BmcEngine(model).prepare(query))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('nonlinear_query', (
        UnsatConstraint('domain', (core.domain_formula,)),
        UnsatConstraint('initial', (core.initial_formula,)),
        UnsatConstraint('transitions', (core.transition_formula,)),
        UnsatConstraint('environment', (core.environment_formula,)),
        UnsatConstraint('objective', (prop.objective_formula,)),
    )), timeout_ms=5000)
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()


@pytest.mark.parametrize('name,source,query', [
    ('false_guard',
     'def int x=0; state Root { state A; state B; [*]->A; A->B: if [x<0]; }',
     'init state("Root.A"); check reach <= 1: active("Root.B");'),
    ('true_guard',
     'def int x=0; state Root { state A; state B; [*]->A; A->B: if [x>=0]; }',
     'init state("Root.A"); check reach <= 1: x<0;'),
    ('increment',
     'def int x=0; state Root { state A { during { x=x+1; } } [*]->A; }',
     'init state("Root.A") havoc { x } where x>=0; check reach <= 3: x<0;'),
    ('conditional_update',
     'def int x=0; state Root { state A { during { x=(x>=0)?x+1:0; } } [*]->A; }',
     'init state("Root.A"); check reach <= 2: x<0;'),
    ('priority',
     'state Root { event Go; state A; state B; state C; [*]->A; A->B: Go; A->C: Go; }',
     'init state("Root.A"); assume event("Root.Go",0)==true; check reach <= 1: active("Root.C");'),
])
def test_control_flow_encodings_have_complete_proofs(name, source, query):
    core = build_bmc_core_formula(BmcEngine(load_state_machine_from_text(source)).prepare(query))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery(name, tuple(UnsatConstraint(key, (expression,)) for key, expression in (
        ('domain', core.domain_formula), ('initial', core.initial_formula),
        ('transitions', core.transition_formula), ('environment', core.environment_formula),
        ('objective', prop.objective_formula),
    ))))
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()


def test_guard_after_prefix_effect_is_proved_at_its_actual_anchor():
    import z3

    model = load_state_machine_from_text('''
def int x=0;
state Root {
    state A; pseudo state Route; state B; state C;
    [*]->A;
    A->Route effect { x=x+2; }
    Route->B: if [x>=2];
    Route->C;
}
''')
    core = build_bmc_core_formula(BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 1: active("Root.B");'))
    case = next(item for item in core.steps[0].case_relations if item.case.target_state_path == 'Root.B')
    guard = next(iter(case.guard_terms.values()))
    report = explain_unsat(UnsatQuery('anchored_guard', (
        UnsatConstraint('initial', (core.initial_formula,)),
        UnsatConstraint('negated_guard', (z3.Not(guard),)),
    )))
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
