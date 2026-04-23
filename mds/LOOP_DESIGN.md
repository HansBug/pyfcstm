# operation block 中 loop 语句可行性评估文档

关联背景：

- `if block` 已在 `pyfcstm` 中完成从语法到 parser、model、simulate、solver、render 的全链路支持
- 相关设计文档见 `mds/IF_DESIGN.md`

本文性质说明：

- 本文是 **feasibility discussion**，目标是把 loop 相关问题摊平、讲透、留档
- 本文 **不代表** 项目已经决定实现 loop
- 本文 **不代表** 已经确认排期、开始编码或冻结具体方案
- 是否实现、何时实现、先实现哪一种 loop 形式，当前都 **未定**

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-18 | 初始版本，讨论 operation block 中 `for` / `while` / 有界循环的可行性、风险与建议方向 | Codex |

---

## 1. 背景

`pyfcstm` 当前已经支持：

- 线性赋值语句
- block-local temporary variable
- operation block 中的 `if / else if / else / nested if`

这意味着 operation block 已经不再是“纯赋值列表”，而是一个 **递归 statement tree**。

从结构上看，这为未来扩展更多 statement 留出了空间，例如：

- `while`
- `for`
- `repeat`
- `assert`
- `let`

但这里必须强调一个关键区别：

- `if` 的本质是 **有限分支选择**
- loop 的本质是 **可能多次迭代，甚至可能不终止**

因此，虽然“在 grammar 里多加一个 statement type”这件事本身不难，但 loop 带来的问题远不止语法层。  
如果说 `if` 是把 operation block 从“赋值列表”升级为“有限递归语句树”，那么 loop 则是在此基础上继续引入：

- 回边
- 迭代语义
- 终止性问题
- 不动点或展开问题
- definite assignment / visibility 在多轮执行下的重新定义

这也是本文的出发点：

- 不急着改代码
- 先明确 loop 到底会影响哪些层
- 再判断“值得不值得做”“适合先做哪一种”“怎样做才不把现有语义体系搞乱”

---

## 2. 文档目标

本文目标不是直接给出一个 ready-to-implement 的 loop 方案，而是完成以下工作：

1. 说明为什么 loop 与 `if block` 不是同一难度等级
2. 从语法、语义、model、simulate、solver、render、文档与编辑器支持等角度做完整评估
3. 区分几类不同 loop 形式的风险
4. 给出“哪些方向值得继续讨论，哪些方向当前不建议动”的结论
5. 给未来可能的实现准备讨论基线

---

## 3. 非目标

本文当前 **不** 追求以下内容：

- 不冻结正式 DSL 语法
- 不承诺开始实现
- 不给出精确开发排期
- 不在本文中直接修改 parser / runtime / solver
- 不讨论所有可能控制流语句，只聚焦 loop 系列

---

## 4. 先给结论

先把结论写在前面，避免后文展开后失焦。

### 4.1 总体判断

如果目标是把 loop 当成 operation block 的通用 statement：

- **语法层面**：可行
- **AST / model 承载层面**：可行
- **render / 导出 / 编辑器支持层面**：可行，主要是工作量问题
- **运行时模拟层面**：可行，但必须引入 operation-level 的终止保护与更复杂作用域规则
- **solver / Z3 化层面**：通用 `while` / C-style `for` 风险很高，当前不建议直接做

### 4.2 推荐排序

若未来真的要做，建议优先级如下：

1. **受限有界循环**，例如 `repeat [N] { ... }`
2. **可静态展开的 range 型 for**
3. **通用 while**
4. **C-style for(init; cond; step)**

这不是按“用户熟悉程度”排序，而是按“与当前架构兼容程度”排序。

### 4.3 当前建议

当前更合理的结论是：

- **不建议直接启动通用 `while` / `for` 的实现**
- 若未来要继续推进，应先设计 **有界、可展开、可证明终止** 的 loop 子集
- 若用户诉求本质是“跨多个周期反复做事直到条件成立”，优先考虑 **状态机建模**，而不是把循环塞进 operation block

