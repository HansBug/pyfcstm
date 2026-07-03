"""Exception hierarchy for FCSTM bounded model checking queries.

The BMC package keeps query, encoding, and construction failures separate from
parser, solver, and verification-registry concerns.  These exceptions are plain
Python errors with stable names so later parser, binder, engine, and adapter
layers can raise structured failures without importing ``pyfcstm.verify``.

Design contracts:

* Error classes are intentionally thin and stable so parser, binder, engine, and
  adapter layers can share them without coupling to each other.
* Query data-model validation uses these BMC-specific exceptions for structural
  failures, while expression category mix-ups still use normal Python type
  errors where that is more precise.

The module contains:

* :class:`BmcError` - Base class for all BMC-specific errors.
* :class:`InvalidBmcQuery` - Query model or semantic-query validation error.
* :class:`UnsupportedBmcQuery` - Well-formed query that this implementation
  deliberately does not support yet.
* :class:`InvalidBmcEncoding` - Invalid symbolic encoding construction error.
* :class:`InvalidBmcDomain` - Invalid BMC model-domain construction error.
* :class:`BmcBuildError` - General BMC build or preparation error.

Example::

    >>> from pyfcstm.bmc.errors import BmcError, InvalidBmcQuery
    >>> try:
    ...     raise InvalidBmcQuery("bad bound")
    ... except BmcError as err:
    ...     str(err)
    'bad bound'
"""


class BmcError(Exception):
    """Base class for FCSTM BMC failures.

    :param message: Human-readable error message.
    :type message: str

    Example::

        >>> err = BmcError("query failed")
        >>> str(err)
        'query failed'
    """


class InvalidBmcQuery(BmcError):
    """Raised when a BMC query model is structurally invalid.

    :param message: Human-readable validation message.
    :type message: str

    Example::

        >>> err = InvalidBmcQuery("mode must be cold")
        >>> isinstance(err, BmcError)
        True
    """


class UnsupportedBmcQuery(BmcError):
    """Raised when a valid BMC query requests unsupported behavior.

    :param message: Human-readable unsupported-feature message.
    :type message: str

    Example::

        >>> err = UnsupportedBmcQuery("called() is not lowered yet")
        >>> isinstance(err, BmcError)
        True
    """


class InvalidBmcEncoding(BmcError):
    """Raised when symbolic BMC encoding data is internally inconsistent.

    :param message: Human-readable encoding message.
    :type message: str

    Example::

        >>> err = InvalidBmcEncoding("missing frame")
        >>> isinstance(err, BmcError)
        True
    """


class InvalidBmcDomain(BmcError):
    """Raised when BMC domain construction receives invalid data.

    :param message: Human-readable domain message.
    :type message: str

    Example::

        >>> err = InvalidBmcDomain("unknown state")
        >>> isinstance(err, BmcError)
        True
    """


class BmcBuildError(BmcError):
    """Raised when BMC preparation cannot build a usable context.

    :param message: Human-readable build message.
    :type message: str

    Example::

        >>> err = BmcBuildError("model binding failed")
        >>> isinstance(err, BmcError)
        True
    """


__all__ = [
    "BmcError",
    "InvalidBmcQuery",
    "UnsupportedBmcQuery",
    "InvalidBmcEncoding",
    "InvalidBmcDomain",
    "BmcBuildError",
]
