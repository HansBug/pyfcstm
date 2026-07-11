How FCSTM Becomes a Bounded Transition System
================================================

Bounded model checking (BMC) does not execute an FCSTM one cycle at a time.
It allocates one symbolic copy of the control state and persistent variables
for every frame, allocates event inputs and case observations for every step,
and asks Z3 whether all copies can satisfy one finite formula.  This page
derives that formula from the data structures in ``pyfcstm.bmc.relation``.

This is an explanation of the relation layer.  It does not define FBMCQ syntax,
compile a property objective, interpret SAT as a property verdict, or claim an
unbounded proof.  The relation builder deliberately stops at :math:`Core_N`;
property compilation and witness/replay are later layers.

The derivation uses the following sets throughout:

* :math:`N` is the query bound; frames use indices :math:`0..N`, while steps
  use :math:`0..N-1`.
* :math:`V` is the set of persistent FCSTM variables and :math:`\tau(v)` is
  the Z3 sort selected for variable :math:`v`.
* :math:`\mathcal{A}` is the set of fully qualified event paths.
* :math:`K_i` is the finite macro-case set expanded for step :math:`i`.
* :math:`\mathbb{B}` is the Boolean domain.  :math:`S_0` and
  :math:`S_{\mathrm{rec}}` are the legal frame-0 and recurrence state-id sets.

A concrete trace used by every section
----------------------------------------

The checked-in :download:`FCSTM model <trace_machine.fcstm>` has one event,
three persistent variables, and two leaf states.  ``Go`` takes ``A`` to ``B``;
the transition adds ten to ``counter``, then the target leaf's ``during`` block
adds one.  Later idle cycles remain in ``B`` and execute that ``during`` block.

.. literalinclude:: trace_machine.fcstm
   :language: fcstm
   :linenos:

The :download:`bound-three query <trace_bound3.fbmcq>` fixes ``Go`` to true at
step 0 and false at steps 1 and 2.

.. literalinclude:: trace_bound3.fbmcq
   :language: fbmcq
   :linenos:

Building ``BmcEngine(model).prepare(query)`` and then
``build_bmc_core_formula(context)`` yields SAT.  Reading the Z3 model gives the
following actual relation trace; state ids 1 and 2 denote ``Root.A`` and
``Root.B`` in this model.

.. list-table:: Bound-three relation trace
   :header-rows: 1

   * - Frame/step
     - Control state
     - ``counter``
     - ``ratio``
     - ``keep``
     - ``Root.Go``
     - Selected case
     - :math:`\Delta_i / \Gamma_i`
   * - :math:`F_0 / E_0`
     - ``Root.A`` (1)
     - 0
     - :math:`1/2`
     - 5
     - true
     - ``transition``
     - false / false
   * - :math:`F_1 / E_1`
     - ``Root.B`` (2)
     - 11
     - :math:`1/2`
     - 5
     - false
     - ``fallback``
     - false / true
   * - :math:`F_2 / E_2`
     - ``Root.B`` (2)
     - 12
     - :math:`1/2`
     - 5
     - false
     - ``fallback``
     - false / true
   * - :math:`F_3`
     - ``Root.B`` (2)
     - 13
     - :math:`1/2`
     - 5
     - n/a
     - n/a
     - n/a

The first row is worth reading carefully: a bound of three means four frames
but only three event slots.  Also, ``counter`` becomes 11, not 10, because the
macro step preserves runtime ordering through the target leaf's first
``during`` action.  The runtime-alignment tests independently check the same
ordering boundary.

1. Allocate the symbolic trace
--------------------------------

Frames
~~~~~~

Each frame is a control-state symbol paired with a valuation of every
persistent variable.  Frame 0 may use the initial-source domain; later frames
use the recurrence domain.

.. math::
   :label: bmc-trace-frame-domain

   \mathcal{F}_N=(F_i)_{i=0}^{N},\qquad
   F_i=(s_i,\nu_i)\in S_i\times\prod_{v\in V}\tau(v),\qquad
   S_i=\begin{cases}S_0&i=0,\\S_{\mathrm{rec}}&1\le i\le N,\end{cases}
   \qquad |\mathcal{F}_N|=N+1.

