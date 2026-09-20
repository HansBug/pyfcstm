"""DSL-style layout of recorded formulas, without solving or changing evidence.

Only Boolean literal identities, exact numeral comparisons and redundant
associative layers are cleaned. Named conditions are layout boundaries;
SMT operations without an exact DSL spelling retain their typed function form.
"""

from collections import namedtuple
from dataclasses import fields, replace
from functools import lru_cache

import z3

from pyfcstm.dsl import node as dsl_nodes
from .domain import STATE_INIT_ID, STATE_TERMINATE_ID


_Term = namedtuple('_Term', 'operator children text', defaults=((), ''))
_PRECEDENCE = {'?:': 0, '=>': 1, '||': 2, 'xor': 3, '&&': 4, 'iff': 5,
               '==': 6, '!=': 6, '<': 6, '<=': 6, '>': 6, '>=': 6,
               '+': 10, '-': 10, '*': 11, '/': 11, '%': 11, '!': 12, 'neg': 12, '**': 13}
_INFIX = {z3.Z3_OP_AND: '&&', z3.Z3_OP_OR: '||', z3.Z3_OP_IMPLIES: '=>',
          z3.Z3_OP_IFF: 'iff', z3.Z3_OP_XOR: 'xor', z3.Z3_OP_EQ: '==',
          z3.Z3_OP_LE: '<=', z3.Z3_OP_GE: '>=', z3.Z3_OP_LT: '<', z3.Z3_OP_GT: '>',
          z3.Z3_OP_ADD: '+', z3.Z3_OP_SUB: '-', z3.Z3_OP_MUL: '*',
          z3.Z3_OP_DIV: '/', z3.Z3_OP_POWER: '**'}


def atom(text):
    return _Term('atom', text=text)


def combine(operator, children):
    """Remove literal noise, retaining operand order and named boundaries."""
    children = tuple(children)
    if operator in ('&&', '||'):
        neutral = atom('true' if operator == '&&' else 'false')
        children = tuple(part for child in children
                         for part in (child.children if child.operator == operator else (child,))
                         if part != neutral)
        if not children:
            return neutral
        if len(children) == 1:
            return children[0]
    if operator == '!':
        child = children[0]
        if child == atom('true'):
            return atom('false')
        if child == atom('false'):
            return atom('true')
        if child.operator == '!':
            return child.children[0]
    return _Term(operator, children)


def source_expression(expression, bindings):
    """Reuse the source AST serializer, replacing only read-name occurrences."""
    def renamed(node):
        if isinstance(node, dsl_nodes.Name):
            return replace(node, name=bindings[node.name])
        return replace(node, **{field.name: renamed(getattr(node, field.name))
                                for field in fields(node)
                                if isinstance(getattr(node, field.name), dsl_nodes.Expr)})
    return str(renamed(expression.to_ast_node()))


