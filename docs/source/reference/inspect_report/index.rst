.. _sec-reference-inspect-report:

Inspect report reference
========================

``pyfcstm inspect`` emits human output by default and structured output when
``--format`` is set.

Formats
-------

.. list-table:: Inspect formats
   :header-rows: 1

   * - Format
     - Intended consumer
     - Notes
   * - ``human``
     - People reading terminal output.
     - Default format; includes source excerpts and optional ANSI color.
   * - ``json``
     - CI, editors, and programmatic integrations.
     - Full report matching the model inspect payload.
   * - ``llm-json``
     - LLM repair loops that prefer structured data.
     - Stable schema ``pyfcstm.inspect.llm.v1`` with summarized repair fields.
   * - ``llm-md``
     - LLM prompts and issue comments.
     - Markdown version of the same LLM-oriented repair contract.

JSON summary fields
-------------------

The full JSON report includes model identity, metrics, derived graph data,
combo provenance, and diagnostics. A real demo currently reports:

.. literalinclude:: ../../tutorials/inspect/inspect_formats.demo.sh.txt
   :language: text
   :lines: 1-8

Diagnostic object keys
----------------------

Default JSON diagnostic objects currently expose these top-level keys:

.. list-table:: Diagnostic object keys
   :header-rows: 1

   * - Key
     - Meaning
   * - ``code``
     - Stable diagnostic code, such as ``W_COMBO_DUPLICATE_EVENT``.
   * - ``severity``
     - ``error``, ``warning``, or ``info``.
   * - ``message``
     - Human-readable diagnostic message.
   * - ``span``
     - Source location when available.
   * - ``refs``
     - Code-specific structured references and repair hints.

Some diagnostics place a suggested edit under ``refs.suggested_fix``. It is not
a top-level diagnostic field. Likewise, ``for_llm`` is registry metadata used to
render LLM formats, not a field emitted by ``--format json``.

LLM report fields
-----------------

LLM formats expose repair-oriented fields such as ``summary``,
``recommended_actions``, ``do_not``, and ``repair_guidance``:

.. literalinclude:: ../../tutorials/inspect/inspect_formats.demo.sh.txt
   :language: text
   :lines: 14-19

Invalid input boundary
----------------------

A parse or model-load failure is a CLI error. Inspect does not emit a successful
JSON payload for invalid input.
