版本说明
========

v0.7.0
------

这个小版本给 FCSTM 增加了\ **有序并行区域**\ ，并把它贯通到仿真、检查报告、有界模型检查、
图、内置模板和文档。同时新增了带只读输入与参数的变量角色，仿真器、求解器与生成运行时共用的
运算符语义，执行轨迹，Python 的图快照与交互式查看器，以及更完整的有界模型检查工具。本版本包含
不兼容变化，更新之前请先阅读本节末尾的“从 0.6.0 升级”。

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
- 不含区域的模型也运行在同一个内核上，所以生成机器的代码体积、内存与每个周期的耗时同样会变化。相对旧模板的体积与速度比值及其测量方法，见 :doc:`/explanations/region_performance/index_zh` 的“生成的 C 运行时”一节；剩余的代价记录在 `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_。

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

- 每条这样的声明用一个隐藏的 ``int`` 变量 ``__forced_<n>`` 来执行；模型已经用掉的名字会被跳过。它和 ``__hist_*`` 一样出现在 ``StateMachine.defines``\ 、\ ``runtime.vars``\ 、抽象处理器的变量快照和生成代码的变量表里，并且在所有地方都是普通变量：热启动（hot start）像对待其他变量一样要求提供它，BMC 也像对待其他变量一样对待它。状态机在一个周期内部把它置起，声明完成后它回到 0，所以每一个停驻点上它都是 0；唯一的例外是目标进不去、整组停在半途时：它保持为 1，直到整组离开。\ :attr:`pyfcstm.model.model.StateMachine.forced_variables`\ 给出这些名字。
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

变量角色与只读输入
~~~~~~~~~~~~~~~~~~

顶层变量现在有一个说明归属的\ **角色**\ （role）。\ ``control``\ （旧写法 ``def``）是模型自己读写的普通变量。\ ``output``\ 由模型写入，供外部使用者读取。\ ``input``\ 由环境在每个周期提供一次，\ ``param``\ 在构造机器时固定；模型对这两种变量只能读。

.. code-block:: fcstm

   input float pressure;
   param float gain = 2.0;
   output float reading = 0.0;
   control int count = 0;

- ``input`` 不能带初始值；\ ``control``、\ ``output`` 和 ``param`` 必须带。在生命周期动作、切面或转换效果里给 ``input`` 或 ``param`` 赋值，包括写在不可达分支里，都是模型错误（``E_INPUT_WRITE`` 与 ``E_PARAM_WRITE``，例如 ``Model operations cannot write input 'a'.``）。初始值规则有各自的诊断码 ``E_INPUT_INITIALIZER`` 和 ``E_VARIABLE_INITIALIZER_REQUIRED``。
- ``control``、\ ``input``、\ ``param``、\ ``output`` 和 ``var`` 与 ``region``、\ ``active`` 一样是保留字（见\ *区域*\ 一节）。把其中任何一个用作状态名、事件名、动作名或变量名的模型需要改名。全部用 ``def`` 声明变量的模型含义不变：这些变量都是 ``control`` 变量。
- ``import`` 的映射块以 ``var`` 为标准关键字，``def`` 仍然可用。子模块的 ``input`` 可以绑定到父模块明确声明的 ``param``、\ ``input``、\ ``control`` 或 ``output``，并采用父声明的角色；被禁止的组合及其诊断见 :doc:`/reference/dsl/index_zh` 的导入一节。
- ``pyfcstm.model.VariableRole`` 与 ``VarDefine.role`` 给出角色。\ ``StateMachine.control_variables``、\ ``inputs``、\ ``parameters``、\ ``output_variables`` 和 ``persistent_variables`` 按声明顺序返回只读映射。把模型导出回 DSL 时保留声明时的写法。
- ``pyfcstm inspect`` 在每个变量下列出角色和外部供给方式，完整报告还为每个变量增加 ``read_sites`` 与 ``write_sites``。输入、参数和输出不会仅仅因为模型从不写入或从不读取，就被报告为未使用、未写入或只写不读的变量。字段约定见 :doc:`/reference/inspect_report/index_zh`。

模拟中的参数与周期输入
~~~~~~~~~~~~~~~~~~~~~~

模拟器和生成的运行时都按角色工作。不含 ``input`` 与 ``param`` 的模型行为不变。

- ``SimulationRuntime(model, parameters=..., input_source=...)`` 在构造时固定参数，并给每个输入绑定一个来源。来源可以是一个数、新增的内置生成器（``ConstantIntInput``、\ ``SequenceInput``、\ ``UniformIntInput``、\ ``NormalFloatInput``、\ ``CallableInput``、\ ``ReplayInputPattern`` 以及 :mod:`pyfcstm.simulate` 中的其他类），也可以是遵循 ``ScalarInputPattern`` 或 ``IntegratedInputPattern`` 的自定义对象。每个周期对每个来源读取一次，并把整个向量冻结到周期结束；\ ``runtime.cycle(inputs={...})`` 只对这一次调用覆盖取值。
- ``CycleResult.inputs``、\ ``runtime.last_inputs``、\ ``runtime.parameters``、\ ``runtime.outputs`` 和 ``runtime.control_variables`` 给出这些值。\ ``runtime.vars`` 只含控制变量和输出变量，含输入的模型的历史记录多一个 ``inputs`` 键。抽象处理器的上下文（``ReadOnlyExecutionContext``）在 ``vars`` 之外单独提供 ``inputs`` 和 ``parameters``。来源读取失败时不会前进，失败表现为带 ``code`` 的 ``SimulationRuntimeInputSourceError``，例如 ``E_INPUT_SOURCE_READ`` 或 ``E_INPUT_SOURCE_MISSING``。
- ``int`` 类型的变量、输入或参数接受像 ``2.0`` 这样的整数值浮点数，并按整数保存。
- ``pyfcstm simulate`` 新增 ``--param NAME=VALUE``\ （可重复，整个会话内固定）和 ``cycle --input NAME=VALUE``。每个真实周期都需要完整的输入向量，没有补零，也不沿用上一次的值。可运行的约定见 :doc:`/reference/simulation/inputs_zh`。
- 内置模板 ``python``、\ ``c``、\ ``c_poll``、\ ``cpp`` 和 ``cpp_poll`` 生成同样的划分：参数是构造参数，输入每个周期通过读取方法获取一次（Python 运行时里是 ``read_<input>()`` 与 ``get_input_<input>()``），C 里则通过输入提供者获取。

文档块
~~~~~~

写在变量声明、状态（包括根状态和伪状态）、事件、转换或生命周期动作正前方的块注释，现在是该声明的\ **文档块**\ （documentation block）。此前这样的注释是语法错误。文档块只是元数据，不改变执行、模拟、验证、PlantUML 输出或 inspect 报告。

.. code-block:: fcstm

   /* Number of retries allowed before the fault state. */
   def int retry_limit = 3;

   /* The top-level state. */
   state Controller {
       [*] -> Ready;
       /* A request is being processed. */
       state Ready;
   }

- Python 模型把它放在 ``VarDefine``、\ ``State``、\ ``Event``、\ ``Transition``、\ ``OnStage`` 和 ``OnAspect`` 的 ``doc`` 字段里。\ ``to_ast_node()`` 与 DSL 导出把它写回带星号边距的块，并区分 ``None``、空字符串和 ``*``。
- 抽象动作原有的尾随写法 ``enter abstract Name /* doc */;`` 仍然有效；同一个动作同时写前置块和尾随块会被拒绝。\ ``import`` 声明和导入映射条目不能拥有文档块。
- 没有闭合的块注释报告为 ``Unterminated multiline comment - missing closing '*/'``。
- 字段规则见 :doc:`/reference/dsl/index_zh` 的文档块一节。

运算符的求值语义
~~~~~~~~~~~~~~~~

每个运算符和数学函数的结果类型、取值与运行时错误，现在只在 :mod:`pyfcstm.semantics.catalog` 里定义一次。模拟器、生成的运行时、\ ``inspect``\ （常量折叠与数值诊断）、验证器和 ``pyfcstm bmc`` 都读取它，不再各说各话。运算、结果与错误种类（``division_by_zero``、\ ``modulo_by_zero``、\ ``zero_negative_power``、\ ``complex_result``、\ ``negative_shift_count``、\ ``math_domain``、\ ``writeback_non_integral``、\ ``writeback_non_finite`` 等）的表格在 :doc:`/reference/dsl/index_zh` 的求值语义一节。

模拟器，对所有模型：

- 把结果写回变量时被拒绝，现在是带运算符目录错误种类（``error.kind``）的 ``SimulationRuntimeExpressionError``，不再是裸的 ``ValueError``。包括：把非整数值写给 ``int`` 变量（``x = 7 / 2``）、产生复数的结果如 ``(-8) ** 0.5``\ （错误种类 ``complex_result``），以及构造时无效的 ``initial_vars`` 或初始值。
- ``cbrt`` 在所有运行时里用同一种算法，对完全立方数精确：\ ``cbrt(1000)`` 是 ``10.0``。上一个版本在平台立方根不是正确舍入的 Linux 构建上返回 ``9.999999999999998``。
- ``sign`` 作用于 NaN 时，所有运行时都得 ``-1``。

生成的 Python 运行时：\ ``**`` 遵循运算符目录（带符号的字面量底数使 ``-2 ** 2`` 等于 ``4``，复数结果是运行时错误），\ ``cbrt`` 与 ``sign`` 同模拟器一致，数学定义域错误在每个受支持的 Python 版本上都带同一条消息。

生成的 C 族运行时（``c``、\ ``c_poll``、\ ``cpp``、\ ``cpp_poll``）此前与模拟器不一致，现在与之对齐。数值落到下列情形的模型，行为会改变：

- ``round`` 在平局时取偶数邻居，与 Python 一致（\ ``round(2.5)`` 是 ``2``）。C 的 ``round`` 曾在平局时远离零取整。
- 负的移位次数是运行时错误。此前它在 C 里是未定义行为，会得到任意值。
- ``%`` 是向下取整的取模，结果与除数同号（\ ``-7 % 2`` 是 ``1``）。此前整数 ``%`` 用 C 的截断运算符，浮点 ``%`` 用 ``fmod``。
- 指数为非负整数的整数 ``**`` 是精确的，不再经过 ``pow``。
- 超出定义域的数学函数、负底数的小数次幂，以及把 NaN 或无穷大写给 ``int`` 变量，现在都是带模拟器措辞的运行时错误；此前生成的代码会产生 NaN 或无穷大。\ ``=>`` 的后件只在前件成立时才检查。
- ``W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE`` 现在分别说明它的三种输入：负的次数在每个生成运行时里都在运行时失败；不小于 C/C++ 宽度的整数次数是 C/C++ 的可移植性风险；非整数次数由操作数类型检查拒绝。

不兼容变化：一条转换上的事件与守卫
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

一条转换由事件\ **或**\ 守卫触发，同一条边上不能同时有两者（\ `issue #515 <https://github.com/HansBug/pyfcstm/issues/515>`_\ ）。DSL 语法本来就不允许把它们写在一起；现在这条规则对 Python 代码构造的对象同样成立。

