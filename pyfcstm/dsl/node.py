import math
from abc import ABC

__all__ = [
    'ASTNode',
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
]


class ASTNode(ABC):
    pass


class Literal(ASTNode):
    def __init__(self, raw_text: str):
        self.raw_text = raw_text

    @property
    def value(self):
        return self._value()

    def _value(self):
        raise NotImplementedError

    def __str__(self):
        return str(self._value())

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.raw_text}>'


class Integer(Literal):
    def _value(self):
        return int(self.raw_text)


class Float(Literal):
    def _value(self):
        return float(self.raw_text)


class Boolean(Literal):
    def __init__(self, raw_text: str):
        super().__init__(raw_text.lower())

    def _value(self):
        return eval(self.raw_text)


class Constant(Literal):
    __KNOWN_CONSTANTS__ = {
        'e': math.e,
        'pi': math.pi,
        'tau': math.tau,
    }

    def _value(self):
        return self.__KNOWN_CONSTANTS__[self.raw_text]


class Name(ASTNode):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'


class Paren(ASTNode):
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return f'({self.expr})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.expr!r}>'


class UnaryOp(ASTNode):
    __aliases__ = {
        'not': '!',
    }

    def __init__(self, op, expr):
        self.op = self.__aliases__.get(op, op)
        self.expr = expr

    def __str__(self):
        return f'{self.op}{self.expr}'

    def __repr__(self):
        return f'<{self.__class__.__name__} op: {self.op!r}, expr: {self.expr!r}>'


class BinaryOp(ASTNode):
    __aliases__ = {
        'and': '&&',
        'or': '||',
    }

    def __init__(self, expr1, op, expr2):
        self.expr1 = expr1
        self.op = self.__aliases__.get(op, op)
        self.expr2 = expr2

    def __str__(self):
        return f'{self.expr1} {self.op} {self.expr2}'

    def __repr__(self):
        return f'<{self.__class__.__name__}, op: {self.op!r}, expr1: {self.expr1!r}, expr2: {self.expr2!r}>'


class UFunc(ASTNode):
    def __init__(self, func, expr):
        self.func = func
        self.expr = expr

    def __str__(self):
        return f'{self.func}({self.expr})'

    def __repr__(self):
        return f'<{self.__class__.__name__}, func: {self.func!r}, expr: {self.expr!r}>'
