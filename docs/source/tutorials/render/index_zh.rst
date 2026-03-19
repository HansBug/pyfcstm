模板系统教程
============

这一节讲的是模板系统本身，而不是某一个现成 builtin template 的用法。目标不是只会调用已有模板，而是理解 pyfcstm 如何把状态机模型变成输出文件，从而让你能够自己设计、测试和维护模板。

模板系统到底做什么
------------------

pyfcstm 把职责拆得比较清楚：

- DSL 解析器读取 ``.fcstm`` 文本并构造 AST
- 模型层把 AST 转成 :class:`pyfcstm.model.StateMachine`
- renderer 读取模板目录，并基于这个模型渲染文件
- 模板本身决定输出文件长什么样

renderer 不是一个“自带全部策略的后端编译器”。它不知道你的目标工程结构应该如何组织，不知道你的命名规范是什么，也不会替你决定生成运行时该膨胀到什么规模。这些都是模板作者要表达的内容。

最简单的理解方式是：

.. code-block:: text

   DSL 文本
     -> StateMachine 模型
     -> StateMachineCodeRenderer(template_dir)
     -> output_dir 下的输出文件树

模板作者要始终站在“模型输入，文件树输出”的视角来设计模板。

当前渲染机制的边界
------------------

当前 renderer 有几个很重要的边界条件，会直接影响模板写法：

- 以 ``.j2`` 结尾的文件会走 Jinja2 渲染
- 非 ``.j2`` 文件会被原样拷贝
- 目录结构会被保留
- 输出文件名由模板文件名决定
  ``machine.py.j2`` 会变成 ``machine.py``
- ignore 规则来自 ``config.yaml``，匹配方式与 gitignore 类似

这意味着模板对文件内容有很强控制力，但当前还不能仅靠模板本身实现“动态输出文件名”。如果你想输出 ``TrafficLightMachine.py`` 这种按状态机名变化的文件名，那不是模板内能单独完成的事情，还需要 renderer 层支持。

模板目录的基本结构
------------------

一个模板目录通常应该保持小而明确：

.. code-block:: text

   my_template/
   ├── config.yaml
   ├── machine.py.j2
   ├── README.md
   ├── README.md.j2
   └── static/
       └── helper.txt

常见文件职责：

- ``config.yaml``：renderer 配置、helper 定义、style 覆盖、ignore 规则
- ``*.j2``：需要渲染的模板文件
- 静态文件：原样拷贝到输出目录
- 模板目录内的 ``README``：给模板维护者看的说明
- 生成 README 模板，例如 ``README.md.j2``：给生成产物使用者看的说明

这两类 README 不应混为一谈。模板 README 解释模板怎么维护；生成 README 解释生成产物怎么使用。

模板作者需要掌握的 Jinja2 最小知识
----------------------------------

pyfcstm 使用 Jinja2 作为模板语言。你不需要一开始就写很复杂的 Jinja2 元编程，但至少要熟悉这些基础能力：

- 变量输出
- ``if`` / ``elif`` / ``else``
- ``for`` 循环
- ``macro``
- filter
- global
- test

最小例子：

.. code-block:: jinja

   {{ model.root_state.name }}

   {% for state in model.walk_states() %}
   - {{ state.name }}
   {% endfor %}

   {% if state.is_leaf_state %}
   leaf
   {% else %}
   composite
   {% endif %}

   {% macro state_id(state) -%}
   {{ state.path | join('_') }}
   {%- endmacro %}

两个很实用的经验：

1. 重复出现的命名或格式化逻辑，不要散落复制在很多文件里，应尽量抽成 helper。
2. 重复出现的大块结构，优先写成 macro；偏命名和 renderer 接口的逻辑，优先放进 ``config.yaml``。

``config.yaml`` 的角色
----------------------

``config.yaml`` 是模板和 renderer 的主连接点。常见段落包括：

- ``expr_styles``
- ``stmt_styles``
- ``globals``
- ``filters``
- ``tests``
- ``ignores``

示例：

.. code-block:: yaml

   expr_styles:
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

   globals:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

   filters:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

   ignores:
     - 'README.md'

可以这样理解这些段落：

