.. _sec-reference-simulation-zh:

仿真参考
========

当你需要精确的仿真（simulation）事实时，使用本页：命令形式、事件输入、设置、历史/导出格式、Python 运行时应用程序接口（API）和公开失败边界。第一次运行见 :doc:`../../tutorials/simulation/index_zh`；任务步骤见 :doc:`../../how_to/simulation/index_zh`；执行顺序语义见 :doc:`../../explanations/execution_semantics/index_zh`。

命令行调用
------------

``pyfcstm simulate`` 会加载一个 FCSTM 文件，将其解析成状态机模型，创建 :class:`pyfcstm.simulate.SimulationRuntime`，然后启动交互命令行（REPL）或运行分号分隔的批处理（batch）命令。

.. list-table:: 命令行选项
   :header-rows: 1

   * - 选项
     - 是否必填
     - 含义
   * - ``-i`` / ``--input-code TEXT``
     - 是
     - FCSTM 输入文件路径。
   * - ``-e`` / ``--execute TEXT``
     - 否
     - 批处理命令字符串。命令之间用分号分隔。
   * - ``--no-color``
     - 否
     - 禁用命令输出中的 ANSI 颜色。
   * - ``-h`` / ``--help``
     - 否
     - 显示 Click 帮助并退出。

解码、语法、语义建模失败会写到标准错误，形如 ``Failed to parse DSL file: ...``，并非零退出。批处理命令失败会停止执行并非零退出；交互命令失败打印提示后可继续输入。

批处理和交互命令
----------------

批处理模式和交互命令行使用同一个命令处理器。

.. list-table:: 仿真器命令
   :header-rows: 1

   * - 命令
     - 参数
     - 输出和边界
   * - ``cycle [count] [events...]``
     - 可选正整数次数，后面接事件输入。没有次数时执行一个周期。
     - 运行一个或多个周期。非正次数会报告 ``Error: cycle count must be a positive integer``。DFS、事件和表达式错误会报告 ``Cycle execution failed: ...``。
   * - ``current``
     - 无
     - 打印当前周期、状态和持久变量。
   * - ``events``
     - 无
     - 列出当前运行时状态可用的事件。
   * - ``history [n|all]``
     - 可选正整数行数或 ``all``。默认 10 行。
     - 打印保留历史。历史为空时报告 ``No execution history available.``。
   * - ``init <position> [var=value...]``
     - 目标状态（含并行区域的模型也可以写配置文本，例如 ``Root.Run{A: X, B: [done]}``\ ）和数值变量赋值。见 :ref:`sim-region-cli-zh`。
     - 把运行时重建为热启动状态。必须提供每个声明过的变量，隐藏变量也不例外。配置文本花括号里的空格不会切开参数；没写出来的部分在第一拍等待初始化。数值支持十进制、十六进制、二进制、浮点和科学计数法。
   * - ``setting [key] [value]``
     - 无参数、一个键或键值对。
     - 列出设置、显示单个设置或修改单个设置。
   * - ``export <filename>``
     - 后缀为 ``.csv``、``.json``、``.yaml`` 或 ``.jsonl`` 的输出路径。
     - 写出保留历史。历史为空、不支持后缀、文件写入失败都会返回明确命令信息。
   * - ``clear``
     - 无
     - 保留会话级配置并重建一个新运行时。
   * - ``help``
     - 无
     - 打印命令帮助和键盘快捷键。
   * - ``quit`` / ``exit``
     - 无
     - 离开交互命令行，或结束批处理命令处理。

事件输入形式
------------

运行时接受模型拥有的 :class:`pyfcstm.model.Event` 对象、单个事件路径字符串，或包含这些值的可迭代对象。裸字符串表示一个事件输入，不会按字符拆分。

.. list-table:: 事件路径形式
   :header-rows: 1

   * - 形式
     - 例子
     - 含义
   * - 短名或相对事件名
     - ``Start``
     - 从当前运行时状态解析。
   * - 点分完整路径
     - ``System.Idle.Start``
     - 按模型事件路径解析。
   * - 父级相对路径
     - ``.error`` 或 ``..system.error``
     - 相对当前状态路径向上导航。
   * - 绝对路径
     - ``/global.shutdown``
     - 从根状态解析。
   * - 多事件
     - ``cycle Start Stop`` 或 ``runtime.cycle(["Start", "Stop"])``
     - 让列出的事件在同一周期可用。