class FormulaText:
    """One scoped display of original Z3 identities and optional condition aliases."""

    def __init__(self, names, domain=None):
        self.names = names
        self.domain = domain
        self.aliases = {}
        self.definitions = []
        self._terms = {}
        # Z3 may reuse an AST id after its last Python/native reference dies.
        # Keep temporary conjunctions alive alongside their memoized terms.
        self._expressions = {}
        # Instance-owned caches do not retain reports globally.
        self.inline = lru_cache(maxsize=None)(self._inline)

    def state(self, state_id, frame):
        if state_id == STATE_INIT_ID:
            return atom('cold@%d' % frame)
        if state_id == STATE_TERMINATE_ID:
            return atom('terminated@%d' % frame)
        entry = self.domain.state_by_id(state_id)
        predicate = 'active' if entry.is_stoppable else 'control'
        result = atom('%s("%s")@%d' % (predicate, entry.path, frame))
        if entry.is_stoppable and entry.is_root:
            # Public active(root) also holds at cold. Its exact entered leaf
            # position must exclude cold, even if a selected core omits the
            # frame-domain group. Do not silently borrow that missing premise.
            return combine('&&', (result, combine('!', (atom('cold@%d' % frame),))))
        return result

    def define(self, expression, label):
        """Bind an already recorded condition, not a new solver assumption."""
        identity = expression.get_id()
        if identity in self.aliases:
            return self.aliases[identity]
        term = self.term(expression)
        reference = atom('<%s>' % label)
        self.definitions.append((reference, term))
        self.aliases[identity] = reference
        self._terms.clear()
        return reference

    def share(self, expressions):
        """Name large repeated/deep Boolean subterms, retaining named roots."""
        roots = {expression.get_id() for expression in expressions}
        nodes, counts, depths, ordered = {}, {}, {}, []

        def visit(expression):
            identity = expression.get_id()
            counts[identity] = counts.get(identity, 0) + 1
            if identity in nodes:
                return
            nodes[identity] = expression
            # A named group already has its own visible definition. Looking
            # inside it here would create unused aliases in the outer scope.
            children = () if identity in self.aliases else expression.children()
            for child in children:
                visit(child)
            depths[identity] = 1 + max((depths[child.get_id()] for child in children), default=0)
            ordered.append(identity)

        for expression in expressions:
            visit(expression)
        number = 0
        for identity in ordered:
            expression = nodes[identity]
            if identity not in roots and identity not in self.aliases and z3.is_bool(expression) and expression.num_args() > 1 and (
                counts[identity] > 1 or depths[identity] >= 4
            ) and len(self.inline(self.term(expression))) > 160:
                number += 1
                self.define(expression, 'condition %d: shared Boolean term' % number)

    def term(self, expression):
        identity = expression.get_id()
        self._expressions[identity] = expression
        if identity in self.aliases:
            return self.aliases[identity]
        if identity not in self._terms:
            self._terms[identity] = self._term(expression)
        return self._terms[identity]

    def _term(self, expression):
        if z3.is_true(expression):
            return atom('true')
        if z3.is_false(expression):
            return atom('false')
        entry = self.names.lookup(expression)
        if entry is not None:
            return atom(entry.display)
        if z3.is_quantifier(expression):
            # BMC currently produces quantifier-free formulas. Preserve any
            # externally supplied binder with the native capture-safe printer.
            return atom(self.names.render(expression))
        kind = expression.decl().kind()
        children = expression.children()
        if kind in (z3.Z3_OP_EQ, z3.Z3_OP_DISTINCT, z3.Z3_OP_LE, z3.Z3_OP_GE,
                    z3.Z3_OP_LT, z3.Z3_OP_GT) and len(children) == 2 and all(
            z3.is_rational_value(child) or z3.is_int_value(child) for child in children
        ):
            left, right = (child.as_long() if z3.is_int_value(child) else child.as_fraction() for child in children)
            result = {z3.Z3_OP_EQ: left == right, z3.Z3_OP_DISTINCT: left != right,
                      z3.Z3_OP_LE: left <= right, z3.Z3_OP_GE: left >= right,
                      z3.Z3_OP_LT: left < right, z3.Z3_OP_GT: left > right}[kind]
            return atom('true' if result else 'false')
        if self.domain is not None and kind in (z3.Z3_OP_EQ, z3.Z3_OP_DISTINCT) and len(children) == 2:
            for slot, value in (children, children[::-1]):
                entry = self.names.lookup(slot)
                if entry is not None and getattr(entry.source, 'kind', None) == 'state' and z3.is_int_value(value):
                    state = self.state(value.as_long(), entry.source.frame)
                    return state if kind == z3.Z3_OP_EQ else combine('!', (state,))
        if not children:
            if z3.is_rational_value(expression):
                # Keep Real constants visibly Real, including exact integers.
                numerator, denominator = expression.numerator_as_long(), expression.denominator_as_long()
                if denominator != 1:
                    return atom('(%s.0 / %s.0)' % (numerator, denominator))
                return atom('(%s.0)' % numerator if numerator < 0 else '%s.0' % numerator)
            text = self.names.render(expression)
            return atom('(' + text + ')' if text.startswith('-') else text)
        parts = tuple(self.term(child) for child in children)
        if kind == z3.Z3_OP_DISTINCT and len(parts) == 2:
            return combine('!=', parts)
        if kind in _INFIX:
            operator = 'iff' if kind == z3.Z3_OP_EQ and z3.is_bool(children[0]) else _INFIX[kind]
            return combine(operator, parts)
        if kind in (z3.Z3_OP_NOT, z3.Z3_OP_UMINUS, z3.Z3_OP_ITE):
            return combine({z3.Z3_OP_NOT: '!', z3.Z3_OP_UMINUS: 'neg', z3.Z3_OP_ITE: '?:'}[kind], parts)
        # Int division/mod, conversions, and bit-vector operations retain their
        # SMT function identity; printing a familiar but different DSL operator
        # would misrepresent negative operands or finite-width arithmetic.
        functions = {z3.Z3_OP_IDIV: 'div', z3.Z3_OP_MOD: 'mod', z3.Z3_OP_REM: 'rem',
                     z3.Z3_OP_TO_REAL: 'to_real', z3.Z3_OP_TO_INT: 'to_int'}
        name = functions.get(kind, str(expression.decl()))
        parameters = expression.decl().params()
        if parameters:
            name += '[' + ', '.join(map(str, parameters)) + ']'
        return _Term('call', parts, name)

    def _operand(self, term, precedence, equal=False):
        text = self.inline(term)
        level = _PRECEDENCE.get(term.operator, 100)
        return '(' + text + ')' if level < precedence or (equal and level == precedence) else text

    def _inline(self, term):
        operator, children, text = term
        if operator == 'atom':
            return text
        if operator == 'call':
            return text + '(' + ', '.join(self.inline(child) for child in children) + ')'
        level = _PRECEDENCE[operator]
        if operator in ('!', 'neg'):
            return ('!' if operator == '!' else '-') + self._operand(children[0], level, equal=True)
        if operator == '?:':
            return '(%s) ? %s : %s' % (self.inline(children[0]),
                                       self._operand(children[1], level, equal=True),
                                       self._operand(children[2], level, equal=True))
        # Preserve grouping even for arithmetic that is mathematically
        # associative: the construction shape remains useful to the reader.
        return (' ' + operator + ' ').join(
            self._operand(child, level, equal=(operator not in ('&&', '||') and
                                              (index > 0 or operator in ('==', '!=', '<', '<=', '>', '>=', 'iff', '=>', '**'))))
            for index, child in enumerate(children))

    def lines(self, term, *, width=96, force=False):
        """Layout complete terms; the first operand aligns after later operators."""
        text = self.inline(term)
        if not force and len(text) <= width:
            return [text]
        if term.operator in ('&&', '||'):
            lines = ['(']
            for index, child in enumerate(term.children):
                parts = self.lines(child, width=width - 7)
                if _PRECEDENCE.get(child.operator, 100) < _PRECEDENCE[term.operator]:
                    if len(parts) == 1:
                        parts = ['(' + parts[0] + ')']
                    elif child.operator not in ('&&', '||'):
                        parts = ['('] + ['    ' + part for part in parts] + [')']
                prefix = '       ' if index == 0 else '    ' + term.operator + ' '
                lines.append(prefix + parts[0])
                lines.extend('       ' + part for part in parts[1:])
            return lines + [')']
        if term.operator in ('=>', 'iff'):
            left, right = term.children
            lines = self.lines(left, width=width)
            parts = self.lines(right, width=width, force=right.operator in ('&&', '||'))
            if force and term.operator == '=>' and len(parts) == 1:
                parts = ['(', '       ' + parts[0], ')']
            for child, output in ((left, lines), (right, parts)):
                if _PRECEDENCE.get(child.operator, 100) <= _PRECEDENCE[term.operator]:
                    if len(output) == 1:
                        output[0] = '(' + output[0] + ')'
                    elif child.operator not in ('&&', '||'):
                        output[:] = ['('] + ['    ' + part for part in output] + [')']
            lines[-1] += ' ' + term.operator + ' ' + parts[0]
            return lines + parts[1:]
        if term.operator == '?:':
            condition, yes, no = term.children
            lines = ['(']
            condition_lines = self.lines(condition, width=width - 8)
            lines.append('    (' + condition_lines[0])
            lines.extend('     ' + part for part in condition_lines[1:])
            lines[-1] += ') ?'
            lines.extend('        ' + part for part in self.lines(yes, width=width - 8))
            lines.append('    :')
            lines.extend('        ' + part for part in self.lines(no, width=width - 8))
            return lines + [')']
        if term.operator == '!' and term.children[0].operator in ('&&', '||'):
            lines = self.lines(term.children[0], width=width - 1, force=True)
            lines[0] = '!' + lines[0]
            return lines
        if term.operator in ('==', '!=', '<', '<=', '>', '>='):
            # Frame equalities often wrap a large branch join. Lay out that
            # conditional too, rather than hiding it on a single huge line.
            left, right = term.children
            if right.operator == '?:':
                lines = self.lines(right, width=width - len(self.inline(left)) - 4)
                if len(lines) > 1:
                    lines[0] = self._operand(left, _PRECEDENCE[term.operator], equal=True) + ' ' + term.operator + ' ' + lines[0]
                    return lines
        # A long arithmetic/function term remains exact, never silently cut.
        return [text]