- ``expr_styles``：定义表达式如何渲染到目标语言或目标作用域
- ``stmt_styles``：定义操作语句如何渲染，包括临时变量等语义
- ``globals``：模板全局可直接调用的 helper 或常量
- ``filters``：写在 ``{{ value | filter_name }}`` 里的转换逻辑
- ``tests``：Jinja2 条件判断里可用的 test
- ``ignores``：告诉 renderer 哪些文件不参与渲染或拷贝

一个很重要的判断标准是：

- 偏“命名规则、renderer 接口、跨文件复用”的逻辑，放 ``config.yaml``
- 偏“文件结构展开”的逻辑，放 macro

理解 ``expr_render``
--------------------

``expr_render`` 是表达式级渲染器。它适合处理“一个 DSL 表达式渲染成一个目标语言表达式字符串”这类需求。

最简单的选择规则是：

- 输入是一个表达式节点，用 ``expr_render``
- 输入是一条操作语句，用 ``stmt_render``
- 输入是一个完整语句块，比如 ``action.operations``，用 ``stmts_render``

典型例子：

.. code-block:: jinja

   {{ transition.guard.to_ast_node() | expr_render(style='python') }}
   {{ some_expr | expr_render(style='c') }}

它适合处理的内容：

- guard 表达式
- 赋值右值
- effect 条件
- 表达式节点的命名或作用域映射

它常见的输入形态：

- 一个 ``pyfcstm.model.expr`` 表达式节点
- 一个 DSL AST 表达式节点，比如 ``guard.to_ast_node()``
- 一个基础字面量，比如 ``1``、``True``，当你希望它也走表达式 renderer 统一格式时

它返回的东西是：

- 一个目标语言表达式字符串
- 不是完整语句
- 通常也不负责缩进、分支结构或整块代码布局

它不适合处理的内容：

- 完整操作块
- 赋值语句
- ``if / else if / else`` 语句树

如果你要生成可执行语句，而不是单个表达式，应使用 ``stmt_render`` 或 ``stmts_render``。

style 继承要点：

- 每个自定义 style 都从 ``base_lang`` 继承
- 只覆写你真正需要修改的节点映射即可
- style 内部递归渲染时，默认会继承当前 style，除非你显式传入别的 style

这一点非常关键。比如：

.. code-block:: yaml

   expr_styles:
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

那么像 ``counter + 1`` 这样的嵌套表达式，在递归渲染内部的 ``Name`` 节点时，依然会继续沿用 ``python_scope_expr``，你不需要为了保持递归一致而把所有内建运算模板整套抄一遍。

还有一个很实用的点：

- 在 :class:`pyfcstm.render.StateMachineCodeRenderer` 真正驱动模板渲染时，如果你调用 ``expr_render`` 不写 ``style=...``，它会使用 ``config.yaml`` 里的 ``default`` expression style
- 如果你的模板整体就是面向 Python 之类的单一目标语言，通常可以把 ``default`` 设成一个薄封装，然后模板里少写很多重复的 ``style='python'``

理解 ``stmt_render`` 与 ``stmts_render``
----------------------------------------

``stmt_render`` 和 ``stmts_render`` 是 ``expr_render`` 对应的语句级渲染器。

使用方式：

- ``stmt_render`` 用来渲染一条操作语句
- ``stmts_render`` 用来渲染一串操作语句，通常对应一个完整 action block

它们常见的输入形态：

- ``stmt_render`` 接收一个 ``OperationStatement``，或者一个 DSL operational AST statement
- ``stmts_render`` 接收这些语句对象组成的 iterable，比如 ``action.operations``

示例：

.. code-block:: jinja

   {{ one_statement | stmt_render(style='python') }}

   {{ action.operations | stmts_render(style='python') }}

当 DSL 块中可能出现以下内容时，它们才是正确入口：

- 赋值
- 临时变量
- ``if / else if / else``
- 嵌套分支

它们返回的东西是：

- 可执行的目标语言语句文本
- 带有缩进感知的多行输出
- 保持 DSL 语义的分支结构

对模板作者来说，最重要的语义点是：语句渲染会区分“持久状态变量”和“块级临时变量”。

