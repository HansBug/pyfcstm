# `c_poll` 内置模板设计文档

关联分支：

- `dev/ctemp_poll`

关联 PR：

- https://github.com/HansBug/pyfcstm/pull/73

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-21 | 初始版本，整理 `c_poll` 模板的命名、目标、运行时语义、API 方向、phase 拆分、checklist 与风险约束 | Codex |

---

## 1. 背景与目标

当前仓库已经有成熟的内置 `c` 模板：

- 目标兼容 `C99` 与 `C++98`
- 运行时语义已与 `SimulationRuntime` 做对齐测试
- 生命周期 abstract action 已经通过 hook 暴露给用户
- 事件输入模式为：调用方在每个 `cycle()` 中显式传入 event id 集合

这次新增的 `c_poll` 模板，不是再做一个完全不同的状态机框架，而是在现有 `c` 模板的骨架上，派生一个**事件输入模型不同**的 built-in template。

`c_poll` 的核心变化只有一件事：

- 事件不再由调用方在 `cycle()` 时传入
- 每个 DSL event 都生成为一个事件检查 hook
- 运行时在状态迁移判定时查询对应 hook
- hook 返回真时视为该事件在本周期成立，否则视为不成立

因此，`c_poll` 的设计目标应明确为：

1. 以现有 `templates/c/` 为蓝本，而不是从零重写一套新 runtime
2. 保持 `C99` / `C++98` 兼容范围不变
3. 保持状态机语义、hot start、rollback、validation、安全限制等核心行为与现有 `c` 模板一致
4. 仅替换“事件输入层”的公开 API 和内部判定路径
5. 让事件源接入方式更适合轮询式主循环、嵌入式、PLC 风格 scan loop、硬件寄存器采样等场景

---

## 2. 模板命名

最终命名定为：

- `c_poll`

命名理由：

- `c`：明确它仍然是 C 运行时模板系谱中的一个变体
- `poll`：明确表达事件来源是“轮询 / 检查”，而不是“外部提交 event 集合”

不采用其他候选名的原因：

- `c_hook`：容易与现有 abstract action hooks 混淆
- `c_eventhook`：语义清楚，但偏长，作为 built-in template 名称不够简洁
- `c_scan`：偏领域化，容易让人误以为强绑定 PLC 语义

---

## 3. 总体设计原则

`c_poll` 必须遵循以下原则：

1. **最小语义偏移**
   除事件输入方式外，应尽量复用现有 `c` 模板的运行时结构、状态推进逻辑、热启动逻辑、错误处理与安全限制。

2. **事件检查只读化**
   事件 hook 的职责是“报告当前周期该事件是否成立”，而不是直接修改状态机持久变量。

3. **单周期结果稳定**
   同一周期内，对同一个 event 的判定结果必须稳定一致，不能因为 validation / rollback / repeated selection 而变化。

4. **与现有 hook 体系并存**
   `c_poll` 仍需保留现有 abstract lifecycle hook 体系，事件 hook 只是新增的另一套扩展面。

5. **保持目标用户心智简单**
   用户应当能够一眼区分：
   - abstract lifecycle hooks：扩展动作行为
   - event check hooks：报告事件是否发生

6. **优先黑盒运行时**
   模板维护者可以让生成的 `machine.c` 偏向性能和专门化；但头文件、README 与公开 API 必须保持清晰可用。

---

## 4. 与现有 `c` 模板的关系

`c_poll` 应视为 `c` 模板的 sibling template，而不是在 `c` 模板内加一个沉重模式开关。

建议组织方式：

- 新增 `templates/c_poll/`
- 初始实现尽量从 `templates/c/` 复制并收敛
- 在后续需要时，再逐步抽取共用说明或共用生成片段

不建议在 `templates/c/` 中通过大量 `if poll_mode` 之类逻辑复用单一模板，原因如下：

- 两者公开 API 已显著不同
- README 与接入示例显著不同
- 事件判定语义不同，需要独立测试套件表达
- 将两种 runtime public contract 混在一个模板里，会显著增加维护复杂度

因此，推荐策略是：

- 先接受少量模板重复，换取语义清晰
- 当 `c_poll` 语义稳定后，再考虑是否抽公共片段

---

## 5. 运行时语义设计

## 5.1 现有 `c` 模板语义

现有 `c` 模板的事件语义可概括为：

- 调用方每个周期向 `cycle(machine, event_ids, event_count)` 传入一组事件
- 运行时先把事件归一化为本周期固定 `event_set`
- 后续 transition select、init transition、validation 和 rollback 都读取同一份 `event_set`

