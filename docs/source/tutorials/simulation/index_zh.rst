FCSTM 仿真指南
===============================================

本指南全面介绍如何仿真 FCSTM DSL 定义的有限状态机。您将学习如何逐步执行状态机、理解执行语义、处理事件、实现抽象动作以及调试复杂的层次状态机。

概述
---------------------------------------

pyfcstm 仿真运行时提供了一个基于 Python 的 FCSTM 状态机执行环境。它允许您：

- **交互式执行状态机**：逐周期运行状态机，完全可控
- **动态触发事件**：在执行期间发送事件以触发转换
- **实现抽象动作**：为 DSL 中声明的抽象动作定义自定义 Python 处理器
- **检查运行时状态**：访问当前状态、变量和执行历史
- **调试复杂逻辑**：理解层次执行顺序和切面动作行为

仿真运行时非常适合：

- **测试状态机逻辑**：在代码生成之前验证行为
- **原型设计**：快速迭代状态机设计
- **教育**：通过交互式示例学习 FCSTM 执行语义
- **调试**：跟踪复杂层次状态机中的执行流程

核心概念
---------------------------------------

状态类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

仿真运行时区分不同的状态类型：

- **叶状态**：没有子状态的状态（可以执行 ``during`` 动作）
- **复合状态**：包含子状态的状态（需要初始转换）
- **伪状态**：跳过祖先切面动作的特殊叶状态
- **可停止状态**：一个周期可以结束的叶状态（非伪状态）

生命周期动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

状态可以定义三种类型的生命周期动作：

- **enter**：进入状态时执行
- **during**：保持在状态中时执行（每个周期）
- **exit**：离开状态时执行

切面动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

切面动作将横切行为应用于后代状态：

- **>> during before**：在任何后代叶状态的 ``during`` 动作之前执行
- **>> during after**：在任何后代叶状态的 ``during`` 动作之后执行
- 伪状态跳过祖先切面动作

复合状态动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

复合状态可以为边界转换定义特殊动作：

- **during before**（不带 ``>>``）：从父状态进入复合状态时执行（``[*] -> Child``）
- **during after**（不带 ``>>``）：从复合状态退出到父状态时执行（``Child -> [*]``）
- **不执行**：在子状态到子状态的转换期间（``Child1 -> Child2``）

执行语义
---------------------------------------

步进语义
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

一个 **步进** 执行单个转换或单个 ``during`` 动作：

1. **如果在叶状态中**：
   - 按定义顺序检查当前状态的所有转换
   - 执行第一个满足守卫条件的转换
   - 如果没有转换触发，执行当前状态的 ``during`` 动作（包括祖先切面动作）

2. **如果在复合状态中**：
   - 按定义顺序检查所有初始转换（``[*] -> Child``）
   - 执行第一个满足守卫条件的转换

**转换执行顺序**：

1. 执行源状态的 ``exit`` 动作
2. 执行转换的 ``effect`` 块
3. 执行目标状态的 ``enter`` 动作
4. 如果目标是复合状态，继续执行初始转换

周期语义
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

一个 **周期** 执行直到达到稳定边界：

1. 执行转换并跟随必要的链，直到以下之一：
   - 到达 **可停止状态**（叶状态，非伪状态）
   - 确认无法到达可停止状态
   - 状态机终止

2. 如果到达可停止状态，执行其 ``during`` 动作

**关键点**：

- 一个周期可能执行多个转换（例如，通过伪状态）
- 一个周期总是在可停止状态或终止时结束
- ``during`` 动作在每个周期的最终可停止状态只执行一次

层次执行顺序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

理解层次状态机中的执行顺序至关重要。考虑这个例子：

.. code-block:: fcstm

   state System {
       >> during before { /* 切面动作 */ }
       >> during after { /* 切面动作 */ }

       state Parent {
           during before { /* 复合边界动作 */ }
           during after { /* 复合边界动作 */ }

           state Child {
               during { /* 叶动作 */ }
           }

           [*] -> Child;
       }
   }

**场景 1：初始进入**（``System -> Parent -> Child``）

进入阶段：

1. ``System.enter``
2. ``Parent.enter``
3. ``Parent.during before``（由 ``[*] -> Child`` 触发）
4. ``Child.enter``

During 阶段（``Child`` 活动时的每个周期）：

1. ``System >> during before``（切面动作）
2. ``Child.during``（叶动作）
3. ``System >> during after``（切面动作）

