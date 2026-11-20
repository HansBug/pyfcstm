"""
Forced transitions that reach regions, lowered into plain transitions.

A forced transition ``!S -> T : /Stop;`` is syntactic sugar: model conversion
expands it into ordinary transitions, so the simulator, templates and BMC never
see a forced construct. For a state ``S`` that contains no state owning regions
the expansion is the plain one, a ``-> [*]`` transition on every state below
``S`` that repeats the event and the guard, and this module does not touch it.

When ``S`` contains a state that owns regions, taking ``S`` away has to take the
whole group of every such owner away, and the event and the guard must be
decided **once**, at the place where the machine rests. The expansion therefore
works in two steps.

Expansion (done while forced transitions are resolved):

* Every stoppable state below ``S`` that is outside a region, and every
  stoppable state inside a region of an owner below ``S``, gets a transition
  that repeats the declared event and guard. Outside regions it is a plain
  ``-> [*]`` transition. Inside a region it is an *exit-group* transition
  (:attr:`pyfcstm.model.model.Transition.exit_group_levels`): when it is taken
  the whole group of the outermost owner below ``S`` leaves, regions in reverse
  declaration order and deepest state first, and control returns to that owner.
* Pseudo states get none: they are never rested in.
* On the level of the declaration the transition ``S -> T`` is the declared one.

Lowering (this module, :func:`lower_forced`): one hidden ``int`` variable
``__forced_<n>`` per declaration records that the event and the guard were
already decided.

1. The transitions that start the exit from a resting state raise the variable
   in their effect and keep the declared event and guard.
2. Every composite or owner on the way up gets a relay transition that has no
   event and only waits for the variable.
3. On the level of the declaration a copy that waits for the variable and
   lowers it goes first; the declared transition stays behind it for the case
   that control comes back to its source without the variable raised.
4. While the variable is raised, every other outgoing transition of the states
   on the way gives way, the declared transition included: each of them gets
   the extra condition that the variable is lowered. A forced transition whose
   target cannot be entered therefore takes nothing, whatever else leaves the
   same state.

This is the only place where a transition of the model carries an event and a
guard at the same time: rule 4 adds a condition to a transition that may have an
event. The simulator evaluates both. The language cannot write the pair, and
neither can it write the relays and the exit-group transitions, so a lowered
machine is never exported or drawn.

The module contains:

* :func:`lower_forced` - Install the hidden variables and the relay edges

Everything that shows the model as its author wrote it, the DSL export, the
PlantUML export and the diagram snapshot, uses the machine that keeps the plain
expansion instead (see :meth:`pyfcstm.model.model.StateMachine.to_ast_node`).
Static analyses judge that machine too: model conversion builds it before
lowering (see :func:`pyfcstm.diagnostics.inspect.inspect_model`), where forced
transitions stop at owners. An analysis that is handed the lowered machine
directly, such as :func:`pyfcstm.verify.run_inspect_algorithms`, sees the hidden
variables and the carrying transitions like any other part of the model, as it
does for a lowered history.

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     event Stop;
    ...     [*] -> Run;
    ...     state Run {
    ...         region A { [*] -> A1; state A1; }
    ...         region B { [*] -> B1; state B1; }
    ...     }
    ...     state Idle;
    ...     !Run -> Idle : /Stop;
    ... }
    ... ''')
    >>> list(model.defines)
    ['__forced_0']
    >>> run = model.root_state.substates['Run']
    >>> [(t.from_state, t.to_state, t.exit_group_levels)
    ...  for region in run.regions.values()
    ...  for t in region.transitions if t.exit_group_levels]
    [('A1', EXIT_STATE, 1), ('B1', EXIT_STATE, 1)]
    >>> [str(t.guard) for t in model.root_state.transitions if t.from_state == 'Run']
    ['__forced_0 == 1', '__forced_0 == 0']
"""

import re
from dataclasses import dataclass, replace
from itertools import count
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Union

from ..diagnostics.sink import DiagnosticSink
from ..dsl import node as dsl_nodes
from ..utils.validate import ModelDiagnostic
from .expr import BinaryOp, Integer, Variable, parse_expr_node_to_expr
from .model import (
    Event,
    Operation,
    OperationStatement,
    State,
    Transition,
    VarDefine,
    _event_origin_from_id,
    _node_span,
)
from .region import Region, namespace_actions, namespace_child, walk_namespaces

__all__ = ["ForcedExpansion", "ForcedInheritance", "lower_forced"]

_Namespace = Union[State, Region]

