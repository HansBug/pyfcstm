:orphan:

BMC 求解、见证与回放边界
========================

有界模型检查（BMC）把一个有限执行边界转换为 Z3 查询。但求解器结果只是三类不同主张中的第一类：

* 求解说明有界目标是否存在模型；
* 解码把 SAT 模型投影成公开的宏步轨迹；
* 回放检查这些投影出来的观测是否与
  :class:`~pyfcstm.simulate.runtime.SimulationRuntime` 一致。

必须把这三类主张分开。SAT 可以给出有用见证，但不能证明所选边界之外的性质。回放成功可以暴露 SMT
编码与运行时在这条轨迹上的一致性，但不能证明任一实现对所有可能轨迹都完备。


这条主张阶梯只能单向使用：

.. list-table:: 求解 / 解码 / 回放主张阶梯
   :header-rows: 1
   :widths: 14 24 30 32

   * - 层级
     - 输入
     - 能够作出的主张
     - 不能作出的主张
   * - 求解
     - :math:`C_N`、性质目标和可选尾部观测
     - 有界 SMT 公式为 SAT、UNSAT、unknown 或 timeout。
     - 它不公开轨迹，也不证明运行时一致。
   * - 解码
     - 主求解得到的 SAT 模型
     - 模型可以投影为公开的宏步轨迹。
     - 它不决定轨迹是期望行为还是违反轨迹；极性负责这个解释。
   * - 回放
     - 解码后的公开轨迹
     - 解码观测在这条有限轨迹上与 ``SimulationRuntime`` 一致。
     - 它不证明所有模型都能解码、不证明所有分支编码正确，也不证明性质在 :math:`N` 之外成立。

一个增量求解器，分阶段检查可行性
----------------------------------

令 :math:`D_N` 表示有界域，:math:`I_0` 表示保留的初始化约束，:math:`T_N` 表示宏步转换关系，
:math:`ENV_N` 表示查询环境约束。求解器维护以下累积空间：

.. math::
   :label: bmc-solve-formulas

   K_N = D_N \land T_N,
   \qquad S_{\mathrm{init}} = K_N \land I_0,
   \qquad S_{\mathrm{assume}} = S_{\mathrm{init}} \land ENV_N.

对于编译后的性质目标 :math:`Obj_q`，主查询是 :math:`\Phi_q = S_{\mathrm{assume}} \land Obj_q`。

先解释主查询结果。只有主查询 UNSAT 时，求解器才检查 :math:`S_{\mathrm{assume}}`，并在必要时继续检查
:math:`S_{\mathrm{init}}` 和 :math:`K_N`，从而区分“仅目标 UNSAT”和“场景不可行”。这些检查在同一个增量求解器上
分阶段执行；已有的 SAT 前缀证据可以标记为 ``inferred``，不必重复求解。

对于 ``response`` 性质，令 :math:`\Omega_q` 表示义务越过边界仍未决的观测，可选的尾部查询是
:math:`\Psi_q = S_{\mathrm{assume}} \land \Omega_q`。

只有在 :math:`S_{\mathrm{assume}}` 已知 SAT、``check_incomplete`` 开启且尾部公式非平凡时，才执行该查询。
尾部模型使用 ``incomplete_suffix`` 角色；它不会把不完整的响应提升为性质结论。

:func:`pyfcstm.bmc.witness.solve_bmc_property` 为每次公开求解创建一个增量求解器和一个共享预算。
``timeout_ms=None`` 表示不向 Z3 设置超时。有限的 ``timeout_ms`` 是主查询、可行性查询和适用尾部查询共享的单调总预算；
每次检查只能使用剩余毫秒数。预算耗尽后不再调用后续检查，其证据保持为 ``not_checked``。

