# FCSTM VSCode 扩展与纯 JS Language Server 设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-18 | 初始版本，聚焦 VSCode 可视化方案与 Node.js 原生语义层路线 | Codex |
| 0.2.0 | 2026-04-06 | 基于当前仓库状态重构文档，补充现状快照、构建链路、纯 JS runtime 约束、完整 language server 路线与 phased execution plan | Codex |

---

## 1. 文档定位

本文档在 `0.1.0` 版本基础上做两个关键修正。

第一，基于当前仓库真实状态更新判断。今天的 `editors/vscode/` 已经不是一个只有语法高亮的静态语言包，而是一个具备 ANTLR JS 解析、诊断、符号、补全、悬停、import-aware 轻量工作区能力和 import path definition 的 parser-backed 扩展。

第二，正式把目标从“先做可视化”提升为“构造一个完整的、纯 JS 的 FCSTM language server”，并把可视化明确降级为该 language server 语义能力的一个下游能力，而不是架构中心。

这里的“纯 JS”需要定义清楚：

- 运行时只依赖 VSCode 扩展宿主自带的 Node.js 环境和可 bundle 的 npm JavaScript 依赖
- 不依赖 Python CLI
- 不依赖 Java / PlantUML jar
- 不依赖其他 VSCode 扩展作为核心功能前提
- 不依赖远程服务或网络渲染

考虑到当前仓库的 VSCode 扩展已经采用 `TypeScript + esbuild + CommonJS + ES2015 target` 的工程基线，源码层继续使用 TypeScript 是与现有 repo 最兼容、成本最低的做法。最终交付物仍然是纯 JavaScript bundle，因此不与“纯 JS runtime”目标冲突。

---

## 2. 当前仓库状态快照（截至 2026-04-06）

### 2.1 当前扩展已经具备的能力

当前 `editors/vscode/` 已经具备以下能力：

- TextMate 语法高亮
- language configuration
- snippets
- 基于 ANTLR JavaScript parser 的 syntax diagnostics
- document symbols / outline
- completion
- hover
- import-aware diagnostics
- import-aware completion / hover
- import path go to definition

也就是说，当前扩展已经跨过“静态语法包”的阶段，进入了“轻量 parser-backed editor support”的阶段。

### 2.2 当前扩展的实现与构建事实

当前工程里与 VSCode 扩展相关的关键事实如下：

| 维度 | 当前状态 |
|------|----------|
| Manifest | `editors/vscode/package.json`，扩展名 `fcstm-language-support`，`engines.vscode` 为 `^1.60.0` |
| 入口 | `main` 指向 `./dist/extension.js` |
| 源码语言 | TypeScript |
| Bundle 方式 | `esbuild`，当前单入口 `src/extension.ts -> dist/extension.js` |
| Bundle 标准 | `platform: node`、`format: cjs`、`target: es2015`、`external: ['vscode']` |
| Parser 来源 | 从仓库 canonical grammar 生成的 ANTLR JavaScript artifacts |
| Parser 版本约束 | `antlr4` 固定为 `4.9.3` |
| 本地构建总入口 | repo root 的 `make vscode` |
| 扩展目录构建入口 | `editors/vscode/Makefile` |
| 打包方式 | `@vscode/vsce`，输出 `.vsix` 到 `editors/vscode/build/` |
| 现有验证 | `verify-p0.2` 到 `verify-p0.6`、`verify-import-editor-support`、`test-e2e` |

### 2.3 当前构建链路

当前构建链路不是抽象设想，而是已经存在并在仓库里落地的流程：

1. repo root 执行 `make vscode`
2. root `Makefile` 调用 `$(MAKE) -C editors/vscode package`
3. `editors/vscode/Makefile` 的 `package` 依赖 `all`
4. `all` 当前依次执行：
   - `icons`
   - `install`
   - `syntaxes`
   - `parser`
   - `build`
5. `build` 使用 `node esbuild.config.js --production`
6. `package` 使用 `npm run package` 产出 `.vsix`

当前 parser 生成仍然依赖 ANTLR jar，这属于开发期构建依赖，不属于扩展运行时依赖。已打包好的 VSIX 在用户机器上运行时并不依赖 Java 或 Python。

### 2.4 当前架构的边界与问题

当前实现虽然已经有不少 editor features，但它们仍然主要堆叠在扩展宿主侧的 provider 和 utility 上：

