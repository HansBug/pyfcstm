from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Union, Tuple, List

import z3

from pyfcstm.dsl import GrammarParseError
from pyfcstm.model import State, StateMachine, parse_expr, Expr
from pyfcstm.solver import expr_to_z3, create_z3_vars_from_state_machine

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal


@dataclass
class SearchFrame:
    """
    表示验证过程中的一个状态节点
    """
    state: Optional[State]  # 对应的状态机状态（end节点时为None）
    type: Literal['leaf', 'composite_in', 'composite_out', 'end']
    # leaf: 叶子状态（包括pseudo和stoppable）
    # composite_in: 复合状态的入口（刚进入复合状态，尚未进入子状态）
    # composite_out: 复合状态的出口（子状态已退出，尚未离开复合状态）
    # end: 终止状态（状态机结束，state为None）

    var_state: Dict[str, z3.ArithRef]  # 到达此节点时的变量状态（符号表达式）
    constraints: z3.BoolRef
    depth: int
    cycle: int  # 到达此节点经过的周期数
    previous_state: Optional['SearchFrame'] = None


@dataclass
class StateSearchSpace:
    state: State
    constraints: z3.BoolRef
    frames: List['SearchFrame']


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

    queue = deque()
    init_frame = SearchFrame(
        state=init_state,
        type='leaf' if init_state.is_leaf_state else 'composite_in',
        var_state=z3_vars,
        constraints=init_constraints,
        depth=0,
        cycle=0,
        previous_state=None,
    )
    queue.append(init_frame)

    reach_constraints: Dict[Optional[Tuple[str, ...]], StateSearchSpace] = {}
    reach_constraints[init_state.path] = StateSearchSpace(
        state=init_state,
        constraints=init_constraints,
        frames=[init_frame],
    )

    while len(queue) > 0:
        head: SearchFrame = queue.popleft()
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
            continue
        else:
            raise RuntimeError(
                "bfs_search() encountered an internal search frame with an unsupported "
                f"type {head.type!r} at state {_format_state_path(head.state)!r}, "
                f"cycle={head.cycle}, depth={head.depth}. "
                "Supported frame types are 'leaf', 'composite_in', 'composite_out', "
                "and 'end'. This usually indicates that the search queue was populated "
                "with an invalid frame."
            )

        for transiton in transitions:
            transiton.to_state.
            pass
