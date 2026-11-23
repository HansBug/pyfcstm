# python template maintainer guide

This guide is for changing the `python` template. Downstream integration belongs in `README.md.j2` / `README_zh.md.j2`; the root [template handbook](../README.md) owns renderer, metadata and packaging contracts. Read the source map, preserve the behavior below, then select the checks for your change.

## Source map and change ownership

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.py.j2` | Runtime source template | `machine.py` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Renderer configuration, Python statement rendering, Jinja helpers, and ignore rules | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

Generation-time helpers run inside pyfcstm; generated programs must remain self-contained. `config.yaml` excludes these maintainer guides and `template.json` from generated output. `make tpl` still includes them in the packaged source archive, so refresh packaging after any template edit.

| Change | Edit and synchronize |
| --- | --- |
| Generated guide | Both README Jinja files, rendered examples and executable documentation tests |
| Role API or lifecycle behavior | Runtime source, generated guide/API tables, role tests and semantic alignment |
| Expression/getter emission | `config.yaml` role-aware expression/statement styles and `../../pyfcstm/render/render.py` context; generated action/guard tests |
| Region behavior | The region blocks of `machine.py.j2` (marked `{# region-kernel:NAME #}`), the region sections of both guides, `test/template/python/test_region_runtime.py` and the shared `regions` fixtures |

## Runtime contracts

The four variable roles are part of the runtime contract, including their observable lifetime and failure behavior:

| Role | Required behavior |
| --- | --- |
| `input` | Acquire every declared input once per active cycle, including unused inputs; freeze across validation/execution; no implicit hold; explicit snapshots bypass acquisition |
| `param` | Copy and validate at construction; omitted cold values use DSL defaults; complete same-checkpoint parameters required for hot start; no cycle override |
| `control` | Persistent writable model state; optional cold preset; complete hot snapshot; hold when unwritten |
| `output` | Same persistent commit/rollback behavior as control; application observes after success; no generated actuator setter |

Sampling or execution failure preserves committed variables and `last_inputs`. Successful Delta cycles hold persistent state but publish the new input snapshot. Construction and ended cycles do not acquire inputs. Action hooks run only during execution, observe read-only context and cannot mutate model state; external side effects cannot be rolled back.

Shared fixtures use top-level `parameters`, `initial.vars` / `initial.outputs`, per-step `inputs` and partial `expect.vars` / `expect.outputs`. Do not add parameter/input expectations or step-level parameter overrides. Tests must execute the generated runtime and compare values, lifecycle observations and failures with the simulator.

Keep generated code Python 3.7+ and standard-library-only. Preserve exact input/parameter suffixes, `read_*` overrides, keyword-only `parameters` / `inputs`, read-only parameter/input snapshots and complete constructor forwarding in documented subclasses. Representative artifacts must pass Ruff check and format with an explicit Python 3.7 target.

The `render_guard_lambda` macro lays every guard lambda out the way Ruff leaves it: a guard of up to 51 characters stays on the lambda line, one of up to 68 is wrapped once in parentheses, and a longer one is split in front of every `and` / `or` that is not inside brackets. Keep these widths in step with the indentation of the guard methods when that changes. Formatter-only rewrites that remain are non-blocking; the outputs are lint-clean and aligned with the simulator: a single operand that does not fit on a line (a parenthesised `||` chain of several terms in front of the give-way condition, for example), a long guard whose outermost operator is a conditional expression, which stays on the lambda line, the redundant outer parentheses that `=>`, `iff` and `xor` are rendered with, a float literal written with an exponent sign such as `1e+308`, an initializer of a variable with a very long hidden name, and long arithmetic in operation blocks and initializers, which is still emitted on one line.

### Regions and the kernel

Every model, with or without regions, is generated with the same kernel. It follows the region-aware part of `SimulationRuntime` (branch stacks, the chain of enclosing owners, group entry with rollback, owner continuation, the aspect ledger, the memoised stable-continuation search, hot start of a position tree, position-dependent event names), but it is written for the one model: states, regions and transitions are small integers, every state gets its own enter, during and transition-picking code with the actions, event checks and guards inline, and the tables that remain are indexed by those integers. Only the names a user passes in (hot-start text, event names) are looked up by string. The template declares `features: [region]` in `config.yaml`; remove that line and the renderer refuses models with regions again. Keep these invariants when changing it:

- Behavior is the contract, not the text of the generated files: every shared fixture, including every `regions` fixture, and every test of the generated runtime must keep passing, and the alignment runner compares the exception class and message text and the position text, so a message of the kernel is copied from the simulator, never reworded.
- A change to the simulator's region behavior is ported in the same change; do not let the two kernels drift. A behavior the fixtures do not pin down is checked with random models, with and without regions, against the simulator, including a hot start from the position of the oracle in the middle of a run.
- Work is skipped only when it is provably not needed for the model, and each skip is checked by that differential run: the loop check of an advance is skipped for a model without pseudo states. The speculative trial of a candidate is never skipped, because an abstract hook of a failed trial would otherwise be seen.
- State is read-only from outside: `vars` is a read-only view, the internal storage is underscore-private, and an interface that has no meaning for a model is not generated: a model with regions has no `current_state_path` or `current_state_name`.
- The generated module stays self-contained, standard-library-only and Python 3.7+. Generated outputs must pass `ruff check`; the formatter may rewrite a few long hidden-variable names, long guard lambdas and float literals that the expression renderer produces.

Verify with `pytest test/template/python` after `make tpl`, and with random models against the simulator for any change to the kernel.

## Documentation maintenance

Maintain the user journey as a whole. There must be one complete Quick Start, followed by extensions of the same instance, recovery, API reference and advanced integration. A new API belongs in its existing tutorial section and reference table; replace obsolete examples and remove duplicate explanations in the same edit. Do not append a second quick start, final “complete example” or corrective note to compensate for a broken earlier section.

Every standalone example must include required input/action/event setup, initialization and error handling. Fragments must name their prerequisite example and insertion point and must not silently recreate the instance. A successful executable exit alone is insufficient: assert sampling, action invocation and committed outputs.

Keep each prose paragraph on one physical line, in both source README files and rendered Markdown. Keep necessary line breaks in code, tables, lists and Jinja control structure. English and Chinese guides must have matching section order and equivalent code examples. Use natural Chinese for prose and preserve literal API names. Review the rendered output, not just the Jinja diff.

Generated guides contain integration instructions, not repository CI troubleshooting or packaging rules. Put shared mechanisms in the root handbook and concrete template decisions here. Preserve runtime limits and compatibility guidance; avoid repeating the same warning in multiple sections. Text/structure checks belong in maintenance tooling; runnable generated examples belong in pytest.

## Verification workflow

Run commands from the repository root. `make template_unittest` refreshes packaged templates and clears inherited slow-test skips for explicitly selected suites. Direct pytest requires a prior `make tpl`. Do not use the lightweight default suite as evidence for native template completion.

```bash
make tpl
PYFCSTM_TEMPLATE_SUITES=python make template_unittest
make test_boundary_check resource_ownership_check
make rst_auto
```

For guide-only changes, execute the generated examples and relevant formatter/build tests. For runtime changes, run the full selected suites and applicable shared fixtures.

Use models with all four roles and actions/events together, input-free and parameter-free models, multiple inputs, unused inputs, scoped names and failure/retry paths. Confirm both language versions render, their anchors and code blocks remain valid, and examples work without editing generated machine files. Review package contents, public API differences and test results before publishing.
