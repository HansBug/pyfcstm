Release Notes
=============

v0.7.0
------

This minor release adds **ordered parallel regions** to FCSTM and carries them
through simulation, inspect, bounded model checking, diagrams, the built-in
templates and the documentation. It also adds variable roles with read-only
inputs and parameters, operator semantics shared by the simulator, the solver and
the generated runtimes, execution traces, Python diagram snapshots and an
interactive viewer, and a larger bounded model checking toolbox. It contains
incompatible changes; read *Upgrading from 0.6.0* at the end of this section
before updating.

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
- Code size, RAM and the time per cycle of a generated machine change for
  models without regions as well, because they now run on the same kernel. The
  measured size and speed ratios against the previous template, with their
  method, are in the section *Generated C runtime* of
  :doc:`/explanations/region_performance/index`; the remaining cost is tracked in
  `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_.

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
  other variable, and BMC treats it like every other variable. The machine
  raises it inside a cycle and a finished declaration leaves it at 0, so it is 0
  wherever a run rests, except while a group is left half-way because the target
  cannot be entered: it stays 1 until the group leaves.
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

Variable Roles and Read-Only Inputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A top-level variable now has a **role** that says who owns it. ``control``
(and its older spelling ``def``) is the ordinary variable the model reads and
writes. ``output`` is written by the model for an external consumer. ``input``
is supplied by the environment once per cycle, and ``param`` is fixed when the
machine is built; the model may only read these two.

.. code-block:: fcstm

   input float pressure;
   param float gain = 2.0;
   output float reading = 0.0;
   control int count = 0;

- ``input`` takes no initializer. ``control``, ``output`` and ``param`` need
  one. An assignment to an ``input`` or ``param`` anywhere in a lifecycle
  action, aspect or effect, including an unreachable branch, is a model error
  (``E_INPUT_WRITE`` and ``E_PARAM_WRITE``, for example ``Model operations
  cannot write input 'a'.``). The initializer rules have their own codes,
  ``E_INPUT_INITIALIZER`` and ``E_VARIABLE_INITIALIZER_REQUIRED``.
- ``control``, ``input``, ``param``, ``output`` and ``var`` are reserved words,
  like ``region`` and ``active`` (see *Regions*). A model that uses one of them
  as a state, event, action or variable name has to rename it. A model that
  declares every variable with ``def`` keeps its meaning: each of those
  variables is a ``control`` variable.
- ``import`` mappings accept ``var`` as the canonical keyword; ``def`` is still
  accepted. A child ``input`` can bind to an explicit parent ``param``,
  ``input``, ``control`` or ``output`` declaration and takes the parent's role;
  the combinations that are forbidden, and the diagnostics they raise, are
  listed in the import section of :doc:`/reference/dsl/index`.
- ``pyfcstm.model.VariableRole`` and ``VarDefine.role`` expose the role.
  ``StateMachine.control_variables``, ``inputs``, ``parameters``,
  ``output_variables`` and ``persistent_variables`` return read-only mappings in
  declaration order. Exporting a model back to DSL keeps the spelling that was
  declared.
- ``pyfcstm inspect`` lists each variable's role and external supply, and the
  full report adds ``read_sites`` and ``write_sites`` to every variable. An
  input, a parameter or an output is not reported as an unused, unwritten or
  write-only variable merely because the model never writes or never reads it.
  The field contract is in :doc:`/reference/inspect_report/index`.

Parameters and Cycle Inputs in Simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simulator and the generated runtimes follow the roles. Models that declare
no ``input`` and no ``param`` behave as before.

- ``SimulationRuntime(model, parameters=..., input_source=...)`` fixes the
  parameters at construction and binds a source to every input. A source is a
  number, one of the new built-in generators (``ConstantIntInput``,
  ``SequenceInput``, ``UniformIntInput``, ``NormalFloatInput``,
  ``CallableInput``, ``ReplayInputPattern`` and the other classes of
  :mod:`pyfcstm.simulate`), or your own object that follows
  ``ScalarInputPattern`` or ``IntegratedInputPattern``. Every cycle reads each
  source once and freezes the vector for the whole cycle;
  ``runtime.cycle(inputs={...})`` overrides values for one call.
- ``CycleResult.inputs``, ``runtime.last_inputs``, ``runtime.parameters``,
  ``runtime.outputs`` and ``runtime.control_variables`` expose the values.
  ``runtime.vars`` holds only the control and output variables, and history
  entries of a model with inputs carry ``inputs``. Abstract-handler contexts
  (``ReadOnlyExecutionContext``) expose ``inputs`` and ``parameters`` apart from
  ``vars``. A source that fails to read does not advance, and the failure is a
  ``SimulationRuntimeInputSourceError`` with a ``code`` such as
  ``E_INPUT_SOURCE_READ`` or ``E_INPUT_SOURCE_MISSING``.
- An ``int`` variable, input or parameter accepts an integral float such as
  ``2.0`` and stores it as an int.
- ``pyfcstm simulate`` gains ``--param NAME=VALUE`` (repeatable, fixed for the
  session) and ``cycle --input NAME=VALUE``. Every real cycle needs the complete
  input vector; there is no zero-fill or hold. The runnable contract is in
  :doc:`/reference/simulation/inputs`.
- The built-in ``python``, ``c``, ``c_poll``, ``cpp`` and ``cpp_poll``
  templates generate the same split: parameters are constructor arguments, and
  inputs are acquired once per cycle through reader methods (``read_<input>()``
  and ``get_input_<input>()`` in the Python runtime) or, in C, through an input
  provider.

Documentation Blocks
~~~~~~~~~~~~~~~~~~~~

A block comment written directly before a variable declaration, a state
(including the root and pseudo states), an event, a transition or a lifecycle
action is now that declaration's **documentation**. Before, such a comment was a
syntax error. Documentation is metadata: it does not change execution,
simulation, verification, PlantUML output or inspect reports.

.. code-block:: fcstm

   /* Number of retries allowed before the fault state. */
   def int retry_limit = 3;

   /* The top-level state. */
   state Controller {
       [*] -> Ready;
       /* A request is being processed. */
       state Ready;
   }

- The Python model carries it in a ``doc`` field on ``VarDefine``, ``State``,
  ``Event``, ``Transition``, ``OnStage`` and ``OnAspect``. ``to_ast_node()`` and
  the DSL export write it back as a block with a star margin, keeping ``None``,
  the empty string and ``*`` distinct.
- The trailing spelling of an abstract action, ``enter abstract Name /* doc */;``
  remains valid. Writing both a leading and a trailing block for one action is
  rejected. ``import`` declarations and import mapping entries cannot own
  documentation.
- A block comment that is never closed is reported as ``Unterminated multiline
  comment - missing closing '*/'``.
- Field rules are in the documentation section of :doc:`/reference/dsl/index`.

Evaluation Semantics of Operators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The result type, value and runtime error of every operator and math function is
now defined once, in :mod:`pyfcstm.semantics.catalog`. The simulator, the
generated runtimes, ``inspect`` (constant folding and numeric diagnostics), the
verifier and ``pyfcstm bmc`` read it, so they no longer disagree. The table of
operations, results and error kinds (``division_by_zero``, ``modulo_by_zero``,
``zero_negative_power``, ``complex_result``, ``negative_shift_count``,
``math_domain``, ``writeback_non_integral``, ``writeback_non_finite`` and the
others) is the *Evaluation semantics* section of :doc:`/reference/dsl/index`.

Simulator, for every model:

- A rejected write of the result into a variable is now a
  ``SimulationRuntimeExpressionError``, with the catalog error kind in
  ``error.kind``, instead of a raw ``ValueError``. This covers a non-integral
  value written to an ``int`` variable (``x = 7 / 2``), a complex result such as
  ``(-8) ** 0.5`` (now the kind ``complex_result``) and, at construction, an
  invalid ``initial_vars`` or initializer value.
- ``cbrt`` is computed identically everywhere and is exact on perfect cubes:
  ``cbrt(1000)`` is ``10.0``, where the previous release returned
  ``9.999999999999998`` on a Linux build whose platform cube root is not
  correctly rounded.
- ``sign`` of NaN is ``-1`` in every runtime.

Generated Python runtime: ``**`` follows the catalog (a signed literal base
makes ``-2 ** 2`` equal ``4``, and a complex result is a runtime error), ``cbrt``
and ``sign`` match the simulator, and a math domain error carries the same
message on every supported Python version.

Generated C-family runtimes (``c``, ``c_poll``, ``cpp``, ``cpp_poll``) used to
differ from the simulator and now follow it. A model whose values reach one of
these cases changes behavior:

- ``round`` breaks ties to the even neighbour, as Python does
  (``round(2.5)`` is ``2``). C's ``round`` broke ties away from zero.
- A negative shift count is a runtime error. It used to be undefined behavior
  in C and produced an arbitrary value.
- ``%`` is floored, so the result takes the sign of the divisor
  (``-7 % 2`` is ``1``). Integer ``%`` used the C truncating operator and float
  ``%`` used ``fmod``.
- An integer ``**`` with a non-negative integer exponent is exact instead of
  going through ``pow``.
- Math functions outside their domain, a negative base with a fractional
  exponent, and a NaN or infinite value written to an ``int`` variable are
  runtime errors with the simulator's wording, where the generated code used to
  produce NaN or an infinity. The consequent of ``=>`` is only checked when its
  premise holds.
- ``W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE`` now explains its three input
  shapes separately: a negative count fails at runtime in every generated
  runtime, an integer count at or above the C/C++ width is a C/C++ portability
  risk, and a non-integer count is rejected by the operand type check.

Compatibility: Event and Guard on One Transition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A transition triggers on an event **or** a guard, never both on one edge
(`issue #515 <https://github.com/HansBug/pyfcstm/issues/515>`_). The DSL grammar
already refused to write them together; the rule now also holds for the objects
that Python code builds.

