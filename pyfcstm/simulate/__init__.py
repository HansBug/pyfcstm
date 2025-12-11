import logging
from typing import Union, List, Dict

from ..dsl import EXIT_STATE
from ..model import StateMachine, Event, Transition, OnStage, OnAspect, State


def _get_event_name(event: Event):
    return '.'.join(event.path)


def _get_func_name(func: Union[OnStage, OnAspect]):
    sp = func.state_path
    if sp[-1] is None:
        sp = tuple((*sp[:-1], '<unnamed>'))
    return '.'.join(sp)


class SimulationRuntime:
    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.stack = [
            (self.state_machine.root_state, 'enter'),
        ]

        self.vars = {}
        for name, define in self.state_machine.defines.items():
            self.vars[name] = define.init(**self.vars)

        self._next_state = None

    def parse_event(self, event: Union[str, Event]) -> Event:
        if isinstance(event, Event):
            return event
        elif isinstance(event, str):
            state = self.state_machine.root_state
            for segment in event.split('.')[:-1]:
                state = state.substates[segment]
            return state.events[event.split('.')[-1]]
        else:
            raise TypeError(f'Unknown event type {type(event)!r} - {event!r}.')

    def is_transition_triggered(self, transition: Transition, d_events: Dict[str, Event]) -> bool:
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
        for effect in (transition.effects or []):
            self.vars[effect.var_name] = effect.expr(**self.vars)

    def execute_func(self, func: Union[OnStage, OnAspect]):
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

    def step(self, events: List[Union[str, Event]] = None):
        events = [self.parse_event(event) for event in list(events or [])]
        d_events = {_get_event_name(event): event for event in events}
        current_state, current_status = self.stack[-1]
        if current_status == 'enter':
            for on_enter in current_state.on_enters:
                self.execute_func(on_enter)
            if current_state.is_leaf_state:
                self.stack[-1] = (current_state, 'during')
            else:
                self.stack[-1] = (current_state, 'during_before')

        elif current_status == 'during_before':
            for on_during_before in current_state.list_on_durings(aspect='before'):
                self.execute_func(on_during_before)
            self.stack[-1] = (current_state, 'during_after')
            for transition in current_state.init_transitions:
                if self.is_transition_triggered(transition, d_events):
                    self.execute_transition_effect(transition)
                    self.stack.append((current_state.substates[transition.to_state], 'enter'))
                    break

        elif current_status == 'during_after':
            self._next_state = None
            for transition in current_state.transitions_from:
                if self.is_transition_triggered(transition, d_events):
                    self.execute_transition_effect(transition)
                    self._next_state = transition.to_state
                    break
            for on_during_before in current_state.list_on_durings(aspect='after'):
                self.execute_func(on_during_before)
            if self._next_state is None:
                self.stack[-1] = (current_state, 'during_before')
            else:
                self.stack[-1] = (current_state, 'exit')

        elif current_status == 'during':
            for _, on_during in current_state.list_on_during_aspect_recursively():
                self.execute_func(on_during)
            self._next_state = None
            for transition in current_state.transitions_from:
                if self.is_transition_triggered(transition, d_events):
                    self.execute_transition_effect(transition)
                    self._next_state = transition.to_state
                    break
            if self._next_state is not None:
                self.stack[-1] = (current_state, 'exit')

        elif current_status == 'exit':
            if self._next_state == EXIT_STATE:
                self.stack.pop()
                if not self.is_ended:
                    logging.info(f'State quit {".".join(current_state.path)} --> {".".join(self.current_state.path)}')
            else:
                self.stack[-1] = (current_state.parent.substates[self._next_state], 'enter')
                logging.info(f'State transited {".".join(current_state.path)} --> {".".join(self.current_state.path)}')

        else:
            assert False, f'Unknown current status {current_status!r} on state {current_state!r}.'

    def cycle(self, events: List[Union[str, Event]] = None):
        events = [self.parse_event(event) for event in list(events or [])]
        if self.is_ended:
            logging.info(f'Runtime ended, nothing to do.')
        else:
            self.step(events)
            while not self.is_ended and not (
                    self.stack[-1][0].is_stoppable and self.stack[-1][1] in {'during', 'during_before'}):
                self.step(events)
            if self.is_ended:
                logging.info(f'Runtime ended.')
            else:
                logging.info(f'Current state: {".".join(self.current_state.path)}')
            logging.info(f'Current vars: {self.vars!r}')

    @property
    def current_state(self) -> State:
        return self.stack[-1][0]

    @property
    def brief_stack(self):
        return [(state.path, status) for state, status in self.stack]

    @property
    def is_ended(self):
        return len(self.stack) == 0
