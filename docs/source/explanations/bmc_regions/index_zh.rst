区域怎样进入有界转移系统
========================

拥有一组区域（region）的状态会在同一个周期里按顺序逐个运行这些区域。有界模型检查（bounded model checking，BMC）必须把这个周期变成一条有限公式，而且不能把各区域路径的每一种组合都写出来；它解码出的见证（witness）还要经得起仿真器的回放（replay）。本页解释 :mod:`pyfcstm.bmc.region_relation` 及其相邻模块怎样做到这些：用哪些符号描述区域，区域怎样串联，拥有者（owner）怎样启动与结束，热启动（hot start）的初始帧从哪里来，以及构造在哪里停下。

本页只讲区域的编码。它不定义 FBMCQ 语法（见 :doc:`FBMCQ 参考 </reference/bmc_query/index_zh>`\ ），不重复不含区域的模型的关系（见 :doc:`/explanations/bmc_semantics/index_zh`\ ），也不给出代价增长的闭式（见 :doc:`/explanations/bmc_scaling/index_zh`\ ）。哪台机器怎样运行一个周期由 :doc:`/explanations/region_semantics/index_zh` 定义；本页只说明编码如何跟随它。BMC 的结论仍然只是关于至多 :math:`N` 个宏步的有界陈述。

术语与符号
----------

**拥有者**\ 是声明了区域的状态。它的\ **区域**\ 按书写顺序运行，书写顺序也是执行顺序。区域是命名空间而不是状态，所以区域持有的是一个\ **位置**\ （position）：它的分支停驻的状态，或下面三个标记之一。当机器在拥有者内部且没有离开时，称拥有者在这一帧\ **停驻**\ 。区域的位置是一个状态时称它\ **仍在工作**\ ，通过 ``[*]`` 结束后称它\ **已完成**\ 。

本页全程使用同一套记号。帧下标 :math:`t`\ 、边界 :math:`N` 与持久变量向量 :math:`\nu_t` 与 :doc:`/explanations/bmc_semantics/index_zh` 中相同。

* :math:`O` 是一个拥有者，\ :math:`R_1,\dots,R_n` 是它按书写顺序排列的区域。例：\ ``Controller.Running`` 是 :math:`n=2` 的拥有者，\ :math:`R_1=` ``Safety``\ ，\ :math:`R_2=` ``Motion``\ 。
* :math:`\mathcal{P}_i` 是 :math:`R_i` 的分支可以停驻的状态标识集合。例：对 ``Motion`` 它包含 ``Off`` 与 ``On`` 的标识。
* :math:`s_t` 是第 :math:`t` 帧的状态符号，\ :math:`\mathrm{id}(O)` 是 :math:`O` 的标识。
* :math:`p_{t,i}` 是区域 :math:`R_i` 在第 :math:`t` 帧的位置符号，代码里写作 ``BmcTraceSymbols.region_position(t, path)``\ 。\ :math:`q_{t,i}` 是同一区域在第 :math:`t` 步轮到自己之后的位置。
* :math:`\mathsf{DONE}`\ 、\ :math:`\mathsf{INACTIVE}` 与 :math:`\mathsf{PENDING}` 是三个标记 ``REGION_DONE_ID``\ （-4）、\ ``REGION_INACTIVE_ID``\ （-5）与 ``REGION_PENDING_ID``\ （-6）。
* :math:`\mathrm{Rest}_t(O)` 表示 :math:`O` 在第 :math:`t` 帧停驻：对不在任何区域内的拥有者它就是 :math:`s_t=\mathrm{id}(O)`\ ，对嵌套的拥有者还要求外层区域的位置是 :math:`O` 且外层拥有者停驻。
* :math:`\xi_t^{(0)},\dots,\xi_t^{(n)}` 是第 :math:`t` 步里从一个区域交给下一个区域的值：持久变量，加上含 ``>> during`` 切面（aspect）的模型里每个切面作用域的两个标志。\ :math:`\xi_t^{(0)}` 是周期开始时的向量，\ :math:`\xi_t^{(i)}` 是区域 :math:`R_i` 留下的向量。
* :math:`\eta` 是进入拥有者时所用的值向量，\ :math:`\mathcal{E}` 是当前路径上正在判定的（拥有者，向量）对的列表，\ :math:`L` 是选项 ``BmcOptions.max_group_reentries``\ 。

贯穿全文的模型
--------------

下面每一节都使用\ :doc:`区域教程 </tutorials/regions/index_zh>`\ 里的联锁控制器。\ ``Safety`` 写在 ``Motion`` 之前，所以每个周期里 ``Safety`` 先更新 ``permit``\ ，\ ``Motion`` 再读取它。

.. literalinclude:: ../../tutorials/regions/controller.fcstm
   :language: fcstm
   :linenos:

要问的是：\ ``permit`` 已经是 0 时电机是否还可能开着。查询在四个宏步内寻找反例：冷启动（cold start）、\ ``/Start``\ 、一次请求，以及与请求同拍到来的故障。

