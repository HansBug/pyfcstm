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

不过，这里也要避免把当前 BFS 理解成“只是一个性能更差的 BMC”。

基于 pyfcstm 现有这套基建，BFS 其实还承担了一个更像**分析底座**的角色，而不只是单次 reachability 查询引擎。

### 8.0 当前 BFS 方案相对 BMC 的额外价值

如果只从“理论表达能力”看，足够增强的 BMC 通过增加辅助变量、micro-step 索引和额外 instrumentation，通常可以编码掉很多 BFS 当前能表达的东西。

但是，从“当前实现形态”和“工程上天然擅长什么”来看，BFS 仍然有几类价值并不是单次 BMC 查询天然提供的。

#### 8.0.1 不必先固定一个唯一的 `k`

BMC 的基本问题形态是：

- 给定一个 bound `k`
- 询问在 `0..k` 内是否存在 witness

而当前 BFS 的工作方式更接近：

- 在给定 cycle/depth 限制下逐层扩展
- 只要还能产生新的可达 frame，就继续探索
- 如果不显式给定严格的 `k`，也仍然可以继续做“尽量展开直到当前抽象下收敛”

这意味着 BFS 更适合承担如下角色：

- 作为“当前可达空间”的构建器
- 作为后续多种分析的公共前端

换句话说，BMC 天然更像“有界判定器”，而 BFS 更像“可达空间探索器”。


#### 8.0.2 reachable space 本身就是产物

当前 BFS 最大的一个实际优势在于：

- 它不只是返回 sat / unsat
- 它还显式保留了搜索上下文、状态分桶和 symbolic frame

这件事非常重要，因为很多后续 verify 能力本质上都可以表述为：

- “先得到一批可达 frame”
- “再对这些 frame 做进一步检查”

例如：

- invariant 反例搜索
- 状态相关输出约束检查
- transition deadness / shadowing
- dead-end / zero-cycle livelock 诊断

对这类任务来说，BFS 的结果不是一个临时中间物，而是直接可复用的分析资产。


#### 8.0.3 更自然支持在线、过程式查询

当前 BFS 的一个很实用的特点是：

- 搜索过程中每当有新 frame 被保留，就可以立即做额外判断
- 一旦命中目标条件，就可以提前停止

这使它很适合承载一些“不一定事先写成单个大公式”的查询方式，例如：

- 一旦发现某类 frame 就停止
- 一旦某个 bucket 的可达条件被扩展到某个程度就停止
- 一旦发现某种 cycle/depth 模式就报告

这种“边探索边做任意 Python 逻辑判断”的能力，在工程上非常灵活。

BMC 当然也可以通过“外部循环 + 多次求解”去模拟，但那已经不是单次 BMC 查询天然擅长的工作方式了。


#### 8.0.4 中间语义边界是第一类对象

pyfcstm 不是一个纯平面的 FSM，它的执行边界里还包含：

- leaf state
- composite 入口边界
- composite 退出边界
- terminal `<end>`

当前 BFS 显式把这些边界节点保留下来，而不是把它们全部压扁到“某个时刻的整体状态变量”里。

这带来的好处是：

- 可以直接观察 composite 进入/退出的可达性
- 可以直接分析 parent boundary 上的卡死与后继
- 可以直接保留 pseudo / boundary 链中的中间 frame

对很多调试和诊断型任务来说，这些中间点本身就是用户关心的对象，而不只是实现内部细节。


#### 8.0.5 对 zero-cycle 问题更自然

在 pyfcstm 里，pseudo state 和某些 composite boundary 会导致：

- `depth` 增长
- 但 `cycle` 不增长

这正是 zero-cycle livelock / pseudo-chain 问题的核心结构。

当前 BFS 直接保留：

- 每个 frame 的 `depth`
- 每个 frame 的 `cycle`
- frame 之间的 predecessor history

因此，像下面这类问题就更自然：

- 是否存在一直增长 `depth` 但不增长 `cycle` 的循环
- 是否卡在 pseudo / composite boundary 内无法回到稳定边界
- 哪一段 zero-cycle 链导致某个状态机设计陷阱

如果用 BMC 来做，同样可以编码，但往往需要引入额外的 micro-step 维度和额外性质定义；这不是它最自然的工作模式。


#### 8.0.6 部分结果仍然有价值

BFS 还有一个经常被低估的优点：

- 即使搜索被边界截断
- 即使还没有完全证明某个全局性质
- 只要已经探索出一部分 reachable buckets / frames

这部分结果本身就已经可以拿来做分析和调试。

而 BMC 更常见的交互模式通常是：

- 构造一个公式
- 扔给 solver
- 等待 sat / unsat / unknown / timeout

如果超时或中途停止，往往更难直接得到一个结构化的“已探索可达空间前缀”。

因此，从工具体验上看：

- BFS 更像 exploration / diagnosis platform
- BMC 更像 property query engine


#### 8.0.7 更准确的角色划分

基于当前实现，更准确的理解通常应该是：

- BFS 不只是“慢版 reachability”
- BFS 更像 verify 的分析底座
- BMC 更像未来 bounded reachability / bounded counterexample 的高效主力后端

