完整诊断码目录
----------------------------------------

本目录以 ``pyfcstm.diagnostics.codes.CODE_REGISTRY`` 为准。源码中的 ``diagnostics-meta`` 和 ``diagnostics-example`` 标记会由 ``python tools/check_diagnostics_reference_docs.py --check`` 检查。

.. list-table:: 注册表摘要
   :header-rows: 1
   :widths: 28 12 18 18 24

   * - 诊断码
     - 严重级别
     - 发射层级
     - 能力层级
     - 源码对象
   * - :ref:`E_UNDEFINED_VAR <diag-code-e-undefined-var-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`E_DUPLICATE_VAR <diag-code-e-duplicate-var-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`E_MISSING_STATE <diag-code-e-missing-state-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_DUPLICATE_STATE <diag-code-e-duplicate-state-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_EVENT_REF_INVALID <diag-code-e-event-ref-invalid-zh>`
     - ``error``
     - ``lookup_api``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`E_EVENT_NOT_FOUND <diag-code-e-event-not-found-zh>`
     - ``error``
     - ``lookup_api``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`E_DANGLING_TRANSITION <diag-code-e-dangling-transition-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_COMBO_TRIGGER_NOT_EXPANDED <diag-code-e-combo-trigger-not-expanded-zh>`
     - ``error``
     - ``catalog_only``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_COMBO_RESERVED_PREFIX_STATE_KIND <diag-code-w-combo-reserved-prefix-state-kind-zh>`
     - ``warning``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_COMBO_RELAY_PSEUDO_HAS_ACTIONS <diag-code-w-combo-relay-pseudo-has-actions-zh>`
     - ``warning``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`I_COMBO_PSEUDO_NAME_EXTENDED <diag-code-i-combo-pseudo-name-extended-zh>`
     - ``info``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_COMBO_PSEUDO_NAME_COLLISION <diag-code-e-combo-pseudo-name-collision-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_COMBO_DUPLICATE_EVENT <diag-code-w-combo-duplicate-event-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_COMBO_GUARD_CONST_TRUE <diag-code-w-combo-guard-const-true-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_CONST_FALSE <diag-code-w-combo-guard-const-false-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_PREFIX_IMPLIED <diag-code-w-combo-guard-prefix-implied-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_COMBO_GUARD_PREFIX_CONTRADICTS <diag-code-w-combo-guard-prefix-contradicts-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`E_TYPE_MISMATCH <diag-code-e-type-mismatch-zh>`
     - ``error``
     - ``partial_static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`E_FORCED_TRANSITION_EXPANSION <diag-code-e-forced-transition-expansion-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_INITIAL_TRANSITION_INVALID <diag-code-e-initial-transition-invalid-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`E_DUPLICATE_FUNCTION_NAME <diag-code-e-duplicate-function-name-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_DURING_ASPECT_INVALID <diag-code-e-during-aspect-invalid-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``lifecycle_action``
   * - :ref:`E_PSEUDO_NOT_LEAF <diag-code-e-pseudo-not-leaf-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`E_NAMED_FUNCTION_REF_CYCLE <diag-code-e-named-function-ref-cycle-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_NAMED_FUNCTION_REF_NOT_FOUND <diag-code-e-named-function-ref-not-found-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`E_IMPORT_NOT_FOUND <diag-code-e-import-not-found-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_CIRCULAR <diag-code-e-import-circular-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_ALIAS_CONFLICT <diag-code-e-import-alias-conflict-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_DUPLICATE_MAPPING <diag-code-e-import-duplicate-mapping-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`E_IMPORT_MAPPING_INVALID <diag-code-e-import-mapping-invalid-zh>`
     - ``error``
     - ``static_pipeline``
     - ``pure_static``
     - ``import_statement``
   * - :ref:`W_UNREACHABLE_STATE <diag-code-w-unreachable-state-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_GUARD_CONST_FALSE <diag-code-w-guard-const-false-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``guard_expression``
   * - :ref:`W_GUARD_CONST_TRUE <diag-code-w-guard-const-true-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``guard_expression``
   * - :ref:`W_DURING_CONST_ASSIGN <diag-code-w-during-const-assign-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``lifecycle_action``
   * - :ref:`W_UNUSED_EVENT <diag-code-w-unused-event-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_DEADLOCK_LEAF <diag-code-w-deadlock-leaf-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_INITIAL_UNCONDITIONAL_MISSING <diag-code-w-initial-unconditional-missing-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`W_FORCED_NEVER_EXPANDS <diag-code-w-forced-never-expands-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_DEAD_NAMED_ACTION <diag-code-w-dead-named-action-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`W_UNREFERENCED_VAR <diag-code-w-unreferenced-var-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`I_UNREFERENCED_VAR_MAYBE_ABSTRACT <diag-code-i-unreferenced-var-maybe-abstract-zh>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_GUARD_VARS_NEVER_CHANGE <diag-code-w-guard-vars-never-change-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``guard_expression``
   * - :ref:`W_UNWRITTEN_READ_VAR <diag-code-w-unwritten-read-var-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_WRITE_ONLY_VAR <diag-code-w-write-only-var-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``variable_declaration``
   * - :ref:`W_REDUNDANT_TRANSITION <diag-code-w-redundant-transition-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_SELF_TRANSITION_NOP <diag-code-w-self-transition-nop-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_EFFECT_SELF_ASSIGN <diag-code-w-effect-self-assign-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``effect_statement``
   * - :ref:`W_FORCED_OVERRIDES_NORMAL <diag-code-w-forced-overrides-normal-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`W_SHADOWED_EVENT <diag-code-w-shadowed-event-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_NAMED_ACTION_SHADOWS_ANCESTOR <diag-code-w-named-action-shadows-ancestor-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``named_action_declaration``
   * - :ref:`W_LITERAL_TYPE_NARROWING <diag-code-w-literal-type-narrowing-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE <diag-code-w-numeric-literal-out-of-target-range-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_NUMERIC_CONSTANT_DIVISION_BY_ZERO <diag-code-w-numeric-constant-division-by-zero-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``expression``
   * - :ref:`W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE <diag-code-w-numeric-shift-count-out-of-target-range-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``const_fold``
     - ``expression``
   * - :ref:`W_NUMERIC_FLOAT_BITWISE <diag-code-w-numeric-float-bitwise-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``expression``
   * - :ref:`W_ASPECT_NO_DESCENDANT_LEAF <diag-code-w-aspect-no-descendant-leaf-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``lifecycle_action``
   * - :ref:`W_HIGH_VAR_TO_LEAF_RATIO <diag-code-w-high-var-to-leaf-ratio-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`W_DEEP_HIERARCHY <diag-code-w-deep-hierarchy-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_LARGE_COMPOSITE <diag-code-w-large-composite-zh>`
     - ``warning``
     - ``static_pipeline``
     - ``pure_static``
     - ``composite_block``
   * - :ref:`I_TRANSITION_TO_SELF_VIA_PARENT <diag-code-i-transition-to-self-via-parent-zh>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`I_TRANSITION_NEVER_EVENT_TRIGGERED <diag-code-i-transition-never-event-triggered-zh>`
     - ``info``
     - ``static_pipeline``
     - ``pure_static``
     - ``transition``
   * - :ref:`I_NONTRIVIAL_SCC <diag-code-i-nontrivial-scc-zh>`
     - ``info``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_TOPOLOGICAL_NOEXIT <diag-code-w-topological-noexit-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`I_TOPOLOGICAL_NON_TERMINATING <diag-code-i-topological-non-terminating-zh>`
     - ``info``
     - ``verify_pipeline``
     - ``pure_static``
     - ``state_identifier``
   * - :ref:`W_EVENT_UNREACHABLE_EMIT <diag-code-w-event-unreachable-emit-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``pure_static``
     - ``event_declaration``
   * - :ref:`W_DEAD_GUARD <diag-code-w-dead-guard-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_GUARD_TAUTOLOGY <diag-code-w-guard-tautology-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_FORCED_GUARD_UNSAT <diag-code-w-forced-guard-unsat-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``guard_expression``
   * - :ref:`W_EFFECT_SMT_NO_OP <diag-code-w-effect-smt-no-op-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``effect_statement``
   * - :ref:`I_EFFECT_GUARD_CONTRADICT <diag-code-i-effect-guard-contradict-zh>`
     - ``info``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``effect_statement``
   * - :ref:`W_TRANSITION_SHADOWED <diag-code-w-transition-shadowed-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``transition``
   * - :ref:`I_ENTER_DURING_CONTRADICT <diag-code-i-enter-during-contradict-zh>`
     - ``info``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``lifecycle_action``
   * - :ref:`W_COMPOSITE_INIT_INCOMPLETE <diag-code-w-composite-init-incomplete-zh>`
     - ``warning``
     - ``verify_pipeline``
     - ``requires_solver``
     - ``composite_block``

名称、变量、类型和导入
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-undefined-var-zh:

E_UNDEFINED_VAR
^^^^^^^^^^^^^^^

.. diagnostics-meta E_UNDEFINED_VAR severity=error emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref E_UNDEFINED_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR referenced_in type=str required=true enum=guard|effect|enter|during|exit|during_aspect|init item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR state_path type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR expr_text type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_UNDEFINED_VAR is_temporary type=bool required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_UNDEFINED_VAR kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``expression``。

