import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLDuringAspectDefinition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    >> during before { x = 10; }
                    """,
                    DuringAspectOperations(aspect='before',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                           name=None)
            ),  # Basic during aspect with before timing and operations
            (
                    """
                    >> during after { x = 10; }
                    """,
                    DuringAspectOperations(aspect='after',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                           name=None)
            ),  # Basic during aspect with after timing and operations
            (
                    """
                    >> during before funcName { x = 10; y = 20; }
                    """,
                    DuringAspectOperations(aspect='before',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                       OperationAssignment(name='y', expr=Integer(raw='20'))],
                                           name='funcName')
            ),  # During aspect with before timing, function name and multiple operations
            (
                    """
                    >> during after funcName { x = 10; y = 20; }
                    """,
                    DuringAspectOperations(aspect='after',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                       OperationAssignment(name='y', expr=Integer(raw='20'))],
                                           name='funcName')
            ),  # During aspect with after timing, function name and multiple operations
            (
                    """
                    >> during before abstract funcName;
                    """,
                    DuringAspectAbstractFunction(name='funcName', aspect='before', doc=None)
            ),  # During aspect with before timing and abstract function
            (
                    """
                    >> during after abstract funcName;
                    """,
                    DuringAspectAbstractFunction(name='funcName', aspect='after', doc=None)
            ),  # During aspect with after timing and abstract function
            (
                    """
                    >> during before abstract funcName /* this is documentation */
                    """,
                    DuringAspectAbstractFunction(name='funcName', aspect='before', doc='this is documentation')
            ),  # During aspect with before timing, abstract function and documentation
            (
                    """
                    >> during after abstract funcName /* this is documentation */
                    """,
                    DuringAspectAbstractFunction(name='funcName', aspect='after', doc='this is documentation')
            ),  # During aspect with after timing, abstract function and documentation
            (
                    """
                    >> during before abstract /* this is documentation */
                    """,
                    DuringAspectAbstractFunction(name=None, aspect='before', doc='this is documentation')
            ),  # During aspect with before timing, abstract function without name and documentation
            (
                    """
                    >> during after abstract /* this is documentation */
                    """,
                    DuringAspectAbstractFunction(name=None, aspect='after', doc='this is documentation')
            ),  # During aspect with after timing, abstract function without name and documentation
            (
                    """
                    >> during before ref chain.id;
                    """,
                    DuringAspectRefFunction(name=None, aspect='before',
                                            ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # During aspect with before timing and chain reference
            (
                    """
                    >> during after ref chain.id;
                    """,
                    DuringAspectRefFunction(name=None, aspect='after',
                                            ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # During aspect with after timing and chain reference
            (
                    """
                    >> during before funcName ref chain.id;
                    """,
                    DuringAspectRefFunction(name='funcName', aspect='before',
                                            ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # During aspect with before timing, function name and chain reference
            (
                    """
                    >> during after funcName ref chain.id;
                    """,
                    DuringAspectRefFunction(name='funcName', aspect='after',
                                            ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # During aspect with after timing, function name and chain reference
            (
                    """
                    >> during before ref /absolute.chain.id;
                    """,
                    DuringAspectRefFunction(name=None, aspect='before',
                                            ref=ChainID(path=['absolute', 'chain', 'id'], is_absolute=True))
            ),  # During aspect with before timing and absolute chain reference
            (
                    """
                    >> during after ref /absolute.chain.id;
                    """,
                    DuringAspectRefFunction(name=None, aspect='after',
                                            ref=ChainID(path=['absolute', 'chain', 'id'], is_absolute=True))
            ),  # During aspect with after timing and absolute chain reference
            (
                    """
                    >> during before ref complex.nested.chain.id;
                    """,
                    DuringAspectRefFunction(name=None, aspect='before',
                                            ref=ChainID(path=['complex', 'nested', 'chain', 'id'], is_absolute=False))
            ),  # During aspect with complex nested chain reference
            (
                    """
                    >> during after ref /root.complex.nested.chain;
                    """,
                    DuringAspectRefFunction(name=None, aspect='after',
                                            ref=ChainID(path=['root', 'complex', 'nested', 'chain'], is_absolute=True))
            ),  # During aspect with absolute complex nested chain reference
            (
                    """
                    >> during before { }
                    """,
                    DuringAspectOperations(aspect='before', operations=[], name=None)
            ),  # During aspect with before timing and empty operations block
            (
                    """
                    >> during after { }
                    """,
                    DuringAspectOperations(aspect='after', operations=[], name=None)
            ),  # During aspect with after timing and empty operations block
            (
                    """
                    >> during before { ; x = 10; ; }
                    """,
                    DuringAspectOperations(aspect='before',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                           name=None)
            ),  # During aspect with before timing and operations with extra semicolons
            (
                    """
                    >> during after { x = 10; ; y = 20; }
                    """,
                    DuringAspectOperations(aspect='after',
                                           operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                       OperationAssignment(name='y', expr=Integer(raw='20'))],
                                           name=None)
            ),  # During aspect with after timing and operations with semicolons
        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="during_aspect_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    >> during before { x = 10; }
                    """,
                    '>> during before {\n    x = 10;\n}'
            ),  # Basic during aspect with before timing and operations
            (
                    """
                    >> during after { x = 10; }
                    """,
                    '>> during after {\n    x = 10;\n}'
            ),  # Basic during aspect with after timing and operations
            (
                    """
                    >> during before funcName { x = 10; y = 20; }
                    """,
                    '>> during before funcName {\n    x = 10;\n    y = 20;\n}'
            ),  # During aspect with before timing, function name and multiple operations
            (
                    """
                    >> during after funcName { x = 10; y = 20; }
                    """,
                    '>> during after funcName {\n    x = 10;\n    y = 20;\n}'
            ),  # During aspect with after timing, function name and multiple operations
            (
                    """
                    >> during before abstract funcName;
                    """,
                    '>> during before abstract funcName;'
            ),  # During aspect with before timing and abstract function
            (
                    """
                    >> during after abstract funcName;
                    """,
                    '>> during after abstract funcName;'
            ),  # During aspect with after timing and abstract function
            (
                    """
                    >> during before abstract funcName /* this is documentation */
                    """,
                    '>> during before abstract funcName /*\n    this is documentation\n*/'
            ),  # During aspect with before timing, abstract function and documentation
            (
                    """
                    >> during after abstract funcName /* this is documentation */
                    """,
                    '>> during after abstract funcName /*\n    this is documentation\n*/'
            ),  # During aspect with after timing, abstract function and documentation
            (
                    """
                    >> during before abstract /* this is documentation */
                    """,
                    '>> during before abstract /*\n    this is documentation\n*/'
            ),  # During aspect with before timing, abstract function without name and documentation
            (
                    """
                    >> during after abstract /* this is documentation */
                    """,
                    '>> during after abstract /*\n    this is documentation\n*/'
            ),  # During aspect with after timing, abstract function without name and documentation
            (
                    """
                    >> during before ref chain.id;
                    """,
                    '>> during before ref chain.id;'
            ),  # During aspect with before timing and chain reference
            (
                    """
                    >> during after ref chain.id;
                    """,
                    '>> during after ref chain.id;'
            ),  # During aspect with after timing and chain reference
            (
                    """
                    >> during before funcName ref chain.id;
                    """,
                    '>> during before funcName ref chain.id;'
            ),  # During aspect with before timing, function name and chain reference
            (
                    """
                    >> during after funcName ref chain.id;
                    """,
                    '>> during after funcName ref chain.id;'
            ),  # During aspect with after timing, function name and chain reference
            (
                    """
                    >> during before ref /absolute.chain.id;
                    """,
                    '>> during before ref /absolute.chain.id;'
            ),  # During aspect with before timing and absolute chain reference
            (
                    """
                    >> during after ref /absolute.chain.id;
                    """,
                    '>> during after ref /absolute.chain.id;'
            ),  # During aspect with after timing and absolute chain reference
            (
                    """
                    >> during before ref complex.nested.chain.id;
                    """,
                    '>> during before ref complex.nested.chain.id;'
            ),  # During aspect with complex nested chain reference
            (
                    """
                    >> during after ref /root.complex.nested.chain;
                    """,
                    '>> during after ref /root.complex.nested.chain;'
            ),  # During aspect with absolute complex nested chain reference
            (
                    """
                    >> during before { }
                    """,
                    '>> during before {\n}'
            ),  # During aspect with before timing and empty operations block
            (
                    """
                    >> during after { }
                    """,
                    '>> during after {\n}'
            ),  # During aspect with after timing and empty operations block
            (
                    """
                    >> during before { ; x = 10; ; }
                    """,
                    '>> during before {\n    x = 10;\n}'
            ),  # During aspect with before timing and operations with extra semicolons
            (
                    """
                    >> during after { x = 10; ; y = 20; }
                    """,
                    '>> during after {\n    x = 10;\n    y = 20;\n}'
            ),  # During aspect with after timing and operations with semicolons
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="during_aspect_definition")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    during before { x = 10; }
                    """,
            ),  # Missing >> prefix for during aspect
            (
                    """
                    during after abstract funcName;
                    """,
            ),  # Missing >> prefix for during aspect abstract function
            (
                    """
                    >> during middle { x = 10; }
                    """,
            ),  # Invalid timing keyword 'middle'
            (
                    """
                    >> during start { x = 10; }
                    """,
            ),  # Invalid timing keyword 'start'
            (
                    """
                    >> during end { x = 10; }
                    """,
            ),  # Invalid timing keyword 'end'
            (
                    """
                    >> during before x = 10;
                    """,
            ),  # Missing braces around operations
            (
                    """
                    >> during after { x = 10
                    """,
            ),  # Missing closing brace for operations
            (
                    """
                    >> during before x = 10; }
                    """,
            ),  # Missing opening brace for operations
            (
                    """
                    >> during before abstract;
                    """,
            ),  # Missing function name for abstract function
            (
                    """
                    >> during after abstract { x = 10; }
                    """,
            ),  # Abstract function cannot have operations block
            (
                    """
                    >> during before abstract funcName { x = 10; }
                    """,
            ),  # Abstract function cannot have operations block
            (
                    """
                    >> during before ref;
                    """,
            ),  # Missing chain ID for reference function
            (
                    """
                    >> during after ref { x = 10; }
                    """,
            ),  # Reference function cannot have operations block
            # (
            #         """
            #         >> during before ref funcName;
            #         """,
            # ),  # Invalid reference syntax - missing chain ID
            (
                    """
                    >> during before abstract funcName
                    """,
            ),  # Missing semicolon after abstract function
            (
                    """
                    >> during after ref chain.id
                    """,
            ),  # Missing semicolon after reference function
            (
                    """
                    >> during before ref .chain.id;
                    """,
            ),  # Invalid chain ID starting with dot
            (
                    """
                    >> during after ref chain..id;
                    """,
            ),  # Invalid chain ID with consecutive dots
            (
                    """
                    >> during before ref chain.;
                    """,
            ),  # Invalid chain ID ending with dot
            (
                    """
                    >> during before { x := 10; }
                    """,
            ),  # Invalid assignment operator in operations
            (
                    """
                    >> during after { x = 10 }
                    """,
            ),  # Missing semicolon in operations
            (
                    """
                    >> during before { x = ; }
                    """,
            ),  # Missing expression in assignment
            (
                    """
                    >> during before after { x = 10; }
                    """,
            ),  # Multiple timing keywords not allowed
            (
                    """
                    >> during abstract ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref keywords
            (
                    """
                    >> during before abstract funcName ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref in same definition
            (
                    """
                    >> during before 123func { x = 10; }
                    """,
            ),  # Invalid function name starting with number
            (
                    """
                    >> during after abstract 123func;
                    """,
            ),  # Invalid abstract function name starting with number
        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="during_aspect_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
