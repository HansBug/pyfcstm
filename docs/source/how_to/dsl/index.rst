
.. _sec-how-to-dsl:

DSL task guide
==============

.. contents:: Task map
   :local:
   :depth: 2

How to use this page
--------------------

This page is not a syntax catalog. It is a set of recipes for authoring or
repairing common FCSTM DSL shapes. Each recipe states when to use the feature,
what to write, how to verify it, what diagnostics to expect, and where to read
more.

A command that mentions a checked example is intended to run from the repository
root.

.. _dsl-small-valid-model-task:

Write a small valid model
-------------------------

Use this when you need a minimal sanity check before adding advanced features.
Start with one root composite, one initial transition, and leaf states owned by
that composite.

.. literalinclude:: ../../tutorials/dsl/first_thermostat.fcstm
   :language: fcstm
   :caption: First runnable model; expected diagnostics: none.

Verify it:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/first_thermostat.fcstm --format human --color never

Expected summary:

.. code-block:: text

   status: ok
   root: Thermostat
   diagnostics: 0 errors / 0 warnings / 0 infos

Common mistake: putting a transition before both endpoint states exist. Keep the
state declarations and transitions inside the same owning composite unless the
transition intentionally enters or exits that composite boundary.

.. _dsl-state-target-task:

Organize states and resolve targets
-----------------------------------

Use this when a transition says it cannot find a state, or when you are unsure
where a transition should be declared.

Recommended complete pattern:

.. code-block:: fcstm

   state Parent {
       [*] -> ChildA;
       state ChildA;
       state ChildB;
       ChildA -> ChildB;
   }

``ChildA -> ChildB`` belongs inside ``Parent`` because ``Parent`` owns both
names. From outside ``Parent``, target ``Parent`` itself and let ``Parent`` use
its initial transition.

Intentional bad pattern:

.. code-block:: fcstm

   state Root {
       [*] -> Outside;
       state Outside;
       state Parent {
           [*] -> ChildA;
           state ChildA;
           state ChildB;
       }
       Outside -> ChildB;  // invalid: ChildB is not owned by Root
   }

The fix is either ``Outside -> Parent;`` or moving the child-targeting
transition inside ``Parent``. Read :ref:`dsl-state-forms` and
:ref:`dsl-ownership-name-resolution` for the exact rule.

.. _dsl-event-scopes-task:

Write event scopes
------------------

Use events for discrete external triggers. Choose the spelling by ownership:

.. list-table:: Event-scope recipe
   :header-rows: 1
   :widths: 24 34 42

   * - Need
     - Write
     - Meaning
   * - Private event of the source state
     - ``Idle -> Heating :: Heat;``
     - Event is local to ``Idle``.
   * - Event owned by containing or named state
     - ``Idle -> Running : Start;``
     - Event resolves through the containing ownership chain.
   * - Root-owned event
     - ``Worker -> Active : /Start;``
     - Event path starts below the root state.

Checked examples:

.. literalinclude:: ../../tutorials/dsl/event_scoping_complete.fcstm
   :language: fcstm
   :caption: Complete event scopes; expected diagnostics: ``W_UNREFERENCED_VAR`` for the demonstration counter.

Verify and inspect event ownership:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/event_scoping_complete.fcstm --format json

In JSON, check ``events[].qualified_name`` and ``events[].scope``. Do not write
``:/Start`` in actual DSL; that shorthand is prose only. The valid absolute form
is ``: /Start`` with the ``:`` token followed by a root path.

.. _dsl-guards-effects-task:

Write guards, effects, and operation blocks
-------------------------------------------

Use guards to decide whether a transition is enabled. Use effects for updates
that happen after the source exits and before the target enters.

A complete operation-block example is checked in:

.. literalinclude:: ../../tutorials/dsl/operation_blocks_complete.fcstm
   :language: fcstm
   :caption: Assignments, block-local temporary, ``if`` / ``else if`` / ``else``, empty statement, and ternary assignment; expected diagnostics: none.

Key points demonstrated by the file:

* ``delta`` and ``next_sample`` are block-local temporaries. They can be read
  only after assignment inside the same block.
* ``if [condition] { ... } else if [condition] { ... } else { ... }`` is legal
  inside operation blocks.
* A standalone ``;`` is an accepted empty statement.
* Guard conditions and assignment expressions are different languages: guards
  use condition expressions; assignments use numeric expressions.

Verify it:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/operation_blocks_complete.fcstm --format human --color never

Expected diagnostic count is zero. If you see ``E_UNDEFINED_VAR`` with
``refs.is_temporary=true``, the usual fix is to assign the temporary before its
first read in the same block.

.. _dsl-expression-safety-task:

Use expressions safely
----------------------

Use this when an expression parses in one place but not another. FCSTM has three
expression contexts:

.. list-table:: Expression contexts
   :header-rows: 1
   :widths: 22 38 40

   * - Context
     - Accepts
     - Does not accept
   * - ``init_expression``
     - literals, ``pi`` / ``E`` / ``tau``, arithmetic, bitwise operators, unary math functions
     - runtime variable reads, ternary expressions
   * - ``num_expression``
     - runtime variables, arithmetic, bitwise, math functions, numeric ternary
     - condition-only operators outside a parenthesized ternary condition
   * - ``cond_expression``
     - comparisons, ``&&`` / ``and``, ``||`` / ``or``, ``!`` / ``not``, ``=>`` / ``implies``, ``xor``, ``iff``, condition ternary
     - numeric assignment statements

Checked expression examples:

.. literalinclude:: ../../tutorials/dsl/expression_condition_ternary.fcstm
   :language: fcstm
   :caption: Runtime expressions, condition operators, implication, xor/iff, and ternary forms; expected diagnostics: none.

A smaller fragment showing the most common spelling traps:

.. code-block:: fcstm

   // Good: boolean xor is the word "xor".
   A -> B : if [(left > 0) xor (right > 0)];

   // Good: implication is "=>" or "implies" in a condition.
   A -> B : if [request > 0 => ready > 0];

   // Good: numeric bitwise xor remains "^".
   flags = flags ^ 0x01;

Do not use ``->`` for implication; it is transition syntax. Do not use ``^`` as
boolean xor. See :ref:`dsl-expression-reference` and
:ref:`dsl-expression-separation` for precedence and design rationale.

.. _dsl-lifecycle-task:

Write lifecycle hooks, refs, and abstract hooks
-----------------------------------------------

Use concrete lifecycle actions when the model itself owns the behavior. Use
``abstract`` when generated code should call a user-provided hook. Use ``ref``
when multiple states should reuse a named lifecycle action.

.. code-block:: fcstm

   state Device {
       enter SharedInit {
           ready = 1;
       }

       state Idle {
           enter ref /SharedInit;
           during abstract PollHardware;
       }
   }

``ref`` points to a named lifecycle action, not to a state and not to an event.
The checked example below shows concrete, abstract, doc-comment abstract, and
reference forms:

.. literalinclude:: ../../tutorials/dsl/abstract_reference_demo.fcstm
   :language: fcstm
   :caption: Abstract and reference actions; expected diagnostics: two ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT`` entries and one ``I_TRANSITION_NEVER_EVENT_TRIGGERED`` note.

Review the diagrams when you need lifecycle ordering:

.. image:: ../../tutorials/dsl/leaf_state_lifecycle.puml.svg
   :alt: Leaf state lifecycle

.. image:: ../../tutorials/dsl/composite_state_lifecycle.puml.svg
   :alt: Composite state lifecycle

.. _dsl-aspect-task:

Use during aspects
------------------

Use ``>> during before`` and ``>> during after`` on an ancestor when monitoring
or logging should wrap descendant leaf-state active cycles. Do not confuse them
with plain ``during before`` / ``during after`` actions on a composite.

.. literalinclude:: ../../tutorials/dsl/hierarchy_execution.fcstm
   :language: fcstm
   :caption: Aspect and hierarchy execution example; expected diagnostics: ``W_UNREFERENCED_VAR`` and ``I_TRANSITION_NEVER_EVENT_TRIGGERED`` for demonstration-only model parts.

Interpretation:

* ancestor ``>> during before`` runs before the active leaf ``during``;
* ancestor ``>> during after`` runs after the active leaf ``during``;
* plain composite ``during before`` / ``during after`` is part of composite
  entry/exit semantics and does not wrap child-to-child transitions;
* aspect actions do not run inside combo pseudo relay states.

See :ref:`dsl-during-aspect-semantics` for the detailed boundary.

.. _dsl-forced-transition-task:

Write forced transitions
------------------------

Use forced transitions when one declaration should expand over many source
states. Forced transitions are expansion shorthand, not a way to hide shared side
effects.

.. literalinclude:: ../../tutorials/dsl/forced_transitions.fcstm
   :language: fcstm
   :caption: Forced transition example; expected diagnostics: two ``W_UNREFERENCED_VAR`` warnings for demonstration-only variables.

Rules:

* ``!State -> Target :: Event;`` expands from the named source and its reachable
  nested sources.
* ``!* -> Target :: Event;`` expands from all applicable sources in the owner
  scope.
* A forced transition may have one local, chain/root, or guard trigger.
* It cannot have a combo ``+`` chain and cannot have an ``effect`` block.

If you need shared side effects, put them in the target state's ``enter`` block
or write explicit normal transitions with visible ``effect`` blocks. See
:ref:`dsl-forced-transition-expansion` for why the DSL keeps this restriction.

.. _dsl-combo-transition-task:

Write combo transitions
-----------------------

