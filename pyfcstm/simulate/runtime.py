"""
Simulation runtime for executing hierarchical finite state machines.

This module implements the cycle-based execution engine for state machines
parsed from the pyfcstm DSL. The runtime maintains a stateful execution
context including an active state stack, variable mappings, and internal
frame modes that control lifecycle progression through entry, during, exit,
initial transitions, and exit-to-parent flows.

The module contains the following main components:

* :class:`_Frame` - Internal stack frame representing an active state and its
  execution phase.
* :class:`SimulationRuntime` - Stateful runtime environment for executing
  hierarchical state machines with cycle-based semantics.
* :class:`SimulationRuntimeDfsError` - Exception raised when speculative
  validation exceeds safety limits.

Core Execution Model
--------------------

The runtime implements a cycle-based execution model where each cycle advances
the state machine until reaching a stable boundary. A cycle can end in three
ways:

1. **Stoppable State**: Reached a leaf state (non-pseudo) where execution can
   stabilize
2. **Termination**: The state machine has ended (empty stack)
3. **Validation Failure**: Cannot reach a stoppable state, changes rolled back

**Frame Modes**:

The runtime uses internal frame modes to track execution phases:

* ``active``: Normal execution state, ready for transitions or during actions
* ``after_entry``: Just entered a leaf state, during already executed
* ``init_wait``: Composite state waiting for initial transition
* ``post_child_exit``: Parent state after child exited via ``[*]``

**Transition Selection**:

Transitions are always selected from the current stack-top state's
``transitions_from`` list in declaration order. This is critical for
understanding cross-level transition behavior:

* A leaf state can only fire its own transitions
* Parent-level transitions are only considered after the child exits to parent
* This explains why some transitions require explicit exit transitions first

Validation and Rollback
------------------------

**Stoppable State Validation**:

When a stoppable state has an enabled transition, the runtime performs
speculative validation to ensure the transition can eventually reach another
stoppable state or terminate. This prevents cycles from getting stuck in
non-stoppable configurations.

Validation works by:

1. Cloning the current execution context (stack + variables)
2. Executing the candidate transition on the clone
3. Running cycle logic until reaching a stable boundary or failure
4. Accepting the transition only if validation succeeds

**Rollback Semantics**:

If a cycle cannot reach a stoppable state, all variable changes are rolled
back and the runtime remains at the previous stable boundary:

* For normal cycles: Restore previous stack and variables
* For initial cycle: Pin runtime at root boundary in ``init_wait`` mode
* All side effects from failed validation are discarded

**DFS Safety Limits**:

To prevent infinite loops in pathological state machines, validation enforces
two safety limits:

* Maximum 1000 speculative steps per validation attempt
* Maximum 64 structural stack depth
* Repeated execution states are pruned automatically

When these limits are exceeded, :class:`SimulationRuntimeDfsError` is raised,
indicating an invalid state machine with unbounded execution chains.

Lifecycle Execution Order
-------------------------

**Leaf State During Chain**:

When a leaf state executes its during actions, the complete chain includes:

1. Ancestor ``>> during before`` actions (root to leaf order)
2. Leaf state's own ``during`` actions
3. Ancestor ``>> during after`` actions (leaf to root order)

Pseudo states skip ancestor aspect actions entirely.

**Composite State Semantics**:

Composite states have special ``during before`` and ``during after`` actions
that execute at specific boundaries:

* ``during before``: Executes when entering composite from parent (``[*] -> Child``)
  - Runs AFTER composite's ``enter`` but BEFORE child's ``enter``
  - NOT executed during child-to-child transitions
* ``during after``: Executes when exiting composite to parent (``Child -> [*]``)
  - Runs AFTER child's ``exit`` but BEFORE composite's ``exit``
  - NOT executed during child-to-child transitions

**Transition Execution**:

Standard transition execution follows this sequence:

1. Execute source state's ``exit`` actions
2. Execute transition's ``effect`` operations
3. Pop source state from stack
4. If target is ``[*]``, finalize exit to parent
5. Otherwise, enter target state (which may trigger initial transitions)

Example Usage
-------------

Basic cycle execution with transitions::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state System {
    ...     state Idle {
    ...         during { counter = counter + 1; }
    ...     }
    ...     state Active {
    ...         during { counter = counter + 10; }
    ...     }
    ...     [*] -> Idle;
    ...     Idle -> Active :: Start;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.current_state.path
    ('System', 'Idle')
    >>> runtime.vars['counter']
    1
    >>> runtime.cycle(['System.Idle.Start'])
    >>> runtime.current_state.path
    ('System', 'Active')

Exit transitions and parent continuation::

    >>> dsl_code = '''
    ... def int x = 0;
    ... state System1 {
    ...     state A {
    ...         during { x = x + 1; }
    ...     }
    ...     [*] -> A;
    ...     A -> [*] :: Exit;
    ... }
    ... state System2 {
    ...     state B {
    ...         during { x = x + 10; }
    ...     }
    ...     [*] -> B;
    ... }
    ... [*] -> System1;
    ... System1 -> System2 :: Switch;
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.current_state.path
    ('System1', 'A')
    >>> # Provide both Exit and Switch events
    >>> runtime.cycle(['System1.A.Exit', 'Switch'])
    >>> runtime.current_state.path
    ('System2', 'B')

Validation preventing invalid transitions::

    >>> dsl_code = '''
    ... state Root {
    ...     state A;
    ...     state B {
    ...         [*] -> C : if [false];
    ...         state C;
    ...     }
    ...     [*] -> A;
    ...     A -> B :: Go;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.cycle(['Root.A.Go'])
    >>> runtime.current_state.path
    ('Root', 'A')  # Remains in A due to validation failure

Aspect actions with hierarchical execution::

    >>> dsl_code = '''
    ... def int log = 0;
    ... state Root {
    ...     >> during before { log = log + 1; }
    ...     >> during after { log = log + 100; }
    ...     state Active {
    ...         during { log = log + 50; }
    ...     }
    ...     [*] -> Active;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.vars['log']
    151  # Root.aspect_before(1) + Active.during(50) + Root.aspect_after(100)
"""


