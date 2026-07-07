.. _sec-reference-diagnostics-codes-zh:

诊断码参考
==========

诊断码（diagnostic code）是 ``pyfcstm inspect``、CI 过滤、IDE 集成和 LLM 修复提示使用的稳定标识。权威注册表是加载后的
``pyfcstm.diagnostics.codes.CODE_REGISTRY`` 对象。原始 ``codes.yaml`` 条目可能省略 ``emit_tier`` 或 ``capability``；加载器会把这些缺省值补成
``static_pipeline`` 和 ``pure_static``。

本页是参考资料，不是教程。当你已经从检查输出中拿到 ``code`` 值，并需要确认它的含义、稳定字段、发射路径、修复方向或边界时，应该查本页。

如何阅读一个诊断
----------------

一个诊断对象会把稳定标识、源码位置和修复上下文放在一起：

.. list-table:: 诊断对象字段
   :header-rows: 1
   :widths: 22 78

   * - 字段
     - 含义
   * - ``code``
     - 稳定标识，例如 ``W_COMBO_DUPLICATE_EVENT``。
   * - ``severity``
     - ``error`` 会阻塞模型构建；``warning`` 指出有风险或可疑的设计；``info`` 是非阻塞观察。
   * - ``message``
     - 面向人的简短说明。
   * - ``span``
     - 分析器能够定位具体对象时给出的源码范围。
   * - ``refs``
     - 工具和 LLM 修复提示使用的结构化载荷。下面每个诊断码都会列出预期字段。
   * - ``suggested_fix``
     - 当注册表能描述安全局部编辑形状时提供的可选编辑元数据。

发射层级
--------

.. list-table:: 发射层级
   :header-rows: 1
   :widths: 24 76

   * - 层级
     - 含义
   * - ``static_pipeline``
     - 默认静态检查或模型诊断路径会产生。
   * - ``verify_pipeline``
     - 只有运行有界且允许进入检查的验证算法时才会产生，通常需要 ``--enable-verify``。
   * - ``lookup_api``
     - 由显式解析 API 产生，不属于默认静态检查输出。
   * - ``partial_static_pipeline``
     - 注册表契约已经存在，但当前不是每个前端或后端都会发射。
   * - ``catalog_only``
     - 只保留兼容契约；当前正常 pyfcstm 路径不应发射。

示例类型
--------

下面每个诊断码至少有三个可见示例或边界示例。源码中还带有隐藏的 ``diagnostics-example`` 标记，供
``python tools/check_diagnostics_reference_docs.py --check`` 检查覆盖率。

.. list-table:: 示例类型
   :header-rows: 1
   :widths: 24 76

   * - 类型
     - 含义
   * - ``repro_cli``
     - 期望可通过当前命令行或模型构建路径复现。
   * - ``repro_api``
     - 期望可通过显式 Python API 调用复现。
   * - ``verify_opt_in``
     - 需要可选验证集成，并可能受求解器策略或超时影响。
   * - ``boundary_only``
     - 说明修复方向或反例边界，不代表单独的命令行触发路径。
   * - ``compatibility_only``
     - 说明历史或跨版本行为；当前正常路径不应发射。

机器覆盖检查
------------

编辑本页或诊断注册表后，运行这个仓库本地维护检查：

.. code-block:: bash

   python tools/check_diagnostics_reference_docs.py --check

该检查会验证诊断码集合、严重级别、发射层级、能力层级、源码对象、``refs`` 字段、双语覆盖和每个诊断码的示例标记数量。它不证明示例在语义上真的不趋同；PR review 仍需要人工抽样。

.. include:: _code_catalog_zh.rst.inc
