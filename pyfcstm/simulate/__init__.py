"""
Simulation runtime for executing finite state machine models.

This module provides a runtime environment for simulating the execution of
hierarchical state machines defined using the pyfcstm DSL. It handles state
transitions, lifecycle actions, aspect-oriented programming, and variable
operations.

The main public components are:

* :class:`SimulationRuntime` - Runtime environment for executing state machines

.. note::
   The simulation runtime follows the exact execution semantics defined in
   CLAUDE.md, including proper handling of aspect actions, composite state
   during before/after timing, and pseudo states.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state Root {
    ...     state A;
    ...     state B;
    ...     [*] -> A;
    ...     A -> B :: Go;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry('state_machine_dsl', dsl_code)
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()  # Enter initial state
    >>> runtime.cycle(['Root.A.Go'])  # Trigger transition
"""

import logging
from typing import Union, List, Dict, Optional, Tuple

from ..dsl import EXIT_STATE
from ..model import StateMachine, Event, Transition, OnStage, OnAspect, State


def _get_event_name(event: Event) -> str:
    """
    Get the full path name of an event.

    :param event: The event object
    :type event: Event
    :return: Dot-separated event path
    :rtype: str
    """
    return '.'.join(event.path)


def _get_func_name(func: Union[OnStage, OnAspect]) -> str:
    """
    Get the full path name of a lifecycle action.

    :param func: The action object
    :type func: Union[OnStage, OnAspect]
    :return: Dot-separated action path
    :rtype: str
    """
    sp = func.state_path
    if sp[-1] is None:
        sp = tuple((*sp[:-1], '<unnamed>'))
    return '.'.join(sp)