# Marks left on transitions by the expansion in
# :func:`pyfcstm.model.model.parse_dsl_node_to_state_machine`: the number of the
# declaration and whether the transition is the one declared on its own level.
_ID_MARK = "_forced_id"
_DECLARED_MARK = "_forced_declared"

def _scope_has_regions(scope: Any) -> bool:
    """
    Tell whether a declaration scope contains a state that owns regions.

    :param scope: A state or region declaration.
    :type scope: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
    :return: ``True`` if ``scope`` or anything below it owns regions.
    :rtype: bool
    """
    return bool(getattr(scope, "regions", ())) or any(
        _scope_has_regions(substate) for substate in scope.substates
    )

def _force_reaches_regions(node: Any, from_state: Any) -> bool:
    """
    Tell whether a forced declaration acts on a state that owns regions.

    A declaration is expanded into regions only when the states it applies
    to contain an owner. Every other declaration keeps its plain expansion,
    so a machine without regions never changes.

    :param node: Declaration scope the transition is written in.
    :type node: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
    :param from_state: Source of the declaration, a state name or ``*``.
    :type from_state: Union[str, pyfcstm.dsl.node._StateSingletonMark]
    :return: ``True`` if one of the states the declaration applies to owns
        regions or contains a state that does.
    :rtype: bool
    """
    return any(
        _scope_has_regions(substate)
        for substate in node.substates
        if from_state is dsl_nodes.ALL or substate.name == from_state
    )

def _forced_node(
    event_id: Any,
    condition_expr: Any,
    event_scope: Any,
    origin: Any,
    span: Any,
    source_path: Optional[str],
    forced_id: Optional[int],
    exit_levels: int,
) -> dsl_nodes.ForceTransitionDefinition:
    """
    Build the node that carries a forced declaration one level deeper.

    :param event_id: Event of the declaration, if any.
    :type event_id: Optional[pyfcstm.dsl.node.ChainID]
    :param condition_expr: Guard of the declaration, if any.
    :type condition_expr: Optional[pyfcstm.dsl.node.Expr]
    :param event_scope: Scope of ``event_id``.
    :type event_scope: Optional[str]
    :param origin: Original text of the declaration.
    :type origin: Optional[str]
    :param span: Source span of the declaration.
    :type span: Optional[Span]
    :param source_path: File the declaration was written in.
    :type source_path: Optional[str]
    :param forced_id: Number of the declaration when it reaches regions.
    :type forced_id: Optional[int]
    :param exit_levels: Number of owners crossed so far.
    :type exit_levels: int
    :return: A node that applies to every state of the next level.
    :rtype: pyfcstm.dsl.node.ForceTransitionDefinition
    """
    carried = dsl_nodes.ForceTransitionDefinition(
        from_state=dsl_nodes.ALL,
        to_state=dsl_nodes.EXIT_STATE,
        event_id=event_id,
        condition_expr=condition_expr,
        event_scope=event_scope,
        source_raw=origin,
        _span=span,
    )
    if source_path is not None:
        # This node is synthesised to carry the declaration one level
        # deeper, and it keeps the declaration's span, so it has to keep
        # its file too.  Without this the descent stops having an answer
        # after the first level, and the span alone cannot supply one
        # across documents.
        setattr(carried, "_source_path", source_path)
    if forced_id is not None:
        setattr(carried, "_forced_id", forced_id)
        setattr(carried, "_exit_levels", exit_levels)
    return carried


