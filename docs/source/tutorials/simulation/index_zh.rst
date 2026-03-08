FCSTM 仿真指南
===============================================

本指南介绍如何在 Python 中仿真 FCSTM 状态机。仿真运行时提供了一个交互式执行环境，用于在代码生成之前测试、原型设计和理解状态机行为。

核心概念
---------------------------------------

在深入使用之前，请理解这些关键概念：

**状态类型**

- **叶状态** ：没有子状态的状态（可以执行 ``during`` 动作）
- **复合状态** ：包含子状态的状态（需要初始转换）
- **伪状态** ：跳过祖先切面动作的特殊叶状态
- **可停止状态** ：一个周期可以结束的叶状态（非伪状态）

**生命周期动作**

- **enter** ：进入状态时执行
- **during** ：保持在状态中时执行（每个周期）
- **exit** ：离开状态时执行

**切面动作**

- **>> during before/after** ：应用于所有后代叶状态的横切动作
- 伪状态跳过祖先切面动作

**复合状态动作**

- **during before** （不带 ``>>``）：从父状态进入复合状态时执行（``[*] -> Child``）
- **during after** （不带 ``>>``）：从复合状态退出到父状态时执行（``Child -> [*]``）
- **不执行** ：在子状态到子状态的转换期间（``Child1 -> Child2``）

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

**关键 API** ：

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

**事件作用域** ：

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

**处理器上下文 API** ：

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

一个 **周期**  执行直到达到稳定边界：

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

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``
- 执行初始转换 ``[*] -> A``
- 执行 ``A.enter``（未定义）
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果** ：``state = Root.A``，``counter = 1``

**周期 2** （无事件）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: Go``（需要事件，未触发）
- 没有转换触发
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果** ：``state = Root.A``，``counter = 2``

**周期 3** （带事件 ``Go``）：

- 当前状态：``Root.A``，``counter = 2``
- 检查转换：``A -> B :: Go``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行转换（无效果）
- 执行 ``B.enter``（未定义）
- 到达可停止状态 ``B``
- 执行 ``B.during``：``counter = 2 + 10 = 12``
- **结果** ：``state = Root.B``，``counter = 12``

示例 2：带初始转换的复合状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example2_composite.full.fcstm
   :language: fcstm
   :caption: 带嵌套状态的复合状态

.. figure:: example2_composite.full.fcstm.puml.svg
   :align: center

   复合状态图

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果** ：``state = Root.A``，``counter = 1``

**周期 2** （带事件 ``GoB``）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``B.enter``（未定义）
- **B 是复合状态**  - 必须跟随初始转换
- 执行 ``[*] -> B1``（在 B 内部）
- 执行 ``B1.enter``（未定义）
- 到达可停止状态 ``B1``
- 执行 ``B1.during``：``counter = 1 + 10 = 11``
- **结果** ：``state = Root.B.B1``，``counter = 11``

**关键点** ：当转换到复合状态时，周期继续跟随初始转换直到到达可停止状态。

**周期 3** （带事件 ``Next``）：

- 当前状态：``Root.B.B1``，``counter = 11``
- 检查转换：``B1 -> B2 :: Next``（事件匹配！）
- 执行 ``B1.exit``（未定义）
- 执行 ``B2.enter``（未定义）
- 到达可停止状态 ``B2``
- 执行 ``B2.during``：``counter = 11 + 100 = 111``
- **结果** ：``state = Root.B.B2``，``counter = 111``

示例 3：切面动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example3_aspect.full.fcstm
   :language: fcstm
   :caption: 带执行顺序的切面动作

.. figure:: example3_aspect.full.fcstm.puml.svg
   :align: center

   切面动作图

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``trace = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 during 阶段：
  1. ``Root >> during before``：``trace = 0 * 10 + 1 = 1``
  2. ``A.during``：``trace = 1 * 10 + 2 = 12``
  3. ``Root >> during after``：``trace = 12 * 10 + 3 = 123``
- **结果** ：``state = Root.A``，``trace = 123``

**周期 2** （无事件）：

- 当前状态：``Root.A``，``trace = 123``
- 没有转换触发
- 执行 during 阶段：
  1. ``Root >> during before``：``trace = 123 * 10 + 1 = 1231``
  2. ``A.during``：``trace = 1231 * 10 + 2 = 12312``
  3. ``Root >> during after``：``trace = 12312 * 10 + 3 = 123123``
- **结果** ：``state = Root.A``，``trace = 123123``

**关键点** ：切面动作（``>> during before/after``）按层次顺序在叶状态的 ``during`` 动作周围执行，形成三明治模式：before → during → after。

示例 4：伪状态（跳过切面动作）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example4_pseudo.full.fcstm
   :language: fcstm
   :caption: 伪状态跳过切面动作