- 语法解析与语义建模尚未分层
- 多文件 import-aware 能力是轻量工作区 helper，不是完整 workspace semantic graph
- diagnostics / completion / hover / definition 还不是通过标准 LSP server 提供
- 语义规则还没有形成独立、可复用、可测试的 Node.js core
- 可视化如果继续往外接 PlantUML，会把真正的核心问题掩盖掉

这说明继续沿着“在 `extension.ts` 周边追加 provider”的方式扩展，边际收益会越来越低。

---

## 3. 为什么当前阶段应该正式转向完整 language server

### 3.1 当前 repo 的 DSL 已经是多文件、带 import、带语义规则的语言

当前仓库的 FCSTM DSL 已经不是只有单文件状态定义的早期形态。它已经包含：

- hierarchical states
- pseudo states
- lifecycle actions
- aspect actions
- event scoping
- forced transitions
- import 语法与映射
- import-aware 的多文件模型装配

这类语言如果继续只用“编辑器端若干轻量 helper”支撑，会越来越难维护。

### 3.2 当前扩展已经出现向 language tooling 演进的自然信号

当前扩展已经有：

- parser-backed diagnostics
- parser-backed symbols
- parser-backed completion
- parser-backed hover
- import-aware workspace resolution
- import path definition

这些能力本身已经在逼近 language server 的职责边界。再往前做 references、rename、code actions、semantic diagnostics、workspace symbols、folding、semantic tokens，就不应该继续靠离散 provider 拼出来。

### 3.3 可视化不是目标本身，而是语义能力的派生产物

如果把重心放在“如何在 VSCode 里把图画出来”，很容易误判真正的工作量。

真正难的是：

- 建立稳定 AST
- 建立完整语义模型
- 做多文件 workspace graph
- 做名称解析、作用域解析、引用解析
- 保证与 Python 端核心语义一致

一旦这些成立：

- preview 只是语义模型的一个 consumer
- references / rename / code actions 是同一套语义模型的 consumer
- semantic diagnostics 也是同一套语义模型的 consumer

因此，这里应该把“完整 language server”作为主目标，把“可视化”降为其中一个高价值交付面。

---

## 4. 新的正式技术结论

### 4.1 主目标

正式方向应调整为：

- 构建 **纯 JS runtime 的 FCSTM language server**
- 让 VSCode 扩展变成一个 **client + bundled server** 的标准结构
- 所有核心 editor intelligence 能力都建立在 Node.js 语义核心之上
- 可视化走 **纯 JS renderer / webview** 路线，不依赖 PlantUML 作为主链路

### 4.2 不推荐再作为正式主架构的方案

以下方案不应再作为正式主架构：

- 通过 Python CLI 驱动 VSCode 功能
- 通过 Java / `plantuml.jar` 作为预览主链路
- 依赖 `jebbs.plantuml` 之类其他扩展提供核心体验
- 继续把复杂语义功能长期堆在 extension host 端的零散 provider 上

### 4.3 与 Python 端的关系

Python 端仍然是当前仓库最成熟的语义实现与功能参考，但 Node.js 侧不应通过“桥接调用 Python”获得能力。

正确关系应是：

- grammar 继续共享
- 语义规则尽可能行为对齐
- 用 golden tests / parity tests 校验一致性
- 运行时各自独立

Node.js 侧的目标是 editor tooling，不是立刻完整复刻 Python 端所有生成、渲染、模板能力。

---

## 5. 纯 JS 路线下的目标架构

### 5.1 架构分层

推荐把 VSCode 相关代码组织成四层。

#### A. Client 层

职责：

- VSCode activation
- 启动 / 监管 language server
- 注册 commands
- settings 映射
- webview / preview UI

这一层应该尽量薄，不承载语义逻辑。

#### B. Server 层

职责：

- LSP 协议处理
- 文档同步
- workspace graph 管理
- 调用 core 完成语义计算
- 返回 diagnostics、completion、hover、definition、references、rename 等结果

这一层是扩展能力中心。

#### C. Core 层

职责：

- parser adapter
- AST
- semantic model
- symbol resolution
- import-aware workspace model
- semantic diagnostics
- exporters / analyzers / diagram IR

这一层必须完全不依赖 VSCode API。

#### D. Renderer 层

