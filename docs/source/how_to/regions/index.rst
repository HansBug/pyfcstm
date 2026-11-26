.. _sec-how-to-regions:

Region modeling tasks
=====================

Use this page when you already know what a region is and need to do one concrete
modeling task: split a state, nest regions, share an event, order regions,
join them, interrupt the whole group, read another region, add an aspect, or
repair a model that is refused.  For the first guided model, start with
:doc:`/tutorials/regions/index`.  For the reasoning behind each rule, see
:doc:`/explanations/region_semantics/index`.  For exact syntax and position
values, see :doc:`/reference/region_model/index`.

Every card states the same six facts: **Input**, **Command or code**,
**Expected signal**, **File side effect**, **First failure check** and
**Reference link**.  Every example model sits next to this page; run the
commands from the directory that holds ``index.rst``.  The outputs below come
from the ``*.demo.py`` and ``*.demox.sh`` files in that directory, so a rebuild
of the documentation regenerates them.

1. Split one state into two regions
-----------------------------------

**Input.** A flat machine whose leaf states are the product of two independent
concerns.  ``panel_flat.fcstm`` has four states (``CoolClosed``, ``CoolOpen``,
``HotClosed``, ``HotOpen``) and eight transitions; ``panel_regions.fcstm``
says the same with two regions of two states and four transitions.

.. literalinclude:: panel_regions.fcstm
   :language: fcstm
   :caption: panel_regions.fcstm

**Command or code.** Run both models over the same inputs and print the
configuration after every cycle:

.. literalinclude:: split_state.demo.py
   :language: python
   :caption: split_state.demo.py

.. literalinclude:: split_state.demo.py.txt
   :language: text

**Expected signal.** Both models agree on the cycles where only one input
changes.  In the second cycle both inputs change at once: the flat machine
takes one transition (``HotClosed``) and misses the door, while the regions
machine takes both (``Panel{Temperature: Hot, Door: Open}``).  Each region
advances once per cycle, so splitting changes behavior when two concerns move in
the same cycle.  Check this difference before you split a machine whose
single-step behavior is relied on.

**File side effect.** None.  The script reads the two ``.fcstm`` files and
prints to stdout.

**First failure check.** If the load fails, run
``pyfcstm inspect -i panel_regions.fcstm`` and read the first error; the usual
cause is a state left outside a region (an owner holds regions or substates,
never both, see task 9).

**Reference link.** :doc:`/reference/region_model/index`.

2. Nest regions through a state
-------------------------------

**Input.** ``nested_cell.fcstm``.  A region cannot hold another region
directly, so ``Line`` holds a state ``Cell`` and ``Cell`` owns the regions
``Feed`` and ``Cut``.

.. literalinclude:: nested_cell.fcstm
   :language: fcstm
   :caption: nested_cell.fcstm

**Command or code.**

.. literalinclude:: nest_regions.demo.py
   :language: python
   :caption: nest_regions.demo.py

.. literalinclude:: nest_regions.demo.py.txt
   :language: text

**Expected signal.** The configuration text nests one block per owner:
``Plant{Line: Cell{Feed: Waiting, Cut: Ready}, Monitor: Watching}``.  The
inner owner is a state, so every path passes through the region name
(``Plant.Line.Cell.Feed.Waiting``).  ``leaves`` lists the three live leaves and
``region_status`` of the inner region is ``live``.

**File side effect.** None.

**First failure check.** If you wrote ``region`` straight inside ``region``,
the parser stops at the inner keyword (task 9 shows the exact message).  Put a
state between the two.

**Reference link.** :doc:`/reference/region_model/index`.

3. Make two regions react to the same event
-------------------------------------------

**Input.** ``shared_event.fcstm`` declares ``event Start;`` on the owner and
both regions use ``/Start``.  ``scoped_event.fcstm`` is the counterexample:
each region declares its own ``Ping`` and uses ``: Ping``.

.. literalinclude:: shared_event.fcstm
   :language: fcstm
   :caption: shared_event.fcstm

**Command or code.**

.. literalinclude:: shared_events.demo.py
   :language: python
   :caption: shared_events.demo.py

.. literalinclude:: shared_events.demo.py.txt
   :language: text

**Expected signal.** ``/Start`` moves both regions in one cycle.  In the
counterexample, ``Rig.Left.Ping`` and ``Rig.Right.Ping`` are two different
events: naming one moves one region, and sending both moves both.  A bare name
(``Start``, ``Ping``) is refused because it is resolved from every live leaf
and matches nothing.  A region-local ``: Name`` belongs to that region and is
never looked up in the owner.

**File side effect.** None.

**First failure check.** If an event is refused, read the message: it lists the
active leaves it tried.  Write the full path or a root path (``/Start``) in the
model and in the call.

**Reference link.** :doc:`/reference/simulation/index`.

4. Decide the writing order of regions
--------------------------------------

**Input.** ``controller.fcstm`` (``Safety`` before ``Motion``) and
``controller_swapped.fcstm`` (the same regions in the other order).  Order is
execution order.  The rule of thumb: a region that reads what another region
writes goes after it (a forward dependency); a read of a later region's value
sees the previous cycle (a backward dependency).

