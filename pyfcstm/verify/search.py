from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Union, Tuple, List

import z3

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


def bfs_search(
        state_machine: StateMachine,
        init_state: Union[State, str],
        init_constraints: Optional[Union[str, z3.BoolRef, Expr]] = None,
        max_cycle: int = 100,
):
    z3_vars = create_z3_vars_from_state_machine(state_machine)

    if isinstance(init_state, str):
        init_state = state_machine.resolve_state(init_state)
    elif isinstance(init_state, State):
        if state_machine.state_belongs_to_machine(init_state):
            # TODO: create a error raising for me
            pass
    else:
        # TODO: create a error raising for me
        pass

    if isinstance(init_constraints, str):
        init_constraints = expr_to_z3(
            expr=parse_expr(init_constraints, mode='logical'),
            z3_vars=z3_vars,
        )
    elif isinstance(init_constraints, z3.BoolRef):
        pass
    elif isinstance(init_constraints, Expr):
        init_constraints = expr_to_z3(expr=init_constraints, z3_vars=z3_vars)
    elif init_constraints is None:
        init_constraints = z3.BoolVal(True)
    else:
        # TODO: create a error raising for me
        pass

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

        if head.type == 'leaf':
            pass
        elif head.type == 'composite_in':
            pass
        elif head.type == 'composite_out':
            pass
        elif head.type == 'end':
            pass
        else:
            # TODO; raise an error, unexpected
            pass
