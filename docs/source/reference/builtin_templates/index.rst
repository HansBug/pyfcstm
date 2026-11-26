.. _sec-reference-builtin-templates:

Built-in templates reference
============================

Use these names with ``pyfcstm generate --template <name>``. Do not use a
repository ``templates/`` path as the ordinary built-in entry point; that path is
maintainer source.

All current built-in templates are marked ``experimental: true`` in packaged
metadata. In this reference, **experimental** means the generated output has the
current repository's test and smoke evidence, but it is not presented as a
production certification or every-platform guarantee.

.. template-ref-meta: name=python title=Python language=python archive=python.zip root_dir=python experimental=true description="Native Python built-in template with embedded runtime logic."
.. template-ref-meta: name=c title=C99 language=c archive=c.zip root_dir=c experimental=true description="Native C99 built-in template with embedded runtime logic and abstract hook callbacks."
.. template-ref-meta: name=c_poll title="C Poll" language=c archive=c_poll.zip root_dir=c_poll experimental=true description="Native C99 / C++98 built-in template with hook-polled events and embedded runtime logic."
.. template-ref-meta: name=cpp title="C++ Wrapper" language=cpp archive=cpp.zip root_dir=cpp experimental=true description="Early-stage first-class C++ template that reuses the C99 runtime core and emits C++ wrapper files."
.. template-ref-meta: name=cpp_poll title="C++ Poll Wrapper" language=cpp archive=cpp_poll.zip root_dir=cpp_poll experimental=true description="Early-stage first-class C++ poll template that reuses the C poll runtime core and emits C++ wrapper files."

.. template-ref-contract: name=python generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status

.. template-ref-profile: name=python event_input=cycle_events wrapper=false core=python native_evidence=false semantic_alignment=true formatter=ruff poll=false
.. template-ref-profile: name=c event_input=explicit_event_ids wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=c_poll event_input=event_checks wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=true
.. template-ref-profile: name=cpp event_input=explicit_event_ids wrapper=true core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=cpp_poll event_input=event_checks wrapper=true core=c_poll native_evidence=true semantic_alignment=true formatter=clang-format poll=true

The hidden ``template-ref-profile`` markers above include a ``core`` value used
only by the documentation drift checker. It is a docs-internal derived field
from generated files and template tests, not a public metadata key in
``template.json`` or ``index.json``.

Metadata matrix
---------------

The table combines ``pyfcstm/template/index.json`` with
``templates/<name>/template.json``. ``archive`` and ``root_dir`` come from the
packaged index; the remaining visible metadata is mirrored by the source
``template.json`` files.

.. list-table:: Built-in template metadata
   :header-rows: 1

   * - Name
     - Title
     - Language
     - Archive / root
     - Experimental
     - Description
   * - ``python``
     - Python
     - ``python``
     - ``python.zip`` / ``python``
     - ``true``
     - Native Python built-in template with embedded runtime logic.
   * - ``c``
     - C99
     - ``c``
     - ``c.zip`` / ``c``
     - ``true``
     - Native C99 built-in template with embedded runtime logic and abstract hook callbacks.
   * - ``c_poll``
     - C Poll
     - ``c``
     - ``c_poll.zip`` / ``c_poll``
     - ``true``
     - Native C99 / C++98 built-in template with hook-polled events and embedded runtime logic.
   * - ``cpp``
     - C++ Wrapper
     - ``cpp``
     - ``cpp.zip`` / ``cpp``
     - ``true``
     - Early-stage first-class C++ template that reuses the C99 runtime core and emits C++ wrapper files.
   * - ``cpp_poll``
     - C++ Poll Wrapper
     - ``cpp``
     - ``cpp_poll.zip`` / ``cpp_poll``
     - ``true``
     - Early-stage first-class C++ poll template that reuses the C poll runtime core and emits C++ wrapper files.

Discovery API
-------------

The public package API in ``pyfcstm.template`` is intentionally small:

.. list-table:: Built-in template API
   :header-rows: 1

   * - Function
     - Use
     - Boundary
   * - ``list_templates()``
     - Return installed built-in template names in packaged-index order.
     - Discovery only; it does not render or validate a model.
   * - ``has_template(name)``
     - Check whether one name is present.
     - Raises index load errors if package metadata is missing or invalid.
   * - ``get_template_info(name)``
     - Return a shallow copy of one metadata entry.
     - Raises ``LookupError`` for an unknown name.
   * - ``extract_template(name, output_dir)``
     - Extract the packaged archive into a normal directory for the renderer.
     - In a development checkout, may copy repository source if the archive is absent.

