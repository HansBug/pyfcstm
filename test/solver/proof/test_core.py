"""Native refutations of exact public queries, independent of BMC."""

import json

import pytest
import z3

import pyfcstm.solver as solver


pytestmark = pytest.mark.unittest


def test_native_proof_binds_all_asserted_leaves_to_the_exact_inputs():
    x, y = z3.Ints('x y')
    query = solver.UnsatQuery('increment', (
        solver.UnsatConstraint('initial', (x >= 0,)),
        solver.UnsatConstraint('update', (y == x + 1,)),
        solver.UnsatConstraint('goal', (y < 0,)),
    ))
    report = solver.explain_unsat(query)
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    graph = report.proof
    assert graph.term(graph.node(graph.root_id).conclusion).value == 'false'
    leaves = [node for node in graph.nodes if node.rule == 'asserted']
    assert len(leaves) == 3
    assert all(node.input_occurrences for node in leaves)
    assert {item.constraint_id for item in graph.inputs} == {'initial', 'update', 'goal'}
    by_occurrence = {item.occurrence_id: item for item in graph.inputs}
    for leaf in leaves:
        for occurrence in leaf.input_occurrences:
            assert by_occurrence[occurrence].term_id == leaf.conclusion
    assert report.input_check == 'passed'
    assert json.loads(json.dumps(report.to_canonical()))['query_id'] == 'increment'


def test_duplicate_formula_origins_remain_alternatives_in_proof_inputs():
    x = z3.Int('x')
    query = solver.UnsatQuery('duplicates', (
        solver.UnsatConstraint('a', (x >= 0,)),
        solver.UnsatConstraint('b', (x >= 0,)),
        solver.UnsatConstraint('goal', (x < 0,)),
    ))
    graph = solver.explain_unsat(query).proof
    by_id = {item.constraint_id: item for item in graph.inputs}
    assert by_id['a'].term_id == by_id['b'].term_id
    leaf = next(node for node in graph.nodes if node.conclusion == by_id['a'].term_id
                and node.rule == 'asserted')
    assert set(leaf.input_occurrences) == {
        by_id['a'].occurrence_id, by_id['b'].occurrence_id,
    }


def test_native_parameters_keep_the_actual_arithmetic_certificate():
    x = z3.Real('x')
    query = solver.UnsatQuery('rational', (
        solver.UnsatConstraint('lower', (x >= z3.RealVal('1/3'),)),
        solver.UnsatConstraint('upper', (x < z3.RealVal('1/3'),)),
    ))
    graph = solver.explain_unsat(query).proof
    assert any(term.value == '1/3' for term in graph.terms)
    # This direct clash may be discharged by unit resolution; the linear chain
    # below forces an arithmetic lemma with native exact rational parameters.
    y = z3.Real('y')
    chain = solver.UnsatQuery('chain', (
        solver.UnsatConstraint('lower', (x >= 0,)),
        solver.UnsatConstraint('update', (y == x + 1,)),
        solver.UnsatConstraint('upper', (y < 0,)),
    ))
    graph = solver.explain_unsat(chain).proof
    arithmetic = [node for node in graph.nodes if node.rule == 'th-lemma']
    assert arithmetic
    assert any(parameter.value == 'farkas' for node in arithmetic
               for parameter in node.parameters)
    assert all(isinstance(parameter.value, str) for node in arithmetic
               for parameter in node.parameters)


def test_capture_uses_an_isolated_context_and_keeps_the_original_query_usable():
    context = z3.Context()
    x = z3.Int('x', ctx=context)
    query = solver.UnsatQuery('local', (
        solver.UnsatConstraint('lower', (x > 0,)),
        solver.UnsatConstraint('upper', (x < 0,)),
    ))
    report = solver.explain_unsat(query)
    assert report.solver_status == 'unsat'
    original = z3.Solver(ctx=context)
    original.add(x == 2)
    assert original.check() == z3.sat
    assert original.model().eval(x).as_long() == 2


@pytest.mark.parametrize('groups', [(), ('true',)])
def test_satisfiable_query_does_not_claim_a_proof(groups):
    query = solver.UnsatQuery('sat', tuple(
        solver.UnsatConstraint(name, (z3.BoolVal(True),)) for name in groups
    ))
    report = solver.explain_unsat(query)
    assert report.solver_status == 'sat'
    assert report.proof is None
    assert report.proof_status == 'unavailable'


