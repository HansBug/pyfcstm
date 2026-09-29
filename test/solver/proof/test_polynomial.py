"""Portable local polynomial witnesses, exact signs and hostile evidence changes."""

from dataclasses import replace
from importlib.util import find_spec

import pytest

from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.proof.core import ProofGraph, ProofNode, ProofTerm

pytestmark = pytest.mark.unittest


def _graph(premises, conclusion=False, prefix='p'):
    terms, cache = [], {}

    def term(expression):
        key = repr(expression)
        if key in cache:
            return cache[key]
        if isinstance(expression, tuple):
            op, operands = expression[0], expression[1:]
            args = tuple(term(child) for child in operands)
            sort = 'Bool' if op in ('not', 'or', '<=', '>=', '<', '>', '=') else 'Real'
            result = ProofTerm(prefix + str(len(terms)), 'application', sort, op, args)
        elif isinstance(expression, bool):
            result = ProofTerm(prefix + str(len(terms)), 'literal', 'Bool', str(expression).lower(), value=str(expression).lower())
        elif isinstance(expression, int) or isinstance(expression, str) and '/' in expression:
            result = ProofTerm(prefix + str(len(terms)), 'literal', 'Real', 'Real', value=str(expression))
        else:
            result = ProofTerm(prefix + str(len(terms)), 'constant', 'Real', expression, value=expression,
                               operator_kind='uninterpreted')
        cache[key] = result.term_id
        terms.append(result)
        return result.term_id

    nodes = [ProofNode('fact' + str(index), 'hypothesis', (), term(premise))
             for index, premise in enumerate(premises)]
    target = ProofNode('target', 'th-lemma', tuple(node.node_id for node in nodes), term(conclusion))
    return ProofGraph('local', 'target', tuple(nodes) + (target,), tuple(terms), ())


def _certificate(graph):
    assert find_spec('pyfcstm.solver.proof.polynomial') is not None, 'local polynomial certificate reconstruction is missing'
    from pyfcstm.solver.proof.polynomial import polynomial_certificate, check_polynomial_certificate

    node = graph.node(graph.root_id)
    certificate = polynomial_certificate(node, graph, SolveBudget(None))
    assert certificate is not None
    assert check_polynomial_certificate(node, graph, certificate)
    pending, used = [len(certificate.steps) - 1], set()
    while pending:
        index = pending.pop()
        if index not in used:
            used.add(index)
            pending.extend(certificate.steps[index].premises)
    assert used == set(range(len(certificate.steps)))
    return certificate


def test_quartic_local_contradiction_has_a_replayable_square_witness():
    certificate = _certificate(_graph((('<=', ('*', 'x', 'x', 'x', 'x'), -1),)))
    assert [step.rule for step in certificate.steps] == ['input', 'square', 'sum']


@pytest.mark.parametrize('premises', [
    (('<', ('+', ('*', 'x', 'x'), ('*', 'y', 'y'), ('*', -2, 'x', 'y')), 0),),
    (('>', 'x', 'y'), ('<=', ('*', 'x', 'x', 'x'), ('*', 'y', 'y', 'y'))),
    (('>=', 'x', 'y'), ('>', 'y', 0), ('<', ('*', 'x', 'x'), ('*', 'y', 'y'))),
    (('>', 'x', 'y'), ('>=', 'y', 0), ('<=', ('^', 'x', 2), ('^', 'y', 2))),
    (('>', 'c', ('+', 'a', 'b')), ('>', 'a', 0), ('>=', 'b', 0), ('>=', 'd', 'c'),
     ('<=', 'x', ('^', 'a', 2)), ('<=', 'y', ('^', 'b', 2)),
     ('>=', ('+', 'u', 'v'), ('^', 'd', 2)), ('>=', 'x', 'u'), ('>=', 'y', 'v')),
    (('<', 'c', 0), ('>', 'c', ('+', 'a', 'b')), ('>=', 'b', 0),
     ('>=', 'x', ('^', 'a', 2)), ('>=', 'y', 0), ('<=', ('+', 'x', 'y'), ('^', 'c', 2))),
    (('=', 'a', 'b'), ('>', 'a', 0), ('<=', 'b', 'c'), ('>', 'c', 0),
     ('<=', 'x', ('^', 'b', 2)), ('>=', 'y', ('^', 'c', 2)), ('>', 'x', 'y')),
])
@pytest.mark.parametrize('prefix', ['ordinary', 'renamed'])
def test_generic_polynomial_sign_and_order_certificates(premises, prefix):
    certificate = _certificate(_graph(premises, prefix=prefix))
    assert certificate.steps[-1].rule == 'sum'


