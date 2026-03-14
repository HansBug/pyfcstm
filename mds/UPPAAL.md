# UPPAAL 模型、机理、性质与 DSL 设计

本文按三个层次展开：

1. 先讲 UPPAAL 的模型本体，也就是它到底建模什么、模型由哪些部分组成、系统如何演化。
2. 再讲 UPPAAL 的性质语言，也就是可以验证哪些问题、语法和语义分别是什么。
3. 最后给出一套面向 **纯模型语义** 的 DSL 设计。这里的目标不是保留 GUI/XML 的视觉布局，而是无损表达可用于验证的模型本身。

默认讨论的是经典 UPPAAL `verifyta` 所使用的 **symbolic semantics** 与 **symbolic queries**。涉及 SMC 的地方会单独说明，但本文的中心不是概率/统计模型检验，而是经典 timed automata 验证。

---

## 第一部分：UPPAAL 的模型与运行机理

## 1. UPPAAL 在建模什么

UPPAAL 的核心对象是 **network of extended timed automata**，也就是：

- 若干个并行运行的自动机
- 每个自动机都有位置（location）和边（edge）
- 系统里有时钟、整数、布尔量、通道、数组、结构体等变量
- 自动机之间可以通过同步通道交互
- 时间既可以流逝，也可以发生离散跳转

因此，UPPAAL 不是一个单纯的“状态机画图工具”，也不是一个通用程序验证器。它面向的是：

- 具有明确控制状态的系统
- 对时间约束敏感的系统
- 组件之间通过同步协作的系统

典型例子包括：

- 协议
- 调度器
- 设备控制逻辑
- 资源互斥系统
- 带超时与等待窗口的工作流

## 2. 一个 UPPAAL 模型由什么组成

从“可验证模型”的角度看，一个完整的 UPPAAL 系统主要包含：

- 全局声明
- 若干模板（templates）
- 模板实例化
- system line
- 可选的优先级定义
- 可选的查询集合

如果写成抽象结构，可以表示为：

```text
Model = (GlobalDecls, Templates, Instantiations, System, Priorities, Queries)
```

其中最核心的是前四项：

- `GlobalDecls`
  - 定义全局类型、变量、时钟、通道、函数
- `Templates`
  - 定义自动机结构
- `Instantiations`
  - 把模板参数绑定成具体进程模板
- `System`
  - 决定哪些进程实际并行组成系统，以及它们的顺序

查询 `Queries` 不改变模型本身，只是作用在模型上的验证问题。

## 3. 声明层：类型、变量、函数、参数、作用域

### 3.1 声明的三种常见位置

UPPAAL 里常见的声明位置有三类：

- 全局声明
- 模板局部声明
- system definition 内的声明

它们的作用不同：

- 全局声明对所有模板和 query 可见
- 模板局部声明只对该模板可见
- system definition 内声明通常服务于实例化和系统组装

### 3.2 常见类型

UPPAAL 的常用类型包括：

- `int`
- `bool`
- `clock`
- `chan`
- `double`
- `string`

以及基于它们构造出的：

- 有界整数：`int[l, r]`
- 标量集合：`scalar[n]`
- 数组
- `struct`
- `typedef`

几个常见前缀也很重要：

- `const`
- `meta`
- `urgent`
- `broadcast`

它们分别影响：

- 常量性
- 是否进入状态空间
- 通道同步时的时间语义
- 通道是二元同步还是广播同步

### 3.3 时钟、整数、布尔和通道各自扮演什么角色

- **clock**
  - 用来表达时间约束
  - 可以在 guard / invariant 中出现
  - 常见更新是 `x = 0`
- **int / bool**
  - 用来表示离散状态数据
  - 可以出现在 guard、update、query 中
- **chan**
  - 用来实现进程间同步
  - 通过 `c!` / `c?` 配对

一个很重要的区别是：

- clock 的使用受 timed automata 语义限制更强
- int / bool 的表达式能力更接近普通程序语言

### 3.4 函数

UPPAAL 支持用户自定义函数，也支持 external functions。函数可以用于：

- 初始化表达式
- guard / invariant 所依赖的表达式
- update

但要明确：

- query、guard、invariant 里的表达式必须满足对应的 side-effect 和类型限制
- update 则允许副作用

### 3.5 参数与传参方式

模板和函数都可以带参数，支持：

- 值传递
- 引用传递 `&`

几个关键约束：

- `clock` 参数必须按引用传递
- `chan` 参数必须按引用传递
- 数组若要按引用传递，也必须显式写 `&`

### 3.6 作用域规则

UPPAAL 每个上下文基本上只有一个名字空间。这意味着：

- 同一上下文里的变量名、类型名、位置名、参数名不能冲突
- 模板局部名字可以遮蔽全局名字

这一点对 DSL 设计非常重要，因为它意味着：

- location 不是“另一个完全独立的命名域”
- 不能简单假设“状态名永远不会与变量名冲突”

## 4. 模板：扩展时间自动机的主体

UPPAAL 中的一个 template，本质上就是一个扩展时间自动机。它主要由这些元素构成：

- 参数列表
- 局部声明
- 位置集合
- 初始位置
- 边集合
- 可选分支点

抽象地写就是：

```text
Template = (Params, LocalDecls, Locations, Branchpoints, Init, Edges)
```

## 5. 位置（locations）

### 5.1 位置是什么

位置就是自动机当前控制状态的离散位置。系统某一时刻处在哪个位置，会直接决定：

- 哪些边可能启用
- 时间是否允许流逝
- 某些 query 中的原子命题是否为真

### 5.2 位置的常见属性

一个位置通常可以带有：

- 可选名字
- invariant
- urgent 标记
- committed 标记
- 在 SMC 中可选的 exponential rate

对经典 symbolic 语义最重要的是前三项。

### 5.3 初始位置

