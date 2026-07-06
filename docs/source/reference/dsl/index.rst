
.. _sec-reference-dsl:

DSL reference
=============

.. contents:: Reference map
   :local:
   :depth: 2

Scope
-----

This is the fact-oriented FCSTM DSL reference. It is checked against the current
split grammar files, especially ``pyfcstm/dsl/grammar/GrammarParser.g4`` and
``pyfcstm/dsl/grammar/GrammarLexer.g4``. Use it for exact forms and boundaries.
Use :doc:`../../tutorials/dsl/index` for a learning path,
:doc:`../../how_to/dsl/index` for task recipes, and
:doc:`../../explanations/dsl_semantics/index` for semantic background.

.. _dsl-syntax-quick-index:

Syntax quick index
------------------

Start here when you need to find the exact form. Examples in this reference are
fragments unless they are introduced as checked files under
``docs/source/tutorials/dsl``. The task guide links each major form to a complete
example and verification command.

.. list-table:: Syntax families
   :header-rows: 1
   :widths: 24 38 38

   * - Family
     - Main forms
     - Details
   * - Program boundary
     - ``def int x = 0;`` / one root ``state``
     - :ref:`dsl-top-level-forms`
   * - States
     - ``state A;`` / ``state A { ... }`` / ``pseudo state P;``
     - :ref:`dsl-state-forms`
   * - Transitions
     - plain, event, guard, guard+effect, combo, forced, entry, exit
     - :ref:`dsl-transition-forms`
   * - Events
     - ``:: Local`` / ``: Chain`` / ``: /RootEvent``
     - :ref:`dsl-events-scopes`
   * - Operation blocks
     - assignment, block-local temporary, ``if`` / ``else if`` / ``else``, empty statement
     - :ref:`dsl-operation-blocks`
   * - Expressions
     - init, numeric, condition, ternary, operator precedence
     - :ref:`dsl-expression-reference`
   * - Lifecycle and aspects
     - ``enter`` / ``during`` / ``exit``; ``abstract``; ``ref``; ``>> during``
     - :ref:`dsl-lifecycle-forms`, :ref:`dsl-aspect-forms`
   * - Imports
     - ``import "path" as Alias`` and mapping block
     - :ref:`dsl-import-forms`
   * - Diagnostics wording
     - target-specific warnings, especially C/C++ deployment-profile risks
     - :ref:`dsl-diagnostics-risk`

.. _dsl-lexical-forms:

Lexical and comment forms
-------------------------

.. list-table:: Lexical forms
   :header-rows: 1

   * - Form
     - Syntax / tokens
     - Notes
   * - Identifier
     - ``[a-zA-Z_][a-zA-Z0-9_]*``
     - Used for variables, states, events, action names, aliases, and path parts.
   * - String
     - Single or double quoted strings
     - Import paths and ``named`` labels use strings; common escape sequences are lexed.
   * - Comments
     - ``/* ... */``, ``// ...``, ``# ...``
     - Multiline comments may become abstract-action documentation in specific lifecycle forms.
   * - Keywords
     - ``def``, ``state``, ``pseudo``, ``event``, ``import``, ``enter``, ``during``, ``exit``, ``abstract``, ``ref``
     - Keywords are reserved by lexer rules.
   * - Compact import tokens
     - selector patterns and target templates
     - Compact forms are tokenized in import-specific lexer modes and are whitespace-sensitive.

.. _dsl-top-level-forms:

Top-level program forms
-----------------------

A normal DSL entry has zero or more persistent variable declarations followed by
one root state:

Fragment::

   def int counter = 0;
   def float threshold = 3.5;

   state Root {
       [*] -> Idle;
       state Idle;
   }

Facts:

* Persistent variable types are ``int`` and ``float``.
* Declarations must appear before the single root ``state``.
* Initializers use ``init_expression``. This subset accepts literals, math
  constants, arithmetic, bitwise operators, and unary math functions, but it
  does not accept runtime variable references or C-style ternary expressions.
* The root may be leaf or composite, but practical models usually use composite
  root state.

.. _dsl-import-preamble-forms:

Import preamble forms
---------------------

The import assembly pipeline also parses a preamble entry point:

.. list-table:: Preamble forms
   :header-rows: 1

   * - Rule
     - Syntax
     - Meaning
   * - ``constant_definition``
     - ``name = init_expression;``
     - Defines a constant-like preamble value for import assembly.
   * - ``initial_assignment``
     - ``name := init_expression;``
     - Provides an initial assignment in the import preamble context.

