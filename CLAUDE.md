# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pyfcstm** is a Python framework for parsing Finite State Machine (FSM) Domain-Specific Language (DSL) and generating
executable code in multiple target languages. It focuses on modeling Hierarchical State Machines (Harel Statecharts)
with a Jinja2-based templated code generation system.

## Common Commands

### Testing

```bash
make unittest                                        # Run all tests
make unittest RANGE_DIR=./config                     # Specific directory
make unittest COV_TYPES="xml term-missing"           # With coverage types
make unittest MIN_COVERAGE=80                        # With minimum coverage
make unittest WORKERS=4                              # With parallel workers

# Run a single test file or function directly:
pytest test/simulate/test_runtime.py -v
pytest test/simulate/test_runtime.py::TestClassName::test_method -v
```

### Building and Packaging

```bash
make package    # Build package (sdist and wheel)
make build      # Build standalone executable with PyInstaller
make test_cli   # Test CLI executable
make clean      # Clean build artifacts
```

### Documentation

```bash
make docs                        # Build documentation locally (auto-detects language)
make docs_en / make docs_zh      # Build for specific language
make pdocs                       # Production documentation with versioning
make rst_auto                    # Generate RST from Python source files
make rst_auto RANGE_DIR=model    # Generate RST for specific directory
make docs_auto                   # Generate Python docstrings (requires hbllmutils)
make todos_auto                  # Complete TODO comments (requires hbllmutils)
make tests_auto                  # Generate unit tests (requires hbllmutils)
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

### ANTLR Grammar Development

```bash
make antlr        # Download ANTLR jar and setup (requires Java)
make antlr_build  # Regenerate parser from grammar file after modifying Grammar.g4
```

### Sample Test Generation

```bash
make sample / make sample_clean  # Generate/clean test files from sample DSL files
```

### VSCode Extension

```bash
make vscode / make vscode_clean  # Build/clean VSCode extension package
```

### Logo Generation

```bash
make logos / make logos_clean    # Generate/clean PNG logos from SVG sources
```

### CLI Usage

```bash
pyfcstm plantuml -i input.fcstm -o output.puml
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/ --clear
pyfcstm simulate -i input.fcstm                                      # Interactive mode
pyfcstm simulate -i input.fcstm -e "cycle; cycle Start; current"     # Batch mode
pyfcstm simulate -i input.fcstm -e "init System.Active counter=10; cycle 5"  # Hot start batch