Generated README contract
-------------------------

Every built-in template emits ``README.md`` and ``README_zh.md``. Those files
are generated from the model and should be treated as the concrete integration
contract for that generated machine. They provide names and ids that cannot be
fully known in this generic reference: class names, C prefixes, hook names,
event ids, state ids, hot-start examples, and target build snippets.

.. _sec-reference-builtin-templates-regions:

Models with regions
-------------------

All five built-in templates declare ``features: [region]`` in their
``config.yaml`` (see :ref:`sec-reference-template-config-features`), so
``pyfcstm generate --template <name>`` renders a model that declares ``region``
blocks, nested ones included, with every one of them. A custom template
directory is refused for such a model unless it declares the feature itself.
For the refusal text, see :doc:`/reference/template_config/index`. The
generated runtime follows the simulator's rules for regions: a region owner
advances its regions in the order they are written, a later region reads what an
earlier one wrote in the same cycle, and the position of the machine is a tree
instead of one path. For those rules, see
:doc:`/explanations/region_semantics/index`.

The facts below were read from the files that ``pyfcstm generate --template X``
writes for ``region_controller.fcstm`` (two regions inside ``Running``) and for
``region_plain.fcstm`` (no region), and from the generated ``README.md`` of
each. The repository's template tests run the 118 shared region cases
(``region_*.yaml`` under ``test/fixtures/simulate_semantics/cases``) against
every built-in template: the Python template is compared with
``SimulationRuntime``, and the four C-family templates are compiled and run
against it. This page did not re-run those suites.

.. literalinclude:: region_controller.fcstm
   :language: fcstm
   :caption: region_controller.fcstm

.. literalinclude:: region_plain.fcstm
   :language: fcstm
   :caption: region_plain.fcstm

Position and queries
~~~~~~~~~~~~~~~~~~~~

.. list-table:: Reading the position, by template and by model kind
   :header-rows: 1

   * - Template
     - Model with regions
     - Model without regions
   * - ``python``
     - ``configuration`` (position text), ``leaves`` (tuple of path tuples), ``is_active(path)``, ``region_status(path)``. No ``current_state_path`` and no ``current_state_name``: reading either is an ``AttributeError``.
     - The same four members, plus ``current_state_path`` (tuple, ``None`` after termination) and ``current_state_name``. ``region_status`` does not exist.
   * - ``c``, ``c_poll``
     - ``<Prefix>_get_configuration`` fills a ``<Prefix>Configuration`` value (``at`` plus one slot per region); the value has query, check, format and parse functions. No ``<Prefix>_current_state_id``, ``_path`` or ``_name`` is declared in ``machine.h``, so a call fails to compile.
     - The configuration functions exist as well; ``<Prefix>_current_state_id``, ``_path`` and ``_name`` also exist.
   * - ``cpp``, ``cpp_poll``
     - ``MachineWrapper::get_configuration`` plus static ``region_status``, ``is_active``, ``leaves``, ``validate_configuration``, ``format_configuration`` and ``parse_configuration``. ``current_state_id()`` and ``current_state_path()`` are not declared.
     - The same members, plus ``current_state_id()`` and ``current_state_path()``.

Position text is the one ``SimulationRuntime`` prints. ``Controller.Idle`` is a
position without regions; ``Controller.Running{Safety: Watching, Motion: On}``
names the deepest state of each region; ``[done]`` replaces a state for a
finished region and ``[init]`` for a region that waits for its initial
transition. In Python, ``region_status(path)`` returns one of four strings, in C
the same four values are ``<PREFIX>_REGION_STATUS_*`` macros:

.. list-table:: Region status values
   :header-rows: 1

   * - Python string
     - C macro (value)
     - Meaning
   * - ``'live'``
     - ``..._REGION_STATUS_LIVE`` (2)
     - The owner is active and the region holds an active state.
   * - ``'done'``
     - ``..._REGION_STATUS_DONE`` (3)
     - The region has finished and stays finished until the owner is entered again.
   * - ``'pending'``
     - ``..._REGION_STATUS_PENDING`` (1)
     - The owner is active and the region has not run its initial transition yet (text ``[init]``).
   * - ``'inactive'``
     - ``..._REGION_STATUS_INACTIVE`` (0)
     - The owner is not part of the position.