def test_fixed_background_and_group_members_keep_distinct_occurrences():
    x = z3.Int('x')
    query = solver.UnsatQuery('groups', (
        solver.UnsatConstraint('goal', (x < 0, x < 10)),
    ), (solver.UnsatConstraint('background', (x >= 0,)),))
    graph = solver.explain_unsat(query).proof
    assert len(graph.inputs) == 3
    assert len({item.occurrence_id for item in graph.inputs}) == 3
    assert [item.constraint_id for item in graph.inputs if item.background] == ['background']


def test_native_ite_proof_preserves_shared_typed_terms():
    x, y = z3.Ints('x y')
    query = solver.UnsatQuery('branches', (
        solver.UnsatConstraint('update', (y == z3.If(x >= 0, x + 1, 0),)),
        solver.UnsatConstraint('goal', (y < 0,)),
    ))
    graph = solver.explain_unsat(query).proof
    assert any(term.operator == 'ite' for term in graph.terms)
    assert len([term for term in graph.terms if term.kind == 'literal'
                and term.sort == 'Int' and term.value == '0']) == 1
    positions = {node.node_id: i for i, node in enumerate(graph.nodes)}
    assert all(positions[parent] < positions[node.node_id]
               for node in graph.nodes for parent in node.parents)


@pytest.mark.parametrize('mode', ['formal', '', None])
def test_invalid_proof_modes_are_rejected(mode):
    with pytest.raises(ValueError, match='mode'):
        solver.explain_unsat(solver.UnsatQuery('empty', ()), mode=mode)


def test_invalid_query_is_rejected_before_native_work():
    with pytest.raises(TypeError, match='query'):
        solver.explain_unsat('not a query')


def test_minimization_retains_full_evidence_and_reproves_the_selected_groups():
    x, y, unrelated = z3.Ints('x y unrelated')
    query = solver.UnsatQuery('minimal', (
        solver.UnsatConstraint('initial', (x >= 0,)),
        solver.UnsatConstraint('update', (y == x + 1,)),
        solver.UnsatConstraint('goal', (y < 0,)),
        solver.UnsatConstraint('unrelated', (unrelated >= 0,)),
    ))
    report = solver.explain_unsat(query, minimize=True)
    assert report.core.core_ids == ('goal', 'initial', 'update')
    assert report.core.subset_minimality == 'proven'
    assert report.proof_scope == 'core'
    assert report.full_proof.execution_id != report.proof.execution_id
    assert {item.constraint_id for item in report.full_proof.inputs} == {
        'initial', 'update', 'goal', 'unrelated'}
    assert {item.constraint_id for item in report.proof.inputs} == {'initial', 'update', 'goal'}
    assert report.reading_status == 'complete'
    assert report.to_canonical()['core']['subset_minimality'] == 'proven'
    for removed in report.core.core_ids:
        native = z3.Solver()
        native.add(*(expression for group in query.constraints
                     if group.stable_id in report.core.core_ids and group.stable_id != removed
                     for expression in group.expressions))
        assert native.check() == z3.sat


def test_minimized_proof_keeps_fixed_background_even_when_the_core_is_empty():
    query = solver.UnsatQuery('background', (
        solver.UnsatConstraint('unrelated', (z3.Bool('irrelevant'),)),
    ), background=(solver.UnsatConstraint('fixed', (z3.BoolVal(False),)),))
    report = solver.explain_unsat(query, minimize=True)
    assert report.core.core_ids == ()
    assert report.core.subset_minimality == 'proven'
    assert report.proof_scope == 'core'
    assert [(item.constraint_id, item.background) for item in report.proof.inputs] == [('fixed', True)]


def test_core_mode_does_not_claim_a_native_derivation(text_aligner):
    query = solver.UnsatQuery('false', (solver.UnsatConstraint('false', (z3.BoolVal(False),)),))
    report = solver.explain_unsat(query, mode='core', minimize=True)
    assert report.core.core_ids == ('false',)
    assert report.core.subset_minimality == 'proven'
    assert report.proof is None
    assert report.full_proof is None
    assert report.proof_status == 'not_requested'
    assert report.proof_scope == 'none'
    text_aligner.assert_equal('''\
Query: false
Solver result: UNSAT
Reading: not_requested

No refutation is available.
''', report.reading.to_text(detail='detailed'))


