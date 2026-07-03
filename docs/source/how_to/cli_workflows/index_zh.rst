.. _sec-how-to-cli-workflows-zh:

CLI 工作流
==========

当你已经知道要完成什么任务时，使用本指南。精确选项事实请查 :doc:`/reference/cli/index_zh`。

查看命令帮助
------------

先看顶层帮助，再查看目标子命令：

.. code-block:: bash

   pyfcstm --help
   pyfcstm simulate --help
   pyfcstm inspect --help
   pyfcstm generate --help
   pyfcstm plantuml --help

运行短仿真
----------

需要可复现命令转录时，使用 batch mode：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"

需要手动探索事件和 hot start 时，使用交互式仿真器：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm

导出 inspect 报告
-----------------

默认输出适合人类阅读：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm

脚本应显式请求结构化格式：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

给 LLM 辅助修复使用时，选择面向 LLM 的格式：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md

从内置模板生成代码
------------------

对打包内置模板，使用 ``--template``：

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear

只有在你明确提供自己维护的自定义模板目录时，才使用 ``-t`` / ``--template-dir``。

导出 PlantUML 源码
------------------

需要稳定、可版本管理的源码文件时，使用 ``plantuml``：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

只有在环境中有可用 PlantUML backend 时，才直接渲染最终图像：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

下一步
------

* :doc:`/how_to/generation/index_zh` 覆盖生成 runtime 任务。
* :doc:`/how_to/inspect/index_zh` 覆盖 CI 和 LLM-oriented inspect 用法。
* :doc:`/how_to/visualization/index_zh` 覆盖图表导出任务。
