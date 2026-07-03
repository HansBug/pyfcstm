.. _sec-explanations-execution-semantics-zh:

执行语义解释
============

本页解释仿真器如何执行模型，不是命令参考。批处理、热启动、导出等任务见
:doc:`../../how_to/simulation/index_zh`。

周期模型
--------

runtime 维护一条从根状态到当前叶状态的活动栈。调用 ``cycle()`` 会基于这条栈和持久变量表执行一个模型步骤。高层阶段是：

1. 如果 runtime 尚未进入模型，则初始化根到叶的活动栈；
2. 提交前先验证候选转换；
3. 对选中的转换执行 exit 和 transition effect；
4. 进入目标路径，并为复合状态执行必要的初始转换；
5. 如果当前叶状态没有提交转换，则执行普通 during 工作；
6. 把结果状态和变量写入 history。

仿真器使用推测性验证；无法到达可停止状态的转换不会部分修改真实 runtime。

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

切面 during 动作
----------------

``>> during before`` 和 ``>> during after`` 是祖先状态贡献给后代叶状态周期的切面动作。它们不同于普通复合状态 ``during before`` / ``during after`` 块。

伪状态是自动路由状态。它们不是普通可停止叶状态，祖先切面 during 动作不会作用在 pseudo/combo 路由链内部的伪状态上。整条链的语义效果会作为外层转换路径的一部分被验证。

转换优先级和验证
----------------

当多个转换可用时，模型顺序以及 guard/event 匹配决定先考虑哪个候选。runtime 会在提交状态或变量变化前验证候选路径。如果被选中的路径无法到达可停止叶状态，runtime 会报告 DFS 验证失败，而不是把机器停在 pseudo 或 composite 路由链中间。

热启动语义
----------

热启动直接根据 ``initial_state`` 和 ``initial_vars`` 构造活动栈。它表示边界已经进入：

* 必须提供所有已声明的持久变量；
* 构造路径上的 enter 动作会被跳过；
* 构造边界上的普通复合状态 ``during before`` 不会重放；
* 后续周期运行正常的转换和 during 语义；
* 复合状态热启动目标会被验证，确保它能到达可停止叶状态。

因此，热启动适合调试和测试，但它不等价于从根初始状态重放完整历史。

runtime history 和导出
----------------------

每次提交周期后，runtime 都会把周期号、活动状态和变量写入 history。REPL 的 ``history`` 命令在终端格式化显示这些记录，``export <path>`` 则把保留的 history 写入文件。导出只是观察功能，不会改变 runtime 状态。

和生成运行时的边界
------------------

仿真器是代码生成前的模型级参考执行器。生成运行时应使用相同场景对齐检查，但目标语言可能增加平台约束，例如整数宽度或 C/C++ 部署风险；这些约束并不直接适用于 Python 仿真器本身。当目标特定行为重要时，应同时使用 inspect 和生成运行时测试。
