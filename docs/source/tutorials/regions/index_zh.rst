第一个含区域的模型
==================

本教程运行一个小型控制器，它在同一个状态里有两个\ **区域（region）**\ ，你会看到区域的顺序起什么作用。最后你会得到：模拟过这个控制器，对调区域顺序并看到结果改变，读到对应的检查诊断，用有界模型检查在两个版本上检查同一条性质，生成并运行 Python 运行时，并看过模型的图。

你需要装好 ``pyfcstm``。把 :download:`controller.fcstm </_models/controller.fcstm>`、:download:`controller_swapped.fcstm </_models/controller_swapped.fcstm>` 和 :download:`fault_beat_motor_off.fbmcq <fault_beat_motor_off.fbmcq>` 下载到一个空目录，所有命令都在该目录里运行。

1. 读模型
---------

控制器是一个联锁。\ ``Safety`` 区域决定电机能否运行，\ ``Motion`` 区域负责切换电机。

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

运行之前先注意三件事：

* ``Running`` 拥有两个 ``region`` 块。\ ``Running`` 活动时两者同时活动，各自有自己的初始转换（``[*] -> Watching`` 和 ``[*] -> Off``）。
* 同一个拥有者（owner）的区域在每个周期里\ **按书写顺序依次执行**。\ ``Safety`` 写在前面，所以它在同一周期里先写 ``permit``，\ ``Motion`` 后读。
* ``!Running -> Idle : /Stop;`` 是写在拥有者上的强制转换（forced transition）。它从两个区域所处的任何位置离开 ``Running``，所以 ``/Stop`` 一次停下整组。强制转换会引入隐藏变量 ``__forced_0``，你会在输出里看到它。

2. 模拟一段场景
---------------

用批处理模式运行一段场景。每个真正执行的周期都需要完整的输入向量，所以每个 ``cycle`` 都给出 ``fault`` 和 ``requested``。\ ``/Start`` 和 ``/Stop`` 是根事件。

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1; \
   cycle --input fault=0 --input requested=1; \
   cycle /Stop --input fault=0 --input requested=1"
   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=0
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Controller.Idle
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle /Start --input fault=0 --input requested=0
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 5
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle /Stop --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 6
   Current State: Controller.Idle
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

逐周期看 ``Current State`` 一行。含区域的模型会打印完整的\ **配置（configuration）**\ ：拥有者后面的花括号里是每个区域的位置，例如 ``Controller.Running{Safety: Watching, Motion: Off}``。

* 周期 1 进入 ``Controller.Idle``。
* 周期 2 处理 ``/Start``。两个区域都执行初始转换，\ ``permit`` 已经是 ``1``，因为 ``Safety`` 在同一周期里执行了它的 ``during``。
* 周期 3 有 ``requested=1``：\ ``Motion`` 转到 ``On``，\ ``motor`` 为 ``1``。
* 周期 4 有 ``fault=1``。看 ``motor``：它在这一个周期里就是 ``0``。\ ``Safety`` 先执行并写入 ``permit = 0``，随后 ``Motion`` 读到这个新值并切回 ``Off``。
* 周期 5 清除故障，电机重新运行。周期 6 处理 ``/Stop``：强制转换离开 ``Running``，配置又变回 ``Controller.Idle``。

3. 对调区域顺序
---------------

``controller_swapped.fcstm`` 有同样两个区域，只是 ``Motion`` 写在 ``Safety`` 前面，其余完全相同。运行同一场景，但让故障连续出现两个周期。周期 1 和 2 省略；周期 3 保留，方便和上面同一个周期比较：

