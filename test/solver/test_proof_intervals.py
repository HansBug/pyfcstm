"""Exact local range evidence, including open endpoints and unsafe mutations."""

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, UnsatReport, explain_unsat
from pyfcstm.solver.proof import analyze_proof
from .test_proof_rules import _certificate_graph

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('case,expected', [
    ('crossing_square', 'checked'), ('unbounded_square', 'checked'),
    ('open_product', 'checked'), ('zero_product', 'checked'),
    ('cast', 'checked'), ('unknown_condition', 'unsupported'),
    ('unbounded_branch', 'unsupported'), ('false_branch', 'checked'),
    ('converging', 'unsupported'), ('satisfiable', 'unsupported'),
])
def test_interval_reconstruction_uses_only_local_arithmetic(case, expected):
    x, y = z3.Reals('x y')
    i = z3.Int('i')
    p = z3.Bool('p')
    cases = {
        'crossing_square': (x >= -2, x <= 3, x * x > 9),
        'unbounded_square': (x * x < 0,),
        'open_product': (x > 1, y >= 2, x * y <= 2),
        'zero_product': (x == 0, x * y > 0),
        'cast': (i >= 2, y >= 2, z3.ToReal(i) * y < 4),
        'unknown_condition': (z3.If(p, x, y) > 0,),
        'unbounded_branch': (x >= 1, z3.If(x > 0, y, -y) < 0),
        'false_branch': (x <= -2, z3.If(x >= 0, x, -x) < 2),
        'converging': (x >= 0, y >= 0, x <= 1, y <= 1, x <= z3.RealVal('1/2') * y, y <= z3.RealVal('1/2') * x),
        'satisfiable': (x >= 0, y >= 0, x * y <= 2),
    }
    graph = _certificate_graph(cases[case], ())
    node = analyze_proof(graph).graph.node(graph.root_id)
    assert node.local_check == expected
    if expected == 'checked':
        assert node.interval is not None
        used, pending = set(), list(node.interval.conflict)
        while pending:
            index = pending.pop()
            if index not in used:
                used.add(index)
                pending.extend(node.interval.steps[index].premises)
        assert used == set(range(len(node.interval.steps)))
    else:
        assert node.interval is None


@pytest.mark.parametrize('mutation', ['term', 'sort', 'infinite_closed', 'linear_bound_missing',
                                     'forward_step', 'bound_index', 'conflict_index',
                                     'different_terms', 'overlap'])
def test_offline_interval_evidence_rejects_bad_references_and_ranges(mutation):
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('square', (UnsatConstraint('condition', (x * x == 2,)),)))
    data = report.to_canonical()
    certificate = next(node['interval'] for node in data['proof']['nodes'] if node['interval'] is not None)
    first = certificate['steps'][0]
    left, right = (certificate['steps'][index] for index in certificate['conflict'])
    if mutation == 'term':
        first['term_id'] = 'missing'
    elif mutation == 'sort':
        next(term for term in data['proof']['terms'] if term['term_id'] == first['term_id'])['sort'] = 'Bool'
    elif mutation == 'infinite_closed':
        first['upper'] = None
        first['upper_open'] = False
    elif mutation == 'linear_bound_missing':
        first['bound_index'] = None
    elif mutation == 'forward_step':
        first['premises'] = [len(certificate['steps'])]
    elif mutation == 'bound_index':
        first['bound_index'] = len(certificate['bounds'])
    elif mutation == 'conflict_index':
        certificate['conflict'] = (len(certificate['steps']), certificate['conflict'][1])
    elif mutation == 'different_terms':
        right['term_id'] = next(step['term_id'] for step in certificate['steps'] if step['term_id'] != left['term_id'])
    else:
        for step in (left, right):
            step.update(lower='2', upper='3', lower_open=False, upper_open=False)
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


