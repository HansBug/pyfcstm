from dataclasses import dataclass
from typing import Optional, Union, List, Dict, Tuple

from .expr import Expr, parse_expr_node_to_expr
from ..dsl import node as dsl_node


@dataclass
class Operation:
    var_name: str
    expr: Expr


@dataclass
class Event:
    name: str
    state_path: Tuple[str, ...]

    @property
    def path(self) -> Tuple[str, ...]:
        return tuple((*self.state_path, self.name))


@dataclass
class Transition:
    src_state: Union[str, dsl_node._StateSingletonMark]
    dst_state: Union[str, dsl_node._StateSingletonMark]
    event: Optional[Event]
    guard: Optional[Expr]
    post_operations: List[Operation]


@dataclass
class State:
    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, Event]
    transitions: List[Transition]

    @property
    def is_leaf_state(self) -> bool:
        return len(self.substates) == 0


@dataclass
class VarDefine:
    name: str
    type: str
    init: Expr


@dataclass
class StateMachine:
    defines: Dict[str, VarDefine]
    root_state: State


def parse_dsl_node_to_state_machine(dnode: dsl_node.StateMachineDSLProgram) -> StateMachine:
    d_defines = {}
    for def_item in dnode.definitions:
        if def_item.name not in d_defines:
            d_defines[def_item.name] = VarDefine(
                name=def_item.name,
                type=def_item.type,
                init=parse_expr_node_to_expr(def_item.expr),
            )
        else:
            raise SyntaxError(f'Duplicated variable definition - {def_item}.')

    def _recursive_build_states(node: dsl_node.StateDefinition, current_path: Tuple[str, ...]):
        current_path = tuple((*current_path, node.name))
        d_substates = {}

        for subnode in node.substates:
            if subnode.name not in d_substates:
                d_substates[subnode.name] = _recursive_build_states(subnode, current_path=current_path)
            else:
                raise SyntaxError(f'Duplicate state name in namespace {".".join(current_path)!r}:\n{subnode}')

        d_events = {}
        transitions = []
        for transnode in node.transitions:
            if transnode.from_state is dsl_node.INIT_STATE:
                from_state = dsl_node.INIT_STATE
            else:
                from_state = transnode.from_state
                if from_state not in d_substates:
                    raise SyntaxError(f'Unknown from state {from_state!r} of transition:\n{transnode}')

            if transnode.to_state is dsl_node.EXIT_STATE:
                to_state = dsl_node.EXIT_STATE
            else:
                to_state = transnode.to_state
                if to_state not in d_substates:
                    raise SyntaxError(f'Unknown to state {to_state!r} to transition:\n{transnode}')

            trans_event, guard = None, None
            if transnode.event_id is not None:
                cur_substates, cur_events = d_substates, d_events
                for seg in transnode.event_id.path[:-1]:
                    cur_substates, cur_events = cur_substates[seg].substates, cur_substates[seg].events

                suffix_name = transnode.event_id.path[-1]
                if suffix_name not in cur_substates:
                    cur_events[suffix_name] = Event(
                        name=suffix_name,
                        state_path=tuple((*current_path, *transnode.event_id.path[:-1]))
                    )
                trans_event = cur_events[suffix_name]
            if transnode.condition_expr is not None:
                guard = parse_expr_node_to_expr(transnode.condition_expr)
                unknown_vars = []
                for var in guard.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if unknown_vars:
                    raise SyntaxError(f'Unknown guard variable {", ".join(unknown_vars)} in transition:\n{transnode}')

            post_operations = []
            for p_op in transnode.post_operations:
                post_operation_val = parse_expr_node_to_expr(p_op.expr)
                unknown_vars = []
                for var in post_operation_val.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if p_op.name not in d_defines and p_op.name not in unknown_vars:
                    unknown_vars.append(p_op.name)
                if unknown_vars:
                    raise SyntaxError(
                        f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{transnode}')
                post_operations.append(Operation(var_name=p_op.name, expr=post_operation_val))

            transition = Transition(
                src_state=from_state,
                dst_state=to_state,
                event=trans_event,
                guard=guard,
                post_operations=post_operations,
            )
            transitions.append(transition)

        return State(
            name=node.name,
            path=current_path,
            substates=d_substates,
            events=d_events,
            transitions=transitions,
        )

    root_state = _recursive_build_states(dnode.root_state, current_path=())
    return StateMachine(
        defines=d_defines,
        root_state=root_state,
    )