所以，如果未来真的引入 BMC，更合理的演进方式通常不是“把 BFS 整体删掉”，而是：

- 保留 BFS 作为 reachable-space exploration、语义调试、结构诊断的平台
- 用 BMC 去承担最核心的 bounded reachability / bounded safety 查询
- 在更需要“证明”的地方再引入 `k-induction` 或更强方法

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


#### 8.1.1 具体示例：将 water heater 状态机编成 BMC 公式

下面用一个具体状态机说明 BMC 到底是如何落地编码的。

示例 DSL：

.. code-block:: fcstm

    def int water_temp = 55;
    def int draw_count = 0;

    state Root {
        state Standby {
            during {
                water_temp = water_temp - 1;
            }
        }

        state Heating {
            during {
                water_temp = water_temp + 4;
            }
        }

        [*] -> Standby;
        Standby -> Heating : if [water_temp <= 50];
        Standby -> Standby :: HotWaterDraw effect {
            water_temp = water_temp - 8;
            draw_count = draw_count + 1;
        };
        Heating -> Standby : if [water_temp >= 60];
        Heating -> Heating :: HotWaterDraw effect {
            water_temp = water_temp - 8;
            draw_count = draw_count + 1;
        };
    }

为了让示例更聚焦，这里采用如下建模约定：

- `state[i]`、`water_temp[i]`、`draw_count[i]` 表示第 `i` 个 cycle 结束后的稳定边界
- `hot_water_draw[i]` 表示第 `i` 个 cycle 中外部是否给了 `HotWaterDraw` 事件
- 初始状态直接从 `[*] -> Standby` 之后的稳定边界开始

这相当于将状态机的执行编码为：

1. 初始约束 `Init(0)`
2. 每一步的 transition relation `Trans(i, i+1)`
3. 最后再附加“目标状态在 `0..k` 范围内出现”的 reachability 公式

下面是一个对应的 Python + Z3 示例：