# Interactive hot start:
# > init System.Active counter=10 flag=1
# > cycle
```

## Architecture Overview

### Core Components

**DSL Parsing Pipeline** (`pyfcstm/dsl/`)

- `grammar/Grammar.g4`: ANTLR4 grammar for states, transitions, events, expressions; hierarchical state definitions
- `parse.py`: Entry point `parse_with_grammar_entry()` for parsing DSL code strings
- `listener.py`: ANTLR listener constructing AST nodes; visitor pattern for each grammar rule
- `node.py`: AST node dataclasses with DSL/PlantUML export methods
- `error.py`: DSL parsing error handling with detailed error messages

**Model Layer** (`pyfcstm/model/`)

- `model.py`: Core classes: `StateMachine`, `State`, `Transition`, `Event`, `Operation`, `VarDefine`, `OnStage`/`OnAspect`
- `expr.py`: Expression system supporting literals, variables, unary/binary operators, bitwise ops, function calls
- `base.py`: Base classes `AstExportable` and `PlantUMLExportable`
- Model methods: `walk_states()` for traversal, `find_state()` for lookups, export capabilities

**Rendering Engine** (`pyfcstm/render/`)

- `render.py`: `StateMachineCodeRenderer` - loads templates, processes `.j2` files, copies static files, gitignore-style ignores
- `env.py`: Jinja2 sandboxed environment with custom globals, filters, and tests
- `expr.py`: Expression rendering for `dsl`, `c`, `cpp`, `python` styles; `{{ expr | expr_render(style='c') }}`
- `func.py`: `process_item_to_object()` converts config items to Python objects (imports, templates, values)

**Simulation Runtime** (`pyfcstm/simulate/`)

- `runtime.py`: `SimulationRuntime` for cycle-based execution
  - Execution stack of active states from root to leaf; speculative validation before transitions
  - **Hot Start**: builds frame stack directly to target state without enter actions
    - Leaf states use `'active'` mode; Composite states use `'init_wait'` mode
    - `initial_vars` must provide all variables; DFS finds stoppable paths
    - Safety limits: 1000 steps max, 64 stack depth max
- `context.py`: Read-only execution context for abstract handlers
- `decorators.py`: `@abstract_handler` decorator for handler registration

**Constraint Solver** (`pyfcstm/solver/`)

- `expr.py`: Translates model expressions into Z3 constraint expressions
- `solve.py`: Z3-based constraint solving for guard reachability analysis
- `operation.py`: Converts state machine operations into solver constraints
- Uses `z3-solver` library; enables static analysis of transition guard satisfiability

**Entry Points** (`pyfcstm/entry/`)

- `cli.py`: Click-based CLI; `pyfcstmcli()` registered as console script
- `plantuml.py`: PlantUML diagram generation from state machine models
- `generate.py`: Orchestrates parsing DSL, building model, and rendering with templates
- `dispatch.py`: Command dispatching logic for CLI subcommands
- `simulate/`: Interactive simulation REPL (sub-package) with `repl.py`, `commands.py`, `completer.py`, `display.py`, `batch.py`, `logging.py`

**Configuration** (`pyfcstm/config/`)

- `meta.py`: `__VERSION__`, `__TITLE__`, `__DESCRIPTION__`, `__AUTHOR__`, `__AUTHOR_EMAIL__`

**Utilities** (`pyfcstm/utils/`)

- `validate.py`: `IValidatable`, `ValidationError`, `ModelValidationError`
- `text.py`: `normalize()`, `to_identifier()` - converts to `[0-9a-zA-Z_]+` via `unidecode`
- `doc.py`: `format_multiline_comment()` - cleans `/* */` ANTLR4 comments
- `safe.py`: `sequence_safe()` - underscore-separated identifier conversion
- `binary.py`, `decode.py`: Binary detection, `auto_decode()` for encoding handling
- `jinja2.py`: `add_builtins_to_env()`, `add_settings_for_env()`
- `json.py`: `IJsonOp` for serialization

### Key Architectural Patterns

**Three-Stage Pipeline**: DSL Text → AST Nodes → State Machine Model → Generated Code

**Template System**: Jinja2 with custom filters and expression styles defined in `config.yaml`. `expr_styles` enables
cross-language expression rendering (DSL expressions rendered as C, Python, etc.).

**Hierarchical State Machines**: Nested states with lifecycle actions (`enter`, `during`, `exit`) and
aspect-oriented programming via `>> during before/after` actions.

**Event Scoping**: Local (`::` source state), chain (`:` parent state), absolute (`/` root state).

## DSL Language Reference

The pyfcstm DSL (`.fcstm` files) defines hierarchical finite state machines combining state definitions, transitions,
events, and expressions.

### Variable Definitions

Variables must be defined at the top of the file before any state definitions:

```
def int counter = 0;
def float temperature = 25.5;
def int flags = 0xFF;           // Hexadecimal literals supported
def int mask = 0b1010;          // Binary literals supported
```

Supported types: `int`, `float`

### State Definitions

```
state Idle;                              // Simple leaf state
state Running named "System Running";    // Named leaf state
pseudo state SpecialState;               // Skips ancestor >> during actions

state Active {                           // Composite state
    state Processing;
    state Waiting;
    [*] -> Processing;                   // Initial transition
    Processing -> Waiting :: Done;
}
```

### Transitions

```
StateA -> StateB;                              // Simple transition
StateA -> StateB :: EventName;                 // Local event (source-scoped)
StateA -> StateB : ChainEvent;                 // Chain event (parent-scoped)
StateA -> StateB : /GlobalEvent;               // Absolute event (root-scoped)
[*] -> InitialState;                           // Entry transition
FinalState -> [*];                             // Exit transition
Idle -> Active : if [counter >= 10];           // Guard condition
Idle -> Running effect { counter = 0; }        // With effect block
StateA -> StateB : if [x > 0] effect { counter = counter + 1; }  // Combined
```

**Forced Transitions** (syntactic sugar expanding to multiple normal transitions):

```
!ErrorState -> [*] :: FatalError;     // Expands from ErrorState
!Running -> SafeMode :: Emergency;    // Expands from Running and all substates
!* -> ErrorHandler :: GlobalError;    // Expands from ALL substates in current scope

