# c 模板维护手册

`c` 是内置原生 C runtime 模板。它会生成自包含的 C99 状态机运行时，并提供面向 C 用户和 C++98 集成路径的公开头文件。

本文件是 `templates/c/` 的维护者手册。它会被 renderer 忽略，不会复制到生成目录。生成目录里的用户手册来自 `README.md.j2` / `README_zh.md.j2`。

## 目标与非目标

当主要需求是生成运行时性能、可预测 C 集成和小而稳定的公开 C API 时，应使用该模板。

生成实现应被视为黑盒运行时代码。需要改变行为的用户应修改 FCSTM DSL 并重新生成。长期人工维护应集中在 `machine.h`、生成 README 和模板源码 review 上，而不是手改生成出来的 `machine.c`。

该模板不是通向 `pyfcstm` 的依赖桥。生成的 C 产物必须在没有 Python package 和任何第三方 runtime library 的情况下运行。

## 源码布局与生成产物

| 模板源码 | 维护职责 | 生成产物 |
| --- | --- | --- |
| `machine.h.j2` | 公开 C 集成面模板 | `machine.h` |
| `machine.c.j2` | 高性能 generated runtime implementation 模板 | `machine.c` |
| `README.md.j2` | 英文生成物用户手册 | `README.md` |
| `README_zh.md.j2` | 中文生成物用户手册 | `README_zh.md` |
| `config.yaml` | renderer 配置、C 语句渲染、helper 命名和 ignore 规则 | 不复制 |
| `template.json` | 内置模板 metadata | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | renderer 不复制，但会进入 packaged template archives |

`config.yaml` 会在渲染输出时忽略 `README.md`、`README_zh.md` 和 `template.json`。但 `make tpl` 仍会打包完整模板源码目录，因此修改本手册后必须通过 `make tpl` 刷新并验证本地生成的 `pyfcstm/template/c.zip`。该 archive 在普通 checkout 中被 git 忽略；setup 和 packaging 命令会从源码重新生成它。

## 兼容性与运行时依赖边界

生成的 C 产物默认应保持以下约束：

- C99 implementation path。
- 生成公开头文件和代表性 harness 保持 C++98-compatible integration path。
- runtime 只依赖标准库。
- 不依赖 `pyfcstm`、Python、生成期 helper 或第三方 C libraries。
- 尽量保持广泛编译器和平台兼容，包括实践中可行的较老 Windows C 环境。

生成代码可以在 runtime 需要时使用长期稳定的 C 标准头，例如 `<stddef.h>`、`<math.h>`、`<stdarg.h>`、`<stdio.h>`、`<stdlib.h>` 和 `<string.h>`。

## 公开集成面

`machine.h` 是公开集成面，应保持小、清楚且稳定。它负责：

- 生成 machine struct type；
- persistent variable struct definitions；
- public state-id 和 event-id macros；
- 通过 `..._cycle(machine, event_ids, event_count)` 进行整数事件提交；
- 通过 generated state ids 和完整变量快照进行 hot start；
- abstract hook callback signatures 和 hook table；
- current-state、variable、ended-state、last-error 和 embedded-model accessors。

`machine.c` 是 generated implementation。下游集成者应将其中的内部 metadata、helper functions、stack frames、validation state 和 scratch storage 视为私有实现细节。

## 性能与实现策略

`machine.c` 的第一优先级是 runtime performance 和 FCSTM semantic correctness。对 generated implementation code 来说，人工可读性是次要目标。注释和结构应足够支撑诊断和 review，但在专用生成路径更快且语义等价时，不要把生成实现退回到人工维护友好的解释器式结构。

当前稳定设计包括：

- id-only public event input，不做运行时字符串事件查找；
- 在 `machine.h` 中公开 event-id 和 state-id macros；
- hybrid event-set backend，在小型和密集事件空间中保持快速，同时避免固定的小事件数量上限；
- 用 state-specialized dispatch 进行 transition selection 和 lifecycle execution；
- concrete action blocks 在生成代码中直接展开；
- abstract hooks 保留为用户定义的少数间接 extension points；
- speculative validation 和 rollback 尽可能减少复制；
- C/C++ keyword-safe generated identifiers；
- 公开 64-bit integer alias strategy，避免把裸 `long long` 作为唯一 ABI 写法。