def test_negated_local_clause_is_the_only_temporary_assumption_source():
    graph = _graph((), ('or', ('<=', 'x', 'y'), ('>', ('^', 'x', 3), ('^', 'y', 3))))
    certificate = _certificate(graph)
    assert all(step.negated for step in certificate.steps if step.rule == 'input')


@pytest.mark.parametrize('mutation', ['operator_kind', 'strict', 'missing_input', 'factor', 'negative_weight', 'forward', 'unknown_rule'])
def test_changed_polynomial_evidence_is_rejected(mutation):
    from pyfcstm.solver.proof.polynomial import check_polynomial_certificate

    graph = _graph((('<', ('+', ('*', 'x', 'x'), ('*', 'y', 'y'), ('*', -2, 'x', 'y')), 0),))
    certificate = _certificate(graph)
    steps = list(certificate.steps)
    if mutation == 'operator_kind':
        graph = replace(graph, terms=tuple(replace(term, operator_kind='uninterpreted')
                                          if term.operator == '*' else term for term in graph.terms))
    elif mutation == 'strict':
        steps[1] = replace(steps[1], strict=True)
    elif mutation == 'missing_input':
        graph = replace(graph, nodes=tuple(replace(node, parents=()) if node.node_id == 'target' else node
                                          for node in graph.nodes))
    elif mutation == 'factor':
        steps[1] = replace(steps[1], factor=(((), '1'),))
    elif mutation == 'negative_weight':
        steps[-1] = replace(steps[-1], weights=('-1',) + steps[-1].weights[1:])
    elif mutation == 'forward':
        steps[-1] = replace(steps[-1], premises=(len(steps),) + steps[-1].premises[1:])
    else:
        steps[1] = replace(steps[1], rule='trust')
    assert not check_polynomial_certificate(graph.node('target'), graph, replace(certificate, steps=tuple(steps)))


@pytest.mark.parametrize('premises', [
    (('>=', 'x', 0), ('>=', 'y', 0), ('>=', ('*', 'x', 'y'), 0)),
    (('=', 'x', 'y'), ('<=', ('^', 'x', 2), 3), ('>=', ('^', 'y', 2), 2)),
    (('<', ('^', 'x', '1/2'), 0),),
    (('=', ('*', 'x', 'y'), 5), ('>', 'x', 1), ('>', 'y', 1)),
])
def test_satisfiable_real_constraints_produce_no_polynomial_contradiction(premises):
    from pyfcstm.solver.proof.polynomial import polynomial_certificate

    graph = _graph(premises)
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


@pytest.mark.parametrize('premises', [
    (('>=', 'x', 1), ('>=', 'y', 1), ('<=', ('^', 'x', 2), ('^', 'y', 2)), ('>', 'x', 'y')),
    (('>', ('-', 'x', 'y'), 0), ('<=', ('^', 'x', 3), ('^', 'y', 3))),
    (('not', ('>=', ('^', ('uminus', 'x'), 4), 0)),),
    (('>', ('-', 'x'), 1), ('<=', ('-', 'x'), 0)),
    (('>', 'y', 'x'), ('<=', ('^', 'y', 3), ('^', 'x', 3))),
])
def test_offsets_unary_operators_and_reversed_cubic_order(premises):
    _certificate(_graph(premises))


