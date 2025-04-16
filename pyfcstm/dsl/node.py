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
    raw_text: str

    @property
    def value(self):
        return self._value()

    def _value(self):
        raise NotImplementedError

    def __str__(self):
        return str(self._value())

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.raw_text}>'


@dataclass
class Integer(Literal):
    def _value(self):
        return int(self.raw_text)


@dataclass
class Float(Literal):
    def _value(self):
        return float(self.raw_text)


@dataclass
class Boolean(Literal):
    def __init__(self, raw_text: str):
        super().__init__(raw_text.lower())

    def _value(self):
        return eval(self.raw_text)


@dataclass
class Constant(Literal):
    __KNOWN_CONSTANTS__ = {
        'e': math.e,
        'pi': math.pi,
        'tau': math.tau,
    }

    def _value(self):
        return self.__KNOWN_CONSTANTS__[self.raw_text]


@dataclass
class Name(Expr):
    name: str

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'


@dataclass
class Paren(Expr):
    expr: Expr

    def __str__(self):
        return f'({self.expr})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.expr!r}>'


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

    def __repr__(self):
        return f'<{self.__class__.__name__} op: {self.op!r}, expr: {self.expr!r}>'


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

    def __repr__(self):
        return f'<{self.__class__.__name__}, op: {self.op!r}, expr1: {self.expr1!r}, expr2: {self.expr2!r}>'


@dataclass
class UFunc(Expr):
    func: str
    expr: Expr

    def __str__(self):
        return f'{self.func}({self.expr})'

    def __repr__(self):
        return f'<{self.__class__.__name__}, func: {self.func!r}, expr: {self.expr!r}>'


@dataclass
class Statement(ASTNode):
    pass


@dataclass
class ConstantDefinition(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} = {self.expr};'

    def __repr__(self):
        return f'<{self.__class__.__name__} name: {self.name!r}, expr: {self.expr!r}>'


@dataclass
class InitialAssignment(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} := {self.expr};'

    def __repr__(self):
        return f'<{self.__class__.__name__} name: {self.name!r}, expr: {self.expr!r}>'


@dataclass
class OperationalAssignment(Statement):
    name: str
    expr: Expr

    def __str__(self):
        return f'{self.name} := {self.expr};'

    def __repr__(self):
        return f'<{self.__class__.__name__} name: {self.name!r}, expr: {self.expr!r}>'


@dataclass
class Condition(ASTNode):
    expr: Expr

    def __str__(self):
        return f'{self.expr}'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.expr!r}>'


@dataclass
class Preamble(ASTNode):
    stats: List[Union[ConstantDefinition, InitialAssignment]]

    def __str__(self):
        return os.linesep.join(map(str, self.stats))

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.stats!r}>'


@dataclass
class Operation(ASTNode):
    stats: List[OperationalAssignment]

    def __str__(self):
        return os.linesep.join(map(str, self.stats))

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.stats!r}>'
