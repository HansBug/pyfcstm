第一份 inspect 报告
========================================

本教程用一个较小但诊断较丰富的 FCSTM 文件运行 ``pyfcstm inspect``。目标不是学习每个报告字段，而是看到三种主要输出形式，并知道下一步去哪里查。

使用诊断较丰富的示例
----------------------------------------

已纳入文档构建的教程输入是：

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm

它是合法 DSL。里面的警告是有意安排的教学信号，不是解析失败。

先运行 human 输出
----------------------------------------

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --color never

预期摘录：

.. code-block:: text

   FCSTM Inspect Report
   Root state: InspectDiagnostics
   Diagnostics:

人类可读渲染器用于阅读。它会展示诊断码、严重级别、信息、可用的源码摘录，以及部分结构化 ``refs``。

导出完整 JSON
----------------------------------------

脚本需要结构事实时使用完整 JSON：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --format json -o /tmp/inspect.json
   python - <<'PY'
   import json
   from pathlib import Path

   report = json.loads(Path('/tmp/inspect.json').read_text())
   print(report['root_state_path'])
   print(len(report['states']))
   print([item['code'] for item in report['diagnostics']])
   PY

这个格式是完整 ``ModelInspect`` 契约。字段说明见 :doc:`../../reference/inspect_report/index_zh`。

导出 LLM 修复报告
----------------------------------------

修复循环需要紧凑指导而不是完整结构清单时，使用 ``llm-json``：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --format llm-json -o /tmp/inspect.llm.json

LLM 报告包含修复协议、源码摘录、``refs``、注册表摘要、建议动作和禁止做法。它故意比完整 JSON 更小。

记住无效输入边界
----------------------------------------

Inspect 报告只会在文件可读取、可解析并能转换成模型之后产生。语法错误是命令行失败，不是带 ``diagnostics`` 数组的成功报告。可以用不存在的文件观察边界：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/does-not-exist.fcstm

下一步
----------------------------------------

* CI、LLM 和验证支持的任务做法见 :doc:`../../how_to/inspect/index_zh`。
* Inspect 能证明什么、不能证明什么见 :doc:`../../explanations/diagnostics/index_zh`。
* 已有具体诊断码时查 :doc:`../../reference/diagnostics_codes/index_zh`。
