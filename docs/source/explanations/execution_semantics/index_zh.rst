.. _sec-explanations-execution-semantics-zh:

执行语义解释
============

本页解释仿真器如何执行模型，不是命令参考。批处理、热启动、导出等任务见
:doc:`../../how_to/simulation/index_zh`。

周期模型
--------

运行时维护一条从根状态到当前叶状态的活动栈。调用 ``cycle()`` 会基于这条栈和持久变量表执行一个模型步骤。状态拥有区域时，这条栈变成一棵树：拥有者之下每个区域各有一条栈，在同一个周期内按书写顺序依次推进（一份输入采样，一次周期计数）。整台机器的位置于是是一个配置（``runtime.configuration``\ ），它的文本形式为每个区域列一个位置。这样的周期怎样运行见\ :doc:`../region_semantics/index_zh`\ ；下面描述的是单路径情形，它也是每个区域内部实际运行的情形。高层阶段是：

1. 如果运行时尚未进入模型，则初始化根到叶的活动栈；
2. 提交前先验证候选转换；
3. 对选中的转换执行 exit 和 transition effect；
4. 进入目标路径，并为复合状态执行必要的初始转换；
5. 如果当前叶状态没有提交转换，则执行普通 during 工作；
6. 把结果状态和变量写入 history。

仿真器使用推测性验证；无法到达可停止状态的转换不会部分修改真实运行时。

执行顺序矩阵
------------

.. list-table:: 常见运行时边界
   :header-rows: 1

   * - 场景
     - 顺序保证
     - 证据族
   * - 冷进入
     - 先执行根状态/复合状态进入，再由初始转换选择叶状态，后续活动周期才会运行叶状态 ``during``。
     - ``cold_initial_*`` 和 ``composite_initial_*`` 测试夹具。
   * - 普通叶状态周期
     - 祖先切面 ``during before`` 先于叶状态 ``during``；切面 ``during after`` 在其后运行。
     - ``design_aspect_*`` 和 ``aspect_context_*`` 测试夹具。
   * - 叶状态转换
     - 源状态 ``exit`` 先运行，然后是转换 ``effect``，最后是目标状态 ``enter``。如果没有转换提交，则运行叶状态 ``during`` 路径。
     - ``design_basic_*`` 和转换 effect 测试夹具。
   * - 复合状态初始转换
     - 复合状态进入后选择初始转换，执行该转换 effect，运行普通复合状态 ``during before``，然后进入被选中的子状态。
     - ``composite_initial_*`` 测试夹具。
   * - 伪状态或组合转换路由
     - 中间伪状态会自动路由，不是可停止叶状态周期；整条候选链会在提交前被验证。
     - ``design_pseudo_chain_*`` 和 ``combo_transition_trigger_*`` 测试夹具。
   * - 热启动
     - 活动栈被构造成“已经进入”的状态；路径上的 enter 动作和普通复合状态 ``during before`` 不会重放。
     - ``abstract_hook_context_hot_start_*`` 和 ``design_multi_level_non_stoppable_*`` 测试夹具。
   * - 终止处理
     - 转到机器结束会清空栈。之后调用 ``cycle()`` 不再推进，``current_state`` 也不再是终止安全查询。
     - ``*_terminal_*`` 和 ``design_explicit_exit_to_root_*`` 测试夹具。
   * - 一个周期里的区域
     - 拥有者的区域按书写顺序执行；靠后的区域能看到靠前区域在同一周期写入的值；输入只采样一次，周期计数只加一。
     - ``region_controller_*``\ 、``region_later_*``\ 、``region_earlier_*``\ 。轨迹见\ :ref:`region-semantics-one-cycle-zh`\ 。
   * - 拥有者的生命周期与切面
     - 拥有者的 ``enter`` 与 ``exit`` 各执行一次；普通 ``during before`` 在整组初始化时执行一次；拥有者及其祖先的 ``>> during`` 切面包住整组，区域自己的切面只包住该区域。
     - ``region_owner_*``\ 、``region_group_*``\ 、``region_aspect*``\ 。轨迹见\ :ref:`region-semantics-aspects-zh`\ 。
   * - 完成
     - 区域经 ``-> [*]`` 完成；最后一次完成在同一周期经拥有者续接，或者被拒绝。
     - ``region_done_*``\ 、``region_last_*``\ 、``region_inner_group_*``\ 。轨迹见\ :ref:`region-semantics-completion-zh`\ 。
   * - 含区域时的候选与 Delta
     - 进不去的候选让位给下一个，前面区域的写入保留；没有合法配置的周期整体是 Delta。
     - ``region_candidate_*``\ 、``region_cold_start_*``\ 。轨迹见\ :ref:`region-semantics-candidates-zh`\ 。

