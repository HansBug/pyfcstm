"""
Fixed-width integer types matching C/C++/Java and Z3 BitVec behavior.

This module provides immutable fixed-width integer types (int8, int16, int32, int64,
uint8, uint16, uint32, uint64) that wrap ctypes and replicate the overflow/underflow
behavior of C/C++/Java integer arithmetic. All operations are designed to align
exactly with Z3 ``BitVec`` semantics for use alongside the constraint solver.

All arithmetic operations follow C/C++/Java and Z3 BitVec semantics including:

* Two's complement representation for signed integers
* Wraparound on overflow/underflow
* Bitwise operations
* Implicit conversion when operating with Python int

**Z3 BitVec operation correspondence**:

+---------------------+----------------------+------------------------------------------+
| Python operator     | Z3 equivalent        | Notes                                    |
+=====================+======================+==========================================+
| ``//``, ``/`` (s)   | ``/`` (SDiv/bvsdiv)  | Truncate toward zero; INT_MIN//-1 wraps  |
+---------------------+----------------------+------------------------------------------+
| ``%`` (signed)      | ``SRem`` (bvsrem)    | Sign follows *dividend*; differs from    |
|                     |                      | Z3's ``%`` (bvsmod, sign follows divisor)|
+---------------------+----------------------+------------------------------------------+
| ``//``, ``/`` (u)   | ``UDiv`` (bvudiv)    | Standard unsigned division               |
+---------------------+----------------------+------------------------------------------+
| ``%`` (unsigned)    | ``URem`` (bvurem)    | Standard unsigned remainder; differs     |
|                     |                      | from Z3's ``%`` (bvsmod)                 |
+---------------------+----------------------+------------------------------------------+
| ``>>`` (signed)     | ``>>`` (bvashr)      | Arithmetic: fills with sign bit          |
+---------------------+----------------------+------------------------------------------+
| ``>>`` (unsigned)   | ``LShR`` (bvlshr)    | Logical: fills with 0                    |
+---------------------+----------------------+------------------------------------------+
| ``<<``              | ``<<`` (bvshl)       | Shift >= bit-width yields 0              |
+---------------------+----------------------+------------------------------------------+
| ``~``               | ``~``                | Bitwise NOT (complement all bits)        |
+---------------------+----------------------+------------------------------------------+
| Unary ``-``         | Unary ``-``          | Two's complement; ``-INT_MIN == INT_MIN``|
+---------------------+----------------------+------------------------------------------+

**Shift amount convention**: When a :class:`_FixedInt` value is used as the shift
amount, its bit pattern is interpreted as unsigned (matching Z3 ``bvshl``/``bvashr``/
``bvlshr``). For example, ``Int8(1) << Int8(-1)`` shifts by 255 positions (the unsigned
value of the 8-bit pattern ``0xFF``), yielding ``Int8(0)``. Plain Python :class:`int`
shift amounts retain standard Python behaviour (negative values raise :exc:`ValueError`).

Example::

    >>> from pyfcstm.utils.fixed import Int8, UInt8
    >>> x = Int8(127)
    >>> x + 1
    Int8(-128)
    >>> y = UInt8(255)
    >>> y + 1
    UInt8(0)
"""

import ctypes
from typing import Union

__all__ = [
    'Int8', 'Int16', 'Int32', 'Int64',
    'UInt8', 'UInt16', 'UInt32', 'UInt64',
]


