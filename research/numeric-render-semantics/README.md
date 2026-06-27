# FCSTM 数值表达式渲染语义调研

本目录保存 [issue #280](https://github.com/HansBug/pyfcstm/issues/280) 的可复跑调研资产。调研目标不是比较目标语言的全部数值体系，而是记录 **FCSTM 当前数值表达式经 pyfcstm renderer / template 实际渲染后的目标表达式**，再把这些表达式与目标语言、主流工具链和 Z3 的语义逐步对齐。

## 当前 PR-1 范围

PR-1 先落库轻量框架和 R0 映射工具；整个调研系列统一禁止修改 `test/` 路径：

| 文件 | 作用 |
|---|---|
| `plan.md` | 子 PR 执行计划、验收命令和边界。 |
| `mapping.md` | R0 render mapping 输出结构和人工阅读指南。 |
| `probes.md` | 后续 probe runner 设计约束；PR-1 仅提供 `env` stub。 |
| `schemas/` | 调研 JSON artifact 的轻量契约。 |
| `results/snapshots/` | 可提交的小型 snapshot。 |
| `results/local/` | gitignored heavy / local 输出目录。 |

## 非目标

- PR-1 不运行 C/C++、Java、Rust、Go、Node 或 TypeScript probe。
- PR-1 不修改 solver、verify、fixed 或模板语义。
- PR-1 不提交 exhaustive 原始输出。
- 整个调研系列不修改 `test/` 路径；调研自检、native probe、exhaustive/shard harness 放在 `tools/` / `research/` 入口和 gitignored `results/local/` 中，避免污染常规 unittest。

## 快速开始

```bash
python tools/numeric_render_mapping.py \
  --output research/numeric-render-semantics/results/snapshots/render_mapping.json

python tools/numeric_render_mapping.py --check

python tools/numeric_render_probe.py env \
  --output research/numeric-render-semantics/results/local/env.json
```

`--check` 是 PR-1 的调研自检入口；后续子 PR 也应继续使用 `tools/` / `research/` 下的自检和 probe 入口，而不是修改 `test/`。`results/local/` 被 `.gitignore` 忽略，适合放本机探测结果和后续 heavy probe 输出。
