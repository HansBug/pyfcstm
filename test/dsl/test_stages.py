import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLStagesEnter:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                """
                enter { x = 10; y = 20; }
                """,
                EnterOperations(
                    operations=[
                        OperationAssignment(name="x", expr=Integer(raw="10")),
                        OperationAssignment(name="y", expr=Integer(raw="20")),
                    ],
                    name=None,
                ),
            ),  # Basic enter block without function name
            (
                """
                enter initialize { counter = 0; flag = 1; }
                """,
                EnterOperations(
                    operations=[
                        OperationAssignment(name="counter", expr=Integer(raw="0")),
                        OperationAssignment(name="flag", expr=Integer(raw="1")),
                    ],
                    name="initialize",
                ),
            ),  # Enter block with function name 'initialize'
            (
                """
                enter setup { x = sin(3.14); y = cos(1.57); }
                """,
                EnterOperations(
                    operations=[
                        OperationAssignment(
                            name="x", expr=UFunc(func="sin", expr=Float(raw="3.14"))
                        ),
                        OperationAssignment(
                            name="y", expr=UFunc(func="cos", expr=Float(raw="1.57"))
                        ),
                    ],
                    name="setup",
                ),
            ),  # Enter block with function name and mathematical expressions
            (
                """
                enter { }
                """,
                EnterOperations(operations=[], name=None),
            ),  # Empty enter block without function name
            (
                """
                enter init { ; }
                """,
                EnterOperations(operations=[], name="init"),
            ),  # Enter block with function name containing only an empty statement
            (
                """
                enter abstract setup;
                """,
                EnterAbstractFunction(name="setup", doc=None),
            ),  # Abstract enter function declaration with name and semicolon
            (
                """
                enter abstract initialize;
                """,
                EnterAbstractFunction(name="initialize", doc=None),
            ),  # Another abstract enter function declaration with semicolon
            (
                """
                enter abstract /* This function initializes the state */
                """,
                EnterAbstractFunction(
                    name=None, doc="This function initializes the state"
                ),
            ),  # Abstract enter function with multiline comment and no function name
            (
                """
                enter abstract setup /* Sets up initial values for the state variables */
                """,
                EnterAbstractFunction(
                    name="setup", doc="Sets up initial values for the state variables"
                ),
            ),  # Abstract enter function with name and multiline comment
            # (
            #         """
            #         enter abstract /*
            #             Multi-line documentation
            #             This function initializes all variables
            #             Parameters: none
            #             Returns: none
            #         */
            #         """,
            #         EnterAbstractFunction(name=None,
            #                               doc='Multi-line documentation\nThis function initializes all variables\nParameters: none\nReturns: none')
            # ),  # Abstract enter function with multi-line comment spanning several lines
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="enter_definition")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                """
                enter { x = 10; y = 20; }
                """,
                "enter {\n    x = 10;\n    y = 20;\n}",
            ),  # Basic enter block without function name
            (
                """
                enter initialize { counter = 0; flag = 1; }
                """,
                "enter initialize {\n    counter = 0;\n    flag = 1;\n}",
            ),  # Enter block with function name 'initialize'
            (
                """
                enter setup { x = sin(3.14); y = cos(1.57); }
                """,
                "enter setup {\n    x = sin(3.14);\n    y = cos(1.57);\n}",
            ),  # Enter block with function name and mathematical expressions
            (
                """
                enter { }
                """,
                "enter {\n}",
            ),  # Empty enter block without function name
            (
                """
                enter init { ; }
                """,
                "enter init {\n}",
            ),  # Enter block with function name containing only an empty statement
            (
                """
                enter abstract setup;
                """,
                "enter abstract setup;",
            ),  # Abstract enter function declaration with name and semicolon
            (
                """
                enter abstract initialize;
                """,
                "enter abstract initialize;",
            ),  # Another abstract enter function declaration with semicolon
            (
                """
                enter abstract /* This function initializes the state */
                """,
                "enter abstract /*\n    This function initializes the state\n*/",
            ),  # Abstract enter function with multiline comment and no function name
            (
                """
                enter abstract setup /* Sets up initial values for the state variables */
                """,
                "enter abstract setup /*\n    Sets up initial values for the state variables\n*/",
            ),  # Abstract enter function with name and multiline comment
            (
                """
                enter abstract /*
                    Multi-line documentation
                    This function initializes all variables
                    Parameters: none
                    Returns: none
                */
                """,
                "enter abstract /*\n    Multi-line documentation\n    This function initializes all variables\n    Parameters: none\n    Returns: none\n*/",
            ),  # Abstract enter function with multi-line comment spanning several lines
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(input_text, entry_name="enter_definition")
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                """
                enter
                """,
            ),  # Missing required block or abstract declaration after 'enter' keyword
            (
                """
                enter setup
                """,
            ),  # Missing required block after function name
            (
                """
                enter abstract
                """,
            ),  # Incomplete abstract declaration - missing function name or comment
            (
                """
                enter { x = 10 }
                """,
            ),  # Missing semicolon after assignment in enter block
            (
                """
                enter setup() { x = 10; }
                """,
            ),  # Invalid function declaration syntax - parentheses not allowed
            (
                """
                enter abstract setup {}
                """,
            ),  # Abstract function cannot have a block, should use semicolon or comment
            (
                """
                enter abstract setup /* comment */;
                """,
            ),  # Cannot have both comment and semicolon for abstract function
            (
                """
                enter { return x; }
                """,
            ),  # Invalid statement 'return' in enter block - only assignments allowed
            (
                """
                enter setup // This is a comment
                """,
            ),  # Using line comment instead of multiline comment for abstract function
            (
                """
                enter abstract setup /* Unclosed comment
                """,
            ),  # Unclosed multiline comment in abstract function declaration
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="enter_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]


