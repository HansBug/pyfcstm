"""Scope analysis and exact linear certificates for portable native proofs.

Arithmetic checks use rational arithmetic only. Recognized mechanical rules
remain explicitly solver-trusted until a dedicated checker is supplied; that
distinction is retained independently of whether their deductions are readable.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Tuple

from .proof import ArithmeticCertificate, LinearBound, ProofGap, ProofGraph


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


def _affine(term_id, graph):
    term = graph.term(term_id)
    if term.kind == 'algebraic':
        return None
    if term.operator_kind == 'uninterpreted':
        return {term_id: Fraction(1)}
    if term.kind == 'literal' and term.sort in ('Int', 'Real'):
        return {None: Fraction(term.value)}
    if term.operator == 'to_real':
        return _affine(term.arguments[0], graph)
    if term.operator in ('+', '-', 'uminus'):
        values = [_affine(child, graph) for child in term.arguments]
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
            value = _affine(child, graph)
            if value is None:
                return None
            if set(value) <= {None}:
                coefficient *= value.get(None, Fraction(0))
            elif variable is None:
                variable = value
            else:
                # Native arithmetic may label nonlinear reasoning as farkas
                # without supplying a linear certificate for these premises.
                return None
        return _add({}, {None: Fraction(1)} if variable is None else variable, coefficient)
    return {term_id: Fraction(1)}


def _bound(term_id, negated, graph):
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
    if operator not in ('<=', '>=', '<', '>', '='):
        return None
    left, right = term.arguments
    if graph.term(left).sort not in ('Int', 'Real'):
        return None
    if operator in ('>=', '>'):
        left, right = right, left
    left_value, right_value = _affine(left, graph), _affine(right, graph)
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


def _complement(left_id, right_id, graph):
    left, right = graph.term(left_id), graph.term(right_id)
    return ((left.operator_kind == 'builtin' and left.operator == 'not' and left.arguments == (right_id,)) or
            (right.operator_kind == 'builtin' and right.operator == 'not' and right.arguments == (left_id,)))


def analyze_proof(graph: ProofGraph, rule_handlers=(), budget=None) -> ProofAnalysis:
    """Annotate a portable proof without treating local assumptions as facts.

    :param graph: Public native evidence graph.
    :param rule_handlers: Optional explicit native-rule interpreters.
    :param budget: Optional shared :class:`~pyfcstm.solver.budget.SolveBudget`.
    :return: Scope status, local checks and explicit proof gaps.
    :rtype: ProofAnalysis
    """
    from .budget import SolveBudget

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
        discharged, certificate = (), None
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
        elif node.rule == 'th-lemma':
            certificate, local = _certificate(node, graph)
            kind = 'arithmetic' if certificate is not None else 'opaque'
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
                                        discharged_hypotheses=discharged, certificate=certificate)
        nodes.append(analyzed[node.node_id])
    root = analyzed[graph.root_id]
    if root.open_hypotheses:
        scope = 'failed'
        gaps.append(ProofGap('open_hypotheses', root.node_id, 'refutation depends on local assumptions'))
    if not _is_false(root.conclusion, graph):
        scope = 'failed'
        gaps.append(ProofGap('non_false_root', root.node_id, 'refutation must conclude False'))
    return ProofAnalysis(replace(graph, nodes=tuple(nodes)), scope, rules, tuple(gaps))
