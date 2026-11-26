Release Notes
=============

Unreleased
----------

Regions
~~~~~~~

This release adds **ordered parallel regions** to FCSTM. A state can hold
several ``region`` blocks instead of ordinary child states. All of them are
active at once, and in every cycle they run one after another in the order they
are written. To see it work, follow :doc:`/tutorials/regions/index`.

**Language.**

- ``region Name { ... }`` is written inside a state. A state holds either
  ordinary child states or regions, never both, and may hold a single region.
  Regions can be nested: a state inside a region can own regions again.
- A region holds an initial transition, child states, ordinary and forced
  transitions, ``event`` declarations and ``>> during before/after`` aspects.
  It cannot hold ``enter``, ``during``, ``exit`` or variable declarations, and
  it is not the source or target of a transition. Two regions of one state
  cannot share a name; ``Duplicate region 'A' in R.`` is the model error.
- ``region`` and ``active`` are reserved words. A model that uses either as a
  state, event or variable name has to rename it.
- The writing order is the execution order, and it is part of the meaning of
  the model. A later region sees the values and states that an earlier region
  produced in the same cycle; an earlier region does not run again because of
  what a later one writes. When several regions write one variable, the last
  write wins.
- A transition cannot lead from one region into another, and a transition
  outside the owner cannot lead into a region. Enter the owner and let each
  region start from its initial transition.
- ``X -> [*]`` written inside a region finishes that region. When the last
  region of an owner finishes, the owner continues through its own transitions
  in the same cycle; the machine never rests with every region finished.
- A forced transition on the owner, such as ``!Running -> Idle : /Stop;``,
  takes the whole group away. It is expanded into ordinary ``-> [*]``
  transitions as described under *Forced Transitions* below.
- An event declared in a region belongs to that region, so two regions can use
  the same event name for different events. Use a path that starts at the root
  (``/Owner.Region.Event``) when several regions must share one event.
- ``active("State.Path")`` is a read-only query that can stand wherever a
  condition can.

**What supports regions.**

- Simulation: cold start, hot start, short event names that depend on the
  position, and ``pyfcstm simulate``; see *Simulating models with regions*
  below. The position is a tree, shown as a configuration text such as
  ``Controller.Running{Safety: Watching, Motion: On}``.
- ``pyfcstm inspect`` reports regions in its summary and adds two diagnostics
  about order. ``I_REGION_BACKWARD_READ`` is an information-level diagnostic: an
  earlier region reads a variable that a later region writes, or asks about the
  state of a later region, so it sees the previous cycle. It describes defined
  behavior, not a defect. ``W_REGION_BLIND_OVERWRITE`` is a warning: a later
  region unconditionally overwrites, in every cycle and without using the old
  value, a variable that an earlier region wrote, so the earlier write is always
  lost. Neither is reported when the later region might read the old value, when
  its write is conditional, when it can finish or contains an abstract action,
  or when a region in between reads the variable.
- ``pyfcstm.verify`` and the reachability analysis of inspect judge a state
  that owns regions by its branches (see *Inspect and verify* below).
- ``pyfcstm bmc`` and ``pyfcstm.bmc`` accept models with regions, including
  witnesses, replay and runtime safety checks (see *Bounded Model Checking of
  Regions* below).
- The built-in templates ``python``, ``c``, ``c_poll``, ``cpp`` and
  ``cpp_poll`` generate runtimes that run models with regions the way the
  simulator does; see *Templates and capability declarations* below.
- PlantUML and the diagram viewer draw regions as concurrent areas (see
  *Drawing regions* below).
- The VS Code extension previews models with regions, folds ``region`` blocks
  and reports ``E_REGION_STRUCTURE``, ``E_DUPLICATE_REGION`` and
  ``E_ACTIVE_QUERY_TARGET`` while you edit.
- The two packaged LLM guides, the FCSTM grammar guide and the FBMCQ language
  guide, describe regions.

**Getting started.** :doc:`/tutorials/regions/index` runs one controller
through simulation, region order, inspect, bounded model checking, generation
and drawing. Task recipes are in :doc:`/how_to/regions/index`, the reasons in
:doc:`/explanations/region_semantics/index` and
:doc:`/explanations/region_design/index`, and the exact rules in
:doc:`/reference/region_model/index`.

**Known limitations.**

- When two forced declarations in regions compete, the first one holds the
  whole group, and a leaf inside a region does not give way. This differs from a
  model without regions; see `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_.
- The behavior diagnostics of ``pyfcstm inspect`` should not depend on whether
  syntactic sugar is expanded; see `issue #588 <https://github.com/HansBug/pyfcstm/issues/588>`_.
