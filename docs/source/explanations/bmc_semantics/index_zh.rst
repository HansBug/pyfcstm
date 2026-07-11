FCSTM 如何编码为有界转换系统
================================

有界模型检查（bounded model checking，BMC）并不是把 FCSTM 一个周期一个周期地具体执行。
它为每个帧（frame）分配一份控制状态与持久变量符号，为每个步（step）分配事件输入与
分支观测，再询问 Z3 这些符号副本能否同时满足一个有限公式。本页从
``pyfcstm.bmc.relation`` 的真实数据结构出发，逐层推导这个公式。

本页只解释关系层：它不定义 FBMCQ 语法，不编译性质目标，不把 SAT 解释为性质结论，
也不声称得到无界证明。关系构造器有意停在 :math:`Core_N`；性质编译、见证解码和
运行时重放属于后续层。

全文使用下列集合：:math:`N` 是查询边界；帧索引为 :math:`0..N`，步索引为
:math:`0..N-1`；:math:`V` 是持久变量集合，:math:`\tau(v)` 是变量 :math:`v` 的 Z3 类型；
:math:`\mathcal{A}` 是全限定事件路径集合；:math:`K_i` 是步 :math:`i` 的宏分支集合；
:math:`\mathbb{B}` 是布尔域；:math:`S_0` 与 :math:`S_{\mathrm{rec}}` 是第 0 帧和递推帧的
合法状态标识集合。

贯穿全文的一条真实轨迹
--------------------------

本页自带的 :download:`FCSTM 模型 <trace_machine.fcstm>` 有一个事件、三个持久变量和两个叶状态。
``Go`` 令 ``A`` 转换到 ``B``；转换效果先把 ``counter`` 加 10，目标叶状态的
``during`` 再加 1。后续空闲周期保持在 ``B`` 并继续执行该 ``during``。

.. literalinclude:: trace_machine.fcstm
   :language: fcstm
   :linenos:

:download:`边界为 3 的查询 <trace_bound3.fbmcq>` 将第 0 步的 ``Go`` 固定为真，将第 1、2 步固定为假。

.. literalinclude:: trace_bound3.fbmcq
   :language: fbmcq
   :linenos:

依次调用 ``BmcEngine(model).prepare(query)`` 与 ``build_bmc_core_formula(context)`` 后，Z3 返回
SAT。读取模型得到下表这条真实关系轨迹；状态标识 1、2 分别表示 ``Root.A``、``Root.B``。

.. list-table:: 边界为 3 的真实关系轨迹
   :header-rows: 1

   * - 帧/步
     - 状态
     - ``counter`` / ``ratio`` / ``keep``
     - ``Root.Go``
     - 选中分支
     - :math:`\Delta_i / \Gamma_i`
   * - :math:`F_0 / E_0`
     - ``Root.A`` (1)
     - 0 / :math:`1/2` / 5
     - 真
     - ``transition``
     - 假 / 假
   * - :math:`F_1 / E_1`
     - ``Root.B`` (2)
     - 11 / :math:`1/2` / 5
     - 假
     - ``fallback``
     - 假 / 真
   * - :math:`F_2 / E_2`
     - ``Root.B`` (2)
     - 12 / :math:`1/2` / 5
     - 假
     - ``fallback``
     - 假 / 真
   * - :math:`F_3`
     - ``Root.B`` (2)
     - 13 / :math:`1/2` / 5
     - 不适用
     - 不适用
     - 不适用

第一行揭示两个易错点：边界为 3 意味着四个帧，却只有三个事件位置；``counter`` 变成 11
而不是 10，是因为宏步按运行时顺序继续执行目标叶状态首次 ``during``。运行时对齐
测试独立冻结了同一顺序边界。

1. 分配符号轨迹
-----------------

每个帧由控制状态符号和全部持久变量赋值组成。第 0 帧可使用初始源域，后续帧使用递推域。

.. math::
   :label: bmc-trace-frame-domain

   \mathcal{F}_N=(F_i)_{i=0}^{N},\qquad
   F_i=(s_i,\nu_i)\in S_i\times\prod_{v\in V}\tau(v),\qquad
   S_i=\begin{cases}S_0&i=0,\\S_{\mathrm{rec}}&1\le i\le N,\end{cases}
   \qquad |\mathcal{F}_N|=N+1.

