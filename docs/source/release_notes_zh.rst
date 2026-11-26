版本说明
========

未发布
------

区域
~~~~

这个版本给 FCSTM 增加了\ **有序并行区域**。一个状态可以包含若干 ``region`` 块，而不是普通子状态。这些区域同时活动，每个周期里按书写顺序依次执行。想看它运行，请跟着 :doc:`/tutorials/regions/index_zh` 操作。

**语言。**

- ``region Name { ... }`` 写在状态内部。一个状态要么包含普通子状态，要么包含区域，不能两者都有，也可以只有一个区域。区域可以嵌套：区域里的状态可以再拥有区域。
- 区域里可以写初始转换、子状态、普通转换和强制转换、``event`` 声明以及 ``>> during before/after`` 切面。不能写 ``enter``、``during``、``exit`` 和变量声明，区域本身也不是转换的源或目标。同一个状态的两个区域不能重名，模型错误是 ``Duplicate region 'A' in R.``。
- ``region`` 与 ``active`` 是保留字。把它们用作状态名、事件名或变量名的模型需要改名。
- 书写顺序就是执行顺序，也是模型含义的一部分。靠后的区域能看到靠前区域在同一周期里产生的值和状态；靠前的区域不会因为靠后区域写了什么而重新执行。多个区域写同一个变量时，最后一次写入生效。
- 转换不能从一个区域通向另一个区域，拥有者之外的转换也不能直接通向区域内部。进入拥有者，让每个区域从自己的初始转换开始。
- 写在区域内部的 ``X -> [*]`` 表示该区域已完成。拥有者的最后一个区域完成时，拥有者在同一周期里继续走自己的转换；机器不会停在所有区域都已完成的位置。
- 写在拥有者上的强制转换，例如 ``!Running -> Idle : /Stop;``，一次带走整组。它按下文\ *强制转换*\ 一节所述展开成普通的 ``-> [*]`` 转换。
- 区域里声明的事件属于该区域，所以两个区域可以用同一个事件名表示不同的事件。多个区域要共用一个事件时，使用从根开始的路径（``/Owner.Region.Event``）。
- ``active("State.Path")`` 是只读查询，可以出现在任何能写条件的位置。

**哪些环节支持区域。**

- 模拟：冷启动、热启动、依赖位置的短事件名和 ``pyfcstm simulate``，见下文\ *含并行区域模型的模拟*。位置是一棵树，显示为配置文本，例如 ``Controller.Running{Safety: Watching, Motion: On}``。
- ``pyfcstm inspect`` 在摘要里报告区域，并新增两条与顺序有关的诊断。``I_REGION_BACKWARD_READ`` 是提示级诊断：靠前的区域读取了靠后区域写入的变量，或查询了靠后区域的状态，因此看到的是上一个周期的值。它描述的是既定行为，不是缺陷。``W_REGION_BLIND_OVERWRITE`` 是警告：靠后的区域每个周期都无条件覆盖靠前区域写的变量，而且没有用到旧值，所以靠前的写入必然丢失。靠后的区域可能读到旧值、写入有条件、能够完成或含抽象动作，或者中间的区域读了该变量时，两条都不报。
- ``pyfcstm.verify`` 与 inspect 的可达性分析按分支判断拥有区域的状态（见下文\ *检查与验证*）。
- ``pyfcstm bmc`` 与 ``pyfcstm.bmc`` 接受含区域的模型，包括见证、回放和运行时安全检查（见下文\ *区域的有界模型检查*）。
- 内置模板 ``python``、``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 生成的运行时按模拟器的方式运行含区域的模型，见下文\ *模板与能力声明*。
- PlantUML 与图形查看器把区域画成并发区域（PlantUML 里称为分区；见下文\ *区域的画法*）。
- VS Code 扩展可以预览含区域的模型，折叠 ``region`` 块，并在编辑时报告 ``E_REGION_STRUCTURE``、``E_DUPLICATE_REGION`` 和 ``E_ACTIVE_QUERY_TARGET``。
- 随包发布的两份大语言模型指南，即 FCSTM 语法指南与 FBMCQ 语言指南，都介绍了区域。

**怎样开始。** :doc:`/tutorials/regions/index_zh` 带你用一个控制器依次走过模拟、区域顺序、检查、有界模型检查、生成和画图。任务做法见 :doc:`/how_to/regions/index_zh`，原因见 :doc:`/explanations/region_semantics/index_zh` 与 :doc:`/explanations/region_design/index_zh`，确切规则见 :doc:`/reference/region_model/index_zh`。

**已知限制。**

- 区域里两条强制声明竞争时，先到的一条占住整组，区域里的叶子也不让位。这与不含区域的模型不同，见 `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_。
- ``pyfcstm inspect`` 的行为类诊断不应随语法糖是否展开而变化，见 `issue #588 <https://github.com/HansBug/pyfcstm/issues/588>`_。
- 编辑器预览对历史的画法与 Python 的图形快照不同，见 `issue #590 <https://github.com/HansBug/pyfcstm/issues/590>`_。``I_REGION_BACKWARD_READ`` 与 ``W_REGION_BLIND_OVERWRITE`` 只由 ``pyfcstm inspect`` 报告，编辑器不报。
- 生成的运行时还可以更小更快。Python 模板记录在 `issue #596 <https://github.com/HansBug/pyfcstm/issues/596>`_，C 系模板记录在 `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_。
- 有界模型检查的代价随区域数与上界增长；`issue #600 <https://github.com/HansBug/pyfcstm/issues/600>`_ 记录了在公式构造与求解上探索过的方向。

