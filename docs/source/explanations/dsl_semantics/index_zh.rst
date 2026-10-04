.. _sec-explanations-dsl-semantics-zh:

DSL 语义解释
============

.. contents:: 语义地图
   :local:
   :depth: 2

范围
----

本页解释 FCSTM DSL 为什么这样运行。精确语法表请看 :doc:`../../reference/dsl/index_zh`；首次跟做教程请看
:doc:`../../tutorials/dsl/index_zh`；更完整的仿真器内部顺序请看 :doc:`../execution_semantics/index_zh`。

本页首次出现必要英文术语时采用“中文（English）”格式，后文只使用中文。代码、DSL 关键字、诊断码、JSON 字段、命令和输出保持原文。

.. _dsl-root-design-zh:

为什么变量在唯一根状态之前
--------------------------

一个 FCSTM 模型（model）表示一个控制器（controller）、一棵状态树和一条活动状态栈（active-state stack）。持久变量
（persistent variable）放在根状态（root state）前面，是为了让守卫条件（guard）、效果动作（effect）、生命周期动作
（lifecycle action）、导入映射（import mapping）和诊断（diagnostic）都看到同一份数据表面。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

这不仅是解析器便利。代码生成需要一个运行时对象、一份变量存储和一个根活动栈。导入组装也需要一个宿主树，把被导入模块重写进去。

.. figure:: ../../tutorials/dsl/first_thermostat.fcstm.puml.svg
   :alt: 第一个温控器模型图
   :align: center

   这个图只有作者写的根复合状态和两个叶状态，没有任何生成节点。它说明最小模型已经具备三件事：一份变量表、一棵状态树和一组转换边。
   后面解释组合转换与强制转换时，所有生成结构都会在这三件事上继续投影。

检查命令能验证这一点：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/first_thermostat.fcstm --format human --color never

报告中的 ``root``、``states``、``transitions`` 和 ``variables`` 分别对应根状态、状态树、转换边和变量表。

.. _dsl-ownership-name-resolution-zh:

所有权树与名称解析
------------------

状态（state）、事件（event）、生命周期动作和导入都由某个状态拥有。转换（transition）只能直接命名它所在拥有者作用域
（owner scope）可见的端点（endpoint）。

.. code-block:: fcstm

   state Root {
       [*] -> Parent;

       state Parent {
           [*] -> ChildA;
           state ChildA;
           state ChildB;
           ChildA -> ChildB;
       }
   }

``ChildA -> ChildB`` 写在 ``Parent`` 内，因为 ``Parent`` 拥有这两个名字。如果父级规则直接写到嵌套私有叶状态，
外层逻辑就会依赖内部实现细节。推荐做法是进入复合状态边界，再由复合状态的初始转换选择子状态，或者把指向子状态的转换放到拥有该叶状态的复合状态内部。

检查输出的 ``transitions[].from_path`` 和 ``transitions[].to_path`` 会展示解析后的路径，可用于确认转换落在边界还是内部子状态。

.. _dsl-composite-entry-semantics-zh:

复合状态进入与初始转换
----------------------

复合状态（composite state）同时是边界和子状态选择规则。进入边界不等于已经处于某个叶子状态。

初始进入的概念顺序是：

1. 进入复合状态边界；
2. 评估并应用复合状态的初始转换；
3. 运行普通复合状态 ``during before``；
4. 进入选中的子状态。

子状态到子状态转换则是：

1. 来源子状态 ``exit``；
2. 转换 ``effect``；
3. 目标子状态 ``enter``。

普通复合状态 ``during before`` / ``during after`` 不包裹子状态内部切换。这样可以避免复合状态进入 / 退出行为变成每次内部切换都会触发的隐藏行为。

.. figure:: ../../tutorials/dsl/hierarchy_execution.fcstm.puml.svg
   :alt: 层级状态执行顺序示例图
   :align: center

   图中的父子层级用于观察“边界进入”和“子状态内部切换”的差异。复核时不要只看状态名称，还要配合检查输出中的
   ``states[].entry_actions``、``during_actions`` 和 ``exit_actions``：父状态的边界动作属于进入 / 离开边界，子状态之间的普通转换只运行来源子状态退出、转换效果动作和目标子状态进入。

