"""
Variable data-flow design-health diagnostics.

This module turns the per-variable read/write summaries that
:func:`pyfcstm.diagnostics.inspect.inspect_model` collects into design-health
warnings: variables that never influence a transition guard, variables that
are read but never written, variables that are written but never read, and
guards that depend only on variables nothing ever changes. It works on the
precomputed :class:`pyfcstm.diagnostics.inspect.VariableInfo` records rather
than re-walking the model, so it stays cheap and consistent with the report.

The module contains:

* :func:`collect_data_flow_warnings` - Derive the data-flow warnings from
  variable summaries

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> from pyfcstm.diagnostics.inspect import inspect_model
    >>> from pyfcstm.diagnostics.analyzers.data_flow import collect_data_flow_warnings
    >>> machine = load_state_machine_from_text('''
    ... def int spare = 0;
    ... state Root { state A; [*] -> A; }
    ... ''')
    >>> report = inspect_model(machine)
    >>> [d.code for d in collect_data_flow_warnings(report.variables, machine)]
    ['W_UNREFERENCED_VAR']
"""

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from ...dsl import EXIT_STATE, INIT_STATE
from ...utils.validate import ModelDiagnostic
from .use_def import collect_expr_variables

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import VariableInfo
    from ...model.model import StateMachine

_INIT_MARK = '[*]'
_EXIT_MARK = '[*]'


def collect_data_flow_warnings(
        variables: Iterable['VariableInfo'],
        machine: Optional['StateMachine'] = None,
) -> List[ModelDiagnostic]:
    """
    Derive data-flow design-health warnings from variable summaries.

    Only variables whose ``role`` is ``'control'`` are checked for the first
    three findings below; they are evaluated per variable in the order given.

    * A variable that affects no transition guard, neither directly nor
      through the use-def graph, yields ``W_UNREFERENCED_VAR`` (severity
      ``warning``). When abstract actions are in scope, which may use the
      variable in ways the model cannot see, the finding is downgraded to
      ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT`` (severity ``info``). A variable
      that is neither read nor written anywhere additionally carries a
      ``definition_delete_anchor`` entry in ``refs``.
    * A variable that is read but never written yields
      ``W_UNWRITTEN_READ_VAR``, with ``read_states`` and ``init_value`` in
      ``refs``.
    * A variable that is written but never read yields ``W_WRITE_ONLY_VAR``,
      with ``written_states`` in ``refs``.

    When ``machine`` is given, every guarded transition whose guard reads only
    ``control`` variables that no action or effect writes additionally yields
    ``W_GUARD_VARS_NEVER_CHANGE``, with ``from_path``, ``to_path`` and
    ``guard_vars`` in ``refs``. Variables with any other role count as supplied
    from outside and never trigger it. Without ``machine`` this last check is
    skipped because there is no transition list to scan.

    :param variables: Variable summaries, normally
        :attr:`pyfcstm.diagnostics.inspect.ModelInspect.variables`.
    :type variables: Iterable[pyfcstm.diagnostics.inspect.VariableInfo]
    :param machine: State machine used for the guard-variable check, defaults
        to ``None``.
    :type machine: Optional[pyfcstm.model.model.StateMachine], optional
    :return: Warnings in variable order, followed by the guard-variable
        warnings in model traversal order.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.diagnostics.inspect import inspect_model
        >>> from pyfcstm.diagnostics.analyzers.data_flow import collect_data_flow_warnings
        >>> machine = load_state_machine_from_text('''
        ... def int limit = 3;
        ... def int spare = 0;
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [limit > 1];
        ... }
        ... ''')
        >>> report = inspect_model(machine)
        >>> for item in collect_data_flow_warnings(report.variables, machine):
        ...     print(item.code, item.refs.get('var_name', item.refs.get('guard_vars')))
        W_UNWRITTEN_READ_VAR limit
        W_UNREFERENCED_VAR spare
        W_GUARD_VARS_NEVER_CHANGE ['limit']
        >>> [d.code for d in collect_data_flow_warnings(report.variables)]
        ['W_UNWRITTEN_READ_VAR', 'W_UNREFERENCED_VAR']
    """
    from ...model.support import require_supported_model

    if machine is not None:
        require_supported_model(machine, 'Data-flow analysis')
    diagnostics: List[ModelDiagnostic] = []
    variables = list(variables)
    variable_spans = {variable.name: variable.span for variable in variables}
    for variable in variables:
        if variable.role != 'control':
            continue
        read_states = set(variable.read_in_states)
        read_states.update(src for src, _ in variable.read_in_guards)
        write_states = set(variable.written_in_states)
        write_states.update(src for src, _ in variable.written_in_effects)
        if not variable.affects_guard_directly and not variable.affects_guard_indirectly:
            if variable.abstract_actions_in_scope:
                diagnostics.append(ModelDiagnostic(
                    code='I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
                    span=variable.span,
                    severity='info',
                    message=(
                        f'Variable {variable.name!r} does not affect any '
                        'transition guard, but abstract actions may use it.'
                    ),
                    refs={
                        'var_name': variable.name,
                        'abstract_actions_in_scope': list(variable.abstract_actions_in_scope),
                    },
                ))
            else:
                refs = {
                    'var_name': variable.name,
                    'init_value': variable.init_value,
                }
                if not read_states and not write_states:
                    refs['definition_delete_anchor'] = variable.name
                diagnostics.append(ModelDiagnostic(
                    code='W_UNREFERENCED_VAR',
                    span=variable.span,
                    severity='warning',
                    message=(
                        f'Variable {variable.name!r} does not affect any '
                        'transition guard.'
                    ),
                    refs=refs,
                ))
            continue
        if read_states and not write_states:
            diagnostics.append(ModelDiagnostic(
                code='W_UNWRITTEN_READ_VAR',
                span=variable.span,
                severity='warning',
                message=(
                    f'Variable {variable.name!r} is read but never written '
                    'by any action or transition effect.'
                ),
                refs={
                    'var_name': variable.name,
                    'read_states': sorted(read_states),
                    'init_value': variable.init_value,
                },
            ))
        if write_states and not read_states:
            diagnostics.append(ModelDiagnostic(
                code='W_WRITE_ONLY_VAR',
                span=variable.span,
                severity='warning',
                message=f'Variable {variable.name!r} is written but never read.',
                refs={
                    'var_name': variable.name,
                    'written_states': sorted(write_states),
                },
            ))
    diagnostics.extend(_guard_vars_never_change_diagnostics(variables, machine, variable_spans))
    return diagnostics