每个模板必须且只能有一个初始位置。系统初始状态中，每个进程都从各自模板的初始位置开始。

### 5.4 invariant 的作用

位置上的 invariant 不是“用来验证的性质”，而是 **模型语义的一部分**。它的含义是：

- 只要系统停留在该位置
- 当前 valuation 就必须满足 invariant
- 一旦不满足，该状态就根本不属于模型状态空间

因此 invariant 和 query 中的安全条件完全不是一回事：

- invariant 决定哪些状态存在
- query 判断存在的状态是否满足某种性质

### 5.5 invariant 的语法限制

虽然 invariant 写成表达式，但经典 symbolic 语义下它受额外限制。通常允许：

- 时钟上界
- 时钟差分约束
- 不涉及时钟的布尔表达式
- `forall` 形式
- stopwatch / derivative 相关写法

但它不是任意布尔表达式都能写。

## 6. urgent 和 committed 的机理

### 6.1 urgent location

urgent location 的含义是：

- 进程处于该位置时，时间不允许流逝

可以把它理解成“必须立刻采取离散动作或同步”。

### 6.2 committed location

committed location 更强。它不仅要求：

- 时间不能流逝

还要求：

- 下一步离散迁移必须涉及某个 committed 位置

它通常用于：

- 编码原子步骤
- 将复杂同步拆成多步但又不让其他动作插入
- 表达“这一步之后必须马上续上下一步”

### 6.3 二者的区别

- `urgent`
  - 只禁止时间流逝
- `committed`
  - 既禁止时间流逝，也限制下一步动作的参与者

## 7. 边（edges）

一条边至少包含：

- 源位置
- 目标位置

并且可以带有如下标签：

- `select`
- `guard`
- `synchronisation`
- `update`
- 概率相关的 `weight`

## 8. select、guard、sync、update 分别是什么

### 8.1 select

`select` 用来做非确定绑定。例如：

```text
select i : int[0, 3]
```

它的含义是：

- 在该边被考虑时
- `i` 非确定地取该类型域中的某个值
- 这个绑定在 guard / sync / update 中可见

### 8.2 guard

guard 表示边何时 enabled。只有 guard 为真，边才可能被走。

在经典 timed automata 语义下，guard 中常见的是：

- 时钟上下界约束
- 时钟差分约束
- 不涉及时钟的布尔表达式

### 8.3 synchronisation

同步标签写作：

- `c!`
- `c?`

它表示：

- 某个发送边和某个接收边必须一起发生

UPPAAL 支持两类主要同步：

- 二元同步
- 广播同步

### 8.4 update

当边被执行时，update 会依次执行。这里有一个非常关键的点：

- update 是 **顺序执行**
- 不是并发赋值

例如：

```text
x = 1, y = 2 * x
```

其结果中 `y` 看到的是更新后的 `x`。

## 9. 二元同步与广播同步

### 9.1 二元同步

二元同步要求：

- 两个不同进程中有一条 `c!` 边和一条 `c?` 边
- 两条边的 guard 都满足
- 它们一起执行

并且 update 的顺序是：

- 先执行 `!` 侧 update
- 再执行 `?` 侧 update

### 9.2 广播同步

若通道是 `broadcast chan`，则语义不同：

- 发送端 `c!` 在 guard 成立时可以独立发送
- 所有当前已启用的 `c?` 接收边都必须参与同步

广播同步下 update 顺序是：

- 先执行发送端 update
- 再按 system line 中的进程顺序执行所有接收端 update

这个“按 system line 顺序执行”是非常关键的语义细节。

### 9.3 urgent channel 的影响

若通道是 `urgent chan`，则：

- 一旦该同步可触发，就不能再拖延时间

并且还要注意一些限制：

- urgent channel 上不允许 clock guard
- broadcast 接收边上也不允许 clock guard

## 10. branchpoint 与概率权重

除了普通 location，UPPAAL 还支持 branchpoint，主要用于：

- 表达概率分支
- 把“先决策，再分流”的结构显式建模

与之配套的是 weight：

- 在 SMC / 概率语义中，weight 决定分支概率比例
- 在经典 symbolic 语义中，weight 会被抽象掉

因此从经典验证角度看：

- weight 不影响真假型 symbolic query 的状态可达性 over-approximation

但从统一模型语言角度看，它仍然是模型元素的一部分。

## 11. system definition：实例化与并行组合

### 11.1 为什么模板和系统不是一回事

模板只是“可被实例化的自动机定义”，并不自动成为系统进程。真正组成系统的是：

- 模板实例化
- system line

### 11.2 模板实例化

UPPAAL 支持：

- 直接列出无参数模板
- 对参数化模板做部分实例化或完全实例化

例如：

```text
P1 = Worker(0);
P2 = Worker(1);
system P1, P2;
```

这里：

- `Worker` 是模板
- `P1`、`P2` 是实例化后的模板名/进程名来源

### 11.3 system line 的作用

`system` 行不只是把进程名字列出来，它还决定：

- 系统到底包含哪些进程
- 广播接收 update 的执行顺序
- 某些优先级相关比较中的顺序依据

所以它是语义的一部分，不是可忽略的样板文本。

## 12. 优先级（priorities）

UPPAAL 支持：

- channel priority
- process priority

它们的直觉语义是：

- 在同一时刻，如果高优先级动作 enabled
- 低优先级动作会被阻塞

几个关键点：

- 延时迁移不会被动作优先级阻塞
- 在同步动作中，多个进程的优先级取其中最高者
- 若同时有 channel 与 process priority，先比较 channel，再比较 process

## 13. 状态、valuation 与系统状态空间

从语义上看，UPPAAL 的一个系统状态可以写成：

```text
State = (L, v)
```

其中：

- `L`
  - 各个进程当前所在位置组成的向量
- `v`
  - 时钟和离散变量当前取值

并且必须满足：

- `v` 满足当前 `L` 对应位置组合的 invariant

