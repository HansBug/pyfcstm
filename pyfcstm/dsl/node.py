import math
from abc import ABC

__all__ = [
    'ASTNode',
    'Literal',
    'Boolean',
    'Integer',
    'Float',
    'Constant',
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
