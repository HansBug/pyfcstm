"""Combo-trigger provenance diagnostics.

This module analyzes generated combo-trigger edges while reporting every
diagnostic against the user-authored combo trigger term that produced the
generated edge. It intentionally stays conservative around side effects:
prefix-sensitive guard warnings are skipped whenever lifecycle actions,
transition effects, or opaque actions may write a variable read by the
guard prefix.

The module contains:

* :func:`collect_combo_warnings` - Entry point used by the design-health
  analyzer pipeline.

Example::

    >>> collect_combo_warnings(None)
    []
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple

from ...utils.validate import ModelDiagnostic, Span
from .const_fold import fold_condition_expression
from .use_def import collect_expr_variables

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only.
    from ...model.expr import Expr
    from ...model.model import OperationStatement, StateMachine, Transition


@dataclass(frozen=True)
class _ComboTerm:
    """One generated edge term projected back to one combo origin."""

    ref: object
    transition: "Transition"

    @property
    def origin_id(self) -> str:
        return self.ref.origin_id

    @property
    def index(self) -> int:
        return self.ref.term_index

    @property
    def term_text(self) -> str:
        return self.ref.term_text

    @property
    def term_span(self) -> Optional[Span]:
        return self.ref.term_span

    @property
    def value_span(self) -> Optional[Span]:
        return self.ref.value_span

    @property
    def transition_span(self) -> Optional[Span]:
        return self.ref.transition_span

    @property
    def trigger_span(self) -> Optional[Span]:
        return self.ref.trigger_span

    @property
    def is_event(self) -> bool:
        return self.transition.event is not None

    @property
    def is_guard(self) -> bool:
        return self.transition.guard is not None

    @property
    def event_name(self) -> Optional[str]:
        event = self.transition.event
        return None if event is None else event.path_name

    @property
    def guard(self) -> Optional["Expr"]:
        return self.transition.guard


def collect_combo_warnings(machine: Optional["StateMachine"]) -> List[ModelDiagnostic]:
    """
    Collect diagnostics tied to combo trigger provenance.

    The returned diagnostics use ``ModelDiagnostic.span`` for the primary
    original combo term and keep related term spans in ``refs`` so editor
    integrations can navigate to the first duplicate event or prior guard.

    :param machine: State machine to inspect, or ``None`` to emit no
        diagnostics.
    :type machine: pyfcstm.model.StateMachine, optional
    :return: Combo provenance diagnostics.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Example::

        >>> collect_combo_warnings(None)
        []
    """
    if machine is None:
        return []
    terms_by_origin = _combo_terms_by_origin(machine)
    diagnostics: List[ModelDiagnostic] = []
    for terms in terms_by_origin.values():
        diagnostics.extend(_duplicate_event_warnings(terms))
        diagnostics.extend(_guard_const_warnings(terms))
        diagnostics.extend(_guard_prefix_warnings(machine, terms))
    return diagnostics


def _combo_terms_by_origin(machine: "StateMachine") -> Dict[str, Tuple[_ComboTerm, ...]]:
    grouped: Dict[str, Dict[int, _ComboTerm]] = {}
    for state in machine.walk_states():
        for transition in state.transitions:
            for ref in getattr(transition, "combo_origin_refs", ()):
                if not ref.consumes_term:
                    continue
                grouped.setdefault(ref.origin_id, {}).setdefault(
                    ref.term_index,
                    _ComboTerm(ref=ref, transition=transition),
                )
    return {
        origin_id: tuple(item for _, item in sorted(by_index.items()))
        for origin_id, by_index in grouped.items()
    }


def _duplicate_event_warnings(terms: Sequence[_ComboTerm]) -> List[ModelDiagnostic]:
    first_by_event: Dict[str, _ComboTerm] = {}
    diagnostics: List[ModelDiagnostic] = []
    for term in terms:
        if not term.is_event or term.event_name is None:
            continue
        first = first_by_event.get(term.event_name)
        if first is None:
            first_by_event[term.event_name] = term
            continue
        diagnostics.append(ModelDiagnostic(
            code="W_COMBO_DUPLICATE_EVENT",
            severity="warning",
            message=(
                f"Combo trigger repeats event {term.event_name!r}; this is "
                "legal but usually redundant."
            ),
            span=term.term_span,
            refs={
                "origin_id": term.origin_id,
                "event_name": term.event_name,
                "term_index": term.index,
                "first_term_index": first.index,
                "term_text": term.term_text,
                "first_term_text": first.term_text,
                "transition_span": term.transition_span,
                "trigger_span": term.trigger_span,
                "term_span": term.term_span,
                "first_term_span": first.term_span,
            },
        ))
    return diagnostics


def _guard_const_warnings(terms: Sequence[_ComboTerm]) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for term in terms:
        if not term.is_guard or term.guard is None:
            continue
        folded = fold_condition_expression(term.guard)
        if folded not in {True, False}:
            continue
        code = "W_COMBO_GUARD_CONST_TRUE" if folded else "W_COMBO_GUARD_CONST_FALSE"
        label = "true" if folded else "false"
        diagnostics.append(ModelDiagnostic(
            code=code,
            severity="warning",
            message=f"Combo guard term {term.term_text!r} is statically {label}.",
            span=term.term_span,
            refs={
                "origin_id": term.origin_id,
                "term_index": term.index,
                "term_text": term.term_text,
                "folded_value": folded,
                "transition_span": term.transition_span,
                "trigger_span": term.trigger_span,
                "term_span": term.term_span,
                "value_span": term.value_span,
            },
        ))
    return diagnostics


def _guard_prefix_warnings(
    machine: "StateMachine",
    terms: Sequence[_ComboTerm],
) -> List[ModelDiagnostic]:
    guard_terms: List[_ComboTerm] = []
    diagnostics: List[ModelDiagnostic] = []
    for term in terms:
        if not term.is_guard or term.guard is None:
            continue
        if guard_terms and not _side_effects_may_change_guard_prefix(
            terms,
            term,
            guard_terms,
        ):
            diagnostic = _prefix_guard_diagnostic(machine, term, guard_terms)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
        guard_terms.append(term)
    return diagnostics


def _prefix_guard_diagnostic(
    machine: "StateMachine",
    current: _ComboTerm,
    prior_terms: Sequence[_ComboTerm],
) -> Optional[ModelDiagnostic]:
    import z3

    from ...solver.expr import create_z3_vars_from_models, expr_to_z3

    z3_vars = create_z3_vars_from_models(machine)
    try:
        prior_z3 = [
            expr_to_z3(term.guard, z3_vars)
            for term in prior_terms
            if term.guard is not None
        ]
        current_z3 = expr_to_z3(current.guard, z3_vars)
    except (ValueError, NotImplementedError, z3.Z3Exception):
        # ValueError: unsupported expression shape or missing variable in the
        # solver conversion; NotImplementedError: unsupported math function;
        # Z3Exception: backend rejects an otherwise parsed expression. Any of
        # these means the conservative static warning should be skipped.
        return None

    if not prior_z3:
        return None
    prefix = z3.And(*prior_z3)
    if _z3_unsat(z3.And(prefix, current_z3)):
        return _make_prefix_guard_diagnostic(
            "W_COMBO_GUARD_PREFIX_CONTRADICTS",
            "contradicts prior combo guard terms",
            current,
            _first_decisive_prior_guard(
                machine,
                prior_terms,
                current_z3,
                "contradicts",
            ),
        )
    if _z3_unsat(z3.And(prefix, z3.Not(current_z3))):
        return _make_prefix_guard_diagnostic(
            "W_COMBO_GUARD_PREFIX_IMPLIED",
            "is implied by prior combo guard terms",
            current,
            _first_decisive_prior_guard(
                machine,
                prior_terms,
                current_z3,
                "implies",
            ),
        )
    return None


def _first_decisive_prior_guard(
    machine: "StateMachine",
    prior_terms: Sequence[_ComboTerm],
    current_z3: object,
    relation: str,
) -> _ComboTerm:
    import z3

    from ...solver.expr import create_z3_vars_from_models, expr_to_z3

    z3_vars = create_z3_vars_from_models(machine)
    prefix_terms = []
    for term in prior_terms:
        if term.guard is None:
            continue
        try:
            prefix_terms.append(expr_to_z3(term.guard, z3_vars))
        except (ValueError, NotImplementedError, z3.Z3Exception):
            # ValueError: unsupported expression or missing variable;
            # NotImplementedError: unsupported function conversion;
            # Z3Exception: backend conversion failure. Fall back to the
            # conservative nearest prior guard chosen by the caller's prefix.
            return prior_terms[-1]
        prefix = z3.And(*prefix_terms)
        if relation == "contradicts" and _z3_unsat(z3.And(prefix, current_z3)):
            return term
        if relation == "implies" and _z3_unsat(z3.And(prefix, z3.Not(current_z3))):
            return term
    return prior_terms[-1]


def _z3_unsat(expr: object) -> bool:
    import z3

    solver = z3.Solver()
    solver.set(timeout=200)
    solver.add(expr)
    return solver.check() == z3.unsat


def _make_prefix_guard_diagnostic(
    code: str,
    relation: str,
    current: _ComboTerm,
    prior: _ComboTerm,
) -> ModelDiagnostic:
    return ModelDiagnostic(
        code=code,
        severity="warning",
        message=f"Combo guard term {current.term_text!r} {relation}.",
        span=current.term_span,
        refs={
            "origin_id": current.origin_id,
            "term_index": current.index,
            "prior_term_index": prior.index,
            "term_text": current.term_text,
            "prior_term_text": prior.term_text,
            "transition_span": current.transition_span,
            "trigger_span": current.trigger_span,
            "term_span": current.term_span,
            "value_span": current.value_span,
            "prior_term_span": prior.term_span,
            "prior_value_span": prior.value_span,
        },
    )


def _side_effects_may_change_guard_prefix(
    terms: Sequence[_ComboTerm],
    current: _ComboTerm,
    prior_terms: Sequence[_ComboTerm],
) -> bool:
    relevant = _guard_variables([*prior_terms, current])
    if not relevant:
        return False
    first_prior_index = min(term.index for term in prior_terms)
    source_transition = terms[0].transition if terms else current.transition
    if _first_hop_actions_may_write(source_transition, relevant):
        return True
    for term in terms:
        if not (first_prior_index <= term.index < current.index):
            continue
        if _statements_may_write_relevant(term.transition.effects, relevant):
            return True
    return False


def _guard_variables(terms: Iterable[_ComboTerm]) -> Tuple[str, ...]:
    out: List[str] = []
    seen = set()
    for term in terms:
        if term.guard is None:
            continue
        for name in collect_expr_variables(term.guard):
            if name in seen:
                continue
            seen.add(name)
            out.append(name)
    return tuple(out)


def _first_hop_actions_may_write(
    transition: "Transition",
    relevant: Sequence[str],
) -> bool:
    from ...dsl import INIT_STATE

    parent = transition.parent
    if parent is None:
        return False
    if transition.from_state is INIT_STATE:
        return _actions_may_write_relevant(
            [
                item for item in parent.on_durings
                if getattr(item, "aspect", None) == "before"
            ],
            relevant,
        )
    if isinstance(transition.from_state, str):
        source = parent.substates.get(transition.from_state)
        if source is not None and _actions_may_write_relevant(source.on_exits, relevant):
            return True
    return False


def _actions_may_write_relevant(actions: Iterable[object], relevant: Sequence[str]) -> bool:
    for action in actions:
        if getattr(action, "is_abstract", False) or getattr(action, "is_ref", False):
            return True
        if _statements_may_write_relevant(getattr(action, "operations", ()), relevant):
            return True
    return False


def _statements_may_write_relevant(
    statements: Iterable["OperationStatement"],
    relevant: Sequence[str],
) -> bool:
    writes: List[str] = []
    for statement in statements:
        if _statement_writes_unknown_or_collects(statement, writes):
            return True
    relevant_set = set(relevant)
    return any(name in relevant_set for name in writes)


def _statement_writes_unknown_or_collects(
    statement: "OperationStatement",
    writes: List[str],
) -> bool:
    from ...model.model import IfBlock, Operation

    if isinstance(statement, Operation):
        writes.append(statement.var_name)
        return False
    if isinstance(statement, IfBlock):
        for branch in statement.branches:
            for inner in branch.statements:
                if _statement_writes_unknown_or_collects(inner, writes):
                    return True
        return False
    return True
