# FCSTM `after/timeout` 设计草案

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-16 | 初始版本，整理 `after/timeout` 的设计目标、语义、lowering 方案与边界规则 | Codex |

---

## 1. 设计目标

本文讨论 FCSTM 中常见 UML/SysML 状态图时间触发语义，重点是：

- 为 DSL 提供 `after(...)` 这一类超时/延时写法
- 尽量不改动现有 `SimulationRuntime` 的核心事件模型
- 与当前“基于周期”的执行语义保持一致
- 使 `simulate`、`verify`、`generate` 都能复用同一套降级结果

本文的核心结论是：

- `after(...)` 不应建模为新的运行时 time-event 实体
- `after(...)` 应建模为编译期语法糖，最终降级为内部 timer 变量、内部动作和普通 guard transition
- 对 leaf state 与 composite state，应采用不同的降级策略

这意味着，FCSTM 中的 `after(...)` 更接近“驻留时间达到阈值后的低优先级转移语法糖”，而不是严格 UML 中那种独立排队的一次性时间事件。

---

## 2. 为什么不引入新的运行时实体

现有架构的关键特征是：

- runtime 是 **cycle-based** 的
- 转移选择按定义顺序进行
- 运行时当前只显式识别“事件命中”和“guard 为真”
- 父状态转移只有在子状态先 `-> [*]` 退出到父状态后才会被考虑

在这样的架构下，如果把 `after(...)` 做成新的 time-event 实体，则会立刻引入一批额外问题：

- 是否需要事件队列
- time-event 是一次性的还是持续有效的
- 时间到达时若 guard 不满足，事件是否丢失
- composite state 的时间触发如何在子状态仍活跃时抢占
- `simulate`、`verify`、`generate` 是否都要理解新的 time-event 语义

这些问题本质上是在改执行模型，而不是加一个 DSL 特性。

相反，如果把 `after(...)` 直接降级为：

- 内部 timer 变量
- 内部 enter/during/aspect 动作
- 普通 guard transition

则当前 runtime、verify 和大部分模板化代码生成逻辑都可以复用，不需要引入新的基础语义。

---

## 3. 设计总原则

### 3.1 `after(...)` 是语法糖，不是新的基础语义

`after(...)` 的编译期含义是：

- 为 source state 合成一个内部时间相关变量
- 在状态进入时重置该变量
- 在状态保持活跃的每个 cycle 中推进该变量
- 将原始 `after(...)` 转换为普通 guard 条件

### 3.2 `after(...)` 是低优先级语义，不是抢占语义

“超时触发”在 FCSTM 中应解释为：

- 当 source state 已驻留足够久时
- 如果当前 active path 上没有更高优先级的普通转移先触发
- 那么 timeout 转移才触发

这里不引入新的 priority 体系，而是直接复用现有的“声明顺序优先”规则：

- 用户写的普通转移优先
- 编译器合成的 timeout 相关转移尾插在末尾

### 3.3 `after(...)` 的根语义是 cycle/tick，而不是 wall-clock

FCSTM 的 runtime 现在没有独立的 wall-clock 驱动机制，因此核心语义应落在：

- `after(N cycle)`
- `after(N tick)`

如果 DSL 表面允许写：

- `after(100ms)`
- `after(2s)`

那么其真实语义仍应通过固定 `cycle_time` 折算为 tick 数：

- `ticks = ceil(delay / cycle_time)`

没有固定 `cycle_time`，就不应承诺 `ms/s` 的精确核心语义。

---

## 4. source state 的分类约束

### 4.1 stoppable leaf state 允许使用 `after(...)`

这是最直接的场景。

对于 leaf state：

- 它本身就是稳定驻留点
- timeout 只需要在该状态自己的每周期推进里累计时间
- 原始转移可以直接 guard 化

### 4.2 composite state 允许使用 `after(...)`

这是更复杂但也很重要的场景。

对于 composite state：

