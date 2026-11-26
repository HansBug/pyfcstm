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

Every trace on this page is the output of the shipped simulator. The shared
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

How to read the traces
----------------------

A trace line is one committed observation of ``CycleResult.trace``. The
helper that prints them is a thin formatter,
:download:`region_trace.py <region_trace.py>`; the simulator calls are the
public ones:

.. code-block:: python

   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 0})
   result = runtime.cycle(["/Start"], inputs={"fault": 0, "requested": 1}, trace=True)
   for entry in result.trace:
       print(entry.kind, entry.state_path, dict(entry.vars))
   print(runtime.configuration)

* ``enter`` and ``exit`` mark a state joining or leaving the configuration.
  The ``enter`` and ``exit`` blocks of that state show up as ``do ... enter
  action`` and ``do ... exit action`` next to them.
* ``take`` is a transition, written ``source  label``; ``[*]->A`` is an initial
  transition and ``A->[*]`` finishes a region.
* ``do`` is a ``during`` block. ``aspect`` is a ``>> during before`` or
  ``>> during after`` block, named after the scope that declares it.
* ``[name a->b]`` after a line means that this block changed a variable.
* ``=>`` is the resting configuration after the cycle, with the variables.
* Paths are printed without the name of the root state.

The command line shows the same configuration text. Three cycles of the
interlock controller (the model below) end like this:

.. literalinclude:: cycle_cli.demo.sh
   :language: bash
   :caption: ``cycle_cli.demo.sh``

.. literalinclude:: cycle_cli.demo.sh.txt
   :language: text

The line ``Controller.Running{Safety: Watching, Motion: On}`` is a
configuration text: the owner, then one entry per region in written order. The
counter says ``Cycle: 3`` although two regions did work in each of the last two
cycles.

The model used throughout
-------------------------

Most sections reuse one model, the interlock controller of the tutorial. The
``Safety`` region decides whether the motor is permitted, and the ``Motion``
region switches the motor on and off:

.. literalinclude:: controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

``fault`` and ``requested`` are inputs. ``permit`` is written by ``Safety`` and
read by ``Motion``, which is the dependency that makes the order of the two
regions matter. ``/Start`` enters ``Running``. ``!Running -> Idle : /Stop`` is a
forced transition of the owner; it is the subject of
:ref:`region-semantics-forced`. The hidden variable ``__forced_0`` that you see
in some outputs comes from it.

.. _region-semantics-one-cycle:

One cycle, one input sample, one count
--------------------------------------

**Claim.** A cycle advances every region of the active owners once, in written
order. All regions see the same inputs and the same event set, and the cycle
counter grows by one.

.. literalinclude:: cycle_order.demo.py
   :language: python
   :caption: ``cycle_order.demo.py``

.. literalinclude:: cycle_order.demo.py.txt
   :language: text

Read the four cycles from the top:

* **Cycle 1** enters the root and ``Idle``. No region exists yet.
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
in a trace on this page.

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

**What the order is made of.** Regions run in written order because the order
of the ``region`` blocks is part of the model: ``to_ast_node()``, formatting and
re-loading keep it.

.. literalinclude:: order_kept.demo.py
   :language: python
   :caption: ``order_kept.demo.py``

.. literalinclude:: order_kept.demo.py.txt
   :language: text
   :caption: ``order_kept.demo.py`` (the script prints the region names of
      ``controller_swapped.fcstm`` in three places)

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

.. literalinclude:: visibility.demo.py
   :language: python
   :caption: ``visibility.demo.py``

.. literalinclude:: visibility.demo.py.txt
   :language: text

* In the forward model ``y`` equals ``x`` in every row: ``Rd`` copies the value
  that ``W`` just wrote.
* In the backward model ``y`` is always one behind: ``Rd`` runs before ``W`` and
  copies last cycle's ``x``. ``W`` is not re-run to make up for it.
* In the multiple-writer model the three regions write ``x = 1`` (in
  ``R1``), ``x = 2`` (in ``R2``) and the chain ``y + 1``, ``y * 10``, ``y + 3`` runs in
  written order, so ``x`` ends at 2 and ``y`` goes 13, 143, 1443. Nothing is
  reported and nothing rolls back.
* In the input model both regions add the same ``k`` in each cycle: 2 in cycle
  1 and 3 in cycle 2. The table shows the consequence of the single sample; it
  cannot show the sampling itself. That contract is the one of
  ``SimulationRuntime.cycle``: every input source is read once per cycle and the
  snapshot is shared by every guard and action of the cycle.

