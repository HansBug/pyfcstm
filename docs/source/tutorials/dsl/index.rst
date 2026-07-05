.. _sec-tutorials-dsl:

Write your first FCSTM DSL model
================================

.. contents:: Page map
   :local:
   :depth: 2

Overview
--------

This tutorial is the short first-success path for the FCSTM DSL. It teaches one
small model that can be parsed, simulated, and inspected. It deliberately does
not try to list every operator, import mapping, transition variant, or diagnostic
code.

Use the split pages when you need more detail:

* :doc:`../../how_to/dsl/index` for task recipes such as event scopes, imports,
  lifecycle reuse, and combo transitions.
* :doc:`../../reference/dsl/index` for exact grammar forms and coverage matrix
  rows.
* :doc:`../../explanations/dsl_semantics/index` for ownership, lifecycle, combo,
  and import semantics.
* :doc:`../../reference/diagnostics_codes/index` for diagnostics wording and
  target-profile risk boundaries.

Start with one valid root
-------------------------

A runnable FCSTM file has persistent variable declarations first, then exactly
one root ``state``. Most real models use a composite root because it can own
child states and an initial transition.

Fragment showing the skeleton::

   def int temperature = 20;
   def int target = 22;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

The declarations are not local variables; they are persistent model variables.
The root state owns the name-resolution tree for child states, events,
transitions, and lifecycle actions.

Add variables and arithmetic
----------------------------

The current persistent variable types are ``int`` and ``float``. Initial values
may use numeric literals, math constants, unary signs, arithmetic, bitwise
operators, and supported math functions. The tutorial only needs simple
arithmetic:

Fragment::

   def int temperature = 20;
   def int target = 22;
   def float gain = 0.5;

Use the full expression reference when you need hexadecimal literals,
``pi``/``E``/``tau``, math functions, bitwise operators, boolean operators, or
C-style ternary expressions: :ref:`dsl-expression-reference`.

Add leaf and composite states
-----------------------------

A leaf state ends with ``;``. A composite state owns nested declarations inside
``{ ... }`` and must choose an initial child with ``[*] -> Child;``.

Fragment::

   state Thermostat {
       [*] -> Idle;
       state Idle;
       state Heating;
   }

Transitions resolve targets in their owner scope. If a target is an inner leaf
owned by a composite, put the transition inside that composite, or transition to
the composite and let its initial transition choose the child.

Add events and transitions
--------------------------

The first model only needs event transitions and guard transitions. Source-local
events use ``:: EventName``. Guard transitions use ``: if [condition]``.

Fragment::

   Idle -> Heating : if [temperature < target];
   Heating -> Idle :: StopHeating;

Ordinary transitions intentionally keep event syntax and guard syntax separate.
When you truly need event-plus-guard behavior, use the combo-trigger recipes and
reference tables rather than inventing a mixed ordinary form.

Add guards and effects
----------------------

Guards are condition expressions. Effects are operation blocks that update
persistent variables and may use block-local temporary variables after assigning
them.

Fragment::

   Idle -> Heating : if [temperature < target] effect {
       delta = target - temperature;
       temperature = temperature + delta;
   }

Assignments require arithmetic expressions. Guards require conditions. A
comparison such as ``temperature < target`` bridges arithmetic expressions into a
condition.

Add minimal lifecycle hooks
---------------------------

Lifecycle blocks run at state boundaries or active cycles. For a first model,
keep them concrete and local:

Fragment::

   state Heating {
       enter {
           heating_on = 1;
       }
       during {
           temperature = temperature + 1;
       }
       exit {
           heating_on = 0;
       }
   }

Named actions, ``abstract`` hooks, documentation-comment abstract hooks, ``ref``
reuse, ``during before`` / ``during after``, and ``>> during`` aspects are
covered in the task guide and reference.

Run and inspect the model
-------------------------

The first runnable tutorial model is kept as a checked-in source file:

.. literalinclude:: thermostat_example.fcstm
   :language: fcstm
   :caption: ``thermostat_example.fcstm``

Run a short simulation from this directory:

.. code-block:: bash

   pyfcstm simulate -i thermostat_example.fcstm -e "cycle; cycle; current"

Then inspect the model structure and diagnostics:

.. code-block:: bash

   pyfcstm inspect -i thermostat_example.fcstm --format json -o thermostat.inspect.json

Only short command outputs belong in this tutorial. If inspect reports a syntax,
model, combo, import, or C/C++ deployment-profile warning, use the diagnostics
and how-to pages for targeted repair steps.

Where next
----------

* Event scopes: :ref:`dsl-event-scopes-task` and :ref:`dsl-events-scopes`.
* Guard/effect operation blocks: :ref:`dsl-guards-effects-task` and
  :ref:`dsl-operation-blocks`.
* Expressions: :ref:`dsl-expression-safety-task` and
  :ref:`dsl-expression-reference`.
* Lifecycle, abstract hooks, refs, and aspects:
  :ref:`dsl-lifecycle-task`, :ref:`dsl-lifecycle-forms`, and
  :ref:`dsl-aspect-forms`.
* Forced and combo transitions: :ref:`dsl-forced-transition-task`,
  :ref:`dsl-combo-transition-task`, and :ref:`dsl-transition-forms`.
* Imports: :ref:`dsl-import-task` and :ref:`dsl-import-forms`.
* Diagnostics and target risk wording: :ref:`dsl-diagnostics-task`,
  :ref:`dsl-diagnostics-risk`, and :doc:`../../reference/diagnostics_codes/index`.
