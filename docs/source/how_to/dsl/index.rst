
.. _sec-how-to-dsl:

DSL task guide
==============

.. contents:: Task map
   :local:
   :depth: 2

Scope and task map
------------------

This page starts from concrete authoring tasks. It gives short snippets or links
to checked-in examples, then points to :doc:`../../reference/dsl/index` for the
complete facts and to :doc:`../../explanations/dsl_semantics/index` for the
semantic background.

Use the tasks below when you need to write or repair a specific DSL shape:

* state ownership and transition targets;
* event scopes;
* guards, effects, operation blocks, and expressions;
* lifecycle actions, ``abstract`` hooks, ``ref``, and ``>> during`` aspects;
* forced transitions and combo transitions;
* imports and diagnostics.

.. _dsl-small-valid-model-task:

Write a small valid model
-------------------------

Start with one root composite, one initial transition, and child leaf states.
The tutorial uses a compact thermostat example as the first runnable model:

.. literalinclude:: ../../tutorials/dsl/first_thermostat.fcstm
   :language: fcstm
   :caption: First runnable DSL model

Check it with:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/first_thermostat.fcstm --format json

.. _dsl-state-target-task:

Organize states and resolve targets
-----------------------------------

Place transitions in the state scope that owns their source and target names.
Sibling transitions belong in the parent composite:

Fragment::

   state Parent {
       [*] -> ChildA;
       state ChildA;
       state ChildB;
       ChildA -> ChildB;
   }

A transition from outside ``Parent`` should target ``Parent`` rather than jumping
directly to ``Parent.ChildB``. The composite entry then uses its initial
transition. Use pseudo states only as routing nodes; user-visible business
states should be normal leaf or composite states.

.. _dsl-event-scopes-task:

Write event scopes
------------------

Use a source-local event when the event is private to the source state:

Fragment::

   Idle -> Heating :: Heat;

Use a chain-scoped event when the event is owned by a containing or named state:

Fragment::

   state Controller {
       event Start;
       Idle -> Running : Start;
   }

Use a root-scoped event when the event is owned by the root state and nested
states need an absolute reference:

Fragment::

   state System {
       [*] -> Worker;
       event Start;
       state Worker {
           [*] -> Idle;
           state Idle;
           state Active;
           Idle -> Active : /Start;
       }
   }

Checked examples:

.. literalinclude:: ../../tutorials/dsl/event_scoping_complete.fcstm
   :language: fcstm
   :caption: Complete event-scope example

.. literalinclude:: ../../tutorials/dsl/event_scoping_comparison.fcstm
   :language: fcstm
   :caption: Event-scope comparison example

.. _dsl-guards-effects-task:

Write guards, effects, and operation blocks
-------------------------------------------

Use ``: if [condition]`` for guard transitions. Add ``effect { ... }`` when the
transition updates variables:

.. literalinclude:: ../../tutorials/dsl/guards_and_effects.fcstm
   :language: fcstm
   :caption: Guards, effects, temporary variables, and ``if`` blocks

Operation blocks support assignments, block-local temporaries, ``if`` / ``else
if`` / ``else`` blocks, and empty statements. A local temporary may be read only
after assignment inside the same block.

.. _dsl-expression-safety-task:

Use expressions safely
----------------------

Assignments use runtime numeric expressions. Top-level and import-preamble
initializers use the stricter ``init_expression`` subset: literals, math
constants, arithmetic, bitwise operators, and unary math functions, but no
runtime variable reads and no C-style ternary. Guards use condition expressions.
Comparisons bridge numeric expressions into conditions. Use the expression
reference for precedence and every supported operator.

Examples to keep straight:

Fragment::

   value = abs(sensor - target) + 1;
   ready = (temperature >= target) ? 1 : 0;
   Idle -> Heating : if [temperature < target && enabled == 1];

The complete expression demo is checked in and should stay parseable:

.. literalinclude:: ../../tutorials/dsl/expression_demo.fcstm
   :language: fcstm
   :caption: Expression demo

.. _dsl-lifecycle-task:

Write lifecycle hooks, refs, and abstract hooks
-----------------------------------------------

Use concrete ``enter``, ``during``, and ``exit`` blocks for local state behavior.
Use named lifecycle actions when the generated extension point should have a
stable name. Use ``abstract`` when generated code should call user-provided
behavior. Use ``ref`` to reuse a named lifecycle action.

Fragment::

   state Active {
       enter Setup {
           flag = 1;
       }
       during abstract Tick;
       exit ref Cleanup;
   }

The checked example covers abstract and reference forms:

.. literalinclude:: ../../tutorials/dsl/abstract_reference_demo.fcstm
   :language: fcstm
   :caption: Abstract and reference action example

Lifecycle diagrams remain as explanatory resources:

.. image:: ../../tutorials/dsl/leaf_state_lifecycle.puml.svg
   :alt: Leaf state lifecycle

.. image:: ../../tutorials/dsl/composite_state_lifecycle.puml.svg
   :alt: Composite state lifecycle

.. _dsl-aspect-task:

Use during aspects
------------------

``>> during before`` and ``>> during after`` are aspect actions contributed by
an ancestor to descendant leaf-state active cycles.

Fragment::

   state Root {
       [*] -> Child;
       >> during before {
           trace = trace + 1;
       }
       state Child;
   }

Do not use aspects as a way to add observable business behavior to combo pseudo
relay states. The pseudo relay chain is routing machinery; aspect actions do not
run inside the relay.

.. _dsl-forced-transition-task:

Write forced transitions
------------------------

Use forced transitions when one declaration should expand over multiple source
states. They may target a state or the exit marker and may use one local, chain,
root, or guard trigger. They do not support combo ``+`` triggers or ``effect``
blocks.

.. literalinclude:: ../../tutorials/dsl/forced_transitions.fcstm
   :language: fcstm
   :caption: Forced transition examples

.. _dsl-combo-transition-task:

Write combo transitions
-----------------------

Use combo triggers when a transition needs multiple trigger terms. Supported
families include ordinary combo and entry combo. Use ``+`` between event and
guard terms. Forced transitions are a separate shorthand and do not accept combo
``+`` triggers.

Fragments::

   Idle -> Running :: Start + [enabled == 1];
   Idle -> Running : [enabled == 1];
   Idle -> Running : [enabled == 1] + Start;
   [*] -> Running :: Boot + [enabled == 1];

``: [condition]`` is the combo guard alias. Use ``: if [condition]`` for
the ordinary single-guard spelling when no combo terms are needed. Combo
expansion uses pseudo relay states. Duplicate event terms, guard aliases,
constant guards, pseudo-name extension, and reserved ``__combo`` names are
reported through diagnostics. Detailed expansion semantics live in
:ref:`dsl-combo-relay-semantics`.

.. _dsl-import-task:

Assemble imports
----------------

Import a file as a child subsystem:

.. literalinclude:: ../../tutorials/dsl/import_host_basic.fcstm
   :language: fcstm
   :caption: Basic import host

The imported worker is:

.. literalinclude:: ../../tutorials/dsl/import_worker.fcstm
   :language: fcstm
   :caption: Imported worker

Map variables and events when parent and child names need rewriting:

.. literalinclude:: ../../tutorials/dsl/import_host_mapped.fcstm
   :language: fcstm
   :caption: Import with mappings

Directory-organized subsystems must import an explicit file such as
``./import_line/main.fcstm``. A bare directory import is not supported:

.. literalinclude:: ../../tutorials/dsl/import_host_directory.fcstm
   :language: fcstm
   :caption: Explicit directory ``main.fcstm`` import

.. literalinclude:: ../../tutorials/dsl/import_line/main.fcstm
   :language: fcstm
   :caption: Directory subsystem entry file

.. literalinclude:: ../../tutorials/dsl/import_line/subsystems/robot.fcstm
   :language: fcstm
   :caption: Nested subsystem file

Import preamble statements inside imported files use ``x = value;`` for
constants and ``x := value;`` for initial assignments. They are parsed by the
preamble entry point, not as ordinary top-level ``def`` declarations.

.. _dsl-diagnostics-task:

Diagnose and fix DSL errors
---------------------------

When parsing fails, fix syntax first. When model validation fails, inspect the
state/event/transition ownership facts. When diagnostics report combo, import,
or target-profile risk, follow the code-specific message and reference table.

Short workflow:

.. code-block:: bash

   pyfcstm inspect -i model.fcstm --format json -o model.inspect.json
   python -m json.tool model.inspect.json | sed -n '1,80p'

Common first fixes:

.. list-table:: Diagnostic repair shortcuts
   :header-rows: 1

   * - Signal
     - What to check first
   * - ``W_GUARD_VARS_NEVER_CHANGE``
     - A guard may read only constants or variables never updated by ``during`` / ``effect``.
   * - ``W_DURING_CONST_ASSIGN``
     - Constant setup probably belongs in ``enter`` instead of every active cycle.
   * - ``W_COMBO_*``
     - Recheck combo trigger terms and remember forced transitions do not support combo ``+`` chains.

Full code descriptions live in :doc:`../../reference/diagnostics_codes/index`.

C/C++ deployment-profile warnings are target-specific review signals for C-family
templates such as ``c``, ``c_poll``, ``cpp``, and ``cpp_poll``. They must not be
reported as proof that Python generated code has the same risk unless the Python
runtime path has its own diagnostic evidence.