.. literalinclude:: interlock.fbmcq
   :language: fbmcq

``forbid`` 搜索 ``motor`` 为 1 且 ``permit`` 为 0 的帧。下面的命令在按原样书写的模型和 ``controller_swapped.fcstm`` 上各运行一次，后者只是把 ``Motion`` 写在 ``Safety`` 之前。脚本删掉了打印求解耗时的那一行，因此每次运行的输出相同。

.. literalinclude:: interlock.demo.sh.txt
   :language: text

先看两条标题行。\ ``Safety`` 在前时结论是 ``PROPERTY GUARANTEED WITHIN BOUND``\ ，退出码为 0：至多四个宏步的任何执行都不会在许可关闭时让电机开着。\ ``Motion`` 在前时结论是 ``PROPERTY DOES NOT HOLD WITHIN BOUND``\ ，退出码为 1，报告打印出一条已由仿真器回放的反例。两个模型只差书写顺序，所以顺序是公式的一部分。本页其余部分推导它怎样进入公式。

这段输出没有说明两件事。它没有说第一个控制器在四个宏步之外也安全。它也没有显示两条公式为什么不同；第 1 节与第 2 节说明这一点。

1. 一步是一个完整周期，每个区域都有一个位置
-------------------------------------------

轨迹为每一帧分配一个状态符号和每个持久变量一个符号，为每个步和每个分支分配一个选择符号，与 :doc:`/explanations/bmc_semantics/index_zh` 描述的完全一致。含区域的模型每帧再多出每个区域一个符号 :math:`p_{t,i}`\ 。一步仍然是一个完整的运行时周期：每个停驻拥有者的区域在同一步内轮流行动，所以第 :math:`t` 步之后的帧已经显示了每个区域做了什么。

位置符号取下列值之一。

.. list-table:: 区域位置符号的取值
   :header-rows: 1
   :widths: 24 30 46

   * - 取值
     - 常量
     - 含义
   * - 一个状态标识
     - :math:`\mathcal{P}_i` 的成员
     - 区域的分支停驻在这个稳定叶子，或停驻在自己也拥有区域的状态。
   * - -4
     - ``REGION_DONE_ID``
     - 区域通过 ``[*]`` 结束，而拥有者仍然停驻。
   * - -5
     - ``REGION_INACTIVE_ID``
     - 拥有者在这一帧没有停驻，所以区域没有位置。
   * - -6
     - ``REGION_PENDING_ID``
     - 热启动省略了这个区域或写了 ``[init]``\ ，区域在第一个周期里启动。只有保存整个起点位置的那一帧可以使用它。

三条约束把每个区域的位置与它的拥有者绑在一起。它们在每一帧都成立，并且是核心公式的一部分：

.. math::
   :label: eq-region-position-domain

   \begin{aligned}
   \mathrm{Rest}_t(O) &\Rightarrow
     \bigwedge_{i=1}^{n}\bigl(p_{t,i}\in\mathcal{P}_i\cup\{\mathsf{DONE}\}\bigr),\\
   \lnot\,\mathrm{Rest}_t(O) &\Rightarrow
     \bigwedge_{i=1}^{n}\bigl(p_{t,i}=\mathsf{INACTIVE}\bigr),\\
   \mathrm{Rest}_t(O) &\Rightarrow
     \bigvee_{i=1}^{n}\bigl(p_{t,i}\neq\mathsf{DONE}\bigr).
   \end{aligned}

第一行让停驻拥有者的区域留在自己的命名空间里。第二行让区域恰好在拥有者没有停驻时处于不活动。第三行禁止区域全部已完成的停驻拥有者：区域全部结束的一组会在同一周期里把控制交还（第 4 节），所以没有任何帧可以停在那里。\ ``region_frame_constraints`` 构造这些约束，\ ``test_the_frame_constraints_are_part_of_the_core_and_can_be_read_back`` 把它们从核心公式中读回。

下面的脚本固定工作查询的四个周期（输入与 ``Start`` 事件），求解核心公式，并为每一帧打印每个区域的位置和两个变量。它是可选的验证基础设施，完整源码是 :download:`positions.demo.py <positions.demo.py>`\ 。读取符号的行是：位置用 ``symbols.region_position(frame, path)``\ ，变量用 ``symbols.frame_var(frame, name)``\ 。

.. literalinclude:: positions.demo.py.txt
   :language: text

看 ``controller`` 块。第 0 帧和第 1 帧里机器在初始哨兵和 ``Idle``\ ，拥有者没有停驻，两个位置都是 ``INACTIVE``\ 。第 2 帧里拥有者停驻，\ ``Safety`` 和 ``Motion`` 分别持有 ``Watching`` 和 ``Off``\ 。没有任何一帧的位置不是自己区域的状态标识、\ ``DONE`` 或 ``INACTIVE``\ ，这就是 :eq:`eq-region-position-domain` 前两行在起作用。这个块只展示一次执行，不能证明约束；证明由测试完成。

