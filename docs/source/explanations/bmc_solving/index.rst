:orphan:

BMC solving, witnesses, and replay boundaries
================================================

Bounded model checking (BMC) turns one finite execution horizon into a Z3
query.  The solver result, however, is only the first of three distinct claims:

* solving says whether a bounded objective has a model;
* decoding projects a SAT model into a public macro-step trace; and
* replay checks that the projected observations agree with
  :class:`~pyfcstm.simulate.runtime.SimulationRuntime`.

Keeping those claims separate is essential.  A SAT result can carry a useful
witness without proving anything beyond the selected bound.  A successful
replay can expose agreement between the SMT encoding and the runtime without
proving that either implementation is complete for every possible trace.


The claim ladder is deliberately one-way:

.. list-table:: Solve/decode/replay claim ladder
   :header-rows: 1
   :widths: 14 24 30 32

   * - Layer
     - Input
     - Claim it can make
     - Claim it cannot make
   * - Solve
     - :math:`C_N`, the property objective, and optional tail observation
     - The bounded SMT formula is SAT, UNSAT, unknown, or timed out.
     - It does not expose a public trace or prove runtime agreement.
   * - Decode
     - A SAT model from the main solve
     - The model can be projected into a public macro-step trace.
     - It does not decide whether the trace is a desired behavior or a violation; polarity does that.
   * - Replay
     - The decoded public trace
     - The decoded observations agree with ``SimulationRuntime`` on this finite trace.
     - It does not prove all models decode, all cases are encoded correctly, or the property holds beyond :math:`N`.

One incremental solver, staged feasibility
------------------------------------------

Let :math:`D_N` be the bounded domain, :math:`I_0` the retained initializer,
:math:`T_N` the macro-step transition relation, and :math:`ENV_N` the query
environment constraints.  The solver keeps the following cumulative spaces:

.. math::
   :label: bmc-solve-formulas

   K_N = D_N \land T_N,
   \qquad S_{\mathrm{init}} = K_N \land I_0,
   \qquad S_{\mathrm{assume}} = S_{\mathrm{init}} \land ENV_N.

For a compiled property objective :math:`Obj_q`, the primary query is
:math:`\Phi_q = S_{\mathrm{assume}} \land Obj_q`.

The primary result is interpreted first.  If it is UNSAT, the solver checks
:math:`S_{\mathrm{assume}}` and, only when necessary, :math:`S_{\mathrm{init}}`
and :math:`K_N` to distinguish an objective-only UNSAT from an infeasible
scenario.  These checks are staged on one incremental solver; SAT prefix
evidence may be marked ``inferred`` rather than being solved again.

For a response property, :math:`\Omega_q` denotes the observation that an
obligation remains beyond the bound, and the optional suffix query is
:math:`\Psi_q = S_{\mathrm{assume}} \land \Omega_q`.

It is evaluated only after :math:`S_{\mathrm{assume}}` is known SAT and only
when ``check_incomplete`` is enabled and the suffix formula is non-trivial.
The suffix model is an ``incomplete_suffix`` role; it does not turn an
incomplete response into a property verdict.

:func:`pyfcstm.bmc.witness.solve_bmc_property` creates one incremental solver
and one shared budget per public solve.  ``timeout_ms=None`` does not install a
Z3 timeout.  A finite ``timeout_ms`` is a monotonic total budget shared by the
primary, feasibility, and applicable suffix checks; each check receives only
the remaining milliseconds.  When the budget is exhausted, later checks are
not called and their evidence remains ``not_checked``.

Z3's ``unknown`` result is split by ``reason_unknown()``: the exact reason
``"timeout"`` becomes public status ``timeout``; other reasons remain
``unknown``.  Neither status carries a model.  Main elapsed time is stored in
``elapsed_ms``; suffix elapsed time is retained as
``incomplete_elapsed_ms=...``.  Disabling the suffix check is observable as
``incomplete_check=disabled`` rather than being treated as a proof that no
incomplete suffix exists.

Verdicts are polarity-aware
---------------------------