注意：``Parent.during before/after`` 在 ``during`` 阶段不执行。

**场景 2：子状态到子状态的转换**（``Child1 -> Child2``）

1. ``Child1.exit``
2. （转换效果，如果有）
3. ``Child2.enter``

关键：``Parent.during before/after`` 在子状态到子状态的转换期间不触发。

**场景 3：从复合状态退出**（``Child -> [*]``）

1. ``Child.exit``
2. ``Parent.during after``（由 ``Child -> [*]`` 触发）
3. ``Parent.exit``
4. ``System.exit``

示例状态机
---------------------------------------

在本指南中，我们将使用以下示例状态机：

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

该状态机演示了：

- **变量**：``counter``、``error_count``、``temperature``
- **层次状态**：``Active`` 包含 ``Processing`` 和 ``Waiting``
- **生命周期动作**：``enter``、``during``、``exit``
- **切面动作**：``>> during before`` 包含抽象和具体动作
- **复合状态动作**：``Active.during before``
- **带守卫的转换**：``Initializing -> Active : if [counter >= 10]``
- **带效果的转换**：``Active -> Idle :: Stop effect { counter = 0; }``
- **强制转换**：``!* -> Error :: FatalError``
- **抽象动作**：``GlobalMonitor``、``HardwareInit``

基本用法
---------------------------------------

创建仿真运行时
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

创建仿真运行时的基本工作流程：

1. 将 DSL 代码解析为 AST
2. 将 AST 转换为状态机模型
3. 创建 ``SimulationRuntime`` 实例
4. 执行周期

**示例**

.. literalinclude:: basic_usage.demo.py
   :language: python
   :caption: 基本仿真用法

输出：

.. literalinclude:: basic_usage.demo.py.txt
   :language: text

**关键点**：

- ``runtime.cycle()``：执行一个完整的周期
- ``runtime.current_state``：获取当前状态路径（例如，``'System.Idle'``）
- ``runtime.vars``：以字典形式访问状态机变量
- 第一次 ``cycle()`` 调用初始化状态机（遵循初始转换）

访问运行时状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``SimulationRuntime`` 提供了几个用于检查状态的属性：

.. code-block:: python

   # 当前状态路径
   state_path = runtime.current_state  # 例如，'System.Active.Processing'

   # 变量访问
   counter_value = runtime.vars['counter']
   runtime.vars['counter'] = 10  # 修改变量

   # 检查是否终止
   if runtime.is_terminated:
       print("状态机已终止")

   # 获取状态对象
   state_obj = runtime.get_current_state_object()
   print(f"状态名称：{state_obj.name}")
   print(f"是否为叶状态：{state_obj.is_leaf_state}")

事件触发
---------------------------------------

事件触发状态机中的转换。仿真运行时支持动态事件触发。

DSL 中的事件语法
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FCSTM 支持三种事件作用域机制：

- **局部事件**（``::``）：作用域为源状态（例如，``StateA -> StateB :: LocalEvent``）
- **链式事件**（``:``）：作用域为父状态（例如，``StateA -> StateB : ChainEvent``）
- **绝对事件**（``/``）：作用域为根状态（例如，``StateA -> StateB : /GlobalEvent``）

在 Python 中触发事件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

将事件名称传递给 ``cycle()`` 以触发转换：

.. literalinclude:: event_triggering.demo.py
   :language: python
   :caption: 事件触发示例

输出：

.. literalinclude:: event_triggering.demo.py.txt
   :language: text

**关键点**：

- 将事件名称作为列表传递给 ``cycle()``：``runtime.cycle(['Start'])``
- 事件名称根据作用域规则解析
- 可以提供多个事件：``runtime.cycle(['Event1', 'Event2'])``
- 事件按提供的顺序检查
- 如果没有事件匹配，状态机执行 ``during`` 动作

事件解析
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

运行时将事件名称解析为完整的事件路径：

.. code-block:: python

   # 对于转换：Idle -> Active :: Start
   # 事件作用域为源状态：System.Idle.Start
   runtime.cycle(['Start'])  # 匹配 System.Idle.Start

   # 对于转换：Idle -> Active : Start
   # 事件作用域为父状态：System.Start
   runtime.cycle(['Start'])  # 匹配 System.Start

   # 对于转换：Idle -> Active : /Start
   # 事件作用域为根状态：System.Start
   runtime.cycle(['Start'])  # 匹配 System.Start

