.. _sec-explanations-dsl-semantics:

DSL semantics explanation
=========================

.. contents:: Table of Contents
   :local:
   :depth: 2

Scope
-----

This page explains the meaning and design boundaries behind the FCSTM DSL. It
is not a syntax table; use :doc:`../../reference/dsl/index` for exact forms. It
is not a first tutorial; use :doc:`../../tutorials/dsl/index` for that. Runtime
cycle details that belong to the simulator, such as hot start and complete
``during before`` / ``during after`` ordering, are intentionally left to the
execution-semantics work.

Why the DSL starts with variables and one root state
------------------------------------------------------

FCSTM models are intended to describe one hierarchical controller at a time.
Putting persistent variables before the single root state makes the model
inputs explicit before behavior is introduced. The root state gives every
transition, event, and lifecycle action a common ownership tree.

This structure also keeps generated code predictable: templates can allocate one
runtime object, one active-state stack, and one variable store for the whole
machine.

Hierarchy and initial transitions
---------------------------------

A composite state is not just a namespace. It owns child states and chooses the
first active child through an initial transition. That is why every composite
state needs a ``[*] -> Child;`` transition.

A transition to a composite state enters the composite first; the initial
transition then selects the child. A transition between two children belongs in
the owning composite so name resolution and lifecycle ownership stay local.

Pseudo and combo transitions
----------------------------

Pseudo states are intermediate control-flow nodes. They should be treated as
routing helpers rather than user-visible business states. Combo trigger syntax
uses this idea: a transition that combines events and guards can be expanded
into a chain of simpler checks using pseudo intermediate states.

The DSL-level semantics are:

* Event and guard terms are separate trigger terms.
* ``+`` means the combo trigger requires the listed terms in the generated
  route, not that ordinary event and guard syntax have become interchangeable.
* Pseudo intermediate states are for expansion and routing. They should not be
  given user business behavior.
* If a generated pseudo-state name would collide with a real state, model
  construction should extend the generated name or report the collision rather
  than silently shadowing the user state.

The exact runtime order after expansion belongs to execution-semantics
verification, especially when future work tightens combo behavior.

Event scopes and ownership
--------------------------

Events are owned by states, just like child states are. The three event forms
exist to make ownership explicit at different distances:

* ``:: Event`` means “the event local to this transition source context”.
* ``: Event`` or ``: Parent.Event`` means “resolve along a chain of containing
  or named scopes”.
* ``: /Event`` means “resolve from the root”.

Use the shortest form that still communicates ownership. Overusing root-scoped
events makes large models harder to refactor; overusing local events can hide
shared protocol signals.

Guards, effects, and expression separation
------------------------------------------

The DSL separates arithmetic expressions from conditions because generated
runtime code may target languages with stricter type and truthiness rules than
Python. Assignments update numeric variables; guards decide control flow.
Comparisons bridge the two worlds.

This separation is especially important for C/C++ target code, where an
expression that accidentally relies on Python truthiness would be misleading.
Python generation may tolerate more runtime values, but the DSL reference should
still describe the language-level contract rather than a single backend’s
accident.

Lifecycle and aspect boundaries
-------------------------------

``enter`` and ``exit`` are state-bound lifecycle hooks. ``during`` is an active
cycle hook. Named, ``abstract``, and ``ref`` forms exist so generated code can
separate model structure from user-provided integration behavior.

``>> during before`` and ``>> during after`` are aspect actions for descendant
leaf-state cycles. They are not meant to add business behavior to pseudo combo
intermediate states. This keeps combo expansion a control-flow detail instead of
creating surprising observable lifecycle behavior.

Import assembly semantics
-------------------------

Imports assemble another FCSTM file as a child subsystem. The imported file
keeps its public entry structure, while mappings rewrite the names that must be
made unique or connected to the parent model.

The import grammar intentionally stops at syntax. File resolution, recursive
loading, mapping precedence, conflict detection, and rewritten model assembly
belong to Python phases after parsing. That split keeps grammar files reusable
and lets diagnostics explain assembly failures with model context.

Design boundaries
-----------------

The DSL is intentionally narrower than a general programming language:

* It models controller state and transitions, not arbitrary computation.
* Operation blocks support assignments and conditional blocks, not loops.
* Events and states are owned by scopes instead of being global strings.
* Imports assemble state-machine fragments instead of textual include files.
* Generated runtime templates must be able to preserve simulator semantics.

These constraints keep models inspectable, renderable, simulatable, and suitable
for target-language generation.