These forms are not ordinary top-level ``def`` declarations. They exist so
imported modules can expose assembly-time constants or initial values before the
model is rewritten into the host.

.. _dsl-state-forms:

State forms
-----------

.. list-table:: State forms
   :header-rows: 1

   * - Form
     - Syntax
     - Boundary
   * - Leaf state
     - ``state Name;``
     - Stoppable runtime state.
   * - Named leaf state
     - ``state Name named "Label";``
     - Adds display metadata.
   * - Composite state
     - ``state Name { ... }``
     - Owns child declarations; must choose an initial child.
   * - Pseudo state
     - ``pseudo state Name;``
     - Routing helper; should be leaf-like and action-free for combo relay use.
   * - Pseudo composite syntax
     - ``pseudo state Name { ... }``
     - Parser shape exists, but model validation rejects non-leaf pseudo states with ``E_PSEUDO_NOT_LEAF``.

Some path-bearing forms use dotted identifiers through ``chain_id``, for
example event scopes, import mappings, or action references. Transition
``from_state`` and ``to_state`` endpoints are different: they are plain
identifiers resolved in the owning state scope, not dotted paths. To reach a
nested leaf, put the transition inside the composite that owns that leaf, or
transition to the composite and let its initial transition select the child.

.. _dsl-transition-forms:

Transition forms
----------------

.. list-table:: Transition families
   :header-rows: 1

   * - Family
     - Syntax shape
     - Effect allowed?
     - Notes
   * - Initial transition
     - ``[*] -> Target;`` or with entry combo trigger
     - Yes
     - Selects initial child for a composite.
   * - Normal transition
     - ``Source -> Target;``
     - Yes
     - Source and target resolve in owner scope.
   * - Exit transition
     - ``Source -> [*];``
     - Yes
     - Leaves through the composite exit marker.
   * - Event transition
     - ``Source -> Target :: Local;`` or ``: EventPath``
     - Yes
     - Ordinary event form without guard syntax.
   * - Guard transition
     - ``Source -> Target : if [condition];``
     - Yes
     - Guard expression is condition-only.
   * - Guard plus effect
     - ``Source -> Target : if [condition] effect { ... }``
     - Yes
     - Event syntax is not part of this ordinary form.
   * - Combo trigger
     - ``[guard]`` alias or ``Event + [guard]`` terms through combo rules
     - Yes for normal/entry combo expansion
     - Used for explicit event-plus-guard, guard alias, or multiple-term triggers.
   * - Forced transition
     - ``!State -> Target ...;`` or ``!* -> Target ...;``
     - No
     - Expands over selected sources.
   * - Forced exit transition
     - ``!State -> [*] ...;`` or ``!* -> [*] ...;``
     - No
     - Forced form targeting exit marker.

Combo details:

* Local combo uses ``::`` and local event terms.
* Chain/root combo uses ``:`` and ``chain_id`` event terms.
* Entry combo triggers are accepted on initial transitions.
* ``: [condition]`` is the combo guard alias for a single guard trigger;
  ``: if [condition]`` is the ordinary guard spelling.
* Leading guard combo terms such as ``: [enabled] + Start`` are accepted.
* Duplicate event terms and constant guards are diagnostics targets.
* Combo pseudo relay states are generated routing helpers. They must not be
  treated as business states or aspect-action execution points.

Forced transition details:

* ``!State`` expands from a named source state.
* ``!*`` expands from all applicable source states in the owner scope.
* Forced forms can carry one local, chain/root, or guard trigger.
* Forced forms cannot carry combo ``+`` trigger chains.
* Forced forms cannot have ``effect`` blocks; put side effects on explicit normal
  transitions if needed.

.. _dsl-events-scopes:

Events and scopes
-----------------

.. list-table:: Event scope forms
   :header-rows: 1

   * - Form
     - Syntax
     - Meaning
   * - Event declaration
     - ``event Name;`` or ``event Name named "Label";``
     - Declares an event owned by the containing state.
   * - Source-local event
     - ``:: Name``
     - Event in the source state's local namespace.
   * - Chain event
     - ``: Name`` or ``: Parent.Event``
     - Event path relative to an owning scope.
   * - Root event
     - ``: /Name`` or ``: /Path.Event``
     - Absolute event path from root.

``chain_id`` is ``/`` optional followed by one or more dotted identifiers. Use
local events for source-private signals, chain paths for containing protocols,
and root paths for globally owned events.

