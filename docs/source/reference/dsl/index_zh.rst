.. _sec-reference-dsl-zh:

DSL 参考
========

.. contents:: 目录
   :local:
   :depth: 2

范围
----

本页是面向事实查询的 DSL reference。内容已对照当前拆分后的 grammar 文件，尤其是 ``pyfcstm/dsl/grammar/GrammarParser.g4`` 和 ``pyfcstm/dsl/grammar/GrammarLexer.g4``。第一次学习请看 :doc:`../../tutorials/dsl/index_zh`，任务写法请看 :doc:`../../how_to/dsl/index_zh`，语义背景请看 :doc:`../../explanations/dsl_semantics/index_zh`。

顶层结构
--------

.. code-block:: fcstm

   def int counter = 0;
   def float target = 22.5;

   state Root {
       [*] -> Idle;
       state Idle;
   }

事实：

* 持久变量写在唯一根 ``state`` 之前。
* 当前持久变量类型是 ``int`` 和 ``float``。
* 顶层只能有一个 root state definition。
* 注释可使用 ``// ...``、``# ...`` 或 ``/* ... */``。

状态形式
--------

.. list-table:: 状态定义形式
   :header-rows: 1

   * - 形式
     - 含义
     - 说明
   * - ``state Name;``
     - leaf state
     - 不包含子声明。
   * - ``state Name { ... }``
     - composite state
     - 必须用 ``[*] -> Child;`` 选择初始子状态。
   * - ``pseudo state Name;``
     - pseudo leaf state
     - 用于自动流程展开和中继路由。
   * - ``pseudo state Name { ... }``
     - pseudo composite state
     - 较少使用；除非功能明确需要，否则 pseudo state 应保持纯中继语义。
   * - ``state Name named "Display";``
     - named state
     - 增加显示名，不改变 identifier。

转换形式
--------

.. list-table:: 常见转换形式
   :header-rows: 1

   * - 形式
     - 含义
     - 是否允许 effect
   * - ``[*] -> Target;``
     - composite 内初始转换
     - 允许：``effect { ... }``
   * - ``Source -> Target;``
     - plain transition
     - 允许
   * - ``Source -> Target :: LocalEvent;``
     - 本地事件转换
     - 允许
   * - ``Source -> Target : ParentEvent;``
     - chain-scoped 事件转换
     - 允许
   * - ``Source -> Target : /RootEvent;``
     - root-scoped 事件转换
     - 允许
   * - ``Source -> Target : if [condition];``
     - guard transition
     - 允许
   * - ``Source -> [*];``
     - 到 owning composite exit marker 的退出转换
     - 允许

普通转换不要把 event 语法和 ``: if [...]`` guard 语法混在一起。显式组合请使用 combo trigger 形式。

Combo trigger 形式
~~~~~~~~~~~~~~~~~~

combo trigger 用 ``+`` 连接 event term 和 guard term。parser 接受如下形式：

.. code-block:: fcstm

   Source -> Target :: Event + [x > 0];
   Source -> Target : Parent.Event + [x > 0];
   Source -> Target : [x > 0] + Parent.Event;

DSL 语义解释页说明 combo trigger 如何展开，以及为什么会出现 pseudo 中继状态。完整 runtime cycle 行为留给执行语义文档。

强制转换形式
~~~~~~~~~~~~

.. code-block:: fcstm

   !State -> Target :: Event;
   !State -> [*] : if [condition];
   !* -> Target : /Reset;
   !* -> [*];

forced transition 会展开为普通转换，目前不支持 ``effect`` block。需要更新变量时，请在显式普通转换上写 side effect。

事件和作用域
------------

在 composite state 内声明事件：

.. code-block:: fcstm

   event Start;
   event Stop named "Stop button";

.. list-table:: 事件作用域形式
   :header-rows: 1

   * - 形式
     - 含义
     - 常见用途
   * - ``:: Local``
     - source-local event name
     - 从 source state 命名空间解析事件。
   * - ``: ParentEvent``
     - chain-scoped event path
     - 沿 containing scopes 搜索事件。
   * - ``: /GlobalEvent``
     - root-scoped absolute path
     - 从 root namespace 解析事件。
   * - ``: Parent.Child.Event``
     - dotted chain path
     - 事件由具名嵌套作用域拥有时使用。

Guard、effect 和操作块
----------------------

