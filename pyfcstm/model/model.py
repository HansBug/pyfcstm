import io
import json
import weakref
from dataclasses import dataclass
from textwrap import indent
from typing import Optional, Union, List, Dict, Tuple

from .base import AstExportable, PlantUMLExportable
from .expr import Expr, parse_expr_node_to_expr
from ..dsl import node as dsl_nodes, INIT_STATE, EXIT_STATE

__all__ = [
    'Operation',
    'Event',
    'Transition',
    'OnStage',
    'State',
    'VarDefine',
    'StateMachine',
    'parse_dsl_node_to_state_machine',
]


@dataclass
class Operation(AstExportable):
    var_name: str
    expr: Expr

    def to_ast_node(self) -> dsl_nodes.OperationAssignment:
        return dsl_nodes.OperationAssignment(
            name=self.var_name,
            expr=self.expr.to_ast_node(),
        )

    def var_name_to_ast_node(self) -> dsl_nodes.Name:
        return dsl_nodes.Name(name=self.var_name)


@dataclass
class Event:
    name: str
    state_path: Tuple[str, ...]

    @property
    def path(self) -> Tuple[str, ...]:
        return tuple((*self.state_path, self.name))


@dataclass
class Transition(AstExportable):
    from_state: Union[str, dsl_nodes._StateSingletonMark]
    to_state: Union[str, dsl_nodes._StateSingletonMark]
    event: Optional[Event]
    guard: Optional[Expr]
    effects: List[Operation]
    parent_ref: Optional[weakref.ReferenceType] = None

    @property
    def parent(self) -> Optional['State']:
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']):
        if new_parent is None:
            self.parent_ref = None
        else:
            self.parent_ref = weakref.ref(new_parent)

    def to_ast_node(self) -> dsl_nodes.ASTNode:
        return self.parent.to_transition_ast_node(self)


