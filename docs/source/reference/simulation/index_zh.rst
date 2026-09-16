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

解码、语法、语义建模失败会写到 stderr，形如 ``Failed to parse DSL file: ...``。批处理和交互命令失败通常返回用户可见信息，而不是让异常穿透 CLI 进程。

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
   * - ``init <state_path> [var=value...]``
     - 目标状态和数值变量赋值。
     - 把运行时重建为热启动状态。必须提供每个声明过的变量。数值支持十进制、十六进制、二进制、浮点和科学计数法。
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

Python 运行时应用程序接口
------------------------------

.. list-table:: 主要运行时表面
   :header-rows: 1

   * - 表面
     - 用途和边界
   * - ``SimulationRuntime(state_machine, abstract_error_mode='raise', history_size=None, initial_state=None, initial_vars=None)``
     - 创建运行时。默认启动模式可接受部分 ``initial_vars``；热启动要求提供每个声明过的持久变量。
       ``history_size=None``\ 表示历史不设上限，而 ``history_size=0``\ 表示不保留历史记录。
   * - ``cycle(events=None, *, trace=False) -> CycleResult``
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
   * - ``current_state``
     - 当前活动状态。可能已经结束时先检查 ``is_ended``；结束后访问会抛出 :class:`pyfcstm.simulate.SimulationRuntimeTerminalStateError`。
   * - ``brief_stack``
     - 终止安全的栈摘要，形状为 ``(state_path, mode)`` 元组列表。
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
       宿主状态路径——进入复合状态时报告的就是宿主路径。
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
     - 错误模式非法、未知变量、缺少热启动变量、状态路径无法解析，或持久值类型非法。
   * - ``SimulationRuntimeEventError``
     - Python 应用程序接口；命令层显示 ``Cycle execution failed: ...``
     - 事件输入不受支持、无法解析，或来自外部状态机。
   * - ``SimulationRuntimeDfsError``
     - Python 应用程序接口；命令层显示无界执行链信息
     - 推测性验证在寻找可停止状态或终止时超过 DFS 或栈深度安全限制。
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
