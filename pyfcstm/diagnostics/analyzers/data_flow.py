"""Variable data-flow design-health diagnostics."""

from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set, Tuple

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import StateInfo, TransitionInfo, VariableInfo


def collect_data_flow_warnings(
    variables: Iterable['VariableInfo'],
    reachability_graph,
    states: Iterable['StateInfo'] = (),
    root_state_path: Optional[str] = None,
    transitions: Iterable['TransitionInfo'] = (),
) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    variables = list(variables)
    states = list(states)
    transitions = list(transitions)
    state_parent_paths = _state_parent_paths(states)
    exit_transition_sources = _exit_transition_sources(transitions)
    normal_edges, initial_edges = _direct_reachability_edges(states, transitions)
    diagnostics.extend(_guard_vars_never_change_diagnostics(variables))
    for variable in variables:
        diagnostics.extend(_variable_usage_diagnostics(
            variable,
            reachability_graph,
            state_parent_paths,
            root_state_path,
            exit_transition_sources,
            normal_edges,
            initial_edges,
        ))
    return diagnostics


def _variable_usage_diagnostics(
    variable: 'VariableInfo',
    reachability_graph,
    state_parent_paths: Dict[str, Optional[str]],
    root_state_path: Optional[str],
    exit_transition_sources: Set[str],
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
) -> List[ModelDiagnostic]:
    usage_read_states = _usage_read_states(variable)
    liveness_read_states = _liveness_read_states(variable)
    initial_guard_read_edges = _initial_guard_read_edges(variable)
    effect_read_edges = _effect_read_edges(variable)
    write_states = _write_states(variable)
    if not usage_read_states and not write_states:
        return [_unreferenced_var_diagnostic(variable)]
    if usage_read_states and not write_states:
        return [_unwritten_read_var_diagnostic(variable, usage_read_states)]
    if write_states and not usage_read_states:
        return [_write_only_var_diagnostic(variable, write_states)]

    final_writes = _final_write_locations(
        variable,
        liveness_read_states,
        reachability_graph,
        state_parent_paths,
        root_state_path,
        exit_transition_sources,
        normal_edges,
        initial_edges,
        initial_guard_read_edges,
        effect_read_edges,
    )
    if final_writes:
        return [
            ModelDiagnostic(
                code='W_VARIABLE_NEVER_READ_AFTER_FINAL_WRITE',
                severity='warning',
                message=(
                    f'Variable {variable.name!r} has final write sites '
                    'with no reachable later read.'
                ),
                refs={
                    'var_name': variable.name,
                    'write_locations': final_writes,
                },
            )
        ]
    return []


def _state_parent_paths(
    states: Iterable['StateInfo'],
) -> Dict[str, Optional[str]]:
    return {
        state.path: state.parent_path
        for state in states
    }


def _exit_transition_sources(
    transitions: Iterable['TransitionInfo'],
) -> Set[str]:
    return {
        transition.from_path
        for transition in transitions
        if transition.to_path == '[*]'
    }


