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
     - 接受有界层级；``bmc_search`` 只为报告策略错误而被解析。
   * - ``--max-call-count-scaling``
     - 验证策略
     - 自动 inspect 会拒绝 ``k_unrollings`` 相关标签。
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
   * - ``ModelDiagnostic``
     - ``code``、``severity``、``message``、``span``、``refs`` 和可选 ``suggested_fix``。
   * - ``Span``
     - ``line``、``column``、``end_line`` 和 ``end_column``。

LLM 报告契约
----------------------------------------

``llm-json`` 和 ``llm-md`` 是修复循环使用的表达契约。它们不替代完整报告。

.. list-table:: LLM 顶层字段
   :header-rows: 1
   :widths: 28 72

   * - 字段
     - 含义
   * - ``schema_version``
     - 常量 ``pyfcstm.inspect.llm.v1``。
   * - ``schema_status``
     - 常量 ``stable``。
   * - ``status``
     - 整体状态：``ok``、``info``、``warning`` 或 ``error``。
   * - ``input``
     - 输入路径或 ``null``。
   * - ``repair_protocol``
     - 含 ``goal`` 和有序 ``rules`` 的安全修复提示协议。
   * - ``summary``
     - 错误、警告、信息、状态、叶状态、转换、变量和根状态计数。
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
     - ``kind`` 和 ``verify_required`` 标志。
   * - ``summary``
     - 诊断码注册表中的 LLM 摘要。
   * - ``recommended_actions`` / ``do_not``
     - 从 ``codes.yaml`` 复制的修复建议和禁止做法。
   * - ``repair_guidance``
     - 渲染器为修复循环生成的短指导。

无效输入边界
----------------------------------------

检查命令会先读取、解码、解析并校验 DSL。任一步失败时，命令会抛出受控 CLI 错误，而不是返回正常检查报告。应把这种情况当作输入失败，而不是带 ``E_*`` 诊断码的 ``diagnostics`` 数组。
