"""Use-def graph construction for guard-affect data-flow analysis."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Set, Tuple

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only
    from ...model.expr import Expr
    from ...model.model import OperationStatement, StateMachine


@dataclass(frozen=True)
class UseDefGraph:
    """Directed variable dependency graph.

    Each edge is ``(source, target)`` and means that ``target``'s value may
    depend on ``source`` through an assignment expression or an enclosing
    operation-block condition.
    """

    edges: Tuple[Tuple[str, str], ...]
    dependencies_by_target: Dict[str, Tuple[str, ...]]

    def dependencies_of(self, target: str) -> Tuple[str, ...]:
        """Return variables that may affect ``target``."""
        return self.dependencies_by_target.get(target, tuple())

    def affecting_variables(self, direct_variables: Iterable[str]) -> Tuple[str, ...]:
        """Return all variables that can flow into ``direct_variables``."""
        direct = set(direct_variables)
        seen: Set[str] = set(direct)
        out: Set[str] = set()
        queue = list(direct)
        while queue:
            target = queue.pop(0)
            for source in self.dependencies_of(target):
                if source in seen:
                    continue
                seen.add(source)
                out.add(source)
                queue.append(source)
        return tuple(sorted(out))


def build_use_def_graph(machine: 'StateMachine') -> UseDefGraph:
    """Build a conservative use-def graph from concrete actions/effects."""
    edges: Set[Tuple[str, str]] = set()

    for state in machine.walk_states():
        for collection in (
                state.on_enters,
                state.on_durings,
                state.on_exits,
                state.on_during_aspects,
        ):
            for action in collection:
                if getattr(action, 'is_abstract', False):
                    continue
                _walk_block(action.operations or [], set(), edges)

        for transition in state.transitions:
            _walk_block(transition.effects or [], set(), edges)

    ordered_edges = tuple(sorted(edges))
    deps: Dict[str, List[str]] = {}
    for source, target in ordered_edges:
        deps.setdefault(target, []).append(source)
    return UseDefGraph(
        edges=ordered_edges,
        dependencies_by_target={
            target: tuple(sources)
            for target, sources in sorted(deps.items())
        },
    )


def collect_expr_variables(expr: 'Expr') -> Tuple[str, ...]:
    """Return variable names read by ``expr`` in stable first-seen order."""
    out: List[str] = []
    _walk_expr_collect(expr, out)
    seen = set()
    deduped: List[str] = []
    for name in out:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return tuple(deduped)


def _walk_block(
        statements: Iterable['OperationStatement'],
        enclosing_cond_vars: Set[str],
        edges: Set[Tuple[str, str]],
) -> None:
    from ...model.model import IfBlock, Operation

    for stmt in statements:
        if isinstance(stmt, Operation):
            deps = set(collect_expr_variables(stmt.expr)) | set(enclosing_cond_vars)
            for source in deps:
                edges.add((source, stmt.var_name))
            continue
        if isinstance(stmt, IfBlock):
            accumulated: Set[str] = set()
            for branch in stmt.branches:
                this_cond = (
                    set(collect_expr_variables(branch.condition))
                    if branch.condition is not None
                    else set()
                )
                branch_enclosing = (
                    set(enclosing_cond_vars) | accumulated | this_cond
                )
                _walk_block(branch.statements, branch_enclosing, edges)
                accumulated.update(this_cond)


def _walk_expr_collect(expr: 'Expr', out: List[str]) -> None:
    from ...model.expr import (
        BinaryOp,
        ConditionalOp,
        UFunc,
        UnaryOp,
        Variable,
    )

    if isinstance(expr, Variable):
        out.append(expr.name)
        return
    if isinstance(expr, UnaryOp):
        _walk_expr_collect(expr.x, out)
        return
    if isinstance(expr, BinaryOp):
        _walk_expr_collect(expr.x, out)
        _walk_expr_collect(expr.y, out)
        return
    if isinstance(expr, ConditionalOp):
        _walk_expr_collect(expr.cond, out)
        _walk_expr_collect(expr.if_true, out)
        _walk_expr_collect(expr.if_false, out)
        return
    if isinstance(expr, UFunc):
        _walk_expr_collect(expr.x, out)
