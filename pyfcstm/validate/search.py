"""
This module provides functionality for searching paths in state machines and generating Z3 expressions
for path constraints. It implements a breadth-first search algorithm to find all possible paths from
a source state to a destination state, considering transition guards and variable constraints.

The main components include:
- SearchState: A dataclass representing a state during the search process
- get_search_expr: Function to generate Z3 expressions for path constraints between states
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

from z3 import ExprRef, BoolVal, And, Or

from .define import def_numbers
from .expr import model_expr_to_z3_expr, operations_to_z3_vars, comprehensive_simplify
from ..dsl import EXIT_STATE
from ..model import State, StateMachine


@dataclass
class SearchState:
    """
    Represents a state during the search process in a state machine.
    
    This class encapsulates all information needed to track a state during path search,
    including the current state, path metrics, variable values, and accumulated constraints.
    
    :param state: The current state in the state machine.
    :type state: State
    :param path_length: The total number of transitions taken to reach this state.
    :type path_length: int
    :param cycle_length: The number of non-pseudo states traversed to reach this state.
    :type cycle_length: int
    :param pre_state: The previous SearchState in the path, None if this is the initial state.
    :type pre_state: Optional['SearchState']
    :param variables: Dictionary mapping variable names to their Z3 expressions.
    :type variables: Dict[str, ExprRef]
    :param constraints: List of Z3 constraint expressions accumulated along the path.
    :type constraints: List[ExprRef]
    """
    state: State
    path_length: int
    cycle_length: int
    pre_state: Optional['SearchState']
    variables: Dict[str, ExprRef]
    constraints: List[ExprRef]

    def get_constraint(self) -> ExprRef:
        """
        Get the combined constraint expression for this search state.
        
        Combines all accumulated constraints into a single Z3 expression using logical AND.
        Returns True if there are no constraints.
        
        :return: A Z3 expression representing the combined constraints.
        :rtype: ExprRef
        
        Example::
            >>> search_state = SearchState(...)
            >>> constraint = search_state.get_constraint()
            >>> # Returns BoolVal(True) if no constraints, otherwise And(*constraints)
        """
        if not self.constraints:
            return BoolVal(True)
        elif len(self.constraints) == 1:
            return self.constraints[0]
        else:
            return And(*self.constraints)


def get_search_expr(model: StateMachine, src_state_path: str, dst_state_path: str,
                    max_path_length: Optional[int] = 20, max_cycle_length: int = 20):
    """
    Generate Z3 expressions for path constraints between source and destination states.
    
    This function performs a breadth-first search from the source state to the destination state,
    collecting all possible paths and their constraints. It returns the initial variable definitions
    and a Z3 expression representing the disjunction of all valid paths.
    
    The search considers:
    - Transition guards as additional constraints
    - Variable effects from transitions
    - Maximum path length and cycle length limits
    - Pseudo states (which don't count towards cycle length)
    
    :param model: The state machine model to search within.
    :type model: StateMachine
    :param src_state_path: The path string identifying the source state.
    :type src_state_path: str
    :param dst_state_path: The path string identifying the destination state.
    :type dst_state_path: str
    :param max_path_length: Maximum number of transitions allowed in a path. None for unlimited.
    :type max_path_length: Optional[int]
    :param max_cycle_length: Maximum number of non-pseudo states allowed in a path.
    :type max_cycle_length: int
    
    :return: A tuple containing:
        - Dictionary of initial variable definitions (name -> Z3 expression)
        - Simplified Z3 expression representing all valid path constraints
    :rtype: tuple[Dict[str, ExprRef], ExprRef]
    
    Example::
        >>> model = StateMachine(...)
        >>> variables, constraints = get_search_expr(model, 'state1', 'state2', max_path_length=10)
        >>> # variables contains initial Z3 variables
        >>> # constraints is a Z3 expression that must be satisfied for a valid path
    """
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