```python
import z3


def build_water_heater_bmc(max_cycles: int):
    # 1. 控制状态枚举
    State, (Standby, Heating) = z3.EnumSort("State", ["Standby", "Heating"])

    # 2. 按时间展开的变量
    state = [z3.Const(f"state_{i}", State) for i in range(max_cycles + 1)]
    water_temp = [z3.Int(f"water_temp_{i}") for i in range(max_cycles + 1)]
    draw_count = [z3.Int(f"draw_count_{i}") for i in range(max_cycles + 1)]

    # 外部事件：第 i 个 cycle 是否发生 HotWaterDraw
    hot_water_draw = [z3.Bool(f"hot_water_draw_{i}") for i in range(max_cycles)]

    s = z3.Solver()

    # 3. 初始条件
    s.add(state[0] == Standby)
    s.add(water_temp[0] == 55)
    s.add(draw_count[0] == 0)

    # 可选的基本域约束
    for i in range(max_cycles + 1):
        s.add(draw_count[i] >= 0)

    # 4. 逐步编码 transition relation
    for i in range(max_cycles):
        in_standby = state[i] == Standby
        in_heating = state[i] == Heating

        # Standby 中按声明顺序：
        # 1. Standby -> Heating : if [water_temp <= 50];
        # 2. Standby -> Standby :: HotWaterDraw effect { ... };
        # 所以第二条只有在第一条不触发时才有机会生效。
        standby_to_heating = z3.And(
            in_standby,
            water_temp[i] <= 50,
        )

        standby_hot_draw = z3.And(
            in_standby,
            water_temp[i] > 50,      # 前一条没有触发
            hot_water_draw[i],       # 事件发生
        )

        standby_stay = z3.And(
            in_standby,
            water_temp[i] > 50,      # 前两条都没触发
            z3.Not(hot_water_draw[i]),
        )

        # Heating 中按声明顺序：
        # 1. Heating -> Standby : if [water_temp >= 60];
        # 2. Heating -> Heating :: HotWaterDraw effect { ... };
        heating_to_standby = z3.And(
            in_heating,
            water_temp[i] >= 60,
        )

        heating_hot_draw = z3.And(
            in_heating,
            water_temp[i] < 60,      # 前一条没有触发
            hot_water_draw[i],
        )

        heating_stay = z3.And(
            in_heating,
            water_temp[i] < 60,
            z3.Not(hot_water_draw[i]),
        )

        cases = [
            standby_to_heating,
            standby_hot_draw,
            standby_stay,
            heating_to_standby,
            heating_hot_draw,
            heating_stay,
        ]

        # 每一步必须且只能命中一个 case
        s.add(z3.PbEq([(c, 1) for c in cases], 1))

        # 5. 每个 case 的后继状态更新
        # 这里同时编码 effect 和目标叶状态的 during

        # Standby -> Heating
        # effect: 无
        # Heating.during: water_temp = water_temp + 4
        s.add(z3.Implies(
            standby_to_heating,
            z3.And(
                state[i + 1] == Heating,
                water_temp[i + 1] == water_temp[i] + 4,
                draw_count[i + 1] == draw_count[i],
            )
        ))

        # Standby -> Standby :: HotWaterDraw
        # effect:
        #   water_temp = water_temp - 8
        #   draw_count = draw_count + 1
        # 然后目标还是 Standby，同 cycle 执行 Standby.during:
        #   water_temp = water_temp - 1
        # 所以净效果是 water_temp - 9, draw_count + 1
        s.add(z3.Implies(
            standby_hot_draw,
            z3.And(
                state[i + 1] == Standby,
                water_temp[i + 1] == water_temp[i] - 9,
                draw_count[i + 1] == draw_count[i] + 1,
            )
        ))

        # Standby 无 transition，执行 Standby.during
        s.add(z3.Implies(
            standby_stay,
            z3.And(
                state[i + 1] == Standby,
                water_temp[i + 1] == water_temp[i] - 1,
                draw_count[i + 1] == draw_count[i],
            )
        ))

        # Heating -> Standby
        # effect: 无
        # 然后执行 Standby.during: water_temp - 1
        s.add(z3.Implies(
            heating_to_standby,
            z3.And(
                state[i + 1] == Standby,
                water_temp[i + 1] == water_temp[i] - 1,
                draw_count[i + 1] == draw_count[i],
            )
        ))

        # Heating -> Heating :: HotWaterDraw
        # effect:
        #   water_temp = water_temp - 8
        #   draw_count = draw_count + 1
        # 然后执行 Heating.during: water_temp + 4
        # 净效果：water_temp - 4, draw_count + 1
        s.add(z3.Implies(
            heating_hot_draw,
            z3.And(
                state[i + 1] == Heating,
                water_temp[i + 1] == water_temp[i] - 4,
                draw_count[i + 1] == draw_count[i] + 1,
            )
        ))

        # Heating 无 transition，执行 Heating.during
        s.add(z3.Implies(
            heating_stay,
            z3.And(
                state[i + 1] == Heating,
                water_temp[i + 1] == water_temp[i] + 4,
                draw_count[i + 1] == draw_count[i],
            )
        ))

    return s, State, Standby, Heating, state, water_temp, draw_count, hot_water_draw


def solve_reach_heating(max_cycles: int):
    s, _, _, Heating, state, water_temp, draw_count, hot_water_draw = build_water_heater_bmc(max_cycles)

    # 6. BMC 查询：是否存在一条长度 <= max_cycles 的路径，到达 Heating
    reach_heating = z3.Or([state[i] == Heating for i in range(1, max_cycles + 1)])
    s.add(reach_heating)

    if s.check() != z3.sat:
        print(f"UNSAT: cannot reach Heating within {max_cycles} cycles")
        return

    m = s.model()
    print(f"SAT: can reach Heating within {max_cycles} cycles")

    first_heating_step = None
    for i in range(1, max_cycles + 1):
        if z3.is_true(m.eval(state[i] == Heating, model_completion=True)):
            first_heating_step = i
            break

    print(f"first Heating step = {first_heating_step}")
    print()

    for i in range(max_cycles + 1):
        st = m.eval(state[i], model_completion=True)
        wt = m.eval(water_temp[i], model_completion=True)
        dc = m.eval(draw_count[i], model_completion=True)
        print(f"step {i}: state={st}, water_temp={wt}, draw_count={dc}")
        if i < max_cycles:
            evt = m.eval(hot_water_draw[i], model_completion=True)
            print(f"        hot_water_draw[{i}] = {evt}")


if __name__ == "__main__":
    print("=== query: reach Heating within 1 cycle ===")
    solve_reach_heating(1)

    print("\\n=== query: reach Heating within 2 cycles ===")
    solve_reach_heating(2)
```

这段代码体现了 BMC 的核心套路：

1. 将状态机按时间展开为 `state_0 .. state_k`
2. 将变量按时间展开为 `water_temp_0 .. water_temp_k`、`draw_count_0 .. draw_count_k`
3. 将外部事件按时间展开为 `hot_water_draw_0 .. hot_water_draw_{k-1}`
4. 对每个 cycle 编写一组 mutually-exclusive 的 case split，体现 transition declaration order
5. 将 effect、目标状态 during、以及未触发 transition 时的驻留 during 全部写进后继更新
6. 最后附加 reachability query，例如 `Or(state_1 == Heating, ..., state_k == Heating)`

从这个例子还能看出 BMC 与 BFS 的一个直观差异：

- BFS 是从初始状态开始一层层扩展后继
- BMC 是直接问 solver：“是否存在一组 `state_i`、`var_i`、`event_i` 的赋值，使得整条 `0..k` 执行链合法并且命中目标”

对于 pyfcstm 当前最常见的 bounded reachability / bounded safety 问题，这种编码方式通常比逐 frame 的 BFS 搜索更适合作为主力后端。


#### 8.1.2 `max_cycle`、伪状态与公式膨胀

上面的 water heater 例子故意选了一个没有 pseudo state、没有 composite boundary 的情形，因此它看起来几乎就是标准的“按 cycle 逐层展开”。

但对 pyfcstm 来说，真正需要提前说明的是：

- `max_cycle` 没有一个固定的“理论支持上限”
- 真正的上限通常取决于求解时间和内存，而不是 API 签名
- 当 `max_cycle` 很大、pseudo state 很多、zero-cycle 链很长时，BMC 公式会明显膨胀

