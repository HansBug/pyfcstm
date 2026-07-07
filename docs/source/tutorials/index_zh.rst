教程路线图
==========

第一次学习 pyfcstm，并且希望每读完一页都有可见进展时，从本页开始。全站左侧导航会直接列出每个教程；本路线图只说明这些同级页面应该按什么顺序阅读，以及当教程刻意停止在入门边界时应该跳到哪里继续查。

怎样阅读教程
------------

教程（tutorial）负责首次成功。每页应该给出一个小而完整的工作结果，然后指向真正负责更广覆盖的任务指南、解释或参考页。

* 如果你刚接触项目，按照下面的推荐路径阅读。
* 如果你已经有明确任务，请直接看 :doc:`/how_to/index_zh`。
* 如果你需要精确选项、语法形式、报告字段或应用程序接口（API）对象，请看 :doc:`/reference/index_zh`。
* 如果你想理解某个行为为什么存在，请看 :doc:`/explanations/index_zh`。

推荐首次路径
------------

1. :doc:`quick_start/index_zh`

   跑通最短端到端流程：安装命令、执行小模型、检查模型、生成代码并导出图。在学习全部概念之前，先用它确认工具链能工作。

   **读完产出：** 你见过核心命令流和主要输出。

2. :doc:`dsl/index_zh`

   有意识地写第一个模型：状态、转换、变量、守卫、生命周期动作，以及学习示例和完整语法参考之间的区别。

   **读完产出：** 你能识别合法 FCSTM 文件的基本形状，并知道何时跳到 :doc:`/reference/dsl/index_zh` 查精确语法。

3. :doc:`simulation/index_zh`

   把模型当作行为执行，而不只是当作文本阅读。这里展示周期、活跃状态变化，以及仿真细节何时应该移交给任务指南或执行语义解释。

   **读完产出：** 你能运行一个小模型，并判断活跃状态路径是否按预期变化。

4. :doc:`inspect/index_zh`

   让 pyfcstm 说明它读懂了什么。本教程聚焦检查（inspect）和诊断（diagnostics）能展示什么、会给出什么样的信息，以及这些信息如何指导人类或大语言模型回到源模型修正问题。

   **读完产出：** 你能生成检查报告，并决定下一步使用人类可读报告、JSON，还是后续诊断参考。

5. :doc:`generation/index_zh`

   通过打包内置模板生成代码。本页是生成流程的学习路径；模板内部、配置键和目标语言族契约不放在教程里展开。

   **读完产出：** 你能在不绕开打包模板提取机制的前提下生成运行时产物。

6. :doc:`visualization/index_zh`

   从同一个模型导出图源码或渲染图，让你可以向其他读者解释模型结构。

   **读完产出：** 你能选择第一条可视化命令，并知道去哪里查渲染器相关选项。

按目标快速跳转
--------------

* **只想确认命令能跑：** 先看 :doc:`quick_start/index_zh`，再跳到 :doc:`/how_to/cli_workflows/index_zh`。
* **需要编写真实模型：** 先看 :doc:`dsl/index_zh`，再用 :doc:`/how_to/dsl/index_zh` 做任务，用 :doc:`/reference/dsl/index_zh` 查精确语法。
* **需要排查模型反馈：** 先看 :doc:`inspect/index_zh`，再用 :doc:`/reference/inspect_report/index_zh` 和 :doc:`/reference/diagnostics_codes/index_zh` 查字段与诊断码。
* **需要生成代码：** 先看 :doc:`generation/index_zh`，再看 :doc:`/how_to/generation/index_zh`、:doc:`/how_to/templates/index_zh` 和模板参考页。
* **需要导出图：** 先看 :doc:`visualization/index_zh`，再用 :doc:`/reference/visualization_options/index_zh` 查选项行为。

教程路径的边界
--------------

教程不应该成为所有命令选项、语法分支、诊断码或渲染设置的唯一事实来源。当你遇到边界时：

* 重复操作任务属于 :doc:`/how_to/index_zh`；
* 设计原因属于 :doc:`/explanations/index_zh`；
* 精确事实属于 :doc:`/reference/index_zh`；
* Python 对象细节属于 :doc:`/api_doc_zh`。

兼容入口页
----------

旧教程 URL 继续作为短入口页保留。它们用于保护旧链接，并指向现在真正负责对应内容的模块，但不再属于主要学习路径：

* :doc:`installation/index_zh`
* :doc:`cli/index_zh`
* :doc:`render/index_zh`
* :doc:`grammar/index_zh`
* :doc:`structure/index_zh`