.. _dsl-operation-blocks:

Operation blocks
----------------

Operation blocks appear in effects and lifecycle bodies.

.. list-table:: Operation statements
   :header-rows: 1

   * - Statement
     - Syntax
     - Notes
   * - Assignment
     - ``name = num_expression;``
     - Updates a persistent variable or introduces a block-local temporary.
   * - Conditional block
     - ``if [condition] { ... } else if [condition] { ... } else { ... }``
     - Conditions use ``cond_expression``.
   * - Empty statement
     - ``;``
     - Accepted as a no-op statement.

A block-local temporary is local to the current operation block and can only be
read after assignment in that block. Persistent variables must be declared in the
top-level ``def`` list.

.. _dsl-expression-reference:

Expression reference
--------------------

.. list-table:: Numeric expression facts
   :header-rows: 1

   * - Category
     - Forms
     - Notes
   * - Literals
     - decimal integer, hexadecimal integer, float
     - Float tokens support decimal/exponent forms.
   * - Constants
     - ``pi``, ``E``, ``tau``
     - Math constants for initializers and numeric expressions.
   * - Variables
     - ``ID``
     - Runtime numeric variable or block-local temporary.
   * - Unary
     - ``+x``, ``-x``
     - Prefix numeric sign.
   * - Power
     - ``x ** y``
     - Right associative.
   * - Multiplicative
     - ``*``, ``/``, ``%``
     - Numeric arithmetic.
   * - Additive
     - ``+``, ``-``
     - Numeric arithmetic.
   * - Shift / bitwise
     - ``<<``, ``>>``, ``&``, ``^``, ``|``
     - Numeric bitwise operators; target warnings may apply for C/C++ profiles.
   * - Function call
     - ``sin(x)``, ``sqrt(x)``, ``abs(x)``, ``sign(x)``, and lexer-listed math functions
     - Unary math functions only.
   * - C-style ternary
     - ``(cond) ? num_expr : num_expr``
     - Condition must be parenthesized before ``?``.

.. list-table:: Condition expression facts
   :header-rows: 1

   * - Category
     - Forms
     - Notes
   * - Boolean literals
     - ``true`` / ``false`` variants
     - Lexer accepts common case variants.
   * - Not
     - ``!cond`` or ``not cond``
     - Prefix condition negation.
   * - Numeric comparison
     - ``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``
     - Bridges numeric expressions into conditions.
   * - Condition equality
     - ``cond == cond``, ``cond != cond``, ``cond iff cond``
     - Condition-level equality and equivalence.
   * - Boolean composition
     - ``&&`` / ``and``, ``||`` / ``or``, ``xor``
     - Do not use ``^`` for boolean xor; ``^`` is numeric bitwise xor.
   * - Implication
     - ``=>`` or ``implies``
     - Right associative; do not use ``->`` as implication.
   * - C-style ternary
     - ``(cond) ? cond : cond``
     - Condition result ternary.

Operator precedence follows the grammar rule order from tight to loose:
parentheses/literals/functions, unary signs, power, multiplicative, additive,
shift, bitwise ``&`` / ``^`` / ``|``, comparisons, condition equality/``iff``,
``and``, ``xor``, ``or``, implication, and ternary forms.

.. _dsl-lifecycle-forms:

Lifecycle forms
---------------

.. list-table:: Lifecycle action forms
   :header-rows: 1

   * - Stage
     - Concrete
     - Named concrete
     - Abstract
     - Doc-comment abstract
     - Ref
   * - ``enter``
     - ``enter { ... }``
     - ``enter Name { ... }``
     - ``enter abstract Name;``
     - ``enter abstract Name? /* doc */``
     - ``enter Name? ref Path;``
   * - ``during``
     - ``during { ... }``
     - ``during Name { ... }``
     - ``during abstract Name;``
     - ``during abstract Name? /* doc */``
     - ``during Name? ref Path;``
   * - ``during before``
     - ``during before { ... }``
     - ``during before Name { ... }``
     - ``during before abstract Name;``
     - ``during before abstract Name? /* doc */``
     - ``during before Name? ref Path;``
   * - ``during after``
     - ``during after { ... }``
     - ``during after Name { ... }``
     - ``during after abstract Name;``
     - ``during after abstract Name? /* doc */``
     - ``during after Name? ref Path;``
   * - ``exit``
     - ``exit { ... }``
     - ``exit Name { ... }``
     - ``exit abstract Name;``
     - ``exit abstract Name? /* doc */``
     - ``exit Name? ref Path;``

