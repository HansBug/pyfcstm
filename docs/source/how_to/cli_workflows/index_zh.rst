.. _sec-how-to-cli-workflows-zh:

命令行工作流
============

当你需要一组可重复命令时使用本指南。本页假设 pyfcstm 已经安装；如果尚未安装，请先看
:doc:`/how_to/installation/index_zh`。精确选项和失败边界请查 :doc:`/reference/cli/index_zh`。

本页中文术语约定：命令（command）、标准输出（stdout）、标准错误（stderr）、退出状态（exit status）、
文件副作用（file side effect）、批处理（batch）、渲染器（renderer）、后端（backend）和第一排查步骤（first troubleshooting step）
首次在这里对应英文；后文普通说明使用中文术语。命令行文本、路径和输出摘录保持原文。

本页使用的具体示例
------------------

当需要真实输入时，本页使用仓库内的 quick-start 源文件
``docs/source/tutorials/quick_start/traffic_light.fcstm``。项目脚本中请替换成自己的状态机文件。

先运行一个命令，确认命令行、解析器和模型导入器看到的是同一份源码：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/quick_start/traffic_light.fcstm

预期成功信号：

.. code-block:: text

   [OK] FCSTM Inspect Report: docs/source/tutorials/quick_start/traffic_light.fcstm
   root: TrafficLight
   states: 4 total / 3 leaf
   transitions: 4
   diagnostics: 0 errors / 0 warnings / 0 infos

如果命令在摘要前失败，先修复这一层，再尝试模拟、生成或可视化。文件不可读、解析错误、模型验证错误都属于更早的层；渲染器或模板配置无法修复这些问题。

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

核心工作流验收卡片
------------------

把命令写进项目自动化时，用下表确认每一步确实成功，并知道失败时先查哪里。

.. list-table:: 命令行任务验收卡片
   :header-rows: 1

   * - 任务
     - 可复制命令
     - 成功信号
     - 文件副作用
     - 第一排查步骤
   * - 模拟一条短路径。
     - ``pyfcstm simulate -i docs/source/tutorials/quick_start/traffic_light.fcstm -e "current; cycle; current"``
     - 周期后输出包含 ``Current State: TrafficLight.Red``。
     - 无；除非 shell 重定向标准输出。
     - 先运行 ``inspect``；若检查干净，再看批处理命令拼写和事件名。
   * - 导出机器事实。
     - ``pyfcstm inspect -i docs/source/tutorials/quick_start/traffic_light.fcstm --format json -o /tmp/traffic.inspect.json``
     - JSON 含有 ``"root_state_path": "TrafficLight"``，且 ``diagnostics`` 列表为空。
     - 写出指定报告文件。
     - 先查 ``--format`` 拼写和验证策略选项，不要马上假设模型错误。
   * - 生成 Python 文件。
     - ``pyfcstm generate -i docs/source/tutorials/quick_start/traffic_light.fcstm --template python -o /tmp/traffic-python --clear``
     - 输出目录包含生成的 Python 运行时文件和生成 README 指引。
     - 带 ``--clear`` 时会替换输出目录。
     - 确认只使用 ``--template`` 或 ``--template-dir`` 其中之一，并确认输出目录可安全删除。
   * - 导出 PlantUML 源码。
     - ``pyfcstm plantuml -i docs/source/tutorials/quick_start/traffic_light.fcstm -o /tmp/traffic.puml``
     - 文件以 ``@startuml`` 开头，并包含 ``state "TrafficLight"``。
     - 只写出指定的 ``.puml`` 文件。
     - 若失败，排查 DSL/模型错误；这里不涉及渲染器。
   * - 检查渲染器。
     - ``pyfcstm visualize --check --renderer auto``
     - 报告至少一个可用渲染器，或给出清楚的后端错误。
     - 不读取 DSL 文件，也不写图表文件。
     - 本地失败时提供 ``--plantuml-jar`` 或 ``PLANTUML_JAR``；远程失败时检查远程主机。
   * - 渲染图表。
     - ``pyfcstm visualize -i docs/source/tutorials/quick_start/traffic_light.fcstm -t svg -o /tmp/traffic.svg --no-open``
     - 指定 SVG 存在且非空。
     - 写出渲染产物，并可能使用渲染器缓存目录。
     - 先运行 ``plantuml``，把源码导出失败和渲染器失败分开。

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

带预期信号的命令例子
--------------------

下面的例子可以直接复制。输出摘录故意保持短小；完整输出可能包含更丰富的终端格式。

.. list-table:: 命令输入和成功信号
   :header-rows: 1

   * - 任务
     - 起始输入
     - 命令
     - 成功信号
     - 文件副作用
   * - 模拟一个冷启动周期。
     - quick-start 教程里的 ``traffic_light.fcstm``。
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``
     - transcript 包含 ``Cycle: 0``，之后出现 ``Cycle: 1`` 和 ``Current State: TrafficLight.Red``。
     - 无。
   * - 导出人类 inspect 报告。
     - 任意可解析 ``.fcstm`` 文件。
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - 干净模型输出以 ``[OK] FCSTM Inspect Report`` 开头，并以 ``No diagnostics.`` 收尾。
     - 无。
   * - 导出 JSON inspect 数据。
     - 任意可解析 ``.fcstm`` 文件。
     - ``pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json``
     - JSON 包含 ``metrics`` 和 ``diagnostics`` 键。
     - 写入 ``traffic_light.inspect.json``。
   * - 生成 Python 内置模板。
     - 任意可解析 ``.fcstm`` 文件。
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - 输出目录包含 ``machine.py``、``README.md`` 和 ``README_zh.md``。
     - 清理并重写 ``generated/python``。
   * - 导出 PlantUML 源码。
     - 任意可解析 ``.fcstm`` 文件。
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - 文件以 ``@startuml`` 开头并包含根状态。
     - 写入 ``traffic_light.puml``。
   * - 检查可视化后端。
     - 不需要 DSL 输入。
     - ``pyfcstm visualize --check --renderer auto``
     - 输出报告本地和/或远程渲染器状态。
     - 无。
   * - 渲染 SVG 产物。
     - 任意可解析 ``.fcstm`` 文件，以及可用渲染器。
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - 成功时命令报告渲染器和输出路径。
     - 写入 ``traffic_light.svg``。

