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
   * - 重复摘要被折叠
     - 引擎确实多次检查了部分边。用 ``report.to_text(verbose=True)`` 或 ``decisions --verbose`` 查看每次检查及其父检查关系。

某个搜索分支的守卫为假，不证明整个候选失败；应结合外层 ``successor_result`` 和子检查证据判断。带 ``blocked_by`` 的 ``not_evaluated`` 表示前序已被选中，不表示后序守卫为假。普通叶状态可以原地保持而不产生 Delta。因此报告记录真实检查，不用拍末变量重新求值猜测。

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

在交互命令行（REPL）中，``setting diagnostics on``、``cycle``、``decisions`` 和 ``why <label>`` 提供相同流程，Tab 可以补全已捕获标签。只保留最近调用；新调用失败、``init`` 或 ``clear`` 都会清除旧报告，避免把旧解释误认成新状态的证据。
