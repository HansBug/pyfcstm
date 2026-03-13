import ctypes

import pytest
import z3

from pyfcstm.utils.fixed import (
    Int8, Int16, Int32, Int64,
    UInt8, UInt16, UInt32, UInt64,
)

_ALL_TYPES = [Int8, Int16, Int32, Int64, UInt8, UInt16, UInt32, UInt64]
_SIGNED = [Int8, Int16, Int32, Int64]
_UNSIGNED = [UInt8, UInt16, UInt32, UInt64]

_TYPE_INFO = [
    (Int8,   -128,                  127,                  8),
    (Int16,  -32768,                32767,                16),
    (Int32,  -2147483648,           2147483647,           32),
    (Int64,  -9223372036854775808,  9223372036854775807,  64),
    (UInt8,   0,                    255,                  8),
    (UInt16,  0,                    65535,                16),
    (UInt32,  0,                    4294967295,           32),
    (UInt64,  0,                    18446744073709551615, 64),
]


# ---------------------------------------------------------------------------
# Z3 BitVec alignment helpers
# ---------------------------------------------------------------------------

def _to_bitvec(v):
    """Convert a _FixedInt instance to a Z3 BitVecVal with matching bit width."""
    bits = ctypes.sizeof(type(v)._ctype) * 8
    return z3.BitVecVal(int(v), bits)


def _bitvec_unsigned_val(bv):
    """Return the unsigned integer value of a Z3 BitVec constant."""
    return z3.simplify(bv).as_long()


def _fixed_unsigned_val(v):
    """Return the unsigned bit-pattern value of a _FixedInt instance."""
    bits = ctypes.sizeof(type(v)._ctype) * 8
    return int(v) & ((1 << bits) - 1)


def _fixed_bit_width(v):
    """Return the bit width of a _FixedInt instance."""
    return ctypes.sizeof(type(v)._ctype) * 8


def _to_bitvec_width(v, bits):
    """Convert a _FixedInt to a Z3 BitVecVal of *bits* width (truncates/sign-wraps as needed)."""
    return z3.BitVecVal(int(v), bits)


def _assert_z3_match(fixed_result, z3_result):
    """Assert that _FixedInt result matches Z3 BitVec result in both value and bit width."""
    fixed_bits = _fixed_bit_width(fixed_result)
    assert z3_result.size() == fixed_bits, \
        f"bit width mismatch: Z3={z3_result.size()} vs FixedInt={fixed_bits}"
    assert _bitvec_unsigned_val(z3_result) == _fixed_unsigned_val(fixed_result), \
        f"value mismatch: Z3={_bitvec_unsigned_val(z3_result):#x} " \
        f"vs FixedInt={_fixed_unsigned_val(fixed_result):#x}"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntConstruction:
    @pytest.mark.parametrize("cls,value,expected", [
        # Int8
        (Int8,  0,    0),   (Int8,  127,  127),  (Int8, -128, -128),
        (Int8,  128, -128), (Int8,  129, -127),  (Int8,  255,   -1),
        (Int8,  256,   0),  (Int8, -129,  127),  (Int8, -255,    1),
        (Int8, -256,   0),
        # Int16
        (Int16,  32767,  32767), (Int16, -32768, -32768),
        (Int16,  32768, -32768), (Int16,  65535,    -1), (Int16, -32769, 32767),
        # Int32
        (Int32,  2147483647,  2147483647), (Int32, -2147483648, -2147483648),
        (Int32,  2147483648, -2147483648), (Int32,  4294967295,          -1),
        # Int64
        (Int64,  9223372036854775807,  9223372036854775807),
        (Int64, -9223372036854775808, -9223372036854775808),
        (Int64,  9223372036854775808, -9223372036854775808),
        # UInt8
        (UInt8,   0,   0), (UInt8, 255, 255), (UInt8, 256,   0),
        (UInt8, 257,   1), (UInt8,  -1, 255), (UInt8,  -2, 254), (UInt8, -256, 0),
        # UInt16
        (UInt16, 65535, 65535), (UInt16, 65536,     0), (UInt16,    -1, 65535),
        # UInt32
        (UInt32, 4294967295, 4294967295), (UInt32, 4294967296, 0),
        (UInt32,          -1, 4294967295),
        # UInt64
        (UInt64, 18446744073709551615, 18446744073709551615),
        (UInt64, 18446744073709551616, 0), (UInt64, -1, 18446744073709551615),
    ])
    def test_init_wraps(self, cls, value, expected):
        assert int(cls(value)) == expected

    @pytest.mark.parametrize("cls,min_val,max_val,_b", _TYPE_INFO)
    def test_boundary_min(self, cls, min_val, max_val, _b):
        assert int(cls(min_val)) == min_val

    @pytest.mark.parametrize("cls,min_val,max_val,_b", _TYPE_INFO)
    def test_boundary_max(self, cls, min_val, max_val, _b):
        assert int(cls(max_val)) == max_val

    def test_from_fixed_int_same_type(self):
        assert int(Int8(Int8(42))) == 42

    def test_from_fixed_int_signed_to_unsigned(self):
        assert int(UInt8(Int8(-1))) == 255

    def test_from_fixed_int_unsigned_to_signed(self):
        assert int(Int8(UInt8(255))) == -1

    @pytest.mark.parametrize("cls", _ALL_TYPES)
    def test_default_zero(self, cls):
        assert int(cls()) == 0


# ---------------------------------------------------------------------------
# repr / str
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntRepr:
    @pytest.mark.parametrize("cls,value,expected", [
        (Int8,    42,   "Int8(42)"),   (Int8,  -128,  "Int8(-128)"),
        (Int8,   127,  "Int8(127)"),   (Int16, -32768, "Int16(-32768)"),
        (Int16, 32767, "Int16(32767)"), (Int32,     0,   "Int32(0)"),
        (Int64,  9223372036854775807, "Int64(9223372036854775807)"),
        (UInt8,  255,  "UInt8(255)"),  (UInt16,    0,  "UInt16(0)"),
        (UInt32,   1,  "UInt32(1)"),
        (UInt64, 18446744073709551615, "UInt64(18446744073709551615)"),
    ])
    def test_repr(self, cls, value, expected):
        assert repr(cls(value)) == expected


# ---------------------------------------------------------------------------
# int / bool / __index__
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntConversions:
    @pytest.mark.parametrize("cls,value", [
        (Int8, 42), (Int8, -1), (UInt8, 255),
        (Int64, -9223372036854775808), (UInt64, 18446744073709551615),
    ])
    def test_int_roundtrip(self, cls, value):
        assert int(cls(value)) == value

    @pytest.mark.parametrize("cls,value,expected_bool", [
        (Int8, 0, False), (Int8, 1, True), (Int8, -1, True), (Int8, 127, True),
        (UInt8, 0, False), (UInt8, 255, True),
        (Int32, 0, False), (Int32, -2147483648, True),
        (UInt64, 0, False), (UInt64, 1, True),
    ])
    def test_bool(self, cls, value, expected_bool):
        assert bool(cls(value)) == expected_bool

    def test_index_bin_hex_oct(self):
        assert hex(UInt8(255)) == "0xff"
        assert bin(UInt8(255)) == "0b11111111"
        assert oct(UInt8(255)) == "0o377"

    def test_index_list_subscript(self):
        lst = [10, 20, 30]
        assert lst[UInt8(1)] == 20
        assert lst[Int8(-1)] == 30

    def test_index_negative(self):
        assert Int8(-1).__index__() == -1


# ---------------------------------------------------------------------------
# bytes / from_bytes
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntBytes:
    @pytest.mark.parametrize("cls,value", [
        (Int8,   -128), (Int8,   127), (Int8,    0),
        (Int16, -32768), (Int16, 32767),
        (Int32, -2147483648), (Int32, 2147483647),
        (Int64, -9223372036854775808), (Int64, 9223372036854775807),
        (UInt8,  255), (UInt8,    0),
        (UInt16, 65535), (UInt16,   0),
        (UInt32, 4294967295), (UInt32, 0),
        (UInt64, 18446744073709551615), (UInt64, 0),
    ])
    def test_bytes_roundtrip_le(self, cls, value):
        assert int(cls.from_bytes(bytes(cls(value)), byteorder='little')) == value

    def test_bytes_length(self):
        for cls, _, _, nbits in _TYPE_INFO:
            assert len(bytes(cls(0))) == nbits // 8

    def test_from_bytes_le_known(self):
        assert int(Int16.from_bytes(b'\x00\x80', byteorder='little')) == -32768
        assert int(UInt16.from_bytes(b'\x00\x80', byteorder='little')) == 0x8000

    def test_from_bytes_be_known(self):
        assert int(Int16.from_bytes(b'\x80\x00', byteorder='big')) == -32768
        assert int(UInt16.from_bytes(b'\x80\x00', byteorder='big')) == 0x8000

    def test_from_bytes_int8_minus_one(self):
        assert int(Int8.from_bytes(b'\xff')) == -1

    def test_from_bytes_uint8_max(self):
        assert int(UInt8.from_bytes(b'\xff')) == 255

    @pytest.mark.parametrize("cls,value", [
        (Int64, -9223372036854775808), (Int64, 9223372036854775807),
        (UInt64, 18446744073709551615),
    ])
    def test_bytes_roundtrip_be(self, cls, value):
        x = cls(value)
        nbytes = len(bytes(x))
        raw = int(x) % (2 ** (8 * nbytes))
        b_big = raw.to_bytes(nbytes, byteorder='big')
        assert int(cls.from_bytes(b_big, byteorder='big')) == value


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntHash:
    @pytest.mark.parametrize("cls,value", [
        (Int8, 5), (Int8, 0), (Int8, -1), (Int8, 127), (Int8, -128),
        (UInt8, 255), (UInt16, 1000), (Int32, -1), (Int64, 0),
        (UInt64, 18446744073709551615),
    ])
    def test_hash_equals_python_int_hash(self, cls, value):
        assert hash(cls(value)) == hash(int(cls(value)))

    def test_cross_type_equal_same_hash(self):
        assert hash(Int8(5)) == hash(UInt8(5)) == hash(5)

    def test_hash_negative(self):
        assert hash(Int8(-1)) == hash(-1)

    def test_usable_in_set(self):
        assert len({Int8(1), Int8(2), Int8(1)}) == 2

    def test_usable_as_dict_key(self):
        d = {Int8(0): "zero", Int8(1): "one"}
        assert d[Int8(0)] == "zero"


