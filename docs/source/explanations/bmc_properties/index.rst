.. _sec-explanations-bmc-properties:

Property Objectives, Definedness, and Bounds
=============================================

A bounded property is not merely a Boolean condition appended to a trace.
pyfcstm first lowers each predicate into a value and the side conditions under
which that value is defined, then chooses an objective whose satisfiability has
the polarity of the property kind.  This page explains that construction and
the separate observation used when a response window extends beyond the bound.

The implementation sources are ``pyfcstm/bmc/properties.py`` and the expression
lowering in ``pyfcstm/bmc/relation.py``.  The primary executable specification
is ``test/bmc/test_properties.py``; call-filter guards are additionally covered
by ``test/bmc/test_call_predicate_guards.py``.  This is an explanation of the
current bounded semantics, not a claim that UNSAT proves an unbounded temporal
property.


One door-latch example for all seven properties
-----------------------------------------------

Use one bounded door-latch story to separate user intent from solver polarity.
Assume the trace starts in ``Door.Locked``.  The event ``Door.Unlock`` may move
the latch to ``Door.Unlocked`` in the next macro step, and the public transition
case is ``Door.Locked::transition::Door.Unlocked::0``.  The examples below are
short property shapes, not a full model listing.

.. list-table:: Seven property kinds at one glance
   :header-rows: 1
   :widths: 13 26 16 24 21

   * - Kind
     - Finite quantifier in the main objective
     - SAT polarity
     - User intent
     - Door-latch shape
   * - ``reach``
     - :math:`\exists` trace, :math:`\exists` frame with :math:`G_i(p)`
     - witness
     - Show that a desired state can occur.
     - ``reach active("Door.Unlocked")``
   * - ``forbid``
     - :math:`\exists` trace, :math:`\exists` forbidden or undefined frame
     - counterexample
     - Reject any trace that visits a forbidden state.
     - ``forbid active("Door.Unlocked")``
   * - ``invariant``
     - :math:`\exists` trace, :math:`\exists` false or undefined frame
     - counterexample
     - Require every visible frame to satisfy a condition.
     - ``invariant active("Door.Locked")``
   * - ``must_reach``
     - :math:`\exists` complete trace with no good matching frame
     - counterexample
     - Require every bounded trace to reach the target.
     - ``must_reach active("Door.Unlocked")``
   * - ``exists_always``
     - :math:`\exists` trace where every frame is good
     - witness
     - Show that some behavior can keep a condition true throughout.
     - ``exists_always active("Door.Locked")``
   * - ``cover``
     - :math:`\exists` trace, :math:`\exists` public case selector
     - witness
     - Show that a named transition or fallback case can be selected.
     - ``cover case("Door.Locked::transition::Door.Unlocked::0")``
   * - ``response``
     - :math:`\exists` trigger step with a complete missing-response window
     - counterexample
     - Require a future response after each trigger within the bound.
     - ``response trigger event("Door.Unlock", current) -> within 1 active("Door.Unlocked")``

The table uses property fragments to keep the example readable.  In a complete
``.fbmcq`` query each fragment appears after ``check <kind> <= N:`` and any
needed initial clause, for example ``init state("Door.Locked");``.  The
important point is the polarity: the decoded SAT model is a desired witness for
``reach``, ``exists_always``, and ``cover``, but a violation trace for
``forbid``, ``invariant``, ``must_reach``, and ``response``.

Notation and three recurring traces
------------------------------------

Let :math:`F_0,\ldots,F_N` be the frames of a trace satisfying
:math:`Core_N`, and let :math:`E_i` be the event input for the macro step from
:math:`F_i` to :math:`F_{i+1}`.  For a frame predicate :math:`p`,
:math:`P_i(p)` is its lowered Boolean value and :math:`D_i(p)` is its runtime
definedness.  A response property uses trigger :math:`t`, response :math:`r`,
and positive window :math:`W`.

