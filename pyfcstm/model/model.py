import io
from dataclasses import dataclass
from textwrap import indent
from typing import Optional, Union, List, Dict, Tuple

from .base import AstExportable, PlantUMLExportable
from .expr import Expr, parse_expr_node_to_expr
from ..dsl import node as dsl_nodes


@dataclass
class Operation(AstExportable):
    var_name: str
    expr: Expr

    def to_ast_node(self) -> dsl_nodes.PostOperationalAssignment:
        return dsl_nodes.PostOperationalAssignment(
            name=self.var_name,
            expr=self.expr.to_ast_node(),
        )


@dataclass
class Event:
    name: str
    state_path: Tuple[str, ...]

    @property
    def path(self) -> Tuple[str, ...]:
        return tuple((*self.state_path, self.name))


@dataclass
class Transition:
    from_state: Union[str, dsl_nodes._StateSingletonMark]
    to_state: Union[str, dsl_nodes._StateSingletonMark]
    event: Optional[Event]
    guard: Optional[Expr]
    post_operations: List[Operation]


@dataclass
class State(AstExportable, PlantUMLExportable):
    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, Event]
    transitions: List[Transition]

    @property
    def is_leaf_state(self) -> bool:
        return len(self.substates) == 0

    @property
    def path_text(self):
        return '.'.join(self.path)

    def to_ast_node(self) -> dsl_nodes.StateDefinition:
        return dsl_nodes.StateDefinition(
            name=self.name,
            substates=[
                substate.to_ast_node()
                for _, substate in self.substates.items()
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=trans.from_state,
                    to_state=trans.to_state,
                    event_id=dsl_nodes.ChainID(
                        path=list(trans.event.path[len(self.path):])) if trans.event is not None else None,
                    condition_expr=trans.guard.to_ast_node() if trans.guard is not None else None,
                    post_operations=[
                        item.to_ast_node()
                        for item in trans.post_operations
                    ]
                ) for trans in self.transitions
            ]
        )

    def to_plantuml(self) -> str:
        with io.StringIO() as sf:
            if self.is_leaf_state:
                print(f'state {self.name}', file=sf, end='')
            else:
                print(f'state {self.name} {{', file=sf)
                for state in self.substates.values():
                    print(indent(state.to_plantuml(), prefix='    '), file=sf)
                for trans in self.transitions:
                    with io.StringIO() as tf:
                        print('[*]' if trans.from_state is dsl_nodes.INIT_STATE else trans.from_state, file=tf, end='')
                        print(' --> ', file=tf, end='')
                        print('[*]' if trans.to_state is dsl_nodes.EXIT_STATE else trans.to_state, file=tf, end='')

                        if trans.event is not None:
                            print(f' : {".".join(list(trans.event.path[len(self.path):]))}', file=tf, end='')
                        elif trans.guard is not None:
                            print(f' : {trans.guard.to_ast_node()}', file=tf, end='')

                        if len(trans.post_operations) > 0:
                            print('', file=tf)
                            print('note on link', file=tf)
                            print('post-operations {', file=tf)
                            for operation in trans.post_operations:
                                print(f'    {operation.to_ast_node()}', file=tf)
                            print('}', file=tf)
                            print('end note', file=tf, end='')

                        trans_text = tf.getvalue()
                    print(indent(trans_text, prefix='    '), file=sf)
                print(f'}}', file=sf, end='')

            return sf.getvalue()

    def walk_states(self):
        yield self
        for _, substate in self.substates.items():
            yield from substate.walk_states()


@dataclass
class VarDefine(AstExportable):
    name: str
    type: str
    init: Expr

    def to_ast_node(self) -> dsl_nodes.DefAssignment:
        return dsl_nodes.DefAssignment(
            name=self.name,
            type=self.type,
            expr=self.init.to_ast_node(),
        )


@dataclass
class StateMachine(AstExportable, PlantUMLExportable):
    defines: Dict[str, VarDefine]
    root_state: State

    def to_ast_node(self) -> dsl_nodes.StateMachineDSLProgram:
        return dsl_nodes.StateMachineDSLProgram(
            definitions=[
                def_item.to_ast_node()
                for _, def_item in self.defines.items()
            ],
            root_state=self.root_state.to_ast_node(),
        )

    def to_plantuml(self) -> str:
        with io.StringIO() as sf:
            print('@startuml', file=sf)
            if self.defines:
                print('note as DefinitionNote', file=sf)
                print('defines {', file=sf)
                for def_item in self.defines.values():
                    print(f'    {def_item.to_ast_node()}', file=sf)
                print('}', file=sf)
                print('end note', file=sf)
                print('', file=sf)
            print(self.root_state.to_plantuml(), file=sf)
            print(f'[*] --> {self.root_state.name}', file=sf)
            print(f'{self.root_state.name} --> [*]', file=sf)
            print('@enduml', file=sf, end='')
            return sf.getvalue()

    def walk_states(self):
        yield from self.root_state.walk_states()


def parse_dsl_node_to_state_machine(dnode: dsl_nodes.StateMachineDSLProgram) -> StateMachine:
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

    def _recursive_build_states(node: dsl_nodes.StateDefinition, current_path: Tuple[str, ...]):
        current_path = tuple((*current_path, node.name))
        d_substates = {}

        for subnode in node.substates:
            if subnode.name not in d_substates:
                d_substates[subnode.name] = _recursive_build_states(subnode, current_path=current_path)
            else:
                raise SyntaxError(f'Duplicate state name in namespace {".".join(current_path)!r}:\n{subnode}')

        d_events = {}
        transitions = []
        has_entry_trans = False
        for transnode in node.transitions:
            if transnode.from_state is dsl_nodes.INIT_STATE:
                from_state = dsl_nodes.INIT_STATE
                has_entry_trans = True
            else:
                from_state = transnode.from_state
                if from_state not in d_substates:
                    raise SyntaxError(f'Unknown from state {from_state!r} of transition:\n{transnode}')

            if transnode.to_state is dsl_nodes.EXIT_STATE:
                to_state = dsl_nodes.EXIT_STATE
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
                from_state=from_state,
                to_state=to_state,
                event=trans_event,
                guard=guard,
                post_operations=post_operations,
            )
            transitions.append(transition)

        if d_substates and not has_entry_trans:
            raise SyntaxError(f'At least 1 entry transition should be assigned in non-leaf states:\n{node}')

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
