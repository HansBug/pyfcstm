"""
Simulation runtime for executing hierarchical finite state machines.

This module implements a cycle-based execution engine for state machines parsed
from the pyfcstm DSL. The runtime maintains an execution stack of active states,
variable mappings, and internal frame modes that control lifecycle progression.

Each cycle advances the state machine until reaching a stable boundary: either a
stoppable state (non-pseudo leaf state), termination (empty stack), or validation
failure (changes rolled back). The runtime uses speculative validation to ensure
transitions can reach valid stable states before executing them.

The execution model uses internal frame modes (active, after_entry, init_wait,
post_child_exit) to track execution phases. Transitions are selected from the
current stack-top state's transitions in declaration order. Parent-level transitions
are only considered after a child explicitly exits to parent via [*] transitions.

Lifecycle actions execute in a specific order: enter when entering states, during
while in leaf states each cycle, and exit when leaving states. For leaf states,
the during chain includes ancestor aspect actions (>> during before/after) that
execute before and after the leaf's own during actions. Pseudo states skip ancestor
aspect actions entirely.

Composite states have special during before/after actions that execute only at
composite boundaries: during before runs when entering from parent ([*] -> Child),
and during after runs when exiting to parent (Child -> [*]). These do NOT execute
during child-to-child transitions.

Validation works by cloning the execution context and speculatively executing the
transition until reaching a stable boundary. If validation succeeds, the real
transition executes. If validation fails or exceeds safety limits (1000 steps or
64 stack depth), the transition is rejected and variables roll back.

Abstract actions can be implemented by registering Python handlers that receive
read-only execution context. Handlers can be registered individually or organized
in classes using the @abstract_handler decorator.

Basic usage::

    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(state_machine)
    runtime.cycle()  # Execute first cycle
    runtime.cycle(['EventName'])  # Execute with events

    # Access state and variables
    current_state = runtime.current_state
    variables = runtime.vars

Abstract handler registration::

    def my_handler(ctx):
        print(f"State: {ctx.get_full_state_path()}")

    runtime.register_abstract_handler('System.Active.Init', my_handler)

    # Or use decorator-based registration
    from pyfcstm.simulate import abstract_handler

    class MyHandlers:
        @abstract_handler('System.Active.Init')
        def handle_init(self, ctx):
            print(f"Counter: {ctx.get_var('counter')}")

    runtime.register_handlers_from_object(MyHandlers())
"""

import copy
import warnings
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from .logging import get_logger

