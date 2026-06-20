# c_poll 模板维护手册

`c_poll` 是内置 C-family runtime 模板，其事件输入模型为 hook-polled。生成运行时不会在每个 cycle 接收外部 event-id 数组，而是调用已安装的 event-check functions 来判断每个 DSL event 在当前 cycle 是否活跃。

本文件是 `templates/c_poll/` 的维护者手册。它会被 renderer 忽略，不会复制到生成目录。生成目录里的用户手册来自 `README.md.j2` / `README_zh.md.j2`。

## 目标与非目标

当宿主环境本身已经通过 callbacks、device reads、polling functions 或 application state 暴露事件信号，并且 `cycle(machine)` 这种 API 比每轮提交 event-id 更适合集成时，应使用该模板。

在事件输入模型不要求差异的地方，`c_poll` 应尽量贴近 `templates/c/`。它不是另一套语义 runtime：FCSTM state、transition、lifecycle、validation、rollback 和 hook behavior 都必须继续与 simulator 以及常规 C 模板对齐。

生成产物不得依赖 `pyfcstm`、Python 或第三方 runtime libraries。

## 源码布局与生成产物

| 模板源码 | 维护职责 | 生成产物 |
| --- | --- | --- |
| `machine.h.j2` | 公开 C 集成面模板，包括 event-check types | `machine.h` |
| `machine.c.j2` | 高性能 hook-polled generated runtime implementation 模板 | `machine.c` |
| `README.md.j2` | 英文生成物用户手册 | `README.md` |
| `README_zh.md.j2` | 中文生成物用户手册 | `README_zh.md` |
| `config.yaml` | renderer 配置、C 语句渲染、helper 命名和 ignore 规则 | 不复制 |
| `template.json` | 内置模板 metadata | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | renderer 不复制，但会进入 packaged template archives |

`config.yaml` 会在生成输出时忽略 `README.md`、`README_zh.md` 和 `template.json`。但 `make tpl` 仍会打包完整模板源码目录，因此修改本手册后必须通过 `make tpl` 刷新并验证本地生成的 `pyfcstm/template/c_poll.zip`。该 archive 在普通 checkout 中被 git 忽略；setup 和 packaging 命令会从源码重新生成它。

## 兼容性与运行时依赖边界

生成的 `c_poll` 产物默认应保持以下约束：

- C99 implementation path。
- 生成公开头文件和代表性 harness 保持 C++98-compatible integration path。
- runtime 只依赖标准库。
- 不依赖 `pyfcstm`、Python、生成期 helper 或第三方 C libraries。
- 保持广泛编译器和平台兼容，与 `templates/c/` 采用的 C-family policy 对齐。

`machine.h` 是公开集成面；`machine.c` 是面向语义和性能优化的 generated runtime implementation。

## 资源生命周期与泄漏策略

Generated `c_poll` runtime 可能在控制应用中长期运行。因此资源 ownership 必须清楚且无泄漏：`..._create()` 负责 allocation，`..._destroy()` 负责释放，`..._init()` / `..._hot_start()` 重置 state 时不能泄漏，`..._set_hooks()` 和 `..._set_event_checks()` 只保存调用方拥有的 table 与 user-data 指针而不接管 ownership，每次 `cycle()` 结束后只能留下 machine-owned persistent state。

修改 `machine.c.j2` 或 allocation 相关 public API 时，在工具可用的情况下，至少用一个代表性 generated harness 跑 AddressSanitizer / LeakSanitizer、valgrind 或等价平台工具。Harness 应覆盖 event-check installation、repeated cycles、hot start、hook callbacks 和 destroy paths。若发现当前改动范围外的既有 leak 或 ownership bug，应记录可复现 harness 并拆成专门修复。

## 部署剖面维护纪律

`c_poll` 模板和 `templates/c/` 共享 C-family 部署剖面，并额外把 event-check 表纳入公开集成面：

