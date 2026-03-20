模板系统教程
============

这一节讲的是模板系统本身，而不是某一个现成内置模板（built-in template）的用法。目标不是只会调用已有模板，而是理解 pyfcstm 如何把状态机模型变成输出文件，从而让你能够自己设计、测试和维护模板。

理解模板系统
------------

模板系统到底做什么
^^^^^^^^^^^^^^^^^^

pyfcstm 把职责拆得比较清楚：

- DSL 解析器读取 ``.fcstm`` 文本并构造 AST
- 模型层把 AST 转成 :class:`pyfcstm.model.StateMachine`
- 渲染器（renderer）读取模板目录，并基于这个模型渲染文件
- 模板本身决定输出文件长什么样

渲染器不是一个“自带全部策略的后端编译器”。它不知道你的目标工程结构应该如何组织，不知道你的命名规范是什么，也不会替你决定生成运行时该膨胀到什么规模。这些都是模板作者要表达的内容。

最简单的理解方式是：

.. code-block:: text

   DSL 文本
     -> StateMachine 模型
     -> StateMachineCodeRenderer(template_dir)
     -> output_dir 下的输出文件树

模板作者要始终站在“模型输入，文件树输出”的视角来设计模板。

当前渲染机制的边界
^^^^^^^^^^^^^^^^^^

当前渲染器有几个很重要的边界条件，会直接影响模板写法：

- 以 ``.j2`` 结尾的文件会走 Jinja2 渲染
- 非 ``.j2`` 文件会被原样拷贝
- 目录结构会被保留
- 输出文件名由模板文件名决定
  ``machine.py.j2`` 会变成 ``machine.py``
- ignore 规则来自 ``config.yaml``，匹配方式与 gitignore 类似

这意味着模板对文件内容有很强控制力，但当前还不能仅靠模板本身实现“动态输出文件名”。如果你想输出 ``TrafficLightMachine.py`` 这种按状态机名变化的文件名，那不是模板内能单独完成的事情，还需要渲染器层支持。

模板目录的基本结构
^^^^^^^^^^^^^^^^^^

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

- ``config.yaml``：渲染器配置、helper 定义、style 覆盖、ignore 规则
- ``*.j2``：需要渲染的模板文件
- 静态文件：原样拷贝到输出目录
- 模板目录内的 ``README``：给模板维护者看的说明
- 生成 README 模板，例如 ``README.md.j2``：给生成产物使用者看的说明

这两类 README 不应混为一谈。模板 README 解释模板怎么维护；生成 README 解释生成产物怎么使用。

掌握模板写作基础
----------------

模板作者需要掌握的 Jinja2 最小知识
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pyfcstm 使用 Jinja2 作为模板语言。你不需要一开始就写很复杂的 Jinja2 元编程，但至少要熟悉这些基础能力：

- 变量输出
- ``if`` / ``elif`` / ``else``
- ``for`` 循环
- 宏（macro）
- 过滤器（filter）
- 全局函数或全局变量（global）
- 测试条件（test）

如果你想系统补 Jinja2，而不是只看本教程里的最小示例，建议直接继续看官方文档：

- `Jinja 官方模板设计文档（Template Designer Documentation） <https://jinja.palletsprojects.com/en/stable/templates/>`_
- `Jinja 官方 API 文档（API Documentation） <https://jinja.palletsprojects.com/en/stable/api/>`_

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

除了这些最小语法，模板作者通常还应该补这几项：

