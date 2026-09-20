"""Construction evidence follows actual writes and conditional execution."""

import pytest
import z3
from dataclasses import replace

from pyfcstm.solver.operation import execute_operations_domain, parse_operations


pytestmark = pytest.mark.unittest


def test_construction_check_uses_one_validated_total_budget():
    graph = execute_operations_domain(
        parse_operations('x = (x > 0) ? x + 1 : x - 1;', ['x']),
        {'x': z3.Int('x')}, record_construction=True,
    ).construction
    assert graph.check(timeout_ms=10000).status == 'verified'
    with pytest.raises(ValueError, match='positive integer'):
        graph.check(timeout_ms=0)


def test_construction_check_reports_expired_time_without_verifying(monkeypatch):
    import time

    graph = execute_operations_domain(parse_operations('x = x + 1;', ['x']),
                                      {'x': z3.Int('x')}, record_construction=True).construction
    # External clock advancement simulates elapsed time, without altering
    # construction records or the checker's consistency rules.
    ticks = iter((0.0, 1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    result = graph.check(timeout_ms=1)
    assert result.status == 'unknown'
    assert result.reason == 'budget exhausted'


@pytest.mark.parametrize('source,ticks_before_expiry', [
    ('x = x + 1;', 3),
    ('if [x > 0] {}', 3),
    ('if [x > 0] {}', 4),
])
def test_binding_checks_do_not_publish_success_after_elapsed_budget(source, ticks_before_expiry, monkeypatch):
    import time
    from itertools import chain, repeat

    graph = execute_operations_domain(parse_operations(source, ['x']), {'x': z3.Int('x')},
                                      record_construction=True).construction
    # Let the public check enter and then advance its external monotonic clock.
    # Cover deadlines crossing both assignment and source-branch checks.
    ticks = chain(repeat(0.0, ticks_before_expiry), repeat(1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    assert graph.check(timeout_ms=1).status == 'unknown'


def test_assignment_keeps_distinct_source_subexpressions():
    statements = parse_operations('x = x + x * 2;', ['x'])
    x = z3.Int('x')
    graph = execute_operations_domain(statements, {'x': x},
                                      record_construction=True).construction
    write = graph.values[-1]
    parts = {part.path: part for part in write.subexpressions}
    assert set(parts) == {(), ('x',), ('y',), ('y', 'x'), ('y', 'y')}
    assert parts[()].source is statements[0].expr
    assert parts[('x',)].source is statements[0].expr.x
    assert parts[('y', 'x')].source is statements[0].expr.y.x
    assert z3.eq(parts[('x',)].expression, parts[('y', 'x')].expression)
    assert parts[('x',)].path != parts[('y', 'x')].path
    assert z3.eq(parts[()].expression, write.expression)


def test_expression_recording_retains_short_circuit_scope_and_definedness():
    from pyfcstm.solver.domain import translate_expr_domain

    source = parse_operations('x = (y > 0) ? x / y : x;', ['x', 'y'])[0].expr
    env = dict(zip(('x', 'y'), z3.Ints('x y')))
    plain = translate_expr_domain(source, env)
    recorded = translate_expr_domain(source, env, record_construction=True)
    assert plain.construction == ()
    assert z3.eq(plain.z3_expr, recorded.z3_expr)
    division = next(part for part in recorded.construction if part.path == ('if_true',))
    assert division.source is source.if_true
    assert z3.eq(division.path_conditions[-1], z3.IntVal(0) < env['y'])
    assert len(division.definedness_constraints) == 1
    assert z3.eq(division.definedness_constraints[0].constraint, env['y'] != 0)
    pruned = translate_expr_domain(source, env, assumptions=(env['y'] <= 0,),
                                   record_construction=True)
    assert all(part.path[:1] != ('if_true',) for part in pruned.construction)
    assert {check.status for check in pruned.feasibility_checks} == {'sat', 'unsat'}


def test_expression_translation_shared_budget_exhaustion_keeps_both_branches(monkeypatch):
    import time
    from pyfcstm.solver.budget import SolveBudget
    from pyfcstm.solver.domain import translate_expr_domain

    source = parse_operations('x = (x > 0) ? x + 1 : x - 1;', ['x'])[0].expr
    ticks = iter((0.0, 1.0, 1.0))
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    result = translate_expr_domain(source, {'x': z3.Int('x')}, budget=SolveBudget(1),
                                   record_construction=True)
    assert result.failure is None
    assert tuple(check.status for check in result.feasibility_checks) == ('unknown', 'unknown')
    assert {part.path[0] for part in result.construction if part.path} == {'cond', 'if_true', 'if_false'}


def test_expression_recording_validates_option_and_retains_translation_failure():
    from pyfcstm.solver.domain import translate_expr_domain

    source = parse_operations('x = sin(x);', ['x'])[0].expr
    with pytest.raises(TypeError, match='record_construction must be bool'):
        translate_expr_domain(source, {'x': z3.Int('x')}, record_construction=1)
    result = translate_expr_domain(source, {'x': z3.Int('x')}, record_construction=True)
    assert result.failure is not None
    assert result.construction[-1].failure is result.failure
    assert result.construction[-1].expression is None


@pytest.mark.parametrize('expression', [
    '-x + sqrt(y)',
    'x % y',
    '(x > 0 && y > 0) ? x : y',
    '(x > 0 || y > 0) ? x : y',
    '(x > 0 && false) ? x : y',
])
@pytest.mark.parametrize('prune', [False, True])
def test_recording_preserves_supported_native_expression_operators(expression, prune):
    from pyfcstm.solver.domain import translate_expr_domain

    source = parse_operations('x = %s;' % expression, ['x', 'y'])[0].expr
    env = dict(zip(('x', 'y'), z3.Ints('x y')))
    plain = translate_expr_domain(source, env, prune_unreachable=prune)
    recorded = translate_expr_domain(source, env, record_construction=True, prune_unreachable=prune)
    assert plain.failure is None
    assert recorded.failure is None
    assert z3.eq(plain.z3_expr, recorded.z3_expr)
    assert z3.eq(recorded.construction[-1].expression, recorded.z3_expr)
    assert [item.constraint.sexpr() for item in recorded.definedness_constraints] == [
        item.constraint.sexpr() for item in plain.definedness_constraints
    ]


def test_assignment_reads_keep_versions_even_when_values_do_not_change():
    statements = parse_operations(
        'x = x; refund = quantum - margin; '
        'proposal = proposal - refund; margin = margin + refund;',
        ['x', 'refund', 'quantum', 'margin', 'proposal'],
    )
    env = dict(zip(['x', 'refund', 'quantum', 'margin', 'proposal'],
                   z3.Ints('x refund quantum margin proposal')))
    ordinary = execute_operations_domain(statements, env)
    assert ordinary.construction is None
    recorded = execute_operations_domain(statements, env, record_construction=True)
    trace = recorded.construction
    writes = [value for value in trace.values if value.kind == 'assignment']
    assert [value.name for value in writes] == ['x', 'refund', 'proposal', 'margin']
    assert writes[0].reads == (('x', trace.initial_versions['x']),)
    assert writes[0].identifier != trace.initial_versions['x']
    assert writes[2].reads == (('proposal', trace.initial_versions['proposal']),
                                ('refund', writes[1].identifier))
    assert writes[3].reads == (('margin', trace.initial_versions['margin']),
                                ('refund', writes[1].identifier))
    assert [value.source for value in writes] == statements
    assert [value.path for value in writes] == [(0,), (1,), (2,), (3,)]
    assert z3.is_true(z3.simplify(recorded.env['margin'] == env['quantum']))
    assert all(z3.eq(recorded.env[name], ordinary.env[name]) for name in env)
    assert trace.check().status == 'verified'


def test_nested_branches_keep_read_versions_and_implicit_preservation():
    statements = parse_operations('''
        if [x > 0] {
            x = x + 1;
            if [y > x] { y = x; }
        } else if [x < 0] { x = x - 1; }
        y = x + y;
    ''', ['x', 'y'])
    x, y = z3.Ints('x y')
    result = execute_operations_domain(statements, {'x': x, 'y': y},
                                       record_construction=True)
    trace = result.construction
    final_write = trace.values[-1]
    values = {item.identifier: item for item in trace.values}
    assert final_write.kind == 'assignment'
    assert all(values[identifier].kind == 'merge' for _, identifier in final_write.reads)
    assert {(branch.path, branch.kind) for branch in trace.branches} == {
        ((0, 0), 'if'), ((0, 0, 1, 0), 'if'), ((0, 1), 'elif'),
    }
    assert trace.check().status == 'verified'
    solver = z3.Solver()
    solver.add(x == 0, result.env['y'] != y)
    assert solver.check() == z3.unsat


def test_block_local_versions_are_retained_but_not_exported():
    x = z3.Int('x')
    result = execute_operations_domain(
        parse_operations('temporary = x * 2; x = temporary + 1;', ['x']),
        {'x': x}, record_construction=True,
    )
    assert tuple(result.construction.final_versions) == ('x',)
    writes = [item for item in result.construction.values if item.kind == 'assignment']
    assert writes[1].reads == (('temporary', writes[0].identifier),)
    assert result.construction.check().status == 'verified'


def test_binding_check_rejects_wrong_source_and_equal_valued_old_version():
    x = z3.Int('x')
    statements = parse_operations('x = x; x = x + 1;', ['x'])
    graph = execute_operations_domain(statements, {'x': x}, record_construction=True).construction
    last = graph.values[-1]
    stale = replace(last, reads=(('x', graph.initial_versions['x']),))
    wrong_source = replace(last, source=parse_operations('x = x + 1;', ['x'])[0])
    wrong_path = replace(last, path=(0,))
    for corrupted in (stale, wrong_source, wrong_path):
        changed = replace(graph, values=(*graph.values[:-1], corrupted))
        assert changed.check().status == 'invalid'


def test_binding_check_rejects_lost_branch_scope():
    x, y = z3.Ints('x y')
    statements = parse_operations('if [x > 0] { y = x; }', ['x', 'y'])
    graph = execute_operations_domain(statements, {'x': x, 'y': y},
                                      record_construction=True).construction
    index = next(i for i, value in enumerate(graph.values) if value.kind == 'assignment')
    changed = replace(graph, values=tuple(
        replace(value, path_conditions=()) if i == index else value
        for i, value in enumerate(graph.values)
    ))
    assert changed.check().status == 'invalid'
    changed = replace(graph, branches=(replace(graph.branches[0], selector=z3.BoolVal(True)),))
    assert changed.check().status == 'invalid'


@pytest.mark.parametrize('code,env', [
    ('if [x > 0] { x = x; } else if [x <= 0] { x = x + 1; } else { x = 0; }',
     {'x': z3.Int('x')}),
    ('if [x > 0] { x = x + 1; } else if [sin(x) > 0] { x = x; }',
     {'x': z3.IntVal(1)}),
    ('if [x > 0] { x = x + 1; } else { x = x; }', {'x': z3.IntVal(0)}),
    ('if [x > 0] { x = x + 1; }', {'x': z3.IntVal(0)}),
    ('x = x / y;', {'x': z3.Int('x'), 'y': z3.Int('y')}),
    ('x = (y > 0) ? x / y : x;', {'x': z3.Int('x'), 'y': z3.Int('y')}),
    ('', {'x': z3.Int('x')}),
])
def test_recorded_conditionals_definedness_and_pruning(code, env):
    statements = parse_operations(code, list(env))
    ordinary = execute_operations_domain(statements, env)
    recorded = execute_operations_domain(statements, env, record_construction=True)
    assert recorded.failure is None
    assert recorded.construction.check().status == 'verified'
    assert all(z3.eq(recorded.env[name], ordinary.env[name]) for name in env)
    assert [item.constraint.sexpr() for item in recorded.definedness_constraints] == [
        item.constraint.sexpr() for item in ordinary.definedness_constraints
    ]


def test_failed_execution_never_publishes_a_complete_construction():
    result = execute_operations_domain(parse_operations('x = sin(x);', ['x']),
                                       {'x': z3.Int('x')}, record_construction=True)
    assert result.failure is not None
    assert result.construction is None
    with pytest.raises(TypeError, match='record_construction must be bool'):
        execute_operations_domain([], {}, record_construction=1)


@pytest.mark.parametrize('corruption', [
    'identifier', 'forward_read', 'input', 'source_path', 'bad_path_type',
    'empty_path', 'duplicate_write', 'expression', 'kind', 'final',
])
def test_public_construction_checker_rejects_invalid_assignment_records(corruption):
    graph = execute_operations_domain(parse_operations('x = 1;', ['x']),
                                      {'x': z3.Int('x')}, record_construction=True).construction
    first, last = graph.values
    changes = {
        'identifier': replace(graph, values=(first, replace(last, identifier=0))),
        'forward_read': replace(graph, values=(first, replace(last, reads=(('x', 2),)))),
        'input': replace(graph, initial_versions={'y': 0}),
        'source_path': replace(graph, values=(first, replace(last, path=(999,)))),
        'bad_path_type': replace(graph, values=(first, replace(last, path=('x',)))),
        'empty_path': replace(graph, values=(first, replace(last, path=()))),
        'duplicate_write': replace(graph, values=(*graph.values, replace(last, identifier=2))),
        'expression': replace(graph, values=(first, replace(last, expression=z3.IntVal(2)))),
        'kind': replace(graph, values=(first, replace(last, kind='invalid'))),
        'final': replace(graph, final_versions={'x': 0}),
    }
    assert changes[corruption].check().status == 'invalid'


@pytest.mark.parametrize('corruption', [
    'duplicate_branch', 'missing_branch', 'merge_input', 'merge_alternative',
    'branch_source', 'branch_reads', 'branch_scope', 'branch_output',
])
def test_public_construction_checker_rejects_invalid_branch_records(corruption):
    graph = execute_operations_domain(
        parse_operations('if [x > 0] { x = x + 1; } else { x = x - 1; }', ['x']),
        {'x': z3.Int('x')}, record_construction=True,
    ).construction
    merge = graph.values[-1]
    branch = graph.branches[0]
    changes = {
        'duplicate_branch': replace(graph, branches=(*graph.branches, branch)),
        'missing_branch': replace(graph, branches=graph.branches[:1]),
        'merge_input': replace(graph, values=(*graph.values[:-1], replace(merge, reads=(('x', 1),)))),
        'merge_alternative': replace(graph, values=(*graph.values[:-1], replace(merge, alternatives=()))),
        'branch_source': replace(graph, branches=(replace(branch, source=graph.branches[1].source),
                                                 graph.branches[1])),
        'branch_reads': replace(graph, branches=(replace(branch, reads=(('x', 1),)), graph.branches[1])),
        'branch_scope': replace(graph, branches=(replace(branch, path_conditions=()), graph.branches[1])),
        'branch_output': replace(graph, branches=(replace(branch, result_versions=(('x', 0),)),
                                                 graph.branches[1])),
    }
    assert changes[corruption].check().status == 'invalid'


def test_captured_graph_detects_later_source_expression_mutation():
    statements = parse_operations('x = x + 1;', ['x'])
    graph = execute_operations_domain(statements, {'x': z3.Int('x')},
                                      record_construction=True).construction
    statements[0].expr = parse_operations('x = sin(x);', ['x'])[0].expr
    assert graph.check().status == 'invalid'


def test_captured_branch_detects_later_condition_mutation():
    statements = parse_operations('if [x > 0] { x = x + 1; }', ['x'])
    graph = execute_operations_domain(statements, {'x': z3.Int('x')},
                                      record_construction=True).construction
    statements[0].branches[0].condition = parse_operations(
        'if [x < 0] { x = x + 1; }', ['x'],
    )[0].branches[0].condition
    assert graph.check().status == 'invalid'


def test_caller_entry_scope_is_preserved():
    x = z3.Int('x')
    graph = execute_operations_domain(parse_operations('x = x + 1;', ['x']), {'x': x},
                                      path_conditions=(x > 0,), record_construction=True).construction
    assert graph.check().status == 'verified'


def test_missing_empty_branch_and_scope_are_detected_without_assignments():
    graph = execute_operations_domain(parse_operations('if [x > 0] {}', ['x']),
                                      {'x': z3.Int('x')}, record_construction=True).construction
    assert graph.check().status == 'verified'
    assert replace(graph, branches=()).check().status == 'invalid'
    branch = graph.branches[0]
    changed = replace(graph, branches=(replace(branch, path_conditions=()),))
    assert changed.check().status == 'invalid'


def test_merge_output_and_branch_output_must_agree_with_actual_writes():
    graph = execute_operations_domain(parse_operations('if [x > 0] { x = x + 1; }', ['x']),
                                      {'x': z3.Int('x')}, record_construction=True).construction
    branch = replace(graph.branches[0], result_versions=(('x', 0),))
    last = replace(graph.values[-1], alternatives=((branch.selector, 0),),
                   expression=z3.If(branch.selector, graph.values[0].expression,
                                    graph.values[0].expression))
    assert replace(graph, branches=(branch,), values=(*graph.values[:-1], last)).check().status == 'invalid'