因此，一个状态不是“程序计数器 + 变量值”这么简单，而是：

- 多个并行进程的位置向量
- 全部变量与时钟取值
- invariant 约束后的合法状态

## 14. 两类迁移：时间迁移与动作迁移

UPPAAL 的 transition relation 包含两类迁移：

- delay transitions
- action transitions

### 14.1 delay transition

时间迁移表示：

- 经过非负实数时间 `d`
- 进程位置不变
- 所有时钟随时间推进

它成立的条件包括：

- 整个等待区间内 invariant 始终成立
- 当前不存在 committed/urgent 位置阻止时间流逝
- urgent channel 的可触发同步也不能被拖延

### 14.2 action transition

动作迁移表示：

- 某条内部边执行
- 或某次二元同步发生
- 或某次广播同步发生

其成立通常要求：

- guard 成立
- update 执行成功
- 目标状态满足 invariant
- committed 约束满足
- 没有更高优先级动作阻塞它

## 15. invalid evaluation 与验证中止

UPPAAL 不是“表达式出错就返回 false”，而是：

- 如果 successor computation 过程中出现 invalid evaluation
- 验证会中止

常见 invalid 情况包括：

- 除零
- 数组越界
- 整数越界赋值
- 给 clock 赋负值
- shift 次数非法

这点很重要，因为它意味着：

- 某些模型错误不是“性质不成立”
- 而是“模型本身非法，验证无法继续”

## 16. deadlock 到底是什么

UPPAAL 里的 `deadlock` 不是“当前没有一条离散边能走”这么简单，而是：

- 当前既不能立即执行动作
- 也不能通过继续等待一段时间后再执行动作

换言之，它是：

- 动作无路可走
- 时间也无路可走

这就是为什么 `A[] not deadlock` 是一个非常基础也非常重要的检查。

## 17. symbolic 与 SMC 的边界

虽然 UPPAAL 家族支持很多扩展能力，但必须明确：

- 经典 symbolic 语义
  - 面向严格的状态空间验证
  - 对 guard / invariant / 时钟约束有限制
- SMC
  - 面向随机仿真和统计估计
  - 允许更多浮点与动态导数特性

因此一个“UPPAAL 模型”能否被哪种引擎支持，不只取决于语法是否能写出来，还取决于该子引擎的语义和限制。

---

## 第二部分：UPPAAL 的性质语言

## 18. 什么是 query

有了前面的模型之后，query 就是在这个状态空间上提问题。常见问题有：

- 坏状态是否可达
- 某个条件是否始终成立
- 某个目标是否必然最终发生
- 请求发生后是否最终响应
- 某个量的上界/下界/区间是多少

因此 query 的对象是：

- 模型诱导出的状态空间
- 而不是模板源代码本身

## 19. 两类常见性质语言

UPPAAL 家族里最常见的两类性质语言是：

- 经典 symbolic queries
- SMC statistical queries

本文重点讨论第一类，也就是：

- `A[]`
- `E<>`
- `E[]`
- `A<>`
- `-->`
- `sup / inf / bounds`

## 20. 经典 symbolic queries 的核心语法

UPPAAL 中经典 symbolic query 的高频形式可以概括为：

```text
A[] φ
E<> φ
E[] φ
A<> φ
φ --> ψ

sup: e1, e2, ...
sup{φ}: e1, e2, ...
inf: e1, e2, ...
inf{φ}: e1, e2, ...
bounds: e1, e2, ...
bounds{φ}: e1, e2, ...
```

这里：

- `φ`、`ψ` 是状态谓词
- `A` 表示所有路径
- `E` 表示存在路径
- `[]` 表示始终
- `<>` 表示最终
- `-->` 表示 leads-to / 响应性质

## 21. 状态谓词 `φ` 能写什么

query 里的 `φ`、`ψ` 是对单个状态求值的表达式，常见内容包括：

- 位置谓词：`P.Wait`
- 特殊谓词：`deadlock`
- 布尔条件：`not error`
- 整数比较：`count < 3`
- 时钟约束：`x <= 5`
- 差分约束：`x - y < 2`
- 量词：`forall(...)`、`exists(...)`
- 聚合：`sum(...)`

例如：

```text
P.Done
not deadlock
P.CS imply not Q.CS
x <= 5 and y - x < 3
forall(i : int[0, 3]) not worker[i].Error
```

query 中的状态表达式必须是 **side-effect free** 的。它们只能观察状态，不能修改状态。

## 22. 五类经典布尔性质

### 22.1 `E<> φ`：可达性

```text
E<> φ
```

含义：

- 存在一条路径
- 其未来某个状态满足 `φ`

它表达的是：

- `φ` 是否可达

典型例子：

```text
E<> error
E<> P.Done
E<> P.CS and Q.CS
```

### 22.2 `A[] φ`：安全性 / 不变性

```text
A[] φ
```

含义：

- 对所有路径
- 所有可达状态都满足 `φ`

它表达的是：

- 某个坏事永远不发生

典型例子：

```text
A[] not deadlock
A[] not (P.CS and Q.CS)
A[] x <= 10
```

### 22.3 `A<> φ`：必然最终发生

```text
A<> φ
```

含义：

- 对所有路径
- 最终都会遇到某个满足 `φ` 的状态

它表达的是：

- 某件事一定最终发生

这和 `E<> φ` 的区别必须分清：

- `E<> φ`：可能发生
- `A<> φ`：必然发生

### 22.4 `E[] φ`：存在一路始终满足

```text
E[] φ
```

含义：

- 存在一条路径
- 这条路径上的每个状态都满足 `φ`

它表达的是：

- 存在一种演化方式，可以一直保持 `φ`

### 22.5 `φ --> ψ`：响应性质

```text
φ --> ψ
```

含义：

- 每当到达一个满足 `φ` 的状态
- 后续都必须最终到达满足 `ψ` 的状态