从控制系统角度看，这个分层非常重要。复合状态通常表示一个控制区域或工作模式，叶状态表示区域内的具体步骤。如果每次子状态切换都自动运行父状态的普通
``during before`` / ``during after``，父状态就会被迫参与所有内部细节，模型会更难推理，也更难生成可预测代码。

.. _dsl-event-ownership-signal-zh:

事件作用域作为所有权信号
------------------------

事件拼写告诉读者信号由谁拥有：

.. list-table:: 事件所有权
   :header-rows: 1
   :widths: 22 36 42

   * - 拼写
     - 示例
     - 含义
   * - ``::``
     - ``Idle -> Heating :: Heat;``
     - 来源状态拥有私有事件名称。
   * - ``:``
     - ``Idle -> Running : Start;``
     - 包含状态或命名状态拥有事件路径。
   * - ``: /``
     - ``Worker -> Active : /Start;``
     - 路径从根状态拥有的事件命名空间开始。

这个区别会影响重构。来源本地事件可以跟着一个状态一起移动；根事件更像公开协议。组合触发项会继承前导作用域，除非后续项显式以 ``/`` 开始。

.. figure:: ../../tutorials/dsl/event_scoping_complete.fcstm.puml.svg
   :alt: 事件作用域示例图
   :align: center

   事件作用域图适合从“谁拥有信号”角度阅读。源码中的 ``::`` 表示来源状态私有事件；``: Name`` 表示包含状态或命名路径上的事件；
   ``: /Name`` 表示根状态拥有的事件。检查输出中的 ``event`` 和 ``event_scope`` 字段可以确认图中边的事件到底被归到哪个命名空间。

强制转换也使用类似触发拼写，但它是声明展开简写。强制触发器产生普通展开转换；它不是组合链，也不能带效果动作。

.. _dsl-expression-separation-zh:

守卫、效果动作与表达式分层
--------------------------

DSL 把数值表达式（numeric expression）和条件表达式（condition expression）分开，是因为数值计算与控制流决策的可移植风险和诊断需求不同。

.. code-block:: fcstm

   Sampling -> Done : if [sensor >= target] effect {
       next_sample = sensor + 1;
       alarm_count = (next_sample > target) ? alarm_count + 1 : alarm_count;
   };

守卫条件先被测试。效果动作只有在转换被选中后才运行。``next_sample`` 是效果动作块内的块内临时变量，离开块后不会成为持久状态。

目标配置警告也必须在这里保持精确。关于固定位宽整数范围、除法策略、移位计数或浮点位运算行为的数值诊断，是 ``c``、``c_poll``、``cpp``、``cpp_poll`` 的 C/C++ 部署配置警告，除非诊断明确另有说明。它不是 Python 生成运行时具有同样固定位宽或未定义行为风险的证据。

.. _dsl-lifecycle-hooks-semantics-zh:

生命周期、抽象钩子与引用
------------------------

生命周期动作把行为挂到状态边界和活动周期上：

* ``enter`` 属于进入；
* 普通叶状态 ``during`` 属于普通活动周期；
* ``exit`` 属于退出；
* 命名动作提供稳定的引用目标和生成钩子名称；
* ``abstract`` 表示生成代码调用用户实现；
* ``ref`` 复用命名生命周期动作路径。

.. code-block:: fcstm

   state Device {
       enter SharedInit {
           ready = 1;
       }
       state Idle {
           enter ref /SharedInit;
           during abstract PollHardware;
       }
   }

``ref`` 指向命名生命周期动作，不指向状态或事件。这样可复用行为仍然显式，不会把状态名称同时当作可调用过程。

.. figure:: ../../tutorials/dsl/abstract_reference_demo.fcstm.puml.svg
   :alt: 抽象动作与引用动作示例图
   :align: center

   这张图强调“状态路径”和“动作路径”不是同一回事。``ref`` 复用的是命名生命周期动作，生成运行时代码可以据此形成稳定钩子；
   它不是把某个状态当函数调用。检查输出的 ``actions`` 和动作引用图可用于复核引用是否指向动作。

.. _dsl-during-aspect-semantics-zh:

活动前后阶段与切面
------------------

两套不同功能都使用 ``during`` 阶段词汇：

* 普通 ``during before`` / ``during after`` 属于复合状态边界；
* ``>> during before`` / ``>> during after`` 是祖先状态贡献给后代叶状态活动周期的切面动作（aspect action）。

