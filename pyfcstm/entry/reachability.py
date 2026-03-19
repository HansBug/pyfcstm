"""
Formal reachability validation CLI built on top of the current symbolic verification engine.

This module ports the old ``dev/damn``-style formal validation flow to the
current ``pyfcstm.verify`` search model, but exposes it through the
``reachability`` command name. It keeps the same general report style while
using ``pyfcstm.verify.search`` frames as the witness source.
"""

from __future__ import annotations

import pathlib
import warnings
from typing import Dict, List, Optional, Tuple, Union

import click
import z3

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..dsl import EXIT_STATE, parse_with_grammar_entry
from ..model import OnAspect, OnStage, State, StateMachine, parse_dsl_node_to_state_machine
from ..solver import (
    create_z3_vars_from_state_machine,
    execute_operations,
    expr_to_z3,
    solve as solve_constraints,
    substitute_and_literalize,
    z3_and,
    z3_not,
    z3_or,
)
from ..utils import auto_decode
from ..verify import bfs_search
from ..verify.search import (
    SearchConcreteFrame,
    SearchFrame,
    StateSearchContext,
    _normalize_bfs_init_constraint,
    _normalize_search_limits,
)


def _resolve_state_path(state_machine: StateMachine, raw_path: str, option_name: str) -> State:
    """
    Resolve one full CLI state path into a concrete state.

    :param state_machine: Parsed state machine.
    :type state_machine: StateMachine
    :param raw_path: Full state path string from CLI.
    :type raw_path: str
    :param option_name: CLI option name used in diagnostics.
    :type option_name: str
    :return: Resolved state.
    :rtype: State
    :raises pyfcstm.entry.base.ClickErrorException: If the path cannot be resolved.
    """
    try:
        return state_machine.resolve_state(raw_path.strip())
    except (LookupError, ValueError) as err:
        raise ClickErrorException(
            f'Failed to resolve {option_name}={raw_path!r}. '
            "Please provide a full state path string such as 'Root.System.Active'."
        ) from err


def _get_state_frame_types(state: State) -> Tuple[str, ...]:
    """
    Map one user-facing state to the internal verification frame types.

    :param state: User-facing state.
    :type state: State
    :return: Candidate internal frame types for this state.
    :rtype: Tuple[str, ...]
    """
    if state.is_leaf_state:
        return 'leaf',
    return 'composite_in', 'composite_out'


def _z3_value_to_literal(value: z3.ExprRef) -> Union[bool, int, float]:
    """
    Convert one evaluated Z3 literal into a Python literal.

    :param value: Evaluated Z3 value.
    :type value: z3.ExprRef
    :return: Python literal value.
    :rtype: Union[bool, int, float]
    :raises ValueError: If the value cannot be converted.
    """
    if z3.is_true(value):
        return True
    if z3.is_false(value):
        return False
    if z3.is_int_value(value):
        return value.as_long()
    if z3.is_rational_value(value):
        return float(value.numerator_as_long()) / float(value.denominator_as_long())
    if z3.is_algebraic_value(value):
        return float(value.approx(20).as_decimal(20))

    raise ValueError(f'Unsupported evaluated Z3 value for witness materialization: {value!r}.')


def _build_complete_solution_for_frame(
        state_machine: StateMachine,
        frame: SearchFrame,
        partial_solution: Optional[Dict[str, Union[bool, int, float]]] = None,
) -> Dict[str, Union[bool, int, float]]:
    """
    Build a fully grounded solution mapping for one target frame history.

    :param state_machine: Parsed state machine.
    :type state_machine: StateMachine
    :param frame: Target symbolic frame.
    :type frame: SearchFrame
    :param partial_solution: Optional partial assignment that should be preserved.
    :type partial_solution: Optional[Dict[str, Union[bool, int, float]]]
    :return: Fully grounded substitution mapping.
    :rtype: Dict[str, Union[bool, int, float]]
    """
    solver = z3.Solver()
    solver.add(frame.constraints)
    partial_solution = partial_solution or {}

    machine_vars = create_z3_vars_from_state_machine(state_machine)
    for name, value in partial_solution.items():
        if name in machine_vars:
            var_expr = machine_vars[name]
        else:
            var_expr = z3.Bool(name)

        if z3.is_bool(var_expr):
            solver.add(var_expr == z3.BoolVal(bool(value)))
        elif z3.is_int(var_expr):
            solver.add(var_expr == z3.IntVal(int(value)))
        elif z3.is_real(var_expr):
            solver.add(var_expr == z3.RealVal(str(value)))
        else:
            raise ClickErrorException(
                f'Unsupported variable sort while materializing witness for {name!r}: {var_expr.sort()!r}.'
            )

    check_result = solver.check()
    if check_result != z3.sat:
        raise ClickErrorException(
            f'Failed to materialize a concrete witness model for target frame: solver returned {check_result!r}.'
        )

    model = solver.model()
    solution: Dict[str, Union[bool, int, float]] = {}

    for var_name, var_expr in machine_vars.items():
        value = model.eval(var_expr, model_completion=True)
        solution[var_name] = _z3_value_to_literal(value)

    for history_frame in frame.get_history():
        if history_frame.event_var is None:
            continue
        event_name = str(history_frame.event_var)
        if event_name in solution:
            continue
        value = model.eval(history_frame.event_var, model_completion=True)
        solution[event_name] = _z3_value_to_literal(value)

    return solution


