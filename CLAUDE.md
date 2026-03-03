# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pyfcstm** is a Python framework for parsing Finite State Machine (FSM) Domain-Specific Language (DSL) and generating
executable code in multiple target languages. It focuses on modeling Hierarchical State Machines (Harel Statecharts)
with a Jinja2-based templated code generation system.

## Common Commands

### Testing

```bash
# Run all tests
make unittest

# Run tests in a specific directory
make unittest RANGE_DIR=./config

# Run tests with coverage types
make unittest COV_TYPES="xml term-missing"

# Run tests with minimum coverage requirement
make unittest MIN_COVERAGE=80

# Run tests with parallel workers
make unittest WORKERS=4
```

### Building and Packaging

```bash
# Build package (sdist and wheel)
make package

# Build standalone executable with PyInstaller
make build

# Clean build artifacts
make clean
```

### Documentation

```bash
# Build documentation locally
make docs

# Build production documentation
make pdocs

# Generate RST documentation from Python source files
make rst_auto

# Generate RST for specific directory
make rst_auto RANGE_DIR=model

# LLM-based documentation generation (requires hbllmutils)
make docs_auto              # Generate Python docstrings
make todos_auto             # Complete TODO comments
make tests_auto             # Generate unit tests

# LLM options can be customized
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

### ANTLR Grammar Development

```bash
# Download ANTLR jar and setup (requires Java)
make antlr

# Regenerate parser from grammar file after modifying Grammar.g4
make antlr_build
```

### Sample Test Generation

```bash
# Generate test files from sample DSL files
make sample

# Clean generated sample tests
make sample_clean
```

### CLI Usage

```bash
# Generate PlantUML diagram from DSL
pyfcstm plantuml -i input.fcstm -o output.puml

# Generate code from DSL using templates
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/

# Clear output directory before generation
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/ --clear
```

## Architecture Overview

### Core Components

**DSL Parsing Pipeline** (`pyfcstm/dsl/`)

- `grammar/Grammar.g4`: ANTLR4 grammar definition for the FSM DSL syntax
    - Defines lexer and parser rules for states, transitions, events, expressions
    - Supports hierarchical state definitions with nested composite states
    - Expression grammar includes numeric operations, bitwise operations, conditionals, and function calls
- `parse.py`: Entry point `parse_with_grammar_entry()` for parsing DSL code strings
- `listener.py`: ANTLR listener that walks the parse tree and constructs AST nodes
    - Implements visitor pattern for each grammar rule
    - Handles state definitions, transitions, lifecycle actions, and expressions
- `node.py`: AST node definitions (dataclasses) representing parsed DSL elements
    - Includes nodes for states, transitions, operations, expressions, events
    - Each node type has methods for exporting back to DSL or PlantUML format
- `error.py`: DSL parsing error handling with detailed error messages

**Model Layer** (`pyfcstm/model/`)

- `model.py`: Core state machine model classes
    - `StateMachine`: Root container with variables, states, and global events
    - `State`: Represents states with parent/child relationships, lifecycle actions (enter/during/exit), and transitions
    - `Transition`: Represents state transitions with source, target, event, guard conditions, and effects
    - `Event`: Named events that trigger transitions with scoping (local `::` vs global `:` or `/`)
    - `Operation`: Variable assignments executed during lifecycle actions or transition effects
    - `VarDefine`: Variable definitions with type (int/float) and initial values
    - `OnStage`/`OnAspect`: Lifecycle action containers for enter/during/exit behaviors
- `expr.py`: Expression system for variables, conditions, and effects
    - Supports literals, variables, unary/binary operators, bitwise operations, function calls
    - Conditional expressions with guards for transitions
    - Expression tree structure that can be rendered to different target languages
- `base.py`: Base classes `AstExportable` and `PlantUMLExportable` for model components

The model layer converts AST nodes from the parser into a structured, queryable state machine model with methods like
`walk_states()` for traversal, `find_state()` for lookups, and export capabilities.

**Rendering Engine** (`pyfcstm/render/`)

- `render.py`: Main `StateMachineCodeRenderer` class
    - Loads template directory and `config.yaml` configuration
    - Processes `.j2` Jinja2 templates with state machine model as context
    - Copies static files directly to output directory
    - Supports file ignoring via gitignore-style patterns
- `env.py`: Jinja2 environment setup and configuration
    - Creates sandboxed Jinja2 environment with custom globals, filters, and tests
    - Configures template loader and rendering options
- `expr.py`: Expression rendering for different target languages
    - `create_expr_render_template()`: Creates language-specific expression renderers
    - Supports multiple expression styles: `dsl`, `c`, `cpp`, `python`
    - Converts DSL expressions to target language syntax (e.g., `&&` to `and` for Python)
    - Available as `expr_render` filter in templates: `{{ expr | expr_render(style='c') }}`
- `func.py`: Custom Jinja2 filters and functions
    - `process_item_to_object()`: Converts config items to Python objects (imports, templates, values)
    - Supports importing external Python functions into template context

The rendering engine reads template directories with `config.yaml` and `.j2` files, then renders the state machine model
into target code using Jinja2 templating with custom expression styles.

**Entry Points** (`pyfcstm/entry/`)

- `cli.py`: Command-line interface implementation using Click framework
    - Main entry point `pyfcstmcli()` registered as console script
- `plantuml.py`: PlantUML diagram generation from state machine models
    - Converts DSL to `.puml` format for visualization
- `generate.py`: Template-based code generation
    - Orchestrates parsing DSL, building model, and rendering with templates
- `dispatch.py`: Command dispatching logic for CLI subcommands

**Configuration** (`pyfcstm/config/`)

- `meta.py`: Package metadata (version, author, description)
    - `__VERSION__`: Current package version
    - `__TITLE__`: Package name ('pyfcstm')
    - `__DESCRIPTION__`: Short package description
    - `__AUTHOR__` and `__AUTHOR_EMAIL__`: Author information
    - Used by `setup.py` for package distribution

**Utilities** (`pyfcstm/utils/`)

- `validate.py`: Validation framework for model validation
    - `IValidatable`: Base class for validatable objects with `__validators__` list
    - `ValidationError`: Exception for single validation rule failures
    - `ModelValidationError`: Aggregates multiple validation errors
    - Used throughout model layer to ensure structural integrity
- `text.py`: String normalization utilities
    - `normalize()`: Converts strings to valid identifiers
    - `to_identifier()`: Converts any string to `[0-9a-zA-Z_]+` format with strict mode
    - Handles Unicode via `unidecode`, removes special characters, prevents consecutive underscores
- `doc.py`: Multiline comment formatting
    - `format_multiline_comment()`: Cleans ANTLR4-parsed comments by removing `/* */` markers
    - Normalizes indentation and whitespace for documentation text
- `safe.py`: Safe identifier generation
    - `sequence_safe()`: Converts string sequences to underscore-separated identifiers
    - Normalizes different naming conventions (CamelCase, snake_case, kebab-case) to consistent format
- `binary.py`: Binary file detection utilities
- `decode.py`: Auto-decoding utilities with `auto_decode()` for handling various encodings
- `jinja2.py`: Jinja2 environment utilities
    - `add_builtins_to_env()`: Adds built-in functions to Jinja2 environment
    - `add_settings_for_env()`: Configures Jinja2 environment settings
- `json.py`: JSON operation interface with `IJsonOp` for serialization

### Key Architectural Patterns

**Three-Stage Pipeline**: DSL Text → AST Nodes → State Machine Model → Generated Code

**Template System**: Uses Jinja2 with custom filters and expression styles defined in `config.yaml`. The `expr_styles`
configuration enables cross-language expression rendering (e.g., DSL expressions can be rendered as C, Python, or other
target languages).

**Hierarchical State Machines**: Supports nested states with lifecycle actions (`enter`, `during`, `exit`) and
aspect-oriented programming through `>> during before/after` actions that execute relative to child states.

**Event Scoping**: Three event types - local events (`::` scoped to source state), global events (`:` or `/` scoped from
root), and chain events (`:` scoped to parent).

## DSL Language Reference

The pyfcstm DSL (`.fcstm` files) is a domain-specific language for defining hierarchical finite state machines. It
combines state definitions, transitions, events, and expressions into a concise, readable format.

### Variable Definitions

Variables must be defined at the top of the file before any state definitions:

```
def int counter = 0;
def float temperature = 25.5;
def int flags = 0xFF;           // Hexadecimal literals supported
def int mask = 0b1010;           // Binary literals supported
```

Supported types: `int`, `float`

### State Definitions

**Leaf States** (no nested states):

```
state Idle;                      // Simple leaf state
state Running;                   // Another leaf state
```

**Composite States** (with nested states):

```
state Active {
    state Processing;
    state Waiting;
    [*] -> Processing;           // Initial transition
    Processing -> Waiting :: Done;
}
```

**Pseudo States** (leaf states that skip ancestor aspect actions):

```
pseudo state SpecialState;       // Won't execute parent's >> during actions
```

**Named States** (with display names for documentation):

```
state Running named "System Running";
state Error named "Error State";
```

### Transitions

**Basic Transitions**:

```
StateA -> StateB;                // Simple transition
StateA -> StateB :: EventName;   // Transition with local event
StateA -> StateB : /GlobalEvent; // Transition with global event
```

**Entry and Exit Transitions**:

```
[*] -> InitialState;             // Entry transition (from pseudo-initial state)
FinalState -> [*];               // Exit transition (to pseudo-final state)
[*] -> InitialState :: Start;    // Entry with event
```

**Forced Transitions** (syntactic sugar for multiple transitions):

```
!ErrorState -> [*] :: FatalError;     // Expands to transition from ErrorState
!Running -> SafeMode :: Emergency;    // Expands to transition from Running
!* -> ErrorHandler :: GlobalError;    // Expands to transitions from ALL substates
```

**How Forced Transitions Work:**

Forced transitions are a **syntactic sugar** that expands during model construction to avoid repetitive code. They are *
*NOT** special transitions - they expand to normal transitions that execute exit actions normally.

**Key Points:**

1. **Syntactic Sugar**: Automatically generates multiple normal transitions
2. **Wildcard Expansion**: `!*` creates transitions from all substates in the current scope
3. **Event Sharing**: All expanded transitions share the **same event object**
4. **Normal Execution**: Exit actions execute normally - these are regular transitions
5. **Recursive Propagation**: Propagates to nested substates

Example expansion:

```
state System {
    ! * -> ErrorHandler :: CriticalError;

    state Running {
        state Processing;
        state Waiting;
    }
    state Idle;
}

