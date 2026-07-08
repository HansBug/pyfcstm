第一张图
========

本教程展示从 FCSTM 模型生成 PlantUML 图源码和渲染示例的最短路径。导出任务配方请见 :doc:`/how_to/visualization/index_zh`；选项事实请见 :doc:`/reference/visualization_options/index_zh`。

术语说明：图源文件（diagram source）、渲染后端（rendering backend）和本地渲染（local rendering）在本页首次交接后，后文只使用中文术语。

示例状态机
----------

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

生成 PlantUML 源码
------------------

需要确定性的文本输出时，使用 ``plantuml``：

.. literalinclude:: cli_basic.demo.sh
   :language: bash
   :caption: 基本 CLI 可视化

预期反馈：

.. literalinclude:: cli_basic.demo.sh.txt
   :language: text

渲染示例
--------

文档资源构建会把生成的 PlantUML 源码渲染为 SVG 产物：

.. figure:: output_cli_basic.puml.svg
   :alt: CLI 基本可视化输出
   :align: center
   :width: 80%

   使用 CLI 默认设置生成的 PlantUML 图表。

尝试详细级别预设
----------------

用 ``-l`` 选择内置详细级别预设：

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm -l minimal -o output_minimal.puml
   pyfcstm plantuml -i example.fcstm -l normal -o output_normal.puml
   pyfcstm plantuml -i example.fcstm -l full -o output_full.puml

选项参考会解释每个预设影响哪些事实。

下一步
------

* :doc:`/how_to/visualization/index_zh` 展示 PlantUML 源码导出和直接渲染文件导出任务。
* :doc:`/reference/visualization_options/index_zh` 列出 ``PlantUMLOptions`` 和 CLI ``-c`` 事实。
* :doc:`/tutorials/quick_start/index_zh` 在最短端到端路径中包含可视化。
