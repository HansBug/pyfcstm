.. _sec-reference-dsl:

DSL reference
=============

.. contents:: Table of Contents
   :local:
   :depth: 2

Scope
-----

This page is the fact-oriented DSL reference. It is checked against the current
split grammar files, especially ``pyfcstm/dsl/grammar/GrammarParser.g4`` and
``pyfcstm/dsl/grammar/GrammarLexer.g4``. Use it when you need exact forms and
boundaries. Use :doc:`../../tutorials/dsl/index` for the first learning path,
:doc:`../../how_to/dsl/index` for recipes, and
:doc:`../../explanations/dsl_semantics/index` for semantic background.

Top-level structure
-------------------

.. code-block:: fcstm

   def int counter = 0;
   def float target = 22.5;

   state Root {
       [*] -> Idle;
       state Idle;
   }

Facts:

* Persistent variables appear before the single root ``state``.
* Supported persistent variable types are ``int`` and ``float``.
* The root state is the only top-level state definition.
* Comments may use ``// ...``, ``# ...``, or ``/* ... */`` forms.

State forms
-----------

.. list-table:: State definition forms
   :header-rows: 1

   * - Form
     - Meaning
     - Notes
   * - ``state Name;``
     - Leaf state
     - No nested declarations.
   * - ``state Name { ... }``
     - Composite state
     - Must choose an initial child with ``[*] -> Child;``.
   * - ``pseudo state Name;``
     - Pseudo leaf state
     - Used by the model for automatic flow expansion and intermediate routing.
   * - ``pseudo state Name { ... }``
     - Pseudo composite state
     - Rare; keep pseudo states pure unless a feature explicitly requires more.
   * - ``state Name named "Display";``
     - Named state
     - Adds a display name without changing the identifier.

Transition forms
----------------

.. list-table:: Common transition forms
   :header-rows: 1

   * - Form
     - Meaning
     - Effect allowed
   * - ``[*] -> Target;``
     - Initial transition inside a composite state
     - Yes: ``effect { ... }``
   * - ``Source -> Target;``
     - Plain transition
     - Yes
   * - ``Source -> Target :: LocalEvent;``
     - Local event transition
     - Yes
   * - ``Source -> Target : ParentEvent;``
     - Chain-scoped event transition
     - Yes
   * - ``Source -> Target : /RootEvent;``
     - Root-scoped event transition
     - Yes
   * - ``Source -> Target : if [condition];``
     - Guard transition
     - Yes
   * - ``Source -> [*];``
     - Exit transition to the owning composite exit marker
     - Yes

Do not combine event syntax and ``: if [...]`` guard syntax in one ordinary
transition. Combo trigger syntax exists for the explicit combined forms below.

Combo trigger forms
~~~~~~~~~~~~~~~~~~~

A combo trigger joins event and guard terms with ``+``. The parser accepts forms
such as:

.. code-block:: fcstm

   Source -> Target :: Event + [x > 0];
   Source -> Target : Parent.Event + [x > 0];
   Source -> Target : [x > 0] + Parent.Event;

The DSL semantics page explains how combo triggers are expanded and why pseudo
intermediate states exist. Runtime cycle details are intentionally deferred to
execution-semantics documentation.

Forced transition forms
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: fcstm

   !State -> Target :: Event;
   !State -> [*] : if [condition];
   !* -> Target : /Reset;
   !* -> [*];

Forced transitions expand into normal transitions and currently do not support
``effect`` blocks. Keep side effects on explicit normal transitions when you need
state updates.

Events and scopes
-----------------

Declare an event inside a composite state with:

.. code-block:: fcstm

   event Start;
   event Stop named "Stop button";

.. list-table:: Event scope forms
   :header-rows: 1

   * - Form
     - Meaning
     - Typical use
   * - ``:: Local``
     - Source-local event name
     - Event is resolved from the source state namespace.
   * - ``: ParentEvent``
     - Chain-scoped event path
     - Event is searched through containing scopes.
   * - ``: /GlobalEvent``
     - Root-scoped absolute path
     - Event is resolved from the root namespace.
   * - ``: Parent.Child.Event``
     - Dotted chain path
     - Use when an event is owned by a named nested scope.

Guards, effects, and operation blocks
-------------------------------------

Guards use condition expressions inside square brackets:

