"""
Symbolic breadth-first search utilities for verification state spaces.

This module implements a symbolic breadth-first search over a
:class:`pyfcstm.model.StateMachine`. The search operates on internal frame
objects that represent leaf states, composite-state entry boundaries,
composite-state exit boundaries, and the terminal ``<end>`` marker.

Each frame carries symbolic variable expressions, accumulated Z3 path
constraints, the triggering event for the last transition, and a link to the
previous frame so complete symbolic paths can be reconstructed after the
search completes.

The main entry point is :func:`bfs_search`, which expands transitions in
declaration order, applies lifecycle actions and transition effects
symbolically, and retains only frames that enlarge the reachable solution
space for a given state and frame type.

The module contains:

* :class:`SearchFrame` - A single symbolic node in the search graph.
* :class:`StateSearchSpace` - Collected frames for one state/type bucket.
* :class:`StateSearchContext` - Search queue, buckets, and symbolic event vars.
* :func:`get_z3_event_key_and_var_name` - Normalize one cycle/event pair.
* :func:`parse_z3_event_var_name` - Parse a symbolic event variable name.
* :func:`bfs_search` - Run symbolic breadth-first exploration.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state Root {
    ...     state Idle;
    ...     [*] -> Idle;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> ctx = bfs_search(sm, 'Root.Idle', init_constraints='counter >= 0', max_cycle=2)
    >>> ('Root.Idle', 'leaf') in ctx.spaces
    True
"""

import re
import warnings
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Union, Tuple, List

import z3

from pyfcstm.dsl import GrammarParseError, EXIT_STATE
from pyfcstm.model import State, StateMachine, parse_expr, Expr, Event, OnAspect, OnStage
from pyfcstm.solver import expr_to_z3, create_z3_vars_from_state_machine, z3_or, z3_not, z3_and, execute_operations, \
    contributes_to_solution_space, solve as solve_constraints, SolveResult

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

FrameTypeTyping = Literal['leaf', 'composite_in', 'composite_out', 'end']
_Z3_EVENT_VAR_NAME_PATTERN = re.compile(r'^_E_C(?P<cycle>\d+)__(?P<event>.+)$')


def get_z3_event_key_and_var_name(cycle: int, event: Union[str, Event]) -> Tuple[Tuple[int, str], str]:
    """
    Normalize one symbolic event identifier into its key and Z3 name.

    Event-triggered transitions are represented with one Z3 boolean variable
    per ``(cycle, event_path)`` pair. This helper canonicalizes the event path
    and returns both the dictionary key and the generated Z3 variable name.

    :param cycle: Cycle index for the event variable.
    :type cycle: int
    :param event: Event object or fully qualified event path string.
    :type event: Union[str, Event]
    :return: ``((cycle, event_path), var_name)`` tuple.
    :rtype: Tuple[Tuple[int, str], str]
    :raises TypeError: If ``cycle`` is not an integer or ``event`` is neither
        a string nor an :class:`pyfcstm.model.Event`.
    :raises ValueError: If ``cycle`` is negative or the event path is empty.

    Example::

        >>> get_z3_event_key_and_var_name(2, 'Root.System.Tick')
        ((2, 'Root.System.Tick'), '_E_C2__Root.System.Tick')
    """
    if isinstance(cycle, bool) or not isinstance(cycle, int):
        raise TypeError(
            "get_z3_event_key_and_var_name() expected 'cycle' to be an int, "
            f"but got {type(cycle).__name__}: {cycle!r}."
        )
    if cycle < 0:
        raise ValueError(
            "get_z3_event_key_and_var_name() expected 'cycle' to be a non-negative int, "
            f"but got {cycle!r}."
        )

    if isinstance(event, Event):
        event = event.path_name
    elif not isinstance(event, str):
        raise TypeError(
            "get_z3_event_key_and_var_name() expected 'event' to be a string or Event, "
            f"but got {type(event).__name__}: {event!r}."
        )

    if not event:
        raise ValueError(
            "get_z3_event_key_and_var_name() expected 'event' to be a non-empty event path string."
        )

    key = (cycle, event)
    var_name = f'_E_C{cycle}__{event}'
    return key, var_name


