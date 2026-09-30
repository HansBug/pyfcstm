
.. _sec-how-to-dsl-zh:

DSL 任务指南
============

.. contents:: 任务地图
   :local:
   :depth: 2

如何使用本页
------------

本页不是语法目录，而是 FCSTM DSL 的任务手册。每个任务配方都说明什么时候使用、推荐写法、如何验证、预期诊断、常见错误和深入阅读位置。

所有引用已检查示例的命令都默认从仓库根目录运行。

术语约定：本页首次出现必要英文术语时采用“中文（English）”格式，后文只使用中文。诊断（diagnostics）是
``pyfcstm inspect`` 给出的检查结果，目标配置（target profile）是生成目标语言或运行时配置，拥有者作用域
（owner scope）是拥有当前声明的状态作用域，端点（endpoint）是转换（transition）的来源或目标，伪中继状态
（pseudo relay state）是组合转换（combo transition）展开生成的纯路由节点。代码、命令、文件路径、JSON 字段、诊断码和 DSL
关键字保持原文。

.. _dsl-small-valid-model-task-zh:

写一个小型有效模型
------------------

当你需要在加入高级功能前做最小健全性检查（sanity check）时，从一个根复合状态（root composite）、一个初始转换（initial transition）和几个叶状态（leaf state）开始。

.. literalinclude:: ../../tutorials/dsl/first_thermostat.fcstm
   :language: fcstm
   :caption: 第一个可运行模型；预期诊断：无。

验证命令：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/first_thermostat.fcstm --format human --color never

预期摘要：

.. code-block:: text

   status: ok
   root: Thermostat
   diagnostics: 0 errors / 0 warnings / 0 infos

常见错误：在端点状态声明之前，或不在同一个拥有者作用域中写转换。除非转换本来就是进入或离开复合状态边界，否则应把端点和转换放在同一个拥有复合状态内。

.. _dsl-state-target-task-zh:

组织状态并解析目标
------------------

当转换报告找不到状态，或你不确定转换应该写在哪里时，用这个规则：转换只能直接引用当前拥有者作用域能看到的端点名称。

推荐完整模式：

.. code-block:: fcstm

   state Parent {
       [*] -> ChildA;
       state ChildA;
       state ChildB;
       ChildA -> ChildB;
   }

``ChildA -> ChildB`` 写在 ``Parent`` 内，因为 ``Parent`` 拥有这两个名字。从 ``Parent`` 外部进入时，应以 ``Parent`` 为目标，再由 ``Parent`` 的初始转换选择子状态。

常见错误：从外部直接以另一个复合状态拥有的子状态为目标。

.. code-block:: fcstm

   state Root {
       [*] -> Outside;
       state Outside;
       state Parent {
           [*] -> ChildA;
           state ChildA;
           state ChildB;
       }
       Outside -> ChildB;  // 错误：ChildB 不属于 Root
   }

修复方式是写 ``Outside -> Parent;``，或把指向子状态的转换移入 ``Parent``。精确规则见 :ref:`dsl-state-forms-zh` 和 :ref:`dsl-ownership-name-resolution-zh`。

如果把上面的坏模型保存为 ``/tmp/nested_target_invalid.fcstm``，可用下面命令验证失败：

.. code-block:: bash

   pyfcstm inspect -i /tmp/nested_target_invalid.fcstm --format human --color never

预期会看到：

.. code-block:: text

   Invalid state machine model ... Unknown to state 'ChildB' of transition:
   Outside -> ChildB; (line 9)

验证一个已检查层级示例：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/hierarchy_execution.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: HierarchyDemo
   diagnostics: 0 errors / 1 warnings / 1 infos

伪状态只负责路由，是叶状态辅助节点，不应承载业务生命周期行为。这个遗留伪状态示例作为已检查资源保留：

.. literalinclude:: ../../tutorials/dsl/pseudo_state_demo.fcstm
   :language: fcstm
   :caption: 伪状态路由示例；预期诊断：一个 ``W_UNREFERENCED_VAR`` 和三个 ``I_TRANSITION_NEVER_EVENT_TRIGGERED``\ 。

.. _dsl-event-scopes-task-zh:

编写事件作用域
--------------

离散外部触发建议用事件。根据所有权选择拼写：

