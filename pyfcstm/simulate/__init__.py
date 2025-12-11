import logging
from typing import Union, List, Dict

from ..dsl import EXIT_STATE
from ..model import StateMachine, Event, Transition, OnStage, OnAspect


def _get_event_name(event: Event):
    return '.'.join(event.path)


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
                logging.info(f'Transition {transition!r} triggered due to event {_get_event_name(transition.event)!r}.')
                return True
            else:
                logging.debug(f'Transition {transition!r} not triggered.')
                return False
        else:
            if transition.guard is None or transition.guard(**self.vars):
                logging.info(f'Transition {transition!r} triggered due to guard {transition.guard!r}.')
                return True
            else:
                logging.debug(f'Transition {transition!r} not triggered.')
                return False

    def execute_transition_effect(self, transition: Transition):
        for effect in (transition.effects or []):
            self.vars[effect.var_name] = effect.expr(**self.vars)

    def execute_func(self, func: Union[OnStage, OnAspect]):
        while func.ref is not None:
            new_func = func.ref
            logging.debug(f'Function {".".join([*func.state_path, func.name])}'
                          f' -> {".".join([*new_func.state_path, new_func.name])}.')
            func = new_func
        if func.is_abstract:
            logging.info(
                f'Execute abstract function {".".join([*func.state_path, func.name])}:\n{func.to_ast_node()}')
        else:
            logging.info(f'Execute function {".".join([*func.state_path, func.name])}.')
            for op in (func.operations or []):
                self.vars[op.var_name] = op.expr(**self.vars)

    def step(self, events: List[Union[str, Event]] = None):
        events = list(events or [])
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

        elif current_status == 'exit':
            pass

        if current_status == 'enter':
            if current_state.is_leaf_state:
                pass

            else:
                for transition in current_state.init_transitions:
                    if self.is_transition_triggered(transition, d_events):
                        self.execute_transition_effect(transition)
                        self.stack.append((current_state.substates[transition.to_state], 'enter'))
                        break

        elif current_status == 'exit':
            for transition in current_state.transitions_from:
                if self.is_transition_triggered(transition, d_events):
                    self.execute_transition_effect(transition)
                    if transition.to_state == EXIT_STATE:
                        self.stack.pop()
                        self.stack[-1] = (self.stack[-1][0], 'exit')
                    else:
                        self.stack[-1] = (current_state.substates[transition.to_state], 'enter')
