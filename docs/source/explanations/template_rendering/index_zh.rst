.. _sec-explanations-template-rendering-zh:

模板渲染解释
============

renderer 将已验证的状态机 model 转换为生成文件树。它刻意保持小而清晰：解析、model validation、内置模板解包、Jinja2 渲染和目标语言 runtime 设计是分开的责任。

渲染流程
--------

生成路径如下：

1. CLI 读取 FCSTM DSL 文本。
2. parser 构建 DSL AST nodes。
3. model importer 构建 ``StateMachine``。
4. 如果使用内置模板，``pyfcstm.template`` 先把打包模板资产解包到临时目录。
5. ``StateMachineCodeRenderer`` 读取模板目录中的 ``config.yaml``。
6. renderer 创建 Jinja2 environment，注册表达式与语句 renderer，并遍历模板文件。
7. ``*.j2`` 文件被渲染；其他未忽略文件被复制。

.. figure:: render_flow.puml.svg

   从 DSL 输入到生成文件的渲染流程。

模板目录边界
------------

模板目录描述输出形状。renderer 不决定 runtime API、目标语言命名方案或构建系统；这些属于模板。因此不同内置模板可以暴露不同集成面，同时共享同一个 model 和 renderer。

.. figure:: architecture.puml.svg

   renderer 组件及其责任边界。

``config.yaml`` 扩展 renderer environment。它应描述表达式样式、语句样式、helper filters、helper tests 和忽略文件等 renderer 事实，不应把目标 runtime 语义隐藏在 Python callback 中。

表达式与语句渲染
----------------

model 使用语言无关形式存储表达式和操作语句。模板选择如何把它们渲染为目标语言：

* ``expr_render`` 渲染 guards 和赋值值等表达式对象。
* ``stmt_render`` 渲染单条操作语句。
* ``stmts_render`` 渲染操作语句序列。

.. figure:: model.puml.svg

   model 对象为模板提供语言无关输入。

旧的 ``operation_stmt_render`` helpers 输出 DSL echo 文本。它们适合文档、注释和调试；runtime 代码生成应使用目标语言 statement renderer。

内置模板打包
------------

仓库模板源码位于 ``templates/``。可分发内置模板资产位于 ``pyfcstm/template/``，通过 ``make tpl`` 刷新。CLI 的 ``pyfcstm generate --template <name>`` 会先解包打包资产，再交给与自定义 ``--template-dir`` 相同的 renderer。

这个边界很重要：用户文档应教 ``--template <name>``；仓库 ``templates/`` 是维护者源码树，不是稳定用户入口。

逻辑应该放在哪里
----------------

.. list-table:: 逻辑归位指南
   :header-rows: 1

   * - 逻辑类型
     - 推荐位置
   * - 目标 runtime 行为
     - 生成源码和目标语言 hooks。
   * - 重复文件结构
     - Jinja2 macros 或 includes。
   * - 命名和格式化辅助
     - 模板本地 filters 或 globals，经 ``config.yaml`` 声明。
   * - 跨模板 renderer 行为
     - 带测试的生产 renderer 代码。
   * - 内置模板资产 metadata
     - ``pyfcstm/template`` 打包 metadata 和生成 README 契约。

.. figure:: core_component.puml.svg

   核心 renderer 组件和扩展点。

最小可维护模板会让这些层次保持显式，从而让输出更易 review、测试更易编写、下游集成更少意外。