职责：

- 从 diagram IR 生成 SVG / HTML
- 在 webview 中展示
- 维护 source-to-diagram 映射

这层是 visualization consumer，不是语义事实源。

### 5.2 推荐目录结构

为了兼容当前 repo，可以不立刻拆成 npm workspace，但逻辑边界应明确。推荐结构类似：

```text
editors/vscode/
  src/
    client/
      extension.ts
      commands/
      preview/
    server/
      main.ts
      handlers/
    core/
      parser/
      ast/
      semantics/
      workspace/
      diagnostics/
      diagram/
    webview/
      preview.ts
  parser/
  scripts/
  syntaxes/
  dist/
```

如果后续需要更强复用性，再把 `core/` 提升成单独 package 也可以，但在本 repo 当前阶段不是必须条件。

### 5.3 关键约束

新的架构必须满足以下硬约束：

- core 不依赖 `vscode`
- client 不重复实现语义逻辑
- server 通过标准 LSP 提供 editor intelligence
- preview 不依赖 Python / Java / PlantUML / 网络服务
- 保持与当前 `engines.vscode = ^1.60.0`、`CommonJS`、`ES2015` 的兼容思路

---

## 6. 语义核心需要覆盖的对象

language server 不只是把现在的 provider 搬到另一个进程，而是要补齐一套真正可复用的语义模型。

推荐最少覆盖以下对象：

- machine
- file / module
- variable definition
- state
- pseudo state
- event
- import statement
- import mappings
- transition
- forced transition expansion result
- lifecycle action
- aspect action
- `ref` target
- operation block
- expression
- source range / symbol identity

推荐最少覆盖以下语义过程：

- state path resolution
- event scope normalization
- import target resolution
- alias mapping
- `ref` resolution
- forced transition expansion
- duplicate definition detection
- unresolved symbol detection
- cross-file cycle detection
- incremental workspace invalidation

如果这些不先建立起来，后面的 references、rename、preview、semantic diagnostics 都会很脆弱。

---

## 7. 可视化在新路线里的定位

### 7.1 可视化仍然重要，但不是主架构

可视化在 editor 体验上仍然有很高价值，但在新的技术路线里，它的前置条件变成：

1. FCSTM source -> AST
2. AST -> semantic model
3. semantic model -> diagram IR
4. diagram IR -> SVG / HTML preview

这里的关键变化是第 4 步不再要求绑定 PlantUML。

### 7.2 为什么不再把 PlantUML 当作预览主链路

如果坚持 PlantUML 主链路，会直接违背“纯 JS runtime、无额外依赖”的目标，因为它通常意味着：

- Java
- `plantuml.jar`
- 额外 VSCode 扩展
- 或远程渲染服务

这些都不适合作为 FCSTM 扩展的正式主路径。

### 7.3 新的推荐方式

推荐方式是：

- language server 输出 diagram IR
- VSCode client 打开 webview
- webview 侧用纯 JS renderer 生成 SVG

后续如果需要兼容导出：

- 可以增加可选的 PlantUML exporter
- 但它只能是一个 export / interop capability
- 不能反向决定 preview 主架构

---

## 8. 与当前 repo 兼容的构建与工程标准

### 8.1 应保留的现有标准

新的 language server 方案应显式适配当前 repo，而不是推翻现有构建体系。

以下标准建议保留：

- repo root 继续以 `make vscode` 作为总入口
- `editors/vscode/Makefile` 继续作为本地扩展构建入口
- parser 继续从 canonical grammar 生成
- parser runtime 继续锁定 `antlr4 4.9.3`
- JS bundle 继续使用 `esbuild`
- client / server bundle 继续使用 `CommonJS`
- target 继续保持保守兼容的 `ES2015`
- `vsce` 继续负责 `.vsix` 打包
- `build-tsc` 可以继续保留给验证脚本使用

### 8.2 需要改造的地方

当前单入口 bundle 需要升级为多入口 bundle。

推荐产物布局改成：

```text
dist/
  client/
    extension.js
  server/
    server.js
  webview/
    preview.js
```

对应的建议：

- `package.json` 的 `main` 改为 `./dist/client/extension.js`
- client bundle 只对 `vscode` 做 external
- server bundle 不依赖 `vscode`
- webview bundle 与 client / server 分离，不混在 extension host bundle 中