- ``Transition.event`` and ``Transition.guard`` of the model, and ``event_id``
  and ``condition_expr`` of ``TransitionDefinition`` and
  ``ForceTransitionDefinition``, raise ``ValueError`` (``event and guard are
  mutually exclusive``) when a construction or an assignment would leave both
  non-``None``. The rejected assignment changes nothing. Both may be ``None``
  for an unconditional edge.
- To migrate code that set both, clear the existing field first and then set
  the other one, or express the two terms as a combo trigger,
  ``A -> B :: Go + [x > 0];``, which expands into separate edges. Models that
  come from DSL text are not affected.

Execution Traces and Candidate Diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two opt-in views of one ``SimulationRuntime.cycle`` call. Neither writes a file
or changes what the call does.

- ``cycle(trace=True)`` returns the committed execution as
  ``CycleResult.trace``, a tuple of ``ExecutionTraceEntry`` objects in execution
  order. Each entry has a ``kind`` (``state_enter``, ``state_exit``,
  ``transition`` or ``action``), the state path, the persistent variables at
  that point, and the transition label or the action address. Rejected
  candidates and rolled-back Delta attempts are not in it. ``print(entry)``
  gives a one-line summary and ``entry.to_dict()`` a JSON-ready dictionary.
- ``cycle(diagnostics=True)`` returns ``CycleResult.diagnostics``, a
  ``CycleDiagnostics`` that records every candidate the runtime considered:
  whether its event was present, its guard result, whether its successor could
  be validated, which earlier selection blocked it, and whether it finally
  committed, with the values it saw and its source position. ``str(report)``
  explains the cycle in text, ``report.to_text(transition=..., check_id=...)``
  narrows it to one transition, and ``report.to_dict()`` is a detached
  dictionary. It answers why a transition that looked enabled was not taken.
- ``pyfcstm simulate`` exposes it with ``--diagnostics``, ``--diagnostics-format
  text|jsonl`` (JSONL needs ``-e`` and prints one report per cycle on standard
  output), and the REPL commands ``decisions`` and ``why <id|label>``.