from ..dsl import EXIT_STATE
from ..model import Event, OnAspect, OnStage, State, StateMachine, Transition
from .context import ReadOnlyExecutionContext


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

    def __init__(
            self,
            state_machine: StateMachine,
            abstract_error_mode: Literal['raise', 'log'] = 'raise',
            history_size: Optional[int] = None
    ):
        """
        Initialize the simulation runtime with a state machine model.

        This constructor prepares the runtime for execution by initializing
        variable storage from the state machine's variable definitions and
        setting up the initial execution stack with the root state. Variables
        are initialized in declaration order, allowing later initializers to
        reference earlier variables.

        The runtime stack is initialized with the root state in ``init_wait``
        mode, allowing :attr:`current_state` to be accessed immediately. Full
        initialization (entering the root state and executing lifecycle actions)
        is deferred until the first :meth:`cycle` call.

        :param state_machine: The state machine model to simulate.
        :type state_machine: StateMachine
        :param abstract_error_mode: Error handling mode for abstract handler exceptions.
            ``'raise'`` (default) stops execution and raises the exception.
            ``'log'`` logs the exception and continues execution.
        :type abstract_error_mode: Literal['raise', 'log']
        :param history_size: Maximum number of history entries to keep.
            ``None`` (default) means unlimited history.
        :type history_size: Optional[int]
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
            >>> runtime.current_state.name
            'Root'
            >>> runtime.current_state.path
            ('Root',)

        .. note::
           Variable initialization and stack setup happen during construction,
           but state entry actions are deferred until the first :meth:`cycle`
           call. This allows inspection of initial variable values and the
           root state before execution begins.
        """
        self.state_machine = state_machine
        self.stack: List[_Frame] = []
        self.vars: Dict[str, Union[int, float]] = {}
        self.cycle_count: int = 0  # Track number of cycles executed
        self.history_size: Optional[int] = history_size  # Maximum history entries (None = unlimited)
        self.history: List[Dict] = []  # Execution history

        # Initialize logger
        self.logger = get_logger()

        for name, define in self.state_machine.defines.items():
            self.vars[name] = define.init(**self.vars)

        self._initialized = False
        self._ended = False

        # Abstract handler registry: action_path -> list of handlers
        self._abstract_handlers: Dict[str, List[Callable[[ReadOnlyExecutionContext], None]]] = {}

        # Track warned anonymous abstracts to avoid duplicate warnings
        self._warned_anonymous_abstracts: set = set()

        # Error handling mode for abstract handlers
        self._abstract_error_mode: Literal['raise', 'log'] = abstract_error_mode

        # Track abstract handler errors (only used in 'log' mode)
        self._abstract_handler_errors: List[Tuple[str, Exception]] = []

        # Error state flag (set to True when handler error occurs in 'raise' mode)
        self._is_error_state = False
        self._error_info: Optional[Tuple[str, Exception]] = None

        # Initialize stack with root state to allow current_state access before first cycle
        self.stack.append(_Frame(self.state_machine.root_state, 'init_wait'))

    def _parse_event(self, event: Union[str, Event]) -> Event:
        """
        Resolve an event reference into a concrete event object.

        This method accepts either an event object (returned as-is) or a
        dot-separated event path string. String paths are resolved using
        intelligent resolution that supports both StateMachine and State
        resolve_event methods for maximum flexibility.

        **Path Resolution Strategy**:

        The method uses a smart resolution strategy based on the current runtime
        state and path syntax:

        1. **If runtime has ended** (no current state): Use StateMachine.resolve_event only
        2. **If path is definitely State.resolve_event syntax** (starts with ``/`` or ``.``):
           Use State.resolve_event from current state
        3. **If path is uncertain** (plain path like ``Root.System.event``):
           Try StateMachine.resolve_event first, fall back to State.resolve_event if it fails

        **Supported Path Formats**:

        - **Full paths**: ``Root.State1.State2.EventName`` (StateMachine.resolve_event)
        - **Relative paths**: ``error.critical`` (State.resolve_event from current state)
        - **Parent-relative**: ``.error`` or ``..system.error`` (State.resolve_event)
        - **Absolute**: ``/global.shutdown`` (State.resolve_event from root)

        :param event: Event object or dot-separated event path string.
        :type event: Union[str, Event]
        :return: The resolved event instance.
        :rtype: Event
        :raises TypeError: If ``event`` is neither a string nor an :class:`Event`.
        :raises LookupError: If the event path cannot be resolved by either method.

        Example::

            >>> from pyfcstm.dsl import parse_with_grammar_entry
            >>> from pyfcstm.model import parse_dsl_node_to_state_machine
            >>> from pyfcstm.simulate import SimulationRuntime
            >>> dsl_code = '''
            ... state System {
            ...     state Idle {
            ...         event Start;
            ...     }
            ...     state Active {
            ...         event Timeout;
            ...     }
            ...     [*] -> Idle;
            ...     Idle -> Active :: Start;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> # Full path (StateMachine.resolve_event)
            >>> event1 = runtime._parse_event('System.Idle.Start')
            >>> event1.name
            'Start'
            >>> # Relative path (State.resolve_event from current state)
            >>> event2 = runtime._parse_event('Start')
            >>> event2.name
            'Start'
            >>> # Parent-relative path (State.resolve_event)
            >>> event3 = runtime._parse_event('.Start')
            >>> event3.name
            'Start'
            >>> # Absolute path (State.resolve_event)
            >>> event4 = runtime._parse_event('/Idle.Start')
            >>> event4.name
            'Start'

        .. note::
           This method is used internally by :meth:`cycle` to normalize the
           events parameter. Users can pass any supported path format directly
           to :meth:`cycle` for maximum flexibility.
        """
        if isinstance(event, Event):
            return event
        elif isinstance(event, str):
            from .utils import is_state_resolve_event_path

            # Check if runtime has ended (no current state)
            has_current_state = len(self.stack) > 0

            # If runtime has ended, only use StateMachine.resolve_event
            if not has_current_state:
                return self.state_machine.resolve_event(event)

            # Check if path is definitely State.resolve_event syntax
            is_definitely_state_path = is_state_resolve_event_path(event)

            if is_definitely_state_path:
                # Use State.resolve_event from current state
                return self.current_state.resolve_event(event)
            else:
                # Uncertain path - try StateMachine first, then State
                try:
                    return self.state_machine.resolve_event(event)
                except (ValueError, LookupError):
                    # Fall back to State.resolve_event
                    try:
                        return self.current_state.resolve_event(event)
                    except (ValueError, LookupError) as e:
                        # Both methods failed - raise informative error
                        raise LookupError(
                            f"Cannot resolve event path {event!r}: "
                            f"failed with both StateMachine.resolve_event and State.resolve_event. "
                            f"Last error: {e}"
                        ) from e
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
        dictionary keyed by :attr:`Event.path_name` so transition
        matching can perform constant-time membership checks.

        :param events: Raw event inputs for the current execution attempt.
        :type events: Optional[List[Union[str, Event]]]
        :return: A pair containing the resolved event list and a name-indexed mapping.
        :rtype: Tuple[List[Event], Dict[str, Event]]
        """
        event_objects = [self._parse_event(event) for event in list(events or [])]
        d_events = {event.path_name: event for event in event_objects}
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

    def _execute_func(
            self,
            func: Union[OnStage, OnAspect],
            vars_: Dict[str, Union[int, float]],
            is_validation_mode: bool = False
    ) -> None:
        """
        Execute a lifecycle or aspect action against a variable mapping.

        Referenced actions are followed transitively through ``func.ref`` until a
        concrete implementation is reached. Abstract actions are logged but do
        not mutate state; concrete actions execute their operations in order.

        For abstract actions:
        - If the action has a name and registered handlers exist, all handlers
          are executed in registration order with a read-only context.
        - If the action has a name but no handlers, a warning is logged.
        - If the action has no name, a warning is issued on first execution
          (only once per unique action).
        - In validation mode, handlers are never executed.

        :param func: Action to execute.
        :type func: Union[OnStage, OnAspect]
        :param vars_: Variable mapping visible to the action.
        :type vars_: Dict[str, Union[int, float]]
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
        :return: ``None``.
        :rtype: None
        """
        while func.ref is not None:
            new_func = func.ref
            self.logger.debug(f'Function {func.func_name} -> {new_func.func_name}.')
            func = new_func

        if func.is_abstract:
            func_path = func.func_name

            # Check if this is an anonymous abstract (no name)
            if func.name is None:
                # Generate a unique key for this anonymous abstract
                anonymous_key = id(func)

                # Warn only once per anonymous abstract
                if anonymous_key not in self._warned_anonymous_abstracts:
                    warnings.warn(
                        f'Abstract action at {func_path} has no name. '
                        f'Named abstract actions are strongly recommended for handler registration. '
                        f'Add a name like: {func.stage} abstract YourFunctionName',
                        UserWarning,
                        stacklevel=2
                    )
                    self._warned_anonymous_abstracts.add(anonymous_key)

                self.logger.info(f'Execute anonymous abstract function {func_path} (no handlers supported)')
                return

            # Named abstract - check for handlers
            handlers = self._abstract_handlers.get(func_path, [])

            # Validation mode: skip execution even if handlers exist
            if is_validation_mode:
                if handlers:
                    self.logger.info(f'[VALIDATION] Skip abstract function {func_path} '
                                     f'({len(handlers)} handler(s) registered but not executed in validation mode)')
                else:
                    self.logger.info(f'[VALIDATION] Skip abstract function {func_path} (no handlers registered)')
                return

            # Real execution mode: check if handlers are registered
            if not handlers:
                self.logger.info(f'[SIMULATION] Skip abstract function {func_path} (no handlers registered)')
                return

            # Has registered handlers - this is real execution mode
            self.logger.info(f'[EXECUTION] Execute abstract function {func_path} '
                             f'with {len(handlers)} handler(s)')

            # Create read-only context
            # func.parent is always set during state machine construction
            ctx = ReadOnlyExecutionContext(
                state_path=func.parent.path,
                vars=dict(vars_),  # Frozen copy
                action_name=func_path,
                action_stage=func.stage
            )

            # Execute all handlers in order
            for idx, handler in enumerate(handlers):
                try:
                    self.logger.debug(f'Executing handler {idx + 1}/{len(handlers)} for {func_path}')
                    handler(ctx)
                except Exception as e:
                    if self._abstract_error_mode == 'raise':
                        # Raise mode: set error state and re-raise
                        self._is_error_state = True
                        self._error_info = (func_path, e)
                        self.logger.error(f'Abstract handler {idx + 1} for {func_path} raised exception: {e}')
                        raise
                    else:
                        # Log mode: record error and continue
                        self._abstract_handler_errors.append((func_path, e))
                        self.logger.error(f'Abstract handler {idx + 1} for {func_path} raised exception '
                                          f'(continuing in log mode): {e}')
        else:
            self.logger.info(f'Execute function {func.func_name}.')
            for op in (func.operations or []):
                vars_[op.var_name] = op.expr(**vars_)

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
        return transition.event.path_name in d_events

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
        return self._transition_matches_event(transition, d_events) and self._transition_matches_guard(transition,
                                                                                                       vars_)

    def _run_leaf_during(
            self,
            state: State,
            vars_: Dict[str, Union[int, float]],
            is_validation_mode: bool = False
    ) -> None:
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
        :return: ``None``.
        :rtype: None
        """
        for _, func in state.iter_on_during_aspect_recursively():
            self._execute_func(func, vars_, is_validation_mode=is_validation_mode)

    def _enter_state(
            self,
            stack: List[_Frame],
            state: State,
            vars_: Dict[str, Union[int, float]],
            d_events: Dict[str, Event],
            is_validation_mode: bool = False
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
        :return: ``None``.
        :rtype: None
        """
        stack.append(_Frame(state, 'active'))
        for on_enter in state.on_enters:
            self._execute_func(on_enter, vars_, is_validation_mode=is_validation_mode)

        if state.is_leaf_state:
            self._run_leaf_during(state, vars_, is_validation_mode=is_validation_mode)
            stack[-1].mode = 'after_entry'
        else:
            for on_during_before in state.list_on_durings(aspect='before'):
                self._execute_func(on_during_before, vars_, is_validation_mode=is_validation_mode)
            stack[-1].mode = 'init_wait'
            self._attempt_init_transition(stack, vars_, d_events, is_validation_mode=is_validation_mode)

    def _attempt_init_transition(
            self,
            stack: List[_Frame],
            vars_: Dict[str, Union[int, float]],
            d_events: Dict[str, Event],
            is_validation_mode: bool = False
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
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
                self._enter_state(stack, target_state, vars_, d_events, is_validation_mode=is_validation_mode)
                return True
        return False

    def _finalize_exit_to_parent(
            self,
            stack: List[_Frame],
            vars_: Dict[str, Union[int, float]],
            is_validation_mode: bool = False
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
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
            self._execute_func(on_during_after, vars_, is_validation_mode=is_validation_mode)
        stack[-1].mode = 'post_child_exit'
        return False

    def _execute_transition_on_context(
            self,
            stack: List[_Frame],
            vars_: Dict[str, Union[int, float]],
            transition: Transition,
            d_events: Dict[str, Event],
            is_validation_mode: bool = False
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
        :return: ``True`` if executing the transition ends the runtime.
        :rtype: bool
        """
        current_state = stack[-1].state

        for on_exit in current_state.on_exits:
            self._execute_func(on_exit, vars_, is_validation_mode=is_validation_mode)

        self._execute_transition_effect(transition, vars_)
        stack.pop()

        if transition.to_state == EXIT_STATE:
            return self._finalize_exit_to_parent(stack, vars_, is_validation_mode=is_validation_mode)

        target_state = current_state.parent.substates[transition.to_state]
        self._enter_state(stack, target_state, vars_, d_events, is_validation_mode=is_validation_mode)
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

        During validation, abstract handlers are not executed to ensure that
        speculative execution does not trigger side effects.

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
        ended = self._execute_transition_on_context(sim_stack, sim_vars, transition, d_events, is_validation_mode=True)
        if ended:
            return True

        success, _ = self._run_cycle_on_context(
            sim_stack,
            sim_vars,
            d_events,
            ended=ended,
            validate_post_child_exit=False,
            is_validation_mode=True,
        )
        return success

    def _initialize_context(
            self,
            stack: List[_Frame],
            vars_: Dict[str, Union[int, float]],
            d_events: Dict[str, Event],
            is_validation_mode: bool = False
    ) -> bool:
        """
        Initialize an arbitrary execution context from the root state.

        This helper initializes a supplied execution context by entering the
        root state and building the initial active execution chain. Used for
        both normal runtime initialization and speculative validation.

        :param stack: Execution stack to reset and initialize.
        :type stack: List[_Frame]
        :param vars_: Variable mapping visible during initialization.
        :type vars_: Dict[str, Union[int, float]]
        :param d_events: Active events available during initial entry.
        :type d_events: Dict[str, Event]
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
        :return: ``True`` if initialization ends the runtime immediately.
        :rtype: bool
        """
        stack.clear()
        self._enter_state(stack, self.state_machine.root_state, vars_, d_events, is_validation_mode=is_validation_mode)
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

    def _run_cycle_on_context(
            self,
            stack: List[_Frame],
            vars_: Dict[str, Union[int, float]],
            d_events: Dict[str, Event],
            *,
            ended: bool = False,
            validate_post_child_exit: bool = True,
            is_validation_mode: bool = False
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
        :param is_validation_mode: Whether this is validation mode (handlers not executed).
        :type is_validation_mode: bool
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
                self.logger.warning('Pruned repeated speculative execution state during DFS validation.')
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
                self.logger.warning(
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
                    ended = self._execute_transition_on_context(stack, vars_, transition, d_events,
                                                                is_validation_mode=is_validation_mode)
                    steps_taken += 1
                    if ended:
                        return True, True
                    continue

                self._run_leaf_during(state, vars_, is_validation_mode=is_validation_mode)
                frame.mode = 'after_entry'
                steps_taken += 1
                continue

            if frame.mode == 'init_wait':
                progressed = self._attempt_init_transition(stack, vars_, d_events,
                                                           is_validation_mode=is_validation_mode)
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
                ended = self._execute_transition_on_context(stack, vars_, transition, d_events,
                                                            is_validation_mode=is_validation_mode)
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

        **Flexible Event Path Formats**:

        The runtime supports multiple event path formats for maximum convenience:

        - **Full paths**: ``"Root.System.Active.Start"`` - Complete path from root
        - **Relative paths**: ``"Start"`` - Resolved from current state
        - **Parent-relative**: ``".error"`` or ``"..system.error"`` - Navigate up hierarchy
        - **Absolute**: ``"/global.shutdown"`` - Resolved from root state

        The runtime intelligently determines which resolution method to use based
        on the path syntax and current runtime state. This allows you to use the
        most convenient format for your use case without worrying about the details.

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

        Example - Flexible event path formats::

            >>> dsl_code = '''
            ... state Root {
            ...     event global_stop;
            ...     state System {
            ...         event system_error;
            ...         state Idle {
            ...             event start;
            ...         }
            ...         state Active {
            ...             event pause;
            ...         }
            ...         [*] -> Idle;
            ...         Idle -> Active :: start;
            ...         Active -> Idle :: pause;
            ...     }
            ...     [*] -> System;
            ... }
            ... '''
            >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
            >>> sm = parse_dsl_node_to_state_machine(ast)
            >>> runtime = SimulationRuntime(sm)
            >>> runtime.cycle()
            >>> runtime.current_state.path
            ('Root', 'System', 'Idle')
            >>> # Use relative path from current state - most convenient!
            >>> runtime.cycle(['start'])
            >>> runtime.current_state.path
            ('Root', 'System', 'Active')
            >>> # Use parent-relative path to access parent's event
            >>> runtime.cycle(['.system_error'])  # Access System.system_error
            >>> # Use absolute path to access root event
            >>> runtime.cycle(['/global_stop'])  # Access Root.global_stop
            >>> # Full path still works for backward compatibility
            >>> runtime.cycle(['Root.System.Active.pause'])
            >>> runtime.current_state.path
            ('Root', 'System', 'Idle')

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
            self.logger.warning('Runtime already ended, cycle ignored.')
            return

        # Log cycle start
        event_names = [e.path_name if isinstance(e, Event) else e for e in (events or [])]
        self.logger.info(f'Cycle {self.cycle_count + 1} starting with events: {event_names if event_names else "none"}')

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
            self.cycle_count += 1  # Increment cycle count on successful cycle

            # Record history entry
            # Get current state path
            try:
                state_path = '.'.join(self.current_state.path) if self.current_state else "(terminated)"
            except (AttributeError, IndexError):
                state_path = "(terminated)"

            # Create history entry
            history_entry = {
                'cycle': self.cycle_count,
                'state': state_path,
                'vars': copy.deepcopy(self.vars),
                'events': event_names
            }

            # Add to history and maintain size limit
            self.history.append(history_entry)
            if self.history_size is not None and len(self.history) > self.history_size:
                self.history.pop(0)  # Remove oldest entry

            # Log successful cycle completion
            self.logger.info(
                f'Cycle {self.cycle_count} completed successfully - State: {state_path}, Vars: {self.vars}')
        else:
            self.vars = snapshot_vars
            self._ended = snapshot_ended
            if not snapshot_initialized and not snapshot_ended:
                self.stack = self._create_root_rollback_stack()
                self._initialized = True
            else:
                self.stack = snapshot_stack
                self._initialized = snapshot_initialized
            self.logger.warning(
                f'Cycle {self.cycle_count + 1} failed - Unable to reach a stoppable state, changes rolled back')

        if self._ended or not self.stack:
            self._ended = True
            self.stack = []
            self.logger.info(f'Runtime ended at cycle {self.cycle_count}')
        else:
            current_state_path = ".".join(self.current_state.path)
            self.logger.debug(f'Cycle {self.cycle_count} - Current state: {current_state_path}, Vars: {self.vars}')

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
            >>> runtime.current_state.name
            'System'
            >>> runtime.current_state.path
            ('System',)
            >>> runtime.cycle()
            >>> runtime.current_state.name
            'Idle'
            >>> runtime.cycle(['System.Idle.Start'])
            >>> runtime.current_state.name
            'Active'

        .. note::
           Before the first :meth:`cycle` call, this returns the root state.
           After the runtime has ended, accessing this property will raise
           an IndexError.
        """
        if not self.stack:
            if self._ended:
                raise IndexError(
                    "Cannot access current_state: runtime has ended."
                )
            else:
                raise IndexError(
                    "Cannot access current_state: runtime has not been initialized. "
                    "This should not happen - the stack should be initialized in __init__."
                )
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

    @property
    def is_error_state(self) -> bool:
        """
        Indicate whether the runtime is in an error state.

        When ``abstract_error_mode`` is ``'raise'`` and an abstract handler
        raises an exception, the runtime enters an error state. In this state,
        the runtime preserves the error information and prevents further execution.

        :return: ``True`` if runtime is in error state, ``False`` otherwise.
        :rtype: bool

        Example::

            >>> runtime = SimulationRuntime(sm, abstract_error_mode='raise')
            >>> runtime.is_error_state
            False
            >>> # After handler raises exception
            >>> runtime.is_error_state
            True
        """
        return self._is_error_state

    @property
    def error_info(self) -> Optional[Tuple[str, Exception]]:
        """
        Get error information if runtime is in error state.

        :return: Tuple of (action_path, exception) if in error state, ``None`` otherwise.
        :rtype: Optional[Tuple[str, Exception]]

        Example::

            >>> if runtime.is_error_state:
            ...     action_path, exception = runtime.error_info
            ...     print(f"Error in {action_path}: {exception}")
        """
        return self._error_info

    @property
    def abstract_handler_errors(self) -> List[Tuple[str, Exception]]:
        """
        Get list of abstract handler errors (only in 'log' mode).

        When ``abstract_error_mode`` is ``'log'``, exceptions from abstract
        handlers are logged and collected here instead of stopping execution.

        :return: List of (action_path, exception) tuples
        :rtype: List[Tuple[str, Exception]]

        Example::

            >>> runtime = SimulationRuntime(sm, abstract_error_mode='log')
            >>> runtime.cycle()
            >>> for action_path, exception in runtime.abstract_handler_errors:
            ...     print(f"Error in {action_path}: {exception}")
        """
        return list(self._abstract_handler_errors)

    def register_abstract_handler(
            self,
            action_path: str,
            handler: Callable[[ReadOnlyExecutionContext], None]
    ) -> None:
        """
        Register a Python function to handle an abstract action.

        Multiple handlers can be registered for the same abstract action.
        They will be executed in registration order.

        :param action_path: Full path to the abstract action (e.g., "System.Active.InitHardware")
        :type action_path: str
        :param handler: Python function that receives read-only context
        :type handler: Callable[[ReadOnlyExecutionContext], None]
        :raises ValueError: If action_path is empty or invalid

        Example::

            >>> def my_init(ctx: ReadOnlyExecutionContext):
            ...     print(f"Initializing in state {ctx.get_state_name()}")
            ...     print(f"Counter value: {ctx.get_var('counter')}")
            >>>
            >>> runtime.register_abstract_handler("System.Active.InitHardware", my_init)
            >>>
            >>> # Register another handler for the same action
            >>> def my_init2(ctx: ReadOnlyExecutionContext):
            ...     print(f"Second handler for {ctx.action_name}")
            >>>
            >>> runtime.register_abstract_handler("System.Active.InitHardware", my_init2)
        """
        if not action_path:
            raise ValueError("action_path cannot be empty")

        if action_path not in self._abstract_handlers:
            self._abstract_handlers[action_path] = []

        self._abstract_handlers[action_path].append(handler)
        self.logger.debug(f'Registered handler for abstract action {action_path} '
                          f'(total handlers: {len(self._abstract_handlers[action_path])})')

    def unregister_abstract_handler(
            self,
            action_path: str,
            handler: Optional[Callable[[ReadOnlyExecutionContext], None]] = None
    ) -> int:
        """
        Unregister abstract handler(s) for an action.

        If handler is ``None``, removes all handlers for the action.
        If handler is provided, removes only that specific handler.

        :param action_path: Full path to the abstract action
        :type action_path: str
        :param handler: Specific handler to remove, or ``None`` to remove all
        :type handler: Optional[Callable[[ReadOnlyExecutionContext], None]]
        :return: Number of handlers removed
        :rtype: int

        Example::

            >>> # Remove all handlers for an action
            >>> count = runtime.unregister_abstract_handler("System.Active.InitHardware")
            >>> print(f"Removed {count} handlers")
            >>>
            >>> # Remove specific handler
            >>> runtime.unregister_abstract_handler("System.Active.InitHardware", my_init)
        """
        if action_path not in self._abstract_handlers:
            return 0

        if handler is None:
            # Remove all handlers
            count = len(self._abstract_handlers[action_path])
            del self._abstract_handlers[action_path]
            self.logger.debug(f'Removed all {count} handlers for abstract action {action_path}')
            return count
        else:
            # Remove specific handler
            handlers = self._abstract_handlers[action_path]
            original_count = len(handlers)
            self._abstract_handlers[action_path] = [h for h in handlers if h is not handler]
            removed_count = original_count - len(self._abstract_handlers[action_path])

            # Clean up empty list
            if not self._abstract_handlers[action_path]:
                del self._abstract_handlers[action_path]

            if removed_count > 0:
                self.logger.debug(f'Removed {removed_count} handler(s) for abstract action {action_path}')

            return removed_count

    def clear_all_abstract_handlers(self) -> int:
        """
        Clear all registered abstract handlers.

        :return: Total number of handlers removed
        :rtype: int

        Example::

            >>> count = runtime.clear_all_abstract_handlers()
            >>> print(f"Cleared {count} handlers")
        """
        total_count = sum(len(handlers) for handlers in self._abstract_handlers.values())
        self._abstract_handlers.clear()
        self._warned_anonymous_abstracts.clear()
        self.logger.debug(f'Cleared all {total_count} abstract handlers')
        return total_count

    def get_abstract_handlers(self, action_path: str) -> List[Callable[[ReadOnlyExecutionContext], None]]:
        """
        Get all registered handlers for an abstract action.

        :param action_path: Full path to the abstract action
        :type action_path: str
        :return: List of registered handlers (may be empty)
        :rtype: List[Callable[[ReadOnlyExecutionContext], None]]

        Example::

            >>> handlers = runtime.get_abstract_handlers("System.Active.InitHardware")
            >>> print(f"Found {len(handlers)} handlers")
        """
        return list(self._abstract_handlers.get(action_path, []))

    def has_abstract_handlers(self, action_path: str) -> bool:
        """
        Check if any handlers are registered for an abstract action.

        :param action_path: Full path to the abstract action
        :type action_path: str
        :return: ``True`` if at least one handler is registered
        :rtype: bool

        Example::

            >>> if runtime.has_abstract_handlers("System.Active.InitHardware"):
            ...     print("Handlers registered")
        """
        return action_path in self._abstract_handlers and len(self._abstract_handlers[action_path]) > 0

    def register_handlers_from_object(self, obj: object) -> int:
        """
        Register all decorated methods from an object as abstract handlers.

        This method scans the object for methods decorated with
        :func:`~pyfcstm.simulate.decorators.abstract_handler` and automatically
        registers them with their specified action paths.

        This provides a convenient way to organize multiple related handlers
        in a single class, maintaining state and shared logic between handlers.

        :param obj: Object instance containing decorated handler methods
        :type obj: object
        :return: Number of handlers registered
        :rtype: int

        Example::

            >>> from pyfcstm.simulate import abstract_handler
            >>> class MyHandlers:
            ...     def __init__(self):
            ...         self.init_count = 0
            ...         self.monitor_count = 0
            ...
            ...     @abstract_handler('System.Active.Init')
            ...     def handle_init(self, ctx: ReadOnlyExecutionContext):
            ...         self.init_count += 1
            ...         print(f"Init called {self.init_count} times")
            ...
            ...     @abstract_handler('System.Active.Monitor')
            ...     def handle_monitor(self, ctx: ReadOnlyExecutionContext):
            ...         self.monitor_count += 1
            ...         counter = ctx.get_var('counter')
            ...         print(f"Monitor: counter={counter}, called {self.monitor_count} times")
            ...
            ...     def helper_method(self):
            ...         # Not decorated, won't be registered
            ...         pass
            >>>
            >>> handlers = MyHandlers()
            >>> count = runtime.register_handlers_from_object(handlers)
            >>> print(f"Registered {count} handlers")
            Registered 2 handlers

        .. note::
           Only methods decorated with :func:`~pyfcstm.simulate.decorators.abstract_handler`
           will be registered. Other methods are ignored.
        """
        from .decorators import get_handler_metadata

        registered_count = 0

        # Iterate through all attributes of the object
        for name in dir(obj):
            # Skip private/magic methods
            if name.startswith('_'):
                continue

            try:
                attr = getattr(obj, name)
            except AttributeError:
                continue

            # Check if it's a callable method
            if not callable(attr):
                continue

            # Check if it has handler metadata
            action_path = get_handler_metadata(attr)
            if action_path is None:
                continue

            # Register the bound method
            self.register_abstract_handler(action_path, attr)
            registered_count += 1
            self.logger.debug(f'Registered method {name} from {obj.__class__.__name__} '
                              f'for action {action_path}')

        self.logger.info(f'Registered {registered_count} handler(s) from {obj.__class__.__name__}')
        return registered_count
