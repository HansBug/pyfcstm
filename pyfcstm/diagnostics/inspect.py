"""
Structured model inspection for pyfcstm.

This module provides :func:`inspect_model`, a single entry point that
walks a :class:`pyfcstm.model.StateMachine` and produces a stable,
serialization-friendly view of its structure plus five derived
relational graphs (reachability, event emission, variable data flow,
aspect impact, action reference). The output is the foundation that
Layer 2 design-health warnings (``W_*`` / ``I_*`` codes) and downstream
LLM / evaluation tooling consume.

The view shape is the **single source of truth** for the pyfcstm /
jsfcstm contract. Adding or renaming a field here must be mirrored on
the jsfcstm side (``editors/jsfcstm/src/diagnostics/inspect.ts``) and
in ``pyfcstm/diagnostics/schema.json``.

The module exposes the following dataclasses:

* :class:`StateInfo` — per-state structural summary
* :class:`TransitionInfo` — per-transition structural summary
* :class:`VariableInfo` — per-variable structural summary plus
  participation flags used by ``W_UNREFERENCED_VAR``
* :class:`EventInfo` — per-event structural summary
* :class:`ModelMetrics` — aggregate counts and ratios
* :class:`ModelInspect` — top-level container including diagnostics

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model.parse import parse_dsl_node_to_state_machine
    >>> from pyfcstm.diagnostics import inspect_model
    >>> source = '''
    ... def int counter = 0;
    ... state Root {
    ...     state Idle;
    ...     state Active;
    ...     [*] -> Idle;
    ...     Idle -> Active : if [counter > 0];
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(source, 'state_machine_dsl')
    >>> machine = parse_dsl_node_to_state_machine(ast)
    >>> report = inspect_model(machine)
    >>> report.metrics.n_states_leaf
    2
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .analyzers import collect_design_health_warnings
from ..utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover - import-time forward refs only
    from ..model.expr import Expr
    from ..model.model import (
        OperationStatement,
        OnAspect,
        OnStage,
        StateMachine,
        Transition,
    )


@dataclass(frozen=True)
class StateInfo:
    """
    Structural summary of a single state.

    :param path: Dotted hierarchical path, e.g. ``'Root.SubSystem.Active'``.
    :type path: str
    :param name: Short name of the state (last component of ``path``).
    :type name: str
    :param parent_path: Dotted path of the parent state, or ``None`` for
        the root state.
    :type parent_path: Optional[str]
    :param is_leaf: ``True`` when this state has no substates.
    :type is_leaf: bool
    :param is_pseudo: ``True`` when the state was declared with
        ``pseudo state``.
    :type is_pseudo: bool
    :param is_composite: ``True`` when this state has substates.
    :type is_composite: bool
    :param substates: Direct-child state paths, in source order.
    :type substates: Tuple[str, ...]
    :param initial_targets: Each item describes one ``[*] -> X`` initial
        transition declared inside this composite. ``target`` is the
        target child path, ``guard`` is the source text of the guard or
        ``None``, ``event`` is the qualified event name or ``None``,
        ``is_unconditional`` is ``True`` only when both guard and event
        are absent.
    :type initial_targets: Tuple[Mapping[str, Any], ...]
    :param entry_actions: Action labels (function name or ``'<inline>'``)
        for ``enter`` actions on this state, in source order.
    :type entry_actions: Tuple[str, ...]
    :param during_actions: Action labels for ``during`` actions.
    :type during_actions: Tuple[str, ...]
    :param exit_actions: Action labels for ``exit`` actions.
    :type exit_actions: Tuple[str, ...]
    :param aspect_before: Aspect-action labels for ``>> during before``.
    :type aspect_before: Tuple[str, ...]
    :param aspect_after: Aspect-action labels for ``>> during after``.
    :type aspect_after: Tuple[str, ...]
    :param has_abstract_action: ``True`` if any of the actions above is
        abstract. Used by :class:`VariableInfo` confidence judgements.
    :type has_abstract_action: bool
    """

    path: str
    name: str
    parent_path: Optional[str]
    is_leaf: bool
    is_pseudo: bool
    is_composite: bool
    substates: Tuple[str, ...]
    initial_targets: Tuple[Dict[str, Any], ...]
    entry_actions: Tuple[str, ...]
    during_actions: Tuple[str, ...]
    exit_actions: Tuple[str, ...]
    aspect_before: Tuple[str, ...]
    aspect_after: Tuple[str, ...]
    has_abstract_action: bool


@dataclass(frozen=True)
class TransitionInfo:
    """
    Structural summary of a single transition.

    :param from_path: Dotted path of the source state, or the literal
        ``'[*]'`` for an initial transition declared at the root.
    :type from_path: str
    :param to_path: Dotted path of the target state, or ``'[*]'`` for an
        exit transition.
    :type to_path: str
    :param event: Qualified event name (e.g. ``'Root.SubA.E'``) or
        ``None`` if the transition has no event.
    :type event: Optional[str]
    :param event_scope: ``'local'``, ``'chain'``, ``'absolute'``, or
        ``None`` when there is no event.
    :type event_scope: Optional[str]
    :param guard: Source text of the guard expression, or ``None``.
    :type guard: Optional[str]
    :param effect: Source text of the effect block, or ``None``.
    :type effect: Optional[str]
    :param is_forced: ``True`` when the transition was expanded from a
        ``!``-prefixed forced transition.
    :type is_forced: bool
    :param forced_origin: Raw source text of the original
        ``!X -> Y`` declaration when ``is_forced`` is ``True``, otherwise
        ``None``.
    :type forced_origin: Optional[str]
    """

    from_path: str
    to_path: str
    event: Optional[str]
    event_scope: Optional[str]
    guard: Optional[str]
    effect: Optional[str]
    is_forced: bool
    forced_origin: Optional[str]


@dataclass(frozen=True)
class VariableInfo:
    """
    Structural summary of a variable definition plus participation flags.

    The ``participates_directly`` and ``participates_indirectly`` flags
    are precomputed here so that unreferenced-variable diagnostics can
    be expressed as a one-line filter against this object.

    :param name: Variable identifier.
    :type name: str
    :param type: Declared type, currently ``'int'`` or ``'float'``.
    :type type: str
    :param init_value: Source text of the initializer expression.
    :type init_value: str
    :param read_in_states: State paths where the variable is read inside
        any action (``enter`` / ``during`` / ``exit`` / aspect).
    :type read_in_states: Tuple[str, ...]
    :param written_in_states: State paths where the variable is written
        inside any action.
    :type written_in_states: Tuple[str, ...]
    :param read_in_guards: Tuples ``(from_path, to_path)`` of transitions
        whose guard reads this variable.
    :type read_in_guards: Tuple[Tuple[str, str], ...]
    :param written_in_effects: Tuples ``(from_path, to_path)`` of
        transitions whose effect block writes this variable.
    :type written_in_effects: Tuple[Tuple[str, str], ...]
    :param participates_directly: ``True`` when the variable is read by
        at least one guard, transition effect, or action operation.
    :type participates_directly: bool
    :param participates_indirectly: ``True`` when the variable is not
        directly referenced but is transitively reachable through
        write-then-read data dependency across blocks. The current
        inspect implementation keeps this field as ``False`` for
        variables that lack any read.
    :type participates_indirectly: bool
    :param abstract_actions_in_scope: Function names of abstract actions
        whose enclosing state is on the ancestor chain or sub-tree of
        any state that touches this variable. Downstream diagnostics can
        use this to distinguish high-confidence unused variables from
        variables that may be touched by abstract behavior.
    :type abstract_actions_in_scope: Tuple[str, ...]
    """

    name: str
    type: str
    init_value: str
    read_in_states: Tuple[str, ...]
    written_in_states: Tuple[str, ...]
    read_in_guards: Tuple[Tuple[str, str], ...]
    written_in_effects: Tuple[Tuple[str, str], ...]
    participates_directly: bool
    participates_indirectly: bool
    abstract_actions_in_scope: Tuple[str, ...]


@dataclass(frozen=True)
class EventInfo:
    """
    Structural summary of an event declaration.

    :param qualified_name: Dotted fully qualified event name
        (e.g. ``'Root.SubA.E'``).
    :type qualified_name: str
    :param scope: ``'local'``, ``'chain'``, or ``'absolute'``.
    :type scope: str
    :param used_by: ``(from_path, to_path)`` tuples for every transition
        that references this event.
    :type used_by: Tuple[Tuple[str, str], ...]
    :param is_declared: ``True`` when the event came from an explicit
        ``event`` declaration.
    :type is_declared: bool
    :param is_used: ``True`` when at least one transition references the
        event.
    :type is_used: bool
    """

    qualified_name: str
    scope: str
    used_by: Tuple[Tuple[str, str], ...]
    is_declared: bool
    is_used: bool


@dataclass(frozen=True)
class ActionInfo:
    """Structural summary of a lifecycle action declaration."""

    signature: str
    state_path: str
    name: Optional[str]
    stage: str
    aspect: Optional[str]
    is_ref: bool
    ref_target: Optional[str]
    is_attached: bool


@dataclass(frozen=True)
class ForcedTransitionInfo:
    """Structural summary of a forced transition declaration."""

    state_path: str
    from_path: str
    to_path: str
    event: Optional[str]
    event_scope: Optional[str]
    guard: Optional[str]
    original_raw: str
    expansion_count: int


@dataclass(frozen=True)
class ModelMetrics:
    """
    Aggregate model metrics.

    :param n_states_leaf: Number of leaf states excluding pseudo states.
    :type n_states_leaf: int
    :param n_states_composite: Number of composite states.
    :type n_states_composite: int
    :param n_states_pseudo: Number of pseudo states.
    :type n_states_pseudo: int
    :param max_hierarchy_depth: Maximum depth of state nesting, counted
        from the root (depth 0 = root).
    :type max_hierarchy_depth: int
    :param n_transitions_normal: Number of transitions that did not
        originate from a ``!``-forced declaration.
    :type n_transitions_normal: int
    :param n_transitions_forced: Number of transitions expanded from
        ``!``-forced declarations.
    :type n_transitions_forced: int
    :param n_events: Number of distinct qualified events exposed by the
        inspect surface, including explicitly declared events that no
        transition uses.
    :type n_events: int
    :param n_variables: Number of variable definitions.
    :type n_variables: int
    :param var_to_leaf_ratio: ``n_variables / max(n_states_leaf, 1)``.
    :type var_to_leaf_ratio: float
    :param aspect_coverage: Mapping ``composite_path -> n_descendant_leaves``
        for composite states that declare ``>> during`` aspects.
    :type aspect_coverage: Dict[str, int]
    :param abstract_action_inventory: Function names of every abstract
        action across the model, sorted for stable output.
    :type abstract_action_inventory: Tuple[str, ...]
    """

    n_states_leaf: int
    n_states_composite: int
    n_states_pseudo: int
    max_hierarchy_depth: int
    n_transitions_normal: int
    n_transitions_forced: int
    n_events: int
    n_variables: int
    var_to_leaf_ratio: float
    aspect_coverage: Dict[str, int]
    abstract_action_inventory: Tuple[str, ...]


@dataclass(frozen=True)
class ModelInspect:
    """
    Top-level structured view of a state machine model.

    :param root_state_path: Dotted path of the root state.
    :type root_state_path: str
    :param states: All states walked from the root in pre-order.
    :type states: Tuple[StateInfo, ...]
    :param transitions: All transitions, including expanded forced
        transitions, in source order.
    :type transitions: Tuple[TransitionInfo, ...]
    :param variables: All ``def`` variables, in declaration order.
    :type variables: Tuple[VariableInfo, ...]
    :param events: All qualified events exposed by the inspect surface,
        including explicitly declared events that no transition uses,
        sorted by qualified name.
    :type events: Tuple[EventInfo, ...]
    :param metrics: Aggregate model metrics.
    :type metrics: ModelMetrics
    :param reachability_graph: Mapping state path → list of state paths
        reachable through normal transitions (BFS closure, ignoring
        guards).
    :type reachability_graph: Dict[str, Tuple[str, ...]]
    :param event_emission_map: Mapping event qualified name → list of
        source state paths that can emit it.
    :type event_emission_map: Dict[str, Tuple[str, ...]]
    :param var_dataflow: Mapping variable name → ``{'reads': [...],
        'writes': [...]}`` of state paths.
    :type var_dataflow: Dict[str, Dict[str, Tuple[str, ...]]]
    :param aspect_impact_map: Mapping composite path → descendant leaf
        paths actually reached by its aspect actions.
    :type aspect_impact_map: Dict[str, Tuple[str, ...]]
    :param action_ref_graph: Mapping named-action function path → list
        of ``ref`` edges out of it.
    :type action_ref_graph: Dict[str, Tuple[str, ...]]
    :param diagnostics: Layer 1 ``E_*`` plus design-health ``W_*`` /
        ``I_*`` diagnostics derived from the inspect payload.
    :type diagnostics: Tuple[ModelDiagnostic, ...]
    """

    root_state_path: str
    states: Tuple[StateInfo, ...]
    transitions: Tuple[TransitionInfo, ...]
    variables: Tuple[VariableInfo, ...]
    events: Tuple[EventInfo, ...]
    actions: Tuple[ActionInfo, ...]
    forced_transitions: Tuple[ForcedTransitionInfo, ...]
    metrics: ModelMetrics
    reachability_graph: Dict[str, Tuple[str, ...]]
    event_emission_map: Dict[str, Tuple[str, ...]]
    var_dataflow: Dict[str, Dict[str, Tuple[str, ...]]]
    aspect_impact_map: Dict[str, Tuple[str, ...]]
    action_ref_graph: Dict[str, Tuple[str, ...]]
    diagnostics: Tuple[ModelDiagnostic, ...] = field(default_factory=tuple)

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize this inspection report to a plain JSON-friendly dict.

        Tuples are converted to lists; frozen dataclasses to dicts.
        ``ModelDiagnostic`` instances are serialized via their public
        attributes (``code``, ``severity``, ``message``, ``span``,
        ``refs``).

        :return: A dict that round-trips through :func:`json.dumps`
            without loss.
        :rtype: Dict[str, Any]

        Example::

            >>> report.to_json()['root_state_path']
            'Root'
        """
        return _to_json_inspect(self)


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