**Command or code.** ``order_regions.demo.py`` sends ``/Start`` in the second
cycle and sets ``fault`` to 1 in cycles 4 and 5:

.. literalinclude:: order_regions.demo.py
   :language: python
   :caption: order_regions.demo.py

.. literalinclude:: order_regions.demo.py.txt
   :language: text

Then ask ``inspect`` which order
is suspicious:

.. literalinclude:: order_check.demo.sh
   :language: bash

.. literalinclude:: order_check.demo.sh.txt
   :language: text

**Expected signal.** In ``controller.fcstm`` the fault cycle (cycle 4) already
shows ``permit=0 motor=0``.  In the swapped file the motor is still ``1`` in
cycle 4 and goes to ``0`` one cycle later, and after the fault clears it comes
back one cycle late.  ``inspect`` prints nothing for ``controller.fcstm`` (the filter keeps only
region order diagnostics) and reports ``I_REGION_BACKWARD_READ`` for the
swapped file; it is an information note, not a defect.

**File side effect.** None.

**First failure check.** If a value arrives one cycle late, check the order of
the regions in the file before you change a guard.

**Reference link.** :doc:`/reference/inspect_report/index`.

5. Let regions finish together and move on
------------------------------------------

**Input.** ``join_done.fcstm``: each region ends with ``Run -> [*]``, and the
owner has an ordinary outgoing transition ``Work -> Next``.
``join_gate.fcstm`` adds a guard ``gate`` to that transition.

**Command or code.**

.. literalinclude:: join_regions.demo.py
   :language: python
   :caption: join_regions.demo.py

.. literalinclude:: join_regions.demo.py.txt
   :language: text

**Expected signal.** A finished region shows ``[done]`` and stays that way.
When the last region finishes, the owner continues in the same cycle
(``Job.Next``).  In ``join_gate.fcstm`` the guard is false in the cycles where
``B`` would finish, so the last completion is refused: ``B`` stays in ``Run``,
its ``during`` still runs (``ticks`` grows), ``A`` stays ``[done]``, and the
machine never rests with every region done.  The event or condition that tried
to finish ``B`` is not kept for the next cycle; with ``gate=1`` the machine
leaves in that cycle.

**File side effect.** None.

**First failure check.** If the owner does not move, check that every region has
a ``-> [*]`` that can fire and that the owner's outgoing guard can become true.
``inspect`` reports ``owner_never_completes`` when a region can never finish
(see the inspect page).

**Reference link.** :doc:`/reference/region_model/index`.

6. Interrupt the whole group from outside
-----------------------------------------

**Input.** ``preempt_group.fcstm``: a forced transition ``!Job -> Idle :
/Cancel`` on the owner, and ``exit`` actions that append a digit to ``order``.
``preempt_blocked.fcstm`` points the forced transition at a state that cannot be
entered.

**Command or code.** ``preempt_owner.demo.py`` runs the two models, sending
``/Cancel`` (and ``/ADone`` in the second run):

.. literalinclude:: preempt_owner.demo.py
   :language: python
   :caption: preempt_owner.demo.py

.. literalinclude:: preempt_owner.demo.py.txt
   :language: text

The forced transition is shorthand.  ``preempt_expansion.demo.py`` prints the
expanded model with ``to_ast_node()``; it shows what each region really contains:

.. literalinclude:: preempt_expansion.demo.py
   :language: python
   :caption: preempt_expansion.demo.py

.. literalinclude:: preempt_expansion.demo.py.txt
   :language: text

**Expected signal.** ``/Cancel`` leaves ``Job`` in one cycle and the exits run
in writing order: ``1`` (``A``), ``2`` (``B``), then the owner (``3``), so
``order=123``.  A region that is already ``[done]`` does not exit again (the
second run gives ``1`` at ``/ADone`` and still ``123`` at the end).  If the
target cannot be entered, the regions leave one after another until the last
one: ``A`` becomes ``[done]`` and ``B`` keeps working, so the machine does not
stop on a half-left owner.  The expansion shows a hidden variable
``__forced_0`` and an ordinary ``-> [*]`` in every region; that variable
appears in ``runtime.vars`` like any other.

**File side effect.** None.

**First failure check.** If nothing leaves, check that the event name is the
owner's event written as ``/Cancel`` and that the target state can be entered
from its initial transition.

**Reference link.** :doc:`/reference/dsl/index`.

7. Read the state of another region
-----------------------------------

**Input.** ``watch_regions.fcstm``: ``Trigger`` is declared between two
readers.  ``Later`` writes the path as ``active("/Trigger.Fired")`` and
``Earlier`` as ``active("Plant.Trigger.Fired")``; both name the same state.

**Command or code.**

.. literalinclude:: watch_regions.demo.py
   :language: python
   :caption: watch_regions.demo.py

.. literalinclude:: watch_regions.demo.py.txt
   :language: text

**Expected signal.** In the cycle where ``Trigger`` reaches ``Fired``, ``Later``
already shows ``Saw``; ``Earlier`` shows ``Saw`` one cycle later.  ``active()``
takes a state path (never a region path) and sees a state from the moment its
``enter`` begins to the moment its ``exit`` has finished.

