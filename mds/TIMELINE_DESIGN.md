# timeline 连续时间场景验证设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.15 | 2026-03-31 | 补充 `model1.xml` 的最小修改建议：新增 `model1_fixed.xml` 所需的顺序图观测 diff，并把 Phase11 示例查询同步到实际可共存的 `region2.L/X` | Codex |
| 0.1.14 | 2026-03-29 | 补回 Phase 9-11 的完整可运行示例代码到文档：覆盖 phase9 output family、phase10 scenario 摘要与 phase11 单条共存时间轴表输出 | Codex |
| 0.1.13 | 2026-03-29 | 收紧 `TimeConstraint` 语义：不再表述为 step-local time window，而统一收敛为带左端点的二元 duration 约束；补充真实样例中 `s02 -> s03`、`s06 -> s07` 的解释 | Codex |
| 0.1.12 | 2026-03-29 | 同步 Phase 7-8 实施进度：补齐 timeline-first import IR、input/event binding 候选、step/SetInput/emit 候选与真实样例验证结果，并更新 checklist 状态 | Codex |
| 0.1.11 | 2026-03-29 | 同步 Phase 5-6 实施进度：补齐真实样例上的 interaction observation stream、统一 trigger 视图与名字归一化提示，并更新 checklist 状态 | Codex |
| 0.1.10 | 2026-03-29 | 同步 Phase 1-4 实施进度：补齐 `doActivity -> during abstract` 与原始 XMI 索引层，并更新 checklist 状态 | Codex |
| 0.1.9 | 2026-03-29 | 补充无条件普通转移的连续时间处理：按最近后继 `emit` 约束隐藏内部迁移时刻，并引入 `delta` 序列建模方向 | Codex |
| 0.1.8 | 2026-03-29 | 按真实样例补充顺序图消息方向过滤规则，明确只把外向内消息当作 `emit`，并新增状态机主干的 pyfcstm DSL 草案与方向冲突说明 | Codex |
| 0.1.7 | 2026-03-29 | 结合真实 SysDeSim 样例补充 timeline-first 落地计划，新增 XMI 解析、条件触发抽象、顺序图观测提取、binding/scenario 生成与 phased checklist | Codex |
| 0.1.6 | 2026-03-22 | 收敛状态推导实现方案：有限复用 `SimulationRuntime` 作为单步状态迁移推导器，通过默认空 cycle 求初始稳定状态，通过热启动 + 单次 cycle 求后继稳定状态 | Codex |
| 0.1.5 | 2026-03-22 | 补充完整示例：多机 fcstm DSL、timeline YAML，以及不同关系类型下的预期 SAT/UNSAT 结果 | Codex |
| 0.1.4 | 2026-03-22 | 扩充形式化验证算法细节，补充 timeline 约束生成流程与 Python/Z3 编码骨架 | Codex |
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
- `T_0 >= 0`
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
    observation_scope: Literal['post_step', 'open_interval', 'both'] = 'both'
```

这样之后，一个 query 就不再局限于“两台机器上一对状态”，而是可以表达：

- 某一组状态谓词里最多一个成立
- 某几个状态谓词不能同时成立
- 某一组状态谓词两两互斥
- 并且可以显式指定是在：
  - `post_step`
  - `open_interval`
  - 或两者都检查

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

- 每个 step 先继承上一时刻的输入快照
- 再把该 step 内的所有 `SetInput` 应用到当前时间点的输入快照上
- 该 step 的 guard 求值和事件处理看到的是这个更新后的输入快照
- step 执行完成后的输入快照等于这个更新后的输入快照
- 直到下一次 `SetInput(x=...)` 之前，该值保持不变

也就是说：

- `SetInput` 是这个时间点发生的环境变化
- 它对这个 step 的状态迁移判定立即可见
- 而不是必须等到下一个 step 才可见

---

## 10. 状态机语义收敛

## 10.1 需要一个“单刺激闭包求值器”

timeline 不需要把 `simulate` 当成主执行框架，但确实需要一个基础能力：

- 给定一个稳定配置 `q`
- 给定一个输入快照 `u`
- 给定一个 step `s`
- 计算动作作用后的下一个稳定配置 `q'`

可记为：

- `step(machine, q, u, s) -> q'`

本设计现在不打算手写这一整套闭包求值逻辑，而是采用一个更务实的实现方案：

- 使用 `pyfcstm.simulate.runtime.SimulationRuntime`
- 但只把它当成“单步状态迁移推导器”
- 不复用它的长期运行实例，不复用 REPL/batch，不复用 cycle 计数语义

具体做法是：

1. 初始稳定配置求解
   - 创建默认初始化的 `SimulationRuntime(machine)`
   - 执行一次空 `cycle()`
   - 读取 `runtime.current_state` 与 `runtime.vars`
2. 后继稳定配置求解
   - 已知上一个时间点后的稳定状态路径 `q_prev`
   - 已知上一个时间点后的变量快照 `vars_prev`
   - 先把本 step 的 `SetInput` 应用到 `vars_prev`，得到 `vars_step`
   - 再创建新的 `SimulationRuntime(machine, initial_state=q_prev, initial_vars=vars_step)`
   - 将本 step 绑定后的事件列表传给 `cycle(events)`
   - 读取新的 `runtime.current_state` 与 `runtime.vars`

因此 runtime 在 timeline 里的角色不是“运行整个时间线”，而是：

- 每次都从一个已知稳定边界热启动
- 只跑一个 step 对应的一次 `cycle()`
- 读出结果后立刻丢弃 runtime 对象

这里的 `s.actions` 可以包含：

- 空动作
- 输入更新
- 事件触发

在当前语义下：

- 输入更新先形成该时间点的环境快照
- 事件在这个快照上参与本次 `cycle()` 的转移选择

因此即使 step 没有事件，只有输入变化：

- 也仍然需要执行一次 `cycle()`
- 因为 guard-only transition 可能会在新的输入快照下发生

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
4. 在 timeline 实现里，把这些外部输入值并入 runtime 的 `initial_vars` 快照。
5. guard 求值时，由 runtime 按正常变量读取路径看到这些值。

这里的“写位置”至少包括：

- `effect` 左值
- `enter/during/exit` 中的赋值左值
- 未来若有其他可写 block，也应一并纳入检查

第一阶段由于本来就限制了无 concrete operation / 无 effect，因此这个检查会更简单。

## 10.3 为什么只有限复用 simulate.runtime，而不复用 simulate/verify 框架

现有 runtime 的问题不是“层次语义错了”，而是：

- 它的主要组织方式是长生命周期 `cycle` 执行
- REPL/batch/simulate 的用户模型也是“不断前进的运行时实例”
- `verify` 则是另一套以搜索为中心的框架

timeline 不需要这些大框架，但可以务实地借 runtime 做一件事：

- 从一个已知稳定配置和变量快照出发
- 推导“本 step 之后的下一个稳定配置”

因此本设计明确采用：

- 借用 fcstm 的 parser 和 model object 表达状态机语义
- 不复用 `pyfcstm.verify`
- 不复用 `pyfcstm.simulate` 的 REPL / batch / 长生命周期运行模式
- 仅有限复用 `pyfcstm.simulate.runtime.SimulationRuntime` 作为一次性单步状态推导器
- timeline 自己负责“场景解释 + 多机绑定 + 区域化 + SMT 编码 + 反例重建”

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

对一个给定的 timeline 场景，不做 BFS，而是先做两层分工：

1. 离散状态推导层
   - 按 step 顺序，利用 `SimulationRuntime` 逐步推导每台机器在各个 `post_step` 切面上的稳定状态与变量快照
   - 这一步是具体执行，不是 SMT 求解
2. 连续时间约束层
   - 对时间变量、区间是否存在、关系是否在同一区域命中等内容建立 Z3 约束
   - 这一步才交给求解器

然后调用 Z3：

- `sat` 则构造反例
- `unsat` 则得到不可满足结论

在当前第一阶段约束下，由于：

- step 顺序固定
- `SetInput` 值是显式的
- 外部输入初始值是显式的
- 时间流逝本身不会触发离散迁移

所以每台机器的离散状态轨迹实际上可以先被具体推导出来，SMT 主要负责：

- 时间约束是否可满足
- 哪些 `open_interval` 真实存在
- 某些关系是否在同一个时间区域上被同时命中

## 11.1.1 形式化验证目标

在第一阶段问题边界内，可以把整个问题写成一个“两段式”有限问题：

- 已知：
  - 有限个 step
  - 有限个外部输入
  - 有限个状态机
  - 每个状态机在该场景下可被 runtime 具体推导出的稳定状态序列
- 求：
  - 是否存在一组时间取值
  - 使得所有场景约束都成立
  - 且某个关系约束在某个观测点被违反

因此，验证问题可以归约为：

```text
Exists time_values :
    ScenarioConstraints
    and PrecomputedMachineOccupancy
    and RelationViolation
```

其中：

- `PrecomputedMachineOccupancy`
  - 不是由 solver 搜索出来的
  - 而是 timeline 在进入 SMT 前，通过 runtime 前向解释得到的离线事实

也就是说，第一阶段更准确地说是：

- “离散状态前向解释 + 连续时间 SMT 判定”

如果结果为：

- `sat`
  - 存在反例时间线
- `unsat`
  - 在当前场景模板允许的全部具体实例下，关系约束都不会被违反

## 11.1.2 不做搜索树，而做一次性约束展开

这里的关键设计选择是：

- **不做 BFS**
- **不做 DFS**
- **不按秒枚举**
- **不按 cycle 推进**

而是：

- 先把场景长度固定为 `N = len(steps)`
- 先前向解释出每个机器在各 `post_step` 切面上的稳定配置
- 再把时间与区域相关部分一次性展开成约束

所以它更接近：

- bounded timed consistency checking

而不是：

- symbolic graph exploration

## 11.1.3 整体算法流程

建议把实现拆成下面 8 个阶段：

1. 解析 `.fcstm`，得到 `StateMachine` model object。
2. 对所有机器做支持子集检查。
3. 归一化 scenario YAML，得到有序 `steps`、输入定义、时间约束、bindings、relations。
4. 使用 runtime 逐步推导每个机器在各 `post_step` 切面上的稳定状态与变量快照。
5. 基于这些离散状态结果，离线计算各状态谓词的命中区域。
6. 创建 Z3 变量：
   - 时间变量
   - 区间存在性相关布尔条件
   - 关系命中布尔量
7. 生成场景约束：
   - 时间约束
   - 必要时的输入一致性约束
8. 生成关系违规约束并调用求解器。

这 8 步里，第 4 步和第 8 步是实现核心。

需要说明的是：

- 下文 `11.2` 到 `11.8` 里仍然保留了一套更一般的 SMT 编码草图
- 这套草图适合将来需要把更多内容也做成符号变量时参考
- 但对当前第一阶段实现，优先推荐的路径是：
- 先用 runtime 预解释出离散状态轨迹
- 再把时间与区域关系交给 Z3

## 11.1.4 Python/Z3 顶层骨架

下面是一版建议的顶层结构，目的是把“约束在什么阶段加入 solver”讲清楚：

```python
import z3


def verify_timeline_constraints(query: TimelineConstraintQuery):
    solver = z3.Solver()

    compiled = compile_timeline_problem(query)

    solver.add(*compiled.time_constraints)
    solver.add(*compiled.input_constraints)
    solver.add(*compiled.machine_constraints)
    solver.add(compiled.violation_constraint)

    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        return build_counterexample(compiled, model)
    elif result == z3.unsat:
        return build_unsat_result(compiled)
    else:
        return build_unknown_result(compiled)
```

其中 `compile_timeline_problem()` 不应该只是“做一点点拼装”，而应该负责：

- 完整预处理
- 全量变量创建
- 全量约束构建
- 形成一个可以直接 `solver.add(...)` 的编译结果对象

## 11.1.5 用“时间占据集合”定义验证问题

前面那套说法还是偏编译实现。站在验证逻辑本身，这个问题其实可以更直接地定义成：

- 时间序列的先后顺序已经由 scenario 固定
- 我们要做的不是“搜索下一步”
- 而是对每个状态机、每个待观察状态，求它在整条时间线上可能占据哪些时间点/时间段

也就是先求一个“时间占据集合”。

设 scenario 一共有 `n` 个 step，它们的时间变量满足：

```text
T_0 <= T_1 <= ... <= T_n
```

则全局时间线天然被切成有限个原子区域：

1. 离散观测点
   - `post_step(s_i)`
   - 表示第 `i` 个 step 执行完成后的离散切面
2. 连续开区间
   - `(T_i, T_{i+1})`
   - 只有 `T_i < T_{i+1}` 时该区间才真实存在

在当前问题子集中：

- 状态机不会因为纯时间流逝自动跳转
- 状态只会在 step 边界发生离散变化

因此：

- 每个开区间内部，状态恒定
- 某个状态机处于某个状态的时间集合，一定可以表示成有限个离散点和有限个区间的并集

记：

- `Occ(m, P)` 表示状态机 `m` 满足状态谓词 `P` 的时间占据集合

那么 `Occ(m, P)` 的形式一定类似：

```text
Occ(m, P) =
    {post_step(s1), post_step(s4)}
    U (T1, T2)
    U (T4, T5)
```

如果只关心连续时间见证，也可以把它理解成：

```text
t_m in [T1, T2] or [T4, T5]
```

这里把离散点也折叠进闭区间端点中只是为了直观，严格实现时仍然建议区分：

- `post_step`
- `open_interval`

因为这两类观测范围在语义上不同。

## 11.1.6 从单个状态机的时间占据集合，到多状态机关系验证

有了 `Occ(m, P)` 之后，性质验证本身就很直接了。

### 11.1.6.1 两个状态是否可能同时出现

对两个状态机 `sm1`、`sm2` 和两个状态谓词 `P1`、`P2`：

```text
Exists t :
    t in Occ(sm1, P1)
    and t in Occ(sm2, P2)
```

这和你说的写法是同一个意思：

```text
Exists t_sm1, t_sm2 :
    t_sm1 in Occ(sm1, P1)
    and t_sm2 in Occ(sm2, P2)
    and t_sm1 == t_sm2
```

也就是：

- 先求 `sm1` 落在什么时间段
- 再求 `sm2` 落在什么时间段
- 最后检查这两边是否存在同一个时间点可以同时满足

如果存在：

- `sat`
- 这个共同时间点就是反例见证

如果不存在：

- `unsat`

### 11.1.6.2 更一般的多状态机、多谓词性质

推广到任意多个状态机、任意多个状态谓词，核心也没变，还是“同一时刻上的联合可满足性”。

例如：

- `forbidden_combination`

  ```text
  Exists t :
      t in Occ(m1, P1)
      and t in Occ(m2, P2)
      and ...
      and t in Occ(mk, Pk)
  ```

- `at_most_one`

  ```text
  Exists t :
      count_true(
          t in Occ(m1, P1),
          t in Occ(m2, P2),
          ...
      ) >= 2
  ```

- `pairwise_mutex_group`

  ```text
  Exists t, i, j :
      i != j
      and t in Occ(mi, Pi)
      and t in Occ(mj, Pj)
  ```

所以从验证本质上看，整个问题就是：

- 先为每个状态谓词求时间占据集合
- 再检查这些集合在同一个时间点上的交、计数或组合条件

## 11.1.7 为什么实现时不必真的引入 `t_sm1`、`t_sm2`

虽然上面的数学定义可以直接写成多个见证时间变量：

