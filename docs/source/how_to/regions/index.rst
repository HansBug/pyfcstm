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
**Reference link**.  Download the models a card names into an empty directory
and run its commands there; the models of the tasks about order
(:download:`controller.fcstm </_models/controller.fcstm>` and
:download:`controller_swapped.fcstm </_models/controller_swapped.fcstm>`) are
the same ones the first tutorial uses.  A line starting with ``...`` in an
output stands for text that the card does not discuss.  The documentation
checks run every command and script on this page against the real
``pyfcstm``, so the outputs are what you get.

1. Split one state into two regions
-----------------------------------

**Input.** A flat machine whose leaf states are the product of two independent
concerns.  ``panel_flat.fcstm`` has four states (``CoolClosed``, ``CoolOpen``,
``HotClosed``, ``HotOpen``) and eight transitions; ``panel_regions.fcstm``
says the same with two regions of two states and four transitions.

.. literalinclude:: panel_flat.fcstm
   :language: fcstm
   :caption: panel_flat.fcstm

.. literalinclude:: panel_regions.fcstm
   :language: fcstm
   :caption: panel_regions.fcstm

**Command or code.** Run both models, and in the second cycle change both
inputs at once.  The first cycle (left out of the output) enters the initial
state:

.. code-block:: console

   $ pyfcstm simulate -i panel_flat.fcstm -e "\
   cycle --input hot=0 --input open=0; \
   cycle --input hot=1 --input open=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input hot=1 --input open=1
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Panel.HotClosed
   $ pyfcstm simulate -i panel_regions.fcstm -e "\
   cycle --input hot=0 --input open=0; \
   cycle --input hot=1 --input open=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input hot=1 --input open=1
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Panel{Temperature: Hot, Door: Open}

**Expected signal.** In the second cycle the flat machine takes one transition
(``HotClosed``) and misses the door, while the regions machine takes both
(``Panel{Temperature: Hot, Door: Open}``).  Each region
advances once per cycle, so splitting changes behavior when two concerns move in
the same cycle.  Check this difference before you split a machine whose
single-step behavior is relied on.

**File side effect.** None.  The commands read the two ``.fcstm`` files and
print to stdout.

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

.. code-block:: console

   $ pyfcstm simulate -i nested_cell.fcstm -e "\
   cycle --input go=0; \
   cycle --input go=1"
   ────────────────────────────────────────────────────────────
   >>> cycle --input go=0
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Plant{Line: Cell{Feed: Waiting, Cut: Ready}, Monitor: Watching}

   ────────────────────────────────────────────────────────────
   >>> cycle --input go=1
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Plant{Line: Cell{Feed: Pushing, Cut: Cutting}, Monitor: Watching}

**Expected signal.** The configuration text nests one block per owner:
``Plant{Line: Cell{Feed: Waiting, Cut: Ready}, Monitor: Watching}``.  The
inner owner is a state, so every path passes through the region name
(``Plant.Line.Cell.Feed.Waiting``), and both inner regions move in the cycle
where ``go`` becomes ``1``.

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

.. literalinclude:: scoped_event.fcstm
   :language: fcstm
   :caption: scoped_event.fcstm

**Command or code.**

The shared event first, then the bare name that is refused:

.. code-block:: console

   $ pyfcstm simulate -i shared_event.fcstm -e "\
   cycle; \
   cycle /Start"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle /Start
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Rig{Left: Busy, Right: Busy}
   $ pyfcstm simulate -i shared_event.fcstm -e "\
   cycle; \
   cycle Start"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle Start
   ────────────────────────────────────────────────────────────
   Cycle execution failed: Position-dependent event name 'Start' matches no event from any active leaf (Rig.Left.Idle, Rig.Right.Idle); use the full event path or a root-based "/path".
   $ echo $?
   1

Then the counterexample, where each region owns a ``Ping``:

