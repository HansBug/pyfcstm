.. _sec-reference-bmc-results-zh:

BMC 命令行与结果协议参考
========================

本页冻结 ``pyfcstm bmc`` 的进程与数据契约，覆盖每次调用的一份 FCSTM 模型和一份 FBMCQ
查询、人类可读报告（human report）、``bmc-cli/v1`` JSON 封装（JSON envelope）、见证
解码（witness decode）、运行时重放（runtime replay）、退出状态、错误和可下载的参考
模式（schema）。这是有界结果协议：有界结论（verdict）成功不等于无界证明。

本页的事实源是 :mod:`pyfcstm.entry.bmc`、与本页 reST 源文件并列维护的
``bmc_cli_v1.schema.json``、:mod:`pyfcstm.bmc.witness` 和入口行为测试。
JSON 类型和必需键以模式为准；执行顺序、标准输出/标准错误、
文件副作用和退出状态以入口模块为准。

可用下面的本页目录直接定位选项、输出事务、结论矩阵、人类可读报告、JSON 封装、
见证、重放、错误或消费规则。``.fbmcq`` 语法和上下文合法性请查
:doc:`../bmc_query/index_zh`，不要从结果页反推语法规则。

.. contents:: 本页目录
   :local:
   :depth: 2

下面的注释是命令行参考检查器的同步标记。中英文页面有意使用
逐字相同的标记行。

.. cli-ref-command: name=bmc
.. cli-ref-option: command=bmc option=-i
.. cli-ref-option: command=bmc option=--input-code
.. cli-ref-option: command=bmc option=-q
.. cli-ref-option: command=bmc option=--query-file
.. cli-ref-option: command=bmc option=-o
.. cli-ref-option: command=bmc option=--output
.. cli-ref-option: command=bmc option=--json
.. cli-ref-option: command=bmc option=--timeout-ms
.. cli-ref-option: command=bmc option=--max-bound
.. cli-ref-option: command=bmc option=--color choices=auto,always,never default=auto
.. cli-ref-option: command=bmc option=--help
.. cli-ref-boundary: command=bmc stdout stderr exit-status side-effects success-signal failure-taxonomy human json atomic-output witness replay dual-check response-cause packaging property-verdict color timing llm-consumption

调用形式与冻结选项面
--------------------

安装后的两种入口行为相同：

.. code-block:: console

   pyfcstm bmc -i machine.fcstm -q property.fbmcq [OPTIONS]
   python -m pyfcstm bmc -i machine.fcstm -q property.fbmcq [OPTIONS]

.. list-table:: 选项
   :header-rows: 1
   :widths: 22 18 20 40

   * - 选项
     - 取值
     - 必需/默认值
     - 精确行为
   * - ``-i, --input-code``
     - 路径文本
     - 必需
     - 使用支持导入的模型加载器加载一份 FCSTM 模型；不接受标准输入。
   * - ``-q, --query-file``
     - 路径文本
     - 必需
     - 读取并自动解码一份 FBMCQ 查询文件。CLI 不接受行内查询文本、标准输入或
       多查询文件。
   * - ``-o, --output``
     - 路径文本
     - 未设置；标准输出
     - 不写标准输出，改为把完整人类可读/JSON 报告写入 UTF-8 文件。原子替换已有文件，
       不创建缺失的父目录。
   * - ``--json``
     - 标志
     - 假；人类可读
     - 选择稳定的 ``bmc-cli/v1`` JSON 封装；有意不提供重叠的 ``--format``。
   * - ``--timeout-ms``
     - 整数，``>= 1``
     - 未设置；Z3 无超时
     - 为一次公共求解建立一个总预算，由所有分阶段 Z3 ``check()`` 共享；不限制加载、解析、
       展开、公式构造、见证解码或重放。
   * - ``--max-bound``
     - 整数，``>= 1``
     - 未设置；无 CLI 上限
     - 构造 ``BmcOptions(max_bound=N)``。查询边界大于 ``N`` 时，在关系
       构造前作为受控编译错误拒绝；不会改写或截断查询边界。
   * - ``--color``
     - ``auto``、``always`` 或 ``never``
     - ``auto``
     - 只控制人类可读输出。``auto`` 要求终端输出、遵守 ``NO_COLOR``，并在
       ``TERM=dumb`` 时关闭颜色；``always`` 可以显式强制管道颜色。JSON 和
       ``--output`` 文件始终不含 ANSI 转义序列。
   * - ``-h, --help``
     - 标志
     - 可选
     - 打印 Click 帮助并以 ``0`` 退出，不加载任一输入。