Z3 返回 ``unknown`` 后，实现会读取 ``reason_unknown()``：原因恰好为 ``"timeout"`` 时，公开状态是
``timeout``；其他原因保持为 ``unknown``。两种状态都不携带模型。主检查耗时写入 ``elapsed_ms``；尾部检查耗时以
``incomplete_elapsed_ms=...`` 保留。禁用尾部检查也会留下 ``incomplete_check=disabled``，而不会被误写成“已经证明不存在
未完成后缀”。

性质结论必须解释极性
--------------------

SAT 对两类性质具有相反含义。``reach``、``exists_always`` 和 ``cover`` 使用见证极性：SAT 找到了性质要求的行为。
``forbid``、``invariant``、``must_reach`` 和 ``response`` 使用反例极性：SAT 找到了违反轨迹。

用 :math:`p \in \{W,C\}` 表示见证或反例极性，用 :math:`q` 表示性质类别，用
:math:`s` 表示主求解状态，再用 :math:`t` 表示响应尾部求解状态。不完整条件被严格限定：
只有反例极性的 ``response``、主公式 UNSAT、且尾部状态为坏状态时，结果才是不完整。尾部结果既不能削弱
主公式 SAT 时已经找到的 ``response`` 反例，也不能影响其他性质类别。公开的三值性质结论为：

.. math::
   :label: bmc-verdict-map

   \begin{aligned}
   T_{\mathrm{bad}}(t)&\equiv
   t\in\{\mathrm{sat},\mathrm{unknown},\mathrm{timeout},
   \mathrm{unchecked}\},\\[0.4em]
   H(p,q,s,t)&\equiv
   (p=C)\land(q=\mathrm{response})\land(s=\mathrm{unsat})\land
   T_{\mathrm{bad}}(t),\\[0.4em]
   V(p,q,s,t)&=
   \begin{cases}
   \top,
      & (p=W \land s=\mathrm{sat})
        \lor (p=C \land s=\mathrm{unsat} \land \neg H(p,q,s,t)), \\
   \bot,
      & (p=W \land s=\mathrm{unsat})
        \lor (p=C \land s=\mathrm{sat}), \\
   ?, & s \in \{\mathrm{unknown},\mathrm{timeout}\} \lor H(p,q,s,t).
   \end{cases}
   \end{aligned}

这就是 ``BmcSolveResult.property_satisfied`` 背后的实现。稳定的 ``outcome`` 字符串进一步细分同一映射：

.. list-table:: 求解状态到公开结果的映射
   :header-rows: 1

   * - 极性 / 性质
     - 主状态
     - 尾部条件
     - ``outcome``
   * - 见证
     - ``sat``
     - 无关
     - ``witness_found``
   * - 见证
     - ``unsat``
     - 无关
     - ``no_witness``
   * - 反例
     - ``sat``
     - 无关
     - ``property_violated``
   * - 反例
     - ``unsat``
     - 不存在、无关或尾部已证明 UNSAT
     - ``property_satisfied``
   * - 反例 ``response``
     - ``unsat``
     - 尾部坏状态：未检查、SAT、unknown 或 timeout
     - ``incomplete``
   * - 任意极性
     - ``unknown`` / ``timeout``
     - 无关
     - ``unknown`` / ``timeout``

主公式一旦 SAT，``response`` 反例就已经确定；即使尾部观测也 SAT，这条具体违反轨迹仍然有效。这个不对称特例只作用于
主公式 UNSAT：在声称性质满足之前，实现还必须排除完整响应窗口落在第 :math:`N` 帧之后的触发条件。


通用见证与反例
~~~~~~~~~~~~~~~~

见证模式是通用的：它记录主目标的 SAT 模型。对见证极性的性质，这个通用见证就是用户要求寻找的行为；
对反例极性的性质，同一个解码模式记录的是反例，因为 SAT 表示违反目标成立。因此，“反例”描述的是主公式 SAT
结果的解释，而不是另一种轨迹格式。

