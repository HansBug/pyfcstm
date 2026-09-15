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