- The editor preview draws history differently from the Python diagram
  snapshot; see `issue #590 <https://github.com/HansBug/pyfcstm/issues/590>`_.
  ``I_REGION_BACKWARD_READ`` and ``W_REGION_BLIND_OVERWRITE`` are reported by
  ``pyfcstm inspect`` only, not by the editor.
- The generated runtimes can still become smaller and faster. The Python
  template is tracked in `issue #596 <https://github.com/HansBug/pyfcstm/issues/596>`_
  and the C-family templates in `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_.
- Bounded model checking cost grows with the number of regions and the bound;
  `issue #600 <https://github.com/HansBug/pyfcstm/issues/600>`_ records the
  directions explored for the formula and the solver.

Templates and capability declarations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A template declares what it can render in the ``features`` list of its
``config.yaml``; ``region`` is the only feature so far, and
``StateMachineCodeRenderer.features`` returns the list. The five built-in
templates declare it. A model with regions given to a template that does not,
including a custom template directory, is refused with ``E_UNSUPPORTED_FEATURE``
before any file is written. The message of ``pyfcstm generate`` says how many
regions the model declares, which template authors should declare the feature,
and which built-in templates the model can use instead.

The generated Python runtime changes in these ways, for every model:

- The text of the generated file changes for models without regions; their
  behavior does not.
- ``vars`` is a read-only view. Write persistent values only through the model,
  or through the hot-start arguments.
- The ``variables`` alias is removed; use ``vars``.
- ``ABSTRACT_HOOKS`` is a read-only mapping.
- ``configuration`` gives the whole position as text, byte for byte the text the
  simulator prints; ``leaves``, ``is_active(path)`` and, for a model with
  regions, ``region_status(path)`` (``live``, ``done``, ``pending`` or
  ``inactive``) query it. ``initial_state`` accepts a configuration text, a dotted
  path or a tuple.
- A model with regions has no ``current_state_path`` or ``current_state_name``;
  reading them is an ``AttributeError``. The context of an abstract action also
  carries ``configuration``.

The C-family runtimes (``c``, ``c_poll``, ``cpp``, ``cpp_poll``) now run on a
static-memory kernel generated for each model. It uses no heap and no
third-party dependency, for models with and without regions alike. For every
model:

- The machine type is opaque. ``MAX_STACK_DEPTH`` and ``MAX_DFS_STEPS`` are
  removed; the public macros ``..._ARENA_CAPACITY``, ``..._TRAIL_CAPACITY`` and
  ``..._STORAGE_BYTES`` replace them, and a run that exceeds a capacity fails
  with a safety-limit error that names the macro.
- ``hot_start_at``, ``hot_start_at_with_parameters`` and ``get_configuration``
  are new, with a configuration value that can be queried, validated and
  formatted as the same text as the simulator; parsing it can be switched off
  with ``PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT``. The C++ wrappers add the
  matching members and ``operator==`` / ``operator!=``.
- A model with regions has no ``current_state_id``, ``current_state_path`` or
  ``current_state_name``; using one is a compile error.