SAT has opposite meanings for the two property families.  ``reach``,
``exists_always``, and ``cover`` use witness polarity: SAT finds the behavior
requested by the property.  ``forbid``, ``invariant``, ``must_reach``, and
``response`` use counterexample polarity: SAT finds a violation.

Write :math:`p \in \{W,C\}` for witness or counterexample polarity,
:math:`q` for the property kind, :math:`s` for the main solver status, and
:math:`t` for the response-tail solver status.  The incomplete condition is
deliberately narrow: only counterexample-polarity ``response`` with a main
UNSAT result and a bad tail status is incomplete.  A tail result cannot weaken a
main SAT response counterexample and cannot affect any other property kind.  The
public three-valued property verdict is:

.. math::
   :label: bmc-verdict-map

   \begin{aligned}
   T_{\mathrm{bad}}(t)&\equiv
   t\in\{\mathrm{sat},\mathrm{unknown},\mathrm{timeout},
   \mathrm{unchecked}\},\\[0.4em]
   H(p,q,s,t)&\equiv
   (p=C)\land(q=\mathrm{response})\land(s=\mathrm{unsat})\land
   T_{\mathrm{bad}}(t),\\[0.4em]
   V(p,q,s,t)&=
   \begin{cases}
   \top,
      & (p=W \land s=\mathrm{sat})
        \lor (p=C \land s=\mathrm{unsat} \land \neg H(p,q,s,t)), \\
   \bot,
      & (p=W \land s=\mathrm{unsat})
        \lor (p=C \land s=\mathrm{sat}), \\
   ?, & s \in \{\mathrm{unknown},\mathrm{timeout}\} \lor H(p,q,s,t).
   \end{cases}
   \end{aligned}

This is the implementation behind ``BmcSolveResult.property_satisfied``.  The
stable ``outcome`` strings refine the same map:

.. list-table:: Solver status to public outcome
   :header-rows: 1

   * - Polarity / property
     - Main status
     - Tail condition
     - ``outcome``
   * - witness
     - ``sat``
     - irrelevant
     - ``witness_found``
   * - witness
     - ``unsat``
     - irrelevant
     - ``no_witness``
   * - counterexample
     - ``sat``
     - irrelevant
     - ``property_violated``
   * - counterexample
     - ``unsat``
     - absent, irrelevant, or tail proved UNSAT
     - ``property_satisfied``
   * - counterexample ``response``
     - ``unsat``
     - tail bad: unchecked, SAT, unknown, or timed out
     - ``incomplete``
   * - either
     - ``unknown`` / ``timeout``
     - irrelevant
     - ``unknown`` / ``timeout``

A response counterexample is decisive as soon as the main formula is SAT.  A
simultaneously satisfiable tail observation does not weaken that concrete
violation.  The asymmetric special case exists only for main UNSAT: before
claiming satisfaction, the implementation must exclude a trigger whose full
response window falls beyond frame :math:`N`.


Generic witnesses and counterexamples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The witness schema is generic: it records a SAT model for the main objective.
For witness-polarity properties, that generic witness is the behavior the user
asked to find.  For counterexample-polarity properties, the same decoded schema
records a counterexample because SAT means the violation objective was
satisfied.  The word ``counterexample`` therefore names the interpretation of a
primary SAT result, not a separate trace format.

A tail SAT model for ``response`` incompleteness is different.  It supports the
``incomplete`` horizon diagnostic, but it is not decoded and replayed as the
primary user witness because the main objective was UNSAT.  Conversely, when the
main response objective is SAT, the decoded primary trace remains a decisive
counterexample even if a separate tail observation is also satisfiable.

From a model to a public witness
--------------------------------

The raw Z3 model contains solver symbols and implementation details.  It is not
the public witness schema.  :func:`pyfcstm.bmc.witness.decode_bmc_witness`
projects the model onto :math:`N+1` frame observations and :math:`N` macro-step
observations:

.. math::
   :label: bmc-witness-projection

   \pi(M)=
   \left\langle
     (q_i,\mathbf{x}_i,\iota_i,\tau_i)_{i=0}^{N},
     (c_i,\Delta_i,\Gamma_i,I_i,U_i,A_i)_{i=0}^{N-1}
   \right\rangle.