``BmcTraceSymbols.allocate`` 创建 ``F_i_state`` 和逐帧变量映射；``__post_init__`` 拒绝不是
``bound + 1`` 项的帧状态或帧变量元组。初态核心测试冻结第 0 帧的值。因此工作
轨迹恰有 :math:`F_0,F_1,F_2,F_3`。反例：把边界 3 当成三个帧会丢掉 :math:`F_3`，这是
差一错误，不是等价记法。

事件属于 :math:`F_i` 到 :math:`F_{i+1}` 的边，最终帧之后没有事件向量。

.. math::
   :label: bmc-trace-event-domain

   \mathcal{E}_N=(E_i)_{i=0}^{N-1},\qquad
   E_i=(e_{i,a})_{a\in\mathcal{A}}\in\mathbb{B}^{|\mathcal{A}|},\qquad
   |\mathcal{E}_N|=N,\qquad
   |\{e_{i,a}\}|=N|\mathcal{A}|.

分配器遍历 ``domain.steps`` 与 ``domain.events``。事件选择器范围测试证明边界为 3 时只有
事件索引 0、1、2；工作值为真、假、假。反例：:math:`E_3` 不是“自由的最终输入”，
而是不存在；读取它已经越过编码范围。

每个持久变量都具体分配为一族独立符号；整数使用 ``z3.Int``，FCSTM float 使用 ``z3.Real``。

.. math::
   :label: bmc-trace-variable-domain

   X_v^N=(x_{i,v})_{i=0}^{N}\in\tau(v)^{N+1}\quad(v\in V),\qquad
   |\{x_{i,v}\mid 0\le i\le N,\ v\in V\}|=(N+1)|V|.

示例有三个符号族和十二个变量符号；初始化器测试检查整数与实数值，分支测试检查值传递。
反例：动作临时变量不属于 :math:`V`，不能获得逐帧符号族；临时变量测试冻结该边界。

每个展开宏分支都有选择变量；每一步另有语义 delta 观测 :math:`\Delta_i` 和稳定回退
观测 :math:`\Gamma_i`。

.. math::
   :label: bmc-trace-selector-domain

   \mathcal{C}_N=
   \{C_{i,k}\mid 0\le i<N,\ k\in K_i\}
   \cup\{\Delta_i,\Gamma_i\mid 0\le i<N\},\qquad
   C_{i,k},\Delta_i,\Gamma_i\in\mathbb{B},\qquad
   |\mathcal{C}_N|=\sum_{i=0}^{N-1}|K_i|+2N.

``allocate`` 接收每步实际分支标签并检查唯一性。工作轨迹第 0 步有两个分支，后续每步有四个；
只选中一次转换与两次 ``Root.B`` 回退。反例：只分配选择变量不能证明损坏的上游
宏分区满足恰选一个；宏展开才拥有该不变量。

2. 限制合法帧与初始帧
-----------------------

分配类型只保证 :math:`s_i` 是整数；:math:`D_N` 把它限制成合法 BMC 状态标识，第 0 帧的域可能
比递推帧更宽。

.. math::
   :label: bmc-domain-formula

   D_N=\left(s_0\in S_0\right)\land
   \bigwedge_{i=1}^{N}\left(s_i\in S_{\mathrm{rec}}\right),\qquad
   (s_i\in S)\equiv\bigvee_{q\in S}(s_i=q).

``_relation_frame_domain`` 生成两个集合，``_build_domain_formula`` 为每帧发出析取式。工作模型的
:math:`F_0` 可取初始哨兵与模型状态，后续帧只取终止哨兵与稳定叶状态。
反例：把 :math:`s_1=999` 与 :eq:`bmc-domain-formula` 合取会得到 UNSAT，不能用任意整数表示
“未知状态”。

查询的初始模式选择一个确定源标识，不把多个初态留给求解器自选。

.. math::
   :label: bmc-initial-control

   I_0^{\mathrm{ctrl}}\equiv s_0=\operatorname{src}(m),\qquad
   \operatorname{src}(m)=
   \begin{cases}
   \mathrm{STATE\_INIT}&m=\mathrm{cold},\\
   \operatorname{id}(p)&m=\mathrm{state}(p),\\
   \mathrm{STATE\_TERMINATE}&m=\mathrm{terminated}.
   \end{cases}

``_initial_source`` 解析并核对源，``_build_initial_formula`` 发出等式。工作查询令
:math:`s_0=1`；测试另覆盖冷启动与终止启动。反例：``init state("Root.A")`` 是热初态，
不会在 :math:`F_0` 前执行冷启动入口路径；混淆两者会重复执行入口效果。