- 模型的 ``Transition.event`` 与 ``Transition.guard``，以及 ``TransitionDefinition`` 和 ``ForceTransitionDefinition`` 的 ``event_id`` 与 ``condition_expr``，在构造或赋值会让两者同时不为 ``None`` 时抛出 ``ValueError``\ （消息 ``event and guard are mutually exclusive``）。被拒绝的赋值不会改动对象。两者都为 ``None`` 表示无条件的边。
- 迁移原来同时设置两者的代码：先清除已有字段再设置另一个，或把两项写成组合触发 ``A -> B :: Go + [x > 0];``，它会展开成分开的边。由 DSL 文本得到的模型不受影响。

执行轨迹与候选决策诊断
~~~~~~~~~~~~~~~~~~~~~~

对一次 ``SimulationRuntime.cycle`` 调用的两种按需视图。两者都不写文件，也不改变这次调用做了什么。

- ``cycle(trace=True)`` 把已提交的执行过程作为 ``CycleResult.trace`` 返回，它是按执行顺序排列的 ``ExecutionTraceEntry`` 元组。每个条目含 ``kind``\ （``state_enter``、\ ``state_exit``、\ ``transition`` 或 ``action``）、状态路径、当时的持久变量，以及转换标签或动作地址。被拒绝的候选和被回滚的 Delta 尝试不在其中。\ ``print(entry)`` 给出单行摘要，\ ``entry.to_dict()`` 给出可直接转成 JSON 的字典。
- ``cycle(diagnostics=True)`` 返回 ``CycleResult.diagnostics``，即 ``CycleDiagnostics``，它记录运行时考虑过的每个候选：事件是否出现、守卫结果、后继能否通过验证、被哪个先前的选择挡住、最终是否提交，以及它看到的取值和源码位置。\ ``str(report)`` 用文字解释这个周期，\ ``report.to_text(transition=..., check_id=...)`` 把范围缩小到一条转换，\ ``report.to_dict()`` 是独立的字典。它回答“为什么一条看似可用的转换没有被执行”。
- ``pyfcstm simulate`` 通过 ``--diagnostics``、\ ``--diagnostics-format text|jsonl``\ （JSONL 需要 ``-e``，每个周期在标准输出上给出一份报告）以及交互命令 ``decisions`` 和 ``why <id|label>`` 提供它。
- 不兼容变化：``pyfcstm simulate -e`` 批处理里的失败命令（未知事件、错误的 ``init``、运行时失败）现在会终止批处理，并让进程以非零状态退出。此前只打印消息，退出码是 0。候选被拒绝或出现 Delta 不算失败。

字段与命令见 :doc:`/reference/simulation/diagnostics_zh`，任务做法见 :doc:`/how_to/simulation/diagnostics_zh`。