``BmcTraceSymbols.allocate`` creates ``F_i_state`` and one mapping of
variable symbols per frame.  ``BmcTraceSymbols.__post_init__`` rejects any
bundle whose frame-state or frame-variable tuple does not contain exactly
``bound + 1`` entries.  ``test_core_formula_constrains_initial_state_and_variable_initializers``
anchors the values at frame 0.  The working trace therefore contains exactly
:math:`F_0,F_1,F_2,F_3`.

Counterexample: treating bound 3 as three frames discards :math:`F_3` and
changes the meaning of ``reach <= 3``.  It is an off-by-one error, not an
alternative notation.

Event inputs
~~~~~~~~~~~~

Events belong to the edge from :math:`F_i` to :math:`F_{i+1}`, so no event
vector exists after the final frame.

.. math::
   :label: bmc-trace-event-domain

   \mathcal{E}_N=(E_i)_{i=0}^{N-1},\qquad
   E_i=(e_{i,a})_{a\in\mathcal{A}}\in\mathbb{B}^{|\mathcal{A}|},\qquad
   |\mathcal{E}_N|=N,\qquad
   |\{e_{i,a}\}|=N|\mathcal{A}|.

The allocator loops over ``domain.steps`` and ``domain.events``, creating one
Boolean ``E_i_event_*`` per pair.  ``test_event_selector_star_and_ranges_lower_to_each_selected_cycle``
shows that a bound-three query has event indices 0, 1, and 2.  In the working
trace these values are true, false, false.

Counterexample: :math:`E_3` is not an unconstrained final input; it does not
exist.  Any response or assumption calculation that reads it has moved beyond
the encoded horizon.

Persistent-variable families
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The frame tuple is materialized as a distinct symbol family for each
persistent variable.  Integers use ``z3.Int`` and FCSTM floats use ``z3.Real``.

.. math::
   :label: bmc-trace-variable-domain

   X_v^N=(x_{i,v})_{i=0}^{N}\in\tau(v)^{N+1}\quad(v\in V),\qquad
   |\{x_{i,v}\mid 0\le i\le N,\ v\in V\}|=(N+1)|V|.

The example has three families and twelve variable symbols: four integer
``counter`` symbols, four real ``ratio`` symbols, and four integer ``keep``
symbols.  The initializer test checks both integer and real values, while the
case-relation test checks that an unwritten variable is carried.

Counterexample: temporary action variables are not members of :math:`V` and
must not receive frame families.  ``test_relation_temporary_variables_do_not_enter_post_var_pool``
freezes this boundary.

Selectors and progress observations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each expanded macro case receives a selector.  Two additional observations
exist for every step: :math:`\Delta_i` for a semantic-delta case and
:math:`\Gamma_i` for a stable fallback case.

.. math::
   :label: bmc-trace-selector-domain

   \mathcal{C}_N=
   \{C_{i,k}\mid 0\le i<N,\ k\in K_i\}
   \cup\{\Delta_i,\Gamma_i\mid 0\le i<N\},\qquad
   C_{i,k},\Delta_i,\Gamma_i\in\mathbb{B},\qquad
   |\mathcal{C}_N|=\sum_{i=0}^{N-1}|K_i|+2N.

``allocate`` receives the actual case labels produced for each step, checks
label uniqueness, and creates ``C_i_*``.  The working trace has two cases at
step 0 and four recurrence cases at each later step; only the transition
selector is true at step 0 and only the ``Root.B`` fallback selector is true
at steps 1 and 2.

Counterexample: selectors are observations bound to antecedents.  Their mere
allocation does not prove that a malformed upstream macro partition is
exactly-one; macro expansion owns that invariant.

2. Restrict the legal frames and initial frame
------------------------------------------------

Control-state domain
~~~~~~~~~~~~~~~~~~~~

The allocation type only says that :math:`s_i` is an integer.  :math:`D_N`
turns that integer into a valid BMC state id, with a potentially wider domain
at frame 0 than at recurrence frames.

.. math::
   :label: bmc-domain-formula

   D_N=\left(s_0\in S_0\right)\land
   \bigwedge_{i=1}^{N}\left(s_i\in S_{\mathrm{rec}}\right),\qquad
   (s_i\in S)\equiv\bigvee_{q\in S}(s_i=q).

``_relation_frame_domain`` derives both sets, and ``_build_domain_formula``
emits the disjunction for every frame.  In the working model, the printed
formula admits the initial sentinel and model states at :math:`F_0`, but only
the terminate sentinel and stable leaves at later frames.

