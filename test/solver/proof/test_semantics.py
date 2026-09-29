"""Compositional power semantics through actual FCSTM translation and replay."""

from dataclasses import replace

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.domain import translate_expr_domain
from pyfcstm.solver.expr import create_z3_vars_from_models
from pyfcstm.solver.proof import UnsatReport
from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.proof.polynomial import polynomial_certificate, check_polynomial_certificate
from .test_polynomial import _graph, _certificate

pytestmark = pytest.mark.unittest


def _expression_report(predicate, timeout_ms=120000):
    # Semantic coverage and text snapshots are not latency benchmarks. Leave
    # room for branch instrumentation and concurrent CI workers.
    model = load_state_machine_from_text(
        'def float x=0; def float y=0; state Root { state A; state B; '
        '[*]->A; A->B: if [%s]; }' % predicate)
    guard = next(t.guard for s in model.walk_states() for t in s.transitions if t.guard is not None)
    domain = translate_expr_domain(guard, create_z3_vars_from_models(model))
    assert domain.failure is None
    inputs = tuple(UnsatConstraint('domain%d' % i, (c.constraint,))
                   for i, c in enumerate(domain.definedness_constraints))
    return explain_unsat(UnsatQuery('power_semantics', inputs + (
        UnsatConstraint('guard', (domain.z3_expr,)),)), timeout_ms=timeout_ms)


@pytest.mark.parametrize('predicate', [
    'x >= 0 && x ** (1.0/3.0) < 0',
    'x >= 0 && x ** (1.0/5.0) < 0',
    'x >= 0 && x ** (2.0/3.0) < 0',
    'x > 0 && y > 0 && x ** y <= 0',
    'x > 0 && y < 0 && x ** y <= 0',
])
def test_public_power_sign_families_have_complete_readings(predicate, text_aligner):
    report = _expression_report(predicate)
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    restored = UnsatReport.from_canonical(report.to_canonical())
    for detail in ('brief', 'standard', 'detailed'):
        text_aligner.assert_equal(report.reading.to_text(detail=detail), restored.reading.to_text(detail=detail))


@pytest.mark.parametrize('exponent', ['1/2', '1/3', '1/5', '2/3', 'y', -2, 0])
def test_positive_base_power_sign_has_exact_local_evidence(exponent):
    graph = _graph((('>', 'x', 0), ('<=', ('^', 'x', exponent), 0)))
    certificate = _certificate(graph)
    assert any(step.rule in ('power_sign', 'power_identity') for step in certificate.steps)


@pytest.mark.parametrize('exponent', ['1/2', '1/3', '2/3'])
def test_nonnegative_base_rational_power_sign_has_exact_local_evidence(exponent):
    _certificate(_graph((('>=', 'x', 0), ('<', ('^', 'x', exponent), 0))))


def test_oversized_optional_power_identity_keeps_the_usable_sign_evidence():
    base = ('*', 'x', 'x')
    _certificate(_graph((('>', base, 0), ('<=', ('^', base, -32), 0))))


def test_an_operation_atom_cannot_supply_a_spurious_zero_assignment_witness():
    _certificate(_graph((('<=', ('^', 2, 'x'), 0),)))


@pytest.mark.parametrize('factor_sign', [-1, 1])
@pytest.mark.parametrize('product_sign', [-1, 1])
def test_product_order_can_strengthen_a_nonnegative_factor(factor_sign, product_sign):
    left, right = ('*', factor_sign, 'x'), ('*', factor_sign, 'z')
    first, second = ('*', product_sign, left, 'y'), ('*', product_sign, right, 'y')
    graph = _graph((('>=', left, 0), ('>=', right, left), ('>=', first, 0),
                    ('>=', second, 0), ('>', first, second)))
    certificate = polynomial_certificate(graph.node('target'), graph, SolveBudget(5000))
    assert certificate is not None
    assert check_polynomial_certificate(graph.node('target'), graph, certificate)


