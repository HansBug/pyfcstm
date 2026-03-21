# c_poll

`c_poll` 是内置的 C99 / C++98 兼容运行时模板目标，事件输入模型改为
hook 轮询检查，而不是在每次 `cycle()` 时由外部提交 event id 集合。

模板源码内容：

- `machine.h.j2`：生成公开运行时头文件
- `machine.c.j2`：生成运行时实现
- `README.md.j2`：输出目录中的英文使用说明
- `README_zh.md.j2`：输出目录中的中文使用说明
- `README.md` / `README_zh.md`：模板维护说明

当前设计方向：

- 除事件输入模型外，尽量以 `templates/c/` 作为行为和结构基线
- 保持生成运行时兼容 `C99` 与 `C++98`
- 把生成的 `machine.c` 视为黑盒高性能运行时
- 把生成的 `machine.h` 保持为面向用户的小而稳接口层
- 对声明了事件的状态机，`cycle()` 前必须挂载完整的 event-check 表
- event-check 明确定义为只读探针：返回非零表示当前 cycle 成立，返回 `0`
  表示当前 cycle 不成立
- 已实现 event-check 的 lazy 求值与单周期缓存语义

当前模板目录阶段状态：

- Phase 1：`templates/c_poll/` 模板骨架已建立
- Phase 2：公开 API 已切换为 event-check 挂载 + `cycle(machine)`
- Phase 3：内部 event-check 缓存与判定路径改造已完成
- Phase 4：运行时测试与 alignment 覆盖已完成

实现说明：

- `machine.c` 不需要以人工友好为目标；它是生成出来的黑盒运行时代码，
  在语义正确前提下应优先考虑运行性能。
- `machine.h` 只应暴露集成方真正需要的公开操作与数据结构。
- formatter 收敛属于完成定义的一部分。生成的 C / C++ 产物应能在
  `clang-format` 下稳定收敛，并符合仓库里的模板开发约束。