两个数值选项的零值和负值都是 Click 用法错误（usage error）。缺少必需选项和未知选项
同样是用法错误，均退出 ``2``。路径按用户提供的字符串传递，JSON 也原样记录；CLI 不会
把它们规范化为绝对路径。

执行与输出事务
--------------

一次调用按固定顺序执行：

#. 使用支持导入的加载器加载 FCSTM 模型。
#. 读取并解码 FBMCQ 文件。
#. 编译恰好一条查询；如有 ``--max-bound``，在此应用。
#. 求解主性质目标。
#. 如果主结果为 UNSAT，检查 ``S_assume``，必要时继续检查 ``S_init`` 和
   ``K_N``；只有确认允许场景可行后，才解释主目标的 UNSAT。
#. 如果场景可行且性质暴露非假的边界不完整公式，在同一个总截止时间内
   执行该诊断检查。
#. 如果选出了 SAT 模型，使用结果绑定的解码器生成 ``bmc-witness/v2``
   轨迹，并以 ``abstract_handlers=None`` 交给 ``SimulationRuntime`` 重放。
   兼容 API ``decode_bmc_witness`` 仍生成 ``bmc-witness/v1``。
#. 计算最终退出码，一次性构造完整报告，再写标准输出或原子替换 ``--output``。
#. 以 JSON ``exit_code`` 记录的同一数值退出。

求解、强制 SAT 解码和强制 SAT 重放完成前不会输出报告。CLI 没有
``--no-replay`` 或 ``--no-incomplete-check`` 绕过选项。重放会记录抽象动作
调用，但 CLI 不注入可修改重放状态或变量的用户处理器。

.. list-table:: 输出路由与文件副作用
   :header-rows: 1
   :widths: 18 18 18 23 23

   * - 分支
     - 标准输出
     - 标准错误
     - ``--output``
     - 已有目标文件
   * - 有报告的结论，未指定 ``-o``
     - 完整报告
     - 空
     - 未使用
     - 不变
   * - 有报告的结论，指定 ``-o``
     - 空
     - 空
     - 完整报告
     - 原子替换；exit ``1``、``3``、``4`` 也会替换
   * - 受控输入/编译错误
     - 空
     - 简洁 Click 错误
     - 不创建、不修改
     - 保留
   * - Click 用法错误
     - 空
     - 用法和错误文本
     - 不创建、不修改
     - 保留
   * - 内部求解/解码/重放失败
     - 空
     - 意外错误横幅和回溯
     - 不产生半成品报告
     - 保留
   * - 输出写入失败
     - 空
     - 简洁 Click 错误
     - 不产生声称成功的载荷
     - 替换未完成时保留原目标

原子输出的含义是：在目标目录创建临时文件，以 UTF-8 和 ``\n`` 换行编码，写入、刷新、
``fsync``、关闭，再调用 ``os.replace``。不会创建父目录。写入或替换失败时会尝试删除
临时文件；若清理也失败，会同时暴露两项失败。原子替换是同文件系统上的单文件操作，
不是多文件事务，也不承诺目录元数据已经持久化。

退出状态与结论矩阵
-----------------------

退出优先级依次是重放不匹配 ``4``、无定论 ``3``，然后才是有界性质结论的
``0`` 或 ``1``。决定性负结果不是进程/协议错误：它仍输出完整报告。

