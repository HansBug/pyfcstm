.. _sec-explanations-bmc-properties-zh:

性质目标、定义性与边界
======================

有界性质并不是简单地在轨迹后面合取一个布尔条件。pyfcstm 会先把每个谓词下沉为一个值以及该值在运行时有定义所需的侧条件，再按性质类别选择具有对应可满足性极性（polarity）的目标。本页解释这一构造，以及 ``response`` 窗口越过边界时使用的独立观察公式。

实现事实来自 ``pyfcstm/bmc/properties.py`` 和 ``pyfcstm/bmc/relation.py`` 中的表达式下沉。主要可执行规约是 ``test/bmc/test_properties.py``；调用过滤器的防御边界还由 ``test/bmc/test_call_predicate_guards.py`` 覆盖。本页解释当前有界语义，不声称 UNSAT 能证明无界时序性质。


同一个门锁例子看七类性质
------------------------

先用一个有界门锁故事区分用户意图和求解极性。假设轨迹从 ``Door.Locked`` 开始，事件
``Door.Unlock`` 可以在下一个宏步骤把门锁移动到 ``Door.Unlocked``，公开转换分支为
``Door.Locked::transition::Door.Unlocked::0``。下表只给短性质形状，不展开完整模型。

.. list-table:: 七类性质速览
   :header-rows: 1
   :widths: 13 26 16 24 21

   * - 类别
     - 主目标中的有限量词
     - SAT 极性
     - 用户意图
     - 门锁形状
   * - ``reach``
     - 存在轨迹，且存在满足 :math:`G_i(p)` 的帧
     - 见证
     - 说明期望状态能够出现。
     - ``reach active("Door.Unlocked")``
   * - ``forbid``
     - 存在轨迹，且存在被禁止或未定义的帧
     - 反例
     - 排除访问被禁止状态的轨迹。
     - ``forbid active("Door.Unlocked")``
   * - ``invariant``
     - 存在轨迹，且存在为假或未定义的帧
     - 反例
     - 要求每个可见帧都满足条件。
     - ``invariant active("Door.Locked")``
   * - ``must_reach``
     - 存在一条完整轨迹，其中没有满足条件的帧
     - 反例
     - 要求每条有界轨迹都到达目标。
     - ``must_reach active("Door.Unlocked")``
   * - ``exists_always``
     - 存在一条轨迹，其中每一帧都满足条件
     - 见证
     - 说明存在一种行为能全程保持条件为真。
     - ``exists_always active("Door.Locked")``
   * - ``cover``
     - 存在轨迹，且存在为真的公开分支选择变量
     - 见证
     - 说明具名转换或回退分支能够被选中。
     - ``cover case("Door.Locked::transition::Door.Unlocked::0")``
   * - ``response``
     - 存在一个触发步，其完整窗口内没有响应
     - 反例
     - 要求每次触发后在边界内出现未来响应。
     - ``response trigger event("Door.Unlock", current) -> within 1 active("Door.Unlocked")``

表中使用性质片段以保持例子简短。完整 ``.fbmcq`` 查询会把每个片段放在 ``check <kind> <= N:``
和所需初始子句之后，例如 ``init state("Door.Locked");``。关键点是极性：解码出的 SAT 模型对
``reach``、``exists_always`` 与 ``cover`` 是期望见证，对 ``forbid``、``invariant``、``must_reach``
与 ``response`` 则是违反轨迹。

符号与三条贯穿轨迹
------------------

令 :math:`F_0,\ldots,F_N` 为满足 :math:`Core_N` 的轨迹帧，:math:`E_i` 为从 :math:`F_i` 到 :math:`F_{i+1}` 的宏步骤事件输入。对帧谓词 :math:`p`，:math:`P_i(p)` 是下沉后的布尔值，:math:`D_i(p)` 是它的运行时定义性（runtime definedness）。``response`` 性质使用触发条件 :math:`t`、响应条件 :math:`r` 和正窗口 :math:`W`。

多数例子使用这个双状态模型：

.. code-block:: text

   state Root {
       event Go;
       state A;
       state B;
       [*] -> A;
       A -> B : Go;
   }

