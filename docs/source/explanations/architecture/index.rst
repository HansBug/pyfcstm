.. _sec-explanations-architecture:

Architecture explanation
========================

pyfcstm is organized around a clear pipeline: DSL text becomes AST nodes, AST
nodes become a validated state-machine model, and that model can be simulated,
inspected, verified, visualized, or rendered into target-language code.

Main pipeline
-------------

.. figure:: structure.puml.svg

   High-level repository pipeline.

The main layers are:

* **DSL parsing** under ``pyfcstm/dsl/``. ANTLR grammar files define syntax, and
  listener code builds AST nodes.
* **Model import** under ``pyfcstm/model/``. The importer resolves states,
  transitions, events, actions, variables, and diagnostics into a semantic
  state-machine model.
* **Runtime tools** under ``pyfcstm/simulate/`` and ``pyfcstm/entry/``. These
  provide interactive and batch simulation, CLI entry points, inspect output,
  and PlantUML export.
* **Rendering** under ``pyfcstm/render/`` and packaged templates under
  ``pyfcstm/template/``. The renderer consumes the model and template assets;
  it does not hard-code a target runtime API.
* **Analysis** under ``pyfcstm/solver/`` and verify/inspect integrations. These
  translate model facts into diagnostics and reachability-style checks.
* **Documentation and LLM guide assets** under ``docs/`` and ``pyfcstm/llm/``.
  The prompt-facing grammar guide is a packaged asset with a checksum.

Current built-in-template shape
-------------------------------

Built-in templates are current behavior, not a planned feature. Editable source
assets live under ``templates/``. Packaged distributable assets live under
``pyfcstm/template/`` and are refreshed with ``make tpl``. The CLI path
``pyfcstm generate --template <name>`` extracts a packaged asset, then uses the
same renderer as a custom template directory.

This split gives maintainers a source tree while giving users a stable named
entry point.

Inspection and diagnostics
--------------------------

Inspect and diagnostics are part of the model-facing toolchain. They provide
structured facts and detailed messages that can guide humans or LLM-assisted
repair. They do not replace runtime simulation or generated-code validation;
they expose what the parser and model importer know about a machine.

Simulation and execution semantics
----------------------------------

The simulator is the reference executable model for Python-side semantic checks.
Template runtimes that claim simulator parity should be tested against simulator
traces. Execution details such as lifecycle action order, hot start behavior,
and composite-state entry semantics belong in
:doc:`../execution_semantics/index`.

Maintenance boundaries
----------------------

* Generated grammar outputs should be regenerated, not hand-edited.
* Generated documentation should be produced by the documented build commands,
  not edited directly.
* Built-in templates should be changed in repository template sources and then
  repackaged.
* Unit tests under ``test/`` should target production ``pyfcstm`` behavior and
  stay independent from JavaScript test trees.

These boundaries keep the repository explainable and make each generated asset
reproducible.
