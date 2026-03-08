#!/usr/bin/env python3
"""
Comprehensive validation script for FCSTM syntax-highlighting assets.

This script validates FCSTM highlighting behavior across both the Pygments
lexer and the TextMate grammar used by the VSCode extension. It keeps the
validation output separated by implementation so it is easy to see which side
passed or failed, while still using a shared set of lexical checkpoints to
ensure both implementations stay aligned.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path to import pyfcstm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pygments.token import Token

from pyfcstm.highlight.pygments_lexer import FcstmLexer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTMATE_GRAMMAR_FILE = os.path.join(ROOT_DIR, 'editors', 'fcstm.tmLanguage.json')
VSCODE_TEXTMATE_GRAMMAR_FILE = os.path.join(ROOT_DIR, 'editors', 'vscode', 'syntaxes', 'fcstm.tmLanguage.json')

COMPREHENSIVE_TEST_CODE = """
// ============================================================================
// FCSTM DSL Comprehensive Test - Covers All Grammar Rules
// ============================================================================

// Variable definitions (def_assignment)
def int counter = 0;                    // Integer with decimal literal
def int flags = 0xFF;                   // Integer with hex literal
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


@dataclass
class ValidationCheckpoint:
    """Represents a validation checkpoint."""

    name: str
    description: str
    passed: bool = False
    failures: List[str] = field(default_factory=list)


@dataclass
class SharedExpectation:
    """Shared lexical expectation for both validators."""

    text: str
    pygments_token: Any
    textmate_section: str
    textmate_scope: str
    capture_group: Optional[int] = None
    mode: str = 'auto'


