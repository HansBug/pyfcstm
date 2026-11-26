Region models and configurations
================================

This page describes Python model construction and position values. Every
consumer in the Python package takes a model with regions: the simulator
(cold and hot start) and ``pyfcstm simulate``, ``pyfcstm inspect`` and the
structural analyses of ``pyfcstm.verify``, bounded model checking and
``pyfcstm bmc``, PlantUML export, ``StateMachine.diagram()`` and
``pyfcstm diagram``, and code generation with the built-in ``python``, ``c``,
``c_poll``, ``cpp`` and ``cpp_poll`` templates. The one refusal that remains is
a template that does not list ``region`` under ``features`` in its
``config.yaml``: ``pyfcstm generate`` stops with ``E_UNSUPPORTED_FEATURE``
before it writes a file (see :doc:`../template_config/index`). Activity queries
are never refused: the model lowers ``active()`` into ordinary hidden
variables. The JavaScript frontend (model, semantic analysis and diagram
preview) supports regions and activity queries; its ``inspectModel`` function
builds no report for a model with regions.

Namespaces and structure
------------------------

``State.regions`` is a declaration-ordered dictionary of ``Region`` objects.
A state owns either direct substates or direct regions, never both. A region
contains ordinary states, local transitions and events, and during aspects.
It cannot directly contain imports or another region, own state lifecycle actions,
or serve as a transition endpoint. Nest parallel structure through a child state.
Each region must contain a state and at least one valid initial transition.

An owner with regions may have its own lifecycle actions and during aspects;
transitions belong inside its regions. Imports belong inside ordinary child
states, not directly inside a region or its owner.
One region is valid and is not itself a warning. History may remain inside an
ordinary state subtree within a region; a history owner whose subtree contains
regions is rejected because a single saved leaf cannot represent that position.

Paths include region names: ``Root.Job.Worker.Idle``. ``State.parent`` returns
the immediate namespace, which can be a ``State`` or ``Region``; ``Region.parent``
returns its owner state. ``walk_states()`` visits only states, including those
inside regions; ``walk_regions()`` visits regions in declaration order.
``StateMachine.has_regions`` reports whether any region exists.

Event and named-action paths traverse both kinds of namespace. Relative upward
steps count the region segment; absolute paths retain their root-relative
meaning. Resolution does not search ancestors for an accidentally matching
name. Imports rebase internal state, event, action-reference and activity-query
paths to the importing instance. Model nodes retain their originating file and
source span. Region-structure and activity-target diagnostics carry
``source_path``; some existing generic build diagnostics, such as a missing
initial transition, still provide a span without the originating file.

Position values
---------------

``Configuration`` describes a position without running initialization, guards
or actions. Construct it with ``Configuration.parse(model, text, mode=...)``
or ``Configuration.from_dict(model, data)``. Values are immutable and hashable;
equality compares mode and ordered paths, independently of model identity.
State objects returned by ``leaves`` belong to the model used for construction.

.. list-table:: Validation modes
   :header-rows: 1
   :widths: 20 80

   * - Mode
     - Accepted positions
   * - ``stable`` (default)
     - Every live branch reaches a non-pseudo leaf; every active owner specifies
       all its regions and has at least one live region. Checked at every depth.
   * - ``initialization``
     - One whole composite/region-owning state awaiting initialization. Region
       entries may be omitted or explicitly ``[init]``; live and Done entries
       are rejected. This is not a partially specified stable configuration.
   * - ``transient``
     - Structurally valid intermediate positions, including pseudo states,
       partial region initialization and all-Done snapshots. A machine never
       rests in such a position, so ``runtime.configuration`` does not return
       one at rest. A hot start reads configuration text in this mode: a region
       that is left out waits for its initialization, and a position in which
       every region of an owner is Done is rejected at any depth.