def _interval_implication_reading():
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofInput, ProofNode, ProofTerm, ProofReading, ReadingBlock

    x, y = z3.Reals('x y')
    graph = _certificate_graph((x >= 2, y >= 2), (), x * y >= 4)
    claim = graph.node(graph.root_id).conclusion
    false = next(term.term_id for term in graph.terms if term.kind == 'literal' and term.value == 'false')
    graph = replace(graph, root_id='resolve',
                    terms=graph.terms + (ProofTerm('negated', 'application', 'Bool', 'not', (claim,)),),
                    inputs=graph.inputs[:2] + (ProofInput('negative', 'negative', 0, 'negated', False),),
                    nodes=graph.nodes + (
                        ProofNode('negative', 'asserted', (), 'negated', input_occurrences=('negative',)),
                        ProofNode('resolve', 'unit-resolution', (graph.root_id, 'negative'), false)))
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'passed'
    assert analysis.gaps == ()
    assert any(bound.negated for bound in analysis.graph.node('combination').interval.bounds)
    graph = analysis.graph
    return ProofReading('implication', 'unsat', graph.root_id, 'complete', tuple(
        ReadingBlock(node.node_id, node.inference_kind, (node.conclusion,), node.parents, (), (node.node_id,))
        for node in graph.nodes), (), (), graph)


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_interval_implication_text_displays_and_discharges_temporary_assumptions(language, text_aligner):
    from pathlib import Path

    expected = (Path(__file__).parent / 'proof_readings' / ('interval_implication.' + language + '.txt')).read_text()
    text_aligner.assert_equal(expected, _interval_implication_reading().to_text(language))


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_explicit_extension_gap_remains_visible_in_full_text(language, text_aligner):
    from pathlib import Path
    from pyfcstm.solver.proof import ProofExtensions, ProofRuleHandler, RuleAnalysis

    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('unknown_rule', (
        UnsatConstraint('lower', (x >= 1,)), UnsatConstraint('upper', (x <= 0,)),
    )), extensions=ProofExtensions(rule_handlers=(
        ProofRuleHandler('th-lemma', lambda node, graph: RuleAnalysis('opaque', 'unsupported')),)))
    assert report.reading_status == 'partial'
    expected = (Path(__file__).parent / 'proof_readings' / ('unknown_rule.' + language + '.txt')).read_text()
    text_aligner.assert_equal(expected, report.reading.to_text(language))


def _singleton_equality_report():
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofNode, ProofParameter, ProofReading, ReadingBlock

    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('singleton', (
        UnsatConstraint('zero', (x >= 0, x <= 0)),
        UnsatConstraint('goal', (x * x == 0,)),
        UnsatConstraint('false', (z3.BoolVal(False),)),
    )))
    graph = report.proof
    nodes = tuple(ProofNode('p%d' % index, 'asserted', (), graph.inputs[index].term_id,
                            input_occurrences=(graph.inputs[index].occurrence_id,)) for index in range(2))
    nodes += (ProofNode('equality', 'th-lemma', ('p0', 'p1'), graph.inputs[2].term_id,
                        parameters=(ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'eq-propagate'))),
              ProofNode('false', 'asserted', (), graph.inputs[3].term_id,
                        input_occurrences=(graph.inputs[3].occurrence_id,)))
    analysis = analyze_proof(replace(graph, nodes=nodes, root_id='false'))
    assert analysis.graph.node('equality').interval.equality is not None
    reading = ProofReading('singleton', 'unsat', 'false', 'complete', tuple(
        ReadingBlock(node.node_id, node.inference_kind, (node.conclusion,), node.parents, (), (node.node_id,))
        for node in analysis.graph.nodes), (), (), analysis.graph)
    return replace(report, proof=analysis.graph, reading=reading)


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_singleton_equality_full_text_and_offline_roundtrip(language, text_aligner):
    from pathlib import Path

    report = _singleton_equality_report()
    expected = (Path(__file__).parent / 'proof_readings' / ('singleton.' + language + '.txt')).read_text()
    text_aligner.assert_equal(expected, report.reading.to_text(language))
    text_aligner.assert_equal(expected, UnsatReport.from_canonical(report.to_canonical()).reading.to_text(language))


@pytest.mark.parametrize('mutation', ['both_results', 'no_result', 'not_singleton', 'wrong_conclusion'])
def test_interval_equality_loading_rejects_ambiguous_or_wrong_results(mutation):
    data = _singleton_equality_report().to_canonical()
    node = next(node for node in data['proof']['nodes'] if node['interval'] is not None)
    certificate = node['interval']
    if mutation == 'both_results':
        certificate['conflict'] = certificate['equality']
    elif mutation == 'no_result':
        certificate['equality'] = None
    elif mutation == 'not_singleton':
        certificate['steps'][certificate['equality'][0]]['upper'] = '1'
    else:
        node['conclusion'] = data['proof']['nodes'][-1]['conclusion']
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


def test_nonsingleton_ranges_do_not_prove_an_arbitrary_equality():
    x, y = z3.Reals('x y')
    graph = _certificate_graph((x >= 1, y >= 1), (), x * y == 0)
    node = analyze_proof(graph).graph.node(graph.root_id)
    assert node.local_check == 'unsupported'
    assert node.interval is None


@pytest.mark.parametrize('sign', [1, -1])
def test_tiny_nonzero_product_does_not_certify_satisfiable_premises(sign):
    x, y = z3.Reals('x y')
    epsilon = z3.RealVal(str(sign) + '/' + str(10 ** 400))
    graph = _certificate_graph((x > 1, y == epsilon, sign * x * y > 0), ())
    assert analyze_proof(graph).graph.node(graph.root_id).local_check == 'unsupported'


def test_large_integer_product_proof_keeps_exact_endpoints():
    x, y = z3.Ints('x y')
    large = 10 ** 310
    report = explain_unsat(UnsatQuery('large', (
        UnsatConstraint('bounds', (x > large, y > 1, x * y < large)),
    )))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'


