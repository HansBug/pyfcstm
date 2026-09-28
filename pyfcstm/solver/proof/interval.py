"""Exact local interval deductions for nonlinear native arithmetic lemmas."""

from dataclasses import dataclass, replace
from fractions import Fraction
from math import ceil, floor, inf

from .core import IntervalCertificate, IntervalStep, TermEquality


def _multiply_endpoint(left, right):
    """Multiply extended rational endpoints without coercing rationals to float."""
    if left == 0 or right == 0:
        return Fraction(0)
    if abs(left) == inf or abs(right) == inf:
        return inf if (left > 0) == (right > 0) else -inf
    return left * right


def _power_endpoint(value, degree):
    """Preserve integer exponent parity for infinite endpoints."""
    if abs(value) == inf:
        return -inf if value < 0 and degree % 2 else inf
    return value ** degree


@dataclass(frozen=True)
class _Range:
    lower: object = -inf
    upper: object = inf
    lower_open: bool = True
    upper_open: bool = True

    def add(self, other):
        return _Range(-inf if self.lower == -inf or other.lower == -inf else self.lower + other.lower,
                      inf if self.upper == inf or other.upper == inf else self.upper + other.upper,
                      self.lower_open or other.lower_open, self.upper_open or other.upper_open)

    def scale(self, coefficient):
        if coefficient == 0:
            return _Range(Fraction(0), Fraction(0), False, False)
        if coefficient > 0:
            return _Range(_multiply_endpoint(self.lower, coefficient), _multiply_endpoint(self.upper, coefficient), self.lower_open, self.upper_open)
        return _Range(_multiply_endpoint(self.upper, coefficient), _multiply_endpoint(self.lower, coefficient), self.upper_open, self.lower_open)

    def contains_zero(self):
        return ((self.lower < 0 or self.lower == 0 and not self.lower_open) and
                (self.upper > 0 or self.upper == 0 and not self.upper_open))

    def multiply(self, other):
        endpoints = [(_multiply_endpoint(a, b), a_open or b_open)
                     for a, a_open in ((self.lower, self.lower_open), (self.upper, self.upper_open))
                     for b, b_open in ((other.lower, other.lower_open), (other.upper, other.upper_open))]
        lower, upper = min(value for value, _ in endpoints), max(value for value, _ in endpoints)
        zero = self.contains_zero() or other.contains_zero()
        return _Range(lower, upper,
                      all(opened for value, opened in endpoints if value == lower) and not (lower == 0 and zero),
                      all(opened for value, opened in endpoints if value == upper) and not (upper == 0 and zero))

    def square(self):
        if self.lower >= 0:
            return _Range(self.lower ** 2, self.upper ** 2, self.lower_open, self.upper_open)
        if self.upper <= 0:
            return _Range(self.upper ** 2, self.lower ** 2, self.upper_open, self.lower_open)
        upper = max(self.lower ** 2, self.upper ** 2)
        opened = all(flag for value, flag in ((self.lower ** 2, self.lower_open), (self.upper ** 2, self.upper_open))
                     if value == upper)
        return _Range(Fraction(0), upper, False, opened)

    def intersect(self, other):
        lower, upper = max(self.lower, other.lower), min(self.upper, other.upper)
        return _Range(lower, upper,
                      any(flag for value, flag in ((self.lower, self.lower_open), (other.lower, other.lower_open))
                          if value == lower),
                      any(flag for value, flag in ((self.upper, self.upper_open), (other.upper, other.upper_open))
                          if value == upper))

    def empty(self):
        return self.lower > self.upper or self.lower == self.upper and (self.lower_open or self.upper_open)

    def integer(self):
        lower = self.lower if self.lower == -inf else floor(self.lower) + 1 if self.lower_open else ceil(self.lower)
        upper = self.upper if self.upper == inf else ceil(self.upper) - 1 if self.upper_open else floor(self.upper)
        return _Range(lower, upper, lower == -inf, upper == inf)


def _equalities(bounds, graph):
    """Recognize exact a=b facts, including scaled opposing inequalities."""
    pending, result = {}, {}
    for index, bound in enumerate(bounds):
        if bound.relation not in ('eq', 'le') or Fraction(bound.constant) != 0 or len(bound.coefficients) != 2:
            continue
        (left, first), (right, second) = bound.coefficients
        if Fraction(first) + Fraction(second) != 0 or graph.term(left).sort != graph.term(right).sort:
            continue
        key, sign = (left, right), Fraction(first) > 0
        if bound.relation == 'eq':
            result[key] = TermEquality(left, right, (index,))
        elif (key, not sign) in pending and key not in result:
            result[key] = TermEquality(left, right, (pending[key, not sign], index))
        pending[key, sign] = index
    return tuple(result.values())


