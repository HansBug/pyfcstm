Inspect and Diagnostics
=======================

``pyfcstm inspect`` is the documentation and tooling entry point for asking
"what did this FCSTM model become?" It builds the same state-machine model used
by simulation, visualization, and code generation, then reports model structure,
metrics, derived graphs, combo-trigger provenance, and diagnostics.

Use it when you want to:

- review a model before generating target-language code;
- export a structured report for CI, editors, or downstream tools;
- give an LLM precise source spans and repair guidance;
- optionally run the subset of verify checks that are safe for automatic
  inspection.

It is not a replacement for simulation, target hardware tests, or a complete
formal-verification workflow. Invalid DSL input is still a CLI parse/model-load
failure, not a successful JSON inspect report.

A diagnostic-heavy example
--------------------------

The examples below use a deliberately noisy model. It contains a constant
``during`` assignment, a duplicate combo event, an implied combo guard, leaf
states with no exits, unreferenced variables, and a C/C++ deployment-profile
numeric risk.

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :caption: inspect_diagnostics.fcstm

Human output is the default
---------------------------

For local reading, run ``inspect`` without ``--format``:

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm

The human renderer summarizes the model first, then prints checker-style
diagnostics with source excerpts, provenance, suggested actions, and do-not
notes:

.. literalinclude:: inspect_human.demo.sh.txt
   :language: text
   :caption: Human inspect output excerpt
   :lines: 1-40

Use ``--color always`` / ``--color never`` only for the human renderer. Machine
formats never contain ANSI color escapes.

Output formats and files
------------------------

``-o`` chooses where to write the report. It does not choose the format. Always
pass ``--format`` explicitly when a script expects JSON or an LLM-oriented
report.

.. list-table:: Inspect output formats
   :header-rows: 1

   * - Format
     - Intended consumer
     - Notes
   * - ``human``
     - People reading terminal output
     - Default format; source excerpts, repair guidance, and optional ANSI color.
   * - ``json``
     - CI, editors, and programmatic integrations
     - Full report matching ``inspect_model(model).to_json()``.
   * - ``llm-json``
     - LLM repair loops that prefer structured data
     - Stable schema ``pyfcstm.inspect.llm.v1`` with summarized repair fields.
   * - ``llm-md``
     - LLM prompts and issue comments
     - Markdown version of the same LLM-oriented repair contract.

Typical commands:

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o report.json
   pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json -o report.llm.json
   pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-md -o report.llm.md

The generated demo confirms the important shapes:

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: Format summary generated from real inspect output
   :lines: 1-12

The default JSON diagnostic object currently has these top-level keys:
``code``, ``severity``, ``message``, ``span``, and ``refs``. Some diagnostics
place a suggested edit under ``refs.suggested_fix``; it is not a top-level JSON
diagnostic field. Likewise, ``for_llm`` is registry metadata used to render the
LLM formats, not a field emitted by ``--format json``.

The LLM formats expose repair-oriented fields such as ``summary``,
``recommended_actions``, ``do_not``, and ``repair_guidance``:

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: LLM report shape generated from real inspect output
   :lines: 23-33

If a file suffix looks suspicious, the CLI warns but still honors the requested
format:

.. literalinclude:: inspect_cli_edges.demo.sh.txt
   :language: text
   :caption: Color and suffix boundary checks

Invalid input is a CLI error
----------------------------

Syntax errors and model-load failures are reported as non-zero CLI failures.
Even if the user passed ``--format json``, inspect does not invent a successful
``diagnostics[]`` payload for an input that could not be parsed or loaded.

.. literalinclude:: inspect_invalid.demo.sh.txt
   :language: text
   :caption: Invalid input boundary

This boundary is useful in automation: parse/model-load failures should stop the
pipeline, while diagnostics on a valid model can be triaged by severity and
code.

Combo-trigger provenance
------------------------

Combo triggers are expanded into generated pseudo-state chains during model
construction. The full JSON report includes ``combo_transitions`` and
``combo_origins`` so downstream tools can connect generated edges back to the
author-written trigger terms.

In the example model:

.. code-block:: fcstm

   Active -> ComboDone :: Confirm + Confirm;
   Active -> Done : [ready > 0] + [ready > -1] effect {
       ratio = ratio + 1.0;
   };

``inspect`` reports source-level combo warnings instead of making users debug
only generated pseudo-state names:

- ``W_COMBO_DUPLICATE_EVENT`` points at the second ``Confirm`` and records the
  first term in ``refs.first_term_span``.
- ``W_COMBO_GUARD_PREFIX_IMPLIED`` points at ``[ready > -1]`` and links the
  decisive earlier guard through ``refs.prior_term_span``.
- The JSON transition records carry combo origin refs, while generated pseudo
  state names remain visible for tooling and visualization.

These diagnostics describe the authored combo trigger. They are not warnings
about ``during before`` aspects firing inside combo relay pseudo states.

C/C++ deployment-profile numeric warnings
-----------------------------------------

Numeric warnings are target-profile warnings. For example,
``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` is about the default C-family runtime
profile using a fixed-width generated integer type. It is not a
language-independent FCSTM model error, and it should not be presented as proof
that a Python generated runtime has the same overflow behavior.

The JSON ``refs`` make the scope explicit:

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: Numeric warning target scope
   :lines: 9-11

Treat these warnings as deployment review items for C/C++ / ``c`` / ``c_poll`` /
``cpp`` / ``cpp_poll`` targets. If the target is Python, the same fixed-width
integer carrying risk usually does not apply, although the model may still have
other design issues worth reviewing.

Optional verify-backed checks
-----------------------------

By default, ``inspect`` runs static diagnostics only. Add ``--enable-verify``
when you want the inspect adapter to run verify algorithms that fit the
automatic-inspection budget:

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json \
     --enable-verify --max-complexity-tier smt_linear --smt-timeout-ms 1000

The adapter deliberately rejects knobs that require a more explicit verification
plan, such as ``bmc_search`` and the ``k_unrollings`` call-count policies:

.. literalinclude:: inspect_verify_policy.demo.sh.txt
   :language: text
   :caption: Forbidden verify policy examples

Use a dedicated verify workflow when you need bounded-model checking, custom
unrolling depth, or a proof budget that should be reviewed independently from a
fast inspect pass.

Using inspect with LLM-assisted repair
--------------------------------------

A practical repair loop is:

1. Run ``pyfcstm inspect`` for a readable overview.
2. Run ``pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json`` or
   ``--format llm-md`` and pass the report to the assistant.
3. Ask for the smallest source edit that preserves the apparent intent.
4. Re-run ``inspect`` and the relevant tests after applying the edit.

The LLM report is good evidence, not an automatic proof. Diagnostics can include
heuristic design warnings, deployment-profile warnings, and verify-backed
results with different strengths, so always rerun tools after editing.

Where to go next
----------------

- :doc:`/tutorials/quick_start/index` shows the short happy path.
- :doc:`/tutorials/simulation/index` explains runtime execution semantics.
- :doc:`/tutorials/generation/index` shows how inspected models feed built-in
  templates.
- :doc:`/tutorials/dsl/index` documents combo triggers and pseudo-state syntax
  in the DSL reference.