_INIT_MARK = '[*]'
_EXIT_MARK = '[*]'


def _state_path(state: Any) -> str:
    path = getattr(state, 'path', None)
    if not path:  # pragma: no cover
        # Defensive: grammar-produced State always has a non-empty
        # ``path`` tuple. Reaching this guard means a future state
        # builder shipped a half-initialized object; keep as fail-soft
        # to avoid masking a downstream rewrite that produced ''.
        return ''
    return '.'.join(p for p in path if p is not None)


def _resolve_sibling_path(parent_state: Any, name: str) -> str:
    """Build the dotted path for a sibling-of-parent state name."""
    parent_path = _state_path(parent_state)
    return f'{parent_path}.{name}' if parent_path else name


def _transition_endpoint(parent_state: Any, marker_or_name: Any, is_source: bool) -> str:
    """Resolve ``Transition.from_state`` / ``to_state`` to a path string."""
    # ``INIT_STATE`` / ``EXIT_STATE`` are SingletonMark instances; the
    # class name is sufficient because the model layer never reuses that
    # class for anything else.
    if marker_or_name.__class__.__name__ == '_StateSingletonMark':
        return _INIT_MARK if is_source else _EXIT_MARK
    if isinstance(marker_or_name, str):
        return _resolve_sibling_path(parent_state, marker_or_name)
    return str(marker_or_name)  # pragma: no cover -- grammar produces
    # only INIT/EXIT singletons and string names; this str() fallback
    # exists for future AST extensions and never fires today.


