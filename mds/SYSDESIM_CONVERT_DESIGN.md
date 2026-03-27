# SysDeSim UML 状态机到 FCSTM 转换设计草案

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.2.0 | 2026-03-17 | 根据进一步讨论调整方案：改为基于 `pyfcstm.dsl` AST Node 构建、模块名改为 `convert`、细化命名规约、变量映射、时间单位与 phase/checklist 组织 | Codex |
| 0.1.0 | 2026-03-17 | 初始版本，整理 SysDeSim XMI/UML 状态机到 FCSTM 的转换目标、IR 设计、lowering 规则、phase 与 checklist | Codex |

---

## 1. 设计目标

本文讨论如何将 SysDeSim 导出的 UML 状态机 XML/XMI 文件转换为当前仓库已经支持的 FCSTM DSL，并以 `pyfcstm.dsl` 中的 AST Node 作为 FCSTM 侧的结构承载。

关于当前样例 XML/XMI 文件本身的结构拆解、图层元数据组织方式，以及状态机图和顺序图在同一文件中的挂接关系，见配套的 XML 格式分析文档。

本文的核心目标是：

- 在 **不改造现有 FCSTM DSL 语法结构** 的前提下完成转换
- 尽量复用当前 `pyfcstm` 的 runtime、parser、model 和 render 能力
- 对 SysDeSim 中常见的 UML 结构给出稳定、可实现、可测试的 lowering 方案
- 对当前无法原生表达的语义明确给出降级策略、拆分策略或拒绝策略

本文的核心结论是：

- 转换器应采用 **三段式架构**：`SysDeSim XML -> SysDeSim IR -> pyfcstm.dsl AST Node -> DSL 文本`
- `uml:TimeEvent` 不应要求 FCSTM 新增 `after(...)` 语法，而应直接按内部变量与 guard 进行 lowering
- 跨层 transition 不能直接映射，必须 lower 成 **flag 驱动的退出链 + 条件化进入链**
- multi-region 并发状态当前不做强行语义兼容，而是按 region 拆分成多个独立状态机

---

## 2. 输入现状与仓库边界

### 2.1 当前样例文件的关键结构

以当前仓库根目录下的 `test_com.sysdesim.metamodel.model.xml` 为例，可以确认：

- 顶层对象是 `uml:Model`
- 状态机实体是 `uml:StateMachine`
- 层级结构通过 `uml:Region` 和 `subvertex` 表达
- 状态使用 `uml:State`
- 初始伪状态使用无名 `uml:Pseudostate`
- 事件触发既有 `uml:SignalEvent`，也有 `uml:TimeEvent`
- 生命周期动作和转移动作通过 `entry`、`exit`、`effect` 关联 `uml:Activity`
- 样例中存在至少一个 `3 region` 的复合状态，因此并发语义真实存在

### 2.2 当前 FCSTM 的能力边界

当前 FCSTM DSL 与 runtime 的关键限制包括：

- 状态是单 active path 的层级状态机，不支持原生并发 region
- 复合状态必须有显式 `[*] -> 子状态` 入口
- 父状态上的 transition 只有在当前子状态先 `-> [*]` 退出后才会被 runtime 考虑
- 现有 DSL 没有 transition 级别的 `after(...)`
- DSL 的 `ID` 只能是 ASCII 标识符，不支持中文直接作为状态名或事件名

因此，转换器的工作不是“把 XML 换个格式输出”，而是做一次有约束的语义重写。

---

## 3. 设计总原则

### 3.1 先建模，再输出

转换器不应直接从 XML 拼接 FCSTM 文本。
SysDeSim IR 到 FCSTM 的这一层，应优先构建 `pyfcstm.dsl.node` 中的 AST Node，再由 AST Node 自带的无损字符串化能力输出 DSL。

推荐流程：

1. 从 XML 解析出 SysDeSim/UML 中间 IR
2. 在 IR 上执行命名归一化、init 推断、time-event lowering、跨层 lowering、region 拆分
3. 将结果构建为 `pyfcstm.dsl` AST Node，例如 `StateMachineDSLProgram`、`StateDefinition`、`EventDefinition`、`TransitionDefinition`
4. 仅在最终输出时，将 AST Node 转为 DSL 文本
5. 立即用现有 parser 回读校验，保证输出 DSL 本身合法

### 3.2 优先保证结构合法，其次追求语义接近

对于 SysDeSim 中无法被当前 FCSTM 无损表达的语义：

- 首先保证输出的 FCSTM 在当前仓库内是可解析、可建模、可模拟的
- 其次通过 lowering 尽量逼近原语义
- 若仍无法逼近，则显式降级或拆分，不做“看起来像成功”的错误映射

### 3.3 降级规则必须可解释

每一种 lowering 都应满足：

- 转换器可以程序化实现
- 转换结果能被人类追踪和审查
- 需要时可回溯到原始 XML 中的对象与路径

### 3.4 内部对象必须稳定命名

所有编译器内部生成的变量、事件、状态、桥接 transition，其命名都应：

- 使用保留前缀
- 仅使用 ASCII
- 与用户原始命名隔离
- 在重复转换时稳定可重现
- 不仅依赖“人类可读名字”，还必须携带足够的结构唯一性信息

推荐前缀：

- 内部变量：`__sysdesim_*`
- 内部事件：`__sysdesim_evt_*`
- 内部 flag：`__sysdesim_flag_*`
- 内部 route id：`__sysdesim_route_*`

对所有 `__sysdesim_*` 内部对象，建议统一采用：

```text
<prefix> + <human_readable_scope_part> + <stable_unique_suffix>
```

其中：

- `human_readable_scope_part` 用于可读性，通常来自状态路径或语义类别
- `stable_unique_suffix` 用于真正避免重名，建议来自稳定的 `xmi:id` / `transition_id` / `signal_id`
- 若某对象没有可直接复用的唯一 id，则使用基于其结构签名的稳定哈希

换句话说：

