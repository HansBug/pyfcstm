# 内置模板系统

本目录存放 `pyfcstm` 内置模板的可编辑源码。它是模板开发和维护的源码侧事实来源；`pyfcstm/template/` 则存放随安装包分发的 zip 资源和 `pyfcstm/template/index.json`。

内置模板系统有两个职责：

1. 通过 renderer 将 FCSTM model 渲染成目标语言文件；
2. 将仓库中的指定模板源码打包，使 `pyfcstm generate --template <name>` 在没有仓库 checkout 的安装环境中也能使用内置模板。

生成 runtime 的语义必须和 FCSTM model 以及 simulator 契约保持一致。对 generated implementation 文件来说，性能和语义正确性优先于人工长期维护可读性。Formatter / linter gate 的目的只是让生成代码看起来专业、清爽、容易集成，不能让实现可读性反过来压过 runtime 行为。

## 文档元数据合同

受支持的 FCSTM 所有者（`State`、`Event`、`Transition`、`VarDefine`、 `OnStage` 和 `OnAspect`）各自携带一个不透明的 `doc` 值。文档块由 grammar 作为所有者前的 leading block 消费；abstract 生命周期动作也兼容历史 trailing 写法，canonical export 会把两者归一为同一个字段。`None`、空字符 串和字面量 `*` 是不同的值。文档属于元数据：它会进入 AST/Model round-trip 和 canonical export，但不会进入 runtime identity、diagnostics、PlantUML 展示或结构化 Diagram 数据。

模板作者应使用显式的 `is not none` 判断消费 `doc`，不能根据源码行号猜测 所有者。canonical `model.to_ast_node()` export 是生成 README/源码文本的权威 来源。它不是秘密边界：生成物可能包含完整文档，因此模板和生成 README 必须 提醒用户不要在文档块中保存凭据、token、密码或私钥。

共享 renderer 提供 `markdown_fence`（保护 README 代码块）和 `escape_python_docstring`（保护 Python 三引号 docstring）。这些 helper 只 保护 Markdown 分隔符和目标语言语法，不改变 Model 的 `doc` 值。C-family canonical 字符串还必须保护 `??/` 等 C 三字符组；这是源码模板自己的转义 策略，`doc` 本身不被修改。值域仍拒绝 `/*` 与 `*/`，以保证每次 canonical export 都能重新解析。

## 目录职责

| 路径 | 职责 | 维护说明 |
| --- | --- | --- |
| `templates/README.md` | 英文模板系统总手册 | 说明仓库级模板规则和维护契约。 |
| `templates/README_zh.md` | 中文模板系统总手册 | 必须与英文版保持仓库级规则等价。 |
| `templates/<name>/` | 单个内置模板的可编辑源码 | 只有一级子目录会被打包为内置模板。 |
| `templates/<name>/README.md` | 单模板英文维护手册 | 说明该模板目标、兼容性、API surface、维护流程和测试。 |
| `templates/<name>/README_zh.md` | 单模板中文维护手册 | 必须与英文单模板维护手册等价。 |
| `templates/<name>/README.md.j2` | 英文生成物用户手册 | 渲染到生成目录，面向下游使用者。 |
| `templates/<name>/README_zh.md.j2` | 中文生成物用户手册 | 渲染到生成目录，面向下游使用者。 |
| `templates/<name>/machine.*.j2` | 目标语言源码模板 | 渲染成 generated runtime source files。 |
| `templates/<name>/config.yaml` | Renderer configuration contract | 定义表达式风格、语句风格、扩展点和忽略规则。 |
| `templates/<name>/template.json` | 内置模板 metadata | 描述打包模板并进入 `pyfcstm/template/index.json`。 |
| `pyfcstm/template/` | 打包后的内置模板资源 | 包含 zip archives 和 `index.json`；由 `tools.package_templates` 生成。 |

根级 `templates/README*.md` 文件不属于任何模板 archive。只修改这些根手册时，不需要重新构建模板 zip 资源。

## 当前内置模板