.. figure:: example4_pseudo.full.fcstm.puml.svg
   :align: center

   伪状态图

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化和终止）：

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
- **结果** ：``state = terminated``，``trace = 2``

**关键点** ：伪状态跳过所有祖先切面动作，只执行自己的 ``during`` 动作。这对于不应触发横切关注点的中间状态很有用。

示例 5：多层复合状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example5_multilevel.full.fcstm
   :language: fcstm
   :caption: 多层嵌套复合状态

.. figure:: example5_multilevel.full.fcstm.puml.svg
   :align: center

   多层复合状态图

**执行摘要（场景 1：A → B）** ：

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

**执行摘要（场景 2：A → C）** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果** ：``state = Root.A``，``counter = 1``

**周期 2** （带事件 ``GoB``）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``B.enter``（未定义）
- **B 是复合状态**  - 跟随 ``[*] -> B1``
- 执行 ``B1.enter``（未定义）
- **B1 也是复合状态**  - 跟随 ``[*] -> B1a``
- 执行 ``B1a.enter``（未定义）
- 到达可停止状态 ``B1a``
- 执行 ``B1a.during``：``counter = 1 + 10 = 11``
- **结果** ：``state = Root.B.B1.B1a``，``counter = 11``

**关键点** ：单个周期可以通过跟随初始转换链遍历多层复合状态，直到到达可停止的叶状态。

**周期 3** （从初始状态带事件 ``GoC``）：

- 重新开始：``counter = 0``
- 执行 ``[*] -> A``
- 执行 ``A.during``：``counter = 1``
- 下一个周期带事件 ``GoC``：

- 检查转换：``A -> C :: GoC``（事件匹配！）
- 执行 ``A.exit``（未定义）
- 执行 ``C.enter``（未定义）
- 到达可停止状态 ``C``
- 执行 ``C.during``：``counter = 1 + 100 = 101``
- **结果** ：``state = Root.C``，``counter = 101``

层次执行顺序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

理解嵌套状态中的执行顺序至关重要：

.. literalinclude:: hierarchy_execution.demo.py
   :language: python
   :caption: 层次执行

输出：

.. literalinclude:: hierarchy_execution.demo.py.txt
   :language: text

**完整执行顺序** ：

**进入阶段** （从父状态）：

1. ``State.enter``
2. ``State.during before``（如果通过 ``[*] -> Child`` 进入）
3. ``Child.enter``

**During 阶段** （叶状态的每个周期）：

1. 祖先 ``>> during before`` 动作（从根到叶）
2. 叶状态 ``during`` 动作
3. 祖先 ``>> during after`` 动作（从叶到根）

**退出阶段** （到父状态）：

1. ``Child.exit``
2. ``State.during after``（如果通过 ``Child -> [*]`` 退出）
3. ``State.exit``

**子状态到子状态的转换** ：

1. ``Child1.exit``
2. （转换效果）
3. ``Child2.enter``
4. 不执行 ``during before/after``

**关键点** ：

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

**执行摘要** ：

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
     - 守卫不满足（counter < 3），执行 ``A.during``（counter + 1）
   * - 3
     - *（无）*
     - Root.A
     - 3
     - 守卫不满足（counter < 3），执行 ``A.during``（counter + 1）
   * - 4
     - *（无）*
     - Root.B
     - 13
     - 两个守卫都满足（counter >= 3），但 ``A -> B`` 定义在前且优先，执行 ``B.during``（counter + 10）

**详细执行跟踪** ：

**周期 1-3** （累积 counter）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- 周期 2-3 继续递增：``counter = 2``，然后 ``counter = 3``

**周期 4** （转换优先级）：

- 当前状态：``Root.A``，``counter = 3``
- 按定义顺序检查转换：
  1. ``A -> B : if [counter >= 3]``（守卫满足！）
  2. ``A -> C : if [counter >= 3]``（守卫也满足，但不检查）
- 执行 ``A.exit``（未定义）
- 执行 ``B.enter``（未定义）
- 到达可停止状态 ``B``
- 执行 ``B.during``：``counter = 3 + 10 = 13``
- **结果** ：``state = Root.B``，``counter = 13``

**关键点** ：转换按定义顺序评估。选择第一个守卫满足的转换，即使多个守卫都满足。

示例 7：自转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

自转换执行退出和进入动作，提供了一种重置状态特定初始化的方法：

.. literalinclude:: example7_self_transition.full.fcstm
   :language: fcstm
   :caption: 带生命周期动作的自转换

.. figure:: example7_self_transition.full.fcstm.puml.svg
   :align: center

   自转换图