当事件输入形状不受支持、无法解析，或属于另一台状态机时，Python 应用程序接口会抛出 :class:`pyfcstm.simulate.SimulationRuntimeEventError`；命令层会显示 ``Cycle execution failed: ...``。

设置
----

设置是命令层会话设置。``--no-color`` 会把该命令行会话的 ``color`` 初始化为 ``False``。

.. list-table:: 设置表
   :header-rows: 1

   * - 键
     - 类型和合法值
     - 默认值
     - 影响
   * - ``table_max_rows``
     - 非负整数
     - ``20``
     - 控制大表格输出的截断。
   * - ``history_size``
     - 非负整数；``0`` 表示运行时历史不设上限
     - ``100``
     - 控制活动运行时保留多少历史记录。
   * - ``color``
     - 布尔字符串 ``on`` / ``off``、``true`` / ``false``、``1`` / ``0``、``yes`` / ``no``
     - 除非使用 ``--no-color``，否则为 ``True``
     - 启用或禁用显示输出中的 ANSI 颜色。
   * - ``log_level``
     - ``debug``、``info``、``warning``、``error`` 或 ``off``
     - ``warning``
     - 控制仿真器日志详细程度。

未知设置会报告 ``Error: 'Unknown setting: <key>'``。非法值会报告设置校验器给出的 ``Error: ...`` 信息。

.. note::
   ``history_size=0``\ 是命令层约定。设置同步时，命令层会把它映射为
   ``SimulationRuntime.history_size = None``\ 。直接使用 Python 应用程序接口时语义不同：
   ``SimulationRuntime(history_size=None)``\ 表示历史不设上限，而
   ``SimulationRuntime(history_size=0)``\ 表示不保留历史记录。

历史和导出格式
--------------

运行时历史记录是包含 ``cycle``、``state``、``vars``、``events`` 和布尔 ``delta`` 键的字典。``history`` 会显示保留行；``export`` 是命令层功能，不是 :class:`pyfcstm.simulate.SimulationRuntime` 方法。

.. list-table:: 导出格式
   :header-rows: 1

   * - 后缀
     - 形状
     - 说明
   * - ``.csv``
     - 列为 ``cycle``、``state``、``delta``、``events``，然后是排序后的变量名。
     - 事件在一个 CSV 单元格内用分号连接。
   * - ``.json``
     - 历史记录对象组成的 JSON 数组。
     - 使用两个空格缩进和 UTF-8 输出。
   * - ``.yaml``
     - 历史记录映射组成的 YAML 序列。
     - 使用支持 Unicode 的 PyYAML 输出。
   * - ``.jsonl``
     - 每行一个 JSON 历史记录对象。
     - 适合追加式或流式后处理。

.. _sim-region-event-names-zh:

多个活动叶子时的事件名
------------------------------

含区域（region）的模型有多个活动叶子。完整的模型路径（例如 ``Controller.Running.Stop``）和从根开始的路径（例如 ``/Running.Stop``）在机器停在哪里都指同一个事件。
依赖当前位置的名字（短名如 ``Go``，或用前导点数层的名字如 ``..Stop``）对每个活动叶子各解析一次，再合并结果。

.. list-table:: 依赖位置的名字的三种结果
   :header-rows: 1
   :widths: 24 30 46

   * - 找到事件的叶子
     - 结果
     - 被拒绝时的报错
   * - 没有
     - 被拒绝；什么都不运行。
     - ``Position-dependent event name 'Nope' matches no event from any active leaf (<leaves>); use the full event path or a root-based "/path".``
       （\ ``Configuration.resolve_event`` 抛出 ``ModelLookupError``，\ ``cycle`` 抛出 ``SimulationRuntimeEventError``\ ）。
   * - 一个或多个，找到的都是同一个事件
     - 使用该事件。找到它的几个区域在同一周期里都会响应。
     - 无
   * - 找到的是不同的事件
     - 作为歧义被拒绝；什么都不运行。
     - ``Position-dependent event name 'Ping' is ambiguous: <event> (from <leaf>); <event> (from <leaf>); use the full event path or a root-based "/path".``
       报错列出每个候选以及指向它的叶子。