### 8.3 当前 `esbuild` 规范对新方案的影响

当前 `esbuild.config.js` 已经明确了以下风格：

- `platform: 'node'`
- `format: 'cjs'`
- `target: 'es2015'`
- `keepNames: true`
- `treeShaking: true`

language server 方案应延续这组标准，而不是引入 ESM-only、Node version 要求更高、或难以和旧 VSCode 兼容的新技术栈。

### 8.4 依赖选择标准

为了适配当前 repo 和 `engines.vscode` 约束，新引入依赖建议满足：

- 可通过 npm 安装并被 esbuild 打包
- 不要求原生编译扩展
- 不要求额外系统级 runtime
- 不要求仅支持 ESM
- 与 VSCode `^1.60.0` 对应的 Node/Electron 能力兼容

这意味着：

- 可以使用 `vscode-languageclient` / `vscode-languageserver`
- 但要选兼容当前 VSCode 引擎范围的版本
- 不应随意引入 native addon 或高版本 Node 专属依赖

### 8.5 构建完成定义

language server 路线落地后，构建完成至少应满足：

- `make parser`
- `make build`
- `make package`
- `make verify`

都能在 `editors/vscode/` 目录中稳定执行。

同时，repo root 的：

- `make vscode`

也必须保持可用，不要求用户学习新的顶层构建入口。

---

## 9. 新的正式 scope

### 9.1 第一优先级能力

完整 language server 的第一优先级能力应为：

- syntax diagnostics
- semantic diagnostics
- document symbols
- completion
- hover
- definition
- references
- rename
- code actions
- folding ranges
- document links

### 9.2 第二优先级能力

在第一优先级稳定后，再进入：

- workspace symbols
- semantic tokens
- diagram preview
- diagram export
- static analyzers
- simulation assistant

### 9.3 暂不作为早期目标的能力

以下能力不适合在 language server 第一轮中扩张：

- 完整模板渲染 / 代码生成移植
- 完整复刻 Python simulate runtime
- 依赖外部工具链的图形输出
- 跨进程桥接 Python 作为语义主实现

---

## 10. 执行规则

本计划采用 phased execution。

每个 phase 都同时包含：

- TODO list
- Checklist

规则如下：

- TODO list 是该 phase 需要完成的工作项
- Checklist 是该 phase 的验收门槛
- 只有当该 phase 的 Checklist 全部勾选，才算 phase 完成
- 不允许只完成部分实现就宣称 phase 结束

---

## 11. 分阶段执行计划

## Phase 0：基线固化与构建重构

### 目标

在不破坏当前扩展能力的前提下，把工程形态从“单 bundle 的 provider 扩展”重构到“client/server/core/webview”结构，并保持当前 repo 构建入口不变。

### TODO

* [ ] 盘点并冻结当前扩展已具备的行为基线：diagnostics、symbols、completion、hover、import-aware 诊断与跳转
* [ ] 把当前 `src/` 中的实现重新划分到 `client/`、`server/`、`core/`、`webview/` 的逻辑边界
* [ ] 将当前单入口 `esbuild.config.js` 改造成多入口 bundle 配置
* [ ] 调整 `package.json` 的 `main`、scripts 和打包清单，使其适配 client/server 双产物
* [ ] 更新 `editors/vscode/Makefile`，让 `build`、`package`、`verify` 认知新的 dist 布局
* [ ] 保持 repo root `make vscode`、`vscode_install`、`vscode_clean` 的使用方式不变

### Checklist

* [ ] `cd editors/vscode && make parser && make build && make package` 可以成功执行
* [ ] repo root 的 `make vscode` 可以成功执行
* [ ] VSIX 中包含新的 client bundle、server bundle 和 icon
* [ ] 当前已有的 parser-backed 功能在重构后不发生明显行为回退

## Phase 1：语法核心与 AST 正规化

### 目标

把 parser 从“供扩展直接消费的工具”提升为“供 language server 与后续 analyzer 复用的核心能力”，并建立稳定 AST。

### TODO