---

## 5. 为什么 loop 和 if 不是一个量级

`if block` 之所以能比较自然地落在现有架构里，核心原因是它仍然满足下面这个性质：

- 整个 statement tree 虽然递归，但 **没有回边**
- 每次进入 operation block，执行步数是 **有限且结构上有上界** 的

这使得以下几层都能成立：

- parser 可以递归构树
- model 可以做单遍或有限递归的可见性分析
- runtime 可以做递归解释执行
- solver 可以把 branch 结果通过 `z3.If(...)` 合并，最终收敛为扁平状态更新函数

而 loop 一旦引入，就会破坏其中最关键的一条：

- operation block 不再天然保证“结构上有限步完成”

这会立刻带来几个本质变化：

1. **runtime 可能卡死**
   - 单次 `during` / `enter` / `effect` 执行不再保证返回

2. **static analysis 不再是简单作用域问题**
   - 变量是否“执行后一定存在”，会依赖迭代次数

3. **solver 不再只是有限条件合流**
   - 要么展开
   - 要么引入 invariant
   - 要么引入 fixpoint / recursive relation

4. **runtime 与 solver 的一致性更难保持**
   - runtime 通常要设上限
   - solver 则倾向无界建模
   - 两边很容易语义分叉

所以，从语言设计视角看：

- `if` 增加的是 **分叉**
- loop 增加的是 **回边**

分叉和回边不是一个量级的问题。

---

## 6. 候选 loop 形式盘点

在讨论“要不要支持 loop”之前，需要先把“loop”拆开。不同形式的复杂度差异很大。

### 6.1 `while [cond] { ... }`

优点：

- 语法直观
- 与当前 `if [cond]` 的 guard 风格一致
- parser 层扩展最自然

问题：

- 存在天然的不终止风险
- loop body 内变量作用域与 definite assignment 语义复杂
- solver 难度最高

### 6.2 C-style `for (init; cond; step) { ... }`

优点：

- 对很多用户熟悉
- 能把初始化、条件、步进放在一起

问题：

- 当前 DSL 并没有这类表达式级 statement 组合的传统
- `init` 和 `step` 应该允许哪些语句，需要重新定义
- loop variable 的生命周期和可见性会成为新问题
- parser 看似简单，语义层实际上比 `while` 更杂

### 6.3 `repeat [N] { ... }`

这里的 `N` 指非负整数上界，且建议要求它能够静态确定。

优点：

- 最接近“可安全展开”的控制结构
- runtime 易于执行
- solver 易于有限展开
- 终止性天然更强

问题：

- 表达能力弱于通用 `while`
- 若 `N` 允许依赖运行期变量，复杂度会立刻上升

### 6.4 `for i in range(...) { ... }`

优点：

- 比 `repeat [N]` 稍强
- 用户表达计数型循环更自然

问题：

- 当前 DSL 没有专门的 loop index / iterable 语义
- `i` 是全局变量、局部变量还是专用 loop variable，需要定义
- solver 若不能静态展开，难度很快接近通用 loop

### 6.5 collection-based `for item in items`

当前 DSL 没有数组、列表、集合、字典的正式数据模型。

结论：

- **当前阶段不应考虑**

---

## 7. 语法层评估

## 7.1 结构承载是足够的

当前 operation block 已经是 statement tree，因此 grammar 与 AST 从结构上具备承载更多 statement 的能力。

如果只从语法承载角度看，新增类似下面的规则并不难：

```antlr
while_statement
    : 'while' '[' cond_expression ']' operation_block
    ;

repeat_statement
    : 'repeat' '[' num_expression ']' operation_block
    ;

operational_statement
    : operation_assignment
    | if_statement
    | while_statement
    | repeat_statement
    | ';'
    ;
```

从 parser 工程角度说，这一步远不是主要风险。

## 7.2 `while [cond]` 比裸 `while cond` 更合适

若真的考虑 `while`，建议仍然复用：

- `if [cond_expression]`
- `while [cond_expression]`

