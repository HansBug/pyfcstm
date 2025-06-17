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
    'StateDefinition',
    'OperationAssignment',
    'StateMachineDSLProgram',
    'INIT_STATE',
    'EXIT_STATE',
    'EnterStatement',
    'EnterOperations',
    'EnterAbstractFunction',
]

from typing import List, Union, Optional


@dataclass
class ASTNode(ABC):
    pass


@dataclass
class Identifier(ASTNode):
    pass


@dataclass
class ChainID(Identifier):
    path: List[str]

    def __str__(self):
        return '.'.join(self.path)


@dataclass
class Expr(ASTNode):
    pass


@dataclass
class Literal(Expr):
    raw: str

    @property
    def value(self):
        return self._value()

    def _value(self):
        raise NotImplementedError  # pragma: no cover

    def __str__(self):
        return str(self._value())


@dataclass
class Integer(Literal):
    def _value(self):
        return int(self.raw)


@dataclass
class HexInt(Literal):
    def _value(self):
        return int(self.raw, 16)

    def __str__(self):
        return self.raw.lower()


@dataclass
class Float(Literal):
    def _value(self):
        return float(self.raw)

    def __str__(self):
        return self.raw


@dataclass
class Boolean(Literal):
    def __post_init__(self):
        self.raw = self.raw.lower()

    def _value(self):
        return json.loads(self.raw)


@dataclass
class Constant(Literal):
    __KNOWN_CONSTANTS__ = {
        'E': math.e,
        'pi': math.pi,
        'tau': math.tau,
    }

    def _value(self):
        return self.__KNOWN_CONSTANTS__[self.raw]

    def __str__(self):
        return f'{self.raw}'


@dataclass
class Name(Expr):
    name: str

    def __str__(self):
        return self.name


@dataclass
class Paren(Expr):
    expr: Expr

    def __str__(self):
        return f'({self.expr})'


@dataclass
class UnaryOp(Expr):
    __aliases__ = {
        'not': '!',
    }

    op: str
    expr: Expr

    def __post_init__(self):
        self.op = self.__aliases__.get(self.op, self.op)

    def __str__(self):
        return f'{self.op}{self.expr}'


@dataclass
class BinaryOp(Expr):
    __aliases__ = {
        'and': '&&',
        'or': '||',
    }

    expr1: Expr
    op: str
    expr2: Expr

    def __post_init__(self):
        self.op = self.__aliases__.get(self.op, self.op)

    def __str__(self):
        return f'{self.expr1} {self.op} {self.expr2}'


@dataclass
class ConditionalOp(Expr):
    cond: Expr
    value_true: Expr
    value_false: Expr

    def __str__(self):
        return f'({self.cond}) ? {self.value_true} : {self.value_false}'


@dataclass
class UFunc(Expr):
    func: str
    expr: Expr

    def __str__(self):
        return f'{self.func}({self.expr})'


@dataclass
class Statement(ASTNode):
    pass


@dataclass
class ConstantDefinition(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} = {self.expr};'


@dataclass
class InitialAssignment(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} := {self.expr};'


@dataclass
class DefAssignment(Statement):
    name: str
    type: str
    expr: Expr

    def __str__(self):
        return f'def {self.type} {self.name} = {self.expr};'


@dataclass
class OperationalDeprecatedAssignment(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} := {self.expr};'


@dataclass
class Condition(ASTNode):
    expr: Expr

    def __str__(self):
        return f'{self.expr}'


@dataclass
class Preamble(ASTNode):
    stats: List[Union[ConstantDefinition, InitialAssignment]]

    def __str__(self):
        return os.linesep.join(map(str, self.stats))


@dataclass
class Operation(ASTNode):
    stats: List[OperationalDeprecatedAssignment]

    def __str__(self):
        return os.linesep.join(map(str, self.stats))


class _StateSingletonMark(SingletonMark):
    def __repr__(self):
        return self.mark


INIT_STATE = _StateSingletonMark('INIT_STATE')
EXIT_STATE = _StateSingletonMark('EXIT_STATE')


@dataclass
class TransitionDefinition(ASTNode):
    from_state: Union[str, _StateSingletonMark]
    to_state: Union[str, _StateSingletonMark]
    event_id: Optional[ChainID]
    condition_expr: Optional[Expr]
    post_operations: List['OperationAssignment']

    def __str__(self):
        with io.StringIO() as sf:
            print('[*]' if self.from_state is INIT_STATE else self.from_state, file=sf, end='')
            print(' -> ', file=sf, end='')
            print('[*]' if self.to_state is EXIT_STATE else self.to_state, file=sf, end='')

            if self.event_id is not None:
                if (self.from_state is INIT_STATE and len(self.event_id.path) == 1) or \
                        (self.from_state is not INIT_STATE and len(self.event_id.path) == 2 and
                         self.event_id.path[0] == self.from_state):
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
class StateDefinition(ASTNode):
    name: str
    substates: List['StateDefinition']
    transitions: List[TransitionDefinition]

    def __str__(self):
        with io.StringIO() as sf:
            if not self.substates and not self.transitions:
                print(f'state {self.name};', file=sf, end='')
            else:
                print(f'state {self.name} {{', file=sf)
                for substate in self.substates:
                    print(indent(str(substate), prefix='    '), file=sf)
                for transition in self.transitions:
                    print(indent(str(transition), prefix='    '), file=sf)
                print(f'}}', file=sf, end='')

            return sf.getvalue()


@dataclass
class OperationAssignment(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} = {self.expr};'


@dataclass
class StateMachineDSLProgram(ASTNode):
    definitions: List[DefAssignment]
    root_state: StateDefinition

    def __str__(self):
        with io.StringIO() as f:
            for definition in self.definitions:
                print(definition, file=f)
            print(self.root_state, file=f, end='')
            return f.getvalue()


@dataclass
class EnterStatement(ASTNode):
    pass


@dataclass
class EnterOperations(EnterStatement):
    operations: List[OperationAssignment]

    def __str__(self):
        with io.StringIO() as f:
            print('enter {', file=f)
            for operation in self.operations:
                print(f'    {operation}', file=f)
            print('}', file=f, end='')
            return f.getvalue()


@dataclass
class EnterAbstractFunction(EnterStatement):
    name: Optional[str]
    doc: Optional[str]

    def __str__(self):
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
