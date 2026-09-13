动态输入源
==========

四种变量具有不同的所有权和生命周期。``control`` 和 ``output`` 在
``runtime.vars`` 中跨拍保存；output 本拍未赋值时保持原值。``param`` 在构造时固定，
通过只读的 ``runtime.parameters`` 访问。``input`` 由环境逐拍提供。参数和输入不会进入
可写的持久变量存储，声明的 initializer 仍然不能引用变量。

构造与逐拍覆盖
--------------

.. code-block:: python

    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate import SimulationRuntime, SequenceInput

    model = parse_dsl_node_to_state_machine(parse_with_grammar_entry('''
        input float pressure;
        param float gain = 2.0;
        output float reading = 0.0;
        state Root {
            state Running { during { reading = pressure * gain; } }
            [*] -> Running;
        }
    ''', 'state_machine_dsl'))
    runtime = SimulationRuntime(
        model,
        parameters={'gain': 3.0},
        input_source={'pressure': SequenceInput([70.0, 80.0, 90.0])},
    )
    first = runtime.cycle()
    second = runtime.cycle(inputs={'pressure': 75.0})
    third = runtime.cycle()
    assert [first.inputs['pressure'], second.inputs['pressure'],
            third.inputs['pressure']] == [70.0, 75.0, 90.0]
    assert runtime.outputs['reading'] == 270.0

构造只验证 source 是否完整、名称和接口是否合法，不调用 ``get()`` 或 ``cycle()``。
冷启动先解析 parameter override/default，再初始化持久变量。热启动必须提供完整
``parameters`` 和 ``initial_vars``，不重新执行 initializer。两种启动方式都在第一次
实际 cycle 才读取第零拍。

``inputs`` 只覆盖当前调用。即使全部输入被覆盖，runtime 仍读取所有绑定 source，
并在成功周期后推进一次。因此 override 不能掩盖 source 耗尽或读取失败；确定性回放应
使用 replay source。非法 override 和事件参数在采样前拒绝。int 输入只接受整数，
不接受 bool；float 输入接受整数和有限浮点数，不接受 NaN 或无穷值。

自定义生成器
------------

公开接口 ``ScalarInputPattern`` 和 ``IntegratedInputPattern`` 都要求
``get()`` 和 ``cycle()``。第三方对象可以直接满足接口，无须继承。integrated source
还必须提供不可变的 ``input_names`` 元组，与模型声明顺序完全一致。每次返回的 mapping
必须含有全部且仅有这些名称，其插入顺序由 runtime 归一化。

新生成器可以继承带缓存的基类：

.. code-block:: python

    from pyfcstm.simulate import BaseScalarInputPattern

    class PressureRamp(BaseScalarInputPattern):
        def __init__(self, start, increment):
            super().__init__()
            self.start = start
            self.increment = increment

        def _sample(self, step):
            return self.start + self.increment * step

    source = PressureRamp(70.0, 5.0)
    assert source.get() == source.get() == 70.0
    source.cycle()  # A bound source is advanced by its runtime instead.
    assert source.get() == 75.0

``BaseIntegratedInputPattern(input_names=(...))`` 的 ``_sample(step)`` 返回完整
mapping，基类会复制并冻结结果。两个基类都缓存当前拍成功的采样；采样失败时不推进，
下一次可重试同一拍。采样不能不可逆地消费外部流。``cycle()`` 只推进索引、使缓存失效，
不读取下一拍，也不做 I/O。

每个 runtime 使用独立的 source 实例。同一个 scalar 实例不能绑定多个输入，相关输入应
使用 integrated source。source 绑定后不可由调用者自行推进。runtime/source 是串行、
不可重入对象。不会暗中向 provider 注入 runtime 或 output 上下文；闭环 plant wiring
不属于这个接口。

内置模式
--------

* ``ConstantIntInput``、``ConstantFloatInput``：类型明确的常量。
  source mapping 中的数值字面量会自动包装为常量。
