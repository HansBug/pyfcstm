解释某条迁移为何未被选择
========================

当提交执行迹（committed trace）只显示最终路径、没有被拒候选时，使用候选决策诊断（candidate diagnostics）。需要当前 pyfcstm 支持 ``cycle(diagnostics=True)`` 和 ``simulate --diagnostics``。普通首次运行流程仍见 :doc:`../../tutorials/simulation/index_zh`；精确字段与命令边界见 :doc:`../../reference/simulation/diagnostics_zh`。下文的守卫条件（guard）指迁移上的布尔条件。

采集后继拒绝证据
----------------

从仓库根目录运行，或下载 :download:`candidate_failure.fcstm` 后调整路径。模型先尝试 ``A -> Blocked``，再尝试 ``A -> B``。进入 ``Blocked`` 会设置 ``x=100``，但其初始迁移要求 ``x < 0``。

.. literalinclude:: candidate_failure.fcstm
   :language: fcstm

.. code-block:: bash

   pyfcstm simulate -i docs/source/how_to/simulation/candidate_failure.fcstm \
     --diagnostics --no-color -e 'cycle; cycle Root.A.Go; why Root.A::0::A->Blocked --verbose'

第二次调用停在 ``Root.B``，最终 ``x=1``。报告中第一个候选为 ``successor_rejected``，其后继守卫检查记录 ``x=100``。``why`` 只展示证据，不执行新周期，不写文件。若显示 ``No diagnostic report``，应先开启采集再重现调用；事后打开开关无法恢复过去的证据。

等价 Python 程序可以直接从仓库执行：

.. code-block:: bash

   python docs/source/how_to/simulation/candidate_diagnostics.demo.py

.. literalinclude:: candidate_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

完整的简洁报告如下：

.. literalinclude:: candidate_diagnostics.demo.py.txt
   :language: text

按下面的顺序理解证据：

.. list-table:: 此报告能够证明什么
   :header-rows: 1

   * - 观察
     - 含义
   * - ``A -> Blocked`` 为 ``successor_rejected``
     - 事件匹配还不够，其后续路径无法到达稳定边界。
   * - 初始守卫看到 ``x=100``
     - 这是推测进入产生的临时值，不是最终提交值。
   * - 预检中 ``A -> B`` 为 ``selected``
     - 整拍检查找到可行选择，但此时尚未提交。
   * - 执行中 ``A -> B`` 标明 ``committed``
     - 这次实际选择最终随整拍提交，同一迁移也出现在提交执行迹中。
   * - 相邻且相同的检查被折叠
     - 仅相同的未提交证据可以折叠，编号与次数仍然可见。用 ``report.to_text(verbose=True)`` 或 ``decisions --verbose`` 查看每次检查及其父检查关系。

某个搜索分支的守卫为假，不证明整个候选失败；应结合外层 ``successor_result`` 和子检查证据判断。带 ``blocked_by`` 的 ``not_evaluated`` 表示前序已被选中，不表示后序守卫为假。普通叶状态可以原地保持而不产生 Delta。因此报告记录真实检查，不用拍末变量重新求值猜测。

排查组合迁移回滚与回退路径
--------------------------

将 :download:`combo_diagnostics.fcstm` 和 :download:`combo_diagnostics.demo.py` 下载到同一目录，或在仓库根目录执行已有程序：

.. code-block:: bash

   python docs/source/how_to/simulation/combo_diagnostics.demo.py

.. literalinclude:: combo_diagnostics.fcstm
   :language: fcstm

程序为三种情形分别构造新实例。``A + B`` 的各项都在同一个宏步骤内检查，使用该次调用冻结的输入；不是第一拍 A、第二拍 B。

.. literalinclude:: combo_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

.. list-table:: 预期提交边界
   :header-rows: 1

   * - 输入与事件
     - 证据
     - 最终边界
   * - ``sensor=12``，只有 A
     - 缺少 B，目标初始守卫未检查。
     - ``Root.Fallback``；``score=121``、``reading=0``。
   * - ``sensor=3``，A、B 都有
     - 目标初始守卫失败，推测快照为 ``score=10011``、``reading=3``。
     - ``Root.Fallback``；``score=121``、``reading=0``。
   * - ``sensor=12``，A、B 都有
     - 整条路径成功，回退候选未检查。
     - ``Root.Target.Good``；``score=11011``、``reading=12``。

下面是第二种情形的真实输出节选；这里省略其他两种情形，它们由同一个程序完整打印：

.. literalinclude:: combo_diagnostics.demo.py.txt
   :language: text
   :start-after: === target guard false ===
   :end-before: === complete path ===

被拒路径计算了源状态退出动作的 ``+1``、末端迁移动作的 ``+10`` 和 ``reading=sensor``，再计算目标进入动作的 ``+10000``，所以初始守卫看到 10011 和 3。这是推测检查时的值。回退路径从原边界出发，提交自己的 ``+1+20+100``，得到 121。报告自身的 ``vars_before`` 和 ``vars_after`` 就能区分最终值与失败检查快照，无需额外读取运行时。

这里没有逐动作撤销日志。``successor_rejected`` 与子检查证据解释被拒路径，已提交微迁移清单和边界值说明哪些结果保留下来；这不承诺撤销外部回调的任意副作用。候选回滚不一定形成 Delta，本例正常提交回退路径。