Here :math:`q_i` and :math:`\mathbf{x}_i` are the public state path and
persistent variables; :math:`\iota_i` and :math:`\tau_i` mark the initial and
terminated sentinels.  Each step records the selected case :math:`c_i`, delta
and gamma progress flags, sparse replay inputs :math:`I_i`, ordered event
accounting :math:`U_i` (consumed and derived unconsumed events), and abstract
call records :math:`A_i`.

The projection is deliberately sparse.  True event Booleans are included in
``input_events`` only when the selected case, an explicit true assumption, or
response-property support needs them for replay.  Negative assumptions and
other inspected event values may appear in ``event_reads`` as debugging data,
but they are not passed to ``runtime.cycle()``.  Case labels, ``gamma``, and
``progress`` remain witness-side explanations; ``delta`` is also emitted as a
public runtime-step observation and is checked during replay.

Decoding therefore has a strict caller boundary: it accepts a compiled formula
and a ``z3.ModelRef`` that the caller obtained from the SAT main solve.  It does
not perform a third satisfiability check.  Invalid model values, a missing or
multiply selected case, and inconsistent internal event support fail loudly as
``BmcBuildError`` because silently manufacturing a partial trace would make
replay evidence meaningless.

Replay agreement and its limits
--------------------------------

Replay initializes ``SimulationRuntime`` from the witness's public initial
metadata, calls ``cycle()`` with only each step's sparse input-event paths, and
records runtime frames, event accounting, and abstract handler contexts.  Let
:math:`W` be the decoded trace and :math:`R(W)` that captured runtime trace.
The success flag is the conjunction of the public comparisons:

.. math::
   :label: bmc-replay-agreement

   \operatorname{ok}(W)
   \iff
   \bigwedge_{i=0}^{N}
      \operatorname{eq}_{F}(W.F_i,R(W).F_i)
   \land
   \bigwedge_{i=0}^{N-1}
      \operatorname{eq}_{S}(W.S_i,R(W).S_i),

where frame equality covers state, termination, persistent-variable keys and
values, and step equality covers input, consumed and unconsumed events, the
``delta`` result, plus ordered abstract-call metadata and snapshots.
Floating-point values use the
explicit replay tolerance rather than bitwise equality.  The initial sentinel
is compared against the runtime state produced by cold initialization, not
mistaken for an ordinary state path.

The following trace shows the ownership boundary for a one-step transition:

.. list-table:: SAT model to replay verdict
   :header-rows: 1

   * - Stage
     - Input
     - Observable result
   * - Solve
     - :math:`C_1 \land Q_1`
     - ``sat`` and one Z3 model
   * - Decode
     - model symbols ``F_0_*``, ``F_1_*``, ``E_0_*``, ``C_0_*``
     - two frames; selected transition; sparse input event; event accounting
   * - Replay
     - initial metadata plus the sparse input event
     - two runtime frames and one captured runtime step
   * - Compare
     - decoded and runtime observations
     - ``ok=True`` only when every comparison in :eq:`bmc-replay-agreement` holds

Case labels and solver-only progress flags are intentionally absent from
:math:`\operatorname{eq}_S`.  A runtime cannot disagree about information it
does not publish.  Conversely, ``delta``, event consumption, and abstract-call snapshots
are included because matching only the final state would miss behaviorally
important divergence.

Counterexample: replay is not a proof of the encoder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose a decoded witness says that frame 1 has ``x=2``, while the runtime
reaches the same state with ``x=1``.  Replay returns structured evidence such
as:

.. code-block:: text

   ok: false
   path: frames[1].vars.x
   expected: 2
   actual: 1
   message: value mismatch

This falsifies alignment for that witness; matching state names alone cannot
hide the variable-effect error.  The converse is weaker: ``ok=True`` proves
agreement only for the decoded public observations on this finite trace.  It
does not prove that unselected cases are encoded correctly, that all SAT models
decode, that the query is true beyond :math:`N`, or that BMC and the runtime do
not share the same modeling mistake.

Where a conflict lies, and why the answer is exclusive
------------------------------------------------------

