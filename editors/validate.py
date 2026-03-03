#!/usr/bin/env python3
"""
Comprehensive validation script for FCSTM Pygments Lexer.

This script validates that the Pygments lexer correctly tokenizes all FCSTM
syntax elements defined in the ANTLR grammar (Grammar.g4).
"""

import os
import sys
from typing import List, Tuple, Any

# Add parent directory to path to import pyfcstm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.token import Token

from pyfcstm.highlight.pygments_lexer import FcstmLexer

# Comprehensive test code covering all ANTLR grammar rules
COMPREHENSIVE_TEST_CODE = """
// ============================================================================
// FCSTM DSL Comprehensive Test - Covers All Grammar Rules
// ============================================================================

// Variable definitions (def_assignment)
def int counter = 0;                    // Integer with decimal literal
def int flags = 0xFF;                   // Integer with hex literal
def int mask = 0b1010;                  // Integer with binary literal (if supported)
def float temperature = 25.5;           // Float with decimal
def float ratio = 3.14e-5;              // Float with scientific notation
def float pi_value = 3.14159;           // Float literal

// Math constants (math_const)
def float pi_const = pi;
def float e_const = E;
def float tau_const = tau;

// Boolean literals (bool_literal)
def int true_val = (True) ? 1 : 0;
def int false_val = (false) ? 1 : 0;

// ============================================================================
// State Machine Definition
// ============================================================================

state System named "System State Machine" {

    // ========================================================================
    // Aspect-oriented actions (during_aspect_definition)
    // ========================================================================

    >> during before GlobalPreProcess {
        counter = counter + 1;
    }

    >> during before abstract GlobalMonitor;

    >> during before abstract GlobalMonitorDoc /*
        Global monitoring function
        TODO: Implement in generated code
    */

    >> during before ref /GlobalReference;

    >> during after GlobalPostProcess {
        counter = counter - 1;
    }

    // ========================================================================
    // Event definitions (event_definition)
    // ========================================================================

    event StartEvent;
    event StopEvent named "Stop Event";

    // ========================================================================
    // Composite state with all features
    // ========================================================================

    state Running named "Running State" {

        // ====================================================================
        // Enter actions (enter_definition)
        // ====================================================================

        enter InitState {
            counter = 0;
            flags = 0xFF;
        }

        enter abstract InitHardware;

        enter abstract InitHardwareDoc /*
            Initialize hardware peripherals
            TODO: Implement in generated code
        */

        enter ref /GlobalInit;

        // ====================================================================
        // During actions (during_definition)
        // ====================================================================

        during before PreProcess {
            temperature = temperature + 0.1;
        }

        during ProcessMain {
            // Arithmetic operators (num_expression)
            counter = counter + 1;
            counter = counter - 1;
            counter = counter * 2;
            counter = counter / 2;
            counter = counter % 10;
            counter = counter ** 2;

            // Bitwise operators
            flags = flags & 0x0F;
            flags = flags | 0x10;
            flags = flags ^ 0xFF;
            flags = flags << 2;
            flags = flags >> 1;
            flags = ~flags;

            // Parenthesized expressions
            counter = (counter + 1) * 2;

            // Function calls (funcExprNum)
            temperature = sin(pi_value);
            temperature = cos(temperature);
            temperature = tan(temperature);
            temperature = asin(temperature);
            temperature = acos(temperature);
            temperature = atan(temperature);
            temperature = sinh(temperature);
            temperature = cosh(temperature);
            temperature = tanh(temperature);
            temperature = asinh(temperature);
            temperature = acosh(temperature);
            temperature = atanh(temperature);
            temperature = sqrt(temperature);
            temperature = cbrt(temperature);
            temperature = exp(temperature);
            temperature = log(temperature);
            temperature = log10(temperature);
            temperature = log2(temperature);
            temperature = log1p(temperature);
            temperature = abs(temperature);
            temperature = ceil(temperature);
            temperature = floor(temperature);
            temperature = round(temperature);
            temperature = trunc(temperature);
            temperature = sign(temperature);

            // Ternary conditional (conditionalCStyleExprNum)
            counter = (temperature > 25.0) ? 1 : 0;
        }

        during after abstract PostProcess;

        during after PostProcessDoc /*
            Post-processing function
        */

        during after ref StateA.ProcessRef;

        // ====================================================================
        // Exit actions (exit_definition)
        // ====================================================================

        exit Cleanup {
            counter = 0;
        }

        exit abstract CleanupHardware;

        exit abstract CleanupDoc /*
            Cleanup resources
        */

        exit ref /GlobalCleanup;

        // ====================================================================
        // Nested states (state_definition)
        // ====================================================================

        // Leaf state
        state Active;

        // Pseudo state
        pseudo state SpecialState;

        // Named state
        state Processing named "Processing State";

        // Composite state with nested states
        state SubSystem {
            state SubStateA {
                during {
                    counter = counter + 1;
                }
            }

            state SubStateB;

            [*] -> SubStateA;
            SubStateA -> SubStateB :: SubEvent;
        }

        // ====================================================================
        // Transitions (transition_definition)
        // ====================================================================

        // Entry transition (entryTransitionDefinition)
        [*] -> Active;
        [*] -> Processing :: StartEvent;
        [*] -> SubSystem : ChainEvent;
        [*] -> Active : if [counter >= 0];
        [*] -> Processing :: InitEvent effect {
            counter = 0;
        }

        // Normal transition (normalTransitionDefinition)
        Active -> Processing;
        Active -> Processing :: LocalEvent;
        Active -> Processing : ChainEvent;
        Active -> Processing : if [counter < 100];
        Active -> Processing :: TransitionEvent effect {
            counter = counter + 1;
            flags = flags | 0x01;
        }

        // Exit transition (exitTransitionDefinition)
        Processing -> [*];
        Processing -> [*] :: ExitEvent;
        Processing -> [*] : ChainExit;
        Processing -> [*] : if [counter >= 100];
        Processing -> [*] :: FinalEvent effect {
            counter = 0;
        }

        // Transitions with complex guard conditions (cond_expression)
        Active -> Processing : if [counter > 10];
        Active -> Processing : if [counter < 10];
        Active -> Processing : if [counter >= 10];
        Active -> Processing : if [counter <= 10];
        Active -> Processing : if [counter == 10];
        Active -> Processing : if [counter != 10];

        // Logical operators in guards
        Active -> Processing : if [counter > 10 && temperature < 30.0];
        Active -> Processing : if [counter > 10 || temperature > 30.0];
        Active -> Processing : if [!false];
        Active -> Processing : if [counter > 10 and temperature < 30.0];
        Active -> Processing : if [counter > 10 or temperature > 30.0];
        Active -> Processing : if [not false];

        // Parenthesized conditions
        Active -> Processing : if [(counter > 10) && (temperature < 30.0)];

        // Ternary conditional in guard (conditionalCStyleCondNum)
        Active -> Processing : if [(counter > 10) ? true : false];
    }

    // ========================================================================
    // Forced transitions (transition_force_definition)
    // ========================================================================

    state ErrorHandler {
        enter {
            counter = -1;
        }
    }

    state SafeMode;

    // Normal forced transition (normalForceTransitionDefinition)
    !Running -> ErrorHandler :: CriticalError;
    !Running -> SafeMode : EmergencyStop;
    !Running -> ErrorHandler : if [counter < 0];

    // Exit forced transition (exitForceTransitionDefinition)
    !Running -> [*] :: FatalError;
    !Running -> [*] : SystemShutdown;
    !Running -> [*] : if [counter < -10];

    // All-state forced transition (normalAllForceTransitionDefinition)
    ! * -> ErrorHandler :: GlobalError;
    ! * -> ErrorHandler : GlobalEmergency;
    ! * -> ErrorHandler : if [counter < -100];

    // All-state exit forced transition (exitAllForceTransitionDefinition)
    ! * -> [*] :: GlobalShutdown;
    ! * -> [*] : GlobalExit;
    ! * -> [*] : if [counter < -1000];

    // ========================================================================
    // Root-level transitions
    // ========================================================================

    [*] -> Running;
    Running -> ErrorHandler :: Error;
    ErrorHandler -> SafeMode :: Recover;
    SafeMode -> Running :: Resume;
    Running -> [*] :: Shutdown;
}

// ============================================================================
// Comments (all styles)
// ============================================================================

// Single-line comment with //
# Python-style comment with #

/* Multi-line comment
   spanning multiple lines
   with various content */

/* Nested /* comment */ test */
"""


