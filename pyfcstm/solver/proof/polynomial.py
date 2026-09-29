"""Exact local polynomial sign certificates with independently replayable steps.

Arithmetic expressions are expanded into sparse rational polynomials. Unknown
numeric expressions, including algebraic values and fractional powers, remain
independent atoms. Search only adds squares, products of proved nonnegative
factors and rational nonnegative sums; it never queries a native solver.
"""

from dataclasses import replace
from fractions import Fraction
from itertools import combinations

from .core import PolynomialCertificate, PolynomialStep


class _SearchLimit(ValueError):
    """Sparse expansion or candidate elimination exceeded its bounded search."""


def _add(left, right, weight=Fraction(1)):
    result = dict(left)
    for key, value in right.items():
        result[key] = result.get(key, Fraction(0)) + weight * value
        if not result[key]:
            del result[key]
    return result


def _scale(polynomial, weight):
    return {key: value * weight for key, value in polynomial.items() if value * weight}


def _multiply(left, right, budget):
    result = {}
    for first, a in left.items():
        for second, b in right.items():
            budget.checkpoint('polynomial proof expansion')
            key = tuple(sorted(first + second))
            result[key] = result.get(key, Fraction(0)) + a * b
            if not result[key]:
                del result[key]
            # ponytail: bounded sparse expansion; retain unsupported evidence
            # when dense polynomials require a dedicated certificate search.
            if len(result) > 4096 or len(key) > 32:
                raise _SearchLimit('polynomial expansion limit')
    return result


def _packed(polynomial):
    return tuple((key, str(value)) for key, value in sorted(polynomial.items()))


def _unpacked(coefficients, graph):
    result = {}
    for monomial, value in coefficients:
        if tuple(sorted(monomial)) != monomial or monomial in result:
            raise ValueError('polynomial monomials must be unique and sorted')
        if any(graph.term(term).sort not in ('Int', 'Real') for term in monomial):
            raise ValueError('polynomial atoms must be arithmetic')
        rational = Fraction(value)
        if not rational:
            raise ValueError('polynomial coefficients must be nonzero')
        result[monomial] = rational
    return result


class _Normalizer:
    def __init__(self, graph, budget):
        self.graph, self.budget, self.values = graph, budget, {}

    def polynomial(self, term_id):
        pending = [(term_id, False)]
        while pending:
            self.budget.checkpoint('polynomial proof normalization')
            current, ready = pending.pop()
            if current in self.values:
                continue
            term = self.graph.term(current)
            if term.sort not in ('Int', 'Real'):
                raise ValueError('nonarithmetic polynomial expression')
            args, op = term.arguments, term.operator
            arithmetic = (term.kind == 'application' and term.operator_kind == 'builtin' and
                          op in ('+', '-', 'uminus', '*', '^', 'to_real'))
            valid = arithmetic and bool(args) and all(self.graph.term(arg).sort == term.sort for arg in args)
            if op in ('uminus', 'to_real'):
                valid = arithmetic and len(args) == 1
                if op == 'to_real':
                    valid = valid and term.sort == 'Real' and self.graph.term(args[0]).sort == 'Int'
            exponent = None
            if op == '^':
                valid = valid and len(args) == 2
                if valid:
                    power = self.graph.term(args[1])
                    if power.kind == 'literal' and power.operator_kind == 'builtin':
                        value = Fraction(power.value)
                        if value.denominator == 1 and 0 < value <= 32:
                            exponent = int(value)
                valid = valid and exponent is not None
            if term.kind == 'literal' and term.operator_kind == 'builtin':
                value = Fraction(term.value)
                result = {(): value} if value else {}
            elif not valid:
                result = {(current,): Fraction(1)}
            else:
                children = args[:1] if op == '^' else args
                if not ready:
                    pending.append((current, True))
                    pending.extend((child, False) for child in reversed(children))
                    continue
                values = [self.values[child] for child in children]
                if op in ('+', '-', 'uminus'):
                    result = _scale(values[0], -1) if op != '+' and len(values) == 1 else values[0]
                    for value in values[1:]:
                        result = _add(result, value, 1 if op == '+' else -1)
                elif op == 'to_real':
                    result = values[0]
                else:
                    result = {(): Fraction(1)}
                    for value in values if op == '*' else [values[0]] * exponent:
                        result = _multiply(result, value, self.budget)
            self.values[current] = result
        return self.values[term_id]

    def literal(self, term_id, negated):
        current, inverse = term_id, negated
        while current is not None:
            self.budget.checkpoint('polynomial proof normalization')
            term = self.graph.term(current)
            if term.operator_kind != 'builtin' or term.sort != 'Bool':
                return ()
            if term.operator != 'not' or len(term.arguments) != 1:
                break
            current, inverse = term.arguments[0], not inverse
        if current is None or term.operator not in ('<', '<=', '>', '>=', '=') or len(term.arguments) != 2:
            return ()
        left, right = (self.graph.term(arg) for arg in term.arguments)
        if left.sort not in ('Int', 'Real') or left.sort != right.sort:
            return ()
        difference = _add(self.polynomial(left.term_id), self.polynomial(right.term_id), -1)
        if term.operator == '=':
            return () if inverse else ((difference, False, '1'), (_scale(difference, -1), False, '-1'))
        positive = term.operator in ('>', '>=')
        polynomial = difference if positive != inverse else _scale(difference, -1)
        return ((polynomial, (term.operator in ('<', '>')) != inverse, '1'),)