补充规则：

* 裸名字只在每个活动叶子自己的命名空间里查找，从不向上查找。复合拥有者、区域或祖先上的事件，要写完整路径、从根开始的 ``/name``，或用前导点数层
  （\ ``..Stop`` 从 ``Running`` 各区域的叶子出发，到达 ``Controller.Running.Stop``\ ）。
* 已完成的区域和仍在等待初始化的区域没有活动叶子，不参与解析。
* ``runtime.cycle`` 先把名字当作完整模型路径尝试，再退回到依赖位置的解析。只有一个活动叶子时，被拒绝的报错写作
  ``Cannot resolve event path 'Reset': failed with both StateMachine.resolve_event and State.resolve_event. ...``。
* 同一周期里的每个名字各自解析。
* ``consumed_events`` 对每条用到事件的转换各列一次；被两个区域共用的事件出现两次。

.. literalinclude:: event_names.fcstm
   :language: fcstm

.. literalinclude:: region_event_names.demo.py.txt
   :language: text

``Configuration.resolve_event`` 一块展示了依赖位置的名字的三种结果：``Trip`` 与 ``Go`` 只有一个叶子找到；``Ping`` 有歧义，因为两个叶子各有一个 ``Ping``；
``Nope`` 与 ``Reset`` 没有叶子找到，尽管 ``Reset`` 存在于根上，因为裸名字从不向上查找。``..Stop``、``/Running.Stop`` 和完整路径都能到达拥有者的事件。
``cycle`` 一块显示被拒绝的调用不改变位置（每行都从全新的运行时开始），并显示已完成的区域让 ``Ping`` 不再有歧义。这些输出确定了解析规则，不能说明解析一个名字要花多久。

.. _sim-region-hot-start-zh:

含区域的模型的热启动
------------------------------

``SimulationRuntime(model, initial_state=position, initial_vars=variables, parameters=..., input_source=...)`` 从一个位置启动，不运行任何 ``enter`` 动作。
冷启动（``initial_state=None``）在第一个周期里运行初始进入。

.. list-table:: ``initial_state`` 的写法
   :header-rows: 1
   :widths: 26 34 40

   * - 写法
     - 示例
     - 得到的位置
   * - 配置文本
     - ``'Controller.Running{Safety: Watching, Motion: On}'``
     - 恰好是写出来的内容。
   * - ``Configuration``
     - ``Configuration.parse(model, text)``
     - 恰好是该值；它必须来自同一个模型对象。
   * - 点路径
     - ``'Controller.Running.Motion.On'``
     - 路径经过的那条分支；路径上每个拥有者的其他区域等待初始化。
   * - 元组
     - ``('Controller', 'Running', 'Motion', 'On')``
     - 与点路径相同。
   * - ``State``
     - ``On`` 的 ``State`` 对象
     - 与点路径相同；它必须属于同一个模型对象。

位置是一棵树。写出来的部分就位，不运行任何 ``enter``；没写出来的部分等待初始化，在第一个周期里按书写顺序走各自的初始转换，其余部分照常工作。
有三种情形会等待：被省略的区域（以及点路径上各拥有者的其他区域）、只写成路径的拥有者（整组）、没写子状态的普通复合状态。

.. list-table:: 热启动的位置文本
   :header-rows: 1
   :widths: 40 60

   * - 文本
     - 含义
   * - ``Root.Job{A: X, B: Y}``
     - 拥有者 ``Root.Job`` 停驻，区域 ``A`` 在状态 ``X``，区域 ``B`` 在 ``Y``。区域条目写的是相对该区域的子状态；更深的叶子写作 ``Comp.In1``；
       嵌套的拥有者再写一个花括号块，如 ``Q{A1: W1, A2: W2}``。
   * - ``Root.Job{A: X}``
     - ``B`` 被省略，等待初始化（显示为 ``B: [init]``）。
   * - ``Root.Job{A: [done], B: Y}``
     - ``A`` 已完成：保持已完成，不做任何工作。
   * - ``Root.Job{A: X, B: [init]}``
     - ``B`` 明确等待；与省略相同。
   * - ``Root.Job``
     - 整组等待初始化。
   * - ``Root.Idle``
     - 普通叶子；与不含区域的模型相同。