``hierarchy_execution.fcstm`` 用数值累加让顺序可观察。概念上，一个叶状态活动周期会看到：

.. code-block:: text

   ancestor >> during before
   parent   >> during before
   leaf     during
   parent   >> during after
   ancestor >> during after

子状态到子状态转换不运行普通复合状态 ``during before`` 或 ``during after``。组合伪中继状态也不执行切面动作。中继状态是路由结构；如果切面观察每个中继跳转，就会把实现细节变成业务行为。

切面更适合表达“控制区域的横切观测”，例如在所有后代叶状态活动周期前后做日志、计数或安全检查。它不适合表达业务路由，也不适合窥探组合转换的中间跳。

.. _dsl-combo-relay-semantics-zh:

伪状态与组合中继语义
--------------------

组合转换解决事件加守卫需求，不需要发明一个把普通事件后缀和普通守卫后缀混在一起的转换形式。

作者写的转换：

.. code-block:: fcstm

   Waiting -> Accepted :: Request + [ready > 0] + Confirm effect {
       accepted = accepted + 1;
   }

模型构建会把它展开成伪中继链。检查输出保留两种视图：

* ``combo_origins`` 记录原始触发项和源码位置；
* ``combo_transitions`` 记录带溯源信息的生成边；
* 生成伪状态使用保留 ``__combo_`` 前缀。

最终效果动作属于到 ``Accepted`` 的语义转换，不能复制到每个中继跳转。如果同一个周期中缺少某个必要事件或守卫项，链条不完成，可见状态不应悄悄前进到最终目标。

.. figure:: ../../tutorials/dsl/combo_transitions.fcstm.puml.svg
   :alt: 组合转换展开语义图
   :align: center

   图中的 ``__combo_`` 节点就是伪中继状态。它们没有业务生命周期动作，也不应该被用户当成可依赖的业务状态。
   从 ``Waiting`` 到 ``Accepted`` 的组合转换被拆成“事件 → 守卫 → 事件 + 效果动作”三段；只有最后一段进入业务目标并执行原始效果动作。

概念展开可以写成下列形状。真实名称会带哈希，下面只表达结构：

.. code-block:: fcstm

   Waiting -> __combo_waiting_request :: Request;
   __combo_waiting_request -> __combo_waiting_ready : if [ready > 0];
   __combo_waiting_ready -> Accepted :: Confirm effect {
       accepted = accepted + 1;
   }

.. list-table:: 组合转换语义断点
   :header-rows: 1
   :widths: 22 38 40

   * - 断点
     - 运行含义
     - 为什么这样设计
   * - 第一跳事件
     - 只消费 ``Request`` 并进入中继状态。
     - 保留事件顺序，不提前执行业务副作用。
   * - 中间守卫
     - 只测试 ``ready > 0``。
     - 守卫失败时链条停住，不伪装成已完成业务转换。
   * - 最后一跳事件
     - 消费 ``Confirm``、进入 ``Accepted``、执行原始效果动作。
     - 效果动作只执行一次，并且只在完整触发链满足后执行。
   * - 伪中继状态
     - 只承载路由，不承载业务动作。
     - 防止生成结构泄露成业务语义。

``W_COMBO_DUPLICATE_EVENT`` 和组合守卫诊断会指回作者写的触发项，而不仅仅指向生成伪状态。这就是检查诊断能指导用户或 LLM 回到原始 DSL 源码的原因。

.. _dsl-forced-transition-expansion-zh:

强制转换展开
------------

强制转换是另一种展开：它把一个来源模式复制到多个具体来源。

.. code-block:: fcstm

   !* -> ErrorHandler :: CriticalError;

展开后的转换在运行时上是普通转换：普通退出动作仍会运行，然后运行目标进入动作。强制转换不能带 ``effect`` 块，因为带副作用的多来源简写很难审计。若所有展开来源都需要同一更新，请把行为放在目标 ``enter``，或写显式普通转换。

强制转换也不能带组合 ``+`` 链。组合转换是有序中继展开；强制转换是来源集合展开。二者分开后，展开模型才容易检查。

