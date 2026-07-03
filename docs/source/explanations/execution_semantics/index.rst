.. _sec-explanations-execution-semantics:

Execution semantics explanation
===============================

This page explains how the simulator executes a model.  It is not a command
reference.  For tasks such as batch mode, hot start and export, see
:doc:`../../how_to/simulation/index`.

Cycle model
-----------

A runtime keeps an active stack from the root state to the active leaf.  Calling
``cycle()`` performs one model step against that stack and the persistent
variable map.  The high-level phases are:

1. initialize the root-to-leaf stack if the runtime has not entered the model;
2. validate candidate transitions before committing them;
3. execute exits and transition effects for the selected transition;
4. enter the target path and perform any initial transitions needed by
   composites;
5. execute ordinary during work when no transition commits for the active leaf;
6. record the resulting state and variables in history.

The simulator uses speculative validation so a transition that cannot reach a
stoppable state does not partially mutate the real runtime.

Initial entry through composites
--------------------------------

A composite state chooses an initial child with ``[*] -> Child``.  On initial
entry through a composite, the simulator runs the composite entry boundary,
selects the initial transition, executes that initial transition's effect, runs
plain ``during before`` for that composite, then enters the selected child.

A child-to-child transition inside a composite is different: it exits the source
child, executes the transition effect, and enters the target child.  Plain
composite ``during before`` and ``during after`` do not wrap ordinary
child-to-child transitions.

The checked demo below shows that plain ``during before`` runs during composite
entry, while ancestor aspect and leaf during work run on later active cycles:

.. literalinclude:: ../../tutorials/simulation/hierarchy_execution.demo.py
   :language: python
   :caption: Hierarchical entry and during execution

Output:

.. literalinclude:: ../../tutorials/simulation/hierarchy_execution.demo.py.txt
   :language: text

Lifecycle and transition effects
--------------------------------

The simulator distinguishes lifecycle blocks from transition effects:

* ``enter`` runs when the state is entered.
* ``during`` runs when the active state remains active for a cycle.
* ``exit`` runs when the state is left.
* transition ``effect`` blocks run between source exit and target entry.

For a source-to-target transition, source exit happens before the effect, and
target entry happens after the effect.  If no transition commits, the active
leaf's ordinary ``during`` path runs instead.

Aspect during actions
---------------------

``>> during before`` and ``>> during after`` are aspect actions contributed by
ancestor states to descendant leaf cycles.  They are different from plain
composite ``during before`` / ``during after`` blocks.

Pseudo states are automatic routing states.  They are not normal stoppable leaf
states, and ancestor aspect during actions do not execute for the pseudo states
inside a pseudo/combo routing chain.  The semantic effect of the whole chain is
validated as part of the surrounding transition path.

Transition priority and validation
----------------------------------

When several transitions are available, the model order and guard/event match
determine which candidate is considered first.  The runtime validates the
candidate path before committing state or variable changes.  If the chosen path
cannot reach a stoppable leaf, the runtime reports a DFS validation failure
instead of leaving the machine halfway through a pseudo or composite routing
chain.

Hot start semantics
-------------------

Hot start builds the active stack directly from an ``initial_state`` and
``initial_vars``.  This represents an already-entered boundary:

* all declared persistent variables must be provided;
* enter actions on the constructed path are skipped;
* plain composite ``during before`` for the constructed boundary is not replayed;
* later cycles run normal transition and during semantics;
* a composite hot-start target is validated so it can reach a stoppable leaf.

This makes hot start useful for debugging and tests, but it is not equivalent to
replaying the full history from the root initial state.

Runtime history and export
--------------------------

After each committed cycle, the runtime records the cycle number, active state
and variables in history.  The REPL ``history`` command formats that in the
terminal, while ``export <path>`` writes the retained history to a file.  Export
is an observation feature; it does not change the runtime state.

Boundary with generated runtimes
--------------------------------

The simulator is the reference model-level executor used before code
generation.  Generated runtimes should be checked against the same scenarios,
but target languages may add platform constraints such as integer width or C/C++
deployment risk that do not apply to the Python simulator itself.  Use inspect
and generated-runtime tests when target-specific behavior matters.