2. 区域按书写顺序串联
---------------------

在第 :math:`t` 步里，各区域并不各自独立读取帧变量。区域 :math:`R_1` 从周期开始的值出发，之后的每个区域从前一个区域留下的值出发。公式在每个区域之后引入一个新的向量 :math:`\xi_t^{(i)}`\ ，并把它们串起来：

.. math::
   :label: eq-region-value-chain

   \begin{aligned}
   \xi_t^{(0)} &= \nu_t,\\
   \mathrm{Chain}_t(O) &\equiv
     \bigwedge_{i=1}^{n}\mathrm{Run}_{t,i}\bigl(\xi_t^{(i-1)},\,p_{t,i},\,\xi_t^{(i)},\,q_{t,i}\bigr).
   \end{aligned}

:math:`\mathrm{Run}_{t,i}` 是区域 :math:`R_i` 这一轮的降低结果。它对区域可能所处的每个位置各有一条蕴含：\ ``p == leaf`` 蕴含该叶子的各条路径；另外还有区域已完成或不活动的情形，那种情形只把位置和值带过去。后面的区域从 :math:`\xi_t^{(i-1)}` 读入，所以它看到前面区域的新值，反过来则不会。没有任何东西让前面的区域在后面区域写入的值上再跑一遍，这就是前面的区域不重跑的设计规则。

第 1 节的脚本还打印了故障周期里交接的值，它们是从求解出的模型的中间符号里读出来的。符号名是实现细节，脚本只是为了展示交接才读取它们。

.. literalinclude:: positions.demo.py.txt
   :language: text
   :lines: 1,7-9,10,16-18

节选保留了每个模型的故障周期。\ ``Safety`` 在前时，区域 1 之后的向量是 ``permit=0``\ 、\ ``motor=1``\ ：\ ``Safety`` 收回了许可，而 ``Motion`` 还没有行动。随后 ``Motion`` 读到 ``permit=0``\ ，把 ``motor`` 置为 0。\ ``Motion`` 在前时，它读到 ``permit=1``\ ，保持开启，\ ``Safety`` 之后才清除许可，所以第二个块的第 4 帧是 ``motor=1`` 且 ``permit=0``\ 。这就是 ``forbid`` 查询找到的反例。节选只说明串联是有序的，不说明 Z3 怎样找到它。

为什么公式是求和
~~~~~~~~~~~~~~~~

每个 :math:`\mathrm{Run}_{t,i}` 只由区域 :math:`R_i` 自己的单元降低而来，各单元只通过 :math:`\xi_t^{(i)}` 相连。平铺展开则需要为各区域路径的每一种组合各写一条路径。下一个脚本统计一个工作周期降低出的路径数，区域数从一到八，每个区域在各自的事件上于两个状态之间切换。

.. literalinclude:: lowered_paths.demo.py.txt
   :language: text

每多一个区域增加四条降低出的路径：两个停驻位置乘以两种结果（转换或回退）。无论区域数是多少，还有两条始终存在：从初始帧出发的冷启动路径，以及所有区域结束后根状态的续接。第三列是按同一描述平铺展开所需的组合路径数。计数说明降低出的路径数随区域数相加增长。它统计的是路径而不是公式节点；精确闭式以及代价仍然陡增的地方见 :doc:`/explanations/bmc_scaling/index_zh`\ 。

3. 进入拥有者会启动每个区域
---------------------------

进入拥有者的转换不会停在拥有者上。它带着整组的初始化：先启动区域 :math:`R_1`\ ，再在 :math:`R_1` 的启动留下的值上启动 :math:`R_2`\ ，依此类推。设 :math:`\eta` 是进入拥有者时的值，\ :math:`\eta^{(i)}` 是 :math:`R_i` 启动之后的值。当区域 :math:`R_i` 在 :math:`\eta^{(i-1)}` 上有一条可以提交的初始路径时它能启动，这个条件记作 :math:`\mathrm{ok}_i`\ 。

.. math::
   :label: eq-region-owner-start

   \begin{aligned}
   \mathrm{ok}_i &\equiv \mathrm{Start}_i\bigl(\eta^{(i-1)}\bigr),\\
   \mathrm{Entry}_O(\eta) &\equiv
     \bigwedge_{i=1}^{n}\Bigl(\bigwedge_{j<i}\mathrm{ok}_j\ \Rightarrow\
       \mathrm{Init}_i\bigl(\eta^{(i-1)},\,q_i,\,\eta^{(i)}\bigr)\Bigr),\\
   \mathrm{Accept}_O(\eta) &\equiv \bigwedge_{i=1}^{n}\mathrm{ok}_i\ \land\
     \Bigl(\lnot\,\mathrm{AllDone}\ \lor\ \mathrm{Can}_O\bigl(\eta^{(n)}\bigr)\Bigr).
   \end{aligned}