- The generated text changes for models without regions; the behavior does not.
- Code size and RAM per machine grow for models without regions: the median
  increase measured over the models without regions is 2.84 times for code and
  3.05 times for RAM, and a chain of 16 or more pseudo states is slower than with
  the previous template. See `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_.

Drawing regions
~~~~~~~~~~~~~~~

``pyfcstm plantuml`` draws the regions of a state as concurrent areas separated
by ``--``. Each area starts with a note ``region N: Name``, where ``N`` counts
from 1 in writing order, because a PlantUML area has no name of its own.
``active("Path")`` is shown as written; the hidden flags and automatic writes
are not drawn.

``StateMachine.diagram()``, ``pyfcstm diagram`` and the HTML viewer place the
regions of one owner side by side inside its frame, separated by dashed lines,
without a frame of their own and with the same ``region N: Name`` title. The
order follows the direction of the layout: left to right in a top-down graph,
top to bottom in a left-to-right one. Folding, details and export work for
regions as they do for states. A region counts as one level for ``max_depth``.
The viewer does not highlight the current configuration. The JSON of the diagram
marks each region node with ``"region": true``.

Forced Transitions
~~~~~~~~~~~~~~~~~~

A forced transition ``!S -> T`` whose source ``S`` has states inside it is now
carried out the same way in every model: its event and guard are decided once,
at the state the machine rests in, and nothing on the way up asks again.
Earlier releases put a copy of the event and the guard on every state below
``S``, pseudo states included, and judged each copy again as the exit moved up.
Models without forced transitions are not affected. For models that have them,
four behaviours change:

- **A guard that refers to a state inside the source.**
  ``!P -> Q : if [active("Root.P.a2")];`` is taken when the machine rests in
  ``a2``. It used to be judged again after ``a2`` had been left, where it could
  never hold.
- **An exit action that changes what the guard reads.** The guard is no longer
  judged again after the exit actions on the way out have run, so they cannot
  cancel the transition half-way and leave the machine in its old state.
- **An entry that passes through a pseudo state.** A forced transition is not
  taken from a pseudo state. When its event or guard already holds in the cycle
  that enters ``S`` through a pseudo state, the entry now completes and the
  forced transition is taken in the next cycle.
- **A target that cannot be entered.** The forced transition then takes
  nothing: it does not leave the state the machine rests in and does not
  consume the event, and no other transition that leaves ``S`` picks the
  machine up half-way. The transitions of the resting state itself are tried
  as usual.

``CycleResult.consumed_events`` lists the event of a forced transition once.
It used to list it once for every level that was left.

When the source of a forced transition contains regions, each region is finished
by ordinary ``-> [*]`` transitions, which the language already has; nothing
takes a whole group away at once. A state that can be rested in below a region
gets two of them: a starter with the declared event and condition, which raises
the hidden variable, and in front of it a follower, which waits for the
variable. Regions advance in declaration order, so the first region whose state
sees the event and the condition raises the variable and finishes, and every
region after it finishes in the same cycle when it sees the variable. When the
last region has finished, the owner continues through its own transitions like
it does for any group that is done. Three things follow:

- **Regions leave in declaration order.** The exit actions of the first region
  run first, nested owners leave after their own regions, and the owner exits
  last.
- **A condition that becomes true while the regions work.** A region that runs
  after the one that made it true sees it in the same cycle and finishes at
  once; the regions before it finish in the next cycle.
- **A target that cannot be entered.** The regions that finished stay finished,
  the last region keeps working with the variable raised, and the group leaves
  in the first cycle in which the target can be entered. When two declarations
  of one owner compete, the one that was raised first holds the group; the
  second is not tried in the meantime, which differs from a model without
  regions, where a target that cannot be entered makes the next declaration
  count.

The text of ``to_ast_node()`` loads to the same machine in all these cases.

Three things become visible:

- Each such declaration is carried out with a hidden ``int`` variable
  ``__forced_<n>``; a name the model already uses is skipped. Like ``__hist_*``
  it appears in ``StateMachine.defines``, ``runtime.vars``, the variable
  snapshots of abstract handlers and the variable tables of generated code, and
  it is an ordinary variable everywhere: a hot start supplies it like every
  other variable, and BMC treats it like every other variable. The machine only
  raises it inside a cycle, so it is 0 at every point where a run rests.
  :attr:`pyfcstm.model.model.StateMachine.forced_variables` lists the names.
- A transition with an event that leaves a state on the way of a forced exit is
  split through a generated pseudo state ``__forced_gate_<n>``. The pseudo
  state appears in ``walk_states()`` and as one more state passed through in an
  execution trace.
- ``to_ast_node()`` exports the machine that runs, with those variables and
  pseudo states, as it already does for history. The model loaded from the
  exported text is the same machine: it takes the same cycles and the same hot
  starts, and every reachability and BMC question gets the same answer. That
  holds for a forced transition that reaches regions as well.

PlantUML, the diagram viewer and ``pyfcstm inspect`` keep showing a forced
transition as one transition per state it applies to. For a model with any
forced declaration they show the model as it was loaded: a model object edited
afterwards is drawn without the edit. A declaration whose sources have nothing
inside them stays one transition per source and gets no variable. In collect
mode (``parse_dsl_node_to_state_machine(..., collect=True)``) a faulty forced
declaration is reported once instead of once per level it was expanded to.

The machine that runs carries no trace of a forced declaration: none of its
transitions is marked ``Transition.is_forced`` or keeps a ``forced_origin``. It
is plain FCSTM, and everything that executes it or answers a question about it,
the simulator, the generated runtimes, BMC, the analyses of
:mod:`pyfcstm.verify` and the analyzers of
:mod:`pyfcstm.diagnostics.analyzers`, takes it as it is, with the generated
transitions and the gate states ``__forced_gate_<n>`` that code walking
``walk_states()`` and ``State.transitions`` meets. The marks exist only in the
model as written, which drawings and
:func:`pyfcstm.diagnostics.inspect.inspect_model` are built from, so the
warnings that are about a declaration itself, such as
``W_FORCED_GUARD_UNSAT``, come from the inspect report. The per-transition
algorithm ``forced_guard_unsat_under_init`` therefore only reports a
transition that is handed to it marked.

Code that compared ``StateMachine.defines``, ``walk_states()`` or exported DSL
text of a model with forced transitions against stored values needs new
expected values. A hot-start snapshot taken from ``runtime.vars`` keeps its
``__forced_*`` entries and supplies them with the other variables.

Bounded Model Checking of Regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:func:`pyfcstm.bmc.build_bmc_core_formula` now describes models that declare
regions. A state that owns regions advances them one after another in a single
cycle, each on the values the previous one left behind, and the formula grows
with the sum of the regions instead of the product of their paths:

- every region has a position symbol per frame, which holds the state its
  branch rests in, or ``REGION_DONE_ID`` once it finished, or
  ``REGION_INACTIVE_ID`` while its owner is not resting;
  ``BmcTraceSymbols.region_position`` returns it;
- starting a state that owns regions starts every region in order, and a region
  that cannot start makes the whole entry fail, which a cold start reports as a
  Delta;
- the last region may only finish if its owner can continue in the same cycle;
- ``>> during`` aspects and the plain ``during before`` of a state that owns
  regions are encoded the way the simulator runs them.

A hot start, :func:`pyfcstm.bmc.compile_bmc_property`,
:func:`pyfcstm.bmc.check_runtime_safety` and ``pyfcstm bmc`` accept such a model
too:

- ``init state("...")`` takes a configuration text such as
  ``Controller.Running{Safety: Watching, Motion: On}``, the path of a state
  inside a region, or the path of an owner alone. A region that is left out, or
  written ``[init]``, waits for its start in the first cycle
  (``REGION_PENDING_ID``). A start that leaves every region of an owner done is
  refused with ``invalid_start_position``;
- ``called`` and ``call_count`` count the abstract calls of regions, runtime
  safety checks the operations of every region, including the probes of
  candidates that were not chosen, and a region that cannot start makes the
  whole cycle a Delta that keeps positions and variables;
- witness frames carry an optional ``configuration`` text, region steps carry
  ``local_cases`` (``scope``, ``kind`` and ``label``), and abstract calls carry
  the configuration of the whole machine at the moment of the call. The
  ``case_label`` of a step is the label of the case that ran outside every
  region, or ``null`` when no case did. Replay compares configurations,
  variables, events, inputs and calls, and it also compares the transitions each
  step committed with the ones the simulator committed, which is what checks the
  case labels. The human report prints one line per region step, with the scope
  of a local case written relative to the owner it belongs to. The new JSON
  fields are optional and absent for models without regions;
- a call of a ``>> during after`` aspect that is settled when a group of regions
  finishes is counted against the state the simulator tells its handler, so
  ``call_count(..., state=...)`` and ``active_leaf=`` agree with a simulated run
  call by call;
- ``active("...")`` accepts a configuration text as a *pattern* (see
  :doc:`the FBMCQ reference </reference/bmc_query/index>`): the regions it
  writes have to be where it says and the regions it leaves out are free;
  ``[done]`` and ``[init]`` are allowed and owners nest. Inside the ``where`` of
  a call filter it describes the machine at the moment of the call. A pattern
  that is not a position of the model is refused with
  ``invalid_active_pattern``, and one expression that nests deeper than 100
  levels is refused with ``expression_too_deep`` instead of exhausting the
  Python stack.

A group that re-enters itself on changing values is unrolled to
:attr:`pyfcstm.bmc.BmcOptions.max_group_reentries` times (16 by default); a
model that needs more raises :class:`pyfcstm.bmc.BmcBuildError` instead of being
approximated, and the option raises the bound. Models without regions produce
the same formulas as before.

History and ``active()``
~~~~~~~~~~~~~~~~~~~~~~~~

The hidden variables of history and of ``active()`` are ordinary variables too,
so a model and the text it exports behave the same in every stage:

- A hot start no longer checks the values of ``__hist_goto`` and the
  ``__hist_*`` records, and a havocked start of a BMC query is no longer kept
  inside the values an execution holds. Whatever value is given is what the
  machine runs on; ``StateMachine.history_variables()`` still computes valid
  ones. The category ``domain.history_variable`` of BMC constraint groups no
  longer exists.
- A model that uses ``active()`` is accepted by hot start, ``pyfcstm simulate``,
  code generation, ``pyfcstm bmc`` and the structural ``pyfcstm.verify``
  algorithms. Its flags ``__active_*`` are supplied by a hot start like any
  other variable; ``StateMachine.active_variables()`` computes them from a
  position. The ``E_UNSUPPORTED_FEATURE`` code lists no ``active`` feature any
  more and the inspect report no longer carries the reason
  ``active_query_unsupported``.

Inspect and verify
~~~~~~~~~~~~~~~~~~

With ``--enable-verify``, the findings of the verify pipeline (``W_DEAD_GUARD``,
``W_GUARD_TAUTOLOGY``, ``W_EFFECT_SMT_NO_OP``, ``I_EFFECT_GUARD_CONTRADICT``,
``W_TRANSITION_SHADOWED``, ``I_ENTER_DURING_CONTRADICT``,
``W_COMPOSITE_INIT_INCOMPLETE``, ``I_NONTRIVIAL_SCC``,
``W_TOPOLOGICAL_NOEXIT``, ``I_TOPOLOGICAL_NON_TERMINATING`` and
``W_EVENT_UNREACHABLE_EMIT``) are judged on the machine that runs. A model that
uses history, ``active()`` or a forced declaration and the text it exports then
give the same ones. The report itself and every finding about what was written
still come from the model as written, and so does ``W_FORCED_GUARD_UNSAT``,
which judges a declaration. A condition on ``active("...")`` is judged like any
condition over its hidden flag instead of being skipped. A finding of the
machine that runs can name a hidden variable or a generated pseudo state and can
report something about them: the relay of a forced declaration lowers the
variable its own guard reads, which is ``I_EFFECT_GUARD_CONTRADICT``. Each such
finding points at the declaration, history or queried state it was lowered
from. A combo trigger keeps reporting the findings about its generated guard as
the term of the trigger, through the ``W_COMBO_*`` codes.

The structural algorithms of ``pyfcstm.verify`` and the reachability of the
inspect report accept models with regions. A composite state is judged by its
branches: a state that owns regions has one branch per region, and a composite
state without regions is the case of one branch, so a model without regions is
the special case of none. An ordinary transition that leaves a composite state
is taken only once a child of it can reach ``[*]``, and a forced transition
leaves from every leaf. This changes what inspect reports for a model without
regions in one respect: a composite state none of whose children can leave never
takes its ordinary outgoing transitions, so the state it leads to is reported
by ``W_UNREACHABLE_STATE`` and the transition gets the reason
``owner_never_completes`` in ``unreachable_transition_reasons``. The simulator
behaves that way already; earlier reports treated the composite state as
something the machine could simply leave. The exits that the expansion of
``!S -> T`` adds below ``S`` do not count as a child leaving on its own, and a
history default that a transition enters through ``Owner.[H]`` starts a branch
like the initial transition does. The jsfcstm inspect report follows the same
rule. The algorithms of ``pyfcstm.verify`` judge the machine that runs, where a
forced declaration is a relay, and stay a guard-agnostic over-approximation
there: a state behind a composite that only a forced declaration can take
elsewhere may still be listed as reachable by them.

The solver queries of ``pyfcstm.verify`` each run in a Z3 context of their own.
Extracting one model from the shared context used to turn the answer of a later
non-linear query from ``sat`` into ``unknown``, so a result depended on what the
process had solved before. A condition such as ``x ** y > 0``, which Z3 cannot
decide, now gives ``unknown`` every time.

Diagrams
~~~~~~~~

A model that uses history is drawn as written. PlantUML shows a transition that
enters a history as ``Owner[H]`` or ``Owner[H*]``, and the default of each
history as a ``[H] -> Child`` or ``[H*] -> Child.Leaf`` line in the description
of the owner, because PlantUML cannot draw an arrow out of a history that a
transition enters. The
diagram snapshot labels such a transition ``Owner.[H]`` or ``Owner.[H*]``.
The hidden variables, gate states and route transitions that history is lowered
into are not drawn, as is already the case for forced declarations.

Simulating models with regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A model with regions can now be hot-started, driven with short event names and
run with ``pyfcstm simulate``.

**Hot start.** ``SimulationRuntime(initial_state=...)`` takes a configuration
text such as ``"Controller.Running{Safety: Watching, Motion: On}"``, a
:class:`~pyfcstm.model.configuration.Configuration`, a state path that may pass
through regions, or a state. What is written is put in place without any
``enter``. What is not written waits for initialization and runs its initial
transitions in the first cycle, in writing order, while the rest works as usual:
a plain composite state written without a child, a region that is left out (a
path into a region leaves the other regions of its owners out), and an owner
written as a bare path. A region written as ``[done]`` stays done. A position in
which every region of an owner is done is rejected, at any depth. Hidden
variables are ordinary variables and have to be given like any other; nothing is
derived from the position.

**Event names.** A full path and a name that starts at the root mean the same
wherever the machine rests. A name that depends on the position, such as ``Go``
or ``.Reset``, used to be refused as soon as several leaves were active. It is
now resolved once for every active leaf: if no leaf finds an event the name is
unknown, if the leaves that find one all find the same event it is used, and if
they find different events the name is ambiguous and the error lists every
candidate with the leaves that led to it.
:meth:`pyfcstm.model.configuration.Configuration.resolve_event` follows the same
rule.

**Command line.** ``pyfcstm simulate`` no longer refuses a model with regions.
The position is shown as its configuration text in the current-state display,
the table of several cycles and the history; ``init`` takes a configuration text
(``init Controller.Running{Safety: Watching, Motion: On} permit=1``); the event
list and the completion cover every active leaf, and a short name that two leaves
use for different events is not offered; ``init`` completes the states inside
regions. A model without regions behaves exactly as before.

Models without regions are not affected by any of this: their hot start and
event names are the same as in the previous release. Two fixes to the command
line apply to every model:

- ``events`` and the completion of ``cycle`` show a short name only when typing
  it works. An event that belongs to a state above the leaf (a composite state,
  a region, an owner) used to be listed as ``Stop (Root.Run.Stop)``, although
  ``cycle Stop`` was refused; it is now listed by its full path alone.
- ``init`` refuses a variable that is assigned twice (``init S n=0 n=5``) instead
  of silently keeping the last value, like ``cycle --input`` already did.

An ``init`` whose braces are not balanced is reported as such for every model. An error that names a path now writes it as ``'W.Nowhere'`` instead of a tuple,
and an event name that is ambiguous between several leaves is reported as such,
with its candidates, instead of after a generic "cannot resolve" sentence.

v0.6.0
------

This minor release adds an end-to-end FBMCQ bounded model checking workflow,
makes inspect reports useful to both people and LLM repair loops, expands the
built-in runtime templates to Python, C, C Poll, C++, and C++ Poll, and ships
substantially expanded bilingual documentation. It also contains public API and
CLI compatibility changes that require callers to review the migration notes.

FBMCQ and Bounded Model Checking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added the FBMCQ property language, parser, model binding, macro expansion,
  transition-relation compiler, Z3 solving pipeline, and public
  :mod:`pyfcstm.bmc` APIs. The language covers reachability, coverage, safety,
  bounded liveness, response, assumptions, and initial-state constraints.
- Added ``pyfcstm bmc`` for one FCSTM model and one FBMCQ query. The default
  terminal report states whether the bounded property holds before showing the
  SAT/UNSAT solver diagnostic, supports optional ANSI color, and requires every
  decoded SAT witness to pass structural validation and simulator replay.
- Added a stable structured JSON result for CI, tools, and LLM consumers, with
  a downloadable schema in the BMC result protocol reference.
  The envelope preserves polarity-aware outcomes, solver timing, witness and
  replay records, diagnostics, and the matching process exit code.

Inspect and Diagnostics
~~~~~~~~~~~~~~~~~~~~~~~

- Changed ``pyfcstm inspect`` to default to a checker-style human report with
  aligned source spans, nearby source context, compact severity labels, and
  ``--color auto|always|never``. Files, pipes, and machine formats remain free
  of ANSI escapes.
- Kept the machine report under ``--format json`` and added ``--format
  llm-json`` and ``--format llm-md``. LLM reports use the schema file shipped
  with the running release and carry source context, provenance, repair
  guidance, and explicit do-not notes; the public payload has no product-level
  schema version or status field.
- Added the descriptive ``summary.structure_statistics`` section to the LLM
  report and ``ModelInspect.structure_statistics`` to the full report. The
  rates are raw
  fractions, use ``null`` for empty denominators, and record conservative
  advisory defaults for transition density and unreachable populations.
  The canonical ``W_UNREACHABLE_TRANSITION`` warning aggregates the reason
  buckets once per authored transition; thresholds remain metadata only and
  do not create a health score. Python callers and the CLI can override or
  disable the thresholds.
- Expanded static and verify-backed diagnostics, including numeric and guard
  reasoning, while keeping solver-backed inspect checks behind the existing
  explicit enablement and safety gates.
- Added ``ModelInspect.verification`` execution metadata to the full JSON/API
  report. Consumers can distinguish disabled verification, policy-excluded
  algorithms, definite results, and indeterminate outcomes without treating
  any of those states as new model diagnostics. The human CLI shows compact
  coverage and indeterminate reasons; the LLM presentation includes the
  structure statistics section described above. The schema file remains a
  release-shipped contract rather than a payload-level version marker.
- Added isolated multi-provider repair evaluations that test whether a consumer
  can locate, explain, repair, and replay real diagnostics without access to
  hidden repository context.

Simulation and Runtime Semantics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Hardened hot start, pseudo-state routing, DFS limits, stack stabilization,
  speculative rollback, expression short-circuiting, persistent-variable
  normalization, event ownership, history resizing, and terminal queries.
- Added :class:`pyfcstm.simulate.CycleResult` event accounting and strengthened
  abstract-handler registration, decorator scanning, execution context, named
  action references, warning metadata, and session-copy behavior.
- Changed non-stoppable hot-start and pseudo-state no-progress behavior to a
  successful Delta cycle: construction no longer rejects a valid blocked target,
  and the first real ``cycle()`` reports ``delta=True`` while advancing the
  public cycle/history contract.
- Extended the shared semantic fixture corpus so the simulator and generated
  runtimes are checked against the same cycle-by-cycle state, variable, event,
  history, callback, and failure behavior.

Compatibility notes
~~~~~~~~~~~~~~~~~~~

- Removed the product-version fields from BMC CLI and witness/native results
  and changed the downloadable result schema to an unversioned filename.
  Consumers must stop reading the removed fields and update schema download
  paths; the standard JSON Schema ``$schema`` dialect URI remains unchanged.

Built-In Templates and DSL
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added the first-class ``cpp`` and ``cpp_poll`` built-in templates alongside
  ``python``, ``c``, and ``c_poll``. C-family templates use CMake-driven native
  checks, simulator-alignment fixtures, wrapper smoke tests, and explicit
  deployment profiles without requiring heap allocation in the runtime core.
- Added ordered combo-transition triggers that combine event and guard terms in
  one cycle. They expand into traceable pseudo relay states while preserving
  source metadata, guard/effect order, rollback, PlantUML output, inspect
  reports, simulation behavior, and generated-runtime alignment.
- Added template-suite detection and dedicated representative/full-suite jobs
  so source-template dependencies and native toolchain coverage fail closed
  without forcing every ordinary change through every expensive native suite.

LLM Prompt Resources
~~~~~~~~~~~~~~~~~~~~

- Added the packaged FBMCQ authoring guide and integrity-checked public APIs:
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_for_llm`,
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_path_for_llm`, and
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_metadata_for_llm`.
- The FCSTM and FBMCQ guide APIs now live in dedicated modules while
  :mod:`pyfcstm.llm` remains the compact public import surface. Both Guide
  resources use adjacent SHA-256 sidecars generated by ``make sha256``.