| Template name | `template.json.language` | 用途 |
| --- | --- | --- |
| `python` | `python` | 自包含 Python runtime template。 |
| `c` | `c` | 自包含 C99 runtime template，并支持 C++98 集成路径。 |
| `c_poll` | `c` | 使用 hook-polled events 的自包含 C99/C++98 runtime template。 |
| `cpp` | `cpp` | 早期一等 C++ runtime template，复用 `c` core 并生成 C++ wrapper files。 |
| `cpp_poll` | `cpp` | 早期一等 C++ poll runtime template，复用 `c_poll` core 并生成 C++ wrapper files。 |

Template name 和目标语言相关但不完全相同。例如，`c_poll` 是独立模板，但它的 generated target language 仍然是 `c`；`cpp_poll` 也是独立模板，但 generated target language 是 `cpp`。

`cpp` 和 `cpp_poll` 在早期推广期仍然有意保留 `experimental: true`。这里的 experimental 表示“早期一等模板”状态：wrapper API、共享语义对齐、packaging 和原生工具链矩阵已经可用且有测试覆盖，但在后续稳定化工作移除该标记前，仍需要明确告知维护者和用户它们处于早期推广期。

## 预留语言 vocabulary

后续模板应使用稳定的 `template.json.language` 值。下面这些值为未来模板工作预留，但当前不要求存在对应模板目录：

| 未来语言 | Reserved value | 当前要求 |
| --- | --- | --- |
| Java | `java` | 为 Java source banner、formatter/build gate、standard-library-only runtime design 预留空间。 |
| JavaScript | `js` | 为 JavaScript source banner、formatter gate、language-core/runtime-free design 预留空间。 |
| Rust | `rust` | 为 Rust source banner、`rustfmt`、standard-library-only runtime design 预留空间。 |
| Ruby | `ruby` | 为 Ruby source banner 和 dependency-free runtime design 预留空间。 |
| Go | `go` | 为 Go source banner、`gofmt`、standard-library-only runtime design 预留空间。 |

检查逻辑必须区分当前模板和预留 vocabulary。`python`、`c`、`c_poll`、`cpp`、`cpp_poll` 是当前 template names。`java`、`js`、`rust`、`ruby`、`go` 是预留目标语言 vocabulary，不应该强制当前存在空目录。

这些预留语言未来新增 formatter 或 linter gate 时，也必须继承同一条仓库级标准：它们是用于发现明显 generated-code 粗糙问题的务实质量门槛，不是绝对风格目标。未来 Java、JavaScript、Rust、Ruby、Go 或其他模板在新增严格检查前，必须在对应模板文档中写清楚这个约束。

## Renderer contract

Renderer 主要实现在 `pyfcstm/render/render.py` 和 `pyfcstm/render/env.py`。

`pyfcstm.render.StateMachineCodeRenderer` 按以下规则消费模板目录：

- 先加载 `config.yaml`，再准备文件映射。
- 以 `.j2` 结尾的 Jinja2 文件会被渲染，输出路径会去掉 `.j2` 后缀。
- 非 `.j2` 文件会作为静态文件复制，除非被忽略规则排除。
- `config.yaml` 本身不会被复制到生成目录。
- 忽略规则通过 `pathspec` 使用 Git-style patterns，由模板的 `ignores` 条目控制。
- 当前 render context 会向模板传入 `model`，但不会传入 raw input source text。
- 表达式渲染和语句渲染通过 `expr_render`、`stmt_render`、`stmts_render` 等 filters 暴露。

核心渲染调用当前形态是 `tp.render(model=model)`。模板作者不能假定存在额外 context variables；除非 renderer 明确新增，并同步更新本手册、单模板 README 和测试。

## `config.yaml` contract

`config.yaml` 是模板的 renderer configuration file。已知 top-level keys 由 `pyfcstm/render/render.py`、`pyfcstm/render/env.py`、`pyfcstm/render/expr.py`、`pyfcstm/render/statement.py`、`pyfcstm/render/func.py` 定义。

| Key | 含义 | Runtime boundary |
| --- | --- | --- |
| `expr_styles` | 新增或覆盖表达式渲染风格。 | 仅 generation-time。 |
| `stmt_styles` | 新增或覆盖语句渲染风格。 | 仅 generation-time。 |
| `globals` | 通过声明式配置项添加 Jinja2 global objects。 | 仅 generation-time。 |
| `filters` | 通过声明式配置项添加 Jinja2 filters。 | 仅 generation-time。 |
| `tests` | 通过声明式配置项添加 Jinja2 tests。 | 仅 generation-time。 |
| `ignores` | 从渲染/复制中排除的 Git-style patterns。 | 仅 generation-time。 |

