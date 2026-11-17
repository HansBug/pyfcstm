"""Ordered region namespaces and traversal shared with hierarchical states."""

import weakref
from dataclasses import dataclass, field
from itertools import chain
from typing import Dict, Iterator, List, Optional, Tuple, TYPE_CHECKING

from .base import AstExportable
from ..diagnostics.sink import DiagnosticSink
from ..dsl import node as dsl_nodes
from ..utils.validate import ModelDiagnostic, Span

if TYPE_CHECKING:
    from .model import Event, OnAspect, State, Transition


def namespace_children(namespace):
    """Iterate direct child namespaces in declaration order."""
    return chain(namespace.substates.values(), getattr(namespace, 'regions', {}).values())


def namespace_child(namespace, name):
    """Look up an immediate state or region without searching ancestors."""
    return namespace.substates.get(name) or getattr(namespace, 'regions', {}).get(name)


def ast_namespace_children(node):
    """Iterate state and region declarations in an AST namespace."""
    return chain(node.substates, getattr(node, 'regions', ()))


def namespace_actions(namespace):
    """Iterate lifecycle and aspect actions owned by a state or region."""
    return chain(*(getattr(namespace, name, ()) for name in
                   ('on_enters', 'on_durings', 'on_exits', 'on_during_aspects')))


def walk_namespaces(namespace):
    """Yield a namespace followed by its descendants in declaration order."""
    yield namespace
    for child in namespace_children(namespace):
        yield from walk_namespaces(child)


def _ast_has_regions(node) -> bool:
    """Whether a state subtree contains a parallel owner."""
    return bool(getattr(node, 'regions', ())) or any(_ast_has_regions(child) for child in node.substates)


def validate_region_structure(node, sink: DiagnosticSink, path=()) -> bool:
    """Validate local region invariants on parsed or publicly constructed ASTs.

    Return whether an error prevents safe namespace construction. Imported
    programs are checked separately when their own assembly begins.
    """
    path = (*path, node.name)
    regions = getattr(node, 'regions', ())
    reason = None
    if isinstance(node, dsl_nodes.RegionDefinition) and not node.substates:
        reason = 'empty_region'
    elif regions and node.substates:
        reason = 'mixed_children'
    elif regions and (node.transitions or node.force_transitions or node.imports or node.histories):
        reason = 'owner_statements'
    elif getattr(node, 'histories', ()) and _ast_has_regions(node):
        reason = 'history_boundary'
    invalid = reason is not None
    if invalid:
        sink.emit(ModelDiagnostic(
            code='E_REGION_STRUCTURE', severity='error',
            message='Invalid region structure at %s (%s).' % ('.'.join(path), reason),
            span=node._span, refs={'namespace_path': '.'.join(path), 'reason': reason,
                                  'source_path': getattr(node, '_source_path', None)},
        ))
    seen = {}
    for region in regions:
        if region.name in seen:
            invalid = True
            sink.emit(ModelDiagnostic(
                code='E_DUPLICATE_REGION', severity='error',
                message='Duplicate region %r in %s.' % (region.name, '.'.join(path)),
                span=region._span,
                refs={'region_name': region.name, 'owner_path': '.'.join(path),
                      'previous_span': seen[region.name],
                      'source_path': getattr(region, '_source_path', None)},
            ))
        seen[region.name] = region._span
    for child in chain(node.substates, regions):
        invalid = validate_region_structure(child, sink, path) or invalid
    return invalid