def _expr_text(expr: Optional['Expr']) -> Optional[str]:
    if expr is None:
        return None
    try:
        return str(expr.to_ast_node())
    except Exception:  # pragma: no cover
        # Defensive: grammar-emitted Expr.to_ast_node always succeeds.
        # The try/except guards against future Expr subclasses whose
        # to_ast_node could fail; keep as fail-soft so inspection
        # never crashes the IDE / CLI.
        return None


def _effects_text(effects: List['OperationStatement']) -> Optional[str]:
    if not effects:
        return None
    parts: List[str] = []
    for stmt in effects:
        try:
            parts.append(str(stmt.to_ast_node()))
        except Exception:  # pragma: no cover
            # Defensive: see ``_expr_text`` — grammar-emitted stmts
            # always serialize.
            continue
    if not parts:  # pragma: no cover
        # Unreachable while ``except`` above is unreachable. Belt-and-
        # braces guard so the empty-parts case still returns None
        # cleanly rather than producing an empty-string label.
        return None
    return ' '.join(parts)


def _walk_expr_variables(expr: Optional['Expr']) -> List[str]:
    """Return variable names read by ``expr`` in left-to-right order."""
    if expr is None:
        return []
    seen: List[str] = []
    _walk_expr_collect(expr, seen)
    return seen


