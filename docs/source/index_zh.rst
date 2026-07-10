欢迎来到 pyfcstm（Python Finite Control State Machine Framework）的文档
==========================================================================

.. only:: html

   .. image:: _static/logos/logo_banner.svg
      :alt: pyfcstm - Python Finite Control State Machine Framework
      :align: center
      :width: 800px

概述
-------------

\ **pyfcstm**\ （Python Finite Control State Machine Framework）是一个强大的 Python 框架，用于解析
\ **FCSTM（Finite Control State Machine）**\ 领域特定语言（DSL）并生成多种目标语言的可执行代码。它专注于使用
灵活的 Jinja2 模板系统建模\ **层次状态机（Harel 状态图）**\ 。

核心特性
~~~~~~~~~~~~~

* **表达性 DSL 语法**：直观的领域特定语言，用于定义状态、转换、事件和生命周期动作
* **层次状态机**：完全支持嵌套状态的父子关系和面向切面编程
* **多语言代码生成**：基于模板的渲染系统，支持 C、C++、Python 和自定义目标语言
* **PlantUML 可视化**：自动生成状态机图表用于文档
* **基于 ANTLR4 的解析器**：强大的语法解析，提供详细的错误报告
* **灵活的事件系统**：本地、链式和全局事件作用域，用于复杂的状态机协调
* **生命周期动作**：进入、期间和退出动作，支持前后切面
* **抽象和引用动作**：声明抽象函数并在状态间重用动作

应用场景
~~~~~~~~~~~~~

pyfcstm 适用于：

* **嵌入式系统**：为微控制器和物联网设备生成高效的状态机代码
* **协议实现**：使用复杂状态转换建模通信协议
* **游戏 AI**：使用层次状态机设计角色行为和游戏逻辑
* **工作流引擎**：使用清晰的状态定义实现业务流程工作流
* **控制系统**：构建具有安全关键状态管理的工业控制逻辑

快速开始
-------------

安装
~~~~

.. code-block:: bash

   pip install pyfcstm

完整安装检查请见 :doc:`how_to/installation/index_zh`。

最快路径
~~~~~~~~

创建 ``traffic_light.fcstm``，并按照 :doc:`tutorials/quick_start/index_zh` 中的完整流程操作。最短命令链如下：

.. code-block:: bash

   pyfcstm simulate -i traffic_light.fcstm -e "cycle; cycle; current"
   pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json
   pyfcstm generate -i traffic_light.fcstm --template python -o generated --clear
   pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml

对打包内置模板使用 ``--template``。只有在渲染自定义模板目录时，才使用 ``-t/--template-dir``。

架构
-------------

pyfcstm 遵循三阶段流水线：

1. **DSL 解析**：基于 ANTLR4 的解析器将 DSL 文本转换为抽象语法树（AST）
2. **模型构建**：AST 节点转换为可查询的状态机模型
3. **代码生成**：Jinja2 模板将模型渲染为目标语言代码

框架提供：

* **DSL 层** (``pyfcstm.dsl``)：语法定义、解析器和 AST 节点
* **模型层** (``pyfcstm.model``)：带验证的状态机模型类
* **渲染引擎** (``pyfcstm.render``)：基于模板的代码生成，支持表达式样式
* **CLI 工具** (``pyfcstm.entry``)：常用操作的命令行界面

教程
-------------------------

教程提供学习路径和首次成功流程。路线图放在第一项，后面直接列出具体教程页面，让首页左侧导航可以直接展示完整学习路径。

.. toctree::
    :maxdepth: 2
    :caption: 教程
    :hidden:

    教程路线图 <tutorials/index_zh>
    tutorials/quick_start/index_zh
    tutorials/dsl/index_zh
    tutorials/simulation/index_zh
    tutorials/inspect/index_zh
    tutorials/generation/index_zh
    tutorials/visualization/index_zh

