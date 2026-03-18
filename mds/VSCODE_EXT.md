# VSCode 扩展与 FCSTM Node.js 语义层设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-18 | 初始版本，定义 VSCode 可视化方案、Node.js 原生语义层定位与分阶段实施计划 | Codex |

---

## 1. 文档目标

本文讨论的不是一个孤立的“VSCode 里把 FCSTM 画出来”的小功能，而是一条更长的技术路线：

1. 先在 Node.js 上建立 **FCSTM 原生语义层**
2. 在此基础上实现 **FCSTM -> PlantUML** 的原生生成能力
3. 再把这一能力接入 VSCode，形成可预览、可配置、可扩展的可视化系统

这里的核心判断是：

- **FCSTM 语义层值得被单独视为一个 project**
- 它的用途绝不只限于 to PlantUML
- 从长期演进看，**优先做 Node.js 原生移植** 明显优于通过外部 CLI 调用 Python

---

## 2. 为什么不能把这件事简单理解为“调一下 PlantUML”

### 2.1 PlantUML 只负责渲染，不负责理解 FCSTM

PlantUML 能做的是：

- 接收 `.puml`
- 渲染成 `png`、`svg`、`pdf`

PlantUML 不能做的是：

- 解析 `.fcstm`
- 建立 FCSTM 的状态机模型
- 理解事件作用域、层次状态、aspect actions、forced transitions、guard/effect 等语义

所以“FCSTM 可视化”至少天然包含两个阶段：

1. **FCSTM -> 语义模型**
2. **语义模型 -> PlantUML**

之后才是：

3. **PlantUML -> 图像或预览**

第三步只是渲染后端问题，前两步才是能力核心。

### 2.2 当前仓库里，VSCode 扩展只有语法层能力，没有语义层能力

目前 VSCode 扩展已经具备：

- 语法高亮
- 基于 ANTLR JS 解析器的语法诊断
- outline/document symbols
- completion
- hover

但这些能力本质上还是停留在：

- token
- parse tree
- 轻量级文档结构提取

它还没有：

- 完整的 FCSTM 语义模型
- 从 parse tree 到状态机模型的 Node.js 语义构建流程
- Node.js 原生的 `to_plantuml()`
- Node.js 原生的语义验证、跳转解析、路径解析、事件归一化

因此，如果现在直接讨论“VSCode 里怎么 preview”，容易把真正的大头工作误判成“接个插件”。

---

## 3. 核心技术判断

### 3.1 Node.js 原生语义层应优先于调用 Python CLI

我倾向于明确把下面这条路线作为正式方向：

- **正式方向**：Node.js 原生语义层
- **不推荐作为正式架构**：VSCode 扩展内通过命令行调用 `pyfcstm`

原因如下。

#### 3.1.1 性能与交互模型

VSCode 场景是高频、增量、交互式的：

- 用户正在输入
- 文档经常处于未保存状态
- 设置项可能频繁切换
- 预览需要去抖刷新

如果每次都调用外部 CLI：

- 进程启动有固定开销
- Python 环境定位有额外不确定性
- 未保存 buffer 需要走临时文件中转
- 错误回传和调试体验会更差
- Windows/macOS/Linux 的环境差异会被放大

而 Node.js 原生方案可以直接读取当前编辑器内存文本，避免额外进程编排。

#### 3.1.2 产品边界更干净

当前扩展本身的定位是：

- 轻量
- 离线可用
- 运行时不依赖 Python

如果在最核心的新能力上重新引入 Python CLI，产品边界会变得不清晰：

- 安装说明复杂化
- 故障定位复杂化
- 平台兼容矩阵膨胀
- 用户会把扩展质量和本机 Python 环境耦合在一起

#### 3.1.3 可复用性远大于可视化

一旦有了 Node.js 原生语义层，可直接支撑的功能不止是 PlantUML：

- richer diagnostics
- semantic validation
- rename / go to definition / find references
- code actions
- formatter
- folding by semantic structure
- dead transition / unreachable state analysis
- event scope inspection
- simulation assistant
- quick fixes
- model export to other targets
- future language server

所以这不是为可视化单独修一条临时通道，而是在补整个 VSCode 生态的真正基础设施。

### 3.2 FCSTM 语义层值得单独立项

我认为这部分非常值得单独当一个子项目来规划。推荐的命名方式可以类似：

- `fcstm-js-semantics`
- `fcstm-node-core`
- `@pyfcstm/fcstm-core`

它的定位不是“VSCode 专用”，而是：

