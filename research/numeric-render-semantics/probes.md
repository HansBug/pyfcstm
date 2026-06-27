# Probe 设计说明

`tools/numeric_render_probe.py env` 用于输出本地 Python、平台和可用命令清单；`c-smoke` / `cpp-smoke` 用于从 R0 `render_mapping.json` 读取 C-family 渲染路径并编译运行小型 smoke 程序。R0 mapping 的契约校验由 `tools/numeric_render_mapping.py --check` 承担。后续 Python/Z3 baseline、语言 smoke 和 exhaustive/shard runner 应继续追加到同一 probe CLI、同一 mapping digest 约定和同一 artifact 目录结构中，而不是重建独立 harness。整个调研系列都不新增 `test/` 路径；任何会调用 native compiler、Node.js、Java、Rust、Go 或 Z3 求解的 probe 都应继续落在 `tools/` / `research/` 与 gitignored `results/local/` 下。

## C/C++ smoke runner

```bash
python tools/numeric_render_probe.py c-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/c_smoke.json
python tools/numeric_render_probe.py cpp-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/cpp_smoke.json
```

Smoke summary 必须写入 `source_mapping_sha256`，并与所读取 mapping 的 `mapping_sha256` 一致。`cases[]` 至少覆盖 `round`、`abs`、`sign`、`cbrt`、`pow`、带符号 shift、整数 division 和除零风险。每个 case 都应保留可供 PR-6 汇总的 join 字段：`operator`、`fcstm_expression`、`case_id`、`render_path` 和 `render_expression`。跨 C/C++、Python 与 Z3 的语义汇总应优先按 `operator` + `fcstm_expression`（或后续显式引入的 `semantic_case_id`）聚合；当前 `case_id` 允许保持 render-path scoped，用于区分同一语义表达式在不同 renderer 路径下的具体 smoke case，`render_path` / `render_expression` 则继续记录目标语言渲染差异。缺 compiler、缺 sanitizer flag 或 partial toolchain availability 通过 `toolchain`、`sanitizer`、`status` 和 `reason` 字段结构化记录；编译失败、链接失败、运行失败和 sanitizer failure 都是有效调研结果。

## 后续 runner 约束

- runner 必须读取 R0 `render_mapping.json`，不要手写与 renderer 脱节的表达式表。
- 后续 runner 应保留可跨 artifact join 的 `operator` / `fcstm_expression` 字段，并在需要时补充稳定的 `semantic_case_id`；`case_id` 可继续作为单个 runner 内的 render-path scoped case 标识，避免 PR-6 为 C/C++、Python 和 Z3 再造第三套对齐 case model。
- 编译失败、链接失败、运行时异常、sanitizer trap 都是结果，不得静默替换为“更合理”的 helper。
- 每次运行前探测 CPU、内存、磁盘、工具链版本和可承受并行度。
- Heavy 输出写入 `results/local/`，小型 summary / digest 才能提交。
- 8-bit exhaustive 可以作为调研阶段强验证；16-bit 必须支持 shard / resume / digest。
