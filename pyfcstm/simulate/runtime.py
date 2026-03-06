"""
Simulation runtime execution semantics for finite state machine models.

This module implements the runtime that executes :class:`pyfcstm.model.StateMachine`
instances produced from the pyfcstm DSL. The implementation is intentionally
stateful: it tracks the active state stack, current variable values, and a small
set of internal frame modes that control how entry, during, exit, initial
transitions, and exit-to-parent flows are advanced.

The module contains the following main components:

* :class:`_Frame` - Internal stack frame describing an active state and its phase.
* :class:`SimulationRuntime` - Runtime environment for cycling a
  hierarchical state machine.

.. note::
   The descriptions in this module document the current behavior implemented in
   :mod:`pyfcstm.simulate.runtime`. They are aligned with the reviewed examples
   in :mod:`SIMULATE_DESIGN.md`, including the corrected behavior around the
   4.25 and 4.26 examples.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state Root {
    ...     state A {
    ...         during {
    ...             counter = counter + 1;
    ...         }
    ...     }
    ...     state B {
    ...         during {
    ...             counter = counter + 10;
    ...         }
    ...     }
    ...     [*] -> A;
    ...     A -> B :: Go;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.current_state.path
    ('Root', 'A')
    >>> runtime.cycle(['Root.A.Go'])
    >>> runtime.current_state.path
    ('Root', 'B')
"""


import copy
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from ..dsl import EXIT_STATE
from ..model import Event, OnAspect, OnStage, State, StateMachine, Transition
from .utils import get_event_name, get_func_name


@dataclass
class _Frame:
    """
    Internal runtime frame for an active state.

    Frames are stored in :attr:`SimulationRuntime.stack` from root to the current
    active state. The ``mode`` field is used by the runtime to distinguish
    whether a frame has just entered a leaf state (``'after_entry'``), is waiting
    for a composite state's initial transition (``'init_wait'``), is ready for
    ordinary execution (``'active'``), or is resuming control after a child
    exited via ``[*]`` (``'post_child_exit'``).

    :param state: The active state represented by this frame.
    :type state: State
    :param mode: Internal execution phase associated with ``state``.
    :type mode: str
    """

    state: State
    mode: str


