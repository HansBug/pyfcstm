.. _sec-explanations-region-semantics:

How a cycle runs a model with regions
=====================================

A state that declares ``region`` blocks is an *owner*: its regions are all
active together, yet the machine still has one global cycle, one input sample
and one cycle counter. This page explains what the simulator does inside that
one cycle, why the results look the way they do, and which behaviours are
deliberate limits. It does not teach the syntax (see
:doc:`Your first model with regions </tutorials/regions/index>`), list the
accepted spellings (see :doc:`/reference/region_model/index`) or explain why the
language chose ordered regions (see
:doc:`Why regions run in order, and how other tools differ </explanations/region_design/index>`).
The execution rules of models without regions are in
:doc:`/explanations/execution_semantics/index`; everything there still holds
below a single region.

Every output on this page is the real output of the shipped simulator. The shared
semantic fixtures behind the claims are listed in
:ref:`region-semantics-evidence`.

Terms
-----

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Term
     - Meaning
   * - owner
     - A state that contains regions instead of ordinary child states.
   * - region
     - A named container inside an owner. Its states and events live in the
       path of the region, for example ``Controller.Running.Motion.On``.
   * - branch
     - One region together with the position it is in.
   * - configuration
     - The position of the whole machine as a tree: one path for a model
       without regions, plus one position per region below every owner.
   * - Done
     - A region that finished through a ``-> [*]`` transition written directly
       in it. Its configuration text is ``[done]``.
   * - Delta
     - A cycle in which no legal configuration can be reached. It commits
       nothing: positions and variables stay as they were, and the cycle still
       counts.
   * - waiting for initialization
     - A region that has not been entered yet. Its configuration text is
       ``[init]``.

The model used throughout
-------------------------

Most sections reuse one model, the interlock controller of the tutorial. The
``Safety`` region decides whether the motor is permitted, and the ``Motion``
region switches the motor on and off:

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

``fault`` and ``requested`` are inputs. ``permit`` is written by ``Safety`` and
read by ``Motion``, which is the dependency that makes the order of the two
regions matter. ``/Start`` enters ``Running``. ``!Running -> Idle : /Stop`` is a
forced transition of the owner; it is the subject of
:ref:`region-semantics-forced`. The hidden variable ``__forced_0`` that you see
in some outputs comes from it.

How to read the examples
------------------------

The commands and scripts on this page run in a directory that holds the
``.fcstm`` files shown here, and the scripts read them from the current
directory. Most examples print the configuration and the variables after each
cycle. When the order inside one cycle matters, the script asks the simulator
for the trace: ``cycle(..., trace=True)`` returns ``CycleResult.trace``, one
committed observation per step. This script prints the trace of the cycle that
handles ``/Start`` in the controller, with the value of ``permit`` after each
step:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   runtime.cycle([])
   result = runtime.cycle(["/Start"], trace=True)
   for entry in result.trace:
       where = entry.transition_label or entry.action_path or ".".join(entry.state_path)
       print(entry.kind, where, "permit =", entry.vars["permit"])
   print(runtime.configuration)

.. testoutput::

   state_exit Controller.Idle permit = 0
   transition Controller.Idle::0::Idle->Running permit = 0
   state_enter Controller.Running permit = 0
   transition Controller.Running.Safety::0::INIT_STATE->Watching permit = 0
   state_enter Controller.Running.Safety.Watching permit = 0
   action Controller.Running.Safety.Watching::on_durings::0 permit = 1
   transition Controller.Running.Motion::0::INIT_STATE->Off permit = 1
   state_enter Controller.Running.Motion.Off permit = 1
   action Controller.Running.Motion.Off::on_durings::0 permit = 1
   Controller.Running{Safety: Watching, Motion: Off}


* ``state_enter`` and ``state_exit`` mark a state joining or leaving the
  configuration. The ``enter`` and ``exit`` blocks of that state show up as
  ``action`` lines with ``on_enters`` or ``on_exits`` in the address.
* ``transition`` lines carry the label ``Scope::index::Source->Target``.
  ``INIT_STATE`` stands for the initial transition ``[*]`` of the scope, and
  the index is the position in the transition list of the source state.
* ``action`` lines carry ``state::collection::index``. ``on_durings`` is a
  ``during`` block, and ``on_during_aspects`` is a ``>> during before`` or
  ``>> during after`` block of the named scope.
* The last line is the configuration in which the machine rests after the
  cycle.

The command line shows the same configuration text. Three cycles of the
interlock controller end like this:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   cycle --input fault=0 --input requested=1; \
   cycle /Start --input fault=0 --input requested=1; \
   cycle --input fault=0 --input requested=1"
   ...
   Cycle: 3
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

The line ``Controller.Running{Safety: Watching, Motion: On}`` is a
configuration text: the owner, then one entry per region in written order. The
counter says ``Cycle: 3`` although two regions did work in each of the last two
cycles.

.. _region-semantics-one-cycle:

One cycle, one input sample, one count
--------------------------------------

**Claim.** A cycle advances every region of the active owners once, in written
order. All regions see the same inputs and the same event set, and the cycle
counter grows by one.

The trace of the second cycle is in the previous section. This script runs the
same four cycles and prints the trace of the third and of the fourth, the one
in which ``fault`` is raised:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   runtime.cycle([])
   runtime.cycle(["/Start"])
   for fault in (0, 1):
       result = runtime.cycle([], inputs={"fault": fault}, trace=True)
       print("cycle", runtime.cycle_count, "fault", fault)
       for entry in result.trace:
           where = entry.transition_label or entry.action_path or ".".join(entry.state_path)
           print(" ", entry.kind, where, "permit =", entry.vars["permit"], "motor =", entry.vars["motor"])

.. testoutput::

   cycle 3 fault 0
     action Controller.Running.Safety.Watching::on_durings::0 permit = 1 motor = 0
     state_exit Controller.Running.Motion.Off permit = 1 motor = 0
     transition Controller.Running.Motion.Off::2::Off->On permit = 1 motor = 0
     state_enter Controller.Running.Motion.On permit = 1 motor = 0
     action Controller.Running.Motion.On::on_durings::0 permit = 1 motor = 1
   cycle 4 fault 1
     action Controller.Running.Safety.Watching::on_durings::0 permit = 0 motor = 1
     state_exit Controller.Running.Motion.On permit = 0 motor = 1
     transition Controller.Running.Motion.On::2::On->Off permit = 0 motor = 1
     state_enter Controller.Running.Motion.Off permit = 0 motor = 1
     action Controller.Running.Motion.Off::on_durings::0 permit = 0 motor = 0


Read the four cycles from the top:

* **Cycle 1** is the first ``runtime.cycle([])`` of the script and is not
  printed. That ``Idle`` is active afterwards shows in cycle 2, which leaves it.
* **Cycle 2** carries ``/Start``. ``Idle`` is left, ``Running`` is entered, and
  then the regions start one after another: ``Safety`` takes its initial
  transition and runs its first ``during`` (``permit`` becomes 1) before
  ``Motion`` even takes its initial transition. ``Motion`` then enters ``Off``
  and runs ``Off``'s ``during`` in the same cycle.
* **Cycle 3** runs ``Safety``'s ``during`` first and then ``Motion``. ``Motion``
  finds ``permit != 0 && requested != 0`` and moves ``Off -> On``; ``On``'s
  ``during`` switches the motor on, in the same cycle.
* **Cycle 4** raises ``fault``. ``Safety`` clears ``permit`` first, then
  ``Motion`` reads the new value and moves ``On -> Off``.

The table below is the order inside one cycle. Each row is a promise that the
simulator keeps in every cycle; the right column points at where you can see it
in an output on this page.