:math:`\mathrm{Init}_i` 是区域 :math:`R_i` 第一条可提交初始路径的关系。只有前面的区域都已启动时才断言它，所以排在起不来的区域之后的区域不赋任何值，它的任何操作也不必有定义。\ :math:`\mathrm{AllDone}` 表示各区域在启动之后立刻全部已完成，:math:`\mathrm{Can}_O` 是第 4 节的续接检查，这里作用于 :math:`\eta^{(n)}`\ ：各区域立刻一起结束时，只有拥有者能在同一周期里续接，这次进入才被接受。\ :math:`\mathrm{Accept}_O` 是进入 :math:`O` 的那条路径能否被采用的条件。它为假时整条路径被拒绝。编码不会回头为前面的区域尝试另一个入口，这就是“后面的区域起不来则拒绝整个进入”的规则。

冷启动最能看出这个拒绝，因为没有别的东西能作用于初始帧。模型有两个区域；只有输入 ``g`` 为正时 ``B`` 才能启动。

.. literalinclude:: blocked.fcstm
   :language: fcstm
   :linenos:

三条查询：一条没有假设，一条固定 ``g == 0`` 并要求到达拥有者，一条固定 ``g == 0`` 且只要求看到任意轨迹。

.. literalinclude:: owner_start.demo.sh.txt
   :language: text

``g`` 自由时一步内就能到达 ``Root.Run``\ ：两个区域都启动。\ ``g == 0`` 时，尽管 ``A`` 自己可以启动，\ ``Root.Run`` 这个目标在两步内也不可实现。只要求轨迹的那条查询打印出两个 ``[delta]`` 步：机器停在初始帧，因为整个进入被拒绝，下一个周期再试一次。这是仿真器规则的编码：无法进入的冷启动让一切保持原样。输出没有展示拒绝的代价，也不声称仿真器会选择另一个入口；按同一条规则它不会。

4. 最后一个区域只有在拥有者能续接时才能结束
-------------------------------------------

通过 ``[*]`` 结束的区域得到位置 :math:`\mathsf{DONE}`\ 。只要还有别的区域在工作，这就是允许的。如果它是最后一个仍在工作的区域，拥有者必须能在同一周期里续接，因为没有任何帧可以保存一个区域全部已完成的停驻拥有者。

设 :math:`\mathrm{Live}_{t,i}` 表示在 :math:`R_i` 这一轮之后还有别的区域仍在工作：某个前面的区域 :math:`R_j` 满足 :math:`q_{t,j}\neq\mathsf{DONE}`\ ，或某个后面的区域的位置既不是 :math:`\mathsf{DONE}` 也不是 :math:`\mathsf{INACTIVE}`\ 。设 :math:`\mathrm{Can}_O(\xi)` 表示 :math:`O` 的一条续接可以在值 :math:`\xi` 上提交，\ :math:`\mathrm{Cont}_O` 是这条续接的关系。

.. math::
   :label: eq-region-joint-completion

   \begin{aligned}
   q_{t,i}=\mathsf{DONE} &\Rightarrow
     \mathrm{Live}_{t,i}\ \lor\ \mathrm{Can}_O\bigl(\xi_t^{(i)}\bigr),\\
   \mathrm{AllDone}_t &\equiv \bigwedge_{i=1}^{n}\bigl(q_{t,i}=\mathsf{DONE}\bigr),\\
   \lnot\,\mathrm{AllDone}_t &\Rightarrow
     \Bigl(s_{t+1}=\mathrm{id}(O)\ \land\ \nu_{t+1}=\xi_t^{(n)}\ \land\
       \bigwedge_{i=1}^{n}p_{t+1,i}=q_{t,i}\Bigr),\\
   \mathrm{AllDone}_t &\Rightarrow
     \mathrm{Cont}_O\bigl(\xi_t^{(n)},\,s_{t+1},\,\nu_{t+1}\bigr).
   \end{aligned}

第一行是对最后一个区域的接受检查，在它自己这一轮之后的值上求值。第三行让拥有者继续停驻，并把串联的结果复制到下一帧。第四行在同一步里把控制交给续接。当最后一个区域想要结束而没有续接可以提交时，第一行拒绝这次结束，区域留在原叶子里，该周期改为执行它的 ``during``\ 。触发结束的事件或条件不会保留到下一个周期。

联合完成的模型有两个都会结束的区域，只有输入 ``ok`` 非零时拥有者才续接到 ``Next``\ 。

.. literalinclude:: joint.fcstm
   :language: fcstm
   :linenos:

脚本提出五个问题，并打印每条查询及其报告的标题行。

.. literalinclude:: joint_completion.demo.sh.txt
   :language: text