When the scenario is infeasible, the first useful question is not *which clause*
but *which part*.  The staged solve already answers it: the kernel, the
initialization, and the assumptions enter the solver in that order, so the stage
at which satisfiability is lost identifies the family.  A kernel that is already
unsatisfiable is a ``kernel_conflict`` and implicates the model rather than the
query.  A kernel that holds until ``init`` arrives gives an
``initialization_*`` family; one that holds until ``assume`` arrives gives an
``assumptions_*`` family.

Within a family the three members are distinguished by *what the new clauses
disagree with*.  ``*_self_conflict`` means the new clauses contradict each other
and would fail with nothing else present.  ``*_domain_conflict`` means each is
individually consistent but together they leave a frame with no legal value --
they exceed what the frame domain allows.  ``assumptions_prefix_conflict`` (and
its initialization counterpart) means the clauses are consistent with the domain
too, and only the transition relation rules them out: nothing the machine can do
reaches the required combination.

The seven values are exclusive because each is decided by the first stage or
sub-check that fails, and the checks are ordered.  That is why the report prints
one classification rather than a set, and why a reader can act on it: the
classification names the file they should open.


Sufficient is not minimal
-------------------------

The solver's own unsat core is *sufficient*: removing all of it makes the
formula satisfiable.  It is not *minimal*: it may contain clauses that play no
part in the conflict, because the solver stops as soon as it has enough.  A
reader handed a sufficient core has to guess which members matter.

Minimization removes the guesswork by testing each member: drop it, re-solve,
and keep the drop only if the remainder is still unsatisfiable.  A core that
survives this for every member is ``subset_minimal`` -- every member is load
bearing, so every member is worth reading.  The published claim distinguishes
the two states honestly: ``raw`` when no member was tested,
``partial_minimized`` when the budget ran out mid-way, ``subset_minimal`` when
all of them were.

This matters because minimality is what makes the next stage possible at all.  A
proof step has to say which core member it restates, and a sufficient-only core
has members that restate nothing.


What the proof is trusted on
-----------------------------

A published proof is a claim that each step was checked.  The interesting design
question is *by whom*, because a checker that shares code with the constructor
agrees with it by construction and proves nothing.

Four methods divide the work.  Input nodes use ``core_binding``: the normalized
fact is re-encoded from scratch and the solver is asked to refute both
``group => fact`` and ``fact => group``.  Both directions are required.  One
direction alone would allow a fact that is merely *implied by* the core member,
which is a summary rather than a restatement -- and a summary can drop exactly
the detail a reader needed.  If either direction comes back satisfiable, unknown,
or times out, the proof does not reach ``complete``.

Derived and root nodes use ``rule_checker``: an independent checker takes the
premises and the claimed conclusion and re-derives it, without calling the code
that produced it.  It compares whole conclusion mappings rather than selected
fields, and refuses a conclusion carrying a field it does not recognize, so a
constructor that quietly adds information cannot slip it past.

``solver_entailment`` covers derived and root steps the solver discharges instead.
``case_condition_entailment`` is one: whether the core members establish a case's
condition is a question about their constraints, and a rule checker sees only the
published facts, which do not contain it.  The node names the members that entail
the condition, and those members are asserted to be a subset of the published core
-- a step resting on something outside it would break the minimality the proof
claims for its own leaves.

A group that holds one requirement per case is a conjunction, and no single fact
can imply the whole of it -- so an input restating one of those requirements uses
``core_binding_unit`` instead.  The same two directions are refuted, against that
one requirement rather than against the group, and the node names which one it was
through ``unit_index`` beside ``unit_count``.  The pair is what lets a reader see
the proportion covered: "requirement 5 of 12" says something that "the transition
relation" does not.  A fact equivalent to two requirements identifies neither, so
the binding is refused rather than resolved -- an index a reader cannot rely on is
worse than no index.

The step relations are the only groups that decompose this way, so a query whose
core rests on one of their cases is where the pair is published: such an input
carries ``core_binding_unit`` while the other members of the same core carry
``core_binding``, and a reader sees which requirement of the relation the case
restated.  For a while the pair was defined and never published, because the
attribution stopped at the binding check and never reached the node -- a gap that
read from the outside exactly like a method no query could produce.