.. figure:: ../../tutorials/dsl/forced_transitions.fcstm.puml.svg
   :alt: 强制转换展开语义图
   :align: center

   图中两条强制声明展开成多条普通转换。``!*`` 负责“当前拥有者作用域内所有适用来源”，``!Running`` 负责 ``Running`` 边界及其相关子路径。
   强制转换本身不携带效果动作；共享行为放在 ``SafeMode.enter`` 或 ``ErrorHandler.enter`` 这样的目标进入动作中。

.. list-table:: 强制转换与组合转换的差异
   :header-rows: 1
   :widths: 24 38 38

   * - 项目
     - 组合转换
     - 强制转换
   * - 展开维度
     - 按触发项顺序展开成中继链。
     - 按来源状态集合展开成多条边。
   * - 中间状态
     - 会生成伪中继状态。
     - 不用伪中继链表达触发顺序。
   * - 效果动作
     - 允许，但只挂在最后一跳。
     - 不允许；避免多来源副作用复制。
   * - 适用问题
     - 同一轮内事件、守卫按顺序满足。
     - 多个状态响应同一紧急事件或守卫。

.. _dsl-history-semantics-zh:

历史的语义与展开
----------------

离开一个复合状态再重新进入，通常会从它的初始转换重新开始。这适合“重新开始”，却不适合“暂停后继续”。历史（history，\ ``[H]`` / ``[H*]``\ ）表达的是后者：通过历史进入所有者时，恢复它上一次被离开时的配置。语法和完整写法见 :ref:`dsl-history-reference-zh`\ ；本节解释记录在什么时候写入、恢复做了什么，以及为什么普通状态机就能精确做到这一点。

三条运行时事实
~~~~~~~~~~~~~~

设计建立在 FCSTM 运行时的三条性质上。

.. list-table:: 历史依赖的运行时事实
   :header-rows: 1
   :widths: 8 46 46

   * - 事实
     - 性质
     - 对历史的推论
   * - F1
     - 转换只连接兄弟状态。所有者的 ``exit`` 只在“以所有者为来源的转换”提交时执行；强制的 ``!P -> Q`` 也会展开成以所有者为来源的边。
     - “所有者被离开”与“以所有者为来源的转换提交”是同一件事，写入点唯一。进入 ``O.[H]`` 的转换总是来自 ``O`` 之外（或者是 ``O`` 自己的外部自环）。
   * - F2
     - 一个周期从一个可停留叶出发，到下一个可停留叶结束；复合状态不能停在等待初始转换的位置。
     - 一个周期至多离开一个可停留叶，并且先叶后祖先，所以所有者退出前的配置，就是本周期出发时所在的叶。
   * - F3
     - 候选转换在变量副本上推测执行，失败时整体丢弃；初始转换按声明顺序尝试，前一条无法稳定时会继续尝试后一条。
     - 记录天然随失败的候选一起回滚。但恢复路由一旦验证失败，就会悄悄落到普通初始转换上，所以普通初始转换必须加闸门（见下文）。

执行规则
~~~~~~~~

.. list-table:: 历史规则
   :header-rows: 1
   :widths: 18 82

   * - 规则
     - 内容
   * - 归属
     - 每个所有者至多声明一个 ``[H]`` 和一个 ``[H*]``\ ，两者共用一份记录。根状态和叶状态都不能拥有历史。
   * - 记录
     - 所有者上一次被离开时所在的可停留叶（相对所有者的路径）。浅历史使用它的第一段，深历史使用完整路径。
   * - 写入
     - 只在以所有者为来源的转换提交时写入。所有者内部的转换、只离开内层复合状态、普通进入和恢复本身都不写入；失败的候选会撤销它的写入。
   * - 伪状态
     - 从不进入记录。一次只经过伪状态就离开的激活保留原有记录。
   * - ``O.[H]``
     - 有记录：进入记录中的直接子状态，再继续执行该子状态的普通初始转换。无记录：浅历史默认目标。
   * - ``O.[H*]``
     - 有记录：精确恢复记录的路径。路径上的普通初始转换（包括它们的守卫、事件和效果动作）都不执行；路径上的 ``enter`` 动作和普通 ``during before`` 照常执行。无记录：深历史默认目标。
   * - 读取
     - 普通进入忽略并保留记录；恢复只读，不消耗记录。只保留最近一次记录。
   * - 全有或全无
     - 如果恢复路径在本周期内到达不了可停留叶——例如记录中的子状态的初始转换被守卫挡住——整条历史转换会像其他失败的候选一样被拒绝，绝不会退化为普通进入。
   * - 业务数据
     - 不恢复变量；路径上的生命周期动作会再次执行。
   * - ``-> [*]``
     - FCSTM 没有终止状态。\ ``X -> [*]``\ 与其他退出一样离开所有者，所以记录是最后一个可停留叶。

