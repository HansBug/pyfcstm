.. _sec-explanations-dsl-semantics-zh:

DSL 语义解释
============

.. contents:: 目录
   :local:
   :depth: 2

范围
----

本页解释 FCSTM DSL 背后的语义和设计边界。它不是语法表；精确形式请看 :doc:`../../reference/dsl/index_zh`。它也不是第一次学习路径；第一次建模请看 :doc:`../../tutorials/dsl/index_zh`。属于 simulator 的完整 runtime cycle 细节，例如 hot start、完整 ``during before`` / ``during after`` 顺序，留给 execution-semantics 工作处理。

为什么先写变量且只有一个根状态
------------------------------

FCSTM 模型一次描述一个层次化控制器。把持久变量放在唯一 root state 之前，可以在引入行为之前先明确模型数据。root state 则为所有 transition、event 和 lifecycle action 提供共同的 ownership tree。

这种结构也让生成代码更可预测：模板可以围绕一个 runtime object、一个 active-state stack 和一份 variable store 生成代码。

层级和初始转换
--------------

composite state 不只是命名空间。它拥有子状态，并通过 initial transition 选择第一个 active child。因此每个 composite state 都需要 ``[*] -> Child;``。

转换到 composite state 时，先进入 composite，再由 initial transition 选择子状态。两个子状态之间的转换属于 owning composite，这样 name resolution 和 lifecycle ownership 都保持局部。

Pseudo 和 combo transition
--------------------------

pseudo state 是中间控制流节点，应被看作路由辅助，而不是用户可见的业务状态。combo trigger syntax 使用这个思想：把 event 和 guard 组合起来的转换可以展开成使用 pseudo intermediate states 的简单检查链。

DSL 层面的语义是：

* event term 和 guard term 是不同 trigger term。
* ``+`` 表示 combo trigger 在生成路线中需要列出的 term，不表示普通 event 语法和 guard 语法可以任意混用。
* pseudo intermediate states 用于展开和路由，不应承载用户业务行为。
* 如果生成的 pseudo-state 名称会和真实 state 冲突，model construction 应伸长生成名或报告冲突，而不是静默覆盖用户状态。

展开后的精确 runtime 顺序属于 execution-semantics 验证范围，尤其是在后续继续收紧 combo 行为时。

事件作用域和归属
----------------

event 和 child state 一样由状态拥有。三种 event 形式用于在不同距离上表达 ownership：

* ``:: Event`` 表示“当前 transition source 语境下的本地事件”。
* ``: Event`` 或 ``: Parent.Event`` 表示“沿 containing 或具名 scope 链解析”。
* ``: /Event`` 表示“从 root 开始解析”。

使用能表达 ownership 的最短形式。过度使用 root-scoped event 会让大模型难以重构；过度使用 local event 则可能隐藏共享协议信号。

Guard、effect 和表达式分离
--------------------------

DSL 区分 arithmetic expression 和 condition，是因为生成 runtime 可能面向比 Python 更严格的目标语言。assignment 更新 numeric variable；guard 决定控制流；comparison 把二者连接起来。

这对 C/C++ target code 尤其重要，因为依赖 Python truthiness 的表达式在 C/C++ 环境下可能误导。Python 生成代码也许能容忍更多 runtime value，但 DSL reference 应描述语言级契约，而不是某个 backend 的偶然行为。

Lifecycle 和 aspect 边界
------------------------

``enter`` 和 ``exit`` 是 state-bound lifecycle hooks。``during`` 是 active cycle hook。named、``abstract`` 和 ``ref`` 形式用于把模型结构与用户提供的 integration behavior 分离。

``>> during before`` 和 ``>> during after`` 是面向 descendant leaf-state cycles 的 aspect action。它们不应该给 combo pseudo intermediate states 添加业务行为。这样 combo 展开保持为控制流细节，而不会制造令人意外的可观察 lifecycle 行为。

Import 装配语义
---------------

import 会把另一个 FCSTM 文件装配成子系统。被导入文件保留自己的公开入口结构，mapping 则改写需要唯一化或需要连接到父模型的名字。

import grammar 有意只负责 syntax。文件解析、递归加载、mapping precedence、冲突检测和改写后的 model assembly 都属于 parse 之后的 Python 阶段。这种拆分让 grammar 文件保持可复用，也让 diagnostics 能结合 model context 解释装配失败。

设计边界
--------

DSL 有意比通用编程语言更窄：

* 它建模 controller state 和 transition，不建模任意计算。
* operation block 支持 assignment 和 conditional block，不支持 loop。
* event 和 state 由 scope 拥有，而不是全局字符串。
* import 装配 state-machine fragment，而不是文本 include。
* generated runtime templates 必须能保持 simulator semantics。

这些约束让模型可 inspect、可 render、可 simulate，也适合生成目标语言代码。