# ---------------------------------------------------------------------------
# Equality / inequality  (30+ cases each)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntEquality:
    @pytest.mark.parametrize("a,b,expected", [
        # same type, same value
        (Int8(0),    Int8(0),    True),  (Int8(1),    Int8(1),    True),
        (Int8(-1),   Int8(-1),   True),  (Int8(127),  Int8(127),  True),
        (Int8(-128), Int8(-128), True),
        # same type, different value
        (Int8(0),  Int8(1),  False), (Int8(1),  Int8(-1), False),
        (Int8(127), Int8(-128), False),
        # unsigned same type
        (UInt8(0),   UInt8(0),   True), (UInt8(255), UInt8(255), True),
        (UInt8(0),   UInt8(255), False),
        # cross signed/unsigned – compare by int value
        (Int8(5),   UInt8(5),   True),  (Int8(0),   UInt8(0),   True),
        (Int8(-1),  UInt8(255), False), (Int8(127), UInt8(127), True),
        # larger types
        (Int16(32767), Int16(32767), True), (Int16(0), Int16(-1), False),
        (Int32(2147483647), Int32(2147483647), True),
        (Int64(9223372036854775807), Int64(9223372036854775807), True),
        (UInt64(18446744073709551615), UInt64(18446744073709551615), True),
        # with Python int
        (Int8(42),   42,    True),  (Int8(-1),  -1,   True),
        (UInt8(255), 255,   True),  (UInt8(0),   0,   True),
        (Int8(1),    2,     False), (UInt8(0),   1,   False),
        # cross-width
        (Int8(0), UInt64(0), True), (Int8(-1), Int64(-1), True),
        (UInt8(128), UInt16(128), True),
        # unsupported type
    ])
    def test_eq(self, a, b, expected):
        assert (a == b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (Int8(0), Int8(1), True), (Int8(1), Int8(1), False),
        (Int8(-1), Int8(0), True), (UInt8(0), UInt8(255), True),
        (Int8(5), UInt8(5), False), (Int8(-1), UInt8(255), True),
        (Int8(42), 42, False), (Int8(42), 43, True),
        (UInt8(255), 255, False), (UInt8(0), 1, True),
        (Int16(32767), Int16(-32768), True),
        (Int32(0), Int32(0), False),
        (Int64(9223372036854775807), Int64(9223372036854775807), False),
        (UInt64(18446744073709551615), UInt64(0), True),
        (Int8(1), 1.0, True),  # float: ne delegates to eq which returns NotImplemented -> not equal
    ])
    def test_ne(self, a, b, expected):
        assert (a != b) == expected

    def test_eq_unsupported_returns_not_implemented(self):
        assert Int8(0).__eq__("hello") is NotImplemented

    def test_ne_unsupported_returns_not_implemented(self):
        assert Int8(0).__ne__("hello") is NotImplemented


# ---------------------------------------------------------------------------
# Ordering  (30+ cases each comparison)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntOrdering:
    @pytest.mark.parametrize("a,b,expected", [
        # Int8
        (Int8(0), Int8(1), True), (Int8(1), Int8(0), False),
        (Int8(0), Int8(0), False), (Int8(-128), Int8(127), True),
        (Int8(127), Int8(-128), False), (Int8(-1), Int8(0), True),
        (Int8(-128), Int8(-127), True), (Int8(127), Int8(126), False),
        # UInt8
        (UInt8(0), UInt8(1), True), (UInt8(255), UInt8(0), False),
        (UInt8(128), UInt8(129), True), (UInt8(0), UInt8(0), False),
        # with Python int
        (Int8(-1), 0, True), (Int8(127), 128, True), (UInt8(254), 255, True),
        (Int8(0), -1, False), (Int8(127), 127, False),
        # larger types
        (Int16(-32768), Int16(32767), True), (Int16(32767), Int16(-32768), False),
        (Int32(-2147483648), Int32(2147483647), True),
        (Int64(-9223372036854775808), Int64(9223372036854775807), True),
        (UInt16(0), UInt16(65535), True), (UInt32(0), UInt32(4294967295), True),
        (UInt64(0), UInt64(18446744073709551615), True),
        # zero comparisons
        (Int8(0), UInt8(0), False), (Int8(-1), Int32(-1), False),
        (Int8(1), UInt8(2), True),
    ])
    def test_lt(self, a, b, expected):
        assert (a < b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (Int8(0), Int8(0), True), (Int8(0), Int8(1), True),
        (Int8(1), Int8(0), False), (Int8(-128), Int8(-128), True),
        (Int8(127), Int8(127), True), (Int8(127), Int8(-128), False),
        (UInt8(0), UInt8(0), True), (UInt8(255), UInt8(255), True),
        (UInt8(254), UInt8(255), True), (UInt8(255), UInt8(254), False),
        (Int8(0), 0, True), (Int8(0), 1, True), (Int8(1), 0, False),
        (Int8(-1), -1, True), (Int8(-1), 0, True), (Int8(0), -1, False),
        (Int16(-32768), Int16(-32768), True), (Int16(32767), Int16(32767), True),
        (Int16(-32768), Int16(32767), True),
        (Int32(0), Int32(0), True), (Int64(0), Int64(0), True),
        (UInt16(0), UInt16(65535), True), (UInt32(100), UInt32(100), True),
        (UInt64(0), UInt64(18446744073709551615), True),
        (Int8(5), UInt8(5), True), (Int8(-1), Int32(-1), True),
        (Int8(5), UInt8(6), True), (UInt8(10), 10, True),
    ])
    def test_le(self, a, b, expected):
        assert (a <= b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (Int8(1), Int8(0), True), (Int8(0), Int8(1), False),
        (Int8(0), Int8(0), False), (Int8(127), Int8(-128), True),
        (Int8(-128), Int8(127), False), (Int8(0), Int8(-1), True),
        (UInt8(1), UInt8(0), True), (UInt8(0), UInt8(1), False),
        (UInt8(255), UInt8(0), True), (UInt8(0), UInt8(0), False),
        (Int8(0), -1, True), (Int8(127), 126, True), (UInt8(255), 254, True),
        (Int8(0), 1, False), (Int8(127), 127, False),
        (Int16(32767), Int16(-32768), True), (Int16(-32768), Int16(32767), False),
        (Int32(2147483647), Int32(-2147483648), True),
        (Int64(9223372036854775807), Int64(-9223372036854775808), True),
        (UInt16(65535), UInt16(0), True), (UInt32(4294967295), UInt32(0), True),
        (UInt64(18446744073709551615), UInt64(0), True),
        (Int8(0), UInt8(0), False), (Int8(1), UInt8(0), True),
        (Int8(2), UInt8(1), True), (UInt8(200), 100, True),
    ])
    def test_gt(self, a, b, expected):
        assert (a > b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (Int8(0), Int8(0), True), (Int8(1), Int8(0), True),
        (Int8(0), Int8(1), False), (Int8(-128), Int8(-128), True),
        (Int8(127), Int8(127), True), (Int8(-128), Int8(127), False),
        (UInt8(0), UInt8(0), True), (UInt8(255), UInt8(255), True),
        (UInt8(255), UInt8(254), True), (UInt8(254), UInt8(255), False),
        (Int8(0), 0, True), (Int8(1), 0, True), (Int8(0), 1, False),
        (Int8(-1), -1, True), (Int8(0), -1, True), (Int8(-1), 0, False),
        (Int16(32767), Int16(32767), True), (Int16(-32768), Int16(-32768), True),
        (Int16(32767), Int16(-32768), True),
        (Int32(0), Int32(0), True), (Int64(0), Int64(0), True),
        (UInt16(65535), UInt16(0), True), (UInt32(100), UInt32(100), True),
        (UInt64(18446744073709551615), UInt64(0), True),
        (Int8(5), UInt8(5), True), (Int8(-1), Int32(-1), True),
        (Int8(6), UInt8(5), True), (UInt8(10), 10, True),
    ])
    def test_ge(self, a, b, expected):
        assert (a >= b) == expected

    def test_lt_unsupported_returns_not_implemented(self):
        assert Int8(0).__lt__("x") is NotImplemented

    def test_le_unsupported_returns_not_implemented(self):
        assert Int8(0).__le__("x") is NotImplemented

    def test_gt_unsupported_returns_not_implemented(self):
        assert Int8(0).__gt__("x") is NotImplemented

    def test_ge_unsupported_returns_not_implemented(self):
        assert Int8(0).__ge__("x") is NotImplemented

    def test_sort_signed(self):
        vals = [Int8(5), Int8(-10), Int8(0), Int8(127), Int8(-128)]
        assert sorted(vals) == [Int8(-128), Int8(-10), Int8(0), Int8(5), Int8(127)]

    def test_sort_unsigned(self):
        vals = [UInt8(255), UInt8(0), UInt8(128), UInt8(1)]
        assert sorted(vals) == [UInt8(0), UInt8(1), UInt8(128), UInt8(255)]