def parse_z3_event_var_name(var_name_or_var: Union[str, z3.ExprRef]) -> Tuple[int, str]:
    """
    Parse a symbolic event variable name back into ``(cycle, event_path)``.

    The input may be the raw variable name string or a Z3 symbolic variable.
    Only uninterpreted Z3 variables are accepted. The expected variable name
    format is ``_E_C<cycle>__<event_path>``.

    :param var_name_or_var: Event variable name string or Z3 variable.
    :type var_name_or_var: Union[str, z3.ExprRef]
    :return: Parsed ``(cycle, event_path)`` tuple.
    :rtype: Tuple[int, str]
    :raises TypeError: If the input is neither a string nor a Z3 variable.
    :raises ValueError: If the input does not follow the expected event
        variable naming format.

    Example::

        >>> parse_z3_event_var_name('_E_C3__Root.System.Tick')
        (3, 'Root.System.Tick')
    """
    if isinstance(var_name_or_var, str):
        var_name = var_name_or_var
    elif isinstance(var_name_or_var, z3.ExprRef):
        if not z3.is_const(var_name_or_var) or var_name_or_var.decl().kind() != z3.Z3_OP_UNINTERPRETED:
            raise TypeError(
                "parse_z3_event_var_name() expected a string or a Z3 symbolic variable, "
                f"but got expression {var_name_or_var!r}."
            )
        var_name = str(var_name_or_var.decl().name())
    else:
        raise TypeError(
            "parse_z3_event_var_name() expected a string or a Z3 symbolic variable, "
            f"but got {type(var_name_or_var).__name__}: {var_name_or_var!r}."
        )

    match = _Z3_EVENT_VAR_NAME_PATTERN.fullmatch(var_name)
    if not match:
        raise ValueError(
            "Failed to parse a Z3 event variable name. "
            f"Received {var_name!r}. "
            "Expected format '_E_C<cycle>__<event_path>', for example "
            "'_E_C2__Root.System.Tick'."
        )

    return int(match.group('cycle')), match.group('event')