- 由 VSCode 首先驱动需求
- 但本身是可独立复用的 Node.js 核心库

推荐目标：

- 输入：FCSTM 源码文本
- 输出：语法树、语义模型、诊断信息、导出结果
- 运行环境：Node.js
- 不依赖 Python 运行时

---

## 4. FCSTM Node.js 语义层的职责边界

建议把 Node.js 侧能力分成四层。

### 4.1 第 1 层：语法层

职责：

- ANTLR lexer/parser
- parse tree 构建
- syntax diagnostics

当前扩展已经有这部分基础。

### 4.2 第 2 层：AST 层

职责：

- 将 parse tree 归一化为更稳定的 AST
- 消除 ANTLR 生成结构带来的不便
- 建立统一的 source range 与节点映射

这一层的价值在于：

- 让上层逻辑不直接依赖 ANTLR 细节
- 便于未来 grammar 演进时降低连锁修改
- 便于做测试和序列化

### 4.3 第 3 层：语义模型层

这是最关键的一层，建议与 Python 的 model 层对齐，但不是机械照搬。

职责包括：

- 状态、事件、转换、变量、操作、生命周期动作的语义建模
- 层次状态结构建立
- 名称解析与路径解析
- `ref` 引用解析
- `::` / `:` / `/` 事件作用域归一化
- initial transition / exit transition 规则化
- pseudo state / composite state / leaf state 分类
- forced transitions 展开
- guard / effect / lifecycle action 语义挂接
- 语义级错误与告警

这一层的产物应该是一个稳定的、可遍历、可导出的状态机语义对象图。

### 4.4 第 4 层：派生能力层

依赖语义模型层实现：

- `to_plantuml`
- semantic diagnostics
- symbol resolution
- code navigation
- simulation support
- export to other IR / formats

PlantUML 只是这一层中的一个输出器。

---

## 5. 为什么语义层是“项目级工作”

### 5.1 FCSTM 不是简单 DSL 文本替换问题

FCSTM 涉及的核心语义远超过“把几行代码映射成几行字符串”：

- hierarchical states
- pseudo states
- composite state initial/exit rules
- lifecycle actions
- aspect actions
- event scoping
- forced transition expansion
- name/display name/path formatting
- expression 分类与约束
- transition guard/effect 绑定

这些都要求先建立正确的语义模型，再谈输出。

### 5.2 VSCode 后续能力几乎都会复用这套语义

如果没有语义层，很多编辑器能力只能停留在非常脆弱的启发式：

- hover 只能写静态文案
- completion 难以做上下文语义补全
- diagnostics 只能做语法错误
- symbol 导航很难做到语义准确
- preview 也只能依赖外部工具黑盒输出

一旦有了语义层，这些都可以统一建立在同一份模型之上。

### 5.3 语义层还能反向提升 Python 端的一致性

如果 Node.js 语义层建设得足够干净，长期甚至可以倒逼仓库把“语义规则”和“输出规则”进一步显式化：

- 哪些是 grammar 规则
- 哪些是 AST 归一化规则
- 哪些是 model 语义规则
- 哪些是 PlantUML 表达规则

这对 Python 与 Node.js 双实现保持一致非常有价值。

---

## 6. VSCode 可视化的正式方案

## 6.1 总体目标

在 `.fcstm` 文档中提供以下体验：

- 可以直接预览状态机图
- 可以通过 Settings 配置 PlantUML 可视化参数
- 可以在未安装 PlantUML 扩展时仍然工作
- 优先保持离线、本地、稳定

## 6.2 渲染链路拆分

推荐将可视化链路明确拆分为三段：

1. `FCSTM source -> semantic model`
2. `semantic model -> PlantUML source`
3. `PlantUML source -> rendered preview`

其中：

- 第 1 段和第 2 段由我们自己负责
- 第 3 段可以复用现有 PlantUML 生态，也可以自己做 fallback

## 6.3 后端策略

推荐定义如下后端策略：

- `auto`
- `plantuml-extension`
- `local-java`

### 6.3.1 `plantuml-extension`

优先复用 `jebbs.plantuml` 扩展。

方式建议为：

1. 生成临时 `.puml`
2. 以 PlantUML 文档方式打开
3. 调用该扩展提供的 `plantuml.preview` 命令

理由：

- 它已经具备成熟的预览 UI
- 支持缩放、滚动、多页等能力
- 减少我们第一版自建预览 UI 的工作量

注意：

- 不建议做 `extensionDependencies` 硬依赖
- 应做运行时软集成
- 若插件不存在，不能影响扩展主功能

