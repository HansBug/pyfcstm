
.. _sec-reference-dsl-zh:

DSL 参考
==============

.. contents:: 参考地图
   :local:
   :depth: 2

范围
----------

本页是面向事实查询的 FCSTM DSL 参考。它对照当前拆分后的语法文件（grammar files），后文只称语法文件，
尤其是 ``pyfcstm/dsl/grammar/GrammarParser.g4`` 和
``pyfcstm/dsl/grammar/GrammarLexer.g4``。

需要学习路径请看 :doc:`../../tutorials/dsl/index_zh`，任务写法请看
:doc:`../../how_to/dsl/index_zh`，语义背景请看
:doc:`../../explanations/dsl_semantics/index_zh`。

同步说明：本页与英文参考按小节、表格行和语法事实逐项对应。中文段落会保留语法规则名
（grammar rule）、词法符号（token）、命令行选项（CLI option）和代码字面量（literal）的英文原文，后文只称语法规则名、词法符号、命令行选项和代码字面量，
但普通说明会给中文解释；复核时应以锚点、表格行、示例和语法事实是否对应为准，而不是用中英文自然换行数判断是否漏译。
复核时建议优先比较：

* 小节锚点是否一一对应；
* 语法 / 诊断表格行是否一一对应；
* 已验证示例与预期诊断是否一致；
* C/C++ 目标风险措辞是否保持同一边界。

.. _dsl-syntax-quick-index-zh:

语法速查索引
------------

需要查精确形式时先看这里。本参考中的示例默认是片段；只有明确说是 ``docs/source/tutorials/dsl`` 下的已验证文件时，
才是完整示例。任务指南会把主要形式链到完整示例和验证命令。

术语约定：本页首次出现必要英文术语时采用“中文（English）”格式，后文只使用中文。标识符（identifier）、字符串
（string）、注释（comment）、关键字（keyword）、持久变量（persistent variable）、复合状态（composite state）、
子状态（child state）、初始转换（initial transition）、组合转换（combo transition）、强制转换
（forced transition）、伪中继状态（pseudo relay state）、条件表达式（condition expression）和数值表达式
（numeric expression）是本页核心术语。代码、语法规则名、诊断码、JSON 字段和命令输出仍保持原文。

.. list-table:: 语法族
   :header-rows: 1
   :widths: 24 38 38

   * - 能力族
     - 主要形式
     - 详情
   * - 程序边界
     - ``def int x = 0;`` / 一个根 ``state``
     - :ref:`dsl-top-level-forms-zh`
   * - 状态
     - ``state A;`` / ``state A { ... }`` / ``pseudo state P;``
     - :ref:`dsl-state-forms-zh`
   * - 转换
     - 普通、事件、守卫、守卫 + 效果、组合、强制、初始、退出
     - :ref:`dsl-transition-forms-zh`
   * - 事件
     - ``:: Local`` / ``: Chain`` / ``: /RootEvent``
     - :ref:`dsl-events-scopes-zh`
   * - 操作块
     - 赋值、块内临时变量、``if`` / ``else if`` / ``else``、空语句
     - :ref:`dsl-operation-blocks-zh`
   * - 表达式
     - 初始化、数值、条件、三目形式、运算符优先级
     - :ref:`dsl-expression-reference-zh`
   * - 生命周期与切面
     - ``enter`` / ``during`` / ``exit``；``abstract``；``ref``；``>> during``
     - :ref:`dsl-lifecycle-forms-zh`、:ref:`dsl-aspect-forms-zh`
   * - 导入
     - ``import "path" as Alias`` 和映射块
     - :ref:`dsl-import-forms-zh`
   * - 诊断措辞
     - 特定目标警告，尤其是 C/C++ 部署配置风险
     - :ref:`dsl-diagnostics-risk-zh`

.. _dsl-lexical-forms-zh:

词法与注释形式
---------------

.. list-table:: 词法形式
   :header-rows: 1

   * - 形式
     - 语法 / 词法符号
     - 说明
   * - 标识符（identifier）
     - ``[a-zA-Z_][a-zA-Z0-9_]*``
     - 用于变量、状态、事件、动作名称、别名和路径片段。
   * - 字符串（string）
     - 单引号或双引号字符串
     - 导入路径和 ``named`` 标签使用字符串；常见转义序列由词法器处理。
   * - 注释（comment）
     - ``/* ... */``、``// ...``、``# ...``
     - 多行注释在特定生命周期形式中可以成为抽象动作文档。
   * - 关键字（keyword）
     - ``def``、``state``、``pseudo``、``event``、``import``、``enter``、``during``、``exit``、``abstract``、``ref``
     - 关键字由词法规则保留，不能作为普通标识符使用。
   * - 紧凑导入词法符号
     - 选择器模式与目标模板
     - 紧凑形式在导入专用词法模式中切分，对空白敏感；``$0`` /
       ``$1`` / ``${1}`` / ``*`` 模板详见 :ref:`dsl-import-forms-zh`。

.. _dsl-top-level-forms-zh:

顶层程序形式
--------------

普通 DSL 入口是零个或多个持久变量声明，后面接一个根状态。

片段：

.. code-block:: fcstm

   def int counter = 0;
   def float threshold = 3.5;

   state Root {
       [*] -> Idle;
       state Idle;
   }

事实：

* 持久变量类型是 ``int`` 和 ``float``。
* 声明必须出现在唯一根 ``state`` 之前。
* 初始化表达式使用 ``init_expression``。这个子集接受字面量、数学常量、算术、
  位运算符和一元数学函数，但不接受运行时变量引用，也不接受 C 风格三目表达式。