- `t_sm1`
- `t_sm2`
- `t_sm3`

但实现时没必要真的这么做。

原因很简单：

- 所有状态机共享同一条全局 timeline
- 这条 timeline 已经被 `T_0, T_1, ..., T_n` 切成了有限个原子区域

因此：

- “存在某个共同时间点 `t` 同时落在多个时间占据集合里”
- 等价于
- “存在某个全局原子区域 `R`，使得这些状态谓词都在 `R` 上成立”

也就是说，求：

```text
Occ(sm1, P1) ∩ Occ(sm2, P2) != empty
```

在实现上可以转化为：

```text
Exists region R :
    Holds(sm1, P1, R)
    and Holds(sm2, P2, R)
```

这里的 `R` 可以是：

- `post_step(s_i)`
- `(T_i, T_{i+1})`

这就是“时间集合求交”和“逐区域检查”之间的精确对应关系。

## 11.1.8 从“时间集合求交”到“逐区域检查”的具体算法

基于上面的等价关系，算法可以明确写成下面几步。

### 第 1 步：由时间序列切出全局原子区域

假设 scenario 有 `n` 个 step，则可得到：

- `n` 个 `post_step(s_i)`
- `n - 1` 个候选开区间 `(T_i, T_{i+1})`

其中候选开区间只有在 `T_i < T_{i+1}` 时才存在。

### 第 2 步：对每个状态机求每个区域上的稳定状态

对每个状态机 `m`：

1. 从初始配置开始
2. 依次按照 step 顺序处理 `s_0, s_1, ..., s_n`
3. 得到每个 `post_step(s_i)` 上机器的稳定配置 `Q[m, i]`

因为在当前问题子集中：

- 区间内没有自动跳转

所以 `(T_i, T_{i+1})` 上的稳定配置直接等于：

```text
Q_interval[m, i] = Q_post[m, i]
```

前提是该区间真实存在，即 `T_i < T_{i+1}`。

### 第 3 步：把状态配置翻译成状态谓词的时间占据集合

对某个状态谓词 `P`，例如：

- `machine_alias = aircraft`
- `state_path = /Aircraft/GearLowering`

我们离线算出：

- 哪些稳定配置编号满足这个谓词

于是就能在每个区域上构造布尔值：

```text
Holds(m, P, post_step(s_i))
Holds(m, P, interval_i)
```

把所有使 `Holds(...)` 为真的区域收集起来，就得到了：

```text
Occ(m, P)
```

如果用户更习惯“时间变量落在哪些区间里”的表述，也可以把它解释成：

```text
t_m in UnionOfIntervals(m, P)
```

只是实现里不会真的单独生成这个 `t_m`。

### 第 4 步：在同一区域上检查关系是否被违反

对每条关系 `Rel` 和每个全局区域 `R`：

- 先算出关系里每个状态谓词在 `R` 上是否成立
- 再按关系类型拼出违规条件

例如：

- `forbidden_combination`
  - `Violation(Rel, R) = And(Holds(P1, R), Holds(P2, R), ..., Holds(Pk, R))`
- `at_most_one`
  - `Violation(Rel, R) = Sum(If(Holds(Pi, R), 1, 0)) >= 2`
- `pairwise_mutex_group`
  - `Violation(Rel, R) = Or(And(Holds(Pi, R), Holds(Pj, R)) for i < j)`

### 第 5 步：把“存在某个共同时间点”落实成 SMT 公式

由于“共同时间点存在”已经被有限区域化，所以最终只需要：

```text
Exists region R :
    Violation(Rel, R)
```

在 Z3 里直接展开成：

```text
Or(
    Violation(Rel, post_step(s0)),
    Violation(Rel, interval_0),
    Violation(Rel, post_step(s1)),
    ...
)
```

这和显式引入：

- `t_sm1`
- `t_sm2`
- `t_sm1 == t_sm2`

在逻辑上是等价的，但编码规模更小，也更直接。

### 第 6 步：对应的 Python/Z3 直接写法

如果把上面的逻辑翻译成 Python/Z3，骨架其实很直接：

```python
import z3


def build_relation_violation_over_regions(compiled, relation):
    region_violations = []

    for region in compiled.regions:
        predicate_holds = []
        for pred in relation.predicates:
            machine_alias = pred.machine_alias
            state_path = pred.state_path
            holds = build_predicate_holds_in_region(
                compiled=compiled,
                machine_alias=machine_alias,
                state_path=state_path,
                region=region,
            )
            predicate_holds.append(holds)

        if relation.kind == 'forbidden_combination':
            region_violations.append(z3.And(*predicate_holds))
        elif relation.kind == 'at_most_one':
            region_violations.append(
                z3.Sum([z3.If(item, z3.IntVal(1), z3.IntVal(0)) for item in predicate_holds]) >= 2
            )
        elif relation.kind == 'pairwise_mutex_group':
            pair_terms = []
            for i in range(len(predicate_holds)):
                for j in range(i + 1, len(predicate_holds)):
                    pair_terms.append(z3.And(predicate_holds[i], predicate_holds[j]))
            region_violations.append(z3.Or(*pair_terms) if pair_terms else z3.BoolVal(False))
        else:
            raise ValueError(f'Unsupported relation kind: {relation.kind!r}')

    return z3.Or(*region_violations) if region_violations else z3.BoolVal(False)
```

这里最关键的不是 `z3.And` / `z3.Or` 这些表面写法，而是：

- `compiled.regions`
  - 已经是由全局时间序列切好的有限区域
- `build_predicate_holds_in_region(...)`
  - 本质上就是在回答：
  - “这个状态谓词是否属于该机器的时间占据集合，并且命中了当前区域”

换句话说，这段代码对应的正是你说的那条主线：

1. 先算每台机器、每个状态谓词在哪些时间段上可能成立
2. 再看不同机器这些时间段能不能在同一个时刻对齐
3. 如果能对齐，就得到 `sat`
4. 如果所有区域都对不齐，就得到 `unsat`

## 11.2 时间变量

对每个 step `i` 对应的 `time_symbol` 创建：

- `T_i : Real`

基础约束：

- 首个时间点非负
- step 顺序约束
- 用户声明的 `min/max delay`

例如：

```text
0 <= T_t1 - T_t0
5 <= T_t2 - T_t0 <= 10
```

此外，对相邻 step 还需自动加入：

- `T_0 >= 0`
- `T_i <= T_{i+1}`

这样就把：

- 时间不允许为负
- step 有序，但时间可相等

这两层语义都固定下来。

## 11.2.1 时间变量的 Python/Z3 表达

建议把每个 `time_symbol` 映射到一个 `z3.Real`：

```python
def build_time_vars(scenario: TimelineScenario) -> dict[str, z3.ArithRef]:
    time_vars = {}
    for step in scenario.steps:
        if step.time_symbol not in time_vars:
            time_vars[step.time_symbol] = z3.Real(step.time_symbol)
    return time_vars
```

相邻 step 的顺序约束：

```python
def build_monotonic_time_constraints(scenario, time_vars):
    constraints = []
    if scenario.steps:
        constraints.append(time_vars[scenario.steps[0].time_symbol] >= z3.RealVal('0'))
    for left, right in zip(scenario.steps, scenario.steps[1:]):
        constraints.append(time_vars[left.time_symbol] <= time_vars[right.time_symbol])
    return constraints
```

用户声明的时间差约束：

```python
def build_temporal_constraints(scenario, time_vars):
    constraints = []
    for item in scenario.temporal_constraints:
        dt = time_vars[item.right_time_symbol] - time_vars[item.left_time_symbol]
        if item.min_delay is not None:
            constraints.append(dt >= z3.RealVal(str(item.min_delay)))
        if item.max_delay is not None:
            constraints.append(dt <= z3.RealVal(str(item.max_delay)))
    return constraints
```

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

## 11.3.1 输入快照索引

建议把“第 `k` 个观测切面的输入值”做成显式变量。

如果场景一共有 `N` 个 step，则第一阶段最简单的索引方案是：

- `k = 0..N`
- `k=0` 表示任何 step 执行前的初始快照
- `k=i+1` 表示 `step_i` 执行后的快照

这样输入轨迹和配置轨迹都可以共用同一个切面索引。

## 11.3.2 输入变量的 Python/Z3 表达

```python
def make_input_var(name: str, index: int, typ: str):
    if typ == 'int':
        return z3.Int(f'{name}__k{index}')
    elif typ == 'float':
        return z3.Real(f'{name}__k{index}')
    elif typ == 'bool':
        return z3.Bool(f'{name}__k{index}')
    else:
        raise ValueError(f'Unsupported input type: {typ}')


def build_input_snapshot_vars(scenario: TimelineScenario):
    num_cuts = len(scenario.steps) + 1
    vars_by_name = {}
    for item in scenario.input_domains:
        vars_by_name[item.input_name] = [
            make_input_var(item.input_name, k, item.type)
            for k in range(num_cuts)
        ]
    return vars_by_name
```

初始值与域约束：

```python
def build_initial_input_constraints(scenario, input_vars):
    constraints = []
    for item in scenario.input_domains:
        x0 = input_vars[item.input_name][0]
        init = item.initial_value
        if item.type == 'bool':
            constraints.append(x0 == z3.BoolVal(bool(init)))
        elif item.type == 'int':
            constraints.append(x0 == z3.IntVal(int(init)))
        elif item.type == 'float':
            constraints.append(x0 == z3.RealVal(str(init)))
        if item.default_constraint is not None:
            # 这里的 parse_input_constraint_to_z3 需要把名字绑定到 k=0 快照
            constraints.append(parse_input_constraint_to_z3(item.default_constraint, {
                name: input_vars[name][0] for name in input_vars
            }))
    return constraints
```

## 11.3.3 `set` 的传播算法

设 `step_i` 执行前快照为 `Input[:, i]`，执行后快照为 `Input[:, i+1]`。

那么每个输入名 `x` 都满足：

- 如果 `step_i` 对 `x` 有 `set`，则 `x_{i+1} = assigned_value`
- 否则 `x_{i+1} = x_i`

Python/Z3 可直接写成：

```python
def build_step_input_constraints(scenario, input_vars):
    constraints = []

    for i, step in enumerate(scenario.steps):
        assigned = {}
        for action in step.actions:
            if isinstance(action, SetInput):
                assigned[action.input_name] = action.value

        for input_name, snapshots in input_vars.items():
            before = snapshots[i]
            after = snapshots[i + 1]
            if input_name in assigned:
                value = assigned[input_name]
                if isinstance(value, bool):
                    constraints.append(after == z3.BoolVal(value))
                elif isinstance(value, int):
                    constraints.append(after == z3.IntVal(value))
                elif isinstance(value, float):
                    constraints.append(after == z3.RealVal(str(value)))
                else:
                    raise ValueError(f'Unsupported set value: {value!r}')
            else:
                constraints.append(after == before)

    return constraints
```

空 step 在这里天然成立：

- 没有任何 `set`
- 所以所有输入都自动满足 `after == before`

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

## 11.4.1 为什么用“稳定配置编号”

直接把 active stack 做成 SMT 结构并不是不可能，但第一阶段没有必要。

对当前需求，更经济的方案是：

1. 对每个机器离线枚举所有可作为稳定落点的配置。
2. 给每个配置一个整数编号。
3. 只在 SMT 中跟踪“当前处于哪个编号”。

这样 guard 判断依然由外部输入决定，但层次状态判断就只需查一张离线表。

## 11.4.2 稳定配置集合的预编译

第一阶段建议把一个稳定配置定义成：

- 一个稳定叶状态
- 加上该叶状态唯一对应的 active ancestor 集合

由于当前模型子集里没有内部变量写，也没有时间流逝触发跳转，因此：

- 同一个稳定叶状态就足以代表一个稳定配置

于是第一阶段可进一步简化为：

- 稳定配置编号 == 稳定叶状态编号

如果未来要支持更复杂语义，再把“配置编号”和“叶状态编号”拆开。

## 11.4.3 配置变量的 Python/Z3 表达

```python
def build_config_vars(machines: dict[str, StateMachine], num_cuts: int):
    config_vars = {}
    for alias in machines:
        config_vars[alias] = [
            z3.Int(f'Q__{alias}__k{k}')
            for k in range(num_cuts)
        ]
    return config_vars
```

每台机器还应附带一组“合法编号范围”约束：

```python
def build_config_domain_constraints(compiled_machine, config_seq):
    max_id = len(compiled_machine.stable_configs) - 1
    return [z3.And(q >= 0, q <= max_id) for q in config_seq]
```

## 11.4.4 初始配置约束

每个机器还需要一个初始切面约束：

- `Q[m, 0] = initial_config_id`

对应 Python/Z3 写法：

```python
def build_initial_config_constraints(compiled_machines, config_vars):
    constraints = []
    for alias, compiled in compiled_machines.items():
        constraints.append(config_vars[alias][0] == compiled.initial_config_id)
    return constraints
```

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

## 11.5.1 迁移表的预编译结果

建议对每台机器先预编译出下面这种结构：

```python
@dataclass
class CompiledEdge:
    from_config_id: int
    event_path: Optional[str]
    guard_expr: Optional[Expr]
    to_config_id: int


@dataclass
class CompiledMachine:
    stable_configs: list[State]
    outgoing_edges: dict[int, list[CompiledEdge]]
    initial_config_id: int
```

这里最关键的是：

- `outgoing_edges[from_config_id]` 必须按原 DSL 声明顺序排列

因为后面的选择编码要依赖这个顺序。

## 11.5.2 每个 step 的事件视图

对每个 step、每个机器，需要先计算“这个 step 对这台机器来说对应哪个事件”：

- 若 step 不含 `emit`，则该机器本 step 没有外部事件
- 若 step 含 `emit(name)`，则通过 `binding.event_map[name]` 找到机器内 event path

可以写成：

```python
def resolve_bound_event(step: TimelineStep, binding: TimelineMachineBinding) -> str | None:
    emit_actions = [a for a in step.actions if isinstance(a, EmitEvent)]
    if not emit_actions:
        return None
    assert len(emit_actions) == 1
    return binding.event_map[emit_actions[0].event_name]
```

## 11.5.3 保留“前面优先”的精确编码

设机器 `m` 在切面 `k` 的当前配置为 `Q[m, k]`，该 step 绑定到本机的事件路径为 `E_m_k`。

对某个 `from_config_id = q` 的候选出边列表 `edge_0, edge_1, ..., edge_n`，按顺序定义：

- `raw_enabled_i`
  - 事件匹配且 guard 成立
- `selected_i`
  - `raw_enabled_i` 成立
  - 且 `edge_0..edge_{i-1}` 都不成立

则：

- 如果存在某个 `selected_i`，下一配置等于其 `to_config_id`
- 如果所有 `raw_enabled_i` 都不成立，下一配置保持不变

这正是 pyfcstm 现有 transition declaration order 的离散版本。

## 11.5.4 guard 的 Z3 绑定环境

对 guard 求值时，变量名不应绑定到机器内部可写状态，而应绑定到当前切面的输入快照：

```python
def build_guard_env(binding, input_vars, cut_index):
    return {
        local_name: input_vars[scenario_name][cut_index]
        for scenario_name, local_name in binding.input_map.items()
    }
```

然后再调用现有 `expr_to_z3(...)`：

```python
guard_z3 = expr_to_z3(edge.guard_expr, z3_vars=guard_env)
```

## 11.5.5 单机单步迁移约束的 Python/Z3 骨架

