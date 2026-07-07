Complete diagnostic code catalog
--------------------------------

This catalog is synchronized with ``pyfcstm.diagnostics.codes.CODE_REGISTRY``. The hidden ``diagnostics-meta`` and ``diagnostics-example`` source markers are checked by ``python tools/check_diagnostics_reference_docs.py --check``.

.. list-table:: Registry summary
   :header-rows: 1
   :widths: 28 12 18 18 24

   * - Code
     - Severity
     - Emit tier
     - Capability
     - Span object
   * - :ref:`E_UNDEFINED_VAR <diag-code-e-undefined-var>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`E_DUPLICATE_VAR <diag-code-e-duplicate-var>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`E_MISSING_STATE <diag-code-e-missing-state>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_DUPLICATE_STATE <diag-code-e-duplicate-state>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_EVENT_REF_INVALID <diag-code-e-event-ref-invalid>`
     - ``error``
     - ``lookup_api``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`E_EVENT_NOT_FOUND <diag-code-e-event-not-found>`
     - ``error``
     - ``lookup_api``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`E_DANGLING_TRANSITION <diag-code-e-dangling-transition>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_COMBO_TRIGGER_NOT_EXPANDED <diag-code-e-combo-trigger-not-expanded>`
     - ``error``
     - ``catalog_only``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_COMBO_RESERVED_PREFIX_STATE_KIND <diag-code-w-combo-reserved-prefix-state-kind>`
     - ``warning``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_COMBO_RELAY_PSEUDO_HAS_ACTIONS <diag-code-w-combo-relay-pseudo-has-actions>`
     - ``warning``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`I_COMBO_PSEUDO_NAME_EXTENDED <diag-code-i-combo-pseudo-name-extended>`
     - ``info``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_COMBO_PSEUDO_NAME_COLLISION <diag-code-e-combo-pseudo-name-collision>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_COMBO_DUPLICATE_EVENT <diag-code-w-combo-duplicate-event>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_COMBO_GUARD_CONST_TRUE <diag-code-w-combo-guard-const-true>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_CONST_FALSE <diag-code-w-combo-guard-const-false>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_PREFIX_IMPLIED <diag-code-w-combo-guard-prefix-implied>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_PREFIX_CONTRADICTS <diag-code-w-combo-guard-prefix-contradicts>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`E_TYPE_MISMATCH <diag-code-e-type-mismatch>`
     - ``error``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`E_FORCED_TRANSITION_EXPANSION <diag-code-e-forced-transition-expansion>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_INITIAL_TRANSITION_INVALID <diag-code-e-initial-transition-invalid>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_DUPLICATE_FUNCTION_NAME <diag-code-e-duplicate-function-name>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_DURING_ASPECT_INVALID <diag-code-e-during-aspect-invalid>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``lifecycle_action``
   * - :ref:`E_PSEUDO_NOT_LEAF <diag-code-e-pseudo-not-leaf>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_NAMED_FUNCTION_REF_CYCLE <diag-code-e-named-function-ref-cycle>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_NAMED_FUNCTION_REF_NOT_FOUND <diag-code-e-named-function-ref-not-found>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_IMPORT_NOT_FOUND <diag-code-e-import-not-found>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_CIRCULAR <diag-code-e-import-circular>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_ALIAS_CONFLICT <diag-code-e-import-alias-conflict>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_DUPLICATE_MAPPING <diag-code-e-import-duplicate-mapping>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_MAPPING_INVALID <diag-code-e-import-mapping-invalid>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`W_UNREACHABLE_STATE <diag-code-w-unreachable-state>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_GUARD_CONST_FALSE <diag-code-w-guard-const-false>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``guard_expression``
   * - :ref:`W_GUARD_CONST_TRUE <diag-code-w-guard-const-true>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``guard_expression``
   * - :ref:`W_DURING_CONST_ASSIGN <diag-code-w-during-const-assign>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``lifecycle_action``
   * - :ref:`W_UNUSED_EVENT <diag-code-w-unused-event>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_DEADLOCK_LEAF <diag-code-w-deadlock-leaf>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_INITIAL_UNCONDITIONAL_MISSING <diag-code-w-initial-unconditional-missing>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`W_FORCED_NEVER_EXPANDS <diag-code-w-forced-never-expands>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_DEAD_NAMED_ACTION <diag-code-w-dead-named-action>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`W_UNREFERENCED_VAR <diag-code-w-unreferenced-var>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`I_UNREFERENCED_VAR_MAYBE_ABSTRACT <diag-code-i-unreferenced-var-maybe-abstract>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_GUARD_VARS_NEVER_CHANGE <diag-code-w-guard-vars-never-change>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``guard_expression``
   * - :ref:`W_UNWRITTEN_READ_VAR <diag-code-w-unwritten-read-var>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_WRITE_ONLY_VAR <diag-code-w-write-only-var>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_REDUNDANT_TRANSITION <diag-code-w-redundant-transition>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_SELF_TRANSITION_NOP <diag-code-w-self-transition-nop>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_EFFECT_SELF_ASSIGN <diag-code-w-effect-self-assign>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``effect_statement``
   * - :ref:`W_FORCED_OVERRIDES_NORMAL <diag-code-w-forced-overrides-normal>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_SHADOWED_EVENT <diag-code-w-shadowed-event>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_NAMED_ACTION_SHADOWS_ANCESTOR <diag-code-w-named-action-shadows-ancestor>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`W_LITERAL_TYPE_NARROWING <diag-code-w-literal-type-narrowing>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE <diag-code-w-numeric-literal-out-of-target-range>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_NUMERIC_CONSTANT_DIVISION_BY_ZERO <diag-code-w-numeric-constant-division-by-zero>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``expression``
   * - :ref:`W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE <diag-code-w-numeric-shift-count-out-of-target-range>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``expression``
   * - :ref:`W_NUMERIC_FLOAT_BITWISE <diag-code-w-numeric-float-bitwise>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_ASPECT_NO_DESCENDANT_LEAF <diag-code-w-aspect-no-descendant-leaf>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``lifecycle_action``
   * - :ref:`W_HIGH_VAR_TO_LEAF_RATIO <diag-code-w-high-var-to-leaf-ratio>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`W_DEEP_HIERARCHY <diag-code-w-deep-hierarchy>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_LARGE_COMPOSITE <diag-code-w-large-composite>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`I_TRANSITION_TO_SELF_VIA_PARENT <diag-code-i-transition-to-self-via-parent>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`I_TRANSITION_NEVER_EVENT_TRIGGERED <diag-code-i-transition-never-event-triggered>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`I_NONTRIVIAL_SCC <diag-code-i-nontrivial-scc>`
     - ``info``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_TOPOLOGICAL_NOEXIT <diag-code-w-topological-noexit>`
     - ``warning``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`I_TOPOLOGICAL_NON_TERMINATING <diag-code-i-topological-non-terminating>`
     - ``info``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_EVENT_UNREACHABLE_EMIT <diag-code-w-event-unreachable-emit>`
     - ``warning``
     - ``verify_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_DEAD_GUARD <diag-code-w-dead-guard>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_GUARD_TAUTOLOGY <diag-code-w-guard-tautology>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_FORCED_GUARD_UNSAT <diag-code-w-forced-guard-unsat>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_EFFECT_SMT_NO_OP <diag-code-w-effect-smt-no-op>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``effect_statement``
   * - :ref:`I_EFFECT_GUARD_CONTRADICT <diag-code-i-effect-guard-contradict>`
     - ``info``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``effect_statement``
   * - :ref:`W_TRANSITION_SHADOWED <diag-code-w-transition-shadowed>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``transition``
   * - :ref:`I_ENTER_DURING_CONTRADICT <diag-code-i-enter-during-contradict>`
     - ``info``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``lifecycle_action``
   * - :ref:`W_COMPOSITE_INIT_INCOMPLETE <diag-code-w-composite-init-incomplete>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``composite_block``

Names, variables, types, and imports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-undefined-var:

E_UNDEFINED_VAR
^^^^^^^^^^^^^^^

.. diagnostics-meta E_UNDEFINED_VAR severity=error emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref E_UNDEFINED_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR referenced_in type=str required=true enum=guard|effect|enter|during|exit|during_aspect|init item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR state_path type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR expr_text type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR is_temporary type=bool required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``expression``.

**Meaning.** A guard, effect, or lifecycle-action block references a name that was never declared with a top-level `def` statement.

**LLM repair summary.** A variable identifier appears in an expression (guard, effect, or action block) but has not been declared with ``def`` at the file top, has not been assigned earlier in the same block (so the block-local temporary path doesn't apply), and is not a known function name. The model refuses to bind unknown identifiers because the generated code would not compile.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - The undeclared identifier as it appeared in the source.
   * - ``referenced_in``
     - ``str``
     - yes
     - Which kind of block contained the reference. (enum: ``guard``, ``effect``, ``enter``, ``during``, ``exit``, ``during_aspect``, ``init``)
   * - ``state_path``
     - ``str_or_null``
     - no
     - Dotted path of the state that owns the offending block, when the reference is inside a state body (not a guard/effect on a transition).
   * - ``expr_text``
     - ``str_or_null``
     - no
     - Original expression text containing the reference.
   * - ``is_temporary``
     - ``bool``
     - no
     - ``True`` when the identifier looked like a block-local temporary (the read occurred before the variable was assigned within the same ``enter`` / ``during`` / ``exit`` / ``effect`` block). Layer 2 merges what jsfcstm previously emitted as ``fcstm.readBeforeAssignTemporary`` into this single ``E_*`` code plus this flag. Defaults to ``False`` / absent for "real" undefined variables that have no matching ``def`` declaration anywhere.

.. diagnostics-example E_UNDEFINED_VAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root { state A; state B; A -> B : if [unknown_var > 0]; }

.. diagnostics-example E_UNDEFINED_VAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_definition`` on ``file_top``: If the variable is genuinely program state, declare it with ``def <type> <name> = <initial>;`` at the file top so the generated runtime allocates storage for it.

.. diagnostics-example E_UNDEFINED_VAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not declare the variable inside an action block expecting it to leak out — block-local temps are discarded at block exit.

.. _diag-code-e-duplicate-var:

E_DUPLICATE_VAR
^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_VAR severity=error emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref E_DUPLICATE_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_VAR previous_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``variable_declaration``.

**Meaning.** A top-level `def` statement re-declares an identifier that was already defined earlier in the file.

**LLM repair summary.** Two ``def`` declarations at the file top use the same variable name. The model allocates one storage slot per name, so a duplicate definition is ambiguous.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - The duplicated identifier.
   * - ``previous_span``
     - ``Span``
     - no
     - Source position of the first declaration.

.. diagnostics-example E_DUPLICATE_VAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   def int x = 1;
   state Root { state A; }

.. diagnostics-example E_DUPLICATE_VAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``drop_duplicate`` on ``variable_definition``: If both definitions are meant to declare the same logical variable, keep the first one and delete the second.

.. diagnostics-example E_DUPLICATE_VAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not assume the second ``def`` overrides the first — the generated runtime treats this as an error and refuses to compile.

.. _diag-code-e-type-mismatch:

E_TYPE_MISMATCH
^^^^^^^^^^^^^^^

.. diagnostics-meta E_TYPE_MISMATCH severity=error emit_tier=partial_static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref E_TYPE_MISMATCH expected type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_TYPE_MISMATCH actual type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_TYPE_MISMATCH expr_text type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``partial_static_pipeline``; capability ``pure_static``; span object ``expression``.

**Meaning.** A guard, effect, or assignment uses an expression whose type does not match the expected category (arithmetic vs boolean).

**LLM repair summary.** An expression mixes an arithmetic and a boolean subexpression in a way the grammar does not allow. ``num_expression`` and ``cond_expression`` are strictly separated; comparison operators bridge them, ternary ``? :`` converts boolean → arithmetic.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``expected``
     - ``str``
     - yes
     - Expected category. One of: 'numeric', 'boolean'.
   * - ``actual``
     - ``str``
     - yes
     - Actual category produced by the expression.
   * - ``expr_text``
     - ``str``
     - yes
     - Original expression text.

.. diagnostics-example E_TYPE_MISMATCH 1 boundary_only

**Example 1** (``boundary_only``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root { state A; state B; A -> B : if [x]; }

.. diagnostics-example E_TYPE_MISMATCH 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``wrap_in_ternary`` on ``expression``: If you wanted to assign a boolean test, wrap it as ``(cond) ? 1 : 0`` so the right-hand side is arithmetic.

.. diagnostics-example E_TYPE_MISMATCH 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not rely on numeric → boolean implicit coercion; the generated runtimes treat the two domains as distinct.

.. _diag-code-e-duplicate-function-name:

E_DUPLICATE_FUNCTION_NAME
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_FUNCTION_NAME severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME stage type=str required=true enum=enter|during|exit|during_aspect item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``named_action_declaration``.

**Meaning.** Two named lifecycle actions (enter / during / exit / during-aspect) within the same state share the same name. Named actions are referenced via `ref <name>` and must be uniquely identifiable.

**LLM repair summary.** Two named action / function blocks share the same name within the same scope. Named blocks must be uniquely identifiable so ``ref`` lookups can bind to a single definition.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``function_name``
     - ``str``
     - yes
     - The duplicated named-action name.
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state declaring the duplicates.
   * - ``stage``
     - ``str``
     - yes
     - Lifecycle stage where the duplicate appears. (enum: ``enter``, ``during``, ``exit``, ``during_aspect``)

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A {
           enter Foo { }
           enter Foo { }
       }
   }

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``rename_one`` on ``named_action``: Give one of the named blocks a distinct identifier so ``ref <name>`` calls resolve unambiguously.

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not assume the second declaration shadows the first — the resolver treats this as a hard error.

.. _diag-code-e-named-function-ref-cycle:

E_NAMED_FUNCTION_REF_CYCLE
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_NAMED_FUNCTION_REF_CYCLE severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE ref_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE cycle_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE reason type=str required=true enum=action_ref_cycle item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``named_action_declaration``.

**Meaning.** A lifecycle action `ref` chain forms a cycle and therefore never reaches a concrete or abstract action implementation.

**LLM repair summary.** An ``enter ref ...`` / ``exit ref ...`` / ``during ref ...`` clause ultimately points back to itself through one or more named actions.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``ref_path``
     - ``str``
     - yes
     - Dot-separated action path where cycle validation started.
   * - ``cycle_path``
     - ``str``
     - yes
     - Dot-separated action path chain that closes the cycle.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing the failure. (enum: ``action_ref_cycle``)

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A {
           enter ref First;
           enter First ref Second;
           enter Second ref First;
       }
   }

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``break_ref_cycle`` on ``action_ref``: Replace one link in the cycle with a concrete action block or an abstract action declaration so the reference chain terminates.

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not execute or render cyclic lifecycle references; reject the model before runtime execution.