这个设计有一个非常重要的性质：

- **同一个周期里，事件输入是稳定的**

这也是 `c_poll` 必须保住的性质。

## 5.2 `c_poll` 的目标语义

在 `c_poll` 中，事件输入改为：

- 每个 event 对应一个 `check_xxx` hook
- 当运行时需要判断某个 transition 的 event 是否成立时，查询对应 hook
- hook 返回非零表示事件成立，返回零表示事件不成立

但是实现上**不能**简单做成“每次判定都直接调用 hook”，因为现有 runtime 中：

- 可能先做 speculative validation
- validation 期间可能再次执行 transition selection
- 某个 transition 或 event 可能在一个周期内被查询多次

如果事件 hook 每次都重新调用，就会引入以下风险：

- 同一周期多次读取到不一致值
- validation 阶段和提交阶段看到不同事件结果
- 带副作用的用户 hook 被重复触发

因此，`c_poll` 必须采用：

- **单周期 lazy + cache**

即：

1. 周期开始时，事件缓存处于“未求值”状态
2. 某个 event 第一次被访问时，调用一次对应 `check_xxx` hook
3. 把该结果写入本周期缓存
4. 本周期后续对该 event 的所有访问都复用缓存值
5. 周期结束后，缓存失效，下一个周期重新按需求值

这是 `c_poll` 设计里的硬约束，不是可选优化。

## 5.3 事件 hook 的副作用约束

建议文档、头文件与 README 中都明确以下规则：

- 事件 hook 应视为只读 probe
- 事件 hook 不应修改状态机持久变量
- 事件 hook 最好也不要依赖“被调用次数”这种不稳定行为
- `c_poll` 会保证单周期内每个 event 最多求值一次，但用户不应把这个机制当作业务逻辑消费接口

第一版不建议引入：

- consume / ack 语义
- “查询即清除” 语义
- 自动边沿检测语义

第一版先把模型收敛为：

- **电平式 / 条件式事件成立检查**

如果后续需要边沿或消费语义，应单独设计，而不是暗中塞进 `check_xxx`。

---

## 6. 公开 API 方向

## 6.1 现有 `c` 模板 API 特征

现有模板的重要公开 API 包括：

- `..._cycle(machine, event_ids, event_count)`
- `..._set_hooks(machine, hooks, user_data)`，用于 abstract lifecycle hooks

## 6.2 `c_poll` 的建议 API

`c_poll` 建议拆成两类 hook 表：

1. lifecycle hooks
2. event check hooks

原因：

- abstract action hook 与 event check hook 的职责完全不同
- 如果混在同一个 struct 中，命名与用户理解都会变乱
- 分开后更利于文档、IDE completion 与测试组织

建议公开 API 方向如下：

```c
typedef void (*RootMachineHookFn)(
    RootMachine *machine,
    const RootMachineExecutionContext *ctx,
    void *user_data
);

typedef int (*RootMachineEventCheckFn)(
    RootMachine *machine,
    const RootMachineEventContext *ctx,
    void *user_data
);

typedef struct RootMachineHooks {
    RootMachineHookFn on_Root_Init;
    RootMachineHookFn on_Root_System_A_Enter;
} RootMachineHooks;

typedef struct RootMachineEventChecks {
    RootMachineEventCheckFn check_Root_A_Go;
    RootMachineEventCheckFn check_Root_Global_Reset;
} RootMachineEventChecks;

void RootMachine_set_hooks(
    RootMachine *machine,
    const RootMachineHooks *hooks,
    void *user_data
);

void RootMachine_set_event_checks(
    RootMachine *machine,
    const RootMachineEventChecks *checks,
    void *user_data
);

int RootMachine_cycle(RootMachine *machine);
```

关键变化：

- `cycle()` 不再接收 `event_ids`
- 新增 `set_event_checks()`
- 保留 `set_hooks()` 继续处理 lifecycle abstract hooks

## 6.3 `user_data` 设计建议

有两种设计路径：

1. lifecycle hooks 与 event checks 共用一份 `user_data`
2. 两类 hook 各自持有独立 `user_data`

建议第一版采用：

- **各自独立 `user_data`**

原因：

- 事件接入层和动作扩展层在实际项目里常常不是同一批上下文
- 分离后更利于 C 工程做结构分层
- 减少用户为了共用一个指针而做强制大杂烩封装

对应建议 API：

```c
void RootMachine_set_hooks(
    RootMachine *machine,
    const RootMachineHooks *hooks,
    void *hook_user_data
);

void RootMachine_set_event_checks(
    RootMachine *machine,
    const RootMachineEventChecks *checks,
    void *event_check_user_data
);
```