它非常适合表达：

- 请求最终响应
- 故障最终恢复
- 等待最终获得服务

## 23. 这些性质的语义如何依赖系统机理

理解 query，必须回到前面的系统机理：

- 路径是由 delay transition 和 action transition 交替构成的
- 状态必须满足 invariant
- committed / urgent / priority 都会影响路径结构

因此 query 不是脱离模型机理单独成立的。例如：

- `deadlock` 依赖时间迁移是否还允许
- `A<> done` 依赖是否存在无穷拖延或 committed/urgent 结构导致的路径
- `P.Wait --> P.Run` 依赖同步顺序、guard 和 invariant 是否允许响应发生

## 24. 常用等价关系

几个非常有用的等价关系是：

```text
A[] φ    ≡ not E<> not φ
A<> φ    ≡ not E[] not φ
φ --> ψ  ≡ A[] (φ imply A<> ψ)
```

这些等价关系的用途主要有两个：

- 帮助理解语义
- 帮助把性质转成“找反例”思维

例如：

```text
A[] safe
```

可以从反例视角理解成：

```text
E<> not safe
```

是否存在一个可达坏状态。

## 25. 数值查询：`sup`、`inf`、`bounds`

除了真假型 query，UPPAAL 还支持数值型查询。

### 25.1 `sup`

```text
sup: e
sup{φ}: e
```

含义：

- 求表达式 `e` 的上界 / 上确界
- 若带 `{φ}`，则只在满足 `φ` 的状态中考虑

### 25.2 `inf`

```text
inf: e
inf{φ}: e
```

含义：

- 求表达式 `e` 的下界 / 下确界

### 25.3 `bounds`

```text
bounds: e
bounds{φ}: e
```

含义：

- 求表达式 `e` 的可能取值边界 / 区间信息

这类查询通常用于：

- 某个 cost 的最大值
- 某个时钟在某位置上的可能范围
- 某个变量在某类状态中的上下界

## 26. query 中最容易混淆的几点

### 26.1 invariant 不是 query

很多新手会把：

- location invariant
- `A[] φ`

混在一起。但两者完全不同：

- invariant 决定状态是否合法
- `A[] φ` 是对合法状态空间做验证

### 26.2 `E<>` 不等于 `A<>`

这是一类最常见错误：

- `E<> done`
  - 只表示“存在一种成功执行”
- `A<> done`
  - 才表示“无论如何最终都会完成”

### 26.3 `A[] not deadlock` 比“没有边可走”更强

因为 `deadlock` 同时要求：

- 没有动作可走
- 时间也不能再往前走

### 26.4 query 看的是真正的状态，不是更新过程中的中间步骤

UPPAAL 验证的是状态空间中的状态点，而不是某次 update 内部每条赋值的“过程动画”。

这在多进程同步和顺序 update 下尤其重要。

## 27. 典型 query 模板

### 27.1 坏状态不可达

```text
A[] not bad
```

或从反例角度写成：

```text
E<> bad
```

### 27.2 互斥

```text
A[] not (P.CS and Q.CS)
```

### 27.3 无死锁

```text
A[] not deadlock
```

### 27.4 终止性

```text
A<> done
```

### 27.5 响应性

```text
request --> grant
```

### 27.6 数值上界

```text
sup: cost
sup{Busy}: waiting_time
```

## 28. 一页速查

```text
E<> φ      存在一条路径，最终到达 φ
A[] φ      所有路径上的所有状态都满足 φ
A<> φ      所有路径最终都会到达 φ
E[] φ      存在一条路径，其上始终满足 φ
φ --> ψ    每次 φ 发生后，之后最终一定出现 ψ
sup: e     求 e 的上界
inf: e     求 e 的下界
bounds: e  求 e 的可能边界/区间
```

## 29. 与 SMC query 的区别

SMC 查询长得会明显不同，例如：

```text
Pr[<=10](<> goal)
E[<=20](max: cost)
```

它们的特点是：

- 基于采样和统计估计
- 返回概率或估计值

而经典 symbolic query 的特点是：

- 在符号状态空间上做严格验证
- 返回真假或精确边界信息

---

## 第三部分：UPPAAL 官方数据格式与纯模型 DSL

## 30. UPPAAL 官方标准数据格式是什么

如果说“UPPAAL 标准的数据格式”，最需要区分的是两层：

- **模型语义格式**
  - 用来表达 timed automata 模型本身
- **工程辅助格式**
  - 用来保存布局、查询或其他附属信息

在实际工具链里，最常见的几种格式是：

- `.xml`
- `.xta`
- `.ta`
- `.ugi`
- `.q`

### 30.1 最常见、最标准的是 NTA XML

对今天的 UPPAAL 用户来说，最标准、最常见、也是 GUI 原生使用的格式，其实是：

- **NTA XML**

也就是一个以 `<nta>` 为根节点的 XML 文档。它通常包含：

- `<declaration>`
- 一个或多个 `<template>`
- `<system>`
- `<queries>`

从结构上看，它大致是：

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System ...//EN' '...'>
<nta>
  <declaration>...</declaration>
  <template>...</template>
  <system>...</system>
  <queries>...</queries>
