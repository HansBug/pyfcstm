"""
Operator catalog: the single definition of FCSTM operator and function semantics.

Every operator and math function of the FCSTM expression language is
registered here exactly once.  An entry states how the operation is typed, how
it evaluates on Python values (the runnable reference used by the simulator),
how it is encoded in Z3 (the formal reference used by the solver, verify and
BMC), and which runtime errors it can raise.  Every execution chain in pyfcstm
takes operator semantics from this table instead of keeping its own copy, so a
language ruling changes one entry and every chain follows.

The module contains:

* :class:`ErrorRule` - One named runtime error an operation can raise.
* :class:`OpSpec` - The catalog entry for one operator or function.
* :data:`CATALOG` - Mapping from canonical operator tokens to entries.
* :func:`lookup` - Return the entry for a token, accepting operator aliases.
* :func:`canonical_token` - Normalize an operator alias such as ``and``.

.. note::
   The runnable and formal references agree on integer and boolean values,
   which the differential tests check.  On floating-point values the runnable
   reference uses IEEE double while Z3 uses exact reals; that difference is a
   documented boundary, not a defect.

Example::

    >>> from pyfcstm.semantics.catalog import lookup
    >>> spec = lookup("%")
    >>> spec.concrete(7, -2)
    -1
    >>> [rule.kind for rule in spec.errors]
    ['modulo_by_zero']
"""

import math
import operator
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Type

import z3

__all__ = [
    "BOOL",
    "INT",
    "FLOAT",
    "NUMBER",
    "EAGER",
    "SHORT_AND",
    "SHORT_OR",
    "SHORT_IMPLIES",
    "COMPLEX_POWER_MESSAGE",
    "MATH_DOMAIN_MESSAGE",
    "ErrorRule",
    "OpSpec",
    "CATALOG",
    "canonical_token",
    "lookup",
    "cbrt",
    "cbrt_fallback",
]

#: Result type of a condition.
BOOL = "bool"
#: Result type of an integer-valued expression.
INT = "int"
#: Result type of a float-valued expression.
FLOAT = "float"
#: Result type of an expression whose runtime value is an ``int`` or a
#: ``float`` depending on operand values, such as ``2 ** n``.
NUMBER = "number"

#: Both operands are always evaluated.
EAGER = "eager"
#: The right operand is evaluated only when the left operand is true.
SHORT_AND = "short_and"
#: The right operand is evaluated only when the left operand is false.
SHORT_OR = "short_or"
#: The right operand is evaluated only when the left operand is true; a false
#: left operand makes the implication true without evaluating the right one.
SHORT_IMPLIES = "short_implies"

_ALIASES = {
    "and": "&&",
    "or": "||",
    "not": "!",
    "implies": "=>",
}


@dataclass(frozen=True)
class ErrorRule:
    """
    One named runtime error an operation can raise.

    The runnable reference raises an ordinary Python exception for the error;
    :attr:`raises` lists the exception classes that identify it, so a caller
    can tell which rule fired without parsing messages.  :attr:`defined`
    gives the same rule as a Z3 condition over the symbolic operands: the
    operation raises the error exactly when that condition does not hold.

    :param kind: Stable error code such as ``"division_by_zero"``.
    :type kind: str
    :param raises: Python exception classes the runnable reference raises for
        this error.
    :type raises: Tuple[Type[BaseException], ...]
    :param defined: Function from Z3 operands to the Z3 condition under which
        the operation does not raise this error, or ``None`` when the error has
        no exact-real counterpart (for example floating-point overflow).  It
        returns ``True`` when the operands rule the error out statically.
    :type defined: Optional[Callable[..., z3.BoolRef]]
    :param description: Short human-readable explanation of the error.
    :type description: str
    :param message: Message used instead of the Python exception text when
        callers report the error, or ``None`` to keep the original text.
        Normalizing keeps messages stable across Python versions whose
        wording differs, defaults to ``None``.
    :type message: Optional[str], optional

    Example::

        >>> import z3
        >>> from pyfcstm.semantics.catalog import lookup
        >>> rule = lookup("/").errors[0]
        >>> rule.kind
        'division_by_zero'
        >>> rule.defined(z3.Int("a"), z3.Int("b"))
        b != 0
    """

    kind: str
    raises: Tuple[Type[BaseException], ...]
    defined: Optional[Callable[..., z3.BoolRef]] = None
    description: str = ""
    message: Optional[str] = None