- Compatibility: a failing command in a ``pyfcstm simulate -e`` batch
  (an unknown event, a bad ``init``, a runtime failure) now stops the batch and
  makes the process exit with a nonzero status. It printed the message and
  exited with 0 before. A rejected candidate or a Delta is not a failure.

The fields and commands are in :doc:`/reference/simulation/diagnostics`; the
task guide is :doc:`/how_to/simulation/diagnostics`.

Delta Cycles and Same-Cycle Loops
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- A cycle whose chosen path cannot reach a stoppable state or termination, but
  is a stable no-progress boundary, now ends as a successful **Delta** cycle
  instead of an error: the position and the variables stay, the cycle count
  and the input sources advance, and ``CycleResult.delta`` is ``True``. History
  entries gain a boolean ``delta``, and ``export`` to CSV adds a ``delta``
  column after ``state``. The generated runtimes expose the same through
  ``last_cycle_was_delta``.
- A loop through initial transitions, pseudo states and parent continuations
  that never reaches a state where the cycle can stop is not a Delta cycle. It
  raises ``SimulationRuntimeDfsError`` that names the states of the loop and
  how to break it. A nested loop of this kind used to end in Python's
  ``RecursionError``. A candidate that only leads back to its own start
  is skipped when a later candidate can rest, so a root with
  ``[*] -> P; [*] -> Ready; P -> P;`` now starts in ``Ready``.
- ``pyfcstm inspect`` reports a closed same-cycle routing component of this kind
  as the warning ``W_INITIAL_LIVELOCK``.

Inspect and Diagnostics
~~~~~~~~~~~~~~~~~~~~~~~

- ``W_DEADLOCK_LEAF`` is now ``W_LEAF_NO_OUTGOING_TRANSITION``. The old name
  stays in ``CODE_REGISTRY`` as a deprecated alias, is no longer emitted, and is
  scheduled for removal in 1.0.0. Scripts that match the code in JSON or LLM
  reports should match the new name, or call ``canonicalize_diagnostic_code``.
- ``pyfcstm inspect --collect-errors`` reports every model error instead of
  stopping at the first one, and still exits with a nonzero status. The loaders
  accept ``load_state_machine_from_text(text, collect=True)`` and
  ``load_state_machine_from_file(path, collect=True)``, and
  ``inspect_model(model, model_diagnostics=...)`` takes the collected
  diagnostics. Parse errors are still reported one at a time.
- The default ``inspect`` run, and ``inspect_model`` on a model loaded the normal
  way, now include the warnings that model building produces, such as
  ``W_COMBO_RESERVED_PREFIX_STATE_KIND``. They used to appear only with
  ``--collect-errors``.
- The JSON and LLM inspect payloads, and the BMC JSON, carry no
  ``schema_version`` or ``schema_status`` field; the schema file shipped with the
  release is the contract. Consumers that read those fields from earlier builds
  must stop doing so.

Bounded Model Checking and Variable Roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``pyfcstm bmc`` and :mod:`pyfcstm.bmc` understand the four variable roles
(``control``, ``input``, ``param`` and ``output``), report runtime errors that
are reachable within the bound, tell an empty scenario apart from a property
verdict, and can explain why a scenario is empty. The full contracts are in
:doc:`/reference/bmc_query/index` and :doc:`/reference/bmc_results/index`; the
tasks are in :doc:`/how_to/bmc/index`.

**Variable roles in queries and witnesses.**

- A variable is named in a query with the same bare name or ``var("name")``
  as before; the role decides how long its value lives. ``control`` and
  ``output`` variables have a value in every frame ``0..N``, and a cycle that
  does not write one keeps the preceding value. A ``param`` has one value for
  the whole trace: its default fixes it, and an initial ``havoc`` allows a
  different value that is still the same in every frame. An ``input`` is sampled
  once per step ``0..N-1``, with an independent value in every step and no
  implicit equality between steps.
- An ``assume`` that mentions an input ranges over steps: ``assume at N`` is
  rejected, because there is no step ``N``, and ``assume always`` covers ``N``
  steps. An ``assume`` without inputs still ranges over frames ``0..N``.
  ``havoc`` and ``init ... where`` reject an input, and frame predicates of the
  property cannot read one; keep an observed sample in a ``control`` or
  ``output`` variable to compare it across frames. ``havoc *`` covers control,
  output and parameter variables.
- The JSON witness records what the solver chose: ``initial.parameters`` holds
  the complete parameter values, and every step that is not an absorb step has
  ``inputs`` (the complete numeric sample, in declaration order, including
  inputs nobody read) and ``input_reads`` (the inputs that a guard or an
  assumption read, in order). ``frames[*].vars`` and the ``snapshot`` of an
  abstract call now hold only ``control`` and ``output`` values. Replay feeds
  the recorded parameters and inputs back to ``SimulationRuntime`` and reports a
  mismatch for any input or parameter that differs; it never fills a missing one
  with zero.
- ``called(...)`` filters match ``active_leaf`` and ``named_ref`` as follows: the
  path is the active leaf where one exists, and otherwise the host state of the
  action, so entering or leaving a composite state, or running a plain
  ``during`` declared on one, matches the host path. ``named_ref`` matches the
  call site's own named ``ref``; a call that only passes through a named action
  on its way matches ``named_ref=null``.