**执行摘要** ：

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
     - *（无）*
     - Root.A
     - 21
     - 无事件，停留在 A，执行 ``A.during``（+10）
   * - 3
     - *（无）*
     - Root.A
     - 31
     - 无事件，停留在 A，执行 ``A.during``（+10）
   * - 4
     - ``Loop``
     - Root.A
     - 142
     - 事件 ``Loop`` 触发 ``A -> A``，执行 ``A.exit``（+100），``A.enter``（+1），``A.during``（+10）

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 执行 ``A.enter``：``counter = 0 + 1 = 1``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 1 + 10 = 11``
- **结果** ：``state = Root.A``，``counter = 11``

**周期 2-3** （停留在状态中无转换）：

- 当前状态：``Root.A``，``counter = 11``
- 未提供事件，无转换触发
- 停留在状态 ``A``
- 执行 ``A.during``：``counter = 11 + 10 = 21``
- **结果** ：``state = Root.A``，``counter = 21``
- 周期 3：同样的过程，``counter = 21 + 10 = 31``

**周期 4** （带事件 ``Loop`` 的自转换）：

- 当前状态：``Root.A``，``counter = 31``
- 检查转换：``A -> A :: Loop``（事件匹配！）
- 执行 ``A.exit``：``counter = 31 + 100 = 131``
- 执行转换（无效果）
- 执行 ``A.enter``：``counter = 131 + 1 = 132``
- 到达可停止状态 ``A``（同一状态）
- 执行 ``A.during``：``counter = 132 + 10 = 142``
- **结果** ：``state = Root.A``，``counter = 142``

**关键点** ：自转换（``A -> A``）执行完整的退出-进入序列，允许状态重新初始化。这与没有转换而停留在状态中不同：

- **停留在状态中** （周期 2-3）：只执行 ``during`` 动作（每个周期 +10）
- **自转换** （周期 4）：执行完整序列：``exit``（+100）→ ``enter``（+1）→ ``during``（+10）

示例 8：带效果的守卫条件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

守卫和效果协同工作，实现带状态修改的复杂条件转换：

.. literalinclude:: example8_guard_effect.full.fcstm
   :language: fcstm
   :caption: 带转换效果的守卫条件

.. figure:: example8_guard_effect.full.fcstm.puml.svg
   :align: center

   守卫和效果图

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1-3** （累积 counter）：

- 初始状态：``counter = 0``，``flag = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- 周期 2-3 继续：``counter = 2``，然后 ``counter = 3``

**周期 4** （守卫满足，效果执行）：

- 当前状态：``Root.A``，``counter = 3``，``flag = 0``
- 检查转换：``A -> B : if [counter >= 3]``（守卫满足！）
- 执行 ``A.exit``（未定义）
- 执行转换效果：``flag = 1``
- 执行 ``B.enter``：``flag = 1``（enter 动作设置 flag）
- **B 是复合状态**  - 跟随 ``[*] -> B1 : if [flag == 1]``（守卫满足！）
- 执行 ``B1.enter``（未定义）
- 到达可停止状态 ``B1``
- 执行 ``B1.during``：``counter = 3 + 10 = 13``
- **结果** ：``state = Root.B.B1``，``counter = 13``，``flag = 1``

**关键点** ：转换效果在退出动作之后但在进入动作之前执行。效果可以修改变量，这些变量会被后续初始转换中的守卫检查，从而实现复杂的多阶段验证。

DFS 验证机制
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

当转换到非可停止状态（复合状态或伪状态）时，运行时执行深度优先搜索（DFS）来验证是否可以到达可停止状态。这可以防止状态机进入无效状态。

**验证规则** ：

1. **复合状态** ：必须至少有一个初始转换可以到达可停止状态
2. **伪状态** ：必须有一个出站转换可以到达可停止状态
3. **事件要求** ：当前周期中必须提供所有必需的事件
4. **守卫条件** ：路径上的所有守卫都必须满足
5. **转换顺序** ：转换按定义顺序评估（DFS，而非 BFS）

**验证过程** ：

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

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果** ：``state = Root.A``，``counter = 1``

**周期 2** （验证失败 - 缺少事件）：

- 当前状态：``Root.A``，``counter = 1``
- 检查转换：``A -> P :: GoP``（事件匹配！）
- **验证阶段** （使用快照）：
  - 目标 ``P`` 是伪状态（非可停止）
  - 模拟：执行 ``P.enter``：``counter_snapshot = 1 + 10 = 11``
  - 检查 ``P`` 的转换：``P -> B :: GoB``（需要 ``GoB`` 事件）
  - 当前周期中事件 ``GoB`` 不可用
  - **验证失败** ：无法到达可停止状态
- 转换被拒绝，停留在 ``A``
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果** ：``state = Root.A``，``counter = 2``

**周期 3** （验证成功 - 提供所有事件）：

