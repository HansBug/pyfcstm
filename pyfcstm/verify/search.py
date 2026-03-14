from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Union, Tuple, List

import z3

from pyfcstm.dsl import GrammarParseError, EXIT_STATE
from pyfcstm.model import State, StateMachine, parse_expr, Expr, Event, OnAspect, OnStage
from pyfcstm.solver import expr_to_z3, create_z3_vars_from_state_machine, z3_or, z3_not, z3_and, execute_operations, \
    contributes_to_solution_space

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

FrameTypeTyping = Literal['leaf', 'composite_in', 'composite_out', 'end']


@dataclass
class SearchFrame:
    """
    表示验证过程中的一个状态节点
    """
    state: Optional[State]  # 对应的状态机状态（end节点时为None）
    type: FrameTypeTyping
    # leaf: 叶子状态（包括pseudo和stoppable）
    # composite_in: 复合状态的入口（刚进入复合状态，尚未进入子状态）
    # composite_out: 复合状态的出口（子状态已退出，尚未离开复合状态）
    # end: 终止状态（状态机结束，state为None）

    var_state: Dict[str, z3.ArithRef]  # 到达此节点时的变量状态（符号表达式）
    constraints: z3.BoolRef
    event: Optional[Event]
    depth: int
    cycle: int  # 到达此节点经过的周期数
    prev_frame: Optional['SearchFrame'] = None


@dataclass
class StateSearchSpace:
    state: State
    frames: List['SearchFrame']


@dataclass
class StateSearchContext:
    queue: deque = field(default_factory=deque)
    spaces: Dict[Tuple[str, str], StateSearchSpace] = field(default_factory=dict)
    z3_events: Dict[Tuple[int, str], z3.Bool] = field(default_factory=dict)

    def get_z3_event(self, cycle: int, event: Union[str, Event], force: bool = False) -> Optional[z3.Bool]:
        if isinstance(event, Event):
            event = event.path_name
        key = (cycle, event)
        var_name = f'_E_C{cycle}__{event}'
        if force and key not in self.z3_events:
            self.z3_events[key] = z3.Bool(var_name)
        return self.z3_events.get(key, None)


def _format_state_path(state: Optional[State]) -> str:
    """Format a state path for user-facing error messages."""
    if state is None:
        return '<end>'
    return '.'.join(state.path)


def _ensure_boolean_constraint(
        constraint: Union[z3.ArithRef, z3.BoolRef],
        source_name: str,
        source_value: object,
) -> z3.BoolRef:
    """Ensure an initial search constraint is a boolean expression."""
    if z3.is_bool(constraint):
        return constraint

    raise ValueError(
        f"{source_name} produced a non-boolean constraint for bfs_search(): {constraint!r}. "
        f"Received {source_value!r}. "
        "Initial search constraints must evaluate to true or false. "
        "If you want to restrict a numeric variable, use a comparison such as "
        "'counter > 0' instead of a numeric expression like 'counter + 1'."
    )


