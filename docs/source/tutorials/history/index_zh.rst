用历史恢复被打断的会话
======================

本教程为一个现成的模型加上历史（history）。你应该已经能读懂 FCSTM 模型（\ :doc:`../dsl/index_zh`\ ），也会运行批处理仿真（\ :doc:`../simulation/index_zh`\ ）。你将看到：故障恢复时以普通方式进入复合状态，为什么会从头开始；加上历史之后，恢复如何从被打断的地方继续；最后用仿真器、检查命令和 Python 热启动（hot start）验证结果。

模型是一台直流充电桩。一次充电会话先对车主鉴权，再分三个阶段充电：\ ``Precharge``\ 、\ ``ConstantCurrent``\ 和 ``ConstantVoltage``\ 。每次预充都要重做一次绝缘检测，所以模型用 ``precharge_runs`` 统计预充次数。过温故障可能打断会话的任何一个阶段。

本页用到的术语：

* **所有者（owner）**\ 是记住自己从哪里离开的复合状态（composite state），这里是 ``Session``\ ；
* **记录（record）**\ 是所有者记住的内容：离开所有者时处于活动状态的叶状态（leaf state）；
* **深历史（deep history）**\ 写作 ``[H*]``\ ，恢复记录中的叶状态本身；
* **浅历史（shallow history）**\ 写作 ``[H]``\ ，只恢复通往该叶状态的、所有者的直接子状态，这个子状态随后执行它自己的初始转换（initial transition）；
* **默认目标（default target）**\ 是所有者还没有记录时历史的去向。

1. 从一个会“忘记”的模型开始
---------------------------

第一版用普通转换从故障中恢复：

.. literalinclude:: charger_restart.fcstm
   :language: fcstm
   :caption: ``charger_restart.fcstm``\ ；预期诊断：三个计数变量各有一条 ``W_UNREFERENCED_VAR`` 警告。

.. figure:: charger_restart.fcstm.puml.svg
   :alt: 没有历史的充电桩：Idle、包含 Authenticating 与 Charging 的 Session，以及 Fault
   :align: center

   ``Session`` 包含 ``Authenticating`` 和三个充电阶段。每个阶段发出的 ``OverTemp`` 与 ``Unplug`` 箭头是两条强制转换展开的结果。\ ``Cleared`` 和 ``ManualReset`` 都指向 ``Session`` 方框本身，表示普通进入。

``!Session -> Fault :: OverTemp;`` 是一条强制转换（forced transition）：从 ``Session`` 的每个阶段都能离开（见 :ref:`dsl-forced-transition-task-zh`\ ）。运行一次会话，进入 ``ConstantVoltage``\ ，让它过温，再让故障自行解除：

.. literalinclude:: charger_restart.demo.sh
   :language: bash
   :caption: ``charger_restart.demo.sh``

由脚本生成的输出：

.. literalinclude:: charger_restart.demo.sh.txt
   :language: text

第二份报告暴露了问题。普通进入会执行 ``Session`` 的初始转换，所以充电桩回到了 ``Authenticating``\ 。车主必须重新鉴权，下一次 ``Authorized`` 还会再执行一遍 ``Precharge`` 及其绝缘检测。在这个模型里，\ ``ManualReset``\ 的行为完全相同。\ ``energy``\ 和 ``faults`` 保持原值，因为离开和进入状态从不重置变量。

2. 在所有者内部声明历史
-----------------------

需要记住位置的复合状态，在它的普通初始转换旁边声明历史：

.. code-block:: fcstm

   state Session {
       // ... 子状态与前面相同 ...
       [*] -> Authenticating;
       [H] -> Authenticating;   // 浅历史
       [H*] -> Authenticating;  // 深历史
       Authenticating -> Charging :: Authorized;
   }

箭头右侧是默认目标，只在 ``Session`` 还没有记录时使用；第 7 步会在断电之后遇到这种情况。浅历史的默认目标必须是所有者的直接子状态；深历史的默认目标可以是相对所有者书写的任意后代路径，例如 ``Charging.Precharge``\ 。

只写声明不会改变任何行为。\ ``Idle -> Session :: PlugIn``\ 这样的普通进入仍然执行 ``[*] -> Authenticating``\ 。

3. 通过历史进入所有者
---------------------

转换把“所有者加标记”写成目标，就会使用历史。这条转换写在所有者的父作用域里，这里是 ``Charger``\ ，也就是原来两条普通恢复转换所在的位置：

