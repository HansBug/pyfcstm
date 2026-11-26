.. _sec-explanations-region-semantics-zh:

含区域的模型怎样执行一个周期
============================

声明了 ``region`` 的状态是一个\ **拥有者**\ （owner）：它的各个区域同时处于活动状态，但整台机器仍然只有一个全局周期、一份输入采样和一个周期计数。本页说明模拟器在这一个周期里做了什么，为什么结果是这样，哪些行为是有意设下的界限。本页不教语法（见\ :doc:`第一个含区域的模型 </tutorials/regions/index_zh>`\ ），不列写法清单（见\ :doc:`/reference/region_model/index_zh`\ ），也不解释语言为什么选择有序区域（见\ :doc:`区域为什么按顺序执行，以及与其他工具的差别 </explanations/region_design/index_zh>`\ ）。不含区域的模型的执行规则在\ :doc:`/explanations/execution_semantics/index_zh`\ ；那里的规则在只有一个区域的拥有者之下仍然成立。

本页的每一处输出都是随仓库发布的模拟器的真实输出。支撑各项论断的共享语义用例列在\ :ref:`region-semantics-evidence-zh`\ 。

术语
----

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - 术语
     - 含义
   * - 拥有者
     - 包含区域而不是普通子状态的状态。
   * - 区域
     - 拥有者里的命名容器。区域里的状态与事件都带着区域这一段路径，例如 ``Controller.Running.Motion.On``\ 。
   * - 分支
     - 一个区域连同它所处的位置。
   * - 配置
     - 整台机器的位置，是一棵树：不含区域的模型是一条路径，拥有者之下每个区域各有一个位置。
   * - 已完成
     - 区域内直接写的 ``-> [*]`` 转换被执行后，该区域完成。位置文本写作 ``[done]``\ 。
   * - Delta
     - 无法得到合法配置的周期。它什么也不提交：位置与变量保持原样，周期仍然计数。
   * - 等待初始化
     - 尚未进入的区域。位置文本写作 ``[init]``\ 。

贯穿全页的模型
--------------

多数小节复用同一个模型，即教程里的交锁控制器。``Safety`` 区域决定是否允许电机运转，``Motion`` 区域负责开关电机：

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

``fault`` 与 ``requested`` 是输入。``permit`` 由 ``Safety`` 写、由 ``Motion`` 读，这条依赖使两个区域的顺序变得重要。``/Start`` 进入 ``Running``\ 。``!Running -> Idle : /Stop`` 是拥有者上的强制转换（forced transition），见\ :ref:`region-semantics-forced-zh`\ ；部分输出里出现的隐藏变量 ``__forced_0`` 就来自它。

怎样读例子
----------

本页的命令与脚本在一个目录里运行，目录里放着本页展示的 ``.fcstm`` 文件，脚本从当前目录读取它们。多数例子打印每个周期之后的配置与变量。需要看清一个周期内部的先后时，脚本向模拟器要求轨迹：``cycle(..., trace=True)`` 返回 ``CycleResult.trace``\ ，每一步是一条已提交的观察。下面的脚本打印控制器处理 ``/Start`` 的那个周期的轨迹，并在每一步之后给出 ``permit`` 的值：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   runtime.cycle([])
   result = runtime.cycle(["/Start"], trace=True)
   for entry in result.trace:
       where = entry.transition_label or entry.action_path or ".".join(entry.state_path)
       print(entry.kind, where, "permit =", entry.vars["permit"])
   print(runtime.configuration)

.. testoutput::

   state_exit Controller.Idle permit = 0
   transition Controller.Idle::0::Idle->Running permit = 0
   state_enter Controller.Running permit = 0
   transition Controller.Running.Safety::0::INIT_STATE->Watching permit = 0
   state_enter Controller.Running.Safety.Watching permit = 0
   action Controller.Running.Safety.Watching::on_durings::0 permit = 1
   transition Controller.Running.Motion::0::INIT_STATE->Off permit = 1
   state_enter Controller.Running.Motion.Off permit = 1
   action Controller.Running.Motion.Off::on_durings::0 permit = 1
   Controller.Running{Safety: Watching, Motion: Off}


* ``state_enter`` 与 ``state_exit`` 表示状态加入或离开配置；该状态的 ``enter`` 块与 ``exit`` 块显示为 ``action`` 行，地址里带 ``on_enters`` 或 ``on_exits``\ 。
* ``transition`` 行带标签 ``范围::序号::源->目标``\ 。``INIT_STATE`` 表示该范围的初始转换 ``[*]``\ ，序号是它在源状态的转换列表里的位置。
* ``action`` 行带 ``状态::集合::序号``\ ：``on_durings`` 是 ``during`` 块，``on_during_aspects`` 是所指范围的 ``>> during before`` 或 ``>> during after`` 块。
* 最后一行是周期结束时机器停驻的配置。

命令行显示同样的配置文本。下面是交锁控制器跑三个周期后的结果：

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   cycle --input fault=0 --input requested=1; \
   cycle /Start --input fault=0 --input requested=1; \
   cycle --input fault=0 --input requested=1"
   ...
   Cycle: 3
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

``Controller.Running{Safety: Watching, Motion: On}`` 是一段配置文本：先写拥有者，再按书写顺序写每个区域的位置。最后两个周期里两个区域都做了工作，计数器却只写 ``Cycle: 3``\ 。

.. _region-semantics-one-cycle-zh:

一个周期，一份输入采样，一次计数
--------------------------------

**论断**\ ：一个周期按书写顺序把活动拥有者的每个区域各推进一次。所有区域看到同一份输入和同一个事件集合，周期计数只加一。

周期 2 的轨迹在上一节。下面的脚本把同样的四个周期跑一遍，打印周期 3 与周期 4 的轨迹，后者是 ``fault`` 置 1 的那个周期：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   runtime.cycle([])
   runtime.cycle(["/Start"])
   for fault in (0, 1):
       result = runtime.cycle([], inputs={"fault": fault}, trace=True)
       print("cycle", runtime.cycle_count, "fault", fault)
       for entry in result.trace:
           where = entry.transition_label or entry.action_path or ".".join(entry.state_path)
           print(" ", entry.kind, where, "permit =", entry.vars["permit"], "motor =", entry.vars["motor"])

.. testoutput::

   cycle 3 fault 0
     action Controller.Running.Safety.Watching::on_durings::0 permit = 1 motor = 0
     state_exit Controller.Running.Motion.Off permit = 1 motor = 0
     transition Controller.Running.Motion.Off::2::Off->On permit = 1 motor = 0
     state_enter Controller.Running.Motion.On permit = 1 motor = 0
     action Controller.Running.Motion.On::on_durings::0 permit = 1 motor = 1
   cycle 4 fault 1
     action Controller.Running.Safety.Watching::on_durings::0 permit = 0 motor = 1
     state_exit Controller.Running.Motion.On permit = 0 motor = 1
     transition Controller.Running.Motion.On::2::On->Off permit = 0 motor = 1
     state_enter Controller.Running.Motion.Off permit = 0 motor = 1
     action Controller.Running.Motion.Off::on_durings::0 permit = 0 motor = 0


从上往下读四个周期：

* **周期 1** 是脚本里的第一个 ``runtime.cycle([])``\ ，没有打印。之后 ``Idle`` 处于活动，可以从周期 2 离开它看出来。
* **周期 2** 带着 ``/Start``\ 。离开 ``Idle``\ ，进入 ``Running``\ ，然后各区域依次启动：``Safety`` 先走初始转换并执行第一次 ``during``\ （``permit`` 变为 1），``Motion`` 才走自己的初始转换，进入 ``Off`` 并在同一周期执行 ``Off`` 的 ``during``\ 。
* **周期 3** 先执行 ``Safety`` 的 ``during``\ ，再轮到 ``Motion``\ 。``Motion`` 发现 ``permit != 0 && requested != 0``\ ，执行 ``Off -> On``\ ；``On`` 的 ``during`` 在同一周期打开电机。
* **周期 4** 把 ``fault`` 置 1。``Safety`` 先把 ``permit`` 清零，``Motion`` 随后读到新值，执行 ``On -> Off``\ 。

下表是一个周期内的顺序。每一行都是模拟器在每个周期里遵守的承诺；右列指出本页哪处输出里能看到它。

