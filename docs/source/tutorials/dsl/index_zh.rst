PyFCSTM DSL 语法教程
========================================

.. contents:: 目录
   :local:
   :depth: 3

概述
----------------------------------------------------

PyFCSTM 领域特定语言（DSL）提供了一套全面的语法，用于定义具有表达式、条件和生命周期动作的层次化有限状态机（Harel 状态图）。本教程涵盖所有语言构造、语义规则、执行模型以及编写正确高效 DSL 程序的最佳实践。

您将学到什么
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 完整的 DSL 语法和文法规则
- 层次化状态机如何执行
- 事件作用域和命名空间解析
- 表达式系统和运算符
- 生命周期动作和面向切面编程
- 实际示例和设计模式

语言结构
----------------------------------------------------

程序组织
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

一个完整的 DSL 程序由可选的变量定义和单个根状态定义组成：

.. code-block::

   program ::= def_assignment* state_definition EOF

顶层结构确保每个状态机恰好有一个根状态，该根状态可以包含嵌套的子状态和转换。

.. note::
   解析器分多个阶段处理您的 DSL 文件：

   1. **词法分析**：将输入标记化为关键字、标识符、运算符和字面量
   2. **语法分析**：按照文法规则构建抽象语法树（AST）
   3. **语义验证**：验证变量引用、状态名称和类型一致性
   4. **模型构建**：将 AST 转换为可执行的状态机模型

变量定义
----------------------------------------------------

语法
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

变量定义使用 ``def`` 关键字声明带有初始值的类型化变量：

.. code-block::

   def_assignment ::= 'def' ('int'|'float') ID '=' init_expression ';'

.. important::
   变量对整个状态机是全局的，可以从任何状态、转换或表达式中访问。DSL 支持两种基本类型：

   - **int**：32 位有符号整数，支持十进制（``42``）、十六进制（``0xFF``）和二进制（``0b1010``）字面量
   - **float**：双精度浮点数，支持标准表示法（``3.14``）和科学计数法（``1e-6``）

   所有变量必须在声明时初始化。初始表达式可以包括：

   - 字面量值（``0``、``3.14``、``0xFF``）
   - 数学常量（``pi``、``E``、``tau``）
   - 算术表达式（``3.14 * 2``、``10 + 5``）
   - 数学函数（``sin(0)``、``sqrt(16)``）

正确用法
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**整数变量：**

.. code-block::

   def int counter = 0;              // 简单初始化
   def int max_attempts = 5;         // 常量值
   def int flags = 0xFF;             // 十六进制字面量
   def int mask = 0b11110000;        // 二进制字面量
   def int computed = 10 * 5 + 3;    // 表达式初始化

**浮点变量：**

.. code-block::

   def float temperature = 25.5;     // 十进制表示法
   def float pi_value = pi;          // 数学常量
   def float ratio = 3.14 * 2;       // 表达式初始化
   def float scientific = 1.5e-3;    // 科学计数法
   def float computed = sqrt(16.0);  // 函数调用

**带注释的示例：**

.. code-block::

   // 系统状态变量
   def int system_state = 0;         // 0=初始化, 1=运行中, 2=错误
   def int error_count = 0;          // 跟踪错误发生次数

   // 传感器读数
   def float temperature = 20.0;     // 当前温度（摄氏度）
   def float target_temp = 22.0;     // 目标温度

   // 控制输出
   def int heating_power = 0;        // 加热功率（0-100%）
   def int fan_speed = 0;            // 风扇速度（0-3）

   // 系统状态的位标志
   def int status_flags = 0x00;      // 位 0：加热，位 1：冷却
                                     // 位 2：风扇，位 3：错误

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

变量定义必须遵循以下语义约束：

1. **唯一名称**：每个变量名在程序作用域内必须唯一
2. **类型一致性**：初始表达式必须求值为与声明类型兼容的值
3. **表达式有效性**：初始表达式只能引用数学常量和字面量（不能引用其他变量）
4. **声明顺序**：变量必须在根状态定义之前声明

.. tip::
   **为什么有这些规则？**

   - **唯一名称**：防止整个状态机中变量引用的歧义
   - **类型一致性**：确保类型安全并防止生成代码中的运行时错误
   - **表达式有效性**：简化初始化并确保确定性的启动状态
   - **声明顺序**：保持数据定义和行为定义之间的清晰分离

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**错误用法：**

.. code-block::

   // 错误：重复的变量名
   def int x = 1;
   def float x = 2.0;  // 语义错误：'x' 已定义

   // 错误：初始化中的未定义引用
   def int y = unknown_var;  // 语义错误：'unknown_var' 未定义

   // 错误：引用另一个变量
   def int a = 10;
   def int b = a;  // 语义错误：初始化中不能引用变量

**正确的替代方案：**

.. code-block::

   // 使用唯一名称
   def int x_int = 1;
   def float x_float = 2.0;

   // 使用字面量或常量初始化
   def int y = 0;

   // 在状态动作中赋值变量
   def int a = 10;
   def int b = 0;

   state Init {
       enter {
           b = a;  // 在生命周期动作中赋值
       }
   }

状态定义
----------------------------------------------------

.. note::
   有限状态机（FSM）是一种计算模型，在任何给定时间只能处于一个状态。机器响应事件在状态之间转换，在这些转换期间执行动作。层次化状态机（Harel 状态图）通过允许状态包含嵌套的子状态来扩展这一概念，实现模块化和可扩展的设计。

语法类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 支持两种基本类型的状态定义：

.. code-block::

   state_definition ::= leafStateDefinition | compositeStateDefinition
   leafStateDefinition ::= ['pseudo'] 'state' ID [named STRING] ';'
   compositeStateDefinition ::= ['pseudo'] 'state' ID [named STRING] '{' state_inner_statement* '}'

.. tip::
   **关键区别：**

   - **叶状态**：没有内部结构的终端状态；表示原子操作模式
   - **复合状态**：包含嵌套子状态的容器状态；表示层次化分解

叶状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

叶状态表示没有内部结构的终端状态。它们是状态机的基本构建块。

**正确用法：**

.. code-block::

   state Idle;                      // 简单叶状态
   state Running;                   // 另一个叶状态
   state Error;                     // 错误状态

   // 带显示名称的叶状态
   state Running named "系统运行中";

   // 伪叶状态（跳过祖先切面动作）
   pseudo state SpecialState;

.. tip::
   **何时使用叶状态：**

   - 表示原子操作模式（空闲、运行、错误）
   - 层次化分解中的最终状态
   - 具有简单、不可分解行为的状态

**带注释的示例：**

.. code-block::

   state TrafficLight {
       // 表示灯光颜色的叶状态
       state Red;      // 停止信号
       state Yellow;   // 警告信号
       state Green;    // 通行信号

       [*] -> Red;
       Red -> Green :: TimerExpired;
       Green -> Yellow :: TimerExpired;
       Yellow -> Red :: TimerExpired;
   }

复合状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

复合状态包含嵌套的子状态、转换和生命周期动作。它们实现复杂行为的层次化分解。

**正确用法：**