</nta>
```

这就是你在 GUI 里最常接触到的“UPPAAL 模型文件”。

### 30.2 `.xta` 是文本化模型格式

`.xta` 更接近“文本化的模型语义表示”。它通常写：

- declarations
- process / template
- state / init / trans
- system

它比 XML 更适合纯文本编辑和程序生成，但它不是 GUI 里最典型的原生持久化形态。

### 30.3 `.ta` 是更老、更小的子集

`.ta` 是更老的文本格式，能力和使用频率都不如 `.xml` / `.xta`。如果目标是现代 UPPAAL 模型表达，通常不以 `.ta` 作为首选。

### 30.4 `.ugi` 主要是图形信息

`.ugi` 的作用主要与图形界面展示有关，例如：

- 布局
- 图形信息

它不是表达 timed automata 语义本体的最佳中心格式。

### 30.5 `.q` 是独立查询文件

查询既可以嵌在 XML 的 `<queries>` 里，也可以单独存成 `.q` 文件。因此：

- 模型文件
- 查询文件

在工具链里是可以分开的。

### 30.6 做 DSL 转换时，优先输出哪种标准格式

如果目标是把自定义 DSL 转成“标准 UPPAAL 数据格式”，最稳妥的建议是：

- 第一优先输出 **NTA XML**
- 第二优先按需提供 **XTA**

原因是：

- XML 是 GUI 主工作流里最常见的标准格式
- XML 覆盖能力最完整
- XML 可以直接内嵌 `<queries>`
- XML 与官方示例、GUI 和生态工具最容易对接

如果只追求纯文本、尽量少视觉噪声，再考虑输出 `.xta`。

## 31. NTA XML 到底长什么样

下面给出一个最小、可读的 NTA XML 例子。这个例子表达的是：

- 一个全局时钟 `x`
- 一个模板 `P`
- 两个位置 `Idle` 和 `Done`
- 初始位置是 `Idle`
- 一条从 `Idle` 到 `Done` 的边
- 一个可达性查询 `E<> P.Done`

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>
<nta>
  <declaration>clock x;</declaration>
  <template>
    <name x="5" y="5">P</name>
    <declaration></declaration>
    <location id="id0" x="0" y="0">
      <name x="-10" y="-20">Idle</name>
      <label kind="invariant" x="0" y="20">x &lt;= 5</label>
    </location>
    <location id="id1" x="120" y="0">
      <name x="110" y="-20">Done</name>
    </location>
    <init ref="id0"/>
    <transition>
      <source ref="id0"/>
      <target ref="id1"/>
      <label kind="guard" x="50" y="-20">x &gt;= 3</label>
      <label kind="assignment" x="50" y="20">x = 0</label>
    </transition>
  </template>
  <system>system P;</system>
  <queries>
    <query>
      <formula>E&lt;&gt; P.Done</formula>
      <comment>reachability</comment>
    </query>
  </queries>
</nta>
```

这个格式里有两个特点要看清：

- 模型语义和查询可以放在同一个 XML 文件里
- XML 同时也带着一些 GUI 友好的字段，例如 `x` / `y` 坐标

所以如果你问“UPPAAL 最标准的官方文件长什么样”，答案一般就是：

- **一个 `<nta>` 根节点的 XML 文件**

### 31.1 对转换器最重要的顶层骨架

对“DSL -> UPPAAL XML”来说，最实用的不是泛泛地说“它是个 XML”，而是记住它的常见骨架：

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.6//EN' 'https://www.it.uu.se/research/group/darts/uppaal/flat-1_6.dtd'>
<nta>
  <declaration>...</declaration>

  <template>...</template>
  <template>...</template>
  ...

  <system>...</system>

  <queries>
    <query>
      <formula>...</formula>
      <comment>...</comment>
    </query>
  </queries>
</nta>
```

这里要特别注意：

- `<system>` 对完整模型来说是必需的
- `<queries>` 是可选的
- 模板可以有多个

### 31.2 `<template>` 内部的推荐顺序

从官方 `utap` 的 XML reader 行为看，一个普通 timed automata template 的读取顺序大致是：

1. `<name>`
2. 可选 `<parameter>`
3. 可选 `<declaration>`
4. 零个或多个 `<location>`
5. 零个或多个 `<branchpoint>`
6. `<init>`
7. 零个或多个 `<transition>`

所以你在生成 XML 时，最好也按这个顺序输出。

一个更完整的 template 骨架可以写成：

```xml
<template>
  <name>T</name>
  <parameter>const int i, clock &amp;x</parameter>
  <declaration>clock y; int c;</declaration>

  <location id="id0">
    <name>Idle</name>
    <label kind="invariant">y &lt;= 5</label>
  </location>

  <location id="id1">
    <name>Busy</name>
    <urgent/>
  </location>

  <branchpoint id="idb0"/>

  <init ref="id0"/>

  <transition>
    <source ref="id0"/>
    <target ref="id1"/>
    <label kind="guard">y &gt;= 3</label>
    <label kind="synchronisation">go!</label>
    <label kind="assignment">y = 0, c = c + 1</label>
  </transition>
</template>
```

### 31.3 `<location>` 的关键字段

一个 location 最核心的语义字段是：

- `id` 属性
- 可选 `<name>`
- 可选 `<label kind="invariant">`
- 可选 `<label kind="exponentialrate">`
- 可选 `<urgent/>`
- 可选 `<committed/>`

对转换器来说，几条关键规则是：

- `id` 是 XML 层引用锚点，`init/source/target` 都通过它引用
- `<name>` 是模型中的位置名，query 中的 `P.Loc` 依赖它
- 如果没有 `<name>`，解析器通常会基于 `id` 派生一个内部名字
- `urgent` / `committed` 是独立子标签，不是某个通用属性

### 31.4 `<branchpoint>` 的具体形态

`branchpoint` 在 XML 里是独立元素：

```xml
<branchpoint id="idb0"/>
```

它不是某种特殊 kind 的 location。对转换器来说：

- branchpoint 必须有唯一 `id`
- 导出 XML 时应生成独立 `<branchpoint>` 节点
- 不要把 branchpoint 伪装成普通 `<location>`

### 31.5 `<transition>` 的标准骨架

一条 transition 的典型写法是：

```xml
<transition>
  <source ref="id0"/>
  <target ref="id1"/>
  <label kind="select">i : int[0,3]</label>
  <label kind="guard">x &gt;= 1 &amp;&amp; c == 0</label>
  <label kind="synchronisation">a[i]?</label>
  <label kind="assignment">x = 0, c = 1</label>