* 根状态可以是叶状态或复合状态；实际模型通常使用复合根状态。

.. _dsl-import-preamble-forms-zh:

导入前置片段形式
--------------------------

导入组装流程还会解析前置片段入口。

.. list-table:: 前置片段形式
   :header-rows: 1

   * - 规则
     - 语法
     - 含义
   * - ``constant_definition``
     - ``name = init_expression;``
     - 为导入组装定义类似常量的前置片段值。
   * - ``initial_assignment``
     - ``name := init_expression;``
     - 在导入前置片段上下文中提供初始赋值。

这些形式不是普通顶层 ``def`` 声明。它们让被导入模块在被宿主模型重写之前暴露组装期常量或初始值。

最小解析辅助验证：

.. code-block:: python

   from pyfcstm.dsl.parse import parse_preamble

   print(parse_preamble("limit = 3;"))
   print(parse_preamble("speed := 5;"))

这是解析辅助事实，不是完整 ``.fcstm`` 文件的普通用户入口。用户面对的导入示例仍应使用具体文件，
例如 ``import "./line/main.fcstm" as Line;``\ 。

.. _dsl-state-forms-zh:

状态形式
------------

.. list-table:: 状态形式
   :header-rows: 1

   * - 形式
     - 语法
     - 边界
   * - 叶状态
     - ``state Name;``
     - 可停留的运行时状态。
   * - 带显示名的叶状态
     - ``state Name named "Label";``
     - 添加显示元数据。
   * - 复合状态
     - ``state Name { ... }``
     - 拥有子声明；必须选择初始子状态。
   * - 伪状态
     - ``pseudo state Name;``
     - 路由辅助节点；组合转换中继使用时应保持叶状态形状且无动作。
   * - 伪复合语法形状
     - ``pseudo state Name { ... }``
     - 解析形状存在，但模型验证会用 ``E_PSEUDO_NOT_LEAF`` 拒绝非叶伪状态。

部分带路径的形式会通过 ``chain_id`` 使用点分标识符，例如事件作用域、导入映射或动作引用。转换的 ``from_state`` 和
``to_state`` 端点则不同：它们是在拥有状态作用域中解析的普通标识符，不是点分路径。若需要进入嵌套叶状态，应把转换写在拥有该叶状态的复合状态内部，
或转换到复合状态并让它的初始转换选择子状态。

.. _dsl-transition-forms-zh:

转换形式
------------

.. list-table:: 转换族
   :header-rows: 1

   * - 类型
     - 语法形状
     - 允许效果动作？
     - 说明
   * - 初始转换
     - ``[*] -> Target;`` 或带初始组合触发器
     - 是
     - 为复合状态选择初始子状态。
   * - 普通转换
     - ``Source -> Target;``
     - 是
     - 来源和目标在拥有者作用域中解析。
   * - 退出转换
     - ``Source -> [*];``
     - 是
     - 通过复合状态退出标记离开。
   * - 事件转换
     - ``Source -> Target :: Local;`` 或 ``: EventPath``
     - 是
     - 普通事件形式，不混入守卫条件语法。
   * - 守卫转换
     - ``Source -> Target : if [condition];``
     - 是
     - 守卫表达式只能是条件。
   * - 守卫加效果动作
     - ``Source -> Target : if [condition] effect { ... }``
     - 是
     - 事件语法不属于这个普通形式。
   * - 组合触发器
     - 通过组合规则使用 ``[guard]`` 别名或 ``Event + [guard]`` 项
     - 普通 / 初始组合展开允许
     - 用于显式事件加守卫、守卫别名或多项触发。
   * - 强制转换
     - ``!State -> Target ...;`` 或 ``!* -> Target ...;``
     - 否
     - 展开到选定来源状态。
   * - 强制退出转换
     - ``!State -> [*] ...;`` 或 ``!* -> [*] ...;``
     - 否
     - 强制形式指向退出标记。

组合转换细节：

* 本地组合转换使用 ``::`` 和本地事件项。
* 链式 / 根组合转换使用 ``:`` 和 ``chain_id`` 事件项。
* 初始组合触发器可用于初始转换。
* ``: [condition]`` 是单个守卫触发器的组合守卫别名；``: if [condition]`` 是普通守卫写法。
* 允许 ``: [enabled] + Start`` 这样的前导守卫项。
* 重复事件项和常量守卫是诊断目标。
* 组合转换的伪中继状态是生成的路由辅助节点，不是业务状态，也不是切面动作执行点。

强制转换细节：

* ``!State`` 从命名来源状态展开。
* ``!*`` 从拥有者作用域中所有适用来源状态展开。
* 强制形式可以带一个本地、链式 / 根事件或守卫触发器。
* 强制形式不能带组合 ``+`` 触发链。
* 强制形式不能有 ``effect`` 块；需要副作用时请写显式普通转换。

.. _dsl-transition-reference-assertions-zh:

转换准规范断言
----------------

本小节把转换写法整理成接近测试断言的形式。阅读时可以把每一行理解为“解析器接受什么、模型层保存什么、检查命令应该看到什么”。