@dataclass(frozen=True)
class OpSpec:
    """
    The catalog entry for one operator or function.

    :param token: Canonical operator token or function name, such as ``"+"``,
        ``"unary-"``, ``"&&"``, ``"?:"`` or ``"sqrt"``.
    :type token: str
    :param kind: Entry kind: ``"unary"``, ``"binary"``, ``"conditional"`` or
        ``"function"``.
    :type kind: str
    :param typing: Function from operand result types (:data:`BOOL`,
        :data:`INT`, :data:`FLOAT`, :data:`NUMBER`) to the result type.
    :type typing: Callable[..., str]
    :param concrete: Runnable reference implementation on Python values.
    :type concrete: Callable[..., object]
    :param symbolic: Z3 implementation on symbolic operands, or ``None`` when
        the operation has no exact Z3 encoding.
    :type symbolic: Optional[Callable[..., object]]
    :param errors: Runtime errors the operation can raise, defaults to ``()``.
    :type errors: Tuple[ErrorRule, ...], optional
    :param control: Evaluation strategy of the operands, one of
        :data:`EAGER`, :data:`SHORT_AND`, :data:`SHORT_OR` and
        :data:`SHORT_IMPLIES`, defaults to :data:`EAGER`.
    :type control: str, optional
    :param unsupported: Reason reported when :attr:`symbolic` is ``None``,
        defaults to ``""``.
    :type unsupported: str, optional

    Example::

        >>> from pyfcstm.semantics.catalog import INT, FLOAT, lookup
        >>> spec = lookup("/")
        >>> spec.typing(INT, INT) == FLOAT
        True
        >>> spec.concrete(7, 2)
        3.5
    """

    token: str
    kind: str
    typing: Callable[..., str]
    concrete: Callable[..., object]
    symbolic: Optional[Callable[..., object]]
    errors: Tuple[ErrorRule, ...] = ()
    control: str = EAGER
    unsupported: str = ""

    @property
    def arity(self) -> int:
        """
        Return the number of operands the entry takes.

        :return: ``1`` for unary operators and functions, ``2`` for binary
            operators and ``3`` for the conditional operator.
        :rtype: int

        Example::

            >>> from pyfcstm.semantics.catalog import lookup
            >>> lookup("?:").arity, lookup("+").arity, lookup("sqrt").arity
            (3, 2, 1)
        """
        return _ARITY[self.kind]

    def error_rule(self, error: BaseException) -> Optional["ErrorRule"]:
        """
        Return the rule that explains an exception raised by :attr:`concrete`.

        :param error: Exception raised by :attr:`concrete`.
        :type error: BaseException
        :return: The first rule whose :attr:`ErrorRule.raises` matches, or
            ``None`` when no rule of this entry explains the exception.
        :rtype: Optional[ErrorRule]

        Example::

            >>> from pyfcstm.semantics.catalog import lookup
            >>> lookup("/").error_rule(ZeroDivisionError("x")).kind
            'division_by_zero'
        """
        for rule in self.errors:
            if isinstance(error, rule.raises):
                return rule
        return None

    def error_kind(self, error: BaseException) -> Optional[str]:
        """
        Return the kind of the rule that explains a raised exception.

        :param error: Exception raised by :attr:`concrete`.
        :type error: BaseException
        :return: The rule kind, or ``None`` when no rule of this entry
            explains the exception.
        :rtype: Optional[str]

        Example::

            >>> from pyfcstm.semantics.catalog import lookup
            >>> spec = lookup("%")
            >>> try:
            ...     spec.concrete(1, 0)
            ... except ZeroDivisionError as err:
            ...     print(spec.error_kind(err))
            modulo_by_zero
        """
        rule = self.error_rule(error)
        return None if rule is None else rule.kind


_ARITY = {"unary": 1, "function": 1, "binary": 2, "conditional": 3}

#: Mapping from canonical operator tokens and function names to entries.
CATALOG: Dict[str, OpSpec] = {}
_REGISTERED: List[OpSpec] = []


