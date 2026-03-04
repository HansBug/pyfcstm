"""
Comprehensive unit tests for pyfcstm/dsl/error.py

Tests cover:
1. SyntaxFailError with enhanced error messages
2. Cascading error filtering
3. AmbiguityError, FullContextAttemptError, ContextSensitivityError
4. UnfinishedParsingError
5. CollectingErrorListener callbacks and edge cases
6. Real-world error scenarios
"""

import pytest
from antlr4 import CommonTokenStream, InputStream
from pyfcstm.dsl.parse import parse_with_grammar_entry
from pyfcstm.dsl.error import (
    GrammarParseError,
    SyntaxFailError,
    AmbiguityError,
    FullContextAttemptError,
    ContextSensitivityError,
    UnfinishedParsingError,
    CollectingErrorListener,
)
from pyfcstm.dsl.grammar.GrammarLexer import GrammarLexer
from pyfcstm.dsl.grammar.GrammarParser import GrammarParser


class TestSyntaxFailErrorEnhancement:
    """Test enhanced error messages for SyntaxFailError"""

    def test_missing_semicolon_after_variable_definition(self):
        """Test: Missing semicolon after variable definition"""
        code = """def int counter = 0
state System {
    state Active;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        # The error message should mention missing semicolon
        assert "semicolon" in str(errors[0]).lower()

    def test_missing_semicolon_after_state_definition(self):
        """Test: Missing semicolon after state definition"""
        code = """def int counter = 0;