短输出摘录
~~~~~~~~~~

批处理模拟输出应类似下面这样，具体边框格式可能随终端变化：

.. code-block:: text

   >>> current
   Cycle: 0
   Current State: TrafficLight
   Variables:
     timer = 0
   >>> cycle
   Cycle: 1
   Current State: TrafficLight.Red

同一干净模型的人类 inspect 输出很短：

.. code-block:: text

   [OK] FCSTM Inspect Report: traffic_light.fcstm
   Summary
     status: ok
     root: TrafficLight
     states: 4 total / 3 leaf
     transitions: 4
     variables: 1
     diagnostics: 0 errors / 0 warnings / 0 infos

   No diagnostics.

Python 生成输出目录至少应有下面的形状：

.. code-block:: text

   README.md
   README_zh.md
   machine.py

PlantUML 源码是文本，不是图片：

.. code-block:: text

   @startuml
   hide empty description
   skinparam state {
     BackgroundColor<<pseudo>> LightGray
   }

失败探针
~~~~~~~~

工作流失败时，用下面的探针快速定位层级：

.. list-table:: 失败探针
   :header-rows: 1

   * - 探针
     - 命令
     - 预期失败信号
     - 含义
   * - 缺少输入选项。
     - ``pyfcstm inspect``
     - ``Missing option '-i' / '--input-code'``。
     - Click 还没有进入 DSL 解析。
   * - inspect 格式非法。
     - ``pyfcstm inspect -i traffic_light.fcstm --format xml``
     - Click 报告允许的 choices。
     - 先修命令语法，再调模型。
   * - 可视化后缀不匹配。
     - ``pyfcstm visualize -i traffic_light.fcstm -o traffic_light.svg -t png --no-open``
     - 输出说明 ``Output file suffix '.svg' does not match render type 'png'.``。
     - 先修输出命名，再调 PlantUML。
   * - 模拟器命令层失败。
     - ``pyfcstm simulate -i traffic_light.fcstm -e "rewind"``
     - 转录显示 ``Unknown command: rewind``，但批处理模式仍以退出状态 ``0`` 结束。
     - 把转录当作失败信号，并修正模拟器命令脚本。
   * - 渲染器可用性。
     - ``pyfcstm visualize --check --renderer local``
     - 本地不可用时报告缺少 Java、PlantUML jar 或后端失败。
     - 配置本地渲染器或切换到允许的远程渲染器。


端到端验收卡片
--------------

当项目 README、CI 任务或问题报告需要不止一条命令时，使用这些卡片。每张卡都把命令序列连接到验收信号和第一步修复路径。

.. list-table:: 工作流验收卡片
   :header-rows: 1

   * - 工作流
     - 命令
     - 何时接受
     - 先修哪里
   * - 复现用户当前状态
     - ``pyfcstm simulate -i machine.fcstm -e "current; cycle Start; current"``。
     - 转录说出起始活动路径，周期数发生变化，变量可见。
     - 如果事件没有效果，检查事件作用域和源状态是否匹配模型。
   * - 把模型交给 LLM 修复
     - ``pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md``。
     - Markdown 报告包含状态、指标、诊断、源码摘录和建议修复事实。
     - 如果报告为空或缺少诊断，用 human 格式确认正在检查的文件。
   * - 捕获机器可读回归产物
     - ``pyfcstm inspect -i machine.fcstm --format json -o reports/machine.inspect.json``。
     - JSON 可解析，并包含 metrics 与 diagnostics 数组。
     - 如果出现后缀警告，重命名目标，避免读者误解格式。
   * - 刷新生成的 Python 代码
     - ``pyfcstm generate -i machine.fcstm --template python -o generated/python --clear``。
     - ``machine.py``、``README.md`` 和 ``README_zh.md`` 存在，目标目录只包含预期生成文件。
     - 如果仍有陈旧文件，检查 ``--clear`` 是否指向你实际检查的生成目录。
   * - 生成可审查图源码
     - ``pyfcstm plantuml -i machine.fcstm -l normal -o diagrams/machine.puml``。
     - 文件是文本，以 ``@startuml`` 开头，并可在代码审查中 diff。
     - 如果审查者期待图片，要么用 ``visualize`` 渲染，要么说明源码审查是有意选择。
   * - 生成文档图片产物
     - ``pyfcstm visualize -i machine.fcstm -t svg -o docs/_static/machine.svg --no-open``。
     - SVG 存在，并且视觉检查确认标签可读。
     - 如果渲染失败，先运行 ``visualize --check``，再改图形选项。

后续阅读
--------

* :doc:`/how_to/generation/index_zh` 讲生成运行时任务。
* :doc:`/how_to/inspect/index_zh` 更深入讲 inspect 工作流。
* :doc:`/how_to/visualization/index_zh` 讲图表导出选择。
