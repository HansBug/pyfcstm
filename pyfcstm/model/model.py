"""
State machine module for parsing and representing hierarchical state machines.

This module provides classes and functions for working with state machines, including:

- Representation of states, transitions, events, and operations
- Parsing state machine DSL nodes into state machine objects
- Exporting state machines to AST nodes and PlantUML diagrams

The module implements a hierarchical state machine model with support for:

- Nested states
- Entry, during, and exit actions
- Guards and effects on transitions
- Abstract function declarations
- Variable definitions
"""
import io
import json
import weakref
from dataclasses import dataclass
from textwrap import indent
from typing import Optional, Union, List, Dict, Tuple

from .base import AstExportable, PlantUMLExportable
from .expr import Expr, parse_expr_node_to_expr
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
    """
    name: str
    state_path: Tuple[str, ...]

    @property
    def path(self) -> Tuple[str, ...]:
        """
        Get the full path of the event including the state path and event name.

        :return: The full path to the event
        :rtype: Tuple[str, ...]
        """
        return tuple((*self.state_path, self.name))


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
    def parent(self, new_parent: Optional['State']):
        """
        Set the parent state of this transition.

        :param new_parent: The new parent state or None to clear the parent
        :type new_parent: Optional['State']
        """
        if new_parent is None:
            self.parent_ref = None  # pragma: no cover
        else:
            self.parent_ref = weakref.ref(new_parent)

    def to_ast_node(self) -> dsl_nodes.ASTNode:
        """
        Convert this transition to an AST node.

        :return: A transition definition AST node
        :rtype: dsl_nodes.ASTNode
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
    """
    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[Operation]

    @property
    def is_abstract(self) -> bool:
        """
        Check if this is an abstract function declaration.

        :return: True if this is an abstract function, False otherwise
        :rtype: bool
        """
        return self.name is not None or self.doc is not None

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: False for OnStage instances (always)
        :rtype: bool
        """
        return False

    def to_ast_node(self) -> Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]:
        """
        Convert this OnStage to an appropriate AST node based on the stage.

        :return: An enter, during, or exit statement AST node
        :rtype: Union[dsl_nodes.EnterStatement, dsl_nodes.DuringStatement, dsl_nodes.ExitStatement]
        :raises ValueError: If the stage is not one of 'enter', 'during', or 'exit'
        """
        if self.stage == 'enter':
            if self.name or self.doc is not None:
                return dsl_nodes.EnterAbstractFunction(
                    name=self.name,
                    doc=self.doc,
                )
            else:
                return dsl_nodes.EnterOperations(
                    name=self.name,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'during':
            if self.name or self.doc is not None:
                return dsl_nodes.DuringAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
                )
            else:
                return dsl_nodes.DuringOperations(
                    name=self.name,
                    aspect=self.aspect,
                    operations=[item.to_ast_node() for item in self.operations],
                )

        elif self.stage == 'exit':
            if self.name or self.doc is not None:
                return dsl_nodes.ExitAbstractFunction(
                    name=self.name,
                    doc=self.doc,
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
    """
    stage: str
    aspect: Optional[str]
    name: Optional[str]
    doc: Optional[str]
    operations: List[Operation]

    @property
    def is_abstract(self) -> bool:
        """
        Check if this is an abstract function declaration.

        :return: True if this is an abstract function, False otherwise
        :rtype: bool
        """
        return self.name is not None or self.doc is not None

    @property
    def is_aspect(self) -> bool:
        """
        Check if this is an aspect-oriented action.

        :return: True for OnAspect instances (always)
        :rtype: bool
        """
        return True

    def to_ast_node(self) -> Union[dsl_nodes.DuringAspectStatement]:
        """
        Convert this OnAspect to an appropriate AST node based on the stage.

        :return: A during aspect statement AST node
        :rtype: Union[dsl_nodes.DuringAspectStatement]
        :raises ValueError: If the stage is not 'during'
        """
        if self.stage == 'during':
            if self.name or self.doc is not None:
                return dsl_nodes.DuringAspectAbstractFunction(
                    name=self.name,
                    aspect=self.aspect,
                    doc=self.doc,
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
    """
    name: str
    path: Tuple[str, ...]
    substates: Dict[str, 'State']
    events: Dict[str, Event] = None
    transitions: List[Transition] = None
    on_enters: List[OnStage] = None
    on_durings: List[OnStage] = None
    on_exits: List[OnStage] = None
    on_during_aspects: List[OnAspect] = None
    parent_ref: Optional[weakref.ReferenceType] = None
    substate_name_to_id: Dict[str, int] = None

    def __post_init__(self):
        """
        Initialize the substate_name_to_id dictionary after instance creation.
        """
        self.events = self.events or {}
        self.transitions = self.transitions or []
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
    def parent(self, new_parent: Optional['State']):
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
            -> List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Recursively iterate through 'before' aspect during actions from parent states to this state.

        This method traverses the state hierarchy from the root state to this state,
        yielding all 'before' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
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
            -> List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
        """
        Recursively iterate through 'after' aspect during actions from this state to the root state.

        This method traverses the state hierarchy from this state to the root state,
        yielding all 'after' aspect during actions along the way.

        :param is_abstract: If provided, filter to only abstract (True) or non-abstract (False) actions
        :type is_abstract: Optional[bool]
        :param with_ids: Whether to include numeric IDs with the actions
        :type with_ids: bool
        :yield: Tuples of (state, action) or (id, state, action) if with_ids is True
        :rtype: List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
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
            -> List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]:
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
        :rtype: List[Union[Tuple[int, 'State', Union[OnAspect, OnStage]], Tuple['State', Union[OnAspect, OnStage]]]]
        """
        yield from self.iter_on_during_before_aspect_recursively(is_abstract=is_abstract, with_ids=with_ids)
        if with_ids:
            for id_, item in self.list_on_durings(is_abstract=is_abstract, aspect=None, with_ids=with_ids):
                yield id_, self, item
        else:
            for item in self.list_on_durings(is_abstract=is_abstract, aspect=None, with_ids=with_ids):
                yield self, item
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
    def transition_to_ast_node(cls, self: Optional['State'], transition: Transition):
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
                # is relative path
                event_id = dsl_nodes.ChainID(path=list(transition.event.path[len(cur_path):]), is_absolute=False)
            else:
                # use absolute path
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
            substates=[
                substate.to_ast_node()
                for _, substate in self.substates.items()
            ],
            transitions=[self.to_transition_ast_node(trans) for trans in self.transitions],
            enters=[item.to_ast_node() for item in self.on_enters],
            durings=[item.to_ast_node() for item in self.on_durings],
            exits=[item.to_ast_node() for item in self.on_exits],
            during_aspects=[item.to_ast_node() for item in self.on_during_aspects],
        )

    def to_plantuml(self) -> str:
        """
        Convert this state to PlantUML notation.

        :return: PlantUML representation of the state
        :rtype: str
        """
        with io.StringIO() as sf:
            if self.is_leaf_state:
                print(f'state {self.name}', file=sf, end='')
            else:
                print(f'state {self.name} {{', file=sf)
                for state in self.substates.values():
                    print(indent(state.to_plantuml(), prefix='    '), file=sf)
                for trans in self.transitions:
                    with io.StringIO() as tf:
                        print('[*]' if trans.from_state is dsl_nodes.INIT_STATE else trans.from_state, file=tf, end='')
                        print(' --> ', file=tf, end='')
                        print('[*]' if trans.to_state is dsl_nodes.EXIT_STATE else trans.to_state, file=tf, end='')

                        if trans.event is not None:
                            print(f' : {".".join(list(trans.event.path[len(self.path):]))}', file=tf, end='')
                        elif trans.guard is not None:
                            print(f' : {trans.guard.to_ast_node()}', file=tf, end='')

                        if len(trans.effects) > 0:
                            print('', file=tf)
                            print('note on link', file=tf)
                            print('effect {', file=tf)
                            for operation in trans.effects:
                                print(f'    {operation.to_ast_node()}', file=tf)
                            print('}', file=tf)
                            print('end note', file=tf, end='')

                        trans_text = tf.getvalue()
                    print(indent(trans_text, prefix='    '), file=sf)
                print(f'}}', file=sf, end='')

            if self.on_enters or self.on_durings or self.on_exits:
                print('', file=sf)
                with io.StringIO() as tf:
                    for enter_item in self.on_enters:
                        print(enter_item.to_ast_node(), file=tf)
                    for during_item in self.on_durings:
                        print(during_item.to_ast_node(), file=tf)
                    for exit_item in self.on_exits:
                        print(exit_item.to_ast_node(), file=tf)
                    for during_aspect_item in self.on_during_aspects:
                        print(during_aspect_item.to_ast_node(), file=tf)
                    text = json.dumps(tf.getvalue().rstrip()).strip("\"")
                    print(f'{self.name} : {text}', file=sf, end='')

            return sf.getvalue()

    def walk_states(self):
        """
        Iterate through this state and all its substates recursively.

        :yield: Each state in the hierarchy, starting with this one
        :rtype: Iterator['State']
        """
        yield self
        for _, substate in self.substates.items():
            yield from substate.walk_states()


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

    def to_plantuml(self) -> str:
        """
        Convert this state machine to PlantUML notation.

        :return: PlantUML representation of the state machine
        :rtype: str
        """
        with io.StringIO() as sf:
            print('@startuml', file=sf)
            if self.defines:
                print('note as DefinitionNote', file=sf)
                print('defines {', file=sf)
                for def_item in self.defines.values():
                    print(f'    {def_item.to_ast_node()}', file=sf)
                print('}', file=sf)
                print('end note', file=sf)
                print('', file=sf)
            print(self.root_state.to_plantuml(), file=sf)
            print(f'[*] --> {self.root_state.name}', file=sf)
            print(f'{self.root_state.name} --> [*]', file=sf)
            print('@enduml', file=sf, end='')
            return sf.getvalue()

    def walk_states(self):
        """
        Iterate through all states in the state machine.

        :yield: Each state in the hierarchy
        :rtype: Iterator[State]
        """
        yield from self.root_state.walk_states()


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
                         transitions, missing entry transitions, etc.
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

    def _recursive_build_states(node: dsl_nodes.StateDefinition, current_path: Tuple[str, ...]):
        current_path = tuple((*current_path, node.name))
        d_substates = {}

        for subnode in node.substates:
            if subnode.name not in d_substates:
                d_substates[subnode.name] = _recursive_build_states(subnode, current_path=current_path)
            else:
                raise SyntaxError(f'Duplicate state name in namespace {".".join(current_path)!r}:\n{subnode}')

        my_state = State(
            name=node.name,
            path=current_path,
            substates=d_substates,
        )
        for _, substate in d_substates.items():
            substate.parent = my_state
        return my_state

    root_state = _recursive_build_states(dnode.root_state, current_path=())

    def _recursive_finish_states(node: dsl_nodes.StateDefinition, current_state: State, current_path: Tuple[str, ...],
                                 force_transitions: List[dsl_nodes.ForceTransitionDefinition] = None):
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

            post_operations = []
            for op_item in transnode.post_operations:
                operation_val = parse_expr_node_to_expr(op_item.expr)
                unknown_vars = []
                for var in operation_val.list_variables():
                    if var.name not in d_defines:
                        unknown_vars.append(var.name)
                if op_item.name not in d_defines and op_item.name not in unknown_vars:
                    unknown_vars.append(op_item.name)
                if unknown_vars:
                    raise SyntaxError(
                        f'Unknown transition operation variable {", ".join(unknown_vars)} in transition:\n{transnode}')
                post_operations.append(Operation(var_name=op_item.name, expr=operation_val))

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

        on_enters = current_state.on_enters
        for enter_item in node.enters:
            if isinstance(enter_item, dsl_nodes.EnterOperations):
                enter_operations = []
                for op_item in enter_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown enter operation variable {", ".join(unknown_vars)} in transition:\n{enter_item}')
                    enter_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_enters.append(OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=None,
                    operations=enter_operations,
                ))
            elif isinstance(enter_item, dsl_nodes.EnterAbstractFunction):
                on_enters.append(OnStage(
                    stage='enter',
                    aspect=None,
                    name=enter_item.name,
                    doc=enter_item.doc,
                    operations=[],
                ))

        on_durings = current_state.on_durings
        for during_item in node.durings:
            if not current_state.substates and during_item.aspect is not None:
                raise SyntaxError(
                    f'For leaf state {node.name!r}, during cannot assign aspect {during_item.aspect!r}:\n{during_item}')
            if current_state.substates and during_item.aspect is None:
                raise SyntaxError(
                    f'For composite state {node.name!r}, during must assign aspect to either \'before\' or \'after\':\n{during_item}')

            if isinstance(during_item, dsl_nodes.DuringOperations):
                during_operations = []
                for op_item in during_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown during operation variable {", ".join(unknown_vars)} in transition:\n{during_item}')
                    during_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_durings.append(OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=None,
                    operations=during_operations,
                ))
            elif isinstance(during_item, dsl_nodes.DuringAbstractFunction):
                on_durings.append(OnStage(
                    stage='during',
                    aspect=during_item.aspect,
                    name=during_item.name,
                    doc=during_item.doc,
                    operations=[],
                ))

        on_exits = current_state.on_exits
        for exit_item in node.exits:
            if isinstance(exit_item, dsl_nodes.ExitOperations):
                exit_operations = []
                for op_item in exit_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown exit operation variable {", ".join(unknown_vars)} in transition:\n{exit_item}')
                    exit_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_exits.append(OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=None,
                    operations=exit_operations,
                ))
            elif isinstance(exit_item, dsl_nodes.ExitAbstractFunction):
                on_exits.append(OnStage(
                    stage='exit',
                    aspect=None,
                    name=exit_item.name,
                    doc=exit_item.doc,
                    operations=[],
                ))

        on_during_aspects = current_state.on_during_aspects
        for during_aspect_item in node.during_aspects:
            if isinstance(during_aspect_item, dsl_nodes.DuringAspectOperations):
                during_operations = []
                for op_item in during_aspect_item.operations:
                    operation_val = parse_expr_node_to_expr(op_item.expr)
                    unknown_vars = []
                    for var in operation_val.list_variables():
                        if var.name not in d_defines:
                            unknown_vars.append(var.name)
                    if op_item.name not in d_defines and op_item.name not in unknown_vars:
                        unknown_vars.append(op_item.name)
                    if unknown_vars:
                        raise SyntaxError(
                            f'Unknown during aspect variable {", ".join(unknown_vars)} in transition:\n{during_aspect_item}')
                    during_operations.append(Operation(var_name=op_item.name, expr=operation_val))
                on_during_aspects.append(OnAspect(
                    stage='during',
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=None,
                    operations=during_operations,
                ))
            elif isinstance(during_aspect_item, dsl_nodes.DuringAspectAbstractFunction):
                on_during_aspects.append(OnAspect(
                    stage='during',
                    aspect=during_aspect_item.aspect,
                    name=during_aspect_item.name,
                    doc=during_aspect_item.doc,
                    operations=[],
                ))

        for transition in current_state.transitions:
            transition.parent = current_state

    _recursive_finish_states(dnode.root_state, current_state=root_state, current_path=())
    return StateMachine(
        defines=d_defines,
        root_state=root_state,
    )