``region_status`` raises ``ValueError`` for a path that is a state (``region_status requires a Region path.``) and for a
path that does not exist (``Unknown configuration path: 'Controller.Nowhere'.``).

Python runtime
~~~~~~~~~~~~~~

.. list-table:: Python generated runtime, public surface
   :header-rows: 1

   * - Member
     - Contract
   * - ``Machine(initial_state=None, initial_vars=None, *, parameters=None)``
     - Cold construction, or complete hot restoration when ``initial_state`` is given.
   * - ``initial_state``
     - Position text, dotted path, or tuple of names. For a model with regions: the leaves that are written are put in place without an enter action; what is not written waits for initialization (``[init]``) and runs its initial transitions in the first cycle. A region written ``[done]`` stays done; an owner whose regions are all ``[done]`` raises ``ValueError``.
   * - ``initial_vars``
     - Every variable, hidden ones such as ``__forced_0`` included, for a hot start. A cold start accepts a partial mapping of control and output variables.
   * - ``cycle(events=None, *, inputs=None)``
     - Returns ``None``. Observe the result through ``configuration``, ``vars``, ``is_ended``, ``last_cycle_was_delta``.
   * - ``vars``
     - Read-only mapping view of the committed variables; there is no ``variables`` alias.
   * - ``ABSTRACT_HOOKS``, ``get_abstract_hook_map()``
     - Read-only mapping of DSL abstract actions to override method names; ``get_abstract_hook_map()`` returns a copy.
   * - hook context ``ctx``
     - ``vars``, ``inputs``, ``parameters``, ``state_path``, ``active_leaf``, ``action_name``, ``abstract_target``, ``action_stage``, ``call_stage``, ``named_ref`` and ``configuration``. For an action that wraps several regions, ``state_path`` and ``active_leaf`` are the deepest state common to every branch, for example the owner.
   * - event names
     - Absolute path, ``/``-rooted path, ``.``-relative path, or a short name. For a model with regions, a short name is resolved once for each active leaf; no match raises ``SimulationRuntimeEventError``, equal matches are used, different matches are reported as ambiguous with every candidate listed. A region in ``[init]`` has no active leaf and takes no part.

The following run generates the Python runtime for both models and drives it.
It shows the position text before and after a ``/Start`` event, the four region
statuses, the missing ``current_state_path`` on the region model, the rejected
paths, six spellings of ``initial_state`` with the resulting position, the
all-``[done]`` refusal, the hook context for an action that wraps two regions,
and the same members on the plain model.

.. literalinclude:: region_python_runtime.demo.py
   :language: python
   :caption: region_python_runtime.demo.py

.. literalinclude:: region_probe.fcstm
   :language: fcstm
   :caption: region_probe.fcstm

.. literalinclude:: region_python_runtime.demo.py.txt
   :language: text
   :caption: region_python_runtime.demo.py output

Reading the output:

* the first cycle only enters ``Controller.Idle``; the ``/Start`` event given to
  the second cycle moves the machine to ``Controller.Running{Safety: Watching,
  Motion: Off}`` and the third cycle turns the motor on, so the position text
  keeps one entry per region;
* after ``/Stop`` the owner is left, both regions report ``inactive`` and the
  hidden variable ``__forced_0`` is back to ``0``;
* the six ``initial_state`` spellings give only four distinct positions: a
  region that is left out, written as a dotted path through another region, or
  given as a bare owner path is ``[init]``; a region written ``[init]`` is
  ``pending`` as well;
* a hot start is not a cycle: the position is set, no enter action runs, and the
  first later cycle initializes the pending regions;
* in the probe, ``Tick`` is inside ``Left`` and reports that leaf, while
  ``Settle`` wraps both regions and reports the owner ``Line.Work``. In the first
  cycle ``Tick`` sees ``Right`` as ``[init]``, because ``Left`` is entered first
  and ``ctx.configuration`` is the position at the moment of the call.

The run does not show a ``done`` region. Whether ``region_status`` returns
``'done'`` for it is covered by the shared region cases, not by this page.

C-family runtime
~~~~~~~~~~~~~~~~

The four C-family templates share one kernel emitter: ``c`` and ``cpp`` take
events as ids, ``c_poll`` and ``cpp_poll`` query an event-check table, and the
C++ templates wrap the C core. For a model with regions:

.. list-table:: C-family generated runtime, public surface (``<Prefix>`` is the generated prefix, for example ``ControllerMachine``)
   :header-rows: 1

   * - Member
     - Contract
   * - ``<Prefix>Configuration``
     - Plain value: ``at`` is the deepest active state outside every region and ``regions[r]`` the deepest active state of region ``r``, ``<PREFIX>_REGION_SLOT_PENDING`` (0) or ``<PREFIX>_REGION_SLOT_DONE`` (-1). A valid value has one representation, so ``memcmp`` compares two values; the C++ wrapper adds ``operator==`` and ``operator!=``.
   * - ``<Prefix>_get_configuration(machine, &cfg)``
     - Writes the current position; returns 0 once the machine has ended.
   * - ``<Prefix>_hot_start_at(machine, &cfg, &vars)``, ``..._hot_start_at_with_parameters(...)``
     - Restores a position and a complete variable snapshot without enter actions. The plain ``hot_start`` (state id) still exists for states outside every region.
   * - ``configuration_region_status``, ``configuration_is_active``, ``configuration_leaves``
     - Queries that take a configuration and no machine. ``configuration_leaves(cfg, NULL, 0u)`` counts the leaves.
   * - ``configuration_validate(cfg, &err)``
     - 1 for a well-formed value, else 0 and a ``<Prefix>ConfigurationError`` with ``kind`` (``<PREFIX>_CONFIGURATION_ERROR_*``, 1 to 11), byte ``position`` and ``message``.
   * - ``configuration_format(cfg, buf, size)``, ``configuration_parse(text, &cfg, &err)``
     - Text form, byte-identical to the simulator's. ``format`` truncates to ``size`` and returns the full length. ``parse`` leaves ``cfg`` unchanged on failure; regions left out of the text are pending. Both are omitted when ``PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT`` is defined for ``machine.c`` and every consumer.
   * - ``<PREFIX>_REGION_COUNT``, ``<PREFIX>_REGION_<path>``
     - Number of regions and one region id per region, in owner order and written order within an owner.
   * - ``<Prefix>ExecutionContext``
     - ``state_id`` and ``active_leaf_state_id`` hold the same value: for an action inside a region its own state, for an aspect or owner action the deepest state common to everything it wraps. A model with regions has no single leaf, so read the position with ``get_configuration``.
   * - ``<PREFIX>_ARENA_CAPACITY``, ``<PREFIX>_TRAIL_CAPACITY``, ``<PREFIX>_STORAGE_BYTES``
     - Static sizing of the machine; see the capacity table below.

Two rules differ between ``c`` / ``cpp`` and ``c_poll`` / ``cpp_poll``:

* ``c``: ``<Prefix>_cycle(machine, event_ids, count)`` and
  ``<Prefix>_cycle_with_inputs(machine, event_ids, count, &inputs)``; ``cpp``:
  ``cycle()``, ``cycle(event_id)``, ``cycle(ids, count)`` and
  ``cycle_with_inputs(inputs, ids, count)``;
* ``c_poll``: ``<Prefix>_set_event_checks(machine, &checks, user_data)`` with a
  ``<Prefix>EventChecks`` table (one ``check_<event>`` function per event,
  initialised with ``<PREFIX>_EVENT_CHECKS_INIT``-style macro
  ``CONTROLLERMACHINE_EVENT_CHECKS_INIT`` for this model),
  ``<Prefix>_cycle(machine)`` and ``<Prefix>_cycle_with_inputs(machine,
  &inputs)``; ``cpp_poll``: ``set_event_checks`` and ``cycle_with_inputs(inputs)``.
  The ``<Prefix>EventContext`` of a check has ``event_id`` and ``vars``; for a
  model without regions it also has ``current_state_id``, which does not exist
  for a model with regions.

