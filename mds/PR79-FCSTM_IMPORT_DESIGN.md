# FCSTM 多文件导入与模块装配设计

## PR 信息

- PR 编号：79
- PR 链接：https://github.com/HansBug/pyfcstm/pull/79
- 文档链接：https://github.com/HansBug/pyfcstm/blob/dev/import/mds/PR79-FCSTM_IMPORT_DESIGN.md

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
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

### 5.10 目标名冲突与共享边界

多个不同源变量若最终展开到同一个目标变量名，默认报错。

例如：

```fcstm
def {a, b} -> shared_var;
```

若这意味着 `a` 和 `b` 都将映射到同一个 `shared_var`，则应直接报错，而不是隐式制造 many-to-one 共享。

建议第一阶段只允许以下形式的显式共享：

- 不同 import 实例中的同名源变量，通过精确规则映射到同一个目标变量名

例如：

```fcstm
import "./worker.fcstm" as A {
    def counter -> shared_counter;
}

import "./worker.fcstm" as B {
    def counter -> shared_counter;
}
```

此时可视为显式共享 `counter`。

但集合规则、模式规则、兜底规则不应默认承担“制造共享变量”的职责。

### 5.11 类型与初始化校验

当多个 import 最终把变量映射到同一目标变量名时，仍需执行一致性校验：

- 变量类型必须一致
- 初始化表达式必须一致，或宿主文件已显式定义该目标变量
- 若类型不一致，报错
- 若初始化冲突且宿主未显式覆盖，报错

建议错误示例：

- `Variable mapping conflict: target variable 'shared_counter' has inconsistent type 'int' vs 'float'.`
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
  - 增加面向文件的高层入口，例如 `load_state_machine_program_from_file()`

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

建议按以下顺序推进：

1. 语法与 AST 支持 import
2. 编译期装配器与展开
3. 变量映射
4. 模块绝对事件映射
5. CLI / generate / simulate / PlantUML 接入文件装配入口
6. VSCode 第一阶段支持
7. VSCode 工作区索引

### 11.3 第一阶段建议边界

第一阶段功能建议严格限定为：

- 仅导入 root state
- `as` 必填
- `named` 选填
- 变量映射完整支持
- 仅模块绝对事件支持跨实例共享映射

---

## 12. 当前建议结论

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
