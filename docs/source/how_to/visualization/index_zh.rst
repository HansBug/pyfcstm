.. _sec-how-to-visualization-zh:

可视化任务指南
==============

当你需要导出图表 artifact 时，使用本指南。选项事实请见 :doc:`/reference/visualization_options/index_zh`。

导出 PlantUML 源码
------------------

PlantUML 源码确定且易于 review：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

用 ``-l`` 选择详细级别预设：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

用重复的 ``-c key=value`` 参数覆盖类型化选项：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=3 \
     -o machine.events.puml


对比详细级别输出
~~~~~~~~~~~~~~~~

同一个机器可以为不同读者生成不同细节的图：

.. list-table:: 详细级别对比
   :header-rows: 1

   * - 预设
     - 适合视图
     - 已生成示例
   * - ``minimal``
     - 仅基本状态结构。
     - :download:`output_minimal.puml <../../tutorials/visualization/output_minimal.puml>`
   * - ``normal``
     - 包含关键 lifecycle 和 transition 信息的平衡视图。
     - :download:`output_normal.puml <../../tutorials/visualization/output_normal.puml>`
   * - ``full``
     - 包含 actions、events、guards 和 effects 的完整细节。
     - :download:`output_full.puml <../../tutorials/visualization/output_full.puml>`

.. figure:: ../../tutorials/visualization/output_minimal.puml.svg
   :alt: 最小详细级别输出
   :align: center
   :width: 70%

   ``minimal``：基本状态结构。

.. figure:: ../../tutorials/visualization/output_normal.puml.svg
   :alt: 普通详细级别输出
   :align: center
   :width: 70%

   ``normal``：平衡默认视图。

.. figure:: ../../tutorials/visualization/output_full.puml.svg
   :alt: 完整详细级别输出
   :align: center
   :width: 70%

   ``full``：面向实现细节的视图。

直接渲染最终文件
----------------

环境中有本地或远端 PlantUML renderer 时，使用 ``visualize``：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

只检查 renderer 可用性，不执行渲染：

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

选择 renderer mode
------------------

* ``--renderer auto`` 先尝试本地渲染，失败后回退到远端渲染。
* ``--renderer local`` 使用 Java 和 PlantUML jar。
* ``--renderer remote`` 使用 PlantUML 服务。

在 CI 或其他 headless 环境中，优先使用 ``--no-open``，避免 viewer 启动影响 job 结果。

需要时使用 Python API
---------------------

CLI ``-c`` 支持类型化标量和元组选项。自定义颜色字典等对象值配置需要使用 Python API。下面的片段假设你已经有解析好的 ``model`` 对象；完整可运行脚本请使用下方 downloadable demo：

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   options = PlantUMLOptions(
       event_visualization_mode='color',
       custom_colors={'System.Start': '#00AA00'},
   )
   plantuml_text = model.to_plantuml(options)

完整可运行示例可下载
:download:`python_basic.demo.py <../../tutorials/visualization/python_basic.demo.py>`
和
:download:`python_options.demo.py <../../tutorials/visualization/python_options.demo.py>`。