@dataclass
class Region(AstExportable):
    """A named ordered namespace within a parallel owner state.

    Regions own transitions, events and during aspects, but do not have state
    lifecycle actions and cannot themselves be transition endpoints. Models
    build regions while converting the AST; use :attr:`State.regions` to reach
    them, not this constructor.

    :param name: Region identifier.
    :type name: str
    :param path: Full namespace path including this region.
    :type path: Tuple[str, ...]
    :param substates: Child states in declaration order.
    :type substates: Dict[str, State]
    :param events: Events belonging to this region.
    :type events: Dict[str, Event], optional
    :param transitions: Ordered initial, ordinary and forced transitions.
    :type transitions: List[Transition], optional
    :param named_functions: Named during-aspect declarations.
    :type named_functions: Dict[str, OnAspect], optional
    :param on_during_aspects: Before/after during aspects.
    :type on_during_aspects: List[OnAspect], optional
    :param doc: Source documentation.
    :type doc: Optional[str], optional

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text(
        ...     'state Root { region Motor { [*] -> Off; state Off; } }'
        ... )
        >>> region = model.root_state.regions['Motor']
        >>> region.path
        ('Root', 'Motor')
        >>> list(region.substates)
        ['Off']
    """

    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, 'Event'] = field(default_factory=dict)
    transitions: List['Transition'] = field(default_factory=list)
    named_functions: Dict[str, 'OnAspect'] = field(default_factory=dict)
    on_during_aspects: List['OnAspect'] = field(default_factory=list)
    doc: Optional[str] = None
    _span: Optional[Span] = field(default=None, repr=False, compare=False)
    parent_ref: Optional[weakref.ReferenceType] = field(default=None, repr=False, compare=False)
    substate_name_to_id: Dict[str, int] = field(init=False)

    def __post_init__(self) -> None:
        """Number child states in declaration order for transition expansion."""
        self.substate_name_to_id = {name: index for index, name in enumerate(self.substates)}

    @property
    def parent(self) -> Optional['State']:
        """Return the state owning this region, or None before attachment."""
        return None if self.parent_ref is None else self.parent_ref()

    @parent.setter
    def parent(self, owner: Optional['State']) -> None:
        self.parent_ref = None if owner is None else weakref.ref(owner)

    @property
    def is_root_state(self) -> bool:
        """Return ``False``: a region is always owned by a state.

        This lets code that handles states and regions uniformly, such as the
        simulator's transition labels, ask the question without a type check.

        :return: Always ``False``.
        :rtype: bool

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text(
            ...     'state Root { region R { [*] -> A; state A; } }'
            ... )
            >>> model.root_state.regions['R'].is_root_state
            False
        """
        return False

    @property
    def init_transitions(self) -> List['Transition']:
        """Return region initial transitions in declaration order."""
        return [edge for edge in self.transitions if edge.from_state is dsl_nodes.INIT_STATE]

    def walk_states(self) -> Iterator['State']:
        """Yield child states recursively, excluding region containers."""
        for state in self.substates.values():
            yield from state.walk_states()

    def walk_regions(self) -> Iterator['Region']:
        """Yield this region and nested regions in declaration order."""
        for namespace in walk_namespaces(self):
            if isinstance(namespace, Region):
                yield namespace

    def resolve_event(self, event_ref: str, *, collect_into=None):
        """Resolve an event using relative, parent-relative or root paths.

        :param event_ref: Event path using the same syntax as State.resolve_event.
        :param collect_into: Optional sink for collecting lookup errors.
        :return: The resolved event, or None after a collected error.
        """
        from .model import State

        return State.resolve_event(self, event_ref, collect_into=collect_into)

    def list_on_during_aspects(self, is_abstract=None, aspect=None, with_ids=False):
        """Return region aspects with the same filters as state aspects.

        :param is_abstract: Optional abstract/concrete action filter.
        :param aspect: Optional ``before`` or ``after`` filter.
        :param with_ids: Include one-based local action indices.
        :return: Matching actions or ``(index, action)`` pairs.
        """
        from .model import State

        return State.list_on_during_aspects(self, is_abstract, aspect, with_ids)

    def iter_on_during_before_aspect_recursively(self, is_abstract=None, with_ids=False):
        """Yield ancestor and region before-aspects in enclosing order.

        :param is_abstract: Optional abstract/concrete action filter.
        :param with_ids: Include one-based local action indices.
        :yield: Namespace/action pairs, optionally preceded by an index.
        """
        from .model import State

        yield from State.iter_on_during_before_aspect_recursively(self, is_abstract, with_ids)

    def iter_on_during_after_aspect_recursively(self, is_abstract=None, with_ids=False):
        """Yield region and ancestor after-aspects in enclosing reverse order.

        :param is_abstract: Optional abstract/concrete action filter.
        :param with_ids: Include one-based local action indices.
        :yield: Namespace/action pairs, optionally preceded by an index.
        """
        from .model import State

        yield from State.iter_on_during_after_aspect_recursively(self, is_abstract, with_ids)

    def to_ast_node(self) -> dsl_nodes.RegionDefinition:
        """Export the namespace as a region declaration, preserving order."""
        from .model import State
        from .imports import _mark_generated_combo_pseudo_node

        children = [state.to_ast_node() for state in self.substates.values()]
        node = dsl_nodes.RegionDefinition(
            name=self.name,
            substates=children,
            transitions=[State.transition_to_ast_node(self, edge) for edge in self.transitions],
            events=[event.to_ast_node() for event in self.events.values()],
            during_aspects=[action.to_ast_node() for action in self.on_during_aspects],
            doc=self.doc,
        )
        for state, child in zip(self.substates.values(), children):
            if state.is_pseudo and state.is_combo_relay:
                _mark_generated_combo_pseudo_node(child, node)
        return node
