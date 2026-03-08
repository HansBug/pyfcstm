FCSTM 仿真指南
===============================================

本指南介绍如何在 Python 中仿真 FCSTM 状态机。仿真运行时提供了一个交互式执行环境，用于在代码生成之前测试、原型设计和理解状态机行为。

核心概念
---------------------------------------

在深入使用之前，请理解这些关键概念：

**状态类型**

- **叶状态**：没有子状态的状态（可以执行 ``during`` 动作）
- **复合状态**：包含子状态的状态（需要初始转换）
- **伪状态**：跳过祖先切面动作的特殊叶状态
- **可停止状态**：一个周期可以结束的叶状态（非伪状态）

**生命周期动作**

- **enter**：进入状态时执行
- **during**：保持在状态中时执行（每个周期）
- **exit**：离开状态时执行

**切面动作**

- **>> during before/after**：应用于所有后代叶状态的横切动作
- 伪状态跳过祖先切面动作

**复合状态动作**

- **during before**（不带 ``>>``）：从父状态进入复合状态时执行（``[*] -> Child``）
- **during after**（不带 ``>>``）：从复合状态退出到父状态时执行（``Child -> [*]``）
- **不执行**：在子状态到子状态的转换期间（``Child1 -> Child2``）

Python 用法
---------------------------------------

创建和运行仿真
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

基本工作流程：

1. 将 DSL 代码解析为 AST
2. 将 AST 转换为状态机模型
3. 创建 ``SimulationRuntime`` 实例
4. 使用 ``runtime.cycle()`` 执行周期

.. literalinclude:: basic_usage.demo.py
   :language: python
   :caption: 基本仿真示例

输出：

.. literalinclude:: basic_usage.demo.py.txt
   :language: text

**关键 API**：

- ``runtime.cycle()``：执行一个完整的周期
- ``runtime.current_state``：获取当前状态对象（使用 ``.path`` 获取元组或 ``'.'.join(.path)`` 获取字符串）
- ``runtime.vars``：以字典形式访问/修改变量
- ``runtime.is_terminated``：检查状态机是否已终止

触发事件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

将事件名称传递给 ``cycle()`` 以触发转换：

.. literalinclude:: event_triggering.demo.py
   :language: python
   :caption: 事件触发

输出：

.. literalinclude:: event_triggering.demo.py.txt
   :language: text

**事件作用域**：

- ``::`` 创建局部事件（作用域为源状态）
- ``:`` 创建链式事件（作用域为父状态）
- ``/`` 创建绝对事件（作用域为根状态）

实现抽象处理器
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 ``@abstract_handler`` 装饰器实现自定义逻辑：

.. literalinclude:: abstract_handlers.demo.py
   :language: python
   :caption: 抽象动作处理器

输出：

.. literalinclude:: abstract_handlers.demo.py.txt
   :language: text

**处理器上下文 API**：

.. code-block:: python

   @abstract_handler('System.Active.Monitor')
   def handle_monitor(self, ctx):
       # 获取当前状态路径
       state_path = ctx.get_full_state_path()

       # 访问/修改变量
       counter = ctx.get_var('counter')
       ctx.set_var('counter', counter + 1)

       # 获取状态对象
       state = ctx.get_state()

       # 访问运行时
       runtime = ctx.get_runtime()

执行语义
---------------------------------------

理解状态机如何执行对于构建正确的行为至关重要。本节提供详细的示例和逐步执行跟踪。

周期执行
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

一个 **周期** 执行直到达到稳定边界：

- 跟随转换链直到到达可停止状态（叶状态，非伪状态）
- 在最终可停止状态执行 ``during`` 动作
- 一个周期可能执行多个转换（例如，通过伪状态）
- 如果没有转换触发，执行当前状态的 ``during`` 动作

示例 1：基本转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example1_basic.fcstm
   :language: fcstm
   :caption: 基本状态转换

