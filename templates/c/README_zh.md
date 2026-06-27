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

## 资源生命周期与泄漏策略

Generated C runtime 可能被嵌入长期稳定运行的控制系统，因此内存和资源 ownership 是 runtime correctness 问题，不是可选优化。Generated API 应保持 ownership 简单清楚：`..._create()` 负责 allocation，`..._destroy()` 负责释放，`..._init()` 和 `..._hot_start()` 重置 runtime state 时不能泄漏，hook registration 只保存调用方拥有的指针而不接管 ownership。Runtime 改动必须保持这个 contract。

修改 `machine.c.j2` 或 `machine.h.j2` 中与 allocation 相关的部分时，在工具可用的情况下，至少用一个代表性 generated harness 跑 AddressSanitizer / LeakSanitizer、valgrind 或等价平台工具。Harness 应覆盖 create/destroy、cold start、hot start、normal cycles、eventful cycles、hook installation，以及与改动相关的 error/rollback paths。若发现明显早于当前改动的 leak，应记录复现方式并拆给专门修复，而不是静默忽略。

## 部署剖面维护纪律

`c` 模板有三种部署剖面，维护时必须同步考虑：

| 剖面 | 公开形态 | 必要检查 |
| --- | --- | --- |
| 默认宿主 C99 | `..._create()`、`..._create_uninitialized()` 和 `..._destroy()` 可用。 | 既有 create/destroy、hot-start、hook 和共享语义对齐测试继续通过。 |
| 调用方拥有对象 | 调用方自己分配 `Machine` 存储，并使用 `..._init(&machine)` / `..._hot_start(...)`。 | CMake 驱动的本机 harness 覆盖栈上存储、静态存储、hook 安装、事件 cycle、hot start 和失败路径，且不依赖 heap helpers。 |
| 无堆剖面 | `PYFCSTM_GENERATED_NO_HEAP` 移除 heap API 声明/定义，以及只服务于 `calloc/free` 的 `<stdlib.h>` include。 | 头文件预处理或生成文件检查证明 heap API 声明消失；link 或 symbol 检查证明不引用 `calloc/free`。 |

`PYFCSTM_GENERATED_NO_HEAP` 是“符号是否存在”的契约。模板代码应使用
`#if defined(PYFCSTM_GENERATED_NO_HEAP)` 或等价 `#ifdef`，不要使用
`#if PYFCSTM_GENERATED_NO_HEAP`。文档推荐消费端写法为
`-DPYFCSTM_GENERATED_NO_HEAP`；如果外部构建写成
`-DPYFCSTM_GENERATED_NO_HEAP=1`，也必须选择同一个无堆剖面。

这份契约有三侧必须同步：

- `machine.h.j2`：无堆剖面下移除公开 heap 声明；
- `machine.c.j2`：无堆剖面下移除 heap 实现和 `<stdlib.h>` include；
- 生成 README 示例：CMake 消费端使用 `PUBLIC` / `INTERFACE` 传播宏，或者所有包含
  `machine.h` 的最终 target 都能看到同一定义。

模板本机测试必须继续使用 CMake 作为构建驱动。用户 README 可以展示 gcc / clang 风格
单命令示例，但 pytest 中不要新增一套手写宿主编译器调度层。



### 原生工具链矩阵维护纪律

原生工具链 pytest 矩阵是 `c` 生成产物的跨实现证据门禁。它使用与仿真器和模板对齐测试相同的共享语义用例，只是把后端换成具体编译器 profile。Profile 名称应描述工具链行为，例如 `linux-gcc-o2`、`linux-aarch64-gcc-o2`、`arm-none-eabi-gcc-o2` 或 `linux-cppcheck`；不要把路线代号、PR 名称或流程阶段写进代码标识符、测试 id、pydoc 或 runtime message。

公开矩阵分三层：

| 层级 | 示例 | 含义 |
| --- | --- | --- |
| 可运行宿主 / 仿真 profile | Linux GCC/Clang 优化等级、Linux 32 位、AArch64+QEMU、macOS AppleClang、Windows MinGW/MSVC/clang-cl、sanitizer profile | 编译 standalone harness，运行每个共享语义用例，并比较公开观察面。 |
| compile-only profile | ARM bare-metal GCC 和后续专有自托管工具链 | 编译每个 generated `machine.c`、`harness.c` 和 C++ header probe 到非空目标文件；不要把它包装成 runtime evidence。 |
| analyze-only profile | `cppcheck`、`clang-tidy` | 扫描每个 generated runtime 与 harness，并保留 report-only artifacts；工具崩溃、解析失败和报告缺失仍然是失败。 |

扩展矩阵时，profile registry、workflow 触发列表、artifact 预期和本维护手册必须一起更新。公共 GitHub-hosted profile 缺工具时必须失败，不能静默 skip。授权或厂商 profile 应保持 manual / self-hosted，除非显式配置 runner，否则不得阻塞公共 CI。

### 部署安全表述纪律

C-family 部署工作是 generated control state-machine code 的工程基线，不是认证包。Maintainer README 和 generated README 可以说明该模板支持 C99、C++98-compatible integration、调用方拥有对象、无堆剖面、共享语义对齐和原生工具链矩阵证据。它们不能说或暗示 generated output 已经满足 MISRA、AUTOSAR、DO-178C、IEC 61508、ISO 26262 或其他 safety standard ready。