令 :math:`H` 为 ``havoc`` 集合。不在 :math:`H` 中的持久变量保留模型初始化器，其运行时
定义性也必须成立。

.. math::
   :label: bmc-initial-retained

   I_0^{\mathrm{ret}}(H)=
   \bigwedge_{v\in V\setminus H}
   \left(\operatorname{Def}(\operatorname{init}_v(\nu_0))\land
   x_{0,v}=\operatorname{init}_v(\nu_0)\right).

``_build_initial_formula`` 先追加非 ``havoc`` 初始化器的定义域约束，再追加等式。工作轨迹
固定 0、:math:`1/2`、5；初始化器测试通过令它们的否定 UNSAT 来证明等式。反例：除零
初始化器不会被替成任意值；无 ``havoc`` 时其定义性令核心公式 UNSAT。

``havoc`` 改变初始化器合取项集合，不会增加第二次赋值或特殊值。

.. math::
   :label: bmc-initial-havoc

   \operatorname{Conj}\!\left(I_0^{\mathrm{ret}}(H)\right)=
   \operatorname{Conj}\!\left(I_0^{\mathrm{ret}}(\varnothing)\right)
   \setminus
   \left\{\operatorname{Def}(\operatorname{init}_v(\nu_0)),
   \ x_{0,v}=\operatorname{init}_v(\nu_0)\mid v\in H\right\}.

实现对 ``havoc_names`` 中的变量直接跳过初始化器翻译。``havoc``/``where`` 测试表明，``havoc`` 的 ``x``
仍可由 ``where x == 7`` 固定，而保留变量维持初始化器。反例：“``havoc`` 完全不受约束”过强；
准确含义是“不受初始化器约束”，:math:`D_N`、``where``、假设与转换关系
仍能约束它。

可选 ``where`` 只在第 0 帧求值，并与控制约束和保留变量约束合取；其定义性
同样是硬约束。

.. math::
   :label: bmc-initial-where

   I_0=I_0^{\mathrm{ctrl}}\land I_0^{\mathrm{ret}}(H)\land
   \begin{cases}
   \operatorname{Def}(W(F_0))\land W(F_0)&\text{if a where predicate }W\text{ is present},\\
   \top&\text{otherwise}.
   \end{cases}

``_lower_bmc_cond_expr(..., frame_index=0)`` 产生值与定义域约束；矛盾 ``where`` 测试
令 :math:`I_0` UNSAT。反例：``where`` 不是宏分支守卫，只约束 :math:`I_0`；专门测试确认
分支分区不包含也不重放它。

3. 下沉每个宏分支
------------------------

对第 :math:`i` 步的分支 :math:`k`，宏展开已用事件原子、转换守卫、优先级
掩码和已接受分支依赖组装布尔模板；关系下沉再合取源状态等式。

.. math::
   :label: bmc-case-antecedent

   A_{i,k}\equiv
   \left(s_i=\operatorname{src}(k)\right)\land
   Q_{i,k}\!\left(F_i,E_i,(A_{i,j})_{j\prec k}\right).

``_lower_bool_template`` 把事件原子映射到 :math:`e_{i,a}`、守卫原子映射到下沉后的守卫、
已接受原子映射到较早前件；``_build_case_relation`` 增加源守卫。工作第 0 步的
转换前件为真，因为 :math:`s_0` 是 ``Root.A`` 且 ``Root.Go`` 为真。反例：当状态
已是 ``B`` 时，为真的 ``Go`` 不能激活 ``A -> B``；只看事件会漏掉源状态合取项。

公开分支选择变量在两个方向上精确观测前件。

.. math::
   :label: bmc-case-selector

   C_{i,k}\leftrightarrow A_{i,k}.

代码对应“选择变量等于前件”；分支关系测试确认前件为假时选择变量不能任意
翻成真。反例：若只有 :math:`C_{i,k}\Rightarrow A_{i,k}`，前件为真时选择变量仍可为假，
从而破坏分支覆盖与调用计数，即使后状态蕴含式仍触发。

后件必须位于蕴含式中；未选中的分支不得写入自己的目标状态或变量。令
:math:`\mathcal{D}_{i,k}` 包含下沉该分支的守卫与有序动作块时累积的全部运行时定义性
条件。这些条件属于被选中分支的后件，不是可有可无的诊断信息。

