.. _sec-explanations-execution-semantics-zh:

执行语义解释
============

本页解释仿真器如何执行模型，不是命令参考。批处理、热启动、导出等任务见
:doc:`../../how_to/simulation/index_zh`。

周期模型
--------

运行时维护一条从根状态到当前叶状态的活动栈。调用 ``cycle()`` 会基于这条栈和持久变量表执行一个模型步骤。高层阶段是：

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

.. _exec-composite-entry-order-zh:

通过复合状态初始进入
--------------------

复合状态使用 ``[*] -> Child`` 选择初始子状态。初始进入复合状态时，仿真器会运行复合状态进入边界，选择初始转换，执行该初始转换的 effect，运行该复合状态的普通 ``during before``，然后进入被选中的子状态。

复合状态内部的子到子转换不同：它会退出源子状态，执行转换 effect，然后进入目标子状态。普通复合状态 ``during before`` 和 ``during after`` 不包裹普通子到子转换。

下面的已检查 demo 展示了普通 ``during before`` 在复合进入时执行，而祖先切面和叶状态 during 工作会在后续活动周期运行：

.. literalinclude:: ../../tutorials/simulation/hierarchy_execution.demo.py
   :language: python
   :caption: 层级进入和 during 执行

输出：

.. literalinclude:: ../../tutorials/simulation/hierarchy_execution.demo.py.txt
   :language: text

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

当多个转换可用时，模型顺序以及 guard/event 匹配决定先考虑哪个候选。运行时会在提交状态或变量变化前验证候选路径。如果被选中的路径无法到达可停止叶状态，运行时会报告 DFS 验证失败，而不是把机器停在伪状态或复合状态路由链中间。

热启动语义
----------

热启动直接根据 ``initial_state`` 和 ``initial_vars`` 构造活动栈。它表示边界已经进入：

* 必须提供所有已声明的持久变量；
* 构造路径上的 enter 动作会被跳过；
* 构造边界上的普通复合状态 ``during before`` 不会重放；
* 后续周期运行正常的转换和 during 语义；
* 复合状态热启动目标会被验证，确保它能到达可停止叶状态。

因此，热启动适合调试和测试，但它不等价于从根初始状态重放完整历史。

运行时历史和导出
----------------

每次提交周期后，运行时都会把周期号、活动状态和变量写入历史。交互命令行的 ``history`` 命令在终端格式化显示这些记录，``export <path>`` 则把保留的历史写入文件。导出只是观察功能，不会改变运行时状态。

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
     - 已进入栈构造、变量要求和不可停止路径拒绝。
   * - 终止处理
     - ``*_terminal_*``、``design_explicit_exit_to_root_*``
     - 结束状态转换、运行时终止和终止安全查询。
   * - 抽象处理器上下文
     - ``abstract_handler_context_*``、``abstract_hook_ref_context_*``
     - 只读变量快照、调用点元数据、命名引用和活动叶状态报告。

和生成运行时的边界
------------------

仿真器是代码生成前的模型级参考执行器。生成运行时应使用相同场景对齐检查，但目标语言可能增加平台约束，例如整数宽度或 C/C++ 部署风险；这些约束并不直接适用于 Python 仿真器本身。当目标特定行为重要时，应同时使用 inspect 和生成运行时测试。