.. list-table:: 转换族断言
   :header-rows: 1
   :widths: 18 26 28 28

   * - 能力点
     - 作者写法
     - 模型投影
     - 检查断言
   * - 普通边
     - ``A -> B;``
     - 来源和目标都在同一拥有者作用域中解析。
     - ``transitions[].from_path`` / ``to_path`` 是完整路径；``event`` 和 ``guard`` 为空。
   * - 事件边
     - ``A -> B :: Go;`` 或 ``A -> B : Parent.Go;``
     - 事件路径按本地、链式或根作用域归一化。
     - ``event`` 是规范化路径；``event_scope`` 表示来源。
   * - 守卫边
     - ``A -> B : if [x > 0];``
     - 守卫条件保存为条件表达式。
     - ``guard`` 是加括号后的可读表达式，不能包含事件项。
   * - 守卫加效果
     - ``A -> B : if [x > 0] effect { y = y + 1; }``
     - 守卫只决定是否可用；效果动作只在选中后执行。
     - ``guard`` 与 ``effect`` 分开出现；效果动作不反向影响本次守卫判断。
   * - 初始边
     - ``[*] -> A;``
     - 为复合状态选择初始子状态。
     - 来源在检查输出中显示为 ``[*]``；目标是复合状态直接拥有的子状态。
   * - 退出边
     - ``A -> [*];``
     - 离开当前复合状态边界。
     - 目标在检查输出中显示为 ``[*]``；实际退出顺序由运行时语义决定。
   * - 组合边
     - ``A -> B :: Go + [ready] + Done``
     - 展开成伪中继状态链。
     - ``combo_origins`` 记录作者触发项，``combo_transitions`` 记录展开边。
   * - 强制边
     - ``!* -> Error :: Fault;``
     - 展开成多条普通边。
     - ``forced_transitions[].expansion_count`` 给出展开数量，展开边含 ``forced_origin``。

非法写法也应按同一套边界理解：普通事件后缀不能再接普通守卫后缀；强制转换不能携带组合链或效果动作；转换端点不是点分路径。
这些限制不是语法缺陷，而是为了让模型可以被检查、仿真和生成代码。

.. _dsl-combo-expansion-reference-zh:

组合转换展开准规范
--------------------

组合转换用于“同一轮内按顺序满足多个触发项”的场景。它不是把两个普通后缀强行拼起来，而是在模型构建时展开为伪中继状态链。

作者写法示例来自 ``combo_transitions.fcstm``：

.. code-block:: fcstm

   Waiting -> Accepted :: Request + [ready > 0] + Confirm effect {
       accepted = accepted + 1;
   }

概念展开可以写成下列形状。真实生成名会带 ``__combo_`` 前缀和哈希，下面的名字只用于解释，不应手写到业务模型中。

.. code-block:: fcstm

   Waiting -> __combo_waiting_request :: Request;
   __combo_waiting_request -> __combo_waiting_ready : if [ready > 0];
   __combo_waiting_ready -> Accepted :: Confirm effect {
       accepted = accepted + 1;
   }

.. figure:: ../../tutorials/dsl/combo_transitions.fcstm.puml.svg
   :alt: 组合转换展开后的状态图
   :align: center

   图中 ``Waiting``、``Accepted``、``Retrying`` 和 ``Booted`` 是作者写的业务状态；带 ``__combo_`` 前缀的节点是生成的伪中继状态。
   从 ``Waiting`` 到 ``Accepted`` 的业务意图被展开为三跳：先消费 ``Request``，再测试 ``ready > 0``，最后消费
   ``Confirm`` 并执行原始效果动作。

.. list-table:: 组合转换展开断言
   :header-rows: 1
   :widths: 24 36 40

   * - 作者触发项
     - 展开边
     - 断言
   * - ``Request``
     - ``Waiting -> __combo_* :: Request``
     - 第一跳只消费事件，不执行原始效果动作。
   * - ``[ready > 0]``
     - ``__combo_* -> __combo_* : if [ready > 0]``
     - 守卫项成为中继边守卫；失败时链条不前进。
   * - ``Confirm``
     - ``__combo_* -> Accepted :: Confirm effect { ... }``
     - 最后一跳进入目标状态；原始效果动作只挂在这一跳。
   * - 伪中继状态
     - ``state.name`` 以 ``__combo_`` 开头
     - 必须是无生命周期动作、无切面动作的纯路由辅助节点。
   * - 溯源字段
     - ``combo_origins`` / ``combo_transitions``
     - 诊断可以指回作者写的具体触发项，而不是只指向生成节点。

用检查命令验证：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_transitions.fcstm --format json

应看到：

* ``states`` 中存在 ``is_pseudo=true`` 且名称以 ``__combo_`` 开头的状态；
* ``combo_origins[].terms`` 记录 ``Request``、``[ready > 0]``、``Confirm`` 的文本和源码位置；
* ``combo_transitions`` 中前缀边的 ``effect`` 为空，最后一跳的 ``effect`` 为 ``accepted = accepted + 1;``；
* 生成的中继状态不出现在作者源码中，用户不应依赖具体哈希名称。

常见错误：

.. code-block:: fcstm

   // 错误：普通事件后缀后又接普通守卫后缀。
   Waiting -> Accepted :: Request if [ready > 0];

   // 正确：使用组合触发项表达事件加守卫。
   Waiting -> Accepted :: Request + [ready > 0];

.. _dsl-forced-expansion-reference-zh:

强制转换展开准规范
--------------------

强制转换是“来源状态集合展开”，不是组合转换链。它把一个声明复制成多条普通转换，适合表达“多个状态收到同一个紧急事件后进入同一个处理状态”。

作者写法示例来自 ``forced_transitions.fcstm``：

.. code-block:: fcstm

   !* -> ErrorHandler :: CriticalError;
   !Running -> SafeMode :: EmergencyStop;