### 6.3.2 `local-java`

当 `jebbs.plantuml` 不存在或用户显式选择本地后端时，fallback 到：

```bash
java -jar <plantuml.jar>
```

建议默认通过 `-pipe` 工作：

- 扩展生成 `.puml` 文本
- 将文本送入 stdin
- 获取 `svg` 或 `png`
- 在我们自己的 webview 中展示

推荐优先 `svg`：

- 文本更清晰
- 缩放体验更好
- 错误提示也更容易处理

### 6.3.3 为什么不考虑 `plantumlcli`

这里不再把 `plantumlcli` 纳入正式方案，原因是：

- 额外引入 Python 依赖
- 和当前扩展定位冲突
- 相比 `java -jar plantuml.jar` 没有明显体系优势

---

## 7. VSCode 设置模型设计

建议直接使用 VSCode 原生 Settings UI，不单独做一个自定义设置页面。

理由：

- 用户已熟悉 VSCode 设置系统
- 搜索、工作区覆盖、用户级覆盖都天然具备
- 维护成本远低于自建配置界面

## 7.1 设置分层

建议把设置分成三组。

### 7.1.1 运行后端与环境

- `fcstm.visualization.backend`
- `fcstm.visualization.javaPath`
- `fcstm.visualization.plantumlJarPath`
- `fcstm.visualization.renderFormat`
- `fcstm.visualization.autoRefresh`
- `fcstm.visualization.refreshDebounceMs`

### 7.1.2 常用可视化选项

- `fcstm.visualization.detailLevel`
- `fcstm.visualization.maxDepth`
- `fcstm.visualization.showEvents`
- `fcstm.visualization.showLifecycleActions`
- `fcstm.visualization.transitionEffectMode`

### 7.1.3 高级选项

这部分应尽量与 `PlantUMLOptions` 对齐：

- `showVariableDefinitions`
- `variableDisplayMode`
- `variableLegendPosition`
- `stateNameFormat`
- `showPseudoStateStyle`
- `collapseEmptyStates`
- `showEnterActions`
- `showDuringActions`
- `showExitActions`
- `showAspectActions`
- `showAbstractActions`
- `showConcreteActions`
- `abstractActionMarker`
- `maxActionLines`
- `showTransitionGuards`
- `showTransitionEffects`
- `showEvents`
- `eventNameFormat`
- `eventVisualizationMode`
- `eventLegendPosition`
- `collapsedStateMarker`
- `useSkinparam`
- `useStereotypes`
- `customColors`

## 7.2 选项元数据需要先统一

在做 VSCode 设置映射前，必须先统一一份 **可视化选项元数据**。

原因：

- Python model 层已有完整定义
- CLI 层的类型表目前不是完全同步的
- 文档里也可能已经存在局部漂移

因此建议新增一个统一的 options schema 作为事实源，至少包含：

- key
- type
- allowed values
- default
- inheritance rule
- description
- VSCode settings title/description

这份 schema 可用于：

- Python CLI 参数解析
- VSCode settings 生成
- 文档生成
- 测试校验

---

## 8. FCSTM 语义层对 VSCode 的具体价值

下面列出语义层一旦建好，VSCode 里可以自然获得的能力。

## 8.1 可视化

- 当前文档直接预览
- 未保存内容实时预览
- 悬停查看状态/事件的语义信息
- 可视化定位回源代码

## 8.2 语义诊断

例如：

- 无效 `ref`
- 重复定义
- 事件作用域冲突
- 找不到目标状态
- 非法 forced transition 展开
- 无法到达的状态
- 无法触发的 transition

## 8.3 导航与重构

- go to definition
- find references
- rename state / event / action
- path completion

## 8.4 编辑器辅助

- 更准确的 completion
- semantic folding
- semantic document outline
- context-aware code actions

## 8.5 分析与模拟辅助

- 静态 reachability 提示
- transition graph inspection
- event dependency inspection
- 面向 simulate 的 editor assistant

---

## 9. 推荐的代码组织方式

建议不要把语义层直接塞成 VSCode 扩展里的几个 util 文件，而是做出清晰边界。

推荐结构：

```text
editors/vscode/
  src/
    extension.ts
    visualization/
      commands.ts
      preview/
      backends/
    integration/
      plantumlExtension.ts
  packages/
    fcstm-core/
      syntax/
      ast/
      semantics/
      diagnostics/
      exporters/
        plantuml/
```

也可以不做 workspace package，但逻辑边界应保持一致。

核心要求：

