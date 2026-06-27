# 调研结果目录

| 路径 | 是否提交 | 用途 |
|---|---|---|
| `snapshots/` | 是 | 小型、可审阅、可复跑的 mapping 或 summary snapshot，例如 `render_mapping.json` 与 `python_z3_baseline.json`。 |
| `local/` | 否 | 本机环境报告、native 编译产物、heavy exhaustive JSONL、临时 shard 输出。 |

`local/` 已由仓库 `.gitignore` 忽略。
