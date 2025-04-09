import copy
from enum import Enum
from pprint import pformat

from ..utils import IJsonOp


class Event(IJsonOp):
    def __init__(self, name: str, guard):
        self.name = name
        self.guard = guard

    def _to_json(self):
        return {
            'name': self.name,
            'guard': self.guard,
        }

    @classmethod
    def _from_json(cls, data):
        v: dict = copy.deepcopy(data)
        name = v.pop('name')
        guard = v.pop('guard')
        if v:
            raise ValueError(f'Unexpected fields {sorted(v.keys())!r} found in event data:\n'
                             f'{pformat(data)}')

        return cls(name, guard)


class StateType(Enum, IJsonOp):
    COMPOSITE = 'composite'
    NORMAL = 'normal'
    PSEUDA = 'pseuda'

    def _to_json(self):
        return self.value

    @classmethod
    def _from_json(cls, data):
        return {value: key for key, value in cls.__members__.items()}[data]


class State:
    pass