// Expands to:
// Running -> ErrorHandler :: CriticalError;
// Idle -> ErrorHandler :: CriticalError;
// And inside Running:
//   Processing -> [*] : /CriticalError;  (exit to parent)
//   Waiting -> [*] : /CriticalError;     (exit to parent)
// All transitions share the SAME CriticalError event object
```

**Key Limitations:**

- Forced transitions **cannot** have effect blocks (syntax restriction)
- Use the target state's enter action for initialization instead
- Exit actions execute normally (not bypassed)

**Use Cases:**

- Avoid repetitive code when many states need the same transition
- Error handling from multiple states
- Emergency shutdown from all states
- Timeout handling across multiple states

**Transitions with Guard Conditions**:

```
Idle -> Active : if [counter >= 10];
Active -> Idle : if [temperature < 20.0];
StateA -> StateB : if [flags & 0x01];  // Bitwise operations
```

**Transitions with Effects** (execute operations on transition):

```
Idle -> Running effect {
    counter = 0;
    flags = flags | 0x01;
}

Running -> Idle :: Stop effect {
    counter = counter + 1;
}
```

**Combined Guard and Effect**:

```
StateA -> StateB : if [counter < 100] effect {
    counter = counter + 1;
}
```

### Event Scoping

The DSL provides **three event scoping mechanisms** to control event namespaces in hierarchical state machines:

**1. Local Events** (`::` - scoped to source state):

```
StateA -> StateB :: LocalEvent;
// Event is scoped to source state: Parent.StateA.LocalEvent
// Equivalent to: StateA -> StateB : /Parent.StateA.LocalEvent
```

Each source state gets its own event. Use when each transition needs a unique event.

**2. Chain Events** (`:` - scoped to parent state):

```
StateA -> StateB : ChainEvent;
// Event is scoped to parent state: Parent.ChainEvent
// Equivalent to: StateA -> StateB : /Parent.ChainEvent
```

Multiple transitions in the same scope share the event. Use when coordinating sibling state transitions.

**3. Absolute Events** (`/` - scoped to root state):

```
StateA -> StateB : /GlobalEvent;
// Event is scoped to root state: Root.GlobalEvent
// Already absolute - no conversion needed
```

All transitions using the same absolute path share the event. Use for cross-module communication or global events.

**Event Resolution Examples:**

```
state System {
    state ModuleA {
        state A1;
        state A2;

        [*] -> A1;
        A1 -> A2 :: E;        // System.ModuleA.A1.E
        A1 -> A2 : E;         // System.ModuleA.E
        A1 -> A2 : /E;        // System.E
    }

    state ModuleB {
        state B1;
        state B2;

        [*] -> B1;
        B1 -> B2 :: E;        // System.ModuleB.B1.E (different from A1's)
        B1 -> B2 : E;         // System.ModuleB.E (different from ModuleA's)
        B1 -> B2 : /E;        // System.E (SAME as ModuleA's)
    }
}
```

**Key Points:**

- `::` creates state-specific events (avoid conflicts)
- `:` creates parent-scoped events (share within scope)
- `/` creates root-scoped events (share globally)
- All three are equivalent to absolute paths with different starting points

### Lifecycle Actions

**Enter Actions** (executed when entering a state):

```
state Active {
    enter {
        counter = 0;
        flags = 0xFF;
    }
}
```

**During Actions** (executed while in a state):

```
state Running {
    during {
        counter = counter + 1;
    }
}
```

**Exit Actions** (executed when leaving a state):

```
state Active {
    exit {
        counter = 0;
    }
}
```

**Aspect Actions for Composite States** (`before` or `after` child state actions):

```
state Parent {
    // For composite states, specify before/after
    during before {
        // Executed before child state's during
    }

    during after {
        // Executed after child state's during
    }

    state Child {
        during {
            // Child's during action
        }
    }
}
```

**Aspect Actions at Root Level** (`>>` - applies to all descendant states):

```
state Root {
    >> during before {
        // Executed before any descendant's during action
    }

    >> during after {
        // Executed after any descendant's during action
    }

    state Child1;
    state Child2;
}
```

### Abstract Actions

Abstract actions declare functions that must be implemented in the generated code:

```
state Active {
    enter abstract InitializeHardware;

    enter abstract SetupSystem /*
        Initialize the system hardware and peripherals.
        TODO: Implement in generated code framework
    */

    during before abstract PreProcessing;
    exit abstract Cleanup;
}
```

### Reference Actions

Reference actions reuse lifecycle actions from other states:

```
state StateA {
    enter UserInit {
        counter = 0;
    }
}

