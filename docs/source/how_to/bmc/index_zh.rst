BMC 任务指南
============

完成 :doc:`../../tutorials/bmc/index_zh` 后，用本页解决具体任务。每张任务卡都使用
本目录的独立夹具，并从仓库根目录运行。专用模型如下：

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``docs/source/how_to/bmc/bmc_tasks.fcstm``

它包含一个持久变量、一个事件、一个抽象 ``during`` 动作和一条事件转换，足以
覆盖公开 BMC CLI，同时不读取 ``test/`` 资源。

任务卡读法
----------

每张卡都明确输入、命令、预期输出、文件副作用、首个失败边界和参考入口。求解器
结论都是报告，包括预期的非零结论；受控输入错误则把短消息写到标准错误
（stderr），不创建半成品报告。

1. 在七类性质中作选择
----------------------

**输入。** ``bmc_tasks.fcstm``，以及分别名为 ``reach``、``forbid``、
``invariant``、``must_reach``、``exists_always``、``response``、``cover``
的七份查询夹具。

**命令。** 运行已核对的演示并保留前七行：

.. code-block:: bash

   bash docs/source/how_to/bmc/bmc_tasks.demo.sh | sed -n '1,7p'

**预期输出。**

.. code-block:: text

   reach sat witness_found exit=0
   forbid sat property_violated exit=1
   invariant unsat property_satisfied exit=0
   must_reach unsat property_satisfied exit=0
   exists_always sat witness_found exit=0
   response unsat property_satisfied exit=0
   cover sat witness_found exit=0

第一、第五和第七类采用见证极性；其余四类采用反例极性。因此 SAT 没有单一的
通用含义。

**文件副作用。** 演示在自身目录使用 ``.bmc_tasks.tmp``，退出时自动删除。

**失败边界。** ``cover`` 只接受裸写、已知且可覆盖的 ``case("...")`` 标签；
修改转换可能改变该标签。有界成功或失败都不能外推到所选边界以外。

**参考。** 精确性质形式见 :doc:`../../reference/bmc_query/index_zh`，目标公式含义见
:doc:`../../explanations/bmc_properties/index_zh`。

2. 指定状态并替换部分初始值
----------------------------

**输入。** ``init_havoc_where.fbmcq`` 从 ``Root.Idle`` 开始，只把 ``x`` 从
初始值约束中移除，并把第零帧约束为 ``x == 7``。

.. literalinclude:: init_havoc_where.fbmcq
   :language: text

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/init_havoc_where.fbmcq --json

**预期输出。** JSON 包含 ``"kind": "reach"``、
``"outcome": "witness_found"``，并且某个见证帧的 ``vars.x`` 为 ``7``；退出
状态是 ``0``。

**文件副作用。** 无；报告写到标准输出。

**失败边界。** ``where`` 只添加初始约束，不会覆盖初始值。不写
``havoc { x }`` 时，模型的 ``x = 0`` 与 ``where x == 7`` 会使轨迹公式 UNSAT。
``havoc *`` 会移除所有持久变量的初始值，应优先使用具名集合。

**参考。** ``cold``、``state(...)``、``terminated``、``havoc`` 与 ``where``
的合法形式见 :doc:`../../reference/bmc_query/index_zh`。

3. 约束帧和事件输入
--------------------

**输入。** ``assumptions.fbmcq`` 在每个帧约束 ``x``，在第零步禁用
``Root.Go``，并对事件集合要求至多一个事件。

.. literalinclude:: assumptions.fbmcq
   :language: text

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/assumptions.fbmcq --json \
       -o /tmp/bmc-assumptions.json

**预期输出。** 载荷报告 ``invariant``、``unsat``、``property_satisfied`` 和
退出 ``0``。由于在这些假设下不存在反例，``witness`` 与 ``replay``
均为 ``null``。

**文件副作用。** 原子创建或替换 ``/tmp/bmc-assumptions.json``。

**失败边界。** 假设会限制被搜索的环境，可能排除原本可行的行为。事件必须
使用全限定路径；未知路径是绑定错误，不是 UNSAT 结论。

**参考。** ``always``、``at``、事件选择器、范围与基数见
:doc:`../../reference/bmc_query/index_zh`。

4. 匹配抽象调用及其快照
------------------------

**输入。** ``calls.fbmcq`` 选择第零步的 ``Root.Idle.Tick`` 调用，要求其运行时
角色，检查调用时的 ``x`` 快照，并统计调用次数。

.. literalinclude:: calls.fbmcq
   :language: text

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/calls.fbmcq --json \
       -o /tmp/bmc-calls.json

**预期输出。** 以 ``0`` 退出，``outcome`` 为 ``witness_found``。第一个见证步
包含一条 ``abstract_calls`` 记录，其中 ``action_name`` 是
``Root.Idle.Tick``、``role`` 是 ``leaf_during``、``snapshot.x`` 是 ``0``。

**文件副作用。** 原子创建或替换 ``/tmp/bmc-calls.json``。