**Runtime errors within the bound.** ``pyfcstm bmc`` now first asks whether some
admissible execution reaches an operation the runtime rejects: division or
modulo by zero, a math domain error, a complex result of ``**``, or an ``int``
variable assigned a non-integral or non-finite value. Every guard and every
action block counts, in the order the simulator evaluates them. When such an
execution exists, the report headline is ``RUNTIME ERROR REACHABLE WITHIN BOUND;
PROPERTY NOT EVALUATED``, the property is not evaluated, and the command exits
with status ``5``. The witness is the prefix of the execution up to the failing
step, with the error kind and location; replay must reproduce an error of the
same kind at the same step, and a different result is a replay mismatch (status
``4``). When the check cannot decide within the budget, the headline is
``RUNTIME SAFETY CHECK UNKNOWN`` or ``TIMED OUT`` and the status is ``3``.
``--no-runtime-safety`` skips the check and evaluates the property over the
executions that raise no error; ``--runtime-safety`` is the default. The check
always runs on the model without ``--cone-slicing``. Python callers pass
``runtime_safety=False`` to :func:`pyfcstm.bmc.solve_bmc_property`, or use
:func:`pyfcstm.bmc.check_runtime_safety` directly. In JSON,
``result.outcome`` is ``runtime_error``, ``runtime_safety_unknown`` or
``runtime_safety_timeout``, and ``result.runtime_safety`` is ``null`` when the
check was switched off, otherwise it has ``status`` (``safe``, ``violated``,
``unknown``, ``timeout`` or ``not_applicable``), ``sites``, ``elapsed_ms``,
``reason`` and, for a violation, ``error`` with ``step``, ``kind`` and
``location``. The kinds are the ones of the operator catalog, for example
``division_by_zero``, ``math_domain`` and ``writeback_non_integral``.

**Empty scenarios.** When the objective of a property is unsatisfiable, the
command now checks whether the admissible scenario itself, that is the model
transition relation, the ``init`` clause and the ``assume`` clauses, has any
execution. If it has none, the result is ``scenario_infeasible``:
``property_satisfied`` is ``null``, no witness is produced, the headline is
``SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED`` and the status is ``3``. An
empty scenario used to be reported as a bounded guarantee for a counterexample
search and as a missing witness for a reach search. The report names the first
stage at which the scenario became empty (kernel, initialization or
assumptions) and ``result.feasibility`` carries the same evidence; a feasibility
check that times out or is undecided is reported as such and never as an empty
scenario. The headline of every result now says what kind of evidence it is, for
example ``PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``, ``PROPERTY DOES NOT HOLD
WITHIN BOUND; COUNTEREXAMPLE FOUND``, ``GOAL UNREALIZABLE WITHIN BOUND; NO
WITNESS`` or ``PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE``, and the
report adds ``Scenario``, ``Property verdict``, ``Semantic interpretation`` and
``Conclusion`` lines. These are bounded statements, not unbounded theorems.

**Explaining an empty scenario.** ``--explain-infeasibility none|formal|proof``
(default ``none``, which costs no extra solver work) adds an explanation to an
empty-scenario result. ``formal`` classifies the conflict and publishes a
source core: the authored FCSTM and FBMCQ constraints (with file positions and
source text) that are enough to make the scenario empty, shrunk to a
subset-minimal core when the budget allows. The classification is one of
``kernel_conflict``, ``initialization_self_conflict``,
``initialization_domain_conflict``, ``initialization_kernel_conflict``,
``assumptions_self_conflict``, ``assumptions_domain_conflict`` and
``assumptions_prefix_conflict``. ``proof`` additionally builds a step-by-step
proof, reads it as numbered sentences under ``Why no execution exists``, and
prints a ``Proof strength`` block. The proof is published only when every step
has been checked: input steps against the constraint they restate, and derived
steps by a separate checker or by the solver. The rules form a closed catalog of
twelve ``rule_id`` values (``source_fact``, ``case_condition_entailment``,
``transition_assignment``, ``equality_substitution``, ``arithmetic_evaluation``,
``interval_intersection``, ``state_domain_exhaustion``,
``definedness_failure``, ``incompatible_equalities``, ``boolean_complement``,
``excluded_state_selected`` and ``preceding_value_entailment``). When no rule
closes the core, the result falls back to ``formal`` instead of publishing an
unchecked proof, and the report says ``Explanation depth: requested proof,
achieved formal``; compare ``requested_mode`` with ``achieved_mode`` in JSON.
The explanation never changes the verdict. Python callers pass
``infeasibility_explanation='formal'`` or ``'proof'`` to
:func:`pyfcstm.bmc.solve_bmc_property`.

**Solver options.**

- ``--cone-slicing`` (off by default) removes writes to variables that the query
  does not observe, but only integer writes whose evaluation cannot fail, and it
  keeps control flow, initial values and everything partial arithmetic depends
  on. The witness still contains every variable and still passes replay. When
  slicing does nothing, ``result.cone_slicing.skipped_reason`` says so
  (``abstract_actions`` or ``no_removable_variables``); without the flag the
  field is absent. In the recorded benchmark the aggregate effect on solve time
  was under one percent and some queries became slower, so measure your own
  model. Python
  callers use ``BmcOptions(cone_slicing=True)``.
- ``--solver-profile default|logic|tactic`` chooses the main solver.
  ``logic`` picks a Z3 logic from the formula (``QF_LIA``, ``QF_LRA``,
  ``QF_LIRA``, ``QF_NIA``, ``QF_NRA`` or ``NIRA``) and falls back to the generic
  solver when none matches; ``tactic`` runs ``simplify``, ``propagate-values``,
  ``solve-eqs`` and ``smt``. A profile does not change the meaning of a result,
  but it can change which witness is found and how long the solve takes, and the
  witness still has to pass replay. The explanation and proof checks always use
  the default solver. In the recorded comparison neither optional profile met the
  adoption criteria, so ``default`` stays the default. The result reports
  ``solver_profile``, ``solver_logic`` and ``solver_statistics``. Python callers
  use ``solver_profile=`` of :func:`pyfcstm.bmc.solve_bmc_property`.
- ``--timeout-ms`` is now one budget shared by every solver check of the run
  (runtime safety, feasibility, explanation, the primary check and the response
  suffix check). It used to apply to each check separately. A check that cannot
  start because the budget is spent is reported as not checked, not as an
  empty scenario.

**Result changes.** The JSON result has these changes relative to the previous
release; validate against the schema file shipped with the release you run.

- ``exit_code`` may be ``5``. Process exit statuses are ``0`` (property holds),
  ``1`` (property does not hold), ``3`` (inconclusive, empty scenario, or an
  undecided safety or feasibility check), ``4`` (replay mismatch) and ``5``
  (reachable runtime error); the priority is ``4``, ``5``, ``3``, then ``0`` or
  ``1``.
