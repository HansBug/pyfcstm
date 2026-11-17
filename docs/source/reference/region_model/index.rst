Region models and configurations
================================

This page describes Python model construction and position values. Execution,
code generation, diagrams and inspect/verify analysis currently reject models
containing regions or activity queries with ``E_UNSUPPORTED_FEATURE``. Parsing
and constructing a model does not imply that those consumers can execute it.
The JavaScript model frontend still rejects these features during construction.

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
       partial region initialization and all-Done snapshots. This does not make
       them valid runtime parking positions or hot-start inputs.

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

Related references: :doc:`../dsl/index`, :doc:`../diagnostics_codes/index`,
and :doc:`/api_doc_en`.
