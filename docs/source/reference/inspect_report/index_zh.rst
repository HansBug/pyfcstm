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
     - 默认检查图：忽略守卫，跟随组合状态初始边。进入 ``Owner.[H]`` / ``Owner.[H*]`` 的转换还会到达默认路径上的状态以及恢复能重新进入的状态，见 :ref:`dsl-history-reference-zh`\ 。
   * - ``event_emission_map``
     - 事件名到可发射它的源状态集合。
   * - ``var_dataflow``
     - 变量名到读写状态路径。
   * - ``aspect_impact_map``
     - 组合状态路径到被切面动作影响的后代叶状态。
   * - ``action_ref_graph``
     - 命名动作签名到被引用命名动作签名。
   * - ``regions``
     - 可选。``RegionInfo`` 对象数组，只有模型声明了区域时才出现，见 :ref:`inspect-report-regions-zh`\ 。
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
     - ``path``、``name``、``parent_path``、叶/伪/组合布尔值、子状态、初始目标、生命周期动作数组、切面数组和 ``has_abstract_action``。使用了历史的模型按展开前的书写形式报告，因此不会出现展开生成的状态或初始目标。见 :ref:`dsl-history-reference-zh`\ 。
   * - ``RegionInfo``
     - ``path``、``name``、``owner_path``、``index``、``substates``、``initial_targets``、``aspect_before`` 和 ``aspect_after``，见 :ref:`inspect-report-regions-zh`\ 。
   * - ``TransitionInfo``
     - 源/目标、事件、事件作用域、守卫、效果动作、自赋值、强制来源、索引和组合投影 / 来源字段。``target_history``\ （\ ``shallow``\ 、\ ``deep`` 或 null）标出进入 ``Target.[H]`` / ``Target.[H*]`` 的转换，其 ``to_path`` 为历史所有者。
   * - ``ComboOriginInfo``
     - ``origin_id``、转换 span、触发器 span 和有序 ``terms``。
   * - ``ComboOriginTermInfo``
     - 项序号、角色、是否消耗触发项、文本，以及转换 / 触发器 / 项 / 值 / 删除 span。
   * - ``ComboOriginRefInfo``
     - 项序号、角色、是否消耗触发项、文本、转换 / 触发器 / 项 / 值 / 删除 span，以及 authored endpoint 来源信息：``source_kind``\ （``state``/``init``）、``source_path``、initial selection 的 ``selection_owner_path``、``target_kind``\ （``state``/``exit``）和 exit 时为 ``[*]`` 的 ``target_path``。
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
     - 作者写的转换数量、``transitions_per_state``\ （``T / S``）、不可达数量/比例，以及守卫/效果/无事件无守卫比例。``S`` 是非伪状态数量；每个比例同时给出分子和分母，空总体返回 ``null``。默认只对三项结构信号给出建议阈值：``T / S <= 6.0``、不可达叶状态比例 ``<= 0.10``、不可达转换比例 ``<= 0.10``；超出只记录元数据，不产生诊断。
   * - ``ModelDiagnostic``
     - ``code``、``severity``、``message``、``span``、``refs`` 和可选 ``suggested_fix``。
   * - ``Span``
     - ``line``、``column``、``end_line`` 和 ``end_column``。

.. _inspect-report-regions-zh:

报告中的区域
----------------------------------------

声明了 ``region`` 块的模型会多出一个可选的顶层 ``regions`` 数组。只有这类模型才有它，因此不含区域的模型，其报告保持不变。每个 ``RegionInfo`` 给出区域的 ``path`` 和 ``name``，拥有它的状态的 ``owner_path``，``index``\ （在同一所属状态的区域中从 0 开始的声明顺序，也就是执行顺序），区域的直接子状态 ``substates``，区域的 ``initial_targets``，以及 ``aspect_before`` / ``aspect_after`` 标签。

区域内的状态、转换、事件和动作出现在普通数组里。区域内状态的 ``parent_path`` 是区域路径；拥有区域的状态的 ``is_composite`` 为真，``substates`` 为空。报告描述的是书写形式的模型，因此 ``active("...")`` 查询不会往 ``variables`` 里增加隐藏标志变量。

