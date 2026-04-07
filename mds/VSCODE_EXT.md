# FCSTM VSCode 扩展、jsfcstm 库与纯 JS Language Server 设计

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-18 | 初始版本，聚焦 VSCode 可视化方案与 Node.js 原生语义层路线 | Codex |
| 0.2.0 | 2026-04-06 | 基于当前仓库状态重构文档，补充现状快照、构建链路、纯 JS runtime 约束、完整 language server 路线与 phased execution plan | Codex |
| 0.3.0 | 2026-04-07 | 引入 JS 库拆分方案，明确 npm 可发布 JS 库优先、VSCode 消费该库、拆分完成前不新增功能 | Codex |
| 0.3.1 | 2026-04-07 | 将库命名统一为 `jsfcstm`，路径调整为 `editors/jsfcstm`，并同步 npm 包命名与发布配置建议 | Codex |

---

## 1. 文档定位

本文档在 `0.2.0` 版本基础上再做一次结构性修正。

第一，继续承认当前仓库真实状态：今天的 `editors/vscode/` 已经不是一个只有语法高亮的静态语言包，而是一个具备 ANTLR JS 解析、诊断、符号、补全、悬停、import-aware 轻量工作区能力和 import path definition 的 parser-backed 扩展。

第二，继续坚持目标不是“先做可视化”，而是“构造一个完整的、纯 JS 的 FCSTM language server”，并把可视化明确降级为该 language server 语义能力的一个下游能力，而不是架构中心。

第三，工程组织上不再建议把主要语义能力继续塞在 `editors/vscode/` 内部，而是明确建议先拆出一个位于 `editors/jsfcstm/` 的、适合独立发布到 npm 的 FCSTM JS 库，再由 VSCode 扩展去 import 它。

这里的“纯 JS”需要定义清楚：

- 运行时只依赖 Node.js 环境和可 bundle 的 npm JavaScript 依赖
- 不依赖 Python CLI
- 不依赖 Java / PlantUML jar
- 不依赖其他 VSCode 扩展作为核心功能前提
- 不依赖远程服务或网络渲染

考虑到当前仓库的 VSCode 扩展已经采用 `TypeScript + esbuild + CommonJS + ES2015 target` 的工程基线，源码层继续使用 TypeScript 依然是与现有 repo 最兼容、成本最低的做法。最终交付物仍然是纯 JavaScript bundle 和可发布的 npm 包，因此不与“纯 JS runtime”目标冲突。

---

## 2. 当前仓库状态快照（截至 2026-04-07）

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
- 还没有一个可独立发布到 npm 的 `editors/jsfcstm` 库承载主要 JS 能力
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

- 先构建位于 `editors/jsfcstm/` 的、可独立发布到 npm 的 FCSTM JS 库
- 构建 **纯 JS runtime 的 FCSTM language server**
- 让 VSCode 扩展变成一个 **client + bundled server** 的标准结构，并消费 `editors/jsfcstm`
- 所有核心 editor intelligence 能力都建立在 `editors/jsfcstm` 提供的 Node.js 语义核心之上
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

### 4.4 拆分优先于新功能

这里再明确一个执行原则：

- 先拆分
- 先维持现状
- 先把 `editors/jsfcstm -> editors/vscode` 的依赖链走通
- 在拆分 checklist 全部通过前，不启动新的 editor feature 开发

原因很直接：

- 如果不先拆，后续新功能会继续长在 `editors/vscode/` 里
- 之后再迁移，只会增加重复重构成本
- 一边拆分、一边新增功能，最容易造成行为漂移和边界失控

---

## 5. 纯 JS 路线下的目标架构

### 5.1 Repo 级拆分原则

推荐先在仓库层面拆成两个明确角色：

- `editors/jsfcstm/`
- `editors/vscode/`

其中：

- `editors/jsfcstm/` 是 FCSTM 的主 JS 库，目标是可独立发布到 npm
- `editors/vscode/` 是 VSCode 扩展和 language server 宿主，主要负责 client glue、server entry、commands、settings、webview

### 5.2 `editors/jsfcstm` 的职责

`editors/jsfcstm` 应承载绝大部分“可复用的非 VSCode 专属能力”，至少包括：