| 剖面 | 公开形态 | 必要检查 |
| --- | --- | --- |
| 默认宿主 C99 | `..._create()`、`..._create_uninitialized()` 和 `..._destroy()` 可用。 | 既有 create/destroy、hot-start、hook、event-check 和共享语义对齐测试继续通过。 |
| 调用方拥有对象 | 调用方自己分配 `Machine` 存储，使用 `..._init(&machine)` / `..._hot_start(...)`，并按需安装 hooks 与 event checks。 | CMake 驱动的本机 harness 覆盖栈上存储、静态存储、event-check 安装、hook 安装、hot start 和失败路径，且不依赖 heap helpers。 |
| 无堆剖面 | `PYFCSTM_GENERATED_NO_HEAP` 移除 heap API 声明/定义，以及只服务于 `calloc/free` 的 `<stdlib.h>` include；event-check API 仍然可用。 | 头文件预处理或生成文件检查证明 heap API 声明消失；link 或 symbol 检查证明不引用 `calloc/free`；event-check CMake harness 仍能运行。 |

`PYFCSTM_GENERATED_NO_HEAP` 是“符号是否存在”的契约。模板代码应使用
`#if defined(PYFCSTM_GENERATED_NO_HEAP)` 或等价 `#ifdef`，不要使用
`#if PYFCSTM_GENERATED_NO_HEAP`。文档推荐消费端写法为
`-DPYFCSTM_GENERATED_NO_HEAP`；如果外部构建写成
`-DPYFCSTM_GENERATED_NO_HEAP=1`，也必须选择同一个无堆剖面。

这份契约有三侧必须同步：

- `machine.h.j2`：无堆剖面下移除公开 heap 声明，同时保留 hook 和 event-check 声明；
- `machine.c.j2`：无堆剖面下移除 heap 实现和 `<stdlib.h>` include；
- 生成 README 示例：CMake 消费端使用 `PUBLIC` / `INTERFACE` 传播宏，或者所有包含
  `machine.h` 的最终 target 都能看到同一定义。

模板本机测试必须继续使用 CMake 作为构建驱动。用户 README 可以展示 gcc / clang 风格
单命令示例，但 pytest 中不要新增一套手写宿主编译器调度层。

## 公开集成面

`machine.h` 负责稳定集成契约：

- generated machine 和 persistent variable types；
- public state-id 和 event-id macros；
- abstract hook callback signatures 和 hook table；
- event-check callback signatures 和完整 generated event-check table；
- 通过 `..._set_event_checks(machine, checks, user_data)` 挂载事件输入；
- 通过 `..._cycle(machine)` 使用已安装 event checks 执行一个 cycle；
- hot start、current-state、variable、ended-state、last-error 和 embedded-model accessors。

`machine.c` 负责 generated execution details、event-check cache、validation state、rollback state 和 dispatch helpers。集成方不应编辑或依赖这些内部细节。

## Event-check 模型

每个声明的 DSL event 都会映射到 generated `EventChecks` table 中的一个字段。对于声明了事件的 machine，调用方必须在 `cycle()` 运行前安装完整 table。

Event-check callback 是只读探针：

- 返回非零表示该 event 在当前 cycle 活跃；
- 返回 `0` 表示该 event 在当前 cycle 不活跃；
- callback 不应修改 machine persistent variables；
- `EventContext` 会标识被查询的 event、当前 leaf state 和变量快照。

Runtime 使用 lazy evaluation 和 per-cycle cache。如果同一个 cycle 内多个 guard 或 transition 查询同一个 event，已安装的 event-check function 应只在需要时被调用，并且第一次观察结果应在该 cycle 剩余部分保持稳定。

## Numeric metadata 维护纪律

生成期可完全枚举的 runtime metadata，应在公开热路径 ABI 中使用 collision-resistant generated macros 和 numeric ids。该规则适用于 state、event、abstract action、具名 `ref` action、lifecycle stage、event-check event id、current-state id、active-leaf id，以及未来同类的有限 metadata domain。