def _run_search_from_initial_frames(
        initial_frames: List[SearchFrame],
        max_cycle: Optional[int],
        max_depth: Optional[int],
        fn_on_enqueue,
) -> StateSearchContext:
    """
    Run BFS expansion from pre-built initial frames inside the entry layer.

    :param initial_frames: Pre-built initial symbolic frames.
    :type initial_frames: List[SearchFrame]
    :param max_cycle: Maximum cycle budget.
    :type max_cycle: Optional[int]
    :param max_depth: Maximum search depth.
    :type max_depth: Optional[int]
    :param fn_on_enqueue: Retained-frame callback.
    :type fn_on_enqueue: callable
    :return: Search context containing explored frames.
    :rtype: StateSearchContext
    """
    if fn_on_enqueue is not None and not callable(fn_on_enqueue):
        raise TypeError(
            "validate entry expected 'fn_on_enqueue' to be None or callable, "
            f"but got {type(fn_on_enqueue).__name__}: {fn_on_enqueue!r}."
        )

    max_cycle, max_depth = _normalize_search_limits(
        max_cycle=max_cycle,
        max_depth=max_depth,
    )

    def _should_stop_search(ctx: StateSearchContext) -> bool:
        if fn_on_enqueue is None:
            return False

        should_stop = fn_on_enqueue(ctx)
        if not isinstance(should_stop, bool):
            raise TypeError(
                "validate entry expected 'fn_on_enqueue' to return a bool, "
                f"but got {type(should_stop).__name__}: {should_stop!r}."
            )
        return should_stop

    ctx = StateSearchContext()
    for initial_frame in initial_frames:
        if ctx.try_append_frame(initial_frame) and _should_stop_search(ctx):
            return ctx

    while len(ctx.queue) > 0:
        head: SearchFrame = ctx.queue.popleft()
        if max_depth is not None and head.depth >= max_depth:
            continue
        if max_cycle is not None and head.cycle >= max_cycle:
            continue

        if head.type != 'end' and head.state is None:
            raise RuntimeError(
                "validate entry encountered an internal search frame with no state attached "
                f"for frame type {head.type!r} at cycle={head.cycle}, depth={head.depth}."
            )

        if head.type == 'leaf' or head.type == 'composite_out':
            transitions = head.state.transitions_from
        elif head.type == 'composite_in':
            transitions = head.state.init_transitions
        elif head.type == 'end':
            transitions = []
        else:
            raise RuntimeError(
                "validate entry encountered an internal search frame with an unsupported "
                f"type {head.type!r} at state "
                f'{(".".join(head.state.path) if head.state is not None else "<end>")!r}.'
            )

        prev_conditions = []
        for transition in transitions:
            from_state = transition.from_state_obj
            to_state = transition.to_state_obj
            if head.type == 'composite_in':
                to_type = 'leaf' if to_state.is_leaf_state else 'composite_in'
            else:
                if to_state == EXIT_STATE:
                    to_state = from_state.parent
                    to_type = 'end' if head.state.is_root_state else 'composite_out'
                else:
                    to_type = 'leaf' if to_state.is_leaf_state else 'composite_in'

            if transition.guard:
                condition = expr_to_z3(expr=transition.guard, z3_vars=head.var_state)
                event_var = None
            elif transition.event:
                condition = ctx.get_z3_event(head.cycle, transition.event, force=True)
                event_var = condition
            else:
                condition = z3.BoolVal(True)
                event_var = None
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
                    action = action  # type: Union[OnAspect, OnStage]
                    z3_vars = execute_operations(
                        operations=action.operations,
                        var_exprs=z3_vars,
                    )

            new_frame = SearchFrame(
                state=to_state,
                type=to_type,
                var_state=z3_vars,
                constraints=z3_and([head.constraints, actual_condition]),
                event_var=event_var,
                depth=head.depth + 1,
                cycle=head.cycle + (1 if to_state is None or to_state.is_stoppable else 0),
                prev_frame=head,
            )
            if ctx.try_append_frame(new_frame) and _should_stop_search(ctx):
                return ctx
            prev_conditions.append(condition)

        if head.type == 'leaf' and head.state.is_stoppable:
            actual_condition = z3_not(z3_or(prev_conditions))
            z3_vars = head.var_state
            for _, action in head.state.iter_on_during_aspect_recursively(is_abstract=False):
                action = action  # type: Union[OnAspect, OnStage]
                z3_vars = execute_operations(
                    operations=action.operations,
                    var_exprs=z3_vars,
                )

            new_frame = SearchFrame(
                state=head.state,
                type=head.type,
                var_state=z3_vars,
                constraints=z3_and([head.constraints, actual_condition]),
                event_var=None,
                depth=head.depth + 1,
                cycle=head.cycle + 1,
                prev_frame=head,
            )
            if ctx.try_append_frame(new_frame) and _should_stop_search(ctx):
                return ctx

    return ctx


