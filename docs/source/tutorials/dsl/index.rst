PyFCSTM DSL first model tutorial
================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

This tutorial is the short learning path for writing your first FCSTM DSL
model. It intentionally avoids being a complete language reference. When you
need a task recipe, a grammar fact, or a semantic explanation, use these pages:

* :doc:`../../how_to/dsl/index` for task-oriented DSL writing recipes.
* :doc:`../../reference/dsl/index` for syntax forms, operators, and boundary
  tables.
* :doc:`../../explanations/dsl_semantics/index` for why the DSL behaves the way
  it does.

The examples here build a small controller that can be parsed and simulated.

Language Structure
------------------

A DSL file has variable declarations first, followed by exactly one root
``state``:

.. code-block:: fcstm

   def int counter = 0;

   state Controller {
       [*] -> Idle;
       state Idle;
   }

Variables are persistent model variables. The current primitive types are
``int`` and ``float``. The root state may be a leaf state or, more commonly, a
composite state that owns substates and transitions.

Variable Definitions
--------------------

Declare variables before the root state. Initial values may use numeric
literals, constants, arithmetic, and supported math functions:

.. code-block:: fcstm

   def int retries = 0;
   def int flags = 0x00;
   def float target = 22.5;
   def float radius = sqrt(16.0);

Use variables from guards and operation blocks after declaration:

.. code-block:: fcstm

   def int count = 0;

   state Counter {
       [*] -> Ready;
       state Ready {
           during {
               count = count + 1;
           }
       }
   }

For the full literal and expression table, see
:doc:`../../reference/dsl/index`.

State Definitions
-----------------

A leaf state ends with ``;``. A composite state owns nested declarations inside
``{ ... }`` and must choose an initial child with ``[*] -> Child;``:

.. code-block:: fcstm

   state Door {
       [*] -> Closed;

       state Closed;
       state Open;
   }

Composite states let you model hierarchy. Put transitions in the scope where
their source and target names are resolved. If you need a transition to an inner
leaf, place that transition inside the owning composite instead of jumping over
its parent.

Transition Definitions
----------------------

The most common transition forms are plain transitions, event transitions,
guard transitions, and guard-plus-effect transitions:

.. code-block:: fcstm

   state Controller {
       event Tick;
       [*] -> Idle;

       state Idle;
       state Active;

       Idle -> Active :: Tick;
       Active -> Idle : if [counter >= 3] effect {
           counter = 0;
       }
   }

Keep event syntax and guard syntax in separate transition forms. Event-triggered
transitions use ``:: EventName`` for a local event or ``: EventPath`` for a
chain/root-scoped event. Guard transitions use ``: if [condition]``.

Event Definitions
-----------------

Declare explicit events when you want reusable names and diagrams to show event
ownership:

.. code-block:: fcstm

   state Controller {
       event Start;
       event Stop;

       [*] -> Idle;
       state Idle;
       state Running;

       Idle -> Running :: Start;
       Running -> Idle :: Stop;
   }

The event-scope details are in :doc:`../../reference/dsl/index`. Practical
recipes for local, parent, and root-scoped events are in
:doc:`../../how_to/dsl/index`.

Guard Conditions and Effects
----------------------------

Guards are boolean conditions. Effects and lifecycle actions contain operation
blocks, where assignments update persistent variables and block-local temporary
variables may be introduced before they are read:

.. code-block:: fcstm

   def int attempts = 0;

   state RetryController {
       event Failed;
       [*] -> Ready;

       state Ready;
       state Backoff;

       Ready -> Backoff :: Failed effect {
           attempts = attempts + 1;
       }

       Backoff -> Ready : if [attempts < 3];
   }

Use comparison operators such as ``<``, ``<=``, ``==``, ``!=``, ``>=``, and
``>`` to bridge arithmetic expressions into conditions. Use ``&&`` / ``and`` and
``||`` / ``or`` for boolean composition.

Expression System
-----------------

Arithmetic and logical expressions are separate. Assignments expect arithmetic
expressions; guards expect conditions:

.. code-block:: fcstm

   def int x = 1;
   def float y = 2.0;

   state ExprDemo {
       [*] -> A;
       state A;
       state B;

       A -> B : if [(x + 1) >= 2 && y < 3.0];
   }

For every operator and function, use the reference table rather than this
learning page: :doc:`../../reference/dsl/index`.

Lifecycle Actions
-----------------

Lifecycle actions run when states are entered, cycled, or exited. A minimal
leaf-state example is:

.. code-block:: fcstm

   def int cycles = 0;

   state Worker {
       [*] -> Active;
       state Active {
           enter {
               cycles = 0;
           }
           during {
               cycles = cycles + 1;
           }
           exit {
               cycles = 0;
           }
       }
   }

For named actions, ``abstract`` hooks, ``ref`` reuse, and ``>> during`` aspect
actions, see :doc:`../../how_to/dsl/index` and
:doc:`../../explanations/dsl_semantics/index`.

Real-World Example: Smart Thermostat
------------------------------------

A small thermostat model combines variables, events, guards, effects, and
hierarchy:

.. literalinclude:: thermostat_example.fcstm
   :language: fcstm
   :caption: Minimal thermostat DSL example

You can simulate the checked-in example:

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/dsl/thermostat_example.fcstm -e "cycle; current"

Semantic Validation Rules
-------------------------

This page only introduces the common rules that keep the first model valid:

* Declare variables before the root state.
* Use one top-level root ``state``.
* Give each composite state one initial transition.
* Keep transition targets inside the correct scope.
* Use arithmetic expressions in assignments and boolean conditions in guards.

Detailed diagnostics, boundary cases, and deployment risk wording belong to the
inspect and reference pages, not this tutorial.

Import Assembly
---------------

Imports assemble another FCSTM file as a child subsystem inside a composite
state. For a first DSL model, skip imports. When you need them, start with the
how-to recipe and then check the syntax table:

* :doc:`../../how_to/dsl/index` for practical import tasks.
* :doc:`../../reference/dsl/index` for import selectors and mapping forms.
* :doc:`../../explanations/dsl_semantics/index` for assembly boundaries.

Summary
-------

You have now seen the minimum FCSTM DSL path: variables, a root state,
substates, transitions, events, guards, effects, lifecycle actions, and a small
model you can simulate. Use the split pages for deeper work:

* Write a task: :doc:`../../how_to/dsl/index`.
* Check exact syntax: :doc:`../../reference/dsl/index`.
* Understand semantics: :doc:`../../explanations/dsl_semantics/index`.