在 ``init state("Root.A")``、边界 1 且步骤 0 的 ``Go`` 为真时，关键轨迹是 :math:`F_0=\texttt{Root.A}, E_0=\texttt{Go}, F_1=\texttt{Root.B}`。关闭 ``Go`` 后，两帧都停留在 ``Root.A``。定义性反例使用 ``x = 1``、``y = 0``：求值 ``x / y > 0`` 时，除法要求 :math:`y\ne0`，所以它的值本身不再有意义。

对调用计数，测试模型在状态 ``during`` 中依次调用 ``Before``、递增 ``x``、调用 ``After``。一个被选择的宏步骤因此包含快照 ``x == 0`` 的 ``Before`` 记录和快照 ``x == 1`` 的 ``After`` 记录。过滤器检查调用时快照，而不是步骤后的帧。

谓词定义性
----------

:eq:`bmc-predicate-defined` 合取下沉 :math:`p` 时产生的全部侧条件。空合取为真，因此 ``active("Root.A")`` 等原子无需虚构额外失败条件就有定义。

.. math::
   :label: bmc-predicate-defined

   D_i(p) \;=\; \bigwedge_{d \in \operatorname{Def}_i(p)} d,
   \qquad
   \bigwedge \varnothing \;=\; \top.

``_PredicateFormula.definedness`` 保存 :eq:`bmc-predicate-defined`，``_lower_predicate`` 则从 ``definedness_constraints`` 构造它。当 ``y == 0`` 时，查询 ``check reach <= 1: x / y > 0;`` 的两个可见帧都有 :math:`D_i(p)=\bot`；查询为 UNSAT，不会从任意的除法值中获得见证。改为 ``y == 1`` 后，同一轨迹有定义并正常计算比较结果。``test_compile_liveness_definedness_failures_are_not_witnesses`` 冻结了该行为。

:eq:`bmc-predicate-good` 定义唯一能够支持见证的谓词状态：表达式必须既有定义又为真。

.. math::
   :label: bmc-predicate-good

   G_i(p) \;=\; D_i(p) \land P_i(p).

对 ``active("Root.A")``，事件轨迹上的 :math:`G_0` 为真、:math:`G_1` 为假。对 ``y == 0`` 时的 ``x / y > 0``，即使求解器表示给除法项分配了某个值，:math:`G_i` 仍为假。``_PredicateFormula.good`` 实现 :eq:`bmc-predicate-good`；可达、必达、存在始终与响应测试覆盖了正反两侧。

安全风格的反例搜索需要两种不同的坏状态。:eq:`bmc-predicate-bad-true` 在被禁止的谓词未定义或为真时成立。

.. math::
   :label: bmc-predicate-bad-true

   B_i^{\top}(p) \;=\; \neg D_i(p) \lor P_i(p).

因此 ``check forbid <= 1: active("Root.A");`` 在 :math:`F_0` 为 SAT，而同一轨迹上的 ``check forbid <= 1: terminated();`` 为 UNSAT。把谓词换成 ``x / y > 0`` 并令 ``y == 0`` 也会形成反例：未定义不能证明被禁止条件始终未出现。代码和测试锚点是 ``_PredicateFormula.bad_true`` 与 ``test_compile_definedness_failures_are_safety_counterexamples``。

:eq:`bmc-predicate-bad-false` 在必须保持的不变量未定义或为假时成立。

.. math::
   :label: bmc-predicate-bad-false

   B_i^{\bot}(p) \;=\; \neg D_i(p) \lor \neg P_i(p).

事件轨迹上，``check invariant <= 1: active("Root.A");`` 在 :math:`F_1` 找到反例；``active("Root")`` 没有这种帧。``y == 0`` 时的 ``x / y > 0`` 同样是反例，而不是空洞成功。这对应 ``_PredicateFormula.bad_false``，由 ``test_compile_forbid_and_invariant_are_counterexample_objectives`` 和上面的定义性回归共同测试。

六种帧与分支目标
------------------

