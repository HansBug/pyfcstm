.. _sec-tutorials-dsl-zh:

编写第一个 FCSTM DSL 模型
==============================

.. contents:: 页面地图
   :local:
   :depth: 2

本教程覆盖什么
--------------

这一页是 FCSTM DSL 的首次成功路径：构建一个小型 thermostat 模型，运行它，并阅读第一份 inspect 报告。它不会试图一次性列完所有 operator、import mapping、combo transition 或 diagnostic code。

* :doc:`../../how_to/dsl/index_zh` 按任务给出写法、示例、命令、预期诊断和修复步骤。
* :doc:`../../reference/dsl/index_zh` 用来查精确语法和覆盖矩阵。
* :doc:`../../explanations/dsl_semantics/index_zh` 解释 ownership、runtime 语义、combo 展开、forced 展开和 import 组装。
* :doc:`../../reference/diagnostics_codes/index_zh` 解释 diagnostic code 和 target-profile warning。

下面所有命令都默认从仓库根目录复制运行。

术语约定：本页首次使用英文 DSL 术语时给出中文括注。``persistent variable`` 是持久变量，``composite`` 是复合状态，
``child state`` 是子状态，``initial transition`` 是初始转换，``ownership tree`` 是所有权树，
``condition expression`` 是条件表达式，``numeric expression`` 是数值表达式。

步骤 1：建立最小结构
--------------------

普通 ``.fcstm`` 文件先写 persistent variable（持久变量），再写唯一 root ``state``。实际模型通常把 root 写成 composite（复合状态），因为它需要拥有 child states（子状态）和 initial transition（初始转换）。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

``def`` 声明的是模型持久状态，不是某个 block 内的临时变量。root state 随后成为 child state、event、transition、lifecycle action 和 import 的 ownership tree（所有权树）。

步骤 2：添加另一个 leaf 和 guard
--------------------------------------

Leaf state 以 ``;`` 结束。写在 ``Thermostat`` 内的 transition 可以使用 ``Thermostat`` 直接拥有的 child 名称。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
       state Heating;

       Idle -> Heating : if [temperature < 20];
       Heating -> Idle : if [temperature >= 22];
   }

``: if`` 后面是 condition expression（条件表达式）。``temperature`` 是 numeric expression（数值表达式）；比较表达式把 numeric value 桥接成 condition。

步骤 3：添加生命周期动作
------------------------

Leaf 的 ``during`` action 在普通 active cycle 中运行。``enter`` action 在进入 state 时运行。下面的版本会修改 ``temperature``，因此两个 guard 的真假会随 cycle 改变。

Patch fragment（补丁片段）：把步骤 2 中两个 leaf declaration 替换成下面两个 state block。这个片段本身不是完整
``.fcstm`` 文件；步骤 4 展示已提交并验证过的完整模型。

.. code-block:: fcstm

   state Idle {
       during {
           temperature = temperature - 1;
       }
   }

   state Heating {
       enter {
           temperature = temperature + 1;
       }
       during {
           temperature = temperature + 1;
       }
   }

Operation block 可以包含 assignment 和 ``if`` block。若某个名字没有用 ``def`` 声明，但先在 block 内被赋值，它就是只在当前 block 内有效的 temporary；完整示例见 how-to 页面。

步骤 4：检查完整文件
--------------------

完整教程模型已经提交为 ``first_thermostat.fcstm``：

.. literalinclude:: first_thermostat.fcstm
   :language: fcstm
   :caption: ``docs/source/tutorials/dsl/first_thermostat.fcstm``

从仓库根目录运行 inspect：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/first_thermostat.fcstm --format human --color never

关键输出应为：

.. code-block:: text

   [OK] FCSTM Inspect Report: docs/source/tutorials/dsl/first_thermostat.fcstm

   Summary
     status: ok
     root: Thermostat
     states: 3 total / 2 leaf
     transitions: 3
     variables: 1
     diagnostics: 0 errors / 0 warnings / 0 infos

   No diagnostics.

如果这里出现 error，应先修复再进入 simulation 或 code generation。Warning 和 info 也值得阅读，因为它们通常会指出具体 target profile、transition、variable 或 source span。

步骤 5：运行两个 cycle
----------------------------

运行 batch simulation：

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/dsl/first_thermostat.fcstm --no-color -e "cycle; cycle; current"

关键输出为：

.. code-block:: text

   Cycle: 1
   Current State: Thermostat.Idle
   Variables:
     temperature = 19

   Cycle: 2
   Current State: Thermostat.Heating
   Variables:
     temperature = 21

第一个 cycle 进入 ``Idle`` 并执行 ``Idle.during``。第二个 cycle 中 ``Idle -> Heating`` guard 为 true，因此 transition 触发，然后执行 ``Heating.enter``。

步骤 6：按主题继续学习
----------------------

不要从这个教程直接跳到巨型模型。每次只加一个 DSL 能力，并在每次修改后重新检查 inspect 输出。

.. list-table:: 下一步
   :header-rows: 1
   :widths: 24 38 38

   * - 目标
     - 从这里开始
     - 原因
   * - 添加 source-local、parent 或 root event
     - :ref:`dsl-event-scopes-task-zh`
     - Event scope 决定 event 名称由谁拥有、如何复用。
   * - 添加 effect、temporary 和 ``if`` block
     - :ref:`dsl-guards-effects-task-zh`
     - Effect 在 transition 执行时更新变量，不参与 guard 测试本身。
   * - 使用完整 expression 语言
     - :ref:`dsl-expression-safety-task-zh`
     - Numeric expression、condition expression 和 ternary form 的合法位置不同。
   * - 复用 lifecycle 行为
     - :ref:`dsl-lifecycle-task-zh`
     - ``abstract`` 和 ``ref`` 是 DSL 结构连接 generated runtime hook 的桥梁。
   * - 建模多 term trigger
     - :ref:`dsl-combo-transition-task-zh`
     - Combo transition 会展开成伪中继状态（pseudo relay states），同时保留作者语义。
   * - 用一个声明覆盖多个 source
     - :ref:`dsl-forced-transition-task-zh`
     - Forced transition 是展开 shorthand，因此有意不支持 effect block。
   * - 把模型拆成多个文件
     - :ref:`dsl-import-task-zh`
     - Import 会组装 state-machine module，并按 mapping 重写 variable/event。
   * - 修复 diagnostics
     - :ref:`dsl-diagnostics-task-zh`
     - Inspect diagnostic 包含 code、severity、source span、refs 和 suggested fix。