.. code-block::

   state Machine {
       // 嵌套子状态
       state Off;
       state On {
           state Slow;
           state Fast;

           [*] -> Slow;
           Slow -> Fast :: SpeedUp;
           Fast -> Slow :: SlowDown;
       }

       // 顶层状态之间的转换
       [*] -> Off;
       Off -> On : if [power_switch == 1];
       On -> Off : if [power_switch == 0];
   }

.. important::
   当复合状态处于活动状态时，其子状态中恰好有一个也处于活动状态。这创建了一个层次化的执行上下文：

   1. **进入**：进入复合状态时，入口转换（``[*] -> ChildState``）决定哪个子状态变为活动状态
   2. **期间**：活动时，复合状态的 ``during before/after`` 动作围绕子状态的动作执行
   3. **退出**：离开复合状态时，活动的子状态首先退出，然后复合状态退出

**带注释的示例：**

.. code-block::

   state PowerManagement {
       // 复合状态生命周期动作
       enter {
           // 从外部进入 PowerManagement 时执行
           power_level = 0;
       }

       during before {
           // 从外部进入子状态时执行
           // 在子状态之间转换时不执行
           monitor_counter = monitor_counter + 1;
       }

       during after {
           // 从子状态退出到外部时执行
           // 在子状态之间转换时不执行
           cleanup_flag = 1;
       }

       exit {
           // 离开 PowerManagement 到外部时执行
           power_level = 0;
       }

       // 子状态
       state LowPower {
           during {
               power_level = 10;
           }
       }

       state NormalPower {
           during {
               power_level = 50;
           }
       }

       state HighPower {
           during {
               power_level = 100;
           }
       }

       [*] -> LowPower;
       LowPower -> NormalPower :: Increase;
       NormalPower -> HighPower :: Increase;
       HighPower -> NormalPower :: Decrease;
       NormalPower -> LowPower :: Decrease;
   }

伪状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

伪状态是跳过祖先切面动作的特殊状态（叶状态或复合状态）。它们对于实现需要绕过横切关注点的特殊行为很有用。

**语法：**

.. code-block::

   pseudo state StateName;
   pseudo state StateName { ... }

.. note::
   普通状态执行父状态中定义的祖先切面动作（``>> during before/after``）。伪状态跳过这些切面动作，提供了一种选择退出横切行为的方法。

**对比示例：**

.. literalinclude:: pseudo_state_demo.fcstm
    :language: python
    :linenos:

**执行对比：**

当 ``RegularState`` 处于活动状态时：

1. 根 ``>> during before`` 执行（``aspect_counter += 1``）
2. ``RegularState.during`` 执行（``aspect_counter += 10``）
3. 根 ``>> during after`` 执行（``aspect_counter += 100``）
4. **每个周期的总增量**：111

当 ``SpecialState``（伪状态）处于活动状态时：

1. 根 ``>> during before`` **跳过**
2. ``SpecialState.during`` 执行（``aspect_counter += 10``）
3. 根 ``>> during after`` **跳过**
4. **每个周期的总增量**：10

.. tip::
   **何时使用伪状态：**

   - 实现绕过正常监控的异常处理器
   - 创建用于测试或调试的特殊状态
   - 通过跳过开销来优化性能关键状态

命名状态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

状态可以有显示名称用于文档和可视化目的：

.. code-block::

   state Running named "系统运行中";
   state Error named "错误状态 - 需要手动重置";
   state Init named "初始化阶段";

显示名称用于 PlantUML 图表和生成的文档，而状态 ID 用于代码生成。

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

状态定义必须遵守以下语义约束：

1. **唯一名称**：状态名称在其包含作用域内必须唯一（但可以在不同作用域中重用）
2. **入口转换**：复合状态必须至少有一个入口转换（``[*] -> state``）
3. **状态引用**：所有转换目标必须引用当前作用域中的现有状态
4. **层次一致性**：嵌套状态遵循正确的父子关系
5. **切面限制**：``during before/after``（不带 ``>>``）仅适用于复合状态

.. tip::
   **为什么有这些规则？**

   - **唯一名称**：防止转换目标和事件作用域的歧义
   - **入口转换**：确保进入复合状态时的确定性行为
   - **状态引用**：防止悬空转换并确保连通性
   - **层次一致性**：维护正确的状态机结构
   - **切面限制**：强制叶状态与复合状态的正确生命周期语义

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**错误用法：**

.. code-block::

   // 错误：缺少入口转换
   state Container {
       state A;
       state B;
       A -> B :: Event;  // 没有 [*] -> A 或 [*] -> B
   }

   // 错误：同一作用域中的重复状态名
   state Root {
       state Child;
       state Child;  // 语义错误：重复名称
   }

   // 错误：无效的转换目标
   state Root {
       state A;
       [*] -> A;
       A -> B :: Event;  // 语义错误：B 不存在
   }

   // 错误：叶状态上的 during before/after
   state LeafState {
       during before {  // 语义错误：叶状态不能有切面
           x = 1;
       }
   }

**正确的替代方案：**

.. code-block::

   // 提供入口转换
   state Container {
       state A;
       state B;
       [*] -> A;  // 需要入口转换
       A -> B :: Event;
   }

   // 使用唯一名称
   state Root {
       state ChildA;
       state ChildB;
   }

   // 定义所有引用的状态
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Event;
   }

   // 对叶状态使用普通 during
   state LeafState {
       during {  // 正确：没有切面关键字
           x = 1;
       }
   }

转换定义
----------------------------------------------------

.. note::
   转换定义状态机如何响应事件或条件从一个状态移动到另一个状态。每个转换可以有：

   - **源状态**：转换起源的状态
   - **目标状态**：转换指向的状态
   - **事件**：激活转换的可选触发器
   - **守卫条件**：转换触发必须为真的可选布尔表达式
   - **效果**：转换期间执行的可选动作

转换类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 支持三种具有不同语法模式的转换类型：

.. code-block::

   transition_definition ::= entryTransitionDefinition | normalTransitionDefinition | exitTransitionDefinition

入口转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

入口转换定义进入复合状态时的初始状态。它们使用伪状态 ``[*]`` 作为源。