**含义。** 某个守卫、效果或生命周期动作块读取了未在文件顶层用 ``def`` 声明、也未在当前块内提前赋值的变量名。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。某个守卫、效果或生命周期动作块读取了未在文件顶层用 ``def`` 声明、也未在当前块内提前赋值的变量名。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``referenced_in``
     - ``str``
     - 是
     - 字段含义：引用发生的块类型。
   * - ``state_path``
     - ``str_or_null``
     - 否
     - 字段含义：相关状态的点分路径。
   * - ``expr_text``
     - ``str_or_null``
     - 否
     - 字段含义：相关表达式的源码文本。
   * - ``is_temporary``
     - ``bool``
     - 否
     - 字段含义：字段 ``is_temporary`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。

.. diagnostics-example E_UNDEFINED_VAR 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   def int x = 0;
   state Root { state A; state B; A -> B : if [unknown_var > 0]; }

.. diagnostics-example E_UNDEFINED_VAR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_UNDEFINED_VAR`` 的修复方向。
典型修复是对 ``file_top`` 执行 ``add_definition``：针对“某个守卫、效果或生命周期动作块读取了未在文件顶层用 ``def`` 声明、也未在当前块内提前赋值的变量名。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_UNDEFINED_VAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_UNDEFINED_VAR`` 的反例边界。
不要这样处理：针对“某个守卫、效果或生命周期动作块读取了未在文件顶层用 ``def`` 声明、也未在当前块内提前赋值的变量名。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-duplicate-var-zh:

E_DUPLICATE_VAR
^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_VAR severity=error emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref E_DUPLICATE_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_VAR previous_span type=Span required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_DUPLICATE_VAR kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``variable_declaration``。

**含义。** 文件顶层出现重复的 ``def`` 变量声明，同一个变量名会对应多个初始化来源。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。文件顶层出现重复的 ``def`` 变量声明，同一个变量名会对应多个初始化来源。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``previous_span``
     - ``Span``
     - 否
     - 字段含义：第一次声明的源码位置。

.. diagnostics-example E_DUPLICATE_VAR 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   def int x = 0;
   def int x = 1;
   state Root { state A; }

.. diagnostics-example E_DUPLICATE_VAR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_DUPLICATE_VAR`` 的修复方向。
典型修复是对 ``variable_definition`` 执行 ``drop_duplicate``：针对“文件顶层出现重复的 ``def`` 变量声明，同一个变量名会对应多个初始化来源。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_DUPLICATE_VAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_DUPLICATE_VAR`` 的反例边界。
不要这样处理：针对“文件顶层出现重复的 ``def`` 变量声明，同一个变量名会对应多个初始化来源。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-type-mismatch-zh:

E_TYPE_MISMATCH
^^^^^^^^^^^^^^^

.. diagnostics-meta E_TYPE_MISMATCH severity=error emit_tier=partial_static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref E_TYPE_MISMATCH expected type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_TYPE_MISMATCH actual type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_TYPE_MISMATCH expr_text type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_TYPE_MISMATCH kind=partial_static_boundary

**注册表事实。** 严重级别 ``error``；发射层级 ``partial_static_pipeline``；能力层级 ``pure_static``；源码对象 ``expression``。

**含义。** 守卫、效果或赋值表达式使用了不匹配的表达式类别，例如把数值表达式和条件表达式混用。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。守卫、效果或赋值表达式使用了不匹配的表达式类别，例如把数值表达式和条件表达式混用。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``expected``
     - ``str``
     - 是
     - 字段含义：期望的表达式类别。
   * - ``actual``
     - ``str``
     - 是
     - 字段含义：实际观测到的类别、数量或度量值。
   * - ``expr_text``
     - ``str``
     - 是
     - 字段含义：相关表达式的源码文本。

.. diagnostics-example E_TYPE_MISMATCH 1 boundary_only

**示例 1**\ （``boundary_only``）——复现边界。
这个注册表契约有意先于所有前端和后端的完整发射一致性。应把示例视为支持的边界形状，并在承诺默认命令行 JSON 前确认当前发射器。

.. code-block:: fcstm

   def int x = 0;
   state Root { state A; state B; A -> B : if [x]; }

.. diagnostics-example E_TYPE_MISMATCH 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_TYPE_MISMATCH`` 的修复方向。
典型修复是对 ``expression`` 执行 ``wrap_in_ternary``：针对“守卫、效果或赋值表达式使用了不匹配的表达式类别，例如把数值表达式和条件表达式混用。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_TYPE_MISMATCH 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_TYPE_MISMATCH`` 的反例边界。
不要这样处理：针对“守卫、效果或赋值表达式使用了不匹配的表达式类别，例如把数值表达式和条件表达式混用。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-duplicate-function-name-zh:

E_DUPLICATE_FUNCTION_NAME
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_FUNCTION_NAME severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_FUNCTION_NAME stage type=str required=true enum=enter|during|exit|during_aspect item_enum=- exact_values=-


.. diagnostics-boundary E_DUPLICATE_FUNCTION_NAME kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``named_action_declaration``。

**含义。** 同一状态内两个命名生命周期动作使用了相同名称，导致 ``ref`` 无法唯一定位。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。同一状态内两个命名生命周期动作使用了相同名称，导致 ``ref`` 无法唯一定位。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``function_name``
     - ``str``
     - 是
     - 字段含义：相关命名动作名称。
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``stage``
     - ``str``
     - 是
     - 字段含义：生命周期阶段。

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root {
       state A {
           enter Foo { }
           enter Foo { }
       }
   }

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_DUPLICATE_FUNCTION_NAME`` 的修复方向。
典型修复是对 ``named_action`` 执行 ``rename_one``：针对“同一状态内两个命名生命周期动作使用了相同名称，导致 ``ref`` 无法唯一定位。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_DUPLICATE_FUNCTION_NAME 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_DUPLICATE_FUNCTION_NAME`` 的反例边界。
不要这样处理：针对“同一状态内两个命名生命周期动作使用了相同名称，导致 ``ref`` 无法唯一定位。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-named-function-ref-cycle-zh:

E_NAMED_FUNCTION_REF_CYCLE
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_NAMED_FUNCTION_REF_CYCLE severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE ref_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE cycle_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_CYCLE reason type=str required=true enum=action_ref_cycle item_enum=- exact_values=-


.. diagnostics-boundary E_NAMED_FUNCTION_REF_CYCLE kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``named_action_declaration``。

**含义。** 生命周期动作 ``ref`` 链形成循环，永远到不了具体或抽象动作实现。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。生命周期动作 ``ref`` 链形成循环，永远到不了具体或抽象动作实现。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``ref_path``
     - ``str``
     - 是
     - 字段含义：相关动作引用路径。
   * - ``cycle_path``
     - ``str``
     - 是
     - 字段含义：形成循环的动作路径链。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root {
       state A {
           enter ref First;
           enter First ref Second;
           enter Second ref First;
       }
   }

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_NAMED_FUNCTION_REF_CYCLE`` 的修复方向。
典型修复是对 ``action_ref`` 执行 ``break_ref_cycle``：针对“生命周期动作 ``ref`` 链形成循环，永远到不了具体或抽象动作实现。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_NAMED_FUNCTION_REF_CYCLE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_NAMED_FUNCTION_REF_CYCLE`` 的反例边界。
不要这样处理：针对“生命周期动作 ``ref`` 链形成循环，永远到不了具体或抽象动作实现。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-named-function-ref-not-found-zh:

E_NAMED_FUNCTION_REF_NOT_FOUND
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_NAMED_FUNCTION_REF_NOT_FOUND severity=error emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND ref_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND reason type=str required=true enum=state_not_found|named_function_not_found item_enum=- exact_values=-
.. diagnostics-ref E_NAMED_FUNCTION_REF_NOT_FOUND missing_segment type=str_or_null required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_NAMED_FUNCTION_REF_NOT_FOUND kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``named_action_declaration``。

**含义。** 生命周期动作 ``ref`` 无法解析到目标命名动作。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。生命周期动作 ``ref`` 无法解析到目标命名动作。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``ref_path``
     - ``str``
     - 是
     - 字段含义：相关动作引用路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。
   * - ``missing_segment``
     - ``str_or_null``
     - 否
     - 字段含义：解析失败的路径片段。

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root {
       state A {
           enter ref NoSuch.NoSuch;
       }
   }

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_NAMED_FUNCTION_REF_NOT_FOUND`` 的修复方向。
典型修复是对 ``action_ref`` 执行 ``fix_ref_path``：针对“生命周期动作 ``ref`` 无法解析到目标命名动作。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_NAMED_FUNCTION_REF_NOT_FOUND 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_NAMED_FUNCTION_REF_NOT_FOUND`` 的反例边界。
不要这样处理：针对“生命周期动作 ``ref`` 无法解析到目标命名动作。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-import-not-found-zh:

E_IMPORT_NOT_FOUND
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_NOT_FOUND severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_NOT_FOUND source_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_NOT_FOUND reason type=str required=true enum=file_not_found|read_error|parse_error|no_root_state item_enum=- exact_values=-


.. diagnostics-boundary E_IMPORT_NOT_FOUND kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``import_statement``。

**含义。** ``import`` 指向的源文件不存在、不可读或无法解析。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``import`` 指向的源文件不存在、不可读或无法解析。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``source_path``
     - ``str``
     - 是
     - 字段含义：导入语句中的源路径文本。
   * - ``alias``
     - ``str``
     - 是
     - 字段含义：导入别名。
   * - ``host_state_path``
     - ``str``
     - 是
     - 字段含义：承载导入语句或导入别名的组合状态路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_IMPORT_NOT_FOUND 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state System {
       import "missing.fcstm" as Sub;
   }

.. diagnostics-example E_IMPORT_NOT_FOUND 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_IMPORT_NOT_FOUND`` 的修复方向。
典型修复是对 ``import_statement`` 执行 ``fix_path``：针对“``import`` 指向的源文件不存在、不可读或无法解析。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_IMPORT_NOT_FOUND 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_IMPORT_NOT_FOUND`` 的反例边界。
不要这样处理：针对“``import`` 指向的源文件不存在、不可读或无法解析。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-import-circular-zh:

E_IMPORT_CIRCULAR
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_CIRCULAR severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_CIRCULAR source_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_CIRCULAR cycle_chain type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_IMPORT_CIRCULAR kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``import_statement``。

**含义。** 多个状态机源文件之间的 ``import`` 关系形成循环。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。多个状态机源文件之间的 ``import`` 关系形成循环。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``source_path``
     - ``str``
     - 是
     - 字段含义：导入语句中的源路径文本。
   * - ``alias``
     - ``str``
     - 是
     - 字段含义：导入别名。
   * - ``host_state_path``
     - ``str``
     - 是
     - 字段含义：承载导入语句或导入别名的组合状态路径。
   * - ``cycle_chain``
     - ``list[str]``
     - 是
     - 字段含义：参与导入循环的文件路径序列。

.. diagnostics-example E_IMPORT_CIRCULAR 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   # a.fcstm
   state A { import "b.fcstm" as B; }
   # b.fcstm
   state B { import "a.fcstm" as A; }

.. diagnostics-example E_IMPORT_CIRCULAR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_IMPORT_CIRCULAR`` 的修复方向。
典型修复是对 ``import_statement`` 执行 ``refactor``：针对“多个状态机源文件之间的 ``import`` 关系形成循环。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_IMPORT_CIRCULAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_IMPORT_CIRCULAR`` 的反例边界。
不要这样处理：针对“多个状态机源文件之间的 ``import`` 关系形成循环。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-import-alias-conflict-zh:

E_IMPORT_ALIAS_CONFLICT
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_ALIAS_CONFLICT severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_ALIAS_CONFLICT conflicting_kind type=str required=true enum=existing_substate|previous_import_alias item_enum=- exact_values=-


.. diagnostics-boundary E_IMPORT_ALIAS_CONFLICT kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``import_statement``。

**含义。** ``import`` 别名与同一组合状态下的已有子状态或其他导入别名冲突。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``import`` 别名与同一组合状态下的已有子状态或其他导入别名冲突。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``alias``
     - ``str``
     - 是
     - 字段含义：导入别名。
   * - ``host_state_path``
     - ``str``
     - 是
     - 字段含义：承载导入语句或导入别名的组合状态路径。
   * - ``conflicting_kind``
     - ``str``
     - 是
     - 字段含义：别名冲突对象类型。

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state System {
       state Worker;
       import "worker.fcstm" as Worker;
   }

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_IMPORT_ALIAS_CONFLICT`` 的修复方向。
典型修复是对 ``import_statement`` 执行 ``rename_alias``：针对“``import`` 别名与同一组合状态下的已有子状态或其他导入别名冲突。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_IMPORT_ALIAS_CONFLICT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_IMPORT_ALIAS_CONFLICT`` 的反例边界。
不要这样处理：针对“``import`` 别名与同一组合状态下的已有子状态或其他导入别名冲突。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-import-duplicate-mapping-zh:

E_IMPORT_DUPLICATE_MAPPING
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_DUPLICATE_MAPPING severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING mapping_kind type=str required=true enum=event|variable item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING duplicated_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING direction type=str required=true enum=source_duplicated|target_duplicated item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_DUPLICATE_MAPPING host_state_path type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_IMPORT_DUPLICATE_MAPPING kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``import_statement``。

**含义。** 同一个 ``import { ... }`` 映射块里存在重复源名或重复宿主名。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。同一个 ``import { ... }`` 映射块里存在重复源名或重复宿主名。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``alias``
     - ``str``
     - 是
     - 字段含义：导入别名。
   * - ``mapping_kind``
     - ``str``
     - 是
     - 字段含义：导入映射类型。
   * - ``duplicated_name``
     - ``str``
     - 是
     - 字段含义：重复出现的源名或目标名。
   * - ``direction``
     - ``str``
     - 是
     - 字段含义：相关方向或重复侧。
   * - ``host_state_path``
     - ``str``
     - 是
     - 字段含义：承载导入语句或导入别名的组合状态路径。

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state System {
       import "sub.fcstm" as Sub {
           def x = a;
           def x = b;
       }
   }

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_IMPORT_DUPLICATE_MAPPING`` 的修复方向。
典型修复是对 ``mapping_clause`` 执行 ``drop_duplicate``：针对“同一个 ``import { ... }`` 映射块里存在重复源名或重复宿主名。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_IMPORT_DUPLICATE_MAPPING 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_IMPORT_DUPLICATE_MAPPING`` 的反例边界。
不要这样处理：针对“同一个 ``import { ... }`` 映射块里存在重复源名或重复宿主名。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-import-mapping-invalid-zh:

E_IMPORT_MAPPING_INVALID
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_IMPORT_MAPPING_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=import_statement
.. diagnostics-ref E_IMPORT_MAPPING_INVALID alias type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID mapping_kind type=str required=true enum=event|variable item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID host_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID reason type=str required=true enum=source_not_found|target_invalid|selector_invalid|template_invalid|empty_path|host_root_mismatch item_enum=- exact_values=-
.. diagnostics-ref E_IMPORT_MAPPING_INVALID detail type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_IMPORT_MAPPING_INVALID kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``import_statement``。

**含义。** 导入映射子句引用了不存在的源名、非法选择器或无法承载映射的宿主目标。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。导入映射子句引用了不存在的源名、非法选择器或无法承载映射的宿主目标。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``alias``
     - ``str``
     - 是
     - 字段含义：导入别名。
   * - ``mapping_kind``
     - ``str``
     - 是
     - 字段含义：导入映射类型。
   * - ``host_state_path``
     - ``str``
     - 是
     - 字段含义：承载导入语句或导入别名的组合状态路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。
   * - ``detail``
     - ``str``
     - 是
     - 字段含义：映射失败的可读细节。

.. diagnostics-example E_IMPORT_MAPPING_INVALID 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state System {
       import "sub.fcstm" as Sub {
           def x = no_such_var;
       }
   }

.. diagnostics-example E_IMPORT_MAPPING_INVALID 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_IMPORT_MAPPING_INVALID`` 的修复方向。
典型修复是对 ``mapping_clause`` 执行 ``fix_source``：针对“导入映射子句引用了不存在的源名、非法选择器或无法承载映射的宿主目标。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_IMPORT_MAPPING_INVALID 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_IMPORT_MAPPING_INVALID`` 的反例边界。
不要这样处理：针对“导入映射子句引用了不存在的源名、非法选择器或无法承载映射的宿主目标。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

状态和转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-missing-state-zh:

E_MISSING_STATE
^^^^^^^^^^^^^^^

.. diagnostics-meta E_MISSING_STATE severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_MISSING_STATE state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_MISSING_STATE referenced_from type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_MISSING_STATE reason type=str required=false enum=not_found|parent_missing|ambiguous|event_path_not_found item_enum=- exact_values=-


.. diagnostics-boundary E_MISSING_STATE kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 转换引用的目标状态路径无法在当前层级或外围层级中解析。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换引用的目标状态路径无法在当前层级或外围层级中解析。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``referenced_from``
     - ``str_or_null``
     - 否
     - 字段含义：发起引用的状态点分路径。
   * - ``reason``
     - ``str``
     - 否
     - 字段含义：原因分类标签。

.. diagnostics-example E_MISSING_STATE 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state A; A -> NoSuch; }

.. diagnostics-example E_MISSING_STATE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_MISSING_STATE`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_typo``：针对“转换引用的目标状态路径无法在当前层级或外围层级中解析。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_MISSING_STATE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_MISSING_STATE`` 的反例边界。
不要这样处理：针对“转换引用的目标状态路径无法在当前层级或外围层级中解析。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-duplicate-state-zh:

E_DUPLICATE_STATE
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DUPLICATE_STATE severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_DUPLICATE_STATE state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_STATE parent_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DUPLICATE_STATE previous_span type=Span required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_DUPLICATE_STATE kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 同一个父状态作用域内存在两个同名子状态。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。同一个父状态作用域内存在两个同名子状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_name``
     - ``str``
     - 是
     - 字段含义：相关状态名。
   * - ``parent_path``
     - ``str``
     - 是
     - 字段含义：父状态的点分路径。
   * - ``previous_span``
     - ``Span``
     - 否
     - 字段含义：第一次声明的源码位置。

.. diagnostics-example E_DUPLICATE_STATE 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state A; state A; }

.. diagnostics-example E_DUPLICATE_STATE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_DUPLICATE_STATE`` 的修复方向。
典型修复是对 ``state_definition`` 执行 ``drop_duplicate``：针对“同一个父状态作用域内存在两个同名子状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_DUPLICATE_STATE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_DUPLICATE_STATE`` 的反例边界。
不要这样处理：针对“同一个父状态作用域内存在两个同名子状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-dangling-transition-zh:

E_DANGLING_TRANSITION
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DANGLING_TRANSITION severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_DANGLING_TRANSITION src type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DANGLING_TRANSITION tgt type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DANGLING_TRANSITION reason type=str required=true enum=src_not_found|tgt_not_found|both_not_found item_enum=- exact_values=-


.. diagnostics-boundary E_DANGLING_TRANSITION kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 转换的源状态或目标状态至少一端无法解析，无法接入调度图。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换的源状态或目标状态至少一端无法解析，无法接入调度图。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``src``
     - ``str_or_null``
     - 否
     - 字段含义：DSL 中写出的原始源状态表达式。
   * - ``tgt``
     - ``str_or_null``
     - 否
     - 字段含义：DSL 中写出的原始目标状态表达式。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_DANGLING_TRANSITION 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state A; NoSuch -> A; }

