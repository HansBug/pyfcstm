"""Local theory interpretation without scope or report-state ownership.

Native hints choose fast paths. Arithmetic fallback order is explicit and
unchanged; the first produced candidate ends the search even if replay rejects
it. A bad candidate must remain observable, rather than being hidden by a later
successful strategy.
"""

from dataclasses import dataclass
from typing import Tuple

from . import rules
from .core import ProofGap
from .evidence import certificate_handlers


@dataclass(frozen=True)
class Reconstruction:
    """Local interpretation and evidence; cannot discharge native hypotheses."""

    kind: str = 'opaque'
    local_check: str = 'unsupported'
    evidence: tuple = ()
    diagnostics: Tuple[ProofGap, ...] = ()


def _candidate(field, certificate, node, graph, budget, *, replay=True):
    if certificate is None:
        return Reconstruction()
    handler = next(item for item in certificate_handlers() if item.field == field)
    if replay and not handler.replay(node, graph, certificate, budget):
        label = {'linear_equality': 'equality', 'cardinality': 'counting'}.get(handler.kind, handler.kind)
        gap = rules._invalid_gap(node, 'invalid_%s_certificate' % handler.kind,
                                 'generated %s evidence failed replay' % label)
        return Reconstruction(diagnostics=(gap,))
    return Reconstruction(handler.kind, 'checked', ((field, certificate),))


def _divisibility(node, graph, budget):
    from .integer import divisibility_certificate

    return _candidate('divisibility', divisibility_certificate(node, graph, budget), node, graph, budget)


def _cardinality(node, graph, budget):
    return _candidate('cardinality', rules._cardinality_certificate(node, graph, budget), node, graph, budget)


def _order(node, graph, budget):
    if rules._order_tautology(node, graph, budget):
        return Reconstruction('order', 'checked')
    if rules._arithmetic_identity(node, graph):
        return Reconstruction('arithmetic_identity', 'checked')
    return Reconstruction()


def _axiom(node, graph, budget):
    kind = (rules._division_axiom(node, graph, budget) or rules._quotient_axiom(node, graph, budget) or
            rules._floor_axiom(node, graph, budget) or rules._power_axiom(node, graph, budget))
    if kind is not None:
        return Reconstruction(kind, 'checked')
    if rules._arithmetic_identity(node, graph):
        return Reconstruction('arithmetic_identity', 'checked')
    if rules._order_tautology(node, graph, budget):
        return Reconstruction('order', 'checked')
    return Reconstruction()


def _weighted(node, graph, budget):
    certificate, status = rules._certificate(node, graph)
    if certificate is None:
        return Reconstruction(local_check=status)
    return _candidate('certificate', certificate, node, graph, budget)


def reconstruct(node, graph, budget):
    """Interpret one theory lemma with the existing fast paths and fallback order.

    The caller owns extension precedence, scopes, shared budget creation and
    timeout handling. Polynomial production already replays its evidence before
    returning, so it is not replayed twice against the same live deadline.
    """
    from .interval import interval_certificate
    from .polynomial import polynomial_certificate

    parameters = tuple(parameter.value for parameter in node.parameters)
    hint = parameters[:2] if parameters[:2] == ('arith', 'gcd-test') else parameters
    interpreters = {
        ('arith', 'gcd-test'): _divisibility,
        ('pb',): _cardinality,
        ('arith', 'triangle-eq'): _order,
        ('arith',): _axiom,
    }
    result = interpreters.get(hint, _weighted)(node, graph, budget)
    if result.diagnostics or result.local_check != 'unsupported' or not parameters or parameters[0] != 'arith':
        return result
    diagnostics = []
    strategies = (
        ('certificate', lambda: rules._local_pair_certificate(node, graph)),
        ('certificate', lambda: rules._linear_certificate(node, graph, budget)),
        ('interval', lambda: interval_certificate(node, graph, budget)),
        ('linear_equality', lambda: rules._linear_equality(node, graph, budget)),
        ('polynomial', lambda: polynomial_certificate(node, graph, budget, diagnostics=diagnostics)),
    )
    for field, produce in strategies:
        certificate = produce()
        if certificate is not None:
            return _candidate(field, certificate, node, graph, budget, replay=field != 'polynomial')
    return Reconstruction(diagnostics=tuple(diagnostics))
