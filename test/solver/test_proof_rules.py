"""Readable inference evidence respects local hypotheses and exact arithmetic."""

from fractions import Fraction

import pytest
import z3

import pyfcstm.solver as solver


pytestmark = pytest.mark.unittest


def test_branch_refutation_closes_hypotheses_before_the_root():
    x, y = z3.Ints('x y')
    query = solver.UnsatQuery('branch', (
        solver.UnsatConstraint('update', (y == z3.If(x >= 0, x + 1, 0),)),
        solver.UnsatConstraint('goal', (y < 0,)),
    ))
    report = solver.explain_unsat(query)
    assert report.scope_check == 'passed'
    assert report.proof.node(report.proof.root_id).open_hypotheses == ()
    lemmas = [node for node in report.proof.nodes if node.rule == 'lemma']
    assert lemmas
    assert all(node.discharged_hypotheses for node in lemmas)
    assert all(node.local_check == 'checked' for node in lemmas)


@pytest.mark.parametrize('sort,bound', [('Int', '1'), ('Real', '1/3')])
def test_arithmetic_certificate_has_exact_weights_and_a_real_contradiction(sort, bound):
    constructor = z3.Int if sort == 'Int' else z3.Real
    x, y = constructor('x'), constructor('y')
    constant = z3.IntVal(bound) if sort == 'Int' else z3.RealVal(bound)
    report = solver.explain_unsat(solver.UnsatQuery('linear', (
        solver.UnsatConstraint('lower', (x >= 0,)),
        solver.UnsatConstraint('step', (y == x + constant,)),
        solver.UnsatConstraint('upper', (y < 0,)),
    )))
    certificates = [node.certificate for node in report.proof.nodes
                    if node.certificate is not None]
    assert certificates
    for certificate in certificates:
        assert all(isinstance(weight, str) for weight in certificate.weights)
        assert Fraction(certificate.constant) >= 0
        assert Fraction(certificate.constant) > 0 or certificate.strict
    assert report.scope_check == 'passed'