**The interlock, both orders.** The controller is the example where the order
changes observable behaviour. The same input sequence runs against the model
with ``Safety`` first and against the swapped model with ``Motion`` first:

.. literalinclude:: interlock.demo.py
   :language: python
   :caption: ``interlock.demo.py``

.. literalinclude:: interlock.demo.py.txt
   :language: text

Look at cycle 4, where ``fault`` becomes 1. With ``Safety`` first ``permit``
drops to 0 and the motor is switched off in the same cycle. With ``Motion``
first the motor still runs (``motor=1``) while ``permit`` is already 0; it goes
off one cycle later. Recovery is also one cycle later in the swapped model
(cycle 7 against cycle 6). Both machines are correct programs; they are
different programs. That is why the order is part of the language and why
:doc:`the design page </explanations/region_design/index>` calls it semantics.

The last block shows the swapped model's fault cycle line by line. ``Motion``'s
``during`` runs first and still sees ``permit=1``; ``Safety`` changes ``permit``
afterwards.

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

.. literalinclude:: completion.demo.py
   :language: python
   :caption: ``completion.demo.py``

.. literalinclude:: completion.demo.py.txt
   :language: text

**Normal joint completion** (first table).

* Cycle 2: ``ADone`` finishes region ``A``. Its ``exit`` ran (``aexit=1``) and
  the configuration shows ``A: [done]``. Region ``B`` keeps working (``b=2``).
* Cycle 3: ``A`` is Done and does not run (``a`` stays 1, ``aexit`` stays 1);
  ``B`` works (``b=3``).
* Cycle 4: ``BDone`` finishes ``B``, which is the last region. In the same cycle
  the owner takes ``Job -> AwaitPermission`` and ``AwaitPermission`` runs its
  ``during`` (``w=1``). The machine never rests in "all regions Done".

**A refused last completion** (second table, ``job_rejected.fcstm``). The
owner's outgoing transition is now ``Job -> Ready : if [proceed != 0]``.

* Cycle 3: ``BDone`` arrives but ``proceed`` is 0, so the owner could not leave.
  The completion is refused as a whole: ``B`` stays in ``Working``, its
  ``during`` runs (``b=3``) and the event is not kept for the next cycle.
* Cycle 4: ``proceed`` is 1 but there is no event, so nothing finishes.
* Cycle 5: ``BDone`` and ``proceed=1`` together finish ``B`` and the owner
  continues to ``Ready``.

**Completion through levels** (third and fourth table). The rule is applied at
every level of nesting, and an outer sibling cannot stand in for an inner owner:

* ``nested_join.fcstm``: inner group ``Q{A1, A2}`` finishes in cycle 3 and its
  owner region ``A`` continues through ``Q -> R`` in the same cycle while
  region ``B`` of the outer owner keeps working (``n`` keeps counting). The
  inner owner does not wait for ``B``.
* ``nested_rejected.fcstm``: the inner region may finish only when the
  continuation of every level above it can commit. ``Inner -> [*]`` needs
  ``ok1`` and ``P -> After`` needs ``ok2``. With only one of them true (cycles 2
  and 3) the machine does not move at all; with both (cycle 4) it ends in
  ``Root.After``.

.. literalinclude:: nested_join.fcstm
   :language: fcstm
   :caption: ``nested_join.fcstm``

.. literalinclude:: nested_rejected.fcstm
   :language: fcstm
   :caption: ``nested_rejected.fcstm``

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
the ``enter`` and ``exit`` of ``A1`` and 7 and 8 those of ``B1``.

.. literalinclude:: group_entry.demo.py
   :language: python
   :caption: ``group_entry.demo.py``

.. literalinclude:: group_entry.demo.py.txt
   :language: text

**Owner lifecycle** (first part).

* Cycle 1: ``P``'s ``enter`` (digit 1) runs once. Region ``A`` takes its initial
  transition, then ``P``'s plain ``during before`` (digit 2) runs, and only then
  ``A1`` is entered (digit 5). The ``during before`` of an owner belongs to the
  initialization of the whole group: it runs once, after the first initial
  transition and before the first real state is entered. Then ``B`` starts.
* Cycle 2: nothing runs. The leaves have no ``during``, so there is no
  ``during`` work, and the ``during before`` and ``during after`` blocks of the
  owner are tied to that work. Both are skipped in a cycle without it.
* Cycle 3: the forced transition takes the group away. The regions leave in
  written order (6 for ``A1``, 8 for ``B1``), the owner's ``during after`` (3)
  runs on the committed path where the group hands control back, and the
  owner's ``exit`` (4) runs once, last.

