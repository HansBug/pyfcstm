import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLEnterDefinition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    enter { x = 10; }
                    """,
                    EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10'))], name=None)
            ),  # Basic enter operation with assignment
            (
                    """
                    enter { x = 10; y = 20; }
                    """,
                    EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                OperationAssignment(name='y', expr=Integer(raw='20'))], name=None)
            ),  # Enter operation with multiple assignments
            (
                    """
                    enter { }
                    """,
                    EnterOperations(operations=[], name=None)
            ),  # Enter operation with empty body
            (
                    """
                    enter initFunc { x = 10; }
                    """,
                    EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10'))], name='initFunc')
            ),  # Enter operation with named function
            (
                    """
                    enter setupState { x = 10; y = x + 5; }
                    """,
                    EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                OperationAssignment(name='y',
                                                                    expr=BinaryOp(expr1=Name(name='x'), op='+',
                                                                                  expr2=Integer(raw='5')))],
                                    name='setupState')
            ),  # Enter operation with named function and multiple assignments
            (
                    """
                    enter onEnter { flag = 0x1; }
                    """,
                    EnterOperations(operations=[OperationAssignment(name='flag', expr=HexInt(raw='0x1'))],
                                    name='onEnter')
            ),  # Enter operation with descriptive function name
            (
                    """
                    enter abstract setupFunc;
                    """,
                    EnterAbstractFunction(name='setupFunc', doc=None)
            ),  # Basic enter abstract function
            (
                    """
                    enter abstract init_state;
                    """,
                    EnterAbstractFunction(name='init_state', doc=None)
            ),  # Enter abstract function with underscore name
            (
                    """
                    enter abstract SETUP;
                    """,
                    EnterAbstractFunction(name='SETUP', doc=None)
            ),  # Enter abstract function with uppercase name
            (
                    """
                    enter abstract setupFunc /* Initialize state variables */
                    """,
                    EnterAbstractFunction(name='setupFunc', doc='Initialize state variables')
            ),  # Enter abstract function with single line documentation
            (
                    """
                    enter abstract /* Setup initial conditions */
                    """,
                    EnterAbstractFunction(name=None, doc='Setup initial conditions')
            ),  # Enter abstract function without name but with documentation
            (
                    """
                    enter ref chain.id;
                    """,
                    EnterRefFunction(name=None, ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # Basic enter reference function
            (
                    """
                    enter ref /absolute.chain.id;
                    """,
                    EnterRefFunction(name=None, ref=ChainID(path=['absolute', 'chain', 'id'], is_absolute=True))
            ),  # Enter reference function with absolute chain ID
            (
                    """
                    enter ref nested.deep.chain;
                    """,
                    EnterRefFunction(name=None, ref=ChainID(path=['nested', 'deep', 'chain'], is_absolute=False))
            ),  # Enter reference function with nested chain ID
            (
                    """
                    enter setupFunc ref chain.id;
                    """,
                    EnterRefFunction(name='setupFunc', ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # Enter reference function with named function
            (
                    """
                    enter initState ref /root.setup;
                    """,
                    EnterRefFunction(name='initState', ref=ChainID(path=['root', 'setup'], is_absolute=True))
            ),  # Enter reference function with named function and absolute chain
            (
                    """
                    enter onEnter ref utils.init;
                    """,
                    EnterRefFunction(name='onEnter', ref=ChainID(path=['utils', 'init'], is_absolute=False))
            ),  # Enter reference function with descriptive name and chain
        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="enter_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    enter { x = 10; }
                    """,
                    'enter {\n    x = 10;\n}'
            ),  # Basic enter operation with assignment
            (
                    """
                    enter { x = 10; y = 20; }
                    """,
                    'enter {\n    x = 10;\n    y = 20;\n}'
            ),  # Enter operation with multiple assignments
            (
                    """
                    enter { }
                    """,
                    'enter {\n}'
            ),  # Enter operation with empty body
            (
                    """
                    enter initFunc { x = 10; }
                    """,
                    'enter initFunc {\n    x = 10;\n}'
            ),  # Enter operation with named function
            (
                    """
                    enter setupState { x = 10; y = x + 5; }
                    """,
                    'enter setupState {\n    x = 10;\n    y = x + 5;\n}'
            ),  # Enter operation with named function and multiple assignments
            (
                    """
                    enter onEnter { flag = 0x1; }
                    """,
                    'enter onEnter {\n    flag = 0x1;\n}'
            ),  # Enter operation with descriptive function name
            (
                    """
                    enter abstract setupFunc;
                    """,
                    'enter abstract setupFunc;'
            ),  # Basic enter abstract function
            (
                    """
                    enter abstract init_state;
                    """,
                    'enter abstract init_state;'
            ),  # Enter abstract function with underscore name
            (
                    """
                    enter abstract SETUP;
                    """,
                    'enter abstract SETUP;'
            ),  # Enter abstract function with uppercase name
            (
                    """
                    enter abstract setupFunc /* Initialize state variables */
                    """,
                    'enter abstract setupFunc /*\n    Initialize state variables\n*/'
            ),  # Enter abstract function with single line documentation
            (
                    """
                    enter abstract /* Setup initial conditions */
                    """,
                    'enter abstract /*\n    Setup initial conditions\n*/'
            ),  # Enter abstract function without name but with documentation
            (
                    """
                    enter ref chain.id;
                    """,
                    'enter ref chain.id;'
            ),  # Basic enter reference function
            (
                    """
                    enter ref /absolute.chain.id;
                    """,
                    'enter ref /absolute.chain.id;'
            ),  # Enter reference function with absolute chain ID
            (
                    """
                    enter ref nested.deep.chain;
                    """,
                    'enter ref nested.deep.chain;'
            ),  # Enter reference function with nested chain ID
            (
                    """
                    enter setupFunc ref chain.id;
                    """,
                    'enter setupFunc ref chain.id;'
            ),  # Enter reference function with named function
            (
                    """
                    enter initState ref /root.setup;
                    """,
                    'enter initState ref /root.setup;'
            ),  # Enter reference function with named function and absolute chain
            (
                    """
                    enter onEnter ref utils.init;
                    """,
                    'enter onEnter ref utils.init;'
            ),  # Enter reference function with descriptive name and chain
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="enter_definition")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    enter;
                    """,
            ),  # Missing enter body, abstract keyword, or ref keyword
            (
                    """
                    enter {
                    """,
            ),  # Missing closing brace for enter operations
            (
                    """
                    enter }
                    """,
            ),  # Missing opening brace for enter operations
            (
                    """
                    enter { x = 10
                    """,
            ),  # Missing closing brace and semicolon
            (
                    """
                    enter abstract;
                    """,
            ),  # Missing function name for abstract enter
            (
                    """
                    enter ref;
                    """,
            ),  # Missing chain ID for reference enter
            (
                    """
                    enter { x := 10; }
                    """,
            ),  # Invalid assignment operator in enter operations
            (
                    """
                    enter { x = 10 }
                    """,
            ),  # Missing semicolon after assignment in enter operations
            (
                    """
                    enter { x == 10; }
                    """,
            ),  # Invalid comparison operator instead of assignment
            (
                    """
                    enter { 123 = x; }
                    """,
            ),  # Invalid left-hand side in assignment
            (
                    """
                    enter 123func { x = 10; }
                    """,
            ),  # Invalid function name starting with number
            (
                    """
                    enter func-name { x = 10; }
                    """,
            ),  # Invalid function name with hyphen
            (
                    """
                    enter func.name { x = 10; }
                    """,
            ),  # Invalid function name with dot
            (
                    """
                    abstract enter setupFunc;
                    """,
            ),  # Wrong order of keywords
            (
                    """
                    enter abstract setupFunc {}
                    """,
            ),  # Abstract function cannot have operation body
            (
                    """
                    enter abstract setupFunc : chain.id;
                    """,
            ),  # Abstract function cannot have chain reference
            (
                    """
                    enter ref;
                    """,
            ),  # Missing chain ID for reference function
            (
                    """
                    enter setupFunc ref;
                    """,
            ),  # Missing chain ID for named reference function
            (
                    """
                    enter ref chain..id;
                    """,
            ),  # Invalid chain ID with consecutive dots
            (
                    """
                    enter ref .chain.id;
                    """,
            ),  # Invalid chain ID starting with dot (not absolute)
            (
                    """
                    enter ref chain.;
                    """,
            ),  # Invalid chain ID ending with dot
            (
                    """
                    enter setupFunc abstract ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref keywords
            (
                    """
                    enter abstract ref chain.id;
                    """,
            ),  # Cannot combine abstract and ref without function name
            (
                    """
                    enter setupFunc { x = 10; } ref chain.id;
                    """,
            ),  # Cannot combine operations body with reference
            (
                    """
                    enter abstract setupFunc
                    """,
            ),  # Missing semicolon after abstract enter function
            (
                    """
                    enter setupFunc ref chain.id
                    """,
            ),  # Missing semicolon after reference enter function
            (
                    """
                    enter abstract setupFunc //* Invalid comment */
                    """,
            ),  # Invalid comment syntax for documentation
            (
                    """
                    enter abstract setupFunc /* Unclosed comment
                    """,
            ),  # Unclosed documentation comment

        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="enter_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