.. _diag-code-e-named-function-ref-not-found:

E_NAMED_FUNCTION_REF_NOT_FOUND
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_NAMED_FUNCTION_REF_NOT_FOUND severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND ref_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND reason type=str required=true enum=state_not_found|named_function_not_found item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND missing_segment type=str_or_null required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``named_action_declaration``.

**Meaning.** A `ref` lifecycle action could not resolve its target named action. Either the path walks through a state that does not exist, or the final segment is not a named action defined inside the resolved state.

**LLM repair summary.** An ``enter ref ...`` / ``exit ref ...`` / ``during ref ...`` clause points at a named action that does not exist. The resolver could not find a matching named block in the indicated scope.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``ref_path``
     - ``str``
     - yes
     - Dotted path of the unresolved reference.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing the resolution failure. (enum: ``state_not_found``, ``named_function_not_found``)
   * - ``missing_segment``
     - ``str_or_null``
     - no
     - The path segment that failed to resolve. For 'state_not_found' this is the state name that does not exist under the parent path; for 'named_function_not_found' this is the action name searched for in the resolved state.

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A {
           enter ref NoSuch.NoSuch;
       }
   }

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_ref_path`` on ``action_ref``: Confirm the dotted ref path matches a real named action. Use ``/`` to anchor at the root, or a relative name for the current state.

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently swap ``ref`` with an inline block — that loses the deduplication that ``ref`` was meant to provide.

.. _diag-code-e-import-not-found:

E_IMPORT_NOT_FOUND
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_NOT_FOUND severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_NOT_FOUND source_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND reason type=str required=true enum=file_not_found|read_error|parse_error|no_root_state item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``import_statement``.

**Meaning.** An ``import`` statement points at a source file that cannot be found, cannot be read, or fails to parse.

**LLM repair summary.** An import target could not be resolved. Inspect ``refs.reason`` to branch the fix: ``file_not_found`` means the path is wrong or the file does not exist; ``read_error`` means the file exists but the I/O layer rejected it (permissions / encoding); ``parse_error`` means the file was loaded but is not valid FCSTM DSL; ``no_root_state`` means the file parses but declares no ``state Root { ... }`` block. The four reasons need different fixes — do not collapse them. Cross-end note (I2 from PR #115 final review): jsfcstm currently only distinguishes ``file_not_found`` and ``no_root_state``; its workspace index treats I/O failures and parse failures alike as ``missing`` and emits ``file_not_found`` for both. When consuming jsfcstm-side diagnostics, treat ``file_not_found`` as "any pre-no_root_state failure" and inspect the imported file directly to disambiguate read vs parse failures.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``source_path``
     - ``str``
     - yes
     - The source-path token from the import statement, exactly as it appeared in the DSL.
   * - ``alias``
     - ``str``
     - yes
     - The alias under which the import was declared.
   * - ``host_state_path``
     - ``str``
     - yes
     - Dotted path of the composite state hosting the import statement.
   * - ``reason``
     - ``str``
     - yes
     - Why resolution failed. (enum: ``file_not_found``, ``read_error``, ``parse_error``, ``no_root_state``)

.. diagnostics-example E_IMPORT_NOT_FOUND 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       import "missing.fcstm" as Sub;
   }

.. diagnostics-example E_IMPORT_NOT_FOUND 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_path`` on ``import_statement``: For ``file_not_found``, adjust the source_path to a real file relative to the host file, or remove the import if the sub-machine is no longer required.

.. diagnostics-example E_IMPORT_NOT_FOUND 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently rename the alias to dodge the missing file.

.. _diag-code-e-import-circular:

E_IMPORT_CIRCULAR
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_CIRCULAR severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_CIRCULAR source_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR cycle_chain type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``import_statement``.

**Meaning.** A cycle was detected while resolving ``import`` statements between two or more state-machine source files.

**LLM repair summary.** Two or more state-machine files import each other transitively. The compiler refuses to resolve cycles to keep the merged hierarchy tractable.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``source_path``
     - ``str``
     - yes
     - The source-path token that closed the cycle.
   * - ``alias``
     - ``str``
     - yes
     - The alias under which the cyclic import was declared.
   * - ``host_state_path``
     - ``str``
     - yes
     - Dotted path of the composite state hosting the import.
   * - ``cycle_chain``
     - ``list[str]``
     - yes
     - Ordered list of file paths that participate in the cycle, starting and ending at the same file.

.. diagnostics-example E_IMPORT_CIRCULAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   # a.fcstm
   state A { import "b.fcstm" as B; }
   # b.fcstm
   state B { import "a.fcstm" as A; }

.. diagnostics-example E_IMPORT_CIRCULAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``refactor`` on ``import_statement``: Break the cycle by extracting the shared state(s) into a third file that both ends import without depending on each other.

.. diagnostics-example E_IMPORT_CIRCULAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not duplicate the imported states inline to break the cycle — that defeats the purpose of imports.

.. _diag-code-e-import-alias-conflict:

E_IMPORT_ALIAS_CONFLICT
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_ALIAS_CONFLICT severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT conflicting_kind type=str required=true enum=existing_substate|previous_import_alias item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``import_statement``.

**Meaning.** An ``import`` alias clashes with an existing child state (or with another import alias) under the same composite state.

**LLM repair summary.** The import alias collides with an already-defined name in the same composite scope. The merged hierarchy cannot have two children sharing a name.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``alias``
     - ``str``
     - yes
     - The conflicting alias name.
   * - ``host_state_path``
     - ``str``
     - yes
     - Dotted path of the composite state hosting the import.
   * - ``conflicting_kind``
     - ``str``
     - yes
     - What the alias clashed with. (enum: ``existing_substate``, ``previous_import_alias``)

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       state Worker;
       import "worker.fcstm" as Worker;
   }

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``rename_alias`` on ``import_statement``: Pick a unique alias for the import; references to the imported machine elsewhere in the file must follow the new alias.

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently drop one of the conflicting definitions.

.. _diag-code-e-import-duplicate-mapping:

E_IMPORT_DUPLICATE_MAPPING
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_DUPLICATE_MAPPING severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING mapping_kind type=str required=true enum=event|variable item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING duplicated_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING direction type=str required=true enum=source_duplicated|target_duplicated item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING host_state_path type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``import_statement``.

**Meaning.** Two or more mapping clauses under the same ``import { ... }`` block target the same source name (event or variable), or two source names target the same host name.

**LLM repair summary.** An import-mapping block contains a duplicate source or target name. Each source identifier can be mapped at most once; each target host slot can receive at most one source.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``alias``
     - ``str``
     - yes
     - The import alias whose mapping is duplicated.
   * - ``mapping_kind``
     - ``str``
     - yes
     - Which mapping flavor was duplicated. (enum: ``event``, ``variable``)
   * - ``duplicated_name``
     - ``str``
     - yes
     - The source-side or target-side name that appears more than once.
   * - ``direction``
     - ``str``
     - yes
     - Which side of the mapping was duplicated. (enum: ``source_duplicated``, ``target_duplicated``)
   * - ``host_state_path``
     - ``str``
     - yes
     - Dotted path of the composite state hosting the import.

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       import "sub.fcstm" as Sub {
           def x = a;
           def x = b;
       }
   }

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``drop_duplicate`` on ``mapping_clause``: Delete the duplicated mapping line — keep the intended one.

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not merge mappings by concatenating their values.

.. _diag-code-e-import-mapping-invalid:

E_IMPORT_MAPPING_INVALID
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_MAPPING_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_MAPPING_INVALID alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID mapping_kind type=str required=true enum=event|variable item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID reason type=str required=true enum=source_not_found|target_invalid|selector_invalid|template_invalid|empty_path|host_root_mismatch item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID detail type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``import_statement``.

**Meaning.** An import-mapping clause refers to a source name that does not exist in the imported machine, uses an invalid selector / template, or points at a host target that cannot host the mapped element.

**LLM repair summary.** An ``import { ... }`` mapping clause is malformed or points at a non-existent element on the source side / a non-receivable element on the host side.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``alias``
     - ``str``
     - yes
     - The import alias whose mapping is malformed.
   * - ``mapping_kind``
     - ``str``
     - yes
     - Mapping flavor. (enum: ``event``, ``variable``)
   * - ``host_state_path``
     - ``str``
     - yes
     - Dotted path of the composite state hosting the import.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing the failure mode. (enum: ``source_not_found``, ``target_invalid``, ``selector_invalid``, ``template_invalid``, ``empty_path``, ``host_root_mismatch``)
   * - ``detail``
     - ``str``
     - yes
     - Human-readable specifics of the mapping failure (mapping text, selector / template literal, or path that failed to resolve).

.. diagnostics-example E_IMPORT_MAPPING_INVALID 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       import "sub.fcstm" as Sub {
           def x = no_such_var;
       }
   }

.. diagnostics-example E_IMPORT_MAPPING_INVALID 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_source`` on ``mapping_clause``: Update the source-side name to match a real def / event in the imported file.

.. diagnostics-example E_IMPORT_MAPPING_INVALID 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not invent fake source names to make the selector match.

States and transitions
~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-missing-state:

E_MISSING_STATE
^^^^^^^^^^^^^^^

.. diagnostics-meta E_MISSING_STATE severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_MISSING_STATE state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_MISSING_STATE referenced_from type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_MISSING_STATE reason type=str required=false enum=not_found|parent_missing|ambiguous|event_path_not_found item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A transition target references a state path that cannot be resolved in the surrounding hierarchy.

**LLM repair summary.** A transition references a state name that does not exist in the machine. The transition target / source must resolve to a state declared in this file or imported.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - The unresolved dotted state path.
   * - ``referenced_from``
     - ``str_or_null``
     - no
     - Dotted path of the state from which the reference was made.
   * - ``reason``
     - ``str``
     - no
     - Short tag describing the resolution failure mode. (enum: ``not_found``, ``parent_missing``, ``ambiguous``, ``event_path_not_found``)

.. diagnostics-example E_MISSING_STATE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; A -> NoSuch; }

.. diagnostics-example E_MISSING_STATE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_typo`` on ``transition``: If the name was meant to refer to an existing state, correct the spelling. ``refs.state_name`` carries the missing token.

.. diagnostics-example E_MISSING_STATE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently delete the transition; the original intent of the missing state is lost.

.. _diag-code-e-duplicate-state:

E_DUPLICATE_STATE
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_STATE severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_DUPLICATE_STATE state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_STATE parent_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_STATE previous_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** Two states share the same name within the same parent scope.

**LLM repair summary.** Two state declarations under the same composite parent use the same name. State names must be unique inside their immediate composite scope.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_name``
     - ``str``
     - yes
     - The duplicated state name.
   * - ``parent_path``
     - ``str``
     - yes
     - Dotted path of the parent that contains both states.
   * - ``previous_span``
     - ``Span``
     - no
     - Source position of the first declaration.

.. diagnostics-example E_DUPLICATE_STATE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state A; }

.. diagnostics-example E_DUPLICATE_STATE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``drop_duplicate`` on ``state_definition``: If both declarations describe the same logical state, keep one and remove the other (merge any actions/transitions onto the survivor).

.. diagnostics-example E_DUPLICATE_STATE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not assume the second declaration overrides the first — duplicate state names produce a hard error.

.. _diag-code-e-dangling-transition:

E_DANGLING_TRANSITION
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DANGLING_TRANSITION severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_DANGLING_TRANSITION src type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DANGLING_TRANSITION tgt type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DANGLING_TRANSITION reason type=str required=true enum=src_not_found|tgt_not_found|both_not_found item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A transition cannot resolve either its source or its target.

**LLM repair summary.** A transition's source or target points at a state that exists neither in the local composite scope nor in any ancestor scope. The transition cannot be wired into the dispatch graph.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``src``
     - ``str_or_null``
     - no
     - Raw source state expression as written in the DSL.
   * - ``tgt``
     - ``str_or_null``
     - no
     - Raw target state expression as written in the DSL.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing the dangling reason. (enum: ``src_not_found``, ``tgt_not_found``, ``both_not_found``)

.. diagnostics-example E_DANGLING_TRANSITION 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; NoSuch -> A; }

.. diagnostics-example E_DANGLING_TRANSITION 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_typo`` on ``transition``: If the dangling name is misspelled, correct it. ``refs.state_path`` carries the location of the offending transition.

.. diagnostics-example E_DANGLING_TRANSITION 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not pretend the transition resolves to ``[*]`` — that has a specific entry/exit semantics.

.. _diag-code-e-initial-transition-invalid:

E_INITIAL_TRANSITION_INVALID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_INITIAL_TRANSITION_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_INITIAL_TRANSITION_INVALID composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_INITIAL_TRANSITION_INVALID reason type=str required=true enum=missing_entry|target_not_child item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A composite state either lacks an entry transition (`[*] -> child`) or declares one whose target is not a direct child of the composite.

**LLM repair summary.** A composite state lacks a valid ``[*] -> Child`` initial transition, or its declared initial target is not actually a child of this composite. The runtime cannot decide which child to enter when this composite is activated.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``composite_path``
     - ``str``
     - yes
     - Dotted path of the offending composite state.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing the failure. (enum: ``missing_entry``, ``target_not_child``)

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state Outer { state Inner; } }

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_initial_transition`` on ``composite_state``: Add ``[*] -> <ChildName>;`` inside the composite, picking a direct substate as the entry point.

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not rely on a default ordering of substates; the runtime requires an explicit initial transition.

.. _diag-code-w-redundant-transition:

W_REDUNDANT_TRANSITION
^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_REDUNDANT_TRANSITION severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_REDUNDANT_TRANSITION from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION duplicate_spans type=list[Span] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** Multiple transitions share the same source, target, event, guard, and effect. Forced and normal transitions with the same behavioral key are counted here as redundant and may also emit W_FORCED_OVERRIDES_NORMAL.

**LLM repair summary.** These transitions are indistinguishable by source, target, event, guard, and effect, so later copies do not add behavior.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``from_path``
     - ``str``
     - yes
     - Dotted source state path.
   * - ``to_path``
     - ``str``
     - yes
     - Dotted target state path.
   * - ``duplicate_spans``
     - ``list[Span]``
     - yes
     - Source spans for the duplicate transition declarations, using null for declarations whose span is unavailable.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example W_REDUNDANT_TRANSITION 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Go;
       A -> B :: Go;
   }

.. diagnostics-example W_REDUNDANT_TRANSITION 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_duplicate`` on ``transition``: Keep one transition and remove redundant copies.

.. diagnostics-example W_REDUNDANT_TRANSITION 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not keep duplicate transitions as comments.

.. _diag-code-w-self-transition-nop:

W_SELF_TRANSITION_NOP
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_SELF_TRANSITION_NOP severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_SELF_TRANSITION_NOP state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A leaf self transition has no event, guard, effect, own lifecycle action, or ancestor aspect action.

**LLM repair summary.** The transition points from a state to itself and has no trigger, guard, effect, or re-entry lifecycle behavior, so it does not model useful behavior.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state with the no-op self transition.
   * - ``from_path``
     - ``str``
     - no
     - Dotted source state path.
   * - ``to_path``
     - ``str``
     - no
     - Dotted target state path.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the no-op self transition when available.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example W_SELF_TRANSITION_NOP 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       [*] -> A;
       A -> A;
   }

.. diagnostics-example W_SELF_TRANSITION_NOP 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_transition`` on ``transition``: Remove the no-op transition.

.. diagnostics-example W_SELF_TRANSITION_NOP 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not apply this warning to self transitions whose re-entry would run enter, during, exit, or ancestor aspect actions.

.. _diag-code-i-transition-to-self-via-parent:

I_TRANSITION_TO_SELF_VIA_PARENT
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TRANSITION_TO_SELF_VIA_PARENT severity=info emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref I_TRANSITION_TO_SELF_VIA_PARENT state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_TO_SELF_VIA_PARENT crosses_composite type=bool required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A composite state transitions to itself, which can intentionally force a re-entry path through child initialization and lifecycle actions.

**LLM repair summary.** This is an informational observation rather than a defect: a composite self-transition may be a deliberate reinitialization pattern.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the self-transitioning composite state.
   * - ``crosses_composite``
     - ``bool``
     - yes
     - Always ``True`` for this info because the state is composite.

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state Active { state Leaf; [*] -> Leaf; }
       [*] -> Active;
       Active -> Active;
   }

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``preserve_if_intentional`` on ``transition``: Keep the transition when the model should re-run composite entry semantics.

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not delete this transition automatically; it may be the intended reset path.

.. _diag-code-w-transition-shadowed:

W_TRANSITION_SHADOWED
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_TRANSITION_SHADOWED severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=transition
.. diagnostics-ref W_TRANSITION_SHADOWED algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED transition_summary type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED source_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED reason type=str required=true enum=guard_shadow|duplicate_event|unconditional_catchall|prior_trigger_cover item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED shadowed_by_count type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TRANSITION_SHADOWED shadowed_by type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``transition``.

**Meaning.** A later outgoing transition is fully covered by earlier same-source triggers and therefore cannot be selected.

**LLM repair summary.** Transition ordering means an earlier same-source transition consumes all cases that could have reached this later transition.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the shadowed transition.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.
   * - ``source_state_path``
     - ``str``
     - yes
     - Dotted source state path whose outgoing order creates the shadowing.
   * - ``reason``
     - ``str``
     - yes
     - Shadowing reason classification. (enum: ``guard_shadow``, ``duplicate_event``, ``unconditional_catchall``, ``prior_trigger_cover``)
   * - ``shadowed_by_count``
     - ``int``
     - yes
     - Number of earlier transitions covering this transition.
   * - ``shadowed_by``
     - ``list[str]``
     - yes
     - Stable summaries of earlier transitions that shadow this transition.

.. diagnostics-example W_TRANSITION_SHADOWED 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       state A;
       state B;
       state C;
       [*] -> A;
       A -> B;
       A -> C;
   }

.. diagnostics-example W_TRANSITION_SHADOWED 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``reorder_transitions`` on ``transition_list``: Move the more specific transition before the broader predecessor if both are needed.

.. diagnostics-example W_TRANSITION_SHADOWED 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not reorder transitions without checking FCSTM first-match semantics.

Events and scopes
~~~~~~~~~~~~~~~~~

.. _diag-code-e-event-ref-invalid:

E_EVENT_REF_INVALID
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_EVENT_REF_INVALID severity=error emit_tier=lookup_api capability=pure_static span_object=event_declaration
.. diagnostics-ref E_EVENT_REF_INVALID event_ref type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_REF_INVALID reason type=str required=true enum=empty|bare_slash|invalid_absolute|invalid_relative|trailing_dots|beyond_root item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``lookup_api``; capability ``pure_static``; span object ``event_declaration``.

**Meaning.** The textual form of an event reference is syntactically invalid (e.g. bare '/', trailing dots, going beyond the root state).

**LLM repair summary.** An event reference (``::``, ``:``, or ``/`` scoped) cannot resolve to a known event under the indicated scope. The grammar accepts the syntactic form, but the resolver cannot bind it to a real event object.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``event_ref``
     - ``str``
     - yes
     - The raw event reference text.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing why the reference is invalid. (enum: ``empty``, ``bare_slash``, ``invalid_absolute``, ``invalid_relative``, ``trailing_dots``, ``beyond_root``)

.. diagnostics-example E_EVENT_REF_INVALID 1 repro_api

**Example 1** (``repro_api``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state B; A -> B : /; }

.. diagnostics-example E_EVENT_REF_INVALID 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_scope_operator`` on ``transition``: The three scope operators do not interchange freely. ``::`` is source-local, ``:`` is parent-chain, ``/`` is root-absolute. Pick the one that matches where the event is actually declared.

.. diagnostics-example E_EVENT_REF_INVALID 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not invent a new event by silently aliasing — the dispatcher won't fire on an undeclared name.

.. _diag-code-e-event-not-found:

E_EVENT_NOT_FOUND
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_EVENT_NOT_FOUND severity=error emit_tier=lookup_api capability=pure_static span_object=event_declaration
.. diagnostics-ref E_EVENT_NOT_FOUND event_ref type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_NOT_FOUND scope type=str required=true enum=local|chain|absolute item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_NOT_FOUND searched_from type=str_or_null required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``lookup_api``; capability ``pure_static``; span object ``event_declaration``.

**Meaning.** An event reference parses correctly but does not resolve to any event defined in the targeted scope.

**LLM repair summary.** A dotted event path could not be resolved against the assembled state hierarchy. The path syntax was valid but no event with that name exists at the resolved state.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``event_ref``
     - ``str``
     - yes
     - The raw event reference text.
   * - ``scope``
     - ``str``
     - yes
     - Resolution scope used. (enum: ``local``, ``chain``, ``absolute``)
   * - ``searched_from``
     - ``str_or_null``
     - no
     - Dotted state path of the **caller** that initiated the lookup (i.e. the state on which `.resolve_event()` was invoked, or, for `StateMachine.resolve_event`, the state machine's root). This is the originating location of the bad reference in source — not the effective search root, which is always the model root for absolute references.

.. diagnostics-example E_EVENT_NOT_FOUND 1 repro_api

**Example 1** (``repro_api``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state B; A -> B :: NoEvent; }

.. diagnostics-example E_EVENT_NOT_FOUND 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_event_path`` on ``transition``: Confirm the dotted path matches the state hierarchy that actually exists after imports have been merged.

.. diagnostics-example E_EVENT_NOT_FOUND 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not paper over the error by introducing a wildcard alias — events are uniquely bound by their scope.

.. _diag-code-w-combo-duplicate-event:

W_COMBO_DUPLICATE_EVENT
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_DUPLICATE_EVENT severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT origin_id type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT event_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT first_term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT first_term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT trigger_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_DUPLICATE_EVENT first_term_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A combo transition trigger repeats the same canonical event term. The model still executes the two generated hops, but the second event term is usually redundant or a typo.

**LLM repair summary.** The combo trigger contains the same resolved event twice, for example ``E1 + E1``. This is legal but normally redundant because one cycle's input event set already contains ``E1``.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``origin_id``
     - ``str``
     - yes
     - Stable identifier of the original combo transition.
   * - ``event_name``
     - ``str``
     - yes
     - Canonical qualified event name that appears more than once.
   * - ``term_index``
     - ``int``
     - yes
     - Zero-based index of the repeated event term.
   * - ``first_term_index``
     - ``int``
     - yes
     - Zero-based index of the first matching event term.
   * - ``term_text``
     - ``str``
     - yes
     - Canonical source text of the repeated event term.
   * - ``first_term_text``
     - ``str``
     - yes
     - Canonical source text of the first matching event term.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the original combo transition.
   * - ``trigger_span``
     - ``Span``
     - no
     - Source span of the combo trigger suffix.
   * - ``term_span``
     - ``Span``
     - no
     - Source span of the repeated event term.
   * - ``first_term_span``
     - ``Span``
     - no
     - Source span of the first matching event term.

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + E1;
   }

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``inspect_terms`` on ``transition``: Check whether the second event was meant to be a different event.

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently delete the repeated event; the explicit pseudo-chain shape may be intentional.

.. _diag-code-w-unused-event:

W_UNUSED_EVENT
^^^^^^^^^^^^^^

.. diagnostics-meta W_UNUSED_EVENT severity=warning emit_tier=static_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_UNUSED_EVENT event_qualified_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNUSED_EVENT scope type=str required=true enum=local|chain|absolute item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``event_declaration``.

**Meaning.** An ``event`` declaration is never referenced by any transition.

**LLM repair summary.** An event is declared but never triggers any transition, so it is unused from the machine's perspective.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``event_qualified_name``
     - ``str``
     - yes
     - Fully qualified event name (e.g. ``Root.SubA.Pause``).
   * - ``scope``
     - ``str``
     - yes
     - Scope at which the event is declared. (enum: ``local``, ``chain``, ``absolute``)

.. diagnostics-example W_UNUSED_EVENT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       event Unused;
       state A;
       state B;
       [*] -> A;
       A -> B :: SomethingElse;
   }

.. diagnostics-example W_UNUSED_EVENT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``wire_event`` on ``transition``: Add a transition that uses the event if it was meant to be emitted.

.. diagnostics-example W_UNUSED_EVENT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not rename the event to dodge the warning — that just shifts the problem.

.. _diag-code-w-shadowed-event:

W_SHADOWED_EVENT
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_SHADOWED_EVENT severity=warning emit_tier=static_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_SHADOWED_EVENT event_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SHADOWED_EVENT local_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SHADOWED_EVENT chain_path type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``event_declaration``.

**Meaning.** A local event name shadows a chain or absolute event with the same leaf name.

**LLM repair summary.** The same event leaf name exists in local and broader scopes, which can make transition triggers easy to misread.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``event_name``
     - ``str``
     - yes
     - Shared event leaf name.
   * - ``local_path``
     - ``str``
     - yes
     - Qualified local event path.
   * - ``chain_path``
     - ``str``
     - yes
     - Qualified chain or absolute event path.

.. diagnostics-example W_SHADOWED_EVENT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       event Tick;
       state A;
       state B;
       [*] -> A;
       A -> B : Tick;
       B -> A :: Tick;
   }

.. diagnostics-example W_SHADOWED_EVENT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``rename_event`` on ``event``: Use distinct event names for different scopes.

.. diagnostics-example W_SHADOWED_EVENT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not rename only one trigger without checking all emitters.

.. _diag-code-i-transition-never-event-triggered:

I_TRANSITION_NEVER_EVENT_TRIGGERED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TRANSITION_NEVER_EVENT_TRIGGERED severity=info emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A normal transition has no event and no guard, so it is an unconditional fall-through candidate.

**LLM repair summary.** The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``from_path``
     - ``str``
     - yes
     - Dotted source state path.
   * - ``to_path``
     - ``str``
     - yes
     - Dotted target state path.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the transition when available.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B;
   }

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``keep_if_fallthrough`` on ``transition``: Keep it when the state should immediately advance.

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a meaningless event just to silence this info.

.. _diag-code-w-event-unreachable-emit:

W_EVENT_UNREACHABLE_EMIT
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_EVENT_UNREACHABLE_EMIT severity=warning emit_tier=verify_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT event_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT consumer_count type=int required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``pure_static``; span object ``event_declaration``.

**Meaning.** A used event has no consumer source that is reachable in the guard-agnostic topology graph.

**LLM repair summary.** The event is used by transitions, but those transition sources are not reachable from the root entry topology.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``topological_only``)
   * - ``event_name``
     - ``str``
     - yes
     - Qualified event name whose consumers are unreachable.
   * - ``consumer_count``
     - ``int``
     - yes
     - Number of unreachable consumer transitions represented by this finding.

.. diagnostics-example W_EVENT_UNREACHABLE_EMIT 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       event Panic;
       state A;
       state LostA;
       state LostB;
       [*] -> A;
       LostA -> A : Panic;
       LostB -> A : Panic;
   }

.. diagnostics-example W_EVENT_UNREACHABLE_EMIT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``connect_consumer`` on ``transition_source``: Add a topology path that reaches the state consuming the event.

.. diagnostics-example W_EVENT_UNREACHABLE_EMIT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add an emitter for this event if no reachable state can consume it.

Combo and relay diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-combo-trigger-not-expanded:

E_COMBO_TRIGGER_NOT_EXPANDED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_COMBO_TRIGGER_NOT_EXPANDED severity=error emit_tier=catalog_only capability=pure_static span_object=transition
.. diagnostics-ref E_COMBO_TRIGGER_NOT_EXPANDED state_path type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_TRIGGER_NOT_EXPANDED trigger type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``catalog_only``; capability ``pure_static``; span object ``transition``.

**Meaning.** A legacy fail-closed compatibility code for implementations that parse combo trigger syntax before model expansion support is available.

**LLM repair summary.** Older pyfcstm/jsfcstm builds may accept a transition trigger such as ``:: E1 + E2`` or ``: E1 + [x > 0]`` but stop before pseudo-state expansion support. Current pyfcstm expands combo triggers instead of emitting this code; the catalog entry remains for cross-version consumers.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str_or_null``
     - no
     - Dotted path of the state that owns the combo transition.
   * - ``trigger``
     - ``str``
     - yes
     - Canonical text of the combo trigger suffix.

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 1 compatibility_only

**Example 1** (``compatibility_only``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state B; A -> B :: Go + Done; }

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``wait_for_expansion_support`` on ``transition``: Keep the DSL syntax if you are testing parser/provenance support; wait for model-expansion support before running simulation, verification, or code generation on combo triggers.

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not treat the first event term as the whole transition; that would silently change model semantics.

.. _diag-code-w-combo-reserved-prefix-state-kind:

W_COMBO_RESERVED_PREFIX_STATE_KIND
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_RESERVED_PREFIX_STATE_KIND severity=warning emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND reserved_prefix type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_kind type=str required=true enum=state|composite item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``partial_static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A non-pseudo state name starts with the automatic combo relay prefix.

**LLM repair summary.** A normal leaf or composite state uses the ``__combo_`` prefix reserved for combo relay pseudo states. The model can still build, but the name is visually ambiguous with generated relay nodes.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_name``
     - ``str``
     - yes
     - State name using the combo relay reserved prefix.
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the offending state.
   * - ``reserved_prefix``
     - ``str``
     - yes
     - Reserved prefix used by generated combo pseudo states.
   * - ``state_kind``
     - ``str``
     - yes
     - Kind of user-authored state that used the reserved prefix. (enum: ``state``, ``composite``)

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 1 boundary_only

**Example 1** (``boundary_only``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state __combo_user; [*] -> __combo_user; }

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``rename_state`` on ``state_identifier``: Rename the user-authored state so readers and generated artifacts do not confuse it with an expanded combo relay.

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not fix this by declaring a business state as pseudo unless it is truly only a relay.

.. _diag-code-w-combo-relay-pseudo-has-actions:

W_COMBO_RELAY_PSEUDO_HAS_ACTIONS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_RELAY_PSEUDO_HAS_ACTIONS severity=warning emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS reserved_prefix type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS action_kinds type=list[str] required=true enum=- item_enum=enter|during|exit|during_aspect exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``partial_static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A pseudo state in the combo relay namespace contains lifecycle or aspect actions, so it is not a pure relay.

**LLM repair summary.** A ``pseudo state __combo_*`` node is allowed so expanded combo DSL can be reimported, but relay pseudo states should stay pure. Lifecycle or aspect actions make the relay observable and may surprise readers.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_name``
     - ``str``
     - yes
     - Pseudo-state name using the combo relay reserved prefix.
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the pseudo state.
   * - ``reserved_prefix``
     - ``str``
     - yes
     - Reserved prefix used by combo relay pseudo states.
   * - ``action_kinds``
     - ``list[str]``
     - yes
     - Lifecycle or aspect action kinds present on the pseudo state. (item enum: ``enter``, ``during``, ``exit``, ``during_aspect``)

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 1 boundary_only

**Example 1** (``boundary_only``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0; state Root { pseudo state __combo_user { enter { x = x + 1; } } state A; [*] -> A; }

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``move_action`` on ``lifecycle_action``: Move the action to the authored source or target state if it is business behavior rather than routing metadata.

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add business logic to generated combo relay pseudo states.

.. _diag-code-i-combo-pseudo-name-extended:

I_COMBO_PSEUDO_NAME_EXTENDED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_COMBO_PSEUDO_NAME_EXTENDED severity=info emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED pseudo_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED payload_digest type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED default_digest_size type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED final_digest_size type=int required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``partial_static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** Combo trigger expansion extended a generated relay name's digest prefix to avoid a same-scope name collision.

**LLM repair summary.** The combo expander found a same-scope name collision at the default digest length and deterministically used a longer digest prefix. This is informational and does not mean the model is invalid.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state where expansion allocated the relay.
   * - ``pseudo_name``
     - ``str``
     - yes
     - Final generated pseudo-state name after digest extension.
   * - ``payload_digest``
     - ``str``
     - yes
     - Full digest of the semantic payload that owns the relay.
   * - ``default_digest_size``
     - ``int``
     - yes
     - Default visible digest length before extension.
   * - ``final_digest_size``
     - ``int``
     - yes
     - Visible digest length used by the final generated name.

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 1 boundary_only

**Example 1** (``boundary_only``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       pseudo state __combo_root_a__e1_hbafca7f66598;
       [*] -> A;
       A -> B :: E1 + E2;
   }

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``keep_generated_name`` on ``pseudo_state``: Leave the extended generated name as-is unless you are manually rewriting the expanded relay chain.

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not shorten the digest manually; that can reintroduce the collision.

.. _diag-code-e-combo-pseudo-name-collision:

E_COMBO_PSEUDO_NAME_COLLISION
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_COMBO_PSEUDO_NAME_COLLISION severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION pseudo_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION payload_digest type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** Combo trigger expansion could not allocate a safe pseudo-state name even after extending to the full payload digest.

**LLM repair summary.** The combo expander first uses a short digest prefix and then lengthens it deterministically on collision. If the full digest still cannot identify a safe relay name in the owning scope, expansion fails rather than silently reusing the wrong pseudo state.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state where expansion attempted to add the pseudo state.
   * - ``pseudo_name``
     - ``str``
     - yes
     - Generated pseudo-state name that collided.
   * - ``payload_digest``
     - ``str``
     - yes
     - Full digest of the semantic payload that attempted to claim the name.

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state B; [*] -> A; A -> B :: E1 + E2; }

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``report_internal_collision`` on ``transition``: This is an internal collision guard. Keep the model unchanged and report the diagnostic, including ``refs.payload_digest``.

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not append an ad-hoc sequence number; user-visible combo names must remain deterministic.

.. _diag-code-w-combo-guard-const-true:

W_COMBO_GUARD_CONST_TRUE
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_GUARD_CONST_TRUE severity=warning emit_tier=static_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE origin_id type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE folded_value type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE trigger_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_TRUE value_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** SMT proves that a guard term inside a combo trigger is always ``true``. The term is redundant for the generated pseudo chain, and the primary span points at the original bracketed guard term.

**LLM repair summary.** SMT proves that a combo guard term is always true and does not constrain the combo chain.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``origin_id``
     - ``str``
     - yes
     - Stable identifier of the original combo transition.
   * - ``term_index``
     - ``int``
     - yes
     - Zero-based index of the constant guard term.
   * - ``term_text``
     - ``str``
     - yes
     - Canonical source text of the guard term.
   * - ``folded_value``
     - ``bool``
     - yes
     - Solver-proven guard value, always ``true`` for this code.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the original combo transition.
   * - ``trigger_span``
     - ``Span``
     - no
     - Source span of the combo trigger suffix.
   * - ``term_span``
     - ``Span``
     - no
     - Source span of the bracketed guard term.
   * - ``value_span``
     - ``Span``
     - no
     - Source span of the guard expression inside the brackets.

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + [x > 0 || x <= 0] + E2;
   }

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_guard_term`` on ``transition``: Remove the guard term if it was only a placeholder.

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a dummy variable dependency only to silence the diagnostic.

.. _diag-code-w-combo-guard-const-false:

W_COMBO_GUARD_CONST_FALSE
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_GUARD_CONST_FALSE severity=warning emit_tier=static_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE origin_id type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE folded_value type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE trigger_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_CONST_FALSE value_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** SMT proves that a guard term inside a combo trigger is always ``false``. Any combo branch that must pass through this term can never complete.

**LLM repair summary.** SMT proves that a combo guard term is always false, so the generated combo branch cannot complete past that term.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``origin_id``
     - ``str``
     - yes
     - Stable identifier of the original combo transition.
   * - ``term_index``
     - ``int``
     - yes
     - Zero-based index of the constant guard term.
   * - ``term_text``
     - ``str``
     - yes
     - Canonical source text of the guard term.
   * - ``folded_value``
     - ``bool``
     - yes
     - Solver-proven guard value, always ``false`` for this code.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the original combo transition.
   * - ``trigger_span``
     - ``Span``
     - no
     - Source span of the combo trigger suffix.
   * - ``term_span``
     - ``Span``
     - no
     - Source span of the bracketed guard term.
   * - ``value_span``
     - ``Span``
     - no
     - Source span of the guard expression inside the brackets.

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + [x > 0 && x <= 0] + E2;
   }

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_guard_term`` on ``transition``: Rewrite the guard so it can become true under some valid state.

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently remove the guard term — that would change the combo semantics.

.. _diag-code-w-combo-guard-prefix-implied:

W_COMBO_GUARD_PREFIX_IMPLIED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_GUARD_PREFIX_IMPLIED severity=warning emit_tier=static_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED origin_id type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED prior_term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED prior_term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED trigger_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED value_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED prior_term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_IMPLIED prior_value_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** In a side-effect-free combo prefix, prior guard terms imply a later guard term. The later guard is redundant under the current static approximation.

**LLM repair summary.** Earlier guard terms in the combo prefix already guarantee this later guard term when no relevant side effects can occur between them.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``origin_id``
     - ``str``
     - yes
     - Stable identifier of the original combo transition.
   * - ``term_index``
     - ``int``
     - yes
     - Zero-based index of the implied guard term.
   * - ``prior_term_index``
     - ``int``
     - yes
     - Zero-based index of the earliest prior guard term that makes the prefix implication or contradiction decisive.
   * - ``term_text``
     - ``str``
     - yes
     - Canonical source text of the implied guard term.
   * - ``prior_term_text``
     - ``str``
     - yes
     - Canonical source text of the prior guard term.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the original combo transition.
   * - ``trigger_span``
     - ``Span``
     - no
     - Source span of the combo trigger suffix.
   * - ``term_span``
     - ``Span``
     - no
     - Source span of the implied guard term.
   * - ``value_span``
     - ``Span``
     - no
     - Source span of the implied guard expression inside brackets.
   * - ``prior_term_span``
     - ``Span``
     - no
     - Source span of the prior guard term.
   * - ``prior_value_span``
     - ``Span``
     - no
     - Source span of the prior guard expression inside brackets.

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : [x > 0] + [x > -1];
   }

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_guard_term`` on ``transition``: Remove the later guard if it is intentionally redundant.

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not apply this reasoning across abstract/ref or unknown side-effect boundaries.

.. _diag-code-w-combo-guard-prefix-contradicts:

W_COMBO_GUARD_PREFIX_CONTRADICTS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_GUARD_PREFIX_CONTRADICTS severity=warning emit_tier=static_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS origin_id type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS prior_term_index type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS prior_term_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS trigger_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS value_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS prior_term_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_GUARD_PREFIX_CONTRADICTS prior_value_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** In a side-effect-free combo prefix, prior guard terms contradict a later guard term. The generated combo branch cannot complete through that term under the current static approximation.

**LLM repair summary.** Earlier guard terms in the combo prefix make this later guard impossible when no relevant side effects can occur between them.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``origin_id``
     - ``str``
     - yes
     - Stable identifier of the original combo transition.
   * - ``term_index``
     - ``int``
     - yes
     - Zero-based index of the contradictory guard term.
   * - ``prior_term_index``
     - ``int``
     - yes
     - Zero-based index of the earliest prior guard term that makes the prefix implication or contradiction decisive.
   * - ``term_text``
     - ``str``
     - yes
     - Canonical source text of the contradictory guard term.
   * - ``prior_term_text``
     - ``str``
     - yes
     - Canonical source text of the prior guard term.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the original combo transition.
   * - ``trigger_span``
     - ``Span``
     - no
     - Source span of the combo trigger suffix.
   * - ``term_span``
     - ``Span``
     - no
     - Source span of the contradictory guard term.
   * - ``value_span``
     - ``Span``
     - no
     - Source span of the contradictory guard expression inside brackets.
   * - ``prior_term_span``
     - ``Span``
     - no
     - Source span of the prior guard term.
   * - ``prior_value_span``
     - ``Span``
     - no
     - Source span of the prior guard expression inside brackets.

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : [x > 0] + [x < 0];
   }

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_guard_term`` on ``transition``: Rewrite the later guard if it was meant to describe a reachable branch.

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not apply this reasoning across abstract/ref or unknown side-effect boundaries.

