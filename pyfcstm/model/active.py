"""
Bind authored activity queries and lower them to independent state flags.

FCSTM conditions may ask whether a state is active, written
``active("Root.Run.Motion.Move")``. During model construction each such query
is bound to a concrete state and rewritten to a comparison on a hidden integer
variable (``__active_Root_Run_Motion_Move != 0``). That variable is set to
``1`` by an action inserted at the start of the state's ``enter`` actions and
cleared to ``0`` by one appended to its ``exit`` actions, so downstream
consumers only ever see ordinary variables and ordinary actions. Only states
that are actually queried receive a flag.

The module contains:

* :class:`ActiveQuery` - Bound target and hidden-variable name of one query
* :func:`lower_active` - Validate queries, then install flags and rewrite
  conditions (invoked by model construction)

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... def int x = 0;
    ... state Root {
    ...     [*] -> Run;
    ...     state Run {
    ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
    ...         region Guard { [*] -> Watch; state Watch; }
    ...     }
    ...     state Off;
    ...     Run -> Off : if [active("Root.Run.Motion.Move") && x > 3];
    ... }
    ... ''')
    >>> model.active_queries
    (ActiveQuery(state_path=('Root', 'Run', 'Motion', 'Move'), variable_name='__active_Root_Run_Motion_Move'),)
    >>> list(model.defines)
    ['x', '__active_Root_Run_Motion_Move']
    >>> str(model.root_state.transitions[-1].guard)
    '__active_Root_Run_Motion_Move != 0 && x > 3'
"""

import re
from dataclasses import dataclass, fields, replace
from typing import Tuple

from .expr import ActiveStateQuery, BinaryOp, Expr, Integer, Variable
from .region import Region, namespace_actions, namespace_child, walk_namespaces
from ..utils.validate import ModelDiagnostic


@dataclass(frozen=True)
class ActiveQuery:
    """
    One queried State and the hidden variable representing its activity.

    Instances are produced by model construction and exposed as
    :attr:`pyfcstm.model.model.StateMachine.active_queries`, one per distinct
    queried state. Use :meth:`pyfcstm.model.model.StateMachine.active_variables`
    to evaluate every flag for a :class:`~pyfcstm.model.configuration.Configuration`.

    :param state_path: Fully qualified State path, including Region segments.
    :type state_path: Tuple[str, ...]
    :param variable_name: Deterministic, collision-free model variable name.
    :type variable_name: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off : if [active("Root.Run.Motion.Move") && x > 3];
        ... }
        ... ''')
        >>> query = model.active_queries[0]
        >>> query.state_path
        ('Root', 'Run', 'Motion', 'Move')
        >>> query.variable_name in model.defines
        True
        >>> from pyfcstm.model import Configuration
        >>> config = Configuration.parse(model, 'Root.Run{Motion: Move, Guard: Watch}')
        >>> model.active_variables(config)
        {'__active_Root_Run_Motion_Move': 1}
    """

    state_path: Tuple[str, ...]
    variable_name: str


