"""Compile BMC query properties into solver objectives.

This module is the property layer above :mod:`pyfcstm.bmc.relation`.  It
consumes a :class:`pyfcstm.bmc.relation.BmcCoreFormula`, keeps the core trace
relation unchanged, and adds the query objective for the bound ``check`` clause.
The compiler does not solve the formula, decode witnesses, replay traces, or
connect to :mod:`pyfcstm.verify`; those stages can consume the returned
:class:`BmcPropertyFormula` later.

The module contains:

* :class:`BmcPropertyFormula` - Compiled objective and diagnostic formulas.
* :func:`compile_bmc_property` - Public entry point for lowering a bound query
  property against an existing core trace formula.

Example::

    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    >>> from pyfcstm.bmc.properties import compile_bmc_property
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");'))
    >>> compile_bmc_property(core).kind
    'reach'
"""

from __future__ import annotations

from collections.abc import Iterable as IterableABC
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

import z3

from pyfcstm.bmc import ast as bmc_ast
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcQuery, UnsupportedBmcQuery
from pyfcstm.bmc.query import BmcProperty
from pyfcstm.bmc.relation import (
    BmcCoreFormula,
    _lower_bmc_cond_expr,
)

_CanonicalDict = Dict[str, Any]
_COVERABLE_CASE_KINDS = {"transition", "fallback"}
_KNOWN_CASE_KINDS = {"transition", "fallback", "initial", "absorb", "delta"}
_WITNESS_KINDS = {"reach", "exists_always", "cover"}
_COUNTEREXAMPLE_KINDS = {"forbid", "invariant", "must_reach", "response"}


def _z3_text(expr: z3.ExprRef) -> str:
    return expr.sexpr()


def _and(items: Iterable[z3.ExprRef]) -> z3.BoolRef:
    values = tuple(items)
    if not values:
        return z3.BoolVal(True)
    if len(values) == 1:
        return values[0]
    return z3.And(*values)


def _or(items: Iterable[z3.ExprRef]) -> z3.BoolRef:
    values = tuple(items)
    if not values:
        return z3.BoolVal(False)
    if len(values) == 1:
        return values[0]
    return z3.Or(*values)


def _require_core(core: object) -> BmcCoreFormula:
    if not isinstance(core, BmcCoreFormula):
        raise BmcBuildError("core must be BmcCoreFormula.")
    return core


def _require_bool(expr: z3.ExprRef, label: str) -> z3.BoolRef:
    if not z3.is_bool(expr):  # pragma: no cover - condition lowering is bool-typed.
        raise BmcBuildError("%s must lower to a Z3 Boolean expression." % label)
    return expr


@dataclass(frozen=True)
class _PredicateFormula:
    value: z3.BoolRef
    definedness: z3.BoolRef

    @property
    def good(self) -> z3.BoolRef:
        return z3.And(self.definedness, self.value)

    @property
    def bad_true(self) -> z3.BoolRef:
        return z3.Or(z3.Not(self.definedness), self.value)

    @property
    def bad_false(self) -> z3.BoolRef:
        return z3.Or(z3.Not(self.definedness), z3.Not(self.value))