- 时间语义应该表示“该 composite state 自进入以来已活跃多久”
- 其内部 child-to-child 切换不应重置该计时
- 若 timeout 到期，应允许从当前任意后代活跃路径递归退出到 composite 边界，再执行最终的 source transition

因此 composite timeout 不能只在 source 那一层改一条 guard transition，而必须递归合成退出链。

### 4.3 pseudo state 不允许使用 `after(...)`

原因如下：

- pseudo state 不是稳定驻留点
- pseudo state 的存在目的是“瞬时过渡”，不应持有时间积累语义
- 允许 pseudo state 使用 `after(...)` 会使“时间是否流逝”变得不明确

因此，应当做成语法级或 lowering 级的硬错误。

---

## 5. 基本语义定义

## 5.1 计时基准

推荐定义为：

- timer 统计的是 **状态活跃期间已经完成的 cycle 数**

这一定义与当前 runtime 的行为一致：

- leaf state 在进入时就会执行一次 `during`
- 因此进入后的第一个成功 cycle 结束时，状态已经“消耗了 1 个 cycle”

## 5.2 触发条件

若 `after(delay)` 被折算为 `N` 个 tick，则触发条件为：

```text
timer >= N
```

如果原转移本身还有额外 guard，则最终条件为：

```text
timer >= N && original_guard
```

## 5.3 进入和重置

source state 每次真正从父状态进入时：

- timer 被重置为 `0`

若仅发生 composite 内部 child-to-child 切换：

- composite state 的 timer 不重置

这与“状态驻留时间”的直觉一致。

## 5.4 effect 的归属

对于由 `after(...)` 触发的 source transition：

- 中间递归退出链不挂 effect
- 只有最终 source transition 挂 effect

否则 effect 会重复执行或在错误层级执行。

---

## 6. Leaf State 的 lowering

设原始 DSL 语义上存在：

```fcstm
A -> B : after(T);
```

且 `A` 是 stoppable leaf state。

### 6.1 合成变量

为 `A` 合成一个内部变量：

```text
__fcstm_after_A_ticks
```

如果同一个 source state `A` 上有多条 `after(...)` 转移，则它们共享同一个 timer 变量。

### 6.2 合成 enter 行为

在 `A.enter` 的内部展开中追加或前置：

```fcstm
__fcstm_after_A_ticks = 0;
```

推荐将其视为编译器内部逻辑，不暴露给用户 DSL 视图。

### 6.3 合成 during 行为

在 `A.during` 的尾部追加：

```fcstm
__fcstm_after_A_ticks = __fcstm_after_A_ticks + 1;
```

这里强调是 **尾部**，理由是：

- timeout 计时不应影响用户当前 cycle 内的业务动作
- 用户已有 `during` 逻辑应先执行
- timeout 计数更适合作为“本周期结束时完成一次推进”

### 6.4 转移 guard 化

原始：

```fcstm
A -> B : after(T);
```

lowering 后：

```fcstm
A -> B : if [__fcstm_after_A_ticks >= N];
```

如果原始语义还有 guard：

```fcstm
A -> B : after(T) if [cond];
```

则 lowering 为：

```fcstm
A -> B : if [(__fcstm_after_A_ticks >= N) && cond];
```

---

## 7. Composite State 的 lowering

设存在：

```fcstm
A -> B : after(T);
```

其中 `A` 是 composite state。

仅把该转移改成：

```fcstm
A -> B : if [timer >= N];
```

是不够的，因为当前 runtime 在 child 活跃时不会直接考虑父状态的转移。

因此必须合成一条 **递归退出链**。

### 7.1 合成变量

为 composite source `A` 合成内部 timer：

```text
__fcstm_after_A_ticks
```

同一个 composite source 上的多条 `after(...)` 共享该 timer。

### 7.2 合成 enter 行为

在 `A.enter` 内部展开中重置：

```fcstm
__fcstm_after_A_ticks = 0;
```

