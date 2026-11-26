How regions enter the bounded transition system
================================================

A state that owns regions runs them one after another inside a single cycle.
Bounded model checking (BMC) has to turn that cycle into one finite formula
without writing down every combination of the regions' paths, and the witness
it decodes has to survive a replay through the simulator.  This page explains
how :mod:`pyfcstm.bmc.region_relation` and its neighbours do that: which symbols
describe a region, how the regions are chained, how an owner is started and
finished, where a hot start comes from, and where the construction stops.

The page covers the encoding of regions.  It does not define the FBMCQ syntax
(see :doc:`the FBMCQ reference </reference/bmc_query/index>`), it does not repeat
the relation for models without regions (see
:doc:`/explanations/bmc_semantics/index`), and it gives no closed form for how
the cost grows (see :doc:`/explanations/bmc_scaling/index`).  Which machine runs
which cycle is defined by
:doc:`/explanations/region_semantics/index`; this page only shows that the
encoding follows it.  A BMC verdict is still a bounded statement about at most
:math:`N` macro-steps.

Terms and symbols
-----------------

An **owner** is a state that declares regions.  Its **regions** run in written
order, which is also the execution order.  A region is a namespace, not a state,
so the thing a region holds is a **position**: the state its branch rests in, or
one of three markers described below.  An owner **rests** in a frame when the
machine is in the owner and has not left it.  A region is **working** while its
position is a state, and **done** after it finished through ``[*]``.

The page keeps one notation throughout.  The frame index :math:`t`, the bound
:math:`N` and the persistent variable vector :math:`\nu_t` are those of
:doc:`/explanations/bmc_semantics/index`.

* :math:`O` is one owner and :math:`R_1,\dots,R_n` are its regions in written
  order.  Example: ``Controller.Running`` is an owner with :math:`n=2` and
  :math:`R_1=` ``Safety``, :math:`R_2=` ``Motion``.
* :math:`\mathcal{P}_i` is the set of state ids a branch of :math:`R_i` can rest
  in.  Example: for ``Motion`` it holds the ids of ``Off`` and ``On``.
* :math:`s_t` is the state symbol of frame :math:`t`; :math:`\mathrm{id}(O)` is
  the id of :math:`O`.
* :math:`p_{t,i}` is the position symbol of region :math:`R_i` in frame
  :math:`t`.  The code names it ``BmcTraceSymbols.region_position(t, path)``.
  :math:`q_{t,i}` is the position the same region has after its turn in step
  :math:`t`.
* :math:`\mathsf{DONE}`, :math:`\mathsf{INACTIVE}` and :math:`\mathsf{PENDING}`
  are the three markers ``REGION_DONE_ID`` (-4), ``REGION_INACTIVE_ID`` (-5) and
  ``REGION_PENDING_ID`` (-6).
* :math:`\mathrm{Rest}_t(O)` says that :math:`O` rests in frame :math:`t`: for
  an owner outside every region it is :math:`s_t=\mathrm{id}(O)`, for a nested
  owner it also requires its enclosing region to be at :math:`O` and the
  enclosing owner to rest.
* :math:`\xi_t^{(0)},\dots,\xi_t^{(n)}` are the values handed from region to
  region in step :math:`t`: the persistent variables plus, for models with
  ``>> during`` aspects, two flags per aspect scope.  :math:`\xi_t^{(0)}` is the
  vector the cycle starts on, :math:`\xi_t^{(i)}` the vector region :math:`R_i`
  leaves behind.
* :math:`\eta` is the vector an owner is entered on, :math:`\mathcal{E}` the
  list of (owner, vector) pairs whose entry is being decided on the current
  path, and :math:`L` the option ``BmcOptions.max_group_reentries``.

The model used throughout
-------------------------

Every section below uses the interlock controller of
:doc:`the region tutorial </tutorials/regions/index>`.  ``Safety`` is written
before ``Motion``, so in every cycle ``Safety`` updates ``permit`` and ``Motion``
reads it.

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :linenos:

The question is whether the motor can still be on while ``permit`` is already
0.  The query asks for a counterexample within four macro-steps: cold start,
``/Start``, a request, and a fault that arrives together with the request.

.. literalinclude:: interlock.fbmcq
   :language: fbmcq

``forbid`` searches for a frame where ``motor`` is 1 and ``permit`` is 0.  The
commands below run it on the model as written and on
:download:`controller_swapped.fcstm </_models/controller_swapped.fcstm>`, which
differs only in that ``Motion`` is written before ``Safety``.  Put
:download:`controller.fcstm </_models/controller.fcstm>`,
:download:`controller_swapped.fcstm </_models/controller_swapped.fcstm>` and
:download:`interlock.fbmcq <interlock.fbmcq>` into one directory to run them.  A
``...`` line stands for report lines the page does not discuss, among them the
one that prints solver time.

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q interlock.fbmcq --color never
   BMC forbid <= 4: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   Conclusion: Every admissible execution within 4 macro-steps satisfies the forbid property.
   ...
   $ echo $?
   0
   $ pyfcstm bmc -i controller_swapped.fcstm -q interlock.fbmcq --color never
   BMC forbid <= 4: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
     Replay: verified (5 frames, 4 steps).
   ...
   Trace
     0: init
          -> Controller.Idle [initial]
          [start] -> Controller.Idle [initial]
     1: Controller.Idle
          -> Controller.Idle [fallback]
          Controller.Idle -> Controller.Idle [fallback]
     2: Controller.Idle
          -> Controller.Running{Motion: Off, Safety: Watching} [transition; events=Controller.Start]
          Controller.Idle -> Controller.Running [transition]
          Running: [start] -> Motion.Off [initial]
          Running: [start] -> Safety.Watching [initial]
     3: Controller.Running{Motion: Off, Safety: Watching}
          -> Controller.Running{Motion: On, Safety: Watching} [transition]
          Motion: Off -> On [transition]
          Safety: Watching -> Watching [fallback]
   ...
   $ echo $?
   1

