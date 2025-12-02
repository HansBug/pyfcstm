import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError, ChainID


@pytest.mark.unittest
class TestDSLChainID:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    simple
                    """,
                    ChainID(path=['simple'], is_absolute=False)
            ),  # Simple single identifier chain ID
            (
                    """
                    chain.id
                    """,
                    ChainID(path=['chain', 'id'], is_absolute=False)
            ),  # Two-part chain ID with dot separator
            (
                    """
                    chain.sub.id
                    """,
                    ChainID(path=['chain', 'sub', 'id'], is_absolute=False)
            ),  # Three-part chain ID with multiple dots
            (
                    """
                    very.long.chain.with.many.parts
                    """,
                    ChainID(path=['very', 'long', 'chain', 'with', 'many', 'parts'], is_absolute=False)
            ),  # Multi-part chain ID with many segments
            (
                    """
                    /absolute
                    """,
                    ChainID(path=['absolute'], is_absolute=True)
            ),  # Absolute chain ID with single identifier
            (
                    """
                    /absolute.chain
                    """,
                    ChainID(path=['absolute', 'chain'], is_absolute=True)
            ),  # Absolute chain ID with two parts
            (
                    """
                    /root.path.to.target
                    """,
                    ChainID(path=['root', 'path', 'to', 'target'], is_absolute=True)
            ),  # Absolute chain ID with multiple parts
            (
                    """
                    /very.deep.nested.chain.id
                    """,
                    ChainID(path=['very', 'deep', 'nested', 'chain', 'id'], is_absolute=True)
            ),  # Deep absolute chain ID
            (
                    """
                    _underscore
                    """,
                    ChainID(path=['_underscore'], is_absolute=False)
            ),  # Chain ID starting with underscore
            (
                    """
                    mixed_Case123
                    """,
                    ChainID(path=['mixed_Case123'], is_absolute=False)
            ),  # Chain ID with mixed case and numbers
            (
                    """
                    path.to._private
                    """,
                    ChainID(path=['path', 'to', '_private'], is_absolute=False)
            ),  # Chain ID with underscore in path
            (
                    """
                    API.v1.endpoint
                    """,
                    ChainID(path=['API', 'v1', 'endpoint'], is_absolute=False)
            ),  # Chain ID with version-like naming
            (
                    """
                    module.Class.method
                    """,
                    ChainID(path=['module', 'Class', 'method'], is_absolute=False)
            ),  # Chain ID resembling code structure
            (
                    """
                    a
                    """,
                    ChainID(path=['a'], is_absolute=False)
            ),  # Single character chain ID
            (
                    """
                    A
                    """,
                    ChainID(path=['A'], is_absolute=False)
            ),  # Single uppercase character chain ID
            (
                    """
                    _
                    """,
                    ChainID(path=['_'], is_absolute=False)
            ),  # Single underscore chain ID
            (
                    """
                    /a
                    """,
                    ChainID(path=['a'], is_absolute=True)
            ),  # Absolute single character chain ID
        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="chain_id") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    simple
                    """,
                    'simple'
            ),  # Simple single identifier chain ID
            (
                    """
                    chain.id
                    """,
                    'chain.id'
            ),  # Two-part chain ID with dot separator
            (
                    """
                    chain.sub.id
                    """,
                    'chain.sub.id'
            ),  # Three-part chain ID with multiple dots
            (
                    """
                    very.long.chain.with.many.parts
                    """,
                    'very.long.chain.with.many.parts'
            ),  # Multi-part chain ID with many segments
            (
                    """
                    /absolute
                    """,
                    '/absolute'
            ),  # Absolute chain ID with single identifier
            (
                    """
                    /absolute.chain
                    """,
                    '/absolute.chain'
            ),  # Absolute chain ID with two parts
            (
                    """
                    /root.path.to.target
                    """,
                    '/root.path.to.target'
            ),  # Absolute chain ID with multiple parts
            (
                    """
                    /very.deep.nested.chain.id
                    """,
                    '/very.deep.nested.chain.id'
            ),  # Deep absolute chain ID
            (
                    """
                    _underscore
                    """,
                    '_underscore'
            ),  # Chain ID starting with underscore
            (
                    """
                    mixed_Case123
                    """,
                    'mixed_Case123'
            ),  # Chain ID with mixed case and numbers
            (
                    """
                    path.to._private
                    """,
                    'path.to._private'
            ),  # Chain ID with underscore in path
            (
                    """
                    API.v1.endpoint
                    """,
                    'API.v1.endpoint'
            ),  # Chain ID with version-like naming
            (
                    """
                    module.Class.method
                    """,
                    'module.Class.method'
            ),  # Chain ID resembling code structure
            (
                    """
                    a
                    """,
                    'a'
            ),  # Single character chain ID
            (
                    """
                    A
                    """,
                    'A'
            ),  # Single uppercase character chain ID
            (
                    """
                    _
                    """,
                    '_'
            ),  # Single underscore chain ID
            (
                    """
                    /a
                    """,
                    '/a'
            ),  # Absolute single character chain ID
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="chain_id")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    123.invalid
                    """,
            ),  # Chain ID starting with number
            (
                    """
                    .invalid
                    """,
            ),  # Chain ID starting with dot
            (
                    """
                    -.invalid
                    """,
            ),  # Chain ID starting with dash
            (
                    """
                    //double.slash
                    """,
            ),  # Double slash in absolute path
            (
                    """
                    /
                    """,
            ),  # Absolute path with no identifier
            (
                    """
                    /.invalid
                    """,
            ),  # Absolute path with dot after slash
            (
                    """
                    chain..double.dot
                    """,
            ),  # Chain ID with consecutive dots
            (
                    """
                    chain.
                    """,
            ),  # Chain ID ending with dot
            (
                    """
                    chain.id.
                    """,
            ),  # Chain ID ending with trailing dot
            (
                    """
                    chain-id
                    """,
            ),  # Chain ID with dash separator
            (
                    """
                    chain id
                    """,
            ),  # Chain ID with space separator
            (
                    """
                    chain@id
                    """,
            ),  # Chain ID with at symbol
            # (
            #         """
            #         chain#id
            #         """,
            # ),  # Chain ID with hash symbol
            (
                    """
                    chain$id
                    """,
            ),  # Chain ID with dollar sign
            (
                    """
            
                    """,
            ),  # Empty chain ID
            (
                    """
                    chain..id
                    """,
            ),  # Chain ID with empty component between dots
            (
                    """
                    /.
                    """,
            ),  # Absolute path with just dot
        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="chain_id"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
