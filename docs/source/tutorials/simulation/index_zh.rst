FCSTM 仿真首次运行
==================

本页是 FCSTM 仿真器的短教程入口。它只保留最少概念、一段可复现批处理命令，以及后续应该阅读的任务指南或执行语义解释。

仿真器检查什么
--------------

仿真器直接执行解析后的模型，适合在生成目标语言代码前检查行为。在一次仿真中：

* **叶状态** 可以成为当前可停止状态；
* **复合状态** 包含子状态，并通过初始转换选择子状态；
* **伪状态** 是自动路由状态，不是普通停止点；
* ``enter``、``during``、``exit`` 等生命周期动作会更新变量，转换负责移动当前状态。

完整执行顺序见 :doc:`../../explanations/execution_semantics/index_zh`。具体命令任务见
:doc:`../../how_to/simulation/index_zh`。精确命令、导出和 Python 应用程序接口事实见
:doc:`../../reference/simulation/index_zh`。

运行一段批处理转录
------------------

批处理模式和交互命令行使用同一套命令处理器。命令用分号分隔，所以一段短转录就能检查初始进入、可用事件、事件驱动转换、当前状态显示和历史输出：

.. code-block:: bash

   pyfcstm simulate -i ../cli/simple_machine.fcstm \
     -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
     --no-color

文档中的输出来自真实 demo 脚本：

.. literalinclude:: cli_batch.demo.sh.txt
   :language: text

第一次 ``cycle`` 会把机器初始化到 ``SimpleMachine.Idle``。``events`` 随后显示当前状态可用的
``Start`` 事件。执行 ``cycle Start`` 后，当前状态变为 ``SimpleMachine.Running``；``cycle Stop`` 到达
``SimpleMachine.Stopped``，短 ``history`` 表展示三次已记录周期。

尝试 Python 运行时循环
----------------------

如果要在 Python 测试或工具中嵌入 pyfcstm，运行时应用程序接口的路径也是一样的：解析 DSL、构建状态机模型、创建
``SimulationRuntime``，然后调用 ``cycle()``。每次调用都会返回循环结果（``CycleResult``）：兼容旧行为的
``value`` 当前为 ``None``，而 ``input_events``、``consumed_events`` 和 ``unconsumed_events`` 会说明本周期提供、使用和未使用的规范事件路径。

.. literalinclude:: basic_usage.demo.py
   :language: python
   :caption: 最小 Python 仿真循环

输出：

.. literalinclude:: basic_usage.demo.py.txt
   :language: text

这个例子只打印状态和变量。如果需要精确的 ``CycleResult`` 字段、事件输入形式、导出格式或公开运行时异常，请查
:doc:`../../reference/simulation/index_zh`。

旧主题去向
----------

旧版仿真指南把教程、任务指南和解释材料混在一个大页里。主要主题现在归位如下：

.. list-table:: 仿真主题去向
   :header-rows: 1

   * - 旧主题
     - 新位置
   * - Python 应用程序接口循环和事件注入
     - :doc:`../../how_to/simulation/index_zh`
   * - 批处理、交互命令行命令、``export`` 和输出格式
     - :doc:`../../how_to/simulation/index_zh`
   * - 热启动任务用法
     - :doc:`../../how_to/simulation/index_zh`
   * - 抽象处理器
     - :doc:`../../how_to/simulation/index_zh`
   * - 配置设置和命令行事实
     - :doc:`../../reference/simulation/index_zh`
   * - 测试、调试和最佳实践说明
     - :doc:`../../how_to/simulation/index_zh`
   * - 业务示例和长语义演练
     - :doc:`../../explanations/execution_semantics/index_zh`
   * - 执行顺序、复合状态进入、切面动作和伪状态
     - :doc:`../../explanations/execution_semantics/index_zh`
   * - 示例使用的 DSL 语法
     - :doc:`../../reference/dsl/index_zh`
   * - DSL 语义背景
     - :doc:`../../explanations/dsl_semantics/index_zh`

旧示例资源继续保留在本目录，保证旧链接和源文件到输出的配对稳定。迁移日志会记录每个资源，最终清理审计也会说明这些兼容资源为什么保留。
