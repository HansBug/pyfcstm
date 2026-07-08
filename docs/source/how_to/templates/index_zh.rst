.. _sec-how-to-templates-zh:

模板作者任务指南
================

当你正在编写、调试或审查自定义模板目录时，使用本指南。只想生成代码时，请使用 :doc:`../generation/index_zh` 和打包内置模板。需要精确 ``config.yaml`` 事实时，请查 :doc:`../../reference/template_config/index_zh`。

自定义模板目录是受信任项目代码。``type: import`` 可以加载生成进程可见的 Python 对象，因此不要渲染不可信模板目录。

创建最小可用模板
----------------

模板目录需要 ``config.yaml`` 和至少一个输出文件。以 ``.j2`` 结尾的文件会通过 Jinja2 渲染；其他未忽略文件会作为静态资源复制。

.. code-block:: text

   my_template/
   ├── config.yaml
   ├── machine_summary.txt.j2
   └── static_note.txt

空配置是合法的：

.. code-block:: yaml

   {}

第一个渲染文件可以先检查模型对象和状态路径：

.. code-block:: jinja

   Machine: {{ model.root_state.name }}
   States:
   {%- for state in model.walk_states() %}
   - {{ state.path | join('.') }}
   {%- endfor %}

用教程模型渲染：

.. code-block:: bash

   pyfcstm generate \
       -i docs/source/tutorials/generation/simple_machine.fcstm \
       -t my_template \
       -o /tmp/pyfcstm-template-check \
       --clear

成功信号是生成 ``machine_summary.txt``，并复制 ``static_note.txt``。这只证明渲染器可以消费该模板；不证明目标语言运行时语义。

理解文件映射
------------

.. list-table:: 文件映射规则
   :header-rows: 1

   * - 模板源码
     - 输出行为
     - 例子
   * - ``*.j2``
     - 通过 Jinja2 渲染，并去掉最后的 ``.j2`` 后缀写出。
     - ``src/machine.py.j2`` 变成 ``src/machine.py``。
   * - 非 ``.j2`` 文件
     - 除非被忽略或等于 ``config.yaml``，否则按字节复制。
     - ``LICENSE`` 仍是 ``LICENSE``。
   * - ``config.yaml``
     - 被渲染器读取，不复制到输出。
     - 生成器配置不进入生成用户文件。
   * - 被忽略路径
     - 不渲染也不复制。
     - ``ignores: ['README.md']`` 会把维护者 README 留在输出之外。

渲染器总会把 ``.git`` 加入输入模板忽略列表。这不会保护输出目录免受 ``--clear`` 影响；清理是输出侧操作。

添加表达式和语句样式
--------------------

表达式和操作块是模型对象，不是目标语言文本。模板选择如何把它们渲染出去：

.. code-block:: yaml

   expr_styles:
     py_runtime_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

   stmt_styles:
     py_runtime_stmt:
       base_lang: python
       expr_lang: python
       state_var_target: "scope[{{ name | tojson }}]"
       temp_var_target: "{{ name }}"

在 ``.j2`` 文件中使用过滤器：

.. code-block:: jinja

   guard = {{ transition.guard | expr_render(style='py_runtime_expr') }}
   {{ action.operations | stmts_render(style='py_runtime_stmt') }}

生成可执行运行时代码时使用 ``stmt_render`` / ``stmts_render``。只有想输出 DSL 文本回显，用于注释、文档或调试时，才使用 ``operation_stmt_render`` / ``operation_stmts_render``。例如 DSL effect ``counter = counter + 1;`` 经过 ``operation_stmt_render`` 后仍是 DSL 形状，不是期望 ``scope[...]`` 访问的 Python 运行时赋值代码。

通过 ``config.yaml`` 注册辅助对象
-------------------------------------

``globals``、``filters`` 和 ``tests`` 共用对象加载形式。它们可以把重复命名和格式化逻辑移出很长的 Jinja 表达式。

.. list-table:: 对象加载形式
   :header-rows: 1

   * - 形式
     - 示例
     - 结果
   * - 带 ``params`` 的 ``type: template``
     - ``params: [state]`` 和 ``template: "{{ state.path | join('.') }}"``
     - 返回一个可调用对象（callable），位置参数会映射到 ``params``。
   * - 不带 ``params`` 的 ``type: template``
     - ``template: "{{ model.root_state.name }}"``
     - 返回 Jinja 模板的 ``render`` 可调用对象。
   * - ``type: import``
     - ``from: pyfcstm.utils.to_c_identifier``
     - 为受信任模板导入 Python 对象。
   * - ``type: value``
     - ``value: 4``
     - 注册字面值。
   * - 未知 ``type``
     - ``{prefix: Demo}``
     - 把剩余映射原样注册。

