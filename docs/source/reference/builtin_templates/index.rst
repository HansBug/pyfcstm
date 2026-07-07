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
     - First-class C++ wrapper template that reuses the C99 runtime core.
   * - ``cpp_poll``
     - C++ Poll Wrapper
     - ``cpp``
     - ``cpp_poll.zip`` / ``cpp_poll``
     - ``true``
     - C++ polling wrapper template that reuses the C polling runtime core.

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

Template contracts
------------------

``python``
~~~~~~~~~~

* Generated files: ``machine.py``, ``README.md``, and ``README_zh.md``.
* Entry point: import the generated machine class from ``machine.py``. For the
  tutorial model this class is ``SimpleMachineMachine``.
* Event model: ``cycle(events=None)`` accepts no event, one event string, or a
  collection of event strings.
* Extension point: subclass the generated class and override protected abstract
  hook methods listed in the generated README.
* Lifecycle concepts: construction, initial ``cycle()``, later ``cycle(...)``
  calls, hot start through constructor arguments, current-state and variable
  snapshots.
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
  ``pyfcstm_generated::<Machine>_cpp::MachineWrapper``; install wrapper hooks
  and wrapper event checks, then call ``cycle()``.
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