- parser adapter
- AST
- semantic model
- symbol resolution
- import-aware workspace model
- semantic diagnostics
- analyzers
- diagram IR
- renderer core 或 renderer 前置数据层

这部分必须满足：

- 不依赖 `vscode`
- 可以被 VSCode 扩展消费
- 可以被未来其他 JS/TS consumer 消费
- 结构上适合独立发到 npm

### 5.3 `editors/vscode` 的职责

`editors/vscode` 的职责应收敛为：

- VSCode activation
- 启动 / 监管 bundled language server
- 将 VSCode 文档事件桥接给 server
- 注册 commands
- settings 映射
- webview / preview UI
- 打包 VSIX

原则上，除了 VSCode API glue 和 UI glue，新的主要功能默认都不直接写在 `editors/vscode/` 里。

### 5.4 推荐目录结构

推荐结构类似：

```text
editors/
  jsfcstm/
    src/
      parser/
      ast/
      semantics/
      workspace/
      diagnostics/
      analyzers/
      diagram/
      renderer/
      index.ts
    dist/
    package.json
    tsconfig.json
    README.md
  vscode/
    src/
      client/
        extension.ts
        commands/
        preview/
      server/
        main.ts
        handlers/
      webview/
        preview.ts
    parser/
    scripts/
    syntaxes/
    dist/
    package.json
```

### 5.5 依赖方向

依赖方向应固定为：

- `editors/vscode -> editors/jsfcstm`
- `editors/jsfcstm -/-> editors/vscode`

进一步说：

- language server handlers 可以位于 `editors/vscode/`，但其语义实现应调用 `editors/jsfcstm`
- preview 可以位于 `editors/vscode/`，但其 diagram 数据和渲染核心应尽量来自 `editors/jsfcstm`
- 除非明确属于 VSCode API 适配，否则新增逻辑默认先考虑放进 `editors/jsfcstm`

### 5.6 本地开发与未来 npm 发布的关系

为了兼容当前 repo，不要求一开始就把整个仓库改造成 npm workspace。

更稳妥的建议是：

- 先创建独立的 `editors/jsfcstm/package.json`
- 先让 `editors/vscode/package.json` 通过本地依赖方式消费它
  - 例如 `file:../jsfcstm`
  - 或后续再升级到 workspace dependency
- 一旦包结构、exports、构建和 smoke test 稳定，再考虑真正发布到 npm

这样做的好处是：

- 先把 repo 内依赖关系跑通
- 不把“是否立刻发布 npm”变成阻塞项
- 但从目录、构建和包边界上，始终按“可发布 npm 库”来设计

### 5.7 包名建议

推荐采用“正式名 + 过渡名”的策略。

正式长期包名建议：

- `@pyfcstm/jsfcstm`

理由：

- 和仓库主项目 `pyfcstm` 的品牌一致
- `jsfcstm` 直接表达这是 FCSTM 的 JS 侧主库
- 在 VSCode、CLI、未来 web playground 等多个 JS consumer 中都自然
- 导入形式简洁：`import { ... } from '@pyfcstm/jsfcstm'`

如果 npm 侧暂时还没有 `@pyfcstm` scope，建议的过渡名：

- `@hansbug/jsfcstm`

如果连个人 scope 也暂时不想处理，最后兜底的 unscoped 名称可考虑：

- `jsfcstm`

但不推荐 unscoped 作为长期正式名，原因是：

- 缺少项目归属信息
- 后续生态扩展时命名空间不清晰
- 对外看不出它和 `pyfcstm` 的关系

截至 2026-04-07，本次检查时以下名字在 npm registry 上都返回了 `404 Not Found`：

- `@pyfcstm/jsfcstm`
- `@hansbug/jsfcstm`
- `jsfcstm`

这说明“包名本身目前没有已发布冲突”，但要注意：

- scoped 包能否真正发布，不只取决于名字是否空闲
- 还取决于你是否拥有对应 scope
- 因此长期方案应尽早把 `@pyfcstm` scope 准备好

### 5.8 关键约束

新的架构必须满足以下硬约束：