不要为了“可读性”在 `ExecutionContext`、`EventContext` 或其他热路径 contract 中保留 `const char *` 字段。只要比较域在模板渲染时已知，就不要把 `strcmp()` 重新引入 runtime selection、event-check logic 或 hook-context checks。真正可读的集成面应是 `machine.h` 中生成的 macro set，例如 `..._STATE_*`、`..._EVENT_*`、`..._ACTION_*` 和 `..._STAGE_*`。

字符串只应保留在冷路径或诊断面：

- `last_error` 和其他需要明确暴露问题的 diagnostic messages；
- `..._dsl_source()` 以及 generated comments / README text；
- `..._current_state_path()`、`..._current_state_name()` 等可选 diagnostic helpers；
- Python test adapters 将 generated ids 映射回 shared fixture schema strings；
- 生成期确实不存在稳定有限 id domain 的不可枚举输出。

新增 event-check、hook-context 或 public metadata value 时，先判断该 domain 是否在模板渲染时已经完全已知。若答案是肯定的，就生成 macro-backed integer id，并把任何字符串映射留在 generated runtime 热路径之外。

有限 domain 的 generated public identifiers 必须保留 path boundaries，不能用普通下划线拼接把 dotted path 打平。`Root.A.B` 和 `Root.A_B` 这类合法 DSL path 绝不能生成同名 public state、event、action、hook 或 event-check identifier。Canonical public macro 和 callback-table field 应使用模板里的 collision-resistant path-identifier helpers；短 alias 只有在该 generated domain 内可证明唯一、且不会碰撞 `..._STATE_COUNT`、`..._EVENT_COUNT`、`..._ACTION_COUNT`、invalid-id sentinel、stage macro 或同域 canonical id 等保留 public macro 时才允许存在。拿不准时应省略 alias，只保留 canonical path-boundary-safe macro。Canonical 有限 domain public macro 必须保留大小写和有效下划线信息；不要对 canonical state/event/action/hook/event-check identifiers 做整体大写、小写、重复下划线折叠或尾下划线裁剪。全大写或扁平化 compatibility alias 只能作为可选便利项存在，且必须在完整 generated domain 内证明唯一并且不碰撞 reserved 或 canonical public macro。Canonical public identifiers 还必须避开 C/C++ reserved identifier 形态，包括双下划线以及以下划线加大写字母开头的名称。

同一 reserved-shape 规则也适用于 root-machine ABI prefix、symbol visibility macro prefix、hook/event-check initializer macros 和 header guard。不要直接把原始 root state name 做整体大写或下划线拼接来生成这些 public names；应使用 public C identifier helpers，确保 `_Root`、`class`、`A__B` 这类合法 root name 不会在 generated header 中泄漏 C/C++ reserved public macros、typedefs、function prefixes 或 include guards。

维护这条 contract 时，下面这些检查属于常规模板 review 的一部分：

- 修改 public metadata 或 identifier helpers 前，至少生成一个同时覆盖嵌套状态、events、abstract actions、具名 `ref` actions、lifecycle stages、event checks，以及 `Root.A.B` / `Root.A_B` 这类相似 path 的模型。
- 检查 generated public ABI 和 hot path。任何生成期可枚举值如果以 `const char *` 出现、需要 `strcmp()`，或需要 per-cycle string allocation / formatting，除非明确限制在冷诊断面，否则都是设计回退。
- 测试 adapter 只能单向兼容：Python fixtures 可以把 numeric ids 映射回 schema strings 方便断言，但这层兼容不能反向要求 generated c_poll ABI 在 hooks、event checks 或 current-state checks 中携带字符串。
- Event-check metadata 也必须保持 numeric。Event-check callback 应接收 generated event 和 state ids，而不是要求集成方在 runtime 比较 event-path strings。
- 共享的 C-family metadata 规则必须同步更新 `c` 和 `c_poll`。只有差异直接来自不同 event-input model，且在两个模板手册中都写清楚时，才允许不同。
- metadata、identifier、hook-context 或 event-check 变更完成前，必须重新运行代表性的 native gates，不能依赖 slow-test skipping 作为完成依据。

## 与 `c` 的关系

`c_poll` 和 `c` 共享相同 C-family 维护约束：