**失败边界。** 调用的 ``where`` 表达式读取调用瞬间捕获的变量；它不能使用
``active()`` 等帧原子，也不能嵌套 ``call_count()``。CLI 重放会记录抽象调用，
但不会安装可能修改运行时状态的用户处理器。

**参考。** 完整调用过滤键和 ``where`` 表达式边界见
:doc:`../../reference/bmc_query/index_zh`。

5. 审计人类可读见证与重放
--------------------------

**输入。** 专用模型与 ``calls.fbmcq``。

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/calls.fbmcq

**预期输出。** 第一行是 ``BMC reach <= 3: PROPERTY HOLDS``。随后
``Solver: SAT`` 给出求解诊断，``Replay: verified`` 给出运行时可信门禁结果，紧凑的
``Trace`` 列出源状态、目标状态、选中分支、事件和调用。进程以 ``0`` 退出。使用
``--color always`` 可强制终端着色，使用 ``--color never`` 可得到稳定纯文本。

**文件副作用。** 无；人类可读摘要写到标准输出。完整见证与重放记录使用 ``--json``。

**失败边界。** SAT 解码或重放抛异常属于内部失败：保留 traceback 并以 ``1``
退出，不输出半成品。若重放成功构造了不匹配项，则输出完整报告并以 ``4`` 退出。
重放检查运行时对齐，不是无界证明。

**参考。** 报告分节、见证列、重放不匹配和退出优先级见
:doc:`../../reference/bmc_results/index_zh`。

6. 用 JSON 和退出状态建立持续集成门禁
---------------------------------------

**输入。** ``forbid.fbmcq`` 会有意找到禁止状态反例，用于展示“合法报告但退出非零”。

**命令。**

.. code-block:: bash

   set +e
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/forbid.fbmcq --json \
       -o /tmp/bmc-ci.json
   rc=$?
   set -e
   BMC_RC="$rc" BMC_JSON=/tmp/bmc-ci.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(Path(os.environ["BMC_JSON"]).read_text(encoding="utf-8"))
   assert payload["exit_code"] == int(os.environ["BMC_RC"])
   print(payload["result"]["outcome"], payload["exit_code"])
   PY

**预期输出。** ``property_violated 1``。持续集成可按项目策略阻塞或容许该结论，
但不能把它误当成 CLI 输入错误。

**文件副作用。** 即使结论退出 ``1``，也会创建 ``/tmp/bmc-ci.json``。

**失败边界。** 退出 ``0`` 表示性质满足或找到正向见证；``1`` 也覆盖受控错误，
但受控错误只有 stderr、没有报告；``2`` 是 Click 用法错误；``3`` 是无定论；
``4`` 是结构化重放不匹配。存在报告时必须读取 JSON。

**参考。** 完整分支矩阵与稳定 JSON 模式见
:doc:`../../reference/bmc_results/index_zh`。

7. 原子写入完整报告
--------------------

**输入。** 任一合法的单查询；这里使用 ``invariant.fbmcq``，目标父目录已存在。

**命令。**

.. code-block:: bash

   mkdir -p /tmp/pyfcstm-bmc
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/invariant.fbmcq \
       --json -o /tmp/pyfcstm-bmc/result.json
   test -s /tmp/pyfcstm-bmc/result.json

**预期输出。** 标准输出为空；``test`` 以 ``0`` 退出，文件含
``"exit_code": 0``。

**文件副作用。** 使用同目录临时文件原子替换目标。

**失败边界。** ``pyfcstm bmc`` 不创建父目录。若读取、编译、内部求解或写入在
完整载荷形成前失败，命令不得把输出文件声明为成功。

**参考。** 覆盖写、stdout、stderr 和 UTF-8 规则见
:doc:`../../reference/bmc_results/index_zh`。

8. 强制最大边界策略
--------------------

**输入。** ``reach_bound_2.fbmcq`` 请求边界 2，而命令策略最多允许 1。

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/reach_bound_2.fbmcq \
       --max-bound 1

**预期输出。** stderr 给出简洁的 ``Failed to compile BMC query``，包含
``query_bound=2`` 和 ``max_bound=1``；退出 ``1``。

**文件副作用。** 无。即使指定 ``-o``，策略拒绝发生在报告构造前，也不会创建或
修改报告。

**失败边界。** ``--max-bound`` 是构造前策略门禁，不会静默截断查询。小于 1 的
值属于 Click 用法错误，退出 ``2``。

**参考。** CLI 选项与错误分类见 :doc:`../../reference/bmc_results/index_zh`。

9. 设置单次求解器检查超时
--------------------------

**输入。** 任一合法查询。小夹具可能在一毫秒以内完成；本任务验证参数传递，
不强求与机器性能相关的超时。

**命令。**

