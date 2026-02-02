"""
This module provides functionality for searching paths in state machines and generating Z3 expressions
for path constraints. It implements a breadth-first search algorithm to find all possible paths from
a source state to a destination state, considering transition guards and variable constraints.

The main components include:

- SearchState: A dataclass representing a state during the search process
- get_search_expr: Function to generate Z3 expressions for path constraints between states

The module uses Z3 SMT solver to create and manipulate constraint expressions that represent
the conditions under which a path from source to destination state is valid. This is useful
for formal verification, test case generation, and reachability analysis of state machines.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

from z3 import ExprRef, BoolVal, And, Or, Not

from .define import def_numbers
from .expr import model_expr_to_z3_expr, operations_to_z3_vars, comprehensive_simplify
from ..dsl import EXIT_STATE
from ..model import State, StateMachine


def _and_constraints(constraints: List[ExprRef], empty_value: bool = True):
    """
    Combine a list of Z3 constraint expressions using logical AND.
    
    This helper function handles special cases:
    
    - Empty list returns a boolean value specified by empty_value
    - Single constraint returns the constraint itself
    - Multiple constraints are combined with And()
    
    :param constraints: List of Z3 constraint expressions to combine.
    :type constraints: List[ExprRef]
    :param empty_value: The boolean value to return when constraints list is empty, defaults to True.
    :type empty_value: bool
    
    :return: Combined Z3 expression or boolean value.
    :rtype: ExprRef
    
    Example::
        >>> _and_constraints([])  # Returns BoolVal(True)
        True
        >>> _and_constraints([expr1])  # Returns expr1
        expr1
        >>> _and_constraints([expr1, expr2])  # Returns And(expr1, expr2)
        And(expr1, expr2)
    """
    if not constraints:
        return BoolVal(empty_value)
    elif len(constraints) == 1:
        return constraints[0]
    else:
        return And(*constraints)


def _or_constraints(constraints: List[ExprRef], empty_value: bool = False):
    """
    Combine a list of Z3 constraint expressions using logical OR.
    
    This helper function handles special cases:
    
    - Empty list returns a boolean value specified by empty_value
    - Single constraint returns the constraint itself
    - Multiple constraints are combined with Or()
    
    :param constraints: List of Z3 constraint expressions to combine.
    :type constraints: List[ExprRef]
    :param empty_value: The boolean value to return when constraints list is empty, defaults to False.
    :type empty_value: bool
    
    :return: Combined Z3 expression or boolean value.
    :rtype: ExprRef
    
    Example::
        >>> _or_constraints([])  # Returns BoolVal(False)
        False
        >>> _or_constraints([expr1])  # Returns expr1
        expr1
        >>> _or_constraints([expr1, expr2])  # Returns Or(expr1, expr2)
        Or(expr1, expr2)
    """
    if not constraints:
        return BoolVal(empty_value)
    elif len(constraints) == 1:
        return constraints[0]
    else:
        return Or(*constraints)


@dataclass
class SearchState:
    """
    Represents a state during the search process in a state machine.
    
    This class encapsulates all information needed to track a state during path search,
    including the current state, path metrics, variable values, and accumulated constraints.
    
    The SearchState is used in breadth-first search to explore paths through a state machine,
    maintaining the context needed to generate Z3 constraint expressions for each path.
    
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
        return _and_constraints(self.constraints, empty_value=True)


def get_search_expr(model: StateMachine, src_state_path: str, dst_state_path: str,
                    max_path_length: Optional[int] = 20, max_cycle_length: int = 20):
    """
    Generate Z3 expressions for path constraints between source and destination states.
    
    This function performs a breadth-first search from the source state to the destination state,
    collecting all possible paths and their constraints. It returns the initial variable definitions
    and a Z3 expression representing the disjunction of all valid paths.
    
    The search algorithm:
    
    1. Starts from the source state with initial variables
    2. Explores all transitions from each state
    3. Accumulates constraints from transition guards
    4. Updates variables based on transition effects
    5. Ensures mutual exclusivity of transitions from the same state
    6. Stops when reaching the destination state or exceeding path limits
    7. Combines all valid paths with logical OR
    
    The search considers:
    
    - Transition guards as additional constraints
    - Variable effects from transitions
    - Maximum path length and cycle length limits
    - Pseudo states (which don't count towards cycle length)
    - Mutual exclusivity of transitions from the same state
    
    :param model: The state machine model to search within.
    :type model: StateMachine
    :param src_state_path: The path string identifying the source state.
    :type src_state_path: str
    :param dst_state_path: The path string identifying the destination state.
    :type dst_state_path: str
    :param max_path_length: Maximum number of transitions allowed in a path. None for unlimited, defaults to 20.
    :type max_path_length: Optional[int]
    :param max_cycle_length: Maximum number of non-pseudo states allowed in a path, defaults to 20.
    :type max_cycle_length: int
    
    :return: A tuple containing:
        - Dictionary of initial variable definitions (name -> Z3 expression)
        - Simplified Z3 expression representing all valid path constraints
        - List of SearchState objects that reached the destination state
    :rtype: tuple[Dict[str, ExprRef], ExprRef, List[SearchState]]
    
    Example::
        >>> model = StateMachine(...)
        >>> variables, constraints, dst_items = get_search_expr(model, 'state1', 'state2', max_path_length=10)
        >>> # variables contains initial Z3 variables
        >>> # constraints is a Z3 expression that must be satisfied for a valid path
        >>> # dst_items contains all search states that reached the destination
        >>> # Use Z3 solver to check satisfiability
        >>> from z3 import Solver
        >>> solver = Solver()
        >>> solver.add(constraints)
        >>> if solver.check() == sat:
        ...     print("Path exists:", solver.model())
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
        else:
            if (max_path_length is None or max_path_length > head.path_length) and \
                    (max_cycle_length is None or max_cycle_length > head.cycle_length):
                records_cons = []
                for transition in head.state.transitions_from:
                    cons = head.constraints
                    if transition.guard:
                        cons = [*cons, model_expr_to_z3_expr(transition.guard, head.variables)]

                    if transition.to_state == EXIT_STATE:
                        pass
                    else:
                        next_state = head.state.parent.substates[transition.to_state]
                        next_item = SearchState(
                            state=next_state,
                            path_length=head.path_length + 1,
                            cycle_length=head.cycle_length + (1 if not next_state.is_pseudo else 0),
                            pre_state=head,
                            variables=operations_to_z3_vars(transition.effects, head.variables),
                            constraints=[*cons, Not(_or_constraints(records_cons, empty_value=False))],
                        )
                        queue.append(next_item)

                    records_cons.append(_and_constraints(cons))

        f += 1

    final_cons = _or_constraints([item.get_constraint() for item in dst_items], empty_value=False)
    final_cons = comprehensive_simplify(final_cons)
    return queue[0].variables, final_cons, dst_items
