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
    """Pure solver-layer operation execution failure.

    :param kind: Normalized failure kind.
    :type kind: str
    :param reason: Human-readable failure reason.
    :type reason: str
    :param source: Optional source metadata, defaults to ``None``.
    :type source: Optional[DomainSource], optional
    :param translation_failure: Underlying expression translation failure,
        defaults to ``None``.
    :type translation_failure: Optional[TranslationFailure], optional

    Example::

        >>> failure = OperationFailure("value_error", "bad operation")
        >>> failure.kind
        'value_error'
    """

    kind: str
    reason: str
    source: Optional[DomainSource] = None
    translation_failure: Optional[TranslationFailure] = None


@dataclass(frozen=True)
class OperationStep:
    """One successful assignment step in a domain-aware operation execution.

    :param source: Optional source metadata for the assignment.
    :type source: Optional[DomainSource]
    :param before: Symbolic environment before the assignment.
    :type before: Mapping[str, Union[z3.ArithRef, z3.BoolRef]]
    :param after: Symbolic environment after the assignment.
    :type after: Mapping[str, Union[z3.ArithRef, z3.BoolRef]]
    :param path_conditions: Predicates that must hold before this assignment,
        defaults to ``()``.
    :type path_conditions: Tuple[z3.ExprRef, ...], optional
    :param definedness_constraints: Runtime-definedness constraints introduced
        by this assignment, defaults to ``()``.
    :type definedness_constraints: Tuple[DomainConstraint, ...], optional

    Example::

        >>> import z3
        >>> step = OperationStep(None, {"x": z3.Int("x")}, {"x": z3.IntVal(1)})
        >>> step.after["x"]
        1
    """

    source: Optional[DomainSource]
    before: Mapping[str, _Z3Expr]
    after: Mapping[str, _Z3Expr]
    path_conditions: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()


@dataclass(frozen=True)
class OperationBranch:
    """One source branch in a domain-aware operation execution.

    :param branch_id: Stable branch identifier within the local ``if`` block.
    :type branch_id: Optional[str]
    :param branch_kind: Branch kind: ``"if"``, ``"elif"``, or ``"else"``.
    :type branch_kind: str
    :param selector: Z3 predicate selecting this branch.
    :type selector: z3.ExprRef
    :param path_conditions: Predicates needed to reach the branch, defaults to
        ``()``.
    :type path_conditions: Tuple[z3.ExprRef, ...], optional
    :param status: Branch reachability status, defaults to ``"sat"``.
    :type status: str, optional
    :param result_env: Branch-local result environment, defaults to ``None``.
    :type result_env: Optional[Mapping[str, Union[z3.ArithRef, z3.BoolRef]]], optional
    :param definedness_constraints: Runtime-definedness constraints introduced
        by this branch, defaults to ``()``.
    :type definedness_constraints: Tuple[DomainConstraint, ...], optional
    :param failure: Branch-local operation failure, defaults to ``None``.
    :type failure: Optional[OperationFailure], optional

    Example::

        >>> import z3
        >>> branch = OperationBranch("0", "if", z3.Bool("cond"))
        >>> branch.branch_kind
        'if'
    """

    branch_id: Optional[str]
    branch_kind: str
    selector: z3.ExprRef
    path_conditions: Tuple[z3.ExprRef, ...] = ()
    status: str = "sat"
    result_env: Optional[Mapping[str, _Z3Expr]] = None
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    failure: Optional[OperationFailure] = None

    def __post_init__(self) -> None:
        """Validate branch invariants after dataclass initialization.

        :return: ``None``.
        :rtype: None
        :raises ValueError: If the branch kind, status, or unreachable-branch
            payload is inconsistent.

        Example::

            >>> import z3
            >>> OperationBranch("0", "if", z3.Bool("c")).status
            'sat'
        """
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
    """Domain-aware operation block execution result.

    The result keeps the final visible environment separate from evidence about
    steps, branches, and runtime-definedness side conditions.  Temporary names
    created inside a block can appear in internal steps, but :attr:`env` exposes
    only names visible before execution started.

    :param env: Final visible symbolic environment.
    :type env: Mapping[str, Union[z3.ArithRef, z3.BoolRef]]
    :param visible_names: Names preserved in the public final environment.
    :type visible_names: Tuple[str, ...]
    :param expr_constraints: Solver-only value constraints, defaults to ``()``.
    :type expr_constraints: Tuple[z3.ExprRef, ...], optional
    :param definedness_constraints: Runtime-definedness constraints collected
        during execution, defaults to ``()``.
    :type definedness_constraints: Tuple[DomainConstraint, ...], optional
    :param steps: Assignment-step evidence, defaults to ``()``.
    :type steps: Tuple[OperationStep, ...], optional
    :param branches: Branch reachability evidence, defaults to ``()``.
    :type branches: Tuple[OperationBranch, ...], optional
    :param failure: Expected execution failure, defaults to ``None``.
    :type failure: Optional[OperationFailure], optional

    Example::

        >>> import z3
        >>> result = OperationExecution({"x": z3.IntVal(1)}, ("x",))
        >>> result.visible_names
        ('x',)
    """

    env: Mapping[str, _Z3Expr]
    visible_names: Tuple[str, ...]
    expr_constraints: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    steps: Tuple[OperationStep, ...] = ()
    branches: Tuple[OperationBranch, ...] = ()
    failure: Optional[OperationFailure] = None