class SimulationRuntime:
    """
    Runtime environment for simulating state machine execution.

    This class manages the execution of a hierarchical state machine, including:
    - State transitions with guards and effects
    - Lifecycle actions (enter/during/exit)
    - Aspect-oriented during actions
    - Variable operations
    - Event triggering

    :param state_machine: The state machine model to simulate
    :type state_machine: StateMachine

    :ivar state_machine: The state machine being simulated
    :vartype state_machine: StateMachine
    :ivar stack: Execution stack of (state, status) tuples
    :vartype stack: List[Tuple[State, str]]
    :ivar vars: Current variable values
    :vartype vars: Dict[str, Union[int, float]]

    Example::

        >>> from pyfcstm.model import StateMachine
        >>> runtime = SimulationRuntime(StateMachine(...))
        >>> runtime.cycle()  # Execute one cycle
        >>> runtime.vars['counter']  # Access variable values
        0
    """

    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.stack: List[Tuple[State, str]] = [
            (self.state_machine.root_state, 'enter'),
        ]

        self.vars: Dict[str, Union[int, float]] = {}
        for name, define in self.state_machine.defines.items():
            self.vars[name] = define.init(**self.vars)

        self._next_state: Optional[str] = None
        self._transition_target_state: Optional[State] = None

    def parse_event(self, event: Union[str, Event]) -> Event:
        """
        Parse an event from string or Event object.

        :param event: Event name (dot-separated path) or Event object
        :type event: Union[str, Event]
        :return: The Event object
        :rtype: Event
        :raises TypeError: If event type is not supported
        """
        if isinstance(event, Event):
            return event
        elif isinstance(event, str):
            # Event path format: "Root.State.EventName"
            # Navigate to the state that owns the event
            segments = event.split('.')
            state = self.state_machine.root_state

            # Navigate through states (all segments except last which is event name)
            # Skip first segment if it matches root state name
            start_idx = 1 if segments[0] == state.name else 0
            for segment in segments[start_idx:-1]:
                state = state.substates[segment]

            # Get the event from the state
            event_name = segments[-1]
            return state.events[event_name]
        else:
            raise TypeError(f'Unknown event type {type(event)!r} - {event!r}.')

    def is_transition_triggered(self, transition: Transition, d_events: Dict[str, Event]) -> bool:
        """
        Check if a transition should be triggered.

        :param transition: The transition to check
        :type transition: Transition
        :param d_events: Dictionary of active events by name
        :type d_events: Dict[str, Event]
        :return: True if transition should trigger
        :rtype: bool
        """
        if transition.event is not None:
            if _get_event_name(transition.event) in d_events:
                logging.info(
                    f'Transition {transition.to_ast_node()} triggered due to event {_get_event_name(transition.event)!r}.')
                return True
            else:
                logging.debug(f'Transition {transition.to_ast_node()} not triggered.')
                return False
        else:
            if transition.guard is None or transition.guard(**self.vars):
                logging.info(f'Transition {transition.to_ast_node()} triggered due to guard.')
                return True
            else:
                logging.debug(f'Transition {transition.to_ast_node()} not triggered.')
                return False

    def execute_transition_effect(self, transition: Transition):
        """
        Execute the effects of a transition.

        :param transition: The transition whose effects to execute
        :type transition: Transition
        """
        for effect in (transition.effects or []):
            self.vars[effect.var_name] = effect.expr(**self.vars)

    def execute_func(self, func: Union[OnStage, OnAspect]):
        """
        Execute a lifecycle action, following references and handling abstracts.

        :param func: The action to execute
        :type func: Union[OnStage, OnAspect]
        """
        # Follow reference chain
        while func.ref is not None:
            new_func = func.ref
            logging.debug(f'Function {_get_func_name(func)}'
                          f' -> {_get_func_name(new_func)}.')
            func = new_func

        if func.is_abstract:
            logging.info(
                f'Execute abstract function {_get_func_name(func)}:\n{func.to_ast_node()}')
        else:
            logging.info(f'Execute function {_get_func_name(func)}.')
            for op in (func.operations or []):
                self.vars[op.var_name] = op.expr(**self.vars)

    def _check_and_handle_parent_transition(self, parent_state: State, d_events: Dict[str, Event]) -> bool:
        """
        Check if parent has transitions and handle them.

        :param parent_state: The parent state to check
        :type parent_state: State
        :param d_events: Dictionary of active events
        :type d_events: Dict[str, Event]
        :return: True if transition was triggered
        :rtype: bool
        """
        self._next_state = None
        self._transition_target_state = None

        for transition in parent_state.transitions_from:
            if self.is_transition_triggered(transition, d_events):
                self.execute_transition_effect(transition)
                self._next_state = transition.to_state

                if self._next_state == EXIT_STATE:
                    self._transition_target_state = None
                else:
                    self._transition_target_state = parent_state.parent.substates[self._next_state]
                return True
        return False

    def step(self, events: List[Union[str, Event]] = None):
        """
        Execute one simulation step.

        :param events: List of events to process in this step
        :type events: List[Union[str, Event]], optional
        """
        events = [self.parse_event(event) for event in list(events or [])]
        d_events = {_get_event_name(event): event for event in events}
        current_state, current_status = self.stack[-1]

        if current_status == 'enter':
            # Execute enter actions
            for on_enter in current_state.on_enters:
                self.execute_func(on_enter)

            if current_state.is_leaf_state:
                # Leaf state: go to during phase
                self.stack[-1] = (current_state, 'during')
            else:
                # Composite state: execute during before and process init transition
                self.stack[-1] = (current_state, 'during_before')

        elif current_status == 'during_before':
            # Execute composite state's during before actions
            for on_during_before in current_state.list_on_durings(aspect='before'):
                self.execute_func(on_during_before)

            # Process initial transition
            for transition in current_state.init_transitions:
                if self.is_transition_triggered(transition, d_events):
                    self.execute_transition_effect(transition)
                    target_state = current_state.substates[transition.to_state]
                    # Replace current state with child state
                    self.stack[-1] = (current_state, 'during_after')
                    self.stack.append((target_state, 'enter'))
                    break
            else:
                # No init transition found - this shouldn't happen in valid FSM
                self.stack[-1] = (current_state, 'during_after')

        elif current_status == 'during_after':
            # Check for transitions from composite state
            if self._check_and_handle_parent_transition(current_state, d_events):
                # Transition triggered: execute during after and exit
                for on_during_after in current_state.list_on_durings(aspect='after'):
                    self.execute_func(on_during_after)
                self.stack[-1] = (current_state, 'exit')
            else:
                # No transition: stay in during_after (waiting for child)
                pass

        elif current_status == 'during':
            # Execute aspect actions for leaf state
            for _, on_during in current_state.iter_on_during_aspect_recursively():
                self.execute_func(on_during)

            # Check for transitions
            if self._check_and_handle_parent_transition(current_state, d_events):
                self.stack[-1] = (current_state, 'exit')

        elif current_status == 'exit':
            # Execute exit actions
            for on_exit in current_state.on_exits:
                self.execute_func(on_exit)

            if self._next_state == EXIT_STATE:
                # Exit to parent
                self.stack.pop()
                if not self.is_ended:
                    parent_state = self.stack[-1][0]
                    logging.info(f'State exited {".".join(current_state.path)} --> {".".join(parent_state.path)}')

                    # Parent composite state needs to execute during after
                    if self.stack[-1][1] == 'during_after':
                        # Execute during after actions
                        for on_during_after in parent_state.list_on_durings(aspect='after'):
                            self.execute_func(on_during_after)

                        # Check if parent has transitions
                        if self._check_and_handle_parent_transition(parent_state, d_events):
                            # Parent transitions
                            self.stack[-1] = (parent_state, 'exit')
                        else:
                            # Parent stays, go back to during_before
                            self.stack[-1] = (parent_state, 'during_before')
            else:
                # Transition to sibling or other state
                self.stack[-1] = (self._transition_target_state, 'enter')
                logging.info(f'State transited {".".join(current_state.path)} --> {".".join(self._transition_target_state.path)}')

        else:
            raise RuntimeError(f'Unknown current status {current_status!r} on state {current_state!r}.')

    def cycle(self, events: List[Union[str, Event]] = None):
        """
        Execute a complete simulation cycle until reaching a stable state.

        A cycle continues stepping until either:
        - The state machine ends
        - A stoppable leaf state is reached and has executed its during action

        :param events: List of events to process
        :type events: List[Union[str, Event]], optional
        """
        events = [self.parse_event(event) for event in list(events or [])]
        if self.is_ended:
            logging.info('Runtime ended, nothing to do.')
        else:
            # Track if we've executed a during action in a stoppable state
            executed_during_in_stoppable = False

            while not self.is_ended:
                current_state, current_status = self.stack[-1]

                # Check if we should stop BEFORE this step
                if executed_during_in_stoppable and current_state.is_stoppable and current_status == 'during':
                    break

                # Remember if we're about to execute during in a stoppable state
                if current_state.is_stoppable and current_status == 'during':
                    executed_during_in_stoppable = True

                self.step(events)

            if self.is_ended:
                logging.info('Runtime ended.')
            else:
                logging.info(f'Current state: {".".join(self.current_state.path)}')
            logging.info(f'Current vars: {self.vars!r}')

    @property
    def current_state(self) -> State:
        """
        Get the current active state.

        :return: The current state
        :rtype: State
        """
        return self.stack[-1][0]

    @property
    def brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        Get a brief representation of the execution stack.

        :return: List of (state_path, status) tuples
        :rtype: List[Tuple[Tuple[str, ...], str]]
        """
        return [(state.path, status) for state, status in self.stack]

    @property
    def is_ended(self) -> bool:
        """
        Check if the state machine execution has ended.

        :return: True if execution has ended
        :rtype: bool
        """
        return len(self.stack) == 0
