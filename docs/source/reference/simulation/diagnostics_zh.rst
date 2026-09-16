候选决策诊断参考
================

本页定义一次仿真器调用捕获的证据。候选迁移（candidate transition）、守卫条件（guard）、预检（preflight）和提交（commit）分别表示待选边、边的布尔条件、正式执行前的检查和最终保留执行结果。可运行的排查步骤见 :doc:`../../how_to/simulation/diagnostics_zh`；执行顺序见 :doc:`../../explanations/execution_semantics/index_zh`；输入源契约见 :doc:`inputs_zh`。

采集与查询
----------

.. list-table:: Python 接口
   :header-rows: 1

   * - 接口
     - 默认值与契约
   * - ``runtime.cycle(events=None, *, trace=False, inputs=None, diagnostics=False)``
     - ``diagnostics`` 是独立的布尔开关，默认关闭。原有事件、输入、提交和异常规则不变，不写文件。
   * - ``result.diagnostics``
     - 关闭时为 ``None``；开启时返回不可变的 ``CycleDiagnostics``，包括没有候选、Delta 和忽略调用的情况。抛出异常时不返回部分报告。
   * - ``report.decisions``
     - 按观察顺序排列的 ``TransitionDecision`` 元组。使用普通 Python 迭代和筛选；每条检查拥有独立快照。
   * - ``str(report)``
     - 纯文本摘要。迁移标签、阶段、结果及提交状态相同的摘要会折叠，并说明省略数量；它不是机器协议。
   * - ``report.to_text(transition=None, verbose=False)``
     - 可用精确迁移标签筛选，包含对应的后继检查。详细模式展开全部检查、父检查关系、完整变量集合和已有源码位置。未知标签显示 ``No recorded evidence``，不推断源状态未激活。
   * - ``report.to_dict()``
     - 返回完整且独立的字典，元组转换为列表，只读映射转换为字典。修改结果不影响原报告。需要序列化时调用 ``json.dumps``，不添加版本或模式分派标记。

报告由调用者持有，独立于运行时历史保留策略。格式化和查询不求值守卫条件、不采样输入、不调用处理器、不推进周期。快照内存与检查次数及变量向量大小成正比；运行时不额外保存无限历史。

人类文本沿用现有的大整数位数表示，例如 ``int<5001 digits>``。结构化值仍是精确整数。序列化异常大的整数时，标准 Python JSON 转换限制仍然适用；库不会修改进程级解释器限制。

报告字段
--------

以下字段均进入 ``to_dict()``。可选值缺失时在 Python 中为 ``None``，在 JSON 中为 ``null``。

.. list-table:: ``CycleDiagnostics``
   :header-rows: 1

   * - 字段
     - 类型
     - 含义
   * - ``cycle_count``
     - 整数
     - 调用后的运行时周期计数；被忽略的调用不增加计数。
   * - ``outcome``
     - 字符串
     - ``cycle``：普通提交周期；``delta``：成功但无进展的一拍；``terminated``：本次调用使模型终止；``noop``：已终止或处于错误状态的运行时忽略本次调用。
   * - ``state_before`` / ``state_after``
     - 路径元组或 ``None``；JSON 列表或 ``null``
     - 调用边界上的活动栈顶路径。``None`` 表示终止；冷启动初始化前仍记录根状态路径。
   * - ``decisions``
     - 检查元组；JSON 数组
     - 实际检查及选择造成的明确短路记录。为空不代表 Delta 或错误。
   * - ``roles``
     - 名称到字符串的映射
     - 组装后的最终角色：``control``、``output``、``input``、``param``；导入变量采用父模型最终绑定。

.. list-table:: ``TransitionDecision``
   :header-rows: 1

   * - 字段
     - 类型
     - 含义
   * - ``id`` / ``parent_id``
     - 正整数 / 可选整数
     - 当前报告内唯一检查编号，以及正在验证其后继的外层候选编号。编号不承诺跨编辑或跨运行稳定。同级记录可能是搜索的不同分支，不代表顺序执行路径。
   * - ``transition_label``
     - 字符串
     - 沿用执行迹和 BMC 的 ``source_path::index::source->target`` 地址。强制迁移、组合触发采用展开后边的地址；合成根退出边下标为零。修改模型或调整声明顺序可能改变标签。
   * - ``phase``
     - 字符串
     - ``preflight``：整拍预检；``execution``：实际选择阶段；``validation``：嵌套后继检查或搜索。只有 ``committed`` 能证明最终执行。
   * - ``state_path``
     - 路径元组；JSON 列表
     - 本次检查的源状态；初始迁移记录所属复合状态。
   * - ``event`` / ``guard``
     - 可选字符串
     - 要求的规范事件路径／守卫表达式。``None`` 表示没有这个条件，不表示条件为假。
   * - ``event_result`` / ``guard_result``
     - 可选布尔值
     - 实际检查结果；``None`` 表示未评估。检查到不存在的条件时以 ``True`` 通过。缺少事件会短路守卫求值。
   * - ``successor_result``
     - 可选布尔值
     - 整体后继验证结果，未要求验证时为 ``None``。某一搜索分支失败，不会在另一延续成功时把该字段变成假。
   * - ``outcome``
     - 字符串
     - ``event_missing``、``guard_false``、``successor_rejected``、``selected``、``enabled`` 或 ``not_evaluated``。``enabled`` 仅说明搜索候选通过条件；``selected`` 表示在其标明的阶段被选中。
   * - ``blocked_by``
     - 可选检查编号
     - 导致当前候选未评估的前序成功选择。前序守卫为真但后继验证失败，不会压制后续候选。
   * - ``committed``
     - 布尔值
     - 仅当实际执行阶段的这次选择最终随整拍提交时为真。Delta 和推测检查始终为假。
   * - ``vars`` / ``inputs`` / ``parameters``
     - 数值映射
     - 本次检查时的持久 control/output 快照、本拍冻结输入以及固定参数。用 ``roles`` 区分 control 和 output；动作局部临时值不是模型变量。
   * - ``location``
     - 映射
     - 已有的 ``line``、``column``、``end_line``、``end_column`` 和 ``path``。坐标从 1 开始，结束列为开区间。合成边或程序构造的边可能为空；不经文件加载器解析时可能缺少 ``path``。
   * - ``to_dict()``
     - 方法
     - 按相同字段含义返回单条检查的独立字典。