抽象动作
---------------------------------------

抽象动作声明必须在 Python 中实现的函数。这允许您将自定义逻辑与状态机集成。

声明抽象动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在 DSL 中，使用 ``abstract`` 关键字：

.. code-block:: fcstm

   state Active {
       enter abstract Init;
       during abstract Monitor;
       exit abstract Cleanup;
   }

实现抽象处理器
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 ``@abstract_handler`` 装饰器实现处理器：

.. literalinclude:: abstract_handlers.demo.py
   :language: python
   :caption: 抽象动作处理器

输出：

.. literalinclude:: abstract_handlers.demo.py.txt
   :language: text

**关键点**：

- 使用 ``@abstract_handler('State.Path.ActionName')`` 注册处理器
- 处理器接收一个包含运行时信息的 ``context`` 对象
- 使用 ``runtime.register_handlers_from_object(handler_obj)`` 注册处理器
- 处理器可以通过 ``ctx.get_var('name')`` 和 ``ctx.set_var('name', value)`` 访问变量
- 处理器可以通过 ``ctx.get_full_state_path()`` 检查状态

处理器上下文 API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

传递给处理器的上下文对象提供：

.. code-block:: python

   @abstract_handler('System.Active.Monitor')
   def handle_monitor(self, ctx):
       # 获取当前状态路径
       state_path = ctx.get_full_state_path()  # 例如，'System.Active'

       # 访问变量
       counter = ctx.get_var('counter')
       ctx.set_var('counter', counter + 1)

       # 获取状态对象
       state = ctx.get_state()
       print(f"状态名称：{state.name}")

       # 访问运行时
       runtime = ctx.get_runtime()
       print(f"当前状态：{runtime.current_state}")

层次执行
---------------------------------------

理解动作在层次状态机中的执行方式对于正确行为至关重要。

切面动作示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: hierarchy_execution.demo.py
   :language: python
   :caption: 层次执行顺序

输出：

.. literalinclude:: hierarchy_execution.demo.py.txt
   :language: text

**解释**：

- **周期 1**（初始化）：在进入期间执行 ``Parent.during before``（100），因为 ``[*] -> Child``
- **周期 2**（during 阶段）：执行 ``>> during before``（1）+ ``Child.during``（10）
- **周期 3**（during 阶段）：与周期 2 相同
- ``Parent.during before`` 在 ``during`` 阶段不执行

执行顺序总结
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**进入阶段**（从父状态）：

1. ``State.enter``
2. ``State.during before``（如果通过 ``[*] -> Child`` 从父状态进入）
3. ``Child.enter``

**During 阶段**（每个周期）：

1. 祖先 ``>> during before`` 动作（从根到叶）
2. 叶状态 ``during`` 动作
3. 祖先 ``>> during after`` 动作（从叶到根）

**退出阶段**（到父状态）：

1. ``Child.exit``
2. ``State.during after``（如果通过 ``Child -> [*]`` 退出到父状态）
3. ``State.exit``

**子状态到子状态的转换**：

1. ``Child1.exit``
2. （转换效果）
3. ``Child2.enter``
4. 不执行 ``during before/after``

伪状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

伪状态跳过祖先切面动作：

.. code-block:: fcstm

   state System {
       >> during before { counter = counter + 1; }

       pseudo state SpecialState {
           during { counter = counter + 10; }
       }
   }

当 ``SpecialState`` 活动时：

- ``System >> during before`` 不执行
- 只执行 ``SpecialState.during``

高级特性
---------------------------------------

多周期执行
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在循环中执行多个周期：

.. code-block:: python

   # 执行 10 个周期
   for i in range(10):
       runtime.cycle()
       print(f"周期 {i+1}：状态={runtime.current_state}，计数器={runtime.vars['counter']}")

   # 执行直到终止
   while not runtime.is_terminated:
       runtime.cycle()

条件执行
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用守卫控制转换：

.. code-block:: python

   # 带守卫的状态机
   dsl_code = """
   def int counter = 0;

   state System {
       [*] -> Idle;

       state Idle {
           during { counter = counter + 1; }
       }

       state Active;

       Idle -> Active : if [counter >= 5];
   }
   """

   runtime = SimulationRuntime(sm)

   # 执行直到转换触发
   while runtime.current_state == 'System.Idle':
       runtime.cycle()
       print(f"计数器：{runtime.vars['counter']}")

   print(f"转换到：{runtime.current_state}")

