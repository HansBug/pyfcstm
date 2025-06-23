"""
State Machine DSL AST Module

This module defines the Abstract Syntax Tree (AST) classes for a State Machine Domain Specific Language.
It provides a comprehensive set of classes to represent various elements of state machines including:

- States and transitions
- Expressions and operations
- Conditions and assignments
- Event handling with enter, during, and exit actions

The AST classes enable parsing, manipulation, and generation of state machine definitions
in a structured way, supporting both simple and hierarchical state machines.
"""

import io
import json
import math
import os
from abc import ABC
from dataclasses import dataclass
from textwrap import indent

from hbutils.design import SingletonMark

__all__ = [
    'ASTNode',
    'Identifier',
    'ChainID',
    'Expr',
    'Literal',
    'Boolean',
    'Integer',
    'HexInt',
    'Float',
    'Constant',
    'Name',
    'Paren',
    'UnaryOp',
    'BinaryOp',
    'ConditionalOp',
    'UFunc',
    'Statement',
    'ConstantDefinition',
    'InitialAssignment',
    'DefAssignment',
    'OperationalDeprecatedAssignment',
    'Preamble',
    'Operation',
    'Condition',
    'TransitionDefinition',
    'ForceTransitionDefinition',
    'StateDefinition',
    'OperationAssignment',
    'StateMachineDSLProgram',
    'INIT_STATE',
    'EXIT_STATE',
    'ALL',
    'EnterStatement',
    'EnterOperations',
    'EnterAbstractFunction',
    'ExitStatement',
    'ExitOperations',
    'ExitAbstractFunction',
    'DuringStatement',
    'DuringOperations',
    'DuringAbstractFunction',
    'DuringAspectStatement',
    'DuringAspectOperations',
    'DuringAspectAbstractFunction',
]

from typing import List, Union, Optional


@dataclass
class ASTNode(ABC):
    """
    Abstract base class for all AST nodes in the state machine DSL.

    This class serves as the foundation for all nodes in the Abstract Syntax Tree,
    providing a common type for all elements in the state machine definition.

    :rtype: ASTNode
    """
    pass


@dataclass
class Identifier(ASTNode):
    """
    Abstract base class for identifiers in the state machine DSL.

    Identifiers are used to reference variables, states, and other named elements
    in the state machine definition.

    :rtype: Identifier
    """
    pass


@dataclass
class ChainID(Identifier):
    """
    Represents a chained identifier (e.g., a.b.c) in the state machine DSL.

    :param path: List of string components that make up the chained identifier
    :type path: List[str]

    :rtype: ChainID

    Example::

        >>> chain_id = ChainID(['state1', 'event'])
        >>> str(chain_id)
        'state1.event'
    """
    path: List[str]
    is_absolute: bool = False

    def __str__(self):
        """
        Convert the ChainID to its string representation.

        :return: String representation of the chained identifier
        :rtype: str
        """
        pth = '.'.join(self.path)
        if self.is_absolute:
            pth = f'/{pth}'
        return pth


@dataclass
class Expr(ASTNode):
    """
    Abstract base class for expressions in the state machine DSL.

    Expressions represent computations that produce values, which can be used in
    conditions, assignments, and other contexts within the state machine.

    :rtype: Expr
    """
    pass


