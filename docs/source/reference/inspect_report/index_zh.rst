.. _sec-reference-inspect-report-zh:

Inspect 报告参考
========================================

``pyfcstm inspect`` 有四种输出格式：

.. list-table:: 输出格式
   :header-rows: 1
   :widths: 18 32 50

   * - 格式
     - 契约
     - 使用场景
   * - ``human``
     - 面向人的文本渲染器。
     - 本地调试、教程和评审评论。
   * - ``json``
     - 完整 ``ModelInspect`` JSON 载荷。
     - CI 检查、仪表盘和精确结构清单。
   * - ``llm-json``
     - 面向 LLM 修复提示的稳定紧凑 JSON。
     - 自动修复循环和缺陷报告附件。
   * - ``llm-md``
     - LLM 报告的稳定 Markdown 表达。
     - 面向人的修复交接。

完整 JSON 结构模式（schema）位于 ``pyfcstm/diagnostics/schema.json``。LLM 报告结构模式位于
``pyfcstm/diagnostics/inspect_llm_report_schema.json``。无效输入不会表现为成功报告：语法错误、文件不可读、解码失败、模型校验失败和被禁止的验证策略都是命令行失败。

影响报告的 CLI 选项
----------------------------------------

.. list-table:: Inspect CLI 控制项
   :header-rows: 1
   :widths: 28 22 50

   * - 选项
     - 作用范围
     - 契约
   * - ``--format human``
     - stdout 或 ``-o``
     - 默认渲染器。ANSI 颜色由 ``--color`` 和终端探测决定。
   * - ``--format json``
     - stdout 或 ``-o``
     - 输出完整 ``ModelInspect`` JSON，按键排序并带末尾换行。
   * - ``--format llm-json``
     - stdout 或 ``-o``
     - 输出稳定 LLM JSON，不是完整结构报告。
   * - ``--format llm-md``
     - stdout 或 ``-o``
     - 输出同一套修复信息的 Markdown 表达。
   * - ``--color auto|always|never``
     - 仅 ``human``
     - 机器可读格式会忽略它。
   * - ``--enable-verify``
     - 报告诊断
     - 在配置策略内追加允许进入 inspect 的验证算法。
   * - ``--max-complexity-tier``
     - 验证策略
     - 选择 inspect 接受的最高结构或局部 SMT 复杂度层级。
   * - ``--max-call-count-scaling``
     - 验证策略
     - 选择 inspect 接受的最高模型派生调用次数规模。
   * - ``--smt-timeout-ms``
     - 求解器支持的验证
     - ``None`` 表示命令行不覆盖超时；``0`` 会转交给 Z3，表示没有有限超时。

完整 JSON 顶层字段
----------------------------------------

完整 JSON 报告来自 ``ModelInspect.to_json()``，包含这些必填顶层字段。

.. list-table:: 完整报告顶层字段
   :header-rows: 1
   :widths: 28 72

   * - 字段
     - 含义
   * - ``root_state_path``
     - 根状态的点分路径。
   * - ``states``
     - 叶状态、组合状态和伪状态的 ``StateInfo`` 数组。
   * - ``transitions``
     - 普通转换和展开后转换摘要。
   * - ``variables``
     - 变量摘要，包括读写和守卫影响事实。
   * - ``events``
     - 事件声明和使用摘要。
   * - ``actions``
     - 生命周期、切面、抽象和引用动作摘要。
   * - ``forced_transitions``
     - 作者写的强制转换及其展开数量。
   * - ``combo_transitions``
     - 为机器消费从 ``transitions`` 复制出的组合转换。
   * - ``combo_origins``
     - 按稳定来源标识分组的组合触发器来源信息。
   * - ``metrics``
     - 聚合计数、层级深度、比例和清单。
   * - ``structure_statistics``
     - 面向 LLM 的描述性结构计数和比例。初始边被排除，生成的组合边和强制展开边按作者写的一条转换折叠；该段不会产生告警或综合健康分数。
   * - ``reachability_graph``
     - 默认检查图：忽略守卫，跟随组合状态初始边。
   * - ``event_emission_map``
     - 事件名到可发射它的源状态集合。
   * - ``var_dataflow``
     - 变量名到读写状态路径。
   * - ``aspect_impact_map``
     - 组合状态路径到被切面动作影响的后代叶状态。
   * - ``action_ref_graph``
     - 命名动作签名到被引用命名动作签名。
   * - ``verification``
     - 验证提供方支持情况、请求策略、执行覆盖率，以及每个已注册算法的一条结果记录。
   * - ``diagnostics``
     - ``ModelDiagnostic`` 对象数组。