- 当前状态：``Root.A``，``counter = 2``
- 检查转换：``A -> P :: GoP``（事件匹配！）
- **验证阶段** （使用快照）：
  - 目标 ``P`` 是伪状态（非可停止）
  - 模拟：执行 ``P.enter``：``counter_snapshot = 2 + 10 = 12``
  - 检查 ``P`` 的转换：``P -> B :: GoB``（需要 ``GoB`` 事件）
  - 当前周期中事件 ``GoB`` 可用
  - 模拟：执行 ``B.enter``（未定义）
  - 目标 ``B`` 是可停止状态
  - **验证成功** ：可以到达可停止状态 ``B``
- **真实执行** ：
  - 执行 ``A.exit``（未定义）
  - 执行 ``P.enter``：``counter = 2 + 10 = 12``
  - 到达伪状态 ``P``（非可停止，立即继续）
  - 执行 ``P.during``：``counter = 12 + 100 = 112``
  - 执行 ``P.exit``（未定义）
  - 执行 ``B.enter``（未定义）
  - 到达可停止状态 ``B``
  - 执行 ``B.during``：``counter = 112 + 1000 = 1112``
- **结果** ：``state = Root.B``，``counter = 1112``

**关键点** ：伪状态是非可停止的，需要验证。验证使用 DFS 检查转换链是否可以使用可用事件到达可停止状态。伪状态在真实转换期间执行其 ``during`` 动作，但这发生在到达最终可停止状态的同一周期中。

示例 10：验证失败 - 不可达的可停止状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

当复合状态的初始转换无法到达可停止状态时，转换被拒绝：

.. literalinclude:: example10_validation_failure.full.fcstm
   :language: fcstm
   :caption: 由于不可达的可停止状态导致的验证失败

.. figure:: example10_validation_failure.full.fcstm.puml.svg
   :align: center

   验证失败图

**执行摘要** ：

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

**详细执行跟踪** ：

**周期 1** （初始化）：

- 初始状态：``counter = 0``，``ready = 0``
- 执行 ``[*] -> A``
- 到达可停止状态 ``A``
- 执行 ``A.during``：``counter = 0 + 1 = 1``
- **结果** ：``state = Root.A``，``counter = 1``，``ready = 0``

**周期 2** （验证失败 - 守卫不满足）：

- 当前状态：``Root.A``，``counter = 1``，``ready = 0``
- 检查转换：``A -> B :: GoB``（事件匹配！）
- **验证阶段** （使用快照）：
  - 目标 ``B`` 是复合状态（非可停止）
  - 模拟：执行 ``B.enter``（未定义）
  - 检查 ``B`` 的初始转换：``[*] -> B1 : if [ready == 1]``
  - 守卫检查：``ready == 1``（当前值：``ready = 0``）
  - **守卫不满足**
  - 没有其他可用的初始转换
  - **验证失败** ：无法到达可停止状态
- 转换被拒绝，停留在 ``A``
- 执行 ``A.during``：``counter = 1 + 1 = 2``
- **结果** ：``state = Root.A``，``counter = 2``，``ready = 0``

**关键点** ：复合状态必须至少有一个初始转换可以到达可停止状态。验证检查路径上的所有守卫和事件要求。如果不存在有效路径，转换被拒绝，状态机保持在当前状态。

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

真实业务例子
---------------------------------------

以下例子展示了 FCSTM 状态机在真实控制系统中的实际应用。每个例子包含多个执行场景，展示不同的业务条件及其详细的执行跟踪。

示例 11：电梯轿门控制
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

此例子模拟常见电梯轿门控制逻辑：收到呼梯后开门，开到位后保持一段时间，再自动关门；如果关门过程中红外光幕检测到有人或物体遮挡，则立即重新开门并重新计时。

.. literalinclude:: example11_elevator_door.full.fcstm
   :language: fcstm
   :caption: 电梯轿门控制系统

.. figure:: example11_elevator_door.full.fcstm.puml.svg
   :align: center

   电梯轿门控制图

**业务背景** ：

此状态机模拟典型的电梯安全系统，其中：

- ``door_pos`` 表示门位置（0=完全关闭，50=半开，100=完全打开）
- ``hold`` 计数门保持完全打开的周期数
- ``reopen_count`` 跟踪因遮挡而重新开门的次数

**场景 A：正常操作** （开门 → 保持 → 关门）

.. list-table::
   :header-rows: 1
   :widths: 8 20 12 12 12 36

   * - 周期
     - 事件
     - 状态
     - door_pos
     - hold
     - 业务含义
   * - 1
     - *（无）*
     - Closed
     - 0
     - 0
     - 电梯空闲，门关闭
   * - 2
     - ``HallCall``
     - Opening
     - 50
     - 0
     - 乘客呼叫电梯，门开始打开
   * - 3
     - *（无）*
     - Opening
     - 100
     - 0
     - 门继续打开到完全打开位置
   * - 4
     - *（无）*
     - Opened
     - 100
     - 1
     - 门完全打开，保持计时器启动
   * - 5
     - *（无）*
     - Opened
     - 100
     - 2
     - 保持计时器继续（等待乘客）
   * - 6
     - *（无）*
     - Closing
     - 50
     - 2
     - 保持时间到期，门开始关闭
   * - 7
     - *（无）*
     - Closing
     - 0
     - 2
     - 门继续关闭到完全关闭
   * - 8
     - *（无）*
     - Closed
     - 0
     - 0
     - 门完全关闭，准备下次呼叫

