"""Source construction is captured while the real BMC relation is built."""

from pathlib import Path
from dataclasses import replace

import pytest
import z3

from pyfcstm.bmc import BmcOptions, compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_file, load_state_machine_from_text


pytestmark = pytest.mark.unittest
FIXTURES = Path(__file__).parent / 'fixtures' / 'construction'


def test_recording_is_explicit_and_does_not_change_the_solver_formula():
    model = load_state_machine_from_text('''
        def int x = 0;
        state Root { enter { x = x + 1; } }
    ''')
    query = 'init cold havoc *; check reach <= 2: x > 0;'
    plain = compile_bmc_query(model, query)
    recorded = compile_bmc_query(model, query, options=BmcOptions(record_construction=True))
    assert z3.eq(plain.solve_formula, recorded.solve_formula)
    assert all(case.construction is None
               for step in plain.core.steps for case in step.case_relations)
    assert all(case.construction is not None
               for step in recorded.core.steps for case in step.case_relations)
    assert solve_bmc_property(plain).property_satisfied == solve_bmc_property(recorded).property_satisfied


def test_full_editor_retains_trim_sources_versions_and_formula_bindings():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_file(str(FIXTURES / 'dose_editor.fcstm'))
    formula = compile_bmc_query(
        model, (FIXTURES / 'dose_editor.fbmcq').read_text(),
        options=BmcOptions(record_construction=True),
    )
    report = get_bmc_construction(formula.core, ('transition.step.0002',))
    assert report.group_ids == ('transition.step.0002',)
    assert {case.step_index for case in report.cases} == {2}
    trim_actions = [action for case in report.cases for action in case.actions
                    if action.block.owner_state_path.endswith('.Trim')]
    assert trim_actions
    for action in trim_actions:
        writes = [value for value in action.execution.values if value.kind == 'assignment']
        assert [value.name for value in writes] == ['refund', 'proposal', 'margin']
        assert writes[1].reads[-1] == ('refund', writes[0].identifier)
        assert writes[2].reads[-1] == ('refund', writes[0].identifier)
        assert action.sources[0].span is not None
        assert action.sources[0].kind == 'fcstm'
        assert action.execution.check().status == 'verified'
    assert report.check().status == 'verified'


def test_construction_request_on_unrecorded_formula_reports_missing_evidence():
    from pyfcstm.bmc.construction import get_bmc_construction

    formula = compile_bmc_query(load_state_machine_from_text('state Root;'),
                                'check reach <= 1: active("Root");')
    with pytest.raises(ValueError, match='record_construction'):
        get_bmc_construction(formula.core, ('transition.step.0000',))