嵌套对象契约
----------------------------------------

.. list-table:: 主要嵌套对象
   :header-rows: 1
   :widths: 24 76

   * - 对象
     - 必填字段和说明
   * - ``StateInfo``
     - ``path``、``name``、``parent_path``、叶/伪/组合布尔值、子状态、初始目标、生命周期动作数组、切面数组和 ``has_abstract_action``。
   * - ``TransitionInfo``
     - 源/目标、事件、事件作用域、守卫、效果动作、自赋值、强制来源、索引和组合投影 / 来源字段。
   * - ``ComboOriginInfo``
     - ``origin_id``、转换 span、触发器 span 和有序 ``terms``。
   * - ``ComboOriginTermInfo`` / ``ComboOriginRefInfo``
     - 项序号、角色、是否消耗触发项、文本，以及转换 / 触发器 / 项 / 值 / 删除 span。
   * - ``VariableInfo``
     - 名称、类型、初值、读写状态路径、守卫影响标志、抽象动作作用域和浮点字面量赋值。
   * - ``EventInfo``
     - 限定名、声明作用域、使用位置，以及是否声明 / 是否使用。
   * - ``ActionInfo``
     - 签名、状态路径、名称、阶段、切面、引用目标和是否附着。
   * - ``ForcedTransitionInfo``
     - 所属状态、源/目标、触发事实、原始文本和展开数量。
   * - ``ModelMetrics``
     - 状态 / 转换 / 事件 / 变量计数、层级深度、变量到叶状态比例、切面覆盖和抽象动作清单。
   * - ``StructureStatistics``
     - 作者写的转换数量、``transitions_per_state``（``T / S``）、不可达数量/比例，以及守卫/效果/无事件无守卫比例。``S`` 是非伪状态数量；每个比例同时给出分子和分母，空总体返回 ``null``。默认只对三项结构信号给出建议阈值：``T / S <= 6.0``、不可达叶状态比例 ``<= 0.10``、不可达转换比例 ``<= 0.10``；超出只记录元数据，不产生诊断。
   * - ``ModelDiagnostic``
     - ``code``、``severity``、``message``、``span``、``refs`` 和可选 ``suggested_fix``。
   * - ``Span``
     - ``line``、``column``、``end_line`` 和 ``end_column``。

验证执行元数据
----------------------------------------

``verification`` 记录哪些验证能力可用、哪些工作实际执行。它是执行元数据，不是另一组诊断。
算法被禁用、被策略排除或返回不确定结果时，不会仅因该执行结果而生成诊断。特别是，不确定结果中的
部分诊断只公开数量，不公开其载荷。

.. list-table:: 验证报告字段
   :header-rows: 1
   :widths: 28 72

   * - 字段
     - 含义
   * - ``supported`` / ``provider``
     - 当前实现是否具备验证提供方及其稳定名称。jsfcstm 报告 ``supported=false`` 和
       ``provider=null``。
   * - ``enabled`` / ``reason_code``
     - 是否请求了验证。``verification_disabled`` 与 ``provider_unsupported`` 区分两种未运行的顶层状态。
   * - ``requested_policy``
     - 请求的最高复杂度层级、调用次数规模和 SMT 超时。不支持验证的提供方把三者都报告为 ``null``。
   * - ``summary``
     - ``registered``、``executed``、``not_run`` 和 ``indeterminate`` 计数。验证被禁用时不会加载注册表，
       因此 ``registered`` 为 ``null``，``not_run`` 为零，而不是伪造一个与注册表大小相等的计数。
   * - ``algorithms``
     - 有序的算法级元数据，包括声明的诊断码、原始 ``result_kind``、排除原因和
       ``partial_diagnostic_count``。

算法 ``result_kind`` 原样保留 ``sat``、``unsat``、``timeout``、``unknown`` 或
``undecidable_skip``；执行前被排除的算法使用 ``not_run``。SAT 与 UNSAT 并不在所有算法中统一表示
“通过”或“失败”，其极性取决于被检查的性质。因此 human 渲染器只汇报已执行与不确定覆盖率，并且只展开
不确定算法及其原因。

对于 structural/topological 算法，``sat`` 表示结构分析已完成并产生拓扑结果；它不表示模型满足所有性质。
消费者必须结合算法的 diagnostics 与 ``result_kind`` 阅读，不能把 structural ``sat`` 当作普遍的通过结论。

