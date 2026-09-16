## 当前范围

本计划对应[周期观测伞 PR](https://github.com/HansBug/pyfcstm/pull/486)及[飞书基础设施路线](https://scngnprmusv9.feishu.cn/wiki/ZyBpw6NFyihccAkKHj2c8733niS)。实验材料、原始结果及复现登记保存在飞书附件；实验采集需求不自动转化为公共保存框架。

| 项目 | 状态 | 当前边界 |
|---|---|---|
| 2.1 提交执行迹 | 已合入 main | [执行迹 PR](https://github.com/HansBug/pyfcstm/pull/484)；后续补齐角色快照。 |
| 2.2 四角色和逐拍输入 | 已合入 main | [角色与输入伞 PR](https://github.com/HansBug/pyfcstm/pull/487)，贯通 simulator、BMC、import 和五模板。 |
| 2.3 实验采集与回放 | 实验已验证 | 仿真脚本保存与重放；BMC 使用原生报告和公开见证回放器。公共保存协议撤出必做范围。 |
| 2.4 宿主观测 | 当前 Python 模板已验证 | 使用现有输入 getter、动作 hook 和公开字段；其他模板及真实外部日志按需求验证。 |
| 2.5 实验结果比较 | 固定字段比较已验证 | 比较首差、字段缺失和截断，不承诺通用等价判定。 |
| 2.6 候选决策诊断 | 开发与验收中 | 真实检查点采集、不可变 Python 报告、文本查询、CLI 与 JSONL。 |

## 候选诊断交付与验收

诊断独立依赖现有运行时，不依赖新增保存或比较协议。`cycle(diagnostics=True)` 捕获实际事件、守卫与后继检查，区分重复验证、选择和提交。提交 trace 保持原义；Delta 保留诊断而不保留提交迹。人类报告和结构化结果共享证据，查询不重新求值、不采样、不调用处理器。

CLI 在 `simulate` 上提供诊断开关、`decisions`、`why`、批处理 JSONL；补齐构造阶段参数和逐拍完整输入入口。JSONL 标准输出不混入人类转录，错误非零退出；初始化、清空和新调用失败均清除旧报告。原有 Python 输入源契约不变，不引入场景格式、五模板诊断、BMC 不可行根因分析或新语法。

验收覆盖候选事件缺失、守卫为假、前序成功压制、前序后继失败而后序成功、多分支搜索、初始化、伪状态／强制／组合链、热启动、import 最终角色、拍内值、Delta／终止／忽略调用及错误清理。通过成对语义 fixture 验证诊断开关不改变执行结果、事件记账、history、采样和处理器次数。新增／改动手写产品代码的单元测试分支覆盖率要求 100%，不新增豁免。

用户文档由 `docs/source/how_to/simulation/diagnostics*.rst` 承担可运行排查流程，由 `docs/source/reference/simulation/diagnostics*.rst` 承担字段、接口、命令和失败边界；原有仿真教程与执行语义解释继续负责首次入门及调度规则。