def _local_literals(node, graph):
    if node.conclusion is None:
        return ()
    literals = [(graph.node(parent).conclusion, False) for parent in node.parents]
    conclusion = graph.term(node.conclusion)
    if not (conclusion.kind == 'literal' and conclusion.operator_kind == 'builtin' and
            conclusion.sort == 'Bool' and conclusion.value == 'false'):
        clauses = (conclusion.arguments if conclusion.operator_kind == 'builtin' and
                   conclusion.operator == 'or' and conclusion.sort == 'Bool' else (node.conclusion,))
        literals.extend((clause, True) for clause in clauses)
    return tuple(literals)


def _contradiction(polynomial, strict):
    return not any(polynomial_key for polynomial_key in polynomial) and (
        polynomial.get((), 0) < 0 or polynomial.get((), 0) == 0 and strict)


def _eliminate(rows, budget):
    """Return exact positive combination weights, treating monomials as atoms."""
    while rows:
        unique = {}
        for polynomial, strict, weights in rows:
            budget.checkpoint('polynomial proof elimination')
            if _contradiction(polynomial, strict):
                return weights
            variables = set(polynomial) - {()}
            if not variables:
                continue
            factor = abs(polynomial[min(variables)])
            polynomial, weights = _scale(polynomial, 1 / factor), _scale(weights, 1 / factor)
            key = tuple(sorted((m, c) for m, c in polynomial.items() if m))
            previous = unique.get(key)
            if previous is None or (-polynomial.get((), 0), strict) > (-previous[0].get((), 0), previous[1]):
                unique[key] = polynomial, strict, weights
        rows = list(unique.values())
        variables = set().union(*(set(p) - {()} for p, _, _ in rows))
        if not variables:
            return None
        pivot = min(variables, key=lambda variable: (
            sum(p.get(variable, 0) > 0 for p, _, _ in rows) *
            sum(p.get(variable, 0) < 0 for p, _, _ in rows), variable))
        positive = [row for row in rows if row[0].get(pivot, 0) > 0]
        negative = [row for row in rows if row[0].get(pivot, 0) < 0]
        rows = [row for row in rows if pivot not in row[0]]
        for left, left_strict, left_weights in positive:
            for right, right_strict, right_weights in negative:
                budget.checkpoint('polynomial proof elimination')
                factor = -left[pivot] / right[pivot]
                rows.append((_add(left, right, factor), left_strict or right_strict,
                             _add(left_weights, right_weights, factor)))
                if len(rows) > 4096:
                    raise _SearchLimit('polynomial elimination limit')
    return None