@dataclass
class Literal(Expr):
    """
    Base class for literal values in expressions.

    Literal values are constants directly expressed in the code, such as numbers,
    booleans, or predefined constants.

    :param raw: The raw string representation of the literal
    :type raw: str

    :rtype: Literal
    """
    raw: str

    @property
    def value(self):
        """
        Get the actual value of the literal.

        :return: The evaluated value of the literal
        :rtype: Any
        """
        return self._value()

    def _value(self):
        """
        Internal method to evaluate the literal's value.

        :return: The evaluated value of the literal
        :rtype: Any
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover

    def __str__(self):
        """
        Convert the literal to its string representation.

        :return: String representation of the literal's value
        :rtype: str
        """
        return str(self._value())


@dataclass
class Integer(Literal):
    """
    Represents an integer literal in the state machine DSL.

    :param raw: The raw string representation of the integer
    :type raw: str

    :rtype: Integer

    Example::

        >>> int_val = Integer("42")
        >>> int_val.value
        42
    """

    def _value(self):
        """
        Convert the raw string to an integer value.

        :return: The integer value
        :rtype: int
        """
        return int(self.raw)


@dataclass
class HexInt(Literal):
    """
    Represents a hexadecimal integer literal in the state machine DSL.

    :param raw: The raw string representation of the hexadecimal integer (e.g., "0xFF")
    :type raw: str

    :rtype: HexInt

    Example::

        >>> hex_val = HexInt("0xFF")
        >>> hex_val.value
        255
    """

    def _value(self):
        """
        Convert the raw hexadecimal string to an integer value.

        :return: The integer value
        :rtype: int
        """
        return int(self.raw, 16)

    def __str__(self):
        """
        Convert the hexadecimal integer to its string representation.

        :return: Lowercase string representation of the hexadecimal value
        :rtype: str
        """
        return self.raw.lower()


@dataclass
class Float(Literal):
    """
    Represents a floating-point literal in the state machine DSL.

    :param raw: The raw string representation of the float
    :type raw: str

    :rtype: Float

    Example::

        >>> float_val = Float("3.14")
        >>> float_val.value
        3.14
    """

    def _value(self):
        """
        Convert the raw string to a float value.

        :return: The float value
        :rtype: float
        """
        return float(self.raw)

    def __str__(self):
        """
        Convert the float to its string representation.

        :return: String representation of the float
        :rtype: str
        """
        return self.raw


@dataclass
class Boolean(Literal):
    """
    Represents a boolean literal in the state machine DSL.

    :param raw: The raw string representation of the boolean ("true" or "false")
    :type raw: str

    :rtype: Boolean

    Example::

        >>> bool_val = Boolean("true")
        >>> bool_val.value
        True
    """

    def __post_init__(self):
        """
        Normalize the raw value to lowercase after initialization.
        """
        self.raw = self.raw.lower()

    def _value(self):
        """
        Convert the raw string to a boolean value.

        :return: The boolean value
        :rtype: bool
        """
        return json.loads(self.raw)


@dataclass
class Constant(Literal):
    """
    Represents a named mathematical constant in the state machine DSL.

    :param raw: The name of the constant (e.g., "pi", "E")
    :type raw: str

    :rtype: Constant

    Example::

        >>> pi_const = Constant("pi")
        >>> pi_const.value
        3.141592653589793
    """
    __KNOWN_CONSTANTS__ = {
        'E': math.e,
        'pi': math.pi,
        'tau': math.tau,
    }

    def _value(self):
        """
        Get the value of the named constant.

        :return: The constant's value
        :rtype: float
        """
        return self.__KNOWN_CONSTANTS__[self.raw]

    def __str__(self):
        """
        Convert the constant to its string representation.

        :return: The name of the constant
        :rtype: str
        """
        return f'{self.raw}'


@dataclass
class Name(Expr):
    """
    Represents a named reference in the state machine DSL.

    Names are used to reference variables, states, or other named elements.

    :param name: The identifier name
    :type name: str

    :rtype: Name

    Example::

        >>> var_name = Name("counter")
        >>> str(var_name)
        'counter'
    """
    name: str

    def __str__(self):
        """
        Convert the name to its string representation.

        :return: The name as a string
        :rtype: str
        """
        return self.name


@dataclass
class Paren(Expr):
    """
    Represents a parenthesized expression in the state machine DSL.

    Parentheses are used to control the order of operations in expressions.

    :param expr: The expression within the parentheses
    :type expr: Expr

    :rtype: Paren

    Example::

        >>> inner_expr = BinaryOp(Name("a"), "+", Name("b"))
        >>> paren_expr = Paren(inner_expr)
        >>> str(paren_expr)
        '(a + b)'
    """
    expr: Expr

    def __str__(self):
        """
        Convert the parenthesized expression to its string representation.

        :return: The expression surrounded by parentheses
        :rtype: str
        """
        return f'({self.expr})'


@dataclass
class UnaryOp(Expr):
    """
    Represents a unary operation in the state machine DSL.

    Unary operations apply a single operator to an expression.

    :param op: The unary operator (e.g., "!", "not", "-")
    :type op: str
    :param expr: The expression to which the operator is applied
    :type expr: Expr

    :rtype: UnaryOp

    Example::

        >>> not_expr = UnaryOp("not", Name("condition"))
        >>> str(not_expr)
        '!condition'
    """
    __aliases__ = {
        'not': '!',
    }

    op: str
    expr: Expr

    def __post_init__(self):
        """
        Replace any operator aliases with their canonical form.
        """
        self.op = self.__aliases__.get(self.op, self.op)

    def __str__(self):
        """
        Convert the unary operation to its string representation.

        :return: String representation of the unary operation
        :rtype: str
        """
        return f'{self.op}{self.expr}'


@dataclass
class BinaryOp(Expr):
    """
    Represents a binary operation in the state machine DSL.

    Binary operations apply an operator to two expressions.

    :param expr1: The left-hand expression
    :type expr1: Expr
    :param op: The binary operator (e.g., "+", "-", "and", "or")
    :type op: str
    :param expr2: The right-hand expression
    :type expr2: Expr

    :rtype: BinaryOp

    Example::

        >>> add_expr = BinaryOp(Name("a"), "+", Name("b"))
        >>> str(add_expr)
        'a + b'
        >>> and_expr = BinaryOp(Name("x"), "and", Name("y"))
        >>> str(and_expr)
        'x && y'
    """
    __aliases__ = {
        'and': '&&',
        'or': '||',
    }

    expr1: Expr
    op: str
    expr2: Expr

    def __post_init__(self):
        """
        Replace any operator aliases with their canonical form.
        """
        self.op = self.__aliases__.get(self.op, self.op)

    def __str__(self):
        """
        Convert the binary operation to its string representation.

        :return: String representation of the binary operation
        :rtype: str
        """
        return f'{self.expr1} {self.op} {self.expr2}'


@dataclass
class ConditionalOp(Expr):
    """
    Represents a conditional (ternary) operation in the state machine DSL.

    The conditional operation evaluates a condition and returns one of two expressions
    based on whether the condition is true or false.

    :param cond: The condition expression
    :type cond: Expr
    :param value_true: The expression to evaluate if the condition is true
    :type value_true: Expr
    :param value_false: The expression to evaluate if the condition is false
    :type value_false: Expr

    :rtype: ConditionalOp

    Example::

        >>> cond_op = ConditionalOp(Name("x"), Integer("1"), Integer("0"))
        >>> str(cond_op)
        '(x) ? 1 : 0'
    """
    cond: Expr
    value_true: Expr
    value_false: Expr

    def __str__(self):
        """
        Convert the conditional operation to its string representation.

        :return: String representation of the conditional operation
        :rtype: str
        """
        return f'({self.cond}) ? {self.value_true} : {self.value_false}'


@dataclass
class UFunc(Expr):
    """
    Represents a unary function call in the state machine DSL.

    Unary functions apply a named function to a single expression.

    :param func: The function name
    :type func: str
    :param expr: The expression to which the function is applied
    :type expr: Expr

    :rtype: UFunc

    Example::

        >>> func_call = UFunc("abs", Name("x"))
        >>> str(func_call)
        'abs(x)'
    """
    func: str
    expr: Expr

    def __str__(self):
        """
        Convert the function call to its string representation.

        :return: String representation of the function call
        :rtype: str
        """
        return f'{self.func}({self.expr})'


@dataclass
class Statement(ASTNode):
    """
    Abstract base class for statements in the state machine DSL.

    Statements represent actions or declarations in the state machine definition.

    :rtype: Statement
    """
    pass


@dataclass
class ConstantDefinition(Statement):
    """
    Represents a constant definition statement in the state machine DSL.

    :param name: The name of the constant
    :type name: str
    :param expr: The expression defining the constant's value
    :type expr: Expr

    :rtype: ConstantDefinition

    Example::

        >>> const_def = ConstantDefinition("MAX_COUNT", Integer("100"))
        >>> str(const_def)
        'MAX_COUNT = 100;'
    """
    name: str
    expr: Expr

    def __str__(self):
        """
        Convert the constant definition to its string representation.

        :return: String representation of the constant definition
        :rtype: str
        """
        return f'{self.name} = {self.expr};'


@dataclass
class InitialAssignment(Statement):
    """
    Represents an initial assignment statement in the state machine DSL.

    Initial assignments are used to set initial values for variables.

    :param name: The name of the variable
    :type name: str
    :param expr: The expression defining the variable's initial value
    :type expr: Expr

    :rtype: InitialAssignment

    Example::

        >>> init_assign = InitialAssignment("counter", Integer("0"))
        >>> str(init_assign)
        'counter := 0;'
    """
    name: str
    expr: Expr

    def __str__(self):
        """
        Convert the initial assignment to its string representation.

        :return: String representation of the initial assignment
        :rtype: str
        """
        return f'{self.name} := {self.expr};'


@dataclass
class DefAssignment(Statement):
    """
    Represents a definition assignment statement in the state machine DSL.

    Definition assignments are used to declare and initialize typed variables.

    :param name: The name of the variable
    :type name: str
    :param type: The type of the variable
    :type type: str
    :param expr: The expression defining the variable's value
    :type expr: Expr

    :rtype: DefAssignment

    Example::

        >>> def_assign = DefAssignment("counter", "int", Integer("0"))
        >>> str(def_assign)
        'def int counter = 0;'
    """
    name: str
    type: str
    expr: Expr

    def __str__(self):
        """
        Convert the definition assignment to its string representation.

        :return: String representation of the definition assignment
        :rtype: str
        """
        return f'def {self.type} {self.name} = {self.expr};'


@dataclass
class OperationalDeprecatedAssignment(Statement):
    """
    Represents a deprecated form of operational assignment in the state machine DSL.

    :param name: The name of the variable
    :type name: str
    :param expr: The expression defining the variable's value
    :type expr: Expr

    :rtype: OperationalDeprecatedAssignment

    Example::

        >>> op_assign = OperationalDeprecatedAssignment("counter", BinaryOp(Name("counter"), "+", Integer("1")))
        >>> str(op_assign)
        'counter := counter + 1;'
    """
    name: str
    expr: Expr

    def __str__(self):
        """
        Convert the operational deprecated assignment to its string representation.

        :return: String representation of the operational deprecated assignment
        :rtype: str
        """
        return f'{self.name} := {self.expr};'


@dataclass
class Condition(ASTNode):
    """
    Represents a condition in the state machine DSL.

    Conditions are used in transitions and other contexts to determine when actions should occur.

    :param expr: The expression defining the condition
    :type expr: Expr

    :rtype: Condition

    Example::

        >>> cond = Condition(BinaryOp(Name("counter"), ">=", Integer("10")))
        >>> str(cond)
        'counter >= 10'
    """
    expr: Expr

    def __str__(self):
        """
        Convert the condition to its string representation.

        :return: String representation of the condition
        :rtype: str
        """
        return f'{self.expr}'


@dataclass
class Preamble(ASTNode):
    """
    Represents a preamble section in the state machine DSL.

    The preamble contains constant definitions and initial assignments that set up
    the state machine's environment.

    :param stats: List of statements in the preamble
    :type stats: List[Union[ConstantDefinition, InitialAssignment]]

    :rtype: Preamble

    Example::

        >>> const_def = ConstantDefinition("MAX", Integer("100"))
        >>> init_assign = InitialAssignment("counter", Integer("0"))
        >>> preamble = Preamble([const_def, init_assign])
        >>> print(str(preamble))
        MAX = 100;
        counter := 0;
    """
    stats: List[Union[ConstantDefinition, InitialAssignment]]

    def __str__(self):
        """
        Convert the preamble to its string representation.

        :return: String representation of the preamble
        :rtype: str
        """
        return os.linesep.join(map(str, self.stats))


@dataclass
class Operation(ASTNode):
    """
    Represents an operation block in the state machine DSL.

    Operations are sequences of assignments that modify the state machine's variables.

    :param stats: List of operational assignments
    :type stats: List[OperationalDeprecatedAssignment]

    :rtype: Operation

    Example::

        >>> op1 = OperationalDeprecatedAssignment("counter", BinaryOp(Name("counter"), "+", Integer("1")))
        >>> op2 = OperationalDeprecatedAssignment("flag", Boolean("true"))
        >>> operation = Operation([op1, op2])
        >>> print(str(operation))
        counter := counter + 1;
        flag := true;
    """
    stats: List[OperationalDeprecatedAssignment]

    def __str__(self):
        """
        Convert the operation to its string representation.

        :return: String representation of the operation
        :rtype: str
        """
        return os.linesep.join(map(str, self.stats))


class _StateSingletonMark(SingletonMark):
    """
    A singleton marker class for special states in the state machine DSL.

    :param mark: The marker name
    :type mark: str

    :rtype: _StateSingletonMark
    """

    def __repr__(self):
        """
        Convert the singleton mark to its string representation.

        :return: The marker name
        :rtype: str
        """
        return self.mark


INIT_STATE = _StateSingletonMark('INIT_STATE')
"""
Special singleton marker representing the initial state in a state machine.

