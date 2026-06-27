# Probe 设计说明

PR-1 提供 `tools/numeric_render_probe.py env`，用于输出本地 Python、平台和可用命令清单；PR-2 增加 `c-smoke` / `cpp-smoke`，用于从 R0 `render_mapping.json` 读取 C-family 渲染路径并编译运行小型 smoke 程序。PR-1 的契约校验由 `tools/numeric_render_mapping.py --check` 承担。整个调研系列都不新增 `test/` 路径；任何会调用 native compiler、Node.js、Java、Rust、Go 或 Z3 求解的 probe 都应继续落在 `tools/` / `research/` 与 gitignored `results/local/` 下。

## C/C++ smoke runner

```bash
python tools/numeric_render_probe.py c-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/c_smoke.json
python tools/numeric_render_probe.py cpp-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/cpp_smoke.json
```

Smoke summary 必须写入 `source_mapping_sha256`，并与所读取 mapping 的 `mapping_sha256` 一致。`cases[]` 至少覆盖 `round`、`abs`、`sign`、`cbrt`、`pow`、带符号 shift、整数 division 和除零风险。缺 compiler、缺 sanitizer flag 或 partial toolchain availability 通过 `toolchain`、`sanitizer`、`status` 和 `reason` 字段结构化记录；编译失败、链接失败、运行失败和 sanitizer failure 都是有效调研结果。

## 后续 runner 约束

- runner 必须读取 R0 `render_mapping.json`，不要手写与 renderer 脱节的表达式表。
- 编译失败、链接失败、运行时异常、sanitizer trap 都是结果，不得静默替换为“更合理”的 helper。
- 每次运行前探测 CPU、内存、磁盘、工具链版本和可承受并行度。
- Heavy 输出写入 `results/local/`，小型 summary / digest 才能提交。
- 8-bit exhaustive 可以作为调研阶段强验证；16-bit 必须支持 shard / resume / digest。
