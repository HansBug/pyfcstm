.. _sec-reference-template-config-zh:

模板配置参考
============

本页是模板（template） ``config.yaml`` 和渲染器（renderer）侧模板目录行为的查准规格。维护模板目录或诊断渲染失败时使用它。任务流程见 :doc:`../../how_to/templates/index_zh`；设计理由见 :doc:`../../explanations/template_rendering/index_zh`。


.. template-config-marker: top-level-key expr_styles
.. template-config-marker: top-level-key stmt_styles
.. template-config-marker: top-level-key globals
.. template-config-marker: top-level-key filters
.. template-config-marker: top-level-key tests
.. template-config-marker: top-level-key ignores
.. template-config-marker: validation yaml-parse-error
.. template-config-marker: validation empty-file
.. template-config-marker: validation root-not-mapping
.. template-config-marker: validation unknown-top-level-key
.. template-config-marker: validation expr-styles-not-mapping
.. template-config-marker: validation stmt-styles-not-mapping
.. template-config-marker: validation globals-not-mapping
.. template-config-marker: validation filters-not-mapping
.. template-config-marker: validation tests-not-mapping
.. template-config-marker: validation expr-style-not-mapping
.. template-config-marker: validation expr-style-missing-base-lang
.. template-config-marker: validation stmt-style-not-mapping
.. template-config-marker: validation stmt-style-missing-base-lang
.. template-config-marker: validation ignores-not-list
.. template-config-marker: validation ignores-item-not-string
.. template-config-marker: validation object-template-missing-template
.. template-config-marker: validation object-import-missing-from
.. template-config-marker: validation object-value-missing-value
.. template-config-marker: validation object-import-target-failure
.. template-config-marker: style-name dsl
.. template-config-marker: style-name c
.. template-config-marker: style-name cpp
.. template-config-marker: style-name python
.. template-config-marker: style-name java
.. template-config-marker: style-name js
.. template-config-marker: style-name ts
.. template-config-marker: style-name rust
.. template-config-marker: style-name go
.. template-config-marker: style-alias py=python
.. template-config-marker: style-alias python3=python
.. template-config-marker: style-alias c++=cpp
.. template-config-marker: style-alias cxx=cpp
.. template-config-marker: style-alias cc=cpp
.. template-config-marker: style-alias javascript=js
.. template-config-marker: style-alias node=js
.. template-config-marker: style-alias nodejs=js
.. template-config-marker: style-alias typescript=ts
.. template-config-marker: style-alias rustlang=rust
.. template-config-marker: style-alias rs=rust
.. template-config-marker: style-alias golang=go
.. template-config-marker: stmt-field base_lang
.. template-config-marker: stmt-field expr_lang
.. template-config-marker: stmt-field expr_templates
.. template-config-marker: stmt-field state_var_target
.. template-config-marker: stmt-field temp_var_target
.. template-config-marker: stmt-field assign
.. template-config-marker: stmt-field declare_temp
.. template-config-marker: stmt-field temp_type_aliases
.. template-config-marker: stmt-field temp_type_fallback
.. template-config-marker: stmt-field if
.. template-config-marker: stmt-field elif
.. template-config-marker: stmt-field else
.. template-config-marker: stmt-field block_end
.. template-config-marker: stmt-field pass
.. template-config-marker: helper INIT_STATE
.. template-config-marker: helper EXIT_STATE
.. template-config-marker: helper expr_render
.. template-config-marker: helper stmt_render
.. template-config-marker: helper stmts_render
.. template-config-marker: helper _stmt_default_state_vars
.. template-config-marker: helper _stmt_default_var_types
.. template-config-marker: helper operation_stmt_render
.. template-config-marker: helper operation_stmts_render
.. template-config-marker: helper normalize
.. template-config-marker: helper to_identifier
.. template-config-marker: helper indent
.. template-config-marker: helper builtins
.. template-config-marker: helper environment-variables
.. template-config-marker: helper render_c_action_body
.. template-config-marker: helper render_c_condition_body
.. template-config-marker: helper render_c_reset_vars_body
.. template-config-marker: helper to_c_identifier
.. template-config-marker: helper to_c_path_identifier
.. template-config-marker: helper to_c_public_identifier
.. template-config-marker: helper to_c_public_macro_identifier
.. template-config-marker: helper is_c_public_identifier_reserved
.. template-config-marker: object-form template-with-params
.. template-config-marker: object-form template-without-params
.. template-config-marker: object-form import
.. template-config-marker: object-form value
.. template-config-marker: object-form unknown-type
.. template-config-marker: object-form no-type
.. template-config-marker: object-form non-dict
.. template-config-marker: file-mapping j2-render
.. template-config-marker: file-mapping static-copy
.. template-config-marker: file-mapping config-samefile-skip
.. template-config-marker: file-mapping git-ignore-input-only
.. template-config-marker: file-mapping ignores-gitwildmatch
.. template-config-marker: file-mapping nested-output-dirs
.. template-config-marker: file-mapping utf8-lf-render
.. template-config-marker: file-mapping static-copy-bytes
.. template-config-marker: file-mapping clear-symlink-unlink
.. template-config-marker: file-mapping clear-file-remove
.. template-config-marker: file-mapping clear-directory-rmtree
.. template-config-marker: file-mapping clear-other-warning