下游职责必须明确保留给消费项目。板级支持包、链接脚本、中断策略、调度器集成、静态分析 waiver 处理、编码规则签核和认证证据都属于 consumer project。模板文档应帮助该项目找到正确的集成检查点，而不是假装完成这些下游流程。

数值风险表述必须绑定目标。Inspect diagnostics 说的是默认 C/C++ deployment profile；不能把它们写成 target-independent FCSTM model error，也不能写成 Python 模板风险。后续 BitVec、BMC、fixed-point、numeric-profile、checked-arithmetic 或 generated failure channel 工作属于 verify 和 codegen 设计路线，不属于 README-only 模板补丁。

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

## Numeric metadata 维护纪律

生成期可完全枚举的 runtime metadata，应在公开热路径 ABI 中使用 collision-resistant generated macros 和 numeric ids。该规则适用于 state、event、abstract action、具名 `ref` action、lifecycle stage、current-state id、active-leaf id，以及未来同类的有限 metadata domain。

不要为了“可读性”在 `ExecutionContext`、事件提交或其他热路径 contract 中保留 `const char *` 字段。只要比较域在模板渲染时已知，就不要把 `strcmp()` 重新引入 runtime selection 或 hook-context checks。真正可读的集成面应是 `machine.h` 中生成的 macro set，例如 `..._STATE_*`、`..._EVENT_*`、`..._ACTION_*` 和 `..._STAGE_*`。

字符串只应保留在冷路径或诊断面：

- `last_error` 和其他需要明确暴露问题的 diagnostic messages；
- `..._dsl_source()` 以及 generated comments / README text；
- `..._current_state_path()`、`..._current_state_name()` 等可选 diagnostic helpers；
- Python test adapters 将 generated ids 映射回 shared fixture schema strings；
- 生成期确实不存在稳定有限 id domain 的不可枚举输出。

新增 context field 或 public metadata value 时，先判断该 domain 是否在模板渲染时已经完全已知。若答案是肯定的，就生成 macro-backed integer id，并把任何字符串映射留在 generated runtime 热路径之外。

有限 domain 的 generated public identifiers 必须保留 path boundaries，不能用普通下划线拼接把 dotted path 打平。`Root.A.B` 和 `Root.A_B` 这类合法 DSL path 绝不能生成同名 public state、event、action、hook 或 event-check identifier。Canonical public macro 和 callback-table field 应使用模板里的 collision-resistant path-identifier helpers；短 alias 只有在该 generated domain 内可证明唯一、且不会碰撞 `..._STATE_COUNT`、`..._EVENT_COUNT`、`..._ACTION_COUNT`、invalid-id sentinel、stage macro 或同域 canonical id 等保留 public macro 时才允许存在。拿不准时应省略 alias，只保留 canonical path-boundary-safe macro。Canonical 有限 domain public macro 必须保留大小写和有效下划线信息；不要对 canonical state/event/action/hook/event-check identifiers 做整体大写、小写、重复下划线折叠或尾下划线裁剪。全大写或扁平化 compatibility alias 只能作为可选便利项存在，且必须在完整 generated domain 内证明唯一并且不碰撞 reserved 或 canonical public macro。Canonical public identifiers 还必须避开 C/C++ reserved identifier 形态，包括双下划线以及以下划线加大写字母开头的名称。

同一 reserved-shape 规则也适用于 root-machine ABI prefix、symbol visibility macro prefix、hook/event-check initializer macros 和 header guard。不要直接把原始 root state name 做整体大写或下划线拼接来生成这些 public names；应使用 public C identifier helpers，确保 `_Root`、`class`、`A__B` 这类合法 root name 不会在 generated header 中泄漏 C/C++ reserved public macros、typedefs、function prefixes 或 include guards。

维护这条 contract 时，下面这些检查属于常规模板 review 的一部分：

- 修改 public metadata 或 identifier helpers 前，至少生成一个同时覆盖嵌套状态、events、abstract actions、具名 `ref` actions、lifecycle stages，以及 `Root.A.B` / `Root.A_B` 这类相似 path 的模型。
- 检查 generated public ABI 和 hot path。任何生成期可枚举值如果以 `const char *` 出现、需要 `strcmp()`，或需要 per-cycle string allocation / formatting，除非明确限制在冷诊断面，否则都是设计回退。
- 测试 adapter 只能单向兼容：Python fixtures 可以把 numeric ids 映射回 schema strings 方便断言，但这层兼容不能反向要求 generated C ABI 在 hooks、event submission 或 current-state checks 中携带字符串。
- 共享的 C-family metadata 规则必须同步更新 `c` 和 `c_poll`。只有差异直接来自不同 event-input model，且在两个模板手册中都写清楚时，才允许不同。
- metadata、identifier 或 hook-context 变更完成前，必须重新运行代表性的 native gates，不能依赖 slow-test skipping 作为完成依据。

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
5. 修改 runtime template 时，生成代表性 machine，并运行 C99 build checks、C++98 integration checks、formatter convergence checks、可用时的 sanitizer 或等价 leak checks，以及 simulator-alignment tests。

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
