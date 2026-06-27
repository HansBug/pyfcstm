# cpp_poll 模板维护手册

`cpp_poll` 是早期一等内置 C++ poll-style 模板。它会生成与 `templates/c_poll/`
相同的 C poll 执行 core，并额外生成 `machine.cpp` / `machine.hpp` wrapper 文件，
提供覆盖公开 C poll API 的 C++98-compatible facade。

本文件是 `templates/cpp_poll/` 的模板维护文档。renderer 会忽略它，生成输出中不会复制它。
面向生成物用户的说明来自 `README.md.j2` / `README_zh.md.j2`。

## 源码布局

| 模板源文件 | 维护职责 | 生成输出 |
| --- | --- | --- |
| `machine.h.j2` | 指向 `../c_poll/machine.h.j2` 的文件级 symlink | `machine.h` |
| `machine.c.j2` | 指向 `../c_poll/machine.c.j2` 的文件级 symlink | `machine.c` |
| `machine.hpp.j2` | C++ poll-wrapper header | `machine.hpp` |
| `machine.cpp.j2` | C++ poll-wrapper implementation | `machine.cpp` |
| `README.md.j2` | 英文生成物使用说明 | `README.md` |
| `README_zh.md.j2` | 中文生成物使用说明 | `README_zh.md` |
| `config.yaml` | 独立 renderer 配置，显式 import C-family helpers | 不复制 |
| `template.json` | built-in template metadata | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | renderer 不复制，但会进入 packaged template archives |

## 维护纪律

`template.json` 在 C++ poll wrapper surface 仍处于早期推广期时会有意保留
`experimental: true`。这个标记表示“早期一等模板”状态，而不是未实现模板：packaging、
wrapper API smoke tests、共享语义 fixture 对齐和原生工具链矩阵覆盖都属于预期维护契约。

C poll core symlink 只是仓库源码层面的复用机制。打包出的 `cpp_poll.zip` 必须包含普通文件，
不能包含 symlink entry；即使解压环境没有 `templates/c_poll/`，也必须自包含可用。

C-family helper 必须由当前模板的 `config.yaml` 加载。不要把这些 helper 放回全局默认
renderer environment。

`machine.cpp.j2` 和 `machine.hpp.j2` 必须保持 C++98-compatible，不依赖异常、RTTI
或 STL 容器。运行时行为必须继续位于生成出的 C poll core 中；wrapper 应只调用
`machine.h` 公开 C poll API，不应直接查看运行时拥有的结构体字段。

共享语义 fixture 对齐必须测试 `machine.hpp` / `machine.cpp` wrapper 表面。fixture
harness 可以编译 `machine.c` 并把它链接进最终可执行文件，但测试入口必须是 C++ wrapper：
harness 源码只应直接 include `machine.hpp`，用 `Wrapper::...` aliases 访问生成运行时
类型，并调用 wrapper public methods，而不是直接调用 `...Machine_*` C 函数。

原生工具链检查应让 `cpp_poll` 和 `c`、`c_poll`、`cpp` 一起进入仓库级矩阵。C++
harness 可以链接生成出的 C poll core，但被测试的公开集成面仍然是 C++ poll wrapper。
Generated README 中的构建示例需要和矩阵实际覆盖的 profile 保持一致，包括 CMake、
GCC/G++、Clang/Clang++、no-exception、no-RTTI 以及适用时的 no-heap 形式。

部署安全表述沿用 `templates/c_poll/` 的 C-family 边界。该模板提供的是非认证工程基线，不是认证包：
C99 poll core、C++98 wrapper、调用方拥有对象与无堆集成、完整 event-check 安装、共享语义对齐和原生工具链矩阵证据。不要把 generated output 描述为 MISRA、AUTOSAR、DO-178C、IEC 61508、ISO 26262 或其他认证 ready。Numeric inspect warning 是默认 C/C++ deployment-profile diagnostics，不是 target-independent FCSTM model error，也不是 Python 模板风险。后续 BitVec、BMC、fixed-point、numeric-profile、checked-arithmetic 或 generated failure channel 工作属于 verify 和 codegen 设计路线。

生成 README 示例属于模板契约。修改 wrapper API 或编译说明时，需要同步更新两份生成
README 模板，并通过模板测试验证代表性命令。
