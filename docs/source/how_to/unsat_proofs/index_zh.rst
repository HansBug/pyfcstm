使用和扩展 UNSAT 解释
=====================

从 :doc:`/tutorials/unsat_proofs/index_zh` 中的 ``query`` 和 ``names`` 开始。
这些任务使用 Python API；BMC CLI 没有新增 solver 证明命令。完整可运行示例见
:download:`proof.demo.py </tutorials/unsat_proofs/proof.demo.py>`。

最小化条件并重新求证
--------------------

.. code-block:: python

    report = explain_unsat(query, names=names, minimize=True)
    print(report.core.core_ids)
    print(report.core.subset_minimality, report.proof_scope)

教程查询的输出为：

.. code-block:: text

    ('goal', 'initial', 'update')
    proven core

先缩核，再捕获选定子集的证明，结果图为 ``proof``。
API 不会消耗共享预算额外捕获原始图，``full_proof`` 为 ``None``。
需要同时查看原始查询的证明时，另行调用 ``explain_unsat(query, minimize=False)``。
节点 ID 属于各自的 ``execution_id``，不要跨报告拼接。
``proven`` 表示无法再单独删除任何保留的可移除条件组，不表示条件数量最少或证明最短。
若某次尝试返回 UNKNOWN，最小性可能仍为 ``not_proven``；请查看 ``stop_reason``。

固定必须保留的条件
------------------

将每次检查都必须存在的条件放入 ``background``：

.. code-block:: python

    fixed = UnsatQuery("fixed", (
        UnsatConstraint("goal", (after < 0,)),
    ), background=(UnsatConstraint("domain", (after >= 0,)),))
    result = explain_unsat(fixed, minimize=True)
    assert result.core.core_ids == ("goal",)

背景自身矛盾时，返回经过验证的空元组 ``()``。``None`` 表示没有验证出核。
两者都不表示 pyfcstm 隐式丢弃了背景。只需要经过检查的核证据时，使用
``mode="core"``；此时 ``proof_status`` 为 ``not_requested``。

在构造时关联来源位置
--------------------

可以直接用 ``SourceDescription`` 作为条件组的 ``source``。
如果来源是应用对象，则继承 ``SourceAdapter``。表达式绑定单独记录构造或上下文关系，
不会凭空添加逻辑前提：

.. code-block:: python

    from pyfcstm.solver import (
        ProofExtensions, SourceAdapter, SourceBinding, SourceDescription,
    )

    update = after == before + 1

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(update, SourceDescription(
                "increment", "Increment action", "virtual:policy",
                excerpt="balance@1 = balance@0 + 1",
            ), "construction"),)

    report = explain_unsat(query, names=names,
                           extensions=ProofExtensions(source_adapter=Sources()))
    assert report.reading.get_source("increment").document_id == "virtual:policy"

这里的文档 ID 特意表示虚拟来源，并不声称对应实际文件位置。
真实前端应提供实际文档 ID、从一开始计数且右端不包含的源码范围，以及可选摘录。
请绑定原始表达式及其实际 Z3 上下文；相同文本或另一个上下文中的表达式不能代替它。

可运行的 ``--case sources`` 示例为配置对象实现了 ``describe(handle)``。
其完整输出如下：

.. literalinclude:: /tutorials/unsat_proofs/proof.demo.py.txt
   :language: text
   :start-after: BEGIN sources zh
   :end-before: END sources zh

逻辑输入来源、构造关联和上下文关联含义不同。同一个公式提交两次时，会保留不同来源候选；
来源关联本身不能证明某一条语句是必要条件。条件组缺少描述时，``source_status``
可能为 ``partial``，而数学推导的阅读完整度仍可为完整。

给推导添加领域标题
------------------

合并器提议一个已有证明片段，而不是提供替代证明。下面只为最后一个块添加标题：

.. code-block:: python

    from pyfcstm.solver import FoldProposal, ReadingFolder

    def title_root(reading):
        root = reading.get_block(reading.root_id)
        yield FoldProposal(
            root.block_id, (root.block_id,), root.premise_block_ids,
            root.claims, root.active_hypotheses,
            "The balance conditions conflict", "余额条件互相矛盾",
        )

    report = explain_unsat(query, names=names, extensions=ProofExtensions(
        reading_folders=(ReadingFolder(title_root),),
    ))
    details = report.reading.expand(report.reading.root_id)
    assert details

阅读层会检查连通性、全部外部前提、精确结论、未关闭的假设，以及片段以外的引用。
遗漏前提或隐藏仍在使用的假设会触发 ``ValueError``。
标题属于受信任的应用文本，并不是独立验证过的自然语言定理。
``expand`` 返回原始阅读块；其 ``evidence_node_ids`` 指向原生证明图。
合并不能把部分可解释的阅读结果升级为完整。

解释另一种原生规则
------------------

登记一个精确规则名，并提供返回 ``RuleAnalysis`` 的解释函数：

.. code-block:: python

    from pyfcstm.solver import ProofRuleHandler, RuleAnalysis

    def interpret_instantiation(node, graph):
        return RuleAnalysis("logical", "trusted")

    extension = ProofExtensions(rule_handlers=(
        ProofRuleHandler("quant-inst", interpret_instantiation),
    ))

这个示例只是对已有实例化步骤分类，并不声称检查了它。
实际检查器只有在完成自身检查后才能返回 ``checked``。重复登记同一规则会报错。
``asserted``、``hypothesis`` 和 ``lemma`` 是保留规则：插件不能替换输入绑定或假设关闭逻辑。
插件异常会向调用者传播。登记某条规则，不等于支持其他全部量词规则，也不会消除它们的缺口。

保存并离线读取
--------------

.. code-block:: python

    import json
    from pyfcstm.solver import UnsatReport

    payload = json.dumps(report.to_canonical(), ensure_ascii=False)
    restored = UnsatReport.from_canonical(json.loads(payload))
    assert restored.to_canonical() == report.to_canonical()

``payload`` 是字符串；此示例不写文件。需要持久化时可使用普通文件 I/O。
读取保存的报告不导入 Z3 库，也不重新求解。加载器拒绝畸形字段、引用和环，
但不会认证快照作者或独立证明其声明。应使用生成该报告的发布版本所对应的数据合同；
载荷中不含用于模式分派的版本字段。

处理未完成的工作
----------------

.. code-block:: python

    report = explain_unsat(query, timeout_ms=1000, minimize=True)
    if report.reading is not None:
        print(report.reading.to_text())
    print(report.solver_status, report.proof_status, report.stop_reason)

同一个期限覆盖最小化、证明捕获和组装。证明捕获失败或超时时，已验证的核仍然保留；
缩核中断时不会宣称已证明最小性。组装超时后仍保留捕获的证明图和已完成的节点检查，
但可能 ``reading=None``。
SAT、UNKNOWN 和超时不会生成伪造的矛盾推导。
期限是协作式的：此 API 不能强制中断正在执行的扩展回调。

完整状态和异常类型见 :doc:`/reference/unsat_proofs/index_zh`。
未来 BMC 前端的职责见 :doc:`/explanations/unsat_proofs/index_zh`。