def _register(spec: OpSpec) -> None:
    _REGISTERED.append(spec)
    CATALOG[spec.token] = spec


def canonical_token(token: str) -> str:
    """
    Normalize an operator alias to its canonical token.

    :param token: Operator token or alias such as ``"and"`` or ``"implies"``.
    :type token: str
    :return: Canonical token such as ``"&&"`` or ``"=>"``.
    :rtype: str

    Example::

        >>> from pyfcstm.semantics.catalog import canonical_token
        >>> canonical_token("and"), canonical_token("+")
        ('&&', '+')
    """
    return _ALIASES.get(token, token)


def lookup(token: str) -> OpSpec:
    """
    Return the catalog entry for an operator token or function name.

    :param token: Operator token, alias or function name.
    :type token: str
    :return: The catalog entry.
    :rtype: OpSpec
    :raises KeyError: If the token is not part of the FCSTM language.

    Example::

        >>> from pyfcstm.semantics.catalog import lookup
        >>> lookup("or").token
        '||'
    """
    return CATALOG[canonical_token(token)]


# ---------------------------------------------------------------------------
# Result typing
#
# A typing rule receives the operand result types and the operand constants
# (``None`` when an operand is not a literal) and returns the result type.
# ---------------------------------------------------------------------------

def _numeric(types, _constants=()) -> str:
    """Promote numeric operand types the way Python arithmetic does."""
    if FLOAT in types:
        return FLOAT
    if NUMBER in types:
        return NUMBER
    return INT


def _first(types, _constants=()) -> str:
    return types[0]


def _always(result: str) -> Callable[..., str]:
    def typing(_types, _constants=()) -> str:
        return result

    return typing


def _power_type(types, constants=()) -> str:
    # ``int ** int`` is an int for a non-negative exponent and a float for a
    # negative one, so it is statically an int only when the exponent is a
    # non-negative literal.
    if FLOAT in types:
        return FLOAT
    exponent = constants[1] if len(constants) > 1 else None
    if types == (INT, INT) and exponent is not None and exponent >= 0:
        return INT
    return NUMBER


def _branch_type(types, _constants=()) -> str:
    # Python returns whichever branch is selected, so mixed branch types give
    # a value whose type depends on the condition.
    _condition, if_true, if_false = types
    return if_true if if_true == if_false else NUMBER


# ---------------------------------------------------------------------------
# Runnable reference helpers (Python values)
# ---------------------------------------------------------------------------

#: Message of the error raised when ``**`` would produce a complex number.
COMPLEX_POWER_MESSAGE = "negative number cannot be raised to a fractional power"
#: Message reported for every math domain error, whatever wording the running
#: Python version uses for it.
MATH_DOMAIN_MESSAGE = "math domain error"


def _power(base, exponent):
    result = base ** exponent
    if isinstance(result, complex):
        # Python returns a complex number for a negative base raised to a
        # non-integral exponent; FCSTM has no complex values, so the
        # operation is a runtime error at the point it is computed.
        raise ValueError(COMPLEX_POWER_MESSAGE)
    return result


def cbrt_fallback(value):
    """
    Return the real cube root without :func:`math.cbrt`.

    This is the reference implementation on Python versions before 3.11.  It
    refines ``abs(x) ** (1/3)`` with one Newton step and returns the exact
    root of a perfect cube.

    :param value: Number to take the cube root of.
    :type value: Union[int, float]
    :return: The real cube root.
    :rtype: float
    :raises OverflowError: If an integer is too large to convert to float.

    Example::

        >>> from pyfcstm.semantics.catalog import cbrt_fallback
        >>> cbrt_fallback(-8), cbrt_fallback(1000)
        (-2.0, 10.0)
    """
    value = float(value)
    if value == 0.0 or not math.isfinite(value):
        return value
    root = math.copysign(abs(value) ** (1.0 / 3.0), value)
    root -= (root * root * root - value) / (3.0 * root * root)
    nearest = round(root)
    if nearest * nearest * nearest == value:
        return float(nearest)
    return root


