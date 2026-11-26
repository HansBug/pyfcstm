.. _sec-how-to-simulation-zh:

仿真任务指南
============

当你已经有一个 FCSTM 模型，并且需要完成具体仿真任务时，使用本页。第一次引导式运行见
:doc:`../../tutorials/simulation/index_zh`；执行顺序推理见
:doc:`../../explanations/execution_semantics/index_zh`；精确命令形式、设置、导出格式和 Python 应用程序接口边界见
:doc:`../../reference/simulation/index_zh`。

术语说明：批处理模式（batch mode）、交互命令行（interactive command line）、热启动（hot start）和抽象处理器（abstract handler）在本页首次交接后，后文只使用中文术语。

快速命令提醒
------------

本节只是任务提醒，完整查阅表在 :doc:`../../reference/simulation/index_zh`。

``pyfcstm simulate`` 当前暴露的 命令行接口很小：

.. list-table:: ``pyfcstm simulate`` 选项
   :header-rows: 1

   * - 选项
     - 含义
   * - ``-i`` / ``--input-code TEXT``
     - 入口 FCSTM 文件；必填。
   * - ``-e`` / ``--execute TEXT``
     - 执行分号分隔的批处理命令，而不是启动交互命令行。
   * - ``--no-color``
     - 禁用命令输出中的 ANSI 颜色。
   * - ``-h`` / ``--help``
     - 显示命令行帮助文本。

批处理字符串和交互命令行共享同一组命令名。最常用的命令如下：

.. list-table:: 仿真器命令
   :header-rows: 1

   * - 命令
     - 用途
   * - ``cycle [count] [events...]``
     - 执行一个或多个周期。省略 ``count`` 时执行一个周期；``cycle Start`` 这类事件名会传入该周期。
   * - ``current``
     - 显示当前周期、当前状态和持久变量。
   * - ``events``
     - 显示当前状态可用的事件。
   * - ``history [n|all]``
     - 显示最近历史行或全部保留历史。
   * - ``init <position> [var=value...]``
     - 使用显式变量在某个状态（含并行区域的模型也可以是配置（configuration）文本）热启动并重建运行时。
   * - ``setting [key] [value]``
     - 查看或修改显示、历史、日志设置。
   * - ``export <path>``
     - 导出历史；格式由文件扩展名推断。
   * - ``clear``
     - 使用当前设置重置运行时。
   * - ``help``
     - 显示命令帮助。
   * - ``quit`` / ``exit``
     - 离开交互命令行。

运行批处理命令
--------------

当你需要在 CI、文档或错误报告中得到可复现转录时，使用 ``-e``。命令之间用分号分隔：

将 :download:`controller.fcstm </_models/controller.fcstm>` 下载到一个空目录，然后运行：

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   cycle --input fault=0 --input requested=0; \
   events; \
   cycle /Start --input fault=0 --input requested=0; \
   history 2"
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
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Controller.Start

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
   >>> history 2
   ────────────────────────────────────────────────────────────
    Cycle                        State                        Delta  __forced_0  motor  permit
   --------------------------------------------------------------------------------------------
      1                     Controller.Idle                   False      0         0      0
      2    Controller.Running{Safety: Watching, Motion: Off}  False      0         0      1

每个真正执行的周期都需要完整的输入向量，所以每条 ``cycle`` 都带 ``--input``；``events`` 列出活动叶子可以响应的事件。

使用交互命令行
--------------

省略 ``-e`` 即可启动交互命令行。交互会话无法由文档检查重放，所以这条命令只展示、不运行。请下载后面几节使用的模型 :download:`simple_machine.fcstm </_models/simple_machine.fcstm>`：

.. literalinclude:: /_models/simple_machine.fcstm
   :language: fcstm
   :caption: simple_machine.fcstm

.. code-block:: bash

   pyfcstm simulate -i simple_machine.fcstm --no-color

然后逐条输入命令：

.. code-block:: text

   cycle
   events
   cycle Start
   current
   history 3
   quit

交互模式额外提供命令历史、补全和建议，但命令语义和批处理模式一致。

注入事件
--------

``cycle Start`` 这类命令会在该周期注入事件。在 Python 中，把事件列表传给
``SimulationRuntime.cycle``：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text("""
   def int counter = 0;
   state System {
       [*] -> Idle;
       state Idle;
       state Active;
       Idle -> Active :: Start;
       Active -> Idle :: Stop;
   }
   """)
   runtime = SimulationRuntime(model)
   runtime.cycle()
   print(runtime.configuration)
   runtime.cycle(["Start"])
   print(runtime.configuration)
   runtime.cycle(["Stop"])
   print(runtime.configuration)