// !* expansion example:
// state System {
//   !* -> ErrorHandler :: CriticalError;
//   state Running { state Processing; state Waiting; }
//   state Idle;
// }
// Expands to: Running -> ErrorHandler; Idle -> ErrorHandler;
// And inside Running: Processing -> [*]; Waiting -> [*];
// All share the SAME CriticalError event object
```

Key rules: Cannot have effect blocks; all expanded transitions share the same event object; propagates recursively.

### Events

```
event EventName;                            // Simple event definition
event ErrorOccurred named "Error Occurred"; // With display name for visualization
```

**Event Scoping**:
- `::` (local) - scoped to source state: `Parent.StateA.EventName`; each source state has unique event
- `:` (chain) - scoped to parent state: `Parent.EventName`; siblings in same scope share the event
- `/` (absolute) - scoped to root state: `Root.EventName`; shared globally across all states

**Event Resolution Example**:
```
state System {
    state ModuleA {
        state A1;
        state A2;
        [*] -> A1;
        A1 -> A2 :: E;        // System.ModuleA.A1.E  (unique to A1)
        A1 -> A2 : E;         // System.ModuleA.E     (shared in ModuleA scope)
        A1 -> A2 : /E;        // System.E             (global)
    }
    state ModuleB {
        state B1;
        state B2;
        [*] -> B1;
        B1 -> B2 :: E;        // System.ModuleB.B1.E  (different from A1's)
        B1 -> B2 : E;         // System.ModuleB.E     (different from ModuleA's)
        B1 -> B2 : /E;        // System.E             (SAME as ModuleA's)
    }
}
```

### Lifecycle Actions

```
state Active {
    enter { counter = 0; flags = 0xFF; }      // On entering state
    during { counter = counter + 1; }          // Each cycle while active
    exit { counter = 0; }                      // On leaving state

    enter abstract InitializeHardware;                    // Abstract (implement in generated code)
    enter abstract SetupSystem /* doc comment */;         // Abstract with documentation
    enter UserInit { counter = 0; }                       // Named action (for ref reuse)
    enter ref StateA.UserInit;                            // Reference to named action
    exit ref /GlobalCleanup;                              // Reference from root
}

state Parent {
    during before { /* runs ONLY on [*]->Child entry */ } // Composite: entry trigger only
    during after  { /* runs ONLY on Child->[*] exit */ }  // Composite: exit trigger only
    >> during before { /* aspect: all descendants */ }    // All descendant leaf states
    >> during after  { /* aspect: all descendants */ }    // All descendant leaf states
}
```

`ref` resolves to a previously named lifecycle action (not a state or event reference).
Relative paths from current state; `/` from root. Use `ref` for sharing behavior; `abstract` for generated code.

### Expression System

**IMPORTANT**: Arithmetic (`num_expression`) and logical (`cond_expression`) are strictly separated. You cannot mix
them freely. Assignments require arithmetic; guards require boolean; comparison operators bridge the two.

```
counter = 10 + 5;                              // Arithmetic: +, -, *, /, **, %
flags = 0xFF & 0x0F;                           // Bitwise: &, |, ^, <<, >>
result = (x > 10) ? 1 : 0;                    // Ternary: only way to convert bool→arithmetic
StateA -> StateB : if [counter >= 10 && temp < 30];   // Guards: >=, <, ==, !=, &&, ||, !
StateA -> StateB : if [flag1 or flag2];               // 'and', 'or', 'not' keywords also valid
result = sin(angle);                           // Function calls

// ERROR: result = (x > 10);    // Cannot assign boolean to variable
// ERROR: if [counter];         // Cannot use arithmetic as condition
// CORRECT: result = (x > 10) ? 1 : 0;
// CORRECT: StateA -> StateB : if [counter > 0];
```

### Complete Example

```
def int counter = 0;
def int error_count = 0;
def float temperature = 25.0;

