# FCSTM 多文件导入与模块装配设计

## PR 信息

- PR 编号：79
- PR 链接：https://github.com/HansBug/pyfcstm/pull/79
- 文档链接：https://github.com/HansBug/pyfcstm/blob/dev/import/mds/PR79-FCSTM_IMPORT_DESIGN.md

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.5.9 | 2026-04-06 | 完成 Phase 4：模型层新增 event mapping 装配、宿主事件合成、显示名冲突校验、force transition 覆盖与独立 Phase 4 回归测试，并补充导出 DSL 的保真路径说明 | Codex |
| 0.5.8 | 2026-04-06 | 制度化后续 phase 测试规范：每个 phase 单独使用 `test_import_phaseN.py`，且典型 case 必须补 `text_aligner` 驱动的 `to_ast_node()` 全量导出比对，并将该要求写入后续 phase checklist | Codex |
| 0.5.7 | 2026-04-06 | 完成 Phase 3：模型层新增 `def` mapping 规则求值、变量深度重写、宿主 / 跨 import 变量合流校验，并补齐 Phase 3 回归测试与勾选状态 | Codex |
| 0.5.6 | 2026-04-05 | 完成 Phase 2：模型层新增 import 装配器，支持多级相对路径递归解析、循环导入检测、alias 装配与模块绝对路径重写；同时保持 `def/event mapping` 与 imported top-level `def` 继续在 Phase 3/4 显式 fail fast | Codex |
| 0.5.5 | 2026-04-05 | 收紧分层边界：`dsl.parse.parse_state_machine_dsl()` 回归纯 AST 入口，不再接收 `path`；路径上下文只由 model / import 装配侧处理 | Codex |
| 0.5.4 | 2026-04-05 | 移除 `StateMachineDSLProgram.source_path`，保持 DSL AST 纯净，并将路径上下文限定在模型构建入口 `path` 参数 | Codex |
| 0.5.3 | 2026-04-04 | 补齐 Phase 1 剩余的 `path` 参数契约、import fail-fast 保护与 public API 回归测试，并勾选 Phase 1 完成状态 | Codex |
| 0.5.2 | 2026-04-03 | 同步 Phase 1 当前实现进展，勾选已完成的 DSL / AST / 回归测试项 | Codex |
| 0.5.1 | 2026-04-03 | 为各 phase 补充回归测试验收要求，并新增 public API 测试约束与 pydoc 编写规范约束 | Codex |
| 0.5.0 | 2026-04-03 | 新增完整实施计划，按 phase 拆分 TODO 与验收 checklist，并补充每次 push 后同步 MD / PR checkbox 的推进规则 | Codex |
| 0.4.3 | 2026-04-03 | 收紧单个 import 实例内的变量映射约束，明确禁止任何内部 many-to-one 变量塌缩 | Codex |
| 0.4.2 | 2026-04-03 | 调整变量共享边界，允许不同 import 实例中的不同源变量汇聚到同一目标变量名，但要求参与汇聚的类型完全一致 | Codex |
| 0.4.1 | 2026-04-03 | 补充映射目标与宿主现有变量同名时的合法性规则，要求类型完全一致，并明确宿主定义优先 | Codex |
| 0.4.0 | 2026-04-03 | 重写 `def` mapping 规范，定义 selector 类型、多 `*` 捕获、`${n}` / `$n` / 裸 `*` 规则，以及优先级与冲突处理 | Codex |
| 0.3.0 | 2026-04-03 | 明确 import 文件系统相对路径按当前文件逐级解析，并调整为 `parse_dsl_node_to_state_machine()` 接收 `path` 参数负责递归导入 | Codex |
| 0.2.1 | 2026-04-03 | 调整 7.4 节事件映射目标路径示例，显式补充最外层 `Root` 并明确相对目标解析结果 | Codex |
| 0.2.0 | 2026-04-03 | 补充事件映射右侧相对路径语义，并允许在事件映射上用 `named` 覆盖最终显示名称 | Codex |
| 0.1.0 | 2026-04-03 | 初始版本，定义 import 装配语义、事件/变量映射规则与 VSCode 支持方案 | Codex |

---

## 1. 背景与目标

当前 FCSTM DSL 以单文件、单 root state 作为主要编写单位。随着状态机规模增长，用户需要将一个完整流程拆分到多个 `.fcstm` 文件中维护，并在主状态机中按模块装配。

本设计的目标是：

- 支持将其他 `.fcstm` 文件的状态机根状态显式导入为当前复合状态下的一个子状态
- 支持同一模块多次导入
- 支持变量默认隔离，并通过显式映射实现变量共享
- 支持事件默认局部化，并通过显式映射实现事件提升或跨模块共享
- 保持现有生成、模拟、PlantUML、模板系统的主要处理链路不被大面积改写
- 为 VSCode 扩展提供渐进式支持路径

非目标：

- 本阶段不支持从一个外部文件中“任选任意嵌套状态”进行导入
- 本阶段不引入运行时模块系统
- 本阶段不将 import 设计为纯文本 include

---

## 2. 总体原则

### 2.1 编译期装配，而非运行时模块系统

`import` 的语义定义为“编译期多文件装配”。实现时，先将多个 DSL 文档解析并展开为一份合成 AST，再复用现有的模型构建、渲染、模拟和代码生成链路。

这意味着：

- import 不参与运行时决策
- 导入后的结果应等价于用户手工把目标状态内联到宿主文件
- `parse_dsl_node_to_state_machine()` 应在内部完成 import 展开，并最终继续构建普通 `StateMachine`

### 2.2 显式优于隐式

对于导入别名、显示名称、变量共享、事件共享，不采用“自动猜测”策略，而要求宿主文件显式声明绑定意图。

### 2.3 默认隔离，按需共享

