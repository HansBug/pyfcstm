.. _sec-explanations-dsl-semantics-zh:

DSL 语义解释
============

.. contents:: 语义地图
   :local:
   :depth: 2

范围
----

本页解释 FCSTM DSL 为什么这样运行。精确语法表请看 :doc:`../../reference/dsl/index_zh`；首次跟做教程请看 :doc:`../../tutorials/dsl/index_zh`；更完整的 simulator 内部顺序请看 :doc:`../execution_semantics/index_zh`。

.. _dsl-root-design-zh:

为什么变量在唯一 root state 之前
--------------------------------

一个 FCSTM model 表示一个 controller 和一条 active-state stack。Persistent variables 放在 root 前面，是为了让 guard、effect、lifecycle action、import mapping 和 diagnostics 都看到同一份数据表面。

.. code-block:: fcstm

   def int temperature = 20;

   state Thermostat {
       [*] -> Idle;
       state Idle;
   }

这不仅是 parser 便利。Code generation 需要一个 runtime object、一份 variable store 和一个 root active stack。Import assembly 也需要一个 host tree，把 imported module 重写进去。

.. _dsl-ownership-name-resolution-zh:

所有权树与名称解析
------------------

State、event、lifecycle action 和 import 都由 state 拥有。Transition 只能直接命名它所在 owner scope 可见的 endpoint。

.. code-block:: fcstm

   state Root {
       [*] -> Parent;

       state Parent {
           [*] -> ChildA;
           state ChildA;
           state ChildB;
           ChildA -> ChildB;
       }
   }

``ChildA -> ChildB`` 写在 ``Parent`` 内，因为 ``Parent`` 拥有这两个名字。如果 parent-level rule 直接写到 nested private leaf，就会让外层逻辑依赖内部实现细节。推荐做法是进入 composite boundary，再由 composite initial transition 选择 child，或者把 child-targeting transition 放到 owning composite 内。

Inspect 的 ``transitions[].from_path`` 和 ``transitions[].to_path`` 会展示解析后的路径，可用于确认 transition 落在 boundary 还是内部 child。

.. _dsl-composite-entry-semantics-zh:

Composite entry 与 initial transition
----------------------------------------------

Composite state 同时是 boundary 和 child-selection rule。进入 boundary 不等于已经处于某个 leaf child。

Initial entry 的概念顺序是：

1. 进入 composite boundary；
2. 评估并应用 composite 的 initial transition；
3. 运行 plain composite ``during before``；
4. 进入选中的 child。

Child-to-child transition 则是：

1. source child ``exit``；
2. transition ``effect``；
3. target child ``enter``。

Plain composite ``during before`` / ``during after`` 不包裹 child-to-child movement。这样可以避免 composite entry/exit behavior 变成每次内部切换都会触发的隐藏行为。

.. _dsl-event-ownership-signal-zh:

Event scope 作为 ownership signal
---------------------------------

Event 拼写告诉读者 signal 由谁拥有：

.. list-table:: Event ownership
   :header-rows: 1
   :widths: 22 36 42

   * - 拼写
     - 示例
     - 含义
   * - ``::``
     - ``Idle -> Heating :: Heat;``
     - Source state 拥有私有 event 名称。
   * - ``:``
     - ``Idle -> Running : Start;``
     - Containing 或 named state 拥有 event path。
   * - ``: /``
     - ``Worker -> Active : /Start;``
     - Path 从 root-owned event namespace 开始。

这个区别会影响重构。Source-local event 可以跟着一个 state 一起移动；root event 更像公开 protocol。Combo term 会继承 leading scope，除非 continuation term 显式以 ``/`` 开始。

Forced transition 也使用类似 trigger spelling，但它是 declaration expansion shorthand。Forced trigger 产生 ordinary expanded transitions；它不是 combo chain，也不能带 effect。

.. _dsl-expression-separation-zh:

Guard、effect 与表达式分层
---------------------------

DSL 把 numeric expression 和 condition 分开，是因为 value computation 与 control-flow decision 的 portability risk 和 diagnostic 需求不同。

.. code-block:: fcstm

   Sampling -> Done : if [sensor >= target] effect {
       next_sample = sensor + 1;
       alarm_count = (next_sample > target) ? alarm_count + 1 : alarm_count;
   };

Guard 先被测试。Effect 只有在 transition 被选中后才运行。``next_sample`` 是 effect block 内的 block-local temporary，离开 block 后不会成为 persistent state。

Target-profile warning 也必须在这里保持精确。关于 fixed-width integer range、division policy、shift count 或 float bitwise behavior 的 numeric diagnostic，是 ``c``、``c_poll``、``cpp``、``cpp_poll`` 的 C/C++ deployment-profile warning，除非 diagnostic 明确另有说明。它不是 Python generated runtime 具有同样 fixed-width 或 undefined-behavior 风险的证据。

.. _dsl-lifecycle-hooks-semantics-zh:

Lifecycle、abstract hooks 与 refs
---------------------------------

