.. _sec-explanations-template-rendering-zh:

模板渲染解释
============

渲染器（renderer）把已经验证的状态机模型变成生成文件树。它刻意只是中间层：它不解析 DSL 文本，不拥有目标语言运行时语义，也不认证本机部署配置。它的职责是把一个 ``StateMachine`` 模型和一个受信任模板目录组合起来。

生成时有两条链路汇合：

* **用户输入链路**：FCSTM DSL 文本 → AST → ``StateMachine`` 模型 → 渲染器 → 生成文件；
* **模板资产链路**：仓库 ``templates/`` 源码 → 打包 → ``pyfcstm/template/index.json`` 与归档 → 解包 → 渲染器。

这两条链路故意分开。内置模板（built-in template）和自定义模板（custom template）在获得普通模板目录后会共享同一个 ``StateMachineCodeRenderer``，但它们的稳定边界不同。

渲染流程
--------

生成路径如下：

1. ``pyfcstm generate`` 读取并解码 FCSTM 文件。
2. 解析器构建 DSL AST 节点。
3. 模型导入器构建已验证的 ``StateMachine``。
4. 对 ``--template <name>``，``pyfcstm.template.extract_template()`` 会把打包内置模板解包到临时目录。
5. 对 ``-t`` / ``--template-dir``，直接使用用户提供的目录。
6. ``StateMachineCodeRenderer`` 读取 ``config.yaml``，校验受支持分节，并准备 Jinja2 环境。
7. 渲染器遍历模板文件：``*.j2`` 文件被渲染，其他未忽略文件被复制，``config.yaml`` 自身被跳过。
8. 生成目录交给目标语言用户构建、导入或检查。

.. figure:: render_flow.puml.svg

   从 DSL 输入到生成文件的渲染流程。

内置模板和自定义模板边界
------------------------

内置模板是打包资产。稳定用户路径是 ``pyfcstm generate --template python`` 或其他已列出的内置名。仓库 ``templates/`` 目录是维护者源码，不是普通用户入口。

自定义模板是通过 ``-t`` / ``--template-dir`` 提供的受信任目录。它可以通过 ``config.yaml`` 注册导入、过滤器和测试器。这足以支持项目本地代码生成，但它不是不可信模板沙箱。

.. figure:: architecture.puml.svg

   渲染器组件及其责任边界。

渲染器负责什么、不负责什么
--------------------------

.. list-table:: 责任边界
   :header-rows: 1

   * - 领域
     - 渲染器负责
     - 模板或目标侧负责
   * - 文件树
     - ``.j2`` 渲染、静态复制、忽略规则、目录创建。
     - 生成文件名、目标构建布局、生成 README 文案。
   * - 配置
     - 接受的 ``config.yaml`` 键、校验、辅助对象注册。
     - 目标运行时需要哪些辅助对象。
   * - 表达式和语句
     - 语言无关渲染器和样式扩展点。
     - 选择目标样式、作用域命名和临时变量声明。
   * - 运行时应用程序接口（API）
     - 不决定目标接口。
     - Python 类、C 头文件接口、C++ 包装层、轮询回调。
   * - 证据
     - 渲染成功和源文件映射。
     - 格式化器、编译器、运行时冒烟检查和语义对齐声明。

这种分层让渲染器保持小而清晰，也让模板可以演进目标接口，而不把渲染器变成跨语言运行时框架。

Jinja 环境
----------

基础环境包含 ``normalize``、``to_identifier``、``indent``、若干 Python 内置对象（builtins）、``INIT_STATE`` 和 ``EXIT_STATE`` 等便利过滤器和全局变量。渲染器随后按配置样式加入 ``expr_render``、``stmt_render`` 和 ``stmts_render``。模板还可以通过 ``config.yaml`` 添加 ``globals``、``filters`` 和 ``tests``。

C 家族辅助函数由 C 家族模板通过 ``type: import`` 显式注册。它们不是每个模板的默认全局对象。这样 C 命名和 C 运行时代码体生成规则会保留在各模板自己的配置中。

表达式与语句渲染
----------------

.. figure:: model.puml.svg

   模型对象为模板提供语言无关输入。

表达式是 guard、赋值值和其他表达式节点。操作语句是生命周期动作和转换 effect 中的赋值与 ``if`` 块。运行时模板应使用目标渲染器：

.. code-block:: jinja

   {{ transition.guard | expr_render(style='c_scope_expr') }}
   {{ action.operations | stmts_render(style='c_runtime') }}

旧辅助函数用途不同：

.. list-table:: 语句辅助函数选择
   :header-rows: 1

   * - 辅助函数
     - 输出意图
     - 正确用途
   * - ``stmt_render`` / ``stmts_render``
     - 目标语言可执行语句。
     - 生成运行时源码。
   * - ``operation_stmt_render`` / ``operation_stmts_render``
     - DSL 文本回显。
     - 注释、调试输出和文档片段。

一个具体反例：用 ``operation_stmt_render`` 渲染 ``counter = counter + 1;`` 会得到 DSL 形状文本。它不是 Python 运行时代码需要的 ``scope['counter']``，也不是 C 运行时代码需要的 ``scope->counter``。生成会执行的代码时，要用运行时语句渲染器。

逻辑应该放在哪里
----------------

.. list-table:: 逻辑归位指南
   :header-rows: 1

   * - 逻辑类型
     - 推荐位置
     - 原因
   * - 目标运行时行为
     - 生成源码和目标语言钩子。
     - 用户可以检查并测试将要交付的产物。
   * - 重复模板结构
     - Jinja macro 或 include。
     - 让布局复用留在模板内部。
   * - 命名和格式化辅助
     - 模板本地全局变量、过滤器或测试器。
     - 目标约定在 ``config.yaml`` 中可见。
   * - 跨模板渲染器行为
     - 生产渲染器代码和测试。
     - 共享行为需要正常接口评审。
   * - 维护者流程
     - 模板维护者 README 和工具检查。
     - 保持用户输出聚焦在集成上。

.. figure:: core_component.puml.svg

   核心渲染器组件和扩展点。

证据边界
--------

生成文档应说明每个声明背后的证据：

.. list-table:: 证据边界
   :header-rows: 1

   * - 声明
     - 证据
     - 不要夸大
   * - 生成可用
     - 命令成功退出且文件存在。
     - 仅创建文件不证明运行时行为。
   * - Python 输出可用
     - 生成类可导入，周期冒烟检查可运行。
     - 不覆盖每个语义样例。
   * - 本机输出可编译
     - 具体编译器 / CMake 冒烟检查成功。
     - 不是对所有工业或嵌入式编译器的认证。
   * - 模拟器等价
     - 对齐测试把 trace 与 ``SimulationRuntime`` 比较。
     - 必须说明样例覆盖和目标特定排除项。
   * - 输出适合格式化
     - 相应格式化器接受代表性输出。
     - 格式化不能压过语义或兼容性。

生成 README 是这条证据链的一部分。参考页给通用契约；生成 README 给出单个模型的机器专属接口 和构建事实。