模板与能力声明
~~~~~~~~~~~~~~

模板在 ``config.yaml`` 的 ``features`` 列表里声明自己能渲染什么；目前唯一的成员是 ``region``，``StateMachineCodeRenderer.features`` 返回这个列表。五套内置模板都声明了它。把含区域的模型交给没有声明的模板（包括自定义模板目录）时，会在写出任何文件之前以 ``E_UNSUPPORTED_FEATURE`` 拒绝。``pyfcstm generate`` 的报错信息会说明模型声明了几个区域、模板作者应当声明什么，以及模型可以改用哪些内置模板。

生成的 Python 运行时对所有模型有这些变化：

- 不含区域的模型，生成文件的文本会变，行为不变。
- ``vars`` 是只读视图。持久值只能通过模型或热启动参数写入。
- ``variables`` 别名已删除，请改用 ``vars``。
- ``ABSTRACT_HOOKS`` 是只读映射。
- ``configuration`` 以文本给出完整位置，与模拟器打印的文本逐字节相同；``leaves``、``is_active(path)``，以及含区域的模型上的 ``region_status(path)``\ （``live``、``done``、``pending`` 或 ``inactive``）用来查询位置。``initial_state`` 接受配置文本、点路径或元组。
- 含区域的模型没有 ``current_state_path`` 与 ``current_state_name``，读取它们会得到 ``AttributeError``。抽象动作的上下文也带有 ``configuration``。

C 系运行时（``c``、``c_poll``、``cpp``、``cpp_poll``）现在运行在为每个模型生成的静态内存内核上，不使用堆，也没有第三方依赖，含区域与不含区域的模型都一样。对所有模型：

