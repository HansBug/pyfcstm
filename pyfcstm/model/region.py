"""
Ordered region namespaces and traversal shared with hierarchical states.

A state either owns child states or owns named regions, never both. A region
is an ordered namespace: it holds child states, its own events, transitions
and ``>> during before/after`` aspects, but no ``enter``/``during``/``exit``
actions of its own, and it is never a transition endpoint. Because states and
regions both contain states and are addressed by dotted paths, the traversal
helpers here treat them uniformly as *namespaces*: anything with a
``substates`` mapping, plus an optional ``regions`` mapping.

The module contains:

* :func:`namespace_children` - Direct child states and regions of a namespace
* :func:`namespace_child` - Look up one immediate child by name
* :func:`ast_namespace_children` - The same listing for DSL AST nodes
* :func:`namespace_actions` - Lifecycle and aspect actions owned by a namespace
* :func:`walk_namespaces` - Depth-first walk over a namespace subtree
* :func:`shown_namespace` - The state or region that is shown in place of one
  of a machine whose forced declarations were lowered
* :func:`validate_region_structure` - Check region invariants on an AST
* :class:`Region` - A named ordered namespace inside a parallel owner state

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     [*] -> Run;
    ...     state Run {
    ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
    ...         region Guard { [*] -> Watch; state Watch; }
    ...     }
    ...     state Off;
    ...     Run -> Off :: Halt;
    ... }
    ... ''')
    >>> root = model.root_state
    >>> run = root.substates['Run']
    >>> from pyfcstm.model.region import namespace_children, walk_namespaces
    >>> [child.name for child in namespace_children(run)]
    ['Motion', 'Guard']
    >>> ['.'.join(namespace.path) for namespace in walk_namespaces(run)]
    ['Root.Run', 'Root.Run.Motion', 'Root.Run.Motion.Stop', 'Root.Run.Motion.Move', 'Root.Run.Guard', 'Root.Run.Guard.Watch']
"""

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
    """
    Iterate the direct child namespaces of a state or region.

    A state yields its child states, then its regions; a region yields its
    child states. Because a state owns either states or regions, never both,
    only one of the two groups is ever non-empty, and each group is in
    declaration order.

    :param namespace: A :class:`~pyfcstm.model.model.State` or
        :class:`Region`.
    :type namespace: Union[pyfcstm.model.model.State, Region]
    :return: Lazily iterated child states and regions.
    :rtype: Iterator[Union[pyfcstm.model.model.State, Region]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off :: Halt;
        ... }
        ... ''')
        >>> root = model.root_state
        >>> run = root.substates['Run']
        >>> from pyfcstm.model.region import namespace_children
        >>> [child.name for child in namespace_children(root)]
        ['Run', 'Off']
        >>> [type(child).__name__ for child in namespace_children(run)]
        ['Region', 'Region']
        >>> [child.name for child in namespace_children(run.regions['Motion'])]
        ['Stop', 'Move']
    """
    return chain(namespace.substates.values(), getattr(namespace, 'regions', {}).values())


def namespace_child(namespace, name):
    """
    Look up an immediate child state or region by name.

    Only the direct children of ``namespace`` are searched: there is no
    ancestor search and no dotted-path handling, so ``'Motion.Stop'`` finds
    nothing.

    :param namespace: A :class:`~pyfcstm.model.model.State` or
        :class:`Region`.
    :type namespace: Union[pyfcstm.model.model.State, Region]
    :param name: Child name, a single identifier.
    :type name: str
    :return: The matching state or region, or ``None`` if there is none.
    :rtype: Optional[Union[pyfcstm.model.model.State, Region]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off :: Halt;
        ... }
        ... ''')
        >>> root = model.root_state
        >>> run = root.substates['Run']
        >>> from pyfcstm.model.region import namespace_child
        >>> namespace_child(run, 'Motion').path
        ('Root', 'Run', 'Motion')
        >>> namespace_child(root, 'Off').name
        'Off'
        >>> namespace_child(run, 'Stop') is None
        True
    """
    return namespace.substates.get(name) or getattr(namespace, 'regions', {}).get(name)