目标 :math:`\Phi_q` 是主求解检查中与 :math:`Core_N` 合取的部分。对 ``reach``、``exists_always`` 和 ``cover``，SAT 表示期望的见证；对 ``forbid``、``invariant``、``must_reach`` 和 ``response``，SAT 表示反例。UNSAT 会反转这种解释，但结论只针对当前有限边界和假设。

:eq:`bmc-objective-reach` 在全部 :math:`N+1` 个帧（包括 :math:`F_0` 和 :math:`F_N`）中搜索一个有定义且为真的可达谓词。

.. math::
   :label: bmc-objective-reach

   \Phi_{\mathrm{reach}}(p) \;=\;
   \bigvee_{i=0}^{N} G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{witness}].

事件轨迹上，``check reach <= 1: active("Root.B");`` 因 :math:`F_1` 而 SAT；``active("Root.A")`` 已因 :math:`F_0` 而 SAT。``terminated()`` 则是“每个可达查询都能找到东西”这一预期的 UNSAT 反例。实现/测试对是 ``_compile_reach`` 与 ``test_compile_reach_witness_covers_frame_zero_and_final_frame``。

:eq:`bmc-objective-forbid` 检查是否存在未定义或使禁止谓词为真的帧。

.. math::
   :label: bmc-objective-forbid

   \Phi_{\mathrm{forbid}}(p) \;=\;
   \bigvee_{i=0}^{N} B_i^{\top}(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

``active("Root.A")`` 在 :math:`F_0` 产生 SAT 反例；``terminated()`` 不产生反例。除零轨迹说明 :eq:`bmc-objective-forbid` 为什么使用 :math:`B^{\top}`，而不是直接使用 :math:`P_i`。参见 ``_compile_forbid`` 与 ``test_compile_forbid_and_invariant_are_counterexample_objectives``。

:eq:`bmc-objective-invariant` 检查是否存在未定义或使不变量为假的帧。

.. math::
   :label: bmc-objective-invariant

   \Phi_{\mathrm{invariant}}(p) \;=\;
   \bigvee_{i=0}^{N} B_i^{\bot}(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

事件轨迹上，``active("Root.A")`` 在 :math:`F_1` 产生 SAT 反例，而 ``active("Root")`` 使目标 UNSAT。未定义的数值不变量也为 SAT。这些情况直接映射到 ``_compile_invariant`` 和 ``test_compile_forbid_and_invariant_are_counterexample_objectives``。

:eq:`bmc-objective-must-reach` 搜索一条完整的有界轨迹，使其中没有任何帧满足“有定义且为真”。尽管“必须到达”的自然语言表述是正向的，它仍是反例目标。

.. math::
   :label: bmc-objective-must-reach

   \Phi_{\mathrm{must\_reach}}(p) \;=\;
   \bigwedge_{i=0}^{N} \neg G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

当 ``Go`` 为假时，``check must_reach <= 1: active("Root.B");`` 为 SAT，轨迹始终停在 ``Root.A``。``active("Root.A")`` 使目标 UNSAT，因为 :math:`F_0` 已经到达它。除零也会阻止有效匹配，因此能支持未到达反例。参见 ``_compile_must_reach`` 和 ``test_compile_must_reach_and_exists_always_polarities``。

:eq:`bmc-objective-exists-always` 搜索一条有界轨迹，使谓词在每个帧都既有定义又为真。这个存在路径目标不是全称不变量证明。

.. math::
   :label: bmc-objective-exists-always

   \Phi_{\mathrm{exists\_always}}(p) \;=\;
   \bigwedge_{i=0}^{N} G_i(p)
   \qquad [\mathrm{polarity}=\mathrm{witness}].

事件轨迹上的 ``active("Root")`` 为 SAT。若强制 ``Go`` 为真，``active("Root.A")`` 因 :math:`F_1` 为 ``Root.B`` 而 UNSAT；未定义谓词同样不能成为见证。代码/测试锚点是 ``_compile_exists_always`` 与 ``test_compile_must_reach_and_exists_always_polarities``。

调用与覆盖目标
-----------------

调用谓词（call predicate）是步骤观察。对锚点 :math:`a`，过滤条件 :math:`f` 选择界内步骤 :math:`S_f(a)`。:math:`K_i` 是步骤 :math:`i` 的分支关系集合，:math:`R_{i,k}` 是某个分支的抽象调用记录序列，:math:`C_{i,k}` 是其选择变量，:math:`M_f(r)` 是动作、阶段、角色、状态、活动叶状态、具名引用与调用快照 ``where`` 条件的合取。

.. math::
   :label: bmc-call-count

   \operatorname{call\_count}_a(f)
   \;=\;
   \sum_{i \in S_f(a)}
   \sum_{k \in K_i}
   \sum_{r \in R_{i,k}}
   \operatorname{ite}\!\left(C_{i,k} \land M_f(r),1,0\right),
   \qquad
   \operatorname{called}_a(f)
   \;\Longleftrightarrow\;
   \operatorname{call\_count}_a(f)>0.

``_lower_call_count`` 实现 :eq:`bmc-call-count`；``_call_match_expr`` 在调用记录快照上计算 ``where``。测试查询统计一次 ``x == 0`` 的 ``Before`` 调用和一次 ``x == 1`` 的 ``After`` 调用。反例 ``call_count("Root.A.After", step=*, where x == 0) >= 1`` 为 UNSAT。参见 ``test_compile_call_count_filters_use_call_time_snapshots`` 和 ``test/bmc/test_call_predicate_guards.py`` 中的守卫用例。省略步选择器时以当前谓词步骤为锚；``*`` 覆盖 :math:`0\le i<N`，越界相对点会被裁剪。未定义的 ``where`` 表达式无法匹配调用记录，因为其定义性会与值合取。

``cover`` 不下沉任意帧谓词。它验证裸 ``case("label")`` 原子，只接受公开的 ``transition`` 与 ``fallback`` 分支类别，并在有界步骤间析取匹配的选择变量。

.. math::
   :label: bmc-objective-cover

   \Phi_{\mathrm{cover}}(\ell) \;=\;
   \bigvee_{\substack{0 \le i < N,\; k \in K_i \\
                      \operatorname{label}(k)=\ell \\
                      \operatorname{kind}(k)\in\{\mathrm{transition},\mathrm{fallback}\}}}
   C_{i,k}
   \qquad [\mathrm{polarity}=\mathrm{witness}].

对事件模型，强制 ``Go`` 为真会使 ``case("Root.A::transition::Root.B::0")`` SAT；强制为假会使同一覆盖目标 UNSAT。``initial``、``delta`` 或 ``absorb`` 标签会成为查询错误，而不是覆盖见证。:eq:`bmc-objective-cover` 映射到 ``_compile_cover`` 和 ``_cover_selectors``，由 ``test_compile_cover_accepts_transition_and_fallback_but_not_internal_cases`` 测试。

``response`` 是严格后继性质
-----------------------------

触发条件在每个可执行步骤 :math:`0\le i<N` 求值，响应条件在帧上求值。步骤 :math:`i` 后的窗口从 :math:`F_{i+1}` 开始：即使响应在 :math:`F_i` 为真，也不能满足该次触发。只有 :math:`i+W\le N` 时窗口才完整。响应只能通过 :math:`G_j(r)` 计入，因此未定义的响应不是成功响应。

:eq:`bmc-response-violation` 是完整窗口上的普通“缺少响应”反例，并包含上界帧 :math:`F_{i+W}`。

.. math::
   :label: bmc-response-violation

   \Phi_{\mathrm{response}}^{\mathrm{miss}}(t,r,W)
   \;=\;
   \bigvee_{\substack{0 \le i < N \\
                      i+W \le N}}
   \left(
       G_i(t) \land
       \neg \bigvee_{j=i+1}^{i+W} G_j(r)
   \right).

步骤 0 的 ``Go`` 为真时，``trigger event("Root.Go", current) -> within 1 active("Root.B")`` 没有反例。把响应换成 ``active("Root.A")`` 后为 SAT：尽管 ``Root.A`` 在触发帧为真，严格后继只检查 :math:`F_1`。边界 2、窗口 2 时，首次在 :math:`F_2` 为真的响应能够满足性质。这些轨迹由 ``_compile_response`` 实现，并由 ``test_compile_response_honors_strict_successor_window_boundaries`` 测试。

未定义触发条件不会被当作“没有触发”。:eq:`bmc-response-trigger-undefined` 把它直接加入主反例目标，再合并两类原因。当前结果与见证协议不区分究竟是哪一个析取项使公式 SAT。

.. math::
   :label: bmc-response-trigger-undefined

   \Phi_{\mathrm{response}}^{\mathrm{undef}}(t)
   \;=\;
   \bigvee_{i=0}^{N-1} \neg D_i(t),
   \qquad
   \Phi_{\mathrm{response}}
   \;=\;
   \Phi_{\mathrm{response}}^{\mathrm{undef}}
   \lor
   \Phi_{\mathrm{response}}^{\mathrm{miss}}
   \qquad [\mathrm{polarity}=\mathrm{counterexample}].

当 ``y == 0`` 时，查询 ``trigger x / y > 0 -> within 1 active("Root")`` 为 SAT，并报告性质违反。相反，有定义且为假的触发条件不贡献违反或不完整性。``test_compile_response_treats_trigger_undefined_as_counterexample`` 固定了这个区别。

:eq:`bmc-response-incomplete` 与主目标分离。它观察一个有定义且为真的触发条件：完整窗口越过 :math:`F_N`，且可见后缀内尚未出现响应。``solve_bmc_property`` 独立于主目标求解这个观察公式；当主检查尚未找到 ``response`` 反例时，它决定 ``incomplete`` 结果。

.. math::
   :label: bmc-response-incomplete

   \Omega_{\mathrm{response}}(t,r,W)
   \;=\;
   \bigvee_{\substack{0 \le i < N \\
                      i+W > N}}
   \left(
       G_i(t) \land
       \neg \bigvee_{j=i+1}^{N} G_j(r)
   \right).

在边界 1、步骤 0 的 ``Go`` 为真、窗口 2、响应为 ``active("Root.A")`` 时，可见后缀只有 :math:`F_1=Root.B`。主 ``response`` 目标因窗口不完整而 UNSAT，:eq:`bmc-response-incomplete` 则为 SAT，结果是 ``incomplete``。若响应已在可见后缀中出现，:math:`\Omega` 为假。``test_compile_response_strict_successor_and_incomplete_suffix`` 与 ``test/bmc/test_witness.py`` 中的求解器级不完整测试覆盖了该行为。

四条 ``response`` 分支不可互换：

.. list-table:: ``response`` 边界矩阵
   :header-rows: 1
   :widths: 18 22 23 20 17

   * - 触发条件
     - 窗口
     - 主目标
     - 不完整公式
     - 结果
   * - 未定义
     - 任意
     - SAT 反例
     - 不决定主结果
     - ``property_violated``
   * - 有定义且为真
     - 完整但无响应
     - SAT 反例
     - 假或无关
     - ``property_violated``
   * - 有定义且为真
     - 截断且无可见响应
     - 对该触发条件为 UNSAT
     - SAT
     - ``incomplete``
   * - 有定义且为假
     - 任意
     - 无贡献
     - 无贡献
     - 由其他步骤决定

这些目标能够说明什么
----------------------

每个主查询都按 :math:`Core_N\land\Phi_q` 求解；``response`` 不完整性按 :math:`Core_N\land\Omega_q` 检查。七种目标不仅对有限帧的量化方式不同，SAT 极性也不同。定义性是这些语义的一部分：删除它会把运行时错误变成错误证明或错误见证。另一方面，``response`` 边界不完整不是运行时定义性错误，也不是反例；增大边界可能补全窗口并改变该有界结果。

这些公式解释当前编译器及其测试。它们不会把有界 UNSAT 提升为无界定理，也不会把重放当成编码正确性的证明。求解结果解释、见证解码与运行时重放由相邻的求解说明页负责。