- 机器类型是不透明的。``MAX_STACK_DEPTH`` 与 ``MAX_DFS_STEPS`` 已删除，由公开宏 ``..._ARENA_CAPACITY``、``..._TRAIL_CAPACITY`` 和 ``..._STORAGE_BYTES`` 取代；运行超出容量时以安全上限类错误失败，并点出宏名。
- 新增 ``hot_start_at``、``hot_start_at_with_parameters`` 和 ``get_configuration``，配置值可以查询、校验，并格式化成与模拟器相同的文本；文本解析可以用 ``PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT`` 关掉。C++ 包装增加了对应成员以及 ``operator==`` / ``operator!=``。
- 含区域的模型没有 ``current_state_id``、``current_state_path`` 和 ``current_state_name``，使用它们是编译错误。
- 不含区域的模型，生成文本会变，行为不变。
- 不含区域的模型也运行在同一个内核上，所以生成机器的代码体积、内存与第一个周期的耗时同样会变化。相对旧模板的体积与速度比值及其测量方法，见 :doc:`/explanations/region_performance/index_zh` 的“生成的 C 运行时”一节；剩余的代价记录在 `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_。

区域的画法
~~~~~~~~~~

``pyfcstm plantuml`` 把一个状态的区域画成用 ``--`` 隔开的并发区域。每个区域以一条 ``region N: Name`` 注释开头，\ ``N`` 按书写顺序从 1 数起，因为 PlantUML 的分区本身没有名字（这里的并发区域在 PlantUML 里就是这种分区）。\ ``active("Path")`` 按书写原样显示，隐藏标志与自动写入不画出来。

``StateMachine.diagram()``、``pyfcstm diagram`` 与 HTML 查看器把同一拥有者的区域在它的外框内并排放置，用虚线隔开，区域没有自己的边框，标题同样是 ``region N: Name``。顺序沿布局方向排开：自上而下的图里从左到右，自左向右的图里从上到下。折叠、详情与导出对区域和对状态一样可用，区域对 ``max_depth`` 算一层。查看器不高亮当前配置。图的 JSON 用 ``"region": true`` 标记每个区域节点。

强制转换
~~~~~~~~

来源状态 ``S`` 内部还有状态的强制转换（forced transition）\ ``!S -> T``\ ，现在在所有模型里按同一种方式执行：事件和条件只在状态机停驻的那个状态上判断一次，向上退出的途中不再重新判断。此前的版本会在 ``S`` 之下的每个状态上各放一份事件和条件的副本，伪状态（pseudo state）也不例外，并在退出逐层上行时把每份副本重新判断一遍。不含强制转换的模型不受影响。含强制转换的模型有四类行为变化：

- **条件引用来源状态内部的状态。**\ ``!P -> Q : if [active("Root.P.a2")];``\ 在状态机停驻于 ``a2`` 时成立并被执行。此前它会在 ``a2`` 已经退出之后再判断一次，而那时条件不可能成立。
- **退出动作改掉了条件读取的变量。**\ 条件不会在途中的退出动作执行之后再判断，所以退出动作不能在半途取消这条转换、让状态机留在原来的状态。
- **进入途经伪状态。**\ 强制转换不会从伪状态上发起。如果在经由伪状态进入 ``S`` 的那个周期里它的事件或条件已经成立，现在会先完成进入，强制转换在下一个周期执行。
- **目标无法进入。**\ 此时强制转换什么都不做：它不会离开状态机停驻的状态，也不消费事件，离开 ``S`` 的其他转换也不会在半途接手。停驻状态自己的转换照常参与判断。

``CycleResult.consumed_events``\ 里，强制转换的事件只列出一次；此前每离开一层就列出一次。

强制转换的来源状态内部有区域（region）时，每个区域都由普通的 ``-> [*]`` 转换结束，这些转换语言本来就有，没有任何东西一次带走整组。区域内每个可以停驻的状态得到两条：一条是带声明事件和条件的发起转换，它置起隐藏变量；排在它前面的是跟随转换，它只等待这个变量。区域按书写顺序推进，所以第一个其状态看到事件和条件成立的区域置起变量并结束，排在它后面的每个区域在同一个周期里看到变量就结束。最后一个区域结束时，拥有者像处理任何已经完成的组一样，通过自己的转换继续。由此有三点：

- **区域按书写顺序离开。**\ 第一个区域的退出动作先执行，嵌套的拥有者在自己的区域之后离开，最外层拥有者最后退出。
- **条件在区域运行的过程中变为成立。**\ 排在使条件成立的那个区域后面的区域，在同一周期里就看到它并立刻结束；排在前面的区域在下一个周期结束。
- **目标无法进入。**\ 已经结束的区域保持结束，最后一个区域带着被置起的变量继续工作，在目标第一次可以进入的周期里整组离开。同一个拥有者的两条声明竞争时，先被置起的那条占住整组，另一条在此期间不会被尝试；这与不含区域的模型不同，那里目标无法进入时轮到下一条声明。

在上述所有情形里，\ ``to_ast_node()``\ 的文本加载得到的都是同一台状态机。

有三样东西变得可见：

- 每条这样的声明用一个隐藏的 ``int`` 变量 ``__forced_<n>`` 来执行；模型已经用掉的名字会被跳过。它和 ``__hist_*`` 一样出现在 ``StateMachine.defines``\ 、\ ``runtime.vars``\ 、抽象处理器的变量快照和生成代码的变量表里，并且在所有地方都是普通变量：热启动（hot start）像对待其他变量一样要求提供它，BMC 也像对待其他变量一样对待它。状态机只在一个周期内部把它置起，所以每一个停驻点上它都是 0。\ :attr:`pyfcstm.model.model.StateMachine.forced_variables`\ 给出这些名字。
- 处在强制退出途中的状态上，带事件的转换会经由一个生成的伪状态 ``__forced_gate_<n>`` 拆成两步。这个伪状态出现在 ``walk_states()`` 里，在执行轨迹中表现为多经过一个状态。
- ``to_ast_node()``\ 导出实际运行的状态机，包含上述变量和伪状态，与历史的现有做法一致。从导出文本加载的模型就是同一台状态机：逐周期行为相同，热启动相同，每个可达性和 BMC 问题的答案也相同。强制转换触达区域的模型也是如此。

PlantUML、图形查看器和 ``pyfcstm inspect`` 仍然把一条强制转换展示为它作用到的每个状态上各一条转换。对含任何强制转换声明的模型（包括来源状态是叶子的），它们展示的是加载时的模型：加载之后再修改模型对象，改动不会出现在这些展示里。来源状态内部没有任何状态的声明保持为每个来源状态一条转换，也不产生隐藏变量。在收集模式（\ ``parse_dsl_node_to_state_machine(..., collect=True)``\ ）下，一条写错的强制转换声明只报告一次，不再按展开的层数重复报告。

实际运行的状态机上没有任何强制转换声明的痕迹：它的转换都不带 ``Transition.is_forced`` 标记，也没有 ``forced_origin``。它就是普通的 FCSTM，所有执行它、或回答与它有关的问题的环节，包括仿真器、生成的运行时、BMC、\ :mod:`pyfcstm.verify`\ 里的分析和 :mod:`pyfcstm.diagnostics.analyzers`\ 里的分析器，都按它本来的样子处理，会遇到生成的转换和门状态 ``__forced_gate_<n>``，自己用 ``walk_states()`` 和 ``State.transitions`` 遍历的代码也一样。标记只存在于按书写的模型里，图形和 :func:`pyfcstm.diagnostics.inspect.inspect_model`\ 就是从它构建的，所以针对声明本身的告警，例如 ``W_FORCED_GUARD_UNSAT``\ ，来自 inspect 报告；单条转换的算法 ``forced_guard_unsat_under_init`` 也只会报告被传入时带着标记的转换。

如果代码把含强制转换的模型的 ``StateMachine.defines``\ 、\ ``walk_states()``\ 或导出的 DSL 文本与保存的期望值比较，需要更新期望值。从 ``runtime.vars`` 取得的热启动快照要连同其中的 ``__forced_*`` 项一起保存和提供，与其他变量一样。

区域的有界模型检查
~~~~~~~~~~~~~~~~~~

:func:`pyfcstm.bmc.build_bmc_core_formula`\ 现在可以描述含区域（region）的模型。拥有区域的状态在一个周期里按书写顺序依次推进各个区域，每个区域接着前一个区域留下的值继续，公式的规模随区域个数相加，不随各区域路径个数相乘：

- 每个区域在每一帧里有一个位置符号，取值是它的分支停驻的状态，或者区域结束后的 ``REGION_DONE_ID``\ ，或者拥有者没有停驻时的 ``REGION_INACTIVE_ID``\ ；\ ``BmcTraceSymbols.region_position``\ 给出它；
- 启动拥有区域的状态会按顺序启动每个区域，任何一个区域起不来，整个进入就失败，冷启动时报告为 Delta；
- 最后一个区域只有在拥有者能在同一周期继续时才可以结束；
- ``>> during`` 切面和拥有区域的状态上的普通 ``during before``\ ，按仿真器运行它们的方式编码。

热启动、\ :func:`pyfcstm.bmc.compile_bmc_property`\ 、\ :func:`pyfcstm.bmc.check_runtime_safety`\ 和 ``pyfcstm bmc`` 现在也接受这类模型：

- ``init state("...")`` 可以写配置文本，例如 ``Controller.Running{Safety: Watching, Motion: On}``\ ，也可以写区域内某个状态的路径，或者只写拥有者的路径。省略的区域，或者写成 ``[init]`` 的区域，在第一个周期里等待启动（\ ``REGION_PENDING_ID``\ ）。让某个拥有者的全部区域都处于完成状态的起点会被 ``invalid_start_position`` 拒绝；
- ``called`` 与 ``call_count`` 统计各区域的抽象调用；运行时安全检查覆盖每个区域的运算，包括没有被选中的候选的探测；起不来的区域让整个周期成为 Delta，位置与变量保持不变；
- 见证帧带有可选的 ``configuration`` 文本，区域步带有 ``local_cases``\ （\ ``scope``\ 、\ ``kind`` 与 ``label``\ ），抽象调用带有调用时刻整台机器的配置。步的 ``case_label`` 是在所有区域之外运行的那个分支的标签，没有这样的分支时为 ``null``\ 。回放比较配置、变量、事件、输入和调用，还会把每一步提交的转换与仿真器提交的转换逐一比较，分支标签正是靠它检查。人类可读报告里每个区域步占一行，局部分支的作用域按所属拥有者写成相对路径。新增的 JSON 字段都是可选的，不含区域的模型不会出现；
- 区域组结束时才结算的 ``>> during after`` 切面调用，按仿真器告诉其处理函数的状态统计，所以 ``call_count(..., state=...)`` 与 ``active_leaf=`` 和仿真运行逐次调用一致；
- ``active("...")`` 接受配置文本作为\ *模式*\ （见 :doc:`FBMCQ 参考 </reference/bmc_query/index_zh>`\ ）：写出的区域必须在所写的位置，省略的区域不受约束；允许 ``[done]`` 与 ``[init]``\ ，拥有者可以嵌套。在调用过滤的 ``where`` 里，它描述调用发生那一刻的整台机器。不是模型位置的模式会被 ``invalid_active_pattern`` 拒绝；单个表达式嵌套超过 100 层会被 ``expression_too_deep`` 拒绝，而不是耗尽 Python 栈。

在变化的取值上重入自身的组，会被展开到 :attr:`pyfcstm.bmc.BmcOptions.max_group_reentries` 次（默认 16）；需要更多时抛出 :class:`pyfcstm.bmc.BmcBuildError`\ ，而不是被近似，调大这个选项即可提高上限。不含区域的模型生成的公式与以前相同。

历史与 ``active()``
~~~~~~~~~~~~~~~~~~~~

历史和 ``active()`` 的隐藏变量同样是普通变量，所以模型和它导出的文本在每个环节的行为都相同：

- 热启动不再检查 ``__hist_goto`` 和各个 ``__hist_*`` 记录的取值，BMC 查询里放开（havoc）的起点也不再被限制在执行能取到的值之内。给什么值，状态机就按什么值运行；\ ``StateMachine.history_variables()``\ 仍然可以算出合法的值。BMC 约束组的类别 ``domain.history_variable`` 不再存在。
- 用到 ``active()`` 的模型，热启动、\ ``pyfcstm simulate``\ 、代码生成、\ ``pyfcstm bmc``\ 和 ``pyfcstm.verify`` 的结构类算法都会接受。它的标志 ``__active_*`` 在热启动时和其他变量一样由调用方提供；\ ``StateMachine.active_variables()``\ 可以从位置算出它们。\ ``E_UNSUPPORTED_FEATURE`` 诊断码不再列出 ``active`` 这个特性，inspect 报告里也不再出现原因 ``active_query_unsupported``\ 。

检查与验证
~~~~~~~~~~

带 ``--enable-verify`` 时，验证流水线的发现（\ ``W_DEAD_GUARD``\ 、\ ``W_GUARD_TAUTOLOGY``\ 、\ ``W_EFFECT_SMT_NO_OP``\ 、\ ``I_EFFECT_GUARD_CONTRADICT``\ 、\ ``W_TRANSITION_SHADOWED``\ 、\ ``I_ENTER_DURING_CONTRADICT``\ 、\ ``W_COMPOSITE_INIT_INCOMPLETE``\ 、\ ``I_NONTRIVIAL_SCC``\ 、\ ``W_TOPOLOGICAL_NOEXIT``\ 、\ ``I_TOPOLOGICAL_NON_TERMINATING`` 和 ``W_EVENT_UNREACHABLE_EMIT``\ ）按实际运行的状态机判断。用到历史、\ ``active()`` 或强制转换声明的模型，和它导出的文本，因此给出相同的发现。报告本身以及所有描述“写成了什么”的发现仍来自按书写的模型，判断声明本身的 ``W_FORCED_GUARD_UNSAT`` 也是如此。\ ``active("...")`` 上的条件，与隐藏标志上的任何条件一样被判断，而不是被跳过。实际运行的状态机里的发现可以提到隐藏变量或生成的伪状态，也可以报告关于它们的事情：强制转换声明的中继转换把自己守卫读取的变量降下来，就是 ``I_EFFECT_GUARD_CONTRADICT``\ 。每一条这样的发现都指向它所降级自的声明、历史或被查询的状态。组合触发（combo trigger）仍然把关于它生成的守卫的发现，以触发项的身份通过 ``W_COMBO_*`` 诊断码报告。

``pyfcstm.verify`` 的结构类算法与 inspect 报告的可达性现在接受含区域的模型。复合状态按分支判断：拥有区域的状态每个区域一条分支，不含区域的复合状态是只有一条分支的情形，所以不含区域的模型是没有分支的特例。离开复合状态的普通转换，只有在它的某个子状态能到达 ``[*]`` 之后才会被执行；强制转换则从每个叶子出发。对不含区域的模型，inspect 报告因此有一处变化：所有子状态都无法离开的复合状态永远不会执行它的普通外出转换，它通向的状态由 ``W_UNREACHABLE_STATE`` 报告，这条转换在 ``unreachable_transition_reasons`` 里得到原因 ``owner_never_completes``\ 。仿真器本来就是这样运行的，此前的报告把这样的复合状态当成机器可以随意离开的状态。\ ``!S -> T`` 展开后加在 ``S`` 内部各状态上的退出，不算子状态自行离开；通过 ``Owner.[H]`` 进入的历史默认目标，与初始转移一样是分支的起点。jsfcstm 的 inspect 报告遵循同一规则。\ ``pyfcstm.verify`` 的算法判断的是实际运行的状态机，强制转换声明在其中是中继，所以它们仍是不看守卫的过近似：只有强制声明能把复合状态带去别处时，它后面的状态仍可能被它们列为可达。

``pyfcstm.verify`` 的求解器查询各自在独立的 Z3 上下文里运行。此前只要从共享上下文里取过一次模型，之后一条非线性查询的答案就可能从 ``sat`` 变成 ``unknown``\ ，结果因此取决于进程之前求解过什么。像 ``x ** y > 0`` 这样 Z3 无法判定的条件，现在每次都得到 ``unknown``\ 。

图形
~~~~

用到历史的模型按书写绘制。PlantUML 把进入历史的转换写成 ``Owner[H]`` 或 ``Owner[H*]``\ ，浅历史和深历史的默认目标各写成所有者描述里的一行 ``[H] -> Child`` 和 ``[H*] -> Child.Leaf``\ ，因为 PlantUML 画不了从一个有转换进入的历史出发的箭头。图形快照把这样的转换标成 ``Owner.[H]`` 或 ``Owner.[H*]``\ 。历史降级成的隐藏变量、门状态和路由转换不再绘制，强制转换声明本来就是这样。

含并行区域模型的模拟
~~~~~~~~~~~~~~~~~~~~

含并行区域（region）的模型现在可以热启动、用短事件名驱动，也可以用 ``pyfcstm simulate`` 运行。

\ **热启动。**\ ``SimulationRuntime(initial_state=...)`` 接受配置文本（例如 ``"Controller.Running{Safety: Watching, Motion: On}"``\ ）、\ :class:`~pyfcstm.model.configuration.Configuration`\ 、可以穿过区域的状态路径，或者状态对象。写出来的部分就位，不执行任何 ``enter``；没写出来的部分等待初始化，第一拍按书写顺序走各自的初始转移，其余部分照常工作：只写到普通复合状态而没写子状态的位置、被省略的区域（穿过区域的路径会让各层拥有者的其余区域都视为省略），以及只写拥有者路径的整组。写成 ``[done]`` 的区域保持完成。任一层拥有者的区域全部完成的位置会被拒绝。隐藏变量与其他变量一视同仁，需要调用方给全，不会按位置推导。

\ **事件名。**\ 完整路径与从根开始的写法在机器停在哪里都含义相同。依赖当前位置的写法（例如 ``Go``、``.Reset``\ ）原先在有多个活动叶子时一律被拒绝，现在对每个活动叶子各解析一次：没有叶子找到事件则报错；找到事件的叶子找到的是同一个事件则使用它；找到不同的事件则报歧义，并列出每个候选及其来源叶子。\ :meth:`pyfcstm.model.configuration.Configuration.resolve_event`\ 遵循同一规则。

\ **命令行。**\ ``pyfcstm simulate`` 不再拒绝含区域的模型。当前状态显示、多拍表格和历史里的位置都按配置文本显示；\ ``init`` 接受配置文本（\ ``init Controller.Running{Safety: Watching, Motion: On} permit=1``\ ）；事件列表与补全覆盖所有活动叶子，两个叶子用同名指向不同事件的短名不再被提示；\ ``init`` 能补全区域里的状态。不含区域的模型行为与此前完全一致。

不含区域的模型不受下面这些影响：热启动与事件名都与上一个版本相同。命令行有两处修正对所有模型生效：

- \ ``events`` 与 ``cycle`` 的补全只在“输入这个短名确实有效”时才显示短名。属于叶子上层的事件（复合状态、区域、拥有者）原先会被列成 ``Stop (Root.Run.Stop)``\ ，可 ``cycle Stop`` 却被拒绝；现在只列完整路径。
- \ ``init`` 拒绝同一个变量被赋值两次（``init S n=0 n=5``\ ），不再静默取最后一个，与 ``cycle --input`` 原有的行为一致。

花括号不平衡的 ``init`` 对所有模型都直接报告这一点。报错里的路径现在写成 ``'W.Nowhere'`` 而不是元组；多个叶子之间有歧义的事件名会直接报歧义并列出候选，不再放在“无法解析”的套话之后。

v0.6.0
------

本次次版本发布新增端到端的 FBMCQ 有界模型检查流程，使检查报告同时适合人类阅读和
大语言模型修复循环，将内置运行时模板扩展为 Python、C、C Poll、C++ 与 C++ Poll，
并交付大幅扩展的双语文档。本版本也包含公开 API 与 CLI 兼容性变化，调用方升级前
需要阅读迁移说明。

FBMCQ 与有界模型检查
~~~~~~~~~~~~~~~~~~~~~

- 新增 FBMCQ 性质语言、解析器、模型绑定、宏展开、转换关系编译器、Z3 求解流程与
  :mod:`pyfcstm.bmc` 公开 API。语言覆盖可达性、覆盖、安全性、有界活性、响应、
  假设与初始状态约束。
- 新增 ``pyfcstm bmc``，每次处理一份 FCSTM 模型和一条 FBMCQ 查询。默认终端报告
  先说明有界性质是否成立，再显示 SAT/UNSAT 求解诊断；支持可选 ANSI 颜色，并要求
  每一条解码后的 SAT 见证都通过结构校验与模拟器重放。
- 新增稳定的结构化 JSON 结果，供持续集成、工具和大语言模型消费，并在 BMC 结果协议
  参考中提供可下载模式。输出保留按极性解释的结论、求解耗时、见证与重放记录、诊断
  及对应进程退出状态。
- 新增中英文教程、任务指南、三篇数学解释和两篇完整参考。解释页推导 40 条带标签、
  可追溯到实现的公式，并通过 MathJax HTML 与 XeLaTeX PDF 验证。

检查与诊断
~~~~~~~~~~

- 将 ``pyfcstm inspect`` 默认输出改为检查器风格的人类报告，提供对齐的源码范围、
  相邻源码上下文、紧凑严重级别标签和 ``--color auto|always|never``。文件、管道和
  机器格式仍不包含 ANSI 转义序列。
- 通过 ``--format json`` 保留机器报告，并新增 ``--format llm-json`` 与
  ``--format llm-md``。大语言模型报告使用随当前发布版本提供的模式文件，包含源码上下文、
  来源、修复指导和明确禁止事项；公开载荷不包含产品级 schema 版本或状态字段。
- 在 LLM 报告的 ``summary.structure_statistics`` 以及完整报告的
  ``ModelInspect.structure_statistics`` 中新增描述性结构统计。比率以原始小数输出，
  空分母使用 ``null``，并记录转换密度和不可达总体的保守建议阈值。超出只记录元数据，
  ``W_UNREACHABLE_TRANSITION`` 会按 authored transition 聚合不可达原因；这些阈值仍只
  是元数据，不生成综合健康分数；Python API 和 CLI 均可覆盖或关闭这些阈值。
- 扩展静态与验证支持的诊断，包括数值和守卫推理；求解器支持的检查仍受既有显式启用
  与安全门控约束。
- 在完整 JSON/API 报告中新增 ``ModelInspect.verification`` 执行元数据，使消费者能够区分
  验证未启用、被策略排除、得到确定结果和无法判定，而不会把这些状态误当成新的模型诊断。
  human CLI 会显示紧凑的覆盖率及不确定原因；LLM 表达契约包含上述结构统计段。模式文件仍是
  随发布版本提供的契约，而不是载荷级版本标记。
- 新增隔离的多提供方修复评测，验证消费者在无法读取隐藏仓库上下文时，是否能定位、
  解释、修复真实诊断并完成重放。

模拟与运行时语义
~~~~~~~~~~~~~~~~

- 强化热启动、伪状态路由、深度优先搜索限制、栈稳定化、推测回滚、表达式短路、持久
  变量归一化、事件所有权、历史长度调整和终止状态查询。
- 新增 :class:`pyfcstm.simulate.CycleResult` 事件记账，并强化抽象处理器注册、装饰器
  扫描、执行上下文、命名动作引用、警告元数据和会话复制行为。
- 将 non-stoppable 热启动和伪状态无进展行为改为成功的 Delta 周期：合法的阻塞目标不再
  在构造器阶段被拒绝，第一次真实 ``cycle()`` 返回 ``delta=True``，并推进公开周期计数
  与 history 契约。
- 扩展共享语义用例语料，使模拟器和生成运行时按周期对齐状态、变量、事件、历史、
  回调与失败行为。

兼容性说明
~~~~~~~~~~

- 删除 BMC CLI、witness/native 结果中的产品版本字段，并将可下载结果模式改为无版本文件名。
  下游必须停止读取已删除字段并更新模式下载路径；标准 JSON Schema 的 ``$schema`` 方言 URI
  保持不变。

内置模板与 DSL
~~~~~~~~~~~~~~

- 在 ``python``、``c``、``c_poll`` 之外新增一等的 ``cpp`` 与 ``cpp_poll``
  内置模板。C 族模板使用 CMake 驱动的原生检查、模拟器对齐用例、封装冒烟测试和明确
  部署剖面，运行时核心不要求堆分配。
- 新增有序组合转换触发器，在同一周期组合事件项和守卫项。组合转换展开为可追溯的
  伪中继状态，同时保持源码元数据、守卫/效果顺序、回滚、PlantUML 输出、检查报告、
  仿真行为和生成运行时对齐。
- 新增模板测试套件检测与专用代表性/完整套件任务，使源码模板依赖和原生工具链覆盖
  失败关闭，同时避免每个普通变更都运行全部昂贵原生套件。

大语言模型提示词资源
~~~~~~~~~~~~~~~~~~~~

- 新增打包的 FBMCQ 编写指南和带完整性检查的公开 API：
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_for_llm`、
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_path_for_llm` 和
  :func:`pyfcstm.llm.get_fbmcq_language_guide_prompt_metadata_for_llm`。
- FCSTM 与 FBMCQ 指南 API 现在分别位于专用模块中，:mod:`pyfcstm.llm` 仍作为紧凑的
  公开导入入口。两份指南资源都使用由 ``make sha256`` 生成的相邻 SHA-256 文件。
- 新增独立的 FBMCQ 指南评测夹具，覆盖七类性质、完整源码与已知事实任务、预期结果
  检查、防空真检查、变异区分和轨迹重放。提供方原始记录仍是仓库证据，不进入包数据。

文档与发布产物
~~~~~~~~~~~~~~

- 按教程、任务指南、解释和参考重组双语文档，提供可运行示例，并为 DSL、仿真、检查、
  模板和 BMC 工作流提供专项内容。
- 新增双语 BMC 教程与任务指南、三篇数学解释和完整的查询/结果参考。解释页推导
  40 条带标签、可追溯到实现的公式，并通过 MathJax HTML 与 XeLaTeX PDF 验证。
- 通过隔离构建、XeLaTeX/CJK 字体检查、结构/内容校验、对抗性自检和完整目录/索引
  验证强化双语 Sphinx PDF 路径。GitHub Release 现在会在包、CLI 和 VSIX 之外附带
  经过验证的英文与中文 PDF 手册。

BMC 使用边界
~~~~~~~~~~~~

有界模型检查结果受查询中的 ``<= N`` 限制，不是无界证明。脚本必须消费 ``--json``，
不得解析人类文案、颜色或实时耗时。对于见证极性性质，SAT 表示找到见证；对于反例极性
性质，SAT 表示找到反例。调用方应读取性质结论或 ``result.outcome``，不能把 SAT 统一
当作成功。

验证与检查
~~~~~~~~~~~~~~

- 从 :data:`pyfcstm.verify.REGISTRY` 删除从未实现的
  ``bounded_reachability``、``symbolic_bfs``、``bounded_safety``、
  ``bounded_invariant`` 和 ``path_witness``。注册表现在只保留 14 个可调用的
  结构与局部 SMT 算法。
- 删除 verify 专用 taxonomy 值 ``bmc_search``、``k_unrollings``、
  ``k_unrollings_times_branching`` 和 ``bmc_unrolled``。BMC 查询与见证
  由 :mod:`pyfcstm.bmc` 提供，不经过验证或检查。

兼容性说明
~~~~~~~~~~

依赖上述旧注册表键或分类值的代码需要迁移到公开的
:mod:`pyfcstm.bmc` 查询 API。``inspect`` CLI 不再为了应用层拒绝而接收这些
BMC 专用值；Click 现在会把它们作为非法选项值处理，用法错误退出状态为 ``2``，
而不是以前的策略错误状态 ``1``。

``inspect`` 默认输出现在面向人类。解析旧默认 JSON 输出的脚本必须显式传入
``--format json``；大语言模型自动化应使用 ``llm-json`` 或 ``llm-md``，不能解析
人类报告。

五个内置模板仍标记为实验性。VSCode 扩展继续使用独立版本线，本 Python 包发布
不会将其版本改为 ``0.6.0``。

v0.5.0
------

本版本应作为次版本发布，而不是 ``v0.4.2`` 这类修订版本。
它增加了新的用户可见 API、CLI 能力、打包的 LLM 资源、接入验证能力的诊断、
DSL 条件表达式运算符，以及模拟器语义修复。已有模型升级前应先阅读兼容性说明。

验证与检查
~~~~~~~~~~~~~~

- 新增 :mod:`pyfcstm.verify` 包，作为原始验证算法、注册表元数据、复杂度分类
  和检查接入门控的公开入口。
- 新增面向守卫、效果、生命周期关系、转换遮蔽和组合状态
  初始化的 SMT 局部验证算法。
- 将检查命令允许调用的验证算法接入
  :func:`pyfcstm.diagnostics.inspect_model` 和 ``pyfcstm inspect`` CLI。
  默认检查分析路径仍不运行验证；需要通过 ``enable_verify=True`` 或
  ``pyfcstm inspect --enable-verify`` 显式启用。
- 增加复杂度层级、调用次数扩展方式和 SMT 超时转发的安全门控。BMC 风格
  搜索仍不进入自动检查路径。

诊断与 CLI
~~~~~~~~~~

- 结构化诊断目录扩展到 59 个代码：20 个 error、32 个 warning、7 个 info。
- 增加验证支持的诊断，同时保持默认检查路径为静态分析。
- 新增 ``pyfcstm inspect``，输出与 ``inspect_model(model).to_json()`` 对齐的
  稳定 JSON 报告。
- 保持 Python / jsfcstm 在规范化诊断码、严重级别和引用载荷上的
  诊断表面一致性，供编辑器集成复用。

LLM 语法指南
~~~~~~~~~~~~

- 新增 :mod:`pyfcstm.llm`，提供
  :func:`pyfcstm.llm.get_grammar_guide_prompt_for_llm`、
  :func:`pyfcstm.llm.get_grammar_guide_prompt_path_for_llm` 和
  :func:`pyfcstm.llm.get_grammar_guide_prompt_metadata_for_llm`。
- 将面向大语言模型的官方 FCSTM 文法指南打包为
  ``pyfcstm/llm/fcstm_grammar_guide.md``。
- 为文法指南提示词增加打包的 SHA-256 附属文件和运行时完整性校验。
  调用方如果确实需要检查损坏资源或开发态资源，可以选择将完整性失败降级为
  警告。
- 新增独立的 ``llm_eval/`` 夹具和报告，用于提示词质量验证。这些
  是仓库评测资料，不会打包进 PyPI 分发物。

模拟器与内置模板
~~~~~~~~~~~~~~~~

- 强化模拟器在推测回滚（speculative rollback）、热启动初始化（hot-start initialization）、
  事件归一化（event normalization）、生命周期动作引用（lifecycle action refs）、
  抽象处理器契约（abstract handler contracts）和周期边界（cycle boundary）行为上的语义。
- 增加模拟器与生成运行时对齐的语义用例语料（semantic fixture corpus）。
- 稳定生成的 Python 运行时元数据、回调回滚行为和表达式错误包装。
- 打包内置模板仍通过 ``pyfcstm generate --template ...`` 使用。当前打包模板为
  ``python``、``c`` 和 ``c_poll``；VSCode 扩展有独立版本线，本 Python 包
  发布不会把 VSCode 扩展版本改为 ``0.5.0``。

DSL 表达式运算符
~~~~~~~~~~~~~~~~

本版本为 ``cond_expression`` 增加三组可用于守卫条件和其他布尔表达式位置的
布尔运算符：

- ``A => B`` 和 ``A implies B`` 表示蕴含。规范化 DSL 写法是 ``=>``。
  蕴含是右结合，因此 ``A => B => C`` 表示 ``A => (B => C)``。
- ``A xor B`` 表示布尔异或。链式 ``xor`` 是左结合的布尔奇偶异或链，
  不是多个输入中恰好一个为真的“恰选一个”运算。
- ``A iff B`` 表示布尔等价，是布尔相等关系的可读写法。链式 ``iff`` 与布尔
  ``==``、``!=`` 使用同一相等关系优先级层。

兼容性说明
~~~~~~~~~~

``implies``、``xor`` 和 ``iff`` 现在是 DSL 保留关键字。已有状态机如果把这些
名字用作变量、状态或事件名，需要在使用本版本前先重命名。

``->`` 仍然是状态转换箭头，不是守卫条件中的蕴含运算符。请使用 ``=>`` 或
``implies``。

``^`` 仍然是数值位异或运算符。它可以出现在守卫中被比较的算术表达式里，例如：

.. code-block:: fcstm

   StateA -> StateB : if [(flags ^ 0xFF) == 0];

它不是布尔异或写法：

.. code-block:: fcstm

   StateA -> StateB : if [a > 0 xor b > 0];   // 有效
   StateA -> StateB : if [(a > 0) ^ (b > 0)]; // 无效
   StateA -> StateB : if [true ^ false];      // 无效

验证与检查 API 是本版本新增的公开能力。函数入口和 JSON 契约会作为稳定
接口维护，但精确诊断文案和求解器证据文本应视为诊断载荷，不建议
下游用字符串解析方式硬编码依赖。
