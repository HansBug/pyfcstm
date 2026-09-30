"""Exact value lattices used when strengthening arithmetic bounds."""

from fractions import Fraction
from math import ceil, floor, gcd


def _gcd(left, right):
    """Greatest common rational step, including the zero constant step."""
    return Fraction(gcd(left.numerator * right.denominator,
                        right.numerator * left.denominator),
                    left.denominator * right.denominator)


def integer_lattice(term_id, graph, values=None):
    """Return a proved (offset, step) containing all values, or None.

    A zero step denotes an exact constant. Integer sorts provide integrality
    without a premise; genuine real atoms provide no lattice. The optional
    cache belongs to one graph and one caller, never to process-global state.
    """
    if values is None:
        values = {}
    pending = [(term_id, False)]
    while pending:
        key, ready = pending.pop()
        if key in values:
            continue
        term = graph.term(key)
        if term.kind == 'literal' and term.operator_kind == 'builtin' and term.sort in ('Int', 'Real'):
            values[key] = Fraction(term.value), Fraction(0)
        elif term.sort == 'Int':
            values[key] = Fraction(0), Fraction(1)
        elif (term.sort != 'Real' or term.operator_kind != 'builtin' or
              term.operator not in ('to_real', '+', '-', 'uminus', '*') or not term.arguments):
            values[key] = None
        elif not ready:
            pending.append((key, True))
            pending.extend((child, False) for child in reversed(term.arguments))
        else:
            parts = [values[child] for child in term.arguments]
            if any(part is None for part in parts):
                values[key] = None
            elif term.operator == 'to_real':
                values[key] = parts[0]
            elif term.operator == '*':
                offset, step = Fraction(1), Fraction(0)
                for other_offset, other_step in parts:
                    # (a+sZ)(b+tZ) is contained in ab+gcd(at,bs,st)Z.
                    step = _gcd(_gcd(abs(offset) * other_step, abs(other_offset) * step),
                                step * other_step)
                    offset *= other_offset
                values[key] = offset, step
            else:
                offset, step = parts[0]
                if term.operator == 'uminus' or (term.operator == '-' and len(parts) == 1):
                    offset = -offset
                for other_offset, other_step in parts[1:]:
                    offset += (-1 if term.operator == '-' else 1) * other_offset
                    step = _gcd(step, other_step)
                values[key] = offset, step
    return values[term_id]


def strengthen_bound(coefficients, constant, relation, graph):
    """Tighten p <= 0 or p < 0 to the largest admissible lattice value."""
    if relation == 'eq':
        return constant, relation
    offset, step, values = constant, Fraction(0), {}
    for key, coefficient in coefficients.items():
        lattice = integer_lattice(key, graph, values)
        if lattice is None:
            return constant, relation
        other_offset, other_step = lattice
        offset += coefficient * other_offset
        step = _gcd(step, abs(coefficient) * other_step)
    if step == 0:
        return constant, relation
    index = ceil(-offset / step) - 1 if relation == 'lt' else floor(-offset / step)
    largest = offset + step * index
    return constant - largest, 'le'