- `editors/jsfcstm` 不依赖 `vscode`
- client 不重复实现语义逻辑
- server 通过标准 LSP 提供 editor intelligence，并优先调用 `editors/jsfcstm`
- preview 不依赖 Python / Java / PlantUML / 网络服务
- 保持与当前 `engines.vscode = ^1.60.0`、`CommonJS`、`ES2015` 的兼容思路

---

## 6. `editors/jsfcstm` 语义核心需要覆盖的对象

language server 不只是把现在的 provider 搬到另一个进程，而是要在 `editors/jsfcstm` 里补齐一套真正可复用的语义模型。

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

- `editors/jsfcstm` 与 `editors/vscode` 都继续采用 npm package 形式管理
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

除了 `editors/vscode` 需要升级为多入口 bundle，仓库里还需要新增 `editors/jsfcstm` 的独立包构建。

推荐未来的构建关系是：

1. 先构建 `editors/jsfcstm`
2. 再构建 `editors/vscode`
3. VSCode 扩展从本地包依赖中消费 `editors/jsfcstm`

推荐产物布局改成：

```text
editors/jsfcstm/
  dist/
    index.js
    ...
editors/vscode/
  dist/
    client/
      extension.js
    server/
      server.js
    webview/
      preview.js
```

对应的建议：

- `editors/jsfcstm/package.json` 应具备清晰的 `name`、`main`、`exports`、`files`、`license`
- `editors/jsfcstm` 应能单独执行 `npm pack`
- `editors/vscode/package.json` 在仓库内先通过本地依赖引用 `editors/jsfcstm`
- `editors/vscode/package.json` 的 `main` 改为 `./dist/client/extension.js`
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

为了适配当前 repo 和 `engines.vscode` 约束，`editors/jsfcstm` 和 `editors/vscode` 新引入依赖都建议满足：

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

- `cd editors/jsfcstm && npm pack`
- `make parser`
- `make build`
- `make package`
- `make verify`

其中：

- `editors/jsfcstm` 需要能单独构建和打包
- `editors/vscode` 需要在消费本地 `editors/jsfcstm` 的前提下稳定构建和打包

同时，repo root 的：

- `make vscode`

也必须保持可用，不要求用户学习新的顶层构建入口。

### 8.6 npm 发布流程（适合没有 JS 经验时照做）

这部分给出一条尽量低风险、适合第一次做 npm 发布的路线。

#### 8.6.1 第一次发布前，你需要先准备什么

你至少需要完成下面这些准备：

* [ ] 安装 Node.js 与 npm
* [ ] 注册一个 npm 账号
* [ ] 在本机执行 `npm login`
* [ ] 执行 `npm whoami`，确认当前登录账号正确
* [ ] 决定最终发布 scope
* [ ] 确认是否启用 2FA，或者准备好可用于发布的 access token

推荐的 scope 决策顺序：

1. 最优先：创建并持有 `@pyfcstm` scope，然后发布 `@pyfcstm/jsfcstm`
2. 过渡方案：如果你当前 npm 用户名就是 `hansbug`，先发布 `@hansbug/jsfcstm`
3. 最后兜底：临时使用 `jsfcstm`

如果你准备走正式方案 `@pyfcstm/jsfcstm`，你需要额外完成：

* [ ] 在 npm 上创建或拿到 `pyfcstm` 这个 scope 的所有权
* [ ] 确认后续发布者也能加入这个 scope，而不是把发布权绑死在个人账号上

#### 8.6.2 `editors/jsfcstm/package.json` 至少应包含什么

推荐最小骨架类似：

```json
{
  "name": "@pyfcstm/jsfcstm",
  "version": "0.1.0-alpha.1",
  "description": "FCSTM core parser, semantics, diagnostics, and diagram support for JavaScript and TypeScript",
  "license": "LGPL-3.0",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "require": "./dist/index.js"
    }
  },
  "files": [
    "dist",
    "README.md",
    "LICENSE"
  ],
  "publishConfig": {
    "access": "public"
  }
}
```

这里有两个关键点：

- scoped public package 要显式设置 `access: public`
- 先用 `alpha` 版本起步，比一上来发 `1.0.0` 更稳

#### 8.6.3 第一次本地打包怎么做