- ``result.outcome`` gains ``scenario_infeasible``, ``feasibility_timeout``,
  ``feasibility_unknown``, ``runtime_error``, ``runtime_safety_unknown`` and
  ``runtime_safety_timeout``. ``result`` gains ``feasibility`` (which carries
  ``explanation``), ``available_model_roles``, ``total_elapsed_ms``,
  ``solver_profile``, ``solver_logic``, ``solver_statistics``,
  ``runtime_safety`` and, only when slicing was requested, ``cone_slicing``.
- ``witness`` and ``replay`` are now bound to the role of the model they
  describe. ``witness`` carries ``model_role`` (``primary_witness``,
  ``primary_counterexample``, ``incomplete_suffix`` or
  ``runtime_error_prefix``) and a ``verdict`` object; an ``incomplete_suffix``
  trace is finite-prefix evidence and never a property verdict. ``replay``
  carries the same role. The new Python function
  :func:`pyfcstm.bmc.decode_bmc_result_trace` decodes the model of a solve
  result in this shape, while :func:`pyfcstm.bmc.decode_bmc_witness` keeps its
  previous output shape.
- Steps gain ``inputs`` and ``input_reads``, and the initial record gains
  ``parameters``, as described above.

**Migration.** Scripts that read the first line of the human report must be
updated to the new headlines, or better, read ``--json``. Callers that
relied on ``--timeout-ms`` being per check should raise it for the whole run.
A model that can divide by zero, take a square root of a negative number or
write a fractional value into an ``int`` variable on an admissible path now
exits with status ``5`` until the operation is guarded or the inputs are
constrained; pass ``--no-runtime-safety`` to restore the earlier behavior.
Consumers that validated JSON against the previous schema copy must use the
copy shipped with this release.

Input Parameters and Sampled Inputs in Built-In Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A model that declares ``param`` or ``input`` variables now generates a runtime
with a matching public interface in all five built-in templates, and the
generated ``README`` guides teach it. Models without those declarations
generate the same interface as before apart from the text changes described in
the previous sections. ``param`` values are fixed per instance; ``input`` values
are sampled once per cycle, are read-only to the model and are not held between
cycles. ``vars`` and ``Vars`` hold only ``control`` and ``output`` variables.
Templates written by hand can read the declarations through
``model.parameters``, ``model.inputs``, ``model.persistent_variables``,
``model.control_variables`` and ``model.output_variables``.

- ``python``: ``Machine(initial_state=None, initial_vars=None, *,
  parameters=None)`` validates and copies ``parameters``; an omitted parameter
  uses its DSL default in a cold start, and a hot start needs all of them.
  Implement ``read_<input>()`` to supply a sample; the runtime reads every input
  once per cycle, including inputs the chosen path does not use, and freezes
  the sample for validation and execution. ``cycle(events=None, *, inputs=None)``
  supplies explicit values for some or all inputs and reads the others through
  their hooks. An unimplemented reader raises ``NotImplementedError``. Read
  ``get_param_<name>()`` and, during a cycle, ``get_input_<name>()``;
  ``parameters`` and ``last_inputs`` expose the fixed values and the last
  committed sample, and the context of an abstract action carries ``vars``,
  ``inputs`` and ``parameters`` as separate read-only mappings. An ``int`` input
  or parameter accepts an integral ``float`` and stores it as an ``int``, like
  the simulator. A failed read or a failed cycle leaves persistent values and
  ``last_inputs`` unchanged.
- ``c`` and ``c_poll``: ``<Prefix>InitOptions`` carries ``vars``, ``parameters``
  and a presence flag for each value (a zero flag means the DSL default), and
  ``<Prefix>_init_with_options(machine, &options)`` starts the machine. Inputs
  are supplied through ``<Prefix>InputProvider``, one ``read_<input>`` callback
  per input, registered with ``<Prefix>_set_input_provider``, or as a complete
  ``<Prefix>Inputs`` value through ``<Prefix>_cycle_with_inputs`` (``c_poll``
  passes no event ids there). A callback
  returns ``1`` after writing a value and ``0`` to abort the cycle; a missing
  provider, a non-finite value or a callback that fails makes the cycle fail
  without committing. ``<Prefix>_get_param_<name>``, ``..._get_input_<name>``
  and ``<Prefix>_last_inputs`` read the values, and
  ``<Prefix>_hot_start_with_parameters`` restores a complete parameter set.
- ``cpp`` and ``cpp_poll``: the wrappers expose the same through
  ``MachineWrapper(const InitOptions &)``, ``init``, ``set_input_provider``,
  ``cycle_with_inputs(inputs, ids, count)`` (``cycle_with_inputs(inputs)`` for
  ``cpp_poll``), ``last_inputs``, ``get_param_<name>`` and
  ``get_input_<name>``. The callbacks keep their C signatures.

Operator Semantics in Generated Runtimes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simulator, the generated runtimes, ``inspect``, the verifier and BMC now
evaluate FCSTM operations from one operator catalog,
:mod:`pyfcstm.semantics.catalog`. The table *Evaluation and runtime errors* in
:doc:`/reference/dsl/index` lists the result and the error kind of every
operator and function. What changes for generated code:

- The C-family templates (``c``, ``c_poll``, ``cpp``, ``cpp_poll``) computed some
  operators differently from the simulator, with no diagnostic. They now follow
  it: ``%`` is a floored modulo whose result takes the sign of the divisor
  (``-7 % 2`` is ``1``), for integers and floats; ``**`` of an ``int`` base and
  a non-negative ``int`` exponent is an exact integer power, where it used to go
  through ``double`` and lose low bits beyond 53 bits (``3 ** 34`` was off by
  one); a zero base with a negative exponent fails when evaluated; ``cbrt`` is
  the real cube root, exact on perfect cubes; ``floor``, ``ceil``, ``trunc`` and
  ``round`` of NaN or of a value outside the ``int64`` range fail instead of
  producing a cast artifact; and an ``int`` variable that is assigned NaN or
  infinity fails with a "must be finite" message.
