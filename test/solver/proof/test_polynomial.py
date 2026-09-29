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


def test_sign_normalization_adds_to_an_existing_constant_weight(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 2),))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    unit = search.square({(): Fraction(1)})
    # This is a valid coefficient witness: (x-2) + 1 + (-x) = -1.
    # The target x needs another unit; it must not overwrite the existing one.
    monkeypatch.setattr(polynomial, '_eliminate', lambda rows, budget, solver: {
        0: Fraction(1), unit: Fraction(1), len(search.facts): Fraction(1)})
    x = next(term.term_id for term in graph.terms if term.operator == 'x')
    index = search.sign({(x,): Fraction(1)})
    assert search.facts[index][0] == {(x,): Fraction(1)}


def test_an_existing_strict_fact_is_reused_without_coefficient_search(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>', 'x', 0),))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    calls = []

    def no_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_eliminate', no_witness)
    x = next(term.term_id for term in graph.terms if term.operator == 'x')
    assert search.sign({(x,): Fraction(1)}) == 0
    assert calls == []


def test_existing_nonstrict_fact_is_reused_after_checking_for_a_stronger_sign(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 0),))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    calls = []

    def no_strict_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_eliminate', no_strict_witness)
    x = next(term.term_id for term in graph.terms if term.operator == 'x')
    assert search.sign({(x,): Fraction(1)}) == 0
    assert len(calls) == 1


def test_positive_constants_cannot_form_a_linear_contradiction(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    calls = []

    def no_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_solve_weights', no_witness)
    rows = [({('x',): Fraction(i), ('y',): Fraction(i * i), (): Fraction(1)},
             bool(i % 2), {i: Fraction(1)}) for i in range(1, 36)]
    assert polynomial._eliminate(rows, SolveBudget(None), object()) is None
    assert calls == []


def test_zero_constant_refutations_discard_positive_constant_rows(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    calls = []

    def no_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_solve_weights', no_witness)
    rows = [({('x',): Fraction(i), ('y',): Fraction(i * i), (): Fraction(1)},
             False, {i: Fraction(1)}) for i in range(1, 36)]
    rows.append(({('x',): Fraction(1)}, True, {36: Fraction(1)}))
    assert polynomial._eliminate(rows, SolveBudget(None), object()) is None
    assert calls == []


def test_one_sided_columns_remove_impossible_weights_to_a_fixed_point(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    calls = []

    def no_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_solve_weights', no_witness)
    # Each positive tail forces its weight to zero; that exposes the previous
    # column. Negative constants prevent the constant-only shortcut applying.
    rows = [({('x%d' % i,): Fraction(-1), ('x%d' % (i + 1),): Fraction(1),
              (): Fraction(-1)}, False, {i: Fraction(1)}) for i in range(40)]
    assert polynomial._eliminate(rows, SolveBudget(None), object()) is None
    assert calls == []


@pytest.mark.parametrize('premises,reason,detail', [
    ((('>=', 'x', 0),), 'proof_search_exhausted', 'bounded polynomial search found no certificate'),
    ((('<', ('*', ('^', 'x', 32), 'x'), 0),), 'proof_search_limit', 'polynomial expansion limit'),
])
def test_polynomial_search_records_why_evidence_is_unavailable(premises, reason, detail):
    from pyfcstm.solver.proof.polynomial import polynomial_certificate
    from pyfcstm.solver.proof import ProofGap

    graph = _graph(premises)
    diagnostics = []
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None), diagnostics=diagnostics) is None
    assert diagnostics == [ProofGap(reason, 'target', detail)]


def test_proof_analysis_preserves_local_search_diagnostics():
    from pyfcstm.solver.proof import ProofParameter, analyze_proof, ProofGap

    graph = _graph((('>=', ('*', ('^', 'x', 32), 'x'), 0),))
    graph = replace(graph, nodes=graph.nodes[:-1] + (replace(
        graph.nodes[-1], parameters=(ProofParameter('symbol', 'arith'),)),))
    analysis = analyze_proof(graph)
    assert ProofGap('proof_search_limit', 'target', 'polynomial expansion limit') in analysis.gaps
    assert not any(gap.reason == 'unsupported_rule' for gap in analysis.gaps)


def test_dense_pairing_uses_native_coefficients_before_cartesian_expansion(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    calls = []

    def no_witness(rows, budget, solver):
        calls.append(rows)
        return None

    monkeypatch.setattr(polynomial, '_solve_weights', no_witness)
    rows = [({('x',): Fraction(sign), ('y',): Fraction(sign * i),
              (): Fraction(-1 if sign > 0 else 2)}, False, {index: Fraction(1)})
            for index, (sign, i) in enumerate((sign, i) for sign in (1, -1) for i in range(1, 10))]
    assert polynomial._eliminate(rows, SolveBudget(None), object()) is None
    assert len(calls) == 1


def test_frame_alias_equalities_are_eliminated_before_native_weight_search(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    monkeypatch.setattr(polynomial, '_solve_weights', lambda rows, budget, solver: None)
    equations = [{('x0',): Fraction(1)}] + [
        {('x%d' % i,): Fraction(1), ('x%d' % (i - 1),): Fraction(-1)} for i in range(1, 20)]
    rows = [(polynomial._scale(equation, sign), False, {2 * i + offset: Fraction(1)})
            for i, equation in enumerate(equations) for offset, sign in enumerate((1, -1))]
    rows.append(({('x19',): Fraction(1)}, True, {40: Fraction(1)}))
    weights = polynomial._eliminate(rows, SolveBudget(None), object())
    assert weights is not None
    assert weights[40] > 0
    result = {}
    for index, weight in weights.items():
        assert weight >= 0
        result = polynomial._add(result, rows[index][0], weight)
    assert result == {}


def test_product_search_does_not_generate_scalar_copies_of_existing_bounds():
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 2), ('<=', 'x', 3)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    assert search.compose_products() is None
    for step in search.steps:
        if step.rule == 'product':
            assert any(search.facts[step.premises[1]][0])


def test_zero_assignment_witness_skips_impossible_polynomial_refutation_search(monkeypatch):
    from pyfcstm.solver.proof import polynomial

    graph = _graph(tuple(('>=', ('+', ('*', i, 'x'), ('*', i * i, 'y')), -1)
                         for i in range(-20, 21) if i))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))

    def unexpected_search(self):
        pytest.fail('the zero assignment already satisfies these polynomial premises')

    monkeypatch.setattr(polynomial._Search, 'deduce', unexpected_search)
    assert search.generate() is None