Lifecycle action 把行为挂到 state boundary 和 active cycle 上：

* ``enter`` 属于 entry；
* plain leaf ``during`` 属于 ordinary active cycle；
* ``exit`` 属于 exit；
* named action 提供稳定的 reference target 和 generated hook name；
* ``abstract`` 表示 generated code 调用用户实现；
* ``ref`` 复用 named lifecycle action path。

.. code-block:: fcstm

   state Device {
       enter SharedInit {
           ready = 1;
       }
       state Idle {
           enter ref /SharedInit;
           during abstract PollHardware;
       }
   }

``ref`` 指向 named lifecycle action，不指向 state 或 event。这样可复用行为仍然显式，不会把 state name 同时当作 callable procedure。

.. _dsl-during-aspect-semantics-zh:

During before/after 与 aspects
------------------------------

两套不同功能都使用 during-stage 词汇：

* plain ``during before`` / ``during after`` 属于 composite boundary；
* ``>> during before`` / ``>> during after`` 是 ancestor 贡献给 descendant leaf-state active cycle 的 aspect。

``hierarchy_execution.fcstm`` 用数值累加让顺序可观察。概念上，一个 leaf active cycle 会看到：

.. code-block:: text

   ancestor >> during before
   parent   >> during before
   leaf     during
   parent   >> during after
   ancestor >> during after

Child-to-child transition 不运行 plain composite ``during before`` 或 ``during after``。Combo pseudo relay state 也不执行 aspect action。Relay state 是 routing machinery；如果 aspect 观察每个 relay hop，就会把实现细节变成业务行为。

.. _dsl-combo-relay-semantics-zh:

Pseudo 与 combo relay 语义
--------------------------

Combo transition 解决 event-plus-guard 需求，不需要发明一个把普通 event suffix 和普通 guard suffix 混在一起的 transition form。

作者写的 transition：

.. code-block:: fcstm

   Waiting -> Accepted :: Request + [ready > 0] + Confirm effect {
       accepted = accepted + 1;
   }

Model construction 会把它展开成 pseudo relay chain。Inspect 保留两种视图：

* ``combo_origins`` 记录原始 trigger terms 和 source spans；
* ``combo_transitions`` 记录带 provenance 的 generated edges；
* generated pseudo states 使用 reserved ``__combo_`` prefix。

Final effect 属于到 ``Accepted`` 的语义 transition，不能复制到每个 relay hop。如果同一个 cycle 中缺少某个 required event 或 guard term，chain 不完成，可见 state 不应悄悄前进到 final target。

``W_COMBO_DUPLICATE_EVENT`` 和 combo guard diagnostics 会指回作者写的 trigger term，而不仅仅指向 generated pseudo state。这就是 inspect diagnostic 能指导用户或 LLM 回到原始 DSL source 的原因。

.. _dsl-forced-transition-expansion-zh:

Forced transition 展开
----------------------

Forced transition 是另一种展开：它把一个 source pattern 复制到多个 concrete sources。

.. code-block:: fcstm

   !* -> ErrorHandler :: CriticalError;

展开后的 transition 在 runtime 上是 ordinary transitions：normal exit action 仍会运行，然后运行 target entry。Forced transition 不能带 ``effect`` block，因为带 side effect 的 many-source shorthand 很难审计。若所有 expanded sources 都需要同一更新，请把行为放在 target ``enter``，或写显式 normal transitions。

Forced transition 也不能带 combo ``+`` chain。Combo 是 ordered relay expansion；forced 是 source-set expansion。二者分开后，展开模型才容易 inspect。

.. _dsl-import-assembly-semantics-zh:

Import assembly 语义
--------------------

Import syntax 可以写在 composite state 内，但 file loading 和 module assembly 在 parsing 之后运行。

.. code-block:: fcstm

   import "./import_worker.fcstm" as LeftWorker {
       def sensor_* -> left_$1;
       def speed -> plant_speed;
       event /Start -> Start named "Shared Start";
   }

Parser 记录 path、alias、optional display name 和 mapping statements。Import/model 层随后解析 path、加载 imported root、检查 conflict、重写 variable name、重写 event path，并把 imported root 作为 alias 下的 child state 加入 host。

Mapping template 不是任意代码。``$0`` 是完整 matched imported variable name；``$1`` / ``${1}`` 是 wildcard selector 的 capture group；``*`` 是 fallback template。Directory project 必须 import 具体 entry file，例如 ``./line/main.fcstm``，因为 bare directory 不是 DSL source。

设计边界
--------

DSL 有意比通用编程语言更窄：

* operation block 中没有 loop；
* DSL source 中没有用户自定义 function；
* ordinary transition 不把 event syntax 和 guard syntax 写成两个后缀；
* forced transition 没有 effect，也没有 combo chain；
* combo relay pseudo state 是纯 routing helper；
* target-risk diagnostic 必须说明 target profile。

这些边界让模型保持 parseable、inspectable、simulatable，并适合生成多种 target language 的代码。
