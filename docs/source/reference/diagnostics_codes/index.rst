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
     - Produced only when closed, policy-budgeted structural or SMT-local verify algorithms run, normally through ``--enable-verify``.
   * - ``lookup_api``
     - Produced by explicit resolver APIs, not by default static inspect output.
   * - ``partial_static_pipeline``
     - Registry contract exists, but not every frontend/backend currently emits it.
   * - ``catalog_only``
     - Compatibility contract only; current normal pyfcstm paths should not emit it.

Deprecated compatibility aliases
---------------------------------

The historical ``W_DEADLOCK_LEAF`` spelling remains present in
``CODE_REGISTRY`` as a deprecated alias of
``W_LEAF_NO_OUTGOING_TRANSITION``. New analyzers emit only the canonical
spelling; consumers that read historical JSON or LLM reports can resolve the
old spelling through ``resolve_diagnostic_code`` and
``canonicalize_diagnostic_code``. The alias is scheduled for removal in
version ``1.0.0`` and its schedule is checked by ``make deprecation_check``.

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

.. _diag-region-examples:

Region diagnostics in a terminal
--------------------------------

The catalog below describes each code. This section runs the region-related codes on the models next to this page, so every message and exit status is the real one. The models that are rejected on purpose use the extension ``.fcstm.txt`` and are shown either in the catalog entries of their codes or just above the commands that run them; they are negative examples, do not copy them as starting points.

``E_REGION_STRUCTURE`` is reported by ``pyfcstm inspect`` as one line that carries the line number of the offending construct. The repaired model and the model with history outside the region subtree are accepted; the full report is long, so only the ``regions:`` line of its summary is kept here.

.. literalinclude:: region_diag_history_boundary.fcstm.txt
   :language: fcstm
   :caption: region_diag_history_boundary.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_empty_region_fixed.fcstm
   :language: fcstm
   :caption: region_diag_empty_region_fixed.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_diag_empty_region.fcstm.txt
   Invalid state machine model in region_diag_empty_region.fcstm.txt: Invalid region structure at Root.Empty (empty_region). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_history_boundary.fcstm.txt
   Invalid state machine model in region_diag_history_boundary.fcstm.txt: Invalid region structure at Root.P (history_boundary). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_empty_region_fixed.fcstm
   ...
     regions: 1
   ...
   $ pyfcstm inspect -i region_diag_history_outside.fcstm
   ...
     regions: 2
   ...

The reasons ``mixed_children`` and ``owner_statements`` cannot be written in text: the parser refuses the text before the model is built, so the user sees a syntax error. They are reachable only by building the syntax tree with the public node classes.

.. literalinclude:: region_diag_mixed_children.fcstm.txt
   :language: fcstm
   :caption: region_diag_mixed_children.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_owner_transition.fcstm.txt
   :language: fcstm
   :caption: region_diag_owner_transition.fcstm.txt (negative example, do not copy)

.. code-block:: console

   $ pyfcstm inspect -i region_diag_mixed_children.fcstm.txt
   Failed to parse input DSL file region_diag_mixed_children.fcstm.txt: Found 3 errors during parsing:
   Error 1: Syntax error at line 3, column 4, near 'region': Unexpected token 'region'
   ...
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_owner_transition.fcstm.txt
   Failed to parse input DSL file region_diag_owner_transition.fcstm.txt: Found 1 errors during parsing:
   Error 1: Syntax error at line 3, column 4, near '[*]': Unexpected token '[*]'
   $ echo $?
   1

``E_DUPLICATE_REGION`` is per owner. The first model declares ``A`` twice under ``Root`` and is rejected; the second declares ``A`` under both ``Root.P`` and ``Root.Q`` and is accepted with three regions.

.. code-block:: console

   $ pyfcstm inspect -i region_diag_duplicate.fcstm.txt
   Invalid state machine model in region_diag_duplicate.fcstm.txt: Duplicate region 'A' in Root. (line 3)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_same_name_two_owners.fcstm
   ...
     regions: 3
   ...

``E_ACTIVE_QUERY_TARGET`` has one reason per rejected shape of query. ``region_diag_active_ok.fcstm`` shows the accepted root-relative form ``active("/B")``.

