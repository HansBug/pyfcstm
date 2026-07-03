PyFCSTM DSL 第一个模型教程
==========================

.. contents:: 目录
   :local:
   :depth: 2

概述
----

本页是编写第一个 FCSTM DSL 模型的短学习路径，不再承担完整语言参考职责。需要任务步骤、语法事实或语义解释时，请转到：

* :doc:`../../how_to/dsl/index_zh`：面向任务的 DSL 写法。
* :doc:`../../reference/dsl/index_zh`：语法形式、运算符和边界表。
* :doc:`../../explanations/dsl_semantics/index_zh`：DSL 语义和设计取舍。

本页示例会构造一个可以解析并仿真的小控制器。

语言结构
--------

DSL 文件先写变量声明，然后写且只写一个根 ``state``：

.. code-block:: fcstm

   def int counter = 0;

   state Controller {
       [*] -> Idle;
       state Idle;
   }

变量是持久模型变量。当前基础类型是 ``int`` 和 ``float``。根状态通常是一个 composite state，用来拥有子状态和转换。

变量定义
--------

变量必须在根状态之前声明。初始值可以使用数字字面量、常量、算术表达式和支持的数学函数：

.. code-block:: fcstm

   def int retries = 0;
   def int flags = 0x00;
   def float target = 22.5;
   def float radius = sqrt(16.0);

声明后可以在 guard 和操作块里使用变量：

.. code-block:: fcstm

   def int count = 0;

   state Counter {
       [*] -> Ready;
       state Ready {
           during {
               count = count + 1;
           }
       }
   }

完整字面量和表达式表见 :doc:`../../reference/dsl/index_zh`。

状态定义
--------

leaf state 以 ``;`` 结束。composite state 在 ``{ ... }`` 中包含子声明，并且必须用 ``[*] -> Child;`` 选择初始子状态：

.. code-block:: fcstm

   state Door {
       [*] -> Closed;

       state Closed;
       state Open;
   }

层级状态用于描述嵌套行为。转换应该写在 source 和 target 名称可以被解析到的作用域中。不要从外层直接跳到某个 composite 内部 leaf；应把转换写在拥有该 leaf 的 composite 内。

转换定义
--------

最常见的转换形式是 plain transition、event transition、guard transition 和 guard-plus-effect transition：

.. code-block:: fcstm

   state Controller {
       event Tick;
       [*] -> Idle;

       state Idle;
       state Active;

       Idle -> Active :: Tick;
       Active -> Idle : if [counter >= 3] effect {
           counter = 0;
       }
   }

event 语法和 guard 语法不要混在同一个 transition 形式里。事件转换使用 ``:: EventName`` 表示本地事件，或使用 ``: EventPath`` 表示链式 / root 作用域事件。guard 转换使用 ``: if [condition]``。

事件定义
--------

需要可复用事件名并希望图中展示事件归属时，可以显式声明事件：

.. code-block:: fcstm

   state Controller {
       event Start;
       event Stop;

       [*] -> Idle;
       state Idle;
       state Running;

       Idle -> Running :: Start;
       Running -> Idle :: Stop;
   }

事件作用域细节见 :doc:`../../reference/dsl/index_zh`。本地、父级和 root-scoped 事件的写法见 :doc:`../../how_to/dsl/index_zh`。

守卫条件和效果
--------------

guard 是布尔条件。effect 和 lifecycle action 中可以写操作块，操作块里的赋值会更新持久变量，也可以先赋值再读取 block-local 临时变量：

.. code-block:: fcstm

   def int attempts = 0;

   state RetryController {
       event Failed;
       [*] -> Ready;

       state Ready;
       state Backoff;

       Ready -> Backoff :: Failed effect {
           attempts = attempts + 1;
       }

       Backoff -> Ready : if [attempts < 3];
   }

比较运算符 ``<``、``<=``、``==``、``!=``、``>=``、``>`` 把 arithmetic expression 连接成 condition。布尔组合使用 ``&&`` / ``and`` 和 ``||`` / ``or``。

表达式系统
----------

算术表达式和逻辑条件是两类东西。赋值需要算术表达式，guard 需要 condition：

.. code-block:: fcstm

   def int x = 1;
   def float y = 2.0;

   state ExprDemo {
       [*] -> A;
       state A;
       state B;

       A -> B : if [(x + 1) >= 2 && y < 3.0];
   }

所有运算符和函数请查 :doc:`../../reference/dsl/index_zh`，不要把本教程当成完整 reference。

生命周期动作
------------

lifecycle action 在进入、循环或退出状态时执行。一个最小 leaf-state 示例是：

.. code-block:: fcstm

   def int cycles = 0;

   state Worker {
       [*] -> Active;
       state Active {
           enter {
               cycles = 0;
           }
           during {
               cycles = cycles + 1;
           }
           exit {
               cycles = 0;
           }
       }
   }

命名 action、``abstract`` hook、``ref`` 复用以及 ``>> during`` aspect action 见 :doc:`../../how_to/dsl/index_zh` 和 :doc:`../../explanations/dsl_semantics/index_zh`。

实际示例：智能恒温器
--------------------

这个小恒温器模型组合了变量、事件、guard、effect 和层级：

.. literalinclude:: thermostat_example.fcstm
   :language: fcstm
   :caption: 最小恒温器 DSL 示例

可以直接仿真这个已入库示例：

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/dsl/thermostat_example.fcstm -e "cycle; current"

语义验证规则
------------

本页只介绍让第一个模型有效的常见规则：

* 在根状态之前声明变量。
* 只写一个顶层根 ``state``。
* 每个 composite state 都选择一个初始子状态。
* 转换 target 要放在正确作用域内。
* 赋值里使用 arithmetic expression，guard 里使用 boolean condition。

更详细的 diagnostics、边界情况和部署风险措辞属于 inspect 和 reference 页面，不放在本教程里。

Import 装配
-----------

import 会把另一个 FCSTM 文件装配成 composite state 内的子系统。第一次写 DSL 时可以先跳过 import。需要 import 时，从任务指南和语法表开始：

* :doc:`../../how_to/dsl/index_zh`：import 实用任务。
* :doc:`../../reference/dsl/index_zh`：import selector 和 mapping 形式。
* :doc:`../../explanations/dsl_semantics/index_zh`：装配语义边界。

总结
----

你已经走完最小 FCSTM DSL 路径：变量、根状态、子状态、转换、事件、guard、effect、lifecycle action，以及一个可以仿真的小模型。深入使用时请转到：

* 写任务：:doc:`../../how_to/dsl/index_zh`。
* 查语法：:doc:`../../reference/dsl/index_zh`。
* 理解语义：:doc:`../../explanations/dsl_semantics/index_zh`。