Forced transition diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-forced-transition-expansion:

E_FORCED_TRANSITION_EXPANSION
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_FORCED_TRANSITION_EXPANSION severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_FORCED_TRANSITION_EXPANSION original_raw type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_FORCED_TRANSITION_EXPANSION reason type=str required=true enum=src_not_found|tgt_not_found|src_is_root|wildcard_no_descendants item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A forced transition (`!State -> ...` or `!*`) cannot be expanded because the source or target reference is invalid.

**LLM repair summary.** A forced transition (``!Source -> Target`` or ``!* -> Target``) failed to expand cleanly — typically because the source name cannot be found, or because the expansion would create an empty/inconsistent fan-out under the current scope.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``original_raw``
     - ``str``
     - yes
     - Raw forced-transition text as written.
   * - ``reason``
     - ``str``
     - yes
     - Short tag describing why expansion failed. (enum: ``src_not_found``, ``tgt_not_found``, ``src_is_root``, ``wildcard_no_descendants``)

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; !NoSuch -> A; }

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_source`` on ``forced_transition``: Confirm the ``!Name`` source is a real state inside the current composite scope. ``!*`` only matches direct substates; deeper descendants need explicit names.

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add an ``effect { ... }`` block to a forced transition — forced transitions cannot carry effects and the expansion would fail anyway.

.. _diag-code-w-forced-never-expands:

W_FORCED_NEVER_EXPANDS
^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_NEVER_EXPANDS severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_FORCED_NEVER_EXPANDS state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_NEVER_EXPANDS original_raw type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A forced transition declaration has no concrete child state in its declaration scope to expand from.

**LLM repair summary.** The forced transition declaration expands to zero concrete transitions, so it has no runtime effect.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state containing the forced transition.
   * - ``original_raw``
     - ``str``
     - yes
     - Original forced transition DSL text.

.. diagnostics-example W_FORCED_NEVER_EXPANDS 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A {
           !* -> [*];
       }
       [*] -> A;
   }

.. diagnostics-example W_FORCED_NEVER_EXPANDS 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``move_transition`` on ``forced_transition``: Move the forced transition to a composite scope that owns matching children.

.. diagnostics-example W_FORCED_NEVER_EXPANDS 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not leave a zero-expansion forced transition as documentation.

.. _diag-code-w-forced-overrides-normal:

W_FORCED_OVERRIDES_NORMAL
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_OVERRIDES_NORMAL severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL forced_declaration_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL normal_transition_span type=Span required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``transition``.

**Meaning.** A forced transition expands to the same source, target, event, and guard as a normal transition.

**LLM repair summary.** The forced transition duplicates a normal transition, which can make the forced declaration misleading or redundant.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``from_path``
     - ``str``
     - yes
     - Dotted source state path.
   * - ``to_path``
     - ``str``
     - yes
     - Dotted target state path.
   * - ``forced_declaration_span``
     - ``Span``
     - no
     - Source span of the forced transition when available.
   * - ``normal_transition_span``
     - ``Span``
     - no
     - Source span of the normal transition when available.

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Go;
       !A -> B :: Go;
   }

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_duplicate`` on ``forced_transition``: Remove the forced transition if the normal one already covers it.

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not keep both unless the generated runtime intentionally treats forced metadata differently.

.. _diag-code-w-forced-guard-unsat:

W_FORCED_GUARD_UNSAT
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_GUARD_UNSAT severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_FORCED_GUARD_UNSAT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT transition_summary type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT scope type=str required=true enum=dsl_def_init_only item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** A forced-transition guard cannot be satisfied under declaration initializer values.

**LLM repair summary.** The forced transition expands structurally, but its guard is false under top-level declaration initializers.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the forced transition.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.
   * - ``scope``
     - ``str``
     - yes
     - Initial-value scope used by the verify algorithm. (enum: ``dsl_def_init_only``)

.. diagnostics-example W_FORCED_GUARD_UNSAT 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       !A -> B : if [x > 0];
   }

.. diagnostics-example W_FORCED_GUARD_UNSAT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``adjust_initializer`` on ``variable_definition``: Change the initializer if the forced transition must be possible at startup.

.. diagnostics-example W_FORCED_GUARD_UNSAT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not delete the forced transition solely because it is impossible at declaration time; later runtime values may still matter for normal guards.

Guard, effect, and solver diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-guard-const-false:

W_GUARD_CONST_FALSE
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_CONST_FALSE severity=warning emit_tier=static_pipeline capability=const_fold span_object=guard_expression
.. diagnostics-ref W_GUARD_CONST_FALSE transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE folded_value type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE guard_text type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``const_fold``; span object ``guard_expression``.

**Meaning.** A transition's guard condition folds to the boolean literal ``false`` using the built-in constant folder, so the transition can never fire. The folder is intentionally side-effect free: it handles literal-only boolean, comparison, arithmetic, bitwise, unary, and ternary expressions, but does not evaluate variables, functions, solvers, or runtime state.

**LLM repair summary.** The transition's guard is statically known to be ``false`` and the transition is effectively dead code.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the transition declaration.
   * - ``folded_value``
     - ``bool``
     - yes
     - Constant-folded guard value (always ``false``).
   * - ``from_path``
     - ``str``
     - no
     - Source state path of the transition, or ``[*]`` for an initial transition.
   * - ``to_path``
     - ``str``
     - no
     - Target state path of the transition, or ``[*]`` for an exit transition.
   * - ``guard_text``
     - ``str``
     - no
     - Normalized guard expression text used to disambiguate spanless inspect diagnostics. Pyfcstm and jsfcstm both render this with the shared inspect expression format: canonical boolean/operator spelling, decimal integer literals, and normalized spacing.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example W_GUARD_CONST_FALSE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(0x0F & 0xF0) != 0];
   }

.. diagnostics-example W_GUARD_CONST_FALSE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_guard`` on ``transition``: Rewrite the guard so it can become true under some valid state.

.. diagnostics-example W_GUARD_CONST_FALSE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently remove the guard — that would change the semantics.

.. _diag-code-w-guard-const-true:

W_GUARD_CONST_TRUE
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_CONST_TRUE severity=warning emit_tier=static_pipeline capability=const_fold span_object=guard_expression
.. diagnostics-ref W_GUARD_CONST_TRUE transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE guard_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE folded_value type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE guard_text type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_TRUE transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``const_fold``; span object ``guard_expression``.

**Meaning.** A transition's guard condition folds to the boolean literal ``true`` using the built-in constant folder, so the guard is redundant for all runtime states covered by that literal-only expression.

**LLM repair summary.** The transition's guard is statically known to be ``true`` and does not constrain the transition.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the transition declaration.
   * - ``guard_span``
     - ``Span``
     - no
     - Source span of the removable guard suffix, including the leading trigger separator when needed. This is reserved for future emitters that can provide a stable guard-only span; the current inspect emitters intentionally omit it.
   * - ``folded_value``
     - ``bool``
     - yes
     - Constant-folded guard value (always ``true``).
   * - ``from_path``
     - ``str``
     - no
     - Source state path of the transition, or ``[*]`` for an initial transition.
   * - ``to_path``
     - ``str``
     - no
     - Target state path of the transition, or ``[*]`` for an exit transition.
   * - ``guard_text``
     - ``str``
     - no
     - Normalized guard expression text used to disambiguate spanless inspect diagnostics. Pyfcstm and jsfcstm both render this with the shared inspect expression format: canonical boolean/operator spelling, decimal integer literals, and normalized spacing.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example W_GUARD_CONST_TRUE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(1 + 2) == 3];
   }

.. diagnostics-example W_GUARD_CONST_TRUE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_guard`` on ``transition``: Remove the guard if the transition is meant to be unconditional.

.. diagnostics-example W_GUARD_CONST_TRUE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a dummy variable dependency only to silence the diagnostic.

.. _diag-code-w-guard-vars-never-change:

W_GUARD_VARS_NEVER_CHANGE
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_VARS_NEVER_CHANGE severity=warning emit_tier=static_pipeline capability=pure_static span_object=guard_expression
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE guard_vars type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``guard_expression``.

**Meaning.** A transition guard reads variables that are never changed by any lifecycle action or transition effect, so the guard only depends on initial values.

**LLM repair summary.** This guard is controlled only by initial variable values. If those values never change, the transition condition is effectively fixed.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``from_path``
     - ``str``
     - yes
     - Source state path of the transition, or [*] for an entry marker.
   * - ``to_path``
     - ``str``
     - yes
     - Target state path of the transition, or [*] for an exit marker.
   * - ``guard_vars``
     - ``list[str]``
     - yes
     - Guard variables that never change.

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_write`` on ``action_or_effect``: Add the missing state update if the guard should evolve at runtime.

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a meaningless self-assignment; it does not model a real change.

.. _diag-code-w-effect-self-assign:

W_EFFECT_SELF_ASSIGN
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_EFFECT_SELF_ASSIGN severity=warning emit_tier=static_pipeline capability=pure_static span_object=effect_statement
.. diagnostics-ref W_EFFECT_SELF_ASSIGN state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN generated_state_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN generated_from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN generated_to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN combo_origin_id type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN combo_owner_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN effect_self_assign_anchor type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN suggested_fix type=dict required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SELF_ASSIGN transition_index type=int required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``effect_statement``.

**Meaning.** An effect statement assigns a variable directly to itself.

**LLM repair summary.** The assignment does not change model state and is likely dead code.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Source state path when known.
   * - ``from_path``
     - ``str``
     - no
     - Public source path for combo terminal effect diagnostics after authored-subject remapping. Ordinary self-assignment diagnostics may omit this field and use ``state_path`` only.
   * - ``generated_state_path``
     - ``str``
     - no
     - Generated combo pseudo state path kept only as secondary debug provenance after the public subject is remapped.
   * - ``generated_from_path``
     - ``str``
     - no
     - Generated transition source path kept as secondary debug provenance.
   * - ``generated_to_path``
     - ``str``
     - no
     - Generated transition target path kept as secondary debug provenance.
   * - ``combo_origin_id``
     - ``str``
     - no
     - Original combo transition identifier for a generated terminal effect.
   * - ``combo_owner_path``
     - ``str``
     - no
     - Owner composite path for entry combo diagnostics whose public subject is the initial marker ``[*]``.
   * - ``transition_span``
     - ``Span``
     - no
     - Source span of the transition containing the effect.
   * - ``var_name``
     - ``str``
     - yes
     - Variable assigned to itself.
   * - ``effect_self_assign_anchor``
     - ``str``
     - no
     - Variable name repeated only when the self-assignment occurrence can be uniquely mapped back to a non-initial effect statement for the same source state and variable.
   * - ``suggested_fix``
     - ``dict``
     - no
     - Structured quick-fix payload for removing the no-op effect statement.
   * - ``transition_index``
     - ``int``
     - no
     - Zero-based index in parent-first model transition order, including expanded forced transitions at their declaring state before ordinary transitions and descendant-state transitions. This is used only as a source-range disambiguation hint when spans are unavailable.

.. diagnostics-example W_EFFECT_SELF_ASSIGN 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B effect { x = x; }
   }

.. diagnostics-example W_EFFECT_SELF_ASSIGN 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_statement`` on ``effect_statement``: Delete the self-assignment.

.. diagnostics-example W_EFFECT_SELF_ASSIGN 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not replace it with another no-op expression.

.. _diag-code-w-dead-guard:

W_DEAD_GUARD
^^^^^^^^^^^^

.. diagnostics-meta W_DEAD_GUARD severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_DEAD_GUARD algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD transition_summary type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** A transition guard is unsatisfiable under model variable type and runtime-definedness constraints.

**LLM repair summary.** SMT proves the guard cannot become true for any valid variable valuation. This differs from W_GUARD_CONST_FALSE, which only reports literal-only guards folded syntactically to false.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the guarded transition.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.

.. diagnostics-example W_DEAD_GUARD 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x > 1 && x < 0];
   }

.. diagnostics-example W_DEAD_GUARD 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_guard`` on ``transition``: Relax or correct the contradictory guard condition.

.. diagnostics-example W_DEAD_GUARD 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not replace the guard with true unless the transition really should become unconditional.

.. _diag-code-w-guard-tautology:

W_GUARD_TAUTOLOGY
^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_TAUTOLOGY severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_GUARD_TAUTOLOGY algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY transition_summary type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``guard_expression``.

**Meaning.** A transition guard is true for every variable valuation that satisfies model type and runtime-definedness constraints.

**LLM repair summary.** SMT proves the guard is always true under the modeled variable constraints. This differs from W_GUARD_CONST_TRUE, which only reports literal-only guards folded syntactically to true.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the guarded transition.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.

.. diagnostics-example W_GUARD_TAUTOLOGY 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x >= 0 || x < 0];
   }

.. diagnostics-example W_GUARD_TAUTOLOGY 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_redundant_guard`` on ``transition``: Remove the guard if the transition should be unconditional.

.. diagnostics-example W_GUARD_TAUTOLOGY 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not assume every tautological guard is wrong; it may document intent.

.. _diag-code-w-effect-smt-no-op:

W_EFFECT_SMT_NO_OP
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_EFFECT_SMT_NO_OP severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=effect_statement
.. diagnostics-ref W_EFFECT_SMT_NO_OP algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP transition_summary type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``effect_statement``.

