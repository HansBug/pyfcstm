"""Scope analysis and exact linear certificates for portable native proofs.

Arithmetic checks use rational arithmetic only. Recognized mechanical rules
remain explicitly solver-trusted until a dedicated checker is supplied; that
distinction is retained independently of whether their deductions are readable.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Tuple

from .core import (ArithmeticCertificate, CardinalityCertificate, CountContribution,
                    LinearBound, ProofGap, ProofGraph)


@dataclass(frozen=True)
class RuleAnalysis:
    """Interpret an existing inference without changing its formula or scope.

    :param kind: ``logical``, ``equality``, ``rewrite``, ``definition``,
        ``resolution`` or ``opaque``.
    :param local_check: ``checked``, ``trusted``, ``unsupported`` or ``invalid``.
        A plugin reporting ``checked`` supplies its own checker and is trusted
        Python code; this is not an independent certification of the plugin.
    """

    kind: str
    local_check: str = 'trusted'

    def __post_init__(self):
        if self.kind not in ('logical', 'equality', 'rewrite', 'definition', 'resolution', 'opaque'):
            raise ValueError('unknown inference kind')
        if self.local_check not in ('checked', 'trusted', 'unsupported', 'invalid'):
            raise ValueError('unknown local check')


@dataclass(frozen=True)
class ProofRuleHandler:
    """A per-call interpreter for one exact native rule name.

    :param rule: Native rule to interpret. Input and scope rules are reserved.
    :param interpret: Callable accepting a node and graph and returning
        :class:`RuleAnalysis`. It cannot replace conclusions or discharge
        hypotheses. Exceptions propagate to the caller.
    """

    rule: str
    interpret: Callable

    def __post_init__(self):
        if not isinstance(self.rule, str) or not self.rule:
            raise ValueError('rule must be a nonempty string')
        if not callable(self.interpret):
            raise TypeError('interpret must be callable')


def _index_handlers(handlers):
    result = {}
    for handler in handlers:
        if not isinstance(handler, ProofRuleHandler):
            raise TypeError('rule_handlers must contain ProofRuleHandler objects')
        if handler.rule in ('asserted', 'hypothesis', 'lemma'):
            raise ValueError('reserved rule: ' + handler.rule)
        if handler.rule in result:
            raise ValueError('duplicate rule handler: ' + handler.rule)
        result[handler.rule] = handler
    return result


@dataclass(frozen=True)
class ProofAnalysis:
    """Evidence after local inference and hypothesis-scope analysis.

    :param graph: Original evidence annotated with checks and hypotheses.
    :param scope_check: ``passed``, ``partial`` or ``failed``.
    :param rule_check: ``complete``, ``partial`` or ``failed``.
    :param gaps: Explicit unsupported or invalid deductions.
    """

    graph: ProofGraph
    scope_check: str
    rule_check: str
    gaps: Tuple[ProofGap, ...]


def _add(left, right, weight=Fraction(1)):
    result = dict(left)
    for term, coefficient in right.items():
        result[term] = result.get(term, Fraction(0)) + weight * coefficient
    return {term: coefficient for term, coefficient in result.items() if coefficient}


def _is_false(term_id, graph):
    if term_id is None:
        return False
    term = graph.term(term_id)
    return (term.kind, term.sort, term.value) == ('literal', 'Bool', 'false')


def _square_base(term, graph):
    if term.operator_kind != 'builtin':
        return None
    if term.operator == '*' and len(term.arguments) == 2 and term.arguments[0] == term.arguments[1]:
        return term.arguments[0]
    if term.operator == '^' and len(term.arguments) == 2 and term.sort == 'Real':
        exponent = graph.term(term.arguments[1])
        if exponent.kind == 'literal' and exponent.sort in ('Int', 'Real') and Fraction(exponent.value) == 2:
            return term.arguments[0]
    return None


def _nonlinear_atom(term, graph):
    base = _square_base(term, graph)
    if base is None:
        return {term.term_id: Fraction(1)}
    # A native square may occur as both a power and a repeated multiplication.
    # Use an existing term identity so portable coefficients remain navigable.
    representative = min((other.operator != '^', other.term_id) for other in graph.terms
                         if _square_base(other, graph) == base)[1]
    return {representative: Fraction(1)}


def _affine(term_id, graph, nonlinear_atoms=False):
    term = graph.term(term_id)
    if term.kind == 'algebraic':
        return None
    if term.operator_kind == 'uninterpreted':
        return {term_id: Fraction(1)}
    if term.kind == 'literal' and term.sort in ('Int', 'Real'):
        return {None: Fraction(term.value)}
    if term.operator == 'to_real':
        return _affine(term.arguments[0], graph, nonlinear_atoms)
    if term.operator in ('+', '-', 'uminus'):
        values = [_affine(child, graph, nonlinear_atoms) for child in term.arguments]
        if any(value is None for value in values):
            return None
        if term.operator == 'uminus' or (term.operator == '-' and len(values) == 1):
            return _add({}, values[0], Fraction(-1))
        result = values[0]
        for value in values[1:]:
            result = _add(result, value, Fraction(-1 if term.operator == '-' else 1))
        return result
    if term.operator == '*':
        coefficient = Fraction(1)
        variable = None
        for child in term.arguments:
            value = _affine(child, graph, nonlinear_atoms)
            if value is None:
                return None
            if set(value) <= {None}:
                coefficient *= value.get(None, Fraction(0))
            elif variable is None:
                variable = value
            else:
                # Order tautologies may compare shared nonlinear atoms; a
                # Farkas certificate must still supply linear premises.
                return _nonlinear_atom(term, graph) if nonlinear_atoms else None
        return _add({}, {None: Fraction(1)} if variable is None else variable, coefficient)
    return _nonlinear_atom(term, graph) if nonlinear_atoms else {term_id: Fraction(1)}


def _bound(term_id, negated, graph, nonlinear_atoms=False):
    original, original_negated = term_id, negated
    term = graph.term(term_id)
    while term.operator_kind == 'builtin' and term.operator == 'not':
        negated = not negated
        term_id = term.arguments[0]
        term = graph.term(term_id)
    operator = term.operator
    if term.operator_kind != 'builtin':
        return None
    if negated:
        operator = {'<=': '>', '>=': '<', '<': '>=', '>': '<='}.get(operator)
    if operator not in ('<=', '>=', '<', '>', '=') or len(term.arguments) != 2:
        return None
    left, right = term.arguments
    if graph.term(left).sort not in ('Int', 'Real'):
        return None
    if operator in ('>=', '>'):
        left, right = right, left
    left_value, right_value = _affine(left, graph, nonlinear_atoms), _affine(right, graph, nonlinear_atoms)
    if left_value is None or right_value is None:
        return None
    coefficients = _add(left_value, right_value, Fraction(-1))
    constant = coefficients.pop(None, Fraction(0))
    relation = 'eq' if operator == '=' else ('lt' if operator in ('<', '>') else 'le')
    if relation == 'lt' and graph.term(left).sort == 'Int' and graph.term(right).sort == 'Int':
        # Integer p < 0 is equivalent to p + 1 <= 0. Keeping real strictness
        # here would miss certificates whose contradiction depends on integrality.
        constant += 1
        relation = 'le'
    return LinearBound(original, original_negated,
                       tuple((key, str(value)) for key, value in sorted(coefficients.items())),
                       str(constant), relation)


def _certificate(node, graph):
    parameters = tuple(parameter.value for parameter in node.parameters)
    if parameters[:2] != ('arith', 'farkas'):
        return None, 'unsupported'
    literals = [(graph.node(parent).conclusion, False) for parent in node.parents]
    conclusion = graph.term(node.conclusion)
    if not _is_false(node.conclusion, graph):
        clauses = conclusion.arguments if conclusion.operator == 'or' else (node.conclusion,)
        literals.extend((clause, True) for clause in clauses)
    weights = tuple(Fraction(value) for value in parameters[2:])
    if len(weights) != len(literals):
        return None, 'unsupported'
    bounds = tuple(_bound(term, negated, graph) for term, negated in literals)
    if any(bound is None for bound in bounds):
        return None, 'unsupported'
    # Z3's check_arith_literal uses abs(coeff) for inequalities after orienting
    # the relation; signed coefficients are meaningful only for equalities.
    weights = tuple(weight if bound.relation == 'eq' else abs(weight)
                    for bound, weight in zip(bounds, weights))
    total, constant, strict = {}, Fraction(0), False
    for bound, weight in zip(bounds, weights):
        total = _add(total, {term: Fraction(value) for term, value in bound.coefficients}, weight)
        constant += weight * Fraction(bound.constant)
        strict = strict or (weight > 0 and bound.relation == 'lt')
    if total or constant < 0 or (constant == 0 and not strict):
        return None, 'invalid'
    return ArithmeticCertificate(bounds, tuple(str(value) for value in weights),
                                 str(constant), strict), 'checked'


def _local_pair_certificate(node, graph):
    literals = [(graph.node(parent).conclusion, False) for parent in node.parents]
    if node.conclusion is None:
        return None
    conclusion = graph.term(node.conclusion)
    if not _is_false(node.conclusion, graph):
        clauses = conclusion.arguments if conclusion.operator_kind == 'builtin' and conclusion.operator == 'or' else (node.conclusion,)
        literals.extend((clause, True) for clause in clauses)
    bounds = tuple(bound for term, negated in literals for bound in (_bound(term, negated, graph, True),)
                   if bound is not None)
    for first in bounds:
        left = {key: Fraction(value) for key, value in first.coefficients}
        if not left:
            continue
        pivot = next(iter(left))
        for second in bounds:
            right = {key: Fraction(value) for key, value in second.coefficients}
            if pivot not in right:
                continue
            weight = -left[pivot] / right[pivot]
            if weight < 0 and second.relation != 'eq' or _add(left, right, weight):
                continue
            constant = Fraction(first.constant) + weight * Fraction(second.constant)
            strict = first.relation == 'lt' or weight > 0 and second.relation == 'lt'
            if constant > 0 or constant == 0 and strict:
                return ArithmeticCertificate((first, second), ('1', str(weight)), str(constant), strict)
    return None


def _arithmetic_identity(node, graph):
    if node.conclusion is None:
        return False
    conclusion = graph.term(node.conclusion)
    clauses = conclusion.arguments if conclusion.operator_kind == 'builtin' and conclusion.operator == 'or' else (node.conclusion,)
    for clause in clauses:
        bound = _bound(clause, False, graph, True)
        if bound is not None and not bound.coefficients:
            constant = Fraction(bound.constant)
            if ((bound.relation == 'eq' and constant == 0) or
                    (bound.relation == 'le' and constant <= 0) or (bound.relation == 'lt' and constant < 0)):
                return True
    return False


def _order_tautology(node, graph, budget):
    """Check a clause covering every sign of one arithmetic difference.

    Nonlinear operands are shared atoms here: only equality and order of the
    same values are used, never an assumed property of multiplication.
    """
    if node.conclusion is None:
        return False
    conclusion = graph.term(node.conclusion)
    if conclusion.operator_kind != 'builtin' or conclusion.operator != 'or':
        return False
    reference, covered = None, set()
    signs = {'=': {0}, '<': {-1}, '<=': {-1, 0}, '>': {1}, '>=': {0, 1}}
    for clause in conclusion.arguments:
        budget.checkpoint('proof analysis')
        term_id, positive = _boolean_literal(clause, True, graph)
        term = graph.term(term_id)
        if (term.operator_kind != 'builtin' or term.operator not in signs or
                len(term.arguments) != 2):
            return False
        left, right = term.arguments
        if any(graph.term(child).sort not in ('Int', 'Real') for child in (left, right)):
            return False
        left_value, right_value = _affine(left, graph, True), _affine(right, graph, True)
        left_value = {left: Fraction(1)} if left_value is None else left_value
        right_value = {right: Fraction(1)} if right_value is None else right_value
        difference = _add(left_value, right_value, Fraction(-1))
        if not difference:
            return False
        pivot = difference[min(difference, key=lambda key: '' if key is None else key)]
        normalized = {key: value / pivot for key, value in difference.items()}
        if reference is None:
            reference = normalized
        elif reference != normalized:
            return False
        accepted = signs[term.operator] if positive else {-1, 0, 1} - signs[term.operator]
        covered.update(sign if pivot > 0 else -sign for sign in accepted)
    return covered == {-1, 0, 1}


def _bound_vector(bound):
    return _add({term: Fraction(value) for term, value in bound.coefficients},
                {None: Fraction(bound.constant)})


def _absolute_value(term, divisor, graph):
    if (term.operator_kind != 'builtin' or term.operator != 'ite' or
            len(term.arguments) != 3):
        return False
    condition, positive, negative = term.arguments
    bound = _bound(condition, False, graph, True)
    value = _affine(divisor, graph, True)
    negated = _add({}, value, Fraction(-1))
    return (bound is not None and bound.relation == 'le' and
            _bound_vector(bound) == negated and
            _affine(positive, graph, True) == value and
            _affine(negative, graph, True) == negated)


def _guarded_divisors(guard, graph):
    if (guard.kind, guard.sort, guard.value) == ('literal', 'Bool', 'false'):
        return tuple(term.term_id for term in graph.terms if term.kind == 'literal' and
                     term.sort in ('Int', 'Real') and Fraction(term.value) != 0)
    if guard.operator_kind != 'builtin' or guard.operator != '=' or len(guard.arguments) != 2:
        return ()
    return tuple(divisor for divisor, zero_id in (guard.arguments, guard.arguments[::-1])
                 if graph.term(divisor).sort in ('Int', 'Real') and
                 (graph.term(zero_id).kind, graph.term(zero_id).value) == ('literal', '0') and
                 graph.term(zero_id).sort == graph.term(divisor).sort)


def _floor_axiom(node, graph, budget):
    if node.conclusion is None:
        return None
    conclusion = graph.term(node.conclusion)
    clauses = conclusion.arguments if conclusion.operator_kind == 'builtin' and conclusion.operator == 'or' else (node.conclusion,)
    for clause in clauses:
        bound = _bound(clause, False, graph, True)
        if bound is None:
            continue
        vector = _bound_vector(bound)
        for term in graph.terms:
            budget.checkpoint('proof analysis')
            if (term.operator_kind != 'builtin' or term.operator != 'to_int' or term.sort != 'Int' or
                    len(term.arguments) != 1 or graph.term(term.arguments[0]).sort != 'Real'):
                continue
            value = _affine(term.arguments[0], graph, True)
            if value is None:
                continue
            difference = _add(value, {term.term_id: Fraction(-1)})
            if bound.relation == 'le' and vector == _add({}, difference, Fraction(-1)):
                return 'floor_lower'
            if bound.relation == 'lt' and vector == _add(difference, {None: Fraction(-1)}):
                return 'floor_upper'
    return None


def _quotient_axiom(node, graph, budget):
    if node.conclusion is None:
        return None
    clause = graph.term(node.conclusion)
    if clause.operator_kind != 'builtin' or clause.operator != 'or' or len(clause.arguments) != 2:
        return None
    for guard_id, body_id in (clause.arguments, clause.arguments[::-1]):
        bound = _bound(body_id, False, graph, True)
        if bound is None:
            continue
        vector = _bound_vector(bound)
        divisors = _guarded_divisors(graph.term(guard_id), graph)
        for term in graph.terms:
            budget.checkpoint('proof analysis')
            if term.operator_kind != 'builtin' or term.operator != '*' or len(term.arguments) != 2:
                continue
            for divisor, quotient_id in (term.arguments, term.arguments[::-1]):
                quotient = graph.term(quotient_id)
                if (divisor not in divisors or quotient.operator_kind != 'builtin' or
                        (quotient.operator, quotient.sort) not in (('/', 'Real'), ('div', 'Int')) or
                        len(quotient.arguments) != 2 or quotient.arguments[1] != divisor):
                    continue
                dividend = _affine(quotient.arguments[0], graph, True)
                product = _affine(term.term_id, graph, True)
                if dividend is None or product is None:
                    continue
                residue = _add(dividend, product, Fraction(-1))
                if quotient.sort == 'Real' and bound.relation == 'eq' and (
                        vector == residue or vector == _add({}, residue, Fraction(-1))):
                    return 'real_division'
                if quotient.sort == 'Int' and bound.relation == 'le' and vector == _add({}, residue, Fraction(-1)):
                    return 'remainder_lower'
    return None


def _division_axiom(node, graph, budget):
    """Recognize guarded Euclidean integer division axioms, including d=0.

    SMT-LIB Ints requires x=d*div(x,d)+mod(x,d) and 0<=mod(x,d)<abs(d)
    only when d is nonzero. Never drop the zero-divisor alternative.
    """
    if node.conclusion is None:
        return None
    clause = graph.term(node.conclusion)
    if (clause.operator_kind != 'builtin' or clause.operator != 'or' or
            len(clause.arguments) != 2):
        return None
    for guard_id, body_id in (clause.arguments, clause.arguments[::-1]):
        for divisor in _guarded_divisors(graph.term(guard_id), graph):
            if graph.term(divisor).sort != 'Int':
                continue
            bound = _bound(body_id, False, graph, True)
            if bound is None:
                continue
            vector = _bound_vector(bound)
            for remainder in graph.terms:
                budget.checkpoint('proof analysis')
                if (remainder.operator_kind != 'builtin' or remainder.operator != 'mod' or
                        remainder.sort != 'Int' or len(remainder.arguments) != 2 or
                        remainder.arguments[1] != divisor or
                        graph.term(remainder.arguments[0]).sort != 'Int'):
                    continue
                rem = {remainder.term_id: Fraction(1)}
                if bound.relation == 'le' and vector == _add({}, rem, Fraction(-1)):
                    return 'remainder_lower'
                divisor_term = graph.term(divisor)
                if divisor_term.kind == 'literal' and bound.relation == 'le':
                    upper = _add(rem, {None: 1 - abs(Fraction(divisor_term.value))})
                    if vector == upper:
                        return 'remainder_upper'
                dividend = remainder.arguments[0]
                for term in graph.terms:
                    budget.checkpoint('proof analysis')
                    if bound.relation == 'le' and _absolute_value(term, divisor, graph):
                        upper = _add(rem, {term.term_id: Fraction(-1), None: Fraction(1)})
                        if vector == upper:
                            return 'remainder_upper'
                    if (bound.relation != 'eq' or term.operator_kind != 'builtin' or
                            term.operator != '*' or len(term.arguments) != 2):
                        continue
                    for factor, quotient_id in (term.arguments, term.arguments[::-1]):
                        quotient = graph.term(quotient_id)
                        if (factor != divisor or quotient.operator_kind != 'builtin' or
                                quotient.operator != 'div' or quotient.sort != 'Int' or
                                quotient.arguments != (dividend, divisor)):
                            continue
                        identity = _add(_add(_affine(term.term_id, graph, True), rem),
                                        _affine(dividend, graph, True), Fraction(-1))
                        if vector == identity or vector == _add({}, identity, Fraction(-1)):
                            return 'division_identity'
    return None


def _power_parts(term, graph):
    if (term.operator_kind != 'builtin' or term.operator != '^' or
            term.sort != 'Real' or len(term.arguments) != 2):
        return None
    base, exponent_id = term.arguments
    exponent = graph.term(exponent_id)
    if (graph.term(base).sort not in ('Int', 'Real') or
            exponent.kind != 'literal' or exponent.sort not in ('Int', 'Real')):
        return None
    return base, Fraction(exponent.value)


def _nonnegative_domain(base, assumptions, graph):
    value = _affine(base, graph, True)
    if value is None:
        return False
    if set(value) <= {None}:
        return value.get(None, Fraction(0)) >= 0
    negative = _add({}, value, Fraction(-1))
    return any(bound is not None and bound.relation in ('le', 'lt') and
               _bound_vector(bound) == negative for bound in assumptions)


def _power_axiom(node, graph, budget):
    """Check even powers and principal real square roots with their domains."""
    if node.conclusion is None:
        return None
    conclusion = graph.term(node.conclusion)
    clauses = (conclusion.arguments if conclusion.operator_kind == 'builtin' and
               conclusion.operator == 'or' else (node.conclusion,))
    literals = tuple((clause, False) for clause in clauses) + tuple(
        (graph.node(parent).conclusion, True) for parent in node.parents)
    for claim, negated in literals:
        budget.checkpoint('proof analysis')
        bound = _bound(claim, negated, graph, True)
        if bound is None:
            continue
        vector = _bound_vector(bound)
        assumptions = tuple(_bound(other, not polarity, graph, True) for other, polarity in literals
                            if (other, polarity) != (claim, negated))
        for term_id, _ in bound.coefficients:
            term = graph.term(term_id)
            parts = _power_parts(term, graph)
            if parts is None:
                continue
            base, exponent = parts
            if bound.relation == 'le' and vector == {term_id: Fraction(-1)}:
                if exponent.denominator == 1 and exponent > 0 and exponent.numerator % 2 == 0:
                    return 'even_power'
                if exponent == Fraction(1, 2) and _nonnegative_domain(base, assumptions, graph):
                    return 'root_nonnegative'
            if bound.relation == 'eq' and exponent == 2:
                inner = _power_parts(graph.term(base), graph)
                if inner is None or inner[1] != Fraction(1, 2):
                    continue
                radicand = inner[0]
                value = _affine(radicand, graph, True)
                if value is None:
                    continue
                identity = _add(value, {term_id: Fraction(-1)})
                if ((vector == identity or vector == _add({}, identity, Fraction(-1))) and
                        _nonnegative_domain(radicand, assumptions, graph)):
                    return 'root_identity'
    return None


def _complement(left_id, right_id, graph):
    left, right = graph.term(left_id), graph.term(right_id)
    return ((left.operator_kind == 'builtin' and left.operator == 'not' and left.arguments == (right_id,)) or
            (right.operator_kind == 'builtin' and right.operator == 'not' and right.arguments == (left_id,)))


def _transitive_path(node, graph, budget):
    """Check the undirected relation path specified by native ``trans*``."""
    if node.conclusion is None:
        return False
    target = graph.term(node.conclusion)
    if (target.operator_kind != 'builtin' or target.operator not in ('=', 'iff', '~') or
            len(target.arguments) != 2):
        return False
    edges = {}
    for parent in node.parents:
        budget.checkpoint('proof analysis')
        fact_id = graph.node(parent).conclusion
        if fact_id is None:
            return False
        fact = graph.term(fact_id)
        if (fact.operator_kind != 'builtin' or fact.operator != target.operator or
                len(fact.arguments) != 2):
            return False
        left, right = fact.arguments
        edges.setdefault(left, set()).add(right)
        edges.setdefault(right, set()).add(left)
    start, end = target.arguments
    pending, visited = [start], set()
    while pending:
        budget.checkpoint('proof analysis')
        current = pending.pop()
        if current == end:
            return True
        if current not in visited:
            visited.add(current)
            pending.extend(edges.get(current, set()) - visited)
    return False


def _boolean_literal(term_id, value, graph):
    term = graph.term(term_id)
    while term.operator_kind == 'builtin' and term.operator == 'not':
        term_id, value = term.arguments[0], not value
        term = graph.term(term_id)
    return term_id, value


def _cardinality_certificate(node, graph, budget):
    """Bound a native PB lemma using only its premises and negated conclusion."""
    conclusion = graph.term(node.conclusion)
    assumptions = (() if _is_false(node.conclusion, graph) else
                   conclusion.arguments if conclusion.operator == 'or' and
                   conclusion.operator_kind == 'builtin' else (node.conclusion,))
    literals = [(graph.node(parent).conclusion, True) for parent in node.parents]
    literals.extend((term, False) for term in assumptions)
    assignments = {}
    for term_id, value in literals:
        budget.checkpoint('proof analysis')
        term_id, value = _boolean_literal(term_id, value, graph)
        if graph.term(term_id).sort != 'Bool':
            return None
        if term_id in assignments and assignments[term_id] != value:
            return None
        assignments[term_id] = value
    operators = {'at-most': 'le', 'at-least': 'ge', 'pble': 'le', 'pbge': 'ge', 'pbeq': 'eq'}
    for term_id, required in assignments.items():
        term = graph.term(term_id)
        if term.operator_kind != 'builtin' or term.operator not in operators:
            continue
        if any(graph.term(argument).sort != 'Bool' for argument in term.arguments):
            return None
        parameters = tuple(parameter.value for parameter in term.parameters)
        expected = 1 if term.operator in ('at-most', 'at-least') else 1 + len(term.arguments)
        if len(parameters) != expected or any(parameter.kind != 'integer' for parameter in term.parameters):
            return None
        threshold = int(parameters[0])
        weights = (1,) * len(term.arguments) if expected == 1 else tuple(int(p) for p in parameters[1:])
        contributions = []
        for argument, weight in zip(term.arguments, weights):
            budget.checkpoint('proof analysis')
            atom, positive = _boolean_literal(argument, True, graph)
            fact = graph.term(atom)
            value = assignments.get(atom)
            if fact.kind == 'literal' and fact.sort == 'Bool':
                value = fact.value == 'true'
            if value is None:
                low, high = min(0, weight), max(0, weight)
            else:
                low = high = weight * int(value == positive)
            contributions.append(CountContribution(argument, weight, low, high))
        certificate = CardinalityCertificate(tuple(assumptions), term_id, required,
                                             tuple(assignments.items()), tuple(contributions))
        low, high = certificate.minimum, certificate.maximum
        relation = operators[term.operator]
        if relation == 'le':
            actual = True if high <= threshold else False if low > threshold else None
        elif relation == 'ge':
            actual = True if low >= threshold else False if high < threshold else None
        else:
            actual = True if low == high == threshold else False if high < threshold or low > threshold else None
        if actual is not None and actual != required:
            return certificate
    return None


def analyze_proof(graph: ProofGraph, rule_handlers=(), budget=None) -> ProofAnalysis:
    """Annotate a portable proof without treating local assumptions as facts.

    :param graph: Public native evidence graph.
    :param rule_handlers: Optional explicit native-rule interpreters.
    :param budget: Optional shared :class:`~pyfcstm.solver.budget.SolveBudget`.
    :return: Scope status, local checks and explicit proof gaps.
    :rtype: ProofAnalysis
    """
    from ..budget import SolveBudget

    budget = SolveBudget(None) if budget is None else budget
    handlers = _index_handlers(rule_handlers)
    mechanical = {
        'mp': 'logical', 'mp~': 'definition', 'rewrite': 'rewrite',
        'refl': 'equality', 'symm': 'equality', 'trans': 'equality',
        'monotonicity': 'equality', 'commutativity': 'equality',
        'unit-resolution': 'resolution', 'and-elim': 'logical',
        'not-or-elim': 'logical', 'iff-true': 'logical', 'iff-false': 'logical',
        'intro-def': 'definition', 'def-axiom': 'definition', 'apply-def': 'definition',
    }
    inputs = {item.occurrence_id: item for item in graph.inputs}
    nodes, analyzed, gaps = [], {}, []
    scope, rules = 'passed', 'complete'
    for node in graph.nodes:
        budget.checkpoint('proof analysis')
        opened = set().union(*(analyzed[parent].open_hypotheses for parent in node.parents))
        discharged, certificate, cardinality, interval = (), None, None, None
        local, kind = 'trusted', mechanical.get(node.rule, 'opaque')
        if node.rule == 'asserted':
            kind = 'input'
            local = 'checked' if node.input_occurrences and all(
                inputs[occurrence].term_id == node.conclusion for occurrence in node.input_occurrences
            ) else 'invalid'
        elif node.rule == 'hypothesis':
            kind, local = 'assumption', 'checked'
            opened.add(node.node_id)
        elif node.rule == 'lemma':
            kind = 'discharge'
            fact = graph.term(node.conclusion)
            literals = fact.arguments if fact.operator == 'or' else (node.conclusion,)
            single = len(opened) == 1 and _complement(
                analyzed[next(iter(opened))].conclusion, node.conclusion, graph,
            )
            valid = (len(node.parents) == 1 and
                     _is_false(analyzed[node.parents[0]].conclusion, graph) and
                     (single or all(any(_complement(analyzed[hyp].conclusion, literal, graph)
                                        for literal in literals) for hyp in opened)))
            local = 'checked' if valid else 'invalid'
            if valid:
                discharged = tuple(sorted(opened))
                opened.clear()
        elif node.rule in handlers:
            result = handlers[node.rule].interpret(node, graph)
            budget.checkpoint('proof analysis')
            if not isinstance(result, RuleAnalysis):
                raise TypeError('rule handler must return RuleAnalysis')
            local, kind = result.local_check, result.kind
        elif node.rule == 'true-axiom':
            kind = 'logical'
            fact = None if node.conclusion is None else graph.term(node.conclusion)
            local = 'checked' if (fact is not None and not node.parents and
                                  (fact.kind, fact.sort, fact.value) ==
                                  ('literal', 'Bool', 'true')) else 'invalid'
        elif node.rule == 'trans*':
            kind = 'equality'
            local = 'checked' if _transitive_path(node, graph, budget) else 'invalid'
        elif node.rule == 'th-lemma':
            if tuple(parameter.value for parameter in node.parameters) == ('pb',):
                cardinality = _cardinality_certificate(node, graph, budget)
                local = 'checked' if cardinality is not None else 'unsupported'
                kind = 'cardinality' if cardinality is not None else 'opaque'
            elif tuple(parameter.value for parameter in node.parameters) == ('arith', 'triangle-eq'):
                local = 'checked' if _order_tautology(node, graph, budget) else 'unsupported'
                kind = 'order' if local == 'checked' else 'opaque'
                if local == 'unsupported' and _arithmetic_identity(node, graph):
                    local, kind = 'checked', 'arithmetic_identity'
            elif tuple(parameter.value for parameter in node.parameters) == ('arith',):
                axiom = (_division_axiom(node, graph, budget) or _quotient_axiom(node, graph, budget) or
                         _floor_axiom(node, graph, budget) or _power_axiom(node, graph, budget))
                local, kind = ('checked', axiom) if axiom is not None else ('unsupported', 'opaque')
                if axiom is None and _arithmetic_identity(node, graph):
                    local, kind = 'checked', 'arithmetic_identity'
                elif axiom is None and _order_tautology(node, graph, budget):
                    local, kind = 'checked', 'order'
            else:
                certificate, local = _certificate(node, graph)
                kind = 'arithmetic' if certificate is not None else 'opaque'
            if local == 'unsupported' and tuple(p.value for p in node.parameters[:2]) in (
                    ('arith',), ('arith', 'farkas'), ('arith', 'eq-propagate')):
                certificate = _local_pair_certificate(node, graph)
                if certificate is not None:
                    local, kind = 'checked', 'arithmetic'
                else:
                    from .interval import interval_certificate
                    interval = interval_certificate(node, graph, budget)
                    if interval is not None:
                        local, kind = 'checked', 'interval'
        elif kind == 'opaque':
            local = 'unsupported'
        if local == 'invalid':
            rules = 'failed'
            gaps.append(ProofGap('invalid_inference', node.node_id, node.rule))
        elif local != 'checked' and rules != 'failed':
            rules = 'partial'
        if local == 'unsupported':
            gaps.append(ProofGap('unsupported_rule', node.node_id, node.rule))
            if node.rule != 'th-lemma':
                scope = 'partial'
        analyzed[node.node_id] = replace(node, local_check=local, inference_kind=kind,
                                        open_hypotheses=tuple(sorted(opened)),
                                        discharged_hypotheses=discharged, certificate=certificate,
                                        cardinality=cardinality, interval=interval)
        nodes.append(analyzed[node.node_id])
    root = analyzed[graph.root_id]
    if root.open_hypotheses:
        scope = 'failed'
        gaps.append(ProofGap('open_hypotheses', root.node_id, 'refutation depends on local assumptions'))
    if not _is_false(root.conclusion, graph):
        scope = 'failed'
        gaps.append(ProofGap('non_false_root', root.node_id, 'refutation must conclude False'))
    return ProofAnalysis(replace(graph, nodes=tuple(nodes)), scope, rules, tuple(gaps))