* [ ] 从当前扩展代码中抽离 parser adapter，放入不依赖 VSCode API 的 core 层
* [ ] 定义统一 AST 节点模型和 source range 模型
* [ ] 为 states、events、transitions、forced transitions、lifecycle actions、imports、mappings、operation blocks、expressions 建立 AST 节点
* [ ] 建立 AST 序列化 / dump 能力，便于 golden test 与调试
* [ ] 补充 AST 级测试语料，覆盖当前 repo 已支持的 import 语法与多文件基础场景
* [ ] 保持 `make parser` 仍然以 canonical grammar 为事实源，不复制手写 grammar 逻辑

### Checklist

* [ ] AST 能稳定覆盖当前 grammar 中的关键结构，不依赖 ANTLR parse tree 细节直接暴露给上层
* [ ] source range 可以稳定用于 diagnostics、hover、definition、rename 等后续能力
* [ ] import 相关语法、forced transition、lifecycle action 和 expression 都有 AST 覆盖
* [ ] parser regeneration 流程仍然可通过 `make parser` 复现

## Phase 2：语义模型与多文件 workspace graph

### 目标

建立真正可供 language server 使用的语义模型，而不是停留在 parse tree 辅助工具层。

### TODO

* [ ] 定义 machine、file/module、state、event、transition、action、variable、import、symbol identity 等语义对象
* [ ] 实现 state path resolution、event scope normalization、`ref` resolution、import target resolution、alias mapping、forced transition expansion
* [ ] 建立多文件 workspace graph，并支持未保存 buffer 与磁盘文件的混合视图
* [ ] 把当前 import-aware 轻量 helper 升级为正式的 workspace semantic index
* [ ] 增加 semantic diagnostics：重复定义、未解析引用、循环 import、非法 mapping、目标状态不存在、事件冲突等
* [ ] 建立与 Python 侧的 parity corpus，比对代表性语义行为而不是桥接调用 Python

### Checklist

* [ ] 多文件模型在 workspace 中可以被稳定解析和组装
* [ ] 语义模型不依赖 `vscode` 模块，可单独测试
* [ ] semantic diagnostics 对同一输入具有确定性输出
* [ ] parity corpus 已覆盖 import、event scope、hierarchy、`ref`、forced transition 等高风险规则

## Phase 3：完整 language server 迁移

### 目标

把当前 extension-host 内的智能能力迁移到标准 LSP server 中，形成正式的 client/server 架构。

### TODO

* [ ] 引入与 `engines.vscode = ^1.60.0` 兼容的 `vscode-languageclient` / `vscode-languageserver` 版本
* [ ] 建立 bundled JS server entrypoint，并由 client 启动和监管
* [ ] 把 diagnostics、document symbols、completion、hover、definition 迁移到 LSP handlers
* [ ] 实现 text document sync、workspace folder sync、cancellation、debounce、server restart 恢复
* [ ] 增加 document links，用于 import path 的跳转体验
* [ ] 保持 client 侧尽量薄，只负责 activation、commands、settings、preview bridge

### Checklist

* [ ] 在 Windows、macOS、Linux 三个平台上都能正常启动 bundled language server
* [ ] 当前已有 editor intelligence 能力已经通过 LSP 提供，而不是继续分散在 extension host 内
* [ ] server 崩溃与重启路径可被验证，不需要用户手工恢复
* [ ] 运行时不依赖 Python、Java、其他 VSCode 扩展或网络服务

## Phase 4：高级语义编辑能力

### 目标

从“会提示”升级到“可导航、可重构、可修复”的完整语言工具体验。

### TODO

* [ ] 实现 references、rename、workspace symbols
* [ ] 实现 folding ranges、semantic tokens
* [ ] 实现 code actions 与 quick fixes，覆盖 import path、alias 冲突、未解析符号、事件作用域等典型问题
* [ ] 增强 completion，使其具备 path-aware、scope-aware、import-aware 的上下文补全能力
* [ ] 增加静态 analyzer：unreachable state、dead transition、unused event、重复 mapping 等
* [ ] 把 definition / references / rename 建立在统一 symbol identity 之上

### Checklist

* [ ] references、definition、rename 在同一 symbol 上结果一致
* [ ] rename 能正确处理多文件 workspace，不破坏 import 场景
* [ ] quick fixes 只在可证明安全时出现，不给出误导性修复
* [ ] 高级能力启用后不会在编辑时产生明显卡顿

## Phase 5：纯 JS 可视化与预览

### 目标

在不引入外部 runtime 的前提下，提供基于语义模型的图形预览能力。

### TODO