.. list-table:: 区域都在工作时，拥有者处的一个周期的顺序
   :header-rows: 1
   :widths: 6 50 44

   * - 步骤
     - 执行内容
     - 在哪里看到
   * - 1
     - 输入只采样一次，本次调用的事件在整个周期内固定。区域执行期间两者都不变。
     - :ref:`region-semantics-visibility-zh`\ 的每一行。
   * - 2
     - 判断第一个区域的转换条件，用的是当前的值。
     - 上面的周期 3 与 4：``Safety`` 没有转换，直接执行 ``during``\ 。
   * - 3
     - 拥有者之下第一次 ``during`` 工作之前，先执行拥有者及其祖先的 ``>> during before``\ ，由外向内。它们对整组只执行一次，不按区域计次。
     - :ref:`region-semantics-aspects-zh`\ 。
   * - 4
     - 每个区域按书写顺序执行：一次转换（源状态 ``exit``\ 、``effect``\ 、目标 ``enter``\ ），或停驻叶子的 ``during``\ 。已完成的区域什么也不做。
     - 上面的周期 3 与 4。
   * - 5
     - 区域自己的 ``>> during after`` 在它的分支结束时执行，所以后面的区域能看到它写的值。
     - :ref:`region-semantics-aspects-zh`\ 。
   * - 6
     - 拥有者及其祖先的 ``>> during after`` 在最后一个区域之后只执行一次，由内向外。
     - :ref:`region-semantics-aspects-zh`\ 。
   * - 7
     - 周期计数加一，历史记录写入结果配置。
     - 上面命令行输出的 ``Cycle:`` 一行。

下面是此后要用的 ``controller_swapped.fcstm``\ 。它就是前面各节的控制器，只是两个区域的书写顺序相反：\ ``Motion``\ （第 12 行）排在 ``Safety``\ （第 19 行）之前，其余完全相同。

.. literalinclude:: /_models/controller_swapped.fcstm
   :language: fcstm
   :caption: ``controller_swapped.fcstm``
   :emphasize-lines: 12,19

**顺序靠什么保证。**\ 区域按书写顺序执行，是因为 ``region`` 块的先后属于模型本身：``to_ast_node()``\ 、格式化和重新加载都保持它。下面的脚本加载 ``controller_swapped.fcstm``\ （上面展示的两个区域写成相反顺序的控制器），用 ``to_ast_node()`` 导出，再把导出的文本加载一遍。两个模型列出的 ``Running`` 的区域都保持书写顺序：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   again = load_state_machine_from_text(str(model.to_ast_node()))
   for item in (model, again):
       print(list(item.root_state.substates["Running"].regions))

.. testoutput::

   ['Motion', 'Safety']
   ['Motion', 'Safety']


**这不能说明什么。**\ 区域不是线程，也不被调度。顺序与时间无关，没有办法让两个区域“在同一时刻”运行。

.. _region-semantics-visibility-zh:

后面的区域看到什么
------------------

**论断**\ ：书写位置靠后的区域能读到前面区域在本周期写入的值，也能看到它们已进入的状态。前面的区域不会因为后面的区域写了什么而重新执行；它在下一周期才看到后面区域的值。多个区域写同一个变量时，最后一次写入生效。

.. literalinclude:: visible_forward.fcstm
   :language: fcstm
   :caption: ``visible_forward.fcstm``\ ：写入者先声明

.. literalinclude:: visible_backward.fcstm
   :language: fcstm
   :caption: ``visible_backward.fcstm``\ ：读取者先声明

.. literalinclude:: multi_writer.fcstm
   :language: fcstm
   :caption: ``multi_writer.fcstm``\ ：三个区域写同样的变量