- 状态实例默认隔离
- 模块变量默认隔离
- 模块事件默认隔离
- 共享通过 import block 中的显式映射产生

---

## 3. 顶层语义模型

### 3.1 导入单位

一个可导入文件仍然是完整合法的 FCSTM 文档：

- 顶层 `def ...`
- 一个 root `state`

导入时，导入目标固定为该文件的 root state。

### 3.2 导入位置

`import` 只允许出现在复合状态内部，导入后在当前复合状态下生成一个新的直接子状态。

### 3.3 导入源路径解析

当 `import` 使用文件系统相对路径时，解析基准必须是“声明这条 import 的那个 `.fcstm` 文件所在目录”，而不是顶层入口文件所在目录。

例如：

- `/a/b/c/root.fcstm` 中写 `import "./xxx.fcstm"`，则应解析到 `/a/b/c/xxx.fcstm`
- `/a/b/c/root.fcstm` 中写 `import "./d/e/xxx.fcstm"`，则应解析到 `/a/b/c/d/e/xxx.fcstm`
- 若 `/a/b/c/d/e/xxx.fcstm` 中再写 `import "./yyy.fcstm"`，则应继续解析到 `/a/b/c/d/e/yyy.fcstm`

也就是说，多级 import 必须逐级相对各自文件位置解析，而不能始终绑定到顶层入口文件目录。

### 3.4 显式别名

每个 import 必须显式写出本地状态名：

- `as Alias` 必填
- `named "Display Name"` 选填

`Alias` 是导入后在宿主状态机中的真实状态名。

### 3.5 显示名称优先级

导入后的显示名称优先级如下：

1. import 语句上的 `named`
2. 被导入文件 root state 自带的 `named`
3. `Alias`

---

## 4. DSL 草案

建议 DSL 形式如下：

```fcstm
state System {
    import "./motor.fcstm" as LeftMotor named "Left Motor" {
        def * -> left_*;
        event /Start -> Start named "Motor Start";
        event /Stop -> /Motors.Stop;
        event /Fault -> /Motors.Fault;
    }

    import "./motor.fcstm" as RightMotor named "Right Motor" {
        def * -> right_*;
        event /Start -> Start named "Motor Start";
        event /Stop -> /Motors.Stop;
        event /Fault -> /Motors.Fault;
    }

    state Done;
    [*] -> LeftMotor;
    LeftMotor -> RightMotor :: Ready;
    RightMotor -> Done :: Completed;
}
```

建议语法结构：

```fcstm
import STRING as ID (named STRING)? ('{' import_mapping_statement* '}')? ';'
```

其中 `import_mapping_statement` 第一阶段建议只支持两类：

- `def ... -> ...;`
- `event ... -> ... (named "...")?;`

这样可以尽量复用现有 DSL 关键字体系，只引入新的 `import`、`as` 两个核心关键字。

---

## 5. 变量设计

### 5.1 设计目标

变量映射系统需要满足以下目标：

- 支持同一模块多次导入
- 支持不同导入实例默认拥有独立变量
- 支持按变量名结构做批量映射
- 保持语义可预测，不把 mapping 扩展成完整脚本语言

本设计明确不引入：

- `exclude` / `include`
- 变量分组
- 端口系统
- 正则表达式映射

### 5.2 默认行为

若 import 未写任何 `def` 映射，则系统对该导入隐式应用：

```fcstm
def * -> <Alias>_*;
```

例如：

```fcstm
import "./worker.fcstm" as A;
import "./worker.fcstm" as B;
```

隐含等价于：

```fcstm
import "./worker.fcstm" as A {
    def * -> A_*;
}

import "./worker.fcstm" as B {
    def * -> B_*;
}
```

这样同一模块多次导入时默认不会发生变量冲突。

### 5.3 Source 侧 selector 语法

建议 `def` mapping 支持 4 类 selector：

```fcstm
def counter -> left_counter;
def {a, b, c} -> ctl_*;
def sensor_* -> io_$1;
def a_*_b_* -> pair_${1}_${2};
def * -> left_$0;
```

分别表示：

1. 精确匹配

```fcstm
def counter -> ...;
```

2. 显式集合匹配

```fcstm
def {a, b, c} -> ...;
```

3. 通配模式匹配

```fcstm
def sensor_* -> ...;
def a_*_b_* -> ...;
```

4. 兜底匹配

```fcstm
def * -> ...;
```

### 5.4 Source 中 `*` 的语义

Source 侧只支持一种通配符：`*`。

规则如下：

- `*` 表示一个捕获槽
- 可以出现多个
- 从左到右编号为第 1、第 2... 个捕获组
- 模式始终匹配整个变量名，而不是子串匹配
- 多个 `*` 的匹配策略采用“左到右、非贪婪匹配，以保证后续字面量仍可继续匹配”

例如：

```fcstm
def a_*_b_* -> ...;
```

对于变量：

```text
a_foo_b_bar
```

有：

- 第 1 个捕获组 = `foo`
- 第 2 个捕获组 = `bar`

对于：

```text
a_x_b_y_b_z
```

建议匹配结果为：

- 第 1 个捕获组 = `x`
- 第 2 个捕获组 = `y_b_z`

### 5.5 Target 模板与占位符语法

Target 侧支持两套等价占位符写法：

- 正式写法：`${n}`
- 简写写法：`$n`

其中：

- `${0}` 表示完整源变量名
- `${1}` 表示第 1 个 `*` 捕获内容
- `${2}` 表示第 2 个 `*` 捕获内容
- 依此类推

例如：

```fcstm
def counter -> left_${0};
def {a, b, c} -> ctl_${0};
def sensor_* -> io_${1};
def a_*_b_* -> pair_${1}_${2};
def * -> left_${0};
```

### 5.6 `$n` 简写规则