This is used to define transitions from the initial pseudo-state.
"""

EXIT_STATE = _StateSingletonMark('EXIT_STATE')
"""
Special singleton marker representing the exit state in a state machine.

This is used to define transitions to the final pseudo-state.
"""

ALL = _StateSingletonMark('ALL')
"""
Special singleton marker representing all states in a state machine.

This is used to define transitions or actions that apply to all states.
"""


@dataclass
class TransitionDefinition(ASTNode):
    """
    Represents a transition definition in the state machine DSL.

    Transitions define how the state machine moves from one state to another in response
    to events and conditions.

    :param from_state: The source state name or INIT_STATE singleton
    :type from_state: Union[str, _StateSingletonMark]
    :param to_state: The target state name or EXIT_STATE singleton
    :type to_state: Union[str, _StateSingletonMark]
    :param event_id: Optional event identifier that triggers the transition
    :type event_id: Optional[ChainID]
    :param condition_expr: Optional condition expression that must be true for the transition
    :type condition_expr: Optional[Expr]
    :param post_operations: List of operations to perform after the transition
    :type post_operations: List[OperationAssignment]

    :rtype: TransitionDefinition

    Example::

        >>> # Transition from initial state to "idle" state
        >>> init_trans = TransitionDefinition(INIT_STATE, "idle", None, None, [])
        >>> # Transition from "idle" to "active" on "start" event
        >>> event_trans = TransitionDefinition("idle", "active", ChainID(["idle", "start"]), None, [])
        >>> # Transition with condition and operations
        >>> op = OperationAssignment("counter", Integer("0"))
        >>> cond_trans = TransitionDefinition("active", "idle", None, BinaryOp(Name("counter"), ">", Integer("10")), [op])
    """
    from_state: Union[str, _StateSingletonMark]
    to_state: Union[str, _StateSingletonMark]
    event_id: Optional[ChainID]
    condition_expr: Optional[Expr]
    post_operations: List['OperationAssignment']

    def __str__(self):
        """
        Convert the transition definition to its string representation.

        :return: String representation of the transition definition
        :rtype: str
        """
        with io.StringIO() as sf:
            print('[*]' if self.from_state is INIT_STATE else self.from_state, file=sf, end='')
            print(' -> ', file=sf, end='')
            print('[*]' if self.to_state is EXIT_STATE else self.to_state, file=sf, end='')

            if self.event_id is not None:
                if not self.event_id.is_absolute and \
                        ((self.from_state is INIT_STATE and len(self.event_id.path) == 1) or
                         (self.from_state is not INIT_STATE and len(self.event_id.path) == 2 and
                          self.event_id.path[0] == self.from_state)):
                    print(f' :: {self.event_id.path[-1]}', file=sf, end='')
                else:
                    print(f' : {self.event_id}', file=sf, end='')
            elif self.condition_expr is not None:
                print(f' : if [{self.condition_expr}]', file=sf, end='')

            if len(self.post_operations) > 0:
                print(' effect {', file=sf)
                for operation in self.post_operations:
                    print(f'    {operation}', file=sf)
                print('}', file=sf, end='')
            else:
                print(';', file=sf, end='')

            return sf.getvalue()


@dataclass
class ForceTransitionDefinition(ASTNode):
    """
    Represents a forced transition definition in the state machine DSL.

    Forced transitions override normal transitions and are used for special cases
    like error handling or interrupts.

    :param from_state: The source state name or ALL singleton
    :type from_state: Union[str, _StateSingletonMark]
    :param to_state: The target state name or EXIT_STATE singleton
    :type to_state: Union[str, _StateSingletonMark]
    :param event_id: Optional event identifier that triggers the transition
    :type event_id: Optional[ChainID]
    :param condition_expr: Optional condition expression that must be true for the transition
    :type condition_expr: Optional[Expr]

    :rtype: ForceTransitionDefinition

    Example::

        >>> # Force transition from any state to "error" state
        >>> force_trans = ForceTransitionDefinition(ALL, "error", None, None)
        >>> str(force_trans)
        '! * -> error;'
    """
    from_state: Union[str, _StateSingletonMark]
    to_state: Union[str, _StateSingletonMark]
    event_id: Optional[ChainID]
    condition_expr: Optional[Expr]

    def __str__(self):
        """
        Convert the force transition definition to its string representation.

        :return: String representation of the force transition definition
        :rtype: str
        """
        with io.StringIO() as sf:
            print('! ', file=sf, end='')
            print('*' if self.from_state is ALL else self.from_state, file=sf, end='')
            print(' -> ', file=sf, end='')
            print('[*]' if self.to_state is EXIT_STATE else self.to_state, file=sf, end='')

            if self.event_id is not None:
                if not self.event_id.is_absolute and \
                        ((self.from_state is ALL and len(self.event_id.path) == 1) or
                         (self.from_state is not ALL and len(self.event_id.path) == 2 and
                          self.event_id.path[0] == self.from_state)):
                    print(f' :: {self.event_id.path[-1]}', file=sf, end='')
                else:
                    print(f' : {self.event_id}', file=sf, end='')
            elif self.condition_expr is not None:
                print(f' : if [{self.condition_expr}]', file=sf, end='')

            print(';', file=sf, end='')
            return sf.getvalue()


@dataclass
class StateDefinition(ASTNode):
    """
    Represents a state definition in the state machine DSL.

    States are the fundamental building blocks of state machines, containing
    transitions, substates, and actions to be performed on entry, during, and exit.

    :param name: The name of the state
    :type name: str
    :param substates: List of nested state definitions
    :type substates: List[StateDefinition]
    :param transitions: List of transitions from this state
    :type transitions: List[TransitionDefinition]
    :param enters: List of actions to perform when entering the state
    :type enters: List[EnterStatement]
    :param durings: List of actions to perform while in the state
    :type durings: List[DuringStatement]
    :param exits: List of actions to perform when exiting the state
    :type exits: List[ExitStatement]

    :rtype: StateDefinition

    Example::

        >>> # Simple state with no internal elements
        >>> simple_state = StateDefinition("idle", [], [], [], [], [])
        >>> str(simple_state)
        'state idle;'

        >>> # State with transitions
        >>> trans = TransitionDefinition("idle", "active", ChainID(["idle", "start"]), None, [])
        >>> state_with_trans = StateDefinition("idle", [], [trans], [], [], [])
    """
    name: str
    substates: List['StateDefinition'] = None
    transitions: List[TransitionDefinition] = None
    enters: List['EnterStatement'] = None
    durings: List['DuringStatement'] = None
    exits: List['ExitStatement'] = None
    during_aspects: List['DuringAspectStatement'] = None
    force_transitions: List['ForceTransitionDefinition'] = None

    def __post_init__(self):
        self.substates = self.substates or []
        self.transitions = self.transitions or []
        self.force_transitions = self.force_transitions or []
        self.enters = self.enters or []
        self.durings = self.durings or []
        self.exits = self.exits or []
        self.during_aspects = self.during_aspects or []

    def __str__(self):
        """
        Convert the state definition to its string representation.

        :return: String representation of the state definition
        :rtype: str
        """
        with io.StringIO() as sf:
            if not self.substates and not self.transitions and \
                    not self.enters and not self.durings and not self.exits and not self.during_aspects:
                print(f'state {self.name};', file=sf, end='')
            else:
                print(f'state {self.name} {{', file=sf)
                for enter_item in self.enters:
                    print(indent(str(enter_item), prefix='    '), file=sf)
                for during_item in self.durings:
                    print(indent(str(during_item), prefix='    '), file=sf)
                for exit_item in self.exits:
                    print(indent(str(exit_item), prefix='    '), file=sf)
                for during_aspect_item in self.during_aspects:
                    print(indent(str(during_aspect_item), prefix='    '), file=sf)
                for substate in self.substates:
                    print(indent(str(substate), prefix='    '), file=sf)
                for transition in self.transitions:
                    print(indent(str(transition), prefix='    '), file=sf)
                print(f'}}', file=sf, end='')

            return sf.getvalue()


@dataclass
class OperationAssignment(Statement):
    """
    Represents an operation assignment in the state machine DSL.

    Operation assignments are used to modify variables during transitions or state actions.

    :param name: The name of the variable
    :type name: str
    :param expr: The expression defining the new value
    :type expr: Expr

    :rtype: OperationAssignment

    Example::

        >>> op_assign = OperationAssignment("counter", BinaryOp(Name("counter"), "+", Integer("1")))
        >>> str(op_assign)
        'counter = counter + 1;'
    """
    name: str
    expr: Expr

    def __str__(self):
        """
        Convert the operation assignment to its string representation.

        :return: String representation of the operation assignment
        :rtype: str
        """
        return f'{self.name} = {self.expr};'


@dataclass
class StateMachineDSLProgram(ASTNode):
    """
    Represents a complete state machine DSL program.

    A program consists of variable definitions and a root state that contains
    the entire state machine hierarchy.

    :param definitions: List of variable definitions
    :type definitions: List[DefAssignment]
    :param root_state: The root state of the state machine
    :type root_state: StateDefinition

    :rtype: StateMachineDSLProgram

    Example::

        >>> def_var = DefAssignment("counter", "int", Integer("0"))
        >>> root = StateDefinition("root", [], [], [], [], [])
        >>> program = StateMachineDSLProgram([def_var], root)
        >>> print(str(program))
        def int counter = 0;
        state root;
    """
    definitions: List[DefAssignment]
    root_state: StateDefinition

    def __str__(self):
        """
        Convert the state machine program to its string representation.

        :return: String representation of the state machine program
        :rtype: str
        """
        with io.StringIO() as f:
            for definition in self.definitions:
                print(definition, file=f)
            print(self.root_state, file=f, end='')
            return f.getvalue()


@dataclass
class EnterStatement(ASTNode):
    """
    Abstract base class for enter statements in the state machine DSL.

    Enter statements define actions to be performed when entering a state.

    :rtype: EnterStatement
    """
    pass


@dataclass
class EnterOperations(EnterStatement):
    """
    Represents a block of operations to perform when entering a state.

    :param operations: List of operation assignments
    :type operations: List[OperationAssignment]

    :rtype: EnterOperations

    Example::

        >>> op = OperationAssignment("counter", Integer("0"))
        >>> enter_ops = EnterOperations([op])
        >>> print(str(enter_ops))
        enter {
            counter = 0;
        }
    """
    operations: List[OperationAssignment]
    name: Optional[str] = None

    def __str__(self):
        """
        Convert the enter operations to their string representation.

        :return: String representation of the enter operations
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'enter {self.name} {{', file=f)
            else:
                print(f'enter {{', file=f)
            for operation in self.operations:
                print(f'    {operation}', file=f)
            print('}', file=f, end='')
            return f.getvalue()