**详细执行跟踪 A** ：

**周期 1** （初始状态）：

- 初始：``door_pos = 0``，``hold = 0``，``reopen_count = 0``
- 执行 ``[*] -> Closed``
- 执行 ``Closed.during``：``hold = 0``
- **结果** ：电梯空闲，门关闭

**周期 2** （收到呼梯）：

- 事件 ``HallCall`` 触发 ``Closed -> Opening``
- 执行 ``Closed.exit``（未定义）
- 执行转换效果：``hold = 0``
- 执行 ``Opening.enter``（未定义）
- 执行 ``Opening.during``：``door_pos = 0 + 50 = 50``
- **结果** ：门开始打开，半开状态

**周期 3** （门继续打开）：

- 检查 ``Opening -> Opened``：``door_pos >= 100`` 不满足（当前：50）
- 执行 ``Opening.during``：``door_pos = 50 + 50 = 100``
- **结果** ：门到达完全打开位置

**周期 4** （转换到打开状态）：

- 检查 ``Opening -> Opened``：``door_pos >= 100`` 满足
- 执行 ``Opening.exit``（未定义）
- 执行转换效果：``hold = 0``
- 执行 ``Opened.enter``（未定义）
- 执行 ``Opened.during``：``hold = 0 + 1 = 1``
- **结果** ：门完全打开，保持计时器启动

**周期 5** （保持计时器继续）：

- 检查 ``Opened -> Closing``：``hold >= 2`` 不满足（当前：1）
- 执行 ``Opened.during``：``hold = 1 + 1 = 2``
- **结果** ：保持计时器达到阈值

**周期 6** （开始关门）：

- 检查 ``Opened -> Closing``：``hold >= 2`` 满足
- 执行 ``Opened.exit``（未定义）
- 执行 ``Closing.enter``（未定义）
- 执行 ``Closing.during``：``door_pos = 100 - 50 = 50``
- **结果** ：门开始关闭

**周期 7** （继续关门）：

- 检查 ``Closing -> Closed``：``door_pos <= 0`` 不满足（当前：50）
- 执行 ``Closing.during``：``door_pos = 50 - 50 = 0``
- **结果** ：门到达完全关闭位置

**周期 8** （转换到关闭状态）：

- 检查 ``Closing -> Closed``：``door_pos <= 0`` 满足
- 执行 ``Closing.exit``（未定义）
- 执行转换效果：``hold = 0``
- 执行 ``Closed.enter``（未定义）
- 执行 ``Closed.during``：``hold = 0``
- **结果** ：门完全关闭，系统就绪

**场景 B：安全重开** （关门时检测到遮挡）

.. list-table::
   :header-rows: 1
   :widths: 8 25 12 12 12 31

   * - 周期
     - 事件
     - 状态
     - door_pos
     - reopen_count
     - 业务含义
   * - 1-5
     - *（同 A）*
     - *（同 A）*
     - *（同）*
     - 0
     - 正常开门和保持序列
   * - 6
     - *（无）*
     - Closing
     - 50
     - 0
     - 门开始自动关闭
   * - 7
     - ``BeamBlocked``
     - Opened
     - 100
     - 1
     - 检测到遮挡！门立即重开以确保安全

**详细执行跟踪 B** ：

**周期 1-6** ：与场景 A 相同（门打开、保持、开始关闭）
- 周期 6 后：``state = Closing``，``door_pos = 50``，``hold = 2``，``reopen_count = 0``

**周期 7** （检测到遮挡）：

- 事件 ``BeamBlocked`` 触发 ``Closing -> Opened``
- 执行 ``Closing.exit``（未定义）
- 执行转换效果：
  - ``reopen_count = 0 + 1 = 1``（跟踪安全重开）
  - ``door_pos = 100``（立即设置为完全打开）
  - ``hold = 0``（重启保持计时器）
- 执行 ``Opened.enter``（未定义）
- 执行 ``Opened.during``：``hold = 0 + 1 = 1``
- **结果** ：门立即重开以确保安全，保持计时器重启

**关键点** ：

- ``door_pos`` 抽象为三个位置（0、50、100）表示关闭、半开和完全打开
- ``BeamBlocked`` 事件仅在 ``Closing`` 状态下有意义，符合真实电梯安全逻辑
- 重开直接转换到 ``Opened``（而非 ``Opening``），立即提供通行空间
- ``reopen_count`` 跟踪安全事件用于维护监控

