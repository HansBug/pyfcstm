Explanation map
===============

Use this page when you need the reasoning behind pyfcstm behavior. The global
sidebar lists each explanation directly; this map gives a conceptual reading
order and shows which questions belong here instead of in tutorials, task
guides, or reference tables.

What explanations promise
-------------------------

Explanations answer why the system is shaped this way: semantic ordering,
architecture boundaries, design trade-offs, and the risks behind supported or
unsupported forms. They do not replace runnable tutorials, step-by-step recipes,
or exact lookup pages.

Conceptual reading route
------------------------

1. :doc:`architecture/index`

   Start here when you need the whole pipeline: DSL text, AST construction,
   model import, inspection, rendering, simulation, verification, and generated
   outputs.

   **Question answered:** how the main package layers fit together, and where a
   behavior should be implemented or documented.

2. :doc:`dsl_semantics/index`

   Read this when syntax alone is not enough. It owns the meaning of states,
   transitions, composite entry, lifecycle actions, event scopes, forced and
   combo transitions, and other modeling semantics.

   **Question answered:** what a model means after parsing and import.

3. :doc:`execution_semantics/index`

   Read this when the order of runtime behavior matters: entering composites,
   during actions, transition effects, exits, hot starts, rollback, pseudo relay
   states, and simulator alignment.

   **Question answered:** why a cycle produces a particular active-state and
   variable trace.

4. :doc:`diagnostics/index`

   Read this when you need to understand the boundary between static inspection,
   diagnostics, optional verification, and LLM-oriented feedback.

   **Question answered:** what kind of problem a diagnostic can prove, warn
   about, or merely describe.

5. :doc:`template_rendering/index`

   Read this when generation behavior depends on the renderer, packaged
   templates, expression rendering, statement rendering, or target-language
   runtime contracts.

   **Question answered:** why code generation goes through configured templates
   and packaged assets instead of ad-hoc file copying.

6. :doc:`grammar_tooling/index`

   Read this when parser grammar, syntax highlighting, and editor tooling must
   remain synchronized.

   **Question answered:** why changing grammar is more than editing one ANTLR
   file.

Choose by question
------------------

* **Where should a feature live?** Read :doc:`architecture/index` first.
* **What does this DSL form mean?** Read :doc:`dsl_semantics/index`, then look
  up exact syntax in :doc:`/reference/dsl/index`.
* **Why did simulation run actions in this order?** Read
  :doc:`execution_semantics/index`, then run a task from
  :doc:`/how_to/simulation/index`.
* **Why did inspect report this issue?** Read :doc:`diagnostics/index`, then
  look up fields and codes in :doc:`/reference/inspect_report/index` and
  :doc:`/reference/diagnostics_codes/index`.
* **Why did generated code look like this?** Read
  :doc:`template_rendering/index`, then check template facts in
  :doc:`/reference/builtin_templates/index` and
  :doc:`/reference/template_config/index`.
* **Why do grammar changes touch editor files?** Read
  :doc:`grammar_tooling/index`, then follow
  :doc:`/how_to/grammar_editor/index`.

Where explanations stop
-----------------------

An explanation may include traces, diagrams, or short examples when they clarify
semantics. It should not become the only place to find command options,
reference tables, or copy-paste recipes. Use:

* :doc:`/tutorials/index` for first-success learning;
* :doc:`/how_to/index` for concrete tasks;
* :doc:`/reference/index` for exact facts;
* :doc:`/api_doc_en` for generated Python API structure.