- 内部名不能只靠状态名
- 也不能只靠事件名
- 必须把作用域路径和稳定唯一后缀一起带上

这条规则尤其适用于：

- 不同复合状态下的同名事件
- 不同层级下的同名状态
- 同一 source state 上的多条 timeout transition
- 所有 route flag、bridge、timeout lowering 生成物

---

## 4. 总体架构

### 4.1 建议模块划分

建议新增一个独立转换模块，例如：

```text
pyfcstm/convert/sysdesim/
    __init__.py
    xml_loader.py
    ir.py
    normalize.py
    build_ast.py
    lower_timeevent.py
    lower_crosslevel.py
    split_parallel.py
    emit_dsl.py
    validate.py
```

其中职责建议如下：

- `xml_loader.py`
  - 负责读取 XML/XMI
  - 建立 `xmi:id -> element` 索引
  - 解析 UML 基本对象
- `ir.py`
  - 定义中间 IR 数据结构
- `normalize.py`
  - 负责命名归一化、显示名保留、init 推断
- `build_ast.py`
  - 负责将 lowering 后的 SysDeSim IR 构建为 `pyfcstm.dsl` AST Node
- `lower_timeevent.py`
  - 负责 `uml:TimeEvent` 降级
- `lower_crosslevel.py`
  - 负责跨层 transition 降级
- `split_parallel.py`
  - 负责 multi-region 状态拆分
- `emit_dsl.py`
  - 负责将 AST Node 序列化为 DSL 文本
- `validate.py`
  - 负责一致性检查、unsupported 检查、回读校验

### 4.2 推荐执行流水线

```text
SysDeSim XML
  -> 解析原始 UML 图
  -> 构建 SysDeSim IR
  -> 命名归一化
  -> init state 推断
  -> parallel region 预扫描
  -> 按策略拆分 machine
  -> time-event lowering
  -> 跨层 transition lowering
  -> 构建 pyfcstm.dsl AST Node
  -> AST Node 转 DSL 文本
  -> FCSTM parser/model 回读校验
```

---

## 5. 中间 IR 设计

### 5.1 为什么必须有 IR

如果直接从 XML 输出 DSL，会立刻遇到以下问题：

- XML 中 source/target 通过 `xmi:id` 关联，不是树内局部名字
- transition 的逻辑语义需要参考祖先关系、region 关系、LCA
- 某些 lowering 会新增内部变量、内部 transition、条件化 init
- multi-region 拆分会复制部分祖先结构并裁剪部分子树

这些操作都要求一个可变、可遍历、可重写的数据模型。
该数据模型建议统一采用 `@dataclass` 定义。

### 5.2 最小 IR 对象建议

建议至少定义以下 `dataclass` 对象：

#### `IrMachine` (`@dataclass`)

- `machine_id`
- `name`
- `root_region`
- `signals`
- `signal_events`
- `time_events`
- `diagnostics`

#### `IrRegion` (`@dataclass`)

- `region_id`
- `owner_state_id`，顶层 region 可为 `None`
- `vertices`
- `transitions`

#### `IrVertex` (`@dataclass`)

公共字段：

- `vertex_id`
- `vertex_type`，例如 `state`、`pseudostate`、`final`
- `raw_name`
- `safe_name`
- `display_name`
- `parent_region_id`
- `entry_action`
- `exit_action`
- `state_invariant`

对 `state` 额外字段：

- `regions`
- `is_composite`
- `is_parallel_owner`

#### `IrTransition` (`@dataclass`)

- `transition_id`
- `source_id`
- `target_id`
- `trigger_kind`，例如 `signal`、`time`、`none`
- `trigger_ref_id`
- `guard_expr_raw`
- `guard_expr_ir`
- `effect_action`
- `source_region_id`
- `target_region_id`
- `is_cross_level`
- `is_cross_region`
- `origin_kind`，例如 `original`、`lowered_timeout`、`lowered_crosslevel`

#### `IrSignal` (`@dataclass`)

- `signal_id`
- `raw_name`
- `safe_name`
- `display_name`

#### `IrTimeEvent` (`@dataclass`)

- `time_event_id`
- `raw_literal`，例如 `2s`
- `is_relative`
- `normalized_delay`
- `normalized_unit`

### 5.3 IR 上必须可快速查询的信息

IR 构建完成后，应至少支持以下查询：

- `vertex_id -> vertex`
- `transition_id -> transition`
- `event_id -> event`
- `region_id -> region`
- `vertex -> parent state path`
- `vertex -> owning region`
- `state -> all descendant states`
- `state -> region count`
- `source/target -> LCA`
- `transition -> 是否跨层`
- `transition -> 是否跨 region`

---

## 6. 命名与显示名策略

### 6.1 问题来源

SysDeSim XML 中的状态名、事件名、动作名可能包含：

- 中文
- 空格
- 特殊符号
- 重名
- 空字符串

而当前 FCSTM 的 `ID` 必须是 `[a-zA-Z_][a-zA-Z0-9_]*`。

因此必须区分：

- **内部标识名**
- **展示名**

### 6.2 总体命名规约

对于需要新生成或归一化的标识符，建议采用以下统一风格：

- 状态 `state` 名称：**UpperCamelCase**
- 事件 `event` 名称：**UPPER_SNAKE_CASE**
- 变量名称：**lower_snake_case**
- 内部保留对象：继续使用 `__sysdesim_*`

其中必须额外区分：

- SysDeSim 中 **显式定义的变量**
- 转换器 **合成的变量**

二者规则不同，详见第 7 章。

### 6.3 状态与事件的命名规则

对于状态、事件、动作名：

- `safe_name` 使用人类友好的命名风格归一化，而不是简单原样保留
- `display_name` 保留原始中文名称
- 若归一化后重名，则追加稳定后缀
- 若原始名称为空，则使用基于类型和 `xmi:id` 的保底名

示例：

