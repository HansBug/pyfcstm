"""
Hierarchical state machine model and DSL conversion utilities.

This module provides the core model objects used to represent hierarchical
state machines, along with conversion helpers that map between the internal
model and the DSL/AST representation. The primary capabilities include:

* Defining states, transitions, events, and variable definitions.
* Representing entry, during, exit, and aspect-oriented actions.
* Parsing a DSL AST into a structured :class:`StateMachine`.
* Exporting models to AST nodes and PlantUML diagrams.

The main public components are:

* :class:`Operation` - Operation assignments used in actions and transitions.
* :class:`Event` - Event definitions scoped to a state path.
* :class:`ComboOriginRef` - Provenance reference from generated combo edges.
* :class:`Transition` - Transition definitions with optional guards and effects.
* :class:`OnStage` - Entry/during/exit actions for a state.
* :class:`OnAspect` - Aspect-oriented during actions.
* :class:`State` - Hierarchical state container with actions and transitions.
* :class:`VarDefine` - Typed variable definitions.
* :class:`StateMachine` - Root container for the full state machine.
* :func:`parse_dsl_node_to_state_machine` - DSL AST parsing utility.

.. note::
   The parsing utilities validate state and variable references. Syntax errors
   are raised when invalid references or structural inconsistencies are found.

Example::

    >>> from pyfcstm.dsl import node as dsl_nodes
    >>> from pyfcstm.model.model import parse_dsl_node_to_state_machine
    >>> program = dsl_nodes.StateMachineDSLProgram(
    ...     definitions=[],
    ...     root_state=dsl_nodes.StateDefinition("root")
    ... )
    >>> sm = parse_dsl_node_to_state_machine(program)
    >>> sm.root_state.name
    'root'

"""

import hashlib
import io
import itertools
import json
import weakref
from dataclasses import dataclass, field
from textwrap import indent
from typing import Optional, Union, List, Dict, Tuple, Iterator, Set

from .base import AstExportable, PlantUMLExportable
from .expr import Expr, parse_expr_node_to_expr
from .imports import assemble_state_machine_imports
from .plantuml import PlantUMLOptions, PlantUMLOptionsInput, format_state_name
from ..diagnostics.sink import DiagnosticSink
from ..diagnostics.sink import _emit as _emit_or_raise
from ..dsl import node as dsl_nodes, INIT_STATE, EXIT_STATE
from ..utils.validate import (
    ModelDiagnostic,
    ModelLookupError,
    ModelValueError,
    Span,
)

__all__ = [
    "OperationStatement",
    "Operation",
    "IfBlockBranch",
    "IfBlock",
    "Event",
    "ComboOriginRef",
    "Transition",
    "OnStage",
    "OnAspect",
    "State",
    "VarDefine",
    "StateMachine",
    "parse_dsl_node_to_state_machine",
]

from ..utils import sequence_safe, to_identifier


def _node_span(node) -> Optional[Span]:
    """Return an AST node span when the parser attached one."""
    # PR-D1 span propagation is deliberately tolerant of AST nodes that do not
    # carry parser spans yet: older synthetic/export-created nodes can still
    # pass through this path, and PR-D2 will decide which missing spans are
    # diagnostic-contract gaps. Keep the missing-span case observable as
    # ``None`` instead of manufacturing an imprecise fallback.
    return getattr(node, "_span", None)


def _event_origin_from_id(
    event_id: dsl_nodes.ChainID,
    event_scope: Optional[str] = None,
    source_state: Optional[str] = None,
) -> str:
    """Infer the event trigger scope preserved by the DSL listener."""
    if event_scope is not None:
        return event_scope
    if event_id.is_absolute:
        return "absolute"
    if (
        source_state is not None
        and len(event_id.path) == 2
        and event_id.path[0] == source_state
    ):
        return "local"
    return "chain"


_COMBO_STATE_PREFIX = "__combo_"
_COMBO_DIGEST_SIZE = 12
_COMBO_DISPLAY_PREFIX = "combo after "
_COMBO_HEX_DIGITS = frozenset("0123456789abcdef")


def _is_combo_pseudo_export_name(name: str) -> bool:
    """Return whether a state name looks like an exported combo pseudo name."""
    digest_tag_size = _COMBO_DIGEST_SIZE + 2
    if (
        not name.startswith(_COMBO_STATE_PREFIX)
        or len(name) <= len(_COMBO_STATE_PREFIX) + digest_tag_size
    ):
        return False
    digest_tag = name[-digest_tag_size:]
    return (
        digest_tag.startswith("_h")
        and len(digest_tag[2:]) == _COMBO_DIGEST_SIZE
        and all(char in _COMBO_HEX_DIGITS for char in digest_tag[2:])
    )


def _is_combo_pseudo_referenced_by_owner(
    name: str, owner_node: Optional[dsl_nodes.StateDefinition]
) -> bool:
    """Return whether an exported combo pseudo is wired into owner transitions."""
    if owner_node is None:
        return False
    has_incoming = False
    has_outgoing = False
    for transition in owner_node.transitions:
        has_incoming = has_incoming or transition.to_state == name
        has_outgoing = has_outgoing or transition.from_state == name
    return has_incoming and has_outgoing


def _combo_export_endpoint_text(endpoint) -> str:
    """Return the endpoint text used by combo pseudo semantic payloads."""
    if endpoint is dsl_nodes.INIT_STATE:
        return "__init__"
    if endpoint is dsl_nodes.EXIT_STATE:
        return "__exit__"
    return str(endpoint)


def _is_combo_export_basic_shape(node: dsl_nodes.StateDefinition) -> bool:
    """Return whether a state has the minimal exported combo pseudo shape."""
    return (
        node.is_pseudo
        and _is_combo_pseudo_export_name(node.name)
        and node.extra_name is not None
        and node.extra_name.startswith(_COMBO_DISPLAY_PREFIX)
        and len(node.extra_name) > len(_COMBO_DISPLAY_PREFIX)
        and not node.events
        and not node.imports
        and not node.substates
        and not node.transitions
        and not node.force_transitions
        and not node.enters
        and not node.durings
        and not node.exits
        and not node.during_aspects
    )


def _combo_export_find_substate(
    owner_node: dsl_nodes.StateDefinition, name: str
) -> Optional[dsl_nodes.StateDefinition]:
    """Return an owner child state by name, preserving AST source order."""
    for subnode in owner_node.substates:
        if subnode.name == name:
            return subnode
    return None


def _combo_export_event_declared(
    owner_node: dsl_nodes.StateDefinition,
    event_id: dsl_nodes.ChainID,
    event_scope: str,
    source_state,
    local_scope: bool,
) -> bool:
    """Return whether an exported edge references an explicit event declaration."""
    if event_id.is_absolute:
        return True
    local_candidate = event_scope == "local" or (
        local_scope
        and isinstance(source_state, str)
        and (len(event_id.path) == 1 or event_id.path[0] == source_state)
    )
    if local_candidate and isinstance(source_state, str):
        source_node = _combo_export_find_substate(owner_node, source_state)
        return source_node is not None and any(
            event.name == event_id.path[-1] for event in source_node.events
        )

    current = owner_node
    for segment in event_id.path[:-1]:
        current = _combo_export_find_substate(current, segment)
        if current is None:
            return False
    return any(event.name == event_id.path[-1] for event in current.events)


def _combo_export_transition_term(
    owner_node: dsl_nodes.StateDefinition,
    transition: dsl_nodes.TransitionDefinition,
    source_state,
    local_scope: bool,
) -> Optional[Tuple[str, Tuple[object, ...]]]:
    """Return the canonical combo term text and semantic key for an edge."""
    if transition.condition_expr is not None:
        expr_text = str(transition.condition_expr)
        return f"[{expr_text}]", ("guard", expr_text)
    if transition.event_id is None:
        return None
    if transition.event_scope == "local" and transition.from_state != source_state:
        return None

    event_id = transition.event_id
    event_scope = _event_origin_from_id(
        event_id,
        transition.event_scope,
        source_state=source_state if isinstance(source_state, str) else None,
    )
    absolute_export = False
    if event_scope == "chain" and not event_id.is_absolute and len(event_id.path) > 1:
        current = owner_node
        for segment in event_id.path[:-1]:
            current = _combo_export_find_substate(current, segment)
            if current is None:
                break
        absolute_export = current is not None and any(
            event.name == event_id.path[-1] for event in current.events
        )
    if not _combo_export_event_declared(
        owner_node, event_id, event_scope, source_state, local_scope
    ):
        return None
    if (
        local_scope
        and isinstance(source_state, str)
        and not event_id.is_absolute
        and len(event_id.path) >= 2
        and event_id.path[0] == source_state
    ):
        event_name = event_id.path[-1]
        return event_name, ("event", "local", False, (event_name,))
    if event_scope == "local" and not event_id.is_absolute:
        event_name = event_id.path[-1]
        return event_name, ("event", "local", False, (event_name,))
    if absolute_export:
        return f"/{event_id}", ("event", "absolute", True, tuple(event_id.path))
    return str(event_id), (
        "event",
        event_scope,
        event_id.is_absolute,
        tuple(event_id.path),
    )


def _combo_export_split_term_texts(text: str) -> Optional[Tuple[str, ...]]:
    """Split exported combo display text into top-level term texts."""
    terms = []
    bracket_depth = 0
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char == "[":
            bracket_depth += 1
            index += 1
            continue
        if char == "]":
            bracket_depth -= 1
            if bracket_depth < 0:
                return None
            index += 1
            continue
        if bracket_depth == 0 and text.startswith(" + ", index):
            terms.append(text[start:index])
            index += 3
            start = index
            continue
        index += 1
    if bracket_depth != 0:
        return None
    terms.append(text[start:])
    if any(not term for term in terms):
        return None
    return tuple(terms)


def _combo_export_display_term_key(
    term_text: str, source_state, local_scope: bool
) -> Optional[Tuple[object, ...]]:
    """Return the semantic key represented by an exported display term."""
    if term_text.startswith("[") and term_text.endswith("]"):
        return ("guard", term_text[1:-1])
    if term_text.startswith("/"):
        return ("event", "absolute", True, tuple(term_text[1:].split(".")))
    if local_scope and isinstance(source_state, str) and "." not in term_text:
        return ("event", "local", False, (term_text,))
    return ("event", "chain", False, tuple(term_text.split(".")))


def _combo_export_event_term_options(
    term_text: str, transition: dsl_nodes.TransitionDefinition, source_state
) -> Tuple[str, ...]:
    """Return plausible original texts for an exported event edge."""
    options = [term_text]
    event_id = transition.event_id
    if (
        event_id is not None
        and not event_id.is_absolute
        and isinstance(source_state, str)
        and len(event_id.path) >= 2
        and event_id.path[0] == source_state
    ):
        source_qualified = ".".join(event_id.path)
        if source_qualified not in options:
            options.append(source_qualified)
    return tuple(options)


def _combo_export_term_slug(term_text: str) -> str:
    """Return the pseudo-name slug for an exported combo term."""
    if term_text.startswith("[") and term_text.endswith("]"):
        text = f"if {term_text[1:-1]}"
        for source, replacement in [
            ("=>", " implies "),
            ("==", " eq "),
            ("!=", " ne "),
            (">=", " ge "),
            ("<=", " le "),
            ("&&", " and "),
            ("||", " or "),
            (">", " gt "),
            ("<", " lt "),
            ("!", " not "),
        ]:
            text = text.replace(source, replacement)
    else:
        text = term_text
        if text.startswith("/"):
            text = f"abs {text[1:]}"
    return to_identifier(text, strict_mode=True).lower()


def _combo_export_trace_prefix(
    node: dsl_nodes.StateDefinition, owner_node: dsl_nodes.StateDefinition
) -> Optional[Tuple[object, Tuple[dsl_nodes.TransitionDefinition, ...]]]:
    """Trace the single generated incoming path ending at an exported pseudo."""
    current_name = node.name
    reverse_edges = []
    seen = set()
    while True:
        if current_name in seen:
            return None
        seen.add(current_name)
        incoming = [
            transition
            for transition in owner_node.transitions
            if transition.to_state == current_name
        ]
        if len(incoming) != 1:
            return None
        edge = incoming[0]
        reverse_edges.append(edge)
        source = edge.from_state
        if isinstance(source, str) and source.startswith(_COMBO_STATE_PREFIX):
            source_node = _combo_export_find_substate(owner_node, source)
            if source_node is None or not _is_combo_export_basic_shape(source_node):
                return None
            current_name = source
            continue
        return source, tuple(reversed(reverse_edges))


def _combo_export_trace_first_terminal(
    node: dsl_nodes.StateDefinition, owner_node: dsl_nodes.StateDefinition
) -> Optional[Tuple[object, Tuple[dsl_nodes.TransitionDefinition, ...]]]:
    """Trace the first generated continuation path leaving an exported pseudo."""
    current_name = node.name
    edges = []
    seen = set()
    while True:
        if current_name in seen:
            return None
        seen.add(current_name)
        outgoing = [
            transition
            for transition in owner_node.transitions
            if transition.from_state == current_name
        ]
        if not outgoing:
            return None
        edge = outgoing[0]
        if edge.event_scope == "local":
            return None
        edges.append(edge)
        target = edge.to_state
        if isinstance(target, str) and target.startswith(_COMBO_STATE_PREFIX):
            target_node = _combo_export_find_substate(owner_node, target)
            if target_node is None or not _is_combo_export_basic_shape(target_node):
                return None
            current_name = target
            continue
        return target, tuple(edges)


def _is_combo_pseudo_export_semantically_valid(
    node: dsl_nodes.StateDefinition,
    owner_node: Optional[dsl_nodes.StateDefinition],
    owner_path: Tuple[str, ...],
) -> bool:
    """Return whether an exported combo pseudo matches generated semantics."""
    if owner_node is None or not _is_combo_export_basic_shape(node):
        return False
    prefix_trace = _combo_export_trace_prefix(node, owner_node)
    terminal_trace = _combo_export_trace_first_terminal(node, owner_node)
    if prefix_trace is None or terminal_trace is None:
        return False

    source_state, prefix_edges = prefix_trace
    target_state, terminal_edges = terminal_trace
    local_scope = False
    if source_state is not dsl_nodes.INIT_STATE:
        for edge in (*prefix_edges, *terminal_edges):
            if edge.event_scope == "local" or (
                edge.event_scope == "chain"
                and edge.event_id is not None
                and not edge.event_id.is_absolute
                and len(edge.event_id.path) >= 2
                and edge.event_id.path[0] == source_state
            ):
                local_scope = True
                break

    display_text = node.extra_name[len(_COMBO_DISPLAY_PREFIX) :]
    consumed_term_texts = _combo_export_split_term_texts(display_text)
    if consumed_term_texts is None or len(consumed_term_texts) != len(prefix_edges):
        return False

    consumed_term_keys = []
    for edge, display_term_text in zip(prefix_edges, consumed_term_texts):
        edge_term = _combo_export_transition_term(
            owner_node, edge, source_state, local_scope
        )
        display_key = _combo_export_display_term_key(
            display_term_text, source_state, local_scope
        )
        if edge_term is None or display_key is None:
            return False
        consumed_term_keys.append(display_key)

    remaining_term_options = []
    for edge in terminal_edges:
        term = _combo_export_transition_term(
            owner_node, edge, source_state, local_scope
        )
        if term is None:
            return False
        term_text, _ = term
        if edge.event_id is None:
            remaining_term_options.append((term_text,))
        else:
            remaining_term_options.append(
                _combo_export_event_term_options(term_text, edge, source_state)
            )

    if local_scope or source_state is dsl_nodes.INIT_STATE:
        prefix_options = ("::", ":")
    else:
        prefix_options = (":",)
    effects = tuple(str(item) for item in terminal_edges[-1].post_operations)
    chooser_key = (
        (owner_path, "entry", "INIT_MARKER")
        if source_state is dsl_nodes.INIT_STATE
        else (owner_path, "state", (*owner_path, source_state))
    )
    source_label = "entry" if chooser_key[1] == "entry" else ".".join(chooser_key[2])
    slug_parts = [to_identifier(source_label, strict_mode=True).lower()]
    slug_parts.extend(_combo_export_term_slug(term) for term in consumed_term_texts)
    expected_name_prefix = f"{_COMBO_STATE_PREFIX}{sequence_safe(slug_parts)}_h"
    if not node.name.startswith(expected_name_prefix):
        return False

    for prefix, remaining_term_texts in itertools.product(
        prefix_options, itertools.product(*remaining_term_options)
    ):
        origin_id = (
            f"{'.'.join(owner_path)}:"
            f"{_combo_export_endpoint_text(source_state)}->"
            f"{_combo_export_endpoint_text(target_state)}:"
            f"{prefix} {' + '.join([*consumed_term_texts, *remaining_term_texts])}"
        )
        if effects:
            origin_id = f"{origin_id}:effect={json.dumps(effects, ensure_ascii=False)}"

        payload_obj = {
            "owner_path": owner_path,
            "chooser_key": chooser_key,
            "consumed_terms": tuple(consumed_term_keys),
            "run_anchor_origin_id": origin_id,
            "semantic_duplicate_discriminator": None,
        }
        payload = json.dumps(payload_obj, ensure_ascii=False, sort_keys=True)
        short_digest = _combo_payload_digest(payload)[:_COMBO_DIGEST_SIZE]
        expected_name = f"{expected_name_prefix}{short_digest}"
        if node.name == expected_name:
            return True
    return False