.. testoutput::

   System.Idle
   System.Active
   System.Idle

示例中的事件名依赖 DSL 事件作用域。语法事实请查 :doc:`../../reference/dsl/index_zh`；本页只说明仿真器如何接收事件。运行时支持的事件输入形式和 ``CycleResult`` 事件统计字段见 :doc:`../../reference/simulation/index_zh`。

在状态上热启动
--------------

当你需要检查后续状态但不想重放所有早期周期时，可以使用 ``init`` 命令。在 ``simple_machine.fcstm`` 上，从 ``Running`` 起步并设 ``counter=10``，再发送 ``Stop``：

.. code-block:: console

   $ pyfcstm simulate -i simple_machine.fcstm --no-color -e "\
   init SimpleMachine.Running counter=10; \
   cycle Stop; \
   current"
   ────────────────────────────────────────────────────────────
   >>> init SimpleMachine.Running counter=10
   ────────────────────────────────────────────────────────────
   Initialized from state: SimpleMachine.Running
   Cycle: 0
   Current State: SimpleMachine.Running
   Variables:
     counter = 10

   ────────────────────────────────────────────────────────────
   >>> cycle Stop
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Stopped
   Variables:
     counter = 11

   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Stopped
   Variables:
     counter = 11

在测试中嵌入同样逻辑时，使用 Python 应用程序接口：

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("simple_machine.fcstm")
   runtime = SimulationRuntime(
       model,
       initial_state="SimpleMachine.Running",
       initial_vars={"counter": 10},
   )
   print(runtime.configuration, dict(runtime.vars))
   runtime.cycle(["Stop"])
   print(runtime.configuration, dict(runtime.vars))

.. testoutput::

   SimpleMachine.Running {'counter': 10}
   SimpleMachine.Stopped {'counter': 11}


热启动有明确边界：

* ``initial_vars`` 必须提供每个已声明的持久变量。
* 预构造路径上的 enter 动作会被跳过。
* 第一个周期开始后，during 动作正常执行。
* 热启动构造只检查结构；首个真实周期没有可提交可停止/终止后继时记录成功 Delta，表达式、事件和 DFS 错误仍在该周期明确报告。

实现抽象处理器
--------------

抽象生命周期动作通过注册 Python 处理器实现。给方法加 ``@abstract_handler``，装饰器参数写 DSL 动作路径，方法名本身可以自定义：

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, abstract_handler

   model = load_state_machine_from_text("""
   def int counter = 0;
   state System {
       [*] -> Active;
       state Active {
           enter abstract Init;
           exit abstract Cleanup;
           during { counter = counter + 1; }
       }
       state Done;
       Active -> Done : if [counter >= 2];
   }
   """)


   class MyHandlers:
       @abstract_handler("System.Active.Init")
       def handle_init(self, ctx):
           print("[Init]", ctx.get_full_state_path(), ctx.get_var("counter"))

       @abstract_handler("System.Active.Cleanup")
       def handle_cleanup(self, ctx):
           print("[Cleanup]", ctx.get_var("counter"))


   runtime = SimulationRuntime(model)
   runtime.register_handlers_from_object(MyHandlers())
   for _ in range(4):
       runtime.cycle()
       print(runtime.configuration)

.. testoutput::

   [Init] System.Active 0
   System.Active
   System.Active
   [Cleanup] 2
   System.Done
   System.Done

处理器上下文是只读的。常用辅助方法包括 ``ctx.get_full_state_path()``、``ctx.get_var(name)``、
``ctx.has_var(name)``、``ctx.active_leaf`` 和 ``ctx.action_stage``。

导出历史
--------

只需要终端输出时用 ``history``。需要后续分析文件时用 ``export <path>``。仿真器从扩展名推断格式；任务文档中建议使用小例子：

.. code-block:: text

   cycle
   cycle Start
   history 2
   export run.json

机器处理优先用 JSON 或 JSONL；表格处理用带有明确 ``delta`` 列的 CSV；YAML 适合人工阅读快照。除非你有意提交导出文件，否则导出文件应放在源码树外。
各格式的精确字段见 :doc:`../../reference/simulation/index_zh`。

调整显示设置
------------

不带参数的 ``setting`` 会列出当前设置。``setting key value`` 会修改当前会话的一个值。常见例子：