- C99 / C++98 compatibility expectations；
- standard-library-only 且严格自包含的 generated runtime；
- `machine.h` 作为稳定公开集成面；
- `machine.c` 作为高性能 generated implementation；
- 无 `pyfcstm` runtime dependency，且无 third-party runtime dependency；
- 与 simulator behavior 保持 semantic alignment。

主要差异是事件输入：

- `c` 在每个 cycle 接收显式 generated event ids。
- `c_poll` 在 `cycle(machine)` 内轮询已挂载的 event-check callbacks。

本 README 必须保持自包含。链接到 `templates/c/` 可以用于对照，但不能只靠链接承载关键 `c_poll` 维护规则。

## 性能与实现策略

生成的 `machine.c` 应优先保证 FCSTM semantics 和 runtime performance。对 implementation code 来说，人工可读性是次要目标。Public header 应保持清楚稳定；generated implementation 可以在不改变可见行为的前提下使用 specialized dispatch、per-cycle event cache storage 和 direct action expansion 来提高性能。

Formatter convergence 是务实的质量门槛，不是绝对风格目标。它应当发现明显粗糙、不专业或难集成的 generated C 形态，让产物整体看起来可靠清爽。不要为了极端 formatter-only edge case 扭曲生成 C 代码，尤其不能牺牲 semantics、performance 或 compatibility；如确有例外，应窄范围记录原因。

## 语义与对齐预期

Hook-polled event 模型必须保持 FCSTM 行为：

- cold start 与 hot start；
- composite initial transition ordering；
- lifecycle enter、during、exit 和 aspect actions；
- event scoping、event identity 和 transition priority；
- guard/effect evaluation 和 speculative rollback；
- abstract hook invocation timing 和 context values；
- event-check invocation timing、context values、lazy evaluation 和 per-cycle cache stability。

Runtime tests 和 alignment tests 是行为权威。README-only 改动不应修改这些测试；runtime template 改动则必须保持它们通过。

## 维护流程

根据改动范围选择最小但足够的验证集：

1. 只改模板维护 README 时，审阅中英文章节对等，并确认没有改 generated user guide 或 source template。
2. 提交仓库改动前运行 `make rst_auto`。本 README 通常不应触发 generated RST diff。
3. 修改 `templates/c_poll/` 下任何文件后都运行 `make tpl`，包括本 README，因为 packaged built-in template archives 会包含模板源码目录。
4. 检查 packaged asset 变化。README-only 改动应刷新本地生成的 `pyfcstm/template/c_poll.zip` archive；由于 zip archives 在普通 checkout 中被 git 忽略，tracked `pyfcstm/template/index.json` 通常应保持内容等价。
5. 修改 runtime template 时，生成代表性 machine，并运行 C99 build checks、C++98 integration checks、formatter convergence checks、可用时的 sanitizer 或等价 leak checks、c_poll-specific event-check tests 和 simulator-alignment tests。

常用命令：

```bash
make rst_auto
make tpl
pytest test/template/c_poll -v
SKIP_SLOW_TESTS=1 make unittest
```

做 c_poll runtime 工作时，不能只依赖 `SKIP_SLOW_TESTS=1`；native C/C++ toolchain tests 属于真正的完成 gate。

## 语言特定验证

代表性 generated C artifacts 应满足：

```bash
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.h
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.c
cmake -S path/to/harness -B path/to/build
cmake --build path/to/build
```

Event-check tests 应包含无声明事件的 machine、单事件 machine 和多个 scoped events 的 machine，确保 complete-table rule 和 cache behavior 持续被覆盖。

## 文档分层

保持文档层次分离：

- 本文件说明如何维护 `c_poll` 模板；
- `README.md.j2` / `README_zh.md.j2` 说明如何使用某个生成 c_poll 目录；
- 根级 `templates/README.md` / `README_zh.md` 说明仓库级模板系统规则。

Generated README 应教会用户如何注册 event checks、运行 cycles、检查 state 和诊断错误，而不要求用户理解仓库 packaging internals。
