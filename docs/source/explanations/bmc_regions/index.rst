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

.. literalinclude:: ../../tutorials/regions/controller.fcstm
   :language: fcstm
   :linenos:

The question is whether the motor can still be on while ``permit`` is already
0.  The query asks for a counterexample within four macro-steps: cold start,
``/Start``, a request, and a fault that arrives together with the request.

.. literalinclude:: interlock.fbmcq
   :language: fbmcq

``forbid`` searches for a frame where ``motor`` is 1 and ``permit`` is 0.  The
command below runs it on the model as written and on
``controller_swapped.fcstm``, which differs only in that ``Motion`` is written
before ``Safety``.  The script cuts the one line that prints solver time, so the
output is the same on every run.

.. literalinclude:: interlock.demo.sh.txt
   :language: text

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

The next script pins the four cycles of the working query (inputs and the
``Start`` event), solves the core formula, and prints the position of each region
and the two variables for every frame.  It is optional verification
infrastructure; the full source is
:download:`positions.demo.py <positions.demo.py>`.  The lines that read the
symbols are ``symbols.region_position(frame, path)`` for a position and
``symbols.frame_var(frame, name)`` for a variable.

.. literalinclude:: positions.demo.py.txt
   :language: text

Look at the ``controller`` block.  In frames 0 and 1 the machine is in the init
sentinel and in ``Idle``, the owner does not rest, and both positions are
``INACTIVE``.  In frame 2 the owner rests and ``Safety`` and ``Motion`` hold
``Watching`` and ``Off``.  No frame has a position that is not a state id of its
own region, ``DONE`` or ``INACTIVE``, which is the first two lines of
:eq:`eq-region-position-domain` at work.  The block shows one execution and does
not prove the constraint; the tests do the proving.

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

The script of section 1 also prints the values handed on in the fault cycle,
read from the intermediate symbols of the solved model.  The symbol names are an
implementation detail; the script reads them only to show the hand-over.

.. literalinclude:: positions.demo.py.txt
   :language: text
   :lines: 1,7-9,10,16-18

The excerpt keeps the fault cycle of each model.  With ``Safety`` first, the
vector after region 1 has ``permit=0`` and ``motor=1``: ``Safety`` took the permit
away and ``Motion`` has not moved yet.  ``Motion`` then reads ``permit=0`` and
leaves ``motor=0``.  With ``Motion`` first it reads ``permit=1``, stays on, and
``Safety`` clears the permit afterwards, so frame 4 of the second block holds
``motor=1`` with ``permit=0``.  That is the counterexample the ``forbid`` query found.  The
excerpt shows that the chain is ordered; it does not show how Z3 finds it.

Why the formula is a sum
~~~~~~~~~~~~~~~~~~~~~~~~

Each :math:`\mathrm{Run}_{t,i}` is lowered from the units of region :math:`R_i`
alone, and the units connect only through :math:`\xi_t^{(i)}`.  A flat expansion
would instead need one path per combination of the regions' paths.  The next
script counts the paths that one working cycle lowers to, for one to eight
regions that each toggle between two states on their own event.

.. literalinclude:: lowered_paths.demo.py.txt
   :language: text

Each region adds four lowered paths: two resting positions times two outcomes,
transition or fallback.  Two more are present at any region count: the cold-start
path out of the init frame and the continuation of the root after all regions
finish.  The third column is the number of combined paths a flat expansion would
need under the same description.  The counts show that the lowered paths grow
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
   \mathrm{Accept}_O(\eta) &\equiv \bigwedge_{i=1}^{n}\mathrm{ok}_i.
   \end{aligned}

:math:`\mathrm{Init}_i` is the relation of the first committable initial path of
region :math:`R_i`.  It is asserted only when every earlier region started, so a
region behind one that cannot start assigns nothing and none of its operations has
to be defined.  :math:`\mathrm{Accept}_O` is the condition under which the path
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

.. literalinclude:: owner_start.demo.sh.txt
   :language: text

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