The boundary is therefore: **a reader may trust that each sentence follows from
the core members named beside it, and may not trust that the encoding faithfully
models their intent.** The proof is about the constraints as encoded.  That is
the same boundary replay draws for a witness, for the same reason.


Why some conflicts have no proof
---------------------------------

The proof depth degrades rather than fabricating, and the reason is structural
rather than incidental.

An input node stands for one core member, and the core is the set of *authored*
clauses plus generated support groups.  A fact about an intermediate frame -- what
a variable holds after two steps, for instance -- is not authored anywhere; it is
*derived* from a transition rule.  So a conflict that only becomes visible after
accumulating across steps has no core member to attribute its key facts to, and
the closure has nowhere to start.  Such a query reports ``achieved_mode`` as
``formal``.

For those conflicts the formal explanation is not a lesser answer.  It names the
classification, the subset-minimal core and every source location, and its
narrative can name the initial state and the conflicting values -- which a proof
built without the intermediate facts would lose.  A reader chasing a cross-step
conflict is better served by ``formal`` today, and the report says so in its
``reason`` line rather than leaving them to wonder.

Three rules were out of reach for one shared reason until recently, and the account
is kept here because the shape it describes is still what a reader meets.  A case
publishes the assignment it makes, but the assignment holds *where the case
applies*, and the evaluation rule refuses an expression carrying a condition --
rightly, since "``x`` increases by one under C" together with "``x`` is 0" does not
give "``x`` is 1" unless C is established.  Nothing established it, so
``transition_assignment`` had no usable premise, and ``equality_substitution`` and
``arithmetic_evaluation`` waited one step further back on the
``arithmetic_expression`` it produces.

``case_condition_entailment`` establishes it.  The condition is proved from the core
members themselves rather than from their published facts -- the members that put the
machine in the state a case names include the step relation that got it there, and a
step relation publishes as ``structural_constraint``, content no reader sees.  So the
solver does that step, the node cites the members it used, and it records
``solver_entailment`` rather than ``rule_checker`` because no predicate over the
premises could have settled it.  The translation from core members to proof facts
emits seven kinds and none of them is an ``arithmetic_expression``, so that fact
still has exactly one producer and the chain still starts where it always would
have -- what changed is that the first link now carries no condition.  Zero of its
ten rules never fire, and the
paragraphs above still describe the conflicts that have no proof: those are the ones
whose *facts* no core member states, which is a different shortage from the one this
rule filled.

A second boundary is narrower.  An event assumption is published as a
``structural_constraint`` fact: the core member is known and located, but its
content is not read, so no rule applies to it.  The narrative then reports
``structural_only`` and says only that the constraints cannot hold together --
true, and unhelpfully thin for a reader who wanted to know *which* two event
requirements collided.  Both boundaries are consequences of decisions recorded
in the contract, not defects in the checker, and both are visible to the caller
through ``achieved_mode`` and ``derivation_status`` rather than silent.


Why the bounded structure grows
--------------------------------

Let :math:`V` be the number of persistent variables, :math:`E` the number of
events, and :math:`K_i` the number of allocated macro-step case selectors at
step :math:`i`.  ``BmcTraceSymbols.allocate`` creates one state and :math:`V`
variable symbols per frame, :math:`E` input-event symbols plus delta and gamma
per step, and one selector per step/case pair.  The exact count of these public
trace symbols is:

.. math::
   :label: bmc-symbol-growth

   |X_N|
   = (N+1)(V+1) + N(E+2) + \sum_{i=0}^{N-1}K_i
   = N\!\left(V+E+3+\bar K\right)+(V+1),
   \qquad
   \bar K=\frac{1}{N}\sum_{i=0}^{N-1}K_i.