@dataclass
class SearchFrame:
    """
    Single symbolic frame produced during verification search.

    A frame represents one execution boundary reached by the symbolic search.
    Depending on :attr:`type`, it may describe a leaf state, a composite-state
    entry point, a composite-state exit point, or the terminal end marker.

    The frame stores the symbolic variable mapping and accumulated Z3
    constraint that must hold for this path to be reachable. Frames are linked
    through :attr:`prev_frame` so callers can reconstruct the symbolic
    execution path that led to the current frame.

    :param state: State represented by this frame. ``None`` is only valid for
        the terminal ``'end'`` frame type.
    :type state: Optional[State]
    :param type: Internal frame category. Supported values are ``'leaf'``,
        ``'composite_in'``, ``'composite_out'``, and ``'end'``.
    :type type: FrameTypeTyping
    :param var_state: Symbolic variable mapping at this frame.
    :type var_state: Dict[str, z3.ArithRef]
    :param constraints: Z3 constraint describing all conditions required to
        reach this frame.
    :type constraints: z3.BoolRef
    :param event: Event that triggered the transition into this frame, or
        ``None`` if the edge was guard-driven or unconditional.
    :type event: Optional[Event]
    :param depth: Search depth from the initial frame.
    :type depth: int
    :param cycle: Cycle count consumed when reaching this frame.
    :type cycle: int
    :param prev_frame: Previous frame in the reconstructed symbolic path.
        Defaults to ``None``.
    :type prev_frame: Optional[SearchFrame], optional

    :ivar state: State represented by this frame.
    :vartype state: Optional[State]
    :ivar type: Internal frame category.
    :vartype type: FrameTypeTyping
    :ivar var_state: Symbolic variable mapping at this frame.
    :vartype var_state: Dict[str, z3.ArithRef]
    :ivar constraints: Reachability constraint for this frame.
    :vartype constraints: z3.BoolRef
    :ivar event: Transition event that led to this frame, if any.
    :vartype event: Optional[Event]
    :ivar depth: Search depth from the initial frame.
    :vartype depth: int
    :ivar cycle: Cycle count consumed at this frame.
    :vartype cycle: int
    :ivar prev_frame: Previous symbolic frame in the explored path.
    :vartype prev_frame: Optional[SearchFrame]

    Example::

        >>> frame = SearchFrame(
        ...     state=None,
        ...     type='end',
        ...     var_state={},
        ...     constraints=z3.BoolVal(True),
        ...     event=None,
        ...     depth=1,
        ...     cycle=1,
        ... )
        >>> frame.type
        'end'
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

    def get_history(self) -> List['SearchFrame']:
        """
        Reconstruct the complete frame history in forward order.

        This walks :attr:`prev_frame` links back to the initial frame and
        returns the resulting path ordered from the oldest frame to ``self``.
        The returned list always includes the current frame.

        :return: Complete symbolic history from the initial frame to ``self``.
        :rtype: List[SearchFrame]

        Example::

            >>> frame0 = SearchFrame(
            ...     state=None,
            ...     type='end',
            ...     var_state={},
            ...     constraints=z3.BoolVal(True),
            ...     event=None,
            ...     depth=0,
            ...     cycle=0,
            ... )
            >>> frame1 = SearchFrame(
            ...     state=None,
            ...     type='end',
            ...     var_state={},
            ...     constraints=z3.BoolVal(True),
            ...     event=None,
            ...     depth=1,
            ...     cycle=1,
            ...     prev_frame=frame0,
            ... )
            >>> [frame.depth for frame in frame1.get_history()]
            [0, 1]
        """
        history = []
        current = self
        while current is not None:
            history.append(current)
            current = current.prev_frame

        history.reverse()
        return history

    def solve(
            self,
            max_solutions: Optional[int] = 10,
            timeout: Optional[int] = None,
            warn_threshold: int = 1000,
    ) -> SolveResult:
        """
        Solve the reachability constraint represented by this frame.

        This is a thin convenience wrapper over :func:`pyfcstm.solver.solve`
        that forwards :attr:`constraints` directly to the solver and returns
        the resulting :class:`pyfcstm.solver.SolveResult`.

        :param max_solutions: Maximum number of solutions to enumerate.
            Defaults to ``10``.
        :type max_solutions: Optional[int], optional
        :param timeout: Solver timeout in milliseconds. ``None`` means no
            timeout. Defaults to ``None``.
        :type timeout: Optional[int], optional
        :param warn_threshold: Warning threshold used when
            ``max_solutions=None``. Defaults to ``1000``.
        :type warn_threshold: int, optional
        :return: Solve result for this frame's reachability constraint.
        :rtype: pyfcstm.solver.SolveResult

        Example::

            >>> x = z3.Int('x')
            >>> frame = SearchFrame(
            ...     state=None,
            ...     type='end',
            ...     var_state={'x': x},
            ...     constraints=x == 3,
            ...     event=None,
            ...     depth=0,
            ...     cycle=0,
            ... )
            >>> frame.solve(max_solutions=1).solutions
            [{'x': 3}]
        """
        return solve_constraints(
            constraints=self.constraints,
            max_solutions=max_solutions,
            timeout=timeout,
            warn_threshold=warn_threshold,
        )


@dataclass
class StateSearchSpace:
    """
    Reachability bucket for frames sharing one state/type location.

    A :class:`StateSearchSpace` groups all symbolic frames that reach the same
    formatted state path and frame type combination. The search uses these
    buckets to decide whether a newly generated frame contributes additional
    solutions before enqueuing it for further expansion.

    :param state: State represented by this bucket. ``None`` is used for the
        terminal ``<end>`` bucket.
    :type state: Optional[State]
    :param frames: Frames collected for this bucket.
    :type frames: List[SearchFrame]

    :ivar state: State represented by the bucket.
    :vartype state: Optional[State]
    :ivar frames: All frames retained for the bucket.
    :vartype frames: List[SearchFrame]

    Example::

        >>> bucket = StateSearchSpace(state=None, frames=[])
        >>> bucket.frames
        []
    """
    state: Optional[State]
    frames: List['SearchFrame']


@dataclass
class StateSearchContext:
    """
    Mutable container for BFS exploration state and results.

    The context tracks three pieces of data during a search:

    * :attr:`queue` - pending frames waiting to be expanded
    * :attr:`spaces` - retained frames grouped by formatted state path and
      frame type
    * :attr:`z3_events` - lazily created symbolic event variables keyed by
      cycle number and event path

    After :func:`bfs_search` returns, the queue is usually empty, while
    :attr:`spaces` and :attr:`z3_events` remain available for inspection or
    follow-up solving.

    :param queue: Pending frame queue. Defaults to an empty ``deque``.
    :type queue: deque
    :param spaces: Reachability buckets keyed by ``(state_path, frame_type)``.
        Defaults to an empty mapping.
    :type spaces: Dict[Tuple[str, str], StateSearchSpace]
    :param z3_events: Symbolic event variables keyed by ``(cycle, event_path)``.
        Defaults to an empty mapping.
    :type z3_events: Dict[Tuple[int, str], z3.BoolRef]

    :ivar queue: Pending frame queue.
    :vartype queue: deque
    :ivar spaces: Retained frames grouped by location.
    :vartype spaces: Dict[Tuple[str, str], StateSearchSpace]
    :ivar z3_events: Lazily created symbolic event variables.
    :vartype z3_events: Dict[Tuple[int, str], z3.BoolRef]

    Example::

        >>> ctx = StateSearchContext()
        >>> bool(ctx.queue)
        False
        >>> ctx.get_z3_event(0, 'Root.Idle.Resume', force=True) is not None
        True
    """
    queue: deque = field(default_factory=deque)
    spaces: Dict[Tuple[str, str], StateSearchSpace] = field(default_factory=dict)
    z3_events: Dict[Tuple[int, str], z3.BoolRef] = field(default_factory=dict)

    def get_z3_event(self, cycle: int, event: Union[str, Event], force: bool = False) -> Optional[z3.BoolRef]:
        """
        Get or create the symbolic Z3 event variable for one cycle/event pair.

        Event-triggered transitions are modeled using one boolean variable per
        cycle and event path. This helper normalizes :class:`Event` objects to
        their path names and optionally creates the corresponding Z3 variable
        when ``force`` is ``True``.

        :param cycle: Cycle index associated with the event variable.
        :type cycle: int
        :param event: Event object or fully qualified event path.
        :type event: Union[str, Event]
        :param force: Whether to create the variable when it does not already
            exist. Defaults to ``False``.
        :type force: bool, optional
        :return: Matching symbolic event variable, or ``None`` if absent and
            ``force`` is ``False``.
        :rtype: Optional[z3.BoolRef]

        Example::

            >>> ctx = StateSearchContext()
            >>> ctx.get_z3_event(1, 'Root.System.Tick') is None
            True
            >>> event_var = ctx.get_z3_event(1, 'Root.System.Tick', force=True)
            >>> str(event_var)
            '_E_C1__Root.System.Tick'
        """
        key, var_name = get_z3_event_key_and_var_name(cycle=cycle, event=event)
        if force and key not in self.z3_events:
            self.z3_events[key] = z3.Bool(var_name)
        return self.z3_events.get(key, None)


def _format_state_path(state: Optional[State]) -> str:
    """
    Format a state path for user-facing messages and search-space keys.

    :param state: State to format, or ``None`` for the terminal end marker.
    :type state: Optional[State]
    :return: Full dotted state path, or ``'<end>'`` when ``state`` is ``None``.
    :rtype: str
    """
    if state is None:
        return '<end>'
    return '.'.join(state.path)


def _ensure_boolean_constraint(
        constraint: Union[z3.ArithRef, z3.BoolRef],
        source_name: str,
        source_value: object,
) -> z3.BoolRef:
    """
    Ensure that an initial search constraint is a boolean Z3 expression.

    :param constraint: Constraint to validate.
    :type constraint: Union[z3.ArithRef, z3.BoolRef]
    :param source_name: Human-readable source label used in error messages.
    :type source_name: str
    :param source_value: Original user-provided value for diagnostics.
    :type source_value: object
    :return: The validated boolean constraint.
    :rtype: z3.BoolRef
    :raises ValueError: If ``constraint`` is not boolean.
    """
    if z3.is_bool(constraint):
        return constraint

    raise ValueError(
        f"{source_name} produced a non-boolean constraint for bfs_search(): {constraint!r}. "
        f"Received {source_value!r}. "
        "Initial search constraints must evaluate to true or false. "
        "If you want to restrict a numeric variable, use a comparison such as "
        "'counter > 0' instead of a numeric expression like 'counter + 1'."
    )


def _normalize_search_limits(
        max_cycle: Optional[int],
        max_depth: Optional[int],
) -> Tuple[Optional[int], Optional[int]]:
    """
    Normalize BFS cycle/depth limits and emit warnings for risky settings.

    ``max_cycle`` remains the primary user-facing limit. When ``max_depth`` is
    omitted, this helper derives a defensive default from ``max_cycle`` to
    prevent long chains of non-stoppable states from expanding without bound.

    :param max_cycle: Maximum cycle expansion limit, or ``None`` for no cycle
        limit.
    :type max_cycle: Optional[int]
    :param max_depth: Maximum search depth, or ``None`` to derive a default.
    :type max_depth: Optional[int]
    :return: Normalized ``(max_cycle, max_depth)`` tuple.
    :rtype: Tuple[Optional[int], Optional[int]]
    """
    if max_cycle is None:
        if max_depth is None:
            warnings.warn(
                "bfs_search() received max_cycle=None and max_depth=None. "
                "The search has no cycle or depth limit and may not terminate "
                "for state machines with unbounded symbolic paths.",
                UserWarning,
                stacklevel=3,
            )
        else:
            warnings.warn(
                f"bfs_search() received max_cycle=None. Cycle expansion is unlimited, "
                f"and the search is bounded only by max_depth={max_depth}. "
                "This may still explore a very large state space.",
                UserWarning,
                stacklevel=3,
            )
        effective_max_depth = max_depth
    else:
        effective_max_depth = int(max_cycle * 3) if max_depth is None else max_depth

    if effective_max_depth is not None and (max_cycle is None or effective_max_depth < max_cycle):
        warnings.warn(
            f"bfs_search() has max_depth={effective_max_depth} and max_cycle={max_cycle!r}. "
            "The depth limit is stricter than the cycle limit, so search expansion "
            "may stop on depth before the configured cycle budget is exhausted.",
            UserWarning,
            stacklevel=3,
        )

    return max_cycle, effective_max_depth


def bfs_search(
        state_machine: StateMachine,
        init_state: Union[State, str],
        init_constraints: Optional[Union[str, z3.BoolRef, Expr]] = None,
        max_cycle: Optional[int] = 100,
        max_depth: Optional[int] = None,
) -> StateSearchContext:
    """
    Explore a state machine symbolically with breadth-first search.

    This function performs symbolic exploration starting from ``init_state``.
    It models guards and events as Z3 constraints, executes lifecycle actions
    and transition effects symbolically, and records every retained frame in a
    :class:`StateSearchContext`.

    Search frames are expanded in declaration order. For each state/type
    bucket, a newly generated frame is retained only when its constraint adds
    solutions beyond the frames already stored in that bucket. Cycles advance
    when the search reaches a stoppable leaf state or the terminal end marker.

    :param state_machine: State machine to explore.
    :type state_machine: StateMachine
    :param init_state: Initial state as a :class:`State` object from the same
        machine or as a full dotted state path.
    :type init_state: Union[State, str]
    :param init_constraints: Optional initial reachability constraint. This may
        be a logical DSL expression string, a Z3 boolean expression, or a
        :class:`pyfcstm.model.Expr` object. Defaults to ``None``.
    :type init_constraints: Optional[Union[str, z3.BoolRef, pyfcstm.model.Expr]], optional
    :param max_cycle: Maximum number of cycles to expand. Frames at or beyond
        this cycle limit are not expanded further. Use ``None`` to disable the
        cycle limit. Defaults to ``100``.
    :type max_cycle: Optional[int], optional
    :param max_depth: Maximum search depth to expand. Frames at or beyond this
        depth limit are not expanded further. When set to ``None``, the
        effective depth limit is also ``None`` if ``max_cycle`` is ``None``,
        otherwise ``int(max_cycle * 3)``. Defaults to ``None``.
    :type max_depth: Optional[int], optional
    :return: Search context containing the explored state-space buckets,
        retained frames, and symbolic event variables.
    :rtype: StateSearchContext
    :raises TypeError: If ``init_state`` or ``init_constraints`` has an
        unsupported type.
    :raises LookupError: If ``init_state`` is a path that cannot be resolved.
    :raises ValueError: If ``init_state`` belongs to another state machine, if
        ``init_constraints`` cannot be parsed as a logical condition, or if an
        internal frame contributes a non-boolean constraint.
    :raises RuntimeError: If the internal search queue contains an invalid
        frame type or a non-terminal frame with ``state=None``.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> dsl_code = '''
        ... def int counter = 0;
        ... state Root {
        ...     state Idle;
        ...     [*] -> Idle;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> ctx = bfs_search(sm, 'Root.Idle', init_constraints='counter >= 0', max_cycle=1)
        >>> list(ctx.spaces.keys())
        [('Root.Idle', 'leaf')]
    """
    z3_vars = create_z3_vars_from_state_machine(state_machine)
    max_cycle, max_depth = _normalize_search_limits(
        max_cycle=max_cycle,
        max_depth=max_depth,
    )

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
        if max_depth is not None and head.depth >= max_depth:
            continue
        if max_cycle is not None and head.cycle >= max_cycle:
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
