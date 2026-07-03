.. _sec-how-to-simulation-zh:

仿真任务指南
============

当你已经有一个 FCSTM 模型，并且需要完成具体仿真任务时，使用本页。第一次引导式运行见
:doc:`../../tutorials/simulation/index_zh`；执行顺序推理见
:doc:`../../explanations/execution_semantics/index_zh`。

CLI 选项和命令事实
------------------

``pyfcstm simulate`` 当前暴露的 CLI 面很小：

.. list-table:: ``pyfcstm simulate`` 选项
   :header-rows: 1

   * - 选项
     - 含义
   * - ``-i`` / ``--input-code TEXT``
     - 入口 FCSTM 文件；必填。
   * - ``-e`` / ``--execute TEXT``
     - 执行分号分隔的批处理命令，而不是启动 REPL。
   * - ``--no-color``
     - 禁用命令输出中的 ANSI 颜色。
   * - ``-h`` / ``--help``
     - 显示 CLI 帮助文本。

批处理字符串和 REPL 共享同一组命令名。最常用的命令如下：

.. list-table:: 仿真器命令
   :header-rows: 1

   * - 命令
     - 用途
   * - ``cycle [count] [events...]``
     - 执行一个或多个周期。计数后面的事件名会传入该周期。
   * - ``current``
     - 显示当前周期、当前状态和持久变量。
   * - ``events``
     - 显示当前状态可用的事件。
   * - ``history [n|all]``
     - 显示最近历史行或全部保留历史。
   * - ``init <state_path> [var=value...]``
     - 使用显式变量在某个状态热启动并重建 runtime。
   * - ``setting [key] [value]``
     - 查看或修改显示、历史、日志设置。
   * - ``export <path>``
     - 导出历史；格式由文件扩展名推断。
   * - ``clear``
     - 使用当前设置重置 runtime。
   * - ``help``
     - 显示命令帮助。
   * - ``quit`` / ``exit``
     - 离开 REPL。

运行批处理命令
--------------

当你需要在 CI、文档或 bug report 中得到可复现转录时，使用 ``-e``。命令之间用分号分隔：

.. code-block:: bash

   pyfcstm simulate -i ../cli/simple_machine.fcstm \
     -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
     --no-color

短教程使用的生成转录保留在这里：

.. literalinclude:: ../../tutorials/simulation/cli_batch.demo.sh.txt
   :language: text

使用交互 REPL
-------------

省略 ``-e`` 即可启动 REPL：

.. code-block:: bash

   pyfcstm simulate -i ../cli/simple_machine.fcstm --no-color

然后逐条输入命令：

.. code-block:: text

   cycle
   events
   cycle Start
   current
   history 3
   quit

交互模式额外提供命令历史、补全和建议，但命令语义和批处理模式一致。

注入事件
--------

``cycle Start`` 这类命令会在该周期注入事件。在 Python 中，把事件列表传给
``SimulationRuntime.cycle``：

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py
   :language: python
   :caption: 通过 Python runtime 注入事件

输出：

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py.txt
   :language: text

示例中的事件名依赖 DSL 事件作用域。语法事实请查 :doc:`../../reference/dsl/index_zh`；本页只说明仿真器如何接收事件。

在状态上热启动
--------------

当你需要检查后续状态但不想重放所有早期周期时，可以使用 REPL 的 ``init`` 命令：

.. code-block:: text

   init System.Active counter=10 flag=1
   cycle
   current

在测试中嵌入同样逻辑时，使用 Python API：

.. code-block:: python

   runtime = SimulationRuntime(
       sm,
       initial_state="System.Active",
       initial_vars={"counter": 10, "flag": 1},
   )

热启动有明确边界：

* ``initial_vars`` 必须提供每个已声明的持久变量。
* 预构造路径上的 enter 动作会被跳过。
* 第一个周期开始后，during 动作正常执行。
* 如果热启动目标是复合状态，它必须能到达某个可停止叶状态，否则 runtime 会报告 DFS 验证错误。

实现抽象处理器
--------------

抽象生命周期动作通过注册 Python handler 实现。给方法加 ``@abstract_handler``，装饰器参数写 DSL 动作路径，方法名本身可以自定义：

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py
   :language: python
   :caption: 仿真 runtime 中的抽象处理器

输出：

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py.txt
   :language: text

handler context 是只读的。常用 helper 包括 ``ctx.get_full_state_path()``、``ctx.get_var(name)``、
``ctx.has_var(name)``、``ctx.active_leaf`` 和 ``ctx.action_stage``。

导出历史
--------

只需要终端输出时用 ``history``。需要后续分析文件时用 ``export <path>``。仿真器从扩展名推断格式；任务文档中建议使用小例子：

.. code-block:: text

   cycle
   cycle Start
   history 2
   export run.json

机器处理优先用 JSON 或 JSONL；表格处理用 CSV；若安装环境支持 YAML，YAML 适合人工阅读快照。除非文件是由 docs build 重新生成并纳入版本控制的 demo 输出，否则导出文件应放在源码树外。

调整显示设置
------------

不带参数的 ``setting`` 会列出当前设置。``setting key value`` 会修改当前会话的一个值。常见例子：

.. code-block:: text

   setting table_max_rows 10
   setting history_size 200
   setting log_level info
   setting color off

``history_size`` 控制保留历史行数。``color`` 也会受 CLI ``--no-color`` 选项影响。

调试失败模型
------------

一个紧凑调试循环是：

1. 如果怀疑解析或诊断问题，先运行 ``pyfcstm inspect``。
2. 用 ``pyfcstm simulate -i ../cli/simple_machine.fcstm -e "cycle; events; current" --no-color``
   获得稳定转录。
3. 每次只增加一个事件。
4. 失败后使用 ``history`` 或 ``export``。
5. 如果热启动失败，检查是否提供了所有变量，以及目标复合状态是否能在不依赖缺失事件的情况下到达可停止叶状态。

不要把仿真输出当作目标运行时测试的替代品。它是快速模型级检查；依赖目标语言行为时，还应搭配生成运行时测试。
