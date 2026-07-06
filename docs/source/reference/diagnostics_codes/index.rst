.. _sec-reference-diagnostics-codes:

Diagnostics code reference
==========================

Diagnostic codes are stable identifiers used by inspect output, CI filters, IDE
integrations, and LLM repair prompts. The full registry lives in
``pyfcstm.diagnostics.CODE_REGISTRY``; this page explains the user-facing codes
that appear most often while writing DSL.

How to read an inspect diagnostic
---------------------------------

Run JSON inspect when you need machine-readable repair context:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_duplicate_event.fcstm --format json

Each diagnostic contains:

* ``code``: stable identifier such as ``W_COMBO_DUPLICATE_EVENT``;
* ``severity``: ``error``, ``warning``, or ``info``;
* ``message``: short human explanation;
* ``span``: source location when available;
* ``refs``: structured fields such as ``event_name`` or ``guard_vars``;
* optional suggested-fix payloads for tools that can propose edits.

Errors block model construction. Warnings and infos do not necessarily block
simulation or generation, but they should be read because many of them identify
risky target profiles, surprising guards, or likely typos.

Common codes
------------

.. list-table:: Common inspect diagnostics
   :header-rows: 1
   :widths: 28 12 60

   * - Code
     - Severity
     - Meaning and usual repair
   * - ``W_DURING_CONST_ASSIGN``
     - warning
     - A concrete ``during`` action assigns the same literal-only numeric value every cycle. Move one-time initialization to ``enter`` or make the expression depend on runtime state.
   * - ``W_COMBO_DUPLICATE_EVENT``
     - warning
     - A combo trigger repeats the same canonical event term. Check whether the second term is a typo; keep it only if the explicit two-hop relay is intentional.
   * - ``W_COMBO_GUARD_PREFIX_IMPLIED``
     - warning
     - Earlier side-effect-free combo guards imply a later guard term. Remove the redundant guard or rewrite it if it was meant to constrain a different condition.
   * - ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``
     - warning
     - A ``pseudo state __combo_*`` node contains lifecycle or aspect actions. Move business behavior to authored states or rename the pseudo state outside the reserved namespace.
   * - ``W_COMBO_RESERVED_PREFIX_STATE_KIND``
     - warning
     - A normal leaf or composite state uses the reserved combo relay prefix. Rename the state; do not make a business state pseudo just to silence the warning.
   * - ``W_GUARD_VARS_NEVER_CHANGE``
     - warning
     - A guard reads only variables that are never changed by actions/effects. Add the missing write or simplify the guard if the initial-value-only behavior is intentional.
   * - ``W_UNWRITTEN_READ_VAR``
     - warning
     - An operation reads a variable before any write in the same block can define its value. Initialize it earlier or reorder the block so the write is visible.
   * - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - warning
     - An integer literal is outside the default C-family generated integer range. Treat it as a C/C++ deployment-profile warning, not as a Python runtime overflow claim.
   * - ``W_DEADLOCK_LEAF``
     - warning
     - A non-pseudo leaf state has no outgoing transition. Add an exit or outgoing transition if the state should not be terminal.
   * - ``W_UNREFERENCED_VAR``
     - warning
     - A variable cannot affect any transition guard through DSL data flow. Remove it or connect it to model behavior unless an external abstract hook uses it.
   * - ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT``
     - info
     - A variable is not used by DSL data flow, but visible abstract actions might use it externally.
   * - ``I_TRANSITION_NEVER_EVENT_TRIGGERED``
     - info
     - An event-triggered transition is not fired by any checked event path. Keep it if external events trigger it, or remove/rename the event if it is stale.

Runnable diagnostic examples
----------------------------

The following checked files intentionally demonstrate common warnings. They are
valid DSL files, not broken parser fixtures.

.. list-table:: Diagnostic examples
   :header-rows: 1
   :widths: 30 32 38

   * - File
     - Key output excerpt
     - What to learn
   * - ``combo_duplicate_event.fcstm``
     - ``warning: W_COMBO_DUPLICATE_EVENT``
     - Inspect points to the repeated combo term via ``refs.term_span`` and ``refs.first_term_span``.
   * - ``guard_vars_never_change.fcstm``
     - ``warning: W_GUARD_VARS_NEVER_CHANGE``
     - A guard that only reads initial values may be fixed or intentionally documented.
   * - ``during_const_assign.fcstm``
     - ``warning: W_DURING_CONST_ASSIGN``
     - Repeated constant assignment in ``during`` often belongs in ``enter``.
   * - ``numeric_target_range.fcstm``
     - ``warning: W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - Numeric target warnings are scoped to C-family generated runtimes.

Example command:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/numeric_target_range.fcstm --format human --color never

Expected excerpt:

.. code-block:: text

   W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE
   C/C++ default deployment profile risk: integer literal 9223372036854775808 is outside the PYFCSTM_GENERATED_INT64 range

.. _diag-c-cpp-risk-wording:

C/C++ target-profile scope
--------------------------

``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` and related numeric deployment
warnings are about C-family generated runtimes. They apply to ``c``,
``c_poll``, ``cpp``, and ``cpp_poll`` deployment review, not to Python generated
runtime overflow behavior. If a future Python-specific diagnostic exists, it
must say so explicitly; do not infer Python risk from C/C++ profile wording.

.. _diag-combo-relay-scope:

Combo relay scope
-----------------

Combo relay pseudo-state warnings are about generated relay purity and reserved
names. They do not mean ``during before`` aspect actions execute inside combo
relay pseudo states. A relay pseudo state should remain a pure routing helper;
observable business behavior belongs on authored states or transition effects.