Read the two headline lines first.  With ``Safety`` first the verdict is
``PROPERTY GUARANTEED WITHIN BOUND`` and the exit status is 0: no execution of at
most four macro-steps puts the motor on with the permit off.  With ``Motion``
first the verdict is ``PROPERTY DOES NOT HOLD WITHIN BOUND`` with exit status 1,
and the report prints a counterexample that the simulator replayed.  The only
difference between the two models is the written order, so the order is part of
the formula.  The rest of the page derives how.

Two things the output does not say.  It does not say the first controller is
safe beyond four macro-steps.  It also does not show why the formulas differ;
sections 1 and 2 do.

1. One step is one whole cycle, and every region has a position
----------------------------------------------------------------

The trace allocates one state symbol and one symbol per persistent variable for
each frame, and one selector per step and case, exactly as
:doc:`/explanations/bmc_semantics/index` describes.  For a model with regions a
frame gets one more symbol per region, :math:`p_{t,i}`.  A step is still one
full runtime cycle: the regions of every resting owner take their turn inside the
same step, so the frame after step :math:`t` already shows what every region did.

The position symbol takes one of these values.

.. list-table:: Values of a region position symbol
   :header-rows: 1
   :widths: 24 30 46

   * - Value
     - Constant
     - Meaning
   * - a state id
     - member of :math:`\mathcal{P}_i`
     - The branch of the region rests in that stable leaf, or in a state that
       owns regions of its own.
   * - -4
     - ``REGION_DONE_ID``
     - The region finished through ``[*]`` and the owner still rests.
   * - -5
     - ``REGION_INACTIVE_ID``
     - The owner does not rest in this frame, so the region has no position.
   * - -6
     - ``REGION_PENDING_ID``
     - A hot start left the region out or wrote ``[init]``; the region starts in
       the first cycle.  Only the frame that holds the whole start position may
       use it.

Three constraints tie the position of each region to its owner.  They hold in
every frame and are part of the core formula:

.. math::
   :label: eq-region-position-domain

   \begin{aligned}
   \mathrm{Rest}_t(O) &\Rightarrow
     \bigwedge_{i=1}^{n}\bigl(p_{t,i}\in\mathcal{P}_i\cup\{\mathsf{DONE}\}\bigr),\\
   \lnot\,\mathrm{Rest}_t(O) &\Rightarrow
     \bigwedge_{i=1}^{n}\bigl(p_{t,i}=\mathsf{INACTIVE}\bigr),\\
   \mathrm{Rest}_t(O) &\Rightarrow
     \bigvee_{i=1}^{n}\bigl(p_{t,i}\neq\mathsf{DONE}\bigr).
   \end{aligned}

The first line keeps a resting owner's regions inside their own namespace.  The
second makes a region inactive exactly when its owner does not rest.  The third
forbids a resting owner whose regions are all done: a group whose regions all
finished hands control back in the same cycle (section 4), so no frame can end
there.  ``region_frame_constraints`` builds these constraints and
``test_the_frame_constraints_are_part_of_the_core_and_can_be_read_back`` reads
them back from the core.

The position symbols are internal to the solver, but the witness that
``pyfcstm bmc`` decodes shows their effect.  The next commands solve the swapped
model of the working query to a JSON result and print, for every frame, its
configuration and the two variables.  A configuration names the regions of an
owner only while the owner rests.

.. code-block:: console

   $ pyfcstm bmc -i controller_swapped.fcstm -q interlock.fbmcq --json -o result.json
   $ echo $?
   1

.. testcode::

   import json

   with open("result.json", encoding="utf-8") as stream:
       result = json.load(stream)
   for frame in result["witness"]["frames"]:
       print(
           "frame %d: %s | permit=%d motor=%d"
           % (
               frame["index"],
               frame.get("configuration") or frame["sentinel"],
               frame["vars"]["permit"],
               frame["vars"]["motor"],
           )
       )

.. testoutput::

   frame 0: init | permit=0 motor=0
   frame 1: Controller.Idle | permit=0 motor=0
   frame 2: Controller.Idle | permit=0 motor=0
   frame 3: Controller.Running{Motion: Off, Safety: Watching} | permit=1 motor=0
   frame 4: Controller.Running{Motion: On, Safety: Watching} | permit=0 motor=1

In frames 0 to 2 the machine is in the init sentinel or in ``Idle``.  The owner
``Running`` does not rest there, so no region is listed; in the encoding both
positions are ``INACTIVE`` in those frames, which is the second line of
:eq:`eq-region-position-domain`.  In frame 3 the owner rests and the listed
regions are ``Motion`` in ``Off`` and ``Safety`` in ``Watching``, the states of
their own regions.  The output shows one execution and does not prove the
constraint; the tests do the proving.

2. Regions are chained in written order
---------------------------------------

Inside step :math:`t` the regions do not read the frame variables independently.
Region :math:`R_1` starts on the values the cycle starts on, and every later
region starts on what the one before it left.  The formula introduces a fresh
vector :math:`\xi_t^{(i)}` after each region and chains them:

.. math::
   :label: eq-region-value-chain

   \begin{aligned}
   \xi_t^{(0)} &= \nu_t,\\
   \mathrm{Chain}_t(O) &\equiv
     \bigwedge_{i=1}^{n}\mathrm{Run}_{t,i}\bigl(\xi_t^{(i-1)},\,p_{t,i},\,\xi_t^{(i)},\,q_{t,i}\bigr).
   \end{aligned}

:math:`\mathrm{Run}_{t,i}` is the lowering of region :math:`R_i`'s turn.  It
holds one implication for each position the region can be in, ``p == leaf``
implies the paths of that leaf, plus the case of a region that is done or
inactive, which only carries its position and the values on.  A later region
reads its inputs from :math:`\xi_t^{(i-1)}`, so it sees the earlier region's new
values and never the other way round.  Nothing makes an earlier region run again
on the values a later one wrote, which is the design rule that the earlier region
does not rerun.

