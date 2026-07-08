.. _sec-how-to-visualization-zh:

可视化任务
==========

当你需要图表源码或渲染后的图表文件时使用本指南。完整选项表见 :doc:`/reference/visualization_options/index_zh`。
首次图表流程见 :doc:`/tutorials/visualization/index_zh`。

先选择源码还是渲染产物
----------------------

.. list-table:: 输出选择
   :header-rows: 1

   * - 需求
     - 使用
     - 原因
   * - 可审阅的图表源码
     - ``pyfcstm plantuml``
     - 生成确定性的 ``.puml`` 文本，不需要渲染器。
   * - 图片或 PDF 产物
     - ``pyfcstm visualize``
     - 构造同一份 PlantUML 源码，并渲染成 ``png``、``svg`` 或 ``pdf``。
   * - 没有图形界面的持续集成（CI）
     - ``visualize --no-open``
     - 避免依赖桌面查看器。
   * - 私有图表
     - ``visualize --renderer local``
     - 避免把 PlantUML 源码发送给远程服务。

导出 PlantUML 源码
------------------

PlantUML 源码是最安全的第一产物，因为它是文本、确定性强、容易比较差异：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

先使用细节预设，再添加单项覆盖：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

只有存在明确阅读目标时，才重复添加 ``-c key=value``：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o machine.events-depth2.puml

比较细节预设输出
----------------

同一个模型可以按不同细节级别呈现给不同读者。下面示例复用可视化教程里的生成产物。

.. list-table:: 细节预设比较
   :header-rows: 1

   * - 预设
     - 目标读者
     - 优先隐藏内容
     - 现有源码
   * - ``minimal``
     - 架构讨论和非实现读者。
     - 生命周期动作和伪状态样式。
     - :download:`output_minimal.puml <../../tutorials/visualization/output_minimal.puml>`
   * - ``normal``
     - 通用文档和代码审查。
     - 生命周期动作体。
     - :download:`output_normal.puml <../../tutorials/visualization/output_normal.puml>`
   * - ``full``
     - 调试、语义审查和实现讨论。
     - 预设级开关不隐藏内容。
     - :download:`output_full.puml <../../tutorials/visualization/output_full.puml>`

.. figure:: ../../tutorials/visualization/output_minimal.puml.svg
   :alt: minimal 细节预设输出
   :align: center
   :width: 70%

   ``minimal`` 在读者只需要结构时保持图形清晰。

.. figure:: ../../tutorials/visualization/output_normal.puml.svg
   :alt: normal 细节预设输出
   :align: center
   :width: 70%

   ``normal`` 是文档和审查的默认折中。

.. figure:: ../../tutorials/visualization/output_full.puml.svg
   :alt: full 细节预设输出
   :align: center
   :width: 70%

   ``full`` 适合动作和转换细节也是审查内容的场景。

聚焦大型模型
------------

大型状态机应先收窄问题，再增加视觉细节。好的聚焦图通常回答以下问题之一：

* 状态层级是什么？
* 哪些事件驱动模型移动？
* 哪些保护条件和效果控制某组转换？
* 哪些生命周期钩子是集成点？
* 本次审查要讨论哪棵子树？

实用命令模式：

.. code-block:: bash

   # 限制层级深度。
   pyfcstm plantuml -i machine.fcstm -c max_depth=2 -o machine.depth2.puml

   # 结构是主题时隐藏事件名。
   pyfcstm plantuml -i machine.fcstm -c show_events=false -o machine.structure.puml

   # 事件流是主题时显示事件分组。
   pyfcstm plantuml -i machine.fcstm \
     -c event_visualization_mode=both \
     -o machine.events.puml

   # 输出紧凑实现视图。
   pyfcstm plantuml -i machine.fcstm \
     -l full \
     -c max_action_lines=3 \
     -c transition_effect_mode=inline \
     -o machine.compact-full.puml

直接渲染最终文件
----------------

当环境应负责渲染时，使用 ``visualize``：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

不读取领域特定语言（DSL）文件，只检查渲染器可用性：

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

明确选择渲染器模式：

.. list-table:: 渲染器选择
   :header-rows: 1

   * - 模式
     - 命令形态
     - 适用场景
   * - ``auto``
     - ``pyfcstm visualize --check --renderer auto``
     - 本地开发中，本地或远程渲染任一可用都可以。
   * - ``local``
     - ``pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open``
     - 图表私有，或构建不应依赖网络。
   * - ``remote``
     - ``pyfcstm visualize -i machine.fcstm --renderer remote --no-open``
     - 允许使用配置的 PlantUML 服务，并且比本地 Java 设置更方便。

保持 CI 图表任务稳定
--------------------

CI 图表任务不应依赖桌面查看器：

.. code-block:: bash

   pyfcstm plantuml -i machines/main.fcstm -o build/main.puml
   pyfcstm visualize -i machines/main.fcstm -t svg -o build/main.svg --no-open

如果渲染在持续集成中是可选项，把源码导出和渲染导出拆开。源码导出证明 pyfcstm 能解析并输出 PlantUML；渲染导出额外证明渲染后端可用。

命令行取值不够时使用 Python 应用程序接口（API）
------------------------------------------------

命令行支持标量和元组值。需要事件颜色字典这类对象配置时，使用 Python 应用程序接口（API）：

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   options = PlantUMLOptions(
       event_visualization_mode='color',
       custom_colors={'System.Start': '#00AA00'},
   )
   plantuml_text = model.to_plantuml(options)

完整可运行示例可下载
:download:`python_basic.demo.py <../../tutorials/visualization/python_basic.demo.py>` 和
:download:`python_options.demo.py <../../tutorials/visualization/python_options.demo.py>`。

排查可视化问题
--------------

.. list-table:: 可视化排查
   :header-rows: 1

   * - 现象
     - 检查
     - 可能修复
   * - ``plantuml`` 失败
     - ``pyfcstm inspect -i machine.fcstm``
     - 先修复 DSL 语法或模型诊断，再导出图表。
   * - ``visualize`` 渲染前失败
     - 输出后缀和 ``--type``
     - 对齐后缀和类型，或省略后缀让 pyfcstm 自动补。
   * - 本地渲染失败
     - ``pyfcstm visualize --check --renderer local``
     - 配置 Java 和 ``PLANTUML_JAR``，或传 ``-p``。
   * - 远程渲染失败
     - ``pyfcstm visualize --check --renderer remote``
     - 检查网络、代理或 ``PLANTUML_HOST``。
   * - 查看器启动被跳过
     - ``PYFCSTM_NO_GUI``、``CI``、显示环境变量
     - 脚本中使用 ``--no-open``；``--strict-open`` 只留给桌面任务。
   * - 图表太密
     - 细节级别和可见性选项
     - 从 ``minimal`` 或 ``normal`` 开始，只添加当前读者需要的事实。