- Added standalone FBMCQ Guide evaluation fixtures for seven property kinds,
  full-source and known-fact task forms, oracle checks, anti-vacuity checks,
  mutation discrimination, and trace replay. Provider transcripts remain
  repository evidence rather than package data.

Documentation and Release Artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Reorganized the bilingual documentation around Tutorials, How-to Guides,
  Explanations, and Reference material, with runnable examples and dedicated
  coverage for the DSL, simulation, inspect, templates, and BMC workflows.
- Added bilingual BMC Tutorial and How-to material, three mathematical
  Explanation pages, and exhaustive query/result Reference pages. The
  explanations derive 40 labelled, implementation-traceable equations and are
  verified in MathJax HTML and XeLaTeX PDF output.
- Hardened the bilingual Sphinx PDF path with isolated builds, XeLaTeX/CJK font
  checks, structural/content validation, adversarial self-checks, and complete
  contents/index verification. GitHub Releases now attach validated English and
  Chinese PDF manuals in addition to package, CLI, and VSIX artifacts.

Verification and Inspect
~~~~~~~~~~~~~~~~~~~~~~~~

- Removed the unimplemented ``bounded_reachability``, ``symbolic_bfs``,
  ``bounded_safety``, ``bounded_invariant``, and ``path_witness`` entries from
  :data:`pyfcstm.verify.REGISTRY`. The registry now contains only its 14
  callable structural and SMT-local algorithms.