class SimulationRuntime:
    """
    Runtime environment for simulating hierarchical state machine execution.

    The runtime owns three pieces of mutable execution state: the active frame
    stack, the current variable mapping, and two lifecycle flags tracking
    whether initialization has already happened and whether the machine has
    ended. Public callers interact with :meth:`cycle` to advance execution
    until it reaches a stable boundary.

    In the current implementation, transition selection is always driven by the
    stack-top state's :attr:`pyfcstm.model.State.transitions_from`. This detail
    is important for understanding why the reviewed 4.25 example in
    :mod:`SIMULATE_DESIGN.md` remains in ``System1.A`` when only the parent-level
    ``System1 -> System2`` transition is offered directly, while 4.26 can advance
    because the leaf state first exits through ``A -> [*]`` and only then allows
    parent-level continuation.

    :param state_machine: The state machine model to simulate.
    :type state_machine: StateMachine

    :ivar state_machine: The state machine being simulated.
    :vartype state_machine: StateMachine
    :ivar stack: Active frames ordered from root to the current execution point.
    :vartype stack: List[_Frame]
    :ivar vars: Mutable variable values visible to guards, effects, and actions.
    :vartype vars: Dict[str, Union[int, float]]
    :ivar _initialized: Whether the runtime has already performed root entry.
    :vartype _initialized: bool
    :ivar _ended: Whether execution has terminated and the active stack is empty.
    :vartype _ended: bool

    Example::

        >>> runtime = SimulationRuntime(sm)
        >>> runtime.cycle()
        >>> runtime.brief_stack
        [(('Root',), 'init_wait'), (('Root', 'A'), 'after_entry')]
    """

    def __init__(self, state_machine: StateMachine):
        """
        Initialize the simulation runtime with a concrete state machine model.

        Variable storage is prepared eagerly from ``state_machine.defines`` in
        declaration order so later initializers can depend on variables defined
        earlier. The runtime itself is still considered uninitialized until the
        first call to :meth:`cycle`, at which point root entry is
        performed by :meth:`_initialize_runtime`.

        :param state_machine: The state machine model to simulate.
        :type state_machine: StateMachine
        :return: ``None``.
        :rtype: None
        """
        self.state_machine = state_machine
        self.stack: List[_Frame] = []
        self.vars: Dict[str, Union[int, float]] = {}
        for name, define in self.state_machine.defines.items():
            self.vars[name] = define.init(**self.vars)

        self._initialized = False
        self._ended = False

    def parse_event(self, event: Union[str, Event]) -> Event:
        """
        Resolve an event reference into a concrete :class:`pyfcstm.model.Event`.

        String inputs are interpreted as dot-separated paths. If the first path
        segment equals the root state's name it is treated as an explicit root
        prefix and skipped during descent. The final segment is then resolved
        from the event table of the enclosing state reached by the preceding
        segments.

        :param event: Event object or dot-separated event path.
        :type event: Union[str, Event]
        :return: The resolved event instance.
        :rtype: Event
        :raises TypeError: If ``event`` is neither a string nor an :class:`Event`.
        """
        if isinstance(event, Event):
            return event
        elif isinstance(event, str):
            segments = event.split('.')
            state = self.state_machine.root_state
            start_idx = 1 if segments[0] == state.name else 0
            for segment in segments[start_idx:-1]:
                state = state.substates[segment]
            return state.events[segments[-1]]
        else:
            raise TypeError(f'Unknown event type {type(event)!r} - {event!r}.')

    @staticmethod
    def _clone_stack(stack: List[_Frame]) -> List[_Frame]:
        """
        Clone a runtime frame stack without duplicating model objects.

        The validation logic needs an isolated stack snapshot while still
        referring to the same immutable :class:`State` objects. This helper
        therefore creates new :class:`_Frame` instances that preserve each
        frame's ``state`` and ``mode``.

        :param stack: Source stack to clone.
        :type stack: List[_Frame]
        :return: A shallow structural copy of the frame stack.
        :rtype: List[_Frame]
        """
        return [_Frame(frame.state, frame.mode) for frame in stack]

    def _normalize_events(self, events: Optional[List[Union[str, Event]]]) -> Tuple[List[Event], Dict[str, Event]]:
        """
        Normalize user-provided events into object and lookup forms.

        The runtime accepts both event objects and string paths. This helper
        resolves them into concrete :class:`Event` instances and also builds a
        dictionary keyed by :func:`pyfcstm.simulate.get_event_name` so transition
        matching can perform constant-time membership checks.

        :param events: Raw event inputs for the current execution attempt.
        :type events: Optional[List[Union[str, Event]]]
        :return: A pair containing the resolved event list and a name-indexed mapping.
        :rtype: Tuple[List[Event], Dict[str, Event]]
        """
        event_objects = [self.parse_event(event) for event in list(events or [])]
        d_events = {get_event_name(event): event for event in event_objects}
        return event_objects, d_events

    def _execute_transition_effect(self, transition: Transition, vars_: Dict[str, Union[int, float]]) -> None:
        """
        Apply a transition's effect operations to a variable mapping.

        Effects are evaluated in declaration order against the mutable ``vars_``
        mapping, so later operations in the same effect block can observe values
        written by earlier ones.

        :param transition: Transition whose effects should be executed.
        :type transition: Transition
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``None``.
        :rtype: None
        """
        for effect in (transition.effects or []):
            vars_[effect.var_name] = effect.expr(**vars_)

    def execute_transition_effect(self, transition: Transition):
        """
        Execute a transition's effects against the runtime's live variables.

        This public wrapper exists mainly for tests and introspection. It uses
        the same effect-order semantics as the internal execution path used by
        actual transitions.

        :param transition: Transition whose effects should be applied.
        :type transition: Transition
        :return: ``None``.
        :rtype: None
        """
        self._execute_transition_effect(transition, self.vars)

    def _execute_func(self, func: Union[OnStage, OnAspect], vars_: Dict[str, Union[int, float]]) -> None:
        """
        Execute a lifecycle or aspect action against a variable mapping.

        Referenced actions are followed transitively through ``func.ref`` until a
        concrete implementation is reached. Abstract actions are logged but do
        not mutate state; concrete actions execute their operations in order.

        :param func: Action to execute.
        :type func: Union[OnStage, OnAspect]
        :param vars_: Variable mapping visible to the action.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``None``.
        :rtype: None
        """
        while func.ref is not None:
            new_func = func.ref
            logging.debug(f'Function {get_func_name(func)} -> {get_func_name(new_func)}.')
            func = new_func

        if func.is_abstract:
            logging.info(f'Execute abstract function {get_func_name(func)}:\n{func.to_ast_node()}')
        else:
            logging.info(f'Execute function {get_func_name(func)}.')
            for op in (func.operations or []):
                vars_[op.var_name] = op.expr(**vars_)

    def execute_func(self, func: Union[OnStage, OnAspect]):
        """
        Execute a lifecycle or aspect action on the live runtime state.

        This method mirrors the action execution semantics used internally by the
        runtime and is primarily useful for tests or interactive inspection.

        :param func: Action to execute.
        :type func: Union[OnStage, OnAspect]
        :return: ``None``.
        :rtype: None
        """
        self._execute_func(func, self.vars)

    def _transition_matches_event(self, transition: Transition, d_events: Dict[str, Event]) -> bool:
        """
        Check whether a transition's event requirement is satisfied.

        Eventless transitions are considered event-matched unconditionally.
        Evented transitions match only when the fully-qualified event name is
        present in ``d_events``.

        :param transition: Transition being tested.
        :type transition: Transition
        :param d_events: Active events indexed by dot-separated name.
        :type d_events: Dict[str, Event]
        :return: ``True`` if the event portion of the transition is satisfied.
        :rtype: bool
        """
        if transition.event is None:
            return True
        return get_event_name(transition.event) in d_events

    def _transition_matches_guard(self, transition: Transition, vars_: Dict[str, Union[int, float]]) -> bool:
        """
        Evaluate a transition's guard against a variable mapping.

        Guardless transitions are accepted immediately. Guarded transitions are
        evaluated with the supplied variable mapping and converted to ``bool``.

        :param transition: Transition being tested.
        :type transition: Transition
        :param vars_: Variables visible to the guard expression.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``True`` if the guard passes.
        :rtype: bool
        """
        if transition.guard is None:
            return True
        return bool(transition.guard(**vars_))

    def is_transition_triggered(self, transition: Transition, d_events: Dict[str, Event]) -> bool:
        """
        Check whether a transition is triggered for the runtime's current state.

        A transition is triggered only when both of its optional conditions are
        satisfied: event matching and guard evaluation. This helper uses the
        runtime's live variable mapping rather than a simulated one.

        :param transition: Transition to test.
        :type transition: Transition
        :param d_events: Active events indexed by dot-separated name.
        :type d_events: Dict[str, Event]
        :return: ``True`` if the transition is triggered.
        :rtype: bool
        """
        matched = self._transition_matches_event(transition, d_events) and self._transition_matches_guard(transition, self.vars)
        if matched:
            logging.info(f'Transition {transition.to_ast_node()} triggered.')
        else:
            logging.debug(f'Transition {transition.to_ast_node()} not triggered.')
        return matched

    def _transition_is_enabled(
        self,
        transition: Transition,
        d_events: Dict[str, Event],
        vars_: Dict[str, Union[int, float]],
    ) -> bool:
        """
        Check whether a transition is enabled in an arbitrary execution context.

        This is the context-parameterized counterpart to
        :meth:`is_transition_triggered`. It is used by validation and init-flow
        logic where guards must be evaluated against cloned variable mappings.

        :param transition: Transition to test.
        :type transition: Transition
        :param d_events: Active events indexed by dot-separated name.
        :type d_events: Dict[str, Event]
        :param vars_: Variable mapping used for guard evaluation.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``True`` if the transition is enabled in the supplied context.
        :rtype: bool
        """
        return self._transition_matches_event(transition, d_events) and self._transition_matches_guard(transition, vars_)

    def _run_leaf_during(self, state: State, vars_: Dict[str, Union[int, float]]) -> None:
        """
        Execute the complete during chain for a leaf state.

        The actual ordering is delegated to
        :meth:`pyfcstm.model.State.iter_on_during_aspect_recursively`, which
        yields ancestor ``>> during before`` actions, the leaf state's own
        ``during`` actions, and then ancestor ``>> during after`` actions in the
        order encoded by the model layer. Pseudo-state behavior is therefore also
        governed by the model layer's traversal logic.

        :param state: Active leaf state whose during chain should run.
        :type state: State
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``None``.
        :rtype: None
        """
        for _, func in state.iter_on_during_aspect_recursively():
            self._execute_func(func, vars_)

    def _enter_state(
        self,
        stack: List[_Frame],
        state: State,
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
    ) -> None:
        """
        Enter a state and perform its immediate entry-time semantics.

        Entering always pushes a new frame and executes the state's ``enter``
        actions first. Leaf states then immediately execute their full during
        chain and switch into ``'after_entry'`` mode so the next cycle can decide
        whether they are already stable. Composite states instead execute their
        local ``during before`` actions, switch into ``'init_wait'`` mode, and
        immediately attempt their initial transition chain.

        :param stack: Target execution stack.
        :type stack: List[_Frame]
        :param state: State being entered.
        :type state: State
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :return: ``None``.
        :rtype: None
        """
        stack.append(_Frame(state, 'active'))
        for on_enter in state.on_enters:
            self._execute_func(on_enter, vars_)

        if state.is_leaf_state:
            self._run_leaf_during(state, vars_)
            stack[-1].mode = 'after_entry'
        else:
            for on_during_before in state.list_on_durings(aspect='before'):
                self._execute_func(on_during_before, vars_)
            stack[-1].mode = 'init_wait'
            self._attempt_init_transition(stack, vars_, d_events)

    def _attempt_init_transition(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
    ) -> bool:
        """
        Attempt to follow a composite state's initial transition.

        Only the current stack-top composite state is considered. The runtime
        scans its ``init_transitions`` in declaration order and enters the target
        substate of the first enabled transition. If no initial transition is
        enabled, the composite state remains in ``'init_wait'`` mode.

        :param stack: Execution stack to inspect and mutate.
        :type stack: List[_Frame]
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :return: ``True`` if an initial transition was taken.
        :rtype: bool
        """
        if not stack:
            return False
        state = stack[-1].state
        if state.is_leaf_state:
            return False

        for transition in state.init_transitions:
            if self._transition_is_enabled(transition, d_events, vars_):
                self._execute_transition_effect(transition, vars_)
                target_state = state.substates[transition.to_state]
                self._enter_state(stack, target_state, vars_, d_events)
                return True
        return False

    def _finalize_exit_to_parent(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
    ) -> bool:
        """
        Complete an ``[*]`` exit after the current state has been popped.

        If the popped state's parent is the root state, exiting to ``[*]`` ends
        the entire runtime and clears the stack. Otherwise the parent remains on
        the stack, executes its local ``during after`` actions, and moves into
        ``'post_child_exit'`` mode so parent-level transitions can be considered
        next.

        :param stack: Execution stack after the child frame has been removed.
        :type stack: List[_Frame]
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :return: ``True`` if the runtime has ended.
        :rtype: bool
        """
        if not stack:
            return True

        parent = stack[-1].state
        if parent.is_root_state:
            stack.clear()
            return True

        for on_during_after in parent.list_on_durings(aspect='after'):
            self._execute_func(on_during_after, vars_)
        stack[-1].mode = 'post_child_exit'
        return False

    def _execute_transition_on_context(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        transition: Transition,
        d_events: Dict[str, Event],
    ) -> bool:
        """
        Execute one transition against a supplied execution context.

        The current stack-top state's ``exit`` actions run first, followed by the
        transition's effect block. The source frame is then removed. Normal
        transitions enter a sibling target state under the same parent; ``[*]``
        exits delegate to :meth:`_finalize_exit_to_parent`.

        :param stack: Execution stack to mutate.
        :type stack: List[_Frame]
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :param transition: Transition to execute.
        :type transition: Transition
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :return: ``True`` if executing the transition ends the runtime.
        :rtype: bool
        """
        current_state = stack[-1].state

        for on_exit in current_state.on_exits:
            self._execute_func(on_exit, vars_)

        self._execute_transition_effect(transition, vars_)
        stack.pop()

        if transition.to_state == EXIT_STATE:
            return self._finalize_exit_to_parent(stack, vars_)

        target_state = current_state.parent.substates[transition.to_state]
        self._enter_state(stack, target_state, vars_, d_events)
        return False

    def _select_transition(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
    ) -> Optional[Transition]:
        """
        Select the next executable transition for the current stack-top state.

        Transitions are considered in declaration order from
        ``current_state.transitions_from``. For stoppable source states, each
        candidate must also pass :meth:`_validate_transition`, which simulates the
        remainder of the chain and rejects transitions that cannot eventually
        reach another stoppable configuration or end the machine.

        :param stack: Execution stack to inspect.
        :type stack: List[_Frame]
        :param vars_: Variable mapping visible to guards.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :return: The first acceptable transition, or ``None``.
        :rtype: Optional[Transition]
        """
        if not stack:
            return None
        current_state = stack[-1].state
        for transition in current_state.transitions_from:
            if not self._transition_is_enabled(transition, d_events, vars_):
                continue
            if current_state.is_stoppable and not self._validate_transition(stack, vars_, transition, d_events):
                continue
            return transition
        return None

    def _validate_transition(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        transition: Transition,
        d_events: Dict[str, Event],
    ) -> bool:
        """
        Validate that taking a transition can reach a stable continuation.

        Validation clones both stack and variables, applies the candidate
        transition, and then simulates the same runtime rules used by
        :meth:`cycle`. The simulation succeeds only if it can eventually reach a
        stable stoppable state or terminate the machine entirely. This is the
        mechanism behind reviewed cases such as 4.26, where a leaf transition is
        accepted only when the subsequent parent-level and target-composite flows
        are also viable.

        :param stack: Current execution stack.
        :type stack: List[_Frame]
        :param vars_: Current variable mapping.
        :type vars_: Dict[str, Union[int, float]]
        :param transition: Candidate transition to validate.
        :type transition: Transition
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :return: ``True`` if the transition leads to a valid continuation.
        :rtype: bool
        """
        sim_stack = self._clone_stack(stack)
        sim_vars = copy.deepcopy(vars_)
        ended = self._execute_transition_on_context(sim_stack, sim_vars, transition, d_events)
        if ended:
            return True

        steps = 0
        max_steps = 1000
        while sim_stack and steps < max_steps:
            frame = sim_stack[-1]
            state = frame.state

            if state.is_leaf_state:
                if frame.mode == 'after_entry':
                    frame.mode = 'active'
                    if state.is_stoppable:
                        return True

                transition = self._select_transition_for_validation(sim_stack, sim_vars, d_events)
                if transition is not None:
                    ended = self._execute_transition_on_context(sim_stack, sim_vars, transition, d_events)
                    if ended:
                        return True
                    steps += 1
                    continue

                if state.is_stoppable:
                    return False
                return False

            if frame.mode == 'init_wait':
                progressed = self._attempt_init_transition(sim_stack, sim_vars, d_events)
                if not progressed:
                    return False
                steps += 1
                continue

            if frame.mode == 'post_child_exit':
                transition = self._select_transition_for_validation(sim_stack, sim_vars, d_events, validate_stoppable=False)
                if transition is None:
                    return False
                ended = self._execute_transition_on_context(sim_stack, sim_vars, transition, d_events)
                if ended:
                    return True
                steps += 1
                continue

            return False

        return False

    def _select_transition_for_validation(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
        validate_stoppable: bool = True,
    ) -> Optional[Transition]:
        """
        Select a transition while simulating future execution during validation.

        This helper mirrors :meth:`_select_transition` but operates on cloned
        execution state. The ``validate_stoppable`` flag is used to suppress
        recursive revalidation in contexts where the caller has already enforced
        the necessary parent-level semantics.

        :param stack: Simulated execution stack.
        :type stack: List[_Frame]
        :param vars_: Simulated variable mapping.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :param validate_stoppable: Whether stoppable-source transitions should be
            recursively validated.
        :type validate_stoppable: bool
        :return: The first acceptable transition in the simulated context, or ``None``.
        :rtype: Optional[Transition]
        """
        if not stack:
            return None
        current_state = stack[-1].state
        for transition in current_state.transitions_from:
            if not self._transition_is_enabled(transition, d_events, vars_):
                continue
            if validate_stoppable and current_state.is_stoppable:
                if not self._validate_transition(stack, vars_, transition, d_events):
                    continue
            return transition
        return None

    def _initialize_runtime(self, d_events: Dict[str, Event]) -> None:
        """
        Perform first-time runtime initialization.

        Initialization clears any existing stack state, enters the root state,
        and lets ordinary entry logic build the first active execution chain. If
        that chain ends immediately, ``_ended`` is set accordingly.

        :param d_events: Active events available during initial entry.
        :type d_events: Dict[str, Event]
        :return: ``None``.
        :rtype: None
        """
        self.stack = []
        self._enter_state(self.stack, self.state_machine.root_state, self.vars, d_events)
        self._initialized = True
        self._ended = len(self.stack) == 0

    def cycle(self, events: List[Union[str, Event]] = None):
        """
        Execute a full runtime cycle until a stable boundary is reached.

        ``cycle()`` repeatedly applies transition, init, and during rules until
        one of four conditions is met: the runtime ends, a stable stoppable leaf
        state is reached, a composite state cannot advance further, or a safety
        limit is hit. In practice this is the method that corresponds most
        closely to the reviewed examples in :mod:`SIMULATE_DESIGN.md`, including
        the difference between 4.25 (stays in ``System1.A``) and 4.26
        (eventually reaches ``System2.B`` once the exit and follow-up
        validations all succeed).

        :param events: Events available for the current cycle.
        :type events: List[Union[str, Event]], optional
        :return: ``None``.
        :rtype: None
        """
        _, d_events = self._normalize_events(events)
        if self._ended:
            logging.info('Runtime ended, nothing to do.')
            return

        if not self._initialized:
            self._initialize_runtime(d_events)

        steps_taken = 0
        max_steps = 1000

        while not self._ended and steps_taken < max_steps:
            if not self.stack:
                self._ended = True
                break

            frame = self.stack[-1]
            state = frame.state

            if state.is_leaf_state:
                if frame.mode == 'after_entry':
                    frame.mode = 'active'
                    if state.is_stoppable:
                        break

                transition = self._select_transition(self.stack, self.vars, d_events)
                if transition is not None:
                    self._ended = self._execute_transition_on_context(self.stack, self.vars, transition, d_events)
                    steps_taken += 1
                    continue

                if frame.mode == 'after_entry':
                    break

                self._run_leaf_during(state, self.vars)
                frame.mode = 'after_entry'
                steps_taken += 1
                continue

            if frame.mode == 'init_wait':
                progressed = self._attempt_init_transition(self.stack, self.vars, d_events)
                steps_taken += 1
                if not progressed:
                    break
                continue

            if frame.mode == 'post_child_exit':
                transition = self._select_transition(self.stack, self.vars, d_events)
                if transition is None:
                    break
                self._ended = self._execute_transition_on_context(self.stack, self.vars, transition, d_events)
                steps_taken += 1
                continue

            break

        if steps_taken >= max_steps:
            logging.error(f'Maximum steps ({max_steps}) reached, possible infinite loop')

        if self._ended or not self.stack:
            self._ended = True
            self.stack = []
            logging.info('Runtime ended.')
        else:
            logging.info(f'Current state: {".".join(self.current_state.path)}')
        logging.info(f'Current vars: {self.vars!r}')

    @property
    def current_state(self) -> State:
        """
        Get the current active state at the top of the execution stack.

        This property is only meaningful when the runtime has not ended and the
        stack is non-empty. Callers typically inspect :attr:`is_ended` first when
        dealing with machines that may already have terminated.

        :return: The current active state.
        :rtype: State
        """
        return self.stack[-1].state

    @property
    def brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        Return a compact representation of the active frame stack.

        Each tuple contains the state's full path and the frame's internal mode.
        The result is useful for debugging or for tests that need to assert the
        runtime's phase without inspecting private frame objects directly.

        :return: List of ``(state_path, mode)`` tuples.
        :rtype: List[Tuple[Tuple[str, ...], str]]
        """
        return [(frame.state.path, frame.mode) for frame in self.stack]

    @property
    def is_ended(self) -> bool:
        """
        Indicate whether the runtime has finished execution.

        Once ``True``, subsequent :meth:`cycle` calls are
        no-ops unless a new :class:`SimulationRuntime` instance is created.

        :return: ``True`` if execution has ended.
        :rtype: bool
        """
        return self._ended
