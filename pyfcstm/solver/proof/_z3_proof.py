"""Native Z3 capture; all context-bound objects remain inside this module."""

from uuid import uuid4
from dataclasses import replace
from fractions import Fraction
import warnings

import z3

from .core import (ProofGraph, ProofInput, ProofNode, ProofParameter, ProofSource,
                    ProofTerm, SourceBinding, SourceDescription, UnsatReport)
from ..unsat import _run_probe
from ..budget import BudgetExpired


class _Terms:
    """Intern ASTs once, retaining typed children instead of repeated sexprs."""

    def __init__(self, displays, budget):
        self.identities = {}
        self.terms = []
        self.displays = displays
        self.budget = budget

    def disambiguate(self):
        """Keep distinct constants distinguishable across the entire report."""
        groups = {}
        bound_names = {name for term in self.terms for name, _ in term.bindings}
        for term in self.terms:
            if term.kind == 'constant':
                groups.setdefault(term.value, []).append(term)
        reserved = set(groups) | bound_names
        replacements = {}
        for display, members in groups.items():
            self.budget.checkpoint('proof symbol names')
            if len(members) == 1 and (display not in bound_names or members[0].operator == display):
                continue
            renamed = []
            for term in members:
                candidate = '%s [%s]' % (display, term.term_id)
                while candidate in reserved:
                    candidate += '_'
                reserved.add(candidate)
                replacements[term.term_id] = candidate
                renamed.append('%s (%s) -> %s' % (term.operator, term.sort, candidate))
            warnings.warn('Proof symbol display collision for %r: %s. '
                          'Distinct symbols retain separate term identities.' %
                          (display, '; '.join(renamed)), UserWarning, stacklevel=3)
        self.terms = [replace(term, value=replacements[term.term_id])
                      if term.term_id in replacements else term for term in self.terms]

    def intern(self, expression):
        pending = [(expression, False)]
        while pending:
            self.budget.checkpoint('proof capture')
            node, ready = pending.pop()
            key = node.get_id()
            if key in self.identities:
                continue
            children = node.children()
            if not ready:
                pending.append((node, True))
                pending.extend((child, False) for child in reversed(children))
                continue
            arguments = tuple(self.identities[child.get_id()] for child in children)
            term_id = 't%d' % len(self.terms)
            kind, operator, value, bindings = 'application', '', '', ()
            operator_kind = 'builtin'
            parameters = ()
            if z3.is_quantifier(node):
                kind = 'quantifier'
                operator = 'forall' if node.is_forall() else ('lambda' if node.is_lambda() else 'exists')
                bindings = tuple((str(node.var_name(i)), str(node.var_sort(i)))
                                 for i in range(node.num_vars()))
            elif z3.is_var(node):
                kind, value = 'variable', str(z3.get_var_index(node))
            else:
                if node.decl().kind() == z3.Z3_OP_UNINTERPRETED:
                    operator_kind = 'uninterpreted'
                operator = 'ite' if z3.is_app_of(node, z3.Z3_OP_ITE) else str(node.decl().name())
                if z3.is_int_value(node) or z3.is_rational_value(node):
                    # Native pretty printing can round rationals and append '?'.
                    # Evidence must retain the exact value independently of it.
                    kind = 'literal'
                    value = (str(node.as_long()) if z3.is_int_value(node) else
                             str(Fraction(node.numerator_as_long(), node.denominator_as_long())))
                elif z3.is_algebraic_value(node):
                    kind, value = 'algebraic', node.sexpr()
                elif z3.is_true(node) or z3.is_false(node):
                    kind, value = 'literal', node.sexpr()
                elif not children:
                    if operator_kind == 'uninterpreted':
                        kind, value = 'constant', self.displays.get(key, operator)
                    else:
                        kind, value = 'literal', node.sexpr()
                if children:
                    parameters = _parameters(node.decl())
            self.identities[key] = term_id
            self.terms.append(ProofTerm(term_id, kind, str(node.sort()), operator,
                                        arguments, value, bindings, operator_kind, parameters))
        return self.identities[expression.get_id()]


def _is_proof(expression):
    return str(expression.sort()) == 'Proof'


def _parameters(declaration):
    values = []
    kinds = {
        z3.Z3_PARAMETER_INT: 'integer', z3.Z3_PARAMETER_DOUBLE: 'double',
        z3.Z3_PARAMETER_RATIONAL: 'rational', z3.Z3_PARAMETER_SYMBOL: 'symbol',
        z3.Z3_PARAMETER_SORT: 'sort', z3.Z3_PARAMETER_AST: 'expression',
        z3.Z3_PARAMETER_FUNC_DECL: 'declaration',
    }
    for index, value in enumerate(declaration.params()):
        kind = z3.Z3_get_decl_parameter_kind(declaration.ctx.ref(), declaration.ast, index)
        if kind == z3.Z3_PARAMETER_SYMBOL:
            value = z3.Z3_get_symbol_string(declaration.ctx.ref(), value)
        elif isinstance(value, z3.AstRef):
            value = value.sexpr()
        values.append(ProofParameter(kinds[kind], str(value)))
    return tuple(values)