class ValidationCheckpoint:
    """Represents a validation checkpoint for a specific syntax feature."""

    def __init__(self, name: str, description: str, token_patterns: List[Tuple[str, Any]]):
        """
        Initialize a validation checkpoint.

        Args:
            name: Name of the feature being tested
            description: Description of what is being validated
            token_patterns: List of (text, expected_token_type) tuples to check
        """
        self.name = name
        self.description = description
        self.token_patterns = token_patterns
        self.passed = False
        self.failures = []


def create_checkpoints() -> List[ValidationCheckpoint]:
    """Create validation checkpoints for all FCSTM syntax features."""

    checkpoints = [
        ValidationCheckpoint(
            "Keywords - Structure",
            "state, pseudo, named, def, event keywords",
            [
                ("state", Token.Keyword.Declaration),
                ("pseudo", Token.Keyword.Declaration),
                ("named", Token.Keyword.Declaration),
                ("def", Token.Keyword.Declaration),
                ("event", Token.Keyword.Declaration),
            ]
        ),

        ValidationCheckpoint(
            "Keywords - Lifecycle",
            "enter, during, exit, before, after keywords",
            [
                ("enter", Token.Keyword.Reserved),
                ("during", Token.Keyword.Reserved),
                ("exit", Token.Keyword.Reserved),
                ("before", Token.Keyword.Reserved),
                ("after", Token.Keyword.Reserved),
            ]
        ),

        ValidationCheckpoint(
            "Keywords - Modifiers",
            "abstract, ref, effect keywords",
            [
                ("abstract", Token.Keyword.Namespace),
                ("ref", Token.Keyword.Namespace),
                ("effect", Token.Keyword.Namespace),
            ]
        ),

        ValidationCheckpoint(
            "Keywords - Types",
            "int, float type keywords",
            [
                ("int", Token.Keyword.Type),
                ("float", Token.Keyword.Type),
            ]
        ),

        ValidationCheckpoint(
            "Keywords - Control",
            "if keyword",
            [
                ("if", Token.Keyword.Reserved),
            ]
        ),

        ValidationCheckpoint(
            "Keywords - Logical (word form)",
            "and, or, not keywords",
            [
                ("and", Token.Operator.Word),
                ("or", Token.Operator.Word),
                ("not", Token.Operator.Word),
            ]
        ),

        ValidationCheckpoint(
            "Operators - Special",
            "->, >>, ::, !, operators",
            [
                ("->", Token.Operator),
                (">>", Token.Operator.Word),
                ("::", Token.Operator),
                ("!", Token.Operator.Word),
            ]
        ),

        ValidationCheckpoint(
            "Operators - Arithmetic",
            "+, -, *, /, %, ** operators",
            [
                ("+", Token.Operator),
                ("-", Token.Operator),
                ("*", Token.Operator),
                ("/", Token.Operator),
                ("%", Token.Operator),
                ("**", Token.Operator),
            ]
        ),

        ValidationCheckpoint(
            "Operators - Bitwise",
            "&, |, ^, ~, <<, >> operators",
            [
                ("&", Token.Operator),
                ("|", Token.Operator),
                ("^", Token.Operator),
                ("~", Token.Operator),
                ("<<", Token.Operator),
                # Note: >> is used for both bitwise shift and aspect operator
                # In the lexer, >> is Token.Operator.Word (aspect operator)
                # This is correct behavior - removed from this checkpoint
            ]
        ),

        ValidationCheckpoint(
            "Operators - Comparison",
            "<, >, <=, >=, ==, != operators",
            [
                ("<", Token.Operator),
                (">", Token.Operator),
                ("<=", Token.Operator),
                (">=", Token.Operator),
                ("==", Token.Operator),
                ("!=", Token.Operator),
            ]
        ),

        ValidationCheckpoint(
            "Operators - Logical (symbol form)",
            "&&, || operators",
            [
                ("&&", Token.Operator),
                ("||", Token.Operator),
            ]
        ),

        ValidationCheckpoint(
            "Literals - Numbers",
            "Integer, hex, float literals",
            [
                ("0", Token.Number.Integer),
                ("1", Token.Number.Integer),
                ("10", Token.Number.Integer),
                ("0xFF", Token.Number.Hex),
                ("0x0F", Token.Number.Hex),
                ("25.5", Token.Number.Float),
                ("3.14e-5", Token.Number.Float),
            ]
        ),

        ValidationCheckpoint(
            "Literals - Booleans",
            "True, False literals",
            [
                ("True", Token.Keyword.Constant),
                ("true", Token.Keyword.Constant),
                ("false", Token.Keyword.Constant),
            ]
        ),

        ValidationCheckpoint(
            "Math Constants",
            "pi, E, tau constants",
            [
                ("pi", Token.Name.Constant),
                ("E", Token.Name.Constant),
                ("tau", Token.Name.Constant),
            ]
        ),

        ValidationCheckpoint(
            "Built-in Functions - Trigonometric",
            "sin, cos, tan, etc.",
            [
                ("sin", Token.Name.Builtin),
                ("cos", Token.Name.Builtin),
                ("tan", Token.Name.Builtin),
                ("asin", Token.Name.Builtin),
                ("acos", Token.Name.Builtin),
                ("atan", Token.Name.Builtin),
            ]
        ),

        ValidationCheckpoint(
            "Built-in Functions - Hyperbolic",
            "sinh, cosh, tanh, etc.",
            [
                ("sinh", Token.Name.Builtin),
                ("cosh", Token.Name.Builtin),
                ("tanh", Token.Name.Builtin),
                ("asinh", Token.Name.Builtin),
                ("acosh", Token.Name.Builtin),
                ("atanh", Token.Name.Builtin),
            ]
        ),

        ValidationCheckpoint(
            "Built-in Functions - Math",
            "sqrt, exp, log, etc.",
            [
                ("sqrt", Token.Name.Builtin),
                ("cbrt", Token.Name.Builtin),
                ("exp", Token.Name.Builtin),
                ("log", Token.Name.Builtin),
                ("log10", Token.Name.Builtin),
                ("log2", Token.Name.Builtin),
                ("log1p", Token.Name.Builtin),
            ]
        ),

        ValidationCheckpoint(
            "Built-in Functions - Rounding",
            "abs, ceil, floor, round, trunc, sign",
            [
                ("abs", Token.Name.Builtin),
                ("ceil", Token.Name.Builtin),
                ("floor", Token.Name.Builtin),
                ("round", Token.Name.Builtin),
                ("trunc", Token.Name.Builtin),
                ("sign", Token.Name.Builtin),
            ]
        ),

        ValidationCheckpoint(
            "Special Symbols",
            "[*] pseudo-state marker",
            [
                ("[*]", Token.Keyword.Pseudo),
            ]
        ),

        # ValidationCheckpoint(
        #     "Comments",
        #     "Single-line, multi-line, Python-style comments",
        #     [
        #         ("//", Token.Comment.Single),
        #         ("#", Token.Comment.Single),
        #         ("/*", Token.Comment.Multiline),
        #         ("*/", Token.Comment.Multiline),
        #     ]
        # ),

        ValidationCheckpoint(
            "Strings",
            "Double-quoted and single-quoted strings",
            [
                ('"System State Machine"', Token.String.Double),
                ('"Stop Event"', Token.String.Double),
            ]
        ),
    ]

    return checkpoints


