# Probe 设计说明

`tools/numeric_render_probe.py env` 用于输出本地 Python、平台和可用命令清单；`c-smoke` / `cpp-smoke` 用于从 R0 `render_mapping.json` 读取 C-family 渲染路径并编译运行小型 smoke 程序；`python-z3-baseline` 用于从同一 R0 snapshot 记录 Python renderer / Python template / statement override 事实和 Z3 capability matrix；`java-smoke` / `rust-smoke` / `java-rust-smoke` 在同一 dispatcher 中追加 Java/Rust native smoke facts。R0 mapping 的契约校验由 `tools/numeric_render_mapping.py --check` 承担。后续语言 smoke 和 exhaustive/shard runner 应继续追加到同一 probe CLI、同一 mapping digest 约定和同一 artifact 目录结构中，而不是重建独立 harness。整个调研系列都不新增 `test/` 路径；任何会调用 native compiler、Node.js、Java、Rust、Go 或 Z3 求解的 probe 都应继续落在 `tools/` / `research/` 与 gitignored `results/local/` 下。

## 当前累计入口

```bash
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
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/java_smoke.json
python tools/numeric_render_probe.py rust-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/local/rust_smoke.json
python tools/numeric_render_probe.py java-rust-smoke \
  --mapping research/numeric-render-semantics/results/snapshots/render_mapping.json \
  --output research/numeric-render-semantics/results/snapshots/java_rust_smoke.json
python tools/numeric_render_probe.py java-rust-smoke --check
```

## C/C++ smoke runner

Smoke summary 必须写入 `source_mapping_sha256`，并与所读取 mapping 的 `mapping_sha256` 一致。`cases[]` 至少覆盖 `round`、`abs`、`sign`、`cbrt`、`pow`、带符号 shift、整数 division 和除零风险。每个 case 都应保留可供 PR-6 汇总的 join 字段：`operator`、`fcstm_expression`、`case_id`、`render_path` 和 `render_expression`。跨 C/C++、Python 与 Z3 的语义汇总应优先按 `operator` + `fcstm_expression`（或显式 `semantic_case_id`）聚合；当前 `case_id` 允许保持 render-path scoped，用于区分同一语义表达式在不同 renderer 路径下的具体 smoke case，`render_path` / `render_expression` 则继续记录目标语言渲染差异。缺 compiler、缺 sanitizer flag 或 partial toolchain availability 通过 `toolchain`、`sanitizer`、`status` 和 `reason` 字段结构化记录；编译失败、链接失败、运行失败和 sanitizer failure 都是有效调研结果。

## Python/Z3 baseline runner

`python-z3-baseline` 默认读取 `research/numeric-render-semantics/results/snapshots/render_mapping.json`，避免手写与 renderer 脱节的表达式表；`--check` 会同时校验 committed `python_z3_baseline.json`、专用 schema、semantic invariants、snapshot-vs-live payload，以及 committed R0 mapping 与 live render mapping 的 drift。baseline 的 `alignment_cases[]` 使用与 smoke runner 相同的 join 字段：`case_id`、`operator`、`fcstm_expression`、`render_path` 和 `render_expression`，并额外提供 `semantic_case_id` 方便 PR-6 先按语义表达式聚合，再按 render path 展开。

Python 输出作为 P3 / 无限精度 / 仿真兼容基线使用，不作为后续 solver / verify 的定长默认语义。Z3 capability matrix 记录 `Int` / `Real` / `BitVec` / `FP` 的 `exact`、`approximate`、`uninterpreted` 或 `unsupported` 等级；当前 baseline 避免记录不稳定 solver model 值，只记录可复跑的 capability、render path 和代表性 counterexample。


## Java/Rust native smoke runner

当前仓库没有 `templates/java` 或 `templates/rust`，因此 Java/Rust smoke 不伪造 template render path；所有 case 都显式记录 `native_only=true` 与 `native_only_reason="no_java_or_rust_template_in_current_repository"`。为便于 PR-6C / PR-6E 复用同一 join 口径，每条 Java/Rust case 仍保留 `case_id`、`operator`、`fcstm_expression`、`render_path` 和 `render_expression`，并额外记录 `language`、`profile`、`native_api_family`、`source_note_ids`、`status` 和 `outcome`。

`java-smoke` 和 `rust-smoke` 是单语言 payload，推荐写入 gitignored `results/local/`；`java-rust-smoke` 是聚合 payload，唯一负责生成可提交的 `results/snapshots/java_rust_smoke.json`，避免两条单语言命令通过 `_write_payload` 覆盖同一路径。`--check` 对 Java/Rust 做 schema、case plan、shared join key、R0 mapping live drift 和 committed aggregate snapshot 校验；由于 `javac`、`java`、`rustc`、`cargo` availability 在本地与 CI 之间可能不同，check 校验结构和事实覆盖，不要求 stdout 与本机 toolchain 结果逐字一致。

Java smoke 的 source-backed notes 指向 Java Language Specification（JLS）和 Java SE `Math` API，覆盖 integer overflow、division / remainder、shift count masking、narrowing conversion、`Math.pow` / `Math.round` 与 `Math.addExact` / `Math.multiplyExact`。Rust smoke 的 source-backed notes 指向 Rust Reference 和 Rust standard library，覆盖 debug / release / `overflow-checks`、division / remainder、invalid shift、cast，以及 `std::primitive::i32` 的 `wrapping_*`、`checked_*`、`overflowing_*` 和 `saturating_*` families。

## 后续 runner 约束

- runner 必须读取 R0 `render_mapping.json`，不要手写与 renderer 脱节的表达式表。
- 后续 runner 应保留可跨 artifact join 的 `operator` / `fcstm_expression` 字段，并在需要时补充稳定的 `semantic_case_id`；`case_id` 可继续作为单个 runner 内的 render-path scoped case 标识，避免 PR-6 为 C/C++、Python 和 Z3 再造第三套对齐 case model。
- 编译失败、链接失败、运行时异常、sanitizer trap 都是结果，不得静默替换为“更合理”的 helper。
- 每次运行前探测 CPU、内存、磁盘、工具链版本和可承受并行度。
- Heavy 输出写入 `results/local/`，小型 summary / digest 才能提交。
- 8-bit exhaustive 可以作为调研阶段强验证；16-bit 必须支持 shard / resume / digest。