下面的输出列出被接受的写法。第一块用每种写法启动教程里的控制器并显示得到的配置，最后一块显示第一个周期会初始化被省略的区域。

.. literalinclude:: region_hot_start.demo.py.txt
   :language: text

规则与拒绝：

* ``initial_vars`` 必须给出每个持久变量，隐藏变量（``__forced_*``、``__hist_*``、``__active_*``）也不例外。它们是普通变量：运行时既不按位置推导，也不检查它们与位置是否一致。
  ``StateMachine.active_variables(config)`` 与 ``history_variables(...)`` 会算出与某个位置一致的值。输入与参数不属于 ``initial_vars``；热启动仍要求完整的 ``parameters`` 与完整的 ``input_source``
  （见 :doc:`inputs_zh`）。
* 任一层拥有者的区域全体已完成，会被拒绝。
* 等待初始化的拥有者在第一个周期里到不了可停驻的位置时，这一整个周期是 Delta：位置与变量保持写出来的样子，``cycle_count`` 仍然前进。

.. literalinclude:: region_hot_start_rejections.demo.py.txt
   :language: text

.. literalinclude:: pending_delta.fcstm
   :language: fcstm

.. literalinclude:: region_pending_delta.demo.py.txt
   :language: text

前三行显示 ``Count`` 没有做 ``during`` 工作（``ticks`` 仍是 ``0``），因为 ``Gate`` 无法启动：该周期被回滚，``delta`` 为 ``True``，位置是写出来的那个。
最后一行是同一个位置在 ``ready=1`` 时的结果：两个区域在该周期里都工作。Delta 的信息也以 ``warning`` 级别记录在 stderr 上；输出记录里已隐去。

.. literalinclude:: active_flags.fcstm
   :language: fcstm

.. literalinclude:: region_active_variables.demo.py.txt
   :language: text

隐藏标志必须和其他变量一起给出；给成 ``0`` 就按 ``0`` 运行，即使位置说明该状态是活动的。标志与位置是否一致，由调用方负责。

.. _sim-region-position-api-zh:

位置、结果与处理器上下文
------------------------------

.. list-table:: 运行时的位置接口
   :header-rows: 1
   :widths: 28 72

   * - 成员
     - 含区域的模型上的行为
   * - ``runtime.configuration``
     - 停驻位置的不可变 :class:`pyfcstm.model.Configuration`，所有模型都可用，含区域与否均可。``str()`` 给出位置文本，``repr()`` 还会显示校验模式。
   * - ``runtime.current_state``
     - 含区域的模型返回同一个 ``Configuration``；不含区域的模型仍然返回 ``State``。先检查 ``is_ended``：终止后访问会抛出 ``SimulationRuntimeTerminalStateError``。
   * - ``runtime.brief_stack``
     - 含区域的模型上抛出 ``SimulationRuntimeRegionQueryError``：``brief_stack describes a single active path, but this model has regions; use configuration, which shows every branch.``
   * - ``Configuration.leaves``
     - 活动的停驻叶子，每条存活的区域分支一个；已完成和等待的分支没有。
   * - ``CycleResult``
     - 字段与不含区域时相同。``input_events`` 是按输入顺序的规范路径；``consumed_events`` 对每条用到事件的转换各列一次；整个周期回滚时 ``delta`` 为 ``True``。
   * - Delta
     - 是整个周期的概念：没有区域保留本周期的写入，位置与变量保持原样，``cycle_count`` 前进。

.. literalinclude:: region_position_api.demo.py.txt
   :language: text

抽象处理器接收一个 ``ReadOnlyExecutionContext``。