文件契约
--------

模板目录可以包含 ``config.yaml``。渲染器会先读取它，再遍历文件。空文件和只有注释的文件会按空映射（mapping）处理。若没有提供 ``expr_styles.default`` 或 ``stmt_styles.default``，渲染器会创建默认 DSL 样式。

只接受这些顶层键：

.. list-table:: ``config.yaml`` 顶层键
   :header-rows: 1

   * - 键
     - 类型
     - 含义
   * - ``expr_styles``
     - 映射
     - 注册 ``expr_render`` 使用的表达式渲染样式。
   * - ``stmt_styles``
     - 映射
     - 注册 ``stmt_render`` 和 ``stmts_render`` 使用的操作语句渲染样式。
   * - ``globals``
     - 映射
     - 通过 ``process_item_to_object`` 添加 Jinja2 全局变量。
   * - ``filters``
     - 映射
     - 通过同一对象加载机制添加 Jinja2 过滤器。
   * - ``tests``
     - 映射
     - 通过同一对象加载机制添加 Jinja2 测试器。
   * - ``ignores``
     - 字符串列表
     - 用 GitWildMatch 风格模式排除输入模板文件。

校验失败
--------

非法配置会快速失败。错误信息会尽量包含配置文件路径和失败键形状。

.. list-table:: 校验分支
   :header-rows: 1

   * - 标记
     - 非法形状
     - 最小反例
   * - ``yaml-parse-error``
     - YAML 语法无法解析。
     - ``expr_styles: [``
   * - ``empty-file``
     - 空文件或只有注释的文件。
     - 按 ``{}`` 接受；不是失败。
   * - ``root-not-mapping``
     - 根值不是映射。
     - ``[]``
   * - ``unknown-top-level-key``
     - 根中有不在允许集合内的键。
     - ``unknown: true``
   * - ``expr-styles-not-mapping``
     - ``expr_styles`` 不是映射。
     - ``expr_styles: []``
   * - ``stmt-styles-not-mapping``
     - ``stmt_styles`` 不是映射。
     - ``stmt_styles: []``
   * - ``globals-not-mapping``
     - ``globals`` 不是映射。
     - ``globals: []``
   * - ``filters-not-mapping``
     - ``filters`` 不是映射。
     - ``filters: []``
   * - ``tests-not-mapping``
     - ``tests`` 不是映射。
     - ``tests: []``
   * - ``expr-style-not-mapping``
     - 某个表达式样式条目不是映射。
     - ``expr_styles: {py: python}``
   * - ``expr-style-missing-base-lang``
     - 某个表达式样式缺 ``base_lang``。
     - ``expr_styles: {py: {Name: x}}``
   * - ``stmt-style-not-mapping``
     - 某个语句样式条目不是映射。
     - ``stmt_styles: {py: python}``
   * - ``stmt-style-missing-base-lang``
     - 某个语句样式缺 ``base_lang``。
     - ``stmt_styles: {py: {assign: x}}``
   * - ``ignores-not-list``
     - ``ignores`` 是字符串或其他非列表值。
     - ``ignores: '*.tmp'``
   * - ``ignores-item-not-string``
     - 某个忽略项不是字符串。
     - ``ignores: [123]``

当对象加载形式不完整或无法导入时，也会失败：

.. list-table:: 对象加载失败形状
   :header-rows: 1

   * - 标记
     - 非法形状
     - 结果
   * - ``object-template-missing-template``
     - ``type: template`` 缺 ``template``。
     - 加载器抛出 ``KeyError``。
   * - ``object-import-missing-from``
     - ``type: import`` 缺 ``from``。
     - 加载器抛出 ``KeyError``。
   * - ``object-value-missing-value``
     - ``type: value`` 缺 ``value``。
     - 加载器抛出 ``KeyError``。
   * - ``object-import-target-failure``
     - ``from`` 指向不可用对象。
     - ``quick_import_object`` 抛出导入失败。

表达式样式
----------

表达式样式把模板本地样式名映射到规范表达式渲染器。每个样式条目都必须包含 ``base_lang``。额外键会为该样式覆盖或扩展节点模板。

.. code-block:: yaml

   expr_styles:
     c_scope_expr:
       base_lang: c
       Name: "scope->{{ node.name | to_c_identifier }}"

模板中这样使用：

.. code-block:: jinja

   {{ transition.guard | expr_render(style='c_scope_expr') }}

规范样式名和别名是精确集合：

.. list-table:: 样式名和别名
   :header-rows: 1

   * - 规范名
     - 别名
   * - ``dsl``
     - 无
   * - ``c``
     - 无
   * - ``cpp``
     - ``c++``、``cxx``、``cc``
   * - ``python``
     - ``py``、``python3``
   * - ``java``
     - 无
   * - ``js``
     - ``javascript``、``node``、``nodejs``
   * - ``ts``
     - ``typescript``
   * - ``rust``
     - ``rustlang``、``rs``
   * - ``go``
     - ``golang``

语句样式
--------

语句样式渲染操作块中的赋值和 ``if`` 块。它同样需要 ``base_lang``，并可以设置这些字段：

.. list-table:: ``stmt_styles`` 字段
   :header-rows: 1

   * - 字段
     - 含义
   * - ``base_lang``
     - 起点规范语句语言。
   * - ``expr_lang``
     - 语句内部使用的表达式渲染器。
   * - ``expr_templates``
     - 限定在语句渲染中的表达式模板覆盖。
   * - ``state_var_target``
     - 持久变量读写目标的 Jinja 模板。
   * - ``temp_var_target``
     - 块内临时变量名的 Jinja 模板。
   * - ``assign``
     - 赋值语句模板。
   * - ``declare_temp``
     - 临时变量首次出现时可选的声明模板。
   * - ``temp_type_aliases``
     - 把 ``int`` / ``float`` 等推断 DSL 类型映射到目标类型。
   * - ``temp_type_fallback``
     - 无法推断时使用的兜底类型。
   * - ``if`` / ``elif`` / ``else`` / ``block_end`` / ``pass``
     - 条件块和空分支模板。

渲染器提供这些辅助签名：

.. code-block:: text

   stmt_render(node, style='default', state_vars=None, var_types=None,
               visible_names=None, visible_var_types=None,
               indent='    ', level=0)

   stmts_render(nodes, style='default', state_vars=None, var_types=None,
                visible_names=None, visible_var_types=None,
                indent='    ', level=0, sep='\n')

完整 ``StateMachine`` 渲染期间，``state_vars`` 和 ``var_types`` 默认来自渲染器注入的模型变量。``visible_names`` 和 ``visible_var_types`` 描述当前可见的临时变量。``sep`` 控制多条语句的拼接方式：

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python_runtime', sep='\n') }}

运行时语句渲染器与 DSL 回显渲染器
----------------------------------

.. list-table:: 语句辅助函数区别
   :header-rows: 1

   * - 辅助函数
     - 契约
     - 不要用于
   * - ``stmt_render`` / ``stmts_render``
     - 渲染目标语言可执行语句。
     - 原始 DSL 回显片段。
   * - ``operation_stmt_render`` / ``operation_stmts_render``
     - 从操作语句渲染 DSL 形状文本。
     - 必须在 Python、C 或其他目标语言中执行的运行时源码。

反例：DSL effect ``counter = counter + 1;`` 用 ``operation_stmt_render`` 渲染后仍是 ``counter = counter + 1;``。Python 运行时样式可能需要 ``scope['counter'] = scope['counter'] + 1``；C 运行时样式可能需要 ``scope->counter = scope->counter + 1;``。

对象加载形式
------------

``globals``、``filters`` 和 ``tests`` 都通过 ``process_item_to_object`` 处理值。

.. list-table:: 对象加载形式
   :header-rows: 1

   * - 形式
     - YAML 形状
     - 注册对象
   * - ``template-with-params``
     - ``type: template`` 加 ``params`` 和 ``template``。
     - 可调用对象（callable），把位置参数映射到 ``params`` 并合并关键字参数。
   * - ``template-without-params``
     - ``type: template`` 加 ``template``。
     - Jinja 模板 ``render`` 可调用对象。
   * - ``import``
     - ``type: import`` 加 ``from``。
     - 导入的 Python 对象。
   * - ``value``
     - ``type: value`` 加 ``value``。
     - 字面值。
   * - ``unknown-type`` / ``no-type``
     - 带未知或缺失 ``type`` 的映射。
     - ``type`` 被弹出后的剩余映射，或原映射。
   * - ``non-dict``
     - 配置分节下的任意非映射值，包括标量、列表和 ``null``。
     - 原样返回。

C 家族模板使用 ``type: import`` 注册 ``render_c_action_body``、``render_c_condition_body``、``render_c_reset_vars_body``、``to_c_identifier``、``to_c_path_identifier``、``to_c_public_identifier``、``to_c_public_macro_identifier`` 和 ``is_c_public_identifier_reserved``。

Jinja 环境辅助对象
-----------------------

默认环境包含：

* 状态常量：``INIT_STATE`` 和 ``EXIT_STATE``；
* 渲染辅助：``expr_render``、``stmt_render``、``stmts_render``、``operation_stmt_render`` 和 ``operation_stmts_render``；
* 文本辅助：``normalize``、``to_identifier`` 和 ``indent``；``normalize`` 使用 ``unidecode`` 先转写 Unicode 文本再清理标识符，所以接收非 ASCII 机器名的模板应测试生成标识符；
* 渲染期语句默认值：``_stmt_default_state_vars`` 和 ``_stmt_default_var_types`` 只在完整 ``StateMachine`` 渲染期间注入，分别提供持久变量名和变量类型；当 ``stmt_render`` / ``stmts_render`` 省略 ``state_vars`` / ``var_types`` 参数时会使用它们；
* 常用 Python 内置对象（builtins），它们会注册为过滤器、测试器或全局变量，包括 ``str``、``set``、``dict``、``keys``、``values``、``enumerate``、``reversed`` 和 ``filter``；
* ``os.environ`` 中所有不与现有 Jinja 全局变量冲突的操作系统环境变量，作为全局变量注入。

环境变量是受控构建环境中的便利项，不是秘密边界：受信任模板可以读取生成进程可见的任意非冲突环境变量。可移植模板不应依赖主机特定值，除非使用该自定义模板的项目明确记录了这种契约。

文件映射、忽略和清理语义
------------------------

.. list-table:: 渲染器文件行为
   :header-rows: 1

   * - 行为
     - 契约
   * - ``j2-render``
     - ``*.j2`` 文件渲染到相同相对路径，并去掉最后后缀。
   * - ``static-copy``
     - 非模板文件通过 ``shutil.copyfile`` 复制，保留字节。
   * - ``config-samefile-skip``
     - ``config.yaml`` 通过 ``os.path.samefile(current_file, self.config_file)`` 跳过。
   * - ``git-ignore-input-only``
     - 扫描模板输入时总是忽略 ``.git``。
   * - ``ignores-gitwildmatch``
     - ``ignores`` 通过 ``pathspec`` 使用 GitWildMatch 风格模式。
   * - ``nested-output-dirs``
     - 嵌套输出路径会创建父目录。
   * - ``utf8-lf-render``
     - 渲染文本以 UTF-8 和 ``newline='\n'`` 写出。
   * - ``static-copy-bytes``
     - 静态资产按字节复制。
   * - ``clear-symlink-unlink`` / ``clear-file-remove`` / ``clear-directory-rmtree``
     - 输出清理会 unlink 符号链接、删除文件、递归删除目录。
   * - ``clear-other-warning``
     - 其他文件类型走防御性警告路径。

``.git`` 输入忽略不会保护输出目录。如果 ``--clear`` 指向某个工作树，渲染器会按输出清理规则处理该目录。

内置配置例子
------------

内置模板也使用同一套契约：

* ``python`` 定义 Python 表达式和语句样式，以及生成钩子命名辅助。
* ``c`` 和 ``c_poll`` 定义 C 作用域表达式渲染、C 运行时语句渲染、C 标识符过滤器和 C 运行时代码体辅助。
* ``cpp`` 和 ``cpp_poll`` 复用 C 家族辅助层，同时增加包装层文件；它们的 ``ignores`` 还冗余列出 ``config.yaml``，这是无害的，因为渲染器已经跳过实际配置文件。

合法与非法例子
--------------

下面的例子故意很短。它们展示渲染器接受或拒绝的形状，不是完整生产模板。

.. list-table:: 顶层例子
   :header-rows: 1

   * - 场景
     - YAML
     - 结果
   * - 空配置。
     - ``{}``
     - 合法。渲染器使用内置默认值，不增加样式或辅助对象。
   * - 表达式样式。
     - ``expr_styles: {py_expr: {base_lang: python}}``
     - 合法。``py_expr`` 委托给 Python 表达式渲染器。
   * - 语句样式。
     - ``stmt_styles: {py_stmt: {base_lang: python, assign: "{target} = {value}"}}``
     - 合法。覆盖项影响该样式的赋值渲染。
   * - 未知键。
     - ``helpers: {}``
     - 非法。应把值放入 ``globals``、``filters`` 或 ``tests``。
   * - 根不是映射。
     - ``[expr_styles]``
     - 非法。根必须是映射。
   * - 忽略规则形状错误。
     - ``ignores: '*.tmp'``
     - 非法。``ignores`` 必须是字符串列表。

.. list-table:: 样式例子
   :header-rows: 1

   * - 场景
     - YAML
     - 结果
   * - 规范表达式样式。
     - ``expr_styles: {c_expr: {base_lang: c}}``
     - 合法。``c_expr`` 可传给 ``expr_render``。
   * - 别名表达式样式。
     - ``expr_styles: {node_expr: {base_lang: nodejs}}``
     - 合法。别名会解析为 ``js``。
   * - 带表达式语言的语句样式。
     - ``stmt_styles: {c_runtime: {base_lang: c, expr_lang: c_scope_expr}}``
     - 合法，前提是 ``c_scope_expr`` 也定义为表达式样式。
   * - 样式是标量。
     - ``expr_styles: {bad: c}``
     - 非法。每个样式条目必须是映射。
   * - 缺少基准样式。
     - ``stmt_styles: {bad: {assign: "{target} = {value};"}}``
     - 非法。必须有 ``base_lang``。
   * - 未知基准样式。
     - ``expr_styles: {bad: {base_lang: ruby}}``
     - 非法，除非渲染器未来增加 ``ruby`` 基准。

对象加载例子
------------

.. list-table:: 对象加载例子
   :header-rows: 1

   * - 形式
     - YAML
     - 说明
   * - 导入辅助对象。
     - ``filters: {snake: {type: import, from: mypkg.naming.snake}}``
     - 导入对象注册为过滤器。
   * - 保存字面值。
     - ``globals: {project: {type: value, value: demo}}``
     - 字面值可通过 ``project`` 访问。
   * - 带参数的模板可调用对象。
     - ``globals: {banner: {type: template, params: [name], template: "{{ name }}"}}``
     - 位置参数绑定到 ``params``，并与关键字参数合并。
   * - 不带参数的模板可调用对象。
     - ``globals: {banner: {type: template, template: "demo"}}``
     - 可调用对象渲染已配置模板，不做位置参数绑定。
   * - 导入目标失败。
     - ``filters: {missing: {type: import, from: no.such.object}}``
     - 环境构建时非法；修复 Python 导入路径。
   * - 未知 ``type``。
     - ``globals: {x: {type: mystery, value: 1}}``
     - 返回剩余映射；不要把它当成公开模板模式。
   * - 缺少 ``type``。
     - ``globals: {x: {value: 1}}``
     - 映射原样返回；若想表达字面值，应写 ``type: value``。

语句辅助函数例子
----------------

.. list-table:: 语句辅助函数调用
   :header-rows: 1

   * - 调用
     - 用途
     - 边界
   * - ``{{ stmt | stmt_render(style='python') }}``
     - 把单个语句节点渲染成 Python 可执行语法。
     - 输入必须是语句节点，不是任意文本。
   * - ``{{ action.operations | stmts_render(style='c_runtime') }}``
     - 把一组操作节点渲染成目标运行时样式。
     - 持久变量和临时变量上下文会影响输出。
   * - ``{{ action.operations | stmts_render(style='python', sep='\n\n') }}``
     - 使用自定义分隔符渲染。
     - 分隔符只改文本布局，不改语义。
   * - ``{{ action.operations | operation_stmts_render }}``
     - 为文档或注释回显 DSL 形状操作文本。
     - 不要用作可执行运行时源码。

校验分支快速参考
----------------

.. list-table:: 无效形状与修复
   :header-rows: 1

   * - 无效形状
     - 错误家族
     - 修复
   * - YAML 格式错误。
     - YAML 解析错误。
     - 先修正缩进、引号或集合语法，再查渲染器事实。
   * - 只有注释的文件。
     - 合法空配置。
     - 不需要修复；它等同 ``{}``。
   * - ``expr_styles: []``。
     - 分节类型错误。
     - 使用从样式名到样式映射的映射。
   * - ``tests: []``。
     - 分节类型错误。
     - 使用从测试器名称到对象加载项的映射。
   * - ``ignores: [1]``。
     - 忽略项类型错误。
     - 把每个模式写成字符串。
   * - ``type: template`` 缺 ``template``。
     - 对象加载校验。
     - 添加 Jinja 模板字符串。
   * - ``type: import`` 缺 ``from``。
     - 对象加载校验。
     - 添加 Python 对象导入路径。
   * - ``type: value`` 缺 ``value``。
     - 对象加载校验。
     - 添加字面值；若未使用则删除该对象。

破坏性输出例子
--------------

``ignores`` 和 ``.git`` 保护的是模板输入扫描，不保护输出目录。这些是命令层事实：

* 把 ``--clear`` 指向 ``/tmp/generated`` 这类可丢弃目录是合适的；
* 把 ``--clear`` 指向项目源码目录，可能在生成前删除该目录中的文件；
* 静态模板文件保持原始字节，渲染文件以 UTF-8 文本和 LF 换行写出；
* 输出目录中已有符号链接时，清理会 unlink 它，而不是跟随为目录树；
* 防御性 ``clear-other-warning`` 路径用于少见文件类型，不应被写成主要清理行为。
