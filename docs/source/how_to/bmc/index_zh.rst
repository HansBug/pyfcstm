BMC 任务指南
============

完成 :doc:`../../tutorials/bmc/index_zh` 后，用本页解决具体任务。先进入一个空的
工作目录，把 :download:`任务模型 <bmc_tasks.fcstm>` 下载到这里。将每项任务展示的
查询文件按标题所写的文件名保存，再从同一目录运行命令。专用模型很小：

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``bmc_tasks.fcstm``

它包含一个持久变量、一个事件、一个抽象 ``during`` 动作和一条事件转换。下面
每项任务先给命令及其真实的终端记录，再给命令所读的完整短 ``.fbmcq`` 文件，
然后说明作用、预期输出和失败边界。终端记录里单独一行 ``...`` 表示任务不讨论的
报告行，例如求解耗时。若一项任务用于对照多个方案，会把每个方案作为单独的文件展示。

如何选择性质类别
----------------

可满足（SAT）对见证极性（witness polarity）和反例极性（counterexample
polarity）的含义不同。先按用户问题选择查询类别，再按该类别的极性读取求解状态。

.. list-table:: BMC 性质选择表
   :header-rows: 1
   :widths: 16 30 22 22 28

   * - 类别
     - 用户意图
     - 量化（quantification）
     - SAT 含义
     - 何时使用
   * - ``reach``
     - 找到一条有界执行，使某个谓词为真。
     - 对轨迹和帧作存在量化。
     - 找到见证；搜索目标成立。
     - 需要到达某状态、变量值、调用或事件条件的具体路径。
   * - ``forbid``
     - 拒绝任何到达坏谓词的有界执行。
     - 以反例搜索编码的全称安全检查。
     - 找到反例；性质被违反。
     - 已知不安全条件，并希望它可达时让持续集成失败。
   * - ``invariant``
     - 要求每个被搜索帧都满足谓词。
     - 对每条有界轨迹的所有帧作全称量化。
     - 找到反例帧；性质被违反。
     - 需要有界安全条件，例如始终满足 ``x >= 0``。
   * - ``must_reach``
     - 要求每条有界执行都到达谓词。
     - 对轨迹作全称量化，并对每条轨迹中的帧作存在量化。
     - 找到一条从未到达该谓词的轨迹；性质被违反。
     - 需要保证有界进展，而不是只找一个成功例子。
   * - ``exists_always``
     - 找到一条执行，使谓词在整个边界内保持为真。
     - 对轨迹作存在量化，并对该轨迹的所有帧作全称量化。
     - 找到见证轨迹；搜索目标成立。
     - 想证明某个稳定场景可能存在，而不是强制所有执行都满足。
   * - ``response``
     - 检查每个触发都在窗口内跟随响应。
     - 对触发步和有界后继帧窗口作全称量化。
     - 找到违反的触发；性质被违反。
     - 需要请求/确认、命令/效果或报警/清除行为。
   * - ``cover``
     - 命中一个具名转换分支标签。
     - 对轨迹和分支标签作存在量化。
     - 找到命中该标签的见证。
     - 需要覆盖某个具体生成转换分支。

如何处理无定论结果
------------------

当 CLI 退出 ``3``，或 JSON 报告的结果不是 ``property_satisfied`` 也不是
``property_violated`` 时，先按下表处理。

.. list-table:: 超时、未知与不完整处理表
   :header-rows: 1
   :widths: 18 24 30 30

   * - 结果
     - 出现位置
     - 含义
     - 首个处理动作
   * - ``timeout``
     - ``result.status`` 和 ``result.outcome`` 都可能是 ``timeout``。
     - Z3 未能在 ``--timeout-ms`` 内完成单次 ``check()``。
     - 增大 ``--timeout-ms``、简化假设或降低边界；不要当成安全结论。
   * - ``unknown``
     - 后端无法决定时，``result.status`` 可能是 ``unknown``。
     - 求解器给出非 SAT、非 UNSAT 的不确定答案。
     - 检查诊断、简化查询或降低边界；不要当成证明。
   * - ``incomplete``
     - ``result.outcome`` 是 ``incomplete``，且 ``result.incomplete`` 为真。
     - 主目标为 UNSAT，但独立响应边界检查为 SAT、``unknown``、``timeout``
       或未执行。
     - 查看 ``result.incomplete_status``。SAT 时增大边界；``unknown`` 或
       ``timeout`` 时排查求解器或超时设置。
   * - ``runtime_safety_unknown`` / ``runtime_safety_timeout``
     - ``result.runtime_safety.status`` 为 ``unknown`` 或 ``timeout``。
     - 在性质之前运行的检查无法判定是否可达运行时错误，因此性质未评估。
     - 增大 ``--timeout-ms`` 或减小边界；``sqrt`` 等非线性运算会让检查更难。可达错误
       见任务 17。

任务卡读法
----------

每张任务卡都包含直接 CLI 命令、相关查询片段、简短说明、预期输出、副作用、
失败边界，以及指向完整语法或结果事实的参考页。求解器结论都是报告，包括预期的
非零结论。受控输入错误会向标准错误写短消息，且不创建半成品报告。

1. 运行所选性质类别
--------------------

**FBMCQ。** 下面是七个独立查询文件，不是同一个文件中的七条 ``check``。
每个文件先写 ``init state("Root.Idle");``，再且仅再写一条 ``check``。
共同的热启动（hot start）行让第 0 帧成为 ``Root.Idle``；下面边界为 1 的 ``forbid`` 和
``cover`` 结果依赖这个前提。

.. literalinclude:: reach.fbmcq
   :language: text
   :caption: reach.fbmcq

.. literalinclude:: forbid.fbmcq
   :language: text
   :caption: forbid.fbmcq

.. literalinclude:: invariant.fbmcq
   :language: text
   :caption: invariant.fbmcq

.. literalinclude:: must_reach.fbmcq
   :language: text
   :caption: must_reach.fbmcq

.. literalinclude:: exists_always.fbmcq
   :language: text
   :caption: exists_always.fbmcq

.. literalinclude:: response.fbmcq
   :language: text
   :caption: response.fbmcq

.. literalinclude:: cover.fbmcq
   :language: text
   :caption: cover.fbmcq