``response`` 不完整性的尾部 SAT 模型不同。它支持 ``incomplete`` 边界诊断，但不会作为主用户见证进行解码和回放，
因为主目标是 UNSAT。反过来，当主 ``response`` 目标为 SAT 时，解码后的主轨迹仍是确定反例，即使独立尾部观测也可满足。

从模型到公开见证
----------------

原始 Z3 模型包含求解器符号和实现细节，它不是公开见证模式。
:func:`pyfcstm.bmc.witness.decode_bmc_witness` 把模型投影到 :math:`N+1` 个帧观测和 :math:`N` 个宏步观测：

.. math::
   :label: bmc-witness-projection

   \pi(M)=
   \left\langle
     (q_i,\mathbf{x}_i,\iota_i,\tau_i)_{i=0}^{N},
     (c_i,\Delta_i,\Gamma_i,I_i,U_i,A_i)_{i=0}^{N-1}
   \right\rangle.

其中 :math:`q_i` 和 :math:`\mathbf{x}_i` 是公开状态路径和持久变量；:math:`\iota_i` 与 :math:`\tau_i` 标记初始和终止
哨兵。每个宏步记录选中分支 :math:`c_i`、delta/gamma 进度标志、稀疏回放输入 :math:`I_i`、有序事件账目
:math:`U_i`\ （已消费事件与派生的未消费事件），以及抽象调用记录 :math:`A_i`。

这个投影有意保持稀疏。只有当选中分支、显式真值假设或 ``response`` 性质支持回放需要某个真值事件布尔量时，
该事件才进入 ``input_events``。假值假设和其他被读取的事件值可以作为调试数据进入 ``event_reads``，但不会传给
``runtime.cycle()``。分支标签、``gamma`` 和 ``progress`` 仍只属于见证解释信息；``delta`` 同时作为运行时宏步的公开观测，
并在回放时进行比较。

因此解码有严格的调用者边界：它接收编译公式和调用者从 SAT 主求解得到的 ``z3.ModelRef``，不会执行第三次可满足性检查。
非法模型值、分支缺失或多选、内部事件支持不一致都会明确抛出 ``BmcBuildError``；静默制造部分轨迹会让后续回放证据失去意义。

回放一致性及其限度
------------------

回放根据见证的公开初始元数据构造 ``SimulationRuntime``，只把每一步的稀疏输入事件路径传给 ``cycle()``，再记录运行时帧、
事件账目和抽象处理器上下文。令 :math:`W` 为解码轨迹，:math:`R(W)` 为捕获到的运行时轨迹。成功标志是所有公开比较的合取：

.. math::
   :label: bmc-replay-agreement

   \operatorname{ok}(W)
   \iff
   \bigwedge_{i=0}^{N}
      \operatorname{eq}_{F}(W.F_i,R(W).F_i)
   \land
   \bigwedge_{i=0}^{N-1}
      \operatorname{eq}_{S}(W.S_i,R(W).S_i),

其中帧相等覆盖状态、终止标志、持久变量键和值；宏步相等覆盖输入事件、已消费与未消费事件、``delta`` 结果，以及有序抽象调用的
元数据和快照。浮点值使用明确的回放容差，而不是逐位相等。初始哨兵与冷初始化实际产生的运行时状态比较，不会被误当成普通状态路径。

下面的单步转换轨迹展示了各层所有权边界：

.. list-table:: 从 SAT 模型到回放结论
   :header-rows: 1

   * - 阶段
     - 输入
     - 可观察结果
   * - 求解
     - :math:`C_1 \land Q_1`
     - ``sat`` 和一个 Z3 模型
   * - 解码
     - 模型符号 ``F_0_*``、``F_1_*``、``E_0_*``、``C_0_*``
     - 两个帧、选中转换、稀疏输入事件和事件账目
   * - 回放
     - 初始元数据和稀疏输入事件
     - 两个运行时帧和一个捕获的运行时宏步
   * - 比较
     - 解码观测和运行时观测
     - 只有 :eq:`bmc-replay-agreement` 中每项都成立时，``ok=True``