.. list-table:: Capacity macros of the generated C-family runtime
   :header-rows: 1

   * - Macro
     - ``region_controller.fcstm``
     - ``region_plain.fcstm``
     - Meaning
   * - ``<PREFIX>_ARENA_CAPACITY``
     - 108
     - 8
     - How many configurations and pending work items one decision of a cycle may examine. The default depends on the model: ``max(24, 12 * scopes)`` for ``region_controller.fcstm``, whose 7 states after lowering and 2 regions make 9 scopes.
   * - ``<PREFIX>_TRAIL_CAPACITY``
     - 52
     - 4
     - How many checks may be nested. The default depends on the model.
   * - ``<PREFIX>_STORAGE_BYTES``
     - 14272 (``944 + 108 * 108 + 52 * 32`` for ``c`` and ``cpp``; 976 as the constant term for ``c_poll`` and ``cpp_poll``)
     - ``848 + 8 * 68 + 4 * 32`` for ``c`` and ``cpp``; 880 as the constant term for ``c_poll`` and ``cpp_poll``
     - Derived from both macros; the machine type is that many bytes of static, opaque storage.

The macros replace ``MAX_STACK_DEPTH`` and ``MAX_DFS_STEPS``, which the runtime
no longer defines. Define a changed value for ``machine.c`` and for every file
that includes ``machine.h``, for example ``-DCONTROLLER_MACHINE_ARENA_CAPACITY=480``,
because the size of a machine depends on them. A cycle that needs more room fails and
``last_error()`` starts with ``Speculative search exceeded the capacity safety
limit`` and names the macro to raise. Depth and step limits that come from the model
(``Speculative DFS exceeded the structural stack-depth safety limit``,
``Group initialization nested deeper than the structural safety limit``,
``Speculative DFS exceeded the step safety limit``) are fixed. A closed loop
that can never stop reports ``Cannot reach a stoppable state in the same cycle; suspected loop.``

.. literalinclude:: region_c_runtime.c
   :language: c
   :caption: region_c_runtime.c (driver for the ``c`` template)

.. literalinclude:: region_c_hooks.c
   :language: c
   :caption: region_c_hooks.c (hook context in a model with two regions)

.. literalinclude:: region_cpp_runtime.cpp
   :language: cpp
   :caption: region_cpp_runtime.cpp (driver for the ``cpp`` template)

.. literalinclude:: region_c_poll_runtime.c
   :language: c
   :caption: region_c_poll_runtime.c (driver for the ``c_poll`` template)

.. literalinclude:: region_cpp_poll_runtime.cpp
   :language: cpp
   :caption: region_cpp_poll_runtime.cpp (driver for the ``cpp_poll`` template)

.. literalinclude:: region_c_family.demo.sh
   :language: bash
   :caption: region_c_family.demo.sh (generates, compiles and runs each driver)

.. literalinclude:: region_c_family.demo.sh.txt
   :language: text
   :caption: region_c_family.demo.sh output

Reading the output:

* ``at=2 regions=[3, 5]`` is the configuration value behind the text
  ``Controller.Running{Safety: Watching, Motion: On}``: ``2`` is ``Running``,
  ``3`` and ``5`` are the active leaves of ``Safety`` and ``Motion``, and a
  region slot of ``0`` means pending; in ``cycle 1`` the owner is not active, so
  both slots are ``0``;
* ``parse`` accepts a text with a region left out and gives ``[init]`` for it,
  and refuses a dotted path through a region (kind 5, a path passes through the
  regions of its owner), an unknown region (kind 6) and a repeated region
  (kind 7); each error carries the byte position of the offence;
* ``hot_start_at`` puts the machine on the saved position and the next cycle
  continues from there; the hot start shows the position without running any
  enter action;
* the hook driver reports the owner-level state for the enter action of ``Line``
  (``state_id=0``) and the leaf ``Left.L`` for the action inside the region,
  with ``active_leaf_state_id`` equal to ``state_id`` in both cases;
* ``c_poll`` and ``cpp_poll`` call the ``Start`` check once per cycle while the
  machine rests in ``Idle`` and never call the ``Stop`` check there (the run
  shows the counts, not the reason, so this page states no rule for it); the
  ``cpp`` drivers compile with ``-std=c++98`` and the C core with ``-std=c99``;
* the plain model keeps ``current_state_name`` and ``current_state_path`` in
  ``machine.h``; the model with regions declares none.

The run does not exercise ``PYFCSTM_GENERATED_NO_HEAP``, the sanitizer builds or
the ``native-toolchain`` matrix; those belong to the template test suites.

