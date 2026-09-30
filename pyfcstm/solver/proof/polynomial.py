"""Exact local polynomial sign certificates with independently replayable steps.

Arithmetic expressions are expanded into sparse rational polynomials. Algebraic
values and fractional powers remain polynomial atoms; semantic rules attach
domain-conditioned facts. Search composes signs, equalities and nonnegative
combinations. Z3 can search for combination weights; portable replay checks the
exact evidence without querying a native solver.
"""

from dataclasses import replace
from fractions import Fraction
from itertools import combinations
from math import factorial

from .core import PolynomialCertificate, PolynomialStep, ProofGap


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


def _power_polynomial(polynomial, exponent, budget):
    result = {(): Fraction(1)}
    for _ in range(exponent):
        result = _multiply(result, polynomial, budget)
    return result


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
            if inverse:
                return ((_multiply(difference, difference, self.budget), True, '1'),)
            return ((difference, False, '1'), (_scale(difference, -1), False, '-1'))
        positive = term.operator in ('>', '>=')
        polynomial = difference if positive != inverse else _scale(difference, -1)
        return ((polynomial, (term.operator in ('<', '>')) != inverse, '1'),)


def _complete_squares(polynomial, budget):
    """Complete rational squares, allowing bounded higher-degree monomials.

    For quadratics this is exact rational elimination of the symmetric form.
    Higher degrees use the same elimination on leading square monomials; a
    failed decomposition says nothing about the sign of the polynomial.
    """
    remainder, factors = dict(polynomial), []
    while any(remainder_key for remainder_key in remainder):
        budget.checkpoint('polynomial square decomposition')
        leading = min((m for m in remainder if m), key=lambda m: (-len(m), m))
        pivot = remainder[leading]
        if pivot < 0 or any(leading.count(atom) % 2 for atom in set(leading)):
            return ()
        base = tuple(sorted(atom for atom in set(leading) for _ in range(leading.count(atom) // 2)))
        factor = {base: Fraction(1)}
        for monomial, coefficient in remainder.items():
            if monomial == leading or any(monomial.count(atom) < base.count(atom) for atom in set(base)):
                continue
            other = list(monomial)
            for atom in base:
                other.remove(atom)
            factor[tuple(other)] = coefficient / (2 * pivot)
        remainder = _add(remainder, _multiply(factor, factor, budget), -pivot)
        factors.append(factor)
        # ponytail: bounded exact completion, not a complete SOS decision
        # procedure; larger witnesses remain an explicit search-limit gap.
        if len(factors) >= 256:
            raise _SearchLimit('polynomial square decomposition limit')
    return tuple(factors) if remainder.get((), 0) >= 0 else ()


def _residual_squares(polynomial, candidates, budget):
    """Try exact completion after removing one suggested nonnegative square."""
    degree = max((len(m) for m in polynomial), default=0)
    if degree <= 2 or polynomial[min(polynomial, key=lambda m: (-len(m), m))] < 0:
        return
    attempts, seen = 0, set()
    for factor in candidates:
        identity = _packed(factor)
        if identity in seen or any(2 * len(m) > degree for m in factor):
            continue
        seen.add(identity)
        square = _multiply(factor, factor, budget)
        if not square or not set(square) <= set(polynomial):
            continue
        for weight in sorted({polynomial[m] / value for m, value in square.items()
                              if polynomial[m] / value > 0}):
            budget.checkpoint('polynomial residual square candidates')
            attempts += 1
            # ponytail: bounded candidate search over observed monomials; a
            # larger SOS search needs a separate verified witness proposal.
            if attempts > 256:
                raise _SearchLimit('polynomial residual square candidate limit')
            yield from _complete_squares(_add(polynomial, square, -weight), budget)


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


def _prune_combination_rows(rows, budget):
    """Remove bounds whose nonnegative weight must be zero in a refutation."""
    if all(p.get((), 0) >= 0 for p, _, _ in rows):
        # A nonnegative combination can then only refute at constant zero;
        # positive constants cannot participate in that certificate.
        rows = [row for row in rows if not row[0].get((), 0)]
        if not any(strict for _, strict, _ in rows):
            return []
    while rows:
        # A column with only one sign cannot cancel in a nonnegative sum.
        # Its incident rows must have zero weight; repeat as their removal
        # can expose another one-sided column.
        signs = {}
        for polynomial, _, _ in rows:
            budget.checkpoint('polynomial coefficient support')
            for monomial, coefficient in polynomial.items():
                if monomial:
                    signs.setdefault(monomial, set()).add(coefficient > 0)
        one_sided = {m for m, values in signs.items() if len(values) == 1}
        if one_sided:
            rows = [row for row in rows if not one_sided.intersection(row[0])]
            continue
        return rows
    return []


def _eliminate(rows, budget, solver):
    """Eliminate sparse rows exactly; use Z3 before the row product grows."""
    while rows:
        rows = _prune_combination_rows(rows, budget)
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
        opposites = {_packed(p): row for row in rows for p, strict, _ in (row,) if not strict}
        equality = next((row for row in rows if not row[1] and
                         _packed(_scale(row[0], -1)) in opposites), None)
        if equality is not None:
            pivot = max(set(equality[0]) - {()}, key=lambda m: (len(m), m))
            inverse = opposites[_packed(_scale(equality[0], -1))]
            reduced = []
            for polynomial, strict, weights in rows:
                coefficient = polynomial.get(pivot, 0)
                if coefficient:
                    other, _, other_weights = equality if coefficient * equality[0][pivot] < 0 else inverse
                    factor = -coefficient / other[pivot]
                    polynomial = _add(polynomial, other, factor)
                    weights = _add(weights, other_weights, factor)
                reduced.append((polynomial, strict, weights))
            rows = reduced
            continue
        if len(rows) > 32:
            return _solve_weights(rows, budget, solver)
        pivot = min(variables, key=lambda variable: (
            sum(p.get(variable, 0) > 0 for p, _, _ in rows) *
            sum(p.get(variable, 0) < 0 for p, _, _ in rows), variable))
        positive = [row for row in rows if row[0].get(pivot, 0) > 0]
        negative = [row for row in rows if row[0].get(pivot, 0) < 0]
        # Avoid Fourier--Motzkin's Cartesian explosion; the existing native
        # linear solver supplies exact coefficients for the same certificate.
        if len(positive) * len(negative) > 64:
            return _solve_weights(rows, budget, solver)
        rows = [row for row in rows if pivot not in row[0]]
        for left, left_strict, left_weights in positive:
            for right, right_strict, right_weights in negative:
                budget.checkpoint('polynomial proof elimination')
                factor = -left[pivot] / right[pivot]
                rows.append((_add(left, right, factor), left_strict or right_strict,
                             _add(left_weights, right_weights, factor)))
    return None


def _solve_weights(rows, budget, solver):
    """Find nonnegative rational combination weights with Z3's linear solver.

    The solver's SAT model supplies candidate coefficients, not a trusted
    contradiction. Detached replay checks their exact sum independently.
    """
    import z3

    budget.checkpoint('polynomial coefficient search')
    solver.reset()
    solver.set(timeout=budget.remaining_ms() or 0)
    ctx = solver.ctx
    variables = [z3.Real('weight%d' % index, ctx=ctx) for index in range(len(rows))]
    columns, strict_weights = {}, []
    for variable, (polynomial, strict, _) in zip(variables, rows):
        budget.checkpoint('polynomial coefficient search')
        solver.add(variable >= 0)
        for monomial, coefficient in polynomial.items():
            columns.setdefault(monomial, []).append(variable * z3.RealVal(str(coefficient), ctx=ctx))
        if strict:
            strict_weights.append(variable)
    zero = z3.RealVal(0, ctx=ctx)
    constant = z3.Sum(columns.pop((), [zero]))
    solver.add(*[z3.Sum(column) == 0 for column in columns.values()])
    solver.add(constant <= 0, z3.Or(constant < 0, z3.Sum(strict_weights or [zero]) > 0))
    result = solver.check()
    budget.checkpoint('polynomial coefficient search')
    if result != z3.sat:
        return None
    model, weights = solver.model(), {}
    for variable, (_, _, source_weights) in zip(variables, rows):
        value = model.eval(variable, model_completion=True)
        coefficient = Fraction(value.numerator_as_long(), value.denominator_as_long())
        weights = _add(weights, source_weights, coefficient)
    return weights


class _Search:
    def __init__(self, node, graph, budget):
        import z3

        self.graph, self.budget = graph, budget
        self.weight_solver = z3.SolverFor('QF_LRA', ctx=z3.Context())
        self.facts, self.steps, self.signs = [], [], {}
        self.fact_indices = {}
        self.rewritten = set()
        self.dependencies = {}
        self.limits = set()
        normalizer = self.normalizer = _Normalizer(graph, budget)
        pending = [term for term, _ in _local_literals(node, graph) if term is not None]
        reached = set()
        while pending:
            budget.checkpoint('polynomial local expressions')
            current = pending.pop()
            if current not in reached:
                reached.add(current)
                pending.extend(graph.term(current).arguments)
        self.local_terms = tuple(sorted(reached))
        for term_id, negated in _local_literals(node, graph):
            for polynomial, strict, multiplier in normalizer.literal(term_id, negated):
                self.record(polynomial, strict, 'input', term_id=term_id, negated=negated, multiplier=multiplier)
        self.initial = tuple(self.facts)

    def record(self, polynomial, strict, rule, **kwargs):
        key = _packed(polynomial), strict
        if key in self.fact_indices:
            return self.fact_indices[key]
        # A nonnegative linear combination adds no information to the cone
        # queried by sign(). Preserve its cached results until a new axiom,
        # product or equality multiple actually enlarges that cone.
        if rule != 'sum':
            roots = {self.component(m) for m in polynomial if m}
            if roots:
                root = min(roots)
                for other in roots:
                    self.dependencies[other] = root
                for target in tuple(self.signs):
                    if any(m and self.component(m) == root for m, _ in target):
                        del self.signs[target]
            else:
                self.signs.clear()
        self.facts.append((polynomial, strict))
        self.steps.append(PolynomialStep(_packed(polynomial), strict, rule, **kwargs))
        index = len(self.steps) - 1
        self.fact_indices[key] = index
        return index

    def component(self, monomial):
        """Find connected columns of the linearized polynomial constraints."""
        self.dependencies.setdefault(monomial, monomial)
        while self.dependencies[monomial] != monomial:
            self.dependencies[monomial] = self.dependencies[self.dependencies[monomial]]
            monomial = self.dependencies[monomial]
        return monomial

    def square(self, polynomial):
        strict = bool(polynomial) and set(polynomial) == {()}
        return self.record(_multiply(polynomial, polynomial, self.budget), strict,
                           'square', factor=_packed(polynomial))

    def product(self, first, second):
        left, a = self.facts[first]
        right, b = self.facts[second]
        return self.record(_multiply(left, right, self.budget), a and b, 'product', premises=(first, second))

    def combination(self, weights):
        pending, flattened = dict(weights), {}
        while pending:
            self.budget.checkpoint('polynomial proof combination')
            index = max(pending)
            weight = pending.pop(index)
            step = self.steps[index]
            if step.rule == 'sum':
                for parent, value in zip(step.premises, step.weights):
                    pending[parent] = pending.get(parent, Fraction(0)) + weight * Fraction(value)
            else:
                flattened[index] = flattened.get(index, Fraction(0)) + weight
        weights = flattened
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
        known = self.fact_indices.get((key, True))
        if known is not None:
            return known
        if key in self.signs:
            return self.signs[key]
        rows = [(p, s, {index: Fraction(1)}) for index, (p, s) in enumerate(self.facts)]
        goal = len(self.facts)
        for strict in (True, False):
            self.budget.checkpoint('polynomial factor sign')
            known = self.fact_indices.get((key, False)) if not strict else None
            if known is not None:
                self.signs[key] = known
                return known
            weights = _eliminate(rows + [(_scale(target, -1), not strict, {goal: Fraction(1)})], self.budget, self.weight_solver)
            if weights is None or not weights.get(goal):
                continue
            factor = weights.pop(goal)
            weights = _scale(weights, 1 / factor)
            actual = {}
            for index, weight in weights.items():
                actual = _add(actual, self.facts[index][0], weight)
            margin = _add(target, actual, -1)
            if margin:
                unit = self.square({(): Fraction(1)})
                weights[unit] = weights.get(unit, Fraction(0)) + margin[()]
            result = self.combination(weights)
            self.signs[key] = result
            return result
        self.signs[key] = None
        return None

    def finish(self):
        rows = [(polynomial, strict, {index: Fraction(1)})
                for index, (polynomial, strict) in enumerate(self.facts)]
        weights = _eliminate(rows, self.budget, self.weight_solver)
        if weights is None:
            return None
        root = self.combination(weights)
        pending, used = [root], set()
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
        # A concrete zero assignment disproves the possibility of refuting
        # these pure polynomial premises. Opaque operation atoms (roots,
        # division, powers, etc.) may have additional semantic constraints,
        # so their arbitrary zero values are not a witness.
        atoms = {atom for polynomial, _ in self.initial for monomial in polynomial for atom in monomial}
        if (all(p.get((), 0) > 0 or p.get((), 0) == 0 and not strict for p, strict in self.initial) and
                all(self.graph.term(atom).kind == 'constant' and
                    self.graph.term(atom).operator_kind == 'uninterpreted' for atom in atoms)):
            return None
        # New semantic facts can enable products and vice versa. Revisit the
        # same local candidates until their shared evidence stops growing.
        while len(self.facts) < 256:
            before = len(self.facts)
            result = self.deduce()
            if result is not None:
                return result
            if len(self.facts) == before:
                break
        if len(self.facts) >= 256:
            self.limits.add('polynomial fact limit')
            # A limit stops generating candidates, not checking the facts
            # already available. They can still contain an exact refutation.
            return self.finish()
        return None

    def deduce(self):
        before = len(self.facts)
        result = self.finish()
        if result is not None:
            return result
        from .semantics import add_semantic_facts

        add_semantic_facts(self)
        result = self.finish()
        if result is not None:
            return result
        atoms = {atom for polynomial, _ in self.initial for monomial in polynomial for atom in monomial}
        squares = []
        bases = {()}
        for polynomial, _ in self.initial:
            for monomial in polynomial:
                self.budget.checkpoint('polynomial square candidates')
                if monomial and all(monomial.count(atom) % 2 == 0 for atom in set(monomial)):
                    half = tuple(sorted(atom for atom in set(monomial) for _ in range(monomial.count(atom) // 2)))
                    squares.append({half: Fraction(1)})
                    bases.add(half)
        squares.extend({(left,): Fraction(1), (right,): Fraction(-1)} for left, right in combinations(sorted(atoms), 2))
        # Original terms suggest unconditional square identities only. Their
        # branch assumptions never become facts in this local inference.
        explicit_bases = set()
        for term in self.graph.terms:
            self.budget.checkpoint('polynomial square candidates')
            if term.operator_kind != 'builtin' or term.sort not in ('Int', 'Real'):
                continue
            if term.operator == '^' and len(term.arguments) == 2:
                exponent = self.graph.term(term.arguments[1])
                if (exponent.kind == 'literal' and exponent.operator_kind == 'builtin' and
                        Fraction(exponent.value) == 2):
                    explicit_bases.add(term.arguments[0])
            elif term.operator == '*' and len(term.arguments) == 2 and term.arguments[0] == term.arguments[1]:
                explicit_bases.add(term.arguments[0])
        for term_id in sorted(explicit_bases):
            try:
                squares.append(self.normalizer.polynomial(term_id))
            except _SearchLimit as error:
                # A suggested factor from another input can exceed sparse
                # expansion limits; it must not abort checking local evidence.
                self.limits.add(str(error))
        squares.extend({left: Fraction(1), right: Fraction(-1)}
                       for left, right in combinations(sorted(bases), 2))
        residual_bases = tuple(squares)
        for polynomial, _ in self.initial:
            for sign in (1, -1):
                try:
                    oriented = _scale(polynomial, sign)
                    completed = _complete_squares(oriented, self.budget)
                    squares.extend(completed)
                    if not completed:
                        squares.extend(_residual_squares(oriented, residual_bases, self.budget))
                except _SearchLimit as error:
                    # Candidate completion can exceed its bound without making
                    # existing local facts or other candidate factors invalid.
                    self.limits.add(str(error))
        seen = set()
        degree = max((len(m) for p, _ in self.initial for m in p), default=0)
        for polynomial in squares:
            identity = _packed(polynomial)
            if identity in seen:
                continue
            seen.add(identity)
            if (any(len(m) * 2 > degree for m in polynomial) or
                    any(atom not in atoms for m in polynomial for atom in m)):
                continue
            square = _multiply(polynomial, polynomial, self.budget)
            if any(set(square) <= set(bound) for bound, _ in self.initial):
                self.square(polynomial)
                bound = self.sign(_scale(square, -1))
                if bound is not None:
                    if self.facts[bound][1]:
                        # The square is already strictly negative. Close this
                        # contradiction before deriving unnecessary zero factors.
                        return self.finish()
                    for orientation in (1, -1):
                        factor = _scale(polynomial, orientation)
                        self.record(factor, False, 'square_zero', premises=(bound,), factor=_packed(factor))
        self.cancel_products()
        result = self.finish()
        if result is not None:
            return result
        result = self.compose_equalities()
        if result is not None:
            return result
        squared = {monomial[0] for polynomial, _ in self.initial for monomial in polynomial
                   if len(monomial) == 2 and monomial[0] == monomial[1]}
        if squared:
            squared.update(atoms)
        pairs = []
        for polynomial, _ in self.initial:
            if polynomial:
                positive = {m: c for m, c in polynomial.items() if c > 0}
                negative = {m: -c for m, c in polynomial.items() if c < 0}
                if positive and negative:
                    pairs.append((positive, negative))
        explicit_pairs = len(pairs)
        for first, second in combinations(sorted(squared), 2):
            left, right = {(first,): Fraction(1)}, {(second,): Fraction(1)}
            pairs.extend(((left, right), (right, left), (_scale(left, -1), _scale(right, -1)),
                          (_scale(right, -1), _scale(left, -1))))
        for pair_index, (left, right) in enumerate(pairs):
            # Finish consequences of actual local bounds before guessing
            # orders between every pair of atoms. Joint product search can
            # already close the obligation without those speculative facts.
            if pair_index == explicit_pairs and len(self.facts) > before:
                result = self.compose_equalities()
                if result is None:
                    result = self.compose_products()
                if result is not None:
                    return result
            self.budget.checkpoint('polynomial order candidates')
            if max(len(m) for m in set(left) | set(right)) > 16:
                continue
            delta = _add(left, right, -1)
            if ((_packed(delta), False) in self.fact_indices and
                    (_packed(_scale(delta, -1)), False) in self.fact_indices):
                # Equality reduction already permits arbitrary polynomial
                # multipliers; multiplying this zero bound adds no sign fact.
                continue
            difference = self.sign(delta)
            total = self.sign(_add(left, right)) if difference is not None else None
            if total is not None:
                previous = len(self.facts)
                self.product(difference, total)
                if len(self.facts) == previous:
                    continue
                result = self.finish()
                if result is not None:
                    return result
        if len(self.facts) > before:
            return self.compose_products()
        for monomial in sorted({m for p, _ in self.initial for m in p if 0 < len(m) <= 16}):
            for orientation in (1, -1):
                sign = self.sign({monomial: Fraction(orientation)})
                if sign is not None and self.facts[sign][1]:
                    self.product(sign, sign)
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
        result = self.power_orders()
        if result is not None:
            return result
        result = self.compose_equalities()
        if result is not None:
            return result
        return self.compose_products()

    def power_orders(self):
        """Generate integer-power order identities for the actual local bases."""
        from .semantics import _power

        bases = {}
        for polynomial, _ in self.initial:
            for monomial in polynomial:
                if len(monomial) > 1 and len(set(monomial)) == 1:
                    bases.setdefault(len(monomial), set()).add(_packed({(monomial[0],): Fraction(1)}))
        for polynomial, _ in self.initial:
            for monomial, coefficient in polynomial.items():
                if len(monomial) > 1 and len(set(monomial)) == 1:
                    shift = polynomial.get(monomial[:-1], Fraction(0)) / (len(monomial) * coefficient)
                    if shift:
                        bases[len(monomial)].add(_packed({(monomial[0],): Fraction(1), (): shift}))
        for term_id in self.local_terms:
            parts = _power(term_id, self.graph, self.normalizer)
            if parts is not None and parts[1] is not None and parts[1].denominator == 1 and 1 < parts[1] <= 32:
                bases.setdefault(int(parts[1]), set()).add(_packed(parts[0]))
        for degree, candidates in sorted(bases.items()):
            for first, second in combinations(sorted(candidates), 2):
                for a, b in ((first, second), (second, first)):
                    for orientation in ((1,) if degree % 2 else (1, -1)):
                        self.budget.checkpoint('polynomial power order candidates')
                        left = {m: Fraction(c) * orientation for m, c in a}
                        right = {m: Fraction(c) * orientation for m, c in b}
                        difference = self.sign(_add(left, right, -1))
                        if difference is None:
                            continue
                        weights = {}
                        if degree % 2:
                            # a^n-b^n = 2^(1-n) sum_{k odd} C(n,k)(a-b)^k(a+b)^(n-k).
                            difference_power = difference
                            for k in range(1, degree + 1, 2):
                                if k > 1:
                                    difference_power = self.product(self.product(difference_power, difference), difference)
                                factor = _power_polynomial(_add(left, right), (degree - k) // 2, self.budget)
                                index = self.product(difference_power, self.square(factor))
                                weights[index] = Fraction(factorial(degree), factorial(k) * factorial(degree - k) * 2 ** (degree - 1))
                        else:
                            positive = self.sign(left), self.sign(right)
                            if any(index is None for index in positive):
                                continue
                            # a^n-b^n = (a-b) sum a^(n-1-k)b^k on the nonnegative half-line.
                            powers = [[self.square({(): Fraction(1)})] for _ in positive]
                            for values, base in zip(powers, positive):
                                for _ in range(degree - 1):
                                    values.append(self.product(values[-1], base))
                            for k in range(degree):
                                index = self.product(powers[0][degree - 1 - k], powers[1][k])
                                weights[index] = weights.get(index, Fraction(0)) + 1
                        combination = self.combination(weights)
                        if not degree % 2:
                            self.product(difference, combination)
                        result = self.finish()
                        if result is not None:
                            return result
        return None

    def cancel_products(self):
        """Compose known monomial signs and cancel strictly positive factors."""
        monomials = sorted({m for p, _ in self.facts for m in p if len(m) > 1})
        for monomial in monomials:
            factors = []
            for atom in monomial:
                factor = self.sign({(atom,): Fraction(1)})
                if factor is None:
                    factor = self.sign({(atom,): Fraction(-1)})
                if factor is None:
                    break
                factors.append(factor)
            else:
                product = factors[0]
                for factor in factors[1:]:
                    product = self.product(product, factor)
            for orientation in (1, -1):
                bound = self.sign({monomial: Fraction(orientation)})
                if bound is None:
                    continue
                for atom in sorted(set(monomial)):
                    for sign in (1, -1):
                        factor = self.sign({(atom,): Fraction(sign)})
                        if factor is not None and self.facts[bound][1] and not self.facts[factor][1]:
                            rest = list(monomial)
                            rest.remove(atom)
                            factor = self.record(self.facts[factor][0], True, 'positive_factor',
                                                 premises=(bound, factor), factor=_packed({
                                                     tuple(rest): Fraction(orientation * sign)}))
                        if factor is not None and self.facts[factor][1]:
                            rest = list(monomial)
                            rest.remove(atom)
                            self.record({tuple(rest): Fraction(orientation * sign)}, self.facts[bound][1],
                                        'cancel_positive', premises=(bound, factor))

    def compose_products(self):
        """Find a joint product witness before recording candidate evidence.

        Candidate bounds are nonnegative products of established bounds. The
        linear coefficient solver can cancel intermediate monomials across
        candidates, even when those monomials do not occur in the premises.
        Only products selected by its exact witness enter the evidence DAG.
        """
        facts = tuple(self.facts)
        rows = [(p, strict, {index: Fraction(1)}) for index, (p, strict) in enumerate(facts)]
        seen = {(_packed(p), strict) for p, strict in facts}
        products = {}
        degree = min(32, 2 * max((len(m) for p, _ in self.initial for m in p), default=0))
        factors = [(index, p, strict) for index, (p, strict) in enumerate(facts)
                   if index not in self.rewritten and self.steps[index].rule != 'equality_product' and any(p)]
        for offset, (first, left, a) in enumerate(factors):
            for second, right, b in factors[offset:]:
                if max(map(len, left)) + max(map(len, right)) > degree:
                    continue
                self.budget.checkpoint('polynomial product candidates')
                value = _multiply(left, right, self.budget)
                key = _packed(value), a and b
                if key in seen:
                    continue
                seen.add(key)
                index = len(rows)
                products[index] = first, second
                rows.append((value, a and b, {index: Fraction(1)}))
                # ponytail: bounded product basis; preserve an explicit limit
                # when this degree-bounded search cannot consider every pair.
                if len(products) >= 4096:
                    self.limits.add('polynomial product candidate limit')
                    break
            if len(products) >= 4096:
                break
        rows = _prune_combination_rows(rows, self.budget)
        if not rows:
            return None
        # Joint candidate pools are deliberately larger than the recorded
        # evidence. Native linear search avoids repeatedly expanding rational
        # substitution weights across thousands of speculative rows.
        weights = _solve_weights(rows, self.budget, self.weight_solver)
        if weights is None:
            return None
        selected = {}
        for index, weight in weights.items():
            actual = self.product(*products[index]) if index in products else index
            selected[actual] = selected.get(actual, Fraction(0)) + weight
        self.combination(selected)
        return self.finish()

    def compose_equalities(self):
        """Reduce local inequalities by established polynomial equalities.

        Graded lexicographic leading monomials strictly decrease at every
        substitution. Each substitution emits an equality product and a sum,
        so replay needs no knowledge of this search strategy.
        """
        from .semantics import add_semantic_facts

        add_semantic_facts(self)
        equations = []
        for index, (polynomial, strict) in enumerate(self.facts):
            opposite = self.fact_indices.get((_packed(_scale(polynomial, -1)), False))
            if not strict and polynomial and opposite is not None and index < opposite:
                leading = max(polynomial, key=lambda m: (len(m), m))
                if leading:
                    equations.append((index, opposite, leading))
        equations.sort(key=lambda item: (len(item[2]), item[2], item[0]))
        for target, (original, strict) in enumerate(tuple(self.facts)):
            polynomial = original
            while polynomial:
                replacement = None
                for monomial in sorted(polynomial, key=lambda m: (len(m), m), reverse=True):
                    for index, opposite, leading in equations:
                        remaining = list(monomial)
                        for atom in leading:
                            if atom not in remaining:
                                break
                            remaining.remove(atom)
                        else:
                            replacement = index, opposite, monomial, tuple(remaining)
                            break
                    if replacement is not None:
                        break
                if replacement is None:
                    break
                index, opposite, monomial, factor = replacement
                equality = self.facts[index][0]
                leading = max(equality, key=lambda m: (len(m), m))
                weight = -polynomial[monomial] / equality[leading]
                multiplier = {factor: weight}
                product = self.record(_multiply(equality, multiplier, self.budget), False,
                                      'equality_product', premises=(index, opposite), factor=_packed(multiplier))
                previous = target
                target = self.combination({target: Fraction(1), product: Fraction(1)})
                # Keep the original evidence for replay, but let its reduced
                # bound supply future product candidates. Equality multiples
                # are proof bookkeeping, not additional nonnegative factors.
                self.rewritten.add(previous)
                polynomial = self.facts[target][0]
                if _contradiction(polynomial, strict):
                    return self.finish()
                # ponytail: bounded local ideal reduction; larger elimination
                # retains an explicit gap instead of unbounded certificate search.
                if len(self.facts) >= 256:
                    return None
        return self.finish()


def polynomial_certificate(node, graph, budget, *, diagnostics=None):
    """Refute local parents and negated conclusion by exact polynomial signs.

    :return: A dependency-pruned certificate, or ``None`` when this bounded
        algebraic search does not establish a local contradiction.
    :param diagnostics: Optional list receiving the local failure reason.
    """
    if node.conclusion is None:
        return None
    reason, detail = 'proof_search_exhausted', 'bounded polynomial search found no certificate'
    try:
        search = _Search(node, graph, budget)
        certificate = search.generate()
        if search.limits:
            reason, detail = 'proof_search_limit', '; '.join(sorted(search.limits))
        if certificate is not None and not check_polynomial_certificate(node, graph, certificate, budget=budget):
            from .rules import _invalid_gap

            reason, detail = 'invalid_generated_certificate', 'generated polynomial certificate failed replay'
            _invalid_gap(node, reason, detail)
        elif certificate is not None:
            return certificate
    except _SearchLimit as err:
        # Sparse normalization/elimination deliberately limits combinatorial expansion.
        reason, detail = 'proof_search_limit', str(err)
    if diagnostics is not None:
        diagnostics.append(ProofGap(reason, node.node_id, detail))
    return None


def check_polynomial_certificate(node, graph, certificate, *, budget=None):
    """Replay a detached local certificate without trusting search or a solver.

    :param budget: Optional shared deadline for replay during live generation.
    :return: Whether every leaf belongs to this inference, every arithmetic
        identity and sign is exact, and the final step is a contradiction.
    """
    from ..budget import SolveBudget

    budget = SolveBudget(None) if budget is None else budget
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
            elif step.rule in ('power_sign', 'power_identity'):
                from .semantics import check_semantic_step

                if not check_semantic_step(step, graph, normalizer, facts):
                    return False
            elif step.term_id is not None or step.negated or step.multiplier != '1':
                return False
            elif step.rule == 'square':
                factor = _unpacked(step.factor, graph)
                strict = bool(factor) and set(factor) == {()}
                if (step.premises or step.weights or step.strict != strict or
                        polynomial != _multiply(factor, factor, budget)):
                    return False
            elif step.rule == 'square_zero':
                if len(step.premises) != 1 or step.weights or step.strict:
                    return False
                factor = _unpacked(step.factor, graph)
                if (polynomial != factor or facts[step.premises[0]][0] !=
                        _scale(_multiply(factor, factor, budget), -1)):
                    return False
            elif step.rule == 'cancel_positive':
                if len(step.premises) != 2 or step.weights or step.factor:
                    return False
                bound, factor = (facts[parent] for parent in step.premises)
                if (not factor[1] or step.strict != bound[1] or
                        _multiply(polynomial, factor[0], budget) != bound[0]):
                    return False
            elif step.rule == 'positive_factor':
                if len(step.premises) != 2 or step.weights or not step.strict:
                    return False
                bound, factor = (facts[parent] for parent in step.premises)
                if (not bound[1] or polynomial != factor[0] or
                        _multiply(polynomial, _unpacked(step.factor, graph), budget) != bound[0]):
                    return False
            elif step.rule == 'product':
                if len(step.premises) != 2 or step.weights or step.factor:
                    return False
                left, right = (facts[parent] for parent in step.premises)
                if polynomial != _multiply(left[0], right[0], budget) or step.strict != (left[1] and right[1]):
                    return False
            elif step.rule == 'equality_product':
                if len(step.premises) != 2 or step.weights or step.strict:
                    return False
                left, right = (facts[parent] for parent in step.premises)
                if (left[1] or right[1] or left[0] != _scale(right[0], -1) or
                        polynomial != _multiply(left[0], _unpacked(step.factor, graph), budget)):
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