默认组合迁移展示原始来源、目标和规范触发串。这是可读语义标签，不是替代 DSL。详细文本与 ``transition_label`` 保留展开地址。共享前缀会明确列出多个来源；共享微迁移提交，不代表它对应的全部原始候选都提交，还需查看末端路径与最终边界。

程序不写文件。若最终目标与预期不同，先检查是否在同一次调用中传入两个完整事件路径，以及冻结输入是否满足目标守卫。使用 ``report.to_text(check_id=3, verbose=True)`` 或命令行 ``why 3 --verbose`` 可以连同祖先一起查询失败检查；编号仅在当前报告有效。选择器与字段契约见 :doc:`../../reference/simulation/diagnostics_zh`。

区分 Delta 与普通原地周期
-------------------------

将 :download:`delta_diagnostics.fcstm` 与 :download:`delta_diagnostics.demo.py` 下载到同一目录，或执行：

.. code-block:: bash

   python docs/source/how_to/simulation/delta_diagnostics.demo.py

.. literalinclude:: delta_diagnostics.fcstm
   :language: fcstm

.. literalinclude:: delta_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

第一拍冻结输入为 3。初始路径计算出 ``score=110``、``reading=3``，但无法从伪状态到达可停止状态，因此返回 Delta，保留原根状态边界和为零的持久变量，提交执行迹为空。第二拍输入为 12，初始化成功，得到 ``score=1110``、``reading=12``；第一拍推测得到的 110 没有累加进来。

.. literalinclude:: delta_diagnostics.demo.py.txt
   :language: text

标准错误还会记录一条 Delta 警告，程序不写文件。Delta 推进周期计数、历史和输入源，不会倒退环境时间。若第二拍仍然失败，检查输入序列与守卫值，不要假设继续使用第一拍样本。普通可停止叶状态可以原地执行 ``during`` 并改变输出，同时 ``decisions`` 为空；这仍是普通周期，报告也会保留输入、参数与前后边界快照。忽略调用则以 ``inputs=None`` 明确表示没有重新采样。

同一伪状态边在一个宏步骤内多次执行时，即使标签相同，每次提交仍然独立展示。紧凑文本仅折叠相邻且除编号外证据完全相同的未提交检查，保留全部编号与次数；变量值或验证父检查不同就是不同事实。详细文本和 JSON 始终保留全部原始检查。与完整路径守卫约束的关系见 :ref:`exec-diagnostic-boundaries-zh`。

提供输入和参数
--------------

将以下独立模型保存为 ``controller.fcstm``：

.. code-block:: fcstm

   input int sensor;
   param int gain = 2;
   output int reading = 0;
   state Controller {
       state Running { during { reading = sensor * gain; } }
       state High;
       [*] -> Running;
       Running -> High : if [sensor > 10];
   }

.. code-block:: bash

   pyfcstm simulate -i controller.fcstm --param gain=3 --diagnostics --no-color \
     -e 'cycle --input sensor=4; cycle --input sensor=12; decisions'

第一拍设置 ``reading=12``。下一次调用选择 ``Running -> High``，检查快照包含 ``sensor=12`` 和 ``gain=3``；锁存输出仍为 12。没有文件副作用。每个实际周期都要提供输入；不带 ``--input sensor=...`` 的 ``cycle`` 会以 ``E_INPUT_SOURCE_CONTRACT`` 失败，应补齐向量，不应期待沿用前值。``cycle 5 --input sensor=4`` 明确表示五拍重复该向量。参数只能在构造时设置，不能通过 ``init`` 或 ``cycle`` 改变。

自定义生成器和传感器回调继续使用现有 Python :doc:`输入源 <../../reference/simulation/inputs_zh>`。诊断读取本拍冻结向量，不重复采样。子输入导入映射到父 control/output 后，按最终父角色报告。

采集机器可读报告
----------------

此处区分标准输出（stdout）、标准错误（stderr）和退出状态（exit status）。

.. code-block:: bash

   pyfcstm simulate -i docs/source/how_to/simulation/candidate_failure.fcstm \
     --diagnostics --diagnostics-format jsonl --no-color \
     -e 'cycle; cycle Root.A.Go' > decisions.jsonl
   python -c 'import json; rows=[json.loads(s) for s in open("decisions.jsonl")]; assert len(rows)==2; assert rows[1]["state_after"]==["Root","B"]; print("2 valid reports")'

第二条命令应输出 ``2 valid reports``。shell 创建或覆盖 ``decisions.jsonl``，内容不含命令标题或 ANSI 转义；人类转录和日志写入标准错误。每条报告与 Python 的 ``to_dict()`` 使用同一份数据。拒绝候选仍属于正常成功运行；后续非法命令使批次非零退出，已经输出的完整记录仍保留。

若 JSON 解析失败，先检查是否同时传入 ``--diagnostics`` 与 ``--diagnostics-format jsonl``，并避免把标准错误并入文件。JSONL 只用于批处理；交互查询输出人类文本。这里不新增自动场景加载、持久化或重放体系；跨运行比较时，由实验脚本保存模型及运行条件。

在交互命令行（REPL）中，``setting diagnostics on``、``cycle``、``decisions`` 和 ``why <id|label>`` 提供相同流程，Tab 可以补全已捕获的检查编号和标签。只保留最近调用；新调用失败、``init`` 或 ``clear`` 都会清除旧报告，避免把旧解释误认成新状态的证据。
