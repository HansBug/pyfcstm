阅读第一份 UNSAT 证明
=====================

本教程从 Python 中的条件合取开始，得到自动组装的可读矛盾推导。
请使用包含 ``pyfcstm.solver.explain_unsat`` 的 pyfcstm 构建及其已有的
``z3-solver`` 依赖。无需安装 Lean、额外证明程序或调用 LLM 服务。

solver API 接受任意应用提供的公式。本教程不运行 BMC，也不改变性质判定的含义。

1. 为原始条件命名
-----------------

余额初始非负，随后增加一。我们询问下一时刻的余额能否为负，同时加入一条
无关条件，观察证明如何只使用提交条件的一部分。

.. code-block:: python

    import z3
    from pyfcstm.solver import (
        SymbolNames, UnsatConstraint, UnsatQuery, explain_unsat,
    )

    before, after, noise = z3.Ints("before after noise")
    query = UnsatQuery("linear", (
        UnsatConstraint("initial", (before >= 0,)),
        UnsatConstraint("update", (after == before + 1,)),
        UnsatConstraint("goal", (after < 0,)),
        UnsatConstraint("unrelated", (noise >= 0,)),
    ))

每个标识符命名一个可移除的条件组。组内表达式取合取；包含多个表达式的组，
在最小化时仍作为一个整体处理。这里的目标也是普通输入条件，并非特殊求解命令。

2. 生成证明
-----------

为实际符号登记显示名称，然后请求证明：

.. code-block:: python

    names = SymbolNames()
    names.register(before, "balance@0")
    names.register(after, "balance@1")
    report = explain_unsat(query, names=names)
    print(report.reading.to_text(language="zh"))

以下是仓库示例的完整真实输出，由 Z3 生成证据、pyfcstm 组装文本。
不同 Z3 版本的原生证明顺序可能不同。

.. literalinclude:: proof.demo.py.txt
   :language: text
   :start-after: BEGIN linear zh
   :end-before: END linear zh

最后一步将三个不等式相加。由于余额是整数，``balance@1 < 0`` 可以改写为
``balance@1 + 1 <= 0``。余额项消去后得到 ``2 <= 0``，从而否定提交的条件合取。
无关条件仍保存在输入表中，但这份原生反证没有使用它。

3. 检查结果的保证范围
---------------------

.. code-block:: python

    assert report.solver_status == "unsat"
    assert report.proof_status == "captured"
    assert report.input_check == "passed"
    assert report.scope_check == "passed"
    assert report.reading_status == "complete"
    root = report.reading.get_block(report.reading.root_id)
    premises = report.reading.expand(root.block_id)

``complete`` 描述可读推导的完整度，并不表示每条原生推理都经过了独立检查：
算术证书使用精确有理数检查，已识别的 Z3 机械推理仍可能标为 ``trusted``。
需要区分这些保证时，请查看 ``rule_check`` 和每个节点的 ``local_check``。
部分可解释的结果会显式保留 ``gaps``。

有些原生算术引理提供组合系数，有些没有展开中间代数步骤。解释器基于该引理的
前提和结论的否定重建局部证据，包括有理数线性组合、整数整除矛盾、区间推导，
以及使用平方非负和非负乘积的多项式恒等式。计算使用精确有理数，不调用第二个
求解器，也不借用无关输入条件。加载可移植报告时，可以不导入 Z3 而重放检查
多项式证据。

这种重建有搜索边界，并非完备的非线性算术判定过程。无法解释的引理仍然保留
明确的缺口。阅读完整也不保证证明全局最短：系统会删除多项式推导中未使用的
步骤和整除证据中的零系数等式，同时保留原生证明的依赖关系。生成文本时不会
展开无关输入公式；证据引用的等价表达式即使不在原生证明结论中，也会按需渲染。

显示名称会在整个捕获查询中检查。如果不同符号将显示为相同名称，捕获时会发出
``UserWarning``，并在显示名称后附加不同的项标识。原始公式和调用者的名称注册表
不会因此改变。

复现与后续阅读
--------------

下载 :download:`proof.demo.py`，或在源码检出目录中将该目录加入 ``PYTHONPATH`` 后运行：

.. code-block:: console

    PYTHONPATH=. python docs/source/tutorials/unsat_proofs/proof.demo.py --case linear --language zh

选择阅读档位
------------

默认档位是 ``standard``。同一份已捕获的证明可以直接展示为三个档位，无需重新求解：

.. code-block:: python

    for detail in ("brief", "standard", "detailed"):
        print(report.reading.to_text(language="zh", detail=detail))

``brief`` 是带公式引用的导读；``standard`` 保留算术证据并折叠机械性前提；
``detailed`` 还会展开已保存的领域折叠。
切换档位不会改变核心最小性、证明检查或已捕获的证据。
可以使用 ``get_term_text(term_id)`` 离线展开引用的完整公式。

演示脚本支持 ``--detail all``，一次展示每份证明的三个档位，也可指定单个档位。
以下快照还使用了真实 FCSTM/FBMCQ 构造器，捕获版本为 Z3 4.15.4。
来源投影使用 BMC provenance 的实验适配器，并不代表 BMC CLI 已切换为新合同。

* 订单流程：:download:`模型 <reading_examples/order_branch.fcstm>`、
  :download:`查询 <reading_examples/order_branch.fbmcq>`、
  :download:`简要档 <reading_examples/order_branch.brief.txt>`、
  :download:`标准档 <reading_examples/order_branch.standard.txt>`、
  :download:`详细档 <reading_examples/order_branch.detailed.txt>`。
* 九条条件共同造成的查询矛盾：
  :download:`模型 <reading_examples/query_conflict.fcstm>`、
  :download:`查询 <reading_examples/query_conflict.fbmcq>`、
  :download:`简要档 <reading_examples/query_conflict.brief.txt>`、
  :download:`标准档 <reading_examples/query_conflict.standard.txt>`、
  :download:`详细档 <reading_examples/query_conflict.detailed.txt>`。

同一个例子的三档输出共享同一份捕获的证明图。
两个例子都是阅读完整、独立规则检查为 partial；档位不会改变这一区别。

脚本还提供 ``--case branches``、``--case sources``、
``--case square``（整数 ``x*x == 2``）和 ``--case product``
（``x >= 2``、``y >= 3``、``x*y < 6``），以及 ``--case shared_square``
（实数上的 ``x*x == 2``、``y*y == 3``、``x == y``），以及
``--case equal_squares``（``x == y``、``x**2 != y*y``）。它打印真实证明，不写文件。
``--minimize`` 请求条件组的包含极小核并重新生成证明；``--fold`` 演示经过边界检查、
保留可展开证据的领域标题。这些是示例脚本的选项，不是新增的 ``pyfcstm bmc`` CLI 参数。

具体任务见 :doc:`/how_to/unsat_proofs/index_zh`，信任和来源边界见
:doc:`/explanations/unsat_proofs/index_zh`，完整 API 合同见
:doc:`/reference/unsat_proofs/index_zh`。
