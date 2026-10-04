# cpp_poll 模板维护指南

本手册面向 `cpp_poll` 模板维护者。下游接入说明由 `README.md.j2` / `README_zh.md.j2` 生成；根级[模板手册](../README_zh.md)负责渲染器、元数据和打包契约。维护时先查看源码分工，确认必须保持的行为，再选择对应检查。

## 源码分工与修改位置

| 模板源文件 | 维护职责 | 生成输出 |
| --- | --- | --- |
| `machine.h.j2` | 指向 `../c_poll/machine.h.j2` 的文件级符号链接 | `machine.h` |
| `machine.c.j2` | 指向 `../c_poll/machine.c.j2` 的文件级符号链接 | `machine.c` |
| `machine.hpp.j2` | C++ poll-wrapper header | `machine.hpp` |
| `machine.cpp.j2` | C++ poll-wrapper implementation | `machine.cpp` |
| `README.md.j2` | 英文生成物使用说明 | `README.md` |
| `README_zh.md.j2` | 中文生成物使用说明 | `README_zh.md` |
| `config.yaml` | 独立渲染配置，显式导入 C 系列辅助函数 | 不复制 |
| `template.json` | 内置模板元数据 | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | 渲染时不复制，但会收入模板源码包 |

生成阶段的辅助函数在 pyfcstm 内运行，生成程序必须保持自包含。`config.yaml` 将本维护手册和 `template.json` 排除在生成输出之外；`make tpl` 仍会把它们收入模板源码归档，因此修改模板后必须刷新打包。

| 改动 | 修改与同步位置 |
| --- | --- |
| 生成指南 | 两份 README Jinja 模板、实际渲染示例和可执行文档测试 |
| 角色接口或生命周期行为 | 运行时源码、生成指南/API 表、角色测试和语义对齐 |
| 表达式/getter 生成 | `../../pyfcstm/render/c_runtime.py`、`config.yaml` 显式导入、C 与轮询内核及两套 C++ 封装 |
| input/param 标识符 | `readonly_value_identifier`；同步声明、getter、输入提供器、README 示例和 ABI 测试 |
| 共享 C 内核 | 修改 `../c_poll/machine.c.j2` / `machine.h.j2`，本目录通过符号链接复用；同时运行内核和封装测试 |

## 运行时契约

四种变量角色属于运行时契约，维护时必须保持其可观察的生命周期和失败行为：

| 角色 | 必须保持的行为 |
| --- | --- |
| `input` | 每个未结束周期对全部输入采样一次，包括未使用输入；验证和执行共享冻结值，无默认保持；显式快照绕过采样 |
| `param` | 构造时复制并校验，冷启动缺省项用 DSL 默认值；热启动要求同一检查点的完整参数；周期内不可覆盖 |
| `control` | 模型持久可写状态，可预设冷启动值；热启动提供完整快照，未写入时保持 |
| `output` | 与 control 共用提交和回滚机制，应用在成功后读取；不生成执行器 setter |

采样或执行失败保留已提交变量和 `last_inputs`。成功的 Delta 周期保持持久状态，但发布本拍输入快照。构造和结束后的周期不采样。动作 Hook 仅在执行阶段调用，观察只读上下文，不能修改模型状态；其外部副作用无法撤销。

共享用例使用顶层 `parameters`、`initial.vars` / `initial.outputs`、逐步 `inputs` 和部分 `expect.vars` / `expect.outputs`。不要添加参数/输入预期，也不要增加逐步参数覆盖。测试必须实际执行生成运行时，并与仿真器比较数值、生命周期观察和失败行为。

`InputProvider` 会复制，但其 `user_data`、`Hooks`、事件表及其数据均为借用。`last_inputs` 和 `vars` 指向实例存储，上下文指针只在回调期间有效。冷初始化清空注册，热启动保留注册。保持 C99、有符号 64 位 `Int` ABI、仅标准库依赖、调用方拥有对象和 `PYFCSTM_GENERATED_NO_HEAP` 可用。浮点转整数必须先检查再转换。同一实例不可重入，资源所有权必须明确。

事件查询与数值输入读取不同：事件按需查询，首次结果在周期内缓存，非零表示事件有效，而不是采样成功。有事件的模型即使使用显式输入快照也必须安装完整事件表。覆盖无事件、单事件和多作用域事件模型。

封装保持 C++98 兼容，不依赖异常、RTTI 或 STL 容器。它只转发公开 C 函数，不实现第二套执行引擎，也不读取私有字段。语义对齐必须通过 `machine.hpp`、`Wrapper::` 别名和封装方法进入。打包时将 C 内核符号链接解析为普通文件，解压后不依赖相邻模板目录。`experimental: true` 表示早期一等模板状态，不表示运行时尚未实现。

## 文档维护纪律

以完整用户路径为单位维护。只保留一份完整快速开始，后续依次扩展同一实例、说明恢复、API 参考和高级集成。新增 API 应并入对应教程章节和参考表，同次修改替换过时示例并删除重复说明。不要通过追加第二份快速开始、末尾“完整示例”或补充声明来掩盖前面章节的问题。

独立示例必须包含所需的 input/action/event 接入、初始化和错误处理。片段明确依赖哪个示例及插入位置，不得悄悄重新创建实例。C++ 指南始终通过封装操作状态机，回调签名可使用已说明的 C 类型别名。程序成功退出不足以证明正确，必须断言采样、动作调用和提交结果。

源码 README 和实际生成 Markdown 的自然段均保持一段一行。代码、表格、列表及 Jinja 控制结构保留必要换行。中英文章节顺序一致，代码示例等价；中文正文使用自然中文，API 名称保持原样。必须审阅实际生成内容，不能只看 Jinja 差异。

生成指南只承载接入说明，仓库 CI 排障和打包规则放维护手册。公共机制写入根级手册，当前模板的具体实现约束写在本文件。保留运行时边界和兼容性说明，避免多个章节重复警告。文字和结构检查放维护工具，可执行生成示例放 pytest。

## 验证流程

原生模板的所有权、无堆配置和工具链证据规则统一维护在根手册的[原生模板验证](../README_zh.md#native-template-verification)一节，并与下方本模板检查一并执行。

以下命令从仓库根目录执行。`make template_unittest` 会刷新模板包，并清除显式选中套件继承的慢测试跳过设置。直接运行 pytest 前必须先执行 `make tpl`，不能将默认轻量套件作为原生模板已完成的证据。

```bash
make tpl
PYFCSTM_TEMPLATE_SUITES=c_poll,cpp_poll make template_unittest
make test_boundary_check resource_ownership_check
make rst_auto
```

只修改生成指南时，执行生成示例及相关格式/构建测试。修改运行时则运行所选完整套件和适用的共享用例；共享 C 渲染变化需要两套 C 内核和两套封装。修改原生数值、ABI 或所有权时，还需运行相关原生工具链/运行时检测工具配置：

```bash
PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 PYFCSTM_TEMPLATE_SUITES=cpp_poll make template_unittest TEMPLATE_UNITTEST_ARGS="--run-native-toolchain"
```

使用同时包含四种角色和动作/事件的模型，以及无输入、无参数、多输入、未使用输入、作用域名称和失败重试模型。确认两种语言均能生成、锚点和代码块有效，示例无需修改生成状态机文件即可使用。发布前审查包内容、公开 API 差异和测试结果。