.. math::
   :label: bmc-case-relation

   T_{i,k}\equiv
   \left(C_{i,k}\leftrightarrow A_{i,k}\right)\land
   \left(A_{i,k}\Rightarrow
   \left(R_{i,k}\land
   \bigwedge_{d\in\mathcal{D}_{i,k}}d\right)\right).

``BmcCaseRelation.formula`` 就是上式。蕴含式核心测试令 ``Go`` 为真时得到转换目标，
令其为假时得到回退目标；运行时对齐测试组独立对齐转换效果。
``_prepare_case_lowering`` 累积守卫和动作定义性，``_build_case_relation`` 再把这些约束
加入 ``consequent``。例如，被选中转换中的效果 ``x = 1 / 0`` 会贡献
:math:`0\ne0`，因此该分支以及这次尝试执行均为 UNSAT。同一非法运算若位于未选中分支，
则不会约束当前步骤，因为定义性合取仍处于蕴含式后件中。反例：换成
:math:`A_{i,k}\land R_{i,k}` 会要求所有展开分支同时被选中，通常令整个步 UNSAT；
省略 :math:`\mathcal{D}_{i,k}` 同样不可靠，因为 Z3 可以给部分算术运算任意赋值，
从而伪造运行时无法执行的转换。

每个选中分支都有一个已展开目标标识，包括稳定叶、delta 停顿的初始哨兵与
终止哨兵。

.. math::
   :label: bmc-case-post-control

   R_{i,k}^{\mathrm{ctrl}}\equiv
   s_{i+1}=\operatorname{tgt}(k).

``_build_case_relation`` 将它作为第一条后置约束。工作转换把 ``Root.B`` 写入
:math:`s_1`；事件转换对齐测试证明 ``Go`` 条件下其他状态标识均为 UNSAT。
反例：不能从 FCSTM 端点重新猜目标；宏展开可能已解析伪状态下降或
终止，绕过 ``case.target_state_id`` 会丢失语义。

动作按运行时顺序符号执行。对分支 :math:`k` 改写的变量集合 :math:`W_k`，最终符号环境就是
下一帧值。

.. math::
   :label: bmc-case-variable-write

   R_{i,k}^{\mathrm{write}}\equiv
   \bigwedge_{v\in W_k}
   \left(x_{i+1,v}=\operatorname{Eval}_v(\operatorname{ops}_k,\nu_i)\right).

``_prepare_case_lowering`` 与 ``_execute_action_block`` 构造 ``final_env``，通用后置循环写到
:math:`i+1`。工作轨迹中转换 ``+10`` 后接目标 ``during`` 的 ``+1``，所以
:math:`x_{1,\mathrm{counter}}=11`；退出/效果/进入测试还冻结 5 + 10 + 2 = 17 的顺序。
反例：把动作块当作无序集合，在多个块改写同一变量时必然错误；后一个表达式必须消费
前一个符号结果。

符号执行从当前帧环境开始，因此未被动作修改的变量保留输入表达式。

.. math::
   :label: bmc-case-variable-carry

   R_{i,k}^{\mathrm{carry}}\equiv
   \bigwedge_{v\in V\setminus W_k}\left(x_{i+1,v}=x_{i,v}\right).

实现无需单独的值传递循环：``final_env`` 仍把未写名映射到 :math:`F_i` 符号，通用后置循环自然
发出等式。工作轨迹中的 ``keep``、``ratio`` 始终为 5、:math:`1/2`，核心测试证明相反值 UNSAT。
反例：将未写后置变量留自由会凭空引入 FCSTM 与 ``SimulationRuntime`` 都没有的非确定状态。

4. 组装单步与有界转换关系
-----------------------------------------

回退是显式展开的分支，不是求解后临时加入的“什么也不做”。它否定较早接受的转换，
而且可以执行 ``during``。

.. math::
   :label: bmc-step-fallback

   T_i^{\mathrm{fb}}\equiv
   \bigwedge_{k\in K_i^{\mathrm{fb}}}
   \left[\left(C_{i,k}\leftrightarrow A_{i,k}\right)\land
   \left(A_{i,k}\Rightarrow R_{i,k}\right)\right],\qquad
   A_{i,k}\Rightarrow\bigwedge_{j\prec k}\neg A_{i,j}.

``_build_step_relation`` 与普通分支一样下沉回退；回退运行时测试观察到被否定的
已接受原子与 ``during`` 更新。工作第 1、2 步选择 ``Root.B`` 回退并递增 ``counter``。
反例：回退不必让变量全部停顿；这里它改变 ``counter``，只有 ``ratio``、``keep`` 传递原值。