.. diagnostics-example E_DANGLING_TRANSITION 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_DANGLING_TRANSITION`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_typo``：针对“转换的源状态或目标状态至少一端无法解析，无法接入调度图。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_DANGLING_TRANSITION 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_DANGLING_TRANSITION`` 的反例边界。
不要这样处理：针对“转换的源状态或目标状态至少一端无法解析，无法接入调度图。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-initial-transition-invalid-zh:

E_INITIAL_TRANSITION_INVALID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_INITIAL_TRANSITION_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_INITIAL_TRANSITION_INVALID composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_INITIAL_TRANSITION_INVALID reason type=str required=true enum=missing_entry|target_not_child item_enum=- exact_values=-


.. diagnostics-boundary E_INITIAL_TRANSITION_INVALID kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 组合状态缺少入口转换，或者入口转换目标不是该组合状态的直接子状态。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合状态缺少入口转换，或者入口转换目标不是该组合状态的直接子状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``composite_path``
     - ``str``
     - 是
     - 字段含义：相关组合状态的点分路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state Outer { state Inner; } }

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_INITIAL_TRANSITION_INVALID`` 的修复方向。
典型修复是对 ``composite_state`` 执行 ``add_initial_transition``：针对“组合状态缺少入口转换，或者入口转换目标不是该组合状态的直接子状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_INITIAL_TRANSITION_INVALID 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_INITIAL_TRANSITION_INVALID`` 的反例边界。
不要这样处理：针对“组合状态缺少入口转换，或者入口转换目标不是该组合状态的直接子状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-redundant-transition-zh:

W_REDUNDANT_TRANSITION
^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_REDUNDANT_TRANSITION severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_REDUNDANT_TRANSITION from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION duplicate_spans type=list[Span] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_REDUNDANT_TRANSITION transition_index type=int required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_REDUNDANT_TRANSITION kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 多个转换拥有相同的源、目标、事件、守卫和效果，行为上重复。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。多个转换拥有相同的源、目标、事件、守卫和效果，行为上重复。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``from_path``
     - ``str``
     - 是
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 是
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``duplicate_spans``
     - ``list[Span]``
     - 是
     - 字段含义：重复转换声明的源码范围列表。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example W_REDUNDANT_TRANSITION 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Go;
       A -> B :: Go;
   }

.. diagnostics-example W_REDUNDANT_TRANSITION 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_REDUNDANT_TRANSITION`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_duplicate``：针对“多个转换拥有相同的源、目标、事件、守卫和效果，行为上重复。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_REDUNDANT_TRANSITION 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_REDUNDANT_TRANSITION`` 的反例边界。
不要这样处理：针对“多个转换拥有相同的源、目标、事件、守卫和效果，行为上重复。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-self-transition-nop-zh:

W_SELF_TRANSITION_NOP
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_SELF_TRANSITION_NOP severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_SELF_TRANSITION_NOP state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SELF_TRANSITION_NOP transition_index type=int required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_SELF_TRANSITION_NOP kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 叶状态自转换没有事件、守卫、效果、自己的生命周期动作或祖先切面动作。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。叶状态自转换没有事件、守卫、效果、自己的生命周期动作或祖先切面动作。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``from_path``
     - ``str``
     - 否
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 否
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example W_SELF_TRANSITION_NOP 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       [*] -> A;
       A -> A;
   }

.. diagnostics-example W_SELF_TRANSITION_NOP 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_SELF_TRANSITION_NOP`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_transition``：针对“叶状态自转换没有事件、守卫、效果、自己的生命周期动作或祖先切面动作。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_SELF_TRANSITION_NOP 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_SELF_TRANSITION_NOP`` 的反例边界。
不要这样处理：针对“叶状态自转换没有事件、守卫、效果、自己的生命周期动作或祖先切面动作。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-transition-to-self-via-parent-zh:

I_TRANSITION_TO_SELF_VIA_PARENT
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TRANSITION_TO_SELF_VIA_PARENT severity=info emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref I_TRANSITION_TO_SELF_VIA_PARENT state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_TO_SELF_VIA_PARENT crosses_composite type=bool required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_TRANSITION_TO_SELF_VIA_PARENT kind=inspect_json

**注册表事实。** 严重级别 ``info``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 组合状态转换到自身，可能是有意强制重新进入子初始化和生命周期动作。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合状态转换到自身，可能是有意强制重新进入子初始化和生命周期动作。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``crosses_composite``
     - ``bool``
     - 是
     - 字段含义：该信息固定为真，表示转换跨越组合状态边界。

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state Active { state Leaf; [*] -> Leaf; }
       [*] -> Active;
       Active -> Active;
   }

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_TRANSITION_TO_SELF_VIA_PARENT`` 的修复方向。
典型修复是对 ``transition`` 执行 ``preserve_if_intentional``：针对“组合状态转换到自身，可能是有意强制重新进入子初始化和生命周期动作。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_TRANSITION_TO_SELF_VIA_PARENT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_TRANSITION_TO_SELF_VIA_PARENT`` 的反例边界。
不要这样处理：针对“组合状态转换到自身，可能是有意强制重新进入子初始化和生命周期动作。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-transition-shadowed-zh:

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


.. diagnostics-boundary W_TRANSITION_SHADOWED kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``transition``。

**含义。** 后面的同源出边转换被前面的触发条件完全覆盖，因此不会被选择。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。后面的同源出边转换被前面的触发条件完全覆盖，因此不会被选择。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。
   * - ``source_state_path``
     - ``str``
     - 是
     - 字段含义：产生该诊断的源状态点分路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。
   * - ``shadowed_by_count``
     - ``int``
     - 是
     - 字段含义：覆盖当前转换的前序转换数量。
   * - ``shadowed_by``
     - ``list[str]``
     - 是
     - 字段含义：覆盖当前转换的前序转换摘要列表。

.. diagnostics-example W_TRANSITION_SHADOWED 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

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

**示例 2**\ （``boundary_only``）——针对 ``W_TRANSITION_SHADOWED`` 的修复方向。
典型修复是对 ``transition_list`` 执行 ``reorder_transitions``：针对“后面的同源出边转换被前面的触发条件完全覆盖，因此不会被选择。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_TRANSITION_SHADOWED 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_TRANSITION_SHADOWED`` 的反例边界。
不要这样处理：针对“后面的同源出边转换被前面的触发条件完全覆盖，因此不会被选择。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

事件和作用域
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-event-ref-invalid-zh:

E_EVENT_REF_INVALID
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_EVENT_REF_INVALID severity=error emit_tier=lookup_api capability=pure_static span_object=event_declaration
.. diagnostics-ref E_EVENT_REF_INVALID event_ref type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_REF_INVALID reason type=str required=true enum=empty|bare_slash|invalid_absolute|invalid_relative|trailing_dots|beyond_root item_enum=- exact_values=-


.. diagnostics-boundary E_EVENT_REF_INVALID kind=api_only

**注册表事实。** 严重级别 ``error``；发射层级 ``lookup_api``；能力层级 ``pure_static``；源码对象 ``event_declaration``。

**含义。** 事件引用的文本形式不合法，例如空引用、裸 ``/``、末尾多余点号或越过根状态。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。事件引用的文本形式不合法，例如空引用、裸 ``/``、末尾多余点号或越过根状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``event_ref``
     - ``str``
     - 是
     - 字段含义：原始事件引用文本。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_EVENT_REF_INVALID 1 repro_api

**示例 1**\ （``repro_api``）——复现边界。
这个诊断由显式解析 API 发射。默认 ``pyfcstm inspect`` 通常不会以报告该码的方式调用对应 API，因此应按 API 边界复现，而不是期待默认命令行 JSON。

.. code-block:: fcstm

   state Root { state A; state B; A -> B : /; }

.. diagnostics-example E_EVENT_REF_INVALID 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_EVENT_REF_INVALID`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_scope_operator``：针对“事件引用的文本形式不合法，例如空引用、裸 ``/``、末尾多余点号或越过根状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_EVENT_REF_INVALID 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_EVENT_REF_INVALID`` 的反例边界。
不要这样处理：针对“事件引用的文本形式不合法，例如空引用、裸 ``/``、末尾多余点号或越过根状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-event-not-found-zh:

E_EVENT_NOT_FOUND
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_EVENT_NOT_FOUND severity=error emit_tier=lookup_api capability=pure_static span_object=event_declaration
.. diagnostics-ref E_EVENT_NOT_FOUND event_ref type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_NOT_FOUND scope type=str required=true enum=local|chain|absolute item_enum=- exact_values=-
.. diagnostics-ref E_EVENT_NOT_FOUND searched_from type=str_or_null required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_EVENT_NOT_FOUND kind=api_only

**注册表事实。** 严重级别 ``error``；发射层级 ``lookup_api``；能力层级 ``pure_static``；源码对象 ``event_declaration``。

**含义。** 事件引用的语法合法，但在目标作用域里找不到对应事件声明。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。事件引用的语法合法，但在目标作用域里找不到对应事件声明。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``event_ref``
     - ``str``
     - 是
     - 字段含义：原始事件引用文本。
   * - ``scope``
     - ``str``
     - 是
     - 字段含义：解析或验证使用的作用域。
   * - ``searched_from``
     - ``str_or_null``
     - 否
     - 字段含义：发起解析调用的状态点分路径。

.. diagnostics-example E_EVENT_NOT_FOUND 1 repro_api

**示例 1**\ （``repro_api``）——复现边界。
这个诊断由显式解析 API 发射。默认 ``pyfcstm inspect`` 通常不会以报告该码的方式调用对应 API，因此应按 API 边界复现，而不是期待默认命令行 JSON。

.. code-block:: fcstm

   state Root { state A; state B; A -> B :: NoEvent; }

.. diagnostics-example E_EVENT_NOT_FOUND 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_EVENT_NOT_FOUND`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_event_path``：针对“事件引用的语法合法，但在目标作用域里找不到对应事件声明。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_EVENT_NOT_FOUND 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_EVENT_NOT_FOUND`` 的反例边界。
不要这样处理：针对“事件引用的语法合法，但在目标作用域里找不到对应事件声明。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-duplicate-event-zh:

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


.. diagnostics-boundary W_COMBO_DUPLICATE_EVENT kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 组合转换触发器重复写入了同一个规范化事件项；通常是冗余或笔误。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合转换触发器重复写入了同一个规范化事件项；通常是冗余或笔误。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``origin_id``
     - ``str``
     - 是
     - 字段含义：原始组合转换的稳定标识。
   * - ``event_name``
     - ``str``
     - 是
     - 字段含义：相关事件的规范化限定名。
   * - ``term_index``
     - ``int``
     - 是
     - 字段含义：相关组合触发项的从零开始索引。
   * - ``first_term_index``
     - ``int``
     - 是
     - 字段含义：首次匹配触发项的从零开始索引。
   * - ``term_text``
     - ``str``
     - 是
     - 字段含义：相关触发项的规范化源码文本。
   * - ``first_term_text``
     - ``str``
     - 是
     - 字段含义：首次匹配触发项的规范化源码文本。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``trigger_span``
     - ``Span``
     - 否
     - 字段含义：组合触发后缀的源码范围。
   * - ``term_span``
     - ``Span``
     - 否
     - 字段含义：相关触发项的源码范围。
   * - ``first_term_span``
     - ``Span``
     - 否
     - 字段含义：首次匹配触发项的源码范围。

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + E1;
   }

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_DUPLICATE_EVENT`` 的修复方向。
典型修复是对 ``transition`` 执行 ``inspect_terms``：针对“组合转换触发器重复写入了同一个规范化事件项；通常是冗余或笔误。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_DUPLICATE_EVENT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_DUPLICATE_EVENT`` 的反例边界。
不要这样处理：针对“组合转换触发器重复写入了同一个规范化事件项；通常是冗余或笔误。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-unused-event-zh:

W_UNUSED_EVENT
^^^^^^^^^^^^^^

.. diagnostics-meta W_UNUSED_EVENT severity=warning emit_tier=static_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_UNUSED_EVENT event_qualified_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNUSED_EVENT scope type=str required=true enum=local|chain|absolute item_enum=- exact_values=-


.. diagnostics-boundary W_UNUSED_EVENT kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``event_declaration``。

**含义。** 某个 ``event`` 声明没有被任何转换引用。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。某个 ``event`` 声明没有被任何转换引用。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``event_qualified_name``
     - ``str``
     - 是
     - 字段含义：字段 ``event_qualified_name`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``scope``
     - ``str``
     - 是
     - 字段含义：解析或验证使用的作用域。

.. diagnostics-example W_UNUSED_EVENT 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       event Unused;
       state A;
       state B;
       [*] -> A;
       A -> B :: SomethingElse;
   }

.. diagnostics-example W_UNUSED_EVENT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_UNUSED_EVENT`` 的修复方向。
典型修复是对 ``transition`` 执行 ``wire_event``：针对“某个 ``event`` 声明没有被任何转换引用。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_UNUSED_EVENT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_UNUSED_EVENT`` 的反例边界。
不要这样处理：针对“某个 ``event`` 声明没有被任何转换引用。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-shadowed-event-zh:

W_SHADOWED_EVENT
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_SHADOWED_EVENT severity=warning emit_tier=static_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_SHADOWED_EVENT event_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SHADOWED_EVENT local_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_SHADOWED_EVENT chain_path type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_SHADOWED_EVENT kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``event_declaration``。

**含义。** 本地事件名遮蔽了同叶名的链式或绝对事件。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。本地事件名遮蔽了同叶名的链式或绝对事件。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``event_name``
     - ``str``
     - 是
     - 字段含义：相关事件的规范化限定名。
   * - ``local_path``
     - ``str``
     - 是
     - 字段含义：本地事件限定路径。
   * - ``chain_path``
     - ``str``
     - 是
     - 字段含义：链式或绝对事件限定路径。

.. diagnostics-example W_SHADOWED_EVENT 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

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

**示例 2**\ （``boundary_only``）——针对 ``W_SHADOWED_EVENT`` 的修复方向。
典型修复是对 ``event`` 执行 ``rename_event``：针对“本地事件名遮蔽了同叶名的链式或绝对事件。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_SHADOWED_EVENT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_SHADOWED_EVENT`` 的反例边界。
不要这样处理：针对“本地事件名遮蔽了同叶名的链式或绝对事件。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-transition-never-event-triggered-zh:

I_TRANSITION_NEVER_EVENT_TRIGGERED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TRANSITION_NEVER_EVENT_TRIGGERED severity=info emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TRANSITION_NEVER_EVENT_TRIGGERED transition_index type=int required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_TRANSITION_NEVER_EVENT_TRIGGERED kind=inspect_json

**注册表事实。** 严重级别 ``info``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 普通转换没有事件也没有守卫，是一个无条件下落候选。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。普通转换没有事件也没有守卫，是一个无条件下落候选。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``from_path``
     - ``str``
     - 是
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 是
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B;
   }

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_TRANSITION_NEVER_EVENT_TRIGGERED`` 的修复方向。
典型修复是对 ``transition`` 执行 ``keep_if_fallthrough``：针对“普通转换没有事件也没有守卫，是一个无条件下落候选。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_TRANSITION_NEVER_EVENT_TRIGGERED 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_TRANSITION_NEVER_EVENT_TRIGGERED`` 的反例边界。
不要这样处理：针对“普通转换没有事件也没有守卫，是一个无条件下落候选。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-event-unreachable-emit-zh:

W_EVENT_UNREACHABLE_EMIT
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_EVENT_UNREACHABLE_EMIT severity=warning emit_tier=verify_pipeline capability=pure_static span_object=event_declaration
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT event_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EVENT_UNREACHABLE_EMIT consumer_count type=int required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_EVENT_UNREACHABLE_EMIT kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``pure_static``；源码对象 ``event_declaration``。

**含义。** 某个已使用事件没有任何在守卫无关拓扑中可达的消费源。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。某个已使用事件没有任何在守卫无关拓扑中可达的消费源。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``event_name``
     - ``str``
     - 是
     - 字段含义：相关事件的规范化限定名。
   * - ``consumer_count``
     - ``int``
     - 是
     - 字段含义：该发现代表的不可达消费转换数量。