原因与 `if block` 一致：

- 保持与 transition guard 风格一致
- 继续利用 `num_expression` 与 `cond_expression` 的分离
- ANTLR 冲突更少
- 用户更容易理解这是布尔条件

## 7.3 C-style `for` 的语法债务

表面上看：

```fcstm
for (i = 0; i < n; i = i + 1) {
    ...
}
```

似乎只是多加一个规则。

但一旦落地，至少要先回答：

- `init` 允许几个 statement
- `step` 允许几个 statement
- `init` 里新名字是循环外可见还是只在循环内可见
- `step` 是否允许再写 `if`
- `init` / `step` 用现有 `operation_assignment` 还是重新造子语法

因此：

- **语法不是最大问题**
- **语法形式一旦选错，后面语义与实现都会被拖复杂**

## 7.4 推荐的语法结论

若未来继续推进，语法层建议优先考虑：

- `repeat [N] { ... }`
- 其次 `while [cond] { ... }`

当前不建议优先讨论：

- C-style `for`
- collection-based `for`

---

## 8. 语义层评估

这是 loop 讨论中最关键的一层。

## 8.1 当前 operation block 的基本语义

当前 operation block 的语义可以概括为：

- 在单次 `enter` / `during` / `exit` / transition `effect` 中执行
- 顺序执行
- 局部临时变量允许存在，但 block 结束即消失
- 整个 block 必须在一次调用中完成

loop 一旦引入，首先要回答：

- operation block 是否仍然要求“单次调用内必须完成”

如果答案是“是”，那 loop 必须解决终止性问题。  
如果答案是“不是”，那 operation block 的语义就会与当前生命周期模型正面冲突。

因此这一点不能模糊：

- **无论未来做哪种 loop，单次 block 执行仍必须要求完成返回**

## 8.2 loop 在状态机 DSL 里的语义张力

状态机 DSL 天然擅长表达的是：

- 当前状态
- 当前周期动作
- 事件驱动迁移
- 多周期行为通过状态与迁移来表达

而 loop 更接近“在一个周期内重复做很多步”。

这会形成一个设计张力：

- 语义上应该跨周期表达的逻辑，如果被塞进 loop，就会把状态机层面的时间展开压扁到单个 cycle 内

例如，“持续加热直到温度达到阈值”在状态机里更自然的表达往往是：

- 处于 `Heating` 状态
- 每个周期做一次 `during`
- guard 满足后迁移

而不是：

```fcstm
during {
    while [temperature < target] {
        temperature = temperature + 1;
    }
}
```

后者虽然直观，但会改变“一个周期内做多少工作”的含义。

因此从 DSL 哲学上说：

- loop 不是天然非法
- 但它很容易把“应该建模成状态迁移的行为”错误压缩成“单周期内部脚本”

## 8.3 终止性必须成为一等公民

对 `if` 来说，终止性几乎不是问题。  
对 loop 来说，终止性必须被明确设计。

至少要回答：

- `while [true] { ... }` 是 parse 合法但运行时报错，还是 model 期就尝试拦截
- `while [x > 0] { y = y + 1; }` 如果 `x` 不变，视为用户错误还是正常但 runtime hit limit
- 浮点条件造成的非收敛如何处理
- 每个 operation block 是否有独立 loop-iteration 上限

如果这些问题不先说清楚，runtime 与 solver 都无法稳定设计。

## 8.4 `break` / `continue` 会成倍增加复杂度

如果未来还打算给 loop 配：

- `break`
- `continue`

那复杂度会进一步上升，因为：

- runtime 需要非局部控制流
- model 需要重新定义“后续语句是否可达”
- solver 需要编码提前退出路径

因此若未来真做 loop，V1 应强烈建议：

- **不支持 `break`**
- **不支持 `continue`**

---

## 9. 临时变量与作用域评估

这是 loop 相比 `if` 的第二个核心难点。

## 9.1 `if` 的作用域为什么相对简单

`if` 目前的规则可以概括为：