终止状态是吸收态；吸收分支还拒绝后续所有事件输入并传递持久变量。

.. math::
   :label: bmc-step-terminated-absorb

   s_i=\mathrm{STATE\_TERMINATE}\Rightarrow
   \left(s_{i+1}=\mathrm{STATE\_TERMINATE}\right)\land
   \bigwedge_{a\in\mathcal{A}}\neg e_{i,a}\land
   \bigwedge_{v\in V}\left(x_{i+1,v}=x_{i,v}\right).

``_recurrence_formals`` 展开 ``terminated_source``，吸收分支追加每个事件输入的否定。
终止测试检查状态吸收与变量传递，并证明终止后强制事件为真会得到 UNSAT。
反例：允许终止后事件会创造运行时无法消费的输入，令见证事件账目与重放分歧。

两个进展观测分别精确等价于对应分支前件的析取，并显式互斥。

.. math::
   :label: bmc-step-delta-gamma

   \Delta_i\leftrightarrow\bigvee_{k\in K_i^{\delta}}A_{i,k},\qquad
   \Gamma_i\leftrightarrow\bigvee_{k\in K_i^{\mathrm{fb}}}A_{i,k},\qquad
   \neg(\Delta_i\land\Gamma_i).

``_build_step_relation`` 发出这三条约束。冷启动源因必需事件缺失而受阻时选择 delta 并停顿；
无转换的稳定叶选择回退并可执行 ``during``。冷启动 delta 与稳定 gamma 两个测试冻结
该差别。反例：:math:`\Delta_i` 不等于“无事件”，:math:`\Gamma_i` 也不等于“变量不变”；它们
分类展开分支语义，而不是原始向量相等性。

一个步合取所有分支公式与观测约束；有界转换公式再合取全部 :math:`N` 步。

.. math::
   :label: bmc-transition-formula

   T_i=\left(\bigwedge_{k\in K_i}T_{i,k}\right)\land
   \left(\Delta_i\leftrightarrow\bigvee_{k\in K_i^{\delta}}A_{i,k}\right)\land
   \left(\Gamma_i\leftrightarrow\bigvee_{k\in K_i^{\mathrm{fb}}}A_{i,k}\right)\land
   \neg(\Delta_i\land\Gamma_i),\qquad
   T_N=\bigwedge_{i=0}^{N-1}T_i.

``build_bmc_core_formula`` 构造每个 ``BmcStepRelation`` 并合取其 ``formula``。工作边界得到
:math:`T_0\land T_1\land T_2`，连接四个帧；边界为二的终止测试确认初始步后使用递推
形式。反例：边界为 3 却只合取 :math:`T_0` 会让 :math:`F_2`、:math:`F_3` 脱离执行关系，
即使它们仍满足 :math:`D_N` 也不是合法轨迹。

5. 加入环境假设并冻结核心公式
-----------------------------

令 :math:`\mathcal{H}_F` 保存帧索引集合与谓词对，:math:`\mathcal{H}_E` 保存固定事件
字面量，:math:`\mathcal{H}_{\le1}` 保存每一步受至多一个约束的事件池；``any`` 不贡献
基数合取项。

.. math::
   :label: bmc-environment-formula

   ENV_N=
   \bigwedge_{(J,p)\in\mathcal{H}_F}\ \bigwedge_{i\in J}
   \left(\operatorname{Def}(p(F_i))\land p(F_i)\right)
   \land
   \bigwedge_{(J,a,b)\in\mathcal{H}_E}\ \bigwedge_{i\in J}
   \left(e_{i,a}=b\right)
   \land
   \bigwedge_{B\in\mathcal{H}_{\le1}}\ \bigwedge_{i=0}^{N-1}
   \operatorname{AtMostOne}\!\left((e_{i,a})_{a\in B}\right).

``_build_environment_formula`` 把 ``always`` 展开到第 0 至 :math:`N` 帧，把 ``at`` 下沉到指定帧，
应用已解析的事件选择器，并为显式事件池调用 ``z3.AtMost``。工作 :math:`ENV_3` 为 ``Go_0``、
非 ``Go_1``、非 ``Go_2``；环境测试验证帧与事件范围。反例：不存在隐式全局
至多一个约束；未声明 ``cardinality at_most_one`` 时两个不同事件可同一步为真，测试覆盖 SAT/UNSAT。

