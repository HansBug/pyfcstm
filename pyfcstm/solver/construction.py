"""Assignment versions captured by the existing symbolic operation executor.

These records describe how expressions were constructed, not why a query is
unsatisfiable. Source objects and occurrence paths remain distinct from Z3 AST
identity: even ``x = x`` creates a new write occurrence. Branch joins retain
their selectors and the incoming value used when no branch executes.

Example::

    >>> import z3
    >>> from pyfcstm.solver.operation import execute_operations_domain, parse_operations
    >>> statements = parse_operations(
    ...     "refund = quantum - margin; proposal = proposal - refund; margin = margin + refund;",
    ...     ["quantum", "margin", "proposal"],
    ... )
    >>> env = dict(zip(("quantum", "margin", "proposal"), z3.Ints("quantum margin proposal")))
    >>> graph = execute_operations_domain(statements, env, record_construction=True).construction
    >>> graph.check().status
    'verified'
    >>> writes = [value for value in graph.values if value.kind == "assignment"]
    >>> writes[1].reads[-1] == ("refund", writes[0].identifier)
    True
    >>> z3.simplify(writes[2].expression)
    quantum

The last line is Z3 simplification of the constructed value, not an arithmetic
proof certificate. ``refund`` is a local in this example: its version remains
available to later assignments within the block but is not exported.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple

import z3

from .domain import ExpressionConstruction, translate_expr_domain
from .budget import SolveBudget


def _source_at(statements, path):
    """Resolve statement/branch indices without executing source statements."""
    current = statements
    for offset, index in enumerate(path):
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(current):
            return None
        node = current[index]
        if offset == len(path) - 1:
            return node
        current = getattr(node, 'branches' if offset % 2 == 0 else 'statements', ())
    return None


def _same_expressions(left, right):
    return len(left) == len(right) and all(z3.eq(a, b) for a, b in zip(left, right))


def _same_expression_records(left, right):
    return len(left) == len(right) and all(
        a.source is b.source and a.path == b.path and
        z3.eq(a.expression, b.expression) and
        _same_expressions(a.path_conditions, b.path_conditions) and
        _same_expressions(tuple(item.constraint for item in a.definedness_constraints),
                          tuple(item.constraint for item in b.definedness_constraints))
        for a, b in zip(left, right)
    )


@dataclass(frozen=True)
class ConstructionCheck:
    """Result of checking construction bindings, not a logical proof.

    :param status: ``verified``, ``invalid`` or ``unknown`` (budget exhausted).
    :param reason: Explanation of the result.
    :param path: Source occurrence of a failed check, if available.
    """

    status: str
    reason: str
    path: Tuple[int, ...] = ()


@dataclass(frozen=True)
class ConstructionValue:
    """One input, assignment, or branch-merge value occurrence.

    :param identifier: Index in the containing construction's value tuple.
    :param name: Authored variable name, including block-local names.
    :param kind: ``input``, ``assignment`` or ``merge``.
    :param expression: Actual expanded Z3 value produced by the executor.
    :param source: Original assignment or if-block; ``None`` for inputs.
    :param path: Statement/branch indices within the source block.
    :param reads: Authored read names paired with predecessor value indices.
    :param alternatives: Ordered selector/value pairs for a branch merge.
        The sole read of a merge is its incoming preservation value.
    :param path_conditions: Conditions at the construction point.
    :param definedness: Prior runtime-domain constraints used for translation.
    :param subexpressions: Source child occurrences and the actual expressions
        produced while translating this assignment, in dependency order.
    """

    identifier: int
    name: str
    kind: str
    expression: z3.ExprRef
    source: object = None
    path: Tuple[int, ...] = ()
    reads: Tuple[Tuple[str, int], ...] = ()
    alternatives: Tuple[Tuple[z3.BoolRef, int], ...] = ()
    path_conditions: Tuple[z3.BoolRef, ...] = ()
    definedness: Tuple[z3.BoolRef, ...] = ()
    subexpressions: Tuple[ExpressionConstruction, ...] = ()


@dataclass(frozen=True)
class ConstructionBranch:
    """One actual source-branch evaluation, including pruned branches.

    :param path: Statement/branch occurrence path within the action block.
    :param source: Original model branch object.
    :param kind: ``if``, ``elif`` or ``else``.
    :param selector: Effective selector, including earlier-branch exclusions.
    :param status: Reachability observation from the executor.
    :param reads: Versions available when evaluating the source condition.
    :param path_conditions: Full branch scope, including outer conditions.
    :param result_versions: Visible output versions; empty when pruned.
    :param subexpressions: Actual condition translation, empty for ``else``
        and branches pruned before their condition is evaluated.
    """

    path: Tuple[int, ...]
    source: object
    kind: str
    selector: z3.BoolRef
    status: str
    reads: Tuple[Tuple[str, int], ...]
    path_conditions: Tuple[z3.BoolRef, ...]
    result_versions: Tuple[Tuple[str, int], ...]
    subexpressions: Tuple[ExpressionConstruction, ...] = ()


@dataclass(frozen=True)
class OperationConstruction:
    """Immutable version graph for one invocation of an operation block.

    :param statements: Original source statements, in execution order.
    :param values: Input, write and merge occurrences in dependency order.
    :param branches: Evaluated source branches, including nested occurrences.
    :param initial_versions: Input name to version index.
    :param final_versions: Exported name to version index; locals are excluded.
    :param assumptions: Caller-supplied translation assumptions.
    :param prune_unreachable: Whether the producing executor pruned branches.
    :param path_conditions: Caller-supplied entry conditions.
    """

    statements: tuple
    values: Tuple[ConstructionValue, ...]
    branches: Tuple[ConstructionBranch, ...]
    initial_versions: Mapping[str, int]
    final_versions: Mapping[str, int]
    assumptions: tuple = ()
    prune_unreachable: bool = True
    path_conditions: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, 'initial_versions', MappingProxyType(dict(self.initial_versions)))
        object.__setattr__(self, 'final_versions', MappingProxyType(dict(self.final_versions)))

    def check(self, *, timeout_ms=None) -> ConstructionCheck:
        """Check local assignment expansion and version dependencies.

        Uses the existing expression translator, never a second statement
        executor. This checks binding consistency, not compiler correctness,
        branch coverage, reachability, or an UNSAT derivation.

        :param timeout_ms: Positive total millisecond budget, or ``None``.
            Includes recursive expression reachability checks. Exhaustion
            returns ``unknown``, never a completed binding check.
        :return: Binding status and the first failed occurrence.
        :rtype: ConstructionCheck
        :raises ValueError: For an invalid budget.
        """
        return self._check(SolveBudget(timeout_ms))

    def _check(self, budget):
        """Check bindings using a deadline shared with the enclosing report."""
        scopes = {(): dict(self.initial_versions)}
        entries = {}
        writes = set()
        branch_lookup = {item.path: item for item in self.branches}
        if len(branch_lookup) != len(self.branches):
            return ConstructionCheck('invalid', 'duplicate branch occurrence')

        def scope_versions(path):
            if path not in scopes:
                parent = scope_versions(path[:-2])
                entry = entries.setdefault(path[:-1], dict(parent))
                scopes[path] = dict(entry)
            return scopes[path]

        for index, value in enumerate(self.values):
            if budget.deadline is not None and budget.remaining_ms() is None:
                return ConstructionCheck('unknown', 'budget exhausted')
            if value.identifier != index or any(
                not 0 <= predecessor < index for _, predecessor in
                (*value.reads, *value.alternatives)
            ):
                return ConstructionCheck('invalid', 'invalid version dependency', value.path)
            if value.kind == 'input':
                if self.initial_versions.get(value.name) != index:
                    return ConstructionCheck('invalid', 'input version mismatch')
                continue
            if _source_at(self.statements, value.path) is not value.source:
                return ConstructionCheck('invalid', 'source occurrence mismatch', value.path)
            parent_scope = value.path[:-1]
            scope = (branch_lookup[parent_scope].path_conditions
                     if parent_scope in branch_lookup else self.path_conditions)
            if not _same_expressions(value.path_conditions, scope):
                return ConstructionCheck('invalid', 'construction scope mismatch', value.path)
            versions = scope_versions(value.path[:-1])
            if value.kind == 'assignment':
                source = value.source
                names = tuple(variable.name for variable in source.expr.list_variables())
                expected_reads = tuple((name, versions.get(name)) for name in names)
                if value.reads != expected_reads or source.var_name != value.name:
                    return ConstructionCheck('invalid', 'assignment read/write mismatch', value.path)
                if value.path in writes:
                    return ConstructionCheck('invalid', 'duplicate assignment occurrence', value.path)
                writes.add(value.path)
                translated = translate_expr_domain(
                    source.expr,
                    {name: self.values[version].expression for name, version in value.reads},
                    assumptions=self.assumptions,
                    path_conditions=(*value.path_conditions, *value.definedness),
                    prune_unreachable=self.prune_unreachable,
                    budget=budget,
                    record_construction=True,
                )
                if budget.deadline is not None and budget.remaining_ms() is None:
                    return ConstructionCheck('unknown', 'budget exhausted', value.path)
                if translated.failure is not None:
                    return ConstructionCheck('invalid', 'source expression translation failed', value.path)
                if not _same_expression_records(value.subexpressions, translated.construction):
                    return ConstructionCheck('invalid', 'source subexpression binding mismatch', value.path)
                expected = translated.z3_expr
            elif value.kind == 'merge':
                incoming = entries.setdefault(value.path, dict(versions))
                if value.reads != ((value.name, incoming.get(value.name)),):
                    return ConstructionCheck('invalid', 'merge incoming version mismatch', value.path)
                branches = [branch_lookup.get((*value.path, i))
                            for i in range(len(value.source.branches))]
                if any(branch is None for branch in branches):
                    return ConstructionCheck('invalid', 'merge branch coverage mismatch', value.path)
                alternatives = tuple((branch.selector, dict(branch.result_versions).get(value.name))
                                     for branch in branches if branch.status != 'unsat')
                if len(alternatives) != len(value.alternatives) or any(
                    expected_version != actual_version or not z3.eq(expected_selector, actual_selector)
                    for (expected_selector, expected_version), (actual_selector, actual_version)
                    in zip(alternatives, value.alternatives)
                ):
                    return ConstructionCheck('invalid', 'merge branch version mismatch', value.path)
                expected = self.values[value.reads[0][1]].expression
                for selector, version in reversed(value.alternatives):
                    expected = z3.If(selector, self.values[version].expression, expected)
            else:
                return ConstructionCheck('invalid', 'unknown construction kind', value.path)
            if not z3.eq(expected, value.expression):
                return ConstructionCheck('invalid', 'constructed expression mismatch', value.path)
            versions[value.name] = index
        for branch in self.branches:
            if budget.deadline is not None and budget.remaining_ms() is None:
                return ConstructionCheck('unknown', 'budget exhausted', branch.path)
            if _source_at(self.statements, branch.path) is not branch.source:
                return ConstructionCheck('invalid', 'branch source mismatch', branch.path)
            incoming = entries.setdefault(branch.path[:-1], dict(scope_versions(branch.path[:-2])))
            condition = branch.source.condition
            names = tuple(variable.name for variable in condition.list_variables()) if condition is not None else ()
            if branch.reads != tuple((name, incoming.get(name)) for name in names):
                return ConstructionCheck('invalid', 'branch input version mismatch', branch.path)
            if branch.subexpressions:
                root = branch.subexpressions[-1]
                translated = translate_expr_domain(
                    condition,
                    {name: self.values[version].expression for name, version in branch.reads},
                    assumptions=self.assumptions, path_conditions=root.path_conditions,
                    prune_unreachable=self.prune_unreachable, budget=budget,
                    record_construction=True,
                )
                if budget.deadline is not None and budget.remaining_ms() is None:
                    return ConstructionCheck('unknown', 'budget exhausted', branch.path)
                if translated.failure is not None or not _same_expression_records(
                    branch.subexpressions, translated.construction,
                ):
                    return ConstructionCheck('invalid', 'branch condition binding mismatch', branch.path)
            parent_path = branch.path[:-2]
            scope = (branch_lookup[parent_path].path_conditions
                     if parent_path in branch_lookup else self.path_conditions)
            if not _same_expressions(branch.path_conditions, (*scope, branch.selector)):
                return ConstructionCheck('invalid', 'branch scope mismatch', branch.path)
            outgoing = scope_versions(branch.path)
            if branch.status != 'unsat' and branch.result_versions != tuple(
                (name, outgoing.get(name)) for name in incoming
            ):
                return ConstructionCheck('invalid', 'branch output version mismatch', branch.path)
        if dict(self.final_versions) != {name: scopes[()][name] for name in self.initial_versions}:
            return ConstructionCheck('invalid', 'final version mismatch')
        return ConstructionCheck('verified', 'local expression bindings checked')


class _ConstructionRecorder:
    """Mutable invocation-local collector owned by the operation executor."""

    def __init__(self, env):
        self.values = []
        self.branches = []
        self.versions = {}
        for name, expression in env.items():
            self.versions[name] = self._append(name, 'input', expression)
        self.initial_versions = dict(self.versions)

    def _append(self, name, kind, expression, **kwargs):
        identifier = len(self.values)
        self.values.append(ConstructionValue(identifier, name, kind, expression, **kwargs))
        return identifier

    def reads(self, expression):
        return tuple((variable.name, self.versions[variable.name])
                     for variable in expression.list_variables())

    def assignment(self, statement, result, path, conditions, domains):
        self.versions[statement.var_name] = self._append(
            statement.var_name, 'assignment', result.z3_expr,
            source=statement, path=path, reads=self.reads(statement.expr),
            path_conditions=tuple(conditions),
            definedness=tuple(item.constraint for item in domains),
            subexpressions=result.construction,
        )

    def fork(self):
        branch = object.__new__(_ConstructionRecorder)
        branch.values = self.values
        branch.branches = self.branches
        branch.versions = dict(self.versions)
        branch.initial_versions = self.initial_versions
        return branch

    def branch(self, statement, path, evidence, child, names, result=None):
        self.branches.append(ConstructionBranch(
            path, statement, evidence.branch_kind, evidence.selector,
            evidence.status,
            self.reads(statement.condition) if statement.condition is not None else (),
            evidence.path_conditions,
            tuple((name, child.versions[name]) for name in names) if child is not None else (),
            result.construction if result is not None else (),
        ))

    def merge(self, statement, path, env, alternatives, conditions):
        for name, expression in env.items():
            self.versions[name] = self._append(
                name, 'merge', expression, source=statement, path=path,
                reads=((name, self.versions[name]),),
                alternatives=tuple((selector, child.versions[name])
                                   for selector, child in alternatives),
                path_conditions=tuple(conditions),
            )

    def finish(self, statements, names, assumptions, prune_unreachable, path_conditions):
        return OperationConstruction(
            tuple(statements), tuple(self.values), tuple(self.branches),
            self.initial_versions, {name: self.versions[name] for name in names},
            tuple(assumptions), prune_unreachable, tuple(path_conditions),
        )