def _walk_expr_collect(expr: 'Expr', out: List[str]) -> None:
    from ..model.expr import (
        BinaryOp,
        ConditionalOp,
        UFunc,
        UnaryOp,
        Variable,
    )
    if isinstance(expr, Variable):
        out.append(expr.name)
        return
    # Constants have no children.
    if isinstance(expr, UnaryOp):
        _walk_expr_collect(expr.x, out)
        return
    if isinstance(expr, BinaryOp):
        _walk_expr_collect(expr.x, out)
        _walk_expr_collect(expr.y, out)
        return
    if isinstance(expr, ConditionalOp):
        _walk_expr_collect(expr.cond, out)
        _walk_expr_collect(expr.if_true, out)
        _walk_expr_collect(expr.if_false, out)
        return
    if isinstance(expr, UFunc):
        _walk_expr_collect(expr.x, out)
        return


def _walk_stmt_reads_writes(
        stmt: 'OperationStatement',
        reads: List[str],
        writes: List[str],
) -> None:
    """Collect variable reads/writes across a single operation statement."""
    from ..model.model import IfBlock, Operation
    if isinstance(stmt, Operation):
        writes.append(stmt.var_name)
        for v in _walk_expr_variables(stmt.expr):
            reads.append(v)
        return
    if isinstance(stmt, IfBlock):
        for branch in stmt.branches:
            if branch.condition is not None:
                for v in _walk_expr_variables(branch.condition):
                    reads.append(v)
            for inner in branch.statements:
                _walk_stmt_reads_writes(inner, reads, writes)


def _stage_function_label(stage_item: 'OnStage') -> str:
    """Choose a stable label for an action (named, abstract, or inline)."""
    if stage_item.name:
        return stage_item.name
    if stage_item.is_ref and stage_item.ref is not None and getattr(stage_item.ref, 'name', None):
        return f'ref:{stage_item.ref.name}'
    return '<inline>'


def _aspect_function_label(aspect_item: 'OnAspect') -> str:
    if aspect_item.name:
        return aspect_item.name
    if aspect_item.is_ref and aspect_item.ref is not None and getattr(aspect_item.ref, 'name', None):
        return f'ref:{aspect_item.ref.name}'
    return '<inline>'


def _is_abstract(stage_or_aspect: Any) -> bool:
    return bool(getattr(stage_or_aspect, 'is_abstract', False))


def _qualified_event_name(transition: 'Transition', parent_state: Any) -> Optional[str]:
    event = transition.event
    if event is None:
        return None
    # ``Event.path_name`` is the canonical dot-separated identifier used
    # by the runtime for matching; reuse it as the public qualified name.
    return event.path_name


def _event_scope(
        event: Any,
        parent_state: Any,
        from_state: Any,
        machine: Any,
) -> str:
    """Infer the scope label by comparing the event's owner path to context.

    The model layer does not store a scope enum on :class:`Event`, but
    the event's ``state_path`` uniquely determines which DSL operator
    declared it:

    * absolute (``/``) — owner is the root state path
    * chain (``:``) — owner is the transition's parent state path
    * local (``::``) — owner is the parent's path extended by
      ``from_state``
    """
    if event is None:  # pragma: no cover
        # Defensive: callers (``_qualified_event_name``) already guard
        # on ``transition.event is None`` and short-circuit; reaching
        # here would mean the caller forgot the guard.
        return 'absolute'
    owner_path = tuple(event.state_path)
    root_path = tuple(machine.root_state.path) if machine is not None else ()
    parent_path = tuple(parent_state.path) if parent_state is not None else ()
    if owner_path == root_path:
        return 'absolute'
    if owner_path == parent_path:
        return 'chain'
    if isinstance(from_state, str) and owner_path == parent_path + (from_state,):
        return 'local'
    # Owner is somewhere else on the chain — conservative fallback.
    # Unreachable via real DSL (events are declared in local / chain /
    # absolute scopes — never in a sibling that the transition cannot
    # reach), but kept as a non-crashing safety net.
    return 'chain'  # pragma: no cover


def _state_actions(
        state: Any,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...], Tuple[str, ...], Tuple[str, ...], bool]:
    entries = tuple(_stage_function_label(a) for a in state.on_enters)
    durings = tuple(_stage_function_label(a) for a in state.on_durings)
    exits = tuple(_stage_function_label(a) for a in state.on_exits)
    asp_before = tuple(
        _aspect_function_label(a) for a in state.on_during_aspects if a.aspect == 'before'
    )
    asp_after = tuple(
        _aspect_function_label(a) for a in state.on_during_aspects if a.aspect == 'after'
    )
    has_abstract = any(
        _is_abstract(a)
        for collection in (
            state.on_enters,
            state.on_durings,
            state.on_exits,
            state.on_during_aspects,
        )
        for a in collection
    )
    return entries, durings, exits, asp_before, asp_after, has_abstract


