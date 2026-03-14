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


## 8. 针对当前 BFS 方案之外的更优验证路线

对于 pyfcstm 这种带有：

- 层次状态机结构
- guard / effect / lifecycle action
- 整数 / 浮点数据路径
- event 驱动与 cycle 驱动混合语义

的模型，单纯依赖 `BFS + symbolic pruning + Z3` 并不是最强路线。

它的优点是：

- 实现直观
- witness 易于生成
- 对 bounded reachability 很自然
- 便于与 simulate 语义对齐

但它的主要弱点也很明显：

- 对不可达 / 安全性证明能力弱
- 很依赖“目标较早出现”
- 搜索过程中需要频繁做 solver 判定
- 对同一状态反复产生新符号区域时容易退化

因此，如果目标是“最起码比 BFS 更好”，更值得重点考虑的是下面几类现有方法。


### 8.1 SMT-Based BMC

这是最直接、最现实、也最适合作为当前 BFS 替代品的方案。

基本思路是：

- 将 `0..k` 个 cycle 一次性展开成一个大公式
- 为每个时刻建立状态位置变量和数据变量
- 将 transition relation、guard、effect、lifecycle actions 编进公式
- 将“目标状态可达”或“坏性质成立”编码为终点条件

相比 BFS，它的优势通常是：

- 不需要显式维护 frontier
- 不需要对每个候选 frame 单独做一次“是否扩展解空间”的剪枝 SAT 判定
- 对 bounded reachability 和 bounded counterexample 通常更强
- 对“寻找一条长度不超过 `k` 的 witness path”尤其合适

对 pyfcstm 来说，这条路线很现实，因为现有代码已经具备：

- `expr -> z3` 转换
- `operation -> symbolic update`
- cycle 语义
- witness 路径思路

也就是说，现有 verify 基础设施已经覆盖了 BMC 所需的一大块底层能力。

它的局限主要是：

- 擅长“找反例 / 找可达路径”，不擅长直接“证明无解”
- `k` 很大时公式可能膨胀
- 更适合 bounded query，而不是无界证明

如果只选一个比 BFS 更值得优先实现的方法，`SMT-based BMC` 是第一选择。


### 8.2 k-Induction

如果要做的不是“找路径”，而是“证明某性质一直成立”，那么 `k-induction` 通常比 BFS 更适合。

其基本结构是：

- Base case：前 `k` 步内性质成立
- Inductive step：若连续 `k` 步都成立，则下一步也成立

适合的问题包括：

- 不变量
- 安全性
- 状态相关输出约束
- 变量范围约束

相比 BFS，它的优势是：

- 不依赖枚举所有 bounded 路径
- 对“证明坏状态不可达”更有形式化意义
- 对线性整数类控制逻辑通常很实用

局限包括：

- 不是所有性质都容易归纳
- 有时需要辅助 invariant
- 对“找最短 witness”不如 BMC / BFS 自然

如果后续要把 `verify_invariant` 做成真正有证明能力的接口，而不是 bounded bug hunting，那么 `k-induction` 很值得尽早纳入设计。


### 8.3 IC3 / PDR

这类方法是更强的一档安全性证明路线。

它的核心思想不是逐层穷举路径，而是：

- 逐步构造 reachable states 的 over-approximation
- 不断阻塞通往 bad states 的前驱
- 最终要么找到 counterexample，要么构造出归纳不变量证明 bad state 不可达

相比 BFS，它更强的点在于：

- 对安全性证明通常更有威力
- 不需要预先给定很大的展开深度
- 常常能避免深路径显式展开

但对 pyfcstm 当前阶段来说，这条路线的现实问题是：

- 实现复杂度明显更高
- 对纯布尔或有限状态系统最成熟
- 对 SMT theory 版本虽然也存在，但工程门槛较高
- 对层次状态机 + 数据路径 + lifecycle semantics 的直接自研成本不低

因此它更适合作为中长期方向，而不是当前 BFS 的第一替代品。


### 8.4 Predicate Abstraction / CEGAR

如果模型的状态空间主要是被数据变量拉大，而不是被控制状态数量拉大，那么抽象路线通常比 BFS 更有上限。

典型做法是：

- 先把变量空间抽象为区间、谓词或模板
- 在抽象模型上验证
- 如果得到伪反例，再 refinement

这类路线的典型价值在于：

- 可以把“很大甚至无穷”的数据域压缩到较小抽象空间
- 特别适合阈值型 guard 主导的控制系统

对 pyfcstm 而言，这一点很有吸引力，因为很多 DSL 模型的 guard 天然是这种风格：

- `x >= 10`
- `temp <= 50`
- `retry_count < 3`

不过，这条路线的实现门槛也不低：

