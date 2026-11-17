"""Bind authored activity queries and lower them to independent state flags."""

import re
from dataclasses import dataclass, fields, replace
from typing import Mapping, Tuple

from .expr import ActiveStateQuery, BinaryOp, Expr, Integer, Variable
from .region import Region, namespace_actions, namespace_child, walk_namespaces
from ..utils.validate import ModelDiagnostic


@dataclass(frozen=True)
class ActiveQuery:
    """One queried State and the hidden variable representing its activity.

    :param state_path: Fully qualified State path, including Region segments.
    :param variable_name: Deterministic, collision-free model variable name.
    """

    state_path: Tuple[str, ...]
    variable_name: str


def _operation_expressions(statements):
    """Yield writable expression slots in nested operation blocks."""
    from .model import IfBlock

    for statement in statements:
        if isinstance(statement, IfBlock):
            for branch in statement.branches:
                if branch.condition is not None:
                    yield branch, 'condition'
                yield from _operation_expressions(branch.statements)
        else:
            yield statement, 'expr'


def _expression_slots(root, defines):
    """Yield model expression owners without following action references."""
    for definition in defines.values():
        if definition.init is not None:
            yield definition, 'init'
    for namespace in walk_namespaces(root):
        for transition in namespace.transitions:
            for name in ('guard', 'history_user_guard'):
                if getattr(transition, name, None) is not None:
                    yield transition, name
            yield from _operation_expressions(transition.effects)
        for action in namespace_actions(namespace):
            yield from _operation_expressions(action.operations)


def _target(root, query):
    """Return a target State and any structured path-validation failure."""
    path = query.path
    parts = tuple(path[1:].split('.')) if path.startswith('/') else tuple(path.split('.'))
    if path.startswith('/'):
        parts = (root.name, *parts)
    if (not all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', part) for part in parts)
            or parts[0] != root.name):
        return None, 'invalid_path'
    current = root
    for segment in parts[1:]:
        current = namespace_child(current, segment)
        if current is None:
            return None, 'not_found'
    if isinstance(current, Region):
        return None, 'region'
    if current.is_pseudo:
        return None, 'pseudo'
    return current, None


def _rewrite(expression, variables):
    """Replace queries while preserving the surrounding expression structure."""
    if isinstance(expression, ActiveStateQuery):
        return BinaryOp(Variable(variables[id(expression)]), '!=', Integer(0))
    updates = {
        item.name: _rewrite(getattr(expression, item.name), variables)
        for item in fields(expression) if isinstance(getattr(expression, item.name), Expr)
    }
    return replace(expression, **updates) if updates else expression


def lower_active(root, defines, sink, *, apply=True):
    """Validate queries and optionally install hidden variables and actions.

    Only queried States receive flags. Each generated write is an anonymous
    action of its own, leaving named action bodies and their callers unchanged.
    Source locations deduplicate diagnostic sites shared by combo expansion.
    """
    from .model import OnStage, Operation, VarDefine

    slots = list(_expression_slots(root, defines))
    targets, seen, invalid = {}, set(), False
    for owner, attribute in slots:
        for expression in getattr(owner, attribute)._iter_all_subs():
            if not isinstance(expression, ActiveStateQuery):
                continue
            state, reason = _target(root, expression)
            if attribute == 'init':
                reason = 'initializer'
            if reason is not None:
                invalid = True
                source_path = getattr(expression, '_source_path', None)
                location = expression._span if expression._span is not None else id(expression)
                key = (expression.path, location, source_path, reason)
                if key not in seen:
                    seen.add(key)
                    sink.emit(ModelDiagnostic(
                        code='E_ACTIVE_QUERY_TARGET', severity='error',
                        message='Invalid active query %r (%s).' % (expression.path, reason),
                        span=expression._span,
                        refs={'state_path': expression.path, 'reason': reason,
                              'source_path': source_path},
                    ))
            else:
                targets[id(expression)] = state.path
    if invalid:
        return ()
    if not targets:
        return ()
    queried = set(targets.values())
    occupied = set(defines)
    occupied.update(owner.var_name for owner, _ in slots if isinstance(owner, Operation))
    metadata = []
    for state in root.walk_states():
        if state.path not in queried:
            continue
        base = '__active_' + '_'.join(state.path)
        name, suffix = base, 2
        while name in occupied:
            name = '%s_%d' % (base, suffix)
            suffix += 1
        occupied.add(name)
        metadata.append(ActiveQuery(state.path, name))
        if apply:
            defines[name] = VarDefine(name=name, type='int', init=Integer(0))
            for stage, value in (('enter', 1), ('exit', 0)):
                action = OnStage(
                    stage=stage, aspect=None, name=None, doc=None,
                    operations=[Operation(name, Integer(value))],
                    is_abstract=False, state_path=(*state.path, None),
                )
                action.parent = state
                if stage == 'enter':
                    state.on_enters.insert(0, action)
                else:
                    state.on_exits.append(action)
    names = {item.state_path: item.variable_name for item in metadata}
    if apply:
        variables = {identity: names[path] for identity, path in targets.items()}
        for owner, attribute in slots:
            setattr(owner, attribute, _rewrite(getattr(owner, attribute), variables))
    result = tuple(metadata)
    for state in root.walk_states():
        state._active_queries = result
    return result


