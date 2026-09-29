"""Exact integer contradictions from opposing arithmetic bounds."""

from fractions import Fraction

from .core import DivisibilityCertificate


def divisibility_certificate(node, graph, budget):
    """Check a native gcd-test by deriving an impossible integer equality.

    Opposing nonstrict bounds establish equalities. Native signed coefficients
    propose a combination, which is independently checked with exact rational
    arithmetic: an integer linear combination cannot equal a noninteger.

    :param node: Candidate native arithmetic inference with false conclusion.
    :param graph: Portable proof evidence containing its premises and terms.
    :param budget: Shared cooperative proof-analysis budget.
    :return: Checked local derivation, or ``None`` for unsupported evidence.
    """
    from .rules import _add, _bound, _bound_vector, _is_false

    if node.conclusion is None or not _is_false(node.conclusion, graph):
        return None
    parameters = tuple(parameter.value for parameter in node.parameters)
    if parameters[:2] != ('arith', 'gcd-test') or len(parameters) - 2 != len(node.parents):
        return None
    try:
        weights = tuple(Fraction(value) for value in parameters[2:])
    except (ValueError, ZeroDivisionError):
        # Fraction rejects malformed native rational text or a zero denominator.
        return None
    pending, pairs, pair_weights, total = {}, [], [], {}
    for parent, weight in zip(node.parents, weights):
        budget.checkpoint('proof analysis')
        bound = _bound(graph.node(parent).conclusion, False, graph)
        if bound is None or bound.relation != 'le':
            return None
        coefficients = tuple((term, Fraction(value)) for term, value in bound.coefficients)
        constant = Fraction(bound.constant)
        opposite = (tuple((term, -value) for term, value in coefficients), -constant, weight)
        if opposite not in pending:
            key = (coefficients, constant, weight)
            pending.setdefault(key, []).append(bound)
            continue
        first = pending[opposite].pop()
        if not pending[opposite]:
            del pending[opposite]
        if not weight:
            continue
        pairs.append((first, bound))
        pair_weights.append(str(weight))
        total = _add(total, _bound_vector(first), weight)
    if pending:
        return None
    constant = total.pop(None, Fraction(0))
    if constant.denominator == 1 or any(
            value.denominator != 1 or graph.term(term).sort != 'Int' for term, value in total.items()):
        return None
    return DivisibilityCertificate(tuple(pairs), tuple(pair_weights),
                                   tuple((term, str(value)) for term, value in sorted(total.items())),
                                   str(constant))