- Removed the verify-only taxonomy values ``bmc_search``, ``k_unrollings``,
  ``k_unrollings_times_branching``, and ``bmc_unrolled``. BMC queries and
  witnesses are exposed by :mod:`pyfcstm.bmc`, not through verify or inspect.

Compatibility Notes
~~~~~~~~~~~~~~~~~~~

BMC results are bounded by the query's ``<= N`` and are not unbounded proofs.
Scripts must consume ``--json`` instead of parsing human wording, color, or
live timing. SAT means a witness for witness-polarity properties and a
counterexample for counterexample-polarity properties; use the reported
property verdict or ``result.outcome`` rather than treating SAT as success.

The default ``inspect`` output is now intended for humans. Existing scripts
that parsed the former default JSON output must pass ``--format json``. LLM
automation should use ``llm-json`` or ``llm-md`` rather than parsing the human
report.

Code that referenced the removed verify registry keys or taxonomy values must
migrate to the public :mod:`pyfcstm.bmc` query APIs. The ``inspect`` CLI no
longer accepts the removed BMC-only values merely to reject them in application
code; Click now reports them as invalid choices with usage exit status ``2``
instead of the former policy-error status ``1``.

The five built-in templates remain marked experimental. The VSCode extension
continues to use its own independent version line and is not versioned as
``0.6.0`` by this Python package release.