下面是一版建议实现：

```python
def build_machine_step_constraints(
    compiled_machine: CompiledMachine,
    machine_alias: str,
    binding: TimelineMachineBinding,
    scenario: TimelineScenario,
    step_index: int,
    config_vars,
    input_vars,
):
    constraints = []
    q_before = config_vars[machine_alias][step_index]
    q_after = config_vars[machine_alias][step_index + 1]
    step = scenario.steps[step_index]
    bound_event = resolve_bound_event(step, binding)

    cases = []
    for from_id, edges in compiled_machine.outgoing_edges.items():
        raw_enabled = []
        selected = []

        for edge in edges:
            event_match = z3.BoolVal(edge.event_path == bound_event)
            if edge.guard_expr is None:
                guard_ok = z3.BoolVal(True)
            else:
                guard_env = build_guard_env(binding, input_vars, step_index)
                guard_ok = expr_to_z3(edge.guard_expr, z3_vars=guard_env)

            enabled = z3.And(event_match, guard_ok)
            raw_enabled.append(enabled)

        for i, enabled in enumerate(raw_enabled):
            selected.append(z3.And(enabled, *[z3.Not(x) for x in raw_enabled[:i]]))

        transition_cases = [
            z3.Implies(selected_i, q_after == edge.to_config_id)
            for selected_i, edge in zip(selected, edges)
        ]

        stay_case = z3.Implies(
            z3.And(q_before == from_id, z3.Not(z3.Or(*raw_enabled)) if raw_enabled else z3.BoolVal(True)),
            q_after == from_id,
        )

        cases.append(z3.Implies(q_before == from_id, z3.And(*(transition_cases + [stay_case]))))

    constraints.extend(cases)
    return constraints
```

上面这个骨架没有处理：

- init/pseudo/hierarchy 闭包

因为这些应在“稳定配置预编译”阶段就被折叠进 `to_config_id` 的求值里，而不是在 SMT 里动态展开。

这正是第一阶段值得采用的一个关键降维手段。

## 11.6 输入更新步编码

若某个 step 只包含输入更新，不含事件，则：

- 该 step 对所有机器都没有外部事件输入
- 但 guard-only / unconditional 转换仍然可能被评估
- 输入快照按 `set` 规则更新到下一切面

在当前第一阶段语义里，`SetInput` 对输入快照的更新是：

- `step_i` 先继承上一切面的输入快照
- 再应用本 step 的 `set`，形成当前时间点可见的输入快照
- `cycle()` 在这个更新后的输入快照上执行
- step 结束后，该输入快照继续传给下一切面

因此对“只包含输入更新、不含事件”的 step 来说：

- 若某台机器在当前切面 `i` 上存在 guard-only 转换且 guard 已经满足，则它可以在该 step 上迁移
- 若 guard 需要依赖本 step 刚刚设置的新值，则这类迁移也可以在该 step 上立即发生

空 step 仍然有意义，但它的作用现在主要是：

- 作为逻辑时间锚点
- 参与时间约束
- 或者在没有新的输入变化和事件时，再评估一次当前快照下的 guard-only 行为

## 11.6.1 空 step 的机器约束

若某个 step：

- 没有 `emit`
- 也没有 `set`

则它只是一个逻辑时间节点。

此时：

- 输入快照满足 `Input[:, k+1] = Input[:, k]`
- 机器没有事件输入
- 但 guard-only / unconditional 转换仍然可能发生

因此空 step 的语义不是“什么都不评估”，而是：

- 不改变输入
- 不提供事件
- 允许模型在当前输入快照上继续演化一次

这正是为什么空 step 可以作为逻辑时间锚点，同时又能在需要时承接 guard-only 转换。

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

## 11.7.1 状态谓词的离线判定

对某个机器的某个稳定配置编号 `q_id`，状态谓词是否成立不需要在 SMT 里递归算祖先路径，可以离线算好：

```python
predicate_holds[config_id][predicate_id] -> bool
```

然后 SMT 里只需要做一个有限分支：

```python
def build_predicate_bool(q_var, valid_config_ids):
    clauses = []
    for config_id, holds in valid_config_ids.items():
        if holds:
            clauses.append(q_var == config_id)
    return z3.Or(*clauses) if clauses else z3.BoolVal(False)
```

## 11.7.2 `at_most_one` 的 Z3 表达

```python
def encode_at_most_one(pred_bools):
    return z3.PbLe([(b, 1) for b in pred_bools], 1)
```

如果我们要编码“关系被违反”，则应取其否定：

```python
def encode_at_most_one_violation(pred_bools):
    return z3.Not(z3.PbLe([(b, 1) for b in pred_bools], 1))
```

## 11.7.3 `forbidden_combination` 的 Z3 表达

```python
def encode_forbidden_combination_violation(pred_bools):
    return z3.And(*pred_bools) if pred_bools else z3.BoolVal(False)
```

## 11.7.4 `pairwise_mutex_group` 的 Z3 表达

```python
def encode_pairwise_mutex_violation(pred_bools):
    violations = []
    for i in range(len(pred_bools)):
        for j in range(i + 1, len(pred_bools)):
            violations.append(z3.And(pred_bools[i], pred_bools[j]))
    return z3.Or(*violations) if violations else z3.BoolVal(False)
```

## 11.7.5 整体坏性质构建

```python
def build_violation_constraint(relation_bools_by_cut):
    per_cut = []
    for relation_bools in relation_bools_by_cut:
        per_cut.append(z3.Or(*relation_bools) if relation_bools else z3.BoolVal(False))
    return z3.Or(*per_cut) if per_cut else z3.BoolVal(False)
```

这个 `violation_constraint` 就是传给 solver 的最终坏性质。

## 11.7.6 `open_interval` 的处理

在当前第一阶段语义下：

- 时间流逝本身不会触发状态变化

因此若 `T_i < T_{i+1}`，那么开区间 `(T_i, T_{i+1})` 内的机器状态与 `step_i` 执行后的状态相同。

所以 `open_interval` 不需要单独引入另一套配置变量，直接复用：

- `Q[:, i+1]`

并额外附加一个“区间真实存在”的布尔前提：

```python
def build_open_interval_exists(time_vars, left_step, right_step):
    return time_vars[left_step.time_symbol] < time_vars[right_step.time_symbol]
```

如果某个关系需要在区间上检查，则可编码为：

```python
interval_violation = z3.And(
    build_open_interval_exists(time_vars, step_i, step_i_plus_1),
    relation_violation_at_cut_i_plus_1,
)
```

这样就不需要再为区间引入一套新的状态传播机制。

进一步地，若关系本身带有：

- `observation_scope = 'post_step'`

则只在离散切面上生成违规谓词。

若关系带有：

- `observation_scope = 'open_interval'`

则只在存在正时长区间的地方生成：

- `interval_exists && relation_violation_at_cut`

若关系带有：

- `observation_scope = 'both'`

则把这两类违规一起并入最终坏性质。

## 11.8 一个更完整的编译结果对象

为了让实现结构清晰，建议把“编译结果”做成明确的数据对象：

```python
@dataclass
class CompiledTimelineProblem:
    time_vars: dict[str, z3.ArithRef]
    input_vars: dict[str, list[z3.ExprRef]]
    config_vars: dict[str, list[z3.ArithRef]]
    time_constraints: list[z3.BoolRef]
    input_constraints: list[z3.BoolRef]
    machine_constraints: list[z3.BoolRef]
    violation_constraint: z3.BoolRef
    compiled_machines: dict[str, CompiledMachine]
```

这样后续：

- `solve`
- `counterexample reconstruction`
- `dump-smt2`

都会更好实现。

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
- `pyfcstm.simulate.runtime`
  - 仅用于：
  - 默认初始化后空 `cycle()` 求初始稳定配置
  - 热启动后单次 `cycle()` 求某个 step 的后继稳定配置
- `pyfcstm.solver.expr`
  - 将 guard 转为 Z3
- `pyfcstm.solver.solve`
  - 求解与解枚举

## 15.2 timeline 自己实现的部分

- 连续时间场景元模型
- 场景归一化
- 基于 runtime 的单步状态推导封装
- 多机绑定与反例重建

## 15.3 明确不复用的部分

- `pyfcstm.verify.search`
- `pyfcstm.entry.simulate`
- `pyfcstm.simulate` 的 REPL / batch / 长生命周期运行框架

原因是：

- 它们的主语义中心是 `cycle`
- timeline 问题的主轴是“step + 连续时间约束 + 场景约束”
- 本需求只想借用 runtime 的状态迁移推导能力，不想被现有 simulate/verify 的整体执行框架牵着走

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

## 16.3 第三阶段：实现基于 runtime 的单机单步推导器

目标：

- 对第一阶段支持的状态机子集
- 给定稳定配置、输入快照、step
- 计算下一个稳定配置

要求：

- 显式拒绝不支持的 DSL 特性
- 保持 transition declaration order 语义
- 支持 hierarchy / init / pseudo 闭包

实现方式：

1. 初始状态推导
   - `runtime = SimulationRuntime(machine)`
   - `runtime.cycle([])`
   - 读取 `runtime.current_state` 与 `runtime.vars`
2. 单 step 推导
   - 根据上一时刻快照生成新的 `initial_vars`
   - `runtime = SimulationRuntime(machine, initial_state=prev_state_path, initial_vars=initial_vars)`
   - `runtime.cycle(bound_events)`
   - 读取新的 `runtime.current_state` 与 `runtime.vars`
3. runtime 对象不复用
   - 每次推导都新建一个 runtime
   - 只做一次 `cycle()`
   - 读取结果后立即丢弃

这是整个 timeline 的关键基础，但不需要自己重写一套复杂的层次状态迁移执行器。

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
- 输入更新但无事件时，guard-only 转换仍可立即发生

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
3. 时间采用“有序 step + 连续时间变量 + 首个时间点自动满足 `T_0 >= 0` + 相邻 step 自动满足 `T_i <= T_{i+1}`”的语义。
4. 不按秒展开，也不按 cycle 展开，而是按场景变化点建立 SMT 约束。
5. 所有外部量都必须显式给出初始值，第一阶段不引入 `assume`。
6. 外部量在语义上按只读 environment input 处理，工程上先由 timeline 侧通过 binding 和静态检查实现。
7. 允许空 step 作为纯逻辑时间节点存在，并参与时间约束。
8. 以 fcstm 的语法与 model object 为主语义载体，不复用 verify；对 simulate 仅有限复用 `SimulationRuntime` 作为一次性单步状态推导器。
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

---

## 20. 完整示例

本节给出一组可以直接用于讨论实现与测试的完整示例。

设计目标是：

- 至少包含多个状态机
- 使用 fcstm DSL 表达模型
- 使用 timeline YAML 表达场景
- 同时覆盖：
  - `forbidden_combination`
  - `at_most_one`
  - `pairwise_mutex_group`
- 同时给出：
  - 预期 `sat`
  - 预期 `unsat`

## 20.1 示例状态机

下面给出 3 个示例状态机：

- `Aircraft`
- `Controller`
- `Monitor`

需要注意：

- 这里都写了 `def float height = 0.0;`
- 这是为了复用当前 fcstm DSL 的变量语法与 model object
- 在 timeline 语义下，`height` 应解释为只读外部输入
- 这些模型中不允许对 `height` 进行任何写操作
- 本节示例已按当前仓库中的 `state_machine_dsl` parser 与 model 转换实际验证过可解析

### 20.1.1 Aircraft.fcstm

```fcstm
def float height = 0.0;

state Aircraft {
    state Cruise;
    state Descending;
    state GearLowering;
    state GearDown;

    [*] -> Cruise;

    Cruise -> Descending : /DescendCmd;
    Descending -> GearLowering : if [height <= 2000];
    GearLowering -> GearDown : /LowerDone;
}
```

语义说明：

- `DescendCmd` 使飞机从 `Cruise` 进入 `Descending`
- 当 `height <= 2000` 时，guard-only 转换会使其进入 `GearLowering`

### 20.1.2 Controller.fcstm

```fcstm
def float height = 0.0;

state Controller {
    state HighSpeedCruise;
    state Approach;
    state GearCommanded;
    state Stabilized;

    [*] -> HighSpeedCruise;

    HighSpeedCruise -> Approach : /DescendCmd;
    Approach -> GearCommanded : if [height <= 2500];
    GearCommanded -> Stabilized : /LowerDone;
}
```

语义说明：

- `DescendCmd` 让控制器离开高速巡航态
- 只要 `height <= 2500`，guard-only 转换就会使其进入 `GearCommanded`

### 20.1.3 Monitor.fcstm

```fcstm
def float height = 0.0;

state Monitor {
    state Normal;
    state WarningIssued;

    [*] -> Normal;

    Normal -> WarningIssued : if [height <= 1800];
}
```

语义说明：

- 当 `height <= 1800` 时，监控器会进入 `WarningIssued`

## 20.2 示例场景

下面给出两个核心场景：

- 一个会导致“多机状态组合冲突”
- 一个不会导致该冲突

### 20.2.1 场景 A：冲突场景

```yaml
name: landing_conflict_sat

inputs:
  - name: height
    type: float
    initial: 3000
    constraint: "height >= 0"

steps:
  - id: s0
    time: t0
    actions: []

  - id: s1
    time: t1
    emit: descend_cmd

  - id: s2
    time: t2
    set:
      height: 1800

  - id: s3
    time: t3
    actions: []

constraints:
  - "0 <= t1 - t0"
  - "5 <= t2 - t1 <= 20"
  - "t3 - t2 == 0"

bindings:
  aircraft:
    event_map:
      descend_cmd: Aircraft.DescendCmd
    input_map:
      height: height

  controller:
    event_map:
      descend_cmd: Controller.DescendCmd
    input_map:
      height: height

  monitor:
    event_map: {}
    input_map:
      height: height
```

场景解释：

- `s1` 时，三个机器共同接收 `descend_cmd`
- `s2` 时，高度先被设置到 `1800`
- 通过 `t3 - t2 == 0` 表示：
  - `s2` 和 `s3` 发生在同一个连续时间点
  - 但顺序仍然是先 `s2`、后 `s3`
- 在当前语义下，`s2` 的输入更新对该 step 立即可见，因此 guard-only 转换已经可以在 `s2` 上发生
- `s3` 在这里只是一个额外的逻辑时间锚点

在 `s2` 之后，且到 `s3` 之前保持不变：

- `Aircraft` 进入 `GearLowering`
- `Controller` 进入 `GearCommanded`
- `Monitor` 进入 `WarningIssued`

### 20.2.2 场景 B：非冲突场景

```yaml
name: landing_conflict_unsat

inputs:
  - name: height
    type: float
    initial: 3000
    constraint: "height >= 0"

steps:
  - id: s0
    time: t0
    actions: []

  - id: s1
    time: t1
    emit: descend_cmd

  - id: s2
    time: t2
    set:
      height: 2300

  - id: s3
    time: t3
    actions: []

constraints:
  - "0 <= t1 - t0"
  - "5 <= t2 - t1 <= 20"
  - "t3 - t2 == 0"
  - "1 <= t3 - t2"

bindings:
  aircraft:
    event_map:
      descend_cmd: Aircraft.DescendCmd
    input_map:
      height: height

  controller:
    event_map:
      descend_cmd: Controller.DescendCmd
    input_map:
      height: height

  monitor:
    event_map: {}
    input_map:
      height: height
```

场景解释：