示例 12：储水式电热水器控温
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

此例子模拟常见家用储水式电热水器：待机时水温缓慢下降，降到下限后自动加热；如果用户集中用水，则水温会在一个周期内显著下降，从而更早触发加热。

.. literalinclude:: example12_water_heater.full.fcstm
   :language: fcstm
   :caption: 储水式电热水器控温系统

.. figure:: example12_water_heater.full.fcstm.puml.svg
   :align: center

   热水器温度控制图

**业务背景** ：

此状态机模拟典型的迟滞温度控制系统，其中：

- ``water_temp`` 表示水温（度）
- ``draw_count`` 跟踪热水使用事件次数
- 待机时温度自然下降 1°/周期
- 加热时温度上升 4°/周期
- 热水抽取导致立即 8° 温降

**场景 A：自然散热与恢复** （无用水）

.. list-table::
   :header-rows: 1
   :widths: 8 20 15 12 43

   * - 周期
     - 事件
     - 状态
     - water_temp
     - 业务含义
   * - 1
     - *（无）*
     - Standby
     - 54
     - 正常待机，逐渐散热
   * - 2
     - *（无）*
     - Standby
     - 53
     - 通过保温层持续散热
   * - 3
     - *（无）*
     - Standby
     - 52
     - 温度接近下限阈值
   * - 4
     - *（无）*
     - Standby
     - 51
     - 温度接近加热启动点
   * - 5
     - *（无）*
     - Standby
     - 50
     - 温度达到下限阈值
   * - 6
     - *（无）*
     - Heating
     - 54
     - 加热启动，温度开始上升
   * - 7
     - *（无）*
     - Heating
     - 58
     - 加热继续向上限阈值

**详细执行跟踪 A** ：

**周期 1** （初始待机）：

- 初始：``water_temp = 55``，``draw_count = 0``
- 执行 ``[*] -> Standby``
- 执行 ``Standby.during``：``water_temp = 55 - 1 = 54``
- **结果** ：通过水箱保温层正常散热

**周期 2-5** （温度逐渐下降）：

- 每周期：检查 ``Standby -> Heating``：``water_temp <= 50`` 不满足
- 执行 ``Standby.during``：``water_temp`` 减 1
- 周期 2：``54 - 1 = 53``
- 周期 3：``53 - 1 = 52``
- 周期 4：``52 - 1 = 51``
- 周期 5：``51 - 1 = 50``
- **结果** ：温度逐渐降至下限阈值

**周期 6** （加热启动）：

- 检查 ``Standby -> Heating``：``water_temp <= 50`` 满足
- 执行 ``Standby.exit``（未定义）
- 执行 ``Heating.enter``（未定义）
- 执行 ``Heating.during``：``water_temp = 50 + 4 = 54``
- **结果** ：加热元件启动，温度开始上升

**周期 7** （继续加热）：

- 检查 ``Heating -> Standby``：``water_temp >= 60`` 不满足（当前：54）
- 执行 ``Heating.during``：``water_temp = 54 + 4 = 58``
- **结果** ：加热继续向上限阈值

**场景 B：大量用水** （早晨淋浴触发提前加热）

.. list-table::
   :header-rows: 1
   :widths: 8 25 15 12 12 28

   * - 周期
     - 事件
     - 状态
     - water_temp
     - draw_count
     - 业务含义
   * - 1
     - *（无）*
     - Standby
     - 54
     - 0
     - 正常待机状态
   * - 2
     - ``HotWaterDraw``
     - Standby
     - 45
     - 1
     - 大量用水（淋浴），温度快速下降
   * - 3
     - *（无）*
     - Heating
     - 49
     - 1
     - 温度低于阈值，加热启动
   * - 4
     - *（无）*
     - Heating
     - 53
     - 1
     - 加热继续
   * - 5
     - *（无）*
     - Heating
     - 57
     - 1
     - 接近上限阈值
   * - 6
     - *（无）*
     - Heating
     - 61
     - 1
     - 温度超过上限阈值
   * - 7
     - *（无）*
     - Standby
     - 60
     - 1
     - 加热停止，返回待机

**详细执行跟踪 B** ：

**周期 1** （初始待机）：

- 与场景 A 相同：``water_temp = 54``，``draw_count = 0``

**周期 2** （大量用水）：

- 事件 ``HotWaterDraw`` 触发 ``Standby -> Standby``（自转换）
- 执行 ``Standby.exit``（未定义）
- 执行转换效果：
  - ``water_temp = 54 - 8 = 46``（冷水涌入）
  - ``draw_count = 0 + 1 = 1``（跟踪用水事件）
- 执行 ``Standby.enter``（未定义）
- 执行 ``Standby.during``：``water_temp = 46 - 1 = 45``
- **结果** ：用水导致显著温降