class _Search:
    def __init__(self, node, graph, budget):
        self.graph, self.budget = graph, budget
        self.facts, self.steps, self.signs = [], [], {}
        normalizer = _Normalizer(graph, budget)
        for term_id, negated in _local_literals(node, graph):
            for polynomial, strict, multiplier in normalizer.literal(term_id, negated):
                self.record(polynomial, strict, 'input', term_id=term_id, negated=negated, multiplier=multiplier)
        self.initial = tuple(self.facts)

    def record(self, polynomial, strict, rule, **kwargs):
        self.facts.append((polynomial, strict))
        self.steps.append(PolynomialStep(_packed(polynomial), strict, rule, **kwargs))
        return len(self.steps) - 1

    def square(self, polynomial):
        strict = bool(polynomial) and set(polynomial) == {()}
        return self.record(_multiply(polynomial, polynomial, self.budget), strict,
                           'square', factor=_packed(polynomial))

    def product(self, first, second):
        left, a = self.facts[first]
        right, b = self.facts[second]
        return self.record(_multiply(left, right, self.budget), a and b, 'product', premises=(first, second))

    def combination(self, weights):
        result, strict = {}, False
        for index, weight in weights.items():
            self.budget.checkpoint('polynomial proof combination')
            polynomial, positive = self.facts[index]
            result = _add(result, polynomial, weight)
            strict = strict or positive and weight > 0
        used = sorted(index for index, weight in weights.items() if weight)
        return self.record(result, strict, 'sum', premises=tuple(used),
                           weights=tuple(str(weights[index]) for index in used))

    def sign(self, target):
        key = _packed(target)
        if key in self.signs:
            return self.signs[key]
        rows = [(p, s, {index: Fraction(1)}) for index, (p, s) in enumerate(self.facts)
                if all(len(m) <= 1 for m in p)]
        goal = len(self.facts)
        for strict in (True, False):
            self.budget.checkpoint('polynomial factor sign')
            weights = _eliminate(rows + [(_scale(target, -1), not strict, {goal: Fraction(1)})], self.budget)
            if weights is None or not weights.get(goal):
                continue
            factor = weights.pop(goal)
            weights = _scale(weights, 1 / factor)
            actual = {}
            for index, weight in weights.items():
                actual = _add(actual, self.facts[index][0], weight)
            margin = _add(target, actual, -1)
            if margin:
                weights[self.square({(): Fraction(1)})] = margin[()]
            result = self.combination(weights)
            self.signs[key] = result
            return result
        self.signs[key] = None
        return None

    def finish(self):
        rows = [(polynomial, strict, {index: Fraction(1)})
                for index, (polynomial, strict) in enumerate(self.facts)]
        weights = _eliminate(rows, self.budget)
        if weights is None:
            return None
        self.combination(weights)
        pending, used = [len(self.steps) - 1], set()
        while pending:
            self.budget.checkpoint('polynomial certificate pruning')
            index = pending.pop()
            if index not in used:
                used.add(index)
                pending.extend(self.steps[index].premises)
        order = sorted(used)
        positions = {old: new for new, old in enumerate(order)}
        return PolynomialCertificate(tuple(replace(self.steps[index], premises=tuple(
            positions[parent] for parent in self.steps[index].premises)) for index in order))

    def generate(self):
        result = self.finish()
        if result is not None:
            return result
        atoms = {atom for polynomial, _ in self.initial for monomial in polynomial for atom in monomial}
        squares = []
        for polynomial, _ in self.initial:
            for monomial in polynomial:
                self.budget.checkpoint('polynomial square candidates')
                if monomial and all(monomial.count(atom) % 2 == 0 for atom in set(monomial)):
                    half = tuple(sorted(atom for atom in set(monomial) for _ in range(monomial.count(atom) // 2)))
                    squares.append({half: Fraction(1)})
        squares.extend({(left,): Fraction(1), (right,): Fraction(-1)} for left, right in combinations(sorted(atoms), 2))
        for polynomial in squares:
            square = _multiply(polynomial, polynomial, self.budget)
            if any(set(square) <= set(bound) for bound, _ in self.initial):
                self.square(polynomial)
        result = self.finish()
        if result is not None:
            return result
        squared = {monomial[0] for polynomial, _ in self.initial for monomial in polynomial
                   if len(monomial) == 2 and monomial[0] == monomial[1]}
        if squared:
            squared.update(atoms)
        pairs = []
        for polynomial, _ in self.initial:
            if polynomial and all(len(m) == 1 and m[0] in squared for m in polynomial):
                positive = {m: c for m, c in polynomial.items() if c > 0}
                negative = {m: -c for m, c in polynomial.items() if c < 0}
                if positive and negative:
                    pairs.append((positive, negative))
        for first, second in combinations(sorted(squared), 2):
            left, right = {(first,): Fraction(1)}, {(second,): Fraction(1)}
            pairs.extend(((left, right), (right, left), (_scale(left, -1), _scale(right, -1)),
                          (_scale(right, -1), _scale(left, -1))))
        for left, right in pairs:
            self.budget.checkpoint('polynomial order candidates')
            difference = self.sign(_add(left, right, -1))
            total = self.sign(_add(left, right)) if difference is not None else None
            if total is not None:
                self.product(difference, total)
                result = self.finish()
                if result is not None:
                    return result
        for first, second in combinations(sorted(squared), 2):
            self.budget.checkpoint('polynomial product candidates')
            left, right = self.sign({(first,): Fraction(1)}), self.sign({(second,): Fraction(1)})
            if left is not None and right is not None:
                self.product(left, right)
                result = self.finish()
                if result is not None:
                    return result
        cubed = {monomial[0] for polynomial, _ in self.initial for monomial in polynomial
                 if len(monomial) == 3 and len(set(monomial)) == 1}
        for first, second in combinations(sorted(cubed), 2):
            for a, b in ((first, second), (second, first)):
                self.budget.checkpoint('polynomial cubic candidates')
                left, right = {(a,): Fraction(1)}, {(b,): Fraction(1)}
                difference = self.sign(_add(left, right, -1))
                if difference is not None:
                    self.product(difference, self.product(difference, difference))
                    self.product(difference, self.square(_add(left, right)))
                    result = self.finish()
                    if result is not None:
                        return result
        return None


def polynomial_certificate(node, graph, budget):
    """Refute local parents and negated conclusion by exact polynomial signs.

    :return: A dependency-pruned certificate, or ``None`` when this bounded
        algebraic search does not establish a local contradiction.
    """
    if node.conclusion is None:
        return None
    try:
        return _Search(node, graph, budget).generate()
    except _SearchLimit:
        # Sparse normalization/elimination deliberately limits combinatorial expansion.
        return None


def check_polynomial_certificate(node, graph, certificate):
    """Replay a detached local certificate without trusting search or a solver.

    :return: Whether every leaf belongs to this inference, every arithmetic
        identity and sign is exact, and the final step is a contradiction.
    """
    from ..budget import SolveBudget

    budget = SolveBudget(None)
    try:
        normalizer = _Normalizer(graph, budget)
        inputs = {}
        for term_id, negated in _local_literals(node, graph):
            for polynomial, strict, multiplier in normalizer.literal(term_id, negated):
                inputs[term_id, negated, multiplier] = (polynomial, strict)
        facts = []
        for index, step in enumerate(certificate.steps):
            polynomial = _unpacked(step.coefficients, graph)
            if type(step.strict) is not bool or any(type(parent) is not int or not 0 <= parent < index
                                                    for parent in step.premises):
                return False
            if step.rule == 'input':
                if (step.premises or step.weights or step.factor or
                        inputs.get((step.term_id, step.negated, step.multiplier)) != (polynomial, step.strict)):
                    return False
            elif step.term_id is not None or step.negated or step.multiplier != '1':
                return False
            elif step.rule == 'square':
                factor = _unpacked(step.factor, graph)
                strict = bool(factor) and set(factor) == {()}
                if (step.premises or step.weights or step.strict != strict or
                        polynomial != _multiply(factor, factor, budget)):
                    return False
            elif step.rule == 'product':
                if len(step.premises) != 2 or step.weights or step.factor:
                    return False
                left, right = (facts[parent] for parent in step.premises)
                if polynomial != _multiply(left[0], right[0], budget) or step.strict != (left[1] and right[1]):
                    return False
            elif step.rule == 'sum':
                if len(step.premises) != len(step.weights) or step.factor:
                    return False
                total, strict = {}, False
                for parent, value in zip(step.premises, step.weights):
                    weight = Fraction(value)
                    if weight < 0:
                        return False
                    total = _add(total, facts[parent][0], weight)
                    strict = strict or facts[parent][1] and weight > 0
                if polynomial != total or step.strict != strict:
                    return False
            else:
                return False
            facts.append((polynomial, step.strict))
        return bool(facts) and _contradiction(*facts[-1])
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        # KeyError: graph lookup names a missing term; ValueError/ZeroDivisionError:
        # malformed rational text or unsupported expansion; TypeError: malformed
        # detached monomial/step fields passed directly rather than through loading.
        return False