def restore_active_expression(expression: Expr, paths: Mapping[str, str]) -> Expr:
    """Turn lowered activity tests back into the ``active("path")`` they came from.

    :func:`lower_active` replaces every query with ``<flag> != 0``. This is
    the inverse, used by exporters that show the model as the user wrote it. The
    input is never modified; subtrees without a lowered test are shared with
    the returned expression.

    :param expression: Expression of a lowered model.
    :type expression: pyfcstm.model.expr.Expr
    :param paths: Hidden flag variable name mapped to the dotted full path of
        the queried state, as in :attr:`pyfcstm.model.model.StateMachine.active_queries`.
    :type paths: Mapping[str, str]
    :return: An equivalent expression whose lowered tests are
        :class:`pyfcstm.model.expr.ActiveStateQuery` nodes.
    :rtype: pyfcstm.model.expr.Expr

    Example::

        >>> from pyfcstm.model.active import restore_active_expression
        >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
        >>> lowered = BinaryOp(Variable('__active_Root_On'), '!=', Integer(0))
        >>> str(restore_active_expression(lowered, {'__active_Root_On': 'Root.On'}).to_ast_node())
        'active("Root.On")'
        >>> other = BinaryOp(Variable('x'), '!=', Integer(0))
        >>> restore_active_expression(other, {'__active_Root_On': 'Root.On'}) is other
        True
    """
    if (isinstance(expression, BinaryOp) and expression.op == '!='
            and isinstance(expression.x, Variable) and expression.x.name in paths
            and isinstance(expression.y, Integer) and expression.y.value == 0):
        return ActiveStateQuery(paths[expression.x.name])
    updates = {}
    for item in fields(expression):
        value = getattr(expression, item.name)
        if isinstance(value, Expr):
            restored = restore_active_expression(value, paths)
            if restored is not value:
                updates[item.name] = restored
    return replace(expression, **updates) if updates else expression


def restore_active_statements(statements, paths: Mapping[str, str]) -> list:
    """Restore ``active("path")`` tests inside operation statements.

    Applies :func:`restore_active_expression` to every assignment value and
    every ``if`` condition, including nested blocks, and returns new statement
    objects; the model's own statements are left untouched.

    :param statements: Operation statements (assignments and ``if`` blocks).
    :type statements: Iterable[pyfcstm.model.model.OperationStatement]
    :param paths: Hidden flag variable name mapped to the dotted state path.
    :type paths: Mapping[str, str]
    :return: New statements, in the original order.
    :rtype: list

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.active import restore_active_statements
        >>> machine = load_state_machine_from_text(
        ...     'state Root { state A; [*] -> A; A -> [*] effect { if [active("Root.A")] { } } }')
        >>> paths = {item.variable_name: '.'.join(item.state_path)
        ...          for item in machine.active_queries}
        >>> edge = machine.root_state.transitions[1]
        >>> restored = restore_active_statements(edge.effects, paths)
        >>> 'active("Root.A")' in str(restored[0].to_ast_node())
        True
    """
    from .model import IfBlock

    result = []
    for statement in statements:
        if isinstance(statement, IfBlock):
            branches = [
                replace(
                    branch,
                    condition=(None if branch.condition is None
                               else restore_active_expression(branch.condition, paths)),
                    statements=restore_active_statements(branch.statements, paths),
                )
                for branch in statement.branches
            ]
            result.append(replace(statement, branches=branches))
        else:
            result.append(replace(statement, expr=restore_active_expression(statement.expr, paths)))
    return result