def _load_state_machine(input_code_file: str) -> StateMachine:
    """
    Load and parse one DSL file into a state machine model.

    :param input_code_file: Input DSL file path.
    :type input_code_file: str
    :return: Parsed state machine model.
    :rtype: StateMachine
    :raises pyfcstm.entry.base.ClickErrorException: If the input file cannot be read.
    """
    input_path = pathlib.Path(input_code_file)
    try:
        code = auto_decode(input_path.read_bytes())
    except FileNotFoundError:
        raise ClickErrorException(f"Input file '{input_code_file}' not found")
    except OSError as err:
        raise ClickErrorException(f"Failed to read input file '{input_code_file}': {err}")

    ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast_node)


def _collect_target_frames(
        ctx: StateSearchContext,
        target_state: State,
        target_frame_types: Tuple[str, ...],
) -> List[SearchFrame]:
    """
    Collect retained search frames that correspond to the requested target state.

    :param ctx: Search context returned by BFS.
    :type ctx: StateSearchContext
    :param target_state: User-facing target state.
    :type target_state: State
    :param target_frame_types: Internal frame types accepted for the target.
    :type target_frame_types: Tuple[str, ...]
    :return: Matching search frames ordered by cycle, depth, and history length.
    :rtype: List[SearchFrame]
    """
    target_frames: List[SearchFrame] = []
    state_key = '.'.join(target_state.path)
    for frame_type in target_frame_types:
        space = ctx.spaces.get((state_key, frame_type))
        if space is not None:
            target_frames.extend(space.frames)

    target_frames.sort(key=lambda frame: (frame.cycle, frame.depth, len(frame.get_history()), frame.type))
    return target_frames


def _build_target_constraint(target_frames: List[SearchFrame]) -> z3.BoolRef:
    """
    Merge all target-frame constraints into one disjunction.

    :param target_frames: Matching target frames.
    :type target_frames: List[SearchFrame]
    :return: Disjunction of target-frame constraints.
    :rtype: z3.BoolRef
    """
    return z3_or([frame.constraints for frame in target_frames])


def _does_frame_match_partial_solution(
        frame: SearchFrame,
        partial_solution: Dict[str, Union[bool, int, float]],
) -> bool:
    """
    Check whether one partial solver assignment satisfies a frame constraint.

    :param frame: Candidate target frame.
    :type frame: SearchFrame
    :param partial_solution: Partial assignment returned by constraint solving.
    :type partial_solution: Dict[str, Union[bool, int, float]]
    :return: Whether the partial assignment satisfies the frame constraint.
    :rtype: bool
    """
    result = substitute_and_literalize(frame.constraints, partial_solution)
    return result is True or z3.is_true(result)


