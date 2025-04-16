import json
import math
import os
from abc import ABC

from dataclasses import dataclass

__all__ = [
    'ASTNode',
    'Expr',
    'Literal',
    'Boolean',
    'Integer',
    'Float',
    'Constant',
    'Name',
    'Paren',
    'UnaryOp',
    'BinaryOp',
    'UFunc',
    'Statement',
    'ConstantDefinition',
    'InitialAssignment',
    'OperationalAssignment',
    'Preamble',
    'Operation',
    'Condition',
]

from typing import List, Union


@dataclass
class ASTNode(ABC):
    pass


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
class Float(Literal):
    def _value(self):
        return float(self.raw)


@dataclass
class Boolean(Literal):
    def __post_init__(self):
        self.raw = self.raw.lower()

    def _value(self):
        return json.loads(self.raw)


@dataclass
class Constant(Literal):
    __KNOWN_CONSTANTS__ = {
        'e': math.e,
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
class OperationalAssignment(Statement):
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
    stats: List[OperationalAssignment]

    def __str__(self):
        return os.linesep.join(map(str, self.stats))