.. list-table:: 区域周围的处理器上下文字段
   :header-rows: 1
   :widths: 26 74

   * - 字段
     - 取值
   * - ``state_path``
     - 该动作所包住范围内最深的公共状态：只包住一条分支时是该分支的叶子，包住整组区域时是拥有者。
   * - ``active_leaf``
     - 与 ``state_path`` 同样取值（恰好包住一个活动叶子时是该叶子，否则是宿主状态路径）。
   * - ``configuration``
     - 调用那一刻的完整配置，类型是 ``Configuration``。尚未启动的区域显示为 ``[init]``；同一周期里已经移动的区域显示新的状态。
   * - ``get_var(name)``
     - 变量快照，包含隐藏变量。

.. literalinclude:: handler_hooks.fcstm
   :language: fcstm

.. literalinclude:: region_handler_context.demo.py.txt
   :language: text

周期 2 里，``Tick``\ （根上的切面）和 ``GroupPre``\ （拥有者上的切面）包住整组区域，所以它们的 ``state_path`` 是 ``Controller.Running``；``SafetyPre`` 与 ``Watch`` 只包住一条分支，报告的是该分支的叶子。
``Motion`` 在该周期的每次调用里都是 ``[init]``，因为它还没有启动；周期 3 里它先是 ``Off``，到 ``Drive`` 调用时是 ``On``。

.. _sim-region-cli-zh:

含区域模型的 simulate 命令
------------------------------

``pyfcstm simulate`` 在批处理和交互模式下都接受含区域的模型。位置以配置文本显示：``current``、``cycle`` 之后、多周期表格、``history`` 和导出的文件里都是如此。

.. list-table:: 命令里与区域有关的事实
   :header-rows: 1
   :widths: 22 78

   * - 命令
     - 行为
   * - ``init <position> var=value ...``
     - 位置可以是配置文本、经过区域的点路径或状态路径。花括号里的空格不会切开参数，所以 ``init Controller.Running{Safety: Watching, Motion: On} permit=1`` 是一个位置。
       括号不平衡时报 ``Error: the braces of the configuration text '...' are not balanced.`` 并给出示例。同一个变量写两次时报 ``Error: variable 'permit' is assigned more than once.``
       缺少变量时报 ``Error: All variables must be provided. Missing: [...]`` 并列出可用变量名。被拒绝的位置报 ``Initialization failed: <message>``，消息见上文的表。
   * - ``events``
     - 列出对各活动叶子来说照原样输入就有效的事件。两个叶子用于不同事件的短名不会列出；祖先、拥有者或区域上的事件以完整路径列出。
   * - ``cycle [count] [events...] [--input name=value ...]``
     - 每个周期都要给完整的输入向量：每个输入变量一个 ``--input``。事件名被拒绝时报 ``Cycle execution failed: ...``，文本见上文的表。
   * - ``history``、``export``
     - ``state`` 列与字段是配置文本。
   * - 补全
     - ``init`` 会补全区域里的状态；``cycle`` 只补全照原样输入就能解析的名字。

.. literalinclude:: region_simulate_cli.demo.sh.txt
   :language: text

第一块对控制器做热启动，显示该位置下 ``events`` 只列出 ``Controller.Stop``，以及故障使电机在看到它的那个周期关断。第二块展示点路径写法：``Safety`` 以 ``[init]`` 等待，在第一个周期启动。
第三块展示导出文件里的位置。这三块的退出状态都是 0。随后是被拒绝的命令及其退出状态：每条被拒绝的命令都会停止批处理并返回状态 1。

.. literalinclude:: region_simulate_cli.demox.sh.txt
   :language: text

Python 运行时应用程序接口
------------------------------

