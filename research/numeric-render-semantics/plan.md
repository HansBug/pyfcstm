# 执行计划

## 原则

1. 以当前 renderer / template 的实际渲染结果为准。
2. 只覆盖 FCSTM 数值表达式，不覆盖逻辑表达式本身。
3. C/C++ 是默认定长语义设计的 P0 参考；Java/Rust 次之；Go/JS/TS 作为未来模板风险面。
4. Z3 是 solver / verify 编码目标，不把 BitVec natural wrap 直接等同于 C/C++ signed semantics。
5. Heavy exhaustive 输出只写入 `results/local/`，不得提交进 git。
6. 整个调研系列不修改 `test/` 路径；调研校验、native probe、exhaustive/shard harness 通过 `tools/` / `research/` 自检入口和 gitignored `results/local/` 完成，避免把一次性研究实验放进常规 unittest。

## PR-1 验收

```bash
python tools/numeric_render_mapping.py \
  --output research/numeric-render-semantics/results/snapshots/render_mapping.json

python tools/numeric_render_mapping.py --check

git check-ignore research/numeric-render-semantics/results/local/dummy-output.jsonl

make rst_auto
```

## PR-3 验收

```bash
python tools/numeric_render_mapping.py --check

python tools/numeric_render_probe.py env \
  --output research/numeric-render-semantics/results/local/env.json

python tools/numeric_render_probe.py python-z3-baseline \
  --output research/numeric-render-semantics/results/snapshots/python_z3_baseline.json

python tools/numeric_render_probe.py python-z3-baseline --check

git check-ignore research/numeric-render-semantics/results/local/dummy-output.jsonl

SKIP_SLOW_TESTS=1 make unittest
```

`python_z3_baseline.json` 只保存小型可审阅 snapshot：Python render/runtime 样例、Z3 `Int` / `Real` / `BitVec` / `FP` capability matrix、mapping digest、generator commit 和工具链版本。它不保存 heavy exhaustive 原始输出，也不把 Python 无限精度行为提升为默认定长 profile。

## PR-6A 验收

```bash
python tools/numeric_render_mapping.py --check

python tools/numeric_render_probe.py python-z3-baseline --check

python tools/numeric_render_probe.py c-cpp-z3-alignment \
  --output research/numeric-render-semantics/results/snapshots/c_cpp_z3_alignment.json

python tools/numeric_render_probe.py c-cpp-z3-alignment --check

git check-ignore research/numeric-render-semantics/results/local/dummy-output.jsonl

SKIP_SLOW_TESTS=1 make unittest
```

`c_cpp_z3_alignment.json` 是 C/C++ ↔ Z3 对齐试点 snapshot。它按 C-family render path 展开每个 FCSTM numeric semantic case，并为每行记录 `value_expr + obligations + outcome`，同时保留 `render_path`、`target_semantics`、`definedness`、`z3_sort`、`z3_profile`、`evidence` 和 `counterexamples`。该 snapshot 不把 BitVec wrap 当作 C/C++ signed semantics；signed overflow、除零、`MIN/-1`、signed shift、math function 可用性和 writeback narrowing 都必须作为 obligation、profile-dependent、unsupported、compile_failed 或 counterexample 表达。

`c-cpp-z3-alignment --check` 是 D6a 的稳定 validator 命令。它不依赖本机 native toolchain；live compile / sanitizer 输出仍应写入 `results/local/`，而 committed snapshot 只保存 deterministic render facts、schema fields 和 digest。

## 后续子 PR

| 子 PR | 状态 | 内容 |
|---|---|---|
| PR-1 | 🟢 已完成 | 落库框架、R0 mapping、env stub、轻量 schema；确立整个调研系列不修改 `test/` 路径。 |
| PR-2 | 🟢 已完成 | C/C++ smoke probe。 |
| PR-3 | 🟢 已完成 | Python + Z3 基线、`python-z3-baseline` probe、small snapshot 与 schema。 |
| PR-4 | 🟡 后续 | Java / Rust smoke probe。 |
| PR-5 | 🟡 后续 | Go / JS / TS smoke probe。 |
| PR-6A | 🟡 当前 | C/C++ ↔ Z3 对齐试点、alignment schema、snapshot 与 validator。 |
| PR-6B~6D | 🟡 后续 | 按 6A schema 套用 Python/DSL、Java/Rust、Go/JS/TS。 |
| PR-6E | 🟡 后续 | 8-bit exhaustive、16-bit shard / sampled、跨语言 mismatch 与 counterexample 汇总。 |
| PR-7 | 🟡 后续 | 最终 Z3 数值语义对齐规范与 solver / fixed / template 产品化方案。 |
