# Force Transition 设计分析

## 1. 背景

这份文档分析仓库中 `force transition` 应该如何建模，重点讨论两种设计：

1. 在 model 构建阶段把 `force transition` 展开成普通 transition。
2. 在 model 中保留原始 `force transition`，只在 `transitions_from` 之类的属性上做展开封装。

这里讨论的不是抽象层面的“哪种更优雅”，而是：

> 对 pyfcstm 这个仓库来说，哪种边界划分更稳，哪种后续维护成本更低。

先给结论：

- 对当前仓库，继续采用“构建期展开”为默认设计更合适。
- 如果未来确实需要源码保真、编辑器重构、或者追踪“这条边来自哪条 force 规则”，更好的方向也不是“只在 `transitions_from` 里做封装”，而是混合设计：
  - 保留规范化后的可执行 model；
  - 另外保存 source-level metadata 或原始 AST。


## 2. 这个仓库里的 `force transition` 到底是什么

在 DSL / AST 层，`force transition` 是一个独立语法节点：

- `pyfcstm.dsl.node.ForceTransitionDefinition`
- 会被放进 `StateDefinition.force_transitions`

但到了 model 层，当前实现并不会保留一个独立的 `ForceTransition` 运行时对象。构建 model 时，它会被递归展开成普通 `Transition`。

而且当前文档口径本身已经把它定义成：

- 语法糖；
- 在 model construction 阶段展开；
- 所有展开出来的 transition 共享同一个 event object；
- 不允许 effect block；
- 展开后按照普通 transition 执行。

也就是说，从仓库现在的公开语义看，`force transition` 更像一个 DSL 前端特性，而不是 runtime / model 层的一等公民。


## 3. 当前实现的分层边界

### 3.1 AST 层保留 force 语法

DSL parser 保留了 source-level 结构：

- 普通 transition 进入 `StateDefinition.transitions`
- force transition 进入 `StateDefinition.force_transitions`

这很合理，因为 AST 还处在贴近 DSL 源码的层次。

### 3.2 Model 层会把 force 归一化掉

在 `parse_dsl_node_to_state_machine(...)` 中，model builder 会做这些事情：

- 校验 force transition 的源状态和目标状态是否合法；
- 解析并复用 / 创建 event object；
- 解析 guard expression；
- 把 force transition 展开成普通 `Transition`；
- 把它递归传播到子层级，在合适位置变成 exit transition。

完成后，model 里真正存在的是：

- `StateMachine`
- `State`
- `Transition`
- `Event`
- `Operation`

而没有单独的 `ForceTransition` 类型。

### 3.3 导出行为是“规范化导出”，不是“源码回写”

`model.to_ast_node()` 会从规范化后的 model 重建 AST。由于 model 里只剩普通 transition，因此导出的 AST 也只会有普通 transition。

这意味着：

- 解析包含 `!` 的 DSL；
- 构建 model；
- 再把 model 导回 AST / DSL 文本；

并不会保留原始的 force 语法。

得到的是一个“语义等价但更展开”的 DSL 形式。

这个点很关键：当前仓库的行为已经更接近“编译器前端 + 规范化 IR”，而不是 formatter、CST-preserving editor，或者 source-to-source 转换器。

### 3.4 现有仓库表面 API 已经默认 transition 是规范化后的图

这点很容易被低估。

当前仓库并不是只暴露了一个 transition 访问口。它同时存在并使用了多种 transition 视图：

- `state.transitions`
- `state.transitions_from`
- `state.transitions_to`
- 直接遍历 `parent.transitions`

而这些访问口被不同子系统用于不同目的：

- runtime 选边；
- CLI 列事件；
- shell completion；
- 模板渲染；
- 测试里直接断言 transition 数量、顺序和导出的 DSL 文本。

所以如果要在 model 中保留 force transition，就必须回答一个更大的问题：