```text
原始状态名: 航路飞行
safe_name: HangLuFeiXing
display_name: 航路飞行

原始事件名: 到达攻击入射角角度
safe_name: DAO_DA_GONG_JI_RU_SHE_JIAO_JIAO_DU
display_name: 到达攻击入射角角度

原始状态名: ""
safe_name: __sysdesim_pseudo_7Yk
display_name: ""
```

### 6.4 FCSTM 输出策略

建议导出时采用：

```fcstm
state HangLuFeiXing named "航路飞行";
event DAO_DA_GONG_JI named "到达攻击";
```

即：

- 内部路径引用永远使用 `safe_name`
- 对用户展示的语义信息使用 `named "..."` 保留
- 当前仓库中的中文状态名、中文事件名，一概通过 `named` 保留，不直接作为 DSL `ID`

### 6.5 动作命名规则

对于 `entry`、`exit`、`effect` 关联的 activity 名称：

- 若需要生成抽象动作名，建议使用 **UpperCamelCase**
- 原始中文 activity 名称保留到注释或 metadata

### 6.6 重名处理策略

若同一作用域下归一化后发生重名，应按稳定规则追加后缀，例如：

```text
HangLuFeiXing
HangLuFeiXing_2
HangLuFeiXing_3
```

后缀生成必须与遍历顺序稳定绑定，避免同一输入文件多次转换输出不同。

对于内部对象，建议优先使用“稳定唯一后缀”而不是简单的 `_2`、`_3`。
推荐顺序为：

1. 优先使用原始 UML 对象的稳定 id 片段
2. 若没有单一对象 id，则使用结构签名哈希
3. 只有在完全无法取得稳定来源时，才退化为作用域内序号

---

## 7. 变量定义映射

### 7.1 显式变量与合成变量必须区分

SysDeSim 中的变量来源至少分为两类：

- **显式定义变量**
- **转换器合成变量**

这两类变量不应混用同一套命名策略。

### 7.2 显式变量的保留规则

对于 SysDeSim 中显式定义的变量：

- 在 FCSTM `def` 部分应尽量保持 **原名**
- 在 FCSTM `def` 部分应尽量保持 **原类型**
- 不对其做人为风格化重命名

换句话说：

- 状态和事件需要按友好风格重命名
- 但显式变量不应因为风格统一而被改名

### 7.3 显式变量名称合法性

由于当前 FCSTM `ID` 仍要求 ASCII 标识符，因此对显式变量有两种可能策略：

- 若原名本身已经符合 FCSTM `ID` 规则，则直接原样保留
- 若原名不符合 FCSTM `ID` 规则，则第一阶段直接报错，不自动改名

这样可以满足“保持原名”的要求，避免后续语义对不上。

### 7.4 显式变量类型映射

第一阶段建议只支持能直接映射到 FCSTM 当前定义的类型：

- `int`
- `float`

若 SysDeSim 中出现更复杂类型，应：

- 记录原始类型
- 明确报 unsupported

### 7.5 合成变量命名规则

转换器为 lowering 新增的内部变量不受“原名保留”约束，统一使用：

- `lower_snake_case`
- `__sysdesim_*` 保留前缀

例如：

```text
__sysdesim_after_hang_lu_fei_xing_ticks
__sysdesim_flag_route_001
```

### 7.6 FCSTM AST 映射

显式变量和合成变量都应优先映射为 `pyfcstm.dsl.node.DefAssignment`，再并入 `StateMachineDSLProgram.definitions`。

---

## 8. 初始伪状态推断规则

### 8.1 背景

SysDeSim 模型中未必显式存在“init state”这一抽象概念，但 UML region 中常有一个：

- 无名
- 只出不进
- 类型为 `uml:Pseudostate`

的伪状态。

该结构可直接解释为 FCSTM 的 `[*]`。

### 8.2 判定规则

在每个 region 内，对 `uml:Pseudostate` 执行以下判断：

- `raw_name == ""`
- `in_degree == 0`
- `out_degree > 0`

若满足，则认定为该 region 的初始化伪状态。

### 8.3 输出规则

该伪状态本身不导出为显式 FCSTM 状态，而是将其 outgoing transition 导出为：

```fcstm
[*] -> TargetState;
```

### 8.4 异常规则

以下情况应直接报错或标记 unsupported：

- 一个 region 有多个满足条件的无名初始伪状态
- 该伪状态有多个 outgoing transition 且转换条件无法线性化
- 该 region 没有任何可推断 init，但其 owner state 是 composite

### 8.5 非 init 伪状态

若某个 `uml:Pseudostate` 不满足上述规则，则不应自动当作 init。

第一阶段建议：

- 若其参与普通路由且不能安全映射，直接报 unsupported
- 后续如有必要，再讨论是否映射为 FCSTM 的 `pseudo state`

---

## 9. 事件模型映射

### 9.1 Signal / SignalEvent

SysDeSim XML 中常见模式为：

- `uml:Signal`
- `uml:SignalEvent`
- `transition.trigger.event -> SignalEvent`
- `SignalEvent.signal -> Signal`

建议统一映射为 FCSTM 事件定义。

### 9.2 事件作用域策略

为了减少歧义，建议第一版统一输出为 **根作用域事件**：

- 所有导出的 signal 事件都挂在根状态下
- 所有 transition 使用绝对事件引用 `: /EventName`

这样做的原因是：

- SysDeSim 中 signal 本身通常是全局语义
- 可以避免局部作用域事件重名和路径歧义
- 更利于跨 region 拆分后的 machine 复用同一套事件命名

若出现“不同复合状态下 raw name 相同，但并不应视为同一个事件”的情况，必须进一步区分：

- 若多个 `SignalEvent` 最终引用的是同一个 `Signal` id，则可合并为同一个 FCSTM event
- 若它们并不指向同一个底层 UML 事件对象，则即便显示名相同，也必须生成不同的 FCSTM event `name`

因此事件命名不能只基于显示名。
建议使用：

