
.. _sec-reference-dsl-zh:

DSL 参考
==============

.. contents:: 参考地图
   :local:
   :depth: 2

范围
----------

本页是面向事实查询的 FCSTM DSL reference。它对照当前拆分后的 grammar 文件，尤其是 ``pyfcstm/dsl/grammar/GrammarParser.g4`` 和 ``pyfcstm/dsl/grammar/GrammarLexer.g4``。需要学习路径请看 :doc:`../../tutorials/dsl/index_zh`，任务写法请看 :doc:`../../how_to/dsl/index_zh`，语义背景请看 :doc:`../../explanations/dsl_semantics/index_zh`。

.. _dsl-coverage-matrix-zh:

DSL 覆盖矩阵
----------------

``N/A`` 表示该页面类型有意不承担这个 leaf ability。每一行仍然必须有 reference 或 explanation 落点。

.. list-table:: DSL 能力覆盖
   :header-rows: 1
   :widths: 16 13 22 18 18 18 18 24 14

   * - feature_id
     - 能力族
     - 事实源
     - Tutorial 覆盖
     - How-to 覆盖
     - Reference 覆盖
     - Explanation 覆盖
     - 示例 / 验证
     - EN/ZH
   * - ``dsl-lexical-comments``
     - lexical
     - ``GrammarLexer.g4`` comments / strings / IDs
     - N/A：tutorial 不展示 token table
     - N/A：task page 使用 snippets
     - :ref:`dsl-lexical-forms-zh`
     - N/A：syntax token facts
     - reference table review
     - synced
   * - ``dsl-top-level-root``
     - top-level
     - ``state_machine_dsl`` / root ``state_definition``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-small-valid-model-task-zh`
     - :ref:`dsl-top-level-forms-zh`
     - :ref:`dsl-root-design-zh`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-top-level-def``
     - top-level
     - ``def_assignment`` / ``init_expression``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-top-level-forms-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-import-preamble``
     - import
     - ``preamble_program`` / ``constant_definition`` / ``initial_assignment``
     - N/A：tutorial 不展开 import
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-preamble-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_*.fcstm`` inspect
     - synced
   * - ``dsl-state-leaf-composite``
     - state
     - ``state_definition`` leaf/composite branches
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-ownership-name-resolution-zh`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-state-pseudo``
     - state
     - ``PSEUDO STATE`` / ``E_PSEUDO_NOT_LEAF``
     - N/A：tutorial 只链接高级 routing
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-combo-relay-semantics-zh`
     - ``pseudo_state_demo.fcstm`` inspect
     - synced
   * - ``dsl-state-target-resolution``
     - state
     - model state lookup / transition ownership
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-state-target-task-zh`
     - :ref:`dsl-state-forms-zh`
     - :ref:`dsl-ownership-name-resolution-zh`
     - scope snippets / model validation
     - synced
   * - ``dsl-transition-initial``
     - transition
     - ``entryTransitionDefinition``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-small-valid-model-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-composite-entry-semantics-zh`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-transition-plain-event``
     - transition
     - ``normalTransitionDefinition`` / event terms
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh` / :ref:`dsl-event-scopes-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-event-ownership-signal-zh`
     - ``event_scoping_complete.fcstm`` inspect
     - synced
   * - ``dsl-transition-guard-effect``
     - transition
     - ``COLON IF`` / ``EFFECT`` operation block
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``guards_and_effects.fcstm`` inspect
     - synced
   * - ``dsl-transition-combo``
     - transition
     - ``combo_transition_trigger`` / ``entry_combo_transition_trigger``
     - N/A：tutorial 只链接高级 transition
     - :ref:`dsl-combo-transition-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-combo-relay-semantics-zh`
     - combo fragments + semantic fixtures
     - synced
   * - ``dsl-transition-forced``
     - transition
     - ``transition_force_definition``
     - N/A：tutorial 只链接高级 transition
     - :ref:`dsl-forced-transition-task-zh`
     - :ref:`dsl-transition-forms-zh`
     - :ref:`dsl-forced-transition-expansion-zh`
     - ``forced_transitions.fcstm`` inspect
     - synced
   * - ``dsl-event-scopes``
     - event
     - ``event_definition`` / ``chain_id``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-event-scopes-task-zh`
     - :ref:`dsl-events-scopes-zh`
     - :ref:`dsl-event-ownership-signal-zh`
     - ``event_scoping_complete.fcstm`` inspect
     - synced
   * - ``dsl-operation-assignment-temp``
     - operation
     - ``operation_assignment`` / local temp tracking
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-operation-blocks-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``guards_and_effects.fcstm`` inspect
     - synced
   * - ``dsl-operation-conditionals``
     - operation
     - ``if_statement`` / empty statement
     - N/A：tutorial 保持 block 简短
     - :ref:`dsl-guards-effects-task-zh`
     - :ref:`dsl-operation-blocks-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``guards_and_effects.fcstm`` inspect
     - synced
   * - ``dsl-expression-init``
     - expression
     - ``init_expression``
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - top-level initializer snippets
     - synced
   * - ``dsl-expression-runtime``
     - expression
     - ``num_expression`` / math functions / bitwise
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_demo.fcstm`` inspect
     - synced
   * - ``dsl-expression-condition``
     - expression
     - ``cond_expression`` / comparison / boolean ops
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_demo.fcstm`` inspect
     - synced
   * - ``dsl-expression-ternary``
     - expression
     - ``conditionalCStyleExprNum`` / ``conditionalCStyleCondNum``
     - N/A：tutorial 保持 arithmetic 简单
     - :ref:`dsl-expression-safety-task-zh`
     - :ref:`dsl-expression-reference-zh`
     - :ref:`dsl-expression-separation-zh`
     - ``expression_demo.fcstm`` inspect
     - synced
   * - ``dsl-lifecycle-concrete``
     - lifecycle
     - ``enter`` / ``during`` / ``exit`` operation forms
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-lifecycle-task-zh`
     - :ref:`dsl-lifecycle-forms-zh`
     - :ref:`dsl-lifecycle-hooks-semantics-zh`
     - ``first_thermostat.fcstm`` inspect
     - synced
   * - ``dsl-lifecycle-named-abstract-ref``
     - lifecycle
     - named / ``abstract`` / doc-comment / ``ref`` branches
     - N/A：tutorial 只链接高级 hook
     - :ref:`dsl-lifecycle-task-zh`
     - :ref:`dsl-lifecycle-forms-zh`
     - :ref:`dsl-lifecycle-hooks-semantics-zh`
     - ``abstract_reference_demo.fcstm`` inspect
     - synced
   * - ``dsl-aspect-forms``
     - aspect
     - ``during_aspect_definition``
     - N/A：tutorial 只给入口链接
     - :ref:`dsl-aspect-task-zh`
     - :ref:`dsl-aspect-forms-zh`
     - :ref:`dsl-during-aspect-semantics-zh`
     - lifecycle diagrams / fragments
     - synced
   * - ``dsl-import-basic-alias``
     - import
     - ``import_statement`` header
     - N/A：tutorial 不展开 import
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_basic.fcstm`` inspect
     - synced
   * - ``dsl-import-mapping``
     - import
     - ``def_mapping_statement`` / ``event_mapping_statement``
     - N/A：tutorial 不展开 import
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_mapped.fcstm`` inspect
     - synced
   * - ``dsl-import-directory-boundary``
     - import
     - import path resolution in ``model/imports.py``
     - N/A：tutorial 不展开 import
     - :ref:`dsl-import-task-zh`
     - :ref:`dsl-import-forms-zh`
     - :ref:`dsl-import-assembly-semantics-zh`
     - ``import_host_directory.fcstm`` inspect
     - synced
   * - ``dsl-diagnostics-target-risk``
     - diagnostics
     - ``pyfcstm/diagnostics/codes.yaml`` / analyzers
     - :ref:`sec-tutorials-dsl-zh`
     - :ref:`dsl-diagnostics-task-zh`
     - :ref:`dsl-diagnostics-risk-zh`
     - :ref:`dsl-expression-separation-zh`
     - risk wording line audit
     - synced

.. _dsl-lexical-forms-zh:

词法与注释形式
---------------

.. list-table:: Lexical forms
   :header-rows: 1

   * - 形式
     - Syntax / tokens
     - Notes
   * - Identifier
     - ``[a-zA-Z_][a-zA-Z0-9_]*``
     - 用于 variables、states、events、action names、aliases 和 path parts。
   * - String
     - single 或 double quoted strings
     - Import paths 和 ``named`` labels 使用 strings；常见 escape sequences 由 lexer 处理。
   * - Comments
     - ``/* ... */``、``// ...``、``# ...``
     - Multiline comment 在特定 lifecycle forms 中可以成为 abstract-action documentation。
   * - Keywords
     - ``def``、``state``、``pseudo``、``event``、``import``、``enter``、``during``、``exit``、``abstract``、``ref``
     - Keywords 由 lexer rules 保留。
   * - Compact import tokens
     - selector patterns and target templates
     - Compact forms 在 import-specific lexer modes 中 tokenized，对 whitespace 敏感。

.. _dsl-top-level-forms-zh:

顶层程序形式
--------------

普通 DSL entry 是零个或多个持久变量声明，后面接一个 root state。

片段：

.. code-block:: fcstm

   def int counter = 0;
   def float threshold = 3.5;

   state Root {
       [*] -> Idle;
       state Idle;
   }

事实：

* 持久变量类型是 ``int`` 和 ``float``。
* 声明必须出现在唯一 root ``state`` 之前。
* Initializers 使用 ``init_expression``。这个子集接受 literal、math constant、arithmetic、bitwise operator 和 unary math function，但不接受 runtime variable reference，也不接受 C-style ternary expression。
* root 可以是 leaf 或 composite；实际模型通常使用 composite root state。

.. _dsl-import-preamble-forms-zh:

Import preamble 形式
--------------------------

Import assembly pipeline 还会解析 preamble entry point。

.. list-table:: Preamble forms
   :header-rows: 1

   * - Rule
     - Syntax
     - Meaning
   * - ``constant_definition``
     - ``name = init_expression;``
     - 为 import assembly 定义 constant-like preamble value。
   * - ``initial_assignment``
     - ``name := init_expression;``
     - 在 import preamble context 中提供 initial assignment。

这些 forms 不是普通 top-level ``def`` declarations。它们让 imported modules 在被 host 重写之前暴露 assembly-time constants 或 initial values。

.. _dsl-state-forms-zh:

状态形式
------------

.. list-table:: State forms
   :header-rows: 1

   * - 形式
     - Syntax
     - 边界
   * - Leaf state
     - ``state Name;``
     - Stoppable runtime state。
   * - Named leaf state
     - ``state Name named "Label";``
     - 添加 display metadata。
   * - Composite state
     - ``state Name { ... }``
     - 拥有 child declarations；必须选择 initial child。
   * - Pseudo state
     - ``pseudo state Name;``
     - Routing helper；combo relay 使用时应保持 leaf-like 且 action-free。
   * - Pseudo composite syntax
     - ``pseudo state Name { ... }``
     - Parser shape 存在，但 model validation 会用 ``E_PSEUDO_NOT_LEAF`` 拒绝 non-leaf pseudo states。

State path 在接受 path 的形式中使用 dotted identifiers。Transition target resolution 仍由 owning state scope 决定；避免越过 composite owner 直接跳到 nested leaf。

.. _dsl-transition-forms-zh:

转移形式
------------

.. list-table:: Transition families
   :header-rows: 1

   * - Family
     - Syntax shape
     - Effect allowed?
     - Notes
   * - Initial transition
     - ``[*] -> Target;`` 或带 entry combo trigger
     - Yes
     - 为 composite 选择 initial child。
   * - Normal transition
     - ``Source -> Target;``
     - Yes
     - Source 和 target 在 owner scope 中解析。
   * - Exit transition
     - ``Source -> [*];``
     - Yes
     - 通过 composite exit marker 离开。
   * - Event transition
     - ``Source -> Target :: Local;`` 或 ``: EventPath``
     - Yes
     - 普通 event form，不混入 guard syntax。
   * - Guard transition
     - ``Source -> Target : if [condition];``
     - Yes
     - Guard expression 只能是 condition。
   * - Guard plus effect
     - ``Source -> Target : if [condition] effect { ... }``
     - Yes
     - Event syntax 不属于这个 ordinary form。
   * - Combo trigger
     - 通过 combo rules 使用 ``[guard]`` alias 或 ``Event + [guard]`` terms
     - Yes for normal/entry combo expansion
     - 用于显式 event-plus-guard、guard alias 或多 trigger terms。
   * - Forced transition
     - ``!State -> Target ...;`` 或 ``!* -> Target ...;``
     - No
     - 展开到选定 source states。
   * - Forced exit transition
     - ``!State -> [*] ...;`` 或 ``!* -> [*] ...;``
     - No
     - Forced form 指向 exit marker。

Combo details：

* Local combo 使用 ``::`` 和 local event terms。
* Chain/root combo 使用 ``:`` 和 ``chain_id`` event terms。
* Entry combo triggers 可用于 initial transitions。
* ``: [condition]`` 是 single guard trigger 的 combo guard alias；``: if [condition]`` 是 ordinary guard spelling。
* 允许 ``: [enabled] + Start`` 这样的 leading guard combo term。
* Duplicate event terms 和 constant guards 是 diagnostics targets。
* Combo pseudo relay states 是 generated routing helpers，不是 business states，也不是 aspect-action execution points。

Forced transition details：

* ``!State`` 从 named source state 展开。
* ``!*`` 从 owner scope 中所有适用 source states 展开。
* Forced forms 可以带一个 local、chain/root 或 guard trigger。
* Forced forms 不能带 combo ``+`` trigger chain。
* Forced forms 不能有 ``effect`` block；需要 side effect 时请写 explicit normal transition。

.. _dsl-events-scopes-zh:

事件与作用域
--------------

.. list-table:: Event scope forms
   :header-rows: 1

   * - Form
     - Syntax
     - Meaning
   * - Event declaration
     - ``event Name;`` 或 ``event Name named "Label";``
     - 声明 containing state 拥有的 event。
   * - Source-local event
     - ``:: Name``
     - Source state local namespace 中的 event。
   * - Chain event
     - ``: Name`` 或 ``: Parent.Event``
     - 相对于 owning scope 的 event path。
   * - Root event
     - ``: /Name`` 或 ``: /Path.Event``
     - 从 root 开始的 absolute event path。

``chain_id`` 是可选 ``/`` 后接一个或多个 dotted identifiers。Source-private signals 使用 local events，containing protocols 使用 chain paths，全局拥有的事件使用 root paths。

.. _dsl-operation-blocks-zh:

Operation blocks
------------------------

Operation blocks 出现在 effects 和 lifecycle bodies 中。

.. list-table:: Operation statements
   :header-rows: 1

   * - Statement
     - Syntax
     - Notes
   * - Assignment
     - ``name = num_expression;``
     - 更新 persistent variable 或引入 block-local temporary。
   * - Conditional block
     - ``if [condition] { ... } else if [condition] { ... } else { ... }``
     - Conditions 使用 ``cond_expression``。
   * - Empty statement
     - ``;``
     - 作为 no-op statement 接受。

Block-local temporary 只在当前 operation block 内有效，并且只能在赋值后读取。Persistent variables 必须在 top-level ``def`` list 中声明。

.. _dsl-expression-reference-zh:

表达式参考
-------------

.. list-table:: Numeric expression facts
   :header-rows: 1

   * - Category
     - Forms
     - Notes
   * - Literals
     - decimal integer、hexadecimal integer、float
     - Float tokens 支持 decimal / exponent forms。
   * - Constants
     - ``pi``、``E``、``tau``
     - Math constants 可用于 initializers 和 numeric expressions。
   * - Variables
     - ``ID``
     - Runtime numeric variable 或 block-local temporary。
   * - Unary
     - ``+x``、``-x``
     - Prefix numeric sign。
   * - Power
     - ``x ** y``
     - Right associative。
   * - Multiplicative
     - ``*``、``/``、``%``
     - Numeric arithmetic。
   * - Additive
     - ``+``、``-``
     - Numeric arithmetic。
   * - Shift / bitwise
     - ``<<``、``>>``、``&``、``^``、``|``
     - Numeric bitwise operators；C/C++ profiles 可能触发 target warnings。
   * - Function call
     - ``sin(x)``、``sqrt(x)``、``abs(x)``、``sign(x)`` 等 lexer-listed math functions
     - 仅 unary math functions。
   * - C-style ternary
     - ``(cond) ? num_expr : num_expr``
     - ``?`` 前的 condition 必须加 parentheses。

.. list-table:: Condition expression facts
   :header-rows: 1

   * - Category
     - Forms
     - Notes
   * - Boolean literals
     - ``true`` / ``false`` variants
     - Lexer 接受常见大小写 variants。
   * - Not
     - ``!cond`` 或 ``not cond``
     - Prefix condition negation。
   * - Numeric comparison
     - ``<``、``>``、``<=``、``>=``、``==``、``!=``
     - 把 numeric expressions 桥接为 conditions。
   * - Condition equality
     - ``cond == cond``、``cond != cond``、``cond iff cond``
     - Condition-level equality and equivalence。
   * - Boolean composition
     - ``&&`` / ``and``、``||`` / ``or``、``xor``
     - 不要用 ``^`` 表示 boolean xor；``^`` 是 numeric bitwise xor。
   * - Implication
     - ``=>`` 或 ``implies``
     - Right associative；不要用 ``->`` 表示 implication。
   * - C-style ternary
     - ``(cond) ? cond : cond``
     - Condition result ternary。

Operator precedence 按 grammar rule order 从紧到松：parentheses/literals/functions、unary signs、power、multiplicative、additive、shift、bitwise ``&`` / ``^`` / ``|``、comparisons、condition equality / ``iff``、``and``、``xor``、``or``、implication 和 ternary forms。

.. _dsl-lifecycle-forms-zh:

生命周期形式
--------------

.. list-table:: Lifecycle action forms
   :header-rows: 1

   * - Stage
     - Concrete
     - Named concrete
     - Abstract
     - Doc-comment abstract
     - Ref
   * - ``enter``
     - ``enter { ... }``
     - ``enter Name { ... }``
     - ``enter abstract Name;``
     - ``enter abstract Name? /* doc */``
     - ``enter Name? ref Path;``
   * - ``during``
     - ``during { ... }``
     - ``during Name { ... }``
     - ``during abstract Name;``
     - ``during abstract Name? /* doc */``
     - ``during Name? ref Path;``
   * - ``during before``
     - ``during before { ... }``
     - ``during before Name { ... }``
     - ``during before abstract Name;``
     - ``during before abstract Name? /* doc */``
     - ``during before Name? ref Path;``
   * - ``during after``
     - ``during after { ... }``
     - ``during after Name { ... }``
     - ``during after abstract Name;``
     - ``during after abstract Name? /* doc */``
     - ``during after Name? ref Path;``
   * - ``exit``
     - ``exit { ... }``
     - ``exit Name { ... }``
     - ``exit abstract Name;``
     - ``exit abstract Name? /* doc */``
     - ``exit Name? ref Path;``

``ref`` 指向 named lifecycle action path，不指向 state 或 event。Doc-comment abstract forms 使用 multiline comment 作为 documentation metadata。

.. _dsl-aspect-forms-zh:

Aspect 形式
-----------------

Aspect actions 使用 ``>> during before`` 或 ``>> during after``。它们支持和 lifecycle ``during before/after`` 相同的 concrete、named、abstract、doc-comment abstract 与 ref families。

.. list-table:: Aspect facts
   :header-rows: 1

   * - Form
     - Example shape
     - Boundary
   * - Concrete aspect
     - ``>> during before { ... }``
     - 在 descendant leaf-state active cycles 中运行。
   * - Named aspect
     - ``>> during after Trace { ... }``
     - 为 generated hooks 提供 stable name。
   * - Abstract aspect
     - ``>> during before abstract Trace;``
     - Generated code 调用 user-provided behavior。
   * - Ref aspect
     - ``>> during after ref Path;``
     - 复用 named action。
   * - Combo pseudo relay
     - N/A
     - Aspect actions 不在 combo pseudo relay chains 内执行。

.. _dsl-import-forms-zh:

Import 形式
-----------------

.. list-table:: Import syntax facts
   :header-rows: 1

   * - Form
     - Syntax
     - Notes
   * - Basic import
     - ``import "file.fcstm" as Alias;``
     - 把 imported root 加为 child ``Alias``。
   * - Named import
     - ``import "file.fcstm" as Alias named "Label";``
     - 添加 display metadata。
   * - Import block
     - ``import "file.fcstm" as Alias { ... }``
     - 包含 mapping statements。
   * - Def fallback selector
     - ``def * -> target;``
     - Fallback variable mapping。
   * - Def set selector
     - ``def {a, b} -> target;``
     - 映射一组 variables。
   * - Def pattern selector
     - ``def sensor_* -> sensor_$0;``
     - Pattern selector 是 compact 且 whitespace-sensitive。
   * - Def exact selector
     - ``def value -> renamed;``
     - 映射一个 variable。
   * - Target template
     - ``ID``、compact template 或 ``*``
     - Compact templates 可使用 ``$0`` 或 ``${0}`` placeholders。
   * - Event mapping
     - ``event Source.Path -> Target.Path;``
     - 可带 ``named "Label"``。
   * - Directory entry
     - ``import "./dir/main.fcstm" as Subsystem;``
     - 使用显式文件；不支持 bare directory import。

File resolution、recursive loading、conflict detection、mapping precedence 和 model assembly 在 parsing 后的 Python import/model code 中实现。

.. _dsl-diagnostics-risk-zh:

Diagnostics 与 target-risk wording
-----------------------------------------

Diagnostics 来自 syntax parsing、model validation、inspect analyzers 和 optional verification phases。用户可见 DSL docs 必须保留每个 diagnostic 的 target scope。

.. list-table:: Diagnostics wording facts
   :header-rows: 1

   * - Area
     - Codes / source
     - Wording rule
   * - Combo expansion
     - ``W_COMBO_*``、``I_COMBO_PSEUDO_NAME_EXTENDED``、``E_COMBO_PSEUDO_NAME_COLLISION``
     - 解释 pseudo relay purity 和 name-extension behavior，不暗示 aspect 在 relays 内运行。
   * - Pseudo state shape
     - ``E_PSEUDO_NOT_LEAF``
     - Parser shape 不等于 model validity。
   * - Numeric literal / operation risk
     - ``W_NUMERIC_*`` and numeric analyzer
     - 除非其他 target 有自己的 evidence，否则描述为 ``c``、``c_poll``、``cpp``、``cpp_poll`` 的 C/C++ deployment-profile risk。
   * - Python generated runtime
     - 不从 C/C++ warnings 自动继承
     - 除非 Python-specific diagnostic 明确说明，否则不要声称 Python generated code 有同样 fixed-width 或 undefined-behavior risk。

Code-level wording 请看 :doc:`../../reference/diagnostics_codes/index_zh`。

.. _dsl-fact-check-notes-zh:

事实核对说明
--------------

* Grammar facts 来自 ``GrammarParser.g4`` 和 ``GrammarLexer.g4``。
* AST shape 与 export details 来自 ``pyfcstm/dsl/node.py`` 和 ``pyfcstm/dsl/listener.py``。
* Import assembly facts 来自 ``pyfcstm/model/imports.py``。
* Target-risk diagnostics 来自 ``pyfcstm/diagnostics/codes.yaml`` 和 ``pyfcstm/diagnostics/analyzers/``。
* LLM-facing syntax guidance 在 ``pyfcstm/llm/fcstm_grammar_guide.md`` 中。本页不修改该 packaged guide。