在 renderer 驱动的模板渲染场景中，如果你没有显式传入 ``state_vars`` 或 ``var_types``，:class:`pyfcstm.render.StateMachineCodeRenderer` 会自动从 ``model.defines`` 注入默认值。也就是说，大多数模板可以直接写：

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python') }}

而不需要在模板中反复手工拼接状态变量列表。

这点为什么重要：

- 持久变量应该映射到目标状态容器，例如 ``scope['counter']`` 或 ``scope->counter``
- 临时变量应该只存在于当前块内
- 分支内部创建的临时变量应遵循运行时语义，不应错误泄漏到外层

当前内建 statement style 已覆盖 ``dsl``、``c``、``cpp``、``python``、``java``、``js``、``ts``、``rust``、``go`` 这些主流目标语言。

还要区分一个常见混淆点：

- ``operation_stmt_render`` 和 ``operation_stmts_render`` 更适合输出 DSL 文本回显
- ``stmt_render`` 和 ``stmts_render`` 才是目标语言代码生成的主入口

如果目标是生成可执行代码，应优先使用 ``stmt_render`` /
``stmts_render``。

最不容易搞错的理解方式，是直接按场景来判断：

.. list-table::
   :header-rows: 1

   * - 目标
     - 输入
     - 正确 filter
     - 典型输出形态
   * - 渲染一个 guard 表达式
     - ``transition.guard.to_ast_node()``
     - ``expr_render``
     - ``counter > 10``
   * - 渲染一条赋值语句
     - ``action.operations`` 里的某一条
     - ``stmt_render``
     - ``scope['counter'] = scope['counter'] + 1``
   * - 渲染一个完整 action block
     - ``action.operations``
     - ``stmts_render``
     - 含缩进和嵌套 ``if`` 的多行语句块

常见误用：

- 把 ``action.operations`` 喂给 ``expr_render``，却期待得到整块代码
- 把 guard 表达式喂给 ``stmts_render``，却期待它自动变成完整 ``if`` 语句
- 本来是要生成目标语言代码，却误用了 ``operation_stmts_render`` 去输出 DSL 文本回显

模板里能拿到什么
----------------

模板渲染时，核心输入对象是 ``model``。模板作者最常用到的内容通常包括：

- ``model.root_state``
- ``model.defines``
- ``model.walk_states()``
- 状态路径、父子关系、事件、动作、转换

例如：

.. code-block:: jinja

   Root: {{ model.root_state.name }}

   Variables:
   {% for def_item in model.defines.values() %}
   - {{ def_item.type }} {{ def_item.name }}
   {% endfor %}

   States:
   {% for state in model.walk_states() %}
   - {{ state.path | join('.') }}
   {% endfor %}

如果你不确定模型暴露了哪些能力，最有效的做法不是盲猜，而是直接去看现有模板和相关单元测试，尤其是模板测试与 model 测试。

生成规模与模板形态
------------------

模板作者需要对“输出规模如何随模型增长”有基本判断：

- 一个模板文件通常对应一个输出文件
- 输出内容往往会随着状态、转换、事件、生命周期动作数量增长
- 如果在模板里写了很多嵌套循环和重复展开，模板本身会很快失控

实践建议：

- 把重复命名逻辑抽成 helper
- 把重复结构抽成 macro
- 尽量保持“清晰的一次展开”，而不是复制很多几乎一样的块
- 生成代码必须保持足够可读，方便下游用户调试

对大型运行时模板来说，可读性不是装饰，而是功能的一部分。不要把 formatter 当成掩盖模板结构混乱的最后手段。

从零写一个最小模板
------------------

学习模板系统最快的方法，往往是先写一个极小模板。

目录：

.. code-block:: text

   demo_template/
   ├── config.yaml
   └── summary.txt.j2

``config.yaml``：

.. code-block:: yaml

   globals:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

``summary.txt.j2``：

.. code-block:: jinja

   Root state: {{ model.root_state.name }}

   Variables:
   {% for def_item in model.defines.values() %}
   - {{ def_item.type }} {{ def_item.name }}
   {% endfor %}

   States:
   {% for state in model.walk_states() %}
   - {{ state | state_path }}
   {% endfor %}

用下面的命令渲染：

.. code-block:: bash

   pyfcstm generate -i ./machine.fcstm -t ./demo_template -o ./out

