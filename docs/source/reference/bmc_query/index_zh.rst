:orphan:

FBMCQ 语言参考
==============

FBMCQ（FCSTM 有界模型检查查询语言，FCSTM bounded-model-checking query
language）是 :func:`pyfcstm.bmc.parse.parse_bmc_query` 接受的 ``.fbmcq``
语言。一个文件选择初始帧，可选地约束环境，并且声明且仅声明一个有界性质。
本页是可查阅的参考；示例足够小，可直接作为解析器或绑定器单测用例。

可用下面的本页目录直接定位完整文法、初始化、假设、表达式、原子、调用过滤器、
性质或合法性汇总。命令输出、退出状态、JSON、见证和重放字段请查
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
     - 使用相同的声明初始化策略。这是符号热启动；不会通过执行更早的入口 action 推导变量。
   * - ``init terminated;``
     - 终止哨兵。
     - 使用相同的声明初始化策略。

``havoc`` 跳过所选持久变量的声明初始化器。它并非赋予一个随机具体值；第 0 帧
符号保持自由，仍可由 ``where`` 约束。``havoc *`` 选择所有持久变量。
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

帧假设
~~~~~~

``assume always`` 作用于全部 ``N+1`` 帧；``assume at k`` 只作用于一帧，
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
     - 调用时的公开活跃叶状态路径。
   * - 具名引用
     - ``named_ref=STRING`` 或 ``named_ref=null``
     - 已存在的具名 ref 调用点，或明确要求不存在具名 ref。
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
   check reach <= 3: called("A", where active("Root.A"));   // call_where_atom_not_allowed

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
     - 调用快照谓词使用了轨迹原子或裸 cycle。
   * - ``unknown_call_action`` / ``unknown_named_ref``
     - 模型感知调用元数据路径不存在。

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