def ast_namespace_children(node):
    """
    Iterate the state and region declarations directly inside an AST node.

    This is the DSL-tree counterpart of :func:`namespace_children`: it works on
    :class:`~pyfcstm.dsl.node.StateDefinition` and
    :class:`~pyfcstm.dsl.node.RegionDefinition` nodes before a model exists.

    :param node: A state or region declaration.
    :type node: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
    :return: Child state declarations, then region declarations.
    :rtype: Iterator[Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]]

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model.region import ast_namespace_children
        >>> program = parse_with_grammar_entry('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ... }
        ... ''', 'state_machine_dsl')
        >>> root = program.root_state
        >>> [child.name for child in ast_namespace_children(root)]
        ['Run', 'Off']
        >>> [type(child).__name__ for child in ast_namespace_children(root.substates[0])]
        ['RegionDefinition', 'RegionDefinition']
    """
    return chain(node.substates, getattr(node, 'regions', ()))


def namespace_actions(namespace):
    """
    Iterate every lifecycle and aspect action a state or region owns.

    Actions are listed in the order ``on_enters``, ``on_durings``,
    ``on_exits``, ``on_during_aspects``. A region has no lifecycle actions of
    its own, so it only contributes its ``>> during before/after`` aspects.

    :param namespace: A :class:`~pyfcstm.model.model.State` or
        :class:`Region`.
    :type namespace: Union[pyfcstm.model.model.State, Region]
    :return: Lazily iterated :class:`~pyfcstm.model.model.OnStage` and
        :class:`~pyfcstm.model.model.OnAspect` objects.
    :rtype: Iterator[Union[pyfcstm.model.model.OnStage, pyfcstm.model.model.OnAspect]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.region import namespace_actions
        >>> model = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root {
        ...     >> during before { x = x + 1; }
        ...     [*] -> Run;
        ...     state Run {
        ...         enter { x = 0; }
        ...         region Motion {
        ...             >> during after { x = x + 2; }
        ...             [*] -> Stop;
        ...             state Stop;
        ...         }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ... }
        ... ''')
        >>> run = model.root_state.substates['Run']
        >>> [(type(action).__name__, action.stage) for action in namespace_actions(run)]
        [('OnStage', 'enter')]
        >>> [(type(action).__name__, action.aspect) for action in namespace_actions(run.regions['Motion'])]
        [('OnAspect', 'after')]
    """
    return chain(*(getattr(namespace, name, ()) for name in
                   ('on_enters', 'on_durings', 'on_exits', 'on_during_aspects')))


def shown_namespace(namespace):
    """
    Return the state or region that is shown in place of ``namespace``.

    A machine that lowered a forced declaration (see
    :mod:`pyfcstm.model.forced`) is drawn through the machine that keeps the
    plain expansion, and so is any state or region of it: the PlantUML text of
    every level comes from the counterpart with the same path in that machine.
    The DSL export does not use it: a state or region exports itself, as the
    machine does, and the text it writes loads to the machine that runs.

    Every other namespace, and every namespace of the plain machine itself, is
    its own counterpart. So is a gate that forced lowering added
    (:attr:`pyfcstm.model.model.State.is_forced_gate`): it exists only in the
    machine that runs and has nothing to stand in for it.

    :param namespace: A state or a region of a built machine.
    :type namespace: Union[pyfcstm.model.model.State, Region]
    :return: The namespace to show.
    :rtype: Union[pyfcstm.model.model.State, Region]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.region import shown_namespace
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { region A { [*] -> A1; state A1; } }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> root = model.root_state
        >>> shown = shown_namespace(root)
        >>> shown is root, shown.path == root.path
        (False, True)
        >>> '__forced' in str(root.to_ast_node())
        True
    """
    view = getattr(namespace, "_plain_forced_view", None)
    if view is None:
        return namespace
    shown = view.machine().root_state
    for name in namespace.path[1:]:
        regions = getattr(shown, "regions", None)
        if regions and name in regions:
            shown = regions[name]
        elif name in shown.substates:
            shown = shown.substates[name]
        else:
            # A gate of forced lowering exists only in the machine that runs.
            return namespace
    return shown