v0.5.0
------

This release is a minor release rather than a ``v0.4.2`` patch release. It adds
new user-facing APIs, CLI surfaces, packaged LLM resources, verification-backed
diagnostics, DSL condition operators, and simulator semantic fixes. Existing
models should review the compatibility notes before upgrading.

Verification and Inspect
~~~~~~~~~~~~~~~~~~~~~~~~

- Added the :mod:`pyfcstm.verify` package as the public entry point for raw
  verification algorithms, registry metadata, complexity taxonomy, and inspect
  gating helpers.
- Added SMT-local verification algorithms for guards, effects, lifecycle
  relations, transition shadowing, and composite initialization checks.
- Integrated inspect-eligible verification algorithms into
  :func:`pyfcstm.diagnostics.inspect_model` and the ``pyfcstm inspect`` CLI.
  Verify-backed checks stay opt-in through ``enable_verify=True`` or
  ``pyfcstm inspect --enable-verify``.
- Added inspect safety gates for complexity tier, call-count scaling, and SMT
  timeout forwarding. BMC-style search remains outside the automatic inspect
  path.

Diagnostics and CLI
~~~~~~~~~~~~~~~~~~~

- Expanded the structured diagnostics catalog to 59 codes: 20 errors,
  32 warnings, and 7 infos.