.. code-block:: text

   setting table_max_rows 10
   setting history_size 200
   setting log_level info
   setting color off

``history_size`` 控制保留历史行数。``color`` 也会受命令行 ``--no-color`` 选项影响。完整设置表、默认值和合法值形式见 :doc:`../../reference/simulation/index_zh`。

调试失败模型
------------

一个紧凑调试循环是：

1. 如果怀疑解析或诊断问题，先运行 ``pyfcstm inspect``。
2. 用一小段批处理命令（见下）获得稳定转录。
3. 每次只增加一个事件。
4. 失败后使用 ``history`` 或 ``export``。
5. 如果热启动失败，先检查是否提供了所有变量和结构深度；若首周期得到 Delta，检查目标是否确实需要事件或存在稳定无进展边界。

针对第 2 步，在交互命令行一节的 ``simple_machine.fcstm`` 上运行：

.. code-block:: console

   $ pyfcstm simulate -i simple_machine.fcstm -e "cycle; events; current" --no-color
   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Idle
   Variables:
     counter = 0

   ────────────────────────────────────────────────────────────
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Start (SimpleMachine.Idle.Start)

   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Idle
   Variables:
     counter = 0

不要把仿真输出当作目标运行时测试的替代品。它是快速模型级检查；依赖目标语言行为时，还应搭配生成运行时测试。

绑定自定义环境输入源
--------------------

通过 ``SimulationRuntime(..., input_source=...)`` 绑定外部数值输入。
单值生成器可继承 ``BaseScalarInputPattern`` 并实现 ``_sample(step)``，相关向量可使用
``BaseIntegratedInputPattern``。可运行示例及采样、覆盖、耗尽和错误契约见
:doc:`../../reference/simulation/inputs_zh`。

候选决策诊断
--------------------------------

排查迁移为何未执行，见 :doc:`diagnostics_zh`；其中包含 Python 采集、交互查询、逐拍输入和 JSONL 示例。

含区域模型的任务
----------------

下面的任务卡使用含区域（region）的模型。每张卡都给出同样的六项：\ **起点**\ 、\ **命令或代码**\ 、\ **预期信号**\ 、\ **文件副作用**\ 、\ **失败时先查什么**\ 、\ **参考链接**\ 。
请把 :download:`controller.fcstm </_models/controller.fcstm>`、:download:`hot_watch.fcstm`、:download:`hot_stuck.fcstm` 和 :download:`leaf_events.fcstm` 下载到一个空目录，并在其中运行示例。``controller.fcstm`` 是 :doc:`/tutorials/regions/index_zh` 里的联锁控制器；建模任务本身见 :doc:`/how_to/regions/index_zh`。

从一个位置热启动含区域的模型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``controller.fcstm`` 和一个起始位置。位置是一棵树：写出来的部分就位，不执行 ``enter`` 动作；没写出来的部分等待初始化。
所有变量都要给全，包括模型转换加入的隐藏变量（这里是 ``__forced_0``）。

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: controller.fcstm

**命令或代码。** ``initial_state`` 接受位置的五种写法；脚本还演示了只写拥有者（owner）的情形：

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("controller.fcstm")
   variables = {"permit": 1, "motor": 1, "__forced_0": 0}
   # one source is shared by all runtimes below, so it holds its last value
   inputs = {
       "fault": SequenceInput([0], end="hold"),
       "requested": SequenceInput([1], end="hold"),
   }
   text = "Controller.Running{Safety: Watching, Motion: On}"
   motion_on = model.root_state.substates["Running"].regions["Motion"].substates["On"]
   forms = {
       "configuration text": text,
       "Configuration object": Configuration.parse(model, text),
       "dotted path": "Controller.Running.Motion.On",
       "tuple path": ("Controller", "Running", "Motion", "On"),
       "State object": motion_on,
       "owner only": "Controller.Running",
   }
   for label, form in forms.items():
       runtime = SimulationRuntime(
           model, initial_state=form, initial_vars=variables, input_source=inputs
       )
       print(label)
       print("  at start    ", runtime.configuration)
       runtime.cycle()
       print("  after cycle ", runtime.configuration)

