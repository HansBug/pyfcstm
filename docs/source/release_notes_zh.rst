版本说明
========

未发布
------

强制转换
~~~~~~~~

来源状态 ``S`` 内部还有状态的强制转换（forced transition）\ ``!S -> T``\ ，现在在所有模型里按同一种方式执行：事件和条件只在状态机停驻的那个状态上判断一次，向上退出的途中不再重新判断。此前的版本会在 ``S`` 之下的每个状态上各放一份事件和条件的副本，伪状态（pseudo state）也不例外，并在退出逐层上行时把每份副本重新判断一遍。不含强制转换的模型不受影响。含强制转换的模型有四类行为变化：

- **条件引用来源状态内部的状态。**\ ``!P -> Q : if [active("Root.P.a2")];``\ 在状态机停驻于 ``a2`` 时成立并被执行。此前它会在 ``a2`` 已经退出之后再判断一次，而那时条件不可能成立。
- **退出动作改掉了条件读取的变量。**\ 条件不会在途中的退出动作执行之后再判断，所以退出动作不能在半途取消这条转换、让状态机留在原来的状态。
- **进入途经伪状态。**\ 强制转换不会从伪状态上发起。如果在经由伪状态进入 ``S`` 的那个周期里它的事件或条件已经成立，现在会先完成进入，强制转换在下一个周期执行。
- **目标无法进入。**\ 此时强制转换什么都不做：它不会离开状态机停驻的状态，也不消费事件，离开 ``S`` 的其他转换也不会在半途接手。停驻状态自己的转换照常参与判断。

``CycleResult.consumed_events``\ 里，强制转换的事件只列出一次；此前每离开一层就列出一次。

有三样东西变得可见：

- 每条这样的声明用一个隐藏的 ``int`` 变量 ``__forced_<n>`` 来执行；模型已经用掉的名字会被跳过。它和 ``__hist_*`` 一样出现在 ``StateMachine.defines``\ 、\ ``runtime.vars``\ 、抽象处理器的变量快照和生成代码的变量表里，并且在所有地方都是普通变量：热启动（hot start）像对待其他变量一样要求提供它，BMC 也像对待其他变量一样对待它。状态机只在一个周期内部把它置起，所以每一个停驻点上它都是 0。\ :attr:`pyfcstm.model.model.StateMachine.forced_variables`\ 给出这些名字。
- 处在强制退出途中的状态上，带事件的转换会经由一个生成的伪状态 ``__forced_gate_<n>`` 拆成两步。这个伪状态出现在 ``walk_states()`` 里，在执行轨迹中表现为多经过一个状态。
- ``to_ast_node()``\ 导出实际运行的状态机，包含上述变量和伪状态，与历史的现有做法一致。从导出文本加载的模型就是同一台状态机：逐周期行为相同，热启动相同，每个可达性和 BMC 问题的答案也相同。例外是强制转换要把某个状态的全部 region 一起带走的模型：它仍把所有强制转换按旧的展开形式导出，从这份文本加载的状态机行为可能不同。

PlantUML、图形查看器和 ``pyfcstm inspect`` 仍然把一条强制转换展示为它作用到的每个状态上各一条转换。对含任何强制转换声明的模型（包括来源状态是叶子的），它们展示的是加载时的模型：加载之后再修改模型对象，改动不会出现在这些展示里。来源状态内部没有任何状态的声明保持为每个来源状态一条转换，也不产生隐藏变量。在收集模式（\ ``parse_dsl_node_to_state_machine(..., collect=True)``\ ）下，一条写错的强制转换声明只报告一次，不再按展开的层数重复报告。

实际运行的状态机上没有任何强制转换声明的痕迹：它的转换都不带 ``Transition.is_forced`` 标记，也没有 ``forced_origin``。它就是普通的 FCSTM，所有执行它、或回答与它有关的问题的环节，包括仿真器、生成的运行时、BMC、\ :mod:`pyfcstm.verify`\ 里的分析和 :mod:`pyfcstm.diagnostics.analyzers`\ 里的分析器，都按它本来的样子处理，会遇到生成的转换和门状态 ``__forced_gate_<n>``，自己用 ``walk_states()`` 和 ``State.transitions`` 遍历的代码也一样。标记只存在于按书写的模型里，图形和 :func:`pyfcstm.diagnostics.inspect.inspect_model`\ 就是从它构建的，所以针对声明本身的告警，例如 ``W_FORCED_GUARD_UNSAT``\ ，来自 inspect 报告；单条转换的算法 ``forced_guard_unsat_under_init`` 也只会报告被传入时带着标记的转换。

如果代码把含强制转换的模型的 ``StateMachine.defines``\ 、\ ``walk_states()``\ 或导出的 DSL 文本与保存的期望值比较，需要更新期望值。从 ``runtime.vars`` 取得的热启动快照要连同其中的 ``__forced_*`` 项一起保存和提供，与其他变量一样。

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