class _FixedInt:
    """
    Base class for fixed-width integer types.

    This class wraps ctypes integer types to provide immutable fixed-width integers
    with C/C++/Java-style overflow behavior. All subclasses must define ``_ctype``
    and ``_type_name`` class attributes.

    :ivar _value: The wrapped ctypes value
    :vartype _value: ctypes integer type
    """

    _ctype = None
    _type_name = None
    _is_signed: bool = False

    def __init__(self, value: Union[int, '_FixedInt'] = 0):
        """
        Initialize a fixed-width integer.

        :param value: Initial value, defaults to ``0``
        :type value: Union[int, _FixedInt], optional
        """
        if isinstance(value, _FixedInt):
            value = int(value)
        self._value = self._ctype(value)

    def __int__(self) -> int:
        """
        Convert to Python int.

        :return: Integer value
        :rtype: int
        """
        return self._value.value

    def __index__(self) -> int:
        """
        Support for bin(), hex(), oct() and indexing.

        :return: Integer value
        :rtype: int
        """
        return self._value.value

    def __repr__(self) -> str:
        """
        Return string representation.

        :return: String like ``Int8(42)``
        :rtype: str
        """
        return f"{self._type_name}({int(self)})"

    def __bytes__(self) -> bytes:
        """
        Convert to bytes representation.

        :return: Bytes in native byte order
        :rtype: bytes
        """
        return bytes(self._value)

    @classmethod
    def from_bytes(cls, b: bytes, byteorder: str = 'little') -> '_FixedInt':
        """
        Create instance from bytes.

        :param b: Byte sequence
        :type b: bytes
        :param byteorder: Byte order ('little' or 'big'), defaults to ``'little'``
        :type byteorder: str, optional
        :return: New fixed-width integer instance
        :rtype: _FixedInt
        """
        value = int.from_bytes(b, byteorder=byteorder, signed=cls._is_signed)
        return cls(value)

    def __hash__(self) -> int:
        """
        Hash value consistent with equality.

        Returns the same hash as the underlying Python ``int`` value so that
        the invariant ``a == b ⟹ hash(a) == hash(b)`` is preserved when
        comparing against Python ``int`` objects or other :class:`_FixedInt`
        instances with the same integer value.

        :return: Hash value
        :rtype: int
        """
        return hash(int(self))

    def __eq__(self, other) -> bool:
        """
        Equality comparison.

        :param other: Value to compare
        :return: ``True`` if equal
        :rtype: bool
        """
        if isinstance(other, _FixedInt):
            return int(self) == int(other)
        elif isinstance(other, int):
            return int(self) == other
        return NotImplemented

    def __ne__(self, other) -> bool:
        """
        Inequality comparison.

        :param other: Value to compare
        :return: ``True`` if not equal
        :rtype: bool
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other) -> bool:
        """
        Less than comparison.

        :param other: Value to compare
        :return: ``True`` if less than
        :rtype: bool
        """
        if isinstance(other, _FixedInt):
            return int(self) < int(other)
        elif isinstance(other, int):
            return int(self) < other
        return NotImplemented

    def __le__(self, other) -> bool:
        """
        Less than or equal comparison.

        :param other: Value to compare
        :return: ``True`` if less than or equal
        :rtype: bool
        """
        if isinstance(other, _FixedInt):
            return int(self) <= int(other)
        elif isinstance(other, int):
            return int(self) <= other
        return NotImplemented

    def __gt__(self, other) -> bool:
        """
        Greater than comparison.

        :param other: Value to compare
        :return: ``True`` if greater than
        :rtype: bool
        """
        if isinstance(other, _FixedInt):
            return int(self) > int(other)
        elif isinstance(other, int):
            return int(self) > other
        return NotImplemented

    def __ge__(self, other) -> bool:
        """
        Greater than or equal comparison.

        :param other: Value to compare
        :return: ``True`` if greater than or equal
        :rtype: bool
        """
        if isinstance(other, _FixedInt):
            return int(self) >= int(other)
        elif isinstance(other, int):
            return int(self) >= other
        return NotImplemented

    def __add__(self, other) -> '_FixedInt':
        """
        Addition with wraparound.

        :param other: Value to add
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) + int(other))
        return NotImplemented

    def __radd__(self, other) -> '_FixedInt':
        """
        Right-hand addition.

        :param other: Value to add
        :return: New instance with result
        :rtype: _FixedInt
        """
        return self.__add__(other)

    def __sub__(self, other) -> '_FixedInt':
        """
        Subtraction with wraparound.

        :param other: Value to subtract
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) - int(other))
        return NotImplemented

    def __rsub__(self, other) -> '_FixedInt':
        """
        Right-hand subtraction.

        :param other: Value to subtract from
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(other) - int(self))
        return NotImplemented

    def __mul__(self, other) -> '_FixedInt':
        """
        Multiplication with wraparound.

        :param other: Value to multiply
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) * int(other))
        return NotImplemented

    def __rmul__(self, other) -> '_FixedInt':
        """
        Right-hand multiplication.

        :param other: Value to multiply
        :return: New instance with result
        :rtype: _FixedInt
        """
        return self.__mul__(other)

    def __floordiv__(self, other) -> '_FixedInt':
        """
        Integer division truncating toward zero (C/C++/Java and Z3 ``SDiv`` semantics).

        Unlike Python's ``//`` which rounds toward negative infinity, this
        truncates toward zero to match C integer division semantics. For signed
        types this is equivalent to Z3's ``/`` operator (``bvsdiv``); for unsigned
        types it is equivalent to Z3's ``UDiv`` (``bvudiv``).

        **Overflow**: dividing ``INT_MIN`` by ``-1`` cannot be represented and wraps
        around to ``INT_MIN`` — the same behaviour as Z3's ``bvsdiv``.  For example,
        ``Int8(-128) // Int8(-1) == Int8(-128)``.

        :param other: Divisor
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero

        Example::

            >>> Int8(-7) // Int8(2)
            Int8(-3)
            >>> Int8(-128) // Int8(-1)
            Int8(-128)
        """
        if isinstance(other, (_FixedInt, int)):
            divisor = int(other)
            if divisor == 0:
                raise ZeroDivisionError("division by zero")
            dividend = int(self)
            # C-style division: truncate toward zero using pure integer arithmetic
            q, r = divmod(dividend, divisor)
            if r != 0 and (dividend < 0) != (divisor < 0):
                q += 1
            return type(self)(q)
        return NotImplemented

    def __rfloordiv__(self, other) -> '_FixedInt':
        """
        Right-hand floor division.

        :param other: Dividend
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero
        """
        if isinstance(other, (_FixedInt, int)):
            dividend = int(other)
            divisor = int(self)
            if divisor == 0:
                raise ZeroDivisionError("division by zero")
            q, r = divmod(dividend, divisor)
            if r != 0 and (dividend < 0) != (divisor < 0):
                q += 1
            return type(self)(q)
        return NotImplemented

    def __truediv__(self, other) -> '_FixedInt':
        """
        True division (delegates to floor division for integer types).

        :param other: Divisor
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero
        """
        return self.__floordiv__(other)

    def __rtruediv__(self, other) -> '_FixedInt':
        """
        Right-hand true division.

        :param other: Dividend
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero
        """
        return self.__rfloordiv__(other)

    def __mod__(self, other) -> '_FixedInt':
        """
        Modulo matching C/C++/Java and Z3 ``SRem``/``URem`` semantics.

        For **signed** types the sign of the result follows the *dividend* (not the
        divisor), matching C semantics and Z3's ``SRem`` (``bvsrem``) function.
        For example, ``Int8(-7) % Int8(3) == Int8(-1)``.

        .. important::

           This is **not** the same as Z3's ``%`` operator, which uses ``bvsmod``
           (sign follows the *divisor*, like Python ``%``).  The Z3 ``%`` operator
           would return ``2`` for ``(-7) % 3``, whereas this method returns ``-1``.

        For **unsigned** types the remainder is always non-negative, equivalent to
        Z3's ``URem`` (``bvurem``).  For example, ``UInt8(255) % UInt8(3) == UInt8(0)``
        (255 = 85 × 3 + 0).  This differs from Z3's ``%`` operator, which treats the
        bit pattern as signed and would return ``2`` (interpreting 255 as -1).

        :param other: Divisor
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero

        Example::

            >>> Int8(-7) % Int8(3)
            Int8(-1)
            >>> Int8(7) % Int8(-3)
            Int8(1)
            >>> UInt8(255) % UInt8(3)
            UInt8(0)
        """
        if isinstance(other, (_FixedInt, int)):
            divisor = int(other)
            if divisor == 0:
                raise ZeroDivisionError("integer division or modulo by zero")
            dividend = int(self)
            # C-style modulo: sign follows dividend, using pure integer arithmetic
            q, r = divmod(dividend, divisor)
            if r != 0 and (dividend < 0) != (divisor < 0):
                r -= divisor
            return type(self)(r)
        return NotImplemented

    def __rmod__(self, other) -> '_FixedInt':
        """
        Right-hand modulo operation.

        :param other: Dividend
        :return: New instance with result
        :rtype: _FixedInt
        :raises ZeroDivisionError: If divisor is zero
        """
        if isinstance(other, (_FixedInt, int)):
            dividend = int(other)
            divisor = int(self)
            if divisor == 0:
                raise ZeroDivisionError("integer division or modulo by zero")
            q, r = divmod(dividend, divisor)
            if r != 0 and (dividend < 0) != (divisor < 0):
                r -= divisor
            return type(self)(r)
        return NotImplemented

    def __pow__(self, other) -> '_FixedInt':
        """
        Power operation with wraparound.

        :param other: Exponent
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            exponent = int(other)
            if exponent < 0:
                raise ValueError("negative exponent not supported for integer types")
            return type(self)(int(self) ** exponent)
        return NotImplemented

    def __rpow__(self, other) -> '_FixedInt':
        """
        Right-hand power operation.

        :param other: Base
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            base = int(other)
            exponent = int(self)
            if exponent < 0:
                raise ValueError("negative exponent not supported for integer types")
            return type(self)(base ** exponent)
        return NotImplemented

    def __lshift__(self, other) -> '_FixedInt':
        """
        Left bit shift matching Z3 ``bvshl`` semantics.

        When the shift amount is a :class:`_FixedInt`, its bit pattern is
        interpreted as **unsigned** — exactly as Z3 ``bvshl`` does.  For example,
        ``Int8(1) << Int8(-1)`` shifts by 255 positions (the unsigned value of
        the 8-bit pattern ``0xFF``) and yields ``Int8(0)``.

        Shift amounts greater than or equal to the bit width always yield ``0``,
        matching Z3 ``bvshl``.  When *other* is a plain :class:`int`, Python's
        standard shift semantics apply (negative shift count raises
        :exc:`ValueError`).

        :param other: Shift amount
        :return: New instance with result
        :rtype: _FixedInt

        Example::

            >>> Int8(1) << Int8(7)
            Int8(-128)
            >>> Int8(1) << Int8(8)
            Int8(0)
            >>> Int8(1) << Int8(-1)
            Int8(0)
        """
        if isinstance(other, (_FixedInt, int)):
            shift_int = int(other)
            if isinstance(other, _FixedInt) and shift_int < 0:
                shift_int += 1 << (ctypes.sizeof(other._ctype) * 8)
            return type(self)(int(self) << shift_int)
        return NotImplemented

    def __rlshift__(self, other) -> '_FixedInt':
        """
        Right-hand left bit shift.

        :param other: Value to shift
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(other) << int(self))
        return NotImplemented

    def __rshift__(self, other) -> '_FixedInt':
        """
        Right bit shift: arithmetic for signed types, logical for unsigned types.

        Signed types fill vacated bits with the sign bit, equivalent to Z3's
        ``>>`` (``bvashr``).  Unsigned types fill with ``0``, equivalent to
        Z3's ``LShR`` (``bvlshr``).

        When the shift amount is a :class:`_FixedInt`, its bit pattern is
        interpreted as **unsigned** — exactly as Z3's ``bvashr``/``bvlshr``
        does.  For example, ``Int8(-1) >> Int8(-1)`` shifts arithmetically by
        255 positions and yields ``Int8(-1)``; ``UInt8(255) >> Int8(-1)`` shifts
        logically by 255 positions and yields ``UInt8(0)``.

        Shift amounts greater than or equal to the bit width yield ``0`` (logical)
        or the sign-extended value (arithmetic, e.g. ``-1`` for all-ones inputs),
        matching Z3 semantics.  When *other* is a plain :class:`int`, Python's
        standard shift semantics apply (negative shift count raises
        :exc:`ValueError`).

        :param other: Shift amount
        :return: New instance with result
        :rtype: _FixedInt

        Example::

            >>> Int8(-128) >> Int8(7)
            Int8(-1)
            >>> UInt8(128) >> UInt8(7)
            UInt8(1)
            >>> Int8(-1) >> Int8(-1)
            Int8(-1)
            >>> UInt8(255) >> Int8(-1)
            UInt8(0)
        """
        if isinstance(other, (_FixedInt, int)):
            shift_int = int(other)
            if isinstance(other, _FixedInt) and shift_int < 0:
                shift_int += 1 << (ctypes.sizeof(other._ctype) * 8)
            return type(self)(int(self) >> shift_int)
        return NotImplemented

    def __rrshift__(self, other) -> '_FixedInt':
        """
        Right-hand right bit shift.

        :param other: Value to shift
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(other) >> int(self))
        return NotImplemented

    def __and__(self, other) -> '_FixedInt':
        """
        Bitwise AND.

        :param other: Value to AND with
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) & int(other))
        return NotImplemented

    def __rand__(self, other) -> '_FixedInt':
        """
        Right-hand bitwise AND.

        :param other: Value to AND with
        :return: New instance with result
        :rtype: _FixedInt
        """
        return self.__and__(other)

    def __or__(self, other) -> '_FixedInt':
        """
        Bitwise OR.

        :param other: Value to OR with
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) | int(other))
        return NotImplemented

    def __ror__(self, other) -> '_FixedInt':
        """
        Right-hand bitwise OR.

        :param other: Value to OR with
        :return: New instance with result
        :rtype: _FixedInt
        """
        return self.__or__(other)

    def __xor__(self, other) -> '_FixedInt':
        """
        Bitwise XOR.

        :param other: Value to XOR with
        :return: New instance with result
        :rtype: _FixedInt
        """
        if isinstance(other, (_FixedInt, int)):
            return type(self)(int(self) ^ int(other))
        return NotImplemented

    def __rxor__(self, other) -> '_FixedInt':
        """
        Right-hand bitwise XOR.

        :param other: Value to XOR with
        :return: New instance with result
        :rtype: _FixedInt
        """
        return self.__xor__(other)

    def __neg__(self) -> '_FixedInt':
        """
        Unary two's-complement negation.

        Matches Z3's unary ``-`` on ``BitVec``.  The result wraps on overflow:
        negating ``INT_MIN`` produces ``INT_MIN`` (e.g. ``-Int8(-128) == Int8(-128)``).
        For unsigned types the result is ``(2^N - x) % 2^N``
        (e.g. ``-UInt8(1) == UInt8(255)``).

        :return: New instance with negated value
        :rtype: _FixedInt

        Example::

            >>> -Int8(-128)
            Int8(-128)
            >>> -UInt8(1)
            UInt8(255)
        """
        return type(self)(-int(self))

    def __pos__(self) -> '_FixedInt':
        """
        Unary plus (identity).

        :return: New instance with same value
        :rtype: _FixedInt
        """
        return type(self)(+int(self))

    def __invert__(self) -> '_FixedInt':
        """
        Bitwise NOT.

        :return: New instance with inverted bits
        :rtype: _FixedInt
        """
        return type(self)(~int(self))

    def __bool__(self) -> bool:
        """
        Boolean conversion.

        :return: ``False`` if zero, ``True`` otherwise
        :rtype: bool
        """
        return int(self) != 0


class Int8(_FixedInt):
    """
    8-bit signed integer (-128 to 127).

    Wraps :class:`ctypes.c_int8` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = Int8(127)
        >>> x + 1
        Int8(-128)
        >>> x - 200
        Int8(183)
    """
    _ctype = ctypes.c_int8
    _type_name = "Int8"
    _is_signed = True


class Int16(_FixedInt):
    """
    16-bit signed integer (-32768 to 32767).

    Wraps :class:`ctypes.c_int16` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = Int16(32767)
        >>> x + 1
        Int16(-32768)
    """
    _ctype = ctypes.c_int16
    _type_name = "Int16"
    _is_signed = True


class Int32(_FixedInt):
    """
    32-bit signed integer (-2147483648 to 2147483647).

    Wraps :class:`ctypes.c_int32` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = Int32(2147483647)
        >>> x + 1
        Int32(-2147483648)
    """
    _ctype = ctypes.c_int32
    _type_name = "Int32"
    _is_signed = True


class Int64(_FixedInt):
    """
    64-bit signed integer (-9223372036854775808 to 9223372036854775807).

    Wraps :class:`ctypes.c_int64` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = Int64(9223372036854775807)
        >>> x + 1
        Int64(-9223372036854775808)
    """
    _ctype = ctypes.c_int64
    _type_name = "Int64"
    _is_signed = True


class UInt8(_FixedInt):
    """
    8-bit unsigned integer (0 to 255).

    Wraps :class:`ctypes.c_uint8` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = UInt8(255)
        >>> x + 1
        UInt8(0)
        >>> x - 1
        UInt8(254)
    """
    _ctype = ctypes.c_uint8
    _type_name = "UInt8"


class UInt16(_FixedInt):
    """
    16-bit unsigned integer (0 to 65535).

    Wraps :class:`ctypes.c_uint16` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = UInt16(65535)
        >>> x + 1
        UInt16(0)
    """
    _ctype = ctypes.c_uint16
    _type_name = "UInt16"


class UInt32(_FixedInt):
    """
    32-bit unsigned integer (0 to 4294967295).

    Wraps :class:`ctypes.c_uint32` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = UInt32(4294967295)
        >>> x + 1
        UInt32(0)
    """
    _ctype = ctypes.c_uint32
    _type_name = "UInt32"


class UInt64(_FixedInt):
    """
    64-bit unsigned integer (0 to 18446744073709551615).

    Wraps :class:`ctypes.c_uint64` to provide C/C++/Java-style overflow behavior.

    :param value: Initial value, defaults to ``0``
    :type value: Union[int, _FixedInt], optional

    Example::

        >>> x = UInt64(18446744073709551615)
        >>> x + 1
        UInt64(0)
    """
    _ctype = ctypes.c_uint64
    _type_name = "UInt64"