``A`` 可以单独结束（第一条）：\ ``B`` 仍在工作，所以 :eq:`eq-region-joint-completion` 的第一行不需要续接就成立。两个区域都已完成的状态不可达（第二条），这是 :eq:`eq-region-position-domain` 第三行的要求。\ ``Next`` 可达（第三条），这需要最后一次结束与交还在同一步里完成。\ ``ok`` 固定为 0 时，\ ``B`` 永远不能结束（第四条），\ ``Next`` 也不可达（第五条）：最后一个区域被拒绝，而不是停在 ``[done]``\ 。这些运行不能证明其他形状也成立；\ ``test_the_last_region_may_finish_only_if_the_owner_can_continue`` 及其相邻测试才能证明。

切面与拥有者的普通 ``during before``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

切面给 :math:`\xi` 再加两类值：对每个声明了 ``>> during`` 动作的作用域，一个表示它的 ``before`` 动作在本周期已经运行的标志，和一个表示它欠着 ``after`` 动作的标志。标志随串联一起传递。因此 ``before`` 动作每个作用域每个周期运行一次，由外向内。欠着的 ``after`` 动作在它所属作用域的分支结束时结算，最内层的作用域先结算，所以下一个区域已经能看到它。不在区域内的作用域在周期末结算。公式随切面作用域的个数增长，而不随它们子集的个数增长。

拥有者上不带 ``>>`` 的普通 ``during before`` 属于整组的初始化：它在进入第一个非伪状态的子状态之前运行一次。普通 ``during after`` 在把控制交还的已提交路径上运行一次。下一个脚本按调用顺序列出两个模型每一步的抽象动作。

.. literalinclude:: aspect_order.demo.sh.txt
   :language: text

第一个模型里，\ ``Pre`` 与 ``Post`` 是根的切面，\ ``PostA`` 声明在区域 ``A`` 内。每一步先调用 ``Pre``\ ，最后调用 ``Post``\ ，而 ``PostA`` 紧跟在 ``WorkA`` 之后、\ ``WorkB`` 开始之前运行：\ ``A`` 的分支结束了，所以它的 ``after`` 动作在 ``B`` 的轮次之前结算。第二个模型里 ``Prep`` 是拥有者的普通 ``during before``\ ，它先于两个区域的 ``enter`` 动作。两个模型在 :download:`aspects.fcstm <aspects.fcstm>` 与 :download:`plain_before.fcstm <plain_before.fcstm>` 中。输出只显示调用顺序，不显示抽象调用的快照，快照在第 6 节讲。

5. 热启动构造第一帧
-------------------

``init state("...")`` 不执行第一个周期的进入。它写下一个位置，第 0 帧恰好保存这个位置，所以第一个周期从它继续。文本可以是配置、经过区域的路径，或只写拥有者。

.. list-table:: ``init state(...)`` 中位置的写法
   :header-rows: 1
   :widths: 34 38 28

   * - 文本
     - 第 0 帧的位置
     - 省略的区域
   * - ``"Controller.Running{Motion: On}"``
     - ``Motion`` 停驻在 ``On``\ ，拥有者停驻
     - ``Safety`` 是 ``PENDING``
   * - ``"Controller.Running.Motion.On"``
     - 同一个位置，写成经过区域的路径
     - ``Safety`` 是 ``PENDING``
   * - ``"Controller.Running"``
     - 拥有者停驻，没有放置任何区域
     - 每个区域都是 ``PENDING``
   * - ``"Root.Job{A: [done]}"``
     - ``A`` 是 ``DONE``
     - 其余区域是 ``PENDING``

写出的分支被直接放到位，不执行任何 ``enter``\ 。被省略或写成 ``[init]`` 的区域是 :math:`\mathsf{PENDING}`\ ，在第一个周期里按书写顺序、在前面区域留下的值上启动。第 1 节的帧约束只在保存整个起点位置的那一帧允许 :math:`\mathsf{PENDING}`\ 。

.. literalinclude:: start_motion_on.fbmcq
   :language: fbmcq

查询让 ``Motion`` 从 ``On`` 开始，并要求到达完整的配置。

.. literalinclude:: hot_start.demo.sh.txt
   :language: text

轨迹从 ``Controller.Running{Safety: [init], Motion: On}`` 开始。第 0 步有两行：\ ``Running: [start] -> Safety.Watching [initial]`` 启动等待初始化的区域，\ ``Motion: On -> On [fallback]`` 运行 ``Motion`` 的 ``during``\ 。没有任何一行进入 ``Motion``\ ，因为它是被直接放到位的。

让某个拥有者的全部区域都已完成的起点会在编译查询时被拒绝，因为没有任何帧可以保存这个位置（\ :eq:`eq-region-position-domain` 的第三行）。这是负例；查询是有意被拒绝的。

.. literalinclude:: hot_start_refused.demo.sh.txt
   :language: text

诊断码是 ``invalid_start_position``\ ，退出码为 1，不写出 JSON 结果。不是模型中位置的配置文本（例如 ``Root.Job{A: Nope}``\ ）也用同一个诊断码拒绝，而指向不存在状态的普通路径用 ``unknown_state`` 拒绝。

6. 模式与调用快照观察机器，而不构造它
-------------------------------------