Delta 周期与同周期循环
~~~~~~~~~~~~~~~~~~~~~~

- 选中的路径到不了可停止状态或终止，但属于稳定的无进展边界时，该周期现在以成功的 **Delta** 周期（无进展步骤）结束，不再是错误：位置和变量保持不变，周期计数和输入来源前进，\ ``CycleResult.delta`` 为 ``True``。历史记录多一个布尔值 ``delta``，导出到 CSV 时在 ``state`` 之后多一列 ``delta``。生成的运行时通过 ``last_cycle_was_delta`` 给出同样的信息。
- 经由初始转换、伪状态和父状态后续转换、永远到不了可停止状态的循环，不是 Delta 周期。它抛出 ``SimulationRuntimeDfsError``，消息里列出循环经过的状态和打破循环的办法。这类嵌套循环此前会以 Python 的 ``RecursionError`` 结束。只会回到自身起点的候选，在后面还有候选可以停驻时被跳过，所以含 ``[*] -> P; [*] -> Ready; P -> P;`` 的根状态现在启动后停在 ``Ready``。
- ``pyfcstm inspect`` 把这类封闭的同周期路由分量报告为警告 ``W_INITIAL_LIVELOCK``。

Inspect 与诊断
~~~~~~~~~~~~~~

- ``W_DEADLOCK_LEAF`` 现在是 ``W_LEAF_NO_OUTGOING_TRANSITION``。旧名称作为已弃用的别名留在 ``CODE_REGISTRY`` 里，不再被发出，计划在 1.0.0 移除。在 JSON 或大语言模型报告里匹配该诊断码的脚本应改匹配新名称，或调用 ``canonicalize_diagnostic_code``。
- ``pyfcstm inspect --collect-errors`` 报告全部模型错误而不是停在第一个，退出状态仍然非零。加载函数接受 ``load_state_machine_from_text(text, collect=True)`` 和 ``load_state_machine_from_file(path, collect=True)``，\ ``inspect_model(model, model_diagnostics=...)`` 接收收集到的诊断。语法错误仍然逐个报告。
- 默认的 ``inspect``，以及对正常加载的模型调用 ``inspect_model``，现在包含模型构建产生的警告，例如 ``W_COMBO_RESERVED_PREFIX_STATE_KIND``。这些警告此前只在 ``--collect-errors`` 下出现。
- inspect 的 JSON 与大语言模型报告以及 BMC 的 JSON 不再带 ``schema_version`` 或 ``schema_status`` 字段，随版本发布的 schema 文件就是约定。从更早的构建里读取这些字段的使用者必须停止读取。

有界模型检查与变量角色
~~~~~~~~~~~~~~~~~~~~~~

``pyfcstm bmc`` 与 :mod:`pyfcstm.bmc` 现在认识四种变量角色（variable role）：
``control``\ 、\ ``input``\ 、\ ``param`` 和 ``output``\ 。有界模型检查（bounded
model checking）还会报告在界内可达的运行时错误，把空场景与性质结论区分开，并能解释场景为什么为空。完整契约见
:doc:`/reference/bmc_query/index` 与 :doc:`/reference/bmc_results/index`\ ，操作步骤见
:doc:`/how_to/bmc/index`\ 。

**查询与见证中的变量角色。**

- 查询里引用变量的写法不变，仍是裸名字或 ``var("name")``\ ；角色决定它的值存活多久。
  ``control`` 与 ``output`` 变量在每个帧 ``0..N`` 上都有值，某个周期不写它就沿用上一个值。
  ``param`` 在整条轨迹上只有一个值：默认值把它定死，初始 ``havoc`` 允许取另一个值，但该值在所有帧上仍然相同。
  ``input`` 在每个步 ``0..N-1`` 各采样一次，每步的值相互独立，步与步之间没有隐含的相等关系。
- 提到输入的 ``assume`` 按步取值范围：\ ``assume at N`` 会被拒绝，因为不存在第 ``N`` 步；\
  ``assume always`` 覆盖 ``N`` 个步。不涉及输入的 ``assume`` 仍然覆盖帧 ``0..N``\ 。
  ``havoc`` 与 ``init ... where`` 拒绝输入，性质的帧谓词也不能读取输入；要跨帧比较某次采样，请把它存进
  ``control`` 或 ``output`` 变量。\ ``havoc *`` 覆盖控制、输出和参数变量。
- JSON 见证记录求解器的选择：\ ``initial.parameters`` 给出完整的参数值；除吸收步外的每一步都有
  ``inputs``\ （按声明顺序的完整数值采样，包括没人读取的输入）和 ``input_reads``\ （按顺序列出被守卫或假设读取的输入）。
  ``frames[*].vars`` 与抽象调用的 ``snapshot`` 现在只含 ``control`` 与 ``output`` 的值。
  回放把记录的参数和输入原样交给 ``SimulationRuntime``\ ，任何输入或参数不一致都报告为不匹配，缺失的值绝不用零补齐。
- ``called(...)`` 过滤器对 ``active_leaf`` 与 ``named_ref`` 的匹配规则是：有活动叶子时取叶子路径，否则取动作所在的宿主状态，
  所以进入或离开复合状态、或运行声明在复合状态上的普通 ``during`` 时，匹配的是宿主路径。\
  ``named_ref`` 匹配调用点自己的具名 ``ref``\ ；只是途经某个具名动作的调用匹配 ``named_ref=null``\ 。

**界内运行时错误。** ``pyfcstm bmc`` 现在先问一个问题：是否存在某个允许的执行，会碰到运行时拒绝的操作——除以零或对零取模、
数学定义域错误、\ ``**`` 的结果是复数，或者给 ``int`` 变量赋非整数、非有限的值。每个守卫和每个动作块都算在内，
顺序与模拟器求值顺序一致。这样的执行存在时，报告标题为 ``RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED``\ ，
性质不再求值，命令以状态码 ``5`` 退出。见证是执行到出错步之前的前缀，附带错误种类与位置；回放必须在同一步复现同一种错误，
否则算回放不匹配（状态码 ``4``\ ）。如果预算内无法判定，标题为 ``RUNTIME SAFETY CHECK UNKNOWN`` 或 ``TIMED OUT``\ ，状态码为
``3``\ 。\ ``--no-runtime-safety`` 跳过这项检查，只在不出错的执行上求值性质；默认是 ``--runtime-safety``\ 。
这项检查总是在没有启用 ``--cone-slicing`` 的模型上运行。Python 调用方向 :func:`pyfcstm.bmc.solve_bmc_property`
传 ``runtime_safety=False``\ ，或直接使用 :func:`pyfcstm.bmc.check_runtime_safety`\ 。在 JSON 中，\
``result.outcome`` 取 ``runtime_error``\ 、\ ``runtime_safety_unknown`` 或 ``runtime_safety_timeout``\ ；
检查被关闭时 ``result.runtime_safety`` 为 ``null``\ ，否则含 ``status``\ （\ ``safe``\ 、\ ``violated``\ 、\ ``unknown``\ 、\
``timeout`` 或 ``not_applicable``\ ）、\ ``sites``\ 、\ ``elapsed_ms``\ 、\ ``reason``\ ，违例时还含
``error``\ （\ ``step``\ 、\ ``kind``\ 、\ ``location``\ ）。错误种类取自运算符目录，例如
``division_by_zero``\ 、\ ``math_domain`` 与 ``writeback_non_integral``\ 。