In text, the outer state path is root-qualified. A region entry names its child
relative to that region; ``[done]`` means that region is Done and ``[init]``
means it has not initialized. Nested parallel
owners introduce another region block. Input entry order is normalized to model
declaration order. Unknown, duplicate or foreign entries are rejected. A linear
path cannot bypass a parallel owner to select only one of its regions.
``stable`` rejects ``[init]`` at every depth. In ``initialization`` and
``transient`` modes, omitted regions mean pending initialization and are shown
explicitly as ``[init]`` by ``str()``. The old configuration marker ``[*]`` is
rejected; the DSL still uses ``[*]`` for initial and final transitions.

.. code-block:: pycon

   >>> from pyfcstm.model import Configuration, load_state_machine_from_text
   >>> source = '''state Root {
   ...     region Left { state Idle; [*] -> Idle; Idle -> [*]; }
   ...     region Right { state Working; [*] -> Working; }
   ... }'''
   >>> model = load_state_machine_from_text(source)
   >>> config = Configuration.parse(model, 'Root{Right: Working, Left: [done]}')
   >>> str(config)
   'Root{Left: [done], Right: Working}'
   >>> [state.path for state in config.leaves]
   [('Root', 'Right', 'Working')]
   >>> config.is_active('Root'), config.is_active('Root.Left.Idle')
   (True, False)
   >>> config.region_status('Root.Left'), config.region_status('Root.Right')
   ('done', 'live')
   >>> Configuration.from_dict(model, config.to_dict()) == config
   True

``str(config)`` is canonical position text. ``repr(config)`` also shows the
validation mode for debugging; it is not an executable constructor expression
or accepted parser input. Reparse a non-stable value with its explicit mode:

.. code-block:: pycon

   >>> pending = Configuration.parse(model, 'Root', mode='initialization')
   >>> str(pending)
   'Root{Left: [init], Right: [init]}'
   >>> repr(pending)
   "Configuration(mode='initialization', position='Root{Left: [init], Right: [init]}')"
   >>> Configuration.parse(model, str(pending), mode=pending.mode) == pending
   True
   >>> mixed = Configuration.parse(model, 'Root{Left: [done]}', mode='transient')
   >>> str(mixed)
   'Root{Left: [done], Right: [init]}'
   >>> mixed.region_status('Root.Left'), mixed.region_status('Root.Right')
   ('done', 'pending')
   >>> Configuration.parse(model, str(mixed), mode=mixed.mode) == mixed
   True

Tokens accept surrounding whitespace, including newlines. Identifiers use
``[A-Za-z_][A-Za-z_0-9]*``; marker spelling is exact, so ``[Done]`` and
``[ init ]`` are rejected. Syntax errors raise ``ValueError`` with one-based
line and character column numbers. Tabs count as one character; newline
characters separate lines. Model errors separately identify invalid paths,
region entries or validation modes. Non-string input raises ``TypeError``.
Excessive nesting raises an informative ``ValueError`` rather than exposing
Python's ``RecursionError``; the supported depth depends on the interpreter's
available stack. Long token/path excerpts are shortened, nonprinting characters
are escaped, and unfinished input is described as ``end of input``. Applications
can catch ``ValueError`` to report invalid text without exposing a traceback.

.. code-block:: pycon

   >>> Configuration.parse(model, 'Root{\n Left: @\n}', mode='transient')
   Traceback (most recent call last):
       ...
   ValueError: Expected a configuration identifier at line 2, column 8, got '@'.

   >>> try:
   ...     Configuration.parse(model, 'Root{Left: Working', mode='transient')
   ... except ValueError as error:
   ...     # ValueError: the input is missing its closing region-block brace.
   ...     print(error)
   Expected '}' at line 1, column 19, got end of input.

``is_active`` accepts State paths, including active ancestors, but rejects
Region paths. ``region_status`` accepts Region paths and returns ``live``,
``done``, ``pending`` (active owner, region not initialized) or ``inactive``
(owner outside this configuration). ``leaves`` omits Done and pending branches.
Unknown paths raise ``ValueError``.

``to_dict()`` returns fresh JSON-compatible containers. The example above yields:

.. code-block:: json

   {
     "mode": "stable",
     "state": "Root",
     "regions": [
       {"name": "Left", "configuration": null},
       {"name": "Right", "configuration": {
         "state": "Root.Right.Working", "regions": []
       }}
     ]
   }