- 是把这些 API 全部一起重定义；
- 还是新增一套并行的 “effective transition” API，并让所有消费者迁移过去。

这显然不是一个只改某个 property 的小调整。

### 3.5 现有测试已经把“规范化 model”当成契约了

当前测试并没有把规范化导出当成偶然行为，而是直接验证它。

典型断言包括：

- force 展开后的 transition 出现在 `state.transitions` 里；
- 相关 event 会被补到正确的 scope 中；
- `model.to_ast_node()` 返回的是规范化 DSL，而不是原始 force 语法；
- 展开后的 transition 顺序是稳定的，甚至可以用下标直接断言。

所以从兼容性角度看，“model 是规范化后的 transition 图”已经是这个仓库事实上的 model contract。


## 4. 为什么这个问题不能只盯着一个 property

直觉上，保留 force transition 看起来很自然，因为它保留了用户原本写下来的意图。

但真正的问题不是“保不保留一个字段”，而是：

> model 层到底要扮演 source-preserving semantic model，还是 executable / renderable intermediate representation？

对这个仓库来说，这个区别非常重要，因为 model 会被：

- simulation runtime 消费；
- PlantUML 渲染消费；
- code generation 模板消费；
- CLI / completer 消费；
- 各种测试直接消费。

所以这不是一个局部问题，而是整个 model 层职责边界的问题。


## 5. 方案 A：在 model 构建阶段展开

这就是当前方案。

### 5.1 核心想法

把 source-level 语法糖：

```fcstm
state System {
    ! * -> ErrorHandler :: FatalError;

    state Running {
        state Processing;
        state Waiting;
    }
    state Idle;
    state ErrorHandler;
}
```

直接变成一个只包含有效 transition 的语义图，效果大致相当于：

```fcstm
state System {
    Running -> ErrorHandler :: FatalError;
    Idle -> ErrorHandler :: FatalError;
    ErrorHandler -> ErrorHandler :: FatalError;

    state Running {
        Processing -> [*] : /FatalError;
        Waiting -> [*] : /FatalError;
    }
}
```

之后 runtime、render、generate 都只面对这些普通 transition。

### 5.2 优点

#### 优点 1：可执行边只有一种概念

runtime 只需要理解一件事：`Transition`。

它不需要到处写特殊分支，例如：

- 如果是 force transition 就先展开；
- 如果是 force transition 就覆盖普通 transition；
- 如果是 force transition 就在运行时动态扫描后代。

这让执行语义明显更单纯。

#### 优点 2：model 分层边界干净

整个分层会变得很清楚：

- AST 层负责 source syntax
- model 层负责 executable semantic graph

这个边界在工程上很稳，也很容易向别人解释。

#### 优点 3：下游消费者都更简单

很多消费者看的不只是 `transitions_from`，而是直接看 transition 图本身。

比如：

- runtime 选边；
- CLI 列可触发事件；
- auto-completion；
- 模板里遍历 `state.transitions` 或 `state.transitions_from`；
- 测试里直接断言 transition 数量和顺序。

如果 model 里只保留普通 transition，那么这些消费者面对的是同一张已经展开好的图，不需要各自重复理解 force 语义。

#### 优点 4：对渲染和代码生成天然友好

PlantUML 和模板渲染真正需要的，本来就是“有效图”，不是“作者写过什么语法糖”。

对 code generation 来说，force transition 本身通常没有目标语言里的独立意义。目标代码真正需要的是：

- 实际有哪些边；
- 这些边带什么 event / guard；
- 这些边如何参与执行。

所以规范化很自然。

#### 优点 5：不变量更容易描述

当 model 已经规范化之后，很多不变量都非常直接：

- 每一条可执行边都是 `Transition`
- `state.transitions` 就是这个 scope 下真正有效的 transition
- `transitions_from` 只是从规范化图里导出的一个视图

这对写测试、写模板、写文档都更省心。

#### 优点 6：它符合当前仓库已经形成的契约

