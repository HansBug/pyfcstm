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

保持 CLI 项目可复现
-------------------

需要在本地或 CI 中重复运行时，应让命令输入和生成输出保持可追踪：

* 使用描述性 ``.fcstm`` 文件名，并把相关机器放在专用目录中，例如 ``src/machines/``。
* 将 ``.fcstm`` 源文件与消费其生成输出的代码一起纳入版本控制。
* 仅对可以安全替换的输出目录使用 ``--clear``\ ，并在提交前 review generated
  code。如果输出按需重新生成，则改为把它们加入 ``.gitignore``\ 。
* 保留一份简短项目说明或 build rule，记录每个 DSL 文件生成到哪个输出目录。
* 对打包内置模板优先使用 ``--template``\ 。如果你明确维护 custom template
  directories，则每个 target profile 保持一个目录，在 ``config.yaml``
  中定义语言相关 render helpers，并在生产使用前用小型 sample machines
  做 smoke test。

下一步
------

* :doc:`/how_to/generation/index_zh` 覆盖生成 runtime 任务。
* :doc:`/how_to/inspect/index_zh` 覆盖 CI 和 LLM-oriented inspect 用法。
* :doc:`/how_to/visualization/index_zh` 覆盖图表导出任务。