.. figure:: example1_basic.fcstm.puml.svg
   :align: center

   状态机图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 20 12 40

   * - 周期
     - 事件
     - 状态
     - counter
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，然后执行 ``A.during`` (counter + 1)
   * - 2
     - *(无)*
     - Root.A
     - 2
     - 无事件，保持在 A，执行 ``A.during`` (counter + 1)
   * - 3
     - ``Go``
     - Root.B
     - 12
     - 事件 ``Go`` 触发 ``A -> B``，然后执行 ``B.during`` (counter + 10)

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``
- 执行初始转换 ``[*] -> A``
- 执行 ``A.enter``（未定义）
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果**：``state = Root.A``，``counter = 1``

**周期 2**（无事件）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: Go``（需要事件，未触发）
- 没有转换触发
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果**：``state = Root.A``，``counter = 2``

**周期 3**（带事件 ``Go``）：

- 当前状态：``Root.A``，``counter = 2``
- 检查转换：``A -> B :: Go``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行转换（无效果）
- 执行 ``B.enter``（未定义）
- 到达可停止状态 ``B``
- 执行 ``B.during``：``counter = 2 + 10 = 12``
- **结果**：``state = Root.B``，``counter = 12``

示例 2：带初始转换的复合状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example2_composite.fcstm
   :language: fcstm
   :caption: 带嵌套状态的复合状态

.. figure:: example2_composite.fcstm.puml.svg
   :align: center

   复合状态图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 22 12 38

   * - 周期
     - 事件
     - 状态
     - counter
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，执行 ``A.during`` (counter + 1)
   * - 2
     - ``GoB``
     - Root.B.B1
     - 11
     - 事件 ``GoB`` 触发 ``A -> B``，跟随 ``[*] -> B1``，执行 ``B1.during`` (counter + 10)
   * - 3
     - ``Next``
     - Root.B.B2
     - 111
     - 事件 ``Next`` 触发 ``B1 -> B2``，执行 ``B2.during`` (counter + 100)

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果**：``state = Root.A``，``counter = 1``

**周期 2**（带事件 ``GoB``）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``B.enter``（未定义）
- **B 是复合状态** - 必须跟随初始转换
- 执行 ``[*] -> B1``（在 B 内部）
- 执行 ``B1.enter``（未定义）
- 到达可停止状态 ``B1``
- 执行 ``B1.during``：``counter = 1 + 10 = 11``
- **结果**：``state = Root.B.B1``，``counter = 11``

**关键点**：当转换到复合状态时，周期继续跟随初始转换直到到达可停止状态。

**周期 3**（带事件 ``Next``）：

- 当前状态：``Root.B.B1``，``counter = 11``
- 检查转换：``B1 -> B2 :: Next``（事件匹配！）
- 执行 ``B1.exit``（未定义）
- 执行 ``B2.enter``（未定义）
- 到达可停止状态 ``B2``
- 执行 ``B2.during``：``counter = 11 + 100 = 111``
- **结果**：``state = Root.B.B2``，``counter = 111``

示例 3：切面动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example3_aspect.fcstm
   :language: fcstm
   :caption: 带执行顺序的切面动作

.. figure:: example3_aspect.fcstm.puml.svg
   :align: center

   切面动作图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 20 12 40

   * - 周期
     - 事件
     - 状态
     - trace
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - Root.A
     - 123
     - 初始转换 ``[*] -> A``，执行：before (×10+1=1) → during (×10+2=12) → after (×10+3=123)
   * - 2
     - *(无)*
     - Root.A
     - 123123
     - 无事件，执行：before (×10+1=1231) → during (×10+2=12312) → after (×10+3=123123)

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``trace = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 during 阶段：
  1. ``Root >> during before``：``trace = 0 * 10 + 1 = 1``
  2. ``A.during``：``trace = 1 * 10 + 2 = 12``
  3. ``Root >> during after``：``trace = 12 * 10 + 3 = 123``
- **结果**：``state = Root.A``，``trace = 123``

**周期 2**（无事件）：