state StateB {
    enter ref StateA.UserInit;      // Reuse StateA's enter action
    exit ref /GlobalCleanup;        // Reference global action
}
```

### Expression System

**IMPORTANT**: The fcstm DSL strictly separates arithmetic expressions (`num_expression`) from logical/boolean
expressions (`cond_expression`). Unlike common high-level languages, you cannot mix arithmetic and logical operations
freely. Assignments require arithmetic expressions, guard conditions require boolean expressions, and comparison
operators bridge the two by taking arithmetic operands and producing boolean results.

**Arithmetic Operators**:

```
counter = 10 + 5;
result = a * b - c / d;
power = base ** exponent;        // Exponentiation
modulo = value % 10;
```

**Bitwise Operators**:

```
flags = 0xFF & 0x0F;             // AND
flags = flags | 0x01;            // OR
flags = flags ^ 0x10;            // XOR
shifted = value << 2;            // Left shift
shifted = value >> 1;            // Right shift
```

**Comparison Operators** (in guard conditions):

```
StateA -> StateB : if [counter >= 10];
StateA -> StateB : if [temp < 20.0];
StateA -> StateB : if [flags == 0xFF];
StateA -> StateB : if [status != 0];
```

**Logical Operators** (in guard conditions):

```
StateA -> StateB : if [counter > 10 && temp < 30];
StateA -> StateB : if [flag1 || flag2];
StateA -> StateB : if [!error_flag];
StateA -> StateB : if [counter > 10 and temp < 30];  // 'and' keyword
StateA -> StateB : if [flag1 or flag2];              // 'or' keyword
StateA -> StateB : if [not error_flag];              // 'not' keyword
```

**Ternary Conditional Expressions** (converts boolean to arithmetic):

```
result = (condition) ? value_if_true : value_if_false;
counter = (temp > 25) ? 1 : 0;   // Use ternary to convert boolean to int
```

**Common Errors**:

```
// ERROR: Cannot assign boolean to variable
result = (x > 10);               // Syntax error

// ERROR: Cannot use arithmetic as condition
StateA -> StateB : if [counter]; // Syntax error

// CORRECT: Use ternary or comparison
result = (x > 10) ? 1 : 0;       // Valid
StateA -> StateB : if [counter > 0];  // Valid
```

**Function Calls**:

```
result = sin(angle);
value = sqrt(x * x + y * y);
```

### Complete Example

```
def int counter = 0;
def int error_count = 0;
def float temperature = 25.0;

state System {
    >> during before {
        // Global pre-processing for all states
        counter = counter + 1;
    }

    >> during before abstract GlobalMonitor;

    [*] -> Initializing;
    !* -> Error :: FatalError;

    state Initializing {
        enter {
            counter = 0;
            error_count = 0;
        }

        enter abstract HardwareInit /*
            Initialize hardware peripherals
            TODO: Implement in generated code
        */

        exit {
            temperature = 25.0;
        }
    }

    state Running {
        during before abstract PreProcess;

        during before {
            temperature = temperature + 0.1;
        }

        during after {
            // Post-processing
        }

        state Active {
            during {
                counter = counter + 1;
            }
        }

        state Idle;

        [*] -> Active;
        Active -> Idle :: Pause;
        Idle -> Active :: Resume;
    }

    state Error {
        enter {
            error_count = error_count + 1;
        }
    }

    Initializing -> Running : if [counter >= 10] effect {
        counter = 0;
    };

    Running -> Error : if [temperature > 100.0];
    Error -> [*] : if [error_count > 5];
}
```

### Key DSL Concepts

**Hierarchical State Execution Order**:

Understanding how actions execute in hierarchical state machines is crucial for building correct state machine logic.
The execution order differs significantly between **leaf states** (states with no children) and **composite states** (
states with children).

When a leaf state is active in a hierarchical state machine, the execution order follows a precise sequence that
combines ancestor aspect actions with the leaf state's own actions. Here's a complete example:

```
def int log_counter = 0;