SHARED_CHECKPOINT_SPECS: List[Dict[str, Any]] = [
    {
        'name': 'Keywords - Structure',
        'description': 'state, pseudo, named, def, event keywords',
        'items': [
            SharedExpectation('state', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('pseudo', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('named', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('def', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('event', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Lifecycle',
        'description': 'enter, during, exit, before, after keywords',
        'items': [
            SharedExpectation('enter', Token.Keyword.Reserved, 'keywords', 'keyword.other.lifecycle.fcstm'),
            SharedExpectation('during', Token.Keyword.Reserved, 'keywords', 'keyword.other.lifecycle.fcstm'),
            SharedExpectation('exit', Token.Keyword.Reserved, 'keywords', 'keyword.other.lifecycle.fcstm'),
            SharedExpectation('before', Token.Keyword.Reserved, 'keywords', 'keyword.other.lifecycle.fcstm'),
            SharedExpectation('after', Token.Keyword.Reserved, 'keywords', 'keyword.other.lifecycle.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Modifiers',
        'description': 'abstract, ref, effect keywords',
        'items': [
            SharedExpectation('abstract', Token.Keyword.Namespace, 'keywords', 'keyword.other.modifier.fcstm'),
            SharedExpectation('ref', Token.Keyword.Namespace, 'keywords', 'keyword.other.modifier.fcstm'),
            SharedExpectation('effect', Token.Keyword.Namespace, 'keywords', 'keyword.other.modifier.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Types',
        'description': 'int, float type keywords',
        'items': [
            SharedExpectation('int', Token.Keyword.Type, 'keywords', 'storage.type.fcstm'),
            SharedExpectation('float', Token.Keyword.Type, 'keywords', 'storage.type.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Control',
        'description': 'if keyword',
        'items': [
            SharedExpectation('if', Token.Keyword.Reserved, 'keywords', 'keyword.control.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Logical (word form)',
        'description': 'and, or, not keywords',
        'items': [
            SharedExpectation('and', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('or', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('not', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
        ],
    },
    {
        'name': 'Operators - Transition and Scope',
        'description': '->, >>, ::, :, /, ! operators',
        'items': [
            SharedExpectation('->', Token.Operator, 'operators', 'keyword.operator.transition.fcstm'),
            SharedExpectation('>>', Token.Operator.Word, 'operators', 'keyword.operator.aspect.fcstm'),
            SharedExpectation('::', Token.Operator, 'operators', 'keyword.operator.scope.fcstm'),
            SharedExpectation(':', Token.Punctuation, 'operators', 'punctuation.separator.transition.fcstm'),
            SharedExpectation('/', Token.Operator, 'operators', 'keyword.operator.path.fcstm'),
            SharedExpectation('!', Token.Operator.Word, 'operators', 'keyword.operator.forced.fcstm'),
        ],
    },
    {
        'name': 'Operators - Arithmetic',
        'description': '+, -, *, /, %, ** operators',
        'items': [
            SharedExpectation('+', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('-', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('*', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('/', Token.Operator, 'operators', 'keyword.operator.path.fcstm'),
            SharedExpectation('%', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('**', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
        ],
    },
    {
        'name': 'Operators - Bitwise',
        'description': '&, |, ^, ~, << operators',
        'items': [
            SharedExpectation('&', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('|', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('^', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('~', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('<<', Token.Operator, 'operators', 'keyword.operator.bitshift.fcstm'),
        ],
    },
    {
        'name': 'Operators - Comparison',
        'description': '<, >, <=, >=, ==, != operators',
        'items': [
            SharedExpectation('<', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('>', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm'),
            SharedExpectation('<=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm'),
            SharedExpectation('>=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm'),
            SharedExpectation('==', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm'),
            SharedExpectation('!=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm'),
        ],
    },
    {
        'name': 'Operators - Logical (symbol form)',
        'description': '&&, || operators',
        'items': [
            SharedExpectation('&&', Token.Operator, 'operators', 'keyword.operator.logical.fcstm'),
            SharedExpectation('||', Token.Operator, 'operators', 'keyword.operator.logical.fcstm'),
        ],
    },
    {
        'name': 'Literals - Numbers',
        'description': 'integer, hex, float literals',
        'items': [
            SharedExpectation('0', Token.Number.Integer, 'numbers', 'constant.numeric.integer.fcstm'),
            SharedExpectation('10', Token.Number.Integer, 'numbers', 'constant.numeric.integer.fcstm'),
            SharedExpectation('0xFF', Token.Number.Hex, 'numbers', 'constant.numeric.hex.fcstm'),
            SharedExpectation('0x0F', Token.Number.Hex, 'numbers', 'constant.numeric.hex.fcstm'),
            SharedExpectation('25.5', Token.Number.Float, 'numbers', 'constant.numeric.float.fcstm'),
            SharedExpectation('3.14e-5', Token.Number.Float, 'numbers', 'constant.numeric.float.fcstm'),
        ],
    },
    {
        'name': 'Literals - Booleans',
        'description': 'True, true, false literals',
        'items': [
            SharedExpectation('True', Token.Keyword.Constant, 'constants', 'constant.language.boolean.fcstm'),
            SharedExpectation('true', Token.Keyword.Constant, 'constants', 'constant.language.boolean.fcstm'),
            SharedExpectation('false', Token.Keyword.Constant, 'constants', 'constant.language.boolean.fcstm'),
        ],
    },
    {
        'name': 'Math Constants',
        'description': 'pi, E, tau constants',
        'items': [
            SharedExpectation('pi', Token.Name.Constant, 'constants', 'constant.language.math.fcstm'),
            SharedExpectation('E', Token.Name.Constant, 'constants', 'constant.language.math.fcstm'),
            SharedExpectation('tau', Token.Name.Constant, 'constants', 'constant.language.math.fcstm'),
        ],
    },
    {
        'name': 'Built-in Functions - Trigonometric',
        'description': 'sin, cos, tan, asin, acos, atan',
        'items': [
            SharedExpectation('sin', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('cos', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('tan', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('asin', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('acos', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('atan', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
        ],
    },
    {
        'name': 'Built-in Functions - Hyperbolic',
        'description': 'sinh, cosh, tanh, asinh, acosh, atanh',
        'items': [
            SharedExpectation('sinh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('cosh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('tanh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('asinh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('acosh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('atanh', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
        ],
    },
    {
        'name': 'Built-in Functions - Math',
        'description': 'sqrt, cbrt, exp, log, log10, log2, log1p',
        'items': [
            SharedExpectation('sqrt', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('cbrt', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('exp', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('log', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('log10', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('log2', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('log1p', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
        ],
    },
    {
        'name': 'Built-in Functions - Rounding',
        'description': 'abs, ceil, floor, round, trunc, sign',
        'items': [
            SharedExpectation('abs', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('ceil', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('floor', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('round', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('trunc', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
            SharedExpectation('sign', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm'),
        ],
    },
    {
        'name': 'Special Symbols',
        'description': '[*] pseudo-state marker',
        'items': [
            SharedExpectation('[*]', Token.Keyword.Pseudo, 'operators', 'constant.language.pseudo-state.fcstm'),
        ],
    },
    {
        'name': 'Comments',
        'description': 'single-line, hash, and block comments',
        'items': [
            SharedExpectation('// Single-line comment with //', Token.Comment.Single, 'comments', 'comment.line.double-slash.fcstm'),
            SharedExpectation('# Python-style comment with #', Token.Comment.Single, 'comments', 'comment.line.number-sign.fcstm'),
            SharedExpectation('/*', Token.Comment.Multiline, 'comments', 'comment.block.fcstm', mode='begin'),
            SharedExpectation('*/', Token.Comment.Multiline, 'comments', 'comment.block.fcstm', mode='end'),
        ],
    },
    {
        'name': 'Strings',
        'description': 'double-quoted strings',
        'items': [
            SharedExpectation('"System State Machine"', Token.String.Double, 'strings', 'string.quoted.double.fcstm'),
            SharedExpectation('"Stop Event"', Token.String.Double, 'strings', 'string.quoted.double.fcstm'),
        ],
    },
]

TEXTMATE_STRUCTURE_SPECS: List[Dict[str, Any]] = [
    {
        'name': 'Grammar Sync',
        'description': 'canonical and VSCode-packaged grammars are identical',
    },
    {
        'name': 'Top-Level Includes',
        'description': 'expected repository includes are present in pattern order',
    },
    {
        'name': 'Repository Sections',
        'description': 'expected repository sections are present',
    },
    {
        'name': 'Operator Order',
        'description': 'multi-character and special operators stay in safe matching order',
    },
    {
        'name': 'Declaration Captures',
        'description': 'declaration patterns provide specific scopes for declared names',
    },
    {
        'name': 'Unsupported Binary Literals',
        'description': 'binary integer highlighting is not introduced without grammar support',
    },
]


def _load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def _token_map(tokens: List[Tuple[Any, str]]) -> Dict[str, List[Any]]:
    mapping: Dict[str, List[Any]] = {}
    for token_type, token_text in tokens:
        if token_text.strip():
            mapping.setdefault(token_text, []).append(token_type)
    return mapping


def _find_textmate_match(
    grammar: Dict[str, Any],
    expectation: SharedExpectation,
) -> Tuple[bool, str]:
    repository = grammar.get('repository', {})
    patterns = repository.get(expectation.textmate_section, {}).get('patterns', [])
    candidate_details = []

    for pattern in patterns:
        scope_name = pattern.get('name')
        regex = pattern.get('match')
        begin = pattern.get('begin')
        end = pattern.get('end')

        if expectation.capture_group is not None:
            if not regex:
                continue
            match = _compile_pattern(regex).search(expectation.text)
            if not match:
                continue

            captures = pattern.get('captures', {})
            actual_scope = captures.get(str(expectation.capture_group), {}).get('name')
            if actual_scope == expectation.textmate_scope:
                return True, ''

            candidate_details.append(
                f"pattern {regex!r} matched, but capture {expectation.capture_group} scope was {actual_scope!r}"
            )
            continue

        if regex:
            if _compile_pattern(regex).search(expectation.text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"pattern {regex!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end and expectation.mode == 'begin':
            if _compile_pattern(begin).search(expectation.text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"begin pattern {begin!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end and expectation.mode == 'end':
            if _compile_pattern(end).search(expectation.text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"end pattern {end!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end:
            begin_match = _compile_pattern(begin).search(expectation.text)
            end_match = _compile_pattern(end).search(expectation.text)
            if begin_match and end_match and begin_match.start() <= end_match.start():
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"span pattern begin={begin!r}, end={end!r} matched, but scope was {scope_name!r}"
                )

    if candidate_details:
        return False, '; '.join(candidate_details)

    return False, (
        f"no pattern in repository section {expectation.textmate_section!r} matched {expectation.text!r} "
        f"with expected scope {expectation.textmate_scope!r}"
    )


def _validate_pygments_shared(code: str) -> Tuple[List[ValidationCheckpoint], int, float]:
    lexer = FcstmLexer()
    tokens = list(lexer.get_tokens(code))
    token_map = _token_map(tokens)
    detection_score = FcstmLexer.analyse_text(code)

    checkpoints: List[ValidationCheckpoint] = []

    tokenization_checkpoint = ValidationCheckpoint(
        name='Tokenization',
        description='the lexer emits tokens for the shared FCSTM test corpus',
    )
    if tokens:
        tokenization_checkpoint.passed = True
    else:
        tokenization_checkpoint.failures.append('lexer returned zero tokens for the shared test corpus')
    checkpoints.append(tokenization_checkpoint)

    detection_checkpoint = ValidationCheckpoint(
        name='Language Detection',
        description='analyse_text reports a confident FCSTM detection score',
    )
    if detection_score >= 0.5:
        detection_checkpoint.passed = True
    else:
        detection_checkpoint.failures.append(
            f'detection score {detection_score:.2f} is below the required threshold 0.50'
        )
    checkpoints.append(detection_checkpoint)

    for spec in SHARED_CHECKPOINT_SPECS:
        checkpoint = ValidationCheckpoint(name=spec['name'], description=spec['description'])

        for item in spec['items']:
            actual_types = token_map.get(item.text)
            if actual_types is None:
                checkpoint.failures.append(f"token {item.text!r} was not found in the token stream")
                continue
            if item.pygments_token not in actual_types:
                actual_text = ', '.join(str(token_type) for token_type in actual_types)
                checkpoint.failures.append(
                    f"token {item.text!r} expected {item.pygments_token}, got {actual_text}"
                )

        checkpoint.passed = not checkpoint.failures
        checkpoints.append(checkpoint)

    return checkpoints, len(tokens), detection_score


def _validate_textmate_shared(grammar: Dict[str, Any]) -> List[ValidationCheckpoint]:
    checkpoints: List[ValidationCheckpoint] = []

    for spec in SHARED_CHECKPOINT_SPECS:
        checkpoint = ValidationCheckpoint(name=spec['name'], description=spec['description'])

        for item in spec['items']:
            matched, failure_detail = _find_textmate_match(grammar, item)
            if not matched:
                checkpoint.failures.append(failure_detail)

        checkpoint.passed = not checkpoint.failures
        checkpoints.append(checkpoint)

    return checkpoints


def _validate_textmate_structure(grammar: Dict[str, Any], vscode_copy: Dict[str, Any]) -> List[ValidationCheckpoint]:
    checkpoints: List[ValidationCheckpoint] = []

    sync_checkpoint = ValidationCheckpoint(
        name='Grammar Sync',
        description='canonical and VSCode-packaged grammars are identical',
    )
    if grammar == vscode_copy:
        sync_checkpoint.passed = True
    else:
        sync_checkpoint.failures.append('canonical TextMate grammar and VSCode-packaged grammar differ')
    checkpoints.append(sync_checkpoint)

    includes_checkpoint = ValidationCheckpoint(
        name='Top-Level Includes',
        description='expected repository includes are present in pattern order',
    )
    expected_includes = [
        '#comments',
        '#declarations',
        '#keywords',
        '#operators',
        '#constants',
        '#strings',
        '#numbers',
        '#identifiers',
    ]
    actual_includes = [item.get('include') for item in grammar.get('patterns', [])]
    if actual_includes == expected_includes:
        includes_checkpoint.passed = True
    else:
        includes_checkpoint.failures.append(
            f'expected includes {expected_includes!r}, got {actual_includes!r}'
        )
    checkpoints.append(includes_checkpoint)

    sections_checkpoint = ValidationCheckpoint(
        name='Repository Sections',
        description='expected repository sections are present',
    )
    expected_sections = ['comments', 'declarations', 'keywords', 'operators', 'constants', 'strings', 'numbers', 'identifiers']
    repository = grammar.get('repository', {})
    for section in expected_sections:
        if section not in repository:
            sections_checkpoint.failures.append(f'missing repository section {section!r}')
    sections_checkpoint.passed = not sections_checkpoint.failures
    checkpoints.append(sections_checkpoint)

    operator_checkpoint = ValidationCheckpoint(
        name='Operator Order',
        description='multi-character and special operators stay in safe matching order',
    )
    expected_operator_order = [
        '>>',
        '->',
        '\\[\\*\\]',
        '::',
        ':',
        '/',
        '\\*\\*',
        '<<',
        '<=|>=|==|!=',
        '&&|\\|\\|',
        '!',
        '[+\\-*%&|^~<>]',
        '=|\\?',
    ]
    operator_patterns = repository.get('operators', {}).get('patterns', [])
    actual_operator_order = [item.get('match') for item in operator_patterns]
    if actual_operator_order == expected_operator_order:
        operator_checkpoint.passed = True
    else:
        operator_checkpoint.failures.append(
            f'expected operator order {expected_operator_order!r}, got {actual_operator_order!r}'
        )
    checkpoints.append(operator_checkpoint)

    declaration_checkpoint = ValidationCheckpoint(
        name='Declaration Captures',
        description='declaration patterns provide specific scopes for declared names',
    )
    declaration_expectations = [
        ('def int counter', 3, 'variable.other.definition.fcstm'),
        ('pseudo state SpecialState', 3, 'entity.name.type.state.fcstm'),
        ('state Running', 2, 'entity.name.type.state.fcstm'),
        ('event StartEvent', 2, 'entity.name.event.fcstm'),
    ]
    declaration_patterns = repository.get('declarations', {}).get('patterns', [])
    for sample_text, capture_group, expected_scope in declaration_expectations:
        matched = False
        for pattern in declaration_patterns:
            regex = pattern.get('match')
            if not regex:
                continue
            match = _compile_pattern(regex).search(sample_text)
            if not match:
                continue
            captures = pattern.get('captures', {})
            actual_scope = captures.get(str(capture_group), {}).get('name')
            if actual_scope == expected_scope:
                matched = True
                break
        if not matched:
            declaration_checkpoint.failures.append(
                f"sample {sample_text!r} did not produce capture {capture_group} with scope {expected_scope!r}"
            )
    declaration_checkpoint.passed = not declaration_checkpoint.failures
    checkpoints.append(declaration_checkpoint)

    binary_checkpoint = ValidationCheckpoint(
        name='Unsupported Binary Literals',
        description='binary integer highlighting is not introduced without grammar support',
    )
    number_patterns = repository.get('numbers', {}).get('patterns', [])
    number_matches = [item.get('match') for item in number_patterns]
    if any('0b' in (item or '') for item in number_matches):
        binary_checkpoint.failures.append('found binary literal highlighting in TextMate number patterns')
    else:
        binary_checkpoint.passed = True
    checkpoints.append(binary_checkpoint)

    return checkpoints


def _print_section(title: str, checkpoints: List[ValidationCheckpoint]) -> None:
    print(f'\n🧪 {title}')
    for checkpoint in checkpoints:
        if checkpoint.passed:
            print(f'✅ {checkpoint.name}')
        else:
            print(f'❌ {checkpoint.name}')
            print(f'   {checkpoint.description}')
            for failure in checkpoint.failures:
                print(f'   - {failure}')


def _count_passed(checkpoints: List[ValidationCheckpoint]) -> int:
    return sum(1 for checkpoint in checkpoints if checkpoint.passed)


def main() -> int:
    print('======================================================================')
    print('FCSTM SYNTAX-HIGHLIGHTING VALIDATION')
    print('======================================================================')

    pygments_checkpoints, token_count, detection_score = _validate_pygments_shared(COMPREHENSIVE_TEST_CODE)

    canonical_grammar = _load_json(TEXTMATE_GRAMMAR_FILE)
    vscode_grammar = _load_json(VSCODE_TEXTMATE_GRAMMAR_FILE)
    textmate_shared_checkpoints = _validate_textmate_shared(canonical_grammar)
    textmate_structure_checkpoints = _validate_textmate_structure(canonical_grammar, vscode_grammar)
    textmate_checkpoints = textmate_shared_checkpoints + textmate_structure_checkpoints

    _print_section('Pygments Validation', pygments_checkpoints)
    print(
        f'ℹ️ Pygments summary: {_count_passed(pygments_checkpoints)}/{len(pygments_checkpoints)} passed, '
        f'tokens={token_count}, detection={detection_score:.2f}'
    )

    _print_section('TextMate Validation', textmate_checkpoints)
    print(
        f'ℹ️ TextMate summary: {_count_passed(textmate_checkpoints)}/{len(textmate_checkpoints)} passed'
    )

    all_checkpoints = pygments_checkpoints + textmate_checkpoints
    all_passed = all(checkpoint.passed for checkpoint in all_checkpoints)

    print('\n======================================================================')
    print('SUMMARY')
    print('======================================================================')
    print(
        f'Pygments: {_count_passed(pygments_checkpoints)}/{len(pygments_checkpoints)} passed | '
        f'TextMate: {_count_passed(textmate_checkpoints)}/{len(textmate_checkpoints)} passed'
    )

    if all_passed:
        print('✅ ALL VALIDATIONS PASSED')
        return 0

    print('❌ VALIDATION FAILURES DETECTED')
    return 1


if __name__ == '__main__':
    sys.exit(main())
