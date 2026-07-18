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

它的轨迹摘要是 ``main=unsat``、``tail=sat``、``outcome=incomplete``。主公式没有 SAT 模型，所以不存在解码见证或回放。
第二个查询执行正向见证路径：

.. code-block:: text

   check reach <= 1: active("Root");

它产生 ``main=sat``、``outcome=witness_found``、两个解码帧、一个解码宏步和 ``replay.ok=true``。对于同一个边界为 1 的查询，
:math:`V=0`、:math:`E=0`，唯一宏步有 :math:`K_0=2` 个选择变量。由 :eq:`bmc-symbol-growth` 可得
:math:`|X_1|=2+2+2=6`：两个帧状态符号、delta 与 gamma，以及两个分支选择变量。

下表是本页带标签公式的前向审计图。字面 LaTeX 就是每个带标签公式目标处的块；中英文文件使用完全相同的块。

.. list-table:: 求解公式台账
   :header-rows: 1
   :widths: 21 27 28 24

   * - 公式与主张
     - 实现锚点
     - 测试锚点
     - 可运行查询与轨迹
   * - :eq:`bmc-solve-formulas`：可行性分阶段检查与响应尾部
     - ``compile_bmc_property``；``solve_bmc_property``；``_SolveBudget``
     - ``test_compile_response_strict_successor_and_incomplete_suffix``；
       ``test_solver_unknown_and_timeout_paths_are_structured``
     - 上面的 ``response`` 查询：主公式 UNSAT、尾部 SAT
   * - :eq:`bmc-verdict-map`：解释极性的三值结论
     - ``BmcSolveResult.property_satisfied`` 与 ``outcome``
     - ``test_solve_result_public_verdict_truth_table``；
       ``test_response_violation_verdict_stays_decisive_with_suffix``
     - ``response`` 得到 ``incomplete``；``reach`` 得到 ``witness_found``
   * - :eq:`bmc-witness-projection`：SAT 模型到稀疏公开轨迹
     - ``decode_bmc_witness``；``_decode_step``；
       ``_event_inputs_for_step``
     - ``test/bmc/test_witness.py`` 中的见证解码器与事件策略测试
     - ``reach`` 查询：两个帧和一个宏步
   * - :eq:`bmc-replay-agreement`：公开观测相等
     - ``replay_bmc_witness``；``_compare_frame``；``_compare_step``
     - ``test_replay_reports_structured_var_mismatch``；
       ``test_bmc_witness_replay_matches_full_semantic_fixture_trace``
     - ``reach`` 查询：``replay.ok=true``；篡改 ``x`` 的轨迹失败
   * - :eq:`bmc-symbol-growth`：已分配轨迹符号的精确计数
     - ``BmcTraceSymbols.allocate``
     - ``test/bmc/test_domain.py`` 与 ``test/bmc/test_relation_public_api.py`` 中的
       形状断言
     - ``reach`` 查询：:math:`N=1,V=0,E=0,K_0=2`，因此共有六个符号

语义夹具回放测试组尤其重要：它对登记为必须通过的场景检查完整运行时轨迹，而不只是检查见证对象能否序列化。
篡改测试提供反方向证据：改变一个公开观测后，必须得到路径精确的不匹配项。