- `s1` 后：
  - `Aircraft = Descending`
  - `Controller = Approach`
  - `Monitor = Normal`
- `s2` 时高度被设置到 `2300`
- 在当前语义下，这个新高度对 `s2` 的 guard 判定立即可见
  - `Aircraft` 的 `height <= 2000` 不成立，所以不会进入 `GearLowering`
  - `Controller` 的 `height <= 2500` 成立，所以会进入 `GearCommanded`
  - `Monitor` 的 `height <= 1800` 不成立，所以不会进入 `WarningIssued`
- `s3` 只是一个空 step，用于额外提供时间锚点，不改变上述结论

因此在 `s2` 之后，且到 `s3` 之前只有：

- `Controller = GearCommanded`

### 20.2.3 场景 C：瞬时穿越场景

这个场景专门用来体现“时间间隔是否为正”对验证结果的影响。

```yaml
name: interval_sensitive_unsat

inputs:
  - name: height
    type: float
    initial: 3000
    constraint: "height >= 0"

steps:
  - id: s0
    time: t0
    actions: []

  - id: s1
    time: t1
    emit: descend_cmd

  - id: s2
    time: t2
    set:
      height: 1800

  - id: s3
    time: t3
    actions: []

constraints:
  - "0 <= t1 - t0"
  - "t2 - t1 == 0"
  - "t3 - t2 == 0"

bindings:
  aircraft:
    event_map:
      descend_cmd: Aircraft.DescendCmd
    input_map:
      height: height

  controller:
    event_map:
      descend_cmd: Controller.DescendCmd
    input_map:
      height: height

  monitor:
    event_map: {}
    input_map:
      height: height
```

场景解释：

- `s1` 后：
  - `Aircraft = Descending`
  - `Controller = Approach`
- 但 `s2` 与 `s3` 都和前一步处于同一连续时间点
- 因此虽然状态序列上出现了：
  - `Descending`
  - `Approach`
  - 以及之后的 `GearLowering`
- 但这些状态之间没有任何正时长开区间

### 20.2.4 场景 D：区间拉开场景

这个场景与场景 C 的离散顺序几乎相同，但显式拉开了时间间隔。

```yaml
name: interval_sensitive_sat

inputs:
  - name: height
    type: float
    initial: 3000
    constraint: "height >= 0"

steps:
  - id: s0
    time: t0
    actions: []

  - id: s1
    time: t1
    emit: descend_cmd

  - id: s2
    time: t2
    set:
      height: 1800

  - id: s3
    time: t3
    actions: []

constraints:
  - "0 <= t1 - t0"
  - "5 <= t2 - t1 <= 20"
  - "t3 - t2 == 0"

bindings:
  aircraft:
    event_map:
      descend_cmd: Aircraft.DescendCmd
    input_map:
      height: height

  controller:
    event_map:
      descend_cmd: Controller.DescendCmd
    input_map:
      height: height

  monitor:
    event_map: {}
    input_map:
      height: height
```

场景解释：

- `s1` 后：
  - `Aircraft = Descending`
  - `Controller = Approach`
- 且由 `5 <= t2 - t1 <= 20` 保证：
  - 从 `s1` 到 `s2` 存在一个正时长开区间
- 在这个开区间内，两台机器会持续停留在：
  - `Aircraft.Descending`
  - `Controller.Approach`
- 到 `s2` 时，新的输入快照立即生效，guard-only 转换会把它们推进到后续状态

## 20.3 示例性质与期望结果

下面分别展示不同类型关系约束下的预期结果。

这里需要强调：

- “满足”与“不满足”说的不是场景本身
- 而是“给定场景下，某条待验证性质是否成立”

因此每个例子都必须明确给出：

- 待验证性质是什么
- 场景是什么
- 预期验证结论是什么
- 为什么会得到这个结论

本文在下面采用如下记法：

- 若某条关系约束在给定场景下可能被违反，则验证结果为 `sat`
- 若某条关系约束在给定场景下不可能被违反，则验证结果为 `unsat`

### 20.3.1 `forbidden_combination` 的 `sat` 示例

待验证性质 `P1`：

- 在任意观测点上，不允许
  - `Aircraft.GearLowering`
  - 与 `Monitor.WarningIssued`
  - 同时成立

也就是下面这条关系约束：

```yaml
relations:
  - kind: forbidden_combination
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: monitor
        state: Monitor.WarningIssued
```

使用场景：

- 场景 A：`landing_conflict_sat`

预期结果：

- `sat`

原因：

- 在 `post_step(s3)` 时：
  - `Aircraft.GearLowering` 为真
  - `Monitor.WarningIssued` 为真
- 被禁止组合成立，因此验证器应返回一条反例

一条确定的反例可以写成：

| 观测点 | `height` | `Aircraft` | `Controller` | `Monitor` |
|--------|----------|------------|--------------|-----------|
| 初始 | 3000 | `Cruise` | `HighSpeedCruise` | `Normal` |
| `post_step(s1)` | 3000 | `Descending` | `Approach` | `Normal` |
| `post_step(s2)` | 1800 | `Descending` | `Approach` | `Normal` |
| `post_step(s3)` | 1800 | `GearLowering` | `GearCommanded` | `WarningIssued` |

在这个反例里：

- `post_step(s3)` 就是违反点
- 因为性质 `P1` 明确禁止 `Aircraft.GearLowering && Monitor.WarningIssued`

### 20.3.2 `forbidden_combination` 的 `unsat` 示例

待验证性质 `P2`：

- 在任意观测点上，不允许
  - `Aircraft.GearLowering`
  - 与 `Controller.HighSpeedCruise`
  - 同时成立

也就是：

```yaml
relations:
  - kind: forbidden_combination
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: controller
        state: Controller.HighSpeedCruise
```

使用场景：

- 场景 A：`landing_conflict_sat`

预期结果：

- `unsat`

原因需要按状态演化逐步展开：

1. 初始时：
   - `Aircraft = Cruise`
   - `Controller = HighSpeedCruise`
   - 此时 `Aircraft.GearLowering` 为假
2. 若想让 `Aircraft.GearLowering` 成立：
   - `Aircraft` 必须先经过 `Cruise -> Descending : /DescendCmd`
   - 然后在后续空 step 上满足 guard `height <= 2000`
3. 但是一旦 `DescendCmd` 在 `s1` 发生：
   - `Controller` 同时会执行 `HighSpeedCruise -> Approach : /DescendCmd`
   - 从此离开 `HighSpeedCruise`
4. 因此在该场景下不存在任何观测点，使得：
   - `Aircraft.GearLowering`
   - 与 `Controller.HighSpeedCruise`
   - 同时为真

这就是为什么性质 `P2` 在场景 A 下的验证结果是 `unsat`。

### 20.3.3 `at_most_one` 的 `sat` 示例

待验证性质 `P3`：

- 在任意观测点上，下面 3 个状态谓词最多只能有 1 个成立：
  - `Aircraft.GearLowering`
  - `Controller.GearCommanded`
  - `Monitor.WarningIssued`

也就是：

```yaml
relations:
  - kind: at_most_one
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: controller
        state: Controller.GearCommanded
      - machine: monitor
        state: Monitor.WarningIssued
```

使用场景：

- 场景 A：`landing_conflict_sat`

预期结果：

- `sat`

原因：

- `post_step(s3)` 时，这三个谓词同时为真
- 显然违反“最多一个成立”

一条确定的反例仍然可以直接使用 `P1` 中的那条轨迹：

| 观测点 | `Aircraft.GearLowering` | `Controller.GearCommanded` | `Monitor.WarningIssued` |
|--------|--------------------------|----------------------------|--------------------------|
| 初始 | 假 | 假 | 假 |
| `post_step(s1)` | 假 | 假 | 假 |
| `post_step(s2)` | 假 | 假 | 假 |
| `post_step(s3)` | 真 | 真 | 真 |

由于 `post_step(s3)` 时同时有 3 个谓词为真，所以性质 `P3` 被明确违反。

### 20.3.4 `at_most_one` 的 `unsat` 示例

待验证性质 `P4`：

- 仍然使用与 `P3` 相同的关系约束：
  - `Aircraft.GearLowering`
  - `Controller.GearCommanded`
  - `Monitor.WarningIssued`
  - 最多只能有一个成立

但这次换到场景 B。

关系定义：

```yaml
relations:
  - kind: at_most_one
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: controller
        state: Controller.GearCommanded
      - machine: monitor
        state: Monitor.WarningIssued
```

使用场景：

- 场景 B：`landing_conflict_unsat`

预期结果：

- `unsat`

原因要逐步看场景 B 的状态：

1. 初始：
   - 三个谓词都为假
2. `post_step(s1)`：
   - `Aircraft = Descending`
   - `Controller = Approach`
   - `Monitor = Normal`
   - 三个目标谓词仍都为假
3. `post_step(s2)`：
   - 高度变为 `2300`
   - `Aircraft.GearLowering` 为假，因为 `2300 <= 2000` 不成立
   - `Controller.GearCommanded` 为真，因为 `2300 <= 2500` 成立
   - `Monitor.WarningIssued` 为假，因为 `2300 <= 1800` 不成立
4. `post_step(s3)`：
   - `Aircraft.GearLowering` 为假，因为 `2300 <= 2000` 不成立
   - `Controller.GearCommanded` 为真，因为 `2300 <= 2500` 成立
   - `Monitor.WarningIssued` 为假，因为 `2300 <= 1800` 不成立

因此每个观测点上，命中数都不超过 1。

所以性质 `P4` 在场景 B 下成立，验证结果应为 `unsat`。

### 20.3.5 `pairwise_mutex_group` 的 `sat` 示例

待验证性质 `P5`：

- 下面 3 个谓词构成一个 pairwise mutex group：
  - `Aircraft.GearLowering`
  - `Controller.GearCommanded`
  - `Monitor.WarningIssued`

也就是任意两两之间都不允许同时成立。

关系定义：

```yaml
relations:
  - kind: pairwise_mutex_group
    predicates:
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: controller
        state: Controller.GearCommanded
      - machine: monitor
        state: Monitor.WarningIssued
```

使用场景：

- 场景 A：`landing_conflict_sat`

预期结果：

- `sat`

原因：

- 该关系会展开成三条两两互斥：
  - `Aircraft.GearLowering` 与 `Controller.GearCommanded`
  - `Aircraft.GearLowering` 与 `Monitor.WarningIssued`
  - `Controller.GearCommanded` 与 `Monitor.WarningIssued`
- 在 `post_step(s3)` 时，上述三对全都被同时违反

一条确定的反例可直接展开成：

| 违反点 | 违反的二元互斥对 |
|--------|------------------|
| `post_step(s3)` | `Aircraft.GearLowering && Controller.GearCommanded` |
| `post_step(s3)` | `Aircraft.GearLowering && Monitor.WarningIssued` |
| `post_step(s3)` | `Controller.GearCommanded && Monitor.WarningIssued` |

### 20.3.6 `pairwise_mutex_group` 的 `unsat` 示例

待验证性质 `P6`：

- `Aircraft` 的以下 4 个叶状态构成一个 pairwise mutex group：
  - `Aircraft.Cruise`
  - `Aircraft.Descending`
  - `Aircraft.GearLowering`
  - `Aircraft.GearDown`

也就是要求这些叶状态两两互斥。

关系定义：

```yaml
relations:
  - kind: pairwise_mutex_group
    predicates:
      - machine: aircraft
        state: Aircraft.Cruise
      - machine: aircraft
        state: Aircraft.Descending
      - machine: aircraft
        state: Aircraft.GearLowering
      - machine: aircraft
        state: Aircraft.GearDown
```

使用场景：

- 场景 A：`landing_conflict_sat`
- 或场景 B：`landing_conflict_unsat`

预期结果：

- `unsat`

原因：

1. 这 4 个谓词都属于同一个状态机 `Aircraft`
2. 它们都是互不相同的稳定叶状态
3. 在第一阶段语义里，一个机器在任意观测点只能处于一个稳定配置
4. 因此 `Aircraft` 在任意观测点都不可能同时命中其中两个叶状态

所以性质 `P6` 在场景 A 和场景 B 下都成立，验证结果都应为 `unsat`。

### 20.3.7 `open_interval` 敏感的 `forbidden_combination`：`unsat` 示例

待验证性质 `P7`：

- 在任何**正时长开区间**上，不允许：
  - `Aircraft.Descending`
  - 与 `Controller.Approach`
  - 同时成立

也就是：

```yaml
relations:
  - kind: forbidden_combination
    observation_scope: open_interval
    predicates:
      - machine: aircraft
        state: Aircraft.Descending
      - machine: controller
        state: Controller.Approach
```

使用场景：

- 场景 C：`interval_sensitive_unsat`

预期结果：

- `unsat`

原因：

1. `post_step(s1)` 的确会出现：
   - `Aircraft.Descending`
   - `Controller.Approach`
2. 但性质 `P7` 检查的不是 `post_step`，而是 `open_interval`
3. 场景 C 中：
   - `t2 - t1 == 0`
   - `t3 - t2 == 0`
4. 因此从 `s1` 之后到后续状态变化之间，不存在正时长开区间
5. 也就不存在任何区间，使得这两个状态在一个非零时长内同时保持为真

所以性质 `P7` 在场景 C 下成立，验证结果应为 `unsat`。

### 20.3.8 `open_interval` 敏感的 `forbidden_combination`：`sat` 示例

待验证性质 `P8`：

- 仍然使用与 `P7` 相同的性质：
  - 在任何正时长开区间上，不允许
    - `Aircraft.Descending`
    - 与 `Controller.Approach`
    - 同时成立

使用场景：

- 场景 D：`interval_sensitive_sat`

预期结果：

- `sat`

原因：

1. `post_step(s1)` 之后，两台机器分别处于：
   - `Aircraft.Descending`
   - `Controller.Approach`
2. 场景 D 明确要求：
   - `5 <= t2 - t1 <= 20`
3. 因此 `(t1, t2)` 是一个真实存在的正时长开区间
4. 在这个开区间内：
   - 没有新的事件
   - 输入也还没有在后续切面生效为新的稳定条件
   - 所以两台机器持续停留在上述两个状态

一条确定的反例可以写成：

| 时间段 / 观测点 | `height` | `Aircraft` | `Controller` |
|-----------------|----------|------------|--------------|
| `post_step(s1)` | 3000 | `Descending` | `Approach` |
| 开区间 `(t1, t2)` | 3000 | `Descending` | `Approach` |
| `post_step(s2)` | 1800 | `Descending` | `Approach` |

因此性质 `P8` 被 `(t1, t2)` 这个正时长区间明确违反，验证结果应为 `sat`。

## 20.4 建议加入自动化测试的样例矩阵

如果后续开始实现，建议把上面的示例直接变成测试夹具，最少覆盖下面这组矩阵：

| 场景 | 关系类型 | 关系内容 | 预期结果 |
|------|----------|----------|----------|
| 场景 A | `forbidden_combination` | `Aircraft.GearLowering && Monitor.WarningIssued` | `sat` |
| 场景 A | `forbidden_combination` | `Aircraft.GearLowering && Controller.HighSpeedCruise` | `unsat` |
| 场景 A | `at_most_one` | `Aircraft.GearLowering, Controller.GearCommanded, Monitor.WarningIssued` | `sat` |
| 场景 B | `at_most_one` | `Aircraft.GearLowering, Controller.GearCommanded, Monitor.WarningIssued` | `unsat` |
| 场景 A | `pairwise_mutex_group` | `Aircraft.GearLowering, Controller.GearCommanded, Monitor.WarningIssued` | `sat` |
| 场景 A/B | `pairwise_mutex_group` | `Aircraft.Cruise, Aircraft.Descending, Aircraft.GearLowering, Aircraft.GearDown` | `unsat` |
| 场景 C | `forbidden_combination@open_interval` | `Aircraft.Descending && Controller.Approach` | `unsat` |
| 场景 D | `forbidden_combination@open_interval` | `Aircraft.Descending && Controller.Approach` | `sat` |