**Meaning.** A transition effect leaves all model variables unchanged for every guarded, runtime-defined execution.

**LLM repair summary.** Symbolic execution proves the effect does not change any persistent model variable when its guard is enabled.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the transition with the effect.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.

.. diagnostics-example W_EFFECT_SMT_NO_OP 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x >= 0] effect { x = x + 0; };
   }

.. diagnostics-example W_EFFECT_SMT_NO_OP 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_effect`` on ``effect_block``: Remove the effect if it is dead or only placeholder logic.

.. diagnostics-example W_EFFECT_SMT_NO_OP 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not report block-local temporary-only changes as state changes; they disappear after the effect block.

.. _diag-code-i-effect-guard-contradict:

I_EFFECT_GUARD_CONTRADICT
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_EFFECT_GUARD_CONTRADICT severity=info emit_tier=verify_pipeline capability=requires_solver span_object=effect_statement
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT transition_summary type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``effect_statement``.

**Meaning.** A transition effect makes the same transition guard false after every guarded, runtime-defined execution.

**LLM repair summary.** The effect immediately invalidates the guard that enabled the transition. This may be a deliberate one-shot or latch reset pattern.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``transition``
     - ``dict``
     - yes
     - Raw verify transition payload for the transition with the effect.
   * - ``transition_summary``
     - ``str``
     - yes
     - Stable human-readable transition summary derived from the raw payload.

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x > 0] effect { x = 0; };
   }

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``review_one_shot`` on ``transition``: Confirm the effect is meant to falsify the enabling guard.

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not treat this info as an automatic defect; guard-reset effects are often intentional.

Lifecycle, aspect, and composite diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-during-aspect-invalid:

E_DURING_ASPECT_INVALID
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DURING_ASPECT_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=lifecycle_action
.. diagnostics-ref E_DURING_ASPECT_INVALID state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DURING_ASPECT_INVALID state_kind type=str required=true enum=leaf|composite item_enum=- exact_values=-
.. diagnostics-ref E_DURING_ASPECT_INVALID aspect type=str_or_null required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``lifecycle_action``.

**Meaning.** A `during` block is declared inconsistently with the host state's leaf/composite kind. Leaf states must use `during { ... }` without an aspect modifier; composite states must use `during before { ... }` or `during after { ... }` (the aspect is mandatory on composites). The global ``>> during before/after`` aspect form is **also** invalid on a leaf state — aspect actions fan out to every descendant leaf, and a leaf has nothing to fan into.

**LLM repair summary.** A ``during before`` / ``during after`` or ``>> during ...`` aspect declaration was placed on a state that cannot legally receive it (typically a leaf state with no descendant for the aspect to fan out to).

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the offending state.
   * - ``state_kind``
     - ``str``
     - yes
     - Kind of the host state. (enum: ``leaf``, ``composite``)
   * - ``aspect``
     - ``str_or_null``
     - no
     - The aspect token that was actually used. ``'before'`` or ``'after'`` for ``during before`` / ``during after`` and ``>> during before/after``; ``null`` when the user wrote a bare ``during`` on a composite state. ``null`` is intentional — the consumer should branch on the bare-during case rather than treat it as an enum value.

.. diagnostics-example E_DURING_ASPECT_INVALID 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A {
           during before { }
       }
   }

.. diagnostics-example E_DURING_ASPECT_INVALID 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``move_to_composite`` on ``aspect_declaration``: Aspect actions only make sense on composite states. Move the declaration to a composite ancestor whose descendants should receive the aspect.

.. diagnostics-example E_DURING_ASPECT_INVALID 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not convert the leaf into a composite just to host the aspect — that changes the runtime entry/exit semantics.

.. _diag-code-e-pseudo-not-leaf:

E_PSEUDO_NOT_LEAF
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_PSEUDO_NOT_LEAF severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_PSEUDO_NOT_LEAF state_path type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``error``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A state was declared with the `pseudo` keyword but has nested substates. Pseudo states must be leaves: they skip ancestor `>> during` aspects and only make sense without inner structure.

**LLM repair summary.** A ``pseudo state`` declaration was given a composite body (or otherwise treated as if it had descendants). Pseudo states must be leaves: they cannot host substates because their semantics explicitly skip ancestor ``>> during`` aspects.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the offending pseudo state.

.. diagnostics-example E_PSEUDO_NOT_LEAF 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       pseudo state Outer {
           state Inner;
           [*] -> Inner;
       }
   }

.. diagnostics-example E_PSEUDO_NOT_LEAF 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``drop_pseudo_marker`` on ``state_definition``: If the state genuinely needs substates, remove the ``pseudo`` keyword and treat it as a normal composite.

.. diagnostics-example E_PSEUDO_NOT_LEAF 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not rely on pseudo states for normal hierarchy modeling — they exist solely to bypass ``>> during`` aspect application.

.. _diag-code-w-during-const-assign:

W_DURING_CONST_ASSIGN
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DURING_CONST_ASSIGN severity=warning emit_tier=static_pipeline capability=const_fold span_object=lifecycle_action
.. diagnostics-ref W_DURING_CONST_ASSIGN state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DURING_CONST_ASSIGN var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DURING_CONST_ASSIGN value type=number required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``const_fold``; span object ``lifecycle_action``.

**Meaning.** A concrete ``during`` action assigns a variable to the same literal-only numeric value every cycle. The analyzer only checks the direct statements in ordinary ``during { ... }`` blocks; it skips abstract actions, refs, composite ``during before`` / ``during after`` actions, aspect actions, functions, variables, and nested control flow.

**LLM repair summary.** The during block writes the same constant numeric value on every cycle, which often indicates initialization logic was placed in ``during`` instead of ``enter``.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the state that owns the during action.
   * - ``var_name``
     - ``str``
     - yes
     - Variable assigned by the constant during statement.
   * - ``value``
     - ``number``
     - yes
     - JSON-stable numeric value assigned on every cycle.

.. diagnostics-example W_DURING_CONST_ASSIGN 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int counter = 0;
   state Root {
       state Idle {
           during { counter = (2 + 3) * 4; }
       }
       [*] -> Idle;
   }

.. diagnostics-example W_DURING_CONST_ASSIGN 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``move_to_enter`` on ``action``: Move the assignment to ``enter`` if it should run once on state entry.

.. diagnostics-example W_DURING_CONST_ASSIGN 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not suppress the warning by adding a meaningless arithmetic no-op.

.. _diag-code-w-aspect-no-descendant-leaf:

W_ASPECT_NO_DESCENDANT_LEAF
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_ASPECT_NO_DESCENDANT_LEAF severity=warning emit_tier=static_pipeline capability=pure_static span_object=lifecycle_action
.. diagnostics-ref W_ASPECT_NO_DESCENDANT_LEAF composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_ASPECT_NO_DESCENDANT_LEAF aspect type=str required=true enum=before|after item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``lifecycle_action``.

**Meaning.** A ``>> during`` aspect is attached to a state with no descendant non-pseudo leaf states, so the aspect cannot affect any leaf cycle.

**LLM repair summary.** The aspect action has no descendant leaf state to wrap, so it has no modeled runtime target.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``composite_path``
     - ``str``
     - yes
     - Dotted path of the state declaring the aspect.
   * - ``aspect``
     - ``str``
     - yes
     - Aspect direction. (enum: ``before``, ``after``)

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       pseudo state Marker;
       [*] -> Marker;
       >> during before { }
   }

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_leaf`` on ``composite_state``: Add the intended descendant leaf state under this composite.

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not replace it with a normal during action unless the execution semantics really should change.

.. _diag-code-i-enter-during-contradict:

I_ENTER_DURING_CONTRADICT
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_ENTER_DURING_CONTRADICT severity=info emit_tier=verify_pipeline capability=requires_solver span_object=lifecycle_action
.. diagnostics-ref I_ENTER_DURING_CONTRADICT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT condition type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT condition_source type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT branch_taken type=str required=true enum=true|false item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``lifecycle_action``.

**Meaning.** Entry-time assignments make a first-cycle during branch condition predetermined; the enter postcondition does not leave both during branches feasible.

**LLM repair summary.** After entering the leaf, the first during cycle already has a fixed branch decision. This may be intentional initialization logic, but the branch is not genuinely conditional on the first cycle.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``state_path``
     - ``str``
     - yes
     - Dotted leaf state path inspected by the lifecycle algorithm.
   * - ``condition``
     - ``str``
     - yes
     - First-cycle during condition proven predetermined.
   * - ``condition_source``
     - ``str``
     - yes
     - Source label for the condition inside the during operation block.
   * - ``branch_taken``
     - ``str``
     - yes
     - Branch direction forced after entry. (enum: ``true``, ``false``)

.. diagnostics-example I_ENTER_DURING_CONTRADICT 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A {
           enter { x = 1; }
           during {
               if [x > 0] { x = x + 1; } else { x = x - 1; }
           }
       }
       [*] -> A;
   }

.. diagnostics-example I_ENTER_DURING_CONTRADICT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``review_enter_during_relation`` on ``lifecycle_action``: Check whether enter assignments intentionally force the first during branch.

.. diagnostics-example I_ENTER_DURING_CONTRADICT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not remove the enter action just to make the first-cycle branch variable; entry side effects may be required.

.. _diag-code-w-composite-init-incomplete:

W_COMPOSITE_INIT_INCOMPLETE
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMPOSITE_INIT_INCOMPLETE severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=composite_block
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE init_transition_count type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE init_transitions type=list[str] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE witness type=str_or_null required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``requires_solver``; span object ``composite_block``.

**Meaning.** A composite state's initial transitions do not jointly cover all variable and event inputs.

**LLM repair summary.** There is a variable/event assignment for which none of the composite initial transitions can fire, so entry can get stuck at the composite.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``smt_local``)
   * - ``composite_path``
     - ``str``
     - yes
     - Dotted composite state path whose initial transitions have a coverage gap.
   * - ``init_transition_count``
     - ``int``
     - yes
     - Number of initial transitions considered for the composite.
   * - ``init_transitions``
     - ``list[str]``
     - yes
     - Stable summaries of the initial transitions considered.
   * - ``witness``
     - ``str_or_null``
     - no
     - Solver model demonstrating an uncovered input valuation, when available.

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A : if [x > 0];
       [*] -> B : if [x < 0];
   }

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_catch_all_initial`` on ``composite_state``: Add an unconditional fallback initial transition if one child should be the default.

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add overlapping initial transitions without reviewing declaration order and guard intent.

Data-flow diagnostics
~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-unreferenced-var:

W_UNREFERENCED_VAR
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNREFERENCED_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_UNREFERENCED_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR init_value type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR definition_delete_anchor type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR suggested_fix type=dict required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``variable_declaration``.

**Meaning.** A variable cannot affect any transition guard either directly or through the action/effect use-def graph, and no abstract action is visible that might use it outside the DSL.

**LLM repair summary.** This variable does not participate in model decisions. It is dead from the DSL's guard-affect data-flow perspective.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - Variable name.
   * - ``init_value``
     - ``str``
     - yes
     - Source text of the initial value.
   * - ``definition_delete_anchor``
     - ``str``
     - no
     - Variable name repeated only when the declaration has no DSL reads or writes, so deleting the declaration alone is a safe quick-fix.
   * - ``suggested_fix``
     - ``dict``
     - no
     - Structured quick-fix payload for removing the variable definition.

.. diagnostics-example W_UNREFERENCED_VAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int unused = 0;
   def int ready = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example W_UNREFERENCED_VAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``remove_variable`` on ``variable_definition``: Remove the variable and related writes if it was speculative scaffolding.

.. diagnostics-example W_UNREFERENCED_VAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a dummy guard reference only to silence the diagnostic.

.. _diag-code-i-unreferenced-var-maybe-abstract:

I_UNREFERENCED_VAR_MAYBE_ABSTRACT
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_UNREFERENCED_VAR_MAYBE_ABSTRACT severity=info emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref I_UNREFERENCED_VAR_MAYBE_ABSTRACT var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_UNREFERENCED_VAR_MAYBE_ABSTRACT abstract_actions_in_scope type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``variable_declaration``.

**Meaning.** A variable cannot affect any transition guard through DSL data-flow, but at least one visible abstract action may use it outside the DSL.

**LLM repair summary.** This variable is unused by DSL guard-affect data-flow, but abstract action implementations may still use it.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - Variable name.
   * - ``abstract_actions_in_scope``
     - ``list[str]``
     - yes
     - Abstract action owners that may access the variable. FCSTM variables are global, so this is the full machine abstract-action inventory.