- 每个 branch 从同一外层可见集进入
- branch 内新临时变量不外泄
- 只有进入 branch 前已可见的名字，才参与回写 / merge

这是一个“单次分支合流”问题。

## 9.2 loop 不是单次合流，而是多轮迭代

看下面这个例子：

```fcstm
while [x > 0] {
    x = x - 1;
}
y = x;
```

这里：

- `y = x` 显然应该合法
- `x` 是 loop 前已可见变量，多轮更新后仍可见

但再看这个：

```fcstm
while [x > 0] {
    tmp = x;
    x = x - 1;
}
y = tmp;
```

这里立刻出现语义问题：

- 若 `x <= 0`，loop 0 次执行，`tmp` 从未定义
- 若 `x > 0`，`tmp` 会在至少一轮中定义

那 `y = tmp` 到底：

- 永远非法
- 仅当能证明 loop 至少执行一次时合法
- 还是要求用户先在 loop 外定义 `tmp`

这说明 loop 带来的不是简单的 branch-local rule，而是：

- definite assignment under iteration

## 9.3 推荐的保守规则

若未来真的做 loop，建议坚持一个非常保守的规则：

- **loop body 中首次引入的新名字，不向 loop 外泄漏**

这条规则与当前 `if` 风格是一致的，优点是：

- 简单
- 容易解释
- runtime 与 solver 更容易对齐

也就是说，下面这种写法建议非法：

```fcstm
while [x > 0] {
    tmp = x;
    x = x - 1;
}
y = tmp;   // 建议非法
```

而建议写成：

```fcstm
tmp = 0;
while [x > 0] {
    tmp = x;
    x = x - 1;
}
y = tmp;   // 合法
```

## 9.4 仍然不够，因为 loop 外已有临时变量会被多轮更新

即便采用保守规则，也还有问题：

```fcstm
tmp = 0;
while [x > 0] {
    tmp = tmp + x;
    x = x - 1;
}
y = tmp;
```

这里虽然 `tmp` 已在外层可见，但 loop 对它做的是：

- 0 次更新
- 1 次更新
- 多次更新

这在 runtime 中不难解释，但在 solver 中已经不再是简单 `z3.If(cond, a, b)` 能表达的有限分支。

---

## 10. model 层评估

## 10.1 数据结构扩展本身不难

如果只看 model 数据结构，新增类似下面的节点没有本质障碍：

```python
@dataclass
class WhileBlock(OperationStatement):
    condition: Expr
    statements: List[OperationStatement]


@dataclass
class RepeatBlock(OperationStatement):
    count: Expr
    statements: List[OperationStatement]
```

当前 `OperationStatement` 抽象已经存在，这一点与当初做 `IfBlock` 类似。

## 10.2 真正困难的是静态校验

当前 `_parse_operation_block()` 及其递归辅助函数的校验模式，本质上还是：

- 顺序可见性分析
- `if` 上做有限次作用域分叉

这套东西面对 loop 时会遇到几个新增问题：

1. 条件能否引用 loop body 中更新过的变量
2. loop body 内新变量是否允许在下一轮使用
3. loop 0 次执行时，哪些赋值应视为“不一定发生”
4. loop 结束后，哪些名字 guaranteed to exist

只要认真处理这些问题，model 层就不再是简单递归，而会朝 fixed-point style analysis 靠近。

## 10.3 `while` 的校验复杂度高于 `repeat [N]`

若是：

```fcstm
repeat [3] {
    x = x + 1;
}
```

model 可以把它理解成“结构上最多 3 次已知展开”，分析难度相对可控。

若是：

```fcstm
while [x > 0] {
    x = x - 1;
}
```

即使这个例子人类看得懂，静态分析也很难普遍判定：

- 是否一定终止
- 循环后哪些变量一定已经被定义

因此从 model 层看，最友好的方向仍然是：

- **可静态展开的 loop**

---

## 11. simulate / runtime 层评估

## 11.1 runtime 可以实现 loop，但不能裸放

