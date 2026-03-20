# c

`c` 是内置的 C99 原生运行时模板。

该模板会在目标目录中生成可直接使用的 C 运行时代码，以及面向当前状态机实例的使用说明文档。

模板源码内容：

- `machine.h.j2`：生成公开运行时头文件
- `machine.c.j2`：生成运行时实现
- `README.md.j2`：在目标目录中生成英文使用说明
- `README_zh.md.j2`：在目标目录中生成中文使用说明
- `README.md` / `README_zh.md`：模板维护者阅读的模板说明

当前特性：

- 目标语言为 C99，仅依赖常见标准库设施
- 默认输出 `machine.h`、`machine.c`、`README.md`、`README_zh.md`
- 内置状态元数据、cycle 逻辑、hot start 和 abstract hook 回调扩展点
- abstract hook 的扩展方式更贴近 C 开发者的回调表使用习惯
- 不生成额外的 handler 注册体系

## 性能演进路线

C 模板应当被视为“生成出来的黑盒运行时”。可维护性主要体现在公开的
`machine.h` 和生成出来的使用说明中；生成出来的 `machine.c` 不需要优先
照顾人工维护，而应当在保证语义正确和公开 API 稳定的前提下，尽可能追求
运行性能。

当前进度：

- Phase 1 已完成。
- Phase 2 已完成。
- Phase 3 已完成。
- Phase 4 已完成。
- 当前 C 模板已经切换到 id-only API，并且混合 event-set 后端已接入。
- 当前热路径已经切换到状态专用分发实现，validation / rollback 路径也已完成减拷贝优化，
  现有 C 模板回归测试已通过。

### Phase 1：移除热路径里的可避免开销

- [x] 从生成出来的公开 C API 中移除字符串事件提交方式。
- [x] 为 transition 直接生成 `event_id` 常量，而不是在运行时持有
      `event_path` 再做查找。
- [x] 将 `cycle()` 直接改为接收整数事件 id。
- [x] 在 `machine.h` 中生成公开的事件 id 宏，调用方无需再做字符串解析。
- [x] 从 hot start API 中移除字符串状态查找，改为直接接收 state id。
- [x] 在 `machine.h` 中生成公开的状态 id 宏，方便 hot start 等性能敏感路径
      直接使用。
- [x] 将当前每次状态推进都会付费的小型 helper 尽量内联或直接展开生成。

### Phase 2：围绕 id 输入改造事件集合表示

- [x] 让基于整数 id 的 `cycle()` 成为头文件里唯一暴露的事件输入方式。
- [x] 替换当前线性的 event-set 判定逻辑，并且不能因为采用位运算就引入一个
      很小的固定事件上限。
- [x] 当状态机总事件数较小或中等时，优先使用紧凑 bitset 作为快速路径。
- [x] 当事件空间较大时，退化为去重后的整数 id 数组，而不是强行只用 bitset。
- [x] 尽量把事件集合需要的临时存储做成 machine 内可复用 scratch 区，避免
      每个 cycle 都做堆分配。

Phase 2 说明：

- 纯 bitset 的优点是快，但成本直接和“总事件空间大小”绑定。
- 纯数组的优点是内存小，但成员判断会退化成和“本轮提交事件数”线性相关。
- 更合理的方向是做“混合表示”，根据生成状态机的元数据和本轮事件规模选后端：
  - 事件空间小或较密集：bitset
  - 事件空间较大，但每轮提交事件很少：排序/去重后的整数数组
  - 更大的稀疏场景：开放寻址哈希集合或类似常数时间成员判断结构
- 这样既保住小状态机的极致快路径，也避免因为只靠位图而引入僵硬的事件数量上限。

### Phase 3：把表驱动执行改造成专用生成代码

- [x] 不再让 `StateInfo` / `TransitionInfo` 这类表扫描承担 cycle 热路径的主执
      行逻辑。
