"""
Hierarchical state machine model and DSL conversion utilities.

This module provides the core model objects used to represent hierarchical
state machines, along with conversion helpers that map between the internal
model and the DSL/AST representation. The primary capabilities include:

* Defining states, transitions, events, and variable definitions.
* Representing entry, during, exit, and aspect-oriented actions.
* Parsing a DSL AST into a structured :class:`StateMachine`.
* Exporting models to AST nodes and PlantUML diagrams.

The main public components are:

* :class:`Operation` - Operation assignments used in actions and transitions.
* :class:`Event` - Event definitions scoped to a state path.
* :class:`Transition` - Transition definitions with optional guards and effects.
* :class:`OnStage` - Entry/during/exit actions for a state.
* :class:`OnAspect` - Aspect-oriented during actions.
* :class:`State` - Hierarchical state container with actions and transitions.
* :class:`VarDefine` - Typed variable definitions.
* :class:`StateMachine` - Root container for the full state machine.
* :func:`parse_dsl_node_to_state_machine` - DSL AST parsing utility.

.. note::
   The parsing utilities validate state and variable references. Syntax errors
   are raised when invalid references or structural inconsistencies are found.

Example::

    >>> from pyfcstm.dsl import node as dsl_nodes
    >>> from pyfcstm.model.model import parse_dsl_node_to_state_machine
    >>> program = dsl_nodes.StateMachineDSLProgram(
    ...     definitions=[],
    ...     root_state=dsl_nodes.StateDefinition("root")
    ... )
    >>> sm = parse_dsl_node_to_state_machine(program)
    >>> sm.root_state.name
    'root'

"""
import io
import json
import weakref
from dataclasses import dataclass
from textwrap import indent
from typing import Optional, Union, List, Dict, Tuple, Iterator

from .base import AstExportable, PlantUMLExportable
from .expr import Expr, parse_expr_node_to_expr
from .plantuml import PlantUMLOptions, PlantUMLOptionsInput, format_state_name
from ..dsl import node as dsl_nodes, INIT_STATE, EXIT_STATE

__all__ = [
    'Operation',
    'Event',
    'Transition',
    'OnStage',
    'OnAspect',
    'State',
    'VarDefine',
    'StateMachine',
    'parse_dsl_node_to_state_machine',
]

from ..utils import sequence_safe


@dataclass
class Operation(AstExportable):
    """
    Represents an operation that assigns a value to a variable.

    An operation consists of a variable name and an expression that will be
    assigned to the variable when the operation is executed.

    :param var_name: The name of the variable to assign to
    :type var_name: str
    :param expr: The expression to evaluate and assign to the variable
    :type expr: Expr

    Example::

        >>> op = Operation(var_name="counter", expr=some_expr)
        >>> op.var_name
        'counter'
    """
    var_name: str
    expr: Expr

    def to_ast_node(self) -> dsl_nodes.OperationAssignment:
        """
        Convert this operation to an AST node.

        :return: An operation assignment AST node
        :rtype: dsl_nodes.OperationAssignment
        """
        return dsl_nodes.OperationAssignment(
            name=self.var_name,
            expr=self.expr.to_ast_node(),
        )

    def var_name_to_ast_node(self) -> dsl_nodes.Name:
        """
        Convert the variable name to an AST node.

        :return: A name AST node
        :rtype: dsl_nodes.Name
        """
        return dsl_nodes.Name(name=self.var_name)


@dataclass
class Event:
    """
    Represents an event that can trigger state transitions.

    An event has a name and is associated with a specific state path in the
    state machine hierarchy.

    :param name: The name of the event
    :type name: str
    :param state_path: The path to the state that owns this event
    :type state_path: Tuple[str, ...]
    :param extra_name: Optional extra name for display purposes
    :type extra_name: Optional[str]

    Example::

        >>> event = Event(name="button_pressed", state_path=("root", "idle"))
        >>> event.path
        ('root', 'idle', 'button_pressed')
    """
    name: str
    state_path: Tuple[str, ...]
    extra_name: Optional[str] = None

    @property
    def path(self) -> Tuple[str, ...]:
        """
        Get the full path of the event including the state path and event name.

        :return: The full path to the event
        :rtype: Tuple[str, ...]
        """
        return tuple((*self.state_path, self.name))

    @property
    def path_name(self) -> str:
        """
        Get the canonical dot-separated path string for this event.

        The returned string serves as the stable identifier used by the runtime
        for event indexing and transition matching. This format matches the
        fully-qualified event paths used in the DSL.

        Event paths follow the state hierarchy where the event is defined. For
        example, a local event ``Go`` defined in state ``System.Active`` would
        have the path ``System.Active.Go``.

        :return: Dot-separated event path matching the DSL structure
        :rtype: str

        Example::

            >>> event = Event(name="Start", state_path=("System", "Idle"))
            >>> event.path_name
            'System.Idle.Start'

        .. note::
           This property is used internally by :class:`SimulationRuntime` when
           building the event dictionary for transition matching. The returned
           string must be stable and unique within the state machine.
        """
        return '.'.join(self.path)

    def to_ast_node(self) -> dsl_nodes.EventDefinition:
        """
        Convert this event to an AST node.

        :return: An event definition AST node
        :rtype: dsl_nodes.EventDefinition
        """
        return dsl_nodes.EventDefinition(
            name=self.name,
            extra_name=self.extra_name,
        )