A ``ref`` points to a named lifecycle action path, not to a state or event.
Doc-comment abstract forms use the multiline comment as documentation metadata.

.. _dsl-aspect-forms:

Aspect forms
------------

Aspect actions are written with ``>> during before`` or ``>> during after``.
They support the same concrete, named, abstract, doc-comment abstract, and ref
families as lifecycle ``during before/after`` forms.

.. list-table:: Aspect facts
   :header-rows: 1

   * - Form
     - Example shape
     - Boundary
   * - Concrete aspect
     - ``>> during before { ... }``
     - Runs for descendant leaf-state active cycles.
   * - Named aspect
     - ``>> during after Trace { ... }``
     - Gives generated hooks a stable name.
   * - Abstract aspect
     - ``>> during before abstract Trace;``
     - Generated code calls user-provided behavior.
   * - Ref aspect
     - ``>> during after ref Path;``
     - Reuses a named action.
   * - Combo pseudo relay
     - N/A
     - Aspect actions do not execute inside combo pseudo relay chains.

.. _dsl-import-forms:

Import forms
------------

.. list-table:: Import syntax facts
   :header-rows: 1

   * - Form
     - Syntax
     - Notes
   * - Basic import
     - ``import "file.fcstm" as Alias;``
     - Adds imported root as child ``Alias``.
   * - Named import
     - ``import "file.fcstm" as Alias named "Label";``
     - Adds display metadata.
   * - Import block
     - ``import "file.fcstm" as Alias { ... }``
     - Contains mapping statements.
   * - Def fallback selector
     - ``def * -> target;``
     - Fallback variable mapping.
   * - Def set selector
     - ``def {a, b} -> target;``
     - Maps a set of variables.
   * - Def pattern selector
     - ``def sensor_* -> sensor_$0;``
     - Pattern selector is compact and whitespace-sensitive.
   * - Def exact selector
     - ``def value -> renamed;``
     - Maps one variable.
   * - Target template
     - ``ID``, compact template, or ``*``
     - Compact templates may use ``$0`` or ``${0}`` placeholders.
   * - Event mapping
     - ``event Source.Path -> Target.Path;``
     - May include ``named "Label"``.
   * - Directory entry
     - ``import "./dir/main.fcstm" as Subsystem;``
     - Use an explicit file; bare directory import is unsupported.

File resolution, recursive loading, conflict detection, mapping precedence, and
model assembly are implemented after parsing in Python import/model code.

.. _dsl-diagnostics-risk:

Diagnostics and target-risk wording
-----------------------------------

Diagnostics come from syntax parsing, model validation, inspect analyzers, and
optional verification phases. User-facing DSL docs must preserve the target
scope of each diagnostic.

.. list-table:: Diagnostics wording facts
   :header-rows: 1

   * - Area
     - Codes / source
     - Wording rule
   * - Combo expansion
     - ``W_COMBO_*``, ``I_COMBO_PSEUDO_NAME_EXTENDED``, ``E_COMBO_PSEUDO_NAME_COLLISION``
     - Explain pseudo relay purity and name-extension behavior without implying aspects run inside relays.
   * - Pseudo state shape
     - ``E_PSEUDO_NOT_LEAF``
     - Parser shape is not the same as model validity.
   * - Numeric literal / operation risk
     - ``W_NUMERIC_*`` and numeric analyzer
     - Describe as C/C++ deployment-profile risk for ``c``, ``c_poll``, ``cpp``, and ``cpp_poll`` unless another target has its own evidence.
   * - Python generated runtime
     - No generic carry-over from C/C++ warnings
     - Do not claim Python generated code has the same fixed-width or undefined-behavior risk unless a Python-specific diagnostic says so.

Use :doc:`../../reference/diagnostics_codes/index` for code-level wording.

Coverage appendix
-----------------

The next matrix is for maintainers and reviewers. It is intentionally placed
after the user-facing syntax facts so normal readers can look up DSL forms
without first crossing a migration audit table.

.. _dsl-coverage-matrix:

DSL coverage matrix
-------------------

``N/A`` means that the page type intentionally does not own that leaf ability.
Every row still has a reference or explanation landing point.

