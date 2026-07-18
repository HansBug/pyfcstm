BMC 任务指南
============

完成 :doc:`../../tutorials/bmc/index_zh` 后，用本页解决具体任务。先进入一个空的
工作目录，把 :download:`任务模型 <bmc_tasks.fcstm>` 下载到这里。将每项任务的
短 FBMCQ 代码块保存成命令所写的文件名，再从同一目录运行命令。专用模型很小：

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``bmc_tasks.fcstm``

它包含一个持久变量、一个事件、一个抽象 ``during`` 动作和一条事件转换。下面
每个示例都先给直接 CLI 命令，再给需要保存的完整短 ``.fbmcq`` 文本，
然后说明作用、预期输出和失败边界。若一个代码块用于对照多个方案，正文会明确
标出它们属于不同文件。

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

任务卡读法
----------

每张任务卡都包含直接 CLI 命令、相关查询片段、简短说明、预期输出、副作用、
失败边界，以及指向完整语法或结果事实的参考页。求解器结论都是报告，包括预期的
非零结论。受控输入错误会向标准错误写短消息，且不创建半成品报告。

1. 运行所选性质类别
--------------------

**CLI。** 将 ``reach.fbmcq`` 替换为你选择的性质查询文件。

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach.fbmcq --json

**FBMCQ。** 下面是七个独立查询文件，不是同一个文件中的七条 ``check``。
每个文件先写 ``init state("Root.Idle");``，再且仅再写表中对应的一条：

.. list-table:: 每个性质文件只含一条 ``check``
   :header-rows: 1
   :widths: 19 81

   * - 文件
     - 公共 ``init`` 行之后的子句
   * - ``reach.fbmcq``
     - ``check reach <= 1: active("Root.Idle");``
   * - ``forbid.fbmcq``
     - ``check forbid <= 1: active("Root.Done");``
   * - ``invariant.fbmcq``
     - ``check invariant <= 1: x == 0;``
   * - ``must_reach.fbmcq``
     - ``check must_reach <= 1: active("Root.Idle");``
   * - ``exists_always.fbmcq``
     - ``check exists_always <= 1: x == 0;``
   * - ``response.fbmcq``
     - ``check response <= 1: trigger false -> within 1 active("Root.Done");``
   * - ``cover.fbmcq``
     - ``check cover <= 1: case("Root.Idle::transition::Root.Done::0");``

**作用。** 命令向模型提出一个有界问题。查询类别决定 SAT 表示正向见证还是反例。
共同的热启动行让第 0 帧成为 ``Root.Idle``；下面边界为 1 的 ``forbid`` 和
``cover`` 结果依赖这个前提。

**预期输出。** 直接 ``reach`` 命令的 JSON 包含 ``"kind": "reach"``、
``"status": "sat"``、``"outcome": "witness_found"`` 和
``"exit_code": 0``。已验证的夹具矩阵为：

.. code-block:: text

   reach sat witness_found exit=0
   forbid sat property_violated exit=1
   invariant unsat property_satisfied exit=0
   must_reach unsat property_satisfied exit=0
   exists_always sat witness_found exit=0
   response unsat property_satisfied exit=0
   cover sat witness_found exit=0

**文件副作用。** 除非增加 ``-o``，否则没有文件副作用。

**失败边界。** ``cover`` 只接受裸写、已知且可覆盖的 ``case("...")`` 标签。
有界结果不能说明所选边界之外的行为。

**参考。** 精确性质形式见 :doc:`../../reference/bmc_query/index_zh`，目标公式含义见
:doc:`../../explanations/bmc_properties/index_zh`。

2. 指定状态并替换部分初始值
----------------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q init_havoc_where.fbmcq --json

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle") havoc { x } where x == 7;
   check reach <= 1: x == 7;

**作用。** 查询从 ``Root.Idle`` 开始，只把 ``x`` 从初始值约束中移除，并把
第零帧约束为 ``x == 7``。

**预期输出。** JSON 包含 ``"kind": "reach"``、
``"outcome": "witness_found"``，并且某个见证帧的 ``vars.x`` 为 ``7``；
退出状态是 ``0``。

**文件副作用。** 无；报告写到标准输出。

**失败边界。** ``where`` 只添加初始约束，不会覆盖初始值。不写
``havoc { x }`` 时，模型的 ``x = 0`` 与 ``where x == 7`` 会使轨迹公式 UNSAT。
``havoc *`` 会移除所有持久变量的初始值，应优先使用具名集合。