def _direct_reachability_edges(
    states: Iterable['StateInfo'],
    transitions: Iterable['TransitionInfo'],
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    normal_edges: Dict[str, Set[str]] = {
        state.path: set()
        for state in states
    }
    initial_edges: Dict[str, Set[str]] = {
        state.path: set()
        for state in states
    }
    for transition in transitions:
        if transition.from_path == '[*]' or transition.to_path == '[*]':
            continue
        if transition.from_path in normal_edges:
            normal_edges[transition.from_path].add(transition.to_path)
    for state in states:
        for target in getattr(state, 'initial_targets', ()):
            target_path = target.get('target')
            if target_path != '[*]':
                initial_edges[state.path].add(target_path)
    return normal_edges, initial_edges


def _usage_read_states(variable: 'VariableInfo') -> Set[str]:
    read_states = set(variable.read_in_states)
    read_states.update(
        _guard_read_state(from_path, to_path)
        for from_path, to_path, _ in _guard_occurrences(variable)
    )
    return read_states


def _liveness_read_states(variable: 'VariableInfo') -> Set[str]:
    read_states = set(variable.read_in_states)
    read_states.update(
        from_path
        for from_path, _, _ in _guard_occurrences(variable)
        if from_path != '[*]'
    )
    return read_states


def _guard_occurrences(variable: 'VariableInfo') -> Tuple[Tuple[str, str, str], ...]:
    occurrences = getattr(variable, 'read_in_guard_occurrences', ())
    if occurrences:
        return tuple(occurrences)
    return tuple(
        (from_path, to_path, f'{from_path}->{to_path}')
        for from_path, to_path in variable.read_in_guards
    )


def _guard_read_state(from_path: str, to_path: str) -> str:
    if from_path == '[*]':
        return to_path
    return from_path


def _initial_guard_read_edges(variable: 'VariableInfo') -> Set[Tuple[str, str]]:
    edges: Set[Tuple[str, str]] = set()
    for from_path, to_path, occurrence_key in _guard_occurrences(variable):
        if from_path != '[*]':
            continue
        owner = _initial_guard_owner(occurrence_key, to_path)
        if owner is not None:
            edges.add((owner, to_path))
    return edges


def _initial_guard_owner(occurrence_key: str, target_path: str) -> Optional[str]:
    if occurrence_key and '#' in occurrence_key:
        owner, _ = occurrence_key.rsplit('#', 1)
        if owner:
            return owner
    if '.' in target_path:
        return target_path.rsplit('.', 1)[0]
    return None


def _write_states(variable: 'VariableInfo') -> Set[str]:
    write_states = set(variable.written_in_states)
    write_states.update(src for src, _ in variable.written_in_effects)
    return write_states


def _unreferenced_var_diagnostic(variable: 'VariableInfo') -> ModelDiagnostic:
    if variable.abstract_actions_in_scope:
        return ModelDiagnostic(
            code='I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
            severity='info',
            message=(
                f'Variable {variable.name!r} is unused in DSL statements, '
                'but abstract actions may use it externally.'
            ),
            refs={
                'var_name': variable.name,
                'abstract_actions_in_scope': list(variable.abstract_actions_in_scope),
            },
        )
    return ModelDiagnostic(
        code='W_UNREFERENCED_VAR',
        severity='warning',
        message=f'Variable {variable.name!r} is never read or written.',
        refs={
            'var_name': variable.name,
            'init_value': variable.init_value,
        },
    )


def _unwritten_read_var_diagnostic(
    variable: 'VariableInfo',
    read_states: Set[str],
) -> ModelDiagnostic:
    return ModelDiagnostic(
        code='W_UNWRITTEN_READ_VAR',
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
    )


def _write_only_var_diagnostic(
    variable: 'VariableInfo',
    write_states: Set[str],
) -> ModelDiagnostic:
    return ModelDiagnostic(
        code='W_WRITE_ONLY_VAR',
        severity='warning',
        message=f'Variable {variable.name!r} is written but never read.',
        refs={
            'var_name': variable.name,
            'written_states': sorted(write_states),
        },
    )


def _guard_vars_never_change_diagnostics(
    variables: List['VariableInfo'],
) -> List[ModelDiagnostic]:
    writes_by_var = {
        variable.name: _write_states(variable)
        for variable in variables
    }
    guard_vars: Dict[Tuple[str, str, str], Set[str]] = {}
    for variable in variables:
        occurrences = getattr(variable, 'read_in_guard_occurrences', ())
        if not occurrences:
            occurrences = tuple(
                (from_path, to_path, f'{from_path}->{to_path}')
                for from_path, to_path in variable.read_in_guards
            )
        for occurrence in occurrences:
            guard_vars.setdefault(occurrence, set()).add(variable.name)

    diagnostics: List[ModelDiagnostic] = []
    emitted_refs: Set[Tuple[Tuple[str, ...], Optional[str]]] = set()
    for occurrence, names in sorted(guard_vars.items()):
        never_changed = sorted(
            name for name in names
            if not writes_by_var.get(name)
        )
        if len(never_changed) != len(names):
            continue
        ref_key = (tuple(never_changed), None)
        if ref_key in emitted_refs:
            continue
        emitted_refs.add(ref_key)
        from_path, to_path, _ = occurrence
        diagnostics.append(ModelDiagnostic(
            code='W_GUARD_VARS_NEVER_CHANGE',
            severity='warning',
            message=(
                f'Transition {from_path!r} -> {to_path!r} guard only reads '
                'variables that never change.'
            ),
            refs={
                'transition_span': None,
                'guard_vars': never_changed,
            },
        ))
    return diagnostics


def _final_write_locations(
    variable: 'VariableInfo',
    read_states: Set[str],
    reachability_graph,
    state_parent_paths: Dict[str, Optional[str]],
    root_state_path: Optional[str],
    exit_transition_sources: Set[str],
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
    initial_guard_read_edges: Set[Tuple[str, str]],
    effect_read_edges: Set[Tuple[str, str]],
) -> List[str]:
    out: List[str] = []
    action_writes = _action_write_stages(variable)
    if not action_writes:
        action_writes = tuple((state_path, None) for state_path in variable.written_in_states)
    for state_path, stage in action_writes:
        if _has_reachable_read_after_action_write(
            state_path,
            stage,
            read_states,
            reachability_graph,
            state_parent_paths,
            root_state_path,
            exit_transition_sources,
            normal_edges,
            initial_edges,
            initial_guard_read_edges,
            effect_read_edges,
        ):
            continue
        out.append(state_path)
    effect_writes = _effect_write_edges(variable)
    for from_path, to_path in effect_writes:
        if to_path == '[*]':
            if _has_reachable_read_after_exit_effect(
                from_path,
                read_states,
                reachability_graph,
                state_parent_paths,
                root_state_path,
                normal_edges,
                initial_edges,
                initial_guard_read_edges,
            ):
                continue
        else:
            if _has_reachable_read(
                to_path,
                read_states,
                reachability_graph,
                normal_edges,
                initial_edges,
                initial_guard_read_edges,
            ):
                continue
        out.append(f'{from_path}->{to_path}')
    return sorted(set(out))


def _action_write_stages(variable: 'VariableInfo') -> Tuple[Tuple[str, Optional[str]], ...]:
    return tuple(
        (state_path, stage)
        for state_path, stage in getattr(variable, 'written_in_action_stages', ())
    )


def _effect_write_edges(variable: 'VariableInfo') -> Tuple[Tuple[str, str], ...]:
    occurrences = getattr(variable, 'written_in_effect_occurrences', ())
    if occurrences:
        return tuple((from_path, to_path) for from_path, to_path, _ in occurrences)
    return tuple(variable.written_in_effects)


def _effect_read_edges(variable: 'VariableInfo') -> Set[Tuple[str, str]]:
    occurrences = getattr(variable, 'read_in_effect_occurrences', ())
    return {
        (from_path, to_path)
        for from_path, to_path, _ in occurrences
    }


def _has_reachable_read_after_action_write(
    state_path: str,
    stage: Optional[str],
    read_states: Set[str],
    reachability_graph,
    state_parent_paths: Dict[str, Optional[str]],
    root_state_path: Optional[str],
    exit_transition_sources: Set[str],
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
    initial_guard_read_edges: Set[Tuple[str, str]],
    effect_read_edges: Set[Tuple[str, str]],
) -> bool:
    if stage != 'exit':
        return _has_reachable_read(
            state_path,
            read_states,
            reachability_graph,
            normal_edges,
            initial_edges,
            initial_guard_read_edges,
        )
    if _has_reachable_read_after_exiting_subtree(
        state_path,
        state_path,
        read_states,
        reachability_graph,
        include_start=False,
        normal_edges=normal_edges,
        initial_edges=initial_edges,
        initial_guard_read_edges=initial_guard_read_edges,
    ):
        return True
    if _has_transition_effect_read_after_exit(state_path, effect_read_edges):
        return True
    exit_parent = _exit_transition_parent_start(
        state_path,
        state_parent_paths,
        root_state_path,
        exit_transition_sources,
    )
    return (
        exit_parent is not None and
        _has_reachable_read_after_exiting_subtree(
            exit_parent,
            exit_parent,
            read_states,
            reachability_graph,
            include_start=True,
            normal_edges=normal_edges,
            initial_edges=initial_edges,
            initial_guard_read_edges=initial_guard_read_edges,
        )
    )


def _has_transition_effect_read_after_exit(
    state_path: str,
    effect_read_edges: Set[Tuple[str, str]],
) -> bool:
    return any(
        from_path == state_path or _is_descendant_path(state_path, from_path)
        for from_path, _ in effect_read_edges
    )


def _has_reachable_read_after_exit_effect(
    from_path: str,
    read_states: Set[str],
    reachability_graph,
    state_parent_paths: Dict[str, Optional[str]],
    root_state_path: Optional[str],
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
    initial_guard_read_edges: Set[Tuple[str, str]],
) -> bool:
    parent_path = _exit_transition_parent_start(
        from_path,
        state_parent_paths,
        root_state_path,
        {from_path},
    )
    return (
        parent_path is not None and
        _has_reachable_read_after_exiting_subtree(
            parent_path,
            parent_path,
            read_states,
            reachability_graph,
            include_start=True,
            normal_edges=normal_edges,
            initial_edges=initial_edges,
            initial_guard_read_edges=initial_guard_read_edges,
        )
    )


def _has_reachable_read_after_exiting_subtree(
    start_path: str,
    exited_path: str,
    read_states: Set[str],
    reachability_graph,
    include_start: bool,
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
    initial_guard_read_edges: Set[Tuple[str, str]],
) -> bool:
    if start_path in normal_edges:
        seen = {(start_path, False)}
        queue = [(start_path, False)]
        while queue:
            current, allow_initial = queue.pop(0)
            if current in read_states and (
                allow_initial or current != start_path or include_start
            ):
                return True
            next_paths = set(normal_edges.get(current, ()))
            if allow_initial:
                for target in initial_edges.get(current, ()):
                    if (current, target) in initial_guard_read_edges:
                        return True
                    next_paths.add(target)
            for next_path in sorted(next_paths):
                item = (next_path, True)
                if item in seen:
                    continue
                seen.add(item)
                queue.append(item)
        return False

    if include_start and start_path in read_states:
        return True
    for reachable in reachability_graph.get(start_path, ()):
        if _is_descendant_path(reachable, exited_path):
            continue
        if reachable in read_states:
            return True
    return False


def _exit_transition_parent_start(
    state_path: str,
    state_parent_paths: Dict[str, Optional[str]],
    root_state_path: Optional[str],
    exit_transition_sources: Set[str],
) -> Optional[str]:
    if state_path not in exit_transition_sources:
        return None
    parent_path = state_parent_paths.get(state_path)
    if parent_path is None or parent_path == root_state_path:
        return None
    return parent_path


def _has_reachable_read(
    start_path: str,
    read_states: Set[str],
    reachability_graph,
    normal_edges: Dict[str, Set[str]],
    initial_edges: Dict[str, Set[str]],
    initial_guard_read_edges: Set[Tuple[str, str]],
) -> bool:
    if start_path in normal_edges:
        seen = {start_path}
        queue = [start_path]
        while queue:
            current = queue.pop(0)
            if current in read_states:
                return True
            next_paths = set(normal_edges.get(current, ()))
            for target in initial_edges.get(current, ()):
                if (current, target) in initial_guard_read_edges:
                    return True
                next_paths.add(target)
            for next_path in sorted(next_paths):
                if next_path in seen:
                    continue
                seen.add(next_path)
                queue.append(next_path)
        return False

    if start_path in read_states:
        return True
    for reachable in reachability_graph.get(start_path, ()):
        if reachable in read_states:
            return True
    return False


def _is_descendant_path(path: str, ancestor_path: str) -> bool:
    return path.startswith(ancestor_path + '.')
