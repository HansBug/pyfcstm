# R0 映射说明

`tools/numeric_render_mapping.py` 生成 `render_mapping.json`，并通过 `python tools/numeric_render_mapping.py --check` 执行不依赖 `test/` 路径的轻量契约自检。该文件用于回答：当前 pyfcstm 把 FCSTM 数值表达式渲染成什么目标表达式，后续 probe 应该测试哪条真实路径。

## 必须保留的层次

| 层次 | JSON 字段 | 说明 |
|---|---|---|
| Builtin expression renderer | `builtin_expr_styles` | `pyfcstm.render.expr` 内置样式，如 `c`、`cpp`、`python`、`go`。 |
| Builtin statement renderer | `builtin_stmt_styles` | `pyfcstm.render.statement` 内置 statement 样式。 |
| Template expression override | `templates.*.expr_styles` | `templates/*/config.yaml` 中的 `expr_styles`。 |
| Statement expression override | `templates.*.stmt_styles.*.expr_templates` | statement 渲染时的表达式 override，例如 Python runtime `_s(...)`。 |
| Helper inventory | `renderer_helper_inventory` | 会改变最终表达式语义或 probe 入口的 helper。 |
| Packaged template metadata | `packaged_templates` | `pyfcstm/template/index.json` 元数据、archive 声明和 source digest；不 hash gitignored zip payload。 |
| C++ 双路径 | `cxx_paths` | 区分 `_CPP_STYLE` standalone 与 `templates/cpp*` 的 `base_lang: c` 生成路径。 |
| 运行时语义备注 | `runtime_semantics_notes` | 记录不能由当前 mapping 自动推出、但后续不能猜测的语义点。 |

## `~` 备注

当前 parser 的数值一元规则只接收 `+` / `-`，因此 PR-1 不能假装已经有运行时 `~` 行为。R0 snapshot 仍显式记录 `~`，用于提醒后续 solver/template 工作不要直接按 Z3 或 C 的 bitwise not 语义猜测。
