快速开始
========

本页给出 pyfcstm 的最短可用路径：编写一个 FCSTM 文件，运行仿真，检查结构化模型报告，使用内置模板生成代码，并生成 PlantUML 图源文件。

更深入的解释请继续阅读每一步链接到的专题教程。本页故意保持短小，并使用内置模板入口 ``--template``，而不是仓库里的模板目录路径。

1. 编写一个小状态机
--------------------

创建 ``traffic_light.fcstm``：

.. literalinclude:: traffic_light.fcstm
   :language: fcstm

2. 仿真行为
-----------

不写 Python 代码也可以先运行几个周期：

.. code-block:: bash

   pyfcstm simulate -i traffic_light.fcstm -e "cycle; cycle; current"

仿真器适合在生成目标语言代码前检查生命周期动作和转换时序。交互会话、热启动、批处理和执行语义请见 :doc:`/tutorials/simulation/index_zh`。

3. 检查模型
-----------

``inspect`` 默认输出适合人类阅读的报告。如果需要包含状态、转换、指标、派生图和诊断信息的结构化 JSON，请显式使用 ``--format json``：

.. code-block:: bash

   pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json

交通灯模型刻意保持简单，因此 diagnostics 可能为空。完整的 :doc:`/tutorials/inspect/index_zh` 教程会展示更丰富的诊断、源码区间、修复建议，以及这些信息如何指导 LLM 辅助修复。

4. 使用内置模板生成代码
-----------------------

对打包内置模板使用 ``--template``：

.. code-block:: bash

   pyfcstm generate -i traffic_light.fcstm --template python -o _quick_start_python --clear

生成目录里包含运行时代码和生成的 README。完整的 :doc:`/tutorials/generation/index_zh` 教程会覆盖 ``python``、``c``、``c_poll``、``cpp`` 和 ``cpp_poll``。

只有在你明确要使用自定义模板目录时，才使用 ``-t/--template-dir``。

5. 生成图源文件
---------------

如果需要稳定、适合纳入版本管理的图源文件，请使用 ``plantuml``：

.. code-block:: bash

   pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml

如果当前环境有可用的 PlantUML 渲染器，``visualize`` 可以直接渲染最终 ``png`` / ``svg`` / ``pdf`` 文件：

.. code-block:: bash

   pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open

完整可视化选项矩阵留在 :doc:`/tutorials/visualization/index_zh`。

你应该看到什么
----------------

上面的命令刻意不依赖外部 PlantUML 渲染器。一次成功的快速开始运行大致会看到下面这些关键信息：

.. code-block:: text

   Current State: TrafficLight.Red
   timer = 2
   states: 4
   transitions: 4
   diagnostics: 0
   _quick_start_python/machine.py
   _quick_start_python/README.md
   @startuml

文档构建仍会在本目录运行脚本 ``quick_start.demo.sh`` 来保证这些例子可复现。这个脚本是构建时的冒烟测试，不是教程正文推荐的阅读方式；人类读者按上面各小节的短命令逐条复制运行即可。
