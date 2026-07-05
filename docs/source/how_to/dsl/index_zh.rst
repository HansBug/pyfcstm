
.. _sec-how-to-dsl-zh:

DSL 任务指南
================

.. contents:: 任务地图
   :local:
   :depth: 2

范围与任务地图
---------------

本页从具体编写任务出发。它给出短片段或链接到 checked-in 示例，然后把完整事实交给 :doc:`../../reference/dsl/index_zh`，把语义背景交给 :doc:`../../explanations/dsl_semantics/index_zh`。

需要写或修复某种 DSL 形状时，请使用下面任务：

* state ownership 与 transition target；
* event scope；
* guard、effect、operation block 与 expression；
* lifecycle action、``abstract`` hook、``ref`` 与 ``>> during`` aspect；
* forced transition 与 combo transition；
* import 与 diagnostics。

.. _dsl-small-valid-model-task-zh:

写一个小型有效模型
------------------

从一个 root composite、一个 initial transition 和 child leaf states 开始。教程使用 thermostat 示例作为 first runnable model：

.. literalinclude:: ../../tutorials/dsl/thermostat_example.fcstm
   :language: fcstm
   :caption: 第一个可运行 DSL 模型

检查命令：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/thermostat_example.fcstm --format json

.. _dsl-state-target-task-zh:

组织状态与解析 target
----------------------

把 transition 放在拥有 source 和 target 名称的 state scope 中。Sibling transitions 属于 parent composite。

片段：

.. code-block:: fcstm

   state Parent {
       [*] -> ChildA;
       state ChildA;
       state ChildB;
       ChildA -> ChildB;
   }

来自 ``Parent`` 外部的 transition 应该指向 ``Parent``，而不是直接跳到 ``Parent.ChildB``。composite 进入后再由 initial transition 选择 child。Pseudo state 只作为 routing node 使用；用户可见业务状态应使用 normal leaf 或 composite state。

.. _dsl-event-scopes-task-zh:

编写 event scope
----------------------

source-local event 用于 source state 自己的事件命名空间。

片段：

.. code-block:: fcstm

   Idle -> Heating :: Heat;

chain-scoped event 用于 containing 或 named scope 拥有的事件。

片段：

.. code-block:: fcstm

   state Controller {
       event Start;
       Idle -> Running : Start;
   }

root-scoped event 用于 root state 拥有、nested state 需要绝对引用的事件。

片段：

.. code-block:: fcstm

   Worker.Idle -> Worker.Active : /Start;

Checked examples：

.. literalinclude:: ../../tutorials/dsl/event_scoping_complete.fcstm
   :language: fcstm
   :caption: 完整 event-scope 示例

.. literalinclude:: ../../tutorials/dsl/event_scoping_comparison.fcstm
   :language: fcstm
   :caption: event-scope 对比示例

.. _dsl-guards-effects-task-zh:

编写 guard、effect 与 operation block
-----------------------------------------

使用 ``: if [condition]`` 编写 guard transition。transition 需要更新变量时添加 ``effect { ... }``。

.. literalinclude:: ../../tutorials/dsl/guards_and_effects.fcstm
   :language: fcstm
   :caption: Guards、effects、temporary variables 与 ``if`` blocks

Operation block 支持 assignment、block-local temporary、``if`` / ``else if`` / ``else`` block 和 empty statement。local temporary 只能在同一个 block 内赋值后读取。

.. _dsl-expression-safety-task-zh:

安全使用 expression
-----------------------

Assignment 和 numeric initializer 使用 arithmetic expression。Guard 使用 condition expression。Comparison 把 numeric expression 桥接为 condition。完整 precedence 和 operator 请看 expression reference。

片段：

.. code-block:: fcstm

   value = abs(sensor - target) + 1;
   ready = (temperature >= target) ? 1 : 0;
   Idle -> Heating : if [temperature < target && enabled == 1];

完整 expression demo：

.. literalinclude:: ../../tutorials/dsl/expression_demo.fcstm
   :language: fcstm
   :caption: Expression demo

.. _dsl-lifecycle-task-zh:

编写 lifecycle hook、ref 与 abstract hook
---------------------------------------------

本地 state 行为使用 concrete ``enter``、``during`` 和 ``exit`` block。需要稳定 generated extension point 时使用 named lifecycle action。需要 generated code 调用用户行为时使用 ``abstract``。复用 named lifecycle action 时使用 ``ref``。

片段：