```text
<EVENT_UPPER_SNAKE> + <optional_scope_part> + <stable_unique_suffix>
```

而原始中文或用户可读名称继续放在 `named "..."` 中。

### 9.3 无 trigger transition

无 trigger 的 transition：

- 若也无 guard，则导出为普通无条件 transition
- 若有 guard，则导出为 guard transition

### 9.4 TimeEvent

`uml:TimeEvent` 不直接导出为 FCSTM 事件。

它应在 lowering 阶段转换为：

- 内部 timer 变量
- enter/during/aspect 赋值
- 普通 guard condition

详见第 12 章。

---

## 10. 生命周期动作与 effect 的映射

### 10.1 状态 entry / exit

SysDeSim 中的：

- `state.entry -> uml:Activity`
- `state.exit -> uml:Activity`

建议第一版映射为 FCSTM 抽象动作：

```fcstm
enter abstract GaoDuKongZhiFuWuQiDong;
exit abstract GaoDuKongZhiFuWuTingZhi;
```

若需要保留原中文名，则不建议在当前阶段强行塞进 DSL 语法本身。
更稳妥的方案是：

- 动作函数名使用 `safe_name`
- 原始名字放在注释或 metadata 中

### 10.2 transition effect

SysDeSim 的 transition `effect` 在语义上接近 FCSTM transition effect block。

但当前 XML 中看到的 `effect` 往往只是一个 `uml:Activity` 名称，而没有直接等价的 FCSTM 语句体。

因此第一版建议：

- 不尝试把 `effect activity` 展开为可执行赋值语句
- 若只有动作名称，则保留为 metadata 或转换报告中的说明
- 不伪造空 `effect {}`，避免让用户误以为已无损保留

### 10.3 后续增强方向

若未来 SysDeSim activity 图本身也需要被导入，可以另开设计：

- `uml:Activity` 到 FCSTM abstract handler
- 或 `uml:Activity` 到独立行为模型

这不属于当前阶段的主目标。

---

## 11. 复合状态与单 region 映射

### 11.1 单 region 复合状态

若某个 `uml:State` 仅包含 1 个 region，则可自然映射为 FCSTM composite state：

```fcstm
state Parent {
    state ChildA;
    state ChildB;
    [*] -> ChildA;
    ChildA -> ChildB : /Evt;
}
```

### 11.2 state invariant

样例中某些状态带 `stateInvariant`。

第一版建议：

- 不将其直接映射为 FCSTM guard 或 during
- 将其纳入转换报告
- 若 invariant 为空，则忽略
- 若 invariant 非空，则标记为 `unsupported-but-recorded`

因为当前 FCSTM 没有一一对应的 “状态不变式” 语义槽位。

---

## 12. `uml:TimeEvent` 的 lowering

### 12.1 设计原则

本节遵循 `mds/TIMEOUT_DESIGN.md` 的总体思路，但当前阶段不向 FCSTM DSL 暴露 `after(...)` 表面语法。

换句话说：

- SysDeSim 的 `uml:TimeEvent`
- 在导出前直接 lower 成
- FCSTM 已经支持的 `def + enter/during/aspect + if [guard]`

### 12.2 时间单位折算

SysDeSim 样例中时间值表现为：

- `2s`
- `100ms`
- `20us`
- `0.5s`
- `4.5s`

由于当前 runtime 是 cycle-based，必须提供一个转换配置：

- `tick_duration_ms`

折算规则：

第一阶段建议明确支持以下时间单位：

- `s`
- `ms`
- `us`

内部建议先统一换算到微秒，再折算为 tick：

```text
delay_us = value * unit_factor
tick_us = tick_duration_ms * 1000
ticks = ceil(delay_us / tick_us)
```

例如：

- `2s` 且 `tick_duration_ms = 100ms`，则 `ticks = 20`
- `0.5s` 且 `tick_duration_ms = 100ms`，则 `ticks = 5`
- `20us` 且 `tick_duration_ms = 1ms`，则 `ticks = 1`

### 12.3 内部变量命名

对于 `TimeEvent` lowering，第一阶段建议按“**每条原始 timeout transition 一个 tick 变量**”处理，而不是按“每个 source state 一个共享 timer”处理。

这样做的原因是：

- 同一个 source state 可能存在多条不同 timeout
- 后续可能需要分别追踪、清理、调试这些 timeout
- 若只靠 source state 名称命名，很容易在复杂层级和拆分后产生歧义
- 分配独立 tick 变量后，实现和排错都更直接

推荐命名格式：

```text
__sysdesim_after_<source_path_snake>__tx_<transition_suffix>_ticks
```

其中：

- `source_path_snake` 来自 source state 的完整层级路径，而不是仅状态短名
- `transition_suffix` 来自该原始 timeout transition 的稳定唯一后缀

例如：

```text
__sysdesim_after_shang_dian_qi_kong_fa_dong_ji_dian_huo__tx_a1b2c3_ticks
```

这样即使出现：

- 同名状态分布在不同复合状态下
- 同一个状态上有多条 timeout
- 并发拆分后保留了多个局部相似子树

也不会发生内部 tick 变量名冲突。

若未来要做优化，可以在“多个 timeout 语义完全等价”时再尝试合并 tick 变量，但那应是显式优化步骤，而不应作为第一阶段默认行为。

### 12.4 leaf source 的 lowering

若 source 是 stoppable leaf state，则：

1. 添加内部变量定义
2. 在 `enter` 逻辑中追加：

```fcstm
__sysdesim_after_<source_path>__tx_<id>_ticks = 0;
```

3. 在 `during` 尾部追加：

```fcstm
__sysdesim_after_<source_path>__tx_<id>_ticks =
    __sysdesim_after_<source_path>__tx_<id>_ticks + 1;
```

4. 将原 time transition 改写为：

```fcstm
A -> B : if [__sysdesim_after_<source_path>__tx_<id>_ticks >= N];
```

若原 transition 同时还有 guard，则合并为：

