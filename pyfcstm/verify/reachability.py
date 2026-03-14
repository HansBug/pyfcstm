"""
Reachability verification helpers built on top of symbolic BFS search.

This module uses :func:`pyfcstm.verify.search.bfs_search` to answer a focused
question: starting from one or more initial state/constraint entries, can the
state machine reach a given target state within the configured cycle budget?

When a reachable target frame is found, the module solves that frame's
symbolic constraints and materializes one concrete path using
:class:`pyfcstm.verify.search.SearchConcreteFrame`.

The module contains:

* :class:`ReachabilityResult` - Reachability verdict and one witness path.
* :func:`verify_reachability` - Run bounded reachability verification.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Union

from pyfcstm.model import StateMachine, State
from pyfcstm.verify.search import (
    bfs_search,
    SearchFrame,
    SearchConcreteFrame,
    StateSearchContext,
    ConcreteLiteralTyping,
    InitTyping,
    _normalize_bfs_init_state,
)


@dataclass(frozen=True)
class ReachabilityResult:
    """
    Result of a bounded state reachability verification query.

    :param reachable: Whether the target state is reachable.
    :type reachable: bool
    :param target_frame: Symbolic frame proving reachability, or ``None`` when
        unreachable.
    :type target_frame: Optional[SearchFrame]
    :param concrete_path: One concrete witness path from an initial entry to
        :attr:`target_frame`, or ``None`` when unreachable.
    :type concrete_path: Optional[List[SearchConcreteFrame]]
    :param solution: Concrete variable assignment used to materialize
        :attr:`concrete_path`, or ``None`` when unreachable.
    :type solution: Optional[Dict[str, ConcreteLiteralTyping]]
    :param search_context: BFS search context produced during the query.
    :type search_context: StateSearchContext
    """

    reachable: bool
    target_frame: Optional[SearchFrame]
    concrete_path: Optional[List[SearchConcreteFrame]]
    solution: Optional[Dict[str, ConcreteLiteralTyping]]
    search_context: StateSearchContext


def verify_reachability(
        state_machine: StateMachine,
        init: InitTyping,
        target_state: Union[State, str],
        max_cycle: Optional[int] = 100,
        max_depth: Optional[int] = None,
) -> ReachabilityResult:
    """
    Verify whether a target state is reachable within the given search bounds.

    This function runs :func:`pyfcstm.verify.search.bfs_search` and uses its
    ``fn_on_enqueue`` callback to inspect every retained symbolic frame as soon
    as it is enqueued. Once a frame whose state matches ``target_state``
    produces one satisfiable solution, the BFS stops immediately and that
    witness is returned.

    :param state_machine: State machine to verify.
    :type state_machine: StateMachine
    :param init: Initial BFS entry specification forwarded to
        :func:`pyfcstm.verify.search.bfs_search`.
    :type init: InitTyping
    :param target_state: Target state as a :class:`State` object from the same
        machine or as a full dotted state path.
    :type target_state: Union[State, str]
    :param max_cycle: Maximum number of cycles to expand. Defaults to ``100``.
    :type max_cycle: Optional[int], optional
    :param max_depth: Maximum search depth to expand. Defaults to ``None``.
    :type max_depth: Optional[int], optional

    .. note::
       When reachability is established early, the returned
       :attr:`ReachabilityResult.search_context` contains only the explored
       prefix of the bounded search space.

    :return: Reachability result with one witness path when reachable.
    :rtype: ReachabilityResult
    :raises TypeError: If ``target_state`` has an unsupported type.
    :raises LookupError: If ``target_state`` is a path that cannot be resolved.
    :raises ValueError: If ``target_state`` belongs to another state machine.
    """
    target_state = _normalize_bfs_init_state(
        state_machine=state_machine,
        raw_init_state=target_state,
        source_name="'target_state'",
    )

    found_target_frame: Optional[SearchFrame] = None
    found_solution: Optional[Dict[str, ConcreteLiteralTyping]] = None
    found_concrete_path: Optional[List[SearchConcreteFrame]] = None

    def _stop_when_target_becomes_sat(ctx: StateSearchContext) -> bool:
        nonlocal found_target_frame, found_solution, found_concrete_path

        frame = ctx.queue[-1]
        if frame.state is not target_state:
            return False

        solve_result = frame.solve(max_solutions=1)
        if solve_result.status != 'sat' or not solve_result.solutions:
            return False

        found_target_frame = frame
        found_solution = solve_result.solutions[0]
        found_concrete_path = frame.to_concrete_frames(found_solution)
        return True

    ctx = bfs_search(
        state_machine=state_machine,
        init=init,
        max_cycle=max_cycle,
        max_depth=max_depth,
        fn_on_enqueue=_stop_when_target_becomes_sat,
    )

    if found_target_frame is not None:
        assert found_solution is not None
        assert found_concrete_path is not None
        return ReachabilityResult(
            reachable=True,
            target_frame=found_target_frame,
            concrete_path=found_concrete_path,
            solution=found_solution,
            search_context=ctx,
        )

    return ReachabilityResult(
        reachable=False,
        target_frame=None,
        concrete_path=None,
        solution=None,
        search_context=ctx,
    )