* ``SequenceInput(values, end='error')``：构造时复制并验证序列。
  ``hold`` 保持最后值，``loop`` 循环。空序列只允许 ``error``；耗尽发生在下一次
  ``get()``，不能由 ``cycle()`` 报错。
* ``UniformIntInput(low, high, seed=...)``：两端包含的均匀整数分布。
  ``UniformFloatInput`` 使用有限浮点边界。
* ``NormalFloatInput(mean, stddev, seed=...)``、``NormalIntInput``：每个实例独立 RNG，
  标准差必须非负。整数模式必须明确指定 ``rounding='round'``、``'floor'``、
  ``'ceil'`` 或 ``'trunc'``；``round`` 使用 ties-to-even。
* ``CallableInput(sample)``：延迟调用 ``sample(step)`` 并缓存。
  ``IntegratedCallableInput(sample, input_names=(...))`` 返回完整向量，构造时不会
  通过预调用推断名称。
* ``IntegratedSequenceInput``：复制并验证所有向量，名称显式提供或从第一项推断；
  空序列必须明确名称。
* ``ReplayInputPattern(snapshots, input_names=(...))``：确定性的有限向量序列，
  耗尽时报错。

提交和失败边界
--------------

一拍只冻结一个输入向量，validation 和 committed 两遍执行共用它。guard、operation、
嵌套分支、生命周期和 abstract context 都读取同一拍。runtime 先准备状态、history、
result 等数据，再推进 source，最后发布准备好的运行边界。

.. list-table:: 周期结果
   :header-rows: 1

   * - 结果
     - source 推进
     - 可观察的 runtime 边界
   * - 成功、Delta、当轮终止
     - 每个 provider 恰好一次
     - cycle count、history、last inputs 一起提交；Delta 保持拍前机器状态。
   * - 非法事件或 override
     - 不读取、不推进
     - 不变。
   * - 读取、类型或运行时执行错误
     - 不推进
     - 丢弃候选状态和输入；健康 source 可重试当前索引，runtime 错误沿用原有契约。
   * - handler 在 raise 模式抛错
     - 不推进
     - 进入已有 error-state，后续调用 no-op。
   * - 已 ended/error
     - 不读取、不推进
     - 不追加 history，不替换输入快照。
   * - 自定义 provider 在推进时抛错
     - 更早的 provider 可能已推进
     - 不提交机器边界；永久 ``input_source_error`` 阻止后续 provider 调用，必须重建。

``SimulationRuntimeInputSourceError.code`` 提供可区分的错误类别：
``E_INPUT_SOURCE_READ`` 保留原始读取异常为 cause；``E_INPUT_SOURCE_TYPE`` 表示数值
不合法；``E_INPUT_SOURCE_MISSING`` / ``E_INPUT_SOURCE_UNKNOWN`` 表示名称缺失或多余；
``E_INPUT_SOURCE_CONTRACT`` 表示协议不合法或推进违反契约。

abstract handler 和外部 observer 的副作用无法回滚，必须能够容忍失败的执行尝试；
这里不承诺设备 I/O 回滚或分布式事务。

观察面与 CLI
------------

``CycleResult.inputs``、``runtime.last_inputs`` 是复制后的只读快照。
第一次 committed cycle 前 ``last_inputs`` 为 ``None``；no-op 返回空 result inputs，
但保留上次 ``last_inputs``。含 dynamic input 的模型会在 history 项中记录 ``inputs``。
``history_size`` 仅接受 ``None`` 或非负整数，零表示不保留 history。

``ReadOnlyExecutionContext.inputs``、``.parameters`` 与持久 ``.vars`` 分开。
trace 条目保留这些角色分区，``to_dict()`` 输出非空 inputs/parameters。
``runtime.control_variables``、``runtime.outputs`` 提供只读投影。

CLI 当前没有 provider 绑定参数，带 dynamic input 的模型应使用 Python API；CLI 会报告
缺少 source。围绕此类 runtime 创建的 REPL 会拒绝 ``init``/``clear``，避免复用已推进的
source。只有参数的模型在 REPL 重建时保留当前 parameters。