这组样例的好处是：

- 机器数量不少于 2
- 同时包含 3 个机器联动
- 同时覆盖 `sat` 与 `unsat`
- 同时覆盖 3 种关系类型
- 还能顺带覆盖：
  - 空 step
  - 共享外部输入
  - 不同 guard 阈值
  - 时间相等与正时长区间的区别
  - `post_step` 与 `open_interval` 两类观测范围

## 21. 基于真实 SysDeSim 样例的落地工作计划

本节是在前文通用 timeline 设计基础上，结合当前真实 SysDeSim 样例、现有 `pyfcstm.convert.sysdesim` 实现现状，以及《SYSDESIM_XML_FORMAT_ANALYSIS.md》《SYSDESIM_CONVERT_DESIGN.md》中的收敛结论，给出的**样例驱动实施计划**。

这一节的目标不是再写一份抽象设计，而是把“接下来真的要怎么做”拆成可执行 phase。

## 21.1 当前现状与问题收敛

当前已知事实如下：

- 当前真实样例不是“纯状态机文件”，而是同时包含：
  - `uml:StateMachine`
  - `uml:Interaction`
  - 多类 `uml:Activity`
  - `Signal` / `SignalEvent`
  - `ChangeEvent`
  - stereotype 与图表示层信息
- 当前样例应被视为 **TIMELINE 计划的真实输入样本**，而不是一个独立的通用转换样例。
- 现有 `pyfcstm.convert.sysdesim.convert` 能够读取 machine，但当前仍在两个位置被样例阻塞：
  - 非 `int/float` 的 property 类型会在变量归一化阶段中止
  - `ChangeEvent` 触发目前不在 Phase2 支持范围内
- 从样例分析结论看，后续工作主线不应是“完整导入所有 property”，而应是：
  - 保留状态机主干
  - 统一 `SignalEvent` / `ChangeEvent` / `guard`
  - 提取顺序图中的消息与赋值观测
  - 生成 TIMELINE 所需的 `event_map`、`input_map`、`step`、`SetInput`

## 21.2 本阶段建议采用的总体技术路线

建议把真实样例接入 TIMELINE 的主链路明确为：

```text
SysDeSim XMI
  -> Raw XMI Index
  -> Machine Extract
  -> Interaction Extract
  -> Trigger/Input Normalize
  -> Timeline Import IR
  -> Timeline Binding/Scenario Candidate
  -> timeline runtime / SMT compile
  -> witness / diagnostics / optional FCSTM compatibility export
```

这里需要特别强调：

- 主模式应是 **timeline-first import**
- 纯 FCSTM 导出应退居为 compatibility mode
- `ChangeEvent` 与文本型 `guard` 应先统一成条件触发抽象
- 顺序图中的 `name=value` 文本，应优先作为 `SetInput` 候选，而不是内部变量写入
- guard 中出现的名字，应优先落入 `input_map` 语义，而不是默认当作内部持久变量

## 21.3 建议增加的代码组织

为避免继续把所有逻辑堆在 `pyfcstm/convert/sysdesim/convert.py`，建议按职责拆层。

建议的代码组织如下：

- `pyfcstm/convert/sysdesim/xml_index.py`
  - 原始 XMI 解析、命名空间处理、`xmi:id` 索引、按 UML 类型分桶
- `pyfcstm/convert/sysdesim/extract_machine.py`
  - 提取状态机、region、vertex、transition、signal、event、guard、action 引用
- `pyfcstm/convert/sysdesim/extract_interaction.py`
  - 提取顺序图 lifeline、message、state invariant、occurrence 顺序、简单赋值观测
- `pyfcstm/convert/sysdesim/normalize.py`
  - 名字归一化、条件表达式归一化、`ChangeEvent/guard` 合流、输入候选分类
- `pyfcstm/convert/sysdesim/timeline_ir.py`
  - timeline-first 的导入 IR，例如条件触发、观测流、step 候选、binding 候选
- `pyfcstm/convert/sysdesim/compat_fcstm.py`
  - timeline-first IR 到 FCSTM 兼容导出
- `pyfcstm/timeline/importers/sysdesim.py`
  - 从 SysDeSim timeline IR 生成 `TimelineScenario`、`TimelineMachineBinding`、候选 step

`convert.py` 不应继续承担“原始 XML 解析 + 归一化 + timeline 方案 + FCSTM 导出 + report”全部职责。更合理的定位是：

- 保留 façade / orchestration 入口
- 下沉具体解析和转换逻辑到上面的模块

但对当前真实样例的**短期落地顺序**不应一开始就大拆模块，而应先基于现有 `pyfcstm.convert.sysdesim` 做增量修改，把状态机主干语义跑通，再决定如何拆分。

## 21.3.1 基于真实 XMI 的 timeline 提取技术方案

对当前真实样例，建议采用下面这条**样例驱动提取算法**：

1. 先用现有 `load_sysdesim_xml()` / `normalize_machine()` 读取状态机主干。
2. 基于状态机主干建立：
   - transition declaration order
   - machine-relevant signal 集合
   - composite-source outgoing transition 集合
3. 在当前样例上，已确认存在一个复合状态直接对外的信号边：
   - `H -> G` on `Sig8`
   - 这条边不应继续按普通 same-region edge 看待，而应进入 force transition 语义
4. 再进入顺序图提取：
   - 找到类下的 `ownedBehavior / uml:Interaction`
   - 读取 `fragment` 的原始顺序
5. 对 `fragment` 做如下分类：
   - `uml:MessageOccurrenceSpecification`
     - 只以 **receive side** 作为 step anchor
     - 先根据 `sendEvent/receiveEvent -> lifeline` 判定消息方向
     - 当前真实样例中，应先把挂有 `StateInvariant` 的 lifeline 视为 machine-internal lifeline
     - 若 message 是 **external -> internal** 且有 `signature`，才生成 `emit(signal_name)` 候选
     - 若 message 是 **internal -> external**，则保留为空 anchor step，并附注它是哪一个 outbound signal
     - 若 message 是 internal self-message，或 message 无 `signature`，同样保留为空 anchor step
   - `uml:StateInvariant`
     - 解析内部 `Constraint -> OpaqueExpression.body`
     - 若文本满足 `name=value`，生成 `SetInput(name=value)` 候选
6. 对时间约束做两类提取：
   - `DurationObservation.event="msgA msgB"` + `DurationConstraint`
     - 生成 `between(step(msgA), step(msgB))` 的 duration constraint
   - `TimeObservation.event="msg"` + `TimeConstraint`
     - 不再把它解释成某个 anchor step 自身的局部 time window
     - 而是先为该消息锚点补出一个左端点，再统一生成二元 duration constraint
     - 对当前真实样例，可按“该消息锚点之前最近一个有效 step”来确定左端点
     - 因而 `s03` 上的 `0s-1s` 应解释为 `between(s02, s03) in [0s, 1s]`
     - `s07` 上的 `0s-1s` 应解释为 `between(s06, s07) in [0s, 1s]`
     - 若 timeline 全局并不自动保证严格递增，则这里还需额外要求左端点时刻严格早于右端点时刻
7. 把顺序图消息同时按“方向”和“是否属于 machine-relevant signal”分层：
   - inbound + machine-relevant
     - 进入后续 `event_map` 候选
   - inbound + external-only
     - 暂保留为 inbound observation
     - 后续再决定是否绑定给别的机器，或直接丢弃
   - outbound + machine-relevant
     - 不生成 `emit`
     - 保留为空 anchor step
     - 同时产出 direction mismatch diagnostics
   - outbound + external-only
     - 只作为 timing anchor 保留
8. 把顺序图赋值名与状态机条件名做归一化：
   - 例如 `Rmt` -> `r_mt`
   - 但不强行假设 `y` 与 `a/b/c/d` 已天然一一对应
9. `signature` 解析需要同时兼容两种样式：
   - interaction message 直接引用 `uml:Signal`
   - state-machine trigger 通过 `SignalEvent -> Signal` 间接引用
10. 最终产出不是直接可执行 timeline，而是三层候选：
   - state-machine main trunk
   - scenario step / `emit` / `SetInput` candidate
   - `event_map` / `input_map` candidate

这套算法的关键顺序是：

```text
先状态机主干
  -> 再知道哪些消息是 machine-relevant
  -> 再从 interaction 里挑出 timeline step / emit / set
  -> 最后生成 binding 候选
```

而不是反过来先把整个顺序图硬翻成 timeline。

## 21.3.2 基于真实样例的手工 timeline 候选

为避免只停留在抽象设计，仓库中已补了一个简单脚本：

- [tools/sysdesim_hand_timeline_sample.py](/home/hansbug/oo-projects/pyfcstm/tools/sysdesim_hand_timeline_sample.py)

这个脚本不是正式 importer，只是对当前真实样例做一次**手工 candidate 转换**，用来验证我们对 XMI 的理解是否一致。

当前脚本对真实样例给出的核心理解是：

- 挂有状态不变量的 lifeline 可作为当前样例的 machine-internal lifeline：
  - `控制`
- 状态机 machine-relevant signals 为：
  - `Sig1`
  - `Sig2`
  - `Sig4`
  - `Sig5`
  - `Sig6`
  - `Sig7`
  - `Sig8`
  - `Sig9`
- 当前样例中存在一条必须按 force transition 处理的边：
  - `H -> G` on `Sig8`
- interaction 中真正可作为 `emit` 的 inbound machine-facing 信号只有：
  - `Sig1`
  - `Sig2`
  - `Sig4`
  - `Sig5`
  - `Sig6`
- 但 interaction 同时还观测到三个**方向冲突**的 machine-relevant 信号：
  - `Sig7`
  - `Sig8`
  - `Sig9`
  - 它们在状态机主干里会触发转移，但在顺序图里都表现为 `控制 -> 模块`
  - 因此当前阶段不能把它们直接生成 `emit(...)`
  - 只能先保留为空 anchor step，并把冲突留给后续 binding / importer diagnostics
- interaction 里可以手工转换出如下 candidate timeline：

```yaml
steps:
  - s01: emit Sig1                       # inbound, 模块 -> 控制
  - s02: set y=2300
  - s03: anchor                         # self, 控制 -> 控制
  - s04: set y=2099
  - s05: anchor                         # outbound Sig11, 发动机点火
  - s06: set y=1300
  - s07: anchor                         # self, 控制 -> 控制
  - s08: set y=1199
  - s09: anchor                         # outbound Sig17, 切换程序角
  - s10: emit Sig2                      # inbound, 模块 -> 控制
  - s11: anchor                         # outbound Sig12, 启动高度控制
  - s12: anchor                         # outbound Sig18, 平飞
  - s13: anchor                         # outbound Sig9, machine-relevant mismatch
  - s14: emit Sig6                      # inbound, 模块 -> 控制
  - s15: anchor                         # outbound Sig13, 第一次航路转弯
  - s16: emit Sig4                      # inbound, 模块 -> 控制
  - s17: anchor                         # outbound Sig14, 直飞
  - s18: anchor                         # outbound Sig15, 启动转弯控制
  - s19: emit Sig4                      # inbound, 模块 -> 控制
  - s20: set r_mt=4999
  - s21: anchor                         # outbound Sig16, 启动导引头控制
  - s22: emit Sig5                      # inbound, 模块 -> 控制
  - s23: anchor                         # outbound Sig8, machine-relevant mismatch, state trunk still has H -> G
  - s24: anchor                         # outbound Sig7, machine-relevant mismatch
```

其中：

- `s01`、`s10`、`s14`、`s16`、`s19`、`s22` 才是当前样例里真正落成 `emit(...)` 的 step
- `s03`、`s07` 是 internal self-message anchor
- `s05`、`s09`、`s11`、`s12`、`s15`、`s17`、`s18`、`s21` 是 outbound external-only signal anchor
- `s13`、`s23`、`s24` 是 outbound machine-relevant anchor
  - 它们必须保留 step，因为 duration / time constraint 仍可能挂在这些消息上
  - 但当前阶段不能把它们当成 `emit`
- 当前样例里还能提取出：
  - `between(s02, s03) in [0s, 1s]`
  - `between(s06, s07) in [0s, 1s]`
  - 这里语义上应保证左端点严格早于右端点；若不由全局 step 顺序保证，则需显式写成严格不等式
- 还能提取出若干 message-to-message duration constraint，例如：

```yaml
duration_constraints:
  - between: [s05, s10]
    value: 20s-30s
  - between: [s11, s12]
    value: 10s
  - between: [s12, s13]
    value: 15s
  - between: [s13, s14]
    value: 10s
  - between: [s15, s16]
    value: 10s
  - between: [s17, s18]
    value: 10s
  - between: [s18, s19]
    value: 5s
  - between: [s19, s21]
    value: 30s
  - between: [s21, s22]
    value: 5s
```

这份 candidate 不是说它已经是最终 timeline YAML，而是说：

- 当前真实 XMI **确实已经足够支撑**出一条 step-ordered scenario candidate
- 其中 message、state invariant、duration/time constraint 都能转成 timeline 侧对象
- 下一步的核心工作是：
  - 把 inbound / outbound / self 三类 step 先稳定分开
  - 让只有 inbound message 才进入 `emit(...)`
  - 对 outbound machine-relevant signal 输出明确 diagnostics，而不是静默丢失
  - 把 `SetInput` 与条件触发绑定起来
  - 把 force transition 纳入状态机主干语义

## 21.3.3 状态机主干导出的 pyfcstm DSL 草案

对当前真实样例，不建议把“主干 DSL 草案”理解成一份单文件、无降级的终态输出。原因很直接：

- `Control` 是四个 region 的并行复合状态
- 现有 `pyfcstm.convert.sysdesim` 的现实路线本来就是 **main shell + split region family**
- 因此最可讨论、也最接近工程落地的草案应是一组输出，而不是硬凑一个单文件 FCSTM

这里先给出**讨论用目标形态**。它不要求当前 converter 已经完全能生成，但它代表后续兼容导出的预期方向。

先说明几个约定：

- 所有可见信号事件统一声明在文件顶层，并在转移中一律用绝对事件引用 `: /SigX`
- 与 timeline 直接无关的 property 先不导出成 `def`
- `ChangeEvent` / `guard` 在 compatibility DSL 里先统一回落为 guard transition
- `entry` 动作导出为 `enter abstract ...`
- `doActivity` 的目标导出形态建议视为 `during abstract ...`
- init transition 上的 `ABC` / `DEF` 属于 transition effect；现有 converter 会忽略这类 effect，因此下面只先保留注释，不伪造错误语义

### 21.3.3.1 main shell 草案

```fcstm
event Sig1;

state Idle;

state Control;

[*] -> Idle;
Idle -> Control : /Sig1;
```

这份 main shell 的作用主要是保留最外层主干轮廓。真正的 region-level 行为建议在 split outputs 中展开。

### 21.3.3.2 `Control` 第 1 个 region 草案

