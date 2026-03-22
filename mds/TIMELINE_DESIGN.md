# timeline 连续时间场景验证设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.3 | 2026-03-22 | 允许空 step 作为逻辑时间节点，删除长期演化相关铺垫，明确 timeline 只借用 fcstm 的语法与 model，不复用 simulate/verify | Codex |
| 0.1.2 | 2026-03-22 | 收紧外部输入设计：要求所有外部量显式给初始值，移除 `assume`，明确外部量在 fcstm 中按只读 environment input 处理 | Codex |
| 0.1.1 | 2026-03-22 | 扩展为任意多个状态机与广义互斥/禁配关系，移除“微步”设计，统一改为带顺序语义的 step | Codex |
| 0.1.0 | 2026-03-22 | 初始版本，定义 timeline 子系统的目标、问题边界、元模型、连续时间语义、SMT 编码方案与实施计划 | Codex |

---

## 1. 背景

当前 `pyfcstm` 已经有一套 `verify` 体系，其核心是：

- 基于 Z3 的符号约束传播
- 基于 BFS 的有界搜索
- 以 `cycle` 作为主要推进单位

这套机制适合处理：

- 有界可达性
- 基于离散步的状态空间搜索
- “若干 cycle 内能否到达某状态”这类问题

但它**不适合**下面这类问题：

- 时间是**连续时间**，不是 cycle
- 状态机本身是**事件驱动**的，而不是周期驱动
- 场景里给出的约束是“谁在谁前面”“两件事之间相隔多少秒”
- 总时长可能是几十秒、几百秒甚至更长
- 希望在**同一条外部时间线场景**下比较任意多个状态机模型

因此，这类问题不应继续挂在 `pyfcstm.verify` 下面硬扩，而应单开一个新的子系统，暂定命名为：

- `pyfcstm.timeline`

它的核心目标不是“搜索所有离散执行路径”，而是：

- 定义一条或一类**连续时间外部场景**
- 将多个状态机绑定到同一个场景上
- 检查某个状态组合约束是否可能被违反
- 如果可能，返回一条带时间戳的反例
- 如果不可能，给出基于 SMT 的不可满足性证明结论

---

## 2. 目标问题

## 2.1 问题表述

给定：

- 一组状态机模型 `M = {M_a, M_b, ...}`
- 一个共享的外部场景 `S`
- 一组状态约束关系 `R`

验证：

- 是否存在一个满足场景 `S` 的具体时间线实例，使得某个观测点上出现了 `R` 所禁止的状态组合

如果存在：

- 返回一条反例时间线

如果不存在：

- 证明在 `S` 允许的所有具体实例中，`R` 不会被违反

## 2.2 典型示例

例如：

- 外部量 `height` 完全由环境决定
- guard 中会出现 `height <= 2000`
- 场景中会出现：
  - 某个事件 `DescendCmd`
  - 某个时间点 `height` 更新为一个满足约束的值
  - 两个动作之间的时间差约束，例如 `5 <= dt <= 10`

验证目标可以是：

- 在同一个场景下，多个模型中的若干状态是否会形成一个被禁止的组合
- 或者一组状态谓词里是否会有超过允许数量的谓词同时成立

---

## 3. 为什么不能继续沿用 verify/BFS/cycle

## 3.1 连续时间与 cycle 不是一回事

现有 `verify` 将事件建模为：

- `(cycle, event_path)` 对应一个布尔变量

而 timeline 问题中需要的是：

- `time(event_i)` 是实数
- 事件之间的先后和间隔是约束的一部分

因此，`cycle` 已经不是合适的主轴。

## 3.2 总时长不应影响搜索复杂度

如果一个模型是纯事件驱动、没有内部定时器，那么：

- 1 秒和 100 秒之间，状态机本身并不会因为“时间流逝”而自动改变状态
- 真正重要的是“外部刺激发生了多少次”“输入在多少个点上发生变化”

因此，算法复杂度应当近似取决于：

- 场景中的**变化点数量**

而不是：

- 总共经过了多少秒

这与 BFS 按 cycle 展开是根本不同的。

## 3.3 该问题更像“共享时间线上的多机同步解释”

我们要做的不是：

- 搜索一个状态机在离散步空间里的所有可能路径

而是：

- 给定一条符号化时间线
- 将多个状态机都解释到这条时间线上
- 判断坏性质是否在某个观测点上成立