记录只在所有者被离开时变化。以 :ref:`dsl-history-task-zh` 中的洗衣机为例，逐周期对照：

.. list-table:: 当前配置与记录
   :header-rows: 1
   :widths: 22 38 40

   * - 周期 / 事件
     - 周期结束后的活动叶
     - ``Program`` 的记录
   * - 1 初始化
     - ``Paused``
     - 无
   * - 2 ``Fresh``
     - ``Program.Idle``
     - 无
   * - 3 ``Start``
     - ``Program.Wash.Fill``
     - 无
   * - 4 ``Filled``
     - ``Program.Wash.Agitate``
     - 无
   * - 5 ``Pause``
     - ``Paused``
     - ``Wash.Agitate``\ （首次写入）
   * - 6 ``Shallow``
     - ``Program.Wash.Fill``
     - ``Wash.Agitate``\ （恢复不写入）
   * - 7 ``Pause``
     - ``Paused``
     - ``Wash.Fill``\ （被本次退出覆盖）
   * - 8 ``Deep``
     - ``Program.Wash.Fill``
     - ``Wash.Fill``
   * - 9 ``Pause``
     - ``Paused``
     - ``Wash.Fill``
   * - 10 ``Fresh``
     - ``Program.Idle``
     - ``Wash.Fill``\ （普通进入保留记录）
   * - 11 ``Pause``
     - ``Paused``
     - ``Idle``
   * - 12 ``Deep``
     - ``Program.Idle``
     - ``Idle``

这一完整序列就是共享语义夹具 ``history_washer_shallow_and_deep_restore``\ ，仿真器、全部五个生成的运行时和 BMC 都会重放它。

作者写法与展开结果
~~~~~~~~~~~~~~~~~~

模型转换在强制转换与组合转换展开之后再展开历史，这时每个历史入口都已经是一条具体的边。状态按前序编号，于是每棵子树对应一个连续的编号区间。四条改写实现上面的规则：

1. **记录**\ ：每个可停留叶的 ``exit`` 把自己的编号写入它上方每个所有者的记录。
2. **入口**\ ：进入 ``O.[H]`` / ``O.[H*]`` 的转换在效果动作末尾一次性算出恢复目标，写入 ``__hist_goto``\ 。
3. **路由**\ ：在通往任一可能目标的路径上，每个“复合状态、子状态”对生成一条带守卫的初始转换 ``[*] -> K : if [goto 落在 K 的区间]``\ ；进入叶状态时清除 ``goto``\ 。指向同一子状态的普通用户初始转换与这条路由合并。
4. **闸门**\ ：这些复合状态上其余的用户初始转换只在没有恢复经过时触发（\ ``goto == 0``\ ，或当复合状态本身就是恢复目标时 ``goto == id(C)``\ ），并且先清除 ``goto``\ 。带事件的初始转换会通过一个 ``__hist_gate_<n>`` 伪状态拆开。

洗衣机的 ``Program`` 展开后有两条初始转换，\ ``Wash``\ 有三条——与细心手写的等价代码数量相同。导出模型（\ ``str(machine.to_ast_node())``\ ）的精简片段，省略了无关行，短块合并为一行：

.. code-block:: fcstm

   Paused -> Program :: Deep effect {
       __hist_goto = (__hist_Program != 0) ? __hist_Program : 6;
   }
   // Program 内部
   [*] -> Wash : if [__hist_goto >= 5 && __hist_goto <= 7];
   [*] -> Idle : if [__hist_goto == 0 || __hist_goto == 4] effect {
       __hist_goto = 0;
   }
   // Wash 内部
   [*] -> Fill : if [__hist_goto == 6] effect { __hist_goto = 0; }
   [*] -> Agitate : if [__hist_goto == 7] effect { __hist_goto = 0; }
   [*] -> Fill : if [__hist_goto == 0 || __hist_goto == 5] effect {
       __hist_goto = 0;
       wash_initials = wash_initials + 1;
   }
   // Program 之下的每个叶状态
   state Agitate { exit { __hist_Program = 7; } }

