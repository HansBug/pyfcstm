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

复现与后续阅读
--------------

下载 :download:`proof.demo.py`，或在源码检出目录中将该目录加入 ``PYTHONPATH`` 后运行：

.. code-block:: console

    PYTHONPATH=. python docs/source/tutorials/unsat_proofs/proof.demo.py --case linear --language zh

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