推荐顺序：

1. 先构建产物
2. 再本地打包
3. 先 dry-run
4. 最后再真实发布

命令顺序建议如下：

```bash
cd editors/jsfcstm

# 安装依赖
npm install

# 构建
npm run build

# 本地生成 tarball，检查真正会被发布的内容
npm pack

# 检查发布流程，不真正上传
npm publish --access public --dry-run
```

你需要重点检查：

* [ ] tarball 里只有 `dist/`、`README.md`、`LICENSE` 之类应发布内容
* [ ] 没有把测试缓存、源码垃圾文件、临时文件带进去
* [ ] `main`、`types`、`exports` 指向的文件都真实存在
* [ ] 从另一个临时目录里可以通过 tarball 安装并 `require()` 成功

#### 8.6.4 第一次真实发布怎么做

如果前面的 `npm pack` 和 `npm publish --dry-run` 都没有问题，第一次真实发布建议发预发布版本：

```bash
cd editors/jsfcstm
npm publish --access public --tag next
```

等预发布验证稳定后，再发正式版本：

```bash
cd editors/jsfcstm
npm publish --access public
```

建议的版本节奏：

- 第一次：`0.1.0-alpha.1`
- 结构稳定后：`0.1.0-beta.1`
- 真正对外稳定后：`0.1.0`

#### 8.6.5 如果你要做 CI/CD 自动发布

推荐优先级如下：

1. 最推荐：npm trusted publishing + GitHub Actions
2. 次选：npm granular access token
3. 不推荐：长期使用个人传统 token + 手工脚本

原因：

- trusted publishing 更安全
- provenance 支持更自然
- 不需要把长期 token 明文绑在仓库 secret 上

如果暂时不做自动发布，也没问题。第一阶段完全可以先手工发布，只要先把：

- 包结构
- 版本规则
- dry-run
- smoke test

走通即可。

#### 8.6.6 如果你完全没有 npm 经验，最小可执行清单

你可以只按下面这组最小步骤做：

1. 去 npmjs.com 注册账号
2. 本机执行 `npm login`
3. 执行 `npm whoami`，确认登录成功
4. 先决定是发 `@pyfcstm/jsfcstm` 还是过渡发 `@hansbug/jsfcstm`
5. 在 `editors/jsfcstm/package.json` 里填好 `name`、`version`、`main`、`types`、`exports`、`files`、`publishConfig.access`
6. 执行 `npm run build`
7. 执行 `npm pack`
8. 执行 `npm publish --access public --dry-run`
9. 没问题后再执行真实 `npm publish`

如果你愿意完全按稳妥路线走，我建议你第一版只做两件事：

- 先把 `npm pack` 走通
- 再把 `npm publish --dry-run` 走通

在这两个命令没有稳定之前，不急着真的发包。

---

## 9. 新的正式 scope

### 9.1 当前第一优先级不是新功能，而是拆分与稳态迁移

在本版计划里，第一优先级不是立刻增加 references、rename、preview 等新能力，而是：

- 创建 `editors/jsfcstm`
- 让 `editors/vscode` 稳定 import `editors/jsfcstm`
- 把当前已有能力迁移到新边界下
- 在“不新增功能”的前提下维持现状

只有这一步走通后，后续新功能开发才是健康的。

### 9.2 拆分完成后的第一优先级能力

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

### 9.3 第二优先级能力

在第一优先级稳定后，再进入：

- workspace symbols
- semantic tokens
- diagram preview
- diagram export
- static analyzers
- simulation assistant

### 9.4 暂不作为早期目标的能力

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
- Phase 0 到 Phase 2 属于拆分期，只允许做拆分、迁移、对齐和兼容性修复
- 在 Phase 2 Checklist 全部通过之前，不启动新的功能开发

---

## 11. 分阶段执行计划

## Phase 0：拆分原则确认与现状基线冻结

### 目标

先把“怎么拆、拆到哪里、什么阶段不许加新功能”说清楚，并把当前扩展行为冻结成可回归的基线。

### TODO

