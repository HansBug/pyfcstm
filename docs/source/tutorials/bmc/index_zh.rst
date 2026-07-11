第一次有界模型检查
==================

本教程用一个很小的 FCSTM 模型完成一次有界模型检查（bounded model
checking，BMC）。你将运行一条 ``reach`` 查询，识别人类可读报告，把同一结果
保存为 JSON，并确认 SAT 见证已由运行时重放。所有命令都从仓库根目录运行。

有界模型检查只搜索查询中给定边界以内的执行。这里的成功表示示例在该边界内
存在一条可重放执行；它不是对所有可能执行的无界证明。

前提
----

命令必须列出 BMC 子命令：

.. code-block:: bash

   python -m pyfcstm bmc --help

首行应为 ``Usage: python -m pyfcstm bmc [OPTIONS]``。若已安装的
``pyfcstm`` 脚本是当前版本，也可以用它代替 ``python -m pyfcstm``。

1. 阅读模型
------------

教程模型只有一个根状态，没有变量或事件：

.. literalinclude:: first_check.fcstm
   :language: text
   :caption: ``docs/source/tutorials/bmc/first_check.fcstm``

这里故意不增加配置。冷启动时，状态机可以进入 ``Door``。

2. 阅读性质
------------

查询询问：是否存在某次执行能在一个宏步以内到达 ``Door``：

.. literalinclude:: reach_door.fbmcq
   :language: text
   :caption: ``docs/source/tutorials/bmc/reach_door.fbmcq``

``reach`` 是\ **见证极性（witness polarity）**\ 性质，因此 SAT 表示 BMC 找到了
所求执行。这与 ``forbid`` 等安全性质不同：安全性质的 SAT 表示找到了反例。

3. 运行第一次检查
------------------

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/tutorials/bmc/first_check.fcstm \
       -q docs/source/tutorials/bmc/reach_door.fbmcq

已核对的报告先给出性质结论。耗时会随机器变化，以下用 ``...`` 代替：

.. code-block:: text

   BMC reach <= 1: PROPERTY HOLDS
   A satisfying execution was found within the bound.

   Solver: SAT in ... ms
   Replay: verified (2 frames, 1 step).

   Trace
     0: init -> Door [initial]

进程以 ``0`` 退出。第一行是性质结论；``Solver`` 行只是支持证据，用户不需要自行
根据极性把 SAT 换算成性质是否成立。交互终端会用绿色显示成立结论，用青色显示诊断
标签；重定向、JSON 和文件输出都不含 ANSI 转义序列。

Z3 返回 SAT 后，CLI 不会立刻输出报告。它先解码符号见证，再用
``SimulationRuntime`` 重放；只有重放成功才产生这里的 ``verified`` 信号。重放增强了
轨迹与当前运行时语义一致的可信度，但它不是第二次形式化证明，CLI 也不会安装
用户抽象处理器。

4. 保存机器可读输出
--------------------

脚本使用 ``--json``，再用 ``-o`` 原子写入完整报告：

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/tutorials/bmc/first_check.fcstm \
       -q docs/source/tutorials/bmc/reach_door.fbmcq \
       --json -o /tmp/first-bmc.json

指定 ``-o`` 后标准输出（stdout）为空；目标的父目录必须已存在。只读取稳定字段：

.. code-block:: bash

   FIRST_BMC_JSON=/tmp/first-bmc.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(
       Path(os.environ["FIRST_BMC_JSON"]).read_text(encoding="utf-8")
   )
   print(payload["schema_version"])
   print(payload["result"]["outcome"])
   print(payload["replay"]["ok"])
   print(payload["exit_code"])
   PY

预期输出：

.. code-block:: text

   bmc-cli/v1
   witness_found
   True
   0

持续集成中不要快照 ``elapsed_ms``，它是实时耗时；这里使用的稳定契约是
``schema_version``、``result.outcome``、``replay.ok`` 和 ``exit_code``。

5. 重跑已核对的演示
--------------------

独立演示会切换到自身目录，因此不依赖 Python 测试树或其他文档夹具：

.. code-block:: bash

   bash docs/source/tutorials/bmc/first_check.demo.sh

它写出 ``docs/source/tutorials/bmc/first_check.result.json``，并打印同一组四字段
JSON 摘要。试验后删除该生成结果；模型、查询和演示脚本才是源夹具。

后续阅读
--------

:doc:`../../how_to/bmc/index_zh` 提供七类性质、初始状态、假设、调用谓词、
持续集成、超时和排错任务。完整 ``.fbmcq`` 语言见
:doc:`../../reference/bmc_query/index_zh`，CLI、JSON、退出状态、见证与重放字段见
:doc:`../../reference/bmc_results/index_zh`。性质极性与有界范围的数学含义见
:doc:`../../explanations/bmc_properties/index_zh`。