- The generated Python runtime rejects a ``**`` with a complex result, treats
  ``-2 ** 2`` as ``4`` like the simulator, computes ``cbrt`` exactly on perfect
  cubes on every supported Python version, returns ``-1`` for ``sign`` of NaN,
  and reports math domain errors with the same message on every Python version
  instead of the wording of the host interpreter.
- A rejected writeback (a non-integral or non-finite value assigned to an
  ``int`` variable) is now a ``SimulationRuntimeExpressionError`` in the
  simulator and in the generated Python runtime, including for ``initial_vars``
  and default initializers, rather than a bare ``ValueError``. In the simulator
  the exception has a ``kind`` attribute with the catalog error kind, for
  example ``writeback_non_integral``.
- In the simulator and in BMC, ``=>`` evaluates its right operand only when the
  left operand holds, so ``d != 0 => 10 / d > 1`` never divides by zero.

Command Line
~~~~~~~~~~~~

- ``pyfcstm bmc`` gains ``--cone-slicing``, ``--runtime-safety`` /
  ``--no-runtime-safety``, ``--solver-profile`` and ``--explain-infeasibility``,
  and exits with status ``5`` for a reachable runtime error, as described above.
  Its help text and the option table are in :doc:`/reference/cli/index`.
- ``pyfcstm simulate`` gains ``--param NAME=VALUE`` (repeatable) to set
  construction parameters. In the REPL and in ``-e`` batches, ``cycle`` takes
  ``--input name=value`` once per input to supply the sample of that cycle; a
  model with ``input`` variables needs a value for every input.
  ``--diagnostics`` records, for every cycle, the candidate transitions that were
  checked and rejected; ``decisions [--verbose]`` and ``why <id|label>
  [--verbose]`` query the latest report. ``--diagnostics-format jsonl`` writes
  each report as one JSON line on standard output and needs both
  ``--diagnostics`` and ``-e``; the transcript and the query output then go to
  standard error. Python callers pass ``diagnostics=True`` to
  ``SimulationRuntime.cycle`` and read ``result.diagnostics``. See
  :doc:`/reference/simulation/diagnostics` and
  :doc:`/reference/simulation/inputs`.
- ``pyfcstm inspect`` gains ``--collect-errors``, which reports every model error
  instead of stopping at the first one and still exits non-zero for an invalid
  model. The Python counterparts are ``collect=True`` of
  ``load_state_machine_from_file`` and ``load_state_machine_from_text``, and the
  ``model_diagnostics`` argument of ``inspect_model``. A model that builds
  successfully now reports the warnings produced while it was converted, such as
  ``W_HISTORY_UNUSED``, ``W_HISTORY_RESERVED_PREFIX``,
  ``W_COMBO_RESERVED_PREFIX_STATE_KIND`` and
  ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``, in the default report; before, they
  appeared only with ``--collect-errors``.
- ``pyfcstm --self-check`` runs installation and runtime checks of the installed
  wheel or standalone executable and reports missing packaged resources,
  unavailable dependencies and platform problems. ``pyfcstm --self-check --help``
  lists its options (``--profile``, ``--format``, ``--report``, ``--color``,
  ``--timeout-scale``, ``--fail-on-warn`` and others). It is a deployment
  diagnostic, not a replacement for the test suite.

Inspect Reports
~~~~~~~~~~~~~~~

- Added the descriptive ``summary.structure_statistics`` section to the LLM
  report and ``ModelInspect.structure_statistics`` to the full report. The rates
  are raw fractions, use ``null`` for empty denominators, and record
  conservative advisory defaults for transition density and unreachable
  populations. The canonical ``W_UNREACHABLE_TRANSITION`` warning aggregates the
  reason buckets once per authored transition; thresholds remain metadata only
  and do not create a health score. Python callers and the CLI can override or
  disable the thresholds.
- Added ``ModelInspect.verification`` execution metadata to the full JSON/API
  report. Consumers can distinguish disabled verification, policy-excluded
  algorithms, definite results, and indeterminate outcomes without treating any
  of those states as new model diagnostics. The human CLI shows compact coverage
  and indeterminate reasons.

Diagram Snapshots and Viewer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The editors could already draw a model in their preview; this release gives
the Python package the same drawing. Nothing under ``pyfcstm.diagram`` or
``pyfcstm diagram`` existed in v0.6.0. The reference is
:doc:`/reference/visualization_options/index` and the reasons are in
:doc:`/explanations/visualization/index`.

- ``StateMachine.diagram()`` returns a :class:`pyfcstm.diagram.api.Diagram`, an
  immutable snapshot that is detached from the model: editing the model
  afterwards cannot change what an already saved view shows, and assigning to
  an attribute is refused. ``with_options()`` and ``with_view_state()`` return
  new snapshots instead of changing this one.
- ``to_dict()`` and ``to_json()`` give deterministic portable data and need no
  optional runtime. ``to_html()`` writes a single self-contained viewer with
  the renderer, the layout engine, the rasteriser and the CJK fonts embedded,
  under a strict inline content policy and without any network access. A
  viewer is roughly 29 MB (29,397,900 bytes for ``state Root;`` loaded from
  text; the number moves with the model). ``save(path)`` picks JSON, HTML, SVG,
  PNG or PDF from the suffix, or from ``format=``. ``show()`` opens the viewer
  in a Chromium-family app window, blocks until the window closes, like
  ``matplotlib.pyplot.show``, and then removes the temporary document it wrote
  unless you passed ``output``.
- The viewer has three modes (source only, diagram only, and a linked split
  view), collapse, zoom and pan. When the model was loaded from text or a
  file, the source pane is embedded and linked to the diagram; a model built
  in Python has no source ranges and the viewer says so instead of showing an
  empty pane.
- :class:`pyfcstm.diagram.api.DiagramOptions` holds ``detail_level``
  (``minimal``, ``normal`` or ``full``), ``direction`` (``TB`` or ``LR``),
  ``palette``, ``mode`` (``light``, ``dark`` or ``auto``) and ``cjk_locale``
  (``sc``, ``tc``, ``hk``, ``jp`` or ``kr``).
  :class:`pyfcstm.diagram.api.DiagramViewState` holds the viewer mode, the
  collapsed state ids, the zoom and the pan. Both accept a mapping, and an
  unknown key is refused.