def test_zero_scale_closes_both_endpoints_of_an_unbounded_range():
    from fractions import Fraction
    from pyfcstm.solver.proof.interval import _Range

    assert _Range().scale(Fraction(0)) == _Range(Fraction(0), Fraction(0), False, False)


@pytest.mark.parametrize('power', [2 ** 53 + 1, 10 ** 310 + 1])
def test_unbounded_odd_power_keeps_negative_infinity(power):
    x = z3.Real('x')
    graph = _certificate_graph((x < 0, x ** power < 0), ())
    assert analyze_proof(graph).graph.node(graph.root_id).local_check == 'unsupported'


@pytest.mark.parametrize('case,expected', [
    ('direct', 'checked'), ('chain', 'checked'), ('scaled', 'checked'),
    ('one_way', 'unsupported'), ('offset', 'unsupported'), ('unequal_coefficients', 'unsupported'),
    ('uninterpreted', 'unsupported'), ('mixed_sorts', 'unsupported'),
    ('consistent', 'unsupported'),
])
def test_congruence_uses_only_proven_same_sort_equalities(case, expected):
    x, y, z = z3.Reals('x y z')
    i = z3.Int('i')
    f = z3.Function('f', z3.RealSort(), z3.RealSort())
    g = z3.Function('g', z3.RealSort(), z3.RealSort())
    cases = {
        'direct': (x == y, x * x <= 2, y * y >= 3),
        'chain': (x == y, y == z, x * x <= 2, z * z >= 3),
        'scaled': (2 * x <= 2 * y, 3 * y <= 3 * x, x * x <= 2, y * y >= 3),
        'one_way': (x <= y, x * x <= 2, y * y >= 3),
        'offset': (x == y + 1, x * x == 4, y * y == 1),
        'unequal_coefficients': (x == 2 * y, x * x == 12, y * y == 3),
        'uninterpreted': (x == y, f(x) == 2, g(y) == 3),
        'mixed_sorts': (z3.ToReal(i) == x, x * x >= 0),
        'consistent': (x == y, x * x <= 3, y * y >= 2),
    }
    graph = _certificate_graph(cases[case], ())
    node = analyze_proof(graph).graph.node(graph.root_id)
    assert node.local_check == expected
    if expected == 'checked':
        assert any(step.rule == 'congruence' for step in node.interval.steps)


def test_congruence_handles_deep_boolean_conditions_without_python_recursion():
    x, y = z3.Reals('x y')
    condition = z3.Bool('p')
    for _ in range(1100):
        condition = z3.Not(condition)
    report = explain_unsat(UnsatQuery('deep', (UnsatConstraint('conditions', (
        x * x == 2, y * y == 3, x == y, z3.If(condition, x, y) > 0,
    )),)))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.gaps == ()


@pytest.mark.parametrize('mutation', ['arity', 'reference', 'sort', 'rule', 'source', 'bound'])
def test_offline_congruence_evidence_rejects_broken_dependencies(mutation):
    x, y = z3.Reals('x y')
    report = explain_unsat(UnsatQuery('shared_square', (UnsatConstraint('conditions', (
        x * x == 2, y * y == 3, x == y,
    )),)))
    data = report.to_canonical()
    step = next(step for node in data['proof']['nodes'] if node['interval'] is not None
                for step in node['interval']['steps'] if step['substitutions'])
    equality = step['substitutions'][0]
    if mutation == 'arity':
        equality['bound_indices'] = []
    elif mutation == 'reference':
        equality['left_id'] = 'missing'
    elif mutation == 'sort':
        next(term for term in data['proof']['terms'] if term['term_id'] == equality['left_id'])['sort'] = 'Int'
    elif mutation == 'rule':
        step['rule'] = 'sum'
    elif mutation == 'source':
        step['premises'] = []
    else:
        equality['bound_indices'] = [-1]
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)



@pytest.mark.parametrize('case,expected', [
    ('algebraic', 'checked'), ('unequal_ratio', 'unsupported'),
    ('nonzero_sum', 'unsupported'), ('nonzero_coefficient', 'unsupported'),
])
def test_congruence_cancellation_requires_exact_zero_coefficients(case, expected):
    x, y, z = z3.Reals('x y z')
    cases = {
        'algebraic': (z > z3.simplify(z3.Sqrt(2)), x == y, x*x-y*y < 0),
        'unequal_ratio': (x+y <= 2*x+3*y,),
        'nonzero_sum': (x == y, x*x+y*y > 0),
        'nonzero_coefficient': (x == y, x*x-2*y*y < 0),
    }
    graph = _certificate_graph(cases[case], ())
    node = analyze_proof(graph).graph.node(graph.root_id)
    assert node.local_check == expected


def test_congruence_handles_deep_arithmetic_without_python_recursion():
    x, y = z3.Reals('x y')
    term = x
    for _ in range(1100):
        term = -term
    report = explain_unsat(UnsatQuery('deep_arithmetic', (UnsatConstraint('conditions', (
        x*x == 2, y*y == 3, x == y, term > 0,
    )),)))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