报告解释机械选择，不回答反事实可达性或任意外部处理器行为。验证不会执行抽象处理器；边满足条件不代表外部代码必定成功。没有证据不代表守卫为假、源状态从未激活或者模型全局不可达。``trace`` 继续只保存已提交观察。

命令行契约
----------

本节区分标准输出（stdout）、标准错误（stderr）和退出状态（exit status）。交互命令行（REPL）与批处理共用命令处理器。

.. list-table:: 选项与命令
   :header-rows: 1

   * - 形式
     - 默认值／合法值
     - 行为和非法情况
   * - ``--diagnostics``
     - 关闭
     - 开启周期候选采集与人类摘要；交互等价形式为 ``setting diagnostics on``。
   * - ``--diagnostics-format text|jsonl``
     - ``text``
     - JSONL 同时要求 ``--diagnostics`` 和批处理 ``-e``。其他值、缺少前提或在 JSONL 批次中关闭诊断均失败。
   * - ``--param NAME=VALUE``
     - 声明默认值；可重复
     - 构造时一次设置参数。未知名称、非参数名称、重复名称或数值类型不匹配均失败。整数参数可用 ``--param gain=3``，不能用 ``--param gain=3.5``。
   * - ``cycle [count] [events...] [--input NAME=VALUE ...]``
     - 次数为 1；输入赋值可重复
     - 每个实际周期要求完整输入向量，不补零、不隐式保持。``cycle 5 --input sensor=3`` 明确表示五拍重复该向量。未知、缺失、重复名称和类型错误均失败。已终止或处于错误状态时不要求新样本。
   * - ``decisions [--verbose]``
     - 最近一次调用
     - 读取最近报告；没有报告时显示 ``No diagnostic report``，不会重放。
   * - ``why <transition-label> [--verbose]``
     - 从摘要或补全取得精确标签
     - 读取该边及其后继检查。缺标签、多余参数、重复 ``--verbose`` 均失败；语法合法但没有记录的标签得到无证据提示。

数值赋值支持十进制、十六进制、二进制和浮点表示，但仍须满足模型类型。``init`` 和 ``clear`` 保留参数、重建命令拥有的输入适配器并清除报告，不允许后续重设参数。外部 Python 输入源仍由其拥有者在重启时构造新运行时。调用失败、尝试初始化或下一拍关闭采集，都会清除旧证据。交互环境只保存最近调用；多周期命令展示各次报告，结束后只能查询最后一次。

文本模式将命令转录写入标准输出，日志写入标准错误。JSONL 模式只把每次正常返回的周期报告写入标准输出；命令标题、表格、查询和日志写入标准错误。报告不含 ANSI 转义；默认颜色设置和 ``--no-color`` 下诊断文本均为纯文本。文件由 shell 重定向产生；此功能不保存场景或重放格式。原有 ``export`` 导出历史，不导出候选报告。

成功批次返回 0，包括候选拒绝和 Delta。非法命令行选项返回 Click 的非零用法状态；解析、构造、命令或运行错误均非零退出，批次在首个失败命令处停止。后续失败不影响先前正常 JSONL 记录的有效性；失败调用不输出成功报告。这改变了以前部分命令错误只打印消息、仍以 0 退出的行为。

拒绝候选、重复检查、缺失输入和 JSONL 验证示例见 :doc:`../../how_to/simulation/diagnostics_zh`。实现依据是 ``pyfcstm/simulate/diagnostics.py``、``runtime.py`` 和 ``pyfcstm/entry/simulate/``；公开案例由 ``test/simulate/test_decision_diagnostics.py`` 与 ``test/entry/test_simulate_diagnostics.py`` 验证。
