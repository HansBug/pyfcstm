# 内置模板系统

本目录存放 `pyfcstm` 内置模板的可编辑源码。它是模板开发和维护的源码侧事实来源；`pyfcstm/template/` 则存放随安装包分发的 zip 资源和 `pyfcstm/template/index.json`。

内置模板系统有两个职责：

1. 通过 renderer 将 FCSTM model 渲染成目标语言文件；
2. 将仓库中的指定模板源码打包，使 `pyfcstm generate --template <name>` 在没有仓库 checkout 的安装环境中也能使用内置模板。

生成 runtime 的语义必须和 FCSTM model 以及 simulator 契约保持一致。对 generated implementation 文件来说，性能和语义正确性优先于人工长期维护可读性。Formatter / linter gate 的目的只是让生成代码看起来专业、清爽、容易集成，不能让实现可读性反过来压过 runtime 行为。

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

Template name 和目标语言相关但不完全相同。例如，`c_poll` 是独立模板，但它的 generated target language 仍然是 `c`。

## 预留语言 vocabulary

后续模板应使用稳定的 `template.json.language` 值。下面这些值为未来模板工作预留，但当前不要求存在对应模板目录：

| 未来语言 | Reserved value | 当前要求 |
| --- | --- | --- |
| Java | `java` | 为 Java source banner、formatter/build gate、standard-library-only runtime design 预留空间。 |
| JavaScript | `js` | 为 JavaScript source banner、formatter gate、language-core/runtime-free design 预留空间。 |
| Rust | `rust` | 为 Rust source banner、`rustfmt`、standard-library-only runtime design 预留空间。 |
| Ruby | `ruby` | 为 Ruby source banner 和 dependency-free runtime design 预留空间。 |
| Go | `go` | 为 Go source banner、`gofmt`、standard-library-only runtime design 预留空间。 |

检查逻辑必须区分当前模板和预留 vocabulary。`python`、`c`、`c_poll` 是当前 template names。`java`、`js`、`rust`、`ruby`、`go` 是预留目标语言 vocabulary，不应该强制当前存在空目录。

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

当代码新增 `config.yaml` key 时，必须同时更新本手册、受影响的单模板 README 和结构检查。

## `template.json` metadata contract

每个打包模板目录都应包含 `template.json`。Metadata loader 实现在 `tools.package_templates`。

| Field | 含义 |
| --- | --- |
| `name` | 模板名。打包器会用一级目录名覆盖该值。 |
| `title` | 人类可读的模板标题。 |
| `description` | 用于模板发现和文档的短说明。 |
| `language` | 生成代码的目标语言，不一定等同于模板名。 |
| `experimental` | 该模板是否为 experimental。 |
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

## Generated runtime policy

Generated runtime files 默认必须严格 self-contained：

- 不依赖 `pyfcstm runtime`。
- 不依赖 third-party runtime library。
- 不依赖不稳定、平台绑定明显或版本要求过新的语言/库特性。
- 优先使用目标语言 core features 和长期稳定的 standard library 能力。
- 保持广泛版本和平台兼容。现有期望包括：`python` 模板支持 Python 3.7+，C implementation 使用 C99，C header / harness 保持 C++98-compatible integration paths。

Generated implementation files 应优先服务模型语义、可预测执行和 runtime performance。对 `machine.py`、`machine.c` 这类实现文件来说，人工可读性是次要目标。`machine.h` 这类 public integration surfaces 会被下游集成者阅读，应保持清晰。

已经定义的 formatter 和 linter checks 仍然必须通过。它们的目的，是让生成输出看起来专业并避免明显集成阻力。不要为了风格偏好而扭曲 generated runtime design，尤其不能牺牲性能或语义。

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
- 定义目标语言兼容性、formatter、build、test gates。
- 添加代表性 generated-runtime tests；适用时添加 simulator alignment tests。
- 运行 packaging checks，确保 `pyfcstm/template/index.json`、zip archives、`extract_template` 和源码模板一致。
- 只有仓库级 contract 变化时才更新本手册；单模板变化应更新单模板 README。

## Maintenance workflow

根据改动范围选择最小但足够的验证集：

- 只改根手册：运行 README structure tests；不需要 `make tpl`。
- 改 `templates/<name>/` 下模板源码：运行 `make tpl` 和对应模板测试。
- 改 generated runtime source-template：生成代表性输出，运行 formatter/build/runtime checks，并在适用时验证 generated README examples。
- 改 Python public API 或 pydoc：运行 `make rst_auto` 并审阅生成的 RST diff。

本地迭代时，`SKIP_SLOW_TESTS=1 make unittest` 会跳过 C/C++ native toolchain template tests，同时保留 Python template、simulator、model、DSL、render、verify 测试。除非已通过与该模板 runtime language 相称的检查，否则不要声称模板改动完成。