**周期 3** （加热启动）：

- 检查 ``Standby -> Heating``：``water_temp <= 50`` 满足（当前：45）
- 执行 ``Standby.exit``（未定义）
- 执行 ``Heating.enter``（未定义）
- 执行 ``Heating.during``：``water_temp = 45 + 4 = 49``
- **结果** ：低温触发立即加热

**周期 4-6** （加热至上限阈值）：

- 每周期：检查 ``Heating -> Standby``：``water_temp >= 60`` 不满足
- 执行 ``Heating.during``：``water_temp`` 增加 4
- 周期 4：``49 + 4 = 53``
- 周期 5：``53 + 4 = 57``
- 周期 6：``57 + 4 = 61``
- **结果** ：温度上升超过上限阈值

**周期 7** （加热停止）：

- 检查 ``Heating -> Standby``：``water_temp >= 60`` 满足
- 执行 ``Heating.exit``（未定义）
- 执行 ``Standby.enter``（未定义）
- 执行 ``Standby.during``：``water_temp = 61 - 1 = 60``
- **结果** ：加热停止，系统返回待机

**关键点** ：

- ``HotWaterDraw`` 模拟用水导致的显著温降
- ``Standby -> Heating`` 和 ``Heating -> Standby`` 形成典型的迟滞控制（50°-60° 死区）
- 自转换 ``Standby -> Standby`` 允许待机时用水
- 自转换 ``Heating -> Heating`` 模拟"边加热边用水"场景
- ``draw_count`` 支持用水模式分析用于能源管理

示例 13：主干道信号灯带行人过街请求
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

此例子模拟城市路口中常见的信号控制器：主干道默认保持绿灯；行人按钮被按下后，请求会先被锁存；只有主干道最小绿灯时间达到后，控制器才进入黄灯和行人放行阶段，结束后再回到主干道绿灯。

.. literalinclude:: example13_traffic_light.full.fcstm
   :language: fcstm
   :caption: 带行人过街的交通信号灯控制

.. figure:: example13_traffic_light.full.fcstm.puml.svg
   :align: center

   交通信号灯控制图

**业务背景** ：

此状态机模拟交通响应式信号系统，其中：

- ``green_ticks`` 计数主干道绿灯持续周期数
- ``request_latched`` 存储行人按钮按下（锁存，非瞬时）
- ``yellow_ticks`` 计数黄灯持续时间
- ``walk_ticks`` 计数行人过街时间
- ``PedestrianPhase`` 是包含黄灯和过街子阶段的复合状态

**场景 A：无行人请求** （保持主干道优先）

.. list-table::
   :header-rows: 1
   :widths: 8 20 15 15 50

   * - 周期
     - 事件
     - 状态
     - green_ticks
     - 业务含义
   * - 1
     - *（无）*
     - MainGreen
     - 1
     - 主干道绿灯激活，无行人请求
   * - 2
     - *（无）*
     - MainGreen
     - 2
     - 继续主干道优先
   * - 3
     - *（无）*
     - MainGreen
     - 3
     - 最小绿灯时间满足，但无行人等待
   * - 4
     - *（无）*
     - MainGreen
     - 4
     - 主干道继续绿灯（高效交通流）

**详细执行跟踪 A** ：

**周期 1** （初始状态）：

- 初始：``green_ticks = 0``，``request_latched = 0``，``yellow_ticks = 0``，``walk_ticks = 0``
- 执行 ``[*] -> MainGreen``
- 执行 ``MainGreen.during``：``green_ticks = 0 + 1 = 1``
- **结果** ：主干道绿灯激活

**周期 2-4** （继续主干道优先）：

- 每周期：检查 ``MainGreen -> PedestrianPhase``：``request_latched == 1 && green_ticks >= 3`` 不满足
- 执行 ``MainGreen.during``：``green_ticks`` 递增
- 周期 2：``green_ticks = 2``
- 周期 3：``green_ticks = 3``（最小绿灯满足，但无请求）
- 周期 4：``green_ticks = 4``
- **结果** ：主干道在无行人需求时保持优先

**场景 B：行人请求与锁存** （按钮提前按下，最小绿灯后放行）

.. list-table::
   :header-rows: 1
   :widths: 8 25 20 15 12 20

   * - 周期
     - 事件
     - 状态
     - green_ticks
     - request_latched
     - 业务含义
   * - 1
     - *（无）*
     - MainGreen
     - 1
     - 0
     - 主干道绿灯激活
   * - 2
     - ``PedRequest``
     - MainGreen
     - 2
     - 1
     - 行人按下按钮，请求被锁存
   * - 3
     - *（无）*
     - MainGreen
     - 3
     - 1
     - 最小绿灯尚未满足，主干道继续
   * - 4
     - *（无）*
     - MainYellow
     - 3
     - 0
     - 最小绿灯满足，进入行人阶段（先黄灯）
   * - 5
     - *（无）*
     - PedWalk
     - 3
     - 0
     - 黄灯完成，行人过街开始
   * - 6
     - *（无）*
     - PedWalk
     - 3
     - 0
     - 行人过街继续
   * - 7
     - *（无）*
     - MainGreen
     - 1
     - 0
     - 行人阶段完成，返回主干道绿灯