def _find_matching_target_frame(
        target_frames: List[SearchFrame],
        partial_solution: Dict[str, Union[bool, int, float]],
) -> Optional[SearchFrame]:
    """
    Find the first target frame satisfied by one partial assignment.

    :param target_frames: Candidate target frames.
    :type target_frames: List[SearchFrame]
    :param partial_solution: Partial assignment returned by solver.
    :type partial_solution: Dict[str, Union[bool, int, float]]
    :return: Matching target frame, or ``None`` if no frame matches.
    :rtype: Optional[SearchFrame]
    """
    for frame in target_frames:
        if _does_frame_match_partial_solution(frame, partial_solution):
            return frame
    return None


def _render_concrete_path(concrete_path: List[SearchConcreteFrame]) -> None:
    """
    Print one concrete witness path in the old validate report format.

    :param concrete_path: Concrete witness path.
    :type concrete_path: List[SearchConcreteFrame]
    :return: ``None``.
    :rtype: None
    """
    for index, frame in enumerate(concrete_path):
        state_path = '.'.join(frame.state.path) if frame.state is not None else '<end>'
        if index == 0:
            click.echo(f"🏁 START: {state_path:<20} [Path: {frame.depth:2d}, Cycle: {frame.cycle:2d}]")
        elif index == len(concrete_path) - 1:
            click.echo(f"🎯 END:   {state_path:<20} [Path: {frame.depth:2d}, Cycle: {frame.cycle:2d}]")
        else:
            click.echo(f"📍 STEP:  {state_path:<20} [Path: {frame.depth:2d}, Cycle: {frame.cycle:2d}]")

        for var_name, var_value in frame.var_state.items():
            click.echo(f"       {var_name} = {var_value}")

        if index < len(concrete_path) - 1:
            if frame.events:
                click.echo(f"       events = {frame.events}")
            click.echo("       ⬇️")


def _run_validate_search(
        state_machine: StateMachine,
        source_state: State,
        constraint: Optional[str],
        max_path_length: int,
        max_cycle_length: int,
) -> StateSearchContext:
    """
    Run bounded symbolic search for the validate CLI.

    :param state_machine: Parsed state machine.
    :type state_machine: StateMachine
    :param source_state: Source state.
    :type source_state: State
    :param constraint: Optional initial constraint.
    :type constraint: Optional[str]
    :param max_path_length: Maximum symbolic path length.
    :type max_path_length: int
    :param max_cycle_length: Maximum cycle length.
    :type max_cycle_length: int
    :return: Search context.
    :rtype: StateSearchContext
    """
    init_frame_types = _get_state_frame_types(source_state)
    if init_frame_types == ('leaf',):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            return bfs_search(
                state_machine=state_machine,
                init=(source_state, constraint) if constraint is not None else source_state,
                max_cycle=max_cycle_length,
                max_depth=max_path_length,
            )

    z3_vars = create_z3_vars_from_state_machine(state_machine)
    init_constraints = _normalize_bfs_init_constraint(
        raw_init_constraints=constraint,
        z3_vars=z3_vars,
        source_name="'constraint'",
    )
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        return _run_search_from_initial_frames(
            initial_frames=[
                SearchFrame(
                    state=source_state,
                    type=frame_type,
                    var_state=z3_vars,
                    constraints=init_constraints,
                    event_var=None,
                    depth=0,
                    cycle=0,
                    prev_frame=None,
                )
                for frame_type in init_frame_types
            ],
            max_cycle=max_cycle_length,
            max_depth=max_path_length,
            fn_on_enqueue=None,
        )


