"""Conservative, query-specific elimination of unobserved integer writes.

The existing use-def graph supplies the dependency closure. Arithmetic whose
runtime totality is not established remains in the cone, including division,
floating-point calculations, powers and mathematical functions. This keeps
scenario feasibility and UNSAT explanations valid without replaying an absent
counterexample. No solver is used to decide which assignments to remove.
"""

from dataclasses import dataclass, field, replace
from typing import Optional, Tuple

from pyfcstm.diagnostics.analyzers.use_def import (
    build_use_def_graph,
    collect_expr_variables,
)
from .errors import BmcBuildError
from pyfcstm.model import IfBlock, Operation
from pyfcstm.model.expr import BinaryOp, Integer, UnaryOp, Variable


@dataclass(frozen=True)
class ConeSlice:
    """Variable partition for a requested conservative slice.

    :param retained_variables: Persistent variables kept in domain order.
    :type retained_variables: Tuple[str, ...]
    :param dropped_variables: Unobserved persistent variables in domain order.
    :type dropped_variables: Tuple[str, ...]
    :param skipped_reason: Reason no slice is applied, or ``None``.
    :type skipped_reason: Optional[str]
    """

    retained_variables: Tuple[str, ...]
    dropped_variables: Tuple[str, ...]
    skipped_reason: Optional[str] = None
    _keep_names: frozenset = field(default_factory=frozenset, repr=False)

    def __post_init__(self):
        for field_name in ("retained_variables", "dropped_variables"):
            names = getattr(self, field_name)
            if not isinstance(names, tuple) or any(
                not isinstance(name, str) or not name for name in names
            ):
                raise BmcBuildError(
                    "%s must be a tuple of variable names." % field_name
                )
            if len(set(names)) != len(names):
                raise BmcBuildError("%s must contain unique names." % field_name)
        if set(self.retained_variables) & set(self.dropped_variables):
            raise BmcBuildError("Retained and dropped variables must be disjoint.")
        if self.skipped_reason not in (
            None,
            "abstract_actions",
            "no_removable_variables",
        ):
            raise BmcBuildError("Invalid cone slicing skip reason.")
        if self.skipped_reason is not None and self.dropped_variables:
            raise BmcBuildError("Skipped slicing must not drop variables.")
        object.__setattr__(
            self,
            "_keep_names",
            frozenset(self._keep_names) | frozenset(self.retained_variables),
        )

    def to_canonical(self):
        """Return public slicing metadata without altering the witness schema.

        :return: Effective partition and skip reason.
        :rtype: dict
        """
        return {
            "enabled": True,
            "retained_count": len(self.retained_variables),
            "dropped_variables": list(self.dropped_variables),
            "skipped_reason": self.skipped_reason,
            "fallback": False,
        }


def _total_integer(expr, integer_names):
    # Only unbounded integer arithmetic is known total here. Extend this set
    # only with an equivalent runtime/encoder definedness argument and tests.
    if isinstance(expr, Integer):
        return True
    if isinstance(expr, Variable):
        return expr.name in integer_names
    if isinstance(expr, UnaryOp):
        return expr.op in ("+", "-") and _total_integer(expr.x, integer_names)
    if isinstance(expr, BinaryOp):
        return (
            expr.op in ("+", "-", "*")
            and _total_integer(expr.x, integer_names)
            and _total_integer(expr.y, integer_names)
        )
    return False


def _operation_seeds(statements, integer_names, seeds):
    for statement in statements:
        if isinstance(statement, Operation):
            if not _total_integer(statement.expr, integer_names):
                seeds.add(statement.var_name)
                integer_names.discard(statement.var_name)
                seeds.update(collect_expr_variables(statement.expr))
        elif isinstance(statement, IfBlock):
            for branch in statement.branches:
                if branch.condition is not None:
                    seeds.update(collect_expr_variables(branch.condition))
                _operation_seeds(branch.statements, integer_names, seeds)
        else:
            raise TypeError(
                "Unsupported operation statement: %s" % type(statement).__name__
            )


def build_cone_slice(context):
    """Collect observations and use the model's existing dependency closure.

    :param context: Fully bound query and original model.
    :type context: pyfcstm.bmc.engine.BmcPreparedContext
    :return: Requested slice with persistent and local dependency names.
    :rtype: ConeSlice
    """
    names = context.domain.persistent_variable_names
    integer_names = {
        variable.name
        for variable in context.domain.variables
        if variable.declared_type == "int"
    }
    seeds = set(names) - integer_names
    seeds.update(
        reference.name
        for reference in context.bound_query.references
        if reference.kind == "variable"
    )
    blocks = []
    for state in context.model.walk_states():
        for actions in (
            state.on_enters,
            state.on_durings,
            state.on_exits,
            state.on_during_aspects,
        ):
            for action in actions:
                if action.is_abstract:
                    return ConeSlice(names, (), "abstract_actions", frozenset(names))
                blocks.append(action.operations or ())
        for transition in state.transitions:
            if transition.guard is not None:
                seeds.update(collect_expr_variables(transition.guard))
            blocks.append(transition.effects or ())
    # Persistent declarations constrain action boundaries, not intermediate
    # scope values. Propagate unsafe writes before treating integer reads as
    # total, including dependencies encountered earlier in the model walk.
    while True:
        previous_integers = set(integer_names)
        for statements in blocks:
            _operation_seeds(statements, integer_names, seeds)
        if integer_names == previous_integers:
            break
    if set(names) <= seeds:
        return ConeSlice(names, (), "no_removable_variables", frozenset(seeds))
    graph = build_use_def_graph(context.model)
    keep = frozenset(seeds | set(graph.affecting_variables(seeds)))
    dropped = tuple(name for name in names if name not in keep)
    retained = tuple(name for name in names if name in keep)
    return ConeSlice(
        retained, dropped, None if dropped else "no_removable_variables", keep
    )


def slice_operations(statements, cone, *, source_paths=None, _source_prefix=(), _result_prefix=()):
    """Filter assignments while preserving ordered branch selection.

    :param statements: Original model operations; never mutated.
    :param cone: Retained persistent and local dependency names.
    :type cone: ConeSlice
    :param source_paths: Optional dictionary populated with retained occurrence
        paths mapped to their original statement/branch paths. Recording is
        performed during slicing; identical statements remain distinct.
    :type source_paths: dict, optional
    :return: Filtered operations preserving source spans and all conditions.
    :rtype: tuple
    """
    result = []
    for index, statement in enumerate(statements):
        source_path = (*_source_prefix, index)
        result_path = (*_result_prefix, len(result))
        if isinstance(statement, Operation):
            if statement.var_name in cone._keep_names:
                if source_paths is not None:
                    source_paths[result_path] = source_path
                result.append(statement)
        elif isinstance(statement, IfBlock):
            # Even an empty branch can block a later else or evaluate a
            # partial condition. Retain every condition and its priority.
            if source_paths is not None:
                source_paths[result_path] = source_path
            result.append(
                replace(
                    statement,
                    branches=[
                        replace(
                            branch,
                            statements=list(slice_operations(
                                branch.statements, cone, source_paths=source_paths,
                                _source_prefix=(*source_path, branch_index),
                                _result_prefix=(*result_path, branch_index),
                            )),
                        )
                        for branch_index, branch in enumerate(statement.branches)
                    ],
                )
            )
        else:
            raise TypeError(
                "Unsupported operation statement: %s" % type(statement).__name__
            )
    return tuple(result)