**File side effect.** None.

**First failure check.** If the build fails with ``Invalid active query``,
you named a region; name a state inside it.  If the value is a cycle late,
the reader is declared before the writer.

**Reference link.** :doc:`/reference/region_model/index`.

8. Add an aspect to a region
----------------------------

**Input.** ``aspect_regions.fcstm``: ``Plant`` has an ancestor aspect
``>> during before``; ``Left`` and ``Right`` have their own region aspects.
``Left`` can finish with ``/End``; ``Right`` has a leaf with no ``during``
action.

**Command or code.** The script prints the counters after every cycle; the
``/End`` event is sent in the third cycle:

.. literalinclude:: aspect_regions.demo.py
   :language: python
   :caption: aspect_regions.demo.py

.. literalinclude:: aspect_regions.demo.py.txt
   :language: text

**Expected signal.** The ancestor aspect runs once per cycle although three
leaves work (``ancestor`` grows by one).  A region aspect runs once per cycle
for each region that has a leaf doing its ``during`` step, even if that leaf
declares no ``during`` action (``right`` grows every cycle).  ``left`` stops
growing in the cycle where ``Left`` finishes, and stays put while ``Left`` is
``[done]``.

**File side effect.** None.

**First failure check.** If a region aspect never runs, check that the region
is not ``[done]`` and has a leaf staying put in this cycle (a cycle in which the
leaf transitions runs no aspect of that region).

**Reference link.** :doc:`/reference/dsl/index`.

9. Diagnose common region errors
--------------------------------

**Input.** One small model per mistake, named ``err_*.fcstm.txt``.  The
suffix keeps the documentation build from drawing invalid models; ``pyfcstm``
reads the files as they are.  Two of them:

.. literalinclude:: err_cross_region.fcstm.txt
   :language: fcstm
   :caption: err_cross_region.fcstm.txt

.. literalinclude:: err_active_region.fcstm.txt
   :language: fcstm
   :caption: err_active_region.fcstm.txt

**Command or code.** Each ``err_*.demox.sh`` runs
``pyfcstm inspect -i err_<name>.fcstm.txt --color never``.  These are negative
examples; do not copy the models.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Mistake
     - Report
     - Fix
   * - A transition leaves its region (``err_cross_region``)
     - ``Invalid state machine model ...: Unknown to state 'Y' of transition:``
     - Move the transition inside one region, or end the region and let the owner decide
   * - Plain substates next to a region (``err_mixed_children``)
     - ``Failed to parse input DSL file ...: Found 2 errors during parsing:``
     - Wrap the plain states in a region, or drop the region
   * - A region without states (``err_empty_region``)
     - ``Invalid region structure at Root.R (empty_region).``
     - Add a state and ``[*] -> State;``, or delete the region
   * - Two regions with one name (``err_duplicate_region``)
     - ``Duplicate region 'R' in Root.``
     - Rename one region
   * - ``active()`` aimed at a region (``err_active_region``)
     - ``Invalid active query 'Root.S' (region).``
     - Name a state inside the region
   * - History on an owner that contains regions (``err_history_owner``)
     - ``Invalid region structure at Root.Owner (history_boundary).``
     - Remove ``[H]``, or keep history inside a plain subtree
   * - A region directly in a region (``err_region_in_region``)
     - ``Failed to parse input DSL file ...: Found 3 errors during parsing:``
     - Put a state between the regions

The full text and exit code of each report are in the generated files.  As an
example, ``err_cross_region.demox.sh``:

.. literalinclude:: err_cross_region.demox.sh.err
   :language: text

Exit code:

.. literalinclude:: err_cross_region.demox.sh.exitcode
   :language: text

The reports of the other six scripts are in ``err_mixed_children.demox.sh.err``,
``err_empty_region.demox.sh.err``, ``err_duplicate_region.demox.sh.err``,
``err_active_region.demox.sh.err``, ``err_history_owner.demox.sh.err`` and
``err_region_in_region.demox.sh.err``; ``pyfcstm inspect`` writes these failures
to stderr and leaves stdout empty.

**Expected signal.** Every command exits with code 1 and prints one of the
reports above.

**File side effect.** None.

**First failure check.** Fix the first reported line only, then run the command
again; later parse errors are often consequences of the first.

**Reference link.** :doc:`/reference/diagnostics_codes/index`.

Where the other tools' tasks are
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Task
     - Page
   * - Hot start, event names, "nothing happened" and the REPL
     - :doc:`/how_to/simulation/index`
   * - Order diagnostics and ``owner_never_completes``
     - :doc:`/how_to/inspect/index`
   * - Queries, local cases and cost
     - :doc:`/how_to/bmc/index`
   * - Generated runtimes and capacity macros
     - :doc:`/how_to/generation/index`
   * - A custom template that supports regions
     - :doc:`/how_to/templates/index`
   * - PlantUML, the viewer and layout
     - :doc:`/how_to/visualization/index`
   * - End-to-end acceptance of one model
     - :doc:`/how_to/cli_workflows/index`