**语法：** ``[*] -> target_state [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**正确用法：**

.. code-block::

   [*] -> Idle;                                    // 简单入口
   [*] -> Running : startup_event;                 // 带链事件的入口
   [*] -> Running :: startup_event;                // 带本地事件的入口
   [*] -> Active : if [ready_flag == 1];           // 带守卫条件的入口
   [*] -> Init effect { counter = 0; };            // 带效果的入口

.. important::
   每个复合状态必须至少有一个入口转换。入口转换决定进入复合状态时哪个子状态变为活动状态。

**带注释的示例：**

.. code-block::

   state System {
       state Idle;
       state Running;
       state Error;

       // 简单入口：进入 System 时默认进入 Idle
       [*] -> Idle;

       // 条件入口：根据标志选择初始状态
       // [*] -> Running : if [auto_start == 1];

       Idle -> Running :: Start;
       Running -> Error : if [error_detected == 1];
   }

普通转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

普通转换定义两个命名状态之间的转换。

**语法：** ``source_state -> target_state [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**正确用法：**

.. code-block::

   Idle -> Running;                                // 简单转换
   Running -> Idle :: Stop;                        // 带本地事件的转换
   Idle -> Running : /GlobalStart;                 // 带全局事件的转换
   Running -> Error : if [temp > 100];             // 带守卫条件的转换
   Idle -> Running effect { counter = 0; };        // 带效果的转换
   Running -> Idle :: Stop : if [safe_mode == 1] effect {
       counter = counter + 1;
       error_flag = 0;
   };                                              // 完整转换

.. tip::
   **转换执行顺序：**

   1. **守卫评估**：如果存在守卫条件，首先评估它。如果为假，转换不触发
   2. **源状态退出**：执行源状态的退出动作
   3. **效果执行**：如果存在，执行转换效果
   4. **目标状态进入**：执行目标状态的进入动作

**带注释的示例：**

.. code-block::

   state TrafficController {
       state Green {
           enter {
               light_color = 2;  // 绿色
               timer = 0;
           }
           during {
               timer = timer + 1;
           }
           exit {
               light_color = 0;  // 关闭
           }
       }

       state Yellow {
           enter {
               light_color = 1;  // 黄色
               timer = 0;
           }
           during {
               timer = timer + 1;
           }
       }

       state Red {
           enter {
               light_color = 0;  // 红色
               timer = 0;
           }
           during {
               timer = timer + 1;
           }
       }

       [*] -> Red;

       // 带守卫的转换：仅当计时器到期时转换
       Red -> Green : if [timer >= 30];
       Green -> Yellow : if [timer >= 25];
       Yellow -> Red : if [timer >= 5];
   }

退出转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

退出转换定义从命名状态到伪状态 ``[*]`` 的转换，表示退出当前复合状态。

**语法：** ``source_state -> [*] [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**正确用法：**

.. code-block::

   Done -> [*];                                    // 简单退出
   Error -> [*] :: FatalError;                     // 带本地事件的退出
   Finished -> [*] : /Shutdown;                    // 带全局事件的退出
   Complete -> [*] : if [all_done == 1];           // 带守卫条件的退出
   Cleanup -> [*] effect { status = 0; };          // 带效果的退出

.. note::
   退出转换将控制权返回给父状态。如果父状态有多个子状态，退出转换允许子状态完成其工作并将控制权返回给父状态的转换逻辑。

**带注释的示例：**

.. code-block::

   state TaskProcessor {
       state Processing {
           state LoadData;
           state ValidateData;
           state ProcessData;
           state SaveResults;

           [*] -> LoadData;
           LoadData -> ValidateData :: DataLoaded;
           ValidateData -> ProcessData :: DataValid;
           ProcessData -> SaveResults :: ProcessingComplete;

           // 退出转换：完成所有步骤后退出
           SaveResults -> [*] :: AllDone;

           // 错误退出：验证失败时退出
           ValidateData -> [*] : if [validation_error == 1];
       }

       state Idle;
       state Error;

       [*] -> Idle;
       Idle -> Processing :: StartTask;

       // 当 Processing 退出时，根据结果转换
       Processing -> Idle : if [error_flag == 0];
       Processing -> Error : if [error_flag == 1];
   }

强制转换
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

强制转换是一种语法糖，可以从多个源状态创建转换到单个目标状态。它们使用 ``!`` 前缀。

**语法：** ``'!' ('*'|state_name) -> target_state [: chain_id|:: event_name] [if [condition]] ';'``

.. important::
   强制转换是**语法糖**，在模型构建期间扩展为普通转换。它们**不是**特殊转换 - 它们扩展为正常执行退出动作的普通转换。

   **关键点：**

   1. **语法糖**：自动生成多个普通转换
   2. **通配符扩展**：``!*`` 从当前作用域中的所有子状态创建转换
   3. **事件共享**：所有扩展的转换共享**相同的事件对象**
   4. **正常执行**：退出动作正常执行 - 这些是常规转换
   5. **递归传播**：传播到嵌套的子状态

**正确用法：**

.. code-block::

   state System {
       state Running;
       state Idle;
       state Processing;

       [*] -> Idle;

       // 强制转换：从所有子状态到 Error
       !* -> Error :: CriticalError;

       // 等价于：
       // Running -> Error :: CriticalError;
       // Idle -> Error :: CriticalError;
       // Processing -> Error :: CriticalError;
       // 所有转换共享相同的 CriticalError 事件对象

       state Error;
   }

**扩展示例：**

.. code-block::

   state System {
       ! * -> ErrorHandler :: CriticalError;

       state Running {
           state Processing;
           state Waiting;
       }
       state Idle;

       state ErrorHandler;
   }

   // 扩展为：
   // Running -> ErrorHandler :: CriticalError;
   // Idle -> ErrorHandler :: CriticalError;
   // 并且在 Running 内部：
   //   Processing -> [*] : /CriticalError;  (退出到父状态)
   //   Waiting -> [*] : /CriticalError;     (退出到父状态)
   // 所有转换共享相同的 CriticalError 事件对象

.. tip::
   **何时使用强制转换：**

   - 当许多状态需要相同的转换时避免重复代码
   - 从多个状态进行错误处理
   - 从所有状态进行紧急关闭
   - 跨多个状态的超时处理

**关键限制：**

- 强制转换**不能**有效果块（语法限制）
- 使用目标状态的进入动作进行初始化
- 退出动作正常执行（不会被绕过）

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

转换定义必须遵守以下语义约束：

1. **有效状态引用**：源状态和目标状态必须存在于当前作用域中
2. **守卫类型**：守卫条件必须是布尔表达式
3. **效果操作**：效果块只能包含赋值操作
4. **事件作用域**：事件必须遵循正确的作用域规则（``::``、``:``、``/``）
5. **入口唯一性**：每个复合状态必须至少有一个入口转换

.. tip::
   **为什么有这些规则？**

   - **有效状态引用**：防止悬空转换并确保状态机连通性
   - **守卫类型**：确保条件可以评估为真/假
   - **效果操作**：保持转换效果简单且可预测
   - **事件作用域**：强制正确的事件命名空间和可见性
   - **入口唯一性**：确保进入复合状态时的确定性行为

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**错误用法：**

.. code-block::

   // 错误：引用不存在的状态
   state Root {
       state A;
       [*] -> A;
       A -> B :: Event;  // 语义错误：B 不存在
   }

   // 错误：守卫中的非布尔表达式
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [counter];  // 语义错误：需要布尔表达式
   }

   // 错误：效果中的非赋值操作
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B effect {
           counter + 1;  // 语义错误：不是赋值
       };
   }

   // 错误：强制转换带效果
   state Root {
       state A;
       state B;
       state Error;
       [*] -> A;
       !* -> Error :: Fail effect { x = 1; };  // 语法错误：强制转换不能有效果
   }

**正确的替代方案：**

.. code-block::

   // 定义所有引用的状态
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Event;
   }

   // 使用比较运算符创建布尔表达式
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B : if [counter > 0];
   }

   // 在效果中使用赋值
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B effect {
           counter = counter + 1;
       };
   }

   // 在目标状态的进入动作中初始化
   state Root {
       state A;
       state B;
       state Error {
           enter {
               x = 1;
           }
       }
       [*] -> A;
       !* -> Error :: Fail;
   }