import copy
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from ..dsl import EXIT_STATE
from ..model import Event, OnAspect, OnStage, State, StateMachine, Transition
from .utils import get_event_name, get_func_name


class SimulationRuntimeDfsError(RuntimeError):
    """
    Raised when speculative validation exceeds safety limits without converging.

    This exception indicates that the state machine contains an invalid
    unbounded execution chain that prevents the runtime from reaching a
    stable stoppable state. The runtime enforces two safety limits during
    speculative validation:

    1. **Step Limit**: Maximum 1000 speculative steps per validation attempt
    2. **Depth Limit**: Maximum 64 structural stack frames

    When either limit is exceeded, validation aborts and raises this exception
    to prevent infinite loops or stack overflow.

    **Why This Happens**:

    This error typically occurs when a state machine has:

    * Composite states with no valid initial transitions
    * Chains of pseudo states that never reach a stoppable state
    * Circular dependencies between exit transitions and parent continuations
    * Guard conditions that create infinite validation loops

    **Error Prevention**:

    To avoid this error, ensure your state machine:

    * Every composite state has at least one unconditional initial transition
    * Pseudo state chains eventually reach a stoppable leaf state
    * Exit transitions lead to valid parent continuations
    * Guard conditions don't create circular validation dependencies

    Example of problematic state machine::

        >>> dsl_code = '''
        ... state Root {
        ...     state A {
        ...         [*] -> B : if [false];  # Always blocked
        ...         pseudo state B;
        ...     }
        ...     [*] -> A;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> runtime = SimulationRuntime(sm)
        >>> runtime.cycle()  # Raises SimulationRuntimeDfsError

    .. note::
       This exception is raised during validation, not during normal execution.
       If you encounter this error, review your state machine definition for
       unbounded execution chains or missing stoppable states.
    """

    pass