guard 在方括号中使用 condition expression：

.. code-block:: fcstm

   A -> B : if [temperature >= target && failures < 3];

effect 和 lifecycle action 使用 operation statements：

.. code-block:: fcstm

   A -> B effect {
       failures = failures + 1;
       tmp = failures * 2;
   }

事实：

* 赋值右侧需要 arithmetic expression。
* guard 需要 boolean condition。
* block-local 临时名可以在同一个 block 中先赋值再读取。
* operation block 内可以使用 ``if [condition] { ... } else { ... }``。

表达式事实
----------

.. list-table:: 表达式类别
   :header-rows: 1

   * - 类别
     - 示例
     - 使用位置
   * - 整数字面量
     - ``0``、``42``、``0xFF``
     - ``int`` 初始化和 arithmetic expression。
   * - 浮点字面量
     - ``3.14``、``.5``、``1e-6``
     - ``float`` 初始化和 arithmetic expression。
   * - 常量
     - ``pi``、``E``、``tau``
     - numeric expression。
   * - 算术运算符
     - ``+``、``-``、``*``、``/``、``%``、``**``
     - numeric expression。
   * - 位运算符
     - ``&``、``|``、``^``、``<<``、``>>``
     - integer-style numeric expression。
   * - 比较
     - ``<``、``<=``、``==``、``!=``、``>=``、``>``
     - 把 numeric expression 转成 condition。
   * - 布尔运算符
     - ``&&`` / ``and``、``||`` / ``or``、``!`` / ``not``
     - condition。
   * - 蕴含 / 等价
     - ``=>`` / ``implies``、``iff``
     - condition。
   * - 布尔 xor
     - ``xor``
     - condition。不要把 numeric ``^`` 当成 boolean xor。

lexer 支持的 unary math function 包括 ``sin``、``cos``、``tan``、``sqrt``、``exp``、``log``、``log10``、``abs``、``ceil``、``floor``、``round``、``trunc`` 以及相关反函数 / 双曲函数。

生命周期形式
------------

.. list-table:: lifecycle action 形式
   :header-rows: 1

   * - 形式
     - 含义
   * - ``enter { ... }``
     - 进入 state 时执行的 concrete action。
   * - ``enter Name { ... }``
     - 具名 concrete enter action。
   * - ``enter abstract Hook;``
     - 由 runtime integration 提供的 abstract hook。
   * - ``enter ref Path.To.Action;``
     - 引用具名 lifecycle action。
   * - ``during { ... }``
     - active cycle 中执行的 concrete action。
   * - ``during before { ... }`` / ``during after { ... }``
     - composite before/after action 形式。
   * - ``>> during before { ... }`` / ``>> during after { ... }``
     - 面向 descendant leaf-state cycles 的 aspect action。
   * - ``exit { ... }``
     - 离开 state 时执行的 concrete action。

按照 grammar，``enter``、``during``、``>> during`` 和 ``exit`` 都有对应的具名、``abstract``、文档注释和 ``ref`` 变体。

Import 形式
-----------

import 只能写在 composite state 内：

.. code-block:: fcstm

   import "worker.fcstm" as Worker;

   import "worker.fcstm" as Worker named "Worker subsystem" {
       def * -> worker_$0;
       event /Done -> /WorkerDone;
   }

.. list-table:: import mapping 形式
   :header-rows: 1

   * - 形式
     - 含义
   * - ``def * -> prefix_$0;``
     - fallback variable mapping。
   * - ``def {a, b} -> mapped_$0;``
     - set selector mapping。
   * - ``def sensor_* -> sensor_$0;``
     - compact wildcard selector 和 target template。
   * - ``def exact -> renamed;``
     - exact variable mapping。
   * - ``event Source.Event -> Target.Event;``
     - event mapping，可选 ``named "Display"``。

compact selector 和 target-template 对空白敏感，因为 lexer 会在 import-specific mode 中识别它们。若空白切开 compact pattern，parser 会在 mapping 位置报错。

事实校验说明
------------

本页使用当前拆分 grammar 文件名：``GrammarParser.g4`` 和 ``GrammarLexer.g4``。旧文档中提过的单个 ``Grammar.g4`` 已不是当前源码布局。

面向 LLM prompt 的建模规则另见包内指南 ``pyfcstm/llm/fcstm_grammar_guide.md``。