state System {
    >> during before { counter = counter + 1; }
    >> during before abstract GlobalMonitor;

    [*] -> Initializing;
    !* -> Error :: FatalError;

    state Initializing {
        enter { counter = 0; error_count = 0; }
        enter abstract HardwareInit /* Initialize hardware peripherals */
        exit { temperature = 25.0; }
    }

    state Running {
        during before abstract PreProcess;
        during before { temperature = temperature + 0.1; }
        during after { }

        state Active { during { counter = counter + 1; } }
        state Idle;

        [*] -> Active;
        Active -> Idle :: Pause;
        Idle -> Active :: Resume;
    }

    state Error { enter { error_count = error_count + 1; } }

    Initializing -> Running : if [counter >= 10] effect { counter = 0; };
    Running -> Error : if [temperature > 100.0];
    Error -> [*] : if [error_count > 5];
}
```

### Key DSL Concepts

**Execution Flow Summary**:

- **Entry** (from parent): `State.enter` → `State.during before` → `Child.enter`
- **During** (each cycle): Aspect `>> during before` → Leaf `during` → Aspect `>> during after`
- **Exit** (to parent): `Child.exit` → `State.during after` → `State.exit`
- **Child-to-Child Transition**: `Child1.exit` → (transition effect) → `Child2.enter` (no `during before/after`)

**Aspect Actions (`>> during before/after`)**:
- Apply to **all descendant leaf states** every cycle
- Root→leaf order for `before`, leaf→root for `after`
- Enable cross-cutting concerns (logging, monitoring, validation)
- Not applied to `pseudo state`

**Composite State Actions (`during before/after` without `>>`)**:
- `during before`: ONLY when entering composite from parent (`[*] → Child`)
  - Executes AFTER composite `enter`, BEFORE child `enter`
  - **NOT triggered** during child-to-child transitions (`Child1 → Child2`)
- `during after`: ONLY when exiting composite to parent (`Child → [*]`)
  - Executes AFTER child `exit`, BEFORE composite `exit`
  - **NOT triggered** during child-to-child transitions

**Leaf State `during`**: Executes every cycle, sandwiched between ancestor aspect actions.

**Event Namespace Resolution**: `::` creates source-state-scoped events; `:` or `/` references parent/root namespaces.

**Detailed Execution Order Scenarios** (for `System.SubSystem.Active` in a composite machine):

**Scenario 1: Initial Entry** (`[*] → SubSystem → [*] → Active`):
- Entry Phase: `System.enter` → `SubSystem.enter` → `SubSystem.during before` (**triggered**) → `Active.enter`
- During Phase (each cycle): `System >> during before` → `Active.during` → `System >> during after`
- Note: `SubSystem.during before/after` do NOT execute during the `during` phase

**Scenario 2: Child-to-Child Transition** (`Active → Idle :: Pause`):
- Sequence: `Active.exit` → (transition effect) → `Idle.enter`
- **CRITICAL**: `SubSystem.during before/after` are NOT triggered during child-to-child transitions

**Scenario 3: Exit from Composite State** (`Idle → [*] :: Stop`):
- Exit Phase: `Idle.exit` → `SubSystem.during after` (**triggered**) → `SubSystem.exit` → `System.exit`

## Python Docstring Style Guide

Use **reStructuredText (reST)** format exclusively, following PEP 257 and Sphinx standards.

### Core Principles

1. **Format**: reST markup exclusively
2. **Completeness**: Document all public APIs (modules, classes, functions, methods)
3. **Clarity**: Explain "why" and "what", not just "how"
4. **Cross-references**: Use reST roles (`:class:`, `:func:`, `:mod:`)
5. **Examples**: Include practical usage examples for public APIs
6. **Tone**: Professional, clear, technical but accessible

### Docstring Templates

**Module**:
```python
"""
Brief one-line description.

Longer description of purpose, main capabilities, and fit in the larger system.

The module contains:
* :class:`ClassName` - Brief description
* :func:`function_name` - Brief description

.. note::
   Important caveats about usage or requirements.

Example::

    >>> from module import something
    >>> result = something()
    >>> result
    expected_output
"""
```

**Class**:
```python
class ClassName:
    """
    Brief one-line description.

    Longer explanation of purpose, responsibilities, and usage patterns.

    :param param_name: Description of constructor parameter
    :type param_name: ParamType
    :param optional_param: Description, defaults to ``default_value``
    :type optional_param: ParamType, optional

    :ivar instance_var: Description of instance variable
    :vartype instance_var: VarType
    :cvar class_var: Description of class variable
    :type class_var: ClassVarType

    Example::

        >>> obj = ClassName(param_name=value)
        >>> obj.method()
        expected_result
    """
