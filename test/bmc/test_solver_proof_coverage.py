"""Actual BMC formulas remain explainable by the generic proof subsystem."""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.proof import UnsatReport

pytestmark = pytest.mark.unittest


def test_three_event_cardinality_has_a_complete_native_proof(text_aligner):
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
    _check_reading_levels(report, text_aligner)
    assert any(node.cardinality is not None for node in report.proof.nodes)


def test_remainder_guard_cannot_reach_target_with_positive_divisor(text_aligner):
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
    _check_reading_levels(report, text_aligner)
    assert any(node.inference_kind == 'remainder_lower' for node in report.proof.nodes)


@pytest.mark.parametrize('guard,kind', [('sqrt(x) < 0.0', 'root_nonnegative'),
                                       ('x ** 2 < 0.0', 'even_power')])
def test_root_and_power_guards_cannot_reach_target(guard, kind, text_aligner):
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
    _check_reading_levels(report, text_aligner)
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
def test_actual_nonlinear_fbmcq_formulas_have_complete_interval_proofs(declarations, assumptions, objective, text_aligner):
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
    _check_reading_levels(report, text_aligner)


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
def test_control_flow_encodings_have_complete_proofs(name, source, query, text_aligner):
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
    _check_reading_levels(report, text_aligner)


def test_guard_after_prefix_effect_is_proved_at_its_actual_anchor(text_aligner):
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
    _check_reading_levels(report, text_aligner)



def test_shared_square_equality_is_explained_in_actual_fbmcq(text_aligner):
    model = load_state_machine_from_text(
        'def float x=0.0; def float y=0.0; state Root { state A; [*]->A; }')
    core = build_bmc_core_formula(BmcEngine(model).prepare(
        'init state("Root.A") havoc { x, y }; check reach <= 1: x*x==2 && y*y==3 && x==y;'))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('shared_square', tuple(UnsatConstraint(key, (expression,))
                          for key, expression in (
        ('domain', core.domain_formula), ('initial', core.initial_formula),
        ('transitions', core.transition_formula), ('environment', core.environment_formula),
        ('objective', prop.objective_formula),
    ))))
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    _check_reading_levels(report, text_aligner)
    assert any(step.substitutions for node in report.proof.nodes if node.interval is not None
               for step in node.interval.steps)


def _check_reading_levels(report, text_aligner):
    """All views of real BMC encodings survive offline loading unchanged."""
    before = report.to_canonical()
    restored = UnsatReport.from_canonical(before)
    for language in ('en', 'zh'):
        for detail in ('brief', 'standard', 'detailed'):
            text_aligner.assert_equal(report.reading.to_text(language, detail),
                                      restored.reading.to_text(language, detail))
    assert report.to_canonical() == before


@pytest.mark.parametrize('name,kind,predicate', [
    ('integer_product', 'int', 'x>1 && y>1 && x*y==5'),
    ('difference_squares', 'float', 'x>y && y>=0 && x*x<=y*y'),
    ('cubic_order', 'float', 'x>y && x*x*x<=y*y*y'),
    ('quartic', 'float', 'x*x*x*x+1==0'),
    ('square_difference', 'float', 'x>=0 && y>=0 && x*x+y*y<2*x*y'),
    ('parity', 'int', 'x%2==0 && (x+1)%2==0'),
    ('sqrt_monotone', 'float', 'x>y && y>=0 && sqrt(x)<=sqrt(y)'),
    ('sqrt_sum', 'float', 'x>=0 && y>=0 && sqrt(x+y)>sqrt(x)+sqrt(y)'),
    ('power_zero', 'int', 'x>0 && x**0!=1'),
    ('variable_power', 'int', 'x>1 && y>1 && x**y<=1'),
])
def test_composed_arithmetic_proofs_explain_every_native_lemma(name, kind, predicate, text_aligner):
    """The public BMC compiler exercises arithmetic combinations, not hand-built proof nodes."""
    model = load_state_machine_from_text(
        'def %s x=0; def %s y=0; state Root { state A; [*]->A; }' % (kind, kind))
    core = build_bmc_core_formula(BmcEngine(model).prepare(
        'init state("Root.A") havoc {x,y}; check reach <= 1: %s;' % predicate))
    prop = compile_bmc_property(core)
    query = UnsatQuery(name, tuple(UnsatConstraint(key, (expression,)) for key, expression in (
        ('domain', core.domain_formula), ('initial', core.initial_formula),
        ('transitions', core.transition_formula), ('environment', core.environment_formula),
        ('objective', prop.objective_formula),
    )))
    # This is a semantic coverage test, not a wall-clock benchmark. Coverage
    # instrumentation and parallel CI workers must not consume its deadline.
    report = explain_unsat(query, timeout_ms=30000)
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    assert report.gaps == ()
    assert report.reading_status == 'complete'
    _check_reading_levels(report, text_aligner)


@pytest.mark.parametrize('name,source,assumptions', [
    ('shifted_power_transition',
     '''def float x=0; def float y=0;
        state Root { state A; state Mid; state Bad; [*]->A;
          A->Mid effect { x=x+1; y=y+1; }
          Mid->Bad: if [x**5 <= y**5]; }''',
     'assume at 0: x>y;'),
    ('root_product_transition',
     '''def float x=0; def float y=0; def float r=0; def float s=0; def float t=0;
        state Root { state A; state Mid; state Bad; [*]->A;
          A->Mid effect { r=sqrt(x); s=sqrt(y); t=sqrt(x*y); }
          Mid->Bad: if [t != r*s]; }''',
     'assume at 0: x>=0; assume at 0: y>=0;'),
])
def test_compositional_proofs_follow_real_updates_across_frames(name, source, assumptions, text_aligner):
    model = load_state_machine_from_text(source)
    core = build_bmc_core_formula(BmcEngine(model).prepare(
        'init state("Root.A") havoc {x,y}; %s check reach <= 2: active("Root.Bad");' % assumptions))
    objective = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery(name, tuple(UnsatConstraint(key, (expression,)) for key, expression in (
        ('domain', core.domain_formula), ('initial', core.initial_formula),
        ('transitions', core.transition_formula), ('environment', core.environment_formula),
        ('objective', objective.objective_formula),
    ))), timeout_ms=120000)
    assert report.solver_status == 'unsat'
    assert report.stop_reason is None
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    _check_reading_levels(report, text_aligner)


def test_fbmcq_only_root_contradiction_uses_compositional_evidence(text_aligner):
    model = load_state_machine_from_text(
        'def float x=0; def float y=0; state Root { state A; [*]->A; }')
    core = build_bmc_core_formula(BmcEngine(model).prepare('''
        init state("Root.A") havoc {x,y};
        assume at 0: x>=0;
        assume at 0: y>=0;
        assume at 0: sqrt(x*y)!=sqrt(x)*sqrt(y);
        check reach <= 1: active("Root.A");
    '''))
    objective = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('query_root_conflict', tuple(
        UnsatConstraint(key, (expression,)) for key, expression in (
            ('domain', core.domain_formula), ('initial', core.initial_formula),
            ('environment', core.environment_formula), ('objective', objective.objective_formula),
        ))), timeout_ms=120000)
    assert report.solver_status == 'unsat'
    assert report.stop_reason is None
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    _check_reading_levels(report, text_aligner)