@dataclass
class EnterAbstractFunction(EnterStatement):
    """
    Represents an abstract function to call when entering a state.

    Abstract functions are placeholders for implementation-specific behavior.

    :param name: Optional name of the function
    :type name: Optional[str]
    :param doc: Optional documentation for the function
    :type doc: Optional[str]

    :rtype: EnterAbstractFunction

    Example::

        >>> enter_func = EnterAbstractFunction("initState", "Initialize the state")
        >>> print(str(enter_func))
        enter abstract initState /*
            Initialize the state
        */
    """
    name: Optional[str]
    doc: Optional[str]

    def __str__(self):
        """
        Convert the enter abstract function to its string representation.

        :return: String representation of the enter abstract function
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'enter abstract {self.name}', file=f, end='')
            else:
                print(f'enter abstract', file=f, end='')

            if self.doc is not None:
                print(' /*', file=f)
                print(indent(self.doc, prefix='    '), file=f)
                print('*/', file=f, end='')
            else:
                print(';', file=f, end='')

            return f.getvalue()


@dataclass
class ExitStatement(ASTNode):
    """
    Abstract base class for exit statements in the state machine DSL.

    Exit statements define actions to be performed when exiting a state.

    :rtype: ExitStatement
    """
    pass


@dataclass
class ExitOperations(ExitStatement):
    """
    Represents a block of operations to perform when exiting a state.

    :param operations: List of operation assignments
    :type operations: List[OperationAssignment]

    :rtype: ExitOperations

    Example::

        >>> op = OperationAssignment("active", Boolean("false"))
        >>> exit_ops = ExitOperations([op])
        >>> print(str(exit_ops))
        exit {
            active = false;
        }
    """
    operations: List[OperationAssignment]
    name: Optional[str] = None

    def __str__(self):
        """
        Convert the exit operations to their string representation.

        :return: String representation of the exit operations
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'exit {self.name} {{', file=f)
            else:
                print(f'exit {{', file=f)

            for operation in self.operations:
                print(f'    {operation}', file=f)
            print('}', file=f, end='')
            return f.getvalue()


