UNSAT 证明 API 参考
===================

本参考覆盖 :mod:`pyfcstm.solver.proof`、:mod:`pyfcstm.solver.proof_rules`、
:mod:`pyfcstm.solver.proof_text`、:mod:`pyfcstm.solver.unsat` 和
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
     - ``node_id``、原生 ``rule``、有序证明 ``parents``、可选 ``conclusion``、其他项 ``operands``、``parameters``、候选 ``input_occurrences``、``open_hypotheses``、``discharged_hypotheses``、``local_check``、``bindings``、``inference_kind`` 和可选 ``certificate``。
   * - ``ProofParameter``
     - ``kind`` 和文本 ``value``。类别为 integer、double、rational、symbol、sort、expression 或 declaration。
   * - ``ArithmeticCertificate``
     - ``bounds``、归一化的精确 ``weights``、相加后的 ``constant`` 和布尔值 ``strict``。每个 ``LinearBound`` 保留 ``term_id``、``negated``、项与系数对、``constant`` 及相对于零的 ``le|lt|eq`` 关系。
   * - ``ReadingBlock``
     - ``block_id``、``kind``、结论 ``claims``、``premise_block_ids``、``active_hypotheses``、``evidence_node_ids``、``source_links``、合并的 ``detail_block_ids``、可选 ``title_en`` 和 ``title_zh``。
   * - ``ProofReading``
     - ``query_id``、``solver_status``、可选 ``root_id``、``status``、可见 ``blocks``、``sources``、``gaps`` 和隐藏的 ``detail_blocks``。绑定的图与报告共享，不在阅读对象内重复序列化。

``local_check`` 为 ``not_run|checked|trusted|unsupported|invalid``。
阅读类别为 ``input``、``assumption``、``discharge``、``arithmetic``、``logical``、
``equality``、``rewrite``、``definition``、``resolution``、``opaque`` 和 ``domain``。
原生绑定变量显示为 de Bruijn 索引：``#0`` 是最内层变量；名称和类型保留在 ``bindings`` 中。
求解器引入的符号不会被解码成虚构的源码变量。

``reading.to_text(language="en")`` 接受 ``en`` 或 ``zh``，返回带末尾换行的完整纯文本。
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