* [ ] 盘点并冻结当前扩展已具备的行为基线：diagnostics、symbols、completion、hover、import-aware 诊断与跳转
* [ ] 明确 `editors/jsfcstm` 与 `editors/vscode` 的边界、职责、依赖方向和所有权
* [ ] 确认 `editors/jsfcstm` 的目标定位是“可独立发布到 npm 的 FCSTM JS 库”
* [ ] 确认 `editors/vscode` 在拆分后只保留 VSCode API glue、LSP server entry、commands、settings、webview 等宿主职责
* [ ] 明确拆分期 feature freeze 规则：Phase 0 到 Phase 2 不新增功能
* [ ] 把现有验证脚本视为迁移验收基线，而不是在拆分期重写需求

### Checklist

* [ ] `editors/jsfcstm` 与 `editors/vscode` 的职责边界已经明确写清
* [ ] 当前扩展已有能力已经被列成可验收的 baseline
* [ ] feature freeze 规则已经明确：拆分完成前不启动新功能
* [ ] 后续阶段都以“先拆分、先维持现状”为默认前提

## Phase 1：建立 `editors/jsfcstm` 可发布库骨架

### 目标

创建 `editors/jsfcstm/`，先把它做成一个结构正确、可被 VSCode 本地消费、未来可发布到 npm 的独立 JS 库，但暂不在此阶段引入新功能。

### TODO

* [ ] 创建 `editors/jsfcstm/` 目录及基础文件：`package.json`、`tsconfig.json`、`README.md`、`src/index.ts`
* [ ] 为 `editors/jsfcstm` 设计清晰的包元数据：`name`、`version`、`main`、`exports`、`files`、`license`
* [ ] 为 `editors/jsfcstm` 建立独立构建脚本和最小 smoke test
* [ ] 让 `editors/vscode/package.json` 通过本地依赖方式消费 `editors/jsfcstm`
* [ ] 调整 `editors/vscode` 构建流程，使其在需要时先解析并使用本地 `editors/jsfcstm`
* [ ] 保持 repo root 的 `make vscode` 路线可演进到“先 js、后 vscode”的顺序

### Checklist

* [ ] `cd editors/jsfcstm && npm pack` 可以成功执行
* [ ] `cd editors/vscode && npm install` 可以成功解析本地 `editors/jsfcstm` 依赖
* [ ] `editors/jsfcstm` 已具备未来发布到 npm 所需的最小包结构
* [ ] 此阶段结束时，扩展功能没有新增，也没有因为拆出空壳包而回退

## Phase 2：把现有能力迁入 `editors/jsfcstm` 并维持现状

### 目标

把现有 parser-backed 能力背后的主要 JS 逻辑迁到 `editors/jsfcstm`，但此阶段仍然不新增功能，只要求维持现状并把依赖方向走通。

### TODO

* [ ] 将 parser adapter 从 `editors/vscode` 抽出到 `editors/jsfcstm`
* [ ] 将可复用的 parse helpers、source range helpers、import resolution / workspace indexing 逻辑迁入 `editors/jsfcstm`
* [ ] 将 VSCode 无关的数据提取逻辑迁入 `editors/jsfcstm`，例如符号提取、补全候选构造、悬停元数据等
* [ ] 让 `editors/vscode` 中现有 providers 改为优先调用 `editors/jsfcstm`
* [ ] 保持现有验证脚本继续可用，并用它们做迁移前后行为对齐
* [ ] 明确此阶段不增加 references、rename、preview 等新功能

### Checklist

* [ ] 现有 parser-backed 功能在用户视角上基本维持现状
* [ ] `verify-p0.2` 到 `verify-p0.6`、`verify-import-editor-support`、`test-e2e` 仍可作为主要回归基线
* [ ] `editors/vscode` 对 `editors/jsfcstm` 的依赖链已经在真实构建中走通
* [ ] Phase 2 完成后，新增功能默认应先开发在 `editors/jsfcstm`，而不是回写到 `editors/vscode`

## Phase 3：在 `editors/jsfcstm` 中建立 AST、语义模型与 workspace graph

### 目标

在拆分完成且现状跑通之后，再开始真正的新内容开发，而且主要开发位置应在 `editors/jsfcstm`。

### TODO