- The detail level changes what is drawn, not what the data contains. At
  ``minimal`` a state shows its title and the transitions, with effects written
  inline; ``normal`` puts effects into notes and tints edges by event; ``full``
  adds the events and lifecycle actions of a leaf state under its title. The
  standalone viewer, the SVG, PNG and PDF exports and the VS Code preview share
  one renderer, so they agree.
- ``pyfcstm diagram -i machine.fcstm`` prints the portable JSON.
  ``-o viewer.html`` writes the viewer, ``--open`` opens it in a window and
  prints a path only when ``-o`` kept the document, and ``-o`` with an ``.svg``,
  ``.png`` or ``.pdf`` suffix (or ``--format``) writes an export. ``--scale``
  applies to PNG only. Input and output problems are reported as command-line
  errors, not tracebacks. The commands are listed in :doc:`/reference/cli/index`.
- A ``Diagram`` shows its SVG in a notebook cell when the rendering runtime is
  installed, and falls back to the plain representation when it is not.

Diagram Export and Editor Preview
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``to_svg()``, ``to_png(scale=...)`` and ``to_pdf()`` export synchronously. They
  need the optional rendering runtime, installed with ``pip install
  pyfcstm[viz]`` (``mini-racer`` on Python 3.8 and later, ``py-mini-racer``
  below 0.7 on Python 3.7); without it they raise
  :class:`pyfcstm.diagram.engine.DiagramUnavailableError` that names the
  dependency. The SVG is the expanded form: glyphs and arrowheads are already
  paths, so it renders the same where none of this project's fonts are
  installed. The PDF is a single-page vector document whose text is outlines,
  so it is not searchable.
- Exports are bounded and refused before rendering with
  :class:`pyfcstm.diagram.engine.DiagramRenderLimitError`: a PNG scale of at
  most 4, an edge of at most 16,384 pixels, at most 16,777,216 pixels, a PNG of
  at most 33,554,432 bytes and an SVG or PDF of at most 67,108,864 bytes.
- ``pyfcstm expand-svg -i canonical.svg [-o expanded.svg]`` converts a canonical
  diagram SVG, which names its fonts, into the self-contained one, and prints
  to standard output without ``-o``. It exists so that a host that holds a
  drawing but no fonts can outline it without re-rendering from the source,
  which would lose the palette and colour mode the user chose.
- The VS Code preview uses it for its SVG download: the extension asks an
  installed ``pyfcstm[viz]`` to outline the text, because bundling the fonts and
  the rasteriser would add roughly 17.7 MB for one CJK locale and 59.4 MB for
  all of them. The new setting ``fcstm.diagram.pyfcstmPath`` names the command
  to use; empty means to try ``pyfcstm``, ``python3 -m pyfcstm`` and ``python -m
  pyfcstm`` in that order. When nothing usable is installed, the export says so
  instead of handing over a file that depends on the reader's fonts.

Self-Check
~~~~~~~~~~

``pyfcstm --self-check`` (also ``python -m pyfcstm --self-check``) is new. It
diagnoses an installed package or a standalone executable in the environment it
runs in: imports, packaged resources, runtime dependencies, platform
compatibility and the optional visualization services (Java and PlantUML). It
is not a second test suite, and a failure points at the deployment, not at the
implementation.

- Checks run in isolated worker processes, so a crash or a hang in one is
  reported and does not stop the others. ``--profile default|full|visualize``
  selects the checks, ``--network`` enables the remote probes and is accepted
  only with ``--profile visualize``, ``--format human|json`` chooses the report,
  ``--report PATH`` names a report file,
  ``--color auto|always|never`` and ``--timeout-scale`` tune the output and the
  time limits, and ``--no-redact`` keeps local paths in the environment
  metadata, which are redacted by default.
- The exit code is ``1`` when a required check fails, and also when one warns
  if ``--fail-on-warn`` is given; otherwise it is ``0``. A missing optional
  Java or PlantUML is a warning.
- ``pyfcstm --version`` now also prints the build revision, the Python version
  and the platform. It is answered before the command line framework is
  imported, so a damaged optional dependency does not hide it. A script that
  parsed the two-line output of v0.6.0 should read the first line only.

Installation and Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The supported Python range is unchanged: ``python_requires`` is ``>=3.7``
  and the test matrix covers CPython 3.7 through 3.14. The minimum VS Code is
  still ``^1.60.0`` and ``jsfcstm`` still declares Node ``>=16``.
- ``requirements.txt`` raises or adds these runtime dependencies:
  ``jinja2>=3.1.6`` (was ``>=3``; the floor that takes the Jinja2 security
  fixes and still supports Python 3.7), ``deprecation>=2.1.0`` and
  ``packaging>=21.3`` (new). It also pins ``lxml``, which ``plantumlcli``
  pulls in through ``pyquery``, to ``>=4.9,<6.1`` on Python 3.7 and 3.8 and to
  ``>=6.1`` on Python 3.9 and later, so each version has wheels on Windows.
  ``z3-solver<=4.15.4`` is unchanged.
- The wheel now carries the diagram runtime assets under
  ``pyfcstm/diagram/assets``: the renderer, the viewer bundle, the resvg
  WebAssembly module, three JetBrains Mono faces and regular and bold Noto Sans
  faces for each of five CJK locales, with their licences. This enlarges the
  installed package. The assets are build products and are not tracked in the
  repository: a source checkout needs ``make build_assets`` (which runs
  ``npm ci``) before ``pip install`` or ``python setup.py build``, and
  ``setup.py`` stops with that instruction when they are missing.
- A new extra, ``pip install pyfcstm[viz]``, installs the MiniRacer runtime
  that SVG, PNG and PDF export need. The viewer, ``to_dict()``, ``to_json()`` and
  ``to_html()`` do not need it.
- The diagnostic code registry can now mark a code as a deprecated alias with
  the version that deprecated it and the version that removes it; see
  *Upgrading from 0.6.0*.