.. list-table:: 进程退出状态
   :header-rows: 1
   :widths: 10 30 30 30

   * - 退出状态
     - 含义
     - 报告行为
     - 修复/消费动作
   * - ``0``
     - 有界性质满足，且任何强制 SAT 重放均匹配。
     - 完整人类可读/JSON 报告。
     - 消费 ``result.outcome``；不要把结论推广到边界之外。
   * - ``1``
     - 决定性有界负结论；或受控输入、编译、读取、写入错误；或内部失败。
     - 负结论输出完整报告；受控/内部错误只写标准错误。
     - 区分带 ``result`` 的报告与仅标准错误失败。
   * - ``2``
     - Click 用法错误。
     - 标准错误上的用法；无报告。
     - 修复缺失/未知选项，数值必须为正整数。
   * - ``3``
     - 求解器 ``unknown``/``timeout``、可行性检查无定论、场景不可行，或
       ``response`` 边界 ``incomplete``。
     - 完整报告；场景不可行和可行性无定论分支的 ``witness``/``replay`` 为
       ``null``；SAT suffix 可以同时存在两者。
     - 先看 ``result.outcome``，再决定增加超时还是边界。
   * - ``4``
     - SAT 成功解码，且重放返回结构化结果，但 ``replay.ok == false``。
     - 完整结果、见证、重放和不匹配项。
     - 视形式化/运行时对齐为不可信，检查不匹配项。

.. list-table:: 有报告分支的完整矩阵
   :header-rows: 1
   :widths: 17 14 18 22 12 17

   * - 性质/目标分支
     - 主状态
     - ``result.outcome``
     - ``witness`` / ``replay``
     - 退出状态
     - 解释
   * - 见证极性：``reach``、``exists_always``、``cover``；目标 SAT
     - ``sat``
     - ``witness_found``
     - 对象 / 对象，重放通过
     - ``0``
     - 找到所需的有界见证。
   * - 见证极性；目标 UNSAT
     - ``unsat``
     - ``no_witness``
     - ``null`` / ``null``
     - ``1``
     - 边界内没有见证。
   * - 反例极性：``forbid``、``invariant``、``must_reach``、
       ``response``；目标 SAT
     - ``sat``
     - ``property_violated``
     - 对象 / 对象，重放通过
     - ``1``
     - 找到有界反例。
   * - 反例极性，非 ``response``；目标 UNSAT
     - ``unsat``
     - ``property_satisfied``
     - ``null`` / ``null``
     - ``0``
     - 边界内没有反例。
   * - ``response`` 目标 UNSAT；后缀检查 UNSAT 或不需要
     - ``unsat``
     - ``property_satisfied``
     - ``null`` / ``null``
     - ``0``
     - 没有完整窗口违反，也没有未覆盖的尾部触发条件。
   * - ``response`` 目标 UNSAT；后缀检查 SAT、``unknown`` 或 ``timeout``
     - ``unsat``
     - ``incomplete``
     - ``null`` / ``null``
     - ``3``
     - 有界尾部不足以给出确定的满足结论。
   * - 任意主目标 ``unknown``
     - ``unknown``
     - ``unknown``
     - ``null`` / ``null``
     - ``3``
     - 求解器没有确定结论；可用时由 ``reason`` 说明原因。
   * - 任意主目标 ``timeout``
     - ``timeout``
     - ``timeout``
     - ``null`` / ``null``
     - ``3``
     - 单次检查超时。
   * - 任意主目标 SAT；解码成功；重放返回不匹配项
     - ``sat``
     - 由极性决定
     - 对象 / 对象，重放未通过
     - ``4``
     - 重放信任门禁覆盖性质自身的退出码。

人类可读报告
--------------

人类可读输出先报告有界性质结论，再展示求解器机制。首行严格采用以下五种形状之一：

.. code-block:: text

   BMC <kind> <= <bound>: PROPERTY HOLDS
   BMC <kind> <= <bound>: PROPERTY DOES NOT HOLD
   BMC <kind> <= <bound>: PROPERTY INCONCLUSIVE
   BMC <kind> <= <bound>: REPLAY MISMATCH; PROPERTY VERDICT UNTRUSTED
   BMC <kind> <= <bound>: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED

下一句解释已经按极性换算的结果。随后 ``Solver`` 显示主检查状态与毫秒耗时；设置后还会
显示所有分阶段检查共享的总超时预算、响应窗口检查状态与耗时、求解器原因和诊断。SAT 结果再显示重放状态与
紧凑轨迹，每行采用 ``源状态 -> 目标状态 [分支；事件；调用]``。事件和调用各预览前三项，
其余项显示省略数量。重放不匹配会逐条显示路径和消息。

末段始终说明有界结果的限制，并引导使用 ``--json`` 获取完整见证、运行时轨迹、不匹配和
稳定诊断。各节之间恰好一个空行，报告末尾恰好一个换行。``--color auto`` 在终端中用绿色
表示性质成立、红色表示不成立或重放不匹配、黄色表示无定论和有界提醒、青色表示诊断标签；
颜色不会进入 JSON 或文件。脚本和大语言模型集成必须使用 ``--json``，不得解析人类文案、
ANSI 或实时耗时。

JSON 封装
-------------

JSON 使用 UTF-8、两空格缩进、递归键排序、保留非 ASCII 字符，并以一个换行结尾。模式
中声明 ``additionalProperties: false`` 的每个对象都拒绝未声明键。原始 Z3 模型和
完整 SMT 公式有意不输出。

.. list-table:: 顶层 ``bmc-cli/v1`` 字段
   :header-rows: 1
   :widths: 20 22 15 43

   * - 字段
     - 类型/允许值
     - 始终存在
     - 含义
   * - ``schema_version``
     - string，固定为 ``bmc-cli/v1``
     - 是
     - 封装版本判别字段。
   * - ``input``
     - 对象
     - 是
     - ``model_path`` 和 ``query_path`` 是用户提供的路径字符串。
   * - ``property``
     - 对象
     - 是
     - 编译后性质身份：``kind``、``polarity``、``bound``、可空
       ``case_label`` 和仅 ``response`` 使用的 ``response_window``。
   * - ``result``
     - 对象
     - 是
     - 规范 ``BmcSolveResult`` 摘要。
   * - ``witness``
     - 对象或 ``null``
     - 是
     - CLI 选出主模型或 suffix 模型时为 ``bmc-witness/v2``；没有模型角色时为
       ``null``。
   * - ``replay``
     - 对象或 ``null``
     - 是
     - 选出模型角色时为运行时重放结果，否则为 ``null``。
   * - ``exit_code``
     - ``0, 1, 3, 4`` 之一
     - 是
     - 有报告分支的准确进程退出码镜像。用法错误和仅标准错误的错误没有封装。

``property.kind`` 是 ``reach``、``forbid``、``invariant``、``must_reach``、
``exists_always``、``response``、``cover`` 之一；``property.polarity`` 是
``witness`` 或 ``counterexample``；``bound`` 是至少为 1 的整数；``case_label`` 是
字符串或 ``null``；``response_window`` 对 ``response`` 是正整数，对其他类别是 ``null``。

