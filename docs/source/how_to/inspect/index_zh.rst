.. _sec-how-to-inspect-zh:

Inspect 任务指南
================

当你想自动运行 ``pyfcstm inspect``，或把输出交给其他工具时，使用本指南。

为 CI 写出 JSON 报告
------------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

在 CI 中，parse/model-load failure 应作为命令失败处理。有效模型上的 diagnostics 再按 ``severity`` 和 ``code`` 分流。

写出 LLM repair report
----------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md
   pyfcstm inspect -i machine.fcstm --format llm-json -o machine.inspect.llm.json

一个实用 LLM 循环是：

1. 运行 inspect，并保留报告作为证据。
2. 要求给出保持意图的最小源码修改。
3. 应用修改。
4. 重新运行 inspect 和相关测试。

LLM report 是指导，不是证明。它可能同时包含启发式设计 warning、deployment-profile warning 和强度不同的 verify-backed 结果。

启用有界 verify 检查
--------------------

默认 inspect 只运行静态检查。只有当 job 能承担成本时才启用 verify：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json --enable-verify \
     --max-complexity-tier smt_linear --smt-timeout-ms 1000 \
     -o machine.verify.inspect.json

Inspect 会拒绝需要单独 proof budget 审查的选项，例如 bounded-model checking depth policy。

保持目标风险措辞精确
--------------------

提到固定宽度生成整数存储的数值部署 warning 是 C/C++ target-profile warning。它们适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 部署审查。它们不是 Python generated runtime 具有同一固定宽度整数承载风险的证据。
