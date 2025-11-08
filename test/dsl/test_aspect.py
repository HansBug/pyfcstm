import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLStagesDuringAspect:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                """
                >> during before { x = 10; }
                """,
                DuringAspectOperations(
                    aspect="before",
                    operations=[OperationAssignment(name="x", expr=Integer(raw="10"))],
                    name=None,
                ),
            ),  # Valid during aspect with 'before' aspect and no function name, containing an operation assignment
            (
                """
                >> during after { y = 5; z = 20; }
                """,
                DuringAspectOperations(
                    aspect="after",
                    operations=[
                        OperationAssignment(name="y", expr=Integer(raw="5")),
                        OperationAssignment(name="z", expr=Integer(raw="20")),
                    ],
                    name=None,
                ),
            ),  # Valid during aspect with 'after' aspect and no function name, containing multiple operation assignments
            (
                """
                >> during before process { }
                """,
                DuringAspectOperations(aspect="before", operations=[], name="process"),
            ),  # Valid during aspect with 'before' aspect and named function 'process', with empty operation block
            (
                """
                >> during after handleEvent { x = x + 1; }
                """,
                DuringAspectOperations(
                    aspect="after",
                    operations=[
                        OperationAssignment(
                            name="x",
                            expr=BinaryOp(
                                expr1=Name(name="x"), op="+", expr2=Integer(raw="1")
                            ),
                        )
                    ],
                    name="handleEvent",
                ),
            ),  # Valid during aspect with 'after' aspect and named function 'handleEvent', containing an operation
            (
                """
                >> during before abstract validateInput;
                """,
                DuringAspectAbstractFunction(
                    name="validateInput", aspect="before", doc=None
                ),
            ),  # Valid abstract during aspect with 'before' aspect and function name ending with semicolon
            (
                """
                >> during before abstract /* This function validates all inputs before processing */
                """,
                DuringAspectAbstractFunction(
                    name=None,
                    aspect="before",
                    doc="This function validates all inputs before processing",
                ),
            ),  # Valid abstract during aspect with 'before' aspect, no function name and multiline comment documentation
            # (
            #         """
            #         >> during after abstract processData /*
            #            This handles post-processing of data
            #            after the main execution
            #         */
            #         """,
            #         DuringAspectAbstractFunction(name='processData', aspect='after',
            #                                      doc='This handles post-processing of data\nafter the main execution')
            # ),  # Valid abstract during aspect with 'after' aspect, function name and multiline comment documentation
            (
                """
                >> during before { ; }
                """,
                DuringAspectOperations(aspect="before", operations=[], name=None),
            ),  # Valid during aspect with 'before' aspect containing only an empty statement
            (
                """
                >> during after compute { x = sin(y); }
                """,
                DuringAspectOperations(
                    aspect="after",
                    operations=[
                        OperationAssignment(
                            name="x", expr=UFunc(func="sin", expr=Name(name="y"))
                        )
                    ],
                    name="compute",
                ),
            ),  # Valid during aspect with 'after' aspect and function using a mathematical function in operation
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="during_aspect_definition")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                """
                >> during before { x = 10; }
                """,
                ">> during before {\n    x = 10;\n}",
            ),  # Valid during aspect with 'before' aspect and no function name, containing an operation assignment
            (
                """
                >> during after { y = 5; z = 20; }
                """,
                ">> during after {\n    y = 5;\n    z = 20;\n}",
            ),  # Valid during aspect with 'after' aspect and no function name, containing multiple operation assignments
            (
                """
                >> during before process { }
                """,
                ">> during before process {\n}",
            ),  # Valid during aspect with 'before' aspect and named function 'process', with empty operation block
            (
                """
                >> during after handleEvent { x = x + 1; }
                """,
                ">> during after handleEvent {\n    x = x + 1;\n}",
            ),  # Valid during aspect with 'after' aspect and named function 'handleEvent', containing an operation
            (
                """
                >> during before abstract validateInput;
                """,
                ">> during before abstract validateInput;",
            ),  # Valid abstract during aspect with 'before' aspect and function name ending with semicolon
            (
                """
                >> during before abstract /* This function validates all inputs before processing */
                """,
                ">> during before abstract /*\n    This function validates all inputs before processing\n*/",
            ),  # Valid abstract during aspect with 'before' aspect, no function name and multiline comment documentation
            (
                """
                >> during after abstract processData /*
                   This handles post-processing of data
                   after the main execution
                */
                """,
                ">> during after abstract processData /*\n    This handles post-processing of data\n    after the main execution\n*/",
            ),  # Valid abstract during aspect with 'after' aspect, function name and multiline comment documentation
            (
                """
                >> during before { ; }
                """,
                ">> during before {\n}",
            ),  # Valid during aspect with 'before' aspect containing only an empty statement
            (
                """
                >> during after compute { x = sin(y); }
                """,
                ">> during after compute {\n    x = sin(y);\n}",
            ),  # Valid during aspect with 'after' aspect and function using a mathematical function in operation
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(
                    input_text, entry_name="during_aspect_definition"
                )
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                """
                during before { x = 10; }
                """,
            ),  # Missing '>>' prefix required for during_aspect_definition
            (
                """
                >> during { x = 5; }
                """,
            ),  # Missing required aspect specifier ('before' or 'after')
            (
                """
                >> during middle { x = 10; }
                """,
            ),  # Invalid aspect specifier 'middle' - only 'before' or 'after' are allowed
            (
                """
                >> during before process
                """,
            ),  # Missing opening brace '{' for operation block
            (
                """
                >> during after handleEvent { x = 1 }
                """,
            ),  # Missing semicolon after operation assignment
            (
                """
                >> during before abstract
                """,
            ),  # Missing semicolon or multiline comment after abstract declaration
            (
                """
                >> during after abstract validateInput
                """,
            ),  # Missing semicolon after abstract function declaration
            (
                """
                >> during before { x = 5; y = 10 }
                """,
            ),  # Missing semicolon after the last operation assignment
            (
                """
                >> during after abstract validateInput // Simple validation
                """,
            ),  # Using line comment instead of required multiline comment for abstract documentation
            (
                """
                >> before during { x = 10; }
                """,
            ),  # Incorrect order of keywords - 'during' must come before aspect specifier
            (
                """
                >> during after abstract handleEvent { x = 5; }
                """,
            ),  # Cannot have both 'abstract' keyword and operation block
            (
                """
                >> during before process() { x = 10; }
                """,
            ),  # Function name should not include parentheses
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="during_aspect_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