- 当前状态：``Root.A``，``trace = 123``
- 没有转换触发
- 执行 during 阶段：
  1. ``Root >> during before``：``trace = 123 * 10 + 1 = 1231``
  2. ``A.during``：``trace = 1231 * 10 + 2 = 12312``
  3. ``Root >> during after``：``trace = 12312 * 10 + 3 = 123123``
- **结果**：``state = Root.A``，``trace = 123123``

**关键点**：切面动作（``>> during before/after``）按层次顺序在叶状态的 ``during`` 动作周围执行，形成三明治模式：before → during → after。

示例 4：伪状态（跳过切面动作）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example4_pseudo.fcstm
   :language: fcstm
   :caption: 伪状态跳过切面动作

.. figure:: example4_pseudo.fcstm.puml.svg
   :align: center

   伪状态图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 22 12 38

   * - 周期
     - 事件
     - 状态
     - trace
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - *(已终止)*
     - 2
     - 初始转换 ``[*] -> A``，伪状态跳过切面动作，执行 ``A.during`` (×10+2=2)，守卫满足，转换到 ``[*]``

**详细执行跟踪**：

**周期 1**（初始化和终止）：

- 初始状态：``trace = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``（伪状态）
- **伪状态跳过切面动作！**
- 执行 during 阶段：
  - ``Root >> during before`` **跳过**
  - ``A.during``：``trace = 0 * 10 + 2 = 2``
  - ``Root >> during after`` **跳过**
- 检查转换：``A -> [*] : if [trace >= 2]``（守卫满足！）
- 执行 ``A.exit``（未定义）
- 转换到最终状态
- **结果**：``state = terminated``，``trace = 2``

**关键点**：伪状态跳过所有祖先切面动作，只执行自己的 ``during`` 动作。这对于不应触发横切关注点的中间状态很有用。

示例 5：多层复合状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example5_multilevel.fcstm
   :language: fcstm
   :caption: 多层嵌套复合状态

.. figure:: example5_multilevel.fcstm.puml.svg
   :align: center

   多层复合状态图

**执行摘要（场景 1：A → B）**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 25 12 35

   * - 周期
     - 事件
     - 状态
     - counter
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，执行 ``A.during`` (counter + 1)
   * - 2
     - ``GoB``
     - Root.B.B1.B1a
     - 11
     - 事件 ``GoB`` 触发 ``A -> B``，跟随 ``[*] -> B1`` 然后 ``[*] -> B1a``，执行 ``B1a.during`` (counter + 10)

**执行摘要（场景 2：A → C）**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 25 12 35

   * - 周期
     - 事件
     - 状态
     - counter
     - 原因
   * - 0
     - *(无)*
     - *(初始)*
     - 0
     - 初始变量值
   * - 1
     - *(无)*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，执行 ``A.during`` (counter + 1)
   * - 2
     - ``GoC``
     - Root.C
     - 101
     - 事件 ``GoC`` 触发 ``A -> C``，执行 ``C.during`` (counter + 100)

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果**：``state = Root.A``，``counter = 1``

**周期 2**（带事件 ``GoB``）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``B.enter``（未定义）
- **B 是复合状态** - 跟随 ``[*] -> B1``
- 执行 ``B1.enter``（未定义）
- **B1 也是复合状态** - 跟随 ``[*] -> B1a``
- 执行 ``B1a.enter``（未定义）
- 到达可停止状态 ``B1a``
- 执行 ``B1a.during``：``counter = 1 + 10 = 11``
- **结果**：``state = Root.B.B1.B1a``，``counter = 11``

**关键点**：单个周期可以通过跟随初始转换链遍历多层复合状态，直到到达可停止的叶状态。

**周期 3**（从初始状态带事件 ``GoC``）：

- 重新开始：``counter = 0``
- 执行 ``[*] -> A``
- 执行 ``A.during``：``counter = 1``
- 下一个周期带事件 ``GoC``：
- 检查转换：``A -> C :: GoC``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``C.enter``（未定义）
- 到达可停止状态 ``C``
- 执行 ``C.during``：``counter = 1 + 100 = 101``
- **结果**：``state = Root.C``，``counter = 101``