state System {
    // Aspect actions with >> apply to ALL descendant leaf states
    // These execute during the leaf state's "during" phase
    >> during before {
        log_counter = log_counter + 1;  // Executes for ALL leaf states (Active, Idle)
    }

    >> during after {
        log_counter = log_counter + 100;  // Executes for ALL leaf states (Active, Idle)
    }

    state SubSystem {
        // Composite state actions (without >>) execute ONLY when entering/exiting the composite state
        // CRITICAL: during before/after are NOT triggered during child-to-child transitions!

        // during before: executes ONLY on [*] -> Child (entering composite state from parent)
        //                AFTER SubSystem.enter but BEFORE Child.enter
        //                NOT executed on Child1 -> Child2 transitions
        during before {
            log_counter = log_counter + 10;  // Only when entering from parent: [*] -> Active
        }

        // during after: executes ONLY on Child -> [*] (exiting composite state to parent)
        //               AFTER Child.exit but BEFORE SubSystem.exit
        //               NOT executed on Child1 -> Child2 transitions
        during after {
            log_counter = log_counter + 1000;  // Only when exiting to parent: Idle -> [*]
        }

        state Active {
            // Leaf state's own during action
            during {
                log_counter = log_counter + 50;  // Executes every cycle while Active is the current state
            }
        }

        state Idle {
            during {
                log_counter = log_counter + 5;
            }
        }

        [*] -> Active;                        // Triggers SubSystem.during before
        Active -> Idle :: Pause;              // Does NOT trigger during before/after
        Idle -> Active :: Resume;             // Does NOT trigger during before/after
        Idle -> [*] :: Stop;                  // Triggers SubSystem.during after
    }

    [*] -> SubSystem;
}
```

**Complete Execution Order for `System.SubSystem.Active`**:

**Scenario 1: Initial Entry** (`System.[*] -> SubSystem -> [*] -> Active`)

**Entry Phase**:

1. `System.enter` - Root state enter actions
2. `SubSystem.enter` - Composite state enter actions
3. `SubSystem.during before` - **Triggered** (because `[*] -> Active`)
4. `Active.enter` - Leaf state enter actions

**During Phase** (each cycle while `Active` remains active):

1. `System >> during before` - Aspect action (executes for ALL leaf states)
2. `Active.during` - Leaf state's own during action
3. `System >> during after` - Aspect action (executes for ALL leaf states)

Note: `SubSystem.during before/after` do **NOT** execute during the `during` phase.

**Scenario 2: Child-to-Child Transition** (`Active -> Idle :: Pause`)

**Transition Sequence**:

1. `Active.exit` - Leaf state exit actions
2. (Transition effect, if any)
3. `Idle.enter` - Leaf state enter actions

**CRITICAL**: `SubSystem.during before/after` are **NOT triggered** during child-to-child transitions!

**Scenario 3: Exit from Composite State** (`Idle -> [*] :: Stop`)

**Exit Phase**:

1. `Idle.exit` - Leaf state exit actions
2. `SubSystem.during after` - **Triggered** (because `Idle -> [*]`)
3. `SubSystem.exit` - Composite state exit actions
4. `System.exit` - Root state exit actions

**Key Concepts**:

**Aspect Actions (`>> during before/after`)**:

- Apply to **all descendant leaf states** in the hierarchy
- Execute during the **leaf state's `during` phase** (every cycle)
- Flow from root to leaf for `before`, leaf to root for `after`
- Enable cross-cutting concerns like logging, monitoring, validation

**Composite State Actions (`during before/after` without `>>`)**:

- `during before`: Executes **ONLY** when entering composite state from parent (`[*] -> Child`)
    - Executes AFTER composite state's `enter` but BEFORE child state's `enter`
    - **NOT triggered** during child-to-child transitions (`Child1 -> Child2`)
- `during after`: Executes **ONLY** when exiting composite state to parent (`Child -> [*]`)
    - Executes AFTER child state's `exit` but BEFORE composite state's `exit`
    - **NOT triggered** during child-to-child transitions (`Child1 -> Child2`)
- Do **NOT** execute during a leaf state's `during` phase
- Used for setup/cleanup when entering/exiting the composite state boundary

**Leaf State Actions (`during`)**:

- Execute every cycle while the leaf state is active
- Sandwiched between ancestor aspect `before` and `after` actions

**Execution Flow Summary**:

- **Entry** (from parent): `State.enter` → `State.during before` → `Child.enter`
- **During** (each cycle): Aspect `>> during before` → Leaf `during` → Aspect `>> during after`
- **Exit** (to parent): `Child.exit` → `State.during after` → `State.exit`
- **Child-to-Child Transition**: `Child1.exit` → (transition effect) → `Child2.enter` (no `during before/after`)

**Aspect-Oriented Programming**:

- `>> during before/after` actions provide cross-cutting concerns
- Applied to all descendant leaf states unless marked as `pseudo state`
- Enables separation of monitoring, logging, or validation logic
- Aspect actions execute in hierarchical order (root to leaf) for `before`, and (leaf to root) for `after`
- Multiple aspect actions at the same level execute in definition order

**Event Namespace Resolution**:

- `::` creates events in source state's namespace
- `:` or `/` references events from root or parent namespaces
- Enables hierarchical event organization and reuse

## Python Docstring Style Guide

This project uses **reStructuredText (reST)** format for all Python docstrings, following PEP 257 conventions and Sphinx documentation standards. Consistency in documentation style is critical for maintainability and automated documentation generation.

### Core Principles

1. **Format**: Use reStructuredText (reST) markup exclusively
2. **Completeness**: Document all public APIs (modules, classes, functions, methods)
3. **Clarity**: Write for both users and maintainers—explain the "why" and "what"
4. **Cross-references**: Use reST roles (`:class:`, `:func:`, `:mod:`) to link related components
5. **Examples**: Include practical usage examples for most public APIs
6. **Tone**: Professional, clear, and technical but accessible

### Module-Level Docstrings

Module docstrings should provide a comprehensive overview of the module's purpose and contents:

```python
"""
Brief one-line description of the module.

Longer description explaining the module's purpose, main capabilities,
and how it fits into the larger system. Can span multiple paragraphs.

The module contains the following main components:

* :class:`ClassName` - Brief description of the class
* :func:`function_name` - Brief description of the function
* :data:`variable_name` - Brief description of module-level data

.. note::
   Additional notes about usage, requirements, or important caveats.

Example::

    >>> from module import something
    >>> result = something()
    >>> result
    expected_output
"""
```

**Real example from the codebase** ([pyfcstm/dsl/parse.py](pyfcstm/dsl/parse.py)):

```python
"""
Grammar parsing utilities for the pyfcstm domain-specific language.

This module provides helper functions for parsing grammar-based input text using
ANTLR4-generated lexer/parser classes and a parse-tree listener that converts
ANTLR parse trees into internal node objects.

The module contains the following main components:

* :func:`parse_with_grammar_entry` - Parse text using an arbitrary grammar entry rule.
* :func:`parse_condition` - Parse a condition expression.
* :func:`parse_preamble` - Parse a preamble program.

.. note::
   All parsing relies on the ANTLR4-generated classes from
   :mod:`pyfcstm.dsl.grammar` and may raise :exc:`pyfcstm.dsl.error.GrammarParseError`
   when input does not conform to the grammar.
"""
```

### Class Docstrings

Class docstrings document the class purpose, constructor parameters, and instance/class variables:

```python
class ClassName:
    """
    Brief one-line description of the class.

    Longer explanation of the class purpose, responsibilities, and usage patterns.
    Explain what the class represents and how it should be used.

    :param param_name: Description of constructor parameter
    :type param_name: ParamType
    :param optional_param: Description, defaults to ``default_value``
    :type optional_param: ParamType, optional

    :ivar instance_var: Description of instance variable
    :vartype instance_var: VarType
    :ivar another_var: Description of another instance variable
    :vartype another_var: AnotherType

    :cvar class_var: Description of class variable
    :type class_var: ClassVarType

    Example::

        >>> obj = ClassName(param_name=value)
        >>> obj.method()
        expected_result
    """
```

**Real example from the codebase** ([pyfcstm/render/render.py](pyfcstm/render/render.py)):

```python
class StateMachineCodeRenderer:
    """
    Renderer for generating code from state machine models using templates.

    This class handles rendering of state machine models into code by combining
    a template directory with a configuration file. It creates a Jinja2
    environment, registers expression rendering styles, and maps template files
    to rendering operations or file copying operations.

    :param template_dir: Directory containing the templates and configuration
    :type template_dir: str
    :param config_file: Name of the configuration file within the template directory,
        defaults to ``'config.yaml'``
    :type config_file: str, optional

    :ivar template_dir: Absolute path to the template directory
    :vartype template_dir: str
    :ivar config_file: Absolute path to the configuration file
    :vartype config_file: str
    :ivar env: Jinja2 environment used for rendering
    :vartype env: jinja2.Environment
    :ivar _ignore_patterns: List of git-style ignore patterns
    :vartype _ignore_patterns: List[str]

    Example::

        >>> renderer = StateMachineCodeRenderer('./templates')
        >>> renderer.render(my_state_machine, './output', clear_previous_directory=True)
    """
```

### Function and Method Docstrings

Function/method docstrings follow this structure:

```python
def function_name(param1: Type1, param2: Type2, optional_param: Type3 = default) -> ReturnType:
    """
    Brief one-line description of what the function does.

    Longer explanation of the function's behavior, algorithm, or important details.
    Explain edge cases, assumptions, or non-obvious behavior.

    :param param1: Description of the first parameter
    :type param1: Type1
    :param param2: Description of the second parameter
    :type param2: Type2
    :param optional_param: Description of optional parameter, defaults to ``default``
    :type optional_param: Type3, optional
    :return: Description of what is returned
    :rtype: ReturnType
    :raises ExceptionType: Description of when this exception is raised
    :raises AnotherException: Description of another exception condition

    Example::

        >>> result = function_name(arg1, arg2)
        >>> result
        expected_output
    """