.. list-table:: 事件作用域写法
   :header-rows: 1
   :widths: 24 34 42

   * - 需求
     - 写法
     - 含义
   * - 来源状态私有事件
     - ``Idle -> Heating :: Heat;``
     - 事件归 ``Idle`` 本地拥有。
   * - 包含状态或命名状态拥有的事件
     - ``Idle -> Running : Start;``
     - 事件沿所有权链解析。
   * - 根状态拥有的事件
     - ``Worker -> Active : /Start;``
     - 事件路径从根状态下方开始。

已检查示例：

.. literalinclude:: ../../tutorials/dsl/event_scoping_complete.fcstm
   :language: fcstm
   :caption: 完整事件作用域示例；预期诊断：演示用 ``counter`` 触发 ``W_UNREFERENCED_VAR``\ 。

.. figure:: ../../tutorials/dsl/event_scoping_complete.fcstm.puml.svg
   :alt: 事件作用域状态图
   :align: center

   阅读这张图时，先问每个信号由谁拥有。使用 ``::`` 的边消费来源状态本地事件；使用
   ``: Name`` 的边消费包含状态或命名状态拥有的事件；使用 ``: /Name`` 的边消费根事件命名空间下的事件。
   复核时查看 ``events[].qualified_name`` 和 ``events[].scope``\ ，确认检查报告中的拥有者与图中标签一致。

验证命令：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/event_scoping_complete.fcstm --format json

在 JSON 中查看 ``events[].qualified_name`` 和 ``events[].scope``。为了可读性，推荐写成 ``: /Start``\ ，因为它把事件作用域
``:`` 词法符号和绝对根路径分开。当前解析器也接受紧凑写法 ``:/Start``\ ，并会序列化成同一个绝对事件，
但带空格的写法更适合教学、搜索和复核。

常见错误：不要只因为“看起来更短”就在 ``::`` 和 ``:`` 之间切换。这个拼写会改变事件拥有者，进而影响导入映射、
仿真输入名称和检查报告的 ``events[].scope`` 输出。

.. _dsl-guards-effects-task-zh:

编写守卫条件、效果动作和操作块
--------------------------------

守卫条件决定转换是否可用。效果动作在来源退出之后、目标进入之前更新变量。

完整操作块示例：

.. literalinclude:: ../../tutorials/dsl/operation_blocks_complete.fcstm
   :language: fcstm
   :caption: 赋值、块内临时变量、``if`` / ``else if`` / ``else``、空语句和三目赋值；预期诊断：无。

示例中的关键点：

* ``delta`` 和 ``next_sample`` 是块内临时变量，只能在同一个块内赋值后读取。
* 操作块内支持 ``if [condition] { ... } else if [condition] { ... } else { ... }``。
* 单独的 ``;`` 是合法空操作语句。
* 守卫条件和赋值右侧是不同表达式上下文。

验证命令：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/operation_blocks_complete.fcstm --format human --color never

常见错误：如果看到 ``E_UNDEFINED_VAR`` 且 ``refs.is_temporary=true``，通常说明临时变量在同一个块内先被读取后被赋值。

.. _dsl-expression-safety-task-zh:

安全使用表达式
--------------

表达式有三个上下文：

.. list-table:: 表达式上下文
   :header-rows: 1
   :widths: 22 38 40

   * - 上下文
     - 接受
     - 不接受
   * - ``init_expression``
     - 字面量、``pi`` / ``E`` / ``tau``、算术、位运算、一元数学函数
     - 运行时变量读取、三目表达式
   * - ``num_expression``
     - 运行时变量、算术、位运算、数学函数、数值三目表达式
     - 条件专用运算符直接出现在数值赋值中
   * - ``cond_expression``
     - 比较、``&&`` / ``and``、``||`` / ``or``、``!`` / ``not``、``=>`` / ``implies``、``xor``、``iff``、条件三目表达式
     - 数值赋值语句

已检查示例：

.. literalinclude:: ../../tutorials/dsl/expression_condition_ternary.fcstm
   :language: fcstm
   :caption: 运行时表达式、条件运算符、蕴含、xor / iff 和三目形式；预期诊断：无。

常见拼写陷阱：

片段模式（片段，不是完整已验证文件；后面有完整已验证文件）：

.. code-block:: fcstm

   // 正确：布尔异或使用 "xor"。
   A -> B : if [(left > 0) xor (right > 0)];

   // 正确：蕴含在条件中使用 "=>" 或 "implies"。
   A -> B : if [request > 0 => ready > 0];

   // 正确：数值位异或仍然是 "^"。
   flags = flags ^ 0x01;