@pytest.mark.unittest
class TestDSLStagesDuring:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                """
                during { x = 10; y = 20; }
                """,
                DuringOperations(
                    aspect=None,
                    operations=[
                        OperationAssignment(name="x", expr=Integer(raw="10")),
                        OperationAssignment(name="y", expr=Integer(raw="20")),
                    ],
                    name=None,
                ),
            ),  # Basic during block with multiple operations
            (
                """
                during processSensors { value = sensor_reading * 2; }
                """,
                DuringOperations(
                    aspect=None,
                    operations=[
                        OperationAssignment(
                            name="value",
                            expr=BinaryOp(
                                expr1=Name(name="sensor_reading"),
                                op="*",
                                expr2=Integer(raw="2"),
                            ),
                        )
                    ],
                    name="processSensors",
                ),
            ),  # During block with a named function
            (
                """
                during before { status = 1; }
                """,
                DuringOperations(
                    aspect="before",
                    operations=[
                        OperationAssignment(name="status", expr=Integer(raw="1"))
                    ],
                    name=None,
                ),
            ),  # During block with 'before' aspect
            (
                """
                during after { result = calculation + offset; }
                """,
                DuringOperations(
                    aspect="after",
                    operations=[
                        OperationAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=Name(name="calculation"),
                                op="+",
                                expr2=Name(name="offset"),
                            ),
                        )
                    ],
                    name=None,
                ),
            ),  # During block with 'after' aspect
            (
                """
                during before updateValues { counter = counter + 1; }
                """,
                DuringOperations(
                    aspect="before",
                    operations=[
                        OperationAssignment(
                            name="counter",
                            expr=BinaryOp(
                                expr1=Name(name="counter"),
                                op="+",
                                expr2=Integer(raw="1"),
                            ),
                        )
                    ],
                    name="updateValues",
                ),
            ),  # During block with both aspect and function name
            (
                """
                during { }
                """,
                DuringOperations(aspect=None, operations=[], name=None),
            ),  # During block with empty operation body
            (
                """
                during { ; ; ; }
                """,
                DuringOperations(aspect=None, operations=[], name=None),
            ),  # During block with only semicolon operations
            (
                """
                during abstract processData;
                """,
                DuringAbstractFunction(name="processData", aspect=None, doc=None),
            ),  # Abstract during with function name and semicolon termination
            (
                """
                during before abstract initializeData;
                """,
                DuringAbstractFunction(
                    name="initializeData", aspect="before", doc=None
                ),
            ),  # Abstract during with 'before' aspect and function name
            (
                """
                during after abstract cleanupData;
                """,
                DuringAbstractFunction(name="cleanupData", aspect="after", doc=None),
            ),  # Abstract during with 'after' aspect and function name
            (
                """
                during abstract /* This function processes sensor data and updates the state */
                """,
                DuringAbstractFunction(
                    name=None,
                    aspect=None,
                    doc="This function processes sensor data and updates the state",
                ),
            ),  # Abstract during with multiline comment documentation
            (
                """
                during abstract processData /* Handles all sensor data processing logic */
                """,
                DuringAbstractFunction(
                    name="processData",
                    aspect=None,
                    doc="Handles all sensor data processing logic",
                ),
            ),  # Abstract during with function name and multiline comment
            (
                """
                during before abstract /* Initialize all sensors before processing */
                """,
                DuringAbstractFunction(
                    name=None,
                    aspect="before",
                    doc="Initialize all sensors before processing",
                ),
            ),  # Abstract during with 'before' aspect and multiline comment
            (
                """
                during after abstract cleanupResources /* Free all allocated memory */
                """,
                DuringAbstractFunction(
                    name="cleanupResources",
                    aspect="after",
                    doc="Free all allocated memory",
                ),
            ),  # Abstract during with 'after' aspect, function name and multiline comment
            (
                """
                during calculateResults { result = (value * 2) + (offset - 5); status = (condition > 0) ? 0x1 : 0x2; }
                """,
                DuringOperations(
                    aspect=None,
                    operations=[
                        OperationAssignment(
                            name="result",
                            expr=BinaryOp(
                                expr1=Paren(
                                    expr=BinaryOp(
                                        expr1=Name(name="value"),
                                        op="*",
                                        expr2=Integer(raw="2"),
                                    )
                                ),
                                op="+",
                                expr2=Paren(
                                    expr=BinaryOp(
                                        expr1=Name(name="offset"),
                                        op="-",
                                        expr2=Integer(raw="5"),
                                    )
                                ),
                            ),
                        ),
                        OperationAssignment(
                            name="status",
                            expr=ConditionalOp(
                                cond=BinaryOp(
                                    expr1=Name(name="condition"),
                                    op=">",
                                    expr2=Integer(raw="0"),
                                ),
                                value_true=HexInt(raw="0x1"),
                                value_false=HexInt(raw="0x2"),
                            ),
                        ),
                    ],
                    name="calculateResults",
                ),
            ),  # During block with complex expressions in operations
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="during_definition")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                """
                during { x = 10; y = 20; }
                """,
                "during {\n    x = 10;\n    y = 20;\n}",
            ),  # Basic during block with multiple operations
            (
                """
                during processSensors { value = sensor_reading * 2; }
                """,
                "during processSensors {\n    value = sensor_reading * 2;\n}",
            ),  # During block with a named function
            (
                """
                during before { status = 1; }
                """,
                "during before {\n    status = 1;\n}",
            ),  # During block with 'before' aspect
            (
                """
                during after { result = calculation + offset; }
                """,
                "during after {\n    result = calculation + offset;\n}",
            ),  # During block with 'after' aspect
            (
                """
                during before updateValues { counter = counter + 1; }
                """,
                "during before updateValues {\n    counter = counter + 1;\n}",
            ),  # During block with both aspect and function name
            (
                """
                during { }
                """,
                "during {\n}",
            ),  # During block with empty operation body
            (
                """
                during { ; ; ; }
                """,
                "during {\n}",
            ),  # During block with only semicolon operations
            (
                """
                during abstract processData;
                """,
                "during abstract processData;",
            ),  # Abstract during with function name and semicolon termination
            (
                """
                during before abstract initializeData;
                """,
                "during before abstract initializeData;",
            ),  # Abstract during with 'before' aspect and function name
            (
                """
                during after abstract cleanupData;
                """,
                "during after abstract cleanupData;",
            ),  # Abstract during with 'after' aspect and function name
            (
                """
                during abstract /* This function processes sensor data and updates the state */
                """,
                "during abstract /*\n    This function processes sensor data and updates the state\n*/",
            ),  # Abstract during with multiline comment documentation
            (
                """
                during abstract processData /* Handles all sensor data processing logic */
                """,
                "during abstract processData /*\n    Handles all sensor data processing logic\n*/",
            ),  # Abstract during with function name and multiline comment
            (
                """
                during before abstract /* Initialize all sensors before processing */
                """,
                "during before abstract /*\n    Initialize all sensors before processing\n*/",
            ),  # Abstract during with 'before' aspect and multiline comment
            (
                """
                during after abstract cleanupResources /* Free all allocated memory */
                """,
                "during after abstract cleanupResources /*\n    Free all allocated memory\n*/",
            ),  # Abstract during with 'after' aspect, function name and multiline comment
            (
                """
                during calculateResults { result = (value * 2) + (offset - 5); status = (condition > 0) ? 0x1 : 0x2; }
                """,
                "during calculateResults {\n    result = (value * 2) + (offset - 5);\n    status = (condition > 0) ? 0x1 : 0x2;\n}",
            ),  # During block with complex expressions in operations
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(input_text, entry_name="during_definition")
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                """
                during processData x = 10; }
                """,
            ),  # Missing opening brace in during block
            (
                """
                during { x = 10; y = 20;
                """,
            ),  # Missing closing brace in during block
            # (
            #         """
            #         during middle { x = 10; }
            #         """,
            # ),  # Invalid aspect name 'middle' - only 'before' or 'after' are allowed
            (
                """
                during middle middle { x = 10; }
                """,
            ),  # Invalid aspect name 'middle' - only 'before' or 'after' are allowed
            (
                """
                during abstract processData
                """,
            ),  # Missing semicolon in abstract during definition
            (
                """
                during { x = 10 y = 20; }
                """,
            ),  # Missing semicolon after assignment in during block
            (
                """
                during { x := 10; }
                """,
            ),  # Wrong assignment operator ':=' in during block (should be '=')
            (
                """
                abstract during { x = 10; }
                """,
            ),  # Abstract keyword in wrong position (should be after 'during')
            (
                """
                during abstract ;
                """,
            ),  # Missing required function name in abstract during definition
            (
                """
                during abstract processData { x = 10; }
                """,
            ),  # Invalid combination of 'abstract' keyword with operation block
            (
                """
                during abstract // This is a comment
                """,
            ),  # Invalid comment format (line comment instead of multiline comment)
            (
                """
                during before after { x = 10; }
                """,
            ),  # Multiple aspects specified (only one of 'before' or 'after' allowed)
            (
                """
                during { x = 10; if(x > 0) { y = 20; } }
                """,
            ),  # Invalid control flow statement inside during operation block
            (
                """
                during abstract
                """,
            ),  # Incomplete abstract during definition (missing semicolon or comment)
            (
                """
                during processData before { x = 10; }
                """,
            ),  # Invalid placement of aspect (should be before function name)
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="during_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]


