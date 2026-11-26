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
     - 使用显式变量在某个状态（含并行区域的模型也可以是配置文本）热启动并重建运行时。
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

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm \
     -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
     --no-color

短教程使用的生成转录保留在这里：

.. literalinclude:: ../../tutorials/simulation/cli_batch.demo.sh.txt
   :language: text

使用交互命令行
--------------

省略 ``-e`` 即可启动交互命令行：

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm --no-color

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

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py
   :language: python
   :caption: 通过 Python 运行时注入事件

输出：

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py.txt
   :language: text

示例中的事件名依赖 DSL 事件作用域。语法事实请查 :doc:`../../reference/dsl/index_zh`；本页只说明仿真器如何接收事件。运行时支持的事件输入形式和 ``CycleResult`` 事件统计字段见 :doc:`../../reference/simulation/index_zh`。

在状态上热启动
--------------

当你需要检查后续状态但不想重放所有早期周期时，可以使用交互命令行的 ``init`` 命令：

.. code-block:: text

   init System.Active counter=10 flag=1
   cycle
   current

在测试中嵌入同样逻辑时，使用 Python 应用程序接口：

.. code-block:: python

   runtime = SimulationRuntime(
       sm,
       initial_state="System.Active",
       initial_vars={"counter": 10, "flag": 1},
   )

热启动有明确边界：

* ``initial_vars`` 必须提供每个已声明的持久变量。
* 预构造路径上的 enter 动作会被跳过。
* 第一个周期开始后，during 动作正常执行。
* 热启动构造只检查结构；首个真实周期没有可提交可停止/终止后继时记录成功 Delta，表达式、事件和 DFS 错误仍在该周期明确报告。

实现抽象处理器
--------------

抽象生命周期动作通过注册 Python 处理器实现。给方法加 ``@abstract_handler``，装饰器参数写 DSL 动作路径，方法名本身可以自定义：

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py
   :language: python
   :caption: 仿真运行时中的抽象处理器

输出：

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py.txt
   :language: text

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

机器处理优先用 JSON 或 JSONL；表格处理用带有明确 ``delta`` 列的 CSV；YAML 适合人工阅读快照。除非文件是由 docs build 重新生成并纳入版本控制的 demo 输出，否则导出文件应放在源码树外。
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
2. 用 ``pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm -e "cycle; events; current" --no-color``
   获得稳定转录。
3. 每次只增加一个事件。
4. 失败后使用 ``history`` 或 ``export``。
5. 如果热启动失败，先检查是否提供了所有变量和结构深度；若首周期得到 Delta，检查目标是否确实需要事件或存在稳定无进展边界。

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
请在本目录里运行。``hot_controller.fcstm`` 是 :doc:`/tutorials/regions/index_zh` 里的联锁控制器；建模任务本身见 :doc:`/how_to/regions/index_zh`。

从一个位置热启动含区域的模型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``hot_controller.fcstm`` 和一个起始位置。位置是一棵树：写出来的部分就位，不执行 ``enter`` 动作；没写出来的部分等待初始化。
所有变量都要给全，包括模型转换加入的隐藏变量（这里是 ``__forced_0``）。

.. literalinclude:: hot_controller.fcstm
   :language: fcstm
   :caption: hot_controller.fcstm

**命令或代码。** ``initial_state`` 接受位置的五种写法；脚本还演示了只写拥有者的情形：

.. literalinclude:: hot_start_forms.demo.py
   :language: python
   :caption: hot_start_forms.demo.py

.. literalinclude:: hot_start_forms.demo.py.txt
   :language: text

**预期信号。** 配置文本和 ``Configuration`` 对象把每个区域都放好。点路径、元组路径和 ``State`` 对象只指明一个叶子：没有经过的区域等待
（``[init]``），第一个周期里走各自的初始转换。只写拥有者时整组等待，各区域按书写顺序启动。已就位的部分不执行任何 ``enter`` 动作。

**文件副作用。** 无。

**失败时先查什么。** 起始位置和预期不同时，在第一个周期之前打印 ``runtime.configuration``，它会准确显示哪些已就位、哪些在等待。

**参考链接。** 位置文本与校验模式见 :doc:`/reference/region_model/index_zh`，构造函数见 :doc:`/reference/simulation/index_zh`。

给全变量，包括隐藏变量
~~~~~~~~~~~~~~~~~~~~~~