```fcstm
A -> B : if [(__sysdesim_after_<source_path>__tx_<id>_ticks >= N) && cond];
```

### 12.5 composite source 的 lowering

若 source 是 composite state，则按 `TIMEOUT_DESIGN.md` 中的 propagated timeout exit chain 处理。
在本设计中，这里的 tick 变量也应当按“每条原始 timeout transition 一份”处理，而不是仅按 composite source 共享。

更准确地说，应是：

1. 添加该 timeout transition 自己的 tick 变量
2. 在 composite `enter` 中重置该变量
3. 在 composite `>> during after` 尾部追加该变量的 `+1`
4. 保留最终 `A -> B : if [timeout_guard]`
5. 对其所有后代活跃路径尾插退出链

其中该 `timeout_guard` 绑定的也是某一条原始 timeout transition 自己的独立 tick 变量，而不是仅按 composite source 名称共享的单一变量。
这样可以避免：

- 同一 composite source 上多条 timeout 混淆
- 不同层级同名 composite state 的内部变量重名

### 12.6 guard 一致性要求

整条 timeout 退出链上的 guard 必须完全一致。

不能只在中间链路判断 `ticks >= N`，最终层再判断原始 guard。

否则会出现：

- 子状态已被 timeout 链退出
- 但最终 source transition 不满足
- 运行时停留在错误层级

### 12.7 优先级规则

timeout lowering 产生的 transition 应尾插：

- 原始普通 transition 优先
- lowering 生成的 timeout 退出链后尝试

这样与 `TIMEOUT_DESIGN.md` 保持一致。

---

## 13. 跨层 transition 的 lowering

### 13.1 背景

当前 FCSTM runtime 的关键约束是：

- 活跃叶子状态只能先尝试自己的 transition
- 父状态 transition 必须在子状态先退出到父状态后才有机会被考虑

因此，SysDeSim 中的跨层 transition 无法直接映射为一条 FCSTM transition。

### 13.2 典型问题

典型示例：

```text
Parent.ChildA.SubA -> Parent.ChildB
```

这在 UML 中是合法的“跨层跳转”，但在当前 FCSTM 中不能直接写成：

```fcstm
SubA -> ChildB : /Evt;
```

因为 `ChildB` 不在 `SubA` 所在局部作用域。

### 13.3 总体策略

建议采用：

- **内部 route flag**
- **退出链**
- **桥接 transition**
- **条件化进入链**

的四段式 lowering。

这与 timeout 的 propagated exit chain 在结构上相似，但触发源是“原始事件/guard 命中”，不是“驻留时间达到阈值”。

### 13.4 route flag 设计

为每条跨层原始 transition 生成一组内部变量，例如：

```text
__sysdesim_flag_route_<source_path_snake>__tx_<transition_suffix>
```

若后续需要表达多目标共享，也可扩展为：

- 一个 `route_kind` 数值变量
- 多个 `== 常量` 的 guard

但第一版建议每条原始跨层 transition 用一个独立 flag，降低实现复杂度。

这里同样不能只用事件名或状态短名命名。
命名必须至少带上：

- source 的完整层级路径
- 原始 transition 的稳定唯一后缀

这样即使出现：

- 不同复合状态下的同名事件
- 不同路径上的同名状态
- 多条语义相近但不是同一条的跨层 transition

也不会发生 route flag 冲突。

### 13.5 触发点 lowering

原始跨层 transition 位于叶子 source `S` 时：

1. 在 `S` 的本地 transition 位置保留原始触发条件
2. 不直接跳去远端 target
3. 而是改为：
   - 设置 `__sysdesim_flag_route_x = 1`
   - 跳到 `[*]`

即：

```fcstm
S -> [*] : if [original_guard] effect {
    __sysdesim_flag_route_x = 1;
}
```

若原始 transition 带事件，则保持事件条件不变。

### 13.6 向上退出链

从 `S` 所在层级开始，沿着 `source -> ... -> LCA` 的祖先路径逐层补充：

```fcstm
Child -> [*] : if [__sysdesim_flag_route_x > 0];
```

这些中间退出链：

- 不挂原始 effect
- 只负责把控制流退回到 LCA

### 13.7 LCA 桥接 transition

到达 source 与 target 的最近公共祖先 `LCA` 后，补一条桥接 transition：

```fcstm
SourceBranchOwner -> TargetBranchOwner : if [__sysdesim_flag_route_x > 0];
```

这里需要根据 target 所在位置选择桥接粒度：

- 若 target 是 `LCA` 的直接子状态，则直接桥过去
- 若 target 更深，则先桥到 target 路径上的第一层子状态

### 13.8 条件化进入链

若 target 位于更深层后代，单靠桥到某个 composite 还不够，因为 runtime 只会走该 composite 的 init 链。

因此需要改写目标路径上的 init transition：

- 在各层 `[*] -> default_child` 之前
- 插入一条基于 route flag 的条件化 init transition

例如目标路径为：

```text
LCA -> B -> C -> D
```

则可生成：

```fcstm
[*] -> B : if [__sysdesim_flag_route_x > 0];
```

在 `B` 内生成：

```fcstm
[*] -> C : if [__sysdesim_flag_route_x > 0];
```

在 `C` 内生成：

```fcstm
[*] -> D : if [__sysdesim_flag_route_x > 0];
```

并把原默认 init 保留在这些条件 init 之后。

### 13.9 flag 清理

到达最终目标叶子或最终目标稳定边界后，必须 clear flag：

```fcstm
enter {
    __sysdesim_flag_route_x = 0;
}
```

更稳妥的做法是：

- 在目标路径最后一个明确状态的 `enter` 中清理
- 或在最后一跳 bridge effect 中清理，但要确保不影响后续条件化 init

因此推荐：

- **最终目标状态 enter 时清理**

### 13.10 effect 保留规则

跨层原始 transition 若有 effect，则：

- 只在第一跳触发点执行一次
- 中间退出链和条件化进入链都不重复执行