def _add_reachability_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``reachability`` subcommand to the CLI group.

    :param cli: Click group to extend.
    :type cli: click.Group
    :return: The mutated Click group.
    :rtype: click.Group
    """

    @cli.command(
        'reachability',
        help='Validate and analyze paths between states in a state machine DSL.',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i',
        '--input-code',
        'input_code_file',
        type=str,
        required=True,
        help='Input code file of state machine DSL.',
    )
    @click.option(
        '-s',
        '--source-state',
        '--src-state',
        'source_state',
        type=str,
        required=True,
        help='Source state path for path validation.',
    )
    @click.option(
        '-d',
        '--destination-state',
        '--dst-state',
        'destination_state',
        type=str,
        required=True,
        help='Destination state path for path validation.',
    )
    @click.option(
        '-p',
        '--max-path-length',
        'max_path_length',
        type=int,
        default=30,
        show_default=True,
        help='Maximum number of symbolic steps allowed in a path.',
    )
    @click.option(
        '-c',
        '--max-cycle-length',
        'max_cycle_length',
        type=int,
        default=20,
        show_default=True,
        help='Maximum number of non-pseudo cycles allowed in a path.',
    )
    @click.option(
        '-n',
        '--max-solutions',
        'max_solutions',
        type=int,
        default=10,
        show_default=True,
        help='Maximum number of solutions to find.',
    )
    @click.option(
        '--constraint',
        'constraint',
        type=str,
        default=None,
        help='Optional logical DSL constraint for the initial state variables.',
    )
    @click.option(
        '--show-constraints',
        'show_constraints',
        is_flag=True,
        help='Show the generated Z3 constraint expression.',
    )
    @click.option(
        '--show-variables',
        'show_variables',
        is_flag=True,
        help='Show the generated Z3 variable definitions.',
    )
    def reachability(
            input_code_file: str,
            source_state: str,
            destination_state: str,
            max_path_length: int,
            max_cycle_length: int,
            max_solutions: int,
            constraint: Optional[str],
            show_constraints: bool,
            show_variables: bool,
    ) -> None:
        """
        Validate and analyze paths between states in a state machine.

        :return: ``None``.
        :rtype: None
        """
        click.echo(f"🔍 Loading state machine from: {input_code_file}")
        state_machine = _load_state_machine(input_code_file)
        click.echo("✅ State machine loaded successfully")

        source_state_obj = _resolve_state_path(state_machine, source_state, '--source-state')
        destination_state_obj = _resolve_state_path(state_machine, destination_state, '--destination-state')

        click.echo(f"\n🔎 Searching paths from '{source_state}' to '{destination_state}'")
        click.echo(f"   Max path length: {max_path_length}")
        click.echo(f"   Max cycle length: {max_cycle_length}")

        ctx = _run_validate_search(
            state_machine=state_machine,
            source_state=source_state_obj,
            constraint=constraint,
            max_path_length=max_path_length,
            max_cycle_length=max_cycle_length,
        )
        target_frames = _collect_target_frames(
            ctx=ctx,
            target_state=destination_state_obj,
            target_frame_types=_get_state_frame_types(destination_state_obj),
        )
        final_constraint = _build_target_constraint(target_frames)

        if show_variables:
            click.echo("\n📊 Z3 Variables:")
            for name, var in create_z3_vars_from_state_machine(state_machine).items():
                click.echo(f"   {name}: {var}")
            for key, var in sorted(ctx.z3_events.items(), key=lambda item: item[0]):
                del key
                click.echo(f"   {var}: {var}")

        if show_constraints:
            click.echo("\n🔗 Z3 Constraints:")
            click.echo(f"   {final_constraint}")

        click.echo("\n⚡ Solving constraints...")
        solve_result = solve_constraints(
            constraints=final_constraint,
            max_solutions=max_solutions,
        )

        if solve_result.status == 'sat' and solve_result.solutions:
            click.echo(f"✅ Found {len(solve_result.solutions)} valid path(s)")

            for index, solution in enumerate(solve_result.solutions, start=1):
                click.echo(f"\n{'=' * 60}")
                click.echo(f"🛤️  PATH {index}")
                click.echo(f"{'=' * 60}")

                matched_frame = _find_matching_target_frame(target_frames, solution)
                if matched_frame is None:
                    click.echo("❌ Error: Could not find corresponding state item")
                    continue

                complete_solution = _build_complete_solution_for_frame(
                    state_machine=state_machine,
                    frame=matched_frame,
                    partial_solution=solution,
                )
                concrete_path = matched_frame.to_concrete_frames(complete_solution)
                _render_concrete_path(concrete_path)
        elif solve_result.status == 'unsat':
            click.echo(f"❌ No valid path found from '{source_state}' to '{destination_state}'")
            click.echo("   The constraints cannot be satisfied with the given parameters.")
        else:
            click.echo("❓ Could not determine if a valid path exists")
            click.echo("   The Z3 solver returned an undetermined result.")
            click.echo("   Try adjusting the path length limits or simplifying the constraints.")

    return cli