</transition>
```

其中：

- `<source>`、`<target>` 是必需的
- 其他 label 都是可选的

### 31.6 常见 `label kind` 一览

对标准 timed automata 模型，最关键的 `label kind` 是：

- `invariant`
- `exponentialrate`
- `select`
- `guard`
- `synchronisation`
- `assignment`
- `probability`

其中：

- `invariant` / `exponentialrate` 常出现在 location 内
- `select` / `guard` / `synchronisation` / `assignment` / `probability` 常出现在 transition 内

如果你的 DSL 当前只面向经典 symbolic timed automata，那么第一阶段至少应该完整支持：

- `invariant`
- `select`
- `guard`
- `synchronisation`
- `assignment`

### 31.7 `<system>` 本质上是一段文本块

`<system>` 不是复杂 XML 子树，而通常是一段文本，里面写：

- system 内声明
- instantiation
- `system ...;`

例如：

```xml
<system>
P1 = Worker(0);
P2 = Worker(1);
system P1, P2;
</system>
```

所以如果你的 DSL 已经把：

- system declarations
- instantiations
- process order

拆开建模，那么导出 XML 时需要把它们重新拼成一段合法的 `<system>` 文本。

### 31.8 `<queries>` 的结构

一个 query 的常见结构是：

```xml
<queries>
  <query>
    <formula>A[] not deadlock</formula>
    <comment>deadlock free</comment>
  </query>
</queries>
```

转换器角度至少要知道：

- `<formula>` 是 query 文本本体
- `<comment>` 是说明文字
- 可以有多个 `<query>`
- query 也可以单独落到 `.q` 文件

### 31.9 DOCTYPE / DTD 版本号

你会看到不同示例里有：

- `Flat System 1.1`
- `Flat System 1.5`
- `Flat System 1.6`

本机安装里的 `utap` XML writer 当前使用的是：

- `-//Uppaal Team//DTD Flat System 1.6//EN`
- `https://www.it.uu.se/research/group/darts/uppaal/flat-1_6.dtd`

而安装包自带 demo 里仍有很多 `1.5` 甚至更早的文件。这说明：

- DTD 版本号会随工具版本演化
- 但核心模型元素长期保持相对稳定
- 转换器应优先面向当前工具链可接受的现代 XML 写法

## 32. XML 中哪些部分是语义，哪些部分只是表示

在 NTA XML 里，既有语义字段，也有表示字段。

### 32.1 语义字段

典型语义字段包括：

- `<declaration>`
- `<template>`
- `<parameter>`
- `<location id="...">`
- `<label kind="invariant">...`
- `<urgent/>`
- `<committed/>`
- `<init ref="..."/>`
- `<transition>`
- `<source ref="..."/>`
- `<target ref="..."/>`
- `<label kind="select">...`
- `<label kind="guard">...`
- `<label kind="synchronisation">...`
- `<label kind="assignment">...`
- `<system>`
- `<queries>`

### 32.2 表示字段

而下面这些更偏视觉表示：

- location 的 `x` / `y`
- `<name>` 元素的坐标
- `<label>` 元素的坐标
- `<nail>`

这些字段会影响 GUI 怎么画，但不改变模型验证语义。

这也正是我们后面 DSL 要主动舍弃它们的原因。

### 32.3 纯模型 DSL 导出 XML 时怎么处理这些字段

如果 DSL 不保留视觉层，而目标格式是 XML，那么导出时有两种常见策略：

- 自动生成一组占位坐标
- 或只把 XML 当交换格式，不追求 GUI 里“好看”

从 `utap` 的 XML writer 可以看到，即使没有真实布局数据，它也会自动填一组坐标。因此：

- 这些坐标在工程上常见
- 但不应反向污染你的 DSL 设计

## 33. 如果不用 XML，只看纯模型，最接近的是哪种官方格式

如果你不想看 GUI 和布局，只想看“纯模型语义”，那么官方现成格式里最接近的是：

- `.xta`

原因是：

- 它是文本化的
- 它围绕 declarations、process、state、trans、system 展开
- 它比 XML 更少视觉噪声

但本文后面仍然要单独设计 DSL，而不是直接把 `.xta` 当最终答案，原因是：

- 我们希望文档里能把模型结构讲得更显式
- 我们也希望把 query 组织得更清晰
- 我们希望 DSL 设计目标是“语义清晰的容器层”，而不仅仅是“官方文本格式原样照抄”

### 33.1 XTA 文本骨架

根据 `utap` 的 pretty-printer，现代 XTA 风格大致可以写成：

```text
clock x;

process P()
{
  state
    Idle {x <= 5},
    Done;

  init Idle;

  trans
    Idle -> Done {
      guard x >= 3;
      assign x = 0;
    };
}

system P;
```

如果模型更复杂，还会看到：

- `branchpoint B;`
- `urgent L1, L2;`
- `commit C1, C2;`
- `select i:int[0,3];`
- `sync a[i]?;`
- `assign x = 0, c = 1;`

### 33.2 XTA 的优点与缺点

优点：

- 更适合纯文本生成
- 更接近模型语义
- 没有 XML 的坐标噪声

缺点：

- GUI 主工作流更偏 XML
- 与官方示例和 GUI 的直接互通通常不如 XML 稳

### 33.3 对转换器的实际建议

如果你要做“我们的 DSL -> 标准 UPPAAL”，工程上最稳的路线通常是：

1. DSL AST
2. 降到统一中间模型
3. 主输出目标选择 NTA XML
4. 按需要从同一中间模型再导出 XTA

这样更容易：

- 与 GUI 对接
- 保持完整性
- 避免在多个官方格式之间来回转造成信息不一致

## 34. 面向纯模型语义的 DSL 设计目标

这里的目标不是去复刻 UPPAAL GUI 的 XML 工程文件，而是设计一套 **纯模型语义 DSL**。也就是说：