.. list-table:: Order of one cycle at an owner whose regions all work
   :header-rows: 1
   :widths: 6 50 44

   * - Step
     - What runs
     - Where to see it
   * - 1
     - The inputs are sampled once and the events of the call are fixed for the
       whole cycle. Neither changes while regions run.
     - Every row of :ref:`region-semantics-visibility`.
   * - 2
     - Conditions of the first region's transitions are judged, on the values
       as they are now.
     - Cycle 3 and 4 above: ``Safety`` has no transition, so it goes straight
       to its ``during``.
   * - 3
     - The first ``during`` work below an owner is preceded by the owner's
       ``>> during before`` blocks and those of its ancestors, outermost first.
       They run once for the whole group, not once per region.
     - :ref:`region-semantics-aspects`.
   * - 4
     - Each region runs in written order: a transition (source ``exit``,
       ``effect``, target ``enter``) or the ``during`` of its resting leaf. A
       region that is Done does nothing.
     - Cycles 3 and 4 above.
   * - 5
     - The region's own ``>> during after`` runs when its branch ends, so the
       next region sees what it wrote.
     - :ref:`region-semantics-aspects`.
   * - 6
     - The ``>> during after`` blocks of the owner and its ancestors run once,
       innermost first, after the last region.
     - :ref:`region-semantics-aspects`.
   * - 7
     - The cycle counter increases by one and the history entry records the
       resulting configuration.
     - The ``Cycle:`` line of the command line output above.

Here is ``controller_swapped.fcstm``, used from here on. It is the controller of
the previous sections with the two regions written in the other order: ``Motion``
(line 12) now comes before ``Safety`` (line 19), and nothing else differs.

.. literalinclude:: /_models/controller_swapped.fcstm
   :language: fcstm
   :caption: ``controller_swapped.fcstm``
   :emphasize-lines: 12,19

**What the order is made of.** Regions run in written order because the order
of the ``region`` blocks is part of the model: ``to_ast_node()``, formatting and
re-loading keep it. The script loads ``controller_swapped.fcstm``, the
controller with the two regions written in the other order
(shown above), exports it with
``to_ast_node()`` and loads the exported text again. Both models list the
regions of ``Running`` in the order they were written:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   again = load_state_machine_from_text(str(model.to_ast_node()))
   for item in (model, again):
       print(list(item.root_state.substates["Running"].regions))

.. testoutput::

   ['Motion', 'Safety']
   ['Motion', 'Safety']


**What this does not say.** Regions are not threads and they are not scheduled.
Nothing about the order depends on timing, and there is no way to run two
regions "at the same moment".

.. _region-semantics-visibility:

What a later region sees
------------------------

**Claim.** A region that comes later in the text reads what earlier regions
wrote in this cycle, and the states they entered. An earlier region never runs
again because a later one wrote something; it sees the later one's values one
cycle later. When several regions write the same variable, the last write wins.

.. literalinclude:: visible_forward.fcstm
   :language: fcstm
   :caption: ``visible_forward.fcstm``: the writer is declared first

.. literalinclude:: visible_backward.fcstm
   :language: fcstm
   :caption: ``visible_backward.fcstm``: the reader is declared first

.. literalinclude:: multi_writer.fcstm
   :language: fcstm
   :caption: ``multi_writer.fcstm``: three regions write the same variables

The script runs three cycles of each model and prints the variables after every
cycle:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("visible_forward", "visible_backward", "multi_writer"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for _ in range(3):
           runtime.cycle([])
           print(name, runtime.cycle_count, dict(runtime.vars))

.. testoutput::

   visible_forward 1 {'x': 1, 'y': 1}
   visible_forward 2 {'x': 2, 'y': 2}
   visible_forward 3 {'x': 3, 'y': 3}
   visible_backward 1 {'x': 1, 'y': 0}
   visible_backward 2 {'x': 2, 'y': 1}
   visible_backward 3 {'x': 3, 'y': 2}
   multi_writer 1 {'x': 2, 'y': 13}
   multi_writer 2 {'x': 2, 'y': 143}
   multi_writer 3 {'x': 2, 'y': 1443}


* In the forward model ``y`` equals ``x`` in every line: ``Rd`` copies the value
  that ``W`` just wrote.
* In the backward model ``y`` is always one behind: ``Rd`` runs before ``W`` and
  copies last cycle's ``x``. ``W`` is not re-run to make up for it.
* In the multiple-writer model the regions write ``x = 1`` (in ``R1``),
  ``x = 2`` (in ``R2``) and the chain ``y + 1``, ``y * 10``, ``y + 3`` runs in
  written order, so ``x`` ends at 2 and ``y`` goes 13, 143, 1443. Nothing is
  reported and nothing rolls back.

In the next model both regions add the same input ``k`` in each cycle:

.. literalinclude:: sampled_once.fcstm
   :language: fcstm
   :caption: ``sampled_once.fcstm``: two regions read the same input

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("sampled_once.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"k": 0})
   for k in (2, 3):
       runtime.cycle([], inputs={"k": k})
       print("k =", k, dict(runtime.vars))

.. testoutput::

   k = 2 {'a': 2, 'b': 2}
   k = 3 {'a': 5, 'b': 5}


``a`` and ``b`` are equal: 2 after the first cycle and 5 after the second. The
output shows the consequence of the single sample; it cannot show the sampling
itself. That contract is the one of ``SimulationRuntime.cycle``: every input
source is read once per cycle and the snapshot is shared by every guard and
action of the cycle.

**The interlock, both orders.** The controller is the example where the order
changes observable behaviour. The same input sequence runs against the model
with ``Safety`` first and against the swapped model with ``Motion`` first
(cycles 4 to 7 are printed; ``fault`` is 1 in cycles 4 and 5):

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("controller", "controller_swapped"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
       for events in (None, ["/Start"], None):
           runtime.cycle(events)
       for fault in (1, 1, 0, 0):
           runtime.cycle([], inputs={"fault": fault})
           print(name, runtime.cycle_count, "fault", fault, end=" ")
           print("permit", runtime.vars["permit"], "motor", runtime.vars["motor"])

.. testoutput::

   controller 4 fault 1 permit 0 motor 0
   controller 5 fault 1 permit 0 motor 0
   controller 6 fault 0 permit 1 motor 1
   controller 7 fault 0 permit 1 motor 1
   controller_swapped 4 fault 1 permit 0 motor 1
   controller_swapped 5 fault 1 permit 0 motor 0
   controller_swapped 6 fault 0 permit 1 motor 0
   controller_swapped 7 fault 0 permit 1 motor 1


Look at cycle 4, where ``fault`` becomes 1. With ``Safety`` first ``permit``
drops to 0 and the motor is switched off in the same cycle. With ``Motion``
first the motor still runs (``motor 1``) while ``permit`` is already 0; it goes
off one cycle later. Recovery is also one cycle later in the swapped model
(cycle 7 against cycle 6). Both machines are correct programs; they are
different programs. That is why the order is part of the language and why
:doc:`the design page </explanations/region_design/index>` calls it semantics.

This script prints the swapped model's fault cycle step by step. ``Motion``'s
``during`` runs first and still sees ``permit = 1``; ``Safety`` changes
``permit`` afterwards:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for events in (None, ["/Start"], None):
       runtime.cycle(events)
   result = runtime.cycle([], inputs={"fault": 1}, trace=True)
   for entry in result.trace:
       print(entry.action_path, "permit =", entry.vars["permit"])

.. testoutput::

   Controller.Running.Motion.On::on_durings::0 permit = 1
   Controller.Running.Safety.Watching::on_durings::0 permit = 0


**What this does not say.** The values a region reads are the values at its turn,
not "the values at the start of the cycle". There is no double buffering. If you
need a snapshot of the previous cycle, copy the variable yourself in a region
that runs first.

.. _region-semantics-completion:

Done, joint completion and resting
----------------------------------

**Claim.** A region finishes when a transition ``X -> [*]`` written directly
inside it is taken; it is then Done and waits. A Done region runs no ``during``.
The cycle in which the last region finishes continues through the owner's own
outgoing transitions immediately. If that continuation cannot be committed, the
last completion is refused and the region stays in its leaf.

.. literalinclude:: job_join.fcstm
   :language: fcstm
   :caption: ``job_join.fcstm``

``Job`` has two regions that finish on events. ``Job -> AwaitPermission`` is an
ordinary transition of the owner and it has no guard.

**Normal joint completion.** Four cycles; ``ADone`` arrives in cycle 2 and
``BDone`` in cycle 4:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("job_join.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"proceed": 0})
   for events in (None, ["/ADone"], None, ["/BDone"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Workflow.Job{A: Working, B: Working} {'a': 1, 'b': 1, 'aexit': 0, 'w': 0, '__forced_0': 0}
   2 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 2, 'aexit': 1, 'w': 0, '__forced_0': 0}
   3 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 3, 'aexit': 1, 'w': 0, '__forced_0': 0}
   4 Workflow.AwaitPermission {'a': 1, 'b': 3, 'aexit': 1, 'w': 1, '__forced_0': 0}


* Cycle 2: ``ADone`` finishes region ``A``. Its ``exit`` ran (``'aexit': 1``) and
  the configuration shows ``A: [done]``. Region ``B`` keeps working (``'b': 2``).
* Cycle 3: ``A`` is Done and does not run (``'a'`` stays 1, ``'aexit'`` stays 1);
  ``B`` works (``'b': 3``).
* Cycle 4: ``BDone`` finishes ``B``, which is the last region. In the same cycle
  the owner takes ``Job -> AwaitPermission`` and ``AwaitPermission`` runs its
  ``during`` (``'w': 1``). The machine never rests in "all regions Done".

**A refused last completion.** In ``job_rejected.fcstm`` the owner's outgoing
transition is ``Job -> Ready : if [proceed != 0]``; everything else is as above.

.. literalinclude:: job_rejected.fcstm
   :language: fcstm
   :caption: ``job_rejected.fcstm``

The script sends ``ADone`` in cycle 2, ``BDone`` in cycle 3 while ``proceed`` is
0, nothing in cycle 4 while ``proceed`` is 1, and ``BDone`` again in cycle 5 with
``proceed`` 1:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("job_rejected.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"proceed": 0})
   for events, proceed in ((None, 0), (["/ADone"], 0), (["/BDone"], 0), (None, 1), (["/BDone"], 1)):
       runtime.cycle(events, inputs={"proceed": proceed})
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Workflow.Job{A: Working, B: Working} {'a': 1, 'b': 1, 'aexit': 0, 'w': 0, '__forced_0': 0}
   2 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 2, 'aexit': 1, 'w': 0, '__forced_0': 0}
   3 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 3, 'aexit': 1, 'w': 0, '__forced_0': 0}
   4 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 4, 'aexit': 1, 'w': 0, '__forced_0': 0}
   5 Workflow.Ready {'a': 1, 'b': 4, 'aexit': 1, 'w': 0, '__forced_0': 0}


* Cycle 3: ``BDone`` arrives but ``proceed`` is 0, so the owner could not leave.
  The completion is refused as a whole: ``B`` stays in ``Working``, its
  ``during`` runs (``'b': 3``) and the event is not kept for the next cycle.
* Cycle 4: ``proceed`` is 1 but there is no event, so nothing finishes.
* Cycle 5: ``BDone`` and ``proceed`` 1 together finish ``B`` and the owner
  continues to ``Ready``.

**Completion through levels.** The rule is applied at every level of nesting,
and an outer sibling cannot stand in for an inner owner. In ``nested_join.fcstm``
the inner group ``Q{A1, A2}`` finishes in cycle 3 and its owner region ``A``
continues through ``Q -> R`` in the same cycle while region ``B`` of the outer
owner keeps working (``n`` keeps counting). The inner owner does not wait for
``B``.

.. literalinclude:: nested_join.fcstm
   :language: fcstm
   :caption: ``nested_join.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_join.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["/D1"], ["/D2"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: Q{A1: W1, A2: W2}, B: N} {'n': 1}
   2 Root.P{A: Q{A1: [done], A2: W2}, B: N} {'n': 2}
   3 Root.P{A: R, B: N} {'n': 3}
   4 Root.P{A: R, B: N} {'n': 4}


In ``nested_rejected.fcstm`` the inner region may finish only when the
continuation of every level above it can commit. ``Inner -> [*]`` needs ``ok1``
and ``P -> After`` needs ``ok2``.

.. literalinclude:: nested_rejected.fcstm
   :language: fcstm
   :caption: ``nested_rejected.fcstm``

With only one of them true (the first two lines) the machine does not move at
all; with both (the last line) it ends in ``Root.After``:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_rejected.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"ok1": 0, "ok2": 0})
   for ok1, ok2 in ((1, 0), (0, 1), (1, 1)):
       runtime.cycle(["/Finish"], inputs={"ok1": ok1, "ok2": ok2})
       print(runtime.cycle_count, "ok1", ok1, "ok2", ok2, runtime.configuration)

