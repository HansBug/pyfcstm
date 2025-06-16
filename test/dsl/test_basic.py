import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLBasicChainID:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        ('x', ChainID(path=['x'])),  # Simple identifier with a single letter
        ('foo', ChainID(path=['foo'])),  # Simple identifier with multiple letters
        ('_test', ChainID(path=['_test'])),  # Identifier starting with underscore
        ('var1', ChainID(path=['var1'])),  # Identifier with letters and numbers
        ('foo.bar', ChainID(path=['foo', 'bar'])),  # Two identifiers connected with a dot
        ('a.b.c', ChainID(path=['a', 'b', 'c'])),  # Three identifiers in a chain
        ('model.layer.weight', ChainID(path=['model', 'layer', 'weight'])),
        # Common use case for accessing nested properties
        ('this_is_snake_case', ChainID(path=['this_is_snake_case'])),  # Snake case identifier
        ('camelCase', ChainID(path=['camelCase'])),  # Camel case identifier
        ('PascalCase', ChainID(path=['PascalCase'])),  # Pascal case identifier
        ('_private.method', ChainID(path=['_private', 'method'])),
        # Identifier starting with underscore followed by dot and another identifier
        ('x1.y2.z3', ChainID(path=['x1', 'y2', 'z3'])),  # Chain of identifiers containing numbers
        ('very_long_identifier.with.many.parts', ChainID(path=['very_long_identifier', 'with', 'many', 'parts'])),
        # Long chain with multiple components
        ('a_1.b_2.c_3', ChainID(path=['a_1', 'b_2', 'c_3'])),  # Chain with underscores and numbers
        ('Class.static_method', ChainID(path=['Class', 'static_method'])),
        # Common pattern for accessing static methods
        ('package.subpackage.Class', ChainID(path=['package', 'subpackage', 'Class'])),
        # Common import or qualification pattern
        ('x', ChainID(path=['x'])),  # Minimal valid chain_id with just one identifier
        ('a.b.c.d.e.f.g', ChainID(path=['a', 'b', 'c', 'd', 'e', 'f', 'g'])),  # Long chain with many segments
        ('_._._', ChainID(path=['_', '_', '_'])),  # Chain of underscore identifiers
        ('A1.B2.C3', ChainID(path=['A1', 'B2', 'C3'])),  # Chain with uppercase letters and numbers
    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name='chain_id') == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        ('x', 'x'),  # Simple identifier with a single letter
        ('foo', 'foo'),  # Simple identifier with multiple letters
        ('_test', '_test'),  # Identifier starting with underscore
        ('var1', 'var1'),  # Identifier with letters and numbers
        ('foo.bar', 'foo.bar'),  # Two identifiers connected with a dot
        ('a.b.c', 'a.b.c'),  # Three identifiers in a chain
        ('model.layer.weight', 'model.layer.weight'),  # Common use case for accessing nested properties
        ('this_is_snake_case', 'this_is_snake_case'),  # Snake case identifier
        ('camelCase', 'camelCase'),  # Camel case identifier
        ('PascalCase', 'PascalCase'),  # Pascal case identifier
        ('_private.method', '_private.method'),
        # Identifier starting with underscore followed by dot and another identifier
        ('x1.y2.z3', 'x1.y2.z3'),  # Chain of identifiers containing numbers
        ('very_long_identifier.with.many.parts', 'very_long_identifier.with.many.parts'),
        # Long chain with multiple components
        ('a_1.b_2.c_3', 'a_1.b_2.c_3'),  # Chain with underscores and numbers
        ('Class.static_method', 'Class.static_method'),  # Common pattern for accessing static methods
        ('package.subpackage.Class', 'package.subpackage.Class'),  # Common import or qualification pattern
        ('x', 'x'),  # Minimal valid chain_id with just one identifier
        ('a.b.c.d.e.f.g', 'a.b.c.d.e.f.g'),  # Long chain with many segments
        ('_._._', '_._._'),  # Chain of underscore identifiers
        ('A1.B2.C3', 'A1.B2.C3'),  # Chain with uppercase letters and numbers
    ])
    def test_positive_cases_str(self, input_text, expected_str):
        assert str(parse_with_grammar_entry(input_text, entry_name='chain_id')) == expected_str

    @pytest.mark.parametrize(['input_text'], [
        ('.foo',),  # Cannot start with a dot - must begin with an identifier
        ('foo.',),  # Cannot end with a dot - must have an identifier after each dot
        ('foo..bar',),  # Cannot have consecutive dots - each dot must be followed by an identifier
        ('1a',),  # Identifiers cannot start with a number
        ('foo.1bar',),  # Each segment after a dot must be a valid identifier (cannot start with a number)
        ('foo-bar',),  # Hyphens are not allowed in identifiers
        ('foo.@bar',),  # Special characters like @ are not allowed in identifiers
        ('foo bar',),  # Spaces are not allowed in chain_id
        ('foo.bar.',),  # Cannot end with a trailing dot
        ('foo.123',),  # Segments after dots cannot be pure numbers
        ('123.abc',),  # First segment cannot start with a number
        ('a.b..c',),  # Double dots are not allowed
        ('.',),  # Lone dot without identifiers is invalid
        ('foo.true',),  # Reserved keyword 'true' can be used as identifier in this grammar
        ('sin.cos',),  # Reserved function names can be used as identifiers in this grammar
        ('foo.0x123',),  # Hex integers cannot be used as identifiers
        ('a b.c',),  # Spaces are not allowed within any part of the chain
        ('a+b.c',),  # Operators are not allowed in identifiers
        ('.a.b',),  # Cannot start with a dot
        ('a.b.',),  # Cannot end with a dot
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name='chain_id')

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]