* [ ] 定义 diagram IR，使其由 semantic model 直接派生
* [ ] 设计纯 JS renderer，输出 SVG 作为首选预览格式
* [ ] 在 VSCode client 中接入 webview preview，不依赖 PlantUML、Java 或其他扩展
* [ ] 支持 unsaved buffer 的实时刷新
* [ ] 支持 source-to-diagram 与 diagram-to-source 的定位映射
* [ ] 提供最小可用命令集，例如 `Open Diagram Preview`、`Reveal Symbol in Diagram`、`Export SVG`
* [ ] 如确有互操作需求，再增加可选 PlantUML exporter，但不作为 preview 主链路

### Checklist

* [ ] 在一台干净的 VSCode 环境中，仅安装本扩展即可完成图形预览
* [ ] 预览可以消费未保存编辑内容，而不是只读磁盘文件
* [ ] 点击图中状态或转换可以回到源码位置
* [ ] SVG 导出结果稳定、可测试、可复现

## Phase 6：加固、文档收敛与发布

### 目标

把 language server 和 preview 方案从“技术可行”推进到“可发布、可回归、可维护”。

### TODO

* [ ] 扩展现有 `verify-*` 体系，新增 LSP、语义模型、preview、package smoke test
* [ ] 为 activation time、server startup、diagnostics latency 建立性能基线
* [ ] 更新 `editors/vscode/README.md`、教程文档、marketplace 文案、`TODO.md`
* [ ] 定义版本发布节奏与 alpha / beta / stable 的收敛策略
* [ ] 为 VSIX 安装、升级、回滚、故障排查准备 release checklist
* [ ] 对老 VSCode 版本兼容性、bundle 体积、server 崩溃恢复做专项验证

### Checklist

* [ ] `make verify` 已覆盖 language server 主路径与 preview 主路径
* [ ] `make package` 产出的 VSIX 可安装、可启动、可 smoke test
* [ ] 文档已不再把扩展描述为“短期内不做 full language server”
* [ ] 发布物、回滚方案和兼容性说明都已准备完毕

---

## 12. 风险与控制点

### 12.1 最大成本在语义建模，不在 LSP 壳子

language server 的协议层本身不是主要风险，主要风险是：

- 语义模型是否完整
- 多文件 import 场景是否稳定
- Python / Node.js 规则是否漂移
- 预览是否真的能不依赖外部工具

因此项目管理上不能把“server 已经跑起来”误认为核心完成。

### 12.2 不能一边继续堆 provider，一边声称在做 LSP

一旦 Phase 3 开始，就不应该继续在 extension host 侧大规模新增平行语义逻辑，否则最终只会得到两套实现：

- 一套 extension-host helper
- 一套 language server handler

这会直接制造漂移。

### 12.3 可视化不能倒逼语义走捷径

如果为了尽快出图而跳过 AST / semantic model / workspace graph，最后会得到一个看起来能 preview、但无法支撑 rename / references / code actions 的半成品体系。

### 12.4 当前 repo 兼容性约束必须持续生效

本仓库对兼容范围非常敏感，因此 VSCode 侧实现不能轻易引入：

- 需要更高 Node 版本的新语法或依赖
- ESM-only 包
- native addon
- 依赖额外系统运行时的工具链

所有技术选择都需要先经过“能否适配当前 repo 构建标准”的审查。

---

## 13. 最终建议

基于当前仓库状态，建议正式确认以下结论：

- `VSCODE_EXT.md` 不应再以“PlantUML 可视化路线”作为核心叙事
- FCSTM VSCode 扩展下一阶段的正式目标应是 **完整的纯 JS language server**
- 可视化是 language server 语义能力的下游能力，而不是主架构
- 运行时必须坚持纯 JS，不依赖 Python、Java、PlantUML 扩展或远程服务
- 工程上必须适配当前 repo 的 `make vscode`、`esbuild`、`vsce`、`CommonJS`、`ES2015`、`antlr4 4.9.3` 基线
- 实施上必须按 phase 推进，并以每个 phase 的 checklist 作为唯一完成标准

一句话总结：

**这件事的正确目标不是“给 FCSTM 接一个图形预览”，而是“把当前 parser-backed 扩展升级成完整、纯 JS、可离线、可发布的 FCSTM language server，并让可视化成为它自然长出来的能力”。**