@dataclass
class _ExecutionResult:
    """Internal execution carrier used while walking operation statements.

    :param env: Current symbolic environment.
    :type env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param definedness_constraints: Runtime-definedness constraints collected
        so far.
    :type definedness_constraints: Tuple[DomainConstraint, ...]
    :param steps: Assignment-step evidence collected so far.
    :type steps: Tuple[OperationStep, ...]
    :param branches: Branch evidence collected so far.
    :type branches: Tuple[OperationBranch, ...]
    :param failure: Expected execution failure, or ``None``.
    :type failure: Optional[OperationFailure]
    :param next_step: Next assignment-step index.
    :type next_step: int

    Example::

        >>> result = _ExecutionResult({}, (), (), (), None, 0)
        >>> result.failure is None
        True
    """

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
        """Validate expression variable references against currently visible names.

        :param expr: Model expression whose variable references should be
            checked.
        :type expr: pyfcstm.model.expr.Expr
        :param available_names: Names visible before evaluating ``expr``.
        :type available_names: set
        :return: ``None``.
        :rtype: None
        :raises ValueError: If ``expr`` references a variable that is not yet
            available in the current operation block.

        Example::

            >>> # This nested helper is exercised through parse_operations().
            >>> parse_operations("tmp = x + 1;", allowed_vars=["x"])[0].var_name
            'tmp'
        """
        for var in expr.list_variables():
            if var.name not in available_names:
                raise ValueError(
                    f"Variable '{var.name}' is not in allowed variables: {allowed_vars}"
                )

    def _convert_statements(
        statements: List[dsl_nodes.OperationalStatement],
        available_names: Optional[set],
    ) -> List[OperationStatement]:
        """Convert parsed DSL operation nodes into model statements.

        The conversion tracks block-local temporary variables in declaration
        order.  Assignment targets become visible after their expression has
        been validated; ``if`` branch bodies inherit only the names visible
        before entering the branch.

        :param statements: Parsed DSL operation statement nodes.
        :type statements: List[pyfcstm.dsl.node.OperationalStatement]
        :param available_names: Names visible before the statement list, or
            ``None`` when reference validation is disabled.
        :type available_names: Optional[set]
        :return: Converted model operation statements.
        :rtype: List[OperationStatement]
        :raises TypeError: If a parsed statement node type is unknown.
        :raises ValueError: If a referenced variable is not available.

        Example::

            >>> # The helper keeps branch-local temporaries from escaping.
            >>> parse_operations("if [x > 0] { tmp = x; }", ["x"])
            [IfBlock(branches=[IfBlockBranch(condition=BinaryOp(...), statements=[Operation(var_name='tmp', expr=Variable(name='x'))])])]
        """
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

    Example::

        >>> import z3
        >>> ops = parse_operations("x = x + 1;", allowed_vars=["x"])
        >>> env = _execute_operation_statements_symbolically(ops, {"x": z3.IntVal(1)})
        >>> z3.simplify(env["x"])
        2
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

    Example::

        >>> import z3
        >>> block = parse_operations("if [x > 0] { y = 1; } else { y = 2; }", ["x", "y"])[0]
        >>> env = _execute_if_block_symbolically(block, {"x": z3.Int("x"), "y": z3.Int("y")})
        >>> str(env["y"])
        'If(0 < x, 1, 2)'
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
    """Normalize one operation statement or statement list to a list.

    :param operations: Single statement or list of statements.
    :type operations: Union[OperationStatement, List[OperationStatement]]
    :return: Operation statement list.
    :rtype: List[OperationStatement]

    Example::

        >>> op = parse_operations("x = 1;")[0]
        >>> _as_operation_list(op) == [op]
        True
    """
    if isinstance(operations, OperationStatement):
        return [operations]
    return list(operations)