@dataclass
class Transition(AstExportable):
    """
    Represents a transition between states in a state machine.

    A transition defines how the state machine moves from one state to another,
    potentially triggered by an event, guarded by a condition, and with effects
    that execute when the transition occurs.

    :param from_state: The source state name or special state marker
    :type from_state: Union[str, dsl_nodes._StateSingletonMark]
    :param to_state: The target state name or special state marker
    :type to_state: Union[str, dsl_nodes._StateSingletonMark]
    :param event: The event that triggers this transition, if any
    :type event: Optional[Event]
    :param guard: The condition that must be true for the transition to occur, if any
    :type guard: Optional[Expr]
    :param effects: Operations to execute when the transition occurs
    :type effects: List[Operation]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> transition = Transition(
        ...     from_state="idle",
        ...     to_state="active",
        ...     event=None,
        ...     guard=None,
        ...     effects=[]
        ... )
    """
    from_state: Union[str, dsl_nodes._StateSingletonMark]
    to_state: Union[str, dsl_nodes._StateSingletonMark]
    event: Optional[Event]
    guard: Optional[Expr]
    effects: List[Operation]
    parent_ref: Optional[weakref.ReferenceType] = None

    @property
    def parent(self) -> Optional['State']:
        """
        Get the parent state of this transition.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']) -> None:
        """
        Set the parent state of this transition.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    def to_ast_node(self) -> dsl_nodes.TransitionDefinition:
        """
        Convert this transition to an AST node.

        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        return State.transition_to_ast_node(self.parent, self)


@dataclass
class OnStage(AstExportable):
    """
    Represents an action that occurs during a specific stage of a state's lifecycle.

    OnStage can represent enter, during, or exit actions, and can be either concrete
    operations or abstract function declarations.

    :param stage: The lifecycle stage ('enter', 'during', or 'exit')
    :type stage: str
    :param aspect: For 'during' actions in composite states, specifies if the action occurs 'before' or 'after' substates
    :type aspect: Optional[str]
    :param name: For abstract functions, the name of the function
    :type name: Optional[str]
    :param doc: For abstract functions, the documentation string
    :type doc: Optional[str]
    :param operations: For concrete actions, the list of operations to execute
    :type operations: List[Operation]
    :param is_abstract: Whether this is an abstract function declaration
    :type is_abstract: bool
    :param state_path: The path to the state that owns this action
    :type state_path: Tuple[Optional[str], ...]
    :param ref: Reference to another OnStage or OnAspect for function references
    :type ref: Union['OnStage', 'OnAspect', None]
    :param ref_state_path: The path to the referenced state for function references
    :type ref_state_path: Optional[Tuple[str, ...]]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> on_enter = OnStage(
        ...     stage="enter",
        ...     aspect=None,
        ...     name="init_counter",
        ...     doc=None,
        ...     operations=[],
        ...     is_abstract=False,
        ...     state_path=("root", "init_counter")
        ... )
    """
    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[Operation]
    is_abstract: bool
    state_path: Tuple[Optional[str], ...]
    ref: Union['OnStage', 'OnAspect', None] = None
    ref_state_path: Optional[Tuple[str, ...]] = None
    parent_ref: Optional[weakref.ReferenceType] = None

    @property
    def parent(self) -> Optional['State']:
        """
        Get the parent state of this action.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None  # pragma: no cover
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']) -> None:
        """
        Set the parent state of this action.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_ref(self) -> bool:
        """
        Check if this action is a reference to another function.

        :return: True if this is a reference, False otherwise
        :rtype: bool
        """
        return bool(self.ref)

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: False for OnStage instances (always)
        :rtype: bool
        """
        return False

    @property
    def func_name(self) -> str:
        """
        Get the readable dot-separated path string for this action.

        The returned string represents the action's location in the state hierarchy,
        making it easy to identify which state owns the action in log messages and
        diagnostic output.

        Unnamed actions (where the name component is ``None``) are rendered with
        ``<unnamed>`` in the terminal position.

        :return: Dot-separated action path with state hierarchy
        :rtype: str

        Example::

            >>> # Named enter action
            >>> action.func_name
            'System.Active.Initialize'
            >>> # Unnamed during action
            >>> action.func_name
            'System.Active.<unnamed>'
        """
        sp = self.state_path
        if sp[-1] is None:
            sp = tuple((*sp[:-1], '<unnamed>'))
        return '.'.join(sp)

    def to_ast_node(self) -> Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]:
        """
        Convert this OnStage to an appropriate AST node based on the stage.

        :return: An enter, during, or exit statement AST node
        :rtype: Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]
        :raises ValueError: If the stage is not one of 'enter', 'during', or 'exit'
        """
        if self.stage == 'enter':
            if self.is_abstract:
                return dsl_nodes.EnterAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[:len(spath)] == spath:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[len(spath):]), is_absolute=False)
                else:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[1:]), is_absolute=True)
                return dsl_nodes.EnterRefFunction(
                    name=self.name,
                    ref=ref
                )
            else:
                return dsl_nodes.EnterOperations(
                    name=self.name,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'during':
            if self.is_abstract:
                return dsl_nodes.DuringAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[:len(spath)] == spath:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[len(spath):]), is_absolute=False)
                else:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[1:]), is_absolute=True)
                return dsl_nodes.DuringRefFunction(
                    name=self.name,
                    aspect=self.aspect,
                    ref=ref
                )
            else:
                return dsl_nodes.DuringOperations(
                    name=self.name,
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'exit':
            if self.is_abstract:
                return dsl_nodes.ExitAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[:len(spath)] == spath:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[len(spath):]), is_absolute=False)
                else:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[1:]), is_absolute=True)
                return dsl_nodes.ExitRefFunction(
                    name=self.name,
                    ref=ref
                )
            else:
                return dsl_nodes.ExitOperations(
                    name=self.name,
                    operations=[item.to_ast_node() for item in self.operations],
                )
        else:
            raise ValueError(f'Unknown stage - {self.stage!r}.')  # pragma: no cover