```

**Function/Method**:
```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    Brief one-line description.

    Longer explanation of behavior, algorithm, or important details.

    :param param1: Description of the first parameter
    :type param1: Type1
    :param param2: Description, defaults to ``default``
    :type param2: Type2, optional
    :return: Description of what is returned
    :rtype: ReturnType
    :raises ExceptionType: Description of when raised
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.

    Example::

        >>> result = function_name(arg1, arg2)
        >>> result
        expected_output
    """
```

**Dataclass**:
```python
@dataclass
class DataClassName:
    """
    Brief description of what this dataclass represents.

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

### Parameter, Return, and Exception Patterns

```python
:param param_name: Description                           # Required parameter
:type param_name: type_annotation
:param param_name: Description, defaults to ``value``   # Optional parameter
:type param_name: type_annotation, optional
:return: Description of what is returned
:rtype: ReturnType
:return: ``None``.                                       # For None-returning functions
:rtype: None
:raises ExceptionType: When this exception is raised
:raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
```

### Cross-References and Markup

- `:class:`ClassName``, `:func:`function_name``, `:meth:`Class.method_name``
- `:mod:`module.name``, `:exc:`ExceptionType``, `:data:`variable_name``, `:attr:`attribute_name``
- Instance variables: `:ivar:` / `:vartype:`; Class variables: `:cvar:` / `:type:`
- Inline code: double backticks `` ``value`` `` (not single backticks)

### Examples in Docstrings

```python
Example::

    >>> from pyfcstm.utils.text import normalize
    >>> normalize("Hello World!")
    'Hello_World'
    >>> normalize("test-case")
    'test_case'
```

For CLI examples, use `$` prefix without `>>>`. For FCSTM DSL in Sphinx docs, use `.. code-block:: fcstm`.
For including external FCSTM files: `.. literalinclude:: example.fcstm` with `:language: fcstm`.

**Real example from codebase** (`pyfcstm/entry/generate.py`):
```python
def generate(input_code_file: str, template_dir: str, output_dir: str, clear_directory: bool) -> None:
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
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises IOError: If reading the input file or writing output files fails.

    Example::

        $ pyfcstm generate -i ./machine.dsl -t ./templates -o ./out --clear
    """
```

### Special Directives

```python
.. note::
   Important information or caveats about usage.
.. warning::
   Critical warnings about potential issues or dangers.
```

### Checklist

- [ ] Brief one-line summary at the top
- [ ] Longer explanation for non-trivial functions/classes
- [ ] All params documented with `:param:` and `:type:`
- [ ] Return value with `:return:` and `:rtype:`
- [ ] All exceptions with `:raises:`
- [ ] Cross-references use reST roles (`:class:`, `:func:`, etc.)
- [ ] Examples for public APIs
- [ ] Inline code uses double backticks
- [ ] Optional params marked with `, optional`; defaults shown in description

### Anti-Patterns

**DON'T**: Google/NumPy style; omit types (always include `:type:` and `:rtype:`); single backticks for inline code;
vague descriptions ("Does something"); bare class/function names without reST roles; volatile implementation details.

**DO**: reST format consistently; explain "why" and "what"; use cross-references; include practical examples;
update docstrings when code changes.

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

**State Machine Domain Concepts**: Use domain-specific terminology consistently: states, transitions, events,
lifecycle actions, guards, effects, composite states, leaf states, aspect actions.

**Template and Rendering Context**: Document Jinja2 template integration and expression rendering styles when relevant.