.. figure:: ../../tutorials/dsl/forced_transitions.fcstm.puml.svg
   :alt: 强制转换展开后的状态图
   :align: center

   图中 ``System`` 直接拥有 ``Initializing``、``Running``、``SafeMode`` 和 ``ErrorHandler``。``!*`` 会在这个拥有者作用域内展开，
   ``!Running`` 还会影响 ``Running`` 边界及其子状态出口。图中展开边可能比作者源码中的两行声明多得多，这正是强制转换的用途。

.. list-table:: 强制转换展开断言
   :header-rows: 1
   :widths: 22 30 48

   * - 作者写法
     - 展开含义
     - 检查断言
   * - ``!* -> ErrorHandler :: CriticalError;``
     - 从当前拥有者作用域内所有适用来源展开。
     - ``forced_transitions[].from_path`` 为 ``*``，``expansion_count`` 给出展开条数。
   * - ``!Running -> SafeMode :: EmergencyStop;``
     - 从 ``Running`` 边界及相关子状态出口展开。
     - 展开边的 ``forced_origin`` 保留原始声明文本。
   * - 无效果动作
     - 强制声明不能写 ``effect``。
     - 展开边的 ``effect`` 为空；共享行为应放到目标状态 ``enter`` 或写显式普通边。
   * - 无组合链
     - 强制声明不能写 ``+``。
     - 需要多项触发时写显式普通组合边，而不是把强制和组合混用。

用检查命令验证：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/forced_transitions.fcstm --format json

应看到 ``forced_transitions`` 摘要和多条带 ``forced_origin`` 的展开边。展开后的边仍是普通转换，因此来源状态的 ``exit`` 动作和目标状态的
``enter`` 动作照常遵循运行时顺序；强制转换本身不会绕过生命周期语义。

.. _dsl-events-scopes-zh:

事件与作用域
--------------

.. list-table:: 事件作用域形式
   :header-rows: 1

   * - 形式
     - 语法
     - 含义
   * - 事件声明
     - ``event Name;`` 或 ``event Name named "Label";``
     - 声明所在状态拥有的事件。
   * - 来源本地事件
     - ``:: Name``
     - 来源状态本地命名空间中的事件。
   * - 链式事件
     - ``: Name`` 或 ``: Parent.Event``
     - 相对于拥有者作用域的事件路径。
   * - 根事件
     - ``: /Name`` 或 ``: /Path.Event``
     - 从根状态开始的绝对事件路径。

``chain_id`` 是可选 ``/`` 后接一个或多个点分标识符。来源私有信号使用本地事件，包含协议使用链式路径，全局拥有的事件使用根路径。

.. _dsl-operation-blocks-zh:

操作块
------------------------

操作块出现在效果动作和生命周期动作体中。

.. list-table:: 操作语句
   :header-rows: 1

   * - 语句
     - 语法
     - 说明
   * - 赋值
     - ``name = num_expression;``
     - 更新持久变量或引入块内临时变量。
   * - 条件块
     - ``if [condition] { ... } else if [condition] { ... } else { ... }``
     - 条件使用 ``cond_expression``。
   * - 空语句
     - ``;``
     - 作为无操作语句接受。

块内临时变量只在当前操作块内有效，并且只能在赋值后读取。持久变量必须在顶层 ``def`` 列表中声明。

.. _dsl-expression-reference-zh:

表达式参考
-------------

.. list-table:: 数值表达式事实
   :header-rows: 1

   * - 类别
     - 形式
     - 说明
   * - 字面量
     - 十进制整数、十六进制整数、浮点数
     - 浮点词法符号支持十进制和指数形式。
   * - 常量
     - ``pi``、``E``、``tau``
     - 数学常量可用于初始化表达式和数值表达式。
   * - 变量
     - ``ID``
     - 运行时数值变量或块内临时变量。
   * - 一元符号
     - ``+x``、``-x``
     - 前缀数值符号。
   * - 幂运算
     - ``x ** y``
     - 右结合。
   * - 乘除取模
     - ``*``、``/``、``%``
     - 数值算术。
   * - 加减
     - ``+``、``-``
     - 数值算术。
   * - 移位 / 位运算
     - ``<<``、``>>``、``&``、``^``、``|``
     - 数值位运算符；C/C++ 配置可能触发目标风险警告。
   * - 函数调用
     - ``sin(x)``、``sqrt(x)``、``abs(x)``、``sign(x)`` 等词法器列出的数学函数
     - 仅一元数学函数。
   * - C 风格三目表达式
     - ``(cond) ? num_expr : num_expr``
     - ``?`` 前的条件必须加括号。

.. list-table:: 条件表达式事实
   :header-rows: 1

   * - 类别
     - 形式
     - 说明
   * - 布尔字面量
     - ``true`` / ``false`` 变体
     - 词法器接受常见大小写变体。
   * - 取反
     - ``!cond`` 或 ``not cond``
     - 前缀条件取反。
   * - 数值比较
     - ``<``、``>``、``<=``、``>=``、``==``、``!=``
     - 把数值表达式桥接为条件。
   * - 条件等价
     - ``cond == cond``、``cond != cond``、``cond iff cond``
     - 条件层面的相等与等价。
   * - 布尔组合
     - ``&&`` / ``and``、``||`` / ``or``、``xor``
     - 不要用 ``^`` 表示布尔异或；``^`` 是数值按位异或。
   * - 蕴含
     - ``=>`` 或 ``implies``
     - 右结合；不要用 ``->`` 表示蕴含。
   * - C 风格三目表达式
     - ``(cond) ? cond : cond``
     - 条件结果三目表达式。