调试技巧
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. 每个周期后打印状态和变量**：

.. code-block:: python

   runtime.cycle()
   print(f"状态：{runtime.current_state}")
   print(f"变量：{runtime.vars}")

**2. 使用抽象处理器跟踪执行**：

.. code-block:: python

   @abstract_handler('System.Active.Monitor')
   def trace_monitor(self, ctx):
       print(f"[跟踪] Monitor 在 {ctx.get_full_state_path()} 被调用")
       print(f"[跟踪] 变量：{dict(ctx.get_runtime().vars)}")

**3. 检查状态对象**：

.. code-block:: python

   state_obj = runtime.get_current_state_object()
   print(f"状态：{state_obj.name}")
   print(f"是否为叶状态：{state_obj.is_leaf_state}")
   print(f"是否为伪状态：{state_obj.is_pseudo}")
   print(f"转换数量：{len(state_obj.transitions)}")

**4. 手动检查转换守卫**：

.. code-block:: python

   for transition in state_obj.transitions:
       if transition.guard:
           print(f"守卫：{transition.guard.to_dsl()}")

最佳实践
---------------------------------------

状态机设计
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **保持状态专注**：每个状态应该有明确的单一职责
- **使用层次状态**：将相关状态分组到复合状态下
- **最小化切面动作**：谨慎使用切面动作处理横切关注点
- **记录抽象动作**：为抽象动作声明添加注释

仿真测试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **测试初始化**：验证状态机到达正确的初始状态
- **测试所有转换**：确保所有转换在正确条件下触发
- **测试守卫**：验证守卫条件按预期工作
- **测试效果**：检查转换效果是否正确修改变量
- **测试终止**：确保状态机在预期时终止

处理器实现
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **保持处理器简单**：处理器应该轻量且专注
- **避免副作用**：最小化处理器中的外部状态修改
- **使用上下文 API**：通过上下文对象访问运行时状态
- **记录处理器执行**：添加日志以调试复杂交互

性能考虑
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **限制周期数**：通过检查终止条件避免无限循环
- **优化守卫**：保持守卫表达式简单以加快评估
- **最小化切面动作**：切面动作在每个周期都执行
- **使用伪状态**：在不需要时跳过切面动作

常见陷阱
---------------------------------------

切面动作混淆
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**问题**：期望 ``during before/after``（不带 ``>>``）在 ``during`` 阶段执行。

**解决方案**：记住复合状态的 ``during before/after`` 只在进入/退出转换期间执行（``[*] -> Child`` 或 ``Child -> [*]``），而不是在 ``during`` 阶段。

事件作用域问题
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**问题**：由于作用域不正确，事件未触发转换。

**解决方案**：理解事件作用域：

- ``::`` 创建状态特定的事件
- ``:`` 创建父作用域的事件
- ``/`` 创建根作用域的事件

变量初始化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**问题**：变量在使用前未初始化。

**解决方案**：始终在 DSL 顶部定义带初始值的变量：

.. code-block:: fcstm

   def int counter = 0;
   def float temperature = 25.0;

缺少抽象处理器
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**问题**：抽象动作已声明但未实现，导致运行时错误。

**解决方案**：在运行仿真之前实现所有抽象处理器：

.. code-block:: python

   # 检查缺少的处理器
   runtime = SimulationRuntime(sm)
   handlers = MyHandlers()
   runtime.register_handlers_from_object(handlers)

   # 如果缺少处理器，这将引发错误
   runtime.cycle()

下一步
---------------------------------------

- 探索 :doc:`../visualization/index` 以可视化您的状态机
- 了解 :doc:`../dsl/index` 的高级 DSL 特性
- 查看 :doc:`../render/index` 从状态机生成代码
- 阅读 :doc:`../cli/index` 了解命令行仿真工具

总结
---------------------------------------

本指南涵盖了：

- 核心概念：状态类型、生命周期动作、切面动作、执行语义
- 基本用法：创建运行时、执行周期、访问状态
- 事件触发：动态事件处理和作用域
- 抽象动作：使用 ``@abstract_handler`` 装饰器实现自定义处理器
- 层次执行：理解嵌套状态中的执行顺序
- 高级特性：多周期、条件执行、调试
- 最佳实践：设计、测试、处理器实现、性能
- 常见陷阱：切面动作、事件作用域、变量初始化

仿真运行时为在代码生成之前测试、原型设计和理解 FCSTM 状态机提供了强大的环境。