带配置文本的 ``active("...")`` 是一个\ **模式**\ （pattern）。写出的区域必须在文本所说的位置；省略的区域不受约束。对写出区域集合为 :math:`W` 的模式 :math:`\pi`\ ，它在位置 :math:`p` 上的谓词是

.. code-block:: text

   in(O) 且对每个写出的区域 i：
       at(R_i, 模式_i)   [done]  ->  p_i = DONE
                         [init]  ->  p_i 是 PENDING 或 INACTIVE
                         状态    ->  嵌套的模式

其中 ``in(O)`` 是普通的 ``active(O)``\ 。与起点的差别在于方向：起点\ *构造*\ 一个位置，所以它省略的区域等待初始化；模式\ *匹配*\ 一个位置，所以它省略的区域可以在任何地方。由 ``init state(...)`` 文本构造出的位置总是匹配同一段文本写成的模式。

不是模型中位置的模式会在编译查询时被拒绝，诊断码是 ``invalid_active_pattern``\ ：语法错误、未知状态、状态并不拥有的区域，或同一个区域写了两次。

在调用过滤器的 ``where`` 里，\ ``active(...)`` 描述的是调用那一刻的整台机器，而不是周期结束时的机器。位置就是处理函数作为 ``ctx.configuration`` 收到的那一份：

* 同一周期里先行动的区域显示它的新位置；
* 还没有启动的区域显示 ``[init]``\ ；
* 同一周期里拥有者被重新进入时，进入的调用看到每个区域都是 ``[init]``\ ，而退出与切面的调用仍然看到原来的位置。

``called`` 与 ``call_count`` 也会把一组区域结束时结算的 ``>> during after`` 调用，按仿真器告诉处理函数的状态来统计：切面包住整组时是拥有者，位于下面时是叶子（\ ``test/bmc/test_region_call_records.py`` 中的 ``test_an_aspect_over_a_group_reports_the_owner_and_over_a_region_its_leaf``\ ）。下一个脚本的模型进入 ``O``\ ，让两个区域结束，并在第二步里再次进入 ``O``\ 。

.. literalinclude:: reenter.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: call_snapshots.demo.sh.txt
   :language: text

成对地看。第 0 步里 ``Q``\ （区域 ``B``\ ）的进入看到 ``A`` 已经在 ``P``\ ：\ ``A`` 先行动。第 0 步里 ``P`` 的进入看到 ``B`` 是 ``[init]``\ 。第 1 步里拥有者在两个区域都结束之后再次被进入：\ ``P`` 的进入看到 ``B`` 是 ``[init]`` 而不是 ``Q``\ ，\ ``P`` 的退出仍然看到 ``B`` 在 ``Q``\ 。每一对里有一条可实现、一条不可实现的查询，所以这个答案是编码的性质，而不是求解器碰巧选出的那一个见证的性质。

7. 见证，以及回放比较什么
-------------------------

解码出的见证保持公开的结构，并增加可选的区域字段，不含区域的模型里没有这些字段。

* 每一帧带有 ``configuration``\ ，与仿真器里 ``str(configuration)`` 给出的文本相同（初始帧没有）。
* 每一步带有 ``local_cases``\ ，每条运行过的路径一项，顺序与仿真器运行它们的顺序相同。每项有 ``scope``\ （路径运行所在的拥有者或区域，在所有区域之外时为 ``null``\ ）、\ ``kind``\ （\ ``initial``\ 、\ ``transition`` 或 ``fallback``\ ）和 ``label``\ 。
* ``case_label`` 是在所有区域之外运行的那条路径的标签，没有这样的路径时为 ``null``\ 。区域内部的分支只在 ``local_cases`` 里报告。
* 抽象调用带有调用那一刻的配置。

下一个脚本把工作查询里对调顺序的模型求解成 JSON，并用 :download:`show_witness.py <show_witness.py>` 打印见证的三个视图。

.. literalinclude:: witness_regions.demo.sh.txt
   :language: text

第 4 帧是反例帧：故障周期之后 ``Motion`` 是 ``On``\ 。第 2 步先列出进入 ``Running`` 的转换（\ ``scope=None``\ ），然后按书写顺序每个区域一条初始路径。第 3 步的 ``case_label=None``\ ，因为没有路径在区域之外运行，并且有两个局部分支：\ ``Motion`` 打开，\ ``Safety`` 回退。这个模型里 ``Motion`` 先写，所以它排在前面。

人读报告把同样的分支打印成轨迹里的行。作用域相对于一步的任一端、机器在所有区域之外停驻的那个状态来书写，所以不同拥有者之下的同名区域读起来不同；拥有者本身读作它自己的最后一段名字，\ ``[start]`` 代表进入一个作用域，\ ``[done]`` 代表已结束的区域。上面报告里的 ``Running: [start] -> Motion.Off [initial]`` 就是区域 ``Motion`` 作为拥有者 ``Running`` 的一部分被进入。