运算符优先级按语法规则顺序从紧到松：

* 括号 / 字面量 / 函数；
* 一元符号和幂运算；
* 乘除取模、加减、移位；
* 位运算 ``&`` / ``^`` / ``|``；
* 比较、条件相等 / ``iff``；
* ``and``、``xor``、``or``；
* 蕴含和三目形式。

.. _dsl-lifecycle-forms-zh:

生命周期形式
--------------

.. list-table:: 生命周期动作形式
   :header-rows: 1

   * - 阶段
     - 具体动作
     - 命名具体动作
     - 抽象动作
     - 文档注释抽象动作
     - 引用动作
   * - ``enter``
     - ``enter { ... }``
     - ``enter Name { ... }``
     - ``enter abstract Name;``
     - ``enter abstract Name /* doc */`` 或 ``enter abstract /* doc */``
     - ``enter ref Path;`` 或 ``enter Name ref Path;``
   * - ``during``
     - ``during { ... }``
     - ``during Name { ... }``
     - ``during abstract Name;``
     - ``during abstract Name /* doc */`` 或 ``during abstract /* doc */``
     - ``during ref Path;`` 或 ``during Name ref Path;``
   * - ``during before``
     - ``during before { ... }``
     - ``during before Name { ... }``
     - ``during before abstract Name;``
     - ``during before abstract Name /* doc */`` 或 ``during before abstract /* doc */``
     - ``during before ref Path;`` 或 ``during before Name ref Path;``
   * - ``during after``
     - ``during after { ... }``
     - ``during after Name { ... }``
     - ``during after abstract Name;``
     - ``during after abstract Name /* doc */`` 或 ``during after abstract /* doc */``
     - ``during after ref Path;`` 或 ``during after Name ref Path;``
   * - ``exit``
     - ``exit { ... }``
     - ``exit Name { ... }``
     - ``exit abstract Name;``
     - ``exit abstract Name /* doc */`` 或 ``exit abstract /* doc */``
     - ``exit ref Path;`` 或 ``exit Name ref Path;``

``ref`` 指向命名生命周期动作路径，不指向状态或事件。文档注释抽象形式使用多行注释作为文档元数据；上表中的可选 ``Name`` 是说明文字，不是字面 ``Name?`` 词法符号。

.. _dsl-aspect-forms-zh:

切面形式
-----------------

切面动作使用 ``>> during before`` 或 ``>> during after``。它们支持和生命周期 ``during before/after`` 相同的具体、命名、抽象、文档注释抽象与引用形式。

.. list-table:: 切面事实
   :header-rows: 1

   * - 形式
     - 示例形状
     - 边界
   * - 具体切面
     - ``>> during before { ... }``
     - 在后代叶状态活动周期中运行。
   * - 命名切面
     - ``>> during after Trace { ... }``
     - 为生成钩子提供稳定名称。
   * - 抽象切面
     - ``>> during before abstract Trace;``
     - 生成代码调用用户提供的行为。
   * - 引用切面
     - ``>> during after ref Path;``
     - 复用命名动作。
   * - 组合伪中继
     - N/A
     - 切面动作不在组合伪中继链内执行。

.. _dsl-import-forms-zh:

导入形式
-----------------

.. list-table:: 导入语法事实
   :header-rows: 1

   * - 形式
     - 语法
     - 说明
   * - 基本导入
     - ``import "file.fcstm" as Alias;``
     - 把被导入根状态加为子状态 ``Alias``。
   * - 命名导入
     - ``import "file.fcstm" as Alias named "Label";``
     - 添加显示元数据。
   * - 导入块
     - ``import "file.fcstm" as Alias { ... }``
     - 包含映射语句。
   * - 变量兜底选择器
     - ``def * -> target;``
     - 兜底变量映射。
   * - 变量集合选择器
     - ``def {a, b} -> target;``
     - 映射一组变量。
   * - 变量模式选择器
     - ``def sensor_* -> sensor_$1;``
     - 模式选择器是紧凑且空白敏感的；``$1`` 表示第一个通配捕获。
   * - 变量精确选择器
     - ``def value -> renamed;``
     - 映射一个变量。
   * - 目标模板
     - ``ID``、紧凑模板或 ``*``
     - ``$0`` / ``${0}`` 表示完整被导入名称；``$1`` / ``${1}`` 表示第一个通配
       捕获。裸 ``*`` 保留被导入名称。
   * - 事件映射
     - ``event Source.Path -> Target.Path;``
     - 可带 ``named "Label"``。
   * - 目录入口
     - ``import "./dir/main.fcstm" as Subsystem;``
     - 使用显式文件；不支持裸目录导入。

文件解析、递归加载、冲突检测、映射优先级和模型组装在解析后的 Python 导入 / 模型代码中实现。

.. _dsl-diagnostics-risk-zh:

诊断与目标风险措辞
-----------------------------------------

诊断来自语法解析、模型验证、检查分析器和可选验证阶段。用户可见 DSL 文档必须保留每个诊断的目标范围。

