.. _sec-tutorials-dsl-zh:

编写第一个 FCSTM DSL 模型
==========================

.. contents:: 页面地图
   :local:
   :depth: 2

概览
----

本教程是 FCSTM DSL 的短学习路径，目标是写出一个能够 parse、simulate、inspect 的小模型。它不会列出所有
operator、import mapping、transition 变体或 diagnostic code。

需要更多细节时请跳到这些页面：

* :doc:`../../how_to/dsl/index_zh`：event scope、import、lifecycle reuse、combo transition 等任务写法。
* :doc:`../../reference/dsl/index_zh`：精确 grammar 形式和 coverage matrix。
* :doc:`../../explanations/dsl_semantics/index_zh`：ownership、lifecycle、combo、import 等语义解释。
* :doc:`../../reference/diagnostics_codes/index_zh`：diagnostics 措辞和 target-profile 风险边界。

从一个合法 root 开始
--------------------

一个可运行 FCSTM 文件先写持久变量声明，然后写唯一 root ``state``。实际模型通常使用 composite root，因为它可以拥有子状态和 initial transition。

片段：

.. code-block:: fcstm

   def int temperature = 20;
   def int target = 22;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

这些声明不是局部变量，而是模型持久变量。root state 为 child state、event、transition 和 lifecycle action 提供名称解析树。

添加变量与基础表达式
--------------------

当前持久变量类型是 ``int`` 和 ``float``。初始值可以使用 numeric literal、math constant、unary sign、arithmetic、bitwise operator 和支持的 math function。本教程只展示简单算术。

片段：

.. code-block:: fcstm

   def int temperature = 20;
   def int target = 22;
   def float gain = 0.5;

需要 hexadecimal literal、``pi`` / ``E`` / ``tau``、math function、bitwise operator、boolean operator 或 C-style ternary expression 时，查看完整表达式参考：:ref:`dsl-expression-reference-zh`。

添加 leaf 与 composite state
----------------------------

leaf state 以 ``;`` 结束。composite state 在 ``{ ... }`` 内拥有嵌套声明，并且必须使用 ``[*] -> Child;`` 选择 initial child。

片段：

.. code-block:: fcstm

   state Thermostat {
       [*] -> Idle;
       state Idle;
       state Heating;
   }

transition 在 owner scope 中解析 target。如果 target 是某个 composite 内部的 leaf，请把 transition 写在拥有该 leaf 的 composite 内部，或者 transition 到 composite 本身并让 initial transition 选择 child。

添加事件与转移
--------------

第一个模型只需要 event transition 和 guard transition。source-local event 使用 ``:: EventName``。guard transition 使用 ``: if [condition]``。

片段：

.. code-block:: fcstm

   Idle -> Heating : if [temperature < target];
   Heating -> Idle :: StopHeating;

普通 transition 刻意把 event syntax 和 guard syntax 分开。确实需要 event-plus-guard 行为时，请使用 combo-trigger 的任务指南和参考表，而不是自行混写普通形式。

添加 guard 与 effect
--------------------

guard 是 condition expression。effect 是 operation block，用来更新持久变量，也可以在赋值后读取 block-local temporary。

片段：

.. code-block:: fcstm

   Idle -> Heating : if [temperature < target] effect {
       delta = target - temperature;
       temperature = temperature + delta;
   }

assignment 需要 arithmetic expression。guard 需要 condition。``temperature < target`` 这样的比较把 arithmetic expression 桥接为 condition。

添加最小生命周期动作
--------------------

lifecycle block 在状态边界或 active cycle 中运行。第一个模型建议只使用 concrete 本地动作。

片段：

.. code-block:: fcstm

   state Heating {
       enter {
           heating_on = 1;
       }
       during {
           temperature = temperature + 1;
       }
       exit {
           heating_on = 0;
       }
   }

named action、``abstract`` hook、documentation-comment abstract hook、``ref`` reuse、``during before`` / ``during after`` 以及 ``>> during`` aspect 都放在任务指南和参考页中。

运行并检查模型
--------------

本教程的 first runnable model 是仓库中的源文件：

.. literalinclude:: thermostat_example.fcstm
   :language: fcstm
   :caption: ``thermostat_example.fcstm``

在本目录运行短 simulation：

.. code-block:: bash

   pyfcstm simulate -i thermostat_example.fcstm -e "cycle; cycle; current"

然后检查模型结构和 diagnostics：

.. code-block:: bash

   pyfcstm inspect -i thermostat_example.fcstm --format json -o thermostat.inspect.json

教程只展示短命令和关键输出。如果 inspect 报出 syntax、model、combo、import 或 C/C++ deployment-profile warning，请使用 diagnostics 和 how-to 页面做定向修复。

下一步去哪里
------------

* Event scope：:ref:`dsl-event-scopes-task-zh` 和 :ref:`dsl-events-scopes-zh`。
* Guard/effect operation block：:ref:`dsl-guards-effects-task-zh` 和 :ref:`dsl-operation-blocks-zh`。
* Expression：:ref:`dsl-expression-safety-task-zh` 和 :ref:`dsl-expression-reference-zh`。
* Lifecycle、abstract hook、ref 与 aspect：:ref:`dsl-lifecycle-task-zh`、:ref:`dsl-lifecycle-forms-zh` 和 :ref:`dsl-aspect-forms-zh`。
* Forced 与 combo transition：:ref:`dsl-forced-transition-task-zh`、:ref:`dsl-combo-transition-task-zh` 和 :ref:`dsl-transition-forms-zh`。
* Import：:ref:`dsl-import-task-zh` 和 :ref:`dsl-import-forms-zh`。
* Diagnostics 与 target risk wording：:ref:`dsl-diagnostics-task-zh`、:ref:`dsl-diagnostics-risk-zh` 和 :doc:`../../reference/diagnostics_codes/index_zh`。