.. diagnostics-example I_UNREFERENCED_VAR_MAYBE_ABSTRACT 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int maybe_external = 0;
   def int ready = 0;
   state Root {
       state A { enter abstract ExternalHook; }
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example I_UNREFERENCED_VAR_MAYBE_ABSTRACT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``inspect_abstract_action`` on ``abstract_action``: Check the external implementation before removing the variable.

.. diagnostics-example I_UNREFERENCED_VAR_MAYBE_ABSTRACT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not remove the variable without checking the abstract implementation.

.. _diag-code-w-unwritten-read-var:

W_UNWRITTEN_READ_VAR
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNWRITTEN_READ_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_UNWRITTEN_READ_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNWRITTEN_READ_VAR read_states type=list[str] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNWRITTEN_READ_VAR init_value type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``variable_declaration``.

**Meaning.** A variable is read in guards or actions but is never written by any lifecycle action or transition effect.

**LLM repair summary.** The variable is used as input but never updated after its initial definition, so model behavior may be accidentally constant.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - Variable name.
   * - ``read_states``
     - ``list[str]``
     - yes
     - State paths where the variable is read.
   * - ``init_value``
     - ``str``
     - yes
     - Source text of the initial value.

.. diagnostics-example W_UNWRITTEN_READ_VAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example W_UNWRITTEN_READ_VAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_write`` on ``action_or_effect``: Add the intended update if the variable should change.

.. diagnostics-example W_UNWRITTEN_READ_VAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a meaningless self-assignment.

.. _diag-code-w-write-only-var:

W_WRITE_ONLY_VAR
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_WRITE_ONLY_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_WRITE_ONLY_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_WRITE_ONLY_VAR written_states type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``variable_declaration``.

**Meaning.** A variable is written by actions or effects but is never read by any guard, action, or transition effect expression.

**LLM repair summary.** The variable is updated but never influences model behavior.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - Variable name.
   * - ``written_states``
     - ``list[str]``
     - yes
     - State paths where the variable is written.

.. diagnostics-example W_WRITE_ONLY_VAR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int counter = 0;
   state Root {
       state A { during { counter = 1; } }
       [*] -> A;
   }

.. diagnostics-example W_WRITE_ONLY_VAR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_read`` on ``guard_or_action``: Read the variable where it should affect behavior.

.. diagnostics-example W_WRITE_ONLY_VAR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add an unused read just to silence the warning.

Numeric and target-profile diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-literal-type-narrowing:

W_LITERAL_TYPE_NARROWING
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_LITERAL_TYPE_NARROWING severity=warning emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref W_LITERAL_TYPE_NARROWING var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LITERAL_TYPE_NARROWING target_type type=str required=true enum=int item_enum=- exact_values=-
.. diagnostics-ref W_LITERAL_TYPE_NARROWING source_expr type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``expression``.

**Meaning.** An ``int`` variable is initialized or assigned directly from a floating-point literal, which can imply silent narrowing in generated code. Compound expressions containing floating-point literals are out of scope for this warning.

**LLM repair summary.** A direct float literal value flows into an ``int`` variable. The model may truncate or generate target-language code with a narrowing conversion; compound expressions such as ``3.0 + 0.5`` are intentionally outside this warning's scope.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``var_name``
     - ``str``
     - yes
     - Target variable name.
   * - ``target_type``
     - ``str``
     - yes
     - Declared target variable type. (enum: ``int``)
   * - ``source_expr``
     - ``str``
     - yes
     - Source text of the direct float literal.

.. diagnostics-example W_LITERAL_TYPE_NARROWING 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int truncated = 3.5;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_LITERAL_TYPE_NARROWING 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``change_type`` on ``variable_definition``: Use ``def float`` when fractional values are intended.

.. diagnostics-example W_LITERAL_TYPE_NARROWING 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not silently rely on target-language truncation rules.

.. _diag-code-w-numeric-literal-out-of-target-range:

W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE severity=warning emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE target_family type=str required=true enum=c_family item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE target_templates type=list[str] required=true enum=- item_enum=c|c_poll|cpp|cpp_poll exact_values=c|c_poll|cpp|cpp_poll
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE runtime_note type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE context type=str required=true enum=var_initializer|guard|transition_effect|lifecycle_action item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE statement_kind type=str required=false enum=operation_assignment item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE expr_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE literal_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE target_bits type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE signed type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE min_value_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE max_value_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE var_name type=str required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``expression``.

**Meaning.** An integer literal that would be rendered into a C/C++ family template falls outside the default ``PYFCSTM_GENERATED_INT64`` signed range. This warning is target-profile-specific: Python generated runtimes may not have the same fixed-width integer carrying risk.

**LLM repair summary.** A literal intended for C/C++ generated code exceeds the default 64-bit signed integer profile. Treat this as a C/C++ deployment-profile warning, not as proof that Python generated code is invalid.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``target_family``
     - ``str``
     - yes
     - Target family whose default deployment profile owns this risk. (enum: ``c_family``)
   * - ``target_templates``
     - ``list[str]``
     - yes
     - Ordered target templates covered by this default C/C++ profile: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``. (item enum: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``; exact: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``)
   * - ``runtime_note``
     - ``str``
     - yes
     - Human-readable note that this is a C/C++ deployment-profile risk and that Python generated runtimes may not have the same risk.
   * - ``context``
     - ``str``
     - yes
     - Expression location where the literal appears. (enum: ``var_initializer``, ``guard``, ``transition_effect``, ``lifecycle_action``)
   * - ``statement_kind``
     - ``str``
     - no
     - Statement shape when the expression is an operation assignment RHS. (enum: ``operation_assignment``)
   * - ``expr_text``
     - ``str``
     - yes
     - Source text of the expression containing the literal.
   * - ``literal_text``
     - ``str``
     - yes
     - Source text of the integer literal after applying a unary sign when present.
   * - ``target_bits``
     - ``int``
     - yes
     - Target integer width in bits.
   * - ``signed``
     - ``bool``
     - yes
     - Whether the target integer profile is signed.
   * - ``min_value_text``
     - ``str``
     - yes
     - Decimal text of the minimum representable target value.
   * - ``max_value_text``
     - ``str``
     - yes
     - Decimal text of the maximum representable target value.
   * - ``var_name``
     - ``str``
     - no
     - Variable receiving the literal when the location can be named.

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int too_large = 9223372036854775808;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``reduce_literal`` on ``expression``: Keep integer literals within the documented C/C++ target range when deploying to C-family templates.

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not describe this as a target-independent FCSTM model error; the risk is tied to the C/C++ default integer profile.

.. _diag-code-w-numeric-constant-division-by-zero:

W_NUMERIC_CONSTANT_DIVISION_BY_ZERO
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NUMERIC_CONSTANT_DIVISION_BY_ZERO severity=warning emit_tier=static_pipeline capability=const_fold span_object=expression
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO target_family type=str required=true enum=c_family item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO target_templates type=list[str] required=true enum=- item_enum=c|c_poll|cpp|cpp_poll exact_values=c|c_poll|cpp|cpp_poll
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO runtime_note type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO context type=str required=true enum=var_initializer|guard|transition_effect|lifecycle_action item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO statement_kind type=str required=false enum=operation_assignment item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO expr_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO operator type=str required=true enum=/|% item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_CONSTANT_DIVISION_BY_ZERO rhs_text type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``const_fold``; span object ``expression``.

**Meaning.** A ``/`` or ``%`` operation has a right-hand side that the lightweight literal-only constant folder can classify as zero. This is reported as a C/C++ deployment-profile risk because generated C/C++ code needs an explicit definition or failure channel; Python runtime exception semantics are different.

**LLM repair summary.** A division or modulo RHS is statically zero under the lightweight literal-only folder. For C/C++ generated code this needs a design fix or explicit failure policy; do not conflate it with Python's exception model.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``target_family``
     - ``str``
     - yes
     - Target family whose default deployment profile owns this risk. (enum: ``c_family``)
   * - ``target_templates``
     - ``list[str]``
     - yes
     - Ordered target templates covered by this default C/C++ profile: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``. (item enum: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``; exact: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``)
   * - ``runtime_note``
     - ``str``
     - yes
     - Human-readable note that this is a C/C++ deployment-profile risk and that Python generated runtimes may not have the same failure contract.
   * - ``context``
     - ``str``
     - yes
     - Expression location where the operator appears. (enum: ``var_initializer``, ``guard``, ``transition_effect``, ``lifecycle_action``)
   * - ``statement_kind``
     - ``str``
     - no
     - Statement shape when the expression is an operation assignment RHS. (enum: ``operation_assignment``)
   * - ``expr_text``
     - ``str``
     - yes
     - Source text of the expression containing the operation.
   * - ``operator``
     - ``str``
     - yes
     - Operator whose right-hand side folded to zero. (enum: ``/``, ``%``)
   * - ``rhs_text``
     - ``str``
     - yes
     - Source text of the right-hand side that folded to zero.

.. diagnostics-example W_NUMERIC_CONSTANT_DIVISION_BY_ZERO 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int result = 0;
   def int input = 1;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B effect { result = input / (1 - 1); };
   }

.. diagnostics-example W_NUMERIC_CONSTANT_DIVISION_BY_ZERO 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``fix_denominator`` on ``expression``: Replace the zero RHS with a non-zero expression or guard the operation before C/C++ deployment.

.. diagnostics-example W_NUMERIC_CONSTANT_DIVISION_BY_ZERO 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not require the whole expression to be literal-only; only the RHS of ``/`` or ``%`` needs to fold to zero.

.. _diag-code-w-numeric-shift-count-out-of-target-range:

W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE severity=warning emit_tier=static_pipeline capability=const_fold span_object=expression
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE target_family type=str required=true enum=c_family item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE target_templates type=list[str] required=true enum=- item_enum=c|c_poll|cpp|cpp_poll exact_values=c|c_poll|cpp|cpp_poll
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE runtime_note type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE context type=str required=true enum=var_initializer|guard|transition_effect|lifecycle_action item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE statement_kind type=str required=false enum=operation_assignment item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE expr_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE operator type=str required=true enum=<<|>> item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE target_bits type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE shift_count_text type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``const_fold``; span object ``expression``.

**Meaning.** A shift count folds to a constant below zero or not less than the default C/C++ target integer width. This is a C/C++ 64-bit deployment-profile portability risk; Python big-integer shifting is not the same target contract.

**LLM repair summary.** A shift count is statically outside the C/C++ default 64-bit profile. Treat this as a target-profile portability warning, not as a Python generated-runtime error.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``target_family``
     - ``str``
     - yes
     - Target family whose default deployment profile owns this risk. (enum: ``c_family``)
   * - ``target_templates``
     - ``list[str]``
     - yes
     - Ordered target templates covered by this default C/C++ profile: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``. (item enum: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``; exact: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``)
   * - ``runtime_note``
     - ``str``
     - yes
     - Human-readable note that this is a C/C++ deployment-profile risk and that Python generated runtimes may not have the same fixed-width shift risk.
   * - ``context``
     - ``str``
     - yes
     - Expression location where the shift appears. (enum: ``var_initializer``, ``guard``, ``transition_effect``, ``lifecycle_action``)
   * - ``statement_kind``
     - ``str``
     - no
     - Statement shape when the expression is an operation assignment RHS. (enum: ``operation_assignment``)
   * - ``expr_text``
     - ``str``
     - yes
     - Source text of the shift expression.
   * - ``operator``
     - ``str``
     - yes
     - Shift operator. (enum: ``<<``, ``>>``)
   * - ``target_bits``
     - ``int``
     - yes
     - Target integer width in bits.
   * - ``shift_count_text``
     - ``str``
     - yes
     - Source text of the shift count after lightweight folding.

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int flags = 1;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(flags << 64) != 0];
   }

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``bound_shift_count`` on ``expression``: Keep constant shift counts within ``0 <= count < 64`` for the default C/C++ profile.

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not report dynamic shift counts as proven unsafe from this catalog-only rule.

.. _diag-code-w-numeric-float-bitwise:

W_NUMERIC_FLOAT_BITWISE
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NUMERIC_FLOAT_BITWISE severity=warning emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE target_family type=str required=true enum=c_family item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE target_templates type=list[str] required=true enum=- item_enum=c|c_poll|cpp|cpp_poll exact_values=c|c_poll|cpp|cpp_poll
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE runtime_note type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE context type=str required=true enum=var_initializer|guard|transition_effect|lifecycle_action item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE statement_kind type=str required=false enum=operation_assignment item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE expr_text type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE operator type=str required=true enum=&|^|||<<|>> item_enum=- exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE operand_types type=list[str] required=true enum=- item_enum=int|float|unknown exact_values=-
.. diagnostics-ref W_NUMERIC_FLOAT_BITWISE operand_type_sources type=list[str] required=true enum=- item_enum=literal|declared_var|local_expression exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``expression``.

**Meaning.** A value known to be ``float`` participates in a bitwise or shift operator that belongs to the C/C++ integer operation profile. The warning is target-profile-specific even when other runtimes may also reject some float-bitwise shapes for different reasons.

**LLM repair summary.** A float-shaped operand reaches a C/C++ integer bitwise operation. Keep the diagnostic target-specific and use the operand type refs to explain why the expression is considered risky.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``target_family``
     - ``str``
     - yes
     - Target family whose default deployment profile owns this risk. (enum: ``c_family``)
   * - ``target_templates``
     - ``list[str]``
     - yes
     - Ordered target templates covered by this default C/C++ profile: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``. (item enum: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``; exact: ``c``, ``c_poll``, ``cpp``, ``cpp_poll``)
   * - ``runtime_note``
     - ``str``
     - yes
     - Human-readable note that this is a C/C++ integer-operation profile risk and that other runtimes may fail for different reasons.
   * - ``context``
     - ``str``
     - yes
     - Expression location where the bitwise operation appears. (enum: ``var_initializer``, ``guard``, ``transition_effect``, ``lifecycle_action``)
   * - ``statement_kind``
     - ``str``
     - no
     - Statement shape when the expression is an operation assignment RHS. (enum: ``operation_assignment``)
   * - ``expr_text``
     - ``str``
     - yes
     - Source text of the bitwise expression.
   * - ``operator``
     - ``str``
     - yes
     - Bitwise or shift operator involving a float-shaped operand. (enum: ``&``, ``^``, ``|``, ``<<``, ``>>``)
   * - ``operand_types``
     - ``list[str]``
     - yes
     - Operand type tags in expression order. Allowed members are ``int``, ``float``, and ``unknown``. (item enum: ``int``, ``float``, ``unknown``)
   * - ``operand_type_sources``
     - ``list[str]``
     - yes
     - Evidence source for each operand type tag. Allowed members are ``literal``, ``declared_var``, and ``local_expression``. (item enum: ``literal``, ``declared_var``, ``local_expression``)