def _operation_expressions(statements):
    """
    Yield every expression slot inside a list of operation statements.

    A slot is an ``(owner, attribute_name)`` pair that can be read with
    ``getattr`` and replaced with ``setattr``: ``'expr'`` on an assignment,
    ``'condition'`` on each ``if``/``else if`` branch. ``else`` branches have no
    condition and are skipped; nested blocks are followed recursively.

    :param statements: Operations and :class:`~pyfcstm.model.model.IfBlock` objects.
    :type statements: Iterable[Union[pyfcstm.model.model.Operation, pyfcstm.model.model.IfBlock]]
    :return: Generator of ``(owner, attribute_name)`` pairs.
    :rtype: Iterator[Tuple[object, str]]
    """
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
    """
    Yield every expression slot of a model, in a fixed deterministic order.

    Order is variable initializers, then for each namespace in
    :func:`~pyfcstm.model.region.walk_namespaces` order the transition guards,
    history guards and effects, then the bodies of its own actions. Actions
    that merely reference a named action (``ref``) are not followed, so each
    expression is visited exactly once.

    :param root: Root state whose subtree is scanned.
    :type root: pyfcstm.model.model.State
    :param defines: Variable definitions of the model.
    :type defines: Dict[str, pyfcstm.model.model.VarDefine]
    :return: Generator of ``(owner, attribute_name)`` pairs.
    :rtype: Iterator[Tuple[object, str]]
    """
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
    """
    Bind an authored query to its target state.

    :param root: Root state of the model.
    :type root: pyfcstm.model.model.State
    :param query: The authored query; ``query.path`` is either a full path
        starting at the root state's name or a ``/``-prefixed path relative to
        the root.
    :type query: pyfcstm.model.expr.ActiveStateQuery
    :return: ``(state, None)`` on success, otherwise ``(None, reason)`` where
        ``reason`` is ``'invalid_path'`` (malformed or wrong root), ``'not_found'``
        (unknown child), ``'region'`` (the path names a region) or ``'pseudo'``
        (the path names a pseudo state).
    :rtype: Tuple[Optional[pyfcstm.model.model.State], Optional[str]]
    """
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
    """
    Replace every bound query in an expression tree with a flag comparison.

    Each :class:`~pyfcstm.model.expr.ActiveStateQuery` becomes
    ``<variable> != 0``. Other nodes are copied only when one of their
    sub-expressions changed, so untouched subtrees are shared, not cloned.

    :param expression: Expression to rewrite.
    :type expression: pyfcstm.model.expr.Expr
    :param variables: Hidden variable name for each query, keyed by ``id()`` of
        the query object.
    :type variables: Dict[int, str]
    :return: The rewritten expression (the input itself if it held no query).
    :rtype: pyfcstm.model.expr.Expr
    """
    if isinstance(expression, ActiveStateQuery):
        return BinaryOp(Variable(variables[id(expression)]), '!=', Integer(0))
    updates = {
        item.name: _rewrite(getattr(expression, item.name), variables)
        for item in fields(expression) if isinstance(getattr(expression, item.name), Expr)
    }
    return replace(expression, **updates) if updates else expression


def lower_active(root, defines, sink, *, apply=True):
    """
    Validate queries and optionally install hidden variables and actions.

    Only queried States receive flags. Each generated write is an anonymous
    action of its own, leaving named action bodies and their callers unchanged.
    Source locations deduplicate diagnostic sites shared by combo expansion.

    The function runs in two steps. First every query is bound to a state
    (see ``E_ACTIVE_QUERY_TARGET`` reasons ``invalid_path``, ``not_found``,
    ``region``, ``pseudo`` and ``initializer``, the last for a query inside a
    variable initializer); if any fails, nothing is changed and ``()`` is
    returned. Then a hidden variable ``__active_<path joined by _>`` is chosen
    per queried state, with a numeric suffix to avoid collisions with user
    variables, and, when ``apply`` is true, the variable is declared, set to
    ``1`` first in the state's enter actions, cleared to ``0`` last in its exit
    actions, and every query is rewritten to ``<variable> != 0``.

    Model construction calls this function; it is documented here because its
    results are the public ``active()`` contract.

    :param root: Root state of the model; flags are installed on its subtree.
    :type root: pyfcstm.model.model.State
    :param defines: Variable definitions, extended in place with the hidden
        variables when ``apply`` is true.
    :type defines: Dict[str, pyfcstm.model.model.VarDefine]
    :param sink: Receives ``E_ACTIVE_QUERY_TARGET`` diagnostics; a strict sink
        raises on the first.
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink
    :param apply: When ``False`` only validate and describe the queries: no
        variable, action or rewrite is installed and the queries stay as
        written. Defaults to ``True``.
    :type apply: bool, optional
    :return: One :class:`ActiveQuery` per distinct queried state, in state walk
        order; ``()`` if there are no queries or any is invalid.
    :rtype: Tuple[ActiveQuery, ...]
    :raises pyfcstm.utils.validate.ModelValidationError: If a query is invalid
        and ``sink`` is strict.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off : if [active("Root.Run.Motion.Move") && x > 3];
        ... }
        ... ''')
        >>> move = model.root_state.substates['Run'].regions['Motion'].substates['Move']
        >>> [(action.stage, action.operations[0].var_name, action.operations[0].expr.value)
        ...  for action in move.on_enters + move.on_exits]
        [('enter', '__active_Root_Run_Motion_Move', 1), ('exit', '__active_Root_Run_Motion_Move', 0)]
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.utils.validate import ModelValidationError
        >>> try:
        ...     load_state_machine_from_text('''
        ...     state Root { [*] -> A; state A; A -> B : if [active("Root.Nope")]; state B; }
        ...     ''')
        ... except ModelValidationError as error:
        ...     print([(item.code, item.message) for item in error.diagnostics])
        [('E_ACTIVE_QUERY_TARGET', "Invalid active query 'Root.Nope' (not_found).")]
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
