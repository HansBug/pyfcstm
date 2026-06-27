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

## 后续子 PR

| 子 PR | 状态 | 内容 |
|---|---|---|
| PR-1 | 🟡 当前 | 落库框架、R0 mapping、env stub、轻量 schema；确立整个调研系列不修改 `test/` 路径。 |
| PR-2 | 🟡 后续 | C/C++ smoke probe。 |
| PR-3 | 🟡 后续 | Python + Z3 基线。 |
| PR-4 | 🟡 后续 | Java / Rust smoke probe。 |
| PR-5 | 🟡 后续 | Go / JS / TS smoke probe。 |
| PR-6 | 🟡 后续 | 8-bit exhaustive 与 16-bit shard harness。 |
| PR-7 | 🟡 后续 | 汇总报告与 solver / fixed / template 后续建议。 |