## 6.4 事件上下文结构

建议为事件 hook 单独生成只读上下文，而不是复用 abstract action 的执行上下文。

建议结构至少包含：

- `event_path`
- `current_state_path`
- `vars`

示意：

```c
typedef struct RootMachineEventContext {
    const char *event_path;
    const char *current_state_path;
    const RootMachineVars *vars;
} RootMachineEventContext;
```

理由：

- event check 的关注点是“当前 event 在当前状态和当前变量快照下是否成立”
- abstract action 的 `action_name` / `action_stage` 对事件检查没有意义
- 分离语义更清晰，也便于后续扩展

---

## 7. 内部实现建议

## 7.1 优先复用现有 `c` 模板骨架

建议保留以下核心结构不变或尽量不变：

- state id / event id / state metadata 生成方式
- 状态栈与 frame mode
- hot start 逻辑
- init transition 逻辑
- `SimulationRuntime` 对齐的状态推进顺序
- validation / rollback 骨架
- 运行时错误信息与安全限制

这样可以把风险集中在事件输入层，而不是扩散到整个 runtime。

## 7.2 事件缓存结构

建议在 machine instance 中引入每周期事件缓存，例如：

- 每个 event 一个位或一个小型状态槽
- 至少区分三种状态：
  - unknown / not evaluated
  - false
  - true

实现形式可以是：

1. `unsigned char event_cache_state[EVENT_COUNT]`
2. 位图加已求值位图双数组
3. 小型 enum 数组

第一版推荐优先可读性和明确性，例如：

- `unsigned char evaluated[EVENT_COUNT]`
- `unsigned char values[EVENT_COUNT]`

后续如有必要，再压缩为 bitset。

## 7.3 周期边界处理

每次 `..._cycle(machine)` 开始时：

- 清空“本周期事件缓存”
- 状态机推进期间按需求值 event checks
- 周期结束后缓存内容可以保留但不再有效；下一个周期必须重新 reset

这样可以避免在 runtime 深层函数之间传递复杂的外部 event object。

## 7.4 事件求值辅助函数

建议新增统一辅助函数，替代现有 `_event_set_has(...)`：

```c
static int _RootMachine_check_event(
    RootMachine *machine,
    const _RootMachineRuntimeContext *context,
    int event_id);
```

其行为应为：

1. 校验 `event_id`
2. 若本周期已缓存，直接返回缓存值
3. 若未缓存，构造 `EventContext`
4. 调用对应 `check_xxx`
5. 缓存结果并返回

## 7.5 transition select 中的替换点

现有 `c` 模板中，transition condition 的 event 部分是：

- `_event_set_has(event_set, event_id)`

`c_poll` 中应改成：

- `_check_event(machine, context, event_id)`

这意味着：

- per-state specialized transition dispatch 仍然可以保留
- 绝大多数模板逻辑无需重写

## 7.6 validation / rollback 与缓存一致性

这是实现里最需要警惕的点。

建议：

- validation 和正式执行共享同一个周期缓存视图
- 验证失败回滚时，不回滚事件缓存
- 因为事件缓存表达的是“本周期外部输入快照”，不是状态机持久变量

只要遵守“单周期只求值一次”，validation 与提交阶段都看到同一结果，语义就是稳定的。

## 7.7 hot start 与首周期行为

建议保留现有 `c` 模板习惯：

- `hot_start()` 只重建状态栈与变量快照
- 不预先求值事件
- 首次 `cycle()` 再按需检查 event hooks

这样最容易与现有测试体系对齐。

---

## 8. 与 DSL 事件作用域的关系

`c_poll` 不应改变 DSL 中 event 的作用域规则。

以下规则应继续保持：

- `::` 本地事件
- `:` 链式作用域事件
- `:/` 或绝对根作用域事件路径解析规则不变
- 同一解析后 event path 仍然代表同一个 event identity

这意味着：

- 事件 hook 的生成单位仍应按“解析后的 event object / event path”来做
- 多个 transition 若引用同一个解析后事件，应共享同一个 `check_xxx`
- 单周期缓存也应以该 event identity 为单位

---

## 9. README 与开发者体验要求

`c_poll` 的 README 应明确告诉用户：

1. 它和 `c` 模板的差别是什么
2. 什么时候适合用 `c_poll`
3. 事件 hook 与 lifecycle hook 的区别
4. 事件 hook 的只读和单周期缓存语义
5. `cycle()` 不再接收 event id
6. 如何在 C 与 C++98 中挂接事件检查函数