事件作用域
----------------------------------------------------

.. note::
   事件是触发转换的命名触发器。DSL 提供三种事件作用域机制来控制层次化状态机中的事件命名空间。

作用域类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 提供**三种事件作用域机制**来控制层次化状态机中的事件命名空间：

**1. 本地事件**（``::`` - 作用域限定于源状态）：

.. code-block::

   StateA -> StateB :: LocalEvent;
   // 事件作用域限定于源状态：Parent.StateA.LocalEvent
   // 等价于：StateA -> StateB : /Parent.StateA.LocalEvent

每个源状态获得自己的事件。当每个转换需要唯一事件时使用。

**2. 链事件**（``:`` - 作用域限定于父状态）：

.. code-block::

   StateA -> StateB : ChainEvent;
   // 事件作用域限定于父状态：Parent.ChainEvent
   // 等价于：StateA -> StateB : /Parent.ChainEvent

同一作用域中的多个转换共享事件。当协调兄弟状态转换时使用。

**3. 绝对事件**（``/`` - 作用域限定于根状态）：

.. code-block::

   StateA -> StateB : /GlobalEvent;
   // 事件作用域限定于根状态：Root.GlobalEvent
   // 已经是绝对路径 - 不需要转换

使用相同绝对路径的所有转换共享事件。用于跨模块通信或全局事件。

事件解析示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   state System {
       state ModuleA {
           state A1;
           state A2;

           [*] -> A1;
           A1 -> A2 :: E;        // System.ModuleA.A1.E
           A1 -> A2 : E;         // System.ModuleA.E
           A1 -> A2 : /E;        // System.E
       }

       state ModuleB {
           state B1;
           state B2;

           [*] -> B1;
           B1 -> B2 :: E;        // System.ModuleB.B1.E（与 A1 的不同）
           B1 -> B2 : E;         // System.ModuleB.E（与 ModuleA 的不同）
           B1 -> B2 : /E;        // System.E（与 ModuleA 的相同）
       }
   }

.. tip::
   **关键点：**

   - ``::`` 创建状态特定的事件（避免冲突）
   - ``:`` 创建父作用域的事件（在作用域内共享）
   - ``/`` 创建根作用域的事件（全局共享）
   - 三者都等价于具有不同起点的绝对路径

实际示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**示例 1：模块间通信**

.. code-block::

   state Application {
       state UIModule {
           state Idle;
           state Busy;

           [*] -> Idle;
           // 使用全局事件与其他模块通信
           Idle -> Busy : /DataRequested;
           Busy -> Idle : /DataReceived;
       }

       state DataModule {
           state Ready;
           state Processing;

           [*] -> Ready;
           // 响应来自 UI 的全局事件
           Ready -> Processing : /DataRequested;
           Processing -> Ready : /DataReceived;
       }
   }

**示例 2：本地状态协调**

.. code-block::

   state Workflow {
       state Step1 {
           state Init;
           state Work;
           state Done;

           [*] -> Init;
           // 本地事件用于内部转换
           Init -> Work :: Start;
           Work -> Done :: Complete;
       }

       state Step2 {
           state Init;
           state Work;
           state Done;

           [*] -> Init;
           // 相同的事件名称，但作用域不同
           Init -> Work :: Start;
           Work -> Done :: Complete;
       }

       [*] -> Step1;
       // 使用链事件协调步骤
       Step1 -> Step2 : NextStep;
   }

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

事件作用域必须遵守以下语义约束：

1. **作用域一致性**：事件引用必须遵循正确的作用域规则
2. **命名空间有效性**：绝对事件路径必须从根状态开始
3. **事件唯一性**：同一作用域中的事件名称必须唯一
4. **引用有效性**：链事件和绝对事件必须引用现有事件

.. tip::
   **为什么有这些规则？**

   - **作用域一致性**：确保事件在正确的命名空间中解析
   - **命名空间有效性**：防止无效的事件路径
   - **事件唯一性**：防止同一作用域中的事件冲突
   - **引用有效性**：确保事件引用可以解析

表达式系统
----------------------------------------------------

.. important::
   fcstm DSL 严格区分算术表达式（``num_expression``）和逻辑/布尔表达式（``cond_expression``）。与常见的高级语言不同，您不能自由混合算术和逻辑操作。赋值需要算术表达式，守卫条件需要布尔表达式，比较运算符通过接受算术操作数并产生布尔结果来桥接两者。

表达式类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 支持两种基本类型的表达式：

1. **算术表达式**（``num_expression``）：求值为数值（int 或 float）
2. **条件表达式**（``cond_expression``）：求值为布尔值（true 或 false）

**示例：**

.. code-block::

   // 简单比较
   Idle -> Active : if [counter >= 10];

   // 逻辑 AND
   Normal -> Critical : if [battery_level < 10 && charging_state == 0];

   // 逻辑 OR
   LowPower -> Critical : if [temperature > 80 || error_count > 5];

   // 位运算
   Charging -> Normal : if [(battery_level >= 90) && (charging_state & 0x01)];

   // 复杂表达式
   StateA -> StateB : if [(temp > 25.0) && (flags & 0xFF) == 0x01];

转换效果
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

转换效果是在转换期间执行的操作块，在源状态退出之后但在目标状态进入之前执行。

**语法：** ``StateA -> StateB effect { operations };``

**示例：**

.. code-block::

   // 简单效果
   Idle -> Running effect {
       counter = 0;
   };

   // 多个操作
   Critical -> Charging effect {
       charging_state = 1;
       error_count = 0;
       temperature = 25;
   };

   // 复杂表达式
   Processing -> Complete effect {
       result = sin(angle) * radius;
       flags = flags | 0x01;
       counter = counter + 1;
   };

组合守卫和效果
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

转换可以同时具有守卫条件和效果：

.. code-block::

   // 守卫和效果
   Charging -> Normal : if [battery_level >= 100] effect {
       charging_state = 0;
       battery_level = 100;
   };

   // 复杂守卫和效果
   Running -> Idle : if [(timeout > 100) && (error_count == 0)] effect {
       cleanup_flag = 1;
       status = 0;
   };

完整示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

这是一个演示守卫和效果的综合示例：

.. literalinclude:: guards_and_effects.fcstm
    :language: python
    :linenos:

**可视化：**

.. figure:: guards_and_effects.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Guards and Effects Example

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

转换必须满足以下语义约束：

1. **状态存在性**：源状态和目标状态都必须存在于当前作用域中
2. **变量有效性**：条件和效果中的所有变量都必须已声明
3. **表达式类型**：守卫条件必须求值为布尔值
4. **入口要求**：复合状态至少需要一个入口转换
5. **效果作用域**：效果只能赋值给已声明的变量

**为什么有这些规则？**

- **状态存在性**：防止悬空转换
- **变量有效性**：确保所有引用都可以解析
- **表达式类型**：在守卫求值中保持类型安全
- **入口要求**：确保复合状态入口的确定性
- **效果作用域**：防止生成代码中的未定义行为

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**错误用法：**

