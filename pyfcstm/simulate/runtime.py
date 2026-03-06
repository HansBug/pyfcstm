"""
Simulation runtime for executing finite state machine models.

This module provides the core :class:`SimulationRuntime` class for simulating
hierarchical state machine execution.
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
    """Internal runtime frame for an active state."""

    state: State
    mode: str


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
    :ivar stack: Execution stack of active states from root to current state
    :vartype stack: List[_Frame]
    :ivar vars: Current variable values
    :vartype vars: Dict[str, Union[int, float]]
    """

    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.stack: List[_Frame] = []
        self.vars: Dict[str, Union[int, float]] = {}
        for name, define in self.state_machine.defines.items():
            self.vars[name] = define.init(**self.vars)

        self._initialized = False
        self._ended = False

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
        return [_Frame(frame.state, frame.mode) for frame in stack]

    def _normalize_events(self, events: Optional[List[Union[str, Event]]]) -> Tuple[List[Event], Dict[str, Event]]:
        event_objects = [self.parse_event(event) for event in list(events or [])]
        d_events = {get_event_name(event): event for event in event_objects}
        return event_objects, d_events

    def _execute_transition_effect(self, transition: Transition, vars_: Dict[str, Union[int, float]]) -> None:
        for effect in (transition.effects or []):
            vars_[effect.var_name] = effect.expr(**vars_)

    def execute_transition_effect(self, transition: Transition):
        """
        Execute the effects of a transition.

        :param transition: The transition whose effects to execute
        :type transition: Transition
        """
        self._execute_transition_effect(transition, self.vars)

    def _execute_func(self, func: Union[OnStage, OnAspect], vars_: Dict[str, Union[int, float]]) -> None:
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
        Execute a lifecycle action, following references and handling abstracts.

        :param func: The action to execute
        :type func: Union[OnStage, OnAspect]
        """
        self._execute_func(func, self.vars)

    def _transition_matches_event(self, transition: Transition, d_events: Dict[str, Event]) -> bool:
        if transition.event is None:
            return True
        return get_event_name(transition.event) in d_events

    def _transition_matches_guard(self, transition: Transition, vars_: Dict[str, Union[int, float]]) -> bool:
        if transition.guard is None:
            return True
        return bool(transition.guard(**vars_))

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
        return self._transition_matches_event(transition, d_events) and self._transition_matches_guard(transition, vars_)

    def _run_leaf_during(self, state: State, vars_: Dict[str, Union[int, float]]) -> None:
        for _, func in state.iter_on_during_aspect_recursively():
            self._execute_func(func, vars_)

    def _enter_state(
        self,
        stack: List[_Frame],
        state: State,
        vars_: Dict[str, Union[int, float]],
        d_events: Dict[str, Event],
    ) -> None:
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
        self.stack = []
        self._enter_state(self.stack, self.state_machine.root_state, self.vars, d_events)
        self._initialized = True
        self._ended = len(self.stack) == 0

    def step(self, events: List[Union[str, Event]] = None):
        """
        Execute one simulation step.

        :param events: List of events to process in this step
        :type events: List[Union[str, Event]], optional
        """
        _, d_events = self._normalize_events(events)
        if self._ended:
            logging.info('Runtime ended, nothing to do.')
            return
        if not self._initialized:
            self._initialize_runtime(d_events)
            return

        if not self.stack:
            self._ended = True
            return

        frame = self.stack[-1]
        state = frame.state

        if state.is_leaf_state:
            transition = self._select_transition(self.stack, self.vars, d_events)
            if transition is not None:
                self._ended = self._execute_transition_on_context(self.stack, self.vars, transition, d_events)
            else:
                self._run_leaf_during(state, self.vars)
                frame.mode = 'after_entry'
            return

        if frame.mode == 'init_wait':
            self._attempt_init_transition(self.stack, self.vars, d_events)
            self._ended = len(self.stack) == 0
            return

        if frame.mode == 'post_child_exit':
            transition = self._select_transition(self.stack, self.vars, d_events)
            if transition is not None:
                self._ended = self._execute_transition_on_context(self.stack, self.vars, transition, d_events)
            return

    def cycle(self, events: List[Union[str, Event]] = None):
        """
        Execute a complete simulation cycle until reaching a stable state.

        :param events: List of events to process
        :type events: List[Union[str, Event]], optional
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
        Get the current active state.

        :return: The current state
        :rtype: State
        """
        return self.stack[-1].state

    @property
    def brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        Get a brief representation of the execution stack.

        :return: List of (state_path, status) tuples
        :rtype: List[Tuple[Tuple[str, ...], str]]
        """
        return [(frame.state.path, frame.mode) for frame in self.stack]

    @property
    def is_ended(self) -> bool:
        """
        Check if the state machine execution has ended.

        :return: True if execution has ended
        :rtype: bool
        """
        return self._ended