.. list-table:: ``result`` 字段
   :header-rows: 1
   :widths: 24 24 52

   * - 字段
     - 类型/值
     - 契约
   * - ``node``
     - 固定为 ``bmc_solve_result``
     - 规范节点判别字段。
   * - ``schema_version``
     - 运行时固定为 ``bmc-solve-result/v2``
     - 嵌套结果版本；外层封装仍是 ``bmc-cli/v1``。
   * - ``kind``, ``polarity``
     - 与 ``property`` 相同的闭集
     - 从已求解公式复制的身份。
   * - ``status``
     - ``sat``、``unsat``、``unknown``、``timeout``
     - 主目标求解器状态；不能直接当作通用成功标志。
   * - ``property_satisfied``
     - 布尔值或 ``null``
     - 考虑极性的有界结论；无定论时为 ``null``。
   * - ``witness_found``
     - 布尔值
     - 仅见证极性目标 SAT 时为真。
   * - ``counterexample_found``
     - 布尔值
     - 仅反例极性目标 SAT 时为真。
   * - ``incomplete``
     - 布尔值
     - 主目标 ``unknown``/``timeout`` 或 ``response`` 边界未决时为真。
   * - ``outcome``
     - ``property_satisfied``、``property_violated``、``witness_found``、
       ``no_witness``、``incomplete``、``timeout``、``unknown``、
       ``scenario_infeasible``、``feasibility_timeout``、
       ``feasibility_unknown``
     - 稳定的消费方分类，应与 ``exit_code`` 一起使用。
   * - ``reason``
     - 字符串或 ``null``
     - 仅主目标 ``unknown``/``timeout`` 时保存原始原因；SAT/UNSAT 时为 ``null``。
   * - ``elapsed_ms``
     - 有限数值，``>= 0``
     - 主检查墙钟时间；本质上不确定。
   * - ``timeout_ms``
     - 正整数或 ``null``
     - 本次调用中所有分阶段检查共享的一次总超时预算。
   * - ``has_model``
     - 布尔值
     - 仅主目标有 SAT 模型时为真；原始模型不输出。
   * - ``incomplete_status``
     - 状态枚举或 ``null``
     - 独立边界不完整检查的状态。
   * - ``incomplete_reason``
     - 字符串或 ``null``
     - 次检查无定论原因；次检查 SAT/UNSAT 时为 ``null``。公式暴露次检查时，CLI 总会启用它。
   * - ``has_incomplete_model``
     - 布尔值
     - 仅次检查有 SAT 模型时为真；原始模型不输出。
   * - ``incomplete_elapsed_ms``
     - 有限数值或 ``null``
     - 次检查实际执行时的耗时。
   * - ``total_elapsed_ms``
     - 有限且至少为 0 的数值
     - Python 侧公共求解端到端区间，包含分阶段结果对象的构造耗时。
   * - ``feasibility``
     - 对象
     - ``K_N``、``S_init``、``S_assume`` 的阶段证据；已检查的
       ``unknown``/``timeout`` 不能升级成 ``scenario_infeasible``。
   * - ``available_model_roles``
     - 封闭角色字符串数组
     - ``primary_witness``、``primary_counterexample`` 或
       ``incomplete_suffix``。
   * - ``diagnostics``
     - 字符串数组
     - 求解器/公式诊断；可含不确定的 ``incomplete_elapsed_ms=...``。

黄金测试对 ``elapsed_ms`` 和次检查耗时诊断应固定假值或检查范围，不能精确
比较实时耗时。键集合、枚举、可空性和其他稳定值仍应精确检查。

可行性与模型角色
------------------

``result.outcome == "scenario_infeasible"`` 表示已经证明 ``S_assume`` 不可满足。
这不是性质失败：``property_satisfied`` 为 ``null``，没有可用模型角色，并且会跳过
response suffix 检查。``S_assume`` 可行时，主目标 SAT 模型会被标记为
``primary_witness`` 或 ``primary_counterexample``；主目标 UNSAT 且 ``Psi_q`` SAT 的
response 结果会被标记为 ``incomplete_suffix``。该轨迹可以用于重放有限前缀，但脱离的
性质结论仍然是 ``incomplete``。

``timeout_ms == null`` 表示不向 Z3 设置超时。有限值是一次公共总预算，由主目标、可行性、
定位和 suffix 检查共同消耗；预算耗尽后不会启动后续检查。

见证字段
------------

CLI 输出的 ``witness`` 使用 ``schema_version == "bmc-witness/v2"``，根节点增加
``model_role`` 和 ``verdict``。兼容 API ``decode_bmc_witness`` 继续输出 v1；在 v2 中
``model_role`` 位于见证根节点，不位于 ``solver`` 内。

