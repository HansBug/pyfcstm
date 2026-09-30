"""
History pseudo-states (``[H]`` / ``[H*]``) lowered into plain FCSTM.

A composite state (the *owner*) declares ``[H] -> Child;`` or
``[H*] -> Child.Grandchild;``, and transitions in its parent scope enter it
with ``Owner.[H]`` or ``Owner.[H*]``.  Like forced and combo transitions,
history is syntactic sugar: :func:`lower_history` rewrites it during model
conversion into ordinary variables, exit actions and initial transitions, so
the simulator, templates and BMC consume a machine that contains no history
construct at all.

The lowering is the minimal one.  States are numbered in preorder, so every
subtree is one contiguous range of ids.  Two kinds of hidden ``int``
variables are added:

* ``__hist_<owner>`` -- one per owner: the id of the last stoppable leaf
  exited below the owner.  While the owner is inactive this is exactly its
  history record (``0`` means no record).
* ``__hist_goto`` -- shared: the id of the state a restore in flight is
  heading for (``0`` means none).  It is ``0`` at every stable point.

Four rewrite rules implement the semantics:

1. Every stoppable leaf's exit writes its id into the record of each owner
   above it.
2. A transition entering ``O.[H]`` / ``O.[H*]`` computes the restore target
   once, at the end of its effect.
3. One route edge ``[*] -> K : if [goto in range(K)]`` per composite and child
   on the way to any possible target; entering a leaf clears ``goto``.  A
   user's plain initial to the same child is merged into that edge.
4. The remaining user initials of those composites fire only while no
   restore passes through them, and clear ``goto`` first.  An evented initial
   is split through a pseudo gate, because a model transition cannot carry an
   event and a guard at the same time.

The module contains:

* :class:`HistoryOwner` - Source-level metadata of one lowered owner
* :func:`lower_history` - Lower every history construct of a built machine
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterator, List, Mapping, Optional, Set, Tuple

from .expr import BinaryOp, ConditionalOp, Expr, Integer, Variable
from ..dsl import node as dsl_nodes
from ..utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..diagnostics.sink import DiagnosticSink
    from .model import State, Transition, VarDefine

__all__ = ["HistoryOwner", "lower_history", "HISTORY_PREFIX"]

HISTORY_PREFIX = "__hist_"
"""Reserved prefix of every name history lowering generates."""

_GOTO_TAG = "goto"
# Every target-language identifier conversion collapses runs of underscores,
# so ``__hist_x`` and ``_hist_x`` meet in generated code.
_RESERVED_IN_HISTORY_MODELS = re.compile(r"_+hist_")

_Path = Tuple[str, ...]


@dataclass(frozen=True)
class HistoryOwner:
    """
    Source-level metadata of one lowered history owner.

    :param owner_path: Dotted path of the owner as a tuple of state names
    :type owner_path: Tuple[str, ...]
    :param record_variable: Name of the variable holding the owner's record
    :type record_variable: str
    :param goto_variable: Name of the shared restore-target variable
    :type goto_variable: str
    :param defaults: Default path, relative to the owner, of each declared
        history kind (``'shallow'`` / ``'deep'``)
    :type defaults: Mapping[str, Tuple[str, ...]]
    :param leaf_ids: Record value of every stoppable leaf below the owner,
        keyed by its path relative to the owner
    :type leaf_ids: Mapping[Tuple[str, ...], int]

    Example::

        >>> owner = HistoryOwner(("R", "O"), "__hist_O", "__hist_goto",
        ...                      {"shallow": ("A",)}, {("A",): 3, ("B",): 4})
        >>> owner.record_value(("B",))
        4
        >>> owner.decode(4)
        ('B',)
    """

    owner_path: _Path
    record_variable: str
    goto_variable: str
    defaults: Mapping[str, _Path]
    leaf_ids: Mapping[_Path, int]

    def leaf_paths(self) -> Tuple[_Path, ...]:
        """
        Return the paths, relative to the owner, of the leaves it can record.

        :return: Stoppable leaf paths below the owner, in preorder
        :rtype: Tuple[Tuple[str, ...], ...]
        """
        return tuple(self.leaf_ids)

    def record_value(self, leaf: _Path) -> Optional[int]:
        """
        Return the record value that means "``leaf`` was left last".

        :param leaf: Leaf path relative to the owner
        :type leaf: Tuple[str, ...]
        :return: Record value, or ``None`` if ``leaf`` is not a stoppable leaf
            below the owner
        :rtype: Optional[int]
        """
        return self.leaf_ids.get(tuple(leaf))

    def decode(self, value: object) -> Optional[_Path]:
        """
        Translate a record value back into a leaf path.

        :param value: Value of :attr:`record_variable`
        :type value: object
        :return: Leaf path relative to the owner, or ``None`` for no record
        :rtype: Optional[Tuple[str, ...]]
        """
        for path, leaf_id in self.leaf_ids.items():
            if leaf_id == value:
                return path
        return None


def _walk(state: "State") -> Iterator["State"]:
    yield state
    for child in state.substates.values():
        for item in _walk(child):
            yield item


def _walk_ast(
    node: dsl_nodes.StateDefinition, path: _Path = ()
) -> Iterator[Tuple[_Path, dsl_nodes.StateDefinition]]:
    path = (*path, node.name)
    yield path, node
    for child in node.substates:
        for item in _walk_ast(child, path):
            yield item


def _operations(statements) -> Iterator:
    for statement in statements:
        if hasattr(statement, "branches"):
            for branch in statement.branches:
                for item in _operations(branch.statements):
                    yield item
        else:
            yield statement


def _state_operations(state: "State") -> Iterator:
    for action in [
        *state.on_enters,
        *state.on_durings,
        *state.on_exits,
        *state.on_during_aspects,
    ]:
        for item in _operations(action.operations):
            yield item
    for transition in state.transitions:
        for item in _operations(transition.effects):
            yield item


class _Lowering:
    """One history lowering run over a built machine."""

    def __init__(self, ast_root, root_state, defines, sink) -> None:
        self.ast_root = ast_root
        self.root = root_state
        self.defines: Dict[str, "VarDefine"] = defines
        self.sink: "DiagnosticSink" = sink
        self.states: Dict[_Path, "State"] = {s.path: s for s in _walk(root_state)}
        self.ids: Dict[_Path, int] = {path: i for i, path in enumerate(self.states, 1)}
        self.goto = HISTORY_PREFIX + _GOTO_TAG

    # -- diagnostics -------------------------------------------------------

    def _emit(self, code: str, severity: str, message: str, span, refs) -> None:
        self.sink.emit(
            ModelDiagnostic(
                code=code, severity=severity, message=message, span=span, refs=refs
            )
        )

    def _check_reserved_names(self, uses_history: bool) -> None:
        seen: Set[Tuple[str, str]] = set()

        def check(identifier: str, kind: str, span) -> None:
            if (identifier, kind) in seen:
                return
            seen.add((identifier, kind))
            if uses_history and _RESERVED_IN_HISTORY_MODELS.match(identifier):
                self._emit(
                    "E_HISTORY_RESERVED_PREFIX",
                    "error",
                    "Identifier %r collides with the names history lowering "
                    "generates (prefix %r)." % (identifier, HISTORY_PREFIX),
                    span,
                    {"identifier": identifier, "identifier_kind": kind},
                )
            elif not uses_history and identifier.startswith(HISTORY_PREFIX):
                self._emit(
                    "W_HISTORY_RESERVED_PREFIX",
                    "warning",
                    "Identifier %r uses the prefix %r reserved for history "
                    "lowering." % (identifier, HISTORY_PREFIX),
                    span,
                    {"identifier": identifier, "identifier_kind": kind},
                )

        for name, define in self.defines.items():
            check(name, "variable", define._span)
        for state in self.states.values():
            check(state.name, "state", state._span)
        for state in self.states.values():
            for operation in _state_operations(state):
                if operation.var_name not in self.defines:
                    check(operation.var_name, "temporary", operation._span)

    # -- declarations and targets -----------------------------------------

    def _resolve_default(self, owner: "State", path: List[str]) -> Optional["State"]:
        state = owner
        for name in path:
            state = state.substates.get(name)
            if state is None:
                return None
        return state

    def _declarations(self) -> Dict[_Path, Dict[str, Tuple[_Path, object]]]:
        """Validate every ``[H]`` / ``[H*]`` declaration of the source."""
        declared: Dict[_Path, Dict[str, Tuple[_Path, object]]] = {}
        for path, node in _walk_ast(self.ast_root):
            for decl in node.histories:
                owner = self.states.get(path)
                if owner is None:  # pragma: no cover - AST states always build.
                    continue
                reason = None
                target = self._resolve_default(owner, decl.default_path)
                if owner is self.root:
                    reason = "root_owner"
                elif decl.kind in declared.get(path, {}):
                    reason = "duplicate"
                elif decl.kind == "shallow" and len(decl.default_path) != 1:
                    reason = "default_not_direct_child"
                elif target is None:
                    reason = "default_not_found"
                elif target.is_pseudo:
                    reason = "default_pseudo"
                if reason is not None:
                    self._emit(
                        "E_HISTORY_DECLARATION_INVALID",
                        "error",
                        "Invalid history declaration in %s (%s):\n%s"
                        % (".".join(path), reason, str(decl.without_docs())),
                        getattr(decl, "_span", None),
                        {
                            "owner_path": ".".join(path),
                            "kind": decl.kind,
                            "default": ".".join(decl.default_path),
                            "reason": reason,
                        },
                    )
                    continue
                declared.setdefault(path, {})[decl.kind] = (
                    tuple(decl.default_path),
                    decl,
                )
        return declared

    def _targets(self, declared) -> List[Tuple["Transition", _Path, str]]:
        """Validate every transition that enters a history."""
        found = []
        reported = set()
        for scope in self.states.values():
            for transition in scope.transitions:
                kind = transition.target_history
                if kind is None:
                    continue
                owner = scope.substates.get(transition.to_state)
                if owner is None:  # pragma: no cover - dangling targets are dropped earlier.
                    continue
                if kind in declared.get(owner.path, {}):
                    found.append((transition, owner.path, kind))
                    continue
                key = (owner.path, kind, transition._span)
                if key not in reported:
                    reported.add(key)
                    self._emit(
                        "E_HISTORY_TARGET_UNDECLARED",
                        "error",
                        "%s does not declare %s history ([%s] -> ...;), so "
                        "it cannot be entered through %s.%s."
                        % (
                            ".".join(owner.path),
                            kind,
                            "H" if kind == "shallow" else "H*",
                            owner.name,
                            dsl_nodes.HISTORY_KINDS[kind],
                        ),
                        transition._span,
                        {"owner_path": ".".join(owner.path), "kind": kind},
                    )
        return found

    # -- expressions -------------------------------------------------------

    def _var(self, name: str) -> Expr:
        return Variable(name)

    def _eq(self, name: str, value: int) -> Expr:
        return BinaryOp(self._var(name), "==", Integer(value))

    def _range(self, name: str, lo: int, hi: int) -> Expr:
        if lo == hi:
            return self._eq(name, lo)
        return BinaryOp(
            BinaryOp(self._var(name), ">=", Integer(lo)),
            "&&",
            BinaryOp(self._var(name), "<=", Integer(hi)),
        )

    def _subtree(self, path: _Path) -> Tuple[int, int]:
        lo = self.ids[path]
        hi = max(v for p, v in self.ids.items() if p[: len(path)] == path)
        return lo, hi

    def _in_subtree(self, path: _Path) -> Expr:
        return self._range(self.goto, *self._subtree(path))

    @staticmethod
    def _assign(name: str, expr: Expr):
        from .model import Operation

        return Operation(var_name=name, expr=expr)

    # -- lowering ----------------------------------------------------------

    def _stoppable_leaves(self, path: _Path) -> List[_Path]:
        return [
            p
            for p, state in self.states.items()
            if p[: len(path)] == path and p != path and state.is_stoppable
        ]

    def _restore_target(self, owner: HistoryOwner, kind: str) -> Expr:
        """The restore target, computed once in the history entry's effect."""
        record = owner.record_variable
        default = self.ids[(*owner.owner_path, *owner.defaults[kind])]
        if kind == "deep":
            return ConditionalOp(
                BinaryOp(self._var(record), "!=", Integer(0)),
                self._var(record),
                Integer(default),
            )
        expr: Expr = Integer(default)
        owner_state = self.states[owner.owner_path]
        for child in reversed(list(owner_state.substates.values())):
            leaves = [self.ids[p] for p in self._stoppable_leaves(child.path)]
            if child.is_stoppable:
                leaves = [self.ids[child.path]]
            if leaves:
                expr = ConditionalOp(
                    self._range(record, min(leaves), max(leaves)),
                    Integer(self.ids[child.path]),
                    expr,
                )
        return expr

    def _possible_targets(self, owner: HistoryOwner, kinds: Set[str]) -> List[_Path]:
        base = owner.owner_path
        found = [(*base, *owner.defaults[kind]) for kind in sorted(kinds)]
        leaves = [(*base, *leaf) for leaf in owner.leaf_ids]
        if "deep" in kinds:
            found.extend(leaves)
        if "shallow" in kinds:
            found.extend(
                child.path
                for child in self.states[base].substates.values()
                if any(leaf[: len(child.path)] == child.path for leaf in leaves)
            )
        return found

    def _owner_tags(self, owner_paths: List[_Path]) -> Dict[_Path, str]:
        tags: Dict[_Path, str] = {}
        taken = {_GOTO_TAG}
        for path in owner_paths:
            base = "_".join(path[1:])
            tag, index = base, 1
            while re.sub("_+", "_", tag) in taken:
                index += 1
                tag = "%s_%d" % (base, index)
            taken.add(re.sub("_+", "_", tag))
            tags[path] = tag
        return tags

    def run(self) -> Tuple[HistoryOwner, ...]:
        from .model import OnStage, State, Transition, VarDefine

        uses_history = any(node.histories for _, node in _walk_ast(self.ast_root)) or any(
            t.target_history is not None
            for state in self.states.values()
            for t in state.transitions
        )
        self._check_reserved_names(uses_history)
        if not uses_history:
            return ()

        declared = self._declarations()
        targets = self._targets(declared)
        used: Dict[_Path, Set[str]] = {}
        for _, owner_path, kind in targets:
            used.setdefault(owner_path, set()).add(kind)
        for owner_path, kinds in declared.items():
            for kind, (_, decl) in kinds.items():
                if kind not in used.get(owner_path, set()):
                    self._emit(
                        "W_HISTORY_UNUSED",
                        "warning",
                        "%s declares %s history, but no transition enters %s.%s."
                        % (
                            ".".join(owner_path),
                            kind,
                            owner_path[-1],
                            dsl_nodes.HISTORY_KINDS[kind],
                        ),
                        getattr(decl, "_span", None),
                        {"owner_path": ".".join(owner_path), "kind": kind},
                    )
        if not used:
            return ()

        owner_paths = [path for path in self.states if path in used]
        tags = self._owner_tags(owner_paths)
        owners: Dict[_Path, HistoryOwner] = {}
        for path in owner_paths:
            owners[path] = HistoryOwner(
                owner_path=path,
                record_variable=HISTORY_PREFIX + tags[path],
                goto_variable=self.goto,
                defaults={kind: item[0] for kind, item in declared[path].items()},
                leaf_ids={
                    leaf[len(path):]: self.ids[leaf]
                    for leaf in self._stoppable_leaves(path)
                },
            )

        self.defines[self.goto] = VarDefine(name=self.goto, type="int", init=Integer(0))
        for owner in owners.values():
            self.defines[owner.record_variable] = VarDefine(
                name=owner.record_variable, type="int", init=Integer(0)
            )

        # 1. record: each stoppable leaf writes its id into every owner above it
        for path, leaf in self.states.items():
            if not leaf.is_stoppable:
                continue
            operations = [
                self._assign(owner.record_variable, Integer(self.ids[path]))
                for owner_path, owner in owners.items()
                if path[: len(owner_path)] == owner_path and path != owner_path
            ]
            if operations:
                action = OnStage(
                    stage="exit",
                    aspect=None,
                    name=None,
                    doc=None,
                    operations=operations,
                    is_abstract=False,
                    state_path=(*path, None),
                )
                action.parent = leaf
                leaf.on_exits.append(action)

        # 2. entry: the history transition computes the restore target once
        for transition, owner_path, kind in targets:
            transition.effects = [
                *transition.effects,
                self._assign(self.goto, self._restore_target(owners[owner_path], kind)),
            ]

        # 3 + 4. routes and gates on every composite a restore passes through
        hops: Dict[_Path, List[str]] = {}
        restore_targets: Set[_Path] = set()
        for owner_path, owner in owners.items():
            for target in self._possible_targets(owner, used[owner_path]):
                restore_targets.add(target)
                for depth in range(len(owner_path), len(target)):
                    bucket = hops.setdefault(target[:depth], [])
                    if target[depth] not in bucket:
                        bucket.append(target[depth])
        composite_targets = {
            path for path in restore_targets if not self.states[path].is_leaf_state
        }

        gate_count = 0
        for comp_path in sorted(set(hops) | composite_targets, key=lambda p: self.ids[p]):
            comp = self.states[comp_path]
            gate = self._eq(self.goto, 0)
            if comp_path in composite_targets:
                gate = BinaryOp(gate, "||", self._eq(self.goto, self.ids[comp_path]))
            pending = list(hops.get(comp_path, ()))
            for transition in list(comp.init_transitions):
                child = comp.substates[transition.to_state]
                user_guard = transition.guard
                transition.history_user_guard = user_guard
                if (
                    transition.event is None
                    and not transition.effects
                    and transition.to_state in pending
                ):
                    # Merge the user's plain initial with the route to the
                    # same child: one edge, both conditions.
                    pending.remove(transition.to_state)
                    allowed = gate if user_guard is None else BinaryOp(gate, "&&", user_guard)
                    transition.guard = BinaryOp(allowed, "||", self._in_subtree(child.path))
                    transition.effects = [
                        self._assign(
                            self.goto,
                            Integer(0)
                            if child.is_leaf_state
                            else ConditionalOp(
                                self._in_subtree(child.path), self._var(self.goto), Integer(0)
                            ),
                        )
                    ]
                    transition.history_role = "merged"
                    continue
                # Clear first: when this initial itself enters a nested
                # history, its effect already sets goto for the next owner.
                transition.effects = [self._assign(self.goto, Integer(0)), *transition.effects]
                transition.history_role = "gated"
                if transition.event is None:
                    transition.guard = (
                        gate if user_guard is None else BinaryOp(gate, "&&", user_guard)
                    )
                    continue
                gate_count += 1
                gate_name = "%sgate_%d" % (HISTORY_PREFIX, gate_count)
                gate_state = State(
                    name=gate_name,
                    path=(*comp_path, gate_name),
                    substates={},
                    is_pseudo=True,
                    is_history_gate=True,
                )
                gate_state.parent = comp
                comp.substates[gate_name] = gate_state
                comp.substate_name_to_id[gate_name] = len(comp.substate_name_to_id)
                entry = Transition(
                    from_state=dsl_nodes.INIT_STATE,
                    to_state=gate_name,
                    event=None,
                    guard=gate,
                    effects=[],
                    history_role="gate",
                    _span=transition._span,
                )
                entry.parent = comp
                comp.transitions[comp.transitions.index(transition)] = entry
                transition.from_state = gate_name
                transition.event_scope = (
                    "absolute" if transition.event_scope == "absolute" else "chain"
                )
                comp.transitions.append(transition)
            routes = []
            for name in pending:
                child = comp.substates[name]
                route = Transition(
                    from_state=dsl_nodes.INIT_STATE,
                    to_state=name,
                    event=None,
                    guard=self._in_subtree(child.path),
                    effects=[self._assign(self.goto, Integer(0))] if child.is_leaf_state else [],
                    history_role="route",
                )
                route.parent = comp
                routes.append(route)
            comp.transitions[:0] = routes

        return tuple(owners.values())


def lower_history(
    ast_root: dsl_nodes.StateDefinition,
    root_state: "State",
    defines: Dict[str, "VarDefine"],
    sink: "DiagnosticSink",
) -> Tuple[HistoryOwner, ...]:
    """
    Lower every history construct of a built machine in place.

    This runs at the end of model conversion, after forced and combo
    transitions have been expanded, so every history entry is already a
    concrete edge.  It validates declarations, targets and reserved names
    through ``sink``, adds the hidden variables to ``defines`` and rewrites
    exits and initial transitions (see the module documentation).

    :param ast_root: Root state of the assembled AST, which carries the
        ``[H]`` / ``[H*]`` declarations
    :type ast_root: pyfcstm.dsl.node.StateDefinition
    :param root_state: Root of the built model
    :type root_state: pyfcstm.model.model.State
    :param defines: Variable definitions of the model, extended in place
    :type defines: Dict[str, pyfcstm.model.model.VarDefine]
    :param sink: Diagnostic sink of the conversion
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink
    :return: Metadata of every lowered owner, in preorder
    :rtype: Tuple[HistoryOwner, ...]
    """
    return _Lowering(ast_root, root_state, defines, sink).run()