- 不关心坐标
- 不关心 label 的视觉摆放
- 不关心 nail、颜色、注释框位置
- 只关心会影响验证语义的模型元素

因此本文中的 DSL 目标是：

- 能无损表达用于验证的 UPPAAL 模型
- 尽量与 UPPAAL 模型结构 1:1 对应
- 不重新发明一套新的 timed automata 语义
- 不把视觉层元数据混入核心模型

## 35. DSL 应覆盖哪些模型元素

从“满足验证即可”的目标出发，DSL 至少应覆盖：

- 全局声明
- 模板参数
- 模板局部声明
- location
- invariant
- urgent / committed
- branchpoint
- edge
- select / guard / sync / update / weight
- init
- instantiation
- system line
- channel priority
- process priority
- queries

其中：

- `queries` 不属于系统动态语义本体
- 但它们是验证工作流的重要输入

所以 DSL 最好把 query 作为与 model 并列的顶层块保留下来。

## 36. DSL 的几个核心设计原则

### 36.1 结构层与表达式层分离

最稳妥的做法不是重新定义一套新的表达式语言，而是：

- DSL 自己定义模型结构
- declarations / invariant / guard / sync / update / query formula 直接嵌入原生 UPPAAL 文本

这样做的好处是：

- 与官方语法最一致
- 语义风险最小
- 后续可以直接调用 `utap` 做解析和类型检查

### 36.2 纯模型语义，不保留 layout

既然目标不是 XML round-trip，那么 DSL 里应明确排除：

- 坐标
- nail
- label 坐标
- 颜色
- 视觉注释

这样 DSL 会更干净，也更接近真正的验证模型。

### 36.3 template、instantiation、system 三层分离

不要把它们揉成一个概念：

- `template`
  - 自动机定义
- `instantiation`
  - 参数绑定后的模板别名
- `system`
  - 实际并行系统的进程集合和顺序

这三层在 UPPAAL 中语义不同，DSL 也应分开。

### 36.4 location 仍然需要稳定标识

即使不保留 XML 的视觉层，DSL 里 location 也必须有稳定标识，因为：

- edge 要引用它
- init 要引用它
- 查询里常常也会通过进程名和位置名引用它

因此 DSL 最适合做法是：

- 每个 location 都有一个模型级名字
- 这个名字直接作为 UPPAAL 中可引用的位置名

## 37. DSL 的抽象模型

可以把 DSL 的抽象 AST 设计为：

```text
Model
├── global_decls : RawDeclBlock
├── templates : Template[]
├── system_decls : RawDeclBlock?
├── instantiations : Instantiation[]
├── system : SystemLine
├── chan_priority : RawText?
├── queries : Query[]

Template
├── name : ID
├── parameters : RawParameter[]
├── local_decls : RawDeclBlock?
├── locations : Location[]
├── branchpoints : Branchpoint[]
├── init : ID
└── edges : Edge[]

Location
├── name : ID
├── invariant : RawExpr?
├── exp_rate : RawExpr?
├── urgent : bool
└── committed : bool

Branchpoint
└── name : ID

Edge
├── source : ID
├── target : ID
├── select : RawExpr?
├── guard : RawExpr?
├── sync : RawExpr?
├── update : RawExpr?
└── weight : RawExpr?
```

这里最关键的决定是：

- 结构是 DSL 自己的
- 表达式内容仍然是原生 UPPAAL 文本

## 38. 一套建议语法

下面给出一份偏工程实现的语法草案。

```text
model          ::= 'model' ID '{' model_item* '}'
model_item     ::= global_block
                 | template
                 | system_decl_block
                 | instantiation
                 | chan_priority
                 | system_line
                 | queries_block

global_block   ::= 'global' raw_block
system_decl_block ::= 'system_decls' raw_block

template       ::= 'template' ID '(' param_list? ')' '{'
                     template_item*
                   '}'
template_item  ::= local_block
                 | location
                 | branchpoint
                 | init_decl
                 | edge

param_list     ::= raw_text (',' raw_text)*
local_block    ::= 'local' raw_block

location       ::= 'location' ID '{'
                     ('invariant' raw_expr ';')?
                     ('exp_rate' raw_expr ';')?
                     ('urgent' ';')?
                     ('committed' ';')?
                   '}'

branchpoint    ::= 'branchpoint' ID ';'
init_decl      ::= 'init' ID ';'

edge           ::= 'edge' ID '->' ID '{'
                     ('select' raw_expr ';')?
                     ('guard' raw_expr ';')?
                     ('sync' raw_expr ';')?
                     ('update' raw_expr ';')?
                     ('weight' raw_expr ';')?
                   '}'

instantiation  ::= 'instantiate' inst_head '=' ID '(' raw_arg_list? ')' ';'
inst_head      ::= ID | ID '(' param_list? ')'
raw_arg_list   ::= raw_expr (',' raw_expr)*

chan_priority  ::= 'chan_priority' raw_text ';'
system_line    ::= 'system' process_group ('<' process_group)* ';'
process_group  ::= process_ref (',' process_ref)*
process_ref    ::= ID | ID '(' raw_arg_list? ')'

queries_block  ::= 'queries' '{' query* '}'
query          ::= 'query' raw_expr ('comment' string)? ';'

raw_block      ::= '<<<' RAW_TEXT '>>>'
raw_expr       ::= '`' RAW_TEXT '`' | '<<<' RAW_TEXT '>>>'
raw_text       ::= same as payload
```

## 39. 为什么这种 DSL 最适合 UPPAAL

因为 UPPAAL 的真正难点不在“有 location 和 edge”这件事，而在：

- 表达式语法复杂
- 不同位置的表达式有不同类型限制
- symbolic / SMC 的支持边界不同
- 模板实例化与 system line 的语义并不平凡

如果 DSL 还想自己重新设计一套表达式语言，就会产生两层风险：