换句话说，BMC 更像是在回答：

- “在给定 `k` 的前提下，这个问题能不能在可接受时间内求出来？”

而不是：

- “这个后端天然支持到多大的 `k`？”


##### 8.1.2.1 没有 pseudo state 时的增长趋势

如果模型只在稳定边界上推进，也就是：

- 每个 cycle 结束时一定落在一个 stoppable state 或 `<end>`
- 中间没有需要额外展开的 zero-cycle 内部步骤

那么一个朴素 BMC 的规模通常近似为：

- 变量数量：`O(k * (|V| + |E| + 1))`
- 约束数量：`O(k * |T|)`

其中：

- `k` 是 `max_cycle`
- `|V|` 是数据变量数量
- `|E|` 是每个 cycle 中被建模的事件布尔变量数量
- `|T|` 是每一步需要区分的 transition case 数量

在这种情况下，公式规模通常是**随 `max_cycle` 线性增长**的。只要 guard/effect 主要是线性整数约束，这类 BMC 在工程上往往是比较可控的。


##### 8.1.2.2 有 pseudo state 时为什么更容易膨胀

pyfcstm 的 pseudo state 有三个关键语义：

- 进入 pseudo state 不增加 cycle
- pseudo state 不能驻停，必须继续前进直到到达 stoppable state 或 `<end>`
- pseudo state 跳过祖先 aspect during actions，但仍然可能执行自己的 enter/during，以及后续状态的边界动作

因此，只用 `state[i] -> state[i+1]` 的单层编码往往不够。

更通用的编码通常需要两层索引：

- `cycle = 0..k`
- `micro_step = 0..M`

也就是在一个 cycle 内继续展开 zero-cycle 的内部迁移，例如：

- `loc[c, m]`：第 `c` 个 cycle 内第 `m` 个 micro-step 所在的位置
- `vars[c, m]`：对应的数据变量状态

这时，规模大致会变成：

- 变量数量：`O(k * M * (|V| + 1) + k * |E|)`
- 约束数量：`O(k * M * |T_step|)`

这里最敏感的量不再只是 `k`，而是 `k * M`。

其中 `M` 近似代表：

- 一个 cycle 内可能经历的 pseudo state 数量
- composite 入口/出口边界数量
- zero-cycle chain 的最大长度

所以对 pyfcstm 这类模型来说，**伪状态多不一定直接导致不可做，但会把原本按 `k` 线性增长的问题，变成按 `k * M` 增长的问题**。


##### 8.1.2.3 伪状态链为什么尤其危险

例如下面这类链：

.. code-block:: fcstm

    state A;
    pseudo state P1;
    pseudo state P2;
    state B;

    A -> P1 :: Go1;
    P1 -> P2 :: Go2;
    P2 -> B  :: Go3;

如果从稳定状态 `A` 出发，在一个 cycle 内必须连续经过 `P1 -> P2 -> B` 才能落到下一个稳定边界，那么这 3 条 zero-cycle 迁移都会被编码进同一个 cycle 的展开里。

如果再叠加：

- 多层 composite 进入/退出
- 带 guard 的 pseudo chain 分支
- 多个事件组合

那么同一个 cycle 内的 case split 数量会迅速上升。

更麻烦的是 zero-cycle 环，例如：

.. code-block:: fcstm

    pseudo state P1;
    pseudo state P2;

    P1 -> P2;
    P2 -> P1;

这种结构不会增加 cycle，但会增加搜索深度或 micro-step 深度。对 BMC 来说，这意味着：

- 必须额外给每个 cycle 设置 `M` 上界
- 或者先做专门的 zero-cycle livelock 检测

否则公式会为了表示“同一个 cycle 内可能走很多步”而迅速膨胀，甚至失去收敛性。


##### 8.1.2.4 还有哪些因素会放大膨胀

除了 `k` 和 pseudo/composite 的 zero-cycle 链，下面这些因素也会明显影响 BMC 可扩展性：

- transition declaration order 带来的 mutually-exclusive case split
- 事件变量数量过多，导致每个 cycle 的布尔选择空间扩大
- guard/effect 中包含复杂非线性算术
- 浮点、幂运算、位运算等对 SMT 不够友好的表达式

对 pyfcstm 来说，这一点尤其值得提前说明，因为现有 `pyfcstm.solver.expr` 已经明确提示了一些表达式的代价，例如：

- `x ** y` 这类双变量幂运算会很慢
- `Int` 上的位运算支持有限
- 某些数学函数需要额外近似或根本无法直接支持

因此，同样的 `max_cycle=50`：

- 如果模型主要是线性整数 guard/effect，通常还比较现实
- 如果模型里混入大量非线性或复杂数值操作，求解难度可能会陡增


##### 8.1.2.5 一个务实的规模判断

从工程角度，更合理的预期通常是：

- 不要把“能支持多大的 `max_cycle`”理解成固定常数
- 应该把它理解为“在当前模型结构和表达式复杂度下，solver 能承受多大的 horizon”

比较保守地说：