因此，更接近：

- bounded symbolic interpretation on a continuous-time scenario

而不是：

- bounded BFS reachability

---

## 4. 第一阶段问题边界

为了让该系统能真正落地，第一阶段必须显式收缩问题边界。

## 4.1 第一阶段支持的模型子集

建议第一阶段只支持下面这类状态机：

- 完全事件驱动
- 没有 concrete operation
- 没有 transition effect
- 没有 abstract handler 对验证语义产生影响
- guard 只读取外部输入变量
- 内部状态迁移不依赖内部可写变量
- 不包含基于时间流逝自动触发的机制

更具体地说，第一阶段**不支持**：

- `enter/during/exit` 中的 concrete operations
- `effect { ... }`
- 内部变量在迁移过程中被修改
- “停留 5 秒后自动转移”这类 timed transition
- state invariant / dwell time / clock reset
- 区间内连续演化的外部量微分语义

## 4.2 第一阶段支持的外部输入语义

建议第一阶段把外部输入建模为：

- **分段常值**
- **显式初始化**

也就是：

- 所有涉及到的外部量都必须在场景开始时给出初始值
- 外部变量只在显式的输入更新点发生变化
- 两个更新点之间保持不变

例如：

```text
t0: height = 2500
t1: emit DescendCmd
t2: height = 1800
```

则：

- 在 `[t0, t2)` 内，若没有其他更新，则 `height` 在各段上是常值

这样做的原因是：

- 初始环境在 `t0` 时必须是完全定义的
- guard 的真假变化点必须可定位
- 否则若只说“height 在 100 秒里连续下降”，那么 `height <= 2000` 究竟在哪一刻翻转，将把问题推进到 hybrid automata 范畴

第一阶段不建议碰这个复杂度。

第一阶段进一步建议：

- 外部量初始值必须是具体字面量
- 暂不支持“初始值是区间”或“初始值是符号约束”

## 4.3 第一阶段支持的验证目标

建议第一阶段只做：

- 多个模型在同一场景下的**状态组合约束验证**

第一阶段建议支持的约束类型至少包括：

- `at_most_one`
  - 一组状态谓词中，在任意观测点最多一个成立
- `forbidden_combination`
  - 某几个状态谓词不允许同时成立
- `pairwise_mutex_group`
  - 对一组状态谓词自动展开成两两互斥

可抽象为：

- `exists observation_point: forbidden_relation_holds(predicates_at_point)`

其中：

- 每个状态谓词都绑定到一个具体机器
- 状态可以是 leaf state
- 也可以是 composite state

当目标状态是 composite state 时，解释为：

- 当前稳定叶状态位于该 composite state 的子树中

---

## 5. timeline 子系统的定位

建议新增独立目录：

```text
pyfcstm/timeline/
```

与 `pyfcstm.verify` 并列，而不是嵌入 `verify`。

建议职责如下：

- `model.py`
  - timeline 场景元模型
- `binding.py`
  - 场景动作与状态机事件/输入的绑定关系
- `normalize.py`
  - 场景归一化、合法性检查、拓扑整理
- `compile.py`
  - 将状态机与场景编译为 SMT 约束
- `solve.py`
  - 求解与结果对象
- `witness.py`
  - 反例时间线与观测点重建
- `entry.py`
  - CLI/API 入口

这套设计的意义是：

- `verify` 仍然保留“符号 BFS + cycle”的主线
- `timeline` 明确代表“连续时间场景验证”
- `timeline` 只借用 fcstm 的 parser/model 表达语义，不借用其 simulate/verify 运行框架
- `timeline` 可以复用 `solver` 中的表达式转换与基础 Z3 能力

---

## 6. 核心语义

## 6.1 时间点与 step

建议采用：

- 一组有序的 `step_0, step_1, ..., step_n`
- 每个 `step_i` 绑定一个连续时间变量 `T_i`

这些 `T_i` 满足：

- `T_i in Real`
- `T_0 <= T_1 <= ... <= T_n`

这里需要注意：

- step 本身已经带有顺序语义
- 因此不需要再额外引入“微步”层
- 如果两个动作要表示“同一时刻但先后有序”，直接写成两个 step，并令：
  - `T_i = T_{i+1}`

例如：

```text
step_3 @ T3: set height = 1990
step_4 @ T4: emit GearDown
constraint: T3 = T4
```

这样已经足以表达：