.. code-block:: fcstm

   state Active {
       enter Setup {
           flag = 1;
       }
       during abstract Tick;
       exit ref Cleanup;
   }

Checked example：

.. literalinclude:: ../../tutorials/dsl/abstract_reference_demo.fcstm
   :language: fcstm
   :caption: Abstract 与 reference action 示例

Lifecycle diagrams：

.. image:: ../../tutorials/dsl/leaf_state_lifecycle.puml.svg
   :alt: Leaf state lifecycle

.. image:: ../../tutorials/dsl/composite_state_lifecycle.puml.svg
   :alt: Composite state lifecycle

.. _dsl-aspect-task-zh:

使用 during aspect
------------------------

``>> during before`` 和 ``>> during after`` 是 ancestor 贡献给 descendant leaf-state active cycles 的 aspect actions。

片段：

.. code-block:: fcstm

   state Root {
       [*] -> Child;
       >> during before {
           trace = trace + 1;
       }
       state Child;
   }

不要把 aspect 当成给 combo pseudo relay state 添加可观察业务行为的机制。Pseudo relay chain 是 routing machinery；aspect actions 不在 relay 内运行。

.. _dsl-forced-transition-task-zh:

编写 forced transition
----------------------------

当一个声明需要展开到多个 source states 时使用 forced transition。它可以指向 state 或 exit marker，也可以使用 local、chain、root 或 guard trigger。它不支持 ``effect`` block。

.. literalinclude:: ../../tutorials/dsl/forced_transitions.fcstm
   :language: fcstm
   :caption: Forced transition 示例

.. _dsl-combo-transition-task-zh:

编写 combo transition
---------------------------

transition 需要多个 trigger terms 时使用 combo trigger。支持 ordinary combo、entry combo 和 forced combo。Event term 与 guard term 之间使用 ``+``。

片段：

.. code-block:: fcstm

   Idle -> Running :: Start + [enabled == 1];
   [*] -> Running :: Boot + [enabled == 1];
   !* -> Fault : /Stop + [enabled == 0];

Combo expansion 使用 pseudo relay states。Duplicate event terms、guard aliases、constant guards、pseudo-name extension 和 reserved ``__combo`` names 会通过 diagnostics 报告。详细 expansion 语义见 :ref:`dsl-combo-relay-semantics-zh`。

.. _dsl-import-task-zh:

组装 import
-----------------

把另一个文件 import 为 child subsystem：

.. literalinclude:: ../../tutorials/dsl/import_host_basic.fcstm
   :language: fcstm
   :caption: Basic import host

被 import 的 worker：

.. literalinclude:: ../../tutorials/dsl/import_worker.fcstm
   :language: fcstm
   :caption: Imported worker

需要重写 parent 与 child 的变量或事件名称时使用 mapping：

.. literalinclude:: ../../tutorials/dsl/import_host_mapped.fcstm
   :language: fcstm
   :caption: Import with mappings

目录组织的 subsystem 必须 import 显式文件，例如 ``./import_line/main.fcstm``。不支持 bare directory import。

.. literalinclude:: ../../tutorials/dsl/import_host_directory.fcstm
   :language: fcstm
   :caption: 显式目录 ``main.fcstm`` import

.. literalinclude:: ../../tutorials/dsl/import_line/main.fcstm
   :language: fcstm
   :caption: Directory subsystem entry file

.. literalinclude:: ../../tutorials/dsl/import_line/subsystems/robot.fcstm
   :language: fcstm
   :caption: Nested subsystem file

Imported file 中的 import preamble statement 使用 ``x = value;`` 表示 constant，使用 ``x := value;`` 表示 initial assignment。它们由 preamble entry point 解析，不是普通 top-level ``def`` declaration。

.. _dsl-diagnostics-task-zh:

诊断并修复 DSL 错误
--------------------

parse 失败时先修 syntax。model validation 失败时检查 state / event / transition ownership facts。diagnostics 报告 combo、import 或 target-profile risk 时，按 code-specific message 和 reference table 修复。

短流程：

.. code-block:: bash

   pyfcstm inspect -i model.fcstm --format json -o model.inspect.json
   python -m json.tool model.inspect.json | sed -n '1,80p'

C/C++ deployment-profile warnings 是面向 ``c``、``c_poll``、``cpp``、``cpp_poll`` 等 C-family templates 的 target-specific review signals。除非 Python runtime path 也有自己的 diagnostic evidence，否则不能把它们写成 Python generated code 具有相同风险。