def test_repeated_named_actions_keep_invocation_local_versions_and_hot_start_has_no_history():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        def int x = 0;
        state Root {
            state Library { enter Shared { temporary = x * 2; x = temporary + 1; } }
            state A {
                enter FirstRef ref /Library.Shared;
                enter SecondRef ref /Library.Shared;
            }
            [*] -> A;
        }
    ''')
    cold = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                             options=BmcOptions(record_construction=True))
    report = get_bmc_construction(cold.core, ('transition.step.0000',))
    assert report.check(timeout_ms=10000).status == 'verified'
    calls = next(case.actions for case in report.cases if len(case.actions) == 2)
    first, second = calls
    assert first.index != second.index
    assert first.block.named_ref != second.block.named_ref
    assert first.execution.values[-1].source is second.execution.values[-1].source
    assert first.execution is not second.execution
    assert z3.eq(second.before['x'], first.after['x'])
    assert z3.is_true(z3.simplify(second.after['x'] == first.before['x'] * 4 + 3))
    assert 'temporary' not in first.after
    assert 'temporary' not in second.before
    hot = compile_bmc_query(model, 'init state("Root.A") havoc *; check reach <= 1: true;',
                            options=BmcOptions(record_construction=True))
    hot_report = get_bmc_construction(hot.core, ('transition.step.0000',))
    # Macro cases describe candidate behaviors. The SAT witness decides
    # which case applies; a hot start must not execute the cold-entry calls.
    result = solve_bmc_property(hot)
    assert result.property_satisfied is True
    assert hot_report.check().status == 'verified'
    solver = z3.Solver()
    solver.add(hot.solve_formula, hot.core.symbols.frame_vars[1]['x'] != hot.core.symbols.frame_vars[0]['x'])
    assert solver.check() == z3.unsat


def test_report_binding_check_validates_budget_and_exhaustion(monkeypatch):
    import time
    from pyfcstm.bmc.construction import get_bmc_construction

    formula = compile_bmc_query(load_state_machine_from_text('state Root;'),
                                'check reach <= 1: true;', options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    with pytest.raises(ValueError, match='positive integer'):
        report.check(timeout_ms=0)
    ticks = iter((0.0, 1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    assert report.check(timeout_ms=1).status == 'unknown'


def test_selected_core_refinement_keeps_guards_and_does_not_add_other_groups():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.solver import UnsatConstraint, UnsatQuery

    model = load_state_machine_from_text('''
        def int x = 0;
        state Root { enter { x = x + 1; } }
    ''')
    formula = compile_bmc_query(model, '''
        init cold havoc *;
        assume at 0: x > 0;
        assume at 1: x <= 0;
        check reach <= 1: true;
    ''', options=BmcOptions(record_construction=True))
    core = formula.core
    ids = ('initial.target', 'transition.step.0000',
           'assumption.0000.frame.0000', 'assumption.0001.frame.0001')
    report = get_bmc_construction(core, ids)
    query = UnsatQuery('scenario', tuple(UnsatConstraint(group.stable_id, group.expressions, group)
                                       for group in report.groups))
    refined = report.refine(query, timeout_ms=10000)
    assert refined.equivalence.status == 'verified'
    assert refined.explanation.core_check == 'verified'
    assert set(item.parent_id for item in refined.units) == set(ids)
    assert any(z3.is_implies(unit.expression) for unit in refined.units)
    assert refined.explanation.derivation_status == 'not_attempted'
    # Caller-supplied groups must match the original compiled formulas.
    wrong = replace(query, constraints=(replace(query.constraints[0], expressions=(z3.BoolVal(True),)),
                                       *query.constraints[1:]))
    with pytest.raises(ValueError, match='binding'):
        report.refine(wrong)


def test_trim_text_exposes_local_reads_before_expanded_formulas(text_aligner):
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        param int quantum = 0;
        def int refund = 0;
        def int proposal = 0;
        def int margin = 0;
        state Root { enter {
            refund = quantum - margin;
            proposal = proposal - refund;
            margin = margin + refund;
        } }
    ''')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    action = next(action for case in report.cases for action in case.actions)
    actual = '\n'.join(action.text_lines(formula.core.symbols.names))
    text_aligner.assert_equal(expect='''
Action 0: Root state_enter
  refund = quantum - margin; [source location unavailable]
    reads: quantum#3, margin#2
    refund#4 := quantum@param - margin@0
    simplified: quantum@param + -1*margin@0
  proposal = proposal - refund; [source location unavailable]
    reads: proposal#1, refund#4
    proposal#5 := proposal@0 - (quantum@param - margin@0)
    simplified: proposal@0 + -1*quantum@param + margin@0
  margin = margin + refund; [source location unavailable]
    reads: margin#2, refund#4
    margin#6 := margin@0 + quantum@param - margin@0
    simplified: quantum@param
'''.strip(), actual=actual)


def test_conditional_identity_write_text_keeps_scope_and_preservation(text_aligner):
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('def int x = 0; state Root { enter { if [x > 0] { x = x; } } }')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    action = next(action for case in report.cases for action in case.actions)
    text_aligner.assert_equal(expect='''
Action 0: Root state_enter
  x = x; [source location unavailable]
    reads: x#0
    when: And(0 < x@0)
    x#1 := x@0
  Merge x: ordered branches, otherwise preserve incoming value.
    reads: x#0
    x#2 := If(0 < x@0, x@0, x@0)
    simplified: x@0
'''.strip(), actual='\n'.join(action.text_lines(formula.core.symbols.names)))


@pytest.mark.parametrize('name', ['pool', 'dose_editor'])
def test_complex_models_bind_all_public_initial_targets(name):
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.bmc.domain import build_bmc_domain

    model = load_state_machine_from_file(str(FIXTURES / (name + '.fcstm')))
    domain = build_bmc_domain(model, 1)
    targets = ['cold', 'terminated'] + ['state("%s")' % state.path for state in domain.states if state.id >= 0]
    for target in targets:
        formula = compile_bmc_query(
            model, 'init %s havoc *; check reach <= 2: true;' % target,
            options=BmcOptions(record_construction=True),
        )
        report = get_bmc_construction(formula.core, ('transition.step.0000', 'transition.step.0001'))
        checked = report.check()
        assert checked.status == 'verified', (target, checked)
        assert all(case.query is formula.core.context.query for case in report.cases)