大多数 key 是可选的，默认等价于空配置。Jinja2、PyYAML、`pathspec`、renderer helpers、imported filters 这类 generation-time dependencies 是允许的，因为它们只在 `pyfcstm` 生成阶段运行。除非 generated target language 明确拥有并通过 runtime policy 批准，否则这些依赖不能泄露为 generated runtime dependency。

目标语言专属 helper 应由对应模板通过 `type: import` 显式加载。`to_c_identifier`、`to_c_path_identifier`、`render_c_action_body`、`render_c_condition_body` 等 C-family helper 属于 `c` / `c_poll` / `cpp` / `cpp_poll` 的 config，而不是默认 renderer 环境。

当代码新增 `config.yaml` key 时，必须同时更新本手册、受影响的单模板 README 和结构检查。

### 严格 config keys 和声明式条目形式

空的 `config.yaml` 会被视为一个空 mapping。未知 top-level key 会直接报错，而不是被静默忽略，这样配置拼写错误会在对应模板目录附近暴露。

`globals`、`filters` 和 `tests` 下的声明式条目支持三种形式：

| 条目形式 | 必填字段 | 含义 | 信任边界 |
| --- | --- | --- | --- |
| `type: template` | `template`，可选有序 `params` | 从内联 Jinja2 片段构建 callable。 | 受信任模板源；仅 generation-time。 |
| `type: import` | `from` | 导入 Python 对象并暴露给模板。 | 受信任模板代码边界；不要用于不可信模板。 |
| `type: value` | `value` | 暴露 YAML literal value。 | 仅 generation-time。 |

目标语言专属 helper 应由对应模板通过 `type: import` 显式加载，不应该注入 default renderer environment。

## `template.json` metadata contract

每个打包模板目录都应包含 `template.json`。Metadata loader 实现在 `tools.package_templates`。

| Field | 含义 |
| --- | --- |
| `name` | 模板名。打包器会用一级目录名覆盖该值。 |
| `title` | 人类可读的模板标题。 |
| `description` | 用于模板发现和文档的短说明。 |
| `language` | 生成代码的目标语言，不一定等同于模板名。 |
| `experimental` | 该模板是否为 experimental。当前 `cpp` / `cpp_poll` 的该字段表示早期一等模板状态，而不是未实现模板。 |
| `archive` | 打包 archive 文件名。打包器会写成 `<name>.zip`。 |
| `root_dir` | archive 内部根目录。打包器会写成 `<name>`。 |

打包后，`name`、`archive`、`root_dir` 以 `tools.package_templates` 从目录名强制写入的值为准。模板作者仍然应保持源码中的 `template.json` 可读且准确，方便 review。

## Packaging and loading contract

内置模板 packaging/loading chain 有多个明确的权威点：

- `tools.package_templates` 只扫描 `templates/` 下一级子目录。
- `tools.package_templates` 读取每个模板的 `template.json`，与默认 metadata 合并，然后强制写入 `name`、`archive`、`root_dir`。
- 写入新 archive 前，`tools.package_templates` 会删除 `pyfcstm/template/` 下陈旧的 `.zip` 文件。
- 每个 archive 使用模板名作为 zip root directory。
- `tools.package_templates` 写入 `pyfcstm/template/index.json` 保存打包模板 metadata。
- `setup.py` 在仓库 checkout 中存在 `templates/` 时调用 `package_templates()`。
- `MANIFEST.in` 将 `pyfcstm/template/*.zip` 和 `pyfcstm/template/*.json` 纳入 source distributions。
- `setup.py` 的 `package_data` 将 `*.zip` 和 `*.json` package resources 纳入 wheels。
- `pyfcstm/template/__init__.py` 提供 `list_templates`、`has_template`、`get_template_info`、`extract_template`。
- 在 installed package 中，`extract_template` 通常按照 `index.json` 引用解压 zip archive。
- 在 development checkout 中，如果 zip archive 缺失，`extract_template` 会 fallback copy `templates/<name>`。
- `pyfcstm/entry/generate.py` 会为 `pyfcstm generate --template <name>` 提取内置模板，再把提取目录交给 `StateMachineCodeRenderer`。