The second equality uses :math:`N>0`; the first equality is the exact count for
every admitted bound.  For a fixed expanded case set, symbol count is linear in
the bound.  That does
not make solving cost linear: the relation also repeats guards, updates,
definedness conditions, call snapshots, and case implications, while the solver
searches their combinations.  Macro expansion can increase :math:`K_i` before
the bound is unrolled, so reducing :math:`N` does not repair a case explosion
inside one step.  Equation :eq:`bmc-symbol-growth` counts allocated trace
variables, not Z3 expression nodes or solver search states.

Working traces and formula ledger
---------------------------------

The five equations can be audited with one minimal model and two queries.  The
model is intentionally small so the solver boundary remains visible:

.. code-block:: fcstm

   state Root;

The response query exercises the staged primary and suffix paths described by
:eq:`bmc-solve-formulas`:

.. code-block:: text

   check response <= 1: trigger true -> within 2 false;

Its trace summary is ``main=unsat``, ``tail=sat``, ``outcome=incomplete``.
There is no primary SAT model and therefore no bounded property verdict.  The
SAT suffix is nevertheless decoded and replayed as an ``incomplete_suffix``
role-aware witness for the executable finite prefix; it must not be mistaken
for a complete witness or counterexample.  The second query exercises the
positive witness path:

.. code-block:: text

   check reach <= 1: active("Root");

It produces ``main=sat``, ``outcome=witness_found``, two decoded frames, one
decoded step, and ``replay.ok=true``.  For the same bound-1 query,
:math:`V=0`, :math:`E=0`, and the sole step has :math:`K_0=2` selectors.
Equation :eq:`bmc-symbol-growth` therefore gives
:math:`|X_1|=2+2+2=6`: two frame-state symbols, delta and gamma, and two case
selectors.

The list below is the forward audit map for the labelled equations in this
page.
Literal LaTeX is the labelled block at each labelled equation target; the
English and Chinese files carry identical blocks.

Each equation below names its implementation, its tests, and the query whose
trace exercises it.

:eq:`bmc-solve-formulas` -- staged feasibility and response suffix
    ``compile_bmc_property``, ``solve_bmc_property`` and ``_SolveBudget``.
    Covered by ``test_compile_response_strict_successor_and_incomplete_suffix``
    and ``test_solver_unknown_and_timeout_paths_are_structured``.  The response
    query above gives UNSAT on the main objective and SAT on the tail.

:eq:`bmc-verdict-map` -- polarity-aware three-valued verdict
    ``BmcSolveResult.property_satisfied`` and ``outcome``.  The response query
    gives ``incomplete``; the reach query gives ``witness_found``.  Covered by:

    - ``test_solve_result_public_verdict_truth_table``
    - ``test_response_violation_verdict_stays_decisive_with_suffix``

:eq:`bmc-witness-projection` -- SAT model to sparse public trace
    ``decode_bmc_witness``, ``_decode_step`` and ``_event_inputs_for_step``.
    Covered by the witness decoder and event-policy tests in
    ``test/bmc/test_witness.py``.  The reach query decodes two frames and one
    step.

:eq:`bmc-replay-agreement` -- public observation equality
    ``replay_bmc_witness``, ``_compare_frame`` and ``_compare_step``.  The reach
    query reports ``replay.ok=true``, and a trace with a tampered ``x`` fails.
    Covered by:

    - ``test_replay_reports_structured_var_mismatch``
    - ``test_bmc_witness_replay_matches_full_semantic_fixture_trace``

:eq:`bmc-symbol-growth` -- exact allocated trace-symbol count
    ``BmcTraceSymbols.allocate``.  Covered by shape assertions in
    ``test/bmc/test_domain.py`` and ``test/bmc/test_relation_public_api.py``.
    The reach query has :math:`N=1,V=0,E=0,K_0=2`, hence six symbols.

The semantic-fixture replay suite is especially important: it checks complete
runtime traces for the registered hard-pass scenarios, not merely that a
witness object can be serialized.  The tampering tests provide the opposite
evidence by changing a public observation and requiring a precise mismatch.


What the explanation claims, formally
-------------------------------------

The four statements below are what the optional explanation asserts about its own
output.  They are separate from the solve equations above because they constrain
a *report*, not a search: each one is a property the published object either has
or is refused for lacking.