* :doc:`教程路线图 <tutorials/index_zh>`
* :doc:`tutorials/quick_start/index_zh`
* :doc:`tutorials/dsl/index_zh`
* :doc:`tutorials/simulation/index_zh`
* :doc:`tutorials/inspect/index_zh`
* :doc:`tutorials/generation/index_zh`
* :doc:`tutorials/visualization/index_zh`

任务指南
--------

任务指南面向具体操作。路线图放在第一项，后面直接列出具体任务页面，让首页左侧导航不需要再点进分类页才能看到工作流。

.. toctree::
    :maxdepth: 2
    :caption: 任务指南
    :hidden:

    任务指南路线图 <how_to/index_zh>
    how_to/installation/index_zh
    how_to/cli_workflows/index_zh
    how_to/dsl/index_zh
    how_to/simulation/index_zh
    how_to/inspect/index_zh
    how_to/generation/index_zh
    how_to/visualization/index_zh
    how_to/templates/index_zh
    how_to/grammar_editor/index_zh

* :doc:`任务指南路线图 <how_to/index_zh>`
* :doc:`how_to/installation/index_zh`
* :doc:`how_to/cli_workflows/index_zh`
* :doc:`how_to/dsl/index_zh`
* :doc:`how_to/simulation/index_zh`
* :doc:`how_to/inspect/index_zh`
* :doc:`how_to/generation/index_zh`
* :doc:`how_to/visualization/index_zh`
* :doc:`how_to/templates/index_zh`
* :doc:`how_to/grammar_editor/index_zh`

解释
----

解释页说明语义、架构、边界和取舍。地图页放在第一项，后面直接列出具体解释主题。

.. toctree::
    :maxdepth: 2
    :caption: 解释
    :hidden:

    解释地图 <explanations/index_zh>
    explanations/architecture/index_zh
    explanations/dsl_semantics/index_zh
    explanations/execution_semantics/index_zh
    explanations/diagnostics/index_zh
    explanations/template_rendering/index_zh
    explanations/grammar_tooling/index_zh

* :doc:`解释地图 <explanations/index_zh>`
* :doc:`explanations/architecture/index_zh`
* :doc:`explanations/dsl_semantics/index_zh`
* :doc:`explanations/execution_semantics/index_zh`
* :doc:`explanations/diagnostics/index_zh`
* :doc:`explanations/template_rendering/index_zh`
* :doc:`explanations/grammar_tooling/index_zh`

参考
----

参考页用于查准事实。地图页放在第一项，自动生成的应用程序接口（API）文档保持为参考区最后一项。

.. toctree::
    :maxdepth: 2
    :caption: 参考
    :hidden:

    参考地图 <reference/index_zh>
    reference/cli/index_zh
    reference/dsl/index_zh
    reference/inspect_report/index_zh
    reference/diagnostics_codes/index_zh
    reference/simulation/index_zh
    reference/visualization_options/index_zh
    reference/template_config/index_zh
    reference/grammar_tooling/index_zh
    reference/builtin_templates/index_zh
    应用程序接口文档 <api_doc_zh>

* :doc:`参考地图 <reference/index_zh>`
* :doc:`reference/cli/index_zh`
* :doc:`reference/dsl/index_zh`
* :doc:`reference/inspect_report/index_zh`
* :doc:`reference/diagnostics_codes/index_zh`
* :doc:`reference/simulation/index_zh`
* :doc:`reference/visualization_options/index_zh`
* :doc:`reference/template_config/index_zh`
* :doc:`reference/grammar_tooling/index_zh`
* :doc:`reference/builtin_templates/index_zh`
* :doc:`应用程序接口文档 <api_doc_zh>`

版本说明
-------------------------

.. toctree::
    :maxdepth: 1
    :caption: 版本说明
    :hidden:

    release_notes_zh

* :doc:`release_notes_zh`

社区和支持
-----------------------

* **GitHub 仓库**：https://github.com/HansBug/pyfcstm
* **问题跟踪**：https://github.com/HansBug/pyfcstm/issues
* **PyPI 包**：https://pypi.org/project/pyfcstm/

许可证
---------

pyfcstm 在 Apache License 2.0 下发布。详情请参阅 LICENSE 文件。
