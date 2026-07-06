.. _sec-explanations-dsl-semantics:

DSL semantics explanation
=========================

.. contents:: Semantics map
   :local:
   :depth: 2

Scope
-----

This page explains why the FCSTM DSL behaves the way it does. It is not the
syntax table; use :doc:`../../reference/dsl/index` for exact grammar forms. It
is not the first tutorial; use :doc:`../../tutorials/dsl/index` for a runnable
starting path. Complete simulator internals live in
:doc:`../execution_semantics/index`.

.. _dsl-root-design:

Why variables come before one root state
----------------------------------------

A FCSTM model is one controller with one active-state stack. Persistent
variables come before the root so every guard, effect, lifecycle action, import
mapping, and diagnostic pass can use the same data surface.

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

This is not only parser convenience. Code generation needs one runtime object,
one variable store, and one root active stack. Import assembly also needs one
host tree into which imported modules can be rewritten.

.. _dsl-ownership-name-resolution:

Ownership tree and name resolution
----------------------------------

States, events, lifecycle actions, and imports are owned by states. A transition
can directly name endpoints visible in the state where the transition is written.

.. code-block:: fcstm

   state Root {
       [*] -> Parent;

       state Parent {
           [*] -> ChildA;
           state ChildA;
           state ChildB;
           ChildA -> ChildB;
       }
   }

``ChildA -> ChildB`` belongs inside ``Parent``. If a parent-level rule wrote
``RootOutside -> ChildB`` while ``ChildB`` is private to ``Parent``, the rule
would couple the parent to a nested implementation detail. The DSL instead
encourages boundary routing: enter ``Parent`` and let ``Parent`` choose a child,
or move the child-targeting transition into ``Parent``.

Inspect exposes the resolved paths in ``transitions[].from_path`` and
``transitions[].to_path``. That is the evidence to use when checking whether a
transition landed on the boundary or an internal child.

.. _dsl-composite-entry-semantics:

Composite entry and initial transitions
---------------------------------------

A composite state is both a boundary and a child-selection rule. Entering the
boundary is not the same thing as already being in a leaf child.

Initial entry through a composite follows this conceptual order:

1. enter the composite boundary;
2. evaluate and apply the composite's initial transition;
3. run plain composite ``during before``;
4. enter the selected child.

A child-to-child transition is different:

1. exit the source child;
2. run the transition effect;
3. enter the target child.

Plain composite ``during before`` / ``during after`` does not wrap that
child-to-child movement. That boundary keeps composite entry/exit behavior from
turning into hidden behavior on every internal state change.

.. _dsl-event-ownership-signal:

Event scopes as ownership signals
---------------------------------

Event spelling tells readers who owns the signal:

.. list-table:: Event ownership
   :header-rows: 1
   :widths: 22 36 42

   * - Spelling
     - Example
     - Meaning
   * - ``::``
     - ``Idle -> Heating :: Heat;``
     - The source state owns a private event name.
   * - ``:``
     - ``Idle -> Running : Start;``
     - A containing or named state owns the event path.
   * - ``: /``
     - ``Worker -> Active : /Start;``
     - The path starts from the root-owned event namespace.

The spelling matters during refactoring. A source-local event can be copied with
one state; a root event is public protocol. Combo terms inherit the leading
scope unless a continuation term explicitly starts with ``/``.

Forced transitions use similar trigger spellings, but they are declaration
expansion shorthand. A forced trigger still produces ordinary expanded
transitions; it is not a combo chain and it cannot carry an effect.

.. _dsl-expression-separation:

Guard, effect, and expression separation
----------------------------------------

The DSL separates numeric expressions from conditions because value computation
and control-flow decisions have different portability and diagnostic needs.

.. code-block:: fcstm

   Sampling -> Done : if [sensor >= target] effect {
       next_sample = sensor + 1;
       alarm_count = (next_sample > target) ? alarm_count + 1 : alarm_count;
   };

The guard is tested first. The effect runs only after the transition is chosen.
``next_sample`` is a block-local temporary inside the effect; it does not become
persistent state after the block exits.

This separation is also where target-profile warnings must stay precise. A
numeric diagnostic about fixed-width integer range, division policy, shift count,
or float bitwise behavior is a C/C++ deployment-profile warning for ``c``,
``c_poll``, ``cpp``, and ``cpp_poll`` unless the diagnostic explicitly says
otherwise. It is not evidence that the Python generated runtime has the same
fixed-width or undefined-behavior risk.

.. _dsl-lifecycle-hooks-semantics:

Lifecycle, abstract hooks, and refs
-----------------------------------

Lifecycle actions attach behavior to state boundaries and active cycles:

* ``enter`` belongs to entry;
* plain leaf ``during`` belongs to ordinary active cycles;
* ``exit`` belongs to exit;
* named actions create stable reference targets and generated hook names;
* ``abstract`` says generated code must call a user-provided implementation;
* ``ref`` reuses a named lifecycle action path.

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

``ref`` deliberately points to a named lifecycle action, not to a state or an
event. That keeps reusable behavior explicit and avoids making state names double
as callable procedures.

.. _dsl-during-aspect-semantics:

During before/after and aspects
-------------------------------

Two different features use during-stage words:

* plain ``during before`` / ``during after`` belongs to the composite boundary;
* ``>> during before`` / ``>> during after`` is an aspect contributed by an
  ancestor to descendant leaf-state active cycles.

The checked ``hierarchy_execution.fcstm`` example uses numeric additions to make
ordering observable. Conceptually, a leaf active cycle sees:

.. code-block:: text

   ancestor >> during before
   parent   >> during before
   leaf     during
   parent   >> during after
   ancestor >> during after

A child-to-child transition does not run plain composite ``during before`` or
``during after``. Combo pseudo relay states also do not receive aspect actions.
Relay states are routing machinery; letting aspects observe each relay hop would
turn an implementation detail into business behavior.

.. _dsl-combo-relay-semantics:

Pseudo and combo relay semantics
--------------------------------

Combo transitions solve the event-plus-guard problem without inventing an
ordinary transition form that mixes separate event and guard suffixes.

Author-written transition:

.. code-block:: fcstm

   Waiting -> Accepted :: Request + [ready > 0] + Confirm effect {
       accepted = accepted + 1;
   }

Model construction expands this into a pseudo relay chain. Inspect keeps both
views:

* ``combo_origins`` records the original trigger terms and source spans;
* ``combo_transitions`` records generated edges with provenance;
* generated pseudo states are named with the reserved ``__combo_`` prefix.

The final effect belongs to the semantic transition to ``Accepted``. It must not
be duplicated on every relay hop. If any required event or guard term is absent
in the same cycle, the chain does not complete and the visible state should not
silently advance to the final target.

``W_COMBO_DUPLICATE_EVENT`` and combo guard diagnostics point back to the
author-written trigger terms, not merely to generated pseudo states. This is why
inspect diagnostics can guide an LLM or user back to the original DSL source.

.. _dsl-forced-transition-expansion:

Forced transition expansion
---------------------------

Forced transitions are a different kind of expansion. They duplicate one source
pattern over multiple concrete sources:

.. code-block:: fcstm

   !* -> ErrorHandler :: CriticalError;

The expanded transitions are ordinary transitions for runtime purposes: normal
exit actions still run, then the target's entry behavior runs. Forced
transitions cannot carry ``effect`` blocks because a side-effectful many-source
shorthand is hard to audit. If the same update must happen for all expanded
sources, put it in the target ``enter`` action or write explicit normal
transitions.

Forced transitions also cannot carry combo ``+`` chains. Combo is ordered relay
expansion; forced is source-set expansion. Keeping them separate makes the
expanded model inspectable.

.. _dsl-import-assembly-semantics:

Import assembly semantics
-------------------------

Import syntax is legal inside composite states, but file loading and module
assembly run after parsing.

.. code-block:: fcstm

   import "./import_worker.fcstm" as LeftWorker {
       def sensor_* -> left_$1;
       def speed -> plant_speed;
       event /Start -> Start named "Shared Start";
   }

The parser records the path, alias, optional display name, and mapping
statements. The import/model layer then resolves the path, loads the imported
root, checks conflicts, rewrites variable names, rewrites event paths, and adds
the imported root as a child state under the alias.

Mapping templates are not arbitrary code. ``$0`` is the whole matched imported
variable name; ``$1`` / ``${1}`` are capture groups from wildcard selectors;
``*`` is the fallback template. Directory projects must import a concrete entry
file such as ``./line/main.fcstm`` because a bare directory is not DSL source.

Design boundaries
-----------------

The DSL is intentionally narrower than a general programming language:

* no loops in operation blocks;
* no user-defined functions in DSL source;
* event syntax and ordinary guard syntax are not combined on the same ordinary
  transition;
* forced transitions have no effects and no combo chains;
* combo relay pseudo states are pure routing helpers;
* target-risk diagnostics must name their target profile.

Those boundaries keep models parseable, inspectable, simulatable, and suitable
for multi-language code generation.