@pytest.mark.parametrize('option,value', [('minimize', 1), ('names', {}), ('extensions', {})])
def test_proof_options_are_checked_even_for_sat_queries(option, value):
    with pytest.raises(TypeError):
        solver.explain_unsat(solver.UnsatQuery('empty', ()), **{option: value})


def test_unknown_during_optional_minimization_preserves_the_full_proof(monkeypatch):
    native_check = z3.Solver.check
    calls = []

    def check(native, *assumptions):
        calls.append(assumptions)
        if len(calls) > 1:
            return z3.unknown
        return native_check(native, *assumptions)

    monkeypatch.setattr(z3.Solver, 'check', check)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda native: 'injected external solver unknown')
    report = solver.explain_unsat(solver.UnsatQuery('false', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    )), minimize=True)
    assert len(calls) == 2
    assert report.solver_status == 'unsat'
    assert report.proof_scope == 'full'
    assert report.proof_status == 'captured'
    assert report.reading_status == 'complete'
    assert report.core.core_ids is None
    assert report.core.subset_minimality == 'not_proven'
    assert report.stop_reason == 'core extraction returned unknown'


def test_slow_rule_extension_exhausts_shared_deadline_without_losing_native_evidence(monkeypatch):
    import time
    from pyfcstm.solver.proof import ProofExtensions
    from pyfcstm.solver.proof import ProofRuleHandler, RuleAnalysis

    now = [0.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])

    def interpret(node, graph):
        now[0] = 1.0
        return RuleAnalysis('logical', 'trusted')

    x = z3.Real('x')
    report = solver.explain_unsat(solver.UnsatQuery('deadline', (
        solver.UnsatConstraint('lower', (x >= 2,)), solver.UnsatConstraint('upper', (x < 1,)),
    )), timeout_ms=60, extensions=ProofExtensions(rule_handlers=(ProofRuleHandler('th-lemma', interpret),)))
    assert report.solver_status == 'unsat'
    assert report.proof is not None
    assert report.proof_status == 'captured'
    assert report.reading_status == 'not_requested'
    assert report.stop_reason == 'budget exhausted during proof analysis'


def test_minimization_and_reproof_share_the_original_deadline(monkeypatch):
    import time

    native_check = z3.Solver.check
    checks = []
    now = [0.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])

    def check(native, *assumptions):
        checks.append(assumptions)
        result = native_check(native, *assumptions)
        if len(checks) == 2:
            now[0] = 1.0
        return result

    monkeypatch.setattr(z3.Solver, 'check', check)
    report = solver.explain_unsat(solver.UnsatQuery('false', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    )), minimize=True, timeout_ms=60)
    assert len(checks) == 2
    assert report.solver_status == 'unsat'
    assert report.proof_scope == 'full'
    assert report.proof_status == 'captured'
    assert report.core.core_ids is None
    assert report.core.core_check == 'timeout'
    assert report.reading_status == 'complete'


def test_deadline_during_native_export_keeps_unsat_but_does_not_publish_a_partial_graph(monkeypatch):
    import time

    now = [0.0]
    native_proof = z3.Solver.proof

    def proof(native):
        result = native_proof(native)
        now[0] = 1.0
        return result

    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(z3.Solver, 'proof', proof)
    report = solver.explain_unsat(solver.UnsatQuery('false', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    )), timeout_ms=100)
    assert report.solver_status == 'unsat'
    assert report.proof is None
    assert report.proof_status == 'unavailable'
    assert report.stop_reason == 'budget exhausted during proof capture'


def test_reproof_unknown_preserves_original_proof_and_the_verified_core(monkeypatch):
    original = z3.Solver.check
    count = [0]

    def check(native, *assumptions):
        count[0] += 1
        return z3.unknown if count[0] == 6 else original(native, *assumptions)

    monkeypatch.setattr(z3.Solver, 'check', check)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda native: 'injected reproof unknown')
    report = solver.explain_unsat(solver.UnsatQuery('false', (
        solver.UnsatConstraint('false', (z3.BoolVal(False),)),
    )), minimize=True)
    assert count[0] == 6
    assert report.proof_status == 'captured'
    assert report.proof_scope == 'full'
    assert report.core.core_ids == ('false',)
    assert report.core.subset_minimality == 'proven'
    assert report.stop_reason == 'injected reproof unknown'
    assert report.reading_status == 'complete'