关系层最后一步只是合取，不添加也不解释性质目标。

.. math::
   :label: bmc-core-formula

   Core_N=D_N\land I_0\land T_N\land ENV_N.

``build_bmc_core_formula`` 按此顺序构造四个具名字段，把合取存入 ``BmcCoreFormula.core``。核心测试
追加预期值的否定并得到 UNSAT，从而证明公式后果；性质编译会在后续层增加目标公式。
反例：:math:`Core_3` UNSAT 只说明没有满足这些初始/环境约束的长度三编码轨迹；
它不证明更大边界没有轨迹，也不是无界模型检查定理。

公式总账与审查锚点
--------------------

下表把本页的关系公式逐项映射到 ``pyfcstm/bmc/relation.py``、语义回归测试与页首独立文档资源。

.. list-table:: 冻结关系公式总账
   :header-rows: 1
   :widths: 23 27 28 22

   * - 公式
     - 实现锚点
     - 测试锚点
     - 工作证据
   * - :eq:`bmc-trace-frame-domain`
     - ``BmcTraceSymbols.allocate``
     - 核心初态测试
     - 边界 3 四帧
   * - :eq:`bmc-trace-event-domain`
     - ``BmcTraceSymbols.allocate``
     - 事件选择器范围测试
     - 三个 ``Go`` 位置
   * - :eq:`bmc-trace-variable-domain`
     - ``BmcTraceSymbols.allocate``
     - 初始化器和值传递测试
     - 三族十二符号
   * - :eq:`bmc-trace-selector-domain`
     - ``BmcTraceSymbols.allocate``
     - 分支/进展测试
     - 转换、两次回退
   * - :eq:`bmc-domain-formula`
     - ``_build_domain_formula``
     - 定义域后果测试
     - 状态标识 1、2
   * - :eq:`bmc-initial-control`
     - ``_build_initial_formula``
     - 冷启动/热启动/终止测试
     - 第 0 帧 ``Root.A``
   * - :eq:`bmc-initial-retained`
     - ``_build_initial_formula``
     - 初始化器测试
     - 0、:math:`1/2`、5
   * - :eq:`bmc-initial-havoc`
     - ``_build_initial_formula``
     - ``havoc``/``where`` 测试
     - 见上文反例
   * - :eq:`bmc-initial-where`
     - ``_build_initial_formula``
     - 矛盾 ``where`` 测试
     - 只约束第 0 帧
   * - :eq:`bmc-case-antecedent`
     - ``_build_case_relation``
     - 语义夹具/优先级测试
     - ``A`` 加 ``Go``
   * - :eq:`bmc-case-selector`
     - ``_build_case_relation``
     - 选择变量真值测试
     - 每步一个选中标签
   * - :eq:`bmc-case-relation`
     - ``_build_case_relation``
     - 蕴含/对齐测试
     - 仅选中分支写入
   * - :eq:`bmc-case-post-control`
     - ``_build_case_relation``
     - 事件转换测试
     - ``Root.A`` 到 ``Root.B``
   * - :eq:`bmc-case-variable-write`
     - ``_build_case_relation``
     - 动作顺序测试
     - ``counter`` 0 到 11
   * - :eq:`bmc-case-variable-carry`
     - ``_build_case_relation``
     - 未写变量传递测试
     - ``ratio``、``keep`` 不变
   * - :eq:`bmc-step-fallback`
     - ``_build_step_relation``
     - 回退对齐测试
     - 空闲 ``B`` 递增
   * - :eq:`bmc-step-terminated-absorb`
     - 吸收分支
     - 终止/事件测试
     - 终止后事件 UNSAT
   * - :eq:`bmc-step-delta-gamma`
     - ``_build_step_relation``
     - delta/gamma 对比测试
     - 空闲 ``B`` 假/真
   * - :eq:`bmc-transition-formula`
     - 步/核心构造器
     - 递推测试
     - 三个相连步
   * - :eq:`bmc-environment-formula`
     - ``_build_environment_formula``
     - 帧/事件/基数测试
     - 真、假、假
   * - :eq:`bmc-core-formula`
     - ``build_bmc_core_formula``
     - ``test_relation_core.py``
     - 已准备查询为 SAT

Sphinx 能验证 :eq:`bmc-core-formula` 这类交叉引用，双语漂移检查器能比较标签与字面 LaTeX；
两者都不能自动证明语义。审阅者仍须把每一行与具名代码、测试和真实轨迹逐项核对。
