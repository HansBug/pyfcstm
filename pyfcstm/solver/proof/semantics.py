"""Domain-conditioned arithmetic facts for local polynomial proofs.

The producer finds useful facts; replay checks the operation and its explicit
domain evidence without invoking either the producer or a native solver.
"""

from fractions import Fraction


def _power(term_id, graph, normalizer):
    term = graph.term(term_id)
    if (term.kind != 'application' or term.operator_kind != 'builtin' or
            term.operator != '^' or term.sort != 'Real' or len(term.arguments) != 2 or
            any(graph.term(arg).sort != 'Real' for arg in term.arguments)):
        return None
    exponent = normalizer.polynomial(term.arguments[1])
    value = exponent.get((), Fraction(0)) if set(exponent) <= {()} else None
    return normalizer.polynomial(term.arguments[0]), value


def add_semantic_facts(search):
    """Derive power signs and identities from established base signs."""
    for term_id in search.local_terms:
        search.budget.checkpoint('arithmetic semantic evidence')
        parts = _power(term_id, search.graph, search.normalizer)
        if parts is None:
            continue
        base, exponent = parts
        premise = search.sign(base)
        if premise is None:
            continue
        strict = search.facts[premise][1]
        if strict or exponent is not None and exponent > 0:
            search.record(search.normalizer.polynomial(term_id), strict, 'power_sign',
                          term_id=term_id, premises=(premise,))
            if exponent is not None and max(abs(exponent.numerator), exponent.denominator) <= 32:
                from .polynomial import _scale, _SearchLimit

                try:
                    identity = _identity(term_id, base, exponent, search.normalizer)
                except _SearchLimit as err:
                    # _identity may exceed sparse expansion limits; this
                    # optional equality must not discard established signs.
                    search.limits.add(str(err))
                    continue
                for orientation in (1, -1):
                    search.record(_scale(identity, orientation), False, 'power_identity',
                                  term_id=term_id, premises=(premise,), multiplier=str(orientation))


def _identity(term_id, base, exponent, normalizer):
    from .polynomial import _add, _multiply, _power_polynomial

    value = _power_polynomial(normalizer.polynomial(term_id), exponent.denominator, normalizer.budget)
    base_power = _power_polynomial(base, abs(exponent.numerator), normalizer.budget)
    if exponent < 0:
        return _add(_multiply(value, base_power, normalizer.budget), {(): Fraction(-1)})
    return _add(value, base_power, -1)


def check_semantic_step(step, graph, normalizer, facts):
    """Check a typed power fact using its recorded domain premise."""
    if (step.term_id is None or step.negated or
            step.weights or step.factor or len(step.premises) != 1):
        return False
    parts = _power(step.term_id, graph, normalizer)
    if parts is None:
        return False
    base, exponent = parts
    domain, strict = facts[step.premises[0]]
    from .polynomial import _unpacked, _scale

    if domain != base or not (strict or exponent is not None and exponent > 0):
        return False
    if step.rule == 'power_sign':
        return (step.multiplier == '1' and step.strict == strict and
                _unpacked(step.coefficients, graph) == normalizer.polynomial(step.term_id))
    return (step.rule == 'power_identity' and exponent is not None and
            max(abs(exponent.numerator), exponent.denominator) <= 32 and
            step.multiplier in ('1', '-1') and not step.strict and
            _unpacked(step.coefficients, graph) == _scale(
                _identity(step.term_id, base, exponent, normalizer), Fraction(step.multiplier)))