The frames of section 1 show the hand-over of the fault cycle, the step from
frame 3 to frame 4.  With ``Motion`` first it reads ``permit=1``, switches the
motor on, and ``Safety`` clears the permit afterwards, so frame 4 holds
``motor=1`` with ``permit=0``.  That is the counterexample the ``forbid`` query
found.  Read from the model text, the order ``Safety`` first hands region 2 the
vector :math:`\xi_t^{(1)}` with ``permit=0``: ``Motion`` then reads ``permit=0``
and leaves ``motor=0``, so no frame can hold the forbidden pair, which is the
verdict of the first command above.  The values in :math:`\xi_t^{(1)}` are
intermediate symbols that no report prints, so that half is a reading of the
model and not an output of this page.

Why the formula is a sum
~~~~~~~~~~~~~~~~~~~~~~~~

Each :math:`\mathrm{Run}_{t,i}` is lowered from the units of region :math:`R_i`
alone, and the units connect only through :math:`\xi_t^{(i)}`.  A flat expansion
would instead need one path per combination of the regions' paths.  The next
script counts the paths that one working cycle lowers to, for one to eight
regions that each toggle between two states on an event.  Its columns are the
number of regions, the lowered paths, and :math:`4^{n}` for :math:`n` regions.

.. testcode::

   from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
   from pyfcstm.model import load_state_machine_from_text

   for regions in range(1, 9):
       text = "state Root { %s }" % "".join(
           "region R%d { [*] -> Off; state Off; state On; Off -> On :: Go; On -> Off :: Go; }" % i
           for i in range(regions)
       )
       query = "check reach <= 2: terminated();"
       core = build_bmc_core_formula(BmcEngine(load_state_machine_from_text(text)).prepare(query))
       print(regions, len(core.region_steps[1].cases), 4**regions)

.. testoutput::

   1 6 4
   2 10 16
   3 14 64
   4 18 256
   5 22 1024
   6 26 4096
   7 30 16384
   8 34 65536

Each region adds four lowered paths: two resting positions times two outcomes,
transition or fallback.  Two more are present at any region count: the cold-start
path out of the init frame and the continuation of the root after all regions
finish.  Step 0 of the query is the cold start, so ``region_steps[1]`` is the
first cycle in which the regions work.  The third column is the number of
combined paths a flat expansion would need under the same description.  The counts show that the lowered paths grow
with the sum.  They are a count of paths, not of formula nodes; the exact closed
forms, and where the cost still grows steeply, are on
:doc:`/explanations/bmc_scaling/index`.

3. Entering an owner starts every region
----------------------------------------

A transition that enters an owner does not stop at the owner.  It carries the
whole initialization of the group: region :math:`R_1` starts first, then
:math:`R_2` on the values :math:`R_1`'s start left, and so on.  Let :math:`\eta`
be the values the owner is entered on and :math:`\eta^{(i)}` those after the
start of :math:`R_i`.  Region :math:`R_i` can start when it has an initial path
that commits on :math:`\eta^{(i-1)}`; call that condition :math:`\mathrm{ok}_i`.

.. math::
   :label: eq-region-owner-start

   \begin{aligned}
   \mathrm{ok}_i &\equiv \mathrm{Start}_i\bigl(\eta^{(i-1)}\bigr),\\
   \mathrm{Entry}_O(\eta) &\equiv
     \bigwedge_{i=1}^{n}\Bigl(\bigwedge_{j<i}\mathrm{ok}_j\ \Rightarrow\
       \mathrm{Init}_i\bigl(\eta^{(i-1)},\,q_i,\,\eta^{(i)}\bigr)\Bigr),\\
   \mathrm{Accept}_O(\eta) &\equiv \bigwedge_{i=1}^{n}\mathrm{ok}_i\ \land\
     \Bigl(\lnot\,\mathrm{AllDone}\ \lor\ \mathrm{Can}_O\bigl(\eta^{(n)}\bigr)\Bigr).
   \end{aligned}

:math:`\mathrm{Init}_i` is the relation of the first committable initial path of
region :math:`R_i`.  It is asserted only when every earlier region started, so a
region behind one that cannot start assigns nothing and none of its operations has
to be defined.  :math:`\mathrm{AllDone}` says that every region is already done
right after its start, and :math:`\mathrm{Can}_O` is the continuation check of
section 4, applied to :math:`\eta^{(n)}`: when the regions finish at once, the
entry is accepted only if the owner can continue in the same cycle.
:math:`\mathrm{Accept}_O` is the condition under which the path
that enters :math:`O` can be taken at all.  When it is false the path is rejected
as a whole.  The encoding does not go back and try another entry of an earlier
region, which is the rule that a later region that cannot start rejects the whole
entry.

The cold start is the case that makes the rejection visible, because nothing
else can apply to the init frame.  The model has two regions; ``B`` can start only
when the input ``g`` is positive.

.. literalinclude:: blocked.fcstm
   :language: fcstm
   :linenos:

Three queries: one without assumptions, one that fixes ``g == 0`` and asks for
the owner, and one that fixes ``g == 0`` and only asks to see any trace.

.. code-block:: console

   $ cat blocked_free.fbmcq blocked_stuck.fbmcq blocked_zero.fbmcq
   check reach <= 1: active("Root.Run");
   assume always: g == 0;
   check reach <= 2: active("Root.Run");
   assume always: g == 0;
   check reach <= 2: true;
   $ pyfcstm bmc -i blocked.fcstm -q blocked_free.fbmcq --color never
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i blocked.fcstm -q blocked_stuck.fbmcq --color never
   BMC reach <= 2: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i blocked.fcstm -q blocked_zero.fbmcq --color never
   ...
   Trace
     0: init
          -> init [delta]
     1: init
          -> init [delta]
   ...

