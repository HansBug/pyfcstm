.. _sec-how-to-dsl:

DSL tasks
=========

.. contents:: Table of Contents
   :local:
   :depth: 2

Scope
-----

This page answers practical “how do I write this DSL shape?” questions. For the
first learning path, use :doc:`../../tutorials/dsl/index`. For exact grammar
facts, use :doc:`../../reference/dsl/index`. For semantic background, use
:doc:`../../explanations/dsl_semantics/index`.

Write a small valid model
-------------------------

Start with variables, a composite root, one initial transition, a source-local
event transition, and two leaf states:

.. code-block:: fcstm

   def int ticks = 0;

   state Machine {
       [*] -> Idle;

       state Idle;
       state Running {
           during {
               ticks = ticks + 1;
           }
       }

       Idle -> Running :: Step;
       Running -> Idle : if [ticks >= 5] effect {
           ticks = 0;
       }
   }

Check it quickly:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "cycle; cycle Step; current"

Write event scopes
------------------

Use local events when the event belongs to the source state’s namespace. A
source-local event does not need a sibling declaration on the parent:

.. code-block:: fcstm

   Idle -> Running :: Start;

Use chain-scoped events when the event belongs to a containing or named scope:

.. code-block:: fcstm

   Running -> Idle : Stop;
   ChildA -> ChildB : Parent.Shared;

Use root-scoped events for global signals:

.. code-block:: fcstm

   Any -> Safe : /EmergencyStop;

If an event cannot be resolved clearly, prefer declaring it close to the owner
state and using the shortest unambiguous scope.

Write guards and effects
------------------------

Use ``: if [condition]`` for a guard and add ``effect { ... }`` when the
transition updates variables:

.. code-block:: fcstm

   Active -> Cooling : if [temperature > target] effect {
       fan_speed = 2;
   }

Do not write event syntax and guard syntax as if they were the same ordinary
trigger. For event-plus-guard, use the combo trigger form below.

Write combo triggers
--------------------

Use ``+`` to combine event and guard terms:

.. code-block:: fcstm

   Idle -> Active :: Start + [enabled == 1];
   Active -> Idle : Stop + [safe == 1];

Keep combo transitions for cases where the model genuinely needs both trigger
terms. The reference page lists accepted forms; the semantics page explains the
pseudo intermediate states used during expansion.

Write composite states
----------------------

Put nested states and their child transitions inside the owning composite:

.. code-block:: fcstm

   state Parent {
       [*] -> A;

       state A;
       state B;

       A -> B;
   }

A parent-level transition to ``Parent`` enters the composite and lets its
initial transition pick the child. A child-to-child transition belongs inside
``Parent``.

Write lifecycle and aspect actions
----------------------------------

Use concrete lifecycle actions for local state behavior:

.. code-block:: fcstm

   state Active {
       enter {
           count = 0;
       }
       during {
           count = count + 1;
       }
       exit {
           count = 0;
       }
   }

Use named actions and ``ref`` when several states should share the same action:

.. code-block:: fcstm

   state Parent {
       enter SharedEnter {
           count = 0;
       }

       state Child {
           enter ref Parent.SharedEnter;
       }
   }

Use ``abstract`` hooks when generated code should call user-provided behavior:

.. code-block:: fcstm

   state Active {
       enter abstract OnActive;
   }

Use aspect actions for descendant leaf-state cycles, not for pseudo-state combo
intermediates:

.. code-block:: fcstm

   state Parent {
       >> during before {
           audit = audit + 1;
       }
   }

Write imports
-------------

Import a subsystem as a child state:

.. code-block:: fcstm

   state System {
       [*] -> Worker;
       import "worker.fcstm" as Worker;
   }

Map imported variables with compact selectors and templates when names need to
be rewritten:

.. code-block:: fcstm

   import "worker.fcstm" as Worker {
       def * -> worker_$0;
       def sensor_* -> worker_sensor_$0;
   }

Map events when the parent and imported subsystem should exchange signals:

.. code-block:: fcstm

   import "worker.fcstm" as Worker {
       event /Start -> /WorkerStart;
       event /WorkerDone -> /Done;
   }

Compact selector/template spelling is whitespace-sensitive. Keep wildcard
patterns such as ``sensor_*`` and templates such as ``worker_$0`` contiguous.

Choose where to read next
-------------------------

* Need exact accepted syntax? Read :doc:`../../reference/dsl/index`.
* Need hierarchy, combo, import, or lifecycle meaning? Read
  :doc:`../../explanations/dsl_semantics/index`.
* Need inspect diagnostics for invalid DSL? Read :doc:`../inspect/index` and
  :doc:`../../reference/diagnostics_codes/index`.