@pytest.mark.unittest
class TestDSLStagesExit:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                """
                exit { x = 10; y = 20; }
                """,
                ExitOperations(
                    operations=[
                        OperationAssignment(name="x", expr=Integer(raw="10")),
                        OperationAssignment(name="y", expr=Integer(raw="20")),
                    ],
                    name=None,
                ),
            ),  # Basic exit block without function name
            (
                """
                exit initialize { counter = 0; flag = 1; }
                """,
                ExitOperations(
                    operations=[
                        OperationAssignment(name="counter", expr=Integer(raw="0")),
                        OperationAssignment(name="flag", expr=Integer(raw="1")),
                    ],
                    name="initialize",
                ),
            ),  # Exit block with function name 'initialize'
            (
                """
                exit setup { x = sin(3.14); y = cos(1.57); }
                """,
                ExitOperations(
                    operations=[
                        OperationAssignment(
                            name="x", expr=UFunc(func="sin", expr=Float(raw="3.14"))
                        ),
                        OperationAssignment(
                            name="y", expr=UFunc(func="cos", expr=Float(raw="1.57"))
                        ),
                    ],
                    name="setup",
                ),
            ),  # Exit block with function name and mathematical expressions
            (
                """
                exit { }
                """,
                ExitOperations(operations=[], name=None),
            ),  # Empty exit block without function name
            (
                """
                exit init { ; }
                """,
                ExitOperations(operations=[], name="init"),
            ),  # Exit block with function name containing only an empty statement
            (
                """
                exit abstract setup;
                """,
                ExitAbstractFunction(name="setup", doc=None),
            ),  # Abstract exit function declaration with name and semicolon
            (
                """
                exit abstract initialize;
                """,
                ExitAbstractFunction(name="initialize", doc=None),
            ),  # Another abstract exit function declaration with semicolon
            (
                """
                exit abstract /* This function initializes the state */
                """,
                ExitAbstractFunction(
                    name=None, doc="This function initializes the state"
                ),
            ),  # Abstract exit function with multiline comment and no function name
            (
                """
                exit abstract setup /* Sets up initial values for the state variables */
                """,
                ExitAbstractFunction(
                    name="setup", doc="Sets up initial values for the state variables"
                ),
            ),  # Abstract exit function with name and multiline comment
            # (
            #         """
            #         exit abstract /*
            #             Multi-line documentation
            #             This function initializes all variables
            #             Parameters: none
            #             Returns: none
            #         */
            #         """,
            #         ExitAbstractFunction(name=None,
            #                              doc='Multi-line documentation\nThis function initializes all variables\nParameters: none\nReturns: none')
            # ),  # Abstract exit function with multi-line comment spanning several lines
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="exit_definition")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                """
                exit { x = 10; y = 20; }
                """,
                "exit {\n    x = 10;\n    y = 20;\n}",
            ),  # Basic exit block without function name
            (
                """
                exit initialize { counter = 0; flag = 1; }
                """,
                "exit initialize {\n    counter = 0;\n    flag = 1;\n}",
            ),  # Exit block with function name 'initialize'
            (
                """
                exit setup { x = sin(3.14); y = cos(1.57); }
                """,
                "exit setup {\n    x = sin(3.14);\n    y = cos(1.57);\n}",
            ),  # Exit block with function name and mathematical expressions
            (
                """
                exit { }
                """,
                "exit {\n}",
            ),  # Empty exit block without function name
            (
                """
                exit init { ; }
                """,
                "exit init {\n}",
            ),  # Exit block with function name containing only an empty statement
            (
                """
                exit abstract setup;
                """,
                "exit abstract setup;",
            ),  # Abstract exit function declaration with name and semicolon
            (
                """
                exit abstract initialize;
                """,
                "exit abstract initialize;",
            ),  # Another abstract exit function declaration with semicolon
            (
                """
                exit abstract /* This function initializes the state */
                """,
                "exit abstract /*\n    This function initializes the state\n*/",
            ),  # Abstract exit function with multiline comment and no function name
            (
                """
                exit abstract setup /* Sets up initial values for the state variables */
                """,
                "exit abstract setup /*\n    Sets up initial values for the state variables\n*/",
            ),  # Abstract exit function with name and multiline comment
            (
                """
                exit abstract /*
                    Multi-line documentation
                    This function initializes all variables
                    Parameters: none
                    Returns: none
                */
                """,
                "exit abstract /*\n    Multi-line documentation\n    This function initializes all variables\n    Parameters: none\n    Returns: none\n*/",
            ),  # Abstract exit function with multi-line comment spanning several lines
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(input_text, entry_name="exit_definition")
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                """
                exit
                """,
            ),  # Missing required block or abstract declaration after 'exit' keyword
            (
                """
                exit setup
                """,
            ),  # Missing required block after function name
            (
                """
                exit abstract
                """,
            ),  # Incomplete abstract declaration - missing function name or comment
            (
                """
                exit { x = 10 }
                """,
            ),  # Missing semicolon after assignment in exit block
            (
                """
                exit setup() { x = 10; }
                """,
            ),  # Invalid function declaration syntax - parentheses not allowed
            (
                """
                exit abstract setup {}
                """,
            ),  # Abstract function cannot have a block, should use semicolon or comment
            (
                """
                exit abstract setup /* comment */;
                """,
            ),  # Cannot have both comment and semicolon for abstract function
            (
                """
                exit { return x; }
                """,
            ),  # Invalid statement 'return' in exit block - only assignments allowed
            (
                """
                exit setup // This is a comment
                """,
            ),  # Using line comment instead of multiline comment for abstract function
            (
                """
                exit abstract setup /* Unclosed comment
                """,
            ),  # Unclosed multiline comment in abstract function declaration
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="exit_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