- 语法不一致
- 语义不一致

而采用“结构化容器 + 原生表达式文本槽位”的方式，可以把风险降到最低。

## 40. DSL 与 UPPAAL 模型元素的对应关系

| DSL 元素 | UPPAAL 对应物 | 说明 |
| --- | --- | --- |
| `global <<<...>>>` | 全局 declarations | 原样保存声明文本 |
| `template T(...)` | template / process template | 自动机定义 |
| `local <<<...>>>` | 模板局部声明 | 原样保存 |
| `location L` | location | 模型级位置 |
| `invariant ...` | invariant label | 位置不变式 |
| `urgent;` | urgent location | 禁止时间流逝 |
| `committed;` | committed location | 禁止时间流逝并限制下一步 |
| `branchpoint B;` | branchpoint | 概率/分流节点 |
| `init L;` | initial location | 初始位置 |
| `edge A -> B` | edge / transition | 边主体 |
| `select ...` | select label | 非确定绑定 |
| `guard ...` | guard label | 启用条件 |
| `sync ...` | synchronisation label | 同步动作 |
| `update ...` | assignment label | 顺序更新 |
| `weight ...` | branch weight | 概率权重 |
| `instantiate ...` | instantiation | 模板参数绑定 |
| `system ...;` | system line | 系统进程与顺序 |
| `chan_priority ...;` | channel priority | 优先级定义 |
| `query ...;` | query | 验证性质 |

## 41. 一个简单示例

```text
model Mutex {
  global <<<
bool busy = false;
>>>

  template Worker() {
    location Idle {}
    location Wait {}
    location CS {}

    init Idle;

    edge Idle -> Wait {
    }

    edge Wait -> CS {
      guard `not busy`;
      update `busy = true`;
    }

    edge CS -> Idle {
      update `busy = false`;
    }
  }

  instantiate P = Worker();
  instantiate Q = Worker();

  system P, Q;

  queries {
    query `A[] not (P.CS and Q.CS)` comment "mutual exclusion";
    query `A[] not deadlock` comment "deadlock free";
  }
}
```

这个示例体现了几件事：

- 模型结构是显式的
- query 与 model 并列存放
- 没有任何视觉层信息
- 用于验证已经足够

## 42. 设计边界与取舍

### 38.1 为什么不保留 layout

因为你要的是“纯模型，满足验证即可”。在这个目标下：

- layout 不影响 symbolic verification 语义
- layout 会增加 DSL 噪声
- layout 会把 DSL 拉向 XML round-trip，而不是模型表达

因此去掉 layout 是合理且必要的收敛。

### 38.2 是否需要支持 queries

严格说，query 不属于系统动态语义本体。但如果 DSL 的目标是“可直接用于验证”，那么 query 非常值得保留，因为：

- 它们是验证任务的一部分
- 它们与模型一起演化更自然

### 38.3 是否需要支持 progress / gantt

如果目标是“满足经典验证模型表达”，它们不是必须的：

- `progress`
  - 更偏验证算法配置
- `gantt`
  - 更偏可视化

因此 DSL 核心版可以不纳入它们，后续若有需要再做扩展块。

### 38.4 是否还需要 branchpoint / weight

如果只服务于最经典的 symbolic query，它们的重要性较低；但若希望 DSL 尽量完整覆盖 UPPAAL 模型家族，仍建议保留：

- `branchpoint`
- `weight`

因为它们是语义级模型元素，而不是视觉层元素。

## 43. 实现建议

如果要真正把这套 DSL 做成工具链，我建议按三层实现：

1. 容器语法层
   - 解析 `model/template/location/edge/system/query` 这些结构
2. 原生文本槽位层
   - declarations / expressions / formula 先按 raw text 保存
3. 语义检查层
   - 调用 `utap` 或兼容解析器对 raw text 做解析、类型检查和导出

这样有几个好处：

- 最接近官方语义
- 不容易和 UPPAAL 表达式语法漂移
- DSL 的职责清晰

## 44. 总结

如果把全文压缩成一句话，那么可以这样理解：

- **UPPAAL 的核心是“并行扩展时间自动机网络 + 明确的时间/同步/更新语义”**
- **性质语言只是作用在这个状态空间上的问题集合**
- **DSL 最适合做的是准确表达模型结构，并把表达式部分直接保持为原生 UPPAAL 文本**

对于你要的目标，“不管视觉层，只保留纯模型、满足验证即可”，最合适的 DSL 就应当：

- 放弃 XML 布局 round-trip
- 保留模型结构 1:1
- 保留 query
- 不重写表达式语义

## 45. 参考资料

- UPPAAL System Description  
  https://docs.uppaal.org/language-reference/system-description/
- UPPAAL Declarations / Types / Parameters / Scope Rules  
  https://docs.uppaal.org/language-reference/system-description/declarations/  
  https://docs.uppaal.org/language-reference/system-description/declarations/types/  
  https://docs.uppaal.org/language-reference/system-description/parameters/  
  https://docs.uppaal.org/language-reference/system-description/scope-rules/
- UPPAAL Templates / Locations / Edges / Priorities / Semantics  
  https://docs.uppaal.org/language-reference/system-description/templates/  
  https://docs.uppaal.org/language-reference/system-description/templates/locations/  
  https://docs.uppaal.org/language-reference/system-description/templates/edges/  
  https://docs.uppaal.org/language-reference/system-description/priorities/  
  https://docs.uppaal.org/language-reference/system-description/semantics/
- UPPAAL Symbolic Query Syntax / Semantics  
  https://docs.uppaal.org/language-reference/query-syntax/symbolic_queries/  
  https://docs.uppaal.org/language-reference/query-semantics/symb_queries/
- UPPAAL Expressions  
  https://docs.uppaal.org/language-reference/expressions/
- UTAP Parser Source  
  https://github.com/UPPAALModelChecker/utap