- [x] 为每个状态生成专用的 transition 分发函数，而不是扫描 transition id 数组。
- [x] 为每个状态生成专用的 `enter`、`during`、`exit` 和 init 分发逻辑。
- [x] concrete action 在生成期直接展开，不再通过 `ActionInfo` 间接调度。
- [x] abstract hook 保留为少数仍需间接调用的扩展点，而且只有用户真的装了 hook
      时才付这部分成本。
- [x] `.h` 继续保持小而稳定，`.c` 则可以更激进地朝专用化方向优化。

### Phase 4：专门优化 validation 和回滚路径

- [x] 先保证回滚语义正确：cycle 失败后必须恢复到上一次已提交状态。
- [x] 保留 speculative validation 的语义，但减少 validation 阶段对通用解释器式
      执行骨架的依赖。
- [x] 在收益足够明显的地方，用专用热路径和减拷贝执行替换通用验证骨架的关键部分。
- [x] 专用化后重新确认 stack-depth 和 DFS-step 这两类安全限制仍然成立。
- [x] 为嵌套复合状态、兄弟状态切换、退出到父状态、abstract hook 交互等关键场
      景补强回归测试。

### 验收标准

- [x] 生成出来的 `machine.h` 保持小而面向使用者。
- [x] 生成出来的 `machine.c` 可以明确偏向运行性能，而不必优先照顾人工可读性。
- [x] 生成出来的公开 API 直接使用整数 id 提交事件。
- [x] `machine.h` 暴露事件 id 和状态 id 宏，使用方不需要依赖运行时字符串查找。
- [x] 事件处理不能因为只使用位运算而引入一个很小的固定上限。
- [x] 现有运行语义、回滚行为和 hook 语义保持正确。

## 基准记录

下面这组基准用于对比当前 Phase 4 运行时和 Phase 1 之前的老版本。

实验步骤：

- 基线版本：`99eb3f1c`（`Document id-only C runtime performance roadmap`），
  这是 Phase 1 实现之前的最后一个版本，已通过临时 worktree checkout 出来。
- 当前版本：本地 `templates/c/` 下的 Phase 4 模板状态。
- 测试模型：一个中等复杂度的“电梯控制系统” FCSTM，包含嵌套的
  `Service -> Door / Motion / Inspection` 复合状态、init transition、
  兄弟状态切换、退出到父状态路径，以及一个通过
  `Idle -> Inspection :: Inspect` 且缺少 `AuthOk` 触发的 validation
  失败路径。
- 老版本提交流程：字符串事件接口
  `cycle(machine, const char *const *events, ...)`。
- 新版本提交流程：id-only 事件接口
  `cycle(machine, const EventId *event_ids, ...)`。
- 编译参数：`cc -O3 -DNDEBUG -std=c99`。
- 计时方式：基准程序内部用 `clock()` 统计 CPU 时间，重复运行若干轮，比较
  mean / median 耗时。

负载设计：

- `mixed`：在同一个状态机上混合施加开机、运动、门控、巡检等事件。
- `validation_heavy`：以大量失败的 `Inspect` 尝试为主，并周期性插入
  `AuthOk` / `ExitInspect`，重点压测 speculative validation 和回滚路径。

结果摘要：

- `mixed`，`4,000,000` 次 cycle，`3` 轮：
  - Phase 1 前老版本 mean：`1.0105s`
  - 当前 Phase 4 mean：`0.1574s`
  - mean 加速比：`6.42x`
  - median 加速比：`7.25x`
- `validation_heavy`，`8,000,000` 次 cycle，`3` 轮：
  - Phase 1 前老版本 mean：`2.3005s`
  - 当前 Phase 4 mean：`0.2399s`
  - mean 加速比：`9.59x`
  - median 加速比：`9.75x`

结果解读：

- 从 Phase 1 前老运行时到当前 Phase 4 运行时，端到端性能提升明显且稳定。
- `validation_heavy` 的加速更大，说明 id-only API、状态专用分发，以及
  validation / rollback 路径的减拷贝优化，确实命中了过去最主要的性能热点。