这个最小例子足以让你先打通完整 renderer 链路，再去尝试更复杂的运行时模板。

模板应该怎么测
--------------

模板工作至少应该分层测试，而不是只看“能不能渲染出文件”。

renderer 级测试
^^^^^^^^^^^^^^^

如果你要验证模板输出结构、helper 行为、style 配置，应该直接使用 :class:`pyfcstm.render.StateMachineCodeRenderer`。

常见检查点：

- 预期文件是否生成
- 静态文件是否保持不变
- 渲染文本是否符合预期
- 自定义 ``expr_styles`` / ``stmt_styles`` 是否工作正常

生成产物级测试
^^^^^^^^^^^^^^

对于运行时模板，不要只做字符串比较。要真正 import 生成结果，并执行它。

常见检查点：

- 生成 Python 文件能否成功 import
- 公开 API 是否符合模板约定
- 简单状态机场景下的行为是否正确

行为对齐测试
^^^^^^^^^^^^

如果一个模板目标是与 :class:`pyfcstm.simulate.SimulationRuntime` 保持语义一致，就应该保留对齐测试，让两个运行时在同一批 DSL 样例上并排跑。

这类测试通常会抓住：

- 转换选择逻辑
- 初始转换
- pseudo state 行为
- aspect action
- hot start
- 临时变量作用域

CLI 端到端测试
^^^^^^^^^^^^^^

当模板面向最终用户公开时，尤其是 builtin template，应该补 CLI 端到端测试：

- 用 ``pyfcstm generate --template ...`` 生成代码
- 验证输出文件是否生成
- import 或执行生成产物
- 检查一条最小行为路径

builtin template 的发布链路
---------------------------

builtin template 在仓库里以源码目录维护，但运行时使用的是打包产物。

当前链路是：

.. code-block:: text

   templates/<name>/
     -> make tpl
     -> pyfcstm/template/<name>.zip + index.json
     -> extract_template(name, output_dir)
     -> StateMachineCodeRenderer(extracted_dir)

这对模板作者很重要，因为 builtin template 不是“仓库里一个目录”这么简单，它还包含打包、索引、释放这条运行链路。

因此 builtin template 的修改通常应同时验证两条路径：

- 直接使用源码模板目录渲染
- 先打包、再解压、再渲染

逻辑该放哪
----------

模板膨胀的一个常见原因，是把逻辑放错位置。

适合放进 ``config.yaml`` helper 的情况：

- 命名规则
- 多个文件都会复用
- 如果不抽出来，模板里会出现很长的重复 Jinja 表达式

适合放进 macro 的情况：

- 主要问题是结构重复
- 同一类块有很多行
- 关注点是输出布局，而不是 helper 接口

只适合直接写在 ``.j2`` 正文里的情况：

- 逻辑只在当前文件局部使用
- 逻辑很短
- 抽出来反而更难读

以 builtin ``python`` 模板为例
------------------------------

builtin ``python`` 模板很适合作为“模板系统如何落地”的一个实例，但它依然只是实例，不是整个模板系统定义本身。

它展示了这些点：

- 单文件运行时模板
- 生成 README 模板
- ``config.yaml`` 中的 helper 命名收敛
- 与模拟器对齐的运行时语义
- 通过 protected hook 扩展 abstract action

适合配套阅读的文件：

- ``templates/python/config.yaml``
- ``templates/python/machine.py.j2``
- ``templates/python/README.md.j2``
- ``test/template/python/test_runtime.py``
- ``test/template/python/test_runtime_alignment.py``

如果你的目标是自己写模板，应该把 ``python`` 模板看成“一个可参考实现”，而不是把它误当成模板系统本身的全部定义。

总结
----

模板作者最需要抓住的几个核心点是：

- 从 ``StateMachine`` 模型输入、文件树输出的视角理解系统
- 把 renderer 相关逻辑收敛进 ``config.yaml``
- 把重复结构收敛进 macro
- 在 renderer、生成产物、CLI 三个层次上测试模板
- 对 builtin template 始终记住它还有打包与释放链路

把这些前提弄清楚之后，写模板就会从“不断试错的 Jinja2 拼接”变成一件可以工程化推进的事情。