不要用 ``->`` 表示蕴含；它是转换语法。不要把 ``^`` 当布尔异或。完整优先级见 :ref:`dsl-expression-reference-zh` 和 :ref:`dsl-expression-separation-zh`。

验证已检查表达式示例：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/expression_condition_ternary.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: ExpressionConditionTernary
   diagnostics: 0 errors / 0 warnings / 0 infos

.. _dsl-lifecycle-task-zh:

编写生命周期钩子、引用和抽象钩子
--------------------------------

模型自己拥有行为时使用具体生命周期动作；生成代码需要调用用户行为时使用 ``abstract``；多个状态复用命名生命周期动作时使用 ``ref``。

片段模式（片段，不是完整已验证文件；后面有完整已验证文件）：

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

``ref`` 指向命名生命周期动作，不指向状态或事件。
常见错误：``enter ref /Idle`` 是在引用状态路径，而不是命名生命周期动作。应先命名动作，再引用这个动作路径。

.. literalinclude:: ../../tutorials/dsl/abstract_reference_demo.fcstm
   :language: fcstm
   :caption: 抽象动作和引用动作示例；预期诊断：两个 ``I_UNREFERENCED_VAR_MAYBE_ABSTRACT`` 和一个 ``I_TRANSITION_NEVER_EVENT_TRIGGERED``\ 。

生命周期顺序可参考：

.. figure:: ../../tutorials/dsl/leaf_state_lifecycle.puml.svg
   :alt: 叶状态生命周期
   :align: center

   叶状态在变为活动时执行 ``enter``\ ，保持活动时执行 ``during``\ ，离开前执行 ``exit``\ 。
   这是作者写出的业务行为，不是组合转换生成的中继结构。

.. figure:: ../../tutorials/dsl/composite_state_lifecycle.puml.svg
   :alt: 复合状态生命周期
   :align: center

   复合状态是子状态选择边界。普通 ``during before`` / ``during after`` 是边界动作；
   它们不同于祖先 ``>> during`` 切面，也不会观察组合中继链里的每一跳。

.. figure:: ../../tutorials/dsl/abstract_reference_demo.fcstm.puml.svg
   :alt: 抽象动作和引用动作状态图
   :align: center

   这张图用来区分动作路径和状态路径。``ref`` 复用命名生命周期动作，不调用状态或事件。
   如果 ``ref`` 路径看起来意外，应同时检查动作列表和引用关系。

验证已检查生命周期示例：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/abstract_reference_demo.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: AbstractReferenceDemo
   diagnostics: 0 errors / 0 warnings / 3 infos

.. _dsl-aspect-task-zh:

使用活动切面
------------

当祖先状态需要在后代叶状态活动周期前后做监控或日志时，使用 ``>> during before`` 和 ``>> during after``。不要把它们和复合状态的普通 ``during before`` / ``during after`` 混为一谈。

.. literalinclude:: ../../tutorials/dsl/hierarchy_execution.fcstm
   :language: fcstm
   :caption: 切面与层级执行示例；预期诊断：``W_UNREFERENCED_VAR`` 和 ``I_TRANSITION_NEVER_EVENT_TRIGGERED``\ 。

.. figure:: ../../tutorials/dsl/hierarchy_execution.fcstm.puml.svg
   :alt: 层级执行状态图
   :align: center

   这张图把作者写出的层级和运行时顺序分开看。父状态与子状态是作者 DSL 节点；
   切面动作不是业务状态，也不会画成组合中继节点。复核行为挂在边界上还是后代叶周期上时，
   应把检查输出里的生命周期 / 动作字段和图中的层级一起读。

解释：

* 祖先状态 ``>> during before`` 在活动叶状态 ``during`` 前运行；
* 祖先状态 ``>> during after`` 在活动叶状态 ``during`` 后运行；
* 普通复合状态 ``during before`` / ``during after`` 属于复合状态进入/退出语义，不包裹子状态到子状态转换；
* 切面动作不在组合伪中继状态内运行。

常见错误：不要用切面去观察组合中继跳转。伪中继状态是生成的路由结构；业务日志应放在作者写的状态或转换效果动作上。