.. code-block::

   // 错误：引用未定义的状态
   StateA -> UndefinedState :: Event;  // 语义错误

   // 错误：缺少入口转换
   state Container {
       state A;
       state B;
       A -> B :: Event;  // 没有 [*] -> A 或 [*] -> B
   }

   // 错误：守卫中的无效变量
   StateA -> StateB : if [undefined_var > 10];  // 语义错误

   // 错误：非布尔守卫
   StateA -> StateB : if [counter + 10];  // 语义错误：不是布尔值

   // 错误：无效的赋值目标
   StateA -> StateB effect {
       undefined_var = 10;  // 语义错误
   };

**正确替代方案：**

.. code-block::

   // 定义所有状态
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB :: Event;
   }

   // 提供入口转换
   state Container {
       state A;
       state B;
       [*] -> A;  // 必需
       A -> B :: Event;
   }

   // 使用已声明的变量
   def int counter = 0;
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB : if [counter > 10];  // 有效
   }

   // 使用布尔表达式
   StateA -> StateB : if [counter > 10];  // 有效：比较返回布尔值

   // 赋值给已声明的变量
   def int result = 0;
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB effect {
           result = 10;  // 有效
       };
   }

表达式系统
----------------------------------------------------

**表达式如何工作：**

DSL 提供了一个全面的表达式系统，用于数学计算、逻辑操作和条件逻辑。表达式可以出现在：

- 变量初始化（``def int x = expression;``）
- 守卫条件（``if [expression]``）
- 转换效果（``variable = expression;``）
- 生命周期动作（``variable = expression;``）

表达式层次结构
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 支持用于数学和逻辑操作的全面表达式类型：

.. code-block::

   init_expression ::= conditional_expression
   num_expression ::= conditional_expression
   cond_expression ::= conditional_expression
   conditional_expression ::= logical_or_expression ['?' expression ':' expression]
   logical_or_expression ::= logical_and_expression [('||' | 'or') logical_and_expression]*
   logical_and_expression ::= bitwise_or_expression [('&&' | 'and') bitwise_or_expression]*
   bitwise_or_expression ::= bitwise_xor_expression ['|' bitwise_xor_expression]*
   bitwise_xor_expression ::= bitwise_and_expression ['^' bitwise_and_expression]*
   bitwise_and_expression ::= equality_expression ['&' equality_expression]*
   equality_expression ::= relational_expression [('==' | '!=') relational_expression]*
   relational_expression ::= shift_expression [('<' | '>' | '<=' | '>=') shift_expression]*
   shift_expression ::= additive_expression [('<<' | '>>') additive_expression]*
   additive_expression ::= multiplicative_expression [('+' | '-') multiplicative_expression]*
   multiplicative_expression ::= power_expression [('*' | '/' | '%') power_expression]*
   power_expression ::= unary_expression ['**' unary_expression]*
   unary_expression ::= ['+' | '-' | '!' | 'not'] primary_expression
   primary_expression ::= literal | variable | function_call | '(' expression ')'

字面量值
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**整数字面量：**

.. code-block::

   def int decimal = 42;           // 十进制表示法
   def int hex = 0xFF;             // 十六进制（0x 前缀）
   def int binary = 0b11110000;    // 二进制（0b 前缀）
   def int octal = 0o755;          // 八进制（0o 前缀）

**浮点数字面量：**

.. code-block::

   def float standard = 3.14;      // 标准表示法
   def float scientific = 1.5e-3;  // 科学计数法（0.0015）
   def float large = 1E10;         // 大数（10000000000）
   def float pi_const = pi;        // 数学常量
   def float e_const = E;          // 欧拉数
   def float tau_const = tau;      // Tau（2*pi）

**布尔字面量：**

.. code-block::

   // True 值（不区分大小写）
   true, True, TRUE

   // False 值（不区分大小写）
   false, False, FALSE

运算符
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**算术运算符（按优先级，从高到低）：**

1. **括号**：``()`` - 分组
2. **一元**：``+``、``-`` - 正、负
3. **幂**：``**`` - 幂运算
4. **乘法**：``*``、``/``、``%`` - 乘、除、取模
5. **加法**：``+``、``-`` - 加、减

**比较运算符：**

- **关系**：``<``、``>``、``<=``、``>=``
- **相等**：``==``、``!=``

**逻辑运算符：**

- **一元**：``!``、``not`` - 逻辑非
- **二元**：``&&``、``and`` - 逻辑与
- **二元**：``||``、``or`` - 逻辑或

**位运算符：**

- **位与**：``&``
- **位或**：``|``
- **位异或**：``^``
- **左移**：``<<``
- **右移**：``>>``

**运算符优先级示例：**

.. code-block::

   // 不使用括号（遵循优先级）
   result = 2 + 3 * 4;              // 结果：14（乘法优先）
   result = 2 ** 3 + 1;             // 结果：9（幂运算优先）
   result = 10 / 2 + 3;             // 结果：8（除法优先）

   // 使用括号（覆盖优先级）
   result = (2 + 3) * 4;            // 结果：20
   result = 2 ** (3 + 1);           // 结果：16
   result = 10 / (2 + 3);           // 结果：2

算术与逻辑表达式分离
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. danger::
   fcstm DSL 严格区分算术表达式（``num_expression``）和逻辑/布尔表达式（``cond_expression``）。与常见的高级语言不同，您**不能**自由混合算术和逻辑操作。

   **关键规则：**

   1. **赋值需要算术表达式** - 您不能直接赋值布尔结果
   2. **守卫条件需要布尔表达式** - 您不能使用算术值作为条件
   3. **比较运算符桥接两者** - 它们接受算术操作数并产生布尔结果

**常见错误：**

.. code-block::

   // 错误：不能将布尔表达式赋值给变量
   result = (x > 10);               // 语法错误：布尔值在算术上下文中
   result = (flag1 && flag2);       // 语法错误：赋值中的逻辑操作

   // 错误：不能使用算术表达式作为条件
   StateA -> StateB : if [counter]; // 语法错误：布尔上下文中的算术
   StateA -> StateB : if [x + 5];   // 语法错误：布尔上下文中的算术

**正确用法：**

.. code-block::

   // 使用三元运算符将布尔值转换为算术值
   result = (x > 10) ? 1 : 0;       // 有效：三元返回算术值
   result = (flag1 && flag2) ? 1 : 0;  // 有效：将布尔值转换为 int

   // 在守卫条件中使用比较运算符
   StateA -> StateB : if [counter > 0];    // 有效：比较返回布尔值
   StateA -> StateB : if [x + 5 > 10];     // 有效：比较中的算术

   // 位运算在算术上下文中工作
   result = flags & 0x01;           // 有效：位运算返回算术值
   StateA -> StateB : if [(flags & 0x01) != 0];  // 有效：比较位运算结果

.. tip::
   **为什么这很重要：**

   这种分离确保了类型安全并防止了模糊的表达式。在像 C 这样的语言中，``if (x + 5)`` 是有效的（非零为真），但在 fcstm DSL 中您必须明确：``if [x + 5 > 0]``。这使状态机逻辑更清晰并防止细微的错误。