- 两个动作发生在同一个连续时间点
- 但它们在场景里有明确顺序

## 6.2 稳定配置

一个 step 执行后，状态机应当被推进到一个**稳定配置**。

这里的“稳定配置”沿用现有层次状态机的直觉，但不再使用 cycle：

- 处理一次外部动作后
- 自动走完该动作直接诱发的 pseudo/init/hierarchy 内部闭包
- 最终停在一个可观测的稳定叶状态

需要注意：

- timeline 子系统可以复用现有 runtime/search 对层次状态机结构的理解
- 但不应复用其 `cycle` 语义

## 6.3 观测点

建议定义两类观测点：

- `post_step`
  - 每个 step 执行后立刻观察
- `open_interval`
  - 相邻 step 之间、且时间严格增加时的开区间 `(T_i, T_{i+1})`

对于第一阶段问题，如果状态机在时间流逝期间不会自动变化，则：

- 只要 step 结束时状态稳定
- 区间内状态与前一个 step 后的状态相同

因此状态组合约束检查可以统一转化为对以下切面检查：

- 每个 step 后的稳定状态
- 每个相邻 step 之间且 `T_i < T_{i+1}` 的区间状态

---

## 7. 场景元模型

## 7.1 总体对象

建议定义：

```python
@dataclass
class TimelineScenario:
    name: Optional[str]
    steps: List[TimelineStep]
    temporal_constraints: List[TemporalConstraint]
    input_domains: List[InputDomain]
```

## 7.2 步

```python
@dataclass
class TimelineStep:
    id: str
    time_symbol: str
    actions: List[TimelineAction]
```

其中：

- `time_symbol` 是这个 step 绑定的时间变量名
- step 在 `steps` 列表中的位置本身就定义了顺序
- 不再需要额外的 `order`
- `actions` 可以为空，表示这是一个纯逻辑时间节点

### 7.2.1 为什么一个 step 仍允许多个 actions

理论上可以把一个 action 就做成一个 step。

但保留 `actions: List[...]` 的好处是：

- 将来可以支持“这个 step 里同时施加多个输入更新”
- 文档结构更紧凑

不过第一阶段实现时，建议强约束为：

- 一个 step 可以没有任何 action
- 一个 step 内最多一个 `emit`
- 任意多个 `set`

允许空 step 的原因是：

- 某些时间点本身就是场景中的逻辑锚点
- 它们虽然不触发任何事件、也不更新输入
- 但仍然需要出现在约束里

例如：

```text
step_5 @ T5: <no actions>
constraint: 10 <= T5 - T2 <= 20
```

## 7.3 动作类型

建议第一阶段先分成两类：

```python
class TimelineAction: ...

@dataclass
class EmitEvent(TimelineAction):
    event_name: str

@dataclass
class SetInput(TimelineAction):
    input_name: str
    value: "InputExpr"
```

其中：

- `event_name` 是场景层名字，不直接等于状态机里的 event path
- `input_name` 也是场景层名字
- 真正如何映射到状态机由 binding 决定

第一阶段明确不引入 `AssumeInput`，原因是：

- 第一版更偏“显式输入轨迹”而不是“部分符号化输入轨迹”
- 这样反例更可读
- 也能避免 solver 自动补出太多用户未显式给定的环境值

## 7.4 时间约束

```python
@dataclass
class TemporalConstraint:
    left_time_symbol: str
    right_time_symbol: str
    min_delay: Optional[float]
    max_delay: Optional[float]
```

语义为：

- `min_delay <= T(right) - T(left) <= max_delay`

允许缺省一侧：

- 只有下界
- 只有上界
- 或两侧都有

## 7.5 输入域约束

为了避免外部输入完全无界，建议加入输入域约束：

```python
@dataclass
class InputDomain:
    input_name: str
    type: Literal['int', 'float', 'bool']
    initial_value: Union[bool, int, float]
    default_constraint: Optional["InputBoolExpr"]
```

例如：

- `height` 是 `float`
- 初始值为 `2500`
- 默认约束 `height >= 0`

这可以避免求解器拿到过于离谱的值。

---

## 8. 模型绑定

## 8.1 为什么需要 binding

场景中的名字是“环境层名字”，而状态机内部名字是“模型层名字”。

例如同一个现实动作“驾驶员按下开始按钮”，在两个模型中可能分别叫：

- `Aircraft.Start`
- `Controller.CmdStart`

