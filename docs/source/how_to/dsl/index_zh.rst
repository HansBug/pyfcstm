.. _sec-how-to-dsl-zh:

DSL 任务指南
============

.. contents:: 目录
   :local:
   :depth: 2

范围
----

本页回答“这个 DSL 形状应该怎么写”的实际问题。第一次学习请看 :doc:`../../tutorials/dsl/index_zh`；精确 grammar facts 请看 :doc:`../../reference/dsl/index_zh`；语义背景请看 :doc:`../../explanations/dsl_semantics/index_zh`。

写一个小型有效模型
------------------

从变量、composite root、一个 initial transition 和两个 leaf state 开始：

.. code-block:: fcstm

   def int ticks = 0;

   state Machine {
       event Step;
       [*] -> Idle;

       state Idle;
       state Running {
           during {
               ticks = ticks + 1;
           }
       }

       Idle -> Running :: Step;
       Running -> Idle : if [ticks >= 5] effect {
           ticks = 0;
       }
   }

快速检查：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "cycle Step; cycle; current"

写事件作用域
------------

事件属于 source state 命名空间时使用 local event：

.. code-block:: fcstm

   Idle -> Running :: Start;

事件属于 containing scope 或具名 scope 时使用 chain-scoped event：

.. code-block:: fcstm

   Running -> Idle : Stop;
   ChildA -> ChildB : Parent.Shared;

全局信号使用 root-scoped event：

.. code-block:: fcstm

   Any -> Safe : /EmergencyStop;

如果事件解析不够清晰，优先把事件声明在 owner state 附近，并使用最短且不歧义的作用域。

写 guard 和 effect
------------------

用 ``: if [condition]`` 写 guard；transition 需要更新变量时加 ``effect { ... }``：

.. code-block:: fcstm

   Active -> Cooling : if [temperature > target] effect {
       fan_speed = 2;
   }

不要把 event 语法和 guard 语法当成同一个普通 trigger 混写。需要 event-plus-guard 时，用下面的 combo trigger。

写 combo trigger
----------------

用 ``+`` 组合 event term 和 guard term：

.. code-block:: fcstm

   Idle -> Active :: Start + [enabled == 1];
   Active -> Idle : Stop + [safe == 1];

只有模型确实需要多个 trigger term 时才使用 combo transition。reference 页列出接受形式；语义解释页说明展开时使用的 pseudo intermediate states。

写 composite state
------------------

嵌套状态和子状态之间的转换应写在 owning composite 内：

.. code-block:: fcstm

   state Parent {
       [*] -> A;

       state A;
       state B;

       A -> B;
   }

外部转换到 ``Parent`` 时会进入 composite，再由 initial transition 选择子状态。子状态之间的转换属于 ``Parent`` 内部。

写 lifecycle 和 aspect action
-----------------------------

本地状态行为使用 concrete lifecycle action：

.. code-block:: fcstm

   state Active {
       enter {
           count = 0;
       }
       during {
           count = count + 1;
       }
       exit {
           count = 0;
       }
   }

多个状态共享 action 时使用 named action 和 ``ref``：

.. code-block:: fcstm

   state Parent {
       enter SharedEnter {
           count = 0;
       }

       state Child {
           enter ref Parent.SharedEnter;
       }
   }

生成代码需要调用用户提供的行为时使用 ``abstract`` hook：

.. code-block:: fcstm

   state Active {
       enter abstract OnActive;
   }

aspect action 面向 descendant leaf-state cycles，不作用于 combo pseudo 中继：

.. code-block:: fcstm

   state Parent {
       >> during before {
           audit = audit + 1;
       }
   }

写 import
---------

把 subsystem 导入为子状态：

.. code-block:: fcstm

   state System {
       [*] -> Worker;
       import "worker.fcstm" as Worker;
   }

需要改写变量名时使用 compact selector 和 template：

.. code-block:: fcstm

   import "worker.fcstm" as Worker {
       def * -> worker_$0;
       def sensor_* -> worker_sensor_$0;
   }

parent 和 imported subsystem 需要交换信号时映射事件：

.. code-block:: fcstm

   import "worker.fcstm" as Worker {
       event /Start -> /WorkerStart;
       event /WorkerDone -> /Done;
   }

compact selector / template 对空白敏感。``sensor_*``、``worker_$0`` 这样的 wildcard pattern 和 template 应保持连续。

继续阅读
--------

* 需要精确语法形式：:doc:`../../reference/dsl/index_zh`。
* 需要 hierarchy、combo、import 或 lifecycle 语义：:doc:`../../explanations/dsl_semantics/index_zh`。
* 需要无效 DSL 的 inspect diagnostics：:doc:`../inspect/index_zh` 和 :doc:`../../reference/diagnostics_codes/index_zh`。