- 对小到中等规模、以线性整数为主、pseudo 链不长的模型，`k = 50..200` 往往是有希望的
- 对大量 pseudo/composite zero-cycle 链的模型，如果采用朴素 `cycle x micro-step` 展开，`k = 10..50` 就可能开始吃力
- 如果再叠加重非线性表达式，那么可行的 `k` 还会进一步下降

这些数字不是承诺，只是说明**瓶颈主要来自公式膨胀和 theory 难度，而不是某个写死的后端上限**。


#### 8.1.3 控制膨胀的更合适建模方式

如果 pyfcstm 未来真的实现 BMC，那么对带 pseudo state 的状态机，最关键的不是“能不能展开”，而是“如何避免无谓展开”。

我更倾向于优先采用下面的策略。


##### 8.1.3.1 优先压缩 zero-cycle 链

对于 pseudo state 和 composite boundary，最好不要一上来就做完全朴素的 `cycle x micro-step` 编码。

更值得优先尝试的是：

- 先把一个稳定边界到下一个稳定边界之间的 zero-cycle 链做静态压缩
- 将这段链视为一个“宏迁移”进行编码

也就是说，把：

- `A -> P1 -> P2 -> B`

尽量压成：

- `A ==[same cycle]==> B`

并将中间的：

- `P1.enter`
- `P1/P2` 的 during
- composite 的边界动作
- transition effect

都合并进这个宏迁移的更新式中。

这样做的直接收益是：

- 变量数量更接近 `O(k * |V|)` 而不是 `O(k * M * |V|)`
- 求解器看到的是“稳定边界之间的后继关系”，更接近真正的 bounded reachability 问题


##### 8.1.3.2 先做 zero-cycle 环检测

如果模型中存在明显的 pseudo/composite zero-cycle 环，那么在进入 BMC 之前，最好先单独做结构检查，例如：

- `verify_zero_cycle_loop`
- `verify_dead_end`

因为这类问题让 SMT 去硬扛并不划算：

- 它们本质上更像结构错误或语义陷阱
- 提前报错通常比把它们编码进大公式更有效


##### 8.1.3.3 使用 incremental BMC，而不是一次把 `k` 拉很大

更务实的方式通常是：

1. 从 `k = 1` 开始
2. 逐步增加到 `k = 2, 3, 4, ...`
3. 一旦找到 witness 就提前停止

这样做至少有两个好处：

- 对 reachability / counterexample 查询非常自然
- 避免一开始就构造一个过大的公式


##### 8.1.3.4 限制首批支持的表达式子集

如果要让 BMC 版本尽快变得可用，首批支持的表达式最好优先聚焦：

- 布尔逻辑
- 整数
- 线性算术
- 简单比较

而对下面这些特性至少要谨慎看待：

- 浮点
- 位运算
- 双变量幂运算
- 复杂非线性表达式

这不是语义上“不能支持”，而是从可扩展性上看，它们很容易让 BMC 退化得过于严重。


##### 8.1.3.5 BMC 更适合 bounded bug hunting，不适合单独承担证明任务

最后还要明确一点：

- BMC 很适合 bounded reachability
- BMC 很适合 bounded safety counterexample
- BMC 很适合 bounded response / bounded recovery

但它并不擅长独立承担“大 `k` 下的不可达证明”。

因此，一个更现实的 verify 架构通常是：

- BMC 负责“找得到路径吗”
- `k-induction` 或更强方法负责“能证明永远到不了吗”

这也正是为什么对 pyfcstm 来说，`SMT-based BMC` 更像是 BFS 的近期替代主力，而不是唯一的长期后端。


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

#### 8.2.1 基于现有基建的可行性

从 8.2 之后这些路线里看，`k-induction` 是和当前 pyfcstm 基建衔接最自然的一条。

原因是现有代码已经具备了以下可直接复用的底层能力：

- 表达式到 Z3 的转换
- 变量定义到 Z3 变量的映射
- effect / lifecycle action 的符号执行
- 当前 BFS 中已经显式编码过的状态机 operational semantics

换句话说，`k-induction` 缺的不是 solver 积木，而是：

- 一层统一的 `Init(s)` / `Trans(s, s')` / `Prop(s)` 构造器
- 一套“当前状态变量”和“下一状态变量”的 priming 机制

只要这层补起来，`k-induction` 的基本框架就有了很强的落地可能性。

#### 8.2.2 实现难度

实现难度我会评估为**中偏高**。

真正的难点主要不在于写出 base case 和 inductive step 这两个 solver 查询，而在于：

- 如何把当前 BFS 中分散在扩展逻辑里的语义，抽象成统一的 transition relation
- 如何处理 pyfcstm 特有的 leaf / pseudo / composite boundary 语义
- 如何把“状态相关性质”稳定地编译成 `Prop(s)` 公式

如果只做一个最小可用版，难度不算特别高；但如果要做到：

- 反例路径可读
- 支持多个 init
- 支持环境约束
- 和未来 BMC 共享统一语义层

那么工程工作量就会明显上升。

#### 8.2.3 现有可复用基建

最值得直接复用的是下面几类组件：

