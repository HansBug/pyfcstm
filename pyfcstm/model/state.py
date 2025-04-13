import io
import uuid
import weakref
from abc import ABCMeta
from typing import Optional, List, Dict, Generic, TypeVar, Union, Type

from hbutils.string import plural_word


class BaseElement:
    def __init__(self, id_: Optional[str] = None):
        self._id = id_ or str(uuid.uuid4())

    @property
    def id(self) -> str:
        return self._id

    def __str__(self):
        return self._repr(full_info=True)

    def __repr__(self):
        return self._repr(full_info=False)

    def _repr(self, full_info: bool = True):
        with io.StringIO() as sio:
            print(f'<{self.__class__.__name__}', file=sio, end='')
            if full_info:
                print(f' #{self._id}', file=sio, end='')
            param_dict = self._repr_dict() if not full_info else self._str_dict()
            for i, (key, value) in enumerate(param_dict.items()):
                print(f'{"," if i > 0 or full_info else ""} {key}={value!r}', file=sio, end='')
            print('>', file=sio, end='')
            return sio.getvalue()

    def _repr_dict(self):
        return {}

    def _str_dict(self):
        return self._repr_dict()


def _to_element_id(element: BaseElement):
    if isinstance(element, BaseElement):
        return element.id
    elif isinstance(element, str):
        return element
    else:
        raise TypeError(f'Unknown element type - {element!r}.')


class ChartElement(BaseElement):
    def __init__(self, chart: Optional['Statechart'], id_: Optional[str] = None):
        super().__init__(id_=id_)
        self._chart_ref = None
        self.chart = chart

    @property
    def chart(self) -> Optional['Statechart']:
        return self._chart_ref() if self._chart_ref is not None else None

    @chart.setter
    def chart(self, chart: Optional['Statechart']):
        self._chart_ref = weakref.ref(chart) if chart is not None else None

    @chart.deleter
    def chart(self):
        self._chart_ref = None


T = TypeVar('T', bound=ChartElement)


class ChartElements(Generic[T]):
    def __init__(self, mapping: Dict[str, T], chart: 'Statechart', element_type: Type[T]):
        self._mapping = mapping
        self._chart = chart
        self._element_type = element_type

    def __contains__(self, item: Union[str, T]):
        element_id = _to_element_id(item)
        return element_id in self._mapping

    def __delitem__(self, item: Union[str, T]):
        element_id = _to_element_id(item)
        del self._mapping[element_id]

    def add(self, item: T):
        if not isinstance(item, self._element_type):
            raise TypeError(f'Element type {self._element_type!r} expected but {item!r} found.')
        self._mapping[item.id] = item
        item.chart = self._chart
        self._after_add(item)

    def _after_add(self, item: T):
        pass

    def get(self, item: Union[str, T]) -> Optional[T]:
        element_id = _to_element_id(item)
        return self._mapping.get(element_id)

    def __getitem__(self, item: Union[str, T]) -> T:
        element_id = _to_element_id(item)
        return self._mapping[element_id]

    def __len__(self):
        return len(self._mapping)

    def __iter__(self):
        yield from self._mapping.values()

    def __repr__(self):
        return (f'<{self.__class__.__name__}[{self._element_type.__name__}] '
                f'{plural_word(len(self._mapping), "item")}>')

    def __str__(self):
        return f'{self._element_type.__name__}{list(self)!r}'


class Statechart(BaseElement):
    def __init__(self, name: str, root_state: 'CompositeState', preamble: Optional[List] = None,
                 states: Optional[List['State']] = None,
                 events: Optional[List['Event']] = None,
                 transitions: Optional[List['Transition']] = None,
                 id_: Optional[str] = None):
        super().__init__(id_=id_)
        self.name = name
        self.preamble = list(preamble or [])

        self._d_states: Dict[str, 'State'] = {}
        for state in (states or []):
            self.states.add(state)
        self._d_events: Dict[str, 'Event'] = {}
        for event in (events or []):
            self.events.add(event)
        self._d_transition: Dict[str, 'Transition'] = {}
        for transition in (transitions or []):
            self.transitions.add(transition)

        self._root_state_id = _to_element_id(root_state)
        if self._root_state_id not in self._d_states:
            self.states.add(root_state)
        _ = self.root_state

    @property
    def root_state_id(self) -> str:
        return self._root_state_id

    @property
    def root_state(self) -> 'CompositeState':
        state: Optional[CompositeState] = self.states.get(self._root_state_id)
        if state is None:
            raise ValueError(f'No root state found in {self!r}.')
        if not isinstance(state, CompositeState):
            raise ValueError(f'Root state not a composite state in {self!r} - {state!r}.')
        return state

    @property
    def states(self) -> ChartElements['State']:
        return ChartElements(self._d_states, chart=self, element_type=State)

    @property
    def transitions(self) -> ChartElements['Transition']:
        return ChartElements(self._d_transition, chart=self, element_type=Transition)

    @property
    def events(self) -> ChartElements['Event']:
        return ChartElements(self._d_events, chart=self, element_type=Event)

    def _repr_dict(self):
        return {
            'name': self.name,
            'root_state': self.root_state,
        }

    def _str_dict(self):
        return {
            'name': self.name,
            'root_state': self.root_state,
            'states': self.states,
            'transitions': self.transitions,
            'events': self.events,
        }


