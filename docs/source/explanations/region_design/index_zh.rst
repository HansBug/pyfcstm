.. _sec-explanations-region-design-zh:

区域为什么按顺序执行，以及与其他工具的差别
==========================================

本页回答“为什么”：为什么一个状态的各个区域按书写顺序一个接一个执行，为什么事件是输入而不是消息，为什么 ``!`` 强制转换（forced transition）与 ``active()`` 是语法糖，以及首版有意不做什么。然后把 FCSTM 与 Stateflow、SCXML 放在一起比较。模拟器在一个周期里做什么见\ :doc:`/explanations/region_semantics/index_zh`\ ；确切写法见\ :doc:`/reference/region_model/index_zh`\ 。

本页的证据规则。下面所有关于 FCSTM 的陈述都用随仓库发布的工具实际运行核对过，命令与输出在本页，或在语义页里（相应陈述带有指向它们的链接）。关于 Stateflow 的陈述是设计这项功能时在 MATLAB R2020a Update 8（Stateflow 10.2）上做过的实验的记录，下表每个 Stateflow 格都附有保存记录的 issue（并行状态与历史见\ `issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_\ ，离开含子状态的状态的转换见\ `issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_\ ）；本页关于 Stateflow 的内容没有一句来自记忆，没有记录的写作“未记录”。关于 SCXML 的陈述是 W3C SCXML 1.0 文本的原文引用，并给出章节号。UML 状态机不做比较，因为写本页时没有核对过它的文本。

为什么有序，而不是并发或不定序
------------------------------

含区域的模型可以有三种含义：区域跑在真正的线程上；以工具自由选择的顺序执行；按作者书写的顺序执行。语言选了第三种，理由有三条，在日常使用中都看得到。

**确定性。**\ 同一个模型、同样的输入，在任何机器上每次运行的轨迹都相同。共用变量的两位作者不必推演交错执行，因为没有交错。

**顺序是建模手段。**\ 教程里的交锁控制器需要安全区域先于运动区域作出决定。有序区域时，这只要在模型里写一句：先写 ``Safety``\ 。\ :doc:`语义页 </explanations/region_semantics/index_zh>`\ 用同样的输入对比了两种顺序：顺序对调后，电机晚一个周期关断。不定序会让同一个模型的两种结果都合法。

**每个工具里含义相同。**\ 被检查、被仿真、被当作生成代码运行的模型必须只有一种含义。下面把对调后的控制器分别放进模拟器和生成的 Python 运行时运行，再用有界模型检查核对性质“只有 ``permit`` 不为 0 时电机才开着”：

.. code-block:: console

   $ pyfcstm generate -i controller_swapped.fcstm --template python -o out

.. testcode::

   import sys

   sys.path.insert(0, "out")
   from machine import ControllerMachine

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   ready = {"fault": 0, "requested": 1}
   fault = {"fault": 1, "requested": 1}
   steps = [(None, ready), (["/Start"], ready), (None, ready), (None, fault), (None, fault), (None, ready)]
   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   simulator = SimulationRuntime(model, input_source=ready)
   generated = ControllerMachine()
   for number, (events, inputs) in enumerate(steps, start=1):
       simulator.cycle(events, inputs=inputs)
       generated.cycle(events, inputs=inputs)
       same = str(simulator.configuration) == generated.configuration and all(
           simulator.vars[name] == generated.vars[name] for name in ("permit", "motor")
       )
       print(number, generated.configuration, generated.vars["permit"], generated.vars["motor"], same)

.. testoutput::

   1 Controller.Idle 0 0 True
   2 Controller.Running{Motion: Off, Safety: Watching} 1 0 True
   3 Controller.Running{Motion: On, Safety: Watching} 1 1 True
   4 Controller.Running{Motion: On, Safety: Watching} 0 1 True
   5 Controller.Running{Motion: Off, Safety: Watching} 0 0 True
   6 Controller.Running{Motion: Off, Safety: Watching} 1 0 True

.. literalinclude:: interlock.fbmcq
   :language: text
   :caption: ``interlock.fbmcq``

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q interlock.fbmcq
   BMC invariant <= 8: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   Scenario: FEASIBLE
   Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)
   ...
   $ pyfcstm bmc -i controller_swapped.fcstm -q interlock.fbmcq
   BMC invariant <= 8: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   Scenario: FEASIBLE
   Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)
   ...
   $ echo $?
   1