def test_pool_repeated_cycles_keep_source_shared_and_frame_values_distinct():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_file(str(FIXTURES / 'pool.fcstm'))
    formula = compile_bmc_query(
        model, 'init state("Pool.Intake") havoc *; check reach <= 8: true;',
        options=BmcOptions(record_construction=True),
    )
    report = get_bmc_construction(formula.core, tuple('transition.step.%04d' % i for i in range(8)))
    assert report.check(timeout_ms=10000).status == 'verified'
    holds = [(case.step_index, action) for case in report.cases for action in case.actions
             if action.block.owner_state_path == 'Pool.Transaction.Hold']
    first_frame, first = holds[0]
    last_frame, last = holds[-1]
    assert last_frame > first_frame
    first_write = next(value for value in first.execution.values if value.kind == 'assignment')
    last_write = next(value for value in last.execution.values if value.kind == 'assignment')
    assert first_write.source is last_write.source
    assert first.execution is not last.execution
    assert not z3.eq(first_write.expression, last_write.expression)
    assert first.sources == last.sources
    assert solve_bmc_property(formula).property_satisfied is True


def test_sliced_actions_bind_original_source_occurrences():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        def int x = 0; def int unused = 0;
        state Root { enter {
            unused = unused + 1;
            if [x > 0] { x = x + 1; }
        } }
    ''')
    formula = compile_bmc_query(model, 'init cold; check reach <= 1: x > 0;',
                                options=BmcOptions(cone_slicing=True, record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    assert formula.core.cone_slice.dropped_variables == ('unused',)
    assert report.check().status == 'verified'
    action = next(action for case in report.cases for action in case.actions)
    write = next(value for value in action.execution.values if value.kind == 'assignment')
    assert action.source_paths[write.path] == (1, 0, 0)


def test_binding_checker_rejects_wrong_case_scope_guard_and_source():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.solver.domain import DomainConstraint

    model = load_state_machine_from_file(str(FIXTURES / 'dose_editor.fcstm'))
    formula = compile_bmc_query(model, (FIXTURES / 'dose_editor.fbmcq').read_text(),
                                options=BmcOptions(record_construction=True))
    all_records = get_bmc_construction(formula.core, ('transition.step.0002',))
    index = next(i for i, case in enumerate(all_records.cases)
                 if case.guards and any(action.execution and action.sources for action in case.actions))
    case = all_records.cases[index]
    guard = case.guards[0]
    action_index = next(i for i, action in enumerate(case.actions) if action.sources)
    def changed_action(**changes):
        return replace(case, actions=tuple(replace(item, **changes) if i == action_index else item
                                           for i, item in enumerate(case.actions)))

    changes = [
        replace(case, query=object()),
        replace(case, step_index=99),
        replace(case, expression=z3.BoolVal(True)),
        replace(case, antecedent=z3.BoolVal(True)),
        replace(case, before={}),
        replace(case, actions=()),
        replace(case, guards=()),
        replace(case, guards=(replace(guard, environment={}), *case.guards[1:])),
        replace(case, guards=(replace(guard, expression=z3.BoolVal(False)), *case.guards[1:])),
        replace(case, guards=(replace(guard, subexpressions=()), *case.guards[1:])),
        replace(case, guards=(replace(guard, definedness=(DomainConstraint(z3.BoolVal(False)),)),
                             *case.guards[1:])),
        changed_action(index=99),
        changed_action(before={}),
        changed_action(execution=None),
        changed_action(source_paths={}),
        changed_action(sources=()),
        changed_action(after={}),
    ]
    for changed in changes:
        report = replace(all_records, cases=tuple(changed if i == index else item
                                                 for i, item in enumerate(all_records.cases)))
        assert report.check().status == 'invalid'
    assert replace(all_records, cases=()).check().status == 'invalid'
    assert replace(all_records, groups=()).check().status == 'invalid'


def test_binding_checker_rejects_lost_nested_sources_and_unchecked_local_reads():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        def int x = 0;
        state Root { enter { if [x > 0] { x = x + 1; } } }
    ''')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    case_index = next(i for i, case in enumerate(report.cases) if case.actions)
    case = report.cases[case_index]
    action = case.actions[0]
    graph = action.execution
    assignment = next(value for value in graph.values if value.kind == 'assignment')
    incorrect = replace(graph, values=tuple(
        replace(value, subexpressions=()) if value is assignment else value for value in graph.values
    ))
    missing_merge_source = {path: original for path, original in action.source_paths.items()
                            if path != (0,)}
    for changed_action in (
        replace(action, execution=incorrect),
        replace(action, source_paths=missing_merge_source),
    ):
        changed_case = replace(case, actions=(changed_action,))
        changed_report = replace(report, cases=tuple(changed_case if i == case_index else item
                                                    for i, item in enumerate(report.cases)))
        assert changed_report.check().status == 'invalid'