**空场景。** 当性质的目标不可满足时，命令现在会检查允许场景本身——模型转移关系、\ ``init`` 子句和 ``assume`` 子句——是否存在任何执行。
若不存在，结果为 ``scenario_infeasible``\ ：\ ``property_satisfied`` 为 ``null``\ ，不产生见证，标题为
``SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED``\ ，状态码为 ``3``\ 。以前，空场景在反例搜索里被报告为有界保证，
在可达搜索里被报告为没有见证。报告会指出场景最先变空的阶段（内核、初始化或假设），\ ``result.feasibility`` 携带同样的证据；
超时或未能判定的可行性检查按原样报告，绝不当作空场景。现在每个结果的标题都说明证据的种类，例如
``PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``\ 、\ ``PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND``\ 、\
``GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS`` 或 ``PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE``\ ，
报告还增加 ``Scenario``\ 、\ ``Property verdict``\ 、\ ``Semantic interpretation`` 与 ``Conclusion`` 几行。
这些都是有界的陈述，不是无界定理。

**解释空场景。** ``--explain-infeasibility none|formal|proof``\ （默认 ``none``\ ，不增加任何求解工作）为空场景的结果附上不可行性解释（infeasibility explanation）。
``formal`` 对冲突分类，并给出源码核心：足以让场景为空的、作者写下的 FCSTM 与 FBMCQ 约束（带文件位置与源码文本），预算允许时会缩小到子集极小。
分类是 ``kernel_conflict``\ 、\ ``initialization_self_conflict``\ 、\ ``initialization_domain_conflict``\ 、\
``initialization_kernel_conflict``\ 、\ ``assumptions_self_conflict``\ 、\ ``assumptions_domain_conflict`` 与
``assumptions_prefix_conflict`` 之一。\ ``proof`` 还会构造逐步证明，在 ``Why no execution exists`` 下读成带编号的句子，
并打印 ``Proof strength`` 块。只有每一步都经过检查才会发布证明：输入步对照它所重述的约束，推导步由独立的检查器或求解器检查。
规则构成封闭的目录，共十二个 ``rule_id``\ （\ ``source_fact``\ 、\ ``case_condition_entailment``\ 、\
``transition_assignment``\ 、\ ``equality_substitution``\ 、\ ``arithmetic_evaluation``\ 、\ ``interval_intersection``\ 、\
``state_domain_exhaustion``\ 、\ ``definedness_failure``\ 、\ ``incompatible_equalities``\ 、\ ``boolean_complement``\ 、\
``excluded_state_selected`` 与 ``preceding_value_entailment``\ ）。没有规则能收口某个核心时，结果退回 ``formal``\ ，
而不是发布未经检查的证明，报告会写 ``Explanation depth: requested proof, achieved formal``\ ；在 JSON 里比较
``requested_mode`` 与 ``achieved_mode``\ 。解释从不改变结论。Python 调用方向 :func:`pyfcstm.bmc.solve_bmc_property`
传 ``infeasibility_explanation='formal'`` 或 ``'proof'``\ 。

**求解选项。**

- ``--cone-slicing``\ （默认关闭）删去查询没有观察到的变量的写入，但只限求值不会失败的整数写入，并保留控制流、初始值以及部分算术所依赖的一切。
  见证仍然包含全部变量，仍然要通过回放。切片什么也没做时，\ ``result.cone_slicing.skipped_reason`` 会说明
  （\ ``abstract_actions`` 或 ``no_removable_variables``\ ）；不带该选项时该字段不出现。记录在案的基准里，
  求解时间的总体影响不到百分之一，个别查询反而变慢，请在自己的模型上测量。Python 调用方使用
  ``BmcOptions(cone_slicing=True)``\ 。
- ``--solver-profile default|logic|tactic`` 选择主求解器。\ ``logic`` 根据公式选一种 Z3 逻辑（\ ``QF_LIA``\ 、\
  ``QF_LRA``\ 、\ ``QF_LIRA``\ 、\ ``QF_NIA``\ 、\ ``QF_NRA`` 或 ``NIRA``\ ），都不匹配时退回通用求解器；\
  ``tactic`` 依次运行 ``simplify``\ 、\ ``propagate-values``\ 、\ ``solve-eqs`` 与 ``smt``\ 。求解配置（solver profile）不改变结果的含义，
  但可能改变找到的见证和求解耗时，见证仍须通过回放。解释与证明的检查始终使用默认求解器。
  在记录在案的对比里，两个可选配置都没有达到采用标准，所以默认值仍是 ``default``\ 。结果会报告
  ``solver_profile``\ 、\ ``solver_logic`` 与 ``solver_statistics``\ 。Python 调用方使用
  :func:`pyfcstm.bmc.solve_bmc_property` 的 ``solver_profile=``\ 。
- ``--timeout-ms`` 现在是整次运行共用的一份预算，由所有求解检查（运行时安全、可行性、解释、主检查与响应后缀检查）共享，
  以前它对每次检查单独生效。因预算用尽而无法开始的检查，报告为未检查，而不是空场景。

**结果变化。** 与上一版本相比，JSON 结果有以下变化；请对照所用版本随发布附带的模式文件校验。

- ``exit_code`` 可以是 ``5``\ 。进程退出状态为 ``0``\ （性质成立）、\ ``1``\ （性质不成立）、\ ``3``\ （无定论、空场景，
  或安全性、可行性检查未能判定）、\ ``4``\ （回放不匹配）和 ``5``\ （运行时错误可达）；优先级依次是 ``4``\ 、\ ``5``\ 、\ ``3``\ ，
  然后才是 ``0`` 或 ``1``\ 。
- ``result.outcome`` 新增 ``scenario_infeasible``\ 、\ ``feasibility_timeout``\ 、\ ``feasibility_unknown``\ 、\
  ``runtime_error``\ 、\ ``runtime_safety_unknown`` 与 ``runtime_safety_timeout``\ 。\ ``result`` 新增
  ``feasibility``\ （内含 ``explanation``\ ）、\ ``available_model_roles``\ 、\ ``total_elapsed_ms``\ 、\
  ``solver_profile``\ 、\ ``solver_logic``\ 、\ ``solver_statistics``\ 、\ ``runtime_safety``\ ，以及仅在请求切片时出现的
  ``cone_slicing``\ 。