README 中至少应包含：

- 最小 cold start 示例
- hot start 示例
- abstract hook 示例
- event check hook 示例
- “不要在 event check 里修改状态机持久变量”的注意事项
- C99 / C++98 编译示例

并且需要特别强调：

- README 里的代码片段也属于模板交付面的一部分
- 代码示例应按对应语言 formatter 的默认风格组织
- 不要靠手工列对齐来营造“整齐”，应以 formatter 可收敛为准

---

## 10. Phase 计划

下面的 phase 以“先保证语义正确，再逐步补齐工程化和文档完整性”为原则。

## Phase 0：设计冻结与范围确认

目标：

- 固定模板名为 `c_poll`
- 冻结“单周期 lazy + cache”语义
- 冻结公开 API 总体方向
- 明确第一版不做 consume / ack / 边沿触发

Checklist：

- [x] 模板名称确定为 `c_poll`
- [x] 以现有 `c` 模板为蓝本的方向确定
- [x] 单周期 lazy + cache 作为硬约束确定
- [x] 第一版只做只读 event checks，不做事件消费语义
- [x] 文档明确 `c_poll` 是 sibling template，而非 `c` 模板模式开关

## Phase 1：模板骨架复制与命名替换

目标：

- 新建 `templates/c_poll/`
- 复制现有 `c` 模板的基础结构
- 调整模板名、README 标题和基础说明

Checklist：

- [ ] 新增 `templates/c_poll/config.yaml`
- [ ] 新增 `templates/c_poll/machine.h.j2`
- [ ] 新增 `templates/c_poll/machine.c.j2`
- [ ] 新增 `templates/c_poll/README.md`
- [ ] 新增 `templates/c_poll/README_zh.md`
- [ ] 新增 `templates/c_poll/README.md.j2`
- [ ] 新增 `templates/c_poll/README_zh.md.j2`
- [ ] 更新模板总 README 与 builtin template 列表说明

## Phase 2：事件公开 API 切换

目标：

- 去掉 `cycle(event_ids, event_count)` 风格输入
- 引入 `EventChecks` 结构和安装 API
- 保留现有 lifecycle hooks

Checklist：

- [ ] `machine.h.j2` 中新增 `EventCheckFn`
- [ ] `machine.h.j2` 中新增 `EventContext`
- [ ] `machine.h.j2` 中新增 `EventChecks`
- [ ] `machine.h.j2` 中新增 `..._set_event_checks(...)`
- [ ] `machine.h.j2` 中将 `..._cycle(...)` 改为无事件参数
- [ ] machine instance 中新增 event check 挂载字段与独立 `user_data`
- [ ] 继续保留现有 lifecycle hooks API

## Phase 3：内部事件缓存与判定路径改造

目标：

- 用单周期 lazy + cache 机制替代现有 event set 输入
- 保持 validation / rollback 语义稳定

Checklist：

- [ ] 新增本周期事件缓存结构
- [ ] 每个周期开始时重置缓存
- [ ] 新增统一 `_check_event(...)` 辅助函数
- [ ] transition dispatch 中用 `_check_event(...)` 替代 `_event_set_has(...)`
- [ ] init transition 路径也切到 `_check_event(...)`
- [ ] validation / rollback 共享同一周期缓存语义
- [ ] 不把事件缓存纳入持久变量回滚

## Phase 4：测试体系补齐

目标：

- 在 `test/template/c_poll/` 下建立与 `c` 模板同级的测试体系
- 既验证公开 API，也验证运行时语义对齐
- 最终目标不是“挑一部分代表例子过掉”，而是对 `c_poll` 适用范围内的全套语义对齐用例完成覆盖与通过

Checklist：

- [ ] 新增 builtin template 提取与存在性测试
- [ ] 新增 Python ctypes/runtime harness 测试
- [ ] 新增 C harness 测试
- [ ] 新增 C++98 harness 测试
- [ ] 对 `C` / `C++` 生成运行时构建测试统一使用 `cmake` 驱动，不手工探测或拼装宿主 C 编译器命令
- [ ] 新增 runtime alignment 测试
- [ ] 对齐 `c` 模板运行时家族应覆盖的完整 alignment 语料，不允许只迁移子集
- [ ] 覆盖 abstract hooks 与 event checks 共存场景
- [ ] 覆盖 validation failure + rollback 场景
- [ ] 覆盖 local / chain / absolute event 作用域场景
- [ ] 覆盖 hot start 场景
- [ ] 覆盖关键字安全标识符场景
- [ ] 最终语义对齐结果要求“适用的例子一个都不能少”，新增模板不能通过删减 case 降低门槛