`$n` 只识别 `$` 后面的一个数字，因此：

- `$0` 等价于 `${0}`
- `$1` 等价于 `${1}`
- `$2` 等价于 `${2}`
- `$12` 解释为 `${1}2`
- `$03` 解释为 `${0}3`

若要引用两位数以上的捕获组编号，必须显式写：

```fcstm
${12}
```

这样可以避免 `$12` 究竟是“第 12 组”还是“第 1 组后接字面量 `2`”的歧义。

### 5.7 Target 侧裸 `*` 简写

为了保留更短的写法，Target 侧允许在特定条件下继续使用裸 `*`：

1. 若 Source 没有捕获组

- 裸 `*` 解释为 `${0}`

例如：

```fcstm
def {a, b, c} -> ctl_*;
def * -> left_*;
```

分别等价于：

```fcstm
def {a, b, c} -> ctl_${0};
def * -> left_${0};
```

2. 若 Source 恰好有 1 个 `*`

- 裸 `*` 解释为 `${1}`

例如：

```fcstm
def sensor_* -> io_*;
```

等价于：

```fcstm
def sensor_* -> io_${1};
```

并且在这种情况下，也允许显式使用：

- `${0}` / `$0`
- `${1}` / `$1`

3. 若 Source 有多个 `*`

- Target 侧禁止再使用裸 `*`
- 必须显式写 `${0}`、`${1}`、`${2}` 或对应的 `$0`、`$1`、`$2`

例如：

```fcstm
def a_*_b_* -> pair_${1}_${2};
```

而下面这种建议直接判为非法：

```fcstm
def a_*_b_* -> pair_*;
```

因为这里的裸 `*` 会产生歧义。

### 5.8 映射优先级

`def` mapping 的优先级固定为：

1. 精确规则
2. 集合规则
3. 通配模式规则
4. 兜底规则 `def * -> ...`

不采用“按书写顺序覆盖”的策略。

例如：

```fcstm
def counter -> shared_counter;
def {counter, status_flag} -> ctl_*;
def *_flag -> flag_$1;
def * -> left_$0;
```

则：

- `counter` 使用精确规则
- `status_flag` 使用集合规则
- `error_flag` 使用模式规则
- `timeout` 使用兜底规则

### 5.9 同优先级冲突规则

为保证可预测性，建议同优先级规则发生冲突时直接报错：

1. 精确规则

- 同一个变量不能出现两条精确规则

2. 集合规则

- 两条集合规则不能包含同一个变量
- 集合规则中出现重复变量应报错

3. 模式规则

- 若同一个变量同时命中多条模式规则，应直接报“模式歧义”错误
- 不再继续发明“更具体模式优先”的附加算法

4. 兜底规则

- `def * -> ...` 只能出现一条

### 5.10 目标名冲突、共享边界与宿主同名绑定

若映射后的目标变量名已经在宿主文件顶层 `def` 中存在，则原则上允许直接绑定到该宿主已有变量，而不视为新建变量。

但前提是：

- 宿主已有变量与被映射过来的模块变量类型必须完全一致
- 当前阶段仅有 `int` / `float` 两类，因此禁止 `int` 映射到宿主 `float`，也禁止 `float` 映射到宿主 `int`

例如：

```fcstm
def int shared_counter = 0;

state System {
    import "./worker.fcstm" as A {
        def counter -> shared_counter;
    }
}
```

若模块中的 `counter` 也是 `int`，则该映射合法；若模块中的 `counter` 是 `float`，则应直接报错。

对于“多个导入变量汇聚到同一个目标变量名”的情况，本设计改为区分两类：

1. 同一个 import 实例内部的多源汇聚

- 一律禁止
- 单个 import 实例内部，变量映射必须满足“不同源变量不能收敛到同一个目标变量名”
- 换句话说，单个 import 内只允许 many-to-many 中“不收敛”的那一部分；严格禁止内部 many-to-one
- 例如 `def {a, b} -> shared_var;` 若发生在同一个 import block 内，则必须直接报错

2. 不同 import 实例之间的多源汇聚

- 原则上允许
- 即使源变量名不同，也允许它们映射到同一个目标变量名
- 但所有参与汇聚的变量类型必须完全一致

例如：

```fcstm
import "./worker_a.fcstm" as A {
    def counter -> shared_var;
}

import "./worker_b.fcstm" as B {
    def pulse_count -> shared_var;
}
```

若 `counter` 与 `pulse_count` 都是 `int`，则该共享合法；若其中一个是 `float`，则应直接报错。

也就是说，第一阶段允许的共享变量来源包括：

- 不同 import 实例中的同名源变量
- 不同 import 实例中的不同源变量
- 宿主已有变量与 import 变量的同名绑定

但同一个 import 实例内部，集合规则、模式规则、兜底规则都不允许制造变量收敛。

### 5.11 类型与初始化校验

当映射结果命中宿主已有变量，或多个 import 最终把变量映射到同一目标变量名时，仍需执行一致性校验：

- 若宿主文件已显式定义该目标变量，则：
  - 变量类型必须与宿主定义完全一致
  - 宿主定义视为最终权威定义
  - import 内部原始变量的初始化表达式不再要求与宿主初始化一致
- 若宿主文件未显式定义该目标变量，而多个 import 共享同一目标变量名，则：
  - 变量类型必须一致
  - 初始化表达式必须一致
- 若同一个 import 实例内部有多个不同源变量试图汇聚到同一目标变量名，则一律直接报错，不进入共享校验分支
- 若类型不一致，报错
- 若初始化冲突且宿主未显式覆盖，报错

建议错误示例：