.. literalinclude:: region_diag_active_invalid_path.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_invalid_path.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_region.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_region.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_pseudo.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_pseudo.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_ok.fcstm
   :language: fcstm
   :caption: region_diag_active_ok.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_diag_active_not_found.fcstm.txt
   Invalid state machine model in region_diag_active_not_found.fcstm.txt: Invalid active query 'Root.Unknown' (not_found). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_invalid_path.fcstm.txt
   Invalid state machine model in region_diag_active_invalid_path.fcstm.txt: Invalid active query 'Other.A' (invalid_path). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_region.fcstm.txt
   Invalid state machine model in region_diag_active_region.fcstm.txt: Invalid active query 'Root.P.R' (region). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_pseudo.fcstm.txt
   Invalid state machine model in region_diag_active_pseudo.fcstm.txt: Invalid active query 'Root.G' (pseudo). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_ok.fcstm
   [WARN] FCSTM Inspect Report: region_diag_active_ok.fcstm
   ...

The reason ``initializer`` is also unreachable from text: a persistent variable initializer that calls ``active(...)`` is a syntax error.

.. code-block:: console

   $ pyfcstm inspect -i region_diag_active_initializer.fcstm.txt
   Failed to parse input DSL file region_diag_active_initializer.fcstm.txt: Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 16, near 'active': Unexpected token 'active'
   ...
   $ echo $?
   1

A structured diagnostic carries the span of the offending construct and the ``refs`` payload of its code. Model construction collects them when it is asked to collect instead of raising. For the duplicate region, ``refs`` also holds ``previous_span``, the position of the first declaration.

.. testcode::

   from pathlib import Path

   from pyfcstm.dsl import parse_with_grammar_entry
   from pyfcstm.model import parse_dsl_node_to_state_machine

   names = (
       "region_diag_empty_region.fcstm.txt",
       "region_diag_duplicate.fcstm.txt",
       "region_diag_active_not_found.fcstm.txt",
   )
   for name in names:
       ast = parse_with_grammar_entry(Path(name).read_text(), "state_machine_dsl")
       model, diagnostics = parse_dsl_node_to_state_machine(ast, collect=True)
       for item in diagnostics:
           print(item.code, item.span)
           print(sorted(item.refs.items()))

.. testoutput::

   E_REGION_STRUCTURE Span(line=2, column=5, end_line=2, end_column=20)
   [('namespace_path', 'Root.Empty'), ('reason', 'empty_region'), ('source_path', None)]
   E_DUPLICATE_REGION Span(line=3, column=5, end_line=3, end_column=42)
   [('owner_path', 'Root'), ('previous_span', Span(line=2, column=5, end_line=2, end_column=42)), ('region_name', 'A'), ('source_path', None)]
   E_ACTIVE_QUERY_TARGET Span(line=2, column=28, end_line=2, end_column=50)
   [('reason', 'not_found'), ('source_path', None), ('state_path', 'Root.Unknown')]

``E_UNSUPPORTED_FEATURE`` is raised when a custom template does not declare ``features: [region]`` and the model has regions. The refusal happens before any output is written, which the next two commands show by checking that the output directory does not exist. The same model generates with the built-in ``python`` template.

.. literalinclude:: region_two_regions.fcstm
   :language: fcstm
   :caption: region_two_regions.fcstm

.. code-block:: console

   $ cat region_plain_template/config.yaml
   expr_styles: {}
   stmt_styles: {}
   globals: {}
   filters: {}
   tests: {}
   ignores: []
   $ pyfcstm generate -i region_two_regions.fcstm -t region_plain_template -o out_plain
   generate with template directory '...region_plain_template' does not support region models yet. (line 2)
   The model declares 2 regions, the first is 'Root.Left'.
   If you write this template: its config.yaml does not list `region` under `features`. ...
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i region_two_regions.fcstm --template c -o out_plain
   Or take the regions out of the model.
   $ echo $?
   1
   $ test -e out_plain || echo "output directory was not created"
   output directory was not created
   $ pyfcstm generate -i region_two_regions.fcstm --template python -o out_python
   $ test -f out_python/machine.py && echo "machine.py generated"
   machine.py generated

Read the refusal in this order: the first line names the template directory; the second line states how many regions the model declares and where the first one is; ``If you write this template`` says what to declare; ``If you write the model`` lists the built-in templates that declare ``region`` and gives a command that can be copied.

.. include:: _code_catalog_en.rst.inc