Most examples use this two-state machine:

.. code-block:: text

   state Root {
       event Go;
       state A;
       state B;
       [*] -> A;
       A -> B : Go;
   }

With ``init state("Root.A")``, bound 1, and ``Go`` true at step 0, its
distinguishing trace is
:math:`F_0=\texttt{Root.A}, E_0=\texttt{Go}, F_1=\texttt{Root.B}`.
Turning ``Go`` off leaves both frames in ``Root.A``.  The definedness
counterexample uses ``x = 1`` and ``y = 0``: evaluating ``x / y > 0`` makes its
value irrelevant because division requires :math:`y\ne0`.

For call counting, the tests use a state whose ``during`` actions call
``Before``, increment ``x``, and call ``After``.  One selected macro step then
contains a ``Before`` record with snapshot ``x == 0`` and an ``After`` record
with snapshot ``x == 1``.  Filters inspect those call-time snapshots, not the
post-step frame.

Predicate definedness
---------------------

The predicate-definedness equation collects every side condition produced
while lowering :math:`p`.
The empty conjunction is true, so atoms such as ``active("Root.A")`` are
defined without inventing an extra failure condition.

.. math::
   :label: bmc-predicate-defined

   D_i(p) \;=\; \bigwedge_{d \in \operatorname{Def}_i(p)} d,
   \qquad
   \bigwedge \varnothing \;=\; \top.

``_PredicateFormula.definedness`` stores :eq:`bmc-predicate-defined`, and
``_lower_predicate`` builds it from ``definedness_constraints``.  In
``check reach <= 1: x / y > 0;`` with
``y == 0``, both observed frames have :math:`D_i(p)=\bot`; the query is UNSAT
rather than gaining a witness from an arbitrary division value.  With
``y == 1``, the same trace is defined and the comparison is evaluated normally.
The behavior is frozen by
``test_compile_liveness_definedness_failures_are_not_witnesses``.

The good-predicate equation names the only predicate state that can support a
witness: the expression must be defined *and* true.

.. math::
   :label: bmc-predicate-good

   G_i(p) \;=\; D_i(p) \land P_i(p).

For ``active("Root.A")``, :math:`G_0` is true on the event trace and
:math:`G_1` is false.  For ``x / y > 0`` with ``y == 0``, :math:`G_i` is false
even if a solver representation happens to assign a value to the division.
``_PredicateFormula.good`` implements :eq:`bmc-predicate-good`; the reach,
must-reach, exists-always, and response tests exercise both sides.

Safety-style counterexample searches need two distinct notions of badness.
:eq:`bmc-predicate-bad-true` is bad when a forbidden predicate is undefined or true.

.. math::
   :label: bmc-predicate-bad-true

   B_i^{\top}(p) \;=\; \neg D_i(p) \lor P_i(p).

Thus ``check forbid <= 1: active("Root.A");`` is SAT at :math:`F_0`, while
``check forbid <= 1: terminated();`` is UNSAT on the same trace.  Replacing the
predicate with ``x / y > 0`` and setting ``y == 0`` is also a counterexample:
undefined does not prove that the forbidden condition stayed absent.
``_PredicateFormula.bad_true`` and
``test_compile_definedness_failures_are_safety_counterexamples`` are the code
and test anchors.

:eq:`bmc-predicate-bad-false` is bad when a required invariant is undefined or false.

.. math::
   :label: bmc-predicate-bad-false

   B_i^{\bot}(p) \;=\; \neg D_i(p) \lor \neg P_i(p).

``check invariant <= 1: active("Root.A");`` finds :math:`F_1` as a
counterexample on the event trace; ``active("Root")`` has no such frame.
Again, ``x / y > 0`` with ``y == 0`` is a counterexample rather than a vacuous
success.  This is ``_PredicateFormula.bad_false`` and is tested by
``test_compile_forbid_and_invariant_are_counterexample_objectives`` plus the
definedness regression above.