With ``g`` free, ``Root.Run`` is reachable in one step: both regions start.
With ``g == 0`` the goal ``Root.Run`` is unrealizable within two steps, although
``A`` could start on its own.  The query that only asks for a trace prints two
steps of ``[delta]``: the machine stays in the init frame because the whole entry
was refused, and the next cycle tries again.  This is the encoding of the
simulator's rule that a cold start which cannot enter leaves everything as it was.
The output does not show the cost of the rejection and does not claim the
simulator would choose another entry; it would not, by the same rule.

4. The last region may finish only if the owner can continue
-------------------------------------------------------------

A region that finishes through ``[*]`` gets the position :math:`\mathsf{DONE}`.
That is allowed whenever another region is still working.  If it is the last
working region, the owner must be able to continue in the same cycle, because no
frame may hold a resting owner whose regions are all done.

Let :math:`\mathrm{Live}_{t,i}` say that some other region is still working after
the turn of :math:`R_i`: an earlier region :math:`R_j` with
:math:`q_{t,j}\neq\mathsf{DONE}`, or a later one whose position is neither
:math:`\mathsf{DONE}` nor :math:`\mathsf{INACTIVE}`.  Let
:math:`\mathrm{Can}_O(\xi)` say that one continuation of :math:`O` can commit on
the values :math:`\xi`, and :math:`\mathrm{Cont}_O` be the relation of that
continuation.

.. math::
   :label: eq-region-joint-completion

   \begin{aligned}
   q_{t,i}=\mathsf{DONE} &\Rightarrow
     \mathrm{Live}_{t,i}\ \lor\ \mathrm{Can}_O\bigl(\xi_t^{(i)}\bigr),\\
   \mathrm{AllDone}_t &\equiv \bigwedge_{i=1}^{n}\bigl(q_{t,i}=\mathsf{DONE}\bigr),\\
   \lnot\,\mathrm{AllDone}_t &\Rightarrow
     \Bigl(s_{t+1}=\mathrm{id}(O)\ \land\ \nu_{t+1}=\xi_t^{(n)}\ \land\
       \bigwedge_{i=1}^{n}p_{t+1,i}=q_{t,i}\Bigr),\\
   \mathrm{AllDone}_t &\Rightarrow
     \mathrm{Cont}_O\bigl(\xi_t^{(n)},\,s_{t+1},\,\nu_{t+1}\bigr).
   \end{aligned}

The first line is the acceptance check on the last region, evaluated on the
values after its own turn.  The third line keeps the owner resting and copies the
chain's result into the next frame.  The fourth line hands control to the
continuation in the same step.  When the last region would finish but no
continuation can commit, the first line rejects that finish and the region stays
in its leaf, where the cycle runs its ``during`` instead.  The event or guard that
triggered the finish is not kept for the next cycle.

The joint model has two regions that both finish, and the owner continues to
``Next`` only when the input ``ok`` is nonzero.

.. literalinclude:: joint.fcstm
   :language: fcstm
   :linenos:

Five queries ask about it.  The first shows the files, the second prints the
headline of each report; every report is cut to the line the page discusses.

.. code-block:: console

   $ cat joint_a_done.fbmcq joint_all_done.fbmcq joint_next.fbmcq joint_blocked_b_done.fbmcq joint_blocked_next.fbmcq
   check reach <= 3: active("Root.Job{A: [done]}");
   check reach <= 3: active("Root.Job{A: [done], B: [done]}");
   check reach <= 3: active("Root.Next");
   assume always: ok == 0;
   check reach <= 3: active("Root.Job{B: [done]}");
   assume always: ok == 0;
   check reach <= 3: active("Root.Next");
   $ pyfcstm bmc -i joint.fcstm -q joint_a_done.fbmcq --color never
   BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i joint.fcstm -q joint_all_done.fbmcq --color never
   BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i joint.fcstm -q joint_next.fbmcq --color never
   BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i joint.fcstm -q joint_blocked_b_done.fbmcq --color never
   BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i joint.fcstm -q joint_blocked_next.fbmcq --color never
   BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1

``A`` can finish alone (first query): ``B`` is still working, so the first line of
:eq:`eq-region-joint-completion` holds without a continuation.  The state with both
regions done is not reachable (second query), as the third line of
:eq:`eq-region-position-domain` demands.  ``Next`` is reachable (third query),
which needs the last finish and the hand-over in one step.  With ``ok`` fixed to
0, ``B`` can never finish (fourth query) and ``Next`` cannot be reached (fifth
query): the last region is refused, not parked in ``[done]``.  The runs do not
prove the same holds for other shapes; ``test_the_last_region_may_finish_only_if_the_owner_can_continue``
and its neighbours do.

Aspects and the owner's plain ``during before``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aspects add two more values to :math:`\xi`: for each scope that declares
``>> during`` actions, a flag that its ``before`` actions already ran in this
cycle, and a flag that it owes its ``after`` actions.  The flags travel with the
chain.  A ``before`` action therefore runs once per scope and cycle, outside in.
An owed ``after`` action is settled when the branch of its scope ends, innermost
scope first, so the next region already sees it.  A scope that is not inside a
region settles at the end of the cycle.  The formula grows with the number of
aspect scopes, not with the number of their subsets.

The plain ``during before`` of an owner, written without ``>>``, belongs to the
group's initialization: it runs once, before the first non-pseudo child is
entered.  The plain ``during after`` runs once on the committed path that hands
control back.  The next script lists the abstract actions of each step in call
order for two models, read from the JSON result that ``pyfcstm bmc --json``
writes.

.. code-block:: console

   $ pyfcstm bmc -i aspects.fcstm -q aspects.fbmcq --json -o aspects.json
   $ pyfcstm bmc -i plain_before.fcstm -q plain_before.fbmcq --json -o plain_before.json

.. testcode::

   import json

   for name in ("aspects", "plain_before"):
       with open(name + ".json", encoding="utf-8") as stream:
           steps = json.load(stream)["witness"]["steps"]
       for step in steps:
           print(name, step["index"], " ".join(call["action_name"] for call in step["abstract_calls"]))