.. _exec-composite-entry-order-zh:

通过复合状态初始进入
--------------------

复合状态使用 ``[*] -> Child`` 选择初始子状态。初始进入复合状态时，仿真器会运行复合状态进入边界，选择初始转换，执行该初始转换的 effect，运行该复合状态的普通 ``during before``，然后进入被选中的子状态。

复合状态内部的子到子转换不同：它会退出源子状态，执行转换 effect，然后进入目标子状态。普通复合状态 ``during before`` 和 ``during after`` 不包裹普通子到子转换。

下面的例子展示了普通 ``during before`` 在复合进入时执行，而祖先切面和叶状态 during 工作会在后续活动周期运行：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text("""
   def int counter = 0;

   state System {
       >> during before { counter = counter + 1; }
       [*] -> Parent;
       state Parent {
           during before { counter = counter + 100; }
           state Child {
               during { counter = counter + 10; }
           }
           [*] -> Child;
       }
   }
   """)
   runtime = SimulationRuntime(model)
   for number in (1, 2, 3):
       runtime.cycle()
       print("cycle", number, "counter =", runtime.vars["counter"])

.. testoutput::

   cycle 1 counter = 111
   cycle 2 counter = 122
   cycle 3 counter = 133

周期 1 增加 111：``Parent`` 的普通 ``during before``\ （100）在复合进入时运行，同时运行祖先切面（1）和 ``Child.during``\ （10）。周期 2 和 3 各增加 11：切面 ``>> during before``\ （1）加 ``Child.during``\ （10），复合状态自己的 ``during before`` 不再运行。

生命周期和转换 effect
---------------------

仿真器区分生命周期块和转换 effect：

* ``enter`` 在进入状态时运行。
* ``during`` 在活动状态保持活动的周期运行。
* ``exit`` 在离开状态时运行。
* 转换 ``effect`` 块在源状态 exit 和目标状态 enter 之间运行。

对于源到目标转换，源状态 exit 先于 effect，目标状态 enter 后于 effect。如果没有转换提交，则会运行活动叶状态的普通 ``during`` 路径。

.. _exec-during-aspect-order-zh:

切面 during 动作
----------------

``>> during before`` 和 ``>> during after`` 是祖先状态贡献给后代叶状态周期的切面动作。它们不同于普通复合状态 ``during before`` / ``during after`` 块。

伪状态是自动路由状态。它们不是普通可停止叶状态，祖先切面 during 动作不会作用在 伪状态/组合转换路由链内部的伪状态上。整条链的语义效果会作为外层转换路径的一部分被验证。

在 ``S1 -> P1 -> P2 -> S2`` 这类链路里，``P1`` 和 ``P2`` 是路由边界。它们的 guard/effect 决策会影响哪条候选路径有效，但它们不会产生普通叶状态 ``during`` 周期，也不会像真实叶状态一样接收祖先切面 ``during`` 动作。

.. _exec-combo-order-zh:

转换优先级和验证
----------------