@dataclass(frozen=True)
class BmcPropertyFormula:
    """Compiled BMC property objective.

    :param core: Core trace formula consumed by this property objective.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param kind: Property kind from the bound query.
    :type kind: str
    :param polarity: ``"witness"`` when SAT means a desired witness, or
        ``"counterexample"`` when SAT means a violation trace.
    :type polarity: str
    :param objective_formula: Property objective ``Phi_q``.
    :type objective_formula: z3.BoolRef
    :param solve_formula: ``Core_N`` conjoined with ``objective_formula``.
    :type solve_formula: z3.BoolRef
    :param incomplete_formula: Optional bounded-horizon incompleteness
        observation ``Omega_q``.  Currently non-trivial for response properties.
    :type incomplete_formula: z3.BoolRef
    :param incomplete_solve_formula: ``Core_N`` conjoined with
        ``incomplete_formula`` for later solver/report layers.
    :type incomplete_solve_formula: z3.BoolRef
    :param diagnostics: Static compiler diagnostics, defaults to ``()``.
    :type diagnostics: Tuple[str, ...], optional
    :param case_label: Cover case label, defaults to ``None``.
    :type case_label: Optional[str], optional
    :param response_window: Response window, defaults to ``None``.
    :type response_window: Optional[int], optional

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");'))
        >>> formula = compile_bmc_property(core)
        >>> formula.to_canonical()['polarity']
        'witness'
    """

    core: BmcCoreFormula
    kind: str
    polarity: str
    objective_formula: z3.BoolRef
    solve_formula: z3.BoolRef
    incomplete_formula: z3.BoolRef
    incomplete_solve_formula: z3.BoolRef
    diagnostics: Tuple[str, ...] = ()
    case_label: Optional[str] = None
    response_window: Optional[int] = None

    def __post_init__(self) -> None:
        _require_core(self.core)
        if not isinstance(self.kind, str) or not self.kind:
            raise BmcBuildError("kind must be a non-empty string.")
        if self.kind not in _WITNESS_KINDS | _COUNTEREXAMPLE_KINDS:
            raise BmcBuildError("Unsupported property kind: %r." % self.kind)
        if self.polarity not in {"witness", "counterexample"}:
            raise BmcBuildError("polarity must be 'witness' or 'counterexample'.")
        if self.polarity != _polarity(self.kind):
            raise BmcBuildError(
                "polarity %r does not match property kind %r."
                % (self.polarity, self.kind)
            )
        for field_name in (
            "objective_formula",
            "solve_formula",
            "incomplete_formula",
            "incomplete_solve_formula",
        ):
            if not z3.is_bool(getattr(self, field_name)):
                raise BmcBuildError("%s must be a Z3 Boolean expression." % field_name)
        if isinstance(self.diagnostics, str) or not isinstance(
            self.diagnostics, IterableABC
        ):
            raise BmcBuildError("diagnostics must be an iterable of strings.")
        diagnostics = tuple(self.diagnostics)
        if not all(isinstance(item, str) for item in diagnostics):
            raise BmcBuildError("diagnostics must contain strings.")
        if self.case_label is not None and not isinstance(self.case_label, str):
            raise BmcBuildError("case_label must be None or str.")
        if self.kind == "cover":
            if not self.case_label:
                raise BmcBuildError(
                    "case_label must be a non-empty string for cover properties."
                )
        elif self.case_label is not None:
            raise BmcBuildError("case_label is only valid for cover properties.")
        if self.response_window is not None and (
            isinstance(self.response_window, bool)
            or not isinstance(self.response_window, int)
            or self.response_window <= 0
        ):
            raise BmcBuildError("response_window must be None or a positive integer.")
        if self.kind == "response":
            if self.response_window is None:
                raise BmcBuildError(
                    "response_window must be a positive integer for response properties."
                )
        elif self.response_window is not None:
            raise BmcBuildError(
                "response_window is only valid for response properties."
            )
        object.__setattr__(self, "diagnostics", diagnostics)

    @property
    def bound(self) -> int:
        """Return the compiled query bound.

        :return: Query bound.
        :rtype: int

        Example::

            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");'))
            >>> compile_bmc_property(core).bound
            1
        """
        return self.core.context.bound

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable compiled-property summary.

        Formula fields use Z3 ``sexpr()`` text so downstream snapshots receive
        SMT-LIB-style expressions instead of Python pretty-printer output.

        :return: Canonical property formula summary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");'))
            >>> compile_bmc_property(core).to_canonical()['node']
            'bmc_property_formula'
        """
        return {
            "node": "bmc_property_formula",
            "kind": self.kind,
            "polarity": self.polarity,
            "bound": self.bound,
            "formulas": {
                "objective": _z3_text(self.objective_formula),
                "solve": _z3_text(self.solve_formula),
                "incomplete": _z3_text(self.incomplete_formula),
                "incomplete_solve": _z3_text(self.incomplete_solve_formula),
            },
            "diagnostics": list(self.diagnostics),
            "case_label": self.case_label,
            "response_window": self.response_window,
        }


def _validate_num_context(expr: bmc_ast.BmcNumExpr, context: str, path: str) -> None:
    if isinstance(
        expr,
        (
            bmc_ast.IntLiteral,
            bmc_ast.FloatLiteral,
            bmc_ast.NameRef,
            bmc_ast.MathConst,
            bmc_ast.FrameVar,
            bmc_ast.Cycle,
        ),
    ):
        return
    if isinstance(expr, bmc_ast.NumUnaryOp):
        _validate_num_context(expr.operand, context, path + ".operand")
        return
    if isinstance(expr, bmc_ast.NumBinaryOp):
        _validate_num_context(expr.left, context, path + ".left")
        _validate_num_context(expr.right, context, path + ".right")
        return
    if isinstance(expr, bmc_ast.NumConditionalOp):
        _validate_condition_context(expr.condition, context, path + ".condition")
        _validate_num_context(expr.if_true, context, path + ".if_true")
        _validate_num_context(expr.if_false, context, path + ".if_false")
        return
    if isinstance(expr, bmc_ast.UFuncCall):
        _validate_num_context(expr.operand, context, path + ".operand")
        return
    raise UnsupportedBmcQuery(  # pragma: no cover - public AST numeric set is closed.
        "%s contains unsupported numeric expression %s." % (path, type(expr).__name__)
    )


def _validate_condition_context(
    expr: bmc_ast.BmcCondExpr, context: str, path: str
) -> None:
    if isinstance(expr, bmc_ast.BoolLiteral):
        return
    if isinstance(expr, bmc_ast.NumericComparison):
        _validate_num_context(expr.left, context, path + ".left")
        _validate_num_context(expr.right, context, path + ".right")
        return
    if isinstance(expr, bmc_ast.CondUnaryOp):
        _validate_condition_context(expr.operand, context, path + ".operand")
        return
    if isinstance(expr, bmc_ast.CondBinaryOp):
        _validate_condition_context(expr.left, context, path + ".left")
        _validate_condition_context(expr.right, context, path + ".right")
        return
    if isinstance(expr, bmc_ast.CondConditionalOp):
        _validate_condition_context(expr.condition, context, path + ".condition")
        _validate_condition_context(expr.if_true, context, path + ".if_true")
        _validate_condition_context(expr.if_false, context, path + ".if_false")
        return
    if isinstance(expr, bmc_ast.Active):
        if expr.frame != "current":
            raise UnsupportedBmcQuery(
                "%s uses an explicit frame selector; property compiler "
                "predicates must use the current frame." % path
            )
        return
    if isinstance(expr, bmc_ast.Terminated):
        if expr.frame != "current":
            raise UnsupportedBmcQuery(
                "%s uses an explicit frame selector; property compiler "
                "predicates must use the current frame." % path
            )
        return
    if isinstance(expr, bmc_ast.Event):
        if context == "response_trigger" and expr.selector == "current":
            return
        if context == "response_trigger":  # pragma: no cover - binder rejects this.
            raise UnsupportedBmcQuery(
                "%s may use only event(..., current), not explicit event selectors."
                % path
            )
        raise UnsupportedBmcQuery(  # pragma: no cover - binder rejects this.
            "%s is frame-local; event atoms are only allowed in response triggers."
            % path
        )
    if isinstance(expr, bmc_ast.Case):
        raise UnsupportedBmcQuery(  # pragma: no cover - binder rejects nested case().
            "%s is not a cover predicate; case atoms are only allowed as naked cover predicates."
            % path
        )
    if isinstance(expr, bmc_ast.Called):
        raise UnsupportedBmcQuery(  # pragma: no cover - binder rejects called() for now.
            "%s uses called(), but abstract call trace properties are not supported yet."
            % path
        )
    raise UnsupportedBmcQuery(  # pragma: no cover - public AST condition set is closed.
        "%s contains unsupported condition expression %s." % (path, type(expr).__name__)
    )


def _lower_predicate(
    core: BmcCoreFormula,
    expr: bmc_ast.BmcCondExpr,
    *,
    frame_index: int,
    step_index: Optional[int] = None,
    context: str,
    path: str,
) -> _PredicateFormula:
    _validate_condition_context(expr, context, path)
    lowered = _lower_bmc_cond_expr(
        expr,
        core.symbols,
        frame_index=frame_index,
        step_index=step_index,
    )
    value = _require_bool(lowered.expr, path)
    definedness = _and(item.constraint for item in lowered.definedness_constraints)
    return _PredicateFormula(value=value, definedness=definedness)


def _property_source(core: BmcCoreFormula) -> BmcProperty:
    prop = core.context.bound_query.property.source
    if not isinstance(prop, BmcProperty):  # pragma: no cover - binder owns this shape.
        raise BmcBuildError("bound query property source must be BmcProperty.")
    return prop


def _polarity(kind: str) -> str:
    if kind in _WITNESS_KINDS:
        return "witness"
    if kind in _COUNTEREXAMPLE_KINDS:
        return "counterexample"
    raise BmcBuildError(  # pragma: no cover - query validation owns property kinds.
        "Unsupported property kind: %r." % kind
    )


def _single_predicate(prop: BmcProperty) -> bmc_ast.BmcCondExpr:
    if (
        prop.predicate is None
    ):  # pragma: no cover - query validation owns property shape.
        raise BmcBuildError("single-body property has no predicate.")
    return prop.predicate


def _frame_predicates(
    core: BmcCoreFormula, expr: bmc_ast.BmcCondExpr
) -> Tuple[_PredicateFormula, ...]:
    return tuple(
        _lower_predicate(
            core,
            expr,
            frame_index=frame_index,
            context="frame",
            path="property.predicate",
        )
        for frame_index in range(core.context.bound + 1)
    )


def _compile_reach(core: BmcCoreFormula, prop: BmcProperty) -> z3.BoolRef:
    predicates = _frame_predicates(core, _single_predicate(prop))
    return _or(item.good for item in predicates)


def _compile_forbid(core: BmcCoreFormula, prop: BmcProperty) -> z3.BoolRef:
    predicates = _frame_predicates(core, _single_predicate(prop))
    return _or(item.bad_true for item in predicates)


def _compile_invariant(core: BmcCoreFormula, prop: BmcProperty) -> z3.BoolRef:
    predicates = _frame_predicates(core, _single_predicate(prop))
    return _or(item.bad_false for item in predicates)


def _compile_must_reach(core: BmcCoreFormula, prop: BmcProperty) -> z3.BoolRef:
    predicates = _frame_predicates(core, _single_predicate(prop))
    return _and(z3.Not(item.good) for item in predicates)


def _compile_exists_always(core: BmcCoreFormula, prop: BmcProperty) -> z3.BoolRef:
    predicates = _frame_predicates(core, _single_predicate(prop))
    return _and(item.good for item in predicates)


def _validate_cover_label_schema(label: str) -> str:
    parts = label.split("::")
    if len(parts) != 4 or not all(parts):
        raise InvalidBmcQuery("cover case label schema is invalid: %r." % label)
    case_kind = parts[1]
    if case_kind not in _KNOWN_CASE_KINDS:
        raise InvalidBmcQuery("cover case label kind is invalid: %r." % label)
    return case_kind


def _cover_selectors(core: BmcCoreFormula, label: str) -> Tuple[z3.BoolRef, ...]:
    label_kind = _validate_cover_label_schema(label)
    relations = tuple(
        relation
        for step in core.steps
        for relation in step.case_relations
        if relation.case.label == label
    )
    if not relations:
        raise InvalidBmcQuery("cover case label is unknown: %r." % label)
    kinds = {relation.case.kind for relation in relations}
    if kinds != {
        label_kind
    }:  # pragma: no cover - relation labels are internally canonical.
        raise BmcBuildError("cover case label kind disagrees with relation cases.")
    if not kinds <= _COVERABLE_CASE_KINDS:
        raise InvalidBmcQuery(
            "cover case label is not coverable: %r has kind %s."
            % (label, sorted(kinds)[0])
        )
    return tuple(relation.selector for relation in relations)


def _compile_cover(core: BmcCoreFormula, prop: BmcProperty) -> Tuple[z3.BoolRef, str]:
    predicate = prop.predicate
    if (
        not isinstance(predicate, bmc_ast.Case) or predicate.frame != "current"
    ):  # pragma: no cover - binder rejects this.
        raise InvalidBmcQuery(
            'cover properties require a naked case("label") predicate.'
        )
    selectors = _cover_selectors(core, predicate.label)
    return _or(selectors), predicate.label


def _compile_response(
    core: BmcCoreFormula, prop: BmcProperty
) -> Tuple[z3.BoolRef, z3.BoolRef, int]:
    if (
        prop.trigger is None or prop.response is None or prop.within is None
    ):  # pragma: no cover - query validation owns response shape.
        raise BmcBuildError(
            "response property is missing trigger, response, or window."
        )
    window = prop.within
    if (
        isinstance(window, bool) or not isinstance(window, int) or window <= 0
    ):  # pragma: no cover - query validation owns response window shape.
        raise InvalidBmcQuery("response window must be a positive integer.")
    trigger_terms = tuple(
        _lower_predicate(
            core,
            prop.trigger,
            frame_index=step_index,
            step_index=step_index,
            context="response_trigger",
            path="property.trigger",
        )
        for step_index in range(core.context.bound)
    )
    response_terms = tuple(
        _lower_predicate(
            core,
            prop.response,
            frame_index=frame_index,
            context="frame",
            path="property.response",
        )
        for frame_index in range(core.context.bound + 1)
    )
    trigger_undefined = [z3.Not(item.definedness) for item in trigger_terms]
    violations = []
    incomplete = []
    for step_index, trigger in enumerate(trigger_terms):
        triggered = trigger.good
        if step_index + window <= core.context.bound:
            responses = [
                response_terms[frame_index].good
                for frame_index in range(step_index + 1, step_index + window + 1)
            ]
            violations.append(z3.And(triggered, z3.Not(_or(responses))))
        else:
            responses = [
                response_terms[frame_index].good
                for frame_index in range(step_index + 1, core.context.bound + 1)
            ]
            incomplete.append(z3.And(triggered, z3.Not(_or(responses))))
    return _or(tuple(trigger_undefined) + tuple(violations)), _or(incomplete), window


def compile_bmc_property(core: BmcCoreFormula) -> BmcPropertyFormula:
    """Compile the prepared query property into a solver objective.

    The returned formula keeps :attr:`pyfcstm.bmc.relation.BmcCoreFormula.core`
    intact and adds only the objective requested by the bound ``check`` clause.
    SAT means a witness for ``reach`` / ``exists_always`` / ``cover`` and a
    counterexample for ``forbid`` / ``invariant`` / ``must_reach`` /
    ``response``.

    :param core: Core trace formula to extend with the query objective.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :return: Compiled property objective bundle.
    :rtype: BmcPropertyFormula
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` or bound property
        metadata is internally inconsistent.
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If a query-level cover label or
        property shape is invalid for property compilation.
    :raises pyfcstm.bmc.errors.UnsupportedBmcQuery: If the property uses a
        parsed but unsupported BMC atom such as ``called(...)``.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");'))
        >>> compile_bmc_property(core).solve_formula.sort().name()
        'Bool'
    """
    checked_core = _require_core(core)
    prop = _property_source(checked_core)
    kind = prop.kind
    case_label = None
    response_window = None
    incomplete_formula = z3.BoolVal(False)
    if kind == "reach":
        objective = _compile_reach(checked_core, prop)
    elif kind == "forbid":
        objective = _compile_forbid(checked_core, prop)
    elif kind == "invariant":
        objective = _compile_invariant(checked_core, prop)
    elif kind == "must_reach":
        objective = _compile_must_reach(checked_core, prop)
    elif kind == "exists_always":
        objective = _compile_exists_always(checked_core, prop)
    elif kind == "cover":
        objective, case_label = _compile_cover(checked_core, prop)
    elif kind == "response":
        objective, incomplete_formula, response_window = _compile_response(
            checked_core, prop
        )
    else:  # pragma: no cover - query validation owns property kinds.
        raise BmcBuildError("Unsupported property kind: %r." % kind)
    solve_formula = z3.And(checked_core.core, objective)
    incomplete_solve_formula = z3.And(checked_core.core, incomplete_formula)
    return BmcPropertyFormula(
        core=checked_core,
        kind=kind,
        polarity=_polarity(kind),
        objective_formula=objective,
        solve_formula=solve_formula,
        incomplete_formula=incomplete_formula,
        incomplete_solve_formula=incomplete_solve_formula,
        diagnostics=(),
        case_label=case_label,
        response_window=response_window,
    )


__all__ = ["BmcPropertyFormula", "compile_bmc_property"]
