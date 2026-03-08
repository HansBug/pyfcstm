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

.. literalinclude:: example1_basic.full.fcstm
   :language: fcstm
   :caption: 基本状态转换

.. figure:: example1_basic.full.fcstm.puml.svg
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

.. literalinclude:: example2_composite.full.fcstm
   :language: fcstm
   :caption: 带嵌套状态的复合状态

.. figure:: example2_composite.full.fcstm.puml.svg
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

.. literalinclude:: example3_aspect.full.fcstm
   :language: fcstm
   :caption: 带执行顺序的切面动作

.. figure:: example3_aspect.full.fcstm.puml.svg
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

.. literalinclude:: example4_pseudo.full.fcstm
   :language: fcstm
   :caption: 伪状态跳过切面动作

.. figure:: example4_pseudo.full.fcstm.puml.svg
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

.. literalinclude:: example5_multilevel.full.fcstm
   :language: fcstm
   :caption: 多层嵌套复合状态

.. figure:: example5_multilevel.full.fcstm.puml.svg
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

示例 6：转换优先级
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

当同一状态的多个转换的守卫条件都满足时，选择定义顺序中的第一个转换：

.. literalinclude:: example6_transition_priority.full.fcstm
   :language: fcstm
   :caption: 转换优先级演示

.. figure:: example6_transition_priority.full.fcstm.puml.svg
   :align: center

   转换优先级图

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
     - *（无）*
     - *（初始）*
     - 0
     - 初始变量值
   * - 1
     - *（无）*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，执行 ``A.during``（counter + 1）
   * - 2
     - *（无）*
     - Root.A
     - 2
     - 无守卫满足，执行 ``A.during``（counter + 1）
   * - 3
     - *（无）*
     - Root.A
     - 3
     - 无守卫满足，执行 ``A.during``（counter + 1）
   * - 4
     - *（无）*
     - Root.C
     - 103
     - 两个守卫都满足（counter >= 5 和 counter >= 3），但 ``A -> C`` 定义在后且优先，执行 ``C.during``（counter + 100）

**详细执行跟踪**：

**周期 1-3**（累积 counter）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- 周期 2-3 继续递增：``counter = 2``，然后 ``counter = 3``

**周期 4**（转换优先级）：

- 当前状态：``Root.A``，``counter = 3``
- 按定义顺序检查转换：
  1. ``A -> B : if [counter >= 5]``（守卫不满足，counter = 3）
  2. ``A -> C : if [counter >= 3]``（守卫满足！）
- 执行 ``A.exit``（未定义）
- 执行 ``C.enter``（未定义）
- 到达可停止状态 ``C``
- 执行 ``C.during``：``counter = 3 + 100 = 103``
- **结果**：``state = Root.C``，``counter = 103``

**关键点**：转换按定义顺序评估。选择第一个守卫满足的转换，即使多个守卫都满足。

示例 7：自转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

自转换执行退出和进入动作，提供了一种重置状态特定初始化的方法：

.. literalinclude:: example7_self_transition.full.fcstm
   :language: fcstm
   :caption: 带生命周期动作的自转换

.. figure:: example7_self_transition.full.fcstm.puml.svg
   :align: center

   自转换图

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
     - *（无）*
     - *（初始）*
     - 0
     - 初始变量值
   * - 1
     - *（无）*
     - Root.A
     - 11
     - 初始转换 ``[*] -> A``，执行 ``A.enter``（+1），然后 ``A.during``（+10）
   * - 2
     - ``Loop``
     - Root.A
     - 122
     - 事件 ``Loop`` 触发 ``A -> A``，执行 ``A.exit``（+100），``A.enter``（+1），``A.during``（+10）

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 执行 ``A.enter``：``counter = 0 + 1 = 1``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 1 + 10 = 11``
- **结果**：``state = Root.A``，``counter = 11``

**周期 2**（带事件 ``Loop`` 的自转换）：

- 当前状态：``Root.A``，``counter = 11``
- 检查转换：``A -> A :: Loop``（事件匹配！）
- 执行 ``A.exit``：``counter = 11 + 100 = 111``
- 执行转换（无效果）
- 执行 ``A.enter``：``counter = 111 + 1 = 112``
- 到达可停止状态 ``A``（同一状态）
- 执行 ``A.during``：``counter = 112 + 10 = 122``
- **结果**：``state = Root.A``，``counter = 122``

**关键点**：自转换（``A -> A``）执行完整的退出-进入序列，允许状态重新初始化。这与没有转换而停留在状态中不同。

