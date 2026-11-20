"""
Forced transitions, expanded so that each one is decided once.

A forced transition ``!S -> T : /Stop;`` is syntactic sugar: model conversion
expands it into ordinary transitions, so the simulator, templates and BMC never
see a forced construct. Taking ``S`` away means leaving the state the machine
rests in below ``S``, every composite state on the way up and, where ``S``
contains a state that owns regions, the whole group of every such owner. The
event and the guard of the declaration are decided **once**, at the place where
the machine rests, and nothing on the way up asks again. An exit action that
changes what the guard reads, or a guard that asks whether a state inside ``S``
is active, therefore cannot turn the transition away half-way, and a forced
transition that cannot be carried out to the end takes nothing at all. The
expansion works in two steps.

Expansion (:class:`ForcedExpansion`, done while forced transitions are
resolved):

* On the level of the declaration the transition ``S -> T`` is the declared one.
* Every state below ``S`` that is outside a region gets a ``-> [*]`` transition
  that repeats the declared event and guard.
* Every state inside a region of an owner below ``S`` that can be rested in
  gets an *exit-group* transition
  (:attr:`pyfcstm.model.model.Transition.exit_group_levels`): when it is taken
  the whole group of the outermost owner below ``S`` leaves, regions in reverse
  declaration order and deepest state first, and control returns to that owner.
* Pseudo states get none: they are never rested in, so a forced transition is
  not taken while an entry only passes through one.

Lowering (:meth:`ForcedExpansion.lower`): one hidden ``int`` variable
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
   on the way gives way, the declared transition included: each of them has to
   wait until the variable is lowered. A forced transition whose target cannot
   be entered therefore takes nothing, whatever else leaves the same state.

A declaration whose sources have nothing inside them needs none of this: its
declared transitions are all there is, and it gets no variable.

Rule 4 never puts an event and a guard on one transition, which neither the
language nor the model allows. A transition without an event gets the condition
added to its guard. A transition with an event is split through a pseudo state
named ``__forced_gate_<n>``
(:attr:`pyfcstm.model.model.State.is_forced_gate`), the way history lowering
gates an evented initial transition: the event leads to the gate, and a second
transition leads on to the target under the condition, carrying the effects.
While the variable is raised the gate is a dead end and the first step is
rejected; otherwise the two steps behave like the transition as written, and a
trace shows the gate as one more state passed through. All of this is done
only after every declaration has its relays, so two declarations on one state
restrict each other in the same way.

The variable is raised and lowered inside one cycle, so it is ``0`` whenever
the machine rests (see :attr:`pyfcstm.model.model.StateMachine.forced_variables`).

The *plain expansion* is the older reading of the same declaration: a ``-> [*]``
transition on every state below ``S``, pseudo states included, that repeats the
event and the guard on every level and stops at owners. No machine runs it any
more, but it is the form a declaration is shown in. The PlantUML export, the
diagram snapshot and the static analyses
(:func:`pyfcstm.diagnostics.inspect.inspect_model`,
:func:`pyfcstm.verify.inspect_adapter.run_inspect_algorithms`,
:func:`pyfcstm.verify.algorithms.transition.transition_shadowed_by_predecessor`
and the topology analyses of :mod:`pyfcstm.verify.topology`) use a machine
built with it, so a drawing shows one transition per state the declaration
applies to and no hidden variable. The DSL export writes the machine that runs,
hidden variables and gates included, as it does for a lowered history; only a
machine with exit-group transitions, the one thing the language cannot write,
is exported in its plain expansion (see
:meth:`pyfcstm.model.model.StateMachine.to_ast_node`).

The module contains:

* :class:`ForcedExpansion` - Resolve the declarations, expand them and lower
  what was expanded into hidden variables, relays and gates
* :class:`ForcedInheritance` - What one namespace hands down to the next

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
    >>> [(t.from_state, t.to_state, t.event is not None, str(t.guard))
    ...  for t in model.root_state.transitions if isinstance(t.from_state, str)]
    [('Run', 'Idle', False, '__forced_0 == 1'), ('Run', '__forced_gate_0', True, 'None'), ('__forced_gate_0', 'Idle', False, '__forced_0 == 0')]

A composite state without regions is lowered the same way, with a plain
``-> [*]`` transition where the machine rests. The exit action of ``A`` changes
what the guard reads, and the transition is taken all the same; the declaration
on ``Idle``, a state with nothing inside it, stays one transition and gets no
variable::

    >>> from pyfcstm.simulate import SimulationRuntime
    >>> model = load_state_machine_from_text('''
    ... def int armed = 1;
    ... state Root {
    ...     [*] -> Run;
    ...     state Run { [*] -> A; state A { exit { armed = 0; } } }
    ...     state Idle;
    ...     !Run -> Idle : if [armed == 1];
    ...     !Idle -> Run : if [armed == 2];
    ... }
    ... ''')
    >>> model.forced_variables
    ('__forced_0',)
    >>> [(t.from_state, t.to_state, str(t.guard))
    ...  for t in model.root_state.substates['Run'].transitions if t.is_forced]
    [('A', EXIT_STATE, 'armed == 1')]
    >>> [(t.from_state, t.to_state, str(t.guard), t.is_forced)
    ...  for t in model.root_state.transitions if isinstance(t.from_state, str)]
    [('Run', 'Idle', '__forced_0 == 1', False), ('Run', 'Idle', 'armed == 1 && __forced_0 == 0', True), ('Idle', 'Run', 'armed == 2', True)]
    >>> runtime = SimulationRuntime(model)
    >>> runtime.cycle().delta, runtime.current_state.path
    (False, ('Root', 'Run', 'A'))
    >>> runtime.cycle().delta, runtime.current_state.path, runtime.vars['armed']
    (False, ('Root', 'Idle'), 0)
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

__all__ = ["ForcedExpansion", "ForcedInheritance"]

_Namespace = Union[State, Region]

# Gates are named ``__forced_gate_<n>`` inside the namespace that needs them.
_GATE_PREFIX = "__forced_gate_"


@dataclass
class _Carried:
    """
    A forced declaration on its way down the state tree.

    :param node: The declaration as it applies to every state of the next
        level: its source is ``*`` and its target the exit of that level.
    :type node: pyfcstm.dsl.node.ForceTransitionDefinition
    :param forced_id: Number of the declaration, or ``None`` in a build that
        keeps the plain expansion.
    :type forced_id: Optional[int]
    :param exit_levels: Number of owners crossed since the declaring level.
    :type exit_levels: int
    """

    node: dsl_nodes.ForceTransitionDefinition
    forced_id: Optional[int]
    exit_levels: int


@dataclass
class _Resolved:
    """
    A forced declaration as it applies in one namespace.

    :param from_state: Source, a child state name or ``*``.
    :type from_state: Union[str, pyfcstm.dsl.node._StateSingletonMark]
    :param to_state: Target, a child state name or the exit of the namespace.
    :type to_state: Union[str, pyfcstm.dsl.node._StateSingletonMark]
    :param event_id: Absolute path of the event, if the declaration has one.
    :type event_id: Optional[pyfcstm.dsl.node.ChainID]
    :param event: The resolved event, or ``None`` without one or when its path
        could not be resolved.
    :type event: Optional[pyfcstm.model.model.Event]
    :param condition_expr: Guard as written, if any.
    :type condition_expr: Optional[pyfcstm.dsl.node.Expr]
    :param guard: The guard as a model expression, if any.
    :type guard: Optional[pyfcstm.model.expr.Expr]
    :param event_scope: Scope the event was written with.
    :type event_scope: Optional[str]
    :param origin: Text of the declaration as written.
    :type origin: str
    :param span: Source span of the declaration.
    :type span: Optional[pyfcstm.utils.validate.Span]
    :param source_path: File the declaration was written in. An expansion
        lands on states from other files, and a span alone cannot say which
        document it belongs to.
    :type source_path: Optional[str]
    :param doc: Documentation attached to the declaration.
    :type doc: Optional[str]
    :param target_history: History the declaration enters its target through.
    :type target_history: Optional[str]
    :param forced_id: Number of the declaration, or ``None`` in a build that
        keeps the plain expansion.
    :type forced_id: Optional[int]
    :param exit_levels: Number of owners crossed since the declaring level.
    :type exit_levels: int
    :param local: Whether the declaration is written in this namespace rather
        than carried into it.
    :type local: bool
    """

    from_state: Any
    to_state: Any
    event_id: Any
    event: Optional[Event]
    condition_expr: Any
    guard: Any
    event_scope: Optional[str]
    origin: str
    span: Any
    source_path: Optional[str]
    doc: Optional[str]
    target_history: Optional[str]
    forced_id: Optional[int]
    exit_levels: int
    local: bool

    def carried(self, exit_levels: int) -> _Carried:
        """
        Build the record that takes the declaration one level deeper.

        :param exit_levels: Number of owners crossed once the next level is
            reached.
        :type exit_levels: int
        :return: The declaration as it applies to every state of that level.
        :rtype: _Carried
        """
        node = dsl_nodes.ForceTransitionDefinition(
            from_state=dsl_nodes.ALL,
            to_state=dsl_nodes.EXIT_STATE,
            event_id=self.event_id,
            condition_expr=self.condition_expr,
            event_scope=self.event_scope,
            source_raw=self.origin,
            _span=self.span,
        )
        if self.source_path is not None:
            # This node is synthesised to carry the declaration one level
            # deeper, and it keeps the declaration's span, so it has to keep
            # its file too.  Without this the descent stops having an answer
            # after the first level, and the span alone cannot supply one
            # across documents.
            setattr(node, "_source_path", self.source_path)
        return _Carried(node, self.forced_id, exit_levels)


@dataclass
class _Expanded:
    """
    One transition the expansion put on a state for a numbered declaration.

    :param namespace: State or region that holds the transition.
    :type namespace: Union[pyfcstm.model.model.State, pyfcstm.model.region.Region]
    :param transition: The transition.
    :type transition: pyfcstm.model.model.Transition
    :param declared: Whether it is the transition written on the declaring
        level rather than one of the transitions below the source.
    :type declared: bool
    """

    namespace: _Namespace
    transition: Transition
    declared: bool


@dataclass
class ForcedInheritance:
    """
    What the namespaces below one namespace inherit from its forced declarations.

    :meth:`ForcedExpansion.expand` returns one record per namespace. The model
    builder hands ``per_substate[i]`` to the ``i``-th child state and the result
    of :meth:`for_region` to each region, so a declaration travels down the
    state tree without the builder knowing how it is expanded.

    The records inside are read back only by :meth:`ForcedExpansion.expand`;
    the builder passes them on as they are.

    :param per_substate: For each child state declaration of the namespace, in
        declaration order, the declarations that continue below it.
    :type per_substate: List[List[_Carried]]
    :param resolved: The declarations that apply in the namespace, each with
        its resolved event, guard and bookkeeping.
    :type resolved: List[_Resolved]

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

    per_substate: List[List[_Carried]]
    resolved: List[_Resolved]

    def for_region(self) -> List[_Carried]:
        """
        Build the declarations one region of the namespace inherits.

        Only an owner has regions, and an owner only keeps numbered
        declarations, so every resolved declaration continues into each
        region, one owner deeper. Every call returns fresh records.

        :return: Declarations that apply to every state of the region.
        :rtype: List[_Carried]

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
        return [item.carried(item.exit_levels + 1) for item in self.resolved]


class ForcedExpansion:
    """
    Resolve and expand the forced declarations of one machine build.

    A forced declaration ``!S -> T : /Stop;`` is syntactic sugar. The model
    builder walks the state tree once and calls :meth:`expand` for every state
    and region; the call resolves the declarations written there and the ones
    inherited from above, puts the expanded transitions on the child states,
    and says what continues further down. How a declaration is expanded is
    decided here and nowhere else:

    * In a build that lowers, every declaration gets the expansion described
      in the module documentation, and a record of the transitions it was
      given, which :meth:`lower` works from: pseudo states below the source
      get no transition, and the declaration continues into the regions of an
      owner.
    * With ``plain`` set, or without ``lower``, every declaration keeps the
      plain expansion instead: every state below the source, pseudo states
      included, gets a ``-> [*]`` transition that repeats the event and the
      guard, and an owner stops the descent. That machine is what drawings
      and static analyses show.

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
    :ivar takes_groups_away: Whether any expanded transition takes a whole
        group of regions away
        (:attr:`pyfcstm.model.model.Transition.exit_group_levels`). The
        language cannot write such a transition, so a machine that has one is
        exported in its plain expansion.
    :vartype takes_groups_away: bool

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
        ['A']

    A drawing of the same model shows the plain expansion, pseudo state
    included::

        >>> [line.strip() for line in model.to_plantuml().splitlines() if 'Stop' in line]
        ['root__run__a --> [*] : /Stop', 'root__run__gate --> [*] : /Stop', 'root__run --> root__idle : Stop']

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
        """
        Start an expansion with no declaration resolved yet.

        :param root_state: Root of the machine being built.
        :type root_state: pyfcstm.model.model.State
        :param defines: Variables of the machine.
        :type defines: Dict[str, pyfcstm.model.model.VarDefine]
        :param sink: Receiver of the diagnostics of faulty declarations.
        :type sink: pyfcstm.diagnostics.sink.DiagnosticSink
        :param lower: Whether the build lowers what it expands.
        :type lower: bool
        :param plain: Whether every declaration keeps the plain expansion
            even in a lowering build.
        :type plain: bool
        :return: ``None``.
        :rtype: None
        """
        self._root_state = root_state
        self._defines = defines
        self._sink = sink
        self._lowering = lower and not plain
        self._ids = count()
        # What each numbered declaration was expanded into, for :meth:`lower`.
        self._expanded: Dict[int, List[_Expanded]] = {}
        self.declarations: List[Dict[str, object]] = []
        self.takes_groups_away = False

    def expand(
        self,
        node: Union[dsl_nodes.StateDefinition, dsl_nodes.RegionDefinition],
        current_state: _Namespace,
        current_path: Tuple[str, ...],
        force_transitions: Optional[List[_Carried]],
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
            above, as an earlier call returned them, or ``None`` at the root.
        :type force_transitions: Optional[List[_Carried]]
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
        inherited = list(force_transitions or [])
        if getattr(current_state, "regions", {}):
            # An owner has no substates to pass a declaration to. Numbered
            # declarations continue into its regions; the plain expansion,
            # whose declarations carry no number, stops here.
            inherited = [item for item in inherited if item.forced_id is not None]

        resolved: List[_Resolved] = []
        work = [(item.node, item.forced_id, item.exit_levels, False) for item in inherited]
        work.extend((item, None, 0, True) for item in node.force_transitions)
        for f_transnode, carried_id, carried_levels, local in work:
            # If either side of a forced transition is unresolved, skip the
            # rest of its processing and do not record it. Otherwise collect
            # mode keeps a record with a bad source or target that quietly
            # corrupts what the child states inherit (a bad target being
            # attached to the transitions of a real substate).
            unresolved = False
            # A numbered declaration is carried into every namespace below
            # it; what is wrong with its trigger was already reported where it
            # was written.
            report = local or carried_id is None
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
                # on.
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

            if local:
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

            # The declaration node is shared with the other build of the same
            # program, so what is decided here stays in the record.
            resolved.append(
                _Resolved(
                    from_state=from_state,
                    to_state=to_state,
                    event_id=my_event_id,
                    event=trans_event,
                    condition_expr=condition_expr,
                    guard=guard,
                    event_scope=f_transnode.event_scope,
                    origin=getattr(f_transnode, "source_raw", None)
                    or str(f_transnode.without_docs()),
                    span=_node_span(f_transnode),
                    source_path=getattr(f_transnode, "_source_path", None),
                    doc=getattr(f_transnode, "doc", None),
                    target_history=getattr(f_transnode, "target_history", None),
                    forced_id=(
                        (next(forced_ids) if self._lowering else None)
                        if local
                        else carried_id
                    ),
                    exit_levels=carried_levels,
                    local=local,
                )
            )

        transitions = current_state.transitions
        per_substate: List[List[_Carried]] = []
        for subnode in node.substates:
            below: List[_Carried] = []
            for item in resolved:
                if not (
                    item.from_state is dsl_nodes.ALL
                    or item.from_state == subnode.name
                ):
                    continue
                substate = current_state.substates[subnode.name]
                if item.forced_id is not None and not item.local and substate.is_pseudo:
                    # A pseudo state is never rested in, so there is nothing to
                    # take away from it; control only passes through.
                    continue

                carried = item.carried(item.exit_levels)
                if item.exit_levels and (substate.substates or substate.regions):
                    # Inside a region only a state that can be rested in holds
                    # the transition; a composite or owner passes it down.
                    below.append(carried)
                    continue
                transition = Transition(
                    from_state=subnode.name,
                    to_state=item.to_state,
                    event=item.event,
                    guard=item.guard,
                    effects=[],
                    doc=item.doc,
                    event_scope=item.event_scope,
                    is_forced=True,
                    forced_origin=item.origin,
                    exit_group_levels=item.exit_levels,
                    _span=item.span,
                    target_history=item.target_history,
                )
                transitions.append(transition)
                if item.exit_levels:
                    self.takes_groups_away = True
                if item.source_path is not None:
                    setattr(transition, "_source_path", item.source_path)
                if item.forced_id is not None:
                    self._expanded.setdefault(item.forced_id, []).append(
                        _Expanded(current_state, transition, item.local)
                    )
                below.append(carried)

            per_substate.append(below)
        return ForcedInheritance(per_substate, resolved)

    def lower(self, defines: Dict[str, VarDefine]) -> Tuple[str, ...]:
        """
        Make every forced declaration that was expanded decide once.

        Call this after every namespace was passed to :meth:`expand` and after
        the other lowerings of the build. For each declaration whose source has
        states or regions inside it this installs the hidden variable in
        ``defines``, rewrites the expanded transitions as described in the
        module documentation, and keeps the declared transition on its own
        level. A declaration whose sources have nothing inside them is left as
        its declared transitions. A build that keeps the plain expansion
        recorded nothing and is left alone.

        The transitions that only pass the exit on, on the composite states
        and owners below the source and in front of the declared transition,
        are generated plumbing: they are no longer marked
        :attr:`pyfcstm.model.model.Transition.is_forced`, and keep
        ``forced_origin`` to say which declaration they belong to. The
        transitions that repeat the declared event and guard, and the declared
        one, stay marked.

        :param defines: Variable definitions of the machine; the hidden
            variables are added.
        :type defines: Dict[str, pyfcstm.model.model.VarDefine]
        :return: Names of the hidden variables that were installed, in the
            order of the declarations they belong to and numbered in that
            order; empty when no declaration needs one.
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
            >>> [(t.to_state, str(t.guard), t.is_forced)
            ...  for t in model.root_state.transitions if t.from_state == 'Run'][0]
            ('Idle', '__forced_0 == 1', False)
        """
        root_state = self._root_state
        # A temporary of an action block would otherwise become a write to the
        # hidden variable once that variable is installed under the same name.
        taken = (
            set(defines).union(_assigned_names(root_state)) if self._expanded else set()
        )
        names: List[str] = []
        waiting: List[Tuple[BinaryOp, List[Tuple[_Namespace, State]], Set[int]]] = []
        # Every declaration first gets its variable, its initiators and its
        # relays. Only then do the other transitions give way, so that a relay
        # of one declaration has already lost its event when another
        # declaration restricts it, and the conditions two declarations put on
        # each other are the same.
        for _, items in sorted(self._expanded.items()):
            if not any(
                item.namespace.substates[item.transition.from_state].substates
                or item.namespace.substates[item.transition.from_state].regions
                for item in items
            ):
                # Every source is a state without anything inside: the declared
                # transitions are all there is, and they already decide once.
                continue
            name = _free_name(taken, len(names))
            taken.add(name)
            raised, lowered = _flag_is(name, 1), _flag_is(name, 0)
            relays: List[Tuple[_Namespace, State]] = []
            # The transitions that carry this declaration on; they do not give
            # way to it.
            carrying: Set[int] = {id(item.transition) for item in items if not item.declared}
            for item in items:
                namespace, transition = item.namespace, item.transition
                source = namespace.substates[transition.from_state]
                if source.substates or source.regions:
                    if item.declared:
                        # The declared transition keeps its own event and guard
                        # for the case that control comes back without the
                        # variable raised; the copy in front of it takes the
                        # raised case.
                        relay = replace(
                            transition,
                            event=None,
                            guard=raised,
                            effects=[
                                Operation(var_name=name, expr=Integer(0)),
                                *transition.effects,
                            ],
                            is_forced=False,
                        )
                        carrying.add(id(relay))
                        namespace.transitions.insert(
                            namespace.transitions.index(transition), relay
                        )
                    else:
                        transition.event = None
                        transition.guard = raised
                        transition.is_forced = False
                    relays.append((namespace, source))
                elif not item.declared:
                    transition.effects = [
                        Operation(var_name=name, expr=Integer(1)),
                        *transition.effects,
                    ]
            defines[name] = VarDefine(name=name, type="int", init=Integer(0))
            names.append(name)
            waiting.append((lowered, relays, carrying))
        gates: Dict[int, Transition] = {}
        for lowered, relays, carrying in waiting:
            for namespace, source in relays:
                for other in list(namespace.transitions):
                    # Everything but the relays of this declaration gives way,
                    # the declared transition included: taken with the variable
                    # raised it would enter its target with relays armed inside
                    # it.
                    if other.from_state == source.name and id(other) not in carrying:
                        _give_way(namespace, other, lowered, gates)
        return tuple(names)


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


def _free_name(taken: Set[str], first: int) -> str:
    """
    Pick the hidden variable of a declaration.

    :param taken: Names the machine already uses: its variables and the targets
        of its assignments, which include the temporaries of action blocks.
    :type taken: Set[str]
    :param first: Smallest number to try, the count of variables handed out so
        far.
    :type first: int
    :return: ``__forced_<n>`` for the smallest ``n >= first`` whose name is
        free. Identifier conversion of the target languages collapses runs of
        leading underscores, so a used ``_forced_<n>`` with any number of
        leading underscores counts as taken too.
    :rtype: str
    """
    number = first
    while any(re.fullmatch("_+forced_%d" % number, name) for name in taken):
        number += 1
    return "__forced_%d" % number


def _give_way(
    namespace: _Namespace,
    transition: Transition,
    condition: BinaryOp,
    gates: Dict[int, Transition],
) -> None:
    """
    Make a transition wait until a hidden variable is lowered.

    A transition without an event gets the condition added to its guard. A
    transition with an event cannot: the model, like the language, lets a
    transition have an event or a guard and never both. It is split through a
    pseudo state instead, the way history lowering gates an evented initial
    transition: the transition keeps its event and now ends in a *gate*, and a
    second transition leads from the gate to the original target, guarded by
    the condition and carrying the effects. While the variable is raised the
    gate is a dead end, so validation rejects the first step; while it is
    lowered the two steps behave like the transition as written.

    :param namespace: State or region that holds ``transition``.
    :type namespace: Union[pyfcstm.model.model.State, pyfcstm.model.region.Region]
    :param transition: Transition to restrict.
    :type transition: pyfcstm.model.model.Transition
    :param condition: Condition that must hold as well.
    :type condition: pyfcstm.model.expr.BinaryOp
    :param gates: The second step of every transition split so far, keyed by
        the identity of the first step; a transition that gives way to several
        declarations keeps one gate and collects their conditions on it.
    :type gates: Dict[int, pyfcstm.model.model.Transition]
    :return: ``None``.
    :rtype: None
    """
    if transition.event is None:
        transition.guard = (
            condition
            if transition.guard is None
            else BinaryOp(transition.guard, "&&", condition)
        )
        return
    through = gates.get(id(transition))
    if through is not None:
        through.guard = BinaryOp(through.guard, "&&", condition)
        return
    number = 0
    while "%s%d" % (_GATE_PREFIX, number) in namespace.substates:
        number += 1
    gate_name = "%s%d" % (_GATE_PREFIX, number)
    gate = State(
        name=gate_name,
        path=(*namespace.path, gate_name),
        substates={},
        is_pseudo=True,
        is_forced_gate=True,
    )
    gate.parent = namespace
    namespace.substates[gate_name] = gate
    namespace.substate_name_to_id[gate_name] = len(namespace.substate_name_to_id)
    through = Transition(
        from_state=gate_name,
        to_state=transition.to_state,
        event=None,
        guard=condition,
        effects=list(transition.effects),
        _span=transition._span,
    )
    through.parent = namespace
    transition.to_state = gate_name
    transition.effects = []
    namespace.transitions.append(through)
    gates[id(transition)] = through