**CLI。** 将 ``reach.fbmcq`` 替换为你选择的性质查询文件。直接运行 ``reach`` 并加
``--json``：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --json
   {
     "exit_code": 0,
   ...
       "kind": "reach",
   ...
       "outcome": "witness_found",
   ...
       "status": "sat",
   ...

**作用。** 命令向模型提出一个有界问题。查询类别决定 SAT 表示正向见证还是反例。

**预期输出。** 直接 ``reach`` 命令的 JSON 包含 ``"kind": "reach"``、
``"status": "sat"``、``"outcome": "witness_found"`` 和
``"exit_code": 0``，如上面的记录所示。用人类可读模式运行这七个文件，每份报告的第一行就是结论；只有 ``forbid`` 以 ``1`` 退出，
因为它的反例表示性质被违反：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q forbid.fbmcq
   BMC forbid <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq
   BMC invariant <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q must_reach.fbmcq
   BMC must_reach <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q exists_always.fbmcq
   BMC exists_always <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response.fbmcq
   BMC response <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q cover.fbmcq
   BMC cover <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...

**文件副作用。** 除非增加 ``-o``，否则没有文件副作用。

**失败边界。** ``cover`` 只接受裸写、已知且可覆盖的 ``case("...")`` 标签。
有界结果不能说明所选边界之外的行为。

**参考。** 精确性质形式见 :doc:`../../reference/bmc_query/index_zh`，目标公式含义见
:doc:`../../explanations/bmc_properties/index_zh`。

2. 指定状态并替换部分初始值
----------------------------

**CLI。** 见证的第零帧带着状态和查询要求的取值：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q init_havoc_where.fbmcq --json
   {
     "exit_code": 0,
   ...
       "outcome": "witness_found",
   ...
     "witness": {
       "diagnostics": [],
       "frames": [
         {
           "index": 0,
           "sentinel": null,
           "state": "Root.Idle",
           "state_id": 2,
           "terminated": false,
           "vars": {
             "x": 7
           }
         },
   ...

**FBMCQ。**

.. literalinclude:: init_havoc_where.fbmcq
   :language: text
   :caption: init_havoc_where.fbmcq

**作用。** 查询从 ``Root.Idle`` 开始，只把 ``x`` 从初始值约束中移除，并把
第零帧约束为 ``x == 7``。

**预期输出。** JSON 包含 ``"kind": "reach"``、
``"outcome": "witness_found"``，并且某个见证帧的 ``vars.x`` 为 ``7``；
退出状态是 ``0``。

**文件副作用。** 无；报告写到标准输出。

**失败边界。** ``where`` 只添加初始约束，不会覆盖初始值。不写
``havoc { x }`` 时，模型的 ``x = 0`` 与 ``where x == 7`` 会使轨迹公式 UNSAT：

.. literalinclude:: init_where_only.fbmcq
   :language: text
   :caption: init_where_only.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q init_where_only.fbmcq
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
     Failure boundary: INITIALIZATION
   ...
   $ echo $?
   3

``havoc *`` 会移除所有持久变量的初始值，应优先使用具名集合。

**参考。** ``cold``、``state(...)``、``terminated``、``havoc`` 与 ``where``
的合法形式见 :doc:`../../reference/bmc_query/index_zh`。

3. 约束帧和事件输入
--------------------

**CLI。** 命令把报告写入文件，不向标准输出打印任何内容；文件显示结论，以及
``witness`` 与 ``replay`` 均为 ``null``：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q assumptions.fbmcq --json -o assumptions.json
   $ cat assumptions.json
   {
     "exit_code": 0,
   ...
     "replay": null,
   ...
       "kind": "invariant",
   ...
       "outcome": "property_satisfied",
   ...
       "status": "unsat",
   ...
     "witness": null
   }

**FBMCQ。**

.. literalinclude:: assumptions.fbmcq
   :language: text
   :caption: assumptions.fbmcq

**作用。** 假设在每个帧约束 ``x``，在第零步禁用 ``Root.Go``，并要求所选事件
集合中至多有一个事件。

**预期输出。** 载荷报告 ``invariant``、``unsat``、``property_satisfied`` 和
退出 ``0``。由于在这些假设下不存在反例，``witness`` 与 ``replay`` 均为
``null``。

**文件副作用。** 在当前目录原子创建或替换 ``assumptions.json``。

**失败边界。** 假设会限制被搜索的环境，可能排除原本可行的行为。事件必须使用
全限定路径；未知路径是绑定错误，不是 UNSAT 结论。

**参考。** ``always``、``at``、事件选择器、范围与基数见
:doc:`../../reference/bmc_query/index_zh`。

4. 匹配抽象调用及其快照
------------------------

**CLI。**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q calls.fbmcq --json
   {
     "exit_code": 0,
   ...
       "outcome": "witness_found",
   ...
     "witness": {
   ...
       "steps": [
         {
           "abstract_calls": [
             {
               "action_name": "Root.Idle.Tick",
               "active_leaf": "Root.Idle",
               "named_ref": null,
               "ordinal": 0,
               "role": "leaf_during",
               "snapshot": {
                 "x": 0
               },
   ...

**FBMCQ。**

.. literalinclude:: calls.fbmcq
   :language: text
   :caption: calls.fbmcq

**作用。** 查询选择第零步的 ``Root.Idle.Tick`` 调用，要求其运行时角色，检查
调用时的 ``x`` 快照，并统计一步边界内的调用次数。

**预期输出。** 以 ``0`` 退出，``outcome`` 为 ``witness_found``。第一个见证步
包含一条 ``abstract_calls`` 记录，其中 ``action_name`` 是
``Root.Idle.Tick``、``role`` 是 ``leaf_during``、``snapshot.x`` 是 ``0``。

**文件副作用。** 无；增加 ``-o`` 会把载荷原子写入文件。

**失败边界。** 调用的 ``where`` 表达式读取调用瞬间捕获的变量；它不能使用
``active()`` 等帧原子，也不能嵌套 ``call_count()``。CLI 重放会记录抽象调用，
但不会安装可能修改运行时状态的用户处理器。

**参考。** 完整调用过滤键和 ``where`` 表达式边界见
:doc:`../../reference/bmc_query/index_zh`。

5. 审计人类可读见证与重放
--------------------------

**CLI。** 每次运行都会变化的行（求解耗时）和本任务不讨论的行用 ``...`` 省略：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q calls.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
     Replay: verified (2 frames, 1 step).
   ...
   Solver: SAT in ... ms
   ...
   Trace
     0: Root.Idle -> Root.Idle [fallback; calls=Root.Idle.Tick]
   ...

**FBMCQ。** 与任务 4 相同的 ``calls.fbmcq``：

.. literalinclude:: calls.fbmcq
   :language: text
   :caption: calls.fbmcq

**作用。** 人类可读模式以紧凑形式打印同一见证，并在报告成功前运行强制重放可信
门禁。

**预期输出。** 第一行是 ``BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``。随后
``Solver: SAT`` 给出求解诊断，``Replay: verified`` 给出运行时可信门禁结果，紧凑
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

**CLI。** 命令以 ``1`` 退出，但仍写出报告：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q forbid.fbmcq --json -o ci.json
   $ echo $?
   1
   $ cat ci.json
   {
     "exit_code": 1,
   ...
       "outcome": "property_violated",
   ...
       "status": "sat",
   ...

**FBMCQ。** 与任务 1 相同的 ``forbid.fbmcq``：

.. literalinclude:: forbid.fbmcq
   :language: text
   :caption: forbid.fbmcq

**作用。** 这条合法查询会有意找到禁止状态反例，展示“存在机器可读报告但进程
退出非零”的情况。

**预期输出。** 命令退出 ``1``，但仍创建 JSON；其中包含 ``"status": "sat"``、
``"outcome": "property_violated"`` 和 ``"exit_code": 1``。持续集成可按项目
策略阻塞或容许该结论，但不能把它误当成 CLI 输入错误。

**文件副作用。** 即使结论退出 ``1``，也会创建 ``ci.json``。

**失败边界。** 退出 ``0`` 表示性质满足或找到正向见证；``1`` 也覆盖受控错误，
但受控错误只有 stderr、没有报告；``2`` 是 Click 用法错误；``3`` 是无定论；
``4`` 是结构化重放不匹配。存在报告时必须读取 JSON。

**参考。** 完整分支矩阵与稳定 JSON 模式见
:doc:`../../reference/bmc_results/index_zh`。

7. 原子写入完整报告
--------------------

**CLI。** 父目录必须已经存在；缺失的父目录会被拒绝：

.. code-block:: console

   $ mkdir reports
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq --json -o reports/result.json
   $ cat reports/result.json
   {
     "exit_code": 0,
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq --json -o missing/result.json
   Failed to write BMC output file missing/result.json: [Errno 2] No such file or directory: '...missing/.result.json...tmp'
   $ echo $?
   1

**FBMCQ。** 与任务 1 相同的 ``invariant.fbmcq``：

.. literalinclude:: invariant.fbmcq
   :language: text
   :caption: invariant.fbmcq

**作用。** CLI 先通过同目录临时文件写出完整 JSON 载荷，再替换目标路径。上面的
错误消息点出了这个临时文件。

**预期输出。** 标准输出为空；文件包含 ``"exit_code": 0``。

**文件副作用。** 原子创建或替换目标文件。父目录必须已经存在。

**失败边界。** ``pyfcstm bmc`` 不创建父目录。若读取、编译、内部求解或写入在
完整载荷形成前失败，命令不得把输出文件声明为成功。

**参考。** 覆盖写、stdout、stderr 和 UTF-8 规则见
:doc:`../../reference/bmc_results/index_zh`。

8. 强制最大边界策略
--------------------

**CLI。**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach_bound_2.fbmcq --max-bound 1
   Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1.
   $ echo $?
   1

**FBMCQ。**

.. literalinclude:: reach_bound_2.fbmcq
   :language: text
   :caption: reach_bound_2.fbmcq

**作用。** 查询请求边界 2，而命令行策略最多允许 1。

**预期输出。** stderr 包含 ``Failed to compile BMC query``、``query_bound=2``
和 ``max_bound=1``；命令退出 ``1``，如上面的块所示。

**文件副作用。** 无。即使指定 ``-o``，策略拒绝发生在报告构造前，也不会创建或
修改报告。

**失败边界。** ``--max-bound`` 是构造前策略门禁，不会静默截断查询。小于 1 的
值属于 Click 用法错误，退出 ``2``。

**参考。** CLI 选项与错误分类见 :doc:`../../reference/bmc_results/index_zh`。

9. 设置单次求解器检查超时
--------------------------

**CLI。** 这条命令不在文档检查里运行，因为一毫秒是否足够取决于机器的速度：

.. code-block:: bash

   pyfcstm bmc -i bmc_tasks.fcstm -q reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o bmc-timeout.json

**FBMCQ。** 与任务 8 相同的 ``reach_bound_2.fbmcq``：

.. literalinclude:: reach_bound_2.fbmcq
   :language: text
   :caption: reach_bound_2.fbmcq

**作用。** 命令把一毫秒超时传给每次求解器 ``check()``。这个夹具是否超时取决于
机器：负载高或较慢的机器可能超过限制，而较快的机器会先得到决定性结果。

**预期输出。** 若超过限制，命令退出 ``3``，JSON 包含
``"timeout_ms": 1``、``"status": "timeout"`` 和
``"outcome": "timeout"``。如果求解先完成，JSON 仍记录
``"timeout_ms": 1``，并使用普通决定性退出状态；撰写本页时，在开发机器上重复运行
都是求解先完成，以 ``0`` 退出，并报告 ``"outcome": "witness_found"``。

**文件副作用。** ``bmc-timeout.json`` 保存完整结论。

**失败边界。** 该超时不是解析、展开、公式构造或整个 CLI 的墙钟预算。
``response`` 可能再执行一次边界不完整检查，后者也得到完整超时预算。

**参考。** 超时字段见 :doc:`../../reference/bmc_results/index_zh`，求解顺序见
:doc:`../../explanations/bmc_solving/index_zh`。

10. 区分 ``response`` 违反与边界不完整
----------------------------------------

**CLI。** 先运行缺失响应场景，再运行短边界场景。人类可读报告的第一行和退出码都能把两者区分开：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_missing.fbmcq
   BMC response <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_incomplete.fbmcq
   BMC response <= 1: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE
   ...
   $ echo $?
   3

两次运行的 JSON 用字段说出同样的事：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_missing.fbmcq --json
   {
     "exit_code": 1,
   ...
       "outcome": "property_violated",
   ...
       "status": "sat",
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_incomplete.fbmcq --json
   {
     "exit_code": 3,
   ...
     "replay": {
       "mismatches": [],
       "model_role": "incomplete_suffix",
       "ok": true,
   ...
       "incomplete": true,
   ...
       "incomplete_status": "sat",
   ...
       "outcome": "incomplete",
   ...
       "status": "unsat",
   ...
     "witness": {
   ...
       "model_role": "incomplete_suffix",
   ...
   $ echo $?
   3

给任一命令加上 ``-o bmc-response.json``，就会把结果写入文件而不是标准输出。

**FBMCQ 文件：** ``response_missing.fbmcq``

.. literalinclude:: response_missing.fbmcq
   :language: text

**FBMCQ 文件：** ``response_incomplete.fbmcq``

.. literalinclude:: response_incomplete.fbmcq
   :language: text

**作用。** 第一条查询是决定性违反：触发存在，且没有响应能满足一步窗口。第二种
形状在边界 1 下无定论，因为两个后继帧的响应窗口越过已检查后缀。

**预期输出。** ``response_missing.fbmcq`` 退出 ``1``，``status`` 为 ``sat``，
``outcome`` 为 ``property_violated``\ （JSON 中）。``response_incomplete.fbmcq`` 退出
``3``，主 ``status`` 为 ``unsat``，``outcome`` 为 ``incomplete``，
``incomplete`` 为 true，``incomplete_status`` 为 ``sat``。它的 ``witness`` 不是
``null``：那是仍可能违反性质的不完整后缀（``model_role`` 为
``incomplete_suffix``），``replay`` 以 ``ok`` 为 true 确认了它。请把这份见证看作
结论无定论的原因，而不是反例。

**文件副作用。** 无；增加 ``-o`` 时，输出文件会被原子地创建或替换。

**失败边界。** 当前结果与见证模式不能区分决定性 ``response`` 反例来自未定义
触发器，还是来自已定义触发器但没有响应；必须结合查询和轨迹人工判断。后缀闭合前
不能把主 UNSAT 解读为满足。增加查询边界才能覆盖观察范围；超时不能修复过短边界。

**参考。** 严格后继窗口见 :doc:`../../explanations/bmc_properties/index_zh`，
不完整字段见 :doc:`../../reference/bmc_results/index_zh`。

11. 诊断解析、绑定和不支持的输入
---------------------------------

**CLI。**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q invalid_state.fbmcq
   Failed to compile BMC query: unknown_state at property.predicate: Unknown state path: 'Root.Missing'.
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invalid_state.fbmcq --json -o invalid.json
   Failed to compile BMC query: unknown_state at property.predicate: Unknown state path: 'Root.Missing'.
   $ echo $?
   1
   $ test -e invalid.json
   $ echo $?
   1

**FBMCQ。**

.. literalinclude:: invalid_state.fbmcq
   :language: text
   :caption: invalid_state.fbmcq

**作用。** 查询语法正确，但引用了模型中不存在的状态。

**预期输出。** 标准错误以 ``Failed to compile BMC query`` 开头并指出
``Root.Missing``；退出 ``1``，标准输出为空。

**文件副作用。** 无。增加 ``-o invalid.json`` 后仍不会创建半成品载荷：上面最后两条命令显示该文件并不存在。

**失败边界。** 畸形 ``.fbmcq`` 在解析阶段失败，未知模型对象路径在绑定阶段失败，
已解析但不支持的表达式报告不支持的查询；这些都是受控用户输入错误。带内部
BMC 哨兵文本的回溯是实现失败，应作为缺陷报告，不能改写到看似 UNSAT。

**参考。** 合法与非法形式见 :doc:`../../reference/bmc_query/index_zh`，错误流见
:doc:`../../reference/bmc_results/index_zh`。

12. 选择解释深度
----------------

**CLI。** 在每个深度上运行同一条查询。两次都以 ``3`` 退出，因为不可行场景是一份
报告而不是失败：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility formal --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE FORMAL DOMAIN EXPLANATION
   Classification: the assumptions are internally inconsistent
   ...
   Conflict constraints:
     1. infeasible_two_values.fbmcq:1:1-1:28
        assume at 1: var("x") == 1;
     2. infeasible_two_values.fbmcq:2:1-2:28
        assume at 1: var("x") == 2;
   ...
   $ echo $?
   3
   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE VERIFIED DOMAIN PROOF
   Classification: the assumptions are internally inconsistent
   ...
   Why no execution exists:
     1. At frame 1, x must equal 1.
     2. At frame 1, x must equal 2.
     3. Therefore one value cannot be two things at once. No execution satisfies these query requirements, and the property was not evaluated.
   ...
   $ echo $?
   3

**FBMCQ。**

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**它做什么。** ``--explain-infeasibility`` 询问"为什么这个不可行场景不可行"。
``none``\ （默认）不增加求解工作；``formal`` 增加分类与源组冲突核；``proof`` 再额外
构造一份逐步核验过的推导。该深度从不改变判定，所以提高它无法把不确定的运行变成
确定的——它只增加诊断信息。

**预期输出。** ``formal`` 报告 ``COMPLETE FORMAL DOMAIN EXPLANATION``，含分类、
冲突核成员及其源位置。同一查询改用 ``--explain-infeasibility proof`` 则报告
``COMPLETE VERIFIED DOMAIN PROOF`` 与编号推导。两者都退出 ``3``。

标题行同时说明深度\ **与**\ 完整程度，所以 ``formal`` 深度上的 ``COMPLETE``
意思是"该档承诺的内容都产出了"，而不是"找到了证明"。四种标题行列在
:doc:`../../reference/bmc_results/index_zh`。

**文件副作用。** 不带 ``-o`` 时没有。

**失败边界。** ``proof`` 有额外求解开销：每个 ``input`` 节点做双向核验，每个
``derived`` 步骤独立重新推导。在本 fixture 上额外开销很小（报告会以毫秒打印
``Explanation time``），但成员众多的大冲突核会更贵。只需要判定的 CI 门用 ``none``，
有人要读失败原因时用 ``formal``，推理本身需要可审计时用 ``proof``。

**下一步诊断。** 若 ``proof`` 返回的 ``achieved_mode`` 是 ``formal``，转任务 15。

**参考。** 选项契约与区块布局见 :doc:`../../reference/bmc_results/index_zh`。


13. 读冲突核并据此行动
----------------------

**CLI。**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_cross_step.fbmcq \
       --explain-infeasibility formal --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE FORMAL DOMAIN EXPLANATION
   Classification: assumptions conflict with the feasible prefix
   ...
   Conflict constraints:
     1. infeasible_cross_step.fbmcq:2:1-2:28
        assume at 1: var("x") == 3;
     2. infeasible_cross_step.fbmcq:1:1-1:38
        init state("Root.Idle") where x == 0;
     3. bmc_tasks.fcstm:1:1-1:15
        def int x = 0;
     4. generated transition constraint at step 0
   ...
   Reduction: subset_minimal
   ...
   $ echo $?
   3

**FBMCQ。**

.. literalinclude:: infeasible_cross_step.fbmcq
   :language: text
   :caption: infeasible_cross_step.fbmcq

**它做什么。** 冲突核是那些合在一起让场景不可行的子句，每个都带有它被写下的位置。

**预期输出。** 读法是：分类告诉你该打开哪个文件，成员告诉你该看哪几行。这里帧 1 的假设与初始化器
和声明所强制的值不一致，所以要么改 ``assume`` 的取值，要么改初始值。

第 4 条没有源位置，因为它不是任何人写的：构造器生成了把帧 0 的取值向前传递的转换
约束。生成成员会给出它的类别与它约束的步骤，你无法编辑它——它告诉你作者写下的那些
成员\ *为什么*\ 冲突，而不是该改什么。

**文件副作用。** 不带 ``-o`` 时没有。

**失败边界。** 除报告另有说明，冲突核只保证\ *可靠*\ 。要看 ``Reduction:`` 行：
``raw`` 可能包含不属于该冲突的成员，``partial_minimized`` 是中途停下的，只有
``subset_minimal`` 保证列出的每个成员都承重，如上面的记录所示。改动 ``raw`` 核里的某个成员可能毫无
效果。

**下一步诊断。** 想看串起这些成员的推理，把深度提到 ``proof`` 并读任务 14。

**参考。** 为什么可靠不等于极小，见
:doc:`../../explanations/bmc_solving/index_zh`。


14. 读证明并把一句话追回到子句
------------------------------

**CLI。** JSON 把叙述和证明图并排保存。每句叙述列出它背后的 ``proof_node_ids``，
每个节点有一个 ``stable_id``，这些列表指向的就是它：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --json
   {
     "exit_code": 3,
   ...
           "narrative": {
   ...
                 "proof_node_ids": [
                   "proof.input.0000"
                 ],
                 "text": "At frame 1, x must equal 1."
   ...
           "proof": {
             "graph_minimality": "dependency_pruned",
             "input_minimality": "subset_minimal",
   ...
                 "rule_id": "source_fact",
                 "stable_id": "proof.input.0000",
                 "verification_method": "core_binding"
   ...
                 "rule_id": "source_fact",
                 "stable_id": "proof.input.0001",
                 "verification_method": "core_binding"
   ...
                 "rule_id": "incompatible_equalities",
                 "stable_id": "proof.step.0002",
                 "verification_method": "rule_checker"
               }
             ],
             "root_id": "proof.step.0002",
   ...
             "verification_status": "verified"
   ...
   $ echo $?
   3

**FBMCQ。** 与任务 12 相同的 ``infeasible_two_values.fbmcq``：

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**它做什么。** 在 ``proof`` 深度，叙述就是按依赖顺序读出的证明，每句话都点名它背后
的节点。JSON 同时保留两者，因此一句话与它对应的已核验步骤可以互相到达。

**预期输出。** JSON 的 ``result.feasibility.explanation.proof`` 给出上面所示的图：
两个 ``input`` 节点，一个冲突核成员一个，各自由 ``core_binding`` 与它所重述的成员
做过核验；一个根（``proof.step.0002``），由独立的 ``rule_checker`` 重新推导。
``input_minimality`` 为 ``subset_minimal``，``graph_minimality`` 为
``dependency_pruned``，``verification_status`` 为 ``verified``。

**文件副作用。** 不带 ``-o`` 时没有；加上 ``-o`` 会把完整结果写入文件而不是标准输出。

**失败边界。** 已核验的证明说的是每一步都从旁边点名的子句推出。它没有说编码符合你
的本意——这与重放为见证划出的边界是同一条。另外，收尾那句话报告的是属性\ *未被求值*\ ；
它不是反例。

**下一步诊断。** 若请求了 ``proof`` 而区块显示 ``achieved formal``，读任务 15。

**参考。** 节点词表与各核验方法检查了什么，见
:doc:`../../reference/bmc_results/index_zh`。


15. 处理降级或超时的解释
------------------------

**起始文件。** 本任务使用 ``controller.fcstm``\ （\ :download:`下载
</_models/controller.fcstm>`\ ），与后面含区域模型的任务是同一个模型，以及一条在帧 1
假设 ``motor`` 取值的查询。``Idle`` 在它的 ``during`` 动作里写 ``motor``，所以帧 1
的取值来自一次执行过的转换，而不是来自声明：

.. literalinclude:: infeasible_after_write.fbmcq
   :language: text
   :caption: infeasible_after_write.fbmcq

**CLI。**

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q infeasible_after_write.fbmcq \
       --explain-infeasibility proof --color never
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
   Explanation depth: requested proof, achieved formal
   Classification: assumptions conflict with the feasible prefix
   ...
   Reason: the formal explanation is complete, but no rule in the catalog closes this core.
   ...
   $ echo $?
   3
   $ pyfcstm bmc -i controller.fcstm -q infeasible_after_write.fbmcq \
       --explain-infeasibility proof --json
   {
     "exit_code": 3,
   ...
           "achieved_mode": "formal",
   ...
           "proof": null,
           "reason": "the formal explanation is complete, but no rule in the catalog closes this core.",
           "requested_mode": "proof",
           "status": "partial"
   ...
   $ echo $?
   3

**它做什么。** 解释报告的是它实际达到的深度，而不是被请求的深度。这里的冲突经过一条写
``motor`` 的转换，证明规则目录里没有规则能闭合这种形状的冲突核，所以报告保留
``formal`` 解释并如实说明。任务 14 的冲突只涉及两条 ``assume``，它就能闭合。

**预期输出。** 如上面的记录所示：人类可读报告在 ``PARTIAL`` 标题下写
``requested proof, achieved formal``；在 JSON 中，``requested_mode`` 为 ``proof``，
``achieved_mode`` 为 ``formal``，``status`` 为 ``partial``，``proof`` 为 ``null``。

**文件副作用。** 不带 ``-o`` 时没有。

**失败边界。** 降级不是错误，也不改变退出状态，所以消费方必须比较
``requested_mode`` 与 ``achieved_mode``，而不能假定 ``proof`` 一定存在。缺失
``proof`` 键意味着没有达到该深度，不意味着运行失败。降级运行的 ``formal`` 解释
仍然是完整的：它点名了初始状态、转换约束和两个冲突取值，见 ``Why no execution
exists`` 区块。

**下一步诊断。** 读 ``reason``。``no rule in the catalog closes this core`` 是能力
边界，重试不会改变它。``status`` 里的 ``timeout`` 或 ``unknown`` 是预算问题：用更大
的 ``--timeout-ms`` 重试，或降到 ``formal``。

**参考。** 为什么有些冲突没有证明，见
:doc:`../../explanations/bmc_solving/index_zh`。


16. 在 CI 中基于解释设门而不抓取文本
------------------------------------

**CLI。** 不可行场景退出 ``3``，那是一份报告而不是失败。第一条命令写出 JSON，
一段短脚本读取它：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never \
       --json -o gate.json
   $ echo $?
   3

.. testcode::

   import json

   with open("gate.json") as handle:
       report = json.load(handle)
   explanation = report["result"]["feasibility"]["explanation"]
   print(explanation["requested_mode"], explanation["achieved_mode"])
   print(explanation["status"], explanation["classification"])

.. testoutput::

   proof proof
   complete assumptions_self_conflict

在 ``set -e`` 下运行的 CI 步骤——GitHub Actions 的每个 ``run:`` 步骤都是——不加保护
的调用会在退出 ``3`` 处中断，永远走不到读取。像下面这段 shell 一样保护命令；它不在
文档检查里运行，因为它是 CI 步骤而不是终端记录：

.. code-block:: bash

   pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never \
       --json -o gate.json && status=0 || status=$?
   test "$status" -eq 3

**FBMCQ。** 与任务 12 相同的 ``infeasible_two_values.fbmcq``：

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**它做什么。** 通过带版本的 JSON 契约读解释，而不是读人类报告——门应该依赖前者。

**预期输出。** 脚本先打印 ``proof proof``，然后是 ``complete
assumptions_self_conflict``。

**文件副作用。** ``gate.json`` 被原子写入。

**失败边界。** 退出状态是门必须处理的契约的一部分：``3`` 意味着场景不可行、属性
未被求值，对这个查询而言这是预期结果而非错误。让 ``set -e`` 在此中断的步骤，永远
读不到它自己请求的解释。

在 ``none`` 深度下 ``explanation`` 为 ``null``，所以门必须处理这种
情况而不是直接索引进去。人类措辞与 ``elapsed_ms`` 不是契约，不能对它们断言；枚举
字段才是。无论 ``--color`` 如何设置，ANSI 装饰都不会进入 JSON 或 ``--output``
文件。

**下一步诊断。** 若只想对某一类冲突失败构建，请把 ``classification`` 与封闭词表
比较，而不是匹配打印出来的短语。

**参考。** JSON 可空性与 schema 见 :doc:`../../reference/bmc_results/index_zh`。

17. 处理模型中的运行时错误
--------------------------

**起始文件。** 把下面的模型保存为 ``runtime_error.fcstm``\ ：第一个守卫不成立时，第二个
守卫会除以输入 ``d``。

.. code-block:: fcstm

   input int d;
   state Root {
       [*] -> A;
       state A;
       state B;
       state C;
       A -> B : if [d == 1];
       A -> C : if [10 / d > 1];
   }

下面的命令把同一个模型写成一行（FCSTM 里空白没有含义），连同查询 ``check reach <= 2:
active("Root.B");``，以及先假设 ``d != 0`` 的变体。

**CLI。** 可达的错误以 ``5`` 退出。报告给出出错的运算和步骤，重放确认仿真器引发了同一个
错误：

.. code-block:: console

   $ echo 'input int d; state Root { [*] -> A; state A; state B; state C; A -> B : if [d == 1]; A -> C : if [10 / d > 1]; }' > runtime_error.fcstm
   $ echo 'check reach <= 2: active("Root.B");' > runtime_error.fbmcq
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error.fbmcq
   BMC reach <= 2: RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED
   ...
     Runtime error: division_by_zero at step 1
     Runtime error location: guard g1 in transition Root.A::1::A->C
   ...
     Replay: runtime error reproduced: transition guard evaluation failed: division by zero
   ...
   $ echo $?
   5

**失败边界。** 性质完全没有评估：到达错误的执行无法继续，因此既不声称“成立”也不声称
“违反”。重放未能复现该错误时，退出状态改为 ``4``。

**下一步。** 按需求的含义选择：

- 若环境保证 ``d != 0``\ ，就把它写出来。在 ``check`` 行之前加上
  ``assume always: d != 0;`` 后，运行以 ``0`` 退出，报告
  ``PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``。
- 若 ``d`` 确实可能为零，就是模型有误：保护这次除法，例如写成
  ``d != 0 && 10 / d > 1``\ ，``&&`` 只在 ``d`` 非零时才求值右侧。
- 若只想在不触发错误的执行上评估性质，加上 ``--no-runtime-safety``\ ；这次运行同样以
  ``0`` 退出并给出见证。错误仍然可达，只是报告不再查找它。

.. code-block:: console

   $ printf 'assume always: d != 0;\ncheck reach <= 2: active("Root.B");\n' > runtime_error_assumed.fbmcq
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error_assumed.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error.fbmcq --no-runtime-safety
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...

**参考。** ``runtime_safety`` 结果、``runtime_error_prefix`` 见证和退出状态 ``5`` 见
:doc:`../../reference/bmc_results/index_zh`。

含区域模型的任务
----------------

这些任务卡使用 ``controller.fcstm``，也就是 :doc:`/tutorials/regions/index_zh` 里的联锁控制器（``Running`` 里 ``Safety`` 在 ``Motion`` 之前）。
请把它（:download:`controller.fcstm </_models/controller.fcstm>`）下载到各任务卡所列查询文件旁边。有界结果不能说明界限之外的任何事情，SAT 与 UNSAT 要像上面的任务卡一样通过性质类别来解读。
这些任务卡用人类可读模式运行 ``pyfcstm bmc`` 并读轨迹；单独一行 ``...`` 表示任务卡不讨论的报告行，例如求解耗时。
同样的事实也在 JSON 结果里（``witness.frames``、``witness.steps``），字段见 :doc:`/reference/bmc_results/index_zh`。

18. 从给定位置起检查性质
~~~~~~~~~~~~~~~~~~~~~~~~

**输入。** ``controller.fcstm`` 与 ``region_start.fbmcq``。``init state(...)`` 接受配置（configuration）文本、经过区域的状态路径，或只写拥有者（owner）。
持久变量保留各自的初始值，除非用 ``havoc`` 放开，所以这里放开并约束 ``permit`` 与 ``motor``。

.. literalinclude:: region_start.fbmcq
   :language: text
   :caption: region_start.fbmcq

**命令行。**

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_start.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: On}
          -> Controller.Idle [transition; events=Controller.Stop]
          Safety: Watching -> [done] [transition]
          Motion: On -> [done] [transition]
          Running: [start] -> Controller.Idle [transition]
   ...

**预期输出。** 第 0 帧恰好是你写的配置。查询要求一步内到达 ``Controller.Idle``，离开 ``Running`` 的唯一途径是 ``Stop`` 强制转换（forced transition），所以轨迹止于 ``Controller.Idle``。
第 0 步为每个有动作的区域列出一个局部情形：``Safety`` 与 ``Motion`` 各走自己的转换到 ``[done]``\ （即 ``__region_done__`` 转换），然后拥有者走向 ``Idle`` 的转换；下一张卡会解释这些条目。如果不写 ``havoc { permit, motor }``，同样的 ``where`` 会让场景不可行，因为初始值 ``permit = 0`` 与 ``motor = 0`` 与它矛盾。
这条查询就是 ``region_start.fbmcq`` 去掉 ``havoc`` 部分：

.. literalinclude:: region_start_no_havoc.fbmcq
   :language: text
   :caption: region_start_no_havoc.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_start_no_havoc.fbmcq
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
     Failure boundary: INITIALIZATION
   ...
   $ echo $?
   3

**文件副作用。** 无；报告写到标准输出。

**失败时先查什么。** 结论是 ``SCENARIO INFEASIBLE`` 时，读人读报告里的 ``Failure boundary`` 一行，并把 ``where`` 与变量初始值对照。
编译以 ``invalid_start_position`` 停止时，说明起始文本有误。下面是负例：``region_bad_start.fbmcq`` 写了不存在的状态，
``region_all_done.fbmcq`` 把拥有者的全部区域都标成 ``[done]``，这永远不是停驻位置。两条命令的退出码都是 1：

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_bad_start.fbmcq
   Failed to compile BMC query: invalid_start_position at initial.state_path: Unknown configuration path: 'Controller.Running.Safety.Nope'.
   $ echo $?
   1
   $ pyfcstm bmc -i controller.fcstm -q region_all_done.fbmcq
   Failed to compile BMC query: invalid_start_position at initial.state_path: all regions are done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1

**参考。** :doc:`/reference/bmc_query/index_zh`。

19. 用 ``active`` 配置模式匹配位置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**输入。** 同一个模型上的三条查询。``init state(...)``\ *构造*\ 一个位置，所以它没写的区域等待初始化；``active("...{...}")``\ *匹配*\ 一个位置，所以它没写的区域不受约束。

.. literalinclude:: region_pattern_construct.fbmcq
   :language: text
   :caption: region_pattern_construct.fbmcq

.. literalinclude:: region_pattern_match.fbmcq
   :language: text
   :caption: region_pattern_match.fbmcq

.. literalinclude:: region_pattern_construct_miss.fbmcq
   :language: text
   :caption: region_pattern_construct_miss.fbmcq

**命令行。** 每条命令只打印第 0 帧（轨迹里的 ``0:`` 一行）：性质在那里已经成立，后面的帧是求解器的自由选择。

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_pattern_construct.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: [init], Motion: On}
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_pattern_match.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: On}
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_pattern_construct_miss.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1

**预期输出。** 第一条查询的起始文本没有写 ``Safety``：第 0 帧显示 ``Safety: [init]``，写了 ``[init]`` 的模式能匹配它。第二条查询两个区域都写了，
模式没有写 ``Safety``，所以 ``Watching`` 无关紧要。第三条查询以 ``Safety: Watching`` 起步，却要求 ``Safety: [init]``：没有见证
（退出码 1）。模式恰好在写出的区域一致时成立；在拥有者正被进入时发生的调用里，``[init]`` 对尚未启动的区域也成立。

**文件副作用。** 无。

**失败时先查什么。** 模式被拒绝时，编译以 ``invalid_active_pattern`` 停止（负例 ``region_bad_pattern.fbmcq``）：

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_bad_pattern.fbmcq
   Failed to compile BMC query: invalid_active_pattern at property.predicate: Unknown state path: 'Controller.Running.Safety.Nope'.
   $ echo $?
   1

模式匹配得过宽时，检查你省略了哪些区域。

**参考。** :doc:`/reference/bmc_query/index_zh`。

20. 读懂 ``local_cases`` 与 ``case_label``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**输入。** ``region_cases.fbmcq`` 与 ``region_cover.fbmcq``。见证的每一步是整整一个周期。``case_label`` 是在所有区域之外运行的那个情形的标签，没有则为 ``null``。
``local_cases`` 按执行顺序为每个有动作的作用域列出一项：``scope``\ （状态路径，在所有区域之外时为 ``null``）、``kind`` 与 ``label``。

.. literalinclude:: region_cases.fbmcq
   :language: text
   :caption: region_cases.fbmcq

.. literalinclude:: region_cover.fbmcq
   :language: text
   :caption: region_cover.fbmcq

**命令行。** 人读轨迹把每一步打印在以步号开头的一行，后面每个情形一行，作用域相对于拥有者。第二条命令覆盖一个局部情形：

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Idle
          -> Controller.Running{Safety: Watching, Motion: Off} [transition; events=Controller.Start]
          Controller.Idle -> Controller.Running [transition]
          Running: [start] -> Safety.Watching [initial]
          Running: [start] -> Motion.Off [initial]
     1: Controller.Running{Safety: Watching, Motion: Off}
          -> Controller.Running{Safety: Watching, Motion: On} [transition]
          Safety: Watching -> Watching [fallback]
          Motion: Off -> On [transition]
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_cover.fbmcq
   BMC cover <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: Off}
          -> Controller.Running{Safety: Watching, Motion: On} [transition]
          Safety: Watching -> Watching [fallback]
          Motion: Off -> On [transition]
   ...

同样的情形在 JSON 里是每个见证步的 ``case_label`` 与 ``local_cases`` 字段：

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq --json
   {
     "exit_code": 0,
   ...
           "case_label": "Controller.Idle::transition::Controller.Running::0",
   ...
           "local_cases": [
             {
               "kind": "transition",
               "label": "Controller.Idle::transition::Controller.Running::0",
               "scope": null
             },
   ...
           "case_kind": "transition",
           "case_label": null,
   ...
           "local_cases": [
             {
               "kind": "fallback",
               "label": "Controller.Running.Safety.Watching::fallback::Controller.Running.Safety.Watching::0",
               "scope": "Controller.Running.Safety"
             },
             {
               "kind": "transition",
               "label": "Controller.Running.Motion.Off::transition::Controller.Running.Motion.On::2",
               "scope": "Controller.Running.Motion"
             }
           ],
   ...

**预期输出。** 第 0 步进入 ``Running``：``0:`` 下面第一行是外层转换（JSON 里的 ``case_label``），第一个情形在所有区域之外，拥有者作用域里每个区域各有一个 ``initial`` 情形。
第 1 步没有外层情形，因为所有情形都在区域里运行：``Safety`` 保持（``fallback``），``Motion`` 迁移（``transition``）。JSON 里同样的情形是 ``local_cases``，第 1 步的 ``case_label`` 为 ``null``。
``cover`` 查询接受单独的 ``case("标签")``，请从见证里复制标签。标签末尾的 ``::2`` 是该情形在展开后的情形中的序号，不是你写下的任何东西的个数。

**文件副作用。** 无。

**失败时先查什么。** ``cover`` 说标签未知时，消息是 ``Failed to compile BMC query: cover case label is unknown``：从同一模型上 ``reach`` 查询的见证里复制标签。

**参考。** :doc:`/reference/bmc_results/index_zh`。

21. 处理 ``max_group_reentries`` 超限
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**输入。** 拥有区域的状态可以在一个周期内被再次进入（``Owner -> Owner``）。每一圈的取值都在变化时，关系会把各圈逐个展开，最多
``BmcOptions.max_group_reentries`` 次（默认 16），超过就抛出 ``BmcBuildError``，而不是近似。``region_reentry_six.fcstm`` 需要六圈；
``region_reentry_loop.fcstm`` 的条件（``n < limit``）没有任何取值能让它停下。

.. literalinclude:: region_reentry_six.fcstm
   :language: fcstm
   :caption: region_reentry_six.fcstm

.. literalinclude:: region_reentry_loop.fcstm
   :language: fcstm
   :caption: region_reentry_loop.fcstm

**命令或代码。** 命令行没有设置这个上限的选项，所以在 Python 里调大它：

.. testcode::

   from pyfcstm.bmc import BmcBuildError, BmcOptions, compile_bmc_query
   from pyfcstm.model import load_state_machine_from_file

   query = "check reach <= 1: terminated();"
   for name, limit in [("region_reentry_six", 7), ("region_reentry_six", 6), ("region_reentry_loop", 64)]:
       model = load_state_machine_from_file(name + ".fcstm")
       options = BmcOptions(max_group_reentries=limit)
       try:
           compile_bmc_query(model, query, options=options)
           print(name, limit, "compiled")
       except BmcBuildError as error:
           print(name, limit, "refused:", error)

.. testoutput::

   region_reentry_six 7 compiled
   region_reentry_six 6 refused: state 'Root.Owner' re-enters its own group more than 6 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.
   region_reentry_loop 64 refused: state 'Root.Owner' re-enters its own group more than 64 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.

再用命令行在同样两个模型上对照：

.. code-block:: console

   $ pyfcstm bmc -i region_reentry_six.fcstm -q region_reentry.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i region_reentry_loop.fcstm -q region_reentry.fbmcq
   ...
   Traceback (most recent call last):
   ...
   _BmcCliInternalError: state 'Root.Owner' re-enters its own group more than 16 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.
   $ echo $?
   1

**预期输出。** 六圈模型在上限为 16（默认值）或 7 时能编译，为 6 时被拒绝；消息会指出状态和选项名。无界的循环在任何上限下都被拒绝：调大数字对它没有帮助（上面命令行用默认上限 16 时出现的就是同样的消息）。
上面的命令行输出不是读取这个上限的办法。六圈模型能构建，它的退出码 1 是一个普通的结论：``reach terminated()`` 在一步内没有见证（``GOAL UNREALIZABLE WITHIN BOUND``），
这与构建无关。对于无界循环，命令行目前以退出码 1 和一段 Python 追踪信息停止，只有最后一行（同样的消息）有用。命令行没有设置这个上限的选项，所以本卡通过 Python 接口来做。

**文件副作用。** 无。

**失败时先查什么。** 先问这个循环是否本该停下：让条件依赖某个计数器或常量，使某个取值能让它停下。只有循环有界、仅仅比 16 圈长时才调大上限。

**参考。** :doc:`/reference/bmc_results/index_zh`。

22. 让查询算得动
~~~~~~~~~~~~~~~~

**输入。** 一条很慢或超时的查询。代价随转换写入的变量数、上界 ``k``、状态数与区域数增长；区域之间是相加而不是相乘，但彼此互斥的区域在求解器必须证明
“不可能”时可能指数增长。这些结论来自合成模型上的测量，不是承诺：数据与推理见 :doc:`/explanations/bmc_scaling/index_zh`，``tools/measure_bmc_scaling.py`` 可以重新生成数据，优化思路记录在\ `问题 #600 <https://github.com/HansBug/pyfcstm/issues/600>`_\ 。

**命令行。** 一次把上界加一，对结论分类而不是默认它是 SAT 或 UNSAT，并用 ``--max-bound`` 设上限。``k=1`` 的查询是
``region_reach_k1.fbmcq``，``region_cases.fbmcq`` 是同一条查询取 ``k=2``：

.. literalinclude:: region_reach_k1.fbmcq
   :language: text
   :caption: region_reach_k1.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_reach_k1.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq --max-bound 1
   Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1.
   $ echo $?
   1

**预期输出。** ``k=1`` 还没有见证（退出码 1），``k=2`` 是第一个有见证的上界，所以对这个问题再加深没有收益；策略 ``--max-bound 1`` 在求解之前就以退出码 1 拒绝了 ``k=2`` 的查询。
把 ``unknown`` 与 ``timeout`` 当作\ *没有结论*\ 的结果，在 CI 里为它们单独设定预期的退出处理；用 ``--timeout-ms`` 给每次 ``check()`` 设上限（退出码 3）。
这些运行都没有超时，所以没有一条显示 ``timeout`` 结论。

缩小一条太慢的查询的步骤：

1. 减少区域写入的变量：只对性质需要的变量 ``havoc``，其余用 ``where`` 约束。
2. 从一个位置起步（任务 18），而不是冷启动，这样第一个上界不会花在走到那里上。
3. 先问能展示该行为的最小 ``k``，再加深。
4. 一次只查一条性质，不要把不相关的谓词合在一起。
5. 区域彼此互斥（一个只有在另一个不运行时才能运行）时，预期“不可能”的证明最慢，此时把 ``k`` 保持得小。

**文件副作用。** 无。

**失败时先查什么。** 读 ``result.status``。``timeout`` 表示某次求解器 ``check()`` 没有在 ``--timeout-ms`` 内完成，它不是结论。

**参考。** :doc:`/reference/bmc_results/index_zh`。

选择并比较求解器配置
--------------------

使用本页的 ``bmc_tasks.fcstm`` 和 ``reach.fbmcq``，在同一目录分别运行三个配置：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile default --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_profile": "default",
   ...
       "status": "sat",
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile logic --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_logic": "QF_LIA",
       "solver_profile": "logic",
   ...
       "status": "sat",
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile tactic --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_profile": "tactic",
   ...
       "status": "sat",
   ...

三个命令均退出 ``0``，输出 ``result.status="sat"``、
``result.property_satisfied=true`` 和 ``replay.ok=true``；配置名分别记录在
``result.solver_profile``。未指定 ``-o``，所以只写标准输出，不生成文件。
查看 ``result.solver_logic`` 可以分辨逻辑片段选择与未命中后的回退：上面 ``logic``
配置选中了 ``QF_LIA``。

先比较结论与重放，再比较耗时。不同策略可能选出不同的合法见证；
``solver_statistics`` 中的上下文累计计数不能当成单次查询的工作量。
要测量自己的模型，应固定输入、Python/Z3 版本，在独立进程中重复运行；
单次更快不足以支持更换默认配置。仓库中的 ``benchmarks/bmc/solving/``
提供四组对照、不可变原始记录和预先登记的性能阈值。

见证默认可复现。\ ``--solver-context fresh`` 把线性算术公式放进全新的 Z3 上下文求解，
上下文里项的内部编号，以及由它决定的搜索路径和返回的见证，只取决于公式本身。
于是同一个模型、查询和选项，无论公式怎样构造、进程之前解过什么，都得到同一条见证。
``--solver-context shared`` 在构造公式的上下文里求解，任何不相关的改动之后都可能返回
另一条有效见证。线性算术之外的查询两种设置下都在共享上下文里求解；\ ``result.solver_context``
会说明本次运行用的是哪一个。

输入 ``--solver-profile fast`` 会退出 ``2``；使用列出的三个小写值之一：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile fast
   Usage: pyfcstm bmc [OPTIONS]
   Try 'pyfcstm bmc --help' for help.

   Error: Invalid value for '--solver-profile': 'fast' is not one of 'default', 'logic', 'tactic'.
   $ echo $?
   2

如果可选配置返回不确定结果，先用 ``default`` 重跑并检查 ``reason``，
不要把它计为性质通过。``--explain-infeasibility formal`` 或 ``proof``
可与任一配置组合，解释路径仍使用默认求解器。

字段、回退和预算边界见 :doc:`../../reference/bmc_results/index_zh`。

按查询尝试保守切片
------------------

只有显式传入开关才启用切片。本页的模型含有抽象动作 ``Root.Idle.Tick``，所以切片会跳过
整个模型，什么也不删除：

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --cone-slicing --json
   {
     "exit_code": 0,
   ...
       "cone_slicing": {
         "dropped_variables": [],
         "enabled": true,
         "fallback": false,
         "retained_count": 1,
         "skipped_reason": "abstract_actions"
       },
   ...

Python 编译入口使用 ``compile_bmc_query(model, query,
options=BmcOptions(cone_slicing=True))``；文件入口支持
``build_bmc_output(..., cone_slicing=True)``。该参数只接受 bool。

切片保留查询引用、guard、操作分支条件及其依赖。除法、取模、幂、函数和浮点计算等
不能证明安全的赋值也保留；声明为 int 的变量若在动作内部暂存非整数值，相关计算
同样保留。任意 abstract 动作会让整个模型跳过切片。此策略保证未读取输出中的
危险运算不会被删掉而改变场景可行性，包括没有 SAT 见证可供重放的 UNSAT 结果。

初始帧和全部变量符号保持完整。解码时使用原始运行时回填被切变量，因此每帧仍有
全部变量；固定初值和事件的确定轨迹保持一致，多解查询可能选择另一条合法路径。
主见证及 response 的 incomplete suffix 都会在求解返回前验证。验证失败时，最多
使用完整模型重跑一次，并共享剩余求解预算；不会重新获得一份 timeout。验证与重建
会消耗剩余时间，但 timeout 不是强制打断这些 Python 操作的墙钟期限。

开启时查看 ``result.cone_slicing`` 中的删除列表、跳过原因和 ``fallback``。
关闭时 JSON 不增加该字段。``total_elapsed_ms`` 包含内部验证和回退；评估性能时
同时测量编译、求解和对外解码重放，不能把见证回填成本从总耗时中扣掉。

本次实测正确性门禁通过，但公式规模仅缩减 6.09%，未达到 T3 的 20% 门槛；
切片默认保持关闭。单例求解最多退化 131.73%，所以应同时比较编译、求解和
对外重放总成本。详细数字见 :ref:`sec-bmc-cone-measurements-zh`。