分支标签和求解器专用进度标志有意不属于 :math:`\operatorname{eq}_S`；``delta``、事件消费和抽象调用快照则属于比较范围。
反过来，事件消费和抽象调用快照必须比较，因为只比较最终状态会漏掉具有行为意义的偏差。

反例：回放不是编码器证明
~~~~~~~~~~~~~~~~~~~~~~~~~~

假设解码见证声称第 1 帧 ``x=2``，但运行时到达同一状态时 ``x=1``。回放会返回如下结构化证据：

.. code-block:: text

   ok: false
   path: frames[1].vars.x
   expected: 2
   actual: 1
   message: value mismatch

这否定了该见证上的对齐；仅有相同状态名不能掩盖变量效果错误。反方向的主张更弱：``ok=True`` 只证明这条有限轨迹上
已解码公开观测的一致性。它不证明未选中分支编码正确，不证明所有 SAT 模型都能解码，不证明查询在 :math:`N` 之外成立，
也不排除 BMC 与运行时共享同一个建模错误。

冲突落在哪里，以及为什么答案是互斥的
------------------------------------

场景不可行时，第一个有用的问题不是\ *哪一条子句*\ ，而是\ *哪一部分*\ 。分阶段
求解已经回答了它：kernel、初始化、假设按此顺序进入求解器，所以可满足性在哪一阶段
丢失就标识出哪个族。kernel 本身已不可满足属于 ``kernel_conflict``，它牵涉的是模型
而非查询。kernel 一直成立直到 ``init`` 加入，给出 ``initialization_*`` 族；一直
成立直到 ``assume`` 加入，给出 ``assumptions_*`` 族。

族内三个成员由\ *新子句与什么相冲突*\ 来区分。``*_self_conflict`` 意味着新子句彼此
矛盾，即使别的什么都不在也会失败。``*_domain_conflict`` 意味着它们各自自洽，但合在
一起让某一帧没有合法取值——它们超出了帧域允许的范围。``assumptions_prefix_conflict``
（以及它的初始化对应项）意味着这些子句与帧域也是相容的，只有转换关系排除了它们：
机器无论怎么走都到不了所要求的组合。

这七个取值互斥，是因为每一个都由第一个失败的阶段或子检查决定，而这些检查是有序的。
这也是报告打印一个分类而不是一个集合的原因，也是读者能据此行动的原因：分类点明了
他们应该打开哪个文件。


可靠不等于极小
--------------

求解器自己给出的 unsat core 是\ *可靠的*\ ：把它整个删掉，公式就变得可满足。但它
不是\ *极小的*\ ：它可能包含与冲突毫无关系的子句，因为求解器一旦够用就停下了。拿到
一个仅可靠的核，读者只能猜哪些成员真的相关。

最小化通过逐个检验成员来消除这种猜测：删掉它、重新求解，只有剩余部分仍不可满足时
才保留这次删除。对每个成员都经受住这一检验的核就是子集极小（subset minimal）的
——每个成员都承重，因此每个成员都值得读。发布的断言如实区分三种状态：没有成员被
检验时为 ``raw``，预算中途耗尽时为 ``partial_minimized``，全部检验完成时为
``subset_minimal``。

这一点之所以重要，是因为极小性正是下一阶段得以可能的前提。证明的一步必须说明它
重述了哪个冲突核成员，而仅可靠的核里有些成员什么也没重述。


证明被信任的是什么
------------------

发布出来的证明，是"每一步都被检查过"这一断言。有意思的设计问题是\ *由谁检查*\ ，
因为与构造者共享代码的检查器是按构造必然同意的，什么也证明不了。

四种方法分担这件事。``input`` 节点用 ``core_binding``：归一化事实被从零重新编码，
并要求求解器同时驳倒 ``group => fact`` 与 ``fact => group``。两个方向都是必需的。
只查一个方向会允许一个仅仅\ *被冲突核成员蕴含*\ 的事实，那是摘要而非重述——而摘要
恰好可能丢掉读者需要的那个细节。任一方向返回可满足、unknown 或超时，该证明就到不了
``complete``。

