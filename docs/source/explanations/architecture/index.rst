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

Worked trace: one source, several kinds of evidence
---------------------------------------------------

Consider the quick-start ``traffic_light.fcstm`` file. The same source text can
produce several different artifacts, but each artifact proves a different thing.

.. list-table:: Trace from source to artifact
   :header-rows: 1

   * - Step
     - Component boundary
     - Example command or object
     - What the evidence proves
     - What it does not prove
   * - Parse text.
     - ``pyfcstm.dsl``
     - ``pyfcstm inspect -i traffic_light.fcstm`` starts by parsing the file.
     - The file is syntactically valid FCSTM.
     - It does not prove target runtime behavior.
   * - Import semantic model.
     - ``pyfcstm.model``
     - The inspect report names root ``TrafficLight`` and counts 4 states / 4 transitions.
     - The model importer accepted names, hierarchy, variables, and transitions.
     - It does not render an image or compile generated code.
   * - Execute reference semantics.
     - ``pyfcstm.simulate``
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``.
     - Cold entry and one cycle produce a concrete active-state trace.
     - It does not prove every generated target template matches the simulator.
   * - Inspect structured facts.
     - ``pyfcstm.diagnostics`` and inspect adapters
     - ``pyfcstm inspect -i traffic_light.fcstm --format json``.
     - Metrics and diagnostics are available for scripts and LLM repair workflows.
     - It does not run hidden unbounded verification.
   * - Export diagram source.
     - ``model.to_plantuml``
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``.
     - The model can be represented as deterministic PlantUML source.
     - It does not prove a renderer is installed.
   * - Render a diagram.
     - ``pyfcstm visualize`` plus external backend
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``.
     - A configured PlantUML backend can turn the source into an image.
     - It does not prove the model semantics are correct beyond the source used.
   * - Generate runtime files.
     - ``pyfcstm.render`` and packaged templates
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``.
     - The template can consume the model and write target files.
     - It does not by itself prove generated runtime parity; alignment tests own that claim.

Command boundary trace
----------------------

The same ``traffic_light.fcstm`` input can pass through several command paths.
The paths are related, but each proves a different boundary. This trace is the
reason the documentation keeps CLI recipes, visualization recipes, and reference
facts separate.

.. list-table:: Boundary trace from one input file
   :header-rows: 1

   * - Step
     - Command or API layer
     - Artifact
     - What the artifact proves
     - What it does not prove
   * - Parse and import
     - ``load_state_machine_from_file`` via command entry points
     - In-memory semantic model
     - The DSL can be decoded, parsed, scoped, and validated as a state machine.
     - It does not prove any renderer, template, or external tool is installed.
   * - Inspect facts
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - Human, JSON, or LLM-oriented report
     - Diagnostics and metrics describe the model facts seen by pyfcstm.
     - It does not execute target-language code.
   * - Simulate behavior
     - ``pyfcstm simulate -i traffic_light.fcstm -e "cycle; current"``
     - Simulator transcript
     - The Python simulator can execute the selected cycle path.
     - It does not prove generated C/C++/Python runtime parity by itself.
   * - Export diagram source
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - PlantUML text
     - The model can be represented as textual diagram source.
     - It does not prove Java, PlantUML, remote rendering, or visual readability.
   * - Render a diagram
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - SVG, PNG, or PDF artifact
     - The selected rendering backend can turn the PlantUML source into an artifact.
     - It does not prove the chosen detail level is the clearest explanation; visual review owns that.
   * - Generate runtime files
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - Generated runtime tree
     - A packaged template can consume the model and write target files.
     - It does not prove native toolchains or downstream integration tests have run.

A failure at a later boundary should not be fixed by guessing at an earlier
layer. For example, a remote PlantUML outage is a visualization-environment
problem, not a DSL parser problem. Conversely, a model-validation error should
be fixed in the DSL/model path before retrying templates or renderers.

Counterexamples that keep the boundaries honest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* A successful ``plantuml`` command only proves source export. It can succeed on
  a machine with no Java, no PlantUML jar, and no network renderer.
* A successful ``visualize`` command proves renderer availability for that run,
  but the remote mode may send PlantUML source outside the local machine.
* A successful ``generate`` command proves rendering completed. It does not prove
  that a C/C++ compiler is installed or that a native executable has been tested.
* A clean inspect report is useful for humans and LLM repair prompts, but it is
  not a promise that every possible runtime path has been explored.

Visual evidence review
~~~~~~~~~~~~~~~~~~~~~~

The architecture figure above was regenerated from ``structure.puml`` for this
PR-Q hardening pass. It is intended to prove three relationships only:

1. all command-facing features share the semantic model boundary;
2. PlantUML source export and image rendering are separate layers;
3. source templates and packaged templates have different maintenance roles.

It is not an API map and it is not a substitute for the generated API reference.
When this figure changes, rebuild the SVG/PNG pair and inspect the rendered HTML
so that labels remain readable at documentation width.


Where to go next
----------------

* Syntax and meaning: :doc:`../dsl_semantics/index`
* Runtime ordering: :doc:`../execution_semantics/index`
* Diagnostics boundaries: :doc:`../diagnostics/index`
* Template design: :doc:`../template_rendering/index`
* Grammar/editor coupling: :doc:`../grammar_tooling/index`