.. testoutput::

   1 ok1 1 ok2 0 Root.P{Outer: Inner{IR: W}}
   2 ok1 0 ok2 1 Root.P{Outer: Inner{IR: W}}
   3 ok1 1 ok2 1 Root.After


**Why the rule is this strict.** A branch may only rest at a non-pseudo leaf or at
Done, and an active owner needs at least one region still working. Together
these exclude an owner that is "finished but still there". The cost is the
refusal above: a completion that has nowhere to go does not happen. A
consequence worth knowing: an owner with a single region behaves like an
ordinary composite state and finishes when its region finishes; and a root
state that is an owner ends the machine when its last region finishes.

**What this does not say.** The refused completion is not a Delta. The cycle
commits, the other work of the cycle stays, and only the completion step is
dropped.

Starting a group
----------------

**Claim.** Entering an owner enters every region, in written order, each at its
first possible entry. If a later region cannot find a legal entry, the whole
entry is refused; the earlier regions do not choose again. The owner's own
``enter``, ``during before``, ``during after`` and ``exit`` run once around the
group, not once per region.

.. literalinclude:: owner_actions.fcstm
   :language: fcstm
   :caption: ``owner_actions.fcstm``

``seq`` records the order of the blocks as digits: 1 is the owner's ``enter``,
2 its ``during before``, 3 its ``during after``, 4 its ``exit``, 5 and 6 are
the ``enter`` and ``exit`` of ``A1`` and 7 and 8 those of ``B1``. Cycle 3
carries ``/Stop``:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("owner_actions.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, None, ["/Stop"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, "seq =", runtime.vars["seq"])

.. testoutput::

   1 Root.P{A: A1, B: B1} seq = 1257
   2 Root.P{A: A1, B: B1} seq = 1257
   3 Root.Off seq = 12576834


**Owner lifecycle.**

* Cycle 1: ``P``'s ``enter`` (digit 1) runs once. Region ``A`` takes its initial
  transition, then ``P``'s plain ``during before`` (digit 2) runs, and only then
  ``A1`` is entered (digit 5). The ``during before`` of an owner belongs to the
  initialization of the whole group: it runs once, after the first initial
  transition and before the first real state is entered. Then ``B`` starts
  (digit 7).
* Cycle 2: nothing runs. The leaves have no ``during``, so there is no
  ``during`` work, and the ``during before`` and ``during after`` blocks of the
  owner are tied to that work. Both are skipped in a cycle without it.
* Cycle 3: the forced transition takes the group away. The regions leave in
  written order (6 for ``A1``, 8 for ``B1``), the owner's ``during after`` (3)
  runs on the committed path where the group hands control back, and the
  owner's ``exit`` (4) runs once, last.

**No backtracking into an earlier region.** Region ``R1`` of ``group_entry.fcstm``
has two initial candidates: ``[*] -> A`` writes ``k = 1`` and ``[*] -> B`` writes
``k = 2``. Region ``R2`` can only start when ``k == 2``. The first candidate of
``R1`` is taken, ``R2`` cannot start, and the group refuses the entry. The
machine does not go back and try ``R1``'s second candidate (which would have let
``R2`` start); instead the transition ``Idle -> P`` is dropped and the next
candidate, ``Idle -> Fallback``, runs. The output shows only the committed
result: ``k`` is still 0, because the rejected attempt left nothing behind.