.. figure:: ../../tutorials/dsl/history_washer.fcstm.puml.svg
   :alt: 带历史路由的展开后洗衣机模型
   :align: center

   PlantUML 绘制的展开后洗衣机模型。从 ``Paused`` 出发的两个历史入口计算 ``__hist_goto``\ ；\ ``Program`` 有一条进入 ``Wash`` 的路由（区间 5..7），以及它自己进入 ``Idle`` 的初始转换，这条初始转换与进入 ``Idle``\ （编号 4）的路由合并；\ ``Wash`` 有进入 ``Fill``\ （6）与 ``Agitate``\ （7）的路由，以及加了闸门的初始转换。图中文字只有代码标识符，所以两种语言共用一张图。

每一部分为什么正确：

* **记录正确。**\ 由 F2，离开所有者的那个周期从某个可停留叶出发，先叶后祖先地退出，途中不会再进入并离开另一个可停留叶。因此所有者退出前的最后一次写入就是那个叶——正是 SCXML 规定的“退出父状态之前的配置”。
* **只需要在读取时正确。**\ 只有所有者的叶会写它的记录，而这些叶只在所有者活动时退出，所以所有者不活动时变量保持不变。只有进入所有者的转换会读取它，由 F1，这时所有者必然不活动。
* **路由互斥。**\ 兄弟子树的编号区间不重叠，\ ``goto == 0``\ 排除所有路由，而且每个稳定点上 ``goto`` 都是 ``0``\ ，因为恢复会在叶上或复合目标的普通初始转换上清除它。
* **失败是原子的。**\ 所有写入都发生在候选的变量副本上（F3）。

为什么普通初始转换必须加闸门
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

没有闸门时，受阻的恢复会悄悄变成普通进入。以共享语义夹具 ``history_blocked_restore_is_rejected_gated_initial`` 的模型为例：\ ``K``\ 的初始转换是 ``[*] -> K1 : if [ready == 1];``\ ，而 ``Block`` 会把 ``ready`` 设为 ``0``\ 。

.. list-table:: 受阻的恢复：有闸门与无闸门
   :header-rows: 1
   :widths: 40 30 30

   * - 场景
     - 有闸门（展开结果）
     - 无闸门
   * - ``Fresh``\ 、\ ``Go``\ 、\ ``Stop``\ 、\ ``Block``\ 、\ ``Resume``\ ：浅历史记录为 ``K``\ ，而它的初始转换此时被挡住
     - 停在 ``Off``\ ；\ ``Resume``\ 没有被消费（全有或全无）
     - 落到 ``O.Idle``\ ；历史悄悄变成了普通进入
   * - ``Block``\ 、\ ``ResumeDeep``\ ：没有记录，深历史默认目标 ``K`` 被挡住
     - 停在 ``Off``
     - 落到 ``O.Idle``
   * - ``Block``\ 、\ ``Fresh``\ ：普通进入
     - ``O.Idle``
     - ``O.Idle``\ ——闸门从不改变普通进入

原因是 F3：路由验证失败后，运行时会尝试列表中的下一条初始转换。UML 与 SCXML 的初始转换不能带守卫或事件，所以不会遇到这个问题；这是 FCSTM 特有的。规则 4 中“先清除 ``goto``\ ”的顺序同样重要：当加闸门的初始转换本身进入嵌套历史（\ ``[*] -> S2.[H*];``\ ）时，它自己的效果动作已经为下一个所有者设置了 ``goto``\ ，之后再清除就会把它抹掉。共享语义夹具 ``history_nested_owner_initial_enters_inner_history`` 固定了这一点。

边界与反例
~~~~~~~~~~