* [ ] 定义统一 AST 节点模型和 source range 模型
* [ ] 为 states、events、transitions、forced transitions、lifecycle actions、imports、mappings、operation blocks、expressions 建立 AST 节点
* [ ] 定义 machine、file/module、state、event、transition、action、variable、import、symbol identity 等语义对象
* [ ] 实现 state path resolution、event scope normalization、`ref` resolution、import target resolution、alias mapping、forced transition expansion
* [ ] 建立多文件 workspace graph，并支持未保存 buffer 与磁盘文件的混合视图
* [ ] 建立与 Python 侧的 parity corpus，比对代表性语义行为而不是桥接调用 Python

### Checklist

* [ ] AST 和语义模型都位于 `editors/jsfcstm`，而不是散落在 `editors/vscode`
* [ ] 语义模型不依赖 `vscode` 模块，可单独测试
* [ ] workspace graph 可以稳定支撑 import-aware 多文件模型
* [ ] parity corpus 已覆盖 import、event scope、hierarchy、`ref`、forced transition 等高风险规则

## Phase 4：完整 language server 迁移

### 目标

在 `editors/jsfcstm` 已具备 AST 和语义模型后，把当前智能能力迁移到标准 LSP server 中，形成正式的 `vscode client + bundled server + editors/jsfcstm` 架构。

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
* [ ] server 的主要语义实现依赖 `editors/jsfcstm`，而不是在 handler 里重写
* [ ] 运行时不依赖 Python、Java、其他 VSCode 扩展或网络服务

## Phase 5：高级语义编辑能力

### 目标

在 `editors/jsfcstm` 语义核心和 language server 都稳定后，再进入 references / rename / analyzers 等真正的新能力。

### TODO

* [ ] 在 `editors/jsfcstm` 中补齐 symbol identity、references graph 和 rename planning 所需数据结构
* [ ] 实现 references、rename、workspace symbols
* [ ] 实现 folding ranges、semantic tokens
* [ ] 实现 code actions 与 quick fixes，覆盖 import path、alias 冲突、未解析符号、事件作用域等典型问题
* [ ] 增强 completion，使其具备 path-aware、scope-aware、import-aware 的上下文补全能力
* [ ] 增加静态 analyzer：unreachable state、dead transition、unused event、重复 mapping 等

### Checklist

* [ ] references、definition、rename 在同一 symbol 上结果一致
* [ ] rename 能正确处理多文件 workspace，不破坏 import 场景
* [ ] quick fixes 只在可证明安全时出现，不给出误导性修复
* [ ] 新能力的主要实现仍然位于 `editors/jsfcstm`，而不是回流到 `editors/vscode`

## Phase 6：纯 JS 可视化与预览

### 目标

在语义基础设施已经稳定之后，再基于 `editors/jsfcstm` 提供的 diagram IR 和 renderer 能力构建预览。

### TODO

* [ ] 在 `editors/jsfcstm` 中定义 diagram IR，使其由 semantic model 直接派生
* [ ] 在 `editors/jsfcstm` 中设计纯 JS renderer，输出 SVG 作为首选预览格式
* [ ] 在 VSCode client 中接入 webview preview，不依赖 PlantUML、Java 或其他扩展
* [ ] 支持 unsaved buffer 的实时刷新
* [ ] 支持 source-to-diagram 与 diagram-to-source 的定位映射
* [ ] 提供最小可用命令集，例如 `Open Diagram Preview`、`Reveal Symbol in Diagram`、`Export SVG`
* [ ] 如确有互操作需求，再增加可选 PlantUML exporter，但不作为 preview 主链路

### Checklist

* [ ] 在一台干净的 VSCode 环境中，仅安装本扩展即可完成图形预览
* [ ] 预览可以消费未保存编辑内容，而不是只读磁盘文件
* [ ] diagram IR 与 renderer 主实现位于 `editors/jsfcstm`
* [ ] SVG 导出结果稳定、可测试、可复现

## Phase 7：加固、文档收敛与双发布准备

### 目标

把 `editors/jsfcstm` 和 VSCode 扩展都推进到“可发布、可回归、可维护”的状态。

### TODO