def _is_exported_combo_pseudo_node(
    node: dsl_nodes.StateDefinition,
    owner_node: Optional[dsl_nodes.StateDefinition] = None,
    owner_path: Tuple[str, ...] = (),
) -> bool:
    """Return whether an AST node is an exported generated combo pseudo state."""
    if not node.is_pseudo or not node.name.startswith(_COMBO_STATE_PREFIX):
        return False
    if getattr(node, "_generated_combo_pseudo", False):
        return True
    has_export_shape = (
        _is_combo_pseudo_export_name(node.name)
        and node.extra_name is not None
        and node.extra_name.startswith(_COMBO_DISPLAY_PREFIX)
        and len(node.extra_name) > len(_COMBO_DISPLAY_PREFIX)
        and not node.events
        and not node.imports
        and not node.substates
        and not node.transitions
        and not node.force_transitions
        and not node.enters
        and not node.durings
        and not node.exits
        and not node.during_aspects
    )
    return (
        has_export_shape
        and _is_combo_pseudo_referenced_by_owner(node.name, owner_node)
        and _is_combo_pseudo_export_semantically_valid(node, owner_node, owner_path)
    )


def _combo_payload_digest(payload: str) -> str:
    """
    Return the full digest for a combo pseudo-state payload.

    The helper is intentionally small and module-level so tests can
    monkey-patch it to exercise truncated digest collision handling without
    searching for real SHA-256 collisions.

    :param payload: Canonical semantic payload for a generated combo object.
    :type payload: str
    :return: Full hexadecimal SHA-256 digest.
    :rtype: str

    Example::

        >>> len(_combo_payload_digest("Root|S1|E1"))
        64
    """
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComboOriginRef:
    """
    Reference from a generated combo edge back to an original combo term.

    Generated prefix edges may represent more than one original combo
    transition. This value object preserves the one-to-many relationship that
    later inspect and visualization layers need in order to project generated
    edges back to user-authored trigger terms.

    :param origin_id: Stable identifier of the original combo transition.
    :type origin_id: str
    :param term_index: Zero-based trigger term index, or the last consumed term
        for terminal no-trigger edges.
    :type term_index: int
    :param role: Generated edge role, such as ``'prefix'`` or ``'terminal'``.
    :type role: str
    :param consumes_term: Whether this generated edge consumes the referenced
        term.
    :type consumes_term: bool
    :param term_text: Canonical text of the referenced term.
    :type term_text: str
    :param transition_span: Source span of the original combo transition.
    :type transition_span: pyfcstm.utils.validate.Span, optional
    :param trigger_span: Source span of the original trigger suffix.
    :type trigger_span: pyfcstm.utils.validate.Span, optional
    :param term_span: Source span of the referenced trigger term.
    :type term_span: pyfcstm.utils.validate.Span, optional
    :param value_span: Source span of the value inside the trigger term when
        available.
    :type value_span: pyfcstm.utils.validate.Span, optional
    :param removal_span: Source span suitable for removing the trigger term.
    :type removal_span: pyfcstm.utils.validate.Span, optional

    Example::

        >>> ref = ComboOriginRef("Root:S1:0", 0, "prefix", True, "E1")
        >>> ref.origin_id
        'Root:S1:0'
    """

    origin_id: str
    term_index: int
    role: str
    consumes_term: bool
    term_text: str
    transition_span: Optional[Span] = field(default=None, compare=False)
    trigger_span: Optional[Span] = field(default=None, compare=False)
    term_span: Optional[Span] = field(default=None, compare=False)
    value_span: Optional[Span] = field(default=None, compare=False)
    removal_span: Optional[Span] = field(default=None, compare=False)


@dataclass(frozen=True)
class _ComboAlternative:
    """
    Internal high-level transition alternative used by the ordered-trie expander.

    :param transnode: Original DSL transition node.
    :type transnode: pyfcstm.dsl.node.TransitionDefinition
    :param terms: Ordered combo trigger terms.
    :type terms: tuple
    :param origin_id: Stable source-origin identifier.
    :type origin_id: str
    :param declaration_index: Index in the original chooser's transition
        priority list.
    :type declaration_index: int
    :param semantic_duplicate_discriminator: Stable discriminator used when
        otherwise identical combo alternatives appear in the same chooser.
    :type semantic_duplicate_discriminator: Optional[int]
    """

    transnode: dsl_nodes.TransitionDefinition
    terms: Tuple[dsl_nodes.ComboTriggerTerm, ...]
    origin_id: str
    declaration_index: int
    semantic_duplicate_discriminator: Optional[int] = None


@dataclass
class OperationStatement(AstExportable):
    """
    Abstract base class for executable statements inside operation blocks.

    Operation statements may be plain assignments or nested control-flow
    structures such as ``if`` blocks.

    :rtype: OperationStatement
    """

    pass


@dataclass
class Operation(OperationStatement):
    """
    Represents an operation that assigns a value to a variable.

    An operation consists of a variable name and an expression that will be
    assigned to the variable when the operation is executed.

    :param var_name: The name of the variable to assign to
    :type var_name: str
    :param expr: The expression to evaluate and assign to the variable
    :type expr: Expr

    Example::

        >>> op = Operation(var_name="counter", expr=some_expr)
        >>> op.var_name
        'counter'
    """

    var_name: str
    expr: Expr
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def to_ast_node(self) -> dsl_nodes.OperationAssignment:
        """
        Convert this operation to an AST node.

        The private ``_span`` metadata is intentionally not copied. Exported
        AST nodes are for DSL serialization, not source-span round-tripping.

        :return: An operation assignment AST node
        :rtype: dsl_nodes.OperationAssignment
        """
        return dsl_nodes.OperationAssignment(
            name=self.var_name,
            expr=self.expr.to_ast_node(),
        )

    def var_name_to_ast_node(self) -> dsl_nodes.Name:
        """
        Convert the variable name to an AST node.

        :return: A name AST node
        :rtype: dsl_nodes.Name
        """
        return dsl_nodes.Name(name=self.var_name)


@dataclass
class IfBlockBranch(AstExportable):
    """
    Represents a single branch inside a model-layer ``if`` block.

    :param condition: Branch condition, or ``None`` for the final ``else`` branch
    :type condition: Optional[Expr]
    :param statements: Statements executed when the branch is selected
    :type statements: List[OperationStatement]
    """

    condition: Optional[Expr]
    statements: List[OperationStatement]
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def to_ast_node(self) -> dsl_nodes.OperationIfBranch:
        """
        Convert this branch back to a DSL AST node.

        The private ``_span`` metadata is intentionally not copied. Exported
        AST nodes are for DSL serialization, not source-span round-tripping.

        :return: Operation-if branch AST node
        :rtype: dsl_nodes.OperationIfBranch
        """
        return dsl_nodes.OperationIfBranch(
            condition=self.condition.to_ast_node()
            if self.condition is not None
            else None,
            statements=[item.to_ast_node() for item in self.statements],
        )


@dataclass
class IfBlock(OperationStatement):
    """
    Represents an ``if / else if / else`` statement in a model operation block.

    :param branches: Ordered branch list
    :type branches: List[IfBlockBranch]
    """

    branches: List[IfBlockBranch]
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def to_ast_node(self) -> dsl_nodes.OperationIf:
        """
        Convert this if-block back to a DSL AST node.

        The private ``_span`` metadata is intentionally not copied. Exported
        AST nodes are for DSL serialization, not source-span round-tripping.

        :return: Operation-if AST node
        :rtype: dsl_nodes.OperationIf
        """
        return dsl_nodes.OperationIf(
            branches=[item.to_ast_node() for item in self.branches],
        )


@dataclass
class Event:
    """
    Represents an event that can trigger state transitions.

    An event has a name and is associated with a specific state path in the
    state machine hierarchy.

    :param name: The name of the event
    :type name: str
    :param state_path: The path to the state that owns this event
    :type state_path: Tuple[str, ...]
    :param extra_name: Optional extra name for display purposes
    :type extra_name: Optional[str]

    Example::

        >>> event = Event(name="button_pressed", state_path=("root", "idle"))
        >>> event.path
        ('root', 'idle', 'button_pressed')
    """

    name: str
    state_path: Tuple[str, ...]
    extra_name: Optional[str] = None
    declared: bool = field(default=False, compare=False)
    origins: List[str] = field(default_factory=list, compare=False)
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.origins = list(self.origins or (["declared"] if self.declared else []))

    @property
    def path(self) -> Tuple[str, ...]:
        """
        Get the full path of the event including the state path and event name.

        :return: The full path to the event
        :rtype: Tuple[str, ...]
        """
        return tuple((*self.state_path, self.name))

    @property
    def path_name(self) -> str:
        """
        Get the canonical dot-separated path string for this event.

        The returned string serves as the stable identifier used by the runtime
        for event indexing and transition matching. This format matches the
        fully-qualified event paths used in the DSL.

        Event paths follow the state hierarchy where the event is defined. For
        example, a local event ``Go`` defined in state ``System.Active`` would
        have the path ``System.Active.Go``.

        :return: Dot-separated event path matching the DSL structure
        :rtype: str

        Example::

            >>> event = Event(name="Start", state_path=("System", "Idle"))
            >>> event.path_name
            'System.Idle.Start'

        .. note::
           This property is used internally by :class:`SimulationRuntime` when
           building the event dictionary for transition matching. The returned
           string must be stable and unique within the state machine.
        """
        return ".".join(self.path)

    def to_ast_node(self) -> dsl_nodes.EventDefinition:
        """
        Convert this event to an AST node.

        :return: An event definition AST node
        :rtype: dsl_nodes.EventDefinition
        """
        return dsl_nodes.EventDefinition(
            name=self.name,
            extra_name=self.extra_name,
        )


@dataclass
class Transition(AstExportable):
    """
    Represents a transition between states in a state machine.

    A transition defines how the state machine moves from one state to another,
    potentially triggered by an event, guarded by a condition, and with effects
    that execute when the transition occurs.

    :param from_state: The source state name or special state marker
    :type from_state: Union[str, dsl_nodes._StateSingletonMark]
    :param to_state: The target state name or special state marker
    :type to_state: Union[str, dsl_nodes._StateSingletonMark]
    :param event: The event that triggers this transition, if any
    :type event: Optional[Event]
    :param guard: The condition that must be true for the transition to occur, if any
    :type guard: Optional[Expr]
    :param effects: Operation statements to execute when the transition occurs
    :type effects: List[OperationStatement]
    :param event_scope: Original DSL trigger scope for ``event`` when
        known. One of ``'local'``, ``'chain'``, or ``'absolute'``.
    :type event_scope: Optional[str]
    :param is_forced: Whether this transition was expanded from a forced
        transition declaration.
    :type is_forced: bool
    :param forced_origin: Original forced transition text when
        ``is_forced`` is true.
    :type forced_origin: Optional[str]
    :param combo_origin_refs: References from this generated transition back
        to original combo trigger terms.
    :type combo_origin_refs: Tuple[ComboOriginRef, ...]
    :param combo_projection_key: Logical chooser key used by combo projection
        snapshots.
    :type combo_projection_key: Optional[Tuple[object, ...]]
    :param combo_projection_order_key: Stable ordered-trie projection order key.
    :type combo_projection_order_key: Optional[Tuple[object, ...]]
    :param combo_reuse_group_id: Stable identifier explaining prefix sharing or
        non-sharing groups.
    :type combo_reuse_group_id: Optional[str]
    :param combo_priority_run_identity: Stable ordered-trie run identity as
        ``(run_anchor_origin_id, semantic_duplicate_discriminator)``.
    :type combo_priority_run_identity: Optional[Tuple[str, Optional[int]]]
    :param combo_priority_run_index: Preorder index of this generated edge
        within combo projection.
    :type combo_priority_run_index: Optional[int]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> transition = Transition(
        ...     from_state="idle",
        ...     to_state="active",
        ...     event=None,
        ...     guard=None,
        ...     effects=[]
        ... )
    """

    from_state: Union[str, dsl_nodes._StateSingletonMark]
    to_state: Union[str, dsl_nodes._StateSingletonMark]
    event: Optional[Event]
    guard: Optional[Expr]
    effects: List[OperationStatement]
    event_scope: Optional[str] = field(default=None, compare=False)
    is_forced: bool = field(default=False, compare=False)
    forced_origin: Optional[str] = field(default=None, compare=False)
    combo_origin_refs: Tuple[ComboOriginRef, ...] = field(
        default_factory=tuple, compare=False
    )
    combo_projection_key: Optional[Tuple[object, ...]] = field(
        default=None, compare=False
    )
    combo_projection_order_key: Optional[Tuple[object, ...]] = field(
        default=None, compare=False
    )
    combo_reuse_group_id: Optional[str] = field(default=None, compare=False)
    combo_priority_run_identity: Optional[Tuple[str, Optional[int]]] = field(
        default=None, compare=False
    )
    combo_priority_run_index: Optional[int] = field(default=None, compare=False)
    parent_ref: Optional[weakref.ReferenceType] = None
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    @property
    def parent(self) -> Optional["State"]:
        """
        Get the parent state of this transition.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional["State"]) -> None:
        """
        Set the parent state of this transition.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    def to_ast_node(self) -> dsl_nodes.TransitionDefinition:
        """
        Convert this transition to an AST node.

        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        return State.transition_to_ast_node(self.parent, self)


@dataclass
class OnStage(AstExportable):
    """
    Represents an action that occurs during a specific stage of a state's lifecycle.

    OnStage can represent enter, during, or exit actions, and can be either concrete
    operations or abstract function declarations.

    :param stage: The lifecycle stage ('enter', 'during', or 'exit')
    :type stage: str
    :param aspect: For 'during' actions in composite states, specifies if the action occurs 'before' or 'after' substates
    :type aspect: Optional[str]
    :param name: For abstract functions, the name of the function
    :type name: Optional[str]
    :param doc: For abstract functions, the documentation string
    :type doc: Optional[str]
    :param operations: For concrete actions, the list of operation statements to execute
    :type operations: List[OperationStatement]
    :param is_abstract: Whether this is an abstract function declaration
    :type is_abstract: bool
    :param state_path: The path to the state that owns this action
    :type state_path: Tuple[Optional[str], ...]
    :param ref: Reference to another OnStage or OnAspect for function references
    :type ref: Union['OnStage', 'OnAspect', None]
    :param ref_state_path: The path to the referenced state for function references
    :type ref_state_path: Optional[Tuple[str, ...]]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> on_enter = OnStage(
        ...     stage="enter",
        ...     aspect=None,
        ...     name="init_counter",
        ...     doc=None,
        ...     operations=[],
        ...     is_abstract=False,
        ...     state_path=("root", "init_counter")
        ... )
    """

    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[OperationStatement]
    is_abstract: bool
    state_path: Tuple[Optional[str], ...]
    ref: Union["OnStage", "OnAspect", None] = None
    ref_state_path: Optional[Tuple[str, ...]] = None
    parent_ref: Optional[weakref.ReferenceType] = None
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    @property
    def parent(self) -> Optional["State"]:
        """
        Get the parent state of this action.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None  # pragma: no cover
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional["State"]) -> None:
        """
        Set the parent state of this action.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_ref(self) -> bool:
        """
        Check if this action is a reference to another function.

        :return: True if this is a reference, False otherwise
        :rtype: bool
        """
        return bool(self.ref)

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: False for OnStage instances (always)
        :rtype: bool
        """
        return False

    @property
    def func_name(self) -> str:
        """
        Get the readable dot-separated path string for this action.

        The returned string represents the action's location in the state hierarchy,
        making it easy to identify which state owns the action in log messages and
        diagnostic output.

        Unnamed actions (where the name component is ``None``) are rendered with
        ``<unnamed>`` in the terminal position.

        :return: Dot-separated action path with state hierarchy
        :rtype: str

        Example::

            >>> # Named enter action
            >>> action.func_name
            'System.Active.Initialize'
            >>> # Unnamed during action
            >>> action.func_name
            'System.Active.<unnamed>'
        """
        sp = self.state_path
        if sp[-1] is None:
            sp = tuple((*sp[:-1], "<unnamed>"))
        return ".".join(sp)

    def to_ast_node(
        self,
    ) -> Union[
        dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement
    ]:
        """
        Convert this OnStage to an appropriate AST node based on the stage.

        :return: An enter, during, or exit statement AST node
        :rtype: Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]
        :raises ValueError: If the stage is not one of 'enter', 'during', or 'exit'
        """
        if self.stage == "enter":
            if self.is_abstract:
                return dsl_nodes.EnterAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[: len(spath)] == spath:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[len(spath) :]), is_absolute=False
                    )
                else:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[1:]), is_absolute=True
                    )
                return dsl_nodes.EnterRefFunction(name=self.name, ref=ref)
            else:
                return dsl_nodes.EnterOperations(
                    name=self.name,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == "during":
            if self.is_abstract:
                return dsl_nodes.DuringAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[: len(spath)] == spath:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[len(spath) :]), is_absolute=False
                    )
                else:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[1:]), is_absolute=True
                    )
                return dsl_nodes.DuringRefFunction(
                    name=self.name, aspect=self.aspect, ref=ref
                )
            else:
                return dsl_nodes.DuringOperations(
                    name=self.name,
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == "exit":
            if self.is_abstract:
                return dsl_nodes.ExitAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[: len(spath)] == spath:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[len(spath) :]), is_absolute=False
                    )
                else:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[1:]), is_absolute=True
                    )
                return dsl_nodes.ExitRefFunction(name=self.name, ref=ref)
            else:
                return dsl_nodes.ExitOperations(
                    name=self.name,
                    operations=[item.to_ast_node() for item in self.operations],
                )
        else:
            raise ValueError(f"Unknown stage - {self.stage!r}.")  # pragma: no cover