@pytest.mark.parametrize('premises', [
    (('>', 'x', 'y'), ('>', ('^', 'x', 3), ('^', 'y', 3))),
    (('>', ('^', 'x', 3), ('^', 'y', 3)),),
    (('not', ('=', 'x', 'y')),),
    (('>', ('^', 'x', 'y'), 0),),
    (('>', ('^', 'x', 0), 0),),
])
def test_unknown_or_satisfiable_power_relationships_are_not_certified(premises):
    from pyfcstm.solver.proof.polynomial import polynomial_certificate

    graph = _graph(premises)
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


def test_cast_preserves_integer_polynomial_identity():
    graph = _graph((('<', ('*', ('to_real', 'i'), ('to_real', 'i')), 0),))
    graph = replace(graph, terms=tuple(replace(term, sort='Int') if term.operator == 'i' else term
                                      for term in graph.terms))
    _certificate(graph)


@pytest.mark.parametrize('mutation', ['unknown_atom', 'zero', 'duplicate', 'unsorted', 'boolean_atom',
                                     'bad_fraction', 'zero_denominator', 'bad_shape', 'metadata',
                                     'nonboolean_strict', 'sum_arity', 'sum_value', 'sum_strict'])
def test_malformed_sparse_polynomials_cannot_be_replayed(mutation):
    from pyfcstm.solver.proof.polynomial import check_polynomial_certificate

    graph = _graph((('<', ('+', ('*', 'x', 'x'), ('*', 'y', 'y'), ('*', -2, 'x', 'y')), 0),))
    certificate = _certificate(graph)
    steps = list(certificate.steps)
    first = steps[0]
    if mutation == 'unknown_atom':
        steps[0] = replace(first, coefficients=((('missing',), '1'),))
    elif mutation == 'zero':
        steps[0] = replace(first, coefficients=(((), '0'),))
    elif mutation == 'duplicate':
        steps[0] = replace(first, coefficients=first.coefficients + first.coefficients)
    elif mutation == 'unsorted':
        pair = next(m for m, c in first.coefficients if len(set(m)) == 2)
        steps[0] = replace(first, coefficients=((tuple(reversed(pair)), '1'),))
    elif mutation == 'boolean_atom':
        steps[0] = replace(first, coefficients=(((graph.node('target').conclusion,), '1'),))
    elif mutation in ('bad_fraction', 'zero_denominator', 'bad_shape'):
        value = 'bad' if mutation == 'bad_fraction' else '1/0' if mutation == 'zero_denominator' else None
        steps[0] = replace(first, coefficients=(((), value),))
    elif mutation == 'metadata':
        steps[1] = replace(steps[1], term_id=first.term_id)
    elif mutation == 'nonboolean_strict':
        steps[0] = replace(first, strict=1)
    elif mutation == 'sum_arity':
        steps[-1] = replace(steps[-1], weights=())
    elif mutation == 'sum_value':
        steps[-1] = replace(steps[-1], coefficients=(((), '1'),))
    else:
        steps[-1] = replace(steps[-1], strict=not steps[-1].strict)
    assert not check_polynomial_certificate(graph.node('target'), graph, replace(certificate, steps=tuple(steps)))


@pytest.mark.parametrize('mutation', ['arity', 'strict', 'value'])
def test_product_rule_needs_both_proven_factors_and_exact_sign(mutation):
    from pyfcstm.solver.proof.polynomial import check_polynomial_certificate

    graph = _graph((('>', 'x', 'y'), ('<=', ('^', 'x', 3), ('^', 'y', 3))))
    certificate = _certificate(graph)
    steps = list(certificate.steps)
    index = next(i for i, step in enumerate(steps) if step.rule == 'product')
    if mutation == 'arity':
        steps[index] = replace(steps[index], premises=steps[index].premises[:1])
    elif mutation == 'strict':
        steps[index] = replace(steps[index], strict=not steps[index].strict)
    else:
        steps[index] = replace(steps[index], coefficients=(((), '1'),))
    assert not check_polynomial_certificate(graph.node('target'), graph, replace(certificate, steps=tuple(steps)))