.. diagnostics-example W_EVENT_UNREACHABLE_EMIT 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

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

**示例 2**\ （``boundary_only``）——针对 ``W_EVENT_UNREACHABLE_EMIT`` 的修复方向。
典型修复是对 ``transition_source`` 执行 ``connect_consumer``：针对“某个已使用事件没有任何在守卫无关拓扑中可达的消费源。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_EVENT_UNREACHABLE_EMIT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_EVENT_UNREACHABLE_EMIT`` 的反例边界。
不要这样处理：针对“某个已使用事件没有任何在守卫无关拓扑中可达的消费源。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

组合与中继诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-combo-trigger-not-expanded-zh:

E_COMBO_TRIGGER_NOT_EXPANDED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_COMBO_TRIGGER_NOT_EXPANDED severity=error emit_tier=catalog_only capability=pure_static span_object=transition
.. diagnostics-ref E_COMBO_TRIGGER_NOT_EXPANDED state_path type=str_or_null required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_TRIGGER_NOT_EXPANDED trigger type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_COMBO_TRIGGER_NOT_EXPANDED kind=compatibility_only

**注册表事实。** 严重级别 ``error``；发射层级 ``catalog_only``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 兼容旧实现的失败关闭诊断；旧实现可能能解析组合触发，却还不能展开组合中继状态。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。兼容旧实现的失败关闭诊断；旧实现可能能解析组合触发，却还不能展开组合中继状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str_or_null``
     - 否
     - 字段含义：相关状态的点分路径。
   * - ``trigger``
     - ``str``
     - 是
     - 字段含义：组合触发后缀的规范化文本。

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 1 compatibility_only

**示例 1**\ （``compatibility_only``）——复现边界。
这个诊断保留兼容或历史失败关闭契约。当前 pyfcstm 正常路径不应发射它；保留该项是为了让旧工具输出仍可被解释。

.. code-block:: fcstm

   state Root { state A; state B; A -> B :: Go + Done; }

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_COMBO_TRIGGER_NOT_EXPANDED`` 的修复方向。
典型修复是对 ``transition`` 执行 ``wait_for_expansion_support``：针对“兼容旧实现的失败关闭诊断；旧实现可能能解析组合触发，却还不能展开组合中继状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_COMBO_TRIGGER_NOT_EXPANDED 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_COMBO_TRIGGER_NOT_EXPANDED`` 的反例边界。
不要这样处理：针对“兼容旧实现的失败关闭诊断；旧实现可能能解析组合触发，却还不能展开组合中继状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-reserved-prefix-state-kind-zh:

W_COMBO_RESERVED_PREFIX_STATE_KIND
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_RESERVED_PREFIX_STATE_KIND severity=warning emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND reserved_prefix type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RESERVED_PREFIX_STATE_KIND state_kind type=str required=true enum=state|composite item_enum=- exact_values=-


.. diagnostics-boundary W_COMBO_RESERVED_PREFIX_STATE_KIND kind=partial_static_boundary

**注册表事实。** 严重级别 ``warning``；发射层级 ``partial_static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 普通叶状态或组合状态使用了自动组合中继状态保留的 ``__combo_`` 前缀。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。普通叶状态或组合状态使用了自动组合中继状态保留的 ``__combo_`` 前缀。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_name``
     - ``str``
     - 是
     - 字段含义：相关状态名。
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``reserved_prefix``
     - ``str``
     - 是
     - 字段含义：组合中继伪状态保留前缀。
   * - ``state_kind``
     - ``str``
     - 是
     - 字段含义：触发诊断的状态类型。

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 1 boundary_only

**示例 1**\ （``boundary_only``）——复现边界。
这个注册表契约有意先于所有前端和后端的完整发射一致性。应把示例视为支持的边界形状，并在承诺默认命令行 JSON 前确认当前发射器。

.. code-block:: fcstm

   state Root { state __combo_user; [*] -> __combo_user; }

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_RESERVED_PREFIX_STATE_KIND`` 的修复方向。
典型修复是对 ``state_identifier`` 执行 ``rename_state``：针对“普通叶状态或组合状态使用了自动组合中继状态保留的 ``__combo_`` 前缀。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_RESERVED_PREFIX_STATE_KIND 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_RESERVED_PREFIX_STATE_KIND`` 的反例边界。
不要这样处理：针对“普通叶状态或组合状态使用了自动组合中继状态保留的 ``__combo_`` 前缀。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-relay-pseudo-has-actions-zh:

W_COMBO_RELAY_PSEUDO_HAS_ACTIONS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMBO_RELAY_PSEUDO_HAS_ACTIONS severity=warning emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS state_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS reserved_prefix type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMBO_RELAY_PSEUDO_HAS_ACTIONS action_kinds type=list[str] required=true enum=- item_enum=enter|during|exit|during_aspect exact_values=-


.. diagnostics-boundary W_COMBO_RELAY_PSEUDO_HAS_ACTIONS kind=partial_static_boundary

**注册表事实。** 严重级别 ``warning``；发射层级 ``partial_static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 组合中继命名空间里的伪状态包含生命周期动作或切面动作，因此不再是纯中继节点。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合中继命名空间里的伪状态包含生命周期动作或切面动作，因此不再是纯中继节点。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_name``
     - ``str``
     - 是
     - 字段含义：相关状态名。
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``reserved_prefix``
     - ``str``
     - 是
     - 字段含义：组合中继伪状态保留前缀。
   * - ``action_kinds``
     - ``list[str]``
     - 是
     - 字段含义：该伪状态上出现的生命周期或切面动作类型。

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 1 boundary_only

**示例 1**\ （``boundary_only``）——复现边界。
这个注册表契约有意先于所有前端和后端的完整发射一致性。应把示例视为支持的边界形状，并在承诺默认命令行 JSON 前确认当前发射器。

.. code-block:: fcstm

   def int x = 0; state Root { pseudo state __combo_user { enter { x = x + 1; } } state A; [*] -> A; }

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS`` 的修复方向。
典型修复是对 ``lifecycle_action`` 执行 ``move_action``：针对“组合中继命名空间里的伪状态包含生命周期动作或切面动作，因此不再是纯中继节点。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_RELAY_PSEUDO_HAS_ACTIONS 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS`` 的反例边界。
不要这样处理：针对“组合中继命名空间里的伪状态包含生命周期动作或切面动作，因此不再是纯中继节点。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-combo-pseudo-name-extended-zh:

I_COMBO_PSEUDO_NAME_EXTENDED
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_COMBO_PSEUDO_NAME_EXTENDED severity=info emit_tier=partial_static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED pseudo_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED payload_digest type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED default_digest_size type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_COMBO_PSEUDO_NAME_EXTENDED final_digest_size type=int required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_COMBO_PSEUDO_NAME_EXTENDED kind=partial_static_boundary

**注册表事实。** 严重级别 ``info``；发射层级 ``partial_static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 组合展开为了避开同作用域命名冲突，自动延长了生成中继名里的摘要前缀。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合展开为了避开同作用域命名冲突，自动延长了生成中继名里的摘要前缀。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``pseudo_name``
     - ``str``
     - 是
     - 字段含义：生成或冲突的伪状态名。
   * - ``payload_digest``
     - ``str``
     - 是
     - 字段含义：拥有该中继语义载荷的完整摘要。
   * - ``default_digest_size``
     - ``int``
     - 是
     - 字段含义：字段 ``default_digest_size`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``final_digest_size``
     - ``int``
     - 是
     - 字段含义：字段 ``final_digest_size`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 1 boundary_only

**示例 1**\ （``boundary_only``）——复现边界。
这个注册表契约有意先于所有前端和后端的完整发射一致性。应把示例视为支持的边界形状，并在承诺默认命令行 JSON 前确认当前发射器。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       pseudo state __combo_root_a__e1_hbafca7f66598;
       [*] -> A;
       A -> B :: E1 + E2;
   }

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_COMBO_PSEUDO_NAME_EXTENDED`` 的修复方向。
典型修复是对 ``pseudo_state`` 执行 ``keep_generated_name``：针对“组合展开为了避开同作用域命名冲突，自动延长了生成中继名里的摘要前缀。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_COMBO_PSEUDO_NAME_EXTENDED 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_COMBO_PSEUDO_NAME_EXTENDED`` 的反例边界。
不要这样处理：针对“组合展开为了避开同作用域命名冲突，自动延长了生成中继名里的摘要前缀。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-combo-pseudo-name-collision-zh:

E_COMBO_PSEUDO_NAME_COLLISION
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_COMBO_PSEUDO_NAME_COLLISION severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION pseudo_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_COMBO_PSEUDO_NAME_COLLISION payload_digest type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_COMBO_PSEUDO_NAME_COLLISION kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 组合展开即使使用完整语义摘要也无法分配安全伪状态名，因此拒绝展开。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合展开即使使用完整语义摘要也无法分配安全伪状态名，因此拒绝展开。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``pseudo_name``
     - ``str``
     - 是
     - 字段含义：生成或冲突的伪状态名。
   * - ``payload_digest``
     - ``str``
     - 是
     - 字段含义：拥有该中继语义载荷的完整摘要。

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state A; state B; [*] -> A; A -> B :: E1 + E2; }

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_COMBO_PSEUDO_NAME_COLLISION`` 的修复方向。
典型修复是对 ``transition`` 执行 ``report_internal_collision``：针对“组合展开即使使用完整语义摘要也无法分配安全伪状态名，因此拒绝展开。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_COMBO_PSEUDO_NAME_COLLISION 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_COMBO_PSEUDO_NAME_COLLISION`` 的反例边界。
不要这样处理：针对“组合展开即使使用完整语义摘要也无法分配安全伪状态名，因此拒绝展开。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-guard-const-true-zh:

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


.. diagnostics-boundary W_COMBO_GUARD_CONST_TRUE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 组合触发器中的某个守卫项被证明恒为真，对生成的中继链没有约束作用。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合触发器中的某个守卫项被证明恒为真，对生成的中继链没有约束作用。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``origin_id``
     - ``str``
     - 是
     - 字段含义：原始组合转换的稳定标识。
   * - ``term_index``
     - ``int``
     - 是
     - 字段含义：相关组合触发项的从零开始索引。
   * - ``term_text``
     - ``str``
     - 是
     - 字段含义：相关触发项的规范化源码文本。
   * - ``folded_value``
     - ``bool``
     - 是
     - 字段含义：常量折叠或求解器证明得到的布尔值。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``trigger_span``
     - ``Span``
     - 否
     - 字段含义：组合触发后缀的源码范围。
   * - ``term_span``
     - ``Span``
     - 否
     - 字段含义：相关触发项的源码范围。
   * - ``value_span``
     - ``Span``
     - 否
     - 字段含义：方括号内守卫表达式的源码范围。

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + [x > 0 || x <= 0] + E2;
   }

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_CONST_TRUE`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_guard_term``：针对“组合触发器中的某个守卫项被证明恒为真，对生成的中继链没有约束作用。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_GUARD_CONST_TRUE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_CONST_TRUE`` 的反例边界。
不要这样处理：针对“组合触发器中的某个守卫项被证明恒为真，对生成的中继链没有约束作用。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-guard-const-false-zh:

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


.. diagnostics-boundary W_COMBO_GUARD_CONST_FALSE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 组合触发器中的某个守卫项被证明恒为假，经过该项的组合分支无法完成。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合触发器中的某个守卫项被证明恒为假，经过该项的组合分支无法完成。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``origin_id``
     - ``str``
     - 是
     - 字段含义：原始组合转换的稳定标识。
   * - ``term_index``
     - ``int``
     - 是
     - 字段含义：相关组合触发项的从零开始索引。
   * - ``term_text``
     - ``str``
     - 是
     - 字段含义：相关触发项的规范化源码文本。
   * - ``folded_value``
     - ``bool``
     - 是
     - 字段含义：常量折叠或求解器证明得到的布尔值。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``trigger_span``
     - ``Span``
     - 否
     - 字段含义：组合触发后缀的源码范围。
   * - ``term_span``
     - ``Span``
     - 否
     - 字段含义：相关触发项的源码范围。
   * - ``value_span``
     - ``Span``
     - 否
     - 字段含义：方括号内守卫表达式的源码范围。

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: E1 + [x > 0 && x <= 0] + E2;
   }

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_CONST_FALSE`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_guard_term``：针对“组合触发器中的某个守卫项被证明恒为假，经过该项的组合分支无法完成。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_GUARD_CONST_FALSE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_CONST_FALSE`` 的反例边界。
不要这样处理：针对“组合触发器中的某个守卫项被证明恒为假，经过该项的组合分支无法完成。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-guard-prefix-implied-zh:

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


.. diagnostics-boundary W_COMBO_GUARD_PREFIX_IMPLIED kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 在无副作用的组合前缀中，前面的守卫项已经蕴含后面的守卫项。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。在无副作用的组合前缀中，前面的守卫项已经蕴含后面的守卫项。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``origin_id``
     - ``str``
     - 是
     - 字段含义：原始组合转换的稳定标识。
   * - ``term_index``
     - ``int``
     - 是
     - 字段含义：相关组合触发项的从零开始索引。
   * - ``prior_term_index``
     - ``int``
     - 是
     - 字段含义：字段 ``prior_term_index`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``term_text``
     - ``str``
     - 是
     - 字段含义：相关触发项的规范化源码文本。
   * - ``prior_term_text``
     - ``str``
     - 是
     - 字段含义：字段 ``prior_term_text`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``trigger_span``
     - ``Span``
     - 否
     - 字段含义：组合触发后缀的源码范围。
   * - ``term_span``
     - ``Span``
     - 否
     - 字段含义：相关触发项的源码范围。
   * - ``value_span``
     - ``Span``
     - 否
     - 字段含义：方括号内守卫表达式的源码范围。
   * - ``prior_term_span``
     - ``Span``
     - 否
     - 字段含义：字段 ``prior_term_span`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``prior_value_span``
     - ``Span``
     - 否
     - 字段含义：字段 ``prior_value_span`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : [x > 0] + [x > -1];
   }

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_PREFIX_IMPLIED`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_guard_term``：针对“在无副作用的组合前缀中，前面的守卫项已经蕴含后面的守卫项。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_GUARD_PREFIX_IMPLIED 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_PREFIX_IMPLIED`` 的反例边界。
不要这样处理：针对“在无副作用的组合前缀中，前面的守卫项已经蕴含后面的守卫项。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-combo-guard-prefix-contradicts-zh:

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


.. diagnostics-boundary W_COMBO_GUARD_PREFIX_CONTRADICTS kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 在无副作用的组合前缀中，前面的守卫项与后面的守卫项矛盾。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。在无副作用的组合前缀中，前面的守卫项与后面的守卫项矛盾。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``origin_id``
     - ``str``
     - 是
     - 字段含义：原始组合转换的稳定标识。
   * - ``term_index``
     - ``int``
     - 是
     - 字段含义：相关组合触发项的从零开始索引。
   * - ``prior_term_index``
     - ``int``
     - 是
     - 字段含义：字段 ``prior_term_index`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``term_text``
     - ``str``
     - 是
     - 字段含义：相关触发项的规范化源码文本。
   * - ``prior_term_text``
     - ``str``
     - 是
     - 字段含义：字段 ``prior_term_text`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``trigger_span``
     - ``Span``
     - 否
     - 字段含义：组合触发后缀的源码范围。
   * - ``term_span``
     - ``Span``
     - 否
     - 字段含义：相关触发项的源码范围。
   * - ``value_span``
     - ``Span``
     - 否
     - 字段含义：方括号内守卫表达式的源码范围。
   * - ``prior_term_span``
     - ``Span``
     - 否
     - 字段含义：字段 ``prior_term_span`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。
   * - ``prior_value_span``
     - ``Span``
     - 否
     - 字段含义：字段 ``prior_value_span`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : [x > 0] + [x < 0];
   }

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_PREFIX_CONTRADICTS`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_guard_term``：针对“在无副作用的组合前缀中，前面的守卫项与后面的守卫项矛盾。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMBO_GUARD_PREFIX_CONTRADICTS 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMBO_GUARD_PREFIX_CONTRADICTS`` 的反例边界。
不要这样处理：针对“在无副作用的组合前缀中，前面的守卫项与后面的守卫项矛盾。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