def _initial_targets(state: Any) -> Tuple[Dict[str, Any], ...]:
    """Collect every ``[*] -> X`` initial transition declared inside the state."""
    out: List[Dict[str, Any]] = []
    for transition in state.transitions:
        if not _is_init_source(transition.from_state):
            continue
        target_name = transition.to_state
        target_path = _resolve_sibling_path(state, target_name) if isinstance(target_name, str) else _EXIT_MARK
        guard_text = _expr_text(transition.guard)
        event = transition.event
        event_name = event.name if event is not None else None
        out.append({
            'target': target_path,
            'guard': guard_text,
            'event': event_name,
            'is_unconditional': guard_text is None and event_name is None,
        })
    return tuple(out)


def _is_init_source(from_state: Any) -> bool:
    from ..dsl.node import INIT_STATE
    return from_state is INIT_STATE


def _is_forced_transition(transition: 'Transition') -> bool:
    return bool(getattr(transition, 'is_forced', False)) or hasattr(
        transition, 'forced_origin'
    ) and getattr(transition, 'forced_origin', None) is not None


def _hierarchy_depth(states: Tuple[StateInfo, ...]) -> int:
    if not states:  # pragma: no cover
        # Defensive: ``inspect_model`` always builds at least one
        # StateInfo (the root). Empty input would mean a caller used
        # this helper outside the pipeline; keep the fail-soft 0.
        return 0
    return max(s.path.count('.') for s in states)


def _build_state_infos(machine: 'StateMachine') -> Tuple[StateInfo, ...]:
    """Pre-order walk yielding one :class:`StateInfo` per state."""
    out: List[StateInfo] = []
    for state in machine.walk_states():
        path = _state_path(state)
        name = state.name
        parent_path = _state_path(state.parent) if state.parent is not None else None
        is_leaf = state.is_leaf_state
        is_pseudo = bool(getattr(state, 'is_pseudo', False))
        is_composite = not is_leaf
        substates = tuple(
            _resolve_sibling_path(state, sub_name) for sub_name in state.substates.keys()
        )
        entries, durings, exits, asp_before, asp_after, has_abstract = _state_actions(state)
        out.append(StateInfo(
            path=path,
            name=name,
            parent_path=parent_path,
            is_leaf=is_leaf,
            is_pseudo=is_pseudo,
            is_composite=is_composite,
            substates=substates,
            initial_targets=_initial_targets(state),
            entry_actions=entries,
            during_actions=durings,
            exit_actions=exits,
            aspect_before=asp_before,
            aspect_after=asp_after,
            has_abstract_action=has_abstract,
        ))
    return tuple(out)


def _build_transition_infos(machine: 'StateMachine') -> Tuple[TransitionInfo, ...]:
    out: List[TransitionInfo] = []
    for state in machine.walk_states():
        for transition in state.transitions:
            from_path = _transition_endpoint(state, transition.from_state, is_source=True)
            to_path = _transition_endpoint(state, transition.to_state, is_source=False)
            qualified_event = _qualified_event_name(transition, state)
            scope = (
                getattr(transition, 'event_scope', None)
                or _event_scope(transition.event, state, transition.from_state, machine)
                if transition.event is not None
                else None
            )
            is_forced = _is_forced_transition(transition)
            forced_origin = getattr(transition, 'forced_origin', None) if is_forced else None
            out.append(TransitionInfo(
                from_path=from_path,
                to_path=to_path,
                event=qualified_event,
                event_scope=scope,
                guard=_expr_text(transition.guard),
                effect=_effects_text(transition.effects),
                is_forced=is_forced,
                forced_origin=forced_origin,
            ))
    return tuple(out)


def _collect_action_reads_writes(state: Any) -> Tuple[Dict[str, bool], Dict[str, bool]]:
    """Aggregate variable reads/writes across all action blocks of a state."""
    reads: Dict[str, bool] = {}
    writes: Dict[str, bool] = {}
    for collection in (
            state.on_enters,
            state.on_durings,
            state.on_exits,
            state.on_during_aspects,
    ):
        for action in collection:
            if not action.operations:
                continue
            local_reads: List[str] = []
            local_writes: List[str] = []
            for stmt in action.operations:
                _walk_stmt_reads_writes(stmt, local_reads, local_writes)
            for name in local_reads:
                reads[name] = True
            for name in local_writes:
                writes[name] = True
    return reads, writes


def _build_variable_infos(
        machine: 'StateMachine',
        states: Tuple[StateInfo, ...],
) -> Tuple[VariableInfo, ...]:
    var_reads_by_state: Dict[str, List[str]] = {name: [] for name in machine.defines}
    var_writes_by_state: Dict[str, List[str]] = {name: [] for name in machine.defines}
    var_read_guards: Dict[str, List[Tuple[str, str]]] = {name: [] for name in machine.defines}
    var_written_effects: Dict[str, List[Tuple[str, str]]] = {name: [] for name in machine.defines}
    state_lookup: Dict[str, StateInfo] = {s.path: s for s in states}

    for state in machine.walk_states():
        path = _state_path(state)
        reads, writes = _collect_action_reads_writes(state)
        for var_name in reads:
            if var_name in var_reads_by_state:
                var_reads_by_state[var_name].append(path)
        for var_name in writes:
            if var_name in var_writes_by_state:
                var_writes_by_state[var_name].append(path)

        for transition in state.transitions:
            from_path = _transition_endpoint(state, transition.from_state, is_source=True)
            to_path = _transition_endpoint(state, transition.to_state, is_source=False)
            for v in _walk_expr_variables(transition.guard):
                if v in var_read_guards:
                    var_read_guards[v].append((from_path, to_path))
            for stmt in transition.effects:
                lreads: List[str] = []
                lwrites: List[str] = []
                _walk_stmt_reads_writes(stmt, lreads, lwrites)
                for v in lreads:
                    if v in var_reads_by_state:
                        var_reads_by_state[v].append(from_path)
                for v in lwrites:
                    if v in var_written_effects:
                        var_written_effects[v].append((from_path, to_path))

    # Stable, deduped sequences for the public payload.
    def _dedupe_ordered(seq: List[str]) -> Tuple[str, ...]:
        seen = set()
        out: List[str] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return tuple(out)

    def _dedupe_pairs(seq: List[Tuple[str, str]]) -> Tuple[Tuple[str, str], ...]:
        seen = set()
        out: List[Tuple[str, str]] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return tuple(out)

    out: List[VariableInfo] = []
    for name, var_define in machine.defines.items():
        read_states = _dedupe_ordered(var_reads_by_state[name])
        written_states = _dedupe_ordered(var_writes_by_state[name])
        read_guards = _dedupe_pairs(var_read_guards[name])
        written_effects = _dedupe_pairs(var_written_effects[name])
        participates_directly = bool(read_states or read_guards)
        abstract_actions = _abstract_actions_in_scope(state_lookup, read_states, written_states)
        out.append(VariableInfo(
            name=name,
            type=var_define.type,
            init_value=_expr_text(var_define.init) or '',
            read_in_states=read_states,
            written_in_states=written_states,
            read_in_guards=read_guards,
            written_in_effects=written_effects,
            participates_directly=participates_directly,
            participates_indirectly=False,
            abstract_actions_in_scope=abstract_actions,
        ))
    return tuple(out)