# ---------------------------------------------------------------------------
# Addition  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntAddition:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # Int8 normal
        (Int8,  0,   0,    0), (Int8,  1,   2,    3), (Int8, -5,   5,    0),
        (Int8, -1,   1,    0), (Int8, 10, -10,    0), (Int8, 64,  63,  127),
        # Int8 overflow / underflow
        (Int8,  127,   1, -128), (Int8, -128,  -1,  127),
        (Int8,  127, 127,   -2), (Int8, -128, -128,   0),
        (Int8,   64,  64, -128), (Int8,  -64,  -65, 127),
        (Int8,  100,  50, -106), (Int8, -100, -100,  56),
        (Int8,   50, 100, -106), (Int8,   -1,  -1,   -2),
        # Int16
        (Int16,  32767,     1, -32768), (Int16, -32768,    -1,  32767),
        (Int16,  32767, 32767,     -2), (Int16,     0,      0,      0),
        # Int32
        (Int32,  2147483647,     1, -2147483648),
        (Int32, -2147483648,    -1,  2147483647),
        # Int64
        (Int64,  9223372036854775807,   1, -9223372036854775808),
        (Int64, -9223372036854775808,  -1,  9223372036854775807),
        # UInt8
        (UInt8,  255,   1,   0), (UInt8,   0, 255, 255),
        (UInt8,  200, 100,  44), (UInt8, 128, 128,   0),
        # UInt16
        (UInt16, 65535,    1,     0), (UInt16, 60000, 10000, 4464),
        # UInt32
        (UInt32, 4294967295, 1, 0),
        # UInt64
        (UInt64, 18446744073709551615, 1, 0),
    ])
    def test_add(self, cls, a, b, expected):
        assert int(cls(a) + cls(b)) == expected

    def test_radd_python_int(self):
        assert int(1 + Int8(127)) == -128
        assert int(0 + UInt8(255)) == 255

    def test_add_python_int(self):
        assert int(Int8(100) + 50) == -106
        assert int(UInt8(200) + 100) == 44

    def test_add_type_preserved(self):
        assert type(Int8(1) + Int8(1)) is Int8
        assert type(UInt32(1) + UInt32(1)) is UInt32

    def test_add_unsupported_returns_not_implemented(self):
        assert Int8(1).__add__(3.14) is NotImplemented


# ---------------------------------------------------------------------------
# Subtraction  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntSubtraction:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # Int8 normal
        (Int8,  5,   3,   2), (Int8,  0,   0,   0), (Int8,  0,   1,  -1),
        (Int8, -5,  -3,  -2), (Int8, 10, -10,  20), (Int8, -10,  10, -20),
        # Int8 overflow / underflow
        (Int8, -128,   1,  127), (Int8,  127,  -1, -128),
        (Int8, -128, -128,   0), (Int8,  127, 127,    0),
        (Int8,   -1, 127, -128), (Int8,    0, -128, -128),
        (Int8,    1, -127, -128), (Int8,  60,  -70, -126),
        (Int8, -50,   50, -100),
        # Int16
        (Int16, -32768,    1,  32767), (Int16,  32767,   -1, -32768),
        (Int16,      0,  32767, -32767), (Int16,      0,      0,      0),
        # Int32
        (Int32, -2147483648,     1,  2147483647),
        (Int32,  2147483647,    -1, -2147483648),
        # Int64
        (Int64, -9223372036854775808,   1,  9223372036854775807),
        (Int64,  9223372036854775807,  -1, -9223372036854775808),
        # UInt8
        (UInt8,   0,   1, 255), (UInt8, 255, 255,   0),
        (UInt8, 100, 200, 156), (UInt8,   1, 255,   2),
        # UInt16
        (UInt16, 0, 1, 65535), (UInt16, 100, 65535, 101),
        # UInt32
        (UInt32, 0, 1, 4294967295),
        # UInt64
        (UInt64, 0, 1, 18446744073709551615),
    ])
    def test_sub(self, cls, a, b, expected):
        assert int(cls(a) - cls(b)) == expected

    def test_rsub_python_int(self):
        assert int(10 - Int8(20)) == -10
        assert int(0 - UInt8(1)) == 255

    def test_rsub_unsupported_returns_not_implemented(self):
        assert Int8(1).__rsub__(3.14) is NotImplemented

    def test_sub_type_preserved(self):
        assert type(UInt8(10) - UInt8(5)) is UInt8


# ---------------------------------------------------------------------------
# Multiplication  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntMultiplication:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # Int8 normal
        (Int8,  0,  127,   0), (Int8,  1,   1,   1), (Int8, -1,   1,  -1),
        (Int8, -1,  -1,    1), (Int8,  2,  63, 126), (Int8, 10, -13, 126),
        # Int8 overflow
        (Int8,   64,   2, -128), (Int8,  -64,   2, -128),
        (Int8,   64,  -2, -128), (Int8,  -64,  -2, -128),
        (Int8, -128,  -1, -128), (Int8,    3,  43, -127),
        (Int8,  127, 127,    1), (Int8,   12,  12, -112),
        (Int8,    2,   8,   16), (Int8,   11,  11, 121),
        # Int16
        (Int16,  256, 256, 0), (Int16, 32767, 2, -2),
        (Int16, -32768, 2, 0),
        # Int32
        (Int32, 65536, 65536, 0), (Int32, 2147483647, 2, -2),
        # Int64
        (Int64, 4611686018427387904, 2, -9223372036854775808),
        # UInt8
        (UInt8,  16,  16,   0), (UInt8, 128,   2,   0),
        (UInt8, 200,   2, 144), (UInt8, 255, 255,   1),
        (UInt8,   3, 100,  44),
        # UInt16
        (UInt16, 256, 256, 0), (UInt16, 65535, 2, 65534),
        # UInt32
        (UInt32, 65536, 65536, 0),
        # UInt64
        (UInt64, 1 << 32, 1 << 32, 0),
    ])
    def test_mul(self, cls, a, b, expected):
        assert int(cls(a) * cls(b)) == expected

    def test_rmul_python_int(self):
        assert int(3 * Int8(50)) == -106
        assert int(2 * UInt8(200)) == 144

    def test_mul_by_zero(self):
        for cls in _ALL_TYPES:
            assert int(cls(127) * cls(0)) == 0

    def test_mul_unsupported_returns_not_implemented(self):
        assert Int8(1).__mul__(3.14) is NotImplemented

    def test_mul_type_preserved(self):
        assert type(Int8(2) * Int8(3)) is Int8