**起点。** 模型转换会加入隐藏变量的模型：强制转换对应 ``__forced_*``，历史对应 ``__hist_*``，``active()`` 查询对应 ``__active_*``。它们是普通变量，
运行时既不推导，也不核对它们与位置是否一致。``hot_watch.fcstm`` 使用了 ``active()``。

**命令或代码。**

.. literalinclude:: hot_active_variables.demo.py
   :language: python
   :caption: hot_active_variables.demo.py

.. literalinclude:: hot_active_variables.demo.py.txt
   :language: text

**预期信号。** ``model.active_queries`` 列出查询及其变量名；``model.active_variables(config)`` 算出与位置匹配的取值。运行时接受它们作为
``initial_vars``，并在 ``runtime.vars`` 里显示。若传入与位置不一致的值，运行时按你传入的值运行。

**文件副作用。** 无。

**失败时先查什么。** 构造时报缺少某个变量，就列出 ``model.active_queries`` 以及模型里的 ``__forced_*``、``__hist_*`` 变量并补上。

**参考链接。** :doc:`/reference/region_model/index_zh`。

排除三种典型的热启动报错
~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``hot_controller.fcstm`` 与下面三种拒绝。脚本 ``hot_start_errors.demo.py`` 构造三次运行时，并每次打印 ``ValueError``。

.. literalinclude:: hot_start_errors.demo.py.txt
   :language: text

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

.. literalinclude:: event_names.demo.py
   :language: python
   :caption: event_names.demo.py

.. literalinclude:: event_names.demo.py.txt
   :language: text

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

.. literalinclude:: hot_delta.demo.py
   :language: python
   :caption: hot_delta.demo.py

.. literalinclude:: hot_delta.demo.py.txt
   :language: text

**预期信号。** ``flag=0`` 时这个周期是 Delta：``delta=True``，配置和变量都不变，连 ``Left`` 的 ``during``\ （本会让 ``work`` 增加）也被回滚。第一条检查指出失败的转换
（``guard_false``，``flag > 0``）。``flag=1`` 时同一个调用让 ``Right`` 就位并执行 ``Left`` 的 ``during``。Delta 是整个周期没有提交；各区域只是原地停留的周期不是 Delta。
命令行用 ``pyfcstm simulate --diagnostics`` 与 ``why`` 给出同样的证据，见 :doc:`diagnostics_zh`。

**文件副作用。** 无；Delta 的警告输出到标准错误。

**失败时先查什么。** 读第一条结果为 ``guard_false`` 或 ``successor_rejected`` 的检查，看它的 ``vars``：那是检查时刻的值，不是最终值。

**参考链接。** :doc:`/reference/simulation/diagnostics_zh`。

在交互命令行里用 ``init`` 输入配置文本并查看 ``events``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``hot_controller.fcstm``。``init`` 接受花括号里的配置文本；每个变量只给一次。

**命令或代码。**

.. literalinclude:: repl_init.demo.sh
   :language: bash

.. literalinclude:: repl_init.demo.sh.txt
   :language: text

**预期信号。** ``init`` 报告它构建出的位置。只写拥有者时，每个区域都显示 ``[init]``。``events`` 只列出从活动叶子出发确实存在的事件。位置在所有地方
（``current``、历史表格、导出）都按配置文本显示。

两种拒绝，都是负例：

.. literalinclude:: repl_init_duplicate.demox.sh.txt
   :language: text

（同一个变量赋值两次；退出码在 ``repl_init_duplicate.demox.sh.exitcode`` 里，为 1。）

.. literalinclude:: repl_init_done.demox.sh.txt
   :language: text

（全体区域已完成；退出码在 ``repl_init_done.demox.sh.exitcode`` 里，为 1。）

在交互命令行里，Tab 补全只提供确实能解析的短事件名，并且能补全区域里的状态。交互命令行使用的补全器给出：

.. literalinclude:: repl_completion.demo.py.txt
   :language: text

``cycle S`` 没有候选，因为 ``Start`` 声明在拥有者上，裸名字不会向上查找；``cycle Co`` 给出完整路径。

**文件副作用。** 无。

**失败时先查什么。** ``init`` 说缺少变量时，对一次正常启动运行 ``current``：它会列出所有变量，包括隐藏变量。

**参考链接。** :doc:`/reference/simulation/index_zh`。