def test_updated_action_records_cannot_be_attached_to_an_older_compiled_relation():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.solver.operation import execute_operations_domain, parse_operations

    model = load_state_machine_from_text('def int x = 0; state Root { enter { x = x + 1; } }')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    index = next(i for i, case in enumerate(report.cases) if case.actions)
    case = report.cases[index]
    action = case.actions[0]
    # Rebuilding valid operation evidence after editing the source does not
    # update the SMT relation already compiled from the previous source.
    action.block.operations[0].expr = parse_operations('x = x + 2;', ['x'])[0].expr
    execution = execute_operations_domain(list(action.block.operations), dict(action.before),
                                          record_construction=True)
    updated = replace(action, after=execution.env, execution=execution.construction)
    changed_case = replace(case, actions=(updated,))
    changed = replace(report, cases=tuple(changed_case if i == index else item
                                         for i, item in enumerate(report.cases)))
    assert changed.check().reason == 'post-state binding mismatch'


def test_updated_guard_records_cannot_be_attached_to_an_older_compiled_relation():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.solver.domain import translate_expr_domain

    model = load_state_machine_from_text('''
        def int x = 0;
        state Root { state A; [*] -> A; A -> A : if [x > 0]; }
    ''')
    formula = compile_bmc_query(model, 'init state("Root.A") havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    index = next(i for i, case in enumerate(report.cases) if case.guards)
    case = report.cases[index]
    guard = case.guards[0]
    guard.requirement.expr.op = '>='
    translated = translate_expr_domain(guard.requirement.expr, dict(guard.environment), record_construction=True)
    updated = replace(guard, expression=translated.z3_expr, subexpressions=translated.construction)
    changed_case = replace(case, guards=(updated, *case.guards[1:]))
    changed = replace(report, cases=tuple(changed_case if i == index else item
                                         for i, item in enumerate(report.cases)))
    assert changed.check().reason == 'guard formula binding mismatch'


def test_abstract_hook_evidence_cannot_introduce_modeled_writes():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('def int x = 0; state Root { enter abstract Observe; }')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('transition.step.0000',))
    index = next(i for i, case in enumerate(report.cases) if case.actions)
    case = report.cases[index]
    action = replace(case.actions[0], after={'x': case.actions[0].before['x'] + 1})
    changed_case = replace(case, actions=(action,))
    changed = replace(report, cases=tuple(changed_case if i == index else item
                                         for i, item in enumerate(report.cases)))
    assert changed.check().reason == 'abstract action changes values'