**参考。** ``cold``、``state(...)``、``terminated``、``havoc`` 与 ``where``
的合法形式见 :doc:`../../reference/bmc_query/index_zh`。

3. 约束帧和事件输入
--------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q assumptions.fbmcq --json \
       -o /tmp/bmc-assumptions.json

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle");
   assume always: x == 0;
   assume event("Root.Go", 0) == false;
   assume events cardinality at_most_one {"Root.Go"};
   check invariant <= 1: x == 0;

**作用。** 假设在每个帧约束 ``x``，在第零步禁用 ``Root.Go``，并要求所选事件
集合中至多有一个事件。

**预期输出。** 载荷报告 ``invariant``、``unsat``、``property_satisfied`` 和
退出 ``0``。由于在这些假设下不存在反例，``witness`` 与 ``replay`` 均为
``null``。

**文件副作用。** 原子创建或替换 ``/tmp/bmc-assumptions.json``。

**失败边界。** 假设会限制被搜索的环境，可能排除原本可行的行为。事件必须使用
全限定路径；未知路径是绑定错误，不是 UNSAT 结论。

**参考。** ``always``、``at``、事件选择器、范围与基数见
:doc:`../../reference/bmc_query/index_zh`。

4. 匹配抽象调用及其快照
------------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q calls.fbmcq --json \
       -o /tmp/bmc-calls.json

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle");
   check reach <= 1:
       called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
       && call_count("Root.Idle.Tick", step=*) == 1;

**作用。** 查询选择第零步的 ``Root.Idle.Tick`` 调用，要求其运行时角色，检查
调用时的 ``x`` 快照，并统计一步边界内的调用次数。

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

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q calls.fbmcq

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle");
   check reach <= 1:
       called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
       && call_count("Root.Idle.Tick", step=*) == 1;

**作用。** 人类可读模式以紧凑形式打印同一见证，并在报告成功前运行强制重放可信
门禁。

**预期输出。** 第一行是 ``BMC reach <= 1: WITNESS FOUND WITHIN BOUND``。随后
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

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q forbid.fbmcq --json \
       -o /tmp/bmc-ci.json

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle");
   check forbid <= 1: active("Root.Done");

**作用。** 这条合法查询会有意找到禁止状态反例，展示“存在机器可读报告但进程
退出非零”的情况。

**预期输出。** 命令退出 ``1``，但仍创建 JSON；其中包含 ``"status": "sat"``、
``"outcome": "property_violated"`` 和 ``"exit_code": 1``。持续集成可按项目
策略阻塞或容许该结论，但不能把它误当成 CLI 输入错误。

**文件副作用。** 即使结论退出 ``1``，也会创建 ``/tmp/bmc-ci.json``。

**失败边界。** 退出 ``0`` 表示性质满足或找到正向见证；``1`` 也覆盖受控错误，
但受控错误只有 stderr、没有报告；``2`` 是 Click 用法错误；``3`` 是无定论；
``4`` 是结构化重放不匹配。存在报告时必须读取 JSON。

**参考。** 完整分支矩阵与稳定 JSON 模式见
:doc:`../../reference/bmc_results/index_zh`。

7. 原子写入完整报告
--------------------

**CLI。**

.. code-block:: bash

   mkdir -p /tmp/pyfcstm-bmc
   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q invariant.fbmcq \
       --json -o /tmp/pyfcstm-bmc/result.json

**FBMCQ。**

.. code-block:: text

   init state("Root.Idle");
   check invariant <= 1: x == 0;

**作用。** CLI 先通过同目录临时文件写出完整 JSON 载荷，再替换目标路径。

**预期输出。** 标准输出为空；文件包含 ``"exit_code": 0``。

**文件副作用。** 原子创建或替换目标文件。父目录必须已经存在。

**失败边界。** ``pyfcstm bmc`` 不创建父目录。若读取、编译、内部求解或写入在
完整载荷形成前失败，命令不得把输出文件声明为成功。

**参考。** 覆盖写、stdout、stderr 和 UTF-8 规则见
:doc:`../../reference/bmc_results/index_zh`。

8. 强制最大边界策略
--------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach_bound_2.fbmcq \
       --max-bound 1

**FBMCQ。**

.. code-block:: text

   check reach <= 2: active("Root.Idle");

**作用。** 查询请求边界 2，而命令行策略最多允许 1。

