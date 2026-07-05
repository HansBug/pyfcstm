
.. _sec-explanations-dsl-semantics:

DSL semantics explanation
=========================

.. contents:: Semantics map
   :local:
   :depth: 2

Scope
-----

This page explains why the FCSTM DSL is shaped the way it is. It is not a syntax
table; use :doc:`../../reference/dsl/index` for exact forms. It is not a first
success tutorial; use :doc:`../../tutorials/dsl/index` for that. Complete runtime
cycle ordering, hot start, and simulator history belong to
:doc:`../execution_semantics/index`.

.. _dsl-root-design:

Why variables come before one root state
----------------------------------------

A model describes one hierarchical controller. Persistent variables come first so
all state behavior has a known data surface before transitions and lifecycle
actions are read. The single root state gives every state, event, transition,
import, and lifecycle action a common ownership tree.

This structure also makes generation predictable. Templates can allocate one
runtime object, one active-stack representation, and one variable store. Import
assembly can then rewrite child subsystems into that tree instead of merging
several unrelated roots.

.. _dsl-ownership-name-resolution:

Ownership tree and name resolution
----------------------------------

States, events, and lifecycle actions are owned by states. Name resolution is
therefore a modeling rule, not just a parser convenience. A transition that moves
between two child states should live in the parent that owns both names. A
transition from outside a composite should enter the composite boundary and let
that composite pick its child through the initial transition.

This keeps ownership local and prevents a parent-level rule from depending on a
private leaf that belongs to a child composite.

.. _dsl-composite-entry-semantics:

Composite entry and initial transitions
---------------------------------------

A composite state is an active boundary plus a child-selection rule. Entering a
composite means entering the boundary first, then following its initial
transition to the selected child. This is different from a child-to-child
transition inside the composite, where the owner already knows both endpoints.

When a transition target is a composite, the target is the boundary. The initial
transition decides the child path. This is why the DSL discourages outer-scope
jumps directly to inner leaves.

.. _dsl-event-ownership-signal:

Event scopes as ownership signals
---------------------------------

The three event scope spellings communicate ownership distance:

* ``:: Local`` says the source state owns or names the event locally.
* ``: EventPath`` says a containing or named scope owns the event.
* ``: /RootEvent`` says the event path is absolute from the root.

The distinction matters for refactoring. A root event can be moved or renamed as
a public protocol. A local event can remain private to one state without forcing
sibling states to agree on a shared event declaration.

.. _dsl-expression-separation:

Guards, effects, and expression separation
------------------------------------------

The DSL separates numeric expressions from conditions because control flow and
value computation have different portability risks. Assignments and numeric
initializers update numbers. Guards decide whether a transition is enabled.
Comparisons bridge numeric values into conditions.

This separation is especially visible when docs discuss generated C/C++ code.
Warnings about fixed-width integers, division-by-zero policy, or bitwise
operation profiles are C/C++ deployment-profile warnings. They should not be
worded as Python generated-runtime failures unless Python-specific evidence
exists.

.. _dsl-lifecycle-hooks-semantics:

Lifecycle, abstract hooks, and refs
-----------------------------------

Lifecycle actions attach behavior to state boundaries and active cycles:
``enter`` on entry, ``during`` while active, and ``exit`` on exit. Named actions
make generated extension points discoverable. ``abstract`` hooks tell generated
code to call user-provided behavior without editing generated files. ``ref``
reuses a named lifecycle action while keeping the state tree explicit.

The design keeps model structure and integration behavior separate. The DSL says
where behavior belongs; the generated runtime exposes target-language hooks for
how abstract behavior is implemented.

.. _dsl-during-aspect-semantics:

During before/after and aspects
-------------------------------

Plain ``during before`` / ``during after`` belongs to a composite lifecycle
boundary. ``>> during before`` / ``>> during after`` are aspect actions that an
ancestor contributes to descendant leaf-state active cycles. They are different
features even though both use during-stage vocabulary.

Aspects do not run inside combo pseudo relay states. Pseudo relays are routing
machinery created to evaluate expanded transition terms; letting ancestor
aspects observe each relay would turn an implementation detail into business
behavior.

.. _dsl-combo-relay-semantics:

Pseudo and combo relay semantics
--------------------------------

Pseudo states represent control-flow routing. Combo transitions use that idea to
turn an event-plus-guard or multi-term trigger into a chain of simpler routing
checks. The chain should have the same external meaning as the original combo
transition, while diagnostics can still inspect each term.

Important boundaries:

* relay pseudo states should be pure routing helpers;
* reserved ``__combo`` names belong to generated relay machinery;
* effect placement must preserve the semantic effect of the original combo
  transition;
* duplicate event and constant guard diagnostics help catch surprising trigger
  definitions;
* aspects do not execute inside the relay chain.

Runtime ordering details belong to :doc:`../execution_semantics/index`.

Forced transition expansion
---------------------------

Forced transitions are shorthand for expanding one declaration across selected
source states. ``!State`` expands from one named source; ``!*`` expands from all
applicable sources in the owner scope. Forced transitions intentionally do not
support ``effect`` blocks because an expanded declaration with side effects would
be hard to audit and would obscure which source actually owns the update.

When effects are needed, write explicit normal transitions so the source, target,
trigger, and update block are all visible.

.. _dsl-import-assembly-semantics:

Import assembly semantics
-------------------------

Import syntax is parsed inside composite states, but path resolution and model
assembly happen after parsing. This split keeps the grammar structural while the
Python import/model layer handles file lookup, recursive loading, aliasing,
variable mappings, event mappings, conflict checks, and diagnostics.

Directory-oriented projects must import an explicit entry file such as
``./line/main.fcstm``. A bare directory is not a DSL file and should not be
documented as supported.

Design boundaries
-----------------

The DSL is intentionally narrower than a general programming language:

* no loops inside operation blocks;
* no arbitrary function definitions;
* arithmetic and condition expressions are separate;
* imports assemble state-machine modules instead of executing code;
* generated-target risks must be described with target scope.

These constraints keep models inspectable, renderable, simulatable, and suitable
for code generation across multiple target languages.