## Phase 5：文档、打包与 CLI 集成

目标：

- 让 `c_poll` 成为正式 builtin template
- 保持文档、打包、CLI、测试同步

Checklist：

- [ ] 更新 `templates/README.md`
- [ ] 更新 `pyfcstm/template/` 打包产物与 `index.json`
- [ ] 确认 `pyfcstm generate --template c_poll` 可工作
- [ ] 更新相关 maintainer docs
- [ ] 确认模板 README 中的示例与公开 API 一致

## Phase 6：formatter 收敛与发布前检查

目标：

- 确保生成产物和 README 示例在目标语言 formatter 下达到稳定终态
- 把 formatter 收敛视为完成定义的一部分，而不是发布前可选美化步骤

Checklist：

- [ ] 生成代表性 `c_poll` 产物
- [ ] 用 `clang-format` 检查 `.c` / `.h` 示例与产物风格
- [ ] 对 C / C++ 生成产物按四空格缩进风格验证 `clang-format` 收敛
- [ ] 检查 README 中 C / C++ 代码片段的风格一致性
- [ ] 如有 JSON / Markdown 辅助文件，检查其 formatter 友好性
- [ ] 确认重新格式化不会持续产生大面积重写
- [ ] 将 formatter 收敛视为完成定义的一部分
- [ ] 对未来扩展到其他语言的模板实现，分别使用该语言对应的 formatter 验证收敛，不允许手工样式游离于 formatter 之外

---

## 11. 验收标准

`c_poll` 第一版至少应满足：

1. 用户可以不传任何 event ids 而执行 `cycle()`
2. 每个 DSL 事件都可通过生成的 `check_xxx` hook 接入外部事件源
3. 同一周期内，对同一事件的观察结果稳定
4. rollback / validation 与正式执行之间不会出现事件观察漂移
5. 运行时语义继续与 `SimulationRuntime` 对齐，且适用的全套对齐用例全部通过，不允许删减例子来声明完成
6. 生成代码继续兼容 `C99` 与 `C++98`
7. README 与生成代码都能在 formatter 流程下达到收敛
8. 对 `C` / `C++` 产物的 formatter 收敛检查应以 `clang-format` 为准，并满足四空格缩进风格

---

## 12. 风险与开放问题

## 12.1 电平触发与边沿触发不是一回事

当前设计更偏向：

- 电平式 / 条件式“本周期是否成立”

如果业务需要：

- 上升沿
- 单次消费
- 查询即清除

则需要额外设计，不能默认塞进 `check_xxx`。

## 12.2 用户可能把 event hook 写成有副作用函数

虽然 runtime 会做单周期缓存，但仍需在 README 和头文件注释中强调：

- 事件 hook 应尽量无副作用
- 不要依赖“调用一次就顺便做状态推进之外的事情”

## 12.3 生命周期 hook 与事件 hook 的上下文容易被混用

因此建议坚持分离：

- `ExecutionContext`
- `EventContext`

避免用户误用字段。

## 12.4 与现有 `c` 模板的长期重复维护成本

短期内接受 `c` 与 `c_poll` 的模板重复是合理的。  
中长期如果两者功能继续扩展，可能需要抽取共用片段或生成辅助宏，但不应在第一版为了“少重复”而提前引入复杂模板继承结构。

---

## 13. 实施建议

推荐实施顺序：

1. 先复制 `c` 模板到 `c_poll`
2. 先改头文件公开 API 与 README 说明
3. 再改内部事件缓存与判定路径
4. 先补基础测试，再补 alignment 测试
5. 最后做模板打包、CLI、formatter 收敛与发布前清理

原因：

- 这样最容易控制差异面
- 这样最容易在评审时看清楚“`c_poll` 到底和 `c` 模板差在哪”
- 也最适合后续 PR 按 phase 拆分

---

## 14. 本文档约束级别

本文档中的以下项目应视为第一版实现硬约束：

- 模板名称为 `c_poll`
- 以现有 `c` 模板为蓝本
- 单周期 lazy + cache
- `cycle()` 不再传入事件集合
- event check hooks 与 lifecycle hooks 分离
- 第一版不做 consume / ack / 边沿触发
- 适用的全套语义对齐用例必须全部通过，一个例子都不能少
- formatter 收敛属于完成定义的一部分
- `C` / `C++` 生成产物以 `clang-format` 验证收敛，并满足四空格缩进风格

其余实现细节如缓存内部布局、辅助函数命名、README 篇章组织方式，可以在实现时做等价调整，但不得破坏上述硬约束。
