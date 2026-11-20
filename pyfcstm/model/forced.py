"""
Forced transitions that reach regions, lowered into plain transitions.

A forced transition ``!S -> T : /Stop;`` is syntactic sugar: model conversion
expands it into ordinary transitions, so the simulator, templates and BMC never
see a forced construct. For a state ``S`` that contains no state owning regions
the expansion is the plain one, a ``-> [*]`` transition on every state below
``S`` that repeats the event and the guard, and this module does not touch it.

When ``S`` contains a state that owns regions, taking ``S`` away has to take the
whole group of every such owner away, and the event and the guard must be
decided **once**, at the place where the machine rests. The expansion therefore
works in two steps.

Expansion (done while forced transitions are resolved):

* Every stoppable state below ``S`` that is outside a region, and every
  stoppable state inside a region of an owner below ``S``, gets a transition
  that repeats the declared event and guard. Outside regions it is a plain
  ``-> [*]`` transition. Inside a region it is an *exit-group* transition
  (:attr:`pyfcstm.model.model.Transition.exit_group_levels`): when it is taken
  the whole group of the outermost owner below ``S`` leaves, regions in reverse
  declaration order and deepest state first, and control returns to that owner.
* Pseudo states get none: they are never rested in.
* On the level of the declaration the transition ``S -> T`` is the declared one.

Lowering (this module, :func:`lower_forced`): one hidden ``int`` variable
``__forced_<n>`` per declaration records that the event and the guard were
already decided.

1. The transitions that start the exit from a resting state raise the variable
   in their effect and keep the declared event and guard.
2. Every composite or owner on the way up gets a relay transition that has no
   event and only waits for the variable.
3. On the level of the declaration a copy that waits for the variable and
   lowers it goes first; the declared transition stays behind it for the case
   that control comes back to its source without the variable raised.
4. While the variable is raised, every other outgoing transition of the states
   on the way gives way, the declared transition included: each of them gets
   the extra condition that the variable is lowered. A forced transition whose
   target cannot be entered therefore takes nothing, whatever else leaves the
   same state.

This is the only place where a transition of the model carries an event and a
guard at the same time: rule 4 adds a condition to a transition that may have an
event. The simulator evaluates both. The language cannot write the pair, so
:meth:`pyfcstm.model.model.Transition.to_ast_node` exports such a transition
with the guard it had before (:func:`authored_guard`).

The module contains:

* :func:`lower_forced` - Install the hidden variables and the relay edges
* :func:`is_forced_carrier` - Tell whether a transition only carries out a
  declaration
* :func:`authored_guard` - The guard a transition had before it was made to
  give way
* :func:`forced_flag_names` - The hidden variables of a lowered machine

The last three are for views that show the model as its author wrote it, such
as the PlantUML export and the diagram snapshot: they leave the carrying
transitions and the hidden variables out and show the declaration once.

Static analyses judge the model as written: model conversion can also build the
machine before lowering (see
:func:`pyfcstm.diagnostics.inspect.inspect_model`), where forced transitions keep
their plain expansion and stop at owners. An analysis that is handed the lowered
machine directly, such as :func:`pyfcstm.verify.run_inspect_algorithms`, sees the
hidden variables and the carrying transitions like any other part of the model,
as it does for a lowered history.

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     event Stop;
    ...     [*] -> Run;
    ...     state Run {
    ...         region A { [*] -> A1; state A1; }
    ...         region B { [*] -> B1; state B1; }
    ...     }
    ...     state Idle;
    ...     !Run -> Idle : /Stop;
    ... }
    ... ''')
    >>> list(model.defines)
    ['__forced_0']
    >>> run = model.root_state.substates['Run']
    >>> [(t.from_state, t.to_state, t.exit_group_levels)
    ...  for region in run.regions.values()
    ...  for t in region.transitions if t.exit_group_levels]
    [('A1', EXIT_STATE, 1), ('B1', EXIT_STATE, 1)]
    >>> [str(t.guard) for t in model.root_state.transitions if t.from_state == 'Run']
    ['__forced_0 == 1', '__forced_0 == 0']
"""

