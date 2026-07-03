.. _sec-reference-diagnostics-codes:

Diagnostics code reference
==========================

Diagnostic codes are stable identifiers used by inspect output, CI filters, and
LLM repair prompts. This page lists the codes most relevant to user-facing
inspect workflows; the full registry lives in ``pyfcstm.diagnostics.CODE_REGISTRY``.

Common codes
------------

.. list-table:: Common inspect diagnostics
   :header-rows: 1

   * - Code
     - Severity
     - Meaning
   * - ``W_DURING_CONST_ASSIGN``
     - warning
     - A concrete ``during`` action assigns the same literal-only numeric value every cycle.
   * - ``W_COMBO_DUPLICATE_EVENT``
     - warning
     - A combo trigger repeats the same canonical event term.
   * - ``W_COMBO_GUARD_PREFIX_IMPLIED``
     - warning
     - Earlier side-effect-free combo guards imply a later guard term.
   * - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - warning
     - An integer literal is outside the default C-family generated integer range.
   * - ``W_DEADLOCK_LEAF``
     - warning
     - A non-pseudo leaf state has no outgoing transition.
   * - ``W_UNREFERENCED_VAR``
     - warning
     - A variable cannot affect any transition guard through DSL data flow.
   * - ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT``
     - info
     - A variable is not used by DSL data flow, but visible abstract actions might use it externally.
   * - ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``
     - warning
     - A combo relay pseudo state contains lifecycle or aspect actions, so it is not a pure relay.
   * - ``W_COMBO_RESERVED_PREFIX_STATE_KIND``
     - warning
     - A non-pseudo state uses the reserved combo relay prefix.

C/C++ target-profile scope
--------------------------

``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` and related numeric deployment
warnings are about C-family generated runtimes. They apply to ``c``,
``c_poll``, ``cpp``, and ``cpp_poll`` deployment review, not to Python generated
runtime overflow behavior.

Combo relay scope
-----------------

Combo relay pseudo-state warnings are about generated relay purity and reserved
names. They do not mean ``during before`` aspect actions execute inside combo
relay pseudo states.