.. testoutput::

   aspects 0 Root.Pre Root.A.P.WorkA Root.A.PostA Root.B.Q.WorkB Root.Post
   aspects 1 Root.Pre Root.A.P.WorkA Root.A.PostA Root.B.Q.WorkB Root.Post
   plain_before 0 Root.Job.Prep Root.Job.A.P.OnP Root.Job.B.Q.OnQ

In the first model, ``Pre`` and ``Post`` are the root's aspects and ``PostA`` is
declared inside region ``A``.  Every step calls ``Pre`` first and ``Post`` last,
and ``PostA`` runs right after ``WorkA``, before ``WorkB`` starts: the branch of
``A`` ended, so its ``after`` action settled before ``B``'s turn.  In the second
model ``Prep`` is the owner's plain ``during before`` and it precedes both
``enter`` actions of the regions.  The two models and their queries are in
:download:`aspects.fcstm <aspects.fcstm>`, :download:`aspects.fbmcq <aspects.fbmcq>`,
:download:`plain_before.fcstm <plain_before.fcstm>` and
:download:`plain_before.fbmcq <plain_before.fbmcq>`.  The output shows call order
only; it does not show the abstract call snapshots, which section 6 covers.

5. A hot start builds the first frame
-------------------------------------

``init state("...")`` does not run the first cycle's entry.  It writes a position,
and frame 0 holds exactly that position, so the first cycle continues from it.
The text can be a configuration, a path through regions, or an owner alone.

.. list-table:: Forms of a position in ``init state(...)``
   :header-rows: 1
   :widths: 34 38 28

   * - Text
     - Position of frame 0
     - Regions left out
   * - ``"Controller.Running{Motion: On}"``
     - ``Motion`` rests in ``On``, the owner rests
     - ``Safety`` is ``PENDING``
   * - ``"Controller.Running.Motion.On"``
     - The same position, written as a path through a region
     - ``Safety`` is ``PENDING``
   * - ``"Controller.Running"``
     - The owner rests, no region is placed
     - Every region is ``PENDING``
   * - ``"Root.Job{A: [done]}"``
     - ``A`` is ``DONE``
     - The other regions are ``PENDING``

A written branch is put in place without running any ``enter``.  A region that is
left out or written ``[init]`` is :math:`\mathsf{PENDING}` and starts in the first
cycle, in written order, on the values the earlier regions left.  The frame
constraints of section 1 allow :math:`\mathsf{PENDING}` only in the frame that
holds the whole start position.

.. literalinclude:: start_motion_on.fbmcq
   :language: fbmcq

The query starts ``Motion`` in ``On`` and asks to reach the full configuration.

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q start_motion_on.fbmcq --color never
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: [init], Motion: On}
          -> Controller.Running{Safety: Watching, Motion: On} [initial]
          Running: [start] -> Safety.Watching [initial]
          Motion: On -> On [fallback]
   ...

The trace starts in ``Controller.Running{Safety: [init], Motion: On}``.  Step 0 has
two lines: ``Running: [start] -> Safety.Watching [initial]`` starts the pending
region, and ``Motion: On -> On [fallback]`` runs ``Motion``'s ``during``.  No line
enters ``Motion``, because it was put in place.

A start that leaves every region of an owner done is refused when the query is
compiled, since no frame can hold that position (the third line of
:eq:`eq-region-position-domain`).  This is a negative example; the query is
refused on purpose.

.. code-block:: console

   $ cat start_all_done.fbmcq
   init state("Root.Job{A: [done], B: [done]}");
   check reach <= 1: true;
   $ pyfcstm bmc -i joint.fcstm -q start_all_done.fbmcq
   Failed to compile BMC query: invalid_start_position at initial.state_path: all regions are done at 'Root.Job'; a finished owner cannot be hot-started.
   $ echo $?
   1

The diagnostic code is ``invalid_start_position`` and the exit status is 1; no
JSON result is written.  A configuration text that is not a position of the model
(for example ``Root.Job{A: Nope}``) is refused with the same code, while a plain
path to a state that does not exist is refused with ``unknown_state``.

6. Patterns and call snapshots look at the machine, they do not build it
------------------------------------------------------------------------

``active("...")`` with a configuration text is a **pattern**.  Written regions
have to be where the text says; regions left out are free.  For a pattern
:math:`\pi` with written regions :math:`W`, the predicate over positions
:math:`p` is

.. code-block:: text

   in(O) and, for every written region i,
       at(R_i, pattern_i)  with  [done]  ->  p_i = DONE
                                 [init]  ->  p_i is PENDING or INACTIVE
                                 State   ->  the nested pattern

where ``in(O)`` is the plain ``active(O)``.  The contrast with a start is the
direction: a start *constructs* a position, so a region it leaves out waits for
initialization, while a pattern *matches* one, so a region it leaves out can be
anywhere.  A position built by an ``init state(...)`` text always matches the
same text as a pattern.

A pattern that is not a position of the model is refused when the query is
compiled, with the diagnostic ``invalid_active_pattern``: a syntax error, an
unknown state, a region the state does not own, or a region written twice.

Inside the ``where`` of a call filter, ``active(...)`` describes the whole machine
at the moment of the call, not at the end of the cycle.  The positions are the
ones the handler is given as ``ctx.configuration``:

* a region that moved earlier in the same cycle shows its new place;
* a region that has not started shows ``[init]``;
* when an owner is entered again in the same cycle, the calls of the entry see
  every region as ``[init]``, and the calls of the exit and of aspects still see
  the old positions.

``called`` and ``call_count`` also count a ``>> during after`` call that a
group's end settles against the state the simulator tells the handler; that
state is the owner when the aspect wraps the whole group, and the leaf when it
sits below
(``test_an_aspect_over_a_group_reports_the_owner_and_over_a_region_its_leaf`` in
``test/bmc/test_region_call_records.py``).
The model of the next script enters ``O``, finishes both regions and
enters ``O`` again in the second step.  Each of the six queries asks whether an
abstract action is called in a step while the whole machine matches a pattern, and
the script prints ``sat`` when such a call exists and ``unsat`` when it does not.