- 语义核心不依赖 VSCode API
- VSCode 只依赖语义核心
- PlantUML exporter 依赖语义核心
- preview/backend 层依赖 exporter，但不反向侵入语义核心

这样后面如果想做：

- CLI for Node.js
- web playground
- language server
- testing toolkit

都会更顺。

---

## 10. 分阶段实施计划

## Phase A: 语义基础设施立项

目标：

- 把 Node.js 原生语义层正式确认为独立工程方向

任务：

- 梳理 Python 现有 DSL/AST/model/export 结构
- 定义 Node.js 侧分层边界
- 定义 AST 与语义模型初稿
- 明确 Python / Node.js 行为一致性测试策略

产出：

- 语义层设计文档
- 模型草图
- 测试样例目录

## Phase B: AST 与语义模型

目标：

- 从 parse tree 到 AST
- 从 AST 到语义模型

任务：

- 建立 source range 映射
- 实现 state / event / transition / operation 基础节点
- 建立路径解析和命名空间机制
- 建立 forced transition 展开逻辑
- 建立生命周期动作语义挂接

产出：

- 可序列化 AST
- 可遍历语义模型
- 基础语义诊断

## Phase C: PlantUML exporter

目标：

- 在 Node.js 侧实现 `semantic model -> PlantUML`

任务：

- 对齐 `PlantUMLOptions`
- 实现 detail level 继承规则
- 实现 state / event / transition 文本格式化
- 复现变量、legend、颜色、max depth 等规则

产出：

- `toPlantUml()` API
- 与 Python 结果对比测试

## Phase D: VSCode preview integration

目标：

- 在 VSCode 中提供可用预览

任务：

- 注册 preview/open/export 命令
- 实现 settings 映射
- 实现 `jebbs.plantuml` 软集成
- 实现 `java -jar plantuml.jar` fallback
- 实现自动刷新与错误展示

产出：

- 用户可见预览能力
- 工作区级设置
- 状态栏/命令面板入口

## Phase E: 语义能力扩展

目标：

- 把语义层价值扩展到可视化之外

任务：

- semantic diagnostics
- navigation
- references / rename
- code actions
- more analyzers

产出：

- 从“语言支持扩展”升级为“语义编辑器扩展”

---

## 11. MVP 建议

如果要尽快落一个第一版，建议 MVP 范围如下：

1. 先不做完整 language server
2. 先做 Node.js 原生 `FCSTM -> PlantUML`
3. VSCode 先提供一个 `Preview FCSTM Diagram` 命令
4. 优先支持最常用的 `PlantUMLOptions`
5. 优先复用 `jebbs.plantuml`
6. 缺失时 fallback 到本地 `java -jar <plantuml.jar>`

MVP 不建议做的内容：

- Python CLI 作为正式主链路
- 自定义设置 webview
- 过早引入远程服务渲染
- 在语义层没稳之前做大规模编辑器重构功能

---

## 12. 风险与注意事项

## 12.1 最大成本不在渲染，而在语义移植

真正复杂的部分不是：

- 怎么弹出一个 webview
- 怎么调 `plantuml.preview`
- 怎么执行 `java -jar`

真正复杂的是：

- 如何在 Node.js 上准确复现 FCSTM 语义
- 如何保证与 Python 现有行为尽量一致
- 如何避免 grammar、AST、model、export 规则在双端漂移

## 12.2 一致性测试必须从一开始就准备

建议用同一批 `.fcstm` 样例，双端比较：

- 语义模型摘要
- diagnostics
- PlantUML 输出

不要等到实现快完成时才想起做一致性校验。

## 12.3 设置项不要直接人工复制

可视化设置很多，如果纯手工在：

- Python model
- CLI
- VSCode `package.json`
- 文档

之间复制，后面极易漂移。应尽早建立统一 schema。

---

## 13. 最终建议

基于当前仓库状态，推荐的正式结论如下：

- 把 **FCSTM Node.js 原生语义层** 作为一个独立项目来做
- 把 **VSCode 可视化** 作为语义层落地的第一批高价值场景
- **优先 Node.js 原生移植**，不要把 Python CLI 当作正式方案主链路
- 渲染后端采用：
  - 优先 `jebbs.plantuml`
  - fallback 到本地 `java -jar plantuml.jar`
- 设置项基于 VSCode 原生 settings，不另做自定义配置页
- 先统一可视化 options schema，再做设置映射

简而言之：

**可视化不是一个独立小功能，而是 FCSTM 语义基础设施建设的第一个大用例。**

