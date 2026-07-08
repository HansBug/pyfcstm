.. _sec-how-to-cli-workflows-zh:

命令行工作流
============

当你需要一组可重复命令时使用本指南。本页假设 pyfcstm 已经安装；如果尚未安装，请先看
:doc:`/how_to/installation/index_zh`。精确选项和失败边界请查 :doc:`/reference/cli/index_zh`。

先选对命令
----------

.. list-table:: 命令选择
   :header-rows: 1

   * - 目标
     - 命令
     - 主要输出
     - 后续参考
   * - 不生成代码，只运行模型
     - ``simulate``
     - 活跃状态和变量轨迹
     - :doc:`/reference/simulation/index_zh`
   * - 读取模型事实和诊断
     - ``inspect``
     - 人类、JSON 或面向大语言模型（LLM）的报告
     - :doc:`/reference/inspect_report/index_zh`
   * - 生成目标语言文件
     - ``generate``
     - 输出目录
     - :doc:`/reference/builtin_templates/index_zh`
   * - 导出图表源码
     - ``plantuml``
     - ``.puml`` 文本
     - :doc:`/reference/visualization_options/index_zh`
   * - 渲染图表产物
     - ``visualize``
     - ``.png``、``.svg`` 或 ``.pdf``
     - :doc:`/reference/visualization_options/index_zh`

查看命令帮助
------------

先看顶层帮助，再看准备运行的子命令：

.. code-block:: bash

   pyfcstm --help
   pyfcstm inspect --help
   pyfcstm generate --help

帮助输出也是环境检查。如果找不到 ``pyfcstm``，用同一环境试 ``python -m pyfcstm --help``，然后回到
:doc:`/how_to/installation/index_zh` 排查安装问题。

运行短模拟
----------

需要写入文档、持续集成（CI）日志或问题报告的记录时，使用批处理模式：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"

手动探索时使用交互模式：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm

实用检查：

* 先运行 ``current``，让记录包含初始活跃路径。
* 批处理脚本中显式写事件名，例如 ``cycle Start``。
* 只有能提供所有必需变量值时才使用热启动。
* 不要把模拟结果当成生成目标代码正确性的证明；它是生成运行时测试应对齐的参考行为。

导出 inspect 报告
-----------------

编辑模型时，人类输出最方便：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm

脚本消费指标、诊断或模型事实时，使用完整 JSON：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

准备把报告贴给 LLM 辅助修复时，使用面向 LLM 的格式：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md

CI 风格检查要显式并且有边界：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm \
     --format json \
     --enable-verify \
     --smt-timeout-ms 2000 \
     -o machine.inspect.json

如果命令在读取模型前失败，先检查验证策略选项。inspect 会解析一部分高成本分类标签，只是为了明确报告自动 inspect 不允许使用它们。

从内置模板生成代码
------------------

普通用户优先使用打包内置模板：

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear

只有在你明确维护自定义模板时，才使用自定义模板目录：

.. code-block:: bash

   pyfcstm generate -i machine.fcstm -t ./templates/my_target -o generated/my_target --clear

生成检查清单：

* 把领域特定语言（DSL）源文件和生成命令一起记录在项目说明或构建规则中。
* 只对可以安全替换的输出目录使用 ``--clear``。
* 提交生成文件前先审阅。
* 如果输出按需重建，把生成目录放进 ``.gitignore``，不要提交过期产物。
* 生成的 README 是运行时集成和冒烟检查的下一入口。

导出 PlantUML 源码
------------------

需要可审阅、可提交、可由其他工具渲染的确定性源码时，使用 ``plantuml``：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

先选细节级别，再加覆盖项：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

只有图表确实需要时，才加入窄范围配置覆盖：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o machine.focused.puml

渲染图表产物
------------

渲染环境不确定时，先用 ``visualize --check``：

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

CI 或无图形界面环境中渲染时不要启动查看器：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

私有图表优先使用本地渲染：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open

只有生成的 PlantUML 源码允许发送到配置服务时，才使用远程渲染：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm --renderer remote --no-open

让命令可复现
------------

依赖 pyfcstm 命令的仓库应明确输入/输出关系：

* 把源状态机放在稳定目录，例如 ``machines/`` 或 ``src/machines/``。
* 按目标命名生成目录，例如 ``generated/python`` 或 ``generated/c_poll``。
* 在 Makefile、CI 作业或项目 README 中记录命令行。
* inspect 报告和图表要么明确是生成物，要么明确作为审查产物提交。
* 不需要渲染图片时，优先导出 ``plantuml`` 源码。
* 脚本中使用 ``visualize --no-open``，避免图形界面可用性影响构建结果。

按层排查
--------

.. list-table:: 排查路线
   :header-rows: 1

   * - 现象
     - 首选命令
     - 下一页
   * - 找不到 ``pyfcstm`` 命令
     - ``python -m pyfcstm --help``
     - :doc:`/how_to/installation/index_zh`
   * - DSL 无法解析
     - ``pyfcstm inspect -i machine.fcstm``
     - :doc:`/reference/dsl/index_zh`
   * - 模型能解析但行为意外
     - ``pyfcstm simulate -i machine.fcstm -e "current; cycle; current"``
     - :doc:`/explanations/execution_semantics/index_zh`
   * - 需要解释诊断
     - ``pyfcstm inspect -i machine.fcstm --format json``
     - :doc:`/reference/diagnostics_codes/index_zh`
   * - 生成失败
     - ``pyfcstm generate ... --template python``
     - :doc:`/reference/builtin_templates/index_zh`
   * - 渲染失败
     - ``pyfcstm visualize --check --renderer auto``
     - :doc:`/reference/visualization_options/index_zh`

后续阅读
--------

* :doc:`/how_to/generation/index_zh` 讲生成运行时任务。
* :doc:`/how_to/inspect/index_zh` 更深入讲 inspect 工作流。
* :doc:`/how_to/visualization/index_zh` 讲图表导出选择。
