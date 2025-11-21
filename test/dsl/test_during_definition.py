import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLDuringDefinition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    during { x = 10; }
                    """,
                    DuringOperations(aspect=None, operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                     name=None)
            ),  # Basic during operation without aspect or function name
            (
                    """
                    during funcName { x = 10; y = 20; }
                    """,
                    DuringOperations(aspect=None, operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                              OperationAssignment(name='y', expr=Integer(raw='20'))],
                                     name='funcName')
            ),  # During operation with function name and multiple assignments
            (
                    """
                    during before { x = 10; }
                    """,
                    DuringOperations(aspect='before',
                                     operations=[OperationAssignment(name='x', expr=Integer(raw='10'))], name=None)
            ),  # During operation with before aspect, no function name
            (
                    """
                    during before funcName { x = 10; y = 20; }
                    """,
                    DuringOperations(aspect='before', operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                                  OperationAssignment(name='y',
                                                                                      expr=Integer(raw='20'))],
                                     name='funcName')
            ),  # During operation with before aspect and function name
            (
                    """
                    during after { x = 10; }
                    """,
                    DuringOperations(aspect='after', operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                     name=None)
            ),  # During operation with after aspect, no function name
            (
                    """
                    during after funcName { x = 10; y = 20; }
                    """,
                    DuringOperations(aspect='after', operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                                 OperationAssignment(name='y', expr=Integer(raw='20'))],
                                     name='funcName')
            ),  # During operation with after aspect and function name
            (
                    """
                    during abstract funcName;
                    """,
                    DuringAbstractFunction(name='funcName', aspect=None, doc=None)
            ),  # Basic abstract during function without aspect
            (
                    """
                    during before abstract funcName;
                    """,
                    DuringAbstractFunction(name='funcName', aspect='before', doc=None)
            ),  # Abstract during function with before aspect
            (
                    """
                    during after abstract funcName;
                    """,
                    DuringAbstractFunction(name='funcName', aspect='after', doc=None)
            ),  # Abstract during function with after aspect
            (
                    """
                    during abstract funcName /* this is documentation */
                    """,
                    DuringAbstractFunction(name='funcName', aspect=None, doc='this is documentation')
            ),  # Abstract during function with documentation
            (
                    """
                    during before abstract funcName /* before aspect documentation */
                    """,
                    DuringAbstractFunction(name='funcName', aspect='before', doc='before aspect documentation')
            ),  # Abstract during function with before aspect and documentation
            (
                    """
                    during after abstract /* after aspect without function name */
                    """,
                    DuringAbstractFunction(name=None, aspect='after', doc='after aspect without function name')
            ),  # Abstract during function with after aspect, no function name, with documentation
            (
                    """
                    during ref chain.id;
                    """,
                    DuringRefFunction(name=None, aspect=None, ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # Basic during reference function without aspect
            (
                    """
                    during funcName ref chain.id;
                    """,
                    DuringRefFunction(name='funcName', aspect=None,
                                      ref=ChainID(path=['chain', 'id'], is_absolute=False))
            ),  # During reference function with function name
            (
                    """
                    during before ref /absolute.chain.id;
                    """,
                    DuringRefFunction(name=None, aspect='before',
                                      ref=ChainID(path=['absolute', 'chain', 'id'], is_absolute=True))
            ),  # During reference function with before aspect and absolute chain ID
            (
                    """
                    during after funcName ref nested.chain.reference;
                    """,
                    DuringRefFunction(name='funcName', aspect='after',
                                      ref=ChainID(path=['nested', 'chain', 'reference'], is_absolute=False))
            ),  # During reference function with after aspect, function name and nested chain ID
            (
                    """
                    during { x = y + z * 2; }
                    """,
                    DuringOperations(aspect=None, operations=[OperationAssignment(name='x',
                                                                                  expr=BinaryOp(expr1=Name(name='y'),
                                                                                                op='+', expr2=BinaryOp(
                                                                                          expr1=Name(name='z'), op='*',
                                                                                          expr2=Integer(raw='2'))))],
                                     name=None)
            ),  # During operation with complex arithmetic expression
            (
                    """
                    during before { result = sin(angle) + cos(angle); }
                    """,
                    DuringOperations(aspect='before', operations=[OperationAssignment(name='result', expr=BinaryOp(
                        expr1=UFunc(func='sin', expr=Name(name='angle')), op='+',
                        expr2=UFunc(func='cos', expr=Name(name='angle'))))], name=None)
            ),  # During operation with mathematical functions
            (
                    """
                    during after calcFunc { value = (x > 5) ? x * 2 : x / 2; }
                    """,
                    DuringOperations(aspect='after', operations=[OperationAssignment(name='value', expr=ConditionalOp(
                        cond=BinaryOp(expr1=Name(name='x'), op='>', expr2=Integer(raw='5')),
                        value_true=BinaryOp(expr1=Name(name='x'), op='*', expr2=Integer(raw='2')),
                        value_false=BinaryOp(expr1=Name(name='x'), op='/', expr2=Integer(raw='2'))))], name='calcFunc')
            ),  # During operation with conditional expression
            (
                    """
                    during { }
                    """,
                    DuringOperations(aspect=None, operations=[], name=None)
            ),  # During operation with empty block
            (
                    """
                    during before funcName { }
                    """,
                    DuringOperations(aspect='before', operations=[], name='funcName')
            ),  # During operation with before aspect and empty block

        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="during_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    during { x = 10; }
                    """,
                    'during {\n    x = 10;\n}'
            ),  # Basic during operation without aspect or function name
            (
                    """
                    during funcName { x = 10; y = 20; }
                    """,
                    'during funcName {\n    x = 10;\n    y = 20;\n}'
            ),  # During operation with function name and multiple assignments
            (
                    """
                    during before { x = 10; }
                    """,
                    'during before {\n    x = 10;\n}'
            ),  # During operation with before aspect, no function name
            (
                    """
                    during before funcName { x = 10; y = 20; }
                    """,
                    'during before funcName {\n    x = 10;\n    y = 20;\n}'
            ),  # During operation with before aspect and function name
            (
                    """
                    during after { x = 10; }
                    """,
                    'during after {\n    x = 10;\n}'
            ),  # During operation with after aspect, no function name
            (
                    """
                    during after funcName { x = 10; y = 20; }
                    """,
                    'during after funcName {\n    x = 10;\n    y = 20;\n}'
            ),  # During operation with after aspect and function name
            (
                    """
                    during abstract funcName;
                    """,
                    'during abstract funcName;'
            ),  # Basic abstract during function without aspect
            (
                    """
                    during before abstract funcName;
                    """,
                    'during before abstract funcName;'
            ),  # Abstract during function with before aspect
            (
                    """
                    during after abstract funcName;
                    """,
                    'during after abstract funcName;'
            ),  # Abstract during function with after aspect
            (
                    """
                    during abstract funcName /* this is documentation */
                    """,
                    'during abstract funcName /*\n    this is documentation\n*/'
            ),  # Abstract during function with documentation
            (
                    """
                    during before abstract funcName /* before aspect documentation */
                    """,
                    'during before abstract funcName /*\n    before aspect documentation\n*/'
            ),  # Abstract during function with before aspect and documentation
            (
                    """
                    during after abstract /* after aspect without function name */
                    """,
                    'during after abstract /*\n    after aspect without function name\n*/'
            ),  # Abstract during function with after aspect, no function name, with documentation
            (
                    """
                    during ref chain.id;
                    """,
                    'during ref chain.id;'
            ),  # Basic during reference function without aspect
            (
                    """
                    during funcName ref chain.id;
                    """,
                    'during funcName ref chain.id;'
            ),  # During reference function with function name
            (
                    """
                    during before ref /absolute.chain.id;
                    """,
                    'during before ref /absolute.chain.id;'
            ),  # During reference function with before aspect and absolute chain ID
            (
                    """
                    during after funcName ref nested.chain.reference;
                    """,
                    'during after funcName ref nested.chain.reference;'
            ),  # During reference function with after aspect, function name and nested chain ID
            (
                    """
                    during { x = y + z * 2; }
                    """,
                    'during {\n    x = y + z * 2;\n}'
            ),  # During operation with complex arithmetic expression
            (
                    """
                    during before { result = sin(angle) + cos(angle); }
                    """,
                    'during before {\n    result = sin(angle) + cos(angle);\n}'
            ),  # During operation with mathematical functions
            (
                    """
                    during after calcFunc { value = (x > 5) ? x * 2 : x / 2; }
                    """,
                    'during after calcFunc {\n    value = (x > 5) ? x * 2 : x / 2;\n}'
            ),  # During operation with conditional expression
            (
                    """
                    during { }
                    """,
                    'during {\n}'
            ),  # During operation with empty block
            (
                    """
                    during before funcName { }
                    """,
                    'during before funcName {\n}'
            ),  # During operation with before aspect and empty block
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="during_definition")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    during;
                    """,
            ),  # Missing operation block or abstract/ref keyword
            (
                    """
                    during {
                    """,
            ),  # Unclosed operation block
            (
                    """
                    during }
                    """,
            ),  # Missing opening brace
            (
                    """
                    during abstract;
                    """,
            ),  # Missing function name for abstract during
            (
                    """
                    during ref;
                    """,
            ),  # Missing chain ID for reference during
            (
                    """
                    during 123func { x = 10; }
                    """,
            ),  # Invalid function name starting with number
            (
                    """
                    during func-name { x = 10; }
                    """,
            ),  # Invalid function name with hyphen
            (
                    """
                    during func name { x = 10; }
                    """,
            ),  # Function name with space
            (
                    """
                    during before abstract { x = 10; }
                    """,
            ),  # Abstract keyword with operation block
            (
                    """
                    during abstract funcName { x = 10; }
                    """,
            ),  # Abstract function with operation block
            (
                    """
                    during abstract funcName ref chain.id;
                    """,
            ),  # Abstract function with reference
            (
                    """
                    during ref { x = 10; }
                    """,
            ),  # Reference keyword with operation block
            (
                    """
                    during funcName ref;
                    """,
            ),  # Reference without chain ID
            (
                    """
                    during ref abstract funcName;
                    """,
            ),  # Reference with abstract keyword
            (
                    """
                    during ref .chain.id;
                    """,
            ),  # Chain ID starting with dot
            (
                    """
                    during ref chain..id;
                    """,
            ),  # Chain ID with consecutive dots
            (
                    """
                    during ref chain.;
                    """,
            ),  # Chain ID ending with dot
            (
                    """
                    during ref /;
                    """,
            ),  # Absolute chain ID with only slash
            (
                    """
                    during { x := 10; }
                    """,
            ),  # Invalid assignment operator in operation
            (
                    """
                    during { x = 10 }
                    """,
            ),  # Missing semicolon in operation
            (
                    """
                    during { x = ; }
                    """,
            ),  # Missing expression in assignment
            (
                    """
                    during { = 10; }
                    """,
            ),  # Missing variable name in assignment
            (
                    """
                    before during { x = 10; }
                    """,
            ),  # Aspect keyword before 'during'
            (
                    """
                    during { x = 10; } before
                    """,
            ),  # Aspect keyword after operation block
            (
                    """
                    during before after { x = 10; }
                    """,
            ),  # Multiple aspect keywords
            (
                    """
                    during before abstract ref chain.id;
                    """,
            ),  # Abstract and reference keywords together
            (
                    """
                    during funcName abstract ref;
                    """,
            ),  # Function name with both abstract and ref
            (
                    """
                    during before funcName abstract { x = 10; };
                    """,
            ),  # Abstract with operation block and semicolon
        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="during_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