.. code-block:: fcstm

   Fault -> Session.[H*] :: Cleared;     // 精确回到被打断的阶段
   Fault -> Session.[H] :: ManualReset;  // 回到 Charging，再重新预充

完整模型与 ``charger_restart.fcstm`` 相比，只有开头注释和高亮的几行不同：

.. literalinclude:: charger.fcstm
   :language: fcstm
   :emphasize-lines: 28,29,38,39
   :caption: ``charger.fcstm``\ ；预期诊断：同样是三条 ``W_UNREFERENCED_VAR`` 警告。

4. 再运行同一次会话
-------------------

下面的脚本运行与第 1 步相同的会话，在 ``ConstantVoltage`` 打断它，然后分别通过两种历史各恢复一次：

.. literalinclude:: charger_resume.demo.sh
   :language: bash
   :caption: ``charger_resume.demo.sh``

由脚本生成的输出：

.. literalinclude:: charger_resume.demo.sh.txt
   :language: text

**深历史**\ 恢复到 ``Charging.ConstantVoltage``\ 。恢复会跳过路径上的初始转换，包括 ``Session`` 里的 ``[*] -> Authenticating`` 和 ``Charging`` 里的 ``[*] -> Precharge``\ ，所以 ``precharge_runs`` 仍为 1。\ ``energy``\ 从 7 增加到 9，因为被恢复的叶状态在进入它的那个周期就执行了 ``during``\ ，与任何被进入的叶状态一样。

**浅历史**\ 只记住 ``Session`` 中通往记录叶状态的直接子状态，也就是 ``Charging``\ 。进入 ``Charging`` 后，它会执行自己的初始转换，所以充电桩处于 ``Precharge``\ ，\ ``precharge_runs``\ 变为 2。操作员的复位会重做绝缘检测，但不需要重新鉴权。

输出里出现两个 ``__hist_*`` 变量，是因为仿真器运行的是模型转换之后的模型：历史已经被改写成普通的变量和转换。第 8 步会展示改写后的样子，现在只需把它们看作记录背后的存储。

5. 观察记录何时变化
-------------------

下面的 Python 循环在每个周期之后打印记录。\ :meth:`~pyfcstm.model.model.StateMachine.history_record`\ 把记录解码为相对 ``Session`` 的叶状态路径。只有 ``Session`` 不活动时，记录才代表最近一次离开，所以其他时候脚本打印 ``(Session active)``\ 。

.. literalinclude:: charger_record.demo.py
   :language: python
   :caption: ``charger_record.demo.py``

由脚本生成的输出：

.. literalinclude:: charger_record.demo.py.txt
   :language: text

从上往下读这张表：

* 第 5、7 行：经由 ``OverTemp`` 离开 ``Session`` 时，记下当时活动的叶状态 ``Charging.ConstantVoltage``\ 。
* 第 6、8 行：两种恢复读取的是同一条记录，区别只在恢复多深，所以只有第 8 行让 ``precharge`` 增加。
* 第 10 行：\ ``Unplug``\ 同样离开了 ``Session``\ ，于是记下 ``Charging.ConstantCurrent``\ 。每次离开所有者都会更新记录，不只是故障。
* 第 11 行：\ ``PlugIn``\ 是普通进入。虽然已经有记录，新会话仍从 ``Authenticating`` 开始；只有 ``Session.[H]`` 和 ``Session.[H*]`` 目标才会读取记录。
* ``precharge``\ 和 ``energy`` 两列从不回退。历史恢复的是状态，不是变量值。

6. 检查模型并修复一个错误
-------------------------

检查命令按你书写的模型（模型转换之前）进行判断。下面的脚本先检查 ``charger.fcstm``\ ，再检查一份删掉了 ``[H*]`` 声明的副本：

.. literalinclude:: charger_check.demo.sh
   :language: bash
   :caption: ``charger_check.demo.sh``

由脚本生成的输出：

.. literalinclude:: charger_check.demo.sh.txt
   :language: text

第一份报告与 ``charger_restart.fcstm`` 一样只有三条警告，说明历史没有带来新的诊断。报告列出你声明的三个变量，没有任何 ``__hist_*`` 变量。

第二份报告是需要学会辨认的错误。\ ``Session.[H*]``\ 要求深历史，但 ``Session`` 已经不再声明它，所以检查命令在这条转换上报告 ``E_HISTORY_TARGET_UNDECLARED``\ ，并以状态码 1 退出。\ ``pyfcstm simulate``\ 、\ ``pyfcstm generate``\ 和 ``pyfcstm bmc`` 也会拒绝同一个模型，因为历史从不会被隐式提供。有两种修复方式：