回放把见证交给 ``SimulationRuntime`` 运行，对含区域的模型，在 :doc:`/explanations/bmc_solving/index_zh` 列出的比较之外还比较：每一帧的配置，每一步提交的转换（这就是检查 ``case_label`` 与 ``local_cases`` 的方式），以及每个抽象调用的配置。输出的最后一行显示 ``replay ok=True mismatches=0``\ 。不一致不是关于模型的结论；它意味着编码与仿真器有分歧，命令行会报告 ``EVIDENCE/REPLAY MISMATCH; RESULT UNTRUSTED``\ ，退出码为 4。回放成功是见证确为真实执行的证据，而不是编码完备的证明。

8. 构造在哪里停下
-----------------

编码不做近似。无法构造有界公式的地方，它会报错。

在同一周期里再次进入自己的组，是关系选择展开而不是直接拒绝的形状。拥有者 :math:`O` 有一条回到自己的转换，在它的区域结束之后立刻触发，就会在第一次进入留下的值上重新进入。编码保存一份当前路径上正在判定的进入列表 :math:`\mathcal{E}`\ ，并应用两条规则：

.. math::
   :label: eq-region-group-reentry

   \begin{aligned}
   \bigl(\exists\,(O,\eta')\in\mathcal{E}:\ \eta'\equiv\eta\bigr) &\Rightarrow
     \mathrm{Accept}_O(\eta)=\bot,\\
   \bigl|\{\,(O',\eta')\in\mathcal{E} : O'=O\,\}\bigr|\ \ge\ L &\Rightarrow
     \mathrm{BuildError}.
   \end{aligned}

第一条规则识别循环：同一个拥有者在完全相同的符号值上再次被进入，什么也改变不了，所以这条路径被拒绝，仿真器也是这样拒绝它的。这里的 ``\equiv`` 指符号表达式完全相同，而不只是数值相等。第二条规则限制展开：路径上同一个拥有者已经被进入 :math:`L` 次时，构建会抛出 ``BmcBuildError``\ ，而不是猜测。\ :math:`L` 就是 ``BmcOptions.max_group_reentries``\ ，默认 16。

第一个模型在每一圈里改变 ``n``\ ，六圈之后停止。它需要七次进入，所以默认的 16 能构建它。

.. literalinclude:: laps.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: spin.fbmcq
   :language: fbmcq

下一个脚本通过 Python 接口用三个上限构建公式。命令行没有设置这个上限的选项。

.. literalinclude:: group_reentry.demo.py.txt
   :language: text

7 允许六圈，默认值也允许；6 少一次，错误里写明了拥有者、上限和选项。第二个模型 ``spin.fcstm`` 用输入来限制圈数，所以任何上限都不够。通过命令行，同一个错误表现为意外错误横幅和退出码 1，因为命令目前还没有把这个构建错误转成受控的诊断。这是负例；不要照抄这个模型。

.. literalinclude:: spin.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: group_reentry.demo.sh.txt
   :language: text

另有三个上限与它无关。

* 一个查询表达式最多嵌套 100 层。更长的链会在构造任何东西之前以 ``expression_too_deep`` 被拒绝；请把它拆到几条 ``assume`` 或 ``check`` 子句里。
* 宏步展开器有区域继承来的固定保护，没有任何选项能改变它们：一条路径上至多 1000 个微步，栈深度 64。它们限制的是穿过一个单元的一条路径。本页不就区域能嵌套多深做任何声明。
* 宏步展开器会拒绝在执行动作的同时回到某个状态的路径，也就是依赖动作的循环；仿真器在运行时抛出的搜索上限没有对应的有界形式。因此在声明了区域的共享语义用例里，四个搜索上限用例、三个依赖动作的循环用例和一个超出展开深度的重入用例被排除在与仿真器的差分检查之外。另有四个区域用例因其他原因被排除：两个需要调用者完整给出变量的热启动，两个需要查询语言从不使用的短事件名。

.. literalinclude:: expression_depth.demo.sh.txt
   :language: text

五十项能构建，性质成立；一百五十项在编译时被拒绝，退出码为 1，没有轨迹。

9. 与仿真器已知的差异
---------------------

关系要求被选中路径上的每个操作都有定义，所以仿真器抛错的周期在那里没有解。有两类求值不同：仿真器还会求值之后走进死路的候选路径上的操作，以及被更高优先级的续接胜过的、已结束的一组的低优先级续接，并在它们失败时抛错。关系不要求它们有定义，所以在仿真器抛错的周期上，核心公式仍然可以满足。走进死路这种形状并不只属于区域：运行时安全阶段在不含区域的模型里也报告同样的形状。

运行时安全阶段就是弥补这个缺口的阶段，默认在性质之前运行。它把各周期再降低一次，以定位每个区域的每个操作，包括没有被选中的候选的探测，以及起不来的区域的操作。下一个脚本运行两个模型：\ ``dead_end.fcstm`` 里一个候选通向伪状态，它的效果用输入做除数；\ ``outranked.fcstm`` 里一个低优先级续接的条件用输入做除数。第三条命令关闭这项检查。

.. literalinclude:: dead_end.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: outranked.fcstm
   :language: fcstm
   :linenos:

.. literalinclude:: known_differences.demo.sh.txt
   :language: text

默认情况下两个模型都报告 ``RUNTIME ERROR REACHABLE WITHIN BOUND``\ ，退出码为 5，并给出失败的操作和运行时复现了该错误的确认。使用 ``--no-runtime-safety`` 时，\ ``dead_end.fcstm`` 上的性质查询找到了见证，回放抛出仿真器自己的错误：命令行打印意外错误横幅，退出码是 1 而不是 4。只有在确认模型不会除以零或越界时才关闭这项检查；之后的结果依赖这个假设。

10. 公式台账
------------

下表是本页五条公式的正向审计图。除非另有说明，名字指 ``pyfcstm/bmc/region_relation.py``\ ；测试在 ``test/bmc/test_region_relation.py``\ ；查询运行在上面展示的模型上。

.. list-table:: 区域公式台账
   :header-rows: 1
   :widths: 18 22 24 18 18

   * - 公式
     - 实现锚点
     - 测试锚点
     - 工作查询
     - 轨迹
   * - :eq:`eq-region-position-domain`
     - ``region_frame_constraints``\ 、\ ``_owner_resting``\ ；\ ``relation.py`` 中的 ``BmcTraceSymbols.region_position``
     - ``test_a_resting_owner_never_has_every_region_done``\ 、\ ``test_regions_are_inactive_exactly_while_their_owner_does_not_rest``
     - ``interlock.fbmcq``
     - 第 1 节第 0 帧到第 4 帧的位置
   * - :eq:`eq-region-value-chain`
     - ``_StepBuilder.advance_group``\ 、\ ``region_env``
     - ``test_the_earlier_region_decides_before_the_later_one_looks``\ 、\ ``test_swapping_the_regions_delays_the_stop_by_one_cycle``
     - 两种顺序下的 ``interlock.fbmcq``
     - 第 3 步交接的值（第 2 节）
   * - :eq:`eq-region-owner-start`
     - ``_StepBuilder.entry``\ （\ ``ok`` 与续接检查）
     - ``test_regions_start_in_declaration_order_on_the_values_left_behind``\ 、\ ``test_a_group_that_cannot_start_leaves_a_cold_start_delta``
     - ``blocked_free.fbmcq``\ 、\ ``blocked_stuck.fbmcq``
     - ``g == 0`` 时的两个 ``[delta]`` 步（第 3 节）
   * - :eq:`eq-region-joint-completion`
     - ``_StepBuilder.done_viable``\ 、\ ``build_owner_source``
     - ``test_the_last_region_may_finish_only_if_the_owner_can_continue``\ 、\ ``test_once_the_owner_can_continue_the_finish_and_the_hand_over_are_one_cycle``
     - ``joint_all_done.fbmcq``\ 、\ ``joint_blocked_next.fbmcq``
     - 第 4 节的五条标题行
   * - :eq:`eq-region-group-reentry`
     - ``_StepBuilder.entry``\ （\ ``_entering``\ ）、\ ``BmcOptions.max_group_reentries``
     - ``test_the_depth_a_group_may_re_enter_itself_is_an_option``\ 、\ ``test_a_loop_that_no_value_can_stop_cannot_be_bounded``
     - ``laps.fcstm`` 与 ``spin.fcstm`` 上的 ``spin.fbmcq``
     - 第 8 节的三个上限

Sphinx 检查引用能否解析，漂移检查比较中英文页面的标签与 LaTeX。两者都不能证明这些论断。审阅者必须把每一行与代码、测试和轨迹逐一对照。

本页确立了什么，没有确立什么：

* 事实，由上面的查询展示：书写顺序改变联锁查询的结论；三个位置标记出现在公式所说的地方；起不来的区域会拒绝冷启动；没有续接时最后一个区域被拒绝；两个上限和两处已知差异的表现与打印出来的一致。
* 事实，由测试而不是本页的运行展示：台账以及第 4 节、第 6 节点名的测试，例如切面包住一组时告诉处理函数的状态。
* 推断：编码在共享语义用例和随机差分模型都不包含的形状上也与仿真器一致。差分检查是证据而不是证明，每个见证的回放是第二道防线。
* 本页不涉及：求解耗时怎样增长，见 :doc:`/explanations/bmc_scaling/index_zh`\ 。

另见
----

* :doc:`/explanations/bmc_semantics/index_zh` 推导不含区域的模型的关系，本页建立在它之上。
* :doc:`/explanations/bmc_solving/index_zh` 讲求解、结论、见证与回放。
* :doc:`FBMCQ 参考 </reference/bmc_query/index_zh>` 记录本页的 ``active`` 模式、\ ``init state`` 与诊断码。
* :doc:`/explanations/region_semantics/index_zh` 定义编码所遵循的周期。