LLM 报告契约
----------------------------------------

``llm-json`` 和 ``llm-md`` 是修复循环使用的表达契约。它们不替代完整报告。
输出不包含 ``verification`` 执行元数据；需要覆盖率或不确定结果的消费者必须使用完整 JSON 报告。
请使用与当前 ``pyfcstm`` 发布版本一同提供的 ``inspect_llm_report_schema.json`` 校验
``llm-json``。公开载荷和 Markdown 表达都不携带产品 schema 版本或状态标记。

结构统计默认只是描述性信息：始终输出原始计数和比例，并记录三项保守的建议阈值。
超出阈值只把字段名加入 ``exceeded_thresholds``，不会生成 G5 健康告警或综合分数。
分母为空时返回 ``null``（human/Markdown 显示 ``N/A``）。调用方可以向
``inspect_model`` 传入 ``StructureStatisticsPolicy``（或部分映射），单项传
``None`` 即可关闭。未来若根据指定语料库设置 cutoff，必须标明语料来源并显式配置，不能从
本报告自行推断。

默认 ``6.0`` 审查触发线参考 PSMBench/RFC2PSM 的 14 个协议汇总值
``T / S = 2.75`` 及其协议级范围（`PSMBench DOI <https://doi.org/10.52202/085713-1899>`_），
但该语料是扁平协议状态机且规模较小，不能定义通用 FCSTM 上限；该值有意取宽，
避免把普通高密度协议状态机标成异常。不可达总体的
``10%`` 默认值是工程审查预算启发式，不是文献给出的质量边界。UML 2.5.1 将
transition 的 ``guard`` 和 ``effect`` 都定义为可选项，因此这两类风格比例不设
默认 cutoff（`OMG UML 2.5.1 <https://www.omg.org/spec/UML/2.5.1/PDF>`_）。

``unguarded_rate`` 只统计 AST 中没有 guard 的作者转换。由于 FCSTM 语法不允许
forced declaration 带 effect，``missing_effect_rate`` 的分母排除 forced 转换。
``eventless_unconditional_rate`` 统计同时没有 event 和 guard 的转换。这些都是
语法层观察，不等价于语义不安全。不可达转换的原因桶有意允许重叠：总数按作者转换
identity 的并集计算，因此同一转换可以出现在多个原因桶中，但总数只计一次。

.. list-table:: LLM 顶层字段
   :header-rows: 1
   :widths: 28 72

   * - 字段
     - 含义
   * - ``status``
     - 整体状态：``ok``、``info``、``warning`` 或 ``error``。
   * - ``input``
     - 输入路径或 ``null``。
   * - ``repair_protocol``
     - 含 ``goal`` 和有序 ``rules`` 的安全修复提示协议。
   * - ``summary``
     - 错误、警告、信息、状态、叶状态、转换、变量和根状态计数，以及 ``structure_statistics`` 对象。
   * - ``diagnostics``
     - 带源码摘录和注册表指导的紧凑诊断条目。

.. list-table:: LLM 诊断字段
   :header-rows: 1
   :widths: 28 72

   * - 字段
     - 含义
   * - ``code`` / ``severity`` / ``message``
     - 与完整报告相同的稳定诊断身份。
   * - ``location``
     - ``path``、``line``、``column``、``end_line``、``end_column`` 或 ``null``。
   * - ``source_excerpt``
     - 锚点行、插入符号和附近上下文行。
   * - ``refs``
     - 从诊断复制的结构化载荷。
   * - ``source``
     - ``inspect-static``、``verify-backed`` 或 ``unknown``。
   * - ``provenance``
     - ``kind`` 和 ``verify_required`` 标志；verify-backed 条目还可能带有
       ``source_ids``，其中是稳定的 ``algorithm_name@verification_scope``
       标识，不包含产品版本或 schema 版本。
   * - ``summary``
     - 诊断码注册表中的 LLM 摘要。
   * - ``recommended_actions`` / ``do_not``
     - 从 ``codes.yaml`` 复制的修复建议和禁止做法。
   * - ``repair_guidance``
     - 渲染器为修复循环生成的短指导。

无效输入边界
----------------------------------------

检查命令会先读取、解码、解析并校验 DSL。任一步失败时，命令会抛出受控 CLI 错误，而不是返回正常检查报告。应把这种情况当作输入失败，而不是带 ``E_*`` 诊断码的 ``diagnostics`` 数组。