@dataclass
class OnStage(AstExportable):
    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[Operation]

    @property
    def is_abstract(self) -> bool:
        return self.name is not None or self.doc is not None

    def to_ast_node(self) -> Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]:
        if self.stage == 'enter':
            if self.name or self.doc is not None:
                return dsl_nodes.EnterAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            else:
                return dsl_nodes.EnterOperations(
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'during':
            if self.name or self.doc is not None:
                return dsl_nodes.DuringAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            else:
                return dsl_nodes.DuringOperations(
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'exit':
            if self.name or self.doc is not None:
                return dsl_nodes.ExitAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            else:
                return dsl_nodes.ExitOperations(
                    operations=[item.to_ast_node() for item in self.operations],
                )
        else:
            raise ValueError(f'Unknown stage - {self.stage!r}.')  # pragma: no cover


@dataclass
class State(AstExportable, PlantUMLExportable):
    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, Event]
    transitions: List[Transition]
    on_enters: List[OnStage]
    on_durings: List[OnStage]
    on_exits: List[OnStage]
    parent_ref: Optional[weakref.ReferenceType] = None
    substate_name_to_id: Dict[str, int] = None

    def __post_init__(self):
        self.substate_name_to_id = {name: i for i, (name, _) in enumerate(self.substates.items())}

    @property
    def is_leaf_state(self) -> bool:
        return len(self.substates) == 0

    @property
    def parent(self) -> Optional['State']:
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']):
        if new_parent is None:
            self.parent_ref = None
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_root_state(self) -> bool:
        return self.parent is None

    @property
    def transitions_from(self) -> List[Transition]:
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.from_state == self.name:
                    retval.append(transition)
        else:
            retval.append(Transition(
                from_state=self.name,
                to_state=EXIT_STATE,
                event=None,
                guard=None,
                effects=[],
                parent_ref=weakref.ref(self),
            ))
        return retval

    @property
    def transitions_to(self) -> List[Transition]:
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.to_state == self.name:
                    retval.append(transition)
        else:
            retval.append(Transition(
                from_state=INIT_STATE,
                to_state=self.name,
                event=None,
                guard=None,
                effects=[],
                parent_ref=weakref.ref(self),
            ))

        return retval

    @property
    def transitions_entering_children(self) -> List[Transition]:
        return [
            transition for transition in self.transitions
            if transition.from_state is INIT_STATE
        ]

    @property
    def transitions_entering_children_for_generation(self) -> List[Optional[Transition]]:
        retval = []
        for transition in self.transitions:
            if transition.from_state is INIT_STATE:
                retval.append(transition)
                if transition.event is None and transition.guard is None:
                    break
        if not retval or (retval and not (retval[-1].event is None and retval[-1].guard is None)):
            retval.append(None)
        return retval

    @property
    def path_text(self):
        return '.'.join(self.path)

    @property
    def abstract_on_enters(self) -> List[OnStage]:
        return [item for item in self.on_enters if item.is_abstract]

    @property
    def non_abstract_on_enters(self) -> List[OnStage]:
        return [item for item in self.on_enters if not item.is_abstract]

    @property
    def abstract_on_durings(self) -> List[OnStage]:
        return [item for item in self.on_durings if item.is_abstract]

    @property
    def non_abstract_on_durings(self) -> List[OnStage]:
        return [item for item in self.on_durings if not item.is_abstract]

    @property
    def abstract_on_exits(self) -> List[OnStage]:
        return [item for item in self.on_exits if item.is_abstract]

    @property
    def non_abstract_on_exits(self) -> List[OnStage]:
        return [item for item in self.on_exits if not item.is_abstract]

    def to_transition_ast_node(self, transition: Transition) -> dsl_nodes.TransitionDefinition:
        return dsl_nodes.TransitionDefinition(
            from_state=transition.from_state,
            to_state=transition.to_state,
            event_id=dsl_nodes.ChainID(
                path=list(transition.event.path[len(self.path):])) if transition.event is not None else None,
            condition_expr=transition.guard.to_ast_node() if transition.guard is not None else None,
            post_operations=[
                item.to_ast_node()
                for item in transition.effects
            ]
        )

    def to_ast_node(self) -> dsl_nodes.StateDefinition:
        return dsl_nodes.StateDefinition(
            name=self.name,
            substates=[
                substate.to_ast_node()
                for _, substate in self.substates.items()
            ],
            transitions=[self.to_transition_ast_node(trans) for trans in self.transitions],
            enters=[item.to_ast_node() for item in self.on_enters],
            durings=[item.to_ast_node() for item in self.on_durings],
            exits=[item.to_ast_node() for item in self.on_exits],
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

                        if len(trans.effects) > 0:
                            print('', file=tf)
                            print('note on link', file=tf)
                            print('effect {', file=tf)
                            for operation in trans.effects:
                                print(f'    {operation.to_ast_node()}', file=tf)
                            print('}', file=tf)
                            print('end note', file=tf, end='')

                        trans_text = tf.getvalue()
                    print(indent(trans_text, prefix='    '), file=sf)
                print(f'}}', file=sf, end='')

            if self.on_enters or self.on_durings or self.on_exits:
                print('', file=sf)
                with io.StringIO() as tf:
                    for enter_item in self.on_enters:
                        print(enter_item.to_ast_node(), file=tf)
                    for during_item in self.on_durings:
                        print(during_item.to_ast_node(), file=tf)
                    for exit_item in self.on_exits:
                        print(exit_item.to_ast_node(), file=tf)
                    text = json.dumps(tf.getvalue().rstrip()).strip("\"")
                    print(f'{self.name} : {text}', file=sf, end='')

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

    def name_ast_node(self) -> dsl_nodes.Name:
        return dsl_nodes.Name(self.name)


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
            for op_item in transnode.post_operations:
                operation_val = parse_expr_node_to_expr(op_item.expr)
                unknown_vars = []
                for var in operation_val.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if op_item.name not in d_defines and op_item.name not in unknown_vars:
                    unknown_vars.append(op_item.name)
                if unknown_vars:
                    raise SyntaxError(
                        f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{transnode}')
                post_operations.append(Operation(var_name=op_item.name, expr=operation_val))

            transition = Transition(
                from_state=from_state,
                to_state=to_state,
                event=trans_event,
                guard=guard,
                effects=post_operations,
            )
            transitions.append(transition)

        if d_substates and not has_entry_trans:
            raise SyntaxError(f'At least 1 entry transition should be assigned in non-leaf states:\n{node}')

        on_enters = []
        for enter_item in node.enters:
            if isinstance(enter_item, dsl_nodes.EnterOperations):
                enter_operations = []
                for op_item in enter_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{enter_item}')
                    enter_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_enters.append(OnStage(
                    stage='enter',
                    aspect=None,
                    name=None,
                    doc=None,
                    operations=enter_operations,
                ))
            elif isinstance(enter_item, dsl_nodes.EnterAbstractFunction):
                on_enters.append(OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=enter_item.doc,
                    operations=[],
                ))

        on_durings = []
        for during_item in node.durings:
            if not d_substates and during_item.aspect is not None:
                raise SyntaxError(f'For leaf state, during cannot assign aspect {during_item.aspect!r}:\n{during_item}')
            if d_substates and during_item.aspect is None:
                raise SyntaxError(
                    f'For composite state, during must assign aspect to either \'before\' or \'after\':\n{during_item}')

            if isinstance(during_item, dsl_nodes.DuringOperations):
                during_operations = []
                for op_item in during_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{during_item}')
                    during_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_durings.append(OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=None,
                    doc=None,
                    operations=during_operations,
                ))
            elif isinstance(during_item, dsl_nodes.DuringAbstractFunction):
                on_durings.append(OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=during_item.doc,
                    operations=[],
                ))

        on_exits = []
        for exit_item in node.exits:
            if isinstance(exit_item, dsl_nodes.ExitOperations):
                exit_operations = []
                for op_item in exit_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{exit_item}')
                    exit_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_exits.append(OnStage(
                    stage='exit',
                    aspect=None,
                    name=None,
                    doc=None,
                    operations=exit_operations,
                ))
            elif isinstance(exit_item, dsl_nodes.ExitAbstractFunction):
                on_exits.append(OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=exit_item.doc,
                    operations=[],
                ))

        my_state = State(
            name=node.name,
            path=current_path,
            substates=d_substates,
            events=d_events,
            transitions=transitions,
            on_enters=on_enters,
            on_durings=on_durings,
            on_exits=on_exits,
            parent_ref=None,
        )
        for _, substate in d_substates.items():
            substate.parent = my_state
        for transition in transitions:
            transition.parent = my_state
        return my_state

    root_state = _recursive_build_states(dnode.root_state, current_path=())
    return StateMachine(
        defines=d_defines,
        root_state=root_state,
    )