当多个转换可用时，模型顺序以及 guard/event 匹配决定先考虑哪个候选。运行时会在提交状态或变量变化前验证候选路径。如果路径没有可提交的可停止叶状态或终止后继，但已经到达稳定的无进展边界，则提交成功的 Delta 宏步骤，状态和变量保持不变；变化签名的循环以及真实表达式、事件或 DFS 错误仍会明确失败，而不会把机器停在伪状态或复合状态路由链中间。

.. _exec-diagnostic-boundaries-zh:

诊断证据与完整宏步骤路径
------------------------

``cycle(diagnostics=True)`` 在真实检查点记录实际变量快照，不用最终值重新求值守卫。调用级报告用 ``vars_before`` 和 ``vars_after`` 保存持久边界快照，与每条检查可能包含推测写入的 ``vars`` 区分；冻结 ``inputs`` 和固定 ``parameters`` 也明确保留，即使普通周期没有候选检查。已提交微迁移清单按执行顺序排列，检查之间的父子关系则表示验证上下文，不表示执行顺序。

对一条确定的候选路径，每个微步骤的守卫都必须满足，而且要在各自动作前缀对应的状态上求值。下面只是路径关系的示意式：

.. code-block:: text

   valid(P) = required events
              AND guard_0(v_0, input_t, parameters)
              AND action updates v_1 = F_0(v_0, input_t, parameters)
              AND guard_1(v_1, input_t, parameters)
              AND ...
              AND a stoppable or terminated final boundary

不能把探索备选路径时观察到的所有检查做合取。各条备选路径有自己的条件，还受声明顺序产生的优先级排除约束；一个分支的守卫失败，不会在其他延续成功时让整个候选失败。输入在同一宏步骤内冻结，参数跨步骤固定。BMC 的宏步骤契约把守卫定位到动作前缀，关系构造按当时的中间环境降低守卫；仿真器则检查推测上下文并放弃失败上下文，得到同一提交边界。已提交执行迹不包含那些被放弃的检查。

在 :doc:`组合迁移例子 <../../how_to/simulation/diagnostics_zh>` 中，末端迁移动作先执行 ``reading=sensor``，目标初始守卫再检查 ``reading >= limit``。在 ``Root.Start`` 边界上，简化后的接受条件是 ``A_t AND B_t AND sensor_t >= limit``。回退路径要求 A 存在且完整组合路径没有被接受，不能只因第一个事件为真就压制回退。``sensor=3`` 时，被拒检查看到 ``score=10011``、``reading=3``，回退路径最终提交 ``score=121``、``reading=0``；这是不同分支的上下文，不是公开写入 10011 后再撤销到 121。

候选被拒后仍可在同一普通周期提交其他候选。Delta 则表示一次成功的无进展宏边界：保持原状态和持久变量，输入源与周期历史依然推进。忽略调用既不推进也不采样，报告使用 ``inputs=None``。这些区分可以避免把“状态相同”误判成 Delta，也避免把“回滚”误解为逆转外部时间或外部回调的任意副作用。字段与查询规则见 :doc:`诊断参考 <../../reference/simulation/diagnostics_zh>`。

热启动语义
----------

热启动直接根据 ``initial_state`` 和 ``initial_vars`` 构造活动栈。它表示边界已经进入。含区域的模型里位置是一棵树，同样的规则逐分支适用：文本写到的部分就位、不执行任何 ``enter``\ ，没写到的部分等待初始化，在第一个周期按书写顺序走各自的初始转换。规则与真实运行见\ :doc:`../region_semantics/index_zh`\ 。对所有模型：

* 必须提供所有已声明的持久变量，包括历史展开生成的 ``__hist_*`` 变量；可用 ``StateMachine.history_variables()`` 从源码层面的记录换算。这些变量和其他变量一样，给什么值就按什么值运行，热启动不会因为取值而拒绝（见 :ref:`dsl-history-reference-zh`\ ）；
* 构造路径上的 enter 动作会被跳过；
* 构造边界上的普通复合状态 ``during before`` 不会重放；
* 后续周期运行正常的转换和 during 语义；
* 含区域时，写作 ``[done]`` 的区域保持已完成、什么也不做；省略或写作 ``[init]`` 的区域等待初始化；任一层拥有者的所有区域都已完成的位置会被拒绝；等待中的区域到不了合法位置时，第一个周期是 Delta；
* 隐藏变量（``__hist_*``\ 、``__forced_*``\ 、``__active_*``\ ）是普通变量：与其他变量一起提供，从不推导；
* 热启动构造只执行结构检查；首个真实周期没有可提交后继时记录 Delta，具体表达式、事件和 DFS 错误在该周期明确报告。