runtime 层是所有部分里“最容易写出一个能跑版本”的。

例如 `while` 的伪代码可以很自然地写成：

```python
while bool(condition(**scope)):
    loop_scope = dict(scope)
    execute_statements(body, loop_scope)
    write_back_visible_names(scope, loop_scope)
```

但这里立刻会遇到两个问题：

- 没有终止保证
- `scope` 的每轮回写规则要重新精确定义

## 11.2 必须有 operation-level loop guard

若未来做 loop，runtime 层必须至少引入：

- 每个 loop 的最大迭代次数
- 每个 operation block 的最大 statement-step 次数

否则一次 DSL 执行就可能卡死 REPL / batch / CLI。

这类保护和当前 hot start / validation 中已有的防护思路是一致的，但影响面更大，因为它会进入常规 execution path。

## 11.3 引入上限后，语义就不再“纯”

一旦 runtime 规定：

- `while` 最多迭代 1000 次

就必须决定：

- 超过上限是抛错
- 记录 warning 后截断
- 还是视为 validation failure

而无论选哪种，都意味着 loop 的“最终语义”会部分依赖运行引擎的保护设置。

对于 `if`，几乎没有这个问题。  
对于 loop，这是 runtime 设计里绕不开的成本。

## 11.4 `during` 中的 loop 风险最大

loop 如果出现在：

- `enter`
- `exit`
- `effect`
- `during`

理论上都可以执行，但风险最大的其实是 `during`，因为它本来就是按 cycle 重复执行的。

如果再在 `during` 内放 loop，就容易形成“双层重复语义”：

- 外层：状态机周期
- 内层：单个周期中的脚本迭代

这会让 DSL 用户很难判断“这段逻辑应该是跨多个 cycle 展开，还是在一个 cycle 中跑完”。

---

## 12. solver / Z3 化评估

这是当前最强的阻塞点。

## 12.1 当前 solver 成立的关键前提

现在 operation block 的 symbolic execution 可以最终收敛成：

```text
(x', y', z', ...) = f(x, y, z, ...)
```

这里的关键是：

- statement tree 是有限的
- `if` 只是有限分支
- 可以用嵌套 `z3.If(...)` 表达

## 12.2 为什么通用 `while` 不自然适配当前 solver

对通用 `while` 来说，想做严肃的 Z3 化，通常只有几条路：

1. **bounded unrolling**
2. **loop invariant**
3. **fixpoint / recursive relation / CHC**

其中：

- 1 能做，但本质是受限近似
- 2 需要用户或系统提供 invariant，当前 DSL 完全没有这个设施
- 3 已经明显超出当前 solver 子系统的复杂度级别

因此如果目标是保持：

- runtime 与 solver 语义高度一致
- solver 输出仍然是可读、可控的状态更新关系

那通用 `while` 会非常吃力。

## 12.3 runtime 与 solver 容易分叉

最常见的分叉方式是：

- runtime 为了安全，设置最大迭代上限
- solver 若做无界建模，则可能得到另一套语义
- solver 若也做同样上限展开，则它分析的是“截断后的伪语义”

这两种都不理想。

相比之下，`if` 几乎天然没有这个分叉。

## 12.4 有界循环为什么相对可控

如果 loop 是：

```fcstm
repeat [3] {
    x = x + 1;
}
```

那么 solver 完全可以按 3 次展开。

如果 loop 是：

```fcstm
for i in range(0, 4) {
    x = x + i;
}
```

只要 range 上界静态确定，同样可以展开。

这里 solver 的工作流仍然接近当前模式：

- 把 statement tree 展开成有限顺序赋值树
- 最终仍收敛到扁平状态更新函数

因此：

- **bounded loop 是 solver 友好的**
- **unbounded loop 不是**

## 12.5 若坚持支持通用 while，需要新增的概念

若未来真的坚持支持通用 `while`，那么至少要补齐以下东西中的一部分：

- loop invariant 表示法
- 终止性 / ranking function 的思路
- solver 侧单独的 loop reasoning framework
- runtime 与 solver 对齐策略