class _Propagation:
    def __init__(self, graph, bounds, budget):
        self.graph, self.bounds, self.budget = graph, bounds, budget
        self.values, self.indices, self.steps = {}, {}, []
        self.conflict = None
        self.equalities = _equalities(bounds, graph)

    def record(self, term_id, value, rule, premises=(), bound_index=None, substitutions=()):
        if self.graph.term(term_id).sort == 'Int':
            value = value.integer()
        previous = self.values.get(term_id, _Range())
        merged = previous.intersect(value)
        if merged == previous:
            return
        index = len(self.steps)
        self.steps.append(IntervalStep(term_id, None if value.lower == -inf else str(value.lower),
                                       None if value.upper == inf else str(value.upper),
                                       value.lower_open, value.upper_open, rule,
                                       tuple(dict.fromkeys(premises)), bound_index, substitutions))
        if merged.empty():
            self.conflict = (self.indices.get(term_id, index), index)
            return
        if merged != value:
            self.steps.append(IntervalStep(term_id, None if merged.lower == -inf else str(merged.lower),
                                           None if merged.upper == inf else str(merged.upper),
                                           merged.lower_open, merged.upper_open, 'intersection',
                                           (self.indices[term_id], index)))
        self.values[term_id], self.indices[term_id] = merged, len(self.steps) - 1

    def certificate(self, equality=None):
        roots = self.conflict if equality is None else equality
        used, pending = set(), list(roots)
        while pending:
            index = pending.pop()
            if index not in used:
                used.add(index)
                pending.extend(self.steps[index].premises)
        order = sorted(used)
        indices = {old: new for new, old in enumerate(order)}
        bounds = sorted({self.steps[index].bound_index for index in order
                         if self.steps[index].bound_index is not None})
        bounds = sorted(set(bounds) | {bound for index in order for equality in self.steps[index].substitutions
                                      for bound in equality.bound_indices})
        bound_indices = {old: new for new, old in enumerate(bounds)}
        steps = tuple(replace(self.steps[index],
                              premises=tuple(indices[parent] for parent in self.steps[index].premises),
                              bound_index=bound_indices.get(self.steps[index].bound_index),
                              substitutions=tuple(replace(equality, bound_indices=tuple(
                                  bound_indices[bound] for bound in equality.bound_indices))
                                  for equality in self.steps[index].substitutions)) for index in order)
        result = tuple(indices[index] for index in roots)
        return IntervalCertificate(tuple(self.bounds[index] for index in bounds), steps,
                                   result if equality is None else None,
                                   None if equality is None else result)

    def congruence(self):
        """Transfer ranges only between expressions equal under local facts."""
        if not self.equalities:
            return
        groups = {}
        for equality in self.equalities:
            merged = groups.get(equality.left_id, {equality.left_id}) | groups.get(equality.right_id, {equality.right_id})
            for term in merged:
                groups[term] = merged
        signatures, dependencies, interned = {}, {}, {}

        def signature(term_id):
            pending = [(term_id, False)]
            while pending:
                self.budget.checkpoint('proof analysis')
                current, ready = pending.pop()
                if current in signatures:
                    continue
                term = self.graph.term(current)
                if current in groups:
                    members = groups[current]
                    key = ('equal', min(members))
                    dependencies[current] = {index for index, equality in enumerate(self.equalities)
                                              if equality.left_id in members}
                elif term.kind == 'application' and term.operator_kind == 'builtin':
                    if not ready:
                        pending.append((current, True))
                        pending.extend((child, False) for child in reversed(term.arguments))
                        continue
                    key = (term.kind, term.sort, term.operator, term.parameters,
                           tuple(signatures[child] for child in term.arguments))
                    dependencies[current] = set().union(*(dependencies[child] for child in term.arguments))
                else:
                    key, dependencies[current] = ('term', current), set()
                signatures[current] = interned.setdefault(key, len(interned))
            return signatures[term_id]

        equivalent = {}
        for term in self.graph.terms:
            self.budget.checkpoint('proof analysis')
            if term.sort in ('Int', 'Real'):
                equivalent.setdefault(signature(term.term_id), []).append(term.term_id)
        for members in equivalent.values():
            for source in members:
                if source not in self.indices:
                    continue
                for target in members:
                    self.budget.checkpoint('proof analysis')
                    if source == target:
                        continue
                    equalities = tuple(self.equalities[index] for index in sorted(
                        dependencies[source] | dependencies[target]))
                    self.record(target, self.values[source], 'congruence', (self.indices[source],),
                                substitutions=equalities)
                    if self.conflict is not None:
                        return

    def linear(self, coefficients, constant):
        value, premises = _Range(constant, constant, False, False), []
        for term, coefficient in coefficients:
            value = value.add(self.values.get(term, _Range()).scale(coefficient))
            if term in self.indices:
                premises.append(self.indices[term])
        return value, tuple(premises)

    def constrain(self, bound, bound_index):
        for orientation in ((1, -1) if bound.relation == 'eq' else (1,)):
            coefficients = [(term, Fraction(value) * orientation) for term, value in bound.coefficients]
            for term, coefficient in coefficients:
                self.budget.checkpoint('proof analysis')
                others, premises = self.linear([(key, value) for key, value in coefficients if key != term],
                                               Fraction(bound.constant) * orientation)
                if others.lower == -inf:
                    continue
                endpoint = -others.lower / coefficient
                opened = others.lower_open or bound.relation == 'lt'
                value = (_Range(-inf, endpoint, True, opened) if coefficient > 0 else
                         _Range(endpoint, inf, opened, True))
                self.record(term, value, 'linear', premises, bound_index)
                if self.conflict is not None:
                    return

    def evaluate(self, term):
        from .rules import _bound

        if term.sort not in ('Int', 'Real') or term.operator_kind != 'builtin':
            return
        if term.kind == 'literal':
            value = Fraction(term.value)
            self.record(term.term_id, _Range(value, value, False, False), 'literal')
            return
        args = term.arguments
        values = [self.values.get(child, _Range()) for child in args]
        premises = tuple(self.indices[child] for child in args if child in self.indices)
        if term.operator == '*' and len(args) == 2 and args[0] == args[1]:
            self.record(term.term_id, values[0].square(), 'square', premises)
        elif term.operator == '*' and values:
            value = _Range(Fraction(1), Fraction(1), False, False)
            for operand in values:
                value = value.multiply(operand)
            self.record(term.term_id, value, 'product', premises)
        elif term.operator in ('+', '-', 'uminus') and values:
            value = values[0].scale(Fraction(-1)) if len(values) == 1 and term.operator != '+' else values[0]
            for operand in values[1:]:
                value = value.add(operand.scale(Fraction(1 if term.operator == '+' else -1)))
            self.record(term.term_id, value, 'sum', premises)
        elif term.operator == '^' and len(args) == 2:
            exponent = values[1]
            if (exponent.lower == exponent.upper and exponent.lower != inf and
                    not exponent.lower_open and not exponent.upper_open and
                    exponent.lower > 0 and Fraction(exponent.lower).denominator == 1):
                power = int(exponent.lower)
                base = values[0] if power % 2 else values[0].square()
                degree = power if power % 2 else power // 2
                self.record(term.term_id, _Range(_power_endpoint(base.lower, degree), _power_endpoint(base.upper, degree),
                                                 base.lower_open, base.upper_open), 'power', premises)
        elif term.operator == 'to_real' and len(args) == 1:
            self.record(term.term_id, values[0], 'cast', premises)
        elif term.operator == 'ite' and len(args) == 3:
            bound = _bound(args[0], False, self.graph, True)
            if bound is None:
                return
            condition, dependencies = self.linear([(key, Fraction(value)) for key, value in bound.coefficients],
                                                   Fraction(bound.constant))
            holds = (condition.upper < 0 or condition.upper == 0 and
                     (bound.relation == 'le' or condition.upper_open))
            fails = (condition.lower > 0 or condition.lower == 0 and
                     (bound.relation == 'lt' or condition.lower_open))
            if bound.relation != 'eq' and (holds or fails):
                chosen = args[1] if holds else args[2]
                if chosen in self.indices:
                    self.record(term.term_id, self.values[chosen], 'conditional',
                                dependencies + (self.indices[chosen],))