# ---------------------------------------------------------------------------
# Floor division  (30+ cases, C truncation toward zero)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntDivision:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # Int8 positive/positive
        (Int8,  7,  2,  3), (Int8,  6, 2,  3), (Int8,  5,  2,  2),
        (Int8,  1, 10,  0), (Int8,  0, 5,  0), (Int8, 127, 1, 127),
        (Int8, 127, 127, 1),
        # Int8 negative dividend (C != Python)
        (Int8,  -7,  2, -3), (Int8,  -6,  2, -3), (Int8,  -5,  2, -2),
        (Int8,  -1,  2,  0),
        # Int8 negative divisor
        (Int8,   7, -2, -3), (Int8,   1, -1, -1), (Int8, 127, -1, -127),
        # both negative
        (Int8,  -7, -2, 3), (Int8,  -6, -3, 2), (Int8, -128, -128, 1),
        # INT_MIN / -1 overflow wraps
        (Int8, -128, -1, -128),
        # UInt8
        (UInt8, 255,   2, 127), (UInt8, 200,  3,  66),
        (UInt8, 100, 100,   1), (UInt8,   7,  2,   3),
        # Int16
        (Int16, -7, 2, -3), (Int16, 32767, 2, 16383),
        # Int32
        (Int32, -9, 4, -2),
        # Int64 precision  (float div would give wrong answer for these)
        (Int64, 9223372036854775807,  2, 4611686018427387903),
        (Int64, 9223372036854775806,  2, 4611686018427387903),
        (Int64, -9223372036854775808, 2, -4611686018427387904),
        (Int64, -7, 2, -3),
        # UInt32/64
        (UInt32, 4294967295,          2, 2147483647),
        (UInt64, 18446744073709551615, 2, 9223372036854775807),
    ])
    def test_floordiv(self, cls, a, b, expected):
        assert int(cls(a) // cls(b)) == expected

    def test_truediv_equals_floordiv(self):
        assert int(Int8(7) / Int8(2)) == int(Int8(7) // Int8(2))
        assert int(Int8(-7) / Int8(2)) == int(Int8(-7) // Int8(2))

    def test_rtruediv_delegates(self):
        # Trigger __rtruediv__ via a subclass whose __truediv__ returns NotImplemented
        class _NoDiv(int):
            def __truediv__(self, other):
                return NotImplemented
        result = _NoDiv(10) / Int8(2)
        assert int(result) == 5

    def test_zero_division_floordiv(self):
        with pytest.raises(ZeroDivisionError):
            Int8(1) // Int8(0)

    def test_zero_division_truediv(self):
        with pytest.raises(ZeroDivisionError):
            Int8(1) / Int8(0)

    def test_rfloordiv_python_int(self):
        assert int(7 // Int8(2)) == 3
        assert int(-7 // Int8(2)) == -3   # C truncation
        assert int(7 // Int8(-2)) == -3

    def test_rfloordiv_zero_division(self):
        with pytest.raises(ZeroDivisionError):
            5 // Int8(0)

    def test_floordiv_unsupported_returns_not_implemented(self):
        assert Int8(1).__floordiv__(3.14) is NotImplemented

    def test_rfloordiv_unsupported_returns_not_implemented(self):
        assert Int8(1).__rfloordiv__(3.14) is NotImplemented

    def test_rtruediv_unsupported_returns_not_implemented(self):
        # Direct call covers line 341 (return self.__rfloordiv__(other))
        result = Int8(2).__rtruediv__(3.14)
        assert result is NotImplemented

    def test_c_vs_python_division(self):
        # Confirm we differ from Python's floor division for negative operands
        assert int(Int8(-7) // Int8(2)) == -3   # C:  -3
        assert (-7) // 2 == -4                   # Python: -4

    def test_div_type_preserved(self):
        assert type(Int8(10) // Int8(3)) is Int8


# ---------------------------------------------------------------------------
# Modulo  (30+ cases, C sign-follows-dividend)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntModulo:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # both positive
        (Int8,   7,  3,  1), (Int8,   6,  3, 0), (Int8,   0,  5, 0),
        (Int8,   5,  1,  0), (Int8,  50,  7, 1), (Int8, 127, 10, 7),
        # negative dividend (sign follows dividend = negative)
        (Int8,  -7,  3, -1), (Int8,  -6,  3, 0),  (Int8,  -1,  2, -1),
        (Int8,  -5,  1,  0), (Int8, -50,  7,-1), (Int8, -128, 10, -8),
        # positive dividend, negative divisor (sign follows dividend = positive)
        (Int8,   7, -3,  1), (Int8,   6, -3, 0),  (Int8,  50, -7,  1),
        # both negative
        (Int8,  -7, -3, -1), (Int8,  -6, -3, 0),  (Int8, -50, -7, -1),
        # Int16
        (Int16,    -7,  3, -1), (Int16, 32767, 7, 0),
        # Int32
        (Int32,    -7,  3, -1),
        # Int64 precision
        (Int64, 9223372036854775807, 2, 1),
        (Int64, 9223372036854775806, 2, 0),
        (Int64, -9223372036854775807, 2, -1),
        (Int64, -7, 3, -1),
        # UInt8
        (UInt8, 255,  3,  0), (UInt8, 100, 30, 10), (UInt8, 7, 2, 1),
        (UInt8, 255, 16, 15),
        # UInt16
        (UInt16, 65535, 256, 255),
        # UInt32
        (UInt32, 4294967295, 256, 255),
        # UInt64
        (UInt64, 18446744073709551615, 256, 255),
    ])
    def test_mod(self, cls, a, b, expected):
        assert int(cls(a) % cls(b)) == expected

    def test_zero_modulo_raises(self):
        with pytest.raises(ZeroDivisionError):
            Int8(5) % Int8(0)

    def test_rmod_python_int(self):
        assert int(-7 % Int8(3)) == -1   # C behavior
        assert int(7 % Int8(-3)) == 1

    def test_rmod_zero_division(self):
        with pytest.raises(ZeroDivisionError):
            5 % Int8(0)

    def test_mod_unsupported_returns_not_implemented(self):
        assert Int8(1).__mod__(3.14) is NotImplemented

    def test_rmod_unsupported_returns_not_implemented(self):
        assert Int8(1).__rmod__(3.14) is NotImplemented

    def test_c_vs_python_modulo(self):
        assert int(Int8(-7) % Int8(3)) == -1   # C: -1
        assert (-7) % 3 == 2                    # Python: 2
        assert int(Int8(7) % Int8(-3)) == 1     # C: 1
        assert 7 % (-3) == -2                   # Python: -2

    def test_mod_type_preserved(self):
        assert type(Int32(10) % Int32(3)) is Int32


# ---------------------------------------------------------------------------
# Power  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntPower:
    @pytest.mark.parametrize("cls,base,exp,expected", [
        # Int8
        (Int8,   0,  0,   1), (Int8,   0,  5,   0), (Int8,  1, 100,   1),
        (Int8,  -1,  2,   1), (Int8,  -1,  3,  -1), (Int8,  2,  0,    1),
        (Int8,   2,  1,   2), (Int8,   2,  6,  64), (Int8,  2,  7, -128),
        (Int8,   2,  8,   0), (Int8,   3,  4,  81), (Int8,  3,  5,  -13),
        (Int8,  -2,  7, -128), (Int8,  -2,  8,  0), (Int8, 10,   2, 100),
        (Int8,  10,  3, -24), (Int8,  11,  2, 121), (Int8, 12,  2, -112),
        (Int8,   7,  2,  49),
        # Int16
        (Int16,  2, 15, -32768), (Int16,  2, 16, 0),
        # Int32
        (Int32,  2, 31, -2147483648), (Int32, 2, 32, 0),
        # Int64
        (Int64,  2, 63, -9223372036854775808), (Int64, 2, 64, 0),
        # UInt8
        (UInt8,  2,  7,  128), (UInt8,  2,  8,   0),
        (UInt8, 16,  2,    0), (UInt8,  3,  4,  81),
        # UInt16
        (UInt16, 2, 16, 0),
        # UInt32
        (UInt32, 2, 32, 0),
        # UInt64
        (UInt64, 2, 64, 0),
    ])
    def test_pow(self, cls, base, exp, expected):
        assert int(cls(base) ** cls(exp)) == expected

    def test_pow_zero_zero(self):
        assert int(UInt8(0) ** UInt8(0)) == 1

    def test_negative_exponent_in_pow_raises(self):
        with pytest.raises(ValueError):
            Int8(2) ** Int8(-1)

    def test_negative_exponent_in_rpow_raises(self):
        # Directly calling __rpow__ with a negative exponent
        with pytest.raises(ValueError):
            Int8(-1).__rpow__(2)

    def test_rpow_python_int(self):
        assert int(2 ** Int8(7)) == -128
        assert int(2 ** UInt8(8)) == 0

    def test_pow_unsupported_returns_not_implemented(self):
        assert Int8(1).__pow__(3.14) is NotImplemented

    def test_rpow_unsupported_returns_not_implemented(self):
        assert Int8(2).__rpow__(3.14) is NotImplemented

    def test_pow_type_preserved(self):
        assert type(Int8(2) ** Int8(3)) is Int8


# ---------------------------------------------------------------------------
# Bitwise AND  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntBitwiseAnd:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # UInt8
        (UInt8, 0xFF, 0x0F, 0x0F), (UInt8, 0xFF, 0xF0, 0xF0),
        (UInt8, 0xFF, 0xFF, 0xFF), (UInt8, 0x00, 0xFF, 0x00),
        (UInt8, 0xAA, 0x55, 0x00), (UInt8, 0xAA, 0xFF, 0xAA),
        (UInt8, 0x12, 0x34, 0x10), (UInt8, 0xC0, 0xF0, 0xC0),
        (UInt8,  255,    1,    1), (UInt8,  128,  127,    0),
        (UInt8,  170,  170,  170), (UInt8,  192,  240,  192),
        # Int8
        (Int8, -1,  127,  127), (Int8,  -1,   -1,   -1),
        (Int8,  0,   -1,    0), (Int8, -128, 127,    0),
        (Int8, -128,  -1, -128), (Int8,  42,   15,   10),
        (Int8,  42,   63,   42), (Int8,   0,   42,    0),
        # Int16
        (Int16, 0x7FFF, 0x00FF, 0x00FF), (Int16, -1, 32767, 32767),
        (Int16, -32768, 32767, 0), (Int16, -32768, -32768, -32768),
        (Int16, 0, -1, 0),
        # UInt32
        (UInt32, 0xDEADBEEF, 0xFFFF0000, 0xDEAD0000),
        (UInt32, 0xDEADBEEF, 0x0000FFFF, 0xBEEF),
        (UInt32, 0xFFFFFFFF, 0x0F0F0F0F, 0x0F0F0F0F),
        # UInt64
        (UInt64, 0xFFFFFFFFFFFFFFFF, 0x0F0F0F0F0F0F0F0F, 0x0F0F0F0F0F0F0F0F),
        (UInt64, 0, 18446744073709551615, 0),
        # Int32
        (Int32, -1, 0x7FFFFFFF, 0x7FFFFFFF),
    ])
    def test_and(self, cls, a, b, expected):
        assert int(cls(a) & cls(b)) == expected

    def test_rand_python_int(self):
        assert int(0xFF & UInt8(0x0F)) == 0x0F

    def test_and_unsupported_returns_not_implemented(self):
        assert Int8(1).__and__(3.14) is NotImplemented

    def test_and_type_preserved(self):
        assert type(Int8(3) & Int8(1)) is Int8


# ---------------------------------------------------------------------------
# Bitwise OR  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntBitwiseOr:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # UInt8
        (UInt8, 0x00, 0x00, 0x00), (UInt8, 0xFF, 0x00, 0xFF),
        (UInt8, 0x0F, 0xF0, 0xFF), (UInt8, 0xAA, 0x55, 0xFF),
        (UInt8, 0xAA, 0xAA, 0xAA), (UInt8, 0x12, 0x34, 0x36),
        (UInt8,    1,    2,    3), (UInt8,  128,   64,  192),
        (UInt8,    1,  254,  255), (UInt8,    3,   12,   15),
        (UInt8,  128,  128,  128), (UInt8,    0,  255,  255),
        # Int8
        (Int8,   0,  -1,  -1), (Int8, -128, 127, -1),
        (Int8,  -1,   0,  -1), (Int8,   -1,  -1, -1),
        (Int8,   0,   0,   0), (Int8,   42,  85, 127),
        (Int8,  64,  63, 127), (Int8,  64,  64,  64),
        (Int8, -64, -65,  -1), (Int8,  -1, 127,  -1),
        # Int16
        (Int16, 0x00FF, 0xFF00, -1), (Int16,    0,    0,     0),
        (Int16, -32768,     0, -32768), (Int16, 0xFF00, 0x00FF, -1),
        # UInt32
        (UInt32, 0xDEAD0000, 0x0000BEEF, 0xDEADBEEF),
        (UInt32,           0, 4294967295, 4294967295),
        # UInt64
        (UInt64,                    0, 18446744073709551615, 18446744073709551615),
        (UInt64, 9223372036854775808, 9223372036854775807,  18446744073709551615),
        # UInt16
        (UInt16, 0xFF00, 0x00FF, 0xFFFF),
    ])
    def test_or(self, cls, a, b, expected):
        assert int(cls(a) | cls(b)) == expected

    def test_ror_python_int(self):
        assert int(0x0F | UInt8(0xF0)) == 0xFF

    def test_or_unsupported_returns_not_implemented(self):
        assert Int8(1).__or__(3.14) is NotImplemented

    def test_or_type_preserved(self):
        assert type(Int8(1) | Int8(2)) is Int8


# ---------------------------------------------------------------------------
# Bitwise XOR  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntBitwiseXor:
    @pytest.mark.parametrize("cls,a,b,expected", [
        # UInt8
        (UInt8, 0xFF, 0xFF, 0x00), (UInt8, 0xFF, 0x00, 0xFF),
        (UInt8, 0x00, 0x00, 0x00), (UInt8, 0xAA, 0x55, 0xFF),
        (UInt8, 0xAA, 0xAA, 0x00), (UInt8, 0x12, 0x34, 0x26),
        (UInt8,  170,   85,  255), (UInt8, 255,    1, 254),
        (UInt8,  128,  127,  255), (UInt8, 192,   48, 240),
        (UInt8,    1,    2,    3), (UInt8,   3,    3,   0),
        (UInt8,   15,   85,   90),
        # Int8
        (Int8,  -1,  -1,   0), (Int8,  -1,   0,  -1),
        (Int8,   0,   0,   0), (Int8,  42,  42,   0),
        (Int8,  42, -43,  -1), (Int8, 127, -128, -1),
        (Int8, -128, -128,  0), (Int8, -128, 127, -1),
        (Int8,   1,   2,   3), (Int8,  64, -64, -128),
        # Int16
        (Int16, -1, -1, 0), (Int16, 0x5555, 0xAAAA, -1),
        (Int16,  0, -1, -1),
        # Int32
        (Int32, -1, -1, 0), (Int32, 0, -1, -1),
        # UInt32
        (UInt32, 0xDEADBEEF, 0xDEADBEEF, 0),
        (UInt32, 0xFFFFFFFF, 0x0F0F0F0F, 0xF0F0F0F0),
        # UInt64
        (UInt64, 0, 18446744073709551615, 18446744073709551615),
        (UInt64, 18446744073709551615, 18446744073709551615, 0),
    ])
    def test_xor(self, cls, a, b, expected):
        assert int(cls(a) ^ cls(b)) == expected

    def test_rxor_python_int(self):
        assert int(0xFF ^ UInt8(0x0F)) == 0xF0

    def test_xor_unsupported_returns_not_implemented(self):
        assert Int8(1).__xor__(3.14) is NotImplemented

    def test_xor_type_preserved(self):
        assert type(Int8(3) ^ Int8(1)) is Int8


# ---------------------------------------------------------------------------
# Bitwise NOT  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntBitwiseNot:
    @pytest.mark.parametrize("cls,value,expected", [
        # UInt8: ~x == 255 - x
        (UInt8,   0,  255), (UInt8, 255,   0), (UInt8,   1, 254),
        (UInt8,   2,  253), (UInt8, 127, 128), (UInt8, 128, 127),
        (UInt8, 170,   85), (UInt8,  85, 170), (UInt8, 240,  15),
        (UInt8,  15,  240), (UInt8, 192,  63), (UInt8,  63, 192),
        # UInt16
        (UInt16,     0, 65535), (UInt16, 65535,     0), (UInt16, 256, 65279),
        # UInt32
        (UInt32,          0, 4294967295), (UInt32, 4294967295,          0),
        (UInt32, 0x0F0F0F0F, 0xF0F0F0F0),
        # UInt64
        (UInt64,                    0, 18446744073709551615),
        (UInt64, 18446744073709551615,                    0),
        # Int8: ~x == -(x+1)
        (Int8,   0,   -1), (Int8,  -1,    0), (Int8,   1,   -2),
        (Int8,  -2,    1), (Int8, 127, -128), (Int8, -128,  127),
        (Int8,  42,  -43), (Int8, -43,   42),
        # Int16
        (Int16,  32767, -32768), (Int16, -32768,  32767),
        (Int16,      0,     -1),
        # Int32
        (Int32,  2147483647, -2147483648), (Int32,          0, -1),
        # Int64
        (Int64,  9223372036854775807, -9223372036854775808),
        (Int64,                    0,                   -1),
    ])
    def test_invert(self, cls, value, expected):
        assert int(~cls(value)) == expected


# ---------------------------------------------------------------------------
# Left shift  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntLeftShift:
    @pytest.mark.parametrize("cls,value,shift,expected", [
        # UInt8
        (UInt8,   0,  0,   0), (UInt8,  1,  0,   1), (UInt8,  1,  1,   2),
        (UInt8,   1,  7, 128), (UInt8,  1,  8,   0), (UInt8,  2,  7,   0),
        (UInt8, 128,  1,   0), (UInt8,  3,  4,  48), (UInt8, 170,  1,  84),
        (UInt8, 255,  1, 254), (UInt8,  16,  4,  0), (UInt8,  15,  4, 240),
        (UInt8,  85,  1, 170),
        # Int8
        (Int8,   1,  0,    1), (Int8,  1,  6,   64), (Int8,   1,  7, -128),
        (Int8,   1,  8,    0), (Int8, -1,  1,   -2), (Int8,  -1,  7, -128),
        (Int8,  -1,  8,    0), (Int8, 64,  1, -128), (Int8, -64,  1, -128),
        (Int8,   2,  6, -128),
        # Int16
        (Int16,  1, 15, -32768), (Int16, 1, 16, 0),
        # Int32
        (Int32,  1, 31, -2147483648), (Int32, 1, 32, 0),
        # Int64
        (Int64,  1, 63, -9223372036854775808), (Int64, 1, 64, 0),
        # UInt16
        (UInt16, 1, 15, 32768),
        # UInt32
        (UInt32, 1, 31, 2147483648),
        # UInt64
        (UInt64, 1, 63, 9223372036854775808),
    ])
    def test_lshift(self, cls, value, shift, expected):
        assert int(cls(value) << cls(shift)) == expected

    def test_lshift_python_int(self):
        assert int(Int8(1) << 7) == -128
        assert int(UInt8(1) << 8) == 0

    def test_rlshift_python_int(self):
        assert int(1 << UInt8(7)) == 128

    def test_lshift_unsupported_returns_not_implemented(self):
        assert Int8(1).__lshift__(3.14) is NotImplemented

    def test_rlshift_unsupported_returns_not_implemented(self):
        assert Int8(1).__rlshift__(3.14) is NotImplemented

    def test_lshift_type_preserved(self):
        assert type(Int32(1) << Int32(3)) is Int32


# ---------------------------------------------------------------------------
# Right shift  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntRightShift:
    @pytest.mark.parametrize("cls,value,shift,expected", [
        # UInt8 logical shift (fills with 0)
        (UInt8, 128,  0, 128), (UInt8, 128,  1,  64), (UInt8, 128,  7,   1),
        (UInt8, 128,  8,   0), (UInt8, 255,  0, 255), (UInt8, 255,  1, 127),
        (UInt8, 255,  4,  15), (UInt8, 255,  7,   1), (UInt8, 255,  8,   0),
        (UInt8,   1,  1,   0), (UInt8, 200,  3,  25), (UInt8,  84,  2,  21),
        (UInt8, 170,  1,  85),
        # Int8 arithmetic shift (fills with sign bit)
        (Int8, -128,  0, -128), (Int8, -128,  1,  -64), (Int8, -128,  7,  -1),
        (Int8,   -1,  1,   -1), (Int8,   -1,  7,   -1), (Int8,   -2,  1,  -1),
        (Int8,   64,  1,   32), (Int8,   64,  6,    1), (Int8,  127,  1,  63),
        (Int8,    0,  7,    0), (Int8, -100,  2,  -25), (Int8,   -4,  1,  -2),
        # Int16
        (Int16, -32768,  0, -32768), (Int16, -32768, 15, -1),
        # Int32
        (Int32, -2147483648, 31, -1),
        # Int64
        (Int64, -9223372036854775808, 63, -1),
        # UInt16/32/64
        (UInt16,  65535,  8, 255), (UInt32, 4294967295, 16, 65535),
        (UInt64, 18446744073709551615, 32, 4294967295),
    ])
    def test_rshift(self, cls, value, shift, expected):
        assert int(cls(value) >> cls(shift)) == expected

    def test_rshift_python_int(self):
        assert int(Int8(-128) >> 7) == -1
        assert int(UInt8(255) >> 4) == 15

    def test_rrshift_python_int(self):
        assert int(128 >> UInt8(7)) == 1

    def test_rshift_by_zero_identity(self):
        assert int(Int8(-1) >> Int8(0)) == -1
        assert int(UInt8(255) >> UInt8(0)) == 255

    def test_rshift_unsupported_returns_not_implemented(self):
        assert Int8(1).__rshift__(3.14) is NotImplemented

    def test_rrshift_unsupported_returns_not_implemented(self):
        assert Int8(1).__rrshift__(3.14) is NotImplemented

    def test_rshift_type_preserved(self):
        assert type(UInt32(8) >> UInt32(1)) is UInt32


# ---------------------------------------------------------------------------
# Unary negation  (30+ cases)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntUnaryNeg:
    @pytest.mark.parametrize("cls,value,expected", [
        # Int8
        (Int8,    0,     0), (Int8,    1,    -1), (Int8,   -1,     1),
        (Int8,  127,  -127), (Int8, -127,   127), (Int8, -128,  -128),
        (Int8,   50,   -50), (Int8,  -50,    50),
        # Int16
        (Int16,     0,     0), (Int16,     1,    -1), (Int16,    -1,     1),
        (Int16, 32767, -32767), (Int16, -32767, 32767), (Int16, -32768, -32768),
        # Int32
        (Int32,          0,          0), (Int32,          1,         -1),
        (Int32, 2147483647, -2147483647), (Int32, -2147483647, 2147483647),
        (Int32, -2147483648, -2147483648),
        # Int64
        (Int64,                   0,                    0),
        (Int64,                   1,                   -1),
        (Int64,  9223372036854775807, -9223372036854775807),
        (Int64, -9223372036854775808, -9223372036854775808),
        # UInt8 (neg wraps as unsigned)
        (UInt8,   0,   0), (UInt8,   1, 255), (UInt8, 128, 128),
        (UInt8, 255,   1), (UInt8,  64, 192), (UInt8, 100, 156),
        # UInt16
        (UInt16,   1, 65535), (UInt16, 0, 0),
        # UInt32
        (UInt32, 1, 4294967295),
        # UInt64
        (UInt64, 1, 18446744073709551615),
    ])
    def test_neg(self, cls, value, expected):
        assert int(-cls(value)) == expected


# ---------------------------------------------------------------------------
# Unary positive  (30+ cases, identity)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntUnaryPos:
    @pytest.mark.parametrize("cls,value", [
        (Int8, 0), (Int8, 1), (Int8, -1), (Int8, 127), (Int8, -128), (Int8, 42),
        (Int16, 0), (Int16, 32767), (Int16, -32768), (Int16, -1), (Int16, 100),
        (Int32, 0), (Int32, 2147483647), (Int32, -2147483648), (Int32, -1),
        (Int64, 0), (Int64, 9223372036854775807), (Int64, -9223372036854775808),
        (Int64, -1), (Int64, 123456789),
        (UInt8, 0), (UInt8, 255), (UInt8, 128), (UInt8, 1), (UInt8, 99),
        (UInt16, 65535), (UInt16, 0), (UInt16, 32768),
        (UInt32, 4294967295), (UInt32, 0), (UInt32, 2147483648),
        (UInt64, 18446744073709551615), (UInt64, 0),
    ])
    def test_pos_is_identity(self, cls, value):
        x = cls(value)
        y = +x
        assert int(y) == int(x)
        assert type(y) is cls


# ---------------------------------------------------------------------------
# Immutability  (no in-place operators)
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntImmutability:
    def test_no_iadd(self):
        with pytest.raises(AttributeError):
            Int8(1).__iadd__(1)

    def test_no_isub(self):
        with pytest.raises(AttributeError):
            Int8(1).__isub__(1)

    def test_arithmetic_returns_new_object(self):
        x = Int8(10)
        y = x + Int8(5)
        assert int(x) == 10
        assert int(y) == 15

    def test_unary_returns_new_object(self):
        x = UInt8(100)
        y = -x
        assert int(x) == 100
        assert int(y) == 156


# ---------------------------------------------------------------------------
# NotImplemented coverage for all remaining operators
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntNotImplemented:
    """
    Ensure every operator returns NotImplemented (not raises) for unsupported
    types such as float.  This covers all ``return NotImplemented`` branches.
    """

    @pytest.mark.parametrize("method,arg", [
        # Comparisons
        ("__lt__",    3.14), ("__le__",    3.14),
        ("__gt__",    3.14), ("__ge__",    3.14),
        # Arithmetic – direct NotImplemented
        ("__add__",   3.14), ("__sub__",   3.14), ("__rsub__",  3.14),
        ("__mul__",   3.14),
        ("__floordiv__",  3.14), ("__rfloordiv__", 3.14),
        ("__truediv__",   3.14),
        # __rtruediv__ delegates to __rfloordiv__, covers line 341
        ("__rtruediv__",  3.14),
        ("__mod__",   3.14), ("__rmod__",  3.14),
        ("__pow__",   3.14), ("__rpow__",  3.14),
        # Shifts
        ("__lshift__",    3.14), ("__rlshift__",   3.14),
        ("__rshift__",    3.14), ("__rrshift__",   3.14),
        # Bitwise
        ("__and__",   3.14), ("__or__",    3.14), ("__xor__",   3.14),
    ])
    def test_returns_not_implemented(self, method, arg):
        result = getattr(Int8(5), method)(arg)
        assert result is NotImplemented

    def test_rpow_negative_exponent_raises(self):
        # Covers the ValueError branch inside __rpow__ (line 414)
        with pytest.raises(ValueError, match="negative exponent"):
            Int8(-1).__rpow__(2)


# ---------------------------------------------------------------------------
# Python int interoperability
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntWithPythonInt:
    def test_add_right(self):
        assert int(Int8(100) + 50) == -106

    def test_add_left(self):
        assert int(50 + Int8(100)) == -106

    def test_sub_right(self):
        assert int(UInt8(5) - 10) == 251

    def test_sub_left(self):
        assert int(5 - UInt8(10)) == 251

    def test_mul_right(self):
        assert int(Int8(10) * 13) == -126

    def test_mul_left(self):
        assert int(13 * Int8(10)) == -126

    def test_floordiv_right(self):
        assert int(Int8(-7) // 2) == -3

    def test_floordiv_left(self):
        assert int(-7 // Int8(2)) == -3

    def test_mod_right(self):
        assert int(Int8(-7) % 3) == -1

    def test_mod_left(self):
        assert int(-7 % Int8(3)) == -1

    def test_and_both_sides(self):
        assert int(UInt8(0xFF) & 0x0F) == 0x0F
        assert int(0x0F & UInt8(0xFF)) == 0x0F

    def test_or_both_sides(self):
        assert int(UInt8(0x0F) | 0xF0) == 0xFF
        assert int(0xF0 | UInt8(0x0F)) == 0xFF

    def test_xor_both_sides(self):
        assert int(UInt8(0xFF) ^ 0x0F) == 0xF0
        assert int(0xFF ^ UInt8(0x0F)) == 0xF0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntEdgeCases:
    def test_int8_min_negation_overflow(self):
        assert int(-Int8(-128)) == -128

    def test_int8_max_plus_one(self):
        assert int(Int8(127) + 1) == -128

    def test_uint8_max_plus_one(self):
        assert int(UInt8(255) + 1) == 0

    def test_int64_max_plus_one(self):
        assert int(Int64(9223372036854775807) + 1) == -9223372036854775808

    def test_uint64_max_plus_one(self):
        assert int(UInt64(18446744073709551615) + 1) == 0

    def test_signed_rshift_fills_ones(self):
        assert int(Int64(-1) >> Int64(63)) == -1

    def test_unsigned_rshift_fills_zeros(self):
        assert int(UInt64(18446744073709551615) >> UInt64(63)) == 1

    def test_large_int64_div_precision(self):
        # Float-based division would give wrong answer here
        x = Int64(9223372036854775807)
        assert int(x // Int64(2)) == 4611686018427387903

    def test_large_int64_mod_precision(self):
        assert int(Int64(9223372036854775807) % Int64(2)) == 1

    def test_uint64_large_mul_wraps(self):
        assert int(UInt64(1 << 63) * UInt64(2)) == 0

    def test_bitwise_not_unsigned_complement(self):
        for cls, min_val, max_val, _bits in _TYPE_INFO:
            if min_val == 0:  # unsigned
                assert int(~cls(42)) == max_val - 42

    def test_zero_to_zero(self):
        assert int(UInt8(0) ** UInt8(0)) == 1

    def test_mul_signed_min_by_minus_one(self):
        assert int(Int8(-128) * Int8(-1)) == -128

    def test_all_types_zero_falsy(self):
        for cls in _ALL_TYPES:
            assert not bool(cls(0))

    def test_from_pyfcstm_utils(self):
        from pyfcstm.utils import Int8 as I8, UInt8 as U8
        assert int(I8(127) + 1) == -128
        assert int(U8(255) + 1) == 0


# ---------------------------------------------------------------------------
# Z3 BitVec alignment
# ---------------------------------------------------------------------------

@pytest.mark.unittest
class TestFixedIntZ3BitVecAlignment:
    """
    Tests verifying exact alignment with Z3 ``BitVec`` semantics by converting
    operands to Z3 BitVec, computing results with the Z3 solver, then asserting
    that the :class:`_FixedInt` result matches in both **numeric value** and
    **bit width**.

    Operator correspondence (see module docstring for the full table):

    * ``//`` / ``/`` (signed) ↔ Z3 ``/`` (``bvsdiv``, truncate toward zero)
    * ``%`` (signed) ↔ Z3 ``SRem`` (``bvsrem``, sign follows dividend)
    * ``%`` (unsigned) ↔ Z3 ``URem`` (``bvurem``)
    * ``>>`` (signed) ↔ Z3 ``>>`` (``bvashr``, arithmetic, fills with sign bit)
    * ``>>`` (unsigned) ↔ Z3 ``LShR`` (``bvlshr``, logical, fills with 0)
    * ``<<`` ↔ Z3 ``<<`` (``bvshl``)

    .. note::

       Z3's ``%`` operator uses ``bvsmod`` (sign follows *divisor*), which differs
       from this module's ``__mod__`` (``SRem``/``URem``).
    """

    # ------------------------------------------------------------------
    # SDiv — INT_MIN // -1 wraps around (bvsdiv overflow)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("cls,min_val", [
        (Int8,  -128),
        (Int16, -32768),
        (Int32, -2147483648),
        (Int64, -9223372036854775808),
    ])
    def test_sdiv_int_min_over_neg1_wraps(self, cls, min_val):
        # Z3: BitVecVal(INT_MIN, n) / BitVecVal(-1, n) == INT_MIN  (bvsdiv overflow)
        a, b = cls(min_val), cls(-1)
        result = a // b
        bv_a, bv_b = _to_bitvec(a), _to_bitvec(b)
        _assert_z3_match(result, bv_a / bv_b)

    # ------------------------------------------------------------------
    # SDiv — truncation toward zero (not Python floor division)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("a,b,expected", [
        # Z3 bvsdiv vs Python // for negative operands
        (-7, 2, -3),     # bvsdiv truncates to -3; Python // gives -4
        (-7, 3, -2),     # bvsdiv truncates to -2; Python // gives -3
        (7, -3, -2),     # bvsdiv truncates to -2; Python // gives -3
        (-10, 3, -3),    # bvsdiv truncates to -3; Python // gives -4
        (-10, -3, 3),    # bvsdiv truncates to  3; Python // gives  3 (same)
    ])
    def test_sdiv_truncates_toward_zero(self, a, b, expected):
        # Z3: BitVecVal(a, 8) / BitVecVal(b, 8)  (bvsdiv)
        result = Int8(a) // Int8(b)
        bv_a = z3.BitVecVal(a, 8)
        bv_b = z3.BitVecVal(b, 8)
        _assert_z3_match(result, bv_a / bv_b)

    # ------------------------------------------------------------------
    # SRem (bvsrem) — sign follows dividend, NOT divisor
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("a,b,srem,note", [
        (-7, 3, -1, "Z3 % (bvsmod) gives  2; SRem gives -1"),
        (7, -3, 1, "Z3 % (bvsmod) gives -2; SRem gives  1"),
        (-7, -3, -1, "both give -1 here"),
        (-128, 3, -2, "Z3 % (bvsmod) gives  1; SRem gives -2"),
        (127, -128, 127, "Z3 % (bvsmod) gives -1; SRem gives 127"),
        (-128, 127, -1, "Z3 % (bvsmod) gives 126; SRem gives -1"),
    ])
    def test_signed_mod_matches_srem_not_smod(self, a, b, srem, note):
        # Z3 SRem(a, b) — sign of result follows the *dividend*
        result = Int8(a) % Int8(b)
        bv_a = z3.BitVecVal(a, 8)
        bv_b = z3.BitVecVal(b, 8)
        _assert_z3_match(result, z3.SRem(bv_a, bv_b))

    # ------------------------------------------------------------------
    # URem (bvurem) — standard unsigned remainder
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("a,b,urem,note", [
        (255, 3,   0, "URem=0 (255=85×3); Z3 % (bvsmod treating 255 as -1) gives 2"),
        (128, 3,   2, "URem=2 (128=42×3+2); Z3 % (bvsmod treating 128 as -128) gives 1"),
        (200, 7,   4, "URem=4 (200=28×7+4)"),
        (128, 127, 1, "URem=1; Z3 % (bvsmod) gives 126"),
    ])
    def test_unsigned_mod_matches_urem_not_smod(self, a, b, urem, note):
        # Z3 URem(a, b) — values treated as unsigned
        result = UInt8(a) % UInt8(b)
        bv_a = z3.BitVecVal(a, 8)
        bv_b = z3.BitVecVal(b, 8)
        _assert_z3_match(result, z3.URem(bv_a, bv_b))

    # ------------------------------------------------------------------
    # Arithmetic right shift — bvashr (fills with sign bit)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("value,shift,expected", [
        (-128, 7, -1),    # 0x80 >> 7 = 0xFF = -1
        (-1, 1, -1),      # 0xFF >> 1 = 0xFF = -1
        (  -1, 7,  -1),   # 0xFF >> 7 = 0xFF = -1
        ( -64, 2, -16),   # 0xC0 >> 2 = 0xF0 = -16
        (-100, 2, -25),   # 0x9C >> 2 = 0xE7 = -25
        (-128, 8,  -1),   # shift >= width: arithmetic fills, Z3 bvashr gives -1
    ])
    def test_signed_rshift_arithmetic_matches_z3_bvashr(self, value, shift, expected):
        # Z3: BitVecVal(value, 8) >> BitVecVal(shift, 8)  (bvashr)
        result = Int8(value) >> Int8(shift)
        bv_v = z3.BitVecVal(value, 8)
        bv_s = z3.BitVecVal(shift, 8)
        _assert_z3_match(result, bv_v >> bv_s)

    # ------------------------------------------------------------------
    # Logical right shift — bvlshr / LShR (fills with 0)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("value,shift,expected", [
        (128, 7, 1),    # 0x80 >> 7 = 0x01
        (255, 7, 1),    # 0xFF >> 7 = 0x01
        (200, 3, 25),   # 0xC8 >> 3 = 0x19 = 25
        (255, 8, 0),    # shift >= width: logical gives 0
        (128, 8, 0),    # shift >= width: logical gives 0
    ])
    def test_unsigned_rshift_logical_matches_z3_lshr(self, value, shift, expected):
        # Z3: LShR(BitVecVal(value, 8), BitVecVal(shift, 8))  (bvlshr)
        result = UInt8(value) >> UInt8(shift)
        bv_v = z3.BitVecVal(value, 8)
        bv_s = z3.BitVecVal(shift, 8)
        _assert_z3_match(result, z3.LShR(bv_v, bv_s))

    # ------------------------------------------------------------------
    # _FixedInt shift amounts treated as unsigned bit patterns (bvshl / bvashr / bvlshr)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("cls,value,neg_shift_val,expected_lshift,expected_rshift", [
        # Int8(-1) as shift = bit pattern 0xFF = 255 unsigned (>= 8 → all-zero or sign-fill)
        (Int8, 1, -1, 0, 0),       # 1 << 255 = 0; 1 >> 255 (arith) = 0
        (Int8, -1, -1, 0, -1),     # (-1) << 255 = 0; (-1) >> 255 (arith) = -1
        (UInt8, 1, -1, 0, 0),      # 1 << 255 = 0; 1 >> 255 (logical) = 0
        (UInt8, 255, -1, 0, 0),    # 255 << 255 = 0; 255 >> 255 (logical) = 0
        # Int8(-8) as shift = bit pattern 0xF8 = 248 unsigned (>= 8 → all-zero or sign-fill)
        (Int8, 1, -8, 0, 0),
        (Int8, -1, -8, 0, -1),
    ])
    def test_negative_fixedint_shift_treated_as_unsigned(
        self, cls, value, neg_shift_val, expected_lshift, expected_rshift
    ):
        """
        Z3 interprets a ``BitVec`` shift amount as unsigned.
        ``Int8(-1)`` has bit pattern ``0xFF`` = 255, so shifting by ``Int8(-1)``
        is equivalent to shifting by 255 positions.
        """
        shift = Int8(neg_shift_val)
        bv_value = _to_bitvec(cls(value))
        bv_shift = _to_bitvec(shift)

        lshift_result = cls(value) << shift
        _assert_z3_match(lshift_result, bv_value << bv_shift)

        rshift_result = cls(value) >> shift
        z3_rshift = bv_value >> bv_shift if cls._is_signed else z3.LShR(bv_value, bv_shift)
        _assert_z3_match(rshift_result, z3_rshift)

    # ------------------------------------------------------------------
    # Negation overflow: -INT_MIN == INT_MIN  (Z3 unary -)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("cls,min_val", [
        (Int8,  -128),
        (Int16, -32768),
        (Int32, -2147483648),
        (Int64, -9223372036854775808),
    ])
    def test_neg_int_min_wraps(self, cls, min_val):
        # Z3: -BitVecVal(INT_MIN, n) == INT_MIN  (two's complement overflow)
        v = cls(min_val)
        result = -v
        bv = _to_bitvec(v)
        _assert_z3_match(result, -bv)

    # ------------------------------------------------------------------
    # Unsigned negation: -UInt(x) == (2^N - x) % 2^N  (Z3 unary -)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("cls,value,expected", [
        (UInt8,   1, 255),
        (UInt8, 127, 129),
        (UInt8, 128, 128),
        (UInt8, 255,   1),
        (UInt16,     1, 65535),
        (UInt32,     1, 4294967295),
        (UInt64,     1, 18446744073709551615),
    ])
    def test_unsigned_neg_wraps(self, cls, value, expected):
        # Z3: -BitVecVal(value, N) == (2^N - value) % 2^N
        v = cls(value)
        result = -v
        bv = _to_bitvec(v)
        _assert_z3_match(result, -bv)

    # ------------------------------------------------------------------
    # Cross-type arithmetic: result type == left operand type
    # Rule: LeftType(a) op RightType(b)  ≡  LeftType(int(a) op int(b))
    # Z3 equivalent: convert right's Python-int value to left's bit width,
    # then apply the Z3 operation — correct because both are mod 2^left_bits.
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("cls_l, a, cls_r, b", [
        # same signedness, different widths
        (Int8,    50,  Int16,   100),   # 150 -> -106
        (Int8,   -50,  Int16,   100),   # 50
        (Int8,   127,  Int16,     1),   # 128 -> -128
        (Int16, 32767, Int8,      1),   # 32768 -> -32768
        (Int16,    -1, Int8,     10),   # 9
        (Int32, 2147483647, Int16,  1), # overflow
        (Int64, 9223372036854775807, Int32, 1),   # overflow
        (UInt8,  250,  UInt16,   10),   # 260 -> 4
        (UInt8,  255,  UInt32,    1),   # overflow -> 0
        (UInt16, 65535, UInt8,    1),   # overflow -> 0
        (UInt32, 4294967295, UInt64, 1),  # overflow -> 0
        (UInt64, 18446744073709551615, UInt8, 1),  # overflow -> 0
        # mixed signedness
        (Int8,    -1,  UInt8,    1),    # 0
        (Int8,    -1,  UInt16,   2),    # 1
        (UInt8,  200,  Int8,   -10),    # 190
        (UInt8,  255,  Int8,     1),    # 256 -> 0
        (Int16,   -1,  UInt8,  255),    # 254
        (UInt16, 100,  Int8,   -50),    # 50
        (UInt32, 100,  Int16, -200),    # -100 -> 4294967196
        (Int32,   50,  UInt32,  100),   # 150
    ])
    def test_cross_type_add(self, cls_l, a, cls_r, b):
        result = cls_l(a) + cls_r(b)
        left_bits = _fixed_bit_width(cls_l(a))
        bv_a = _to_bitvec(cls_l(a))
        bv_b = _to_bitvec_width(cls_r(b), left_bits)
        _assert_z3_match(result, bv_a + bv_b)

    @pytest.mark.parametrize("cls_l, a, cls_r, b", [
        # same signedness, different widths
        (Int8,    10,  Int16,    20),   # -10
        (Int8,  -128,  Int16,     1),   # -129 -> 127
        (Int8,   127,  Int16,    -1),   # 128 -> -128
        (Int16, -32768, Int8,     1),   # underflow -> 32767
        (Int32, -2147483648, Int16,  1),  # underflow -> 2147483647
        (Int64, -9223372036854775808, Int8, 1),  # underflow -> max
        (UInt8,  255,  UInt16, 256),    # 255 - 256 = -1 -> 255
        (UInt16,   0,  UInt8,    1),    # 0 - 1 -> 65535
        (UInt32,   0,  UInt64,   1),    # wraparound -> 4294967295
        (UInt64,   0,  UInt8,    1),    # wraparound -> max
        # mixed signedness
        (Int8,     0,  UInt8,    1),    # -1
        (Int8,   127,  UInt8,  128),    # -1
        (UInt8,    5,  Int8,    10),    # 5-10=-5 -> 251
        (UInt8,  100,  Int16,  200),    # -100 -> 156
        (UInt8,    0,  Int16,    1),    # -1 -> 255
        (Int32,   50,  UInt32,  100),   # -50
        (UInt32, 100,  Int16,  -200),   # 300 -> 300
        (Int16,  100,  UInt32, 200),    # -100
        (UInt64,  10,  Int8,    20),    # -10 -> 18446744073709551606
    ])
    def test_cross_type_sub(self, cls_l, a, cls_r, b):
        result = cls_l(a) - cls_r(b)
        left_bits = _fixed_bit_width(cls_l(a))
        bv_a = _to_bitvec(cls_l(a))
        bv_b = _to_bitvec_width(cls_r(b), left_bits)
        _assert_z3_match(result, bv_a - bv_b)

    @pytest.mark.parametrize("cls_l, a, cls_r, b", [
        # same signedness, different widths
        (Int8,    10,  Int16,    13),   # 130 -> -126
        (Int8,    -1,  Int16,    -1),   # 1
        (Int8,     2,  Int32,    64),   # 128 -> -128
        (Int16,  100,  Int8,     50),   # 5000
        (Int16,  200,  Int8,    200),   # 40000 -> -25536
        (Int32, 100000, Int16,  100),   # 10000000
        (Int64, 4611686018427387904, Int32, 2),  # overflow -> min
        (UInt8,   16,  UInt16,   16),   # 256 -> 0
        (UInt8,  100,  UInt16,    3),   # 300 -> 44
        (UInt16, 1000, UInt8,   256),   # 1000 * 256 = 256000 -> 256000 % 65536
        (UInt32, 100000, UInt64, 100),  # 10000000
        (UInt64, 9223372036854775808, UInt8, 2),  # overflow -> 0
        # mixed signedness
        (Int8,   -10,  UInt8,    20),   # -200 -> 56
        (Int8,   127,  UInt16,  127),   # 16129 % 256 = 1
        (UInt8,  200,  Int8,     -2),   # -400 -> 112
        (UInt16, 1000, Int8,     -3),   # -3000 -> 62536
        (UInt32, 1000, Int16,  -100),   # -100000 -> 4294867296
        (Int32,  100,  UInt8,   255),   # 25500
        (Int16, -100,  UInt8,    10),   # -1000
    ])
    def test_cross_type_mul(self, cls_l, a, cls_r, b):
        result = cls_l(a) * cls_r(b)
        left_bits = _fixed_bit_width(cls_l(a))
        bv_a = _to_bitvec(cls_l(a))
        bv_b = _to_bitvec_width(cls_r(b), left_bits)
        _assert_z3_match(result, bv_a * bv_b)