不要用临时 runtime discovery 替换这条链路。如果 packaging behavior 改变，必须一起更新 `tools.package_templates`、`setup.py`、`MANIFEST.in`、`pyfcstm/template/__init__.py`、本手册和模板打包测试。

## Documentation layering rules

文档必须保持分层，避免模板维护者和生成代码用户拿到错误信息。

| Layer | Audience | Should contain | Should avoid |
| --- | --- | --- | --- |
| 根级 `templates/README.md` / `templates/README_zh.md` | 模板系统维护者 | 仓库级机制、治理规则、packaging、renderer contracts、未来语言 vocabulary。 | 单模板用户教程或 generated runtime API 细节。 |
| 单模板 `templates/<name>/README.md` / `templates/<name>/README_zh.md` | 某个模板的维护者 | 目标语言、兼容性、public integration surface、性能策略、源码布局、维护命令、测试。 | 应放在 `README.md.j2` 的生成物 onboarding。 |
| 生成物 `README.md.j2` / `README_zh.md.j2` | 单个生成目录的使用者 | 生成了什么、模型摘要、变量/event/hook 用法、冷启动、热启动、完整最小运行流程。 | 模板内部 packaging 机制。 |
| `machine.py.j2`、`machine.c.j2`、`machine.h.j2` 等 source `.j2` files | Renderer 和 generated runtime | 高效的目标语言实现，以及简洁的生成文件提示。 | 大段模板系统说明。 |

只看到生成目录的人或 LLM，应能仅凭 generated README 使用 generated runtime，而不需要理解仓库模板系统。

## 生成 README 写作规则

生成的 `README.md.j2` 和 `README_zh.md.j2` 面向只持有生成目录的使用者，必须提供完整接入指导。模板目录中的 `README.md` / `README_zh.md` 面向维护者，说明源码分工、行为约束、联动修改和验证命令。两类文档的职责必须明确。

- 维护一条使用路径：完整快速开始、输入/动作/事件、初始化与恢复、结果/错误/生命周期、API 参考、高级构建选项和模型参考。第一份可运行程序应在长篇模型清单及部署讨论之前。
- 每种语言、每套模板只保留一份完整快速开始。新增 API 时同步修改教程、示例和参考表，替换过时示例并删除重复内容，不追加第二份快速开始或补丁式说明来弥补前文。
- 独立示例包含初始化、输入读取、所需动作/事件注册及检查返回值的周期调用。片段明确前置示例和插入位置，继续使用同一实例，不悄悄重新初始化。C++ 指南始终使用封装方法，明确说明沿用的 C 回调签名。
- 展示固定 `parameters` 构造、每个 `input` 采样、抽象动作挂载、事件提交/查询和已提交 control/output 读取。区分每拍数值采样、仅执行阶段调用的动作和按需缓存的事件查询，并说明返回约定、借用与复制的生命周期。
- 冷初始化可使用默认值；热恢复使用同一检查点的状态、全部持久值和全部参数。说明采样失败、重试、Delta 周期、结束后调用和无法撤销的外部副作用。
- 源码及生成 Markdown 的自然段均保持一段一行。代码、列表、表格和 Jinja 控制结构保留必要换行。中英文章节顺序等价、可执行示例同步；标识符以外使用自然中文。
- 渲染现有角色用例、组合 input/param/control/output/action/event 模型及缺少可选功能的模型。审阅实际输出的表格、锚点和代码块，不能只检查 Jinja 是否成功。
- 通过打包模板/公开渲染路径执行生成示例，断言读取次数、动作调用、提交结果、连续周期、失败重试和恢复。退出码为零不足以证明正确。行为测试保留在 pytest，源码/纯文档检查放维护工具。
- 回调映射和公开 API 清单与生成头文件/模块同步。`model.to_ast_node()` 使用规范化模型导出的表述。内部引擎布局、CI 产物排障和打包机制不进入入门主线。

实质性修改指南后，应由新的审阅者只根据生成目录完成小型接入。缺失配置、未定义符号、接口混用和误导示例必须在交付前解决。记录实际编译或执行的内容，区分命令次数与程序数量。