def walk_namespaces(namespace):
    """
    Walk a namespace subtree depth first, parents before children.

    Every state and every region in the subtree is yielded exactly once, in
    declaration order, starting with ``namespace`` itself. Region containers
    appear in the walk; use :meth:`~pyfcstm.model.model.State.walk_states` when
    only states are wanted.

    :param namespace: Root of the walk, a :class:`~pyfcstm.model.model.State`
        or :class:`Region`.
    :type namespace: Union[pyfcstm.model.model.State, Region]
    :return: Generator of the namespace and all its descendants.
    :rtype: Iterator[Union[pyfcstm.model.model.State, Region]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off :: Halt;
        ... }
        ... ''')
        >>> root = model.root_state
        >>> run = root.substates['Run']
        >>> from pyfcstm.model.region import walk_namespaces
        >>> ['.'.join(item.path) for item in walk_namespaces(run.regions['Guard'])]
        ['Root.Run.Guard', 'Root.Run.Guard.Watch']
        >>> [type(item).__name__ for item in walk_namespaces(run)]
        ['State', 'Region', 'State', 'State', 'Region', 'State']
    """
    yield namespace
    for child in namespace_children(namespace):
        yield from walk_namespaces(child)


def _ast_has_regions(node) -> bool:
    """
    Whether an AST subtree declares any region.

    :param node: State or region declaration to search, including itself.
    :type node: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
    :return: ``True`` if ``node`` or any descendant state has a region.
    :rtype: bool
    """
    return bool(getattr(node, 'regions', ())) or any(_ast_has_regions(child) for child in node.substates)


