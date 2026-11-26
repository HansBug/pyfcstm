第一个含区域的模型
==================

本教程运行一个小型控制器，它在同一个状态里有两个\ **区域（region）**\ ，你会看到区域的顺序起什么作用。最后你会得到：模拟过这个控制器，对调区域顺序并看到结果改变，读到对应的检查诊断，用有界模型检查在两个版本上检查同一条性质，生成并运行 Python 运行时，并看过模型的图。

你需要装好 ``pyfcstm``，并把两个模型文件放在同一目录。把 :download:`controller.fcstm <controller.fcstm>` 和 :download:`controller_swapped.fcstm <controller_swapped.fcstm>` 下载到一个空目录，所有命令都在该目录里运行。命令只使用相对文件名。

1. 读模型
---------

控制器是一个联锁。\ ``Safety`` 区域决定电机能否运行，\ ``Motion`` 区域负责切换电机。

.. literalinclude:: controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

运行之前先注意三件事：

* ``Running`` 拥有两个 ``region`` 块。\ ``Running`` 活动时两者同时活动，各自有自己的初始转换（``[*] -> Watching`` 和 ``[*] -> Off``）。
* 同一个拥有者（owner）的区域在每个周期里\ **按书写顺序依次执行**。\ ``Safety`` 写在前面，所以它在同一周期里先写 ``permit``，\ ``Motion`` 后读。
* ``!Running -> Idle : /Stop;`` 是写在拥有者上的强制转换（forced transition）。它从两个区域所处的任何位置离开 ``Running``，所以 ``/Stop`` 一次停下整组。强制转换会引入隐藏变量 ``__forced_0``，你会在输出里看到它。

2. 模拟一段场景
---------------

用批处理模式运行一段场景。每个真正执行的周期都需要完整的输入向量，所以每条命令把 ``fault`` 和 ``requested`` 各给一次。\ ``/Start`` 和 ``/Stop`` 是根事件。

.. literalinclude:: simulate_interlock.demo.sh
   :language: bash
   :caption: ``simulate_interlock.demo.sh``

:download:`下载 simulate_interlock.demo.sh <simulate_interlock.demo.sh>` 后运行，或者把其中的 ``pyfcstm simulate`` 命令贴进终端。输出是：

.. literalinclude:: simulate_interlock.demo.sh.txt
   :language: text
   :caption: ``simulate_interlock.demo.sh.txt``

逐周期看 ``Current State`` 一行。含区域的模型会打印完整的\ **配置（configuration）**\ ：拥有者后面的花括号里是每个区域的位置，例如 ``Controller.Running{Safety: Watching, Motion: Off}``。

* 周期 1 进入 ``Controller.Idle``。
* 周期 2 处理 ``/Start``。两个区域都执行初始转换，\ ``permit`` 已经是 ``1``，因为 ``Safety`` 在同一周期里执行了它的 ``during``。
* 周期 3 有 ``requested=1``：\ ``Motion`` 转到 ``On``，\ ``motor`` 为 ``1``。
* 周期 4 有 ``fault=1``。看 ``motor``：它在这一个周期里就是 ``0``。\ ``Safety`` 先执行并写入 ``permit = 0``，随后 ``Motion`` 读到这个新值并切回 ``Off``。
* 周期 5 清除故障，电机重新运行。周期 6 处理 ``/Stop``：强制转换离开 ``Running``，配置又变回 ``Controller.Idle``。

3. 对调区域顺序
---------------

``controller_swapped.fcstm`` 有同样两个区域，只是 ``Motion`` 写在 ``Safety`` 前面，其余完全相同。运行同一场景，但让故障连续出现两个周期：

.. literalinclude:: simulate_swapped.demo.sh
   :language: bash
   :caption: ``simulate_swapped.demo.sh``

:download:`下载 simulate_swapped.demo.sh <simulate_swapped.demo.sh>`，在放着模型的目录里用 ``sh simulate_swapped.demo.sh`` 运行。

.. literalinclude:: simulate_swapped.demo.sh.txt
   :language: text
   :caption: ``simulate_swapped.demo.sh.txt``