- ``witness`` 与 ``replay`` 现在绑定到它们所描述的模型的角色。\ ``witness`` 带 ``model_role``\ （\ ``primary_witness``\ 、\
  ``primary_counterexample``\ 、\ ``incomplete_suffix`` 或 ``runtime_error_prefix``\ ）和一个 ``verdict`` 对象；
  ``incomplete_suffix`` 轨迹是有限前缀的证据，绝不构成性质结论。\ ``replay`` 带同一个角色。新增的 Python 函数
  :func:`pyfcstm.bmc.decode_bmc_result_trace` 按这种形状解码求解结果的模型，而 :func:`pyfcstm.bmc.decode_bmc_witness`
  保持原来的输出形状。
- 步新增 ``inputs`` 与 ``input_reads``\ ，初始记录新增 ``parameters``\ ，如上所述。

**迁移。** 读取人类可读报告第一行的脚本必须改用新的标题，更好的做法是读取 ``--json``\ 。
曾依赖 ``--timeout-ms`` 按单次检查计时的调用方，需要为整次运行调大它。如果模型在某条允许的路径上可能除以零、
对负数开平方，或把小数写入 ``int`` 变量，现在会以状态码 ``5`` 退出，直到给该操作加上保护或约束输入；
传 ``--no-runtime-safety`` 可恢复先前的行为。曾按旧模式文件校验 JSON 的使用方，必须改用本版本附带的那一份。

内置模板的实例参数与采样输入
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

模型声明了 ``param`` 或 ``input`` 变量时，五个内置模板现在都会生成带有相应公开接口的运行时，生成的 ``README`` 指南也讲解了它。
没有这些声明的模型，除前面各节所述的文本变化外，生成的接口与以前相同。\ ``param`` 的值按实例固定；\ ``input`` 的值每个周期采样一次，
对模型只读，也不会在周期之间保持。\ ``vars`` 与 ``Vars`` 只含 ``control`` 和 ``output`` 变量。手写模板可以通过
``model.parameters``\ 、\ ``model.inputs``\ 、\ ``model.persistent_variables``\ 、\ ``model.control_variables`` 与
``model.output_variables`` 读取这些声明。

- ``python``\ ：\ ``Machine(initial_state=None, initial_vars=None, *, parameters=None)`` 校验并复制 ``parameters``\ ；
  冷启动时省略的参数取 DSL 默认值，热启动则需要给全。实现 ``read_<input>()`` 来提供采样；运行时每个周期对每个输入读取一次，
  包括所选路径用不到的输入，并在校验与执行期间冻结该采样。\ ``cycle(events=None, *, inputs=None)`` 为部分或全部输入提供显式值，
  其余输入通过各自的钩子读取。没有实现读取方法时抛出 ``NotImplementedError``\ 。用 ``get_param_<name>()``
  读参数，周期内用 ``get_input_<name>()`` 读输入；\ ``parameters`` 与 ``last_inputs`` 暴露固定值和最近一次提交的采样，
  抽象动作的上下文把 ``vars``\ 、\ ``inputs`` 与 ``parameters`` 作为三个独立的只读映射携带。\ ``int`` 输入或参数接受整数值的
  ``float`` 并按 ``int`` 存储，与模拟器一致。读取失败或周期失败时，持久变量与 ``last_inputs`` 保持不变。
- ``c`` 与 ``c_poll``\ ：\ ``<Prefix>InitOptions`` 携带 ``vars``\ 、\ ``parameters`` 以及每个值的存在标志（标志为零表示用 DSL 默认值），
  用 ``<Prefix>_init_with_options(machine, &options)`` 启动机器。输入通过 ``<Prefix>InputProvider`` 提供，每个输入一个
  ``read_<input>`` 回调，用 ``<Prefix>_set_input_provider`` 注册；也可以把完整的 ``<Prefix>Inputs`` 值交给
  ``<Prefix>_cycle_with_inputs``\ （\ ``c_poll`` 在这里不传事件编号）。回调写入值后返回 ``1``\ ，返回 ``0`` 则中止该周期；
  缺少提供者、值非有限或回调失败，都会使周期失败且不提交。用 ``<Prefix>_get_param_<name>``\ 、\
  ``..._get_input_<name>`` 与 ``<Prefix>_last_inputs`` 读取这些值，用 ``<Prefix>_hot_start_with_parameters`` 恢复完整的参数集合。
- ``cpp`` 与 ``cpp_poll``\ ：包装类通过 ``MachineWrapper(const InitOptions &)``\ 、\ ``init``\ 、\ ``set_input_provider``\ 、\
  ``cycle_with_inputs(inputs, ids, count)``\ （\ ``cpp_poll`` 为 ``cycle_with_inputs(inputs)``\ ）、\ ``last_inputs``\ 、\
  ``get_param_<name>`` 与 ``get_input_<name>`` 暴露同样的能力。回调保持 C 签名。

生成运行时的运算符语义
~~~~~~~~~~~~~~~~~~~~~~

模拟器、生成的运行时、\ ``inspect``\ 、验证器和 BMC 现在都从同一份运算符目录（operator catalog）\ :mod:`pyfcstm.semantics.catalog`
求值。\ :doc:`/reference/dsl/index` 中的表 *Evaluation and runtime errors* 列出了每个运算符和函数的结果与错误种类。对生成代码而言，变化是：

- C 族模板（\ ``c``\ 、\ ``c_poll``\ 、\ ``cpp``\ 、\ ``cpp_poll``\ ）曾在某些运算符上与模拟器不同，却没有任何提示。现在它们与模拟器一致：
  ``%`` 是向下取整的取模，结果与除数同号（\ ``-7 % 2`` 是 ``1``\ ），对整数和浮点数都如此；\ ``int`` 底数加非负 ``int`` 指数的 ``**`` 是精确的整数幂，
  以前它经过 ``double``\ ，超过 53 位的低位会丢失（\ ``3 ** 34`` 曾差一）；零底数加负指数在求值时失败；\
  ``cbrt`` 是实数立方根，对完全立方数精确；\ ``floor``\ 、\ ``ceil``\ 、\ ``trunc`` 与 ``round`` 作用于 NaN 或超出 ``int64`` 范围的值时失败，
  而不是产生类型转换的假结果；给 ``int`` 变量赋 NaN 或无穷时，以 "must be finite" 报错。
- 生成的 Python 运行时拒绝结果为复数的 ``**``\ ，与模拟器一样把 ``-2 ** 2`` 当作 ``4``\ ，在所有受支持的 Python 版本上对完全立方数精确计算
  ``cbrt``\ ，对 NaN 的 ``sign`` 返回 ``-1``\ ，并且在所有 Python 版本上以同一条消息报告数学定义域错误，而不是宿主解释器的措辞。
- 被拒绝的写回（把非整数或非有限的值赋给 ``int`` 变量）现在在模拟器和生成的 Python 运行时里都是 ``SimulationRuntimeExpressionError``\ ，
  包括 ``initial_vars`` 与默认初始化，而不是裸 ``ValueError``\ 。在模拟器里，该异常带有 ``kind`` 属性，取值为目录中的错误种类，例如
  ``writeback_non_integral``\ 。