**No backtracking into an earlier region** (second part,
``group_entry.fcstm``). Region ``R1`` has two initial candidates: ``[*] -> A``
writes ``k = 1`` and ``[*] -> B`` writes ``k = 2``. Region ``R2`` can only start
when ``k == 2``. The first candidate of ``R1`` is taken, ``R2`` cannot start, and
the group refuses the entry. The machine does not go back and try ``R1``'s
second candidate (which would have let ``R2`` start); instead the transition
``Idle -> P`` is dropped and the next candidate, ``Idle -> Fallback``, runs.
The trace shows only the committed result: ``k`` is still 0, because the rejected
attempt left nothing behind.

.. literalinclude:: group_entry.fcstm
   :language: fcstm
   :caption: ``group_entry.fcstm``

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

.. literalinclude:: fallback.demo.py
   :language: python
   :caption: ``fallback.demo.py``

.. literalinclude:: fallback.demo.py.txt
   :language: text

* ``candidate_fallback.fcstm``: ``t`` is 1, not 11, because the dropped candidate
  leaves no effect behind, and ``x`` is 2 because ``R1``'s write from this cycle
  is not undone.
* ``initial_fallback.fcstm``: an initial candidate that starts a nested group
  and fails halfway is dropped as well; ``leak`` stays 0 although its ``enter``
  would have run, and the second candidate ``Plain`` is entered (``picked=1``).
* ``group_delta.fcstm`` (cold start): region ``R2`` cannot initialize while ``g``
  is 0, so the machine cannot enter ``P`` at all. The cycle is a Delta: the
  configuration stays ``Root``, the variables stay, and the marker ``(Delta)``
  shows in the table. In cycle 3 ``g`` is 1 and the group starts.
* ``group_delta.fcstm`` (hot start with ``R2`` waiting): the cycle cannot
  initialize ``R2``, so even though ``R1`` could work, the whole cycle is a Delta
  and ``n`` stays 0. Only the cycle that can place ``R2`` commits ``R1``'s work.

.. literalinclude:: group_delta.fcstm
   :language: fcstm
   :caption: ``group_delta.fcstm``

**Why the cycle is the unit of the rollback.** There is no per-region
transaction. A cycle is the one thing that other tools see (inputs, outputs,
generated code), so it either happens fully or not at all. Individual candidates
inside it are tried on a copy; the first one that reaches a legal position wins.

**The limit.** Groups can re-enter each other inside one cycle. The simulator
stops a chain that nests or repeats more than 64 groups in one cycle with a
documented error:

.. literalinclude:: nesting_limit.demo.py
   :language: python
   :caption: ``nesting_limit.demo.py``

.. literalinclude:: nesting_limit.demo.py.txt
   :language: text

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
``during`` blocks of ``X1``, ``Y1``, ``B1``.

.. literalinclude:: aspect_order.demo.py
   :language: python
   :caption: ``aspect_order.demo.py``

.. literalinclude:: aspect_order.demo.py.txt
   :language: text

