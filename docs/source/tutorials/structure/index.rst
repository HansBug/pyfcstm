Project Structure Guide
====================================================================================================

Overview
----------------------------------------------------------------------------------------------------

PyFCSTM is a Python framework for parsing Finite State Machine (FSM) Domain-Specific Language (DSL) and generating executable code in multiple target languages. The framework implements a complete pipeline from DSL text to executable code through a three-stage architecture: **DSL Parsing → State Machine Modeling → Code Generation**.

The project follows a layered modular design that separates concerns and enables extensibility for new target languages and template formats.

Architecture Layers
----------------------------------------------------------------------------------------------------

The framework is organized into four distinct architectural layers:

**Foundation Layer** (``pyfcstm.utils``, ``pyfcstm.config``)
    Provides cross-cutting utilities and project metadata used by all other layers.

**Core Layer** (``pyfcstm.dsl``, ``pyfcstm.model``)
    Implements DSL parsing and state machine modeling - the heart of the framework.

**Application Layer** (``pyfcstm.render``, ``pyfcstm.entry``)
    Provides code generation engine and command-line interface for end users.

**Extension Layer** (``pyfcstm.template``)
    Reserved for custom template extensions and future expansion.

Module Reference
----------------------------------------------------------------------------------------------------

Foundation Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**pyfcstm.config** - Project Metadata
    - ``meta.py``: Package metadata (version, author, description, title)
    - Provides ``__VERSION__``, ``__TITLE__``, ``__AUTHOR__``, ``__DESCRIPTION__``
    - Used by ``setup.py`` for package distribution

**pyfcstm.utils** - Utility Functions
    - ``validate.py``: Validation framework with ``IValidatable`` base class and ``ModelValidationError``
    - ``text.py``: String normalization (``normalize()``, ``to_identifier()``) for identifier generation
    - ``safe.py``: Safe sequence identifier generation (``sequence_safe()``)
    - ``doc.py``: Multiline comment formatting (``format_multiline_comment()``)
    - ``binary.py``: Binary file detection utilities
    - ``decode.py``: Auto-decoding with ``auto_decode()`` for various encodings
    - ``jinja2.py``: Jinja2 environment utilities (``add_builtins_to_env()``, ``add_settings_for_env()``)
    - ``json.py``: JSON operation interface with ``IJsonOp`` for serialization

Core Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**pyfcstm.dsl** - DSL Parsing Pipeline
    Converts DSL text into Abstract Syntax Tree (AST) nodes using ANTLR4.

    - ``parse.py``: Entry point with ``parse_with_grammar_entry()`` for parsing DSL code strings
    - ``listener.py``: ANTLR listener (``GrammarParseListener``) that walks parse tree and constructs AST nodes
    - ``node.py``: AST node definitions (dataclasses) for states, transitions, operations, expressions
    - ``error.py``: DSL parsing error handling (``GrammarParseError``, ``SyntaxFailError``)
    - ``grammar/Grammar.g4``: ANTLR4 grammar defining lexer and parser rules for FSM DSL syntax
    - ``grammar/GrammarLexer.py``, ``grammar/GrammarParser.py``, ``grammar/GrammarListener.py``: Auto-generated ANTLR4 code

    **Key Concepts:**
        - Supports hierarchical state definitions with nested composite states
        - Expression grammar includes numeric operations, bitwise operations, conditionals, function calls
        - Each AST node has methods for exporting back to DSL or PlantUML format

**pyfcstm.model** - State Machine Modeling
    Converts AST nodes into structured, queryable state machine models.

    - ``model.py``: Core state machine model classes
        - ``StateMachine``: Root container with variables, states, and global events
        - ``State``: Represents states with parent/child relationships, lifecycle actions (enter/during/exit), transitions
        - ``Transition``: State transitions with source, target, event, guard conditions, effects
        - ``Event``: Named events with scoping (local ``::`` vs global ``:`` or ``/``)
        - ``Operation``: Variable assignments executed during lifecycle actions or transition effects
        - ``VarDefine``: Variable definitions with type (int/float) and initial values
        - ``OnStage``/``OnAspect``: Lifecycle action containers for enter/during/exit behaviors
    - ``expr.py``: Expression system for variables, conditions, and effects
        - Supports literals, variables, unary/binary operators, bitwise operations, function calls
        - Conditional expressions with guards for transitions
        - Expression tree structure renderable to different target languages
    - ``base.py``: Base classes ``AstExportable`` and ``PlantUMLExportable`` for model components

    **Key Methods:**
        - ``walk_states()``: Traverse state hierarchy
        - ``find_state()``: Lookup states by name
        - Export capabilities for DSL and PlantUML formats