```

**Real example from the codebase** ([pyfcstm/entry/generate.py](pyfcstm/entry/generate.py)):

```python
def generate(
    input_code_file: str,
    template_dir: str,
    output_dir: str,
    clear_directory: bool,
) -> None:
    """
    Generate code from a state machine DSL file using templates.

    This command reads the DSL file as bytes, decodes it with
    :func:`pyfcstm.utils.auto_decode`, parses it with the grammar entry
    ``state_machine_dsl``, converts the AST to a state machine model, and
    renders output using :class:`pyfcstm.render.StateMachineCodeRenderer`.

    :param input_code_file: Path to the input DSL code file.
    :type input_code_file: str
    :param template_dir: Path to the directory containing templates.
    :type template_dir: str
    :param output_dir: Path to the directory where generated code will be written.
    :type output_dir: str
    :param clear_directory: Whether to clear the output directory before rendering.
    :type clear_directory: bool
    :return: ``None``.
    :rtype: None

    :raises UnicodeDecodeError: If the input file cannot be decoded.
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises IOError: If reading the input file or writing output files fails.

    Example::

        $ pyfcstm generate -i ./machine.dsl -t ./templates -o ./out --clear
    """
```

### Dataclass Docstrings

Dataclasses document their fields using `:param:` and `:type:` tags:

```python
@dataclass
class DataClassName:
    """
    Brief description of what this dataclass represents.

    Longer explanation of the dataclass purpose and usage.

    :param field1: Description of the first field
    :type field1: Type1
    :param field2: Description of the second field
    :type field2: Type2

    Example::

        >>> obj = DataClassName(field1=value1, field2=value2)
        >>> obj.field1
        value1
    """
    field1: Type1
    field2: Type2
```

**Real example from the codebase** ([pyfcstm/model/model.py](pyfcstm/model/model.py)):

```python
@dataclass
class Operation(AstExportable):
    """
    Represents an operation that assigns a value to a variable.

    An operation consists of a variable name and an expression that will be
    assigned to the variable when the operation is executed.

    :param var_name: The name of the variable to assign to
    :type var_name: str
    :param expr: The expression to evaluate and assign to the variable
    :type expr: Expr

    Example::

        >>> op = Operation(var_name="counter", expr=some_expr)
        >>> op.var_name
        'counter'
    """
    var_name: str
    expr: Expr
```

### Parameter Documentation Patterns

**Required parameters**:
```python
:param param_name: Description of the parameter
:type param_name: type_annotation
```

**Optional parameters with defaults**:
```python
:param param_name: Description, defaults to ``default_value``
:type param_name: type_annotation, optional
```

**Note**: Use double backticks for inline code (`` ``default_value`` ``).

### Return Value Documentation

Always document both the description and type:

```python
:return: Description of what is returned
:rtype: ReturnType
```

For functions returning `None`:
```python
:return: ``None``.
:rtype: None
```

### Exception Documentation

Document all exceptions that may be raised:

```python
:raises ExceptionType: Description of when this exception is raised
:raises AnotherException: Description of another exception condition
```

Use fully qualified exception names when referencing custom exceptions:
```python
:raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
```

### Cross-References and Markup

Use reST roles to create hyperlinks in generated documentation:

- **Classes**: `:class:`ClassName`` or `:class:`module.ClassName``
- **Functions**: `:func:`function_name`` or `:func:`module.function_name``
- **Methods**: `:meth:`method_name`` or `:meth:`Class.method_name``
- **Modules**: `:mod:`module.name``
- **Exceptions**: `:exc:`ExceptionType``
- **Data/Variables**: `:data:`variable_name``
- **Attributes**: `:attr:`attribute_name``

**Example**:
```python
"""
This function uses :class:`StateMachineCodeRenderer` to render templates.
It calls :func:`parse_with_grammar_entry` from :mod:`pyfcstm.dsl.parse`
and may raise :exc:`pyfcstm.dsl.error.GrammarParseError`.
"""
```

### Examples in Docstrings

Include practical examples using the `Example::` directive (note the double colon):

```python
Example::

    >>> from pyfcstm.utils.text import normalize
    >>> normalize("Hello World!")
    'Hello_World'
    >>> normalize("test-case")
    'test_case'
```

For CLI examples, use shell syntax without `>>>`:

```python
Example::

    $ pyfcstm plantuml -i input.fcstm -o output.puml
    $ pyfcstm generate -i input.fcstm -t templates/ -o output/
```

### Special Directives

Use reST directives for special content:

**Notes**:
```python
.. note::
   Important information or caveats about usage.
```

**Warnings**:
```python
.. warning::
   Critical warnings about potential issues or dangers.
```

### Instance and Class Variables

**Instance variables** (use `:ivar:` and `:vartype:`):
```python
:ivar variable_name: Description of the instance variable
:vartype variable_name: VariableType
```

**Class variables** (use `:cvar:` and `:type:`):
```python
:cvar class_variable: Description of the class variable
:type class_variable: ClassVariableType
```

### Common Patterns in pyfcstm

**AST and Model Conversions**:
```python
def to_ast_node(self) -> dsl_nodes.ASTNode:
    """
    Convert this model object to an AST node representation.

    :return: An AST node representing this object.
    :rtype: pyfcstm.dsl.node.ASTNode
    """
```

**State Machine Domain Concepts**:
Use domain-specific terminology consistently: states, transitions, events, lifecycle actions, guards, effects, composite states, leaf states, aspect actions.

**Template and Rendering Context**:
Document Jinja2 template integration and expression rendering styles when relevant.

### Checklist for Writing Docstrings

When writing or reviewing docstrings, ensure:

- [ ] Brief one-line summary at the top
- [ ] Longer explanation if the function/class is non-trivial
- [ ] All parameters documented with `:param:` and `:type:`
- [ ] Return value documented with `:return:` and `:rtype:`
- [ ] All exceptions documented with `:raises:`
- [ ] Cross-references use reST roles (`:class:`, `:func:`, etc.)
- [ ] Examples included for public APIs
- [ ] Inline code uses double backticks (`` ``value`` ``)
- [ ] Optional parameters marked with ``, optional`` in type
- [ ] Default values shown in parameter description
- [ ] Tone is professional and clear
- [ ] No typos or grammatical errors

### Anti-Patterns to Avoid

**DON'T**:
- Use Google-style or NumPy-style docstrings (use reST only)
- Omit type information (always include `:type:` and `:rtype:`)
- Use single backticks for inline code (use double backticks)
- Write vague descriptions like "Does something" or "Helper function"
- Forget to document exceptions
- Use bare class/function names without reST roles
- Include implementation details that may change
- Write overly verbose documentation for trivial functions

**DO**:
- Follow the reST format consistently
- Explain the "why" and "what", not just the "how"
- Use cross-references to connect related components
- Include practical examples
- Keep descriptions concise but complete
- Update docstrings when code changes

## Development Notes

### LLM-Based Documentation Generation

The project includes tools for automated documentation generation using Large Language Models (LLMs), migrated from the hbutils project.

#### Overview

The LLM documentation system provides:

1. **RST Generation** - Automatically generate reStructuredText documentation from Python source files
2. **Pydoc Generation** - Generate comprehensive Python docstrings using LLMs (requires `hbllmutils`)
3. **TODO Completion** - Complete TODO comments in code using contextual analysis (requires `hbllmutils`)
4. **Unit Test Generation** - Generate unit tests for Python modules (requires `hbllmutils`)

#### Setup

**For RST Generation Only** (no additional setup needed):
- Uses standard dependencies already in `requirements.txt`
- Scripts: `auto_rst.py` and `auto_rst_top_index.py`

**For LLM-Based Features** (pydoc, todo, unittest):

1. Install `hbllmutils`:
   ```bash
   pip install hbllmutils
   ```

2. Configure LLM API:
   ```bash
   cp .llmconfig.yaml.example .llmconfig.yaml
   # Edit .llmconfig.yaml and add your API token
   ```

3. The `.llmconfig.yaml` file is gitignored to protect API credentials.

#### Usage

**RST Documentation Generation**:

```bash
# Generate RST for all Python files
make rst_auto