强制转换诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-forced-transition-expansion-zh:

E_FORCED_TRANSITION_EXPANSION
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_FORCED_TRANSITION_EXPANSION severity=error emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref E_FORCED_TRANSITION_EXPANSION original_raw type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_FORCED_TRANSITION_EXPANSION reason type=str required=true enum=src_not_found|tgt_not_found|src_is_root|wildcard_no_descendants item_enum=- exact_values=-


.. diagnostics-boundary E_FORCED_TRANSITION_EXPANSION kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 强制转换因为源或目标引用非法而无法展开成具体转换。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。强制转换因为源或目标引用非法而无法展开成具体转换。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``original_raw``
     - ``str``
     - 是
     - 字段含义：原始强制转换文本。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root { state A; !NoSuch -> A; }

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_FORCED_TRANSITION_EXPANSION`` 的修复方向。
典型修复是对 ``forced_transition`` 执行 ``fix_source``：针对“强制转换因为源或目标引用非法而无法展开成具体转换。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_FORCED_TRANSITION_EXPANSION 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_FORCED_TRANSITION_EXPANSION`` 的反例边界。
不要这样处理：针对“强制转换因为源或目标引用非法而无法展开成具体转换。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-forced-never-expands-zh:

W_FORCED_NEVER_EXPANDS
^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_NEVER_EXPANDS severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_FORCED_NEVER_EXPANDS state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_NEVER_EXPANDS original_raw type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_FORCED_NEVER_EXPANDS kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 强制转换声明所在作用域没有可用于展开的具体子状态。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。强制转换声明所在作用域没有可用于展开的具体子状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``original_raw``
     - ``str``
     - 是
     - 字段含义：原始强制转换文本。

.. diagnostics-example W_FORCED_NEVER_EXPANDS 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A {
           !* -> [*];
       }
       [*] -> A;
   }

.. diagnostics-example W_FORCED_NEVER_EXPANDS 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_FORCED_NEVER_EXPANDS`` 的修复方向。
典型修复是对 ``forced_transition`` 执行 ``move_transition``：针对“强制转换声明所在作用域没有可用于展开的具体子状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_FORCED_NEVER_EXPANDS 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_FORCED_NEVER_EXPANDS`` 的反例边界。
不要这样处理：针对“强制转换声明所在作用域没有可用于展开的具体子状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-forced-overrides-normal-zh:

W_FORCED_OVERRIDES_NORMAL
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_OVERRIDES_NORMAL severity=warning emit_tier=static_pipeline capability=pure_static span_object=transition
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL forced_declaration_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_OVERRIDES_NORMAL normal_transition_span type=Span required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_FORCED_OVERRIDES_NORMAL kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``transition``。

**含义。** 强制转换展开后与某个普通转换的源、目标、事件和守卫相同。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。强制转换展开后与某个普通转换的源、目标、事件和守卫相同。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``from_path``
     - ``str``
     - 是
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 是
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``forced_declaration_span``
     - ``Span``
     - 否
     - 字段含义：强制转换声明的源码范围。
   * - ``normal_transition_span``
     - ``Span``
     - 否
     - 字段含义：普通转换声明的源码范围。

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Go;
       !A -> B :: Go;
   }

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_FORCED_OVERRIDES_NORMAL`` 的修复方向。
典型修复是对 ``forced_transition`` 执行 ``remove_duplicate``：针对“强制转换展开后与某个普通转换的源、目标、事件和守卫相同。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_FORCED_OVERRIDES_NORMAL 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_FORCED_OVERRIDES_NORMAL`` 的反例边界。
不要这样处理：针对“强制转换展开后与某个普通转换的源、目标、事件和守卫相同。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-forced-guard-unsat-zh:

W_FORCED_GUARD_UNSAT
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_FORCED_GUARD_UNSAT severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_FORCED_GUARD_UNSAT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT transition_summary type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_FORCED_GUARD_UNSAT scope type=str required=true enum=dsl_def_init_only item_enum=- exact_values=-


.. diagnostics-boundary W_FORCED_GUARD_UNSAT kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 强制转换守卫在声明初始化值下不可满足。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。强制转换守卫在声明初始化值下不可满足。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。
   * - ``scope``
     - ``str``
     - 是
     - 字段含义：解析或验证使用的作用域。

.. diagnostics-example W_FORCED_GUARD_UNSAT 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       !A -> B : if [x > 0];
   }

.. diagnostics-example W_FORCED_GUARD_UNSAT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_FORCED_GUARD_UNSAT`` 的修复方向。
典型修复是对 ``variable_definition`` 执行 ``adjust_initializer``：针对“强制转换守卫在声明初始化值下不可满足。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_FORCED_GUARD_UNSAT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_FORCED_GUARD_UNSAT`` 的反例边界。
不要这样处理：针对“强制转换守卫在声明初始化值下不可满足。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

守卫、效果动作与求解器诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-guard-const-false-zh:

W_GUARD_CONST_FALSE
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_CONST_FALSE severity=warning emit_tier=static_pipeline capability=const_fold span_object=guard_expression
.. diagnostics-ref W_GUARD_CONST_FALSE transition_span type=Span required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE folded_value type=bool required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE from_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE to_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE guard_text type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_CONST_FALSE transition_index type=int required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_GUARD_CONST_FALSE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``const_fold``；源码对象 ``guard_expression``。

**含义。** 转换守卫可由轻量常量折叠器判定恒为假，因此该转换永远不会触发。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换守卫可由轻量常量折叠器判定恒为假，因此该转换永远不会触发。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``folded_value``
     - ``bool``
     - 是
     - 字段含义：常量折叠或求解器证明得到的布尔值。
   * - ``from_path``
     - ``str``
     - 否
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 否
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``guard_text``
     - ``str``
     - 否
     - 字段含义：规范化后的守卫表达式文本。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example W_GUARD_CONST_FALSE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(0x0F & 0xF0) != 0];
   }

.. diagnostics-example W_GUARD_CONST_FALSE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_GUARD_CONST_FALSE`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_guard``：针对“转换守卫可由轻量常量折叠器判定恒为假，因此该转换永远不会触发。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_GUARD_CONST_FALSE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_GUARD_CONST_FALSE`` 的反例边界。
不要这样处理：针对“转换守卫可由轻量常量折叠器判定恒为假，因此该转换永远不会触发。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-guard-const-true-zh:

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


.. diagnostics-boundary W_GUARD_CONST_TRUE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``const_fold``；源码对象 ``guard_expression``。

**含义。** 转换守卫可由轻量常量折叠器判定恒为真，因此该守卫对运行时状态没有实际过滤作用。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换守卫可由轻量常量折叠器判定恒为真，因此该守卫对运行时状态没有实际过滤作用。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``guard_span``
     - ``Span``
     - 否
     - 字段含义：可删除守卫后缀的源码范围。
   * - ``folded_value``
     - ``bool``
     - 是
     - 字段含义：常量折叠或求解器证明得到的布尔值。
   * - ``from_path``
     - ``str``
     - 否
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 否
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``guard_text``
     - ``str``
     - 否
     - 字段含义：规范化后的守卫表达式文本。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example W_GUARD_CONST_TRUE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(1 + 2) == 3];
   }

.. diagnostics-example W_GUARD_CONST_TRUE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_GUARD_CONST_TRUE`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_guard``：针对“转换守卫可由轻量常量折叠器判定恒为真，因此该守卫对运行时状态没有实际过滤作用。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_GUARD_CONST_TRUE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_GUARD_CONST_TRUE`` 的反例边界。
不要这样处理：针对“转换守卫可由轻量常量折叠器判定恒为真，因此该守卫对运行时状态没有实际过滤作用。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-guard-vars-never-change-zh:

W_GUARD_VARS_NEVER_CHANGE
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_VARS_NEVER_CHANGE severity=warning emit_tier=static_pipeline capability=pure_static span_object=guard_expression
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE from_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE to_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_VARS_NEVER_CHANGE guard_vars type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_GUARD_VARS_NEVER_CHANGE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``guard_expression``。

**含义。** 转换守卫读取的变量从未被生命周期动作或转换效果修改，因此只依赖初始值。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换守卫读取的变量从未被生命周期动作或转换效果修改，因此只依赖初始值。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``from_path``
     - ``str``
     - 是
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``to_path``
     - ``str``
     - 是
     - 字段含义：转换目标状态路径；退出标记可写作 ``[*]``。
   * - ``guard_vars``
     - ``list[str]``
     - 是
     - 字段含义：不会变化但被守卫读取的变量列表。

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_GUARD_VARS_NEVER_CHANGE`` 的修复方向。
典型修复是对 ``action_or_effect`` 执行 ``add_write``：针对“转换守卫读取的变量从未被生命周期动作或转换效果修改，因此只依赖初始值。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_GUARD_VARS_NEVER_CHANGE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_GUARD_VARS_NEVER_CHANGE`` 的反例边界。
不要这样处理：针对“转换守卫读取的变量从未被生命周期动作或转换效果修改，因此只依赖初始值。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-effect-self-assign-zh:

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


.. diagnostics-boundary W_EFFECT_SELF_ASSIGN kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``effect_statement``。

**含义。** 转换效果把变量直接赋值给它自己。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换效果把变量直接赋值给它自己。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``from_path``
     - ``str``
     - 否
     - 字段含义：转换源状态路径；入口标记可写作 ``[*]``。
   * - ``generated_state_path``
     - ``str``
     - 否
     - 字段含义：生成组合伪状态路径，仅作辅助溯源。
   * - ``generated_from_path``
     - ``str``
     - 否
     - 字段含义：生成转换源路径，仅作辅助溯源。
   * - ``generated_to_path``
     - ``str``
     - 否
     - 字段含义：生成转换目标路径，仅作辅助溯源。
   * - ``combo_origin_id``
     - ``str``
     - 否
     - 字段含义：生成终端效果对应的原始组合转换标识。
   * - ``combo_owner_path``
     - ``str``
     - 否
     - 字段含义：入口组合诊断的拥有组合状态路径。
   * - ``transition_span``
     - ``Span``
     - 否
     - 字段含义：相关转换声明的源码范围。
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``effect_self_assign_anchor``
     - ``str``
     - 否
     - 字段含义：可唯一定位自赋值效果语句时使用的变量锚点。
   * - ``suggested_fix``
     - ``dict``
     - 否
     - 字段含义：可选的结构化快速修复载荷。
   * - ``transition_index``
     - ``int``
     - 否
     - 字段含义：父优先转换顺序中的从零开始索引。

.. diagnostics-example W_EFFECT_SELF_ASSIGN 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int x = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B effect { x = x; }
   }

.. diagnostics-example W_EFFECT_SELF_ASSIGN 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_EFFECT_SELF_ASSIGN`` 的修复方向。
典型修复是对 ``effect_statement`` 执行 ``remove_statement``：针对“转换效果把变量直接赋值给它自己。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_EFFECT_SELF_ASSIGN 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_EFFECT_SELF_ASSIGN`` 的反例边界。
不要这样处理：针对“转换效果把变量直接赋值给它自己。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-dead-guard-zh:

W_DEAD_GUARD
^^^^^^^^^^^^

.. diagnostics-meta W_DEAD_GUARD severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_DEAD_GUARD algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_GUARD transition_summary type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_DEAD_GUARD kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 在模型变量类型和运行时已定义性约束下，转换守卫不可满足。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。在模型变量类型和运行时已定义性约束下，转换守卫不可满足。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。

.. diagnostics-example W_DEAD_GUARD 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x > 1 && x < 0];
   }

.. diagnostics-example W_DEAD_GUARD 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_DEAD_GUARD`` 的修复方向。
典型修复是对 ``transition`` 执行 ``fix_guard``：针对“在模型变量类型和运行时已定义性约束下，转换守卫不可满足。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_DEAD_GUARD 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_DEAD_GUARD`` 的反例边界。
不要这样处理：针对“在模型变量类型和运行时已定义性约束下，转换守卫不可满足。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-guard-tautology-zh:

W_GUARD_TAUTOLOGY
^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_GUARD_TAUTOLOGY severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=guard_expression
.. diagnostics-ref W_GUARD_TAUTOLOGY algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_GUARD_TAUTOLOGY transition_summary type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_GUARD_TAUTOLOGY kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``guard_expression``。

**含义。** 在模型变量类型和运行时已定义性约束下，转换守卫对所有取值都为真。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。在模型变量类型和运行时已定义性约束下，转换守卫对所有取值都为真。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。

.. diagnostics-example W_GUARD_TAUTOLOGY 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x >= 0 || x < 0];
   }

.. diagnostics-example W_GUARD_TAUTOLOGY 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_GUARD_TAUTOLOGY`` 的修复方向。
典型修复是对 ``transition`` 执行 ``remove_redundant_guard``：针对“在模型变量类型和运行时已定义性约束下，转换守卫对所有取值都为真。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_GUARD_TAUTOLOGY 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_GUARD_TAUTOLOGY`` 的反例边界。
不要这样处理：针对“在模型变量类型和运行时已定义性约束下，转换守卫对所有取值都为真。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-effect-smt-no-op-zh:

W_EFFECT_SMT_NO_OP
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_EFFECT_SMT_NO_OP severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=effect_statement
.. diagnostics-ref W_EFFECT_SMT_NO_OP algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_EFFECT_SMT_NO_OP transition_summary type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_EFFECT_SMT_NO_OP kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``effect_statement``。

**含义。** 在所有满足守卫且运行时定义良好的执行中，转换效果不会改变任何模型变量。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。在所有满足守卫且运行时定义良好的执行中，转换效果不会改变任何模型变量。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。