### 7.3 合成 aspect 行为

在 `A` 的 `>> during after` 尾部追加：

```fcstm
__fcstm_after_A_ticks = __fcstm_after_A_ticks + 1;
```

这里使用 `>> during after`，而不是普通 `during`，因为：

- composite 的普通 `during before/after` 只在进出 composite 边界时触发
- `>> during after` 会在任意后代叶子状态稳定活跃时每个 cycle 运行
- 尾部推进不干扰用户该 cycle 内的本地业务逻辑

### 7.4 合成最终 source transition

在 `A` 的父状态中，保留最终转移：

```fcstm
A -> B : if [__fcstm_after_A_ticks >= N];
```

若原始还有 guard，则合并为：

```fcstm
A -> B : if [(__fcstm_after_A_ticks >= N) && cond];
```

### 7.5 合成递归退出链

为了让当前活跃叶子能够一路退回到 `A`，需要对 `A` 的内部所有后代层级合成尾插的退出转移。

其本质效果等价于：

- 活跃叶子 `L -> [*] : if [timeout_guard]`
- 中间 composite `C -> [*] : if [timeout_guard]`
- 直到 `A -> B : if [timeout_guard]`

其中：

```text
timeout_guard = (__fcstm_after_A_ticks >= N) && original_guard
```

若没有原始 guard，则只保留 `__ticks >= N`。

### 7.6 为什么中间链路也要带完整 guard

中间退出链不能只判断 `__ticks >= N`，必须与最终 guard 保持一致。  
否则会出现：

- 子状态先被 timeout 链退出
- 但回到 `A` 之后最终 `A -> B` guard 又不满足
- 导致状态机停在错误层级或触发错误的后续逻辑

因此，整条 timeout 退出链必须共享同一套触发条件。

---

## 8. “低优先级 force transition” 的解释

从概念上看，composite timeout 的递归退出链确实很像一种“低优先级 force transition”。

但在实现上，不建议真的引入一个新的 force transition 语法类别。

更合理的做法是：

- 借用现有 force transition 的 **递归展开思路**
- 但不要复用现有 force transition 的 **前插优先级行为**
- timeout lowering 应该在每个相关 source 的转移列表末尾尾插

因此它更准确的名字应是：

- **propagated timeout exit chain**
- 或 **tail-expanded timeout transitions**

而不是新的运行时 force 机制。

---

## 9. 优先级与顺序规则

FCSTM 中不为 timeout 单独定义新优先级体系，而是完全复用现有顺序语义。

规则如下：

- 用户显式编写的普通 transition 优先
- 编译器合成的 timeout 相关 transition 尾插
- 多条 timeout transition 之间，保持原始 DSL 中的书写顺序

这会带来几个直接后果：

- 若 leaf state 自己有普通转移和 timeout-exit，则普通转移先尝试
- 若 composite state 父层有普通 `A -> X` 转移和 timeout 的 `A -> B`，则普通转移先尝试
- 若同一 source 上有多条 timeout 转移，按 DSL 顺序决定哪条先赢

这是最符合当前架构的做法，因为 runtime 本身就是“顺序选第一条满足条件的转移”。

---

## 10. 时间单位与折算

## 10.1 核心建议

核心语义建议只认：

- `cycle`
- `tick`

也就是：

```fcstm
after(5cycle)
after(3tick)
```

## 10.2 如果支持 `ms/s`

若 DSL 表面上允许：

```fcstm
after(100ms)
after(2s)
```

则必须要求存在固定 `cycle_time`。

折算公式应为：

```text
ticks = ceil(delay / cycle_time)
```

而不是直接整除。

示例：

- `delay = 100ms`
- `cycle_time = 20ms`
- `ticks = ceil(100 / 20) = 5`

若：

- `delay = 101ms`
- `cycle_time = 20ms`

则：

- `ticks = ceil(101 / 20) = 6`

这样才能保证“不早于设定超时”。