Nested nodes use full state paths and omit ``mode``. ``null`` means Done;
pending entries remain omitted in JSON, including an empty region list when
the whole owner awaits initialization. ``[init]`` and ``[done]`` are text
markers, not JSON string values. Omitted outer ``mode`` defaults to ``stable``. Text does not
encode the mode: pass it again when reparsing a non-stable value.

.. code-block:: pycon

   >>> pending.to_dict()
   {'mode': 'initialization', 'state': 'Root', 'regions': []}
   >>> mixed.to_dict()
   {'mode': 'transient', 'state': 'Root', 'regions': [{'name': 'Left', 'configuration': None}]}
   >>> Configuration.from_dict(model, mixed.to_dict()) == mixed
   True

Activity queries
----------------

``active("Root.Job.Worker.Idle")`` and ``active("/Job.Worker.Idle")``
select the same state in a model rooted at ``Root``. The target must exist and
be a non-pseudo State, not a Region. Queries are allowed in guards and operation
conditions, including lifecycle/aspect conditions; persistent initializers
cannot query an active position. Invalid targets produce
``E_ACTIVE_QUERY_TARGET``. ``parse_expr`` can retain an ``ActiveStateQuery``
without a model, but evaluating that unbound expression raises ``TypeError``.

Within an imported module, queries starting with that module's root name or
``/`` are rebased to the instance. An explicitly named host-root path is bound
against the assembled model; such a module depends on that host path existing.

Model construction binds queries and lowers each distinct target to an integer
activity flag. ``StateMachine.active_queries`` exposes ``ActiveQuery`` records
with ``state_path`` and ``variable_name``. Names avoid persistent variables and
block-local temporaries;
consumers should use the records rather than guess generated names. Anonymous
enter/exit actions maintain flags without modifying named action bodies.
``model.active_variables(config)`` derives the flag values for a configuration
constructed against that exact model; it does not execute any actions.

.. code-block:: pycon

   >>> model = load_state_machine_from_text('state Root { during { if [active("Root")] {} } }')
   >>> config = Configuration.parse(model, 'Root')
   >>> query, = model.active_queries
   >>> query.state_path, model.active_variables(config)[query.variable_name]
   (('Root',), 1)

``to_ast_node()`` exports the current model, including lowering. It must not be
treated as a lossless source-text roundtrip. Configuration JSON is a separate
value contract; it does not add fields to public inspect or BMC reports.

.. _region-limits-and-gaps:

Limits and known gaps
---------------------

The table lists every limit and known gap that touches models with regions. A
number appears only where a real run produced it: ``region_limits.demo.py`` next
to this page reproduces the limits and the checked gaps, and its output follows
the table. A row whose last column says *recorded* describes a gap taken from
its issue and not re-run for this page.

