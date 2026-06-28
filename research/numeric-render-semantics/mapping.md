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

## PR-3 Python/Z3 baseline 使用方式

`tools/numeric_render_probe.py python-z3-baseline` 会读取 live R0 mapping，并在 snapshot 中记录 `source_mapping_sha256` / `render_mapping_sha256`。如果 R0 mapping digest 变化，`python-z3-baseline --check` 会要求重新生成 Python/Z3 baseline snapshot，避免 PR-6 / PR-7 读取过期的 render path 事实。


## PR-4 Java/Rust smoke 使用方式

`tools/numeric_render_probe.py java-rust-smoke` 继续默认读取 `research/numeric-render-semantics/results/snapshots/render_mapping.json`，并在 payload 中记录 `source_mapping_sha256` / `render_mapping_sha256`，以便后续 `--check` 对 committed R0 mapping 和 live render mapping 做 drift 校验。R0 snapshot 已包含 builtin `java` / `rust` expression styles，但当前 repository-source templates 只有 `c`、`c_poll`、`cpp`、`cpp_poll` 和 `python`；没有 `templates/java` / `templates/rust`。因此 PR-4 的 Java/Rust facts 是 native smoke facts，不是 template-generated facts。

Java/Rust case 仍使用 PR-6 shared join key：`case_id`、`operator`、`fcstm_expression`、`render_path`、`render_expression`。其中 `render_path` 使用 `native_java` 或 `native_rust`，并通过 `native_only=true` / `native_only_reason` 明确说明没有当前模板路径。后续若新增 Java/Rust built-in template，应新增 template render path，不应回写或伪造 PR-4 native-only facts。

官方资料摘要与 mapping 的关系也固定下来：Java case 的 source notes 引用 Java Language Specification（JLS）对 integer overflow、division / remainder、shift count masking 和 narrowing conversion 的规定，并引用 Java SE `Math.*Exact`（例如 `Math.addExact`、`Math.multiplyExact`）作为 checked arithmetic reference；Rust case 的 source notes 引用 Rust Reference 对 overflow、debug / release / `overflow-checks`、division / remainder、shift 和 cast 的规定，并引用 Rust standard library `wrapping_*`、`checked_*`、`overflowing_*`、`saturating_*` 作为显式语义族。