def _positive_factor_report():
    import z3
    from pyfcstm.solver.proof import analyze_proof, ProofReading, ReadingBlock
    from .test_rules import _certificate_graph

    x, y, z = z3.Reals('x y z')
    graph = _certificate_graph((x >= 0, z >= x, x*y >= 0, z*y >= 0, x*y > z*y), ())
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'passed'
    assert analysis.rule_check == 'complete'
    assert analysis.gaps == ()
    graph = analysis.graph
    reading = ProofReading('product_order', 'unsat', graph.root_id, 'complete', tuple(
        ReadingBlock(node.node_id, node.inference_kind, (node.conclusion,), node.parents, (), (node.node_id,))
        for node in graph.nodes), (), (), graph)
    return UnsatReport('product_order', 'unsat', 'captured', graph, input_check='passed',
                       scope_check='passed', rule_check='complete', reading=reading,
                       reading_status='complete', proof_scope='full')


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_positive_factor_reading_is_complete_and_portable(language, text_aligner):
    from pathlib import Path

    report = _positive_factor_report()
    expected = Path(__file__).with_name('proof_readings') / ('positive_factor.%s.txt' % language)
    text_aligner.assert_equal(expected.read_text(encoding='utf-8'), report.reading.to_text(language))
    restored = UnsatReport.from_canonical(report.to_canonical())
    for detail in ('brief', 'standard', 'detailed'):
        text_aligner.assert_equal(report.reading.to_text(language, detail=detail),
                                  restored.reading.to_text(language, detail=detail))


def test_derived_order_bound_can_be_multiplied_by_another_positive_factor():
    graph = _graph((('>', 'x', 0), ('>', 'y', 0), ('>=', 'r', 'x'), ('>=', 't', 0),
                    ('=', ('*', 't', 't'), ('*', 'x', 'x', 'y', 'y')),
                    ('>', 't', ('*', 'r', 'y'))))
    certificate = polynomial_certificate(graph.node('target'), graph, SolveBudget(5000))
    assert certificate is not None
    assert check_polynomial_certificate(graph.node('target'), graph, certificate)


@pytest.mark.parametrize('fixture_name', ['root_product_local.json', 'root_product_order_local.json'])
def test_root_product_with_frame_aliases_uses_composed_bounds(fixture_name):
    import json
    from pathlib import Path
    from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofTerm

    # Actual local arithmetic obligation emitted by the two-frame BMC test.
    # Retain term identities so this also guards native proof decomposition.
    data = json.loads(Path(__file__).with_name(fixture_name).read_text())
    terms = tuple(ProofTerm(**dict(term, arguments=tuple(term['arguments']),
                                  bindings=tuple(term['bindings']))) for term in data['terms'])
    node = ProofNode('target', 'th-lemma', (), data['conclusion'])
    graph = ProofGraph('local', 'target', (node,), terms, ())
    certificate = polynomial_certificate(node, graph, SolveBudget(30000))
    assert certificate is not None
    assert check_polynomial_certificate(node, graph, certificate)


@pytest.mark.parametrize('premises', [
    (('>=', 'x', 0), ('<=', ('^', 'x', '1/3'), 0)),
    (('>=', 'x', 0), ('<=', ('^', 'x', 'y'), 0)),
    (('<', 'x', 0), ('<', ('^', 'x', 3), 0)),
    (('<', ('^', 'x', '1/2'), 0),),
])
def test_power_domains_are_not_silently_strengthened(premises):
    graph = _graph(premises)
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


@pytest.mark.parametrize('numerator,denominator', [(1, 2), (1, 3), (1, 5), (2, 3), (-1, 2), (0, 1)])
def test_rational_power_identity_composes_with_polynomial_equality(numerator, denominator):
    root = ('^', 'x', '%d/%d' % (numerator, denominator))
    left = ('^', root, denominator)
    right = ('^', 'x', numerator) if numerator > 0 else 1
    if numerator < 0:
        left = ('*', left, ('^', 'x', -numerator))
    graph = _graph((('>', 'x', 0), ('not', ('=', left, right))))
    _certificate(graph)