- 在模拟器和 BMC 中，\ ``=>`` 只在左操作数成立时才对右操作数求值，所以 ``d != 0 => 10 / d > 1`` 绝不会除以零。

命令行
~~~~~~

- ``pyfcstm bmc`` 新增 ``--cone-slicing``\ 、\ ``--runtime-safety`` / ``--no-runtime-safety``\ 、\ ``--solver-profile`` 与
  ``--explain-infeasibility``\ ，运行时错误可达时以状态码 ``5`` 退出，详见上文。帮助文本与选项表见 :doc:`/reference/cli/index`\ 。
- ``pyfcstm simulate`` 新增可重复的 ``--param NAME=VALUE``\ ，用于设置构造参数。在 REPL 和 ``-e`` 批处理里，\ ``cycle`` 可对每个输入各写一次
  ``--input name=value``\ ，提供该周期的采样；带 ``input`` 变量的模型需要给全每个输入的值。\ ``--diagnostics`` 为每个周期记录被检查并被否决的候选转移；
  ``decisions [--verbose]`` 与 ``why <id|label> [--verbose]`` 查询最近一份报告。\ ``--diagnostics-format jsonl`` 把每份报告写成标准输出上的一行 JSON，
  需要同时给出 ``--diagnostics`` 与 ``-e``\ ；此时过程记录和查询输出改走标准错误。Python 调用方向 ``SimulationRuntime.cycle`` 传
  ``diagnostics=True``\ ，再读取 ``result.diagnostics``\ 。参见 :doc:`/reference/simulation/diagnostics` 与
  :doc:`/reference/simulation/inputs`\ 。
- ``pyfcstm inspect`` 新增 ``--collect-errors``\ ，报告全部模型错误而不是停在第一个，对无效模型仍以非零状态退出。对应的 Python 接口是
  ``load_state_machine_from_file`` 与 ``load_state_machine_from_text`` 的 ``collect=True``\ ，以及 ``inspect_model`` 的
  ``model_diagnostics`` 参数。能成功构建的模型，其转换过程中产生的警告，例如 ``W_HISTORY_UNUSED``\ 、\ ``W_HISTORY_RESERVED_PREFIX``\ 、\
  ``W_COMBO_RESERVED_PREFIX_STATE_KIND`` 与 ``W_COMBO_RELAY_PSEUDO_HAS_ACTIONS``\ ，现在会出现在默认报告里；以前只有加
  ``--collect-errors`` 才会出现。
- ``pyfcstm --self-check`` 对已安装的 wheel 或独立可执行文件运行安装与运行时检查，报告缺失的打包资源、不可用的依赖和平台问题。
  ``pyfcstm --self-check --help`` 列出它的选项（\ ``--profile``\ 、\ ``--format``\ 、\ ``--report``\ 、\ ``--color``\ 、\
  ``--timeout-scale``\ 、\ ``--fail-on-warn`` 等）。它是部署诊断，不能代替测试套件。

检查报告
~~~~~~~~

- 在 LLM 报告的 ``summary.structure_statistics`` 以及完整报告的
  ``ModelInspect.structure_statistics`` 中新增描述性结构统计。比率以原始小数输出，
  空分母使用 ``null``，并记录转换密度和不可达总体的保守建议阈值。
  ``W_UNREACHABLE_TRANSITION`` 会按每条书写的转换聚合不可达原因；这些阈值仍只是元数据，
  不生成综合健康分数；Python API 和命令行均可覆盖或关闭这些阈值。
- 在完整 JSON/API 报告中新增 ``ModelInspect.verification`` 执行元数据，使消费者能够区分
  验证未启用、被策略排除、得到确定结果和无法判定，而不会把这些状态误当成新的模型诊断。
  命令行的人类可读输出会显示紧凑的覆盖率及不确定原因。

图的快照与查看器
~~~~~~~~~~~~~~~~

编辑器的预览早已能画出模型；本版本让 Python 包拥有同一套绘制。v0.6.0 中并没有
``pyfcstm.diagram`` 与 ``pyfcstm diagram``。参考见
:doc:`/reference/visualization_options/index`\ ，缘由见
:doc:`/explanations/visualization/index`\ 。

- ``StateMachine.diagram()`` 返回 :class:`pyfcstm.diagram.api.Diagram`\ ，这是一份
  与模型脱离的不可变快照（snapshot）：之后再修改模型，不会改变已保存视图的内容，
  给属性赋值也会被拒绝。\ ``with_options()`` 与 ``with_view_state()`` 返回新的快照，
  不改动原对象。
- ``to_dict()`` 与 ``to_json()`` 给出确定性的可移植数据，不需要任何可选运行时。
  ``to_html()`` 写出单个自包含的查看器，内嵌渲染器、布局引擎、光栅化器与中日韩
  字体，使用严格的内联内容策略，不访问网络。一个查看器约 29 MB（用文本载入
  ``state Root;`` 时为 29,397,900 字节，数字会随模型变化）。\ ``save(path)`` 按后缀
  （或 ``format=``\ ）选择 JSON、HTML、SVG、PNG 或 PDF。\ ``show()`` 在基于 Chromium
  的应用窗口中打开查看器，并像 ``matplotlib.pyplot.show`` 那样阻塞到窗口关闭，随后
  删除它写下的临时文档，除非你传入了 ``output``\ 。
- 查看器有三种模式（仅源码、仅图、联动分栏），支持折叠、缩放与平移。模型从文本或
  文件载入时，源码面板会被嵌入并与图联动；在 Python 中直接构建的模型没有源码范围，
  查看器会说明这一点，而不是显示一个空面板。
- :class:`pyfcstm.diagram.api.DiagramOptions` 包含 ``detail_level``\ （\ ``minimal``\ 、
  ``normal`` 或 ``full``\ ）、\ ``direction``\ （\ ``TB`` 或 ``LR``\ ）、\ ``palette``\ 、
  ``mode``\ （\ ``light``\ 、\ ``dark`` 或 ``auto``\ ）以及 ``cjk_locale``\ （\ ``sc``\ 、
  ``tc``\ 、\ ``hk``\ 、\ ``jp`` 或 ``kr``\ ）。
  :class:`pyfcstm.diagram.api.DiagramViewState` 包含查看器模式、折叠的状态标识、缩放
  与平移。两者都接受映射，未知的键会被拒绝。
- 细节级别（detail level）改变的是画出什么，而不是数据里有什么。\ ``minimal`` 只画
  状态标题与转换，效果写在行内；\ ``normal`` 把效果放进注释框，并按事件给边着色；
  ``full`` 在叶子状态的标题下再列出它自己的事件与生命周期动作。独立查看器、SVG、
  PNG 与 PDF 导出以及 VS Code 预览共用同一个渲染器，所以画法一致。