数学函数
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 提供了广泛的数学函数支持：

**三角函数：**

.. code-block::

   // 基本三角函数
   result = sin(angle);             // 正弦
   result = cos(angle);             // 余弦
   result = tan(angle);             // 正切

   // 反三角函数
   result = asin(value);            // 反正弦
   result = acos(value);            // 反余弦
   result = atan(value);            // 反正切

   // 双曲函数
   result = sinh(value);            // 双曲正弦
   result = cosh(value);            // 双曲余弦
   result = tanh(value);            // 双曲正切

**指数和对数：**

.. code-block::

   result = exp(x);                 // e^x
   result = log(x);                 // 自然对数（以 e 为底）
   result = log10(x);               // 以 10 为底的对数
   result = log2(x);                // 以 2 为底的对数

**其他数学函数：**

.. code-block::

   result = sqrt(x);                // 平方根
   result = abs(x);                 // 绝对值
   result = ceil(x);                // 向上取整
   result = floor(x);               // 向下取整
   result = round(x);               // 四舍五入到最接近的整数

条件表达式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

条件表达式使用三元运算符语法进行内联条件逻辑。

**语法：** ``(condition) ? true_value : false_value``

.. important::
   条件必须用括号括起来。

**示例：**

.. code-block::

   // 简单条件
   result = (x > 0) ? 1 : -1;

   // 使用变量
   status = (temperature > 25.0) ? 1 : 0;

   // 嵌套条件
   level = (temp > 30) ? 3 : ((temp > 20) ? 2 : 1);

   // 使用复杂条件
   value = (counter >= 10 && flags & 0x01) ? 100 : 0;

   // 分支中使用表达式
   result = (mode == 1) ? (base * 2) : (base / 2);

**常见错误：**

.. warning::
   .. code-block::

      // 错误：条件周围缺少括号
      result = x > 0 ? 1 : -1;  // 语法错误

      // 正确：需要括号
      result = (x > 0) ? 1 : -1;

完整表达式示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

这是一个演示所有表达式功能的综合示例：

.. literalinclude:: expression_demo.fcstm
    :language: python
    :linenos:

**可视化：**

.. figure:: expression_demo.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Expression System Demonstration

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

表达式必须遵循以下语义约束：

1. **变量声明**：所有引用的变量都必须已声明
2. **类型一致性**：操作必须在兼容的类型上执行
3. **函数参数**：数学函数需要适当的参数类型
4. **布尔上下文**：条件守卫必须求值为布尔值
5. **运算符兼容性**：运算符必须与兼容的操作数类型一起使用

**为什么有这些规则？**

- **变量声明**：防止未定义行为
- **类型一致性**：确保生成代码中的类型安全
- **函数参数**：防止数学操作中的运行时错误
- **布尔上下文**：在控制流中保持语义正确性
- **运算符兼容性**：确保有意义的操作

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**错误用法：**

.. code-block::

   // 错误：未定义的变量引用
   result = unknown_var + 10;  // 语义错误

   // 错误：类型不匹配（混合不兼容的类型）
   // 注意：DSL 是动态类型的，但某些操作可能会失败

   // 错误：无效的函数参数
   result = sqrt(-1);  // 可能导致运行时错误

   // 错误：格式错误的条件（缺少括号）
   result = x > 0 ? 1 : -1;  // 语法错误

**正确替代方案：**

.. code-block::

   // 声明所有变量
   def int result = 0;
   def int known_var = 10;

   state Example {
       enter {
           result = known_var + 10;  // 有效
       }
   }

   // 使用适当的函数参数
   def float value = 16.0;
   state Example {
       enter {
           result = sqrt(value);  // 有效：正参数
       }
   }

   // 在条件中使用括号
   result = (x > 0) ? 1 : -1;  // 有效

生命周期动作
----------------------------------------------------

.. note::
   **生命周期动作如何工作：**

   生命周期动作定义在状态生命周期的特定点执行的行为：

   - **Enter 动作**：进入状态时执行一次
   - **During 动作**：状态活动时重复执行
   - **Exit 动作**：离开状态时执行一次

   对于复合状态，生命周期动作可以具有**切面**（``before``/``after``），用于控制相对于子状态的执行顺序。

动作类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

状态支持三个生命周期阶段及相应的动作定义：

.. code-block::

   enter_definition ::= enterOperations | enterAbstractFunc | enterRefFunc
   during_definition ::= duringOperations | duringAbstractFunc
   exit_definition ::= exitOperations | exitAbstractFunc | exitRefFunc

   enterOperations ::= 'enter' [ID] '{' operation* '}'
   enterAbstractFunc ::= 'enter' 'abstract' ID [MULTILINE_COMMENT]
   enterRefFunc ::= 'enter' [ID] 'ref' chain_id

   duringOperations ::= 'during' ['before'|'after'] [ID] '{' operation* '}'
   duringAbstractFunc ::= 'during' ['before'|'after'] 'abstract' ID [MULTILINE_COMMENT]

   exitOperations ::= 'exit' [ID] '{' operation* '}'
   exitAbstractFunc ::= 'exit' 'abstract' ID [MULTILINE_COMMENT]
   exitRefFunc ::= 'exit' [ID] 'ref' chain_id

Enter 动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enter 动作在从外部进入状态时执行。

**具体操作：**

.. code-block::

   state Active {
       // 简单的 enter 动作
       enter {
           counter = 0;
           status_flag = 0x1;
       }

       // 命名的 enter 动作（用于引用）
       enter InitializeSystem {
           counter = 0;
           flags = 0xFF;
           temperature = 25.0;
       }
   }

**抽象函数：**

抽象 enter 动作声明必须在生成的代码中实现的函数：

.. code-block::

   state Active {
       // 简单的抽象 enter
       enter abstract initialize_system;

       // 带文档的抽象 enter
       enter abstract setup_resources /*
           初始化系统资源和外设。
           此函数必须分配内存、打开文件
           并配置硬件接口。
           TODO：在生成的代码框架中实现
       */
   }

**引用动作：**

引用动作重用其他状态的 enter 动作：

.. code-block::

   state BaseState {
       enter CommonInit {
           counter = 0;
           flags = 0xFF;
       }
   }

   state DerivedState {
       // 重用 BaseState 的 enter 动作
       enter ref BaseState.CommonInit;

       // 也可以引用全局动作
       enter ref /GlobalInit;
   }

During 动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During 动作在状态活动时执行。叶状态和复合状态的行为不同。

**叶状态 During 动作：**

叶状态使用不带切面关键字的普通 ``during``：

.. code-block::

   state Running {
       // 在 Running 活动时每个周期执行
       during {
           heartbeat_counter = heartbeat_counter + 1;
           temperature = temperature + 0.1;
       }
   }

**复合状态 During 动作：**

复合状态必须使用 ``before`` 或 ``after`` 切面：