# Generate RST for specific directory
make rst_auto RANGE_DIR=model

# Generate top-level API index
python auto_rst_top_index.py -i pyfcstm -o docs/source/api_doc.rst
```

**LLM-Based Documentation** (requires `hbllmutils`):

```bash
# Generate Python docstrings
make docs_auto

# Complete TODO comments
make todos_auto

# Generate unit tests
make tests_auto

# Customize LLM options
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

#### File Structure

```
pyfcstm/
├── auto_rst.py                    # RST generation from Python files
├── auto_rst_top_index.py          # Top-level API index generation
├── .llmconfig.yaml.example        # Example LLM configuration
├── .llmconfig.yaml                # Your LLM configuration (gitignored)
├── LLM_DOCS_README.md             # Detailed documentation
└── docs/source/api_doc/           # Generated RST files
```

#### Key Features

**RST Generation** (`auto_rst.py`):
- Uses AST parsing to extract public members (classes, functions, variables)
- Generates Sphinx directives (`automodule`, `autoclass`, `autofunction`, `autodata`)
- Creates toctree navigation for packages
- Handles `__init__.py` files specially to create package indexes

**LLM-Based Generation** (via `hbllmutils`):
- Analyzes code structure, imports, and dependencies
- Generates contextually appropriate documentation/code
- Validates generated code syntax with AST parsing
- Supports multiple LLM providers (DeepSeek, OpenRouter, etc.)

#### Configuration

The `AUTO_OPTIONS` variable in the Makefile controls LLM behavior:

```makefile
AUTO_OPTIONS ?= --param max_tokens=400000 --no-ignore-module pyfcstm --model-name deepseek-chat
```

Common options:
- `--param max_tokens=N` - Set maximum tokens for LLM response
- `--model-name MODEL` - Specify LLM model to use
- `--no-ignore-module pyfcstm` - Don't ignore pyfcstm imports in analysis
- `--timeout SECONDS` - API request timeout (default: 210s)

#### Best Practices

1. **Start with RST Generation** - Generate RST files first to establish documentation structure
2. **Review LLM Output** - Always review generated docstrings and code before committing
3. **Incremental Updates** - Use `RANGE_DIR` to target specific modules for updates
4. **Version Control** - Commit generated documentation separately from code changes
5. **API Token Security** - Never commit `.llmconfig.yaml` to git

For detailed information, see `LLM_DOCS_README.md`.

### ANTLR Grammar Modifications

When modifying `pyfcstm/dsl/grammar/Grammar.g4`:

1. Ensure Java is installed
2. Run `make antlr` to download ANTLR jar (only needed once)
3. Run `make antlr_build` to regenerate parser code
4. Update `listener.py` and `node.py` if grammar structure changes
5. **Update syntax highlighting implementations** to match grammar changes:
   - `pyfcstm/highlight/pygments_lexer.py` - Pygments lexer (serves as reference implementation)
   - `editors/fcstm.tmLanguage.json` - TextMate grammar
6. **Validate syntax highlighting** after changes:
   - Run `python editors/validate.py` to verify Pygments lexer works correctly
7. Run tests to verify changes

**Important Notes for Syntax Highlighting Updates:**

- **Operator Ordering**: When adding new operators, ensure multi-character operators are matched before single-character ones to avoid tokenization conflicts. For example:
  - `**` must come before `*`
  - `<<` must come before `<`
  - `<=`, `>=`, `==`, `!=` must come before `<`, `>`, `!`
  - `&&`, `||` must come before `!`

- **Consistency**: Both implementations (Pygments, TextMate) should be kept in sync. The Pygments lexer serves as the reference implementation.

- **Testing**: The `editors/validate.py` script provides comprehensive validation with 20+ checkpoints covering all ANTLR grammar rules. All checkpoints must pass (100% pass rate) before committing changes.

**Adding New Keywords:**

When adding new keywords to the FCSTM grammar:

1. Update `pyfcstm/dsl/grammar/Grammar.g4` with the new keyword
2. Regenerate parser: `make antlr_build`
3. Update `pyfcstm/highlight/pygments_lexer.py`:
   - Add keyword to appropriate `words()` group (Declaration, Reserved, Namespace, Type, etc.)
4. Update `editors/fcstm.tmLanguage.json`:
   - Add keyword to appropriate pattern in the `keywords` repository section
5. Run `python editors/validate.py` to verify all changes work correctly

### Template Development

Template directories must contain:

- `config.yaml`: Defines `expr_styles`, `globals`, `filters`, and `ignores`
- `.j2` files: Jinja2 templates with access to the state machine model
- Static files: Copied directly to output (preserve directory structure)

Key model objects in templates:

- `model`: Root state machine object
- `model.walk_states()`: Iterator over all states
- `state.name`, `state.is_leaf_state`, `state.transitions`, `state.parent`
- `transition.from_state`, `transition.to_state`, `transition.guard`, `transition.effects`

Use `{{ expr | expr_render(style='c') }}` to render expressions in target language syntax.

### Testing Strategy

- Tests are organized by module in `test/` directory
- Use `@pytest.mark.unittest` for unit tests
- Sample DSL files in `test/testfile/sample_codes/` auto-generate tests via `make sample`
- Negative test cases in `test/testfile/sample_neg_codes/`
- Test timeout is 300 seconds (configured in `pytest.ini`)

### Dependencies

Core runtime dependencies (see `requirements.txt`):

- `antlr4-python3-runtime==4.9.3`: Parser runtime
- `jinja2>=3`: Template engine
- `pyyaml`: Configuration parsing
- `click>=8`: CLI framework
- `hbutils>=0.14.0`: Utility functions
- `pathspec`: Git-like pattern matching for ignores

Development requires `ruff` for formatting (see `requirements-dev.txt`).

### Documentation Editing

The documentation system uses Sphinx with a sophisticated build pipeline that automatically generates derived resources
from source files. Understanding this pipeline is critical to avoid editing generated files that will be overwritten.

#### Documentation Structure

Documentation source files are in `docs/source/` with the following organization:

- `*.rst` files: ReStructuredText documentation pages
- `*.md` files: Markdown documentation pages
- `*.mk` files: Makefile fragments defining resource generation rules
- `conf.py`: Sphinx configuration
- Subdirectories: `tutorials/`, `information/`, `api_doc/`, etc.

#### Resource Generation Pipeline

