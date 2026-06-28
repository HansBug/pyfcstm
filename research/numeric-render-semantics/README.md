# FCSTM 数值表达式渲染语义调研

本目录保存 [issue #280](https://github.com/HansBug/pyfcstm/issues/280) 的可复跑调研资产。调研目标不是比较目标语言的全部数值体系，而是记录 **FCSTM 当前数值表达式经 pyfcstm renderer / template 实际渲染后的目标表达式**，再把这些表达式与目标语言、主流工具链和 Z3 的语义逐步对齐。

## 当前调研工具范围

当前调研工具提供轻量框架、R0 映射工具、C-family smoke 入口、Python/Z3 baseline 入口、Java/Rust native smoke 入口和 C/C++ ↔ Z3 alignment contract 入口；后续 Go/JS/TS 与 exhaustive/shard runner 应继续追加到同一 probe CLI 和 artifact 约定中，而不是替换已有入口。整个调研系列统一禁止修改 `test/` 路径。

| 文件 | 作用 |
|---|---|
| `plan.md` | 子 PR 执行计划、验收命令和边界。 |
| `mapping.md` | R0 render mapping 输出结构和人工阅读指南。 |
| `probes.md` | Probe runner 设计约束；当前累计提供 `env`、`c-smoke`、`cpp-smoke`、`python-z3-baseline`、`java-smoke`、`rust-smoke`、`java-rust-smoke` 和 `c-cpp-z3-alignment` 入口，并说明后续 runner 的共享字段约定。 |
| `schemas/` | 调研 JSON artifact 的轻量契约。 |
| `results/snapshots/` | 可提交的小型 snapshot。 |
| `results/local/` | gitignored heavy / local 输出目录。 |

## 非目标

- 当前 Java/Rust native smoke 不引入 Java/Rust template；仓库暂无 `templates/java` / `templates/rust`，因此相关 case 均记录为 `native_only=true`。
- 当前 Python/Z3 baseline、Java/Rust smoke 与 C/C++ ↔ Z3 alignment 不把 Go、Node 或 TypeScript probe 纳入范围；这些后续入口仍应复用同一 probe harness。
- 本调研工具范围不修改 solver、verify、fixed 或模板语义。
- 本调研工具范围不提交 exhaustive 原始输出。
- 整个调研系列不修改 `test/` 路径；调研自检、native probe、exhaustive/shard harness 放在 `tools/` / `research/` 入口和 gitignored `results/local/` 中，避免污染常规 unittest。

## 快速开始

```bash
python tools/numeric_render_mapping.py \
  --output research/numeric-render-semantics/results/snapshots/render_mapping.json

python tools/numeric_render_mapping.py --check

python tools/numeric_render_probe.py env \
  --output research/numeric-render-semantics/results/local/env.json

python tools/numeric_render_probe.py c-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/c_smoke.json

python tools/numeric_render_probe.py cpp-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/cpp_smoke.json

python tools/numeric_render_probe.py python-z3-baseline \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/snapshots/python_z3_baseline.json

python tools/numeric_render_probe.py python-z3-baseline --check

python tools/numeric_render_probe.py java-smoke \
  --output research/numeric-render-semantics/results/local/java_smoke.json

python tools/numeric_render_probe.py rust-smoke \
  --output research/numeric-render-semantics/results/local/rust_smoke.json

python tools/numeric_render_probe.py java-rust-smoke \
  --output research/numeric-render-semantics/results/snapshots/java_rust_smoke.json

python tools/numeric_render_probe.py java-rust-smoke --check

python tools/numeric_render_probe.py c-cpp-z3-alignment \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/snapshots/c_cpp_z3_alignment.json

python tools/numeric_render_probe.py c-cpp-z3-alignment --check
```

`--check` 是 R0 mapping、Python/Z3 baseline、Java/Rust smoke 和 C/C++ ↔ Z3 alignment contract 的调研自检入口；`c-smoke` / `cpp-smoke` 是 C-family smoke probe 入口，summary 会引用 R0 `mapping_sha256`，并把 compile / link / runtime / sanitizer findings 记录成结果而不是命令失败。`python-z3-baseline` 默认读取同一份 R0 snapshot，并在 `--check` 中额外与 live mapping 做 drift 校验。`java-smoke` / `rust-smoke` 会把缺少 `javac` / `rustc` 记录为 structured unavailable；`java-rust-smoke` 是唯一写入 `results/snapshots/java_rust_smoke.json` 的聚合入口，避免单语言输出互相覆盖。Java notes 以 Java Language Specification（JLS）和 `Math.*Exact` API 为依据；Rust notes 以 Rust Reference 和 `std::primitive::i32` 的 `wrapping_*` / `checked_*` / `overflowing_*` / `saturating_*` API 为依据。`c-cpp-z3-alignment` 生成 committed alignment snapshot，按 `value_expr + obligations + outcome` 三元组记录 C/C++ render path 到 Z3 profile 的候选值、definedness obligation 和 outcome；其 `--check` 校验 schema、required 字段、outcome 枚举、render path / operator 覆盖，以及 mapping、Python/Z3 baseline 和 C-family smoke fact digest。后续语言 smoke 和 exhaustive/shard runner 也应继续使用 `tools/` / `research/` 下的同一 probe CLI、自检和 artifact 约定，而不是修改 `test/` 或重建独立 harness。`results/local/` 被 `.gitignore` 忽略，适合放本机探测结果和后续 heavy probe 输出。