.. code-block:: console

   $ pyfcstm simulate -i controller_swapped.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   >>> cycle --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Controller.Running{Motion: On, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Controller.Running{Motion: On, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 5
   Current State: Controller.Running{Motion: Off, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

把周期 4 和上一次运行比较。故障已经出现，\ ``permit`` 是 ``0``，\ ``motor`` 却仍是 ``1``。\ ``Motion`` 现在先执行，所以它读到的是 ``Safety`` 在上一个周期写的 ``permit``。电机晚一个周期，在周期 5 才关。配置文本里区域也按新顺序列出：``{Motion: On, Safety: Watching}``。

区域的书写顺序是模型含义的一部分。只在这个顺序上不同的两个模型是不同的模型。

4. 检查模型
-----------

``pyfcstm inspect`` 会报告区域并检查它们的顺序。报告很长，这里只给出开头：

.. code-block:: console

   $ pyfcstm inspect -i controller.fcstm
   [WARN] FCSTM Inspect Report: controller.fcstm

   Summary
     status: warning
     root: Controller
     states: 6 total / 4 leaf
     transitions: 7
     regions: 2
       Controller.Running.Safety: order 0 in Controller.Running; 1 states
       Controller.Running.Motion: order 1 in Controller.Running; 2 states
   ...
     diagnostics: 0 errors / 4 warnings / 0 infos
   ...
   [WARN] W_DURING_CONST_ASSIGN
   ...
   [WARN] W_LEAF_NO_OUTGOING_TRANSITION
   ...

摘要里有 ``regions: 2``，并列出每个区域在拥有者里的顺序（\ ``order 0`` 是写在最前面的）。``diagnostics:`` 一行统计出四条警告、没有提示：三条 ``W_DURING_CONST_ASSIGN`` 针对常量的 ``during`` 赋值，一条 ``W_LEAF_NO_OUTGOING_TRANSITION`` 针对一个没有出边的叶子状态。它们说的是这个示例的写法，与区域无关，也不影响上面的场景。

对调后的模型有同样的四条警告，外加一条诊断：它的 ``diagnostics:`` 一行统计出一条提示，报告以它结尾：

.. code-block:: console

   $ pyfcstm inspect -i controller_swapped.fcstm
   ...
     diagnostics: 0 errors / 4 warnings / 1 infos
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Controller.Running.Motion' reads variable 'permit', which is produced by the later region 'Controller.Running.Safety'; it sees the value from the previous cycle.
     --> controller_swapped.fcstm:16:13
       |
    15 |             state On { during { motor = 1; } }
    16 |             Off -> On : if [permit != 0 && requested != 0];
       |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    17 |             On -> Off : if [permit == 0 || requested == 0];
       |
      = source: inspect-static
      = why: An earlier region reads something a later region produces in the same cycle, so it sees the previous cycle's value.
      = fix: kind: confirm_order; target: region; rationale: Keep the declaration order when reading the previous cycle's value is intended.
      = fix: kind: reorder_regions; target: region; rationale: Declare the producing region before the reading region when the current cycle's value is needed.
      = do-not: Do not treat this as a defect; it is the defined behavior of ordered regions.

``I_REGION_BACKWARD_READ`` 是提示级诊断：\ ``Motion`` 读取的 ``permit`` 由靠后的 ``Safety`` 区域写入，所以 ``Motion`` 看到的是上一个周期的值。诊断信息写明这是有序区域的既定行为，不是缺陷。想要上一周期的值就保持顺序，想要当前周期的值就把写入方区域写在前面。

5. 用有界模型检查验证性质
-------------------------

写出性质“故障出现时，电机在该周期结束时是关的”。性质文件 ``fault_beat_motor_off.fbmcq`` 是：

.. literalinclude:: fault_beat_motor_off.fbmcq
   :language: text
   :caption: ``fault_beat_motor_off.fbmcq``

第一行假设故障输入在第 3 步（第四个宏步）非零。第二行是上界为 4 的 ``forbid`` 性质：搜索最多四个宏步的运行，使得第 3 步之后（``cycle == 4``）电机仍然是开的。

在联锁模型上运行：

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q fault_beat_motor_off.fbmcq
   BMC forbid <= 4: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   Scenario: FEASIBLE
   Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)
   Semantic interpretation: The counterexample objective is unsatisfiable over the feasible bounded scenario; every admissible execution within the bound satisfies the property.
   Primary search: COUNTEREXAMPLE = UNSAT
   Conclusion: Every admissible execution within 4 macro-steps satisfies the forbid property.
   Evidence:
     Model evidence: no SAT model available.

   Solver: UNSAT in ... ms
   Feasibility: kernel=sat, initialization=sat, assumptions=sat

   This is a bounded result over at most 4 macro-steps; it does not establish behavior beyond that bound.
   Use --json for the complete witness, replay trace, and stable machine-readable diagnostics.

先读结论：\ ``PROPERTY GUARANTEED WITHIN BOUND``。求解器搜索反例但没有找到（``UNSAT``），所以在第 3 步出现故障、至多 4 个宏步的所有运行里性质都成立。\ ``Solver`` 一行是求解耗时，每次运行都不同。最后几行是上界：它对更长的运行什么也没说。

再在对调后的模型上运行同一条性质。性质在这里不成立，所以命令以退出状态 ``1`` 结束：

.. code-block:: console

   $ pyfcstm bmc -i controller_swapped.fcstm -q fault_beat_motor_off.fbmcq
   BMC forbid <= 4: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   Scenario: FEASIBLE
   Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)
   Semantic interpretation: A counterexample execution exists within the bound; the property is not satisfied there.
   Primary search: COUNTEREXAMPLE = SAT
   Conclusion: At least one admissible execution violates the forbid property within 4 macro-steps.
   Evidence:
     Model role: PRIMARY COUNTEREXAMPLE
     Model evidence: SAT model available.
     Replay: verified (5 frames, 4 steps).

   Solver: SAT in ... ms
   Feasibility: kernel=sat, initialization=sat, assumptions=sat

   Trace
     0: init
          -> Controller.Idle [initial]
          [start] -> Controller.Idle [initial]
     1: Controller.Idle
          -> Controller.Running{Motion: Off, Safety: Watching} [transition; events=Controller.Start]
          Controller.Idle -> Controller.Running [transition]
          Running: [start] -> Motion.Off [initial]
          Running: [start] -> Safety.Watching [initial]
     2: Controller.Running{Motion: Off, Safety: Watching}
          -> Controller.Running{Motion: On, Safety: Watching} [transition]
          Motion: Off -> On [transition]
          Safety: Watching -> Watching [fallback]
     3: Controller.Running{Motion: On, Safety: Watching}
          -> Controller.Running{Motion: On, Safety: Watching} [fallback]
          Motion: On -> On [fallback]
          Safety: Watching -> Watching [fallback]

   This is a bounded result over at most 4 macro-steps; it does not establish behavior beyond that bound.
   Use --json for the complete witness, replay trace, and stable machine-readable diagnostics.
   $ echo $?
   1

结论是 ``PROPERTY DOES NOT HOLD WITHIN BOUND``，求解器状态是 ``SAT``。求解器状态描述的是反例搜索，结论才是对你的性质意味着什么。这里的 ``SAT`` 是坏消息，上一次的 ``UNSAT`` 是好消息。轨迹就是反例：\ ``Motion`` 在第 2 步 ``Off -> On``，第 3 步虽然有故障仍保持 ``On``，这正是你在模拟器里看到的晚关。\ ``Replay: verified`` 表示模拟器复现了这条轨迹。结果的全部字段见 :doc:`/reference/bmc_results/index_zh`。

6. 生成并运行 Python 运行时
---------------------------

为联锁模型生成内置的 Python 运行时。命令不打印任何内容，只把 ``machine.py`` 和两个 README 文件写进 ``runtime_out``：

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o runtime_out

用第 2 步的场景驱动生成的 ``ControllerMachine``。把下面的脚本保存为同一目录里的 ``run_scenario.py``，用 ``python run_scenario.py`` 运行：

.. testcode::

   import sys

   sys.path.insert(0, "runtime_out")
   from machine import ControllerMachine

   # (event, fault, requested) for each cycle of the scenario.
   scenario = [
       (None, 0, 0),
       ("/Start", 0, 0),
       (None, 0, 1),
       (None, 1, 1),
       (None, 0, 1),
       ("/Stop", 0, 1),
   ]

   machine = ControllerMachine()
   for event, fault, requested in scenario:
       machine.cycle(events=event, inputs={"fault": fault, "requested": requested})
       print(
           machine.cycle_count,
           machine.configuration,
           "permit=%d" % machine.vars["permit"],
           "motor=%d" % machine.vars["motor"],
       )

It prints:

.. testoutput::

   1 Controller.Idle permit=0 motor=0
   2 Controller.Running{Safety: Watching, Motion: Off} permit=1 motor=0
   3 Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1
   4 Controller.Running{Safety: Watching, Motion: Off} permit=0 motor=0
   5 Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1
   6 Controller.Idle permit=1 motor=0

六行输出对应第 2 步的六个周期：配置、\ ``permit`` 和 ``motor`` 都相同，包括故障周期里电机关断。含区域的模型没有 ``current_state_path``，位置要用 ``configuration`` 读。

7. 看图
-------

``pyfcstm plantuml`` 打印模型的 PlantUML 文本，下面是画出 ``Running`` 里两个区域的部分：

.. code-block:: console

   $ pyfcstm plantuml -i controller.fcstm
   @startuml
   ...
       state "Running" as controller__running <<composite>> {
           note as controller__running__safety
               **region 1: Safety**
           end note
           state "Watching" as controller__running__safety__watching
           [*] --> controller__running__safety__watching
           --
           note as controller__running__motion
               **region 2: Motion**
           end note
   ...
   @enduml

在 ``Running`` 里找到两条区域注释 ``region 1: Safety`` 和 ``region 2: Motion``。一行 ``--`` 把区域隔开，渲染出的图里它们上下堆叠：

.. figure:: /_models/controller.fcstm.puml.svg
   :alt: 控制器的 PlantUML 图，Safety 区域在 Motion 区域上方
   :align: center

   ``Running`` 里 ``region 1: Safety`` 在 ``region 2: Motion`` 上方，中间用虚线隔开。

``pyfcstm diagram`` 写出交互式查看器，它是一个不需要网络的自包含 HTML 文件。文档检查不运行这条命令，因为写出查看器需要打包好的查看器资源，打开它还需要浏览器：

.. code-block:: bash

   pyfcstm diagram -i controller.fcstm -o viewer.html

在浏览器里打开 ``viewer.html``。检查 ``Running`` 的外框里有两个区域，标题分别是 ``region 1: Safety`` 和 ``region 2: Motion``，中间用虚线隔开。

8. 下一步
---------

现在你有了一个区域按书写顺序执行的模型，并在模拟器、检查报告、检查器、生成的运行时和图里都见过这个顺序。按你想做的事继续：

* :doc:`/how_to/regions/index_zh` 是任务做法：添加区域、选择顺序、读取配置、对含区域的模型热启动（hot start）。
* :doc:`/explanations/region_semantics/index_zh` 用轨迹解释一个周期怎样执行含区域的模型。
* :doc:`/explanations/region_design/index_zh` 解释区域为什么按顺序执行。
* :doc:`/reference/region_model/index_zh` 列出语言与模型的确切规则。
* :doc:`/reference/simulation/index_zh` 和 :doc:`/reference/bmc_query/index_zh` 列出上面用到的模拟器与查询事实。