**详细执行跟踪 B** ：

**周期 1** （初始状态）：

- 与场景 A 相同：``green_ticks = 1``，``request_latched = 0``

**周期 2** （行人按钮按下）：

- 事件 ``PedRequest`` 触发 ``MainGreen -> MainGreen``（自转换）
- 检查 ``MainGreen -> PedestrianPhase``：``request_latched == 1 && green_ticks >= 3`` 不满足
- 执行 ``MainGreen.exit``（未定义）
- 执行转换效果：``request_latched = 1``（锁存请求）
- 执行 ``MainGreen.enter``（未定义）
- 执行 ``MainGreen.during``：``green_ticks = 1 + 1 = 2``
- **结果** ：请求被锁存，但最小绿灯尚未满足

**周期 3** （等待最小绿灯）：

- 检查 ``MainGreen -> PedestrianPhase``：``request_latched == 1 && green_ticks >= 3`` 不满足（当前：2）
- 执行 ``MainGreen.during``：``green_ticks = 2 + 1 = 3``
- **结果** ：最小绿灯时间现已满足

**周期 4** （进入行人阶段 - 黄灯）：

- 检查 ``MainGreen -> PedestrianPhase``：``request_latched == 1 && green_ticks >= 3`` 满足
- 执行 ``MainGreen.exit``（未定义）
- 执行转换效果：
  - ``request_latched = 0``（清除锁存）
  - ``yellow_ticks = 0``（重置黄灯计时器）
  - ``walk_ticks = 0``（重置过街计时器）
- 执行 ``PedestrianPhase.enter``（未定义）
- **PedestrianPhase 是复合状态**  - 跟随 ``[*] -> MainYellow``
- 执行 ``MainYellow.enter``（未定义）
- 执行 ``MainYellow.during``：``yellow_ticks = 0 + 1 = 1``
- **结果** ：黄灯清空车辆交通

**周期 5** （转换到行人过街）：

- 检查 ``MainYellow -> PedWalk``：``yellow_ticks >= 1`` 满足
- 执行 ``MainYellow.exit``（未定义）
- 执行 ``PedWalk.enter``（未定义）
- 执行 ``PedWalk.during``：``walk_ticks = 0 + 1 = 1``
- **结果** ：行人过街信号激活

**周期 6** （行人过街继续）：

- 检查 ``PedWalk -> [*]``：``walk_ticks >= 2`` 不满足（当前：1）
- 执行 ``PedWalk.during``：``walk_ticks = 1 + 1 = 2``
- **结果** ：行人过街时间满足

**周期 7** （返回主干道绿灯）：

- 检查 ``PedWalk -> [*]``：``walk_ticks >= 2`` 满足
- 执行 ``PedWalk.exit``（未定义）
- 退出到 ``PedestrianPhase``
- 检查 ``PedestrianPhase -> MainGreen``：无条件转换
- 执行 ``PedestrianPhase.exit``（未定义）
- 执行转换效果：
  - ``green_ticks = 0``（重置主干道绿灯计时器）
  - ``yellow_ticks = 0``（重置黄灯计时器）
  - ``walk_ticks = 0``（重置过街计时器）
- 执行 ``MainGreen.enter``（未定义）
- 执行 ``MainGreen.during``：``green_ticks = 0 + 1 = 1``
- **结果** ：主干道绿灯恢复，系统准备下一周期

**关键点** ：

- ``request_latched`` 实现按钮请求记忆（不需要持续按压）
- ``PedestrianPhase`` 复合状态模拟真实世界序列：黄灯 → 行人过街 → 返回
- 最小绿灯时间（``green_ticks >= 3``）防止过度中断主干道
- ``PedWalk -> [*]`` 退出到父状态，然后 ``PedestrianPhase -> MainGreen`` 完成周期
- 所有计时器在阶段转换时重置，确保下一周期的干净状态
- 自转换 ``MainGreen -> MainGreen`` 允许请求锁存而不改变状态

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

- **核心概念** ：状态类型、生命周期动作、切面动作、执行语义
- **Python 用法** ：创建运行时、执行周期、触发事件、实现处理器
- **执行语义** ：周期执行、层次执行顺序
- **最佳实践** ：设计、测试、调试、性能优化

更多信息，请探索：

- :doc:`../visualization/index` - 可视化状态机
- :doc:`../dsl/index` - 高级 DSL 特性
- :doc:`../render/index` - 从状态机生成代码