```fcstm
event Sig1;
event Sig2;
event Sig5;

state Idle;

state Control {
    state A;

    state B {
        enter abstract P1;
    }

    state C;

    state D {
        enter abstract P2;
    }

    state E {
        enter abstract P4;
        during abstract P3;
    }

    [*] -> A;

    A -> B : if [a < b];
    B -> C : /Sig2;
    C -> D : if [r_mt < 5000];
    D -> E : /Sig5;
}

[*] -> Idle;
Idle -> Control : /Sig1;
```

这份草案中有两个关键点：

- `A -> B` 不是保留两条边，而是把 `ChangeEvent(a<b)` 和 `guard a<b` 合并成一条条件边
- `C -> D` 的 `R_mt<5000` 在兼容 DSL 层先归一化成 `r_mt < 5000`

### 21.3.3.3 `Control` 第 2 个 region 草案

```fcstm
event Sig1;
event Sig2;
event Sig6;
event Sig8;
event Sig9;

state Idle;

state Control {
    state F {
        enter abstract L;
    }

    state W {
        enter abstract R;
    }

    state G {
        enter abstract T;
    }

    state H {
        state L {
            enter abstract N;
        }

        state M {
            enter abstract Q;
        }

        [*] -> L;   // original init edge carries effect DEF

        L -> M : /Sig9;
        M -> L : /Sig6;
    }

    [*] -> F;       // original init edge carries effect ABC

    F -> W : if [c < d];
    W -> H : /Sig2;
    !H -> G : /Sig8;
}

[*] -> Idle;
Idle -> Control : /Sig1;
```

这部分是当前样例里最关键的一段，因为它同时覆盖了三件事：

- `F -> W` 的 `ChangeEvent(c<d)` 与 `guard c<d>` 合并
- `H` 保持单 region 复合态，而不是被拍平成普通叶子
- `H -> G` 应导出成 `!H -> G : /Sig8;`
  - 也就是把复合源状态的对外转移当作 force transition 处理

同时也要看到真实样例里的歧义：

- `Sig8` 在状态机主干里是消费事件
- 但在顺序图里它被观测成 outbound message
- 因此 `!H -> G : /Sig8;` 这条主干 DSL 草案是成立的
- 但 scenario binding 不能直接把顺序图里的 `s23` 当成这个 transition 的 `emit`

### 21.3.3.4 `Control` 第 3 个 region 草案

```fcstm
event Sig1;
event Sig2;
event Sig4;
event Sig7;

state Idle;

state Control {
    state J;

    state K {
        enter abstract Z;
    }

    state S {
        enter abstract U;
    }

    state X {
        enter abstract I;
    }

    state O {
        enter abstract Y;
    }

    [*] -> J;

    J -> K : /Sig2;
    K -> S : /Sig4;
    S -> X;         // raw XMI confirms: no trigger, no guard, no effect
    X -> S : /Sig4;
    S -> O : /Sig7;
}

[*] -> Idle;
Idle -> Control : /Sig1;
```

这里同样存在方向问题：

- `S -> X` 在原始 XMI 里确认为无 trigger、无 guard、无 effect 的无条件边
- 在当前 timeline 语义下，不再把这类边解释成“下一次 step 自动迁移”，而是把它视为**连续时间上的隐藏内部迁移**
- 具体做法是：若某个显式 transition 在时刻 `t0` 后进入了这条无条件链，则取其后的最近一个 machine-facing `emit` 时刻 `t1`
- 对链中的第 1 条无条件边，赋予内部发生时刻 `t0 + delta1`
- 对链中的第 2 条无条件边，赋予内部发生时刻 `t0 + delta1 + delta2`
- 依此类推，形成严格递增的内部时刻序列
- 并要求整条无条件链的最后一个内部迁移时刻严格早于该最近 `emit`，即 `t0 + delta1 + ... + deltaN < t1`
- 对当前样例，第 3 个 region 可先按下面的收敛理解：
  - `K -> S : /Sig4` 发生在收到该次 `Sig4` 的时刻 `t0`
  - `S -> X` 作为隐藏内部迁移，发生在 `t0 + delta1`
  - 后续最近一个相关 inbound `emit` 是下一次 `Sig4`，其时刻记为 `t1`
  - 因而当前样例里应约束 `t0 + delta1 < t1`
- 若后续存在多次连续无条件跳转，则统一按 `t0 + delta1 + ... + deltaN` 这样的链式形式处理
- 这类边应在 importer / report 中被单独标记为 `auto_transition`，并附带它所绑定的 `(t0, t1, delta-sequence)` 说明
- `Sig7` 在主干里是 `S -> O` 的消费信号
- 但 interaction 里 `Sig7` 是 outbound message
- 因此它在主干 DSL 里保留 `event Sig7` 与 `S -> O : /Sig7;`
- 但 timeline importer 需要把对应顺序图 step 保留成空 anchor，而不是 `emit Sig7`

### 21.3.3.5 `Control` 第 4 个 region 草案

```fcstm
event Sig1;

state Idle;

state Control {
    state V {
        enter abstract X;
    }

    [*] -> V;
}

[*] -> Idle;
Idle -> Control : /Sig1;
```

### 21.3.3.6 这份 DSL 草案对后续 phase 的直接含义

- 先要把“状态机主干可稳定抽取”做成事实，否则 timeline 绑定根本无从谈起
- 当前样例里真正卡转换的，并不是主干拓扑本身，而是：
  - 非 `int/float` property 类型先把导出流程中止了
  - `ChangeEvent` 还没进入统一条件触发抽象
  - `doActivity` 还没进入 state-level DSL lowering
  - transition effect `ABC/DEF` 还只能 warning/忽略
- 因此后续 phase 不该把精力放在“读尽所有 property”，而应优先让上面这几个主干阻塞点消失

## 21.4 Phase 1: 基于现有 sysdesim 支持收敛状态机主干

* [x] 以现有 `load_sysdesim_xml()`、`load_sysdesim_machine()`、`normalize_machine()` 为起点，不先重写整条解析链。
* [x] 先让真实样例的 state machine main trunk 能稳定完成 load / inspect / normalize。
* [x] 输出当前样例的状态机主干摘要：state tree、region tree、transition order、signal trigger 集合。
* [x] 额外把 state-level action 主干一起盘清：`entry`、`exit`、`doActivity`、init transition effect。
* [x] 把“当前阶段完成标准”定义为“状态机主干可稳定抽取”，而不是“interaction 与 timeline 已全部完成”。
* [x] 明确第一阶段默认忽略与状态机主干无关的 property、端口、枚举说明类结构和图形元数据。
* [x] 明确 timeline-first import 是主路线，但首个工程入口必须先把状态机主干打稳。

## 21.5 Phase 2: composite-source outgoing transition 收敛为 force transition

* [x] 在现有状态机主干抽取结果上，检测“source 是 composite state 且 transition 指向外部 state”的边。
* [x] 针对当前真实样例，显式把 `H -> G` on `Sig8` 收敛为 force transition 语义。
* [x] 不再把这类边当成普通 same-region edge，也不再要求 source 必须是 leaf。
* [x] 在 timeline-first IR 中为这类边增加 `force_transition` 标记。
* [x] 在 FCSTM compatibility mode 中，为这类边设计 propagated exit / force transition lowering。
* [x] 为当前样例补回归测试，确保 `H -> G` 不会再次被当作普通边忽略。

## 21.6 Phase 3: 基于现有 converter 收敛当前样例的主干可转换子集

* [x] 让非 `int/float` property 不再阻塞状态机主干抽取。
* [x] 让未参与主干语义的枚举 property 自动旁路为 ignored 或 warning。
* [x] 把 `ChangeEvent` 从 unsupported 调整为可进入条件触发抽象的输入。
* [x] 让同源同宿同条件的 `ChangeEvent/guard` 在主干层先完成合流。
* [x] 增加名称归一化，覆盖 `rmt` / `Rmt` / `R_mt` 这类当前样例已经出现的漂移。
* [x] 把 `doActivity` 纳入主干抽取结果，至少能形成 `during abstract ...` 候选。
* [x] 为 init transition effect `ABC/DEF` 增加显式保留策略：短期可 warning + 注释化，不能再静默丢失。
* [x] 让当前真实样例至少能产出“主干 machine + condition trigger + signal trigger”的中间结果。

## 21.7 Phase 4: 原始 XMI 索引层

* [x] 在主干语义已经稳定后，再把原始 XMI 索引层独立出来，不和前面的语义收敛同时推进。
* [x] 建立 `xmi:id -> element` 的全局索引。
* [x] 建立按 `xmi:type`、标签名、父子关系分组的辅助索引，便于后续抽取 `StateMachine`、`Interaction`、`Activity`、`Signal`、`Property`。
* [x] 显式保存 namespace 信息，避免在后续解析阶段重复硬编码。
* [x] 对 diagram / notation / stereotype / binary object 层做“可见但默认旁路”的索引，不把它们混入状态机语义主链。
* [x] 提供一份原始结构摘要报告，用于诊断“当前文件里到底有哪些机器、交互图、信号、属性、动作对象”。
* [x] 为原始 XMI 索引层补最小测试，确保真实样例在结构遍历上稳定可重现。

## 21.8 Phase 5: 顺序图与活动观测抽取层

* [x] 从 `uml:Interaction` 中抽取 lifeline、message、occurrence 顺序、`StateInvariant` 与可关联的文本。
* [x] 建立一条稳定的 observation stream，而不是只保留离散对象集合。
* [x] 基于 `StateInvariant` 所挂 lifeline，推断当前样例的 machine-internal lifeline 候选。
* [x] 对每条 message 同时记录 source lifeline、target lifeline 与相对方向：inbound / outbound / self。
* [x] 从顺序图文本中抽取简单的 `name=value` 赋值观测。
* [x] 从活动对象或动作体文本中补充简单赋值观测，但只支持保守可识别子集，不做通用脚本求值。
* [x] 为每条观测保留来源上下文：所属 interaction、出现次序、原始文本、归一化后名字。
* [x] 把消息抽取结果与信号定义建立候选映射，为后续 `emit(...)` 候选提供依据。
* [x] 对当前样例显式支持：
  - receive-side message -> step anchor
  - no-signature message -> empty step anchor
  - outbound signal message -> empty step anchor with note
  - self message -> empty step anchor with note
  - `StateInvariant.body` -> `SetInput`
  - `DurationObservation + DurationConstraint` -> between-step duration
  - `TimeObservation + TimeConstraint` -> 导入后同样收敛为 between-step duration
* [x] 明确这一层的目标是“生成 TIMELINE 场景线索”，不是恢复顺序图的完整执行语义。

当前真实样例的 Phase 5 验证结论：

* 已稳定抽出 `1` 个 interaction、`2` 条 lifeline、`19` 条 message、`5` 条 `StateInvariant`、`9` 条 `DurationConstraint` 与 `2` 条 `TimeConstraint`。
* 当前样例的 machine-internal lifeline 可稳定识别为“控制”，消息方向分布为 `6` 条 inbound、`11` 条 outbound、`2` 条 self。
* 当前层只负责保留 observation stream 与后续建模线索，不在此阶段恢复 step 语义或顺序图完整执行语义。

## 21.9 Phase 6: 条件触发统一抽象与名字归一化

* [x] 在 SysDeSim IR 中引入统一触发抽象：`TriggerSignal`、`TriggerCondition`、`TriggerNone`。
* [x] 让 `ChangeEvent` 与文本型 `guard` 都落入 `TriggerCondition`，不要再把二者分裂处理。
* [x] 对 `(source_state_id, target_state_id, normalized_expr)` 做去重，合并同语义的 `ChangeEvent/guard`。
* [x] 若同一条边同时有 `ChangeEvent(expr_a)` 和 `guard(expr_b)` 且两者不同，则生成复合条件触发 `expr_a AND expr_b`。
* [x] 引入统一的名字归一化规则，例如忽略大小写、去下划线、token 正规化。
* [x] 把顺序图观测中的变量名与 guard/change 中出现的变量名接到同一个归一化空间。
* [x] 对当前无法安全解析的条件表达式保留 warning 与原文，不在这一阶段直接中止整个导入。

当前真实样例的 Phase 6 验证结论：

* 已可稳定输出 `TriggerSignal`、`TriggerCondition`、`TriggerNone` 三类统一 trigger 视图。
* 当前样例中 `Idle -> Control` 被识别为 signal trigger，`Control.A -> Control.B` / `Control.C -> Control.D` / `Control.F -> Control.W` 被识别为 condition trigger，`Control.S -> Control.X` 被识别为 none trigger。
* 名字归一化已覆盖真实样例中的 `Rmt` / `rmt` / `R_mt` 漂移，并能把顺序图观测名与条件触发里的变量名收敛到同一归一化空间。
* 当前真实样例虽然全局存在 `22` 个 `uml:TimeEvent`，但状态机 transition 实际引用数为 `0`；同时样例中 cross-level transition 数为 `0`、cross-region transition 数为 `0`。

## 21.10 Phase 7: 外部输入候选分类与 timeline-first IR

* [x] 新增 timeline-first 导入 IR，而不是直接把 SysDeSim IR 硬压成 FCSTM AST。
* [x] 在 IR 中显式表示 machine graph、condition trigger、signal trigger、observation stream、input candidate、step candidate、event candidate。
* [x] 在 IR 中为无 trigger 且无 guard 的普通边增加 `auto_transition` 类别，不再把它们混进普通 event/guard 转移。
* [x] 把 guard / change 中涉及的名字优先分类为 external input candidate，而不是内部状态变量。
* [x] 只有当某个名字明确出现在动作赋值左值且该写语义不可忽略时，才把它回收为 internal state candidate。
* [x] 让 `input_map` 候选显式记录场景层名字、机器内局部名字、来源表达式、歧义说明。
* [x] 让 `event_map` 候选显式记录场景消息名、机器内 event path、对应的 signal / message 证据链。
* [x] 让 `event_map` / diagnostics 同时保留消息方向，避免把 outbound signal 误绑定成 `emit(...)`。

当前真实样例的 Phase 7 验证结论：

* 已可稳定生成 timeline-first import IR，显式包含 machine graph、input candidate、event candidate、step candidate，以及统一的时长约束候选。
* machine graph 已收敛为 `11` 条 `signal_transition`、`3` 条 `condition_transition`、`6` 条 `initial_transition` 与 `1` 条 `auto_transition`。
* 当前真实样例里唯一需要显式标记的 `force_transition` 是 `Control.H -> Control.G`。
* `input_map` 候选当前已稳定抽出 `a / b / c / d / mode / rmt / y` 七个名字，其中：
  - `a / b / c / d / rmt` 为外部输入优先
  - `mode` 为内部写变量优先
  - `y` 为顺序图 observation-only 名字
* `event_map` 候选已能稳定区分：
  - `Sig1 / Sig2 / Sig4 / Sig5 / Sig6` 为可绑定机器事件且允许后续 `emit`
  - `Sig7 / Sig8 / Sig9` 为 machine-relevant 但 direction mismatch 的 outbound 候选
  - `Sig11 / Sig12 / Sig13 / Sig14 / Sig15 / Sig16 / Sig17 / Sig18` 为 interaction-only outbound 候选

## 21.11 Phase 8: 从真实样例生成 step / SetInput / emit 候选