## Generated runtime policy

Generated runtime files 默认必须严格 self-contained：

- 不依赖 `pyfcstm runtime`。
- 不依赖 third-party runtime library。
- 不依赖不稳定、平台绑定明显或版本要求过新的语言/库特性。
- 优先使用目标语言 core features 和长期稳定的 standard library 能力。
- 保持广泛版本和平台兼容。现有期望包括：`python` 模板支持 Python 3.7+，C implementation 使用 C99，C header / harness 保持 C++98-compatible integration paths。

Generated implementation files 应优先服务模型语义、可预测执行和运行时性能（runtime performance）。对 `machine.py`、`machine.c` 这类实现文件来说，人工可读性是次要目标。`machine.h` 这类 public integration surfaces 会被下游集成者阅读，应保持清晰。

已经定义的 formatter 和 linter checks 仍然必须通过。它们的目的，是让生成输出看起来专业并避免明显集成阻力。这是务实质量门槛，不是无限追求风格完美。不要为了风格偏好而扭曲 generated runtime design，尤其不能牺牲性能、语义、兼容性或 simulator/template alignment。如果极少数 formatter-only 例外被接受，必须窄范围记录 runtime 与兼容性理由。

这条 policy 同样适用于现有 formatter flow 和未来新增的 formatter flow。新增模板不得定义会迫使维护者围绕极端 edge case 过度优化的 formatter 规则；与可见行为或集成质量无关的纯风格问题不应压过模板核心目标。

对于需要显式管理内存或其他资源的目标语言，模板维护者还必须把资源生命周期视为 runtime correctness 的一部分。Generated runtime 很可能被嵌入长期稳定运行的控制系统，因此 generated code 必须对 allocation、initialization、hot start、cycle execution、hook/event-check registration 和 destruction 有清楚的 ownership model。C/C++ 模板以及未来 native 或 resource-owning 模板在修改 runtime source templates 时，应运行代表性的 sanitizer、leak-check、valgrind 或等价 harness。若发现既有 leak 或资源生命周期问题且不属于当前改动范围，应留下可复现 harness 和记录，而不是静默忽略。

## C/C++ 部署安全表述

当前 C-family 模板（`c`、`c_poll`、`cpp` 和 `cpp_poll`）提供的是面向控制状态机 生成运行时的部署硬化工程基线（deployment-hardened engineering baseline）。 这条基线包括 C99 execution core、适用时的 C++98-compatible integration surface、 调用方拥有对象与无堆剖面、共享语义对齐，以及原生工具链矩阵证据。

这不是安全认证声明。维护文档和生成物文档都不能把这些模板描述为已经满足 MISRA、AUTOSAR、DO-178C、IEC 61508、ISO 26262 或其他认证 ready。正确表述是： 它们是非认证的 generated-code baseline，用于支撑后续项目自己的静态分析、 编码规则审查、板级支持包集成和认证证据工作。

职责边界应保持分离：

- `pyfcstm inspect` 负责轻量模型诊断，包括当前 C/C++ 默认部署剖面的数值 warning。
- 形式化验证路线负责后续 BitVec、BMC、fixed-point 和 numeric-profile proof 工作。
- 代码生成路线负责后续 checked arithmetic、目标相关 failure channel 等生成代码数值策略。
- 模板 README 负责集成边界、资源生命周期、编译器剖面、hook/event-check 安装、并发假设、
  外部 I/O adapter 和认证表述边界。

C/C++ 生成指南必须在相关用法和构建说明中讲清集成边界。只拿到生成目录的用户， 也应能直接看到 compiler/profile 边界、内存 ownership 选择、event/hook 要求、单实例并发假设、 外部设备 adapter 边界、numeric inspect 入口，以及“工程证据不等于认证”的边界，而不需要阅读本维护手册。

## Source context contract

当前 renderer 会传入 model object，但不会传入 raw source text。因此 generated artifacts 必须精确标注 model text 来源：

- 只有确实来自用户输入文件的 bytes/text，才能称为 `original source`。
- 由 `model.to_ast_node()` 或其他 model export path 生成的文本，应称为 `canonical model export`、`normalized model export` 或等价表述。
- 不要把 canonical export 称为 raw source。
- 如果未来 renderer 新增 raw source context，必须一起更新 `pyfcstm/render/render.py`、`pyfcstm/entry/generate.py`、generated README templates、source metadata 和测试。