Use combo triggers when one transition should require an ordered chain of event
terms and guard terms in the same cycle. Combo transitions expand into pseudo
relay states during model construction; simulation, inspect, generation, and
PlantUML consume the expanded model.

.. literalinclude:: ../../tutorials/dsl/combo_transitions.fcstm
   :language: fcstm
   :caption: Normal combo, entry combo, guard alias, root event term, effects, and generated pseudo relay states; expected diagnostics: none.

Verify the expansion:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_transitions.fcstm --format json

Useful JSON fields:

* ``combo_origins`` keeps the author-written trigger and each term.
* ``combo_transitions`` lists generated edges that carry provenance back to the
  original combo.
* ``states`` includes generated pseudo states with ``is_pseudo=true`` and names
  beginning with ``__combo_``.

Repair examples:

.. code-block:: fcstm

   // Bad ordinary syntax: event suffix plus separate guard suffix.
   A -> B :: Go if [ready > 0];

   // Good combo syntax: event term plus bracketed guard term.
   A -> B :: Go + [ready > 0];

Repeated event terms are legal but suspicious. The checked warning example is:

.. literalinclude:: ../../tutorials/dsl/combo_duplicate_event.fcstm
   :language: fcstm
   :caption: Intentional duplicate-event combo example; expected diagnostics: ``W_COMBO_DUPLICATE_EVENT`` and ``I_TRANSITION_NEVER_EVENT_TRIGGERED``.

.. _dsl-import-task:

Assemble imports
----------------

Use imports when a composite state should include another FCSTM module as a
child. Imports are parsed in the DSL, then path resolution and assembly run in
the Python model/import layer.

Basic import:

.. literalinclude:: ../../tutorials/dsl/import_host_basic.fcstm
   :language: fcstm
   :caption: Basic import host

Mapping import:

.. literalinclude:: ../../tutorials/dsl/import_host_mapped.fcstm
   :language: fcstm
   :caption: Import with variable and event mappings

Imported worker:

.. literalinclude:: ../../tutorials/dsl/import_worker.fcstm
   :language: fcstm
   :caption: Imported worker module

Mapping facts:

* ``def speed -> plant_speed;`` maps one imported variable to one host variable.
* ``def sensor_* -> left_$1;`` captures the wildcard suffix and inserts it into
  the target template.
* ``def * -> prefix_$0;`` is a fallback mapping; ``$0`` is the whole imported
  variable name.
* ``event /Start -> Start;`` maps an imported root event to a host event.
* Directory projects must import a concrete entry file such as
  ``./import_line/main.fcstm``; a bare directory is not a DSL file.

Preamble forms such as ``name = value;`` and ``name := value;`` are parser-helper
entry points used by import assembly tests and helpers. They are not ordinary
root-level ``def`` declarations in a normal ``state_machine_dsl`` file. See
:ref:`dsl-import-preamble-forms` for the exact boundary.

.. _dsl-diagnostics-task:

Diagnose and repair DSL errors
------------------------------

Use inspect diagnostics as a repair loop:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_duplicate_event.fcstm --format json

A diagnostic has a ``code``, ``severity``, human message, source span, and
``refs`` payload. Many diagnostics also carry a suggested fix.

.. list-table:: Diagnostic repair lab
   :header-rows: 1
   :widths: 22 30 48

   * - Example
     - Expected code
     - Repair direction
   * - ``combo_duplicate_event.fcstm``
     - ``W_COMBO_DUPLICATE_EVENT``
     - Check whether the second event term is a typo. Keep it only if the explicit two-hop relay is intentional.
   * - ``guard_vars_never_change.fcstm``
     - ``W_GUARD_VARS_NEVER_CHANGE``
     - Add the missing lifecycle/effect write, or simplify the guard if an initial-value-only guard is intentional.
   * - ``during_const_assign.fcstm``
     - ``W_DURING_CONST_ASSIGN``
     - Move one-time initialization to ``enter`` or make the ``during`` expression depend on runtime state.
   * - ``numeric_target_range.fcstm``
     - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - Treat it as a C/C++ deployment-profile warning for ``c`` / ``c_poll`` / ``cpp`` / ``cpp_poll``. It is not evidence that Python generated code has the same fixed-width risk.

Minimal bad syntax example kept as a text fixture because it is intentionally not parseable as ``*.fcstm``:

.. literalinclude:: ../../tutorials/dsl/event_guard_mixed_invalid.fcstm.txt
   :language: fcstm
   :caption: Intentional parser error; expected excerpt: ``Unexpected token 'if'``.

It fails because ordinary event syntax and ordinary guard syntax are two separate transition forms. Repair it as combo syntax:

.. code-block:: fcstm

   A -> B :: Go + [ready > 0];

For code-level details, read :doc:`../../reference/diagnostics_codes/index`.