.. code-block:: console

   $ pyfcstm simulate -i scoped_event.fcstm -e "\
   cycle; \
   cycle Rig.Left.Ping; \
   cycle Rig.Right.Ping"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle Rig.Left.Ping
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Rig{Left: Busy, Right: Idle}

   ────────────────────────────────────────────────────────────
   >>> cycle Rig.Right.Ping
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Rig{Left: Busy, Right: Busy}
   $ pyfcstm simulate -i scoped_event.fcstm -e "\
   cycle; \
   cycle Ping"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle Ping
   ────────────────────────────────────────────────────────────
   Cycle execution failed: Position-dependent event name 'Ping' matches no event from any active leaf (Rig.Left.Idle, Rig.Right.Idle); use the full event path or a root-based "/path".
   $ echo $?
   1

**Expected signal.** ``/Start`` moves both regions in one cycle.  In the
counterexample, ``Rig.Left.Ping`` and ``Rig.Right.Ping`` are two different
events: naming one moves one region, and the other region needs its own event.
A bare name (``Start``, ``Ping``) is refused with exit code 1 because it is
resolved from every live leaf and matches nothing.  A region-local ``: Name``
belongs to that region and is never looked up in the owner.

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

**Command or code.** Send ``/Start`` in the second cycle and raise ``fault``
in the fourth cycle (and in the fifth, for the swapped file).  The first three
cycles are left out of the output:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0
   $ pyfcstm simulate -i controller_swapped.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Controller.Running{Motion: On, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 5
   Current State: Controller.Running{Motion: Off, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

Then ask ``inspect`` which order is suspicious.  The line starting with
``diagnostics:`` counts the findings, and the swapped file has one more:

.. code-block:: console

   $ pyfcstm inspect -i controller.fcstm --color never
   ...
     diagnostics: 0 errors / 4 warnings / 0 infos
   ...
   $ pyfcstm inspect -i controller_swapped.fcstm --color never
   ...
     diagnostics: 0 errors / 4 warnings / 1 infos
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Controller.Running.Motion' reads variable 'permit', which is produced by the later region 'Controller.Running.Safety'; it sees the value from the previous cycle.
   ...

**Expected signal.** In ``controller.fcstm`` the fault cycle (cycle 4) already
shows ``permit = 0`` and ``motor = 0``.  In the swapped file the motor is still
``1`` in cycle 4 and goes to ``0`` one cycle later.  ``inspect`` counts no
information note for ``controller.fcstm`` and reports
``I_REGION_BACKWARD_READ`` for the swapped file; it is an information note, not
a defect.

**File side effect.** None.

**First failure check.** If a value arrives one cycle late, check the order of
the regions in the file before you change a guard.

**Reference link.** :doc:`/reference/inspect_report/index`.

5. Let regions finish together and move on
------------------------------------------

**Input.** ``join_done.fcstm``: each region ends with ``Run -> [*]``, and the
owner has an ordinary outgoing transition ``Work -> Next``.
``join_gate.fcstm`` adds a guard ``gate`` to that transition.

.. literalinclude:: join_done.fcstm
   :language: fcstm
   :caption: join_done.fcstm

.. literalinclude:: join_gate.fcstm
   :language: fcstm
   :caption: join_gate.fcstm

**Command or code.**

Let ``A`` finish first and ``B`` one cycle later:

.. code-block:: console

   $ pyfcstm simulate -i join_done.fcstm -e "\
   cycle --input a_ready=0 --input b_ready=0; \
   cycle --input a_ready=1 --input b_ready=0; \
   cycle --input a_ready=1 --input b_ready=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input a_ready=1 --input b_ready=0
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Job.Work{A: [done], B: Run}
   Variables:
     stage = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input a_ready=1 --input b_ready=1
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Job.Next
   Variables:
     stage = 1

Now the gated version, where ``gate`` stays ``0`` while ``B`` would finish:

.. code-block:: console

   $ pyfcstm simulate -i join_gate.fcstm -e "\
   cycle --input a_ready=1 --input b_ready=0 --input gate=0; \
   cycle --input a_ready=1 --input b_ready=1 --input gate=0; \
   cycle --input a_ready=1 --input b_ready=1 --input gate=0; \
   cycle --input a_ready=1 --input b_ready=1 --input gate=1"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle --input a_ready=1 --input b_ready=1 --input gate=0
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Job.Work{A: [done], B: Run}
   Variables:
     ticks = 2

   ────────────────────────────────────────────────────────────
   >>> cycle --input a_ready=1 --input b_ready=1 --input gate=0
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Job.Work{A: [done], B: Run}
   Variables:
     ticks = 3

   ────────────────────────────────────────────────────────────
   >>> cycle --input a_ready=1 --input b_ready=1 --input gate=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Job.Next
   Variables:
     ticks = 3

**Expected signal.** A finished region shows ``[done]`` and stays that way.
When the last region finishes, the owner continues in the same cycle
(``Job.Next``, with ``stage = 1``).  In ``join_gate.fcstm`` the guard is false
in the cycles where ``B`` would finish, so the last completion is refused:
``B`` stays in ``Run``, its ``during`` still runs (``ticks`` grows), ``A`` stays
``[done]``, and the machine never rests with every region done.  The event or condition that tried
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

.. literalinclude:: preempt_group.fcstm
   :language: fcstm
   :caption: preempt_group.fcstm

.. literalinclude:: preempt_blocked.fcstm
   :language: fcstm
   :caption: preempt_blocked.fcstm

**Command or code.** Finish ``A`` with ``/ADone``, then send ``/Cancel``:

.. code-block:: console

   $ pyfcstm simulate -i preempt_group.fcstm -e "\
   cycle; \
   cycle /ADone; \
   cycle /Cancel"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle /ADone
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Workflow.Job{A: [done], B: Working}
   Variables:
     __forced_0 = 0
     order = 1

   ────────────────────────────────────────────────────────────
   >>> cycle /Cancel
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Workflow.Idle
   Variables:
     __forced_0 = 0
     order = 123

Then the model whose forced transition points at a state that cannot be
entered:

.. code-block:: console

   $ pyfcstm simulate -i preempt_blocked.fcstm -e "\
   cycle; \
   cycle /Cancel"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle /Cancel
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Workflow.Job{A: [done], B: Working}
   Variables:
     __forced_0 = 1
     order = 1

The forced transition is shorthand.  Loading the model and printing it with
``to_ast_node()`` shows what each region really contains (the output is cut to
the parts this card discusses):

.. testcode::

   from pyfcstm.model import load_state_machine_from_file

   model = load_state_machine_from_file("preempt_group.fcstm")
   print(model.to_ast_node())

.. testoutput::

   ...
   def int __forced_0 = 0;
   ...
           region A {
   ...
               Working -> [*] : if [__forced_0 == 1];
               Working -> [*] : /Cancel effect {
                   __forced_0 = 1;
               }
   ...
           region B {
   ...
               Working -> [*] : if [__forced_0 == 1];
               Working -> [*] : /Cancel effect {
                   __forced_0 = 1;
               }
   ...

**Expected signal.** ``/Cancel`` leaves ``Job`` in one cycle and the exits run
in writing order: ``1`` (``A``), ``2`` (``B``), then the owner (``3``), so
``order = 123``.  A region that is already ``[done]`` does not exit again
(``order = 1`` after ``/ADone`` and still ``123`` at the end).  If the target
cannot be entered, the regions leave one after another until the last one:
``A`` becomes ``[done]`` and ``B`` keeps working, so the machine does not stop
on a half-left owner.  The expansion shows a hidden variable ``__forced_0`` and
an ordinary ``-> [*]`` in every region; that variable is printed with the other
variables of every cycle.

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

.. literalinclude:: watch_regions.fcstm
   :language: fcstm
   :caption: watch_regions.fcstm

**Command or code.**

.. code-block:: console

   $ pyfcstm simulate -i watch_regions.fcstm -e "\
   cycle --input go=0; \
   cycle --input go=1; \
   cycle --input go=1"
   ────────────────────────────────────────────────────────────
   >>> cycle --input go=0
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Plant{Earlier: Waiting, Trigger: Quiet, Later: Waiting}
   Variables:
     __active_Plant_Trigger_Fired = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input go=1
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}
   Variables:
     __active_Plant_Trigger_Fired = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input go=1
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Plant{Earlier: Saw, Trigger: Fired, Later: Saw}
   Variables:
     __active_Plant_Trigger_Fired = 1

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

.. literalinclude:: aspect_regions.fcstm
   :language: fcstm
   :caption: aspect_regions.fcstm

**Command or code.** The counters are printed after every cycle; the ``/End``
event is sent in the third cycle, and the first cycle is left out:

.. code-block:: console

   $ pyfcstm simulate -i aspect_regions.fcstm -e "\
   cycle; \
   cycle; \
   cycle /End; \
   cycle"
   ...
   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Plant.Run{Left: A, Right: B, Third: C}
   Variables:
     ancestor = 2
     left = 2
     right = 2
     work = 22

   ────────────────────────────────────────────────────────────
   >>> cycle /End
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Plant.Run{Left: [done], Right: B, Third: C}
   Variables:
     ancestor = 3
     left = 2
     right = 3
     work = 32

   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Plant.Run{Left: [done], Right: B, Third: C}
   Variables:
     ancestor = 4
     left = 2
     right = 4
     work = 42

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
reads the files as they are.  The seven models:

.. literalinclude:: err_cross_region.fcstm.txt
   :language: fcstm
   :caption: err_cross_region.fcstm.txt

.. literalinclude:: err_mixed_children.fcstm.txt
   :language: fcstm
   :caption: err_mixed_children.fcstm.txt

.. literalinclude:: err_empty_region.fcstm.txt
   :language: fcstm
   :caption: err_empty_region.fcstm.txt

.. literalinclude:: err_duplicate_region.fcstm.txt
   :language: fcstm
   :caption: err_duplicate_region.fcstm.txt

.. literalinclude:: err_active_region.fcstm.txt
   :language: fcstm
   :caption: err_active_region.fcstm.txt

.. literalinclude:: err_history_owner.fcstm.txt
   :language: fcstm
   :caption: err_history_owner.fcstm.txt

.. literalinclude:: err_region_in_region.fcstm.txt
   :language: fcstm
   :caption: err_region_in_region.fcstm.txt

**Command or code.** Run ``pyfcstm inspect -i err_<name>.fcstm.txt --color never``
on each model.  These are negative examples; do not copy the models.  Every
command exits with code 1:

.. code-block:: console

   $ pyfcstm inspect -i err_cross_region.fcstm.txt --color never
   Invalid state machine model in err_cross_region.fcstm.txt: Unknown to state 'Y' of transition:
   X -> Y; (line 5)
   $ echo $?
   1
   $ pyfcstm inspect -i err_mixed_children.fcstm.txt --color never
   Failed to parse input DSL file err_mixed_children.fcstm.txt: Found 2 errors during parsing:
   Error 1: Syntax error at line 4, column 4, near 'region': Unexpected token 'region'
   Error 2: Syntax error at line 8, column 0, near '}': Extra closing brace - check for mismatched braces
   $ echo $?
   1
   $ pyfcstm inspect -i err_empty_region.fcstm.txt --color never
   Invalid state machine model in err_empty_region.fcstm.txt: Invalid region structure at Root.R (empty_region). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i err_duplicate_region.fcstm.txt --color never
   Invalid state machine model in err_duplicate_region.fcstm.txt: Duplicate region 'R' in Root. (line 6)
   $ echo $?
   1
   $ pyfcstm inspect -i err_active_region.fcstm.txt --color never
   Invalid state machine model in err_active_region.fcstm.txt: Invalid active query 'Root.S' (region). (line 6)
   $ echo $?
   1
   $ pyfcstm inspect -i err_history_owner.fcstm.txt --color never
   Invalid state machine model in err_history_owner.fcstm.txt: Invalid region structure at Root.Owner (history_boundary). (line 3)
   $ echo $?
   1
   $ pyfcstm inspect -i err_region_in_region.fcstm.txt --color never
   Failed to parse input DSL file err_region_in_region.fcstm.txt: Found 3 errors during parsing:
   Error 1: Syntax error at line 3, column 8, near 'region': Unexpected token 'region'
   Error 2: Syntax error at line 3, column 21, near '{': Invalid syntax - check for missing semicolons, braces, or operators
   Error 3: Syntax error at line 7, column 8, near '[*]': Unexpected token '[*]'
   $ echo $?
   1

The table lists the mistake behind each report and its fix.

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

``pyfcstm inspect`` writes these failures to stderr and leaves stdout empty.

**Expected signal.** Every command exits with code 1 and prints one of the
reports above, as the block shows.

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