@pytest.mark.parametrize('strict', [False, True])
def test_native_combination_weights_produce_replayable_large_cycle_certificates(strict):
    # Forty linked bounds exceed the sparse row threshold. A SAT coefficient
    # model must supply the witness; its exact sum is checked independently.
    premises = tuple(('>' if strict and i == 0 else '>=', 'x%d' % i,
                      'x%d' % ((i + 1) % 40) if strict else
                      ('+', 'x%d' % ((i + 1) % 40), 1)) for i in range(40))
    _certificate(_graph(premises))


def test_a_redundant_zero_bound_does_not_change_satisfiable_sign_conditions():
    from pyfcstm.solver.proof.polynomial import polynomial_certificate

    graph = _graph((('>=', 0, 0), ('>', 'x', 0), ('<', 'y', 0)))
    assert polynomial_certificate(graph.node('target'), graph, SolveBudget(None)) is None


def test_constant_contradictions_are_not_used_as_equality_rewrite_divisors():
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 1, 0), ('>=', -1, 0)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    certificate = search.compose_equalities()
    assert certificate is not None
    assert polynomial.check_polynomial_certificate(graph.node('target'), graph, certificate)


@pytest.mark.parametrize('square', [False, True])
def test_product_candidate_stages_return_independently_checked_certificates(square, monkeypatch):
    from pyfcstm.solver.proof import polynomial

    premises = ((('>', 'x', 0), ('<=', ('*', 'x', 'x'), 0)) if square else
                (('>=', 'x', 0), ('>=', 'y', 0), ('<', ('*', 'x', 'y'), 0),
                 ('>=', ('*', 'x', 'x'), 0)))
    graph = _graph(premises)
    finish = polynomial._Search.finish

    def finish_after_candidate(self):
        step = self.steps[-1]
        if step.rule == 'product' and (step.premises[0] == step.premises[1]) == square:
            return finish(self)
        return None

    # Isolate the candidate producers from earlier shortcuts. The resulting
    # evidence must still replay against the unchanged original premises.
    monkeypatch.setattr(polynomial._Search, 'finish', finish_after_candidate)
    monkeypatch.setattr(polynomial._Search, 'cancel_products', lambda self: None)
    monkeypatch.setattr(polynomial._Search, 'compose_equalities', lambda self: None)
    _certificate(graph)


def test_linear_combinations_do_not_invalidate_known_sign_search_results(monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 0), ('<=', 'y', 2)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    y = next(term.term_id for term in graph.terms if term.operator == 'y')
    target = {(y,): Fraction(1)}
    assert search.sign(target) is None
    search.combination({0: Fraction(2)})

    def redundant_search(rows, budget, solver):
        pytest.fail('a linear consequence cannot change feasibility of the cached sign query')

    monkeypatch.setattr(polynomial, '_eliminate', redundant_search)
    assert search.sign(target) is None


