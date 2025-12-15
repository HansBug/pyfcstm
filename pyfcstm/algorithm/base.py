from typing import List

from ..model import State


def list_non_leaf_substates(state: State) -> List[str]:
    substate_names = []
    for _, substate in state.substates.items():
        if not is_leaf_state(state):
            substate_names.append(substate.name)
    return substate_names


def is_flatted_state(state: State) -> bool:
    return list_non_leaf_substates(state) == []


def is_leaf_state(state: State) -> bool:
    return len(state.substates) == 0