示例 8：带效果的守卫条件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

守卫和效果协同工作，实现带状态修改的复杂条件转换：

.. literalinclude:: example8_guard_effect.full.fcstm
   :language: fcstm
   :caption: 带转换效果的守卫条件

.. figure:: example8_guard_effect.full.fcstm.puml.svg
   :align: center

   守卫和效果图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 25 12 12 31

   * - 周期
     - 事件
     - 状态
     - counter
     - flag
     - 原因
   * - 0
     - *（无）*
     - *（初始）*
     - 0
     - 0
     - 初始变量值
   * - 1
     - *（无）*
     - Root.A
     - 1
     - 0
     - 初始转换 ``[*] -> A``，执行 ``A.during``（counter + 1）
   * - 2
     - *（无）*
     - Root.A
     - 2
     - 0
     - 守卫不满足（counter < 3），执行 ``A.during``（counter + 1）
   * - 3
     - *（无）*
     - Root.A
     - 3
     - 0
     - 守卫不满足（counter < 3），执行 ``A.during``（counter + 1）
   * - 4
     - *（无）*
     - Root.B.B1
     - 13
     - 1
     - 守卫满足（counter >= 3），效果设置 flag=1，``B.enter`` 验证 ``B1`` 可达，执行 ``B1.during``（counter + 10）

**详细执行跟踪**：

**周期 1-3**（累积 counter）：

- 初始状态：``counter = 0``，``flag = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- 周期 2-3 继续：``counter = 2``，然后 ``counter = 3``

**周期 4**（守卫满足，效果执行）：

- 当前状态：``Root.A``，``counter = 3``，``flag = 0``
- 检查转换：``A -> B : if [counter >= 3]``（守卫满足！）
- 执行 ``A.exit``（未定义）
- 执行转换效果：``flag = 1``
- 执行 ``B.enter``：``flag = 1``（enter 动作设置 flag）
- **B 是复合状态** - 跟随 ``[*] -> B1 : if [flag == 1]``（守卫满足！）
- 执行 ``B1.enter``（未定义）
- 到达可停止状态 ``B1``
- 执行 ``B1.during``：``counter = 3 + 10 = 13``
- **结果**：``state = Root.B.B1``，``counter = 13``，``flag = 1``

**关键点**：转换效果在退出动作之后但在进入动作之前执行。效果可以修改变量，这些变量会被后续初始转换中的守卫检查，从而实现复杂的多阶段验证。

DFS 验证机制
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

当转换到非可停止状态（复合状态或伪状态）时，运行时执行深度优先搜索（DFS）来验证是否可以到达可停止状态。这可以防止状态机进入无效状态。

**验证规则**：

1. **复合状态**：必须至少有一个初始转换可以到达可停止状态
2. **伪状态**：必须有一个出站转换可以到达可停止状态
3. **事件要求**：当前周期中必须提供所有必需的事件
4. **守卫条件**：路径上的所有守卫都必须满足
5. **转换顺序**：转换按定义顺序评估（DFS，而非 BFS）

**验证过程**：

1. 创建当前变量的快照
2. 使用 DFS 模拟转换链：
   - 执行 enter 动作（修改快照）
   - 检查守卫（使用快照）
   - 递归跟随初始转换
3. 如果到达可停止状态：验证成功，执行真实转换
4. 如果无法到达可停止状态：验证失败，停留在当前状态

示例 9：伪状态链验证
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

伪状态需要验证以确保它们通向可停止状态：

.. literalinclude:: example9_pseudo_chain.full.fcstm
   :language: fcstm
   :caption: 需要验证的伪状态链

.. figure:: example9_pseudo_chain.full.fcstm.puml.svg
   :align: center

   伪状态链图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 25 20 12 35

   * - 周期
     - 事件
     - 状态
     - counter
     - 原因
   * - 0
     - *（无）*
     - *（初始）*
     - 0
     - 初始变量值
   * - 1
     - *（无）*
     - Root.A
     - 1
     - 初始转换 ``[*] -> A``，执行 ``A.during``（counter + 1）
   * - 2
     - ``GoP``
     - Root.A
     - 2
     - 事件 ``GoP`` 触发 ``A -> P``，但 P 是伪状态（非可停止），验证失败（无 ``GoB`` 事件），停留在 A，执行 ``A.during``（counter + 1）
   * - 3
     - ``GoP``，``GoB``
     - Root.B
     - 1112
     - 提供两个事件，验证成功：``A -> P``（+10，+100）``-> B``，执行 ``B.during``（+1000）

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果**：``state = Root.A``，``counter = 1``

