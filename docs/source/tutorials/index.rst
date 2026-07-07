Tutorial roadmap
================

Use this page when you are learning pyfcstm for the first time and want a
guided path with visible progress after each page. The global sidebar lists each
tutorial directly; this roadmap only explains which sibling page to read next
and where to jump when a tutorial deliberately stops before reference-level
detail.

How to read tutorials
---------------------

Tutorials are for first success. Each page should give you a small working
result, then point to the task guide, explanation, or reference page that owns
broader coverage.

* If you are new to the project, follow the recommended path below.
* If you already have a concrete job, use :doc:`/how_to/index` instead.
* If you need exact options, syntax forms, report fields, or API objects, use
  :doc:`/reference/index`.
* If you want to understand why a behavior exists, use
  :doc:`/explanations/index`.

Recommended first path
----------------------

1. :doc:`quick_start/index`

   Run the shortest end-to-end path: install the command, execute a small
   machine, inspect it, generate code, and export a diagram. Read this first
   when you want proof that the toolchain works before learning every concept.

   **Outcome:** you know the core command flow and have seen the major outputs.

2. :doc:`dsl/index`

   Build the first model intentionally: states, transitions, variables, guards,
   lifecycle actions, and the difference between a learning example and the full
   DSL reference.

   **Outcome:** you can recognize the shape of a valid FCSTM file and know when
   to move from tutorial examples to :doc:`/reference/dsl/index`.

3. :doc:`simulation/index`

   Execute the model as behavior, not just text. Use this page to see cycles,
   active state changes, and the point where simulation details move into task
   guides and execution-semantics explanations.

   **Outcome:** you can run a small model and tell whether the active state path
   changes as expected.

4. :doc:`inspect/index`

   Ask pyfcstm what it understood. This tutorial focuses on what inspection and
   diagnostics can show, what kinds of messages they produce, and how those
   messages can guide a human or an LLM back to the source model.

   **Outcome:** you can produce an inspect report and decide whether to continue
   with a human-readable report, JSON, or a later diagnostics reference lookup.

5. :doc:`generation/index`

   Generate code through a packaged built-in template. This page is the learning
   path for the generation flow; template internals, configuration keys, and
   target-family contracts live outside the tutorial.

   **Outcome:** you can generate a runtime artifact without bypassing packaged
   template extraction.

6. :doc:`visualization/index`

   Export a diagram source or rendered image from the same model so you can
   explain its structure to another reader.

   **Outcome:** you can choose the first visualization command and know where to
   look up renderer-specific options.

Shortcuts by goal
-----------------

* **I only want to confirm the command works:** start with
  :doc:`quick_start/index`, then jump to :doc:`/how_to/cli_workflows/index`.
* **I need to author a real model:** read :doc:`dsl/index`, then use
  :doc:`/how_to/dsl/index` for tasks and :doc:`/reference/dsl/index` for exact
  syntax.
* **I need to debug model feedback:** read :doc:`inspect/index`, then use
  :doc:`/reference/inspect_report/index` and
  :doc:`/reference/diagnostics_codes/index` for exact fields and codes.
* **I need generated code:** read :doc:`generation/index`, then use
  :doc:`/how_to/generation/index`, :doc:`/how_to/templates/index`, and the
  template references.
* **I need a diagram:** read :doc:`visualization/index`, then use
  :doc:`/reference/visualization_options/index` for exact option behavior.

Where the tutorial path stops
-----------------------------

A tutorial should not become the only source of truth for every command option,
syntax branch, diagnostic code, or renderer setting. When you reach a boundary:

* task repetition belongs in :doc:`/how_to/index`;
* design reasoning belongs in :doc:`/explanations/index`;
* exact facts belong in :doc:`/reference/index`;
* Python object details belong in :doc:`/api_doc_en`.

Compatibility landing pages
---------------------------

Older tutorial URLs remain available as short landing pages. They preserve old
links and point to the current module that owns the content, but they are not
part of the main learning path anymore:

* :doc:`installation/index`
* :doc:`cli/index`
* :doc:`render/index`
* :doc:`grammar/index`
* :doc:`structure/index`