- `pyfcstm.solver.expr`：表达式转 Z3
- `pyfcstm.solver.vars`：从状态机变量定义创建 Z3 变量
- `pyfcstm.solver.operation`：effect / during / enter / exit 的符号执行
- `pyfcstm.verify.search`：当前 operational semantics 的语义参考实现

尤其是 `verify.search` 这一层，虽然它目前是 BFS 驱动的，但实际上已经把很多关键语义写清楚了：

- transition declaration order
- pseudo state 的 cycle 语义
- composite 入口/出口边界
- aspect 与普通 during 的执行顺序

这会让 `k-induction` 的 transition relation 建模比“从零发明语义”容易很多。

#### 8.2.4 主要缺口

当前最关键的缺口，是**没有显式的 transition-system builder**。

也就是说，现在有的是：

- “如何从一个 frame 扩展到后继 frame”

但还没有：

- “如何一次性构造 `Trans(s, s')` 这类关系公式”

如果要支持 `k-induction`，至少需要补下面这些公共基建：

- control-location 编码
- primed / unprimed 变量命名与映射
- `Init(s)` 构造器
- `Trans(s, s')` 构造器
- `Prop(s)` / `Bad(s)` 编译器
- 结果对象：区分 `proved` / `counterexample` / `unknown`

此外，最好还要有：

- witness path replay
- 反例从 Z3 model 回译到 pyfcstm path 的工具
- 对 induction 失败原因的区分（base-case 失败、step-case 失败、solver timeout）

#### 8.2.5 需要补的 DSL 语义

首版 `k-induction` 不一定非要新增 DSL 语义。

如果只想验证：

- invariant
- state predicate
- 基本 safety

那么复用现有 DSL 表达式系统就够了。

但如果想把这条路线做得真正可用，我认为最好补下面几类语义或至少补出对应 API：

- 环境 assumptions
- 变量域 / 取值范围约束
- 正式的 property 输入形式

原因很简单：很多 induction 是否能成功，很依赖：

- 初始条件是否足够明确
- 环境输入是否被合理约束
- 变量空间是否有工程上已知的界限

没有这些信息时，很多原本在业务上显然为真的性质，在形式上会很难归纳。

#### 8.2.6 更现实的首批落地边界

我更推荐的首批支持边界是：

- 变量类型优先支持 `bool` / `int`
- `float` 先按 Z3 `Real` 语义处理，并明确这不是 IEEE 浮点精确语义
- 表达式优先支持线性算术和简单比较
- 先支持 `verify_invariant` / `verify_state_predicate`

暂时不建议一开始就承诺：

- 复杂非线性
- 强位运算语义
- 全量浮点精确证明

如果先把这条线做好，它会是 8.2 之后最有现实产出的一个后端。


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

#### 8.3.1 基于现有基建的可行性

如果问题是“能不能基于现有基建往这边走”，答案是：

- **不是完全不可行**
- 但当前基建距离可用的 IC3 / PDR 还差得非常远

现有基建能提供的是：

- 表达式与约束层
- 部分 operational semantics 参考
- 一些基本 solver 工具

但 IC3 / PDR 真正依赖的是另一套能力：

- predecessor blocking
- generalized cube learning
- 归纳 frame 序列
- 安全性证明过程中的 generalized clause strengthening

这些都不在当前 verify/solver 的能力范围里。

#### 8.3.2 实现难度

实现难度我会评估为**很高**。

尤其是对 pyfcstm 这种模型，困难不只是算法本身，而是算法与 DSL 语义的耦合：

- hierarchy
- pseudo / composite boundary
- 事件驱动与 cycle 驱动混合
- 整数 / 实数数据路径

如果是纯布尔、有限状态、扁平 transition system，IC3/PDR 的落地门槛已经不低；对当前 pyfcstm 这种 richer semantics 的模型，自研成本会进一步抬高。

#### 8.3.3 现有可复用基建

可复用的部分主要还停留在“底层积木”：

- `expr_to_z3`
- 变量创建
- 基本逻辑关系检查
- operation 的符号执行

这些组件对 IC3 / PDR 是必要的，但远远不够。

也就是说，当前基建最多能解决：

- 状态和公式怎么表示

但解决不了：

- 如何做 PDR 主循环
- 如何做 blocking/generalization
- 如何构造 inductive strengthening

#### 8.3.4 主要缺口

如果未来真的要做这条路线，至少需要补：

- 明确的 `Init/Trans/Bad` 公式层
- predecessor 查询接口
- cube / region 表示
- generalized blocking 机制
- frame 序列管理
- 证明对象或归纳不变量提取

此外，还很可能需要更强的 solver 支撑，例如：

- unsat core
- model-based projection
- 更强的 generalization 辅助

否则做出来的版本很容易停留在“概念存在、稳定性不足”的阶段。

#### 8.3.5 需要补的 DSL 语义

这条路线如果想可控，几乎一定需要**限制 DSL 子集**，而不是无条件吃全量语义。

更适合作为首批目标的子集通常是：

- 布尔
- 有界整数或至少较容易抽象的整数
- 线性算术
- 相对简单的控制流

而对下面这些特性，应当非常谨慎：

- 复杂非线性
- 强浮点语义
- 复杂位运算
- 过于自由的无限域数据路径