@dataclass
class OnAspect(AstExportable):
    """
    Represents an aspect-oriented action that occurs during a specific stage of a state's lifecycle.

    OnAspect is specifically used for aspect-oriented programming features in the state machine,
    allowing actions to be defined that apply across multiple states.

    :param stage: The lifecycle stage (currently only supports 'during')
    :type stage: str
    :param aspect: Specifies if the action occurs 'before' or 'after' substates
    :type aspect: Optional[str]
    :param name: For abstract functions, the name of the function
    :type name: Optional[str]
    :param doc: For abstract functions, the documentation string
    :type doc: Optional[str]
    :param operations: For concrete actions, the list of operations to execute
    :type operations: List[Operation]
    :param is_abstract: Whether this is an abstract function declaration
    :type is_abstract: bool
    :param state_path: The path to the state that owns this action
    :type state_path: Tuple[Optional[str], ...]
    :param ref: Reference to another OnStage or OnAspect for function references
    :type ref: Union['OnStage', 'OnAspect', None]
    :param ref_state_path: The path to the referenced state for function references
    :type ref_state_path: Optional[Tuple[str, ...]]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]

    Example::

        >>> aspect = OnAspect(
        ...     stage="during",
        ...     aspect="before",
        ...     name="log_entry",
        ...     doc=None,
        ...     operations=[],
        ...     is_abstract=True,
        ...     state_path=("root", "log_entry")
        ... )
    """
    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[Operation]
    is_abstract: bool
    state_path: Tuple[Optional[str], ...]
    ref: Union['OnStage', 'OnAspect', None] = None
    ref_state_path: Optional[Tuple[str, ...]] = None
    parent_ref: Optional[weakref.ReferenceType] = None

    @property
    def parent(self) -> Optional['State']:
        """
        Get the parent state of this aspect action.

        :return: The parent state or None if no parent is set
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None  # pragma: no cover
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']) -> None:
        """
        Set the parent state of this aspect action.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_ref(self) -> bool:
        """
        Check if this action is a reference to another function.

        :return: True if this is a reference, False otherwise
        :rtype: bool
        """
        return bool(self.ref)

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: True for OnAspect instances (always)
        :rtype: bool
        """
        return True

    @property
    def func_name(self) -> str:
        """
        Get the readable dot-separated path string for this action.

        The returned string represents the action's location in the state hierarchy,
        making it easy to identify which state owns the action in log messages and
        diagnostic output.

        Unnamed actions (where the name component is ``None``) are rendered with
        ``<unnamed>`` in the terminal position.

        :return: Dot-separated action path with state hierarchy
        :rtype: str

        Example::

            >>> # Named aspect action
            >>> action.func_name
            'System.PreProcess'
            >>> # Unnamed aspect action
            >>> action.func_name
            'System.<unnamed>'
        """
        sp = self.state_path
        if sp[-1] is None:
            sp = tuple((*sp[:-1], '<unnamed>'))
        return '.'.join(sp)

    def to_ast_node(self) -> Union[dsl_nodes.DuringAspectStatement]:
        """
        Convert this OnAspect to an appropriate AST node based on the stage.

        :return: A during aspect statement AST node
        :rtype: Union[dsl_nodes.DuringAspectStatement]
        :raises ValueError: If the stage is not 'during'
        """
        if self.stage == 'during':
            if self.is_abstract:
                return dsl_nodes.DuringAspectAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            elif self.is_ref:
                spath = self.state_path[:-1]
                if self.ref_state_path[:len(spath)] == spath:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[len(spath):]), is_absolute=False)
                else:
                    ref = dsl_nodes.ChainID(path=list(self.ref_state_path[1:]), is_absolute=True)
                return dsl_nodes.DuringAspectRefFunction(
                    name=self.name,
                    aspect=self.aspect,
                    ref=ref
                )
            else:
                return dsl_nodes.DuringAspectOperations(
                    name=self.name,
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        else:
            raise ValueError(f'Unknown aspect - {self.stage!r}.')  # pragma: no cover


@dataclass
class State(AstExportable, PlantUMLExportable):
    """
    Represents a state in a hierarchical state machine.

    A state can contain substates, transitions between those substates, and actions
    that execute on enter, during, or exit of the state.

    :param name: The name of the state
    :type name: str
    :param path: The full path to this state in the hierarchy
    :type path: Tuple[str, ...]
    :param substates: Dictionary mapping substate names to State objects
    :type substates: Dict[str, 'State']
    :param events: Dictionary mapping event names to Event objects
    :type events: Dict[str, Event]
    :param transitions: List of transitions between substates
    :type transitions: List[Transition]
    :param named_functions: Dictionary mapping function names to their implementations
    :type named_functions: Dict[str, Union[OnStage, OnAspect]]
    :param on_enters: List of actions to execute when entering the state
    :type on_enters: List[OnStage]
    :param on_durings: List of actions to execute while in the state
    :type on_durings: List[OnStage]
    :param on_exits: List of actions to execute when exiting the state
    :type on_exits: List[OnStage]
    :param on_during_aspects: List of aspect-oriented actions for the during stage
    :type on_during_aspects: List[OnAspect]
    :param parent_ref: Weak reference to the parent state
    :type parent_ref: Optional[weakref.ReferenceType]
    :param substate_name_to_id: Dictionary mapping substate names to numeric IDs
    :type substate_name_to_id: Dict[str, int]
    :param extra_name: Optional extra name for display purposes
    :type extra_name: Optional[str]
    :param is_pseudo: Whether this is a pseudo state
    :type is_pseudo: bool

    Example::

        >>> state = State(
        ...     name="idle",
        ...     path=("root", "idle"),
        ...     substates={}
        ... )
        >>> state.is_leaf_state
        True
    """
    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, Event] = None
    transitions: List[Transition] = None
    named_functions: Dict[str, Union[OnStage, OnAspect]] = None
    on_enters: List[OnStage] = None
    on_durings: List[OnStage] = None
    on_exits: List[OnStage] = None
    on_during_aspects: List[OnAspect] = None
    parent_ref: Optional[weakref.ReferenceType] = None
    substate_name_to_id: Dict[str, int] = None
    extra_name: Optional[str] = None
    is_pseudo: bool = False

    def __post_init__(self) -> None:
        """
        Initialize default values for optional fields after instance creation.
        """
        self.events = self.events or {}
        self.transitions = self.transitions or []
        self.named_functions = self.named_functions or {}
        self.on_enters = self.on_enters or []
        self.on_durings = self.on_durings or []
        self.on_exits = self.on_exits or []
        self.on_during_aspects = self.on_during_aspects or []
        self.substate_name_to_id = {name: i for i, (name, _) in enumerate(self.substates.items())}

    @property
    def is_leaf_state(self) -> bool:
        """
        Check if this state is a leaf state (has no substates).

        :return: True if this is a leaf state, False otherwise
        :rtype: bool
        """
        return len(self.substates) == 0

    @property
    def is_stoppable(self) -> bool:
        """
        Check if this state is stoppable (is a leaf state and not pseudo).

        :return: True if this state is stoppable, False otherwise
        :rtype: bool
        """
        return self.is_leaf_state and not self.is_pseudo

    @property
    def parent(self) -> Optional['State']:
        """
        Get the parent state of this state.

        :return: The parent state or None if this is the root state
        :rtype: Optional['State']
        """
        if self.parent_ref is None:
            return None
        else:
            return self.parent_ref()

    @parent.setter
    def parent(self, new_parent: Optional['State']) -> None:
        """
        Set the parent state of this state.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    @property
    def is_root_state(self) -> bool:
        """
        Check if this state is the root state (has no parent).

        :return: True if this is the root state, False otherwise
        :rtype: bool
        """
        return self.parent is None

    @property
    def init_transitions(self) -> List[Transition]:
        """
        Get all transitions that start from the initial state (INIT_STATE).

        :return: List of transitions from INIT_STATE
        :rtype: List[Transition]
        """
        retval = []
        for transition in self.transitions:
            if transition.from_state == dsl_nodes.INIT_STATE:
                retval.append(transition)
        return retval

    @property
    def transitions_from(self) -> List[Transition]:
        """
        Get all transitions that start from this state.

        For non-root states, these are transitions in the parent state where this state
        is the source. For the root state, a synthetic transition to EXIT_STATE is returned.

        :return: List of transitions from this state
        :rtype: List[Transition]
        """
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.from_state == self.name:
                    retval.append(transition)
        else:
            retval.append(Transition(
                from_state=self.name,
                to_state=EXIT_STATE,
                event=None,
                guard=None,
                effects=[],
                parent_ref=self.parent_ref,
            ))
        return retval

    @property
    def transitions_to(self) -> List[Transition]:
        """
        Get all transitions that end at this state.

        For non-root states, these are transitions in the parent state where this state
        is the target. For the root state, a synthetic transition from INIT_STATE is returned.

        :return: List of transitions to this state
        :rtype: List[Transition]
        """
        parent = self.parent
        retval = []
        if parent is not None:
            for transition in parent.transitions:
                if transition.to_state == self.name:
                    retval.append(transition)
        else:
            retval.append(Transition(
                from_state=INIT_STATE,
                to_state=self.name,
                event=None,
                guard=None,
                effects=[],
                parent_ref=self.parent_ref,
            ))

        return retval

    @property
    def transitions_entering_children(self) -> List[Transition]:
        """
        Get all transitions that start from the initial state (INIT_STATE).

        These are the transitions that define the initial substate when entering this state.

        :return: List of transitions from INIT_STATE
        :rtype: List[Transition]
        """
        return [
            transition for transition in self.transitions
            if transition.from_state is INIT_STATE
        ]

    @property
    def transitions_entering_children_simplified(self) -> List[Optional[Transition]]:
        """
        Get a simplified list of transitions entering child states.

        If there's a default transition (no event or guard), only include that one.
        Otherwise include all transitions and add None at the end.

        :return: List of transitions, possibly with None at the end
        :rtype: List[Optional[Transition]]
        """
        retval = []
        for transition in self.transitions:
            if transition.from_state is INIT_STATE:
                retval.append(transition)
                if transition.event is None and transition.guard is None:
                    break
        if not retval or (retval and not (retval[-1].event is None and retval[-1].guard is None)):
            retval.append(None)
        return retval

    def list_on_enters(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of enter actions, optionally filtered by abstract status and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of enter actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_enters, 1):
            if (is_abstract is not None and
                    ((item.is_abstract and not is_abstract) or (not item.is_abstract and is_abstract))):
                continue
            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_enters(self) -> List[OnStage]:
        """
        Get all abstract enter actions.

        :return: List of abstract enter actions
        :rtype: List[OnStage]
        """
        return self.list_on_enters(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_enters(self) -> List[OnStage]:
        """
        Get all non-abstract enter actions.

        :return: List of non-abstract enter actions
        :rtype: List[OnStage]
        """
        return self.list_on_enters(is_abstract=False, with_ids=False)

    def list_on_durings(self, is_abstract: Optional[bool] = None, aspect: Optional[str] = None,
                        with_ids: bool = False) -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of during actions, optionally filtered by abstract status, aspect, and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param aspect: If provided, filter to only actions with the given aspect ('before' or 'after')
        :type aspect: Optional[str]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_durings, 1):
            if (is_abstract is not None and
                    ((item.is_abstract and not is_abstract) or (not item.is_abstract and is_abstract))):
                continue
            if aspect is not None and item.aspect != aspect:
                continue

            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_durings(self) -> List[OnStage]:
        """
        Get all abstract during actions.

        :return: List of abstract during actions
        :rtype: List[OnStage]
        """
        return self.list_on_durings(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_durings(self) -> List[OnStage]:
        """
        Get all non-abstract during actions.

        :return: List of non-abstract during actions
        :rtype: List[OnStage]
        """
        return self.list_on_durings(is_abstract=False, with_ids=False)

    def list_on_exits(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> List[Union[Tuple[int, OnStage], OnStage]]:
        """
        Get a list of exit actions, optionally filtered by abstract status and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of exit actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnStage], OnStage]]
        """
        retval = []
        for id_, item in enumerate(self.on_exits, 1):
            if (is_abstract is not None and
                    ((item.is_abstract and not is_abstract) or (not item.is_abstract and is_abstract))):
                continue
            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_exits(self) -> List[OnStage]:
        """
        Get all abstract exit actions.

        :return: List of abstract exit actions
        :rtype: List[OnStage]
        """
        return self.list_on_exits(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_exits(self) -> List[OnStage]:
        """
        Get all non-abstract exit actions.

        :return: List of non-abstract exit actions
        :rtype: List[OnStage]
        """
        return self.list_on_exits(is_abstract=False, with_ids=False)

    def list_on_during_aspects(self, is_abstract: Optional[bool] = None, aspect: Optional[str] = None,
                               with_ids: bool = False) -> List[Union[Tuple[int, OnAspect], OnAspect]]:
        """
        Get a list of during aspect actions, optionally filtered by abstract status, aspect, and with IDs.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param aspect: If provided, filter to only actions with the given aspect ('before' or 'after')
        :type aspect: Optional[str]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during aspect actions, optionally with IDs
        :rtype: List[Union[Tuple[int, OnAspect], OnAspect]]
        """
        retval = []
        for id_, item in enumerate(self.on_during_aspects, 1):
            if (is_abstract is not None and
                    ((item.is_abstract and not is_abstract) or (not item.is_abstract and is_abstract))):
                continue
            if aspect is not None and item.aspect != aspect:
                continue

            if with_ids:
                retval.append((id_, item))
            else:
                retval.append(item)
        return retval

    @property
    def abstract_on_during_aspects(self) -> List[OnAspect]:
        """
        Get all abstract during aspect actions.

        :return: List of abstract during aspect actions
        :rtype: List[OnAspect]
        """
        return self.list_on_during_aspects(is_abstract=True, with_ids=False)

    @property
    def non_abstract_on_during_aspects(self) -> List[OnAspect]:
        """
        Get all non-abstract during aspect actions.

        :return: List of non-abstract during aspect actions
        :rtype: List[OnAspect]
        """
        return self.list_on_during_aspects(is_abstract=False, with_ids=False)

    def iter_on_during_before_aspect_recursively(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Recursively iterate through 'before' aspect during actions from parent states to this state.

        This method traverses the state hierarchy from the root state to this state,
        yielding all 'before' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if self.parent is not None:
            yield from self.parent.iter_on_during_before_aspect_recursively(is_abstract=is_abstract, with_ids=with_ids)
        if with_ids:
            for id_, item in self.list_on_during_aspects(is_abstract=is_abstract, aspect='before', with_ids=with_ids):
                yield id_, self, item
        else:
            for item in self.list_on_during_aspects(is_abstract=is_abstract, aspect='before', with_ids=with_ids):
                yield self, item

    def iter_on_during_after_aspect_recursively(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Recursively iterate through 'after' aspect during actions from this state to the root state.

        This method traverses the state hierarchy from this state to the root state,
        yielding all 'after' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if with_ids:
            for id_, item in self.list_on_during_aspects(is_abstract=is_abstract, aspect='after', with_ids=with_ids):
                yield id_, self, item
        else:
            for item in self.list_on_during_aspects(is_abstract=is_abstract, aspect='after', with_ids=with_ids):
                yield self, item
        if self.parent is not None:
            yield from self.parent.iter_on_during_after_aspect_recursively(is_abstract=is_abstract, with_ids=with_ids)

    def iter_on_during_aspect_recursively(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Recursively iterate through all during actions in the proper execution order.

        This method yields actions in the following order:

        1. 'Before' aspect actions from root state to this state
        2. Regular during actions for this state
        3. 'After' aspect actions from this state to root state

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: Iterator[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        if not self.is_pseudo:
            yield from self.iter_on_during_before_aspect_recursively(is_abstract=is_abstract, with_ids=with_ids)
        if with_ids:
            for id_, item in self.list_on_durings(is_abstract=is_abstract, aspect=None, with_ids=with_ids):
                yield id_, self, item
        else:
            for item in self.list_on_durings(is_abstract=is_abstract, aspect=None, with_ids=with_ids):
                yield self, item
        if not self.is_pseudo:
            yield from self.iter_on_during_after_aspect_recursively(is_abstract=is_abstract, with_ids=with_ids)

    def list_on_during_aspect_recursively(self, is_abstract: Optional[bool] = None, with_ids: bool = False) \
            -> List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Get a list of all during actions in the proper execution order.

        This is a convenience method that collects the results of iter_on_during_aspect_recursively.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :return: List of during actions in execution order
        :rtype: List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        return list(self.iter_on_during_aspect_recursively(is_abstract, with_ids))

    @classmethod
    def transition_to_ast_node(cls, self: Optional['State'], transition: Transition) -> dsl_nodes.TransitionDefinition:
        """
        Convert a transition to an AST node, considering the context of its parent state.

        :param self: The parent state, or None
        :type self: Optional['State']
        :param transition: The transition to convert
        :type transition: Transition
        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        if self:
            cur_path = self.path
        else:
            cur_path = ()

        if transition.event:
            if len(transition.event.path) > len(cur_path) and transition.event.path[:len(cur_path)] == cur_path:
                event_id = dsl_nodes.ChainID(path=list(transition.event.path[len(cur_path):]), is_absolute=False)
            else:
                event_id = dsl_nodes.ChainID(path=list(transition.event.path[1:]), is_absolute=True)
        else:
            event_id = None

        return dsl_nodes.TransitionDefinition(
            from_state=transition.from_state,
            to_state=transition.to_state,
            event_id=event_id,
            condition_expr=transition.guard.to_ast_node() if transition.guard is not None else None,
            post_operations=[
                item.to_ast_node()
                for item in transition.effects
            ]
        )

    def to_transition_ast_node(self, transition: Transition) -> dsl_nodes.TransitionDefinition:
        """
        Convert a transition to an AST node in the context of this state.

        :param transition: The transition to convert
        :type transition: Transition
        :return: A transition definition AST node
        :rtype: dsl_nodes.TransitionDefinition
        """
        return self.transition_to_ast_node(self, transition)

    def to_ast_node(self) -> dsl_nodes.StateDefinition:
        """
        Convert this state to an AST node.

        :return: A state definition AST node
        :rtype: dsl_nodes.StateDefinition
        """
        return dsl_nodes.StateDefinition(
            name=self.name,
            extra_name=self.extra_name,
            events=[event.to_ast_node() for _, event in self.events.items()],
            substates=[substate.to_ast_node() for _, substate in self.substates.items()],
            transitions=[self.to_transition_ast_node(trans) for trans in self.transitions],
            enters=[item.to_ast_node() for item in self.on_enters],
            durings=[item.to_ast_node() for item in self.on_durings],
            exits=[item.to_ast_node() for item in self.on_exits],
            during_aspects=[item.to_ast_node() for item in self.on_during_aspects],
            is_pseudo=bool(self.is_pseudo),
        )

    def to_plantuml(self, options: PlantUMLOptionsInput = None, current_depth: int = 0, event_colors: Optional[Dict[str, str]] = None) -> str:
        """
        Convert this state to PlantUML notation.

        :param options: Configuration input for PlantUML generation
        :type options: PlantUMLOptionsInput
        :param current_depth: Current depth in the state hierarchy (for max_depth support)
        :type current_depth: int
        :param event_colors: Optional mapping of event paths to color codes
        :type event_colors: Optional[Dict[str, str]]
        :return: PlantUML representation of the state
        :rtype: str
        """
        # Resolve configuration
        options = PlantUMLOptions.from_value(options)
        config = options.to_config()

        if event_colors is None:
            event_colors = {}

        def _name_safe(sub_state: Optional[str] = None) -> str:
            subpath = [*self.path]
            if sub_state is not None:
                subpath.append(sub_state)
            return sequence_safe(subpath)

        # Check if this is an empty state (for collapse_empty_states)
        is_empty_state = (
            not self.on_enters and
            not self.on_durings and
            not self.on_exits and
            not self.on_during_aspects
        )

        state_style_marks = []
        if self.is_pseudo and config.show_pseudo_state_style:
            state_style_marks.append('line.dotted')
        state_style_mark_str = " #" + ";".join(state_style_marks) if state_style_marks else ""

        # Build stereotype string
        stereotype_parts = []
        if config.use_stereotypes:
            if self.is_pseudo:
                stereotype_parts.append('pseudo')
            if not self.is_leaf_state:
                stereotype_parts.append('composite')
        stereotype_str = f' <<{",".join(stereotype_parts)}>>' if stereotype_parts else ""

        with io.StringIO() as sf:
            # Format state name according to configuration
            shown_name = format_state_name(self, config.state_name_format)

            print(f'state {json.dumps(shown_name, ensure_ascii=False)} as {_name_safe()}{stereotype_str}{state_style_mark_str}',
                  file=sf, end='')

            if not self.is_leaf_state:
                print(f' {{', file=sf)

                # Check if we should expand substates or collapse them
                should_expand_substates = (
                    config.max_depth is None or
                    current_depth < config.max_depth
                )

                if should_expand_substates:
                    # Expand substates normally
                    for state in self.substates.values():
                        print(indent(state.to_plantuml(options, current_depth=current_depth + 1, event_colors=event_colors), prefix='    '), file=sf)
                else:
                    # Collapsed: show marker state
                    marker_name = config.collapsed_state_marker
                    marker_safe_name = sequence_safe([*self.path, '__collapsed__'])
                    print(f'    state {json.dumps(marker_name, ensure_ascii=False)} as {marker_safe_name}', file=sf)

                for trans in self.transitions:
                    with io.StringIO() as tf:
                        print('[*]' if trans.from_state is dsl_nodes.INIT_STATE
                              else _name_safe(trans.from_state), file=tf, end='')

                        # Apply event_visualization_mode colors to arrow
                        arrow_str = ' -->'
                        if config.event_visualization_mode in ('color', 'both') and trans.event is not None:
                            event_path = '.'.join(trans.event.path)
                            if event_path in event_colors:
                                color = event_colors[event_path]
                                arrow_str = f' -[{color}]->'

                        print(arrow_str, file=tf, end=' ')
                        print('[*]' if trans.to_state is dsl_nodes.EXIT_STATE
                              else _name_safe(trans.to_state), file=tf, end='')

                        trans_node: dsl_nodes.TransitionDefinition = trans.to_ast_node()

                        # Show event if enabled
                        if config.show_events and trans.event is not None:
                            from .plantuml import format_event_name
                            formatted_event = format_event_name(trans.event, config.event_name_format, trans_node=trans_node)
                            print(f' : {formatted_event}', file=tf, end='')
                        elif config.show_transition_guards and trans.guard is not None:
                            print(f' : {trans.guard.to_ast_node()}', file=tf, end='')

                        # Show transition effects if enabled
                        if config.show_transition_effects and len(trans.effects) > 0:
                            if config.transition_effect_mode == 'note':
                                print('', file=tf)
                                print('note on link', file=tf)
                                print('effect {', file=tf)
                                for operation in trans.effects:
                                    print(f'    {operation.to_ast_node()}', file=tf)
                                print('}', file=tf)
                                print('end note', file=tf, end='')
                            elif config.transition_effect_mode == 'inline':
                                # Display effects inline on the transition arrow
                                effect_strs = [str(operation.to_ast_node()) for operation in trans.effects]
                                effect_text = '; '.join(effect_strs)
                                # Append to existing label or create new one
                                print(f' / {effect_text}', file=tf, end='')

                        trans_text = tf.getvalue()
                    print(indent(trans_text, prefix='    '), file=sf)

                print(f'}}', file=sf, end='')

            # Show lifecycle actions if enabled (skip if collapse_empty_states is True and state is empty)
            should_show_actions = (
                not (config.collapse_empty_states and is_empty_state) and
                (
                    (config.show_lifecycle_actions and config.show_enter_actions and self.on_enters) or
                    (config.show_lifecycle_actions and config.show_during_actions and self.on_durings) or
                    (config.show_lifecycle_actions and config.show_exit_actions and self.on_exits) or
                    (config.show_lifecycle_actions and config.show_aspect_actions and self.on_during_aspects)
                )
            )

            if should_show_actions:
                from .plantuml import should_show_action, format_action_text

                print('', file=sf)
                with io.StringIO() as tf:
                    if config.show_enter_actions:
                        for enter_item in self.on_enters:
                            # Apply abstract/concrete filtering
                            if should_show_action(enter_item, config):
                                formatted_text = format_action_text(enter_item, config)
                                print(formatted_text, file=tf)
                    if config.show_during_actions:
                        for during_item in self.on_durings:
                            if should_show_action(during_item, config):
                                formatted_text = format_action_text(during_item, config)
                                print(formatted_text, file=tf)
                    if config.show_exit_actions:
                        for exit_item in self.on_exits:
                            if should_show_action(exit_item, config):
                                formatted_text = format_action_text(exit_item, config)
                                print(formatted_text, file=tf)
                    if config.show_aspect_actions:
                        for during_aspect_item in self.on_during_aspects:
                            if should_show_action(during_aspect_item, config):
                                formatted_text = format_action_text(during_aspect_item, config)
                                print(formatted_text, file=tf)

                    action_text = tf.getvalue().rstrip().replace('\r\n', '\n').replace('\r', '\n')
                    if action_text:  # Only show if there's actual content
                        text = json.dumps(action_text).strip("\"")
                        print(f'{_name_safe()} : {text}', file=sf, end='')

            return sf.getvalue()

    def walk_states(self) -> Iterator['State']:
        """
        Iterate through this state and all its substates recursively.

        :yield: Each state in the hierarchy, starting with this one
        :rtype: Iterator['State']
        """
        yield self
        for _, substate in self.substates.items():
            yield from substate.walk_states()

    def resolve_event(self, event_ref: str) -> Event:
        """
        Resolve an event reference string to an existing Event object in the state hierarchy.

        This method supports three types of event references:

        1. **Relative events** (e.g., ``"xxx.yyy.zzz"``): Resolved relative to the current state's path.
           If the current state is ``XXX.YYY``, the event resolves to ``XXX.YYY.xxx.yyy.zzz``.

        2. **Parent-relative events** (e.g., ``".xxx.yyy.zzz"``): Each leading dot represents moving up
           one level in the state hierarchy. If the current state is ``XXX.YYY.ZZZ``, then ``.xxx``
           resolves to ``XXX.YYY.xxx`` (up one level), and ``..xxx`` resolves to ``XXX.xxx`` (up two levels).

        3. **Absolute events** (e.g., ``"/xxx.yyy"``): Resolved relative to the root state.
           If the root state is ``Root``, the event resolves to ``Root.xxx.yyy``.

        :param event_ref: The event reference string to resolve
        :type event_ref: str
        :return: The resolved Event object from the state hierarchy
        :rtype: Event
        :raises ValueError: If the event reference is invalid or cannot be resolved
        :raises ValueError: If parent-relative reference goes beyond the root state
        :raises LookupError: If the event does not exist in the state hierarchy

        Example::

            >>> # Assuming current state path is ("Root", "System", "Active")
            >>> # and an event "critical" exists in state "Root.System.Active.error"
            >>> state.resolve_event("error.critical")
            Event(name="critical", state_path=("Root", "System", "Active", "error"))

            >>> state.resolve_event(".error.critical")
            Event(name="critical", state_path=("Root", "System", "error"))

            >>> state.resolve_event("/global.shutdown")
            Event(name="shutdown", state_path=("Root", "global"))
        """
        if not event_ref:
            raise ValueError("Event reference cannot be empty")

        # Determine the target state path and event name based on reference type
        target_state_path = None
        event_name = None

        # Handle absolute events (starting with '/')
        if event_ref.startswith('/'):
            # Remove leading '/' and resolve from root
            relative_path = event_ref[1:]
            if not relative_path:
                raise ValueError("Absolute event reference cannot be just '/'")

            # Find root state
            root_state = self
            while root_state.parent is not None:
                root_state = root_state.parent

            # Split the path
            path_parts = relative_path.split('.')
            if not all(path_parts):
                raise ValueError(f"Invalid absolute event reference: {event_ref!r}")

            event_name = path_parts[-1]
            target_state_path = root_state.path + tuple(path_parts[:-1])

        # Handle parent-relative events (starting with '.')
        elif event_ref.startswith('.'):
            # Count leading dots
            dot_count = 0
            for char in event_ref:
                if char == '.':
                    dot_count += 1
                else:
                    break

            # Get the remaining path after dots
            remaining_path = event_ref[dot_count:]
            if not remaining_path:
                raise ValueError(f"Parent-relative event reference cannot end with dots: {event_ref!r}")

            # Move up the hierarchy
            current_state = self
            for _ in range(dot_count):
                if current_state.parent is None:
                    raise ValueError(
                        f"Parent-relative event reference {event_ref!r} goes beyond root state "
                        f"(current state: {'.'.join(self.path)}, tried to go up {dot_count} levels)"
                    )
                current_state = current_state.parent

            # Split the remaining path
            path_parts = remaining_path.split('.')
            if not all(path_parts):
                raise ValueError(f"Invalid parent-relative event reference: {event_ref!r}")

            event_name = path_parts[-1]
            target_state_path = current_state.path + tuple(path_parts[:-1])

        # Handle relative events (no leading '/' or '.')
        else:
            path_parts = event_ref.split('.')
            if not all(path_parts):
                raise ValueError(f"Invalid relative event reference: {event_ref!r}")

            event_name = path_parts[-1]
            target_state_path = self.path + tuple(path_parts[:-1])

        # Now find the state and retrieve the event
        # First, find the root state
        root_state = self
        while root_state.parent is not None:
            root_state = root_state.parent

        # Navigate to the target state
        current_state = root_state
        for i, state_name in enumerate(target_state_path[1:], 1):  # Skip root name
            if state_name not in current_state.substates:
                raise LookupError(
                    f"State {'.'.join(target_state_path[:i+1])!r} not found in hierarchy "
                    f"while resolving event reference {event_ref!r}"
                )
            current_state = current_state.substates[state_name]

        # Look for the event in the target state
        if event_name not in current_state.events:
            raise LookupError(
                f"Event {event_name!r} not found in state {'.'.join(target_state_path)!r} "
                f"while resolving event reference {event_ref!r}"
            )

        return current_state.events[event_name]


@dataclass
class VarDefine(AstExportable):
    """
    Represents a variable definition in a state machine.

    :param name: The name of the variable
    :type name: str
    :param type: The type of the variable
    :type type: str
    :param init: The initial value expression
    :type init: Expr

    Example::

        >>> var_def = VarDefine(name="counter", type="int", init=some_expr)
        >>> var_def.name
        'counter'
    """
    name: str
    type: str
    init: Expr

    def to_ast_node(self) -> dsl_nodes.DefAssignment:
        """
        Convert this variable definition to an AST node.

        :return: A definition assignment AST node
        :rtype: dsl_nodes.DefAssignment
        """
        return dsl_nodes.DefAssignment(
            name=self.name,
            type=self.type,
            expr=self.init.to_ast_node(),
        )

    def name_ast_node(self) -> dsl_nodes.Name:
        """
        Convert the variable name to an AST node.

        :return: A name AST node
        :rtype: dsl_nodes.Name
        """
        return dsl_nodes.Name(self.name)


@dataclass
class StateMachine(AstExportable, PlantUMLExportable):
    """
    Represents a complete state machine with variable definitions and a root state.

    :param defines: Dictionary mapping variable names to their definitions
    :type defines: Dict[str, VarDefine]
    :param root_state: The root state of the state machine
    :type root_state: State

    Example::

        >>> sm = StateMachine(defines={}, root_state=some_state)
        >>> list(sm.walk_states())  # Get all states in the machine
        [...]
    """
    defines: Dict[str, VarDefine]
    root_state: State

    def to_ast_node(self) -> dsl_nodes.StateMachineDSLProgram:
        """
        Convert this state machine to an AST node.

        :return: A state machine DSL program AST node
        :rtype: dsl_nodes.StateMachineDSLProgram
        """
        return dsl_nodes.StateMachineDSLProgram(
            definitions=[
                def_item.to_ast_node()
                for _, def_item in self.defines.items()
            ],
            root_state=self.root_state.to_ast_node(),
        )

    def to_plantuml(self, options: PlantUMLOptionsInput = None) -> str:
        """
        Convert this state machine to PlantUML notation.

        :param options: Configuration input for PlantUML generation
        :type options: PlantUMLOptionsInput
        :return: PlantUML representation of the state machine
        :rtype: str
        """
        # Resolve configuration
        options = PlantUMLOptions.from_value(options)
        config = options.to_config()

        with io.StringIO() as sf:
            print('@startuml', file=sf)
            print('hide empty description', file=sf)

            # Add skinparam styling if enabled
            if config.use_skinparam:
                print('', file=sf)
                print('skinparam state {', file=sf)
                print('  BackgroundColor<<pseudo>> LightGray', file=sf)
                print('  BackgroundColor<<composite>> LightBlue', file=sf)
                print('  BorderColor<<pseudo>> Gray', file=sf)
                print('  FontStyle<<pseudo>> italic', file=sf)
                print('}', file=sf)
                print('', file=sf)

            # Show variable definitions if enabled
            if config.show_variable_definitions and self.defines:
                if config.variable_display_mode == 'note':
                    print('note as DefinitionNote', file=sf)
                    print('defines {', file=sf)
                    for def_item in self.defines.values():
                        print(f'    {def_item.to_ast_node()}', file=sf)
                    print('}', file=sf)
                    print('end note', file=sf)
                    print('', file=sf)
                elif config.variable_display_mode == 'legend':
                    # Display variables as a legend
                    from .plantuml import escape_plantuml_table_cell
                    # Use configured legend position
                    print(f'legend {config.variable_legend_position}', file=sf)
                    # Header row
                    print('|= Variable |= Type |= Initial Value |', file=sf)
                    for def_item in self.defines.values():
                        var_name = def_item.name
                        var_type = def_item.type
                        var_init = def_item.init.to_ast_node() if def_item.init else 'N/A'
                        # Escape pipe characters in the initial value
                        var_init_escaped = escape_plantuml_table_cell(str(var_init))
                        # All columns left-aligned
                        print(f'| {var_name} | {var_type} | {var_init_escaped} |', file=sf)
                    print('endlegend', file=sf)
                    print('', file=sf)

            # Collect events and assign colors if event visualization is enabled
            event_colors = {}
            event_map = {}
            if config.event_visualization_mode != 'none':
                from .plantuml import collect_event_transitions, assign_event_colors
                event_map = collect_event_transitions(self)
                event_colors = assign_event_colors(event_map, config.custom_colors)

            # Add event legend if event_visualization_mode is 'legend' or 'both'
            if config.event_visualization_mode in ('legend', 'both') and event_map:
                print(f'legend {config.event_legend_position}', file=sf)
                print('**Event Scoping**', file=sf)
                print('----', file=sf)
                for event_path in sorted(event_map.keys()):
                    transitions = event_map[event_path]
                    color = event_colors.get(event_path, '#000000')
                    # Show event name and count
                    event_name = event_path.split('.')[-1]
                    print(f'<color:{color}>■</color> **{event_name}** ({len(transitions)} transitions)', file=sf)
                    # Show event path
                    print(f'  <size:10><color:gray>/{".".join(event_path.split(".")[1:])}</color></size>', file=sf)
                print('endlegend', file=sf)
                print('', file=sf)

            print(self.root_state.to_plantuml(options, event_colors=event_colors), file=sf)
            print(f'[*] --> {sequence_safe(self.root_state.path)}', file=sf)
            print(f'{sequence_safe(self.root_state.path)} --> [*]', file=sf)
            print('@enduml', file=sf, end='')
            return sf.getvalue()

    def walk_states(self) -> Iterator[State]:
        """
        Iterate through all states in the state machine.

        :yield: Each state in the hierarchy
        :rtype: Iterator[State]
        """
        yield from self.root_state.walk_states()

    def resolve_event(self, event_path: str) -> Event:
        """
        Resolve a full event path to an existing Event object in the state machine.

        This method requires a complete event path in the format ``State1.State2.State3.event_name``,
        where the path must include all states from the root to the event location. Unlike
        :meth:`State.resolve_event`, this method does not support relative, parent-relative,
        or absolute path notations (no leading dots or slashes).

        :param event_path: The complete event path (e.g., ``"Root.System.Active.error"``)
        :type event_path: str
        :return: The resolved Event object from the state hierarchy
        :rtype: Event
        :raises ValueError: If the event path is invalid or empty
        :raises LookupError: If any state in the path or the event does not exist

        Example::

            >>> # Assuming a state machine with Root -> System -> Active -> error event
            >>> sm = StateMachine(defines={}, root_state=root_state)
            >>> event = sm.resolve_event("Root.System.Active.error")
            >>> event.name
            'error'
        """
        if not event_path:
            raise ValueError("Event path cannot be empty")

        # Split the path into components
        path_parts = event_path.split('.')
        if not all(path_parts):
            raise ValueError(f"Invalid event path: {event_path!r} (contains empty parts)")

        if len(path_parts) < 2:
            raise ValueError(
                f"Invalid event path: {event_path!r} "
                f"(must contain at least state name and event name)"
            )

        # The last part is the event name, everything before is the state path
        event_name = path_parts[-1]
        state_path_parts = path_parts[:-1]

        # Navigate to the target state starting from root
        current_state = self.root_state

        # Verify the first part matches the root state name
        if state_path_parts[0] != current_state.name:
            raise LookupError(
                f"Event path root '{state_path_parts[0]}' does not match "
                f"state machine root '{current_state.name}' "
                f"while resolving event path {event_path!r}"
            )

        # Navigate through the remaining state path
        for i, state_name in enumerate(state_path_parts[1:], 1):
            if state_name not in current_state.substates:
                raise LookupError(
                    f"State '{state_name}' not found in state '{'.'.join(state_path_parts[:i])}' "
                    f"while resolving event path {event_path!r}"
                )
            current_state = current_state.substates[state_name]

        # Look for the event in the target state
        if event_name not in current_state.events:
            raise LookupError(
                f"Event '{event_name}' not found in state '{'.'.join(state_path_parts)}' "
                f"while resolving event path {event_path!r}"
            )

        return current_state.events[event_name]


def parse_dsl_node_to_state_machine(dnode: dsl_nodes.StateMachineDSLProgram) -> StateMachine:
    """
    Parse a state machine DSL program AST node into a StateMachine object.

    This function validates the state machine structure and builds a complete
    StateMachine object with all states, transitions, events, and variable definitions.

    :param dnode: The state machine DSL program AST node to parse
    :type dnode: dsl_nodes.StateMachineDSLProgram

    :return: The parsed state machine
    :rtype: StateMachine

    :raises SyntaxError: If there are syntax errors in the state machine definition,
                         such as duplicate variable definitions, unknown states in
                         transitions, missing entry transitions, or invalid references.

    Example::

        >>> # Assuming you have a parsed DSL node
        >>> state_machine = parse_dsl_node_to_state_machine(dsl_program_node)
        >>> state_machine.root_state.name
        'root'
    """
    d_defines = {}
    for def_item in dnode.definitions:
        if def_item.name not in d_defines:
            d_defines[def_item.name] = VarDefine(
                name=def_item.name,
                type=def_item.type,
                init=parse_expr_node_to_expr(def_item.expr),
            )
        else:
            raise SyntaxError(f'Duplicated variable definition - {def_item}.')

    def _parse_operation_block(
            op_nodes: List[dsl_nodes.OperationAssignment],
            unknown_var_message: str,
            owner_node: AstExportable,
    ) -> List[Operation]:
        operations = []
        available_vars = set(d_defines)
        for op_item in op_nodes:
            operation_val = parse_expr_node_to_expr(op_item.expr)
            unknown_vars = []
            for var in operation_val.list_variables():
                if var.name not in available_vars and var.name not in unknown_vars:
                    unknown_vars.append(var.name)

            if unknown_vars:
                raise SyntaxError(
                    f'{unknown_var_message} {", ".join(unknown_vars)} in transition:\n{owner_node}'
                )

            operations.append(Operation(var_name=op_item.name, expr=operation_val))
            available_vars.add(op_item.name)

        return operations

    def _recursive_build_states(node: dsl_nodes.StateDefinition, current_path: Tuple[str, ...]) -> State:
        current_path = tuple((*current_path, node.name))
        d_substates = {}

        for subnode in node.substates:
            if subnode.name not in d_substates:
                d_substates[subnode.name] = _recursive_build_states(subnode, current_path=current_path)
            else:
                raise SyntaxError(f'Duplicate state name in namespace {".".join(current_path)!r}:\n{subnode}')

        named_functions = {}
        on_enters = []
        for enter_item in node.enters:
            on_stage = None
            if isinstance(enter_item, dsl_nodes.EnterOperations):
                enter_operations = _parse_operation_block(
                    enter_item.operations,
                    'Unknown enter operation variable',
                    enter_item,
                )
                on_stage = OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=None,
                    operations=enter_operations,
                    is_abstract=False,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(enter_item, dsl_nodes.EnterAbstractFunction):
                on_stage = OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=enter_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(enter_item, dsl_nodes.EnterRefFunction):
                on_stage = OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, enter_item.name),
                    ref=None,
                    ref_state_path=(
                        *((dnode.root_state.name,) if enter_item.ref.is_absolute else current_path),
                        *enter_item.ref.path
                    ),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        raise SyntaxError(f'Duplicate function name {on_stage.name!r} in state:\n{node}')
                    named_functions[on_stage.name] = on_stage
                on_enters.append(on_stage)

        on_durings = []
        for during_item in node.durings:
            if not d_substates and during_item.aspect is not None:
                raise SyntaxError(
                    f'For leaf state {node.name!r}, during cannot assign aspect {during_item.aspect!r}:\n{during_item}')
            if d_substates and during_item.aspect is None:
                raise SyntaxError(
                    f'For composite state {node.name!r}, during must assign aspect to either \'before\' or \'after\':\n{during_item}')

            on_stage = None
            if isinstance(during_item, dsl_nodes.DuringOperations):
                during_operations = _parse_operation_block(
                    during_item.operations,
                    'Unknown during operation variable',
                    during_item,
                )
                on_stage = OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=None,
                    operations=during_operations,
                    is_abstract=False,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(during_item, dsl_nodes.DuringAbstractFunction):
                on_stage = OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=during_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(during_item, dsl_nodes.DuringRefFunction):
                on_stage = OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, during_item.name),
                    ref=None,
                    ref_state_path=(
                        *((dnode.root_state.name,) if during_item.ref.is_absolute else current_path),
                        *during_item.ref.path
                    ),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        raise SyntaxError(f'Duplicate function name {on_stage.name!r} in state:\n{node}')
                    named_functions[on_stage.name] = on_stage
                on_durings.append(on_stage)

        on_exits = []
        for exit_item in node.exits:
            on_stage = None
            if isinstance(exit_item, dsl_nodes.ExitOperations):
                exit_operations = _parse_operation_block(
                    exit_item.operations,
                    'Unknown exit operation variable',
                    exit_item,
                )
                on_stage = OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=None,
                    operations=exit_operations,
                    is_abstract=False,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(exit_item, dsl_nodes.ExitAbstractFunction):
                on_stage = OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=exit_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(exit_item, dsl_nodes.ExitRefFunction):
                on_stage = OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, exit_item.name),
                    ref=None,
                    ref_state_path=(
                        *((dnode.root_state.name,) if exit_item.ref.is_absolute else current_path),
                        *exit_item.ref.path
                    ),
                )

            if on_stage is not None:
                if on_stage.name:
                    if on_stage.name in named_functions:
                        raise SyntaxError(f'Duplicate function name {on_stage.name!r} in state:\n{node}')
                    named_functions[on_stage.name] = on_stage
                on_exits.append(on_stage)

        on_during_aspects = []
        for during_aspect_item in node.during_aspects:
            on_aspect = None
            if isinstance(during_aspect_item, dsl_nodes.DuringAspectOperations):
                during_operations = _parse_operation_block(
                    during_aspect_item.operations,
                    'Unknown during aspect variable',
                    during_aspect_item,
                )
                on_aspect = OnAspect(
                    stage='during',
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=None,
                    operations=during_operations,
                    is_abstract=False,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(during_aspect_item, dsl_nodes.DuringAspectAbstractFunction):
                on_aspect = OnAspect(
                    stage='during',
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=during_aspect_item.doc,
                    operations=[],
                    is_abstract=True,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=None,
                )
            elif isinstance(during_aspect_item, dsl_nodes.DuringAspectRefFunction):
                on_aspect = OnAspect(
                    stage='during',
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=None,
                    operations=[],
                    is_abstract=False,
                    state_path=(*current_path, during_aspect_item.name),
                    ref=None,
                    ref_state_path=(
                        *((dnode.root_state.name,) if during_aspect_item.ref.is_absolute else current_path),
                        *during_aspect_item.ref.path
                    ),
                )

            if on_aspect is not None:
                if on_aspect.name:
                    if on_aspect.name in named_functions:
                        raise SyntaxError(f'Duplicate function name {on_aspect.name!r} in state:\n{node}')
                    named_functions[on_aspect.name] = on_aspect
                on_during_aspects.append(on_aspect)

        d_events = {}
        for event in node.events:
            d_events[event.name] = Event(
                name=event.name,
                extra_name=event.extra_name,
                state_path=current_path,
            )

        my_state = State(
            name=node.name,
            extra_name=node.extra_name,
            events=d_events,
            path=current_path,
            substates=d_substates,
            is_pseudo=bool(node.is_pseudo),
            on_enters=on_enters,
            on_durings=on_durings,
            on_exits=on_exits,
            on_during_aspects=on_during_aspects,
            named_functions=named_functions,
        )
        if my_state.is_pseudo and not my_state.is_leaf_state:
            raise SyntaxError(f'Pseudo state {".".join(current_path)} must be a leaf state:\n{node}')
        for func_item in [*my_state.on_enters, *my_state.on_durings, *my_state.on_exits, *my_state.on_during_aspects]:
            func_item.parent = my_state
        for _, substate in d_substates.items():
            substate.parent = my_state
        return my_state

    root_state = _recursive_build_states(dnode.root_state, current_path=())

    def _recursive_finish_states(node: dsl_nodes.StateDefinition, current_state: State, current_path: Tuple[str, ...],
                                 force_transitions: Optional[List[dsl_nodes.ForceTransitionDefinition]] = None) -> None:
        current_path = tuple((*current_path, current_state.name))
        force_transitions = list(force_transitions or [])

        force_transition_tuples_to_inherit = []
        for f_transnode in [*force_transitions, *node.force_transitions]:
            if f_transnode.from_state == dsl_nodes.ALL:
                from_state = dsl_nodes.ALL
            else:
                from_state = f_transnode.from_state
                if from_state not in current_state.substates:
                    raise SyntaxError(f'Unknown from state {from_state!r} of force transition:\n{f_transnode}')

            if f_transnode.to_state is dsl_nodes.EXIT_STATE:
                to_state = dsl_nodes.EXIT_STATE
            else:
                to_state = f_transnode.to_state
                if to_state not in current_state.substates:
                    raise SyntaxError(f'Unknown to state {to_state!r} of force transition:\n{f_transnode}')

            my_event_id, trans_event = None, None
            if f_transnode.event_id is not None:
                my_event_id = f_transnode.event_id
                if not my_event_id.is_absolute:
                    my_event_id = dsl_nodes.ChainID(
                        path=[*current_state.path[1:], *my_event_id.path],
                        is_absolute=True
                    )
                start_state = root_state
                base_path = (root_state.name,)
                for seg in my_event_id.path[:-1]:
                    if seg in start_state.substates:
                        start_state = start_state.substates[seg]
                    else:
                        raise SyntaxError(
                            f'Cannot find state {".".join((*base_path, *my_event_id.path[:-1]))} for transition:\n{f_transnode}')

                suffix_name = my_event_id.path[-1]
                if suffix_name not in start_state.events:
                    start_state.events[suffix_name] = Event(
                        name=suffix_name,
                        state_path=start_state.path,
                    )
                trans_event = start_state.events[suffix_name]

            condition_expr, guard = f_transnode.condition_expr, None
            if f_transnode.condition_expr is not None:
                guard = parse_expr_node_to_expr(f_transnode.condition_expr)
                unknown_vars = []
                for var in guard.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if unknown_vars:
                    raise SyntaxError(
                        f'Unknown guard variable {", ".join(unknown_vars)} in force transition:\n{f_transnode}')

            force_transition_tuples_to_inherit.append(
                (from_state, to_state, my_event_id, trans_event, condition_expr, guard))

        transitions = current_state.transitions
        for subnode in node.substates:
            _inner_force_transitions = []
            for from_state, to_state, my_event_id, trans_event, condition_expr, guard in force_transition_tuples_to_inherit:
                if from_state is dsl_nodes.ALL or from_state == subnode.name:
                    transitions.append(Transition(
                        from_state=subnode.name,
                        to_state=to_state,
                        event=trans_event,
                        guard=guard,
                        effects=[],
                    ))
                    _inner_force_transitions.append(dsl_nodes.ForceTransitionDefinition(
                        from_state=dsl_nodes.ALL,
                        to_state=dsl_nodes.EXIT_STATE,
                        event_id=my_event_id,
                        condition_expr=condition_expr,
                    ))

            _recursive_finish_states(
                node=subnode,
                current_state=current_state.substates[subnode.name],
                current_path=current_path,
                force_transitions=_inner_force_transitions,
            )

        has_entry_trans = False
        for transnode in node.transitions:
            if transnode.from_state is dsl_nodes.INIT_STATE:
                from_state = dsl_nodes.INIT_STATE
                has_entry_trans = True
            else:
                from_state = transnode.from_state
                if from_state not in current_state.substates:
                    raise SyntaxError(f'Unknown from state {from_state!r} of transition:\n{transnode}')

            if transnode.to_state is dsl_nodes.EXIT_STATE:
                to_state = dsl_nodes.EXIT_STATE
            else:
                to_state = transnode.to_state
                if to_state not in current_state.substates:
                    raise SyntaxError(f'Unknown to state {to_state!r} of transition:\n{transnode}')

            trans_event, guard = None, None
            if transnode.event_id is not None:
                if transnode.event_id.is_absolute:
                    start_state = root_state
                    base_path = (root_state.name,)
                else:
                    start_state = current_state
                    base_path = current_state.path
                for seg in transnode.event_id.path[:-1]:
                    if seg in start_state.substates:
                        start_state = start_state.substates[seg]
                    else:
                        raise SyntaxError(
                            f'Cannot find state {".".join((*base_path, *transnode.event_id.path[:-1]))} for transition:\n{transnode}')

                suffix_name = transnode.event_id.path[-1]
                if suffix_name not in start_state.events:
                    start_state.events[suffix_name] = Event(
                        name=suffix_name,
                        state_path=start_state.path,
                    )
                trans_event = start_state.events[suffix_name]

            if transnode.condition_expr is not None:
                guard = parse_expr_node_to_expr(transnode.condition_expr)
                unknown_vars = []
                for var in guard.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if unknown_vars:
                    raise SyntaxError(f'Unknown guard variable {", ".join(unknown_vars)} in transition:\n{transnode}')

            post_operations = _parse_operation_block(
                transnode.post_operations,
                'Unknown transition operation variable',
                transnode,
            )

            transition = Transition(
                from_state=from_state,
                to_state=to_state,
                event=trans_event,
                guard=guard,
                effects=post_operations,
            )
            transitions.append(transition)

        if current_state.substates and not has_entry_trans:
            raise SyntaxError(
                f'At least 1 entry transition should be assigned in non-leaf state {node.name!r}:\n{node}')

        for func_item in [
            *current_state.on_enters,
            *current_state.on_durings,
            *current_state.on_exits,
            *current_state.on_during_aspects,
        ]:
            if func_item.ref_state_path is not None:
                state = root_state
                for i, segment in enumerate(func_item.ref_state_path[1:-1], start=1):
                    if segment not in state.substates:
                        raise SyntaxError(f'Cannot find state {".".join(func_item.ref_state_path[:i + 1])} '
                                          f'under state {".".join(func_item.ref_state_path[:i])}, '
                                          f'so cannot resolve reference {".".join(func_item.ref_state_path)!r}.')
                    state = state.substates[segment]

                segment = func_item.ref_state_path[-1]
                if segment not in state.named_functions:
                    raise SyntaxError(f'Cannot find named function {segment!r} under state:\n{state.to_ast_node()}')
                func_item.ref = state.named_functions[segment]
                assert func_item.ref.state_path == func_item.ref_state_path

        for transition in current_state.transitions:
            transition.parent = current_state

    _recursive_finish_states(dnode.root_state, current_state=root_state, current_path=())
    return StateMachine(
        defines=d_defines,
        root_state=root_state,
    )