* 两个运行时每个周期都一致，包括对调后的控制器同时出现 ``permit=0`` 与 ``motor=1`` 的那个周期。
* 在 ``Safety`` 在前的控制器上，性质在上界内成立；在对调后的控制器上，性质在上界内被违反（退出状态 ``1`` 表示违反）。检查器找到了轨迹里那个晚一拍的现象，而没有人为它写过测试。
* 这不证明性质永远成立：结果受限于 8 个宏步，报告自己也这么说。含区域的周期怎样编码见\ :doc:`/explanations/bmc_regions/index_zh`\ 。

如果区域以不定的顺序执行，检查器就得考虑每一种顺序，生成代码得挑一种，“模拟器与生成代码一致”也就不再是一条可以测试的性质。真正的并发语义会让检查器的情形数乘上交错数。有序执行让代价与各区域之和成正比，这是\ :doc:`/explanations/region_performance/index_zh`\ 的主题。

代价。对顺序敏感的模型很容易写出来。因此 ``pyfcstm inspect`` 会报告靠前的区域读取靠后区域所写的变量，以及靠后区域悄悄覆盖靠前写入的情形；见\ :doc:`/explanations/diagnostics/index_zh`\ 。

事件是输入，不是消息
--------------------

FCSTM 里的事件是调用方为一个周期提供的标志。周期里所有部分看到同一个集合，用掉一个事件并不会把它移走。没有引发事件的语句，没有广播，没有队列，也没有确认。

理由与上面相同。机器内部的队列会增加第二种时间（周期内的步），而“这个事件什么时候被那个区域看到”需要一个所有工具都认同的回答。事件来自外部时，回答是“在周期里轮到它时，永远是同一个集合”。

语言围绕这一点设计：区域声明的事件归该区域，依赖位置的名字对每个活动叶子各解析一次，有歧义就拒绝（见\ :doc:`语义页 </explanations/region_semantics/index_zh>`\ ）。区域需要告诉另一个区域什么，就写一个变量，另一个区域在轮到它时读取；顺序决定它在哪个周期看到。

有内部队列的 SCXML 是这样写的：\ ``The SCXML processor MUST place the event that is generated at the rear of the session's internal event queue.``\ （W3C SCXML 1.0，4.2 节）。FCSTM 有意不提供对应的队列。

强制转换与 ``active()`` 是语法糖
--------------------------------

两者都被语言接受，并在任何东西运行之前被去掉：模拟器、生成的运行时和有界模型检查器都看不到特例。

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - 写法
     - 实际运行
     - 代价
   * - 含区域的状态上的 ``!P -> Off : if [x >= 2];``
     - 每个区域里两条 ``-> [*]`` 转换（置起隐藏变量的发起者和跟随者），再加拥有者（owner）的两条转换。见语义页里的展开式。
     - ``runtime.vars`` 与生成代码里多一个隐藏变量 ``__forced_<n>``\ ；多出的转换；更长的导出文本。
   * - ``active("Root.P.A.A2")``
     - 一个隐藏变量 ``__active_Root_P_A_A2``\ ，在该状态 ``enter`` 的第一行置起，在 ``exit`` 的最后一行清除。
     - 一个隐藏变量，以及被查询状态两个块里的赋值。

把它们保持为语法糖，首版接受三个后果：