这不只是“架构上更优雅”，也是更低风险的做法。

因为当前仓库已经：

- 在文档里把 force 定义成语法糖；
- 在 `model.to_ast_node()` 中导出规范化后的 DSL；
- 在测试里依赖展开后的结果。

继续保持这个方向，可以避免文档、测试、API 语义三方重新收敛的成本。

### 5.3 缺点

#### 缺点 1：源码层意图会丢失

一旦进入 model，很多 source-level 信息就没了，例如：

- 这条 transition 是用户显式写的，还是从 force 规则展开出来的；
- 多条展开后的 transition 是不是来自同一条 force 规则；
- 原始 force 规则具体长什么样。

#### 缺点 2：`to_ast_node()` 变成“规范化导出”，不是“原样回写”

如果有人期望：

- 解析源码；
- 再导回源码；

得到的结构还能和原文接近，那么当前设计满足不了这种期待。

它输出的是语义归一化后的 DSL，而不是 source round-trip。

#### 缺点 3：transition 数量会膨胀

force transition 会递归展开。在层级较深、节点较多的模型里，这会显著增加 transition 数量。

这通常不是致命问题，但它确实带来成本：

- model 体积变大；
- 调试时看到的边更多；
- 某些图形输出会更拥挤。

#### 缺点 4：force 的“特殊性”被类型系统抹平了

展开之后，force 的特殊性只会以：

- 顺序；
- 或 metadata；

这种方式间接保留下来，而不会通过类型直接体现。

现在的实现实际上会把展开出的 force transition 放在普通 transition 之前，这会影响选择顺序。这个行为可能正是想要的，但如果不写清楚，就容易让人误以为它只是“纯语法糖，不影响优先级”。

这不是拒绝规范化的理由，但确实需要把优先级语义写明白。


## 6. 方案 B：在 model 中保留 force transition

这个方案的意思是：model 中也显式保留 force 级别的概念，例如：

- `State.force_transitions`
- 甚至同时保留 `State.transitions`
- 再在需要时动态导出 effective transitions

### 6.1 核心想法

在 model 里仍然保留：

```fcstm
state System {
    ! * -> ErrorHandler :: FatalError;
}
```

只在以下时刻再做展开：

- runtime 查询当前可走的边；
- visualization 需要画图；
- code generation 需要真实 transition 图。

### 6.2 优点

#### 优点 1：更保留用户原始意图

model 可以回答：

- 用户原始写了什么；
- 哪些 transition 是隐式展开出来的；
- 哪几条展开边来自同一个 force 规则。

这对解释器、诊断信息、重构工具、编辑器功能都很有价值。

#### 优点 2：可追踪性更好

如果运行时或分析工具能够报告：

- “这条 transition 来自 force 规则 X”

那么对用户理解模型会更友好。

#### 优点 3：可以支持多种导出模式

比如未来可以同时支持：

- 规范化导出；
- source-preserving 导出。

如果仓库往 IDE / refactor / formatter 方向扩展，这会更有吸引力。

### 6.3 缺点

#### 缺点 1：model 不再是一张单一语义图

此时 model 里会混杂：

- 显式普通 transition；
- force transition；
- 也许还有某种动态导出的 effective transition。

这会让 model 的职责边界明显更复杂。

#### 缺点 2：只在 `transitions_from` 里做封装是不够的

这是最关键的一点。

如果你在 model 中保留 force transition，但只在 `transitions_from` 里展开，那么很多别的访问口都会变得不一致。

例如：

- `state.transitions`
- `parent.transitions`
- `transitions_to`
- PlantUML 画边时的遍历
- CLI 收集事件
- code generation 模板
- 测试中对 `state.transitions` 的直接断言

它们仍然会看到“未展开图”，除非你让每个地方都再理解一次 force 语义，或者统一迁移到新的 effective API。

复杂度并没有消失，只是被搬家了。