## 10.3 没有固定 `cycle_time` 时的约束

若运行环境没有固定 `cycle_time`，则以下两种做法必须二选一：

- 禁止 `ms/s` 写法，只允许 `tick/cycle`
- 或明确声明 `ms/s` 只是一种目标模板层面的便利写法，不属于 simulator/verify 的统一核心语义

推荐第一种。

---

## 11. 多条 `after(...)` 转移共享 timer 的规则

同一个 source state 上的多条 `after(...)` 应共享一个 timer。

例如：

```fcstm
A -> B : after(5cycle);
A -> C : after(10cycle);
```

其 lowering 不应生成两个 timer，而应是：

- 一个 `__fcstm_after_A_ticks`
- 两条不同阈值的 guard

即：

```fcstm
A -> B : if [__ticks >= 5];
A -> C : if [__ticks >= 10];
```

此时若在 `__ticks >= 10` 时两者都满足，则按声明顺序，`A -> B` 先赢。  
这是顺序语义的自然结果。

---

## 12. 与现有 runtime 行为的兼容性

此设计的优点是：

- runtime 无需理解新的 `after` 基础语义
- lowering 后仍然只是普通变量、动作、guard 和 transition
- verify 可以直接分析 lowering 后的模型
- generate 也只需面对普通模型对象

换句话说，`after(...)` 的复杂度被集中在：

- DSL 前端
- lowering 过程

而不是扩散到每个后端。

---

## 13. 与严格 UML time-event 的差异

本文方案明确 **不是** 严格 UML 的 time-event 语义。

几个关键差异如下：

- 本方案不是独立事件排队
- 本方案不是“一次性到点即丢弃”的触发
- 本方案是“状态驻留 tick 达阈值后，持续为真直到退出”的 guard-like 语义

这意味着它更接近：

- timeout condition
- dwell-time trigger

而不是经典 UML 中的 queued time event。

这不是缺陷，而是与 FCSTM 当前架构保持一致的有意识选择。

---

## 14. 对用户可见性的建议

虽然 `after(...)` 最终会被 lowering 成内部变量和内部转移，但这些内部对象不应直接污染用户视图。

建议：

- 内部变量统一使用保留前缀，如 `__fcstm_after_...`
- PlantUML 和文档导出优先显示原始 `after(...)`
- `simulate` 默认不要把内部 timer 当作普通业务变量高亮展示

否则，虽然技术上可行，但调试体验会显著变差。

这也意味着：

- 最好在前端或中间层保留 source-level 的 `after(...)` 元信息
- 到 simulate/generate/verify 之前再做 lowering

这里保留的是“编译期语法糖信息”，不等于引入新的运行时 time-event 实体。

---

## 15. 推荐的落地顺序

建议按如下顺序推进：

1. 先确定表面 DSL 语法
2. 明确 source state 的合法性规则
3. 明确 tick 语义和 `cycle_time` 折算规则
4. 先完成 leaf state 的 lowering
5. 再完成 composite state 的 propagated timeout exit chain lowering
6. 最后处理 PlantUML、round-trip、调试显示等体验问题

不建议一开始就直接改 runtime。

---

## 16. 最终设计摘要

本文最终建议可以浓缩为一句话：

> `after(...)` 在 FCSTM 中不是新的运行时事件，而是 source state 驻留时间达到阈值后的低优先级转移语法糖；leaf source 直接 guard 化，composite source 通过尾插式递归退出链实现。

具体化为：

- leaf source:
  - `enter` 重置 timer
  - `during` 尾部 `+1`
  - 最终转移 guard 化

- composite source:
  - `enter` 重置 timer
  - `>> during after` 尾部 `+1`
  - 最终 source transition guard 化
  - 内部递归合成尾插式 timeout 退出链

- pseudo source:
  - 禁止

这是当前 FCSTM 技术架构下最一致、最小侵入、最容易被各子系统复用的方案。