详见 :ref:`dsl-during-aspect-semantics-zh`。

验证已检查切面示例：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/hierarchy_execution.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: HierarchyDemo
   diagnostics: 0 errors / 1 warnings / 1 infos

.. _dsl-forced-transition-task-zh:

编写强制转换
----------------------

当一个声明要展开到多个来源状态时使用强制转换。强制转换是展开简写，不是隐藏共享副作用的办法。

.. literalinclude:: ../../tutorials/dsl/forced_transitions.fcstm
   :language: fcstm
   :caption: 强制转换示例；预期诊断：两个演示变量触发 ``W_UNREFERENCED_VAR``\ 。

.. figure:: ../../tutorials/dsl/forced_transitions.fcstm.puml.svg
   :alt: 强制转换展开图
   :align: center

   这张图展示强制转换展开后的结构。源码里只有两条强制声明，但检查模型中会出现多条带
   ``forced_origin`` 的展开转换。图中 ``Running`` 的子状态也会通过退出标记参与紧急停止路径，
   这说明强制转换不是“跳过层级”，而是在展开后仍遵循普通退出语义。

规则：

* ``!State -> Target :: Event;`` 从命名来源及其可达嵌套来源展开。
* ``!* -> Target :: Event;`` 从拥有者作用域内所有适用来源展开。
* 强制转换可以带一个本地、链式 / 根事件或守卫触发器。
* 它不能带组合 ``+`` 链，也不能有 ``effect`` 块。

需要共享副作用时，把行为放到目标状态 ``enter``，或写显式普通转换。原因见 :ref:`dsl-forced-transition-expansion-zh`。

常见错误：``!* -> Target :: Event effect { ... };`` 是非法的。强制转换会展开成多条普通转换，复制副作用会隐藏行为；需要效果动作时请写显式普通转换。

验证展开规模：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/forced_transitions.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: System
   transitions: 17
   diagnostics: 0 errors / 2 warnings / 0 infos

展开读法：

.. list-table:: 强制转换展开读法
   :header-rows: 1
   :widths: 26 34 40

   * - 作者写法
     - 展开效果
     - 用户应检查什么
   * - ``!* -> ErrorHandler :: CriticalError;``
     - 当前拥有者作用域内多个状态都能响应 ``CriticalError``。
     - ``forced_transitions[].from_path`` 为 ``*``，``expansion_count`` 给出展开数量。
   * - ``!Running -> SafeMode :: EmergencyStop;``
     - ``Running`` 及其相关子路径会得到紧急停止出口。
     - 展开边的 ``forced_origin`` 保留原始声明文本。
   * - 不允许 ``effect``
     - 展开不会复制副作用。
     - 共享副作用应放到 ``SafeMode.enter`` / ``ErrorHandler.enter``，或写显式普通转换。

.. _dsl-combo-transition-task-zh:

编写组合转换
---------------------

当一个转换需要在同一个周期内按顺序满足多个事件项和守卫项时，使用组合触发器。组合转换在模型构建阶段展开成伪中继状态；仿真、检查、生成和 PlantUML 都消费展开后的模型。

.. literalinclude:: ../../tutorials/dsl/combo_transitions.fcstm
   :language: fcstm
   :caption: 普通组合、初始组合、守卫别名、根事件项、效果动作和生成的伪中继状态；预期诊断：无。

.. figure:: ../../tutorials/dsl/combo_transitions.fcstm.puml.svg
   :alt: 组合转换展开图
   :align: center

   图中的 ``__combo_`` 节点是生成的伪中继状态，不是作者写的业务状态。以
   ``Waiting -> Accepted :: Request + [ready > 0] + Confirm`` 为例，图中会先从
   ``Waiting`` 到第一个中继节点消费 ``Request``，再经过守卫边，最后消费 ``Confirm`` 进入
   ``Accepted``。原始效果动作只在最后一跳执行。

验证展开：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_transitions.fcstm --format json

JSON 中重点看：

* ``combo_origins`` 保留作者写的触发器和每个项；
* ``combo_transitions`` 列出带溯源信息的生成边；
* ``states`` 中会出现 ``is_pseudo=true`` 且以 ``__combo_`` 开头的生成伪状态。

概念展开：

