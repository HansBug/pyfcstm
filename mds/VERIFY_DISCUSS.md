# pyfcstm verify 可扩展性质讨论

## 1. 现有 verify 的能力边界

从当前实现看，`pyfcstm.verify` 的核心能力并不是完整的时序逻辑模型检验，而是：

- 基于 Z3 的符号执行
- 基于 BFS 的有界状态空间搜索
- 将 guard / event 建模为约束
- 对可达路径给出 concrete witness

当前公开接口主要是：

- `bfs_search`
- `verify_reachability`

对应实现位置：

- `pyfcstm/verify/search.py`
- `pyfcstm/verify/reachability.py`
- `pyfcstm/verify/DESIGN.md`

因此，后续最值得补充的，不是一次性引入完整 CTL/LTL，而是优先增加那些能够直接复用现有“symbolic BFS + Z3 + witness”骨架的控制系统常用性质。


## 2. 最适合由现有 verify 扩出来的性质

### 2.1 安全性 / 禁态不可达

这是最自然的一类。

典型问题：

- 加热开启时，排空阀不能打开
- 正反转输出不能同时为 1
- 进入 Fault 后，危险执行器必须关闭
- 某些状态组合永远不允许同时出现

本质上，这类问题就是：

- 是否存在一条路径到达 `bad state`
- 或者是否存在一条路径使 `bad predicate` 成立

这与当前 `verify_reachability` 的思路高度一致，只需要把目标从“到某个状态”扩展到“到某个坏条件”。


### 2.2 变量范围不变量

控制系统里非常常见。

典型问题：

- `0 <= retry_count <= 3`
- `0 <= duty <= 100`
- `pressure <= max_pressure`
- `temperature >= 0`

这类性质不一定对应某个特定状态，而是要求“所有可达 frame 都满足某个约束”。

在当前实现上，可将其转化为：

- 对每个可达 frame 检查 `frame.constraints && not(invariant(frame.var_state))` 是否可满足

只要能找到反例，就能生成 counterexample witness。


### 2.3 状态相关输出约束

这比单纯的全局变量范围更贴近状态机控制逻辑。

典型问题：

- 在 `Heating` 状态时，`heater_cmd == 1`
- 在 `Fault` 状态时，`motor_enable == 0`
- 在 `DoorOpen` 状态时，`lock_cmd == 0`
- 在 `Completed` 状态时，`busy == 0`

本质上是“状态蕴含变量约束”：

- `in_state(S) => predicate(vars)`

这类性质和控制需求文档很接近，也适合做成 verify API。


### 2.4 死转换 / 不可触发转换

这是工程上非常有价值的一类静态分析。

典型问题：

- 某条 transition 的 guard 永远不成立
- 某个 event transition 在给定初始条件和边界内永远不可能被走到
- 设计者以为保留了 fallback 分支，实际上永远走不到

可验证内容包括：

- 某条 transition 是否存在 witness path 使其被触发
- 某条 transition 是否在当前初值假设下完全 dead

这既能帮助发现 DSL 设计问题，也能帮助清理冗余状态图。


### 2.5 转换遮蔽 / 优先级错误

这一类非常适合你们当前实现，因为当前 BFS 已明确把 transition declaration order 作为语义的一部分处理。

典型问题：

- 后面的 guard 虽然自身可满足，但总会被前面的 guard 抢先吃掉
- fallback transition 放错顺序，导致目标分支永远不可达
- “看起来存在”的故障转移分支，实际上一直被更早的条件覆盖

可以进一步区分两层：

- guard 自身可满足，但 transition 的 `actual_condition` 永远不可满足
- transition 在全局上可达，但覆盖范围与设计意图不一致

这类检查在状态机设计 review 里非常实用。


### 2.6 死锁 / 卡死 / 零周期活锁

对于层次状态机和 pseudo state，这类性质很关键。

建议区分：

- 真死锁：到达某 frame 后，没有任何 satisfiable successor
- 有界卡死：在有限 cycle 内无法继续推进到期望区域
- 零周期活锁：一直在 pseudo / composite boundary 内绕圈，`depth` 增长但 `cycle` 不增长

特别是 pseudo chain 和边界动作组合，如果出现零周期环，用户从图上往往不容易看出来。


### 2.7 有界恢复性

控制系统里很常见，尤其是故障处理。

典型问题：

- 进入 `Fault` 后，是否存在路径在 3 个 cycle 内回到 `Idle`
- 进入 `Error` 后，是否存在路径在 5 个 cycle 内到达 `SafeStop`
- 进入 `Retrying` 后，是否能在给定边界内回到 `Running`

这类性质本质上是：

- 从某个状态或状态条件出发，验证 bounded reachability 到恢复目标

与当前 `verify_reachability` 的骨架非常接近。


### 2.8 有界响应性

比“能否到达”更接近控制需求。

典型问题：

- 检测到低温后，是否能在 2 个 cycle 内进入 `Heating`
- 门关闭命令发出后，是否能在 5 个 cycle 内进入 `Closed` 或 `Fault`
- 启动命令生效后，是否能在 1 个 cycle 内离开 `Idle`