``derived`` 与根节点用 ``rule_checker``：一个独立检查器拿前提与所声称的结论，不调用
产出它的代码而重新推导一遍。它比较整个结论映射而不是挑选字段，并拒绝携带它不认识的
字段的结论，因此悄悄添加信息的构造者无法蒙混过关。

``solver_entailment`` 用于改由求解器判定的 ``derived`` 与根步骤。``case_condition_entailment``
就是其中一条：冲突核成员是否确立了某个 case 的条件，问的是这些成员的约束，而检查器只看得到
已发布的事实，那里面并没有这个信息。节点会点名蕴含该条件的成员，且这些成员被断言为已发布
冲突核的子集——一个步骤若依赖核外的东西，就会破坏证明对自己叶子所声称的极小性。

一个按 case 各持一条要求的组是合取式，任何单条事实都蕴含不了它的全部——因此重述
其中某一条要求的 ``input`` 节点改用 ``core_binding_unit``。要驳倒的仍是同样两个方向，
只是对着那一条要求而非整组，节点再通过 ``unit_index`` 与 ``unit_count`` 指明是哪一条。
这一对数字的用处是让读者看见覆盖比例：「12 条要求中的第 5 条」说出了「转移关系」说不
出的东西。若一条事实同时等价于两条要求，它谁也没有指认，此时绑定被拒绝而不是择一——
一个读者不能依赖的索引比没有索引更糟。

会这样分解的组只有步关系，因此冲突核落在它某个 case 上的查询，就是这一对数字被发布的
地方：这样的 ``input`` 节点携带 ``core_binding_unit``\ ，同一冲突核的其他成员携带
``core_binding``\ ，节点由此点明该 case 重述的是这个关系的哪一条要求。这一对数字送达的是
JSON 结果的消费方；终端报告携带的是每个节点的句子，而不是它是如何被核验的。这一对数字曾有一段
时间是已定义而从不发布的，原因是归属只停在绑定检查里、从未走到节点上——这个缺口从外面
看，和「没有查询能产出这个方法」一模一样。

所以边界是：\ **读者可以相信每一句话都从旁边点名的那些冲突核成员推出，但不能相信
编码忠实地建模了他们的意图。** 证明谈论的是编码之后的约束。这与重放为见证划出的
边界是同一条，理由也相同。


为什么有些冲突没有证明
----------------------

``proof`` 深度会降级而不是伪造，其原因是结构性的而非偶然的。

一个 ``input`` 节点代表一个冲突核成员，而冲突核是\ *作者写下的*\ 子句加上生成的
支撑组。关于中间帧的事实——比如某变量走两步之后持有什么——并没有写在任何地方；它是
从转换规则\ *派生*\ 出来的。因此，只有在跨步累加之后才显现的冲突，其关键事实没有
可归属的冲突核成员，闭包也就无处起步。这类查询把 ``achieved_mode`` 报告为
``formal``。

对这些冲突来说，``formal`` 解释并不是次一等的答案。它给出分类、子集极小的冲突核
以及每个源位置，而它的叙述能点名初始状态与冲突的具体取值——那恰恰是缺少中间事实的
证明会丢掉的东西。追查跨步冲突的读者今天从 ``formal`` 得到的服务更好，而报告会在
``reason`` 行里说明这一点，不让人猜。

有三条规则曾因同一个原因不可达，这里保留那段说明，因为它描述的形状仍是读者会遇到的。
一个 case 发布它所做的赋值，但该赋值只在\ **该 case 适用时**\ 成立，而求值规则拒绝
携带条件的表达式——这是对的：「在条件 C 下 x 增加 1」加上「x 等于 0」推不出「x 等于 1」，
除非 C 被立起来。当时没有任何东西立它，于是 ``transition_assignment`` 拿不到可用的前提，
``equality_substitution`` 与 ``arithmetic_evaluation`` 又隔着它产出的
``arithmetic_expression`` 再等一层。