Changed names for older integrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Interfaces that no longer exist
   :header-rows: 1

   * - Older integration code
     - Current generated runtime
   * - Python ``machine.variables``
     - Removed; use ``machine.vars`` (read-only view).
   * - Python ``machine.vars['x'] = 1``
     - Not supported; ``vars`` is a read-only view. Express writes in the DSL.
   * - Python ``ABSTRACT_HOOKS`` as a dictionary to edit
     - A read-only mapping; ``get_abstract_hook_map()`` returns a copy.
   * - Python ``current_state_path`` on a model with regions
     - ``AttributeError``; read ``configuration`` or ``leaves``.
   * - C ``MAX_STACK_DEPTH``, ``MAX_DFS_STEPS``
     - Removed; use the ``ARENA_CAPACITY`` and ``TRAIL_CAPACITY`` macros.
   * - C ``<Prefix>_current_state_id`` on a model with regions
     - Not declared, so the call fails to compile; use ``get_configuration``.
   * - C machine as a transparent struct
     - The machine is opaque storage of ``<PREFIX>_STORAGE_BYTES`` bytes; use the functions in ``machine.h``.

Template contracts
------------------

``python``
~~~~~~~~~~

* Generated files: ``machine.py``, ``README.md``, and ``README_zh.md``.
* Entry point: import the generated machine class from ``machine.py``. For the
  tutorial model this class is ``SimpleMachineMachine``.
* Event model: ``cycle(events=None, *, inputs=None)`` accepts no event, one
  event string, or a list, tuple or set of event strings; ``inputs`` supplies
  numeric input values for that cycle.
* Extension point: subclass the generated class and override protected abstract
  hook methods listed in the generated README.
* Lifecycle concepts: construction, initial ``cycle()``, later ``cycle(...)``
  calls, hot start through constructor arguments (``initial_state``,
  ``initial_vars``, ``parameters``), position and variable reads. A model with
  regions reads its position through ``configuration``; see
  :ref:`sec-reference-builtin-templates-regions`.
* Target boundary: Python 3.7+ standard library runtime; generated code should
  not import ``pyfcstm``.
* Evidence boundary: Python template tests and semantic-alignment tests cover
  the supported generated-runtime behavior; one tutorial smoke check is only a
  first-success signal.

``c``
~~~~~

* Generated files: ``machine.h``, ``machine.c``, ``README.md``, and
  ``README_zh.md``.
* Entry point: include ``machine.h`` and call generated C functions such as
  ``..._init(...)``, ``..._cycle(machine, event_ids, event_count)``,
  ``..._vars(...)``, and ``..._destroy(...)`` when heap helpers are enabled.
* Event model: the application passes generated integer event ids to each cycle.
* Extension point: install an abstract-hook table whose callback signatures are
  described in the generated header and README.
* Lifecycle concepts: caller-owned or heap-allocated machine object,
  initialization, hot start, cycle, variable reads, state reads, and destroy.
* Target boundary: C99 core, C++98-compatible public header use, standard
  library only by default, fixed-width generated integer profile for integer
  variables.
* Evidence boundary: native smoke and template alignment checks are toolchain
  evidence, not certification for every compiler or deployment profile.

``c_poll``
~~~~~~~~~~

* Generated files: ``machine.h``, ``machine.c``, ``README.md``, and
  ``README_zh.md``.
* Entry point: include ``machine.h``, initialize the machine, install hooks and
  a complete ``EventChecks`` table, then call the polling cycle API.
* Event model: the runtime calls installed event-check functions during a cycle;
  it does not accept per-cycle external event-id arrays.
* Extension point: abstract hooks use ``Hooks``; event truth comes from
  ``EventChecks`` callbacks.
* Lifecycle concepts: initialization, event-check installation, hot start,
  cycle, variable reads, state reads, and destroy.
* Target boundary: same C-family profile as ``c``, with event polling added to
  the public surface.
* Evidence boundary: native and alignment evidence must include event-check
  behavior; a callback result should behave as a read-only probe for one cycle.

``cpp``
~~~~~~~

* Generated files: ``machine.h``, ``machine.c``, ``machine.hpp``,
  ``machine.cpp``, ``README.md``, and ``README_zh.md``.
* Entry point: include ``machine.hpp`` and use
  ``pyfcstm_generated::<Machine>_cpp::MachineWrapper``. The C core is included,
  but C++ user code should not bypass the wrapper as its main surface.
* Event model: wrapper cycle methods submit generated event ids to the reused C
  core.
* Extension point: the wrapper exposes C hook registration through C++ aliases;
  runtime behavior remains in the generated C core.