* 如果恢复应当精确回到被打断的阶段，把 ``[H*] -> Authenticating;`` 放回 ``Session``\ ；
* 如果恢复应当从头开始，改写成 ``Fault -> Session :: Cleared;``\ 。

7. 跨越断电保存记录
-------------------

充电桩在 ``Fault`` 中断电后重新启动时，必须恢复会话的记录。热启动要提供所有变量，包括 ``__hist_*`` 变量，所以控制器必须把记录存下来。请保存源码层面的记录，而不是那些数字：数字是状态编号，模型一改就会变。\ :meth:`~pyfcstm.model.model.StateMachine.history_variables`\ 会把保存的记录换算回展开后的变量。

.. literalinclude:: charger_hot_start.demo.py
   :language: python
   :caption: ``charger_hot_start.demo.py``

由脚本生成的输出：

.. literalinclude:: charger_hot_start.demo.py.txt
   :language: text

有保存的记录时，重启后的 ``Cleared`` 恢复到 ``ConstantCurrent``\ ，与没有断电时完全一样，也不会重复预充。没有记录时，深历史使用默认目标，会话从 ``Authenticating`` 开始。

8. 可选：看看模型转换产生了什么
-------------------------------

仿真器、生成的代码和 BMC 都看不到 ``[H]`` 或 ``[H*]``\ 。在它们运行之前，模型转换已经把历史改写成普通的 FCSTM。打印转换后的模型，就能看到改写后的样子：

.. literalinclude:: charger_lowered.demo.py
   :language: python
   :caption: ``charger_lowered.demo.py``

由脚本生成的输出：

.. literalinclude:: charger_lowered.demo.py.txt
   :language: fcstm

用这份输出核对前面几步观察到的现象：

* 你声明的变量后面多了两个 ``int`` 变量：\ ``__hist_Session``\ 保存记录，\ ``__hist_goto``\ 保存进行中的恢复，状态机稳定时它总是 0。
* ``Session``\ 下的每个叶状态都有一个 ``exit`` 动作，把自己的编号写入 ``__hist_Session``\ ：\ ``Authenticating``\ 是 4，三个充电阶段是 6 到 8。第 5 步表格第 5 行记下 ``Charging.ConstantVoltage``\ （编号 8）靠的就是它，这也是每次离开所有者都会更新记录的原因。
* ``Fault -> Session.[H*] :: Cleared``\ 变成了一条普通进入，它的 ``effect`` 在有记录时把 ``__hist_goto`` 设为记录，没有记录时设为 4，也就是默认目标 ``Authenticating`` 的编号。
* ``Fault -> Session.[H] :: ManualReset``\ 把 ``Charging`` 内部的记录（编号 6 到 8）映射为 5，也就是 ``Charging`` 自身的编号。
* ``Session``\ 和 ``Charging`` 的初始转换都由 ``__hist_goto`` 守卫。0 选择普通的初始子状态，其他值把进入引向恢复目标，到达目标的那条转换再把 ``__hist_goto`` 重置为 0。以 5 为目标的恢复最终落在 ``Charging`` 的 ``[*] -> Precharge`` 上，这正是浅历史恢复会重新预充的原因。

``pyfcstm plantuml -i charger.fcstm``\ 画出的也是这个转换后的模型。

下一步去哪里
------------

本教程只涉及一个所有者，从它的父状态通过两种历史进入。当你的问题变了，就离开本教程：

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - 问题
     - 页面
   * - 怎样给自己的模型加上历史？常见错误是什么意思？
     - :ref:`dsl-history-task-zh`\ ，带排错表的操作指南。
   * - 哪些写法合法？历史也可以从初始转换、强制转换或外部自环进入。
     - :ref:`dsl-history-reference-zh`\ ，列出所有写法、诊断与展开生成的名字。
   * - 为什么所有者结束时记录不会被清除？恢复被为假的守卫挡住时会怎样？
     - :ref:`dsl-history-semantics-zh`\ 。被挡住的恢复会拒绝整条转换，而不会退化为普通进入。
   * - BMC 查询如何对待 ``__hist_*`` 变量？
     - :doc:`/reference/bmc_query/index_zh`\ 中的 ``havoc`` 一行。