Six frame and case objectives
-----------------------------

The objective :math:`\Phi_q` is the part conjoined with :math:`Core_N` for the
main solver check.  SAT means a desired witness for ``reach``,
``exists_always``, and ``cover``.  SAT means a counterexample for ``forbid``,
``invariant``, ``must_reach``, and ``response``.  An UNSAT result reverses that
interpretation, but only for this finite bound and these assumptions.

:eq:`bmc-objective-reach` searches all :math:`N+1` frames, including :math:`F_0` and
:math:`F_N`, for one good reach predicate.

.. math::
   :label: bmc-objective-reach

   \Phi_{\mathrm{reach}}(p) \;=\;
   \bigvee_{i=0}^{N} G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{witness}].

On the event trace, ``check reach <= 1: active("Root.B");`` is SAT because of
:math:`F_1`; ``active("Root.A")`` is already SAT because of :math:`F_0`.
``terminated()`` is an UNSAT counterexample to the expectation that every reach
query finds something.  The implementation/test pair is ``_compile_reach`` and
``test_compile_reach_witness_covers_frame_zero_and_final_frame``.

:eq:`bmc-objective-forbid` asks whether any frame is undefined or makes the forbidden predicate
true.

.. math::
   :label: bmc-objective-forbid

   \Phi_{\mathrm{forbid}}(p) \;=\;
   \bigvee_{i=0}^{N} B_i^{\top}(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

``active("Root.A")`` produces a SAT counterexample at :math:`F_0`;
``terminated()`` produces no counterexample.  The division-by-zero trace shows
why :eq:`bmc-objective-forbid` uses :math:`B^{\top}` rather than simply
:math:`P_i`.  See ``_compile_forbid`` and
``test_compile_forbid_and_invariant_are_counterexample_objectives``.

:eq:`bmc-objective-invariant` asks whether any frame is undefined or makes the invariant false.

.. math::
   :label: bmc-objective-invariant

   \Phi_{\mathrm{invariant}}(p) \;=\;
   \bigvee_{i=0}^{N} B_i^{\bot}(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

On the event trace, ``active("Root.A")`` yields a SAT counterexample at
:math:`F_1`, while ``active("Root")`` makes the objective UNSAT.  An undefined
numeric invariant is also SAT.  These cases map directly to
``_compile_invariant`` and
``test_compile_forbid_and_invariant_are_counterexample_objectives``.

:eq:`bmc-objective-must-reach` searches for a complete bounded trace on which no frame is a good
match.  It is therefore a counterexample objective, despite the positive
English phrase “must reach”.

.. math::
   :label: bmc-objective-must-reach

   \Phi_{\mathrm{must\_reach}}(p) \;=\;
   \bigwedge_{i=0}^{N} \neg G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

With ``Go`` false, ``check must_reach <= 1: active("Root.B");`` is SAT and its
trace remains in ``Root.A``.  ``active("Root.A")`` makes the objective UNSAT
because :math:`F_0` already reaches it.  Division by zero also prevents a good
match and therefore supports the miss.  See ``_compile_must_reach`` and
``test_compile_must_reach_and_exists_always_polarities``.

:eq:`bmc-objective-exists-always` searches for one bounded trace whose predicate is good at every
frame.  This existential path objective is not a universal invariant proof.

.. math::
   :label: bmc-objective-exists-always

   \Phi_{\mathrm{exists\_always}}(p) \;=\;
   \bigwedge_{i=0}^{N} G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{witness}].

``active("Root")`` is SAT on the event trace.  If ``Go`` is forced true,
``active("Root.A")`` is UNSAT because :math:`F_1` is ``Root.B``; an undefined
predicate is likewise not a witness.  The source/test anchors are
``_compile_exists_always`` and
``test_compile_must_reach_and_exists_always_polarities``.

Calls and cover objectives
--------------------------

Call predicates are step observations.  For an anchor :math:`a`, a filter
:math:`f` selects in-bound steps :math:`S_f(a)`.  :math:`K_i` is the set of
case relations at step :math:`i`, :math:`R_{i,k}` is the abstract-call record
sequence for one case, :math:`C_{i,k}` is its selector, and :math:`M_f(r)` is
the conjunction of action, stage, role, state, active-leaf, named-reference,
and call-snapshot ``where`` filters.

.. math::
   :label: bmc-call-count

   \operatorname{call\_count}_a(f)
   \;=\;
   \sum_{i \in S_f(a)}
   \sum_{k \in K_i}
   \sum_{r \in R_{i,k}}
   \operatorname{ite}\!\left(C_{i,k} \land M_f(r),1,0\right),
   \qquad
   \operatorname{called}_a(f)
   \;\Longleftrightarrow\;
   \operatorname{call\_count}_a(f)>0.

``_lower_call_count`` implements :eq:`bmc-call-count`; ``_call_match_expr``
evaluates a ``where`` clause on the record snapshot.  The tested query counts one
``Before`` call where ``x == 0`` and one ``After`` call where ``x == 1``.  The
counterexample ``call_count("Root.A.After", step=*, where x == 0) >= 1`` is
UNSAT.  See ``test_compile_call_count_filters_use_call_time_snapshots`` and the
guard cases in ``test/bmc/test_call_predicate_guards.py``.  An omitted step
selector is anchored at the current predicate step; ``*`` spans
:math:`0\le i<N`, and out-of-bound relative points are clipped.  An undefined
``where`` expression cannot match a record because its definedness is conjoined
with its value.

``cover`` does not lower an arbitrary frame predicate.  It validates a naked
``case("label")`` atom, accepts only public ``transition`` and ``fallback``
case kinds, and disjoins matching selectors across the bounded steps.

.. math::
   :label: bmc-objective-cover

   \Phi_{\mathrm{cover}}(\ell) \;=\;
   \bigvee_{\substack{0 \le i < N,\; k \in K_i \\
                      \operatorname{label}(k)=\ell \\
                      \operatorname{kind}(k)\in\{\mathrm{transition},\mathrm{fallback}\}}}
   C_{i,k}
   \qquad [\mathrm{polarity}=\mathrm{witness}].

For the event machine, forcing ``Go`` true makes
``case("Root.A::transition::Root.B::0")`` SAT; forcing it false makes the same
cover objective UNSAT.  An ``initial``, ``delta``, or ``absorb`` label is a
query error rather than a cover witness.  :eq:`bmc-objective-cover` maps to ``_compile_cover``
and ``_cover_selectors`` and is tested by
``test_compile_cover_accepts_transition_and_fallback_but_not_internal_cases``.

Response is a strict-successor property
---------------------------------------

A trigger is evaluated at each executable step :math:`0\le i<N`.  A response
is evaluated on frames.  The window after step :math:`i` starts at
:math:`F_{i+1}`: truth in :math:`F_i` never satisfies that trigger.  A window
is complete only when :math:`i+W\le N`.  A response counts only through
:math:`G_j(r)`, so an undefined response is not a successful response.

:eq:`bmc-response-violation` is the ordinary missing-response counterexample over complete
windows.  The upper endpoint :math:`F_{i+W}` is included.

.. math::
   :label: bmc-response-violation

   \Phi_{\mathrm{response}}^{\mathrm{miss}}(t,r,W)
   \;=\;
   \bigvee_{\substack{0 \le i < N \\
                      i+W \le N}}
   \left(
       G_i(t) \land
       \neg \bigvee_{j=i+1}^{i+W} G_j(r)
   \right).

With ``Go`` true at step 0,
``trigger event("Root.Go", current) -> within 1 active("Root.B")`` has no
counterexample.  Replacing the response with ``active("Root.A")`` is SAT:
although ``Root.A`` is true at the trigger frame, strict succession examines
only :math:`F_1`.  With bound 2 and window 2, a response first true at
:math:`F_2` satisfies the property.  These traces are implemented by
``_compile_response`` and tested by
``test_compile_response_honors_strict_successor_window_boundaries``.

Undefined triggers are not treated as “not triggered”.  :eq:`bmc-response-trigger-undefined` adds them
directly to the main counterexample objective and then combines the two causes.
The current result and witness protocols do not classify which disjunct made
the formula SAT.

.. math::
   :label: bmc-response-trigger-undefined

   \Phi_{\mathrm{response}}^{\mathrm{undef}}(t)
   \;=\;
   \bigvee_{i=0}^{N-1} \neg D_i(t),
   \qquad
   \Phi_{\mathrm{response}}
   \;=\;
   \Phi_{\mathrm{response}}^{\mathrm{undef}}
   \lor
   \Phi_{\mathrm{response}}^{\mathrm{miss}}
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

The query ``trigger x / y > 0 -> within 1 active("Root")`` with ``y == 0`` is
SAT and reports a property violation.  In contrast, a defined false trigger
contributes neither a violation nor incompleteness.  This distinction is fixed
by ``test_compile_response_treats_trigger_undefined_as_counterexample``.

The response-incompleteness equation is separate from the main objective.  It
observes a good trigger
whose full window lies beyond :math:`F_N` and for which no response has appeared
in the visible suffix.  ``solve_bmc_property`` solves this observation
separately from the main objective; it determines an ``incomplete`` outcome
when the primary check has not already found a response counterexample.

.. math::
   :label: bmc-response-incomplete

   \Omega_{\mathrm{response}}(t,r,W)
   \;=\;
   \bigvee_{\substack{0 \le i < N \\
                      i+W > N}}
   \left(
       G_i(t) \land
       \neg \bigvee_{j=i+1}^{N} G_j(r)
   \right).

At bound 1, ``Go`` true at step 0, window 2, and response
``active("Root.A")``, the visible suffix contains only :math:`F_1=Root.B`.
The main response objective is UNSAT because the window is not complete, while
:eq:`bmc-response-incomplete` is SAT and the outcome is ``incomplete``.  A
response already visible in the suffix makes :math:`\Omega` false.  This is
covered by ``test_compile_response_strict_successor_and_incomplete_suffix`` and
the solver-level incomplete tests in ``test/bmc/test_witness.py``.

The response branches are intentionally non-interchangeable:

.. list-table:: Response boundary matrix
   :header-rows: 1
   :widths: 18 22 23 20 17

   * - Trigger
     - Window
     - Main objective
     - Incomplete formula
     - Result
   * - Undefined
     - Any
     - SAT counterexample
     - Does not decide the main result
     - ``property_violated``
   * - Defined and true
     - Complete, no response
     - SAT counterexample
     - False or irrelevant
     - ``property_violated``
   * - Defined and true
     - Truncated, no visible response
     - UNSAT for this trigger
     - SAT
     - ``incomplete``
   * - Defined and false
     - Any
     - No contribution
     - No contribution
     - Other steps decide

What these objectives establish
--------------------------------

Every main query is solved as :math:`Core_N\land\Phi_q`; response
incompleteness is checked as :math:`Core_N\land\Omega_q`.  The seven
objectives differ both in quantification over the finite frames and in SAT
polarity.  Definedness is part of that semantics: it cannot be erased without
turning runtime errors into false proofs or false witnesses.  Conversely,
response horizon incompleteness is not a runtime-definedness error and not a
counterexample.  Increasing the bound may complete the window and change that
bounded result.

These formulas explain the current compiler and its tests.  They do not elevate
bounded UNSAT to an unbounded theorem, and they do not make replay a proof of
the encoding.  Solver-result interpretation, witness decoding, and runtime
replay are covered by the sibling solving explanation.
