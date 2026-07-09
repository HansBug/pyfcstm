.. _sec-tutorials-dsl-zh:

编写第一个 FCSTM DSL 模型
==============================

.. contents:: 页面地图
   :local:
   :depth: 2

本教程覆盖什么
--------------

这一页是 FCSTM DSL 的首次成功路径：构建一个小型温控器模型，运行它，并阅读第一份检查报告（inspect report）。它不会试图一次性列完所有运算符、导入映射（import mapping）、组合转换
（combo transition）或诊断码（diagnostic code）。这些高级主题后文只称为导入映射、组合转换和诊断码。

* :doc:`../../how_to/dsl/index_zh` 按任务给出写法、示例、命令、预期诊断和修复步骤。
* :doc:`../../reference/dsl/index_zh` 用来查精确语法和覆盖矩阵。
* :doc:`../../explanations/dsl_semantics/index_zh` 解释所有权、运行时语义、组合转换展开、强制转换展开和导入组装。
* :doc:`../../reference/diagnostics_codes/index_zh` 解释诊断码和目标配置风险警告。

下面所有命令都默认从仓库根目录复制运行。

术语约定：本页首次使用必要英文术语时采用“中文（English）”格式，后文只使用中文。持久变量
（persistent variable）是模型长期保存的数据；复合状态（composite state）拥有子状态；初始转换
（initial transition）选择复合状态的起始子状态；条件表达式（condition expression）决定转换是否可用；
数值表达式（numeric expression）计算变量值。

步骤 1：建立最小结构
--------------------

普通 ``.fcstm`` 文件先写持久变量，再写唯一根状态（root state）。实际模型通常把根状态写成复合状态，
因为它需要拥有子状态（child state）和初始转换。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

``def`` 声明的是模型持久状态，不是某个操作块（operation block）内的临时变量。根状态随后成为子状态、
事件（event）、转换（transition）、生命周期动作（lifecycle action）和导入（import）的所有权树
（ownership tree）。

步骤 2：添加另一个叶状态和守卫条件
----------------------------------

叶状态（leaf state）以 ``;`` 结束。写在 ``Thermostat`` 内的转换可以使用 ``Thermostat`` 直接拥有的子状态名称。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
       state Heating;

       Idle -> Heating : if [temperature < 20];
       Heating -> Idle : if [temperature >= 22];
   }

``: if`` 后面是条件表达式。``temperature`` 是数值表达式；比较表达式把数值桥接成条件。

步骤 3：添加生命周期动作
------------------------

叶状态的 ``during`` 动作在普通活动周期（active cycle）中运行。``enter`` 动作在进入状态时运行。
下面的版本会修改 ``temperature``，因此两个守卫条件（guard）的真假会随周期改变。

补丁片段（patch fragment）：把步骤 2 中两个叶状态声明替换成下面两个状态块。这个片段本身不是完整
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

操作块可以包含赋值和 ``if`` 分支。若某个名字没有用 ``def`` 声明，但先在块内被赋值，它就是只在当前块内有效的临时变量；完整示例见任务指南页面。

步骤 4：检查完整文件
--------------------

完整教程模型已经提交为 ``first_thermostat.fcstm``：

.. literalinclude:: first_thermostat.fcstm
   :language: fcstm
   :caption: ``docs/source/tutorials/dsl/first_thermostat.fcstm``

模型图先给出整体形状：

.. figure:: first_thermostat.fcstm.puml.svg
   :alt: 第一个温控器模型的状态图
   :align: center

   图中 ``Thermostat`` 是根复合状态，``Idle`` 和 ``Heating`` 是作者写的两个叶状态。两条有守卫条件的边来自
   DSL 中的 ``Idle -> Heating`` 和 ``Heating -> Idle``；初始边 ``[*] -> Idle`` 表示进入模型时先停在
   ``Idle``。这张图没有生成状态，适合作为后续理解组合转换和强制转换展开的基线。

从仓库根目录运行检查命令：

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

如果这里出现错误，应先修复再进入仿真（simulation）或代码生成（code generation）。后文只称仿真和代码生成。警告和信息也值得阅读，
因为它们通常会指出具体目标配置、转换、变量或源码位置。

步骤 5：运行两个周期
--------------------

运行批处理仿真（batch simulation）：

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

第一个周期进入 ``Idle`` 并执行 ``Idle.during``。第二个周期中 ``Idle -> Heating`` 的守卫条件为真，因此转换触发，
然后执行 ``Heating.enter``。

步骤 6：修复一个故意语法错误
----------------------------

检查也是修复 DSL 小错误最快的入口。普通事件语法和普通守卫语法是两种独立转换形式，所以这个故意坏掉的文本夹具会失败：

.. literalinclude:: event_guard_mixed_invalid.fcstm.txt
   :language: fcstm
   :caption: 故意解析错误；预期摘录：``Unexpected token 'if'``\ 。

把它当普通输入文件运行：

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/dsl/event_guard_mixed_invalid.fcstm.txt --format human --color never

关键摘录为：

.. code-block:: text

   Syntax error at line 7, column 17, near 'if': Unexpected token 'if'

当同一个触发器需要同时包含事件项和守卫项时，用组合语法修复：

.. code-block:: fcstm

   A -> B :: Go + [ready > 0];

以后每次改模型都可以按这个最小循环操作：运行 ``pyfcstm inspect``，阅读诊断码和源码区间，再修复诊断指向的 DSL 形式。

步骤 7：按主题继续学习
----------------------

不要从这个教程直接跳到巨型模型。每次只加一个 DSL 能力，并在每次修改后重新阅读检查输出。

.. list-table:: 下一步
   :header-rows: 1
   :widths: 24 38 38

   * - 目标
     - 从这里开始
     - 原因
   * - 添加源状态本地、父级或根事件
     - :ref:`dsl-event-scopes-task-zh`
     - 事件作用域决定事件名称由谁拥有、如何复用。
   * - 添加效果动作、临时变量和 ``if`` 分支
     - :ref:`dsl-guards-effects-task-zh`
     - 效果动作在转换执行时更新变量，不参与守卫条件测试本身。
   * - 使用完整表达式语言
     - :ref:`dsl-expression-safety-task-zh`
     - 数值表达式、条件表达式和三目形式的合法位置不同。
   * - 复用生命周期行为
     - :ref:`dsl-lifecycle-task-zh`
     - ``abstract`` 和 ``ref`` 是 DSL 结构连接生成运行时钩子的桥梁。
   * - 建模多项触发器
     - :ref:`dsl-combo-transition-task-zh`
     - 组合转换会展开成伪中继状态（pseudo relay state），后文只称伪中继状态，同时保留作者语义。
   * - 用一个声明覆盖多个来源状态
     - :ref:`dsl-forced-transition-task-zh`
     - 强制转换（forced transition）是展开简写，后文只称强制转换，因此有意不支持效果动作块。
   * - 把模型拆成多个文件
     - :ref:`dsl-import-task-zh`
     - 导入会组装状态机模块，并按映射重写变量和事件。
   * - 修复诊断
     - :ref:`dsl-diagnostics-task-zh`
     - 检查诊断包含诊断码、严重级别、源码位置、结构化引用和修复建议。