.. list-table:: ``RegionInfo`` 字段
   :header-rows: 1
   :widths: 24 76

   * - 字段
     - 含义
   * - ``path``
     - 区域的点路径，即拥有者（owner）路径加区域名，例如 ``Root.First``\ 。
   * - ``name``
     - 区域的书写名字。
   * - ``owner_path``
     - 拥有这个区域的状态的点路径。
   * - ``index``
     - 在同一拥有者的区域中从 0 开始的声明顺序，也是执行顺序。
   * - ``substates``
     - 区域的直接子状态路径。
   * - ``initial_targets``
     - 区域内 ``[*] -> ...`` 转换的目标，每项含 ``target``、``guard``、``event`` 和 ``is_unconditional``\ 。
   * - ``aspect_before`` / ``aspect_after``
     - 区域内声明的 ``>> during before`` 与 ``>> during after`` 动作的标签。

下面的模型有两个区域，都写 ``out``\ 。第一条命令输出人读报告的开头几行；第二条命令输出 JSON 报告，其中 ``...`` 代表本页不讨论的部分，剩下的是盲目覆盖诊断、完整的 ``regions`` 数组和相邻的 ``states`` 事实。

.. literalinclude:: region_overwrite_basic.fcstm
   :language: fcstm
   :caption: region_overwrite_basic.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_overwrite_basic.fcstm --color never
   [WARN] FCSTM Inspect Report: region_overwrite_basic.fcstm

   Summary
     status: warning
     root: Root
     states: 3 total / 2 leaf
     transitions: 2
     regions: 2
       Root.First: order 0 in Root; 1 states
       Root.Second: order 1 in Root; 1 states
     variables: 2
       out: control; external supply: none
       y: control; external supply: none
   ...

