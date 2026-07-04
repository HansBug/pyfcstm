"""Macro-step expansion aligned with the FCSTM simulation runtime.

The expansion layer turns a :class:`pyfcstm.bmc.source.MacroStepSource` into a
solver-independent :class:`pyfcstm.bmc.macro.MacroStepFormal`.  It mirrors the
cycle-level control flow of :class:`pyfcstm.simulate.SimulationRuntime` without
creating Z3 symbols or verify-registry entries.  The output conditions remain
bare case predicates; later relation builders compose the source-state guard and
lower each case as an implication.  Ordered transitions use accepted
continuations for priority masks, and event reads used only by those masks are
kept in :class:`pyfcstm.bmc.macro.EventUse` metadata for witness explanations.

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
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from pyfcstm.bmc.domain import STATE_TERMINATE_ID, BmcDomain
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcDomain, InvalidBmcEncoding
from pyfcstm.bmc.macro import (
    BoolTemplate,
    CycleCase,
    EventUse,
    MacroStepFormal,
    VarUpdate,
    build_semantic_delta_case,
    diagnostic_absorb_case,
    terminated_absorb_case,
)
from pyfcstm.bmc.source import TERMINATE_CASE_PATH, MacroStepSource
from pyfcstm.dsl import EXIT_STATE
from pyfcstm.model import (
    BinaryOp,
    Boolean,
    ConditionalOp,
    Expr,
    Float,
    IfBlock,
    Integer,
    OnAspect,
    OnStage,
    Operation,
    OperationStatement,
    State,
    StateMachine,
    Transition,
    UFunc,
    UnaryOp,
    Variable,
)

_CASE_KIND_FALLBACK = "fallback"
_CASE_KIND_INITIAL = "initial"
_CASE_KIND_TRANSITION = "transition"
_EVENT_ATOM_PREFIX = "event:"
_GUARD_ATOM_PREFIX = "guard:"
_PRE_VAR_PREFIX = "pre:"


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
    :param partition_max_assignments: Truth-table assignment budget for the
        current solver-independent checker, defaults to ``4096``.
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
                self.partition_max_assignments,
                "partition_max_assignments",
            ),
        )
        if not isinstance(self.verify_partition, bool):
            raise InvalidBmcEncoding("verify_partition must be a boolean.")


@dataclass(frozen=True)
class _LinearExpr:
    coeffs: Mapping[str, float]
    const: float = 0.0

    @classmethod
    def variable(cls, name: str) -> "_LinearExpr":
        return cls({name: 1.0}, 0.0)

    @classmethod
    def const_value(cls, value: float) -> "_LinearExpr":
        return cls({}, float(value))

    def add(self, other: "_LinearExpr") -> "_LinearExpr":
        coeffs = dict(self.coeffs)
        for name, coeff in other.coeffs.items():
            coeffs[name] = coeffs.get(name, 0.0) + coeff
            if coeffs[name] == 0:
                del coeffs[name]
        return _LinearExpr(coeffs, self.const + other.const)

    def mul_const(self, value: float) -> "_LinearExpr":
        return _LinearExpr(
            {name: coeff * value for name, coeff in self.coeffs.items()},
            self.const * value,
        )

    def to_text(self) -> str:
        parts = []
        for name in sorted(self.coeffs):
            coeff = self.coeffs[name]
            if coeff == 1:
                part = name
            elif coeff == -1:
                part = "-%s" % name
            else:
                part = "%s * %s" % (_format_number(coeff), name)
            parts.append(part)
        const = self.const
        if const:
            const_text = _format_number(abs(const))
            if parts:
                parts.append(("+ " if const > 0 else "- ") + const_text)
            else:
                parts.append(_format_number(const))
        if not parts:
            return "0"
        text = parts[0]
        for part in parts[1:]:
            if part.startswith("+ ") or part.startswith("- "):
                text = "%s %s" % (text, part)
            elif part.startswith("-"):
                text = "%s - %s" % (text, part[1:])
            else:
                text = "%s + %s" % (text, part)
        return text


@dataclass(frozen=True)
class _ValueTemplate:
    text: str
    linear: Optional[_LinearExpr] = None

    @classmethod
    def variable(cls, name: str) -> "_ValueTemplate":
        text = "%s%s" % (_PRE_VAR_PREFIX, name)
        return cls(text, _LinearExpr.variable(text))

    @classmethod
    def const_value(cls, value: float) -> "_ValueTemplate":
        text = _format_number(value)
        return cls(text, _LinearExpr.const_value(value))

    def binary(self, op: str, other: "_ValueTemplate") -> "_ValueTemplate":
        if op == "+" and self.linear is not None and other.linear is not None:
            return _value_from_linear(self.linear.add(other.linear))
        if op == "-" and self.linear is not None and other.linear is not None:
            return _value_from_linear(self.linear.add(other.linear.mul_const(-1)))
        if op == "*":
            if self.linear is not None and not self.linear.coeffs:
                return (
                    _value_from_linear(other.linear.mul_const(self.linear.const))
                    if other.linear is not None
                    else _ValueTemplate("%s * %s" % (self.text, other.text))
                )
            if other.linear is not None and not other.linear.coeffs:
                return (
                    _value_from_linear(self.linear.mul_const(other.linear.const))
                    if self.linear is not None
                    else _ValueTemplate("%s * %s" % (self.text, other.text))
                )
        if (
            op == "/"
            and other.linear is not None
            and not other.linear.coeffs
            and other.linear.const != 0
            and self.linear is not None
        ):
            return _value_from_linear(self.linear.mul_const(1.0 / other.linear.const))
        return _ValueTemplate("%s %s %s" % (self.text, op, other.text))

    def unary(self, op: str) -> "_ValueTemplate":
        if op == "+":
            return self
        if op == "-" and self.linear is not None:
            return _value_from_linear(self.linear.mul_const(-1))
        return _ValueTemplate("%s%s" % (op, self.text))


def _format_number(value: float) -> str:
    if int(value) == value:
        return str(int(value))
    return repr(float(value))


def _value_from_linear(linear: _LinearExpr) -> _ValueTemplate:
    return _ValueTemplate(linear.to_text(), linear)


@dataclass(frozen=True)
class _FormalStackFrame:
    state: State
    mode: str
    plain_before_pending: bool = False


@dataclass(frozen=True)
class _Store:
    values: Mapping[str, _ValueTemplate]


@dataclass(frozen=True)
class _MacroFrontier:
    stack: Tuple[_FormalStackFrame, ...]
    store: _Store
    condition: BoolTemplate
    used_events: Tuple[EventUse, ...]
    case_kind: str
    path_signatures: Tuple[Tuple[object, ...], ...] = ()
    depth: int = 0


@dataclass(frozen=True)
class _MacroOutcome:
    target_state_id: int
    target_state_path: str
    condition: BoolTemplate
    store: _Store
    used_events: Tuple[EventUse, ...]
    case_kind: str
    failed_conditions: Tuple[BoolTemplate, ...] = ()


@dataclass(frozen=True)
class _Expansion:
    outcomes: Tuple[_MacroOutcome, ...]
    failed: Tuple[BoolTemplate, ...]
    diagnostics: Tuple[BoolTemplate, ...]


@dataclass(frozen=True)
class _Branch:
    condition: BoolTemplate
    store: _Store


class _Expander:
    def __init__(self, source: MacroStepSource, options: MacroExpansionOptions):
        if source.domain is None:
            raise InvalidBmcEncoding("macro-step source must be domain-backed.")
        if not isinstance(source.domain, BmcDomain):
            raise InvalidBmcEncoding("source.domain must be BmcDomain.")
        self.source = source
        self.domain = source.domain
        self.options = options
        model = getattr(self.domain, "model", None)
        if not isinstance(model, StateMachine):
            raise InvalidBmcEncoding(
                "source domain must preserve the state machine model for expansion."
            )
        self.model = model
        self.states_by_path = {
            ".".join(state.path): state for state in model.walk_states()
        }
        self.event_entries = {entry.path: entry for entry in self.domain.events}
        self.state_ids = {entry.path: entry.id for entry in self.domain.states}

    def expand(self) -> MacroStepFormal:
        if self.source.kind == "terminated":
            return MacroStepFormal(self.source, (terminated_absorb_case(self.domain),))
        if self.source.kind == "diagnostic":
            return MacroStepFormal(self.source, (diagnostic_absorb_case(self.domain),))

        initial_frontiers = self._frontiers_from_source()
        expansion = self._merge_expansions(
            self._expand_frontier(frontier) for frontier in initial_frontiers
        )
        if self.source.kind == "stable_leaf" and expansion.diagnostics:
            raise BmcBuildError("stable macro expansion produced build diagnostics.")

        success_cases = self._cases_from_outcomes(expansion.outcomes)
        delta_cases = ()
        diagnostics = expansion.diagnostics
        if self.source.kind == "entry":
            delta = build_semantic_delta_case(
                self.domain,
                self.source,
                success_cases,
                diagnostics,
                expansion.failed,
            )
            delta_cases = (delta,)

        formal = MacroStepFormal(
            self.source,
            success_cases,
            delta_cases,
            diagnostics,
        )
        if self.options.verify_partition:
            formal.verify_partition(
                max_assignments=self.options.partition_max_assignments
            )
        return formal

    @staticmethod
    def _merge_expansions(expansions: Iterable[_Expansion]) -> _Expansion:
        outcomes = []
        failed = []
        diagnostics = []
        for expansion in expansions:
            outcomes.extend(expansion.outcomes)
            failed.extend(expansion.failed)
            diagnostics.extend(expansion.diagnostics)
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    def _frontiers_from_source(self) -> Tuple[_MacroFrontier, ...]:
        store = _Store(
            {
                entry.name: _ValueTemplate.variable(entry.name)
                for entry in self.domain.variables
            }
        )
        state = self._source_state()
        if self.source.kind == "stable_leaf":
            stack = tuple(
                _FormalStackFrame(item, "active") for item in _path_to_root(state)
            )
            return (
                _MacroFrontier(
                    stack, store, BoolTemplate.true(), (), _CASE_KIND_TRANSITION
                ),
            )

        if self.source.kind != "entry":
            raise InvalidBmcEncoding("unsupported source kind: %r." % self.source.kind)
        if state.is_root_state:
            base = _MacroFrontier(
                (), store, BoolTemplate.true(), (), _CASE_KIND_INITIAL
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
                tuple(stack), store, BoolTemplate.true(), (), _CASE_KIND_INITIAL
            ),
        )

    def _source_state(self) -> State:
        state = self.states_by_path.get(self.source.source_state_path)
        if state is None:
            raise InvalidBmcEncoding("source state is not present in the model.")
        return state

    def _expand_frontier(self, frontier: _MacroFrontier) -> _Expansion:
        if frontier.depth >= self.options.max_micro_steps:
            return _Expansion((), (), (frontier.condition,))
        if len(frontier.stack) > self.options.max_stack_depth:
            return _Expansion((), (), (frontier.condition,))
        signature = self._frontier_signature(frontier)
        if signature in frontier.path_signatures:
            return _Expansion((), (frontier.condition,), ())
        frontier = self._replace_frontier(
            frontier,
            path_signatures=frontier.path_signatures + (signature,),
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
        return _Expansion((), (), (frontier.condition,))

    def _expand_leaf_active(self, frontier: _MacroFrontier) -> _Expansion:
        accelerated = self._try_expand_pseudo_threshold_loop(frontier)
        if accelerated is not None:
            return accelerated

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
        return _Expansion(
            (), (frontier.condition,) + expanded.failed, expanded.diagnostics
        )

    def _try_expand_pseudo_threshold_loop(
        self, frontier: _MacroFrontier
    ) -> Optional[_Expansion]:
        """Return an accelerated expansion for simple monotone pseudo loops.

        The runtime validation worklist can accept a pseudo self-loop that
        monotonically increments an integer variable until a complementary exit
        guard becomes true.  Symbolic recursion cannot prove that convergence
        by path-signature repetition alone because each loop iteration changes
        the symbolic store.  This helper recognizes that narrow runtime-safe
        pattern and summarizes the finite loop as a threshold writeback before
        executing the ordinary exit transition.

        :param frontier: Current macro frontier whose stack top may be a pseudo
            state.
        :type frontier: _MacroFrontier
        :return: Accelerated expansion, or ``None`` if the frontier does not
            match the supported monotone pseudo-loop shape.
        :rtype: Optional[_Expansion]
        """
        top = frontier.stack[-1]
        state = top.state
        if not state.is_pseudo:
            return None
        if not self._pseudo_state_is_accelerable(state):
            return None
        transitions = tuple(state.transitions_from)
        if len(transitions) != 2:
            return None
        first, second = transitions
        first_loop = self._accelerable_pseudo_loop(first, state)
        second_loop = self._accelerable_pseudo_loop(second, state)
        if first_loop is not None and second_loop is None:
            exit_transition = second
            loop_has_priority = True
            variable_name, increment, threshold = first_loop
        elif second_loop is not None and first_loop is None:
            exit_transition = first
            loop_has_priority = False
            variable_name, increment, threshold = second_loop
        else:
            return None
        if not self._is_complementary_threshold_exit(
            exit_transition, state, variable_name, threshold
        ):
            return None

        loop_trigger = self._threshold_store_condition(
            frontier.store, variable_name, "lt", threshold
        )
        exit_trigger = self._threshold_store_condition(
            frontier.store, variable_name, "ge", threshold
        )
        if loop_has_priority:
            loop_condition = loop_trigger
            exit_condition = BoolTemplate.not_(loop_trigger)
        else:
            loop_condition = BoolTemplate.not_(exit_trigger)
            exit_condition = exit_trigger

        loop_store = dict(frontier.store.values)
        loop_store[variable_name] = _threshold_reached_value(
            frontier.store.values[variable_name],
            threshold,
            increment,
        )
        accelerated_loop = self._replace_frontier(
            frontier,
            condition=BoolTemplate.and_(frontier.condition, loop_condition),
            store=_Store(loop_store),
        )
        loop_expansion = (
            _Expansion((), (), ())
            if _has_direct_atom_contradiction(accelerated_loop.condition)
            else self._expand_triggered_transition(accelerated_loop, exit_transition)
        )

        direct_exit = self._replace_frontier(
            frontier,
            condition=BoolTemplate.and_(frontier.condition, exit_condition),
        )
        if _has_direct_atom_contradiction(direct_exit.condition):
            exit_expansion = _Expansion((), (), ())
        else:
            exit_expansion = self._expand_triggered_transition(
                direct_exit, exit_transition
            )

        return self._merge_expansions((loop_expansion, exit_expansion))

    def _expand_triggered_transition(
        self, frontier: _MacroFrontier, transition: Transition
    ) -> _Expansion:
        """Execute a transition whose trigger is already part of ``frontier``.

        :param frontier: Frontier with the selected transition condition already
            included.
        :type frontier: _MacroFrontier
        :param transition: Transition to execute.
        :type transition: pyfcstm.model.Transition
        :return: Expansion produced by executing the transition and continuing
            to a stable boundary.
        :rtype: _Expansion
        """
        outcomes: List[_MacroOutcome] = []
        failed: List[BoolTemplate] = []
        diagnostics: List[BoolTemplate] = []
        for branch in self._execute_transition(frontier, transition):
            branch_expansion = self._expand_frontier(branch)
            outcomes.extend(branch_expansion.outcomes)
            failed.extend(branch_expansion.failed)
            diagnostics.extend(branch_expansion.diagnostics)
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    @staticmethod
    def _pseudo_state_is_accelerable(state: State) -> bool:
        """Return whether a pseudo state has no lifecycle side effects.

        :param state: Pseudo state candidate.
        :type state: pyfcstm.model.State
        :return: Whether the state can be summarized without losing lifecycle
            behavior.
        :rtype: bool
        """
        return not (
            state.on_enters
            or state.on_exits
            or state.on_durings
            or state.on_during_aspects
        )

    def _accelerable_pseudo_loop(
        self, transition: Transition, state: State
    ) -> Optional[Tuple[str, int, int]]:
        """Extract the integer threshold pattern from a pseudo self-loop.

        :param transition: Candidate self-loop transition.
        :type transition: pyfcstm.model.Transition
        :param state: Pseudo state that owns the transition.
        :type state: pyfcstm.model.State
        :return: ``(variable_name, increment, threshold)`` for integer forms
            equivalent to ``x < K`` plus ``x = x + step`` loops, or ``None``
            for unsupported shapes.
        :rtype: Optional[Tuple[str, int, int]]
        """
        if transition.from_state != state.name or transition.to_state != state.name:
            return None
        if transition.event is not None:
            return None
        guard = _integer_threshold_guard(transition.guard)
        if guard is None:
            return None
        variable_name, relation, threshold = guard
        if relation != "lt":
            return None
        if not self._is_int_variable(variable_name):
            return None
        if len(transition.effects) != 1:
            return None
        effect = transition.effects[0]
        increment = _positive_integer_increment_effect(effect, variable_name)
        if increment is None:
            return None
        return variable_name, increment, threshold

    def _is_complementary_threshold_exit(
        self,
        transition: Transition,
        state: State,
        variable_name: str,
        threshold: int,
    ) -> bool:
        """Return whether ``transition`` exits once the loop threshold is met.

        :param transition: Candidate exit transition.
        :type transition: pyfcstm.model.Transition
        :param state: Pseudo state that owns the transition.
        :type state: pyfcstm.model.State
        :param variable_name: Integer variable advanced by the loop.
        :type variable_name: str
        :param threshold: Loop threshold.
        :type threshold: int
        :return: Whether the transition has an integer guard equivalent to
            ``x >= K`` and leaves the pseudo state.
        :rtype: bool
        """
        if transition.from_state != state.name or transition.to_state == state.name:
            return False
        if transition.event is not None:
            return False
        guard = _integer_threshold_guard(transition.guard)
        if guard is None:
            return False
        exit_variable_name, relation, exit_threshold = guard
        return (
            exit_variable_name == variable_name
            and relation == "ge"
            and exit_threshold == threshold
        )

    def _threshold_store_condition(
        self,
        store: _Store,
        variable_name: str,
        relation: str,
        threshold: int,
    ) -> BoolTemplate:
        """Build a normalized threshold condition over the symbolic store.

        :param store: Current symbolic variable store.
        :type store: _Store
        :param variable_name: Persistent integer variable to compare.
        :type variable_name: str
        :param relation: ``"lt"`` for ``x < threshold`` or ``"ge"`` for
            ``x >= threshold``.
        :type relation: str
        :param threshold: Integer threshold.
        :type threshold: int
        :return: Boolean recipe for the normalized comparison.
        :rtype: pyfcstm.bmc.macro.BoolTemplate
        :raises BmcBuildError: If the variable is missing or ``relation`` is
            unsupported.
        """
        if variable_name not in store.values:
            raise BmcBuildError("unknown threshold variable %r." % variable_name)
        if relation == "lt":
            return _comparison_condition(
                store.values[variable_name],
                "<",
                _ValueTemplate.const_value(threshold),
            )
        if relation == "ge":
            return _comparison_condition(
                store.values[variable_name],
                ">=",
                _ValueTemplate.const_value(threshold),
            )
        raise BmcBuildError("unsupported threshold relation %r." % relation)

    def _is_int_variable(self, variable_name: str) -> bool:
        """Return whether ``variable_name`` is a persistent integer variable.

        :param variable_name: Candidate persistent variable name.
        :type variable_name: str
        :return: Whether the BMC domain declares it as ``int``.
        :rtype: bool
        """
        try:
            entry = self.domain.variable_by_name(variable_name)
        except InvalidBmcDomain:
            return False
        return entry.declared_type == "int"

    def _expand_ordered_candidates(
        self,
        frontier: _MacroFrontier,
        transitions: Sequence[Transition],
        *,
        is_initial: bool,
    ) -> _Expansion:
        outcomes: List[_MacroOutcome] = []
        failed: List[BoolTemplate] = []
        diagnostics: List[BoolTemplate] = []
        previous_accepted: List[BoolTemplate] = []
        previous_event_uses: List[EventUse] = []
        for transition in transitions:
            raw, raw_events = self._transition_trigger(
                transition, frontier.store, is_initial=is_initial
            )
            candidate = self._replace_frontier(
                frontier,
                condition=BoolTemplate.and_(frontier.condition, raw),
                used_events=_merge_event_uses(frontier.used_events, raw_events),
            )
            branches = (
                self._execute_initial_transition(candidate, transition)
                if is_initial
                else self._execute_transition(candidate, transition)
            )
            candidate_outcomes: List[_MacroOutcome] = []
            candidate_failed: List[BoolTemplate] = []
            for branch in branches:
                branch_expansion = self._expand_frontier(branch)
                candidate_outcomes.extend(branch_expansion.outcomes)
                candidate_failed.extend(branch_expansion.failed)
                diagnostics.extend(branch_expansion.diagnostics)
            accepted = BoolTemplate.or_(
                *[item.condition for item in candidate_outcomes]
            )
            priority = BoolTemplate.and_(
                *[BoolTemplate.not_(item) for item in previous_accepted]
            )
            priority_events = tuple(
                EventUse(item.event_id, item.path, "negative", "priority")
                for item in previous_event_uses
            )
            for outcome in candidate_outcomes:
                outcomes.append(
                    _MacroOutcome(
                        outcome.target_state_id,
                        outcome.target_state_path,
                        BoolTemplate.and_(priority, outcome.condition),
                        outcome.store,
                        _merge_event_uses(outcome.used_events, priority_events),
                        outcome.case_kind,
                        outcome.failed_conditions,
                    )
                )
            failed.extend(candidate_failed)
            previous_accepted.append(accepted)
            previous_event_uses = list(
                _merge_event_uses(
                    previous_event_uses,
                    tuple(
                        EventUse(item.event_id, item.path, "negative", "priority")
                        for item in raw_events
                    ),
                )
            )
            accepted_event_uses = tuple(
                item
                for outcome in candidate_outcomes
                for item in outcome.used_events
                if item.polarity == "positive"
            )
            previous_event_uses = list(
                _merge_event_uses(
                    previous_event_uses,
                    accepted_event_uses,
                    _event_uses_from_condition(accepted, self.domain),
                )
            )
        return _Expansion(tuple(outcomes), tuple(failed), tuple(diagnostics))

    def _transition_trigger(
        self,
        transition: Transition,
        store: _Store,
        *,
        is_initial: bool,
    ) -> Tuple[BoolTemplate, Tuple[EventUse, ...]]:
        conditions = []
        event_uses = []
        if transition.event is not None:
            atom = BoolTemplate.atom(_event_atom(transition.event.path_name))
            conditions.append(atom)
            entry = self.event_entries.get(transition.event.path_name)
            if entry is None:
                raise InvalidBmcEncoding("transition event is missing from BMC domain.")
            reason = "descent" if is_initial else "trigger"
            event_uses.append(EventUse(entry.id, entry.path, "positive", reason))
        if transition.guard is not None:
            conditions.append(self._condition_from_expr(transition.guard, store))
        return BoolTemplate.and_(*conditions), tuple(event_uses)

    def _execute_initial_transition(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
    ) -> Tuple[_MacroFrontier, ...]:
        top = frontier.stack[-1]
        if not isinstance(transition.to_state, str):
            raise BmcBuildError("initial transition target must be a child state.")
        target = top.state.substates[transition.to_state]
        branches = self._execute_operation_block(frontier, transition.effects)
        result = []
        for branch in branches:
            current_items = (branch,)
            if not target.is_pseudo:
                current_items = self._consume_plain_before_if_pending(branch)
            for current in current_items:
                result.extend(self._enter_state(current, target))
        return tuple(result)

    def _execute_transition(
        self,
        frontier: _MacroFrontier,
        transition: Transition,
    ) -> Tuple[_MacroFrontier, ...]:
        current_state = frontier.stack[-1].state
        branches = (frontier,)
        for on_exit in current_state.on_exits:
            branches = self._flat_map(
                branches, lambda item, func=on_exit: self._execute_func(item, func)
            )
        branches = self._flat_map(
            branches,
            lambda item: self._execute_operation_block(item, transition.effects),
        )
        result = []
        for branch in branches:
            popped = self._replace_frontier(branch, stack=branch.stack[:-1])
            if transition.to_state == EXIT_STATE:
                if current_state.is_pseudo:
                    popped = self._clear_parent_plain_before_pending_after_pseudo_exit(
                        popped, current_state
                    )
                result.extend(self._finalize_exit_to_parent(popped))
                continue
            if not isinstance(transition.to_state, str):
                raise BmcBuildError("transition target must be a sibling state.")
            if current_state.parent is None:
                raise BmcBuildError("root transition cannot target a sibling state.")
            target_state = current_state.parent.substates[transition.to_state]
            current = popped
            if (
                current_state.is_pseudo
                and current.stack
                and current.stack[-1].state is current_state.parent
                and not target_state.is_pseudo
            ):
                for consumed in self._consume_plain_before_if_pending(current):
                    result.extend(self._enter_state(consumed, target_state))
                continue
            result.extend(self._enter_state(current, target_state))
        return tuple(result)

    def _enter_state(
        self, frontier: _MacroFrontier, state: State
    ) -> Tuple[_MacroFrontier, ...]:
        entered = self._replace_frontier(
            frontier, stack=frontier.stack + (_FormalStackFrame(state, "active"),)
        )
        branches = (entered,)
        for on_enter in state.on_enters:
            branches = self._flat_map(
                branches, lambda item, func=on_enter: self._execute_func(item, func)
            )
        result = []
        for branch in branches:
            if state.is_leaf_state:
                during_branches = self._run_leaf_during(branch, state)
                result.extend(
                    self._replace_top(item, _FormalStackFrame(state, "after_entry"))
                    for item in during_branches
                )
            else:
                result.append(
                    self._replace_top(
                        branch,
                        _FormalStackFrame(
                            state, "init_wait", plain_before_pending=True
                        ),
                    )
                )
        return tuple(result)

    def _finalize_exit_to_parent(
        self, frontier: _MacroFrontier
    ) -> Tuple[_MacroFrontier, ...]:
        if not frontier.stack:
            return (frontier,)
        parent = frontier.stack[-1].state
        branches = (frontier,)
        for on_during_after in parent.list_on_durings(aspect="after"):
            branches = self._flat_map(
                branches,
                lambda item, func=on_during_after: self._execute_func(item, func),
            )
        if parent.is_root_state:
            for on_exit in parent.on_exits:
                branches = self._flat_map(
                    branches, lambda item, func=on_exit: self._execute_func(item, func)
                )
            return tuple(self._replace_frontier(item, stack=()) for item in branches)
        return tuple(
            self._replace_top(item, _FormalStackFrame(parent, "post_child_exit"))
            for item in branches
        )

    def _leaf_fallback_outcomes(
        self,
        frontier: _MacroFrontier,
        accepted: Sequence[_MacroOutcome],
        failed: Sequence[BoolTemplate],
    ) -> Tuple[_MacroOutcome, ...]:
        fallback_events: Tuple[EventUse, ...] = ()
        if accepted:
            accepted_condition = BoolTemplate.or_(
                *[item.condition for item in accepted]
            )
            condition = BoolTemplate.and_(
                frontier.condition,
                BoolTemplate.not_(accepted_condition),
            )
            fallback_events = _event_uses_from_condition(
                accepted_condition,
                self.domain,
                polarity="negative",
                reason="fallback",
            )
        else:
            condition = frontier.condition
        failed_events = _event_uses_from_condition(
            BoolTemplate.or_(*failed),
            self.domain,
            polarity="negative",
            reason="fallback",
        )
        fallback_frontier = self._replace_frontier(
            frontier,
            condition=condition,
            case_kind=_CASE_KIND_FALLBACK,
        )
        branches = self._run_leaf_during(fallback_frontier, frontier.stack[-1].state)
        outcomes = []
        for branch in branches:
            active = self._replace_top(
                branch, _FormalStackFrame(branch.stack[-1].state, "after_entry")
            )
            expansion = self._expand_frontier(active)
            outcomes.extend(expansion.outcomes)
        if not outcomes:
            raise BmcBuildError("stable fallback did not produce an outcome.")
        return tuple(
            _MacroOutcome(
                outcome.target_state_id,
                outcome.target_state_path,
                outcome.condition,
                outcome.store,
                _merge_event_uses(
                    outcome.used_events,
                    fallback_events,
                    failed_events,
                ),
                _CASE_KIND_FALLBACK,
                tuple(failed),
            )
            for outcome in outcomes
        )

    def _run_leaf_during(
        self, frontier: _MacroFrontier, state: State
    ) -> Tuple[_MacroFrontier, ...]:
        branches = (frontier,)
        for item in state.iter_on_during_aspect_recursively():
            func = item[-1]
            branches = self._flat_map(
                branches, lambda item, action=func: self._execute_func(item, action)
            )
        return tuple(branches)

    def _consume_plain_before_if_pending(
        self, frontier: _MacroFrontier
    ) -> Tuple[_MacroFrontier, ...]:
        frame = frontier.stack[-1]
        if not frame.plain_before_pending:
            return (frontier,)
        branches = (frontier,)
        # Plain boundary ``during before`` actions live in ``on_durings``.
        # Descendant aspect actions (``>> during before``) are intentionally
        # executed later by ``_run_leaf_during``, matching SimulationRuntime.
        for on_during_before in frame.state.list_on_durings(aspect="before"):
            branches = self._flat_map(
                branches,
                lambda item, func=on_during_before: self._execute_func(item, func),
            )
        return tuple(
            self._replace_top(
                current,
                _FormalStackFrame(frame.state, frame.mode, plain_before_pending=False),
            )
            for current in branches
        )

    def _clear_parent_plain_before_pending_after_pseudo_exit(
        self,
        frontier: _MacroFrontier,
        current_state: State,
    ) -> _MacroFrontier:
        if (
            frontier.stack
            and frontier.stack[-1].state is current_state.parent
            and frontier.stack[-1].plain_before_pending
        ):
            parent = frontier.stack[-1]
            return self._replace_top(
                frontier, _FormalStackFrame(parent.state, parent.mode, False)
            )
        return frontier

    def _execute_func(
        self, frontier: _MacroFrontier, func: object
    ) -> Tuple[_MacroFrontier, ...]:
        if isinstance(func, (OnStage, OnAspect)) and func.is_ref:
            if func.ref is None:
                raise BmcBuildError("action reference is missing a target.")
            return self._execute_func(frontier, func.ref)
        if not isinstance(func, (OnStage, OnAspect)):
            raise BmcBuildError("unsupported lifecycle action type.")
        if func.is_abstract:
            return (frontier,)
        return self._execute_operation_block(frontier, func.operations)

    def _execute_operation_block(
        self,
        frontier: _MacroFrontier,
        operations: Sequence[OperationStatement],
    ) -> Tuple[_MacroFrontier, ...]:
        if not operations:
            return (frontier,)
        branches = (_Branch(frontier.condition, frontier.store),)
        for statement in operations:
            next_branches = []
            for branch in branches:
                next_branches.extend(self._execute_statement(branch, statement))
            branches = tuple(next_branches)
        persistent_names = tuple(entry.name for entry in self.domain.variables)
        return tuple(
            self._replace_frontier(
                frontier,
                condition=branch.condition,
                store=_Store(
                    {name: branch.store.values[name] for name in persistent_names}
                ),
            )
            for branch in branches
        )

    def _execute_statement(
        self, branch: _Branch, statement: OperationStatement
    ) -> Tuple[_Branch, ...]:
        if isinstance(statement, Operation):
            scope = dict(branch.store.values)
            value = self._value_from_expr(statement.expr, scope)
            scope[statement.var_name] = value
            return (_Branch(branch.condition, _Store(scope)),)
        if isinstance(statement, IfBlock):
            result = []
            previous = []
            has_else = False
            for block_index, block_branch in enumerate(statement.branches):
                if block_branch.condition is None:
                    selector = BoolTemplate.true()
                    has_else = True
                else:
                    selector = self._condition_from_expr(
                        block_branch.condition, branch.store
                    )
                active = BoolTemplate.and_(
                    branch.condition,
                    *[BoolTemplate.not_(item) for item in previous],
                    selector,
                )
                visible = tuple(branch.store.values)
                nested = (_Branch(active, branch.store),)
                for nested_statement in block_branch.statements:
                    nested = tuple(
                        item
                        for nested_branch in nested
                        for item in self._execute_statement(
                            nested_branch, nested_statement
                        )
                    )
                for nested_branch in nested:
                    writeback = {
                        name: nested_branch.store.values[name] for name in visible
                    }
                    result.append(_Branch(nested_branch.condition, _Store(writeback)))
                previous.append(selector)
                if (
                    block_branch.condition is None
                    and block_index == len(statement.branches) - 1
                ):
                    break
            if not has_else:
                result.append(
                    _Branch(
                        BoolTemplate.and_(
                            branch.condition,
                            *[BoolTemplate.not_(item) for item in previous],
                        ),
                        branch.store,
                    )
                )
            return tuple(result)
        raise BmcBuildError(
            "unsupported operation statement type: %r." % (type(statement),)
        )

    def _value_from_expr(
        self, expr: Expr, scope: Mapping[str, _ValueTemplate]
    ) -> _ValueTemplate:
        if isinstance(expr, Integer):
            return _ValueTemplate.const_value(expr.value)
        if isinstance(expr, Float):
            return _ValueTemplate.const_value(expr.value)
        if isinstance(expr, Variable):
            if expr.name not in scope:
                raise BmcBuildError("unknown symbolic variable %r." % expr.name)
            return scope[expr.name]
        if isinstance(expr, UnaryOp):
            return self._value_from_expr(expr.x, scope).unary(expr.op)
        if isinstance(expr, BinaryOp):
            left = self._value_from_expr(expr.x, scope)
            right = self._value_from_expr(expr.y, scope)
            return left.binary(expr.op, right)
        if isinstance(expr, UFunc):
            value = self._value_from_expr(expr.x, scope)
            return _ValueTemplate("%s(%s)" % (expr.func, value.text))
        if isinstance(expr, ConditionalOp):
            condition = self._condition_from_expr(expr.cond, _Store(scope))
            if_true = self._value_from_expr(expr.if_true, scope)
            if_false = self._value_from_expr(expr.if_false, scope)
            return _ValueTemplate(
                "if(%s, %s, %s)"
                % (_condition_text(condition), if_true.text, if_false.text)
            )
        if isinstance(expr, Boolean):
            return _ValueTemplate("true" if expr.value else "false")
        raise BmcBuildError("unsupported expression type: %r." % (type(expr),))

    def _condition_from_expr(self, expr: Expr, store: _Store) -> BoolTemplate:
        if isinstance(expr, Boolean):
            return BoolTemplate.true() if expr.value else BoolTemplate.false()
        if isinstance(expr, UnaryOp) and expr.op == "!":
            return BoolTemplate.not_(self._condition_from_expr(expr.x, store))
        if isinstance(expr, BinaryOp) and expr.op in ("&&", "and"):
            return BoolTemplate.and_(
                self._condition_from_expr(expr.x, store),
                self._condition_from_expr(expr.y, store),
            )
        if isinstance(expr, BinaryOp) and expr.op in ("||", "or"):
            return BoolTemplate.or_(
                self._condition_from_expr(expr.x, store),
                self._condition_from_expr(expr.y, store),
            )
        if isinstance(expr, BinaryOp) and expr.op == "xor":
            left = self._condition_from_expr(expr.x, store)
            right = self._condition_from_expr(expr.y, store)
            return BoolTemplate.or_(
                BoolTemplate.and_(left, BoolTemplate.not_(right)),
                BoolTemplate.and_(BoolTemplate.not_(left), right),
            )
        if isinstance(expr, BinaryOp) and expr.op == "=>":
            return BoolTemplate.or_(
                BoolTemplate.not_(self._condition_from_expr(expr.x, store)),
                self._condition_from_expr(expr.y, store),
            )
        if isinstance(expr, BinaryOp) and expr.op == "iff":
            left = self._condition_from_expr(expr.x, store)
            right = self._condition_from_expr(expr.y, store)
            return BoolTemplate.or_(
                BoolTemplate.and_(left, right),
                BoolTemplate.and_(BoolTemplate.not_(left), BoolTemplate.not_(right)),
            )
        if (
            isinstance(expr, BinaryOp)
            and expr.op in ("==", "!=")
            and (_is_condition_expr(expr.x) or _is_condition_expr(expr.y))
        ):
            left = self._condition_from_expr(expr.x, store)
            right = self._condition_from_expr(expr.y, store)
            equal = BoolTemplate.or_(
                BoolTemplate.and_(left, right),
                BoolTemplate.and_(BoolTemplate.not_(left), BoolTemplate.not_(right)),
            )
            return BoolTemplate.not_(equal) if expr.op == "!=" else equal
        if isinstance(expr, BinaryOp) and expr.op in ("<", "<=", ">", ">=", "==", "!="):
            left = self._value_from_expr(expr.x, store.values)
            right = self._value_from_expr(expr.y, store.values)
            return _comparison_condition(left, expr.op, right)
        if isinstance(expr, ConditionalOp):
            selector = self._condition_from_expr(expr.cond, store)
            if_true = self._condition_from_expr(expr.if_true, store)
            if_false = self._condition_from_expr(expr.if_false, store)
            return BoolTemplate.or_(
                BoolTemplate.and_(selector, if_true),
                BoolTemplate.and_(BoolTemplate.not_(selector), if_false),
            )
        value = self._value_from_expr(expr, store.values)
        return BoolTemplate.atom("%s%s" % (_GUARD_ATOM_PREFIX, value.text))

    def _stable_outcome(self, frontier: _MacroFrontier, state: State) -> _MacroOutcome:
        path = ".".join(state.path)
        return _MacroOutcome(
            self.state_ids[path],
            path,
            frontier.condition,
            frontier.store,
            frontier.used_events,
            frontier.case_kind,
        )

    def _terminate_outcome(self, frontier: _MacroFrontier) -> _MacroOutcome:
        return _MacroOutcome(
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            frontier.condition,
            frontier.store,
            frontier.used_events,
            frontier.case_kind,
        )

    def _cases_from_outcomes(
        self, outcomes: Sequence[_MacroOutcome]
    ) -> Tuple[CycleCase, ...]:
        counters: Dict[str, int] = {}
        cases = []
        for outcome in outcomes:
            ordinal = counters.get(outcome.case_kind, 0)
            counters[outcome.case_kind] = ordinal + 1
            cases.append(
                CycleCase(
                    outcome.case_kind,
                    self.source.source_state_id,
                    self.source.source_state_path,
                    outcome.target_state_id,
                    outcome.target_state_path,
                    "%s::%s::%s::%d"
                    % (
                        self.source.source_state_path,
                        outcome.case_kind,
                        outcome.target_state_path,
                        ordinal,
                    ),
                    outcome.condition,
                    self._var_updates(outcome.store),
                    used_events=outcome.used_events,
                    failed_conditions=outcome.failed_conditions,
                    domain=self.domain,
                )
            )
        return tuple(cases)

    def _var_updates(self, store: _Store) -> Tuple[VarUpdate, ...]:
        updates = []
        for entry in self.domain.variables:
            value = store.values[entry.name]
            carry_text = "%s%s" % (_PRE_VAR_PREFIX, entry.name)
            updates.append(
                VarUpdate(
                    entry.id,
                    entry.name,
                    value.text,
                    is_carry=value.text == carry_text,
                )
            )
        return tuple(updates)

    def _frontier_signature(self, frontier: _MacroFrontier) -> Tuple[object, ...]:
        return (
            tuple(
                (frame.state.path, frame.mode, frame.plain_before_pending)
                for frame in frontier.stack
            ),
            tuple(
                sorted(
                    (name, value.text) for name, value in frontier.store.values.items()
                )
            ),
            _condition_text(frontier.condition),
            tuple(
                item.to_canonical()["path"] + ":" + item.to_canonical()["polarity"]
                for item in frontier.used_events
            ),
            frontier.case_kind,
        )

    def _replace_frontier(
        self, frontier: _MacroFrontier, **updates: object
    ) -> _MacroFrontier:
        values = {
            "stack": frontier.stack,
            "store": frontier.store,
            "condition": frontier.condition,
            "used_events": frontier.used_events,
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

    @staticmethod
    def _flat_map(
        frontiers: Iterable[_MacroFrontier], func
    ) -> Tuple[_MacroFrontier, ...]:
        return tuple(item for frontier in frontiers for item in func(frontier))


def _literal_int(expr: Expr) -> Optional[int]:
    """Return an integer literal value if ``expr`` is integral syntax.

    Pure integer constant expressions such as ``4 - 1`` and ``2 * (1 + 1)``
    are folded so threshold normalization can recognize natural guard forms
    without evaluating expressions that depend on model variables.

    :param expr: Model expression to inspect.
    :type expr: pyfcstm.model.Expr
    :return: Integer literal value, or ``None`` for non-integer syntax.
    :rtype: Optional[int]
    """
    if isinstance(expr, Integer):
        return expr.value
    if isinstance(expr, UnaryOp) and expr.op in ("+", "-"):
        value = _literal_int(expr.x)
        if value is None:
            return None
        return value if expr.op == "+" else -value
    if isinstance(expr, BinaryOp) and expr.op in ("+", "-", "*", "%", "/"):
        left = _literal_int(expr.x)
        right = _literal_int(expr.y)
        if left is None or right is None:
            return None
        if expr.op == "+":
            return left + right
        if expr.op == "-":
            return left - right
        if expr.op == "*":
            return left * right
        if right == 0:
            return None
        if expr.op == "%":
            return left % right
        if left % right == 0:
            return left // right
    return None


def _integer_threshold_guard(expr: Optional[Expr]) -> Optional[Tuple[str, str, int]]:
    """Normalize simple integer threshold guards.

    The pseudo-loop accelerator needs to recognize syntactic variants that are
    equivalent over integer variables.  This helper converts comparisons such
    as ``x <= K - 1``, ``K > x``, and negated comparisons into a half-line
    predicate represented as ``(variable_name, relation, threshold)`` where
    ``relation`` is ``"lt"`` for ``x < threshold`` or ``"ge"`` for
    ``x >= threshold``.

    :param expr: Candidate guard expression.
    :type expr: Optional[pyfcstm.model.Expr]
    :return: Normalized integer threshold predicate, or ``None`` for
        unsupported syntax.
    :rtype: Optional[Tuple[str, str, int]]

    Example::

        >>> _integer_threshold_guard(BinaryOp(Variable('x'), '<=', Integer(3)))
        ('x', 'lt', 4)
        >>> _integer_threshold_guard(UnaryOp('!', BinaryOp(Variable('x'), '<', Integer(4))))
        ('x', 'ge', 4)
    """
    if isinstance(expr, UnaryOp) and expr.op == "!":
        inner = _integer_threshold_guard(expr.x)
        if inner is None:
            return None
        variable_name, relation, threshold = inner
        return variable_name, "ge" if relation == "lt" else "lt", threshold
    if not isinstance(expr, BinaryOp) or expr.op not in ("<", "<=", ">", ">="):
        return None

    op = expr.op
    if isinstance(expr.x, Variable):
        variable_name = expr.x.name
        value = _literal_int(expr.y)
    elif isinstance(expr.y, Variable):
        variable_name = expr.y.name
        value = _literal_int(expr.x)
        op = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}[op]
    else:
        return None

    if value is None:
        return None
    if op == "<":
        return variable_name, "lt", value
    if op == "<=":
        return variable_name, "lt", value + 1
    if op == ">":
        return variable_name, "ge", value + 1
    if op == ">=":
        return variable_name, "ge", value
    return None


def _positive_integer_increment_effect(
    statement: OperationStatement, variable_name: str
) -> Optional[int]:
    """Return the positive integer step for ``variable_name = variable_name + N``.

    :param statement: Operation statement to inspect.
    :type statement: pyfcstm.model.OperationStatement
    :param variable_name: Persistent variable that should be incremented.
    :type variable_name: str
    :return: Positive integer increment, or ``None`` for unsupported shapes.
    :rtype: Optional[int]
    """
    if not isinstance(statement, Operation):
        return None
    if statement.var_name != variable_name:
        return None
    expr = statement.expr
    if not isinstance(expr, BinaryOp) or expr.op != "+":
        return None
    if isinstance(expr.x, Variable) and expr.x.name == variable_name:
        value = _literal_int(expr.y)
        return value if value is not None and value > 0 else None
    if isinstance(expr.y, Variable) and expr.y.name == variable_name:
        value = _literal_int(expr.x)
        return value if value is not None and value > 0 else None
    return None


def _threshold_reached_value(
    value: _ValueTemplate,
    threshold: int,
    increment: int,
) -> _ValueTemplate:
    """Return the first loop value that satisfies ``x >= threshold``.

    :param value: Current symbolic value before the accelerated loop.
    :type value: _ValueTemplate
    :param threshold: Exit threshold.
    :type threshold: int
    :param increment: Positive loop increment.
    :type increment: int
    :return: First value reached by repeated increments that exits the loop.
    :rtype: _ValueTemplate
    :raises BmcBuildError: If the loop input is not a linear expression over
        pre-state variables or the increment is invalid.
    """
    if increment <= 0:
        raise BmcBuildError("pseudo loop increment must be positive.")
    if value.linear is None:
        raise BmcBuildError("pseudo loop acceleration requires a linear integer value.")
    if any(not name.startswith(_PRE_VAR_PREFIX) for name in value.linear.coeffs):
        raise BmcBuildError("pseudo loop acceleration requires pre-state variables.")
    if increment == 1:
        return _ValueTemplate.const_value(threshold)
    threshold_text = _format_number(threshold)
    increment_text = _format_number(increment)
    # The generated recipe intentionally uses Python/Z3 Euclidean modulo
    # semantics.  PR-10 relation lowering must preserve that meaning for
    # negative pre-state values instead of adopting target-language remainder
    # semantics such as C's truncated ``%``.
    return _ValueTemplate(
        "%s + (((%s) - %s) %% %s)"
        % (threshold_text, value.text, threshold_text, increment_text)
    )


def _has_direct_atom_contradiction(condition: BoolTemplate) -> bool:
    """Return whether a conjunction contains both ``a`` and ``not a``.

    :param condition: Boolean recipe to inspect.
    :type condition: pyfcstm.bmc.macro.BoolTemplate
    :return: Whether a direct atom contradiction is present.
    :rtype: bool
    """
    positive = set()
    negative = set()
    for item in _conjunctive_literals(condition):
        if item.kind == "atom":
            positive.add(item._atom_name())
        elif item.kind == "not" and item.operands[0].kind == "atom":
            negative.add(item.operands[0]._atom_name())
    return bool(positive.intersection(negative))


def _conjunctive_literals(condition: BoolTemplate) -> Tuple[BoolTemplate, ...]:
    """Flatten conjunction operands for direct literal inspection.

    :param condition: Boolean recipe to flatten.
    :type condition: pyfcstm.bmc.macro.BoolTemplate
    :return: Tuple of conjunction leaves.
    :rtype: Tuple[pyfcstm.bmc.macro.BoolTemplate, ...]
    """
    if condition.kind == "and":
        result = []
        for operand in condition.operands:
            result.extend(_conjunctive_literals(operand))
        return tuple(result)
    return (condition,)


def _comparison_condition(
    left: _ValueTemplate, op: str, right: _ValueTemplate
) -> BoolTemplate:
    if left.linear is not None and right.linear is not None:
        diff = left.linear.add(right.linear.mul_const(-1))
        normalized = _single_var_threshold(diff, op)
        if normalized is not None:
            atom_text, negated = normalized
            atom = BoolTemplate.atom("%s%s" % (_GUARD_ATOM_PREFIX, atom_text))
            return BoolTemplate.not_(atom) if negated else atom
    return BoolTemplate.atom(
        "%s%s %s %s" % (_GUARD_ATOM_PREFIX, left.text, op, right.text)
    )


def _single_var_threshold(diff: _LinearExpr, op: str) -> Optional[Tuple[str, bool]]:
    if len(diff.coeffs) != 1:
        return None
    ((name, coeff),) = diff.coeffs.items()
    if coeff == 0:
        return None
    threshold = -diff.const / coeff
    if coeff < 0:
        reverse = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}
        op = reverse[op]
    value = _format_number(threshold)
    if op == "<":
        return "%s < %s" % (name, value), False
    if op == ">=":
        return "%s < %s" % (name, value), True
    if op == "<=":
        return "%s <= %s" % (name, value), False
    if op == ">":
        return "%s <= %s" % (name, value), True
    if op == "==":
        return "%s == %s" % (name, value), False
    if op == "!=":
        return "%s == %s" % (name, value), True
    return None


def _condition_text(condition: BoolTemplate) -> str:
    return repr(condition.to_canonical())


def _is_condition_expr(expr: Expr) -> bool:
    if isinstance(expr, Boolean):
        return True
    if isinstance(expr, UnaryOp) and expr.op in ("!", "not"):
        return True
    if isinstance(expr, BinaryOp) and expr.op in (
        "&&",
        "and",
        "||",
        "or",
        "xor",
        "=>",
        "implies",
        "iff",
    ):
        return True
    if isinstance(expr, BinaryOp) and expr.op in ("<", "<=", ">", ">="):
        return True
    if isinstance(expr, BinaryOp) and expr.op in ("==", "!="):
        return _is_condition_expr(expr.x) or _is_condition_expr(expr.y)
    if isinstance(expr, ConditionalOp):
        return _is_condition_expr(expr.if_true) or _is_condition_expr(expr.if_false)
    return False


def _event_atom(path: str) -> str:
    return "%s%s" % (_EVENT_ATOM_PREFIX, path)


def _event_uses_from_condition(
    condition: BoolTemplate,
    domain: BmcDomain,
    polarity: str = "positive",
    reason: str = "trigger",
) -> Tuple[EventUse, ...]:
    entries = {entry.path: entry for entry in domain.events}
    result = []
    for variable in condition.variables:
        if not variable.startswith(_EVENT_ATOM_PREFIX):
            continue
        path = variable[len(_EVENT_ATOM_PREFIX) :]
        entry = entries.get(path)
        if entry is not None:
            result.append(EventUse(entry.id, entry.path, polarity, reason))
    return tuple(result)


def _merge_event_uses(*groups: Sequence[EventUse]) -> Tuple[EventUse, ...]:
    by_key = {}
    for group in groups:
        for item in group:
            by_key[(item.event_id, item.path, item.polarity, item.reason)] = item
    return tuple(
        sorted(
            by_key.values(),
            key=lambda item: (item.event_id, item.polarity, item.reason),
        )
    )


def _path_to_root(state: State) -> Tuple[State, ...]:
    path = []
    current = state
    while current is not None:
        path.insert(0, current)
        current = current.parent
    return tuple(path)


def expand_macro_step_cases(
    source: MacroStepSource,
    options: Optional[MacroExpansionOptions] = None,
) -> MacroStepFormal:
    """Expand one macro-step source into source-local cycle cases.

    :param source: Domain-backed macro-step source profile.
    :type source: MacroStepSource
    :param options: Optional expansion options, defaults to ``None``.
    :type options: MacroExpansionOptions, optional
    :return: Source-local macro-step formal buckets.
    :rtype: pyfcstm.bmc.macro.MacroStepFormal
    :raises InvalidBmcEncoding: If ``source`` is not a supported domain-backed
        source or its domain lacks a model snapshot.
    :raises BmcBuildError: If expansion cannot prove a local partition or hits
        runtime-aligned safety limits.

    Example::

        >>> from pyfcstm.bmc import build_bmc_domain, stable_leaf_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> domain = build_bmc_domain(model, 1)
        >>> expand_macro_step_cases(stable_leaf_source(domain, 'Root')).source.kind
        'stable_leaf'
    """
    if not isinstance(source, MacroStepSource):
        raise InvalidBmcEncoding("source must be MacroStepSource.")
    if options is None:
        options = MacroExpansionOptions()
    if not isinstance(options, MacroExpansionOptions):
        raise InvalidBmcEncoding("options must be MacroExpansionOptions.")
    try:
        return _Expander(source, options).expand()
    except RecursionError as err:
        # RecursionError: hostile macro graphs may create structurally new
        # recursive frontiers faster than Python's call stack can represent.
        # Surface that as a build failure rather than leaking an interpreter
        # implementation limit to BMC callers.
        raise BmcBuildError(
            "macro expansion exceeded the Python recursion limit before "
            "reaching a runtime-aligned safety cap."
        ) from err


__all__ = ["MacroExpansionOptions", "expand_macro_step_cases"]
