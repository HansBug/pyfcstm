UNSAT 证明 API 参考
===================

本参考覆盖 :mod:`pyfcstm.solver.proof`、:mod:`pyfcstm.solver.unsat` 和
:mod:`pyfcstm.solver.symbols` 中的独立 API。
示例见 :doc:`/tutorials/unsat_proofs/index_zh` 与 :doc:`/how_to/unsat_proofs/index_zh`。
现有 BMC 命令保持原有合同。

输入与入口
----------

.. code-block:: python

    UnsatConstraint(stable_id, expressions, source=None)
    UnsatQuery(query_id, constraints, background=())
    explain_unsat(query, *, mode="proof", minimize=False, timeout_ms=None,
                  names=None, extensions=None)

``stable_id`` 和 ``query_id`` 为非空字符串。``expressions`` 为非空的 Z3 布尔表达式可迭代对象。
同一查询中的表达式共享一个上下文，条件和背景之间的 ID 也必须唯一。
空查询合法且为 SAT。Python ``True`` 不是 Z3 表达式，应使用 ``z3.BoolVal(True)``。
集合输入会固定为元组。

.. list-table:: 入口选项
   :header-rows: 1
   :widths: 22 28 50

   * - 参数
     - 默认值／允许值
     - 合同
   * - ``mode``
     - ``"proof"``；``"core"``
     - 请求原生证明，或仅请求经过检查的核证据。
   * - ``minimize``
     - ``False``；布尔值
     - 删除可移除条件组；证明模式下对选定子集重新求证。不优化最小基数。
   * - ``timeout_ms``
     - ``None``；排除布尔值的正整数
     - 以毫秒计的共享协作式期限。``None`` 表示不限时。
   * - ``names``
     - ``None``；``SymbolNames``
     - 通过 ``register(symbol, display)`` 登记实际符号。冲突的显示名称会被拒绝。
   * - ``extensions``
     - ``None``；``ProofExtensions``
     - 每次调用的规则解释器、来源适配器和阅读合并器；没有全局注册表。

``explain_unsat_core(query, *, selected_ids=None, minimize=True, timeout_ms=None)``
是底层核 API。它默认 ``minimize=True``，与 ``explain_unsat`` 不同。
``selected_ids`` 显式选择可移除来源出现位置，ID 必须已知且不重复。
即使是显式选择，也会在不恢复已省略条件的情况下独立复查。
使用 ``minimize=False`` 可保留这个选择。
其 ``UnsatCoreResult.query`` 仍持有原生表达式和调用者对象；需要可移植证据时，应序列化 ``UnsatReport``。

报告字段
--------

``explain_unsat`` 返回 ``UnsatReport``。可选字段在 Python 中使用 ``None``，在 JSON 中使用 ``null``。

.. list-table:: 完整报告字段组
   :header-rows: 1
   :widths: 30 70

   * - 字段
     - 含义与取值
   * - ``query_id``
     - 原始调用者标识，不是性质判定。
   * - ``solver_status``
     - ``sat``、``unsat``、``unknown`` 或 ``timeout``。
   * - ``proof_status``
     - ``captured``、``invalid``、``unavailable`` 或 ``not_requested``。捕获不等于独立认证。
   * - ``proof``
     - 选定的 ``ProofGraph`` 或 ``None``。无效证据也可能保留以供检查。
   * - ``proof_scope``
     - ``full``、``core`` 或 ``none``，说明选定图所证明的条件合取。
   * - ``full_proof``
     - 缩减图被接受后保存的原始图，否则为 ``None``。缩减失败时，原始图仍在 ``proof`` 中。
   * - ``input_check``
     - ``not_run``、``passed`` 或 ``failed``；检查断言叶子与精确输入的对应关系。
   * - ``scope_check``
     - ``not_run``、``passed``、``partial`` 或 ``failed``；检查局部假设和 False 根节点。
   * - ``rule_check``
     - ``not_run``、``complete``、``partial`` 或 ``failed``。受信任的机械步骤会使独立规则检查保持部分完成。
   * - ``gaps``
     - ``ProofGap(reason, node_id, detail)`` 元组；``node_id`` 可为 ``None``。原因包括 ``unsupported_rule``、``invalid_inference``、``open_hypotheses`` 和 ``non_false_root``。
   * - ``reading``
     - ``ProofReading``；组装未完成时可为 ``None``。
   * - ``reading_status``
     - ``complete``、``partial`` 或 ``not_requested``，不等同于 ``rule_check``。
   * - ``source_status``
     - ``absent``、``partial`` 或 ``complete``。完整表示被使用的命名输入组都有描述，不代表唯一必要的源码范围。
   * - ``core``
     - 请求核处理时为 ``CoreEvidence``，否则为 ``None``。
   * - ``stop_reason``
     - 可选的中断或不可用原因。原始求解为 UNSAT 时也应读取。