.. testoutput::

   configuration text
     at start     Controller.Running{Safety: Watching, Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   Configuration object
     at start     Controller.Running{Safety: Watching, Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   dotted path
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   tuple path
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   State object
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   owner only
     at start     Controller.Running{Safety: [init], Motion: [init]}
     after cycle  Controller.Running{Safety: Watching, Motion: Off}

**预期信号。** 配置文本和 ``Configuration`` 对象把每个区域都放好。点路径、元组路径和 ``State`` 对象只指明一个叶子：没有经过的区域等待
（``[init]``），第一个周期里走各自的初始转换。只写拥有者时整组等待，各区域按书写顺序启动。已就位的部分不执行任何 ``enter`` 动作。

**文件副作用。** 无。

**失败时先查什么。** 起始位置和预期不同时，在第一个周期之前打印 ``runtime.configuration``，它会准确显示哪些已就位、哪些在等待。

**参考链接。** 位置文本与校验模式见 :doc:`/reference/region_model/index_zh`，构造函数见 :doc:`/reference/simulation/index_zh`。

给全变量，包括隐藏变量
~~~~~~~~~~~~~~~~~~~~~~

**起点。** 模型转换会加入隐藏变量的模型：强制转换（forced transition）对应 ``__forced_*``，历史对应 ``__hist_*``，``active()`` 查询对应 ``__active_*``。它们是普通变量，
运行时既不推导，也不核对它们与位置是否一致。``hot_watch.fcstm`` 使用了 ``active()``。

**命令或代码。**

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("hot_watch.fcstm")
   config = Configuration.parse(
       model, "Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}"
   )
   hidden = model.active_variables(config)
   print("queries:", [(".".join(q.state_path), q.variable_name) for q in model.active_queries])
   print("hidden variables for this position:", hidden)

   runtime = SimulationRuntime(
       model,
       initial_state=config,
       initial_vars=hidden,
       input_source={"go": SequenceInput([1])},
   )
   runtime.cycle()
   print("after one cycle:", runtime.configuration)
   print("runtime.vars:", dict(runtime.vars))

.. testoutput::

   queries: [('Plant.Trigger.Fired', '__active_Plant_Trigger_Fired')]
   hidden variables for this position: {'__active_Plant_Trigger_Fired': 1}
   after one cycle: Plant{Earlier: Saw, Trigger: Fired, Later: Saw}
   runtime.vars: {'__active_Plant_Trigger_Fired': 1}

同一个位置，隐藏变量分别设为 ``1`` 和 ``0``。只有查询为真时 ``Earlier`` 才会进入 ``Saw``：

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("hot_watch.fcstm")
   config = Configuration.parse(
       model, "Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}"
   )
   for value in (1, 0):
       runtime = SimulationRuntime(
           model,
           initial_state=config,
           initial_vars={"__active_Plant_Trigger_Fired": value},
           input_source={"go": SequenceInput([1])},
       )
       runtime.cycle()
       print(value, runtime.configuration)

.. testoutput::

   1 Plant{Earlier: Saw, Trigger: Fired, Later: Saw}
   0 Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}

**预期信号。** ``model.active_queries`` 列出查询及其变量名；``model.active_variables(config)`` 算出与位置匹配的取值。运行时接受它们作为
``initial_vars``，并在 ``runtime.vars`` 里显示。若传入与位置不一致的值，运行时按你传入的值运行，见第二个脚本。

**文件副作用。** 无。

**失败时先查什么。** 构造时报缺少某个变量，就列出 ``model.active_queries`` 以及模型里的 ``__forced_*``、``__hist_*`` 变量并补上。

**参考链接。** :doc:`/reference/region_model/index_zh`。

排除三种典型的热启动报错
~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``controller.fcstm`` 与下面三种拒绝。脚本构造三次运行时，并每次打印 ``ValueError``。

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("controller.fcstm")
   full = {"permit": 1, "motor": 1, "__forced_0": 0}
   cases = [
       ("hidden variable left out", "Controller.Running{Safety: Watching, Motion: On}",
        {"permit": 1, "motor": 1}),
       ("every region done", "Controller.Running{Safety: [done], Motion: [done]}", full),
       ("unknown state", "Controller.Running{Safety: Nope, Motion: On}", full),
   ]
   for label, initial_state, variables in cases:
       try:
           SimulationRuntime(
               model,
               initial_state=initial_state,
               initial_vars=variables,
               input_source={"fault": SequenceInput([0]), "requested": SequenceInput([1])},
           )
       except ValueError as error:
           print(f"{label}: ValueError: {error}")

.. testoutput::

   hidden variable left out: ValueError: initial_vars must provide all variables. Missing: ['__forced_0']
   every region done: ValueError: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   unknown state: ValueError: Unknown configuration path: 'Controller.Running.Safety.Nope'.

**命令或代码与修法。**

* *漏掉隐藏变量*\ （第一行）：把 ``__forced_0`` 加进 ``initial_vars``。不要因为源文本里没写就省掉它。
* *全体区域已完成*\ （第二行）：一个拥有者的区域全部为 ``[done]`` 的配置，在任何层级都不可能是停驻位置。留一个区域在工作，或改从拥有者续接的状态启动。
* *未知状态*\ （第三行）：路径不存在。打印 ``[s.path for s in model.walk_states()]``，从中复制一条路径。

**预期信号。** 每种拒绝都在任何周期运行之前抛出 ``ValueError``。

**文件副作用。** 无。

**失败时先查什么。** 读报错：每条都会指出缺少的变量、全体已完成的拥有者，或未知路径。

**参考链接。** :doc:`/reference/simulation/index_zh`。

解决事件名歧义
~~~~~~~~~~~~~~

**起点。** ``leaf_events.fcstm``：两个叶子各声明了名为 ``Ping`` 的事件，一个叶子声明了 ``Go``。完整路径与 ``/名字`` 在任何位置含义相同。
短名对每个活动叶子各解析一次：没有匹配是错误，找到同一个事件就使用，找到不同事件则是歧义。

.. literalinclude:: leaf_events.fcstm
   :language: fcstm
   :caption: leaf_events.fcstm

**命令或代码。**

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime
   from pyfcstm.simulate.runtime import SimulationRuntimeEventError
   from pyfcstm.utils.validate import ModelLookupError, ModelValueError

   model = load_state_machine_from_file("leaf_events.fcstm")
   config = Configuration.parse(model, "Root.P{L: X, R: Y}")
   for name in ("Go", "/Reset", "Ping", "Nope"):
       try:
           print(f"{name!r} -> {config.resolve_event(name).path_name}")
       except (ModelValueError, ModelLookupError) as error:
           print(f"{name!r} -> {type(error).__name__}: {error}")

   for events in (["Ping"], ["Root.P.L.X.Ping"], ["Root.P.L.X.Ping", "Root.P.R.Y.Ping"]):
       runtime = SimulationRuntime(model)
       runtime.cycle()
       try:
           runtime.cycle(events)
       except SimulationRuntimeEventError as error:
           print(f"cycle({events}) -> refused: {error}")
       else:
           print(f"cycle({events}) -> {runtime.configuration}")

.. testoutput::

   'Go' -> Root.P.L.X.Go
   '/Reset' -> Root.Reset
   'Ping' -> ModelValueError: Position-dependent event name 'Ping' is ambiguous: Root.P.L.X.Ping (from Root.P.L.X); Root.P.R.Y.Ping (from Root.P.R.Y); use the full event path or a root-based "/path".
   'Nope' -> ModelLookupError: Position-dependent event name 'Nope' matches no event from any active leaf (Root.P.L.X, Root.P.R.Y); use the full event path or a root-based "/path".
   cycle(['Ping']) -> refused: Position-dependent event name 'Ping' is ambiguous: Root.P.L.X.Ping (from Root.P.L.X); Root.P.R.Y.Ping (from Root.P.R.Y); use the full event path or a root-based "/path".
   cycle(['Root.P.L.X.Ping']) -> Root.P{L: X, R: Y}
   cycle(['Root.P.L.X.Ping', 'Root.P.R.Y.Ping']) -> Root.P{L: X, R: Y2}

**预期信号。** ``Go`` 解析为一个事件；``/Reset`` 在任何位置都能解析；``Ping`` 抛出歧义错误，列出每个候选及其来源叶子；``Nope`` 抛出查找错误，列出尝试过的叶子。
``cycle(['Ping'])`` 以同样的歧义被拒绝，而完整路径让一个区域动，两条完整路径让两个区域都动。裸名字不会向上查找，
已完成的区域和还在等待初始化的区域不参与解析。

**文件副作用。** 无。

**失败时先查什么。** 把报错里的完整路径复制到调用或模型里。

**参考链接。** :doc:`/reference/simulation/index_zh`。

查明这一拍为什么什么都没发生
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``hot_stuck.fcstm``：``Right`` 只有在 ``flag > 0`` 时才能启动。从 ``Root.Pair{Left: Busy}`` 以 ``flag=0`` 热启动，等待中的区域到不了停驻位置。

.. literalinclude:: hot_stuck.fcstm
   :language: fcstm
   :caption: hot_stuck.fcstm

**命令或代码。**

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("hot_stuck.fcstm")
   for flag in (0, 1):
       runtime = SimulationRuntime(
           model,
           initial_state="Root.Pair{Left: Busy}",
           initial_vars={"flag": flag, "work": 0},
       )
       result = runtime.cycle(diagnostics=True)
       print(f"flag={flag}: delta={result.delta} outcome={result.diagnostics.outcome}")
       print(f"  {runtime.configuration} {dict(runtime.vars)}")
       for item in result.diagnostics.decisions:
           print(f"  #{item.id} {item.transition_label}")
           print(f"     {item.outcome}: {item.guard} is {item.guard_result}")

.. testoutput::

   Cycle 1 completed as Delta - State: Root.Pair{Left: Busy, Right: [init]}; no stoppable successor was committed
   flag=0: delta=True outcome=delta
     Root.Pair{Left: Busy, Right: [init]} {'flag': 0, 'work': 0}
     #1 Root.Pair.Right::0::INIT_STATE->Ready
        guard_false: flag > 0 is False
   flag=1: delta=False outcome=cycle
     Root.Pair{Left: Busy, Right: Ready} {'flag': 1, 'work': 1}
     #1 Root.Pair.Right::0::INIT_STATE->Ready
        selected: flag > 0 is True
     #2 Root.Pair.Right::0::INIT_STATE->Ready
        selected: flag > 0 is True

**预期信号。** ``flag=0`` 时这个周期是 Delta：``delta=True``，配置和变量都不变，连 ``Left`` 的 ``during``\ （本会让 ``work`` 增加）也被回滚。第一条检查指出失败的转换：``Root.Pair.Right::0::INIT_STATE->Ready`` 是 ``Right`` 的初始转换，它以 ``guard_false`` 结束，守卫是 ``flag > 0``。``flag=1`` 时同一个调用让 ``Right`` 就位并执行 ``Left`` 的 ``during``。Delta 是整个周期没有提交；各区域只是原地停留的周期不是 Delta。
命令行用 ``pyfcstm simulate --diagnostics`` 与 ``why`` 给出同样的证据，见 :doc:`diagnostics_zh`。

**文件副作用。** 无；Delta 的警告输出到标准错误。

**失败时先查什么。** 读第一条结果为 ``guard_false`` 或 ``successor_rejected`` 的检查，看它的 ``vars``：那是检查时刻的值，不是最终值。

**参考链接。** :doc:`/reference/simulation/diagnostics_zh`。

在交互命令行里用 ``init`` 输入配置文本并查看 ``events``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``controller.fcstm``。``init`` 接受花括号里的配置文本；每个变量只给一次。

**命令或代码。**

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; \
   events; \
   init Controller.Running permit=1 motor=0 __forced_0=0"
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
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Controller.Stop

   ────────────────────────────────────────────────────────────
   >>> init Controller.Running permit=1 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialized from state: Controller.Running
   Cycle: 0
   Current State: Controller.Running{Safety: [init], Motion: [init]}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

**预期信号。** ``init`` 报告它构建出的位置。只写拥有者时，每个区域都显示 ``[init]``。``events`` 只列出从活动叶子出发确实存在的事件。位置在所有地方
（``current``、历史表格、导出）都按配置文本显示。

两种拒绝，都是负例，退出状态都是 1：

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running permit=1 permit=0 motor=0 __forced_0=0"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running permit=1 permit=0 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Error: variable 'permit' is assigned more than once.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=0 __forced_0=0"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialization failed: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1

在交互命令行里，Tab 补全只提供确实能解析的短事件名，并且能补全区域里的状态。补全需要终端，所以不在文档检查里运行；在 ``controller.fcstm`` 的交互会话里先执行一次 ``cycle``，输入 ``init Controller.Running.`` 后按 Tab，会给出 ``Controller.Running.Motion.Off``、``Controller.Running.Motion.On`` 和 ``Controller.Running.Safety.Watching`` 三个叶子状态；输入 ``cycle Co`` 会给出事件名 ``Controller.Start``；输入 ``cycle S`` 没有候选。

``cycle S`` 没有候选，因为 ``Start`` 声明在拥有者上，裸名字不会向上查找；``cycle Co`` 给出完整路径。

**文件副作用。** 无。

**失败时先查什么。** ``init`` 说缺少变量时，对一次正常启动运行 ``current``：它会列出所有变量，包括隐藏变量。

**参考链接。** :doc:`/reference/simulation/index_zh`。