def _constraint_exprs(items: Sequence[DomainConstraint]) -> Tuple[z3.ExprRef, ...]:
    """Return raw Z3 predicates from domain-constraint objects.

    :param items: Domain constraints.
    :type items: Sequence[DomainConstraint]
    :return: Raw Z3 predicates.
    :rtype: Tuple[z3.ExprRef, ...]

    Example::

        >>> import z3
        >>> _constraint_exprs((DomainConstraint(z3.Int("x") != 0),))
        (x != 0,)
    """
    return tuple(item.constraint for item in items)


def _true_expr() -> z3.BoolRef:
    """Return the constant true Z3 predicate.

    :return: Z3 Boolean true.
    :rtype: z3.BoolRef

    Example::

        >>> _true_expr()
        True
    """
    return z3.BoolVal(True)


def _and_expr(items: Sequence[z3.ExprRef]) -> z3.ExprRef:
    """Conjoin predicates while keeping empty and singleton cases compact.

    :param items: Predicates to conjoin.
    :type items: Sequence[z3.ExprRef]
    :return: Combined predicate.
    :rtype: z3.ExprRef

    Example::

        >>> import z3
        >>> _and_expr((z3.BoolVal(True), z3.BoolVal(False)))
        And(True, False)
    """
    if not items:
        return _true_expr()
    if len(items) == 1:
        return items[0]
    return z3.And(*items)


def _path_guard(
    domains: Sequence[DomainConstraint],
    path_conditions: Sequence[z3.ExprRef],
) -> Tuple[DomainConstraint, ...]:
    """Guard domain constraints by the path that introduces them.

    :param domains: Runtime-definedness constraints from the current step or
        branch.
    :type domains: Sequence[DomainConstraint]
    :param path_conditions: Predicates needed to reach the step or branch.
    :type path_conditions: Sequence[z3.ExprRef]
    :return: Guarded domain constraints.
    :rtype: Tuple[DomainConstraint, ...]

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> guarded = _path_guard((DomainConstraint(x != 0),), (x > 1,))
        >>> guarded[0].constraint
        Implies(x > 1, x != 0)
    """
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
    """Wrap an expression translation failure as an operation failure.

    :param failure: Expression translation failure.
    :type failure: TranslationFailure
    :return: Operation failure preserving the original failure object.
    :rtype: OperationFailure

    Example::

        >>> failure = TranslationFailure("value_error", "bad expression")
        >>> _operation_failure_from_translation(failure).translation_failure is failure
        True
    """
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
    """Create an operation failure without a nested translation failure.

    :param kind: Normalized failure kind.
    :type kind: str
    :param reason: Human-readable failure reason.
    :type reason: str
    :param source: Optional source metadata.
    :type source: Optional[DomainSource]
    :return: Operation failure.
    :rtype: OperationFailure

    Example::

        >>> _operation_failure("unsupported", "bad op", None).kind
        'unsupported'
    """
    return OperationFailure(kind=kind, reason=reason, source=source)


def _normalize_solver_status(status: str) -> str:
    """Normalize solver status strings for operation evidence.

    :param status: Raw status string from a solver helper.
    :type status: str
    :return: ``"sat"``, ``"unsat"``, or ``"unknown"``.
    :rtype: str

    Example::

        >>> _normalize_solver_status("timeout")
        'unknown'
    """
    return status if status in ("sat", "unsat") else "unknown"