def test_guard_check_expiry_does_not_publish_success(monkeypatch):
    import time
    from itertools import chain, repeat
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        def int x = 0;
        state Root { state A; [*] -> A; A -> A : if [x > 0]; }
    ''')
    formula = compile_bmc_query(model, 'init state("Root.A") havoc *; check reach <= 1: true;',
                                options=BmcOptions(record_construction=True))
    index = next(i for i, case in enumerate(formula.core.steps[0].case_relations)
                 if case.construction.guards)
    report = get_bmc_construction(formula.core, ('transition.case.0000.%04d' % index,))
    ticks = chain((0.0, 0.0), repeat(1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    assert report.check(timeout_ms=1).status == 'unknown'


def test_recorded_inputs_parameters_locals_and_abstract_hook():
    from pyfcstm.bmc.construction import get_bmc_construction

    model = load_state_machine_from_text('''
        input int request;
        param int gain = 1;
        def int x = 0;
        state Root {
            enter abstract Observe;
            during { temporary = request * gain; x = x + temporary; }
        }
    ''')
    formula = compile_bmc_query(model, 'init cold havoc *; check reach <= 3: x > 0;',
                                options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, tuple('transition.step.%04d' % i for i in range(3)))
    assert report.check().status == 'verified'
    calls = [action for case in report.cases for action in case.actions if action.block.is_abstract]
    assert calls
    assert calls[0].text_lines() == (
        'Action 0: Root state_enter', '  Abstract hook: recorded call, no modeled writes.',
    )
    recorded = [case for case in report.cases if any(action.execution for action in case.actions)]
    assert z3.eq(recorded[0].before['gain'], recorded[-1].before['gain'])
    assert not z3.eq(recorded[0].before['request'], recorded[-1].before['request'])
    assert all('temporary' not in action.after for case in report.cases for action in case.actions)


def test_source_selection_validation_and_exact_case_selection():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.bmc.errors import BmcBuildError

    with pytest.raises(BmcBuildError, match='record_construction must be bool'):
        BmcOptions(record_construction=1)
    assert BmcOptions(record_construction=True).to_canonical()['record_construction'] is True
    formula = compile_bmc_query(load_state_machine_from_text('state Root;'),
                                'check reach <= 1: true;', options=BmcOptions(record_construction=True))
    for ids in (('missing',), ('initial.target', 'initial.target')):
        with pytest.raises(ValueError, match='unique existing source IDs'):
            get_bmc_construction(formula.core, ids)
    report = get_bmc_construction(formula.core, ('transition.case.0000.0000',))
    assert len(report.cases) == 1
    assert report.check().status == 'verified'


@pytest.fixture
def one_group_construction():
    from pyfcstm.bmc.construction import get_bmc_construction
    from pyfcstm.solver import UnsatConstraint, UnsatQuery

    formula = compile_bmc_query(load_state_machine_from_text('state Root;'),
                                'check reach <= 1: true;', options=BmcOptions(record_construction=True))
    report = get_bmc_construction(formula.core, ('initial.target',))
    group = report.groups[0]
    query = UnsatQuery('selected', (UnsatConstraint(group.stable_id, group.expressions, group),))
    return report, query


def test_refinement_validates_types_and_preserves_sat_and_fixed_background(one_group_construction):
    report, query = one_group_construction
    with pytest.raises(TypeError, match='UnsatQuery'):
        report.refine(object())
    with pytest.raises(TypeError, match='Boolean'):
        report.refine(query, minimize=1)
    with pytest.raises(ValueError, match='positive integer'):
        report.refine(query, timeout_ms=0)
    with pytest.raises(ValueError, match='source-group binding mismatch'):
        replace(report, groups=()).refine(query)
    result = report.refine(query)
    assert result.equivalence.status == 'verified'
    assert result.explanation.solver_status == 'sat'
    background_only = replace(query, constraints=(), background=query.constraints)
    result = report.refine(background_only)
    assert result.query.background is background_only.background
    assert result.units == ()
    assert result.explanation.solver_status == 'sat'


@pytest.mark.parametrize('deadline_at', [0, 1])
def test_refinement_shared_budget_expiry_does_not_publish_unchecked_core(
    one_group_construction, monkeypatch, deadline_at,
):
    from pyfcstm.solver.budget import SolveBudget

    report, query = one_group_construction
    calls = []

    def remaining(self):
        calls.append(1)
        return 100 if len(calls) <= deadline_at else None

    # Inject deadline exhaustion to check the public refinement contract at
    # both boundaries without depending on the host's scheduling latency.
    monkeypatch.setattr(SolveBudget, 'remaining_ms', remaining)
    result = report.refine(query, timeout_ms=100)
    assert result.explanation is None
    assert result.equivalence.status == ('unknown' if deadline_at == 0 else 'verified')


def test_refinement_unknown_equivalence_never_becomes_verified(one_group_construction, monkeypatch):
    report, query = one_group_construction
    # Instrument the solver boundary to exercise UNKNOWN independent of
    # machine speed; no production invariant is inferred from this injection.
    monkeypatch.setattr(z3.Solver, 'check', lambda self, *args: z3.unknown)
    result = report.refine(query)
    assert result.equivalence.status == 'unknown'
    assert result.explanation is None
