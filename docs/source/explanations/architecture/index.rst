.. _sec-explanations-architecture:

Architecture explanation
========================

pyfcstm is organized around a model-centered pipeline. DSL text becomes parser
nodes, parser nodes become a semantic state-machine model, and the model can
then be simulated, inspected, verified within bounded policies, visualized, or
rendered into target-language code.

Main pipeline
-------------

.. figure:: structure.puml.svg
   :alt: pyfcstm architecture pipeline
   :align: center

   High-level repository pipeline.

The important design choice is that most features converge on the model layer.
The parser should not know about target-language code generation; templates
should not re-parse DSL text; visualization should not invent model facts that
the importer did not produce.

.. list-table:: Layer responsibilities
   :header-rows: 1

   * - Layer
     - Representative paths
     - Owns
     - Must not own
   * - DSL parsing
     - ``pyfcstm/dsl/grammar/``, ``pyfcstm/dsl/parse.py``, ``pyfcstm/dsl/listener.py``
     - Grammar entry points, parse errors, AST node construction.
     - Semantic validation that requires resolved model context.
   * - Model import and model objects
     - ``pyfcstm/model/``
     - States, variables, transitions, events, lifecycle actions, references, PlantUML export, validation diagnostics.
     - CLI presentation or template-specific target runtime behavior.
   * - Simulation
     - ``pyfcstm/simulate/`` and ``pyfcstm/entry/simulate/``
     - Executable reference semantics for cycles, events, hot starts, action ordering, and active-state traces.
     - Generated target-language runtime implementation details.
   * - Diagnostics and verify integration
     - ``pyfcstm/diagnostics/``, ``pyfcstm/verify/``, ``pyfcstm/solver/``
     - Structured model facts, diagnostic messages, bounded verification checks, SMT translation.
     - Unbounded proofs hidden inside everyday inspect commands.
   * - Rendering and templates
     - ``pyfcstm/render/``, ``templates/``, ``pyfcstm/template/``
     - Jinja environment, expression/statement rendering, packaged template assets, generated artifacts.
     - Parser grammar or simulator shortcuts.
   * - CLI entry points
     - ``pyfcstm/entry/``
     - User-facing command wiring, option parsing, output routing, and command-specific error boundaries.
     - Business logic that belongs in model, render, simulate, or diagnostics modules.
   * - Documentation and LLM assets
     - ``docs/``, ``pyfcstm/llm/``
     - User guides, generated resources, prompt-facing grammar guide, checksum discipline.
     - Runtime-only facts that are not validated against code or documented examples.

Why the model is central
------------------------

The DSL is intentionally compact, but its semantics require resolution:
transition targets need owning scopes, events need scope rules, lifecycle actions
need a concrete order, and forced or combo transitions expand into ordinary model
facts. Keeping that resolution in the model layer gives every downstream tool
the same source of truth.

This prevents three common drift problems:

* The simulator and templates disagree because each reinterprets DSL text.
* The diagram output shows syntax that the model importer would reject.
* Inspect reports and diagnostics describe a different graph than code
  generation consumes.

Command-facing flow
-------------------

The public CLI commands are thin orchestrators over the same pipeline:

.. list-table:: CLI flow
   :header-rows: 1

   * - Command
     - Reads DSL
     - Builds model
     - Downstream action
     - External dependency boundary
   * - ``simulate``
     - yes
     - yes
     - Runs ``SimulationRuntime``.
     - None for normal use.
   * - ``inspect``
     - yes
     - yes
     - Runs diagnostics and optional inspect-eligible verify checks.
     - SMT work is bounded by explicit inspect policy knobs.
   * - ``generate``
     - yes
     - yes
     - Runs ``StateMachineCodeRenderer`` with built-in or custom templates.
     - Target compilers are outside generation itself.
   * - ``plantuml``
     - yes
     - yes
     - Calls model PlantUML export and writes source text.
     - No renderer required.
   * - ``visualize``
     - yes, except ``--check``
     - yes, except ``--check``
     - Builds PlantUML source, then renders via ``plantumlcli``.
     - Java/jar or remote PlantUML service may be required.

Template asset split
--------------------

Built-in templates have two homes for different reasons:

* ``templates/`` is the editable repository source for maintainers.
* ``pyfcstm/template/`` contains packaged zip assets and ``index.json`` for
  installed users.

``make tpl`` refreshes packaged assets from repository sources. Tests and CLI
paths that exercise built-in templates should enter through packaged/public
surfaces so they match user behavior. This is why documentation distinguishes
maintainer template editing from normal ``pyfcstm generate --template python``
usage.

Diagnostics, verification, and inspect
--------------------------------------

Diagnostics and inspect output expose model facts and actionable messages. They
are intentionally detailed enough to guide humans and LLM-assisted repair, but
they remain bounded:

* Inspect always reports parse/model facts and diagnostics.
* Optional verify integration is explicit and policy-limited.
* Higher-cost or unbounded verification families are not silently run by an
  everyday inspect command.
* A diagnostic can point to a likely cause and source location; it does not
  replace simulation, target compilation, or generated-runtime tests.

Simulation and generated runtimes
---------------------------------

The Python simulator is the reference executable semantics for repository
alignment checks. Built-in runtime templates that claim parity should be tested
against simulator traces rather than merely compiling. That gives a concrete
contract for lifecycle ordering, hot starts, transition effects, and active-state
updates.

Generated target runtimes still have target-language concerns: API shape,
formatter stability, compiler/toolchain behavior, and integration hooks for
abstract actions. Those belong in template design and tests, not in the parser.

Visualization boundary
----------------------

PlantUML export belongs to the model because diagrams need resolved model facts.
Rendering belongs to the CLI and optional runtime environment because it depends
on Java, PlantUML jar files, remote services, file suffixes, caches, and desktop
viewer behavior.

That split is why ``plantuml`` is a source-export command and ``visualize`` is a
rendering command. A user can rely on source export without having a rendering
backend installed.

Generated asset boundaries
--------------------------

Several repository files are generated and should not be edited directly:

* ANTLR parser outputs under grammar output directories.
* Packaged template zip assets and template index files after template source
  changes.
* Documentation diagrams, demo outputs, and notebook result files generated by
  the documentation build rules.
* Generated API reference files produced by the RST generator.

The safe pattern is always: edit the source, run the generator, review the diff,
and record the verification command.

Where to go next
----------------

* Syntax and meaning: :doc:`../dsl_semantics/index`
* Runtime ordering: :doc:`../execution_semantics/index`
* Diagnostics boundaries: :doc:`../diagnostics/index`
* Template design: :doc:`../template_rendering/index`
* Grammar/editor coupling: :doc:`../grammar_tooling/index`
