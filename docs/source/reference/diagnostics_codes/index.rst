.. _sec-reference-diagnostics-codes:

Diagnostics code reference
==========================

Diagnostic codes are stable identifiers used by ``pyfcstm inspect``, CI filters,
IDE integrations, and LLM repair prompts. The authoritative registry is the
loaded ``pyfcstm.diagnostics.codes.CODE_REGISTRY`` object. Raw
``codes.yaml`` entries may omit ``emit_tier`` or ``capability``; the loader fills
those defaults as ``static_pipeline`` and ``pure_static``.

This page is a reference, not a tutorial. Use it when you already have a
``code`` value from inspect output and need to know what it means, which report
fields are stable, which pipeline can emit it, and how to repair or explain it.

How to read one diagnostic
--------------------------

A diagnostic object combines a stable identifier with source-location and repair
context:

.. list-table:: Diagnostic object keys
   :header-rows: 1
   :widths: 22 78

   * - Key
     - Meaning
   * - ``code``
     - Stable identifier such as ``W_COMBO_DUPLICATE_EVENT``.
   * - ``severity``
     - ``error`` blocks model construction; ``warning`` flags risky or suspicious design; ``info`` records a non-blocking observation.
   * - ``message``
     - Human-readable short explanation.
   * - ``span``
     - Source range when the analyzer can point to a concrete object.
   * - ``refs``
     - Structured payload used by tools and LLM repair prompts. Each code below lists the expected fields.
   * - ``suggested_fix``
     - Optional edit metadata when the registry can describe a safe local edit shape.

Emission tiers
--------------

.. list-table:: Emit tiers
   :header-rows: 1
   :widths: 24 76

   * - Tier
     - Meaning
   * - ``static_pipeline``
     - Produced by the default static inspect/model diagnostics path.
   * - ``verify_pipeline``
     - Produced only when bounded inspect-eligible verify algorithms run, normally through ``--enable-verify``.
   * - ``lookup_api``
     - Produced by explicit resolver APIs, not by default static inspect output.
   * - ``partial_static_pipeline``
     - Registry contract exists, but not every frontend/backend currently emits it.
   * - ``catalog_only``
     - Compatibility contract only; current normal pyfcstm paths should not emit it.

Example kinds
-------------

Each code below has at least three visible examples or boundary examples. The
source also carries hidden ``diagnostics-example`` markers so
``python tools/check_diagnostics_reference_docs.py --check`` can verify coverage.

.. list-table:: Example kind labels
   :header-rows: 1
   :widths: 24 76

   * - Kind
     - Meaning
   * - ``repro_cli``
     - Intended to be reproducible as a successful inspect report; use
       ``pyfcstm inspect -i <file> --format json`` and read ``diagnostics[]``.
   * - ``cli_error``
     - Intended to be reproducible as a controlled CLI/model-validation error.
       Current inspect formats exit non-zero before producing a successful JSON
       report, so assert stderr and exit status rather than ``diagnostics[]``.
   * - ``repro_api``
     - Intended to be reproducible through an explicit Python API call.
   * - ``verify_opt_in``
     - Requires optional verify integration and may depend on solver policy or timeout.
   * - ``boundary_only``
     - Documents a repair or anti-pattern boundary rather than a separate CLI trigger.
   * - ``compatibility_only``
     - Documents historical or cross-version behavior that current normal paths should not emit.

Machine coverage check
----------------------

Run this repository-local maintenance check after editing this page or the code
registry:

.. code-block:: bash

   python tools/check_diagnostics_reference_docs.py --check

The check verifies code-set, severity, emit tier, capability, span object,
``refs`` schema, bilingual coverage, per-code reproduction-boundary markers, and
per-code example-marker counts. It does not prove that examples are semantically
distinct; reviewer sampling remains part of the PR acceptance gate.

.. include:: _code_catalog_en.rst.inc