Application Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**pyfcstm.render** - Code Generation Engine
    Transforms state machine models into target code using Jinja2 templates.

    - ``render.py``: Main ``StateMachineCodeRenderer`` class
        - Loads template directory and ``config.yaml`` configuration
        - Processes ``.j2`` Jinja2 templates with state machine model as context
        - Copies static files directly to output directory
        - Supports file ignoring via gitignore-style patterns
    - ``env.py``: Jinja2 environment setup and configuration
        - Creates sandboxed Jinja2 environment with custom globals, filters, tests
        - Configures template loader and rendering options
    - ``expr.py``: Expression rendering for different target languages
        - ``create_expr_render_template()``: Creates language-specific expression renderers
        - Supports multiple expression styles: ``dsl``, ``c``, ``cpp``, ``python``
        - Converts DSL expressions to target language syntax (e.g., ``&&`` to ``and`` for Python)
        - Available as ``expr_render`` filter in templates: ``{{ expr | expr_render(style='c') }}``
    - ``func.py``: Custom Jinja2 filters and functions
        - ``process_item_to_object()``: Converts config items to Python objects (imports, templates, values)
        - Supports importing external Python functions into template context

    **Template System:**
        - Template directories must contain ``config.yaml`` defining ``expr_styles``, ``globals``, ``filters``, ``ignores``
        - ``.j2`` files have access to state machine model via ``model`` variable
        - Static files are copied directly preserving directory structure

**pyfcstm.entry** - Command-Line Interface
    Provides user-facing commands for DSL processing.

    - ``cli.py``: CLI implementation using Click framework
        - Main entry point ``pyfcstmcli()`` registered as console script
        - Subcommand aggregation and argument parsing
    - ``dispatch.py``: Command dispatching logic and version information
    - ``plantuml.py``: PlantUML diagram generation from state machine models
        - Converts DSL to ``.puml`` format for visualization
    - ``generate.py``: Template-based code generation
        - Orchestrates parsing DSL, building model, and rendering with templates
    - ``base.py``: CLI base functionality and exception handling

Extension Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**pyfcstm.template** - Template Extensions
    Reserved module for custom template extensions and future expansion.

Architecture Diagram
----------------------------------------------------------------------------------------------------

The following diagram illustrates the module relationships and data flow through the framework:

.. figure:: structure.puml.svg
   :width: 100%
   :align: center
   :alt: PyFCSTM Architecture Diagram

   PyFCSTM layered architecture showing module dependencies and data flow

Processing Pipeline
----------------------------------------------------------------------------------------------------

The framework processes FSM definitions through a three-stage pipeline:

**Stage 1: DSL Parsing** (``pyfcstm.dsl``)
    1. User provides DSL code as text (from ``.fcstm`` files)
    2. ANTLR4 parser tokenizes and parses according to ``Grammar.g4`` rules
    3. ``GrammarParseListener`` walks parse tree and constructs AST nodes
    4. Output: AST node tree (``node.py`` dataclasses)

**Stage 2: Model Construction** (``pyfcstm.model``)
    1. AST nodes are converted to state machine model objects
    2. Hierarchical state relationships are established (parent/child)
    3. Transitions, events, and expressions are linked to states
    4. Model validation ensures structural integrity
    5. Output: Queryable ``StateMachine`` object with ``State``, ``Transition``, ``Event`` instances

**Stage 3: Code Generation** (``pyfcstm.render``)
    1. Template directory is loaded with ``config.yaml`` configuration
    2. Jinja2 environment is configured with custom filters and expression renderers
    3. Templates receive ``model`` object as context
    4. Expression rendering converts DSL expressions to target language syntax
    5. Output: Generated code files in target language

User Interaction Flow
----------------------------------------------------------------------------------------------------

Users interact with the framework through CLI commands (``pyfcstm.entry``):

**PlantUML Generation**::

    pyfcstm plantuml -i input.fcstm -o output.puml

    Flow: DSL → Parser → Model → PlantUML Exporter → .puml file

**Code Generation**::

    pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/

    Flow: DSL → Parser → Model → Template Renderer → Generated code files

Dependency Relationships
----------------------------------------------------------------------------------------------------

The layered architecture enforces clear dependency rules:

- **Foundation Layer** has no dependencies on other layers
- **Core Layer** depends only on Foundation Layer
- **Application Layer** depends on Core and Foundation Layers
- **Extension Layer** depends on Application, Core, and Foundation Layers

This design ensures:

- **Modularity**: Each layer has well-defined responsibilities
- **Testability**: Lower layers can be tested independently
- **Extensibility**: New target languages can be added via templates without modifying core logic
- **Maintainability**: Changes in upper layers don't affect lower layers

Key Design Patterns
----------------------------------------------------------------------------------------------------

**Visitor Pattern** (``pyfcstm.dsl.listener``)
    ANTLR listener walks parse tree and constructs AST nodes

**Template Method Pattern** (``pyfcstm.model.base``)
    Base classes define export interfaces implemented by model classes

**Strategy Pattern** (``pyfcstm.render.expr``)
    Expression rendering strategies for different target languages

**Facade Pattern** (``pyfcstm.entry``)
    CLI provides simplified interface to complex parsing and rendering subsystems