- `Variable mapping conflict: target variable 'shared_counter' has inconsistent type 'int' vs 'float'.`
- `Variable mapping conflict: target variable 'shared_counter' already exists in host model as type 'int', cannot bind imported type 'float'.`
- `Variable mapping conflict: target variable 'shared_var' receives incompatible imported types 'int' and 'float'.`
- `Variable mapping conflict: import 'A' maps multiple source variables to the same target variable 'shared_var'.`
- `Variable mapping conflict: target variable 'shared_counter' has conflicting initial values.`

### 5.12 示例

假设模块变量有：

```text
counter
status_flag
sensor_temp
sensor_pressure
a_main_b_low
timeout
```

宿主映射如下：

```fcstm
def counter -> shared_counter;
def {status_flag} -> ctl_*;
def sensor_* -> io_*;
def a_*_b_* -> pair_${1}_${2};
def * -> left_$0;
```

则结果为：

- `counter -> shared_counter`
- `status_flag -> ctl_status_flag`
- `sensor_temp -> io_temp`
- `sensor_pressure -> io_pressure`
- `a_main_b_low -> pair_main_low`
- `timeout -> left_timeout`

---

## 6. 事件设计

### 6.1 设计目标

事件系统需要同时支持：

- 导入实例拥有各自局部事件
- 模块事件可提升到主状态机事件空间
- 多个同构模块可绑定到同一套宿主事件

### 6.2 默认行为

默认情况下，事件随导入实例一起局部化，不自动共享。

具体规则：

- `::` 产生的局部事件继续保持局部
- 普通链式 `:` 事件在导入展开后仍绑定到导入实例内部相对作用域
- 模块内部使用 `/...` 的事件路径，不直接解释为宿主根绝对路径，而解释为“模块根绝对路径”

也就是说，被导入模块中的：

```fcstm
StateA -> StateB : /Start;
```

默认不是宿主 `Root.Start`，而是模块根下的 `/Start`，导入后默认重写为与该实例绑定的事件路径。

### 6.3 显式事件映射

建议只允许对“模块绝对事件”做跨实例绑定。左侧必须是模块绝对事件路径，右侧既可以是宿主绝对路径，也可以是宿主相对路径：

```fcstm
event /Start -> Start;
event /Start -> Start named "Motor Start";
event /Stop -> /Motors.Stop;
event /Fault -> /GlobalFault;
```

解释：

- 左侧 `/Start` 指模块根绝对事件
- 右侧 `/Motors.Start` 指宿主装配后的最终绝对事件路径
- 右侧 `Start` 指相对于“import 所在宿主 state”的事件路径
- `named "Motor Start"` 用于覆盖装配后目标事件的显示名称

例如：

```fcstm
state System {
    import "./motor.fcstm" as LeftMotor {
        event /Start -> Start;
    }
}
```

这里右侧 `Start` 不指向 `System.LeftMotor.Start`，而是指向 import 所在的宿主 state，也就是 `System.Start`。

也就是说，事件映射的右侧相对路径解析基准是“import 所在 state”，而不是“被导入模块实例根”。

### 6.4 为什么只映射模块绝对事件

第一阶段建议只开放模块绝对事件映射，不允许直接把 `::` 或链式 `:` 事件跨实例共享，原因如下：

- `::` 的语义本来就是源状态局部
- 链式 `:` 的语义强依赖当前状态树位置
- 允许这两类事件被外部共享会显著增加重写复杂度和语义歧义

因此建议模块设计者若希望某个事件可被宿主提升或跨实例共享，应在模块内部主动使用模块根绝对事件 `/...`。

### 6.5 共享事件

两个同构模块要共享同一套事件，只需把各自模块绝对事件映射到同一宿主事件路径：

```fcstm
import "./motor.fcstm" as LeftMotor {
    event /Start -> Start;
}

import "./motor.fcstm" as RightMotor {
    event /Start -> Start;
}
```

若这两个 import 都位于宿主 `state System` 内，则此时两个模块都可响应宿主 `System.Start`。

若希望共享到更高层的事件总线，也可以显式写为：

```fcstm
import "./motor.fcstm" as LeftMotor {
    event /Start -> /Motors.Start;
}

import "./motor.fcstm" as RightMotor {
    event /Start -> /Motors.Start;
}
```

此时两个模块都可响应宿主 `Root.Motors.Start`。

### 6.6 默认未映射时的重写

若模块绝对事件未显式映射，建议默认重写到实例作用域下，例如：

- 模块内部 `/Start`
- 导入为 `LeftMotor`
- 默认展开后解析为 `System.LeftMotor.Start`

这样仍然保持实例隔离。

### 6.7 事件显示名称覆盖

事件映射支持在语句尾部添加 `named`，用于覆盖最终宿主事件的显示名称：

```fcstm
event /Start -> Start named "Motor Start";
event /Fault -> /GlobalFault named "Motor Fault";
```

建议显示名称优先级如下：

1. 事件映射语句上的 `named`
2. 宿主侧已存在目标事件的 `named`
3. 模块源事件自带的 `named`
4. 目标事件名本身

若多个映射命中同一目标事件并给出不同的 `named` 值，建议直接报冲突错误，避免最终显示名称不确定。

---

## 7. 路径与引用重写规则

为了使 import 保持“像内联一样”的最终语义，装配器需要在 AST 层统一重写路径。

### 7.1 需要重写的对象

- 状态根名称
- transition 中的 `event_id`
- `enter ref`
- `during ref`
- `exit ref`
- `>> during ... ref`
- force transition 中的 `event_id`
- 变量定义名
- 表达式中的变量引用
- 操作块中的赋值目标变量名

### 7.2 状态路径重写

被导入文件的 root state 名称被替换为 `Alias`。

### 7.3 模块绝对路径重写

模块内绝对路径 `/A.B` 在装配阶段按以下顺序处理：

1. 若命中显式映射规则，则映射到指定宿主目标
2. 否则重写为导入实例作用域下的默认路径