把周期 4 和上一次运行比较。故障已经出现，\ ``permit`` 是 ``0``，\ ``motor`` 却仍是 ``1``。\ ``Motion`` 现在先执行，所以它读到的是 ``Safety`` 在上一个周期写的 ``permit``。电机晚一个周期，在周期 5 才关。配置文本里区域也按新顺序列出：``{Motion: On, Safety: Watching}``。

区域的书写顺序是模型含义的一部分。只在这个顺序上不同的两个模型是不同的模型。

4. 检查模型
-----------

``pyfcstm inspect`` 会报告区域并检查它们的顺序。演示脚本先打印 ``controller.fcstm`` 报告的开头，再只打印两个模型的诊断码，最后完整打印与区域顺序有关的那一条诊断。

.. literalinclude:: inspect_regions.demo.sh
   :language: bash
   :caption: ``inspect_regions.demo.sh``

:download:`下载 inspect_regions.demo.sh <inspect_regions.demo.sh>`，在放着模型的目录里用 ``sh inspect_regions.demo.sh`` 运行。

.. literalinclude:: inspect_regions.demo.sh.txt
   :language: text
   :caption: ``inspect_regions.demo.sh.txt``

看三个地方：

* 摘要里有 ``regions: 2``，并列出每个区域在拥有者里的顺序（\ ``order 0`` 是写在最前面的）。
* ``controller.fcstm`` 没有区域顺序诊断。它确实有四条警告，分别针对常量的 ``during`` 赋值和一个没有出边的叶子状态。它们说的是这个示例的写法，与区域无关，也不影响上面的场景。
* ``controller_swapped.fcstm`` 多了 ``I_REGION_BACKWARD_READ``。它是提示级诊断：\ ``Motion`` 读取的 ``permit`` 由靠后的 ``Safety`` 区域写入，所以 ``Motion`` 看到的是上一个周期的值。诊断信息写明这是有序区域的既定行为，不是缺陷。想要上一周期的值就保持顺序，想要当前周期的值就把写入方区域写在前面。

5. 用有界模型检查验证性质
-------------------------

写出性质“故障出现时，电机在该周期结束时是关的”。性质文件 ``fault_beat_motor_off.fbmcq`` 是：

.. literalinclude:: fault_beat_motor_off.fbmcq
   :language: text
   :caption: ``fault_beat_motor_off.fbmcq``

:download:`下载 fault_beat_motor_off.fbmcq <fault_beat_motor_off.fbmcq>`。第一行假设故障输入在第 3 步（第四个宏步）非零。第二行是上界为 4 的 ``forbid`` 性质：搜索最多四个宏步的运行，使得第 3 步之后（``cycle == 4``）电机仍然是开的。

在联锁模型上运行：

.. literalinclude:: bmc_interlock.demo.sh
   :language: bash
   :caption: ``bmc_interlock.demo.sh``

:download:`下载 bmc_interlock.demo.sh <bmc_interlock.demo.sh>`，在放着模型的目录里用 ``sh bmc_interlock.demo.sh`` 运行。

.. literalinclude:: bmc_interlock.demo.sh.txt
   :language: text
   :caption: ``bmc_interlock.demo.sh.txt``

命令去掉了 ``Solver:`` 耗时行，让输出每次都相同。先读结论：\ ``PROPERTY GUARANTEED WITHIN BOUND``。求解器搜索反例但没有找到（``UNSAT``），所以在第 3 步出现故障、至多 4 个宏步的所有运行里性质都成立。最后一行是上界：它对更长的运行什么也没说。

再在对调后的模型上运行同一条性质。性质不成立，所以这条命令预期失败，退出状态为 ``1``：

.. literalinclude:: bmc_swapped.demox.sh
   :language: bash
   :caption: ``bmc_swapped.demox.sh``

:download:`下载 bmc_swapped.demox.sh <bmc_swapped.demox.sh>`，用 ``sh bmc_swapped.demox.sh`` 运行。这个脚本按设计以退出状态 ``1`` 结束。不要把它的几行贴进交互式终端：检查失败时 ``set -e`` 会关掉终端。

.. literalinclude:: bmc_swapped.demox.sh.txt
   :language: text
   :caption: ``bmc_swapped.demox.sh.txt``