- ``pyfcstm diagram -i machine.fcstm`` 输出可移植的 JSON。\ ``-o viewer.html`` 写出
  查看器；\ ``--open`` 在窗口中打开它，只有用 ``-o`` 保留了文档时才打印路径；\ ``-o``
  带 ``.svg``\ 、\ ``.png`` 或 ``.pdf`` 后缀（或使用 ``--format``\ ）则写出导出文件。
  ``--scale`` 只用于 PNG。输入与输出方面的问题以命令行错误报告，而不是回溯。命令列表见
  :doc:`/reference/cli/index`\ 。
- 安装了渲染运行时时，\ ``Diagram`` 会在笔记本单元格里显示 SVG；未安装时退回普通的
  文本表示。

图的导出与编辑器预览
~~~~~~~~~~~~~~~~~~~~

- ``to_svg()``\ 、\ ``to_png(scale=...)`` 与 ``to_pdf()`` 同步导出。它们需要可选的渲染
  运行时，用 ``pip install pyfcstm[viz]`` 安装（Python 3.8 及以上使用 ``mini-racer``\ ，
  Python 3.7 使用低于 0.7 的 ``py-mini-racer``\ ）；缺少时抛出
  :class:`pyfcstm.diagram.engine.DiagramUnavailableError`\ ，并指明依赖。SVG 是展开后的
  形式：字形与箭头已是路径，因此在没有安装本项目字体的机器上显示也一样。PDF 是单页
  矢量文档，文字已转为轮廓，所以不能检索文字。
- 导出有上限，超出时在渲染之前就以
  :class:`pyfcstm.diagram.engine.DiagramRenderLimitError` 拒绝：PNG 缩放不超过 4，
  单边不超过 16,384 像素，总像素不超过 16,777,216，PNG 不超过 33,554,432 字节，
  SVG 或 PDF 不超过 67,108,864 字节。
- ``pyfcstm expand-svg -i canonical.svg [-o expanded.svg]`` 把一份标准形式的图 SVG
  （其中指名了字体）转换成自包含的形式；不带 ``-o`` 时输出到标准输出。它的用途是：
  手里有图却没有字体的宿主，可以直接把文字转为轮廓，而不必按源码重新渲染，因为重新
  渲染会丢掉用户选定的调色板与颜色模式。
- VS Code 预览的 SVG 下载用到了它：扩展请已安装的 ``pyfcstm[viz]`` 把文字转为轮廓，
  因为随扩展捆绑字体与光栅化器，一个中日韩语言区要多出约 17.7 MB，全部语言区约
  59.4 MB。新设置 ``fcstm.diagram.pyfcstmPath`` 指定要用的命令；留空则依次尝试
  ``pyfcstm``\ 、\ ``python3 -m pyfcstm`` 与 ``python -m pyfcstm``\ 。没有可用的安装时，
  导出会如实说明，而不是交出一份依赖读者字体的文件。

自检
~~~~

``pyfcstm --self-check``\ （也可写作 ``python -m pyfcstm --self-check``\ ）是新增的。它在
当前运行环境中诊断已安装的包或独立可执行文件：导入、打包资源、运行时依赖、平台兼容性，
以及可选的可视化服务（Java 与 PlantUML）。它不是第二套测试，失败说明的是部署环境的
问题，而不是实现的问题。

- 各项检查在隔离的工作进程中运行，其中一项崩溃或挂起会被如实报告，不会拖垮其余各项。
  ``--profile default|full|visualize`` 选择检查集合；\ ``--network`` 启用远程探测，只能与
  ``--profile visualize`` 一起使用；\ ``--format human|json`` 选择报告形式；
  ``--report PATH`` 指定报告文件；\ ``--color auto|always|never`` 与 ``--timeout-scale``
  调整输出与时间限制；\ ``--no-redact`` 在环境信息里保留本地路径，默认会隐去。
- 必需的检查失败时退出码为 ``1``\ ，给了 ``--fail-on-warn`` 时必需检查出现警告也是
  ``1``\ ，其余为 ``0``\ 。缺少可选的 Java 或 PlantUML 只是警告。
- ``pyfcstm --version`` 现在还会打印构建修订、Python 版本与平台。它在导入命令行框架
  之前就已应答，所以损坏的可选依赖不会让它失效。解析过 v0.6.0 两行输出的脚本应当只
  读第一行。

安装与兼容性
~~~~~~~~~~~~

- 支持的 Python 范围不变：\ ``python_requires`` 仍是 ``>=3.7``\ ，测试矩阵覆盖 CPython
  3.7 到 3.14。VS Code 的最低版本仍是 ``^1.60.0``\ ，\ ``jsfcstm`` 仍声明 Node ``>=16``\ 。
- ``requirements.txt`` 抬高或新增了这些运行时依赖：\ ``jinja2>=3.1.6``\ （原为
  ``>=3``\ ；这是既能获得 Jinja2 安全修复、又仍支持 Python 3.7 的下限）、
  ``deprecation>=2.1.0`` 与 ``packaging>=21.3``\ （新增）。另外把 ``plantumlcli`` 经
  ``pyquery`` 引入的 ``lxml`` 在 Python 3.7 与 3.8 上限定为 ``>=4.9,<6.1``\ ，在
  Python 3.9 及以上限定为 ``>=6.1``\ ，使各个版本在 Windows 上都有预编译包。
  ``z3-solver<=4.15.4`` 不变。
- 发布包现在携带 ``pyfcstm/diagram/assets`` 下的图运行时资源：渲染器、查看器脚本、
  resvg WebAssembly 模块、三个 JetBrains Mono 字重，以及五个中日韩语言区各一套常规与
  粗体 Noto Sans 字体，并附带许可证文件。已安装的包因此变大。这些资源是构建产物，
  不在仓库中跟踪：从源码检出安装时，需要先运行 ``make build_assets``\ （其中会执行
  ``npm ci``\ ），再 ``pip install`` 或 ``python setup.py build``\ ，缺少资源时
  ``setup.py`` 会停下并给出这条指示。
- 新增可选依赖组 ``pip install pyfcstm[viz]``\ ，安装 SVG、PNG 与 PDF 导出所需的
  MiniRacer 运行时。查看器、\ ``to_dict()``\ 、\ ``to_json()`` 与 ``to_html()`` 不需要它。
- 诊断码注册表现在可以把一个诊断码标记为已弃用的别名，并记录弃用它的版本与移除它的
  版本；见\ *从 0.6.0 升级*\ 。

文档与大语言模型指南
~~~~~~~~~~~~~~~~~~~~

- 文档页面上的例子现在把命令或脚本与它的真实输出放在一起，文档检查（\ ``make
  docs_doctest``\ ）会运行这些例子，并把实际输出与页面所示逐一比对。区域教程已经
  改写成这种形式。
- ``pyfcstm`` 包内每个文档字符串里的 ``>>>`` 例子都由 ``make doctest`` 运行，这道
  检查没有已知失败清单。因此应用程序接口参考中的例子都是能运行的例子。