def capture_proof(query, budget, names, source_adapter):
    """Recheck exact inputs and detach one native refutation into plain data."""
    status = 'timeout'
    try:
        budget.checkpoint('proof capture')
        context = z3.Context(proof=True)
        native = z3.Solver(ctx=context)
        native.set('arith.solver', 2)
        native.set('arith.propagation_mode', 0)
        groups = query.background + query.constraints
        original_context = groups[0].expressions[0].ctx if groups else None
        source_bindings = tuple(source_adapter.bindings())
        for binding in source_bindings:
            budget.checkpoint('proof capture')
            if not isinstance(binding, SourceBinding):
                raise TypeError('bindings must contain SourceBinding objects')
            if not isinstance(binding.expression, z3.ExprRef):
                raise TypeError('source binding expression must be a Z3 expression')
            if original_context is not None and binding.expression.ctx != original_context:
                raise ValueError('source binding must use the query context')
        translated_names = () if names is None else tuple(
            (entry.symbol.translate(context), entry.display)
            for entry in names.entries if entry.symbol.ctx == original_context
        )
        # Keep handles alive: Z3 can reuse an AST id after its last reference dies.
        displays = {symbol.get_id(): display for symbol, display in translated_names}
        terms = _Terms(displays, budget)
        inputs, assertions = [], []
        origins = {}
        for background, groups in ((True, query.background), (False, query.constraints)):
            for group in groups:
                for index, expression in enumerate(group.expressions):
                    translated = expression.translate(context)
                    term_id = terms.intern(translated)
                    occurrence = 'i%d' % len(inputs)
                    inputs.append(ProofInput(occurrence, group.stable_id, index,
                                             term_id, background))
                    origins.setdefault(translated.get_id(), []).append(occurrence)
                    assertions.append(translated)
                    native.add(translated)
        terms.disambiguate()
        status, check = _run_probe(native, budget, 'proof', ())
        if status == 'unknown' and any(reason in (check.reason or '') for reason in (
                'incomplete (theory arithmetic)', 'tseitin-cnf does not support proof production')):
            # Retry only known arithmetic/proof limitations, with the same
            # assertions and total deadline. Export one execution's proof.
            budget.checkpoint('proof capture')
            retry = z3.Solver(ctx=context)
            retry.set('arith.solver', 6)
            retry.add(*assertions)
            native = retry
            status, check = _run_probe(native, budget, 'proof', ())
        if status != 'unsat':
            return UnsatReport(query.query_id, status, 'unavailable', None,
                               stop_reason=check.reason)

        root = native.proof()
        identities, nodes = {}, []
        pending = [(root, False)]
        while pending:
            budget.checkpoint('proof capture')
            node, ready = pending.pop()
            if node.get_id() in identities:
                continue
            children = node.children()
            rule = str(node.decl().name())
            binder = children[0] if rule == 'proof-bind' else None
            parents = ((binder.body(),) if binder is not None else
                       tuple(child for child in children if _is_proof(child)))
            if not ready:
                pending.append((node, True))
                pending.extend((parent, False) for parent in reversed(parents))
                continue
            fact = None if binder is not None else children[-1]
            conclusion = None if fact is None else terms.intern(fact)
            operands = tuple(terms.intern(child) for child in children[:-1]
                             if not _is_proof(child))
            node_id = 'n%d' % len(nodes)
            identities[node.get_id()] = node_id
            nodes.append(ProofNode(
                node_id, rule, tuple(identities[parent.get_id()] for parent in parents),
                conclusion, operands, _parameters(node.decl()),
                tuple(origins.get(fact.get_id(), ())) if rule == 'asserted' else (),
                bindings=tuple((str(binder.var_name(i)), str(binder.var_sort(i)))
                               for i in range(binder.num_vars())) if binder is not None else (),
            ))
        bound_sources = []
        for binding in source_bindings:
            budget.checkpoint('proof capture')
            expression = binding.expression.translate(context)
            if expression.get_id() in terms.identities:
                description = source_adapter.describe(binding.source)
                if not isinstance(description, SourceDescription):
                    raise TypeError('source adapter must return SourceDescription')
                bound_sources.append(ProofSource(terms.identities[expression.get_id()], description, binding.relation))
        terms.disambiguate()
        graph = ProofGraph(uuid4().hex, identities[root.get_id()], tuple(nodes),
                           tuple(terms.terms), tuple(inputs), tuple(bound_sources))
        bound = all(node.input_occurrences for node in nodes if node.rule == 'asserted')
        return UnsatReport(query.query_id, status, 'captured', graph,
                           input_check='passed' if bound else 'failed', proof_scope='full')
    except BudgetExpired as error:
        # Input translation/native DAG export cooperatively check the deadline.
        # An incomplete graph is never published, but an obtained UNSAT is kept.
        return UnsatReport(query.query_id, status, 'unavailable', None,
                           stop_reason=str(error))
