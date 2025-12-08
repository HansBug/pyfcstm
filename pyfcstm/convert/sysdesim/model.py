from dataclasses import dataclass
from typing import List, Dict, Union, Optional


@dataclass
class XMIObject:
    id: str
    type: str
    name: str


@dataclass
class Signal(XMIObject):
    pass


@dataclass
class SignalEvent(XMIObject):
    signal: str
    signal_object: Optional['Signal'] = None


@dataclass
class TimeEvent(XMIObject):
    is_relative: bool
    expression: str


@dataclass
class Clazz(XMIObject):
    classifier_behavior: str
    state_machine: 'StateMachine'


@dataclass
class StateMachine(XMIObject):
    regions: List['Region']


@dataclass
class Region(XMIObject):
    transitions: List['Transition']
    states: List['State']


@dataclass
class Transition(XMIObject):
    source: str
    target: str


@dataclass
class State(XMIObject):
    regions: List['Region']

    def is_pseudo(self) -> bool:
        return self.type == 'uml:Pseudostate'


@dataclass
class Model:
    clazz: 'Clazz'
    events: Dict[str, Union[TimeEvent, SignalEvent]]
