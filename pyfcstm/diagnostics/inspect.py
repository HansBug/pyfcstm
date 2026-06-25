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
  guard-affect flags used by ``W_UNREFERENCED_VAR``
* :class:`EventInfo` — per-event structural summary
* :class:`ModelMetrics` — aggregate counts and ratios
* :class:`ModelInspect` — top-level container including diagnostics

Examples::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
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

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .analyzers import (
    build_use_def_graph,
    collect_design_health_warnings,
    collect_expr_variables,
)
from .codes import CODE_REGISTRY, CodeFieldSpec, CodeSpec
from ..utils.validate import ModelDiagnostic, Span

if TYPE_CHECKING:  # pragma: no cover - import-time forward refs only
    from ..model.expr import Expr, Float, Integer
    from ..model.model import (
        OperationStatement,
        OnAspect,
        OnStage,
        StateMachine,
        Transition,
    )
    from ..verify.inspect_adapter import InspectRunResult


DEFAULT_DEEP_HIERARCHY_THRESHOLD = 6
DEFAULT_LARGE_COMPOSITE_THRESHOLD = 12
DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD = 2.0

# PR-D2 span contract guard: analyzer diagnostics should carry a real
# source span by default. Any future code that intentionally cannot point to
# one source object must be listed here and covered by
# test/diagnostics/test_inspect_span_contract.py.
KNOWN_SPANLESS_CODES = frozenset()

# Some structural verify algorithms intentionally reuse a legacy static
# diagnostic code so callers see one stable public code for the same model
# problem, regardless of whether it came from design-health analysis or the
# optional verify adapter.
VERIFY_SHARED_STATIC_CODES = frozenset({
    'W_UNREACHABLE_STATE',
})


_OP_PRECEDENCE = {
    'function_call': 90,
    'unary+': 80,
    'unary-': 80,
    '!': 80,
    'not': 80,
    '**': 70,
    '*': 60,
    '/': 60,
    '%': 60,
    '+': 50,
    '-': 50,
    '<<': 40,
    '>>': 40,
    '&': 35,
    '^': 30,
    '|': 25,
    '<': 20,
    '>': 20,
    '<=': 20,
    '>=': 20,
    '==': 20,
    '!=': 20,
    '&&': 15,
    'and': 15,
    '||': 10,
    'or': 10,
    '?:': 5,
}

