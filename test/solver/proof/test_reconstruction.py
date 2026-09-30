"""Local interpretation is independent of proof-scope orchestration."""

from dataclasses import replace
from importlib.util import find_spec

import pytest

from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.proof import ProofParameter

from .test_polynomial import _graph


pytestmark = pytest.mark.unittest


def _reconstruct(node, graph, budget):
    assert find_spec('pyfcstm.solver.proof.reconstruction') is not None, 'local reconstruction dispatch is missing'
    from pyfcstm.solver.proof.reconstruction import reconstruct
    return reconstruct(node, graph, budget)


def test_local_reconstruction_retains_exact_linear_evidence():
    graph = _graph((('>=', 'x', 1), ('<=', 'x', 0)))
    node = replace(graph.node(graph.root_id), parameters=(ProofParameter('symbol', 'arith'),))
    result = _reconstruct(node, graph, SolveBudget(None))
    assert (result.kind, result.local_check) == ('arithmetic', 'checked')
    assert tuple(field for field, _ in result.evidence) == ('certificate',)
    certificate = result.evidence[0][1]
    assert certificate.constant == '1'
    assert certificate.weights == ('1', '1')
    assert result.diagnostics == ()


def test_unknown_native_theory_does_not_run_arithmetic_search():
    graph = _graph((('>=', 'x', 1), ('<=', 'x', 0)))
    node = replace(graph.node(graph.root_id), parameters=(ProofParameter('symbol', 'other'),))
    result = _reconstruct(node, graph, SolveBudget(None))
    assert (result.kind, result.local_check, result.evidence, result.diagnostics) == (
        'opaque', 'unsupported', (), (),
    )


def test_invalid_native_weighted_proof_does_not_fall_back_to_another_proof():
    graph = _graph((('>=', 'x', 1), ('<=', 'x', 0)))
    node = replace(graph.node(graph.root_id), parameters=(
        ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'farkas'),
        ProofParameter('rational', '0'), ProofParameter('rational', '0'),
    ))
    result = _reconstruct(node, graph, SolveBudget(None))
    assert (result.kind, result.local_check, result.evidence) == ('opaque', 'invalid', ())


def test_reconstruction_stops_at_the_first_successful_fallback(monkeypatch):
    from pyfcstm.solver.proof import rules, interval, polynomial

    graph = _graph((('>=', 'x', 1), ('<=', 'x', 0)))
    node = replace(graph.node(graph.root_id), parameters=(ProofParameter('symbol', 'arith'),))
    calls = []
    for module, name in ((rules, '_local_pair_certificate'), (rules, '_linear_certificate'),
                         (interval, 'interval_certificate'), (rules, '_linear_equality'),
                         (polynomial, 'polynomial_certificate')):
        original = getattr(module, name)

        def tracked(*args, _name=name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(module, name, tracked)
    result = _reconstruct(node, graph, SolveBudget(None))
    assert result.local_check == 'checked'
    assert calls == ['_local_pair_certificate']


def test_analyzer_delegates_local_theory_nodes_with_the_same_budget(monkeypatch, proof_snapshot):
    from pyfcstm.solver.proof import analyze_proof, reconstruction

    graph = proof_snapshot('integer_product').proof
    budget = SolveBudget(None)
    original = reconstruction.reconstruct
    calls = []

    def tracked(node, current_graph, current_budget):
        assert current_graph is graph
        assert current_budget is budget
        calls.append(node.node_id)
        return original(node, current_graph, current_budget)

    monkeypatch.setattr(reconstruction, 'reconstruct', tracked)
    analysis = analyze_proof(graph, budget=budget)
    assert calls == [node.node_id for node in graph.nodes if node.rule == 'th-lemma']
    assert analysis.scope_check == 'passed'
    assert analysis.gaps == ()


def test_rejected_fast_path_evidence_is_not_hidden_by_successful_fallback(monkeypatch):
    from pyfcstm.solver.proof import rules

    graph = _graph((('>=', 'x', 1), ('<=', 'x', 0)))
    node = replace(graph.node(graph.root_id), parameters=(
        ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'farkas'),
        ProofParameter('rational', '1'), ProofParameter('rational', '1'),
    ))
    original = rules._certificate

    def corrupted(current, current_graph):
        certificate, status = original(current, current_graph)
        return replace(certificate, constant='999999'), status

    monkeypatch.setattr(rules, '_certificate', corrupted)
    with pytest.warns(RuntimeWarning, match='invalid_arithmetic_certificate'):
        result = _reconstruct(node, graph, SolveBudget(None))
    assert result.local_check == 'unsupported'
    assert result.evidence == ()
    assert [gap.reason for gap in result.diagnostics] == ['invalid_arithmetic_certificate']