### 7.4 事件映射目标路径重写

事件映射右侧目标路径的解析规则建议为：

- 若右侧以 `/` 开头，则按宿主最终 root 绝对路径解析
- 若右侧不以 `/` 开头，则按“import 所在宿主 state”相对路径解析

例如：

```fcstm
state Root {
    state System {
        import "./motor.fcstm" as LeftMotor {
            event /Start -> Start;
            event /Stop -> Bus.Stop;
            event /Fault -> /GlobalFault;
        }
    }
}
```

应分别解析为：

- `Start` -> `Root.System.Start`
- `Bus.Stop` -> `Root.System.Bus.Stop`
- `/GlobalFault` -> `Root.GlobalFault`

### 7.5 相对路径重写

模块内相对路径继续保持相对语义，但其所属状态树已被整体挂载到 `Alias` 之下，因此最终会自然落到导入实例内部。

---

## 8. 编译与装配流程

### 8.1 推荐实现落点

推荐让 `parse_dsl_node_to_state_machine()` 直接承担“基于当前文件路径进行递归导入装配”的职责，同时把展开逻辑拆分到独立辅助模块中复用，而不是把 import 支持塞进运行时或模板系统。

建议流程：

1. 读取入口 `.fcstm`
2. 解析为 AST
3. 调用 `parse_dsl_node_to_state_machine(ast_node, path=...)`
4. 在模型构建过程中递归处理 import
5. 检测循环导入
6. 基于当前文件路径加载被导入 AST
7. 对导入模块执行变量与事件映射
8. 将导入模块根状态注入宿主状态树
9. 合并并生成最终 `StateMachineDSLProgram`
10. 继续完成后续状态机模型构建

### 8.2 新增组件建议

建议新增如下模块：

- `pyfcstm/dsl/imports.py`
  - 文件读取
  - import 解析与装配
  - 循环依赖检测
  - 路径/变量/事件重写
- `pyfcstm/dsl/node.py`
  - 增加 import AST 节点与映射 AST 节点
- `pyfcstm/dsl/listener.py`
  - 构建 import 相关 AST
- `pyfcstm/dsl/parse.py`
  - 保持纯语法解析职责，只返回 DSL AST，不承载文件路径或 import 装配语义
- `pyfcstm/model/model.py`
  - `parse_dsl_node_to_state_machine(..., path=...)` 负责接住路径上下文并驱动后续 import 装配

### 8.3 文件系统相对路径解析

建议将 import 源路径解析规则固定为：

- 若 `import` 路径是绝对路径，则直接使用该绝对路径
- 若 `import` 路径是相对路径，则相对于“当前正在解析的 fcstm 文件所在目录”解析
- 递归进入子 import 后，新的相对路径基准必须切换到子文件自己的所在目录

示例：

- 入口文件：`/a/b/c/root.fcstm`
- `root.fcstm` 中：`import "./d/e/xxx.fcstm"`
- 被导入文件：`/a/b/c/d/e/xxx.fcstm`
- `xxx.fcstm` 中：`import "./yyy.fcstm"`

则第二层 import 必须解析为：

- `/a/b/c/d/e/yyy.fcstm`

而不是：

- `/a/b/c/yyy.fcstm`

### 8.4 循环导入检测

装配器需要维护 import 栈，并在发现同一路径再次进入当前栈时直接报错。

示例：

- `A.fcstm -> B.fcstm -> A.fcstm`

应报：

- `Circular import detected: A.fcstm -> B.fcstm -> A.fcstm`

---

## 9. AST 与模型层影响

### 9.1 AST 层

建议新增节点：

- `ImportDefinition`
- `ImportDefMapping`
- `ImportEventMapping`

其中 `ImportDefinition` 至少包含：

- `file_path`
- `alias`
- `extra_name`
- `def_mappings`
- `event_mappings`

### 9.2 模型层

模型层需要最小限度地理解 import，并且需要知道“当前文档文件路径”以正确处理递归导入。

建议将接口调整为：

```python
parse_dsl_node_to_state_machine(
    dnode: StateMachineDSLProgram,
    path: Optional[str] = None,
) -> StateMachine
```

其中：

- `path` 可表示当前 `.fcstm` 文件路径，或显式指定的导入基准路径
- 若 `path` 为文件路径，则相对 import 基于其父目录解析
- 若 `path` 为目录路径，则直接以该目录作为导入基准
- 若 `path` 为 `None`，则默认使用当前工作目录

这样设计的原因是：

- 现有调用方不会因为 import 功能引入而崩溃
- CLI、测试、示例代码可以显式传入当前文件路径
- 递归导入时，父级 `parse_dsl_node_to_state_machine()` 可以继续调用自身，并把子文件路径传下去
- 多级相对 import 的解析基准可以自然随文件层级切换

建议实现方式：

- `parse_dsl_node_to_state_machine()` 负责维护当前解析基准与 import 栈
- 具体的文件读取、AST 解析、映射展开逻辑可委托给 `pyfcstm/dsl/imports.py`
- 在最终进入现有状态/事件/变量校验逻辑前，先把 import 展开为普通 `StateMachineDSLProgram`

这样虽然模型层不再是“完全不理解 import”，但改动边界仍然集中在构建入口，而不会扩散到 simulate、render、template、PlantUML 的后续流程。

---

## 10. VSCode 扩展支持方案

现有 VSCode 扩展位于 `editors/vscode/`，定位是“轻量、离线、非 LSP”的 ANTLR 解析扩展。import 方案需要按阶段支持，避免一次性把扩展做成完整语言服务器。

### 10.1 阶段一：单文件语法支持

第一阶段目标：

