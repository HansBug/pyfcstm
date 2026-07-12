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
     - The model can be projected into a ``bmc-witness/v1`` macro-step trace.
     - It does not decide whether the trace is a desired behavior or a violation; polarity does that.
   * - Replay
     - The decoded public trace
     - The decoded observations agree with ``SimulationRuntime`` on this finite trace.
     - It does not prove all models decode, all cases are encoded correctly, or the property holds beyond :math:`N`.

Two formulas, two Z3 checks
---------------------------

Let :math:`C_N` be the core transition relation for bound :math:`N`,
:math:`Q_N` the compiled property objective, and :math:`\Omega_N` the optional
observation that a response obligation extends beyond the horizon.  Property
compilation produces two independently solvable formulas:

.. math::
   :label: bmc-solve-formulas

   \Phi_{\mathrm{main}} = C_N \land Q_N,
   \qquad
   \Phi_{\mathrm{tail}} = C_N \land \Omega_N.

The first check is always executed.  The second is executed only when
``check_incomplete`` is true and :math:`\Omega_N` is not the constant false
formula.  At present that makes the second check a response-property concern;
other property kinds have no non-trivial tail observation.

:func:`pyfcstm.bmc.witness.solve_bmc_property` calls a private ``_solve`` once
for each applicable formula.  Each call creates a fresh ``z3.Solver``, applies
the same ``timeout_ms`` value, adds exactly one formula, and calls ``check()``.
Consequently, the timeout is **per check**, not a shared total budget.  If both
checks are needed, a timeout value :math:`T` permits approximately
:math:`2T` of solver time plus construction and reporting overhead.  Even a
timeout on the main check does not cancel the separate tail check.

Z3's ``unknown`` result is split by ``reason_unknown()``: the exact reason
``"timeout"`` becomes public status ``timeout``; other reasons remain
``unknown``.  Neither status carries a model.  Main elapsed time is stored in
``elapsed_ms``; tail elapsed time is retained as an
``incomplete_elapsed_ms=...`` diagnostic.  Disabling the second check is also
observable as ``incomplete_check=disabled`` rather than being treated as a
proof that no incomplete suffix exists.

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
but they are not passed to ``runtime.cycle()``.  Case labels, ``delta``,
``gamma``, and ``progress`` likewise remain witness-side explanations; the
runtime does not expose corresponding public observations.

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
values, and step equality covers input, consumed and unconsumed events plus
ordered abstract-call metadata and snapshots.  Floating-point values use the
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
does not publish.  Conversely, event consumption and abstract-call snapshots
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

The tail query exercises both formulas in :eq:`bmc-solve-formulas`:

.. code-block:: text

   check response <= 1: trigger true -> within 2 false;

Its trace summary is ``main=unsat``, ``tail=sat``, ``outcome=incomplete``.
There is no primary SAT model, so there is no decoded witness or replay.  The
second query exercises the positive witness path:

.. code-block:: text

   check reach <= 1: active("Root");

It produces ``main=sat``, ``outcome=witness_found``, two decoded frames, one
decoded step, and ``replay.ok=true``.  For the same bound-1 query,
:math:`V=0`, :math:`E=0`, and the sole step has :math:`K_0=2` selectors.
Equation :eq:`bmc-symbol-growth` therefore gives
:math:`|X_1|=2+2+2=6`: two frame-state symbols, delta and gamma, and two case
selectors.

The table is the forward audit map for the labelled equations in this page.
Literal LaTeX is the labelled block at each labelled equation target; the
English and Chinese files carry identical blocks.

.. list-table:: Solving-equation ledger
   :header-rows: 1
   :widths: 21 27 28 24

   * - Equation and claim
     - Implementation anchor
     - Test anchor
     - Working query and trace
   * - :eq:`bmc-solve-formulas`: separate main and tail checks
     - ``compile_bmc_property``; ``solve_bmc_property``; ``_solve``
     - ``test_compile_response_strict_successor_and_incomplete_suffix``;
       ``test_solver_unknown_and_timeout_paths_are_structured``
     - Response query above: UNSAT main, SAT tail
   * - :eq:`bmc-verdict-map`: polarity-aware three-valued verdict
     - ``BmcSolveResult.property_satisfied`` and ``outcome``
     - ``test_solve_result_public_verdict_truth_table``;
       ``test_response_violation_verdict_stays_decisive_with_suffix``
     - Response gives ``incomplete``; reach gives ``witness_found``
   * - :eq:`bmc-witness-projection`: SAT model to sparse public trace
     - ``decode_bmc_witness``; ``_decode_step``;
       ``_event_inputs_for_step``
     - witness decoder and event-policy tests in ``test/bmc/test_witness.py``
     - Reach query: two frames and one step
   * - :eq:`bmc-replay-agreement`: public observation equality
     - ``replay_bmc_witness``; ``_compare_frame``; ``_compare_step``
     - ``test_replay_reports_structured_var_mismatch``;
       ``test_bmc_witness_replay_matches_full_semantic_fixture_trace``
     - Reach query: ``replay.ok=true``; tampered ``x`` trace fails
   * - :eq:`bmc-symbol-growth`: exact allocated trace-symbol count
     - ``BmcTraceSymbols.allocate``
     - shape assertions in ``test/bmc/test_domain.py`` and
       ``test/bmc/test_relation_public_api.py``
     - Reach query: :math:`N=1,V=0,E=0,K_0=2`, hence six symbols

The semantic-fixture replay suite is especially important: it checks complete
runtime traces for the registered hard-pass scenarios, not merely that a
witness object can be serialized.  The tampering tests provide the opposite
evidence by changing a public observation and requiring a precise mismatch.