.. code-block:: fcstm

   // 作者写法
   Waiting -> Accepted :: Request + [ready > 0] + Confirm effect {
       accepted = accepted + 1;
   }

   // 概念展开。真实中继名带哈希，不应手写。
   Waiting -> __combo_waiting_request :: Request;
   __combo_waiting_request -> __combo_waiting_ready : if [ready > 0];
   __combo_waiting_ready -> Accepted :: Confirm effect {
       accepted = accepted + 1;
   }

.. list-table:: 组合转换展开读法
   :header-rows: 1
   :widths: 24 36 40

   * - 触发项
     - 展开边
     - 用户应检查什么
   * - ``Request``
     - 从业务状态到第一个伪中继状态的事件边。
     - ``combo_transitions`` 中这一跳 ``effect`` 为空。
   * - ``[ready > 0]``
     - 两个伪中继状态之间的守卫边。
     - 守卫失败时不会进入目标状态。
   * - ``Confirm``
     - 最后一跳进入目标状态。
     - 原始 ``effect`` 只在这一跳出现。
   * - ``__combo_`` 状态
     - 生成的纯路由节点。
     - 不写业务动作；不执行切面动作。

修复示例：

.. code-block:: fcstm

   // 错误：普通事件后缀后又接守卫后缀。
   A -> B :: Go if [ready > 0];

   // 正确：组合转换使用方括号守卫项。
   A -> B :: Go + [ready > 0];

重复事件项合法但可疑。已验证警告示例：

.. literalinclude:: ../../tutorials/dsl/combo_duplicate_event.fcstm
   :language: fcstm
   :caption: 故意重复事件项的组合示例；预期诊断：``W_COMBO_DUPLICATE_EVENT`` 和 ``I_TRANSITION_NEVER_EVENT_TRIGGERED``\ 。

.. _dsl-history-task-zh:

用历史恢复复合状态
------------------

当离开一个复合状态之后再回来，需要从离开时的位置继续、而不是从头开始时，使用历史（history）。下面以洗衣机模型为起点：\ ``Program``\ 可以暂停，之后既可以重新进入，也可以通过浅历史（shallow history）或深历史（deep history）恢复。

.. literalinclude:: ../../tutorials/dsl/history_washer.fcstm
   :language: fcstm
   :caption: ``Program``\ 上的浅历史与深历史；预期诊断：四个计数变量各有一条 ``W_UNREFERENCED_VAR`` 警告。

1. **在复合状态内部声明历史**\ （这个复合状态称为历史的所有者）。\ ``[H] -> Idle;``\ 声明浅历史，\ ``[H*] -> Wash.Fill;``\ 声明深历史。箭头右侧只是所有者还没有记录时的去向：浅历史的默认目标必须是直接子状态，深历史的默认目标可以是相对所有者书写的任意后代路径。
2. **在所有者的父作用域里通过历史进入。**\ 把所有者写成目标并加上标记：\ ``Paused -> Program.[H] :: Shallow;``\ 。所有普通转换写法都接受历史目标：事件与守卫触发、组合触发、\ ``effect``\ 块、\ ``!State``\ 与 ``!*`` 强制转换、父状态的初始转换 ``[*] -> Program.[H*];``\ ，以及外部自环 ``!Program -> Program.[H*] :: Reenter;``\ 。
3. **运行模型。**\ 演示脚本在 ``Agitate`` 暂停，然后分别通过两种历史各恢复一次：

   .. literalinclude:: ../../tutorials/dsl/history_washer.demo.sh
      :language: bash
      :caption: ``history_washer.demo.sh``

   由脚本生成的输出：

   .. literalinclude:: ../../tutorials/dsl/history_washer.demo.sh.txt
      :language: text

   深历史精确恢复到 ``Wash.Agitate``\ ：\ ``fill_entries``\ 仍为 1，\ ``wash_initials``\ 也仍为 1，因为恢复路径上的初始转换不会执行。浅历史只记住直接子状态 ``Wash``\ ，所以进入 ``Wash`` 后会再次执行它的普通初始转换（\ ``wash_initials``\ 变为 2）。两个 ``__hist_*`` 变量就是展开后的历史，见第 5 步。