The documentation build system uses multiple Makefile fragments (`*.mk`) to define generation rules for different
resource types. These rules create a dependency chain where source files generate intermediate files, which in turn
generate final output files.

**CRITICAL RULE**: Always edit source files only. Never edit generated files directly, as they will be overwritten
during the next build.

#### Generation Rules by File Type

**1. FSM DSL to Diagrams** (`fcstms.mk`)

Source files with `.fcstm` extension generate PlantUML and image files:

```
*.fcstm → *.fcstm.puml → *.fcstm.puml.png
                       → *.fcstm.puml.svg
```

- **Edit**: `*.fcstm` files only
- **Generated** (do not edit): `*.fcstm.puml`, `*.fcstm.puml.png`, `*.fcstm.puml.svg`
- **Commands**:
    - `make -f docs/source/fcstms.mk SOURCE=docs/source build` - Generate all FSM diagrams
    - `make -f docs/source/fcstms.mk SOURCE=docs/source clean` - Remove generated files

**2. PlantUML to Images** (`diagrams.mk`)

Standalone PlantUML files (not generated from `.fcstm`) generate image files:

```
*.puml → *.puml.png
       → *.puml.svg
```

- **Edit**: `*.puml` files only (unless they have `.fcstm.puml` extension, which are generated)
- **Generated** (do not edit): `*.puml.png`, `*.puml.svg`
- **Commands**:
    - `make -f docs/source/diagrams.mk SOURCE=docs/source build` - Generate PlantUML images
    - `make -f docs/source/diagrams.mk SOURCE=docs/source clean` - Remove generated images

**3. Graphviz to Images** (`graphviz.mk`)

Graphviz DOT files generate image files:

```
*.gv → *.gv.png
     → *.gv.svg
```

- **Edit**: `*.gv` files only
- **Generated** (do not edit): `*.gv.png`, `*.gv.svg`
- **Commands**:
    - `make -f docs/source/graphviz.mk SOURCE=docs/source build` - Generate Graphviz images
    - `make -f docs/source/graphviz.mk SOURCE=docs/source clean` - Remove generated images

**4. Demo Scripts to Output** (`demos.mk`)

Python and shell demo scripts generate output files:

```
*.demo.py → *.demo.py.txt
*.demox.py → *.demox.py.txt + *.demox.py.err + *.demox.py.exitcode
*.plot.py → *.plot.py.svg
*.demo.sh → *.demo.sh.txt
*.demox.sh → *.demox.sh.txt + *.demox.sh.err + *.demox.sh.exitcode
```

- **Edit**: `*.demo.py`, `*.demox.py`, `*.plot.py`, `*.demo.sh`, `*.demox.sh` files only
- **Generated** (do not edit): `*.py.txt`, `*.py.err`, `*.py.exitcode`, `*.py.svg`, `*.sh.txt`, `*.sh.err`,
  `*.sh.exitcode`
- **Commands**:
    - `make -f docs/source/demos.mk SOURCE=docs/source build` - Run all demo scripts
    - `make -f docs/source/demos.mk SOURCE=docs/source clean` - Remove generated outputs
    - `make -f docs/source/demos.mk SOURCE=docs/source cleanplt` - Remove plot outputs only

**5. Jupyter Notebooks** (`notebook.mk`)

Jupyter notebooks generate executed versions:

```
*.ipynb → *.result.ipynb
```

- **Edit**: `*.ipynb` files only (with outputs cleared)
- **Generated** (do not edit): `*.result.ipynb`
- **Commands**:
    - `make -f docs/source/notebook.mk SOURCE=docs/source build` - Execute notebooks
    - `make -f docs/source/notebook.mk SOURCE=docs/source clean` - Remove executed notebooks and clear outputs

#### Unified Build Commands

The `all.mk` file orchestrates all generation rules. Use these commands from `docs/source/`:

```bash
# Generate all resources (diagrams, demos, notebooks, etc.)
make -f all.mk build

# Clean all generated resources
make -f all.mk clean

# Clean plot outputs only
make -f all.mk cleanplt

# Install documentation dependencies
make -f all.mk pip
```

From the `docs/` directory, use the main Makefile:

```bash
# Build HTML documentation (includes resource generation)
make html

# Build production documentation with versioning
make prod

# Generate resources only (without building HTML)
make contents

# Clean generated resources only
make clean

# Clean Sphinx build output only
make doc_clean

# Clean plot outputs only
make cleanplt
```

#### Documentation Editing Workflow

**When editing documentation**:

1. **Identify the source file type** - Check if the file you want to edit is a source or generated file
2. **Edit source files only** - Never edit files with extensions like `.fcstm.puml`, `.puml.png`, `.py.txt`, etc.
3. **Regenerate derived files** - After editing source files, run the appropriate build command
4. **Verify changes** - Check that generated files reflect your source changes

**Example workflow for FSM diagrams**:

```bash
# 1. Edit the source FSM DSL file
vim docs/source/tutorials/example.fcstm

# 2. Regenerate PlantUML and images
make -f docs/source/fcstms.mk SOURCE=docs/source build

# 3. Build documentation to see results
cd docs && make html

# 4. View in browser
open build/html/index.html
```

**Example workflow for PlantUML diagrams**:

```bash
# 1. Check if .puml file is generated from .fcstm
ls docs/source/tutorials/example.fcstm  # If exists, edit this instead!

# 2. If no .fcstm exists, edit .puml directly
vim docs/source/tutorials/example.puml

# 3. Regenerate images
make -f docs/source/diagrams.mk SOURCE=docs/source build

# 4. Build documentation
cd docs && make html
```

**Example workflow for demo scripts**:

```bash
# 1. Edit the demo script
vim docs/source/tutorials/example.demo.py

# 2. Regenerate output
make -f docs/source/demos.mk SOURCE=docs/source build

# 3. Build documentation
cd docs && make html
```

#### Common Pitfalls

**DO NOT**:

- Edit `*.fcstm.puml` files - these are generated from `*.fcstm` files
- Edit `*.puml.png` or `*.puml.svg` files - these are generated from `*.puml` or `*.fcstm` files
- Edit `*.gv.png` or `*.gv.svg` files - these are generated from `*.gv` files
- Edit `*.py.txt`, `*.py.err`, `*.py.exitcode` files - these are generated from demo scripts
- Edit `*.result.ipynb` files - these are generated from `*.ipynb` files
- Commit generated files without regenerating them from source

**DO**:

- Edit `*.fcstm` files for FSM state machines
- Edit `*.puml` files only if no corresponding `*.fcstm` file exists
- Edit `*.gv` files for Graphviz diagrams
- Edit `*.demo.py`, `*.plot.py`, `*.demo.sh` files for demos
- Edit `*.ipynb` files for notebooks (with outputs cleared)
- Run `make contents` before committing documentation changes
- Verify that generated files are up-to-date with source files

#### File Extension Reference

**Source files** (edit these):

- `.fcstm` - FSM DSL source
- `.puml` - PlantUML source (only if not generated from `.fcstm`)
- `.gv` - Graphviz DOT source
- `.demo.py`, `.demox.py`, `.plot.py` - Python demo scripts
- `.demo.sh`, `.demox.sh` - Shell demo scripts
- `.ipynb` - Jupyter notebooks
- `.rst`, `.md` - Documentation text