@dataclass
class ForcedInheritance:
    """
    What the namespaces below one namespace inherit from its forced declarations.

    :meth:`ForcedExpansion.expand` returns one record per namespace. The model
    builder hands ``per_substate[i]`` to the ``i``-th child state and the result
    of :meth:`for_region` to each region, so a declaration travels down the
    state tree without the builder knowing how it is expanded.

    :param per_substate: For each child state declaration of the namespace, in
        declaration order, the declarations that continue below it.
    :type per_substate: List[List[pyfcstm.dsl.node.ForceTransitionDefinition]]
    :param resolved: The declarations that apply in the namespace, each with
        its resolved event, guard and bookkeeping.
    :type resolved: List[Tuple[Any, ...]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { [*] -> A; state A; state B; A -> B; }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> run = model.root_state.substates['Run']
        >>> sorted(t.from_state for t in run.transitions if t.is_forced)
        ['A', 'B']
    """

    per_substate: List[List[dsl_nodes.ForceTransitionDefinition]]
    resolved: List[Tuple[Any, ...]]

    def for_region(self) -> List[dsl_nodes.ForceTransitionDefinition]:
        """
        Build the declarations one region of the namespace inherits.

        Only an owner has regions, and an owner only keeps the declarations
        that reach regions, so every resolved declaration continues into each
        region, one owner deeper. Every call returns fresh nodes.

        :return: Declarations that apply to every state of the region.
        :rtype: List[pyfcstm.dsl.node.ForceTransitionDefinition]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     event Stop;
            ...     [*] -> Run;
            ...     state Run { region A { [*] -> A1; state A1; } }
            ...     state Idle;
            ...     !Run -> Idle : /Stop;
            ... }
            ... ''')
            >>> region = model.root_state.substates['Run'].regions['A']
            >>> [(t.from_state, t.exit_group_levels) for t in region.transitions if t.is_forced]
            [('A1', 1)]
        """
        carried: List[dsl_nodes.ForceTransitionDefinition] = []
        for (
            _,
            _,
            item_event_id,
            _,
            item_condition,
            _,
            item_scope,
            item_origin,
            item_span,
            item_source_path,
            _,
            _,
            item_id,
            item_levels,
            _,
        ) in self.resolved:
            carried.append(
                _forced_node(
                    item_event_id,
                    item_condition,
                    item_scope,
                    item_origin,
                    item_span,
                    item_source_path,
                    item_id,
                    item_levels + 1,
                )
            )
        return carried