@pytest.mark.parametrize('degree', [3, 5, 7, 9])
@pytest.mark.parametrize('expanded', [False, True])
def test_odd_power_order_is_parameterized(degree, expanded):
    left = ('*',) + ('x',) * degree if expanded else ('^', 'x', degree)
    right = ('*',) + ('y',) * degree if expanded else ('^', 'y', degree)
    _certificate(_graph((('>', 'x', 'y'), ('<=', left, right))))


@pytest.mark.parametrize('predicate', [
    'x > y && x*x*x*x*x <= y*y*y*y*y',
    'x >= 0 && y >= 0 && sqrt(x*y) != sqrt(x)*sqrt(y)',
    'x >= 0 && sqrt(sqrt(x)) ** 4 != x',
])
def test_public_composed_algebraic_readings(predicate):
    report = _expression_report(predicate)
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert UnsatReport.from_canonical(report.to_canonical()).reading_status == 'complete'


@pytest.mark.parametrize('prefix', ['normal', 'renamed'])
def test_products_compose_upper_bounds_without_assuming_a_positive_left_factor(prefix):
    # This is the local arithmetic obligation emitted for a root-product guard.
    graph = _graph((('>', 't', 0), ('>', 'r', 0), ('>=', ('*', 'x', 'y'), ('^', 't', 2)),
                    ('>', 'y', 0), ('>', 's', 0), ('<=', 'y', ('^', 's', 2)),
                    ('<=', 'x', ('^', 'r', 2)), ('>', 't', ('*', 'r', 's'))), prefix=prefix)
    _certificate(graph)


@pytest.mark.parametrize('predicate', [
    'y >= 0 && y ** (1.0/3.0) < 0',
    'x >= 0 && y >= 0 && sqrt(y)*sqrt(x) != sqrt(y*x)',
    'x >= 0 && y >= 0 && sqrt((x+1)*(y+1)) != sqrt(x+1)*sqrt(y+1)',
    'x > y && (x+1)**5 <= (y+1)**5',
    'x >= y && y >= 0 && x**4 < y**4',
    'x >= 0 && sqrt(sqrt(sqrt(x))) ** 8 != x',
])
def test_composition_survives_renaming_reordering_and_nested_expressions(predicate):
    report = _expression_report(predicate)
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.stop_reason is None
    assert UnsatReport.from_canonical(report.to_canonical()).reading_status == 'complete'


@pytest.mark.parametrize('predicate', [
    'x == 0 && x ** (1.0/3.0) == 0',
    'x == -1 && x**3 < 0',
    'x == -2 && y == -1 && x**4 > y**4',
    'x == 1 && y == 4 && sqrt(x*y) == sqrt(x)*sqrt(y)',
])
def test_public_satisfiable_boundaries_are_not_explained_as_contradictions(predicate):
    report = _expression_report(predicate)
    if '1.0/3.0' in predicate:
        # Z3 may leave fractional powers incomplete even at a fixed zero base.
        assert report.solver_status in ('sat', 'unknown')
    else:
        assert report.solver_status == 'sat'
    assert report.proof is None


@pytest.mark.parametrize('rule', ['power_sign', 'power_identity'])
@pytest.mark.parametrize('mutation', ['domain', 'premises', 'operator', 'sort', 'term', 'multiplier',
                                     'strict', 'value', 'weights', 'factor', 'negated'])
