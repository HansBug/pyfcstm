# python 模板维护手册

`python` 是内置模板，用于为一个 FCSTM model 生成原生 Python 状态机运行时。本文件是
`templates/python/` 模板源码的维护者手册，不会被复制到生成目录。生成目录里的用户手册由
`README.md.j2` / `README_zh.md.j2` 生成。

## 目标与非目标

当目标产物是一个可导入、无运行时第三方依赖的 Python runtime，并且需要嵌入应用、测试、示例或小型自动化脚本时，应使用该模板。

该模板不是 simulator 实现，生成后不应依赖 `pyfcstm` runtime package。它也不应演变成围绕生成代码的大型框架：下游用户如果需要改变运行逻辑，应修改 FCSTM DSL 并重新生成，而不是长期手改生成出来的运行时代码。

## 源码布局与生成产物

| 模板源码 | 维护职责 | 生成产物 |
| --- | --- | --- |
| `machine.py.j2` | runtime source template | `machine.py` |
| `README.md.j2` | 英文生成物用户手册 | `README.md` |
| `README_zh.md.j2` | 中文生成物用户手册 | `README_zh.md` |
| `config.yaml` | renderer 配置、Python 语句渲染、Jinja helper 和 ignore 规则 | 不复制 |
| `template.json` | 内置模板 metadata | 不复制 |
| `README.md` / `README_zh.md` | 模板维护手册 | renderer 不复制，但会进入 packaged template archives |

`config.yaml` 会忽略 `README.md`、`README_zh.md` 和 `template.json`，避免这些维护文件泄露到生成目录。但 `make tpl` 会打包完整模板源码目录，因此修改这些维护 README 后也必须通过 `make tpl` 刷新并验证本地生成的 `pyfcstm/template/python.zip`。该 archive 在普通 checkout 中被 git 忽略；setup 和 packaging 命令会从源码重新生成它。

## 兼容性与运行时依赖边界

生成的 `machine.py` 默认应保持以下约束：

- 支持 Python 3.7 或更新版本。
- 只依赖 Python 标准库。
- 不从 `pyfcstm` 或仓库测试 helper 导入内容。
- 不引入第三方 runtime dependency。
- 不无故使用会抬高最低 Python 版本的语法。

Jinja2、YAML 解析、renderer filters 和 statement renderers 这类 generation-time 依赖属于 `pyfcstm` 生成阶段，不能变成 generated runtime 的运行要求。

## 公开集成面

生成代码的用户主要和一个由 root state 派生命名的 machine class 交互。稳定集成面应集中在：

- 构造生成的 machine class；
- 使用生成 API 支持的 event name 或 event collection 调用 `cycle(...)`；
- 读取当前 state 和 persistent variable snapshot；
- 使用显式 state 和完整变量快照进行 hot start；
- 通过 subclass 覆盖 abstract lifecycle hook。

Abstract lifecycle actions 应保持可发现的稳定 protected hook method names。Hook 命名必须能清楚映射回 DSL abstract action name，使 DSL 作者可以借助 IDE 补全快速找到需要覆盖的方法。

## 语义与对齐预期

生成的 Python runtime 是产品化产物，不是 `pyfcstm.simulate.SimulationRuntime` 的薄封装。但它的可见行为仍必须和 simulator 在受支持的 FCSTM 语义上保持一致：

- cold start 与 hot start；
- initial transition 和 composite entry 顺序；
- lifecycle action 顺序，包括 aspect actions；
- event scoping 和 transition priority；
- guard、effect、rollback 和 validation 行为；
- abstract hook 的调用时机和 context values。

语义对齐测试在本 README 之外维护。只修改本文件这类文档时，不应改动这些测试；修改 runtime template 时则必须把它们作为正确性 gate。

## 生成实现策略

生成的 `machine.py` 可以为了可预测 runtime 行为采用直接的生成式控制流，而不是优先照顾人工阅读体验。Public class API 和 generated README 应保持清楚；实现主体可以更机械，只要它仍然确定、自包含并且 formatter-stable。

Formatter 和 linter checks 是专业度和集成卫生的质量门槛。它们不应迫使 runtime design 牺牲 FCSTM 语义或性能。

## 维护流程

根据改动范围选择最小但足够的验证集：

1. 只改模板维护 README 时，审阅中英文文件的章节对等和事实一致性。
2. 提交仓库改动前运行 `make rst_auto`。本 README 通常不应触发 generated RST diff。
3. 修改 `templates/python/` 下任何文件后都运行 `make tpl`，包括本 README，因为 packaged built-in template archives 会包含模板源码目录。
4. 检查 packaged asset 变化。README-only 改动应刷新本地生成的 `pyfcstm/template/python.zip` archive；由于 zip archives 在普通 checkout 中被 git 忽略，tracked `pyfcstm/template/index.json` 通常应保持内容等价。
5. 修改 runtime template 时，生成代表性产物并运行 Python template tests 和 simulator-alignment tests。

常用命令：

```bash
make rst_auto
make tpl
pytest test/template/python -v
SKIP_SLOW_TESTS=1 make unittest
```

## 语言特定验证

代表性生成 `machine.py` 应满足：

```bash
ruff check path/to/generated/machine.py
ruff format --check path/to/generated/machine.py
```

生成代码应在用户不手工修改的情况下保持 lint-clean 和 formatter-stable。如果极少数生成结构确实需要例外，例外应保持窄范围，并在模板中说明它服务的 runtime 语义或兼容性理由。

## 文档分层

保持三层文档职责分离：

- 本文件说明如何维护 `python` 模板；
- `README.md.j2` / `README_zh.md.j2` 说明如何使用某个生成目录；
- 根级 `templates/README.md` / `README_zh.md` 说明仓库级模板系统规则。

不要把 packaging internals 放进 generated README。只看到生成目录的下游用户或 LLM 应学习如何实例化并运行 machine，而不是学习仓库如何打包模板。