#: Real cube root.  ``math.cbrt`` (Python 3.11+) calls the platform C library,
#: so it agrees with generated C code on the same platform; older Pythons use
#: :func:`cbrt_fallback`, which is exact on perfect cubes.
cbrt = getattr(math, "cbrt", cbrt_fallback)


def _sign(value):
    # ``sign(nan)`` is ``-1``: NaN is neither zero nor positive.
    return 0 if value == 0 else (1 if value > 0 else -1)


# ---------------------------------------------------------------------------
# Formal reference helpers (Z3 values)
# ---------------------------------------------------------------------------

def _real(value):
    if z3.is_real(value):
        return value
    if z3.is_int_value(value):
        # An integer numeral becomes a real numeral, which keeps divisions by
        # constants linear for Z3.
        return z3.RealVal(value.as_long())
    return z3.ToReal(value)


def _numeral(value):
    return z3.is_int_value(value) or z3.is_rational_value(value)


def _is_zero_numeral(value) -> bool:
    return _numeral(value) and z3.simplify(value == 0).eq(z3.BoolVal(True))


def _z3_true_division(left, right):
    if z3.is_int(left) and z3.is_int(right):
        return _real(left) / _real(right)
    return left / right


def _z3_floor_mod(left, right):
    if z3.is_int(left) and z3.is_int(right):
        # Z3 ``mod`` is Euclidean (non-negative remainder); Python's ``%``
        # takes the sign of the divisor.
        euclidean = left % right
        return z3.If(
            right > 0,
            euclidean,
            z3.If(euclidean == 0, euclidean, euclidean + right),
        )
    left, right = _real(left), _real(right)
    return left - right * z3.ToReal(z3.ToInt(left / right))


def _z3_power(base, exponent):
    result = base ** exponent
    if (_numeral(base) and not _is_zero_numeral(base)) or (
        _numeral(exponent) and not _is_zero_numeral(exponent)
    ):
        return result
    # Z3 leaves ``0 ** 0`` unspecified while Python defines it as ``1``.
    return z3.If(z3.And(base == 0, exponent == 0), z3.RealVal(1), result)


def _z3_sign(value):
    return z3.If(value == 0, z3.IntVal(0), z3.If(value > 0, z3.IntVal(1), z3.IntVal(-1)))


def _z3_floor(value):
    return value if z3.is_int(value) else z3.ToInt(_real(value))


def _z3_ceil(value):
    return value if z3.is_int(value) else -z3.ToInt(-_real(value))


def _z3_trunc(value):
    if z3.is_int(value):
        return value
    real = _real(value)
    return z3.If(real >= 0, z3.ToInt(real), -z3.ToInt(-real))


def _z3_round(value):
    if z3.is_int(value):
        return value
    real = _real(value)
    floor_value = z3.ToInt(real)
    fraction = real - z3.ToReal(floor_value)
    half = z3.RealVal("1/2")
    return z3.If(
        fraction < half,
        floor_value,
        z3.If(
            fraction > half,
            floor_value + 1,
            z3.If(floor_value % 2 == 0, floor_value, floor_value + 1),
        ),
    )


def _z3_logical(name, builder):
    def apply(left, right):
        if not z3.is_bool(left) or not z3.is_bool(right):
            raise ValueError(
                "Boolean operands required for operator '%s', got %s and %s"
                % (name, left.sort(), right.sort())
            )
        return builder(left, right)

    return apply


def _numeral_value(value):
    if z3.is_int_value(value):
        return value.as_long()
    if z3.is_rational_value(value):
        return value.numerator_as_long() / value.denominator_as_long()
    return None


def _power_defined_at_zero(base, exponent):
    base_value, exponent_value = _numeral_value(base), _numeral_value(exponent)
    if (base_value is not None and base_value != 0) or (
        exponent_value is not None and exponent_value >= 0
    ):
        return z3.BoolVal(True)
    return z3.Or(base != 0, exponent >= 0)


def _power_defined_real(base, exponent):
    if z3.is_int(exponent):
        return z3.BoolVal(True)
    base_value, exponent_value = _numeral_value(base), _numeral_value(exponent)
    if (base_value is not None and base_value >= 0) or (
        exponent_value is not None and float(exponent_value).is_integer()
    ):
        return z3.BoolVal(True)
    return z3.Or(base >= 0, z3.IsInt(exponent))