- 语法高亮识别 `import`、`as`
- ANTLR 语法允许 import
- diagnostics 能识别 import 语法错误
- outline 至少展示 import alias
- completion 提供 `import`、`as`、`named`、`def`、`event` 等关键字补全
- hover 提供 import 语义说明

需要更新的部位：

- `editors/fcstm.tmLanguage.json`
- `editors/vscode/src/parser.ts`
- `editors/vscode/src/diagnostics.ts`
- `editors/vscode/src/symbols.ts`
- `editors/vscode/src/completion.ts`
- `editors/vscode/src/hover.ts`
- 对应 verify 脚本

### 10.2 阶段二：工作区索引

第二阶段增加轻量工作区索引，而不是引入完整 LSP。

建议新增 `WorkspaceIndex`：

- 扫描工作区内 `.fcstm` 文件
- 解析每个文件的 import / root state / exports
- 建立文件依赖图
- 提供循环导入与路径不存在的编辑器诊断
- 为 import block 提供模块变量名、模块绝对事件路径补全
- 支持跳转到 import 文件
- hover 展示被导入文件摘要

### 10.3 阶段三：跨文件语义增强

后续可逐步扩展：

- import 路径跳转
- 映射目标合法性检查
- alias 冲突检查
- 同一宿主状态内重复导入别名冲突提示

### 10.4 不建议的路线

本阶段不建议直接引入完整 LSP，因为：

- 当前扩展定位明确偏轻量
- import 带来的首要需求并不需要完整语言服务器即可满足
- 维护复杂度会显著上升

---

## 11. 兼容性与落地策略

### 11.1 向后兼容

没有使用 import 的现有 DSL 文件行为保持不变。

### 11.2 建议分阶段交付

详细执行计划见第 12 节，后续实际推进应以第 12 节中的 phase / TODO / checklist 为准。

### 11.3 第一阶段建议边界

第一阶段功能建议严格限定为：

- 仅导入 root state
- `as` 必填
- `named` 选填
- 变量映射完整支持
- 仅模块绝对事件支持跨实例共享映射

---

## 12. 实施计划与推进规则

### 12.1 维护与同步规则

本节作为本 PR 的执行计划主文档。后续只要该 PR 仍用于跟踪 import 功能推进，就应持续维护本节中的 checkbox 状态。

推进时必须遵守以下规则：

* [ ] 每次准备 push 前，先同步本文档中的 phase、TODO 与 checklist checkbox 状态
* [ ] 每次 push 完成后，立即同步 GitHub PR body 中对应的 phase checkbox 状态
* [ ] 若某个 phase 的范围、拆分方式或验收口径发生变化，必须在同一次 push 中同时更新本文档与 PR body
* [ ] 只有当某个 phase 的 checklist 全部满足后，才允许勾选该 phase 的总览 checkbox
* [ ] GitHub PR body 中必须始终保留本文档链接，方便从 PR 直接跳转到详细设计与执行计划
* [ ] 每个 phase 在验收前都必须按影响范围执行回归测试；最少粒度为 `make unittest RANGE_DIR=./<一级模块>`，若影响跨一级模块或顶层链路，则应提升到更高层级，必要时执行 `make unittest`
* [ ] 新功能与修复对应的测试应尽可能提高覆盖率，尤其覆盖新增语法、装配逻辑、错误路径与回归场景
* [ ] 每个 phase 的单元测试必须拆分到对应的独立测试文件中，命名采用 `test_import_phaseN.py`
* [ ] 每个 phase 的典型正向 case 必须至少包含一类 `text_aligner` 驱动的整体验证：从 public API 加载模型后执行 `to_ast_node()` 再 `str(...)`，并对完整导出 DSL 文本做全量比对
* [ ] 测试构造过程中严禁直接使用任何 private / protected 模块、类、函数、方法、字段；所有测试一律通过 public API 构造输入与断言行为
* [ ] 所有新增或修改的 Python pydoc / docstring 必须严格遵循 AGENTS 中的 reST 与 docstring 规范，并与现有模块写法保持一致

### 12.2 Phase 总览

* [x] Phase 1: DSL Grammar / AST / Parse API 落地
* [x] Phase 2: Import 装配器与递归路径解析
* [x] Phase 3: `def` mapping 与变量合流校验
* [ ] Phase 4: event mapping 与路径重写
* [ ] Phase 5: CLI / generate / simulate / PlantUML 接入
* [ ] Phase 6: VSCode 扩展支持
* [ ] Phase 7: 测试、样例、文档与收尾

### 12.3 Phase 1: DSL Grammar / AST / Parse API 落地

本 phase 做到 parser 层已经能完整承载 import 语法与 mapping 语法，语法树与模型入口契约稳定可供后续装配实现使用，但尚不要求完成跨文件展开。当前实现中，`dsl.parse.parse_state_machine_dsl()` 保持纯 AST 入口，不接收路径上下文；DSL AST 也不在 `StateMachineDSLProgram` 上挂载文件路径。路径与 import 装配语义统一留在模型入口 `parse_dsl_node_to_state_machine(..., path=...)` 侧处理；在 Phase 2 完成前，模型入口遇到尚未装配的 import AST 会显式 fail fast，而不是静默忽略 import。

TODO

* [x] 修改 `GrammarLexer.g4` / `GrammarParser.g4`，加入 `import ... as ... named ... { ... }` 及 mapping 语法
* [x] 重新生成 ANTLR 产物，并确认生成文件已纳入正确的提交流程
* [x] 在 AST 节点层增加 import block、`def` mapping、event mapping 等节点表示
* [x] 更新 listener / parse 流程，使 import 语法可被解析为完整 AST
* [x] 为 `parse_dsl_node_to_state_machine()` 设计并落地 `path` 参数契约
* [x] 补齐最小正反例，覆盖 `as` 必填、`named` 选填、mapping block 可选等语法边界

