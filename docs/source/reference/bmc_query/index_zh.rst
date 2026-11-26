:orphan:

FBMCQ 语言参考
==============

FBMCQ（FCSTM 有界模型检查查询语言，FCSTM bounded-model-checking query
language）是 :func:`pyfcstm.bmc.parse.parse_bmc_query` 接受的 ``.fbmcq``
语言。一个文件选择初始帧，可选地约束环境，并且声明且仅声明一个有界性质。
本页是可查阅的参考；示例足够小，可直接作为解析器或绑定器单测用例。

可用下面的本页目录直接定位完整文法、初始化、假设、表达式、原子、调用过滤器、
含区域（region）的模型、性质或合法性汇总。命令输出、退出状态、JSON、见证和重放字段请查
:doc:`../bmc_results/index_zh`，不要从语法页猜测进程协议。

.. contents:: 本页目录
   :local:
   :depth: 2

有效性分为三个层级；查询可以通过前一层而在后一层失败。本文将解析（parse）、
绑定（bind）和下沉（lower）分别称为语法解析、语义绑定和求解器下沉。

.. list-table:: 验证层级
   :header-rows: 1
   :widths: 18 29 25 28

   * - 层级
     - 检查内容
     - 公开失败类型
     - 主要事实来源
   * - 解析
     - 词元、子句顺序、标点和表达式类别。
     - :class:`pyfcstm.bmc.errors.BmcQueryParseError`
     - ``pyfcstm/bmc/grammar/BmcQueryLexer.g4`` 和
       ``BmcQueryParser.g4``
   * - 绑定
     - 正数边界、选择器范围、原子上下文和模型名称。
     - :class:`pyfcstm.bmc.errors.InvalidBmcQuery`，通常带有
       ``BmcBindingDiagnostic`` 诊断码和路径
     - ``pyfcstm/bmc/query.py`` 和 ``binding.py``
   * - 下沉
     - 当前 Z3 编码是否实现了已经成功解析的操作。
     - :class:`pyfcstm.bmc.errors.UnsupportedBmcQuery`
     - ``pyfcstm/bmc/relation.py`` 和 ``properties.py``

有界轨迹包含帧 ``0 .. N``，可执行宏步和事件输入则为 ``0 .. N-1``。
因此，帧选择器可以等于 ``N``，事件选择器和绝对调用步选择器不可以。

完整文件文法
------------

顶层顺序固定。``init`` 子句可省略，假设子句可重复，最后必须有一个
``check`` 子句。每个子句都以 ``;`` 结束；结尾多余词元不会被忽略。

.. code-block:: text

   query          ::= init_clause? assume_clause* check_clause EOF
   init_clause    ::= "init" init_target init_havoc? ("where" cond_expr)? ";"
   init_target    ::= "cold" | "terminated" | "state" "(" STRING ")"
   init_havoc     ::= "havoc" "*"
                    | "havoc" "{" init_var ("," init_var)* "}"
   init_var       ::= ID | STRING

   assume_clause  ::= "assume" ("always" | "at" INT) ":" cond_expr ";"
                    | "assume" "event" "(" STRING "," event_range ")"
                      ("==" | "!=") bool_literal ";"
                    | "assume" "events" "cardinality" "any" ";"
                    | "assume" "events" "cardinality" "at_most_one"
                      "{" STRING ("," STRING)* "}" ";"

   check_clause   ::= "check" property_kind "<=" INT ":" property_body ";"
   property_kind  ::= "reach" | "forbid" | "invariant" | "must_reach"
                    | "exists_always" | "response" | "cover"
   property_body  ::= cond_expr
                    | "trigger" cond_expr "->" "within" INT cond_expr

默认值与规范化
~~~~~~~~~~~~~~

.. list-table:: 默认值
   :header-rows: 1
   :widths: 26 30 44

   * - 省略的语法面
     - 生效值
     - 边界
   * - 整个 ``init`` 子句
     - ``init cold``
     - 声明初始化器保留；无初始 ``where`` 谓词。
   * - 假设
     - 空列表
     - FBMCQ 不再对事件施加其他约束。
   * - ``active(path)``、``terminated()``、``case(label)`` 的选择器
     - ``current``
     - 整数选择器能通过文法解析，但在用户性质和假设上下文中会被绑定器拒绝。
   * - ``called(...)`` / ``call_count(...)`` 的步选择器
     - 当前性质锚点
     - 此处不能写 ``current``；该关键字在调用步选择器中非法。
   * - 省略的调用过滤器字段
     - 不限制对应的调用记录维度
     - 完全空的过滤器匹配所选步上的所有已记录抽象调用。

ASCII 十进制整数允许前导零并规范化为十进制：``01`` 变为 ``1``，
``01 .. 03`` 变为 ``1..3``。bound 和 ``within`` 窗口必须为正数。
十六进制和浮点数是数值表达式字面量，不能用作 bound 或选择器。

词法表面
--------

``ID`` 为 ``[A-Za-z_][A-Za-z0-9_]*``。单双引号字符串支持 ``\\b``、
``\\t``、``\\n``、``\\f``、``\\r``、转义引号和反斜线、八进制转义、
``\\xHH`` 与 ``\\uHHHH``。因此，引号内名称可含 Unicode，也可与关键字冲突。
三种注释都会被丢弃：``// line``、``# line`` 和 ``/* block */``。

.. code-block:: fbmcq

   // 默认冷启动；注释只是 trivia。
   assume always: var("temperature") >= -40;
   # 最终 check 仍然必需。
   check reach <= 01: active('Root.Ready');

非法词法或文件形状包括：