# ---------------------------------------------------------------------------
# Error rules shared by several entries
# ---------------------------------------------------------------------------

_OVERFLOW = ErrorRule(
    "overflow",
    (OverflowError,),
    description="the result does not fit a Python float",
)
_DIVISION_BY_ZERO = ErrorRule(
    "division_by_zero",
    (ZeroDivisionError,),
    lambda left, right: right != 0,
    "the divisor is zero",
)
_MODULO_BY_ZERO = ErrorRule(
    "modulo_by_zero",
    (ZeroDivisionError,),
    lambda left, right: right != 0,
    "the divisor is zero",
)
_ZERO_NEGATIVE_POWER = ErrorRule(
    "zero_negative_power",
    (ZeroDivisionError,),
    _power_defined_at_zero,
    "zero is raised to a negative power",
)
_COMPLEX_RESULT = ErrorRule(
    "complex_result",
    (ValueError,),
    _power_defined_real,
    "a negative number is raised to a non-integral power",
)
_INVALID_OPERAND = ErrorRule(
    "invalid_operand",
    (TypeError,),
    description="an operand has a type the operation does not accept",
)
_NEGATIVE_SHIFT_COUNT = ErrorRule(
    "negative_shift_count",
    (ValueError,),
    lambda value, count: count >= 0,
    "the shift count is negative",
)
_HUGE_SHIFT = ErrorRule(
    "overflow",
    (OverflowError, MemoryError),
    description="the shifted value cannot be represented",
)


def _math_domain(defined=None, message=MATH_DOMAIN_MESSAGE):
    return ErrorRule(
        "math_domain",
        (ValueError,),
        defined,
        "the argument is outside the function's domain",
        message,
    )


_BITWISE_UNSUPPORTED = (
    "Bitwise operators need a fixed-width integer profile; the default "
    "Python-integer profile has no exact Z3 encoding for them."
)


def _transcendental_unsupported(name):
    if name == "cbrt":
        return (
            "Mathematical function 'cbrt' is not directly supported in Z3. "
            "Consider using uninterpreted functions or polynomial constraints (y^3 = x)."
        )
    if name == "exp":
        family = "Mathematical function"
    elif name.startswith("log"):
        family = "Logarithmic function"
    elif name in ("sinh", "cosh", "tanh", "asinh", "acosh", "atanh"):
        family = "Hyperbolic function"
    else:
        family = "Trigonometric function"
    return (
        "%s '%s' is not directly supported in Z3. "
        "Consider using uninterpreted functions or approximations." % (family, name)
    )


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

for _token, _function, _symbolic in (
    ("+", operator.add, lambda a, b: a + b),
    ("-", operator.sub, lambda a, b: a - b),
    ("*", operator.mul, lambda a, b: a * b),
):
    _register(OpSpec(_token, "binary", _numeric, _function, _symbolic, (_OVERFLOW,)))

_register(
    OpSpec(
        "/",
        "binary",
        _always(FLOAT),
        operator.truediv,
        _z3_true_division,
        (_DIVISION_BY_ZERO, _OVERFLOW),
    )
)
_register(OpSpec("%", "binary", _numeric, operator.mod, _z3_floor_mod, (_MODULO_BY_ZERO,)))
_register(
    OpSpec(
        "**",
        "binary",
        _power_type,
        _power,
        _z3_power,
        (_ZERO_NEGATIVE_POWER, _COMPLEX_RESULT, _OVERFLOW),
    )
)

for _token, _function in (
    ("<", operator.lt),
    ("<=", operator.le),
    (">", operator.gt),
    (">=", operator.ge),
    ("==", operator.eq),
    ("!=", operator.ne),
):
    _register(OpSpec(_token, "binary", _always(BOOL), _function, _function))

