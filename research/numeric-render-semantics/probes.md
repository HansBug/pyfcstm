# Probe 设计说明

PR-1 提供 `tools/numeric_render_probe.py env`，用于输出本地 Python、平台和可用命令清单；PR-3 新增 `python-z3-baseline`，用于输出 Python render/runtime 小样例和 Z3 capability matrix。PR-1 的 R0 契约校验由 `tools/numeric_render_mapping.py --check` 承担；PR-3 的 baseline 契约校验由 `tools/numeric_render_probe.py python-z3-baseline --check` 承担。整个调研系列都不新增 `test/` 路径；任何会调用 native compiler、Node.js、Java、Rust、Go 或重型 Z3 求解的 probe 都应在后续子 PR 中继续落在 `tools/` / `research/` 与 gitignored `results/local/` 下。

## Python + Z3 baseline

`python-z3-baseline` 读取 R0 `render_mapping.json` 的 live mapping，生成 `results/snapshots/python_z3_baseline.json`。该 snapshot 固定以下边界：

- Python 是 P3 / 无限精度 / 仿真兼容基线，不是默认定长 profile。
- Python render path 同时记录 builtin Python style、`templates/python/config.yaml` 的 `python_expr` / `python_scope_expr` override，以及 statement runtime `_s(...)` override。
- `python_expr` / `python_scope_expr` / `python_runtime` 不只记录 raw override template，也记录 `sign(A)`、`round(A)`、`cbrt(A)`、`sqrt(A)` 等代表性表达式经真实 renderer 渲染后的成品，避免后续 PR 只读配置字符串而误判运行路径。
- `round`、`sign`、`cbrt`、常量、division/modulo、shift、bitwise 和 unary `~` 都有代表性样例或显式 parse-status 记录。
- Z3 额外记录轻量 construction sample：当前 z3py `Int` bitwise 构造为 `type_error`，`BitVec` bitwise 构造成功，用作后续 fixed-width profile 的边界证据。
- Z3 matrix 对每个 operator / UFunc 按 `Int`、`Real`、`BitVec`、`FP` 记录 `exact`、`approximate`、`uninterpreted` 或 `unsupported`；当前 solver 直接 `NotImplementedError` 拒绝的 `cbrt`、三角、双曲、指数和对数函数按当前事实标为 `unsupported`，未来如引入 uninterpreted / obligation 编码再单独更新。
- baseline 默认不保存依赖 solver model 选择的数值；若未来加入 model-valued 字段，必须记录 Z3 seed / relevant `set_param` 与 `z3-solver` 版本。
- `python-z3-baseline --check` 同时执行轻量 schema 形状校验、手写语义断言和 live-vs-snapshot 字节级稳定比较；schema 文件不是只作文档说明。

## 后续 runner 约束

- runner 必须读取 R0 `render_mapping.json`，不要手写与 renderer 脱节的表达式表。
- 编译失败、链接失败、运行时异常、sanitizer trap 都是结果，不得静默替换为“更合理”的 helper。
- 每次运行前探测 CPU、内存、磁盘、工具链版本和可承受并行度。
- Heavy 输出写入 `results/local/`，小型 summary / digest 才能提交。
- 8-bit exhaustive 可以作为调研阶段强验证；16-bit 必须支持 shard / resume / digest。