def test_unsupported_nonlinear_inference_is_visible_as_a_gap():
    x = z3.Int('x')
    report = solver.explain_unsat(solver.UnsatQuery('nonlinear', (
        solver.UnsatConstraint('square', (x * x == 2,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    assert report.rule_check == 'partial'
    assert any(gap.reason == 'unsupported_rule' for gap in report.gaps)


def test_quantifier_proof_binders_are_preserved_and_not_claimed_checked():
    x = z3.Int('x')
    f = z3.Function('f', z3.IntSort(), z3.IntSort())
    report = solver.explain_unsat(solver.UnsatQuery('quantified', (
        solver.UnsatConstraint('positive', (z3.ForAll(x, f(x) > 0),)),
        solver.UnsatConstraint('negative', (f(0) < 0,)),
    )))
    assert report.proof_status == 'captured'
    assert report.scope_check == 'partial'
    binders = [node for node in report.proof.nodes if node.rule == 'proof-bind']
    assert binders
    assert all(node.bindings and node.conclusion is None for node in binders)
    assert any(gap.reason == 'unsupported_rule' for gap in report.gaps)


def test_asserted_false_is_a_closed_checked_refutation():
    report = solver.explain_unsat(solver.UnsatQuery('false', (
        solver.UnsatConstraint('impossible', (z3.BoolVal(False),)),
    )))
    assert report.scope_check == 'passed'
    assert report.rule_check == 'complete'
    assert report.gaps == ()


def test_valid_scoped_public_graph_can_be_analyzed_without_native_objects():
    from pyfcstm.solver.proof import ProofGraph, ProofInput, ProofNode, ProofTerm
    from pyfcstm.solver.proof_rules import analyze_proof

    graph = ProofGraph('manual', 'n2', (
        ProofNode('n0', 'hypothesis', (), 'false'),
        ProofNode('n1', 'lemma', ('n0',), 'not-false'),
        ProofNode('n2', 'asserted', (), 'false', input_occurrences=('i0',)),
    ), (
        ProofTerm('false', 'literal', 'Bool', 'false', value='false'),
        ProofTerm('not-false', 'application', 'Bool', 'not', ('false',)),
    ), (ProofInput('i0', 'impossible', 0, 'false', False),))
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'passed'
    assert analysis.graph.node('n1').discharged_hypotheses == ('n0',)


def test_escaping_hypothesis_is_rejected_through_public_evidence_analysis():
    from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofTerm
    from pyfcstm.solver.proof_rules import analyze_proof

    graph = ProofGraph('manual', 'n0', (
        ProofNode('n0', 'hypothesis', (), 'false'),
    ), (ProofTerm('false', 'literal', 'Bool', 'false', value='false'),), ())
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'failed'
    assert any(gap.reason == 'open_hypotheses' for gap in analysis.gaps)


def _certificate_graph(expressions, weights, conclusion=None):
    """Construct caller-owned evidence for a proposed local linear certificate."""
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofNode, ProofParameter

    facts = tuple(expressions) + ((conclusion,) if conclusion is not None else ())
    query = solver.UnsatQuery('candidate-certificate', tuple(
        solver.UnsatConstraint('fact%d' % index, (expression,)) for index, expression in enumerate(facts)
    ) + (solver.UnsatConstraint('false', (z3.BoolVal(False, ctx=expressions[0].ctx),)),))
    graph = solver.explain_unsat(query).proof
    nodes = tuple(ProofNode('a%d' % index, 'asserted', (), graph.inputs[index].term_id,
                            input_occurrences=(graph.inputs[index].occurrence_id,))
                  for index in range(len(expressions)))
    claim = graph.inputs[len(expressions)].term_id
    params = (ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'farkas')) + tuple(
        ProofParameter('rational', str(weight)) for weight in weights)
    root = ProofNode('combination', 'th-lemma', tuple(node.node_id for node in nodes), claim, parameters=params)
    return replace(graph, root_id=root.node_id, nodes=nodes + (root,))


@pytest.mark.parametrize('case,expected', [
    ('unary', 'checked'), ('difference', 'checked'), ('coercion', 'checked'),
    ('constant_product', 'checked'), ('negative_equality', 'checked'),
    ('integer_strict', 'checked'), ('nested_nonlinear_sum', 'unsupported'),
    ('nested_nonlinear_product', 'unsupported'), ('boolean_equality', 'unsupported'),
    ('uninterpreted_predicate', 'unsupported'), ('disequality', 'unsupported'),
    ('missing_weight', 'unsupported'), ('nonconstant_sum', 'invalid'),
    ('satisfiable_interval', 'invalid'), ('nonstrict_zero', 'invalid'),
    ('zero_weights', 'invalid'), ('single_clause', 'checked'),
])
def test_local_certificate_checks_the_given_premises_not_the_full_unsat_query(case, expected):
    from pyfcstm.solver.proof_rules import analyze_proof

    x, y = z3.Reals('x y')
    i = z3.Int('i')
    p, q = z3.Bools('p q')
    predicate = z3.Function('<', z3.RealSort(), z3.RealSort(), z3.BoolSort())
    cases = {
        'unary': ((x >= 0, -x > 0), (1, 1), None),
        'difference': ((x - y >= 1, y - x >= 0), (1, 1), None),
        'coercion': ((z3.ToReal(i) <= 0, z3.ToReal(i) > 0), (1, 1), None),
        'constant_product': (((z3.RealVal(2) * 3) * x <= 0, x >= 1), (1, 6), None),
        'negative_equality': ((x == 1, x <= 0), (-1, 1), None),
        'integer_strict': ((i > 0, i < 1), (1, 1), None),
        'nested_nonlinear_sum': ((x * x + 1 <= 0, x >= 1), (1, 1), None),
        'nested_nonlinear_product': ((2 * (x * x) <= 0, x >= 1), (1, 1), None),
        'boolean_equality': ((p == q,), (1,), None),
        'uninterpreted_predicate': ((predicate(x, y),), (1,), None),
        'disequality': ((z3.Not(x == y),), (1,), None),
        'missing_weight': ((x > 0, x <= 0), (1,), None),
        'nonconstant_sum': ((x >= 0, y < 0), (1, 1), None),
        'satisfiable_interval': ((x >= 0, x <= 1), (1, 1), None),
        'nonstrict_zero': ((x >= 0, x <= 0), (1, 1), None),
        'zero_weights': ((x < 0, x >= 0), (0, 0), None),
        'single_clause': ((x < 0,), (1, 1), z3.Not(x >= 0)),
    }
    expressions, weights, conclusion = cases[case]
    graph = _certificate_graph(expressions, weights, conclusion)
    analysis = analyze_proof(graph)
    root = analysis.graph.node(graph.root_id)
    assert root.local_check == expected
    if expected == 'checked':
        assert root.certificate is not None
        assert root.certificate.weights == tuple(str(weight) for weight in weights)
    else:
        assert root.certificate is None


def test_a_boolean_symbol_named_false_is_not_a_refutation():
    from pyfcstm.solver.proof import ProofGraph, ProofInput, ProofNode, ProofTerm
    from pyfcstm.solver.proof_rules import analyze_proof

    graph = ProofGraph('caller', 'n', (
        ProofNode('n', 'asserted', (), 'symbol', input_occurrences=('i',)),
    ), (ProofTerm('symbol', 'constant', 'Bool', 'false', value='false',
                  operator_kind='uninterpreted'),),
        (ProofInput('i', 'assumption', 0, 'symbol', False),))
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'failed'
    assert analysis.gaps[-1].reason == 'non_false_root'


def test_an_opaque_arithmetic_term_can_cancel_without_interpreting_its_operator():
    from pyfcstm.solver.proof_rules import analyze_proof

    x = z3.Real('x')
    graph = _certificate_graph((x / 2 >= 1, x / 2 <= 0), (1, 1))
    analysis = analyze_proof(graph)
    assert analysis.graph.node(graph.root_id).local_check == 'checked'
    assert analysis.graph.node(graph.root_id).certificate.constant == '1'


def test_a_proof_binder_without_a_false_root_is_not_a_refutation():
    from pyfcstm.solver.proof import ProofGraph, ProofNode
    from pyfcstm.solver.proof_rules import analyze_proof

    graph = ProofGraph('binder', 'root', (ProofNode('root', 'proof-bind', (), None),), (), ())
    analysis = analyze_proof(graph)
    assert analysis.scope_check == 'failed'
    assert analysis.gaps[-1].reason == 'non_false_root'


def test_a_lemma_cannot_discharge_an_unrelated_conclusion():
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofNode
    from pyfcstm.solver.proof_rules import analyze_proof

    x = z3.Real('x')
    graph = _certificate_graph((x > 0, x <= 0), (1, 1))
    assumption = ProofNode('hyp', 'hypothesis', (), graph.inputs[0].term_id)
    bad_lemma = ProofNode('lemma', 'lemma', ('hyp',), graph.inputs[1].term_id)
    graph = replace(graph, root_id='lemma', nodes=graph.nodes + (assumption, bad_lemma))
    analysis = analyze_proof(graph)
    assert analysis.graph.node('lemma').local_check == 'invalid'
    assert analysis.graph.node('lemma').open_hypotheses == ('hyp',)
    assert analysis.scope_check == 'failed'


def test_algebraic_bounds_do_not_claim_a_rational_certificate():
    from pyfcstm.solver.proof_rules import analyze_proof

    x = z3.Real('x')
    graph = _certificate_graph((x >= z3.simplify(z3.Sqrt(2)), x < 0), (1, 1))
    analysis = analyze_proof(graph)
    assert analysis.graph.node('combination').local_check == 'unsupported'
