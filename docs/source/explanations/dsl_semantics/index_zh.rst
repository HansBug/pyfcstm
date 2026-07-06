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

.. _dsl-import-assembly-semantics-zh:

导入组装语义
------------

导入语法可以写在复合状态内，但文件加载和模块组装在解析之后运行。

.. code-block:: fcstm

   import "./import_worker.fcstm" as LeftWorker {
       def sensor_* -> left_$1;
       def speed -> plant_speed;
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