层次执行顺序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

理解嵌套状态中的执行顺序至关重要：

.. literalinclude:: hierarchy_execution.demo.py
   :language: python
   :caption: 层次执行

输出：

.. literalinclude:: hierarchy_execution.demo.py.txt
   :language: text

**完整执行顺序**：

**进入阶段**（从父状态）：

1. ``State.enter``
2. ``State.during before``（如果通过 ``[*] -> Child`` 进入）
3. ``Child.enter``

**During 阶段**（叶状态的每个周期）：

1. 祖先 ``>> during before`` 动作（从根到叶）
2. 叶状态 ``during`` 动作
3. 祖先 ``>> during after`` 动作（从叶到根）

**退出阶段**（到父状态）：

1. ``Child.exit``
2. ``State.during after``（如果通过 ``Child -> [*]`` 退出）
3. ``State.exit``

**子状态到子状态的转换**：

1. ``Child1.exit``
2. （转换效果）
3. ``Child2.enter``
4. 不执行 ``during before/after``

**关键点**：

- 切面动作（``>> during before/after``）在所有后代叶状态的 ``during`` 阶段执行
- 复合状态动作（``during before/after`` 不带 ``>>``）只在进入/退出转换期间执行，而不是在 ``during`` 阶段
- 伪状态跳过祖先切面动作

最佳实践
---------------------------------------

状态机设计
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 保持状态专注，具有明确的单一职责
- 使用层次状态将相关状态分组
- 最小化切面动作 - 谨慎用于横切关注点
- 用注释记录抽象动作

测试和调试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 测试初始化、所有转换、守卫、效果和终止
- 每个周期后打印状态和变量以进行调试
- 使用抽象处理器跟踪执行
- 使用 ``runtime.get_current_state_object()`` 检查状态对象

处理器实现
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 保持处理器简单且专注
- 避免副作用 - 最小化外部状态修改
- 使用上下文 API 访问运行时状态
- 添加日志以调试复杂交互

性能
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 限制周期数以避免无限循环
- 保持守卫表达式简单以加快评估
- 最小化切面动作（它们每个周期都执行）
- 使用伪状态在不需要时跳过切面动作

常见陷阱
---------------------------------------

**切面动作混淆**

问题：期望 ``during before/after``（不带 ``>>``）在 ``during`` 阶段执行。

解决方案：记住复合状态的 ``during before/after`` 只在进入/退出转换期间执行（``[*] -> Child`` 或 ``Child -> [*]``），而不是在 ``during`` 阶段。

**事件作用域问题**

问题：由于作用域不正确，事件未触发。

解决方案：理解事件作用域 - ``::`` 创建状态特定的事件，``:`` 创建父作用域的事件，``/`` 创建根作用域的事件。

**变量初始化**

问题：变量在使用前未初始化。

解决方案：始终在 DSL 顶部定义带初始值的变量：

.. code-block:: fcstm

   def int counter = 0;
   def float temperature = 25.0;

**缺少抽象处理器**

问题：抽象动作已声明但未实现，导致运行时错误。

解决方案：在运行仿真之前实现所有抽象处理器，并使用 ``runtime.register_handlers_from_object(handlers)`` 注册它们。

总结
---------------------------------------

仿真运行时为测试和理解 FCSTM 状态机提供了强大的环境：

- **核心概念**：状态类型、生命周期动作、切面动作、执行语义
- **Python 用法**：创建运行时、执行周期、触发事件、实现处理器
- **执行语义**：周期执行、层次执行顺序
- **最佳实践**：设计、测试、调试、性能优化

更多信息，请探索：

- :doc:`../visualization/index` - 可视化状态机
- :doc:`../dsl/index` - 高级 DSL 特性
- :doc:`../render/index` - 从状态机生成代码
