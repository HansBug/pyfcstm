"""
Operation parsing and execution utilities for Z3 solver integration.

This module provides functions to parse DSL operation code strings into
operation statements and execute them on Z3 variable dictionaries.

The module contains the following main components:

* :func:`parse_operations` - Parse DSL operation code string to statement tree
* :func:`execute_operations` - Execute operation statements on a Z3 variable dictionary

Example::

    >>> from pyfcstm.solver.operation import parse_operations, execute_operations
    >>> import z3
    >>>
    >>> # Parse operation statements from DSL string
    >>> ops = parse_operations("x = x + 1; y = x * 2;", allowed_vars=['x', 'y'])
    >>>
    >>> # Execute operations on Z3 variables
    >>> z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
    >>> z3_state = {'x': z3.IntVal(5), 'y': z3.IntVal(0)}
    >>> new_state = execute_operations(ops, z3_state)
    >>> # new_state['x'] represents the Z3 expression: 5 + 1
    >>> # new_state['y'] represents the Z3 expression: (5 + 1) * 2
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import List, Dict, Mapping, Optional, Sequence, Tuple, Union

import z3

from .expr import expr_to_z3
from .domain import (
    DomainConstraint,
    DomainSource,
    TranslationFailure,
    merge_definedness_constraints,
    translate_expr_domain,
)
from .logical import is_sat
from ..dsl.parse import parse_with_grammar_entry
from ..dsl import node as dsl_nodes
from ..model.expr import parse_expr_node_to_expr
from ..model.model import IfBlock, IfBlockBranch, Operation, OperationStatement


_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_Z3Env = Dict[str, _Z3Expr]

OperationSource = DomainSource


@dataclass(frozen=True)
class OperationFailure:
    """Pure solver-layer operation execution failure."""

    kind: str
    reason: str
    source: Optional[DomainSource] = None
    translation_failure: Optional[TranslationFailure] = None


@dataclass(frozen=True)
class OperationStep:
    """One successful assignment step in a domain-aware operation execution."""

    source: Optional[DomainSource]
    before: Mapping[str, _Z3Expr]
    after: Mapping[str, _Z3Expr]
    path_conditions: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()


@dataclass(frozen=True)
class OperationBranch:
    """One source branch in a domain-aware operation execution."""

    branch_id: Optional[str]
    branch_kind: str
    selector: z3.ExprRef
    path_conditions: Tuple[z3.ExprRef, ...] = ()
    status: str = "sat"
    result_env: Optional[Mapping[str, _Z3Expr]] = None
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    failure: Optional[OperationFailure] = None

    def __post_init__(self) -> None:
        if self.branch_kind not in ("if", "elif", "else"):
            raise ValueError(f"Unsupported operation branch kind: {self.branch_kind}")
        if self.status not in ("sat", "unsat", "unknown"):
            raise ValueError(f"Unsupported operation branch status: {self.status}")
        if self.status == "unsat":
            if self.result_env is not None:
                raise ValueError(
                    "Unreachable operation branches must not carry result_env."
                )
            if self.definedness_constraints:
                raise ValueError(
                    "Unreachable operation branches must not carry definedness constraints."
                )
            if self.failure is not None:
                raise ValueError(
                    "Unreachable operation branches must not carry failures."
                )


@dataclass(frozen=True)
class OperationExecution:
    """Domain-aware operation block execution result."""

    env: Mapping[str, _Z3Expr]
    visible_names: Tuple[str, ...]
    expr_constraints: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    steps: Tuple[OperationStep, ...] = ()
    branches: Tuple[OperationBranch, ...] = ()
    failure: Optional[OperationFailure] = None


@dataclass
class _ExecutionResult:
    """Internal mutable execution carrier."""

    env: _Z3Env
    definedness_constraints: Tuple[DomainConstraint, ...]
    steps: Tuple[OperationStep, ...]
    branches: Tuple[OperationBranch, ...]
    failure: Optional[OperationFailure]
    next_step: int


def parse_operations(
    code: str, allowed_vars: Optional[List[str]] = None
) -> List[OperationStatement]:
    """
    Parse DSL operation code string into a list of operation statements.

    This function parses a DSL code string containing operation statements
    (assignments and ``if`` blocks) and converts them into model-layer
    operation statements. It can optionally validate that expressions only
    reference variables that are already available at that point in the block.
    Unknown assignment targets are treated as block-local temporary variables.

    :param code: DSL operation code string to parse
    :type code: str
    :param allowed_vars: List of initially available variable names, or ``None`` for free mode
    :type allowed_vars: Optional[List[str]]
    :return: List of parsed operation statements
    :rtype: List[OperationStatement]
    :raises ValueError: If an expression references a variable that is not yet available
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails

    Example::

        >>> ops = parse_operations("x = x + 1; y = 10;", allowed_vars=['x', 'y'])
        >>> len(ops)
        2
        >>> ops[0].var_name
        'x'

        >>> # Free mode - no variable restrictions
        >>> ops = parse_operations("a = b + c;", allowed_vars=None)

        >>> # Restricted mode - raises ValueError for variables used before assignment
        >>> ops = parse_operations("y = z + 1; z = 1;", allowed_vars=['x', 'y'])
        Traceback (most recent call last):
            ...
        ValueError: Variable 'z' is not in allowed variables: ['x', 'y']
    """
    parsed_node = parse_with_grammar_entry(code, "operational_statement_set")

    def _validate_expression_variables(expr, available_names: set) -> None:
        for var in expr.list_variables():
            if var.name not in available_names:
                raise ValueError(
                    f"Variable '{var.name}' is not in allowed variables: {allowed_vars}"
                )

    def _convert_statements(
        statements: List[dsl_nodes.OperationalStatement],
        available_names: Optional[set],
    ) -> List[OperationStatement]:
        converted = []
        current_names = None if available_names is None else set(available_names)

        for statement in statements:
            if isinstance(statement, dsl_nodes.OperationAssignment):
                expr = parse_expr_node_to_expr(statement.expr)
                if current_names is not None:
                    _validate_expression_variables(expr, current_names)
                    current_names.add(statement.name)

                converted.append(Operation(var_name=statement.name, expr=expr))
                continue

            if isinstance(statement, dsl_nodes.OperationIf):
                base_names = None if current_names is None else set(current_names)
                branches = []

                for branch in statement.branches:
                    condition = None
                    if branch.condition is not None:
                        condition = parse_expr_node_to_expr(branch.condition)
                        if base_names is not None:
                            _validate_expression_variables(condition, base_names)

                    branch_names = None if base_names is None else set(base_names)
                    branch_statements = _convert_statements(
                        branch.statements, branch_names
                    )
                    branches.append(
                        IfBlockBranch(
                            condition=condition,
                            statements=branch_statements,
                        )
                    )

                converted.append(IfBlock(branches=branches))
                continue

            raise TypeError(
                f"Unknown operational statement node type {type(statement)!r}."
            )

        return converted

    initial_names = None if allowed_vars is None else set(allowed_vars)
    return _convert_statements(parsed_node, initial_names)


def _execute_operation_statements_symbolically(
    statements: List[OperationStatement],
    exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute a sequence of operation statements symbolically.

    :param statements: Statements to execute in order.
    :type statements: List[OperationStatement]
    :param exprs: Current symbolic environment.
    :type exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Updated symbolic environment.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    """
    current_exprs = dict(exprs)

    for statement in statements:
        if isinstance(statement, Operation):
            current_exprs[statement.var_name] = expr_to_z3(
                statement.expr, current_exprs
            )
        elif isinstance(statement, IfBlock):
            current_exprs = _execute_if_block_symbolically(statement, current_exprs)
        else:
            raise TypeError(f"Unknown operation statement type {type(statement)!r}.")

    return current_exprs