.. list-table:: 见证根节点与嵌套记录
   :header-rows: 1
   :widths: 24 25 51

   * - 路径/记录
     - 字段
     - 含义与约束
   * - ``witness.property``
     - ``kind``、``polarity``、``bound``、``case_label``、``response_window``
     - 与封装中的性质形状相同。
   * - ``witness.solver``
     - ``model_status``、``primary_status``、``incomplete_status``、耗时和原因字段
     - 选中的模型状态为 SAT；``incomplete_suffix`` 的主状态为 UNSAT、次状态为 SAT；
       已完成的 SAT/UNSAT 检查原因为 ``null``。
   * - ``witness.model_role`` 和 ``witness.verdict``
     - 封闭角色和脱离的结论对象
     - 角色与结论必须一致；suffix 重放不能被提升为性质结论。
   * - ``witness.initial``
     - ``mode``、``state``、``sentinel``、``vars``
     - 重放初始化元数据。状态可为 ``null``；哨兵为 ``init``、``terminated`` 或
       ``null``；变量是 JSON 稳定映射。
   * - ``witness.frames[]``
     - ``index``、``state_id``、``state``、``sentinel``、``terminated``、``vars``
     - 解码后的符号帧。哨兵帧的状态标识/路径为 ``null``；``terminated``
       与哨兵一致。
   * - ``witness.steps[]``
     - ``index``、``source_frame``、``target_frame``、``case_label``、
       ``case_kind``、``progress``、``source_state``、``target_state``、
       ``delta``、``gamma``、``input_events``、``event_reads``、
       ``abstract_calls``、``consumed_events``、``unconsumed_events``
     - 一个解码后的宏步。哨兵对应的源/目标状态可为 ``null``。
       事件消费有顺序；未消费事件等于重放输入减去已消费事件。
   * - ``witness.diagnostics``
     - 字符串数组
     - 解码诊断。

每个事件对象有 ``path``\ （全限定事件路径）、``reason``\ （解码来源）和布尔值
``model_value``。重放的 ``input_events`` 只包含值为真且原因为
``case_positive``、``explicit_true_assumption`` 或 ``property_support`` 的事件。
调试用 ``event_reads`` 使用 ``negative_case_read``、``explicit_false_assumption`` 或
``model_debug``，不作为重放输入。

每条抽象调用记录有 ``ordinal``、``action_name``、``stage``、``role``、
``state``、``active_leaf``、可空 ``named_ref`` 和调用前变量 ``snapshot``。CLI 在重放
中记录调用，但不提供用户处理器行为。JSON 稳定映射允许 ``null``、布尔值、有限数值、
字符串、数组和字符串键嵌套对象；非有限数值与原始 Python/Z3 对象
不是公开 JSON 值。模式的复用 ``stringMap`` 有意较宽，而当前见证发射器把
帧/运行时 ``vars`` 和调用 ``snapshot`` 的值限制为有限整数或浮点数。消费方可以
依赖模式有效性，但不能自行构造一个只满足模式上限的轨迹，就假定 Python
构造器一定接受其中每一种值。

重放字段与信任边界
---------------------

仅当 ``mismatches`` 为空时 ``replay.ok`` 为真。完整重放对象包含：

.. list-table:: 重放记录
   :header-rows: 1
   :widths: 25 28 47

   * - 路径/记录
     - 字段
     - 含义
   * - ``replay``
     - ``ok``、``runtime_trace``、``mismatches``
     - 结构化对齐结论、运行时观测和全部不匹配项。
   * - ``runtime_trace.frames[]``
     - ``index``、``state``、``terminated``、``vars``
     - 重放后的公开运行时帧；与见证帧不同，没有符号 ``state_id`` 或
       哨兵字段。
   * - ``runtime_trace.steps[]``
     - ``index``、``input_events``、``consumed_events``、
       ``unconsumed_events``、``abstract_calls``
     - 实际运行时事件账目和记录的抽象调用。
   * - ``mismatches[]``
     - ``path``、``expected``、``actual``、``message``、``tolerance``
     - 一项比较失败。期望值/实际值是 JSON 值；容差是非负数值或 ``null``。

重放是针对已解码有界轨迹的运行时对齐判据，不是独立无界证明。因为 CLI 使用
``abstract_handlers=None``，成功也不验证任意用户抽象处理器实现。只有重放
返回带不匹配项的 ``BmcReplayResult`` 才产生退出状态 ``4``。若在结果形成前抛异常，则属于
内部失败：退出状态 ``1``、打印回溯、无半成品 JSON/人类可读报告。

双检查与 ``response`` 原因边界
-----------------------------------

