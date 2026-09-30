"""Shared certificate dispatch preserves exact detached proof checking."""

from dataclasses import FrozenInstanceError, replace
from importlib.util import find_spec

import pytest

from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.proof import ProofNode


pytestmark = pytest.mark.unittest


def _handlers():
    assert find_spec('pyfcstm.solver.proof.evidence') is not None, 'shared certificate catalog is missing'
    from pyfcstm.solver.proof.evidence import certificate_handlers
    return certificate_handlers()


def test_certificate_catalog_is_explicit_and_immutable():
    handlers = _handlers()
    assert isinstance(handlers, tuple)
    assert [(item.field, item.kind) for item in handlers] == [
        ('certificate', 'arithmetic'), ('linear_equality', 'linear_equality'),
        ('divisibility', 'divisibility'), ('polynomial', 'polynomial'),
        ('interval', 'interval'), ('cardinality', 'cardinality'),
    ]
    assert len({item.payload_type for item in handlers}) == 6
    with pytest.raises(FrozenInstanceError):
        handlers[0].field = 'other'


@pytest.mark.parametrize('family', ['certificate', 'polynomial', 'interval'])
def test_catalog_replays_real_evidence_and_rejects_changed_payload(family, proof_snapshot):
    handler = next(item for item in _handlers() if item.field == family)
    graph = proof_snapshot('integer_product').proof
    node = next(node for node in graph.nodes if getattr(node, family) is not None)
    certificate = getattr(node, family)
    assert isinstance(certificate, handler.payload_type)
    assert handler.replay(node, graph, certificate, SolveBudget(None))
    if family == 'certificate':
        changed = replace(certificate, constant='999999')
    elif family == 'polynomial':
        changed = replace(certificate, steps=())
    else:
        changed = replace(certificate, steps=(replace(certificate.steps[0], lower='999999'),)
                          + certificate.steps[1:])
    assert not handler.replay(node, graph, changed)


def test_catalog_selects_only_attached_evidence_in_declared_order(proof_snapshot):
    handlers = _handlers()
    from pyfcstm.solver.proof.evidence import iter_evidence

    empty = ProofNode('empty', 'rewrite', (), None)
    assert tuple(iter_evidence(empty)) == ()
    graph = proof_snapshot('integer_product').proof
    fields = {
        field: next(getattr(node, field) for node in graph.nodes if getattr(node, field) is not None)
        for field in ('certificate', 'polynomial', 'interval')
    }
    node = replace(empty, **fields)
    assert [(handler.field, payload) for handler, payload in iter_evidence(node)] == [
        (handler.field, fields[handler.field]) for handler in handlers if handler.field in fields
    ]


def test_offline_loading_uses_the_shared_certificate_checker(monkeypatch, proof_snapshot):
    from pyfcstm.solver.proof import UnsatReport

    handlers = _handlers()
    data = proof_snapshot('integer_product').to_canonical()
    handler_type = type(handlers[0])
    original = handler_type.replay

    def reject_arithmetic(self, node, graph, certificate, budget=None):
        # A rejecting checker models a changed certificate rule, not a solver failure.
        return self.field != 'certificate' and original(self, node, graph, certificate, budget)

    monkeypatch.setattr(handler_type, 'replay', reject_arithmetic)
    with pytest.raises(ValueError, match='invalid arithmetic derivation'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('family', ['linear_equality', 'divisibility', 'cardinality'])
def test_catalog_replays_the_other_exact_certificate_families(family):
    from pyfcstm.solver.proof.rules import _linear_equality, _cardinality_certificate
    from .test_integer import _graph as integer_graph, _check
    from .test_polynomial import _graph as arithmetic_graph
    from .test_theories import _counting_graph

    handler = next(item for item in _handlers() if item.field == family)
    if family == 'divisibility':
        graph = integer_graph()
        certificate = _check(graph)
        changed = replace(certificate, upper='999999')
    elif family == 'linear_equality':
        graph = arithmetic_graph((('<=', 'x', 'y'), ('<=', 'y', 'x')), ('=', 'x', 'y'))
        certificate = _linear_equality(graph.node(graph.root_id), graph, SolveBudget(None))
        changed = replace(certificate, greater=certificate.less)
    else:
        graph = _counting_graph('at-most', (1, 1, 1), 1, True, (('a', True), ('b', True)))
        certificate = _cardinality_certificate(graph.node(graph.root_id), graph, SolveBudget(None))
        changed = replace(certificate, constraint_value=not certificate.constraint_value)
    node = graph.node(graph.root_id)
    assert isinstance(certificate, handler.payload_type)
    assert handler.replay(node, graph, certificate, SolveBudget(None))
    assert not handler.replay(node, graph, changed)
