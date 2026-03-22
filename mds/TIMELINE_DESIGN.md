# timeline 连续时间场景验证设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
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

## 11.1.1 形式化验证目标

在第一阶段问题边界内，可以把整个问题写成一个有限约束系统：

- 已知：
  - 有限个 step
  - 有限个外部输入
  - 有限个状态机
  - 每个状态机有限个稳定配置
- 求：
  - 是否存在一组时间取值、输入轨迹和机器配置轨迹
  - 使得所有场景约束都成立
  - 且某个关系约束在某个观测点被违反

因此，验证问题可以归约为：

```text
Exists time_values, input_values, machine_configs :
    ScenarioConstraints
    and MachineTransitionConstraints
    and RelationViolation
```

也就是一个标准的 SMT satisfiability 问题。

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
- 再对每个机器、每个观测点直接建立配置变量
- 把“这个 step 之后配置应该是什么”一次性展开成约束

所以它更接近：

- bounded model checking

而不是：

- symbolic graph exploration

## 11.1.3 整体算法流程

建议把实现拆成下面 8 个阶段：

1. 解析 `.fcstm`，得到 `StateMachine` model object。
2. 对所有机器做支持子集检查。
3. 归一化 scenario YAML，得到有序 `steps`、输入定义、时间约束、bindings、relations。
4. 为每个机器预编译“稳定配置集合”和“按声明顺序的候选迁移表”。
5. 创建 Z3 变量：
   - 时间变量
   - 输入快照变量
   - 配置变量
   - 关系命中布尔量
6. 生成场景约束：
   - 时间约束
   - 初始输入
   - `set` 传播
7. 生成机器约束：
   - 初始配置
   - 每个 step 的离散迁移关系
8. 生成关系违规约束并调用求解器。

这 8 步里，第 4 步和第 7 步是实现核心。

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

- 对所有机器都有 `Q[m, k+1] = Q[m, k]`
- 只更新输入快照

这点非常关键，因为它让“输入先变化，再触发事件”可被精确表达。

## 11.6.1 空 step 的机器约束

若某个 step：

- 没有 `emit`
- 也没有 `set`

则它只是一个逻辑时间节点。

此时机器约束也自然退化为：

- 对所有机器都有 `Q[m, k+1] = Q[m, k]`

这和“只包含输入更新、不含事件”的 step 只有一步之差：

- 输入更新 step 会改输入快照，不改机器配置
- 空 step 既不改输入快照，也不改机器配置

因此空 step 不需要额外特殊语义，只需在输入和机器传播规则里自然落下即可。

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