.. diagnostics-example W_EFFECT_SMT_NO_OP 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x >= 0] effect { x = x + 0; };
   }

.. diagnostics-example W_EFFECT_SMT_NO_OP 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_EFFECT_SMT_NO_OP`` 的修复方向。
典型修复是对 ``effect_block`` 执行 ``remove_effect``：针对“在所有满足守卫且运行时定义良好的执行中，转换效果不会改变任何模型变量。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_EFFECT_SMT_NO_OP 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_EFFECT_SMT_NO_OP`` 的反例边界。
不要这样处理：针对“在所有满足守卫且运行时定义良好的执行中，转换效果不会改变任何模型变量。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-effect-guard-contradict-zh:

I_EFFECT_GUARD_CONTRADICT
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_EFFECT_GUARD_CONTRADICT severity=info emit_tier=verify_pipeline capability=requires_solver span_object=effect_statement
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT transition type=dict required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_EFFECT_GUARD_CONTRADICT transition_summary type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_EFFECT_GUARD_CONTRADICT kind=verify_smt_linear

**注册表事实。** 严重级别 ``info``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``effect_statement``。

**含义。** 转换效果执行后会让同一转换守卫变为假。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。转换效果执行后会让同一转换守卫变为假。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``transition``
     - ``dict``
     - 是
     - 字段含义：原始验证转换载荷。
   * - ``transition_summary``
     - ``str``
     - 是
     - 字段含义：由原始载荷派生的稳定转换摘要。

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A;
       A -> B : if [x > 0] effect { x = 0; };
   }

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_EFFECT_GUARD_CONTRADICT`` 的修复方向。
典型修复是对 ``transition`` 执行 ``review_one_shot``：针对“转换效果执行后会让同一转换守卫变为假。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_EFFECT_GUARD_CONTRADICT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_EFFECT_GUARD_CONTRADICT`` 的反例边界。
不要这样处理：针对“转换效果执行后会让同一转换守卫变为假。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

生命周期、切面和组合状态诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-e-during-aspect-invalid-zh:

E_DURING_ASPECT_INVALID
^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_DURING_ASPECT_INVALID severity=error emit_tier=static_pipeline capability=pure_static span_object=lifecycle_action
.. diagnostics-ref E_DURING_ASPECT_INVALID state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref E_DURING_ASPECT_INVALID state_kind type=str required=true enum=leaf|composite item_enum=- exact_values=-
.. diagnostics-ref E_DURING_ASPECT_INVALID aspect type=str_or_null required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_DURING_ASPECT_INVALID kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``lifecycle_action``。

**含义。** ``during`` 块的写法与宿主状态类型不一致；叶状态和组合状态对普通 ``during`` 与切面 ``during`` 的要求不同。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``during`` 块的写法与宿主状态类型不一致；叶状态和组合状态对普通 ``during`` 与切面 ``during`` 的要求不同。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``state_kind``
     - ``str``
     - 是
     - 字段含义：触发诊断的状态类型。
   * - ``aspect``
     - ``str_or_null``
     - 否
     - 字段含义：实际使用的切面方向。

.. diagnostics-example E_DURING_ASPECT_INVALID 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root {
       state A {
           during before { }
       }
   }

.. diagnostics-example E_DURING_ASPECT_INVALID 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_DURING_ASPECT_INVALID`` 的修复方向。
典型修复是对 ``aspect_declaration`` 执行 ``move_to_composite``：针对“``during`` 块的写法与宿主状态类型不一致；叶状态和组合状态对普通 ``during`` 与切面 ``during`` 的要求不同。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_DURING_ASPECT_INVALID 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_DURING_ASPECT_INVALID`` 的反例边界。
不要这样处理：针对“``during`` 块的写法与宿主状态类型不一致；叶状态和组合状态对普通 ``during`` 与切面 ``during`` 的要求不同。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-e-pseudo-not-leaf-zh:

E_PSEUDO_NOT_LEAF
^^^^^^^^^^^^^^^^^

.. diagnostics-meta E_PSEUDO_NOT_LEAF severity=error emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref E_PSEUDO_NOT_LEAF state_path type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary E_PSEUDO_NOT_LEAF kind=cli_error

**注册表事实。** 严重级别 ``error``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 带 ``pseudo`` 关键字的状态仍然声明了子状态；伪状态必须是叶节点。

**面向 LLM 的修复摘要。** 这是会阻塞模型构建或目标 API 解析的错误。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。带 ``pseudo`` 关键字的状态仍然声明了子状态；伪状态必须是叶节点。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。

.. diagnostics-example E_PSEUDO_NOT_LEAF 1 cli_error

**示例 1**\ （``cli_error``）——复现边界。
这个源码形状会通过 ``pyfcstm inspect`` 复现受控的模型校验失败。当前命令行会在成功生成检查 JSON 前以非零状态退出，因此应断言错误文本和退出状态，不应期待在 ``diagnostics[]`` 中读到该码。

.. code-block:: fcstm

   state Root {
       pseudo state Outer {
           state Inner;
           [*] -> Inner;
       }
   }

.. diagnostics-example E_PSEUDO_NOT_LEAF 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``E_PSEUDO_NOT_LEAF`` 的修复方向。
典型修复是对 ``state_definition`` 执行 ``drop_pseudo_marker``：针对“带 ``pseudo`` 关键字的状态仍然声明了子状态；伪状态必须是叶节点。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example E_PSEUDO_NOT_LEAF 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``E_PSEUDO_NOT_LEAF`` 的反例边界。
不要这样处理：针对“带 ``pseudo`` 关键字的状态仍然声明了子状态；伪状态必须是叶节点。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-during-const-assign-zh:

W_DURING_CONST_ASSIGN
^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DURING_CONST_ASSIGN severity=warning emit_tier=static_pipeline capability=const_fold span_object=lifecycle_action
.. diagnostics-ref W_DURING_CONST_ASSIGN state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DURING_CONST_ASSIGN var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DURING_CONST_ASSIGN value type=number required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_DURING_CONST_ASSIGN kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``const_fold``；源码对象 ``lifecycle_action``。

**含义。** 普通 ``during`` 动作每个周期都把变量写成同一个字面量数值。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。普通 ``during`` 动作每个周期都把变量写成同一个字面量数值。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``value``
     - ``number``
     - 是
     - 字段含义：字段 ``value`` 的稳定载荷；具体含义由本诊断的含义、类型和枚举共同限定。

.. diagnostics-example W_DURING_CONST_ASSIGN 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int counter = 0;
   state Root {
       state Idle {
           during { counter = (2 + 3) * 4; }
       }
       [*] -> Idle;
   }

.. diagnostics-example W_DURING_CONST_ASSIGN 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_DURING_CONST_ASSIGN`` 的修复方向。
典型修复是对 ``action`` 执行 ``move_to_enter``：针对“普通 ``during`` 动作每个周期都把变量写成同一个字面量数值。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_DURING_CONST_ASSIGN 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_DURING_CONST_ASSIGN`` 的反例边界。
不要这样处理：针对“普通 ``during`` 动作每个周期都把变量写成同一个字面量数值。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-aspect-no-descendant-leaf-zh:

W_ASPECT_NO_DESCENDANT_LEAF
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_ASPECT_NO_DESCENDANT_LEAF severity=warning emit_tier=static_pipeline capability=pure_static span_object=lifecycle_action
.. diagnostics-ref W_ASPECT_NO_DESCENDANT_LEAF composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_ASPECT_NO_DESCENDANT_LEAF aspect type=str required=true enum=before|after item_enum=- exact_values=-


.. diagnostics-boundary W_ASPECT_NO_DESCENDANT_LEAF kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``lifecycle_action``。

**含义。** ``>> during`` 切面挂在没有非伪叶子后代的状态上，因此不会影响任何叶周期。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``>> during`` 切面挂在没有非伪叶子后代的状态上，因此不会影响任何叶周期。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``composite_path``
     - ``str``
     - 是
     - 字段含义：相关组合状态的点分路径。
   * - ``aspect``
     - ``str``
     - 是
     - 字段含义：实际使用的切面方向。

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       pseudo state Marker;
       [*] -> Marker;
       >> during before { }
   }

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_ASPECT_NO_DESCENDANT_LEAF`` 的修复方向。
典型修复是对 ``composite_state`` 执行 ``add_leaf``：针对“``>> during`` 切面挂在没有非伪叶子后代的状态上，因此不会影响任何叶周期。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_ASPECT_NO_DESCENDANT_LEAF 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_ASPECT_NO_DESCENDANT_LEAF`` 的反例边界。
不要这样处理：针对“``>> during`` 切面挂在没有非伪叶子后代的状态上，因此不会影响任何叶周期。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-enter-during-contradict-zh:

I_ENTER_DURING_CONTRADICT
^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_ENTER_DURING_CONTRADICT severity=info emit_tier=verify_pipeline capability=requires_solver span_object=lifecycle_action
.. diagnostics-ref I_ENTER_DURING_CONTRADICT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT condition type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT condition_source type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_ENTER_DURING_CONTRADICT branch_taken type=str required=true enum=true|false item_enum=- exact_values=-


.. diagnostics-boundary I_ENTER_DURING_CONTRADICT kind=verify_smt_linear

**注册表事实。** 严重级别 ``info``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``lifecycle_action``。

**含义。** 进入时赋值会让首个周期的 ``during`` 分支条件预先确定。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。进入时赋值会让首个周期的 ``during`` 分支条件预先确定。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``condition``
     - ``str``
     - 是
     - 字段含义：被证明预先确定的首周期 ``during`` 条件。
   * - ``condition_source``
     - ``str``
     - 是
     - 字段含义：``during`` 操作块内该条件的来源标签。
   * - ``branch_taken``
     - ``str``
     - 是
     - 字段含义：进入后被强制选择的分支方向。

.. diagnostics-example I_ENTER_DURING_CONTRADICT 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

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

**示例 2**\ （``boundary_only``）——针对 ``I_ENTER_DURING_CONTRADICT`` 的修复方向。
典型修复是对 ``lifecycle_action`` 执行 ``review_enter_during_relation``：针对“进入时赋值会让首个周期的 ``during`` 分支条件预先确定。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_ENTER_DURING_CONTRADICT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_ENTER_DURING_CONTRADICT`` 的反例边界。
不要这样处理：针对“进入时赋值会让首个周期的 ``during`` 分支条件预先确定。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-composite-init-incomplete-zh:

W_COMPOSITE_INIT_INCOMPLETE
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_COMPOSITE_INIT_INCOMPLETE severity=warning emit_tier=verify_pipeline capability=requires_solver span_object=composite_block
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE verification_scope type=str required=true enum=smt_local item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE init_transition_count type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE init_transitions type=list[str] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_COMPOSITE_INIT_INCOMPLETE witness type=str_or_null required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_COMPOSITE_INIT_INCOMPLETE kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``requires_solver``；源码对象 ``composite_block``。

**含义。** 组合状态的入口转换不能共同覆盖所有变量和事件输入。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合状态的入口转换不能共同覆盖所有变量和事件输入。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``composite_path``
     - ``str``
     - 是
     - 字段含义：相关组合状态的点分路径。
   * - ``init_transition_count``
     - ``int``
     - 是
     - 字段含义：纳入分析的入口转换数量。
   * - ``init_transitions``
     - ``list[str]``
     - 是
     - 字段含义：纳入分析的入口转换稳定摘要。
   * - ``witness``
     - ``str_or_null``
     - 否
     - 字段含义：可选求解器模型，用于展示未覆盖输入取值。

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   def int x = 0;
   state System {
       state A;
       state B;
       [*] -> A : if [x > 0];
       [*] -> B : if [x < 0];
   }

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_COMPOSITE_INIT_INCOMPLETE`` 的修复方向。
典型修复是对 ``composite_state`` 执行 ``add_catch_all_initial``：针对“组合状态的入口转换不能共同覆盖所有变量和事件输入。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_COMPOSITE_INIT_INCOMPLETE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_COMPOSITE_INIT_INCOMPLETE`` 的反例边界。
不要这样处理：针对“组合状态的入口转换不能共同覆盖所有变量和事件输入。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

数据流诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-unreferenced-var-zh:

W_UNREFERENCED_VAR
^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNREFERENCED_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_UNREFERENCED_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR init_value type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR definition_delete_anchor type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNREFERENCED_VAR suggested_fix type=dict required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_UNREFERENCED_VAR kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``variable_declaration``。

**含义。** 变量无法通过 DSL 数据流影响任何转换守卫，且没有可见抽象动作可能在 DSL 外使用它。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。变量无法通过 DSL 数据流影响任何转换守卫，且没有可见抽象动作可能在 DSL 外使用它。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``init_value``
     - ``str``
     - 是
     - 字段含义：初始值源码文本。
   * - ``definition_delete_anchor``
     - ``str``
     - 否
     - 字段含义：可安全删除变量声明时使用的定位锚点。
   * - ``suggested_fix``
     - ``dict``
     - 否
     - 字段含义：可选的结构化快速修复载荷。

.. diagnostics-example W_UNREFERENCED_VAR 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

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

**示例 2**\ （``boundary_only``）——针对 ``W_UNREFERENCED_VAR`` 的修复方向。
典型修复是对 ``variable_definition`` 执行 ``remove_variable``：针对“变量无法通过 DSL 数据流影响任何转换守卫，且没有可见抽象动作可能在 DSL 外使用它。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_UNREFERENCED_VAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_UNREFERENCED_VAR`` 的反例边界。
不要这样处理：针对“变量无法通过 DSL 数据流影响任何转换守卫，且没有可见抽象动作可能在 DSL 外使用它。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-unreferenced-var-maybe-abstract-zh:

I_UNREFERENCED_VAR_MAYBE_ABSTRACT
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_UNREFERENCED_VAR_MAYBE_ABSTRACT severity=info emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref I_UNREFERENCED_VAR_MAYBE_ABSTRACT var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_UNREFERENCED_VAR_MAYBE_ABSTRACT abstract_actions_in_scope type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_UNREFERENCED_VAR_MAYBE_ABSTRACT kind=inspect_json

**注册表事实。** 严重级别 ``info``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``variable_declaration``。

**含义。** 变量无法通过 DSL 数据流影响守卫，但至少一个可见抽象动作可能在 DSL 外使用它。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。变量无法通过 DSL 数据流影响守卫，但至少一个可见抽象动作可能在 DSL 外使用它。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``abstract_actions_in_scope``
     - ``list[str]``
     - 是
     - 字段含义：可能在 DSL 外访问变量的抽象动作拥有者。

.. diagnostics-example I_UNREFERENCED_VAR_MAYBE_ABSTRACT 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

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

**示例 2**\ （``boundary_only``）——针对 ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT`` 的修复方向。
典型修复是对 ``abstract_action`` 执行 ``inspect_abstract_action``：针对“变量无法通过 DSL 数据流影响守卫，但至少一个可见抽象动作可能在 DSL 外使用它。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_UNREFERENCED_VAR_MAYBE_ABSTRACT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT`` 的反例边界。
不要这样处理：针对“变量无法通过 DSL 数据流影响守卫，但至少一个可见抽象动作可能在 DSL 外使用它。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-unwritten-read-var-zh:

W_UNWRITTEN_READ_VAR
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNWRITTEN_READ_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_UNWRITTEN_READ_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNWRITTEN_READ_VAR read_states type=list[str] required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_UNWRITTEN_READ_VAR init_value type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_UNWRITTEN_READ_VAR kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``variable_declaration``。

**含义。** 变量被守卫或动作读取，但从未被生命周期动作或转换效果写入。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。变量被守卫或动作读取，但从未被生命周期动作或转换效果写入。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``read_states``
     - ``list[str]``
     - 是
     - 字段含义：读取变量的状态路径列表。
   * - ``init_value``
     - ``str``
     - 是
     - 字段含义：初始值源码文本。

.. diagnostics-example W_UNWRITTEN_READ_VAR 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [ready > 0];
   }

.. diagnostics-example W_UNWRITTEN_READ_VAR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_UNWRITTEN_READ_VAR`` 的修复方向。
典型修复是对 ``action_or_effect`` 执行 ``add_write``：针对“变量被守卫或动作读取，但从未被生命周期动作或转换效果写入。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_UNWRITTEN_READ_VAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_UNWRITTEN_READ_VAR`` 的反例边界。
不要这样处理：针对“变量被守卫或动作读取，但从未被生命周期动作或转换效果写入。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-write-only-var-zh:

W_WRITE_ONLY_VAR
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_WRITE_ONLY_VAR severity=warning emit_tier=static_pipeline capability=pure_static span_object=variable_declaration
.. diagnostics-ref W_WRITE_ONLY_VAR var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_WRITE_ONLY_VAR written_states type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_WRITE_ONLY_VAR kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``variable_declaration``。

**含义。** 变量被动作或效果写入，但从未被守卫、动作或转换效果读取。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。变量被动作或效果写入，但从未被守卫、动作或转换效果读取。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``written_states``
     - ``list[str]``
     - 是
     - 字段含义：写入变量的状态路径列表。

.. diagnostics-example W_WRITE_ONLY_VAR 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int counter = 0;
   state Root {
       state A { during { counter = 1; } }
       [*] -> A;
   }

.. diagnostics-example W_WRITE_ONLY_VAR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_WRITE_ONLY_VAR`` 的修复方向。
典型修复是对 ``guard_or_action`` 执行 ``add_read``：针对“变量被动作或效果写入，但从未被守卫、动作或转换效果读取。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_WRITE_ONLY_VAR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_WRITE_ONLY_VAR`` 的反例边界。
不要这样处理：针对“变量被动作或效果写入，但从未被守卫、动作或转换效果读取。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

数值和目标配置诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-literal-type-narrowing-zh:

W_LITERAL_TYPE_NARROWING
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_LITERAL_TYPE_NARROWING severity=warning emit_tier=static_pipeline capability=pure_static span_object=expression
.. diagnostics-ref W_LITERAL_TYPE_NARROWING var_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LITERAL_TYPE_NARROWING target_type type=str required=true enum=int item_enum=- exact_values=-
.. diagnostics-ref W_LITERAL_TYPE_NARROWING source_expr type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_LITERAL_TYPE_NARROWING kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``expression``。

**含义。** ``int`` 变量直接从浮点字面量初始化或赋值，生成代码可能发生静默收窄。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``int`` 变量直接从浮点字面量初始化或赋值，生成代码可能发生静默收窄。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``var_name``
     - ``str``
     - 是
     - 字段含义：相关变量名或变量标识。
   * - ``target_type``
     - ``str``
     - 是
     - 字段含义：目标变量声明类型。
   * - ``source_expr``
     - ``str``
     - 是
     - 字段含义：直接浮点字面量的源码文本。

.. diagnostics-example W_LITERAL_TYPE_NARROWING 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int truncated = 3.5;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_LITERAL_TYPE_NARROWING 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_LITERAL_TYPE_NARROWING`` 的修复方向。
典型修复是对 ``variable_definition`` 执行 ``change_type``：针对“``int`` 变量直接从浮点字面量初始化或赋值，生成代码可能发生静默收窄。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_LITERAL_TYPE_NARROWING 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_LITERAL_TYPE_NARROWING`` 的反例边界。
不要这样处理：针对“``int`` 变量直接从浮点字面量初始化或赋值，生成代码可能发生静默收窄。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-numeric-literal-out-of-target-range-zh:

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


.. diagnostics-boundary W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``expression``。

**含义。** 面向 C/C++ 系模板渲染的整数字面量超出默认有符号 64 位范围。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。面向 C/C++ 系模板渲染的整数字面量超出默认有符号 64 位范围。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``target_family``
     - ``str``
     - 是
     - 字段含义：拥有该风险的目标模板家族。
   * - ``target_templates``
     - ``list[str]``
     - 是
     - 字段含义：该目标档案覆盖的模板列表。
   * - ``runtime_note``
     - ``str``
     - 是
     - 字段含义：关于目标运行时差异的说明。
   * - ``context``
     - ``str``
     - 是
     - 字段含义：表达式出现的位置。
   * - ``statement_kind``
     - ``str``
     - 否
     - 字段含义：表达式所在语句形状。
   * - ``expr_text``
     - ``str``
     - 是
     - 字段含义：相关表达式的源码文本。
   * - ``literal_text``
     - ``str``
     - 是
     - 字段含义：应用一元符号后的整数字面量文本。
   * - ``target_bits``
     - ``int``
     - 是
     - 字段含义：目标整数宽度。
   * - ``signed``
     - ``bool``
     - 是
     - 字段含义：目标整数档案是否有符号。
   * - ``min_value_text``
     - ``str``
     - 是
     - 字段含义：目标范围最小值的十进制文本。
   * - ``max_value_text``
     - ``str``
     - 是
     - 字段含义：目标范围最大值的十进制文本。
   * - ``var_name``
     - ``str``
     - 否
     - 字段含义：相关变量名或变量标识。

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int too_large = 9223372036854775808;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` 的修复方向。
典型修复是对 ``expression`` 执行 ``reduce_literal``：针对“面向 C/C++ 系模板渲染的整数字面量超出默认有符号 64 位范围。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` 的反例边界。
不要这样处理：针对“面向 C/C++ 系模板渲染的整数字面量超出默认有符号 64 位范围。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-numeric-constant-division-by-zero-zh:

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


.. diagnostics-boundary W_NUMERIC_CONSTANT_DIVISION_BY_ZERO kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``const_fold``；源码对象 ``expression``。

**含义。** ``/`` 或 ``%`` 运算右侧可由轻量常量折叠判定为零。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。``/`` 或 ``%`` 运算右侧可由轻量常量折叠判定为零。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``target_family``
     - ``str``
     - 是
     - 字段含义：拥有该风险的目标模板家族。
   * - ``target_templates``
     - ``list[str]``
     - 是
     - 字段含义：该目标档案覆盖的模板列表。
   * - ``runtime_note``
     - ``str``
     - 是
     - 字段含义：关于目标运行时差异的说明。
   * - ``context``
     - ``str``
     - 是
     - 字段含义：表达式出现的位置。
   * - ``statement_kind``
     - ``str``
     - 否
     - 字段含义：表达式所在语句形状。
   * - ``expr_text``
     - ``str``
     - 是
     - 字段含义：相关表达式的源码文本。
   * - ``operator``
     - ``str``
     - 是
     - 字段含义：相关运算符。
   * - ``rhs_text``
     - ``str``
     - 是
     - 字段含义：折叠后为零的右侧表达式文本。

.. diagnostics-example W_NUMERIC_CONSTANT_DIVISION_BY_ZERO 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

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

**示例 2**\ （``boundary_only``）——针对 ``W_NUMERIC_CONSTANT_DIVISION_BY_ZERO`` 的修复方向。
典型修复是对 ``expression`` 执行 ``fix_denominator``：针对“``/`` 或 ``%`` 运算右侧可由轻量常量折叠判定为零。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_NUMERIC_CONSTANT_DIVISION_BY_ZERO 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_NUMERIC_CONSTANT_DIVISION_BY_ZERO`` 的反例边界。
不要这样处理：针对“``/`` 或 ``%`` 运算右侧可由轻量常量折叠判定为零。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-numeric-shift-count-out-of-target-range-zh:

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


.. diagnostics-boundary W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``const_fold``；源码对象 ``expression``。

**含义。** 移位次数折叠为负数，或不小于默认 C/C++ 目标整数宽度。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。移位次数折叠为负数，或不小于默认 C/C++ 目标整数宽度。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``target_family``
     - ``str``
     - 是
     - 字段含义：拥有该风险的目标模板家族。
   * - ``target_templates``
     - ``list[str]``
     - 是
     - 字段含义：该目标档案覆盖的模板列表。
   * - ``runtime_note``
     - ``str``
     - 是
     - 字段含义：关于目标运行时差异的说明。
   * - ``context``
     - ``str``
     - 是
     - 字段含义：表达式出现的位置。
   * - ``statement_kind``
     - ``str``
     - 否
     - 字段含义：表达式所在语句形状。
   * - ``expr_text``
     - ``str``
     - 是
     - 字段含义：相关表达式的源码文本。
   * - ``operator``
     - ``str``
     - 是
     - 字段含义：相关运算符。
   * - ``target_bits``
     - ``int``
     - 是
     - 字段含义：目标整数宽度。
   * - ``shift_count_text``
     - ``str``
     - 是
     - 字段含义：折叠后的移位次数文本。

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int flags = 1;
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [(flags << 64) != 0];
   }

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE`` 的修复方向。
典型修复是对 ``expression`` 执行 ``bound_shift_count``：针对“移位次数折叠为负数，或不小于默认 C/C++ 目标整数宽度。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE`` 的反例边界。
不要这样处理：针对“移位次数折叠为负数，或不小于默认 C/C++ 目标整数宽度。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-numeric-float-bitwise-zh:

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


.. diagnostics-boundary W_NUMERIC_FLOAT_BITWISE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``expression``。

**含义。** 已知为 ``float`` 的值参与了 C/C++ 整数运算档案里的位运算或移位运算。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。已知为 ``float`` 的值参与了 C/C++ 整数运算档案里的位运算或移位运算。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``target_family``
     - ``str``
     - 是
     - 字段含义：拥有该风险的目标模板家族。
   * - ``target_templates``
     - ``list[str]``
     - 是
     - 字段含义：该目标档案覆盖的模板列表。
   * - ``runtime_note``
     - ``str``
     - 是
     - 字段含义：关于目标运行时差异的说明。
   * - ``context``
     - ``str``
     - 是
     - 字段含义：表达式出现的位置。
   * - ``statement_kind``
     - ``str``
     - 否
     - 字段含义：表达式所在语句形状。
   * - ``expr_text``
     - ``str``
     - 是
     - 字段含义：相关表达式的源码文本。
   * - ``operator``
     - ``str``
     - 是
     - 字段含义：相关运算符。
   * - ``operand_types``
     - ``list[str]``
     - 是
     - 字段含义：操作数类型标签列表。
   * - ``operand_type_sources``
     - ``list[str]``
     - 是
     - 字段含义：操作数类型标签的证据来源。

.. diagnostics-example W_NUMERIC_FLOAT_BITWISE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

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

**示例 2**\ （``boundary_only``）——针对 ``W_NUMERIC_FLOAT_BITWISE`` 的修复方向。
典型修复是对 ``expression`` 执行 ``use_integer_operand``：针对“已知为 ``float`` 的值参与了 C/C++ 整数运算档案里的位运算或移位运算。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_NUMERIC_FLOAT_BITWISE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_NUMERIC_FLOAT_BITWISE`` 的反例边界。
不要这样处理：针对“已知为 ``float`` 的值参与了 C/C++ 整数运算档案里的位运算或移位运算。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

拓扑和设计健康诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-unreachable-state-zh:

W_UNREACHABLE_STATE
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_UNREACHABLE_STATE severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_UNREACHABLE_STATE state_path type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_UNREACHABLE_STATE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 从根入口路径出发，无法通过普通或强制转换到达某个状态。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。从根入口路径出发，无法通过普通或强制转换到达某个状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。

.. diagnostics-example W_UNREACHABLE_STATE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state Idle;
       state Orphan;
       [*] -> Idle;
   }

.. diagnostics-example W_UNREACHABLE_STATE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_UNREACHABLE_STATE`` 的修复方向。
典型修复是对 ``state`` 执行 ``add_inbound_transition``：针对“从根入口路径出发，无法通过普通或强制转换到达某个状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_UNREACHABLE_STATE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_UNREACHABLE_STATE`` 的反例边界。
不要这样处理：针对“从根入口路径出发，无法通过普通或强制转换到达某个状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-deadlock-leaf-zh:

W_DEADLOCK_LEAF
^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEADLOCK_LEAF severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_DEADLOCK_LEAF state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF parent_path type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF reason type=str required=true enum=no_outgoing_transition item_enum=- exact_values=-
.. diagnostics-ref W_DEADLOCK_LEAF suggested_fix type=dict required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_DEADLOCK_LEAF kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 非伪叶状态没有任何出边转换，进入后无法离开。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。非伪叶状态没有任何出边转换，进入后无法离开。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``state_path``
     - ``str``
     - 是
     - 字段含义：相关状态的点分路径。
   * - ``parent_path``
     - ``str``
     - 否
     - 字段含义：父状态的点分路径。
   * - ``reason``
     - ``str``
     - 是
     - 字段含义：原因分类标签。
   * - ``suggested_fix``
     - ``dict``
     - 否
     - 字段含义：可选的结构化快速修复载荷。

.. diagnostics-example W_DEADLOCK_LEAF 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       [*] -> A;
   }

.. diagnostics-example W_DEADLOCK_LEAF 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_DEADLOCK_LEAF`` 的修复方向。
典型修复是对 ``state`` 执行 ``add_transition``：针对“非伪叶状态没有任何出边转换，进入后无法离开。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_DEADLOCK_LEAF 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_DEADLOCK_LEAF`` 的反例边界。
不要这样处理：针对“非伪叶状态没有任何出边转换，进入后无法离开。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-high-var-to-leaf-ratio-zh:

W_HIGH_VAR_TO_LEAF_RATIO
^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_HIGH_VAR_TO_LEAF_RATIO severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO n_vars type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO n_leaf_states type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO actual type=number required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_HIGH_VAR_TO_LEAF_RATIO threshold type=number required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_HIGH_VAR_TO_LEAF_RATIO kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``composite_block``。