def test_missing_conclusion_and_unsupported_literals_do_not_create_assumptions():
    from pyfcstm.solver.proof.core import PolynomialCertificate
    from pyfcstm.solver.proof.polynomial import polynomial_certificate, check_polynomial_certificate

    for graph in (_graph((True,)), _graph((('=', True, False),)), _graph((('<=', 'x', 1),), ('=', 'x', 0))):
        assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None
    graph = _graph((('<=', 'x', 0),))
    term = graph.term(graph.node('fact0').conclusion)
    opaque = replace(graph, terms=tuple(replace(item, operator_kind='uninterpreted') if item == term else item
                                        for item in graph.terms))
    assert polynomial_certificate(opaque.node('target'), opaque, SolveBudget(None)) is None
    missing = replace(graph.node('target'), conclusion=None)
    assert polynomial_certificate(missing, graph, SolveBudget(None)) is None
    assert not check_polynomial_certificate(missing, graph, PolynomialCertificate(()))
    missing_parent = replace(graph.node('fact0'), conclusion=None)
    absent = replace(graph, nodes=(missing_parent, graph.node('target')))
    assert polynomial_certificate(absent.node('target'), absent, SolveBudget(None)) is None


def test_deep_arithmetic_normalization_is_iterative_and_algebraic_values_are_atoms():
    graph = _graph((('<', ('^', 'x', 4), 0),))
    x = next(term for term in graph.terms if term.operator == 'x')
    chain = tuple(ProofTerm('negative' + str(index), 'application', 'Real', 'uminus',
                            (x.term_id if index == 0 else 'negative' + str(index - 1),))
                  for index in range(1200))
    graph = replace(graph, terms=tuple(replace(term, arguments=('negative1199', term.arguments[1]))
                                      if term.operator == '^' else term for term in graph.terms) + chain)
    _certificate(graph)
    algebraic = replace(graph, terms=tuple(replace(term, kind='algebraic', operator='Root',
                                                  value='(root-obj (+ (^ x 2) (- 2)) 2)', operator_kind='builtin')
                                          if term == x else term for term in graph.terms))
    _certificate(algebraic)


def test_sparse_expansion_and_shared_deadline_are_enforced():
    from pyfcstm.solver.budget import BudgetExpired
    from pyfcstm.solver.proof.polynomial import polynomial_certificate

    graph = _graph((('<', ('*', ('^', 'x', 32), 'x'), 0),))
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None
    budget = SolveBudget(1)
    budget.deadline = 0
    with pytest.raises(BudgetExpired, match='polynomial'):
        polynomial_certificate(graph.node('target'), graph, budget)


def test_corrupted_unary_child_and_incomplete_power_are_not_arithmetic_axioms():
    from pyfcstm.solver.proof.polynomial import polynomial_certificate, check_polynomial_certificate

    graph = _graph((('<', ('^', ('uminus', 'x'), 4), 0),))
    certificate = _certificate(graph)
    bad_sort = replace(graph, terms=tuple(replace(term, sort='Bool') if term.operator == 'x' else term
                                         for term in graph.terms))
    assert not check_polynomial_certificate(bad_sort.node('target'), bad_sort, certificate)
    incomplete = replace(graph, terms=tuple(replace(term, arguments=term.arguments[:1])
                                           if term.operator == '^' else term for term in graph.terms))
    assert polynomial_certificate(incomplete.node('target'), incomplete, SolveBudget(None)) is None


def test_dense_elimination_stops_without_claiming_an_infeasible_system():
    from pyfcstm.solver.proof.polynomial import polynomial_certificate

    # x=y=0 satisfies every row. Both variables have 65 positive and 65 negative
    # occurrences, so either first elimination would exceed the sparse row bound.
    premises = tuple(('>=', ('+', ('*', sign * index, 'x'), ('*', sign * index * index, 'y')), -1)
                     for sign in (1, -1) for index in range(1, 66))
    graph = _graph(premises)
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None