import re
from dataclasses import replace
from typing import (
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from .expr import BinaryOp, Expr, Integer, Variable
from .model import Operation, OperationStatement, State, Transition, VarDefine
from .region import Region, namespace_actions, walk_namespaces

__all__ = ["lower_forced", "is_forced_carrier", "authored_guard", "forced_flag_names"]

_Namespace = Union[State, Region]

# Marks left on transitions by the expansion in
# :func:`pyfcstm.model.model.parse_dsl_node_to_state_machine`: the number of the
# declaration and whether the transition is the one declared on its own level.
_ID_MARK = "_forced_id"
_DECLARED_MARK = "_forced_declared"

# Marks written by the lowering and read back by the three query functions
# below: a transition that exists only to carry out a declaration, the guard a
# transition had before the declaration made it give way, and the hidden
# variables of the machine (kept on its root state).
_HIDDEN_MARK = "_forced_hidden"
_AUTHORED_GUARD_MARK = "_forced_authored_guard"
_FLAGS_MARK = "_forced_flags"


def is_forced_carrier(transition: Transition) -> bool:
    """
    Tell whether a transition only carries out a forced declaration.

    Lowering adds transitions that the author never wrote: the ones that start
    the exit from a resting state, the relays on the way up, and the copy that
    waits for the hidden variable on the level of the declaration. The declared
    transition itself is not one of them.

    :param transition: Transition of a built machine.
    :type transition: pyfcstm.model.model.Transition
    :return: ``True`` if lowering added the transition.
    :rtype: bool

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.forced import is_forced_carrier
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { region A { [*] -> A1; state A1; } }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> [is_forced_carrier(t) for t in model.root_state.transitions]
        [True, False, False]
    """
    return bool(getattr(transition, _HIDDEN_MARK, False))


def authored_guard(transition: Transition) -> Optional[Expr]:
    """
    Return the guard a transition had before forced lowering restricted it.

    Lowering makes the other outgoing transitions of a state give way while a
    forced declaration is being carried out, by adding a condition on the
    hidden variable. This returns the guard without that addition; for every
    other transition it is simply the guard.

    :param transition: Transition of a built machine.
    :type transition: pyfcstm.model.model.Transition
    :return: The guard as written, or ``None`` if there was none.
    :rtype: Optional[pyfcstm.model.expr.Expr]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.forced import authored_guard
        >>> model = load_state_machine_from_text('''
        ... def int x = 1;
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { region A { [*] -> A1; state A1; } }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ...     Run -> Idle : if [x > 0];
        ... }
        ... ''')
        >>> plain = model.root_state.transitions[-1]
        >>> str(plain.guard), str(authored_guard(plain))
        ('x > 0 && __forced_0 == 0', 'x > 0')
    """
    return getattr(transition, _AUTHORED_GUARD_MARK, (transition.guard,))[0]


def forced_flag_names(root_state: State) -> FrozenSet[str]:
    """
    Return the hidden variables that forced lowering installed in a machine.

    :param root_state: Root state of a built machine.
    :type root_state: pyfcstm.model.model.State
    :return: Names of the hidden variables; empty for a machine whose forced
        declarations do not reach regions.
    :rtype: FrozenSet[str]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.forced import forced_flag_names
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run { region A { [*] -> A1; state A1; } }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> sorted(forced_flag_names(model.root_state))
        ['__forced_0']
    """
    return getattr(root_state, _FLAGS_MARK, frozenset())


def _flag_is(name: str, value: int) -> BinaryOp:
    """
    Build the condition ``name == value``.

    :param name: Hidden variable.
    :type name: str
    :param value: Value to compare with.
    :type value: int
    :return: The comparison.
    :rtype: pyfcstm.model.expr.BinaryOp
    """
    return BinaryOp(Variable(name), "==", Integer(value))


def _declarations(root_state: State) -> Dict[int, List[Tuple[_Namespace, Transition]]]:
    """
    Group the expanded transitions by the declaration they came from.

    :param root_state: Root of the machine.
    :type root_state: pyfcstm.model.model.State
    :return: Transitions with the namespace that holds them, per declaration,
        in the order the declarations were resolved.
    :rtype: Dict[int, List[Tuple[Union[State, Region], Transition]]]
    """
    groups: Dict[int, List[Tuple[_Namespace, Transition]]] = {}
    for namespace in walk_namespaces(root_state):
        for transition in namespace.transitions:
            forced_id = getattr(transition, _ID_MARK, None)
            if forced_id is not None:
                groups.setdefault(forced_id, []).append((namespace, transition))
    return dict(sorted(groups.items()))


def _assigned_names(root_state: State) -> Iterator[str]:
    """
    Yield the target of every assignment a machine executes.

    Assignments come from the actions of every state and region and from the
    effects of every transition; the statements of conditional branches are
    included. A name that no variable declares is a temporary of its block.

    :param root_state: Root of the machine.
    :type root_state: pyfcstm.model.model.State
    :return: Assignment targets, possibly repeated.
    :rtype: Iterator[str]
    """

    def targets(statements: Iterable[OperationStatement]) -> Iterator[str]:
        for statement in statements:
            if isinstance(statement, Operation):
                yield statement.var_name
            else:
                for branch in statement.branches:
                    yield from targets(branch.statements)

    for namespace in walk_namespaces(root_state):
        for action in namespace_actions(namespace):
            yield from targets(action.operations)
        for transition in namespace.transitions:
            yield from targets(transition.effects)


def _free_name(taken: Set[str], forced_id: int) -> str:
    """
    Pick the hidden variable of a declaration.

    :param taken: Names the machine already uses: its variables and the targets
        of its assignments, which include the temporaries of action blocks.
    :type taken: Set[str]
    :param forced_id: Number of the declaration.
    :type forced_id: int
    :return: ``__forced_<n>`` for the smallest ``n >= forced_id`` that no used
        name can be mistaken for. Identifier conversion of the target languages
        collapses runs of underscores, so ``_forced_<n>`` counts as taken too.
    :rtype: str
    """
    number = forced_id
    while any(re.fullmatch("_+forced_%d" % number, name) for name in taken):
        number += 1
    return "__forced_%d" % number


def lower_forced(root_state: State, defines: Dict[str, VarDefine]) -> None:
    """
    Make every forced declaration that reaches regions decide once.

    Declarations that did not reach regions carry no mark and are left alone.
    For each marked declaration this installs the hidden variable in
    ``defines``, rewrites the expanded transitions as described in the module
    documentation, and keeps the declared transition on its own level.

    :param root_state: Root of the machine; its transitions are rewritten in
        place.
    :type root_state: pyfcstm.model.model.State
    :param defines: Variable definitions of the machine; the hidden variables
        are added.
    :type defines: Dict[str, pyfcstm.model.base.VarDefine]
    :return: ``None``.
    :rtype: None

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Stop;
        ...     [*] -> Run;
        ...     state Run {
        ...         region A { [*] -> A1; state A1; }
        ...     }
        ...     state Idle;
        ...     !Run -> Idle : /Stop;
        ... }
        ... ''')
        >>> a1 = model.root_state.substates['Run'].regions['A'].transitions
        >>> [str(op.expr) for t in a1 if t.exit_group_levels for op in t.effects]
        ['1']
    """
    declarations = _declarations(root_state)
    # A temporary of an action block would otherwise become a write to the
    # hidden variable once that variable is installed under the same name.
    taken = set(defines).union(_assigned_names(root_state)) if declarations else set()
    for forced_id, items in declarations.items():
        name = _free_name(taken, forced_id)
        taken.add(name)
        raised, lowered = _flag_is(name, 1), _flag_is(name, 0)
        relays: List[Tuple[_Namespace, State]] = []
        for namespace, transition in items:
            source = namespace.substates[transition.from_state]
            declared = getattr(transition, _DECLARED_MARK, False)
            if source.substates or source.regions:
                if declared:
                    # The declared transition keeps its own event and guard for
                    # the case that control comes back without the variable
                    # raised; the copy in front of it takes the raised case.
                    relay = replace(
                        transition,
                        event=None,
                        guard=raised,
                        effects=[
                            Operation(var_name=name, expr=Integer(0)),
                            *transition.effects,
                        ],
                    )
                    setattr(relay, _ID_MARK, forced_id)
                    setattr(relay, _HIDDEN_MARK, True)
                    namespace.transitions.insert(
                        namespace.transitions.index(transition), relay
                    )
                else:
                    transition.event = None
                    transition.guard = raised
                    setattr(transition, _HIDDEN_MARK, True)
                relays.append((namespace, source))
            elif not declared:
                transition.effects = [
                    Operation(var_name=name, expr=Integer(1)),
                    *transition.effects,
                ]
                setattr(transition, _HIDDEN_MARK, True)
        for namespace, source in relays:
            for other in namespace.transitions:
                carries = (
                    is_forced_carrier(other)
                    and getattr(other, _ID_MARK, None) == forced_id
                )
                # Everything but the relay of this declaration gives way, the
                # declared transition included: taken with the variable raised
                # it would enter its target with relays armed inside it.
                if other.from_state == source.name and not carries:
                    _and_condition(other, lowered)
        # A declaration only carries a number when it acts on a state that
        # owns regions, and the source on its own level is then a composite or
        # an owner, so the variable is always needed.
        defines[name] = VarDefine(name=name, type="int", init=Integer(0))
        setattr(root_state, _FLAGS_MARK, forced_flag_names(root_state) | {name})


def _and_condition(transition: Transition, condition: BinaryOp) -> None:
    """
    Add a condition to a transition, whatever trigger it has.

    :class:`~pyfcstm.model.model.Transition` refuses an event and a guard
    together because the language has no way to write them; lowering needs the
    pair, so the guard is written to the field directly.

    :param transition: Transition to restrict.
    :type transition: pyfcstm.model.model.Transition
    :param condition: Condition that must hold as well.
    :type condition: pyfcstm.model.expr.BinaryOp
    :return: ``None``.
    :rtype: None
    """
    if not hasattr(transition, _AUTHORED_GUARD_MARK):
        setattr(transition, _AUTHORED_GUARD_MARK, (transition.guard,))
    guard = (
        condition
        if transition.guard is None
        else BinaryOp(transition.guard, "&&", condition)
    )
    object.__setattr__(transition, "guard", guard)