**Real example from codebase** (`pyfcstm/render/render.py`):
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
    :ivar env: Jinja2 environment used for rendering
    :vartype env: jinja2.Environment

    Example::

        >>> renderer = StateMachineCodeRenderer('./templates')
        >>> renderer.render(my_state_machine, './output', clear_previous_directory=True)
    """
```

## Development Notes

### LLM-Based Documentation Generation

```bash
# RST generation (no additional setup needed)
make rst_auto                    # Generate RST for all Python files
make rst_auto RANGE_DIR=model    # Specific directory
python auto_rst_top_index.py -i pyfcstm -o docs/source/api_doc.rst

# LLM features (requires: pip install hbllmutils + configure .llmconfig.yaml)
make docs_auto    # Generate Python docstrings
make todos_auto   # Complete TODO comments
make tests_auto   # Generate unit tests
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

Common `AUTO_OPTIONS`: `--param max_tokens=N`, `--model-name MODEL`, `--no-ignore-module pyfcstm`, `--timeout SECONDS`.

Key file: `.llmconfig.yaml` (gitignored, contains API credentials; copy from `.llmconfig.yaml.example`).

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

#### Best Practices

1. **Start with RST Generation** - Generate RST files first to establish structure
2. **Review LLM Output** - Always review generated docstrings and code before committing
3. **Incremental Updates** - Use `RANGE_DIR` to target specific modules
4. **Version Control** - Commit generated documentation separately from code changes
5. **API Token Security** - Never commit `.llmconfig.yaml` to git

See `LLM_DOCS_README.md` for detailed documentation.

### ANTLR Grammar Modifications

When modifying `pyfcstm/dsl/grammar/Grammar.g4`:

1. Ensure Java is installed
2. `make antlr` - download ANTLR jar (only needed once)
3. `make antlr_build` - regenerate parser code
4. Update `listener.py` and `node.py` if grammar structure changes
5. Update syntax highlighting:
   - `pyfcstm/highlight/pygments_lexer.py` (Pygments lexer, reference implementation)
   - `editors/fcstm.tmLanguage.json` (TextMate grammar)
6. `python editors/validate.py` - verify all 20+ checkpoints pass (100% required)

**Operator Ordering**: Multi-character operators before single-character ones:
- `**` before `*`; `<<` before `<`; `<=`, `>=`, `==`, `!=` before `<`, `>`, `!`; `&&`, `||` before `!`

**Adding New Keywords**: Grammar.g4 → `make antlr_build` → update `pygments_lexer.py` (appropriate `words()` group)
→ update `fcstm.tmLanguage.json` (keywords repository section) → `python editors/validate.py`.

### Template Development

Template directories must contain:
- `config.yaml`: Defines `expr_styles`, `globals`, `filters`, `ignores`
- `.j2` files: Jinja2 templates with state machine model as context
- Static files: Copied directly to output (preserve directory structure)

Key template objects:
- `model`, `model.walk_states()`
- `state.name`, `state.is_leaf_state`, `state.transitions`, `state.parent`
- `transition.from_state`, `transition.to_state`, `transition.guard`, `transition.effects`

Use `{{ expr | expr_render(style='c') }}` to render expressions in target language syntax.

### Testing Strategy

- Tests in `test/`; use `@pytest.mark.unittest`
- Shared test utilities and fixtures in `test/testings/`
- Sample DSL files in `test/testfile/sample_codes/` (auto-generate tests via `make sample`)
- Negative cases in `test/testfile/sample_neg_codes/`
- Test timeout: 300 seconds (configured in `pytest.ini`)

### Dependencies

Core (`requirements.txt`): `antlr4-python3-runtime==4.9.3`, `jinja2>=3`, `pyyaml`, `click>=8`, `hbutils>=0.14.0`,
`pathspec`, `z3-solver<=4.15.4` (constraint solver), `prompt_toolkit>=3.0.0` + `rich>=13,<14` (simulation REPL UI),
`pygments>=2.10.0` (syntax highlighting), `unidecode`, `chardet`. Development (`requirements-dev.txt`): `ruff`.

### Documentation Editing

**CRITICAL RULE**: Always edit source files only. Never edit generated files directly—they will be overwritten.

#### Documentation Structure

Files in `docs/source/`:
- `*.rst`/`*.md`: Documentation pages
- `*.mk`: Makefile fragments for resource generation
- `conf.py`: Sphinx configuration
- Subdirectories: `tutorials/`, `information/`, `api_doc/`, etc.

#### File Generation Rules

| Source | Generated |
|--------|-----------|
| `*.fcstm` | `*.fcstm.puml` → `*.fcstm.puml.{png,svg}` |
| `*.puml` | `*.puml.{png,svg}` |
| `*.gv` | `*.gv.{png,svg}` |
| `*.demo.py` | `*.demo.py.txt` |
| `*.demox.py` | `*.demox.py.{txt,err,exitcode}` |
| `*.plot.py` | `*.plot.py.svg` |
| `*.demo.sh` | `*.demo.sh.txt` |
| `*.demox.sh` | `*.demox.sh.{txt,err,exitcode}` |
| `*.ipynb` | `*.result.ipynb` |

#### Build Commands

```bash
# From docs/source/
make -f all.mk build      # Generate all resources (diagrams, demos, notebooks)
make -f all.mk clean      # Clean all generated resources
make -f all.mk cleanplt   # Clean plot outputs only

# From docs/
make html       # Build HTML documentation (includes resource generation)
make contents   # Generate resources only (without building HTML)
make prod       # Production build with versioning
make clean      # Clean generated resources
make doc_clean  # Clean Sphinx build output only
```

#### DO and DO NOT

**DO NOT** edit generated files:
- `*.fcstm.puml`, `*.fcstm.puml.{png,svg}` (from `.fcstm`)
- `*.puml.{png,svg}` (from `.puml`)
- `*.gv.{png,svg}` (from `.gv`)
- `*.py.txt`, `*.py.err`, `*.py.exitcode`, `*.py.svg` (from demo scripts)
- `*.sh.txt`, `*.sh.err`, `*.sh.exitcode` (from shell scripts)
- `*.result.ipynb` (from `.ipynb`)
- `docs/source/index.rst` (generated during build—do not edit directly)

**DO** edit source files:
- `*.fcstm` for FSM state machines
- `*.puml` only if no corresponding `*.fcstm` exists
- `*.gv` for Graphviz diagrams
- `*.demo.py`, `*.demox.py`, `*.plot.py`, `*.demo.sh`, `*.demox.sh` for demos
- `*.ipynb` for notebooks (with outputs cleared)
- `*.rst`, `*.md` for documentation text

Run `make contents` before committing documentation changes.

#### Example Workflow

```bash
# Editing an FSM diagram:
vim docs/source/tutorials/example.fcstm           # Edit source
make -f docs/source/fcstms.mk SOURCE=docs/source build  # Regenerate
cd docs && make html                              # Build docs

# Editing a demo script:
vim docs/source/tutorials/example.demo.py         # Edit source
make -f docs/source/demos.mk SOURCE=docs/source build   # Regenerate output
cd docs && make html                              # Build docs
```

#### Documentation Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-doc.txt
```

Requires: `sphinx`, `sphinx-multiversion`, `plantumlcli`, `graphviz` (`dot`), `jupyter`, `nbconvert`.

### Multilingual Documentation Support

Language selection via `READTHEDOCS_LANGUAGE` env var (default `en`). `docs/source/conf.py` copies
`index_<lang>.rst` → `index.rst` at build time. Language codes normalized (`zh-CN`, `zh_CN` → `zh`).

#### File Naming Conventions

- Root level: `index_en.rst`, `index_zh.rst` (sources); `index.rst` (generated—do not edit directly)
- Subsections: `index.rst` = English default; `index_zh.rst` = Chinese translation
- Shared resources (images, demos, code) should be language-agnostic (no duplication per language)
- API docs (`api_doc/`) typically have no language variants

#### Build for Specific Language

```bash
cd docs && make html                          # English (default)
cd docs && READTHEDOCS_LANGUAGE=zh make html  # Chinese
```

#### Translation Workflow

When creating a new section:
1. Create English version as `index.rst`
2. Create Chinese version as `index_zh.rst`
3. Update parent index files to reference correct language versions:

```rst
.. toctree::
    :maxdepth: 2

    tutorials/installation/index_zh    # Chinese version reference
    tutorials/dsl/index                # English/default version reference
```

When translating: preserve all reST directives, file references, and code blocks; keep images/demos language-agnostic.

#### DO and DO NOT

**DO**:
- Create `index_zh.rst` for Chinese translations of subsections
- Use `index.rst` as English default for subsections
- Update parent index files to reference the correct language versions
- Test both language builds locally before committing

**DO NOT**:
- Edit `docs/source/index.rst` directly (generated at build time)
- Create `index_en.rst` for subsections (use `index.rst` as English default)
- Duplicate shared resources (images, demos) per language
- Translate code examples or API documentation (keep language-agnostic)

#### Translation Checklist

- [ ] Create `index_zh.rst` with translated content
- [ ] Preserve all reST directives (`:maxdepth:`, `.. literalinclude::`, etc.)
- [ ] Keep file references unchanged (images/demos work for all languages)
- [ ] Update parent index to reference `index_zh` for Chinese builds
- [ ] Verify shared resources are language-agnostic
- [ ] Test: `READTHEDOCS_LANGUAGE=zh make html`
- [ ] Check all links and references work correctly