def _guard_vars_never_change_diagnostics(
        variables: List['VariableInfo'],
        machine: Optional['StateMachine'],
        variable_spans: Dict[str, object],
) -> List[ModelDiagnostic]:
    if machine is None:
        return []
    written_vars = {
        variable.name
        for variable in variables
        if variable.role != 'control' or variable.written_in_states or variable.written_in_effects
    }
    declared_vars = {variable.name for variable in variables}
    diagnostics: List[ModelDiagnostic] = []
    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.guard is None:
                continue
            guard_vars = sorted(
                v for v in collect_expr_variables(transition.guard)
                if v in declared_vars
            )
            if not guard_vars:
                continue
            if any(v in written_vars for v in guard_vars):
                continue
            from_path = _transition_endpoint(
                state,
                transition.from_state,
                is_source=True,
            )
            to_path = _transition_endpoint(
                state,
                transition.to_state,
                is_source=False,
            )
            diagnostics.append(ModelDiagnostic(
                code='W_GUARD_VARS_NEVER_CHANGE',
                span=getattr(transition, '_span', None) or (variable_spans.get(guard_vars[0]) if guard_vars else None),
                severity='warning',
                message=(
                    'Transition guard reads only variables that are never '
                    'changed by actions or effects.'
                ),
                refs={
                    'from_path': from_path,
                    'to_path': to_path,
                    'guard_vars': guard_vars,
                },
            ))
    return diagnostics


def _state_path(state: Any) -> str:
    path = getattr(state, 'path', None)
    if not path:  # pragma: no cover
        return ''
    return '.'.join(p for p in path if p is not None)


def _resolve_sibling_path(parent_state: Any, name: str) -> str:
    parent_path = _state_path(parent_state)
    return f'{parent_path}.{name}' if parent_path else name


def _transition_endpoint(parent_state: Any, marker_or_name: Any, is_source: bool) -> str:
    if marker_or_name is INIT_STATE:
        return _INIT_MARK
    if marker_or_name is EXIT_STATE:
        return _EXIT_MARK
    if isinstance(marker_or_name, str):
        return _resolve_sibling_path(parent_state, marker_or_name)
    return str(marker_or_name)  # pragma: no cover