**周期 2**（验证失败 - 缺少事件）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> P :: GoP``（事件匹配！）
- **验证阶段**（使用快照）：
  - 目标 ``P`` 是伪状态（非可停止）
  - 模拟：执行 ``P.enter``：``counter_snapshot = 1 + 10 = 11``
  - 检查 ``P`` 的转换：``P -> B :: GoB``（需要 ``GoB`` 事件）
  - 当前周期中事件 ``GoB`` 不可用
  - **验证失败**：无法到达可停止状态
- 转换被拒绝，停留在 ``A``
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果**：``state = Root.A``，``counter = 2``

**周期 3**（验证成功 - 提供所有事件）：

- 当前状态：``Root.A``，``counter = 2``
- 检查转换：``A -> P :: GoP``（事件匹配！）
- **验证阶段**（使用快照）：
  - 目标 ``P`` 是伪状态（非可停止）
  - 模拟：执行 ``P.enter``：``counter_snapshot = 2 + 10 = 12``
  - 检查 ``P`` 的转换：``P -> B :: GoB``（需要 ``GoB`` 事件）
  - 当前周期中事件 ``GoB`` 可用
  - 模拟：执行 ``B.enter``（未定义）
  - 目标 ``B`` 是可停止状态
  - **验证成功**：可以到达可停止状态 ``B``
- **真实执行**：
  - 执行 ``A.exit``（未定义）
  - 执行 ``P.enter``：``counter = 2 + 10 = 12``
  - 到达伪状态 ``P``（非可停止，立即继续）
  - 执行 ``P.during``：``counter = 12 + 100 = 112``
  - 执行 ``P.exit``（未定义）
  - 执行 ``B.enter``（未定义）
  - 到达可停止状态 ``B``
  - 执行 ``B.during``：``counter = 112 + 1000 = 1112``
- **结果**：``state = Root.B``，``counter = 1112``

**关键点**：伪状态是非可停止的，需要验证。验证使用 DFS 检查转换链是否可以使用可用事件到达可停止状态。伪状态在真实转换期间执行其 ``during`` 动作，但这发生在到达最终可停止状态的同一周期中。

示例 10：验证失败 - 不可达的可停止状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

当复合状态的初始转换无法到达可停止状态时，转换被拒绝：

.. literalinclude:: example10_validation_failure.full.fcstm
   :language: fcstm
   :caption: 由于不可达的可停止状态导致的验证失败

.. figure:: example10_validation_failure.full.fcstm.puml.svg
   :align: center

   验证失败图

**执行摘要**：

.. list-table::
   :header-rows: 1
   :widths: 8 20 20 12 12 28

   * - 周期
     - 事件
     - 状态
     - counter
     - ready
     - 原因
   * - 0
     - *（无）*
     - *（初始）*
     - 0
     - 0
     - 初始变量值
   * - 1
     - *（无）*
     - Root.A
     - 1
     - 0
     - 初始转换 ``[*] -> A``，执行 ``A.during``（counter + 1）
   * - 2
     - ``GoB``
     - Root.A
     - 2
     - 0
     - 事件 ``GoB`` 触发 ``A -> B``，但验证失败（``B`` 没有有效的初始转换到达可停止状态），停留在 A，执行 ``A.during``（counter + 1）

**详细执行跟踪**：

**周期 1**（初始化）：

- 初始状态：``counter = 0``，``ready = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果**：``state = Root.A``，``counter = 1``，``ready = 0``

**周期 2**（验证失败 - 守卫不满足）：

- 当前状态：``Root.A``，``counter = 1``，``ready = 0``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- **验证阶段**（使用快照）：
  - 目标 ``B`` 是复合状态（非可停止）
  - 模拟：执行 ``B.enter``（未定义）
  - 检查 ``B`` 的初始转换：``[*] -> B1 : if [ready == 1]``
  - 守卫检查：``ready == 1``（当前值：``ready = 0``）
  - **守卫不满足**
  - 没有其他可用的初始转换
  - **验证失败**：无法到达可停止状态
- 转换被拒绝，停留在 ``A``
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果**：``state = Root.A``，``counter = 2``，``ready = 0``

**关键点**：复合状态必须至少有一个初始转换可以到达可停止状态。验证检查路径上的所有守卫和事件要求。如果不存在有效路径，转换被拒绝，状态机保持在当前状态。

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