def test_semantic_evidence_requires_exact_operation_domain_and_conclusion(rule, mutation):
    graph = _graph((('>', 'x', 0), ('<=', ('^', 'x', '1/3'), 0))) if rule == 'power_sign' else _graph(
        (('>', 'x', 0), ('not', ('=', ('^', ('^', 'x', '1/3'), 3), 'x'))))
    certificate = _certificate(graph)
    steps = list(certificate.steps)
    index = next(i for i, step in enumerate(steps) if step.rule == rule)
    step = steps[index]
    if mutation == 'domain':
        # A different already-proven fact is not the base's domain evidence.
        steps[index] = replace(step, premises=(index - 1,))
        if steps[index].premises == step.premises:
            steps[index] = replace(step, premises=(0,))
        if steps[index].premises == step.premises:
            steps[index] = replace(step, premises=())
    elif mutation == 'premises':
        steps[index] = replace(step, premises=())
    elif mutation in ('operator', 'sort'):
        graph = replace(graph, terms=tuple(replace(t, **({'operator_kind': 'uninterpreted'} if mutation == 'operator'
                                                        else {'sort': 'Int'})) if t.term_id == step.term_id else t
                                          for t in graph.terms))
    elif mutation == 'term':
        steps[index] = replace(step, term_id=None)
    elif mutation == 'multiplier':
        steps[index] = replace(step, multiplier='2')
    elif mutation == 'strict':
        steps[index] = replace(step, strict=not step.strict)
    elif mutation == 'value':
        steps[index] = replace(step, coefficients=(((), '1'),))
    elif mutation == 'weights':
        steps[index] = replace(step, weights=('1',))
    elif mutation == 'factor':
        steps[index] = replace(step, factor=(((), '1'),))
    else:
        steps[index] = replace(step, negated=True)
    assert not check_polynomial_certificate(graph.node('target'), graph, replace(certificate, steps=tuple(steps)))


def test_generated_polynomial_evidence_is_replayed_before_it_is_accepted(monkeypatch):
    from pyfcstm.solver.proof import polynomial
    from pyfcstm.solver.proof.core import PolynomialCertificate, PolynomialStep

    monkeypatch.setattr(polynomial._Search, 'generate', lambda self: PolynomialCertificate((
        PolynomialStep((), True, 'square', factor=(((), '1'),)),)))
    graph = _graph((('>', 'x', 0), ('<=', ('^', 'x', 'y'), 0)))
    with pytest.warns(RuntimeWarning, match='generated polynomial certificate failed replay'):
        assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


@pytest.mark.parametrize('name,predicate', [
    ('positive_power', 'x>0 && y>0 && x**y<=0'),
    ('rational_power', 'x>=0 && x**(1.0/3.0)<0'),
    ('nested_root', 'x>=0 && sqrt(sqrt(x))**4!=x'),
])
@pytest.mark.parametrize('language', ['en', 'zh'])
def test_semantic_readings_match_complete_text_fixtures(name, predicate, language, text_aligner):
    from pathlib import Path

    report = _expression_report(predicate)
    assert report.reading_status == 'complete'
    expected = Path(__file__).with_name('proof_readings') / ('semantic_%s.%s.txt' % (name, language))
    text_aligner.assert_equal(expected.read_text(encoding='utf-8'),
                              report.reading.to_text(language=language, detail='detailed'))


@pytest.mark.parametrize('premises', [
    (('>', 'y', 0), ('<=', ('*', 'x', 'y'), 0), ('>=', 'x', 0),
     ('>=', 'r', 0), ('=', ('*', 'r', 'r'), 'x'), ('>', 'r', 0)),
    (('<', 'y', 0), ('>=', ('*', 'x', 'y'), 0), ('>', 'x', 0)),
    (('=', ('*', 'x', 'x'), 0), ('<', 'x', 0)),
    (('=', ('*', 'x', 'x'), 0), ('>', 'x', 0)),
])
def test_zero_products_and_zero_squares_have_composable_evidence(premises):
    _certificate(_graph(premises))


def test_cancellation_cannot_use_a_merely_nonnegative_factor():
    graph = _graph((('>=', 'y', 0), ('<=', ('*', 'x', 'y'), 0), ('>', 'x', 0)))
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


def test_frame_equalities_are_substituted_before_nonlinear_definitions():
    graph = _graph((('=', ('*', 'a', 'b'), ('^', 'r', 2)),
                    ('=', ('*', 'c', 'd'), ('^', 's', 2)),
                    ('=', 'a', 'c'), ('=', 'b', 'd'),
                    ('>', ('*', 'a', 'b'), ('*', 'c', 'd'))))
    _certificate(graph)