.. list-table:: Limits and known gaps of models with regions
   :header-rows: 1
   :widths: 24 30 26 20

   * - Limit or gap
     - Value or behavior
     - Source
     - Documented in
   * - Owners entered inside one another within one cycle
     - At most 64 levels. The 65th raises ``SimulationRuntimeDfsError`` (``Group
       initialization nested deeper than the structural safety limit (64) within
       one cycle``); 64 nested owners run. The same limit applies to a loop that
       re-enters a group more than about 64 times in one cycle. The model itself
       builds at any depth.
     - ``_DFS_STRUCTURAL_DEPTH_LIMIT`` in ``pyfcstm/simulate/runtime.py``; the
       generated Python runtime and the C kernel carry the same constants;
       fixture ``region_unbounded_group_reentry_is_reported_as_a_safety_limit_error``.
     - :ref:`region-limits-run`, :doc:`../simulation/index`
   * - Steps in one cycle
     - At most 1000 speculative steps. A pseudo state that turns 500 times in one
       cycle raises ``Speculative DFS exceeded the step safety limit (1000)``.
       The cost of validating a long chain grows faster than its length
       (`issue #579 <https://github.com/HansBug/pyfcstm/issues/579>`_, the same
       for models without regions); the number of turns is not measured here.
     - ``_DFS_STEP_LIMIT`` in ``pyfcstm/simulate/runtime.py``; fixture
       ``pseudo_self_loop_step_limit_raises_dfs_error``.
     - :ref:`region-limits-run`
   * - BMC: re-entries of one owner inside its own entry
     - ``BmcOptions.max_group_reentries``, default ``16``. A model that needs more
       raises ``BmcBuildError`` instead of being approximated. There is no
       command-line option: ``pyfcstm bmc`` always uses the default.
     - ``pyfcstm/bmc/engine.py``, ``pyfcstm/bmc/region_relation.py``;
       ``test/bmc/test_region_relation.py``.
     - :ref:`region-limits-run`, :doc:`/reference/bmc_query/index`
   * - BMC: depth of one expression
     - 100 levels. A query whose expression nests deeper is refused with
       ``expression_too_deep``; 98 prefix negations in front of one comparison are
       accepted and 99 are refused.
     - ``pyfcstm/bmc/binding.py``; ``test/bmc/test_query_binding.py``.
     - :ref:`region-limits-run`
   * - A history owner whose subtree contains a region
     - Rejected with ``E_REGION_STRUCTURE`` (``history_boundary``). A history
       inside a region, over states without regions, is legal.
     - ``validate_region_structure`` in ``pyfcstm/model/region.py``;
       ``test/model/test_region_consumers.py``.
     - :ref:`dsl-history-regions`
   * - jsfcstm ``inspectModel``
     - Builds no report for a model with regions or ``active()`` queries:
       ``isInspectable(machine)`` is ``false`` and ``inspectModel`` throws
       ``inspectModel does not support machines with regions or active() queries``.
       The editor skips the inspect diagnostics for such a model; the model,
       the semantic diagnostics and the diagram preview support regions.
     - ``editors/jsfcstm/src/diagnostics/inspect.ts``;
       ``editors/jsfcstm/test/region-diagnostics.test.ts``.
     - this table
   * - jsfcstm order diagnostics
     - ``I_REGION_BACKWARD_READ`` and ``W_REGION_BLIND_OVERWRITE`` do not exist in
       jsfcstm; only the Python ``pyfcstm inspect`` reports them.
     - Absent from ``editors/jsfcstm/src``; defined in
       ``pyfcstm/diagnostics/codes.yaml``.
     - :doc:`/reference/diagnostics_codes/index`
   * - Inspect over-approximation: history defaults
     - A composite state that is entered only through its history default still
       has its ordinary initial child counted as reachable, so ``inspect`` does
       not report that child (the output below: ``unreachable: 0``). The rule
       errs towards a missed finding, never a false one.
     - ``pyfcstm/diagnostics/inspect.py``; release notes.
     - :ref:`region-limits-run`
   * - Inspect over-approximation: verify on the machine that runs
     - ``pyfcstm.verify`` judges the machine after lowering. For a forced
       declaration it stays a guard-agnostic over-approximation, so a state behind
       a composite that only a forced declaration can leave may still be listed
       as reachable.
     - Release notes (Inspect and verify).
     - recorded
   * - Inspect over-approximation: one mark per forced declaration
     - A forced declaration is marked as a whole when one of its expansions starts
       from an unreachable state.
     - Release notes (Inspect and verify).
     - recorded
   * - Forced declarations over regions
     - Two declarations of one owner compete for the group: the one raised first
       holds it and the second is not tried, where a model without regions tries
       the next declaration. Other transitions of a leaf inside a region keep
       working while the variable is raised
       (`issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_).
     - Fixture
       ``region_forced_declaration_whose_target_cannot_be_entered_holds_the_group_against_a_later_declaration``.
     - :ref:`dsl-region-forced`
   * - Candidate that only loops, in a composite state
     - In a model without regions, a candidate that leads back to its own start
       through a pseudo state makes the cycle a Delta instead of letting a later
       candidate fire (the output below;
       `issue #578 <https://github.com/HansBug/pyfcstm/issues/578>`_).
       The same issue records a second defect, handler calls inside a Delta cycle;
       that one was not re-run.
     - ``limits_composite_loop.fcstm`` and the demo output.
     - :ref:`region-limits-run`
   * - Exported text of a forced declaration over regions
     - ``to_ast_node()`` text loads to a machine that behaves the same on the
       reproduction of `issue #580 <https://github.com/HansBug/pyfcstm/issues/580>`_
       (exit order and result agree, output below); the issue records the earlier
       behavior.
     - ``region_limits.demo.py``.
     - :ref:`region-limits-run`
   * - Behavioral inspect diagnostics and sugar
     - Which diagnostic codes belong to the model as written and which to the
       machine that runs is still being classified; a finding of the machine that
       runs can name a hidden variable or a generated state
       (`issue #588 <https://github.com/HansBug/pyfcstm/issues/588>`_).
     - Issue text and release notes.
     - recorded
   * - jsfcstm preview of a history
     - The editor preview draws a history after lowering; the Python diagram
       snapshot and PlantUML draw it as written
       (`issue #590 <https://github.com/HansBug/pyfcstm/issues/590>`_).
     - Issue text.
     - recorded
   * - Generated C family: capacities
     - ``..._ARENA_CAPACITY`` defaults to ``8`` for a model without regions,
       pseudo states and composite states, otherwise ``max(24, 12 * scopes)``, and
       ``..._TRAIL_CAPACITY`` to ``4`` or ``16 + 4 * scopes``, where scopes is the
       number of states after lowering (hidden gate states such as
       ``__forced_gate_0`` included) plus the number of regions; the tutorial
       controller has 7 states after lowering and 2 regions, so 9 scopes. The values are an empirical
       formula, not a proven bound; a cycle that needs more fails with
       ``Speculative search exceeded the capacity safety limit`` naming the macro.
       Raise the macro for every translation unit
       (`issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_).
     - ``_plan_capacity`` in ``pyfcstm/render/c_kernel.py``;
       ``test/render/test_c_kernel.py``.
     - :ref:`region-limits-run`, :doc:`/reference/builtin_templates/index`
   * - Generated Python runtime
     - Every generated ``machine.py`` carries the general search kernel (position
       parsing, memoization, group initialization) whether or not the model uses
       regions, and does the same speculative work as the simulator; further
       specialization is tracked in
       `issue #596 <https://github.com/HansBug/pyfcstm/issues/596>`_. The
       limits 64 and 1000 apply to it.
     - ``templates/python/machine.py.j2``.
     - :doc:`/reference/builtin_templates/index`
   * - Templates without ``region`` in ``features``
     - ``pyfcstm generate`` refuses a model with regions with ``E_UNSUPPORTED_FEATURE``
       before writing a file.
     - ``pyfcstm/entry/generate.py``.
     - :doc:`/reference/cli/index`

.. _region-limits-run:

Reproducing the limits
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: limits_composite_loop.fcstm
   :language: fcstm

.. literalinclude:: limits_history_default.fcstm
   :language: fcstm

.. literalinclude:: region_limits.demo.py.txt
   :language: text

Read the blocks in order. The depth block shows the boundary between 64 and 65
nested owners; the step block shows the refusal of a 500-turn chain; the BMC
blocks show the default bound of 16 re-entries (``n < 3`` builds, ``n < 20``
does not) and that the option lowers or raises it, and the 98/99 boundary of
expression depth; the history block shows the rejection. The composite block
shows the cycle that becomes a Delta (``delta=True`` on both ``Root.Go`` cycles)
although ``S -> T`` could fire; the export block shows both machines agreeing; the
inspect block shows ``unreachable: 0`` for a model in which ``Root.P.A`` cannot be
entered, because ``P`` is entered only through its history default ``B`` and has
no way out, so nothing ever records ``A``. The capacity block prints the defaults
the C templates use for the tutorial controller and for a flat machine. None of
these numbers is a performance figure.

Related references: :doc:`../dsl/index`, :doc:`../diagnostics_codes/index`,
and :doc:`/api_doc_en`.
