任务指南路线图
==============

当你已经知道自己要完成什么任务时，从本页选择入口。全站左侧导航会直接列出每个任务指南；本路线图按输入、输出、成功信号和失败后去哪里查，帮助你选择正确的同级页面。

任务指南承诺什么
----------------

任务指南（how-to guide）从具体任务开始，以可观察结果结束。它不负责从零教学所有概念，也不复制选项表或模式表。首次学习请看教程，需要设计原因请看解释，需要精确查阅请看参考。

按任务选择页面
--------------

安装或检查环境
~~~~~~~~~~~~~~

当输入是一套新的 Python 环境，或者一台还不确定是否安装 pyfcstm 的机器时，打开 :doc:`installation/index_zh`。

* **输出：** 可工作的命令行入口。
* **成功信号：** ``pyfcstm --help`` 等命令能在目标环境中运行。
* **失败后：** 先用安装页检查包和平台；命令已经存在后，再到 :doc:`/reference/cli/index_zh` 查精确选项。

运行命令行流程
~~~~~~~~~~~~~~

当任务是组合现有命令，例如解析文件、仿真、检查、生成输出或产出图时，打开 :doc:`cli_workflows/index_zh`。

* **输出：** 可重复的命令序列，以及位置明确的文件或终端结果。
* **成功信号：** 命令成功退出，并出现文档中说明的输出。
* **失败后：** 先到 :doc:`/reference/cli/index_zh` 查精确选项；如果失败来自模型内容，再看诊断参考。

编写或修改模型
~~~~~~~~~~~~~~

当你需要变量、状态、转换、守卫、动作或建模模式的操作配方时，打开 :doc:`dsl/index_zh`。

* **输出：** 能表达目标行为的源文件。
* **成功信号：** 解析、检查或仿真命令接受这个文件。
* **失败后：** 到 :doc:`/reference/dsl/index_zh` 查精确语法，到 :doc:`/explanations/dsl_semantics/index_zh` 理解建模语义。

运行仿真任务
~~~~~~~~~~~~

当你需要交互式或批处理执行、周期、事件、热启动或状态历史检查时，打开 :doc:`simulation/index_zh`。

* **输出：** 可见的活跃状态和变量演化。
* **成功信号：** 仿真得到的状态路径符合你从模型中预期的行为。
* **失败后：** 到 :doc:`/explanations/execution_semantics/index_zh` 理解生命周期顺序；再回到仿真教程或任务指南做可运行排查。

检查和诊断模型
~~~~~~~~~~~~~~

当你需要结构化报告、适合大语言模型阅读的反馈，或编辑模型前的诊断证据时，打开 :doc:`inspect/index_zh`。

* **输出：** 人类可读输出、JSON 或面向大语言模型的报告文本。
* **成功信号：** 报告包含预期指标、诊断和源位置。
* **失败后：** 到 :doc:`/reference/inspect_report/index_zh` 查报告形状，到 :doc:`/reference/diagnostics_codes/index_zh` 查诊断码。

生成代码
~~~~~~~~

当任务是用打包内置模板或自定义模板目录运行 ``pyfcstm generate`` 时，打开 :doc:`generation/index_zh`。

* **输出：** 目标输出目录中的生成文件。
* **成功信号：** 生成目录包含预期产物和 README 指引。
* **失败后：** 到 :doc:`/reference/builtin_templates/index_zh` 查内置模板事实，到 :doc:`/reference/template_config/index_zh` 查配置键和渲染边界。

可视化模型
~~~~~~~~~~

当你需要为模型生成 PlantUML 源码或渲染图片时，打开 :doc:`visualization/index_zh`。

* **输出：** 图源码或图片产物。
* **成功信号：** 图文件存在，并能展示你想说明的状态结构。
* **失败后：** 到 :doc:`/reference/visualization_options/index_zh` 查精确渲染选项和环境假设。

维护模板
~~~~~~~~

当你是在编写、打包或审查模板，而不只是使用模板时，打开 :doc:`templates/index_zh`。

* **输出：** 能通过公共渲染路径工作的模板目录或打包模板资产。
* **成功信号：** 生成产物来自 ``pyfcstm.template`` 或渲染器入口，而不是测试里直接绕到仓库模板源码。
* **失败后：** 到 :doc:`/explanations/template_rendering/index_zh` 理解设计边界，到 :doc:`/reference/template_config/index_zh` 查精确配置事实。

更新语法和编辑器资产
~~~~~~~~~~~~~~~~~~~~

当你触碰语法文件、语法高亮或编辑器支持资产时，打开 :doc:`grammar_editor/index_zh`。

* **输出：** 仍然对齐的解析器、高亮和编辑器资产。
* **成功信号：** 文档说明的验证命令通过，并且没有手改生成解析器输出。
* **失败后：** 到 :doc:`/reference/grammar_tooling/index_zh` 查命令和资产路径，再到 :doc:`/explanations/grammar_tooling/index_zh` 理解耦合原因。

怎样离开任务指南区
------------------

* 需要首次学习路径时，去 :doc:`/tutorials/index_zh`。
* 需要理解顺序或边界背后的原因时，去 :doc:`/explanations/index_zh`。
* 需要精确值、字段、默认值或合法形式时，去 :doc:`/reference/index_zh`。