结论是 ``PROPERTY DOES NOT HOLD WITHIN BOUND``，求解器状态是 ``SAT``。求解器状态描述的是反例搜索，结论才是对你的性质意味着什么。这里的 ``SAT`` 是坏消息，上一次的 ``UNSAT`` 是好消息。轨迹就是反例：\ ``Motion`` 在第 2 步 ``Off -> On``，第 3 步虽然有故障仍保持 ``On``，这正是你在模拟器里看到的晚关。\ ``Replay: verified`` 表示模拟器复现了这条轨迹。结果的全部字段见 :doc:`/reference/bmc_results/index_zh`。

6. 生成并运行 Python 运行时
---------------------------

为联锁模型生成内置的 Python 运行时，并用第 2 步的场景驱动它：

.. literalinclude:: generate_runtime.demo.sh
   :language: bash
   :caption: ``generate_runtime.demo.sh``

:download:`下载 generate_runtime.demo.sh <generate_runtime.demo.sh>`，在放着模型的目录里用 ``sh generate_runtime.demo.sh`` 运行。

驱动脚本 ``run_scenario.py`` 在 ``inputs`` 参数里给出每个周期的输入，并打印周期数、\ ``configuration`` 和两个变量：

.. literalinclude:: run_scenario.py
   :language: python
   :caption: ``run_scenario.py``

:download:`下载 run_scenario.py <run_scenario.py>` 到同一目录。输出是：

.. literalinclude:: generate_runtime.demo.sh.txt
   :language: text
   :caption: ``generate_runtime.demo.sh.txt``

前三行是 ``pyfcstm generate`` 写出的文件。后六行对应第 2 步的六个周期：配置、\ ``permit`` 和 ``motor`` 都相同，包括故障周期里电机关断。含区域的模型没有 ``current_state_path``，位置要用 ``configuration`` 读。

7. 看图
-------

``pyfcstm plantuml`` 打印模型的 PlantUML 文本：

.. literalinclude:: plantuml_regions.demo.sh.txt
   :language: text
   :caption: ``pyfcstm plantuml -i controller.fcstm``

在 ``Running`` 里找到两条区域注释 ``region 1: Safety`` 和 ``region 2: Motion``。一行 ``--`` 把区域隔开，渲染出的图里它们上下堆叠。

``pyfcstm diagram`` 写出交互式查看器，它是一个不需要网络的自包含 HTML 文件：

.. code-block:: bash

   pyfcstm diagram -i controller.fcstm -o viewer.html

在浏览器里打开 ``viewer.html``。检查 ``Running`` 的外框里并排放着两个区域，标题分别是 ``region 1: Safety`` 和 ``region 2: Motion``，中间用虚线隔开。不带 ``-o`` 时，同一命令打印图的可移植 JSON，其中每个区域是一个带区域标记的节点：

.. literalinclude:: diagram_regions.demo.sh
   :language: bash
   :caption: ``diagram_regions.demo.sh``

:download:`下载 diagram_regions.demo.sh <diagram_regions.demo.sh>`，在放着模型的目录里用 ``sh diagram_regions.demo.sh`` 运行。

.. literalinclude:: diagram_regions.demo.sh.txt
   :language: text
   :caption: ``diagram_regions.demo.sh.txt``

要运行这条命令，请把 :download:`list_regions.py <list_regions.py>` 下载到同一目录。

8. 下一步
---------

现在你有了一个区域按书写顺序执行的模型，并在模拟器、检查报告、检查器、生成的运行时和图里都见过这个顺序。按你想做的事继续：

* :doc:`/how_to/regions/index_zh` 是任务做法：添加区域、选择顺序、读取配置、对含区域的模型热启动（hot start）。
* :doc:`/explanations/region_semantics/index_zh` 用轨迹解释一个周期怎样执行含区域的模型。
* :doc:`/explanations/region_design/index_zh` 解释区域为什么按顺序执行。
* :doc:`/reference/region_model/index_zh` 列出语言与模型的确切规则。
* :doc:`/reference/simulation/index_zh` 与 :doc:`/reference/bmc_query/index_zh` 列出上文用到的模拟器与查询事实。