这些是稳定设计事实，不是临时开发计划。不要重新把临时里程碑列表或里程碑标题作为 README 主体结构。

## 性能证据

一组历史 benchmark 曾用包含嵌套 composites、initial transitions、sibling transitions、exit-to-parent paths 和 validation rollback 的中等复杂度电梯控制模型，对比当前专用化 C runtime 设计和更早的字符串提交 runtime。

该 benchmark 使用 `cc -O3 -DNDEBUG -std=c99`，并测量两类 workload：

| Workload | Cycles | 稳定观察 |
| --- | ---: | --- |
| `mixed` | 4,000,000 | mean speedup 约为 `6.42x`；median speedup 约为 `7.25x`。 |
| `validation_heavy` | 8,000,000 | mean speedup 约为 `9.59x`；median speedup 约为 `9.75x`。 |

结果支持当前设计方向：id-only event input、specialized state dispatch 和 reduced-copy validation / rollback 显著改善了 generated C runtime 中占主导的热路径成本。

Benchmark 记录是维护决策证据，不是 semantic regression tests 的替代品。不要为了 microbenchmark 放松 correctness、rollback 或 hook behavior。

## 语义与对齐预期

C 模板必须保持 FCSTM runtime contract：

- cold start 与 hot start；
- composite initial transition ordering；
- lifecycle enter、during、exit 和 aspect actions；
- event scoping、event identity 和 transition priority；
- guard/effect evaluation 和 speculative rollback；
- abstract hook invocation timing 和 read-only execution context。

C runtime tests 和 alignment tests 是行为权威。模板 README 改动不改变这些测试；runtime template 改动则必须保持它们通过。

## 维护流程

根据改动范围选择最小但足够的验证集：

1. 只改模板维护 README 时，审阅中英文章节对等，并确认没有改 generated user guide 或 source template。
2. 提交仓库改动前运行 `make rst_auto`。本 README 通常不应触发 generated RST diff。
3. 修改 `templates/c/` 下任何文件后都运行 `make tpl`，包括本 README，因为 packaged built-in template archives 会包含模板源码目录。
4. 检查 packaged asset 变化。README-only 改动应刷新本地生成的 `pyfcstm/template/c.zip` archive；由于 zip archives 在普通 checkout 中被 git 忽略，tracked `pyfcstm/template/index.json` 通常应保持内容等价。
5. 修改 runtime template 时，生成代表性 machine，并运行 C99 build checks、C++98 integration checks、formatter convergence checks 和 simulator-alignment tests。

常用命令：

```bash
make rst_auto
make tpl
pytest test/template/c -v
SKIP_SLOW_TESTS=1 make unittest
```

做 C runtime 工作时，不能只依赖 `SKIP_SLOW_TESTS=1`；native C/C++ toolchain tests 属于真正的完成 gate。

## 语言特定验证

代表性 generated C artifacts 应满足：

```bash
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.h
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.c
cmake -S path/to/harness -B path/to/build
cmake --build path/to/build
```

Formatter convergence 是务实的质量门槛，不是绝对风格目标。它应当发现明显粗糙、不专业或难集成的 generated C 形态，让产物整体看起来可靠清爽。不要为了极端 formatter-only edge case 扭曲生成 C 代码，尤其不能牺牲 semantics、performance 或 compatibility；如确有例外，应窄范围记录原因。

## 与 `c_poll` 的关系

`c` 和 `c_poll` 共享 C-family 兼容性和 self-contained runtime policy，但事件输入模型不同：

- `c` 通过公开 cycle API 在每个 cycle 接收显式 generated event ids。
- `c_poll` 通过已安装的 event-check callbacks 询问每个 generated event 在当前 cycle 是否活跃。

不要只通过链接把 `c` 的关键维护要求转移给 `c_poll`。每个模板 README 都必须保持自包含。

## 文档分层

保持文档层次分离：

- 本文件说明如何维护 `c` 模板；
- `README.md.j2` / `README_zh.md.j2` 说明如何使用某个生成 C 目录；
- 根级 `templates/README.md` / `README_zh.md` 说明仓库级模板系统规则。

Generated README 应帮助下游用户在不理解模板打包内部机制的前提下 build 并运行生成的 C machine。