.. list-table:: 主要运行时表面
   :header-rows: 1

   * - 表面
     - 用途和边界
   * - ``SimulationRuntime(state_machine, abstract_error_mode='raise', history_size=None, initial_state=None, initial_vars=None)``
     - 创建运行时。默认启动模式可接受部分 ``initial_vars``；热启动要求提供每个声明过的持久变量。
       ``history_size=None``\ 表示历史不设上限，而 ``history_size=0``\ 表示不保留历史记录。
   * - ``cycle(events=None, *, trace=False, inputs=None, diagnostics=False) -> CycleResult``
     - 执行一个周期，验证候选路径，提交或回滚，并记录历史。
   * - ``CycleResult.value``
     - 兼容旧行为的返回值；当前为 ``None``。
   * - ``CycleResult.input_events``
     - 本周期提供的规范事件路径，按归一化输入顺序排列。
   * - ``CycleResult.consumed_events``
     - 本周期实际执行的事件转换对应的规范事件路径。
   * - ``CycleResult.unconsumed_events``
     - 已提供但没有对应已执行事件转换的规范事件路径。
   * - ``CycleResult.delta``
     - 成功但没有可提交后继时为 ``True``；普通成功、错误和已结束空操作为 ``False``。
   * - ``CycleResult.trace``
     - ``trace=True`` 时返回不可变执行记录组成的元组；默认关闭。
       Delta 和被忽略的调用也返回空元组。异常不会返回结果或部分执行迹。
   * - ``vars`` / ``cycle_count`` / ``history`` / ``history_size``
     - 命令显示、测试和工具使用的公开运行时状态。命令层 ``history_size`` 设置会把 ``0`` 映射为运行时
       ``None``；直接编写运行时代码时，需要传入 ``None`` 来表示历史不设上限。
   * - ``configuration``
     - 停驻位置的不可变 :class:`pyfcstm.model.Configuration`，所有模型都可用；见 :ref:`sim-region-position-api-zh`。
   * - ``current_state``
     - 当前活动状态。可能已经结束时先检查 ``is_ended``；结束后访问会抛出 :class:`pyfcstm.simulate.SimulationRuntimeTerminalStateError`。含区域的模型返回 ``Configuration``，而不是 ``State``。
   * - ``brief_stack``
     - 终止安全的栈摘要，形状为 ``(state_path, mode)`` 元组列表。含区域的模型上抛出 ``SimulationRuntimeRegionQueryError``。
   * - ``is_ended``
     - 运行时终止后为 ``True``。之后调用 ``cycle()`` 不再推进。
   * - ``is_error_state`` / ``error_info`` / ``abstract_handler_errors``
     - 抽象处理器诊断状态。
   * - ``register_abstract_handler`` / ``unregister_abstract_handler``
     - 管理命名抽象动作的处理器。
   * - ``clear_abstract_handler_session`` / ``clear_all_abstract_handlers``
     - 清除处理器和相关诊断。
   * - ``get_abstract_handlers`` / ``has_abstract_handlers``
     - 查看处理器注册状态。
   * - ``register_handlers_from_object``
     - 注册使用 ``@abstract_handler`` 标记的对象方法。
   * - ``ReadOnlyExecutionContext``
     - 不可变处理器上下文，暴露状态路径、变量快照、动作元数据、活跃叶状态、抽象目标和命名引用元数据。
       ``active_leaf`` 是动作执行时的运行时状态路径：存在活跃叶状态时为该叶状态，否则为该动作的
       宿主状态路径——进入复合状态时报告的就是宿主路径。区域周围的动作见 :ref:`sim-region-position-api-zh`；上下文还带有 ``configuration``，即调用那一刻的完整位置。
   * - ``abstract_handler(action_path)``
     - 装饰器，用于标记可批量注册的对象方法。

已提交执行迹
------------

``runtime.cycle(trace=True)`` 只收集本次调用的执行记录。
推测性验证、被拒绝的候选迁移和已回滚的 Delta 尝试不会进入结果。
后续调用仍需显式开启；``history`` 和命令行 ``export`` 的字段不变。
保留返回的 ``CycleResult`` 即可保留执行迹，它不受 ``history_size`` 限制。
``trace`` 是只能按名称传入的布尔参数，默认 ``False``。
开启后，每条记录都会保存一份持久变量快照；收集过程不读写文件。