@dataclass
class _Frame:
    """
    Internal stack frame representing an active state and its execution phase.

    Frames are stored in the runtime's execution stack from root to the current
    active state. Each frame tracks both the state itself and its current
    execution mode, which controls how the runtime processes the frame during
    cycle execution.

    **Frame Modes**:

    * ``active``: Normal execution state, ready for transitions or during actions
    * ``after_entry``: Just entered a leaf state, during chain already executed,
      waiting to stabilize or fire transitions
    * ``init_wait``: Composite state waiting for an initial transition to enter
      a child state
    * ``post_child_exit``: Parent state after a child exited via ``[*]``,
      ready to consider parent-level transitions

    **Mode Transitions**:

    Leaf states:
    - Enter with ``active`` → execute during chain → switch to ``after_entry``
    - Next cycle: ``after_entry`` → ``active`` (if stoppable, cycle ends here)

    Composite states:
    - Enter with ``active`` → execute ``during before`` → switch to ``init_wait``
    - After child exits: switch to ``post_child_exit``

    :param state: The active state represented by this frame.
    :type state: State
    :param mode: Internal execution phase controlling frame processing.
    :type mode: str

    Example::

        >>> # Internal frame structure (not directly created by users)
        >>> frame = _Frame(state=some_state, mode='active')
        >>> frame.state.path
        ('System', 'Active')
        >>> frame.mode
        'active'

    .. note::
       This is an internal implementation detail. Users should interact with
       the runtime through :class:`SimulationRuntime` methods rather than
       manipulating frames directly.
    """

    state: State
    mode: str