**预期输出。** stderr 包含 ``Failed to compile BMC query``、``query_bound=2``
和 ``max_bound=1``；命令退出 ``1``。

**文件副作用。** 无。即使指定 ``-o``，策略拒绝发生在报告构造前，也不会创建或
修改报告。

**失败边界。** ``--max-bound`` 是构造前策略门禁，不会静默截断查询。小于 1 的
值属于 Click 用法错误，退出 ``2``。

**参考。** CLI 选项与错误分类见 :doc:`../../reference/bmc_results/index_zh`。

9. 设置单次求解器检查超时
--------------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o /tmp/bmc-timeout.json

**FBMCQ。**

.. code-block:: text

   check reach <= 2: active("Root.Idle");

**作用。** 命令把一毫秒超时传给每次求解器 ``check()``。这个夹具在负载中的
开发机器上通常会报告超时，但极快机器可能先得到决定性结果。

**预期输出。** 已验证运行中，命令退出 ``3``，JSON 包含
``"timeout_ms": 1``、``"status": "timeout"`` 和
``"outcome": "timeout"``。如果求解先完成，JSON 仍记录
``"timeout_ms": 1``，并使用普通决定性退出状态。

**文件副作用。** ``/tmp/bmc-timeout.json`` 保存完整结论。

**失败边界。** 该超时不是解析、展开、公式构造或整个 CLI 的墙钟预算。
``response`` 可能再执行一次边界不完整检查，后者也得到完整超时预算。

**参考。** 超时字段见 :doc:`../../reference/bmc_results/index_zh`，求解顺序见
:doc:`../../explanations/bmc_solving/index_zh`。

10. 区分 ``response`` 违反与边界不完整
----------------------------------------

**CLI。** 先运行缺失响应场景；需要短边界场景时，用同一命令形状替换为
``response_incomplete.fbmcq``。

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q response_missing.fbmcq --json \
       -o /tmp/bmc-response.json

**FBMCQ 文件：** ``response_missing.fbmcq``

.. code-block:: text

   check response <= 1: trigger true -> within 1 false;

**FBMCQ 文件：** ``response_incomplete.fbmcq``

.. code-block:: text

   check response <= 1: trigger true -> within 2 false;

**作用。** 第一条查询是决定性违反：触发存在，且没有响应能满足一步窗口。第二种
形状在边界 1 下无定论，因为两个后继帧的响应窗口越过已检查后缀。

**预期输出。** ``response_missing.fbmcq`` 退出 ``1``，``status`` 为 ``sat``，
``outcome`` 为 ``property_violated``。``response_incomplete.fbmcq`` 退出
``3``，主 ``status`` 为 ``unsat``，``outcome`` 为 ``incomplete``，
``incomplete`` 为 true，``incomplete_status`` 为 ``sat``，见证与重放均为
``null``。

**文件副作用。** 在 ``/tmp`` 下原子创建或替换所选输出文件。

**失败边界。** 当前结果与见证模式不能区分决定性 ``response`` 反例来自未定义
触发器，还是来自已定义触发器但没有响应；必须结合查询和轨迹人工判断。后缀闭合前
不能把主 UNSAT 解读为满足。增加查询边界才能覆盖观察范围；超时不能修复过短边界。

**参考。** 严格后继窗口见 :doc:`../../explanations/bmc_properties/index_zh`，
不完整字段见 :doc:`../../reference/bmc_results/index_zh`。

11. 诊断解析、绑定和不支持的输入
---------------------------------

**CLI。**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q invalid_state.fbmcq

**FBMCQ。**

.. code-block:: text

   check reach <= 1: active("Root.Missing");

**作用。** 查询语法正确，但引用了模型中不存在的状态。

**预期输出。** 标准错误以 ``Failed to compile BMC query`` 开头并指出
``Root.Missing``；退出 ``1``，标准输出为空。

**文件副作用。** 无。增加 ``-o /tmp/invalid.json`` 后仍不能创建半成品载荷。

**失败边界。** 畸形 ``.fbmcq`` 在解析阶段失败，未知模型对象路径在绑定阶段失败，
已解析但不支持的表达式报告不支持的查询；这些都是受控用户输入错误。带内部
BMC 哨兵文本的回溯是实现失败，应作为缺陷报告，不能改写到看似 UNSAT。

**参考。** 合法与非法形式见 :doc:`../../reference/bmc_query/index_zh`，错误流见
:doc:`../../reference/bmc_results/index_zh`。