Documentation and LLM Guides
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Examples on documentation pages now show a command or a script together
  with its real output, and a documentation gate (``make docs_doctest``)
  runs them and compares what they print with what the page shows. The
  region tutorial is written in this form.
- Every ``>>>`` example in a docstring of the ``pyfcstm`` package is run by
  ``make doctest``, and the gate has no list of known failures. The examples
  in the API reference are therefore examples that run.
- The two packaged LLM guides follow the language. The FCSTM grammar guide
  gained the sections *Documentation Blocks*, *Reserved Identifiers*,
  *Variable Roles*, *Import variable roles*, *History* and *Regions*, and the
  FBMCQ language guide gained *Starting a model with regions*, *Variable roles
  in assumptions* and *A model with regions*. Each guide is protected by its
  ``.sha256`` file, as before.

Upgrading from 0.6.0
~~~~~~~~~~~~~~~~~~~~

Go through this list when you move a model, a script or a downstream
integration from v0.6.0 to v0.7.0. Each line points to the section that has the
details.

- **Names.** ``region`` and ``active`` are reserved words, and so are ``var``,
  ``control``, ``input``, ``param`` and ``output`` (the last four declare
  variable roles; the FCSTM grammar guide lists them under *Reserved
  Identifiers* and *Variable Roles*). A model that uses one of them as a state,
  event, action, variable or import alias name has to rename it, for example to
  ``Active`` or ``active_flag``. See *Regions*.
- **Forced transitions.** ``!S -> T`` with states inside ``S`` is carried out
  once, at the resting state; its four changed behaviours, the hidden
  ``__forced_<n>`` variables, the ``__forced_gate_<n>`` pseudo states, the
  changed output of ``walk_states()``, ``StateMachine.defines`` and
  ``to_ast_node()``, and the missing ``Transition.is_forced`` on the machine
  that runs mean that stored expected values need updating. See *Forced
  Transitions*.
- **Hot start of history and active() models.** ``__hist_goto`` and the
  ``__hist_*`` records are no longer checked, and the BMC constraint category
  ``domain.history_variable`` is gone. See *History and active()*.
- **Unsupported-feature code.** ``E_UNSUPPORTED_FEATURE`` no longer lists an
  ``active`` feature, the inspect reason ``active_query_unsupported`` is gone,
  and a model with regions given to a template without the ``region`` feature
  is refused with ``E_UNSUPPORTED_FEATURE``. See *Templates and capability
  declarations*.
- **Inspect reachability.** A composite state none of whose children can leave
  never takes its ordinary outgoing transitions; the state it leads to is now
  reported by ``W_UNREACHABLE_STATE`` and the transition gets the reason
  ``owner_never_completes``. See *Inspect and verify*.
- **Diagnostic code rename.** ``W_DEADLOCK_LEAF`` is now
  ``W_LEAF_NO_OUTGOING_TRANSITION``. The old spelling stays in
  ``CODE_REGISTRY`` as a deprecated alias (deprecated in 0.7.0, to be removed in
  1.0.0) and resolves through ``resolve_diagnostic_code`` and
  ``canonicalize_diagnostic_code``; new reports emit only the new spelling, so
  filters on the old code have to be updated. See
  :doc:`/reference/diagnostics_codes/index`.
- **Transition fields.** In the Python model and AST, ``Transition.event`` and
  ``Transition.guard`` (and ``event_id`` and ``condition_expr`` of the AST
  transitions) are mutually exclusive: setting both raises ``ValueError`` and
  leaves the object unchanged. Clear one field before setting the other. See
  :doc:`/reference/dsl/index`.
- **Generated Python runtime.** ``vars`` is a read-only view, the ``variables``
  alias is removed, ``ABSTRACT_HOOKS`` is a read-only mapping, and a model with
  regions has no ``current_state_path`` or ``current_state_name``. Regenerate
  the file; its text changes for models without regions as well. See
  *Templates and capability declarations*.
- **Generated C and C++ runtimes.** The machine type is opaque,
  ``MAX_STACK_DEPTH`` and ``MAX_DFS_STEPS`` are replaced by the
  ``..._ARENA_CAPACITY``, ``..._TRAIL_CAPACITY`` and ``..._STORAGE_BYTES``
  macros, and a model with regions has no ``current_state_id``,
  ``current_state_path`` or ``current_state_name``. Regenerate and rebuild;
  code size, RAM and time per cycle change. See *Templates and capability
  declarations*.
- **Simulator command line.** ``events`` and the completion of ``cycle`` list
  only short names that work, and ``init`` refuses a variable that is given
  twice. See *Simulating models with regions*.
- **Installing.** Update to ``jinja2>=3.1.6``; ``deprecation`` and ``packaging``
  are installed with the package. A source checkout needs ``make
  build_assets`` before it is built or installed. See *Installation and
  Compatibility*.
- **Version output.** ``pyfcstm --version`` prints more than two lines. See
  *Self-Check*.

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
- Added the stable ``bmc-cli/v1`` JSON envelope for CI, tools, and LLM
  consumers, with a downloadable schema in the BMC result protocol reference.
  The envelope preserves polarity-aware outcomes, solver timing, witness and
  replay records, diagnostics, and the matching process exit code.

Inspect and Diagnostics
~~~~~~~~~~~~~~~~~~~~~~~

- Changed ``pyfcstm inspect`` to default to a checker-style human report with
  aligned source spans, nearby source context, compact severity labels, and
  ``--color auto|always|never``. Files, pipes, and machine formats remain free
  of ANSI escapes.
- Kept the stable machine report under ``--format json`` and added
  ``--format llm-json`` and ``--format llm-md`` using schema
  ``pyfcstm.inspect.llm.v1``. LLM reports carry source context, provenance,
  repair guidance, and explicit do-not notes.
- Expanded static and verify-backed diagnostics, including numeric and guard
  reasoning, while keeping solver-backed inspect checks behind the existing
  explicit enablement and safety gates.
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
- Extended the shared semantic fixture corpus so the simulator and generated
  runtimes are checked against the same cycle-by-cycle state, variable, event,
  history, callback, and failure behavior.

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