``CoreEvidence`` 包含 ``constraint_ids`` （全部原始可移除组）、 ``background_ids`` （固定组）、
``core_ids`` （经过验证的子集或 ``None`` ）、 ``core_check``
（ ``verified|not_checked|sat|unknown|timeout`` ）、 ``subset_minimality``
（ ``proven|not_proven`` ）、 ``reduction`` （ ``raw|partial_minimized|subset_minimal`` ）
及核处理的 ``stop_reason``。经过验证的 ``core_ids=()`` 表示背景自身矛盾。

例如，捕获后组装超时，可以产生 ``solver_status="unsat", proof_status="captured",
reading_status="not_requested"``。存在受信任的机械规则时，可以同时出现
``rule_check="partial", reading_status="complete"``。
缩减子集重新求证失败时，可以出现 ``core.subset_minimality="proven", proof_scope="full"``：
核证据与选定证明图各自保留独立的保证范围。

证据与阅读数据
--------------

.. list-table:: 数据记录
   :header-rows: 1
   :widths: 25 75

   * - 记录
     - 字段
   * - ``ProofGraph``
     - ``execution_id``、``root_id``、拓扑排序的 ``nodes`` 和 ``terms``、原始 ``inputs``、``source_bindings``。``node(id)`` 和 ``term(id)`` 查询精确记录。
   * - ``ProofTerm``
     - ``term_id``、 ``kind`` （literal/algebraic/constant/application/variable/quantifier）、 ``sort``、 ``operator``、子项 ``arguments``、 ``value``、绑定变量 ``bindings``、 ``operator_kind`` （builtin/uninterpreted）及带索引运算符的 ``parameters``。
   * - ``ProofInput``
     - ``occurrence_id``、``constraint_id``、从零开始的 ``expression_index``、``term_id`` 和布尔值 ``background``。未使用的提交表达式也会记录。
   * - ``ProofNode``
     - ``node_id``、原生 ``rule``、有序证明 ``parents``、可选 ``conclusion``、其他项 ``operands``、``parameters``、候选 ``input_occurrences``、``open_hypotheses``、``discharged_hypotheses``、``local_check``、``bindings``、``inference_kind`` 和可选 ``certificate``、``cardinality``、``interval`` 证据。
   * - ``ProofParameter``
     - ``kind`` 和文本 ``value``。类别为 integer、double、rational、symbol、sort、expression 或 declaration。
   * - ``ArithmeticCertificate``
     - ``bounds``、归一化的精确 ``weights``、相加后的 ``constant`` 和布尔值 ``strict``。每个 ``LinearBound`` 保留 ``term_id``、``negated``、项与系数对、``constant`` 及相对于零的 ``le|lt|eq`` 关系。
   * - ``CardinalityCertificate``
     - 临时 ``assumptions``、``constraint_id``、所需 ``constraint_value``、已知布尔 ``assignments`` 和加权 ``contributions``。``minimum`` 与 ``maximum`` 为精确整数总和。
   * - ``CountContribution``
     - 布尔 ``term_id``、带符号整数 ``weight`` 及精确的 ``minimum`` / ``maximum`` 贡献。
   * - ``IntervalCertificate``
     - 局部归一化 ``bounds``、有序 ``steps``，以及二选一的 ``conflict`` 或 ``equality``。结果对为从零开始的步骤索引。矛盾使用同一项的不相交范围；等式使用结论某个等式分支两侧相等的闭单点范围。
   * - ``TermEquality``
     - ``left_id``、``right_id`` 及 ``bound_indices``：建立项相等关系的一条局部等式，或方向相反的两条非严格边界。
   * - ``IntervalStep``
     - ``term_id``、精确有理数 ``lower`` / ``upper``（``None`` 表示无穷）、``lower_open`` / ``upper_open``、推导 ``rule``、先前步骤 ``premises``，以及线性推导可用的 ``bound_index``。``substitutions`` 保存局部等式。``congruence`` 从唯一的源范围传递边界；``congruence_sum`` 检查相等项的精确系数相消，记录所得常量单点。最终结果未使用的步骤会被移除。
   * - ``ReadingBlock``
     - ``block_id``、``kind``、结论 ``claims``、``premise_block_ids``、``active_hypotheses``、``evidence_node_ids``、``source_links``、合并的 ``detail_block_ids``、可选 ``title_en`` 和 ``title_zh``。
   * - ``ProofReading``
     - ``query_id``、``solver_status``、可选 ``root_id``、``status``、可见 ``blocks``、``sources``、``gaps`` 和隐藏的 ``detail_blocks``。绑定的图与报告共享，不在阅读对象内重复序列化。