C 家族模板会显式导入 ``to_c_identifier``、``to_c_path_identifier``、``to_c_public_identifier``、``render_c_action_body`` 和 ``render_c_condition_body`` 等辅助对象。这些对象不会默认注入每个渲染器环境。

把目标运行时行为留在生成代码里
------------------------------

模板逻辑应放在便于评审的位置：

.. list-table:: 逻辑归位
   :header-rows: 1

   * - 逻辑类型
     - 推荐位置
     - 原因
   * - 目标运行时行为
     - 生成的目标语言源码和目标语言钩子。
     - 用户可以检查输出并运行目标侧检查。
   * - 重复文件结构
     - Jinja 宏（macro）或包含指令（include）。
     - 保持模板可读，不把行为移入 Python 回调。
   * - 命名和格式化辅助
     - 模板本地 ``globals`` / ``filters`` / ``tests``。
     - 约定在 ``config.yaml`` 中显式可见。
   * - 跨模板渲染器行为
     - 带测试的 ``pyfcstm/render/`` 生产代码。
     - 共享行为需要正常 Python 评审和回归覆盖。
   * - 维护者工作流规则
     - ``templates/README*.md`` 和模板测试。
     - 它们不是生成用户输出。

验证自定义模板
--------------

按声明逐步加强检查：

.. list-table:: 自定义模板验证矩阵
   :header-rows: 1

   * - 层级
     - 何时需要
     - 成功信号
     - 边界
   * - 渲染器冒烟检查
     - 每个自定义模板。
     - 小 ``.fcstm`` 可渲染，``*.j2`` 输出出现，静态文件复制，忽略规则生效。
     - 只证明渲染器兼容性。
   * - 格式化器
     - 生成目标语言源码会给用户使用。
     - 代表性输出在目标格式化器下稳定。
     - 风格质量门，不是语义证明。
   * - 编译器 / 本机冒烟检查
     - 生成本机源码应可编译。
     - 当前工具链能配置、构建并运行小驱动。
     - 仅是具体工具链证据。
   * - 运行时冒烟检查
     - 生成输出暴露可执行运行时行为。
     - 最小消费者能构造机器并执行周期。
     - 不覆盖全部 FCSTM 语义。
   * - 模拟器对齐
     - 模板声称与 ``SimulationRuntime`` 等价。
     - 共享语义样例或追踪与模拟器一致。
     - 必须说明事件模型排除项和覆盖范围。

排查模板作者常见失败
--------------------

.. list-table:: 模板作者排查表
   :header-rows: 1

   * - 失败
     - 检查什么
     - 常见修复
   * - ``config.yaml`` 顶层键未知
     - 渲染器错误中的具体键。
     - 把值移动到 ``expr_styles``、``stmt_styles``、``globals``、``filters``、``tests`` 或 ``ignores`` 之一。
   * - 样式条目缺 ``base_lang``
     - ``expr_styles.<name>`` 或 ``stmt_styles.<name>``。
     - 添加 ``python`` 或 ``c`` 等规范基准样式。
   * - 辅助导入失败
     - ``from`` 路径和已安装 Python 环境。
     - 使用公开导入路径，或把辅助对象放在生成时可见的项目代码中。
   * - 静态文件意外复制
     - ``ignores`` 规则和路径拼写。
     - 添加 gitignore 风格规则；记住 ``config.yaml`` 会单独跳过。
   * - 输出目录丢了无关文件
     - 是否使用 ``--clear``。
     - 渲染到临时目录；需要保留文件时不要使用 ``--clear``。

作者任务卡
----------

下面的卡片把自定义模板指南变成可评审任务。新建模板或检查操作指南示例时，用它们确认示例不是孤立片段。