**Generated files** (never edit):

- `.fcstm.puml` - Generated from `.fcstm`
- `.fcstm.puml.png`, `.fcstm.puml.svg` - Generated from `.fcstm.puml`
- `.puml.png`, `.puml.svg` - Generated from `.puml`
- `.gv.png`, `.gv.svg` - Generated from `.gv`
- `.py.txt`, `.py.err`, `.py.exitcode`, `.py.svg` - Generated from demo scripts
- `.sh.txt`, `.sh.err`, `.sh.exitcode` - Generated from shell scripts
- `.result.ipynb` - Generated from `.ipynb`

#### Dependencies

Documentation generation requires:

- `sphinx` and `sphinx-multiversion` - Documentation builder
- `plantumlcli` - PlantUML command-line tool (for diagram generation)
- `pyfcstm` - This package (for `.fcstm` to `.puml` conversion)
- `graphviz` (`dot` command) - Graphviz renderer
- `jupyter` and `nbconvert` - Notebook execution

Install with:

```bash
pip install -r requirements.txt
pip install -r requirements-doc.txt
```

### Multilingual Documentation Support

The documentation system supports multiple languages through a dynamic index file mechanism. Understanding this system
is essential for writing and translating documentation.

#### Language Support Mechanism

The project uses a **language-specific index file pattern** where:

1. **Language-specific index files** are created with the suffix `_<lang>` (e.g., `index_en.rst`, `index_zh.rst`)
2. **Build-time index selection** happens in `docs/source/conf.py`:
    - Reads `READTHEDOCS_LANGUAGE` environment variable (defaults to `'en'`)
    - Copies the appropriate `index_<language>.rst` to `index.rst` before building
    - The copied `index.rst` becomes the entry point for Sphinx
3. **Language detection** normalizes language codes (e.g., `zh-CN`, `zh_CN`, `zh-Hans` all become `zh`)

**Key Configuration in `conf.py`:**

```python
READTHEDOCS_LANGUAGE = os.environ.get('READTHEDOCS_LANGUAGE', 'en')
language = READTHEDOCS_LANGUAGE
if 'zh' in re.split(r'[_-]+', language.lower()):
    language = 'zh'

_source_index = os.path.join(_DOC_PATH, f'index_{language}.rst')
_target_index = os.path.join(_DOC_PATH, 'index.rst')
shutil.copyfile(_source_index, _target_index)
```

#### File Naming Conventions

**Root-Level Index Files** (`docs/source/`):

- `index_en.rst` - English root index (source file)
- `index_zh.rst` - Chinese root index (source file)
- `index.rst` - Generated entry point (copied from `index_<lang>.rst` during build)

**Section-Level Index Files** (e.g., `docs/source/tutorials/installation/`):

- `index.rst` - Default/English version (source file)
- `index_zh.rst` - Chinese version (source file)
- No `index_en.rst` needed if `index.rst` serves as English version

**Content Files** (non-index documentation):

- Most content files have a single language version without suffix
- Language-specific content uses `_<lang>` suffix when multiple versions exist
- API documentation (`api_doc/`) typically has no language variants (code is language-agnostic)

#### Directory Structure Pattern

```
docs/source/
├── index_en.rst              # English root (source)
├── index_zh.rst              # Chinese root (source)
├── index.rst                 # Generated entry point (do not edit directly)
├── tutorials/
│   ├── installation/
│   │   ├── index.rst         # English version (source)
│   │   ├── index_zh.rst      # Chinese version (source)
│   │   ├── install_check.demo.py
│   │   └── cli_check.demo.sh
│   ├── structure/
│   │   ├── index.rst         # English version (source)
│   │   ├── index_zh.rst      # Chinese version (source)
│   │   └── structure.puml
│   ├── dsl/
│   │   └── index.rst         # Single language version
│   └── cli/
│       └── index.rst         # Single language version
└── api_doc/
    ├── config/
    │   └── index.rst         # API docs typically single language
    └── model/
        └── index.rst
```

#### Translation Workflow

**When creating a new documentation section:**

1. **Create English version first** as `index.rst` (or `<section>.rst`)
2. **Create translated versions** with language suffix (e.g., `index_zh.rst`)
3. **Update parent index files** to reference the appropriate language version:

```rst
.. toctree::
    :maxdepth: 2
    :caption: Tutorials

    tutorials/installation/index_zh    # Reference Chinese version
    tutorials/structure/index_zh       # Reference Chinese version
    tutorials/dsl/index                # Reference default (English) version
```

**When translating existing documentation:**

1. **Identify the source file** (usually `index.rst` or `<section>.rst`)
2. **Create language-specific copy** with `_<lang>` suffix (e.g., `index_zh.rst`)
3. **Translate content** while preserving:
    - ReStructuredText directives and formatting
    - File references (e.g., `.. literalinclude:: install_check.demo.py`)
    - Image references (e.g., `.. figure:: structure.puml.svg`)
    - Code blocks and examples
4. **Update parent index** to reference the new translation
5. **Verify shared resources** (demo scripts, images, diagrams) work for both languages

#### Language-Specific Index References

Parent index files must reference the correct language version of child sections:

**English root index** (`index_en.rst`):

```rst
.. toctree::
    :maxdepth: 2

    tutorials/installation/index       # English version
    tutorials/structure/index          # English version
```

**Chinese root index** (`index_zh.rst`):

```rst
.. toctree::
    :maxdepth: 2

    tutorials/installation/index_zh    # Chinese version
    tutorials/structure/index_zh       # Chinese version
```

#### Best Practices

**DO**:

- Create `index_en.rst` and `index_zh.rst` at the root level (`docs/source/`)
- Use `index.rst` as the default English version for subsections
- Add `index_zh.rst` for Chinese translations of subsections
- Keep shared resources (images, demos, code) language-agnostic
- Update parent index files to reference the correct language version
- Preserve all ReStructuredText formatting and directives during translation
- Test both language builds locally before committing

**DO NOT**:

- Edit `docs/source/index.rst` directly (it's generated during build)
- Create `index_en.rst` for subsections (use `index.rst` as English default)
- Duplicate shared resources (images, demos) for each language
- Translate code examples or API documentation (keep language-agnostic)
- Forget to update parent index files after adding translations

#### Building Documentation for Specific Languages

**Local builds** (defaults to English):

```bash
cd docs
make html
```

**Build for specific language**:

```bash
cd docs
READTHEDOCS_LANGUAGE=zh make html
```

**Production builds** (ReadTheDocs):

- ReadTheDocs automatically sets `READTHEDOCS_LANGUAGE` based on project configuration
- Each language version is built separately with the appropriate environment variable

#### Translation Checklist

When translating a documentation section:

- [ ] Create `index_zh.rst` (or `<section>_zh.rst`) with translated content
- [ ] Preserve all ReStructuredText directives (`:maxdepth:`, `.. literalinclude::`, etc.)
- [ ] Keep file references unchanged (demo scripts, images work for all languages)
- [ ] Update parent index file to reference `index_zh` for Chinese builds
- [ ] Verify shared resources (images, diagrams, demos) are language-agnostic
- [ ] Test build with `READTHEDOCS_LANGUAGE=zh make html`
- [ ] Check that all links and references work correctly
- [ ] Ensure consistent terminology across translated sections
