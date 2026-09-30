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

    def reciprocal(self):
        """Invert a nonempty interval excluding zero, retaining open endpoints."""
        if self.empty() or self.contains_zero():
            return None
        lower = (-inf if self.upper == 0 else Fraction(0) if self.upper == inf
                 else Fraction(1) / self.upper)
        upper = (inf if self.lower == 0 else Fraction(0) if self.lower == -inf
                 else Fraction(1) / self.lower)
        return _Range(lower, upper, self.upper_open, self.lower_open)

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
        from .rules import _affine, _square_base

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
                    base = _square_base(term, self.graph)
                    key = (('square', term.sort, signatures[base]) if base is not None else
                           (term.kind, term.sort, term.operator, term.parameters,
                            tuple(signatures[child] for child in term.arguments)))
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
        for term in self.graph.terms:
            self.budget.checkpoint('proof analysis')
            if term.sort not in ('Int', 'Real'):
                continue
            vector = _affine(term.term_id, self.graph, True)
            if vector is None:
                continue
            constant, coefficients, used = vector.pop(None, Fraction(0)), {}, set()
            for atom, weight in vector.items():
                key = signature(atom)
                coefficients[key] = coefficients.get(key, Fraction(0)) + weight
                used.update(dependencies[atom])
            if used and not any(coefficients.values()):
                self.record(term.term_id, _Range(constant, constant, False, False), 'congruence_sum',
                            substitutions=tuple(self.equalities[index] for index in sorted(used)))
                if self.conflict is not None:
                    return
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
        from .rules import _affine

        relation = self.graph.term(bound.term_id)
        while relation.operator == 'not':
            relation = self.graph.term(relation.arguments[0])
        coefficients = {term: Fraction(value) for term, value in bound.coefficients}
        for side in relation.arguments:
            vector = _affine(side, self.graph, True)
            constant = vector.pop(None, Fraction(0))
            if len(vector) <= 1 or set(vector) != set(coefficients):
                continue
            first = next(iter(vector))
            factor = coefficients[first] / vector[first]
            if any(coefficients[key] != factor * value for key, value in vector.items()):
                continue
            endpoint = constant - Fraction(bound.constant) / factor
            value = (_Range(endpoint, endpoint, False, False) if bound.relation == 'eq' else
                     _Range(-inf, endpoint, True, bound.relation == 'lt') if factor > 0 else
                     _Range(endpoint, inf, bound.relation == 'lt', True))
            self.record(side, value, 'linear', bound_index=bound_index)
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
        if self.conflict is None and term.operator == '*' and len(args) == 2 and term.term_id in self.indices:
            for child, divisor in ((args[0], args[1]), (args[1], args[0])):
                factor = self.values.get(divisor, _Range())
                inverse = factor.reciprocal()
                if inverse is not None:
                    self.record(child, self.values[term.term_id].multiply(inverse), 'product_inverse',
                                (self.indices[term.term_id], self.indices[divisor]))
                    if self.conflict is not None:
                        return


def interval_certificate(node, graph, budget):
    """Refute local premises plus the negated conclusion by exact intervals."""
    from .rules import _bound, _clause_literals, _is_false

    if node.conclusion is None:
        return None
    literals = [(graph.node(parent).conclusion, False) for parent in node.parents]
    if not _is_false(node.conclusion, graph):
        conclusion = graph.term(node.conclusion)
        clauses = _clause_literals(conclusion)
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
        candidates = _clause_literals(conclusion)
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


def _step_range(step):
    return _Range(-inf if step.lower is None else Fraction(step.lower),
                  inf if step.upper is None else Fraction(step.upper),
                  step.lower_open, step.upper_open)


def _congruent_signatures(graph, equalities, budget):
    """Canonicalize exact local equalities and builtin expression structure."""
    from .rules import _square_base

    groups = {}
    for equality in equalities:
        members = groups.get(equality.left_id, {equality.left_id}) | groups.get(equality.right_id, {equality.right_id})
        for key in members:
            groups[key] = members
    signatures, interned = {}, {}
    for term in graph.terms:
        budget.checkpoint('proof analysis')
        if term.term_id in groups:
            key = ('equal', min(groups[term.term_id]))
        elif term.kind == 'application' and term.operator_kind == 'builtin':
            base = _square_base(term, graph)
            key = (('square', term.sort, signatures[base]) if base is not None else
                   (term.kind, term.sort, term.operator, term.parameters,
                    tuple(signatures[child] for child in term.arguments)))
        else:
            key = ('term', term.term_id)
        signatures[term.term_id] = interned.setdefault(key, len(interned))
    return signatures