``case_condition_entailment`` 把它立起来。条件是从冲突核\ **成员自身**\ 证出的，
而不是从它们已发布的事实：把机器置于该 case 所指状态的成员里，包含那条把它送到那里的
步关系，而步关系发布为 ``structural_constraint``，内容读者看不见。所以这一步由求解器完成，
节点点名它用到的成员，并记 ``solver_entailment`` 而非 ``rule_checker``——因为任何只看前提
的谓词都判不了它。从冲突核成员到证明事实的翻译仍只发出七种 kind，其中并没有
``arithmetic_expression``，所以那个事实依旧只有一个产出者、链条起点也依旧在原处，
变的只是第一环不再带条件。十二条规则里零条从不触发，而上面几段描述的仍然是那些没有证明的
冲突：那些冲突缺的是\ **事实**\ ——没有冲突核成员能陈述它们，这与本规则填上的短缺不是
同一件事。

第二条边界更窄。事件假设发布为 ``structural_constraint`` 事实：冲突核成员是已知且
已定位的，但它的内容没有被读出，所以没有规则适用于它。叙述随之报告
``structural_only``，只说这些约束无法同时成立——这是真的，但对想知道\ *是哪两个*\ 事件
要求撞在一起的读者来说过于单薄。两条边界都是契约中所记录决策的后果，而不是检查器的
缺陷，并且两者都通过 ``achieved_mode`` 与 ``derivation_status`` 对调用方可见，不是
静默的。


为什么有界结构会增长
--------------------

令 :math:`V` 为持久变量数量，:math:`E` 为事件数量，:math:`K_i` 为宏步 :math:`i` 分配的分支选择变量数量。
``BmcTraceSymbols.allocate`` 为每帧创建一个状态符号和 :math:`V` 个变量符号，为每步创建 :math:`E` 个输入事件符号以及
delta、gamma 两个符号，并为每个步/分支对创建一个选择变量。公开轨迹符号的精确数量为：

.. math::
   :label: bmc-symbol-growth

   |X_N|
   = (N+1)(V+1) + N(E+2) + \sum_{i=0}^{N-1}K_i
   = N\!\left(V+E+3+\bar K\right)+(V+1),
   \qquad
   \bar K=\frac{1}{N}\sum_{i=0}^{N-1}K_i.

第二个等号使用 :math:`N>0`；第一个等号对所有允许的边界都是精确计数。当展开后的分支集合固定时，符号数量随边界线性增长，
但求解成本不一定线性增长：关系还会重复守卫、更新、定义性
条件、调用快照和分支蕴含式，求解器还要搜索它们的组合。宏步展开可能在边界展开前就增大 :math:`K_i`，所以降低
:math:`N` 无法修复单个宏步内部的分支爆炸。:eq:`bmc-symbol-growth` 只计算已分配轨迹变量，不计算 Z3 表达式节点或
求解器搜索状态。

可运行轨迹与公式台账
--------------------

五个公式可以用一个最小模型和两个查询审计。模型有意保持很小，让求解边界清晰可见：

.. code-block:: fcstm

   state Root;

响应查询会执行 :eq:`bmc-solve-formulas` 所述的分阶段主查询和尾部查询：

.. code-block:: text

   check response <= 1: trigger true -> within 2 false;

它的轨迹摘要是 ``main=unsat``、``tail=sat``、``outcome=incomplete``。主公式没有 SAT 模型，因此不能给出有界性质结论；但 SAT 尾部仍会以 ``incomplete_suffix`` 角色解码并回放可执行的有限前缀。这个角色不能被误读为完整见证或反例。
第二个查询执行正向见证路径：

.. code-block:: text

   check reach <= 1: active("Root");