.. code-block:: console

   $ pyfcstm inspect -i region_overwrite_basic.fcstm --format json
   ...
       {
         "code": "W_REGION_BLIND_OVERWRITE",
         "message": "Region 'Root.Second' overwrites variable 'out' in every cycle without using the value written by the earlier region 'Root.First'; that earlier write is lost whenever it runs.",
         "refs": {
           "owner_path": "Root",
           "previous_region": "Root.First",
           "previous_write_span": {
             "column": 28,
             "end_column": 36,
             "end_line": 5,
             "line": 5
           },
           "region": "Root.Second",
           "variable": "out"
         },
         "severity": "warning",
         "span": {
           "column": 28,
           "end_column": 40,
           "end_line": 9,
           "line": 9
         }
       }
     ],
   ...
     "regions": [
       {
         "aspect_after": [],
         "aspect_before": [],
         "index": 0,
         "initial_targets": [
           {
             "event": null,
             "guard": null,
             "is_unconditional": true,
             "target": "Root.First.A"
           }
         ],
         "name": "First",
         "owner_path": "Root",
         "path": "Root.First",
         "substates": [
           "Root.First.A"
         ]
       },
       {
         "aspect_after": [],
         "aspect_before": [],
         "index": 1,
         "initial_targets": [
           {
             "event": null,
             "guard": null,
             "is_unconditional": true,
             "target": "Root.Second.B"
           }
         ],
         "name": "Second",
         "owner_path": "Root",
         "path": "Root.Second",
         "substates": [
           "Root.Second.B"
         ]
       }
     ],
     "root_state_path": "Root",
     "states": [
       {
   ...
         "is_composite": true,
   ...
         "parent_path": null,
         "path": "Root",
         "substates": []
       },
       {
   ...
         "is_composite": false,
   ...
         "parent_path": "Root.First",
         "path": "Root.First.A",
         "substates": []
       },
   ...

不含区域的模型根本没有 ``regions`` 键：

.. code-block:: console

   $ pyfcstm inspect -i region_branch_plain_exits.fcstm --format json
   ...
     "reachability_graph": {
   ...
     },
     "root_state_path": "Root",
   ...

输出这样读。``index`` 为 0 和 1 是声明顺序，所以 ``Root.First`` 先于 ``Root.Second`` 执行。\ ``Root.First.A`` 的 ``parent_path`` 是 ``Root.First``\ ，\ ``Root`` 是复合状态且没有直接的 ``substates``\ 。不含区域的模型根本没有 ``regions`` 键（最后一段输出里 ``reachability_graph`` 之后紧接着就是 ``root_state_path``\ ）。完整的人读报告还带有通常的结构统计和 ``W_UNREFERENCED_VAR`` 这类无关警告，本页不再重复。

.. _inspect-report-region-order-zh:

顺序诊断
~~~~~~~~~~~~~~~~~

两条顺序诊断都按书写的模型判断，即 ``active()`` 查询降级成隐藏标志变量之前。它们每次只看同一拥有者的各个区域；嵌套在区域里的区域，在轮到它自己的拥有者时才检查，它的访问也计入外层区域。不含区域的模型不会产生它们。

.. list-table:: 顺序诊断
   :header-rows: 1
   :widths: 28 12 60

   * - 诊断码
     - 级别
     - ``refs`` 字段
   * - ``I_REGION_BACKWARD_READ``
     - ``info``
     - ``owner_path``、``reader_region``、``target_kind``\ （\ ``variable`` 或 ``active``\ ）、\ ``target``\ （变量名，或被查询状态的点路径）、\ ``writer_regions``\ （所有写这个变量或包含被查询状态的靠后区域）。
   * - ``W_REGION_BLIND_OVERWRITE``
     - ``warning``
     - ``owner_path``、\ ``region``\ （靠后的、做覆盖的区域）、\ ``previous_region``\ （同样写这个变量的最近的靠前区域）、\ ``variable``、\ ``previous_write_span``\ （被丢掉的那次写入）。

当一个区域读取变量，或用 ``active("...")`` 查询某个状态，而同一拥有者里\ **靠后**\ 的区域写这个变量或包含这个状态时，报告 ``I_REGION_BACKWARD_READ``\ 。靠前的区域先运行，所以读到的是上一周期的值。它是提示级，因为这正是有序区域的既定行为；消息只是让作者确认顺序符合本意。读取发生在同一动作链里对同一变量的写入之后（区域读的是自己刚写的值）、写入者是\ **靠前**\ 的区域（正向读取），或者没有靠后区域写这个变量时，不报告。

``W_REGION_BLIND_OVERWRITE`` 只在靠前的写入每个周期都必然丢失时才报告，下列条件必须全部成立：

* 靠后区域的每个非伪状态叶子，都在 ``during`` 动作的最外层，或在该区域自己声明的 ``>> during before`` 动作的最外层，无条件地写这个变量；
* 靠后区域里没有任何地方在这次写入之前读它：没有条件、效果、\ ``enter``、\ ``exit``、右侧表达式、\ ``if`` 条件或更早的语句，也没有不写它的状态；
* 靠后区域不可能完成（没有 ``[*]`` 出口），不含嵌套的区域拥有者，也没有可供处理器读取该变量的抽象动作或 ``ref`` 动作；
* 靠前那次写入之后、同一周期内执行的东西都没有读这个变量，两者之间的区域没有读它也没有抽象动作，靠前的区域没有抽象动作。

声明在拥有者或更外层的切面，每周期只在整组区域外围执行一次，既不用到旧值，也不保护旧值，因此被忽略。诊断指向做覆盖的语句，\ ``previous_write_span`` 指出被丢掉的写入。

下面的循环把 ``I_REGION_BACKWARD_READ`` 的六个模型与 ``W_REGION_BLIND_OVERWRITE`` 的八个模型的 JSON 检查报告写进文件，脚本读取它们并输出每个模型触发了这两条诊断码中的哪几条；空列表表示两条都没有触发。\ ``region_overwrite_middle_reads.fcstm`` 属于第二组，却触发了第一条诊断码，原因见后面的表格。

.. code-block:: console

   $ for m in region_backward_read_*.fcstm region_overwrite_*.fcstm; do pyfcstm inspect -i $m --format json -o $m.json; done

.. testcode::

   import json
   from pathlib import Path

   wanted = {"I_REGION_BACKWARD_READ", "W_REGION_BLIND_OVERWRITE"}
   for pattern in ("region_backward_read_*.fcstm.json", "region_overwrite_*.fcstm.json"):
       for path in sorted(Path(".").glob(pattern)):
           report = json.load(open(path))
           codes = {item["code"] for item in report["diagnostics"]}
           print(path.stem, sorted(codes & wanted))

.. testoutput::

   region_backward_read_active.fcstm ['I_REGION_BACKWARD_READ']
   region_backward_read_forward.fcstm []
   region_backward_read_no_writer.fcstm []
   region_backward_read_own_write.fcstm []
   region_backward_read_two_writers.fcstm ['I_REGION_BACKWARD_READ']
   region_backward_read_variable.fcstm ['I_REGION_BACKWARD_READ']
   region_overwrite_aspect.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_basic.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_can_finish.fcstm []
   region_overwrite_conditional.fcstm []
   region_overwrite_middle_reads.fcstm ['I_REGION_BACKWARD_READ']
   region_overwrite_skip_middle.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_some_states.fcstm []
   region_overwrite_uses_old.fcstm []

一条发现的信息，在人读报告里是这样打印的：

.. code-block:: console

   $ pyfcstm inspect -i region_backward_read_two_writers.fcstm --color never
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Root.Reader' reads variable 'level', which is produced by the later region 'Root.First', 'Root.Second'; it sees the value from the previous cycle.
   ...

.. list-table:: 各模型为什么报告或保持安静
   :header-rows: 1
   :widths: 38 14 48

   * - 模型文件
     - 是否报告
     - 原因
   * - ``region_backward_read_variable.fcstm``
     - 是
     - 先声明的 ``Reader`` 在 ``seen = level;`` 里读 ``level``\ ，\ ``Writer`` 写它。
   * - ``region_backward_read_active.fcstm``
     - 是
     - ``active("Root.Writer.Busy")`` 查询靠后区域的状态：\ ``target_kind`` 为 ``active``\ 。
   * - ``region_backward_read_two_writers.fcstm``
     - 是
     - 两个靠后区域都写 ``level``\ ，\ ``writer_regions`` 列出两个（消息把它们连在同一个分句里）。
   * - ``region_backward_read_own_write.fcstm``
     - 否
     - ``level = 5; seen = level;`` 读的是区域自己刚写的值。
   * - ``region_backward_read_forward.fcstm``
     - 否
     - 写入者先声明，读取者看到的是本周期的值。
   * - ``region_backward_read_no_writer.fcstm``
     - 否
     - 靠后的区域里没有任何东西写 ``level``\ 。
   * - ``region_overwrite_basic.fcstm``
     - 是
     - ``Second`` 只有一个叶子，在 ``during`` 最外层写 ``out = y + 2;``\ ，而且不可能完成。
   * - ``region_overwrite_aspect.fcstm``
     - 是
     - 覆盖写在区域级的 ``>> during before`` 动作里，它先于每个 ``during`` 执行。
   * - ``region_overwrite_skip_middle.fcstm``
     - 是
     - ``Middle`` 既不读也不写 ``out``\ ，\ ``previous_region`` 是 ``Root.First``\ 。
   * - ``region_overwrite_uses_old.fcstm``
     - 否
     - ``out = out + y + 2;`` 用到了旧值。
   * - ``region_overwrite_conditional.fcstm``
     - 否
     - 写入在 ``if [y > 0] { ... }`` 里面。
   * - ``region_overwrite_some_states.fcstm``
     - 否
     - ``B2`` 不写 ``out``\ ，区域停在那里时前面的默认值保留。
   * - ``region_overwrite_can_finish.fcstm``
     - 否
     - ``B -> [*]`` 让区域可以完成，而已完成的区域不再写入。
   * - ``region_overwrite_middle_reads.fcstm``
     - 覆盖诊断为否
     - ``Middle`` 在两次写入之间读了 ``out``\ ，所以第一次写入被用到。\ ``Middle`` 读取 ``Last`` 写的值，本身会被报告为 ``I_REGION_BACKWARD_READ``\ 。

.. _inspect-report-region-reachability-zh:

分支规则与可达性
~~~~~~~~~~~~~~~~~

报告的可达性和 ``pyfcstm.verify`` 的结构算法把复合状态理解为\ *分支*\ ：拥有区域的状态每个区域一条分支，普通复合状态是只有一条分支的情形，不含复合状态的模型没有分支。规则如下：

.. list-table:: 分支规则
   :header-rows: 1
   :widths: 30 70

   * - 构造
     - 规则
   * - 进入拥有区域的状态
     - 到达每个区域的初始目标。
   * - 离开复合状态的普通转换（\ ``Job -> Next``\ ）
     - 只有状态的某个子状态能到达 ``[*]`` 时才算可达（拥有者则要每个区域都能）。否则由 ``W_UNREACHABLE_TRANSITION`` 以原因 ``owner_never_completes`` 报告，它的目标由 ``W_UNREACHABLE_STATE`` 报告。
   * - 强制转换（\ ``!Group -> Next :: Stop``\ ）
     - 从状态的每个叶子离开，因此随状态可达。它的展开在状态以下加出的退出，不算子状态自行离开。
   * - 历史默认目标（\ ``[H] -> Child``\ ，经 ``Owner.[H]`` 进入）
     - 与初始转换一样，是一条分支的起点。

下面的循环把每个模型的 JSON 检查报告写进文件，脚本对成对的模型输出不可达的发现，每条发现给出诊断码和所在行。这些发现来自默认的静态报告，不需要 ``--enable-verify``\ 。

.. literalinclude:: region_owner_never_completes.fcstm
   :language: fcstm
   :caption: region_owner_never_completes.fcstm

.. code-block:: console

   $ for m in region_owner_*.fcstm region_branch_*.fcstm region_over_history_initial.fcstm; do pyfcstm inspect -i $m --format json -o $m.json; done

.. testcode::

   import json
   from pathlib import Path

   patterns = ("region_owner_*.fcstm.json", "region_branch_*.fcstm.json", "region_over_history_initial.fcstm.json")
   for pattern in patterns:
       for path in sorted(Path(".").glob(pattern)):
           report = json.load(open(path))
           found = []
           for item in report["diagnostics"]:
               if item["code"].startswith("W_UNREACHABLE"):
                   found.append((item["code"], item["span"]["line"]))
           print(path.stem, found)

.. testoutput::

   region_owner_completes.fcstm []
   region_owner_never_completes.fcstm [('W_UNREACHABLE_STATE', 15), ('W_UNREACHABLE_TRANSITION', 17)]
   region_branch_forced.fcstm []
   region_branch_history.fcstm []
   region_branch_plain_exits.fcstm []
   region_branch_plain_stuck.fcstm [('W_UNREACHABLE_STATE', 9), ('W_UNREACHABLE_TRANSITION', 11)]
   region_over_history_initial.fcstm []

人读报告给出了第一个模型的原因：

.. code-block:: console

   $ pyfcstm inspect -i region_owner_never_completes.fcstm --color never
   ...
   [WARN] W_UNREACHABLE_STATE
     State 'Root.Next' is unreachable from the root entry path.
   ...
   [WARN] W_UNREACHABLE_TRANSITION
     Authored transition 'Root.Job' -> 'Root.Next' is unreachable for reasons: owner_never_completes.
   ...

在 ``region_owner_never_completes.fcstm`` 里，\ ``Monitor`` 区域没有 ``[*]`` 出口，所以 ``Job -> Next`` 永远不会执行：\ ``Root.Next`` 不可达，转换得到 ``owner_never_completes``\ 。给 ``Monitor`` 加上出口（\ ``region_owner_completes.fcstm``\ ）后，两条发现都消失。

**不含区域的模型上唯一有意的输出变化。**\ 子状态都无法离开的普通复合状态，永远不会执行它的普通外出转换。\ ``region_branch_plain_stuck.fcstm`` 展示了这一点：\ ``Group -> Next`` 得到 ``owner_never_completes``\ ，\ ``Root.Next`` 不可达，而此前的报告把这个复合状态当作机器可以随意离开的东西。仿真器本来就是这样运行的。\ ``region_branch_plain_exits.fcstm``\ （\ ``B -> [*]``\ ）、\ ``region_branch_forced.fcstm``\ （强制转换）和 ``region_branch_history.fcstm``\ （强制转换加 ``[H]`` 默认目标）什么都不输出。

已知的过近似
~~~~~~~~~~~~~~~~~

结构分析里保留了三处近似，方向都是\ *漏报*\ ，所以报告为空并不证明可达。

#. 只经 ``Owner.[H]`` 进入的复合状态，它的普通初始子状态仍被视为可达。在 ``region_over_history_initial.fcstm`` 里，\ ``Work`` 只经 ``Work.[H]`` 进入，默认目标是 ``Slow``\ ；\ ``Fast`` 永远进不去，而上面的脚本没有为它输出任何发现。
#. ``pyfcstm.verify`` 的算法判断的是可执行的机器，其中强制转换声明是一个中继，并且对它保持不看守卫的过近似。一个只有强制转换声明能把它带去别处的复合状态，其后的状态仍可能被列为可达。
#. 单个强制转换声明，只要有一个展开从不可达状态出发，就整体被标记。这是早于区域的有意聚合。

带 ``--enable-verify`` 时，拓扑算法（\ ``topological_reachable_set``、\ ``unreachable_states``、\ ``strongly_connected_components``、\ ``topological_finite``、\ ``topological_inevitable_terminator`` 和 ``event_emission_to_consumer_reachable``\ ）对含区域的模型与对其他模型一样运行。没有任何可达位置包含的状态是不可达的；围绕某个叶子的分支不能全部结束时，这个叶子没有出路（报告里称为死锁）；可达位置里存在可以重复或者动不了的位置时，拓扑是非终止的。求解器局部算法会在区域内运行，区域内状态的生命周期检查则被跳过。

jsfcstm 的边界
~~~~~~~~~~~~~~~~~

jsfcstm 的结构检查器不为含区域的模型产生报告。对声明了区域或使用 ``active()`` 查询的机器，\ ``isInspectable(machine)`` 返回 ``false``\ ，\ ``inspectModel`` 抛出 ``Error``\ （\ ``inspectModel does not support machines with regions or active() queries``\ ），而不是返回报告。jsfcstm 的语义分析仍会检查这样的模型；上面的可达性规则，包括不含区域的模型上的 ``owner_never_completes``\ ，在 jsfcstm 里同样实现。要得到顺序诊断和 ``regions`` 数组，使用 ``pyfcstm inspect``\ 。

发现按哪台机器判断
----------------------------------------

报告本身，以及所有描述“写成了什么”的发现，都按书写的模型判断：状态、转换、历史入口、强制转换声明和 ``active()`` 查询都保持它们在文本里的样子。验证流水线的发现说的是机器怎样运行，所以按可执行的机器判断。历史、``active()`` 和强制转换声明会降级成带隐藏变量、中继转换和门状态的普通 FCSTM，而模型导出的文本就是这份普通 FCSTM，因此模型和它导出的文本给出相同的验证发现。\ ``active("...")`` 上的条件，与隐藏标志变量上没有任何约束的普通条件一样判断。

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 判断的对象
     - 诊断码
   * - 可执行的机器
     - ``I_NONTRIVIAL_SCC``、``W_TOPOLOGICAL_NOEXIT``、``I_TOPOLOGICAL_NON_TERMINATING``、``W_EVENT_UNREACHABLE_EMIT``、``W_DEAD_GUARD``、``W_GUARD_TAUTOLOGY``、``W_EFFECT_SMT_NO_OP``、``I_EFFECT_GUARD_CONTRADICT``、``W_TRANSITION_SHADOWED``、``I_ENTER_DURING_CONTRADICT``、``W_COMPOSITE_INIT_INCOMPLETE``
   * - 书写的模型
     - 其余所有诊断码，包括 ``W_FORCED_GUARD_UNSAT``\ ：它判断的是强制转换声明，而可执行的机器已经不再携带声明

可执行的机器里有降级的产物，所以一条发现可能提到 ``__forced_0``、``__hist_goto`` 这样的隐藏变量、生成的门状态，或者文本从未写过的转换；写得完全正确的模型也可能因此得到发现：中继转换把自己守卫读取的隐藏变量降下来，会被报告为 ``I_EFFECT_GUARD_CONTRADICT``\ 。这样的发现指向它所降级自的那处构造。不带 ``--enable-verify`` 时，没有任何东西按可执行的机器判断。组合触发是另一种情形：它的中继守卫生成的发现，只会以触发项的身份，由该项对应的 ``W_COMBO_*`` 诊断码报告一次。

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
分母为空时返回 ``null``\ （human/Markdown 显示 ``N/A``）。调用方可以向
``inspect_model`` 传入 ``StructureStatisticsPolicy``\ （或部分映射），单项传
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

变量角色与访问位置
------------------

``VariableInfo`` 保留既有读写汇总字段，并增加 ``external_supply``、
``diagnostic_policy``、``read_sites`` 和 ``write_sites``。
这些字段描述展开后的模型，不是执行轨迹。

.. list-table:: 所有权与诊断适用范围
   :header-rows: 1
   :widths: 22 23 55

   * - ``role``
     - ``external_supply``
     - ``diagnostic_policy``
   * - ``control``，包括旧写法 ``def``
     - ``none``
     - ``unused``、``unwritten``、``write_only``、``constant_guard`` 均为 true。
   * - ``input``
     - ``cycle``
     - 四项均为 false；由环境逐拍提供。
   * - ``param``
     - ``construction``
     - 四项均为 false；构造时确定，此后固定。
   * - ``output``
     - ``none``
     - 四项均为 false；外部消费者不必通过模型内部读取输出。

策略标志说明既有 control 变量未使用、未写入但被读取、只写，以及 guard
变量不变诊断的适用范围。它们不是可配置的屏蔽开关，也不关闭其他校验或常量
表达式分析。写入 ``input`` 或 ``param`` 仍然是模型错误；``output`` 仍允许多个写入者。

每个访问位置包含以下字段：

.. list-table:: VariableAccessSite
   :header-rows: 1
   :widths: 25 75

   * - 字段
     - 含义
   * - ``kind``
     - ``action``、``guard`` 或 ``effect``；action/effect 内部的条件沿用其容器类别。
   * - ``state_path``
     - 展开后的所属状态路径，包含 import 实例位置。
   * - ``action`` / ``action_index``
     - 动作签名及其在 ``actions`` 中的零基索引；transition 访问两者均为 null。inline 签名可能重复，索引用于区分。
   * - ``transition_index``
     - guard/effect 在 ``transitions`` 中对应的零基索引；action 为 null。
   * - ``statement_path``
     - 容器内部的零基语句、分支索引。``[0]`` 是首条语句；``[0, 0]`` 是该条件语句的首个分支条件；``[0, 0, 1]`` 是该分支内第二条语句。transition guard 使用 ``[]``。
   * - ``source_path``
     - 实际书写的源文件，与展开状态路径不同；无法取得时为 null。
   * - ``span``
     - 语句、分支块或 transition 的源码范围，沿用从 1 开始、末端不包含的 ``Span`` 约定；无法取得时为 null。它不是变量 token 的精确范围。

同一个表达式内重复出现的变量只产生一个读取位置；不同语句、分支和导入实例
分别保留。赋值若读取自身，则同时产生读取与写入位置。initializer 属于声明
元数据，不算 action/effect 写入。不可达语句仍然记录；抽象动作不虚构访问。
动作引用通过既有 ``action_ref_graph`` 表达，具体函数体在其定义处记录访问。
访问数组按模型遍历顺序排列，每个状态先动作后 transition，嵌套语句遵循源码
顺序。索引只在本份报告内有效，不是跨编辑稳定标识。

human 报告列出变量角色和外部供给方式。LLM 修复报告加入所有权说明，避免把
``input``/``param`` 没有模型写入、``output`` 没有内部读取误当成需要修复的问题。
完整结构化访问位置保留在 full JSON 报告中。公共 payload 不加入 schema 或
产品版本标记，消费者应使用运行版本随包发布的 schema 校验。