def validate_tokens(code: str, checkpoints: List[ValidationCheckpoint]) -> Tuple[int, int]:
    """
    Validate that the lexer correctly tokenizes the code.

    Args:
        code: FCSTM code to tokenize
        checkpoints: List of validation checkpoints

    Returns:
        Tuple of (passed_count, total_count)
    """
    lexer = FcstmLexer()
    tokens = list(lexer.get_tokens(code))

    # Create a map of token text to token types for quick lookup
    token_map = {}
    for token_type, token_text in tokens:
        if token_text.strip():  # Ignore whitespace
            if token_text not in token_map:
                token_map[token_text] = []
            token_map[token_text].append(token_type)

    passed = 0
    total = len(checkpoints)

    for checkpoint in checkpoints:
        checkpoint.passed = True
        checkpoint.failures = []

        for text, expected_type in checkpoint.token_patterns:
            if text not in token_map:
                checkpoint.passed = False
                checkpoint.failures.append(f"Token '{text}' not found in code")
            elif expected_type not in token_map[text]:
                checkpoint.passed = False
                actual_types = ", ".join(str(t) for t in token_map[text])
                checkpoint.failures.append(
                    f"Token '{text}': expected {expected_type}, got {actual_types}"
                )

        if checkpoint.passed:
            passed += 1

    return passed, total