In cycle 2 (all regions resting) the digits read 1 2 3 4 5 7 8 6 9: the
outermost ``before`` first, then each inner one, the ``during`` blocks of
``X1`` and ``Y1`` (``Q``'s branches), the ``after`` of ``Q`` (7) and of ``A`` (8)
when region ``A``'s branch ends, then region ``B`` (6), and finally ``P``'s
``after`` (9) once. Region ``B`` declares no aspect, so the ``before`` of ``A``
(2) does not appear around it. Cycle 1 shows the same order during entry.

**Where a** ``before`` **sits.** It is placed right before the first ``during`` work
below its scope, after the conditions of the branches that were judged earlier.

.. literalinclude:: aspect_position.fcstm
   :language: fcstm
   :caption: ``aspect_position.fcstm``

.. literalinclude:: aspect_position.demo.py
   :language: python
   :caption: ``aspect_position.demo.py``

.. literalinclude:: aspect_position.demo.py.txt
   :language: text

In cycle 2 ``R1``'s condition ``tick >= 2`` is judged first and sees ``tick = 1``;
then the root's ``before`` makes it 2 and ``P``'s ``before`` runs; ``R2``'s
condition, judged after them, sees ``tick = 2`` and takes ``U -> V``. The root's
``after`` runs once at the end. The last block is
``region_aspect.fcstm``: the ``before`` and ``after`` of ``R1`` run once in each
of cycles 1 and 2 (``r1`` and ``r1after`` go 1, 2) and only around ``R1``'s
branch, while ``R2``'s own ``before`` runs in every cycle (``r2`` 1 to 4). In
cycle 3 ``R1`` finishes through ``A -> [*]``, which is not ``during`` work, so
its aspects do not run (``r1`` stays 2); from then on only ``R2``'s aspect
continues.

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

.. literalinclude:: forced.demo.py
   :language: python
   :caption: ``forced.demo.py``

.. literalinclude:: forced.demo.py.txt
   :language: text

The first block is the model in ``forced_condition.fcstm``: ``!P -> Off : if [x
>= 2]``. The second is the machine that runs, printed by ``to_ast_node()``:

* Each region gets two transitions to ``[*]``: a **starter** with the declared
  condition (``x >= 2``) whose effect raises ``__forced_0``, and, written in front
  of it, a **follower** that fires when the variable is already raised.
* The owner gets two transitions to ``Off``: one that waits for the raised
  variable and lowers it, which is the case after the group ended, and, behind
  it, the declared transition, kept for the case that control comes back to the
  owner without the variable raised.

The third block is the run, and it shows the three consequences:

* **Condition judged at each region's turn.** In cycle 2 ``A``'s ``during`` makes
  ``x`` 2 *after* ``A`` had its turn, so ``A`` carries on. ``B``, which comes
  later, sees ``x >= 2`` at its turn and finishes at once (``B: [done]``,
  ``__forced_0`` is 1). ``A`` finishes in cycle 3, when it sees the raised
  variable, and the owner leaves in the same cycle. The condition is judged once
  per region turn at the state that rests, not again after exits.
* **Leave in written order.** In the controller's ``/Stop`` cycle, ``Safety``
  leaves first, then ``Motion``, then the owner. The block for
  ``forced_nested.fcstm`` shows nested owners: ``X1`` and ``Y1`` leave, then
  their owner ``Inner``, then ``Z1`` of the next region, then ``Outer``. A
  nested owner leaves right after its own regions, and exit actions of Done
  regions are not run twice.
* **The variable is an ordinary variable.** ``__forced_0`` is 0 at every point
  where the machine rests in the examples above, and it is visible in
  ``runtime.vars``.

**When the target cannot be entered.**

.. literalinclude:: forced_blocked.fcstm
   :language: fcstm
   :caption: ``forced_blocked.fcstm``

.. literalinclude:: forced_blocked.demo.py
   :language: python
   :caption: ``forced_blocked.demo.py``

.. literalinclude:: forced_blocked.demo.py.txt
   :language: text

``!P -> Blocked`` cannot complete because ``Blocked``'s initial transition has a
guard that never holds. ``A`` finishes in cycle 2 and its ``exit`` runs
(``seq=18``), but the last region ``B`` keeps working with the variable raised
(``__forced_0=1``); the configuration ``P{A: [done], B: B1}`` rests. The group
leaves in the first cycle in which the target can be entered. The ordinary
``P -> Other : /Stop`` is not taken: it needs the whole group to finish first.
This is the one situation in which ``__forced_*`` is 1 at rest.

In ``forced_two_declarations.fcstm`` two declarations compete. The first one
that is raised holds the group; the second one is not tried in the meantime.
In a model without regions a target that cannot be entered makes the next
declaration count instead; the difference is a consequence of expanding with
ordinary transitions only, and it is a known gap (see
`issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_).

**It is shorthand, and it behaves like its expansion.** The model that runs and
the model loaded from its exported text take the same cycles:

.. literalinclude:: forced_equivalence.demo.py
   :language: python
   :caption: ``forced_equivalence.demo.py``

.. literalinclude:: forced_equivalence.demo.py.txt
   :language: text

The exported text loads to a machine with an ordinary variable ``__forced_0``
and nothing marks it as forced any more. Both machines produce the same
configuration and variables in every cycle. The same holds for hot start,
generated runtimes, bounded model checking and the verify pipeline: they take
the machine that runs. Drawings and the report of ``pyfcstm inspect`` show the
model as written, because they describe what you wrote.

**What this does not say.** The expansion does not reproduce every detail of other
tools, and the two gaps above are deliberate. See
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

The six variables record what ``active()`` answered at six places: ``exit_self``
and ``exit_other`` inside ``Normal``'s ``exit``, ``effect_source`` and
``effect_target`` inside the transition's ``effect``, ``enter_self`` and
``enter_other`` inside ``Tripped``'s ``enter``. The value 1 means active and 2
means not active.

.. literalinclude:: active_query.demo.py
   :language: python
   :caption: ``active_query.demo.py``

.. literalinclude:: active_query.demo.py.txt
   :language: text

* ``exit_self=1``, ``exit_other=2``: inside ``Normal``'s ``exit``, ``Normal`` is
  still active and ``Tripped`` is not yet.
* ``effect_source=2``, ``effect_target=2``: during the effect the machine has
  left ``Normal`` and has not entered ``Tripped``.
* ``enter_self=1``, ``enter_other=2``: inside ``Tripped``'s ``enter``, ``Tripped``
  is active and ``Normal`` is not.
* With ``Safety`` first (first table), ``Motion`` sees ``Tripped`` in the cycle
  in which it was entered and stops at once (``m`` stays 1). With ``Motion``
  first (second table), ``Motion`` runs one more cycle (``m=2``) and stops in the
  next. The same one-cycle lag as for variables.

**How it works.** ``active()`` is shorthand for an ordinary flag:

.. literalinclude:: active_lowering.demo.py
   :language: python
   :caption: ``active_lowering.demo.py``

.. literalinclude:: active_lowering.demo.py.txt
   :language: text

The model that runs has one hidden ``int`` variable per queried state. The flag
is set at the first line of ``enter`` and cleared at the last line of ``exit``,
which is what puts ``enter`` and ``exit`` blocks at the edges of the "active"
interval and nothing else. The queried state is never a region; naming one is an
error when the model is built. In cycle 2 region ``B`` reads the flag that
region ``A`` raised in the same cycle.

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

.. literalinclude:: configuration_text.demo.py
   :language: python
   :caption: ``configuration_text.demo.py``

.. literalinclude:: configuration_text.demo.py.txt
   :language: text

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

Hot start
---------

**Claim.** A hot start places what the text names and leaves everything else to
initialize in the first cycle, in written order. Nothing placed is entered
again.

.. literalinclude:: hot_start.demo.py
   :language: python
   :caption: ``hot_start.demo.py``

.. literalinclude:: hot_start.demo.py.txt
   :language: text

Read the six starts one by one:

* **Every leaf named.** The first cycle shows no ``enter`` for ``Safety`` or
  ``Motion``: they are in place. The regions just work, and ``Motion`` moves
  ``Off -> On`` because ``permit`` was given as 1.
* **A region Done.** ``Safety: [done]`` stays done and runs nothing; only
  ``Motion`` does.
* **A path into a region** (``Controller.Running.Motion.On``). The other region
  starts waiting (``Safety: [init]``). In cycle 1 ``Safety`` takes its initial
  transition and enters ``Watching``, in written order before ``Motion``'s
  ``during``. The path keeps only the branch it goes through.
* **The owner alone.** The group waits as a whole and both regions initialize in
  written order; compare the trace of entering ``Running`` in the first section.
* **All regions Done.** Refused with ``All regions are Done``, at any depth of
  nesting: a finished owner has nowhere to rest.
* **A missing variable.** Refused. Hidden variables such as ``__forced_0`` are
  ordinary variables and the caller supplies them with the others; nothing is
  derived from the position.

The same text works on the command line, and so does the refusal:

.. literalinclude:: hot_start_cli.demo.sh
   :language: bash
   :caption: ``hot_start_cli.demo.sh``

.. literalinclude:: hot_start_cli.demo.sh.txt
   :language: text

.. literalinclude:: hot_start_refused.demox.sh
   :language: bash
   :caption: ``hot_start_refused.demox.sh``

.. literalinclude:: hot_start_refused.demox.sh.txt
   :language: text

The refusal is printed on standard output and the command exits with status
``1``; the captured status is in ``hot_start_refused.demox.sh.exitcode``.

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

.. literalinclude:: event_names.fcstm
   :language: fcstm
   :caption: ``event_names.fcstm``

.. literalinclude:: event_names.demo.py
   :language: python
   :caption: ``event_names.demo.py``

.. literalinclude:: event_names.demo.py.txt
   :language: text

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
  twice in ``consumed``, once for each transition it moved.
* With ``Safety`` Done, there is only one active leaf, so ``Ping`` is no longer
  ambiguous: Done regions and regions waiting for initialization do not take
  part.

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

.. literalinclude:: handler_context.demo.py
   :language: python
   :caption: ``handler_context.demo.py``

.. literalinclude:: handler_context.demo.py.txt
   :language: text

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
* **Forced transitions.** The two differences from models without regions are
  listed in :ref:`region-semantics-forced`. The expansion adds a hidden variable
  to the model.
* **Comparison with other tools** (what a Stateflow user will notice, and the
  measured gaps) is on :doc:`the design page </explanations/region_design/index>`.
* **Known gaps and limits of the model** are collected in the "Limits and known
  gaps" section of :doc:`/reference/region_model/index`.