.. code-block:: fcstm

   A -> B : if [temperature >= target && failures < 3];

Effects and lifecycle actions use operation statements:

.. code-block:: fcstm

   A -> B effect {
       failures = failures + 1;
       tmp = failures * 2;
   }

Facts:

* Assignments require arithmetic expressions on the right-hand side.
* Guards require boolean conditions.
* A block-local temporary name may be assigned before it is read in the same
  block.
* ``if [condition] { ... } else { ... }`` is valid inside operation blocks.

Expression facts
----------------

.. list-table:: Expression categories
   :header-rows: 1

   * - Category
     - Examples
     - Where it is used
   * - Integer literals
     - ``0``, ``42``, ``0xFF``
     - ``int`` initialization and arithmetic expressions.
   * - Float literals
     - ``3.14``, ``.5``, ``1e-6``
     - ``float`` initialization and arithmetic expressions.
   * - Constants
     - ``pi``, ``E``, ``tau``
     - Numeric expressions.
   * - Arithmetic operators
     - ``+``, ``-``, ``*``, ``/``, ``%``, ``**``
     - Numeric expressions.
   * - Bitwise operators
     - ``&``, ``|``, ``^``, ``<<``, ``>>``
     - Integer-style numeric expressions.
   * - Comparisons
     - ``<``, ``<=``, ``==``, ``!=``, ``>=``, ``>``
     - Bridge numeric expressions into conditions.
   * - Boolean operators
     - ``&&`` / ``and``, ``||`` / ``or``, ``!`` / ``not``
     - Conditions.
   * - Implication/equivalence
     - ``=>`` / ``implies``, ``iff``
     - Conditions.
   * - Boolean xor
     - ``xor``
     - Conditions. Do not use numeric ``^`` as boolean xor.

Supported unary math function names are tokenized by the lexer and include
``sin``, ``cos``, ``tan``, ``sqrt``, ``exp``, ``log``, ``log10``, ``abs``,
``ceil``, ``floor``, ``round``, ``trunc``, and related inverse/hyperbolic
forms.

Lifecycle forms
---------------

.. list-table:: Lifecycle action forms
   :header-rows: 1

   * - Form
     - Meaning
   * - ``enter { ... }``
     - Concrete action when entering the state.
   * - ``enter Name { ... }``
     - Named concrete enter action.
   * - ``enter abstract Hook;``
     - Abstract hook supplied by runtime integration.
   * - ``enter ref Path.To.Action;``
     - Reference to a named lifecycle action.
   * - ``during { ... }``
     - Concrete action during an active cycle.
   * - ``during before { ... }`` / ``during after { ... }``
     - Composite before/after action forms.
   * - ``>> during before { ... }`` / ``>> during after { ... }``
     - Aspect actions for descendant leaf-state cycles.
   * - ``exit { ... }``
     - Concrete action when leaving the state.

The same named, ``abstract``, documentation-comment, and ``ref`` variants exist
for ``enter``, ``during``, ``>> during``, and ``exit`` according to the grammar.

Import forms
------------

Imports are legal inside composite states:

.. code-block:: fcstm

   import "worker.fcstm" as Worker;

   import "worker.fcstm" as Worker named "Worker subsystem" {
       def * -> worker_$0;
       event /Done -> /WorkerDone;
   }

.. list-table:: Import mapping forms
   :header-rows: 1

   * - Form
     - Meaning
   * - ``def * -> prefix_$0;``
     - Fallback variable mapping.
   * - ``def {a, b} -> mapped_$0;``
     - Set selector mapping.
   * - ``def sensor_* -> sensor_$0;``
     - Compact wildcard selector and target template.
   * - ``def exact -> renamed;``
     - Exact variable mapping.
   * - ``event Source.Event -> Target.Event;``
     - Event mapping, with optional ``named "Display"``.

Compact selector and target-template forms are whitespace-sensitive because the
lexer recognizes them in import-specific modes. If whitespace splits the compact
pattern, parsing fails at the mapping location.

Fact-check notes
----------------

This page intentionally names the current split grammar files:
``GrammarParser.g4`` and ``GrammarLexer.g4``. Older documentation sometimes
referred to a single ``Grammar.g4`` file; that is no longer the current source
layout.

For LLM prompt-oriented modeling rules, also see the packaged guide at
``pyfcstm/llm/fcstm_grammar_guide.md``.