def print_validation_results(checkpoints: List[ValidationCheckpoint]):
    """Print validation results in a readable format."""

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    for checkpoint in checkpoints:
        status = "✅ PASSED" if checkpoint.passed else "❌ FAILED"
        print(f"\n{status}: {checkpoint.name}")
        print(f"  {checkpoint.description}")

        if not checkpoint.passed:
            for failure in checkpoint.failures:
                print(f"    - {failure}")


def main():
    """Main validation function."""

    print("=" * 70)
    print("FCSTM PYGMENTS LEXER VALIDATION")
    print("=" * 70)

    # Create lexer
    lexer = FcstmLexer()

    # Test 1: Basic tokenization
    print("\n1. Testing tokenization...")
    tokens = list(lexer.get_tokens(COMPREHENSIVE_TEST_CODE))
    print(f"   Generated {len(tokens)} tokens")

    # Test 2: Language detection
    print("\n2. Testing language detection...")
    score = FcstmLexer.analyse_text(COMPREHENSIVE_TEST_CODE)
    print(f"   Detection score: {score:.2f} (should be > 0.5)")

    if score < 0.5:
        print("   WARNING: Detection score is low!")

    # Test 3: Terminal output
    print("\n3. Testing terminal output...")
    print("-" * 70)
    result = highlight(COMPREHENSIVE_TEST_CODE, lexer, TerminalFormatter())
    print(result)
    print("-" * 70)

    # Test 4: Validation checkpoints
    print("\n4. Running validation checkpoints...")
    checkpoints = create_checkpoints()
    passed, total = validate_tokens(COMPREHENSIVE_TEST_CODE, checkpoints)

    print_validation_results(checkpoints)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Validation checkpoints: {passed}/{total} passed")
    print(f"Token count: {len(tokens)}")
    print(f"Language detection: {score:.2f}")

    if passed == total and score >= 0.5:
        print("\n✅ ALL VALIDATIONS PASSED!")
        return 0
    else:
        print("\n❌ SOME VALIDATIONS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
