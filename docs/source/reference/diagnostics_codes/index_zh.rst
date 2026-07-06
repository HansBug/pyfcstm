.. _sec-reference-diagnostics-codes-zh:

诊断码参考
==========

Diagnostic code 是 inspect 输出、CI 过滤、IDE 集成和 LLM repair prompt 使用的稳定标识。完整 registry 位于 ``pyfcstm.diagnostics.CODE_REGISTRY``；本页解释编写 DSL 时最常见的用户侧 code。

如何阅读 inspect diagnostic
---------------------------

需要机器可读修复上下文时运行 JSON inspect：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_duplicate_event.fcstm --format json

每个 diagnostic 包含：

* ``code``：稳定标识，例如 ``W_COMBO_DUPLICATE_EVENT``；
* ``severity``：``error``、``warning`` 或 ``info``；
* ``message``：简短人工说明；
* ``span``：可用时给出 source location；
* ``refs``：结构化字段，例如 ``event_name`` 或 ``guard_vars``；
* 可选 suggested-fix payload，供工具生成修复建议。

Error 会阻塞 model construction。Warning 和 info 不一定阻塞 simulation 或 generation，但仍应阅读，因为它们经常指出 target profile risk、可疑 guard 或可能的 typo。

常见代码
--------

.. list-table:: 常见 inspect diagnostics
   :header-rows: 1
   :widths: 28 12 60

   * - Code
     - Severity
     - 含义与常见修复
   * - ``W_DURING_CONST_ASSIGN``
     - warning
     - Concrete ``during`` action 每个 cycle 都赋同一个 literal-only numeric value。一次性初始化应移到 ``enter``，或者让 expression 依赖 runtime state。
   * - ``W_COMBO_DUPLICATE_EVENT``
     - warning
     - Combo trigger 重复同一个 canonical event term。检查第二个 term 是否 typo；只有需要显式 two-hop relay 时才保留。
   * - ``W_COMBO_GUARD_PREFIX_IMPLIED``
     - warning
     - 前面的 side-effect-free combo guards 蕴含后面的 guard term。移除冗余 guard，或改写成真正想表达的条件。
   * - ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``
     - warning
     - ``pseudo state __combo_*`` node 含 lifecycle 或 aspect action。把业务行为移到 authored state，或把 pseudo state 改名到 reserved namespace 之外。
   * - ``W_COMBO_RESERVED_PREFIX_STATE_KIND``
     - warning
     - Normal leaf 或 composite state 使用 reserved combo relay prefix。应重命名 state，不要为了消除 warning 把业务 state 改成 pseudo。
   * - ``W_GUARD_VARS_NEVER_CHANGE``
     - warning
     - Guard 只读取从不被 action/effect 修改的变量。添加缺失的 write，或确认 initial-value-only 行为后简化 guard。
   * - ``W_UNWRITTEN_READ_VAR``
     - warning
     - Operation 在同一 block 中读到了尚未被 write 定义的变量。应提前初始化，或调整 block 顺序让 write 先可见。
   * - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - warning
     - Integer literal 超出默认 C-family generated integer range。这是 C/C++ deployment-profile warning，不是 Python runtime overflow 结论。
   * - ``W_DEADLOCK_LEAF``
     - warning
     - 非 pseudo leaf state 没有 outgoing transition。如果它不应 terminal，应添加 exit 或 outgoing transition。
   * - ``W_UNREFERENCED_VAR``
     - warning
     - 变量无法通过 DSL data flow 影响任何 transition guard。除非外部 abstract hook 使用它，否则应移除或接入模型行为。
   * - ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT``
     - info
     - 变量未被 DSL data flow 使用，但 visible abstract actions 可能在外部使用它。
   * - ``I_TRANSITION_NEVER_EVENT_TRIGGERED``
     - info
     - Event-triggered transition 没有被 checked event path 触发。若它由外部 event 触发可保留，否则应移除或重命名 stale event。

可运行 diagnostic 示例
----------------------

下面这些 checked files 故意展示常见 warning。它们是有效 DSL 文件，不是破坏 parser 的 fixture。

.. list-table:: Diagnostic examples
   :header-rows: 1
   :widths: 30 32 38

   * - File
     - 关键输出摘录
     - 学习点
   * - ``combo_duplicate_event.fcstm``
     - ``warning: W_COMBO_DUPLICATE_EVENT``
     - Inspect 通过 ``refs.term_span`` 和 ``refs.first_term_span`` 指向重复 combo term。
   * - ``guard_vars_never_change.fcstm``
     - ``warning: W_UNWRITTEN_READ_VAR`` + ``warning: W_GUARD_VARS_NEVER_CHANGE`` + ``info: I_TRANSITION_NEVER_EVENT_TRIGGERED``
     - 只读取初始值的 guard 需要修复，或明确记录为 intentional；额外 read/write 和 fallthrough diagnostics 是这个紧凑 fixture 的预期输出。
   * - ``during_const_assign.fcstm``
     - ``warning: W_DURING_CONST_ASSIGN``
     - ``during`` 中反复赋常量通常应移到 ``enter``。
   * - ``numeric_target_range.fcstm``
     - ``warning: W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - Numeric target warning 只限定到 C-family generated runtimes。

示例命令：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/numeric_target_range.fcstm --format human --color never

预期摘录：

.. code-block:: text

   W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE
   C/C++ default deployment profile risk: integer literal 9223372036854775808 is outside the PYFCSTM_GENERATED_INT64 range

.. _diag-c-cpp-risk-wording-zh:

C/C++ target-profile 范围
--------------------------------

``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` 和相关 numeric deployment warning 关注 C-family generated runtimes。它们适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 部署审查，不代表 Python generated runtime 也有同样 overflow 行为。如果未来存在 Python-specific diagnostic，必须由对应 diagnostic 明确说明；不能从 C/C++ profile wording 推断 Python risk。

.. _diag-combo-relay-scope-zh:

Combo relay 范围
----------------

Combo relay pseudo-state warning 关注 generated relay 的纯粹性和保留命名。它们不表示 ``during before`` aspect actions 会在 combo relay pseudo states 内执行。Relay pseudo state 应保持纯 routing helper；可观察业务行为应放在 authored states 或 transition effects 上。