.. list-table:: ``ExecutionTraceEntry`` 字段
   :header-rows: 1

   * - 字段
     - 含义与边界
   * - ``kind``
     - ``Literal["state_enter", "state_exit", "transition", "action"]``：
       ``state_enter`` 在进入动作前记录；``state_exit`` 在退出动作后记录；
       ``transition`` 在迁移效果执行后记录；``action`` 在操作块或抽象动作分派完成后记录。
       条目按执行顺序排列，包括伪状态链。
   * - ``state_path``
     - 字符串元组：进入或退出的状态、迁移源状态（初始迁移取所属复合状态），或动作执行位置的不可变路径。
       祖先切面动作记录其实际作用的后代状态位置。
   * - ``vars``
     - 变量名到 ``int``/``float`` 值的只读映射，不含局部临时变量；后续周期不会改变此快照。
   * - ``transition_label``
     - 与 BMC 标签格式一致的 ``source_path::index::source->target``；其他条目为 ``None``。
       从零开始的索引对应源状态的初始迁移或出边列表。
       初始源使用 ``INIT_STATE``，退出目标使用 ``[*]``，合成根退出的索引为零。
       强制转换和组合转换使用展开后的模型边地址，包括组合转换的中继状态。
       这些地址仅对当前模型有效，编辑模型或调整声明顺序后不能继续当作稳定标识。
   * - ``action_path`` / ``resolved_action_path``
     - 调用位置与最终 ``ref`` 目标，格式为 ``state::collection::index``；其他条目为 ``None``。
       集合名称为 ``on_enters``、``on_durings``、``on_exits`` 或 ``on_during_aspects``。
       从零开始的索引可区分匿名动作。地址对应当前模型，导出执行迹时应同时保存该模型。
   * - ``to_dict()``
     - 返回独立字典，其中路径为列表、变量为字典，可交给 JSON/YAML 序列化。
       修改导出字典不会改变原条目。
   * - ``str(entry)`` / ``print(entry)``
     - 返回便于阅读的单行摘要，包含操作、状态、适用的迁移或动作地址、与调用位置不同的最终引用目标，
       以及按名称排序的变量。大整数以位数简写显示。``repr(entry)`` 保留数据类的表示形式；
       程序需要完整数值时使用 ``to_dict()``。

下面的完整示例区分迁移效果和目标进入动作：迁移记录看到 ``x == 1``，
随后的动作记录看到 ``x == 2``：

.. code-block:: pycon

    >>> import json
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> model = load_state_machine_from_text('''
    ... def int x = 0;
    ... state Root {
    ...     state Idle;
    ...     state Done { enter { x = x + 1; } }
    ...     [*] -> Idle;
    ...     Idle -> Done :: Go effect { x = x + 1; };
    ... }
    ... ''')
    >>> runtime = SimulationRuntime(model, history_size=0)
    >>> _ = runtime.cycle()
    >>> result = runtime.cycle('Root.Idle.Go', trace=True)
    >>> [(entry.kind, entry.vars['x']) for entry in result.trace]
    [('state_exit', 0), ('transition', 1), ('state_enter', 1), ('action', 2)]
    >>> payload = json.dumps([entry.to_dict() for entry in result.trace])
    >>> json.loads(payload)[1]['transition_label']
    'Root.Idle::0::Idle->Done'
    >>> runtime.history
    []
    >>> for entry in result.trace:
    ...     print(entry)
    State exit Root.Idle | vars={x=0}
    Transition Root.Idle | transition=Root.Idle::0::Idle->Done | vars={x=1}
    State enter Root.Done | vars={x=1}
    Action Root.Done | action=Root.Done::on_enters::0 | vars={x=2}

空执行迹本身不代表 Delta 或终止。稳定状态没有周期动作，也没有可执行迁移时，
这一拍不执行需要记录的操作：

.. code-block:: pycon

    >>> idle = runtime.cycle(trace=True)
    >>> (idle.delta, idle.trace, runtime.is_ended)
    (False, (), False)

快照不能原地修改；需要编辑数据时先调用 ``to_dict()``。
``trace`` 必须按名称传入，不能作为第二个位置参数：

.. code-block:: pycon

    >>> result.trace[-1].vars['x'] = 9
    Traceback (most recent call last):
        ...
    TypeError: 'mappingproxy' object does not support item assignment
    >>> runtime.cycle(None, True)
    Traceback (most recent call last):
        ...
    TypeError: ...

该接口序列化的是条目，不是自包含的回放文件。保存记录时，调用者还需保留模型、
周期编号、输入事件和观察约定；命令行 ``export`` 仍然导出宏步历史。