def _abstract_actions_in_scope(
        state_lookup: Dict[str, StateInfo],
        read_states: Tuple[str, ...],
        written_states: Tuple[str, ...],
) -> Tuple[str, ...]:
    """Return abstract action labels visible from any touching state."""
    touched = set(read_states) | set(written_states)
    if not touched:
        # Variable touches no state — declared but unused. There is no
        # abstract-action scope to inspect from here.
        return tuple()
    out: List[str] = []
    for path in sorted(touched):
        info = state_lookup.get(path)
        if info is None:  # pragma: no cover
            # Defensive: ``touched`` paths come from VariableInfo
            # read_in_states / written_in_states, which are populated
            # only with paths that exist in state_lookup. Unreachable
            # in the current pipeline; kept as a safety net.
            continue
        if info.has_abstract_action:
            label = f'{info.path}:<abstract>'
            if label not in out:
                out.append(label)
    return tuple(out)


def _build_event_infos(machine: 'StateMachine', transitions: Tuple[TransitionInfo, ...]) -> Tuple[EventInfo, ...]:
    """Group declared and transition-used events by qualified event name."""
    event_users: Dict[str, List[Tuple[str, str]]] = {}
    event_scope: Dict[str, str] = {}
    event_declared: Dict[str, bool] = {}
    for state in machine.walk_states():
        for event in state.events.values():
            qn = event.path_name
            event_users.setdefault(qn, [])
            event_scope[qn] = _scope_from_event_origins(
                getattr(event, 'origins', None) or []
            )
            event_declared[qn] = bool(getattr(event, 'declared', False))

    for state in machine.walk_states():
        for transition in state.transitions:
            qn = _qualified_event_name(transition, state)
            if qn is None:
                continue
            from_path = _transition_endpoint(state, transition.from_state, is_source=True)
            to_path = _transition_endpoint(state, transition.to_state, is_source=False)
            event_users.setdefault(qn, []).append((from_path, to_path))
            event_scope[qn] = (
                getattr(transition, 'event_scope', None)
                or _event_scope(transition.event, state, transition.from_state, machine)
            )
            event_declared.setdefault(
                qn,
                bool(getattr(transition.event, 'declared', False)),
            )
    out: List[EventInfo] = []
    for qn in sorted(set(event_users.keys()) | set(event_declared.keys())):
        used_by = tuple(event_users.get(qn, []))
        out.append(EventInfo(
            qualified_name=qn,
            scope=event_scope.get(qn, 'absolute'),
            used_by=used_by,
            is_declared=event_declared.get(qn, False),
            is_used=bool(used_by),
        ))
    return tuple(out)


def _scope_from_event_origins(origins: List[str]) -> str:
    scopes = [origin for origin in origins if origin != 'declared']
    if 'local' in scopes:
        return 'local'
    if 'absolute' in scopes:
        return 'absolute'
    return 'chain'


def _build_action_infos(machine: 'StateMachine') -> Tuple[ActionInfo, ...]:
    out: List[ActionInfo] = []
    for state in machine.walk_states():
        path = _state_path(state)
        for collection in (
                state.on_enters,
                state.on_durings,
                state.on_exits,
                state.on_during_aspects,
        ):
            for action in collection:
                signature = _function_signature(state, path, action)
                ref_target = (
                    _function_signature(None, None, action.ref)
                    if action.is_ref and action.ref is not None
                    else None
                )
                out.append(ActionInfo(
                    signature=signature,
                    state_path=path,
                    name=action.name,
                    stage=action.stage,
                    aspect=action.aspect,
                    is_ref=action.is_ref,
                    ref_target=ref_target,
                    is_attached=True,
                ))
    return tuple(out)


def _build_forced_transition_infos(machine: 'StateMachine') -> Tuple[ForcedTransitionInfo, ...]:
    out: List[ForcedTransitionInfo] = []
    for item in getattr(machine, 'forced_transitions', ()):
        out.append(ForcedTransitionInfo(
            state_path=str(item.get('state_path', '')),
            from_path=str(item.get('from_path', '')),
            to_path=str(item.get('to_path', '')),
            event=(
                None if item.get('event') is None
                else str(item.get('event'))
            ),
            event_scope=(
                None if item.get('event_scope') is None
                else str(item.get('event_scope'))
            ),
            guard=(
                None if item.get('guard') is None
                else str(item.get('guard'))
            ),
            original_raw=str(item.get('original_raw', '')),
            expansion_count=int(item.get('expansion_count', 0)),
        ))
    return tuple(out)