- Added verify-backed diagnostic coverage while keeping the default inspect
  path static unless verification is explicitly enabled.
- Added ``pyfcstm inspect`` for stable JSON output matching
  ``inspect_model(model).to_json()``.
- Preserved Python / jsfcstm diagnostic-surface parity for normalized code,
  severity, and reference payloads used by editor integrations.

LLM Grammar Guide
~~~~~~~~~~~~~~~~~

- Added :mod:`pyfcstm.llm` with
  :func:`pyfcstm.llm.get_grammar_guide_prompt_for_llm`,
  :func:`pyfcstm.llm.get_grammar_guide_prompt_path_for_llm`, and
  :func:`pyfcstm.llm.get_grammar_guide_prompt_metadata_for_llm`.
- Packaged the official LLM-facing FCSTM grammar guide as
  ``pyfcstm/llm/fcstm_grammar_guide.md``.
- Added a packaged SHA-256 sidecar and runtime integrity verification for the
  grammar guide prompt. Callers may downgrade integrity failures to warnings
  when they intentionally need to inspect a damaged or development resource.
- Added standalone ``llm_eval/`` fixtures and reports for prompt-quality
  validation. These files are repository evaluation assets and are not packaged
  into PyPI distributions.

Simulation and Built-In Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Hardened simulator semantics around speculative rollback, hot-start
  initialization, event normalization, lifecycle action references, abstract
  handler contracts, and cycle boundary behavior.