@pytest.mark.parametrize('connected', [False, True])
def test_new_products_invalidate_only_connected_sign_queries(connected, monkeypatch):
    from fractions import Fraction
    from pyfcstm.solver.proof import polynomial

    premises = (('>=', 'x', 0), ('>=', 'z', 0), ('<=', 'y', 2))
    if connected:
        premises += (('>=', 'y', ('*', 'x', 'z')),)
    graph = _graph(premises)
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(None))
    atoms = {term.operator: term.term_id for term in graph.terms if term.kind == 'constant'}
    target = {(atoms['y'],): Fraction(1)}
    assert search.sign(target) is None
    search.product(search.sign({(atoms['x'],): Fraction(1)}),
                   search.sign({(atoms['z'],): Fraction(1)}))
    if connected:
        index = search.sign(target)
        assert index is not None
        assert search.facts[index][0] == target
    else:
        def redundant_search(rows, budget, solver):
            pytest.fail('the new product has no linear dependency on the cached target')

        monkeypatch.setattr(polynomial, '_eliminate', redundant_search)
        assert search.sign(target) is None


def test_joint_product_search_records_only_the_selected_witness():
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 0), ('>=', 'y', 0), ('<', ('*', 'x', 'y'), 0),
                    ('>=', 'unused_a', 0), ('>=', 'unused_b', 0)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(5000))
    certificate = search.compose_products()
    assert certificate is not None
    assert polynomial.check_polynomial_certificate(graph.node('target'), graph, certificate)
    assert sum(step.rule == 'product' for step in certificate.steps) == 1
    used_terms = {step.term_id for step in certificate.steps if step.rule == 'input'}
    assert used_terms == {node.conclusion for node in graph.nodes[:3]}


def test_unsuccessful_joint_product_search_does_not_grow_the_evidence():
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>=', 'x', 1), ('>=', 'y', 2)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(5000))
    before = tuple(search.steps)
    assert search.compose_products() is None
    assert tuple(search.steps) == before


def test_joint_product_candidate_limit_is_explicit_and_keeps_evidence_unchanged():
    from pyfcstm.solver.proof import polynomial

    graph = _graph(tuple(('>=', 'x%d' % i, 1) for i in range(92)))
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(10000))
    before = tuple(search.steps)
    assert search.compose_products() is None
    assert search.limits == {'polynomial product candidate limit'}
    assert tuple(search.steps) == before


@pytest.mark.parametrize('conflict', [False, True])
def test_fact_limit_preserves_available_contradictions_and_reports_search_limits(conflict):
    from pyfcstm.solver.proof import polynomial, ProofGap

    premises = tuple(('>=', 'x%d' % i, 1) for i in range(256))
    if conflict:
        premises += (('<=', 'x0', 0),)
    graph = _graph(premises)
    diagnostics = []
    certificate = polynomial.polynomial_certificate(
        graph.node('target'), graph, SolveBudget(5000), diagnostics=diagnostics)
    if conflict:
        assert certificate is not None
        assert polynomial.check_polynomial_certificate(graph.node('target'), graph, certificate)
        assert diagnostics == []
    else:
        assert certificate is None
        assert diagnostics == [ProofGap('proof_search_limit', 'target', 'polynomial fact limit')]


def test_empty_linear_combination_has_no_contradiction():
    from pyfcstm.solver.proof import polynomial

    assert polynomial._eliminate([], SolveBudget(None), object()) is None


def test_alias_reduction_stops_at_the_fact_generation_limit():
    from pyfcstm.solver.proof import polynomial

    premises = tuple(('=', 'x%d' % i, 'y%d' % i) for i in range(80)) + tuple(
        ('>=', 'y%d' % i, i + 1) for i in range(80))
    graph = _graph(premises)
    search = polynomial._Search(graph.node('target'), graph, SolveBudget(10000))
    assert search.compose_equalities() is None
    assert len(search.facts) >= 256


def test_late_arithmetic_facts_are_checked_after_the_power_stage(monkeypatch):
    from pyfcstm.solver.proof import polynomial

    graph = _graph((('>', 'x', 0), ('>', 'y', 0), ('<', ('*', 'x', 'y'), 0)))
    finish = polynomial._Search.finish
    reached = []

    def finish_after_power_stage(self):
        return finish(self) if reached else None

    def produce_product(self):
        # Isolate the final equality pass using a valid late arithmetic fact.
        # Replay must still validate the certificate against the original input.
        self.product(0, 1)
        reached.append(True)
        return None

    monkeypatch.setattr(polynomial._Search, 'finish', finish_after_power_stage)
    monkeypatch.setattr(polynomial._Search, 'cancel_products', lambda self: None)
    monkeypatch.setattr(polynomial._Search, 'power_orders', produce_product)
    _certificate(graph)
    assert reached == [True]