.. literalinclude:: group_entry.fcstm
   :language: fcstm
   :caption: ``group_entry.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("group_entry.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["Root.Idle.Go"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.Idle {'k': 0}
   2 Root.Fallback {'k': 0}


**Why no backtracking.** Searching the product of every region's entries would
make the cost multiply with the number of regions and would make the result
depend on a search order that nobody wrote down. Taking the first entry of each
region keeps the cost proportional to the sum, and makes the rule easy to state
in the model: "first possible entry, in written order".

.. _region-semantics-candidates:

Candidates, fallback and Delta
------------------------------

**Claim.** A transition that cannot be entered gives way to the next candidate of
the same state, starting from where it started. The writes of earlier regions
in this cycle stay. If the cycle as a whole cannot reach a legal configuration,
it becomes a Delta and the whole cycle rolls back.

.. literalinclude:: candidate_fallback.fcstm
   :language: fcstm
   :caption: ``candidate_fallback.fcstm``

In cycle 2 region ``R1`` writes ``x = 2``. Then ``R2`` tries ``B -> C``, which
would add 10 to ``t``, but ``C``'s initial transition needs ``x > 100``, so ``C``
cannot be entered. The candidate is dropped with its effect, and ``B -> D`` runs.

.. literalinclude:: initial_fallback.fcstm
   :language: fcstm
   :caption: ``initial_fallback.fcstm``

The script runs two cycles of each model:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("candidate_fallback", "initial_fallback"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for _ in range(2):
           runtime.cycle([])
           print(name, runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   candidate_fallback 1 Root.P{R1: A, R2: B} {'x': 1, 't': 0}
   candidate_fallback 2 Root.P{R1: A, R2: D} {'x': 2, 't': 1}
   initial_fallback 1 Root.P{R: Plain} {'g': 0, 'leak': 0, 'picked': 1}
   initial_fallback 2 Root.P{R: Plain} {'g': 0, 'leak': 0, 'picked': 1}


* ``candidate_fallback.fcstm``: ``t`` is 1, not 11, because the dropped candidate
  leaves no effect behind, and ``x`` is 2 because ``R1``'s write from this cycle
  is not undone.
* ``initial_fallback.fcstm``: an initial candidate that starts a nested group
  and fails halfway is dropped as well; ``leak`` stays 0 although its ``enter``
  would have run, and the second candidate ``Plain`` is entered (``picked`` is 1).

In ``group_delta.fcstm`` region ``R2`` can start only while the input ``g`` is
not 0:

.. literalinclude:: group_delta.fcstm
   :language: fcstm
   :caption: ``group_delta.fcstm``

The script runs the model twice: ``cold`` starts from the beginning, ``hot``
starts with ``R1`` in ``A`` and ``R2`` still waiting for initialization. The
lines that begin with ``Cycle`` are the simulator's own notice of a Delta. The
notice goes to standard error, so the script prints with ``flush=True`` to keep
each notice next to the line it belongs to:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("group_delta.fcstm").read())
   cold = SimulationRuntime(model, input_source={"g": 0})
   hot = SimulationRuntime(
       model,
       input_source={"g": 0},
       initial_state="Root.P{R1: A, R2: [init]}",
       initial_vars={"n": 0},
   )
   for g in (0, 0, 1):
       for name, runtime in (("cold", cold), ("hot", hot)):
           result = runtime.cycle([], inputs={"g": g})
           print(name, runtime.cycle_count, "g =", g, runtime.configuration, end=" ", flush=True)
           print("n =", runtime.vars["n"], "delta =", result.delta, flush=True)

.. testoutput::

   Cycle 1 completed as Delta - State: Root; no stoppable successor was committed
   cold 1 g = 0 Root n = 0 delta = True
   Cycle 1 completed as Delta - State: Root.P{R1: A, R2: [init]}; no stoppable successor was committed
   hot 1 g = 0 Root.P{R1: A, R2: [init]} n = 0 delta = True
   Cycle 2 completed as Delta - State: Root; no stoppable successor was committed
   cold 2 g = 0 Root n = 0 delta = True
   Cycle 2 completed as Delta - State: Root.P{R1: A, R2: [init]}; no stoppable successor was committed
   hot 2 g = 0 Root.P{R1: A, R2: [init]} n = 0 delta = True
   cold 3 g = 1 Root.P{R1: A, R2: X} n = 1 delta = False
   hot 3 g = 1 Root.P{R1: A, R2: X} n = 1 delta = False


* Cold start: region ``R2`` cannot initialize while ``g`` is 0, so the machine
  cannot enter ``P`` at all. The cycle is a Delta: the configuration stays
  ``Root`` and the variables stay. In cycle 3 ``g`` is 1 and the group starts.
* Hot start with ``R2`` waiting: the cycle cannot initialize ``R2``, so even
  though ``R1`` could work, the whole cycle is a Delta and ``n`` stays 0. Only
  the cycle that can place ``R2`` commits ``R1``'s work.

**Why the cycle is the unit of the rollback.** There is no per-region
transaction. A cycle is the one thing that other tools see (inputs, outputs,
generated code), so it either happens fully or not at all. Individual candidates
inside it are tried on a copy; the first one that reaches a legal position wins.

**The limit.** Groups can re-enter each other inside one cycle. The simulator
stops a chain that nests or repeats more than 64 groups in one cycle with a
documented error. The script prints the model for two groups inside one another;
``nested_model`` repeats the same ``region R { ... state O { ... } }``
wrapper once more for each further group. It then starts a chain of 64 groups,
which works, and one of 65:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError


   def nested_model(groups):
       body = "region R { [*] -> L; state L; }"
       for _ in range(groups - 1):
           body = "region R {\n[*] -> O;\nstate O {\n%s\n}\n}" % body
       return "state Root {\n[*] -> P;\nstate P {\n%s\n}\n}" % body


   print(nested_model(2))
   for groups in (64, 65):
       machine = load_state_machine_from_text(nested_model(groups))
       try:
           SimulationRuntime(machine).cycle([])
           print(groups, "groups inside one another start")
       except SimulationRuntimeDfsError as error:
           print(groups, "groups:", error)

.. testoutput::

   state Root {
   [*] -> P;
   state P {
   region R {
   [*] -> O;
   state O {
   region R { [*] -> L; state L; }
   }
   }
   }
   }
   64 groups inside one another start
   65 groups: Group initialization nested deeper than the structural safety limit (64) within one cycle; the state machine either enters more than 64 groups inside one another or one after another in the same cycle, or re-enters a group without bound.


.. _region-semantics-aspects:

Aspects around regions
----------------------

**Claim.** ``>> during before`` and ``>> during after`` of an owner and its
ancestors run once per cycle around the whole group. Those declared inside a
region run only around that region's branch. A scope with no ``during`` work in
this cycle runs neither of them. Before and after nest in pairs.

.. literalinclude:: nested_aspects.fcstm
   :language: fcstm
   :caption: ``nested_aspects.fcstm``

Each ``seq`` digit marks one block: 1 and 9 are the ``before`` and ``after`` of
``P``, 2 and 8 those of region ``A``, 3 and 7 those of ``Q``, and 4, 5, 6 the
``during`` blocks of ``X1``, ``Y1``, ``B1``. The script prints ``seq`` after two
cycles:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_aspects.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(2):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.vars["seq"])

.. testoutput::

   1 123457869
   2 123457869123457869


Cycle 1 appends the digits 1 2 3 4 5 7 8 6 9 and cycle 2 appends the same nine
digits again, which is the order of a cycle in which all regions rest: the
outermost ``before`` first, then each inner one, the ``during`` blocks of ``X1``
and ``Y1`` (``Q``'s branches), the ``after`` of ``Q`` (7) and of ``A`` (8) when
region ``A``'s branch ends, then region ``B`` (6), and finally ``P``'s ``after``
(9) once. Region ``B`` declares no aspect, so the ``before`` of ``A`` (2) does
not appear around it. Cycle 1 shows the same order during entry.

**Where a** ``before`` **sits.** It is placed right before the first ``during``
work below its scope, after the conditions of the branches that were judged
earlier.

.. literalinclude:: aspect_position.fcstm
   :language: fcstm
   :caption: ``aspect_position.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("aspect_position.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(3):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{R1: S, R2: U} {'tick': 1, 'post': 1, 'own': 1}
   2 Root.P{R1: S, R2: V} {'tick': 2, 'post': 2, 'own': 2}
   3 Root.P{R1: T, R2: V} {'tick': 3, 'post': 3, 'own': 3}


In cycle 2 ``R1``'s condition ``tick >= 2`` is judged first and sees ``tick = 1``,
so ``R1`` stays in ``S``; then the root's ``before`` makes ``tick`` 2 and ``P``'s
``before`` runs; ``R2``'s condition, judged after them, sees ``tick = 2`` and
takes ``U -> V``. The root's ``after`` runs once at the end (``post``). ``R1``
follows in cycle 3.

An aspect declared in a region covers only that region and only its ``during``
work:

.. literalinclude:: region_aspect.fcstm
   :language: fcstm
   :caption: ``region_aspect.fcstm``

The script sends ``/End1`` in cycle 3:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("region_aspect.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, None, ["/End1"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{R1: A, R2: B} {'r1': 1, 'r1after': 1, 'r2': 1, 'a': 1, 'b': 1}
   2 Root.P{R1: A, R2: B} {'r1': 2, 'r1after': 2, 'r2': 2, 'a': 2, 'b': 2}
   3 Root.P{R1: [done], R2: B} {'r1': 2, 'r1after': 2, 'r2': 3, 'a': 2, 'b': 3}
   4 Root.P{R1: [done], R2: B} {'r1': 2, 'r1after': 2, 'r2': 4, 'a': 2, 'b': 4}


The ``before`` and ``after`` of ``R1`` run once in each of cycles 1 and 2
(``r1`` and ``r1after`` go 1, 2) and only around ``R1``'s branch, while ``R2``'s
own ``before`` runs in every cycle (``r2`` 1 to 4). In cycle 3 ``R1`` finishes
through ``A -> [*]``, which is not ``during`` work, so its aspects do not run
(``r1`` stays 2); from then on only ``R2``'s aspect continues.

**What this does not say.** Pseudo states on the way to a resting state do not
trigger aspects, as in models without regions.

.. _region-semantics-forced:

Forced transitions that reach regions
-------------------------------------

**Claim.** A forced transition ``!Owner -> Target`` whose source contains
regions is shorthand for ordinary ``-> [*]`` transitions inside every region.
Nothing in the simulator takes a group away at once. The event or condition is
judged by each region at its own turn, regions leave in written order and the
owner continues through its own transition when the last one is Done.

The model in ``forced_condition.fcstm`` has ``!P -> Off : if [x >= 2]``:

.. literalinclude:: forced_condition.fcstm
   :language: fcstm
   :caption: ``forced_condition.fcstm``

The machine that runs is what ``to_ast_node()`` prints:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text

   model = load_state_machine_from_text(open("forced_condition.fcstm").read())
   print(model.to_ast_node())

.. testoutput::

   def int x = 0;
   def int __forced_0 = 0;
   state Root {
       state P {
           region A {
               state A1 {
                   during {
                       x = x + 1;
                   }
               }
               A1 -> [*] : if [__forced_0 == 1];
               A1 -> [*] : if [x >= 2] effect {
                   __forced_0 = 1;
               }
               [*] -> A1;
           }
           region B {
               state B1;
               B1 -> [*] : if [__forced_0 == 1];
               B1 -> [*] : if [x >= 2] effect {
                   __forced_0 = 1;
               }
               [*] -> B1;
           }
       }
       state Off;
       P -> Off : if [__forced_0 == 1] effect {
           __forced_0 = 0;
       }
       P -> Off : if [x >= 2 && __forced_0 == 0];
       [*] -> P;
   }


* Each region gets two transitions to ``[*]``: a **starter** with the declared
  condition (``x >= 2``) whose effect raises ``__forced_0``, and, written in front
  of it, a **follower** that fires when the variable is already raised.
* The owner gets two transitions to ``Off``: one that waits for the raised
  variable and lowers it, which is the case after the group ended, and, behind
  it, the declared transition, kept for the case that control comes back to the
  owner without the variable raised.

Running it shows the three consequences. **The condition is judged at each
region's turn.**

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("forced_condition.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(3):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: A1, B: B1} {'x': 1, '__forced_0': 0}
   2 Root.P{A: A1, B: [done]} {'x': 2, '__forced_0': 1}
   3 Root.Off {'x': 2, '__forced_0': 0}


In cycle 2 ``A``'s ``during`` makes ``x`` 2 *after* ``A`` had its turn, so ``A``
carries on. ``B``, which comes later, sees ``x >= 2`` at its turn and finishes at
once (``B: [done]``, ``__forced_0`` is 1). ``A`` finishes in cycle 3, when it sees
the raised variable, and the owner leaves in the same cycle. The condition is
judged by each region at its own turn, which is why ``A`` and ``B`` come out
differently in the same cycle.

**Regions leave in written order.** This script runs the controller until
both regions work, sends ``/Stop`` and prints the states that are exited:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for events in (None, ["/Start"], None):
       runtime.cycle(events)
   result = runtime.cycle(["/Stop"], trace=True)
   for entry in result.trace:
       if entry.kind == "state_exit":
           print(".".join(entry.state_path))

.. testoutput::

   Controller.Running.Safety.Watching
   Controller.Running.Motion.On
   Controller.Running


``Safety`` leaves first, then ``Motion``, then the owner. In ``forced_nested.fcstm``
the owners are nested:

.. literalinclude:: forced_nested.fcstm
   :language: fcstm
   :caption: ``forced_nested.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("forced_nested.fcstm").read())
   runtime = SimulationRuntime(model)
   runtime.cycle([])
   for entry in runtime.cycle(["Root.Halt"], trace=True).trace:
       if entry.kind == "state_exit":
           print(".".join(entry.state_path))

.. testoutput::

   Root.Outer.R1.Inner.X.X1
   Root.Outer.R1.Inner.Y.Y1
   Root.Outer.R1.Inner
   Root.Outer.R2.Z1
   Root.Outer


``X1`` and ``Y1`` leave, then their owner ``Inner``, then ``Z1`` of the next
region, then ``Outer``. A nested owner leaves right after its own regions, and
exit actions of Done regions are not run twice.

**The variable is an ordinary variable.** ``__forced_0`` is raised only while the
group is leaving: it is 1 after cycle 2 above, and 0 again as soon as the owner
has left. It is visible in ``runtime.vars``.

**When the target cannot be entered.**

.. literalinclude:: forced_blocked.fcstm
   :language: fcstm
   :caption: ``forced_blocked.fcstm``

In ``forced_two_declarations.fcstm`` two declarations compete:

.. literalinclude:: forced_two_declarations.fcstm
   :language: fcstm
   :caption: ``forced_two_declarations.fcstm``

The script sends ``/Stop`` in cycles 2 and 4 of each model:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("forced_blocked", "forced_two_declarations"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for events in (None, ["Root.Stop"], None, ["Root.Stop"]):
           runtime.cycle(events)
           print(name, runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   forced_blocked 1 Root.P{A: A1, B: B1} {'seq': 1, '__forced_0': 0}
   forced_blocked 2 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_blocked 3 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_blocked 4 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_two_declarations 1 Root.P{A: A1, B: B1} {'never': 0, '__forced_0': 0, '__forced_1': 0}
   forced_two_declarations 2 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}
   forced_two_declarations 3 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}
   forced_two_declarations 4 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}


``!P -> Blocked`` cannot complete because ``Blocked``'s initial transition has a
guard that never holds. ``A`` finishes in cycle 2 and its ``exit`` runs
(``'seq': 18``), but the last region ``B`` keeps working with the variable raised
(``'__forced_0': 1``); the configuration ``P{A: [done], B: B1}`` rests, also after
the second ``/Stop``. The group leaves in the first cycle in which the target can
be entered. The ordinary ``P -> Other : /Stop`` is not taken: it needs the whole
group to finish first. The variable stays raised for as long as the target
cannot be entered.

In ``forced_two_declarations.fcstm`` the first declaration that is raised holds
the group; the second one is not tried in the meantime. In a model without
regions a target that cannot be entered makes the next declaration count
instead; the difference is a consequence of expanding with ordinary transitions
only, and it is a known gap (see
`issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_).

**It is shorthand, and it behaves like its expansion.** The model that runs and
the model loaded from its exported text take the same cycles. The script prints
the hidden variables each model marks, then the last cycle of the written model
and whether all five cycles are identical in both:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   written = load_state_machine_from_text(open("controller.fcstm").read())
   reloaded = load_state_machine_from_text(str(written.to_ast_node()))
   print(written.forced_variables, reloaded.forced_variables)


   def run(model):
       runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
       history = []
       for events in (None, ["/Start"], None, None, ["/Stop"]):
           runtime.cycle(events)
           history.append((str(runtime.configuration), dict(runtime.vars)))
       return history


   first, second = run(written), run(reloaded)
   print(first[-1], first == second)

.. testoutput::

   ('__forced_0',) ()
   ('Controller.Idle', {'permit': 1, 'motor': 0, '__forced_0': 0}) True


The exported text loads to a machine with an ordinary variable ``__forced_0``
and nothing marks it as forced any more (the empty tuple). Both machines produce
the same configuration and variables in every cycle. The same holds for hot
start, generated runtimes, bounded model checking and the verify pipeline: they
take the machine that runs. Drawings and the report of ``pyfcstm inspect`` show
the model as written, because they describe what you wrote.

**What this does not say.** The expansion does not reproduce every detail of other
tools, and the one known gap above (issue #591) is still open. See
:doc:`/explanations/region_design/index` for the comparison, and
:ref:`region-semantics-limits` for what remains.

.. _region-semantics-active:

``active()`` and the order of regions
-------------------------------------

**Claim.** ``active("Path")`` is true from the start of the state's ``enter`` to
the end of its ``exit``. During a transition's ``effect`` neither the source nor
the target is active. A region that runs later in the same cycle sees the
change at once; one that ran earlier sees it in the next cycle.

.. literalinclude:: active_query.fcstm
   :language: fcstm
   :caption: ``active_query.fcstm``

``active_query_swapped.fcstm`` is the same model with ``Motion`` written before
``Safety``:

.. literalinclude:: active_query_swapped.fcstm
   :language: fcstm
   :caption: ``active_query_swapped.fcstm``

The six variables record what ``active()`` answered at six places: ``exit_self``
and ``exit_other`` inside ``Normal``'s ``exit``, ``effect_source`` and
``effect_target`` inside the transition's ``effect``, ``enter_self`` and
``enter_other`` inside ``Tripped``'s ``enter``. The value 1 means active and 2
means not active. The script raises ``fault`` in cycle 2 and prints the
configuration and ``m`` of each cycle, then the six variables:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   probes = ("exit_self", "exit_other", "effect_source", "effect_target", "enter_self", "enter_other")
   for name in ("active_query", "active_query_swapped"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model, input_source={"fault": 0})
       for fault in (0, 1, 1):
           runtime.cycle([], inputs={"fault": fault})
           print(name, runtime.cycle_count, runtime.configuration, "m =", runtime.vars["m"])
       print({probe: runtime.vars[probe] for probe in probes})

.. testoutput::

   active_query 1 Root.P{Safety: Normal, Motion: Run} m = 1
   active_query 2 Root.P{Safety: Tripped, Motion: Stop} m = 1
   active_query 3 Root.P{Safety: Tripped, Motion: Stop} m = 1
   {'exit_self': 1, 'exit_other': 2, 'effect_source': 2, 'effect_target': 2, 'enter_self': 1, 'enter_other': 2}
   active_query_swapped 1 Root.P{Motion: Run, Safety: Normal} m = 1
   active_query_swapped 2 Root.P{Motion: Run, Safety: Tripped} m = 2
   active_query_swapped 3 Root.P{Motion: Stop, Safety: Tripped} m = 2
   {'exit_self': 1, 'exit_other': 2, 'effect_source': 2, 'effect_target': 2, 'enter_self': 1, 'enter_other': 2}


* ``exit_self`` 1, ``exit_other`` 2: inside ``Normal``'s ``exit``, ``Normal`` is
  still active and ``Tripped`` is not yet.
* ``effect_source`` 2, ``effect_target`` 2: during the effect the machine has
  left ``Normal`` and has not entered ``Tripped``.
* ``enter_self`` 1, ``enter_other`` 2: inside ``Tripped``'s ``enter``, ``Tripped``
  is active and ``Normal`` is not.
* With ``Safety`` first (first model), ``Motion`` sees ``Tripped`` in the cycle
  in which it was entered and stops at once (``m`` stays 1). With ``Motion``
  first (swapped model), ``Motion`` runs one more cycle (``m`` is 2) and stops
  in the next. The same one-cycle lag as for variables.

**How it works.** ``active()`` is shorthand for an ordinary flag:

.. literalinclude:: active_lowering.fcstm
   :language: fcstm
   :caption: ``active_lowering.fcstm``

The script prints the machine that runs, and the flag that
``StateMachine.active_variables`` computes for a position:

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text

   model = load_state_machine_from_text(open("active_lowering.fcstm").read())
   print(model.to_ast_node())
   print(model.active_variables(Configuration.parse(model, "Root.P{A: A2, B: B1}")))

.. testoutput::

   def int __active_Root_P_A_A2 = 0;
   state Root {
       state P {
           region A {
               state A1 {
                   event Go;
               }
               state A2 {
                   enter {
                       __active_Root_P_A_A2 = 1;
                   }
                   exit {
                       __active_Root_P_A_A2 = 0;
                   }
               }
               [*] -> A1;
               A1 -> A2 :: Go;
           }
           region B {
               state B1;
               state B2;
               [*] -> B1;
               B1 -> B2 : if [__active_Root_P_A_A2 != 0];
           }
       }
       [*] -> P;
   }
   {'__active_Root_P_A_A2': 1}


The model that runs has one hidden ``int`` variable per queried state. The flag
is set at the first line of ``enter`` and cleared at the last line of ``exit``,
which is what puts ``enter`` and ``exit`` blocks at the edges of the "active"
interval and nothing else. The queried state is never a region; naming one is an
error when the model is built. When ``Go`` moves region ``A`` to ``A2`` in cycle
2, region ``B`` reads the flag that region ``A`` raised in the same cycle:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("active_lowering.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["Root.P.A.A1.Go"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: A1, B: B1} {'__active_Root_P_A_A2': 0}
   2 Root.P{A: A2, B: B2} {'__active_Root_P_A_A2': 1}
   3 Root.P{A: A2, B: B2} {'__active_Root_P_A_A2': 1}


The flag is an ordinary variable everywhere: a hot start has to supply it
like every other variable, the runtime does not derive or check it against the
position, and ``StateMachine.active_variables(config)`` computes the values for
a position when you want them.

Configuration is a tree
-----------------------

**Claim.** The position of a machine with regions is a tree, and it has a short
text form that reads back into the same value. Every model has a
``runtime.configuration``; ``runtime.current_state`` is a ``State`` for models
without regions and a configuration for models with regions.

The script parses four texts of the controller and prints each result, or the
error that refuses it:

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text

   model = load_state_machine_from_text(open("controller.fcstm").read())
   for text, mode in [
       ("Controller.Running{Safety: [done], Motion: On}", "stable"),
       ("Controller.Running{Safety: [init], Motion: [init]}", "initialization"),
       ("Controller.Running", "stable"),
       ("Controller.Running{Safety: [done], Motion: [done]}", "stable"),
   ]:
       try:
           config = Configuration.parse(model, text, mode=mode)
       except ValueError as error:
           print("ValueError:", error)
       else:
           print(repr(config), [".".join(state.path) for state in config.leaves])

.. testoutput::

   Configuration(mode='stable', position='Controller.Running{Safety: [done], Motion: On}') ['Controller.Running.Motion.On']
   Configuration(mode='initialization', position='Controller.Running{Safety: [init], Motion: [init]}') []
   ValueError: Missing region in stable configuration for 'Controller.Running'.
   ValueError: All regions are Done at 'Controller.Running'.


* A state is a full dotted path. An owner is followed by ``{Region: position,
  ...}`` in written order. A position can itself be an owner with its own
  braces, so the text follows the tree.
* ``[done]`` is a finished region and ``[init]`` a region that has not been
  entered. ``leaves`` lists the states that carry the ``during`` work: a Done
  region has none.
* The three modes say what a text may describe: ``stable`` is a position a
  machine can rest in; ``initialization`` is a whole owner that has not started;
  ``transient`` also allows pseudo states and partly started groups, which is
  what handlers see in the middle of a cycle. A stable position must list every
  region, and it must not have every region Done, as the two errors show.
* ``str(config)`` is the text; ``repr(config)`` also shows the mode.

A runtime reports its position the same way, before and after the first cycle:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   print(repr(runtime.configuration))
   runtime.cycle([])
   print(repr(runtime.configuration), type(runtime.current_state).__name__)

.. testoutput::

   Configuration(mode='initialization', position='Controller')
   Configuration(mode='stable', position='Controller.Idle') Configuration


Hot start
---------

**Claim.** A hot start places what the text names and leaves everything else to
initialize in the first cycle, in written order. Nothing placed is entered
again.

The script starts the controller from four different texts, runs one cycle and
prints the configuration afterwards and the states that the cycle entered:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   variables = {"permit": 1, "motor": 0, "__forced_0": 0}
   for text in (
       "Controller.Running{Safety: Watching, Motion: Off}",
       "Controller.Running{Safety: [done], Motion: On}",
       "Controller.Running.Motion.On",
       "Controller.Running",
   ):
       runtime = SimulationRuntime(
           model,
           initial_state=text,
           initial_vars=variables,
           input_source={"fault": 0, "requested": 1},
       )
       result = runtime.cycle([], trace=True)
       entered = [".".join(e.state_path) for e in result.trace if e.kind == "state_enter"]
       print(text, "->", runtime.configuration, entered)

.. testoutput::

   Controller.Running{Safety: Watching, Motion: Off} -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Motion.On']
   Controller.Running{Safety: [done], Motion: On} -> Controller.Running{Safety: [done], Motion: On} []
   Controller.Running.Motion.On -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Safety.Watching']
   Controller.Running -> Controller.Running{Safety: Watching, Motion: Off} ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']


* **Every leaf named.** ``Safety`` and ``Motion`` are in place, and the cycle
  does not enter ``Watching`` or ``Off`` again. The regions just work, and
  ``Motion`` moves ``Off -> On`` because ``permit`` was given as 1; ``On`` is the
  only state entered.
* **A region Done.** ``Safety: [done]`` stays done and runs nothing; only
  ``Motion`` does, and nothing is entered.
* **A path into a region** (``Controller.Running.Motion.On``). The other region
  starts waiting (``Safety: [init]``). In the cycle ``Safety`` takes its initial
  transition and enters ``Watching``, in written order before ``Motion``'s
  ``during``. The path keeps only the branch it goes through.
* **The owner alone.** The group waits as a whole and both regions initialize in
  written order, ``Safety`` and then ``Motion``; compare the trace of entering
  ``Running`` in the first sections.

The same text works on the command line:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; \
   cycle --input fault=1 --input requested=1"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialized from state: Controller.Running{Safety: Watching, Motion: On}
   Cycle: 0
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

So do the two refusals. **All regions Done** is refused with ``All regions are
Done``, at any depth of nesting: a finished owner has nowhere to rest. **A missing
variable** is refused too. Hidden variables such as ``__forced_0`` are ordinary
variables and the caller supplies them with the others; nothing is derived from
the position. Both commands exit with status ``1``:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=1 __forced_0=0"
   ...
   Initialization failed: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm -e "init Controller.Running{Safety: Watching, Motion: Off} permit=1 motor=0"
   ...
   Error: All variables must be provided. Missing: ['__forced_0']
   Available variables: ['__forced_0', 'motor', 'permit']
   $ echo $?
   1

A waiting region that cannot reach a legal position makes the cycle a Delta, as
in the previous section on candidates. ``initial_state`` also accepts a
``Configuration`` object, a tuple path and a ``State`` of a model without
regions; a hot start is not equivalent to replaying the history from the cold
start, because no ``enter`` ran.

External event names
--------------------

**Claim.** A full path and a name that starts at the root mean the same wherever
the machine rests. A name that depends on the position is resolved once for every
active leaf, and the three outcomes are "none found", "one event" and
"different events". A bare name never searches upward.

.. literalinclude:: /_models/event_names.fcstm
   :language: fcstm
   :caption: ``event_names.fcstm``

The script starts the machine with both regions working, sends each name in a
cycle of its own, and finally sends ``Ping`` when ``Safety`` is Done:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("event_names.fcstm").read())
   both = "Controller.Running{Safety: Watching, Motion: Off}"
   one_done = "Controller.Running{Safety: [done], Motion: Off}"
   names = ["Go", "Trip", "Ping", "Stop", "Reset", "..Stop", "/Running.Stop", "Controller.Running.Motion.Off.Ping"]
   for name, start in [(name, both) for name in names] + [("Ping", one_done)]:
       runtime = SimulationRuntime(model, initial_state=start, initial_vars={"trail": 0})
       try:
           result = runtime.cycle([name])
       except ValueError as error:
           print(name, "refused:", error)
       else:
           print(name, "->", runtime.configuration, list(result.consumed_events))

.. testoutput::

   Go -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Motion.Off.Go']
   Trip -> Controller.Running{Safety: Tripped, Motion: Off} ['Controller.Running.Safety.Watching.Trip']
   Ping refused: Position-dependent event name 'Ping' is ambiguous: Controller.Running.Safety.Watching.Ping (from Controller.Running.Safety.Watching); Controller.Running.Motion.Off.Ping (from Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   Stop refused: Position-dependent event name 'Stop' matches no event from any active leaf (Controller.Running.Safety.Watching, Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   Reset refused: Position-dependent event name 'Reset' matches no event from any active leaf (Controller.Running.Safety.Watching, Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   ..Stop -> Controller.Running{Safety: Tripped, Motion: On} ['Controller.Running.Stop', 'Controller.Running.Stop']
   /Running.Stop -> Controller.Running{Safety: Tripped, Motion: On} ['Controller.Running.Stop', 'Controller.Running.Stop']
   Controller.Running.Motion.Off.Ping -> Controller.Running{Safety: Watching, Motion: Off} ['Controller.Running.Motion.Off.Ping']
   Ping -> Controller.Running{Safety: [done], Motion: Off} ['Controller.Running.Motion.Off.Ping']


* ``Go`` exists only below ``Motion``'s leaf, so only that leaf finds it and
  the event is used. ``Trip`` works the same for ``Safety``.
* ``Ping`` exists on both leaves with different meanings. The cycle is refused
  and the message lists every candidate with the leaf that led to it; nothing
  runs. The fix is the full path (``Controller.Running.Motion.Off.Ping``).
* ``Stop`` is an event of the owner ``Running``, and ``Reset`` an event of the
  root. A bare name is looked up only in the namespace of each active leaf, so
  neither is found. This is the rule models without regions have always had.
* ``..Stop`` counts levels up from each leaf and reaches the same event of the
  owner from both leaves, so the event is used and both regions move.
  ``/Running.Stop`` and the full path reach it from anywhere. The event appears
  twice in the consumed list, once for each transition it moved.
* With ``Safety`` Done (last line), there is only one active leaf, so ``Ping``
  is no longer ambiguous: Done regions and regions waiting for initialization do
  not take part.

**Why not broadcast.** Events with the same name in different places are different
events. Taking them together would make a model's behaviour depend on what happens
to be active; the model would change meaning when a region finishes. Resolving
once per leaf and failing on ambiguity keeps the choice visible to the writer.

Handler context
---------------

**Claim.** An abstract handler is told where it runs and what the machine looks
like at that moment. ``state_path`` and ``active_leaf`` are the deepest state
common to everything the action wraps: the leaf when it wraps one branch, the
owner when it wraps the whole group. ``configuration`` is the full position at
the time of the call.

.. literalinclude:: handler_context.fcstm
   :language: fcstm
   :caption: ``handler_context.fcstm``

The script registers a handler for each abstract action that prints its name,
``state_path``, ``active_leaf`` and ``configuration``, then runs three cycles:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   def report(name):
       def handler(context):
           print(name, ".".join(context.state_path), ".".join(context.active_leaf), context.configuration)
       return handler

   model = load_state_machine_from_text(open("handler_context.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for action in ("Controller.Tick", "Controller.Running.GroupPre", "Controller.Running.Safety.SafetyPre", "Controller.Running.Safety.Normal.Watch", "Controller.Running.Motion.On.Drive"):
       runtime.register_abstract_handler(action, report(action.split(".")[-1]))
   for events in (None, ["/Start"], None):
       print("cycle", runtime.cycle_count + 1)
       runtime.cycle(events)

.. testoutput::

   cycle 1
   Tick Controller.Idle Controller.Idle Controller.Idle
   cycle 2
   Tick Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: [init]}
   GroupPre Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: [init]}
   SafetyPre Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: [init]}
   Watch Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: [init]}
   cycle 3
   Tick Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: Off}
   GroupPre Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: Off}
   SafetyPre Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: Off}
   Watch Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: Off}
   Drive Controller.Running.Motion.On Controller.Running.Motion.On Controller.Running{Safety: Normal, Motion: On}


* ``Tick`` is declared on the root and wraps the whole machine: in
  ``Idle`` it reports ``Idle``; in ``Running`` (cycles 2 and 3) it reports the
  owner ``Running``, because it wraps both regions.
* ``SafetyPre`` belongs to region ``Safety`` and wraps only that branch, so it
  reports the leaf ``Running.Safety.Normal``. ``Watch`` is the leaf's own
  action.
* In cycle 2 the owner is being entered. ``Motion`` has not started yet, so the
  configuration shows ``Motion: [init]`` while ``Safety`` is already in
  ``Normal``. In cycle 3 ``Drive`` sees ``Motion: On``, because ``Motion`` moved
  ``Off -> On`` earlier in the same cycle.

The probing that happens before a candidate is committed calls no handler; only
the committed path does.

.. _region-semantics-evidence:

Evidence: which fixtures prove what
-----------------------------------

The semantic fixtures are shared data files that the simulator, the generated
Python runtime and, where the case allows it, the generated C-family runtimes
and the bounded model checker all run. The 118 cases whose names start with
``region_`` are grouped by theme below. The table names families by
case-name prefix and by one representative title; individual assertions are not
listed so that the page stays valid while cases are added.

.. list-table:: Region fixture families
   :header-rows: 1
   :widths: 24 8 34 34

   * - Family (case-name prefix)
     - Cases
     - What it proves
     - Section
   * - ``region_controller_*``, ``region_later_*``, ``region_earlier_*``,
       ``region_multiple_writers_*``, ``region_inputs_*``,
       ``region_parallel_leaves_*``, ``region_same_external_*``
     - 8
     - The interlock in both orders, forward and backward reads, last write
       wins, one input sample for all regions.
     - :ref:`region-semantics-one-cycle`, :ref:`region-semantics-visibility`
   * - ``region_done_*``, ``region_last_*``, ``region_indirect_*``,
       ``region_inner_group_*``, ``region_completion_*``,
       ``region_nested_group_*``, ``region_parallel_root_*``,
       ``region_groups_chained_*``, ``region_single_*``
     - 11
     - Done regions, joint completion, the refused last completion,
       completion through composites and nested owners, a single region equal to
       an ordinary composite state.
     - :ref:`region-semantics-completion`
   * - ``region_group_entry_*``, ``region_group_exit_*``,
       ``region_group_preemption_*``, ``region_group_reentry_*``,
       ``region_owner_*``, ``region_owners_*``, ``region_reentry_*``,
       ``region_three_nested_*``, ``region_group_reentered_*``,
       ``region_group_whose_*``, ``region_root_group_*``,
       ``region_that_finishes_*``
     - 21
     - Entry in written order without backtracking, owner ``enter`` / ``exit``
       once, plain ``during before`` and ``during after``, re-entry that resets
       regions but not variables, depth-first start of nested groups.
     - Starting a group
   * - ``region_candidate_*``, ``region_cold_start_*``, ``region_cycle_that_*``,
       ``region_initial_candidate_*``, ``region_unreachable_*``,
       ``region_looping_*``, ``region_loop_*``, ``region_unbounded_*``,
       ``region_group_that_could_*``, ``region_reentering_*``,
       ``region_start_with_*``
     - 14
     - Fallback to the next candidate, rollback of a rejected entry, the
       whole-cycle Delta, loops and the safety limit.
     - :ref:`region-semantics-candidates`
   * - ``region_after_*``, ``region_ancestor_*``, ``region_aspect_*``,
       ``region_aspects_*``, ``region_pseudo_states_*``
     - 7
     - Aspect counts and positions, nesting of ``before`` and ``after``, aspects
       of a region only around that region.
     - :ref:`region-semantics-aspects`
   * - ``region_forced_*``
     - 16
     - Forced transitions from owners, from regions and from ancestors, wildcard
       forms, conditions that become true half-way, unreachable targets,
       competing declarations.
     - :ref:`region-semantics-forced`
   * - ``region_active_*``
     - 3
     - ``active()`` in ``enter``, ``exit`` and ``effect``, in a later region and
       after a group is taken away.
     - :ref:`region-semantics-active`
   * - ``region_hot_start_*``
     - 17
     - Starts that name every leaf, a Done region, a path into a region or an owner
       alone; waiting and Done regions, nested owners, rejected
       positions and the supply of hidden variables.
     - Hot start
   * - ``region_event_name_*``, ``region_scoped_*``
     - 8
     - The three outcomes of a position-dependent name, Done regions not taking
       part, events scoped to their region.
     - External event names
   * - ``region_abstract_*``, ``region_leaf_abstract_*``, ``region_transient_*``,
       ``region_pseudo_state_enter_*``
     - 4
     - Handler contexts and the transient configuration texts during entry and
       completion.
     - Handler context
   * - ``region_actions_*``, ``region_history_*``, ``region_dead_*``,
       ``region_declared_*``, ``region_entry_*``, ``region_rejected_*``,
       ``region_choice_*``, ``region_combo_*``
     - 9
     - Temporaries and ``if`` blocks in region actions, history of a composite
       inside a region, pseudo state and combo transitions, and rejected
       candidates that leave no trace.
     - Candidates and the sections above

A case may support several sections; the table gives the main one. Families that
sit in the ``region_`` namespace but belong to the BMC, the generated runtimes
or the editors are documented on their own pages.

.. _region-semantics-limits:

Boundaries
----------

* **Nesting.** One cycle starts at most 64 groups inside one another or one
  after another. The error is a ``SimulationRuntimeDfsError`` (see the output
  in the section on candidates). It exists to stop unbounded re-entry; it is not
  a modelling budget.
* **No broadcast, no queue.** Events are inputs of the cycle. A region cannot
  send an event to another region, and nothing is delivered in a later step of
  the same cycle. Use a variable.
* **No jump between regions.** A transition cannot leave one region for a state
  of another, nor enter a region's state from outside the owner. Transitions end
  at the owner, which starts every region.
* **History of an owner.** An owner that has regions cannot declare history.
  History of a composite state inside a region works (see the history family).
* **Forced transitions.** The difference from models without regions (the
  next declaration when a target cannot be entered) is described in
  :ref:`region-semantics-forced`. The expansion adds a hidden variable
  to the model.
* **Comparison with other tools** (what a Stateflow user will notice, and the
  measured gaps) is on :doc:`the design page </explanations/region_design/index>`.
* **Known gaps and limits of the model** are collected in the "Limits and known
  gaps" section of :doc:`/reference/region_model/index`.