* [x] 基于 observation stream 生成 step 候选顺序。
* [x] 把顺序图中的简单赋值观测转换为 `SetInput` 候选。
* [x] 只把 external -> internal 的带 signature 消息转换为 `emit` 候选。
* [x] 把 internal -> external 的带 signature 消息保留为空 step，并附加 `outbound_signal=...` 说明。
* [x] 把 internal self-message 保留为空 step，并附加 `self_message` 说明。
* [x] 对 machine-relevant 但方向为 outbound 的消息显式产出 mismatch diagnostics。
* [x] 当一个 step 同时包含输入更新和消息时，按 TIMELINE 语义规定“先 `SetInput`，后事件求值”。
* [x] 即使某个 step 没有消息，也要允许其成为“只包含输入更新”或“空 step”的候选。
* [x] 为每个候选 step 保留来源链，便于后续 witness 输出回指原始顺序图观测。
* [x] 对歧义场景保留多候选或 warning，而不是强行猜测唯一场景。

当前真实样例的 Phase 8 验证结论：

* 已可稳定生成 `24` 个 step 候选：
  - `6` 个 `emit` step：`s01 / s10 / s14 / s16 / s19 / s22`
  - `5` 个 `SetInput` step：`s02 / s04 / s06 / s08 / s20`
  - 其余为 self / outbound / empty anchor step
* 当前真实样例里的两条 `TimeConstraint` 更合适的语义应收敛为：
  - `between(s02, s03) in [0s, 1s]`
  - `between(s06, s07) in [0s, 1s]`
* 这两条约束不再推荐单独称为 step-local time window，而应和普通 duration constraint 使用统一表示；若全局 step 顺序本身不保证严格递增，则还需显式补上 `t02 < t03`、`t06 < t07` 这样的严格先后条件。
* 当前真实样例里的 outbound machine-relevant mismatch step 为 `s13 / s23 / s24`，分别对应 `Sig9 / Sig8 / Sig7`。
* 当前真实样例里的 duration constraint 已稳定绑定到具体 step 对：
  - `s05 -> s10 : 20s-30s`
  - `s11 -> s12 : 10s`
  - `s12 -> s13 : 15s`
  - `s13 -> s14 : 10s`
  - `s15 -> s16 : 10s`
  - `s17 -> s18 : 10s`
  - `s18 -> s19 : 5s`
  - `s19 -> s21 : 30s`
  - `s21 -> s22 : 5s`
* 当前样例里 step 候选与此前手工 timeline candidate 已基本收敛一致；后续阶段的重点将转向 runtime / SMT 绑定，而不是继续修补 observation 读取本身。

## 21.12 Phase 9: FCSTM 兼容导出收口

* [x] 保持 `pyfcstm.convert.sysdesim` 仍可对支持子集导出 FCSTM，作为调试与兼容产物。
* [x] 在 compatibility mode 中，把 `TriggerCondition` 回落成 guard transition。
* [x] 在 compatibility mode 中，把 `doActivity` 回落成 `during abstract ...`。
* [x] 在 compatibility mode 中，把 composite-source outgoing transition 回落成 `!H -> G : /Sig8;` 这类 force transition。
* [x] 对未参与状态机主干的非数值 property 直接忽略，不再阻塞导出。
* [ ] 对参与条件但仍无法安全表达的名字保留 warning，并在报告中显式列出。
* [ ] 对 init transition effect `ABC/DEF` 明确采用临时降级策略，并在导出报告中可见。
* [x] 明确当前真实样例的兼容导出是 output family，而不是单文件：main shell + `Control` 各 region split outputs。
* [ ] 让 compatibility mode 与 timeline-first mode 共用同一套前置抽取与归一化，不要形成两套分叉解析器。
* [x] 为当前真实样例提供“timeline-first 抽取成功，但 FCSTM 兼容导出允许部分降级”的清晰报告。

## 21.13 Phase 10: 接入 timeline runtime 与单步闭包求值

* [x] 把 SysDeSim timeline IR 转为 `TimelineScenario` 与 `TimelineMachineBinding` 候选对象。
* [x] 让 `event_map` 驱动每个 step 的 bound event 解析。
* [ ] 让 `input_map` 驱动 guard 的变量绑定环境。
* [x] 把 `SetInput` 候选应用到 step 输入快照上，并保证对当前 step 立即可见。
* [ ] 验证“无显式消息但有输入变化”的 step 仍会触发 guard-only / condition-only 迁移。
* [ ] 验证 `TriggerCondition` 在 timeline 里不需要单独再模拟一个外部事件对象，而是直接进入更新后快照上的条件求值。
* [ ] 为 `auto_transition` 引入隐藏内部时间变量 `t0 + delta1 + ... + deltaN` 的连续时间建模，并把它们绑定到“当前链起点之后最近一个 machine-facing emit”之前。
* [x] 对当前真实样例显式覆盖 `K -> S -> X` 这条链，要求 `K -> S` 之后的 `S -> X` 内部发生时刻严格早于下一次相关 inbound `Sig4`。
* [x] 明确当前样例对 `SimulationRuntime` 的复用边界，只把它当成一次性单步稳定配置推导器。

## 21.14 Phase 11: SMT 编译、反例重建与可解释性输出

* [x] 让来自真实样例的 imported scenario 能直接进入 timeline SMT 编译流程。
* [ ] 在 `build_guard_env(...)` 中优先绑定 `input_map` 对应的外部输入，而不是内部可写变量。
* [x] 在 witness 中同时输出 step 序号、时间变量、`SetInput`、`emit`、各机器稳定状态、触发该 step 的观测来源。
* [ ] 对 condition-trigger 命中增加解释字段，例如“由哪个输入更新使条件从 false 变 true”。
* [ ] 对无法唯一解释的 step 或 binding 保留 diagnostics，而不是只输出失败。
* [x] 确保 witness 能反查到“原始顺序图消息 / 赋值观测 -> step -> 状态变化”的链路。

当前实现补充说明：

- 已新增 `timeline_verify.py`，把 phase9 output family、phase10 runtime trace 与 phase11 的 Z3 共存查询串联起来。
- 当前真实样例里，`StateMachine__Control_region3` 会在 `s16` 和 `s19` 后生成隐藏 auto occurrence：
  - `StateMachine.Control.S -> StateMachine.Control.X`
- 当前真实样例里，`StateMachine__Control_region2.M` 与 `StateMachine__Control_region3.X` 的共存查询已可直接编码为 Z3 约束，结果为精确 `unsat`：
  - 原因不是时间约束冲突，而是 region2 的导入轨迹中根本没有出现 `M`

### 21.14.1 Phase 9-11 完整示例代码

下面这段代码是一个完整的、可直接运行的 Phase 9-11 样例。它刻意不写任何具体本地路径，只要求从命令行传入 XML 路径：

- Phase 9：打印 compatibility output family
- Phase 10：打印 step 序列与归一化时间约束
- Phase 11：打印单条共存 witness 时间轴表，重点展示“每个时间点发生了什么、各状态机当前状态是什么、首次共存从哪里开始”

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from pyfcstm.convert.sysdesim import (
    build_sysdesim_phase10_report,
    build_sysdesim_phase9_report,
    build_sysdesim_state_coexistence_timeline_report,
)


def _fit(text: str, width: int) -> str:
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _short_machine_alias(machine_alias: str) -> str:
    if machine_alias == "StateMachine":
        return "Main"
    if "_region" in machine_alias:
        return "R{}".format(machine_alias.rsplit("_region", 1)[-1])
    return machine_alias


def _short_state_text(state_path: str) -> str:
    if ".Control." in state_path:
        return state_path.split(".Control.", 1)[1]
    if state_path.endswith(".Control"):
        return "Control"
    return state_path.rsplit(".", 1)[-1]


def _format_actions(actions: Tuple[str, ...]) -> str:
    if not actions:
        return "-"
    rendered = []
    for item in actions:
        if item.startswith("hidden_auto(") and ": " in item and " -> " in item:
            prefix = item[len("hidden_auto(") : -1]
            machine_alias, arc = prefix.split(": ", 1)
            src, dst = arc.split(" -> ", 1)
            rendered.append(
                "tau:{alias} {src}->{dst}".format(
                    alias=_short_machine_alias(machine_alias),
                    src=_short_state_text(src),
                    dst=_short_state_text(dst),
                )
            )
        elif item.startswith("SetInput("):
            rendered.append(item[len("SetInput(") : -1])
        else:
            rendered.append(item)
    return ",".join(rendered)