Checklist

* [x] 新语法可以被 parser 正确接受并生成稳定 AST
* [x] 不含 import 的旧 DSL 文件解析行为保持不变
* [x] `path` 参数语义明确，且不会破坏现有调用方
* [x] 语法错误能定位到具体 import / mapping 语句，而不是只报笼统 parse 失败
* [x] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.4 Phase 2: Import 装配器与递归路径解析

本 phase 做到多文件 import 可按声明文件所在目录递归解析、检测循环导入，并把被导入 root state 以内联等价的方式挂载到宿主状态树中。

当前实现说明：

- `dsl.parse.parse_state_machine_dsl()` 仍保持纯 AST 解析，不接触文件路径与 import 装配
- Phase 2 的文件读取、递归 import 解析、循环检测与状态树内联均落在 model 层辅助装配器中，由 `parse_dsl_node_to_state_machine(..., path=...)` 驱动
- 本 phase 已完成结构装配与模块绝对路径默认实例化重写；后续 Phase 3 已在同一装配器内补完 `def mapping` 与 imported top-level `def` 合并，当前仅 `event mapping` 仍保留到 Phase 4

TODO

* [x] 增加 import 解析与装配辅助模块，负责文件加载、递归展开与错误组织
* [x] 让 `parse_dsl_node_to_state_machine(..., path=...)` 在模型构建前或构建中完成 import 递归处理
* [x] 实现“相对路径相对当前声明文件目录解析”的规则，并支持多级 import
* [x] 检测并报错：文件不存在、循环导入、被导入文件缺失 root state、同一宿主作用域 alias 冲突
* [x] 按 `as Alias` 重命名导入 root state，并应用 `named` 的显示名优先级规则
* [x] 保证装配后状态树对后续模型构建、渲染、模拟表现为普通内联状态树

Checklist

* [x] 多级相对路径 import 能按各自文件位置正确解析
* [x] 循环导入能被稳定检测，并给出可读错误链路
* [x] 只允许导入外部文件的 root state，其他情况均能明确报错
* [x] 装配结果在结构上等价于手工内联，不引入额外运行时概念
* [x] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.5 Phase 3: `def` mapping 与变量合流校验

本 phase 做到变量映射可在装配期间完整生效，包括 exact / set / pattern / fallback 规则、通配捕获、宿主同名绑定、跨 import 合流，以及严格禁止单个 import 内部 many-to-one。

TODO

* [x] 实现 exact、set、pattern、fallback 四类 `def` mapping 规则与优先级
* [x] 实现 Source 侧 `*` 捕获、Target 侧 `${n}` / `$n` / 裸 `*` 展开逻辑
* [x] 在装配阶段统一重写变量定义名、表达式中的变量引用、操作块赋值目标
* [x] 实现默认变量隔离规则，即未写 mapping 时等价于 `def * -> <Alias>_*;`
* [x] 严格禁止单个 import 实例内部多个源变量映射到同一个目标变量名
* [x] 允许不同 import 实例的不同源变量汇聚到同一目标变量名，但要求类型完全一致
* [x] 允许映射到宿主已有变量名，但要求宿主类型与 import 变量类型完全一致
* [x] 对共享目标变量执行初始化一致性校验：宿主未显式定义时需一致，宿主已定义时宿主定义优先

Checklist

* [x] 同一模块多次导入时，默认变量不会互相冲突
* [x] `def` mapping 的优先级、冲突规则与占位符语义都按文档实现
* [x] 单个 import 内部任何 many-to-one 变量收敛都会被直接拒绝
* [x] 跨 import 或宿主绑定的变量共享只会在类型完全一致时通过
* [x] `int` / `float` 混合汇聚会稳定报错
* [x] 当被导入子状态机在多层状态、guard、操作块与生命周期动作中大量使用变量时，`def` mapping 仍会把定义、引用与赋值目标一致地重写到宿主变量空间
* [x] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.6 Phase 4: event mapping 与路径重写

本 phase 做到模块绝对事件 `/...` 可被显式映射到宿主事件空间，并支持右侧相对路径、绝对路径与 `named` 显示名覆盖；未映射事件则继续按实例局部化处理。

当前实现说明：

- 仅允许 `event mapping` 左侧使用模块绝对事件路径 `/...`
- 右侧相对路径按 `import` 所在宿主 state 解析，右侧绝对路径按宿主 root 解析
- 映射不仅会重写普通 transition，也会覆盖 force transition 与指向同一模块根事件的等价相对引用
- 若被映射的模块事件在源 AST 中有显式 `event` 定义，其定义会迁移到宿主目标作用域，避免装配后残留重复事件节点
- 宿主目标事件支持 `named` 覆盖，并会对跨 import / 宿主已有事件的显示名冲突做显式报错
- 对于“最终落到宿主祖先 state 上的事件引用”，当前 `to_ast_node()` 会保真导出为绝对路径，如 `/System.Start`。这是因为现有 DSL / AST 尚无专门语法无歧义表达“祖先作用域 chain event 引用”

TODO

* [x] 实现模块绝对事件路径的识别、默认实例内重写与显式映射逻辑
* [x] 支持 event mapping 左侧仅接受模块绝对事件路径
* [x] 支持 event mapping 右侧解析为宿主绝对路径或相对于 import 所在 state 的相对路径
* [x] 支持 event mapping 上的 `named`，用于覆盖最终宿主事件显示名称
* [x] 在装配阶段重写 transition、force transition 与相关路径引用中的事件路径
* [x] 校验共享目标事件的显示名冲突与路径冲突
* [x] 保持 `::`、链式 `:` 与模块绝对 `/...` 在导入后的语义边界清晰且可预测

Checklist

