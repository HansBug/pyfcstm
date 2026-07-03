第一份 inspect 报告
==============================

``pyfcstm inspect`` 用来回答“这段 FCSTM 最终变成了什么模型”。它会构建与仿真、可视化和代码生成相同的状态机模型，然后报告结构、指标、派生图、组合 provenance 和诊断。

本教程只保留一次诊断较丰富的首次运行。CI 和 LLM 任务请见 :doc:`/how_to/inspect/index_zh`。报告字段和诊断码请见 :doc:`/reference/inspect_report/index_zh` 与 :doc:`/reference/diagnostics_codes/index_zh`。

使用诊断较丰富的示例
--------------------

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :caption: inspect_diagnostics.fcstm

先运行 human 输出
-----------------

默认输出适合人类阅读：

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm

报告会先显示模型身份和指标，然后输出带源码上下文、provenance、建议动作和 do-not notes 的诊断：

.. literalinclude:: inspect_human.demo.sh.txt
   :language: text
   :caption: human inspect 输出摘录
   :lines: 1-40

导出结构化 JSON
---------------

脚本需要完整报告时，使用 ``--format json``：

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o report.json

生成 demo 会总结形态：

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: JSON report 摘要
   :lines: 1-12

记住无效输入边界
----------------

语法错误和模型加载失败是 CLI failure。即便请求了 ``--format json``，inspect 也不会为无法解析或无法加载的输入伪造一份成功的 ``diagnostics[]`` payload：

.. literalinclude:: inspect_invalid.demo.sh.txt
   :language: text
   :caption: 无效输入边界

下一步
------

* :doc:`/how_to/inspect/index_zh` 展示 CI 和 LLM-oriented inspect 任务。
* :doc:`/reference/inspect_report/index_zh` 列出报告字段和格式。
* :doc:`/reference/diagnostics_codes/index_zh` 列出常见诊断码。
* :doc:`/explanations/diagnostics/index_zh` 解释诊断边界。