@dataclass
class ExitAbstractFunction(ExitStatement):
    """
    Represents an abstract function to call when exiting a state.

    Abstract functions are placeholders for implementation-specific behavior.

    :param name: Optional name of the function
    :type name: Optional[str]
    :param doc: Optional documentation for the function
    :type doc: Optional[str]

    :rtype: ExitAbstractFunction

    Example::

        >>> exit_func = ExitAbstractFunction("cleanupState", "Clean up resources")
        >>> print(str(exit_func))
        exit abstract cleanupState /*
            Clean up resources
        */
    """
    name: Optional[str]
    doc: Optional[str]

    def __str__(self):
        """
        Convert the exit abstract function to its string representation.

        :return: String representation of the exit abstract function
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'exit abstract {self.name}', file=f, end='')
            else:
                print(f'exit abstract', file=f, end='')

            if self.doc is not None:
                print(' /*', file=f)
                print(indent(self.doc, prefix='    '), file=f)
                print('*/', file=f, end='')
            else:
                print(';', file=f, end='')

            return f.getvalue()


@dataclass
class DuringStatement(ASTNode):
    """
    Abstract base class for during statements in the state machine DSL.

    During statements define actions to be performed while in a state.

    :rtype: DuringStatement
    """
    pass


@dataclass
class DuringOperations(DuringStatement):
    """
    Represents a block of operations to perform while in a state.

    :param aspect: Optional aspect name (e.g., "entry", "do", "exit")
    :type aspect: Optional[str]
    :param operations: List of operation assignments
    :type operations: List[OperationAssignment]

    :rtype: DuringOperations

    Example::

        >>> op = OperationAssignment("counter", BinaryOp(Name("counter"), "+", Integer("1")))
        >>> during_ops = DuringOperations("do", [op])
        >>> print(str(during_ops))
        during do {
            counter = counter + 1;
        }
    """
    aspect: Optional[str]
    operations: List[OperationAssignment]
    name: Optional[str] = None

    def __str__(self):
        """
        Convert the during operations to their string representation.

        :return: String representation of the during operations
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                if self.aspect:
                    print(f'during {self.aspect} {self.name} {{', file=f)
                else:
                    print(f'during {self.name} {{', file=f)
            else:
                if self.aspect:
                    print(f'during {self.aspect} {{', file=f)
                else:
                    print(f'during {{', file=f)
            for operation in self.operations:
                print(f'    {operation}', file=f)
            print('}', file=f, end='')
            return f.getvalue()