def _build_metrics(
        states: Tuple[StateInfo, ...],
        transitions: Tuple[TransitionInfo, ...],
        variables: Tuple[VariableInfo, ...],
        events: Tuple[EventInfo, ...],
) -> ModelMetrics:
    n_pseudo = sum(1 for s in states if s.is_pseudo)
    n_leaf = sum(1 for s in states if s.is_leaf and not s.is_pseudo)
    n_composite = sum(1 for s in states if s.is_composite)
    n_normal = sum(1 for t in transitions if not t.is_forced)
    n_forced = sum(1 for t in transitions if t.is_forced)
    aspect_coverage: Dict[str, int] = {}
    for s in states:
        if not (s.is_composite and (s.aspect_before or s.aspect_after)):
            continue
        aspect_coverage[s.path] = sum(
            1
            for desc in states
            if desc.path != s.path
            and desc.path.startswith(s.path + '.')
            and desc.is_leaf
            and not desc.is_pseudo
        )
    abstract_inventory: List[str] = []
    for s in states:
        if s.has_abstract_action:
            abstract_inventory.append(s.path)
    return ModelMetrics(
        n_states_leaf=n_leaf,
        n_states_composite=n_composite,
        n_states_pseudo=n_pseudo,
        max_hierarchy_depth=_hierarchy_depth(states),
        n_transitions_normal=n_normal,
        n_transitions_forced=n_forced,
        n_events=len(events),
        n_variables=len(variables),
        var_to_leaf_ratio=(len(variables) / n_leaf) if n_leaf else 0.0,
        aspect_coverage=aspect_coverage,
        abstract_action_inventory=tuple(sorted(abstract_inventory)),
    )


def _build_reachability_graph(
        states: Tuple[StateInfo, ...],
        transitions: Tuple[TransitionInfo, ...],
) -> Dict[str, Tuple[str, ...]]:
    """BFS reachability over normal transitions, ignoring guards."""
    # Adjacency list keyed by state path. ``[*]`` markers are skipped.
    adjacency: Dict[str, set] = {s.path: set() for s in states}
    initial_edges: Dict[str, set] = {s.path: set() for s in states}
    for t in transitions:
        if t.from_path == _INIT_MARK or t.to_path == _EXIT_MARK:
            # Initial / exit pseudo edges feed reachability from the
            # parent composite (the parent's "active" implies traversing
            # the initial transition).
            continue
        if t.from_path not in adjacency:  # pragma: no cover
            # Defensive: transitions emitted by the model layer always
            # have from_path equal to a known state path (or the INIT
            # marker caught above). Unreachable through grammar-driven
            # input; kept as a safety net so a future synthesizer that
            # invents from_paths doesn't crash here.
            continue
        adjacency[t.from_path].add(t.to_path)

    for s in states:
        if s.is_composite and s.initial_targets:
            for it in s.initial_targets:
                target = it['target']
                if target != _EXIT_MARK:
                    initial_edges[s.path].add(target)

    out: Dict[str, Tuple[str, ...]] = {}
    for s in states:
        seen = set()
        queue = [s.path]
        while queue:
            cur = queue.pop(0)
            for nxt in sorted(adjacency.get(cur, set()) | initial_edges.get(cur, set())):
                if nxt in seen or nxt == s.path:
                    continue
                seen.add(nxt)
                queue.append(nxt)
        out[s.path] = tuple(sorted(seen))
    return out


def _build_event_emission_map(
        events: Tuple[EventInfo, ...],
) -> Dict[str, Tuple[str, ...]]:
    out: Dict[str, Tuple[str, ...]] = {}
    for e in events:
        if not e.is_used:
            continue
        froms = sorted({pair[0] for pair in e.used_by if pair[0] != _INIT_MARK})
        out[e.qualified_name] = tuple(froms)
    return out


def _build_var_dataflow(
        variables: Tuple[VariableInfo, ...],
) -> Dict[str, Dict[str, Tuple[str, ...]]]:
    out: Dict[str, Dict[str, Tuple[str, ...]]] = {}
    for v in variables:
        out[v.name] = {
            'reads': tuple(sorted(set(v.read_in_states))),
            'writes': tuple(sorted(set(v.written_in_states))),
        }
    return out


def _build_aspect_impact_map(
        states: Tuple[StateInfo, ...],
) -> Dict[str, Tuple[str, ...]]:
    out: Dict[str, Tuple[str, ...]] = {}
    for s in states:
        if not (s.is_composite and (s.aspect_before or s.aspect_after)):
            continue
        descendants = tuple(sorted(
            desc.path
            for desc in states
            if desc.path != s.path
            and desc.path.startswith(s.path + '.')
            and desc.is_leaf
            and not desc.is_pseudo
        ))
        out[s.path] = descendants
    return out


def _build_action_ref_graph(machine: 'StateMachine') -> Dict[str, Tuple[str, ...]]:
    """Capture ``ref`` edges between named actions in the model."""
    edges: Dict[str, List[str]] = {}
    for state in machine.walk_states():
        path = _state_path(state)
        for collection in (
                state.on_enters,
                state.on_durings,
                state.on_exits,
                state.on_during_aspects,
        ):
            for action in collection:
                source_label = _function_signature(state, path, action)
                if action.is_ref and action.ref is not None:
                    target_label = _function_signature(None, None, action.ref)
                    edges.setdefault(source_label, []).append(target_label)
                else:
                    # Ensure even non-ref'd functions appear in the graph
                    # so downstream "no outgoing edges" lookups work.
                    edges.setdefault(source_label, [])
    return {key: tuple(sorted(set(value))) for key, value in edges.items()}