因此，热启动适合调试和测试，但它不等价于从根初始状态重放完整历史。

运行时历史和导出
----------------

每次成功周期（包括 Delta 周期）后，运行时都会把周期号、活动状态、变量、输入事件和布尔值 ``delta`` 写入历史。这份周期日志与 :ref:`dsl-history-semantics-zh` 中复合状态的 ``[H]`` / ``[H*]`` 历史无关。交互命令行的 ``history`` 命令在终端格式化显示这些记录，``export <path>`` 则把保留的历史写入文件。导出只是观察功能，不会改变运行时状态。

测试夹具证据矩阵
----------------

语义测试夹具（fixture）套件是本页背后的可执行证据。下表有意写测试夹具家族，而不是逐条断言；这样解释页面可以保持稳定，同时允许测试继续增加更聚焦的用例。

.. list-table:: 测试夹具家族和覆盖行为
   :header-rows: 1

   * - 行为族
     - 代表测试夹具模式
     - 保护内容
   * - 生命周期顺序
     - ``design_basic_*``、``composite_initial_*``、``cold_initial_*``
     - 冷进入、状态进入、叶状态 ``during``、源状态 ``exit``、目标状态 ``enter`` 和复合状态初始转换顺序。
   * - 切面动作
     - ``design_aspect_*``、``design_multi_layer_aspect_*``、``aspect_context_*``
     - 祖先切面前后动作，以及处理器看到的活动叶状态元数据。
   * - 伪状态链
     - ``design_pseudo_chain_*``、``design_evented_pseudo_chain_*``
     - 经由伪状态的自动路由，以及从非法候选恢复。
   * - 组合转换路由
     - ``combo_transition_trigger_*``、``combo_initial_*``
     - 展开的组合转换中继路径、guard/effect 顺序、回滚、终止验证和切面边界。
   * - 回滚
     - ``*_rollback_*``、``composite_initial_skips_unstable_*``
     - 推测性验证拒绝路径时的变量和栈回滚。
   * - 热启动
     - ``abstract_hook_context_hot_start_*``、``design_multi_level_non_stoppable_*``
     - 已进入栈构造、变量要求、Delta 无进展和首周期错误边界。
   * - 终止处理
     - ``*_terminal_*``、``design_explicit_exit_to_root_*``
     - 结束状态转换、运行时终止和终止安全查询。
   * - 抽象处理器上下文
     - ``abstract_handler_context_*``、``abstract_hook_ref_context_*``
     - 只读变量快照、调用点元数据、命名引用和活动叶状态报告。
   * - 区域
     - ``region_*``\ （118 个用例；各族列在\ :ref:`region-semantics-evidence-zh`\ ）
     - 含区域的模型的书写顺序执行、同周期可见性、完成、整组启动、回退与 Delta、切面、强制展开、``active()``\ 、热启动、事件名与处理器上下文。

和生成运行时的边界
------------------

仿真器是代码生成前的模型级参考执行器。生成运行时应使用相同场景对齐检查，但目标语言可能增加平台约束，例如整数宽度或 C/C++ 部署风险；这些约束并不直接适用于 Python 仿真器本身。当目标特定行为重要时，应同时使用 inspect 和生成运行时测试。

含区域的模型上，同样的测试夹具会在生成的 Python 运行时和四套 C 系运行时上运行，生成运行时报告的配置文本与仿真器报告的文本逐字节相同。生成运行时的形态见\ :doc:`../template_rendering/index_zh`\ 。