@dataclass
class DuringAbstractFunction(DuringStatement):
    """
    Represents an abstract function to call while in a state.

    Abstract functions are placeholders for implementation-specific behavior.

    :param name: Optional name of the function
    :type name: Optional[str]
    :param aspect: Optional aspect name (e.g., "entry", "do", "exit")
    :type aspect: Optional[str]
    :param doc: Optional documentation for the function
    :type doc: Optional[str]

    :rtype: DuringAbstractFunction

    Example::

        >>> during_func = DuringAbstractFunction("processData", "do", "Process incoming data")
        >>> print(str(during_func))
        during do abstract processData /*
            Process incoming data
        */
    """
    name: Optional[str]
    aspect: Optional[str]
    doc: Optional[str]

    def __str__(self):
        """
        Convert the during abstract function to its string representation.

        :return: String representation of the during abstract function
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                if self.aspect:
                    print(f'during {self.aspect} abstract {self.name}', file=f, end='')
                else:
                    print(f'during abstract {self.name}', file=f, end='')
            else:
                if self.aspect:
                    print(f'during {self.aspect} abstract', file=f, end='')
                else:
                    print(f'during abstract', file=f, end='')

            if self.doc is not None:
                print(' /*', file=f)
                print(indent(self.doc, prefix='    '), file=f)
                print('*/', file=f, end='')
            else:
                print(';', file=f, end='')

            return f.getvalue()


@dataclass
class DuringAspectStatement(ASTNode):
    """
    Abstract base class for during aspect statements in the state machine DSL.

    During aspect statements define aspect-specific actions to be performed while in a state.

    :rtype: DuringAspectStatement
    """
    pass


@dataclass
class DuringAspectOperations(DuringAspectStatement):
    """
    Represents a block of aspect-specific operations to perform while in a state.

    :param aspect: The aspect name (e.g., "entry", "do", "exit")
    :type aspect: str
    :param operations: List of operation assignments
    :type operations: List[OperationAssignment]
    :param name: Optional name for the operation block
    :type name: Optional[str]

    :rtype: DuringAspectOperations

    Example::

        >>> op = OperationAssignment("counter", BinaryOp(Name("counter"), "+", Integer("1")))
        >>> during_ops = DuringAspectOperations("before", [op])
        >>> print(str(during_ops))
        >> during before {
            counter = counter + 1;
        }
    """
    aspect: str
    operations: List[OperationAssignment]
    name: Optional[str] = None

    def __str__(self):
        """
        Convert the during aspect operations to their string representation.

        :return: String representation of the during aspect operations
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'>> during {self.aspect} {self.name} {{', file=f)
            else:
                print(f'>> during {self.aspect} {{', file=f)
            for operation in self.operations:
                print(f'    {operation}', file=f)
            print('}', file=f, end='')
            return f.getvalue()


