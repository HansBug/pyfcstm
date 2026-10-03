"""Integer lattices survive casts without assigning integrality to real atoms."""

from fractions import Fraction

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.proof.arithmetic import integer_lattice, strengthen_bound

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('expression,expected', [
    (lambda i, x: i, ('0', '1')),
    (lambda i, x: x, None),
    (lambda i, x: z3.RealVal('1/3'), ('1/3', '0')),
    (lambda i, x: z3.IntVal(-3), ('-3', '0')),
    (lambda i, x: z3.ToReal(i), ('0', '1')),
    (lambda i, x: z3.ToReal(i) / 2, None),
    (lambda i, x: z3.RealVal('1/2') * z3.ToReal(i), ('0', '1/2')),
    (lambda i, x: z3.RealVal('1/3') + z3.RealVal('1/2') * z3.ToReal(i), ('1/3', '1/2')),
    (lambda i, x: -(z3.RealVal('1/3') + z3.ToReal(i)), ('-1/3', '1')),
    (lambda i, x: z3.ToReal(i) - z3.RealVal('1/3'), ('-1/3', '1')),
    (lambda i, x: z3.ToReal(i) + x, None),
    (lambda i, x: z3.ToReal(i) * z3.ToReal(i), ('0', '1')),
    (lambda i, x: (z3.ToReal(i) + z3.RealVal('1/2')) * (z3.ToReal(i) + z3.RealVal('1/3')), ('1/6', '1/6')),
    (lambda i, x: z3.ToReal(z3.ToInt(x)), ('0', '1')),
    (lambda i, x: z3.Function('f', z3.RealSort(), z3.RealSort())(x), None),
])
def test_exported_expression_lattice_is_exact_or_explicitly_unknown(expression, expected):
    i, x = z3.Int('i'), z3.Real('x')
    value = expression(i, x)
    report = explain_unsat(UnsatQuery('lattice', (
        UnsatConstraint('term', (value == value,)),
        UnsatConstraint('false', (z3.BoolVal(False),)),
    )))
    graph = report.proof
    term_id = graph.term(graph.inputs[0].term_id).arguments[0]
    lattice = integer_lattice(term_id, graph)
    assert lattice == (None if expected is None else tuple(Fraction(v) for v in expected))
    cache = {}
    assert integer_lattice(term_id, graph, cache) == lattice
    assert integer_lattice(term_id, graph, cache) == lattice


@pytest.mark.parametrize('relation,constant,expected', [
    ('lt', '0', ('1/2', 'le')),
    ('le', '0', ('0', 'le')),
    ('lt', '1/3', ('1/2', 'le')),
    ('le', '1/3', ('1/2', 'le')),
    ('lt', '-1/3', ('0', 'le')),
    ('le', '-1/3', ('0', 'le')),
    ('eq', '1/3', ('1/3', 'eq')),
])
def test_half_integer_bounds_round_in_the_correct_direction(relation, constant, expected):
    i = z3.Int('i')
    graph = explain_unsat(UnsatQuery('lattice', (
        UnsatConstraint('term', (i == i,)),
        UnsatConstraint('false', (z3.BoolVal(False),)),
    ))).proof
    term_id = graph.term(graph.inputs[0].term_id).arguments[0]
    result = strengthen_bound({term_id: Fraction('1/2')}, Fraction(constant), relation, graph)
    assert result == (Fraction(expected[0]), expected[1])


@pytest.mark.parametrize('formula', [
    lambda x: z3.And(x >= 0, x < z3.RealVal('1/3')),
    lambda x: z3.And(x < 0, z3.ToReal(z3.ToInt(x)) < 0),
    lambda x: z3.And(x > 0, -z3.ToReal(z3.ToInt(-x)) > 0),
    lambda x: z3.And(z3.ToReal(z3.ToInt(x)) < z3.RealVal('1/2'), x == 0),
])
def test_real_and_rounding_sat_controls_never_produce_a_refutation(formula):
    report = explain_unsat(UnsatQuery('sat_control', (
        UnsatConstraint('condition', (formula(z3.Real('x')),)),
    )))
    assert report.solver_status == 'sat'
    assert report.proof is None


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_rounding_proof_text_explains_the_exact_integer_step(language, text_aligner):
    import json
    from pathlib import Path
    from pyfcstm.solver import UnsatReport

    fixtures = Path(__file__).parent / 'proof_readings'
    report = UnsatReport.from_canonical(json.loads((fixtures / 'rounding.json').read_text('utf-8')))
    expected = (fixtures / ('rounding.%s.txt' % language)).read_text('utf-8')
    text_aligner.assert_equal(expected, report.reading.to_text(language, 'detailed'))