- 随包发布的两份大语言模型（LLM）指南跟随语言一起更新。FCSTM 语法指南新增了
  *Documentation Blocks*\ 、\ *Reserved Identifiers*\ 、\ *Variable Roles*\ 、
  *Import variable roles*\ 、\ *History* 与 *Regions* 各节；FBMCQ 语言指南新增了
  *Starting a model with regions*\ 、\ *Variable roles in assumptions* 与
  *A model with regions*\ 。两份指南仍由各自旁边的 ``.sha256`` 文件保护。

从 0.6.0 升级
~~~~~~~~~~~~~

把模型、脚本或下游集成从 v0.6.0 迁到 v0.7.0 时，请逐条对照下面的清单。每条都指向
写有细节的小节。

- **名字。** ``region`` 与 ``active`` 是保留字，\ ``var``\ 、\ ``control``\ 、\ ``input``\ 、
  ``param`` 与 ``output`` 同样是（后四个用于声明变量角色；FCSTM 语法指南在
  *Reserved Identifiers* 与 *Variable Roles* 中列出）。把其中任何一个用作状态、事件、
  动作、变量或导入别名名字的模型，需要改名，例如改成 ``Active`` 或 ``active_flag``\ 。
  见\ *Regions*\ 。
- **强制转换。** 源状态内部有状态的 ``!S -> T`` 现在只在停留的状态处判定一次；四处
  行为变化、隐藏变量 ``__forced_<n>``\ 、伪状态 ``__forced_gate_<n>``\ 、
  ``walk_states()``\ 、\ ``StateMachine.defines`` 与 ``to_ast_node()`` 输出的变化，以及运行
  的机器上不再有 ``Transition.is_forced``\ ，都意味着保存下来的期望值需要更新。见
  *Forced Transitions*\ 。
- **含历史与 active() 的模型的热启动。** ``__hist_goto`` 与 ``__hist_*`` 记录不再被
  检查，BMC 约束类别 ``domain.history_variable`` 已不存在。见 *History and active()*\ 。
- **不支持特性的诊断码。** ``E_UNSUPPORTED_FEATURE`` 不再列出 ``active`` 特性，inspect
  的原因 ``active_query_unsupported`` 已移除；带区域的模型交给没有声明 ``region`` 特性
  的模板时，会以 ``E_UNSUPPORTED_FEATURE`` 拒绝。见 *Templates and capability
  declarations*\ 。
- **inspect 的可达性。** 子状态都不能离开的复合状态永远不会走它的普通出边；它指向的
  状态现在由 ``W_UNREACHABLE_STATE`` 报告，该转换的原因是 ``owner_never_completes``\ 。
  见 *Inspect and verify*\ 。
- **诊断码改名。** ``W_DEADLOCK_LEAF`` 现在是 ``W_LEAF_NO_OUTGOING_TRANSITION``\ 。旧写法
  作为已弃用的别名留在 ``CODE_REGISTRY`` 中（0.7.0 起弃用，计划在 1.0.0 移除），可通过
  ``resolve_diagnostic_code`` 与 ``canonicalize_diagnostic_code`` 解析；新的报告只输出
  新写法，所以按旧诊断码过滤的地方需要更新。见
  :doc:`/reference/diagnostics_codes/index`\ 。
- **转换的字段。** 在 Python 模型与 AST 中，\ ``Transition.event`` 与
  ``Transition.guard``\ （以及 AST 转换的 ``event_id`` 与 ``condition_expr``\ ）互斥：
  两者都设置会抛出 ``ValueError``\ ，并保持对象不变。要先清空一个字段再设置另一个。见
  :doc:`/reference/dsl/index`\ 。
- **生成的 Python 运行时。** ``vars`` 是只读视图，别名 ``variables`` 已移除，
  ``ABSTRACT_HOOKS`` 是只读映射，带区域的模型没有 ``current_state_path`` 与
  ``current_state_name``\ 。请重新生成文件；没有区域的模型生成的文本也会变化。见
  *Templates and capability declarations*\ 。
- **生成的 C 与 C++ 运行时。** 机器类型是不透明的，\ ``MAX_STACK_DEPTH`` 与
  ``MAX_DFS_STEPS`` 由 ``..._ARENA_CAPACITY``\ 、\ ``..._TRAIL_CAPACITY`` 与
  ``..._STORAGE_BYTES`` 宏取代，带区域的模型没有 ``current_state_id``\ 、
  ``current_state_path`` 与 ``current_state_name``\ 。请重新生成并重新构建；代码体积、
  内存与每个周期的耗时都会变化。见 *Templates and capability declarations*\ 。
- **模拟器命令行。** ``events`` 与 ``cycle`` 的补全只列出能用的短名字，\ ``init`` 会
  拒绝重复给出的变量。见 *Simulating models with regions*\ 。
- **安装。** 请升级到 ``jinja2>=3.1.6``\ ；\ ``deprecation`` 与 ``packaging`` 会随包一起
  安装。从源码检出构建或安装之前，需要先运行 ``make build_assets``\ 。见\ *安装与兼容性*\ 。
- **版本输出。** ``pyfcstm --version`` 的输出不止两行。见\ *自检*\ 。

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
- 新增稳定的 ``bmc-cli/v1`` JSON 封装，供持续集成、工具和大语言模型消费，并在 BMC
  结果协议参考中提供可下载模式。输出保留按极性解释的结论、求解耗时、见证与重放
  记录、诊断及对应进程退出状态。
- 新增中英文教程、任务指南、三篇数学解释和两篇完整参考。解释页推导 40 条带标签、
  可追溯到实现的公式，并通过 MathJax HTML 与 XeLaTeX PDF 验证。

检查与诊断
~~~~~~~~~~

- 将 ``pyfcstm inspect`` 默认输出改为检查器风格的人类报告，提供对齐的源码范围、
  相邻源码上下文、紧凑严重级别标签和 ``--color auto|always|never``。文件、管道和
  机器格式仍不包含 ANSI 转义序列。
- 通过 ``--format json`` 保留稳定的机器报告，并新增使用
  ``pyfcstm.inspect.llm.v1`` 模式的 ``--format llm-json`` 与
  ``--format llm-md``。大语言模型报告包含源码上下文、来源、修复指导和明确禁止事项。
- 扩展静态与验证支持的诊断，包括数值和守卫推理；求解器支持的检查仍受既有显式启用
  与安全门控约束。
- 新增隔离的多提供方修复评测，验证消费者在无法读取隐藏仓库上下文时，是否能定位、
  解释、修复真实诊断并完成重放。

模拟与运行时语义
~~~~~~~~~~~~~~~~

- 强化热启动、伪状态路由、深度优先搜索限制、栈稳定化、推测回滚、表达式短路、持久
  变量归一化、事件所有权、历史长度调整和终止状态查询。
- 新增 :class:`pyfcstm.simulate.CycleResult` 事件记账，并强化抽象处理器注册、装饰器
  扫描、执行上下文、命名动作引用、警告元数据和会话复制行为。
- 扩展共享语义用例语料，使模拟器和生成运行时按周期对齐状态、变量、事件、历史、
  回调与失败行为。

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
