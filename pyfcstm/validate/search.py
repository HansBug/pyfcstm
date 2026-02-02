from dataclasses import dataclass
from typing import List, Dict, Optional

from z3 import ExprRef, BoolVal, And, Or

from .define import def_numbers
from .expr import model_expr_to_z3_expr, operations_to_z3_vars, comprehensive_simplify
from ..dsl import EXIT_STATE
from ..model import State, StateMachine


@dataclass
class SearchState:
    state: State
    path_length: int
    cycle_length: int
    pre_state: Optional['SearchState']
    variables: Dict[str, ExprRef]
    constraints: List[ExprRef]

    def get_constraint(self) -> ExprRef:
        if not self.constraints:
            return BoolVal(True)
        elif len(self.constraints) == 1:
            return self.constraints[0]
        else:
            return And(*self.constraints)


def get_search_expr(model: StateMachine, src_state_path: str, dst_state_path: str,
                    max_path_length: Optional[int] = 20, max_cycle_length: int = 20):
    src_state = model.resolve_state(src_state_path)
    dst_state = model.resolve_state(dst_state_path)

    init = SearchState(
        state=src_state,
        path_length=0,
        cycle_length=0,
        pre_state=None,
        variables=def_numbers({name: def_item.type for name, def_item in model.defines.items()}),
        constraints=[],
    )
    queue = [init]
    f = 0
    dst_items = []
    while f < len(queue):
        head: SearchState = queue[f]
        if head.state.path == dst_state.path:
            dst_items.append(head)

        if (max_path_length is None or max_path_length > head.path_length) and \
                (max_cycle_length is None or max_cycle_length > head.cycle_length):
            for transition in head.state.transitions_from:
                if transition.to_state == EXIT_STATE:
                    continue

                next_state = head.state.parent.substates[transition.to_state]
                cons = head.constraints
                if transition.guard:
                    cons = [*cons, model_expr_to_z3_expr(transition.guard, head.variables)]
                next_item = SearchState(
                    state=next_state,
                    path_length=head.path_length + 1,
                    cycle_length=head.cycle_length + (1 if not next_state.is_pseudo else 0),
                    pre_state=head,
                    variables=operations_to_z3_vars(transition.effects, head.variables),
                    constraints=cons,
                )
                queue.append(next_item)

        f += 1

    if not dst_items:
        final_cons = BoolVal(True)
    elif len(dst_items) == 1:
        final_cons = dst_items[0].get_constraint()
    else:
        final_cons = Or(*(item.get_constraint() for item in dst_items))

    return queue[0].variables, comprehensive_simplify(final_cons)
