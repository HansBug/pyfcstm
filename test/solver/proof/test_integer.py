"""Integer divisibility contradictions require checked equalities and exact sums."""

from dataclasses import replace

import pytest

from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofParameter, ProofTerm


pytestmark = pytest.mark.unittest


def _graph():
    terms = (
        ProofTerm('x', 'constant', 'Int', 'x', operator_kind='uninterpreted'),
        ProofTerm('y', 'constant', 'Int', 'y', operator_kind='uninterpreted'),
        ProofTerm('zero', 'literal', 'Int', 'Int', value='0'),
        ProofTerm('one', 'literal', 'Int', 'Int', value='1'),
        ProofTerm('two', 'literal', 'Int', 'Int', value='2'),
        ProofTerm('twice', 'application', 'Int', '*', ('two', 'x')),
        ProofTerm('upper', 'application', 'Bool', '<=', ('twice', 'one')),
        ProofTerm('lower', 'application', 'Bool', '>=', ('twice', 'one')),
        ProofTerm('y_upper', 'application', 'Bool', '<=', ('y', 'zero')),
        ProofTerm('y_lower', 'application', 'Bool', '>=', ('y', 'zero')),
        ProofTerm('false', 'literal', 'Bool', 'false', value='false'),
    )
    nodes = tuple(ProofNode(name, 'asserted', (), name) for name in ('upper', 'y_upper', 'lower', 'y_lower'))
    parameters = (ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'gcd-test')) + tuple(
        ProofParameter('rational', value) for value in ('1/2', '1', '1/2', '1'))
    root = ProofNode('root', 'th-lemma', tuple(node.node_id for node in nodes), 'false', parameters=parameters)
    return ProofGraph('divisibility', 'root', nodes + (root,), terms, ())


def _check(graph):
    from pyfcstm.solver.proof.integer import divisibility_certificate
    return divisibility_certificate(graph.node(graph.root_id), graph, SolveBudget(None))


def test_interleaved_opposing_bounds_prove_integer_divisibility():
    certificate = _check(_graph())
    assert certificate is not None
    assert certificate.weights == ('1/2', '1')
    assert certificate.coefficients == (('x', '1'), ('y', '1'))
    assert certificate.constant == '-1/2'
    assert tuple((first.term_id, second.term_id) for first, second in certificate.bound_pairs) == (
        ('upper', 'lower'), ('y_upper', 'y_lower'))


@pytest.mark.parametrize('case', [
    'no_conclusion', 'nonfalse_conclusion', 'wrong_rule', 'missing_weight', 'odd_bounds',
    'unpaired_bound', 'unequal_weights', 'zero_weights', 'malformed_weight', 'zero_denominator',
    'boolean_bound', 'equality_bound', 'strict_real_bound', 'real_atoms', 'nonintegral_coefficient',
    'integral_constant', 'unequal_constants', 'empty_bounds',
])
def test_invalid_divisibility_candidates_are_rejected(case):
    graph = _graph()
    root = graph.node('root')
    terms = {term.term_id: term for term in graph.terms}
    if case == 'no_conclusion':
        root = replace(root, conclusion=None)
    elif case == 'nonfalse_conclusion':
        root = replace(root, conclusion='upper')
    elif case == 'wrong_rule':
        root = replace(root, parameters=(ProofParameter('symbol', 'other'),) + root.parameters[1:])
    elif case == 'missing_weight':
        root = replace(root, parameters=root.parameters[:-1])
    elif case == 'odd_bounds':
        root = replace(root, parents=root.parents[:-1], parameters=root.parameters[:-1])
    elif case == 'unpaired_bound':
        root = replace(root, parents=('upper', 'y_upper', 'upper', 'y_lower'))
    elif case == 'unequal_weights':
        root = replace(root, parameters=root.parameters[:-2] + (ProofParameter('rational', '1'),) + root.parameters[-1:])
    elif case in ('zero_weights', 'malformed_weight', 'zero_denominator', 'nonintegral_coefficient'):
        value = {'zero_weights': '0', 'malformed_weight': 'bad', 'zero_denominator': '1/0',
                 'nonintegral_coefficient': '1/3'}[case]
        root = replace(root, parameters=root.parameters[:2] + tuple(ProofParameter('rational', value) for _ in root.parents))
    elif case == 'boolean_bound':
        terms['upper'] = replace(terms['upper'], operator='and', arguments=('false', 'false'))
    elif case == 'equality_bound':
        terms['upper'] = replace(terms['upper'], operator='=')
    elif case in ('strict_real_bound', 'real_atoms'):
        terms = {key: replace(term, sort='Real') if term.sort == 'Int' else term for key, term in terms.items()}
        if case == 'strict_real_bound':
            terms['upper'] = replace(terms['upper'], operator='<')
    elif case == 'integral_constant':
        terms['one'] = replace(terms['one'], value='2')
    elif case == 'unequal_constants':
        terms['lower'] = replace(terms['lower'], arguments=('twice', 'zero'))
    elif case == 'empty_bounds':
        root = replace(root, parents=(), parameters=root.parameters[:2])
    graph = replace(graph, terms=tuple(terms.values()), nodes=graph.nodes[:-1] + (root,))
    assert _check(graph) is None