* **不是并发。**\ FCSTM 只有一条活动路径，没有正交区域，也就不存在相互影响的多个历史。
* **不是持久化。**\ 记录就在状态机的变量里，与其他状态一样；跨进程保存由宿主负责（热启动通过 :meth:`pyfcstm.model.model.StateMachine.history_variables` 恢复它们）。
* **不恢复业务数据。**\ 恢复不会回滚变量；洗衣机的计数变量每次恢复都会继续累加。
* **不支持多层目标。**\ ``X -> P.O.[H]``\ 会被拒绝；请进入 ``P``\ ，由 ``P`` 在自己的作用域里进入 ``O.[H]``\ ，或者把历史声明在 ``P`` 上。
* **默认去向不能带效果动作。**\ ``[H] -> Child effect { ... }`` 不是合法写法；把效果动作放到历史入口转换上，或放进 ``Child`` 的 ``enter``\ 。
* **所有者活动时看不到原始记录。**\ 这时 ``__hist_<所有者>`` 会随叶的退出而变化；请在所有者不活动时用 ``history_record()`` 读取。
* **历史不会让卡住的模型变得可运行。**\ 恢复可能到达普通进入永远到达不了的配置（例如跳过的初始转换效果动作让某个变量保持另一个值）。如果那个配置会在伪状态之间循环，运行时报告的循环与不用历史、直接写出同一配置时完全一样。

单元测试之外的证据：维护命令 ``python tools/check_history_xstate.py --models 1500 --events 80``\ （先执行 ``npm ci --prefix tools/history_xstate``\ ）在 FCSTM 与 XState 5.33.2 上运行每个生成的模型，并在每个事件之后比较活动叶以及退出/进入顺序，输出 ``models=1489 steps=120609 transitions=84488 restores=12978 mismatching_models=0``\ 。这些模型覆盖两个引擎共有的语义；伪状态、守卫、组合转换与被阻塞的恢复在 XState 中的建模方式不同，它们由单元测试中的 FCSTM 专属判定器（oracle）在 120 个固定种子的随机模型上检查。

.. _dsl-import-assembly-semantics-zh:

导入组装语义
------------

导入语法可以写在复合状态内，但文件加载和模块组装在解析之后运行。

.. code-block:: fcstm

   import "./import_worker.fcstm" as LeftWorker {
       var sensor_* -> left_$1;
       var speed -> plant_speed;
       event /Start -> Start named "Shared Start";
   }

解析器记录路径、别名、可选显示名和映射语句。导入 / 模型层随后解析路径、加载被导入根状态、检查冲突、重写变量名、重写事件路径，并把被导入根状态作为别名下的子状态加入宿主模型。

映射模板不是任意代码。``$0`` 是完整匹配的被导入变量名；``$1`` / ``${1}`` 是通配选择器的捕获组；``*`` 是兜底模板。目录项目必须导入具体入口文件，例如 ``./line/main.fcstm``，因为裸目录不是 DSL 源文件。

.. figure:: ../../tutorials/dsl/import_host_mapped.fcstm.puml.svg
   :alt: 导入组装后的宿主模型图
   :align: center

   这个图展示宿主模型如何把被导入模块挂到别名下面。变量与事件映射不会在图上显示成一段脚本，但会影响检查输出中的变量表、事件表和转换路径。
   阅读导入示例时，应同时看源码、图和检查输出：源码说明映射规则，图说明状态树位置，检查输出说明重写结果。

设计边界
--------

DSL 有意比通用编程语言更窄：

* 操作块中没有循环；
* DSL 源文件中没有用户自定义函数；
* 普通转换不把事件语法和守卫语法写成两个后缀；
* 强制转换没有效果动作，也没有组合链；
* 组合中继伪状态是纯路由辅助节点；
* 目标风险诊断必须说明目标配置。

事件加守卫边界是有意暴露出来的。下面这种普通转换形式非法：

.. literalinclude:: ../../tutorials/dsl/event_guard_mixed_invalid.fcstm.txt
   :language: fcstm
   :caption: 非法普通事件加守卫后缀；预期解析器摘录：``Unexpected token 'if'``

需要同时要求事件和守卫时，请使用组合语法：

.. code-block:: fcstm

   A -> B :: Go + [ready > 0];

其他边界也会在解析器或模型验证层失败，而不是被静默改写。例如：带 ``effect`` 块的强制转换会被拒绝，而不是把副作用克隆到多个来源；带生命周期动作的组合中继伪状态会被拒绝或告警，因为它只是路由结构，不是业务状态；数值目标风险警告也必须限定到具有固定位宽或未定义行为风险的 C/C++ 部署配置。

这些边界让模型保持可解析、可检查、可仿真，并适合生成多种目标语言的代码。
