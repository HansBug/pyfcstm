"""Source construction attached to the actual bounded transition relation.

Capture is explicitly requested with ``BmcOptions(record_construction=True)``.
Reading a construction does not recompile the model or infer source locations
from encoded symbol names. Local binding checks are not UNSAT proofs.

Example::

    >>> from pyfcstm.bmc import BmcOptions, compile_bmc_query
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text("def int x = 0; state Root { enter { x = x; } }")
    >>> compiled = compile_bmc_query(model, "init cold havoc *; check reach <= 1: true;",
    ...                              options=BmcOptions(record_construction=True))
    >>> report = get_bmc_construction(compiled.core, ("transition.step.0000",))
    >>> report.check().status
    'verified'
    >>> action = next(action for case in report.cases for action in case.actions)
    >>> action.execution.values[-1].reads
    (('x', 0),)

This successful binding check does not determine the property verdict. The
ordinary property solver still owns objective polarity and mandatory replay.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

import z3

from pyfcstm.solver.construction import ConstructionCheck, OperationConstruction
from pyfcstm.solver.construction import _same_expression_records, _same_expressions, _source_at
from pyfcstm.solver.domain import DomainConstraint, ExpressionConstruction, translate_expr_domain
from pyfcstm.solver.budget import SolveBudget
from pyfcstm.solver.unsat import UnsatConstraint, UnsatQuery, explain_unsat_core

from .macro import ActionBlock, GuardRequirement
from .provenance import BmcSourceRef, conjunctive_units


def _same_environment(left, right):
    return left.keys() == right.keys() and all(z3.eq(left[name], right[name]) for name in left)


@dataclass(frozen=True)
class BmcActionConstruction:
    """One action invocation, including its local construction graph.

    :param index: Action ordinal in the enclosing case.
    :param block: Actual macro action, with lifecycle and ref identity.
    :param before: Values at action entry.
    :param after: Values at action exit; local temporaries are not exported.
    :param execution: Captured operation graph, or ``None`` for abstract hooks.
    :param sources: Source references for assignment values, in graph order.
    :param source_paths: Retained occurrence path to original source path.
    """

    index: int
    block: ActionBlock
    before: Mapping[str, z3.ExprRef]
    after: Mapping[str, z3.ExprRef]
    execution: Optional[OperationConstruction]
    sources: Tuple[BmcSourceRef, ...]
    source_paths: Mapping[tuple, tuple]

    def text_lines(self, names=None, *, expanded=False) -> Tuple[str, ...]:
        """Show source statements and local value definitions.

        Input values are explicitly bound as ``x@entry`` at this call entry.
        ``x#n`` is the nth definition of x within this invocation, including
        necessary branch joins; it is not an internal graph ID or a frame
        value. Authored identity writes remain visible.
        For frame, case, guard and cross-action context, use the enclosing
        :meth:`BmcConstructionReport.text_lines` instead. This local view
        does not assert that the action is reachable or executes unconditionally.

        :param names: Optional construction-time symbol display registry.
        :type names: Optional[pyfcstm.solver.symbols.SymbolNames]
        :param expanded: Add actual expanded values and recorded translation
            context, without additional solving or algebraic simplification.
            Defaults to ``False``. Booleans use DSL notation; numeric SMT
            primitives without an exact DSL equivalent retain typed forms.
        :type expanded: bool
        :return: Complete lines for this action, without truncation.
        :rtype: Tuple[str, ...]
        :raises TypeError: If ``expanded`` is not Boolean.
        """
        from ._construction_text import _action_text

        return _action_text(self, names, expanded=expanded)[0]


@dataclass(frozen=True)
class BmcConstructionUnit:
    """Condition-preserving conjunct with an exact parent source group.

    :param parent_id: Original group ID.
    :param index: Conjunct ordinal within that parent.
    :param expression: Refined Boolean formula, retaining implication guards.
    :param source: Original source-group object, preserved by identity.
    """

    parent_id: str
    index: int
    expression: z3.BoolRef
    source: object


@dataclass(frozen=True)
class BmcConstructionRefinement:
    """Equivalent selected groups and independently rechecked fine core.

    :param query: Fine-grained query, with the original fixed background.
    :param units: Fine constraints with source-parent mappings.
    :param equivalence: Per-parent conjunction equivalence check outcome.
    :param explanation: Independent fine-core check, or ``None`` if equivalence
        was not established or the shared budget was exhausted.
    """

    query: UnsatQuery
    units: Tuple[BmcConstructionUnit, ...]
    equivalence: ConstructionCheck
    explanation: object = None


@dataclass(frozen=True)
class BmcGuardConstruction:
    """Guard expression bound to its actual action-prefix environment.

    :param requirement: Original guard and its evaluation anchor.
    :param environment: Symbolic values at that anchor.
    :param expression: Actual lowered guard expression.
    :param source: Source location, explicitly incomplete when unavailable.
    :param subexpressions: Source child occurrences from the actual translation.
    :param definedness: Runtime requirements produced by this guard evaluation.
    """

    requirement: GuardRequirement
    environment: Mapping[str, z3.ExprRef]
    expression: z3.BoolRef
    source: BmcSourceRef
    subexpressions: Tuple[ExpressionConstruction, ...] = ()
    definedness: Tuple[DomainConstraint, ...] = ()


@dataclass(frozen=True)
class BmcCaseConstruction:
    """Construction instance for one query, frame and macro case.

    :param query: Original prepared query object, preserved by identity.
    :param step_index: BMC step of this execution instance.
    :param case: Original macro case object.
    :param expression: Exact selector binding and implication submitted to SMT.
    :param antecedent: Complete effective case scope, not just a source guard.
    :param before: Incoming frame variables, inputs and shared parameters.
    :param actions: Ordered action invocations.
    :param guards: Guards with their action-prefix anchors.
    """

    query: object
    step_index: int
    case: object
    expression: z3.BoolRef
    antecedent: z3.BoolRef
    before: Mapping[str, z3.ExprRef]
    actions: Tuple[BmcActionConstruction, ...]
    guards: Tuple[BmcGuardConstruction, ...]


class _CaseConstructionBuilder:
    """Collect existing executor evidence while lowering one case."""

    def __init__(self, context, env):
        self.context = context
        self.before = MappingProxyType(dict(env))
        self.actions = []
        self.guards = []

    def action(self, block, before, execution, source_paths=None):
        graph = execution.construction if execution is not None else None
        paths = (dict(source_paths) if source_paths is not None else
                 {value.path: value.path for value in graph.values if value.kind != 'input'}
                 if graph is not None else {})
        sources = tuple(
            self.context._source_registry.model_reference(_source_at(block.operations, paths[value.path]))
            for value in graph.values if value.kind == 'assignment'
        ) if graph is not None else ()
        self.actions.append(BmcActionConstruction(
            len(self.actions), block, MappingProxyType(dict(before)),
            MappingProxyType(dict(execution.env if execution is not None else before)),
            graph, sources, MappingProxyType(paths),
        ))

    def guard(self, requirement, env, expression, result):
        self.guards.append(BmcGuardConstruction(
            requirement, MappingProxyType(dict(env)), expression,
            self.context._source_registry.model_reference(requirement.expr),
            result.construction, result.definedness_constraints,
        ))

    def finish(self, step_index, case, expression, antecedent):
        return BmcCaseConstruction(
            self.context.query, step_index, case, expression, antecedent,
            self.before, tuple(self.actions), tuple(self.guards),
        )


@dataclass(frozen=True)
class BmcConstructionReport:
    """Selected source groups and their retained construction instances.

    :param core: The original compiled core, which supplies binding anchors.
    :param group_ids: Exactly the requested source-group identifiers.
    :param groups: Original source-group objects in request order.
    :param cases: Related case constructions, in frame/case order.
    """

    core: object
    group_ids: Tuple[str, ...]
    groups: tuple
    cases: Tuple[BmcCaseConstruction, ...]

    def text_lines(self, *, expanded=False) -> Tuple[str, ...]:
        """Describe selected groups and conditional cases across frame boundaries.

        Each frame/case owns per-variable definitions ``x#n``; boundary values
        ``x@f`` connect adjacent frames. A definition never crosses a case or
        frame boundary. Events and leaf states use ``event("path")@k`` and
        ``active("path")@k``. Each boundary lists all retained persistent
        variables, including preservation, and its target control position.
        Cold, terminated and nonleaf entries are explicit; an entered leaf
        root also needs ``!cold`` because fbmcq active(root) includes cold.
        Sliced-out variables are disclosed, not given invented equations.

        Listing alternatives does not select a trace or prove coverage. DSL
        Boolean layout cleans neutral literals, double negation, exact numeral
        comparisons and redundant connective layers within named groups.
        Typed SMT operations retain their meaning; no global simplifier runs.
        Local condition aliases are definitions, not additional premises.
        Rendering does not solve, recompile, or certify the records; call :meth:`check`
        separately. Only selected groups are premises. Priority dependencies
        are descriptions of conditions already embedded in the selected case.

        :param expanded: Include actual expanded assignment values, a boundary
            without local definitions or display aliases, and the full
            submitted case formula. Defaults to ``False``. Expansion can be
            large; formulas are never silently truncated. It uses recorded
            expressions and does not re-execute actions or call a solver.
        :type expanded: bool
        :return: Complete text lines, without truncation or file side effects.
        :rtype: Tuple[str, ...]
        :raises TypeError: If ``expanded`` is not Boolean.
        """
        from ._construction_text import _report_text

        return _report_text(self, expanded=expanded)

    def refine(self, query, *, timeout_ms=None, minimize=True) -> BmcConstructionRefinement:
        """Refine only the selected query's groups, preserving its background.

        Each parent is checked for equivalence separately, so deleting a
        whole group still deletes exactly its requirements. OR and ITE are
        never flattened into unconditional assertions. Fine-core minimality
        is measured afresh rather than inherited from the original core.

        :param query: Exact selected K/B as a solver ``UnsatQuery``. All its
            group IDs and formulas must match this report's original groups.
        :type query: pyfcstm.solver.unsat.UnsatQuery
        :param timeout_ms: Total positive millisecond budget, or ``None``.
        :param minimize: Whether to minimize the independently checked fine core.
        :return: Refinement and separately qualified solver evidence.
        :rtype: BmcConstructionRefinement
        :raises TypeError: For a non-query input or non-Boolean minimization flag.
        :raises ValueError: For a source/formula binding mismatch or invalid budget.
        """
        if not isinstance(query, UnsatQuery) or not isinstance(minimize, bool):
            raise TypeError('refinement requires UnsatQuery and Boolean minimize')
        budget = SolveBudget(timeout_ms)
        bound = get_bmc_construction(self.core, self.group_ids)
        if len(bound.groups) != len(self.groups) or any(
            left is not right for left, right in zip(bound.groups, self.groups)
        ):
            raise ValueError('selected source-group binding mismatch')
        original = {group.stable_id: group for group in self.groups}
        requested = (*query.constraints, *query.background)
        if set(original) != {group.stable_id for group in requested} or any(
            group.stable_id not in original or
            len(group.expressions) != len(original[group.stable_id].expressions) or
            any(not z3.eq(left, right) for left, right in
                zip(group.expressions, original[group.stable_id].expressions))
            for group in requested
        ):
            raise ValueError('selected query source/formula binding mismatch')
        units = []
        constraints = []
        for parent_index, group in enumerate(query.constraints):
            for index, expression in enumerate(
                unit for expression in group.expressions for unit in conjunctive_units(expression)
            ):
                unit = BmcConstructionUnit(group.stable_id, index, expression, original[group.stable_id])
                units.append(unit)
                constraints.append(UnsatConstraint('unit.%d.%d' % (parent_index, index), (expression,), unit))
        # Built-in source-group IDs use initial/assumption/transition/domain
        # namespaces, so the unit namespace cannot collide with this background.
        refined = UnsatQuery(query.query_id, tuple(constraints), query.background)
        for group in query.constraints:
            remaining = budget.remaining_ms()
            if budget.deadline is not None and remaining is None:
                return BmcConstructionRefinement(refined, tuple(units),
                                                 ConstructionCheck('unknown', 'budget exhausted'))
            solver = z3.Solver(ctx=group.expressions[0].ctx)
            if remaining is not None:
                solver.set(timeout=remaining)
            parent = z3.And(*group.expressions)
            children = z3.And(*(unit.expression for unit in units if unit.parent_id == group.stable_id))
            solver.add(parent != children)
            status = solver.check()
            if status != z3.unsat:
                return BmcConstructionRefinement(refined, tuple(units), ConstructionCheck(
                    'unknown' if status == z3.unknown else 'invalid', 'parent equivalence not established'))
        equivalence = ConstructionCheck('verified', 'each parent conjunction is equivalent')
        remaining = budget.remaining_ms()
        if budget.deadline is not None and remaining is None:
            return BmcConstructionRefinement(refined, tuple(units), equivalence)
        explanation = explain_unsat_core(refined, minimize=minimize, timeout_ms=remaining)
        return BmcConstructionRefinement(refined, tuple(units), equivalence, explanation)

    def check(self, *, timeout_ms=None) -> ConstructionCheck:
        """Check query/frame, action, guard and final-formula bindings.

        :param timeout_ms: Positive total millisecond budget, or ``None``.
            The same deadline covers all actions and guard translations.
            Exhaustion returns ``unknown`` without changing the BMC verdict.
        :return: First binding failure or a verified construction status.
        :rtype: pyfcstm.solver.construction.ConstructionCheck
        :raises ValueError: For an invalid budget.
        """
        budget = SolveBudget(timeout_ms)
        expected = get_bmc_construction(self.core, self.group_ids)
        if len(self.groups) != len(expected.groups) or any(
            left is not right for left, right in zip(self.groups, expected.groups)
        ):
            return ConstructionCheck('invalid', 'selected source-group binding mismatch')
        if len(self.cases) != len(expected.cases) or any(
            left.step_index != right.step_index or left.case is not right.case
            for left, right in zip(self.cases, expected.cases)
        ):
            return ConstructionCheck('invalid', 'selected case coverage mismatch')
        for evidence in self.cases:
            if budget.deadline is not None and budget.remaining_ms() is None:
                return ConstructionCheck('unknown', 'budget exhausted')
            if evidence.query is not self.core.context.query:
                return ConstructionCheck('invalid', 'query identity mismatch')
            relations = self.core.steps[evidence.step_index].case_relations
            relation = next((item for item in relations if item.case is evidence.case), None)
            if relation is None or not z3.eq(evidence.expression, relation.formula):
                return ConstructionCheck('invalid', 'case formula binding mismatch')
            if not z3.eq(evidence.antecedent, relation.antecedent):
                return ConstructionCheck('invalid', 'case scope mismatch')
            env = dict(self.core.symbols.frame_vars[evidence.step_index])
            env.update(self.core.symbols.step_inputs[evidence.step_index])
            env.update(self.core.symbols.parameters)
            if not _same_environment(env, evidence.before):
                return ConstructionCheck('invalid', 'incoming frame values mismatch')
            if len(evidence.actions) != len(evidence.case.action_blocks):
                return ConstructionCheck('invalid', 'action coverage mismatch')
            if tuple(item.requirement for item in evidence.guards) != tuple(
                sorted(evidence.case.guard_requirements,
                       key=lambda item: (item.after_action_block_index, item.requirement_id))
            ):
                return ConstructionCheck('invalid', 'guard coverage mismatch')
            for anchor in range(len(evidence.actions) + 1):
                for guard in evidence.guards:
                    if guard.requirement.after_action_block_index != anchor:
                        continue
                    if not _same_environment(env, guard.environment):
                        return ConstructionCheck('invalid', 'guard version mismatch')
                    translated = translate_expr_domain(guard.requirement.expr, env, budget=budget,
                                                       record_construction=True)
                    if budget.deadline is not None and budget.remaining_ms() is None:
                        return ConstructionCheck('unknown', 'budget exhausted')
                    expected = translated.z3_expr
                    if translated.failure is not None or not z3.eq(expected, guard.expression):
                        return ConstructionCheck('invalid', 'guard expression mismatch')
                    if not _same_expression_records(guard.subexpressions, translated.construction):
                        return ConstructionCheck('invalid', 'guard subexpression binding mismatch')
                    if not _same_expressions(
                        tuple(item.constraint for item in guard.definedness),
                        tuple(item.constraint for item in translated.definedness_constraints),
                    ):
                        return ConstructionCheck('invalid', 'guard definedness binding mismatch')
                    if not z3.eq(guard.expression, relation.guard_terms[guard.requirement.requirement_id]):
                        return ConstructionCheck('invalid', 'guard formula binding mismatch')
                if anchor == len(evidence.actions):
                    continue
                action = evidence.actions[anchor]
                if action.index != anchor or action.block is not evidence.case.action_blocks[anchor]:
                    return ConstructionCheck('invalid', 'action source mismatch')
                if not _same_environment(env, action.before):
                    return ConstructionCheck('invalid', 'action input version mismatch')
                if action.block.is_abstract:
                    if action.execution is not None or not _same_environment(env, action.after):
                        return ConstructionCheck('invalid', 'abstract action changes values')
                else:
                    graph = action.execution
                    if graph is None:
                        return ConstructionCheck('invalid', 'action construction missing')
                    sources = []
                    for value in graph.values:
                        if value.kind == 'input':
                            continue
                        source = _source_at(action.block.operations, action.source_paths.get(value.path, ()))
                        if value.kind == 'assignment':
                            if source is not value.source:
                                return ConstructionCheck('invalid', 'assignment source binding mismatch')
                            sources.append(self.core.context._source_registry.model_reference(source))
                        else:
                            # Slicing retains each original condition, even when
                            # it removes assignments from that branch's body.
                            if source is None or len(source.branches) != len(value.source.branches) or any(
                                left.condition is not right.condition
                                for left, right in zip(source.branches, value.source.branches)
                            ):
                                return ConstructionCheck('invalid', 'branch source binding mismatch')
                    if tuple(sources) != action.sources:
                        return ConstructionCheck('invalid', 'source location binding mismatch')
                    incoming = {name: graph.values[index].expression
                                for name, index in graph.initial_versions.items()}
                    outgoing = {name: graph.values[index].expression
                                for name, index in graph.final_versions.items()}
                    if not _same_environment(incoming, env) or not _same_environment(outgoing, action.after):
                        return ConstructionCheck('invalid', 'action graph boundary mismatch')
                    checked = graph._check(budget)
                    if checked.status != 'verified':
                        return checked
                env = dict(action.after)
            if any(not z3.eq(env[name], expression)
                   for name, expression in relation.post_var_exprs.items()):
                return ConstructionCheck('invalid', 'post-state binding mismatch')
        return ConstructionCheck('verified', 'selected construction bindings checked')


def get_bmc_construction(core, group_ids) -> BmcConstructionReport:
    """Read captured construction for exactly the requested source groups.

    :param core: Core compiled with ``record_construction=True``.
    :param group_ids: Unique IDs from the core's tracked or case-group ledger.
        Selecting a step includes its cases; selecting a case includes only it.
        Initialization/assumption groups retain their direct source binding.
    :return: Source groups and construction instances, without solving.
    :rtype: BmcConstructionReport
    :raises ValueError: For missing recording, duplicate or unknown IDs.
    """
    if not core.context.options.record_construction:
        raise ValueError('compile with BmcOptions(record_construction=True) first')
    identifiers = tuple(group_ids)
    lookup = {item.stable_id: item for item in (*core._tracked_groups, *core._tracked_case_groups)}
    if len(set(identifiers)) != len(identifiers) or any(name not in lookup for name in identifiers):
        raise ValueError('construction group IDs must be unique existing source IDs')
    groups = tuple(lookup[name] for name in identifiers)
    selected = set()
    for group in groups:
        if group.category == 'transition.step':
            step_index = group.refs['step']
            selected.update((step_index, index)
                            for index in range(len(core.steps[step_index].case_relations)))
        elif group.category == 'transition.case':
            selected.add((group.refs['step'], group.refs['case_index']))
    cases = tuple(core.steps[step].case_relations[index].construction
                  for step, index in sorted(selected))
    return BmcConstructionReport(core, identifiers, groups, cases)