.. diagnostics-example W_NUMERIC_FLOAT_BITWISE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def float gain = 1.5;
   def int flags = 1;
   state Root {
       state A {
           during { flags = flags & gain; }
       }
       [*] -> A;
   }

.. diagnostics-example W_NUMERIC_FLOAT_BITWISE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``use_integer_operand`` on ``expression``: Replace the float operand with an integer flag/mask value when deploying to C/C++ templates.

.. diagnostics-example W_NUMERIC_FLOAT_BITWISE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not describe this only as a generic Python TypeError; the shared contract is about the C/C++ integer-operation profile.

Topology and design-health diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-unreachable-state:

W_UNREACHABLE_STATE
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNREACHABLE_STATE severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_UNREACHABLE_STATE state_path type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A state is not reachable from the model's root entry path via any sequence of normal or forced transitions.

**LLM repair summary.** This state cannot be entered at runtime; the surrounding transitions never lead to it. It is dead from the machine's perspective.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the unreachable state.

.. diagnostics-example W_UNREACHABLE_STATE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state Idle;
       state Orphan;
       [*] -> Idle;
   }

.. diagnostics-example W_UNREACHABLE_STATE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_inbound_transition`` on ``state``: Add a transition that reaches the state if it was meant to be used.

.. diagnostics-example W_UNREACHABLE_STATE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a self-loop to mask the unreachability.

.. _diag-code-w-deadlock-leaf:

W_DEADLOCK_LEAF
^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEADLOCK_LEAF severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_DEADLOCK_LEAF state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF parent_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF reason type=str required=true enum=no_outgoing_transition item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF suggested_fix type=dict required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A non-pseudo leaf state has no outgoing transition.

**LLM repair summary.** This leaf state has no outgoing transition, so once the machine enters it there is no modeled way to leave.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``state_path``
     - ``str``
     - yes
     - Dotted path of the deadlocking leaf state.
   * - ``parent_path``
     - ``str``
     - no
     - Dotted path of the leaf state's parent. Present only when an exit-transition quick-fix can be inserted inside a parent state.
   * - ``reason``
     - ``str``
     - yes
     - Why the leaf is considered a deadlock. (enum: ``no_outgoing_transition``)
   * - ``suggested_fix``
     - ``dict``
     - no
     - Structured quick-fix payload for adding a parent exit transition.

.. diagnostics-example W_DEADLOCK_LEAF 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       [*] -> A;
   }

.. diagnostics-example W_DEADLOCK_LEAF 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_transition`` on ``state``: Add a modeled transition to the next intended state.

.. diagnostics-example W_DEADLOCK_LEAF 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add a self-loop just to silence the warning.

.. _diag-code-w-high-var-to-leaf-ratio:

W_HIGH_VAR_TO_LEAF_RATIO
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_HIGH_VAR_TO_LEAF_RATIO severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO n_vars type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO n_leaf_states type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO actual type=number required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO threshold type=number required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``composite_block``.

**Meaning.** The number of variables is high relative to the number of non-pseudo leaf states.

**LLM repair summary.** The model has many variables for its number of leaf states, which often indicates flag bloat or speculative state that does not belong in the DSL.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``n_vars``
     - ``int``
     - yes
     - Number of top-level variable definitions.
   * - ``n_leaf_states``
     - ``int``
     - yes
     - Number of non-pseudo leaf states.
   * - ``actual``
     - ``number``
     - yes
     - Actual ``n_vars / max(n_leaf_states, 1)`` ratio.
   * - ``threshold``
     - ``number``
     - yes
     - Effective threshold used for this inspection call.

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int a = 0;
   def int b = 0;
   def int c = 0;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``audit_variables`` on ``variable_definitions``: Remove or consolidate variables that do not represent durable machine state.

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not raise the threshold without checking whether the variables influence behavior.

.. _diag-code-w-deep-hierarchy:

W_DEEP_HIERARCHY
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEEP_HIERARCHY severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_DEEP_HIERARCHY max_depth type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY deepest_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY actual type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY threshold type=int required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** The state hierarchy exceeds the configured maximum depth.

**LLM repair summary.** The hierarchy is deeper than the configured readability threshold, making lifecycle order and transition scope harder to reason about.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``max_depth``
     - ``int``
     - yes
     - Maximum hierarchy depth found in the model.
   * - ``deepest_path``
     - ``str``
     - yes
     - One deepest state path that triggered the warning.
   * - ``actual``
     - ``int``
     - yes
     - Actual maximum hierarchy depth.
   * - ``threshold``
     - ``int``
     - yes
     - Effective threshold used for this inspection call.

.. diagnostics-example W_DEEP_HIERARCHY 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A { state B { state C; [*] -> C; } [*] -> B; } [*] -> A; }

.. diagnostics-example W_DEEP_HIERARCHY 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``flatten_hierarchy`` on ``state_tree``: Collapse levels that do not add lifecycle or transition semantics.

.. diagnostics-example W_DEEP_HIERARCHY 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not flatten a level that carries required enter, exit, during, or aspect semantics.

.. _diag-code-w-large-composite:

W_LARGE_COMPOSITE
^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_LARGE_COMPOSITE severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_LARGE_COMPOSITE composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE n_children type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE actual type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE threshold type=int required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``composite_block``.

**Meaning.** A composite state has more direct children than the configured threshold.

**LLM repair summary.** A single composite state owns many direct children, which can make transition review and initial-state reasoning difficult.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``composite_path``
     - ``str``
     - yes
     - Dotted path of the large composite state.
   * - ``n_children``
     - ``int``
     - yes
     - Number of direct child states.
   * - ``actual``
     - ``int``
     - yes
     - Actual direct child count.
   * - ``threshold``
     - ``int``
     - yes
     - Effective threshold used for this inspection call.

.. diagnostics-example W_LARGE_COMPOSITE 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root { state A; state B; state C; [*] -> A; }

.. diagnostics-example W_LARGE_COMPOSITE 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``group_children`` on ``composite_state``: Introduce meaningful nested composites to group related child states.

.. diagnostics-example W_LARGE_COMPOSITE 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add arbitrary grouping states that have no semantic meaning.

.. _diag-code-i-nontrivial-scc:

I_NONTRIVIAL_SCC
^^^^^^^^^^^^^^^^

.. diagnostics-meta I_NONTRIVIAL_SCC severity=info emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_NONTRIVIAL_SCC algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC scc type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``verify_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A non-trivial strongly connected component exists in the guard-agnostic leaf-level topology graph.

**LLM repair summary.** The topology contains a cycle. This is often intentional in state machines, so treat it as a review prompt rather than a direct defect.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``topological_only``)
   * - ``representative_state_path``
     - ``str``
     - yes
     - One state path from the reported strongly connected component.
   * - ``scc``
     - ``list[str]``
     - yes
     - State paths in the non-trivial strongly connected component.

.. diagnostics-example I_NONTRIVIAL_SCC 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       state A;
       state B;
       [*] -> A;
       A -> B;
       B -> A;
   }

.. diagnostics-example I_NONTRIVIAL_SCC 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``review_cycle`` on ``topology``: Confirm the cycle has a deliberate runtime exit or event-driven purpose.

.. diagnostics-example I_NONTRIVIAL_SCC 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not delete cyclic transitions automatically; cyclic control flow can be valid FCSTM behavior.

.. _diag-code-w-topological-noexit:

W_TOPOLOGICAL_NOEXIT
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_TOPOLOGICAL_NOEXIT severity=warning emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT counterexample_kind type=str required=true enum=trap_cycle|deadlock item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT scc type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``verify_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** A root-reachable leaf or cycle has no guard-agnostic route to the root exit sink.

**LLM repair summary.** From the current topology, execution can enter a region that has no structural path to terminate at the root exit.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``topological_only``)
   * - ``representative_state_path``
     - ``str``
     - yes
     - One state path from the no-exit counterexample.
   * - ``counterexample_kind``
     - ``str``
     - yes
     - Shape of the topological counterexample. (enum: ``trap_cycle``, ``deadlock``)
   * - ``scc``
     - ``list[str]``
     - yes
     - Trap-cycle component paths, or an empty list for a deadlock leaf.

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       state A;
       state B;
       [*] -> A;
       A -> B;
   }

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_exit_transition`` on ``topology``: Add a route from the stuck state or cycle to an exit-capable path.

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add an unconditional exit without checking lifecycle and event semantics.

.. _diag-code-i-topological-non-terminating:

I_TOPOLOGICAL_NON_TERMINATING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TOPOLOGICAL_NON_TERMINATING severity=info emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING counterexample_path type=list[str] required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``info``; emit tier ``verify_pipeline``; capability ``pure_static``; span object ``state_identifier``.

**Meaning.** The topology does not force all root-reachable executions to eventually reach the root terminator.

**LLM repair summary.** The structural graph allows a path that can avoid termination forever. This may be a valid service loop, but it should be reviewed explicitly.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``algorithm_name``
     - ``str``
     - yes
     - Verify registry algorithm that produced the raw finding.
   * - ``verification_scope``
     - ``str``
     - yes
     - Verify scope for this finding. (enum: ``topological_only``)
   * - ``representative_state_path``
     - ``str``
     - yes
     - One state path from the non-terminating counterexample.
   * - ``counterexample_path``
     - ``list[str]``
     - yes
     - Representative cycle or deadlock path reported by topology verify.

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 1 verify_opt_in

**Example 1** (``verify_opt_in``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state System {
       state A;
       [*] -> A;
       A -> A;
       A -> [*];
   }

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``review_nontermination`` on ``topology``: Decide whether the non-terminating path is intended.

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not treat every loop as a bug; long-running control loops are common state-machine behavior.

Compatibility-only and miscellaneous diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-initial-unconditional-missing:

W_INITIAL_UNCONDITIONAL_MISSING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_INITIAL_UNCONDITIONAL_MISSING severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING existing_conditional_count type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING first_child_name type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING suggested_fix type=dict required=false enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``composite_block``.

**Meaning.** A composite state has no unconditional ``[*] -> child`` entry transition. Guarded or event-triggered entry transitions do not provide a guaranteed initial child.

**LLM repair summary.** The composite state can fail to choose an initial child because no unconditional entry transition is declared.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``composite_path``
     - ``str``
     - yes
     - Dotted path of the composite state.
   * - ``existing_conditional_count``
     - ``int``
     - yes
     - Number of existing initial transitions that are not unconditional.
   * - ``first_child_name``
     - ``str``
     - no
     - First declared non-pseudo child state name used as the fallback insertion target.
   * - ``suggested_fix``
     - ``dict``
     - no
     - Structured quick-fix payload for inserting an unconditional entry transition.

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       [*] -> A : if [ready > 0];
   }

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``add_unconditional_initial`` on ``composite_state``: Add a fallback ``[*] -> Child;`` entry transition.

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not assume a guarded initial transition always fires without proving the guard.

.. _diag-code-w-dead-named-action:

W_DEAD_NAMED_ACTION
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEAD_NAMED_ACTION severity=warning emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref W_DEAD_NAMED_ACTION function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_NAMED_ACTION defined_in type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``named_action_declaration``.

**Meaning.** A named action belongs to an unreachable state and is not referenced by any reachable action ref.

**LLM repair summary.** This named action cannot run through the reachable state graph and is not referenced from elsewhere.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``function_name``
     - ``str``
     - yes
     - Named action identifier.
   * - ``defined_in``
     - ``str``
     - yes
     - Dotted path of the state where the action is defined.

.. diagnostics-example W_DEAD_NAMED_ACTION 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       state A;
       state B { enter Cleanup {} }
       [*] -> A;
   }

.. diagnostics-example W_DEAD_NAMED_ACTION 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``connect_state`` on ``state``: Add a transition path to the owning state if the action matters.

.. diagnostics-example W_DEAD_NAMED_ACTION 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not add an unrelated ref just to silence the warning.

.. _diag-code-w-named-action-shadows-ancestor:

W_NAMED_ACTION_SHADOWS_ANCESTOR
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NAMED_ACTION_SHADOWS_ANCESTOR severity=warning emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR inner_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR outer_state_path type=str required=true enum=- item_enum=- exact_values=-

**Registry facts.** Severity ``warning``; emit tier ``static_pipeline``; capability ``pure_static``; span object ``named_action_declaration``.

**Meaning.** A named lifecycle action reuses the same function name as an ancestor-scoped named action.

**LLM repair summary.** A nested state defines a named action with the same name as an ancestor action. Relative action refs can become hard to audit because the same leaf name means different functions at different hierarchy levels.

.. list-table:: Refs schema
   :header-rows: 1
   :widths: 22 16 14 48

   * - Field
     - Type
     - Required
     - Meaning
   * - ``function_name``
     - ``str``
     - yes
     - Reused named action identifier.
   * - ``inner_state_path``
     - ``str``
     - yes
     - Dotted path of the state containing the shadowing action.
   * - ``outer_state_path``
     - ``str``
     - yes
     - Dotted path of the ancestor state containing the shadowed action.

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 1 repro_cli

**Example 1** (``repro_cli``) — trigger shape.
Use this registry trigger as the smallest source shape to discuss the code. If the emit tier is not ``static_pipeline``, run it through the path named by the example kind rather than assuming default CLI output.

.. code-block:: fcstm

   state Root {
       enter Sync { }
       state Child { enter Sync { } }
       [*] -> Child;
   }

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 2 boundary_only

**Example 2** (``boundary_only``) — repair direction.
A typical repair is ``rename_inner_action`` on ``named_action``: Give the nested action a distinct name when it implements different behavior.

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 3 boundary_only

**Example 3** (``boundary_only``) — anti-pattern boundary.
Do not leave the shadowing name in place unless the scope distinction is intentional and documented outside the DSL.