.. code-block::

   state Parent {
       // 从外部进入子状态时执行
       // 在子状态之间转换时不执行
       during before {
           monitor_counter = monitor_counter + 1;
       }

       // 从子状态退出到外部时执行
       // 在子状态之间转换时不执行
       during after {
           cleanup_flag = 1;
       }

       state Child1;
       state Child2;

       [*] -> Child1;
       Child1 -> Child2 :: Switch;  // during before/after 不触发
       Child2 -> [*];
   }

**抽象 During 动作：**

.. code-block::

   state Processing {
       // 叶状态抽象 during
       during abstract process_data;

       // 带文档
       during abstract process_data /*
           处理传入的数据包。
           TODO：实现数据处理逻辑
       */
   }

   state Container {
       // 带切面的复合状态抽象 during
       during before abstract pre_process /*
           子状态执行前的预处理。
           TODO：实现预处理逻辑
       */

       during after abstract post_process;

       state Child;
       [*] -> Child;
   }

Exit 动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exit 动作在离开状态到外部时执行。

**具体操作：**

.. code-block::

   state Active {
       exit {
           save_state = current_value;
           cleanup_flag = 0x1;
           status = 0;
       }

       // 命名的 exit 动作
       exit CleanupResources {
           flags = 0x00;
           counter = 0;
       }
   }

**抽象函数：**

.. code-block::

   state Active {
       exit abstract cleanup_resources;

       exit abstract finalize_operations /*
           退出前清理资源。
           释放内存、关闭文件并关闭硬件。
           TODO：在生成的代码框架中实现
       */
   }

**引用动作：**

.. code-block::

   state BaseState {
       exit CommonCleanup {
           cleanup_flag = 1;
           counter = 0;
       }
   }

   state DerivedState {
       exit ref BaseState.CommonCleanup;
   }

切面动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

切面动作使用 ``>>`` 前缀应用于**所有后代叶状态**。

**语法：**

.. code-block::

   state Root {
       // 在每个后代叶状态的 during 动作之前执行
       >> during before {
           global_counter = global_counter + 1;
       }

       // 在每个后代叶状态的 during 动作之后执行
       >> during after {
           global_counter = global_counter + 100;
       }

       state Child {
           state GrandChild {
               during {
                   local_counter = local_counter + 10;
               }
           }

           [*] -> GrandChild;
       }

       [*] -> Child;
   }

**GrandChild 的执行顺序：**

1. ``Root >> during before``（``global_counter += 1``）
2. ``GrandChild.during``（``local_counter += 10``）
3. ``Root >> during after``（``global_counter += 100``）

层次化执行顺序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

理解层次化状态机中的执行顺序至关重要。这是一个完整的示例：

.. literalinclude:: hierarchy_execution.fcstm
    :language: python
    :linenos:

**可视化：**

.. figure:: hierarchy_execution.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Hierarchical Execution Order

.. important::
   **执行场景：**

   **场景 1：初始进入**（``HierarchyDemo -> Parent -> ChildA``）

   1. ``HierarchyDemo.enter``（如果定义）
   2. ``Parent.enter``（如果定义）
   3. ``Parent.during before`` 执行（``execution_log += 100``）
   4. ``ChildA.enter``（如果定义）

   **场景 2：During 阶段**（当 ``ChildA`` 活动时，每个周期）

   1. ``HierarchyDemo >> during before``（``execution_log += 1000``）
   2. ``Parent >> during before``（``execution_log += 10``）
   3. ``ChildA.during``（``execution_log += 1``）
   4. ``Parent >> during after``（``execution_log += 90``）
   5. ``HierarchyDemo >> during after``（``execution_log += 9000``）

   **每个周期总计**：10101

   **场景 3：子状态之间的转换**（``ChildA -> ChildB :: Switch``）

   1. ``ChildA.exit``（如果定义）
   2. 转换效果（如果有）
   3. ``ChildB.enter``（如果定义）

   **关键**：``Parent.during before/after`` **不**执行！

   **场景 4：从复合状态退出**（``ChildB -> [*] :: Exit``）

   1. ``ChildB.exit``（如果定义）
   2. ``Parent.during after`` 执行（``execution_log += 900``）
   3. ``Parent.exit``（如果定义）
   4. ``HierarchyDemo.exit``（如果定义）

**生命周期流程图：**

.. list-table::
   :widths: 55 45
   :align: center

   * - .. figure:: composite_state_lifecycle.puml.svg
          :width: 100%
          :align: center
          :alt: Lifecycle of Composite States

     - .. figure:: leaf_state_lifecycle.puml.svg
          :width: 100%
          :align: center
          :alt: Lifecycle of Leaf States

抽象和引用动作示例
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

这是一个演示抽象函数和动作引用的完整示例：

.. literalinclude:: abstract_reference_demo.fcstm
    :language: python
    :linenos:

**可视化：**

.. figure:: abstract_reference_demo.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Abstract and Reference Actions

语义规则
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

生命周期动作必须遵守以下约束：

1. **变量有效性**：所有引用的变量都必须已声明
2. **切面限制**：``before`` 和 ``after`` 切面仅适用于复合状态
3. **赋值目标**：只能为已声明的变量赋值
4. **表达式类型**：赋值表达式必须类型兼容
5. **引用有效性**：引用的动作必须存在于指定的状态中

.. tip::
   **为什么有这些规则？**

   - **变量有效性**：防止未定义行为
   - **切面限制**：强制执行正确的生命周期语义
   - **赋值目标**：确保所有赋值都有效
   - **表达式类型**：保持类型安全
   - **引用有效性**：防止悬空引用

常见错误
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
   **错误用法：**

   .. code-block::

      // 错误：动作中的未定义变量
      state Example {
          enter {
              undefined_var = 10;  // 语义错误
          }
      }

      // 错误：叶状态上的切面
      state LeafState {
          during before {  // 语义错误：叶状态不能有切面
              x = 1;
          }
      }

      // 错误：复合状态上的普通 during
      state CompositeState {
          state Child;
          [*] -> Child;

          during {  // 语义错误：复合状态需要 before/after
              x = 1;
          }
      }

      // 错误：无效引用
      state Example {
          enter ref NonExistentState.Action;  // 语义错误
      }

**正确替代方案：**

.. code-block::

   // 声明所有变量
   def int result = 0;

   state Example {
       enter {
           result = 10;  // 有效
       }
   }

   // 对叶状态使用普通 during
   state LeafState {
       during {  // 正确
           result = 1;
       }
   }

   // 对复合状态使用切面
   state CompositeState {
       state Child;
       [*] -> Child;

       during before {  // 正确
           result = 1;
       }
   }

   // 引用现有动作
   state BaseState {
       enter CommonInit {
           result = 0;
       }
   }

   state DerivedState {
       enter ref BaseState.CommonInit;  // 有效
   }

实际示例：智能恒温器
----------------------------------------------------

为了在实际环境中演示所有 DSL 功能，这是一个全面的智能恒温器控制器实现：

.. literalinclude:: thermostat_example.fcstm
    :language: python
    :linenos:

**可视化：**

.. figure:: thermostat_example.fcstm.puml.svg
   :width: 90%
   :align: center
   :alt: Smart Thermostat State Machine