它产生 ``main=sat``、``outcome=witness_found``、两个解码帧、一个解码宏步和 ``replay.ok=true``。对于同一个边界为 1 的查询，
:math:`V=0`、:math:`E=0`，唯一宏步有 :math:`K_0=2` 个选择变量。由 :eq:`bmc-symbol-growth` 可得
:math:`|X_1|=2+2+2=6`：两个帧状态符号、delta 与 gamma，以及两个分支选择变量。

下列条目是本页带标签公式的前向审计图。字面 LaTeX 就是每个带标签公式目标处的块；中英文文件使用完全相同的块。

下面每个方程都点名它的实现、它的测试，以及能行使它的查询轨迹。

:eq:`bmc-solve-formulas` —— 可行性分阶段检查与响应尾部
    ``compile_bmc_property``、``solve_bmc_property`` 与 ``_SolveBudget``。由
    ``test_compile_response_strict_successor_and_incomplete_suffix`` 与
    ``test_solver_unknown_and_timeout_paths_are_structured`` 覆盖。上文的
    ``response`` 查询在主目标上给出 UNSAT，在尾部给出 SAT。

:eq:`bmc-verdict-map` —— 极性感知的三值判定
    ``BmcSolveResult.property_satisfied`` 与 ``outcome``。``response`` 查询给出
    ``incomplete``，``reach`` 查询给出 ``witness_found``。由以下测试覆盖：

    - ``test_solve_result_public_verdict_truth_table``
    - ``test_response_violation_verdict_stays_decisive_with_suffix``

:eq:`bmc-witness-projection` —— 从 SAT 模型到稀疏的公开轨迹
    ``decode_bmc_witness``、``_decode_step`` 与 ``_event_inputs_for_step``。由
    ``test/bmc/test_witness.py`` 中的见证解码与事件策略测试覆盖。``reach``
    查询解码出两帧一步。

:eq:`bmc-replay-agreement` —— 公开观测相等
    ``replay_bmc_witness``、``_compare_frame`` 与 ``_compare_step``。``reach``
    查询报告 ``replay.ok=true``，而篡改过 ``x`` 的轨迹会失败。覆盖它的测试是：

    - ``test_replay_reports_structured_var_mismatch``
    - ``test_bmc_witness_replay_matches_full_semantic_fixture_trace``

:eq:`bmc-symbol-growth` —— 精确的轨迹符号分配数
    ``BmcTraceSymbols.allocate``。由 ``test/bmc/test_domain.py`` 与
    ``test/bmc/test_relation_public_api.py`` 中的形状断言覆盖。``reach`` 查询有
    :math:`N=1,V=0,E=0,K_0=2`，因此共六个符号。

语义夹具回放测试组尤其重要：它对登记为必须通过的场景检查完整运行时轨迹，而不只是检查见证对象能否序列化。
篡改测试提供反方向证据：改变一个公开观测后，必须得到路径精确的不匹配项。


解释在形式上断言了什么
----------------------

下面四条陈述是可选解释对它自己的输出所作的断言。它们与上文的求解方程是分开的，因为
它们约束的是一份\ *报告*\ 而不是一次搜索：每一条都是发布对象要么具备、要么因缺失而
被拒绝发布的性质。

设 :math:`C = \{c_1, \dots, c_n\}` 为发布出来的源组冲突核，每个 :math:`c_i` 是一条
作者写下的子句或一个生成支撑组的编码，并以 :math:`\Phi` 表示合取。

可靠性是最弱的断言，每个冲突核都作出它。冲突核可靠，是指仅凭它的成员就已经不容许
任何赋值：

.. math::
   :label: bmc-core-soundness

   \mathrm{UNSAT}\bigl(\Phi(C)\bigr)

这正是求解器自己给出的核所提供的，它并没有说明每个成员是否都必需。子集极小性是更强
的断言，只有在每个成员都经过"删掉它再重新求解"的检验之后才作出：

