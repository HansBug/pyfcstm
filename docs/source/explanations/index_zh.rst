解释地图
========

当你需要理解 pyfcstm 行为背后的原因时，从本页选择入口。全站左侧导航会直接列出每个解释页面；本地图给出概念阅读顺序，并说明哪些问题属于解释，而不是教程、任务指南或参考表。

解释承诺什么
------------

解释（explanation）回答系统为什么这样设计：语义顺序、架构边界、设计取舍，以及支持或不支持形式背后的风险。它不替代可运行教程、逐步任务配方或精确查阅页面。

概念阅读路线
------------

1. :doc:`architecture/index_zh`

   当你需要理解完整流水线时，从这里开始：语言文本、抽象语法树、模型导入、检查、渲染、仿真、验证和生成输出。

   **回答的问题：** 主要包层次如何配合，以及一个行为应该放在哪里实现或记录。

2. :doc:`dsl_semantics/index_zh`

   当语法本身还不够时，阅读本页。这里负责解释状态、转换、组合状态进入、生命周期动作、事件作用域、强制转换（forced transition）、组合转换（combo transition）和其他建模语义。

   **回答的问题：** 模型完成解析和导入后到底意味着什么。

3. :doc:`execution_semantics/index_zh`

   当运行顺序很重要时阅读本页：进入组合状态、执行 ``during`` 动作、转换效果、退出动作、热启动、回滚、伪中继状态（pseudo relay state）和仿真器对齐。

   **回答的问题：** 为什么一个周期会产生某条活跃状态和变量轨迹。

4. :doc:`diagnostics/index_zh`

   当你需要理解静态检查、诊断、可选验证和面向大语言模型反馈之间的边界时，阅读本页。

   **回答的问题：** 某条诊断能证明、警告或描述什么类型的问题。

5. :doc:`template_rendering/index_zh`

   当生成行为取决于渲染器、打包模板、表达式渲染、语句渲染或目标语言运行时契约时，阅读本页。

   **回答的问题：** 为什么代码生成要通过配置模板和打包资产，而不是临时复制文件。

6. :doc:`grammar_tooling/index_zh`

   当解析器语法、语法高亮和编辑器工具必须保持同步时，阅读本页。

   **回答的问题：** 为什么修改语法不只是编辑一个 ANTLR 文件。

按问题选择
----------

* **功能应该放在哪里？** 先读 :doc:`architecture/index_zh`。
* **这个语言形式是什么意思？** 读 :doc:`dsl_semantics/index_zh`，再到 :doc:`/reference/dsl/index_zh` 查精确语法。
* **为什么仿真按这个顺序执行动作？** 读 :doc:`execution_semantics/index_zh`，再到 :doc:`/how_to/simulation/index_zh` 跑任务。
* **为什么检查报告这个问题？** 读 :doc:`diagnostics/index_zh`，再到 :doc:`/reference/inspect_report/index_zh` 和 :doc:`/reference/diagnostics_codes/index_zh` 查字段与诊断码。
* **为什么生成代码长这样？** 读 :doc:`template_rendering/index_zh`，再到 :doc:`/reference/builtin_templates/index_zh` 和 :doc:`/reference/template_config/index_zh` 查模板事实。
* **为什么语法变化会牵动编辑器文件？** 读 :doc:`grammar_tooling/index_zh`，再按 :doc:`/how_to/grammar_editor/index_zh` 操作。

解释在哪里停止
--------------

解释可以包含轨迹、图或短例子，只要它们能澄清语义。解释不应该成为查命令选项、参考表或复制粘贴配方的唯一位置。请按需要跳到：

* :doc:`/tutorials/index_zh`，用于首次成功学习；
* :doc:`/how_to/index_zh`，用于具体任务；
* :doc:`/reference/index_zh`，用于精确事实；
* :doc:`/api_doc_zh`，用于自动生成的 Python API 结构。