.. list-table:: 诊断措辞事实
   :header-rows: 1

   * - 区域
     - 诊断码 / 来源
     - 措辞规则
   * - 组合转换展开
     - ``W_COMBO_*``、``I_COMBO_PSEUDO_NAME_EXTENDED``、``E_COMBO_PSEUDO_NAME_COLLISION``
     - 解释伪中继纯度和名称扩展行为，不暗示切面在中继内运行。
   * - 伪状态形状
     - ``E_PSEUDO_NOT_LEAF``
     - 解析形状不等于模型有效性。
   * - 数值字面量 / 操作风险
     - ``W_NUMERIC_*`` 和数值分析器
     - 除非其他目标有自己的证据，否则描述为 ``c``、``c_poll``、``cpp``、``cpp_poll`` 的 C/C++ 部署配置风险。
   * - Python 生成运行时
     - 不从 C/C++ 警告自动继承
     - 除非 Python 专属诊断明确说明，否则不要声称 Python 生成代码有同样
       固定位宽或未定义行为风险。

诊断码级措辞请看 :doc:`../../reference/diagnostics_codes/index_zh`。

.. _dsl-quasi-test-reference-zh:

准测试参考断言
----------------

本节把前面的语法事实压缩成可复核的断言清单。它不是替代正式单元测试，而是帮助文档复核者逐项确认：每个 DSL 能力都有语法、语义投影、检查字段和错误边界。

.. list-table:: 状态与名称解析断言
   :header-rows: 1
   :widths: 22 28 25 25

   * - 能力
     - 合法写法
     - 检查字段
     - 失败边界
   * - 根状态
     - 一个顶层 ``state Root { ... }``
     - ``root_state_path``
     - 多个顶层根状态应被拒绝。
   * - 叶状态
     - ``state A;``
     - ``states[].is_leaf=true``
     - 叶状态不能拥有子声明。
   * - 复合状态
     - ``state A { [*] -> B; state B; }``
     - ``states[].is_composite=true`` / ``initial_targets``
     - 没有初始子状态会产生模型错误。
   * - 伪状态
     - ``pseudo state P;``
     - ``states[].is_pseudo=true``
     - 非叶伪状态由 ``E_PSEUDO_NOT_LEAF`` 拒绝。
   * - 端点解析
     - ``A -> B;`` 写在拥有 ``A`` / ``B`` 的复合状态内
     - ``transitions[].from_path`` / ``to_path``
     - 不允许把点分私有叶路径当普通端点。

.. list-table:: 事件与触发断言
   :header-rows: 1
   :widths: 22 28 25 25

   * - 能力
     - 合法写法
     - 检查字段
     - 失败边界
   * - 来源本地事件
     - ``A -> B :: Go;``
     - ``event_scope=local``
     - 事件名称归属于来源状态。
   * - 链式事件
     - ``A -> B : Go;``
     - ``event_scope=chain``
     - 事件路径相对拥有者解析。
   * - 根事件
     - ``A -> B : /Go;``
     - ``event_scope=absolute``
     - 根事件表达公开协议，不应误写成本地私有事件。
   * - 守卫触发
     - ``A -> B : if [ready > 0];``
     - ``guard=ready > 0``
     - 普通守卫形式不能再同时写普通事件后缀。
   * - 组合触发
     - ``A -> B :: Go + [ready > 0];``
     - ``combo_origins`` / ``combo_transitions``
     - 重复事件项可能触发 ``W_COMBO_DUPLICATE_EVENT``。

.. list-table:: 操作块断言
   :header-rows: 1
   :widths: 22 30 24 24

   * - 能力
     - 合法写法
     - 语义
     - 诊断边界
   * - 持久变量赋值
     - ``counter = counter + 1;``
     - 更新顶层 ``def`` 声明的变量。
     - 未使用或只读变量可能触发数据流诊断。
   * - 块内临时变量
     - ``next = sensor + 1;`` 后再读取 ``next``
     - 仅当前操作块有效。
     - 赋值前读取会触发未写先读诊断。
   * - 条件分支
     - ``if [a] { ... } else if [b] { ... } else { ... }``
     - 条件必须是 ``cond_expression``。
     - 用数值表达式直接当条件会失败。
   * - 空语句
     - ``;``
     - 无操作占位。
     - 不应误用来隐藏缺失动作。

.. list-table:: 表达式断言
   :header-rows: 1
   :widths: 22 30 24 24

   * - 能力
     - 合法写法
     - 使用位置
     - 失败边界
   * - 初始化表达式
     - ``def int x = 1 + 2;``
     - 顶层变量初值、前置片段常量。
     - 不能读取运行时变量。
   * - 数值表达式
     - ``x + y * 2``、``sensor & mask``
     - 赋值右侧、数值比较、数值三目分支。
     - C/C++ 位宽风险必须由诊断限定目标。
   * - 条件表达式
     - ``x > 0 && ready == 1``
     - 守卫、``if`` 分支、条件三目条件。
     - ``^`` 不是布尔异或；应使用 ``xor``。
   * - 数值三目
     - ``(ready > 0) ? x : y``
     - 产生数值结果。
     - 条件必须加括号。
   * - 条件三目
     - ``(ready > 0) ? true : false``
     - 产生条件结果。
     - 不要混入数值分支。