.. list-table:: 模板作者任务卡
   :header-rows: 1

   * - 任务
     - 输入
     - 输出或成功信号
     - 第一排查步骤
   * - 渲染一个文本文件。
     - ``config.yaml`` 加 ``machine_summary.txt.j2``。
     - 输出目录出现 ``machine_summary.txt``，其中有模型名。
     - 若文件缺失，确认源文件确实以 ``.j2`` 结尾且没有被忽略。
   * - 复制静态文件。
     - 非 ``.j2`` 文件，例如 ``static_note.txt``。
     - 输出目录出现相同字节。
     - 若文件意外复制，检查 ``ignores``；记住 ``config.yaml`` 会单独跳过。
   * - 渲染嵌套输出路径。
     - ``src/machine.py.j2`` 或 ``include/machine.h.j2``。
     - 父目录被创建，最终后缀被移除。
     - 若目录不存在，先缩减到单个嵌套文件，再加入宏。
   * - 添加目标表达式样式。
     - ``config.yaml`` 中的 ``expr_styles.<name>.base_lang``。
     - ``{{ guard | expr_render(style='<name>') }}`` 输出目标语法。
     - 若校验拒绝样式，检查样式值是否为映射并包含 ``base_lang``。
   * - 添加目标语句样式。
     - ``stmt_styles.<name>.base_lang`` 加 ``assign`` 等覆盖项。
     - ``stmts_render`` 输出目标侧可执行赋值或 ``if`` 块。
     - 若输出仍像 DSL，检查是否误用了 ``operation_stmt_render``。
   * - 注册过滤器。
     - ``filters.<name>: {type: import, from: package.module.object}``。
     - 模板可调用 ``{{ value | name }}``。
     - 若导入失败，在生成环境中用 Python 运行同一个 import。
   * - 注册字面值。
     - ``globals.project_name: {type: value, value: Demo}``。
     - ``{{ project_name }}`` 输出配置值。
     - 若得到的是映射，检查 ``type`` 是否缺失或拼错。
   * - 注册模板可调用对象。
     - ``type: template``，可带 ``params``。
     - 重复格式化逻辑进入可调用对象，不写成长行 Jinja。
     - 若参数绑定异常，分别测试位置参数和关键字参数。
   * - 证明模板没有隐藏运行时行为。
     - 生成源码加短消费者或编译冒烟检查。
     - 运行时行为在目标语言输出和钩子里可见。
     - 若行为只在 Python 辅助导入中，移入生成代码，或说明它只是维护者内部逻辑。

最小调试流程
------------

自定义模板失败时，按渲染器实际顺序调试：

1. 先用 ``pyfcstm inspect`` 等普通命令校验输入 FCSTM 模型。
2. 再按 :doc:`../../reference/template_config/index_zh` 校验 ``config.yaml`` 形状。
3. 缩减到一个 ``*.j2`` 文件和一个静态文件。
4. 依次加入表达式渲染、语句渲染、导入辅助对象。
5. 渲染冒烟检查通过后，再跑格式化器、编译器、运行时或语义对齐检查。

这个顺序能避免编译错误掩盖渲染错误，也避免渲染错误掩盖无效模型。

可运行微型模板形状
------------------

短作者示例应能放在一个屏幕内。把项目特定逻辑留在正文外，并明确写出成功信号：

.. code-block:: text

   my_template/
     config.yaml
     machine_summary.txt.j2
     static_note.txt

.. code-block:: yaml

   expr_styles:
     py_expr:
       base_lang: python

.. code-block:: jinja

   model={{ model.root_state.name }}
   states={{ model.walk_states() | list | length }}

成功信号是渲染出的 ``machine_summary.txt`` 和复制出的 ``static_note.txt``。这个例子证明文件映射和命名表达式样式可以加载；它不证明生成运行时正确。

辅助对象设计检查表
------------------

.. list-table:: 辅助对象归位检查表
   :header-rows: 1

   * - 问题
     - 好答案
     - 高风险答案
   * - 辅助对象只是命名或格式化吗？
     - 注册成本地过滤器或全局变量，并用渲染冒烟覆盖。
     - 把目标运行时语义藏进用户不可见的 Python 辅助对象。
   * - 辅助对象会输出 C 家族运行时代码体吗？
     - 复用 ``pyfcstm/render/c_runtime.py`` 的事实，并记录目标配置。
     - 用没有测试的临时 Jinja 字符串重新实现 C 作用域修改。
   * - 辅助对象依赖主机环境变量吗？
     - 视为项目特定契约，并记录变量含义。
     - 依赖开发者 shell 变量且没有兜底。
   * - 辅助对象跨多个内置模板吗？
     - 把共享行为放入经过评审且有测试的渲染器代码。
     - 在多个模板里复制会漂移的版本。

应保留的验证记录
----------------

模板作者变更需要在适用时报告这些记录：

* 渲染器冒烟命令，以及它生成的文件；
* 格式化命令，以及被检查的代表性文件；
* 编译器或本机冒烟命令，或缺失工具的确切原因；
* 运行时冒烟命令和观测输出片段；
* 声称语义等价时的模拟器对齐命令；
* 简短说明 ``operation_stmt_render`` 没有用于可执行运行时代码体。