可以看作：

- trigger condition 成立后，是否存在 / 是否必须在给定 cycle 上界内到达 response state

其中“存在”版本可以直接基于现有 verify 做。


### 2.9 顺序约束 / 流程约束

适合工艺流程、任务执行、操作许可链。

典型问题：

- 不允许绕过 `Warmup` 直接进入 `Run`
- 必须先 `Arm` 才能 `Launch`
- `SealVerified` 之前禁止进入 `Fire`

本质上可以转换为：

- 禁止到达“违反先后约束”的坏状态
- 或检查“目标状态可达时，路径上必须经过某些状态”

前者更容易直接落地到现有框架。


### 2.10 完成性 / 终止性

典型问题：

- 系统是否存在路径到达 `Completed` / `Done` / `<end>`
- 是否存在执行会一直无法完成
- 某条任务流是否一定能收敛到完成或故障终止

对 batch workflow、任务调度类状态机很有意义。


## 3. 推荐优先级

如果要按工程投入产出比排序，建议优先做下面几类：

### 第一优先级

- `verify_safety`
- `verify_invariant`
- `verify_state_predicate`

原因：

- 需求最常见
- 与现有可达性搜索最贴近
- 很容易产生可读的 counterexample


### 第二优先级

- `verify_transition_enablement`
- `verify_transition_shadowing`
- `verify_transition_deadness`

原因：

- 很适合状态机 DSL 的设计期检查
- 非常容易发现 guard 写错、顺序放错的问题
- 对状态图维护质量提升很明显


### 第三优先级

- `verify_dead_end`
- `verify_zero_cycle_loop`
- `verify_termination`

原因：

- 对层次状态机特别重要
- 能发现 simulate 时不容易第一眼定位的问题


### 第四优先级

- `verify_bounded_response`
- `verify_recovery`

原因：

- 业务价值高
- 但接口设计上需要先把“触发条件”“起始区域”“目标区域”“cycle 上界”这些概念定义得更清楚


## 4. 现有语义下必须说明的限制

### 4.1 当前更偏“存在性验证”，不是“全称验证”

当前 `verify` 对 event 的建模方式，本质上是：

- 每个 cycle 上，某个 event 是否触发，是一个布尔变量
- 搜索时只要求“存在一组赋值”即可

因此当前更适合回答：

- 是否存在一组初值和事件序列，使某个状态可达
- 是否存在一条 counterexample path 使某个坏条件发生

而不是直接回答：

- 对任意环境输入，系统都安全
- 无论事件怎么来，系统都不会进入危险状态

后者需要更强的全称语义或环境建模。


### 4.2 当前不适合直接宣称支持的性质

以下性质虽然在控制系统中也常见，但不建议在当前语义下直接宣称“已经支持”：

- 无界 liveness
- fairness
- 对任意输入的鲁棒安全性
- 对抗环境下的控制闭环安全性
- timed property
- watchdog timeout / deadline / 最小驻留时间
- 概率性质
- 连续系统或 hybrid system 性质

这些问题要么需要：

- 时间语义
- 全称量化或博弈语义
- 概率语义
- 连续动力学建模

都超出了当前 verify 的能力边界。


## 5. 建议的 verify API 演进方向

如果后续要逐步扩展 `pyfcstm.verify`，建议优先形成下面这组接口：

- `verify_reachability`
- `verify_safety`
- `verify_invariant`
- `verify_state_predicate`
- `verify_transition_enablement`
- `verify_transition_shadowing`
- `verify_transition_deadness`
- `verify_dead_end`
- `verify_zero_cycle_loop`
- `verify_termination`
- `verify_bounded_response`
- `verify_recovery`

其中可以先实现最小闭环版本：

1. `verify_safety`
2. `verify_invariant`
3. `verify_transition_enablement`
4. `verify_transition_shadowing`
5. `verify_dead_end`

这五类已经足够覆盖大部分设计期验证需求。


## 6. 一个务实的落地思路

建议不要一开始把 verify 做成“大而全的性质语言”。

更务实的路线是：

1. 继续把当前 `symbolic BFS + witness` 能力打磨扎实
2. 在此基础上按“查询类型”逐步封装
3. 先支持最常用的 bounded safety / bounded liveness 子集
4. 等事件环境假设、输入模型、cycle 语义更稳定之后，再考虑更强的时序逻辑接口

这样做的好处是：

- 与现有实现连续性强
- 用户更容易理解 verify 的真实边界
- 每个新增性质都能复用现有搜索、求解、witness 生成基础设施


## 7. 总结

对 pyfcstm 当前的 verify 能力来说，最有价值、也最现实的方向，不是一步跨到完整模型检验，而是优先补齐下面这些控制系统高频性质：

- 安全性 / 禁态不可达
- 变量范围不变量
- 状态相关输出约束
- 死转换 / 不可触发转换
- 转换遮蔽 / 优先级错误
- 死锁 / 零周期活锁
- 有界恢复性
- 有界响应性
- 顺序约束
- 完成性 / 终止性

其中前五类最值得优先进入正式的 verify 能力清单。