Counterexample: an arbitrary integer such as 999 cannot be used as a cheap
``unknown state``.  Conjoining :math:`s_1=999` with :eq:`bmc-domain-formula`
is UNSAT.

Initial control
~~~~~~~~~~~~~~~

The query's initial mode selects one concrete source id.  It is not left as a
choice inside the solver.

.. math::
   :label: bmc-initial-control

   I_0^{\mathrm{ctrl}}\equiv s_0=\operatorname{src}(m),\qquad
   \operatorname{src}(m)=
   \begin{cases}
   \mathrm{STATE\_INIT}&m=\mathrm{cold},\\
   \operatorname{id}(p)&m=\mathrm{state}(p),\\
   \mathrm{STATE\_TERMINATE}&m=\mathrm{terminated}.
   \end{cases}

``_initial_source`` calls ``source_from_initial_spec`` and checks the bound
state id against the resolved source.  ``_build_initial_formula`` then emits
the equality.  The working query uses ``state("Root.A")``, hence :math:`s_0=1`.
Tests separately cover default cold start and terminated start.

Counterexample: ``init state("Root.A")`` does not execute the cold-entry path
before :math:`F_0`; it establishes a hot initial control state.  Confusing the
two can replay entry effects that the query did not request.

Retained initializers
~~~~~~~~~~~~~~~~~~~~~

Let :math:`H` be the query's havoc set.  Every persistent variable outside
:math:`H` retains its model initializer, including its runtime-definedness
conditions.

.. math::
   :label: bmc-initial-retained

   I_0^{\mathrm{ret}}(H)=
   \bigwedge_{v\in V\setminus H}
   \left(\operatorname{Def}(\operatorname{init}_v(\nu_0))\land
   x_{0,v}=\operatorname{init}_v(\nu_0)\right).

``_build_initial_formula`` translates each non-havoc model initializer against
the frame-0 environment, appends its domain constraints, then appends the
equality.  The working trace therefore fixes ``counter=0``, ``ratio=1/2``, and
``keep=5``.  ``test_core_formula_constrains_initial_state_and_variable_initializers``
proves these equalities by making their negations UNSAT.

Counterexample: a division-by-zero initializer is not silently assigned an
arbitrary value.  Without havoc its definedness conjunct makes the core UNSAT.

Havoc removes initializer equalities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Havoc changes the set of initializer conjuncts; it does not create a second
assignment or a magic value.

.. math::
   :label: bmc-initial-havoc

   \operatorname{Conj}\!\left(I_0^{\mathrm{ret}}(H)\right)=
   \operatorname{Conj}\!\left(I_0^{\mathrm{ret}}(\varnothing)\right)
   \setminus
   \left\{\operatorname{Def}(\operatorname{init}_v(\nu_0)),
   \ x_{0,v}=\operatorname{init}_v(\nu_0)\mid v\in H\right\}.

The implementation literally skips the initializer translation when a name is
in ``havoc_names``.  ``test_initial_havoc_variable_skips_initializer_but_where_constrains_frame0``
shows the important consequence: a havoced ``x`` may be fixed to 7 by
``where x == 7``, while a retained variable still equals its initializer.

Counterexample: “havoc means unconstrained” is too strong.  It means
“unconstrained by the model initializer”; :math:`D_N`, ``where``, assumptions,
and transition relations may still constrain that symbol.

The initial ``where`` predicate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The optional ``where`` expression is evaluated at frame 0 and conjoined with
control and retained-variable constraints.  Its own definedness is mandatory.

.. math::
   :label: bmc-initial-where

   I_0=I_0^{\mathrm{ctrl}}\land I_0^{\mathrm{ret}}(H)\land
   \begin{cases}
   \operatorname{Def}(W(F_0))\land W(F_0)&\text{if a where predicate }W\text{ is present},\\
   \top&\text{otherwise}.
   \end{cases}

``_lower_bmc_cond_expr(..., frame_index=0)`` produces the value and domain
constraints.  ``test_initial_where_without_havoc_keeps_initializer_and_can_be_unsat``
uses an initializer and contradictory ``where`` to make :math:`I_0` UNSAT.

Counterexample: ``where`` is not a macro-case guard.  It constrains
:math:`I_0` only; ``test_initial_where_only_constrains_i0_not_macro_case_partition``
checks that no case label contains or re-expands it.

