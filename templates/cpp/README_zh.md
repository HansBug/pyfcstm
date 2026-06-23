# cpp 模板维护手册

`cpp` 是实验性的 C++ 内置模板骨架。它生成与 `templates/c/` 完全一致的
C99 执行核心，同时额外生成最小 `machine.cpp` / `machine.hpp` 包装文件。完整
C++ facade API 不在本阶段实现，留给后续 wrapper 工作。

本文件面向 `templates/cpp/` 维护者。它会被 renderer 忽略，不会复制到生成目录；
生成物用户手册来自 `README.md.j2` / `README_zh.md.j2`。

## 源码布局

| 模板源码 | 维护职责 | 生成输出 |
| --- | --- | --- |
| `machine.h.j2` | 文件级 symlink 到 `../c/machine.h.j2` | `machine.h` |
| `machine.c.j2` | 文件级 symlink 到 `../c/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | 最小 C++ wrapper header 骨架 | `machine.hpp` |
| `machine.cpp.j2` | 最小 C++ wrapper implementation 骨架 | `machine.cpp` |
| `README.md.j2` | 英文生成物用户手册 | `README.md` |
| `README_zh.md.j2` | 中文生成物用户手册 | `README_zh.md` |
| `config.yaml` | 独立 renderer 配置，并显式 import C-family helper | 不复制 |
| `template.json` | 内置模板 metadata | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | renderer 不复制，但会进入模板 archive |

## 维护纪律

C core symlink 只用于仓库源码复用。打包后的 `cpp.zip` 必须包含普通文件，不能保留
symlink 条目，并且在没有 `templates/c/` 的安装环境中仍然自包含。

`to_c_identifier`、`to_c_path_identifier`、`render_c_action_body` 等 C-family
helper 由本模板 `config.yaml` 显式加载。不要把这些 helper 加回默认 renderer 环境。

完整 wrapper 落地前，`machine.cpp.j2` 和 `machine.hpp.j2` 应保持小而明确，兼容
C++98，不使用 exception / RTTI，也不要求 STL 容器。运行时行为仍由生成的 C core 承担。
