import pytest
from unittest.mock import patch

from pyfcstm.utils.parse import parse_value, parse_key_value_pairs


@pytest.mark.unittest
class TestParseValue:
    """Test parse_value function with various type hints and auto mode."""

    # Auto mode tests
    def test_auto_mode_int(self):
        """Test auto mode parsing integers."""
        assert parse_value('42') == 42
        assert parse_value('0') == 0
        assert parse_value('-123') == -123

    def test_auto_mode_float(self):
        """Test auto mode parsing floats."""
        assert parse_value('3.14') == 3.14
        assert parse_value('0.0') == 0.0
        assert parse_value('-2.5') == -2.5

    def test_auto_mode_quoted_string(self):
        """Test auto mode parsing quoted strings."""
        assert parse_value('"hello"') == 'hello'
        assert parse_value("'world'") == 'world'
        assert parse_value('"hello world"') == 'hello world'

    def test_auto_mode_quoted_string_with_escapes(self):
        """Test auto mode parsing quoted strings with escape sequences."""
        assert parse_value('"hello\\nworld"') == 'hello\nworld'
        assert parse_value('"tab\\there"') == 'tab\there'
        assert parse_value('"quote\\"test"') == 'quote"test'
        assert parse_value('"backslash\\\\"') == 'backslash\\'

    def test_auto_mode_none(self):
        """Test auto mode parsing None values."""
        assert parse_value('none') is None
        assert parse_value('None') is None
        assert parse_value('NONE') is None
        assert parse_value('null') is None
        assert parse_value('NULL') is None

    def test_auto_mode_bool(self):
        """Test auto mode parsing boolean values."""
        assert parse_value('true') is True
        assert parse_value('True') is True
        assert parse_value('TRUE') is True
        assert parse_value('yes') is True
        assert parse_value('YES') is True
        assert parse_value('false') is False
        assert parse_value('False') is False
        assert parse_value('FALSE') is False
        assert parse_value('no') is False
        assert parse_value('NO') is False

    def test_auto_mode_unquoted_string(self):
        """Test auto mode parsing unquoted strings."""
        assert parse_value('hello') == 'hello'
        assert parse_value('hello_world') == 'hello_world'
        assert parse_value('some-value') == 'some-value'

    # Explicit type hints - type objects
    def test_explicit_int_type(self):
        """Test parsing with explicit int type."""
        assert parse_value('42', int) == 42
        assert parse_value('0', int) == 0
        assert parse_value('-123', int) == -123

    def test_explicit_int_type_invalid(self):
        """Test parsing invalid int values."""
        with pytest.raises(ValueError, match="Expected int"):
            parse_value('hello', int)
        with pytest.raises(ValueError, match="Expected int"):
            parse_value('3.14', int)

    def test_explicit_float_type(self):
        """Test parsing with explicit float type."""
        assert parse_value('3.14', float) == 3.14
        assert parse_value('0.0', float) == 0.0
        assert parse_value('-2.5', float) == -2.5

    def test_explicit_float_type_invalid(self):
        """Test parsing invalid float values."""
        with pytest.raises(ValueError, match="Expected float"):
            parse_value('hello', float)

    def test_explicit_bool_type(self):
        """Test parsing with explicit bool type."""
        assert parse_value('true', bool) is True
        assert parse_value('yes', bool) is True
        assert parse_value('1', bool) is True
        assert parse_value('false', bool) is False
        assert parse_value('no', bool) is False
        assert parse_value('0', bool) is False

    def test_explicit_bool_type_invalid(self):
        """Test parsing invalid bool values."""
        with pytest.raises(ValueError, match="Expected bool"):
            parse_value('hello', bool)
        with pytest.raises(ValueError, match="Expected bool"):
            parse_value('42', bool)

    def test_explicit_str_type(self):
        """Test parsing with explicit str type."""
        assert parse_value('hello', str) == 'hello'
        assert parse_value('"hello world"', str) == 'hello world'
        assert parse_value("'test'", str) == 'test'

    def test_explicit_str_type_with_escapes(self):
        """Test parsing str with escape sequences."""
        assert parse_value('"hello\\nworld"', str) == 'hello\nworld'
        assert parse_value('"tab\\there"', str) == 'tab\there'

    def test_explicit_none_type_with_type_none(self):
        """Test parsing with type(None)."""
        assert parse_value('none', type(None)) is None
        assert parse_value('null', type(None)) is None

    def test_explicit_none_type_with_none(self):
        """Test parsing with None."""
        assert parse_value('none', None) is None
        assert parse_value('null', None) is None

    def test_explicit_none_type_invalid(self):
        """Test parsing invalid None values."""
        with pytest.raises(ValueError, match="Expected None"):
            parse_value('hello', type(None))
        with pytest.raises(ValueError, match="Expected None"):
            parse_value('hello', None)

    # Explicit type hints - string representations
    def test_explicit_int_string(self):
        """Test parsing with 'int' string."""
        assert parse_value('42', 'int') == 42
        assert parse_value('0', 'int') == 0

    def test_explicit_float_string(self):
        """Test parsing with 'float' string."""
        assert parse_value('3.14', 'float') == 3.14
        assert parse_value('0.0', 'float') == 0.0

    def test_explicit_bool_string(self):
        """Test parsing with 'bool' string."""
        assert parse_value('true', 'bool') is True
        assert parse_value('false', 'bool') is False

    def test_explicit_str_string(self):
        """Test parsing with 'str' string."""
        assert parse_value('hello', 'str') == 'hello'
        assert parse_value('"hello world"', 'str') == 'hello world'

    def test_explicit_none_string(self):
        """Test parsing with 'none' string."""
        assert parse_value('none', 'none') is None
        assert parse_value('null', 'none') is None

    def test_explicit_none_string_invalid(self):
        """Test parsing invalid None with 'none' string."""
        with pytest.raises(ValueError, match="Expected None"):
            parse_value('hello', 'none')

    def test_unknown_type_string(self):
        """Test parsing with unknown type string."""
        with pytest.raises(ValueError, match="Unknown type"):
            parse_value('42', 'unknown')

    # Tuple types - variable length
    def test_tuple_str_variable_length(self):
        """Test parsing variable length tuple of strings."""
        assert parse_value('a,b,c', 'tuple[str, ...]') == ('a', 'b', 'c')
        assert parse_value('name,path', 'tuple[str, ...]') == ('name', 'path')
        assert parse_value('single', 'tuple[str, ...]') == ('single',)

    def test_tuple_int_variable_length(self):
        """Test parsing variable length tuple of ints."""
        assert parse_value('1,2,3', 'tuple[int, ...]') == (1, 2, 3)
        assert parse_value('42', 'tuple[int, ...]') == (42,)

    def test_tuple_float_variable_length(self):
        """Test parsing variable length tuple of floats."""
        assert parse_value('1.0,2.5,3.14', 'tuple[float, ...]') == (1.0, 2.5, 3.14)

    def test_tuple_bool_variable_length(self):
        """Test parsing variable length tuple of bools."""
        assert parse_value('true,false,yes', 'tuple[bool, ...]') == (True, False, True)

    # Tuple types - fixed length
    def test_tuple_fixed_length_str_int(self):
        """Test parsing fixed length tuple with str and int."""
        assert parse_value('name,42', 'tuple[str, int]') == ('name', 42)

    def test_tuple_fixed_length_str_float(self):
        """Test parsing fixed length tuple with str and float."""
        assert parse_value('value,3.14', 'tuple[str, float]') == ('value', 3.14)

    def test_tuple_fixed_length_int_bool(self):
        """Test parsing fixed length tuple with int and bool."""
        assert parse_value('42,true', 'tuple[int, bool]') == (42, True)

    def test_tuple_fixed_length_mismatch(self):
        """Test parsing fixed length tuple with wrong number of elements."""
        with pytest.raises(ValueError, match="Expected 2 elements"):
            parse_value('a,b,c', 'tuple[str, int]')
        with pytest.raises(ValueError, match="Expected 3 elements"):
            parse_value('a,b', 'tuple[str, int, float]')

    def test_tuple_fixed_length_invalid_type(self):
        """Test parsing fixed length tuple with invalid element type."""
        with pytest.raises(ValueError, match="Expected int"):
            parse_value('name,hello', 'tuple[str, int]')

    # Unsupported type
    def test_unsupported_type(self):
        """Test parsing with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported type"):
            parse_value('42', list)

    def test_escape_sequence_decode_failure(self):
        """Test handling of invalid escape sequences that fail to decode."""
        # This tests the exception handler in _decode_string
        # We need to mock codecs.decode to raise an exception
        with patch('pyfcstm.utils.parse.codecs.decode', side_effect=Exception('decode error')):
            # When decode fails, the function should return the string as-is
            result = parse_value('"test"', str)
            assert result == 'test'

    def test_tuple_with_none_element(self):
        """Test parsing tuple with None element using type(None)."""
        # This tests the _parse_single_value path for type(None) in tuple parsing
        assert parse_value('none,test', 'tuple[none, str]') == (None, 'test')
        assert parse_value('test,none', 'tuple[str, none]') == ('test', None)

    def test_tuple_with_none_element_invalid(self):
        """Test parsing tuple with invalid None element."""
        # This tests the error path in _parse_single_value for type(None)
        with pytest.raises(ValueError, match="Expected None"):
            parse_value('invalid,test', 'tuple[none, str]')


@pytest.mark.unittest
class TestParseKeyValuePairs:
    """Test parse_key_value_pairs function."""

    def test_auto_mode_all_fields(self):
        """Test parsing with auto mode for all fields."""
        result = parse_key_value_pairs(
            ('show_events=true', 'max_depth=2', 'name=hello')
        )
        assert result == {'show_events': True, 'max_depth': 2, 'name': 'hello'}

    def test_with_type_hints_type_objects(self):
        """Test parsing with type hints as type objects."""
        result = parse_key_value_pairs(
            ('count=42', 'ratio=3.14', 'enabled=true', 'name=test'),
            type_hints={'count': int, 'ratio': float, 'enabled': bool, 'name': str}
        )
        assert result == {'count': 42, 'ratio': 3.14, 'enabled': True, 'name': 'test'}

    def test_with_type_hints_string_representations(self):
        """Test parsing with type hints as string representations."""
        result = parse_key_value_pairs(
            ('count=42', 'ratio=3.14', 'enabled=true'),
            type_hints={'count': 'int', 'ratio': 'float', 'enabled': 'bool'}
        )
        assert result == {'count': 42, 'ratio': 3.14, 'enabled': True}

    def test_with_tuple_type_hints(self):
        """Test parsing with tuple type hints."""
        result = parse_key_value_pairs(
            ('tags=a,b,c', 'coords=1.0,2.5'),
            type_hints={'tags': 'tuple[str, ...]', 'coords': 'tuple[float, ...]'}
        )
        assert result == {'tags': ('a', 'b', 'c'), 'coords': (1.0, 2.5)}

    def test_mixed_auto_and_explicit(self):
        """Test parsing with mixed auto and explicit type hints."""
        result = parse_key_value_pairs(
            ('count=42', 'name=test', 'tags=a,b'),
            type_hints={'count': int, 'tags': 'tuple[str, ...]'}
        )
        assert result == {'count': 42, 'name': 'test', 'tags': ('a', 'b')}

    def test_quoted_strings(self):
        """Test parsing with quoted strings."""
        result = parse_key_value_pairs(
            ('name="My App"', 'desc="Hello World"'),
            type_hints={'name': str, 'desc': str}
        )
        assert result == {'name': 'My App', 'desc': 'Hello World'}

    def test_escape_sequences(self):
        """Test parsing with escape sequences."""
        result = parse_key_value_pairs(
            ('text="hello\\nworld"',),
            type_hints={'text': str}
        )
        assert result == {'text': 'hello\nworld'}

    def test_none_values(self):
        """Test parsing with None values."""
        result = parse_key_value_pairs(
            ('value=none', 'other=null'),
            type_hints={'value': None, 'other': type(None)}
        )
        assert result == {'value': None, 'other': None}

    def test_invalid_format_no_equals(self):
        """Test parsing with invalid format (no equals sign)."""
        with pytest.raises(ValueError, match="Option must be in 'key=value' format"):
            parse_key_value_pairs(('invalid',))

    def test_invalid_format_multiple_pairs(self):
        """Test parsing with one invalid pair among valid ones."""
        with pytest.raises(ValueError, match="Option must be in 'key=value' format"):
            parse_key_value_pairs(('valid=true', 'invalid', 'another=42'))

    def test_parsing_error_propagation(self):
        """Test that parsing errors are properly propagated."""
        with pytest.raises(ValueError, match="Failed to parse option 'count'"):
            parse_key_value_pairs(
                ('count=hello',),
                type_hints={'count': int}
            )

    def test_empty_tuple(self):
        """Test parsing with empty tuple."""
        result = parse_key_value_pairs(())
        assert result == {}

    def test_none_type_hints(self):
        """Test parsing with None type_hints."""
        result = parse_key_value_pairs(
            ('count=42', 'name=test'),
            type_hints=None
        )
        assert result == {'count': 42, 'name': 'test'}

    def test_whitespace_handling(self):
        """Test parsing with whitespace around keys and values."""
        result = parse_key_value_pairs(
            ('  count = 42  ', ' name = test '),
        )
        assert result == {'count': 42, 'name': 'test'}

    def test_complex_example(self):
        """Test complex example with multiple types."""
        result = parse_key_value_pairs(
            ('name="My App"', 'version=1.0', 'debug=false', 'ports=8080,8081,8082'),
            type_hints={'name': str, 'version': float, 'debug': bool, 'ports': 'tuple[int, ...]'}
        )
        assert result == {
            'name': 'My App',
            'version': 1.0,
            'debug': False,
            'ports': (8080, 8081, 8082)
        }


@pytest.mark.unittest
class TestOptionalSupport:
    """Test optional type support."""

    def test_optional_without_type_parameter(self):
        """Test optional without type parameter (equivalent to optional[auto])."""
        assert parse_value('none', 'optional') is None
        assert parse_value('null', 'optional') is None
        assert parse_value('42', 'optional') == 42
        assert parse_value('3.14', 'optional') == 3.14
        assert parse_value('true', 'optional') is True
        assert parse_value('hello', 'optional') == 'hello'

    def test_optional_with_str(self):
        """Test optional[str]."""
        assert parse_value('none', 'optional[str]') is None
        assert parse_value('null', 'optional[str]') is None
        assert parse_value('hello', 'optional[str]') == 'hello'
        assert parse_value('"hello world"', 'optional[str]') == 'hello world'

    def test_optional_with_int(self):
        """Test optional[int]."""
        assert parse_value('none', 'optional[int]') is None
        assert parse_value('42', 'optional[int]') == 42
        assert parse_value('0', 'optional[int]') == 0

    def test_optional_with_float(self):
        """Test optional[float]."""
        assert parse_value('none', 'optional[float]') is None
        assert parse_value('3.14', 'optional[float]') == 3.14

    def test_optional_with_bool(self):
        """Test optional[bool]."""
        assert parse_value('none', 'optional[bool]') is None
        assert parse_value('true', 'optional[bool]') is True
        assert parse_value('false', 'optional[bool]') is False

    def test_optional_with_invalid_value(self):
        """Test optional with invalid value for inner type."""
        with pytest.raises(ValueError, match="Expected int"):
            parse_value('hello', 'optional[int]')

    def test_optional_case_insensitive(self):
        """Test optional is case insensitive."""
        assert parse_value('none', 'Optional[str]') is None
        assert parse_value('none', 'OPTIONAL[int]') is None


@pytest.mark.unittest
class TestAutoInTuple:
    """Test auto type in tuple support."""

    def test_tuple_auto_variable_length(self):
        """Test tuple[auto, ...] with variable length."""
        assert parse_value('42,hello,3.14', 'tuple[auto, ...]') == (42, 'hello', 3.14)
        assert parse_value('true,42,none', 'tuple[auto, ...]') == (True, 42, None)
        assert parse_value('"hello",world', 'tuple[auto, ...]') == ('hello', 'world')

    def test_tuple_auto_fixed_length(self):
        """Test tuple with auto in fixed positions."""
        assert parse_value('42,hello,true', 'tuple[auto, auto, auto]') == (42, 'hello', True)
        assert parse_value('42,hello', 'tuple[int, auto]') == (42, 'hello')
        assert parse_value('hello,42', 'tuple[auto, int]') == ('hello', 42)

    def test_tuple_mixed_auto_and_explicit(self):
        """Test tuple with mixed auto and explicit types."""
        assert parse_value('42,hello,3.14', 'tuple[int, auto, float]') == (42, 'hello', 3.14)
        assert parse_value('hello,42,true', 'tuple[auto, int, bool]') == ('hello', 42, True)

    def test_tuple_auto_with_quoted_strings(self):
        """Test tuple[auto, ...] with quoted strings."""
        assert parse_value('"hello world",42', 'tuple[auto, ...]') == ('hello world', 42)

    def test_tuple_auto_case_insensitive(self):
        """Test auto is case insensitive in tuple."""
        assert parse_value('42,hello', 'tuple[Auto, ...]') == (42, 'hello')
        assert parse_value('42,hello', 'tuple[AUTO, auto]') == (42, 'hello')


@pytest.mark.unittest
class TestComplexCombinations:
    """Test complex combinations of optional and auto."""

    def test_optional_in_parse_key_value_pairs(self):
        """Test optional types in parse_key_value_pairs."""
        result = parse_key_value_pairs(
            ('name=none', 'count=42', 'value=none'),
            type_hints={'name': 'optional[str]', 'count': 'optional[int]', 'value': 'optional'}
        )
        assert result == {'name': None, 'count': 42, 'value': None}

    def test_auto_in_parse_key_value_pairs(self):
        """Test auto in tuple within parse_key_value_pairs."""
        result = parse_key_value_pairs(
            ('tags=a,b,c', 'mixed=42,hello,3.14'),
            type_hints={'tags': 'tuple[auto, ...]', 'mixed': 'tuple[int, auto, float]'}
        )
        assert result == {'tags': ('a', 'b', 'c'), 'mixed': (42, 'hello', 3.14)}

    def test_combined_optional_and_auto(self):
        """Test combining optional and auto in complex scenarios."""
        result = parse_key_value_pairs(
            ('name=none', 'tags=42,hello,true', 'count=100'),
            type_hints={'name': 'optional[str]', 'tags': 'tuple[auto, ...]', 'count': 'optional[int]'}
        )
        assert result == {'name': None, 'tags': (42, 'hello', True), 'count': 100}

    def test_auto_type_in_parse_single_value(self):
        """Test that 'auto' type works correctly in _parse_single_value."""
        # This tests the 'auto' branch in _parse_single_value (line 338)
        # which is called when using auto in tuple elements
        assert parse_value('42,hello,3.14', 'tuple[auto, auto, auto]') == (42, 'hello', 3.14)

    def test_type_none_in_parse_single_value(self):
        """Test that type(None) works correctly in _parse_single_value."""
        # This tests the type(None) branch in _parse_single_value (lines 342-344)
        # which is called when using 'none' type in tuple elements
        assert parse_value('none,test', 'tuple[none, str]') == (None, 'test')

        # Test the error path
        with pytest.raises(ValueError, match="Expected None"):
            parse_value('invalid,test', 'tuple[none, str]')


@pytest.mark.unittest
class TestWhitespaceInsensitivity:
    """Test whitespace insensitivity in tuple type specifications."""

    def test_tuple_variable_length_whitespace_variations(self):
        """Test tuple[T, ...] with various whitespace patterns."""
        # Standard format
        assert parse_value('a,b,c', 'tuple[str, ...]') == ('a', 'b', 'c')
        # No spaces
        assert parse_value('a,b,c', 'tuple[str,...]') == ('a', 'b', 'c')
        # Extra spaces
        assert parse_value('a,b,c', 'tuple[str , ...]') == ('a', 'b', 'c')
        assert parse_value('a,b,c', 'tuple[ str , ... ]') == ('a', 'b', 'c')
        assert parse_value('a,b,c', 'tuple[  str  ,  ...  ]') == ('a', 'b', 'c')

    def test_tuple_fixed_length_whitespace_variations(self):
        """Test tuple[T1, T2] with various whitespace patterns."""
        # Standard format
        assert parse_value('hello,42', 'tuple[str, int]') == ('hello', 42)
        # No spaces
        assert parse_value('hello,42', 'tuple[str,int]') == ('hello', 42)
        # Extra spaces
        assert parse_value('hello,42', 'tuple[str , int]') == ('hello', 42)
        assert parse_value('hello,42', 'tuple[ str , int ]') == ('hello', 42)
        assert parse_value('hello,42', 'tuple[  str  ,  int  ]') == ('hello', 42)

    def test_tuple_auto_whitespace_variations(self):
        """Test tuple with auto and various whitespace patterns."""
        assert parse_value('42,hello', 'tuple[auto, ...]') == (42, 'hello')
        assert parse_value('42,hello', 'tuple[auto,...]') == (42, 'hello')
        assert parse_value('42,hello', 'tuple[ auto , ... ]') == (42, 'hello')
        assert parse_value('42,hello', 'tuple[  auto  ,  ...  ]') == (42, 'hello')

    def test_tuple_mixed_types_whitespace_variations(self):
        """Test tuple with mixed types and various whitespace patterns."""
        assert parse_value('42,hello,3.14', 'tuple[int, auto, float]') == (42, 'hello', 3.14)
        assert parse_value('42,hello,3.14', 'tuple[int,auto,float]') == (42, 'hello', 3.14)
        assert parse_value('42,hello,3.14', 'tuple[ int , auto , float ]') == (42, 'hello', 3.14)