_register(
    OpSpec(
        "&&",
        "binary",
        _always(BOOL),
        lambda left, right: bool(left) and bool(right),
        z3.And,
        control=SHORT_AND,
    )
)
_register(
    OpSpec(
        "||",
        "binary",
        _always(BOOL),
        lambda left, right: bool(left) or bool(right),
        z3.Or,
        control=SHORT_OR,
    )
)
_register(
    OpSpec(
        "=>",
        "binary",
        _always(BOOL),
        lambda left, right: (not bool(left)) or bool(right),
        _z3_logical("=>", z3.Implies),
        control=SHORT_IMPLIES,
    )
)
_register(
    OpSpec(
        "xor",
        "binary",
        _always(BOOL),
        lambda left, right: bool(left) != bool(right),
        _z3_logical("xor", z3.Xor),
    )
)
_register(
    OpSpec(
        "iff",
        "binary",
        _always(BOOL),
        lambda left, right: bool(left) == bool(right),
        _z3_logical("iff", lambda left, right: left == right),
    )
)

for _token, _function in (("&", operator.and_), ("|", operator.or_), ("^", operator.xor)):
    _register(
        OpSpec(
            _token,
            "binary",
            _always(INT),
            _function,
            None,
            (_INVALID_OPERAND,),
            unsupported=_BITWISE_UNSUPPORTED,
        )
    )
for _token, _function in (("<<", operator.lshift), (">>", operator.rshift)):
    _register(
        OpSpec(
            _token,
            "binary",
            _always(INT),
            _function,
            None,
            (_INVALID_OPERAND, _NEGATIVE_SHIFT_COUNT, _HUGE_SHIFT),
            unsupported=_BITWISE_UNSUPPORTED,
        )
    )

_register(OpSpec("unary+", "unary", _first, operator.pos, lambda value: value))
_register(OpSpec("unary-", "unary", _first, operator.neg, lambda value: -value))
_register(OpSpec("!", "unary", _always(BOOL), lambda value: not bool(value), z3.Not))

_register(
    OpSpec(
        "?:",
        "conditional",
        _branch_type,
        lambda condition, if_true, if_false: if_true if condition else if_false,
        z3.If,
    )
)

_register(
    OpSpec(
        "abs",
        "function",
        _first,
        abs,
        lambda value: z3.If(value >= 0, value, -value),
        (_OVERFLOW,),
    )
)
_register(OpSpec("sign", "function", _always(INT), _sign, _z3_sign))
for _token, _function, _symbolic in (
    ("floor", math.floor, _z3_floor),
    ("ceil", math.ceil, _z3_ceil),
    ("trunc", math.trunc, _z3_trunc),
    ("round", round, _z3_round),
):
    _register(
        OpSpec(
            _token,
            "function",
            _always(INT),
            _function,
            _symbolic,
            # NaN cannot be converted to an integer; Python's wording for it
            # is stable, so the original message is kept.
            (_math_domain(message=None), _OVERFLOW),
        )
    )
def _z3_sqrt(value):
    if z3.is_bool(value):
        raise NotImplementedError(
            "sqrt requires Real or Int operand, got %s. Cannot convert to Real." % (value.sort(),)
        )
    return z3.Sqrt(_real(value))


_register(
    OpSpec(
        "sqrt",
        "function",
        _always(FLOAT),
        math.sqrt,
        _z3_sqrt,
        (_math_domain(lambda value: value >= 0), _OVERFLOW),
    )
)
for _token, _function in (
    ("sin", math.sin),
    ("cos", math.cos),
    ("tan", math.tan),
    ("asin", math.asin),
    ("acos", math.acos),
    ("atan", math.atan),
    ("sinh", math.sinh),
    ("cosh", math.cosh),
    ("tanh", math.tanh),
    ("asinh", math.asinh),
    ("acosh", math.acosh),
    ("atanh", math.atanh),
    ("cbrt", cbrt),
    ("exp", math.exp),
    ("log", math.log),
    ("log10", math.log10),
    ("log2", math.log2),
    ("log1p", math.log1p),
):
    _register(
        OpSpec(
            _token,
            "function",
            _always(FLOAT),
            _function,
            None,
            (_math_domain(), _OVERFLOW),
            unsupported=_transcendental_unsupported(_token),
        )
    )

del _token, _function, _symbolic
# Every token is registered exactly once; a second entry would silently
# replace the first, so the table is checked when the module loads.
assert len(CATALOG) == len(_REGISTERED), "duplicate operator token in the catalog"