每种性质都执行一次主检查。只有公式具有非假的边界不完整观察时才执行
第二次检查；当前非平凡情形是 ``response``。所有分阶段检查共享一次完整的 ``--timeout-ms``
总预算；后续检查只能使用剩余预算，预算耗尽后不会启动新的检查。

.. list-table:: ``response`` 双检查解释
   :header-rows: 1
   :widths: 18 20 20 16 26

   * - 主检查
     - 次不完整检查
     - 结果
     - 退出状态
     - 说明
   * - SAT
     - 任意/不影响决定性
     - ``property_violated``
     - ``1`` 或重放 ``4``
     - 完整反例已经决定性质结论。
   * - UNSAT
     - UNSAT 或公式为假
     - ``property_satisfied``
     - ``0``
     - 没有完整违反，也没有未覆盖的后缀触发条件。
   * - UNSAT
     - SAT
     - ``incomplete``
     - ``3``
     - 未覆盖的触发窗口可能延伸出边界。
   * - UNSAT
     - ``unknown`` 或 ``timeout``
     - ``incomplete``
     - ``3``
     - 后缀诊断无定论。
   * - ``unknown``/``timeout``
     - 任意
     - ``unknown``/``timeout``
     - ``3``
     - 主目标自身无定论。

``response`` 反例可能来自未定义触发条件，也可能来自已定义触发条件的完整窗口内没有
响应。二者属于同一个反例目标；当前都会产生 SAT、
``property_violated``，且重放匹配时退出状态为 ``1``。``result.outcome`` 和
``bmc-witness/v2`` 均不提供稳定、机器可读的原因判别字段。人可以结合原查询和轨迹
检查；脚本不得推断或依赖协议中不存在的原因分类。

错误分类
--------------

.. list-table:: 失败与可观测性
   :header-rows: 1
   :widths: 22 34 28 8 8

   * - 类别
     - 来源
     - 可观测契约
     - 退出状态
     - 报告
   * - Click 用法错误
     - 缺少必需选项、未知选项、非整数或非正数值
     - 标准错误上的用法/错误文本
     - ``2``
     - 无
   * - 受控模型输入
     - 主模型缺失、文件系统/权限错误、解码错误、FCSTM 文法错误、模型
       验证错误
     - 以受控模型操作开头的简洁标准错误
     - ``1``
     - 无
   * - 受控查询输入
     - FBMCQ 文件缺失、读取失败、解码失败
     - 简洁标准错误
     - ``1``
     - 无
   * - 受控 BMC 编译输入
     - 查询解析/绑定错误、不支持的查询、用户触发的定义域/编码/构造
       验证、``max_bound`` 策略拒绝
     - 标准错误上的 ``Failed to compile BMC query: ...``
     - ``1``
     - 无
   * - 决定性负结论
     - 见证极性未找到见证，或 SAT 反例
     - 完整选定格式报告；标准错误为空
     - ``1``
     - 有
   * - 无定论结论
     - 求解器 ``unknown``/``timeout``、``response`` 边界不完整
     - 完整选定格式报告；标准错误为空
     - ``3``
     - 有
   * - 结构化重放不匹配
     - 解码成功，重放返回一项或多项不匹配
     - 完整结果、见证和重放报告
     - ``4``
     - 有
   * - 输出失败
     - 临时文件创建、UTF-8 写入、刷新/同步、替换或清理失败
     - 标准错误上的 ``Failed to write BMC output file ...``
     - ``1``
     - 无成功报告
   * - 内部一致性失败
     - 内部 BMC 哨兵、求解不变量失败、见证解码异常、
       重放异常或其他意外异常
     - 意外错误横幅和回溯；保留缺陷哨兵
     - ``1``
     - 无

识别的内部 BMC 文本哨兵是 ``internal BMC bug:``、``internal error:`` 和
``internal BMC witness consistency error``，不会被降级成用户输入错误。退出状态 ``4`` 绝不
用于异常；它只表示一个已完整构造、可检查的不匹配结果。

可复现示例
----------

假设 ``machine.fcstm`` 的内容是 ``state Root;``。每条命令的查询文件只包含所示语句。

