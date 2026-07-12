#!/usr/bin/env python3
# fmt: off
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
from typing import Any, Dict, List, Optional, Pattern, Tuple

# Add parent directory to path to import pyfcstm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pygments.token import Token

from pyfcstm.highlight import FcstmBmcQueryLexer, FcstmLexer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTMATE_GRAMMAR_FILE = os.path.join(ROOT_DIR, 'editors', 'fcstm.tmLanguage.json')
VSCODE_TEXTMATE_GRAMMAR_FILE = os.path.join(ROOT_DIR, 'editors', 'vscode', 'syntaxes', 'fcstm.tmLanguage.json')
FBMCQ_TEXTMATE_GRAMMAR_FILE = os.path.join(ROOT_DIR, 'editors', 'fcstm-bmc-query.tmLanguage.json')
VSCODE_FBMCQ_TEXTMATE_GRAMMAR_FILE = os.path.join(
    ROOT_DIR, 'editors', 'vscode', 'syntaxes', 'fcstm-bmc-query.tmLanguage.json'
)
VSCODE_PACKAGE_FILE = os.path.join(ROOT_DIR, 'editors', 'vscode', 'package.json')


FBMCQ_TEST_CODE = """
// FCSTM BMC Query syntax-highlighting fixture.
init state("Root.System.A") where x >= 0 and active("Root.System.A");

assume always: terminated(current) or var("x") <= 1000 and cycle >= 0 or not called("Hook", current);
assume at 0: sin(pi) + 0xFF + 3.5e-1 + .5 + 1. + (flags ** 2) + (flags >> 1) + (flags * 2 / 3 % 4) + (flags | 1) + (flags ^ 2) == var("x");
assume event("Root.System.A.Tick", 0..3) != false;
assume events cardinality at_most_one {
    "Root.System.A.Tick",
    "Root.System.A.Reset"
};
assume events cardinality any {
    "Root.System.A.Tick",
    "Root.System.A.Reset"
};

check reach <= 2: active("Root.Done");
check forbid <= 2: terminated(current);
check invariant <= 2: var("x") >= 0;
check must_reach <= 4: active("Root.Recovering");
check exists_always <= 4: active("Root.Safe");
check response <= 10:
    trigger event("Root.System.A.Tick", current) && active("Root.System.A")
    -> within 3 active("Root.Recovering") iff true xor !false implies true;

check cover <= 6:
    ((~flags & 0xFF) == 0) || (cycle << 1) >= +2 && (-x <= 3.5e-1) => case("Root.System.A::transition::Root.System.B::1");

# hash comment
/* block comment */
assume always: 'Root.System.A' == 'Root.System.A';
"""

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

            // Operation-block control flow
            if [counter > 0] {
                mode = 1;
            } else {
                mode = 0;
            }
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
        Active -> Processing : if [counter > 10 => temperature < 30.0];
        Active -> Processing : if [counter > 10 implies temperature < 30.0];
        Active -> Processing : if [counter > 10 xor temperature < 30.0];
        Active -> Processing : if [counter > 10 iff temperature < 30.0];
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
    // Import statements (import_statement)
    // ========================================================================

    state ImportHost named "Import Host" {
        state Bus;

        // Simple import without block
        import "./modules/simple.fcstm" as Simple;

        // Import with block and every mapping form the grammar accepts
        import "./modules/worker.fcstm" as Worker named "Worker Module" {
            def counter -> shared_counter;
            def {status_flag, a, b, c} -> set_*;
            def sensor_* -> sensor_$1;
            def a_*_b_* -> pair_${1}_${2}_${0};
            def * -> fallback_$0;
            event /Start -> Bus.Start named "Mapped Start";
            event /Alarm -> /Bus.Alarm;
        }

        [*] -> Bus;
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
    textmate_sample: Optional[str] = None


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
        'name': 'Keywords - Import',
        'description': 'import, as keywords used by import statements',
        'items': [
            SharedExpectation('import', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('as', Token.Keyword.Declaration, 'keywords', 'keyword.control.fcstm'),
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
        'description': 'if, else keywords',
        'items': [
            SharedExpectation('if', Token.Keyword.Reserved, 'keywords', 'keyword.control.fcstm'),
            SharedExpectation('else', Token.Keyword.Reserved, 'keywords', 'keyword.control.fcstm'),
        ],
    },
    {
        'name': 'Keywords - Logical (word form)',
        'description': 'and, or, not, implies, xor, iff keywords',
        'items': [
            SharedExpectation('and', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('or', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('not', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('implies', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('xor', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
            SharedExpectation('iff', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm'),
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
        'description': '&&, ||, => operators',
        'items': [
            SharedExpectation('&&', Token.Operator, 'operators', 'keyword.operator.logical.fcstm'),
            SharedExpectation('||', Token.Operator, 'operators', 'keyword.operator.logical.fcstm'),
            SharedExpectation('=>', Token.Operator, 'operators', 'keyword.operator.logical.fcstm'),
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
    {
        'name': 'Import Block - Templates and Selectors',
        'description': 'wildcard selectors and target templates in import mappings',
        'items': [
            SharedExpectation('sensor_*', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
            SharedExpectation('a_*_b_*', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
            SharedExpectation('set_*', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
            SharedExpectation('sensor_$1', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
            SharedExpectation('fallback_$0', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
            SharedExpectation('pair_${1}_${2}_${0}', Token.Name.Variable, 'import-body', 'variable.parameter.fcstm'),
        ],
    },
]


FBMCQ_CHECKPOINT_SPECS: List[Dict[str, Any]] = [
    {
        'name': 'FBMCQ Query Clauses',
        'description': 'init, assume, check, and query clause keywords',
        'items': [
            SharedExpectation('init', Token.Keyword.Declaration, 'clauses', 'keyword.control.fcstm.bmc.query'),
            SharedExpectation('state', Token.Keyword.Declaration, 'clauses', 'keyword.control.fcstm.bmc.query'),
            SharedExpectation('where', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('assume', Token.Keyword.Declaration, 'clauses', 'keyword.control.fcstm.bmc.query'),
            SharedExpectation('always', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('at', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('events', Token.Keyword.Declaration, 'clauses', 'keyword.control.fcstm.bmc.query'),
            SharedExpectation('cardinality', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('any', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('check', Token.Keyword.Declaration, 'clauses', 'keyword.control.fcstm.bmc.query'),
            SharedExpectation('reach', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('forbid', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('invariant', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('must_reach', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('exists_always', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('response', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('cover', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('trigger', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('within', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
            SharedExpectation('current', Token.Keyword.Reserved, 'clauses', 'keyword.other.query-clause.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ BMC Atoms',
        'description': 'BMC atom names and helpers',
        'items': [
            SharedExpectation('var', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='var('),
            SharedExpectation('cycle', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query'),
            SharedExpectation('active', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='active('),
            SharedExpectation('terminated', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='terminated('),
            SharedExpectation('event', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='event('),
            SharedExpectation('case', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='case('),
            SharedExpectation('called', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query', textmate_sample='called('),
            SharedExpectation('at_most_one', Token.Name.Builtin, 'atoms', 'support.function.bmc-atom.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ Logical Operators',
        'description': 'symbol and word logical operators',
        'items': [
            SharedExpectation('and', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('or', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('not', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('implies', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('xor', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('iff', Token.Operator.Word, 'keywords', 'keyword.operator.word.fcstm.bmc.query'),
            SharedExpectation('&&', Token.Operator, 'operators', 'keyword.operator.logical.fcstm.bmc.query'),
            SharedExpectation('||', Token.Operator, 'operators', 'keyword.operator.logical.fcstm.bmc.query'),
            SharedExpectation('=>', Token.Operator, 'operators', 'keyword.operator.logical.fcstm.bmc.query'),
            SharedExpectation('!', Token.Operator.Word, 'operators', 'keyword.operator.logical.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ Response and Ranges',
        'description': 'response arrow and event range operators',
        'items': [
            SharedExpectation('->', Token.Operator, 'operators', 'keyword.operator.response.fcstm.bmc.query'),
            SharedExpectation('..', Token.Operator, 'operators', 'keyword.operator.range.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ Numeric Operators',
        'description': 'FCSTM-compatible arithmetic and bitwise operators',
        'items': [
            SharedExpectation('**', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('<<', Token.Operator, 'operators', 'keyword.operator.bitshift.fcstm.bmc.query'),
            SharedExpectation('>>', Token.Operator, 'operators', 'keyword.operator.bitshift.fcstm.bmc.query'),
            SharedExpectation('+', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('-', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('*', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('/', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('%', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('&', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('|', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('^', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('~', Token.Operator, 'operators', 'keyword.operator.arithmetic.fcstm.bmc.query'),
            SharedExpectation('<=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm.bmc.query'),
            SharedExpectation('>=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm.bmc.query'),
            SharedExpectation('==', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm.bmc.query'),
            SharedExpectation('!=', Token.Operator, 'operators', 'keyword.operator.comparison.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ Literals and Functions',
        'description': 'numbers, strings, booleans, math constants, and ufuncs',
        'items': [
            SharedExpectation('0', Token.Number.Integer, 'numbers', 'constant.numeric.integer.fcstm.bmc.query'),
            SharedExpectation('1000', Token.Number.Integer, 'numbers', 'constant.numeric.integer.fcstm.bmc.query'),
            SharedExpectation('0xFF', Token.Number.Hex, 'numbers', 'constant.numeric.hex.fcstm.bmc.query'),
            SharedExpectation('3.5e-1', Token.Number.Float, 'numbers', 'constant.numeric.float.fcstm.bmc.query'),
            SharedExpectation('.5', Token.Number.Float, 'numbers', 'constant.numeric.float.fcstm.bmc.query'),
            SharedExpectation('1.', Token.Number.Float, 'numbers', 'constant.numeric.float.fcstm.bmc.query'),
            SharedExpectation('true', Token.Keyword.Constant, 'constants', 'constant.language.boolean.fcstm.bmc.query'),
            SharedExpectation('false', Token.Keyword.Constant, 'constants', 'constant.language.boolean.fcstm.bmc.query'),
            SharedExpectation('pi', Token.Name.Constant, 'constants', 'constant.language.math.fcstm.bmc.query'),
            SharedExpectation('sin', Token.Name.Builtin, 'constants', 'support.function.builtin.fcstm.bmc.query'),
            SharedExpectation('"Root.System.A"', Token.String.Double, 'strings', 'string.quoted.double.fcstm.bmc.query'),
            SharedExpectation("'Root.System.A'", Token.String.Single, 'strings', 'string.quoted.single.fcstm.bmc.query'),
        ],
    },
    {
        'name': 'FBMCQ Comments',
        'description': 'single-line, hash, and block comments',
        'items': [
            SharedExpectation('// FCSTM BMC Query syntax-highlighting fixture.', Token.Comment.Single, 'comments', 'comment.line.double-slash.fcstm.bmc.query'),
            SharedExpectation('# hash comment', Token.Comment.Single, 'comments', 'comment.line.number-sign.fcstm.bmc.query'),
            SharedExpectation('/*', Token.Comment.Multiline, 'comments', 'comment.block.fcstm.bmc.query', mode='begin'),
            SharedExpectation('*/', Token.Comment.Multiline, 'comments', 'comment.block.fcstm.bmc.query', mode='end'),
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
    {
        'name': 'Import Block Captures',
        'description': 'block-form import declaration exposes alias and display-name scopes',
    },
]


def _load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _compile_pattern(pattern: str) -> Pattern[str]:
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
    sample_text = expectation.textmate_sample or expectation.text
    candidate_details = []

    for pattern in patterns:
        scope_name = pattern.get('name')
        regex = pattern.get('match')
        begin = pattern.get('begin')
        end = pattern.get('end')

        if expectation.capture_group is not None:
            if not regex:
                continue
            match = _compile_pattern(regex).search(sample_text)
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
            if _compile_pattern(regex).search(sample_text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"pattern {regex!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end and expectation.mode == 'begin':
            if _compile_pattern(begin).search(sample_text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"begin pattern {begin!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end and expectation.mode == 'end':
            if _compile_pattern(end).search(sample_text):
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"end pattern {end!r} matched, but scope was {scope_name!r}"
                )
            continue

        if begin and end:
            begin_match = _compile_pattern(begin).search(sample_text)
            end_match = _compile_pattern(end).search(sample_text)
            if begin_match and end_match and begin_match.start() <= end_match.start():
                if scope_name == expectation.textmate_scope:
                    return True, ''
                candidate_details.append(
                    f"span pattern begin={begin!r}, end={end!r} matched, but scope was {scope_name!r}"
                )

    if candidate_details:
        return False, '; '.join(candidate_details)

    return False, (
        f"no pattern in repository section {expectation.textmate_section!r} matched {sample_text!r} "
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
    expected_sections = [
        'comments', 'declarations', 'keywords', 'operators', 'constants',
        'strings', 'numbers', 'identifiers', 'import-body', 'import-selector-set',
    ]
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
        '=>',
        ',',
        '\\{|\\}',
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

    import_block_checkpoint = ValidationCheckpoint(
        name='Import Block Captures',
        description='block-form import declaration exposes alias and display-name scopes',
    )
    import_block_sample = 'import "./worker.fcstm" as Worker named "Worker Module" {'
    import_block_expectations = [
        (1, 'keyword.control.fcstm'),
        (3, 'keyword.control.fcstm'),
        (4, 'entity.name.type.state.fcstm'),
        (5, 'keyword.control.fcstm'),
        (7, 'punctuation.section.mapping.fcstm'),
    ]
    matched_block_pattern = None
    for pattern in declaration_patterns:
        begin_regex = pattern.get('begin')
        if not begin_regex:
            continue
        match = _compile_pattern(begin_regex).search(import_block_sample)
        if not match:
            continue
        matched_block_pattern = pattern
        break
    if matched_block_pattern is None:
        import_block_checkpoint.failures.append(
            f"no declaration pattern with begin captures matched {import_block_sample!r}"
        )
    else:
        begin_captures = matched_block_pattern.get('beginCaptures', {})
        for capture_group, expected_scope in import_block_expectations:
            actual_scope = begin_captures.get(str(capture_group), {}).get('name')
            if actual_scope != expected_scope:
                import_block_checkpoint.failures.append(
                    f"block-form import capture {capture_group} expected scope {expected_scope!r}, "
                    f"got {actual_scope!r}"
                )
    import_block_checkpoint.passed = not import_block_checkpoint.failures
    checkpoints.append(import_block_checkpoint)

    return checkpoints



def _validate_fbmcq_pygments(code: str) -> Tuple[List[ValidationCheckpoint], int, float]:
    lexer = FcstmBmcQueryLexer()
    tokens = list(lexer.get_tokens(code))
    token_map = _token_map(tokens)
    detection_score = FcstmBmcQueryLexer.analyse_text(code)

    checkpoints: List[ValidationCheckpoint] = []

    metadata_checkpoint = ValidationCheckpoint(
        name='FBMCQ Pygments Metadata',
        description='the lexer exposes stable aliases, filenames, and MIME types',
    )
    metadata_expectations = [
        ('name', FcstmBmcQueryLexer.name, 'FCSTM BMC Query'),
        ('aliases', FcstmBmcQueryLexer.aliases, ['fbmcq', 'fcstm-bmc-query']),
        ('filenames', FcstmBmcQueryLexer.filenames, ['*.fbmcq']),
        ('mimetypes', FcstmBmcQueryLexer.mimetypes, ['text/x-fcstm-bmc-query']),
    ]
    for label, actual, expected in metadata_expectations:
        if actual != expected:
            metadata_checkpoint.failures.append(f'{label} expected {expected!r}, got {actual!r}')
    metadata_checkpoint.passed = not metadata_checkpoint.failures
    checkpoints.append(metadata_checkpoint)

    tokenization_checkpoint = ValidationCheckpoint(
        name='FBMCQ Tokenization',
        description='the lexer emits tokens for the shared BMC query test corpus',
    )
    if tokens:
        tokenization_checkpoint.passed = True
    else:
        tokenization_checkpoint.failures.append('lexer returned zero tokens for the BMC query test corpus')
    checkpoints.append(tokenization_checkpoint)

    detection_checkpoint = ValidationCheckpoint(
        name='FBMCQ Language Detection',
        description='analyse_text reports a confident BMC query detection score',
    )
    if detection_score >= 0.5:
        detection_checkpoint.passed = True
    else:
        detection_checkpoint.failures.append(
            f'detection score {detection_score:.2f} is below the required threshold 0.50'
        )
    checkpoints.append(detection_checkpoint)

    for spec in FBMCQ_CHECKPOINT_SPECS:
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


def _validate_fbmcq_textmate_shared(grammar: Dict[str, Any]) -> List[ValidationCheckpoint]:
    checkpoints: List[ValidationCheckpoint] = []

    for spec in FBMCQ_CHECKPOINT_SPECS:
        checkpoint = ValidationCheckpoint(name=spec['name'], description=spec['description'])

        for item in spec['items']:
            matched, failure_detail = _find_textmate_match(grammar, item)
            if not matched:
                checkpoint.failures.append(failure_detail)

        checkpoint.passed = not checkpoint.failures
        checkpoints.append(checkpoint)

    return checkpoints



def _match_textmate_root_token(grammar: Dict[str, Any], source: str, position: int = 0) -> Tuple[Optional[str], Optional[str]]:
    repository = grammar.get('repository', {})
    for include in grammar.get('patterns', []):
        include_name = include.get('include')
        if not include_name or not include_name.startswith('#'):
            continue
        section = repository.get(include_name[1:], {})
        for pattern in section.get('patterns', []):
            regex = pattern.get('match') or pattern.get('begin')
            if not regex:
                continue
            match = _compile_pattern(regex).match(source, position)
            if match:
                return pattern.get('name'), match.group(0)
    return None, None


def _validate_fbmcq_textmate_structure(
    grammar: Dict[str, Any],
    vscode_copy: Dict[str, Any],
    package_json: Dict[str, Any],
) -> List[ValidationCheckpoint]:
    checkpoints: List[ValidationCheckpoint] = []

    sync_checkpoint = ValidationCheckpoint(
        name='FBMCQ Grammar Sync',
        description='canonical and VSCode-packaged BMC query grammars are identical',
    )
    if grammar == vscode_copy:
        sync_checkpoint.passed = True
    else:
        sync_checkpoint.failures.append('canonical BMC query grammar and VSCode-packaged grammar differ')
    checkpoints.append(sync_checkpoint)

    includes_checkpoint = ValidationCheckpoint(
        name='FBMCQ Top-Level Includes',
        description='expected BMC query repository includes are present in pattern order',
    )
    expected_includes = [
        '#comments',
        '#atoms',
        '#clauses',
        '#keywords',
        '#constants',
        '#strings',
        '#numbers',
        '#operators',
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
        name='FBMCQ Repository Sections',
        description='expected BMC query repository sections are present',
    )
    expected_sections = [
        'comments', 'atoms', 'clauses', 'keywords', 'operators',
        'constants', 'strings', 'numbers', 'identifiers',
    ]
    repository = grammar.get('repository', {})
    for section in expected_sections:
        if section not in repository:
            sections_checkpoint.failures.append(f'missing repository section {section!r}')
    sections_checkpoint.passed = not sections_checkpoint.failures
    checkpoints.append(sections_checkpoint)

    numeric_root_checkpoint = ValidationCheckpoint(
        name='FBMCQ Numeric Root Matching',
        description='root include order lets BMC query numbers win over accessor punctuation when appropriate',
    )
    numeric_root_expectations = [
        ('.5', 0, 'constant.numeric.float.fcstm.bmc.query', '.5'),
        ('1.', 0, 'constant.numeric.float.fcstm.bmc.query', '1.'),
        ('0..3', 0, 'constant.numeric.integer.fcstm.bmc.query', '0'),
        ('0..3', 1, 'keyword.operator.range.fcstm.bmc.query', '..'),
        ('0..3', 3, 'constant.numeric.integer.fcstm.bmc.query', '3'),
    ]
    for sample_text, position, expected_scope, expected_text in numeric_root_expectations:
        actual_scope, actual_text = _match_textmate_root_token(grammar, sample_text, position)
        if (actual_scope, actual_text) != (expected_scope, expected_text):
            numeric_root_checkpoint.failures.append(
                f"sample {sample_text!r} at {position} expected {(expected_scope, expected_text)!r}, "
                f"got {(actual_scope, actual_text)!r}"
            )
    numeric_root_checkpoint.passed = not numeric_root_checkpoint.failures
    checkpoints.append(numeric_root_checkpoint)

    operator_checkpoint = ValidationCheckpoint(
        name='FBMCQ Operator Order',
        description='multi-character BMC query operators stay in safe matching order',
    )
    expected_operator_order = [
        '\\*\\*',
        '>>|<<',
        '<=|>=|==|!=',
        '&&|\\|\\|',
        '=>',
        '->',
        '\\.\\.',
        '!',
        '[+\\-*/%&|^~<>]',
        '=|\\?',
        ',|;|:',
        '\\{|\\}|\\(|\\)|\\[|\\]',
        '\\.',
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

    contribution_checkpoint = ValidationCheckpoint(
        name='FBMCQ VSCode Contribution',
        description='package.json registers the BMC query language and grammar',
    )
    contributes = package_json.get('contributes', {})
    languages = contributes.get('languages', [])
    grammars = contributes.get('grammars', [])
    language = next((item for item in languages if item.get('id') == 'fcstm-bmc-query'), None)
    if language is None:
        contribution_checkpoint.failures.append('missing language contribution id "fcstm-bmc-query"')
    else:
        if language.get('extensions') != ['.fbmcq']:
            contribution_checkpoint.failures.append(
                f'language extensions expected [\'.fbmcq\'], got {language.get("extensions")!r}'
            )
        expected_aliases = ['FCSTM BMC Query', 'fbmcq', 'fcstm-bmc-query']
        if language.get('aliases') != expected_aliases:
            contribution_checkpoint.failures.append(
                f'language aliases expected {expected_aliases!r}, got {language.get("aliases")!r}'
            )
    grammar_entry = next((item for item in grammars if item.get('language') == 'fcstm-bmc-query'), None)
    if grammar_entry is None:
        contribution_checkpoint.failures.append('missing grammar contribution for language "fcstm-bmc-query"')
    else:
        if grammar_entry.get('scopeName') != 'source.fcstm.bmc.query':
            contribution_checkpoint.failures.append(
                f'grammar scope expected source.fcstm.bmc.query, got {grammar_entry.get("scopeName")!r}'
            )
        expected_path = './syntaxes/fcstm-bmc-query.tmLanguage.json'
        if grammar_entry.get('path') != expected_path:
            contribution_checkpoint.failures.append(
                f'grammar path expected {expected_path!r}, got {grammar_entry.get("path")!r}'
            )
    contribution_checkpoint.passed = not contribution_checkpoint.failures
    checkpoints.append(contribution_checkpoint)

    negative_checkpoint = ValidationCheckpoint(
        name='FBMCQ VSCode Negative Integration',
        description='BMC query files do not activate FCSTM preview or language-server surfaces',
    )
    suspicious_needles = ('fcstm-bmc-query', '.fbmcq')
    for activation in package_json.get('activationEvents', []):
        if any(needle in activation for needle in suspicious_needles):
            negative_checkpoint.failures.append(f'activation event must not target BMC query files: {activation!r}')
    for menu_name, menu_items in contributes.get('menus', {}).items():
        for item in menu_items:
            when_clause = item.get('when', '')
            if any(needle in when_clause for needle in suspicious_needles):
                negative_checkpoint.failures.append(
                    f'menu {menu_name!r} must not target BMC query files: {when_clause!r}'
                )
    for item in contributes.get('keybindings', []):
        when_clause = item.get('when', '')
        if any(needle in when_clause for needle in suspicious_needles):
            negative_checkpoint.failures.append(f'keybinding must not target BMC query files: {when_clause!r}')
    negative_checkpoint.passed = not negative_checkpoint.failures
    checkpoints.append(negative_checkpoint)

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

    fbmcq_pygments_checkpoints, fbmcq_token_count, fbmcq_detection_score = _validate_fbmcq_pygments(FBMCQ_TEST_CODE)
    fbmcq_canonical_grammar = _load_json(FBMCQ_TEXTMATE_GRAMMAR_FILE)
    fbmcq_vscode_grammar = _load_json(VSCODE_FBMCQ_TEXTMATE_GRAMMAR_FILE)
    vscode_package = _load_json(VSCODE_PACKAGE_FILE)
    fbmcq_textmate_shared_checkpoints = _validate_fbmcq_textmate_shared(fbmcq_canonical_grammar)
    fbmcq_textmate_structure_checkpoints = _validate_fbmcq_textmate_structure(
        fbmcq_canonical_grammar,
        fbmcq_vscode_grammar,
        vscode_package,
    )
    fbmcq_textmate_checkpoints = fbmcq_textmate_shared_checkpoints + fbmcq_textmate_structure_checkpoints

    _print_section('FCSTM Pygments Validation', pygments_checkpoints)
    print(
        f'ℹ️ FCSTM Pygments summary: {_count_passed(pygments_checkpoints)}/{len(pygments_checkpoints)} passed, '
        f'tokens={token_count}, detection={detection_score:.2f}'
    )

    _print_section('FCSTM TextMate Validation', textmate_checkpoints)
    print(
        f'ℹ️ FCSTM TextMate summary: {_count_passed(textmate_checkpoints)}/{len(textmate_checkpoints)} passed'
    )

    _print_section('FBMCQ Pygments Validation', fbmcq_pygments_checkpoints)
    print(
        f'ℹ️ FBMCQ Pygments summary: '
        f'{_count_passed(fbmcq_pygments_checkpoints)}/{len(fbmcq_pygments_checkpoints)} passed, '
        f'tokens={fbmcq_token_count}, detection={fbmcq_detection_score:.2f}'
    )

    _print_section('FBMCQ TextMate and VSCode Validation', fbmcq_textmate_checkpoints)
    print(
        f'ℹ️ FBMCQ TextMate summary: '
        f'{_count_passed(fbmcq_textmate_checkpoints)}/{len(fbmcq_textmate_checkpoints)} passed'
    )

    all_checkpoints = (
        pygments_checkpoints
        + textmate_checkpoints
        + fbmcq_pygments_checkpoints
        + fbmcq_textmate_checkpoints
    )
    all_passed = all(checkpoint.passed for checkpoint in all_checkpoints)

    print('\n======================================================================')
    print('SUMMARY')
    print('======================================================================')
    print(
        f'FCSTM Pygments: {_count_passed(pygments_checkpoints)}/{len(pygments_checkpoints)} passed | '
        f'FCSTM TextMate: {_count_passed(textmate_checkpoints)}/{len(textmate_checkpoints)} passed | '
        f'FBMCQ Pygments: {_count_passed(fbmcq_pygments_checkpoints)}/{len(fbmcq_pygments_checkpoints)} passed | '
        f'FBMCQ TextMate: {_count_passed(fbmcq_textmate_checkpoints)}/{len(fbmcq_textmate_checkpoints)} passed'
    )

    if all_passed:
        print('✅ ALL VALIDATIONS PASSED')
        return 0

    print('❌ VALIDATION FAILURES DETECTED')
    return 1


if __name__ == '__main__':
    sys.exit(main())

# fmt: on
