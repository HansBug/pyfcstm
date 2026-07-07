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

Execution-order matrix
----------------------

.. list-table:: Common runtime boundaries
   :header-rows: 1

   * - Scenario
     - Ordering guarantee
     - Evidence family
   * - Cold entry
     - Root/composite entry happens first, then initial transitions choose a
       leaf, and only then can later active cycles run leaf ``during``.
     - ``cold_initial_*`` and ``composite_initial_*`` fixtures.
   * - Ordinary leaf cycle
     - Ancestor aspect ``during before`` runs before leaf ``during``; aspect
       ``during after`` runs afterward.
     - ``design_aspect_*`` and ``aspect_context_*`` fixtures.
   * - Leaf transition
     - Source ``exit`` runs, then transition ``effect``, then target ``enter``.
       If no transition commits, the leaf ``during`` path runs instead.
     - ``design_basic_*`` and transition-effect fixtures.
   * - Composite initial transition
     - Composite entry chooses the initial transition, runs its effect, runs
       plain composite ``during before``, then enters the selected child.
     - ``composite_initial_*`` fixtures.
   * - Pseudo or combo routing
     - Intermediate pseudo states route automatically and are not stoppable
       leaf cycles; the whole candidate chain is validated before commit.
     - ``design_pseudo_chain_*`` and ``combo_transition_trigger_*`` fixtures.
   * - Hot start
     - The stack is constructed as already entered; enter actions on that path
       and plain composite ``during before`` are not replayed.
     - ``abstract_hook_context_hot_start_*`` and ``design_multi_level_non_stoppable_*`` fixtures.
   * - Terminal/end handling
     - Exiting to the machine end empties the stack.  Later ``cycle()`` calls
       are no-ops, and ``current_state`` is no longer terminal-safe.
     - ``*_terminal_*`` and ``design_explicit_exit_to_root_*`` fixtures.

.. _exec-composite-entry-order:

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

.. _exec-during-aspect-order:

Aspect during actions
---------------------

``>> during before`` and ``>> during after`` are aspect actions contributed by
ancestor states to descendant leaf cycles.  They are different from plain
composite ``during before`` / ``during after`` blocks.

Pseudo states are automatic routing states.  They are not normal stoppable leaf
states, and ancestor aspect during actions do not execute for the pseudo states
inside a pseudo/combo routing chain.  The semantic effect of the whole chain is
validated as part of the surrounding transition path.

In a chain such as ``S1 -> P1 -> P2 -> S2``, ``P1`` and ``P2`` are routing
boundaries.  Their guard/effect decisions can affect which candidate path is
valid, but they do not create ordinary leaf ``during`` cycles and do not receive
ancestor aspect ``during`` actions as if they were real leaves.

.. _exec-combo-order:

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

Fixture evidence matrix
-----------------------

The semantic fixture suite is the executable evidence behind this page.  The
table intentionally names fixture families instead of individual assertions so
the explanation remains stable while tests add more focused cases.

.. list-table:: Fixture families and covered behavior
   :header-rows: 1

   * - Behavior family
     - Representative fixture pattern
     - What the family protects
   * - Lifecycle ordering
     - ``design_basic_*``, ``composite_initial_*``, ``cold_initial_*``
     - Cold entry, state entry, leaf ``during``, source ``exit``, target
       ``enter`` and composite initial transition order.
   * - Aspect actions
     - ``design_aspect_*``, ``design_multi_layer_aspect_*``, ``aspect_context_*``
     - Ancestor aspect before/after actions and the active-leaf metadata seen
       by handlers.
   * - Pseudo chains
     - ``design_pseudo_chain_*``, ``design_evented_pseudo_chain_*``
     - Automatic routing through pseudo states and recovery from invalid
       candidates.
   * - Combo routing
     - ``combo_transition_trigger_*``, ``combo_initial_*``
     - Expanded combo relay paths, guard/effect order, rollback, terminal
       validation, and aspect boundaries.
   * - Rollback
     - ``*_rollback_*``, ``composite_initial_skips_unstable_*``
     - Variable and stack rollback when speculative validation rejects a path.
   * - Hot start
     - ``abstract_hook_context_hot_start_*``, ``design_multi_level_non_stoppable_*``
     - Already-entered stack construction, variable requirements, and
       non-stoppable path rejection.
   * - Terminal/end handling
     - ``*_terminal_*``, ``design_explicit_exit_to_root_*``
     - End-state transitions, runtime termination, and terminal-safe queries.
   * - Abstract-handler context
     - ``abstract_handler_context_*``, ``abstract_hook_ref_context_*``
     - Read-only variable snapshots, callsite metadata, named references and
       active-leaf reporting.

Boundary with generated runtimes
--------------------------------

The simulator is the reference model-level executor used before code
generation.  Generated runtimes should be checked against the same scenarios,
but target languages may add platform constraints such as integer width or C/C++
deployment risk that do not apply to the Python simulator itself.  Use inspect
and generated-runtime tests when target-specific behavior matters.