这已经不是“在 if 的基础上再加一点”了，而是新主题。

---

## 13. render、导出、模板与编辑器支持评估

这部分反而是 loop 里相对不危险的一层。

## 13.1 statement tree 承载已经存在

render 层目前已经能按 operation statement 而不是纯 assignment 渲染，因此：

- DSL 导出
- 模板层 helper
- PlantUML 文本展示

都已经具备 statement-oriented 的承载能力。

## 13.2 这部分主要是工作量，不是架构阻塞点

如果未来新增 `WhileBlock` / `RepeatBlock`，外围需要做的是：

- `__str__()` 渲染
- AST round-trip
- Jinja2 helper 更新
- Pygments / VSCode keyword 支持
- 教程文档补充

这些工作不轻，但相对明确，不是核心风险源。

---

## 14. 几种方案的可行性分档

为了避免“loop”这个词过于笼统，这里给一个明确分档。

## 14.1 A 档：建议优先讨论

### `repeat [N] { ... }`

前提建议：

- `N` 为非负整数
- `N` 必须可静态确定，或至少可在 parse/model 阶段证明有小上界
- 不支持 `break`
- 不支持 `continue`

优点：

- 终止性最好
- runtime 最容易做
- solver 最容易有限展开
- 用户也容易理解

风险：

- 表达能力有限
- 若允许 `N` 依赖运行时变量，风险会上升

总体判断：

- **最值得优先讨论**

## 14.2 B 档：可讨论，但必须很受限

### `for i in range(a, b[, step]) { ... }`

前提建议：

- `a/b/step` 需要可静态求值
- 或者至少能证明总迭代次数上界很小
- loop variable 仅在 loop 内可见
- 不支持 `break`
- 不支持 `continue`

优点：

- 比 `repeat [N]` 表达能力更好
- 对计数型循环更自然

问题：

- 需要新定义 loop variable 语义
- solver 仍依赖可展开性

总体判断：

- **可以讨论，但设计成本明显高于 `repeat [N]`**

## 14.3 C 档：不建议作为第一步

### `while [cond] { ... }`

优点：

- 用户最熟悉
- 表达能力最强

问题：

- 终止性风险大
- static analysis 明显复杂
- solver 成本高
- runtime / solver 对齐困难

总体判断：

- **现在不建议直接启动**

## 14.4 D 档：当前不建议优先考虑

### C-style `for (init; cond; step) { ... }`

问题不止是不终止，还包括：

- 语法风格和当前 DSL 不够统一
- 初始化、步进、loop variable 生命周期都会新增歧义

总体判断：

- **现在不建议优先讨论**

## 14.5 E 档：当前不应进入范围

### collection-based `for item in items`

由于当前 DSL 没有集合类型与迭代模型：

- **不应纳入当前讨论范围**

---

## 15. 若未来真的做，建议坚持的语义原则

虽然本文不主张立刻实现，但如果以后继续推进，建议先把原则钉住。

## 15.1 原则一：operation block 仍必须一次执行完成

不能把 loop 设计成“可能悬挂到后续 cycle 再继续”。

否则：

- lifecycle action 语义会被破坏
- simulate 的执行模型会整体漂移

## 15.2 原则二：loop 内新引入名字不向外泄漏

保持与当前 `if block` 风格一致：

- 进入 loop 前不可见的名字
- 即使在 body 中被定义
- 也不应在 loop 外自动变成可见

## 15.3 原则三：V1 不支持 `break` / `continue`

先把 loop 本身语义站稳，不要一开始就引入额外控制流。

## 15.4 原则四：solver 必须有明确策略，不接受“以后再说”

loop 如果不能被 solver 合理解释，就很难说它真正进入了当前语言体系。

至少要在设计阶段明确：

- 是静态展开
- 是有界近似
- 还是 loop 在 solver 中暂不支持

不能出现 parser / runtime 已支持，solver 完全没定义的长期悬置状态。