class SimulationRuntime:
    """
    Runtime environment for executing hierarchical finite state machines.

    This class provides the stateful execution engine for state machines parsed
    from the pyfcstm DSL. It maintains an active state stack, variable mappings,
    and lifecycle flags that control cycle-based execution semantics.

    **Core Execution Model**:

    The runtime implements cycle-based execution where each :meth:`cycle` call
    advances the state machine until reaching a stable boundary. Cycles can end
    in three ways:

    1. **Stoppable State**: Reached a leaf state (non-pseudo) where execution
       can stabilize
    2. **Termination**: The state machine has ended (empty stack)
    3. **Validation Failure**: Cannot reach a stoppable state, changes rolled back

    **Transition Selection**:

    Transitions are always selected from the current stack-top state's
    ``transitions_from`` list in declaration order. This is critical for
    understanding cross-level transition behavior:

    * A leaf state can only fire its own transitions
    * Parent-level transitions are only considered after the child exits to parent
    * This explains why some transitions require explicit exit transitions first

    For example, if state ``System1.A`` wants to trigger a parent-level
    transition ``System1 -> System2``, it must first exit to parent via
    ``A -> [*]``, which puts ``System1`` in ``post_child_exit`` mode where
    parent-level transitions can be considered.

    **Validation and Rollback**:

    When a stoppable state has an enabled transition, the runtime performs
    speculative validation to ensure the transition can eventually reach another
    stoppable state or terminate. This prevents cycles from getting stuck in
    non-stoppable configurations.

    If validation fails or a cycle cannot reach a stoppable state, all variable
    changes are rolled back and the runtime remains at the previous stable
    boundary. For the initial cycle, rollback pins the runtime at the root
    boundary in ``init_wait`` mode.

    **DFS Safety Limits**:

    To prevent infinite loops in pathological state machines, validation enforces
    two safety limits:

    * Maximum 1000 speculative steps per validation attempt
    * Maximum 64 structural stack depth
    * Repeated execution states are pruned automatically

    When these limits are exceeded, :class:`SimulationRuntimeDfsError` is raised.

    :param state_machine: The state machine model to simulate.
    :type state_machine: StateMachine

    :ivar state_machine: The state machine being simulated.
    :vartype state_machine: StateMachine
    :ivar stack: Active frames ordered from root to current execution point.
    :vartype stack: List[_Frame]
    :ivar vars: Mutable variable values visible to guards, effects, and actions.
    :vartype vars: Dict[str, Union[int, float]]
    :ivar _initialized: Whether the runtime has performed root entry.
    :vartype _initialized: bool
    :ivar _ended: Whether execution has terminated (empty stack).
    :vartype _ended: bool

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.simulate import SimulationRuntime
        >>> dsl_code = '''
        ... def int counter = 0;
        ... state System {
        ...     state Idle {
        ...         during { counter = counter + 1; }
        ...     }
        ...     state Active {
        ...         during { counter = counter + 10; }
        ...     }
        ...     [*] -> Idle;
        ...     Idle -> Active :: Start;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> runtime = SimulationRuntime(sm)
        >>> runtime.cycle()
        >>> runtime.current_state.path
        ('System', 'Idle')
        >>> runtime.vars['counter']
        1
        >>> runtime.cycle(['System.Idle.Start'])
        >>> runtime.current_state.path
        ('System', 'Active')
        >>> runtime.vars['counter']
        11
    """

    def __init__(self, state_machine: StateMachine):
        """
        Initialize the simulation runtime with a state machine model.

        This constructor prepares the runtime for execution by initializing
        variable storage from the state machine's variable definitions. Variables
        are initialized in declaration order, allowing later initializers to
        reference earlier variables.

        The runtime is not fully initialized until the first :meth:`cycle` call,
        which performs root state entry and builds the initial execution stack.

        :param state_machine: The state machine model to simulate.
        :type state_machine: StateMachine
        :return: ``None``.
        :rtype: None

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... def int x = 10;
            ... def int y = x + 5;  # Can reference earlier variables
            ... state Root {
            ...     state A;
            ...     [*] -> A;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.vars
            {'x': 10, 'y': 15}
            >>> runtime.is_ended
            False
            >>> runtime.stack
            []  # Not initialized until first cycle

        .. note::
           Variable initialization happens eagerly during construction, but
           state entry is deferred until the first :meth:`cycle` call. This
           allows inspection of initial variable values before execution begins.
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
        Resolve an event reference into a concrete event object.

        This method accepts either an event object (returned as-is) or a
        dot-separated event path string. String paths are resolved by walking
        the state hierarchy to find the enclosing state, then looking up the
        event name in that state's event table.

        **Path Resolution**:

        Event paths follow the format ``State1.State2.EventName`` where:
        - ``State1.State2`` is the state hierarchy path
        - ``EventName`` is the event name in the final state's event table

        If the path starts with the root state name, it's treated as an explicit
        root prefix and skipped during resolution.

        :param event: Event object or dot-separated event path string.
        :type event: Union[str, Event]
        :return: The resolved event instance.
        :rtype: Event
        :raises TypeError: If ``event`` is neither a string nor an :class:`Event`.

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... state System {
            ...     state Idle;
            ...     state Active;
            ...     [*] -> Idle;
            ...     Idle -> Active :: Start;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> # Parse event by string path
            >>> event = runtime.parse_event('System.Idle.Start')
            >>> event.name
            'Start'
            >>> # Parse event by object (returns same object)
            >>> same_event = runtime.parse_event(event)
            >>> same_event is event
            True

        .. note::
           This method is used internally by :meth:`cycle` to normalize the
           events parameter. Users typically pass string paths directly to
           :meth:`cycle` rather than calling this method explicitly.
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

        This method applies the transition's effect operations to the runtime's
        variable mapping in declaration order. Each operation evaluates its
        expression and assigns the result to the target variable.

        This is a public wrapper around the internal effect execution logic,
        primarily useful for testing and introspection.

        :param transition: Transition whose effects should be applied.
        :type transition: Transition
        :return: ``None``.
        :rtype: None

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... def int x = 0;
            ... def int y = 0;
            ... state Root {
            ...     state A;
            ...     state B;
            ...     [*] -> A;
            ...     A -> B effect {
            ...         x = 10;
            ...         y = x + 5;
            ...     }
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> transition = sm.root_state.substates['A'].transitions_from[0]
            >>> runtime.execute_transition_effect(transition)
            >>> runtime.vars
            {'x': 10, 'y': 15}

        .. note::
           This method mutates the runtime's live variable mapping. It's
           primarily intended for testing and debugging rather than normal
           runtime operation.
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

        This method executes the action's operations against the runtime's
        variable mapping. Referenced actions are followed transitively through
        ``func.ref`` until a concrete implementation is reached. Abstract
        actions are logged but do not mutate state.

        This is a public wrapper around the internal action execution logic,
        primarily useful for testing and introspection.

        :param func: Lifecycle or aspect action to execute.
        :type func: Union[OnStage, OnAspect]
        :return: ``None``.
        :rtype: None

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... def int counter = 0;
            ... state Root {
            ...     state A {
            ...         enter Initialize {
            ...             counter = 100;
            ...         }
            ...     }
            ...     [*] -> A;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> enter_action = sm.root_state.substates['A'].on_enters[0]
            >>> runtime.execute_func(enter_action)
            >>> runtime.vars['counter']
            100

        .. note::
           This method mutates the runtime's live variable mapping. It's
           primarily intended for testing and debugging rather than normal
           runtime operation.
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
        *,
        validate_stoppable: bool = True,
    ) -> Optional[Transition]:
        """
        Select the next executable transition for the current stack-top state.

        Transitions are considered in declaration order from
        ``current_state.transitions_from``. For stoppable source states, each
        candidate may also pass :meth:`_validate_transition`, which simulates the
        remainder of the chain and rejects transitions that cannot eventually
        reach another stoppable configuration or end the machine.

        :param stack: Execution stack to inspect.
        :type stack: List[_Frame]
        :param vars_: Variable mapping visible to guards.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :param validate_stoppable: Whether stoppable-source transitions should be
            recursively validated.
        :type validate_stoppable: bool
        :return: The first acceptable transition, or ``None``.
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

        success, _ = self._run_cycle_on_context(
            sim_stack,
            sim_vars,
            d_events,
            ended=ended,
            validate_post_child_exit=False,
        )
        return success

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

    def _initialize_context(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
    ) -> bool:
        """
        Initialize an arbitrary execution context from the root state.

        This helper mirrors :meth:`_initialize_runtime` but operates on caller-
        supplied stack and variable containers so cycle-level speculative
        execution can start from a cloned context.

        :param stack: Execution stack to reset and initialize.
        :type stack: List[_Frame]
        :param vars_: Variable mapping visible during initialization.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events available during initial entry.
        :type d_events: Dict[str, Event]
        :return: ``True`` if initialization ends the runtime immediately.
        :rtype: bool
        """
        stack.clear()
        self._enter_state(stack, self.state_machine.root_state, vars_, d_events)
        return len(stack) == 0

    def _create_root_rollback_stack(self) -> List[_Frame]:
        """
        Create the rollback stack used for initial-cycle dead ends.

        When the very first cycle cannot reach a stoppable state, the reviewed
        design keeps the runtime pinned at the root boundary with all simulated
        side effects discarded. The returned stack represents that boundary.

        :return: Single-frame stack rooted at the state machine root.
        :rtype: List[_Frame]
        """
        return [_Frame(self.state_machine.root_state, 'init_wait')]

    @staticmethod
    def _create_execution_signature(
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
    ) -> Tuple[Tuple[Tuple[str, ...], str], Tuple[Tuple[str, Union[int, float]], ...]]:
        """
        Build a hashable execution signature for DFS pruning.

        The signature captures the full active stack shape, each frame mode, and
        the current numeric variable mapping in deterministic key order. It is
        used only for speculative DFS protection so repeated execution states on
        the same search path can be pruned safely.

        :param stack: Execution stack to summarize.
        :type stack: List[_Frame]
        :param vars_: Variable mapping to summarize.
        :type vars_: Dict[str, Union[int, float]]
        :return: Hashable execution signature.
        :rtype: Tuple[Tuple[Tuple[str, ...], str], Tuple[Tuple[str, Union[int, float]], ...]]
        """
        stack_signature = tuple((frame.state.path, frame.mode) for frame in stack)
        vars_signature = tuple((key, vars_[key]) for key in sorted(vars_))
        return stack_signature, vars_signature

    @staticmethod
    def _create_structural_signature(stack: List[_Frame]) -> Tuple[Tuple[Tuple[str, ...], str], ...]:
        """
        Build a stack-shape signature for deep-search protection.

        Unlike :meth:`_create_execution_signature`, this helper ignores variable
        values and keeps only the structural execution path. It is used to
        detect unbounded speculative descent through ever-new stack/mode shapes.

        :param stack: Execution stack to summarize.
        :type stack: List[_Frame]
        :return: Hashable structural signature.
        :rtype: Tuple[Tuple[Tuple[str, ...], str], ...]
        """
        return tuple((frame.state.path, frame.mode) for frame in stack)

    def _raise_dfs_depth_error(self, max_steps: int) -> None:
        """
        Raise the DFS safety error used for pathological speculative searches.

        :param max_steps: Maximum speculative steps permitted before aborting.
        :type max_steps: int
        :raises SimulationRuntimeDfsError: Always raised to signal a non-converging DFS.
        """
        raise SimulationRuntimeDfsError(
            'Speculative DFS exceeded the safety limit without reaching a '
            f'stoppable state, ending the runtime, or being pruned after {max_steps} steps; '
            'the state machine likely contains an invalid unbounded execution chain.'
        )

    def _run_cycle_on_context(
        self,
        stack: List[_Frame],
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
        *,
        ended: bool = False,
        validate_post_child_exit: bool = True,
    ) -> Tuple[bool, bool]:
        """
        Advance a full cycle on an arbitrary execution context.

        The context is mutated in place using the same rules as :meth:`cycle`.
        Success means the execution reaches either a stoppable stable boundary
        or machine termination. Failure means the cycle cannot form a valid
        stoppable continuation and should therefore be rolled back by the caller.
        Repeated execution states within the same speculative search are pruned,
        while unusually deep non-converging searches raise
        :class:`SimulationRuntimeDfsError` to indicate a likely invalid state
        machine definition.

        :param stack: Execution stack to mutate.
        :type stack: List[_Frame]
        :param vars_: Variable mapping to mutate.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events for the current execution attempt.
        :type d_events: Dict[str, Event]
        :param ended: Whether the supplied context has already ended.
        :type ended: bool
        :param validate_post_child_exit: Whether transitions selected after a
            child exits to its parent should still perform stoppable validation.
        :type validate_post_child_exit: bool
        :return: Pair ``(success, ended)`` describing the result.
        :rtype: Tuple[bool, bool]
        :raises SimulationRuntimeDfsError: If speculative DFS exceeds the safety
            limit without convergence or pruning.
        """
        if ended:
            return True, True

        steps_taken = 0
        max_steps = 1000
        seen_signatures = set()
        max_structural_depth = 64

        while not ended:
            if not stack:
                ended = True
                break

            signature = self._create_execution_signature(stack, vars_)
            if signature in seen_signatures:
                logging.warning('Pruned repeated speculative execution state during DFS validation.')
                return False, False
            seen_signatures.add(signature)

            structural_signature = self._create_structural_signature(stack)
            if len(structural_signature) > max_structural_depth:
                raise SimulationRuntimeDfsError(
                    'Speculative DFS exceeded the structural stack-depth safety limit '
                    f'({max_structural_depth}) without reaching a stoppable state or pruning; '
                    'the state machine likely contains an invalid unbounded nesting chain.'
                )

            if steps_taken >= max_steps:
                logging.warning(
                    'Speculative DFS reached the step safety limit (%s) without convergence; '
                    'treating the path as invalid continuation.',
                    max_steps,
                )
                return False, False

            frame = stack[-1]
            state = frame.state

            if state.is_leaf_state:
                if frame.mode == 'after_entry':
                    frame.mode = 'active'
                    if state.is_stoppable:
                        return True, False
                    steps_taken += 1
                    continue

                transition = self._select_transition(stack, vars_, d_events)
                if transition is not None:
                    ended = self._execute_transition_on_context(stack, vars_, transition, d_events)
                    steps_taken += 1
                    if ended:
                        return True, True
                    continue

                self._run_leaf_during(state, vars_)
                frame.mode = 'after_entry'
                steps_taken += 1
                continue

            if frame.mode == 'init_wait':
                progressed = self._attempt_init_transition(stack, vars_, d_events)
                steps_taken += 1
                if not progressed:
                    return False, False
                continue

            if frame.mode == 'post_child_exit':
                transition = self._select_transition(
                    stack,
                    vars_,
                    d_events,
                    validate_stoppable=validate_post_child_exit,
                )
                if transition is None:
                    return False, False
                ended = self._execute_transition_on_context(stack, vars_, transition, d_events)
                steps_taken += 1
                if ended:
                    return True, True
                continue

            return False, False

        return True, True

    def cycle(self, events: List[Union[str, Event]] = None):
        """
        Execute a full runtime cycle until reaching a stable boundary.

        This method advances the state machine through transitions and lifecycle
        actions until one of three conditions is met:

        1. **Stoppable State**: Reached a leaf state (non-pseudo) where execution
           can stabilize
        2. **Termination**: The state machine has ended (empty stack)
        3. **Validation Failure**: Cannot reach a stoppable state, changes rolled back

        **Cycle Execution Flow**:

        The cycle operates in two phases:

        1. **Speculative Execution**: Clone the current context and simulate the
           cycle to validate it can reach a stable boundary
        2. **Commit or Rollback**: If validation succeeds, commit the changes;
           otherwise, rollback to the previous stable state

        **Event Handling**:

        Events can be provided as either event objects or dot-separated path
        strings. Multiple events can be active simultaneously, allowing complex
        transition chains to execute in a single cycle.

        **Validation and Safety**:

        When a stoppable state has an enabled transition, the runtime validates
        that taking the transition can eventually reach another stoppable state
        or terminate. This prevents cycles from getting stuck in non-stoppable
        configurations.

        Validation enforces safety limits:
        - Maximum 1000 speculative steps per validation
        - Maximum 64 structural stack depth
        - Repeated execution states are pruned automatically

        **Rollback Behavior**:

        If a cycle cannot reach a stoppable state, all variable changes are
        rolled back:
        - For normal cycles: Restore previous stack and variables
        - For initial cycle: Pin runtime at root boundary in ``init_wait`` mode
        - All side effects from failed validation are discarded

        :param events: Events available for the current cycle. Can be event
            objects or dot-separated path strings.
        :type events: List[Union[str, Event]], optional
        :return: ``None``.
        :rtype: None

        Example - Basic cycle execution::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... def int counter = 0;
            ... state System {
            ...     state Idle {
            ...         during { counter = counter + 1; }
            ...     }
            ...     state Active {
            ...         during { counter = counter + 10; }
            ...     }
            ...     [*] -> Idle;
            ...     Idle -> Active :: Start;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()  # Initialize and reach Idle
            >>> runtime.current_state.path
            ('System', 'Idle')
            >>> runtime.vars['counter']
            1
            >>> runtime.cycle(['System.Idle.Start'])  # Transition to Active
            >>> runtime.current_state.path
            ('System', 'Active')

        Example - Exit transitions and parent continuation::

            >>> dsl_code = '''
            ... def int x = 0;
            ... state System1 {
            ...     state A {
            ...         during { x = x + 1; }
            ...     }
            ...     [*] -> A;
            ...     A -> [*] :: Exit;
            ... }
            ... state System2 {
            ...     state B {
            ...         during { x = x + 10; }
            ...     }
            ...     [*] -> B;
            ... }
            ... [*] -> System1;
            ... System1 -> System2 :: Switch;
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.current_state.path
            ('System1', 'A')
            >>> # Provide both Exit and Switch events
            >>> runtime.cycle(['System1.A.Exit', 'Switch'])
            >>> runtime.current_state.path
            ('System2', 'B')

        Example - Validation preventing invalid transitions::

            >>> dsl_code = '''
            ... state Root {
            ...     state A;
            ...     state B {
            ...         [*] -> C : if [false];  # Blocked initial transition
            ...         state C;
            ...     }
            ...     [*] -> A;
            ...     A -> B :: Go;  # Rejected by validation
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.cycle(['Root.A.Go'])  # Rejected - cannot reach stoppable
            >>> runtime.current_state.path
            ('Root', 'A')  # Remains in A due to validation failure

        Example - Multiple cycles with state changes::

            >>> dsl_code = '''
            ... def int counter = 0;
            ... state Root {
            ...     state A {
            ...         during { counter = counter + 1; }
            ...     }
            ...     [*] -> A;
            ...     A -> A : if [counter >= 3];  # Self-transition after 3 cycles
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.vars['counter']
            1
            >>> runtime.cycle()
            >>> runtime.vars['counter']
            2
            >>> runtime.cycle()
            >>> runtime.vars['counter']
            3
            >>> runtime.cycle()  # Self-transition fires
            >>> runtime.vars['counter']
            4  # Exit + re-enter + during

        .. note::
           Once the runtime has ended (:attr:`is_ended` is ``True``), subsequent
           :meth:`cycle` calls are no-ops. Create a new :class:`SimulationRuntime`
           instance to restart execution.

        .. warning::
           If validation exceeds safety limits (1000 steps or 64 stack depth),
           :class:`SimulationRuntimeDfsError` is raised. This indicates an
           invalid state machine with unbounded execution chains.
        """
        _, d_events = self._normalize_events(events)
        if self._ended:
            logging.warning('Runtime already ended, cycle ignored.')
            return

        snapshot_stack = self._clone_stack(self.stack)
        snapshot_vars = copy.deepcopy(self.vars)
        snapshot_initialized = self._initialized
        snapshot_ended = self._ended

        sim_stack = self._clone_stack(self.stack)
        sim_vars = copy.deepcopy(self.vars)
        sim_initialized = self._initialized
        sim_ended = self._ended

        if not sim_initialized:
            sim_ended = self._initialize_context(sim_stack, sim_vars, d_events)
            sim_initialized = True

        success, sim_ended = self._run_cycle_on_context(sim_stack, sim_vars, d_events, ended=sim_ended)

        if success:
            self.stack = [] if sim_ended else sim_stack
            self.vars = sim_vars
            self._initialized = sim_initialized
            self._ended = sim_ended
        else:
            self.vars = snapshot_vars
            self._ended = snapshot_ended
            if not snapshot_initialized and not snapshot_ended:
                self.stack = self._create_root_rollback_stack()
                self._initialized = True
            else:
                self.stack = snapshot_stack
                self._initialized = snapshot_initialized
            logging.warning('Unable to reach a stoppable state in current cycle, changes rolled back.')

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

        This property returns the state currently being executed by the runtime.
        For leaf states, this is the state where during actions execute. For
        composite states in ``init_wait`` mode, this is the parent waiting for
        an initial transition.

        :return: The current active state.
        :rtype: State
        :raises IndexError: If the runtime has ended and the stack is empty.

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... state System {
            ...     state Idle;
            ...     state Active;
            ...     [*] -> Idle;
            ...     Idle -> Active :: Start;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.current_state.name
            'Idle'
            >>> runtime.current_state.path
            ('System', 'Idle')
            >>> runtime.cycle(['System.Idle.Start'])
            >>> runtime.current_state.name
            'Active'

        .. note::
           This property is only meaningful when the runtime has not ended.
           Check :attr:`is_ended` first to avoid accessing an empty stack.
        """
        return self.stack[-1].state

    @property
    def brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        Return a compact representation of the active execution stack.

        Each tuple contains the state's full path and the frame's internal mode.
        This representation is useful for debugging, testing, and understanding
        the runtime's current execution phase without inspecting internal frame
        objects directly.

        **Frame Modes**:

        * ``active``: Normal execution state
        * ``after_entry``: Just entered a leaf state, during already executed
        * ``init_wait``: Composite state waiting for initial transition
        * ``post_child_exit``: Parent state after child exited via ``[*]``

        :return: List of ``(state_path, mode)`` tuples from root to current state.
        :rtype: List[Tuple[Tuple[str, ...], str]]

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... state System {
            ...     state SubSystem {
            ...         state Active;
            ...         [*] -> Active;
            ...     }
            ...     [*] -> SubSystem;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.brief_stack
            [(('System',), 'active'), (('System', 'SubSystem'), 'active'), (('System', 'SubSystem', 'Active'), 'active')]

        .. note::
           This property is primarily useful for testing and debugging. It
           provides insight into the runtime's internal execution state without
           exposing the internal :class:`_Frame` objects.
        """
        return [(frame.state.path, frame.mode) for frame in self.stack]

    @property
    def is_ended(self) -> bool:
        """
        Indicate whether the runtime has finished execution.

        Once ``True``, the state machine has terminated and the execution stack
        is empty. Subsequent :meth:`cycle` calls become no-ops. To restart
        execution, create a new :class:`SimulationRuntime` instance.

        **Termination Conditions**:

        The runtime ends when:
        - The root state exits to ``[*]``
        - An exit transition from a root-level state completes
        - The execution stack becomes empty for any reason

        :return: ``True`` if execution has ended, ``False`` otherwise.
        :rtype: bool

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... def int counter = 0;
            ... state System {
            ...     state Active {
            ...         during { counter = counter + 1; }
            ...     }
            ...     [*] -> Active;
            ...     Active -> [*] : if [counter >= 3];
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.is_ended
            False
            >>> runtime.cycle()
            >>> runtime.is_ended
            False
            >>> runtime.cycle()
            >>> runtime.is_ended
            False
            >>> runtime.cycle()
            >>> runtime.is_ended
            False
            >>> runtime.cycle()  # counter >= 3, exit transition fires
            >>> runtime.is_ended
            True
            >>> runtime.cycle()  # No-op, runtime already ended
            >>> runtime.is_ended
            True

        .. note::
           Once the runtime has ended, the only way to restart execution is
           to create a new :class:`SimulationRuntime` instance with the same
           or a different state machine model.
        """
        return self._ended