如果不引入 binding，就无法表达：

- 同一个场景动作驱动两个模型的不同事件命名

## 8.2 建议的绑定结构

```python
@dataclass
class TimelineMachineBinding:
    machine_alias: str
    event_map: Dict[str, str]
    input_map: Dict[str, str]
```

其中：

- `event_map`
  - 场景事件名 -> 机器内完整 event path
- `input_map`
  - 场景输入名 -> 机器内 guard 中使用的变量名

如果两个模型的 guard 都直接使用 `height`，那映射可以是同名。

这里的 `input_map` 只是**名字绑定**，不是说这些量在模型内部就应被视为普通内部变量。对 timeline 而言，它们的语义应当是：

- 由场景提供
- 状态机只能读取
- 状态机不能写入

## 8.3 状态谓词与关系约束

建议显式引入“状态谓词”与“关系约束”这两层对象。

```python
@dataclass
class TimelineStatePredicate:
    machine_alias: str
    state_path: str

@dataclass
class TimelineRelationConstraint:
    kind: Literal['at_most_one', 'forbidden_combination', 'pairwise_mutex_group']
    predicates: List[TimelineStatePredicate]
```

这样之后，一个 query 就不再局限于“两台机器上一对状态”，而是可以表达：

- 某一组状态谓词里最多一个成立
- 某几个状态谓词不能同时成立
- 某一组状态谓词两两互斥

## 8.4 多机验证任务对象

```python
@dataclass
class TimelineConstraintQuery:
    machines: Dict[str, StateMachine]
    bindings: Dict[str, TimelineMachineBinding]
    scenario: TimelineScenario
    relations: List[TimelineRelationConstraint]
```

---

## 9. 连续时间语义

## 9.1 时间只约束场景，不直接驱动状态变化

第一阶段的关键语义收敛是：

- 时间流逝本身不会触发状态变化
- 状态变化只在 step 执行时发生

因此：

- 从 `T_k` 到 `T_{k+1}` 的 100 秒，不会导致额外的离散状态跳转
- 这 100 秒只影响场景是否合法，不影响离散步数量

这保证了：

- 复杂度与“场景变化点数”相关
- 而不是与“总秒数”相关

## 9.2 输入值的生效范围

建议语义为：

- `SetInput(x=v)` 在该 step 执行完成后生效
- 后续 step 可以看到新值
- 直到下一次 `SetInput(x=...)` 之前，该值保持不变

---

## 10. 状态机语义收敛

## 10.1 需要一个“单刺激闭包求值器”

timeline 不需要 cycle runtime，但需要一个新的基础能力：

- 给定一个稳定配置 `q`
- 给定一个输入快照 `u`
- 给定一个 step `s`
- 计算动作作用后的下一个稳定配置 `q'`

可记为：

- `step(machine, q, u, s) -> q'`

这里的 `s.actions` 可以包含：

- 空动作
- 输入更新
- 事件触发

但真正导致状态迁移的通常只有：

- `emit`

输入更新更多是为了改变 guard 所见环境。

## 10.2 外部值在 fcstm 状态机里的处理方式

语义上，timeline 中的外部值不应被当成普通内部变量，而应被视为：

- 只读的 `environment input`

也就是：

- 状态机可以在 guard 中读取这些值
- 这些值由场景在每个 step 上提供快照
- 状态机自身不能写这些值

因此，在 timeline 语义中，guard 求值时读取的不是“机器内部变量状态”，而是：

- 当前 step 对应的输入快照

工程上，第一阶段建议不要立刻修改主 `.fcstm` grammar，而是采取下面的落地方式：

1. 参与验证的模型继续使用现成的 `pyfcstm.model.StateMachine` 对象表达。
2. timeline 侧通过 `input_map` 指出哪些名字属于外部输入。
3. timeline 自己对 model 做静态检查，确保这些名字不会出现在任何写位置。
4. guard 求值时，将这些名字绑定到 timeline 当前切面的输入值。

这里的“写位置”至少包括：

- `effect` 左值
- `enter/during/exit` 中的赋值左值
- 未来若有其他可写 block，也应一并纳入检查

第一阶段由于本来就限制了无 concrete operation / 无 effect，因此这个检查会更简单。

## 10.3 为什么不复用 simulate/verify

现有 runtime 的问题不是“层次语义错了”，而是：