Let :math:`C = \{c_1, \dots, c_n\}` be the published conflict core, each
:math:`c_i` the encoding of one authored clause or generated support group, and
let :math:`\Phi` denote conjunction.

Soundness is the weakest claim, and every core makes it.  A core is sound when
its members alone already admit no assignment:

.. math::
   :label: bmc-core-soundness

   \mathrm{UNSAT}\bigl(\Phi(C)\bigr)

This is what the solver's own core gives, and it says nothing about whether every
member is needed.  Subset-minimality is the stronger claim, and it is made only
when every member was tested by removing it and re-solving:

.. math::
   :label: bmc-core-subset-minimality

   \forall c \in C:\ \mathrm{SAT}\bigl(\Phi(C \setminus \{c\})\bigr)

A core satisfying :eq:`bmc-core-subset-minimality` reports ``subset_minimal``
with ``subset_minimality`` as ``proven``.  One satisfying only
:eq:`bmc-core-soundness` reports ``raw``, and one whose testing was cut short
reports ``partial_minimized``.  The distinction is what tells a reader whether
every listed line is worth editing.

At proof depth each input node restates one core member as a normalized fact
:math:`f`.  Restatement is stronger than implication in both directions, and both
are required:

.. math::
   :label: bmc-proof-input-binding

   \mathrm{UNSAT}\bigl(\Phi(c) \wedge \neg f\bigr)
   \ \wedge\
   \mathrm{UNSAT}\bigl(f \wedge \neg \Phi(c)\bigr)

The left conjunct says the member forces the fact; the right says the fact forces
the member.  Checking only the left would admit an :math:`f` weaker than
:math:`c` -- a summary, which may have dropped the detail the reader needed.  Any
of these checks returning satisfiable, unknown, or timing out keeps the proof out
of ``complete``.

Finally the inputs and the core stand in bijection, so that every member is read
exactly once and no node speaks for two:

.. math::
   :label: bmc-proof-input-bijection

   \bigl|\{\,v : \mathrm{kind}(v) = \texttt{input}\,\}\bigr| = |C|
   \ \wedge\
   \forall v:\ \bigl|\mathrm{items}(v)\bigr| = 1

A missing, extra, or duplicated input violates
:eq:`bmc-proof-input-bijection` and is refused rather than published --
including the case of two distinct members stating the same fact, which has no
place to go: merging them would give one node two attributions and dropping one
would leave a member unread.

Each claim below names its implementation, its test, and a query that produces
it.  All four share the two-line query
``assume at 1: var("x") == 1; assume at 1: var("x") == 2;``, so one run
reproduces the whole ledger.

:eq:`bmc-core-soundness` -- the core alone is unsatisfiable
    Built by ``extract_source_core`` in ``pyfcstm/bmc/infeasibility.py``; covered
    by ``test/bmc/test_infeasibility.py``.  The query reports ``Core size: 2``
    with the scenario UNSAT.

:eq:`bmc-core-subset-minimality` -- every member is load bearing
    Built by the minimization loop in the same function; covered by
    ``test_reduction_and_minimality_stay_coupled`` in
    ``test/bmc/test_explanation.py``.  The query reports
    ``Reduction: subset_minimal`` and ``Subset minimality: proven``.

:eq:`bmc-proof-input-binding` -- both directions are refuted
    Checked by ``check_core_bindings`` in ``pyfcstm/bmc/infeasibility.py``;
    covered by ``test/bmc/test_proof_wiring.py``.  The query publishes both
    inputs with ``verification_method`` as ``core_binding``.

:eq:`bmc-proof-input-bijection` -- one node per member
    Enforced by ``build_domain_proof`` in ``pyfcstm/bmc/proof.py``.  The query
    publishes two input nodes for a two-member core, each with one entry in
    ``item_ids``.  Its two tests take a line each, so that a long identifier is
    not clipped in a narrow column:

    - ``test_an_input_node_restates_one_member_and_says_so``
    - ``test_two_members_stating_one_fact_are_refused_rather_than_merged``

The ledger is worth reading against the boundary above: these four claims are
about the constraints as encoded.  None of them says the encoding matches what
the author meant, which is why the trust boundary is stated separately.