_FLOAT_EPSILON = 1e-10


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
    span: Optional['Span'] = None


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
    :param guard: Normalized guard expression text, or ``None``.
        Pyfcstm and jsfcstm share this inspect expression format so
        downstream range resolution can treat ``guard_text`` as a stable
        disambiguation hint.
    :type guard: Optional[str]
    :param effect: Source text of the effect block, or ``None``.
    :type effect: Optional[str]
    :param effect_self_assigns: Variable names assigned to themselves
        anywhere inside the transition effect block, including nested
        ``if`` branches. Duplicate names are preserved so quick-fix
        emitters can detect ambiguous occurrences.
    :type effect_self_assigns: Tuple[str, ...]
    :param effect_self_assign_spans: Source spans for the self-assign
        statements listed in ``effect_self_assigns``. The order matches
        ``effect_self_assigns`` and uses ``None`` when a statement has no
        source span, preventing later spans from shifting to earlier names.
    :type effect_self_assign_spans: Tuple[Optional[pyfcstm.utils.validate.Span], ...]
    :param is_forced: ``True`` when the transition was expanded from a
        ``!``-prefixed forced transition.
    :type is_forced: bool
    :param forced_origin: Raw source text of the original
        ``!X -> Y`` declaration when ``is_forced`` is ``True``, otherwise
        ``None``.
    :type forced_origin: Optional[str]
    :param transition_index: Zero-based index in parent-first model
        transition order, including expanded forced transitions at their
        declaring state before ordinary transitions and descendant-state
        transitions. Downstream tooling may use this as a best-effort
        source-range disambiguation hint when spans are not available.
    :type transition_index: Optional[int]
    """

    from_path: str
    to_path: str
    event: Optional[str]
    event_scope: Optional[str]
    guard: Optional[str]
    effect: Optional[str]
    effect_self_assigns: Tuple[str, ...]
    is_forced: bool
    forced_origin: Optional[str]
    transition_index: Optional[int]
    span: Optional['Span'] = None
    effect_spans: Tuple['Span', ...] = field(default_factory=tuple)
    effect_self_assign_spans: Tuple[Optional['Span'], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VariableInfo:
    """
    Structural summary of a variable definition plus guard-affect flags.

    The ``affects_guard_directly`` and ``affects_guard_indirectly`` flags
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
    :param affects_guard_directly: ``True`` when the variable is read by
        at least one transition guard.
    :type affects_guard_directly: bool
    :param affects_guard_indirectly: ``True`` when the variable reaches
        a transition guard through the conservative use-def graph.
    :type affects_guard_indirectly: bool
    :param abstract_actions_in_scope: Function names of abstract actions
        that may access this variable. FCSTM variables are global, so any
        abstract action in the machine is conservatively visible here.
        Downstream diagnostics can use this to distinguish high-confidence
        unused variables from variables that may be touched by abstract
        behavior.
    :type abstract_actions_in_scope: Tuple[str, ...]
    :param float_literal_assignments: Source text of float literal
        assignments to this variable from lifecycle actions or transition
        effects.
    :type float_literal_assignments: Tuple[str, ...]
    """

    name: str
    type: str
    init_value: str
    read_in_states: Tuple[str, ...]
    written_in_states: Tuple[str, ...]
    read_in_guards: Tuple[Tuple[str, str], ...]
    written_in_effects: Tuple[Tuple[str, str], ...]
    affects_guard_directly: bool
    affects_guard_indirectly: bool
    abstract_actions_in_scope: Tuple[str, ...]
    float_literal_assignments: Tuple[str, ...] = field(default_factory=tuple)
    span: Optional['Span'] = None
    float_literal_assignment_spans: Tuple[Optional['Span'], ...] = field(default_factory=tuple)


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
    span: Optional['Span'] = None


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
    span: Optional['Span'] = None


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
    span: Optional['Span'] = None


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
    :param reachability_graph: Mapping from every state path to state paths
        reachable through normal transitions and composite initial edges.
        Guards are ignored; ``[*]`` entry/exit markers are not exposed.
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

        Examples::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> ast = parse_with_grammar_entry('state Root;', 'state_machine_dsl')
            >>> machine = parse_dsl_node_to_state_machine(ast)
            >>> report = inspect_model(machine)
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


def _canonical_binary_operator(op: str) -> str:
    if op == 'and':
        return '&&'
    if op == 'or':
        return '||'
    return op


def _canonical_unary_operator(op: str) -> str:
    return '!' if op == 'not' else op


def _unary_precedence_key(op: str) -> str:
    canonical = _canonical_unary_operator(op)
    return f'unary{canonical}' if canonical in {'+', '-'} else canonical


def _expr_precedence(expr: 'Expr') -> Optional[int]:
    from ..model.expr import BinaryOp, ConditionalOp, UnaryOp

    if isinstance(expr, BinaryOp):
        return _OP_PRECEDENCE.get(_canonical_binary_operator(expr.op))
    if isinstance(expr, ConditionalOp):
        return _OP_PRECEDENCE['?:']
    if isinstance(expr, UnaryOp):
        return _OP_PRECEDENCE.get(_unary_precedence_key(expr.op))
    return None


def _integer_text(expr: 'Integer') -> str:
    return str(int(expr.value))


def _float_text(expr: 'Float') -> str:
    if abs(expr.value - math.pi) < _FLOAT_EPSILON:
        return 'pi'
    if abs(expr.value - math.e) < _FLOAT_EPSILON:
        return 'E'
    if abs(expr.value - math.tau) < _FLOAT_EPSILON:
        return 'tau'
    if float(expr.value).is_integer():
        return f'{int(expr.value)}.0'
    return str(expr.value)


def _expr_text(expr: Optional['Expr']) -> Optional[str]:
    if expr is None:
        return None
    from ..model.expr import (
        BinaryOp,
        Boolean,
        ConditionalOp,
        Float,
        Integer,
        UFunc,
        UnaryOp,
        Variable,
    )

    if isinstance(expr, Integer):
        return _integer_text(expr)
    if isinstance(expr, Float):
        return _float_text(expr)
    if isinstance(expr, Boolean):
        return 'true' if expr.value else 'false'
    if isinstance(expr, Variable):
        return expr.name
    if isinstance(expr, UFunc):
        argument = _expr_text(expr.x)
        return None if argument is None else f'{expr.func}({argument})'
    if isinstance(expr, UnaryOp):
        op = _canonical_unary_operator(expr.op)
        my_precedence = _OP_PRECEDENCE[_unary_precedence_key(expr.op)]
        value = _expr_text(expr.x)
        if value is None:
            return None
        value_precedence = _expr_precedence(expr.x)
        if value_precedence is not None and value_precedence <= my_precedence:
            value = f'({value})'
        return f'{op}{value}'
    if isinstance(expr, BinaryOp):
        op = _canonical_binary_operator(expr.op)
        my_precedence = _OP_PRECEDENCE[op]
        left = _expr_text(expr.x)
        right = _expr_text(expr.y)
        if left is None or right is None:
            return None
        left_precedence = _expr_precedence(expr.x)
        if left_precedence is not None and left_precedence < my_precedence:
            left = f'({left})'
        right_precedence = _expr_precedence(expr.y)
        if right_precedence is not None and right_precedence <= my_precedence:
            right = f'({right})'
        return f'{left} {op} {right}'
    if isinstance(expr, ConditionalOp):
        my_precedence = _OP_PRECEDENCE['?:']
        condition = _expr_text(expr.cond)
        when_true = _expr_text(expr.if_true)
        when_false = _expr_text(expr.if_false)
        if condition is None or when_true is None or when_false is None:
            return None
        true_precedence = _expr_precedence(expr.if_true)
        if true_precedence is not None and true_precedence <= my_precedence:
            when_true = f'({when_true})'
        false_precedence = _expr_precedence(expr.if_false)
        if false_precedence is not None and false_precedence <= my_precedence:
            when_false = f'({when_false})'
        return f'({condition}) ? {when_true} : {when_false}'

    try:
        return str(expr.to_ast_node())
    except (AttributeError, TypeError, ValueError):  # pragma: no cover
        # AttributeError: non-model Expr-like object; TypeError/ValueError:
        # future expression implementations with invalid AST conversion.
        return None


def _effects_text(effects: List['OperationStatement']) -> Optional[str]:
    if not effects:
        return None
    parts: List[str] = []
    for stmt in effects:
        try:
            parts.append(str(stmt.to_ast_node()))
        except (AttributeError, TypeError, ValueError):  # pragma: no cover
            # AttributeError: non-model statement-like object; TypeError/ValueError:
            # future statement implementations with invalid AST conversion.
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
    return list(collect_expr_variables(expr))


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


def _effect_self_assigns(effects: List['OperationStatement']) -> Tuple[str, ...]:
    out: List[str] = []
    for stmt in effects:
        _walk_stmt_self_assigns(stmt, out)
    return tuple(out)


def _effect_self_assign_spans(effects: List['OperationStatement']) -> Tuple[Optional['Span'], ...]:
    out: List[Optional['Span']] = []
    for stmt in effects:
        _walk_stmt_self_assign_spans(stmt, out)
    return tuple(out)


def _walk_stmt_self_assigns(stmt: 'OperationStatement', out: List[str]) -> None:
    from ..model.expr import Variable
    from ..model.model import IfBlock, Operation
    if isinstance(stmt, Operation):
        if isinstance(stmt.expr, Variable) and stmt.expr.name == stmt.var_name:
            out.append(stmt.var_name)
        return
    if isinstance(stmt, IfBlock):
        for branch in stmt.branches:
            for inner in branch.statements:
                _walk_stmt_self_assigns(inner, out)


def _walk_stmt_self_assign_spans(stmt: 'OperationStatement', out: List[Optional['Span']]) -> None:
    from ..model.expr import Variable
    from ..model.model import IfBlock, Operation
    if isinstance(stmt, Operation):
        if isinstance(stmt.expr, Variable) and stmt.expr.name == stmt.var_name:
            out.append(getattr(stmt, '_span', None))
        return
    if isinstance(stmt, IfBlock):
        for branch in stmt.branches:
            for inner in branch.statements:
                _walk_stmt_self_assign_spans(inner, out)


def _walk_stmt_float_literal_assignments(
        stmt: 'OperationStatement',
        out: Dict[str, List[str]],
        spans: Optional[Dict[str, List[Optional[Span]]]] = None,
) -> None:
    from ..model.expr import Float
    from ..model.model import IfBlock, Operation
    if isinstance(stmt, Operation):
        if isinstance(stmt.expr, Float):
            out.setdefault(stmt.var_name, []).append(_expr_text(stmt.expr) or '')
            if spans is not None:
                spans.setdefault(stmt.var_name, []).append(getattr(stmt, '_span', None))
        return
    if isinstance(stmt, IfBlock):
        for branch in stmt.branches:
            for inner in branch.statements:
                _walk_stmt_float_literal_assignments(inner, out, spans)


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
            span=getattr(state, '_span', None),
        ))
    return tuple(out)


def _build_transition_infos(machine: 'StateMachine') -> Tuple[TransitionInfo, ...]:
    out: List[TransitionInfo] = []
    transition_index = 0
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
                effect_self_assigns=_effect_self_assigns(transition.effects),
                is_forced=is_forced,
                forced_origin=forced_origin,
                transition_index=transition_index,
                span=getattr(transition, '_span', None),
                effect_spans=tuple(
                    span
                    for span in (getattr(effect, '_span', None) for effect in transition.effects)
                    if span is not None
                ),
                effect_self_assign_spans=_effect_self_assign_spans(transition.effects),
            ))
            transition_index += 1
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
    var_float_literal_assignments: Dict[str, List[str]] = {
        name: [] for name in machine.defines
    }
    var_float_literal_assignment_spans: Dict[str, List[Optional[Span]]] = {
        name: [] for name in machine.defines
    }
    state_lookup: Dict[str, StateInfo] = {s.path: s for s in states}

    for state in machine.walk_states():
        path = _state_path(state)
        reads, writes = _collect_action_reads_writes(state)
        float_assigns: Dict[str, List[str]] = {}
        float_assign_spans: Dict[str, List[Optional[Span]]] = {}
        for collection in (
                state.on_enters,
                state.on_durings,
                state.on_exits,
                state.on_during_aspects,
        ):
            for action in collection:
                for stmt in action.operations:
                    _walk_stmt_float_literal_assignments(stmt, float_assigns, float_assign_spans)
        for var_name in reads:
            if var_name in var_reads_by_state:
                var_reads_by_state[var_name].append(path)
        for var_name in writes:
            if var_name in var_writes_by_state:
                var_writes_by_state[var_name].append(path)
        for var_name, assignments in float_assigns.items():
            if var_name in var_float_literal_assignments:
                var_float_literal_assignments[var_name].extend(assignments)
                var_float_literal_assignment_spans[var_name].extend(float_assign_spans.get(var_name, []))

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
                lfloat_assigns: Dict[str, List[str]] = {}
                lfloat_assign_spans: Dict[str, List[Optional[Span]]] = {}
                _walk_stmt_float_literal_assignments(stmt, lfloat_assigns, lfloat_assign_spans)
                for v in lreads:
                    if v in var_reads_by_state:
                        var_reads_by_state[v].append(from_path)
                for v in lwrites:
                    if v in var_written_effects:
                        var_written_effects[v].append((from_path, to_path))
                for v, assignments in lfloat_assigns.items():
                    if v in var_float_literal_assignments:
                        var_float_literal_assignments[v].extend(assignments)
                        var_float_literal_assignment_spans[v].extend(lfloat_assign_spans.get(v, []))

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

    def _dedupe_float_assignment_pairs(
            exprs: List[str],
            spans: List[Optional[Span]],
    ) -> Tuple[Tuple[str, ...], Tuple[Optional[Span], ...]]:
        seen = set()
        out_exprs: List[str] = []
        out_spans: List[Optional[Span]] = []
        for index, expr in enumerate(exprs):
            if expr in seen:
                continue
            seen.add(expr)
            out_exprs.append(expr)
            out_spans.append(spans[index] if index < len(spans) else None)
        return tuple(out_exprs), tuple(out_spans)

    use_def_graph = build_use_def_graph(machine)
    direct_guard_vars = {
        name for name, entries in var_read_guards.items()
        if entries
    }
    indirect_guard_vars = set(use_def_graph.affecting_variables(direct_guard_vars))

    out: List[VariableInfo] = []
    for name, var_define in machine.defines.items():
        read_states = _dedupe_ordered(var_reads_by_state[name])
        written_states = _dedupe_ordered(var_writes_by_state[name])
        read_guards = _dedupe_pairs(var_read_guards[name])
        written_effects = _dedupe_pairs(var_written_effects[name])
        abstract_actions = _abstract_actions_in_scope(state_lookup)
        float_assignments, float_assignment_spans = _dedupe_float_assignment_pairs(
            var_float_literal_assignments[name],
            var_float_literal_assignment_spans[name],
        )
        out.append(VariableInfo(
            name=name,
            type=var_define.type,
            init_value=_expr_text(var_define.init) or '',
            read_in_states=read_states,
            written_in_states=written_states,
            read_in_guards=read_guards,
            written_in_effects=written_effects,
            affects_guard_directly=name in direct_guard_vars,
            affects_guard_indirectly=(
                name not in direct_guard_vars and name in indirect_guard_vars
            ),
            abstract_actions_in_scope=abstract_actions,
            float_literal_assignments=float_assignments,
            span=getattr(var_define, '_span', None),
            float_literal_assignment_spans=float_assignment_spans,
        ))
    return tuple(out)


def _abstract_actions_in_scope(
        state_lookup: Dict[str, StateInfo],
) -> Tuple[str, ...]:
    """Return abstract action labels that can see global variables."""
    return tuple(
        f'{info.path}:<abstract>'
        for info in sorted(state_lookup.values(), key=lambda item: item.path)
        if info.has_abstract_action
    )


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
        event_obj = _find_event_by_qualified_name(machine, qn)
        out.append(EventInfo(
            qualified_name=qn,
            scope=event_scope.get(qn, 'absolute'),
            used_by=used_by,
            is_declared=event_declared.get(qn, False),
            is_used=bool(used_by),
            span=getattr(event_obj, '_span', None) if event_obj is not None else None,
        ))
    return tuple(out)


def _find_event_by_qualified_name(machine: 'StateMachine', qualified_name: str):
    for state in machine.walk_states():
        for event in state.events.values():
            if event.path_name == qualified_name:
                return event
    return None


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
                    span=getattr(action, '_span', None),
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
            span=item.get('span'),
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
        var_to_leaf_ratio=len(variables) / max(n_leaf, 1),
        aspect_coverage=aspect_coverage,
        abstract_action_inventory=tuple(sorted(abstract_inventory)),
    )


def _build_reachability_graph(
        states: Tuple[StateInfo, ...],
        transitions: Tuple[TransitionInfo, ...],
) -> Dict[str, Tuple[str, ...]]:
    """Return the default inspect reachability graph.

    The inspect graph is a guard-agnostic breadth-first closure over normal
    transition endpoints plus composite ``[*]`` initial edges. It is a stable
    inspect/jsfcstm contract and therefore intentionally independent from the
    optional verify topology projection that only runs when callers pass
    ``enable_verify=True`` to :func:`inspect_model`.

    :param states: Inspect state records, one per state path.
    :type states: Tuple[StateInfo, ...]
    :param transitions: Inspect transition records in model order.
    :type transitions: Tuple[TransitionInfo, ...]
    :return: Mapping from every state path to reachable state paths.
    :rtype: Dict[str, Tuple[str, ...]]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, 'state_machine_dsl')
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> states = _build_state_infos(machine)
        >>> transitions = _build_transition_infos(machine)
        >>> _build_reachability_graph(states, transitions)['Root']
        ('Root.A', 'Root.B')
        >>> _build_reachability_graph(states, transitions)['Root.A']
        ('Root.B',)
    """
    adjacency: Dict[str, set] = {state.path: set() for state in states}
    initial_edges: Dict[str, set] = {state.path: set() for state in states}
    for transition in transitions:
        if (
                transition.from_path == _INIT_MARK
                or transition.to_path == _EXIT_MARK
        ):
            continue
        if transition.from_path not in adjacency:  # pragma: no cover
            # Model-built transitions always point at a known source path. The
            # guard keeps hand-built test doubles from crashing this helper.
            continue
        adjacency[transition.from_path].add(transition.to_path)

    for state in states:
        if not (state.is_composite and state.initial_targets):
            continue
        for initial_target in state.initial_targets:
            target = initial_target['target']
            if target != _EXIT_MARK:
                initial_edges[state.path].add(target)

    graph: Dict[str, Tuple[str, ...]] = {}
    for state in states:
        seen = set()
        queue = [state.path]
        while queue:
            current = queue.pop(0)
            next_paths = adjacency.get(current, set()) | initial_edges.get(
                current,
                set(),
            )
            for next_path in sorted(next_paths):
                if next_path in seen or next_path == state.path:
                    continue
                seen.add(next_path)
                queue.append(next_path)
        graph[state.path] = tuple(sorted(seen))
    return graph


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


def _run_verify_inspect_algorithms(machine: 'StateMachine', **kwargs):
    """Run the verify inspect adapter lazily.

    Keeping this import behind the ``enable_verify`` branch preserves the
    default inspect path for users that only need structural diagnostics.

    :param machine: State machine to verify.
    :type machine: pyfcstm.model.StateMachine
    :param kwargs: Inspect-adapter policy arguments.
    :type kwargs: object
    :return: Adapter results in registry order.
    :rtype: Tuple[pyfcstm.verify.inspect_adapter.InspectRunResult, ...]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> ast = parse_with_grammar_entry("state Root;", "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> bool(_run_verify_inspect_algorithms(machine))
        True
    """
    from ..verify.inspect_adapter import run_inspect_algorithms

    return run_inspect_algorithms(machine, **kwargs)


def _transition_summary(payload: Mapping[str, Any]) -> str:
    """Render a raw verify transition payload as a compact label.

    :param payload: Raw transition payload produced by
        :mod:`pyfcstm.verify.encoding`.
    :type payload: Mapping[str, Any]
    :return: ``parent:from->to`` transition label.
    :rtype: str

    Examples::

        >>> _transition_summary({
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ... })
        'Root:A->B'
    """
    return '{parent}:{from_state}->{to_state}'.format(**payload)


def _verify_transition_payload(payload: Any) -> Optional[Dict[str, Any]]:
    """Return a validated raw verify transition payload.

    Verify algorithms return diagnostics-layer-free dictionaries. The
    inspect conversion layer must fail closed when a raw payload is malformed,
    because the public ``ModelDiagnostic.refs`` schema can only validate the
    outer ``dict`` type for transition refs.

    :param payload: Raw transition payload to validate.
    :type payload: Any
    :return: A defensive copy when the payload is shaped like
        ``pyfcstm.verify.encoding`` transition data, otherwise ``None``.
    :rtype: Optional[Dict[str, Any]]

    Examples::

        >>> _verify_transition_payload({
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': 'x > 0',
        ...     'is_forced': False,
        ... })['from_state']
        'A'
        >>> _verify_transition_payload({'parent': 'Root'}) is None
        True
    """
    if not isinstance(payload, Mapping):
        return None
    parent = payload.get('parent')
    from_state = payload.get('from_state')
    to_state = payload.get('to_state')
    event = payload.get('event')
    guard = payload.get('guard')
    is_forced = payload.get('is_forced')
    if not all(isinstance(item, str) for item in (parent, from_state, to_state)):
        return None
    if event is not None and not isinstance(event, str):
        return None
    if guard is not None and not isinstance(guard, str):
        return None
    if not isinstance(is_forced, bool):
        return None
    return {
        'parent': parent,
        'from_state': from_state,
        'to_state': to_state,
        'event': event,
        'guard': guard,
        'is_forced': is_forced,
    }


def _verify_transition_summaries(payloads: Any) -> Optional[List[str]]:
    """Return summaries for a sequence of raw verify transition payloads.

    The conversion fails closed: one malformed item invalidates the entire
    sequence so the diagnostic cannot present partial evidence as complete.

    :param payloads: Raw transition payload sequence.
    :type payloads: Any
    :return: Transition summaries, or ``None`` when the sequence is malformed.
    :rtype: Optional[List[str]]

    Examples::

        >>> _verify_transition_summaries(({
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': None,
        ...     'is_forced': False,
        ... },))
        ['Root:A->B']
        >>> _verify_transition_summaries(({'parent': 'Root'},)) is None
        True
    """
    if not isinstance(payloads, (list, tuple)):
        return None
    summaries: List[str] = []
    for raw_item in payloads:
        item = _verify_transition_payload(raw_item)
        if item is None:
            return None
        summaries.append(_transition_summary(item))
    return summaries


def _state_span_by_path(states: Sequence[StateInfo], state_path: Optional[str]) -> Optional[Span]:
    """Return the source span for a state path.

    :param states: Inspect state payloads.
    :type states: Sequence[StateInfo]
    :param state_path: Dotted state path to locate.
    :type state_path: Optional[str]
    :return: Matching state span, or ``None`` when the path is absent.
    :rtype: Optional[Span]

    Examples::

        >>> state = StateInfo(
        ...     path='Root',
        ...     name='Root',
        ...     parent_path=None,
        ...     is_leaf=True,
        ...     is_pseudo=False,
        ...     is_composite=False,
        ...     substates=(),
        ...     initial_targets=(),
        ...     entry_actions=(),
        ...     during_actions=(),
        ...     exit_actions=(),
        ...     aspect_before=(),
        ...     aspect_after=(),
        ...     has_abstract_action=False,
        ...     span=Span(line=1, column=1),
        ... )
        >>> _state_span_by_path((state,), 'Root').line
        1
    """
    if state_path is None:
        return None
    for state in states:
        if state.path == state_path:
            return state.span
    return None


def _event_span_by_name(events: Sequence[EventInfo], event_name: Optional[str]) -> Optional[Span]:
    """Return the source span for a qualified event name.

    :param events: Inspect event payloads.
    :type events: Sequence[EventInfo]
    :param event_name: Qualified event name to locate.
    :type event_name: Optional[str]
    :return: Matching event declaration span, or ``None``.
    :rtype: Optional[Span]

    Examples::

        >>> event = EventInfo(
        ...     qualified_name='Root.Tick',
        ...     scope='chain',
        ...     used_by=(),
        ...     is_declared=True,
        ...     is_used=False,
        ...     span=Span(line=2, column=5),
        ... )
        >>> _event_span_by_name((event,), 'Root.Tick').column
        5
    """
    if event_name is None:
        return None
    for event in events:
        if event.qualified_name == event_name:
            return event.span
    return None


def _transition_matches_payload(info: TransitionInfo, payload: Mapping[str, Any]) -> bool:
    """Return whether inspect transition data matches raw verify payload.

    :param info: Inspect transition payload.
    :type info: TransitionInfo
    :param payload: Raw verify transition payload.
    :type payload: Mapping[str, Any]
    :return: ``True`` when endpoints, event, guard, and forced flag match.
    :rtype: bool

    Examples::

        >>> info = TransitionInfo(
        ...     from_path='Root.A',
        ...     to_path='Root.B',
        ...     event=None,
        ...     event_scope=None,
        ...     guard='x > 0',
        ...     effect=None,
        ...     effect_self_assigns=(),
        ...     is_forced=False,
        ...     forced_origin=None,
        ...     transition_index=0,
        ... )
        >>> _transition_matches_payload(info, {
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': 'x > 0',
        ...     'is_forced': False,
        ... })
        True
    """
    transition_payload = _verify_transition_payload(payload)
    if transition_payload is None:
        return False
    parent = transition_payload['parent']
    from_state = transition_payload['from_state']
    to_state = transition_payload['to_state']
    from_path = '[*]' if from_state == '[*]' else (
        f'{parent}.{from_state}' if parent else from_state
    )
    to_path = '[*]' if to_state == '[*]' else (
        f'{parent}.{to_state}' if parent else to_state
    )
    return (
        info.from_path == from_path
        and info.to_path == to_path
        and info.event == transition_payload['event']
        and info.guard == transition_payload['guard']
        and info.is_forced == transition_payload['is_forced']
    )


def _transition_span_by_payload(
        transitions: Sequence[TransitionInfo],
        payload: Optional[Mapping[str, Any]],
) -> Optional[Span]:
    """Return the transition span for a raw verify transition payload.

    :param transitions: Inspect transition payloads.
    :type transitions: Sequence[TransitionInfo]
    :param payload: Raw verify transition payload.
    :type payload: Optional[Mapping[str, Any]]
    :return: Matching transition source span, or ``None``.
    :rtype: Optional[Span]

    Examples::

        >>> transition = TransitionInfo(
        ...     from_path='Root.A',
        ...     to_path='Root.B',
        ...     event=None,
        ...     event_scope=None,
        ...     guard=None,
        ...     effect=None,
        ...     effect_self_assigns=(),
        ...     is_forced=False,
        ...     forced_origin=None,
        ...     transition_index=0,
        ...     span=Span(line=3, column=5),
        ... )
        >>> _transition_span_by_payload((transition,), {
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': None,
        ...     'is_forced': False,
        ... }).line
        3
    """
    if payload is None:
        return None
    for transition in transitions:
        if _transition_matches_payload(transition, payload):
            return transition.span
    return None


def _effect_span_by_payload(
        transitions: Sequence[TransitionInfo],
        payload: Optional[Mapping[str, Any]],
) -> Optional[Span]:
    """Return the most specific effect span for a raw transition payload.

    :param transitions: Inspect transition payloads.
    :type transitions: Sequence[TransitionInfo]
    :param payload: Raw verify transition payload.
    :type payload: Optional[Mapping[str, Any]]
    :return: First effect span when present, otherwise the transition span.
    :rtype: Optional[Span]

    Examples::

        >>> span = Span(line=4, column=10)
        >>> transition = TransitionInfo(
        ...     from_path='Root.A',
        ...     to_path='Root.B',
        ...     event=None,
        ...     event_scope=None,
        ...     guard=None,
        ...     effect='x = x + 0',
        ...     effect_self_assigns=(),
        ...     is_forced=False,
        ...     forced_origin=None,
        ...     transition_index=0,
        ...     effect_spans=(span,),
        ... )
        >>> _effect_span_by_payload((transition,), {
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': None,
        ...     'is_forced': False,
        ... }).column
        10
    """
    if payload is None:
        return None
    for transition in transitions:
        if _transition_matches_payload(transition, payload):
            if transition.effect_spans:
                return transition.effect_spans[0]
            return transition.span
    return None


def _action_span_by_state_and_condition(
        actions: Sequence[ActionInfo],
        state_path: Optional[str],
        condition_source: Optional[str],
) -> Optional[Span]:
    """Return the lifecycle action span associated with a verify condition.

    :param actions: Inspect action payloads.
    :type actions: Sequence[ActionInfo]
    :param state_path: State path reported by the raw verify diagnostic.
    :type state_path: Optional[str]
    :param condition_source: Condition source label, such as
        ``"during:0"``.
    :type condition_source: Optional[str]
    :return: Matching action span, or ``None``.
    :rtype: Optional[Span]

    Examples::

        >>> action = ActionInfo(
        ...     signature='Root.A:<inline>',
        ...     state_path='Root.A',
        ...     name=None,
        ...     stage='during',
        ...     aspect=None,
        ...     is_ref=False,
        ...     ref_target=None,
        ...     is_attached=True,
        ...     span=Span(line=5, column=9),
        ... )
        >>> _action_span_by_state_and_condition(
        ...     (action,),
        ...     'Root.A',
        ...     'during:0',
        ... ).line
        5
    """
    if state_path is None:
        return None
    if condition_source and ':' in condition_source:
        stage = condition_source.split(':', 1)[0]
        for action in actions:
            if action.state_path == state_path and action.stage == stage:
                return action.span
    for action in actions:
        if action.state_path == state_path and action.stage == 'during':
            return action.span
    return None


def _verify_smt_refs(raw: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Build inspect diagnostic refs from one raw SMT-local finding.

    Raw verify algorithms deliberately return dictionaries so they do not
    depend on the diagnostics package. This helper translates the shared raw
    fields into the refs vocabulary declared in ``codes.yaml``.

    :param raw: Raw diagnostic dictionary with ``code``, ``algorithm_name``,
        and ``data`` keys.
    :type raw: Mapping[str, Any]
    :return: Refs payload candidate, or ``None`` when ``raw`` is not shaped
        like a verify diagnostic.
    :rtype: Optional[Dict[str, Any]]

    Examples::

        >>> raw = {
        ...     'code': 'W_DEAD_GUARD',
        ...     'algorithm_name': 'dead_guard',
        ...     'data': {
        ...         'transition': {
        ...             'parent': 'Root',
        ...             'from_state': 'A',
        ...             'to_state': 'B',
        ...             'event': None,
        ...             'guard': 'x > 0',
        ...             'is_forced': False,
        ...         },
        ...         'verification_scope': 'smt_local',
        ...     },
        ... }
        >>> refs = _verify_smt_refs(raw)
        >>> refs['transition_summary']
        'Root:A->B'
    """
    code = raw.get('code')
    data = raw.get('data')
    if not isinstance(code, str) or not isinstance(data, Mapping):
        return None
    refs: Dict[str, Any] = {
        'algorithm_name': raw.get('algorithm_name'),
        'verification_scope': data.get('verification_scope'),
    }

    transition_dict = _verify_transition_payload(data.get('transition'))
    if transition_dict is not None:
        refs['transition'] = transition_dict
        refs['transition_summary'] = _transition_summary(transition_dict)

    if code == 'W_FORCED_GUARD_UNSAT':
        refs['scope'] = data.get('scope')
    elif code == 'W_TRANSITION_SHADOWED':
        shadowed_by = data.get('shadowed_by') or ()
        shadowed_by_summaries = _verify_transition_summaries(shadowed_by)
        if shadowed_by_summaries is None:
            return None
        refs.update({
            'source_state_path': data.get('source'),
            'reason': data.get('reason'),
            'shadowed_by_count': len(shadowed_by_summaries),
            'shadowed_by': shadowed_by_summaries,
        })
    elif code == 'I_ENTER_DURING_CONTRADICT':
        refs.update({
            'state_path': data.get('state'),
            'condition': data.get('condition'),
            'condition_source': data.get('condition_source'),
            'branch_taken': data.get('branch_taken'),
        })
    elif code == 'W_COMPOSITE_INIT_INCOMPLETE':
        init_transitions = data.get('init_transitions') or ()
        init_transition_summaries = _verify_transition_summaries(init_transitions)
        if init_transition_summaries is None:
            return None
        refs.update({
            'composite_path': data.get('state'),
            'init_transition_count': len(init_transition_summaries),
            'init_transitions': init_transition_summaries,
            'witness': data.get('witness'),
        })
    return refs


def _verify_smt_span(
        code: str,
        raw: Mapping[str, Any],
        states: Sequence[StateInfo],
        transitions: Sequence[TransitionInfo],
        actions: Sequence[ActionInfo],
) -> Optional[Span]:
    """Choose a source span for an SMT-local verify diagnostic.

    The span follows the semantic object declared for each verify code:
    guard/transition findings point at the transition, effect findings prefer
    the effect statement, lifecycle findings point at the relevant action, and
    composite-init findings point at the composite state.

    :param code: Diagnostic code.
    :type code: str
    :param raw: Raw verify diagnostic dictionary.
    :type raw: Mapping[str, Any]
    :param states: Inspect state payloads.
    :type states: Sequence[StateInfo]
    :param transitions: Inspect transition payloads.
    :type transitions: Sequence[TransitionInfo]
    :param actions: Inspect action payloads.
    :type actions: Sequence[ActionInfo]
    :return: Best-effort source span, or ``None`` when no source object can
        be matched.
    :rtype: Optional[Span]

    Examples::

        >>> transition = TransitionInfo(
        ...     from_path='Root.A',
        ...     to_path='Root.B',
        ...     event=None,
        ...     event_scope=None,
        ...     guard='x > 0',
        ...     effect=None,
        ...     effect_self_assigns=(),
        ...     is_forced=False,
        ...     forced_origin=None,
        ...     transition_index=0,
        ...     span=Span(line=3, column=5),
        ... )
        >>> raw = {'data': {'transition': {
        ...     'parent': 'Root',
        ...     'from_state': 'A',
        ...     'to_state': 'B',
        ...     'event': None,
        ...     'guard': 'x > 0',
        ...     'is_forced': False,
        ... }}}
        >>> _verify_smt_span('W_DEAD_GUARD', raw, (), (transition,), ()).line
        3
    """
    data = raw.get('data')
    if not isinstance(data, Mapping):
        return None
    transition = data.get('transition')
    if code in {
            'W_DEAD_GUARD',
            'W_GUARD_TAUTOLOGY',
            'W_FORCED_GUARD_UNSAT',
            'W_TRANSITION_SHADOWED',
    }:
        return _transition_span_by_payload(transitions, transition)
    if code in {'W_EFFECT_SMT_NO_OP', 'I_EFFECT_GUARD_CONTRADICT'}:
        return _effect_span_by_payload(transitions, transition)
    if code == 'I_ENTER_DURING_CONTRADICT':
        return _action_span_by_state_and_condition(
            actions,
            data.get('state'),
            data.get('condition_source'),
        )
    if code == 'W_COMPOSITE_INIT_INCOMPLETE':
        return _state_span_by_path(states, data.get('state'))
    return None


def _structural_verify_diagnostics(
        result: 'InspectRunResult',
        states: Sequence[StateInfo],
        events: Sequence[EventInfo],
) -> List[ModelDiagnostic]:
    """Convert structural verify payloads into model diagnostics.

    Structural algorithms return graph-oriented payloads rather than raw
    diagnostic dictionaries. This helper maps the known structural adapter
    results onto the verify-pipeline codes declared in ``codes.yaml``.

    :param result: One normalized inspect-adapter result.
    :type result: pyfcstm.verify.inspect_adapter.InspectRunResult
    :param states: Inspect state payloads for source-span lookup.
    :type states: Sequence[StateInfo]
    :param events: Inspect event payloads for event-span and consumer lookup.
    :type events: Sequence[EventInfo]
    :return: Diagnostics converted from ``result``.
    :rtype: List[ModelDiagnostic]

    Examples::

        >>> from pyfcstm.verify.inspect_adapter import InspectRunResult
        >>> state = StateInfo(
        ...     path='Root.A',
        ...     name='A',
        ...     parent_path='Root',
        ...     is_leaf=True,
        ...     is_pseudo=False,
        ...     is_composite=False,
        ...     substates=(),
        ...     initial_targets=(),
        ...     entry_actions=(),
        ...     during_actions=(),
        ...     exit_actions=(),
        ...     aspect_before=(),
        ...     aspect_after=(),
        ...     has_abstract_action=False,
        ...     span=Span(line=2, column=5),
        ... )
        >>> result = InspectRunResult(
        ...     algorithm_name='strongly_connected_components',
        ...     complexity_tier='structural',
        ...     smt_logic=None,
        ...     verification_scope='topological_only',
        ...     diagnostic_codes=('I_NONTRIVIAL_SCC',),
        ...     result_kind='sat',
        ...     diagnostics=(),
        ...     reason=None,
        ...     raw_result=(('Root.A',),),
        ... )
        >>> _structural_verify_diagnostics(result, (state,), ())[0].code
        'I_NONTRIVIAL_SCC'
    """
    diagnostics: List[ModelDiagnostic] = []
    if result.algorithm_name == 'strongly_connected_components':
        for component in result.raw_result or ():
            scc = list(component)
            if not scc:
                continue
            refs = {
                'algorithm_name': result.algorithm_name,
                'verification_scope': result.verification_scope,
                'representative_state_path': scc[0],
                'scc': scc,
            }
            diagnostic = _make_verify_diagnostic(
                'I_NONTRIVIAL_SCC',
                refs,
                _state_span_by_path(states, scc[0]),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    elif result.algorithm_name == 'unreachable_states':
        for state_path in result.raw_result or ():
            refs = {'state_path': state_path}
            diagnostic = _make_verify_diagnostic(
                'W_UNREACHABLE_STATE',
                refs,
                _state_span_by_path(states, state_path),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    elif result.algorithm_name == 'topological_finite':
        counterexamples = getattr(result.raw_result, 'counterexamples', ())
        for kind, payload in counterexamples:
            representative = payload[0] if isinstance(payload, tuple) else payload
            scc = list(payload) if isinstance(payload, tuple) else [payload]
            refs = {
                'algorithm_name': result.algorithm_name,
                'verification_scope': result.verification_scope,
                'representative_state_path': representative,
                'counterexample_kind': kind,
                'scc': scc,
            }
            diagnostic = _make_verify_diagnostic(
                'W_TOPOLOGICAL_NOEXIT',
                refs,
                _state_span_by_path(states, representative),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    elif result.algorithm_name == 'topological_inevitable_terminator':
        path = list(getattr(result.raw_result, 'counterexample_path', ()) or ())
        if path:
            refs = {
                'algorithm_name': result.algorithm_name,
                'verification_scope': result.verification_scope,
                'representative_state_path': path[0],
                'counterexample_path': path,
            }
            diagnostic = _make_verify_diagnostic(
                'I_TOPOLOGICAL_NON_TERMINATING',
                refs,
                _state_span_by_path(states, path[0]),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    elif result.algorithm_name == 'event_emission_to_consumer_reachable':
        for event_name in result.raw_result or ():
            refs = {
                'algorithm_name': result.algorithm_name,
                'verification_scope': result.verification_scope,
                'event_name': event_name,
                'consumer_count': _event_consumer_count(events, event_name),
            }
            diagnostic = _make_verify_diagnostic(
                'W_EVENT_UNREACHABLE_EMIT',
                refs,
                _event_span_by_name(events, event_name),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    return diagnostics


def _event_consumer_count(events: Sequence[EventInfo], event_name: str) -> int:
    """Return how many inspect transitions consume an event.

    :param events: Inspect event payloads.
    :type events: Sequence[EventInfo]
    :param event_name: Qualified event name.
    :type event_name: str
    :return: Number of transition consumers recorded for the event.
    :rtype: int

    Examples::

        >>> event = EventInfo(
        ...     qualified_name='Root.Panic',
        ...     scope='chain',
        ...     used_by=(('Root.Lost', 'Root.A'),),
        ...     is_declared=True,
        ...     is_used=True,
        ... )
        >>> _event_consumer_count((event,), 'Root.Panic')
        1
    """
    for event in events:
        if event.qualified_name == event_name:
            return len(event.used_by)
    return 0


def _type_matches_schema(value: Any, field_spec: CodeFieldSpec) -> bool:
    """Return whether a runtime value fits a ``codes.yaml`` type token.

    :param value: Runtime value from a diagnostic refs payload.
    :type value: Any
    :param field_spec: Field schema loaded from ``codes.yaml``.
    :type field_spec: CodeFieldSpec
    :return: ``True`` when ``value`` fits the field type.
    :rtype: bool

    Examples::

        >>> spec = CodeFieldSpec(
        ...     name='count',
        ...     type='int',
        ...     required=True,
        ...     description='Count value.',
        ... )
        >>> _type_matches_schema(3, spec)
        True
        >>> _type_matches_schema(True, spec)
        False
    """
    type_token = field_spec.type
    if type_token == 'str':
        return isinstance(value, str)
    if type_token == 'int':
        return isinstance(value, int) and not isinstance(value, bool)
    if type_token == 'float':
        return isinstance(value, float)
    if type_token == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_token == 'bool':
        return isinstance(value, bool)
    if type_token == 'dict':
        return isinstance(value, dict)
    if type_token == 'list[str]':
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if type_token == 'list[Span]':
        return isinstance(value, list) and all(
            item is None or hasattr(item, 'line') for item in value
        )
    if type_token == 'Span':
        return value is None or hasattr(value, 'line')
    if type_token == 'str_or_null':
        return value is None or isinstance(value, str)
    if type_token == 'int_or_null':
        return value is None or (
            isinstance(value, int) and not isinstance(value, bool)
        )
    return True


def _refs_match_code_schema(
        code: str,
        refs: Mapping[str, Any],
        *,
        _registry: Mapping[str, CodeSpec] = CODE_REGISTRY,
) -> bool:
    """Return whether refs satisfy the declared verify-adapter schema.

    The conversion layer uses this as a fail-closed guard: raw verify findings
    are emitted only after their refs are declared, complete, enum-safe, and
    type-compatible with ``codes.yaml``. Most accepted codes are declared as
    ``emit_tier: verify_pipeline``; codes in
    :data:`VERIFY_SHARED_STATIC_CODES` are legacy static diagnostics that a
    structural verify algorithm may also emit.

    :param code: Diagnostic code to validate.
    :type code: str
    :param refs: Candidate refs payload.
    :type refs: Mapping[str, Any]
    :param _registry: Diagnostic code registry used for validation. Defaults
        to :data:`CODE_REGISTRY`; tests may pass a synthetic registry to cover
        schema predicates without mutating the global registry.
    :type _registry: Mapping[str, CodeSpec], optional
    :return: ``True`` when the code may be emitted by the verify adapter and
        refs match its schema.
    :rtype: bool

    Examples::

        >>> _refs_match_code_schema('W_DEAD_GUARD', {
        ...     'algorithm_name': 'dead_guard',
        ...     'verification_scope': 'smt_local',
        ...     'transition': {
        ...         'parent': 'Root',
        ...         'from_state': 'A',
        ...         'to_state': 'B',
        ...     },
        ...     'transition_summary': 'Root:A->B',
        ... })
        True
        >>> _refs_match_code_schema('W_UNREACHABLE_STATE', {
        ...     'state_path': 'Root.Orphan',
        ... })
        True
    """
    spec = _registry.get(code)
    if spec is None:
        return False
    if spec.emit_tier != 'verify_pipeline' and code not in VERIFY_SHARED_STATIC_CODES:
        return False
    declared = set(spec.refs_schema.keys())
    if set(refs.keys()) - declared:
        return False
    for field_name in spec.required_fields():
        if field_name not in refs or refs[field_name] is None:
            return False
    for field_name, field_spec in spec.refs_schema.items():
        if field_name not in refs:
            continue
        value = refs[field_name]
        if field_spec.enum and value not in set(field_spec.enum):
            return False
        if not _type_matches_schema(value, field_spec):
            return False
        if field_spec.item_enum:
            allowed_items = set(field_spec.item_enum)
            if any(item not in allowed_items for item in value):
                return False
        if field_spec.exact_values and tuple(value) != field_spec.exact_values:
            return False
    return True


def _make_verify_diagnostic(
        code: str,
        refs: Mapping[str, Any],
        span: Optional[Span],
) -> Optional[ModelDiagnostic]:
    """Create one ``ModelDiagnostic`` from verified refs.

    Verify diagnostics must bind back to the source object declared by the
    code registry. A raw verify finding with valid refs but no source object
    is dropped instead of becoming a public spanless diagnostic.

    :param code: Verify-pipeline diagnostic code.
    :type code: str
    :param refs: Candidate refs payload.
    :type refs: Mapping[str, Any]
    :param span: Best-effort source span for the diagnostic.
    :type span: Optional[Span]
    :return: ``ModelDiagnostic`` when refs pass schema validation, otherwise
        ``None``.
    :rtype: Optional[ModelDiagnostic]

    Examples::

        >>> diag = _make_verify_diagnostic('I_NONTRIVIAL_SCC', {
        ...     'algorithm_name': 'strongly_connected_components',
        ...     'verification_scope': 'topological_only',
        ...     'representative_state_path': 'Root.A',
        ...     'scc': ['Root.A'],
        ... }, Span(line=2, column=5))
        >>> diag.code
        'I_NONTRIVIAL_SCC'
    """
    if not _refs_match_code_schema(code, refs):
        return None
    spec = CODE_REGISTRY[code]
    if (
            spec.span_object is not None
            and code not in KNOWN_SPANLESS_CODES
            and span is None
    ):
        return None
    return ModelDiagnostic(
        code=code,
        severity=spec.severity,
        message=spec.description,
        span=span,
        refs=dict(refs),
    )


def _verify_diagnostics_from_results(
        results: Sequence['InspectRunResult'],
        states: Sequence[StateInfo],
        transitions: Sequence[TransitionInfo],
        events: Sequence[EventInfo],
        actions: Sequence[ActionInfo],
) -> Tuple[ModelDiagnostic, ...]:
    """Convert inspect-adapter results into public model diagnostics.

    SMT-local raw diagnostic dictionaries are consumed directly. Structural
    results are interpreted only for algorithms whose payloads have an
    explicit conversion. Indeterminate results are skipped even when partial
    raw diagnostics are attached, so ``unknown`` or ``timeout`` does not
    become a false warning.

    :param results: Normalized inspect-adapter results.
    :type results: Sequence[pyfcstm.verify.inspect_adapter.InspectRunResult]
    :param states: Inspect state payloads.
    :type states: Sequence[StateInfo]
    :param transitions: Inspect transition payloads.
    :type transitions: Sequence[TransitionInfo]
    :param events: Inspect event payloads.
    :type events: Sequence[EventInfo]
    :param actions: Inspect action payloads.
    :type actions: Sequence[ActionInfo]
    :return: Converted verify diagnostics.
    :rtype: Tuple[ModelDiagnostic, ...]

    Examples::

        >>> from pyfcstm.verify.inspect_adapter import InspectRunResult
        >>> result = InspectRunResult(
        ...     algorithm_name='dead_guard',
        ...     complexity_tier='smt_linear',
        ...     smt_logic='QF_LIRA',
        ...     verification_scope='smt_local',
        ...     diagnostic_codes=('W_DEAD_GUARD',),
        ...     result_kind='unknown',
        ...     diagnostics=(),
        ...     reason='solver said unknown',
        ...     raw_result=None,
        ... )
        >>> _verify_diagnostics_from_results((result,), (), (), (), ())
        ()
    """
    diagnostics: List[ModelDiagnostic] = []
    for result in results:
        if result.result_kind in {'unknown', 'timeout', 'undecidable_skip'}:
            continue
        if result.diagnostics:
            for raw in result.diagnostics:
                if not isinstance(raw, Mapping):
                    continue
                code = raw.get('code')
                if not isinstance(code, str):
                    continue
                refs = _verify_smt_refs(raw)
                if refs is None:
                    continue
                diagnostic = _make_verify_diagnostic(
                    code,
                    refs,
                    _verify_smt_span(code, raw, states, transitions, actions),
                )
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
            continue
        diagnostics.extend(_structural_verify_diagnostics(result, states, events))
    return tuple(diagnostics)


def _catalog_emittable_diagnostics(
        diagnostics: Sequence[ModelDiagnostic],
) -> Tuple[ModelDiagnostic, ...]:
    """
    Return diagnostics that are allowed to appear in inspect output.

    Catalog-only codes freeze cross-end contracts before an analyzer is wired.
    If a future analyzer accidentally emits such a code before the contract is
    promoted to a real emit tier, the public inspect surface must fail closed
    by dropping it.

    :param diagnostics: Candidate diagnostics collected from inspect analyzers.
    :type diagnostics: Sequence[ModelDiagnostic]
    :return: Diagnostics whose code registry entry is not ``catalog_only``.
    :rtype: Tuple[ModelDiagnostic, ...]

    Example::

        >>> diagnostic = ModelDiagnostic(
        ...     code='W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE',
        ...     severity='warning',
        ...     message='partial-static test',
        ... )
        >>> _catalog_emittable_diagnostics((diagnostic,)) == (diagnostic,)
        True
    """
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if CODE_REGISTRY.get(diagnostic.code) is None
        or CODE_REGISTRY[diagnostic.code].emit_tier != 'catalog_only'
    )


def _deduplicate_model_diagnostics(
        diagnostics: Sequence[ModelDiagnostic],
) -> Tuple[ModelDiagnostic, ...]:
    """Remove semantic duplicates while preserving diagnostic order.

    The inspect surface may combine legacy design-health warnings with optional
    verify-pipeline diagnostics. When both paths report the same unreachable
    state, callers should see one diagnostic rather than two equivalent
    warnings. Other diagnostics are left untouched because repeated findings on
    one state can represent distinct source occurrences.

    :param diagnostics: Diagnostics in emission order.
    :type diagnostics: Sequence[ModelDiagnostic]
    :return: Diagnostics with duplicate state-scoped entries removed.
    :rtype: Tuple[ModelDiagnostic, ...]

    Examples::

        >>> diag = ModelDiagnostic(
        ...     code='W_UNREACHABLE_STATE',
        ...     severity='warning',
        ...     message='unreachable',
        ...     refs={'state_path': 'Root.Orphan'},
        ... )
        >>> len(_deduplicate_model_diagnostics((diag, diag)))
        1
    """
    out: List[ModelDiagnostic] = []
    seen_state_scoped = set()
    for diagnostic in diagnostics:
        state_path = diagnostic.refs.get('state_path')
        if diagnostic.code == 'W_UNREACHABLE_STATE' and isinstance(state_path, str):
            key = (diagnostic.code, state_path)
            if key in seen_state_scoped:
                continue
            seen_state_scoped.add(key)
        out.append(diagnostic)
    return tuple(out)


def inspect_model(
        machine: 'StateMachine',
        *,
        deep_hierarchy_threshold: int = DEFAULT_DEEP_HIERARCHY_THRESHOLD,
        large_composite_threshold: int = DEFAULT_LARGE_COMPOSITE_THRESHOLD,
        var_to_leaf_ratio_threshold: float = DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD,
        enable_verify: bool = False,
        max_complexity_tier: str = 'structural',
        max_call_count_scaling: str = 'linear_in_transitions',
        smt_timeout_ms: Optional[int] = None,
) -> ModelInspect:
    """
    Build a structured inspection report for a state machine model.

    The report combines the structural payload, the five derived view
    graphs, and design-health diagnostics that can be computed from the
    inspect surface.

    :param machine: The state machine model to inspect.
    :type machine: pyfcstm.model.StateMachine
    :param deep_hierarchy_threshold: Maximum accepted hierarchy depth.
    :type deep_hierarchy_threshold: int
    :param large_composite_threshold: Maximum accepted number of direct
        child states in one composite.
    :type large_composite_threshold: int
    :param var_to_leaf_ratio_threshold: Maximum accepted variable to
        non-pseudo leaf-state ratio.
    :type var_to_leaf_ratio_threshold: float
    :param enable_verify: Whether to run inspect-eligible
        :mod:`pyfcstm.verify` algorithms and append their diagnostics.
        The default ``False`` preserves the Layer 2 inspect contract.
    :type enable_verify: bool, optional
    :param max_complexity_tier: Maximum verify complexity tier accepted by
        the inspect adapter when ``enable_verify`` is true.
        ``"structural"`` keeps the default to graph-only verification.
    :type max_complexity_tier: str, optional
    :param max_call_count_scaling: Maximum verify call-count scaling accepted
        by the inspect adapter when ``enable_verify`` is true.
    :type max_call_count_scaling: str, optional
    :param smt_timeout_ms: Optional solver timeout forwarded to SMT-local
        verify algorithms. ``None`` preserves the raw verify default of no
        configured timeout.
    :type smt_timeout_ms: Optional[int], optional
    :return: Structured view of the model.
    :rtype: ModelInspect

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, 'state_machine_dsl')
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> report = inspect_model(machine)
        >>> report.reachability_graph['Root.A']
        ('Root.B',)
        >>> verify_report = inspect_model(machine, enable_verify=True)
        >>> len(verify_report.diagnostics) >= len(report.diagnostics)
        True
    """
    deep_hierarchy_threshold = _normalize_int_threshold(
        'deep_hierarchy_threshold',
        deep_hierarchy_threshold,
    )
    large_composite_threshold = _normalize_int_threshold(
        'large_composite_threshold',
        large_composite_threshold,
    )
    var_to_leaf_ratio_threshold = _normalize_float_threshold(
        'var_to_leaf_ratio_threshold',
        var_to_leaf_ratio_threshold,
    )
    states = _build_state_infos(machine)
    transitions = _build_transition_infos(machine)
    variables = _build_variable_infos(machine, states)
    events = _build_event_infos(machine, transitions)
    actions = _build_action_infos(machine)
    forced_transitions = _build_forced_transition_infos(machine)
    metrics = _build_metrics(states, transitions, variables, events)
    reachability_graph = _build_reachability_graph(states, transitions)
    root_state_path = _state_path(machine.root_state)
    diagnostics = list(collect_design_health_warnings(
        states,
        transitions,
        variables,
        events,
        actions,
        forced_transitions,
        metrics,
        reachability_graph,
        root_state_path=root_state_path,
        deep_hierarchy_threshold=deep_hierarchy_threshold,
        large_composite_threshold=large_composite_threshold,
        var_to_leaf_ratio_threshold=var_to_leaf_ratio_threshold,
        machine=machine,
    ))
    if enable_verify:
        verify_results = _run_verify_inspect_algorithms(
            machine,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
            smt_timeout_ms=smt_timeout_ms,
        )
        diagnostics.extend(_verify_diagnostics_from_results(
            verify_results,
            states,
            transitions,
            events,
            actions,
        ))
    diagnostics = list(_catalog_emittable_diagnostics(diagnostics))
    diagnostics = list(_deduplicate_model_diagnostics(diagnostics))
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
        diagnostics=tuple(diagnostics),
    )


def _normalize_int_threshold(name: str, value: int) -> int:
    if isinstance(value, bool):
        raise TypeError(f'{name} must be an integer threshold, got bool')
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        raise ValueError(f'{name} must be an integer threshold, got {value!r}')
    raise TypeError(f'{name} must be an integer threshold, got {type(value).__name__}')


def _normalize_float_threshold(name: str, value: float) -> float:
    if isinstance(value, bool):
        raise TypeError(f'{name} must be a finite numeric threshold, got bool')
    if isinstance(value, (int, float)):
        normalized = float(value)
        if math.isfinite(normalized):
            return normalized
        raise ValueError(f'{name} must be a finite numeric threshold, got {value!r}')
    raise TypeError(f'{name} must be a finite numeric threshold, got {type(value).__name__}')


def _to_json_dataclass(obj: Any) -> Any:
    if hasattr(obj, '__dataclass_fields__'):
        return {
            name: _to_json_dataclass(getattr(obj, name))
            for name in obj.__dataclass_fields__
            if name not in {
                'span',
                'effect_spans',
                'effect_self_assign_spans',
                'float_literal_assignment_spans',
            }
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
    if d.span is not None:
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
        'refs': _to_json_dataclass(d.refs),
    }
