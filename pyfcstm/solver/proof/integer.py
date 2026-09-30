"""Exact integer contradictions from opposing arithmetic bounds."""

from fractions import Fraction
from math import ceil, floor

from .core import DivisibilityCertificate


def divisibility_certificate(node, graph, budget):
    """Check a native gcd-test by deriving an impossible integer range.

    Opposing coefficient vectors establish closed ranges, including equalities.
    Native signed coefficients propose a combination. Exact replay proves that
    the resulting integer sum lies in a range containing no integer.

    :param node: Candidate native arithmetic inference with false conclusion.
    :param graph: Portable proof evidence containing its premises and terms.
    :param budget: Shared cooperative proof-analysis budget.
    :return: Checked local derivation, or ``None`` for unsupported evidence.
    """
    from .rules import _bound, _is_false

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
    pending, pairs, pair_weights = {}, [], []
    for parent, weight in zip(node.parents, weights):
        budget.checkpoint('proof analysis')
        bound = _bound(graph.node(parent).conclusion, False, graph, nonlinear_atoms=True, tighten=False)
        if bound is None or bound.relation != 'le':
            return None
        coefficients = tuple((term, Fraction(value)) for term, value in bound.coefficients)
        opposite = (tuple((term, -value) for term, value in coefficients), weight)
        if opposite not in pending:
            key = (coefficients, weight)
            pending.setdefault(key, []).append(bound)
            continue
        first = pending[opposite].pop()
        if not pending[opposite]:
            del pending[opposite]
        if not weight:
            continue
        pairs.append((first, bound))
        pair_weights.append(str(weight))
    if pending or not pairs:
        return None
    coefficients, lower, upper = _combine_pairs(pairs, pair_weights)
    if ceil(lower) <= floor(upper) or any(
            value.denominator != 1 or graph.term(term).sort != 'Int' for term, value in coefficients.items()):
        return None
    return DivisibilityCertificate(tuple(pairs), tuple(pair_weights),
                                   tuple((term, str(value)) for term, value in sorted(coefficients.items())),
                                   str(lower), str(upper))


def _combine_pairs(pairs, weights):
    """Compute both endpoints, reversing the range for a negative multiplier."""
    from .rules import _add

    total, lower, upper = {}, Fraction(0), Fraction(0)
    for (first, second), value in zip(pairs, weights):
        weight = Fraction(value)
        total = _add(total, {key: Fraction(coefficient) for key, coefficient in first.coefficients}, weight)
        first_constant, second_constant = Fraction(first.constant), Fraction(second.constant)
        lower += weight * (second_constant if weight >= 0 else -first_constant)
        upper += weight * (-first_constant if weight >= 0 else second_constant)
    return total, lower, upper


def check_divisibility_certificate(node, graph, certificate):
    """Replay the local bounds and exact integer range, independently of search."""
    from .rules import _add, _bound, _is_false

    if node.conclusion is None or not _is_false(node.conclusion, graph):
        return False
    if not certificate.bound_pairs or len(certificate.bound_pairs) != len(certificate.weights):
        return False
    premises = {graph.node(parent).conclusion for parent in node.parents}
    for pair in certificate.bound_pairs:
        first, second = pair
        if (first.relation != 'le' or second.relation != 'le' or
                _add({key: Fraction(value) for key, value in first.coefficients},
                     {key: Fraction(value) for key, value in second.coefficients})):
            return False
        for bound in pair:
            if bound.term_id not in premises or bound.negated:
                return False
            if bound != _bound(bound.term_id, False, graph, nonlinear_atoms=True, tighten=False):
                return False
    total, lower, upper = _combine_pairs(certificate.bound_pairs, certificate.weights)
    return (lower == Fraction(certificate.lower) and upper == Fraction(certificate.upper) and
            ceil(lower) > floor(upper) and
            total == {key: Fraction(value) for key, value in certificate.coefficients} and
            all(value.denominator == 1 and graph.term(key).sort == 'Int' for key, value in total.items()))
