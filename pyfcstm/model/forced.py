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
   lowers it goes first; the declared transition stays behind it.
4. While the variable is raised, the other outgoing transitions of the states
   on the way give way: each of them gets the extra condition that the variable
   is lowered.

This is the only place where a transition of the model carries an event and a
guard at the same time: rule 4 adds a condition to a transition that may have an
event. The simulator evaluates both; a consumer that cannot should treat the
pair as a conjunction.

The module contains:

* :func:`lower_forced` - Install the hidden variables and the relay edges

Static analyses judge the model as written: model conversion can also build the
machine before lowering (see
:func:`pyfcstm.diagnostics.inspect.inspect_model`), where forced transitions keep
their plain expansion and stop at owners.

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
    ['__forced_0 == 1', 'None']
"""

import re
from dataclasses import replace
from typing import Dict, List, Tuple, Union

from .expr import BinaryOp, Integer, Variable
from .model import Operation, State, Transition, VarDefine
from .region import Region, walk_namespaces

__all__ = ["lower_forced", "HIDDEN_MARK", "AUTHORED_GUARD_MARK", "FLAGS_MARK"]

_Namespace = Union[State, Region]

# Marks left on transitions by the expansion in
# :func:`pyfcstm.model.model.parse_dsl_node_to_state_machine`: the number of the
# declaration and whether the transition is the one declared on its own level.
_ID_MARK = "_forced_id"
_DECLARED_MARK = "_forced_declared"

# Marks written by the lowering for exporters that show the model as written:
# a transition that exists only to carry out a declaration, and the guard a
# transition had before the declaration made it give way.
HIDDEN_MARK = "_forced_hidden"
AUTHORED_GUARD_MARK = "_forced_authored_guard"
FLAGS_MARK = "_forced_flags"


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


def _free_name(defines: Dict[str, VarDefine], forced_id: int) -> str:
    """
    Pick the hidden variable of a declaration.

    :param defines: Variables of the machine; a taken name is skipped.
    :type defines: Dict[str, pyfcstm.model.base.VarDefine]
    :param forced_id: Number of the declaration.
    :type forced_id: int
    :return: ``__forced_<n>`` for the smallest ``n >= forced_id`` that no
        declared variable can be mistaken for. Identifier conversion of the
        target languages collapses runs of underscores, so ``_forced_<n>``
        counts as taken too.
    :rtype: str
    """
    number = forced_id
    while any(re.fullmatch("_+forced_%d" % number, name) for name in defines):
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
    for forced_id, items in _declarations(root_state).items():
        name = _free_name(defines, forced_id)
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
                    setattr(relay, HIDDEN_MARK, True)
                    namespace.transitions.insert(
                        namespace.transitions.index(transition), relay
                    )
                else:
                    transition.event = None
                    transition.guard = raised
                    setattr(transition, HIDDEN_MARK, True)
                relays.append((namespace, source))
            elif not declared:
                transition.effects = [
                    Operation(var_name=name, expr=Integer(1)),
                    *transition.effects,
                ]
                setattr(transition, HIDDEN_MARK, True)
        for namespace, source in relays:
            for other in namespace.transitions:
                if (
                    other.from_state == source.name
                    and getattr(other, _ID_MARK, None) != forced_id
                ):
                    _and_condition(other, lowered)
        # A declaration only carries a number when it acts on a state that
        # owns regions, and the source on its own level is then a composite or
        # an owner, so the variable is always needed.
        defines[name] = VarDefine(name=name, type="int", init=Integer(0))
        flags = getattr(root_state, FLAGS_MARK, frozenset())
        setattr(root_state, FLAGS_MARK, flags | {name})


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
    if not hasattr(transition, AUTHORED_GUARD_MARK):
        setattr(transition, AUTHORED_GUARD_MARK, (transition.guard,))
    guard = (
        condition
        if transition.guard is None
        else BinaryOp(transition.guard, "&&", condition)
    )
    object.__setattr__(transition, "guard", guard)