- 抽象域设计需要经验
- witness 还原比 BFS / BMC 更复杂
- refinement 策略需要仔细设计

因此更适合作为中长期路线，而不是当前版本的近期替代方案。


### 8.5 组合式 / 层次化验证

对于层次状态机，一个常见问题是：

- 如果完全 flatten 再验证，状态空间会迅速膨胀

因此更高级的路线通常会考虑：

- 保留 hierarchy
- 按子系统 / 子状态机 / 模式分块验证
- 引入 assume-guarantee 或 compositional reasoning

这条路线的价值不是“换个 solver”，而是从建模结构上降低爆炸。

但目前 pyfcstm 的 DSL 和 verify 仍更接近单体状态机验证框架，因此这条路线暂时更像未来架构方向，而不是短期替换 BFS 的首选。


### 8.6 Timed Automata / UPPAAL

如果后续 verify 的目标扩展到这些时间性质：

- timeout
- deadline
- 最小驻留时间
- watchdog
- bounded response time

那么继续沿着当前 cycle-BFS 路线硬扩展通常不划算。

这时更自然的方案往往是：

- timed automata
- UPPAAL

这类工具对时间性质更原生，通常也比在当前 BFS 框架里手工编码时钟语义更可靠。


## 9. 常见现成工具与适配方向

### 9.1 nuXmv / SMV 系列

优点：

- 工业成熟
- 对安全性、可达性、CTL/LTL 都有成熟支持
- 具有符号模型检验和证明能力

潜在问题：

- pyfcstm DSL 需要先降成标准 transition system
- 对复杂算术和浮点的适配不如 SMT 路线自然
- hierarchy 需要做语义映射


### 9.2 UPPAAL

优点：

- 对 timed automata 很成熟
- 很适合 timeout、响应时间、deadline 一类问题

潜在问题：

- 对一般数据路径算术验证并不是万能方案
- 需要先明确 pyfcstm 的时钟语义与时间推进语义


### 9.3 SPIN / Promela

优点：

- 对并发协议、消息交互、离散控制流很强

潜在问题：

- pyfcstm 当前模型更偏“层次状态机 + 数据路径”
- 不一定是最贴合的直接后端


### 9.4 TLA+ / Apalache

优点：

- 规格层表达能力强
- 适合高层行为约束建模

潜在问题：

- 更适合作为规格级工具
- 不太像直接吃现有 pyfcstm DSL 的工程化后端


## 10. 针对 pyfcstm 的推荐演进路线

如果目标是“找到一条显著强于当前 BFS 的路线”，建议优先级如下。

### 10.1 短期路线

保留当前 BFS，但不要继续把它当成唯一主力引擎。

更合适的短期策略是：

1. 保留 BFS 作为：
   - 小模型 reachability
   - witness replay
   - 调试与语义核对工具
2. 新增 `SMT-based BMC` 作为：
   - bounded reachability
   - bounded safety counterexample
   - bounded response / recovery

这一步往往就能覆盖当前 verify 里最常见的高价值需求。


### 10.2 中期路线

在 BMC 之外，增加更强的“证明”能力。

建议优先考虑：

- `k-induction`

优先支持的性质可以包括：

- 变量范围不变量
- 状态相关输出约束
- 基本安全性

如果要提升稳定性，还可以考虑对 verify 支持的表达式子集做约束，例如优先聚焦：

- 布尔
- 整数
- 线性算术

而将下列高风险表达式视作“高级模式”：

- 浮点
- 位运算
- 幂运算
- 复杂非线性表达式


### 10.3 长期路线

长期如果要把 verify 做成 pyfcstm 的核心优势，可以考虑三条更重型的路线：

- 自研 `IC3/PDR-like` 安全性证明引擎
- 做 `predicate abstraction + CEGAR`
- 导出到 `nuXmv` / `UPPAAL` 这类成熟工具

三者各有取舍：

- 自研证明引擎：可深度贴合 DSL，但开发成本最高
- 抽象验证：数据域上限更强，但实现复杂
- 导出现成工具：可快速获得成熟算法，但需要做可靠的语义映射


## 11. 一个更现实的结论

如果问题是“对于 pyfcstm 这种状态机模型，现有更好的做法是什么”，那么最务实的答案不是一个“万能更优算法”，而是按问题类型分层：

- bounded reachability：优先 `SMT-based BMC`
- invariant / safety proving：优先 `k-induction`
- 更强安全性证明：长期考虑 `IC3/PDR`
- 数据域主导的爆炸：长期考虑 `predicate abstraction / CEGAR`
- 时间性质：优先 `UPPAAL`

换句话说，真正比 BFS 更好的路线，并不是单点替代，而是把 pyfcstm 的 verify 能力从“单一 BFS 引擎”升级为“按性质选择后端”的架构。