3. Lower each macro case
-------------------------

Case antecedent
~~~~~~~~~~~~~~~

For case :math:`k` at step :math:`i`, macro expansion has already assembled a
Boolean template from event atoms, transition guards, priority masks, and any
accepted-case dependencies.  Relation lowering combines that condition with
the source-state equality.

.. math::
   :label: bmc-case-antecedent

   A_{i,k}\equiv
   \left(s_i=\operatorname{src}(k)\right)\land
   Q_{i,k}\!\left(F_i,E_i,(A_{i,j})_{j\prec k}\right).

``_lower_bool_template`` maps event atoms to :math:`e_{i,a}`, guard atoms to
lowered guard terms, and accepted atoms to recursively lowered earlier
antecedents.  ``_build_case_relation`` adds the source guard.  The working
step-0 transition antecedent is true because :math:`s_0` is ``Root.A`` and
``Root.Go`` is true.

Counterexample: a true ``Go`` input cannot activate an ``A -> B`` case when
:math:`s_i` is ``B``.  Event truth alone omits the source-state conjunct.

Selector equivalence
~~~~~~~~~~~~~~~~~~~~

The public case selector is exactly an observation of the antecedent, in both
directions.

.. math::
   :label: bmc-case-selector

   C_{i,k}\leftrightarrow A_{i,k}.

The code is the Z3 equality ``selector == antecedent``.  The case-relation
test constrains ``Go`` false and proves the fallback selector cannot be
arbitrarily flipped when its antecedent is false; canonical dumps expose both
expressions.

Counterexample: the one-way constraint :math:`C_{i,k}\Rightarrow A_{i,k}`
would allow :math:`A_{i,k}` to be true while the selector remains false.  That
would corrupt case coverage and call-count observations even if the post-state
implication still fired.

Guarded case relation
~~~~~~~~~~~~~~~~~~~~~

The postcondition belongs under an implication.  An unselected case must not
write its target state or variables.  Let :math:`\mathcal{D}_{i,k}` contain
every runtime-definedness condition accumulated while lowering the case's
guards and ordered action blocks.  Those conditions are part of the selected
case's postcondition, not optional diagnostics.

.. math::
   :label: bmc-case-relation

   T_{i,k}\equiv
   \left(C_{i,k}\leftrightarrow A_{i,k}\right)\land
   \left(A_{i,k}\Rightarrow
   \left(R_{i,k}\land
   \bigwedge_{d\in\mathcal{D}_{i,k}}d\right)\right).

``BmcCaseRelation.formula`` is the conjunction shown above.
``test_case_relation_uses_implication_not_global_and_and_carries_vars`` fixes
``Go`` true and obtains the transition target, then fixes it false and obtains
the fallback target.  The separate runtime-alignment suite checks transition
effects against ``SimulationRuntime``.  ``_prepare_case_lowering`` accumulates
guard and action definedness, and ``_build_case_relation`` appends those
constraints to ``consequent``.  For example, a selected transition effect
``x = 1 / 0`` contributes :math:`0\ne0`; the case, and therefore that attempted
execution, is UNSAT.  The same impossible operation in an unselected case does
not constrain the step because the conjunction remains under the implication.

Counterexample: replacing the implication with a global conjunction
:math:`A_{i,k}\land R_{i,k}` would require every expanded case to be selected
simultaneously, usually making the step UNSAT.  Omitting
:math:`\mathcal{D}_{i,k}` is also unsound: Z3 could assign an arbitrary value
to a partial arithmetic operation and manufacture a transition that the
runtime cannot execute.

Post-control write
~~~~~~~~~~~~~~~~~~

Every selected case has one expanded target id.  This includes stable leaves,
the init sentinel for a delta stutter, and the terminate sentinel.

.. math::
   :label: bmc-case-post-control

   R_{i,k}^{\mathrm{ctrl}}\equiv
   s_{i+1}=\operatorname{tgt}(k).

``_build_case_relation`` makes this the first post constraint.  The working
transition writes ``Root.B`` to :math:`s_1`; the runtime-alignment test proves
that asking for any other state id is UNSAT under ``Go``.

Counterexample: the target is not derived merely from the FCSTM transition
endpoint at this layer.  Macro expansion may resolve pseudo-state descent and
termination before relation lowering, so bypassing ``case.target_state_id``
loses that semantics.