def _execution_point_status(
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
) -> str:
    """Return whether the current execution point is reachable.

    :param assumptions: Caller-known facts for the whole operation block.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach the current point.
    :type path_conditions: Sequence[z3.ExprRef]
    :param definedness_constraints: Runtime-definedness constraints collected
        before the current point.
    :type definedness_constraints: Sequence[DomainConstraint]
    :param prune_unreachable: Whether to run the reachability query.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int]
    :return: Normalized reachability status.
    :rtype: str

    Example::

        >>> _execution_point_status(
        ...     assumptions=(),
        ...     path_conditions=(),
        ...     definedness_constraints=(),
        ...     prune_unreachable=False,
        ...     timeout_ms=None,
        ... )
        'sat'
    """
    if not prune_unreachable:
        return "sat"
    result = is_sat(
        (
            *assumptions,
            *path_conditions,
            *_constraint_exprs(definedness_constraints),
        ),
        timeout_ms=timeout_ms,
    )
    return _normalize_solver_status(result.kind)


def _condition_expr_for_metadata(expr, env: _Z3Env) -> Optional[z3.ExprRef]:
    """Best-effort translation used only for unreachable-branch evidence.

    :param expr: Branch condition expression.
    :type expr: object
    :param env: Symbolic environment used for translation.
    :type env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Boolean condition expression, or ``None`` if it cannot be built
        without affecting execution.
    :rtype: Optional[z3.ExprRef]

    Example::

        >>> import z3
        >>> cond = parse_operations("if [x > 0] { y = 1; }", ["x", "y"])[0].branches[0].condition
        >>> _condition_expr_for_metadata(cond, {"x": z3.Int("x"), "y": z3.Int("y")})
        0 < x
    """
    try:
        condition_expr = expr_to_z3(expr, env)
    except NotImplementedError:
        # NotImplementedError: expr_to_z3 raises this for supported expression
        # nodes whose math function is intentionally unsupported by Z3.
        return None
    except ValueError:
        # ValueError: expr_to_z3 raises this for unknown variables, unknown
        # operators, and unsupported expression object types.
        return None
    except TypeError:
        # TypeError: Python/Z3 operator overloads can reject malformed operand
        # combinations before Z3 wraps the failure.
        return None
    except z3.Z3Exception:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None
    if not z3.is_bool(condition_expr):
        return None
    return condition_expr


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
    """Translate an operation expression in the current execution context.

    :param expr: Operation expression to translate.
    :type expr: object
    :param env: Current symbolic environment.
    :type env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param assumptions: Caller-known block facts.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach this expression.
    :type path_conditions: Sequence[z3.ExprRef]
    :param definedness_constraints: Runtime-definedness constraints collected
        before this expression.
    :type definedness_constraints: Sequence[DomainConstraint]
    :param source: Optional source metadata.
    :type source: Optional[DomainSource]
    :param prune_unreachable: Whether nested conditional branches should be
        pruned.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int]
    :return: Domain-aware expression translation.
    :rtype: pyfcstm.solver.domain.ExprDomain

    Example::

        >>> import z3
        >>> expr = parse_operations("x = 1 / y;", ["x", "y"])[0].expr
        >>> result = _translate_operation_expr(
        ...     expr,
        ...     {"x": z3.Int("x"), "y": z3.Int("y")},
        ...     assumptions=(),
        ...     path_conditions=(),
        ...     definedness_constraints=(),
        ...     source=None,
        ...     prune_unreachable=True,
        ...     timeout_ms=None,
        ... )
        >>> [str(item.constraint) for item in result.definedness_constraints]
        ['y != 0']
    """
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
    """Return whether a candidate operation branch is reachable.

    :param assumptions: Caller-known block facts.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach the enclosing branch
        point.
    :type path_conditions: Sequence[z3.ExprRef]
    :param definedness_constraints: Runtime-definedness constraints collected
        before this branch.
    :type definedness_constraints: Sequence[DomainConstraint]
    :param selector: Branch selector predicate.
    :type selector: z3.ExprRef
    :param prune_unreachable: Whether to run the reachability query.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int]
    :return: Normalized branch reachability status.
    :rtype: str

    Example::

        >>> import z3
        >>> _branch_status(
        ...     assumptions=(),
        ...     path_conditions=(),
        ...     definedness_constraints=(),
        ...     selector=z3.BoolVal(False),
        ...     prune_unreachable=True,
        ...     timeout_ms=None,
        ... )
        'unsat'
    """
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