.. list-table:: DSL capability coverage
   :header-rows: 1
   :widths: 16 13 22 18 18 18 18 24 14

   * - feature_id
     - Family
     - Fact source
     - Tutorial coverage
     - How-to coverage
     - Reference coverage
     - Explanation coverage
     - Example / verification
     - EN/ZH
   * - ``dsl-lexical-comments``
     - lexical
     - ``GrammarLexer.g4`` comments / strings / IDs
     - N/A: tutorial hides token table
     - N/A: task pages use snippets
     - :ref:`dsl-lexical-forms`
     - N/A: syntax token facts
     - reference table review
     - synced
   * - ``dsl-top-level-root``
     - top-level
     - ``state_machine_dsl`` / root ``state_definition``
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-small-valid-model-task`
     - :ref:`dsl-top-level-forms`
     - :ref:`dsl-root-design`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-top-level-def``
     - top-level
     - ``def_assignment`` / ``init_expression``
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-expression-safety-task`
     - :ref:`dsl-top-level-forms`
     - :ref:`dsl-expression-separation`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-import-preamble``
     - import
     - ``preamble_program`` / ``constant_definition`` / ``initial_assignment``
     - N/A: tutorial skips imports
     - :ref:`dsl-import-task`
     - :ref:`dsl-import-preamble-forms`
     - :ref:`dsl-import-assembly-semantics`
     - ``import_host_*.fcstm`` inspect
     - synced
   * - ``dsl-state-leaf-composite``
     - state
     - ``state_definition`` leaf/composite branches
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-state-target-task`
     - :ref:`dsl-state-forms`
     - :ref:`dsl-ownership-name-resolution`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-state-pseudo``
     - state
     - ``PSEUDO STATE`` / ``E_PSEUDO_NOT_LEAF``
     - N/A: tutorial links advanced routing
     - :ref:`dsl-state-target-task`
     - :ref:`dsl-state-forms`
     - :ref:`dsl-combo-relay-semantics`
     - ``pseudo_state_demo.fcstm`` inspect
     - synced
   * - ``dsl-state-target-resolution``
     - state
     - model state lookup / transition ownership
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-state-target-task`
     - :ref:`dsl-state-forms`
     - :ref:`dsl-ownership-name-resolution`
     - scope snippets / model validation
     - synced
   * - ``dsl-transition-initial``
     - transition
     - ``entryTransitionDefinition``
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-small-valid-model-task`
     - :ref:`dsl-transition-forms`
     - :ref:`dsl-composite-entry-semantics`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-transition-plain-event``
     - transition
     - ``normalTransitionDefinition`` / event terms
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-guards-effects-task` / :ref:`dsl-event-scopes-task`
     - :ref:`dsl-transition-forms`
     - :ref:`dsl-event-ownership-signal`
     - ``event_scoping_complete.fcstm`` inspect
     - synced
   * - ``dsl-transition-guard-effect``
     - transition
     - ``COLON IF`` / ``EFFECT`` operation block
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-guards-effects-task`
     - :ref:`dsl-transition-forms`
     - :ref:`dsl-expression-separation`
     - ``operation_blocks_complete.fcstm`` inspect
     - synced
   * - ``dsl-transition-combo``
     - transition
     - ``combo_transition_trigger`` / ``entry_combo_transition_trigger``
     - N/A: tutorial links advanced transition
     - :ref:`dsl-combo-transition-task`
     - :ref:`dsl-transition-forms`
     - :ref:`dsl-combo-relay-semantics`
     - ``combo_transitions.fcstm`` inspect
     - synced
   * - ``dsl-transition-forced``
     - transition
     - ``transition_force_definition``
     - N/A: tutorial links advanced transition
     - :ref:`dsl-forced-transition-task`
     - :ref:`dsl-transition-forms`
     - :ref:`dsl-forced-transition-expansion`
     - ``forced_transitions.fcstm`` inspect
     - synced
   * - ``dsl-event-scopes``
     - event
     - ``event_definition`` / ``chain_id``
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-event-scopes-task`
     - :ref:`dsl-events-scopes`
     - :ref:`dsl-event-ownership-signal`
     - ``event_scoping_complete.fcstm`` inspect
     - synced
   * - ``dsl-operation-assignment-temp``
     - operation
     - ``operation_assignment`` / local temp tracking
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-guards-effects-task`
     - :ref:`dsl-operation-blocks`
     - :ref:`dsl-expression-separation`
     - ``operation_blocks_complete.fcstm`` inspect
     - synced
   * - ``dsl-operation-conditionals``
     - operation
     - ``if_statement`` / empty statement
     - N/A: tutorial keeps blocks small
     - :ref:`dsl-guards-effects-task`
     - :ref:`dsl-operation-blocks`
     - :ref:`dsl-expression-separation`
     - ``operation_blocks_complete.fcstm`` inspect
     - synced
   * - ``dsl-expression-init``
     - expression
     - ``init_expression``
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-expression-safety-task`
     - :ref:`dsl-expression-reference`
     - :ref:`dsl-expression-separation`
     - top-level initializer snippets
     - synced
   * - ``dsl-expression-runtime``
     - expression
     - ``num_expression`` / math functions / bitwise
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-expression-safety-task`
     - :ref:`dsl-expression-reference`
     - :ref:`dsl-expression-separation`
     - ``expression_condition_ternary.fcstm`` inspect
     - synced
   * - ``dsl-expression-condition``
     - expression
     - ``cond_expression`` / comparison / boolean ops
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-expression-safety-task`
     - :ref:`dsl-expression-reference`
     - :ref:`dsl-expression-separation`
     - ``expression_condition_ternary.fcstm`` inspect
     - synced
   * - ``dsl-expression-ternary``
     - expression
     - ``conditionalCStyleExprNum`` / ``conditionalCStyleCondNum``
     - N/A: tutorial keeps arithmetic simple
     - :ref:`dsl-expression-safety-task`
     - :ref:`dsl-expression-reference`
     - :ref:`dsl-expression-separation`
     - ``expression_condition_ternary.fcstm`` inspect
     - synced
   * - ``dsl-lifecycle-concrete``
     - lifecycle
     - ``enter`` / ``during`` / ``exit`` operation forms
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-lifecycle-task`
     - :ref:`dsl-lifecycle-forms`
     - :ref:`dsl-lifecycle-hooks-semantics`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-lifecycle-named-abstract-ref``
     - lifecycle
     - named / ``abstract`` / doc-comment / ``ref`` branches
     - N/A: tutorial links advanced hooks
     - :ref:`dsl-lifecycle-task`
     - :ref:`dsl-lifecycle-forms`
     - :ref:`dsl-lifecycle-hooks-semantics`
     - ``abstract_reference_demo.fcstm`` inspect
     - synced
   * - ``dsl-aspect-forms``
     - aspect
     - ``during_aspect_definition``
     - N/A: tutorial only links
     - :ref:`dsl-aspect-task`
     - :ref:`dsl-aspect-forms`
     - :ref:`dsl-during-aspect-semantics`
     - ``hierarchy_execution.fcstm`` inspect
     - synced
   * - ``dsl-import-basic-alias``
     - import
     - ``import_statement`` header
     - N/A: tutorial skips imports
     - :ref:`dsl-import-task`
     - :ref:`dsl-import-forms`
     - :ref:`dsl-import-assembly-semantics`
     - ``import_host_basic.fcstm`` inspect
     - synced
   * - ``dsl-import-mapping``
     - import
     - ``def_mapping_statement`` / ``event_mapping_statement``
     - N/A: tutorial skips imports
     - :ref:`dsl-import-task`
     - :ref:`dsl-import-forms`
     - :ref:`dsl-import-assembly-semantics`
     - ``import_host_mapped.fcstm`` inspect
     - synced
   * - ``dsl-import-directory-boundary``
     - import
     - import path resolution in ``model/imports.py``
     - N/A: tutorial skips imports
     - :ref:`dsl-import-task`
     - :ref:`dsl-import-forms`
     - :ref:`dsl-import-assembly-semantics`
     - ``import_host_directory.fcstm`` inspect
     - synced
   * - ``dsl-diagnostics-target-risk``
     - diagnostics
     - ``pyfcstm/diagnostics/codes.yaml`` / analyzers
     - :ref:`sec-tutorials-dsl`
     - :ref:`dsl-diagnostics-task`
     - :ref:`dsl-diagnostics-risk`
     - :ref:`dsl-expression-separation`
     - risk wording line audit
     - synced

.. _dsl-fact-check-notes:

Fact-check notes
----------------

* Grammar facts come from ``GrammarParser.g4`` and ``GrammarLexer.g4``.
* AST shape and export details come from ``pyfcstm/dsl/node.py`` and
  ``pyfcstm/dsl/listener.py``.
* Import assembly facts come from ``pyfcstm/model/imports.py``.
* Target-risk diagnostics come from ``pyfcstm/diagnostics/codes.yaml`` and
  ``pyfcstm/diagnostics/analyzers/``.
* LLM-facing syntax guidance is in ``pyfcstm/llm/fcstm_grammar_guide.md``. This
  page does not modify that packaged guide.