Written variables
~~~~~~~~~~~~~~~~~

Actions are executed symbolically in runtime order.  For the set :math:`W_k`
of variables changed by case :math:`k`, the final symbolic environment becomes
the next-frame value.

.. math::
   :label: bmc-case-variable-write

   R_{i,k}^{\mathrm{write}}\equiv
   \bigwedge_{v\in W_k}
   \left(x_{i+1,v}=\operatorname{Eval}_v(\operatorname{ops}_k,\nu_i)\right).

``_prepare_case_lowering`` and ``_execute_action_block`` build ``final_env``;
``_build_case_relation`` writes every resulting expression to frame
:math:`i+1`.  In the working trace, transition effect ``+10`` followed by the
target ``during`` action ``+1`` gives :math:`x_{1,\mathrm{counter}}=11`.
``test_relation_exit_effect_enter_order_matches_simulation_runtime`` similarly
freezes exit, transition-effect, and enter order as 5 + 10 + 2 = 17.

Counterexample: lowering action blocks as an unordered set is unsound whenever
two blocks write the same variable.  The later expression consumes the earlier
symbolic result.

Unwritten-variable carry
~~~~~~~~~~~~~~~~~~~~~~~~

The symbolic executor starts from the current frame environment.  A variable
that no action changes therefore retains its incoming expression.

.. math::
   :label: bmc-case-variable-carry

   R_{i,k}^{\mathrm{carry}}\equiv
   \bigwedge_{v\in V\setminus W_k}\left(x_{i+1,v}=x_{i,v}\right).

The implementation does not need a separate carry loop: ``final_env`` still
maps an unwritten name to its :math:`F_i` symbol, and the common post-write loop
emits the equality.  ``keep`` and ``ratio`` remain 5 and :math:`1/2` through
all four working frames.  The core test explicitly makes ``keep`` inequality
UNSAT.

Counterexample: leaving an unwritten post variable unconstrained invents
nondeterministic state that neither FCSTM nor ``SimulationRuntime`` has.

4. Assemble one step and the bounded transition relation
----------------------------------------------------------

Fallback cases
~~~~~~~~~~~~~~

Fallback is an explicit expanded case, not an implicit “do nothing” inserted
after solving.  Its condition contains the negation of earlier accepted
transition cases, and it may execute ``during`` actions.

.. math::
   :label: bmc-step-fallback

   T_i^{\mathrm{fb}}\equiv
   \bigwedge_{k\in K_i^{\mathrm{fb}}}
   \left[\left(C_{i,k}\leftrightarrow A_{i,k}\right)\land
   \left(A_{i,k}\Rightarrow R_{i,k}\right)\right],\qquad
   A_{i,k}\Rightarrow\bigwedge_{j\prec k}\neg A_{i,j}.

``_build_step_relation`` lowers fallback cases exactly like other cases.
``test_relation_fallback_negates_failed_guard_and_runs_during`` sees the
negated accepted atom and observes the ``during`` update.  Working steps 1 and
2 select the ``Root.B`` fallback and increment ``counter``.

Counterexample: fallback does not necessarily stutter every variable.  In the
working model it changes ``counter`` on each idle cycle; only ``ratio`` and
``keep`` carry.

Terminated absorption
~~~~~~~~~~~~~~~~~~~~~

Termination is absorbing.  The absorb case also rejects all later event input
and carries persistent variables.

.. math::
   :label: bmc-step-terminated-absorb

   s_i=\mathrm{STATE\_TERMINATE}\Rightarrow
   \left(s_{i+1}=\mathrm{STATE\_TERMINATE}\right)\land
   \bigwedge_{a\in\mathcal{A}}\neg e_{i,a}\land
   \bigwedge_{v\in V}\left(x_{i+1,v}=x_{i,v}\right).

``_recurrence_formals`` expands ``terminated_source``; the absorb branch in
``_build_case_relation`` appends every negated event input.  The terminated
tests check state absorption, variable carry, and UNSAT when an event is forced
true after termination.

Counterexample: allowing events after termination would create inputs that the
runtime cannot consume and would make witness event accounting disagree with
replay.

Delta, fallback, and mutual exclusion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The two progress observations are exact disjunctions of their respective case
antecedents.  They are also explicitly mutually exclusive.

