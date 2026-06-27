# Probe 设计说明

PR-1 只提供 `tools/numeric_render_probe.py env`，用于输出本地 Python、平台和可用命令清单；PR-1 的契约校验由 `tools/numeric_render_mapping.py --check` 承担。整个调研系列都不新增 `test/` 路径；任何会调用 native compiler、Node.js、Java、Rust、Go 或 Z3 求解的 probe 都应在后续子 PR 中继续落在 `tools/` / `research/` 与 gitignored `results/local/` 下。

## 后续 runner 约束

- runner 必须读取 R0 `render_mapping.json`，不要手写与 renderer 脱节的表达式表。
- 编译失败、链接失败、运行时异常、sanitizer trap 都是结果，不得静默替换为“更合理”的 helper。
- 每次运行前探测 CPU、内存、磁盘、工具链版本和可承受并行度。
- Heavy 输出写入 `results/local/`，小型 summary / digest 才能提交。
- 8-bit exhaustive 可以作为调研阶段强验证；16-bit 必须支持 shard / resume / digest。
