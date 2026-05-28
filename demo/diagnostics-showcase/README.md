# pyfcstm diagnostics showcase

Layer 2 PR-A 端到端 diagnostic 对齐演示。打开任何 `.fcstm` 文件，VSCode 应当显示对应的 `E_*` / `W_*` code（Problems 面板）。

## 使用方法

1. 安装新构建的 vsix：
   ```bash
   make vscode_install     # uninstall + install one-shot
   ```
2. 用 VSCode 打开本 `demo/diagnostics-showcase/` 目录
3. 逐个打开 `01-...fcstm`、`02-...fcstm` ...（**13-16 是多文件目录**，要先打开它们的子目录）；每个文件顶部注释列出预期 diagnostic code 和行号

## 已对齐的 code（14 个 E_* + 3 个 W_*）

### 单文件 fixture

| 序号 | 文件 | code |
|---|---|---|
| 01 | `01-undefined-variable.fcstm` | `E_UNDEFINED_VAR`（普通 + `is_temporary=true`） |
| 02 | `02-duplicate-variable.fcstm` | `E_DUPLICATE_VAR` |
| 03 | `03-missing-state.fcstm` | `E_MISSING_STATE` + `E_DANGLING_TRANSITION` |
| 04 | `04-duplicate-state.fcstm` | `E_DUPLICATE_STATE` |
| 05 | `05-duplicate-function-name.fcstm` | `E_DUPLICATE_FUNCTION_NAME` |
| 06 | `06-pseudo-not-leaf.fcstm` | `E_PSEUDO_NOT_LEAF` |
| 07 | `07-during-aspect-invalid.fcstm` | `E_DURING_ASPECT_INVALID` |
| 08 | `08-initial-transition-invalid.fcstm` | `E_INITIAL_TRANSITION_INVALID` |
| 09 | `09-named-function-ref-not-found.fcstm` | `E_NAMED_FUNCTION_REF_NOT_FOUND` |
| 10 | `10-forced-transition-expansion.fcstm` | `E_FORCED_TRANSITION_EXPANSION` |
| 11 | `11-temporary-read-before-assign.fcstm` | `E_UNDEFINED_VAR` (`is_temporary: true`) |
| 12 | `12-warnings-mixed.fcstm` | `W_UNREACHABLE_STATE` + `W_GUARD_CONST_FALSE` + `W_UNUSED_EVENT` |

### 多文件 import fixture（打开 `host.fcstm` / `a.fcstm`）

| 序号 | 目录 | code |
|---|---|---|
| 13 | `13-import-not-found/host.fcstm` | `E_IMPORT_NOT_FOUND` |
| 14 | `14-import-alias-conflict/host.fcstm` | `E_IMPORT_ALIAS_CONFLICT`（含 alias vs sibling state 检查） |
| 15 | `15-import-duplicate-mapping/host.fcstm` | `E_IMPORT_DUPLICATE_MAPPING` |
| 16 | `16-import-circular/a.fcstm` | `E_IMPORT_CIRCULAR` |

## 不在 jsfcstm 端 emit 的 code（pyfcstm 仍登记）

| code | 原因 |
|---|---|
| `E_EVENT_REF_INVALID` / `E_EVENT_NOT_FOUND` | pyfcstm/jsfcstm 都对未声明 event 做 implicit 创建；这两个 code 只在显式 `resolve_event(ref)` API 调用时触发，**不进静态分析层**。jsfcstm 当前没有等价 query API |
| `E_TYPE_MISMATCH` | pyfcstm/jsfcstm grammar **严格分离 num/cond expression**，几乎所有 type 不匹配的 DSL 在 parse 阶段就被拒绝；jsfcstm 端实现了完整 expr 类型推断器作为 safety net（单元测试覆盖：`test/analyzers-type-mismatch.test.ts`），但实际不通过 parse 触发 |
| `E_IMPORT_MAPPING_INVALID` | pyfcstm imports.py 收口 PR-A 内 codes.yaml 占位；jsfcstm 端实际语法报错由 grammar/semantic 层多分支处理。后续 PR 内继续收紧 |

## 自动化测试

每个 demo fixture 都有对应的内联 mocha 测试在
`editors/jsfcstm/test/diagnostics-showcase-demos.test.ts`，DSL 文本直接写在 .ts 文件里，**不读取外部 .fcstm**。`demo/diagnostics-showcase/` 下的同名文件只是 owner 视觉验收的镜像材料。

跑测试：
```bash
cd editors/jsfcstm && npm run test:unit
```