def _merge_branch_env(
    base_env: _Z3Env,
    merge_names: Sequence[str],
    branch_results: Sequence[Tuple[z3.ExprRef, Mapping[str, _Z3Expr]]],
) -> _Z3Env:
    """Merge branch environments with nested Z3 ``If`` expressions.

    :param base_env: Environment before entering the ``if`` block.
    :type base_env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param merge_names: Names that are visible outside the ``if`` block.
    :type merge_names: Sequence[str]
    :param branch_results: Branch selectors and their result environments.
    :type branch_results: Sequence[Tuple[z3.ExprRef, Mapping[str, Union[z3.ArithRef, z3.BoolRef]]]]
    :return: Merged symbolic environment.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]

    Example::

        >>> import z3
        >>> merged = _merge_branch_env(
        ...     {"x": z3.Int("x")},
        ...     ("x",),
        ...     ((z3.Bool("take"), {"x": z3.IntVal(1)}),),
        ... )
        >>> str(merged["x"])
        'If(take, 1, x)'
    """
    merged_env = dict(base_env)
    for name in merge_names:
        merged_value = base_env[name]
        for selector, result_env in reversed(branch_results):
            merged_value = z3.If(selector, result_env[name], merged_value)
        merged_env[name] = merged_value
    return merged_env


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
    """Execute a statement sequence with path and domain evidence.

    :param statements: Operation statements to execute in order.
    :type statements: Sequence[OperationStatement]
    :param env: Starting symbolic environment.
    :type env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param visible_names: Names visible at the public block boundary.
    :type visible_names: Tuple[str, ...]
    :param assumptions: Caller-known block facts.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach the statement sequence.
    :type path_conditions: Sequence[z3.ExprRef]
    :param definedness_constraints: Runtime-definedness constraints collected
        before the sequence starts.
    :type definedness_constraints: Sequence[DomainConstraint]
    :param source: Optional source metadata copied into step-level metadata.
    :type source: Optional[DomainSource]
    :param prune_unreachable: Whether to stop translating paths proved
        unreachable.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int]
    :param step_start: First assignment-step index for this sequence.
    :type step_start: int
    :return: Internal execution carrier.
    :rtype: _ExecutionResult

    Example::

        >>> import z3
        >>> ops = parse_operations("x = x + 1;", ["x"])
        >>> result = _execute_operation_statements_domain(
        ...     ops,
        ...     {"x": z3.IntVal(1)},
        ...     visible_names=("x",),
        ...     assumptions=(),
        ...     path_conditions=(),
        ...     definedness_constraints=(),
        ...     source=None,
        ...     prune_unreachable=True,
        ...     timeout_ms=None,
        ...     step_start=0,
        ... )
        >>> z3.simplify(result.env["x"])
        2
    """
    current_env = dict(env)
    current_domains: Tuple[DomainConstraint, ...] = tuple(definedness_constraints)
    steps: List[OperationStep] = []
    branches: List[OperationBranch] = []
    step_index = step_start

    for statement in statements:
        point_status = _execution_point_status(
            assumptions=assumptions,
            path_conditions=path_conditions,
            definedness_constraints=current_domains,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        if point_status == "unsat":
            break

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
    """Execute an ``if`` block with path-sensitive branch pruning.

    :param if_block: If-block to execute.
    :type if_block: IfBlock
    :param env: Environment before the ``if`` block.
    :type env: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param visible_names: Names visible at the public block boundary.
    :type visible_names: Tuple[str, ...]
    :param assumptions: Caller-known block facts.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach the ``if`` block.
    :type path_conditions: Sequence[z3.ExprRef]
    :param definedness_constraints: Runtime-definedness constraints collected
        before the ``if`` block.
    :type definedness_constraints: Sequence[DomainConstraint]
    :param source: Optional source metadata copied into nested step metadata.
    :type source: Optional[DomainSource]
    :param prune_unreachable: Whether to skip branches proved unreachable.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int]
    :param step_start: First assignment-step index inside the block.
    :type step_start: int
    :return: Internal execution carrier.
    :rtype: _ExecutionResult

    Example::

        >>> import z3
        >>> block = parse_operations("if [x > 0] { y = 1; } else { y = 2; }", ["x", "y"])[0]
        >>> result = _execute_if_block_domain(
        ...     block,
        ...     {"x": z3.Int("x"), "y": z3.Int("y")},
        ...     visible_names=("x", "y"),
        ...     assumptions=(),
        ...     path_conditions=(),
        ...     definedness_constraints=(),
        ...     source=None,
        ...     prune_unreachable=True,
        ...     timeout_ms=None,
        ...     step_start=0,
        ... )
        >>> [branch.branch_kind for branch in result.branches]
        ['if', 'else']
    """
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
                    condition_expr = _condition_expr_for_metadata(
                        branch.condition, base_env
                    )
                    selector = (
                        _and_expr((*prefix_selectors, condition_expr))
                        if condition_expr is not None
                        else _and_expr(tuple(prefix_selectors))
                    )
                    branches.append(
                        OperationBranch(
                            branch_id=branch_id,
                            branch_kind=branch_kind,
                            selector=selector,
                            path_conditions=(*path_conditions, selector),
                            status="unsat",
                            result_env=None,
                            definedness_constraints=(),
                            failure=None,
                        )
                    )
                    if condition_expr is not None:
                        prefix_selectors.append(z3.Not(condition_expr))
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
                    env=_merge_branch_env(base_env, merge_names, branch_results),
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
                    env=_merge_branch_env(base_env, merge_names, branch_results),
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
                    env=_merge_branch_env(base_env, merge_names, branch_results),
                    definedness_constraints=tuple(all_domains),
                    steps=tuple(steps),
                    branches=tuple(branches),
                    failure=branch_result.failure,
                    next_step=step_index,
                )

        if branch.condition is not None:
            prefix_selectors.append(z3.Not(condition_expr))

    merged_env = _merge_branch_env(base_env, merge_names, branch_results)

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
    """Execute operation statements with runtime-definedness metadata.

    This path-sensitive executor preserves legacy symbolic assignment behavior
    while also returning branch evidence and constraints needed for FCSTM
    runtime-definedness.  The returned environment contains only variables that
    were visible before execution started; block-local temporaries stay internal.

    :param operations: Single operation statement or statement list.
    :type operations: Union[OperationStatement, List[OperationStatement]]
    :param var_exprs: Starting symbolic environment.
    :type var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param assumptions: Caller-known facts added to reachability checks,
        defaults to ``()``.
    :type assumptions: Sequence[z3.ExprRef], optional
    :param path_conditions: Predicates needed to reach this block, defaults to
        ``()``.
    :type path_conditions: Sequence[z3.ExprRef], optional
    :param source: Optional source metadata copied into step evidence, defaults
        to ``None``.
    :type source: Optional[DomainSource], optional
    :param prune_unreachable: Whether to skip paths proved unreachable,
        defaults to ``True``.
    :type prune_unreachable: bool, optional
    :param timeout_ms: Optional solver timeout in milliseconds.
    :type timeout_ms: Optional[int], optional
    :return: Domain-aware operation execution result.
    :rtype: OperationExecution

    Example::

        >>> import z3
        >>> ops = parse_operations("x = x + 1;", allowed_vars=["x"])
        >>> result = execute_operations_domain(ops, {"x": z3.Int("x")})
        >>> result.failure is None
        True
        >>> len(result.steps)
        1
    """
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
    """Flatten operation-domain and domain-constraint inputs in order.

    :param items: Domain constraints, operation execution objects, operation
        steps, operation branches, or iterables of those objects.
    :type items: object
    :return: Flattened runtime-definedness constraints.
    :rtype: Tuple[DomainConstraint, ...]
    :raises TypeError: If any item is not a supported operation-domain shape.

    Example::

        >>> import z3
        >>> item = DomainConstraint(z3.Int("x") != 0)
        >>> merge_operation_definedness(item) == (item,)
        True
    """
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