* Lifecycle concepts: wrapper construction, hook registration, cycle overloads,
  variable/state reads, hot start through the public C core where documented,
  and wrapper-owned initialization.
* Target boundary: C99 execution core plus C++98-compatible, exception-free,
  RTTI-free wrapper with no STL container requirement.
* Evidence boundary: C++ smoke tests must exercise ``machine.hpp`` /
  ``machine.cpp`` wrapper entry points, even though the final executable links
  the generated C core.

``cpp_poll``
~~~~~~~~~~~~

* Generated files: ``machine.h``, ``machine.c``, ``machine.hpp``,
  ``machine.cpp``, ``README.md``, and ``README_zh.md``.
* Entry point: include ``machine.hpp`` and construct
  ``pyfcstm_generated::<Machine>_cpp_poll::MachineWrapper`` (note the
  ``_cpp_poll`` namespace); install wrapper hooks and wrapper event checks,
  then call ``cycle()``.
* Event model: the reused C polling core calls installed event-check functions;
  the C++ wrapper exposes aliases and setter methods for those checks.
* Extension point: abstract hooks and event checks are both installed through
  wrapper-facing APIs.
* Lifecycle concepts: wrapper construction, hook/event-check installation,
  cycle, variable/state reads, hot start through the underlying public surface
  where documented, and wrapper-owned initialization.
* Target boundary: C polling core plus C++98-compatible wrapper; not a fully
  independent C++ runtime.
* Evidence boundary: smoke and alignment tests must cover the wrapper and the
  polling event model, not just the reused C core.

Target-profile notes
--------------------

C-family templates use fixed-width generated integer storage in the default
profile. Numeric deployment warnings therefore apply to ``c``, ``c_poll``,
``cpp``, and ``cpp_poll`` targets. They should not be presented as proof that a
Python generated runtime has the same fixed-width integer carrying risk.

C++ templates reuse C cores by design. ``cpp`` reuses the C99 core; ``cpp_poll``
reuses the C polling core. Their C++ value is the wrapper integration surface,
not a separate execution semantics implementation.

Selection and misuse matrix
---------------------------

.. list-table:: Selection matrix
   :header-rows: 1

   * - Template
     - Good first use
     - Misuse to avoid
     - First verification
   * - ``python``
     - Application or test code can import a Python module and call ``cycle``.
     - Treating Python smoke success as evidence for C-family integer storage or compiler behavior.
     - Import ``machine.py`` and run a short event sequence from the generated README.
   * - ``c``
     - A C host collects events and submits generated event ids each cycle.
     - Expecting polling callbacks to be queried by the explicit-event API.
     - Compile ``machine.c`` with a driver that includes ``machine.h`` and submits ids.
   * - ``c_poll``
     - A C host wants event truth queried from callbacks at cycle time.
     - Leaving an ``EventChecks`` entry unset and assuming a missing callback means false in every integration shape.
     - Compile and run a driver that installs the full event-check table.
   * - ``cpp``
     - A C++ host wants wrapper methods while accepting a generated C core.
     - Calling it a fully independent C++ runtime or testing only the C core.
     - Compile a consumer that includes ``machine.hpp`` and uses the wrapper.
   * - ``cpp_poll``
     - A C++ host wants wrapper-facing polling callbacks.
     - Mixing explicit event ids with the polling wrapper and expecting both APIs to be equivalent.
     - Compile a wrapper consumer that installs event checks and calls ``cycle()``.

Per-template evidence cards
---------------------------

.. list-table:: Evidence cards
   :header-rows: 1

   * - Template
     - Source facts
     - Runtime evidence
     - Boundary evidence
   * - ``python``
     - Packaged metadata, Python template config, generated README templates, Python template tests.
     - Import/cycle smoke and simulator-alignment tests for the supported Python generated runtime.
     - No native compiler proof; generated code should be self-contained Python standard-library code.
   * - ``c``
     - C template config, C runtime helpers from ``pyfcstm/render/c_runtime.py``, generated C README, native tests.
     - C compiler smoke and semantic-alignment coverage for explicit event ids.
     - Fixed-width integer profile and toolchain-specific native evidence must remain visible.
   * - ``c_poll``
     - C polling template config, event-check generated files, C runtime helper source facts.
     - Native smoke that exercises polling callbacks and alignment coverage for the polling event model.
     - Polling changes event input, not FCSTM lifecycle semantics.
   * - ``cpp``
     - C core template facts plus wrapper ``machine.hpp`` / ``machine.cpp`` templates.
     - C++ wrapper smoke, not merely C core compile success.
     - Wrapper integration surface is C++98-compatible and reuses the generated C core.
   * - ``cpp_poll``
     - C polling core facts plus polling wrapper templates.
     - Wrapper smoke with event checks installed through the wrapper-facing surface.
     - Not an independent C++ polling runtime; it is a C polling core plus wrapper.