.. literalinclude:: reenter.fcstm
   :language: fcstm
   :linenos:

.. testcode::

   from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
   from pyfcstm.model import load_state_machine_from_text

   with open("reenter.fcstm", encoding="utf-8") as stream:
       model = load_state_machine_from_text(stream.read())
   asks = [
       ("Root.O.B.Q.OnQ", 0, "Root.O{A: P}"),
       ("Root.O.B.Q.OnQ", 0, "Root.O{A: [init]}"),
       ("Root.O.A.P.OnEnter", 1, "Root.O{B: [init]}"),
       ("Root.O.A.P.OnEnter", 1, "Root.O{B: Q}"),
       ("Root.O.A.P.OnExit", 1, "Root.O{B: Q}"),
       ("Root.O.A.P.OnExit", 1, "Root.O{B: [init]}"),
   ]
   for action, step, pattern in asks:
       query = 'check reach <= 2: called("%s", step=%d, where active("%s"));' % (action, step, pattern)
       print(solve_bmc_property(compile_bmc_query(model, query)).status, query)

.. testoutput::

   sat check reach <= 2: called("Root.O.B.Q.OnQ", step=0, where active("Root.O{A: P}"));
   unsat check reach <= 2: called("Root.O.B.Q.OnQ", step=0, where active("Root.O{A: [init]}"));
   sat check reach <= 2: called("Root.O.A.P.OnEnter", step=1, where active("Root.O{B: [init]}"));
   unsat check reach <= 2: called("Root.O.A.P.OnEnter", step=1, where active("Root.O{B: Q}"));
   sat check reach <= 2: called("Root.O.A.P.OnExit", step=1, where active("Root.O{B: Q}"));
   unsat check reach <= 2: called("Root.O.A.P.OnExit", step=1, where active("Root.O{B: [init]}"));

Read the pairs.  In step 0 the enter of ``Q`` (region ``B``) sees ``A`` already at
``P``: ``A`` moved first, and it never sees ``A`` as ``[init]``.
In step 1 the owner is entered again after both regions finished: the enter of
``P`` sees ``B`` as ``[init]`` and not as ``Q``, while the exit of ``P`` still
sees ``B`` in ``Q``.  Each pair has one realizable and one unrealizable query, so
the answer is a property of the encoding and not of the one witness the solver
happened to pick.

7. The witness and what replay compares
---------------------------------------

The decoded witness keeps the public schema and adds optional region fields,
which are absent for models without regions.

* Every frame carries ``configuration``, the same text ``str(configuration)``
  gives in the simulator (the init frame has none).
* Every step carries ``local_cases``, one entry per path that ran, in the order
  the simulator ran them.  Each has a ``scope`` (the owner or region the path ran
  in, ``null`` outside every region), a ``kind`` (``initial``, ``transition`` or
  ``fallback``) and a ``label``.
* ``case_label`` is the label of the path that ran outside every region, and
  ``null`` when no path did.  The cases inside regions are reported in
  ``local_cases`` only.
* Abstract calls carry the configuration at the moment of the call.

The ``result.json`` of section 1 holds that witness for the swapped model of the
working query.  The next script prints the label of the path that ran outside every
region and the local cases of each step, then the replay outcome.

.. testcode::

   import json

   with open("result.json", encoding="utf-8") as stream:
       result = json.load(stream)
   for step in result["witness"]["steps"]:
       print("step %d: case_label=%s" % (step["index"], step["case_label"]))
       for case in step["local_cases"]:
           print("    scope=%s kind=%s" % (case["scope"], case["kind"]))
   print("replay ok=%s mismatches=%d" % (result["replay"]["ok"], len(result["replay"]["mismatches"])))

.. testoutput::

   step 0: case_label=__init__::initial::Controller.Idle::0
       scope=None kind=initial
   step 1: case_label=Controller.Idle::fallback::Controller.Idle::0
       scope=None kind=fallback
   step 2: case_label=Controller.Idle::transition::Controller.Running::0
       scope=None kind=transition
       scope=Controller.Running kind=initial
       scope=Controller.Running kind=initial
   step 3: case_label=None
       scope=Controller.Running.Motion kind=transition
       scope=Controller.Running.Safety kind=fallback
   replay ok=True mismatches=0

Frame 4 of section 1 is the counterexample frame: ``Motion`` is ``On`` after the fault cycle.
Step 2 lists the transition into ``Running`` with ``scope=None`` and then one
initial path per region, in written order.  Step 3 has ``case_label=None``
because no path ran outside the regions, and two local cases: ``Motion`` switched
on and ``Safety`` fell back.  ``Motion`` is listed first because it is written
first in this model.

The human report prints the same cases as lines of a trace.  A scope is written
relative to the state the machine rests in outside every region, at one end of the
step, so regions that share a name below different owners read differently; the
owner itself reads as its own last name segment, ``[start]`` stands for the entry
of a scope and ``[done]`` for a region that finished.  The line
``Running: [start] -> Motion.Off [initial]`` of the report above is the entry of
region ``Motion`` as part of the owner ``Running``.

Replay runs the witness through ``SimulationRuntime`` and compares, for models with
regions, the following in addition to what
:doc:`/explanations/bmc_solving/index` lists: the configuration of each frame, the
transitions each step committed (which is what checks ``case_label`` and
``local_cases``), and, for each abstract call, its configuration.  The last line of
the output shows ``replay ok=True mismatches=0``.  A mismatch is not a verdict
about the model; it means the encoding and the simulator disagree, and the
command line reports ``EVIDENCE/REPLAY MISMATCH; RESULT UNTRUSTED`` with exit
status 4.  Replay succeeding is
evidence that the witness is a real execution, not a proof that the encoding is
complete.

