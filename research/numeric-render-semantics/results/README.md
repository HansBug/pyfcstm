# 调研结果目录

| 路径 | 是否提交 | 用途 |
|---|---|---|
| `snapshots/` | 是 | 小型、可审阅、可复跑的 mapping、baseline、summary 或 alignment snapshot，例如 `render_mapping.json`、`python_z3_baseline.json`、`java_rust_smoke.json`、`java_rust_smoke.json.sha256` 与 `c_cpp_z3_alignment.json`。 |
| `local/` | 否 | 本机环境报告、native 编译产物、heavy exhaustive JSONL、临时 shard 输出。 |

`local/` 已由仓库 `.gitignore` 忽略。