.. math::
   :label: bmc-core-subset-minimality

   \forall c \in C:\ \mathrm{SAT}\bigl(\Phi(C \setminus \{c\})\bigr)

满足 :eq:`bmc-core-subset-minimality` 的冲突核报告 ``subset_minimal``，且
``subset_minimality`` 为 ``proven``。只满足 :eq:`bmc-core-soundness` 的报告
``raw``，检验被中途截断的报告 ``partial_minimized``。这个区分正是告诉读者"列出的
每一行是否都值得改"的依据。

在 ``proof`` 深度，每个 ``input`` 节点把一个冲突核成员重述为归一化事实 :math:`f`。
重述比双向的任一单向蕴含都强，而两个方向都是必需的：

.. math::
   :label: bmc-proof-input-binding

   \mathrm{UNSAT}\bigl(\Phi(c) \wedge \neg f\bigr)
   \ \wedge\
   \mathrm{UNSAT}\bigl(f \wedge \neg \Phi(c)\bigr)

左侧合取项说的是成员强制该事实；右侧说的是该事实强制该成员。只检查左侧会容许一个
比 :math:`c` 更弱的 :math:`f`——那是摘要，而摘要可能已经丢掉了读者需要的细节。这些
检查中任何一个返回可满足、unknown 或超时，都会让该证明到不了 ``complete``。

最后，输入与冲突核之间是双射，从而每个成员恰好被读一次，且没有节点替两个成员说话：

.. math::
   :label: bmc-proof-input-bijection

   \bigl|\{\,v : \mathrm{kind}(v) = \texttt{input}\,\}\bigr| = |C|
   \ \wedge\
   \forall v:\ \bigl|\mathrm{items}(v)\bigr| = 1

缺失、多余或重复的输入都违反 :eq:`bmc-proof-input-bijection`，会被拒绝而不是发布
——包括两个不同成员陈述同一事实的情形，那种情形无处安放：合并它们会让一个节点带上
两份归属，丢掉一个又会让某个成员没人读。

下面每条断言都点名它的实现、它的测试，以及一个能产出它的查询。四条共用同一个两行
查询 ``assume at 1: var("x") == 1; assume at 1: var("x") == 2;``，所以跑一次就能
重现整份台账。

:eq:`bmc-core-soundness` —— 仅冲突核本身不可满足
    由 ``pyfcstm/bmc/infeasibility.py`` 中的 ``extract_source_core`` 构造；由
    ``test/bmc/test_infeasibility.py`` 覆盖。该查询在场景 UNSAT 的同时报告
    ``Core size: 2``。

:eq:`bmc-core-subset-minimality` —— 每个成员都承重
    由同一函数中的最小化循环构造；由 ``test/bmc/test_explanation.py`` 中的
    ``test_reduction_and_minimality_stay_coupled`` 覆盖。该查询报告
    ``Reduction: subset_minimal`` 与 ``Subset minimality: proven``。

:eq:`bmc-proof-input-binding` —— 两个方向都被驳倒
    由 ``pyfcstm/bmc/infeasibility.py`` 中的 ``check_core_bindings`` 检查；由
    ``test/bmc/test_proof_wiring.py`` 覆盖。该查询发布两个输入，
    ``verification_method`` 均为 ``core_binding``。

:eq:`bmc-proof-input-bijection` —— 一个成员一个节点
    由 ``pyfcstm/bmc/proof.py`` 中的 ``build_domain_proof`` 强制。该查询为两成员
    冲突核发布两个 ``input`` 节点，各自的 ``item_ids`` 只有一项。覆盖它的两个测试
    各占一行，以免长标识符在窄栏里被裁断：

    - ``test_an_input_node_restates_one_member_and_says_so``
    - ``test_two_members_stating_one_fact_are_refused_rather_than_merged``

这份台账值得对照上文的边界来读：这四条断言谈论的都是编码之后的约束。没有一条说编码
符合作者的本意，这也正是信任边界要单独陈述的原因。
