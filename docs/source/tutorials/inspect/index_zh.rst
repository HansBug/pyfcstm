Inspect 与诊断
==============

本页是独立 inspect 教程的临时入口，后续文档更新会把这里扩展成完整指南。

目前可以使用 ``pyfcstm inspect`` 输出结构化 JSON 报告：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm -o machine.inspect.json

报告包含模型结构、指标、派生图和诊断信息。诊断信息应当足够精确，可以服务人类阅读和 LLM 辅助修复流程，但 inspect 不能替代仿真、目标硬件测试或完整形式化验证。

需要 verify 支撑的可选检查时，显式开启 ``--enable-verify``；它不是默认快速路径的一部分。