def _execute_if_block_symbolically(
    if_block: IfBlock,
    exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute an ``if`` block symbolically with branch-local merge semantics.

    Each branch is symbolically executed from the same pre-``if`` environment.
    Only names that were already visible before entering the ``if`` block
    participate in the final merge. This keeps branch-local temporary
    variables out of the merged outer environment.

    :param if_block: If-block to execute.
    :type if_block: IfBlock
    :param exprs: Current symbolic environment.
    :type exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Merged symbolic environment after the if-block.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    """
    base_exprs = dict(exprs)
    visible_names = tuple(base_exprs.keys())
    branch_results = []

    for branch in if_block.branches:
        branch_results.append(
            (
                expr_to_z3(branch.condition, base_exprs)
                if branch.condition is not None
                else None,
                _execute_operation_statements_symbolically(
                    branch.statements, base_exprs
                ),
            )
        )

    merged_exprs = dict(base_exprs)
    for name in visible_names:
        merged_value = base_exprs[name]
        for branch_condition, branch_exprs in reversed(branch_results):
            if branch_condition is None:
                merged_value = branch_exprs[name]
            else:
                merged_value = z3.If(branch_condition, branch_exprs[name], merged_value)

        merged_exprs[name] = merged_value

    return merged_exprs


def _as_operation_list(
    operations: Union[OperationStatement, List[OperationStatement]],
) -> List[OperationStatement]:
    if isinstance(operations, OperationStatement):
        return [operations]
    return list(operations)


def _constraint_exprs(items: Sequence[DomainConstraint]) -> Tuple[z3.ExprRef, ...]:
    return tuple(item.constraint for item in items)


def _true_expr() -> z3.BoolRef:
    return z3.BoolVal(True)


def _and_expr(items: Sequence[z3.ExprRef]) -> z3.ExprRef:
    if not items:
        return _true_expr()
    if len(items) == 1:
        return items[0]
    return z3.And(*items)


def _path_guard(
    domains: Sequence[DomainConstraint],
    path_conditions: Sequence[z3.ExprRef],
) -> Tuple[DomainConstraint, ...]:
    if not domains:
        return ()
    if not path_conditions:
        return tuple(domains)
    guard = _and_expr(tuple(path_conditions))
    return tuple(
        DomainConstraint(
            z3.Implies(guard, item.constraint),
            source=item.source,
        )
        for item in domains
    )


def _operation_failure_from_translation(
    failure: TranslationFailure,
) -> OperationFailure:
    return OperationFailure(
        kind=failure.kind,
        reason=failure.reason,
        source=failure.source,
        translation_failure=failure,
    )


def _operation_failure(
    kind: str,
    reason: str,
    source: Optional[DomainSource],
) -> OperationFailure:
    return OperationFailure(kind=kind, reason=reason, source=source)


def _normalize_solver_status(status: str) -> str:
    return status if status in ("sat", "unsat") else "unknown"


def _translate_operation_expr(
    expr,
    env: _Z3Env,
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
):
    return translate_expr_domain(
        expr,
        env,
        assumptions=assumptions,
        path_conditions=(
            *path_conditions,
            *_constraint_exprs(definedness_constraints),
        ),
        source=source,
        prune_unreachable=prune_unreachable,
        timeout_ms=timeout_ms,
    )


def _branch_status(
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint],
    selector: z3.ExprRef,
    prune_unreachable: bool,
    timeout_ms: Optional[int],
) -> str:
    if not prune_unreachable:
        return "sat"
    result = is_sat(
        (
            *assumptions,
            *path_conditions,
            *_constraint_exprs(definedness_constraints),
            selector,
        ),
        timeout_ms=timeout_ms,
    )
    return _normalize_solver_status(result.kind)


def _execute_operation_statements_domain(
    statements: Sequence[OperationStatement],
    env: _Z3Env,
    *,
    visible_names: Tuple[str, ...],
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
    step_start: int,
) -> _ExecutionResult:
    current_env = dict(env)
    current_domains: Tuple[DomainConstraint, ...] = tuple(definedness_constraints)
    steps: List[OperationStep] = []
    branches: List[OperationBranch] = []
    step_index = step_start

    for statement in statements:
        if isinstance(statement, Operation):
            before = dict(current_env)
            step_source = (
                DomainSource(
                    label=source.label,
                    step=step_index,
                    snapshot=source.snapshot,
                    prefix_id=source.prefix_id,
                )
                if source is not None
                else DomainSource(step=step_index)
            )
            result = _translate_operation_expr(
                statement.expr,
                current_env,
                assumptions=assumptions,
                path_conditions=path_conditions,
                definedness_constraints=current_domains,
                source=step_source,
                prune_unreachable=prune_unreachable,
                timeout_ms=timeout_ms,
            )
            step_domains = _path_guard(
                result.definedness_constraints,
                path_conditions,
            )
            combined_domains = (*current_domains, *step_domains)
            if result.failure is not None:
                return _ExecutionResult(
                    env=current_env,
                    definedness_constraints=combined_domains,
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=_operation_failure_from_translation(result.failure),
                    next_step=step_index,
                )

            current_env = dict(current_env)
            current_env[statement.var_name] = result.z3_expr
            step = OperationStep(
                source=step_source,
                before=before,
                after=dict(current_env),
                path_conditions=tuple(path_conditions),
                definedness_constraints=step_domains,
            )
            steps.append(step)
            current_domains = combined_domains
            step_index += 1
            continue

        if isinstance(statement, IfBlock):
            result = _execute_if_block_domain(
                statement,
                current_env,
                visible_names=visible_names,
                assumptions=assumptions,
                path_conditions=path_conditions,
                definedness_constraints=current_domains,
                source=source,
                prune_unreachable=prune_unreachable,
                timeout_ms=timeout_ms,
                step_start=step_index,
            )
            branches.extend(result.branches)
            steps.extend(result.steps)
            current_env = result.env
            current_domains = result.definedness_constraints
            step_index = result.next_step
            if result.failure is not None:
                return _ExecutionResult(
                    env=current_env,
                    definedness_constraints=current_domains,
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=result.failure,
                    next_step=step_index,
                )
            continue

        return _ExecutionResult(
            env=current_env,
            definedness_constraints=current_domains,
            steps=tuple(steps),
            branches=tuple(branches),
            failure=_operation_failure(
                "unsupported_statement",
                f"Unknown operation statement type {type(statement).__name__}.",
                source,
            ),
            next_step=step_index,
        )

    return _ExecutionResult(
        env=current_env,
        definedness_constraints=current_domains,
        steps=tuple(steps),
        branches=tuple(branches),
        failure=None,
        next_step=step_index,
    )


def _execute_if_block_domain(
    if_block: IfBlock,
    env: _Z3Env,
    *,
    visible_names: Tuple[str, ...],
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
    step_start: int,
) -> _ExecutionResult:
    base_env = dict(env)
    merge_names = tuple(base_env.keys())
    prefix_selectors: List[z3.ExprRef] = []
    branch_results = []
    branches: List[OperationBranch] = []
    steps: List[OperationStep] = []
    all_domains: List[DomainConstraint] = list(definedness_constraints)
    step_index = step_start

    for index, branch in enumerate(if_block.branches):
        branch_kind = (
            "else" if branch.condition is None else ("if" if index == 0 else "elif")
        )
        branch_id = str(index)
        arrival_conditions = (*path_conditions, *prefix_selectors)
        local_domains: List[DomainConstraint] = []

        if branch.condition is None:
            condition_expr = None
            selector = _and_expr(tuple(prefix_selectors))
        else:
            if prefix_selectors:
                arrival_status = _branch_status(
                    assumptions=assumptions,
                    path_conditions=path_conditions,
                    definedness_constraints=tuple(all_domains),
                    selector=_and_expr(tuple(prefix_selectors)),
                    prune_unreachable=prune_unreachable,
                    timeout_ms=timeout_ms,
                )
                if arrival_status == "unsat":
                    branches.append(
                        OperationBranch(
                            branch_id=branch_id,
                            branch_kind=branch_kind,
                            selector=_and_expr(tuple(prefix_selectors)),
                            path_conditions=arrival_conditions,
                            status="unsat",
                            result_env=None,
                            definedness_constraints=(),
                            failure=None,
                        )
                    )
                    continue

            condition_result = _translate_operation_expr(
                branch.condition,
                base_env,
                assumptions=assumptions,
                path_conditions=arrival_conditions,
                definedness_constraints=all_domains,
                source=source,
                prune_unreachable=prune_unreachable,
                timeout_ms=timeout_ms,
            )
            condition_domains = _path_guard(
                condition_result.definedness_constraints,
                arrival_conditions,
            )
            all_domains.extend(condition_domains)
            local_domains.extend(condition_domains)
            if condition_result.failure is not None:
                return _ExecutionResult(
                    env=base_env,
                    definedness_constraints=tuple(all_domains),
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=_operation_failure_from_translation(
                        condition_result.failure
                    ),
                    next_step=step_index,
                )
            if not z3.is_bool(condition_result.z3_expr):
                return _ExecutionResult(
                    env=base_env,
                    definedness_constraints=tuple(all_domains),
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=_operation_failure(
                        "non_bool_condition",
                        "Operation if condition did not translate to a Boolean Z3 expression.",
                        source,
                    ),
                    next_step=step_index,
                )
            condition_expr = condition_result.z3_expr
            selector = (
                condition_expr
                if not prefix_selectors
                else z3.And(*prefix_selectors, condition_expr)
            )

        status = _branch_status(
            assumptions=assumptions,
            path_conditions=path_conditions,
            definedness_constraints=tuple(all_domains),
            selector=selector,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )

        if status == "unsat":
            branches.append(
                OperationBranch(
                    branch_id=branch_id,
                    branch_kind=branch_kind,
                    selector=selector,
                    path_conditions=(*path_conditions, selector),
                    status=status,
                    result_env=None,
                    definedness_constraints=(),
                    failure=None,
                )
            )
        else:
            branch_result = _execute_operation_statements_domain(
                branch.statements,
                base_env,
                visible_names=visible_names,
                assumptions=assumptions,
                path_conditions=(*path_conditions, selector),
                definedness_constraints=tuple(all_domains),
                source=source,
                prune_unreachable=prune_unreachable,
                timeout_ms=timeout_ms,
                step_start=step_index,
            )
            steps.extend(branch_result.steps)
            nested_branches = branch_result.branches
            branch_body_definedness = branch_result.definedness_constraints[
                len(all_domains) :
            ]
            branch_definedness = (*local_domains, *branch_body_definedness)
            result_env = {
                name: branch_result.env[name]
                for name in merge_names
                if name in branch_result.env
            }
            branch_obj = OperationBranch(
                branch_id=branch_id,
                branch_kind=branch_kind,
                selector=selector,
                path_conditions=(*path_conditions, selector),
                status=status,
                result_env=result_env,
                definedness_constraints=branch_definedness,
                failure=branch_result.failure,
            )
            branches.append(branch_obj)
            branches.extend(nested_branches)
            all_domains.extend(branch_body_definedness)
            branch_results.append((selector, result_env))
            step_index = branch_result.next_step
            if branch_result.failure is not None:
                return _ExecutionResult(
                    env=base_env,
                    definedness_constraints=tuple(all_domains),
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=branch_result.failure,
                    next_step=step_index,
                )

        if branch.condition is not None:
            prefix_selectors.append(z3.Not(condition_expr))

    merged_env = dict(base_env)
    for name in merge_names:
        merged_value = base_env[name]
        for selector, result_env in reversed(branch_results):
            merged_value = z3.If(selector, result_env[name], merged_value)
        merged_env[name] = merged_value

    return _ExecutionResult(
        env=merged_env,
        definedness_constraints=tuple(all_domains),
        steps=tuple(steps),
        branches=tuple(branches),
        failure=None,
        next_step=step_index,
    )


def execute_operations_domain(
    operations: Union[OperationStatement, List[OperationStatement]],
    var_exprs: Dict[str, _Z3Expr],
    *,
    assumptions: Sequence[z3.ExprRef] = (),
    path_conditions: Sequence[z3.ExprRef] = (),
    source: Optional[DomainSource] = None,
    prune_unreachable: bool = True,
    timeout_ms: Optional[int] = None,
) -> OperationExecution:
    """Execute operation statements with runtime-definedness metadata."""
    operation_list = _as_operation_list(operations)
    visible_names = tuple(var_exprs.keys())
    result = _execute_operation_statements_domain(
        operation_list,
        dict(var_exprs),
        visible_names=visible_names,
        assumptions=tuple(assumptions),
        path_conditions=tuple(path_conditions),
        definedness_constraints=(),
        source=source,
        prune_unreachable=prune_unreachable,
        timeout_ms=timeout_ms,
        step_start=0,
    )
    env = {name: result.env[name] for name in visible_names}
    return OperationExecution(
        env=env,
        visible_names=visible_names,
        expr_constraints=(),
        definedness_constraints=result.definedness_constraints,
        steps=result.steps,
        branches=result.branches,
        failure=result.failure,
    )


def merge_operation_definedness(*items) -> Tuple[DomainConstraint, ...]:
    """Flatten operation-domain and domain-constraint inputs in order."""
    merged: List[DomainConstraint] = []
    for item in items:
        if isinstance(item, DomainConstraint):
            merged.append(item)
        elif isinstance(item, (OperationExecution, OperationStep, OperationBranch)):
            merged.extend(item.definedness_constraints)
        elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            for sub_item in item:
                if isinstance(
                    sub_item,
                    (
                        DomainConstraint,
                        OperationExecution,
                        OperationStep,
                        OperationBranch,
                    ),
                ):
                    merged.extend(merge_operation_definedness(sub_item))
                    continue
                raise TypeError(
                    "Unsupported operation definedness item: {type_name}".format(
                        type_name=type(sub_item).__name__,
                    )
                )
        else:
            raise TypeError(
                "Unsupported operation definedness item: {type_name}".format(
                    type_name=type(item).__name__,
                )
            )
    return merge_definedness_constraints(merged)


def execute_operations(
    operations: Union[OperationStatement, List[OperationStatement]],
    var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute operation statements on a Z3 variable expression dictionary.

    This function takes one operation statement or a statement list and
    symbolically executes it against a variable-expression dictionary.
    Assignments update the current symbolic environment directly, while ``if``
    blocks evaluate each branch from the same pre-``if`` environment and then
    merge only the names that were already visible before entering the block.
    Statements are executed in order, so later statements can reference the
    results of earlier ones.

    This performs symbolic execution - expressions are built up symbolically
    rather than being evaluated to concrete values.

    :param operations: Single statement or list of statements to execute
    :type operations: Union[OperationStatement, List[OperationStatement]]
    :param var_exprs: Dictionary mapping variable names to current Z3 expressions
    :type var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: New variable expression dictionary with updated global Z3 expressions
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :raises ValueError: If a variable referenced in an expression is not available in the current block scope

    Example::

        >>> import z3
        >>> from pyfcstm.model.model import Operation
        >>> from pyfcstm.model.expr import Variable, Integer, BinaryOp
        >>>
        >>> # Create Z3 symbolic variables
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>> var_exprs = {'x': x, 'y': y}
        >>>
        >>> # Create operations: x = x + 2; y = y + x;
        >>> op1 = Operation(var_name='x', expr=BinaryOp(x=Variable('x'), op='+', y=Integer(2)))
        >>> op2 = Operation(var_name='y', expr=BinaryOp(x=Variable('y'), op='+', y=Variable('x')))
        >>>
        >>> # Execute operations symbolically
        >>> new_exprs = execute_operations([op1, op2], var_exprs)
        >>> # new_exprs['x'] is the Z3 expression: x + 2
        >>> # new_exprs['y'] is the Z3 expression: y + (x + 2)
        >>>
        >>> # Can verify with solver
        >>> solver = z3.Solver()
        >>> solver.add(x == 5, y == 10)
        >>> solver.add(new_exprs['x'] == 7)  # 5 + 2
        >>> solver.add(new_exprs['y'] == 17)  # 10 + 7
        >>> solver.check()
        sat
    """
    operation_list = _as_operation_list(operations)
    original_var_names = list(var_exprs.keys())
    current_exprs = _execute_operation_statements_symbolically(
        operation_list, var_exprs
    )

    return {name: current_exprs[name] for name in original_var_names}


__all__ = [
    "OperationBranch",
    "OperationExecution",
    "OperationFailure",
    "OperationSource",
    "OperationStep",
    "execute_operations",
    "execute_operations_domain",
    "merge_operation_definedness",
    "parse_operations",
]
