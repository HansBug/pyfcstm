
.. _sec-explanations-dsl-semantics-zh:

DSL 语义解释
================

.. contents:: 语义地图
   :local:
   :depth: 2

范围
----------

本页解释 FCSTM DSL 为什么这样设计。它不是语法表；精确形式请看 :doc:`../../reference/dsl/index_zh`。它也不是首次成功教程；第一次建模请看 :doc:`../../tutorials/dsl/index_zh`。完整 runtime cycle ordering、hot start 和 simulator history 属于 :doc:`../execution_semantics/index_zh`。

.. _dsl-root-design-zh:

为什么变量在唯一 root state 之前
--------------------------------

一个模型描述一个层次化 controller。Persistent variables 放在前面，可以在阅读 transitions 和 lifecycle actions 之前先确定数据表面。唯一 root state 则为所有 state、event、transition、import 和 lifecycle action 提供共同 ownership tree。

这个结构也让 generation 更可预测。Templates 可以围绕一个 runtime object、一个 active-stack representation 和一份 variable store 生成代码。Import assembly 也可以把 child subsystem 重写进这棵树，而不是合并多个互不相关的 roots。

.. _dsl-ownership-name-resolution-zh:

所有权树与名称解析
------------------

States、events 和 lifecycle actions 都由 states 拥有。因此 name resolution 是建模规则，不只是 parser 便利。两个 child states 之间的 transition 应该写在拥有这两个名字的 parent 中。Composite 外部的 transition 应该进入 composite boundary，再由该 composite 的 initial transition 选择 child。

这样 ownership 保持局部，也避免 parent-level rule 依赖某个 child composite 内部的 private leaf。

.. _dsl-composite-entry-semantics-zh:

组合状态进入与 initial transition
----------------------------------

Composite state 是 active boundary 加 child-selection rule。进入 composite 表示先进入 boundary，然后跟随 initial transition 到选中的 child。这和 composite 内部 child-to-child transition 不同，后者的 owner 已经知道两个 endpoint。

当 transition target 是 composite 时，target 是 boundary。Initial transition 决定 child path。这就是 DSL 不鼓励 outer-scope 直接跳到 inner leaf 的原因。

.. _dsl-event-ownership-signal-zh:

Event scope 作为 ownership signal
---------------------------------------

三种 event scope spelling 表示 ownership 距离：

* ``:: Local`` 表示 source state 局部拥有或命名该 event。
* ``: EventPath`` 表示 containing 或 named scope 拥有该 event。
* ``: /RootEvent`` 表示 event path 从 root 开始绝对解析。

这个区别影响重构。Root event 可以作为公开 protocol 移动或改名。Local event 可以保持一个 state 的私有信号，不要求 sibling states 共享同一个 event declaration。

.. _dsl-expression-separation-zh:

Guard、effect 与表达式分层
---------------------------

DSL 把 numeric expressions 与 conditions 分开，因为 control flow 和 value computation 有不同的 portability risk。Assignments 和 numeric initializers 更新 numbers。Guards 决定 transition 是否启用。Comparisons 把 numeric values 桥接为 conditions。

当文档讨论 generated C/C++ code 时，这个分层尤其重要。Fixed-width integer、division-by-zero policy 或 bitwise operation profile 的 warning 是 C/C++ deployment-profile warning。除非存在 Python-specific evidence，否则不能写成 Python generated-runtime failure。

.. _dsl-lifecycle-hooks-semantics-zh:

Lifecycle、abstract hooks 与 refs
---------------------------------------

Lifecycle actions 把行为挂到 state boundaries 和 active cycles 上：``enter`` 表示 entry，``during`` 表示 active，``exit`` 表示 exit。Named actions 让 generated extension points 更容易发现。``abstract`` hooks 表示 generated code 调用用户提供的行为，而不需要编辑 generated files。``ref`` 复用 named lifecycle action，同时保持 state tree 显式。

这个设计把 model structure 和 integration behavior 分开。DSL 说明行为属于哪里；generated runtime 暴露 target-language hooks 来实现 abstract behavior。

.. _dsl-during-aspect-semantics-zh:

During before/after 与 aspects
-------------------------------------

Plain ``during before`` / ``during after`` 属于 composite lifecycle boundary。``>> during before`` / ``>> during after`` 是 ancestor 贡献给 descendant leaf-state active cycles 的 aspect actions。它们都使用 during-stage 词汇，但不是同一个功能。

Aspects 不在 combo pseudo relay states 内运行。Pseudo relays 是为 evaluated expanded transition terms 创建的 routing machinery；如果让 ancestor aspects 观察每个 relay，就会把 implementation detail 变成 business behavior。

.. _dsl-combo-relay-semantics-zh:

Pseudo 与 combo relay 语义
-------------------------------

Pseudo states 表示 control-flow routing。Combo transitions 使用这个概念，把 event-plus-guard 或 multi-term trigger 转换成一串更简单的 routing checks。这个 chain 对外应该保持原始 combo transition 的语义，同时 diagnostics 仍然可以检查每个 term。

重要边界：

* relay pseudo states 应该是纯 routing helpers；
* reserved ``__combo`` names 属于 generated relay machinery；
* effect placement 必须保持原始 combo transition 的 semantic effect；
* duplicate event 和 constant guard diagnostics 用来发现令人意外的 trigger definitions；
* aspects 不在 relay chain 内执行。

Runtime ordering details 属于 :doc:`../execution_semantics/index_zh`。

.. _dsl-forced-transition-expansion-zh:

Forced transition 展开
----------------------------

Forced transitions 是把一个声明展开到选定 source states 的 shorthand。``!State`` 从一个 named source 展开；``!*`` 从 owner scope 中所有适用 sources 展开。Forced transitions 有意不支持 ``effect`` blocks，因为带 side effects 的展开声明难以审计，也会模糊到底哪个 source 拥有 update。

需要 effects 时，请写 explicit normal transitions，让 source、target、trigger 和 update block 都可见。

.. _dsl-import-assembly-semantics-zh:

Import assembly 语义
--------------------------

Import syntax 在 composite states 内解析，但 path resolution 和 model assembly 在 parsing 之后执行。这个分层让 grammar 保持 structural，同时由 Python import/model layer 处理 file lookup、recursive loading、aliasing、variable mappings、event mappings、conflict checks 和 diagnostics。

目录组织的项目必须 import 显式 entry file，例如 ``./line/main.fcstm``。Bare directory 不是 DSL file，不应该被文档写成受支持。

设计边界
------------

DSL 有意比 general programming language 更窄：

* operation blocks 中没有 loops；
* 没有任意 function definitions；
* arithmetic 和 condition expressions 分开；
* imports 组装 state-machine modules，而不是执行代码；
* generated-target risks 必须带 target scope 描述。

这些限制让模型保持 inspectable、renderable、simulatable，并适合生成多种 target languages 的代码。