def _replay_step(step, certificate, graph, budget):
    """Compute a single proposed range from its recorded premises only."""
    from .rules import _affine, _bound

    term = graph.term(step.term_id)
    parents = tuple(certificate.steps[index] for index in step.premises)
    values = {}
    for parent in parents:
        values[parent.term_id] = values.get(parent.term_id, _Range()).intersect(_step_range(parent))
    args = term.arguments
    operands = [values.get(key, _Range()) for key in args]
    if step.rule == 'intersection':
        if len(parents) == 2 and all(parent.term_id == step.term_id for parent in parents):
            return (values[step.term_id],)
        return ()
    if step.rule in ('congruence', 'congruence_sum'):
        if any(equality not in _equalities(certificate.bounds, graph) for equality in step.substitutions):
            return ()
        signatures = _congruent_signatures(graph, step.substitutions, budget)
        if step.rule == 'congruence':
            if len(parents) == 1 and signatures[parents[0].term_id] == signatures[step.term_id]:
                return (_step_range(parents[0]),)
            return ()
        vector = _affine(step.term_id, graph, True)
        if vector is None:
            return ()
        constant, total = vector.pop(None, Fraction(0)), {}
        for key, weight in vector.items():
            signature = signatures[key]
            total[signature] = total.get(signature, Fraction(0)) + weight
        return (_Range(constant, constant, False, False),) if not any(total.values()) else ()
    if step.rule == 'linear':
        bound = certificate.bounds[step.bound_index]
        coefficients = {key: Fraction(value) for key, value in bound.coefficients}
        ranges = []
        vector = _affine(step.term_id, graph, True)
        if vector is None:
            return ()
        constant = vector.pop(None, Fraction(0))
        if len(vector) > 1 and set(vector) == set(coefficients):
            first = next(iter(vector))
            factor = coefficients[first] / vector[first]
            if factor and all(coefficients[key] == factor * value for key, value in vector.items()):
                endpoint = constant - Fraction(bound.constant) / factor
                ranges.append(_Range(endpoint, endpoint, False, False) if bound.relation == 'eq' else
                              _Range(-inf, endpoint, True, bound.relation == 'lt') if factor > 0 else
                              _Range(endpoint, inf, bound.relation == 'lt', True))
        if step.term_id in coefficients:
            for sign in ((1, -1) if bound.relation == 'eq' else (1,)):
                other = _Range(Fraction(bound.constant) * sign, Fraction(bound.constant) * sign, False, False)
                for key, weight in coefficients.items():
                    if key != step.term_id:
                        other = other.add(values.get(key, _Range()).scale(sign * weight))
                if other.lower == -inf:
                    continue
                weight = coefficients[step.term_id] * sign
                endpoint, opened = -other.lower / weight, other.lower_open or bound.relation == 'lt'
                ranges.append(_Range(-inf, endpoint, True, opened) if weight > 0 else
                              _Range(endpoint, inf, opened, True))
        return tuple(ranges)
    if step.rule == 'product_inverse':
        if len(parents) != 2:
            return ()
        product, divisor = (graph.term(parent.term_id) for parent in parents)
        factor = _step_range(parents[1])
        inverse = factor.reciprocal()
        if (product.operator_kind != 'builtin' or product.operator != '*' or
                len(product.arguments) != 2 or
                product.arguments not in ((step.term_id, divisor.term_id), (divisor.term_id, step.term_id)) or
                inverse is None):
            return ()
        return (_step_range(parents[0]).multiply(inverse),)
    if term.operator_kind != 'builtin':
        return ()
    if step.rule == 'literal' and term.kind == 'literal' and not parents:
        value = Fraction(term.value)
        return (_Range(value, value, False, False),)
    if step.rule == 'square' and term.operator == '*' and len(args) == 2 and args[0] == args[1]:
        return (operands[0].square(),)
    if step.rule == 'product' and term.operator == '*' and args:
        value = _Range(Fraction(1), Fraction(1), False, False)
        for operand in operands:
            value = value.multiply(operand)
        return (value,)
    if step.rule == 'sum' and term.operator in ('+', '-', 'uminus') and args:
        value = operands[0].scale(-1) if len(args) == 1 and term.operator != '+' else operands[0]
        for operand in operands[1:]:
            value = value.add(operand.scale(1 if term.operator == '+' else -1))
        return (value,)
    if step.rule == 'cast' and term.operator == 'to_real' and len(args) == 1:
        return (operands[0],)
    if step.rule == 'power' and term.operator == '^' and len(args) == 2:
        exponent = operands[1]
        if (exponent.lower == exponent.upper and abs(exponent.lower) != inf and exponent.lower > 0 and
                not exponent.lower_open and not exponent.upper_open and Fraction(exponent.lower).denominator == 1):
            power = int(exponent.lower)
            base = operands[0] if power % 2 else operands[0].square()
            degree = power if power % 2 else power // 2
            return (_Range(_power_endpoint(base.lower, degree), _power_endpoint(base.upper, degree),
                           base.lower_open, base.upper_open),)
    if step.rule == 'conditional' and term.operator == 'ite' and len(args) == 3:
        bound = _bound(args[0], False, graph, True)
        if bound is None or bound.relation == 'eq':
            return ()
        value = _Range(Fraction(bound.constant), Fraction(bound.constant), False, False)
        for key, weight in bound.coefficients:
            value = value.add(values.get(key, _Range()).scale(Fraction(weight)))
        holds = value.upper < 0 or value.upper == 0 and (bound.relation == 'le' or value.upper_open)
        fails = value.lower > 0 or value.lower == 0 and (bound.relation == 'lt' or value.lower_open)
        if holds or fails:
            return (operands[1] if holds else operands[2],)
    return ()