``local_check`` 为 ``not_run|checked|trusted|unsupported|invalid``。
阅读类别为 ``input``、``assumption``、``discharge``、``arithmetic``、``cardinality``、``order``、``logical``、
``division_identity``、``remainder_lower``、``remainder_upper``、
``floor_lower``、``floor_upper``、``real_division``、``arithmetic_identity``、
``even_power``、``root_nonnegative``、``root_identity``、``interval``、
``equality``、``rewrite``、``definition``、``resolution``、``opaque`` 和 ``domain``。
原生绑定变量显示为 de Bruijn 索引：``#0`` 是最内层变量；名称和类型保留在 ``bindings`` 中。
求解器引入的符号不会被解码成虚构的源码变量。
``order`` 类别检查等式与大小关系分支是否覆盖同一归一化算术差值的全部符号。
检查可以将共享的非线性项视为原子，但不因此认证乘法本身的性质。
整除类别匹配 `SMT-LIB Ints <https://smt-lib.org/theories-Ints.shtml>`_ 中带条件的
欧几里得整除恒等式和余数边界。证明保留除数为零的分支，不在零除数上推导这些性质。
幂类别检查正偶数次整数幂，以及主平方根的符号和平方恒等式。
平方根推导要求被开方数非负；该条件由局部前提、子句分支或数值常量建立。
检查也覆盖从局部前提直接推出矛盾的形状，不借用无关的查询断言证明中间步骤。
区间推导使用精确有理数边界、开端点、整数取整、乘积、重复因子的平方和条件分支。
只有本节点的局部前提及结论分支的临时否定能建立范围。
文本展示这些假设、保留下来的每一步范围推导，以及最终矛盾或单点等式。
区间传播有轮数上限，找不到证书时仍明确保留 unsupported，
不会仅因整体查询为 UNSAT 就把局部推导标为已检查。

取整检查建立 ``to_int(x) <= x < to_int(x) + 1``；实数除法检查保留除数非零条件。
等价的 ``x*x`` 和 ``x^2`` 共享算术原子，消去仍要求精确系数匹配。
原生权重不可用时，可以从两条局部边界重建精确消元权重。
指数已由局部证据确定为正整数单点时，可以传播幂的范围。
所有有限端点始终使用精确有理数，包括极大和极小的值。

初始算术配置返回已知的算术或证明生成限制时，捕获使用 Z3 算术求解器 6 重试。
重试使用保存的原始断言，共享同一个总预算，只导出最终一次执行的证明。
超时以及仍无法解决的 UNKNOWN 会明确保留。

``reading.to_text(language="en", detail="standard")`` 接受 ``en`` 或 ``zh``，
返回带末尾换行的纯文本。阅读档位与核心最小化、规则检查相互独立：

* ``brief`` 为导读：展示输入、关键推导和矛盾。线性组合展示结果而不逐项列出系数，
  长公式使用引用；此档会明确标注它不是独立完整推导。
* ``standard`` 为默认档：将专用于后续步骤的机械前提折叠进该推导，
  保留算术证书、局部假设、假设关闭边界和未支持的步骤。
  共享长公式在文末附完整定义。