def test_strict_integer_bound_is_normalized_before_pairing():
    graph = _graph()
    terms = tuple(replace(term, operator='<', arguments=('twice', 'two'))
                  if term.term_id == 'upper' else term for term in graph.terms)
    certificate = _check(replace(graph, terms=terms))
    assert certificate is not None
    assert certificate.constant == '-1/2'


def test_negative_weights_preserve_equality_orientation():
    graph = _graph()
    root = graph.node('root')
    root = replace(root, parameters=root.parameters[:2] + tuple(
        ProofParameter('rational', value) for value in ('-1/2', '-1', '-1/2', '-1')))
    certificate = _check(replace(graph, nodes=graph.nodes[:-1] + (root,)))
    assert certificate is not None
    assert certificate.coefficients == (('x', '-1'), ('y', '-1'))
    assert certificate.constant == '1/2'


def test_repeated_bound_pairs_keep_each_contribution():
    graph = _graph()
    root = graph.node('root')
    root = replace(root, parents=('upper', 'upper', 'upper', 'lower', 'lower', 'lower'),
                   parameters=root.parameters[:2] + (ProofParameter('rational', '1/2'),) * 6)
    certificate = _check(replace(graph, nodes=graph.nodes[:-1] + (root,)))
    assert certificate is not None
    assert len(certificate.bound_pairs) == 3
    assert certificate.coefficients == (('x', '3'),)
    assert certificate.constant == '-3/2'


def test_divisibility_analysis_obeys_shared_deadline():
    from pyfcstm.solver.budget import BudgetExpired
    from pyfcstm.solver.proof.integer import divisibility_certificate

    graph = _graph()
    budget = SolveBudget(None)
    budget.deadline = 0
    with pytest.raises(BudgetExpired):
        divisibility_certificate(graph.node('root'), graph, budget)


def test_public_parity_proof_checks_every_native_divisibility_node():
    from fractions import Fraction
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
    from pyfcstm.model import load_state_machine_from_text
    from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat

    model = load_state_machine_from_text('def int x=0; def int y=0; state Root { state A; [*]->A; }')
    core = build_bmc_core_formula(BmcEngine(model).prepare(
        'init state("Root.A") havoc {x,y}; check reach <= 1: x%2==0 && (x+1)%2==0;'))
    prop = compile_bmc_property(core)
    report = explain_unsat(UnsatQuery('parity', tuple(
        UnsatConstraint(key, (expression,)) for key, expression in (
            ('domain', core.domain_formula), ('initial', core.initial_formula),
            ('transitions', core.transition_formula), ('environment', core.environment_formula),
            ('objective', prop.objective_formula),
        ))))
    assert report.solver_status == 'unsat'
    nodes = tuple(node for node in report.proof.nodes if any(parameter.value == 'gcd-test' for parameter in node.parameters))
    assert nodes
    for node in nodes:
        assert node.local_check == 'checked'
        assert node.inference_kind == 'divisibility'
        certificate = node.divisibility
        assert certificate is not None
        assert Fraction(certificate.constant).denominator == 2
        assert all(Fraction(value).denominator == 1 and report.proof.term(term).sort == 'Int'
                   for term, value in certificate.coefficients)
        assert certificate == _check(replace(report.proof, root_id=node.node_id))
        broken = replace(node, parents=(node.parents[0],) * len(node.parents))
        graph = replace(report.proof, root_id=broken.node_id,
                        nodes=tuple(broken if item.node_id == node.node_id else item for item in report.proof.nodes))
        assert _check(graph) is None


def test_zero_weight_equalities_are_absent_from_the_divisibility_path():
    graph = _graph()
    root = graph.node('root')
    root = replace(root, parameters=root.parameters[:2] + tuple(
        ProofParameter('rational', value) for value in ('1/2', '0', '1/2', '0')))
    certificate = _check(replace(graph, nodes=graph.nodes[:-1] + (root,)))
    assert certificate is not None
    assert certificate.weights == ('1/2',)
    assert tuple((first.term_id, second.term_id) for first, second in certificate.bound_pairs) == (
        ('upper', 'lower'),)
    assert certificate.coefficients == (('x', '1'),)
    assert certificate.constant == '-1/2'