.. tip::
   **演示的关键设计模式：**

   1. **层次化分解**：``OperationalMode`` 包含多个子模式（Idle、Heating、Cooling、AutoMode）
   2. **面向切面编程**：全局 ``>> during before/after`` 用于日志记录和显示更新
   3. **比例控制**：根据温度差计算加热/冷却功率
   4. **自动模式切换**：``AutoMode`` 智能地在加热、冷却和空闲之间切换
   5. **错误处理**：在异常条件下转换到 ``ErrorState``
   6. **维护调度**：1000 个周期后自动转换到维护
   7. **抽象函数**：硬件特定操作声明为抽象，用于平台实现

**执行流程示例：**

从 ``Initializing`` 开始：

1. 系统执行自检（抽象函数）
2. 如果 ``error_code == 0``，转换到 ``OperationalMode.Idle``
3. ``OperationalMode.during before`` 执行（递增 ``runtime_hours``）
4. 在 ``Idle`` 中：
   - 全局 ``>> during before`` 记录系统状态
   - ``Idle.during`` 递增 ``maintenance_counter``
   - 全局 ``>> during after`` 更新显示
5. 如果 ``current_temp < target_temp - 1``，转换到 ``Heating``
6. 在 ``Heating`` 中：
   - ``Heating.during`` 计算比例加热功率
   - 如果 ``current_temp >= target_temp``，转换回 ``Idle``
7. 1000 个周期后，转换到 ``Maintenance``

注释样式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 支持多种注释格式用于文档：

**行注释：**

.. code-block::

   // C++ 风格的行注释
   # Python 风格的行注释

   def int counter = 0;  // 内联注释
   def int flags = 0xFF; # 另一个内联注释

**块注释：**

.. code-block::

   /*
    * 多行块注释
    * 用于详细文档
    */

**抽象函数文档：**

.. code-block::

   enter abstract InitializeHardware /*
       初始化硬件外设和传感器。

       此函数必须：
       1. 配置 GPIO 引脚
       2. 初始化 SPI/I2C 接口
       3. 校准传感器
       4. 验证硬件连接

       返回：成功时返回 0，失败时返回错误代码
       TODO：在生成的代码框架中实现
   */

文档最佳实践
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**变量文档：**

.. code-block::

   // 系统状态变量
   def int system_state = 0;         // 0=初始化，1=运行，2=错误
   def int error_count = 0;          // 启动以来的错误数

   // 传感器读数（SI 单位）
   def float temperature = 20.0;     // 温度（摄氏度）
   def float pressure = 101.325;     // 压力（kPa）

   // 控制输出（0-100 范围）
   def int heating_power = 0;        // 加热功率百分比
   def int cooling_power = 0;        // 冷却功率百分比

**状态文档：**

.. code-block::

   state System {
       // 初始化阶段 - 启动时运行一次
       state Initializing {
           enter {
               // 将所有系统变量重置为安全默认值
               error_count = 0;
               system_state = 0;
           }
       }

       // 正常操作 - 主系统循环
       state Running {
           // 活动处理状态
           state Active {
               during {
                   // 为看门狗递增心跳计数器
                   heartbeat = heartbeat + 1;
               }
           }

           // 空闲状态 - 低功耗模式
           state Idle;

           [*] -> Active;
       }

       [*] -> Initializing;
       Initializing -> Running : if [error_count == 0];
   }

**转换文档：**

.. code-block::

   // 当电池电量低且没有关键任务活动时
   // 转换到低功耗模式
   Normal -> LowPower : if [
       (battery_level < 30) &&
       (charging_state == 0) &&
       (critical_task_active == 0)
   ] effect {
       // 降低系统时钟频率
       clock_divider = 8;
       // 禁用非必要外设
       peripheral_enable = 0x01;
   };

语义验证规则
----------------------------------------------------

全面验证
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DSL 解析器在解析过程中执行广泛的语义验证：

**变量验证：**

1. 程序中的变量名称唯一
2. 所有引用的变量都必须已声明
3. 赋值和表达式中的类型一致性
4. 有效的初始化表达式

**状态验证：**

1. 每个作用域内的状态名称唯一
2. 所有转换中的有效状态引用
3. 复合状态需要入口转换
4. 正确的层次化嵌套

**表达式验证：**

1. 格式良好的数学和逻辑表达式
2. 带有适当参数的有效函数调用
3. 正确的运算符优先级和结合性
4. 操作中的类型兼容性

**结构验证：**

1. 复合状态的正确嵌套
2. 有效的生命周期动作放置
3. 正确的转换连接性
4. 切面动作限制

错误处理
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

解析器为常见错误提供详细的错误消息：

**语法错误：**

- 格式错误的表达式和语句
- 缺少标点符号和关键字
- 无效的标记序列
- 不正确的运算符使用

**语义错误：**

- 未定义的变量或状态引用
- 操作中的类型不匹配
- 结构不一致
- 无效的生命周期动作放置

**错误消息示例：**

.. code-block::

   Error: Undefined variable 'unknown_var' at line 15
   Error: Duplicate state name 'Active' in scope 'System' at line 23
   Error: Missing entry transition for composite state 'Container' at line 45
   Error: Invalid aspect 'before' on leaf state 'Running' at line 67

总结
----------------------------------------------------

本教程涵盖了完整的 PyFCSTM DSL 语法，包括：

- **变量定义**：带有初始化表达式的类型化变量
- **状态定义**：叶状态、复合状态、伪状态和命名状态
- **转换**：带有守卫和效果的入口、普通、退出和强制转换
- **强制转换**：扩展为多个共享事件的普通转换的语法糖
- **事件作用域**：三种机制 - 本地事件（``::``）、链事件（``:``）和绝对事件（``/``）
- **事件命名空间**：理解事件如何在层次化状态机中解析
- **表达式**：全面的运算符支持和数学函数
- **生命周期动作**：带有面向切面编程的 enter、during 和 exit 动作
- **层次化执行**：复合状态和叶状态中嵌套状态的执行顺序
- **抽象函数**：声明平台特定的实现
- **引用动作**：跨状态重用动作
- **注释**：用于文档的行注释和块注释

.. important::
   **关键概念：**

   - **层次化状态机**：状态可以包含嵌套的子状态，实现模块化设计
   - **面向切面编程**：``>> during before/after`` 动作应用于所有后代叶状态
   - **复合状态生命周期**：``during before/after`` 仅在进入/退出时执行，在子状态之间转换时不执行
   - **事件命名空间**：三种作用域机制（``::`` 用于本地，``:`` 用于链，``/`` 用于绝对）
   - **事件解析**：所有事件作用域机制都等同于具有不同起点的绝对路径
   - **语义验证**：全面的验证确保正确的状态机定义

.. seealso::
   **其他资源：**

   - 文法定义：``pyfcstm/dsl/grammar/Grammar.g4``
   - 解析器实现：``pyfcstm/dsl/parse.py``
   - 模型系统：``pyfcstm/model/model.py``
   - 测试套件：``test/testfile/sample_codes/``

   有关实现细节，请参阅文法定义、解析管道和模型系统文档。测试套件为复杂用例提供了额外的示例和验证模式。