抽象动作的 ``action`` 条目表示执行到该分派位置，不要求存在已注册处理器。
``abstract_error_mode='log'`` 也允许处理器报错后继续完成周期；此类错误需要查看
``abstract_handler_errors``。热启动只记录后续周期实际执行的工作，不补记构造时跳过的进入动作。

完整可运行示例见 :meth:`pyfcstm.simulate.runtime.SimulationRuntime.cycle`。
``test/simulate/test_execution_trace.py`` 核对执行顺序、快照、引用、候选拒绝、
Delta、异常、中断、热启动，以及伪状态、强制转换和组合转换链。
``test/simulate/test_execution_trace_semantic_fixtures.py`` 在全部可运行的共享仿真样例上
对照开启执行迹与普通执行；``test/bmc/test_execution_trace_alignment.py``
对照公开的有界模型检查展开接口，验证边地址一致。

公开失败和边界
--------------

.. list-table:: 失败表面
   :header-rows: 1

   * - 失败
     - 出现位置
     - 含义
   * - 构造或热启动中的 ``ValueError``
     - Python 应用程序接口和 ``init`` 命令信息
     - 错误模式非法、未知变量、缺少热启动变量、状态路径无法解析，或持久值类型非法。含区域模型的位置还包括：把区域当作位置、未知条目、重复的区域、位置文本有误、任一层拥有者的区域全体已完成、
       另一个模型的 ``Configuration`` 或 ``State``\ （文本见 :ref:`sim-region-hot-start-zh`）；位置的类型不对时抛出 ``TypeError``。
   * - ``SimulationRuntimeEventError``
     - Python 应用程序接口；命令层显示 ``Cycle execution failed: ...``
     - 事件输入不受支持、无法解析，或来自外部状态机。
   * - ``SimulationRuntimeDfsError``
     - Python 应用程序接口；命令层显示无界执行链信息
     - 所有候选都无法稳定，且验证发现同一周期内重复的执行路径；
       或者搜索超过 DFS 步数、栈深度安全限制。
       循环错误包含状态路径与修复建议。若后续候选可以到达可停止状态或终止，
       则跳过循环候选，继续执行合法候选。
   * - ``SimulationRuntimeRegionQueryError``
     - Python 应用程序接口的 ``brief_stack``
     - 模型含区域，单条栈无法描述它；请使用 ``configuration``。
   * - ``SimulationRuntimeTerminalStateError``
     - 终止后访问 Python 应用程序接口的 ``current_state``
     - 运行时已结束，活动栈为空。
   * - ``SimulationRuntimeExpressionError``
     - Python 应用程序接口；命令层显示 ``Cycle execution failed: ...``
     - guard 或动作表达式的运行时求值失败。
   * - ``SimulationRuntimeActionReferenceError``
     - Python 应用程序接口
     - 命名动作引用无法解析或无法安全执行。
   * - 抽象处理器异常
     - Python 应用程序接口
     - 在 ``abstract_error_mode='raise'`` 时，运行时进入错误状态并抛出；在 ``'log'`` 模式下，错误会收集到 ``abstract_handler_errors``。
   * - 不支持的导出后缀或文件错误
     - 命令层
     - ``export`` 返回一条信息；它不是 Python 运行时方法。

事实源
------

本参考与以下实现和测试事实对齐：

* ``pyfcstm/entry/simulate/__init__.py``：Click 选项和解析失败处理。
* ``pyfcstm/entry/simulate/batch.py`` 与 ``commands.py``：批处理和交互命令行为。
* ``pyfcstm/simulate/runtime.py``、``context.py`` 和 ``decorators.py``：Python 应用程序接口表面。
* ``test/fixtures/simulate_semantics/cases/`` 与 ``test/testings/simulate_semantics.py``：执行顺序场景。
* ``docs/source/tutorials/simulation/*.demo.*``：文档中已检查的命令转录。

.. toctree::
   :maxdepth: 1

   inputs_zh

候选决策诊断
--------------------------------

排查迁移为何未执行，见 :doc:`diagnostics_zh`；其中包含 Python 采集、交互查询、逐拍输入和 JSONL 示例。