.. code-block:: fbmcq
   :caption: 非法示例

   init cold check reach <= 1: true;       // init 缺少分号
   init cold;                              // 缺少 check
   check reach <= 0x1: true;               // bound 必须使用 INT
   check reach <= 1: true; trailing        // 拒绝尾随输入
   check reach <= 1: active("Root.A);       // 字符串未闭合

初始帧：``init``、``havoc`` 与 ``where``
-----------------------------------------

.. list-table:: 初始目标
   :header-rows: 1
   :widths: 19 30 51

   * - 形式
     - 第 0 帧控制源
     - 变量行为
   * - 省略或 ``init cold;``
     - 内部冷启动哨兵，随后执行正常入口展开。
     - 除非被 ``havoc`` 选中，否则每个持久变量声明初始化器都约束第 0 帧。
   * - ``init state("path");``
     - 指定模型状态，解析为稳定叶状态源或入口源。
     - 使用相同的声明初始化策略。这是符号热启动；不会通过执行更早的入口 action 推导变量。含区域的模型里文本还可以是配置，见“含区域的模型”一节。
   * - ``init terminated;``
     - 终止哨兵。
     - 使用相同的声明初始化策略。

``havoc`` 跳过所选持久变量的声明初始化器。它并非赋予一个随机具体值；第 0 帧
符号保持自由，仍可由 ``where`` 约束。``havoc *`` 选择所有持久变量。历史展开生成的变量是“自由”的唯一例外：被 ``havoc`` 的 ``__hist_goto`` 为 ``0``\ ，被 ``havoc`` 的 ``__hist_<所有者>`` 记录为 ``0`` 或所有者下某个可停留叶的编号，这是执行能取到的全部值（见 :ref:`dsl-history-reference-zh`\ ）。\ ``where``\ 要求其他取值时，初始化不可行。
具名集合不得为空、不得重复，并且必须解析到已声明变量。保留字或非标识符名称可加引号。

``where`` 只向第 0 帧增加条件。它可使用帧变量、字面量、算术与逻辑运算、
``active(...)`` 和 ``terminated()``。裸 ``cycle``、``event``、``case``、
``called`` 和 ``call_count`` 在此上下文中非法。模型变量若恰好名为 ``cycle``，
仍可写作 ``var("cycle")``。

三种非同质合法形式：

.. code-block:: fbmcq

   check reach <= 1: true;  // 隐式 cold；无 havoc；无 where

.. code-block:: fbmcq

   init state("Root.Idle") havoc { retries, "cycle" }
       where retries >= 0 && var("cycle") == 1;
   check invariant <= 4: retries >= 0;

.. code-block:: fbmcq

   init terminated havoc * where terminated();
   check must_reach <= 1: terminated();

边界与非法形式：

.. code-block:: fbmcq
   :caption: 边界：havoc 释放变量，where 随后约束它

   init cold havoc { x } where x == 7;
   check reach <= 1: x == 7;

.. code-block:: fbmcq
   :caption: 非法初始形式

   init state("Root.A") havoc {}; check reach <= 1: true;       // 空集合
   init state("Root.A") havoc {x, x}; check reach <= 1: true;   // 重复
   init cold where cycle == 0; check reach <= 1: true;          // cycle_not_allowed
   init cold where event("Root.E", current); check reach <= 1: true;
   init state("$STATE_INIT"); check reach <= 1: true;            // 保留路径
   init state("Root.A") where x == 1 havoc {x}; check reach <= 1: true;

环境假设
--------

假设把约束与核心轨迹合取，不会改变性质极性（polarity）。

假设中的变量角色
~~~~~~~~~~~~~~~~

四种角色都沿用普通名称或 ``var("name")`` 引用，角色差异由绑定和求解处理，
不引入新的 FBMCQ 语法：

* ``control`` / ``output`` 属于 ``0..N`` 帧。本周期没有写入时，保持上一帧值。
* 动态 ``input`` 属于 ``0..N-1`` 步。每步使用独立符号，不默认与上一拍相等。
* ``param`` 在所有帧中严格相等。默认值固定其初值；初始 ``havoc`` 可以放开取值，
  但选定的值仍在整条轨迹中保持不变。

引用输入的假设使用步范围：``assume at N`` 被拒绝，``assume always`` 作用于
N 个步。混合角色的假设读取源帧的持久状态和当前步的输入。不引用输入的假设
仍使用完整的 ``0..N`` 帧范围。例如，模型为
``input int sensor; param int gain = 2; state Root;`` 时：

.. code-block:: text

    assume at 0: sensor == 1;
    assume at 1: var("sensor") == 3;
    assume at 2: gain == 2;
    check reach <= 2: active("Root");

该查询为 SAT，记录两拍输入 ``{"sensor": 1}``、``{"sensor": 3}``。
将最后一条假设改成 ``sensor == 2`` 会产生绑定错误：界限为 2 时没有第三拍输入。
在两个合法帧上约束参数取不同值则为 UNSAT，因为参数不能随帧变化。

动态输入不参与初始化，不能出现在 ``havoc`` 或 ``init ... where`` 中。
``havoc *`` 覆盖持久状态、输出和参数。帧性质不能直接引用动态输入；如需跨帧检查
已观测的采样值，应在模型中将其锁存到持久状态或输出。参数沿用普通引用，
也可用于调用过滤谓词。

帧假设
~~~~~~

对于不含动态输入的谓词，``assume always`` 作用于全部 ``N+1`` 帧；``assume at k`` 只作用于一帧，
要求 ``0 <= k <= N``。帧谓词允许 ``cycle`` 及当前帧的
``active``/``terminated`` 原子，不允许事件、分支或调用原子。

.. code-block:: fbmcq

   assume always: x >= 0;
   check invariant <= 3: x >= 0;

.. code-block:: fbmcq

   assume at 0: active("Root.Idle");
   check reach <= 2: active("Root.Done");

.. code-block:: fbmcq

   assume at 3: cycle == 3 && !terminated();
   check forbid <= 3: x < 0;

第三例是合法上边界 ``k == N``。以下形式非法：

.. code-block:: fbmcq

   assume at 4: true; check reach <= 3: true;                    // 越界
   assume always: event("Root.Tick", current); check reach <= 1: true;
   assume always: called("Root.Hook"); check reach <= 1: true;

事件假设
~~~~~~~~

事件假设寻址可执行步，因此点和闭区间端点必须满足 ``0 <= k < N``；``*``
展开到所有步。``!=`` 会通过反转布尔值规范化，例如 ``!= false`` 表示期望 ``true``。

.. code-block:: fbmcq

   assume event("Root.Tick", *) == false;
   check reach <= 3: true;

.. code-block:: fbmcq

   assume event("Root.Start", 0) == true;
   check reach <= 2: active("Root.Running");

.. code-block:: fbmcq

   assume event("Root.Reset", 1 .. 2) != false;
   check reach <= 3: terminated();

合法的最后一点是 ``N-1``。反向区间在结构上非法；端点等于 ``N`` 会在绑定时越界。

.. code-block:: fbmcq

   assume event("Root.Tick", 3) == true; check reach <= 3: true;
   assume event("Root.Tick", 2..3) == true; check reach <= 3: true;
   assume event("Root.Tick", 3..1) == true; check reach <= 4: true;

基数假设
~~~~~~~~

``any`` 不增加基数限制。``at_most_one`` 在每个可执行步分别约束列出的事件集合。
列表必须非空、无重复且能在模型中解析；它不表示必须发生一个事件。

.. code-block:: fbmcq

   assume events cardinality any;
   check reach <= 1: true;

.. code-block:: fbmcq

   assume events cardinality at_most_one {"Root.Start"};
   check reach <= 2: active("Root.Running");

.. code-block:: fbmcq

   assume events cardinality at_most_one {
       "Root.Tick",
       "Root.Reset",
       "Root.Stop"
   };
   check forbid <= 4: terminated();

单元素集合是合法但逻辑上平凡的边界。空集合和重复集合非法：

.. code-block:: fbmcq

   assume events cardinality at_most_one {}; check reach <= 1: true;
   assume events cardinality at_most_one {"Root.E", "Root.E"};
   check reach <= 1: true;

表达式
------

数值表达式
~~~~~~~~~~

.. list-table:: 数值基本形式
   :header-rows: 1
   :widths: 25 35 40

   * - 语法族
     - 形式
     - 说明
   * - 字面量
     - ``0``、``001``、``0x2A``、``.5``、``1.``、``3.5e1``
     - 十六进制前缀必须是小写 ``0x``；浮点数下沉为实数。
   * - 常量
     - ``pi``、``E``、``tau``
     - 从 Python 浮点常量编码为 Z3 实数值。
   * - 变量
     - ``x`` 或 ``var("any name")``
     - 裸名称必须满足 ``ID`` 且不能是保留字；``var`` 支持关键字、Unicode 和带标点名称。
   * - 帧索引
     - ``cycle``
     - 当前帧索引；初始 ``where`` 和调用 ``where`` 中不可用。
   * - 调用
     - ``call_count(...)``
     - 仅性质上下文可用；返回匹配的调用记录数。
   * - 一元
     - ``+x``、``-x``
     - 数值一元运算。
   * - 条件
     - ``(condition) ? if_true : if_false``
     - 条件外的圆括号必需。

数值优先级从高到低为：圆括号/基本表达式；一元 ``+ -``；右结合 ``**``；
``* / %``；``+ -``；``<< >>``；``&``；``^``；``|``；条件运算。
代表性合法形式：

.. code-block:: fbmcq

   check reach <= 2: x + y * z ** 2 >= 10;
   check reach <= 2: ((active("Root.A")) ? x : var("fallback")) >= 0;
   check reach <= 2: sqrt(abs(x)) + round(y) >= pi;

除法和取模增加除数非零定义性条件；``sqrt`` 增加操作数非负条件。未定义谓词按下文
性质语义处理，不会被静默赋值。

解析器识别的全部一元函数名为：

.. code-block:: text

   sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh
   sqrt cbrt exp log log10 log2 log1p abs ceil floor round trunc sign

当前下沉实现 ``sqrt``、``abs``、``ceil``、``floor``、``round``、``trunc``
和 ``sign``。其余名称可解析、可绑定，但抛出 ``UnsupportedBmcQuery``。
整数位运算/移位 ``& | ^ << >>`` 同样可解析、可绑定，但当前算术配置不是 BitVec，
因此不支持。``%`` 支持整数操作数；``f % 1.0`` 这类实数取模不支持。

.. code-block:: fbmcq
   :caption: 可解析且可绑定，但下沉时不受支持

   assume always: sin(x) >= 0;
   check reach <= 1: true;

.. code-block:: fbmcq
   :caption: 非法表达式类别

   check reach <= 1: x + 1;                    // 数值不是布尔条件
   check reach <= 1: active("Root.A") + 1 > 2; // 布尔原子不能参与算术

条件表达式
~~~~~~~~~~

条件基本形式包括布尔字面量、比较、BMC 原子和括号条件。布尔值接受
``true/True/TRUE`` 与 ``false/False/FALSE``。符号和关键字别名会规范化为下表所示形式。

.. list-table:: 条件运算符，按优先级从高到低
   :header-rows: 1
   :widths: 24 30 46

   * - 运算
     - 可接受拼写
     - 说明
   * - 否定
     - ``!p``、``not p``
     - 规范形式为 ``!``。
   * - 数值比较
     - ``< > <= >= == !=``
     - 两侧都是数值。
   * - 布尔相等
     - ``== != iff``
     - 两侧都是布尔；``iff`` 规范化后仍为 ``iff``。
   * - 合取
     - ``&&``、``and``
     - 保留短路定义性。
   * - 异或
     - ``xor``
     - 两侧都求值。
   * - 析取
     - ``||``、``or``
     - 保留短路定义性。
   * - 蕴含
     - ``=>``、``implies``
     - 右结合；保留两侧定义性条件。
   * - 条件
     - ``(condition) ? if_true : if_false``
     - 三个分支都是条件；只有选中分支贡献定义性。

.. code-block:: fbmcq

   check reach <= 3: !(x < 0) && active("Root.Ready");
   check reach <= 3: (x == 1) implies (y == 2);
   check reach <= 3: (active("Root.A")) ? !terminated() : y >= tau;

边界 ``((true) ? 1 : (1 / 0)) == 1`` 有定义，因为非法分支未被选择；
``((false) ? 1 : (1 / 0)) == 1`` 无定义。

BMC 原子及上下文合法性
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 原子形式
   :header-rows: 1
   :widths: 18 37 45

   * - 原子
     - 文法
     - 含义与默认值
   * - 帧变量
     - ``var(STRING)``
     - 当前求值帧的持久变量。
   * - 帧索引
     - ``cycle``
     - 数值型当前帧索引。
   * - 活跃状态
     - ``active(STRING[, current|INT])``
     - 状态活跃；省略选择器表示 current。
   * - 终止
     - ``terminated([current|INT])``
     - 帧使用终止哨兵；省略表示 current。
   * - 事件
     - ``event(STRING, current|INT)``
     - 某一步的事件输入；选择器必需。
   * - 分支
     - ``case(STRING[, current|INT])``
     - 内部宏步分支标签；用户绑定只允许它裸写为 ``cover`` 主体。
   * - 已调用
     - ``called(call_filter?)``
     - 是否存在至少一条匹配的抽象调用记录。
   * - 调用计数
     - ``call_count(call_filter?)``
     - 匹配记录的数值计数。

.. list-table:: 上下文矩阵
   :header-rows: 1
   :widths: 24 11 11 11 11 14 18

   * - 上下文
     - ``cycle``
     - 活跃 / 终止
     - 事件
     - 分支
     - 调用原子
     - 选择器规则
   * - 初始 ``where``
     - 否
     - 是
     - 否
     - 否
     - 否
     - 仅 current
   * - 帧假设
     - 是
     - 是
     - 否
     - 否
     - 否
     - 仅 current
   * - 普通性质主体
     - 是
     - 是
     - 否
     - 否
     - 是
     - 仅 current
   * - ``response`` 触发侧
     - 是
     - 是
     - 仅 ``current``
     - 否
     - 是
     - 仅 current
   * - ``response`` 响应侧
     - 是
     - 是
     - 否
     - 否
     - 是
     - 仅 current
   * - ``cover`` 主体
     - 否
     - 否
     - 否
     - 仅裸原子
     - 否
     - 省略或 ``current``
   * - 调用 ``where``
     - 否
     - 否
     - 否
     - 否
     - 否
     - 仅快照变量和普通表达式运算

三种非同质合法原子组合为：

.. code-block:: fbmcq

   check reach <= 3: active("Root.A") && !terminated();

.. code-block:: fbmcq

   check response <= 3:
       trigger event("Root.Tick", current)
       -> within 1 active("Root.Ready");

.. code-block:: fbmcq

   check reach <= 3:
       cycle >= 0 && var("cycle") >= cycle && called();

合法选择器边界 ``active("Root.A", current)`` 与省略选择器等价。相反，
``event("Root.Tick")`` 缺少必需的步选择器，属于语法错误。

对含区域的模型，``active(...)`` 的字符串也可以是配置文本，写法与见证里打印的一致，这时这个原子是一个\ **模式**\ ：文本里写出的区域必须在所写的位置，没有写出的区域不受约束。

.. code-block:: fbmcq

   check reach <= 3: active("Controller.Running{Motion: On}");              // Safety 不受约束
   check reach <= 3: active("Controller.Running{Safety: Watching, Motion: On}");
   check reach <= 3: active("Root.Run{Motion: [done]}");                    // Motion 已完成
   check reach <= 1: active("Root.Run{Motion: [init]}");                    // 等待启动
   check reach <= 3: active("Root.Run{Work: Inner{X: x1}}");                // 嵌套的拥有者

不带花括号的路径就是不写任何区域的模式，所以 ``active("Root.Run")`` 的含义与以前相同。它与 ``init state(...)`` 的差别是有意的：起点是在\ **构造**\ 一个位置，没写的区域等待初始化；模式是在\ **匹配**\ 一个位置，没写的区域不受约束。由 ``init state(...)`` 的文本构造出的位置，一定匹配同一段文本写成的模式。拥有者（owner）正在被进入时发出的调用里，还没启动的区域同样满足 ``[init]``。

在调用过滤器的 ``where`` 里，``active(...)`` 描述调用那一刻机器所在的位置，也就是处理器拿到的 ``ctx.configuration``：同一周期里先走的区域显示新位置，还没启动的区域显示 ``[init]``。不含区域的模型里，它就是动作所在的状态及其祖先。

.. code-block:: fbmcq

   check reach <= 4: called("Root.B.Work", where active("Root{A: Done}"));

所以下列形式虽然通过文法解析，却在绑定时非法：

.. code-block:: fbmcq

   check reach <= 5: active("Root.Idle", 2);                 // explicit_frame_selector
   check reach <= 5: event("Root.Tick", current);            // event_not_allowed
   check response <= 5: trigger event("Root.Tick", 3)
       -> within 2 active("Root.Done");                       // event_not_allowed
   check reach <= 3: (cycle < 2) ? true : case("label");     // case_not_allowed

抽象调用过滤器
~~~~~~~~~~~~~~

``called`` 是存在性判断，等价于匹配计数至少为一；``call_count`` 是数值计数。
两者使用同一过滤器。位置参数必须先于具名参数；``where`` 必须最后出现；每个维度至多一次。

.. list-table:: 调用过滤器维度
   :header-rows: 1
   :widths: 20 28 52

   * - 维度
     - 可接受形式
     - 约束
   * - 动作
     - 第一位置参数 ``STRING`` 或 ``action=STRING``
     - 已存在的具名抽象动作路径；省略时匹配任意动作。
   * - 步
     - 第二位置选择器或 ``step=selector``
     - 省略时选择锚点；绝对点满足 ``0 <= k < N``。
   * - 生命周期阶段
     - ``stage=STRING``
     - 闭集：``enter``、``during``、``exit``。
   * - 运行时角色
     - ``role=STRING``
     - ``state_enter``、``state_exit``、``leaf_during``、
       ``plain_during_before``、``plain_during_after``、
       ``aspect_during_before``、``aspect_during_after`` 或
       ``transition_effect``。
   * - 状态
     - ``state=STRING``
     - 公开运行时状态路径。
   * - 活跃叶状态
     - ``active_leaf=STRING``
     - 调用执行时的运行时状态路径：存在活跃叶状态时为该叶状态，否则为该调用的
       宿主状态路径。进入或离开复合状态、以及执行声明在复合状态上的普通
       ``during`` 动作时不存在活跃叶状态，此时匹配宿主状态路径。
   * - 具名引用
     - ``named_ref=STRING`` 或 ``named_ref=null``
     - 已存在的具名 ``ref`` 调用点，或明确要求不存在具名 ``ref``。
       匹配调用点自身的具名 ``ref``；引用链仅在中途经过具名动作的调用不具有
       具名 ``ref``\ ，由 ``named_ref=null`` 匹配。
   * - 快照谓词
     - ``where cond_expr``
     - 对调用时捕获的持久变量值求值。

三种非同质合法过滤器：

.. code-block:: fbmcq

   check reach <= 3: called("Root.A.Hook");

.. code-block:: fbmcq

   check reach <= 3:
       call_count("Root.A.Hook", step=*, stage="during", role="leaf_during") >= 2;

.. code-block:: fbmcq

   check reach <= 4:
       called(action="Root.Library.Shared", step=-2..+0,
              state="Root.A", active_leaf="Root.A",
              named_ref="Root.A.FirstRef", where x >= 0 && var("y") < 10);

进入复合状态时不存在活跃叶状态，此时 ``active_leaf`` 是宿主状态路径而非叶状态。
对下面这个模型，复合状态 ``Root`` 上的 ``enter ref`` 记录的是 ``state="Root"``
与 ``active_leaf="Root"``，尽管模型里唯一的叶状态是 ``Root.Inner.Leaf``：

.. code-block:: fcstm

   def int a = 0;

   state Root
   {
       [*]->Inner;
       Inner->[*];

       enter ref Inner.act;

       state Inner
       {
           [*]->Leaf;
           Leaf->[*];

           enter abstract act;

           state Leaf;
       }
   }

.. code-block:: fbmcq

   check reach <= 2:
       called("Root.Inner.act", step=0, state="Root", active_leaf="Root");

空过滤器合法：``called()`` 查询当前锚点是否发生过任意抽象调用，
``call_count(step=*)`` 统计整个有界轨迹中的所有已记录调用。匿名 abstract block
不会产生用户可见调用记录。

步选择器可以是 ``*``、绝对点（``2``）、相对点（``+0``、``-1``）或闭区间。
缺失的区间端点表示当前锚点而非轨迹端点；相对结果裁剪到 ``[0, N)``。

.. list-table:: 步选择器示例
   :header-rows: 1
   :widths: 22 33 45

   * - 选择器
     - 锚点 ``i`` 上的含义
     - 边界
   * - 省略或 ``+0``
     - 第 ``i`` 步
     - 在第 ``N`` 帧可能选不到可执行步。
   * - ``*``
     - 全部 ``0 .. N-1`` 步
     - 与锚点无关。
   * - ``-2..+0``
     - 当前步及前两步，越界裁剪
     - 在锚点 0 只含第 0 步。
   * - ``..+2``
     - 当前步至未来两步，越界裁剪
     - 缺失起点表示当前步。
   * - ``+0..``
     - 仅当前步
     - 缺失终点表示当前步，不是 ``N-1``。
   * - ``0..2``
     - 绝对闭区间
     - 两个端点都必须小于 ``N``。

非法过滤器及调用 ``where`` 中不支持的原子：

.. code-block:: fbmcq

   check reach <= 3: called(stage="during", 1);             // 具名参数后不能有位置参数
   check reach <= 3: called("A", action="B");               // action 重复
   check reach <= 3: called(foo="A");                       // unsupported argument
   check reach <= 3: called(step=current);                   // 选择器语法非法
   check reach <= 3: called(step=3);                         // N=3 时越界
   check reach <= 3: called("A", stage="middle");           // call_stage
   check reach <= 3: called("A", where cycle == 0);         // cycle_not_allowed
   check reach <= 3: called("A", where terminated());       // call_where_atom_not_allowed

含区域的模型
------------

含 ``region`` 块的模型没有唯一的当前状态。查询里一切描述\ *机器在哪里*\ 的写法，因此都使用配置（configuration）的文本形式，也就是仿真器打印、见证记录的那种文本，例如 ``Job.Run{Prep: Ready, Work: Busy}``。不含区域的模型不受本节任何内容影响：下面每种写法都退化为前文所述的普通状态路径。示例使用本页旁边的四个小模型，每个例子都运行真实的命令。

.. literalinclude:: /_models/region_job.fcstm
   :language: fcstm
   :caption: region_job.fcstm：``Job.Run`` 下有两个区域；两者都完成后，拥有者继续前往 ``Next``

.. literalinclude:: /_models/region_nested.fcstm
   :language: fcstm
   :caption: region_nested.fcstm：区域 ``Work`` 里的状态 ``Inner`` 本身又是拥有者

.. literalinclude:: /_models/region_calls.fcstm
   :language: fcstm
   :caption: region_calls.fcstm：拥有者、两个区域上的抽象动作，以及整组的 ``>> during after``

``controller.fcstm`` 是区域教程里共用的控制联锁模型，``region_plain.fcstm`` 是没有区域的两状态机；两者各只用于一个示例。下面每个脚本把一条查询写进文件，运行 ``pyfcstm bmc -i <模型> -q <查询>``\ ，并打印退出状态和命令打印内容的第一行。

配置文本
~~~~~~~~

.. list-table:: ``init state(...)`` 与 ``active(...)`` 接受的配置文本形式
   :header-rows: 1
   :widths: 30 36 34

   * - 形式
     - 含义
     - 示例
   * - ``Path``
     - 状态路径；路径可以经过区域名。
     - ``Job.Next``、``Root.Run.Work.Inner.X.x2``
   * - ``Owner{Region: State, ...}``
     - 拥有区域的状态，后面写出每个区域的位置。区域名是区域的裸名，值是该区域直接子状态的名字。
     - ``Job.Run{Prep: Ready, Work: Busy}``
   * - ``Region: [done]``
     - 该区域已完成（``[done]`` 是已完成的文本）。
     - ``Job.Run{Prep: [done]}``
   * - ``Region: [init]``
     - 该区域在等待初始化。
     - ``Job.Run{Prep: [init]}``
   * - ``Region: State{...}``
     - 区域里的状态本身又是拥有者；它的区域以同样方式嵌套，深度不限。
     - ``Root.Run{Work: Inner{X: x2}}``

``:``、``,``、``{``、``}`` 两侧的空白会被忽略。区域名与状态名按模型里的写法精确匹配（区分大小写）。不符合这种形状的文本是语法错误，报错带有文本里的列号。读入这套文法的还有 :meth:`pyfcstm.model.configuration.Configuration.parse`\ ；两个入口的差别只在\ *没写出的*\ 区域意味着什么，见下一节。

``init state(...)``：构造一个起点
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``init state("...")`` 的文本\ *构造*\ 第 0 帧的位置。写出的部分直接就位，不执行 ``enter`` 动作；没写出的部分等待初始化（``[init]``），在第一个宏步里走各自的 ``[*]`` 转换。模型层面的规则与仿真器的热启动一致（见 :doc:`/reference/simulation/index_zh`\ ）。

.. list-table:: ``region_job.fcstm`` 的合法起点位置（第 0 帧与见证的前几步）
   :header-rows: 1
   :widths: 34 66

   * - ``init state("...")``
     - 第 0 帧的配置，以及见证接下来做什么
   * - ``Job.Run{Prep: Ready, Work: Busy}``
     - 每个区域都写出：第 0 帧恰是这段文本。``Prep`` 在第 0 步完成（``Job.Run{Prep: [done], Work: Busy}``）。
   * - ``Job.Run.Work.Busy``
     - 经过区域的路径只保留它经过的那一支：第 0 帧是 ``Job.Run{Prep: [init], Work: Busy}``，``Prep`` 在第 0 步走 ``[*] -> Wait``。
   * - ``Job.Run{Work: Busy}``
     - 与路径写法是同一个位置：没写的区域等待。
   * - ``Job.Run``
     - 只写拥有者：整组等待，第 0 帧是 ``Job.Run{Prep: [init], Work: [init]}``，两个区域在第 0 步按书写顺序初始化。
   * - ``Job.Run{Prep: [done], Work: Busy}``
     - 只要还有一个区域在工作，已完成的区域就是合法起点。
   * - ``Job.Next``\ （不是拥有者）
     - 普通状态：第 0 帧是 ``Job.Next``。

下面的脚本运行起点的五种写法，并打印每个见证的前三帧：

.. testcode::

   import json
   import subprocess
   from pathlib import Path

   for text in ("Job.Run{Prep: Ready, Work: Busy}", "Job.Run.Work.Busy", "Job.Run{Work: Busy}",
                "Job.Run", "Job.Run{Prep: [done], Work: Busy}"):
       query = 'init state("%s"); check reach <= 2: true;' % text
       Path("query.fbmcq").write_text(query + "\n")
       subprocess.run(["pyfcstm", "bmc", "-i", "region_job.fcstm", "-q", "query.fbmcq", "--json", "-o", "result.json"], check=True)
       print(text)
       for frame in json.loads(Path("result.json").read_text())["witness"]["frames"]:
           print("  frame %d: %s" % (frame["index"], frame["configuration"]))

.. testoutput::

   Job.Run{Prep: Ready, Work: Busy}
     frame 0: Job.Run{Prep: Ready, Work: Busy}
     frame 1: Job.Run{Prep: [done], Work: Busy}
     frame 2: Job.Run{Prep: [done], Work: Busy}
   Job.Run.Work.Busy
     frame 0: Job.Run{Prep: [init], Work: Busy}
     frame 1: Job.Run{Prep: Wait, Work: Busy}
     frame 2: Job.Run{Prep: Ready, Work: Busy}
   Job.Run{Work: Busy}
     frame 0: Job.Run{Prep: [init], Work: Busy}
     frame 1: Job.Run{Prep: Wait, Work: Busy}
     frame 2: Job.Run{Prep: Ready, Work: Busy}
   Job.Run
     frame 0: Job.Run{Prep: [init], Work: [init]}
     frame 1: Job.Run{Prep: Wait, Work: Idle}
     frame 2: Job.Run{Prep: Wait, Work: Busy}
   Job.Run{Prep: [done], Work: Busy}
     frame 0: Job.Run{Prep: [done], Work: Busy}
     frame 1: Job.Run{Prep: [done], Work: Busy}
     frame 2: Job.Run{Prep: [done], Work: Busy}

第二种写法要看的是：第 0 帧打印出起点构造的 ``[init]``，第 1 帧显示 ``Prep`` 初始化到了 ``Wait``。它不能说明 ``Work`` 没有运行：``Busy`` 是起点，它的 ``during`` 在第 0 步照常执行。

.. list-table:: 非法起点位置（除特别说明外，诊断码为 ``invalid_start_position``；退出状态 1，标准输出为空）
   :header-rows: 1
   :widths: 38 62

   * - ``init state("...")``
     - 报告的消息
   * - ``Job.Run{Prep: [done], Work: [done]}``
     - ``all regions are done at 'Job.Run'; a finished owner cannot be hot-started.``
   * - ``Job.Run{Nope: Wait}``
     - ``Unknown region in configuration for 'Job.Run'.``
   * - ``Job.Run{Prep: Busy}``
     - ``Unknown configuration path: 'Job.Run.Prep.Busy'.``\ （``Busy`` 属于另一个区域）
   * - ``Job.Run{Prep: Wait, Prep: Ready}``
     - ``Duplicate region in configuration for 'Job.Run'.``
   * - ``Job.Run.Prep.Busy``
     - 诊断码 ``unknown_state``：``Unknown state path: 'Job.Run.Prep.Busy'.`` 普通路径先按状态绑定，再按位置读取。

每条消息的前缀都是 ``Failed to compile BMC query: <诊断码> at initial.state_path:``\ ，表中每个文本在下面的脚本里都是这样：

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for text in ("Job.Run{Prep: [done], Work: [done]}", "Job.Run{Nope: Wait}", "Job.Run{Prep: Busy}",
                "Job.Run{Prep: Wait, Prep: Ready}", "Job.Run.Prep.Busy"):
       print(text)
       print("  " + verdict("region_job.fcstm", 'init state("%s"); check reach <= 2: true;' % text))

.. testoutput::

   Job.Run{Prep: [done], Work: [done]}
     1 Failed to compile BMC query: invalid_start_position at initial.state_path: all regions are done at 'Job.Run'; a finished owner cannot be hot-started.
   Job.Run{Nope: Wait}
     1 Failed to compile BMC query: invalid_start_position at initial.state_path: Unknown region in configuration for 'Job.Run'.
   Job.Run{Prep: Busy}
     1 Failed to compile BMC query: invalid_start_position at initial.state_path: Unknown configuration path: 'Job.Run.Prep.Busy'.
   Job.Run{Prep: Wait, Prep: Ready}
     1 Failed to compile BMC query: invalid_start_position at initial.state_path: Duplicate region in configuration for 'Job.Run'.
   Job.Run.Prep.Busy
     1 Failed to compile BMC query: unknown_state at initial.state_path: Unknown state path: 'Job.Run.Prep.Busy'.

“全部完成”规则在每一层嵌套都适用：它与仿真器里“每个区域都是 ``[done]`` 不是合法热启动位置”是同一条规则。

``active(...)``：匹配一个配置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在性质、假设、``where`` 或调用过滤器里，``active("文本")`` 是一个\ *模式*。当且仅当下面三条同时成立，它在某一帧上成立：

* 文本指明的状态处于活动；
* 文本写出的每个区域都在所写的位置（一个状态、``[done]`` 或 ``[init]``），嵌套的拥有者递归地适用；
* 文本没写出的每个区域都是自由的：可以在任何位置。

没有区域块的模式就是本页前半部分的状态路径测试。它与 ``init state(...)`` 的差别是有意设计的，也是最常被读错的地方：

.. list-table:: 同一段文本作为起点和作为模式
   :header-rows: 1
   :widths: 24 38 38

   * - 文本 ``Job.Run{Work: Busy}``
     - 作为 ``init state(...)``\ （构造）
     - 作为 ``active(...)``\ （匹配）
   * - 区域 ``Work``
     - 放在 ``Busy``。
     - 必须在 ``Busy``。
   * - 区域 ``Prep``\ （没写出）
     - 等待初始化：``[init]``。
     - 自由：``Wait``、``Ready``、``[done]`` 都匹配。
   * - 关系
     - 构造出的位置一定满足用同一段文本写成的模式。
     - 模式不说明机器能到达哪个位置。

.. list-table:: 合法模式及其检查的内容（除特别说明外用 ``region_nested.fcstm``）
   :header-rows: 1
   :widths: 46 54

   * - ``active("...")``
     - 结论与读法（查询均为 ``check reach <= 2``）
   * - ``Root.Run{Work: Inner{X: x2}}``
     - 成立：``Y`` 与 ``Aux`` 自由。
   * - ``Root.Run{Work: Inner{X: x2, Y: y1}}``
     - 成立：两个内层区域都写出。
   * - ``Root.Run{Aux: a1}``
     - 成立：``Work`` 自由。
   * - ``Root.Run.Work.Inner.X.x2``
     - 成立：经过区域的普通路径；与 ``Root.Run{Work: Inner{X: x2}}`` 是同一批帧。
   * - ``Root.Run{Work: [done]}``
     - 在上界内不成立：``Inner`` 是区域永不结束的拥有者，所以 ``Work`` 永远不会完成。
   * - ``Root.Run{Work: Inner{X: x2}, Aux: [init]}``
     - 不成立：稳定帧里没有区域在等待初始化（见下面的 ``[init]``）。
   * - ``Job.Run{Prep: [done], Work: Busy}``\ （``region_job.fcstm``，上界 6）
     - 成立：``Prep`` 已完成而 ``Work`` 仍在工作。
   * - ``Job.Run{Work: [done]}``\ （``region_job.fcstm``，上界 6）
     - 成立：``Work`` 在 ``Prep`` 之前完成（``n >= 3``）。

下面的脚本运行表里的模式；退出状态 0 带有见证，1 表示上界内没有任何执行能达到该模式：

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for text in ("Root.Run{Work: Inner{X: x2}}", "Root.Run{Work: Inner{X: x2, Y: y1}}", "Root.Run{Aux: a1}",
                "Root.Run.Work.Inner.X.x2", "Root.Run{Work: [done]}", "Root.Run{Work: Inner{X: x2}, Aux: [init]}"):
       print(text)
       print("  " + verdict("region_nested.fcstm", 'check reach <= 2: active("%s");' % text))
   for text in ("Job.Run{Prep: [done], Work: Busy}", "Job.Run{Work: [done]}"):
       print(text)
       print("  " + verdict("region_job.fcstm", 'check reach <= 6: active("%s");' % text))

.. testoutput::

   Root.Run{Work: Inner{X: x2}}
     0 BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Root.Run{Work: Inner{X: x2, Y: y1}}
     0 BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Root.Run{Aux: a1}
     0 BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Root.Run.Work.Inner.X.x2
     0 BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Root.Run{Work: [done]}
     1 BMC reach <= 2: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   Root.Run{Work: Inner{X: x2}, Aux: [init]}
     1 BMC reach <= 2: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   Job.Run{Prep: [done], Work: Busy}
     0 BMC reach <= 6: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Job.Run{Work: [done]}
     0 BMC reach <= 6: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND

这只能读成“没有任何不超过两个宏步的执行能让 ``Work`` 处于已完成”，不能多读：这是可达目标在上界内的回答。

``[init]`` 只在区域尚未启动时成立：起点没写出该区域的第 0 帧上，以及拥有者正在被进入时发出的调用的 ``where`` 里（见下一部分）。冷启动或稳定宏步产生的任何帧上它都不成立，因为宏步只会结束在每个区域都有位置的配置上：

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   print(verdict("region_job.fcstm", 'init state("Job.Run"); check reach <= 1: active("Job.Run{Prep: [init]}");'))
   print(verdict("controller.fcstm", 'check reach <= 3: active("Controller.Running{Motion: [init]}");'))

.. testoutput::

   0 BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS

.. list-table:: 非法模式
   :header-rows: 1
   :widths: 36 18 46

   * - ``active("...")``
     - 诊断码
     - 消息（前缀\ ``Failed to compile BMC query: <诊断码> at property.predicate:``\ 之后）
   * - ``Root.Run{Work: Nope}``
     - ``invalid_active_pattern``
     - ``Unknown state path: 'Root.Run.Work.Nope'.``
   * - ``Root.Run{Zed: a1}``
     - ``invalid_active_pattern``
     - ``state 'Root.Run' has no region 'Zed'.``
   * - ``Root.Run{Aux: a1, Aux: a1}``
     - ``invalid_active_pattern``
     - ``region 'Aux' of 'Root.Run' is written twice.``
   * - ``Root.Run{Work: Inner{X: x2}``
     - ``invalid_active_pattern``
     - ``Expected '}' at line 1, column 28, got end of input.``
   * - ``Root.Run{Work: x1}``
     - ``invalid_active_pattern``
     - ``Unknown state path: 'Root.Run.Work.x1'.``\ （``x1`` 不是 ``Work`` 的直接子状态）
   * - 在 ``region_plain.fcstm`` 上写 ``Root.Idle{A: x}``
     - ``invalid_active_pattern``
     - ``the model declares no regions, so a configuration pattern with region blocks matches nothing.``
   * - ``Root.Nope``
     - ``unknown_state``
     - ``Unknown state path: 'Root.Nope'.``\ （不带花括号的普通路径按状态绑定）

每条非法查询的退出状态都是 1，消息打印在标准错误；脚本把标准错误并入它打印的那一行：

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for text in ("Root.Run{Work: Nope}", "Root.Run{Zed: a1}", "Root.Run{Aux: a1, Aux: a1}",
                "Root.Run{Work: Inner{X: x2}", "Root.Run{Work: x1}", "Root.Nope"):
       print(text)
       print("  " + verdict("region_nested.fcstm", 'check reach <= 2: active("%s");' % text))
   print("Root.Idle{A: x} on region_plain.fcstm")
   print("  " + verdict("region_plain.fcstm", 'check reach <= 2: active("Root.Idle{A: x}");'))

.. testoutput::

   Root.Run{Work: Nope}
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: Unknown state path: 'Root.Run.Work.Nope'.
   Root.Run{Zed: a1}
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: state 'Root.Run' has no region 'Zed'.
   Root.Run{Aux: a1, Aux: a1}
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: region 'Aux' of 'Root.Run' is written twice.
   Root.Run{Work: Inner{X: x2}
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: Expected '}' at line 1, column 28, got end of input.
   Root.Run{Work: x1}
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: Unknown state path: 'Root.Run.Work.x1'.
   Root.Nope
     1 Failed to compile BMC query: unknown_state at property.predicate: Unknown state path: 'Root.Nope'.
   Root.Idle{A: x} on region_plain.fcstm
     1 Failed to compile BMC query: invalid_active_pattern at property.predicate: the model declares no regions, so a configuration pattern with region blocks matches nothing.


含区域的模型里的调用过滤器
~~~~~~~~~~~~~~~~~~~~~~~~~~

``called(...)`` 与 ``call_count(...)`` 里的 ``where active(...)`` 描述\ *调用那一刻的整台机器*，也就是处理器作为 ``ctx.configuration`` 拿到的位置。下面每条规则都在 ``region_calls.fcstm`` 上用 ``check reach <= 3`` 核对过：

.. list-table:: ``where active(...)`` 看到什么
   :header-rows: 1
   :widths: 30 30 40

   * - 调用
     - 调用时的配置
     - 成立的模式 / 永不成立的模式
   * - 拥有者 ``Run`` 的 ``enter``\ （``step=0``）
     - 两个区域都还在等待
     - 成立：``Root.Run{A: [init], B: [init]}``
   * - ``A1`` 的 ``enter``\ （``step=0``）
     - ``A`` 已就位，``B`` 未启动
     - 成立：``Root.Run{A: A1, B: [init]}``；永不：``Root.Run{B: B1}``
   * - ``B1`` 的 ``enter``\ （``step=0``）
     - 两者都已就位：``B1`` 在它的 ``enter`` 运行之前就已在配置里
     - 成立：``Root.Run{A: A1, B: B1}``；永不：``Root.Run{B: [init]}``
   * - 拥有者在同一周期内被重新进入时 ``Run`` 的 ``enter``\ （``step=1``）
     - 重新进入前区域被复位：两者都是 ``[init]``
     - 成立：``Root.Run{A: [init], B: [init]}``；永不：``Root.Run{A: [done]}``
   * - 离开时 ``Run`` 的 ``exit``\ （``step=1``）
     - 离开之前的位置，这里两个区域都已完成
     - 成立：``Root.Run{A: [done], B: [done]}``；永不：``Root.Run{A: [init]}``

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for text in (
       'called("Root.Run.RunEnter", step=0, where active("Root.Run{A: [init], B: [init]}"))',
       'called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [init], B: [init]}"))',
       'called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [done]}"))',
       'called("Root.Run.RunExit", step=1, where active("Root.Run{A: [done], B: [done]}"))',
       'called("Root.Run.RunExit", where active("Root.Run{A: [init]}"))',
       'called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{A: A1, B: [init]}"))',
       'called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{B: B1}"))',
       'called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{A: A1, B: B1}"))',
       'called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{B: [init]}"))',
   ):
       print(text)
       print("  " + verdict("region_calls.fcstm", "check reach <= 3: %s;" % text))

.. testoutput::

   called("Root.Run.RunEnter", step=0, where active("Root.Run{A: [init], B: [init]}"))
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [init], B: [init]}"))
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [done]}"))
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   called("Root.Run.RunExit", step=1, where active("Root.Run{A: [done], B: [done]}"))
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.RunExit", where active("Root.Run{A: [init]}"))
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{A: A1, B: [init]}"))
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{B: B1}"))
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{A: A1, B: B1}"))
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{B: [init]}"))
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS

同一周期里先走的区域，会把新位置显示给之后发出的调用；排在后面的区域在启动之前显示 ``[init]``。被重新进入的拥有者，它自己的 ``enter`` 看到 ``[init]``，而在它之前的 ``exit`` 与切面仍看到原位置。永不成立的模式和其他够不到的 ``reach`` 一样，只是上界内的回答。

调用上的 ``state=`` 与 ``active_leaf=`` 按仿真器交给处理器的状态统计（``ctx.state_path``、``ctx.active_leaf``）：即动作所包住的全部范围里最深的公共状态。拥有者的 ``>> during after`` 包住整组区域，所以对它来说两者都是拥有者：

.. list-table:: 各过滤器下的 ``GroupTail``\ （``Root.Run`` 的 ``>> during after``）
   :header-rows: 1
   :widths: 64 36

   * - 查询（``check reach <= 3``）
     - 结论
   * - ``called("Root.Run.GroupTail", state="Root.Run", active_leaf="Root.Run")``
     - 成立
   * - ``called("Root.Run.GroupTail", state="Root.Run.A.A1")``
     - 不成立
   * - ``called("Root.Run.GroupTail", active_leaf="Root.Run.B.B1")``
     - 不成立
   * - ``call_count("Root.Run.GroupTail", step=*) == 2``
     - 成立：运行这一组的两个周期里各调用一次
   * - ``call_count("Root.Run.GroupTail", step=*) == 3``
     - 不成立
   * - ``call_count(step=*, active_leaf="Root.Run") == 6``
     - 成立：``RunEnter`` 与 ``GroupTail``\ （周期 0），``RunExit``、``RunEnter`` 与 ``GroupTail``\ （周期 1），``RunExit``\ （周期 2）
   * - ``call_count(step=*, state="Root.Run") == 6``
     - 成立：同样这六次调用
   * - ``call_count("Root.Run.A.A1.AWork", step=*, active_leaf="Root.Run.A.A1") >= 1``
     - 成立：叶子的 ``during`` 报告叶子

下面的脚本运行表里的查询：

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for text in (
       'called("Root.Run.GroupTail", state="Root.Run", active_leaf="Root.Run")',
       'called("Root.Run.GroupTail", state="Root.Run.A.A1")',
       'called("Root.Run.GroupTail", active_leaf="Root.Run.B.B1")',
       'call_count("Root.Run.GroupTail", step=*) == 2',
       'call_count("Root.Run.GroupTail", step=*) == 3',
       'call_count(step=*, active_leaf="Root.Run") == 6',
       'call_count(step=*, state="Root.Run") == 6',
       'call_count("Root.Run.A.A1.AWork", step=*, active_leaf="Root.Run.A.A1") >= 1',
   ):
       print(text)
       print("  " + verdict("region_calls.fcstm", "check reach <= 3: %s;" % text))

.. testoutput::

   called("Root.Run.GroupTail", state="Root.Run", active_leaf="Root.Run")
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   called("Root.Run.GroupTail", state="Root.Run.A.A1")
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   called("Root.Run.GroupTail", active_leaf="Root.Run.B.B1")
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   call_count("Root.Run.GroupTail", step=*) == 2
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   call_count("Root.Run.GroupTail", step=*) == 3
     1 BMC reach <= 3: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   call_count(step=*, active_leaf="Root.Run") == 6
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   call_count(step=*, state="Root.Run") == 6
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   call_count("Root.Run.A.A1.AWork", step=*, active_leaf="Root.Run.A.A1") >= 1
     0 BMC reach <= 3: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND

计数的单位是调用，不是活动叶子：整组的 ``>> during after`` 每个周期只调用一次，不论它包住多少个区域（不含区域的状态上的切面则按活动叶子周期各执行一次）。

``case(...)`` 与局部情形
~~~~~~~~~~~~~~~~~~~~~~~~

含区域的模型里，一个宏步由一串有序的\ *局部情形*\ 组成：被进入的每个拥有者的初始转换、每个有工作的区域的一个分支（转换或回退），以及所有区域完成之后继续前行的拥有者的分支。``case("标签")`` 与 ``cover`` 性质指明其中一个局部情形；标签仍是四段式 ``source::kind::target::ordinal``，其中的状态路径会经过区域。作为 ``cover`` 的目标，``kind`` 必须是 ``transition`` 或 ``fallback``；``initial`` 标签是已知的，但不可覆盖。

.. testcode::

   import subprocess
   from pathlib import Path


   def verdict(model, query):
       Path("query.fbmcq").write_text(query + "\n")
       command = ["pyfcstm", "bmc", "-i", model, "-q", "query.fbmcq"]
       done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
       return "%d %s" % (done.returncode, done.stdout.splitlines()[0])

   for label in (
       "Job.Run.Prep.Wait::transition::Job.Run.Prep.Ready::0",
       "Job.Run.Work.Busy::fallback::Job.Run.Work.Busy::0",
       "Job.Run::transition::Job.Next::0",
       "Job.Run::initial::Job.Run.Prep.Wait::0",
       "Job.Run.Prep.Wait::transition::Job.Run.Prep.Nope::0",
   ):
       print(label)
       print("  " + verdict("region_job.fcstm", 'check cover <= 6: case("%s");' % label))

.. testoutput::

   Job.Run.Prep.Wait::transition::Job.Run.Prep.Ready::0
     0 BMC cover <= 6: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Job.Run.Work.Busy::fallback::Job.Run.Work.Busy::0
     0 BMC cover <= 6: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Job.Run::transition::Job.Next::0
     0 BMC cover <= 6: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Job.Run::initial::Job.Run.Prep.Wait::0
     1 Failed to compile BMC query: cover case label is not coverable: 'Job.Run::initial::Job.Run.Prep.Wait::0' has kind initial.
   Job.Run.Prep.Wait::transition::Job.Run.Prep.Nope::0
     1 Failed to compile BMC query: cover case label is unknown: 'Job.Run.Prep.Wait::transition::Job.Run.Prep.Nope::0'.

三种可覆盖的合法写法是：区域内的转换（第一条查询）、区域内的回退（``Job.Run.Work.Busy::fallback::Job.Run.Work.Busy::0``）以及拥有者自己的继续（``Job.Run::transition::Job.Next::0``）。最后一个的轨迹展示了一步里局部情形的顺序（摘录；``Prep`` 与 ``Work`` 是区域名，每个情形前面的作用域写成相对于最外层拥有者的路径，见 :doc:`../bmc_results/index_zh`\ ）：

.. code-block:: console

   $ echo 'check cover <= 6: case("Job.Run::transition::Job.Next::0");' > case_next.fbmcq
   $ pyfcstm bmc -i region_job.fcstm -q case_next.fbmcq
   ...
     5: Job.Run{Prep: Ready, Work: [done]}
          -> Job.Next [transition]
          Prep: Ready -> [done] [transition]
          Run: [start] -> Job.Next [transition]
   ...

``Prep: Ready -> [done]`` 先运行，因为 ``Prep`` 写在 ``Work`` 前面；``Run: [start] -> Job.Next`` 是拥有者的继续，在最后一个区域完成之后运行。``case("...")`` 作为 ``cover`` 之外的原子时，规则与不含区域的模型相同（``case_not_allowed``）；见证步里的 ``case_label`` 字段只命名在所有区域之外运行的那个分支，见 :doc:`../bmc_results/index_zh`\ 。

性质
----

所有边界都必须为正数。``N`` 包含帧 ``0 .. N``；任何性质都不声称有限范围
以外的结论。SAT 的极性随性质而异：``reach``、``exists_always``、``cover``
寻找期望见证；``forbid``、``invariant``、``must_reach``、``response`` 寻找反例。

对于某帧上的谓词 ``p``，令 ``defined(p)`` 表示所有算术定义域条件，并定义：

.. code-block:: text

   good(p)      = defined(p) and p
   bad_true(p)  = not defined(p) or p
   bad_false(p) = not defined(p) or not p

.. list-table:: 性质语义
   :header-rows: 1
   :widths: 18 20 36 26

   * - 类别
     - SAT 极性
     - 在边界内搜索的目标
     - 谓词未定义时
   * - ``reach``
     - 期望见证
     - 某帧存在 ``good(p)``。
     - 不能构成 reach 见证。
   * - ``forbid``
     - 反例
     - 某帧存在 ``bad_true(p)``。
     - 计为违反。
   * - ``invariant``
     - 反例
     - 某帧存在 ``bad_false(p)``。
     - 计为违反。
   * - ``must_reach``
     - 反例
     - 没有任何帧存在 ``good(p)``。
     - 不能满足最终到达义务。
   * - ``exists_always``
     - 期望见证
     - 同一条轨迹上每帧都有 ``good(p)``。
     - 破坏见证。
   * - ``cover``
     - 期望见证
     - 指定转换/回退分支在某一步被选择。
     - 不基于谓词。
   * - ``response``
     - 反例
     - 触发条件未定义，或定义为真的触发条件在后续 ``within`` 帧中没有定义为真的响应。
     - 未定义触发条件是违反；未定义响应不能满足义务。

``reach``
~~~~~~~~~

.. code-block:: fbmcq

   check reach <= 4: active("Root.Done");
   check reach <= 4: x >= 10 && !terminated();
   check reach <= 4: called("Root.A.Hook", step=*) && call_count(step=*) >= 2;

边界：``check reach <= 1: true;`` 可以在第 0 帧给出见证。
``check reach <= 0: true;`` 非法。主体中的事件原子或显式帧选择器是绑定错误。

``forbid``
~~~~~~~~~~

.. code-block:: fbmcq

   check forbid <= 5: active("Root.Fault");
   check forbid <= 5: temperature > 100 || retries > 3;
   check forbid <= 5: called(role="transition_effect", step=*);

边界：``check forbid <= 1: false;`` 在有定义轨迹上不存在真谓词违反。除零使谓词
未定义，因此会计为 ``forbid`` 违反。

``invariant``
~~~~~~~~~~~~~

.. code-block:: fbmcq

   check invariant <= 6: !terminated();
   check invariant <= 6: 0 <= pressure && pressure <= 200;
   check invariant <= 6: called("Root.A.Hook") implies active("Root.A");

边界：``check invariant <= 1: true;`` 检查第 0、1 两帧。任一帧为假或未定义都构成反例。

``must_reach``
~~~~~~~~~~~~~~

.. code-block:: fbmcq

   check must_reach <= 6: active("Root.Done");
   check must_reach <= 6: progress == 100;
   check must_reach <= 6: called("Root.Commit", step=*);

边界：``check must_reach <= 1: true;`` 没有反例，因为第 0 帧已经 good。这里 SAT
表示存在一条所有帧都不 good 的轨迹，不是期望的可达见证。

``exists_always``
~~~~~~~~~~~~~~~~~

.. code-block:: fbmcq

   check exists_always <= 4: active("Root.Safe");
   check exists_always <= 4: energy >= 0;
   check exists_always <= 4: !called(role="transition_effect") || x >= 0;

边界：``check exists_always <= 1: true;`` 要求第 0、1 两帧都定义为真。它对轨迹
作存在量化；``invariant`` 则以 SAT 目标搜索违反轨迹，两者不可混同。

``cover``
~~~~~~~~~

主体必须恰为 ``case("label")`` 或 ``case("label", current)``。合取、固定步选择器
和其他原子都会被拒绝。编译要求标签满足 ``source::kind::target::ordinal``，标签真实
存在，且 ``kind`` 为 ``transition`` 或 ``fallback``。``initial``、``absorb`` 和
``delta`` 是已知但不可覆盖的类别。

.. code-block:: fbmcq

   check cover <= 4: case("Root.Idle::transition::Root.Run::0");
   check cover <= 4: case("Root.Run::fallback::Root.Run::0");
   check cover <= 4: case("Root.Run::transition::Root.Done::2", current);

边界：``current`` 合法并规范化为省略选择器。以下查询在不同层失败：

.. code-block:: fbmcq

   check cover <= 4: active("Root.Run") && case("label");  // cover_predicate
   check cover <= 4: case("label", 2);                    // cover_predicate
   check cover <= 4: case("Root::initial::Root::0");      // 不可 cover
   check cover <= 4: case("missing");                     // schema 非法或标签未知

``response``
~~~~~~~~~~~~

``response`` 窗口为正数并使用严格后继：第 ``i`` 步的触发条件只能由
``i+1 .. i+within`` 帧响应。触发条件在 ``0 .. N-1`` 步求值，也是唯一允许
``event(path, current)`` 的上下文；响应侧不允许事件原子。

.. code-block:: fbmcq

   check response <= 8:
       trigger event("Root.Fault", current)
       -> within 3 active("Root.Recovering");

.. code-block:: fbmcq

   check response <= 5:
       trigger called("Root.Request", step=+0)
       -> within 2 called("Root.Acknowledge", step=-1..+0);

.. code-block:: fbmcq

   check response <= 6:
       trigger queue_depth > 0
       -> within 1 queue_depth == 0;

``within`` 大于剩余范围合法。若接近结尾的触发条件在第 ``N`` 帧之前未收到响应，
它进入独立的 ``incomplete`` 目标，而不会在未来帧不足时直接宣告违反。``within``
无需小于等于 ``N``。边界与非法形式：

.. code-block:: fbmcq

   check response <= 1: trigger true -> within 2 false;  // 合法，可能 incomplete
   check response <= 1: trigger true -> within 0 true;   // 窗口必须为正
   check response <= 2: true;                            // property body 错误
   check reach <= 2: trigger true -> within 1 true;      // reach 使用 response body
   check response <= 3: trigger true
       -> within 1 event("Root.E", current);             // event_not_allowed

合法、非法与不支持形式汇总
-----------------------------

.. list-table:: 失败边界速查
   :header-rows: 1
   :widths: 28 24 24 24

   * - 示例
     - 解析
     - 绑定
     - 下沉
   * - ``check reach <= 1: sqrt(x) >= 0;``
     - 合法
     - ``x`` 存在时合法
     - 合法；定义性要求 ``x >= 0``
   * - ``check reach <= 1: sin(x) >= 0;``
     - 合法
     - ``x`` 存在时合法
     - ``UnsupportedBmcQuery``
   * - ``check reach <= 1: x & 1 == 0;``
     - 合法
     - ``x`` 存在时合法
     - 当前 Int 配置不支持
   * - ``check reach <= 1: event("E", current);``
     - 合法
     - ``event_not_allowed``
     - 不会执行
   * - ``check cover <= 1: case("bad");``
     - 合法
     - 裸 cover 形状合法
     - 标签模式非法或未知
   * - ``assume at 1: true; check reach <= 1: true;``
     - 合法
     - 合法帧上边界
     - 合法
   * - ``assume event("E", 1) == true; check reach <= 1: true;``
     - 合法
     - ``event_selector_out_of_range``
     - 不会执行

模型感知绑定还会拒绝未知状态、事件、变量、抽象动作和具名引用路径，
拒绝仅含空白的引号引用，以及保留状态路径 ``$STATE_INIT`` 和
``$STATE_TERMINATE``。无模型的结构绑定可以验证上下文与范围，但不能证明名称存在。

.. list-table:: 常见稳定绑定诊断码
   :header-rows: 1
   :widths: 31 69

   * - 诊断码
     - 原因
   * - ``query_shape``
     - 非正数或畸形查询字段、仅含空白的引用，或其他 AST 形状违反。
   * - ``unknown_state`` / ``unknown_event`` / ``unknown_variable``
     - 模型感知引用不存在。
   * - ``reserved_state_path``
     - 用户文本引用 ``$STATE_INIT`` 或 ``$STATE_TERMINATE``。
   * - ``explicit_frame_selector``
     - 帧局部原子使用整数，而非省略/``current``。
   * - ``frame_selector_out_of_range``
     - ``assume at k`` 不满足 ``0 <= k <= N``。
   * - ``event_selector_out_of_range`` / ``event_range_out_of_range``
     - 事件假设点或区间不满足 ``0 <= k < N``。
   * - ``event_not_allowed`` / ``case_not_allowed``
     - 原子出现在不允许它的上下文。
   * - ``called_not_allowed`` / ``call_count_not_allowed``
     - 调用谓词出现在性质上下文之外。
   * - ``cover_predicate``
     - ``cover`` body 不是裸写的当前步 ``case`` 原子。
   * - ``call_step_out_of_range``
     - 绝对调用步或端点不在 ``0 .. N-1``。
   * - ``call_stage`` / ``call_role``
     - 过滤器值不属于文档规定的闭集。
   * - ``call_where_atom_not_allowed`` / ``cycle_not_allowed``
     - 调用快照谓词使用了除 ``active(...)`` 之外的轨迹原子（``terminated()``、``event()``、``case()``、``called()``）或裸 ``cycle``。
   * - ``invalid_active_pattern``
     - ``active(...)`` 里的配置模式不是该模型的模式：语法错误、状态不存在、状态没有这个区域、同一区域写了两次，或者在没有区域的模型里写了区域块。
   * - ``unknown_call_action`` / ``unknown_named_ref``
     - 模型感知调用元数据路径不存在。
   * - ``invalid_start_position``
     - ``init state(...)`` 的文本不是含区域模型的一个位置，或者让某个拥有者的全部区域都已完成。
   * - ``expression_too_deep``
     - 一个表达式的嵌套超过 100 层，例如几百个 ``&&`` 连成的链；请拆成几条子句。

源码与测试可追溯性
------------------

本参考逐项核对了：

* 文法与词元：``pyfcstm/bmc/grammar/BmcQueryParser.g4`` 和
  ``BmcQueryLexer.g4``；
* AST、默认值、规范文本和调用过滤器：``pyfcstm/bmc/ast.py`` 与 ``query.py``；
* 上下文与模型感知合法性：``pyfcstm/bmc/binding.py``；
* 冷启动、状态与终止源选择：``pyfcstm/bmc/source.py``；
* 定义性、调用过滤器、七种目标和不支持形式的下沉：``pyfcstm/bmc/relation.py``
  与 ``properties.py``；
* 可执行期望：``test/bmc/test_query_grammar.py``、``test_query_parser.py``、
  ``test_query_binding.py``、``test_query_expression_parity.py``、
  ``test_call_predicate_guards.py``、``test_relation_environment.py`` 和
  ``test_properties.py``。