class ForcedExpansion:
    """
    Resolve and expand the forced declarations of one machine build.

    A forced declaration ``!S -> T : /Stop;`` is syntactic sugar. The model
    builder walks the state tree once and calls :meth:`expand` for every state
    and region; the call resolves the declarations written there and the ones
    inherited from above, puts the expanded transitions on the child states,
    and says what continues further down. How a declaration is expanded is
    decided here and nowhere else:

    * A declaration whose states contain no state that owns regions keeps the
      plain expansion: every state below the source, pseudo states included,
      gets a ``-> [*]`` transition that repeats the event and the guard.
    * A declaration that reaches regions gets the expansion described in the
      module documentation, and the marks :func:`lower_forced` works from.
    * With ``plain`` set, or without ``lower``, every declaration keeps the
      plain expansion, which stops at owners. That machine is what exports,
      drawings and static analyses show.

    :param root_state: Root of the machine being built; event paths are
        resolved from it.
    :type root_state: pyfcstm.model.model.State
    :param defines: Variables of the machine; guards are checked against them.
    :type defines: Dict[str, pyfcstm.model.model.VarDefine]
    :param sink: Receiver of the diagnostics of faulty declarations.
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink
    :param lower: Whether the build lowers what it expands.
    :type lower: bool
    :param plain: Whether every declaration keeps the plain expansion even in
        a lowering build.
    :type plain: bool

    :ivar declarations: One summary per declaration, in the order they were
        resolved; it becomes :attr:`pyfcstm.model.model.StateMachine.forced_transitions`.
    :vartype declarations: List[Dict[str, object]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { [*] -> A; state A; pseudo state Gate; }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> [(item['from_path'], item['to_path'], item['event']) for item in model.forced_transitions]
        [('Root.Run', 'Root.Idle', 'Root.Stop')]
        >>> run = model.root_state.substates['Run']
        >>> sorted(t.from_state for t in run.transitions if t.is_forced)
        ['A', 'Gate']

    A declaration that names a state that does not exist is reported::

        >>> from pyfcstm.utils.validate import ModelValidationError
        >>> try:
        ...     load_state_machine_from_text(
        ...         'state Root { [*] -> A; state A; !Missing -> A; }')
        ... except ModelValidationError as err:
        ...     print(err.diagnostics[0].code, err.diagnostics[0].refs['reason'])
        E_FORCED_TRANSITION_EXPANSION src_not_found
    """

    def __init__(
        self,
        root_state: State,
        defines: Dict[str, VarDefine],
        sink: DiagnosticSink,
        lower: bool,
        plain: bool,
    ) -> None:
        self._root_state = root_state
        self._defines = defines
        self._sink = sink
        self._lowering = lower and not plain
        self._ids = count()
        self.declarations: List[Dict[str, object]] = []

    def expand(
        self,
        node: Union[dsl_nodes.StateDefinition, dsl_nodes.RegionDefinition],
        current_state: _Namespace,
        current_path: Tuple[str, ...],
        force_transitions: Optional[List[dsl_nodes.ForceTransitionDefinition]],
    ) -> ForcedInheritance:
        """
        Expand the forced declarations that apply in one namespace.

        The declarations inherited from above come first and the ones written
        in the namespace follow, each in its own order. Events named by a
        declaration are created where they belong, guards are checked, and the
        expanded transitions are appended to ``current_state.transitions`` in
        child declaration order. Nothing below the namespace is touched: the
        caller recurses with the returned record.

        :param node: Declaration of the namespace.
        :type node: Union[pyfcstm.dsl.node.StateDefinition, pyfcstm.dsl.node.RegionDefinition]
        :param current_state: The built state or region of ``node``.
        :type current_state: Union[pyfcstm.model.model.State, pyfcstm.model.region.Region]
        :param current_path: Path of the namespace from the root.
        :type current_path: Tuple[str, ...]
        :param force_transitions: Declarations inherited from the namespace
            above, or ``None`` at the root.
        :type force_transitions: Optional[List[pyfcstm.dsl.node.ForceTransitionDefinition]]
        :return: What the child states and regions inherit.
        :rtype: ForcedInheritance

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> A;
            ...     state A;
            ...     state B;
            ...     !* -> B :: Reset;
            ... }
            ... ''')
            >>> [(t.from_state, t.to_state, t.event.name) for t in model.root_state.transitions if t.is_forced]
            [('A', 'B', 'Reset'), ('B', 'B', 'Reset')]
        """
        sink = self._sink
        root_state = self._root_state
        d_defines = self._defines
        forced_transition_declarations = self.declarations
        forced_ids = self._ids
        force_transitions = list(force_transitions or [])
        if getattr(current_state, "regions", {}):
            # An owner has no substates to pass a declaration to. Only the
            # declarations that reach regions continue below it.
            force_transitions = [
                item
                for item in force_transitions
                if getattr(item, "_forced_id", None) is not None
            ]

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
            # A declaration that reaches regions is carried into every
            # namespace below it; what is wrong with its trigger was already
            # reported where it was written.
            report = (
                id(f_transnode) in local_force_ids
                or getattr(f_transnode, "_forced_id", None) is None
            )
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
                                "transition:\n"
                                f"{str(f_transnode.without_docs())}"
                            ),
                            span=getattr(f_transnode, "_span", None),
                            refs={
                                "original_raw": str(f_transnode.without_docs()),
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
                                "transition:\n"
                                f"{str(f_transnode.without_docs())}"
                            ),
                            span=getattr(f_transnode, "_span", None),
                            refs={
                                "original_raw": str(f_transnode.without_docs()),
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
                    if namespace_child(start_state, seg) is not None:
                        start_state = namespace_child(start_state, seg)
                    else:
                        if report:
                            sink.emit(
                                ModelDiagnostic(
                                    code="E_MISSING_STATE",
                                    severity="error",
                                    message=(
                                        f"Cannot find state "
                                        f"{'.'.join((*base_path, *my_event_id.path[:-1]))} "
                                        "for transition:\n"
                                        f"{str(f_transnode.without_docs())}"
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
                            # The event is synthesized from a transition
                            # trigger, so the source documentation belongs to
                            # the transition rather than this new owner.
                            doc=None,
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
                for unknown_var in unknown_vars if report else ():
                    sink.emit(
                        ModelDiagnostic(
                            code="E_UNDEFINED_VAR",
                            severity="error",
                            message=(
                                f"Unknown guard variable "
                                f"{unknown_var} in force "
                                "transition:\n"
                                f"{str(f_transnode.without_docs())}"
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
                        "original_raw": str(f_transnode.without_docs()),
                        "expansion_count": expansion_count,
                        "span": _node_span(f_transnode),
                    }
                )

            if id(f_transnode) in local_force_ids:
                # The declaration is shared with the other build of the same
                # program, so what is decided here stays in the tuple.
                forced_id = (
                    next(forced_ids)
                    if self._lowering
                    and _force_reaches_regions(node, from_state)
                    else None
                )
            else:
                forced_id = getattr(f_transnode, "_forced_id", None)

            force_transition_tuples_to_inherit.append(
                (
                    from_state,
                    to_state,
                    my_event_id,
                    trans_event,
                    condition_expr,
                    guard,
                    f_transnode.event_scope,
                    getattr(f_transnode, "source_raw", None)
                    or str(f_transnode.without_docs()),
                    _node_span(f_transnode),
                    # The file the declaration was written in, carried with its
                    # span.  An expansion lands on states from other files, and a
                    # span alone cannot say which document it belongs to -- two
                    # modules that put a statement of the same length at the same
                    # place share a key.  Asking the declaration directly is exact.
                    getattr(f_transnode, "_source_path", None),
                    getattr(f_transnode, "doc", None),
                    getattr(f_transnode, "target_history", None),
                    forced_id,
                    getattr(f_transnode, "_exit_levels", 0),
                    id(f_transnode) in local_force_ids,
                )
            )

        transitions = current_state.transitions
        per_substate: List[List[dsl_nodes.ForceTransitionDefinition]] = []
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
                forced_source_path,
                forced_doc,
                forced_target_history,
                forced_id,
                exit_levels,
                forced_local,
            ) in force_transition_tuples_to_inherit:
                if not (from_state is dsl_nodes.ALL or from_state == subnode.name):
                    continue
                substate = current_state.substates[subnode.name]
                if forced_id is not None and not forced_local and substate.is_pseudo:
                    # A pseudo state is never rested in, so there is nothing to
                    # take away from it; control only passes through.
                    continue

                carried = _forced_node(
                    my_event_id,
                    condition_expr,
                    event_scope,
                    forced_origin,
                    forced_span,
                    forced_source_path,
                    forced_id,
                    exit_levels,
                )
                if exit_levels and (substate.substates or substate.regions):
                    # Inside a region only a state that can be rested in holds
                    # the transition; a composite or owner passes it down.
                    _inner_force_transitions.append(carried)
                    continue
                transitions.append(
                    Transition(
                        from_state=subnode.name,
                        to_state=to_state,
                        event=trans_event,
                        guard=guard,
                        effects=[],
                        doc=forced_doc,
                        event_scope=event_scope,
                        is_forced=True,
                        forced_origin=forced_origin,
                        exit_group_levels=exit_levels,
                        _span=forced_span,
                        target_history=forced_target_history,
                    )
                )
                if forced_source_path is not None:
                    setattr(transitions[-1], "_source_path", forced_source_path)
                if forced_id is not None:
                    setattr(transitions[-1], "_forced_id", forced_id)
                    setattr(transitions[-1], "_forced_declared", forced_local)
                _inner_force_transitions.append(carried)

            per_substate.append(_inner_force_transitions)
        return ForcedInheritance(per_substate, force_transition_tuples_to_inherit)


def _flag_is(name: str, value: int) -> BinaryOp:
    """
    Build the condition ``name == value``.

    :param name: Hidden variable.
    :type name: str
    :param value: Value to compare with.
    :type value: int
    :return: The comparison.
    :rtype: pyfcstm.model.expr.BinaryOp
    """
    return BinaryOp(Variable(name), "==", Integer(value))


def _declarations(root_state: State) -> Dict[int, List[Tuple[_Namespace, Transition]]]:
    """
    Group the expanded transitions by the declaration they came from.

    :param root_state: Root of the machine.
    :type root_state: pyfcstm.model.model.State
    :return: Transitions with the namespace that holds them, per declaration,
        in the order the declarations were resolved.
    :rtype: Dict[int, List[Tuple[Union[State, Region], Transition]]]
    """
    groups: Dict[int, List[Tuple[_Namespace, Transition]]] = {}
    for namespace in walk_namespaces(root_state):
        for transition in namespace.transitions:
            forced_id = getattr(transition, _ID_MARK, None)
            if forced_id is not None:
                groups.setdefault(forced_id, []).append((namespace, transition))
    return dict(sorted(groups.items()))


def _assigned_names(root_state: State) -> Iterator[str]:
    """
    Yield the target of every assignment a machine executes.

    Assignments come from the actions of every state and region and from the
    effects of every transition; the statements of conditional branches are
    included. A name that no variable declares is a temporary of its block.

    :param root_state: Root of the machine.
    :type root_state: pyfcstm.model.model.State
    :return: Assignment targets, possibly repeated.
    :rtype: Iterator[str]
    """

    def targets(statements: Iterable[OperationStatement]) -> Iterator[str]:
        for statement in statements:
            if isinstance(statement, Operation):
                yield statement.var_name
            else:
                for branch in statement.branches:
                    yield from targets(branch.statements)

    for namespace in walk_namespaces(root_state):
        for action in namespace_actions(namespace):
            yield from targets(action.operations)
        for transition in namespace.transitions:
            yield from targets(transition.effects)


def _free_name(taken: Set[str], forced_id: int) -> str:
    """
    Pick the hidden variable of a declaration.

    :param taken: Names the machine already uses: its variables and the targets
        of its assignments, which include the temporaries of action blocks.
    :type taken: Set[str]
    :param forced_id: Number of the declaration.
    :type forced_id: int
    :return: ``__forced_<n>`` for the smallest ``n >= forced_id`` that no used
        name can be mistaken for. Identifier conversion of the target languages
        collapses runs of underscores, so ``_forced_<n>`` counts as taken too.
    :rtype: str
    """
    number = forced_id
    while any(re.fullmatch("_+forced_%d" % number, name) for name in taken):
        number += 1
    return "__forced_%d" % number


def lower_forced(
    root_state: State, defines: Dict[str, VarDefine]
) -> Tuple[str, ...]:
    """
    Make every forced declaration that reaches regions decide once.

    Declarations that did not reach regions carry no mark and are left alone.
    For each marked declaration this installs the hidden variable in
    ``defines``, rewrites the expanded transitions as described in the module
    documentation, and keeps the declared transition on its own level.

    :param root_state: Root of the machine; its transitions are rewritten in
        place.
    :type root_state: pyfcstm.model.model.State
    :param defines: Variable definitions of the machine; the hidden variables
        are added.
    :type defines: Dict[str, pyfcstm.model.base.VarDefine]
    :return: Names of the hidden variables that were installed, in the order of
        the declarations; empty when no declaration reaches regions.
    :rtype: Tuple[str, ...]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run {
        ...         region A { [*] -> A1; state A1; }
        ...     }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> a1 = model.root_state.substates['Run'].regions['A'].transitions
        >>> [str(op.expr) for t in a1 if t.exit_group_levels for op in t.effects]
        ['1']
    """
    declarations = _declarations(root_state)
    # A temporary of an action block would otherwise become a write to the
    # hidden variable once that variable is installed under the same name.
    taken = set(defines).union(_assigned_names(root_state)) if declarations else set()
    names: List[str] = []
    for forced_id, items in declarations.items():
        name = _free_name(taken, forced_id)
        taken.add(name)
        raised, lowered = _flag_is(name, 1), _flag_is(name, 0)
        relays: List[Tuple[_Namespace, State]] = []
        for namespace, transition in items:
            source = namespace.substates[transition.from_state]
            declared = getattr(transition, _DECLARED_MARK, False)
            if source.substates or source.regions:
                if declared:
                    # The declared transition keeps its own event and guard for
                    # the case that control comes back without the variable
                    # raised; the copy in front of it takes the raised case.
                    relay = replace(
                        transition,
                        event=None,
                        guard=raised,
                        effects=[
                            Operation(var_name=name, expr=Integer(0)),
                            *transition.effects,
                        ],
                    )
                    setattr(relay, _ID_MARK, forced_id)
                    namespace.transitions.insert(
                        namespace.transitions.index(transition), relay
                    )
                else:
                    transition.event = None
                    transition.guard = raised
                relays.append((namespace, source))
            elif not declared:
                transition.effects = [
                    Operation(var_name=name, expr=Integer(1)),
                    *transition.effects,
                ]
        for namespace, source in relays:
            for other in namespace.transitions:
                carries = getattr(other, _ID_MARK, None) == forced_id and not getattr(
                    other, _DECLARED_MARK, False
                )
                # Everything but the relay of this declaration gives way, the
                # declared transition included: taken with the variable raised
                # it would enter its target with relays armed inside it.
                if other.from_state == source.name and not carries:
                    _and_condition(other, lowered)
        # A declaration only carries a number when it acts on a state that
        # owns regions, and the source on its own level is then a composite or
        # an owner, so the variable is always needed.
        defines[name] = VarDefine(name=name, type="int", init=Integer(0))
        names.append(name)
    return tuple(names)


def _and_condition(transition: Transition, condition: BinaryOp) -> None:
    """
    Add a condition to a transition, whatever trigger it has.

    :class:`~pyfcstm.model.model.Transition` refuses an event and a guard
    together because the language has no way to write them; lowering needs the
    pair, so the guard is written to the field directly.

    :param transition: Transition to restrict.
    :type transition: pyfcstm.model.model.Transition
    :param condition: Condition that must hold as well.
    :type condition: pyfcstm.model.expr.BinaryOp
    :return: ``None``.
    :rtype: None
    """
    guard = (
        condition
        if transition.guard is None
        else BinaryOp(transition.guard, "&&", condition)
    )
    object.__setattr__(transition, "guard", guard)