如果不加限制，PDR 的理论优势在工程实现中很容易被语义复杂度抵消掉。

#### 8.3.6 更现实的落地方式

更现实的路线不是“直接自研一整套 IC3/PDR”，而是：

1. 先把 `Init/Trans/Prop` 这层补好
2. 先把 BMC / `k-induction` 做稳
3. 再决定是：
   - 自研一个受限子集的 PDR-like 引擎
   - 还是尽量复用现有 solver/外部后端提供的固定点或 Horn 能力

所以，这条路线更像长期增强方向，而不是近期里程碑。


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

#### 8.4.1 基于现有基建的可行性

如果只看 8.2 之后几条路线里“哪条和 pyfcstm DSL 的 guard 风格最契合”，我反而会把这一条排得很靠前。

原因是很多 pyfcstm 模型天然就是阈值驱动的：

- `x >= 10`
- `temp <= 50`
- `retry_count < 3`

这类 guard 很适合抽象成谓词。

因此，基于当前基建做 Predicate Abstraction / CEGAR，**可行性是中到高**的。

它比 IC3/PDR 更贴近你现在的数据路径形态，也比 timed automata 需要更少的新 DSL 语义。

#### 8.4.2 实现难度

实现难度我会评估为**中偏高**。

主要挑战不是 solver 不够，而是需要补一整套“抽象层”和“refinement 层”：

- 谓词收集
- abstract state 表示
- abstract successor 计算
- spurious counterexample replay
- predicate refinement

好消息是，这些工作虽然多，但大多是工程构造问题，不像 PDR 那样对底层证明算法依赖那么强。

#### 8.4.3 现有可复用基建

当前最适合复用的有三类：

- 现有 solver 层：用于 concrete feasibility check
- 现有 BFS 或未来 BMC：用于生成 candidate counterexample
- 现有 guard/effect 表达式：用于抽取初始谓词集合

特别是当前 DSL guard 的风格，本身就可以作为谓词候选来源。

也就是说，这条路线和现有 pyfcstm 的契合点在于：

- 控制状态保持精确
- 数据状态做抽象

这恰好符合当前模型的结构特征。

#### 8.4.4 主要缺口

如果未来要做这条路线，当前缺的主要是：

- predicate manager
- abstract state 表示
- abstract transition relation
- spurious path replay
- refinement engine

此外，还需要一个关键设计决策：

- 控制状态是否保持精确
- 数据状态是否只做谓词抽象

对 pyfcstm 来说，我更推荐：

- **控制结构精确保留**
- **数据路径做抽象**

否则 hierarchy / pseudo / boundary 这些语义会一起被抽象掉，结果很容易失真。

#### 8.4.5 需要补的 DSL 语义

首版其实不一定需要新增 DSL 语义。

因为谓词可以先从下列来源自动提取：

- transition guards
- target predicate
- invariant / safety property

但如果想提升工程可用性，最好补出下面这些能力：

- 用户显式提供 predicates
- 变量范围或阈值注解
- 环境 assumptions

这样 refinement 才不会完全依赖自动猜测。

#### 8.4.6 更现实的落地方式

我更推荐的落地方式是：

1. 先做“控制状态精确 + 数据谓词抽象”的 MVP
2. 用现有 solver 做 concrete replay，排除伪反例
3. refinement 先从“把反例路径中出现的 guard/比较加入谓词集”开始

这样做的好处是：

- 不需要一开始就实现很强的自动谓词发现
- 可以尽量复用现有搜索与求解器能力
- 和 pyfcstm 当前的 guard 风格很匹配

从中期路线看，这条线很值得认真评估。


### 8.5 组合式 / 层次化验证

对于层次状态机，一个常见问题是：

- 如果完全 flatten 再验证，状态空间会迅速膨胀

因此更高级的路线通常会考虑：

- 保留 hierarchy
- 按子系统 / 子状态机 / 模式分块验证
- 引入 assume-guarantee 或 compositional reasoning

这条路线的价值不是“换个 solver”，而是从建模结构上降低爆炸。

但目前 pyfcstm 的 DSL 和 verify 仍更接近单体状态机验证框架，因此这条路线暂时更像未来架构方向，而不是短期替换 BFS 的首选。

#### 8.5.1 基于现有基建的可行性

这里要区分两件事：

- 保留 hierarchy 做摘要或优化
- 真正做 assume-guarantee compositional verification

前者基于现有基建是**中等可行**的；
后者基于现有基建则是**较低可行**的。

原因在于，当前 verify/search 已经显式把 hierarchy 的边界节点保留了：

- composite_in
- composite_out

这意味着“做复合状态摘要”并不是毫无基础。

但当前 DSL 和 verify 还没有：

- 组件接口
- assume / guarantee
- 模块化环境边界

所以距离真正的 compositional reasoning 还差很远。

#### 8.5.2 实现难度

如果目标只是：

- 利用 hierarchy 做状态空间压缩
- 为 composite state 生成 summary

那么实现难度大致是**中等**。

但如果目标升级为：

- 子系统分块验证
- assume-guarantee
- 局部证明后自动组合成全局证明

那难度会迅速上升到**很高**，而且挑战主要在语义设计，不在 solver。