Generic example snippets
------------------------

The exact names are model-specific. Treat these snippets as shape examples and
read the generated README for the concrete symbols.

.. list-table:: Integration shapes
   :header-rows: 1

   * - Template
     - Shape example
     - What the generated README supplies
   * - ``python``
     - ``from machine import <GeneratedMachine>; machine = <GeneratedMachine>(); machine.cycle()``
     - Class name, event strings, hook method names, state and variable readers.
   * - ``c``
     - ``#include "machine.h"`` then initialize a machine object and pass event-id arrays to the generated cycle function.
     - C prefix, type names, event ids, hook table fields, init/cycle/destroy names.
   * - ``c_poll``
     - Initialize the machine, install hooks, install ``EventChecks``, and call the polling cycle function.
     - Event-check table fields, callback signatures, lifecycle function names.
   * - ``cpp``
     - ``#include "machine.hpp"`` then construct the generated wrapper and call wrapper cycle methods.
     - Namespace, wrapper class name, hook aliases, cycle overloads.
   * - ``cpp_poll``
     - Construct the wrapper, install wrapper hooks and event checks, then call ``cycle()``.
     - Wrapper event-check aliases, setter names, and polling lifecycle snippets.

Unsupported or risky assumptions
--------------------------------

.. list-table:: Counterexamples
   :header-rows: 1

   * - Assumption
     - Why it is wrong
     - Safer wording
   * - "All built-in templates are production certified."
     - Metadata currently marks all five templates as experimental.
     - They have current repository tests and smoke evidence, not every-platform certification.
   * - "The repository ``templates/`` directory is the user API."
     - Ordinary users should use packaged assets through ``--template``.
     - Repository template source is a maintainer input and packaging source.
   * - "C++ templates do not need the C generated core."
     - ``cpp`` and ``cpp_poll`` reuse generated C cores.
     - C++ templates provide wrapper integration surfaces over the generated C core.
   * - "Polling templates change state-machine semantics."
     - Polling changes how event truth is supplied.
     - Lifecycle and transition semantics should remain aligned with the simulator, within documented exclusions.
   * - "A generated file tree proves runtime correctness."
     - Rendering success proves file creation only.
     - Runtime, native and semantic claims need matching smoke or alignment evidence.

When reviewing an integration claim with this table, first ask which evidence
layer the claim needs. File existence needs only a generation command; importing
a Python class needs a consumer smoke check; compiling C-family output needs a
native toolchain; semantic equivalence needs simulator-alignment fixtures.

That is why this page does not turn "a built-in template exists" into "the
target platform is certified." The template contract states what this repository
can prove; release, embedded-porting, or safety-critical deployment still needs
project-specific evidence from the target environment.

Source-fact audit map
---------------------

A reviewer can audit this page without guessing by checking these sources:

* package list and archive names: ``pyfcstm/template/index.json``;
* per-template title, language, description and experimental status:
  ``templates/<name>/template.json``;
* generated files and integration snippets: generated ``README.md`` and
  ``README_zh.md`` from each template;
* event input models: generated README files, runtime templates and template
  tests;
* C-family helper and fixed-width body facts: ``pyfcstm/render/c_runtime.py``;
* wrapper facts: ``templates/cpp`` and ``templates/cpp_poll`` source templates
  plus wrapper smoke tests;
* region support: ``features`` in each ``templates/<name>/config.yaml``, the
  C kernel emitters ``pyfcstm/render/c_kernel.py``,
  ``pyfcstm/render/c_kernel_engine.py`` and ``pyfcstm/render/c_configuration.py``,
  and the files that ``pyfcstm generate --template <name>`` writes for
  ``region_controller.fcstm`` and ``region_plain.fcstm``;
* current evidence boundary: template unit tests, semantic-alignment tests,
  formatter checks and native smoke checks when the host toolchain is available.