@dataclass
class DuringAspectAbstractFunction(DuringAspectStatement):
    """
    Represents an abstract function to call for a specific aspect while in a state.

    Abstract functions are placeholders for implementation-specific behavior.

    :param name: Optional name of the function
    :type name: Optional[str]
    :param aspect: The aspect name (e.g., "before", "after")
    :type aspect: str
    :param doc: Optional documentation for the function
    :type doc: Optional[str]

    :rtype: DuringAspectAbstractFunction

    Example::

        >>> during_func = DuringAspectAbstractFunction("processData", "before", "Process incoming data")
        >>> print(str(during_func))
        >> during before abstract processData /*
            Process incoming data
        */
    """
    name: Optional[str]
    aspect: str
    doc: Optional[str]

    def __str__(self):
        """
        Convert the during aspect abstract function to its string representation.

        :return: String representation of the during aspect abstract function
        :rtype: str
        """
        with io.StringIO() as f:
            if self.name:
                print(f'>> during {self.aspect} abstract {self.name}', file=f, end='')
            else:
                print(f'>> during {self.aspect} abstract', file=f, end='')

            if self.doc is not None:
                print(' /*', file=f)
                print(indent(self.doc, prefix='    '), file=f)
                print('*/', file=f, end='')
            else:
                print(';', file=f, end='')

            return f.getvalue()