#### 8.5.3 现有可复用基建

这条路线最值得复用的，其实不是 solver，而是当前 BFS 已经显式化的 hierarchy 语义：

- 复合状态入口边界
- 复合状态出口边界
- 边界动作
- pseudo / stoppable / composite 的区分

也就是说，当前 verify/search 其实已经把“层次边界”作为第一类对象建模了。

这对做：

- entry-to-exit summary
- child-to-parent continuation summary
- hierarchy-preserving compression

都是很好的基础。

#### 8.5.4 主要缺口

如果未来要认真推进这条路线，缺口主要在下面这些方面：

- summary 形式定义
- 子状态机接口定义
- 组件局部环境的语义
- contract 检查器
- 组合规则

换句话说，现在缺的不是“如何表示状态”，而是：

- “如何切分系统”
- “如何描述切分后的边界”
- “如何证明局部结论能安全组合”

这类问题不补清楚，组合式验证就很容易只停留在概念层面。

#### 8.5.5 需要补的 DSL 语义

如果只做 hierarchy-preserving summary，首版不一定非要新增 DSL。

但如果要做更正式的 compositional verification，几乎一定需要补：

- 模块或组件边界
- 输入 / 输出事件或接口语义
- 变量可见性与读写边界
- assume / guarantee 语法或至少对应 API

没有这些，就很难让“局部证明”具备明确的组合意义。

#### 8.5.6 更现实的落地方式

这条路线更现实的第一步不是“做完整 assume-guarantee”，而是：

- 先做复合状态摘要
- 先把 hierarchy 用来压缩搜索和公式规模

也就是说，它更像：

- 先作为 BFS/BMC 的优化技术
- 再逐步演进成真正的组合式验证框架

如果按阶段推进，我会把它放在：

- BMC / `k-induction` 之后
- 真正的 timed / compositional 大扩展之前


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

#### 8.6.1 基于现有基建的可行性

如果不扩 DSL 时间语义，单靠当前基建直接走 timed automata / UPPAAL，**可行性是比较低的**。

原因很直接：

- 当前 pyfcstm 有 cycle 语义
- 但还没有真正的 clock / time-elapse / state invariant 语义

也就是说，现在离“可以做 timed automata 导出”之间，还隔着一层更根本的工作：

- 先把时间语义本身定义出来

#### 8.6.2 实现难度

如果只是说“把已经存在的 timed semantics 导出给现成工具”，实现难度并不一定最高。

真正困难的是：

- 当前还没有完整 timed semantics
- 需要先扩 DSL
- 还要让 simulate / verify 都理解这套时间语义

因此，从整体工作量看，这条路线是**高难度**的，而且难点更多在语义设计与一致性维护，而不只是 exporter。

#### 8.6.3 现有可复用基建

当前可复用的部分主要有：

- 现有控制状态结构
- guard/effect 表达式系统
- hierarchy 语义

但这些只能算“控制流基底”。

真正 timed automata 核心依赖的那些东西，目前都还没有，例如：

- 时钟变量
- 时钟重置
- 状态不变式
- 时间推进规则
- timeout/deadline/min-dwell 语义

所以这条路线的可复用度其实没有前几条那么高。

#### 8.6.4 主要缺口

如果未来真的要走 timed automata / UPPAAL，这里缺的不是一个小模块，而是一整块新的语义层：

- clock domain
- time elapse semantics
- state invariant
- clock guard
- reset 规则
- timed property 编译器

此外，还需要考虑：

- hierarchy 如何降成 timed automata
- 事件语义如何映射到同步或离散跳转
- continuous-time / dense-time 还是 discrete-time

这些都不是当前 verify/BFS 里顺手补几行代码就能解决的。

#### 8.6.5 需要补的 DSL 语义

这条路线如果要认真做，DSL 基本一定要新增以下至少一部分：

- `clock` 或其他明确的时钟变量类型
- clock reset 语法
- 基于时钟的 guard
- 状态不变式
- timeout / deadline / 最小驻留时间语义
- urgent / committed 一类时间推进控制语义（如果要贴近 timed automata 习惯）

没有这些，所谓“导出到 timed automata”大概率只是把 cycle 计数器换个名字，而不是真正的 timed semantics。

#### 8.6.6 更现实的落地方式

如果后续确定要走这条路线，我更建议的实现策略是：

1. 先在 pyfcstm 内部明确时间语义
2. 先让 simulator 和 verify 对这套语义达成一致
3. 再考虑导出和对接外部 timed 后端

并且，基于你现在的想法，我认为这里最值得优先评估的是：

- **尽量复用 UPPAAL 官方提供的验证引擎 / 算法库**
- **避免从零自研 zone / DBM / timed reachability 核心算法**

原因很现实：

- timed automata 的核心算法本身已经很成熟
- 自研时间区域/zone 算法成本高、踩坑多、验证难
- pyfcstm 更适合把精力放在 DSL 语义映射、模型降级和 counterexample 回译上

也就是说，这条路线更像：

- 先补时间语义
- 再做可靠的模型映射
- 最后尽量挂接官方后端

而不是：

- 一开始就在 pyfcstm 内部重做一套完整 timed model checking 核心


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
