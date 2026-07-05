.. _sec-reference-diagnostics-codes-zh:

诊断码参考
==========

诊断码是 inspect 输出、CI 过滤和 LLM repair prompt 使用的稳定标识。本页列出用户侧 inspect workflow 中最常用的代码；完整 registry 位于 ``pyfcstm.diagnostics.CODE_REGISTRY``。

常见代码
--------

.. list-table:: 常见 inspect diagnostics
   :header-rows: 1

   * - 代码
     - 严重级别
     - 含义
   * - ``W_DURING_CONST_ASSIGN``
     - warning
     - 具体 ``during`` 动作每个 cycle 都赋同一个 literal-only 数值。
   * - ``W_COMBO_DUPLICATE_EVENT``
     - warning
     - combo trigger 重复同一个 canonical event term。
   * - ``W_COMBO_GUARD_PREFIX_IMPLIED``
     - warning
     - 前面的 side-effect-free combo guards 蕴含后面的 guard term。
   * - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - warning
     - 整数字面量超出默认 C-family 生成整数范围。
   * - ``W_DEADLOCK_LEAF``
     - warning
     - 非伪叶状态没有 outgoing transition。
   * - ``W_UNREFERENCED_VAR``
     - warning
     - 变量无法通过 DSL data flow 影响任何 transition guard。
   * - ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT``
     - info
     - 变量未被 DSL data flow 使用，但可见 abstract actions 可能在外部使用它。
   * - ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``
     - warning
     - combo relay pseudo state 含 lifecycle 或 aspect actions，因此不是纯 relay。
   * - ``W_COMBO_RESERVED_PREFIX_STATE_KIND``
     - warning
     - 非伪状态使用了保留的 combo relay 前缀。

.. _diag-c-cpp-risk-wording-zh:

C/C++ target-profile 范围
--------------------------------

``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` 和相关数值部署 warning 关注 C-family generated runtimes。它们适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 部署审查，不代表 Python generated runtime 也有同样 overflow 行为。

.. _diag-combo-relay-scope-zh:

Combo relay 范围
----------------

Combo relay pseudo-state warning 关注生成 relay 的纯粹性和保留命名。它们不表示 ``during before`` aspect actions 会在 combo relay pseudo states 内部执行。