这与 timeout lowering 中“只有最终 source transition 挂 effect”的原则相似，本质上都是防止 effect 重复。

### 13.11 优先级规则

route flag 相关 transition 应有足够优先级以保证整条链能闭合。

建议：

- 第一跳触发 transition 仍在原 source 的原位置
- 中间退出链、条件化 init、桥接 transition 应在各自作用域中前插

理由是：

- 一旦 `route flag` 已置位，说明当前 cycle 正在执行一条已被选中的跨层迁移
- 后续链不应被普通 transition 抢占

这与 timeout lowering 的尾插不同。
两者的差别在于：

- timeout 是低优先级语义
- 跨层迁移一旦触发，就应视为当前 cycle 的已选路径延续

### 13.12 适用范围

第一阶段建议只支持：

- `leaf source -> 任意 target`
- `trigger 为 signal`、`none` 或已在 Phase 3 中完成 timer guard lowering 的 `time`
- `guard 可为空`

对于更复杂情况：

- composite source 的跨层迁移
- 跨并发 region 迁移
- 以祖先状态作为 target 的跨层迁移
- 多层条件 init 冲突

第一阶段可先报 unsupported。

---

## 14. multi-region 并发状态的拆分策略

### 14.1 问题定义

SysDeSim/UML 的一个复合状态可拥有多个 region，表示并发状态。

当前 FCSTM 不支持：

- 多 active leaf
- 并发 region 的同步进入/退出
- 跨 region 同时稳定驻留

因此不能直接映射。

### 14.2 总体策略

当前阶段不做“伪并发模拟”，而采用：

- **按 region 拆分为多个独立 machine**

### 14.3 拆分原则

若某个状态 `P` 拥有 `n > 1` 个 region，则：

- 生成 `n` 个独立的 FCSTM 状态机
- 每个输出 machine 保留从根到 `P` 的祖先路径
- 在 `P` 之下只保留其中一个 region 的子树
- 其他 region 的内容不并入该 machine

可以理解为：

- 从一个并发状态图中切出多个串行子状态机视图

### 14.4 输出命名建议

若原 machine 名为 `FeiKong`，状态 `QiKong` 下有三个 region，则可输出：

```text
FeiKong__QiKong_region1.fcstm
FeiKong__QiKong_region2.fcstm
FeiKong__QiKong_region3.fcstm
```

或在单文件中输出多个顶层 machine，这取决于现有导出接口支持情况。

### 14.5 语义声明

必须明确说明：

- 这不是 UML 并发语义的等价转换
- 这是为了在现有 FCSTM 执行模型下保留每个 region 的局部行为
- 拆分结果不能自动表达 region 之间的同步

### 14.6 cross-region transition

若发现 transition：

- source 与 target 分属同一并发 owner 的不同 region

则第一阶段建议直接标记为 unsupported。

因为该场景无法通过单机串行 lowering 自然表达。

---

## 15. SysDeSim IR -> FCSTM AST Node 构建

### 15.1 核心原则

在 SysDeSim IR -> FCSTM 的这一环节，不要直接写 FCSTM 代码字符串。
应统一构建 `pyfcstm.dsl.node` 中的 AST Node。

这样做的原因是：

- AST Node 已经具备稳定、无损的字符串化能力
- 可以减少手写 DSL 文本时的语法拼接错误
- 便于在构建阶段做结构校验
- 更容易与现有 model 层 round-trip

### 15.2 建议使用的 AST Node

建议优先使用以下对象：

- `StateMachineDSLProgram`
- `DefAssignment`
- `StateDefinition`
- `EventDefinition`
- `TransitionDefinition`
- `ForceTransitionDefinition`
- `OperationAssignment`
- 各类 `EnterStatement`、`DuringStatement`、`ExitStatement`、`DuringAspectStatement`

### 15.3 构建顺序

建议构建顺序为：

1. 构建 `definitions`
2. 构建根 `StateDefinition`
3. 递归构建子状态
4. 追加事件定义
5. 追加 transition / force transition
6. 组装为 `StateMachineDSLProgram`

### 15.4 AST 到文本的职责边界

`emit_dsl.py` 的职责应仅限于：

- 接收已经构建完成的 AST Node
- 调用其字符串化能力输出文本

而不应再在这个阶段做结构性重写。

---

## 16. unsupported 与降级边界

以下场景第一阶段建议不支持或仅记录不执行：

- 并发 region 之间的直接 transition
- 需要多个并发 region 同步决定的 guard
- `stateInvariant` 的强语义执行
- 无法解析的 guard 表达式
- 一个 region 多个 init 伪状态且需要复杂选择
- 历史状态、choice、junction、fork、join 等更复杂 UML 伪状态
- 依赖 activity 图内部执行语义的 transition effect
- composite source 的复杂跨层迁移

对这些情况，转换器不应静默忽略。
应给出：

- 明确诊断信息
- 原始 `xmi:id`
- 原始状态路径
- 失败原因

---

## 17. 转换输出策略

### 17.1 输出形式建议

建议支持三种输出：

- 调试用 JSON/IR dump
- `pyfcstm.dsl` AST dump 或调试输出
- `fcstm` DSL 文本

其中：

- AST 用于调试和结构检查
- DSL 文本用于交给现有 parser/model/simulate/generate
- IR dump 用于排查 lowering 是否符合预期

### 17.2 导出后自校验

每次导出后，应立刻执行：

1. 用现有 FCSTM parser 回读
2. 构建 model
3. 检查是否满足现有验证规则

至少要确认：

- 所有复合状态都有 init transition
- 所有状态引用路径合法
- 所有 guard 只引用已定义变量
- 所有 event 引用路径合法

### 17.3 转换报告

建议同时输出一份报告，包含：

- 输入 machine 名
- 输出 machine 数量
- 是否发生 parallel split
- 是否发生 cross-level lowering
- 是否发生 time-event lowering
- unsupported 列表
- 被忽略/仅记录的动作与 invariant