4. **检查模型。**\ 检查按作者书写的模型进行判断，因此历史本身不会产生额外的诊断：

   .. code-block:: bash

      pyfcstm inspect -i docs/source/tutorials/dsl/history_washer.fcstm --format human --color never

   预期输出片段（已截断）：

   .. code-block:: text

      states: 7 total / 4 leaf
      transitions: 13
      variables: 4
        program_entries: control; external supply: none
        ...
      diagnostics: 0 errors / 4 warnings / 0 infos

   四条警告是计数变量的 ``W_UNREFERENCED_VAR``\ 。报告描述的是展开前的模型：它列出四个计数变量，但没有任何 ``__hist_*`` 变量；\ ``transitions: 13``\ 只统计文件中书写的转换（强制转换 ``!Program`` 已展开），不包含展开生成的路由。
5. **带着记录热启动。**\ 历史会展开成仿真器、生成代码与 BMC 都能看到的普通 ``int`` 变量：\ ``__hist_goto``\ （进行中的恢复，在稳定点上总是 ``0``\ ）以及每个所有者一个 ``__hist_<所有者>`` 记录。热启动必须像其他持久变量一样提供它们。请用 :meth:`pyfcstm.model.model.StateMachine.history_variables` 从源码层面的记录换算，而不要手写编号：

   .. code-block:: python

      from pyfcstm.model import load_state_machine_from_text
      from pyfcstm.simulate import SimulationRuntime

      machine = load_state_machine_from_text(open("history_washer.fcstm").read())
      user = {"program_entries": 0, "fill_entries": 0, "agitate_entries": 0, "wash_initials": 0}
      runtime = SimulationRuntime(
          machine,
          initial_state="Washer.Paused",
          initial_vars={**user, **machine.history_variables({"Washer.Program": "Wash.Agitate"})},
      )
      runtime.cycle()
      runtime.cycle(["Washer.Paused.Deep"])
      print(".".join(runtime.current_state.path))   # Washer.Program.Wash.Agitate
      print(machine.history_record(runtime.vars, "Washer.Program"))   # Wash.Agitate

   ``history_record()``\ 把记录解码回叶路径，只在所有者不活动时有意义。如果热启动给出的 ``__hist_goto`` 不是 ``0``\ ，或者记录不是所有者下某个可停留叶的编号，仿真器会拒绝，并在报错里按叶路径列出合法编号。\ ``pyfcstm simulate``\ 的 ``init`` 命令接受同样的变量，例如 ``__hist_goto=0 __hist_Program=7``\ 。

常见错误与修复：

.. list-table::
   :header-rows: 1
   :widths: 30 34 36

   * - 现象
     - 原因
     - 修复
   * - ``E_HISTORY_TARGET_UNDECLARED``\ ：\ ``R.O does not declare shallow history``
     - 写了 ``X -> O.[H]``\ ，但 ``O`` 内部没有 ``[H] -> ...;``\ 。历史不会被隐式提供。
     - 在 ``O`` 中补上声明，或者普通地进入 ``O``\ 。
   * - ``E_HISTORY_DECLARATION_INVALID``\ ，\ ``reason: default_not_direct_child``
     - ``[H] -> W.W1;``\ ——浅历史只记住直接子状态。
     - 改成 ``[H] -> W;``\ ，或者声明 ``[H*] -> W.W1;``\ 。
   * - ``E_HISTORY_DECLARATION_INVALID``\ ，原因为 ``default_not_found``\ 、\ ``default_pseudo``\ 、\ ``root_owner`` 或 ``leaf_owner``
     - 默认目标不存在或是伪状态，或者根状态、叶状态声明了历史。
     - 让默认目标指向所有者下真实存在的状态；把历史声明在会被离开又重新进入的复合状态里。
   * - ``W_HISTORY_UNUSED``
     - 声明了某种历史，但没有任何 ``Owner.[H]`` / ``Owner.[H*]`` 目标使用它。
     - 在需要恢复的地方加上目标，或者删掉这条声明。
   * - ``E_HISTORY_RESERVED_PREFIX``
     - 使用了历史的模型里，有变量、状态或临时变量命名为 ``__hist_x`` 或 ``_hist_x`` 这样的形式。
     - 改名；目标语言会合并连续下划线，两者都会与展开生成的名字冲突。
   * - 恢复事件没有被消费，状态机停在原地
     - 恢复路径受阻，例如记录中的子状态的初始转换守卫为假。整条转换会被有意拒绝，绝不会退化为普通进入。
     - 让记录的路径可以进入，或者为这种情况单独写一条普通进入。见 :ref:`dsl-history-semantics-zh`\ 。

