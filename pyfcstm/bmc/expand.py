"""Runtime-aligned macro-step expansion for FCSTM BMC.

The expansion layer turns a :class:`pyfcstm.bmc.source.MacroStepSource` into a
solver-independent :class:`pyfcstm.bmc.macro.MacroStepFormal`.  It mirrors the
cycle-level control flow of :class:`pyfcstm.simulate.SimulationRuntime` while
staying strictly below solver lowering: the output is a flat control-path plan
with event atoms, anchored guard requirements, accepted-path priority masks, and
ordered model action blocks.  The expander does not build Z3 expressions, does
not turn operations into writeback strings, and does not split action-local
``if`` blocks into separate cases.

The module contains:

* :class:`MacroExpansionOptions` - Runtime-aligned safety and self-check limits.
* :func:`expand_macro_step_cases` - Public source-only macro-step expander.

Example::

    >>> from pyfcstm.bmc import build_bmc_domain, stable_leaf_source
    >>> from pyfcstm.bmc.expand import expand_macro_step_cases
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('def int x = 0; state Root { during { x = x + 1; } }')
    >>> domain = build_bmc_domain(model, 1)
    >>> formal = expand_macro_step_cases(stable_leaf_source(domain, 'Root'))
    >>> formal.success_cases[0].kind
    'fallback'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union, cast

from pyfcstm.bmc.domain import STATE_TERMINATE_ID, BmcDomain
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcDomain, InvalidBmcEncoding
from pyfcstm.bmc.macro import (
    ActionBlock,
    BoolTemplate,
    CycleCase,
    EventUse,
    GuardRequirement,
    MacroStepFormal,
    PriorityExclusion,
    build_semantic_delta_case,
    diagnostic_absorb_case,
    terminated_absorb_case,
)
from pyfcstm.bmc.source import TERMINATE_CASE_PATH, MacroStepSource
from pyfcstm.dsl import EXIT_STATE
from pyfcstm.model import (
    Boolean,
    OnAspect,
    OnStage,
    OperationStatement,
    State,
    Transition,
)

_CASE_KIND_FALLBACK = "fallback"
_CASE_KIND_INITIAL = "initial"
_CASE_KIND_TRANSITION = "transition"
_EVENT_ATOM_PREFIX = "event:"
_GUARD_ATOM_PREFIX = "guard:"
_ACCEPTED_ATOM_PREFIX = "accepted:"


def _internal_expansion_error(detail: str) -> BmcBuildError:
    return BmcBuildError(
        "internal error: %s This indicates a pyfcstm BMC bug or a corrupted "
        "internal object; please report this issue with the FCSTM input, query, "
        "and traceback at https://github.com/HansBug/pyfcstm/issues." % detail
    )


def _validate_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBmcEncoding("%s must be a positive integer." % field_name)
    if value <= 0:
        raise InvalidBmcEncoding("%s must be a positive integer." % field_name)
    return value


@dataclass(frozen=True)
class MacroExpansionOptions:
    """Options controlling macro-step expansion safety checks.

    :param max_micro_steps: Maximum symbolic micro-steps explored before the
        build fails, defaults to ``1000``.
    :type max_micro_steps: int, optional
    :param max_stack_depth: Maximum runtime stack depth, defaults to ``64``.
    :type max_stack_depth: int, optional
    :param verify_partition: Whether to run the source-local partition
        self-check after building cases, defaults to ``True``.
    :type verify_partition: bool, optional
    :param partition_max_assignments: Assignment budget for the fallback
        truth-table checker, defaults to ``4096``.  Structurally recognized
        accepted/fallback masks can validate without enumerating this budget.
    :type partition_max_assignments: int, optional

    Example::

        >>> MacroExpansionOptions(max_micro_steps=10).max_stack_depth
        64
    """

    max_micro_steps: int = 1000
    max_stack_depth: int = 64
    verify_partition: bool = True
    partition_max_assignments: int = 4096

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_micro_steps",
            _validate_positive_int(self.max_micro_steps, "max_micro_steps"),
        )
        object.__setattr__(
            self,
            "max_stack_depth",
            _validate_positive_int(self.max_stack_depth, "max_stack_depth"),
        )
        object.__setattr__(
            self,
            "partition_max_assignments",
            _validate_positive_int(
                self.partition_max_assignments, "partition_max_assignments"
            ),
        )
        if not isinstance(self.verify_partition, bool):
            raise InvalidBmcEncoding("verify_partition must be a boolean.")


@dataclass(frozen=True)
class _FormalStackFrame:
    state: State
    mode: str
    plain_before_pending: bool = False


@dataclass(frozen=True)
class _MacroFrontier:
    stack: Tuple[_FormalStackFrame, ...]
    condition: BoolTemplate
    used_events: Tuple[EventUse, ...]
    action_blocks: Tuple[ActionBlock, ...]
    guard_requirements: Tuple[GuardRequirement, ...]
    priority_exclusions: Tuple[PriorityExclusion, ...]
    case_kind: str
    path_signatures: Tuple[Tuple[Tuple[object, ...], int], ...] = ()
    depth: int = 0


@dataclass(frozen=True)
class _MacroOutcome:
    label: str
    target_state_id: int
    target_state_path: str
    condition: BoolTemplate
    used_events: Tuple[EventUse, ...]
    action_blocks: Tuple[ActionBlock, ...]
    guard_requirements: Tuple[GuardRequirement, ...]
    priority_exclusions: Tuple[PriorityExclusion, ...]
    case_kind: str
    failed_conditions: Tuple[BoolTemplate, ...] = ()


@dataclass(frozen=True)
class _Expansion:
    outcomes: Tuple[_MacroOutcome, ...]
    failed: Tuple[BoolTemplate, ...]
    diagnostics: Tuple[BoolTemplate, ...]


def expand_macro_step_cases(
    source: MacroStepSource,
    options: Optional[MacroExpansionOptions] = None,
) -> MacroStepFormal:
    """Expand one macro-step source into runtime-aligned flat cases.

    :param source: Macro-step source profile to expand.
    :type source: MacroStepSource
    :param options: Expansion safety options, defaults to ``None``.
    :type options: MacroExpansionOptions, optional
    :return: Source-local macro-step formal.
    :rtype: pyfcstm.bmc.macro.MacroStepFormal
    :raises InvalidBmcEncoding: If the source is malformed or lacks a domain
        model reference.
    :raises BmcBuildError: If expansion cannot safely summarize a bounded
        runtime path.

    Example::

        >>> from pyfcstm.bmc import build_bmc_domain, stable_leaf_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> domain = build_bmc_domain(model, 1)
        >>> expand_macro_step_cases(stable_leaf_source(domain, 'Root')).success_cases[0].kind
        'fallback'
    """
    if not isinstance(source, MacroStepSource):
        raise InvalidBmcEncoding("source must be MacroStepSource.")
    if options is None:
        options = MacroExpansionOptions()
    elif not isinstance(options, MacroExpansionOptions):
        raise InvalidBmcEncoding("options must be MacroExpansionOptions.")
    return _MacroExpander(source, options).expand()


class _MacroExpander:
    """Internal runtime-aligned macro-step expander."""

    def __init__(self, source: MacroStepSource, options: MacroExpansionOptions) -> None:
        self.source = source
        domain = source.domain
        if domain is None:
            raise InvalidBmcEncoding(
                "macro-step expansion requires a domain-backed source."
            )
        if not isinstance(domain, BmcDomain):
            raise _internal_expansion_error(  # pragma: no cover
                "macro-step source domain is not a BmcDomain after source validation."
            )
        model = domain.model
        if model is None:
            raise InvalidBmcEncoding(
                "macro-step expansion requires a domain with model back-reference."
            )
        self.domain = domain
        self.model = model
        self.options = options
        self.states_by_path: Dict[str, State] = {
            ".".join(state.path): state for state in self.model.walk_states()
        }
        self.state_ids: Dict[str, int] = {
            entry.path: entry.id
            for entry in self.domain.states
            if not entry.is_sentinel
        }
        self._case_counters: Dict[str, int] = {}
        self._failed_guard_requirements: Dict[str, GuardRequirement] = {}
        self._guard_counter = 0
        self._decision_counter = 0

    def expand(self) -> MacroStepFormal:
        """Return the expanded macro-step formal."""
        if self.source.kind == "terminated":
            return MacroStepFormal(self.source, (terminated_absorb_case(self.domain),))
        if self.source.kind == "diagnostic":
            return MacroStepFormal(self.source, (diagnostic_absorb_case(self.domain),))

        expansion = self._merge_expansions(
            self._expand_frontier(frontier)
            for frontier in self._frontiers_from_source()
        )
        success_cases = self._cases_from_outcomes(expansion.outcomes)
        delta_cases = ()
        diagnostics = expansion.diagnostics
        if self.source.allows_semantic_delta:
            delta_cases = (
                build_semantic_delta_case(
                    self.domain,
                    self.source,
                    success_cases,
                    diagnostics,
                    expansion.failed,
                    guard_requirements=self._guard_requirements_for_conditions(
                        expansion.failed
                    ),
                ),
            )
        elif diagnostics:
            raise _internal_expansion_error(  # pragma: no cover
                "stable macro-step source produced unsupported build diagnostic "
                "conditions."
            )
        formal = MacroStepFormal(self.source, success_cases, delta_cases, diagnostics)
        if self.options.verify_partition:
            formal.verify_partition(
                max_assignments=self.options.partition_max_assignments
            )
        return formal

    @staticmethod
    def _merge_expansions(expansions: Iterable[_Expansion]) -> _Expansion:
        outcomes: List[_MacroOutcome] = []
        failed: List[BoolTemplate] = []
        diagnostics: List[BoolTemplate] = []
        for expansion in expansions:
            outcomes.extend(expansion.outcomes)
            failed.extend(expansion.failed)
            diagnostics.extend(expansion.diagnostics)
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    def _frontiers_from_source(self) -> Tuple[_MacroFrontier, ...]:
        state = self._source_state()
        if self.source.kind == "stable_leaf":
            stack = tuple(
                _FormalStackFrame(item, "active") for item in _path_to_root(state)
            )
            return (
                _MacroFrontier(
                    stack,
                    BoolTemplate.true(),
                    (),
                    (),
                    (),
                    (),
                    _CASE_KIND_TRANSITION,
                ),
            )

        if self.source.kind != "entry":
            raise _internal_expansion_error(  # pragma: no cover
                "unsupported source kind reached macro expansion: %r."
                % self.source.kind
            )
        if state.is_root_state:
            base = _MacroFrontier(
                (),
                BoolTemplate.true(),
                (),
                (),
                (),
                (),
                _CASE_KIND_INITIAL,
            )
            return self._enter_state(base, state)
        stack = []
        path = _path_to_root(state)
        for index, item in enumerate(path):
            is_target = index == len(path) - 1
            if item.is_leaf_state:
                stack.append(_FormalStackFrame(item, "active"))
            elif is_target:
                stack.append(
                    _FormalStackFrame(item, "init_wait", plain_before_pending=False)
                )
            else:
                stack.append(_FormalStackFrame(item, "active"))
        return (
            _MacroFrontier(
                tuple(stack),
                BoolTemplate.true(),
                (),
                (),
                (),
                (),
                _CASE_KIND_INITIAL,
            ),
        )

    def _source_state(self) -> State:
        state = self.states_by_path.get(self.source.source_state_path)
        if state is None:
            raise InvalidBmcEncoding("source state is not present in the model.")
        return state

    def _expand_frontier(self, frontier: _MacroFrontier) -> _Expansion:
        if frontier.depth >= self.options.max_micro_steps:
            raise BmcBuildError(
                "macro-step expansion exceeded the micro-step safety limit."
            )
        if len(frontier.stack) > self.options.max_stack_depth:
            raise BmcBuildError(
                "macro-step expansion exceeded the stack-depth safety limit."
            )
        if frontier.condition.kind == "false":
            return _Expansion((), (), ())
        signature = self._frontier_signature(frontier)
        for previous_signature, previous_action_count in frontier.path_signatures:
            if previous_signature != signature:
                continue
            if len(frontier.action_blocks) > previous_action_count:
                raise BmcBuildError(
                    "macro-step expansion encountered an action-dependent pseudo loop."
                )
            self._remember_failed_guard_requirements(frontier)
            return _Expansion((), (frontier.condition,), ())
        frontier = self._replace_frontier(
            frontier,
            path_signatures=frontier.path_signatures
            + ((signature, len(frontier.action_blocks)),),
            depth=frontier.depth + 1,
        )

        if not frontier.stack:
            return _Expansion((self._terminate_outcome(frontier),), (), ())

        top = frontier.stack[-1]
        state = top.state
        if state.is_leaf_state and top.mode == "after_entry":
            active = self._replace_top(frontier, _FormalStackFrame(state, "active"))
            if state.is_stoppable:
                return _Expansion((self._stable_outcome(active, state),), (), ())
            return self._expand_frontier(active)

        if state.is_leaf_state:
            return self._expand_leaf_active(frontier)
        if top.mode == "init_wait":
            return self._expand_initial_transitions(frontier)
        if top.mode == "post_child_exit":
            return self._expand_parent_continuation(frontier)
        raise _internal_expansion_error(  # pragma: no cover
            "unsupported macro frontier stack frame mode: %r." % top.mode
        )

    def _expand_leaf_active(self, frontier: _MacroFrontier) -> _Expansion:
        transitions = frontier.stack[-1].state.transitions_from
        expanded = self._expand_ordered_candidates(
            frontier, transitions, is_initial=False
        )
        if expanded.outcomes:
            if frontier.stack[-1].state.is_stoppable:
                fallback = self._leaf_fallback_outcomes(
                    frontier, expanded.outcomes, expanded.failed
                )
                return _Expansion(
                    expanded.outcomes + fallback,
                    expanded.failed,
                    expanded.diagnostics,
                )
            return expanded
        if not frontier.stack[-1].state.is_stoppable:
            self._remember_failed_guard_requirements(frontier)
            return _Expansion(
                (), (frontier.condition,) + expanded.failed, expanded.diagnostics
            )
        fallback = self._leaf_fallback_outcomes(frontier, (), expanded.failed)
        return _Expansion(fallback, expanded.failed, expanded.diagnostics)

    def _expand_initial_transitions(self, frontier: _MacroFrontier) -> _Expansion:
        transitions = frontier.stack[-1].state.init_transitions
        expanded = self._expand_ordered_candidates(
            frontier, transitions, is_initial=True
        )
        if expanded.outcomes:
            return expanded
        self._remember_failed_guard_requirements(frontier)
        return _Expansion(
            (), (frontier.condition,) + expanded.failed, expanded.diagnostics
        )

    def _expand_parent_continuation(self, frontier: _MacroFrontier) -> _Expansion:
        transitions = frontier.stack[-1].state.transitions_from
        expanded = self._expand_ordered_candidates(
            frontier, transitions, is_initial=False
        )
        if expanded.outcomes:
            return expanded
        self._remember_failed_guard_requirements(frontier)
        return _Expansion(
            (), (frontier.condition,) + expanded.failed, expanded.diagnostics
        )

    def _expand_ordered_candidates(
        self,
        frontier: _MacroFrontier,
        transitions: Sequence[Transition],
        is_initial: bool,
    ) -> _Expansion:
        outcomes: List[_MacroOutcome] = []
        failed: List[BoolTemplate] = []
        diagnostics: List[BoolTemplate] = []
        for index, transition in enumerate(transitions):
            candidate = self._apply_priority_exclusion(frontier, outcomes, is_initial)
            candidate = self._apply_transition_trigger(
                candidate, transition, index, is_initial
            )
            if candidate.condition.kind == "false":
                continue
            branch_expansion = self._expand_triggered_transition(
                candidate, transition, is_initial
            )
            if branch_expansion.outcomes:
                outcomes.extend(branch_expansion.outcomes)
            else:
                self._remember_failed_guard_requirements(candidate)
                failed.append(candidate.condition)
            failed.extend(branch_expansion.failed)
            diagnostics.extend(branch_expansion.diagnostics)
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    def _apply_priority_exclusion(
        self,
        frontier: _MacroFrontier,
        accepted: Sequence[_MacroOutcome],
        is_initial: bool,
    ) -> _MacroFrontier:
        if not accepted:
            return frontier
        labels = tuple(outcome.label for outcome in accepted)
        accepted_condition = BoolTemplate.or_(
            *[
                BoolTemplate.atom("%s%s" % (_ACCEPTED_ATOM_PREFIX, label))
                for label in labels
            ]
        )
        event_paths = tuple(
            sorted(
                {event.path for outcome in accepted for event in outcome.used_events}
            )
        )
        guard_ids = tuple(
            sorted(
                {
                    guard.requirement_id
                    for outcome in accepted
                    for guard in outcome.guard_requirements
                }
            )
        )
        decision_id = "d%d" % self._decision_counter
        self._decision_counter += 1
        priority = PriorityExclusion(
            decision_id,
            "initial_priority" if is_initial else "transition_priority",
            labels,
            accepted_condition,
            event_paths,
            guard_ids,
        )
        return self._replace_frontier(
            frontier,
            condition=BoolTemplate.and_(
                frontier.condition, BoolTemplate.not_(accepted_condition)
            ),
            used_events=_merge_event_uses(
                frontier.used_events,
                self._event_uses_for_paths(event_paths, "negative", "priority"),
            ),
            priority_exclusions=frontier.priority_exclusions + (priority,),
        )

    def _apply_transition_trigger(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
        transition_index: int,
        is_initial: bool,
    ) -> _MacroFrontier:
        conditions = [frontier.condition]
        used_events = frontier.used_events
        guard_requirements = frontier.guard_requirements
        owner = frontier.stack[-1].state
        transition_label = self._transition_label(owner, transition, transition_index)
        if transition.event is not None:
            path = transition.event.path_name
            conditions.append(BoolTemplate.atom("%s%s" % (_EVENT_ATOM_PREFIX, path)))
            used_events = _merge_event_uses(
                used_events,
                self._event_uses_for_paths((path,), "positive", "trigger"),
            )
        if transition.guard is not None:
            if isinstance(transition.guard, Boolean):
                if transition.guard.value:
                    pass
                else:
                    conditions.append(BoolTemplate.false())
            else:
                requirement_id = "g%d" % self._guard_counter
                self._guard_counter += 1
                owner_path = ".".join(owner.path)
                guard = GuardRequirement(
                    requirement_id,
                    self._state_id(owner_path),
                    owner_path,
                    transition_label,
                    transition.guard,
                    "positive",
                    self._guard_reason(frontier, is_initial),
                    len(frontier.action_blocks),
                )
                guard_requirements = guard_requirements + (guard,)
                conditions.append(BoolTemplate.atom(guard.atom_name))
        return self._replace_frontier(
            frontier,
            condition=BoolTemplate.and_(*conditions),
            used_events=used_events,
            guard_requirements=guard_requirements,
        )

    def _expand_triggered_transition(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
        is_initial: bool,
    ) -> _Expansion:
        branches = (
            self._execute_initial_transition(frontier, transition)
            if is_initial
            else self._execute_transition(frontier, transition)
        )
        outcomes: List[_MacroOutcome] = []
        failed: List[BoolTemplate] = []
        diagnostics: List[BoolTemplate] = []
        for branch in branches:
            branch_expansion = self._expand_frontier(branch)
            outcomes.extend(branch_expansion.outcomes)
            failed.extend(branch_expansion.failed)
            diagnostics.extend(branch_expansion.diagnostics)
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    def _execute_initial_transition(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
    ) -> Tuple[_MacroFrontier, ...]:
        composite_frame = frontier.stack[-1]
        state = composite_frame.state
        current = self._record_transition_effect(frontier, state, transition)
        target_name = transition.to_state
        if not isinstance(target_name, str):
            raise _internal_expansion_error(  # pragma: no cover
                "initial transition target is not a child state name."
            )
        target_state = state.substates[target_name]
        if not target_state.is_pseudo:
            current = self._consume_plain_before_if_pending(current)
        entered = self._enter_state(current, target_state)
        result = []
        for item in entered:
            if any(frame.state is composite_frame.state for frame in item.stack):
                item = self._replace_frame(
                    item, composite_frame.state, "active", plain_before_pending=False
                )
            result.append(item)
        return tuple(result)

    def _execute_transition(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
    ) -> Tuple[_MacroFrontier, ...]:
        current_state = frontier.stack[-1].state
        current = frontier
        for on_exit in current_state.on_exits:
            current = self._record_func(
                current, current_state, on_exit, "state_action", "state_exit"
            )
        current = self._record_transition_effect(current, current_state, transition)
        current = self._replace_frontier(current, stack=current.stack[:-1])

        if transition.to_state == EXIT_STATE:
            current = self._clear_parent_plain_before_pending_after_pseudo_exit(
                current, current_state
            )
            return (self._finalize_exit_to_parent(current),)

        parent = current_state.parent
        if parent is None:
            raise _internal_expansion_error(  # pragma: no cover
                "non-exit transition source has no parent state."
            )
        target_name = transition.to_state
        if not isinstance(target_name, str):
            raise _internal_expansion_error(  # pragma: no cover
                "transition target is not a sibling state name."
            )
        target_state = parent.substates[target_name]
        if (
            current_state.is_pseudo
            and current.stack
            and current.stack[-1].state is parent
            and not target_state.is_pseudo
        ):
            current = self._consume_plain_before_if_pending(current)
        return self._enter_state(current, target_state)

    def _finalize_exit_to_parent(self, frontier: _MacroFrontier) -> _MacroFrontier:
        if not frontier.stack:
            return frontier
        parent = frontier.stack[-1].state
        current = frontier
        for on_during_after in parent.list_on_durings(aspect="after"):
            current = self._record_func(
                current,
                parent,
                on_during_after,
                "state_action",
                "plain_during_after",
            )
        if parent.is_root_state:
            for on_exit in parent.on_exits:
                current = self._record_func(
                    current, parent, on_exit, "state_action", "state_exit"
                )
            return self._replace_frontier(current, stack=())
        return self._replace_top(current, _FormalStackFrame(parent, "post_child_exit"))

    def _enter_state(
        self, frontier: _MacroFrontier, state: State
    ) -> Tuple[_MacroFrontier, ...]:
        current = self._replace_frontier(
            frontier,
            stack=frontier.stack + (_FormalStackFrame(state, "active"),),
        )
        for on_enter in state.on_enters:
            current = self._record_func(
                current, state, on_enter, "state_action", "state_enter"
            )

        if state.is_leaf_state:
            current = self._run_leaf_during(current, state)
            return (
                self._replace_top(current, _FormalStackFrame(state, "after_entry")),
            )
        return (
            self._replace_top(
                current,
                _FormalStackFrame(state, "init_wait", plain_before_pending=True),
            ),
        )

    def _run_leaf_during(
        self, frontier: _MacroFrontier, state: State
    ) -> _MacroFrontier:
        current = frontier
        for item in state.iter_on_during_aspect_recursively():
            owner, func = cast(Tuple[State, Union[OnAspect, OnStage]], item)
            if not isinstance(owner, State):
                raise _internal_expansion_error(  # pragma: no cover
                    "State.iter_on_during_aspect_recursively() yielded a non-State "
                    "owner when called without with_ids."
                )
            if not isinstance(func, (OnAspect, OnStage)):
                raise _internal_expansion_error(  # pragma: no cover
                    "State.iter_on_during_aspect_recursively() yielded a non-lifecycle "
                    "action when called without with_ids."
                )
            if isinstance(func, OnAspect):
                role = (
                    "aspect_during_before"
                    if func.aspect == "before"
                    else "aspect_during_after"
                )
                current = self._record_func(current, owner, func, "aspect_action", role)
            else:
                current = self._record_func(
                    current, owner, func, "state_action", "leaf_during"
                )
        return current

    def _consume_plain_before_if_pending(
        self, frontier: _MacroFrontier
    ) -> _MacroFrontier:
        if not frontier.stack:
            raise _internal_expansion_error(  # pragma: no cover
                "plain during-before consumption received an empty runtime stack."
            )
        frame = frontier.stack[-1]
        if not frame.plain_before_pending:
            return frontier
        current = frontier
        for on_during_before in frame.state.list_on_durings(aspect="before"):
            current = self._record_func(
                current,
                frame.state,
                on_during_before,
                "state_action",
                "plain_during_before",
            )
        return self._replace_top(
            current,
            _FormalStackFrame(frame.state, frame.mode, plain_before_pending=False),
        )

    def _clear_parent_plain_before_pending_after_pseudo_exit(
        self,
        frontier: _MacroFrontier,
        current_state: State,
    ) -> _MacroFrontier:
        if (
            current_state.is_pseudo
            and frontier.stack
            and frontier.stack[-1].state is current_state.parent
            and frontier.stack[-1].plain_before_pending
        ):
            parent = frontier.stack[-1]
            return self._replace_top(
                frontier,
                _FormalStackFrame(parent.state, parent.mode, False),
            )
        return frontier

    def _record_transition_effect(
        self,
        frontier: _MacroFrontier,
        owner: State,
        transition: Transition,
    ) -> _MacroFrontier:
        if not transition.effects:
            return frontier
        return self._append_action_block(
            frontier,
            owner,
            "transition_effect",
            "transition_effect",
            tuple(transition.effects),
            None,
            self._transition_label(
                owner, transition, self._transition_index(owner, transition)
            ),
            False,
        )

    def _record_func(
        self,
        frontier: _MacroFrontier,
        owner: State,
        func: object,
        block_kind: str,
        runtime_role: str,
    ) -> _MacroFrontier:
        if isinstance(func, (OnStage, OnAspect)) and func.is_ref:
            if func.ref is None:
                raise _internal_expansion_error(  # pragma: no cover
                    "action reference is missing its resolved target."
                )
            ref_owner = func.ref.parent if func.ref.parent is not None else owner
            return self._record_func(
                frontier, ref_owner, func.ref, block_kind, runtime_role
            )
        if not isinstance(func, (OnStage, OnAspect)):
            raise _internal_expansion_error(  # pragma: no cover
                "unsupported lifecycle action object reached macro expansion."
            )
        operations = () if func.is_abstract else tuple(func.operations)
        if not operations and not func.is_abstract:
            return frontier
        return self._append_action_block(
            frontier,
            owner,
            block_kind,
            runtime_role,
            operations,
            func.func_name,
            None,
            func.is_abstract,
        )

    def _append_action_block(
        self,
        frontier: _MacroFrontier,
        owner: State,
        block_kind: str,
        runtime_role: str,
        operations: Tuple[OperationStatement, ...],
        action_name: Optional[str],
        transition_label: Optional[str],
        is_abstract: bool,
    ) -> _MacroFrontier:
        owner_path = ".".join(owner.path)
        block = ActionBlock(
            block_kind,
            runtime_role,
            self._state_id(owner_path),
            owner_path,
            operations,
            action_name=action_name,
            transition_label=transition_label,
            is_abstract=is_abstract,
        )
        return self._replace_frontier(
            frontier,
            action_blocks=frontier.action_blocks + (block,),
        )

    def _leaf_fallback_outcomes(
        self,
        frontier: _MacroFrontier,
        accepted: Sequence[_MacroOutcome],
        failed: Sequence[BoolTemplate],
    ) -> Tuple[_MacroOutcome, ...]:
        condition = frontier.condition
        used_events = frontier.used_events
        priority_exclusions = frontier.priority_exclusions
        if accepted:
            labels = tuple(outcome.label for outcome in accepted)
            accepted_condition = BoolTemplate.or_(
                *[
                    BoolTemplate.atom("%s%s" % (_ACCEPTED_ATOM_PREFIX, label))
                    for label in labels
                ]
            )
            condition = BoolTemplate.and_(
                condition, BoolTemplate.not_(accepted_condition)
            )
            event_paths = tuple(
                sorted(
                    {
                        event.path
                        for outcome in accepted
                        for event in outcome.used_events
                    }
                )
            )
            guard_ids = tuple(
                sorted(
                    {
                        guard.requirement_id
                        for outcome in accepted
                        for guard in outcome.guard_requirements
                    }
                )
            )
            # These ids describe guards read by the excluded accepted paths.
            # They are witness/debug metadata only; the fallback truth source
            # remains ``condition`` plus ``not(accepted_condition)`` above.
            priority = PriorityExclusion(
                "fallback%d" % self._decision_counter,
                "fallback",
                labels,
                accepted_condition,
                event_paths,
                guard_ids,
            )
            self._decision_counter += 1
            priority_exclusions = priority_exclusions + (priority,)
            used_events = _merge_event_uses(
                used_events,
                self._event_uses_for_paths(event_paths, "negative", "fallback"),
            )
        failed_condition = BoolTemplate.or_(*failed)
        used_events = _merge_event_uses(
            used_events,
            self._event_uses_for_paths(
                _event_paths_from_condition(failed_condition), "negative", "fallback"
            ),
        )
        fallback_frontier = self._replace_frontier(
            frontier,
            condition=condition,
            used_events=used_events,
            priority_exclusions=priority_exclusions,
            case_kind=_CASE_KIND_FALLBACK,
        )
        fallback_frontier = self._run_leaf_during(
            fallback_frontier, frontier.stack[-1].state
        )
        active = self._replace_top(
            fallback_frontier,
            _FormalStackFrame(fallback_frontier.stack[-1].state, "after_entry"),
        )
        expansion = self._expand_frontier(active)
        if not expansion.outcomes:
            raise _internal_expansion_error(  # pragma: no cover
                "stable fallback did not produce a stable or terminal outcome."
            )
        failed_guard_requirements = self._guard_requirements_for_conditions(failed)
        return tuple(
            _MacroOutcome(
                outcome.label,
                outcome.target_state_id,
                outcome.target_state_path,
                outcome.condition,
                outcome.used_events,
                outcome.action_blocks,
                _merge_guard_requirements(
                    outcome.guard_requirements, failed_guard_requirements
                ),
                outcome.priority_exclusions,
                _CASE_KIND_FALLBACK,
                tuple(failed),
            )
            for outcome in expansion.outcomes
        )

    def _stable_outcome(self, frontier: _MacroFrontier, state: State) -> _MacroOutcome:
        path = ".".join(state.path)
        return _MacroOutcome(
            self._allocate_case_label(frontier.case_kind, path),
            self._state_id(path),
            path,
            frontier.condition,
            frontier.used_events,
            frontier.action_blocks,
            frontier.guard_requirements,
            frontier.priority_exclusions,
            frontier.case_kind,
        )

    def _terminate_outcome(self, frontier: _MacroFrontier) -> _MacroOutcome:
        return _MacroOutcome(
            self._allocate_case_label(frontier.case_kind, TERMINATE_CASE_PATH),
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            frontier.condition,
            frontier.used_events,
            frontier.action_blocks,
            frontier.guard_requirements,
            frontier.priority_exclusions,
            frontier.case_kind,
        )

    def _cases_from_outcomes(
        self, outcomes: Sequence[_MacroOutcome]
    ) -> Tuple[CycleCase, ...]:
        return tuple(
            CycleCase(
                outcome.case_kind,
                self.source.source_state_id,
                self.source.source_state_path,
                outcome.target_state_id,
                outcome.target_state_path,
                outcome.label,
                outcome.condition,
                outcome.action_blocks,
                used_events=outcome.used_events,
                guard_requirements=outcome.guard_requirements,
                priority_exclusions=outcome.priority_exclusions,
                failed_conditions=outcome.failed_conditions,
                domain=self.domain,
            )
            for outcome in outcomes
        )

    def _guard_reason(self, frontier: _MacroFrontier, is_initial: bool) -> str:
        if is_initial:
            return "initial_guard"
        frame = frontier.stack[-1]
        if frame.mode == "post_child_exit":
            return "parent_continuation_guard"
        if frame.state.is_pseudo:
            return "pseudo_guard"
        return "transition_guard"

    def _remember_failed_guard_requirements(self, frontier: _MacroFrontier) -> None:
        for guard in frontier.guard_requirements:
            self._failed_guard_requirements[guard.requirement_id] = guard

    def _guard_requirements_for_conditions(
        self, conditions: Sequence[BoolTemplate]
    ) -> Tuple[GuardRequirement, ...]:
        ids = {
            atom[len(_GUARD_ATOM_PREFIX) :]
            for condition in conditions
            for atom in condition.variables
            if atom.startswith(_GUARD_ATOM_PREFIX)
        }
        return tuple(
            self._failed_guard_requirements[item]
            for item in sorted(ids)
            if item in self._failed_guard_requirements
        )

    def _allocate_case_label(self, case_kind: str, target_path: str) -> str:
        ordinal = self._case_counters.get(case_kind, 0)
        self._case_counters[case_kind] = ordinal + 1
        return "%s::%s::%s::%d" % (
            self.source.source_state_path,
            case_kind,
            target_path,
            ordinal,
        )

    def _transition_label(
        self, owner: State, transition: Transition, index: int
    ) -> str:
        target = (
            "[*]" if transition.to_state == EXIT_STATE else str(transition.to_state)
        )
        return "%s::%d::%s->%s" % (
            ".".join(owner.path),
            index,
            transition.from_state,
            target,
        )

    @staticmethod
    def _transition_index(owner: State, transition: Transition) -> int:
        for transitions in (owner.init_transitions, owner.transitions_from):
            for index, item in enumerate(transitions):
                if item is transition:
                    return index
        raise _internal_expansion_error(  # pragma: no cover
            "transition object was not found on its owner state."
        )

    def _event_uses_for_paths(
        self, paths: Sequence[str], polarity: str, reason: str
    ) -> Tuple[EventUse, ...]:
        result = []
        for path in sorted(set(paths)):
            try:
                entry = self.domain.event_by_path(path)
            except InvalidBmcDomain as err:
                # InvalidBmcDomain: event paths in transition triggers or priority
                # masks must exist in the domain snapshot.
                raise InvalidBmcEncoding(str(err)) from err
            result.append(EventUse(entry.id, entry.path, polarity, reason))
        return tuple(result)

    def _state_id(self, path: str) -> int:
        try:
            return self.domain.state_path_to_id(path)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: model state paths encountered by the expander
            # must exist in the domain snapshot built from the same model.
            raise InvalidBmcEncoding(str(err)) from err

    def _frontier_signature(self, frontier: _MacroFrontier) -> Tuple[object, ...]:
        return (
            tuple(
                (frame.state.path, frame.mode, frame.plain_before_pending)
                for frame in frontier.stack
            ),
            frontier.case_kind,
        )

    def _replace_frontier(
        self, frontier: _MacroFrontier, **updates: object
    ) -> _MacroFrontier:
        values = {
            "stack": frontier.stack,
            "condition": frontier.condition,
            "used_events": frontier.used_events,
            "action_blocks": frontier.action_blocks,
            "guard_requirements": frontier.guard_requirements,
            "priority_exclusions": frontier.priority_exclusions,
            "case_kind": frontier.case_kind,
            "path_signatures": frontier.path_signatures,
            "depth": frontier.depth,
        }
        values.update(updates)
        return _MacroFrontier(**values)

    def _replace_top(
        self, frontier: _MacroFrontier, frame: _FormalStackFrame
    ) -> _MacroFrontier:
        return self._replace_frontier(frontier, stack=frontier.stack[:-1] + (frame,))

    def _replace_frame(
        self,
        frontier: _MacroFrontier,
        state: State,
        mode: str,
        plain_before_pending: bool,
    ) -> _MacroFrontier:
        frames = []
        replaced = False
        for frame in frontier.stack:
            if frame.state is state and not replaced:
                frames.append(_FormalStackFrame(state, mode, plain_before_pending))
                replaced = True
            else:
                frames.append(frame)
        return self._replace_frontier(frontier, stack=tuple(frames))


def _path_to_root(state: State) -> Tuple[State, ...]:
    result = []
    current = state
    while current is not None:
        result.append(current)
        current = current.parent
    return tuple(reversed(result))


def _merge_event_uses(*groups: Sequence[EventUse]) -> Tuple[EventUse, ...]:
    by_key = {}
    for group in groups:
        for item in group:
            by_key[(item.event_id, item.path, item.polarity, item.reason)] = item
    return tuple(by_key[key] for key in sorted(by_key))


def _merge_guard_requirements(
    *groups: Sequence[GuardRequirement],
) -> Tuple[GuardRequirement, ...]:
    by_id = {}
    for group in groups:
        for item in group:
            by_id[item.requirement_id] = item
    return tuple(by_id[key] for key in sorted(by_id))


def _event_paths_from_condition(condition: BoolTemplate) -> Tuple[str, ...]:
    return tuple(
        sorted(
            atom[len(_EVENT_ATOM_PREFIX) :]
            for atom in condition.variables
            if atom.startswith(_EVENT_ATOM_PREFIX)
        )
    )


__all__ = [
    "MacroExpansionOptions",
    "expand_macro_step_cases",
]