8. Where construction stops
----------------------------

The encoding does not approximate.  Where it cannot build a bounded formula it
raises an error.

A group that enters itself again in the same cycle is the shape the relation
unrolls instead of refusing outright.  An owner :math:`O` with a transition back to itself that
fires right after its regions finished re-enters on the values the first
entry left.  The encoding keeps the list :math:`\mathcal{E}` of the entries it is
deciding on the current path and applies two rules:

.. math::
   :label: eq-region-group-reentry

   \begin{aligned}
   \bigl(\exists\,(O,\eta')\in\mathcal{E}:\ \eta'\equiv\eta\bigr) &\Rightarrow
     \mathrm{Accept}_O(\eta)=\bot,\\
   \bigl|\{\,(O',\eta')\in\mathcal{E} : O'=O\,\}\bigr|\ \ge\ L &\Rightarrow
     \mathrm{BuildError}.
   \end{aligned}

The first rule recognizes a loop: the same owner entered again on identical
symbolic values cannot change anything, so that path is rejected, as the simulator
rejects it.  ``\equiv`` here means identical symbolic expressions, not merely
equal numbers.  The second rule bounds the unrolling: when the same owner is
already being entered :math:`L` times on the path, the build raises
``BmcBuildError`` instead of guessing.  :math:`L` is
``BmcOptions.max_group_reentries``, 16 by default.

The first model changes ``n`` in every lap and stops after six laps.  It needs
seven entries, so the default 16 builds it.

.. literalinclude:: laps.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: spin.fbmcq
   :language: fbmcq

The next script builds the formula of ``laps.fcstm`` with two limits through the
Python API.  The command line has no option for the limit.

.. testcode::

   from pyfcstm.bmc import BmcBuildError, BmcOptions, compile_bmc_query
   from pyfcstm.model import load_state_machine_from_text

   with open("laps.fcstm", encoding="utf-8") as stream:
       model = load_state_machine_from_text(stream.read())
   with open("spin.fbmcq", encoding="utf-8") as stream:
       query = stream.read()
   for limit in (7, 6):
       try:
           compile_bmc_query(model, query, options=BmcOptions(max_group_reentries=limit))
           print("max_group_reentries=%d: built" % limit)
       except BmcBuildError as err:
           print("max_group_reentries=%d: BmcBuildError: %s" % (limit, err))

.. testoutput::

   max_group_reentries=7: built
   max_group_reentries=6: BmcBuildError: state 'Root.Spin' re-enters its own group more than 6 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.

Seven allows six laps and the default 16 allows it too; six is one too few, and the
error names the owner, the limit and the option.  The second model, ``spin.fcstm``,
bounds its laps by an input, so no limit is enough.  Through the command line the
same error appears as an unexpected-error banner and exit status 1, because the
command does not yet turn this build error into a controlled diagnostic.  This is a
negative example; do not copy the model.

.. literalinclude:: spin.fcstm
   :language: fcstm
   :linenos:

.. code-block:: console

   $ pyfcstm bmc -i spin.fcstm -q spin.fbmcq
   Unexpected error found when running pyfcstm!
   Traceback (most recent call last):
   ...
   _BmcCliInternalError: state 'Root.Spin' re-enters its own group more than 16 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.
   $ echo $?
   1

Three more limits are separate from this one.

* One query expression may nest at most 100 levels.  A longer chain is refused with
  ``expression_too_deep`` before anything is built; split it over several
  ``assume`` or ``check`` clauses.
* The macro-step expander has fixed guards that regions inherit and that no
  option changes: at most 1000 micro-steps and a stack depth of 64 on one path.
  They bound one path through a unit.  This page makes no claim about how deeply
  regions may nest.
* The macro-step expander refuses a path that returns to a state while it runs
  actions, an action-dependent loop, and a search limit that the simulator raises
  at run time has no bounded counterpart.  Of the shared semantic cases that
  declare regions, four search-limit cases, three action-dependent loops and one
  re-entry past the unroll depth are therefore excluded from the differential
  check against the simulator.  Four more region cases are excluded for other
  reasons: two need a hot start whose variables the caller must give completely,
  and two need a short event name that the query language never uses.

.. testcode::

   from pyfcstm.bmc import InvalidBmcQuery, compile_bmc_query
   from pyfcstm.model import load_state_machine_from_text

   with open("blocked.fcstm", encoding="utf-8") as stream:
       model = load_state_machine_from_text(stream.read())
   for terms in (50, 150):
       query = "check reach <= 1: %s;" % " && ".join(["true"] * terms)
       try:
           compile_bmc_query(model, query)
           print("%d terms: compiled" % terms)
       except InvalidBmcQuery as err:
           print("%d terms: InvalidBmcQuery: %s" % (terms, err))

.. testoutput::

   50 terms: compiled
   150 terms: InvalidBmcQuery: expression_too_deep at query: an expression nests deeper than 100 levels; split the chain of operators across several assume or check clauses.

Fifty terms compile; one hundred and fifty terms are refused at compile time.
Through the command line the same refusal is the line ``Failed to compile BMC
query: expression_too_deep ...`` with exit status 1 and no trace.

9. Known differences from the simulator
----------------------------------------

The relation requires every operation on the chosen path to be defined, so a cycle
in which the simulator raises has no solution there.  Two kinds of evaluation are
different: the simulator also evaluates operations on a candidate path that later
dead-ends, and on a lower-priority continuation of a finished group that a higher
one wins over, and it raises if those fail.  The relation does not require them
to be defined, so the core formula can be satisfiable on a cycle in which the
simulator raises.  The dead-end shape is not specific to regions: the runtime-safety
stage reports the same shape in a model without regions.

Runtime safety is the stage that closes this gap, and it runs before the property
by default.  It lowers the cycles a second time to locate every operation of every
region, including the probes of candidates that were not chosen and the
operations of regions that cannot start.  The next script runs two models: in
``dead_end.fcstm`` a candidate leads into a pseudo state and its effect divides by
the input; in ``outranked.fcstm`` the guard of a lower-priority continuation
divides by the input.  The third command turns the check off.

.. literalinclude:: dead_end.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: outranked.fcstm
   :language: fcstm
   :linenos:

.. code-block:: console

   $ pyfcstm bmc -i dead_end.fcstm -q dead_end.fbmcq --color never
   BMC reach <= 2: RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED
   ...
     Runtime error: modulo_by_zero at step 1
     Runtime error location: action block transition_effect in transition Root.Run.R.C::0::INIT_STATE->J
   ...
     Replay: runtime error reproduced: operation assignment to 'x' evaluation failed: integer ...modulo by zero
   ...
   $ echo $?
   5
   $ pyfcstm bmc -i outranked.fcstm -q outranked.fbmcq --color never
   BMC reach <= 3: RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED
   ...
     Runtime error: modulo_by_zero at step 1
     Runtime error location: guard g1 in transition Root.Q::1::Q->T2
   ...
     Replay: runtime error reproduced: transition guard evaluation failed: integer ...modulo by zero
   ...
   $ echo $?
   5
   $ pyfcstm bmc -i dead_end.fcstm -q dead_end.fbmcq --color never --no-runtime-safety
   Unexpected error found when running pyfcstm!
   Traceback (most recent call last):
   ...
   SimulationRuntimeExpressionError: operation assignment to 'x' evaluation failed: integer ...modulo by zero
   $ echo $?
   1

With the default, both models report ``RUNTIME ERROR REACHABLE WITHIN BOUND`` with
exit status 5, the failing operation, and the confirmation that the runtime
reproduced the error.  With ``--no-runtime-safety`` the property query on
``dead_end.fcstm`` finds a witness, and the replay raises the simulator's own
error: the command line prints the unexpected-error banner and exits with 1, not
with 4.  Turn the check off only when you know the model cannot divide or index
out of range; the result then depends on that assumption.

10. Equation ledger
-------------------

The table is the forward audit map for the five equations of this page.  Names
refer to ``pyfcstm/bmc/region_relation.py`` unless noted; the tests live in
``test/bmc/test_region_relation.py`` unless noted; the queries run on the models
shown above.

.. list-table:: Region equation ledger
   :header-rows: 1
   :widths: 18 22 24 18 18

   * - Equation
     - Implementation anchor
     - Test anchor
     - Working query
     - Trace
   * - :eq:`eq-region-position-domain`
     - ``region_frame_constraints``, ``_owner_resting``;
       ``BmcTraceSymbols.region_position`` in ``relation.py``
     - ``test_a_resting_owner_never_has_every_region_done``,
       ``test_regions_are_inactive_exactly_while_their_owner_does_not_rest``
     - ``interlock.fbmcq``
     - Configurations of frames 0 to 4 in section 1
   * - :eq:`eq-region-value-chain`
     - ``_StepBuilder.advance_group``, ``region_env``
     - ``test_the_earlier_region_decides_before_the_later_one_looks``,
       ``test_swapping_the_regions_delays_the_stop_by_one_cycle``
     - ``interlock.fbmcq`` on both orders
     - Frames 3 and 4 of section 1 (section 2)
   * - :eq:`eq-region-owner-start`
     - ``_StepBuilder.entry`` (``ok`` and the continuation check)
     - ``test_regions_start_in_declaration_order_on_the_values_left_behind``,
       ``test_a_group_that_cannot_start_leaves_a_cold_start_delta``
     - ``blocked_free.fbmcq``, ``blocked_stuck.fbmcq``
     - Two ``[delta]`` steps with ``g == 0`` (section 3)
   * - :eq:`eq-region-joint-completion`
     - ``_StepBuilder.done_viable``, ``build_owner_source``
     - ``test_the_last_region_may_finish_only_if_the_owner_can_continue``,
       ``test_once_the_owner_can_continue_the_finish_and_the_hand_over_are_one_cycle``
     - ``joint_all_done.fbmcq``, ``joint_blocked_next.fbmcq``
     - Five headlines in section 4
   * - :eq:`eq-region-group-reentry`
     - ``_StepBuilder.entry`` (``_entering``), ``BmcOptions.max_group_reentries``
     - ``test_the_depth_a_group_may_re_enter_itself_is_an_option``,
       ``test_a_loop_that_no_value_can_stop_cannot_be_bounded``
     - ``spin.fbmcq`` on ``laps.fcstm`` and ``spin.fcstm``
     - Three limits in section 8

Sphinx checks that the references resolve and a drift check compares the labels
and LaTeX of the English and Chinese pages.  Neither proves the claims.  A reviewer
has to read each row against the code, the test and the trace.

What the page establishes, and what it does not:

* Fact, shown by the queries above: the written order changes the verdict of the
  interlock query; the configurations of the frames follow the position
  constraints; a region that cannot start rejects the cold start; the last region is refused
  without a continuation; the two limits and the two known differences behave as
  printed.
* Fact, shown by tests rather than by a run on this page: the tests named in
  the ledger and in sections 4 and 6, for example the state a handler is told for
  an aspect over a group.
* Inference: that the encoding agrees with the simulator on shapes the shared
  semantic cases and the random differential models do not contain.  The
  differential check is evidence, not a proof, and the replay of every witness is
  the second line of defence.
* Not covered here: how solver time grows, which is on
  :doc:`/explanations/bmc_scaling/index`.

See also
--------

* :doc:`/explanations/bmc_semantics/index` derives the relation for models without
  regions, on which this page builds.
* :doc:`/explanations/bmc_solving/index` covers solving, verdicts, witnesses and
  replay.
* :doc:`the FBMCQ reference </reference/bmc_query/index>` documents the ``active``
  patterns, ``init state`` and the diagnostic codes of this page.
* :doc:`/explanations/region_semantics/index` defines the cycle that the encoding
  follows.