复现第一种错误：把下面的模型保存为 ``undeclared.fcstm``\ ，其中 ``O`` 没有声明历史，

.. code-block:: fcstm

   state R {
       state A;
       state O { state B; [*] -> B; }
       [*] -> A;
       A -> O.[H] :: Resume;
   }

再用 ``--collect-errors`` 检查：

.. code-block:: bash

   pyfcstm inspect -i undeclared.fcstm --collect-errors --format human --color never

预期输出片段：

.. code-block:: text

   [ERROR] E_HISTORY_TARGET_UNDECLARED
     R.O does not declare shallow history ([H] -> ...;), so it cannot be entered through O.[H].
     --> undeclared.fcstm:5:5

全部写法、诊断与展开生成的名字见 :ref:`dsl-history-reference-zh`\ ；执行规则及其成立的原因见 :ref:`dsl-history-semantics-zh`\ 。

.. _dsl-import-task-zh:

组装导入
-----------

当一个复合状态需要把另一个 FCSTM 模块作为子状态时使用导入。导入语法在 DSL 中解析；路径解析和组装在 Python 模型 / 导入层执行。

基本导入：

.. literalinclude:: ../../tutorials/dsl/import_host_basic.fcstm
   :language: fcstm
   :caption: 基本导入宿主模型；预期诊断：两个 ``W_UNREFERENCED_VAR``\ 。

映射导入：

.. literalinclude:: ../../tutorials/dsl/import_host_mapped.fcstm
   :language: fcstm
   :caption: 带变量和事件映射的导入；预期诊断：三个 ``W_UNREFERENCED_VAR``\ 。

.. figure:: ../../tutorials/dsl/import_host_mapped.fcstm.puml.svg
   :alt: 导入映射后的宿主模型图
   :align: center

   图中宿主模型把被导入模块挂到别名下面。映射不是文本替换脚本，而是模型组装阶段的重写：
   变量名和事件路径按映射表变成宿主可见的名称。复核时应同时看图中的状态树和检查输出中的变量、事件、转换路径。

被导入工作模块：

.. literalinclude:: ../../tutorials/dsl/import_worker.fcstm
   :language: fcstm
   :caption: 被导入工作模块；预期诊断：两个 ``W_UNREFERENCED_VAR``\ 。

目录入口导入：

.. literalinclude:: ../../tutorials/dsl/import_host_directory.fcstm
   :language: fcstm
   :caption: 通过显式 ``main.fcstm`` 入口文件执行目录式导入；预期诊断：``W_UNUSED_EVENT``、``W_LEAF_NO_OUTGOING_TRANSITION`` 和 ``W_UNREFERENCED_VAR``\ ，均来自演示用被导入资源。

映射事实：

* ``var speed -> plant_speed;`` 映射一个被导入变量到一个宿主变量。
* ``var sensor_* -> left_$1;`` 捕获通配后缀，并插入目标模板。
* ``var * -> prefix_$0;`` 是兜底映射；``$0`` 表示完整被导入变量名。
* ``event /Start -> Start;`` 映射被导入根事件到宿主事件。
* 目录项目必须导入具体入口文件，例如 ``./import_line/main.fcstm``；裸目录不是 DSL 文件。

常见错误：裸目录路径不会被当作 DSL 源加载；``var sensor_* -> left_$2;`` 这样的越界占位符
会触发导入映射验证错误。``$0`` 表示完整被导入名称，``$1`` / ``${1}`` 表示第一个通配捕获。
展开后的目标必须是合法 DSL 标识符，不能是空捕获、数字名称或 ``input``、``param`` 等保留字。

``var`` 是规范映射关键字，``def`` 保留为显式旧拼写。数值类型必须一致。子 ``input`` 可以绑定父四种角色；子 ``param`` 只能绑定父 ``param``；子 ``control/output`` 只能绑定父 ``control/output``。合法绑定采用父角色，完整结果矩阵见 :ref:`dsl-import-forms-zh`。

父级必须显式声明跨角色目标。缺失目标按子角色创建；同角色隐式共享必须有一致默认值，``input`` 共享必须显式声明。显式父默认值优先，多个合法写入者不增加限制。源只读变量的非法写入在映射前拒绝。收集诊断模式下，失败的变量绑定不会提交该导入的声明和子状态，诊断保留源文件及导入位置。