* [ ] 扩展现有 `verify-*` 体系，新增 JS library、LSP、preview、package smoke test
* [ ] 为 activation time、server startup、diagnostics latency 建立性能基线
* [ ] 更新 `editors/jsfcstm/README.md`、`editors/vscode/README.md`、教程文档、marketplace 文案、`TODO.md`
* [ ] 为 `editors/jsfcstm` 准备 npm 发布前检查，例如 `npm pack` / `npm publish --dry-run`
* [ ] 为 VSIX 安装、升级、回滚、故障排查准备 release checklist
* [ ] 对老 VSCode 版本兼容性、bundle 体积、server 崩溃恢复做专项验证

### Checklist

* [ ] `editors/jsfcstm` 已达到可发布 npm 包的基本质量门槛
* [ ] `make verify` 已覆盖 JS library 主路径、language server 主路径与 preview 主路径
* [ ] `make package` 产出的 VSIX 可安装、可启动、可 smoke test
* [ ] 发布物、回滚方案和兼容性说明都已准备完毕

---

## 12. 风险与控制点

### 12.1 最大前置风险是拆分不彻底

如果 `editors/jsfcstm` 没有真正成为主库，只是形式上创建目录，后续会出现三个问题：

- 新能力继续写回 `editors/vscode`
- JS library 变成空壳或二等产物
- 未来 npm 发布和 VSCode 复用都会被迫再次重构

因此 Phase 0 到 Phase 2 的拆分验收必须严格执行，不能一边拆分一边新增功能。

### 12.2 最大技术成本在语义建模，不在 LSP 壳子

language server 的协议层本身不是主要风险，主要风险是：

- 语义模型是否完整
- 多文件 import 场景是否稳定
- Python / Node.js 规则是否漂移
- 预览是否真的能不依赖外部工具

因此项目管理上不能把“server 已经跑起来”误认为核心完成。

### 12.3 不能一边继续堆 provider，一边声称在做 LSP

一旦 Phase 4 开始，就不应该继续在 extension host 侧大规模新增平行语义逻辑，否则最终只会得到两套实现：

- 一套 extension-host helper
- 一套 language server handler

这会直接制造漂移。

### 12.4 可视化不能倒逼语义走捷径

如果为了尽快出图而跳过 AST / semantic model / workspace graph，最后会得到一个看起来能 preview、但无法支撑 rename / references / code actions 的半成品体系。

### 12.5 当前 repo 兼容性约束必须持续生效

本仓库对兼容范围非常敏感，因此 `editors/jsfcstm` 和 VSCode 侧实现都不能轻易引入：

- 需要更高 Node 版本的新语法或依赖
- ESM-only 包
- native addon
- 依赖额外系统运行时的工具链

所有技术选择都需要先经过“能否适配当前 repo 构建标准”的审查。

---

## 13. 最终建议

基于当前仓库状态，建议正式确认以下结论：

- `VSCODE_EXT.md` 不应再以“PlantUML 可视化路线”作为核心叙事
- 先创建位于 `editors/jsfcstm` 的、适合独立发布到 npm 的 FCSTM JS 库
- 该库的正式长期包名建议定为 `@pyfcstm/jsfcstm`
- VSCode 扩展应消费 `editors/jsfcstm`，而不是继续把主要逻辑堆在 `editors/vscode`
- FCSTM VSCode 扩展下一阶段的正式目标应是 **完整的纯 JS language server**
- 可视化是 language server 语义能力的下游能力，而不是主架构
- 运行时必须坚持纯 JS，不依赖 Python、Java、PlantUML 扩展或远程服务
- 执行顺序必须是：先拆分、先维持现状、拆分走通后再开发新功能
- 工程上必须适配当前 repo 的 `make vscode`、`esbuild`、`vsce`、`CommonJS`、`ES2015`、`antlr4 4.9.3` 基线
- 实施上必须按 phase 推进，并以每个 phase 的 checklist 作为唯一完成标准

一句话总结：

**这件事的正确目标不是“继续在 `editors/vscode` 里边改边长功能”，而是“先拆出 `editors/jsfcstm` 这个可发布 npm 库、让 VSCode 扩展消费它、在维持现状的前提下完成拆分，然后再把新的 language server 与可视化能力主要开发在这个 JS 库之上”。**