- Added a semantic fixture corpus for simulator and generated-runtime alignment.
- Stabilized generated Python runtime metadata, callback rollback behavior, and
  expression-error wrapping.
- The packaged built-in template flow remains available through
  ``pyfcstm generate --template ...``. Current packaged templates are
  ``python``, ``c``, and ``c_poll``; the VSCode extension has its own
  independent version line and is not versioned as ``0.5.0`` by this Python
  package release.

DSL Expression Operators
~~~~~~~~~~~~~~~~~~~~~~~~

This release extends ``cond_expression`` with three boolean operators for guard
conditions and other boolean expression sites:

- ``A => B`` and ``A implies B`` express implication. The canonical DSL spelling
  is ``=>``. Implication is right-associative, so ``A => B => C`` means
  ``A => (B => C)``.
- ``A xor B`` expresses boolean exclusive-or. Chained ``xor`` is a
  left-associative boolean parity chain, not an exactly-one-of-many operator.
- ``A iff B`` expresses boolean equivalence and is the readable spelling of
  boolean equality. Chained ``iff`` expressions use the same boolean equality
  precedence layer as ``==`` and ``!=``.

Compatibility Notes
~~~~~~~~~~~~~~~~~~~

``implies``, ``xor``, and ``iff`` are now reserved DSL keywords. Existing
machines that used these names for variables, states, or events must rename
those identifiers before using this release.

``->`` remains the state-transition arrow and is not an implication operator in
guard conditions. Use ``=>`` or ``implies`` instead.

``^`` remains the numeric bitwise XOR operator. It can be used inside arithmetic
expressions that are compared in a guard, for example:

.. code-block:: fcstm

   StateA -> StateB : if [(flags ^ 0xFF) == 0];

It is not a boolean XOR spelling:

.. code-block:: fcstm

   StateA -> StateB : if [a > 0 xor b > 0];   // valid
   StateA -> StateB : if [(a > 0) ^ (b > 0)]; // invalid
   StateA -> StateB : if [true ^ false];      // invalid

The verification and inspect APIs are new public surfaces in this release. They
are intended to be stable at the function and JSON-contract level, but callers
should still treat precise diagnostic wording and solver evidence text as
diagnostic payloads rather than hard-coded parsing targets.