def bfs_search(
        state_machine: StateMachine,
        init_state: Union[State, str],
        init_constraints: Optional[Union[str, z3.BoolRef, Expr]] = None,
        max_cycle: int = 100,
):
    z3_vars = create_z3_vars_from_state_machine(state_machine)

    if isinstance(init_state, str):
        try:
            init_state = state_machine.resolve_state(init_state)
        except (ValueError, LookupError) as err:
            raise type(err)(
                "Failed to resolve 'init_state' for bfs_search(). "
                f"Received state path {init_state!r}. "
                f"{err} "
                "Make sure the path is complete, starts from the state machine root, "
                "and points to an existing state, for example 'Root.System.Active'."
            ) from err
    elif isinstance(init_state, State):
        if not state_machine.state_belongs_to_machine(init_state):
            raise ValueError(
                "bfs_search() received a State object in 'init_state' that does not belong "
                f"to the provided state machine. Received state {_format_state_path(init_state)!r}. "
                "This usually means the State object came from a different parsed state machine "
                "instance. Use a State returned by this 'state_machine', or pass a full state "
                "path string instead."
            )
    else:
        raise TypeError(
            "bfs_search() expected 'init_state' to be a State object or a full state path "
            f"string, but got {type(init_state).__name__}: {init_state!r}. "
            "Pass a State from this state machine, or a string like 'Root.System.Active'."
        )

    if isinstance(init_constraints, str):
        try:
            init_constraints_expr = parse_expr(init_constraints, mode='logical')
        except GrammarParseError as err:
            raise ValueError(
                "Failed to parse 'init_constraints' for bfs_search(). "
                f"Received {init_constraints!r}. "
                "This argument must be a logical DSL condition, not an arithmetic expression "
                "or statement. Examples: 'counter > 0', 'ready && retries < 3'."
            ) from err
        init_constraints = _ensure_boolean_constraint(
            constraint=expr_to_z3(expr=init_constraints_expr, z3_vars=z3_vars),
            source_name="'init_constraints'",
            source_value=init_constraints,
        )
    elif isinstance(init_constraints, z3.BoolRef):
        pass
    elif isinstance(init_constraints, Expr):
        init_constraints = _ensure_boolean_constraint(
            constraint=expr_to_z3(expr=init_constraints, z3_vars=z3_vars),
            source_name="'init_constraints'",
            source_value=init_constraints,
        )
    elif init_constraints is None:
        init_constraints = z3.BoolVal(True)
    else:
        raise TypeError(
            "bfs_search() expected 'init_constraints' to be None, a logical DSL expression "
            "string, a Z3 BoolRef, or a pyfcstm Expr object, "
            f"but got {type(init_constraints).__name__}: {init_constraints!r}. "
            "If you want to pass DSL text, use a logical condition such as "
            "'counter > 0 && enabled'."
        )

    ctx = StateSearchContext()
    init_frame = SearchFrame(
        state=init_state,
        type='leaf' if init_state.is_leaf_state else 'composite_in',
        var_state=z3_vars,
        constraints=init_constraints,
        event=None,
        depth=0,
        cycle=0,
        prev_frame=None,
    )
    ctx.queue.append(init_frame)
    init_type = 'leaf' if init_state.is_leaf_state else 'composite_in'
    ctx.spaces[(_format_state_path(init_state), init_type)] = StateSearchSpace(
        state=init_state,
        frames=[init_frame],
    )

    def _try_append_frame(frame: SearchFrame):
        space_key = (_format_state_path(frame.state), frame.type)
        if space_key in ctx.spaces:
            space = ctx.spaces[space_key]
            current_cond = z3_or([f.constraints for f in space.frames])
            if contributes_to_solution_space(
                    x=current_cond,
                    y=frame.constraints,
            ):
                space.frames.append(frame)
                ctx.queue.append(frame)
        else:
            ctx.spaces[space_key] = StateSearchSpace(
                state=frame.state,
                frames=[frame],
            )
            ctx.queue.append(frame)

    while len(ctx.queue) > 0:
        head: SearchFrame = ctx.queue.popleft()
        if head.cycle >= max_cycle:
            continue

        if head.type != 'end' and head.state is None:
            raise RuntimeError(
                "bfs_search() encountered an internal search frame with no state attached "
                f"for frame type {head.type!r} at cycle={head.cycle}, depth={head.depth}. "
                "Only the 'end' frame type may have 'state=None'. This usually indicates that "
                "the search queue was populated with an invalid frame."
            )

        if head.type == 'leaf' or head.type == 'composite_out':
            transitions = head.state.transitions_from
        elif head.type == 'composite_in':
            transitions = head.state.init_transitions
        elif head.type == 'end':
            transitions = []
        else:
            raise RuntimeError(
                "bfs_search() encountered an internal search frame with an unsupported "
                f"type {head.type!r} at state {_format_state_path(head.state)!r}, "
                f"cycle={head.cycle}, depth={head.depth}. "
                "Supported frame types are 'leaf', 'composite_in', 'composite_out', "
                "and 'end'. This usually indicates that the search queue was populated "
                "with an invalid frame."
            )

        prev_conditions = []
        for transition in transitions:
            from_state = transition.from_state_obj
            to_state = transition.to_state_obj
            to_type: FrameTypeTyping
            if head.type == 'composite_in':
                if to_state.is_leaf_state:
                    to_type = 'leaf'
                else:
                    to_type = 'composite_in'
            else:
                if to_state == EXIT_STATE:
                    to_state = from_state.parent
                    if head.state.is_root_state:
                        to_type = 'end'
                    else:
                        to_type = 'composite_out'
                elif to_state.is_leaf_state:
                    to_type = 'leaf'
                else:
                    to_type = 'composite_in'

            if transition.guard:
                condition = expr_to_z3(expr=transition.guard, z3_vars=head.var_state)
                event = None
            elif transition.event:
                condition = ctx.get_z3_event(head.cycle, transition.event, force=True)
                event = transition.event
            else:
                condition = z3.BoolVal(True)
                event = None
            actual_condition = z3_and([z3_not(z3_or(prev_conditions)), condition])

            z3_vars = head.var_state

            if head.type == 'composite_in':
                for action in head.state.list_on_durings(is_abstract=False, aspect='before'):
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )
            elif head.type == 'leaf' or head.type == 'composite_out':
                for action in head.state.list_on_exits(is_abstract=False):
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )

            z3_vars = execute_operations(
                operations=transition.effects,
                var_exprs=z3_vars,
            )

            if to_type == 'composite_out':
                for action in to_state.list_on_durings(is_abstract=False, aspect='after'):
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )
            elif to_type == 'leaf' or to_type == 'composite_in':
                for action in to_state.list_on_enters(is_abstract=False):
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )

            if to_state and to_state.is_leaf_state:
                for _, action in to_state.list_on_during_aspect_recursively(is_abstract=False):
                    action: Union[OnAspect, OnStage]
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )

            new_frame = SearchFrame(
                state=to_state,
                type=to_type,
                var_state=z3_vars,
                constraints=z3_and([head.constraints, actual_condition]),
                event=event,
                depth=head.depth + 1,
                cycle=head.cycle + (1 if to_state is None or to_state.is_stoppable else 0),
                prev_frame=head,
            )
            _try_append_frame(new_frame)
            prev_conditions.append(condition)

        if head.type == 'leaf' and head.state.is_stoppable:
            actual_condition = z3_not(z3_or(prev_conditions))
            z3_vars = head.var_state
            for _, action in head.state.iter_on_during_aspect_recursively(is_abstract=False):
                action: Union[OnAspect, OnStage]
                z3_vars = execute_operations(
                    operations=action.operations,
                    var_exprs=z3_vars,
                )

            new_frame = SearchFrame(
                state=head.state,
                type=head.type,
                var_state=z3_vars,
                constraints=z3_and([head.constraints, actual_condition]),
                event=None,
                depth=head.depth + 1,
                cycle=head.cycle + 1,
                prev_frame=head,
            )
            _try_append_frame(new_frame)

    return ctx