- 注释：``{# ... #}``
- 模板复用：``{% import ... %}``、``{% from ... import ... %}``
- 空白控制：``{%-`` 和 ``-%}``
- 过滤器链：``{{ value | filter_a | filter_b }}``
- 测试条件：``{% if value is defined %}``

这些能力在模板里非常常见。例如：

.. code-block:: jinja

   {# 避免最后多出一行空白 #}
   {% for state in model.walk_states() -%}
   - {{ state.path | join('.') }}
   {% endfor %}

   {% if state.doc is defined %}
   # {{ state.doc }}
   {% endif %}

   {% from 'macros.j2' import render_state_block %}
   {{ render_state_block(model.root_state) }}

两个很实用的经验：

1. 重复出现的命名或格式化逻辑，不要散落复制在很多文件里，应尽量抽成 helper。
2. 重复出现的大块结构，优先写成宏；偏命名和渲染器接口的逻辑，优先放进 ``config.yaml``。

``config.yaml`` 的角色
^^^^^^^^^^^^^^^^^^^^^^

``config.yaml`` 是模板和渲染器的主连接点。常见段落包括：

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
- ``tests``：Jinja2 条件判断里可用的测试条件
- ``ignores``：告诉渲染器哪些文件不参与渲染或拷贝

一个很重要的判断标准是：

- 偏“命名规则、渲染器（renderer）接口、跨文件复用”的逻辑，放 ``config.yaml``
- 偏“文件结构展开”的逻辑，放宏（macro）

理解渲染接口与上下文
--------------------

理解 ``expr_render``
^^^^^^^^^^^^^^^^^^^^

``expr_render`` 是表达式级渲染器。它适合处理“一个 DSL 表达式渲染成一个目标语言表达式字符串”这类需求。

最简单的选择规则是：

- 输入是一个表达式节点，用 ``expr_render``
- 输入是一条操作语句，用 ``stmt_render``
- 输入是一个完整语句块，比如 ``action.operations``，用 ``stmts_render``

典型例子：

.. code-block:: jinja

   {{ transition.guard.to_ast_node() | expr_render(style='python') }}
   {{ some_expr | expr_render(style='c') }}

参数说明：

.. list-table::
   :header-rows: 1

   * - 字段
     - 是否必填
     - 含义
     - 常见取值
   * - ``node``
     - 是
     - 要渲染的单个表达式节点
     - ``transition.guard.to_ast_node()``、``some_expr``、``1``、``True``
   * - ``style``
     - 否
     - 使用哪一种表达式 style
     - ``python``、``c``、``default``，或者你在 ``config.yaml`` 里自定义的名字

这里最容易忽略的是 ``style`` 的默认行为：

- 顶层调用时，如果不写 ``style=...``，会使用 ``default``
- 在递归渲染内部，如果不写 ``style=...``，会继承当前 style

它适合处理的内容：

- guard 表达式
- 赋值右值
- effect 条件
- 表达式节点的命名或作用域映射

它常见的输入形态：

- 一个 ``pyfcstm.model.expr`` 表达式节点
- 一个 DSL AST 表达式节点，比如 ``guard.to_ast_node()``
- 一个基础字面量，比如 ``1``、``True``，当你希望它也走表达式渲染器统一格式时

它返回的东西是：

- 一个目标语言表达式字符串
- 不是完整语句
- 通常也不负责缩进、分支结构或整块代码布局

它不适合处理的内容：

- 完整操作块
- 赋值语句
- ``if / else if / else`` 语句树

如果你要生成可执行语句，而不是单个表达式，应使用 ``stmt_render`` 或 ``stmts_render``。

``expr_render`` 到底是怎么找模板 key 的
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

这一点非常关键，因为你在 ``config.yaml`` 里 override 的其实不是“某个语言整体”，而是“某一类表达式节点的渲染模板”。

匹配顺序可以概括成：

1. 先看有没有“更具体”的 key。
2. 没有的话，再退回同类节点的通用 key。
3. 还没有的话，再退回 ``default``。

对模板作者最有用的 key 规则如下：

.. list-table::
   :header-rows: 1

   * - key 写法
     - 匹配什么
     - 例子
     - 常见用途
   * - ``Float``
     - 浮点字面量
     - ``3.14``
     - 改浮点格式
   * - ``Integer``
     - 十进制整数
     - ``42``
     - 改整数格式
   * - ``Boolean``
     - 布尔字面量
     - ``true`` / ``false`` 这类目标语言写法
     - 改布尔字面量
   * - ``Constant``
     - DSL 常量节点
     - ``pi``、``e``、``tau``
     - 映射到 ``Math.PI``、``math.Pi`` 之类
   * - ``HexInt``
     - 十六进制整数
     - ``0xFF``
     - 保持十六进制输出
   * - ``Paren``
     - 括号表达式
     - ``(a + b)``
     - 控制括号保留方式
   * - ``Name``
     - 变量名
     - ``counter``
     - 做作用域映射，例如 ``scope['counter']``
   * - ``UFunc``
     - 所有一元函数调用
     - ``sin(x)``
     - 定义一元函数的通用写法
   * - ``UFunc(sin)``
     - 某个具体函数
     - ``sin(x)``
     - 对某个函数做专门覆盖
   * - ``UnaryOp``
     - 所有一元运算
     - ``-x``
     - 定义一元运算通用写法
   * - ``UnaryOp(!)``
     - 某个具体一元运算符
     - ``!flag``
     - 把 ``!`` 映射成 ``not`` 等
   * - ``BinaryOp``
     - 所有二元运算
     - ``a + b``
     - 定义二元运算通用写法
   * - ``BinaryOp(**)``
     - 某个具体二元运算符
     - ``a ** b``
     - 把幂运算映射成 ``pow(...)`` 等
   * - ``ConditionalOp``
     - 三元条件表达式
     - ``cond ? a : b``
     - 映射成目标语言三元或等价写法
   * - ``default``
     - 兜底
     - 某类节点没有专门模板时
     - 做最后回退

要点是：

- ``UFunc(sin)`` 会优先于 ``UFunc``
- ``UnaryOp(!)`` 会优先于 ``UnaryOp``
- ``BinaryOp(**)`` 会优先于 ``BinaryOp``
- ``Name``、``Float``、``Integer`` 这类没有再细分操作符的节点，直接按节点类型名匹配

所以，像 Python style 里：

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       UnaryOp(!): 'not {{ node.expr | expr_render }}'
       BinaryOp(&&): '{{ node.expr1 | expr_render }} and {{ node.expr2 | expr_render }}'
       BinaryOp(||): '{{ node.expr1 | expr_render }} or {{ node.expr2 | expr_render }}'

它的含义不是“重写整个 Python 表达式系统”，而只是：

- 对 ``!`` 做专门覆盖
- 对 ``&&`` 做专门覆盖
- 对 ``||`` 做专门覆盖
- 其他表达式节点仍然沿用 ``base_lang: python`` 的默认写法

这正是模板系统的关键优势：你通常不需要复制整张 style 表，只 override 你关心的 key。

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

- 在 :class:`pyfcstm.render.StateMachineCodeRenderer` 真正驱动模板渲染时，如果你调用 ``expr_render`` 不写 ``style=...``，它会使用 ``config.yaml`` 里的 ``default`` 表达式 style
- 如果你的模板整体就是面向 Python 之类的单一目标语言，通常可以把 ``default`` 设成一个薄封装，然后模板里少写很多重复的 ``style='python'``

你应该怎么 override 这些 key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

最常见的 override 场景有三类。

1. 只改变量名映射：

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

效果：

- ``counter + 1`` 会变成 ``scope["counter"] + 1``
- 其他节点仍然沿用 Python 内建 style

2. 只改某个具体运算符：

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: c
       BinaryOp(**): 'pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})'

效果：

- ``a ** b`` 变成 ``pow(a, b)``
- 其他二元运算仍然沿用 C style 的通用写法

3. 只改某个具体函数：

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       UFunc(sin): 'fast_sin({{ node.expr | expr_render }})'

效果：

- ``sin(x)`` 变成 ``fast_sin(x)``
- ``cos(x)``、``sqrt(x)`` 等仍然沿用原有 Python style

你真正需要避免的反模式是：

- 为了改一个 ``Name``，把整套 ``Float`` / ``Integer`` / ``BinaryOp`` / ``UFunc`` 全抄一遍
- 为了改一个操作符，重复维护几十个无关 key
- 在 ``.j2`` 文件里手写越来越多表达式拼接，而不是把表达式策略收敛进 style

一个很实用的重构例子：

重构前：

.. code-block:: jinja

   if {{ transition.guard.to_ast_node() | expr_render(style='python') }}:
       ...

   value = {{ some_expr | expr_render(style='python') }}

重构后：

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

.. code-block:: jinja

   if {{ transition.guard.to_ast_node() | expr_render }}:
       ...

   value = {{ some_expr | expr_render }}

效果：

- 模板正文更短
- 目标语言切换时，改动更集中
- 同一模板里不容易出现 style 写漏或写错

理解 ``stmt_render`` 与 ``stmts_render``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``stmt_render`` 和 ``stmts_render`` 是 ``expr_render`` 对应的语句级渲染器。

使用方式：

- ``stmt_render`` 用来渲染一条操作语句
- ``stmts_render`` 用来渲染一串操作语句，通常对应一个完整动作块（action block）

它们常见的输入形态：

- ``stmt_render`` 接收一个 ``OperationStatement``，或者一个 DSL AST 操作语句
- ``stmts_render`` 接收这些语句对象组成的 iterable，比如 ``action.operations``

示例：

.. code-block:: jinja

   {{ one_statement | stmt_render(style='python') }}

   {{ action.operations | stmts_render(style='python') }}

参数说明：

``stmt_render``：

.. list-table::
   :header-rows: 1

   * - 字段
     - 是否必填
     - 含义
     - 常见取值
   * - ``node``
     - 是
     - 一条操作语句
     - ``action.operations[0]``
   * - ``style``
     - 否
     - 使用哪一种语句 style
     - ``python``、``c``、``default``
   * - ``state_vars``
     - 否
     - 哪些名字应被视为持久状态变量
     - ``('counter', 'flag')``
   * - ``var_types``
     - 否
     - 状态变量类型信息，主要给静态语言 style 用
     - ``{'counter': 'int', 'ratio': 'float'}``
   * - ``visible_names``
     - 否
     - 在这条语句开始前，哪些临时变量已经可见
     - ``('tmp', 'error')``
   * - ``visible_var_types``
     - 否
     - 已可见临时变量的类型信息
     - ``{'tmp': 'int'}``
   * - ``indent``
     - 否
     - 一个缩进单元是什么
     - ``'    '``、``'  '``
   * - ``level``
     - 否
     - 从第几级缩进开始渲染
     - ``0``、``1``、``2``

``stmts_render``：

.. list-table::
   :header-rows: 1

   * - 字段
     - 是否必填
     - 含义
     - 常见取值
   * - ``nodes``
     - 是
     - 一串操作语句
     - ``action.operations``
   * - ``style``
     - 否
     - 使用哪一种语句 style
     - ``python``、``c``、``default``
   * - ``state_vars``
     - 否
     - 哪些名字应被视为持久状态变量
     - ``('counter', 'flag')``
   * - ``var_types``
     - 否
     - 状态变量类型信息，主要给静态语言 style 用
     - ``{'counter': 'int', 'ratio': 'float'}``
   * - ``visible_names``
     - 否
     - 在这一串语句开始前，哪些临时变量已经可见
     - ``('tmp', 'error')``
   * - ``visible_var_types``
     - 否
     - 已可见临时变量的类型信息
     - ``{'tmp': 'int'}``
   * - ``indent``
     - 否
     - 一个缩进单元是什么
     - ``'    '``、``'  '``
   * - ``level``
     - 否
     - 从第几级缩进开始渲染
     - ``0``、``1``、``2``
   * - ``sep``
     - 否
     - 顶层语句之间的分隔符
     - ``'\\n'``

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

在渲染器驱动的模板渲染场景中，如果你没有显式传入 ``state_vars`` 或 ``var_types``，:class:`pyfcstm.render.StateMachineCodeRenderer` 会自动从 ``model.defines`` 注入默认值。也就是说，大多数模板可以直接写：

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python') }}

而不需要在模板中反复手工拼接状态变量列表。

这点为什么重要：

- 持久变量应该映射到目标状态容器，例如 ``scope['counter']`` 或 ``scope->counter``
- 临时变量应该只存在于当前块内
- 分支内部创建的临时变量应遵循运行时语义，不应错误泄漏到外层

一个很典型的重构例子，是把手写展开改成统一语句渲染。

重构前：

.. code-block:: jinja

   {% for op in action.operations %}
   {{ op.target.name }} = {{ op.expr.to_ast_node() | expr_render(style='python') }}
   {% endfor %}

这类写法的问题是：

- 只能覆盖最简单赋值
- 一遇到临时变量就容易错
- 一遇到 ``if / else if / else`` 就必须继续手写分支模板
- 最后模板会越来越像“自己重写了一遍语句渲染器”

重构后：

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python') }}

效果：

- 赋值、临时变量、条件分支都由统一语句渲染器处理
- 模板更短，也更不容易漏语义
- 后续如果你要改作用域映射或静态类型信息，只需要改 style 或参数

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
^^^^^^^^^^^^^^^^

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

如果你想系统查看模型层 API，而不是只靠现有模板猜测，可以直接继续看 :doc:`../../api_doc/model/index` 。

这份 API 文档会比教程更完整，适合你查：

- ``StateMachine`` 暴露了哪些字段和方法
- ``State``、``Transition``、``Event``、``OnStage``、``OnAspect`` 分别能拿到什么
- 表达式节点和模型对象之间怎么对应

设计模板与组织实现
------------------

生成规模与模板形态
^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^

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

为了让这个最小例子更直观，假设输入 DSL 是：

.. code-block:: fcstm

   def int counter = 0;

   state TrafficLight {
       [*] -> Red;

       state Red;
       state Green;
   }

那么实际渲染出来的 ``out/summary.txt`` 会是：

.. code-block:: text

   Root state: TrafficLight

   Variables:
   - int counter

   States:
   - TrafficLight
   - TrafficLight.Red
   - TrafficLight.Green

这个最小例子足以让你先打通完整渲染器链路，再去尝试更复杂的运行时模板。

内置模板（built-in template）
----------------------------

渲染系统本身是通用的，但仓库里也已经提供了一组内置模板，它们本身就是现实可用的参考实现。

当前内置模板列表：

- ``python``
  - 状态：当前内置模板
  - 设计定位：模板系统结构与运行时语义对齐的参考实现
- ``c``
  - 状态：当前内置模板
  - 设计定位：面向直接集成部署的自包含 C 运行时模板

对于内置模板，pyfcstm 还会在生成目录里一并产出配套使用说明。实际使用时，用户会在输出目录中看到
``README.md`` 和 ``README_zh.md``，这两份生成文档就是目标模板具体用法的主要入口。

python - 模板系统与运行时语义对齐的参考模板
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``python`` 模板是当前最清晰、最适合作为整体参考实现的内置模板。

它当前的设计定位主要包括：

- 作为内置模板目录结构的参考实现
- 单文件运行时模板
- 面向最终用户的生成 README 模板
- 与模拟器对齐的运行时语义
- 通过 protected hook 扩展 abstract action

如果你想先理解模板目录结构、helper 设计、生成运行时形态，以及与模拟器对齐的行为语义，可以优先从
``templates/python/`` 入手，再结合生成目录里的 ``README.md`` / ``README_zh.md`` 看最终使用方式。

c - 面向原生集成的自包含运行时模板
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``c`` 模板是当前面向原生运行时集成的内置模板。它生成的是围绕 ``machine.h`` 和 ``machine.c``
组织的自包含 C 运行时，而不是像 Python 模板那样的单文件运行时，但它依然遵循同一套模板系统和渲染流程。

它当前的设计定位主要包括：

- 面向直接嵌入和系统集成的生成型 C 运行时
- 通过公开头文件暴露清晰的运行时 API，而不是走 Python import 风格入口
- 以生成出来的 ``README.md`` / ``README_zh.md`` 作为主要用户集成说明
- 通过运行时测试和行为对齐测试来约束生成结果

如果你关注的是原生 API、运行时集成方式，以及生成代码如何通过 README 对最终用户进行引导，就应该看
``templates/c/``，并把输出目录中的 ``README.md`` / ``README_zh.md`` 视为最终使用说明入口。

测试与收束
----------

模板应该怎么测
^^^^^^^^^^^^^^

模板工作至少应该分层测试，而不是只看“能不能渲染出文件”。

先给一个模板作者视角下的最小调试流程：

1. 准备一个极小 DSL 样例，只覆盖你眼前正在写的模板能力。
2. 用模板目录直接生成到临时输出目录。
3. 打开生成文件，先看名字、结构、缩进、变量映射是不是对。
4. 如果是运行时模板，真的去 import 并执行最小路径。
5. 再把这个样例固定进单元测试，避免以后改模板时回归。

不要一上来就拿一个很大的状态机调试模板。模板错误一旦和模型复杂度叠在一起，定位会非常慢。

渲染器级测试
~~~~~~~~~~~~

如果你要验证模板输出结构、helper 行为、style 配置，应该直接使用 :class:`pyfcstm.render.StateMachineCodeRenderer`。

常见检查点：

- 预期文件是否生成
- 静态文件是否保持不变
- 渲染文本是否符合预期
- 自定义 ``expr_styles`` / ``stmt_styles`` 是否工作正常

生成产物级测试
~~~~~~~~~~~~~~

对于运行时模板，不要只做字符串比较。要真正 import 生成结果，并执行它。

常见检查点：

- 生成 Python 文件能否成功 import
- 公开 API 是否符合模板约定
- 简单状态机场景下的行为是否正确

行为对齐测试
~~~~~~~~~~~~

如果一个模板目标是与 :class:`pyfcstm.simulate.SimulationRuntime` 保持语义一致，就应该保留对齐测试，让两个运行时在同一批 DSL 样例上并排跑。

这类测试通常会抓住：

- 转换选择逻辑
- 初始转换
- pseudo state 行为
- aspect action
- hot start
- 临时变量作用域

命令行（CLI）端到端测试
~~~~~~~~~~~~~~~~~~~~~~~~

如果你的模板面向 CLI 用户，或者你希望确认“用户实际使用命令生成代码”这条路径没有问题，就应该补 CLI 端到端测试。

常见做法：

- 用 ``pyfcstm generate -t ./your_template`` 生成代码
- 验证输出文件是否生成
- 检查生成结果里最关键的一个入口文件
- import 或执行生成产物
- 检查一条最小行为路径

如果模板调试卡住了，常见排查顺序是：

1. 先看 ``config.yaml`` 的 helper / style 是否已经按预期生效。
2. 再看 ``.j2`` 正文里传给 ``expr_render`` / ``stmt_render`` / ``stmts_render`` 的对象是不是对的。
3. 如果你怀疑 DSL block 本身和自己理解不一致，可以先用 ``operation_stmt_render`` / ``operation_stmts_render`` 把 DSL 文本回显出来做对照。
4. 如果文件内容对了但运行不对，再去看生成产物级测试。

逻辑该放哪
^^^^^^^^^^

模板膨胀的一个常见原因，是把逻辑放错位置。

适合放进 ``config.yaml`` helper 的情况：

- 命名规则
- 多个文件都会复用
- 如果不抽出来，模板里会出现很长的重复 Jinja 表达式

适合放进宏（macro）的情况：

- 主要问题是结构重复
- 同一类块有很多行
- 关注点是输出布局，而不是 helper 接口

只适合直接写在 ``.j2`` 正文里的情况：

- 逻辑只在当前文件局部使用
- 逻辑很短
- 抽出来反而更难读

总结
^^^^

模板作者最需要抓住的几个核心点是：

- 从 ``StateMachine`` 模型输入、文件树输出的视角理解系统
- 把渲染器相关逻辑收敛进 ``config.yaml``
- 把重复结构收敛进宏（macro）
- 先学会用官方 Jinja 文档补基础，再回来看模板系统里的约定
- 在渲染器、生成产物、CLI 三个层次上测试模板

把这些前提弄清楚之后，写模板就会从“不断试错的 Jinja2 拼接”变成一件可以工程化推进的事情。