以下示例要求已安装 pyfcstm。在同一目录保存 ``child.fcstm``：

.. code-block:: fcstm

   input int reading;
   output int result = 0;
   state Child { enter { result = reading; } }

保存 ``host.fcstm``，把子输入绑定父控制状态，并把子输出收进父内部状态：

.. code-block:: fcstm

   control int cached = 5;
   control int internal = 0;
   state Host {
       import "./child.fcstm" as Child {
           var reading -> cached;
           var result -> internal;
       }
       [*] -> Child;
   }

在该目录运行以下 Python 代码；操作只在内存中执行，不产生输出文件：

.. code-block:: python

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("host.fcstm")
   runtime = SimulationRuntime(model)
   runtime.cycle()
   print(runtime.vars["internal"])
   print(list(model.inputs), list(model.output_variables))

预期输出如下，证明结果为 5，且最终模型不需要外部输入，也没有系统输出：

.. code-block:: text

   5
   [] []

若改成父 ``param int internal = 0``，子 ``output`` 的绑定将以 ``E_IMPORT_DUPLICATE_MAPPING`` 拒绝；应选择可写父目标。若改用不同数值类型，应修正声明类型，不能靠转换绕过校验。子输入绑定父可变值后按执行顺序读取最新值，原先依赖整拍输入稳定的性质应在组装模型上重新验证。

前置片段形式（preamble form）例如 ``name = value;`` 和 ``name := value;``，它是导入组装辅助测试使用的解析辅助入口，不是普通 ``state_machine_dsl`` 文件里的根级 ``def``。边界见 :ref:`dsl-import-preamble-forms-zh`。

从仓库根目录验证映射导入：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/import_host_mapped.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: System
   variables: 3
   diagnostics: 0 errors / 3 warnings / 0 infos

验证目录入口导入：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/import_host_directory.fcstm --format human --color never

预期摘录：

.. code-block:: text

   root: Factory
   diagnostics: 0 errors / 3 warnings / 0 infos

.. _dsl-diagnostics-task-zh:

诊断并修复 DSL 错误
--------------------

把检查诊断当成修复循环：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_duplicate_event.fcstm --format json

诊断包含 ``code``、``severity``、面向人的消息、源码区间和 ``refs`` 载荷。很多诊断也携带建议修复。

.. list-table:: 诊断修复练习
   :header-rows: 1
   :widths: 22 30 48

   * - 示例
     - 预期诊断码
     - 修复方向
   * - ``combo_duplicate_event.fcstm``
     - ``W_COMBO_DUPLICATE_EVENT``
     - 检查第二个事件项是否写错。只有确实需要显式两跳中继时才保留。
   * - ``guard_vars_never_change.fcstm``
     - ``W_UNWRITTEN_READ_VAR`` + ``W_GUARD_VARS_NEVER_CHANGE`` + ``I_TRANSITION_NEVER_EVENT_TRIGGERED``
     - 添加缺失的生命周期 / 效果动作写入，或确认这是有意的初值守卫后简化守卫；退出转换信息是这个最小警告示例的预期输出。
   * - ``during_const_assign.fcstm``
     - ``W_DURING_CONST_ASSIGN``
     - 一次性初始化移到 ``enter``，或让 ``during`` 表达式依赖运行时状态。
   * - ``numeric_target_range.fcstm``
     - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``
     - 这是 ``c`` / ``c_poll`` / ``cpp`` / ``cpp_poll`` 的 C/C++ 部署配置警告，不代表 Python 生成代码具有同样固定位宽风险。

最小坏语法示例作为文本夹具（text fixture）保存，因为它故意不是可解析的 ``*.fcstm`` 文件：

.. literalinclude:: ../../tutorials/dsl/event_guard_mixed_invalid.fcstm.txt
   :language: fcstm
   :caption: 故意解析错误；预期摘录：``Unexpected token 'if'``\ 。

它失败的原因是普通事件语法和普通守卫语法是两种独立转换形式。修复为组合语法：

.. code-block:: fcstm

   A -> B :: Go + [ready > 0];

代码层细节见 :doc:`../../reference/diagnostics_codes/index_zh`。

验证有意触发警告的文件：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/combo_duplicate_event.fcstm --format human --color never

预期摘录：

.. code-block:: text

   W_COMBO_DUPLICATE_EVENT
   diagnostics: 0 errors / 1 warnings / 1 infos