def validate_region_structure(node, sink: DiagnosticSink, path=()) -> bool:
    """
    Validate local region invariants on parsed or publicly constructed ASTs.

    Return whether an error prevents safe namespace construction. Imported
    programs are checked separately when their own assembly begins.

    The checks per node are, in priority order, ``E_REGION_STRUCTURE`` with
    reason ``empty_region`` (a region without states), ``mixed_children`` (a
    state with both states and regions), ``owner_statements`` (a parallel owner
    with its own transitions, forced transitions, imports or histories) and
    ``history_boundary`` (a state with history whose subtree contains regions);
    plus ``E_DUPLICATE_REGION`` for repeated region names in one owner. The
    walk always recurses into every child, so with a collecting sink one call
    reports, for every node of the subtree, at most one ``E_REGION_STRUCTURE``
    (the first matching reason) plus every duplicate region name.

    :param node: Root state or region declaration to check, with its subtree.
    :type node: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
    :param sink: Where diagnostics go. A strict sink raises
        :class:`~pyfcstm.utils.validate.ModelValidationError` on the first one;
        a collecting sink records them all.
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink
    :param path: Names of the ancestors of ``node``, used to build messages.
        Defaults to ``()``.
    :type path: Tuple[str, ...], optional
    :return: ``True`` if any error was found; ``False`` if the subtree is safe.
    :rtype: bool
    :raises pyfcstm.utils.validate.ModelValidationError: If ``sink`` is strict
        and a problem is found.

    Example::

        >>> from pyfcstm.diagnostics.sink import DiagnosticSink
        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model.region import validate_region_structure
        >>> good = parse_with_grammar_entry(
        ...     'state Root { region A { [*] -> X; state X; } region B { [*] -> Y; state Y; } }',
        ...     'state_machine_dsl').root_state
        >>> sink = DiagnosticSink(collect=True)
        >>> validate_region_structure(good, sink), sink.diagnostics
        (False, [])
        >>> bad = parse_with_grammar_entry(
        ...     'state Root { region A { } region A { [*] -> X; state X; } }',
        ...     'state_machine_dsl').root_state
        >>> sink = DiagnosticSink(collect=True)
        >>> validate_region_structure(bad, sink)
        True
        >>> [(item.code, item.message) for item in sink.diagnostics]
        [('E_DUPLICATE_REGION', "Duplicate region 'A' in Root."), ('E_REGION_STRUCTURE', 'Invalid region structure at Root.A (empty_region).')]
        >>> from pyfcstm.utils.validate import ModelValidationError
        >>> try:
        ...     validate_region_structure(bad, DiagnosticSink())
        ... except ModelValidationError as error:
        ...     print([item.code for item in error.diagnostics])
        ['E_DUPLICATE_REGION']
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
    """
    A named ordered namespace within a parallel owner state.

    Regions own transitions, events and during aspects, but do not have state
    lifecycle actions and cannot themselves be transition endpoints.

    The declaration order of the regions inside one owner is preserved by the
    model and by :meth:`to_ast_node`. Regions are built by
    :func:`~pyfcstm.model.model.parse_dsl_node_to_state_machine` and reached
    through :attr:`pyfcstm.model.model.State.regions`; construct one directly
    only when assembling a model by hand.

    :param name: Region identifier.
    :type name: str
    :param path: Full namespace path including this region.
    :type path: Tuple[str, ...]
    :param substates: Child states in declaration order.
    :type substates: Dict[str, pyfcstm.model.model.State]
    :param events: Events belonging to this region, defaults to an empty dict.
    :type events: Dict[str, pyfcstm.model.model.Event], optional
    :param transitions: Ordered initial, ordinary and forced transitions,
        defaults to an empty list.
    :type transitions: List[pyfcstm.model.model.Transition], optional
    :param named_functions: Named during-aspect declarations, defaults to an
        empty dict.
    :type named_functions: Dict[str, pyfcstm.model.model.OnAspect], optional
    :param on_during_aspects: Before/after during aspects, defaults to an empty
        list.
    :type on_during_aspects: List[pyfcstm.model.model.OnAspect], optional
    :param doc: Source documentation, defaults to ``None``.
    :type doc: Optional[str], optional

    :ivar substate_name_to_id: Zero-based index of each child state in
        declaration order, filled in on construction.
    :vartype substate_name_to_id: Dict[str, int]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root {
        ...     >> during before { x = x + 1; }
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion {
        ...             >> during after { x = x + 2; }
        ...             >> during before abstract Sample;
        ...             event Go;
        ...             [*] -> Stop;
        ...             state Stop;
        ...             state Active {
        ...                 region Inner { [*] -> A; state A; }
        ...             }
        ...             Stop -> Active :: Go;
        ...         }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ... }
        ... ''')
        >>> run = model.root_state.substates['Run']
        >>> motion = run.regions['Motion']
        >>> motion.name, motion.path
        ('Motion', ('Root', 'Run', 'Motion'))
        >>> list(motion.substates), motion.substate_name_to_id
        (['Stop', 'Active'], {'Stop': 0, 'Active': 1})
        >>> motion.parent is run
        True
        >>> run.regions['Guard'].events
        {}
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
        """
        Number child states in declaration order for transition expansion.

        The numbering is stored in :attr:`substate_name_to_id`.

        :return: ``None``.
        :rtype: None
        """
        self.substate_name_to_id = {name: index for index, name in enumerate(self.substates)}

    @property
    def parent(self) -> Optional['State']:
        """
        The state that owns this region.

        The link is held weakly, so a region never keeps its owner alive and
        the property returns ``None`` before attachment or after the owner has
        been garbage collected. Assigning ``None`` detaches the region.

        :return: The owning :class:`~pyfcstm.model.model.State`, or ``None``.
        :rtype: Optional[pyfcstm.model.model.State]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> motion.parent.name
            'Run'
            >>> motion.parent = None
            >>> motion.parent is None
            True
            >>> motion.parent = run
            >>> motion.parent.name
            'Run'
        """
        return None if self.parent_ref is None else self.parent_ref()

    @parent.setter
    def parent(self, owner: Optional['State']) -> None:
        """
        Attach this region to an owner state, or detach it with ``None``.

        :param owner: The owning state, or ``None`` to detach.
        :type owner: Optional[pyfcstm.model.model.State]
        :return: ``None``.
        :rtype: None

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run { region Motion { [*] -> Stop; state Stop; } region Guard { [*] -> Watch; state Watch; } }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> motion.parent = None
            >>> motion.parent is None
            True
            >>> motion.parent = run
            >>> motion.parent is run
            True
        """
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
        """
        Initial transitions (``[*] -> Child``) of this region.

        :return: The transitions whose source is the initial pseudo state, in
            declaration order.
        :rtype: List[pyfcstm.model.model.Transition]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [str(edge.to_state) for edge in motion.init_transitions]
            ['Stop']
            >>> len(motion.transitions)
            2
        """
        return [edge for edge in self.transitions if edge.from_state is dsl_nodes.INIT_STATE]

    def walk_states(self) -> Iterator['State']:
        """
        Walk every state inside this region, depth first.

        Child states come in declaration order, each followed by its own
        descendants (including states inside nested regions). Region containers
        themselves are not yielded; use :meth:`walk_regions` for those.

        :return: Generator of :class:`~pyfcstm.model.model.State` objects.
        :rtype: Iterator[pyfcstm.model.model.State]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [state.name for state in motion.walk_states()]
            ['Stop', 'Active', 'A']
        """
        for state in self.substates.values():
            yield from state.walk_states()

    def walk_regions(self) -> Iterator['Region']:
        """
        Walk this region and every region nested below it.

        :return: Generator starting with this region, then nested regions in
            declaration order.
        :rtype: Iterator[Region]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [region.name for region in motion.walk_regions()]
            ['Motion', 'Inner']
            >>> [region.name for region in run.regions['Guard'].walk_regions()]
            ['Guard']
        """
        for namespace in walk_namespaces(self):
            if isinstance(namespace, Region):
                yield namespace

    def resolve_event(self, event_ref: str, *, collect_into=None):
        """
        Resolve an event using relative, parent-relative or root paths.

        A region is its own event namespace: ``Go`` resolves to an event
        declared in this region, ``.`` and ``/`` prefixes follow the same rules
        as :meth:`pyfcstm.model.model.State.resolve_event`.

        :param event_ref: Event path using the same syntax as State.resolve_event.
        :type event_ref: str
        :param collect_into: Optional sink for collecting lookup errors; with
            ``None`` the first failure raises. Defaults to ``None``.
        :type collect_into: Optional[pyfcstm.diagnostics.sink.DiagnosticSink], optional
        :return: The resolved event, or None after a collected error.
        :rtype: Optional[pyfcstm.model.model.Event]
        :raises pyfcstm.utils.validate.ModelLookupError: If the event cannot be
            found and ``collect_into`` is not a collecting sink.
        :raises pyfcstm.utils.validate.ModelValueError: If ``event_ref`` is not
            a valid event path (for example an empty string), under the same
            sink rule.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> motion.resolve_event('Go').path
            ('Root', 'Run', 'Motion', 'Go')
            >>> from pyfcstm.diagnostics.sink import DiagnosticSink
            >>> sink = DiagnosticSink(collect=True)
            >>> motion.resolve_event('Nope', collect_into=sink) is None
            True
            >>> [item.code for item in sink.diagnostics]
            ['E_EVENT_NOT_FOUND']
            >>> from pyfcstm.utils.validate import ModelLookupError
            >>> try:
            ...     motion.resolve_event('Nope')
            ... except ModelLookupError as error:
            ...     print([item.code for item in error.diagnostics])
            ['E_EVENT_NOT_FOUND']
        """
        from .model import State

        return State.resolve_event(self, event_ref, collect_into=collect_into)

    def list_on_during_aspects(self, is_abstract=None, aspect=None, with_ids=False):
        """
        Return region aspects with the same filters as state aspects.

        :param is_abstract: ``True`` for abstract actions only, ``False`` for
            concrete only, ``None`` for both. Defaults to ``None``.
        :type is_abstract: Optional[bool], optional
        :param aspect: ``'before'`` or ``'after'`` to keep one kind, ``None``
            for both. Defaults to ``None``.
        :type aspect: Optional[str], optional
        :param with_ids: Include one-based local action indices. Defaults to
            ``False``.
        :type with_ids: bool, optional
        :return: Matching :class:`~pyfcstm.model.model.OnAspect` objects, or
            ``(index, action)`` pairs when ``with_ids`` is true.
        :rtype: list

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [(action.aspect, action.is_abstract) for action in motion.list_on_during_aspects()]
            [('after', False), ('before', True)]
            >>> [action.aspect for action in motion.list_on_during_aspects(is_abstract=False)]
            ['after']
            >>> [(index, action.aspect) for index, action in motion.list_on_during_aspects(aspect='before', with_ids=True)]
            [(2, 'before')]
        """
        from .model import State

        return State.list_on_during_aspects(self, is_abstract, aspect, with_ids)

    def iter_on_during_before_aspect_recursively(self, is_abstract=None, with_ids=False):
        """
        Yield ancestor and region before-aspects in enclosing order.

        The outermost ancestor's ``>> during before`` actions come first and
        this region's own come last.

        :param is_abstract: ``True`` for abstract actions only, ``False`` for
            concrete only, ``None`` for both. Defaults to ``None``.
        :type is_abstract: Optional[bool], optional
        :param with_ids: Include one-based local action indices. Defaults to
            ``False``.
        :type with_ids: bool, optional
        :yield: Namespace/action pairs, optionally preceded by an index.
        :rtype: Iterator[tuple]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [(owner.name, action.is_abstract) for owner, action in motion.iter_on_during_before_aspect_recursively()]
            [('Root', False), ('Motion', True)]
            >>> [(index, owner.name) for index, owner, action in motion.iter_on_during_before_aspect_recursively(with_ids=True)]
            [(1, 'Root'), (2, 'Motion')]
        """
        from .model import State

        yield from State.iter_on_during_before_aspect_recursively(self, is_abstract, with_ids)

    def iter_on_during_after_aspect_recursively(self, is_abstract=None, with_ids=False):
        """
        Yield region and ancestor after-aspects in enclosing reverse order.

        This region's own ``>> during after`` actions come first and the
        outermost ancestor's last, the mirror image of
        :meth:`iter_on_during_before_aspect_recursively`.

        :param is_abstract: ``True`` for abstract actions only, ``False`` for
            concrete only, ``None`` for both. Defaults to ``None``.
        :type is_abstract: Optional[bool], optional
        :param with_ids: Include one-based local action indices. Defaults to
            ``False``.
        :type with_ids: bool, optional
        :yield: Namespace/action pairs, optionally preceded by an index.
        :rtype: Iterator[tuple]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... def int x = 0;
            ... state Root {
            ...     >> during before { x = x + 1; }
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion {
            ...             >> during after { x = x + 2; }
            ...             >> during before abstract Sample;
            ...             event Go;
            ...             [*] -> Stop;
            ...             state Stop;
            ...             state Active {
            ...                 region Inner { [*] -> A; state A; }
            ...             }
            ...             Stop -> Active :: Go;
            ...         }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> run = model.root_state.substates['Run']
            >>> motion = run.regions['Motion']
            >>> [(owner.name, action.aspect) for owner, action in motion.iter_on_during_after_aspect_recursively()]
            [('Motion', 'after')]
        """
        from .model import State

        yield from State.iter_on_during_after_aspect_recursively(self, is_abstract, with_ids)

    def to_plantuml(self, options=None, current_depth: int = 0, event_colors=None) -> str:
        """Convert this region to the body of a PlantUML concurrent section.

        PlantUML concurrent sections (separated by ``--`` inside a composite
        state) are anonymous, so the text starts with a floating note reading
        ``region N: Name``, where ``N`` is the one-based declaration (and
        therefore execution) position among the owner's regions, followed by
        the region's ``>> during`` aspects when they are shown. Child states
        and transitions come next; ``active("...")`` is shown as written.

        The result is a fragment, not a diagram: it is meant to sit inside the
        composite drawn by :meth:`pyfcstm.model.model.State.to_plantuml`, which
        puts ``--`` between the fragments of its regions.

        :param options: Detail level name, :class:`~pyfcstm.model.plantuml.PlantUMLOptions`
            or ``None`` for the defaults, defaults to ``None``.
        :type options: PlantUMLOptionsInput, optional
        :param current_depth: Depth of this region; a region counts as one
            level for ``max_depth``, defaults to ``0``.
        :type current_depth: int, optional
        :param event_colors: Event path to colour mapping used by the event
            colouring modes, defaults to ``None`` (no colours).
        :type event_colors: Optional[Dict[str, str]], optional
        :return: PlantUML text of the region body without a trailing newline.
        :rtype: str

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> machine = load_state_machine_from_text(
            ...     'state Root { region Motor { state Off; [*] -> Off; } }')
            >>> print(machine.root_state.regions['Motor'].to_plantuml('minimal'))
            note as root__motor
                **region 1: Motor**
            end note
            state "Off" as root__motor__off
            [*] --> root__motor__off
        """
        from .model import _region_to_plantuml

        return _region_to_plantuml(
            shown_namespace(self), options, current_depth, event_colors
        )

    def to_ast_node(self) -> dsl_nodes.RegionDefinition:
        """
        Export this region as a DSL ``region`` declaration.

        Child states, transitions, events and aspects keep their declaration
        order in the exported node.

        :return: A :class:`~pyfcstm.dsl.node.RegionDefinition` whose string form
            is valid FCSTM source.
        :rtype: pyfcstm.dsl.node.RegionDefinition

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { event Go; [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> motion = model.root_state.substates['Run'].regions['Motion']
            >>> print(motion.to_ast_node())
            region Motion {
                state Stop;
                event Go;
                [*] -> Stop;
            }
        """
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