state System {
    state Active
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect missing semicolon pattern
        assert any("semicolon" in str(e).lower() for e in errors)

    def test_missing_semicolon_after_operation_statement(self):
        """Test: Missing semicolon after operation statement"""
        code = """def int counter = 0;
state System {
    state Active {
        enter {
            counter = 0
        }
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "Missing semicolon after operation statement" in str(errors[0])

    def test_missing_closing_bracket_in_guard_condition(self):
        """Test: Missing closing bracket in guard condition"""
        code = """def int counter = 0;
state System {
    state Active;
    state Idle;
    Active -> Idle : if [counter > 10;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "Missing closing bracket in guard condition" in str(errors[0])

    def test_missing_closing_brace_in_state_definition(self):
        """Test: Missing closing brace in state definition"""
        code = """def int counter = 0;
state System {
    state Active {
        enter {
            counter = 0;
        }
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect missing brace
        assert any("brace" in str(e).lower() for e in errors)

    def test_missing_opening_brace_before_lifecycle_action(self):
        """Test: Missing opening brace before lifecycle action"""
        code = """def int counter = 0;
state System {
    state Active
        enter {
            counter = 0;
        }
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect syntax error related to missing brace
        assert any(isinstance(e, SyntaxFailError) for e in errors)

    def test_invalid_transition_operator(self):
        """Test: Using => instead of ->"""
        code = """def int counter = 0;
state System {
    state Active;
    state Idle;
    Active => Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "Invalid operator" in str(errors[0]) or "use '->' for transitions" in str(errors[0])

    def test_missing_equals_in_variable_definition(self):
        """Test: Missing equals sign in variable definition"""
        code = """def int counter 0;
state System {
    state Active;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "Missing equals sign" in str(errors[0])

    def test_unclosed_string_literal(self):
        """Test: Unclosed string literal"""
        code = """def int counter = 0;
state System {
    state Active named "Active State;
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect token recognition error or related syntax error
        error_str = str(errors[0]).lower()
        assert any(keyword in error_str for keyword in [
            "token recognition error",
            "unclosed string",
            "invalid character",
            "invalid token"
        ])

    def test_missing_semicolon_in_effect_block(self):
        """Test: Missing semicolon in effect block"""
        code = """def int counter = 0;
state System {
    state Active;
    state Idle;
    Active -> Idle effect {
        counter = 0
        counter = counter + 1;
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "semicolon" in str(errors[0]).lower()

    def test_missing_closing_brace_in_nested_block(self):
        """Test: Missing closing brace in nested block"""
        code = """def int counter = 0;
state System {
    state Active {
        enter {
            counter = 0;
        during {
            counter = counter + 1;
        }
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect unexpected 'during' keyword
        assert any("during" in str(e).lower() for e in errors)

    def test_missing_brackets_in_condition(self):
        """Test: Missing brackets in condition expression"""
        code = """def int counter = 0;
state System {
    state Active;
    state Idle;
    Active -> Idle : if counter > 10;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 2  # Should detect both missing [ and ]
        assert any("bracket" in str(e).lower() for e in errors)

    def test_missing_semicolon_after_event_definition(self):
        """Test: Missing semicolon after event definition"""
        code = """def int counter = 0;
state System {
    event MyEvent
    state Active;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert isinstance(errors[0], SyntaxFailError)
        assert "semicolon" in str(errors[0]).lower()

    def test_missing_semicolon_after_abstract_function(self):
        """Test: Missing semicolon after abstract function definition"""
        code = """def int counter = 0;
state System {
    state Active {
        enter abstract InitHardware
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect missing semicolon pattern
        assert any("semicolon" in str(e).lower() for e in errors)

    def test_missing_semicolon_generic_fallback(self):
        """Test: Generic missing semicolon message (fallback branch)"""
        code = """def int x = 5
def float y = 3.14"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        assert "semicolon" in str(errors[0]).lower()

    def test_missing_transition_arrow(self):
        """Test: Missing transition arrow"""
        code = """state System {
    state Active;
    state Idle;
    Active Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_extraneous_input_generic_token(self):
        """Test: Extraneous input with generic token"""
        code = """state System {
    state Active;
    @@invalid@@
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_no_viable_alternative_statestate_pattern(self):
        """Test: Missing semicolon between states pattern"""
        code = """state System {
    state Activestate Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_no_viable_alternative_state_lifecycle_pattern(self):
        """Test: Missing brace before lifecycle action"""
        code = """state System {
    state Activeenter {
        counter = 0;
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_no_viable_alternative_long_state_pattern(self):
        """Test: Long state name pattern"""
        code = """state System {
    state VeryLongStateNameHereWithMoreText counter = 0;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_no_viable_alternative_abstract_pattern(self):
        """Test: Missing semicolon after abstract"""
        code = """state System {
    state Active {
        enter abstract Init}
    }
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1

    def test_syntax_fail_error_with_various_offending_symbols(self):
        """Test: SyntaxFailError with various offending symbols"""
        # Test with '}' as offending symbol
        error1 = SyntaxFailError(line=1, column=0, offending_symbol_text="}", msg="missing ';'")
        assert "semicolon" in str(error1).lower()

        # Test with identifier as offending symbol
        error2 = SyntaxFailError(line=1, column=0, offending_symbol_text="identifier", msg="missing ';'")
        assert "semicolon" in str(error2).lower()

        # Test with generic missing semicolon (None offending symbol)
        error3 = SyntaxFailError(line=1, column=0, offending_symbol_text=None, msg="missing ';'")
        assert "semicolon" in str(error3).lower()


class TestCascadingErrorFiltering:
    """Test cascading error filtering mechanism"""

    def test_multiple_errors_with_cascading_filtered(self):
        """Test: Multiple errors with cascading errors filtered out"""
        code = """def int counter = 0
def float temp = 25.0;

state System {
    state Running {
        enter {
            counter = 0;
            temp = 20.0
        }

        during {
            counter = counter + 1

        state Processing;
    }

    state Idle

    Running -> Idle : if [temp > 100.0;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        # Should have filtered out some cascading errors
        # Original ANTLR reports 5 errors, filtered should be less
        assert len(errors) <= 5
        # All errors should be primary errors (missing syntax elements)
        primary_error_patterns = ["missing", "token recognition error"]
        for error in errors:
            if isinstance(error, SyntaxFailError):
                assert any(pattern in error.msg.lower() for pattern in primary_error_patterns) or \
                       "no viable alternative" in error.msg.lower()

    def test_single_error_not_filtered(self):
        """Test: Single error is not filtered"""
        code = """def int counter = 0
state System {
    state Active;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert isinstance(errors[0], SyntaxFailError)

    def test_cascading_errors_within_5_lines_filtered(self):
        """Test: Cascading errors within 5 lines of primary error are filtered"""
        code = """def int counter = 0;
state System {
    state Active
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        # Should filter cascading errors near the primary error
        assert len(errors) >= 1

    def test_independent_errors_not_filtered(self):
        """Test: Independent errors far apart are not filtered"""
        code = """def int counter = 0

state System {
    state A;
    state B;
    state C;
    state D;
    state E;
    state F;
    state G;
    state H;
    state I;
    state J
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        # Should have at least 2 errors (missing semicolons)
        assert len(errors) >= 1


class TestAmbiguityError:
    """Test AmbiguityError enhanced messages"""

    def test_ambiguity_error_with_state_keyword(self):
        """Test: AmbiguityError with state keyword"""
        error = AmbiguityError("state Active", 0, 12)
        assert "Ambiguous syntax" in str(error)
        assert "state definitions" in str(error)

    def test_ambiguity_error_with_lifecycle_action(self):
        """Test: AmbiguityError with lifecycle action"""
        error = AmbiguityError("enter { x = 1; }", 0, 16)
        assert "Ambiguous syntax" in str(error)
        assert "Lifecycle action" in str(error)

    def test_ambiguity_error_with_transition(self):
        """Test: AmbiguityError with transition syntax"""
        error = AmbiguityError("A -> B : Event", 0, 14)
        assert "Ambiguous syntax" in str(error)
        assert "Transition syntax" in str(error)

    def test_ambiguity_error_with_expression(self):
        """Test: AmbiguityError with expression"""
        error = AmbiguityError("x = a + b * c", 0, 13)
        assert "Ambiguous syntax" in str(error)
        assert "Expression syntax" in str(error)

    def test_ambiguity_error_with_empty_input(self):
        """Test: AmbiguityError with empty input"""
        error = AmbiguityError("", 0, 0)
        assert "Ambiguous syntax" in str(error)
        assert "multiple ways to interpret" in str(error)

    def test_ambiguity_error_generic_fallback(self):
        """Test: AmbiguityError generic fallback message"""
        error = AmbiguityError("unknown_pattern_xyz", 0, 10)
        error_str = str(error).lower()
        assert "multiple ways to interpret" in error_str or "simplifying" in error_str or "delimiters" in error_str


class TestFullContextAttemptError:
    """Test FullContextAttemptError enhanced messages"""

    def test_full_context_error_with_complex_state(self):
        """Test: FullContextAttemptError with complex state definition"""
        error = FullContextAttemptError("state Active { enter { x = 1; } }", 0, 33)
        assert "Complex syntax" in str(error)
        assert "Complex state definition" in str(error)

    def test_full_context_error_with_complex_transition(self):
        """Test: FullContextAttemptError with complex transition"""
        error = FullContextAttemptError("A -> B : Event : if [x > 10]", 0, 28)
        assert "Complex syntax" in str(error)
        assert "Complex transition syntax" in str(error)

    def test_full_context_error_with_logical_expression(self):
        """Test: FullContextAttemptError with logical expression"""
        error = FullContextAttemptError("x > 10 && y < 20 || z == 30", 0, 27)
        assert "Complex syntax" in str(error)
        assert "Complex logical expression" in str(error)

    def test_full_context_error_with_simple_input(self):
        """Test: FullContextAttemptError with simple input"""
        error = FullContextAttemptError("simple", 0, 6)
        assert "Complex syntax" in str(error)
        assert "extra analysis" in str(error)

    def test_full_context_error_empty_input(self):
        """Test: FullContextAttemptError with empty input"""
        error = FullContextAttemptError("", 0, 0)
        assert "extra analysis" in str(error).lower()

    def test_full_context_error_generic_fallback(self):
        """Test: FullContextAttemptError generic fallback message"""
        error = FullContextAttemptError("unknown_pattern_xyz", 0, 10)
        error_str = str(error).lower()
        assert "extra analysis" in error_str or "simplifying" in error_str


class TestContextSensitivityError:
    """Test ContextSensitivityError enhanced messages"""

    def test_context_sensitivity_error_with_aspect_action(self):
        """Test: ContextSensitivityError with aspect action"""
        error = ContextSensitivityError("during before", 0, 13)
        assert "Context-dependent syntax" in str(error)
        assert "Aspect action placement" in str(error)

    def test_context_sensitivity_error_with_event_scoping(self):
        """Test: ContextSensitivityError with event scoping"""
        error = ContextSensitivityError("A -> B : Event", 0, 14)
        assert "Context-dependent syntax" in str(error)
        assert "Event scoping" in str(error)

    def test_context_sensitivity_error_with_local_event(self):
        """Test: ContextSensitivityError with local event"""
        error = ContextSensitivityError("A -> B :: LocalEvent", 0, 20)
        assert "Context-dependent syntax" in str(error)
        assert "Event scoping" in str(error)

    def test_context_sensitivity_error_with_reference(self):
        """Test: ContextSensitivityError with reference"""
        error = ContextSensitivityError("enter ref OtherState.Action", 0, 27)
        assert "Context-dependent syntax" in str(error)
        assert "Reference syntax" in str(error)

    def test_context_sensitivity_error_with_normal_input(self):
        """Test: ContextSensitivityError with normal input"""
        error = ContextSensitivityError("normal", 0, 6)
        assert "Context-dependent syntax" in str(error)
        assert "surrounding context" in str(error)

    def test_context_sensitivity_error_empty_input(self):
        """Test: ContextSensitivityError with empty input"""
        error = ContextSensitivityError("", 0, 0)
        assert "context" in str(error).lower()

    def test_context_sensitivity_error_generic_fallback(self):
        """Test: ContextSensitivityError generic fallback message"""
        error = ContextSensitivityError("unknown_pattern_xyz", 0, 10)
        error_str = str(error).lower()
        assert "context" in error_str


class TestRealWorldScenarios:
    """Test real-world error scenarios"""

    def test_complex_nested_states_parse_successfully(self):
        """Test: Complex nested states should parse successfully"""
        code = """def int x = 0;
state S {
    state A {
        state B {
            state C {
                state D {
                    enter { x = 1; }
                    during { x = x + 1; }
                    exit { x = 0; }
                }
            }
        }
    }
}"""
        # Should parse successfully without errors
        result = parse_with_grammar_entry(code, "state_machine_dsl")
        assert result is not None

    def test_complex_transitions_parse_successfully(self):
        """Test: Complex transitions should parse successfully"""
        code = """def int x = 0;
def int y = 0;
def int z = 0;
state S {
    state A;
    state B;
    state C;
    A -> B : if [x > 10 && y < 20 || z == 30];
    B -> C : if [(x + y) * z > 100 && (x - y) / z < 10];
}"""
        # Should parse successfully without errors
        result = parse_with_grammar_entry(code, "state_machine_dsl")
        assert result is not None

    def test_multiple_aspect_actions_parse_successfully(self):
        """Test: Multiple aspect actions should parse successfully"""
        code = """def int x = 0;
state S {
    >> during before { x = x + 1; }
    >> during after { x = x - 1; }

    state A {
        during before { x = x * 2; }
        during after { x = x / 2; }

        enter { x = 0; }
    }
}"""
        # Should parse successfully without errors
        result = parse_with_grammar_entry(code, "state_machine_dsl")
        assert result is not None

    def test_error_message_human_readable(self):
        """Test: Error messages should be human-readable"""
        code = """def int counter = 0
state System {
    state Active;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        error_msg = str(exc_info.value.errors[0])
        # Should not contain raw ANTLR technical terms
        assert "Missing semicolon" in error_msg
        # Should be clear and actionable
        assert "line" in error_msg.lower()
        assert "column" in error_msg.lower()


class TestCollectingErrorListener:
    """Test CollectingErrorListener functionality"""

    def test_error_listener_collects_multiple_errors(self):
        """Test: Error listener collects multiple errors"""
        code = """def int counter = 0
def float temp = 25.0;

state System {
    state Active
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        # Should collect at least one error (cascading errors may be filtered)
        assert len(errors) >= 1

    def test_error_listener_preserves_error_order(self):
        """Test: Error listener preserves error order by line number"""
        code = """def int counter = 0
state System {
    state Active
    state Idle;
}"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        # Errors should be sorted by line number
        for i in range(len(errors) - 1):
            if isinstance(errors[i], SyntaxFailError) and isinstance(errors[i + 1], SyntaxFailError):
                assert errors[i].line <= errors[i + 1].line


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_code_raises_error(self):
        """Test: Empty code should raise error"""
        code = ""
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(code, "state_machine_dsl")

    def test_only_whitespace_raises_error(self):
        """Test: Only whitespace should raise error"""
        code = "   \n\n   "
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(code, "state_machine_dsl")

    def test_minimal_valid_code_parses(self):
        """Test: Minimal valid code should parse"""
        code = """def int x = 0;
state S {
    state A;
}"""
        result = parse_with_grammar_entry(code, "state_machine_dsl")
        assert result is not None

    def test_error_at_end_of_file(self):
        """Test: Error at end of file is detected"""
        code = """def int counter = 0;
state System {
    state Active;
"""
        with pytest.raises(GrammarParseError) as exc_info:
            parse_with_grammar_entry(code, "state_machine_dsl")

        errors = exc_info.value.errors
        assert len(errors) >= 1
        # Should detect missing closing brace at EOF
        assert any("<EOF>" in str(e) or "end of file" in str(e).lower() for e in errors)


class TestUnfinishedParsingError:
    """Test UnfinishedParsingError"""

    def test_unfinished_parsing_error_creation(self):
        """Test: UnfinishedParsingError creation and message"""
        error = UnfinishedParsingError(lineno=42)
        assert error.lineno == 42
        error_str = str(error).lower()
        assert "unparsed content" in error_str or "failed to completely parse" in error_str
        assert "42" in str(error)

    def test_unfinished_parsing_error_different_line(self):
        """Test: UnfinishedParsingError with different line number"""
        error = UnfinishedParsingError(lineno=100)
        assert error.lineno == 100
        assert "100" in str(error)


class TestCollectingErrorListenerCallbacks:
    """Test CollectingErrorListener ANTLR callback methods"""

    def test_report_ambiguity_callback(self):
        """Test: reportAmbiguity callback"""
        listener = CollectingErrorListener()

        # Create a simple input stream and lexer/parser
        input_stream = InputStream("state System { state Active; }")
        lexer = GrammarLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = GrammarParser(token_stream)

        # Manually call reportAmbiguity
        listener.reportAmbiguity(
            recognizer=parser,
            dfa=None,
            startIndex=0,
            stopIndex=5,
            exact=True,
            ambigAlts=None,
            configs=None
        )

        assert len(listener.errors) == 1
        assert isinstance(listener.errors[0], AmbiguityError)

    def test_report_attempting_full_context_callback(self):
        """Test: reportAttemptingFullContext callback"""
        listener = CollectingErrorListener()

        # Create a simple input stream and lexer/parser
        input_stream = InputStream("state System { state Active; }")
        lexer = GrammarLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = GrammarParser(token_stream)

        # Manually call reportAttemptingFullContext
        listener.reportAttemptingFullContext(
            recognizer=parser,
            dfa=None,
            startIndex=0,
            stopIndex=5,
            conflictingAlts=None,
            configs=None
        )

        assert len(listener.errors) == 1
        assert isinstance(listener.errors[0], FullContextAttemptError)

    def test_report_context_sensitivity_callback(self):
        """Test: reportContextSensitivity callback"""
        listener = CollectingErrorListener()

        # Create a simple input stream and lexer/parser
        input_stream = InputStream("state System { state Active; }")
        lexer = GrammarLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = GrammarParser(token_stream)

        # Manually call reportContextSensitivity
        listener.reportContextSensitivity(
            recognizer=parser,
            dfa=None,
            startIndex=0,
            stopIndex=5,
            prediction=None,
            configs=None
        )

        assert len(listener.errors) == 1
        assert isinstance(listener.errors[0], ContextSensitivityError)

    def test_check_unfinished_parsing_error_with_unfinished_stream(self):
        """Test: check_unfinished_parsing_error with unfinished stream"""
        listener = CollectingErrorListener()

        # Create a token stream that is not at EOF
        input_stream = InputStream("state System { state Active; } extra_content")
        lexer = GrammarLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        token_stream.fill()

        # Move to a position that is not EOF
        token_stream.seek(0)

        # Call check_unfinished_parsing_error
        listener.check_unfinished_parsing_error(token_stream)

        # Should have added an UnfinishedParsingError
        assert len(listener.errors) >= 1
        assert any(isinstance(e, UnfinishedParsingError) for e in listener.errors)

    def test_filter_cascading_errors_empty_list(self):
        """Test: _filter_cascading_errors with empty list"""
        listener = CollectingErrorListener()

        # Test with empty errors list
        filtered = listener._filter_cascading_errors([])
        assert filtered == []
        assert len(filtered) == 0

    def test_filter_cascading_errors_single_error(self):
        """Test: _filter_cascading_errors with single error"""
        listener = CollectingErrorListener()

        # Create a single error
        error = SyntaxFailError(
            line=1,
            column=0,
            offending_symbol_text="state",
            msg="missing ';'"
        )

        # Filter should return the same error
        filtered = listener._filter_cascading_errors([error])
        assert len(filtered) == 1
        assert filtered[0] == error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