.. math::
   :label: bmc-step-delta-gamma

   \Delta_i\leftrightarrow\bigvee_{k\in K_i^{\delta}}A_{i,k},\qquad
   \Gamma_i\leftrightarrow\bigvee_{k\in K_i^{\mathrm{fb}}}A_{i,k},\qquad
   \neg(\Delta_i\land\Gamma_i).

``_build_step_relation`` emits these three constraints after all case
relations.  A cold source blocked on a required event selects a delta and
stutters; a stable leaf with no transition selects fallback and may run
``during``.  ``test_cold_no_progress_delta_stutters_state_and_vars`` and
``test_stable_leaf_fallback_gamma_commits_during_actions`` freeze the contrast.

Counterexample: :math:`\Delta_i` does not mean “no event input”, and
:math:`\Gamma_i` does not mean “no variable changed”.  They classify expanded
case semantics, not raw vector equality.

All steps
~~~~~~~~~

One step conjoins every case formula and the observation constraints; the
bounded transition formula conjoins all :math:`N` steps.

.. math::
   :label: bmc-transition-formula

   T_i=\left(\bigwedge_{k\in K_i}T_{i,k}\right)\land
   \left(\Delta_i\leftrightarrow\bigvee_{k\in K_i^{\delta}}A_{i,k}\right)\land
   \left(\Gamma_i\leftrightarrow\bigvee_{k\in K_i^{\mathrm{fb}}}A_{i,k}\right)\land
   \neg(\Delta_i\land\Gamma_i),\qquad
   T_N=\bigwedge_{i=0}^{N-1}T_i.

``build_bmc_core_formula`` builds each ``BmcStepRelation`` and conjoins its
``formula``.  The working bound produces :math:`T_0\land T_1\land T_2`, which
links four frames.  The bound-two termination test confirms that recurrence
formals, including absorb, are used after the initial step.

Counterexample: conjoining only :math:`T_0` in a bound-three query leaves
:math:`F_2` and :math:`F_3` disconnected from execution even if their state ids
still satisfy :math:`D_N`.

5. Add environment assumptions and freeze the core
-----------------------------------------------------

Environment assumptions
~~~~~~~~~~~~~~~~~~~~~~~

Let :math:`\mathcal{H}_F` contain frame assumptions as a frame-index set and
predicate pair; :math:`\mathcal{H}_E` contain fixed event literals; and
:math:`\mathcal{H}_{\le1}` contain event pools subject to at-most-one on every
step.  ``any`` contributes no cardinality conjunct.

.. math::
   :label: bmc-environment-formula

   ENV_N=
   \bigwedge_{(J,p)\in\mathcal{H}_F}\ \bigwedge_{i\in J}
   \left(\operatorname{Def}(p(F_i))\land p(F_i)\right)
   \land
   \bigwedge_{(J,a,b)\in\mathcal{H}_E}\ \bigwedge_{i\in J}
   \left(e_{i,a}=b\right)
   \land
   \bigwedge_{B\in\mathcal{H}_{\le1}}\ \bigwedge_{i=0}^{N-1}
   \operatorname{AtMostOne}\!\left((e_{i,a})_{a\in B}\right).

``_build_environment_formula`` expands ``always`` to frames 0 through
:math:`N`, lowers ``at`` to its one frame, applies resolved event selectors,
and calls ``z3.AtMost`` for an explicitly requested pool.  The working
:math:`ENV_3` is simply ``Go_0`` and not ``Go_1`` and not ``Go_2``.
Environment tests prove both frame ranges and event ranges.

Counterexample: there is no implicit global at-most-one policy.  Two distinct
events may both be true in one step unless the query requests
``cardinality at_most_one``; the environment tests check both SAT and UNSAT
forms.

The core formula
~~~~~~~~~~~~~~~~

The relation layer's final operation is conjunction.  It neither adds nor
interprets the property objective.

.. math::
   :label: bmc-core-formula

   Core_N=D_N\land I_0\land T_N\land ENV_N.

``build_bmc_core_formula`` constructs the four named fields in this order and
stores their conjunction in ``BmcCoreFormula.core``.  The core tests inspect
the canonical node and prove consequences by adding a negated expected value
to :math:`Core_N` and obtaining UNSAT.  Property compilation later forms a
separate solve formula from this core and an objective.