**含义。** 变量数量相对于非伪叶状态数量偏高，常见于标志位膨胀或职责分配不清。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。变量数量相对于非伪叶状态数量偏高，常见于标志位膨胀或职责分配不清。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``n_vars``
     - ``int``
     - 是
     - 字段含义：文件顶层变量定义数量。
   * - ``n_leaf_states``
     - ``int``
     - 是
     - 字段含义：非伪叶状态数量。
   * - ``actual``
     - ``number``
     - 是
     - 字段含义：实际观测到的类别、数量或度量值。
   * - ``threshold``
     - ``number``
     - 是
     - 字段含义：本次检查使用的阈值。

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int a = 0;
   def int b = 0;
   def int c = 0;
   state Root { state A; [*] -> A; }

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_HIGH_VAR_TO_LEAF_RATIO`` 的修复方向。
典型修复是对 ``variable_definitions`` 执行 ``audit_variables``：针对“变量数量相对于非伪叶状态数量偏高，常见于标志位膨胀或职责分配不清。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_HIGH_VAR_TO_LEAF_RATIO 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_HIGH_VAR_TO_LEAF_RATIO`` 的反例边界。
不要这样处理：针对“变量数量相对于非伪叶状态数量偏高，常见于标志位膨胀或职责分配不清。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-deep-hierarchy-zh:

W_DEEP_HIERARCHY
^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEEP_HIERARCHY severity=warning emit_tier=static_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_DEEP_HIERARCHY max_depth type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY deepest_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY actual type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEEP_HIERARCHY threshold type=int required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_DEEP_HIERARCHY kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 状态层级深度超过配置阈值。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。状态层级深度超过配置阈值。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``max_depth``
     - ``int``
     - 是
     - 字段含义：观察到或配置的最大层级深度。
   * - ``deepest_path``
     - ``str``
     - 是
     - 字段含义：触发深度诊断的一个最深状态路径。
   * - ``actual``
     - ``int``
     - 是
     - 字段含义：实际观测到的类别、数量或度量值。
   * - ``threshold``
     - ``int``
     - 是
     - 字段含义：本次检查使用的阈值。

.. diagnostics-example W_DEEP_HIERARCHY 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root { state A { state B { state C; [*] -> C; } [*] -> B; } [*] -> A; }

.. diagnostics-example W_DEEP_HIERARCHY 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_DEEP_HIERARCHY`` 的修复方向。
典型修复是对 ``state_tree`` 执行 ``flatten_hierarchy``：针对“状态层级深度超过配置阈值。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_DEEP_HIERARCHY 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_DEEP_HIERARCHY`` 的反例边界。
不要这样处理：针对“状态层级深度超过配置阈值。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-large-composite-zh:

W_LARGE_COMPOSITE
^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_LARGE_COMPOSITE severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_LARGE_COMPOSITE composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE n_children type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE actual type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_LARGE_COMPOSITE threshold type=int required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_LARGE_COMPOSITE kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``composite_block``。

**含义。** 组合状态的直接子状态数量超过配置阈值。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合状态的直接子状态数量超过配置阈值。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``composite_path``
     - ``str``
     - 是
     - 字段含义：相关组合状态的点分路径。
   * - ``n_children``
     - ``int``
     - 是
     - 字段含义：直接子状态数量。
   * - ``actual``
     - ``int``
     - 是
     - 字段含义：实际观测到的类别、数量或度量值。
   * - ``threshold``
     - ``int``
     - 是
     - 字段含义：本次检查使用的阈值。

.. diagnostics-example W_LARGE_COMPOSITE 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root { state A; state B; state C; [*] -> A; }

.. diagnostics-example W_LARGE_COMPOSITE 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_LARGE_COMPOSITE`` 的修复方向。
典型修复是对 ``composite_state`` 执行 ``group_children``：针对“组合状态的直接子状态数量超过配置阈值。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_LARGE_COMPOSITE 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_LARGE_COMPOSITE`` 的反例边界。
不要这样处理：针对“组合状态的直接子状态数量超过配置阈值。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-nontrivial-scc-zh:

I_NONTRIVIAL_SCC
^^^^^^^^^^^^^^^^

.. diagnostics-meta I_NONTRIVIAL_SCC severity=info emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_NONTRIVIAL_SCC algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_NONTRIVIAL_SCC scc type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_NONTRIVIAL_SCC kind=verify_smt_linear

**注册表事实。** 严重级别 ``info``；发射层级 ``verify_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 守卫无关的叶级拓扑图中存在非平凡强连通分量。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。守卫无关的叶级拓扑图中存在非平凡强连通分量。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``representative_state_path``
     - ``str``
     - 是
     - 字段含义：报告对象中的一个代表状态路径。
   * - ``scc``
     - ``list[str]``
     - 是
     - 字段含义：强连通分量或陷阱循环路径列表。

.. diagnostics-example I_NONTRIVIAL_SCC 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   state System {
       state A;
       state B;
       [*] -> A;
       A -> B;
       B -> A;
   }

.. diagnostics-example I_NONTRIVIAL_SCC 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_NONTRIVIAL_SCC`` 的修复方向。
典型修复是对 ``topology`` 执行 ``review_cycle``：针对“守卫无关的叶级拓扑图中存在非平凡强连通分量。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_NONTRIVIAL_SCC 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_NONTRIVIAL_SCC`` 的反例边界。
不要这样处理：针对“守卫无关的叶级拓扑图中存在非平凡强连通分量。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-topological-noexit-zh:

W_TOPOLOGICAL_NOEXIT
^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_TOPOLOGICAL_NOEXIT severity=warning emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT counterexample_kind type=str required=true enum=trap_cycle|deadlock item_enum=- exact_values=-
.. diagnostics-ref W_TOPOLOGICAL_NOEXIT scc type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_TOPOLOGICAL_NOEXIT kind=verify_smt_linear

**注册表事实。** 严重级别 ``warning``；发射层级 ``verify_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 根可达的叶状态或循环没有守卫无关路径通向根退出汇点。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。根可达的叶状态或循环没有守卫无关路径通向根退出汇点。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``representative_state_path``
     - ``str``
     - 是
     - 字段含义：报告对象中的一个代表状态路径。
   * - ``counterexample_kind``
     - ``str``
     - 是
     - 字段含义：拓扑反例形状。
   * - ``scc``
     - ``list[str]``
     - 是
     - 字段含义：强连通分量或陷阱循环路径列表。

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   state System {
       state A;
       state B;
       [*] -> A;
       A -> B;
   }

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_TOPOLOGICAL_NOEXIT`` 的修复方向。
典型修复是对 ``topology`` 执行 ``add_exit_transition``：针对“根可达的叶状态或循环没有守卫无关路径通向根退出汇点。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_TOPOLOGICAL_NOEXIT 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_TOPOLOGICAL_NOEXIT`` 的反例边界。
不要这样处理：针对“根可达的叶状态或循环没有守卫无关路径通向根退出汇点。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-i-topological-non-terminating-zh:

I_TOPOLOGICAL_NON_TERMINATING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta I_TOPOLOGICAL_NON_TERMINATING severity=info emit_tier=verify_pipeline capability=pure_static span_object=state_identifier
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING algorithm_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING verification_scope type=str required=true enum=topological_only item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING representative_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref I_TOPOLOGICAL_NON_TERMINATING counterexample_path type=list[str] required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary I_TOPOLOGICAL_NON_TERMINATING kind=verify_smt_linear

**注册表事实。** 严重级别 ``info``；发射层级 ``verify_pipeline``；能力层级 ``pure_static``；源码对象 ``state_identifier``。

**含义。** 拓扑结构不能保证所有根可达执行最终到达根终止点。

**面向 LLM 的修复摘要。** 这是非阻塞的信息性观察。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。拓扑结构不能保证所有根可达执行最终到达根终止点。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``algorithm_name``
     - ``str``
     - 是
     - 字段含义：产生原始发现的验证算法名称。
   * - ``verification_scope``
     - ``str``
     - 是
     - 字段含义：验证发现所属的作用域。
   * - ``representative_state_path``
     - ``str``
     - 是
     - 字段含义：报告对象中的一个代表状态路径。
   * - ``counterexample_path``
     - ``list[str]``
     - 是
     - 字段含义：拓扑验证报告的代表性循环或死锁路径。

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 1 verify_opt_in

**示例 1**\ （``verify_opt_in``）——复现边界。
这个诊断需要显式开启验证集成。复现时应使用 ``pyfcstm inspect -i <file> --enable-verify --max-complexity-tier smt_linear --format json``；默认结构验证预算不会运行发射它的求解器局部算法。

.. code-block:: fcstm

   state System {
       state A;
       [*] -> A;
       A -> A;
       A -> [*];
   }

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``I_TOPOLOGICAL_NON_TERMINATING`` 的修复方向。
典型修复是对 ``topology`` 执行 ``review_nontermination``：针对“拓扑结构不能保证所有根可达执行最终到达根终止点。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example I_TOPOLOGICAL_NON_TERMINATING 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``I_TOPOLOGICAL_NON_TERMINATING`` 的反例边界。
不要这样处理：针对“拓扑结构不能保证所有根可达执行最终到达根终止点。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

兼容边界和其他诊断
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _diag-code-w-initial-unconditional-missing-zh:

W_INITIAL_UNCONDITIONAL_MISSING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_INITIAL_UNCONDITIONAL_MISSING severity=warning emit_tier=static_pipeline capability=pure_static span_object=composite_block
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING composite_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING existing_conditional_count type=int required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING first_child_name type=str required=false enum=- item_enum=- exact_values=-
.. diagnostics-ref W_INITIAL_UNCONDITIONAL_MISSING suggested_fix type=dict required=false enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_INITIAL_UNCONDITIONAL_MISSING kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``composite_block``。

**含义。** 组合状态没有无条件 ``[*] -> child`` 入口转换；带守卫或事件的入口转换不能保证初始子状态。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。组合状态没有无条件 ``[*] -> child`` 入口转换；带守卫或事件的入口转换不能保证初始子状态。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``composite_path``
     - ``str``
     - 是
     - 字段含义：相关组合状态的点分路径。
   * - ``existing_conditional_count``
     - ``int``
     - 是
     - 字段含义：已有条件入口转换数量。
   * - ``first_child_name``
     - ``str``
     - 否
     - 字段含义：用于插入默认入口转换的第一个非伪子状态名。
   * - ``suggested_fix``
     - ``dict``
     - 否
     - 字段含义：可选的结构化快速修复载荷。

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   def int ready = 0;
   state Root {
       state A;
       [*] -> A : if [ready > 0];
   }

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_INITIAL_UNCONDITIONAL_MISSING`` 的修复方向。
典型修复是对 ``composite_state`` 执行 ``add_unconditional_initial``：针对“组合状态没有无条件 ``[*] -> child`` 入口转换；带守卫或事件的入口转换不能保证初始子状态。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_INITIAL_UNCONDITIONAL_MISSING 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_INITIAL_UNCONDITIONAL_MISSING`` 的反例边界。
不要这样处理：针对“组合状态没有无条件 ``[*] -> child`` 入口转换；带守卫或事件的入口转换不能保证初始子状态。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-dead-named-action-zh:

W_DEAD_NAMED_ACTION
^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_DEAD_NAMED_ACTION severity=warning emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref W_DEAD_NAMED_ACTION function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_DEAD_NAMED_ACTION defined_in type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_DEAD_NAMED_ACTION kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``named_action_declaration``。

**含义。** 命名动作位于不可达状态内，并且没有被任何可达动作引用。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。命名动作位于不可达状态内，并且没有被任何可达动作引用。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``function_name``
     - ``str``
     - 是
     - 字段含义：相关命名动作名称。
   * - ``defined_in``
     - ``str``
     - 是
     - 字段含义：动作定义所在状态路径。

.. diagnostics-example W_DEAD_NAMED_ACTION 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       state A;
       state B { enter Cleanup {} }
       [*] -> A;
   }

.. diagnostics-example W_DEAD_NAMED_ACTION 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_DEAD_NAMED_ACTION`` 的修复方向。
典型修复是对 ``state`` 执行 ``connect_state``：针对“命名动作位于不可达状态内，并且没有被任何可达动作引用。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_DEAD_NAMED_ACTION 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_DEAD_NAMED_ACTION`` 的反例边界。
不要这样处理：针对“命名动作位于不可达状态内，并且没有被任何可达动作引用。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。

.. _diag-code-w-named-action-shadows-ancestor-zh:

W_NAMED_ACTION_SHADOWS_ANCESTOR
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. diagnostics-meta W_NAMED_ACTION_SHADOWS_ANCESTOR severity=warning emit_tier=static_pipeline capability=pure_static span_object=named_action_declaration
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR function_name type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR inner_state_path type=str required=true enum=- item_enum=- exact_values=-
.. diagnostics-ref W_NAMED_ACTION_SHADOWS_ANCESTOR outer_state_path type=str required=true enum=- item_enum=- exact_values=-


.. diagnostics-boundary W_NAMED_ACTION_SHADOWS_ANCESTOR kind=inspect_json

**注册表事实。** 严重级别 ``warning``；发射层级 ``static_pipeline``；能力层级 ``pure_static``；源码对象 ``named_action_declaration``。

**含义。** 命名生命周期动作复用了祖先作用域里的命名动作名称。

**面向 LLM 的修复摘要。** 这是提示设计风险或可疑结构的警告。 修复时先根据 ``refs`` 定位对象，再做最小、可解释、保留模型意图的修改。命名生命周期动作复用了祖先作用域里的命名动作名称。

.. list-table:: ``refs`` 字段
   :header-rows: 1
   :widths: 22 16 14 48

   * - 字段
     - 类型
     - 必填
     - 含义
   * - ``function_name``
     - ``str``
     - 是
     - 字段含义：相关命名动作名称。
   * - ``inner_state_path``
     - ``str``
     - 是
     - 字段含义：包含遮蔽动作的内部状态路径。
   * - ``outer_state_path``
     - ``str``
     - 是
     - 字段含义：包含被遮蔽动作的祖先状态路径。

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 1 repro_cli

**示例 1**\ （``repro_cli``）——复现边界。
这个诊断可以出现在成功构建模型后的检查报告中。可用 ``pyfcstm inspect -i <file> --format json`` 复现，并读取 ``diagnostics[]`` 数组。

.. code-block:: fcstm

   state Root {
       enter Sync { }
       state Child { enter Sync { } }
       [*] -> Child;
   }

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 2 boundary_only

**示例 2**\ （``boundary_only``）——针对 ``W_NAMED_ACTION_SHADOWS_ANCESTOR`` 的修复方向。
典型修复是对 ``named_action`` 执行 ``rename_inner_action``：针对“命名生命周期动作复用了祖先作用域里的命名动作名称。”，结合上方 ``refs`` 定位具体对象，做最小语义保持修改；如果无法确认意图，先补充模型上下文或保留诊断。

.. diagnostics-example W_NAMED_ACTION_SHADOWS_ANCESTOR 3 boundary_only

**示例 3**\ （``boundary_only``）——针对 ``W_NAMED_ACTION_SHADOWS_ANCESTOR`` 的反例边界。
不要这样处理：针对“命名生命周期动作复用了祖先作用域里的命名动作名称。”，不要只为消除诊断而做语义不明的删除、重命名、阈值放宽或占位写法；必须先确认真实控制意图。