脚本把每个模型运行三个周期，并在每个周期之后打印变量：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("visible_forward", "visible_backward", "multi_writer"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for _ in range(3):
           runtime.cycle([])
           print(name, runtime.cycle_count, dict(runtime.vars))

.. testoutput::

   visible_forward 1 {'x': 1, 'y': 1}
   visible_forward 2 {'x': 2, 'y': 2}
   visible_forward 3 {'x': 3, 'y': 3}
   visible_backward 1 {'x': 1, 'y': 0}
   visible_backward 2 {'x': 2, 'y': 1}
   visible_backward 3 {'x': 3, 'y': 2}
   multi_writer 1 {'x': 2, 'y': 13}
   multi_writer 2 {'x': 2, 'y': 143}
   multi_writer 3 {'x': 2, 'y': 1443}


* 正向模型里每一行都是 ``y`` 等于 ``x``\ ：``Rd`` 复制了 ``W`` 刚写入的值。
* 反向模型里 ``y`` 总是慢一拍：``Rd`` 先于 ``W`` 运行，复制的是上一周期的 ``x``\ ；``W`` 不会为了补上而重跑。
* 多写入者模型里，各区域依次写 ``x = 1``\ （``R1``\ ）、``x = 2``\ （``R2``\ ）以及 ``y + 1``\ 、``y * 10``\ 、``y + 3`` 这条链，所以 ``x`` 最终为 2，``y`` 依次为 13、143、1443。没有报告，也没有回滚。

下一个模型里，两个区域在每个周期加的是同一个输入 ``k``\ ：

.. literalinclude:: sampled_once.fcstm
   :language: fcstm
   :caption: ``sampled_once.fcstm``\ ：两个区域读同一个输入

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("sampled_once.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"k": 0})
   for k in (2, 3):
       runtime.cycle([], inputs={"k": k})
       print("k =", k, dict(runtime.vars))

.. testoutput::

   k = 2 {'a': 2, 'b': 2}
   k = 3 {'a': 5, 'b': 5}


``a`` 与 ``b`` 相等：第一个周期之后是 2，第二个周期之后是 5。输出展示的是单次采样的后果，展示不了采样本身；这一契约属于 ``SimulationRuntime.cycle``\ ：每个输入源每个周期只读一次，快照由本周期的所有条件与动作共享。

**交锁控制器，两种顺序。**\ 控制器是顺序会改变可观察行为的例子。同一串输入分别喂给 ``Safety`` 在前的模型和 ``Motion`` 在前的对调模型（打印周期 4 到 7；``fault`` 在周期 4 与 5 为 1）：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("controller", "controller_swapped"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
       for events in (None, ["/Start"], None):
           runtime.cycle(events)
       for fault in (1, 1, 0, 0):
           runtime.cycle([], inputs={"fault": fault})
           print(name, runtime.cycle_count, "fault", fault, end=" ")
           print("permit", runtime.vars["permit"], "motor", runtime.vars["motor"])

.. testoutput::

   controller 4 fault 1 permit 0 motor 0
   controller 5 fault 1 permit 0 motor 0
   controller 6 fault 0 permit 1 motor 1
   controller 7 fault 0 permit 1 motor 1
   controller_swapped 4 fault 1 permit 0 motor 1
   controller_swapped 5 fault 1 permit 0 motor 0
   controller_swapped 6 fault 0 permit 1 motor 0
   controller_swapped 7 fault 0 permit 1 motor 1


看周期 4，``fault`` 变为 1。``Safety`` 在前时，``permit`` 降为 0，电机在同一周期关断。``Motion`` 在前时，电机仍在转（``motor 1``\ ）而 ``permit`` 已经是 0，晚一个周期才关断。对调模型恢复也晚一个周期（周期 7，对比周期 6）。两台机器都是正确的程序，只是不同的程序。这就是顺序属于语言本身的原因，也是\ :doc:`设计页 </explanations/region_design/index_zh>`\ 把它称为语义的原因。

下面的脚本逐步打印对调模型的故障周期：``Motion`` 的 ``during`` 先执行，仍看到 ``permit = 1``\ ；``Safety`` 随后才改 ``permit``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for events in (None, ["/Start"], None):
       runtime.cycle(events)
   result = runtime.cycle([], inputs={"fault": 1}, trace=True)
   for entry in result.trace:
       print(entry.action_path, "permit =", entry.vars["permit"])

.. testoutput::

   Controller.Running.Motion.On::on_durings::0 permit = 1
   Controller.Running.Safety.Watching::on_durings::0 permit = 0


**这不能说明什么。**\ 区域读到的是轮到它时的值，而不是“周期开始时的值”。没有双缓冲。如果需要上一周期的快照，请在最先运行的区域里自己复制变量。

.. _region-semantics-completion-zh:

已完成、联合完成（joint completion）与停驻
------------------------------------------

**论断**\ ：区域内直接写的 ``X -> [*]`` 被执行时，区域完成，随后等待。已完成的区域不执行 ``during``\ 。最后一个区域完成的那个周期，立即续接拥有者自己的出边。如果续接无法提交，最后这次完成被拒绝，区域留在原来的叶子上。

.. literalinclude:: job_join.fcstm
   :language: fcstm
   :caption: ``job_join.fcstm``

``Job`` 有两个由事件结束的区域。``Job -> AwaitPermission`` 是拥有者的普通转换，没有条件。

**正常的联合完成。**\ 四个周期；``ADone`` 在周期 2 到达，``BDone`` 在周期 4 到达：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("job_join.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"proceed": 0})
   for events in (None, ["/ADone"], None, ["/BDone"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Workflow.Job{A: Working, B: Working} {'a': 1, 'b': 1, 'aexit': 0, 'w': 0, '__forced_0': 0}
   2 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 2, 'aexit': 1, 'w': 0, '__forced_0': 0}
   3 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 3, 'aexit': 1, 'w': 0, '__forced_0': 0}
   4 Workflow.AwaitPermission {'a': 1, 'b': 3, 'aexit': 1, 'w': 1, '__forced_0': 0}


* 周期 2：``ADone`` 使区域 ``A`` 完成。它的 ``exit`` 已执行（``'aexit': 1``\ ），配置显示 ``A: [done]``\ 。区域 ``B`` 继续工作（``'b': 2``\ ）。
* 周期 3：``A`` 已完成，不再运行（``'a'`` 与 ``'aexit'`` 都保持 1）；``B`` 工作（``'b': 3``\ ）。
* 周期 4：``BDone`` 使最后一个区域 ``B`` 完成。同一周期里拥有者执行 ``Job -> AwaitPermission``\ ，``AwaitPermission`` 执行 ``during``\ （``'w': 1``\ ）。机器从不停在“全体已完成”上。

**被拒绝的最后一次完成。**\ 在 ``job_rejected.fcstm`` 里，拥有者的出边是 ``Job -> Ready : if [proceed != 0]``\ ，其余都和上面一样。

.. literalinclude:: job_rejected.fcstm
   :language: fcstm
   :caption: ``job_rejected.fcstm``

脚本在周期 2 发送 ``ADone``\ ，在 ``proceed`` 为 0 的周期 3 发送 ``BDone``\ ，在 ``proceed`` 为 1 的周期 4 什么也不发送，在周期 5 带着 ``proceed`` 1 再次发送 ``BDone``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("job_rejected.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"proceed": 0})
   for events, proceed in ((None, 0), (["/ADone"], 0), (["/BDone"], 0), (None, 1), (["/BDone"], 1)):
       runtime.cycle(events, inputs={"proceed": proceed})
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Workflow.Job{A: Working, B: Working} {'a': 1, 'b': 1, 'aexit': 0, 'w': 0, '__forced_0': 0}
   2 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 2, 'aexit': 1, 'w': 0, '__forced_0': 0}
   3 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 3, 'aexit': 1, 'w': 0, '__forced_0': 0}
   4 Workflow.Job{A: [done], B: Working} {'a': 1, 'b': 4, 'aexit': 1, 'w': 0, '__forced_0': 0}
   5 Workflow.Ready {'a': 1, 'b': 4, 'aexit': 1, 'w': 0, '__forced_0': 0}


* 周期 3：``BDone`` 到了，但 ``proceed`` 为 0，拥有者出不去。这次完成整体被拒绝：``B`` 留在 ``Working``\ ，``during`` 照常执行（``'b': 3``\ ），事件也不会保留到下一周期。
* 周期 4：``proceed`` 为 1，但没有事件，什么也不会完成。
* 周期 5：``BDone`` 与 ``proceed`` 1 同时出现，``B`` 完成，拥有者续接到 ``Ready``\ 。

**逐层的完成。**\ 每一层嵌套都应用同一规则，外层的兄弟不能替内层拥有者提供停驻资格。在 ``nested_join.fcstm`` 里，内层的组 ``Q{A1, A2}`` 在周期 3 完成，它所在的区域 ``A`` 在同一周期经 ``Q -> R`` 续接，外层拥有者的区域 ``B`` 继续工作（``n`` 一直在计数）。内层拥有者不等 ``B``\ 。

.. literalinclude:: nested_join.fcstm
   :language: fcstm
   :caption: ``nested_join.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_join.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["/D1"], ["/D2"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: Q{A1: W1, A2: W2}, B: N} {'n': 1}
   2 Root.P{A: Q{A1: [done], A2: W2}, B: N} {'n': 2}
   3 Root.P{A: R, B: N} {'n': 3}
   4 Root.P{A: R, B: N} {'n': 4}


在 ``nested_rejected.fcstm`` 里，内层区域只有在它上面每一层的续接都能提交时才允许完成。``Inner -> [*]`` 需要 ``ok1``\ ，``P -> After`` 需要 ``ok2``\ 。

.. literalinclude:: nested_rejected.fcstm
   :language: fcstm
   :caption: ``nested_rejected.fcstm``

只有其中一个为真时（前两行）机器完全不动；两个都为真（最后一行）才落到 ``Root.After``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_rejected.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"ok1": 0, "ok2": 0})
   for ok1, ok2 in ((1, 0), (0, 1), (1, 1)):
       runtime.cycle(["/Finish"], inputs={"ok1": ok1, "ok2": ok2})
       print(runtime.cycle_count, "ok1", ok1, "ok2", ok2, runtime.configuration)

.. testoutput::

   1 ok1 1 ok2 0 Root.P{Outer: Inner{IR: W}}
   2 ok1 0 ok2 1 Root.P{Outer: Inner{IR: W}}
   3 ok1 1 ok2 1 Root.After


**规则为什么这么严。**\ 每条分支只能停在非伪状态的叶子或“已完成”上，活动的拥有者至少要有一个区域仍在工作。两条合在一起，就排除了“已经结束却还在那里”的拥有者。代价就是上面的拒绝：无处可去的完成不会发生。顺带一提：只有一个区域的拥有者与普通复合状态行为相同，区域完成时它即完成；根状态本身是拥有者时，最后一个区域完成就使机器结束。

**这不能说明什么。**\ 被拒绝的完成不是 Delta。周期照常提交，周期内的其他工作保留，只是完成这一步被丢弃。

整组启动
--------

**论断**\ ：进入拥有者就按书写顺序进入每个区域，各取第一个可能的入口。后面的区域找不到合法入口时，整次进入被拒绝；前面的区域不会重新选择。拥有者自己的 ``enter``\ 、``during before``\ 、``during after`` 与 ``exit`` 绕着整组各执行一次，不按区域计次。

.. literalinclude:: owner_actions.fcstm
   :language: fcstm
   :caption: ``owner_actions.fcstm``

``seq`` 用数字记录各块的先后：1 是拥有者的 ``enter``\ ，2 是它的 ``during before``\ ，3 是 ``during after``\ ，4 是 ``exit``\ ；5、6 是 ``A1`` 的 ``enter`` 与 ``exit``\ ，7、8 是 ``B1`` 的。周期 3 带着 ``/Stop``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("owner_actions.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, None, ["/Stop"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, "seq =", runtime.vars["seq"])

.. testoutput::

   1 Root.P{A: A1, B: B1} seq = 1257
   2 Root.P{A: A1, B: B1} seq = 1257
   3 Root.Off seq = 12576834


**拥有者的生命周期。**

* 周期 1：``P`` 的 ``enter``\ （数字 1）执行一次。区域 ``A`` 走初始转换，然后 ``P`` 的普通 ``during before``\ （数字 2）执行，最后才进入 ``A1``\ （数字 5）。拥有者的 ``during before`` 属于整组的初始化：在第一次初始转换之后、第一个真实状态进入之前执行一次。接着 ``B`` 启动（数字 7）。
* 周期 2：什么也不执行。叶子没有 ``during``\ ，也就没有 ``during`` 工作，而拥有者的 ``during before`` 与 ``during after`` 与这项工作绑定，没有工作的周期里两者都跳过。
* 周期 3：强制转换把整组带走。区域按书写顺序离开（``A1`` 是 6，``B1`` 是 8），拥有者的 ``during after``\ （3）在整组交还控制的已提交路径上执行，拥有者的 ``exit``\ （4）最后执行一次。

**不回头重选前面的区域。**\ ``group_entry.fcstm`` 的区域 ``R1`` 有两个初始候选（candidate）：``[*] -> A`` 写 ``k = 1``\ ，``[*] -> B`` 写 ``k = 2``\ 。区域 ``R2`` 只有在 ``k == 2`` 时才能启动。``R1`` 取第一个候选，``R2`` 启动不了，整组拒绝进入。机器不会回头试 ``R1`` 的第二个候选（那样 ``R2`` 就能启动）；而是丢弃转换 ``Idle -> P``\ ，运行下一个候选 ``Idle -> Fallback``\ 。输出只显示已提交的结果：``k`` 仍是 0，因为被拒绝的尝试什么也没留下。

.. literalinclude:: group_entry.fcstm
   :language: fcstm
   :caption: ``group_entry.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("group_entry.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["Root.Idle.Go"]):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.Idle {'k': 0}
   2 Root.Fallback {'k': 0}


**为什么不回头。**\ 在各区域入口的乘积里搜索，代价会随区域个数相乘，结果还取决于没有人写下来的搜索顺序。每个区域取第一个入口，代价与个数成正比，也容易写进模型的说法里：“按书写顺序，第一个可能的入口”。

.. _region-semantics-candidates-zh:

候选、回退与 Delta
------------------

**论断**\ ：进不去的转换让位给同一状态的下一个候选，并回到它的起点。本周期里前面区域的写入保留。如果整个周期无法得到合法配置，它成为 Delta，整个周期回滚。

.. literalinclude:: candidate_fallback.fcstm
   :language: fcstm
   :caption: ``candidate_fallback.fcstm``

周期 2 里 ``R1`` 写入 ``x = 2``\ 。随后 ``R2`` 尝试 ``B -> C``\ ，它会给 ``t`` 加 10，但 ``C`` 的初始转换要求 ``x > 100``\ ，``C`` 进不去。这个候选连同它的效果一起被丢弃，``B -> D`` 运行。

.. literalinclude:: initial_fallback.fcstm
   :language: fcstm
   :caption: ``initial_fallback.fcstm``

脚本把两个模型各运行两个周期：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("candidate_fallback", "initial_fallback"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for _ in range(2):
           runtime.cycle([])
           print(name, runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   candidate_fallback 1 Root.P{R1: A, R2: B} {'x': 1, 't': 0}
   candidate_fallback 2 Root.P{R1: A, R2: D} {'x': 2, 't': 1}
   initial_fallback 1 Root.P{R: Plain} {'g': 0, 'leak': 0, 'picked': 1}
   initial_fallback 2 Root.P{R: Plain} {'g': 0, 'leak': 0, 'picked': 1}


* ``candidate_fallback.fcstm``\ ：``t`` 是 1 而不是 11，因为被丢弃的候选没有留下效果；``x`` 是 2，因为 ``R1`` 本周期的写入没有被撤销。
* ``initial_fallback.fcstm``\ ：一个启动嵌套组、中途失败的初始候选同样被丢弃；``leak`` 保持 0（虽然它的 ``enter`` 本来会执行），第二个候选 ``Plain`` 被进入（``picked`` 为 1）。

在 ``group_delta.fcstm`` 里，只有输入 ``g`` 不为 0 时区域 ``R2`` 才能启动：

.. literalinclude:: group_delta.fcstm
   :language: fcstm
   :caption: ``group_delta.fcstm``

脚本把这个模型运行两次：``cold`` 从头开始，``hot`` 在 ``R1`` 处于 ``A``\ 、``R2`` 仍在等待初始化的位置开始（热启动，hot start）。以 ``Cycle`` 开头的几行是模拟器自己给出的 Delta 提示。提示写到标准错误，所以脚本用 ``flush=True`` 输出，让每条提示紧挨着它所属的那一行：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("group_delta.fcstm").read())
   cold = SimulationRuntime(model, input_source={"g": 0})
   hot = SimulationRuntime(
       model,
       input_source={"g": 0},
       initial_state="Root.P{R1: A, R2: [init]}",
       initial_vars={"n": 0},
   )
   for g in (0, 0, 1):
       for name, runtime in (("cold", cold), ("hot", hot)):
           result = runtime.cycle([], inputs={"g": g})
           print(name, runtime.cycle_count, "g =", g, runtime.configuration, end=" ", flush=True)
           print("n =", runtime.vars["n"], "delta =", result.delta, flush=True)

.. testoutput::

   Cycle 1 completed as Delta - State: Root; no stoppable successor was committed
   cold 1 g = 0 Root n = 0 delta = True
   Cycle 1 completed as Delta - State: Root.P{R1: A, R2: [init]}; no stoppable successor was committed
   hot 1 g = 0 Root.P{R1: A, R2: [init]} n = 0 delta = True
   Cycle 2 completed as Delta - State: Root; no stoppable successor was committed
   cold 2 g = 0 Root n = 0 delta = True
   Cycle 2 completed as Delta - State: Root.P{R1: A, R2: [init]}; no stoppable successor was committed
   hot 2 g = 0 Root.P{R1: A, R2: [init]} n = 0 delta = True
   cold 3 g = 1 Root.P{R1: A, R2: X} n = 1 delta = False
   hot 3 g = 1 Root.P{R1: A, R2: X} n = 1 delta = False


* 冷启动：``g`` 为 0 时区域 ``R2`` 无法初始化，机器根本进不了 ``P``\ 。这个周期是 Delta：配置仍是 ``Root``\ ，变量不变。周期 3 里 ``g`` 为 1，整组启动。
* ``R2`` 等待的热启动：这个周期初始化不了 ``R2``\ ，所以即使 ``R1`` 本可工作，整个周期仍是 Delta，``n`` 保持 0。只有能安放 ``R2`` 的周期才会提交 ``R1`` 的工作。

**为什么以周期为回滚单位。**\ 没有每个区域各自的事务。周期是别的工具能观察到的唯一单位（输入、输出、生成代码），所以它要么完整发生，要么完全不发生。周期里的各个候选在副本上试，第一个到达合法位置的获胜。

**界限。**\ 组可以在一个周期内互相重入。模拟器对一个周期内嵌套或重复超过 64 个组的链，给出有记载的错误。脚本先打印两个组互相嵌套的模型；\ ``nested_model`` 每多一个组，就把同样的 ``region R { ... state O { ... } }`` 再套一层。随后它启动 64 个组的链（能启动）和 65 个组的链：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError


   def nested_model(groups):
       body = "region R { [*] -> L; state L; }"
       for _ in range(groups - 1):
           body = "region R {\n[*] -> O;\nstate O {\n%s\n}\n}" % body
       return "state Root {\n[*] -> P;\nstate P {\n%s\n}\n}" % body


   print(nested_model(2))
   for groups in (64, 65):
       machine = load_state_machine_from_text(nested_model(groups))
       try:
           SimulationRuntime(machine).cycle([])
           print(groups, "groups inside one another start")
       except SimulationRuntimeDfsError as error:
           print(groups, "groups:", error)

.. testoutput::

   state Root {
   [*] -> P;
   state P {
   region R {
   [*] -> O;
   state O {
   region R { [*] -> L; state L; }
   }
   }
   }
   }
   64 groups inside one another start
   65 groups: Group initialization nested deeper than the structural safety limit (64) within one cycle; the state machine either enters more than 64 groups inside one another or one after another in the same cycle, or re-enters a group without bound.


.. _region-semantics-aspects-zh:

围绕区域的切面（aspect）
------------------------

**论断**\ ：拥有者及其祖先的 ``>> during before`` 与 ``>> during after`` 每个周期绕整组各执行一次；声明在区域内部的只绕该区域的分支。本周期没有 ``during`` 工作的范围，两者都不执行。before 与 after 成对嵌套。

.. literalinclude:: nested_aspects.fcstm
   :language: fcstm
   :caption: ``nested_aspects.fcstm``

每个 ``seq`` 数字标记一个块：1 与 9 是 ``P`` 的 ``before`` 与 ``after``\ ，2 与 8 是区域 ``A`` 的，3 与 7 是 ``Q`` 的，4、5、6 是 ``X1``\ 、``Y1``\ 、``B1`` 的 ``during``\ 。脚本打印两个周期之后的 ``seq``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("nested_aspects.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(2):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.vars["seq"])

.. testoutput::

   1 123457869
   2 123457869123457869


周期 1 追加数字 1 2 3 4 5 7 8 6 9，周期 2 再追加同样的九个数字，这就是各区域都在停驻的周期的顺序：最外层的 ``before`` 最先，然后是各内层，接着是 ``X1`` 与 ``Y1``\ （``Q`` 的分支）的 ``during``\ ，区域 ``A`` 的分支结束时依次是 ``Q`` 的 ``after``\ （7）与 ``A`` 的 ``after``\ （8），然后是区域 ``B``\ （6），最后 ``P`` 的 ``after``\ （9）只执行一次。区域 ``B`` 没有声明切面，所以 ``A`` 的 ``before``\ （2）不会出现在它周围。周期 1 在进入过程中显示同样的顺序。

**before 的位置。**\ 它紧贴在所属范围之下第一次 ``during`` 工作之前，排在先判断的分支的条件之后。

.. literalinclude:: aspect_position.fcstm
   :language: fcstm
   :caption: ``aspect_position.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("aspect_position.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(3):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{R1: S, R2: U} {'tick': 1, 'post': 1, 'own': 1}
   2 Root.P{R1: S, R2: V} {'tick': 2, 'post': 2, 'own': 2}
   3 Root.P{R1: T, R2: V} {'tick': 3, 'post': 3, 'own': 3}


周期 2 里，``R1`` 的条件 ``tick >= 2`` 先判断，看到的是 ``tick = 1``\ ，所以 ``R1`` 留在 ``S``\ ；然后根状态的 ``before`` 把 ``tick`` 变成 2，``P`` 的 ``before`` 执行；后判断的 ``R2`` 的条件看到 ``tick = 2``\ ，执行 ``U -> V``\ 。根状态的 ``after`` 在最后执行一次（``post``\ ）。``R1`` 在周期 3 跟上。

声明在区域里的切面只覆盖这个区域，并且只覆盖它的 ``during`` 工作：

.. literalinclude:: region_aspect.fcstm
   :language: fcstm
   :caption: ``region_aspect.fcstm``

脚本在周期 3 发送 ``/End1``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("region_aspect.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, None, ["/End1"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{R1: A, R2: B} {'r1': 1, 'r1after': 1, 'r2': 1, 'a': 1, 'b': 1}
   2 Root.P{R1: A, R2: B} {'r1': 2, 'r1after': 2, 'r2': 2, 'a': 2, 'b': 2}
   3 Root.P{R1: [done], R2: B} {'r1': 2, 'r1after': 2, 'r2': 3, 'a': 2, 'b': 3}
   4 Root.P{R1: [done], R2: B} {'r1': 2, 'r1after': 2, 'r2': 4, 'a': 2, 'b': 4}


``R1`` 的 ``before`` 与 ``after`` 在周期 1 与 2 里各执行一次（``r1`` 与 ``r1after`` 依次为 1、2），只绕 ``R1`` 的分支；``R2`` 自己的 ``before`` 每个周期都执行（``r2`` 为 1 到 4）。周期 3 里 ``R1`` 经 ``A -> [*]`` 完成，这不是 ``during`` 工作，所以它的切面不执行（``r1`` 保持 2）；此后只有 ``R2`` 的切面继续。

**这不能说明什么。**\ 通往停驻状态途中的伪状态不触发切面，与不含区域的模型相同。

.. _region-semantics-forced-zh:

触达区域的强制转换
------------------

**论断**\ ：源状态里含有区域的强制转换 ``!Owner -> Target``\ ，是在每个区域内部写普通 ``-> [*]`` 转换的简写。模拟器里没有“一次把整组带走”的特判。事件或条件由各个区域在轮到自己时判断，区域按书写顺序离开，最后一个已完成时拥有者经自己的转换续接。

``forced_condition.fcstm`` 里的模型带有 ``!P -> Off : if [x >= 2]``\ ：

.. literalinclude:: forced_condition.fcstm
   :language: fcstm
   :caption: ``forced_condition.fcstm``

实际运行的机器就是 ``to_ast_node()`` 打印的内容：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text

   model = load_state_machine_from_text(open("forced_condition.fcstm").read())
   print(model.to_ast_node())

.. testoutput::

   def int x = 0;
   def int __forced_0 = 0;
   state Root {
       state P {
           region A {
               state A1 {
                   during {
                       x = x + 1;
                   }
               }
               A1 -> [*] : if [__forced_0 == 1];
               A1 -> [*] : if [x >= 2] effect {
                   __forced_0 = 1;
               }
               [*] -> A1;
           }
           region B {
               state B1;
               B1 -> [*] : if [__forced_0 == 1];
               B1 -> [*] : if [x >= 2] effect {
                   __forced_0 = 1;
               }
               [*] -> B1;
           }
       }
       state Off;
       P -> Off : if [__forced_0 == 1] effect {
           __forced_0 = 0;
       }
       P -> Off : if [x >= 2 && __forced_0 == 0];
       [*] -> P;
   }


* 每个区域得到两条通往 ``[*]`` 的转换：一条\ **发起者**\ ，带声明的条件（``x >= 2``\ ），效果是把 ``__forced_0`` 置起；写在它前面的一条\ **跟随者**\ ，在变量已置起时触发。
* 拥有者得到两条通往 ``Off`` 的转换：一条等待已置起的变量并把它清除，这是整组结束之后的情形；写在它后面的是声明的那条转换，留给控制权回到拥有者而变量并未置起的情形。

运行它，能看到三个后果。\ **条件在各区域轮到时判断。**

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("forced_condition.fcstm").read())
   runtime = SimulationRuntime(model)
   for _ in range(3):
       runtime.cycle([])
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: A1, B: B1} {'x': 1, '__forced_0': 0}
   2 Root.P{A: A1, B: [done]} {'x': 2, '__forced_0': 1}
   3 Root.Off {'x': 2, '__forced_0': 0}


周期 2 里，``A`` 的 ``during`` 在 ``A`` 轮完之\ *后*\ 才把 ``x`` 变成 2，所以 ``A`` 继续工作。排在后面的 ``B`` 在轮到自己时看到 ``x >= 2``\ ，立即完成（``B: [done]``\ ，``__forced_0`` 为 1）。``A`` 在周期 3 看到已置起的变量时完成，拥有者在同一周期离开。条件由每个区域在自己的轮次判断，所以 ``A`` 与 ``B`` 在同一个周期里结果不同。

**区域按书写顺序离开。**\ 下面的脚本让控制器运行到两个区域都在工作，发送 ``/Stop``\ ，并打印被退出的状态：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for events in (None, ["/Start"], None):
       runtime.cycle(events)
   result = runtime.cycle(["/Stop"], trace=True)
   for entry in result.trace:
       if entry.kind == "state_exit":
           print(".".join(entry.state_path))

.. testoutput::

   Controller.Running.Safety.Watching
   Controller.Running.Motion.On
   Controller.Running


先是 ``Safety`` 离开，然后 ``Motion``\ ，最后拥有者。``forced_nested.fcstm`` 里的拥有者是嵌套的：

.. literalinclude:: forced_nested.fcstm
   :language: fcstm
   :caption: ``forced_nested.fcstm``

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("forced_nested.fcstm").read())
   runtime = SimulationRuntime(model)
   runtime.cycle([])
   for entry in runtime.cycle(["Root.Halt"], trace=True).trace:
       if entry.kind == "state_exit":
           print(".".join(entry.state_path))

.. testoutput::

   Root.Outer.R1.Inner.X.X1
   Root.Outer.R1.Inner.Y.Y1
   Root.Outer.R1.Inner
   Root.Outer.R2.Z1
   Root.Outer


``X1`` 与 ``Y1`` 离开，然后是它们的拥有者 ``Inner``\ ，再是下一个区域的 ``Z1``\ ，最后 ``Outer``\ 。嵌套的拥有者在自己的区域之后立即离开，已完成区域的 ``exit`` 不会执行两次。

**变量是普通变量。**\ ``__forced_0`` 只在整组离开的过程中被置起：上面的周期 2 之后它是 1，拥有者一离开又回到 0。它在 ``runtime.vars`` 里可见。

**目标进不去的时候。**

.. literalinclude:: forced_blocked.fcstm
   :language: fcstm
   :caption: ``forced_blocked.fcstm``

在 ``forced_two_declarations.fcstm`` 里两条声明相互竞争：

.. literalinclude:: forced_two_declarations.fcstm
   :language: fcstm
   :caption: ``forced_two_declarations.fcstm``

脚本在两个模型的周期 2 与周期 4 发送 ``/Stop``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   for name in ("forced_blocked", "forced_two_declarations"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model)
       for events in (None, ["Root.Stop"], None, ["Root.Stop"]):
           runtime.cycle(events)
           print(name, runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   forced_blocked 1 Root.P{A: A1, B: B1} {'seq': 1, '__forced_0': 0}
   forced_blocked 2 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_blocked 3 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_blocked 4 Root.P{A: [done], B: B1} {'seq': 18, '__forced_0': 1}
   forced_two_declarations 1 Root.P{A: A1, B: B1} {'never': 0, '__forced_0': 0, '__forced_1': 0}
   forced_two_declarations 2 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}
   forced_two_declarations 3 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}
   forced_two_declarations 4 Root.P{A: [done], B: B1} {'never': 0, '__forced_0': 1, '__forced_1': 0}


``!P -> Blocked`` 无法完成，因为 ``Blocked`` 的初始转换的条件永远不成立。``A`` 在周期 2 完成，它的 ``exit`` 已执行（``'seq': 18``\ ），但最后一个区域 ``B`` 带着已置起的变量继续工作（``'__forced_0': 1``\ ）；配置 ``P{A: [done], B: B1}`` 停驻，第二次 ``/Stop`` 之后也是如此。整组在目标第一次可以进入的周期离开。普通的 ``P -> Other : /Stop`` 不会被执行：它要求整组先完成。只要目标进不去，这个变量就一直保持置起。

在 ``forced_two_declarations.fcstm`` 里，先被置起的那条声明占住整组，第二条在此期间不被尝试。在不含区域的模型里，目标进不去时由下一条声明接手；这一差别是只用普通转换展开的后果，也是已知的差距（见\ `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_\ ）。

**它是简写，行为与它的展开式一致。**\ 实际运行的模型与由它导出的文本重新加载的模型，周期完全一致。脚本先打印两个模型各自标记的隐藏变量，再打印书写的模型的最后一个周期，以及五个周期在两个模型里是否完全相同：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   written = load_state_machine_from_text(open("controller.fcstm").read())
   reloaded = load_state_machine_from_text(str(written.to_ast_node()))
   print(written.forced_variables, reloaded.forced_variables)


   def run(model):
       runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
       history = []
       for events in (None, ["/Start"], None, None, ["/Stop"]):
           runtime.cycle(events)
           history.append((str(runtime.configuration), dict(runtime.vars)))
       return history


   first, second = run(written), run(reloaded)
   print(first[-1], first == second)

.. testoutput::

   ('__forced_0',) ()
   ('Controller.Idle', {'permit': 1, 'motor': 0, '__forced_0': 0}) True


导出的文本加载出的机器里 ``__forced_0`` 是普通变量，没有任何东西再把它标成强制（空元组）。两台机器每个周期的配置与变量都相同。热启动、生成的运行时、有界模型检查与验证流水线也是如此：它们取实际运行的机器。图与 ``pyfcstm inspect`` 的报告则按书写的模型呈现，因为它们描述的是你写了什么。

**这不能说明什么。**\ 展开式并不复现其他工具的每个细节，上面提到的那一处已知缺口（issue #591）仍未解决。比较见\ :doc:`/explanations/region_design/index_zh`\ ，遗留事项见\ :ref:`region-semantics-limits-zh`\ 。

.. _region-semantics-active-zh:

``active()`` 与区域的顺序
-------------------------

**论断**\ ：``active("路径")`` 从该状态 ``enter`` 开始起为真，到它的 ``exit`` 执行完为止。转换的 ``effect`` 期间，源状态与目标状态都不是活动的。本周期里轮到更靠后的区域能立即看到变化；更靠前的区域在下一周期才看到。

.. literalinclude:: active_query.fcstm
   :language: fcstm
   :caption: ``active_query.fcstm``

``active_query_swapped.fcstm`` 是同一个模型，只是 ``Motion`` 写在 ``Safety`` 之前：

.. literalinclude:: active_query_swapped.fcstm
   :language: fcstm
   :caption: ``active_query_swapped.fcstm``

六个变量记录 ``active()`` 在六个位置的回答：``exit_self`` 与 ``exit_other`` 在 ``Normal`` 的 ``exit`` 里，``effect_source`` 与 ``effect_target`` 在转换的 ``effect`` 里，``enter_self`` 与 ``enter_other`` 在 ``Tripped`` 的 ``enter`` 里。值 1 表示活动，2 表示不活动。脚本在周期 2 把 ``fault`` 置 1，打印每个周期的配置与 ``m``\ ，最后打印这六个变量：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   probes = ("exit_self", "exit_other", "effect_source", "effect_target", "enter_self", "enter_other")
   for name in ("active_query", "active_query_swapped"):
       model = load_state_machine_from_text(open(name + ".fcstm").read())
       runtime = SimulationRuntime(model, input_source={"fault": 0})
       for fault in (0, 1, 1):
           runtime.cycle([], inputs={"fault": fault})
           print(name, runtime.cycle_count, runtime.configuration, "m =", runtime.vars["m"])
       print({probe: runtime.vars[probe] for probe in probes})

.. testoutput::

   active_query 1 Root.P{Safety: Normal, Motion: Run} m = 1
   active_query 2 Root.P{Safety: Tripped, Motion: Stop} m = 1
   active_query 3 Root.P{Safety: Tripped, Motion: Stop} m = 1
   {'exit_self': 1, 'exit_other': 2, 'effect_source': 2, 'effect_target': 2, 'enter_self': 1, 'enter_other': 2}
   active_query_swapped 1 Root.P{Motion: Run, Safety: Normal} m = 1
   active_query_swapped 2 Root.P{Motion: Run, Safety: Tripped} m = 2
   active_query_swapped 3 Root.P{Motion: Stop, Safety: Tripped} m = 2
   {'exit_self': 1, 'exit_other': 2, 'effect_source': 2, 'effect_target': 2, 'enter_self': 1, 'enter_other': 2}


* ``exit_self`` 为 1，``exit_other`` 为 2：在 ``Normal`` 的 ``exit`` 里，``Normal`` 仍然活动，``Tripped`` 还不是。
* ``effect_source`` 为 2，``effect_target`` 为 2：效果执行期间，机器已离开 ``Normal`` 而尚未进入 ``Tripped``\ 。
* ``enter_self`` 为 1，``enter_other`` 为 2：在 ``Tripped`` 的 ``enter`` 里，``Tripped`` 活动而 ``Normal`` 不活动。
* ``Safety`` 在前（第一个模型）时，``Motion`` 在 ``Tripped`` 被进入的那个周期就看到它并立即停下（``m`` 保持 1）。``Motion`` 在前（对调模型）时，``Motion`` 多运行一个周期（``m`` 为 2），下一周期才停。与变量同样是慢一拍。

**它是怎么工作的。**\ ``active()`` 是普通标志变量的简写：

.. literalinclude:: active_lowering.fcstm
   :language: fcstm
   :caption: ``active_lowering.fcstm``

脚本打印实际运行的机器，以及 ``StateMachine.active_variables`` 为一个位置算出的标志：

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text

   model = load_state_machine_from_text(open("active_lowering.fcstm").read())
   print(model.to_ast_node())
   print(model.active_variables(Configuration.parse(model, "Root.P{A: A2, B: B1}")))

.. testoutput::

   def int __active_Root_P_A_A2 = 0;
   state Root {
       state P {
           region A {
               state A1 {
                   event Go;
               }
               state A2 {
                   enter {
                       __active_Root_P_A_A2 = 1;
                   }
                   exit {
                       __active_Root_P_A_A2 = 0;
                   }
               }
               [*] -> A1;
               A1 -> A2 :: Go;
           }
           region B {
               state B1;
               state B2;
               [*] -> B1;
               B1 -> B2 : if [__active_Root_P_A_A2 != 0];
           }
       }
       [*] -> P;
   }
   {'__active_Root_P_A_A2': 1}


实际运行的模型为每个被查询的状态加一个隐藏的 ``int`` 变量。标志在 ``enter`` 的第一行置 1、在 ``exit`` 的最后一行清 0，这正是 ``enter`` 与 ``exit`` 块位于“活动”区间两端的原因。被查询的状态不能是区域，写区域会在构建模型时报错。周期 2 里 ``Go`` 把区域 ``A`` 带到 ``A2``\ ，区域 ``B`` 读到了区域 ``A`` 在同一周期置起的标志：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("active_lowering.fcstm").read())
   runtime = SimulationRuntime(model)
   for events in (None, ["Root.P.A.A1.Go"], None):
       runtime.cycle(events)
       print(runtime.cycle_count, runtime.configuration, dict(runtime.vars))

.. testoutput::

   1 Root.P{A: A1, B: B1} {'__active_Root_P_A_A2': 0}
   2 Root.P{A: A2, B: B2} {'__active_Root_P_A_A2': 1}
   3 Root.P{A: A2, B: B2} {'__active_Root_P_A_A2': 1}


标志在所有环节都是普通变量：热启动要像提供其他变量一样提供它，运行时不推导它，也不校验它与位置是否一致；需要按位置算出它的值时，调用 ``StateMachine.active_variables(config)``\ 。

配置是一棵树
------------

**论断**\ ：含区域的机器的位置是一棵树，有一种可以读回同一个值的短文本形式。所有模型都有 ``runtime.configuration``\ ；``runtime.current_state`` 在不含区域的模型上是 ``State``\ ，在含区域的模型上是配置对象。

脚本解析控制器的四段文本，打印每个结果，或者拒绝它的错误：

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text

   model = load_state_machine_from_text(open("controller.fcstm").read())
   for text, mode in [
       ("Controller.Running{Safety: [done], Motion: On}", "stable"),
       ("Controller.Running{Safety: [init], Motion: [init]}", "initialization"),
       ("Controller.Running", "stable"),
       ("Controller.Running{Safety: [done], Motion: [done]}", "stable"),
   ]:
       try:
           config = Configuration.parse(model, text, mode=mode)
       except ValueError as error:
           print("ValueError:", error)
       else:
           print(repr(config), [".".join(state.path) for state in config.leaves])

.. testoutput::

   Configuration(mode='stable', position='Controller.Running{Safety: [done], Motion: On}') ['Controller.Running.Motion.On']
   Configuration(mode='initialization', position='Controller.Running{Safety: [init], Motion: [init]}') []
   ValueError: Missing region in stable configuration for 'Controller.Running'.
   ValueError: All regions are Done at 'Controller.Running'.


* 状态写成完整的点路径。拥有者后面跟 ``{区域: 位置, ...}``\ ，按书写顺序。位置本身也可以是带花括号的拥有者，文本跟着树走。
* ``[done]`` 是已完成的区域，``[init]`` 是尚未进入的区域。``leaves`` 列出承担 ``during`` 工作的状态：已完成的区域没有。
* 三种模式说明一段文本可以描述什么：``stable`` 是机器可以停驻的位置；``initialization`` 是整个尚未启动的拥有者；``transient`` 还允许伪状态与启动到一半的组，这是处理器在周期中途看到的。稳定位置必须列出每个区域，也不能所有区域都已完成，上面的两个错误就是例子。
* ``str(config)`` 是文本；``repr(config)`` 还显示模式。

运行时用同样的方式报告它的位置，下面是第一个周期之前与之后：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   print(repr(runtime.configuration))
   runtime.cycle([])
   print(repr(runtime.configuration), type(runtime.current_state).__name__)

.. testoutput::

   Configuration(mode='initialization', position='Controller')
   Configuration(mode='stable', position='Controller.Idle') Configuration


热启动
------

**论断**\ ：热启动把文本写到的部分就位，其余部分留到第一个周期按书写顺序初始化。已就位的部分不会再次进入。

脚本用四段不同的文本启动控制器，运行一个周期，打印之后的配置以及这个周期进入过的状态：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("controller.fcstm").read())
   variables = {"permit": 1, "motor": 0, "__forced_0": 0}
   for text in (
       "Controller.Running{Safety: Watching, Motion: Off}",
       "Controller.Running{Safety: [done], Motion: On}",
       "Controller.Running.Motion.On",
       "Controller.Running",
   ):
       runtime = SimulationRuntime(
           model,
           initial_state=text,
           initial_vars=variables,
           input_source={"fault": 0, "requested": 1},
       )
       result = runtime.cycle([], trace=True)
       entered = [".".join(e.state_path) for e in result.trace if e.kind == "state_enter"]
       print(text, "->", runtime.configuration, entered)

.. testoutput::

   Controller.Running{Safety: Watching, Motion: Off} -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Motion.On']
   Controller.Running{Safety: [done], Motion: On} -> Controller.Running{Safety: [done], Motion: On} []
   Controller.Running.Motion.On -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Safety.Watching']
   Controller.Running -> Controller.Running{Safety: Watching, Motion: Off} ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']


* **每个叶子都写了。**\ ``Safety`` 与 ``Motion`` 都已就位，这个周期不会再次进入 ``Watching`` 或 ``Off``\ 。区域只是在工作：``Motion`` 因为 ``permit`` 给的是 1 而执行 ``Off -> On``\ ，进入的只有 ``On``\ 。
* **一个区域已完成。**\ ``Safety: [done]`` 保持完成、什么也不做，只有 ``Motion`` 在工作，没有任何状态被进入。
* **进入区域的路径**\ （``Controller.Running.Motion.On``\ ）。另一个区域处于等待（``Safety: [init]``\ ）。这个周期里 ``Safety`` 走初始转换并进入 ``Watching``\ ，按书写顺序排在 ``Motion`` 的 ``during`` 之前。路径只保留它经过的那条分支。
* **只写拥有者。**\ 整组作为一个整体等待，两个区域按书写顺序初始化，先 ``Safety`` 后 ``Motion``\ ；对照前面各节里进入 ``Running`` 的轨迹。

命令行里同样的文本也可用：

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; \
   cycle --input fault=1 --input requested=1"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialized from state: Controller.Running{Safety: Watching, Motion: On}
   Cycle: 0
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

拒绝同样成立。\ **所有区域已完成**\ 以 ``All regions are Done`` 拒绝，任何嵌套深度都是如此：已完成的拥有者没有地方可以停驻。\ **缺少变量**\ 同样被拒绝。``__forced_0`` 这样的隐藏变量是普通变量，由调用方与其他变量一起提供；不会从位置推导。两条命令都以状态码 ``1`` 退出：

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=1 __forced_0=0"
   ...
   Initialization failed: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm -e "init Controller.Running{Safety: Watching, Motion: Off} permit=1 motor=0"
   ...
   Error: All variables must be provided. Missing: ['__forced_0']
   Available variables: ['__forced_0', 'motor', 'permit']
   $ echo $?
   1

等待中的区域到不了合法位置时，该周期是 Delta，见上一节关于候选的内容。``initial_state`` 还接受 ``Configuration`` 对象、元组路径，以及不含区域的模型的 ``State``\ ；热启动不等价于从冷启动重放历史，因为没有任何 ``enter`` 运行过。

外部事件名
----------

**论断**\ ：完整路径与从根开始的写法，在机器停在哪里都含义相同。依赖位置的名字对每个活动叶子各解析一次，结果只有三种：“都找不到”“同一个事件”“不同的事件”。裸名字从不向上查找。

.. literalinclude:: /_models/event_names.fcstm
   :language: fcstm
   :caption: ``event_names.fcstm``

脚本让两个区域都在工作的机器逐个发送这些名字，每个名字各占一个周期，最后在 ``Safety`` 已完成时发送 ``Ping``\ ：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(open("event_names.fcstm").read())
   both = "Controller.Running{Safety: Watching, Motion: Off}"
   one_done = "Controller.Running{Safety: [done], Motion: Off}"
   names = ["Go", "Trip", "Ping", "Stop", "Reset", "..Stop", "/Running.Stop", "Controller.Running.Motion.Off.Ping"]
   for name, start in [(name, both) for name in names] + [("Ping", one_done)]:
       runtime = SimulationRuntime(model, initial_state=start, initial_vars={"trail": 0})
       try:
           result = runtime.cycle([name])
       except ValueError as error:
           print(name, "refused:", error)
       else:
           print(name, "->", runtime.configuration, list(result.consumed_events))

.. testoutput::

   Go -> Controller.Running{Safety: Watching, Motion: On} ['Controller.Running.Motion.Off.Go']
   Trip -> Controller.Running{Safety: Tripped, Motion: Off} ['Controller.Running.Safety.Watching.Trip']
   Ping refused: Position-dependent event name 'Ping' is ambiguous: Controller.Running.Safety.Watching.Ping (from Controller.Running.Safety.Watching); Controller.Running.Motion.Off.Ping (from Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   Stop refused: Position-dependent event name 'Stop' matches no event from any active leaf (Controller.Running.Safety.Watching, Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   Reset refused: Position-dependent event name 'Reset' matches no event from any active leaf (Controller.Running.Safety.Watching, Controller.Running.Motion.Off); use the full event path or a root-based "/path".
   ..Stop -> Controller.Running{Safety: Tripped, Motion: On} ['Controller.Running.Stop', 'Controller.Running.Stop']
   /Running.Stop -> Controller.Running{Safety: Tripped, Motion: On} ['Controller.Running.Stop', 'Controller.Running.Stop']
   Controller.Running.Motion.Off.Ping -> Controller.Running{Safety: Watching, Motion: Off} ['Controller.Running.Motion.Off.Ping']
   Ping -> Controller.Running{Safety: [done], Motion: Off} ['Controller.Running.Motion.Off.Ping']


* ``Go`` 只存在于 ``Motion`` 的叶子之下，所以只有那个叶子找到它，事件被采用。``Trip`` 对 ``Safety`` 同理。
* ``Ping`` 在两个叶子上都有，含义不同。该周期被拒绝，信息列出每个候选及引出它的叶子；什么都不会运行。修正办法是写完整路径（``Controller.Running.Motion.Off.Ping``\ ）。
* ``Stop`` 是拥有者 ``Running`` 的事件，``Reset`` 是根的事件。裸名字只在每个活动叶子自己的名字空间里查找，所以两者都找不到。这与不含区域的模型一直遵守的规则相同。
* ``..Stop`` 从每个叶子向上数层，两个叶子都到达拥有者的同一个事件，于是事件被采用，两个区域都动。``/Running.Stop`` 与完整路径从任何位置都能到达它。事件在被消耗的列表里出现两次，每次对应它推动的一次转换。
* ``Safety`` 已完成时（最后一行）只剩一个活动叶子，``Ping`` 不再有歧义：已完成的区域与等待初始化的区域不参与解析。

**为什么不广播。**\ 不同位置上的同名事件是不同的事件。把它们合在一起，模型的行为就取决于碰巧哪些区域活动；区域一完成，模型的含义就变了。每个叶子解析一次、有歧义就失败，让选择始终摆在写作者面前。

处理器上下文
------------

**论断**\ ：抽象处理器会被告知它在哪里运行，以及此刻机器是什么样子。``state_path`` 与 ``active_leaf`` 取该动作所包住范围内最深的公共状态：只包住一条分支时是这条分支的叶子，包住整组时是拥有者。``configuration`` 是调用那一刻的完整位置。

.. literalinclude:: handler_context.fcstm
   :language: fcstm
   :caption: ``handler_context.fcstm``

脚本为每个抽象动作注册一个处理器，它打印动作名、``state_path``\ 、``active_leaf`` 与 ``configuration``\ ，然后运行三个周期：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   def report(name):
       def handler(context):
           print(name, ".".join(context.state_path), ".".join(context.active_leaf), context.configuration)
       return handler

   model = load_state_machine_from_text(open("handler_context.fcstm").read())
   runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 1})
   for action in ("Controller.Tick", "Controller.Running.GroupPre", "Controller.Running.Safety.SafetyPre", "Controller.Running.Safety.Normal.Watch", "Controller.Running.Motion.On.Drive"):
       runtime.register_abstract_handler(action, report(action.split(".")[-1]))
   for events in (None, ["/Start"], None):
       print("cycle", runtime.cycle_count + 1)
       runtime.cycle(events)

.. testoutput::

   cycle 1
   Tick Controller.Idle Controller.Idle Controller.Idle
   cycle 2
   Tick Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: [init]}
   GroupPre Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: [init]}
   SafetyPre Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: [init]}
   Watch Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: [init]}
   cycle 3
   Tick Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: Off}
   GroupPre Controller.Running Controller.Running Controller.Running{Safety: Normal, Motion: Off}
   SafetyPre Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: Off}
   Watch Controller.Running.Safety.Normal Controller.Running.Safety.Normal Controller.Running{Safety: Normal, Motion: Off}
   Drive Controller.Running.Motion.On Controller.Running.Motion.On Controller.Running{Safety: Normal, Motion: On}


* ``Tick`` 声明在根上，包住整台机器：在 ``Idle`` 里报告 ``Idle``\ ；在 ``Running`` 里（周期 2 与 3）报告拥有者 ``Running``\ ，因为它包住两个区域。
* ``SafetyPre`` 属于区域 ``Safety``\ ，只包住这条分支，所以报告叶子 ``Running.Safety.Normal``\ 。``Watch`` 是叶子自己的动作。
* 周期 2 里拥有者正在被进入。``Motion`` 还没有启动，所以配置显示 ``Motion: [init]``\ ，而 ``Safety`` 已经在 ``Normal``\ 。周期 3 里 ``Drive`` 看到 ``Motion: On``\ ，因为 ``Motion`` 在同一周期更早已执行 ``Off -> On``\ 。

候选提交之前的试探不调用任何处理器，只有已提交的路径才会调用。

.. _region-semantics-evidence-zh:

证据：哪些用例证明什么
----------------------

语义用例是共享的数据文件，模拟器、生成的 Python 运行时，以及在用例允许时生成的 C 系运行时和有界模型检查器都会运行它们。名字以 ``region_`` 开头的 118 个用例按主题归组如下。表按用例名前缀和一个代表性标题列出各族；不逐条列断言，这样页面不会随用例增加而失效。

.. list-table:: 区域用例族
   :header-rows: 1
   :widths: 24 8 34 34

   * - 族（用例名前缀）
     - 数量
     - 证明什么
     - 小节
   * - ``region_controller_*``\ 、``region_later_*``\ 、``region_earlier_*``\ 、``region_multiple_writers_*``\ 、``region_inputs_*``\ 、``region_parallel_leaves_*``\ 、``region_same_external_*``
     - 8
     - 两种顺序的交锁、正向与反向读取、最后写入生效、所有区域共用一份输入采样。
     - :ref:`region-semantics-one-cycle-zh`\ 、\ :ref:`region-semantics-visibility-zh`
   * - ``region_done_*``\ 、``region_last_*``\ 、``region_indirect_*``\ 、``region_inner_group_*``\ 、``region_completion_*``\ 、``region_nested_group_*``\ 、``region_parallel_root_*``\ 、``region_groups_chained_*``\ 、``region_single_*``
     - 11
     - 已完成的区域、联合完成、被拒绝的最后一次完成、经复合状态与嵌套拥有者的完成、单个区域等同于普通复合状态。
     - :ref:`region-semantics-completion-zh`
   * - ``region_group_entry_*``\ 、``region_group_exit_*``\ 、``region_group_preemption_*``\ 、``region_group_reentry_*``\ 、``region_owner_*``\ 、``region_owners_*``\ 、``region_reentry_*``\ 、``region_three_nested_*``\ 、``region_group_reentered_*``\ 、``region_group_whose_*``\ 、``region_root_group_*``\ 、``region_that_finishes_*``
     - 21
     - 按书写顺序进入且不回头、拥有者的 ``enter`` 与 ``exit`` 各一次、普通 ``during before`` 与 ``during after``\ 、重新进入时区域复位而变量保留、嵌套组深度优先启动。
     - 整组启动
   * - ``region_candidate_*``\ 、``region_cold_start_*``\ 、``region_cycle_that_*``\ 、``region_initial_candidate_*``\ 、``region_unreachable_*``\ 、``region_looping_*``\ 、``region_loop_*``\ 、``region_unbounded_*``\ 、``region_group_that_could_*``\ 、``region_reentering_*``\ 、``region_start_with_*``
     - 14
     - 回退到下一个候选、被拒绝的进入的回滚、整周期 Delta、回路与安全上限。
     - :ref:`region-semantics-candidates-zh`
   * - ``region_after_*``\ 、``region_ancestor_*``\ 、``region_aspect_*``\ 、``region_aspects_*``\ 、``region_pseudo_states_*``
     - 7
     - 切面的次数与位置、before 与 after 的嵌套、区域的切面只绕该区域。
     - :ref:`region-semantics-aspects-zh`
   * - ``region_forced_*``
     - 16
     - 来自拥有者、区域与祖先的强制转换、通配形式、条件在中途成立、目标进不去、相互竞争的声明。
     - :ref:`region-semantics-forced-zh`
   * - ``region_active_*``
     - 3
     - ``enter``\ 、``exit`` 与 ``effect`` 里的 ``active()``\ ，后面的区域，以及整组被带走之后。
     - :ref:`region-semantics-active-zh`
   * - ``region_hot_start_*``
     - 17
     - 写出每个叶子、已完成的区域、进入区域的路径或只写拥有者的启动，等待与已完成的区域、嵌套拥有者、被拒绝的位置、隐藏变量的提供。
     - 热启动
   * - ``region_event_name_*``\ 、``region_scoped_*``
     - 8
     - 依赖位置的名字的三种结果、已完成区域不参与解析、事件归属于各自的区域。
     - 外部事件名
   * - ``region_abstract_*``\ 、``region_leaf_abstract_*``\ 、``region_transient_*``\ 、``region_pseudo_state_enter_*``
     - 4
     - 处理器上下文，以及进入与完成过程中的瞬时配置文本。
     - 处理器上下文
   * - ``region_actions_*``\ 、``region_history_*``\ 、``region_dead_*``\ 、``region_declared_*``\ 、``region_entry_*``\ 、``region_rejected_*``\ 、``region_choice_*``\ 、``region_combo_*``
     - 9
     - 区域动作里的临时变量与 ``if`` 块、区域内复合状态的历史、伪状态与组合转换，以及不留痕迹的被拒候选。
     - 候选各节与上面各节

一个用例可以同时支撑多个小节，表里给的是主要的一个。有些用例族虽在 ``region_`` 名字空间下，却属于有界模型检查、生成的运行时或编辑器，在它们各自的页面里说明。

.. _region-semantics-limits-zh:

界限
----

* **嵌套。**\ 一个周期最多启动 64 个互相嵌套或先后相接的组。错误是 ``SimulationRuntimeDfsError``\ （输出见候选一节）。它用来制止无界的重入，不是建模预算。
* **没有广播，没有队列。**\ 事件是周期的输入。区域不能向另一个区域发送事件，同一周期的后续步骤里也不会投递任何东西。请用变量。
* **不能在区域之间跳转。**\ 转换不能从一个区域离开去另一个区域的状态，也不能从拥有者外面进入区域里的状态。转换以拥有者为终点，由拥有者启动每个区域。
* **拥有者的历史。**\ 含区域的拥有者不能声明历史。区域内部的复合状态的历史可以工作（见历史相关的用例族）。
* **强制转换。**\ 与不含区域的模型的差异（目标进不去时改为计入下一条声明）见\ :ref:`region-semantics-forced-zh`\ 。展开会给模型增加一个隐藏变量。
* **与其他工具的比较**\ （Stateflow 用户会注意到什么，以及实测的差距）见\ :doc:`设计页 </explanations/region_design/index_zh>`\ 。
* **已知的差距与模型的限制**\ 汇集在\ :doc:`/reference/region_model/index_zh`\ 的 “界限与已知差距”一节。