## 15.5 原则五：优先鼓励状态机建模，而不是脚本化堆循环

若某类需求天然更适合：

- 多状态
- 多周期
- guard + transition

那应优先建议用户这么建模，而不是把 operation block 变成小脚本语言。

---

## 16. 若未来继续推进，建议的最小切入点

如果未来项目确实想试探性推进 loop，我建议最小切入点不是 `while`，而是：

```fcstm
repeat [N] {
    ...
}
```

并且明确限定：

1. `N` 必须是非负整数
2. `N` 必须在 model 阶段可静态求值
3. body 内仍然只支持当前 operation statement 子集
4. 不支持 `break`
5. 不支持 `continue`
6. loop 内新临时变量不向外泄漏
7. solver 按固定次数展开

这样做的好处是：

- 语言复杂度增加最少
- 风险可控
- 能验证 statement tree 对“有限迭代控制结构”的承载是否健康
- 即使后续决定不继续扩展到 `while`，这个能力本身也可能有独立价值

---

## 17. 如果以后真要做通用 while，需要先补哪些设计问题

这里只列问题，不给实现承诺。

### 17.1 终止保护

- 最大迭代次数是多少
- 配置项在何处暴露
- 超限如何报错

### 17.2 静态分析

- loop body 中新变量下一轮是否可见
- loop 外哪些变量 guaranteed to exist
- 0 次执行如何处理

### 17.3 runtime 与 solver 对齐

- solver 是做 bounded unrolling 还是别的
- runtime 的上限与 solver 的上限是否一致
- 若不一致，如何向用户解释

### 17.4 文档与用户教育

- 哪些需求更应该建模成 state / transition
- 哪些需求适合 loop
- 如何避免把 DSL 用成脚本语言

如果这些问题不先回答，直接开工大概率会出现“能 parse、能跑一部分，但语义边界越来越乱”的局面。

---

## 18. 推荐结论

基于当前仓库架构与设计目标，我的推荐结论如下：

1. 这次不要把“statement tree 已经支持扩展”误解成“loop 也已经接近可做”
2. `if` 的成功经验主要来自它仍然是有限控制流，这一点不应被忽略
3. 通用 `while` / C-style `for` 当前都不建议直接进入实现阶段
4. 若未来要继续，应先讨论 **有界、可展开** 的 loop 子集
5. `repeat [N] { ... }` 是最有希望与当前架构兼容的第一步
6. 在没有明确 solver 策略前，不建议对 loop 做 parser-first 的半成品支持
7. 对许多“持续做直到条件满足”的需求，仍应优先推荐状态机化建模，而非 operation block 内循环

---

## 19. 当前状态声明

为了避免误解，这里再明确一次当前状态：

- 本文仅为 **可行性评估与设计讨论**
- 当前 **没有** 承诺开始实现 loop
- 当前 **没有** 承诺实现 `while`
- 当前 **没有** 承诺实现 `for`
- 当前 **没有** 承诺实现 `repeat`
- 当前 **没有** 确认排期

更准确地说：

- 现在只是把“值不值得做、做哪种、风险在哪”先讨论清楚
- 至于什么时候开始做，当前 **不好说**

---

## 20. 后续可选动作

若后续要继续这条线，建议动作顺序如下：

1. 先决定是否真的需要 loop，而不是默认“语法上能加就值得加”
2. 若答案是需要，再先比较 `repeat [N]` 与 `while [cond]`
3. 若选择 `repeat [N]`，先补一份更窄、更可落地的设计文档
4. 在开始写 parser 代码前，先把 runtime / solver 策略写清楚
5. 若未来发现大多数诉求其实可通过状态机建模解决，则应考虑不做 loop

---

## 21. 一句话总结

`if block` 的扩展证明了 operation block 适合承载 **有限递归控制流**；  
它并没有自动证明 operation block 已经适合承载 **通用循环语义**。  
对 `loop`，当前更合理的状态是：**先讨论清楚，再决定做不做；即使要做，也应先从有界循环而不是通用 `while` 开始。**