Counterexample: UNSAT of :math:`Core_3` means that no length-three encoded
trace satisfies these initial and environment constraints.  It does not prove
that the model has no trace at larger bounds, and it is not an unbounded model
checking theorem.

Formula ledger and review anchors
----------------------------------

The table is the forward audit map for the first 21 frozen equations.  Function
names refer to ``pyfcstm/bmc/relation.py``; tests are repository-local semantic
regressions, while the downloadable files above are independent documentation
resources.

.. list-table:: Frozen relation-equation ledger
   :header-rows: 1
   :widths: 22 25 29 24

   * - Equation
     - Implementation anchor
     - Test anchor
     - Working evidence
   * - :eq:`bmc-trace-frame-domain`
     - ``BmcTraceSymbols.allocate``
     - ``test_relation_core.py`` initial/core tests
     - Four frames at bound 3
   * - :eq:`bmc-trace-event-domain`
     - ``BmcTraceSymbols.allocate``
     - ``test_relation_environment.py`` selector-range test
     - Three ``Go`` slots
   * - :eq:`bmc-trace-variable-domain`
     - ``BmcTraceSymbols.allocate``
     - ``test_relation_core.py`` initializer/carry tests
     - Three families, twelve symbols
   * - :eq:`bmc-trace-selector-domain`
     - ``BmcTraceSymbols.allocate``
     - ``test_relation_core.py`` case/progress tests
     - Transition then two fallbacks
   * - :eq:`bmc-domain-formula`
     - ``_build_domain_formula``
     - ``test_relation_core.py`` domain consequences
     - State ids 1, 2 only on shown trace
   * - :eq:`bmc-initial-control`
     - ``_build_initial_formula``
     - cold/hot/terminated initial tests
     - ``Root.A`` at frame 0
   * - :eq:`bmc-initial-retained`
     - ``_build_initial_formula``
     - initializer type/value test
     - 0, :math:`1/2`, 5
   * - :eq:`bmc-initial-havoc`
     - ``_build_initial_formula``
     - havoc/where tests
     - Counterexample described above
   * - :eq:`bmc-initial-where`
     - ``_build_initial_formula``
     - contradictory ``where`` test
     - Frame-0-only constraint
   * - :eq:`bmc-case-antecedent`
     - ``_build_case_relation``
     - semantic fixture and priority tests
     - ``A`` plus ``Go`` at step 0
   * - :eq:`bmc-case-selector`
     - ``_build_case_relation``
     - selector truth checks
     - One selected label per shown step
   * - :eq:`bmc-case-relation`
     - ``_build_case_relation``
     - implication and runtime-alignment tests
     - Selected-case-only writes
   * - :eq:`bmc-case-post-control`
     - ``_build_case_relation``
     - event transition alignment test
     - ``Root.A`` to ``Root.B``
   * - :eq:`bmc-case-variable-write`
     - ``_build_case_relation``
     - action-order alignment tests
     - ``counter`` 0 to 11
   * - :eq:`bmc-case-variable-carry`
     - ``_build_case_relation``
     - unwritten carry test
     - ``ratio`` and ``keep`` unchanged
   * - :eq:`bmc-step-fallback`
     - ``_build_step_relation``
     - fallback runtime-alignment test
     - Idle ``B`` increments
   * - :eq:`bmc-step-terminated-absorb`
     - ``_build_step_relation`` / absorb branch
     - terminated/event rejection tests
     - Forged post-termination event is UNSAT
   * - :eq:`bmc-step-delta-gamma`
     - ``_build_step_relation``
     - delta/gamma contrast tests
     - false/true on idle ``B``
   * - :eq:`bmc-transition-formula`
     - ``_build_step_relation`` and core builder
     - bound-two recurrence test
     - Three linked steps
   * - :eq:`bmc-environment-formula`
     - ``_build_environment_formula``
     - frame/event/cardinality tests
     - true, false, false event vector
   * - :eq:`bmc-core-formula`
     - ``build_bmc_core_formula``
     - ``test_relation_core.py``
     - SAT complete prepared query

Reviewing the page therefore has two distinct parts.  Sphinx can verify that
all :eq:`bmc-core-formula`-style references resolve, and a bilingual drift
check can compare labels and literal LaTeX.  Neither check proves the semantic
claims: a reviewer must still compare every row with the named code, test, and
working trace.