#### 缺点 3：多种视图之间容易漂移

一旦存在多种 transition 视图，就很容易出现这种 bug：

- runtime 看到的是展开后的图；
- renderer 看到的是原始图；
- completer 只看到显式事件；
- 测试依赖某种视图，但用户看到的是另一种视图。

这种“不一致的部分真相”通常比单纯选择任一方案都更危险。

#### 缺点 4：所有消费者都得知道自己要哪种 transition

每个 transition 消费者都要回答：

- 我要 source transition 还是 effective transition？
- 这里要不要展开 force？
- 要不要 deduplicate？
- event object 的共享身份要不要维持？

对一个以 simulate / render / generate 为主的仓库来说，这种复杂度通常不值得。

#### 缺点 5：如果认真做，往往会引出更大的 API 重构

如果仓库真的决定在 model 中保留 force transition，那么一个靠谱的设计通常至少会需要三套概念：

- declared normal transitions
- declared force transitions
- effective transitions

也就是说，真正的 source-preserving 设计一般不会停留在“多存一个字段”。它往往会演化成显式的多视图 API。

这不是不能做，但它已经是一个实打实的架构改动了。


## 7. 为什么“只在 `transitions_from` 里展开”通常是错误抽象

这一点单独拿出来说，因为它最容易让人觉得是“两全其美”，但实际上往往是最别扭的折中。

### 7.1 它只解决了一个 accessor

假设 model 保存的是：

- `state.transitions = 只有显式普通 transition`
- `state.force_transitions = 原始 force 规则`

然后 `state.transitions_from` 动态展开它们。

那么 `state.transitions` 到底表示什么？

可能的答案只有三种：

1. 只表示显式普通 transition；
2. 表示显式普通 transition 加有效展开边；
3. 表示一种混合状态。

无论哪种都不舒服：

- 如果它只表示显式普通 transition，很多现有消费者会失真或变得不完整；
- 如果它表示有效展开边，那本质上你还是在规范化；
- 如果它表示混合态，model 会更难理解。

### 7.2 effective semantics 远不止“当前 state 的 outgoing”

force transition 影响的不只是“从当前 state 出发的边”。

它还影响：

- incoming relationship；
- 事件可见性；
- 图形边；
- 规范化 DSL 导出；
- transition 顺序和优先级；
- 针对整张 transition 图的分析。

所以把它绑定在一个“当前 state 的 from view”上，抽象范围太窄了。

### 7.3 它会制造隐藏语义

如果 `state.transitions` 和 `state.transitions_from` 看到的是两张不同的世界，那么 model 对 API 使用者来说会变得很“惊喜”。

一个正常使用者会自然地以为：

- `transitions_from` 只是 `transition graph` 的一个过滤视图；
- 而不是一套在背后偷偷补图的新语义。

一旦这个直觉被打破，model 的可理解性就会明显下降。


## 8. 具体例子

### 8.1 例子 A：runtime 执行

源码：

```fcstm
state Root {
    ! * -> Error :: Panic;

    state A;
    state B;
    state Error;
    [*] -> A;
}
```

如果 model 是规范化后的，那么 runtime 看到的是：

- `A -> Error :: Panic`
- `B -> Error :: Panic`
- `Error -> Error :: Panic`

这很简单，transition selection 只需要按顺序遍历普通 transition 即可。

如果 model 保留 force，只在 `transitions_from` 里做展开，那么 runtime 也许还能工作，但前提是所有 runtime 路径都必须严格经过这个 accessor。一旦某个辅助逻辑直接读取 `parent.transitions`，行为就可能开始分叉。

### 8.2 例子 B：层级传播

源码：

```fcstm
state System {
    ! * -> Error :: Fatal;

    state Active {
        state Processing;
        state Waiting;
        [*] -> Processing;
    }
    state Idle;
    state Error;
    [*] -> Active;
}
```

它的有效语义不只是：