* ``detailed`` 展示完整阅读推导，并展开调用者定义的领域折叠。
  它不逐个打印所有原生求解器节点；捕获的证明图仍作为独立证据保留。

切换档位不会重新求解、修改报告、最小化核心或提升 ``rule_check`` 状态。
所有档位都保留明确的缺口。``[[t12]]`` 这样的公式引用对应报告图中的术语 ID；
``reading.get_term_text("t12")`` 可以离线取得未缩写的完整公式。
未知 ID 触发 ``KeyError``，没有证明图时触发 ``ValueError``。
序列化报告重新加载后，详细阅读和公式展开同样无需 Z3。

``get_block(id)`` 和 ``get_source(id)`` 查询记录。
``expand(id)`` 在存在合并详情时返回这些详情，否则返回直接前提块；未知 ID 会触发 ``KeyError``。
``to_canonical()`` 返回脱离调用者可变对象的 JSON 兼容数据。
报告层的 ``UnsatReport.from_canonical(data)`` 无需 Z3 即可重建和校验它。
不支持的字段、错误类型、重复标识、缺失引用、环及互相矛盾的报告状态会触发 ``ValueError``。

扩展与来源合同
--------------

``ProofExtensions(rule_handlers=(), source_adapter=None, reading_folders=())``
会固定两个集合。应用回调属于受信任代码，按同步方式调用；意外异常不会被吞掉。

* ``ProofRuleHandler(rule, interpret)`` 选择一个精确原生规则。
  ``interpret(node, graph)`` 返回 ``RuleAnalysis(kind, local_check="trusted")``。
  允许类别为 logical/equality/rewrite/definition/resolution/opaque，
  检查值为 checked/trusted/unsupported/invalid。
  输入和作用域规则 ``asserted``、``hypothesis``、``lemma`` 不允许覆盖。
* ``SourceAdapter.describe(handle)`` 返回 ``SourceDescription``，默认接受已有描述。
  ``bindings()`` 返回 ``SourceBinding`` 记录，默认为空。
* ``SourceBinding(expression, source, relation="construction")`` 绑定原始上下文中的精确表达式。
  关系为 construction/context，不能为 logical。
  未匹配表达式不会添加假设或项关联。
  ``ProofSource`` 在图中保存匹配的 ``term_id``、``description`` 和 ``relation``。
* ``SourceDescription(source_id, title, document_id=None, span=None, excerpt=None)``
  的标识和标题必须为非空字符串，可选文档和摘录也必须是字符串。
  源码范围由四个正整数坐标组成，右端不包含，并复制成元组。
  同一 ID 对应互相冲突的描述时会报错。
* ``SourceLink(source_id, relation, occurrence_id=None, term_id=None)``
  区分 logical/construction/context。
  出现位置关联指向实际输入；项关联记录构造或上下文附加信息。
* ``ReadingFolder(propose)`` 调用 ``propose(reading)``，得到可迭代的
  ``FoldProposal(root_id, block_ids, premise_block_ids, claims,
  active_hypotheses, title_en, title_zh)`` 记录，两个标题都必需。
  已移除或未知块、重复或不连通片段、修改结论、遗漏前提和隐藏仍在使用的假设都会被拒绝。

错误与运行边界
--------------

错误输入、条件组、上下文或选项类型会按生成的 API 文档触发 ``TypeError`` 或 ``ValueError``。
无效例子包括 ``minimize=1``、``timeout_ms=0``、``expressions`` 中的 Python 布尔值，
以及来自其他上下文的来源表达式。应分别改为布尔选项、正整数期限、Z3 布尔表达式及原始上下文中的绑定。

求解结果不是完整的独立证书；不支持的原生规则保持部分可解释状态。
线性算术检查不声称实现了通用非线性或量词证明重建。
来源映射报告调用者的元数据，不证明源语言语义正确。
文本和证明形状可能随 Z3 版本变化；机器应使用规范化记录，而不是解析人类文本。
这些辅助 API 不写文件，也不向服务发送数据。
离线加载只验证快照合同，不认证真实性。
不承诺最小基数核、最短证明、回调硬期限或跨执行节点身份。