def check_interval_certificate(node, graph, certificate, *, budget=None):
    """Replay recorded interval steps; never run the propagation search."""
    from .rules import _bound, _clause_literals, _is_false
    from ..budget import SolveBudget

    budget = SolveBudget(None) if budget is None else budget
    if node.conclusion is None or not certificate.steps:
        return False
    literals = {(graph.node(parent).conclusion, False) for parent in node.parents}
    if not _is_false(node.conclusion, graph):
        literals.update((key, True) for key in _clause_literals(graph.term(node.conclusion)))
    for bound in certificate.bounds:
        budget.checkpoint('proof analysis')
        if ((bound.term_id, bound.negated) not in literals or
                bound != _bound(bound.term_id, bound.negated, graph, True)):
            return False
    for index, step in enumerate(certificate.steps):
        budget.checkpoint('proof analysis')
        if (any(parent < 0 or parent >= index for parent in step.premises) or
                graph.term(step.term_id).sort not in ('Int', 'Real') or
                (step.rule == 'linear') != (step.bound_index is not None) or
                step.bound_index is not None and not 0 <= step.bound_index < len(certificate.bounds) or
                step.substitutions and step.rule not in ('congruence', 'congruence_sum')):
            return False
        candidates = _replay_step(step, certificate, graph, budget)
        if graph.term(step.term_id).sort == 'Int':
            candidates = tuple(value.integer() for value in candidates)
        if _step_range(step) not in candidates:
            return False
    if (certificate.conflict is None) == (certificate.equality is None):
        return False
    result = certificate.conflict if certificate.conflict is not None else certificate.equality
    if any(index < 0 or index >= len(certificate.steps) for index in result):
        return False
    left, right = (certificate.steps[index] for index in result)
    first, second = _step_range(left), _step_range(right)
    if certificate.conflict is not None:
        return left.term_id == right.term_id and first.intersect(second).empty()
    if not (first.lower == first.upper == second.lower == second.upper and abs(first.lower) != inf and
            not any((first.lower_open, first.upper_open, second.lower_open, second.upper_open))):
        return False
    return any(graph.term(key).operator_kind == 'builtin' and graph.term(key).operator == '=' and
               graph.term(key).arguments == (left.term_id, right.term_id)
               for key in _clause_literals(graph.term(node.conclusion)))