- `Active -> Error :: Fatal`
- `Idle -> Error :: Fatal`

还包括在 `Active` 里面自动补出来的：

- `Processing -> [*] : /Fatal`
- `Waiting -> [*] : /Fatal`

这样叶子状态才能先退出到父状态，再让父状态级别的 `Active -> Error` 接上执行。

这不是一个“小 property 技巧”，而是一个递归图变换。这也是为什么它很自然地适合放在 model construction 阶段做。

### 8.3 例子 C：模板渲染

模板作者可能会写：

```jinja
{% for transition in state.transitions %}
  {{ transition.from_state }} -> {{ transition.to_state }}
{% endfor %}
```

也可能写：

```jinja
{% for transition in state.transitions_from %}
  {{ transition.from_state }} -> {{ transition.to_state }}
{% endfor %}
```

如果 force 逻辑只藏在 `transitions_from` 里，那么这两段模板遍历出来的其实可能是两张不同的图。

对于一个拿来当模板上下文的 model 来说，这不是一个好的 API 体验。

### 8.4 例子 D：源码保真工具

假设未来有这样的命令：

- “把所有 force transition rewrite 成显式普通 transition”
- 或者 “解释这条 runtime edge 来自源码哪一行”
- 或者 IDE 里折叠 / 编辑 force transition 声明

那么保留 source-level force 信息当然就很有价值。

但即便在这种场景里，也不代表 executable model 就应该停止规范化。更合理的做法仍然是：

- 可执行图保持规范化；
- 另外保存 source provenance。


## 9. 仓库定位为什么决定了答案

这个仓库当前的主要定位是：

- DSL parser；
- semantic state-machine model builder；
- simulator；
- PlantUML renderer；
- template-based code generator。

它更像一条编译器式流水线：

1. 解析 DSL；
2. 构建 semantic model；
3. 再 simulate / render / generate。

这种定位天然更偏向“规范化 model 层”。

如果仓库的主要身份变成：

- language server；
- formatter；
- structural editor；
- source-to-source refactoring tool；

那么在 model 中保留 force transition 就会显得更有吸引力。

但这不是这个仓库当前最主要的身份。


## 10. 对这个仓库的建议

### 10.1 总体建议

继续保留当前默认架构：

- DSL AST 层保留 `ForceTransitionDefinition`
- model 层把 force 展开成普通 `Transition`
- runtime / render / generate 全都只面对规范化后的 transition 图

这和仓库当前的用途最匹配。

### 10.2 不建议做的事情

不建议改成这种形式：

- model 中保留 force transition；
- 但展开逻辑只藏在 `transitions_from` 这种 property 里。

这种做法通常会同时拿到两种设计的复杂度，却拿不到任何一边的清晰边界。

### 10.3 更好的增强方向：混合设计

如果你希望提升“可追踪性”而不破坏当前 model 的清晰度，更好的方向是 hybrid。

可能的做法有：

#### 方案 A：给展开后的 transition 挂 source metadata

例如每条展开后的 `Transition` 都额外挂：

- `expanded_from_force = True`
- `origin_force_path`
- `origin_force_index`
- `origin_force_ast`

这样 executable graph 仍然是规范化的，但 provenance 还在。

#### 方案 B：把原始 AST 挂在 `StateMachine` 上

例如：

- `StateMachine.source_ast`
- 或者一张 side-table，把 model object 映射回 AST node

这样可以支持 source-preserving 工具，而不会污染 executable model。

#### 方案 C：显式区分规范化导出和源码导出

如果未来真的需要两套导出契约，不建议用一个模糊的 `to_ast_node()` 同时承担两种含义。

更清楚的方式是：

- `to_ast_node()` 继续表示规范化导出；
- 另加 `to_source_ast_node()` 之类的方法表示源码保真导出。

这样“导出”到底表示“用户原文”还是“语义执行图”就不会混淆。


## 11. 什么时候该选哪种设计