---

## 18. 分阶段实施与阶段检查清单

### Phase 0: 解析与观测

目标：

- 建立 XML 解析器
- 构建基础 IR
- 能打印完整状态树、region 树、transition 列表

交付：

- `xmi:id` 索引
- `state/region/transition/event` 基础结构
- 调试输出或 JSON dump
- Phase 0 单元测试

验收标准：

- 能正确解析 `test_com.sysdesim.metamodel.model.xml`
- 能列出所有 state、region、trigger、timeEvent

Phase 0 checklist：

- [x] 能读取 `uml:StateMachine`
- [x] 能读取所有 `region`
- [x] 能读取所有 `subvertex`
- [x] 能读取所有 `transition`
- [x] 能关联 `source` 与 `target`
- [x] 能解析 `Signal` 与 `SignalEvent`
- [x] 能解析 `TimeEvent`
- [x] 能读取 `entry`、`exit`、`effect`
- [x] 能建立 `xmi:id -> element` 索引
- [x] 具备针对解析层的单元测试

### Phase 1: IR dataclass、命名与变量映射

目标：

- 固化 IR `dataclass`
- 完成状态、事件、变量的命名与合法性策略
- 明确显式变量保留规则

交付：

- `dataclass` 化 IR
- 状态 UpperCamelCase
- 事件 UPPER_SNAKE_CASE
- 显式变量原名原类型保留
- 合成变量 lower_snake_case
- Phase 1 单元测试

验收标准：

- 显式变量与合成变量策略不冲突
- 命名结果稳定可重现

Phase 1 checklist：

- [x] IR 使用 `@dataclass`
- [x] 中文状态名可稳定转成 UpperCamelCase
- [x] 中文事件名可稳定转成 UPPER_SNAKE_CASE
- [x] 中文显示名统一通过 `named` 保留
- [x] 显式变量在合法时按原名保留
- [x] 显式变量按原类型保留
- [x] 非法显式变量名会报错而不是自动改名
- [x] 合成变量统一使用 `__sysdesim_*`
- [x] 所有 `__sysdesim_*` 名称都带稳定唯一后缀，不仅依赖短名
- [x] 具备针对命名与变量映射的单元测试

### Phase 2: 单 region 基础结构与 AST 构建

目标：

- 在不处理并发、不处理 time、不处理跨层的前提下
- 完成单 region、同层 transition 的 FCSTM AST 构建

交付：

- `Pseudostate init -> [*]`
- `SignalEvent -> event`
- `State -> StateDefinition`
- `entry/exit -> abstract action`
- `StateMachineDSLProgram` 构建
- `emit_dsl.py`
- Phase 2 单元测试

验收标准：

- 输出 AST 可稳定转为 DSL
- 输出 DSL 可被 parser/model 正常回读
- 基础路径和 init 关系正确

Phase 2 checklist：

- [x] init 伪状态可识别
- [x] 复合状态缺失 init 时可报错
- [x] 同层 transition 可导出
- [x] signal trigger 可导出为事件引用
- [x] 能构建 `StateMachineDSLProgram`
- [x] AST 输出 DSL 后可被 parser 回读
- [x] 具备针对 AST 构建层的单元测试

### Phase 3: TimeEvent lowering

目标：

- 支持 `uml:TimeEvent`
- 用内部 timer 变量与 guard 完成导出

交付：

- `tick_duration_ms` 配置
- `s/ms/us` 单位支持
- leaf source lowering
- composite source lowering
- Phase 3 单元测试

验收标准：

- 样例中的 `2s`、`0.5s`、`4.5s` 均能被转换
- 输出 DSL 中不依赖新增语法

Phase 3 checklist：

- [x] 可识别 `uml:TimeEvent`
- [x] 可读取原始时间字面量
- [x] 支持 `s`
- [x] 支持 `ms`
- [x] 支持 `us`
- [x] 可按 `tick_duration_ms` 折算 tick
- [x] 同一 source 多条 time transition 可生成彼此独立的 tick 变量
- [x] tick 变量名包含 source 路径与稳定唯一后缀
- [x] leaf source 会在 `enter` 重置 timer
- [x] leaf source 会在 `during` 尾部累加 timer
- [x] composite source 会在 `>> during after` 尾部累加 timer
- [x] timeout guard 全链一致
- [x] timeout lowering transition 为尾插
- [x] 具备针对 time-event lowering 的单元测试

### Phase 4: 跨层 transition lowering

目标：

- 支持单机单 region 下的跨层迁移

交付：

- LCA 计算
- route flag 设计
- 退出链
- 桥接 transition
- 条件化 init 进入链
- Phase 4 单元测试

验收标准：

- 样例中的跨层迁移可导出为合法 FCSTM
- flag 生命周期正确
- 不发生重复 effect

Phase 4 checklist：

- [x] 能识别跨层 transition
- [x] 能计算 source 与 target 的 LCA
- [x] 能为原始跨层 transition 分配 route flag
- [x] route flag 名称包含 source 路径与稳定唯一后缀
- [x] 第一跳只负责置 flag 和退出或直达目标分支首层桥接
- [x] 中间退出链不重复 effect
- [x] 桥接 transition 可把控制流带到目标分支
- [x] 条件化 init 可把进入路径导到目标叶子
- [x] 最终目标状态能清理 flag
- [x] route 相关 transition 具备足够优先级
- [x] 具备针对跨层 lowering 的单元测试

### Phase 5: parallel split

目标：

- 支持 multi-region owner 的拆分导出，同时保留一份完整主状态机输出

交付：

- 主状态机降级保留策略
- 并发 owner 检测
- 按 region 切分 region-level machine
- 命名和输出组织策略
- cross-region unsupported 检查
- Phase 5 单元测试

验收标准：

- 样例中的 `启控` 会导出 1 份主状态机和 3 份 region-level machine
- 主状态机中 `启控` 外围的层级、变量、事件与外层 transition 会被保留
- 每份输出 machine 可独立解析