def test_quantifier_instantiation_parameters_preserve_the_exact_expression():
    i = z3.Int('i')
    f = z3.Function('f', z3.IntSort(), z3.IntSort())
    report = solver.explain_unsat(solver.UnsatQuery('instantiate-seven', (
        solver.UnsatConstraint('all', (z3.ForAll(i, f(i) > i),)),
        solver.UnsatConstraint('seven', (f(7) < 7,)),
    )))
    parameters = tuple(parameter.value for node in report.proof.nodes if node.rule == 'quant-inst'
                       for parameter in node.parameters if parameter.kind == 'expression')
    assert parameters == ('7',)


@pytest.mark.parametrize('decimal', [False, True])
@pytest.mark.parametrize('precision', [2, 10, 30])
def test_exact_numeric_capture_is_independent_of_native_display(decimal, precision, text_aligner):
    import subprocess
    import sys

    # A separate interpreter isolates process-wide Z3 presentation options.
    program = '''
import z3
import json
from pyfcstm.solver import UnsatConstraint, UnsatQuery, UnsatReport, explain_unsat
z3.set_option(rational_to_decimal=%r, precision=%d)
for lower, upper in [('1/3', '1/4'), ('-1/4', '-1/3'),
                     ('123456789012345678901234567890', '0')]:
    x = z3.Real('x')
    report = explain_unsat(UnsatQuery('exact', (
        UnsatConstraint('lower', (x >= z3.RealVal(lower),)),
        UnsatConstraint('upper', (x <= z3.RealVal(upper),)),
    )))
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    assert report.reading_status == 'complete'
    values = {term.value for term in report.proof.terms if term.kind == 'literal'}
    assert lower in values, values
    assert upper in values, values
    restored = UnsatReport.from_canonical(report.to_canonical())
    assert restored.proof == report.proof
    if lower == '1/3':
        print(json.dumps(restored.reading.to_text('en', detail='detailed')))
i = z3.Int('i')
r = explain_unsat(UnsatQuery('integer', (
    UnsatConstraint('lower', (i >= 123456789012345678901234567890,)),
    UnsatConstraint('upper', (i <= 0,)),
)))
assert r.reading_status == 'complete'
assert any(t.value == '123456789012345678901234567890' for t in r.proof.terms)
a = z3.Real('a')
root = z3.simplify(z3.Sqrt(2))
r = explain_unsat(UnsatQuery('algebraic', (
    UnsatConstraint('equal', (a == root,)),
    UnsatConstraint('false', (z3.BoolVal(False),)),
)))
assert r.reading_status == 'complete'
assert {t.value for t in r.proof.terms if t.kind == 'algebraic'} == {
    '(root-obj (+ (^ x 2) (- 2)) 2)'}
assert UnsatReport.from_canonical(r.to_canonical()).proof == r.proof
''' % (decimal, precision)
    completed = subprocess.run([sys.executable, '-c', program],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    text_aligner.assert_equal("""\
Query: exact
Solver result: UNSAT
Reading: complete

P1  Exact linear combination
  To refute the negated conclusion, temporarily assume:
    (x <= 1/4)
    (x >= 1/3)
  1 * [x + -1/4 <= 0]
  1 * [-1 * x + 1/3 <= 0]
  Sum: 1/12 <= 0; contradiction.
  Discharge these temporary assumptions.
  Therefore: (not ((x <= 1/4)) or not ((x >= 1/3)))

P2  Input
  Input origins: lower
  Therefore: (1/3 <= x)

P3  Input
  Input origins: upper
  Therefore: (1/4 >= x)

P4  Resolve the clauses
  From: P1, P2, P3
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.

""", json.loads(completed.stdout))


def test_native_capture_classifies_each_shared_ast_only_once(monkeypatch):
    from collections import Counter
    from pyfcstm.solver.proof import _z3_proof

    calls = Counter()
    original = _z3_proof._is_proof

    def counted(expression):
        calls[expression.get_id()] += 1
        return original(expression)

    monkeypatch.setattr(_z3_proof, '_is_proof', counted)
    values = z3.Ints(' '.join('x%d' % i for i in range(17)))
    formulas = [values[0] == 0] + [
        z3.Implies(values[i] >= 0, values[i+1] == values[i] + 1) for i in range(16)
    ] + [values[-1] < 0]
    report = solver.explain_unsat(solver.UnsatQuery('shared_capture', tuple(
        solver.UnsatConstraint('condition_%d' % i, (formula,)) for i, formula in enumerate(formulas)
    )))
    assert report.reading_status == 'complete'
    assert calls
    assert max(calls.values()) == 1
