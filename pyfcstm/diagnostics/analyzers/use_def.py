"""
Use-def graph construction for guard-affect data-flow analysis.

This module builds a conservative directed graph that records which variables
may influence the value of which other variables, based on the assignments in
concrete lifecycle actions and transition effects. The data-flow analyzers use
it to decide whether a variable can reach a transition guard, directly or
through a chain of assignments. The graph is conservative: it records every
dependency that may exist and does not try to prove that an assignment is
reachable or that a branch is taken.

The module contains:

* :class:`UseDefGraph` - Immutable dependency graph with transitive queries
* :func:`build_use_def_graph` - Build the graph for a state machine
* :func:`collect_expr_variables` - List the variables read by one expression

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> from pyfcstm.diagnostics.analyzers.use_def import build_use_def_graph
    >>> machine = load_state_machine_from_text('''
    ... def int a = 0;
    ... def int b = 0;
    ... def int c = 0;
    ... state Root {
    ...     state S { during { b = a + 1; c = b * 2; } }
    ...     [*] -> S;
    ... }
    ... ''')
    >>> graph = build_use_def_graph(machine)
    >>> graph.edges
    (('a', 'b'), ('b', 'c'))
    >>> graph.affecting_variables(['c'])
    ('a', 'b')
"""

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
        index = 0
        while index < len(queue):
            target = queue[index]
            index += 1
            for source in self.dependencies_of(target):
                if source in seen:
                    continue
                seen.add(source)
                out.add(source)
                queue.append(source)
        return tuple(sorted(out))


def build_use_def_graph(machine: 'StateMachine') -> UseDefGraph:
    """
    Build a conservative use-def graph from concrete actions and effects.

    Every state is scanned for its ``enter``, ``during``, ``exit`` and aspect
    actions (abstract actions have no body and are skipped), and every
    transition for its effect block. Each assignment ``target = expr`` adds an
    edge ``(source, target)`` for every variable ``source`` read by ``expr``.
    Inside an ``if`` block, the variables read by the enclosing conditions, and
    by the conditions of earlier branches of the same chain, also become
    sources of every assignment in the branch, because whether the assignment
    runs depends on them. An assignment of a literal outside any ``if`` block
    produces no edge, while inside an ``if`` block it still depends on the
    branch conditions. The graph does not distinguish declared variables from
    block-local temporaries.

    Edges are sorted, so the result is deterministic for a given model.

    :param machine: State machine whose actions and transition effects are
        scanned.
    :type machine: pyfcstm.model.model.StateMachine
    :return: The dependency graph; it has no edges when no assignment reads a
        variable, in its expression or in an enclosing ``if`` condition.
    :rtype: UseDefGraph

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.diagnostics.analyzers.use_def import build_use_def_graph
        >>> machine = load_state_machine_from_text('''
        ... def int a = 0;
        ... def int b = 0;
        ... def int c = 0;
        ... state Root {
        ...     state S {
        ...         during {
        ...             b = a + 1;
        ...             if [b > 0] { c = 2; }
        ...         }
        ...     }
        ...     [*] -> S;
        ... }
        ... ''')
        >>> graph = build_use_def_graph(machine)
        >>> graph.edges
        (('a', 'b'), ('b', 'c'))
        >>> graph.dependencies_of('c')
        ('b',)
        >>> graph.dependencies_of('a')
        ()
    """
    from ...model.support import require_supported_model

    require_supported_model(machine, 'Use-def analysis')
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
            continue
        raise TypeError(
            f'unhandled OperationStatement subclass: {type(stmt).__name__}'
        )


def _walk_expr_collect(expr: 'Expr', out: List[str]) -> None:
    from ...model.expr import (
        BinaryOp,
        Boolean,
        ConditionalOp,
        Float,
        Integer,
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
        return
    if isinstance(expr, (Integer, Float, Boolean)):
        return
    raise TypeError(f'unhandled Expr subclass: {type(expr).__name__}')