**例 1：正向见证。** 在 ``reach.fbmcq`` 中写入
``check reach <= 1: active("Root");``：

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q reach.fbmcq --json
   {
     "exit_code": 0,
     ...
     "result": {"outcome": "witness_found", "status": "sat", ...},
     "replay": {"mismatches": [], "ok": true, ...},
     "witness": {"schema_version": "bmc-witness/v2", "model_role": "primary_witness", ...}
   }

这是示意摘录，因为美化并排序后的 JSON 在这些行之间还有其他键，
且实时耗时会变化。完整载荷可通过可下载的参考模式校验。

**例 2：反例是负结论，不是 CLI 错误。** 在 ``forbid.fbmcq`` 中写入
``check forbid <= 1: active("Root");``：

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q forbid.fbmcq --json > result.json
   $ echo $?
   1

``result.json`` 完整存在：``status`` 为 ``sat``，``outcome`` 为
``property_violated``，见证/重放都是对象；标准错误为空。

**例 3：** ``response``\ 边界不完整。在 ``response.fbmcq`` 中写入
``check response <= 1: trigger true -> within 2 false;``：

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q response.fbmcq --json -o response.json
   $ echo $?
   3

标准输出和标准错误均为空；``response.json`` 的主 ``status: unsat``、
``incomplete_status: sat``、``outcome: incomplete``，且 ``exit_code: 3``。
由于 suffix 模型可用，``witness`` 和 ``replay`` 是带有 ``bmc-witness/v2`` 与
``model_role: incomplete_suffix`` 的对象；它们只描述可执行前缀，不会把脱离的结果提升为性质结论。
如需确定边界，应增大查询边界。

**例 4：策略拒绝只写标准错误，并保留输出文件。** 在 ``large.fbmcq`` 中写入
``check reach <= 2: active("Root");``，并假设 ``result.json`` 已存在：

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q large.fbmcq --max-bound 1 \
       --json -o result.json
   Error: Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1. ...

命令退出 ``1``，不输出 JSON，并保持旧 ``result.json`` 不变。``-o`` 的父目录不存在时
同样失败，不会自动创建目录。

模式下载与消费方检查
--------------------

:download:`下载规范的 bmc-cli/v1 JSON Schema
<bmc_cli_v1.schema.json>`。

这个模式是参考资料，不是运行时依赖。Sphinx 通过上面的下载链接发布它；不要根据
当前页面的渲染后网址推测模式网址。它有意不放入 ``pyfcstm`` wheel、源码发行包或
独立可执行文件。需要结构校验的消费方应下载或随自己的集成固定保存对应版本的模式，
再读取本地副本：

.. code-block:: python

   import json
   from pathlib import Path

   schema = json.loads(
       Path("bmc_cli_v1.schema.json").read_text(encoding="utf-8")
   )

使用 ``jsonschema`` 时，先把模式自身按 Draft 2020-12 校验，再校验完整矩阵中各个有
报告分支的代表性封装。tools-only BMC 文档检查负责校验该资料，并拒绝
``pyfcstm/entry`` 下重新出现副本。模式的 ``$id`` 是标识符；消费方在校验时不应依赖
联网获取它。

消费方规则
----------

* 先按进程退出状态和 JSON 报告是否存在分支。仅凭退出状态 ``1`` 无法区分负结论与
  仅标准错误失败。
* JSON 存在时，要求 ``schema_version == "bmc-cli/v1"``，并验证
  ``payload.exit_code`` 等于进程退出状态。
* 使用 ``result.outcome`` 和 ``result.polarity``；绝不能把 SAT 当作通用成功。
* 退出状态 ``3`` 是一个进程类别，但在调整超时或边界前，要区分 ``timeout``、``unknown``、
  可行性失败、场景不可行和 ``response`` 不完整。无定论的 response 结果仍可能包含
  suffix 模型。
* 退出状态 ``4`` 是可检查的信任失败；不要与异常或性质反例混淆。
* 不要解析人类可读表格、依赖实时耗时、期待原始模型/公式、推断 ``response``
  原因，也不要假设重放能证明已解码有界轨迹之外的行为。