该 contract 适用于 generated README、`DSL_SOURCE` 风格常量、C helper functions（如 `_dsl_source()`）、docstrings、comments，以及任何 public/generated metadata。

## New template checklist

新增内置模板目录前，必须确认以下事项：

- 添加 `templates/<name>/template.json`，并准确填写 `title`、`description`、`language`、`experimental`。
- 添加 `templates/<name>/config.yaml`；除非同一改动扩展 renderer，否则只能使用已文档化的 renderer keys。
- 添加单模板维护者使用的 `README.md` 和 `README_zh.md`。
- 添加生成目录用户使用的 `README.md.j2` 和 `README_zh.md.j2`。
- 添加 generated source templates，并在实际生成文件首个真实输出附近放置 generated-file banners。
- 保持 generated runtime self-contained：无 `pyfcstm runtime`、无 third-party runtime dependency、无不稳定 runtime dependency。
- 定义目标语言兼容性、formatter、build、test gates；formatter gate 必须写成务实质量检查，而不是绝对风格目标。
- 对需要显式资源 ownership 的模板，把资源生命周期和 leak-check 期望与 build/runtime gates 一起定义清楚。
- 添加代表性 generated-runtime tests；适用时添加 simulator alignment tests。
- 运行 packaging checks，确保 `pyfcstm/template/index.json`、zip archives、`extract_template` 和源码模板一致。
- 只有仓库级 contract 变化时才更新本手册；单模板变化应更新单模板 README。

<a id="native-template-verification"></a>

## 原生模板验证

原生 pytest 构建复用现有 CMake 测试程序，不新增第二套主机编译器调度层。现有 README 命令测试可直接执行文档中的 gcc/clang 命令，验证这些具体构建方法。运行测试通过共享语义用例比较公开观察值，包括事件与动作行为。

`PYFCSTM_GENERATED_NO_HEAP` 按宏是否定义选择（`#if defined(...)` / `#ifdef`），`-DNAME` 和 `-DNAME=1` 均需有效。头文件堆接口声明、实现及其 `<stdlib.h>` 依赖一起移除；通过预处理和符号/链接检查确认不存在堆辅助函数及 `calloc/free` 引用。保留调用方拥有的存储、动作回调和轮询事件查询。用 CMake `PUBLIC` / `INTERFACE` 或一致的最终目标定义，确保 C 内核、封装及所有消费端使用相同宏。

| 证据类型 | 必须证明的结果 |
| --- | --- |
| 宿主或模拟环境执行 | 编译并运行每个共享语义用例，比较公开数值、生命周期和事件观察 |
| 仅编译 | 生成非空的运行时、测试程序和 C++ 头文件探测目标文件；不能宣称已证明运行时对齐 |
| 仅分析 | 保留 cppcheck/clang-tidy 等工具的报告；工具崩溃、解析失败和缺报告均视为失败 |

新增编译器配置时，同步现有配置注册表、工作流选择、预期产物和维护文档，以工具链行为命名配置。公开宿主配置缺少必需工具时必须失败；需要授权的厂商工具保持手动或自托管运行，直到配置好相应执行环境。涉及源码所有权或兼容性变化时，在常规语义对齐之外执行代表性的运行时错误与泄漏检查。

## Maintenance workflow

根据改动范围选择最小但足够的验证集：

- 只改根手册：执行 README structure review 和 self-check；不需要 `make tpl`。
- 改 `templates/<name>/` 下模板源码：运行 `make tpl` 和对应模板测试。
- 改 generated runtime source-template：生成代表性输出，运行 formatter/build/runtime checks，并在适用时验证 generated README examples。
- 改 Python public API 或 pydoc：运行 `make rst_auto` 并审阅生成的 RST diff。

本地迭代时，`SKIP_SLOW_TESTS=1 make unittest` 会跳过 C/C++ native toolchain template tests，同时保留 Python template、simulator、model、DSL、render、verify 测试。除非已通过与该模板 runtime language 相称的检查，否则不要声称模板改动完成。