- 它把运行组织成 cycle
- `during` / stoppable / validation 都围绕 cycle 展开

timeline 第一阶段不需要这些。

因此本设计明确采用：

- 只借用 fcstm 的 parser 和 model object 表达状态机语义
- 不复用 `pyfcstm.simulate`
- 不复用 `pyfcstm.verify`
- timeline 自己实现“场景解释 + 模型检查 + SMT 编码”

## 10.4 第一阶段建议支持的迁移类型

由于第一阶段限制了模型子集，求值器主要需要处理：

- 初始闭包
- 事件触发的 transition
- guard 读取外部输入
- hierarchical entry/exit/pseudo/init 链

第一阶段中，如果发现模型包含以下内容，应直接拒绝：

- concrete enter/during/exit
- effect
- 依赖内部变量值的 guard

这样能显著降低语义不一致风险。

---

## 11. SMT 编码

## 11.1 总体思路

对一个给定的 timeline 场景，不做 BFS，而是直接建立一组符号变量和约束：

- 时间变量
- 输入快照变量
- 多个状态机在各观测切面的配置变量
- 状态转移一致性约束
- 坏性质约束

然后调用 Z3：

- `sat` 则构造反例
- `unsat` 则得到不可满足结论

## 11.2 时间变量

对每个 step `i` 对应的 `time_symbol` 创建：

- `T_i : Real`

基础约束：

- step 顺序约束
- 用户声明的 `min/max delay`

例如：

```text
0 <= T_t1 - T_t0
5 <= T_t2 - T_t0 <= 10
```

此外，对相邻 step 还需自动加入：

- `T_i <= T_{i+1}`

这样就把“step 有序，但时间可相等”的语义固定下来。

## 11.3 输入变量

对每个场景输入 `x`，在每个观测切面 `k` 上创建：

- `x_k`

其值由以下规则决定：

- 初始切面使用场景中显式给定的初始值，加上域约束
- `SetInput` 在相应 step 后更新到新表达式
- 之后按持久化语义向后传递

由于第一阶段取消了 `assume`，因此输入轨迹在结构上是完全显式的。

如果第一阶段只允许常量赋值，则编码会更简单。

建议 V1 限制：

- `SetInput` 的 `value` 只能是常量或简单符号字面量

## 11.4 状态变量

不要直接把完整 active stack 都做成显式 SMT 结构。

更实际的办法是：

- 先把状态机编译成有限个“稳定配置编号”
- 每个稳定配置编号对应一个稳定叶状态
- composite active 关系通过离线索引推导

于是可创建：

- `Q[m, k] : Int`

表示：

- 机器 `m` 在第 `k` 个观测切面时所在的稳定配置编号

## 11.5 迁移关系编码

第一阶段模型子集足够受限，因此可以将每个模型预编译为一个有限迁移表：

- 当前稳定配置
- 事件
- guard over inputs
- 下一个稳定配置

可形式化为：

```text
delta: (q, event, input_snapshot) -> q'
```

对每个触发事件的 step `k`，编码成：

- 如果当前配置是 `q`
- 且绑定后的对应事件是 `e`
- 且 guard 条件成立
- 则下一配置必须是某个 `q'`

由于 transition declaration order 在 pyfcstm 里是语义的一部分，因此编码要保留“前面优先”的选择语义。

可行实现是：

- 对当前配置的出边按声明顺序展开
- 第 `i` 条边的启用条件为：
  - 自己 guard 成立
  - 且前面所有边都不成立

这和现有 `verify/search.py` 中 `prev_conditions` 的思路一致，但这里不是 BFS，而是静态展开成约束。

## 11.6 输入更新步编码

若某个 step 只包含输入更新，不含事件，则：

- 对所有机器都有 `Q[m, k+1] = Q[m, k]`
- 只更新输入快照

这点非常关键，因为它让“输入先变化，再触发事件”可被精确表达。

## 11.7 坏性质编码

定义：

- `Pred(p, k)` 表示在切面 `k` 时，状态谓词 `p` 成立
- `Rel(r, k)` 表示在切面 `k` 时，关系约束 `r` 被违反

则坏性质为：

```text
Or_k Or_r Rel(r, k)
```

例如：

- `at_most_one(p1, p2, p3)` 可编码为真值和不超过 1
- `forbidden_combination(p1, p2, p3)` 可编码为 `p1 && p2 && p3`
- `pairwise_mutex_group(...)` 可展开为若干二元禁止组合

