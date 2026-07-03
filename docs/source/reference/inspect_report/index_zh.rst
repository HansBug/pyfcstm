.. _sec-reference-inspect-report-zh:

Inspect 报告参考
================

``pyfcstm inspect`` 默认输出 human 文本；设置 ``--format`` 后输出结构化内容。

格式
----

.. list-table:: Inspect 格式
   :header-rows: 1

   * - 格式
     - 目标消费者
     - 说明
   * - ``human``
     - 阅读终端输出的人。
     - 默认格式；包含源码摘录和可选 ANSI color。
   * - ``json``
     - CI、编辑器和程序化集成。
     - 完整报告，匹配 model inspect payload。
   * - ``llm-json``
     - 偏好结构化数据的 LLM repair loop。
     - 稳定 schema ``pyfcstm.inspect.llm.v1``，包含摘要化修复字段。
   * - ``llm-md``
     - LLM prompt 和 issue comment。
     - 同一 LLM-oriented repair contract 的 Markdown 版本。

JSON 摘要字段
-------------

完整 JSON 报告包含模型身份、指标、派生图数据、combo provenance 和 diagnostics。真实 demo 当前报告：

.. literalinclude:: ../../tutorials/inspect/inspect_formats.demo.sh.txt
   :language: text
   :lines: 1-8

Diagnostic 对象 key
-------------------

默认 JSON diagnostic 对象当前暴露这些顶层 key：

.. list-table:: Diagnostic 对象 key
   :header-rows: 1

   * - Key
     - 含义
   * - ``code``
     - 稳定诊断码，例如 ``W_COMBO_DUPLICATE_EVENT``。
   * - ``severity``
     - ``error``、``warning`` 或 ``info``。
   * - ``message``
     - 人类可读诊断消息。
   * - ``span``
     - 可用时的源码位置。
   * - ``refs``
     - code-specific 结构化引用和修复提示。

有些诊断会把建议编辑放在 ``refs.suggested_fix`` 中。它不是 diagnostic 顶层字段。同理，``for_llm`` 是用于渲染 LLM 格式的 registry metadata，不是 ``--format json`` 直接输出的字段。

LLM report 字段
---------------

LLM 格式暴露 ``summary``、``recommended_actions``、``do_not`` 和 ``repair_guidance`` 等面向修复的字段：

.. literalinclude:: ../../tutorials/inspect/inspect_formats.demo.sh.txt
   :language: text
   :lines: 14-19

无效输入边界
------------

parse 或 model-load failure 是 CLI error。Inspect 不会为无效输入输出成功 JSON payload。

输出后缀 warning 只是 warning。如果显式传入 ``--format``，即使输出文件后缀看起来可疑，inspect 仍会尊重该格式。