def _function_signature(state: Any, default_path: Optional[str], action: Any) -> str:
    """Build a stable ``state_path:function`` label for a named action."""
    action_path = getattr(action, 'state_path', None)
    if action_path is not None:
        normalized = '.'.join(p for p in action_path[:-1] if p is not None) or (
            default_path or _state_path(state)
        )
    else:  # pragma: no cover
        # Defensive: grammar-emitted actions always have a non-empty
        # state_path. Reaching here means a future action synthesizer
        # produced an action without one; fall through to the
        # default_path / state.path chain so labels stay useful.
        normalized = default_path or _state_path(state) or ''
    leaf = (action.name or '<inline>') if action_path is None else (action_path[-1] or '<inline>')
    return f'{normalized}:{leaf}' if normalized else leaf


def inspect_model(machine: 'StateMachine') -> ModelInspect:
    """
    Build a structured inspection report for a state machine model.

    The report combines the structural payload, the five derived view
    graphs, and design-health diagnostics that can be computed from the
    inspect surface.

    :param machine: The state machine model to inspect.
    :type machine: pyfcstm.model.StateMachine
    :return: Structured view of the model.
    :rtype: ModelInspect

    Example::

        >>> report = inspect_model(machine)
        >>> sorted(report.reachability_graph['Root.Sub.A'])
        ['Root.Sub.B']
    """
    states = _build_state_infos(machine)
    transitions = _build_transition_infos(machine)
    variables = _build_variable_infos(machine, states)
    events = _build_event_infos(machine, transitions)
    actions = _build_action_infos(machine)
    forced_transitions = _build_forced_transition_infos(machine)
    metrics = _build_metrics(states, transitions, variables, events)
    reachability_graph = _build_reachability_graph(states, transitions)
    root_state_path = _state_path(machine.root_state)
    return ModelInspect(
        root_state_path=root_state_path,
        states=states,
        transitions=transitions,
        variables=variables,
        events=events,
        actions=actions,
        forced_transitions=forced_transitions,
        metrics=metrics,
        reachability_graph=reachability_graph,
        event_emission_map=_build_event_emission_map(events),
        var_dataflow=_build_var_dataflow(variables),
        aspect_impact_map=_build_aspect_impact_map(states),
        action_ref_graph=_build_action_ref_graph(machine),
        diagnostics=tuple(collect_design_health_warnings(
            states,
            transitions,
            variables,
            events,
            actions,
            forced_transitions,
            reachability_graph,
            root_state_path=root_state_path,
        )),
    )


def _to_json_dataclass(obj: Any) -> Any:
    if hasattr(obj, '__dataclass_fields__'):
        return {
            name: _to_json_dataclass(getattr(obj, name))
            for name in obj.__dataclass_fields__
        }
    if isinstance(obj, tuple):
        return [_to_json_dataclass(x) for x in obj]
    if isinstance(obj, list):  # pragma: no cover
        # Defensive: the current model emits ``Tuple[...]`` fields
        # exclusively, but future payloads may introduce list-typed
        # dataclass fields.
        return [_to_json_dataclass(x) for x in obj]
    if isinstance(obj, dict):  # pragma: no cover
        # Same as list: the current ModelInspect keeps every dict field
        # at the top level, but nested dict payloads should still
        # serialize predictably if introduced later.
        return {str(k): _to_json_dataclass(v) for k, v in obj.items()}
    return obj


def _to_json_inspect(report: ModelInspect) -> Dict[str, Any]:
    """Custom serializer that flattens dataclass attribute names cleanly."""
    return {
        'root_state_path': report.root_state_path,
        'states': [_to_json_dataclass(s) for s in report.states],
        'transitions': [_to_json_dataclass(t) for t in report.transitions],
        'variables': [_to_json_dataclass(v) for v in report.variables],
        'events': [_to_json_dataclass(e) for e in report.events],
        'actions': [_to_json_dataclass(a) for a in report.actions],
        'forced_transitions': [
            _to_json_dataclass(f) for f in report.forced_transitions
        ],
        'metrics': _to_json_dataclass(report.metrics),
        'reachability_graph': {k: list(v) for k, v in report.reachability_graph.items()},
        'event_emission_map': {k: list(v) for k, v in report.event_emission_map.items()},
        'var_dataflow': {
            k: {kk: list(vv) for kk, vv in inner.items()}
            for k, inner in report.var_dataflow.items()
        },
        'aspect_impact_map': {k: list(v) for k, v in report.aspect_impact_map.items()},
        'action_ref_graph': {k: list(v) for k, v in report.action_ref_graph.items()},
        'diagnostics': [_diagnostic_to_json(d) for d in report.diagnostics],
    }


def _diagnostic_to_json(d: ModelDiagnostic) -> Dict[str, Any]:
    span = None
    if d.span is not None:  # pragma: no cover
        # Current design-health diagnostics are spanless, but the JSON
        # contract already supports spans for diagnostics that can be
        # anchored precisely.
        span = {
            'line': d.span.line,
            'column': d.span.column,
            'end_line': d.span.end_line,
            'end_column': d.span.end_column,
        }
    return {
        'code': d.code,
        'severity': d.severity,
        'message': d.message,
        'span': span,
        'refs': dict(d.refs),
    }