如果还要检查开区间，则对区间切面也建立对应谓词。

---

## 12. 反例输出

如果求解结果为 `sat`，建议输出：

- 每个 step 对应时间的具体值
- 每个 step 的动作
- 每个 step 后所有机器的稳定配置
- 每个输入变量在对应切面上的具体值
- 哪个观测点违反了哪条关系约束

建议定义：

```python
@dataclass
class TimelineCounterExample:
    time_values: Dict[str, float]
    steps: List[ConcreteTimelineStep]
    violation_observation_id: str
```

其中 `ConcreteTimelineStep` 应至少包含：

- 时间值
- step 标识
- 动作列表
- 各机器配置
- 输入快照

---

## 13. 对 DSL 的影响

## 13.1 第一阶段不修改主 `.fcstm` 语法

建议：

- 现有状态机 DSL 保持不动
- timeline 场景使用 sidecar 文件

原因：

- 一个状态机模型可能需要配多个不同场景
- 场景属于验证输入，不属于模型本体
- 这样可以避免把 timeline 语义污染进主 DSL grammar

## 13.2 场景文件格式建议

第一阶段建议优先采用：

- YAML

而不是立刻做新的 ANTLR DSL。

原因：

- 语义尚在收敛阶段
- YAML 更方便频繁修改字段结构
- CLI 与测试样例也更容易搭建

## 13.3 一个建议的 YAML 草案

```yaml
name: landing_conflict_check

inputs:
  - name: height
    type: float
    initial: 2500
    constraint: "height >= 0"

steps:
  - id: s0
    time: t0
    set:
      height: 2500

  - id: s1
    time: t1
    emit: descend_cmd

  - id: s2
    time: t2
    set:
      height: 1800
    emit: gear_down

  - id: s3
    time: t3
    actions: []

constraints:
  - "0 <= t1 - t0"
  - "5 <= t2 - t1 <= 20"
  - "1 <= t3 - t2 <= 3"

bindings:
  aircraft:
    event_map:
      descend_cmd: Aircraft.DescendCmd
      gear_down: Aircraft.GearDown
    input_map:
      height: height

  controller:
    event_map:
      descend_cmd: Controller.CmdDescend
      gear_down: Controller.CmdGearDown
    input_map:
      height: height

relations:
  - kind: forbidden_combination
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: controller
        state: Controller.HighSpeedCruise
```

这个格式不必一次定死，但它表达了第一阶段所需的核心信息。

---

## 14. API 与 CLI 建议

## 14.1 Python API

建议新增如下入口：

```python
def verify_timeline_constraints(
    machines: Dict[str, StateMachine],
    scenario: TimelineScenario,
    bindings: Dict[str, TimelineMachineBinding],
    relations: List[TimelineRelationConstraint],
) -> TimelineVerificationResult:
    ...
```

## 14.2 CLI

建议新增命令：

```bash
pyfcstm timeline \
    --machine aircraft=model_a.fcstm \
    --machine controller=model_b.fcstm \
    --scenario landing.yaml
```

后续可以扩展：

- `--format json`
- `--dump-smt2`
- `--show-counterexample`

---

## 15. 与现有模块的关系

## 15.1 直接借用的部分

- `pyfcstm.dsl`
  - 状态机解析
- `pyfcstm.model`
  - 状态、转换、事件、层次结构
- `pyfcstm.solver.expr`
  - 将 guard 转为 Z3
- `pyfcstm.solver.solve`
  - 求解与解枚举

## 15.2 timeline 自己实现的部分

- 连续时间场景元模型
- 场景归一化
- timeline 专用配置求值器
- 多机绑定与反例重建

## 15.3 明确不复用的部分

- `pyfcstm.verify.search`
- `pyfcstm.simulate.runtime`

原因是：

- 它们的主语义中心是 `cycle`
- timeline 问题的主轴是“step + 连续时间约束 + 场景约束”
- 本需求只想借用 fcstm 的语法与 model 表达语义，不想被现有 simulate/verify 的实现框架牵着走

---

## 16. 实施计划

## 16.1 第一阶段：文档与问题收敛

目标：

- 固化第一阶段问题边界
- 确认场景语义
- 确认 YAML 草案

输出：

- 本文档
- 若干示例场景

## 16.2 第二阶段：只做元模型与归一化

目标：