def _print_timeline_table(
    timeline_points,
    first_symbol: Optional[str],
) -> None:
    headers = ["t", "pt", "act", "Main", "R1", "R2", "R3", "R4", "co"]
    widths = [6, 8, 16, 8, 8, 8, 8, 8, 8]

    def _row(values: List[str]) -> str:
        return "| " + " | ".join(
            _fit(item, width) for item, width in zip(values, widths)
        ) + " |"

    print("列说明：")
    print("  - t: 连续时间上的实数值。")
    print("  - pt: sXX 表示 step，tau@... 表示隐藏 auto。")
    print("  - Main/R1/R2/R3/R4: 主状态机与各 region 输出。")
    print("  - co: start 表示从该行开始首次共存，yes 表示该行时仍在共存。")
    print()
    print(_row(headers))
    print(_row(["-" * width for width in widths]))

    for item in timeline_points:
        state_map = {
            _short_machine_alias(alias): _short_state_text(state)
            for alias, state in item.machine_states
        }
        point_label = item.point_label
        if item.point_kind == "auto":
            point_label = "tau@{}".format(point_label)
        co_text = ""
        if item.is_coexistent:
            co_text = "start" if item.symbol == first_symbol else "yes"
        print(
            _row(
                [
                    item.time_value_text,
                    point_label,
                    _format_actions(item.actions),
                    state_map.get("Main", "-"),
                    state_map.get("R1", "-"),
                    state_map.get("R2", "-"),
                    state_map.get("R3", "-"),
                    state_map.get("R4", "-"),
                    co_text,
                ]
            )
        )


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print("用法: python phase9_11_demo.py path/to/model.xml", file=sys.stderr)
        return 2

    xml_path = Path(argv[1]).expanduser()
    if not xml_path.exists():
        print("XML 文件不存在。", file=sys.stderr)
        return 2

    phase9 = build_sysdesim_phase9_report(str(xml_path))
    phase10 = build_sysdesim_phase10_report(str(xml_path))
    sat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_path),
        "StateMachine__Control_region2",
        "L",
        "StateMachine__Control_region3",
        "X",
    )
    unsat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_path),
        "StateMachine__Control_region2",
        "M",
        "StateMachine__Control_region3",
        "X",
    )

    print("=" * 80)
    print("Phase9: output family")
    print("输出族:", [item.output_name for item in phase9.outputs])
    for item in phase9.outputs:
        print(
            "  - {name} | defines={defines} | events={events}".format(
                name=item.output_name,
                defines=list(item.define_names),
                events=list(item.event_runtime_refs),
            )
        )

    print("=" * 80)
    print("Phase10: scenario 摘要")
    print("step 序列:", [item.step_id for item in phase10.scenario.steps])
    print("时间约束:")
    for item in phase10.scenario.temporal_constraints:
        print(
            "  - {left} -> {right} | [{min_text}, {max_text}] | strict={strict}".format(
                left=item.left_step_id,
                right=item.right_step_id,
                min_text=item.min_seconds_text,
                max_text=item.max_seconds_text,
                strict=item.strict_lower,
            )
        )

    print("=" * 80)
    print("Phase11: 可共存查询")
    print("结果:", sat_timeline.status)
    print("时间域:", sat_timeline.time_domain)
    print(
        "首次共存: {symbol} = {time}".format(
            symbol=sat_timeline.first_coexistence_symbol,
            time=sat_timeline.first_coexistence_time_text,
        )
    )
    print("说明:", sat_timeline.first_coexistence_note)
    print()
    _print_timeline_table(
        sat_timeline.timeline_points,
        sat_timeline.first_coexistence_symbol,
    )

    print()
    print("=" * 80)
    print("Phase11: 不可共存查询")
    print("结果:", unsat_timeline.status)
    print("原因:", unsat_timeline.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

这段脚本的关键点是：

- 时间变量的求解域使用 `Z3 Real`，语义上是连续时间实数，展示时输出为普通十进制文本。
- Phase 11 不再强调“所有候选构造方式”，而是只输出一条 witness 时间轴。
- witness 时间轴会把普通 `step` 和隐藏 `auto transition` 都排到同一条时间线上。
- `co` 列可以直接看出“首次共存从哪一行开始”，以及后续哪些点仍然保持共存。

## 21.15 Phase 12: 测试、回归样例与 CLI

* [ ] 为真实样例建立固定测试夹具，不再只依赖临时本地文件。
* [ ] 覆盖至少三类测试：原始 XMI 抽取测试、timeline import IR 归一化测试、timeline 运行与 SMT 结果测试。
* [ ] 增加针对当前已知阻塞点的回归测试：非 `int/float` property 不应导致整体导入失败。
* [ ] 增加针对当前已知阻塞点的回归测试：`ChangeEvent` 不应再被直接判成 unsupported。
* [ ] 增加针对当前已知阻塞点的回归测试：同源同宿同条件的 `ChangeEvent/guard` 必须合并。
* [ ] 增加顺序图观测解析测试，验证 `name=value` 能稳定生成 `SetInput` 候选。
* [ ] 增加 timeline step 语义测试，验证“输入更新在当前 step 立即可见”。
* [ ] 为 CLI 或 report 输出增加 `--timeline-import-report` 一类入口，方便人工审查 binding 与 scenario 候选。

## 21.16 文档收口与后续扩展点

* [ ] 在 TIMELINE 文档中补一节“真实 SysDeSim 样例导入子系统”，说明主模式与兼容模式的区别。
* [ ] 在 SysDeSim 相关文档中明确引用 TIMELINE 这条主路线，避免继续把工作目标误写成“完整 XML -> FCSTM”。
* [ ] 补充一份开发者导图，说明 raw XMI index、machine extract、interaction extract、timeline IR、timeline binding 之间的关系。
* [ ] 明确第一阶段不做的内容，例如通用脚本动作求值、所有 UML 变体兼容、连续演化输入、混合系统语义。
* [ ] 在完成第一阶段后，再决定是否扩展到更多 SysDeSim 导出变体和更多 interaction 语法。

## 21.17 阶段完成判据

当下面这些条件都满足时，可以认为“真实 SysDeSim 样例已初步接入 TIMELINE”：

- 能稳定读取真实样例并生成 machine graph
- 不再因为无关枚举 property 而整体失败
- `ChangeEvent` 与 `guard` 已统一进入条件触发抽象
- 能从顺序图中抽取 `emit` 与 `SetInput` 候选
- 能生成可人工审查的 `event_map` / `input_map` / `step` 候选
- 能把这些候选喂给 timeline runtime / SMT 编译主链
- 能输出可解释的 witness / diagnostics

在这之前，不建议把工作完成标准定义为“能导出一个看起来像样的 FCSTM 文件”。对于当前真实样例，那只是辅助手段，不是主目标。

## 21.18 当前 `model1.xml` 的最小修改建议

针对当前真实样例，`region1` 的 `a < b` 与 `region2` 的 `c < d` 都缺少像 `y=...`、`Rmt=...` 那样可被顺序图导入器稳定识别的显式赋值观测。实际症状是：

- `a/b/c/d` 只在 guard 或条件里出现，但在 interaction 里没有对应的 `StateInvariant name=value` 观测。
- 因此导入后 `region2` 会长期停在 `F`，`region1` 也缺少把比较条件从 false 翻到 true 的明确证据。

为满足“**不修改原始 `model1.xml`**、只给出最小修正建议”的要求，建议在同路径创建 `model1_fixed.xml`，并仅增加顺序图上的 8 个 `StateInvariant` 片段，不改状态机结构、不改 transition、不改 guard。本次建议 diff 如下：

```diff
--- /home/hansbug/文档/damnx_sysdesim_sample/model1.xml
+++ /home/hansbug/文档/damnx_sysdesim_sample/model1_fixed.xml
@@ -99,30 +99,78 @@
           </ownedRule>
           <ownedAttribute xmi:type="uml:Property" xmi:id="_8YItACQGEfGBBP-2kAbLRg" name="控制"/>
           <ownedAttribute xmi:type="uml:Property" xmi:id="_8uzgkCQGEfGBBP-2kAbLRg" name="模块"/>
-          <lifeline xmi:type="uml:Lifeline" xmi:id="_8XZGICQGEfGBBP-2kAbLRg" name="控制" represents="_8YItACQGEfGBBP-2kAbLRg" coveredBy="_PtYDYCQHEfGBBP-2kAbLRg _R4wV0CQHEfGBBP-2kAbLRg _aV3sECQHEfGBBP-2kAbLRg _abpj8CQHEfGBBP-2kAbLRg _aZMF0CQHEfGBBP-2kAbLRg _OZ3XoCQIEfGBBP-2kAbLRg _OhtsECQIEfGBBP-2kAbLRg _qtZesCQIEfGBBP-2kAbLRg _qx49ICQIEfGBBP-2kAbLRg _5M_UwCQIEfGBBP-2kAbLRg _5QacMCQIEfGBBP-2kAbLRg _9eUAACQIEfGBBP-2kAbLRg _DIhJwCQJEfGBBP-2kAbLRg _DO760CQJEfGBBP-2kAbLRg _OpCmpCQJEfGBBP-2kAbLRg _OtLfwCQJEfGBBP-2kAbLRg _JEPE0CQKEfGBBP-2kAbLRg _JKMi4CQKEfGBBP-2kAbLRg _0jTh8CQKEfGBBP-2kAbLRg _GVfxMCQLEfGBBP-2kAbLRg _GeQroCQLEfGBBP-2kAbLRg _T4zlMCQLEfGBBP-2kAbLRg _T_ifUCQLEfGBBP-2kAbLRg _ZEsbQCQLEfGBBP-2kAbLRg _ZLJokCQLEfGBBP-2kAbLRg _belq1CQLEfGBBP-2kAbLRg _bh9u8CQLEfGBBP-2kAbLRg _nY7V4CQLEfGBBP-2kAbLRg _nf3EUCQLEfGBBP-2kAbLRg _r3ZsUCQLEfGBBP-2kAbLRg _r78OECQLEfGBBP-2kAbLRg _zQZTICQLEfGBBP-2kAbLRg _zWt9kCQLEfGBBP-2kAbLRg _6x2SYCQLEfGBBP-2kAbLRg _6386YCQLEfGBBP-2kAbLRg _APY5JCQMEfGBBP-2kAbLRg _ATA04CQMEfGBBP-2kAbLRg _HmlJICQMEfGBBP-2kAbLRg _HseVwCQMEfGBBP-2kAbLRg _O5tYgCQMEfGBBP-2kAbLRg _PA3wcCQMEfGBBP-2kAbLRg _BXTRgCQOEfGBBP-2kAbLRg _FJDE0CQOEfGBBP-2kAbLRg _FONRoCQOEfGBBP-2kAbLRg _FMlhACQOEfGBBP-2kAbLRg"/>
+          <lifeline xmi:type="uml:Lifeline" xmi:id="_8XZGICQGEfGBBP-2kAbLRg" name="控制" represents="_8YItACQGEfGBBP-2kAbLRg" coveredBy="_PtYDYCQHEfGBBP-2kAbLRg codex_fix_a0_frag codex_fix_b0_frag codex_fix_c0_frag codex_fix_d0_frag _R4wV0CQHEfGBBP-2kAbLRg codex_fix_a1_frag codex_fix_b1_frag _aV3sECQHEfGBBP-2kAbLRg _abpj8CQHEfGBBP-2kAbLRg _aZMF0CQHEfGBBP-2kAbLRg _OZ3XoCQIEfGBBP-2kAbLRg _OhtsECQIEfGBBP-2kAbLRg _qtZesCQIEfGBBP-2kAbLRg _qx49ICQIEfGBBP-2kAbLRg _5M_UwCQIEfGBBP-2kAbLRg _5QacMCQIEfGBBP-2kAbLRg _9eUAACQIEfGBBP-2kAbLRg _DIhJwCQJEfGBBP-2kAbLRg _DO760CQJEfGBBP-2kAbLRg _OpCmpCQJEfGBBP-2kAbLRg _OtLfwCQJEfGBBP-2kAbLRg _JEPE0CQKEfGBBP-2kAbLRg _JKMi4CQKEfGBBP-2kAbLRg _0jTh8CQKEfGBBP-2kAbLRg codex_fix_c1_frag codex_fix_d1_frag _GVfxMCQLEfGBBP-2kAbLRg _GeQroCQLEfGBBP-2kAbLRg _T4zlMCQLEfGBBP-2kAbLRg _T_ifUCQLEfGBBP-2kAbLRg _ZEsbQCQLEfGBBP-2kAbLRg _ZLJokCQLEfGBBP-2kAbLRg _belq1CQLEfGBBP-2kAbLRg _bh9u8CQLEfGBBP-2kAbLRg _nY7V4CQLEfGBBP-2kAbLRg _nf3EUCQLEfGBBP-2kAbLRg _r3ZsUCQLEfGBBP-2kAbLRg _r78OECQLEfGBBP-2kAbLRg _zQZTICQLEfGBBP-2kAbLRg _zWt9kCQLEfGBBP-2kAbLRg _6x2SYCQLEfGBBP-2kAbLRg _6386YCQLEfGBBP-2kAbLRg _APY5JCQMEfGBBP-2kAbLRg _ATA04CQMEfGBBP-2kAbLRg _HmlJICQMEfGBBP-2kAbLRg _HseVwCQMEfGBBP-2kAbLRg _O5tYgCQMEfGBBP-2kAbLRg _PA3wcCQMEfGBBP-2kAbLRg _BXTRgCQOEfGBBP-2kAbLRg _FJDE0CQOEfGBBP-2kAbLRg _FONRoCQOEfGBBP-2kAbLRg _FMlhACQOEfGBBP-2kAbLRg"/>
           <lifeline xmi:type="uml:Lifeline" xmi:id="_8twXtCQGEfGBBP-2kAbLRg" name="模块" represents="_8uzgkCQGEfGBBP-2kAbLRg" coveredBy="_Ob0fdCQIEfGBBP-2kAbLRg _OfpPgCQIEfGBBP-2kAbLRg _qrKqECQIEfGBBP-2kAbLRg _qz-AwCQIEfGBBP-2kAbLRg _5LhVICQIEfGBBP-2kAbLRg _5RtcsCQIEfGBBP-2kAbLRg _DKAXhCQJEfGBBP-2kAbLRg _DNsksCQJEfGBBP-2kAbLRg _Om878CQJEfGBBP-2kAbLRg _OumcECQJEfGBBP-2kAbLRg _JFlvsCQKEfGBBP-2kAbLRg _JI5iYCQKEfGBBP-2kAbLRg _GXofNCQLEfGBBP-2kAbLRg _GccGsCQLEfGBBP-2kAbLRg _T6tpsCQLEfGBBP-2kAbLRg _T-O3wCQLEfGBBP-2kAbLRg _ZGhAMCQLEfGBBP-2kAbLRg _ZJ5EUCQLEfGBBP-2kAbLRg _bdNKwCQLEfGBBP-2kAbLRg _bjXdICQLEfGBBP-2kAbLRg _naNvUCQLEfGBBP-2kAbLRg _neRI4CQLEfGBBP-2kAbLRg _r1x7sCQLEfGBBP-2kAbLRg _r9ftQCQLEfGBBP-2kAbLRg _zR4g5CQLEfGBBP-2kAbLRg _zVeAYCQLEfGBBP-2kAbLRg _6zVgICQLEfGBBP-2kAbLRg _62s9MCQLEfGBBP-2kAbLRg _ANmwcCQMEfGBBP-2kAbLRg _AUPj8CQMEfGBBP-2kAbLRg _Hn6l5CQMEfGBBP-2kAbLRg _HrNxgCQMEfGBBP-2kAbLRg _O7C1RCQMEfGBBP-2kAbLRg _O_FAsCQMEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_5RtcsCQIEfGBBP-2kAbLRg" name="sendEvent" covered="_8twXtCQGEfGBBP-2kAbLRg" message="_5OOD1CQIEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_5QacMCQIEfGBBP-2kAbLRg" name="receiveEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_5OOD1CQIEfGBBP-2kAbLRg"/>
-          <fragment xmi:type="uml:StateInvariant" xmi:id="_PtYDYCQHEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
-            <invariant xmi:type="uml:Constraint" xmi:id="_Pu0N0CQHEfGBBP-2kAbLRg" name="">
-              <specification xmi:type="uml:OpaqueExpression" xmi:id="_PvdHACQHEfGBBP-2kAbLRg">
-                <language>English</language>
-                <body>y=2300</body>
-              </specification>
-            </invariant>
-          </fragment>
-          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_abpj8CQHEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_aXfcsCQHEfGBBP-2kAbLRg"/>
-          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_aZMF0CQHEfGBBP-2kAbLRg" name="receiveEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_aXfcsCQHEfGBBP-2kAbLRg"/>
-          <fragment xmi:type="uml:StateInvariant" xmi:id="_R4wV0CQHEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
-            <invariant xmi:type="uml:Constraint" xmi:id="_R6L5MCQHEfGBBP-2kAbLRg" name="">
-              <specification xmi:type="uml:OpaqueExpression" xmi:id="_R6rocCQHEfGBBP-2kAbLRg">
-                <language>English</language>
-                <body>y=2099</body>
-              </specification>
-            </invariant>
-          </fragment>
-          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_OhtsECQIEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_OdkL5CQIEfGBBP-2kAbLRg"/>
-          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_OfpPgCQIEfGBBP-2kAbLRg" name="receiveEvent" covered="_8twXtCQGEfGBBP-2kAbLRg" message="_OdkL5CQIEfGBBP-2kAbLRg"/>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="_PtYDYCQHEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="_Pu0N0CQHEfGBBP-2kAbLRg" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="_PvdHACQHEfGBBP-2kAbLRg">
+                <language>English</language>
+                <body>y=2300</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_a0_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_a0_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_a0_expr">
+                <language>English</language>
+                <body>a=5</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_b0_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_b0_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_b0_expr">
+                <language>English</language>
+                <body>b=1</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_c0_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_c0_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_c0_expr">
+                <language>English</language>
+                <body>c=5</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_d0_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_d0_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_d0_expr">
+                <language>English</language>
+                <body>d=1</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_abpj8CQHEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_aXfcsCQHEfGBBP-2kAbLRg"/>
+          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_aZMF0CQHEfGBBP-2kAbLRg" name="receiveEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_aXfcsCQHEfGBBP-2kAbLRg"/>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="_R4wV0CQHEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="_R6L5MCQHEfGBBP-2kAbLRg" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="_R6rocCQHEfGBBP-2kAbLRg">
+                <language>English</language>
+                <body>y=2099</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_a1_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_a1_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_a1_expr">
+                <language>English</language>
+                <body>a=1</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_b1_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_b1_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_b1_expr">
+                <language>English</language>
+                <body>b=2</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_OhtsECQIEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_OdkL5CQIEfGBBP-2kAbLRg"/>
+          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_OfpPgCQIEfGBBP-2kAbLRg" name="receiveEvent" covered="_8twXtCQGEfGBBP-2kAbLRg" message="_OdkL5CQIEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:StateInvariant" xmi:id="_BXTRgCQOEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
             <invariant xmi:type="uml:Constraint" xmi:id="_BZPLMCQOEfGBBP-2kAbLRg" name="">
               <specification xmi:type="uml:OpaqueExpression" xmi:id="_BZ_ZICQOEfGBBP-2kAbLRg">
@@ -133,15 +181,31 @@
           </fragment>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_FONRoCQOEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_FKi5oCQOEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_FMlhACQOEfGBBP-2kAbLRg" name="receiveEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_FKi5oCQOEfGBBP-2kAbLRg"/>
-          <fragment xmi:type="uml:StateInvariant" xmi:id="_0jTh8CQKEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
-            <invariant xmi:type="uml:Constraint" xmi:id="_0lhvgCQKEfGBBP-2kAbLRg" name="">
-              <specification xmi:type="uml:OpaqueExpression" xmi:id="_0micICQKEfGBBP-2kAbLRg">
-                <language>English</language>
-                <body>y=1199</body>
-              </specification>
-            </invariant>
-          </fragment>
-          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_GeQroCQLEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_GZuJ5CQLEfGBBP-2kAbLRg"/>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="_0jTh8CQKEfGBBP-2kAbLRg" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="_0lhvgCQKEfGBBP-2kAbLRg" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="_0micICQKEfGBBP-2kAbLRg">
+                <language>English</language>
+                <body>y=1199</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_c1_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_c1_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_c1_expr">
+                <language>English</language>
+                <body>c=1</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:StateInvariant" xmi:id="codex_fix_d1_frag" name="" covered="_8XZGICQGEfGBBP-2kAbLRg">
+            <invariant xmi:type="uml:Constraint" xmi:id="codex_fix_d1_constraint" name="">
+              <specification xmi:type="uml:OpaqueExpression" xmi:id="codex_fix_d1_expr">
+                <language>English</language>
+                <body>d=2</body>
+              </specification>
+            </invariant>
+          </fragment>
+          <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_GeQroCQLEfGBBP-2kAbLRg" name="sendEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_GZuJ5CQLEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_GccGsCQLEfGBBP-2kAbLRg" name="receiveEvent" covered="_8twXtCQGEfGBBP-2kAbLRg" message="_GZuJ5CQLEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_qz-AwCQIEfGBBP-2kAbLRg" name="sendEvent" covered="_8twXtCQGEfGBBP-2kAbLRg" message="_qviMsCQIEfGBBP-2kAbLRg"/>
           <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="_qx49ICQIEfGBBP-2kAbLRg" name="receiveEvent" covered="_8XZGICQGEfGBBP-2kAbLRg" message="_qviMsCQIEfGBBP-2kAbLRg"/>
```

这些新增观测的语义安排是：

- 初始先令比较条件不成立：`a=5`、`b=1`、`c=5`、`d=1`
- 在较后的顺序图位置再把条件翻转为成立：`a=1`、`b=2`、`c=1`、`d=2`
- 插入位置尽量贴近已有 `y=...` 观测：
  - `y=2300` 后插入 `a/b/c/d` 的初值
  - `y=2099` 后插入 `a/b` 的翻转值
  - `y=1199` 后插入 `c/d` 的翻转值

按这份最小修正，`model1.xml` 原文件可保持不动，而 `model1_fixed.xml` 可以让导入器稳定得到：

- `region1`: `A -> B -> C -> D -> EState`
- `region2`: `F -> W -> H.L`
- `region3.X` 与 `region2.L` 在时间 `67` 处首次共存
