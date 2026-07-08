Tutorial roadmap
================

Use this page when you are learning pyfcstm for the first time and want a
small, observable success after each step. The global sidebar lists the tutorial
pages directly; this roadmap is only the sibling guide that explains which page
to read next, why that page belongs in the tutorial path, and where to leave the
path when you need task recipes, explanations, or reference facts.

Role: this page is the Tutorial router for first-success learning. It gives a
safe reading order, identifies the result each tutorial should produce, and
keeps beginners from falling into reference-level detail too early.

Non-goals: this page is not the complete DSL reference, not a CLI option table,
not the inspect schema, not a generated-template contract, and not the API map.
When you need exact facts, use :doc:`/reference/index`; when you already know
the task, use :doc:`/how_to/index`; when you need reasoning, use
:doc:`/explanations/index`.

How to read tutorial pages
--------------------------

Tutorial pages should teach one primary success path. They intentionally stop
before every option, every edge case, or every diagnostic code. A tutorial is
acceptable when it gives you an input, a command or short code fragment, visible
output, and a next link that tells you where broader coverage lives.

The strongest signal that you should leave Tutorials is that your question has
changed from "what is the first working path?" to "how do I repeat this in my
own project?" or "what is the exact legal form?". At that point, the sibling
areas are more useful than another tour.

New-user path
-------------

Follow this route if you have not used pyfcstm before.

1. Start with :doc:`quick_start/index` to prove that the installed command can
   simulate, inspect, generate, and export from one small file.
2. Read :doc:`dsl/index` to understand the source file shape behind that first
   run.
3. Choose the first feedback loop: :doc:`simulation/index` if you want runtime
   behavior, or :doc:`inspect/index` if you want model structure and diagnostic
   feedback.
4. Read :doc:`generation/index` when you want generated Python output from the
   same model.
5. Finish the first learning loop with :doc:`visualization/index` so the model
   can be explained with a diagram.

Experienced-user path
---------------------

Use this route if you already know the project shape and only need the tutorial
that refreshes one workflow.

* Already have an FCSTM file but do not trust it yet: jump to
  :doc:`inspect/index` and then to :doc:`/reference/diagnostics_codes/index`.
* Already have a valid model but need behavior evidence: jump to
  :doc:`simulation/index` and then to :doc:`/how_to/simulation/index`.
* Already know the model and need output files: jump to :doc:`generation/index`
  or :doc:`visualization/index` and then to the matching how-to page.
* Already need exact syntax, command options, or schema fields: skip tutorials
  and start at :doc:`/reference/index`.

Maintainer path
---------------

Use this route when reviewing or extending tutorial material.

* Confirm each tutorial has a realistic starting state and a single primary
  success path.
* Confirm each command or code block has a short observable result rather than a
  long opaque script.
* Confirm every tutorial states where it stops and links to the how-to,
  explanation, or reference page that owns the remaining depth.
* Confirm Chinese and English tutorial pages teach the same capability and expose
  the same risk boundaries, even when the prose is not word-for-word identical.

Reader completion signals
-------------------------

After a tutorial, readers should be able to answer three questions.

* What input file did I just run or read?
* What did the output, state change, report, or diagram prove?
* Where should I leave the tutorial when I need to repeat, look up, or explain
  the same behavior?

If those questions are still unclear, the tutorial needs a shorter output
excerpt, a clearer result explanation, or a more explicit next link. If those
questions are already clear, do not move reference tables into the tutorial;
send the reader to the matching how-to guide, explanation, or reference page.

A tutorial may stay compact, but it must make the completed learning loop and
the next document role visible.

Sibling tutorial cards
----------------------

Quick start: :doc:`quick_start/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: Python and the ``pyfcstm`` command are available, or you are ready
to follow :doc:`/how_to/installation/index` first.

Outcome: you run the shortest end-to-end command chain over one traffic-light
model and see simulation, inspect, generation, and PlantUML output families.

Non-goal: it does not explain every command option, every generated file, or the
semantics behind state-machine execution.

Next step: read :doc:`dsl/index` when you want to understand the input file, or
jump to :doc:`/how_to/cli_workflows/index` when you only need repeatable command
recipes.

DSL tutorial: :doc:`dsl/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have seen a tiny FCSTM file in the quick start and can edit a
plain text file.

Outcome: you can build a small model with states, transitions, guards,
lifecycle actions, and one deliberate repair step.

Non-goal: it is not the exhaustive grammar; legal forms, illegal forms, sugar
expansion, and diagnostics live in :doc:`/reference/dsl/index`.

Next step: read :doc:`simulation/index` to execute the model, or
:doc:`/explanations/dsl_semantics/index` to understand why those constructs mean
what they mean.

Simulation tutorial: :doc:`simulation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a valid sample model and want to observe active-state
movement rather than only parse text.

Outcome: you can run a batch transcript or a short Python runtime loop and
recognize the active path after cycles or events.

Non-goal: it does not catalog every REPL command, display setting, history
format, or hot-start boundary.

Next step: use :doc:`/how_to/simulation/index` for repeatable tasks and
:doc:`/reference/simulation/index` for exact command and API facts.

Inspect tutorial: :doc:`inspect/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a model and want pyfcstm to report what it parsed, what
it inferred, and which diagnostics can guide repair.

Outcome: you can produce human, JSON, and LLM-oriented inspect outputs and know
why diagnostics can guide a human or an LLM back to source spans.

Non-goal: it does not enumerate every JSON field, diagnostic code, severity, or
optional verification boundary.

Next step: use :doc:`/how_to/inspect/index` for triage recipes, then
:doc:`/reference/inspect_report/index` and
:doc:`/reference/diagnostics_codes/index` for exact lookup.

Generation tutorial: :doc:`generation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a valid model and want the packaged built-in Python
template to produce files without hand-editing template internals.

Outcome: you can run ``pyfcstm generate --template python`` and inspect the
first generated runtime artifacts.

Non-goal: it does not teach custom template authoring, every built-in target
contract, formatter policy, or renderer internals.

Next step: use :doc:`/how_to/generation/index` for target-specific recipes,
:doc:`/how_to/templates/index` for authoring, and
:doc:`/explanations/template_rendering/index` for the rendering pipeline.

Visualization tutorial: :doc:`visualization/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a valid model and want a diagram source or rendered
artifact that explains structure to another reader.

Outcome: you can export PlantUML source, understand what the rendered example
proves, and try the first detail presets.

Non-goal: it does not list every visualization option, renderer backend, suffix
rule, or headless/CI boundary.

Next step: use :doc:`/how_to/visualization/index` for diagram tasks and
:doc:`/reference/visualization_options/index` for exact option behavior.

Where the tutorial path stops
-----------------------------

Leave Tutorials deliberately when you need breadth or precision. Repeated
operations belong in How-to Guides, design reasoning belongs in Explanations,
and exact facts belong in Reference. That split keeps the first-success path
short while still giving each capability a deeper owner.

Compatibility landing pages
---------------------------

The following old tutorial URLs remain reachable as compatibility landing notes.
They protect old links and point to the current owner pages, but they are not
part of the six sibling tutorial cards above.

* :doc:`installation/index`
* :doc:`cli/index`
* :doc:`grammar/index`
* :doc:`render/index`
* :doc:`structure/index`
