# pyfcstm diagnostics showcase

Layer 2 PR-A 端到端 diagnostic 对齐演示。打开任何 `.fcstm` 文件，VSCode 应当显示对应的 `E_*` / `W_*` code（左下 Problems 面板）。

## 使用方法

1. 安装新构建的 vsix：
   ```bash
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix
   ```
   或者在 VSCode 里打开命令面板（Cmd/Ctrl+Shift+P）→ `Extensions: Install from VSIX...` 选择上面的 vsix。

2. 用 VSCode 打开本 `demo/diagnostics-showcase/` 目录。

3. 逐个打开 `01-...fcstm`、`02-...fcstm`... 文件，应该在 Problems 面板看到对应的 diagnostic code。每个文件顶部注释列出预期诊断的 code 名和行号。

## 当前 PR-A 已对齐的 code 列表

| code | 严重度 | 触发 fixture |
|---|---|---|
| `E_UNDEFINED_VAR` | error | `01-undefined-variable.fcstm`, `11-temporary-read-before-assign.fcstm`（含 `is_temporary: true` data） |
| `E_DUPLICATE_VAR` | error | `02-duplicate-variable.fcstm` |
| `E_MISSING_STATE` | error | `03-missing-state.fcstm`（源侧失败） |
| `E_DANGLING_TRANSITION` | error | `03-missing-state.fcstm`（目标侧失败） |
| `E_DUPLICATE_STATE` | error | `04-duplicate-state.fcstm` |
| `E_DUPLICATE_FUNCTION_NAME` | error | `05-duplicate-function-name.fcstm` |
| `E_PSEUDO_NOT_LEAF` | error | `06-pseudo-not-leaf.fcstm` |
| `E_DURING_ASPECT_INVALID` | error | `07-during-aspect-invalid.fcstm` |
| `E_INITIAL_TRANSITION_INVALID` | error | `08-initial-transition-invalid.fcstm` |
| `E_NAMED_FUNCTION_REF_NOT_FOUND` | error | `09-named-function-ref-not-found.fcstm` |
| `E_FORCED_TRANSITION_EXPANSION` | error | `10-forced-transition-expansion.fcstm` |
| `W_UNREACHABLE_STATE` | warning | `12-warnings-mixed.fcstm` |
| `W_GUARD_CONST_FALSE` | warning | `12-warnings-mixed.fcstm` |
| `W_UNUSED_EVENT` | warning | `12-warnings-mixed.fcstm` |

## 暂未在 jsfcstm 端 emit 的 code（pyfcstm 仍 emit）

PR-A 内确认但尚未在 jsfcstm 端实现，留给后续 PR：

| code | 原因 |
|---|---|
| `E_EVENT_REF_INVALID` | jsfcstm grammar 在 parser 阶段就拦截了多数 event ref 语法错误；正式接入留 PR-B |
| `E_EVENT_NOT_FOUND` | jsfcstm 当前对未声明的 event 是 implicit 创建（跟 pyfcstm 一致），但 `resolve_event()` 等显式 API 路径未对齐到 jsfcstm，PR-B 决策 |
| `E_TYPE_MISMATCH` | 需要从零写 jsfcstm 端 expr 类型推断器，工作量约 8-12h，PR-A.5 / PR-B 处理 |
| `E_IMPORT_*` 系列 | jsfcstm workspace 层已有 import 错误检测，但当前用 `W_` 级；PR-B 收口到 `E_IMPORT_*` |

## 验收清单

- [ ] 每个 demo fcstm 在 VSCode 里都有对应 squiggle（红色 = error，黄色 = warning）
- [ ] Problems 面板能看到 code 列（`E_*` / `W_*` 前缀）
- [ ] Hover 在错误处显示对应的 message
- [ ] 同一份 .fcstm 用 `python -c "from pyfcstm.dsl import ...; ..."` 跑一遍，pyfcstm 端 emit 出来的 ModelDiagnostic.code 集合跟 jsfcstm 一致（可以用 `pyfcstmcli` 直接验证）
