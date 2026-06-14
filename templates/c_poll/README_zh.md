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