def test_polynomial_sums_do_not_retain_intermediate_linear_combinations():
    report = _expression_report('x>=0 && sqrt(sqrt(x))**4!=x')
    assert report.reading_status == 'complete'
    certificates = [node.polynomial for node in report.proof.nodes if node.polynomial is not None]
    assert certificates
    for certificate in certificates:
        for step in certificate.steps:
            if step.rule == 'sum':
                assert all(certificate.steps[parent].rule != 'sum' for parent in step.premises)


@pytest.mark.parametrize('rule', ['cancel_positive', 'positive_factor', 'square_zero', 'equality_product'])
@pytest.mark.parametrize('mutation', ['arity', 'weights', 'strict', 'value', 'condition', 'factor'])
def test_compositional_algebra_rejects_changed_evidence(rule, mutation):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial
    from pyfcstm.solver.proof.core import PolynomialCertificate

    premises = {
        'cancel_positive': (('<=', ('*', 'x', 'y'), 0), ('>', 'y', 0), ('>', 'x', 0)),
        'positive_factor': (('>=', 'x', 0), ('>', ('*', 'x', 'y'), 0), ('<=', 'x', 0)),
        'square_zero': (('<=', ('*', 'x', 'x'), 0), ('<', 'x', 0)),
        'equality_product': (('=', 'x', 0), ('>', ('*', 'x', 'x'), 0)),
    }[rule]
    graph = _graph(premises)
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    x = next(term.term_id for term in graph.terms if term.operator == 'x')
    if rule == 'cancel_positive':
        index = search.record({(x,): Fraction(-1)}, False, rule, premises=(0, 1))
        search.combination({index: Fraction(1), 2: Fraction(1)})
    elif rule == 'positive_factor':
        y = next(term.term_id for term in graph.terms if term.operator == 'y')
        index = search.record({(x,): Fraction(1)}, True, rule, premises=(1, 0), factor=(((y,), '1'),))
        search.combination({index: Fraction(1), 2: Fraction(1)})
    elif rule == 'square_zero':
        index = search.record({(x,): Fraction(1)}, False, rule, premises=(0,), factor=(((x,), '1'),))
        search.combination({index: Fraction(1), 1: Fraction(1)})
    else:
        index = search.record({(x, x): Fraction(-1)}, False, rule, premises=(0, 1), factor=(((x,), '-1'),))
        search.combination({index: Fraction(1), 2: Fraction(1)})
    certificate = PolynomialCertificate(tuple(search.steps))
    assert check_polynomial_certificate(graph.node('target'), graph, certificate)
    steps = list(certificate.steps)
    step = steps[index]
    if mutation == 'arity':
        steps[index] = replace(step, premises=())
    elif mutation == 'weights':
        steps[index] = replace(step, weights=('1',))
    elif mutation == 'strict':
        steps[index] = replace(step, strict=not step.strict)
    elif mutation == 'value':
        steps[index] = replace(step, coefficients=(((), '1'),))
    elif mutation == 'factor':
        steps[index] = replace(step, factor=(((), '1'),))
    elif rule in ('cancel_positive', 'positive_factor'):
        domain = graph.node('fact1').conclusion
        graph = replace(graph, terms=tuple(replace(t, operator='>=') if t.term_id == domain else t
                                          for t in graph.terms))
        steps[1] = replace(steps[1], strict=False)
    elif rule == 'square_zero':
        domain = graph.node('fact0').conclusion
        graph = replace(graph, terms=tuple(replace(t, operator='>=') if t.term_id == domain else t
                                          for t in graph.terms))
        steps[0] = replace(steps[0], coefficients=(((x, x), '1'),))
    else:
        steps[index] = replace(step, premises=(0, 0))
    assert not check_polynomial_certificate(graph.node('target'), graph, replace(certificate, steps=tuple(steps)))


@pytest.mark.parametrize('degree', [15, 17, 31, 32])
def test_admitted_power_degrees_do_not_fail_on_oversized_search_candidates(degree):
    _certificate(_graph((('>', 'x', 'y'), ('>=', 'y', 0),
                         ('<=', ('^', 'x', degree), ('^', 'y', degree)))))
