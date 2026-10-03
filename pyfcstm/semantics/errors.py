"""
Structured runtime errors of FCSTM execution.

The module contains:

* :class:`EvaluationError` - A runtime error raised by an operation.
* :class:`WritebackError` - A value rejected by persistent writeback.

Example::

    >>> from pyfcstm.semantics.errors import WritebackError
    >>> issubclass(WritebackError, ValueError)
    True
"""

from typing import Optional

__all__ = [
    "EvaluationError",
    "WritebackError",
]


class EvaluationError(Exception):
    """
    A runtime error raised by an operation during concrete execution.

    :param kind: Catalog error kind such as ``"division_by_zero"``.
    :type kind: str
    :param error: Exception reported to callers.  It is the Python exception
        raised by the operation, or a replacement carrying the catalog's
        normalized message.
    :type error: BaseException
    :param node: IR node of the failing operation.
    :type node: pyfcstm.semantics.ir.Expr

    :ivar kind: Catalog error kind.
    :vartype kind: str
    :ivar error: Exception reported to callers.
    :vartype error: BaseException
    :ivar node: IR node of the failing operation.
    :vartype node: pyfcstm.semantics.ir.Expr
    :ivar statement: Innermost IR statement or branch being executed when the
        error was raised, or ``None`` outside statement execution.
    :vartype statement: Optional[pyfcstm.semantics.ir.Node]
    :ivar role: ``"value"`` when the error came from an assigned expression,
        ``"test"`` when it came from a branch condition, else ``None``.
    :vartype role: Optional[str]

    Example::

        >>> from pyfcstm.semantics.errors import EvaluationError
        >>> err = EvaluationError("division_by_zero", ZeroDivisionError("division by zero"), None)
        >>> str(err)
        'division by zero'
    """

    def __init__(self, kind: str, error: BaseException, node: Optional[object]):
        super().__init__(str(error))
        self.kind = kind
        self.error = error
        self.node = node
        self.statement = None
        self.role = None


class WritebackError(ValueError):
    """
    A value rejected by persistent writeback.

    :param kind: Rejection kind: ``"writeback_type"``,
        ``"writeback_non_finite"``, ``"writeback_float_range"`` or
        ``"writeback_non_integral"``.
    :type kind: str
    :param message: Human-readable message.
    :type message: str

    :ivar kind: Rejection kind.
    :vartype kind: str

    Example::

        >>> from pyfcstm.semantics.errors import WritebackError
        >>> WritebackError("writeback_non_integral", "bad").kind
        'writeback_non_integral'
    """

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
