import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLExitDefinition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    exit { x = 10; }
                    """,
                    ExitOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10'))], name=None)
            ),  # Basic exit operation with assignment
            (
                    """
                    exit { x = 10; y = 20; }
                    """,
                    ExitOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                               OperationAssignment(name='y', expr=Integer(raw='20'))], name=None)
            ),  # Exit operation with multiple assignments
            (
                    """
                    exit { }
                    """,
                    ExitOperations(operations=[], name=None)
            ),  # Exit operation with empty body
            (
                    """
                    exit initFunc { x = 10; }
                    """,
                    ExitOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10'))], name='initFunc')
            ),  # Exit operation with named function
            (
                    """
                    exit setupState { x = 10; y = x + 5; }
                    """,
                    ExitOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                               OperationAssignment(name='y',
                                                                   expr=BinaryOp(expr1=Name(name='x'), op='+',
                                                                                 expr2=Integer(raw='5')))],
                                   name='setupState')
            ),  # Exit operation with named function and multiple assignments
            (
                    """
                    exit onExit { flag = 0x1; }
                    """,
                    ExitOperations(operations=[OperationAssignment(name='flag', expr=HexInt(raw='0x1'))],
                                   name='onExit')
            ),  # Exit operation with descriptive function name
            (
                    """
                    exit abstract setupFunc;
                    """,
                    ExitAbstractFunction(name='setupFunc', doc=None)
            ),  # Basic exit abstract function
            (
                    """
                    exit abstract init_state;
                    """,
                    ExitAbstractFunction(name='init_state', doc=None)
            ),  # Exit abstract function with underscore name
            (
                    """
                    exit abstract SETUP;
                    """,
                    ExitAbstractFunction(name='SETUP', doc=None)
            ),  # Exit abstract function with uppercase name
            (
                    """
                    exit abstract setupFunc /* Initialize state variables */
                    """,
                    ExitAbstractFunction(name='setupFunc', doc='Initialize state variables')
            ),  # Exit abstract function with single line documentation
            (
                    """
                    exit abstract /* Setup initial conditions */
                    """,
                    ExitAbstractFunction(name=None, doc='Setup initial conditions')
            ),  # Exit abstract function without name but with documentation
            (
                    """
                    exit ref chain.id;
                    """,
                    ExitRefFunction(name=None, ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # Basic exit reference function
            (
                    """
                    exit ref /absolute.chain.id;
                    """,
                    ExitRefFunction(name=None, ref=ChainID(path=['absolute', 'chain', 'id'], is_absolute=True))
            ),  # Exit reference function with absolute chain ID
            (
                    """
                    exit ref nested.deep.chain;
                    """,
                    ExitRefFunction(name=None, ref=ChainID(path=['nested', 'deep', 'chain'], is_absolute=False))
            ),  # Exit reference function with nested chain ID
            (
                    """
                    exit setupFunc ref chain.id;
                    """,
                    ExitRefFunction(name='setupFunc', ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # Exit reference function with named function
            (
                    """
                    exit initState ref /root.setup;
                    """,
                    ExitRefFunction(name='initState', ref=ChainID(path=['root', 'setup'], is_absolute=True))
            ),  # Exit reference function with named function and absolute chain
            (
                    """
                    exit onExit ref utils.init;
                    """,
                    ExitRefFunction(name='onExit', ref=ChainID(path=['utils', 'init'], is_absolute=False))
            ),  # Exit reference function with descriptive name and chain
        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="exit_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    exit { x = 10; }
                    """,
                    'exit {\n    x = 10;\n}'
            ),  # Basic exit operation with assignment
            (
                    """
                    exit { x = 10; y = 20; }
                    """,
                    'exit {\n    x = 10;\n    y = 20;\n}'
            ),  # Exit operation with multiple assignments
            (
                    """
                    exit { }
                    """,
                    'exit {\n}'
            ),  # Exit operation with empty body
            (
                    """
                    exit initFunc { x = 10; }
                    """,
                    'exit initFunc {\n    x = 10;\n}'
            ),  # Exit operation with named function
            (
                    """
                    exit setupState { x = 10; y = x + 5; }
                    """,
                    'exit setupState {\n    x = 10;\n    y = x + 5;\n}'
            ),  # Exit operation with named function and multiple assignments
            (
                    """
                    exit onExit { flag = 0x1; }
                    """,
                    'exit onExit {\n    flag = 0x1;\n}'
            ),  # Exit operation with descriptive function name
            (
                    """
                    exit abstract setupFunc;
                    """,
                    'exit abstract setupFunc;'
            ),  # Basic exit abstract function
            (
                    """
                    exit abstract init_state;
                    """,
                    'exit abstract init_state;'
            ),  # Exit abstract function with underscore name
            (
                    """
                    exit abstract SETUP;
                    """,
                    'exit abstract SETUP;'
            ),  # Exit abstract function with uppercase name
            (
                    """
                    exit abstract setupFunc /* Initialize state variables */
                    """,
                    'exit abstract setupFunc /*\n    Initialize state variables\n*/'
            ),  # Exit abstract function with single line documentation
            (
                    """
                    exit abstract /* Setup initial conditions */
                    """,
                    'exit abstract /*\n    Setup initial conditions\n*/'
            ),  # Exit abstract function without name but with documentation
            (
                    """
                    exit ref chain.id;
                    """,
                    'exit ref chain.id;'
            ),  # Basic exit reference function
            (
                    """
                    exit ref /absolute.chain.id;
                    """,
                    'exit ref /absolute.chain.id;'
            ),  # Exit reference function with absolute chain ID
            (
                    """
                    exit ref nested.deep.chain;
                    """,
                    'exit ref nested.deep.chain;'
            ),  # Exit reference function with nested chain ID
            (
                    """
                    exit setupFunc ref chain.id;
                    """,
                    'exit setupFunc ref chain.id;'
            ),  # Exit reference function with named function
            (
                    """
                    exit initState ref /root.setup;
                    """,
                    'exit initState ref /root.setup;'
            ),  # Exit reference function with named function and absolute chain
            (
                    """
                    exit onExit ref utils.init;
                    """,
                    'exit onExit ref utils.init;'
            ),  # Exit reference function with descriptive name and chain
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="exit_definition")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    exit;
                    """,
            ),  # Missing exit body, abstract keyword, or ref keyword
            (
                    """
                    exit {
                    """,
            ),  # Missing closing brace for exit operations
            (
                    """
                    exit }
                    """,
            ),  # Missing opening brace for exit operations
            (
                    """
                    exit { x = 10
                    """,
            ),  # Missing closing brace and semicolon
            (
                    """
                    exit abstract;
                    """,
            ),  # Missing function name for abstract exit
            (
                    """
                    exit ref;
                    """,
            ),  # Missing chain ID for reference exit
            (
                    """
                    exit { x := 10; }
                    """,
            ),  # Invalid assignment operator in exit operations
            (
                    """
                    exit { x = 10 }
                    """,
            ),  # Missing semicolon after assignment in exit operations
            (
                    """
                    exit { x == 10; }
                    """,
            ),  # Invalid comparison operator instead of assignment
            (
                    """
                    exit { 123 = x; }
                    """,
            ),  # Invalid left-hand side in assignment
            (
                    """
                    exit 123func { x = 10; }
                    """,
            ),  # Invalid function name starting with number
            (
                    """
                    exit func-name { x = 10; }
                    """,
            ),  # Invalid function name with hyphen
            (
                    """
                    exit func.name { x = 10; }
                    """,
            ),  # Invalid function name with dot
            (
                    """
                    abstract exit setupFunc;
                    """,
            ),  # Wrong order of keywords
            (
                    """
                    exit abstract setupFunc {}
                    """,
            ),  # Abstract function cannot have operation body
            (
                    """
                    exit abstract setupFunc : chain.id;
                    """,
            ),  # Abstract function cannot have chain reference
            (
                    """
                    exit ref;
                    """,
            ),  # Missing chain ID for reference function
            (
                    """
                    exit setupFunc ref;
                    """,
            ),  # Missing chain ID for named reference function
            (
                    """
                    exit ref chain..id;
                    """,
            ),  # Invalid chain ID with consecutive dots
            (
                    """
                    exit ref .chain.id;
                    """,
            ),  # Invalid chain ID starting with dot (not absolute)
            (
                    """
                    exit ref chain.;
                    """,
            ),  # Invalid chain ID ending with dot
            (
                    """
                    exit setupFunc abstract ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref keywords
            (
                    """
                    exit abstract ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref without function name
            (
                    """
                    exit setupFunc { x = 10; } ref chain.id;
                    """,
            ),  # Cannot combine operations body with reference
            (
                    """
                    exit abstract setupFunc
                    """,
            ),  # Missing semicolon after abstract exit function
            (
                    """
                    exit setupFunc ref chain.id
                    """,
            ),  # Missing semicolon after reference exit function
            (
                    """
                    exit abstract setupFunc //* Invalid comment */
                    """,
            ),  # Invalid comment syntax for documentation
            (
                    """
                    exit abstract setupFunc /* Unclosed comment
                    """,
            ),  # Unclosed documentation comment

        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="exit_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