def interval_certificate(node, graph, budget):
    """Refute local premises plus the negated conclusion by exact intervals."""
    from .rules import _bound, _is_false

    if node.conclusion is None:
        return None
    literals = [(graph.node(parent).conclusion, False) for parent in node.parents]
    if not _is_false(node.conclusion, graph):
        conclusion = graph.term(node.conclusion)
        clauses = conclusion.arguments if conclusion.operator == 'or' else (node.conclusion,)
        literals.extend((clause, True) for clause in clauses)
    bounds = tuple(bound for term, negated in literals
                   for bound in (_bound(term, negated, graph, True),) if bound is not None)
    state = _Propagation(graph, bounds, budget)
    # ponytail: bounded propagation may miss slowly converging systems; replace
    # with a work queue/stronger certificate search when such inputs require it.
    for _ in range(2 * len(graph.terms) + 1):
        previous = len(state.steps)
        for index, bound in enumerate(bounds):
            state.constrain(bound, index)
            if state.conflict is not None:
                return state.certificate()
        for term in graph.terms:
            budget.checkpoint('proof analysis')
            state.evaluate(term)
            if state.conflict is not None:
                return state.certificate()
        state.congruence()
        if state.conflict is not None:
            return state.certificate()
        conclusion = graph.term(node.conclusion)
        candidates = (conclusion.arguments if conclusion.operator_kind == 'builtin' and
                      conclusion.operator == 'or' else (node.conclusion,))
        for candidate in candidates:
            equality = graph.term(candidate)
            if (equality.operator_kind == 'builtin' and equality.operator == '=' and
                    len(equality.arguments) == 2 and all(term in state.indices for term in equality.arguments)):
                left, right = (state.values[term] for term in equality.arguments)
                if (left.lower == left.upper == right.lower == right.upper and
                        not any((left.lower_open, left.upper_open, right.lower_open, right.upper_open))):
                    return state.certificate(tuple(state.indices[term] for term in equality.arguments))
        if len(state.steps) == previous:
            break
    return None