* [x] `event /Start -> Start;` 能正确解析为 import 所在宿主 state 下的 `Start`
* [x] `event /Start -> /Motors.Start;` 能正确解析为宿主 root 下的绝对事件路径
* [x] 未映射的模块绝对事件会落到实例作用域而不是错误提升到宿主 root
* [x] 多个 import 共享同一宿主事件时，路径和显示名行为可预测且冲突可诊断
* [x] 即便子状态机内有多个 transition 指向同一个模块绝对事件，event mapping 后这些 transition 仍会稳定绑定到同一个宿主事件对象
* [x] Phase 4 单元测试使用独立的 `test_import_phase4.py`，且典型正向 case 至少包含 `text_aligner` 驱动的 `to_ast_node()` 全量导出 DSL 比对
* [x] Phase 4 的复杂正向 case 也必须覆盖多 import 共享事件、宿主相对多段目标、显式事件定义迁移、force transition 重写，以及嵌套 import 下的二次 event remap 链，并继续使用 `text_aligner` 做完整 DSL 结构比对
* [x] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.7 Phase 5: CLI / generate / simulate / PlantUML 接入

本 phase 做到 import 装配能力进入现有主链路，用户通过现有 CLI 命令即可处理多文件模型，而不需要额外工具或新入口。

TODO

* [ ] 将 import-aware 的 parse / build 流程接入 `generate`
* [ ] 将 import-aware 的 parse / build 流程接入 `plantuml`
* [ ] 将 import-aware 的 parse / build 流程接入 `simulate`
* [ ] 确保 CLI 入口能把输入文件路径正确传入 `path` 参数
* [ ] 为缺失文件、循环导入、mapping 冲突等错误提供面向用户的可读输出
* [ ] 验证模板渲染侧看到的是装配完成后的最终状态机，而不是残留 import 语义

Checklist

* [ ] `pyfcstm generate` 可以处理多文件 import 模型
* [ ] `pyfcstm plantuml` 输出的结构与装配后的状态树一致
* [ ] `pyfcstm simulate` 可以在多文件装配后正常运行
* [ ] 现有单文件使用路径在 CLI 层保持兼容
* [ ] Phase 5 单元测试使用独立的 `test_import_phase5.py`，且典型正向 case 至少包含 `text_aligner` 驱动的 `to_ast_node()` 全量导出 DSL 比对
* [ ] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.8 Phase 6: VSCode 扩展支持

本 phase 做到 VSCode 扩展至少能识别 import 语法、给出基础诊断，并在工作区级别支持 import 文件导航与轻量索引，不引入完整 LSP。

TODO

* [ ] 更新 VSCode 语法高亮与相关语法定义，覆盖 `import`、`as`、mapping block、event mapping
* [ ] 为 import 路径、alias 冲突、缺失文件、循环导入提供基础诊断入口
* [ ] 增加轻量 `WorkspaceIndex`，索引工作区内 `.fcstm` 文件与 import 依赖关系
* [ ] 支持从 import 路径跳转到目标文件
* [ ] 为 import block 提供模块变量名、模块绝对事件路径等基础补全能力
* [ ] 在 hover 或辅助信息中展示被导入文件 root state 的摘要信息

Checklist

* [ ] 扩展能稳定识别 import 相关新语法
* [ ] 缺失文件与循环导入能在编辑器内得到可用提示
* [ ] 至少支持从 import 源路径跳转到被导入文件
* [ ] 工作区索引不会把扩展复杂度直接推向完整 LSP
* [ ] Phase 6 单元测试使用独立的 `test_import_phase6.py`，且典型正向 case 至少包含 `text_aligner` 驱动的 `to_ast_node()` 全量导出 DSL 比对
* [ ] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

### 12.9 Phase 7: 测试、样例、文档与收尾

本 phase 做到 import 功能具备可回归测试、样例工程、用户文档和最终验收口径，能够作为正式功能进入后续发布流程。

TODO

* [ ] 增加 parser 层测试，覆盖 import 语法与正反例
* [ ] 增加装配层测试，覆盖多级相对路径、循环导入、alias 冲突、root state 限制
* [ ] 增加变量映射与事件映射测试，覆盖共享、冲突与边界条件
* [ ] 增加 CLI / PlantUML / simulate 集成测试
* [ ] 增加多文件 sample DSL，作为回归样例与文档示例
* [ ] 更新用户文档、教程与必要的变更说明
* [ ] 在最终合并前统一核对本文档与 PR body 中全部 checkbox 状态

Checklist

* [ ] 关键 pass / fail 路径都有自动化测试覆盖
* [ ] 样例 DSL 能直观展示 import、变量映射、事件映射的推荐写法
* [ ] 文档、PR body、实现状态三者一致
* [ ] 不使用 import 的现有功能回归测试全部通过
* [ ] Phase 7 单元测试使用独立的 `test_import_phase7.py`，且典型正向 case 至少包含 `text_aligner` 驱动的 `to_ast_node()` 全量导出 DSL 比对
* [ ] 已按影响范围完成回归测试；至少使用 `make unittest RANGE_DIR=./<一级模块>` 级别命令，若本 phase 影响跨一级模块或顶层链路，则已提升到更高层级

---

## 13. 当前建议结论

基于当前代码架构，推荐采用以下方案作为主线：

- 使用编译期多文件装配，不做运行时模块系统
- import 只导入目标文件 root state
- 每个 import 必须显式 `as Alias`
- 通过 `named` 重载显示名称
- 变量默认按 alias 隔离，靠显式映射实现共享
- 事件默认实例隔离，仅模块绝对事件支持显式提升或共享
- 文件系统相对 import 一律相对当前声明文件逐级解析
- `parse_dsl_node_to_state_machine()` 接收 `path` 参数并负责递归 import 装配
- VSCode 先做语法与轻量工作区索引，不切换到 LSP

---