class State(ChartElement, metaclass=ABCMeta):
    def __init__(self, name: str, description: str = '',
                 min_time_lock: Optional[int] = None, max_time_lock: Optional[int] = None,
                 on_entry=None, on_during=None, on_exit=None,
                 chart: Optional['Statechart'] = None, id_: Optional[str] = None):
        super().__init__(chart=chart, id_=id_)
        self.name = name
        self.description = description
        self.min_time_lock = min_time_lock
        self.max_time_lock = max_time_lock
        self.on_entry = on_entry
        self.on_during = on_during
        self.on_exit = on_exit

    def list_states(self) -> List['State']:
        retval = [self]
        exist_ids = {self.id}
        for state in self._yield_child_states():
            if state.id not in exist_ids:
                exist_ids.add(state.id)
                retval.append(state)
        return retval

    def _yield_child_states(self):
        raise NotImplementedError

    def _repr_dict(self):
        d = {
            'name': self.name
        }
        if self.min_time_lock is not None:
            d['min_time_lock'] = self.min_time_lock
        if self.max_time_lock is not None:
            d['max_time_lock'] = self.max_time_lock
        if self.on_entry is not None:
            d['on_entry'] = self.on_entry
        if self.on_during is not None:
            d['on_during'] = self.on_during
        if self.on_entry is not None:
            d['on_exit'] = self.on_exit
        return d


class StateElements(ChartElements[State]):
    def _after_add(self, item: T):
        super()._after_add(item)
        if self._chart is not None:
            if item not in self._chart.states:
                self._chart.states.add(item)


class CompositeState(State):
    def __init__(self, name: str, initial_state: Union[str, State], description: str = '',
                 min_time_lock: Optional[int] = None, max_time_lock: Optional[int] = None,
                 on_entry=None, on_during=None, on_exit=None, states: Optional[List[Union[str, State]]] = None,
                 chart: Optional['Statechart'] = None, id_: Optional[str] = None):
        super().__init__(
            name=name,
            description=description,
            min_time_lock=min_time_lock,
            max_time_lock=max_time_lock,
            on_entry=on_entry,
            on_during=on_during,
            on_exit=on_exit,
            chart=chart,
            id_=id_
        )

        self._initial_state_id = _to_element_id(initial_state)
        self._d_states = {}
        for state in (states or []):
            self.states.add(state)

    @property
    def initial_state_id(self):
        return self._initial_state_id

    @property
    def initial_state(self) -> Optional[State]:
        if self.chart is not None:
            return self.chart.states.get(self._initial_state_id)
        else:
            return None

    @initial_state.setter
    def initial_state(self, state: State):
        if self.chart is not None and state not in self.chart.states:
            self.chart.states.add(state)
        state.chart = self.chart
        self._initial_state_id = state.id

    @property
    def states(self):
        return StateElements(self._d_states, chart=self.chart, element_type=State)

    def _yield_child_states(self):
        for state in self.states:
            state: State
            yield from state._yield_child_states()

    def _repr_dict(self):
        return super()._repr_dict()

    def _str_dict(self):
        return {
            **super()._str_dict(),
            'states': self.states,
        }


class NormalState(State):
    def _yield_child_states(self):
        yield from []


class PseudoState(State):
    def _yield_child_states(self):
        yield from []


class Transition(ChartElement):
    def __init__(self, src_state: Union[str, State], dst_state: Union[str, State], event: Union[str, 'Event'],
                 chart: Optional['Statechart'] = None, id_: Optional[str] = None):
        super().__init__(chart=chart, id_=id_)

        self._src_state_id = _to_element_id(src_state)
        self._dst_state_id = _to_element_id(dst_state)
        self._event_id = _to_element_id(event)

    @property
    def src_state_id(self):
        return self._src_state_id

    @property
    def src_state(self) -> Optional[State]:
        if self.chart is not None:
            return self.chart.states.get(self.src_state_id)
        else:
            return None

    @src_state.setter
    def src_state(self, state: State):
        if self.chart is not None and state not in self.chart.states:
            self.chart.states.add(state)
        state.chart = self.chart
        self._src_state_id = state.id

    @property
    def dst_state_id(self):
        return self._dst_state_id

    @property
    def dst_state(self) -> Optional[State]:
        if self.chart is not None:
            return self.chart.states.get(self._dst_state_id)
        else:
            return None

    @dst_state.setter
    def dst_state(self, state: State):
        if self.chart is not None and state not in self.chart.states:
            self.chart.states.get(state)
        state.chart = self.chart
        self._src_state_id = state.id

    @property
    def event_id(self):
        return self._event_id

    @property
    def event(self) -> 'Event':
        if self.chart is not None:
            return self.chart.events.get(self._event_id)
        else:
            return None

    @event.setter
    def event(self, event: 'Event'):
        if self.chart is not None and event not in self.chart.events:
            self.chart.events.add(event)
        event.chart = self.chart
        self._event_id = event.id

    def _repr_dict(self):
        return {
            'src_state': self.src_state if self.src_state else None,
            'dst_state': self.dst_state if self.dst_state else None,
            'event': self.event if self.event else None,
        }


class Event(ChartElement):
    def __init__(self, name: str, guard=None, chart: Optional['Statechart'] = None, id_: Optional[str] = None):
        super().__init__(chart=chart, id_=id_)
        self.name = name
        self.guard = guard

    def _repr_dict(self):
        return {
            'name': self.name,
        }

    def _str_dict(self):
        return {
            'name': self.name,
            'guard': self.guard,
        }