Phase 5 checklist：

- [x] 能检测多 region owner
- [x] 能保留完整主状态机输出
- [x] 能为每个 region 切出独立 machine
- [x] 能复制祖先路径
- [x] 能稳定命名拆分后的输出
- [x] 可检测并拒绝 cross-region transition
- [x] 转换报告会说明并发拆分是降级语义
- [x] 具备针对 parallel split 的单元测试

### Phase 6: 完整校验与 CLI 接入

目标：

- 提供正式命令入口
- 增加单元测试与样例回归

交付：

- CLI 接口
- 转换报告
- 错误消息与诊断
- 覆盖核心 lowering 的测试
- Phase 6 单元测试

验收标准：

- 用户可从命令行直接完成转换
- 关键样例具备稳定回归测试
- `python -m pyfcstm sysdesim -i test_com.sysdesim.metamodel.model.xml -o <dir> --tick-duration-ms 100`
  可成功导出 1 份主状态机、3 份 region-level 状态机和 1 份 JSON 报告

Phase 6 checklist：

- [x] 导出 DSL 后可被 parser 回读
- [x] model 构建成功
- [x] 所有 guard 变量都有定义
- [x] 所有事件路径合法
- [x] 所有复合状态都有 init
- [x] 样例文件具备稳定回归测试
- [x] unsupported 场景有明确错误消息
- [x] 提供 CLI 命令入口
- [x] 具备针对 CLI 与整体回归的单元测试

---

## 19. 建议的测试策略

### 19.1 单元测试维度

建议按以下维度建立测试：

- XML 解析测试
- IR `dataclass` 构建测试
- 命名归一化测试
- 显式变量保留测试
- init 伪状态识别测试
- 单 region AST 构建测试
- signal event 映射测试
- leaf time-event lowering 测试
- composite time-event lowering 测试
- 跨层 transition lowering 测试
- parallel split 测试
- unsupported 检测测试

### 19.1.1 正向导出测试的统一断言约定

对所有“应成功导出 FCSTM DSL”的单元测试，后续统一要求：

1. 先准备完整 `expected_dsl` 文本
2. 对导出的 `dsl_code` 做规范化换行后的**整段全文相等断言**
   - 推荐形式：`assert _normalize_newlines(dsl_code) == expected_dsl`
3. 若测试同时构建了 AST `program`，则也应断言：
   - `assert _normalize_newlines(str(program)) == expected_dsl`
4. 必须对导出的 DSL 文本执行 parser + model 回读：
   - `parsed_program = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')`
   - `model = parse_dsl_node_to_state_machine(parsed_program)`
5. 在完成全文相等与回读检查后，才追加少量结构性断言
   - 例如 route flag 名称、init 顺序、transition 类型、target clear 行为
6. 对 `parallel split` 一类多输出正向测试，必须覆盖嵌套 multi-region 场景
   - 至少有一个 case 让 multi-region 出现在多层级子状态内
   - 断言 split 后不仅 region 子树正确，而且外围主状态机结构、变量、事件、外层 transition 仍完整保留

不应只依赖：

- 子串存在断言
- transition 顺序的局部断言
- 仅对 AST 结构断言而不检查最终 DSL 文本

原因是转换器的最终交付物是 DSL 文本，全文断言与 parser/model 回读才能稳定覆盖：

- AST 到文本的序列化正确性
- lowering 的整体布局、顺序与缩进
- 导出结果在现有 FCSTM 解析与建模链路中的真实可用性

### 19.2 样例测试组织建议

建议准备一组最小 XML 片段样例，而不是只依赖大样例文件：

- `basic_single_region.xml`
- `timeevent_leaf.xml`
- `timeevent_composite.xml`
- `crosslevel_leaf_to_ancestor_sibling.xml`
- `parallel_two_regions.xml`
- `parallel_nested_regions_keep_outer_structure.xml`
- `cross_region_unsupported.xml`
- `explicit_variables_keep_name.xml`

### 19.3 集成测试

对导出的 FCSTM，建议执行：

1. parser 回读
2. model 构建
3. `dsl_code == expected_dsl` 的全文断言
4. AST round-trip
5. 必要时使用 `SimulationRuntime` 进行最小行为验证

---

## 20. 当前推荐的实施顺序

如果按最小可用路径推进，建议顺序如下：

1. 先完成 XML -> IR
2. 再完成 `dataclass` 化 IR 与命名/变量规则
3. 再完成单 region AST 构建
4. 再完成 `TimeEvent` lowering
5. 再完成单 region 下的跨层 transition lowering
6. 最后做 parallel split 与 CLI 整合

这样做的原因是：

- 前三步可以尽快把“能输出合法 FCSTM AST 并稳定转成 DSL”这个骨架跑通
- `TimeEvent` lowering 已有较成熟设计可依赖
- 跨层和并发是复杂度最高的部分，应放在基础结构稳定之后

---

## 21. 最终结论

SysDeSim UML 状态机到 FCSTM 的转换，本质上不是格式转换，而是一次受当前 runtime 语义约束的 lowering。

在现阶段最务实、最可落地的路线是：

- 用 `dataclass` IR 承接 XML 的 UML 结构
- 用稳定且人类友好的命名解决中文与路径问题
- 对显式变量保持原名和原类型
- 用 init 推断适配无名初始伪状态
- 用 timer 变量与普通 guard 吃掉 `uml:TimeEvent`
- 用 route flag、退出链、桥接和条件化 init 吃掉跨层 transition
- 用 `pyfcstm.dsl` AST Node 作为 FCSTM 侧的结构承载
- 对 multi-region 并发不做伪兼容，而是显式拆分为多个 machine

这条路线虽然不是对原 UML 语义的完全无损映射，但它与当前仓库的 FCSTM 语法、AST 结构和 runtime 能力是相容的，并且具备清晰的实现路径、测试路径与后续演进空间。