* 模型与它导出的文本在每个环节行为一致。检查靠真实运行：控制器与它的导出文本产生相同的周期（输出在语义页里）。
* 隐藏变量是普通变量。热启动（hot start）要提供它们，运行时不推导也不校验。这是调用方的负担，也是没有特例的代价。
* 展开式不能与其他工具完全一致的地方，差异被保留并记录，例如同一个拥有者里两条相互竞争的强制声明（\ `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_\ ）。

图与 ``pyfcstm inspect`` 的报告按书写的模型呈现，不显示隐藏变量。加上 ``--enable-verify`` 时，说明机器怎样运行的发现按实际运行的机器判断，因此可能点名隐藏变量（见\ :doc:`/explanations/diagnostics/index_zh`\ ）。

首版不做什么
------------

下面每一项都是语言的有意界限。五个示例里四个被语法拒绝，区域之间的跳转被模型构建拒绝，输出是真实的：

.. testcode::

   from pyfcstm.dsl.error import GrammarParseError
   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.utils.validate import ModelValidationError

   cases = [
       ("history written on an owner", "state Root { [*] -> P; state P { region R { [*] -> A; state A; } [H] -> A; } }"),
       ("child states mixed with a region", "state Root { [*] -> P; state P { state X; region R { [*] -> A; state A; } } }"),
       ("enter block inside a region", "state Root { [*] -> P; state P { region R { enter { } [*] -> A; state A; } } }"),
       ("jump from one region to another", "state Root { [*] -> P; state P { region R1 { [*] -> A; state A; } region R2 { [*] -> B; state B; B -> A; } } }"),
       ("variable declared in a region", "state Root { [*] -> P; state P { region R { def int x = 0; [*] -> A; state A; } } }"),
   ]
   for title, text in cases:
       try:
           load_state_machine_from_text(text)
       except (GrammarParseError, ModelValidationError) as error:
           # GrammarParseError: the grammar refuses the text; ModelValidationError: the model builder refuses it.
           print("==", title)
           print(type(error).__name__)
           print("\n".join(str(error).splitlines()[:2]))

.. testoutput::

   == history written on an owner
   GrammarParseError
   Found 2 errors during parsing:
   Error 1: Syntax error at line 1, column 65, near '[H]': Unexpected token '[H]'
   == child states mixed with a region
   GrammarParseError
   Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 42, near 'region': Unexpected token 'region'
   == enter block inside a region
   GrammarParseError
   Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 44, near 'enter': Unexpected token 'enter'
   == jump from one region to another
   ModelValidationError
   Unknown to state 'A' of transition:
   B -> A; (line 1)
   == variable declared in a region
   GrammarParseError
   Found 2 errors during parsing:
   Error 1: Syntax error at line 1, column 44, near 'def': Unexpected token 'def'

* **拥有者上的历史。**\ 拥有者不能在区域旁边声明 ``[H]`` 或 ``[H*]``\ （第一个示例把 ``[H] -> A`` 写在区域之后）。区域内部的复合状态的历史可以使用。
* **子状态与区域混写。**\ 一个状态要么含普通子状态，要么含区域。
* **区域里的生命周期动作与变量。**\ 区域里放状态、转换、事件和切面（aspect）。``enter``\ 、``during``\ 、``exit`` 与变量声明属于拥有者或状态。
* **在区域之间跳转。**\ 转换不能从一个区域离开去另一个区域的状态，也不能从外部进入区域里的状态；转换以拥有者为终点。第四个示例在区域 ``R2`` 里写 ``B -> A``\ 去找 ``R1`` 的状态：``A`` 不是 ``R2`` 的状态，所以模型构建拒绝它（``Unknown to state 'A' of transition``\ ）。
* **内部事件与队列。**\ 不提供，见上文。
* **真正的并行。**\ 不提供；区域只是逻辑并发。

FCSTM 与 Stateflow、SCXML 的差别
--------------------------------

表里列出任务要求的几个主题，以及各来源能支撑什么。``未记录`` 表示本页没有可用的实验或引文，该格有意不作任何断言。

.. list-table::
   :header-rows: 1
   :widths: 16 28 28 28

   * - 主题
     - FCSTM（随仓库发布的工具）
     - Stateflow（R2020a 实验）
     - SCXML 1.0（W3C 文本）
   * - 同时活动的部分
     - 活动拥有者的所有区域。配置每个区域列一个位置，例如 ``Controller.Running{Safety: Watching, Motion: On}``\ 。
     - 拥有者之下的并行（AND）状态；实验用的是一个带两个并行子状态的拥有者（\ `issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_\ ）。
     - “The <parallel> element encapsulates a set of child states which are simultaneously active when the parent element is active.”（3.4）
   * - 各部分的执行顺序
     - 书写顺序，可观察且有保证（轨迹见语义页）。
     - 未记录
     - 未记录
   * - 事件从哪里来
     - 周期的输入，所有区域共享，不会被移走。区域没有引发事件的办法。
     - 未记录
     - 机器引发的事件进入队列：\ ``The SCXML processor MUST place the event that is generated at the rear of the session's internal event queue.``\ （4.2）
   * - 事件的作用范围
     - 区域拥有它声明的事件；依赖位置的名字对每个活动叶子各解析一次，有歧义就拒绝。
     - 未记录
     - 未记录
   * - 完成的含义
     - 区域内写的 ``-> [*]`` 被执行时该区域已完成；最后一个已完成的区域在同一周期经拥有者的出边续接，或者这次完成被拒绝。
     - 未记录
     - “When all of the children reach final states, the <parallel> element itself is considered to be in a final state”（3.1.3）
   * - 历史
     - 拥有者不能声明历史。区域内的复合状态可以，拥有者经 ``Owner.[H]`` 或 ``Owner.[H*]`` 进入。
     - 并行（AND）状态不能直接放历史连接点（模型在编译时被拒绝）；它外面和里面的 OR 状态可以。只在外层状态放历史时，两个并行分支都从各自的第一个状态重新开始；外层与每个分支都放历史时，各分支恢复各自的最后一个状态（\ `issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_\ ）。
     - 未记录
   * - 状态查询
     - ``active("路径")``\ ，隐藏标志的语法糖；从 ``enter`` 开始到 ``exit`` 结束为真。
     - 转换条件里的 ``in(P.a2)``\ 。实测：条件读取转换源状态内部的某个状态时，机器停在那个状态里条件即成立（\ `issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_\ ，第二个情形）。
     - 未记录
   * - 离开含子状态的状态的转换
     - 只在机器停驻的状态上判一次；目标进不去则转换什么也不做。含区域时按上文展开。
     - 在互斥父状态上实测：条件在父状态上判一次，退出顺序由内向外，改了条件所读变量的退出动作不会取消转换。目标进不去的图在编译时被拒绝；把该诊断降为警告后，运行时以 “State inconsistency” 错误中止（\ `issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_\ ，第 3、6 个情形，以及“目标进不去”一节）。
     - 未记录

表中 Stateflow 关于强制转换的格子来自\ `issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_\ 记录的十二个对照模型，父状态都是互斥的：十一个与当前展开逐步一致，第十二个的差别与这条转换无关。它们对并行状态没有任何说明，而 FCSTM 展开到区域里的做法只与 FCSTM 自己比较过（共享用例）。区域里仍存在的两处差异见\ `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_\ 。

从 Stateflow 迁移
-----------------

下面是 Stateflow 用户最先遇到的差别。每一条都是关于 FCSTM 的事实，可以用本页的命令核对；有实验的地方才标出 Stateflow 一侧。

* **区域是名字空间，不是状态。**\ 路径经过区域（``Controller.Running.Motion.On``\ ），同一个状态名可以出现在两个区域里。Stateflow 的并行子状态是状态；实验也按状态处理（\ `issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_\ ）。
* **顺序就是文本顺序。**\ 在 FCSTM 里 ``region`` 块的位置就是顺序，没有别的东西可设。调换块的位置会改变行为，对调后的控制器就是例子。Stateflow 怎样给并行状态排序，本页没有测过。
* **历史是显式的。**\ 转换用 ``Owner.[H]`` 或 ``Owner.[H*]`` 进入历史；不会因为状态里有一个连接点就记住什么。拥有者本身不能带历史。
* **事件不会传递。**\ 没有东西在区域之间发送事件。用变量加顺序。
* **整组经**\ ``-> [*]``\ **离开。**\ 用强制转换离开整组就是上面的展开，不是特例。仍存在的差异见\ `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_\ 。
* **变量是输入、控制和输出。**\ 持久变量在根状态之前声明；关键字 ``log`` 等函数名不能当变量名。

这次比较的界限
--------------

* Stateflow 的实验只用了一个产品版本（R2020a Update 8），不描述其他版本。
* 顺序、事件作用范围与完成含义没有为 Stateflow 测过，因此不做比较。
* 不比较 UML 状态机。
* SCXML 的引文说明文本写了什么，不说明任何实现的行为。