@dataclass
class OnAspect(AstExportable):
    """
    Represents an aspect-oriented action that occurs during a specific stage of a state's lifecycle.

    OnAspect is specifically used for aspect-oriented programming features in the state machine,
    allowing actions to be defined that apply across multiple states.

    :param stage: The lifecycle stage (currently only supports 'during')
    :type stage: str
    :param aspect: Specifies if the action occurs 'before' or 'after' substates
    :type aspect: Optional[str]
    :param name: For abstract functions, the name of the function
    :type name: Optional[str]
    :param doc: For abstract functions, the documentation string
    :type doc: Optional[str]
    :param operations: For concrete actions, the list of operation statements to execute
    :type operations: List[OperationStatement]
    :param is_abstract: Whether this is an abstract function declaration
    :type is_abstract: bool
    :param state_path: The path to the state that owns this action
    :type state_path: Tuple[Optional[str], ...]
    :param ref: Reference to another OnStage or OnAspect for function references
    :type ref: Union['OnStage', 'OnAspect', None]
    :param ref_state_path: The path to the referenced state for function references
    :type ref_state_path: Optional[Tuple[str, ...]]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> aspect = OnAspect(
        ...     stage="during",
        ...     aspect="before",
        ...     name="log_entry",
        ...     doc=None,
        ...     operations=[],
        ...     is_abstract=True,
        ...     state_path=("root", "log_entry")
        ... )
    """

    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[OperationStatement]
    is_abstract: bool
    state_path: Tuple[Optional[str], ...]
    ref: Union["OnStage", "OnAspect", None] = None
    ref_state_path: Optional[Tuple[str, ...]] = None
    parent_ref: Optional[weakref.ReferenceType] = None
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    @property
    def parent(self) -> Optional["State"]:
        """
        Get the parent state of this aspect action.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None  # pragma: no cover
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional["State"]) -> None:
        """
        Set the parent state of this aspect action.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_ref(self) -> bool:
        """
        Check if this action is a reference to another function.

        :return: True if this is a reference, False otherwise
        :rtype: bool
        """
        return bool(self.ref)

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: True for OnAspect instances (always)
        :rtype: bool
        """
        return True

    @property
    def func_name(self) -> str:
        """
        Get the readable dot-separated path string for this action.

        The returned string represents the action's location in the state hierarchy,
        making it easy to identify which state owns the action in log messages and
        diagnostic output.

        Unnamed actions (where the name component is ``None``) are rendered with
        ``<unnamed>`` in the terminal position.

        :return: Dot-separated action path with state hierarchy
        :rtype: str

        Example::

            >>> # Named aspect action
            >>> action.func_name
            'System.PreProcess'
            >>> # Unnamed aspect action
            >>> action.func_name
            'System.<unnamed>'
        """
        sp = self.state_path
        if sp[-1] is None:
            sp = tuple((*sp[:-1], "<unnamed>"))
        return ".".join(sp)

    def to_ast_node(self) -> Union[dsl_nodes.DuringAspectStatement]:
        """
        Convert this OnAspect to an appropriate AST node based on the stage.

        :return: A during aspect statement AST node
        :rtype: Union[dsl_nodes.DuringAspectStatement]
        :raises ValueError: If the stage is not 'during'
        """
        if self.stage == "during":
            if self.is_abstract:
                return dsl_nodes.DuringAspectAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[: len(spath)] == spath:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[len(spath) :]), is_absolute=False
                    )
                else:
                    ref = dsl_nodes.ChainID(
                        path=list(self.ref_state_path[1:]), is_absolute=True
                    )
                return dsl_nodes.DuringAspectRefFunction(
                    name=self.name, aspect=self.aspect, ref=ref
                )
            else:
                return dsl_nodes.DuringAspectOperations(
                    name=self.name,
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        else:
            raise ValueError(f"Unknown aspect - {self.stage!r}.")  # pragma: no cover


@dataclass
class State(AstExportable, PlantUMLExportable):
    """
    Represents a state in a hierarchical state machine.

    A state can contain substates, transitions between those substates, and actions
    that execute on enter, during, or exit of the state.

    :param name: The name of the state
    :type name: str
    :param path: The full path to this state in the hierarchy
    :type path: Tuple[str, ...]
    :param substates: Dictionary mapping substate names to State objects
    :type substates: Dict[str, 'State']
    :param events: Dictionary mapping event names to Event objects
    :type events: Dict[str, Event]
    :param transitions: List of transitions between substates
    :type transitions: List[Transition]
    :param named_functions: Dictionary mapping function names to their implementations
    :type named_functions: Dict[str, Union[OnStage, OnAspect]]
    :param on_enters: List of actions to execute when entering the state
    :type on_enters: List[OnStage]
    :param on_durings: List of actions to execute while in the state
    :type on_durings: List[OnStage]
    :param on_exits: List of actions to execute when exiting the state
    :type on_exits: List[OnStage]
    :param on_during_aspects: List of aspect-oriented actions for the during stage
    :type on_during_aspects: List[OnAspect]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]
    :param substate_name_to_id: Dictionary mapping substate names to numeric IDs
    :type substate_name_to_id: Dict[str, int]
    :param extra_name: Optional extra name for display purposes
    :type extra_name: Optional[str]
    :param is_pseudo: Whether this is a pseudo state
    :type is_pseudo: bool

    Example::

        >>> state = State(
        ...     name="idle",
        ...     path=("root", "idle"),
        ...     substates={}
        ... )
        >>> state.is_leaf_state
        True
    """

    name: str
    path: Tuple[str, ...]
    substates: Dict[str, "State"]
    events: Dict[str, Event] = None
    transitions: List[Transition] = None
    named_functions: Dict[str, Union[OnStage, OnAspect]] = None
    on_enters: List[OnStage] = None
    on_durings: List[OnStage] = None
    on_exits: List[OnStage] = None
    on_during_aspects: List[OnAspect] = None
    parent_ref: Optional[weakref.ReferenceType] = None
    substate_name_to_id: Dict[str, int] = None
    extra_name: Optional[str] = None
    is_pseudo: bool = False
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """
        Initialize default values for optional fields after instance creation.
        """
        self.events = self.events or {}
        self.transitions = self.transitions or []
        self.named_functions = self.named_functions or {}
        self.on_enters = self.on_enters or []
        self.on_durings = self.on_durings or []
        self.on_exits = self.on_exits or []
        self.on_during_aspects = self.on_during_aspects or []
        self.substate_name_to_id = {
            name: i for i, (name, _) in enumerate(self.substates.items())
        }

    @property
    def is_leaf_state(self) -> bool:
        """
        Check if this state is a leaf state (has no substates).

        :return: True if this is a leaf state, False otherwise
        :rtype: bool
        """
        return len(self.substates) == 0

    @property
    def is_stoppable(self) -> bool:
        """
        Check if this state is stoppable (is a leaf state and not pseudo).

        :return: True if this state is stoppable, False otherwise
        :rtype: bool
        """
        return self.is_leaf_state and not self.is_pseudo

    @property
    def parent(self) -> Optional["State"]:
        """
        Get the parent state of this state.

        :return: The parent state or None if this is the root state
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional["State"]) -> None:
        """
        Set the parent state of this state.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_root_state(self) -> bool:
        """
        Check if this state is the root state (has no parent).

        :return: True if this is the root state, False otherwise
        :rtype: bool
        """
        return self.parent is None

    @property
    def init_transitions(self) -> List[Transition]:
        """
        Get all transitions that start from the initial state (INIT_STATE).

        :return: List of transitions from INIT_STATE
        :rtype: List[Transition]
        """
        retval = []
        for transition in self.transitions:
            if transition.from_state == dsl_nodes.INIT_STATE:
                retval.append(transition)
        return retval

    @property
    def transitions_from(self) -> List[Transition]:
        """
        Get all transitions that start from this state.

        For non-root states, these are transitions in the parent state where this state
        is the source. For the root state, a synthetic transition to EXIT_STATE is returned.

        :return: List of transitions from this state
        :rtype: List[Transition]
        """
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.from_state == self.name:
                    retval.append(transition)
        else:
            retval.append(
                Transition(
                    from_state=self.name,
                    to_state=EXIT_STATE,
                    event=None,
                    guard=None,
                    effects=[],
                    parent_ref=self.parent_ref,
                )
            )
        return retval

    @property
    def transitions_to(self) -> List[Transition]:
        """
        Get all transitions that end at this state.

        For non-root states, these are transitions in the parent state where this state
        is the target. For the root state, a synthetic transition from INIT_STATE is returned.

        :return: List of transitions to this state
        :rtype: List[Transition]
        """
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.to_state == self.name:
                    retval.append(transition)
        else:
            retval.append(
                Transition(
                    from_state=INIT_STATE,
                    to_state=self.name,
                    event=None,
                    guard=None,
                    effects=[],
                    parent_ref=self.parent_ref,
                )
            )

        return retval

    @property
    def transitions_entering_children(self) -> List[Transition]:
        """
        Get all transitions that start from the initial state (INIT_STATE).

        These are the transitions that define the initial substate when entering this state.

        :return: List of transitions from INIT_STATE
        :rtype: List[Transition]
        """
        return [
            transition
            for transition in self.transitions
            if transition.from_state is INIT_STATE
        ]

    @property
    def transitions_entering_children_simplified(self) -> List[Optional[Transition]]:
        """
        Get a simplified list of transitions entering child states.

        If there's a default transition (no event or guard), only include that one.
        Otherwise include all transitions and add None at the end.

        :return: List of transitions, possibly with None at the end
        :rtype: List[Optional[Transition]]
        """
        retval = []
        for transition in self.transitions:
            if transition.from_state is INIT_STATE:
                retval.append(transition)
                if transition.event is None and transition.guard is None:
                    break
        if not retval or (
            retval and not (retval[-1].event is None and retval[-1].guard is None)
        ):
            retval.append(None)
        return retval

    def list_on_enters(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of enter actions, optionally filtered by abstract status and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of enter actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_enters, 1):
            if is_abstract is not None and (
                (item.is_abstract and not is_abstract)
                or (not item.is_abstract and is_abstract)
            ):
                continue
            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_enters(self) -> List[OnStage]:
        """
        Get all abstract enter actions.

        :return: List of abstract enter actions
        :rtype: List[OnStage]
        """
        return self.list_on_enters(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_enters(self) -> List[OnStage]:
        """
        Get all non-abstract enter actions.

        :return: List of non-abstract enter actions
        :rtype: List[OnStage]
        """
        return self.list_on_enters(is_abstract=False, with_ids=False)

    def list_on_durings(
        self,
        is_abstract: Optional[bool] = None,
        aspect: Optional[str] = None,
        with_ids: bool = False,
    ) -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of during actions, optionally filtered by abstract status, aspect, and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param aspect: If provided, filter to only actions with the given aspect ('before' or 'after')
        :type aspect: Optional[str]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_durings, 1):
            if is_abstract is not None and (
                (item.is_abstract and not is_abstract)
                or (not item.is_abstract and is_abstract)
            ):
                continue
            if aspect is not None and item.aspect != aspect:
                continue

            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_durings(self) -> List[OnStage]:
        """
        Get all abstract during actions.

        :return: List of abstract during actions
        :rtype: List[OnStage]
        """
        return self.list_on_durings(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_durings(self) -> List[OnStage]:
        """
        Get all non-abstract during actions.

        :return: List of non-abstract during actions
        :rtype: List[OnStage]
        """
        return self.list_on_durings(is_abstract=False, with_ids=False)

    def list_on_exits(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of exit actions, optionally filtered by abstract status and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of exit actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_exits, 1):
            if is_abstract is not None and (
                (item.is_abstract and not is_abstract)
                or (not item.is_abstract and is_abstract)
            ):
                continue
            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_exits(self) -> List[OnStage]:
        """
        Get all abstract exit actions.

        :return: List of abstract exit actions
        :rtype: List[OnStage]
        """
        return self.list_on_exits(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_exits(self) -> List[OnStage]:
        """
        Get all non-abstract exit actions.

        :return: List of non-abstract exit actions
        :rtype: List[OnStage]
        """
        return self.list_on_exits(is_abstract=False, with_ids=False)

    def list_on_during_aspects(
        self,
        is_abstract: Optional[bool] = None,
        aspect: Optional[str] = None,
        with_ids: bool = False,
    ) -> List[Union[Tuple[int, OnAspect], OnAspect]]:
        """
        Get a list of during aspect actions, optionally filtered by abstract status, aspect, and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param aspect: If provided, filter to only actions with the given aspect ('before' or 'after')
        :type aspect: Optional[str]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during aspect actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnAspect], OnAspect]]
        """
        retval = []
        for id_, item in enumerate(self.on_during_aspects, 1):
            if is_abstract is not None and (
                (item.is_abstract and not is_abstract)
                or (not item.is_abstract and is_abstract)
            ):
                continue
            if aspect is not None and item.aspect != aspect:
                continue

            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_during_aspects(self) -> List[OnAspect]:
        """
        Get all abstract during aspect actions.

        :return: List of abstract during aspect actions
        :rtype: List[OnAspect]
        """
        return self.list_on_during_aspects(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_during_aspects(self) -> List[OnAspect]:
        """
        Get all non-abstract during aspect actions.

        :return: List of non-abstract during aspect actions
        :rtype: List[OnAspect]
        """
        return self.list_on_during_aspects(is_abstract=False, with_ids=False)

    def iter_on_during_before_aspect_recursively(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> Iterator[
        Union[
            Tuple[int, "State", Union[OnAspect, OnStage]],
            Tuple["State", Union[OnAspect, OnStage]],
        ]
    ]:
        """
        Recursively iterate through 'before' aspect during actions from parent states to this state.

        This method traverses the state hierarchy from the root state to this state,
        yielding all 'before' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if self.parent is not None:
            yield from self.parent.iter_on_during_before_aspect_recursively(
                is_abstract=is_abstract, with_ids=with_ids
            )
        if with_ids:
            for id_, item in self.list_on_during_aspects(
                is_abstract=is_abstract, aspect="before", with_ids=with_ids
            ):
                yield id_, self, item
        else:
            for item in self.list_on_during_aspects(
                is_abstract=is_abstract, aspect="before", with_ids=with_ids
            ):
                yield self, item

    def iter_on_during_after_aspect_recursively(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> Iterator[
        Union[
            Tuple[int, "State", Union[OnAspect, OnStage]],
            Tuple["State", Union[OnAspect, OnStage]],
        ]
    ]:
        """
        Recursively iterate through 'after' aspect during actions from this state to the root state.

        This method traverses the state hierarchy from this state to the root state,
        yielding all 'after' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if with_ids:
            for id_, item in self.list_on_during_aspects(
                is_abstract=is_abstract, aspect="after", with_ids=with_ids
            ):
                yield id_, self, item
        else:
            for item in self.list_on_during_aspects(
                is_abstract=is_abstract, aspect="after", with_ids=with_ids
            ):
                yield self, item
        if self.parent is not None:
            yield from self.parent.iter_on_during_after_aspect_recursively(
                is_abstract=is_abstract, with_ids=with_ids
            )

    def iter_on_during_aspect_recursively(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> Iterator[
        Union[
            Tuple[int, "State", Union[OnAspect, OnStage]],
            Tuple["State", Union[OnAspect, OnStage]],
        ]
    ]:
        """
        Recursively iterate through all during actions in the proper execution order.

        This method yields actions in the following order:

        1. 'Before' aspect actions from root state to this state
        2. Regular during actions for this state
        3. 'After' aspect actions from this state to root state

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if not self.is_pseudo:
            yield from self.iter_on_during_before_aspect_recursively(
                is_abstract=is_abstract, with_ids=with_ids
            )
        if with_ids:
            for id_, item in self.list_on_durings(
                is_abstract=is_abstract, aspect=None, with_ids=with_ids
            ):
                yield id_, self, item
        else:
            for item in self.list_on_durings(
                is_abstract=is_abstract, aspect=None, with_ids=with_ids
            ):
                yield self, item
        if not self.is_pseudo:
            yield from self.iter_on_during_after_aspect_recursively(
                is_abstract=is_abstract, with_ids=with_ids
            )

    def list_on_during_aspect_recursively(
        self, is_abstract: Optional[bool] = None, with_ids: bool = False
    ) -> List[
        Union[
            Tuple[int, "State", Union[OnAspect, OnStage]],
            Tuple["State", Union[OnAspect, OnStage]],
        ]
    ]:
        """
        Get a list of all during actions in the proper execution order.

        This is a convenience method that collects the results of iter_on_during_aspect_recursively.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during actions in execution order
        :rtype: List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        return list(self.iter_on_during_aspect_recursively(is_abstract, with_ids))

    @classmethod
    def transition_to_ast_node(
        cls, self: Optional["State"], transition: Transition
    ) -> dsl_nodes.TransitionDefinition:
        """
        Convert a transition to an AST node, considering the context of its parent state.

        :param self: The parent state, or None
        :type self: Optional['State']
        :param transition: The transition to convert
        :type transition: Transition
        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        if self:
            cur_path = self.path
        else:
            cur_path = ()

        if transition.event:
            if (
                len(transition.event.path) > len(cur_path)
                and transition.event.path[: len(cur_path)] == cur_path
            ):
                event_id = dsl_nodes.ChainID(
                    path=list(transition.event.path[len(cur_path) :]), is_absolute=False
                )
            else:
                event_id = dsl_nodes.ChainID(
                    path=list(transition.event.path[1:]), is_absolute=True
                )
        else:
            event_id = None

        return dsl_nodes.TransitionDefinition(
            from_state=transition.from_state,
            to_state=transition.to_state,
            event_id=event_id,
            condition_expr=transition.guard.to_ast_node()
            if transition.guard is not None
            else None,
            post_operations=[item.to_ast_node() for item in transition.effects],
        )

    def to_transition_ast_node(
        self, transition: Transition
    ) -> dsl_nodes.TransitionDefinition:
        """
        Convert a transition to an AST node in the context of this state.

        :param transition: The transition to convert
        :type transition: Transition
        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        return self.transition_to_ast_node(self, transition)

    def to_ast_node(self) -> dsl_nodes.StateDefinition:
        """
        Convert this state to an AST node.

        :return: A state definition AST node
        :rtype: dsl_nodes.StateDefinition
        """
        node = dsl_nodes.StateDefinition(
            name=self.name,
            extra_name=self.extra_name,
            events=[event.to_ast_node() for _, event in self.events.items()],
            substates=[
                substate.to_ast_node() for _, substate in self.substates.items()
            ],
            transitions=[
                self.to_transition_ast_node(trans) for trans in self.transitions
            ],
            enters=[item.to_ast_node() for item in self.on_enters],
            durings=[item.to_ast_node() for item in self.on_durings],
            exits=[item.to_ast_node() for item in self.on_exits],
            during_aspects=[item.to_ast_node() for item in self.on_during_aspects],
            is_pseudo=bool(self.is_pseudo),
        )
        if (
            self.is_pseudo
            and self.name.startswith(_COMBO_STATE_PREFIX)
            and getattr(self, "_generated_combo_pseudo", False)
        ):
            node._generated_combo_pseudo = True
        return node

    def to_plantuml(
        self,
        options: PlantUMLOptionsInput = None,
        current_depth: int = 0,
        event_colors: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Convert this state to PlantUML notation.

        :param options: Configuration input for PlantUML generation
        :type options: PlantUMLOptionsInput
        :param current_depth: Current depth in the state hierarchy (for max_depth support)
        :type current_depth: int
        :param event_colors: Optional mapping of event paths to color codes
        :type event_colors: Optional[Dict[str, str]]
        :return: PlantUML representation of the state
        :rtype: str
        """
        # Resolve configuration
        options = PlantUMLOptions.from_value(options)
        config = options.to_config()

        if event_colors is None:
            event_colors = {}

        def _name_safe(sub_state: Optional[str] = None) -> str:
            subpath = [*self.path]
            if sub_state is not None:
                subpath.append(sub_state)
            return sequence_safe(subpath)

        # Check if this is an empty state (for collapse_empty_states)
        is_empty_state = (
            not self.on_enters
            and not self.on_durings
            and not self.on_exits
            and not self.on_during_aspects
        )

        state_style_marks = []
        if self.is_pseudo and config.show_pseudo_state_style:
            state_style_marks.append("line.dotted")
        state_style_mark_str = (
            " #" + ";".join(state_style_marks) if state_style_marks else ""
        )

        # Build stereotype string
        stereotype_parts = []
        if config.use_stereotypes:
            if self.is_pseudo:
                stereotype_parts.append("pseudo")
            if not self.is_leaf_state:
                stereotype_parts.append("composite")
        stereotype_str = (
            f" <<{','.join(stereotype_parts)}>>" if stereotype_parts else ""
        )

        with io.StringIO() as sf:
            # Format state name according to configuration
            shown_name = format_state_name(self, config.state_name_format)

            print(
                f"state {json.dumps(shown_name, ensure_ascii=False)} as {_name_safe()}{stereotype_str}{state_style_mark_str}",
                file=sf,
                end="",
            )

            if not self.is_leaf_state:
                print(" {", file=sf)

                # Check if we should expand substates or collapse them
                should_expand_substates = (
                    config.max_depth is None or current_depth < config.max_depth
                )

                if should_expand_substates:
                    # Expand substates normally
                    for state in self.substates.values():
                        print(
                            indent(
                                state.to_plantuml(
                                    options,
                                    current_depth=current_depth + 1,
                                    event_colors=event_colors,
                                ),
                                prefix="    ",
                            ),
                            file=sf,
                        )
                else:
                    # Collapsed: show marker state
                    marker_name = config.collapsed_state_marker
                    marker_safe_name = sequence_safe([*self.path, "__collapsed__"])
                    print(
                        f"    state {json.dumps(marker_name, ensure_ascii=False)} as {marker_safe_name}",
                        file=sf,
                    )

                for trans in self.transitions:
                    with io.StringIO() as tf:
                        print(
                            "[*]"
                            if trans.from_state is dsl_nodes.INIT_STATE
                            else _name_safe(trans.from_state),
                            file=tf,
                            end="",
                        )

                        # Apply event_visualization_mode colors to arrow
                        arrow_str = " -->"
                        if (
                            config.event_visualization_mode in ("color", "both")
                            and trans.event is not None
                        ):
                            event_path = ".".join(trans.event.path)
                            if event_path in event_colors:
                                color = event_colors[event_path]
                                arrow_str = f" -[{color}]->"

                        print(arrow_str, file=tf, end=" ")
                        print(
                            "[*]"
                            if trans.to_state is dsl_nodes.EXIT_STATE
                            else _name_safe(trans.to_state),
                            file=tf,
                            end="",
                        )

                        trans_node: dsl_nodes.TransitionDefinition = trans.to_ast_node()

                        # Show event if enabled
                        if config.show_events and trans.event is not None:
                            from .plantuml import format_event_name

                            formatted_event = format_event_name(
                                trans.event,
                                config.event_name_format,
                                trans_node=trans_node,
                            )
                            print(f" : {formatted_event}", file=tf, end="")
                        elif config.show_transition_guards and trans.guard is not None:
                            print(f" : {trans.guard.to_ast_node()}", file=tf, end="")

                        # Show transition effects if enabled
                        if config.show_transition_effects and len(trans.effects) > 0:
                            if config.transition_effect_mode == "note":
                                print("", file=tf)
                                print("note on link", file=tf)
                                print("effect {", file=tf)
                                for operation in trans.effects:
                                    print(f"    {operation.to_ast_node()}", file=tf)
                                print("}", file=tf)
                                print("end note", file=tf, end="")
                            elif config.transition_effect_mode == "inline":
                                # Display effects inline on the transition arrow
                                effect_strs = [
                                    str(operation.to_ast_node())
                                    for operation in trans.effects
                                ]
                                effect_text = "; ".join(effect_strs)
                                # Append to existing label or create new one
                                print(f" / {effect_text}", file=tf, end="")

                        trans_text = tf.getvalue()
                    print(indent(trans_text, prefix="    "), file=sf)

                print("}", file=sf, end="")

            # Show lifecycle actions if enabled (skip if collapse_empty_states is True and state is empty)
            should_show_actions = not (
                config.collapse_empty_states and is_empty_state
            ) and (
                (
                    config.show_lifecycle_actions
                    and config.show_enter_actions
                    and self.on_enters
                )
                or (
                    config.show_lifecycle_actions
                    and config.show_during_actions
                    and self.on_durings
                )
                or (
                    config.show_lifecycle_actions
                    and config.show_exit_actions
                    and self.on_exits
                )
                or (
                    config.show_lifecycle_actions
                    and config.show_aspect_actions
                    and self.on_during_aspects
                )
            )

            if should_show_actions:
                from .plantuml import should_show_action, format_action_text

                print("", file=sf)
                with io.StringIO() as tf:
                    if config.show_enter_actions:
                        for enter_item in self.on_enters:
                            # Apply abstract/concrete filtering
                            if should_show_action(enter_item, config):
                                formatted_text = format_action_text(enter_item, config)
                                print(formatted_text, file=tf)
                    if config.show_during_actions:
                        for during_item in self.on_durings:
                            if should_show_action(during_item, config):
                                formatted_text = format_action_text(during_item, config)
                                print(formatted_text, file=tf)
                    if config.show_exit_actions:
                        for exit_item in self.on_exits:
                            if should_show_action(exit_item, config):
                                formatted_text = format_action_text(exit_item, config)
                                print(formatted_text, file=tf)
                    if config.show_aspect_actions:
                        for during_aspect_item in self.on_during_aspects:
                            if should_show_action(during_aspect_item, config):
                                formatted_text = format_action_text(
                                    during_aspect_item, config
                                )
                                print(formatted_text, file=tf)

                    action_text = (
                        tf.getvalue().rstrip().replace("\r\n", "\n").replace("\r", "\n")
                    )
                    if action_text:  # Only show if there's actual content
                        text = json.dumps(action_text).strip('"')
                        print(f"{_name_safe()} : {text}", file=sf, end="")

            return sf.getvalue()

    def walk_states(self) -> Iterator["State"]:
        """
        Iterate through this state and all its substates recursively.

        :yield: Each state in the hierarchy, starting with this one
        :rtype: Iterator['State']
        """
        yield self
        for _, substate in self.substates.items():
            yield from substate.walk_states()

    def resolve_event(
        self,
        event_ref: str,
        *,
        collect_into: Optional[DiagnosticSink] = None,
    ) -> Optional[Event]:
        """
        Resolve an event reference string to an existing Event object in the state hierarchy.

        This method supports three types of event references:

        1. **Relative events** (e.g., ``"xxx.yyy.zzz"``): Resolved relative to the current state's path.
           If the current state is ``XXX.YYY``, the event resolves to ``XXX.YYY.xxx.yyy.zzz``.

        2. **Parent-relative events** (e.g., ``".xxx.yyy.zzz"``): Each leading dot represents moving up
           one level in the state hierarchy. If the current state is ``XXX.YYY.ZZZ``, then ``.xxx``
           resolves to ``XXX.YYY.xxx`` (up one level), and ``..xxx`` resolves to ``XXX.xxx`` (up two levels).

        3. **Absolute events** (e.g., ``"/xxx.yyy"``): Resolved relative to the root state.
           If the root state is ``Root``, the event resolves to ``Root.xxx.yyy``.

        :param event_ref: The event reference string to resolve
        :type event_ref: str
        :param collect_into: Optional structured-diagnostic sink. Behavior
            depends on which sink mode the caller picked:

            * ``None`` (the default) — raise :class:`ModelValueError` or
              :class:`ModelLookupError` immediately on failure. Both
              multi-inherit ``ValueError`` / ``LookupError`` for backwards
              compatibility with existing ``except ValueError:`` /
              ``except LookupError:`` callers.
            * ``DiagnosticSink(collect=True)`` — record the failure as a
              :class:`pyfcstm.utils.validate.ModelDiagnostic` on the sink
              and return ``None`` instead of raising. Lets callers
              accumulate multiple diagnostics across many invocations in
              a single pass (IDE / agent loop usage).
            * ``DiagnosticSink(collect=False)`` (strict sink) — also
              raise, but route the diagnostic through the sink first so
              any previously accumulated entries (e.g. warnings) are
              carried into the raise. The raise still uses the typed
              :class:`ModelValueError` / :class:`ModelLookupError`
              subclass, preserving the legacy catch surface.
        :type collect_into: pyfcstm.diagnostics.DiagnosticSink, optional
        :return: The resolved Event object from the state hierarchy, or
            ``None`` when ``collect_into`` is a ``collect=True`` sink and
            resolution failed.
        :rtype: Optional[Event]
        :raises pyfcstm.utils.validate.ModelValueError: If the event
            reference is syntactically invalid (empty, malformed, exceeds
            root). Multi-inherits :class:`ValueError`. Raised when
            ``collect_into`` is ``None`` or a strict sink.
        :raises pyfcstm.utils.validate.ModelLookupError: If the event
            reference parses but the targeted state or event does not
            exist. Multi-inherits :class:`LookupError`. Raised when
            ``collect_into`` is ``None`` or a strict sink.

        Example::

            >>> # Assuming current state path is ("Root", "System", "Active")
            >>> # and an event "critical" exists in state "Root.System.Active.error"
            >>> state.resolve_event("error.critical")
            Event(name="critical", state_path=("Root", "System", "Active", "error"))

            >>> state.resolve_event(".error.critical")
            Event(name="critical", state_path=("Root", "System", "error"))

            >>> state.resolve_event("/global.shutdown")
            Event(name="shutdown", state_path=("Root", "global"))
        """
        # Determine the resolution scope from the lexical form of the reference.
        # This is used both for the structured ``refs.scope`` field on
        # ``E_EVENT_NOT_FOUND`` and to keep the legacy error message text
        # accurate for the parent-relative branch ("chain") versus the bare
        # relative form ("local"). The empty-ref case has no meaningful
        # scope yet — we default to ``'local'`` for refs purposes.
        if not event_ref:
            scope = "local"
        elif event_ref.startswith("/"):
            scope = "absolute"
        elif event_ref.startswith("."):
            scope = "chain"
        else:
            scope = "local"

        def _fail_invalid(reason: str, message: str) -> None:
            _emit_or_raise(
                collect_into,
                ModelDiagnostic(
                    code="E_EVENT_REF_INVALID",
                    severity="error",
                    message=message,
                    refs={"event_ref": event_ref, "reason": reason},
                ),
                exc_cls=ModelValueError,
            )

        def _fail_not_found(message: str, searched_from: Optional[str] = None) -> None:
            _emit_or_raise(
                collect_into,
                ModelDiagnostic(
                    code="E_EVENT_NOT_FOUND",
                    severity="error",
                    message=message,
                    refs={
                        "event_ref": event_ref,
                        "scope": scope,
                        "searched_from": searched_from,
                    },
                ),
                exc_cls=ModelLookupError,
            )

        if not event_ref:
            _fail_invalid("empty", "Event reference cannot be empty")
            return None

        # Determine the target state path and event name based on reference type
        target_state_path = None
        event_name = None

        # Handle absolute events (starting with '/')
        if event_ref.startswith("/"):
            # Remove leading '/' and resolve from root
            relative_path = event_ref[1:]
            if not relative_path:
                _fail_invalid(
                    "bare_slash", "Absolute event reference cannot be just '/'"
                )
                return None

            # Find root state
            root_state = self
            while root_state.parent is not None:
                root_state = root_state.parent

            # Split the path
            path_parts = relative_path.split(".")
            if not all(path_parts):
                _fail_invalid(
                    "invalid_absolute",
                    f"Invalid absolute event reference: {event_ref!r}",
                )
                return None

            event_name = path_parts[-1]
            target_state_path = root_state.path + tuple(path_parts[:-1])

        # Handle parent-relative events (starting with '.')
        elif event_ref.startswith("."):
            # Count leading dots
            dot_count = 0
            for char in event_ref:
                if char == ".":
                    dot_count += 1
                else:
                    break

            # Get the remaining path after dots
            remaining_path = event_ref[dot_count:]
            if not remaining_path:
                _fail_invalid(
                    "trailing_dots",
                    f"Parent-relative event reference cannot end with dots: {event_ref!r}",
                )
                return None

            # I2 from PR-112 review: validate the remaining dotted path
            # BEFORE walking up the hierarchy. Otherwise a malformed tail
            # like ``.foo..bar`` reports ``reason='beyond_root'`` when
            # called from the root (walk exhausts first) but
            # ``reason='invalid_relative'`` from a deeper state (walk
            # succeeds, then split fails). ``reason`` is a schema-backed
            # enum contract field — the same syntax error must produce
            # the same reason regardless of caller depth.
            path_parts = remaining_path.split(".")
            if not all(path_parts):
                _fail_invalid(
                    "invalid_relative",
                    f"Invalid parent-relative event reference: {event_ref!r}",
                )
                return None

            # Move up the hierarchy (now safe — syntax already validated)
            current_state = self
            for _ in range(dot_count):
                if current_state.parent is None:
                    _fail_invalid(
                        "beyond_root",
                        f"Parent-relative event reference {event_ref!r} goes beyond root state "
                        f"(current state: {'.'.join(self.path)}, tried to go up {dot_count} levels)",
                    )
                    return None
                current_state = current_state.parent

            event_name = path_parts[-1]
            target_state_path = current_state.path + tuple(path_parts[:-1])

        # Handle relative events (no leading '/' or '.')
        else:
            path_parts = event_ref.split(".")
            if not all(path_parts):
                _fail_invalid(
                    "invalid_relative",
                    f"Invalid relative event reference: {event_ref!r}",
                )
                return None

            event_name = path_parts[-1]
            target_state_path = self.path + tuple(path_parts[:-1])

        # Now find the state and retrieve the event
        # First, find the root state
        root_state = self
        while root_state.parent is not None:
            root_state = root_state.parent

        # Navigate to the target state
        current_state = root_state
        for i, state_name in enumerate(target_state_path[1:], 1):  # Skip root name
            if state_name not in current_state.substates:
                _fail_not_found(
                    f"State {'.'.join(target_state_path[: i + 1])!r} not found in hierarchy "
                    f"while resolving event reference {event_ref!r}",
                    searched_from=".".join(self.path),
                )
                return None
            current_state = current_state.substates[state_name]

        # Look for the event in the target state
        if event_name not in current_state.events:
            _fail_not_found(
                f"Event {event_name!r} not found in state {'.'.join(target_state_path)!r} "
                f"while resolving event reference {event_ref!r}",
                searched_from=".".join(self.path),
            )
            return None

        return current_state.events[event_name]


@dataclass
class VarDefine(AstExportable):
    """
    Represents a variable definition in a state machine.

    :param name: The name of the variable
    :type name: str
    :param type: The type of the variable
    :type type: str
    :param init: The initial value expression
    :type init: Expr

    Example::

        >>> var_def = VarDefine(name="counter", type="int", init=some_expr)
        >>> var_def.name
        'counter'
    """

    name: str
    type: str
    init: Expr
    _span: Optional[Span] = field(default=None, repr=False, compare=False)

    def to_ast_node(self) -> dsl_nodes.DefAssignment:
        """
        Convert this variable definition to an AST node.

        :return: A definition assignment AST node
        :rtype: dsl_nodes.DefAssignment
        """
        return dsl_nodes.DefAssignment(
            name=self.name,
            type=self.type,
            expr=self.init.to_ast_node(),
        )

    def name_ast_node(self) -> dsl_nodes.Name:
        """
        Convert the variable name to an AST node.

        :return: A name AST node
        :rtype: dsl_nodes.Name
        """
        return dsl_nodes.Name(self.name)


@dataclass
class StateMachine(AstExportable, PlantUMLExportable):
    """
    Represents a complete state machine with variable definitions and a root state.

    :param defines: Dictionary mapping variable names to their definitions
    :type defines: Dict[str, VarDefine]
    :param root_state: The root state of the state machine
    :type root_state: State

    Example::

        >>> sm = StateMachine(defines={}, root_state=some_state)
        >>> list(sm.walk_states())  # Get all states in the machine
        [...]
    """

    defines: Dict[str, VarDefine]
    root_state: State
    forced_transitions: Tuple[Dict[str, object], ...] = field(default_factory=tuple)

    def to_ast_node(self) -> dsl_nodes.StateMachineDSLProgram:
        """
        Convert this state machine to an AST node.

        :return: A state machine DSL program AST node
        :rtype: dsl_nodes.StateMachineDSLProgram
        """
        return dsl_nodes.StateMachineDSLProgram(
            definitions=[
                def_item.to_ast_node() for _, def_item in self.defines.items()
            ],
            root_state=self.root_state.to_ast_node(),
        )

    def to_plantuml(self, options: PlantUMLOptionsInput = None) -> str:
        """
        Convert this state machine to PlantUML notation.

        :param options: Configuration input for PlantUML generation
        :type options: PlantUMLOptionsInput
        :return: PlantUML representation of the state machine
        :rtype: str
        """
        # Resolve configuration
        options = PlantUMLOptions.from_value(options)
        config = options.to_config()

        with io.StringIO() as sf:
            print("@startuml", file=sf)
            print("hide empty description", file=sf)

            # Add skinparam styling if enabled
            if config.use_skinparam:
                print("", file=sf)
                print("skinparam state {", file=sf)
                print("  BackgroundColor<<pseudo>> LightGray", file=sf)
                print("  BackgroundColor<<composite>> LightBlue", file=sf)
                print("  BorderColor<<pseudo>> Gray", file=sf)
                print("  FontStyle<<pseudo>> italic", file=sf)
                print("}", file=sf)
                print("", file=sf)

            # Show variable definitions if enabled
            if config.show_variable_definitions and self.defines:
                if config.variable_display_mode == "note":
                    print("note as DefinitionNote", file=sf)
                    print("defines {", file=sf)
                    for def_item in self.defines.values():
                        print(f"    {def_item.to_ast_node()}", file=sf)
                    print("}", file=sf)
                    print("end note", file=sf)
                    print("", file=sf)
                elif config.variable_display_mode == "legend":
                    # Display variables as a legend
                    from .plantuml import escape_plantuml_table_cell

                    # Use configured legend position
                    print(f"legend {config.variable_legend_position}", file=sf)
                    # Header row
                    print("|= Variable |= Type |= Initial Value |", file=sf)
                    for def_item in self.defines.values():
                        var_name = def_item.name
                        var_type = def_item.type
                        var_init = (
                            def_item.init.to_ast_node() if def_item.init else "N/A"
                        )
                        # Escape pipe characters in the initial value
                        var_init_escaped = escape_plantuml_table_cell(str(var_init))
                        # All columns left-aligned
                        print(
                            f"| {var_name} | {var_type} | {var_init_escaped} |", file=sf
                        )
                    print("endlegend", file=sf)
                    print("", file=sf)

            # Collect events and assign colors if event visualization is enabled
            event_colors = {}
            event_map = {}
            if config.event_visualization_mode != "none":
                from .plantuml import collect_event_transitions, assign_event_colors

                event_map = collect_event_transitions(self)
                event_colors = assign_event_colors(event_map, config.custom_colors)

            # Add event legend if event_visualization_mode is 'legend' or 'both'
            if config.event_visualization_mode in ("legend", "both") and event_map:
                print(f"legend {config.event_legend_position}", file=sf)
                print("**Event Scoping**", file=sf)
                print("----", file=sf)
                for event_path in sorted(event_map.keys()):
                    transitions = event_map[event_path]
                    color = event_colors.get(event_path, "#000000")
                    # Show event name and count
                    event_name = event_path.split(".")[-1]
                    print(
                        f"<color:{color}>■</color> **{event_name}** ({len(transitions)} transitions)",
                        file=sf,
                    )
                    # Show event path
                    print(
                        f"  <size:10><color:gray>/{'.'.join(event_path.split('.')[1:])}</color></size>",
                        file=sf,
                    )
                print("endlegend", file=sf)
                print("", file=sf)

            print(
                self.root_state.to_plantuml(options, event_colors=event_colors), file=sf
            )
            print(f"[*] --> {sequence_safe(self.root_state.path)}", file=sf)
            print(f"{sequence_safe(self.root_state.path)} --> [*]", file=sf)
            print("@enduml", file=sf, end="")
            return sf.getvalue()

    def walk_states(self) -> Iterator[State]:
        """
        Iterate through all states in the state machine.

        :yield: Each state in the hierarchy
        :rtype: Iterator[State]
        """
        yield from self.root_state.walk_states()

    def resolve_event(
        self,
        event_path: str,
        *,
        collect_into: Optional[DiagnosticSink] = None,
    ) -> Optional[Event]:
        """
        Resolve a full event path to an existing Event object in the state machine.

        This method requires a complete event path in the format ``State1.State2.State3.event_name``,
        where the path must include all states from the root to the event location. Unlike
        :meth:`State.resolve_event`, this method does not support relative, parent-relative,
        or absolute path notations (no leading dots or slashes).

        :param event_path: The complete event path (e.g., ``"Root.System.Active.error"``)
        :type event_path: str
        :param collect_into: Optional structured-diagnostic sink. Behavior
            depends on the sink mode (see :meth:`State.resolve_event` for
            the full matrix):

            * ``None`` — raise :class:`ModelValueError` /
              :class:`ModelLookupError` immediately.
            * ``DiagnosticSink(collect=True)`` — accumulate on the sink
              and return ``None``.
            * ``DiagnosticSink(collect=False)`` (strict) — also raise the
              typed subclass, but route through the sink first so any
              previously accumulated entries are preserved into the raise.
        :type collect_into: pyfcstm.diagnostics.DiagnosticSink, optional
        :return: The resolved Event object, or ``None`` when
            ``collect_into`` is a ``collect=True`` sink and resolution
            failed.
        :rtype: Optional[Event]
        :raises pyfcstm.utils.validate.ModelValueError: If the event path
            is invalid or empty (multi-inherits :class:`ValueError`).
            Raised when ``collect_into`` is ``None`` or strict.
        :raises pyfcstm.utils.validate.ModelLookupError: If any state in
            the path or the event does not exist (multi-inherits
            :class:`LookupError`). Raised when ``collect_into`` is
            ``None`` or strict.

        Example::

            >>> # Assuming a state machine with Root -> System -> Active -> error event
            >>> sm = StateMachine(defines={}, root_state=root_state)
            >>> event = sm.resolve_event("Root.System.Active.error")
            >>> event.name
            'error'
        """

        def _fail_invalid(reason: str, message: str) -> None:
            _emit_or_raise(
                collect_into,
                ModelDiagnostic(
                    code="E_EVENT_REF_INVALID",
                    severity="error",
                    message=message,
                    refs={"event_ref": event_path, "reason": reason},
                ),
                exc_cls=ModelValueError,
            )

        def _fail_not_found(message: str, searched_from: Optional[str] = None) -> None:
            _emit_or_raise(
                collect_into,
                ModelDiagnostic(
                    code="E_EVENT_NOT_FOUND",
                    severity="error",
                    message=message,
                    refs={
                        "event_ref": event_path,
                        "scope": "absolute",
                        "searched_from": searched_from,
                    },
                ),
                exc_cls=ModelLookupError,
            )

        if not event_path:
            _fail_invalid("empty", "Event path cannot be empty")
            return None

        # Split the path into components
        path_parts = event_path.split(".")
        if not all(path_parts):
            _fail_invalid(
                "invalid_absolute",
                f"Invalid event path: {event_path!r} (contains empty parts)",
            )
            return None

        if len(path_parts) < 2:
            _fail_invalid(
                "invalid_absolute",
                f"Invalid event path: {event_path!r} "
                f"(must contain at least state name and event name)",
            )
            return None

        # The last part is the event name, everything before is the state path
        event_name = path_parts[-1]
        state_path_parts = path_parts[:-1]

        # Navigate to the target state starting from root
        current_state = self.root_state

        # Verify the first part matches the root state name
        if state_path_parts[0] != current_state.name:
            _fail_not_found(
                f"Event path root '{state_path_parts[0]}' does not match "
                f"state machine root '{current_state.name}' "
                f"while resolving event path {event_path!r}",
                searched_from=current_state.name,
            )
            return None

        # Navigate through the remaining state path
        for i, state_name in enumerate(state_path_parts[1:], 1):
            if state_name not in current_state.substates:
                _fail_not_found(
                    f"State '{state_name}' not found in state "
                    f"'{'.'.join(state_path_parts[:i])}' "
                    f"while resolving event path {event_path!r}",
                    searched_from=".".join(state_path_parts[:i]),
                )
                return None
            current_state = current_state.substates[state_name]

        # Look for the event in the target state
        if event_name not in current_state.events:
            _fail_not_found(
                f"Event '{event_name}' not found in state "
                f"'{'.'.join(state_path_parts)}' "
                f"while resolving event path {event_path!r}",
                searched_from=".".join(state_path_parts),
            )
            return None

        return current_state.events[event_name]


def parse_dsl_node_to_state_machine(
    dnode: dsl_nodes.StateMachineDSLProgram,
    path: Optional[str] = None,
    *,
    collect: bool = False,
) -> Union[
    StateMachine,
    Tuple[Optional[StateMachine], List[ModelDiagnostic]],
]:
    """
    Parse a state machine DSL program AST node into a StateMachine object.

    This function validates the state machine structure and builds a complete
    StateMachine object with all states, transitions, events, and variable
    definitions.

    The implementation routes every semantic error through a
    :class:`pyfcstm.diagnostics.DiagnosticSink`. In the default **strict**
    mode (``collect=False``), the first error raises
    :class:`pyfcstm.utils.validate.ModelValidationError` carrying a
    :class:`pyfcstm.utils.validate.ModelDiagnostic` list. In **collect**
    mode (``collect=True``), all detected errors are accumulated and
    returned alongside the partially-built model (which may be ``None`` if
    construction could not progress past a fatal point).

    The ``ModelValidationError`` exception multi-inherits from
    :class:`SyntaxError`, so callers using ``except SyntaxError:`` continue
    to work after this refactor.

    :param dnode: The state machine DSL program AST node to parse
    :type dnode: dsl_nodes.StateMachineDSLProgram
    :param path: Optional path contract reserved for import-aware assembly.
        When provided, the value defines the current DSL location for import
        resolution. When omitted, the current working directory is used.
        Existing directories are treated as import base directories directly,
        while file paths use their parent directory as the import base.
    :type path: Optional[str]
    :param collect: When ``True``, return ``(model_or_None, diagnostics)``
        instead of raising on the first error. Defaults to ``False``.
    :type collect: bool

    :return: The parsed state machine, or a ``(model, diagnostics)`` tuple
        when ``collect=True``.
    :rtype: Union[StateMachine, Tuple[Optional[StateMachine], List[ModelDiagnostic]]]

    :raises pyfcstm.utils.validate.ModelValidationError: When ``collect=False``
        and the DSL contains a semantic error. Multi-inherits from
        :class:`SyntaxError` for backwards compatibility.

    Example::

        >>> # Assuming you have a parsed DSL node
        >>> state_machine = parse_dsl_node_to_state_machine(
        ...     dsl_program_node,
        ...     path="root.fcstm",
        ... )
        >>> state_machine.root_state.name
        'root'
    """

    sink = DiagnosticSink(collect=collect)
    dnode = assemble_state_machine_imports(dnode, path=path, collect_into=sink)

    d_defines: Dict[str, VarDefine] = {}
    # Track first-declaration spans so duplicate diagnostics can point at
    # the previous definition.
    d_define_spans: Dict[str, Optional[Span]] = {}
    for def_item in dnode.definitions:
        if def_item.name not in d_defines:
            d_defines[def_item.name] = VarDefine(
                name=def_item.name,
                type=def_item.type,
                init=parse_expr_node_to_expr(def_item.expr),
                _span=_node_span(def_item),
            )
            d_define_spans[def_item.name] = _node_span(def_item)
        else:
            sink.emit(
                ModelDiagnostic(
                    code="E_DUPLICATE_VAR",
                    severity="error",
                    message=f"Duplicated variable definition - {def_item}.",
                    span=getattr(def_item, "_span", None),
                    refs={
                        "var_name": def_item.name,
                        "previous_span": d_define_spans.get(def_item.name),
                    },
                )
            )

    def _collect_block_local_names(
        op_nodes: List[dsl_nodes.OperationalStatement],
        accum: Set[str],
    ) -> None:
        """Walk an operation block and record every assignment LHS name
        whose target is NOT a file-top ``def`` — those are exactly the
        names that look like block-local temporaries (I-i).

        I5 (PR #116 re-review): this scan deliberately flattens across
        ``if`` branches — a name assigned in branch A is treated as
        "could be a temp" even when read in branch B's body. The
        alternative (branch-aware analysis) would require per-path
        reachable-assignment tracking and is more precision than the
        ``is_temporary`` schema flag is meant to carry. Both jsfcstm
        and pyfcstm agree on this flattened heuristic (jsfcstm's
        ``analyzeOperationStatements`` always emits ``is_temporary:
        true`` for operation-block reads), so the flag stays
        cross-end consistent at the cost of cross-branch precision.
        """
        for op_item in op_nodes:
            if isinstance(op_item, dsl_nodes.OperationAssignment):
                if op_item.name not in d_defines:
                    accum.add(op_item.name)
            elif isinstance(op_item, dsl_nodes.OperationIf):
                for branch in op_item.branches:
                    _collect_block_local_names(branch.statements, accum)

    def _parse_operation_block(
        op_nodes: List[dsl_nodes.OperationalStatement],
        unknown_var_message: str,
        referenced_in: str,
        owner_node,
        available_vars: Optional[Set[str]] = None,
        state_path: Optional[str] = None,
        block_local_names: Optional[Set[str]] = None,
    ) -> List[OperationStatement]:
        available_vars = set(available_vars or d_defines)
        # On the outermost call (no block_local_names yet) pre-walk the
        # block to discover all would-be block-local temps so each emit
        # can fill the ``is_temporary`` schema flag accurately.
        if block_local_names is None:
            block_local_names = set()
            _collect_block_local_names(op_nodes, block_local_names)
        operations = []
        for op_item in op_nodes:
            operations.append(
                _parse_operation_statement(
                    op_item=op_item,
                    unknown_var_message=unknown_var_message,
                    referenced_in=referenced_in,
                    owner_node=owner_node,
                    available_vars=available_vars,
                    state_path=state_path,
                    block_local_names=block_local_names,
                )
            )

        return operations

    def _parse_operation_statement(
        op_item: dsl_nodes.OperationalStatement,
        unknown_var_message: str,
        referenced_in: str,
        owner_node,
        available_vars: Set[str],
        state_path: Optional[str] = None,
        block_local_names: Optional[Set[str]] = None,
    ) -> OperationStatement:
        block_local_names = (
            block_local_names if block_local_names is not None else set()
        )
        if isinstance(op_item, dsl_nodes.OperationAssignment):
            operation_val = parse_expr_node_to_expr(op_item.expr)
            unknown_vars = []
            for var in operation_val.list_variables():
                if var.name not in available_vars and var.name not in unknown_vars:
                    unknown_vars.append(var.name)

            for unknown_var in unknown_vars:
                # I-i: ``is_temporary`` is True when this name is
                # assigned somewhere later in the same operation block,
                # which is the read-before-assign signature of a
                # would-be block-local temporary. Names that are
                # neither defined at file top nor assigned anywhere in
                # this block are "real" undefineds and leave the flag
                # off per schema default.
                is_temporary = unknown_var in block_local_names
                sink.emit(
                    ModelDiagnostic(
                        code="E_UNDEFINED_VAR",
                        severity="error",
                        message=(
                            f"{unknown_var_message} {unknown_var} "
                            f"in transition:\n{owner_node}"
                        ),
                        span=getattr(owner_node, "_span", None),
                        refs={
                            "var_name": unknown_var,
                            "referenced_in": referenced_in,
                            "state_path": state_path,
                            "expr_text": str(op_item.expr),
                            "is_temporary": is_temporary,
                        },
                    )
                )

            operation = Operation(
                var_name=op_item.name,
                expr=operation_val,
                _span=_node_span(op_item),
            )
            available_vars.add(op_item.name)
            return operation
        elif isinstance(op_item, dsl_nodes.OperationIf):
            return _parse_if_block(
                if_node=op_item,
                unknown_var_message=unknown_var_message,
                referenced_in=referenced_in,
                owner_node=owner_node,
                available_vars=available_vars,
                state_path=state_path,
                block_local_names=block_local_names,
            )
        else:  # pragma: no cover
            # Defensive: the grammar only produces ``OperationAssignment``
            # or ``OperationIf``. Reaching this branch means a future
            # parser change started emitting a new node kind without
            # extending this helper — fail loudly.
            raise TypeError(f"Unknown operation statement node - {op_item!r}.")

    def _parse_if_block(
        if_node: dsl_nodes.OperationIf,
        unknown_var_message: str,
        referenced_in: str,
        owner_node,
        available_vars: Set[str],
        state_path: Optional[str] = None,
        block_local_names: Optional[Set[str]] = None,
    ) -> IfBlock:
        block_local_names = (
            block_local_names if block_local_names is not None else set()
        )
        base_available_vars = set(available_vars)
        branches = []
        for branch in if_node.branches:
            condition = None
            if branch.condition is not None:
                condition = parse_expr_node_to_expr(branch.condition)
                unknown_vars = []
                for var in condition.list_variables():
                    if (
                        var.name not in base_available_vars
                        and var.name not in unknown_vars
                    ):
                        unknown_vars.append(var.name)
                for unknown_var in unknown_vars:
                    # I-i: see _parse_operation_statement.
                    is_temporary = unknown_var in block_local_names
                    sink.emit(
                        ModelDiagnostic(
                            code="E_UNDEFINED_VAR",
                            severity="error",
                            message=(
                                f"{unknown_var_message} {unknown_var} "
                                f"in transition:\n{owner_node}"
                            ),
                            span=getattr(owner_node, "_span", None),
                            refs={
                                "var_name": unknown_var,
                                "referenced_in": referenced_in,
                                "state_path": state_path,
                                "expr_text": str(branch.condition),
                                "is_temporary": is_temporary,
                            },
                        )
                    )

            branch_available_vars = set(base_available_vars)
            branch_statements = _parse_operation_block(
                op_nodes=branch.statements,
                unknown_var_message=unknown_var_message,
                referenced_in=referenced_in,
                owner_node=owner_node,
                available_vars=branch_available_vars,
                state_path=state_path,
                block_local_names=block_local_names,
            )
            branches.append(
                IfBlockBranch(
                    condition=condition,
                    statements=branch_statements,
                    _span=_node_span(branch),
                )
            )

        return IfBlock(branches=branches, _span=_node_span(if_node))

    def _recursive_build_states(
        node: dsl_nodes.StateDefinition,
        current_path: Tuple[str, ...],
        owner_node: Optional[dsl_nodes.StateDefinition] = None,
    ) -> State:
        current_path = tuple((*current_path, node.name))
        if node.name.startswith(_COMBO_STATE_PREFIX) and not (
            _is_exported_combo_pseudo_node(node, owner_node, current_path[:-1])
        ):
            sink.emit(
                ModelDiagnostic(
                    code="E_COMBO_RESERVED_STATE_NAME",
                    severity="error",
                    message=(
                        f"State name {node.name!r} uses reserved combo "
                        f"prefix {_COMBO_STATE_PREFIX!r}:\n{node}"
                    ),
                    span=getattr(node, "_span", None),
                    refs={
                        "state_name": node.name,
                        "state_path": ".".join(current_path),
                        "reserved_prefix": _COMBO_STATE_PREFIX,
                    },
                )
            )
        d_substates = {}

        substate_first_spans: Dict[str, Optional[Span]] = {}
        for subnode in node.substates:
            if subnode.name not in d_substates:
                d_substates[subnode.name] = _recursive_build_states(
                    subnode, current_path=current_path, owner_node=node
                )
                substate_first_spans[subnode.name] = getattr(subnode, "_span", None)
            else:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DUPLICATE_STATE",
                        severity="error",
                        message=(
                            f"Duplicate state name in namespace "
                            f"{'.'.join(current_path)!r}:\n{subnode}"
                        ),
                        span=getattr(subnode, "_span", None),
                        refs={
                            "state_name": subnode.name,
                            "parent_path": ".".join(current_path),
                            "previous_span": substate_first_spans.get(subnode.name),
                        },
                    )
                )

        named_functions = {}
        on_enters = []
        for enter_item in node.enters:
            on_stage = None
            if isinstance(enter_item, dsl_nodes.EnterOperations):
                enter_operations = _parse_operation_block(
                    enter_item.operations,
                    "Unknown enter operation variable",
                    "enter",
                    enter_item,
                    state_path=".".join(current_path),
                )
                on_stage = OnStage(
                    stage="enter",
                    aspect=None,
                    name=enter_item.name,
                    doc=None,
                    operations=enter_operations,
                    is_abstract=False,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(enter_item),
                )
            elif isinstance(enter_item, dsl_nodes.EnterAbstractFunction):
                on_stage = OnStage(
                    stage="enter",
                    aspect=None,
                    name=enter_item.name,
                    doc=enter_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(enter_item),
                )
            elif isinstance(enter_item, dsl_nodes.EnterRefFunction):
                on_stage = OnStage(
                    stage="enter",
                    aspect=None,
                    name=enter_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=(
                        *(
                            (dnode.root_state.name,)
                            if enter_item.ref.is_absolute
                            else current_path
                        ),
                        *enter_item.ref.path,
                    ),
                    _span=_node_span(enter_item),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        # I1 from PR-110: first-wins tiebreaker — keep the
                        # initial declaration so collect/strict modes resolve
                        # ``ref X`` identically (strict raises before the
                        # overwrite would have happened).
                        sink.emit(
                            ModelDiagnostic(
                                code="E_DUPLICATE_FUNCTION_NAME",
                                severity="error",
                                message=(
                                    f"Duplicate function name {on_stage.name!r} "
                                    f"in state:\n{node}"
                                ),
                                span=getattr(enter_item, "_span", None),
                                refs={
                                    "function_name": on_stage.name,
                                    "state_path": ".".join(current_path),
                                    "stage": "enter",
                                },
                            )
                        )
                    else:
                        named_functions[on_stage.name] = on_stage
                on_enters.append(on_stage)

        on_durings = []
        for during_item in node.durings:
            if not d_substates and during_item.aspect is not None:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DURING_ASPECT_INVALID",
                        severity="error",
                        message=(
                            f"For leaf state {node.name!r}, during cannot assign "
                            f"aspect {during_item.aspect!r}:\n{during_item}"
                        ),
                        span=getattr(during_item, "_span", None),
                        refs={
                            "state_path": ".".join(current_path),
                            "state_kind": "leaf",
                            "aspect": during_item.aspect,
                        },
                    )
                )
            if d_substates and during_item.aspect is None:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DURING_ASPECT_INVALID",
                        severity="error",
                        message=(
                            f"For composite state {node.name!r}, during must "
                            f"assign aspect to either 'before' or 'after':\n"
                            f"{during_item}"
                        ),
                        span=getattr(during_item, "_span", None),
                        refs={
                            "state_path": ".".join(current_path),
                            "state_kind": "composite",
                            "aspect": None,
                        },
                    )
                )

            on_stage = None
            if isinstance(during_item, dsl_nodes.DuringOperations):
                during_operations = _parse_operation_block(
                    during_item.operations,
                    "Unknown during operation variable",
                    "during",
                    during_item,
                    state_path=".".join(current_path),
                )
                on_stage = OnStage(
                    stage="during",
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=None,
                    operations=during_operations,
                    is_abstract=False,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(during_item),
                )
            elif isinstance(during_item, dsl_nodes.DuringAbstractFunction):
                on_stage = OnStage(
                    stage="during",
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=during_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(during_item),
                )
            elif isinstance(during_item, dsl_nodes.DuringRefFunction):
                on_stage = OnStage(
                    stage="during",
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=(
                        *(
                            (dnode.root_state.name,)
                            if during_item.ref.is_absolute
                            else current_path
                        ),
                        *during_item.ref.path,
                    ),
                    _span=_node_span(during_item),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        sink.emit(
                            ModelDiagnostic(
                                code="E_DUPLICATE_FUNCTION_NAME",
                                severity="error",
                                message=(
                                    f"Duplicate function name {on_stage.name!r} "
                                    f"in state:\n{node}"
                                ),
                                span=getattr(during_item, "_span", None),
                                refs={
                                    "function_name": on_stage.name,
                                    "state_path": ".".join(current_path),
                                    "stage": "during",
                                },
                            )
                        )
                    else:
                        named_functions[on_stage.name] = on_stage
                on_durings.append(on_stage)

        on_exits = []
        for exit_item in node.exits:
            on_stage = None
            if isinstance(exit_item, dsl_nodes.ExitOperations):
                exit_operations = _parse_operation_block(
                    exit_item.operations,
                    "Unknown exit operation variable",
                    "exit",
                    exit_item,
                    state_path=".".join(current_path),
                )
                on_stage = OnStage(
                    stage="exit",
                    aspect=None,
                    name=exit_item.name,
                    doc=None,
                    operations=exit_operations,
                    is_abstract=False,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(exit_item),
                )
            elif isinstance(exit_item, dsl_nodes.ExitAbstractFunction):
                on_stage = OnStage(
                    stage="exit",
                    aspect=None,
                    name=exit_item.name,
                    doc=exit_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(exit_item),
                )
            elif isinstance(exit_item, dsl_nodes.ExitRefFunction):
                on_stage = OnStage(
                    stage="exit",
                    aspect=None,
                    name=exit_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=(
                        *(
                            (dnode.root_state.name,)
                            if exit_item.ref.is_absolute
                            else current_path
                        ),
                        *exit_item.ref.path,
                    ),
                    _span=_node_span(exit_item),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        sink.emit(
                            ModelDiagnostic(
                                code="E_DUPLICATE_FUNCTION_NAME",
                                severity="error",
                                message=(
                                    f"Duplicate function name {on_stage.name!r} "
                                    f"in state:\n{node}"
                                ),
                                span=getattr(exit_item, "_span", None),
                                refs={
                                    "function_name": on_stage.name,
                                    "state_path": ".".join(current_path),
                                    "stage": "exit",
                                },
                            )
                        )
                    else:
                        named_functions[on_stage.name] = on_stage
                on_exits.append(on_stage)

        on_during_aspects = []
        for during_aspect_item in node.during_aspects:
            # PR-A alignment with jsfcstm: ``>> during before/after`` is
            # only meaningful on a composite state (it fans out to every
            # descendant leaf). On a leaf state there is nothing to fan
            # into, so the aspect is invalid.
            if not d_substates:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DURING_ASPECT_INVALID",
                        severity="error",
                        message=(
                            f"For leaf state {node.name!r}, ``>> during "
                            f"{during_aspect_item.aspect}`` aspect actions "
                            f"need at least one descendant leaf:\n"
                            f"{during_aspect_item}"
                        ),
                        span=getattr(during_aspect_item, "_span", None),
                        refs={
                            "state_path": ".".join(current_path),
                            "state_kind": "leaf",
                            "aspect": during_aspect_item.aspect,
                        },
                    )
                )
            on_aspect = None
            if isinstance(during_aspect_item, dsl_nodes.DuringAspectOperations):
                during_operations = _parse_operation_block(
                    during_aspect_item.operations,
                    "Unknown during aspect variable",
                    "during_aspect",
                    during_aspect_item,
                    state_path=".".join(current_path),
                )
                on_aspect = OnAspect(
                    stage="during",
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=None,
                    operations=during_operations,
                    is_abstract=False,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(during_aspect_item),
                )
            elif isinstance(during_aspect_item, dsl_nodes.DuringAspectAbstractFunction):
                on_aspect = OnAspect(
                    stage="during",
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=during_aspect_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=None,
                    _span=_node_span(during_aspect_item),
                )
            elif isinstance(during_aspect_item, dsl_nodes.DuringAspectRefFunction):
                on_aspect = OnAspect(
                    stage="during",
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=(
                        *(
                            (dnode.root_state.name,)
                            if during_aspect_item.ref.is_absolute
                            else current_path
                        ),
                        *during_aspect_item.ref.path,
                    ),
                    _span=_node_span(during_aspect_item),
                )

            if on_aspect is not None:
                if on_aspect.name:
                    if on_aspect.name in named_functions:
                        sink.emit(
                            ModelDiagnostic(
                                code="E_DUPLICATE_FUNCTION_NAME",
                                severity="error",
                                message=(
                                    f"Duplicate function name {on_aspect.name!r} "
                                    f"in state:\n{node}"
                                ),
                                span=getattr(during_aspect_item, "_span", None),
                                refs={
                                    "function_name": on_aspect.name,
                                    "state_path": ".".join(current_path),
                                    "stage": "during_aspect",
                                },
                            )
                        )
                    else:
                        named_functions[on_aspect.name] = on_aspect
                on_during_aspects.append(on_aspect)

        d_events = {}
        for event in node.events:
            d_events[event.name] = Event(
                name=event.name,
                extra_name=event.extra_name,
                state_path=current_path,
                declared=True,
                origins=["declared"],
                _span=_node_span(event),
            )

        my_state = State(
            name=node.name,
            extra_name=node.extra_name,
            events=d_events,
            path=current_path,
            substates=d_substates,
            is_pseudo=bool(node.is_pseudo),
            on_enters=on_enters,
            on_durings=on_durings,
            on_exits=on_exits,
            on_during_aspects=on_during_aspects,
            named_functions=named_functions,
            _span=_node_span(node),
        )
        if my_state.is_pseudo and not my_state.is_leaf_state:
            sink.emit(
                ModelDiagnostic(
                    code="E_PSEUDO_NOT_LEAF",
                    severity="error",
                    message=(
                        f"Pseudo state {'.'.join(current_path)} must be a leaf "
                        f"state:\n{node}"
                    ),
                    span=getattr(node, "_span", None),
                    refs={
                        "state_path": ".".join(current_path),
                    },
                )
            )
        for func_item in [
            *my_state.on_enters,
            *my_state.on_durings,
            *my_state.on_exits,
            *my_state.on_during_aspects,
        ]:
            func_item.parent = my_state
        for _, substate in d_substates.items():
            substate.parent = my_state
        return my_state

    root_state = _recursive_build_states(dnode.root_state, current_path=())
    forced_transition_declarations = []

    def _recursive_finish_states(
        node: dsl_nodes.StateDefinition,
        current_state: State,
        current_path: Tuple[str, ...],
        force_transitions: Optional[List[dsl_nodes.ForceTransitionDefinition]] = None,
    ) -> None:
        current_path = tuple((*current_path, current_state.name))
        force_transitions = list(force_transitions or [])

        force_transition_tuples_to_inherit = []
        local_force_ids = {id(item) for item in node.force_transitions}
        for f_transnode in [*force_transitions, *node.force_transitions]:
            # I3 from PR-110: if either side of a forced transition is
            # unresolved, skip the rest of the per-transition processing
            # AND the inherit-tuple append. Otherwise collect mode keeps a
            # bad ``(from_state, to_state, ...)`` tuple that quietly
            # corrupts the inheritance phase (bad to_state being attached
            # to a real substate's transitions).
            unresolved = False
            if f_transnode.from_state == dsl_nodes.ALL:
                from_state = dsl_nodes.ALL
            else:
                from_state = f_transnode.from_state
                if from_state not in current_state.substates:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_FORCED_TRANSITION_EXPANSION",
                            severity="error",
                            message=(
                                f"Unknown from state {from_state!r} of force "
                                f"transition:\n{f_transnode}"
                            ),
                            span=getattr(f_transnode, "_span", None),
                            refs={
                                "original_raw": str(f_transnode),
                                "reason": "src_not_found",
                            },
                        )
                    )
                    unresolved = True

            if f_transnode.to_state is dsl_nodes.EXIT_STATE:
                to_state = dsl_nodes.EXIT_STATE
            else:
                to_state = f_transnode.to_state
                if to_state not in current_state.substates:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_FORCED_TRANSITION_EXPANSION",
                            severity="error",
                            message=(
                                f"Unknown to state {to_state!r} of force "
                                f"transition:\n{f_transnode}"
                            ),
                            span=getattr(f_transnode, "_span", None),
                            refs={
                                "original_raw": str(f_transnode),
                                "reason": "tgt_not_found",
                            },
                        )
                    )
                    unresolved = True

            if unresolved:
                continue

            my_event_id, trans_event = None, None
            if f_transnode.event_id is not None:
                my_event_id = f_transnode.event_id
                source_state = from_state if isinstance(from_state, str) else None
                origin = _event_origin_from_id(
                    my_event_id,
                    f_transnode.event_scope,
                    source_state=source_state,
                )
                if not my_event_id.is_absolute:
                    my_event_id = dsl_nodes.ChainID(
                        path=[*current_state.path[1:], *my_event_id.path],
                        is_absolute=True,
                    )
                start_state = root_state
                base_path = (root_state.name,)
                # Walk the event-id state segments. On a missing segment
                # we emit the diagnostic and skip the suffix resolution —
                # without this guard, collect mode would silently fabricate
                # an Event in whatever partial state ``start_state`` landed
                # on (C1 from PR-110 review).
                path_resolved = True
                for seg in my_event_id.path[:-1]:
                    if seg in start_state.substates:
                        start_state = start_state.substates[seg]
                    else:
                        sink.emit(
                            ModelDiagnostic(
                                code="E_MISSING_STATE",
                                severity="error",
                                message=(
                                    f"Cannot find state "
                                    f"{'.'.join((*base_path, *my_event_id.path[:-1]))} "
                                    f"for transition:\n{f_transnode}"
                                ),
                                span=getattr(f_transnode, "_span", None),
                                refs={
                                    "state_path": ".".join(
                                        (*base_path, *my_event_id.path[:-1])
                                    ),
                                    "referenced_from": ".".join(current_path),
                                    "reason": "event_path_not_found",
                                },
                            )
                        )
                        path_resolved = False
                        break

                if path_resolved:
                    suffix_name = my_event_id.path[-1]
                    if suffix_name not in start_state.events:
                        start_state.events[suffix_name] = Event(
                            name=suffix_name,
                            state_path=start_state.path,
                            origins=[origin],
                            _span=_node_span(f_transnode),
                        )
                    else:
                        if origin not in start_state.events[suffix_name].origins:
                            start_state.events[suffix_name].origins.append(origin)
                    trans_event = start_state.events[suffix_name]

            condition_expr, guard = f_transnode.condition_expr, None
            if f_transnode.condition_expr is not None:
                guard = parse_expr_node_to_expr(f_transnode.condition_expr)
                unknown_vars = []
                for var in guard.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                for unknown_var in unknown_vars:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_UNDEFINED_VAR",
                            severity="error",
                            message=(
                                f"Unknown guard variable "
                                f"{unknown_var} in force "
                                f"transition:\n{f_transnode}"
                            ),
                            span=getattr(f_transnode, "_span", None),
                            refs={
                                "var_name": unknown_var,
                                "referenced_in": "guard",
                                "state_path": ".".join(current_path),
                                "expr_text": str(f_transnode.condition_expr),
                            },
                        )
                    )

            if id(f_transnode) in local_force_ids:
                if from_state is dsl_nodes.ALL:
                    source_path = "*"
                    expansion_count = len(node.substates)
                else:
                    source_path = ".".join((*current_path, from_state))
                    expansion_count = 1
                forced_transition_declarations.append(
                    {
                        "state_path": ".".join(current_path),
                        "from_path": source_path,
                        "to_path": (
                            "[*]"
                            if to_state is dsl_nodes.EXIT_STATE
                            else ".".join((*current_path, to_state))
                        ),
                        "event": trans_event.path_name
                        if trans_event is not None
                        else None,
                        "event_scope": (
                            f_transnode.event_scope if trans_event is not None else None
                        ),
                        "guard": str(condition_expr)
                        if condition_expr is not None
                        else None,
                        "original_raw": str(f_transnode),
                        "expansion_count": expansion_count,
                        "span": _node_span(f_transnode),
                    }
                )

            force_transition_tuples_to_inherit.append(
                (
                    from_state,
                    to_state,
                    my_event_id,
                    trans_event,
                    condition_expr,
                    guard,
                    f_transnode.event_scope,
                    getattr(f_transnode, "source_raw", None) or str(f_transnode),
                    _node_span(f_transnode),
                )
            )

        transitions = current_state.transitions
        for subnode in node.substates:
            _inner_force_transitions = []
            for (
                from_state,
                to_state,
                my_event_id,
                trans_event,
                condition_expr,
                guard,
                event_scope,
                forced_origin,
                forced_span,
            ) in force_transition_tuples_to_inherit:
                if from_state is dsl_nodes.ALL or from_state == subnode.name:
                    transitions.append(
                        Transition(
                            from_state=subnode.name,
                            to_state=to_state,
                            event=trans_event,
                            guard=guard,
                            effects=[],
                            event_scope=event_scope,
                            is_forced=True,
                            forced_origin=forced_origin,
                            _span=forced_span,
                        )
                    )
                    _inner_force_transitions.append(
                        dsl_nodes.ForceTransitionDefinition(
                            from_state=dsl_nodes.ALL,
                            to_state=dsl_nodes.EXIT_STATE,
                            event_id=my_event_id,
                            condition_expr=condition_expr,
                            event_scope=event_scope,
                            source_raw=forced_origin,
                            _span=forced_span,
                        )
                    )

            _recursive_finish_states(
                node=subnode,
                current_state=current_state.substates[subnode.name],
                current_path=current_path,
                force_transitions=_inner_force_transitions,
            )

        def _emit_dangling_transition_diagnostics(transnode) -> bool:
            """Validate transition endpoints and return whether they are usable."""
            src_unknown = (
                transnode.from_state is not dsl_nodes.INIT_STATE
                and transnode.from_state not in current_state.substates
            )
            tgt_unknown = (
                transnode.to_state is not dsl_nodes.EXIT_STATE
                and transnode.to_state not in current_state.substates
            )

            from_state = (
                dsl_nodes.INIT_STATE
                if transnode.from_state is dsl_nodes.INIT_STATE
                else transnode.from_state
            )
            to_state = (
                dsl_nodes.EXIT_STATE
                if transnode.to_state is dsl_nodes.EXIT_STATE
                else transnode.to_state
            )

            if src_unknown and tgt_unknown:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DANGLING_TRANSITION",
                        severity="error",
                        message=(
                            f"Unknown from state {from_state!r} and "
                            f"unknown to state {to_state!r} of "
                            f"transition:\n{transnode}"
                        ),
                        span=getattr(transnode, "_span", None),
                        refs={
                            "src": str(transnode.from_state),
                            "tgt": str(transnode.to_state),
                            "reason": "both_not_found",
                        },
                    )
                )
            elif src_unknown:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DANGLING_TRANSITION",
                        severity="error",
                        message=(
                            f"Unknown from state {from_state!r} of "
                            f"transition:\n{transnode}"
                        ),
                        span=getattr(transnode, "_span", None),
                        refs={
                            "src": str(transnode.from_state),
                            "tgt": (
                                None
                                if transnode.to_state is dsl_nodes.EXIT_STATE
                                else str(transnode.to_state)
                            ),
                            "reason": "src_not_found",
                        },
                    )
                )
            elif tgt_unknown:
                sink.emit(
                    ModelDiagnostic(
                        code="E_DANGLING_TRANSITION",
                        severity="error",
                        message=(
                            f"Unknown to state {to_state!r} of transition:\n{transnode}"
                        ),
                        span=getattr(transnode, "_span", None),
                        refs={
                            "src": (
                                None
                                if transnode.from_state is dsl_nodes.INIT_STATE
                                else str(transnode.from_state)
                            ),
                            "tgt": str(transnode.to_state),
                            "reason": "tgt_not_found",
                        },
                    )
                )

            return not (src_unknown or tgt_unknown)

        def _resolve_transition_event(
            transnode,
            event_id: dsl_nodes.ChainID,
            event_scope: Optional[str],
            source_state_name: Optional[str],
        ) -> Tuple[Optional[str], Optional[Event]]:
            event_scope = _event_origin_from_id(
                event_id,
                event_scope,
                source_state=source_state_name,
            )
            effective_event_id = event_id
            if event_id.is_absolute:
                start_state = root_state
                base_path = (root_state.name,)
            else:
                start_state = current_state
                base_path = current_state.path
                if event_scope == "local" and source_state_name is not None:
                    if not event_id.path or event_id.path[0] != source_state_name:
                        effective_event_id = dsl_nodes.ChainID(
                            path=[source_state_name, *event_id.path],
                            is_absolute=False,
                        )

            path_resolved = True
            for seg in effective_event_id.path[:-1]:
                if seg in start_state.substates:
                    start_state = start_state.substates[seg]
                else:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_MISSING_STATE",
                            severity="error",
                            message=(
                                f"Cannot find state "
                                f"{'.'.join((*base_path, *effective_event_id.path[:-1]))} "
                                f"for transition:\n{transnode}"
                            ),
                            span=getattr(transnode, "_span", None),
                            refs={
                                "state_path": ".".join(
                                    (*base_path, *effective_event_id.path[:-1])
                                ),
                                "referenced_from": ".".join(current_path),
                                "reason": "event_path_not_found",
                            },
                        )
                    )
                    path_resolved = False
                    break

            if not path_resolved:
                return event_scope, None

            suffix_name = effective_event_id.path[-1]
            if suffix_name not in start_state.events:
                start_state.events[suffix_name] = Event(
                    name=suffix_name,
                    state_path=start_state.path,
                    origins=[event_scope],
                    _span=_node_span(transnode),
                )
            elif event_scope not in start_state.events[suffix_name].origins:
                start_state.events[suffix_name].origins.append(event_scope)
            return event_scope, start_state.events[suffix_name]

        def _combo_term_event_id(
            transnode,
            term: dsl_nodes.ComboEventTerm,
        ) -> dsl_nodes.ChainID:
            return term.event_id

        def _combo_term_semantic_key(
            transnode,
            term: dsl_nodes.ComboTriggerTerm,
        ) -> Tuple[object, ...]:
            if isinstance(term, dsl_nodes.ComboEventTerm):
                event_id = _combo_term_event_id(transnode, term)
                event_scope = _event_origin_from_id(
                    event_id,
                    term.event_scope,
                    source_state=(
                        transnode.from_state
                        if isinstance(transnode.from_state, str)
                        else None
                    ),
                )
                return (
                    "event",
                    event_scope,
                    event_id.is_absolute,
                    tuple(event_id.path),
                )
            return ("guard", str(term.condition_expr))

        def _parse_transition_guard(transnode, condition_node) -> Optional[Expr]:
            if condition_node is None:
                return None
            guard = parse_expr_node_to_expr(condition_node)
            unknown_vars = []
            for var in guard.list_variables():
                if var.name not in d_defines:
                    unknown_vars.append(var.name)
            for unknown_var in unknown_vars:
                sink.emit(
                    ModelDiagnostic(
                        code="E_UNDEFINED_VAR",
                        severity="error",
                        message=(
                            f"Unknown guard variable "
                            f"{unknown_var} in "
                            f"transition:\n{transnode}"
                        ),
                        span=getattr(transnode, "_span", None),
                        refs={
                            "var_name": unknown_var,
                            "referenced_in": "guard",
                            "state_path": ".".join(current_path),
                            "expr_text": str(condition_node),
                        },
                    )
                )
            return guard

        def _parse_transition_effects(transnode) -> List[OperationStatement]:
            return _parse_operation_block(
                transnode.post_operations,
                "Unknown transition operation variable",
                "effect",
                transnode,
                state_path=".".join(current_path),
            )

        def _make_origin_ref(
            alternative: _ComboAlternative,
            term_index: int,
            role: str,
            consumes_term: bool,
        ) -> ComboOriginRef:
            term = alternative.terms[term_index]
            return ComboOriginRef(
                origin_id=alternative.origin_id,
                term_index=term_index,
                role=role,
                consumes_term=consumes_term,
                term_text=term.canonical_text,
                transition_span=_node_span(alternative.transnode),
                trigger_span=alternative.transnode.combo_trigger.trigger_span,
                term_span=getattr(term, "term_span", None),
                value_span=getattr(term, "value_span", None),
                removal_span=getattr(term, "removal_span", None),
            )

        combo_name_payloads: Dict[str, str] = {}
        combo_digest_payloads: Dict[Tuple[Tuple[str, ...], str], str] = {}

        def _term_name_slug(term: dsl_nodes.ComboTriggerTerm) -> str:
            if isinstance(term, dsl_nodes.ComboGuardTerm):
                text = f"if {term.condition_expr}"
                for source, replacement in [
                    ("=>", " implies "),
                    ("==", " eq "),
                    ("!=", " ne "),
                    (">=", " ge "),
                    ("<=", " le "),
                    ("&&", " and "),
                    ("||", " or "),
                    (">", " gt "),
                    ("<", " lt "),
                    ("!", " not "),
                ]:
                    text = text.replace(source, replacement)
                return to_identifier(
                    text,
                    strict_mode=True,
                ).lower()
            text = term.canonical_text
            if text.startswith("/"):
                text = f"abs {text[1:]}"
            return to_identifier(text, strict_mode=True).lower()

        def _transition_endpoint_text(endpoint) -> str:
            if endpoint is dsl_nodes.INIT_STATE:
                return "__init__"
            if endpoint is dsl_nodes.EXIT_STATE:
                return "__exit__"
            return str(endpoint)

        def _combo_effect_signature(transnode) -> Tuple[str, ...]:
            return tuple(str(item) for item in transnode.post_operations)

        def _combo_origin_id(
            transnode,
            semantic_duplicate_discriminator: Optional[int],
        ) -> str:
            base = (
                f"{'.'.join(current_state.path)}:"
                f"{_transition_endpoint_text(transnode.from_state)}->"
                f"{_transition_endpoint_text(transnode.to_state)}:"
                f"{transnode.combo_trigger.canonical_text}"
            )
            effects = _combo_effect_signature(transnode)
            if effects:
                base = f"{base}:effect={json.dumps(effects, ensure_ascii=False)}"
            if semantic_duplicate_discriminator is not None:
                base = f"{base}#dup{semantic_duplicate_discriminator}"
            return base

        def _combo_alternative_key(
            transnode,
        ) -> Tuple[object, ...]:
            return (
                _combo_projection_key(transnode),
                _transition_endpoint_text(transnode.to_state),
                tuple(
                    _combo_term_semantic_key(transnode, term)
                    for term in transnode.combo_trigger.terms
                ),
                _combo_effect_signature(transnode),
            )

        def _make_pseudo_state(
            chooser_key: Tuple[object, ...],
            consumed_terms: Tuple[dsl_nodes.ComboTriggerTerm, ...],
            consumed_term_keys: Tuple[Tuple[object, ...], ...],
            run_anchor_origin_id: str,
            semantic_duplicate_discriminator: Optional[int],
        ) -> State:
            term_texts = tuple(term.canonical_text for term in consumed_terms)
            payload_obj = {
                "owner_path": current_state.path,
                "chooser_key": chooser_key,
                "consumed_terms": consumed_term_keys,
                "run_anchor_origin_id": run_anchor_origin_id,
                "semantic_duplicate_discriminator": semantic_duplicate_discriminator,
            }
            payload = json.dumps(payload_obj, ensure_ascii=False, sort_keys=True)
            digest = _combo_payload_digest(payload)
            short_digest = digest[:_COMBO_DIGEST_SIZE]
            digest_key = (current_state.path, short_digest)
            source_label = (
                "entry" if chooser_key[1] == "entry" else ".".join(chooser_key[2])
            )
            slug_parts = [to_identifier(source_label, strict_mode=True).lower()]
            slug_parts.extend(_term_name_slug(term) for term in consumed_terms)
            slug = sequence_safe(slug_parts)
            name = f"{_COMBO_STATE_PREFIX}{slug}_h{short_digest}"

            existing_digest_payload = combo_digest_payloads.get(digest_key)
            if (
                existing_digest_payload is not None
                and existing_digest_payload != payload
            ):
                sink.emit(
                    ModelDiagnostic(
                        code="E_COMBO_PSEUDO_NAME_COLLISION",
                        severity="error",
                        message=(
                            f"Generated combo pseudo state digest {short_digest!r} "
                            "collides for distinct semantic payloads."
                        ),
                        span=None,
                        refs={
                            "state_path": ".".join(current_state.path),
                            "pseudo_name": name,
                            "payload_digest": digest,
                        },
                    )
                )
            elif existing_digest_payload is None:
                combo_digest_payloads[digest_key] = payload

            existing_payload = combo_name_payloads.get(name)
            if existing_payload is not None and existing_payload != payload:
                sink.emit(
                    ModelDiagnostic(
                        code="E_COMBO_PSEUDO_NAME_COLLISION",
                        severity="error",
                        message=(
                            f"Generated combo pseudo state name {name!r} collides "
                            "for distinct semantic payloads."
                        ),
                        span=None,
                        refs={
                            "state_path": ".".join(current_state.path),
                            "pseudo_name": name,
                            "payload_digest": digest,
                        },
                    )
                )
            elif existing_payload is None:
                combo_name_payloads[name] = payload

            if name in current_state.substates:
                state = current_state.substates[name]
                if not state.is_pseudo:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_COMBO_PSEUDO_NAME_COLLISION",
                            severity="error",
                            message=(
                                f"Generated combo pseudo state name {name!r} "
                                "collides with a non-pseudo state."
                            ),
                            span=state._span,
                            refs={
                                "state_path": ".".join(current_state.path),
                                "pseudo_name": name,
                                "payload_digest": digest,
                            },
                        )
                    )
                return state

            display = _COMBO_DISPLAY_PREFIX + " + ".join(term_texts)
            state = State(
                name=name,
                extra_name=display,
                events={},
                path=(*current_state.path, name),
                substates={},
                is_pseudo=True,
            )
            state._generated_combo_pseudo = True
            state.parent = current_state
            current_state.substates[name] = state
            current_state.substate_name_to_id[name] = len(
                current_state.substate_name_to_id
            )
            return state

        def _append_generated_transition(
            from_state,
            to_state,
            event: Optional[Event],
            guard: Optional[Expr],
            effects: List[OperationStatement],
            event_scope: Optional[str],
            origin_refs: Tuple[ComboOriginRef, ...],
            projection_key: Tuple[object, ...],
            projection_order_key: Tuple[object, ...],
            reuse_group_id: str,
            priority_run_identity: Tuple[str, Optional[int]],
            priority_run_index: int,
            source_span: Optional[Span],
        ) -> None:
            transitions.append(
                Transition(
                    from_state=from_state,
                    to_state=to_state,
                    event=event,
                    guard=guard,
                    effects=effects,
                    event_scope=event_scope,
                    combo_origin_refs=origin_refs,
                    combo_projection_key=projection_key,
                    combo_projection_order_key=projection_order_key,
                    combo_reuse_group_id=reuse_group_id,
                    combo_priority_run_identity=priority_run_identity,
                    combo_priority_run_index=priority_run_index,
                    _span=source_span,
                )
            )

        combo_preorder_counter = 0

        def _emit_combo_edge_for_term(
            alternatives: Tuple[_ComboAlternative, ...],
            term_index: int,
            from_state,
            to_state,
            projection_key: Tuple[object, ...],
            projection_order_key: Tuple[object, ...],
            reuse_group_id: str,
            priority_run_identity: Tuple[str, Optional[int]],
            priority_run_index: int,
            role: str,
            effects: List[OperationStatement],
        ) -> None:
            first_alt = alternatives[0]
            term = first_alt.terms[term_index]
            event = None
            guard = None
            event_scope = None
            if isinstance(term, dsl_nodes.ComboEventTerm):
                event_id = _combo_term_event_id(first_alt.transnode, term)
                event_scope, event = _resolve_transition_event(
                    first_alt.transnode,
                    event_id,
                    term.event_scope,
                    source_state_name=(
                        first_alt.transnode.from_state
                        if isinstance(first_alt.transnode.from_state, str)
                        else None
                    ),
                )
            else:
                guard = _parse_transition_guard(
                    first_alt.transnode, term.condition_expr
                )

            origin_refs = tuple(
                _make_origin_ref(
                    alternative,
                    term_index=term_index,
                    role=role,
                    consumes_term=True,
                )
                for alternative in alternatives
            )
            _append_generated_transition(
                from_state=from_state,
                to_state=to_state,
                event=event,
                guard=guard,
                effects=effects,
                event_scope=event_scope,
                origin_refs=origin_refs,
                projection_key=projection_key,
                projection_order_key=projection_order_key,
                reuse_group_id=reuse_group_id,
                priority_run_identity=priority_run_identity,
                priority_run_index=priority_run_index,
                source_span=_node_span(first_alt.transnode),
            )

        def _expand_combo_alternatives(
            alternatives: Tuple[_ComboAlternative, ...],
            term_index: int,
            from_state,
            consumed_terms: Tuple[dsl_nodes.ComboTriggerTerm, ...],
            consumed_term_keys: Tuple[Tuple[object, ...], ...],
            projection_key: Tuple[object, ...],
        ) -> None:
            nonlocal combo_preorder_counter
            i = 0
            while i < len(alternatives):
                alternative = alternatives[i]
                remaining = len(alternative.terms) - term_index
                if remaining <= 0:
                    i += 1
                    continue

                term = alternative.terms[term_index]
                term_key = _combo_term_semantic_key(alternative.transnode, term)
                if remaining == 1:
                    order_index = combo_preorder_counter
                    combo_preorder_counter += 1
                    effects = _parse_transition_effects(alternative.transnode)
                    _emit_combo_edge_for_term(
                        (alternative,),
                        term_index=term_index,
                        from_state=from_state,
                        to_state=(
                            dsl_nodes.EXIT_STATE
                            if alternative.transnode.to_state is dsl_nodes.EXIT_STATE
                            else alternative.transnode.to_state
                        ),
                        projection_key=projection_key,
                        projection_order_key=(
                            alternative.declaration_index,
                            order_index,
                            term_index,
                            "terminal",
                        ),
                        reuse_group_id=f"{alternative.origin_id}:terminal:{term_index}",
                        priority_run_identity=(
                            alternative.origin_id,
                            alternative.semantic_duplicate_discriminator,
                        ),
                        priority_run_index=order_index,
                        role="terminal",
                        effects=effects,
                    )
                    i += 1
                    continue

                group = [alternative]
                j = i + 1
                while j < len(alternatives):
                    candidate = alternatives[j]
                    candidate_remaining = len(candidate.terms) - term_index
                    if candidate_remaining <= 1:
                        break
                    candidate_term = candidate.terms[term_index]
                    candidate_key = _combo_term_semantic_key(
                        candidate.transnode, candidate_term
                    )
                    if candidate_key != term_key:
                        break
                    group.append(candidate)
                    j += 1

                group_tuple = tuple(group)
                run_anchor_origin_id = group_tuple[0].origin_id
                consumed_next = (*consumed_terms, term)
                consumed_next_keys = (*consumed_term_keys, term_key)
                pseudo_state = _make_pseudo_state(
                    projection_key,
                    consumed_next,
                    consumed_next_keys,
                    run_anchor_origin_id,
                    semantic_duplicate_discriminator=(
                        group_tuple[0].semantic_duplicate_discriminator
                    ),
                )
                order_index = combo_preorder_counter
                combo_preorder_counter += 1
                reuse_group_id = (
                    f"{run_anchor_origin_id}:prefix:{term_index}:{order_index}"
                )
                _emit_combo_edge_for_term(
                    group_tuple,
                    term_index=term_index,
                    from_state=from_state,
                    to_state=pseudo_state.name,
                    projection_key=projection_key,
                    projection_order_key=(
                        group_tuple[0].declaration_index,
                        order_index,
                        term_index,
                        "prefix",
                    ),
                    reuse_group_id=reuse_group_id,
                    priority_run_identity=(
                        run_anchor_origin_id,
                        group_tuple[0].semantic_duplicate_discriminator,
                    ),
                    priority_run_index=order_index,
                    role="prefix",
                    effects=[],
                )
                _expand_combo_alternatives(
                    group_tuple,
                    term_index + 1,
                    pseudo_state.name,
                    consumed_next,
                    consumed_next_keys,
                    projection_key,
                )
                i = j

        def _normal_transition(transnode) -> Transition:
            _emit_dangling_transition_diagnostics(transnode)

            if transnode.from_state is dsl_nodes.INIT_STATE:
                from_state = dsl_nodes.INIT_STATE
            else:
                from_state = transnode.from_state

            if transnode.to_state is dsl_nodes.EXIT_STATE:
                to_state = dsl_nodes.EXIT_STATE
            else:
                to_state = transnode.to_state

            trans_event = None
            event_scope = None
            if transnode.event_id is not None:
                event_scope, trans_event = _resolve_transition_event(
                    transnode,
                    transnode.event_id,
                    transnode.event_scope,
                    source_state_name=(
                        transnode.from_state
                        if isinstance(transnode.from_state, str)
                        else None
                    ),
                )

            guard = _parse_transition_guard(transnode, transnode.condition_expr)
            post_operations = _parse_transition_effects(transnode)
            return Transition(
                from_state=from_state,
                to_state=to_state,
                event=trans_event,
                guard=guard,
                effects=post_operations,
                event_scope=event_scope,
                _span=_node_span(transnode),
            )

        def _combo_projection_key(transnode) -> Tuple[object, ...]:
            if transnode.from_state is dsl_nodes.INIT_STATE:
                return (current_state.path, "entry", "INIT_MARKER")
            source_state_name = (
                transnode.from_state
                if isinstance(transnode.from_state, str)
                else str(transnode.from_state)
            )
            return (
                current_state.path,
                "state",
                (*current_state.path, source_state_name),
            )

        def _is_combo_transition(transnode) -> bool:
            return (
                getattr(transnode, "combo_trigger", None) is not None
                and transnode.combo_trigger.is_combo
            )

        transition_endpoint_cache: Dict[int, bool] = {}

        def _transition_endpoints_usable(transnode) -> bool:
            cache_key = id(transnode)
            if cache_key not in transition_endpoint_cache:
                transition_endpoint_cache[cache_key] = (
                    _emit_dangling_transition_diagnostics(transnode)
                )
            return transition_endpoint_cache[cache_key]

        has_entry_trans = False
        processed_combo_transition_ids = set()
        combo_alternative_counts: Dict[Tuple[object, ...], int] = {}
        i = 0
        while i < len(node.transitions):
            transnode = node.transitions[i]
            if transnode.from_state is dsl_nodes.INIT_STATE:
                has_entry_trans = True

            if id(transnode) in processed_combo_transition_ids:
                i += 1
                continue

            if not _is_combo_transition(transnode):
                transition = _normal_transition(transnode)
                transitions.append(transition)
                i += 1
                continue

            if not _transition_endpoints_usable(transnode):
                i += 1
                continue

            projection_key = _combo_projection_key(transnode)
            first_term = transnode.combo_trigger.terms[0]
            first_key = _combo_term_semantic_key(transnode, first_term)
            run = []
            j = i
            while j < len(node.transitions):
                candidate = node.transitions[j]
                if id(candidate) in processed_combo_transition_ids:
                    j += 1
                    continue
                if not _is_combo_transition(candidate):
                    if _combo_projection_key(candidate) == projection_key:
                        break
                    break
                if _combo_projection_key(candidate) != projection_key:
                    break
                if not _transition_endpoints_usable(candidate):
                    j += 1
                    continue
                if candidate.from_state is dsl_nodes.INIT_STATE:
                    has_entry_trans = True
                candidate_first = candidate.combo_trigger.terms[0]
                candidate_key = _combo_term_semantic_key(candidate, candidate_first)
                if candidate_key != first_key:
                    break
                processed_combo_transition_ids.add(id(candidate))
                alternative_key = _combo_alternative_key(candidate)
                duplicate_index = combo_alternative_counts.get(alternative_key, 0)
                combo_alternative_counts[alternative_key] = duplicate_index + 1
                run.append(
                    _ComboAlternative(
                        transnode=candidate,
                        terms=tuple(candidate.combo_trigger.terms),
                        origin_id=_combo_origin_id(
                            candidate,
                            duplicate_index if duplicate_index else None,
                        ),
                        declaration_index=j,
                        semantic_duplicate_discriminator=(
                            duplicate_index if duplicate_index else None
                        ),
                    )
                )
                j += 1

            from_state = (
                dsl_nodes.INIT_STATE
                if transnode.from_state is dsl_nodes.INIT_STATE
                else transnode.from_state
            )
            _expand_combo_alternatives(
                tuple(run),
                term_index=0,
                from_state=from_state,
                consumed_terms=(),
                consumed_term_keys=(),
                projection_key=projection_key,
            )
            i += 1

        if current_state.substates and not has_entry_trans:
            sink.emit(
                ModelDiagnostic(
                    code="E_INITIAL_TRANSITION_INVALID",
                    severity="error",
                    message=(
                        f"At least 1 entry transition should be assigned in "
                        f"non-leaf state {node.name!r}:\n{node}"
                    ),
                    span=getattr(node, "_span", None),
                    refs={
                        "composite_path": ".".join(current_path),
                        "reason": "missing_entry",
                    },
                )
            )

        for func_item in [
            *current_state.on_enters,
            *current_state.on_durings,
            *current_state.on_exits,
            *current_state.on_during_aspects,
        ]:
            if func_item.ref_state_path is not None:
                state = root_state
                walk_failed = False
                for i, segment in enumerate(func_item.ref_state_path[1:-1], start=1):
                    if segment not in state.substates:
                        # M1 from PR-110 review: the named-function ref AST
                        # nodes don't carry their own spans yet, so fall back
                        # to the owning state's span. State-level anchoring
                        # is imprecise but vastly better than line 1.
                        sink.emit(
                            ModelDiagnostic(
                                code="E_NAMED_FUNCTION_REF_NOT_FOUND",
                                severity="error",
                                message=(
                                    f"Cannot find state "
                                    f"{'.'.join(func_item.ref_state_path[: i + 1])} "
                                    f"under state "
                                    f"{'.'.join(func_item.ref_state_path[:i])}, "
                                    f"so cannot resolve reference "
                                    f"{'.'.join(func_item.ref_state_path)!r}."
                                ),
                                span=getattr(node, "_span", None),
                                refs={
                                    "ref_path": ".".join(func_item.ref_state_path),
                                    "reason": "state_not_found",
                                    "missing_segment": segment,
                                },
                            )
                        )
                        walk_failed = True
                        break
                    state = state.substates[segment]
                if walk_failed:
                    continue

                segment = func_item.ref_state_path[-1]
                if segment not in state.named_functions:
                    sink.emit(
                        ModelDiagnostic(
                            code="E_NAMED_FUNCTION_REF_NOT_FOUND",
                            severity="error",
                            message=(
                                f"Cannot find named function {segment!r} under "
                                f"state:\n{state.to_ast_node()}"
                            ),
                            span=getattr(node, "_span", None),
                            refs={
                                "ref_path": ".".join(func_item.ref_state_path),
                                "reason": "named_function_not_found",
                                "missing_segment": segment,
                            },
                        )
                    )
                    continue
                func_item.ref = state.named_functions[segment]
                assert func_item.ref.state_path == func_item.ref_state_path

        for transition in current_state.transitions:
            transition.parent = current_state

    _recursive_finish_states(
        dnode.root_state, current_state=root_state, current_path=()
    )

    def _iter_lifecycle_actions(state: State) -> Iterator[Union[OnStage, OnAspect]]:
        for func_item in [
            *state.on_enters,
            *state.on_durings,
            *state.on_exits,
            *state.on_during_aspects,
        ]:
            yield func_item
        for substate in state.substates.values():
            for func_item in _iter_lifecycle_actions(substate):
                yield func_item

    def _validate_action_ref_cycles() -> None:
        for root_func in _iter_lifecycle_actions(root_state):
            seen_by_id = {}
            chain = []
            func_item = root_func
            while func_item.ref is not None:
                func_id = id(func_item)
                if func_id in seen_by_id:
                    cycle_items = chain[seen_by_id[func_id] :] + [func_item]
                    cycle_path = " -> ".join(item.func_name for item in cycle_items)
                    sink.emit(
                        ModelDiagnostic(
                            code="E_NAMED_FUNCTION_REF_CYCLE",
                            severity="error",
                            message=f"Action reference cycle: {cycle_path}",
                            span=getattr(func_item, "_span", None),
                            refs={
                                "ref_path": root_func.func_name,
                                "cycle_path": cycle_path,
                                "reason": "action_ref_cycle",
                            },
                        )
                    )
                    break
                seen_by_id[func_id] = len(chain)
                chain.append(func_item)
                func_item = func_item.ref

    _validate_action_ref_cycles()

    machine = StateMachine(
        defines=d_defines,
        root_state=root_state,
        forced_transitions=tuple(forced_transition_declarations),
    )

    if collect:
        # In collect mode we always return the tuple. ``machine`` is the
        # best-effort build even when diagnostics were emitted; downstream
        # callers should consult ``has_errors()`` (or the diagnostics list)
        # before treating it as valid.
        return machine, sink.diagnostics

    # Strict mode: sink already raised on any error diagnostic at emit
    # time, so reaching here means the build is clean. ``finalize_or_raise``
    # is a no-op for strict mode but kept for symmetry / future-proofing.
    sink.finalize_or_raise()
    return machine