.. code-block:: bash

   set +e
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o /tmp/bmc-timeout.json
   rc=$?
   set -e
   BMC_JSON=/tmp/bmc-timeout.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(Path(os.environ["BMC_JSON"]).read_text(encoding="utf-8"))
   print("timeout_ms:", payload["result"]["timeout_ms"])
   print("outcome:", payload["result"]["outcome"])
   PY

**预期输出。** 先打印 ``timeout_ms: 1``，再打印决定性结果或
``outcome: timeout``。真实超时退出 ``3``；快速完成时保留普通退出状态。

**文件副作用。** ``/tmp/bmc-timeout.json`` 保存完整结论。

**失败边界。** 该值分别作用于每次 Z3 ``check()``，不是解析、展开、公式构造或
整个 CLI 的墙钟预算。``response`` 可能再执行一次边界不完整检查，后者也
得到完整超时预算。

**参考。** 超时字段见 :doc:`../../reference/bmc_results/index_zh`，求解顺序见
:doc:`../../explanations/bmc_solving/index_zh`。

10. 区分 ``response`` 违反与边界不完整
----------------------------------------

**输入。** ``response_missing.fbmcq`` 的触发器有定义但没有响应；
``response_trigger_undefined.fbmcq`` 在 ``x == 0`` 的触发器中执行除法；
``response_incomplete.fbmcq`` 的边界是 1，却要求在两个后继帧以内响应。

.. literalinclude:: response_incomplete.fbmcq
   :language: text

**命令。**

.. code-block:: bash

   set +e
   for name in response_missing response_trigger_undefined; do
       python -m pyfcstm bmc \
           -i docs/source/how_to/bmc/bmc_tasks.fcstm \
           -q "docs/source/how_to/bmc/$name.fbmcq" --json \
           -o "/tmp/$name.json"
       echo "$name exit=$?"
   done
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/response_incomplete.fbmcq --json \
       -o /tmp/bmc-incomplete.json
   echo "response_incomplete exit=$?"
   set -e

**预期输出。** 前两行以 ``exit=1`` 结尾，两份 JSON 的 ``status`` 都是 ``sat``、
``outcome`` 都是 ``property_violated``。最后一行是
``response_incomplete exit=3``；其 JSON 主 ``status`` 是 ``unsat``，但
``outcome`` 是 ``incomplete``、``incomplete`` 为 true、
``incomplete_status`` 为 ``sat``，见证与重放均为 ``null``。

**文件副作用。** 在 ``/tmp`` 下创建三份完整 JSON 报告。

**失败边界。** 当前结果与见证模式不能区分决定性 ``response`` 反例来自
未定义触发器，还是来自已定义触发器但没有响应；必须结合查询和轨迹人工判断。
后缀闭合前不能把主 UNSAT 解读为满足。增加查询边界才能覆盖观察范围；超时
不能修复过短的边界。

**参考。** 严格后继窗口见 :doc:`../../explanations/bmc_properties/index_zh`，
不完整字段见 :doc:`../../reference/bmc_results/index_zh`。

11. 诊断解析、绑定和不支持的输入
---------------------------------

**输入。** ``invalid_state.fbmcq`` 语法正确，但引用不存在的
``Root.Missing``。

**命令。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/invalid_state.fbmcq

**预期输出。** stderr 以 ``Failed to compile BMC query`` 开头并指出
``Root.Missing``；退出 ``1``，stdout 为空。

**文件副作用。** 无。增加 ``-o /tmp/invalid.json`` 后仍不能创建半成品载荷。

**失败边界。** 畸形 ``.fbmcq`` 在解析阶段失败，未知模型路径在绑定阶段失败，
已解析但不支持的表达式报告不支持的查询；这些都是受控用户输入错误。带内部
BMC 哨兵文本的回溯是实现失败，应作为缺陷报告，不能改写到看似 UNSAT。

**参考。** 合法与非法形式见 :doc:`../../reference/bmc_query/index_zh`，错误流见
:doc:`../../reference/bmc_results/index_zh`。

12. 升级后重跑主要夹具矩阵
--------------------------------

**输入。** 本目录的模型、查询夹具和 ``bmc_tasks.demo.sh``；脚本自身维护
预期退出矩阵。

**命令。**

.. code-block:: bash

   bash docs/source/how_to/bmc/bmc_tasks.demo.sh

**预期输出。** 十一行结论摘要以 ``response unsat incomplete exit=3`` 结束，
随后是 ``invalid_state controlled_error exit=1``。只有每条嵌套命令都符合冻结预期，
脚本自身才以 ``0`` 退出。

**文件副作用。** 临时 JSON 写到
``docs/source/how_to/bmc/.bmc_tasks.tmp``，由退出陷阱删除。

**失败边界。** 永远不比较实时 ``elapsed_ms``。脚本失败时，先用人类可读模式直接
运行对应查询，再检查性质极性、结果、重放状态与进程退出，然后才考虑修改预期。

**参考。** 稳定字段与非确定字段见 :doc:`../../reference/bmc_results/index_zh`。
该脚本是文档冒烟检查，不能替代仓库 BMC 单元测试。