.. list-table:: 生命周期与切面断言
   :header-rows: 1
   :widths: 22 30 24 24

   * - 能力
     - 合法写法
     - 语义
     - 失败边界
   * - 进入动作
     - ``enter { ... }``
     - 进入状态边界时执行。
     - 不等同于初始转换效果动作。
   * - 活动动作
     - ``during { ... }``
     - 叶状态普通活动周期执行。
     - 复合边界的 ``during before`` / ``during after`` 有独立语义。
   * - 退出动作
     - ``exit { ... }``
     - 离开状态边界时执行。
     - 强制转换展开后仍遵循普通退出语义。
   * - 命名与引用
     - ``enter Init { ... }`` / ``enter ref /Init;``
     - 引用命名生命周期动作。
     - ``ref`` 不指向状态或事件。
   * - 抽象动作
     - ``during abstract Poll;``
     - 生成运行时代码调用用户实现。
     - 文档注释抽象动作只提供元数据，不执行 DSL 块。
   * - 切面动作
     - ``>> during before { ... }``
     - 祖先状态包裹后代叶状态活动周期。
     - 不在组合转换伪中继状态内执行。

.. list-table:: 导入断言
   :header-rows: 1
   :widths: 22 30 24 24

   * - 能力
     - 合法写法
     - 语义
     - 检查边界
   * - 基本导入
     - ``import "worker.fcstm" as Worker;``
     - 把被导入根状态挂到别名下。
     - 路径解析在模型导入层执行。
   * - 显示名
     - ``import "worker.fcstm" as Worker named "Worker";``
     - 保存显示元数据。
     - 不改变路径解析。
   * - 变量映射
     - ``def sensor_* -> left_$1;``
     - 用通配捕获重写变量名。
     - ``$1`` 只能引用存在的捕获组。
   * - 兜底映射
     - ``def * -> *;``
     - 保留未被更具体规则命中的名称。
     - 规则优先级必须可审计。
   * - 事件映射
     - ``event /Start -> Start named "Shared Start";``
     - 重写导入事件路径并可添加显示名。
     - 映射后仍需避免路径冲突。
   * - 目录入口
     - ``import "./line/main.fcstm" as Line;``
     - 显式导入入口文件。
     - 裸目录不是 DSL 源文件。

.. list-table:: 诊断断言
   :header-rows: 1
   :widths: 24 28 24 24

   * - 诊断族
     - 触发例子
     - 结构化字段
     - 修复方向
   * - 组合重复项
     - ``Go + Go``
     - ``refs.term_span`` / ``refs.first_term_span``
     - 删除重复项或确认是否真的需要中继。
   * - 伪中继命名
     - 手写 ``__combo_`` 普通状态
     - 状态路径与保留前缀
     - 改名；不要把业务状态塞进保留命名空间。
   * - 守卫变量不变化
     - 守卫只读从未写入变量
     - ``refs.guard_vars``
     - 添加写入、改用初值常量，或删除无效守卫。
   * - 数值目标风险
     - 超出 C/C++ 系列默认整数范围
     - 数值字面量、目标配置
     - 限定到 ``c`` / ``c_poll`` / ``cpp`` / ``cpp_poll``，不要泛化到 Python。

覆盖附录
--------

下面的矩阵面向维护者和复核者。它有意放在用户语法事实之后，避免普通读者在查 DSL 形式前先被迁移审计表阻挡。

.. _dsl-coverage-matrix-zh:

DSL 覆盖矩阵
----------------

``N/A`` 表示该页面类型有意不承担这个叶能力。每一行仍然必须有参考或解释落点。