### 11.1 适合在 model 构建阶段展开的场景

当以下条件成立时，优先选“构建期展开”：

- 主要消费者是 runtime、renderer、generator、analyzer；
- 你想维护一张单一、规范化的 transition graph；
- 你更重视语义清晰和维护成本，而不是源码保真；
- 你希望模板作者和测试代码直接看到有效行为。

这正是当前仓库的情况。

### 11.2 适合在 model 中保留 force 的场景

当以下条件成立时，保留 source-level force 才更有意义：

- 主要消费者是 IDE、编辑器、重构工具；
- 你需要 round-trip 尽量贴近用户原始 DSL；
- 你需要把诊断信息精确绑定到原始语法；
- 你需要把 force 规则作为“一等 authored object”展示和编辑。

这并不是当前仓库的主定位。

### 11.3 适合混合设计的场景

当以下条件同时存在时，hybrid 往往是最佳解：

- runtime / render / generate 仍然需要规范化图；
- 但诊断、解释、IDE 功能又需要 provenance。

如果未来仓库往 tooling 方向增强，这大概率会是最稳妥的升级路径。


## 12. 额外需要明确的一点：优先级语义

还有一个细节最好明确写进文档。

当前实现中，展开出来的 force transition 会先于同层普通 transition 进入相关列表，因此它们通常会更早参与按顺序的 transition selection。

这个行为可能正是想要的，但它应该被当成“明确语义”，而不是“碰巧如此”。

所以无论最终选哪种表示方式，都最好把这个问题说清楚：

- force transition 只是普通 transition 的语法糖吗？
- 还是它本身也意味着比普通 transition 更强的选择优先级？

如果答案是“有更高优先级”，那就应该把这一点文档化，并且直接加测试覆盖。

如果答案是“没有，只是语法糖”，那就应该重新审视当前展开顺序，确保运行时行为真的和这个说法一致。


## 13. 如果未来真的要在 model 中保留 force，建议长什么样

如果未来版本真的决定把 source preservation 引入 model 层，那么更干净的方式不是把逻辑藏进 `transitions_from`，而是显式做多视图 API。

### 13.1 建议采用显式多视图命名

例如：

- `state.declared_transitions`
- `state.declared_force_transitions`
- `state.effective_transitions`
- `state.effective_transitions_from`
- `state.effective_transitions_to`

这样 authored syntax 和 executable semantics 的区别是显式的，不会靠猜。

### 13.2 下游消费者仍然应该默认走 effective view

即便 source-preserving 数据存在，runtime、renderer、generator，以及绝大多数模板仍然应该默认消费 effective graph。

这样 operational semantics 不会被 source-level 结构反向污染。

### 13.3 导出 API 也应该显式区分

如果同时支持源码导出和规范化导出，它们不应该共用一个含糊的方法名。

更好的做法是：

- `to_source_ast_node()`
- `to_normalized_ast_node()`

或者等价命名。

这样就不会出现“这个 export 到底是用户写的，还是 model 执行的”这种歧义。


## 14. 最终结论

对 pyfcstm 这个仓库来说，把 `force transition` 在 model 构建阶段展开成普通 `Transition`，仍然是更合理的架构选择。

原因很直接：

- 仓库核心目标是执行、渲染、生成，而不是源码保真；
- model 层现在已经天然扮演规范化 semantic IR；
- 很多消费者会直接读取 transition 图本身，所以不能把 force 语义只藏在一个 property 里；
- 单一、规范化的 transition graph 更容易测试、解释、渲染，也更适合给模板作者使用。

如果未来确实需要更强的源码保真能力，最好的升级方式也不是让 executable model 重新背上 source-level 语法糖，而是：

- 继续保留规范化后的 executable graph；
- 另外保留 provenance metadata 或原始 AST。

这样才能同时拿到：

- 清晰稳定的执行模型；
- 以及面向工具链扩展的可追踪性。