The script asks five questions and prints each query with the headline of its
report.

.. literalinclude:: joint_completion.demo.sh.txt
   :language: text

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
order for two models.

.. literalinclude:: aspect_order.demo.sh.txt
   :language: text

In the first model, ``Pre`` and ``Post`` are the root's aspects and ``PostA`` is
declared inside region ``A``.  Every step calls ``Pre`` first and ``Post`` last,
and ``PostA`` runs right after ``WorkA``, before ``WorkB`` starts: the branch of
``A`` ended, so its ``after`` action settled before ``B``'s turn.  In the second
model ``Prep`` is the owner's plain ``during before`` and it precedes both
``enter`` actions of the regions.  The two models are in
:download:`aspects.fcstm <aspects.fcstm>` and
:download:`plain_before.fcstm <plain_before.fcstm>`.  The output shows call order
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

.. literalinclude:: hot_start.demo.sh.txt
   :language: text

The trace starts in ``Controller.Running{Safety: [init], Motion: On}``.  Step 0 has
two lines: ``Running: [start] -> Safety.Watching [initial]`` starts the pending
region, and ``Motion: On -> On [fallback]`` runs ``Motion``'s ``during``.  No line
enters ``Motion``, because it was put in place.

A start that leaves every region of an owner done is refused when the query is
compiled, since no frame can hold that position (the third line of
:eq:`eq-region-position-domain`).  This is a negative example; the query is
refused on purpose.

.. literalinclude:: hot_start_refused.demo.sh.txt
   :language: text

The diagnostic code is ``invalid_start_position`` and the exit status is 1; no
JSON result is written.  A text that is not a position of the model is refused
with the same code.

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
(``test_an_aspect_over_a_group_reports_the_owner_and_over_a_region_its_leaf``).
The model of the next script enters ``O``, finishes both regions and
enters ``O`` again in the second step.

.. literalinclude:: reenter.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: call_snapshots.demo.sh.txt
   :language: text

Read the pairs.  In step 0 the enter of ``Q`` (region ``B``) sees ``A`` already at
``P``: ``A`` moved first.  The enter of ``P`` in step 0 sees ``B`` as ``[init]``.
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

The next script solves the swapped model from the working query to JSON and prints
three views of the witness with
:download:`show_witness.py <show_witness.py>`.

.. literalinclude:: witness_regions.demo.sh.txt
   :language: text

Frame 4 is the counterexample frame: ``Motion`` is ``On`` after the fault cycle.
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

The next script builds the formula with three limits through the Python API.  The
command line has no option for the limit.

.. literalinclude:: group_reentry.demo.py.txt
   :language: text

Seven allows six laps and the default allows it too; six is one too few, and the
error names the owner, the limit and the option.  The second model, ``spin.fcstm``,
bounds its laps by an input, so no limit is enough.  Through the command line the
same error appears as an unexpected-error banner and exit status 1, because the
command does not yet turn this build error into a controlled diagnostic.  This is a
negative example; do not copy the model.

.. literalinclude:: spin.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: group_reentry.demo.sh.txt
   :language: text

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
  check against the simulator.

.. literalinclude:: expression_depth.demo.sh.txt
   :language: text

Fifty terms build and the property holds; one hundred and fifty terms are refused
at compile time, with exit status 1 and no trace.

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

.. literalinclude:: known_differences.demo.sh.txt
   :language: text

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
     - Positions of frames 0 to 4 in section 1
   * - :eq:`eq-region-value-chain`
     - ``_StepBuilder.advance_group``, ``region_env``
     - ``test_the_earlier_region_decides_before_the_later_one_looks``,
       ``test_swapping_the_regions_delays_the_stop_by_one_cycle``
     - ``interlock.fbmcq`` on both orders
     - Values handed on in step 3 (section 2)
   * - :eq:`eq-region-owner-start`
     - ``_StepBuilder.entry``
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
  interlock query; the three position markers appear where the equations say; a
  region that cannot start rejects the cold start; the last region is refused
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