.. list-table:: DSL 能力覆盖
   :header-rows: 1
   :widths: 16 13 22 18 18 18 18 24 14

   * - 能力标识
     - 能力族
     - 事实源
     - 教程覆盖
     - 任务指南覆盖
     - 参考覆盖
     - 解释覆盖
     - 示例 / 验证
     - EN/ZH
   * - ``dsl-lexical-comments``
     - 词法
     - ``GrammarLexer.g4`` 注释 / 字符串 / 标识符
     - N/A：教程不展示词法符号表
     - N/A：任务指南使用片段
     - :ref:`dsl-lexical-forms-zh`
     - N/A：语法词法事实
     - 参考表复核
     - 已同步
   * - ``dsl-top-level-root``
     - 顶层
     - ``state_machine_dsl`` / root ``state_definition``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-small-valid-model-task-zh`
     - :ref:`dsl-top-level-forms-zh`
     - :ref:`dsl-root-design-zh`
     - ``first_thermostat.fcstm`` inspect
     - 已同步
   * - ``dsl-top-level-def``
     - 顶层
     - ``def_assignment`` / ``init_expression``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-top-level-forms-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``first_thermostat.fcstm`` inspect
     - 已同步
   * - ``dsl-import-preamble``
     - 导入
     - ``preamble_program`` / ``constant_definition`` / ``initial_assignment``
     - N/A：教程不展开导入
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-preamble-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``parse_preamble("limit = 3;")`` / 仅解析辅助
     - 已同步
   * - ``dsl-state-leaf-composite``
     - 状态
     - ``state_definition`` 叶状态 / 复合状态分支
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-ownership-name-resolution-zh`
     - ``first_thermostat.fcstm`` inspect
     - 已同步
   * - ``dsl-state-pseudo``
     - 状态
     - ``PSEUDO STATE`` / ``E_PSEUDO_NOT_LEAF``
     - N/A：教程只链接高级路由
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-combo-relay-semantics-zh`
     - ``pseudo_state_demo.fcstm`` inspect
     - 已同步
   * - ``dsl-state-target-resolution``
     - 状态
     - 模型状态查找 / 转换所有权
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-ownership-name-resolution-zh`
     - 作用域片段 / 模型验证
     - 已同步
   * - ``dsl-transition-initial``
     - 转换
     - ``entryTransitionDefinition``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-small-valid-model-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-composite-entry-semantics-zh`
     - ``first_thermostat.fcstm`` inspect
     - 已同步
   * - ``dsl-transition-plain-event``
     - 转换
     - ``normalTransitionDefinition`` / 事件项
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh` / :ref:`dsl-event-scopes-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-event-ownership-signal-zh`
     - ``event_scoping_complete.fcstm`` inspect
     - 已同步
   * - ``dsl-transition-guard-effect``
     - 转换
     - ``COLON IF`` / ``EFFECT`` 操作块
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``operation_blocks_complete.fcstm`` inspect
     - 已同步
   * - ``dsl-transition-combo``
     - 转换
     - ``combo_transition_trigger`` / ``entry_combo_transition_trigger``
     - N/A：教程只链接高级转换
     - :ref:`dsl-combo-transition-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-combo-relay-semantics-zh`
     - ``combo_transitions.fcstm`` inspect
     - 已同步
   * - ``dsl-transition-forced``
     - 转换
     - ``transition_force_definition``
     - N/A：教程只链接高级转换
     - :ref:`dsl-forced-transition-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-forced-transition-expansion-zh`
     - ``forced_transitions.fcstm`` inspect
     - 已同步
   * - ``dsl-event-scopes``
     - 事件
     - ``event_definition`` / ``chain_id``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-event-scopes-task-zh`
     - :ref:`dsl-events-scopes-zh`
     - :ref:`dsl-event-ownership-signal-zh`
     - ``event_scoping_complete.fcstm`` inspect
     - 已同步
   * - ``dsl-operation-assignment-temp``
     - 操作
     - ``operation_assignment`` / 局部临时变量跟踪
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-operation-blocks-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``operation_blocks_complete.fcstm`` inspect
     - 已同步
   * - ``dsl-operation-conditionals``
     - 操作
     - ``if_statement`` / 空语句
     - N/A：教程保持块示例简短
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-operation-blocks-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``operation_blocks_complete.fcstm`` inspect
     - 已同步
   * - ``dsl-expression-init``
     - 表达式
     - ``init_expression``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - 顶层初始化片段
     - 已同步
   * - ``dsl-expression-runtime``
     - 表达式
     - ``num_expression`` / 数学函数 / 位运算
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_condition_ternary.fcstm`` inspect
     - 已同步
   * - ``dsl-expression-condition``
     - 表达式
     - ``cond_expression`` / 比较 / 布尔运算
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_condition_ternary.fcstm`` inspect
     - 已同步
   * - ``dsl-expression-ternary``
     - 表达式
     - ``conditionalCStyleExprNum`` / ``conditionalCStyleCondNum``
     - N/A：教程保持算术示例简单
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_condition_ternary.fcstm`` inspect
     - 已同步
   * - ``dsl-lifecycle-concrete``
     - 生命周期
     - ``enter`` / ``during`` / ``exit`` 操作形式
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-lifecycle-task-zh`
     - :ref:`dsl-lifecycle-forms-zh`
     - :ref:`dsl-lifecycle-hooks-semantics-zh`
     - ``first_thermostat.fcstm`` inspect
     - 已同步
   * - ``dsl-lifecycle-named-abstract-ref``
     - 生命周期
     - 命名 / ``abstract`` / 文档注释 / ``ref`` 分支
     - N/A：教程只链接高级钩子
     - :ref:`dsl-lifecycle-task-zh`
     - :ref:`dsl-lifecycle-forms-zh`
     - :ref:`dsl-lifecycle-hooks-semantics-zh`
     - ``abstract_reference_demo.fcstm`` inspect
     - 已同步
   * - ``dsl-aspect-forms``
     - 切面
     - ``during_aspect_definition``
     - N/A：教程只给入口链接
     - :ref:`dsl-aspect-task-zh`
     - :ref:`dsl-aspect-forms-zh`
     - :ref:`dsl-during-aspect-semantics-zh`
     - ``hierarchy_execution.fcstm`` inspect
     - 已同步
   * - ``dsl-import-basic-alias``
     - 导入
     - ``import_statement`` 头部形式
     - N/A：教程不展开导入
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_basic.fcstm`` inspect
     - 已同步
   * - ``dsl-import-mapping``
     - 导入
     - ``def_mapping_statement`` / ``event_mapping_statement``
     - N/A：教程不展开导入
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_mapped.fcstm`` inspect
     - 已同步
   * - ``dsl-import-directory-boundary``
     - 导入
     - 导入路径解析位于 ``model/imports.py``
     - N/A：教程不展开导入
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_directory.fcstm`` inspect
     - 已同步
   * - ``dsl-diagnostics-target-risk``
     - 诊断
     - ``pyfcstm/diagnostics/codes.yaml`` / 分析器
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-diagnostics-task-zh`
     - :ref:`dsl-diagnostics-risk-zh`
     - :ref:`dsl-expression-separation-zh`
     - 风险措辞行级审计
     - 已同步

.. _dsl-fact-check-notes-zh:

事实核对说明
--------------

* 语法事实来自 ``GrammarParser.g4`` 和 ``GrammarLexer.g4``。
* AST 形状与导出细节来自 ``pyfcstm/dsl/node.py`` 和 ``pyfcstm/dsl/listener.py``。
* 导入组装事实来自 ``pyfcstm/model/imports.py``。
* 目标风险诊断来自 ``pyfcstm/diagnostics/codes.yaml`` 和 ``pyfcstm/diagnostics/analyzers/``。
* 面向 LLM 的语法指南在 ``pyfcstm/llm/fcstm_grammar_guide.md`` 中。本页不修改该打包指南。