- 创建 `pyfcstm.timeline.model`
- 创建 `pyfcstm.timeline.normalize`
- 实现 YAML -> dataclass
- 校验：
  - `time_symbol` 存在性
  - binding 完整性
  - relation 中目标状态存在性

这一阶段先不碰 SMT。

## 16.3 第三阶段：实现单机“单刺激闭包求值器”

目标：

- 对第一阶段支持的状态机子集
- 给定稳定配置、输入快照、step
- 计算下一个稳定配置

要求：

- 显式拒绝不支持的 DSL 特性
- 保持 transition declaration order 语义
- 支持 hierarchy / init / pseudo 闭包

这是整个 timeline 的关键基础。

## 16.4 第四阶段：实现多机 SMT 编码

目标：

- 把 scenario + bindings + 多台状态机编译成 Z3 约束
- 实现关系约束违规编码
- 返回 sat / unsat

这一阶段先不追求最强泛化，只追求：

- 在第一阶段问题边界内稳定工作

## 16.5 第五阶段：实现反例重建与 CLI

目标：

- 从 solver model 重建时间点取值
- 重建每一步输入快照
- 重建所有机器的稳定配置序列
- 输出可读反例

## 16.6 第六阶段：测试与样例

建议至少覆盖：

- 同一时刻但不同 step 顺序导致不同结果
- 时间约束可满足与不可满足
- 多机同场景禁配关系可达
- 多机同场景禁配关系不可达
- binding 名称不同但语义相同
- composite state 目标判断
- 输入更新但无事件时状态保持不变

---

## 17. 需要注意的点

## 17.1 “外部输入变量”与现有 `def` 变量的语义重叠

当前 DSL 中的变量更偏“状态机内部变量”。

但 timeline 场景里的 `height` 等量，语义上更像：

- environment input

这个需求当前不追求长期演化，因此第一阶段直接采用：

- 用现有 fcstm model object 承载语义
- 由 timeline 侧通过 binding 和静态检查把这些名字解释成只读 environment input

不在本次需求中继续展开 DSL 层面的长期演进设计。

## 17.2 外部输入必须显式初始化

如果不要求所有外部量在场景开始时给初始值，会直接带来：

- 初始环境不完整
- solver 自由补值
- 反例可解释性下降

因此第一阶段应当把“显式初始值”设为硬规则。

## 17.3 稳定配置的定义必须严谨

如果对 pseudo/init/hierarchy 闭包的终点定义不清晰，会直接导致：

- 状态编号不稳定
- 两次求值结果不一致
- 反例不可解释

因此第三阶段实现前，应先把“稳定配置”定义写成更严格的小文档或注释规范。

---

## 18. 当前建议结论

当前建议是：

1. 将此类问题独立为 `pyfcstm.timeline`，不要放在 `verify` 下。
2. 第一阶段只支持“纯事件驱动 + 无内部写变量 + guard 只读外部输入 + 分段常值输入”的子集。
3. 时间采用“有序 step + 连续时间变量 + 相邻 step 自动满足 `T_i <= T_{i+1}`”的语义。
4. 不按秒展开，也不按 cycle 展开，而是按场景变化点建立 SMT 约束。
5. 所有外部量都必须显式给出初始值，第一阶段不引入 `assume`。
6. 外部量在语义上按只读 environment input 处理，工程上先由 timeline 侧通过 binding 和静态检查实现。
7. 允许空 step 作为纯逻辑时间节点存在，并参与时间约束。
8. 只借用 fcstm 的语法与 model object，不复用 simulate/verify 的运行与验证框架。
9. 先用 YAML sidecar 描述场景，不急着修改主 DSL。
10. 先把“多机状态组合约束验证”做实，不为长期演化额外铺垫。

---

## 19. 下一步讨论建议

继续讨论时，建议优先收敛下面几个问题：

1. 第一阶段是否允许模型中存在 `enter/during/exit abstract` 但在 timeline 中忽略它们。
2. `SetInput` 的值是否允许引用其他输入变量，还是先限制为常量。
3. 同一 step 内是否允许同时 `set` 和 `emit`，以及是否需要固定内部执行顺序。
4. 空 step 在 YAML 里是统一写成 `actions: []`，还是允许完全省略动作字段。
5. 目标状态若是 composite state，是否统一采用“当前稳定叶状态属于其子树”语义。
6. 场景文件是否要从第一版开始支持多个 relation 与多个 query。
