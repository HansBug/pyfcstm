# c_poll template maintainer guide

This guide is for changing the `c_poll` template. Downstream integration belongs in `README.md.j2` / `README_zh.md.j2`; the root [template handbook](../README.md) owns renderer, metadata and packaging contracts. Read the source map, preserve the behavior below, then select the checks for your change.

## Source map and change ownership

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | Public C integration surface template, including event-check types | `machine.h` |
| `machine.c.j2` | Generated high-performance hook-polled runtime implementation template | `machine.c` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Renderer configuration, C statement rendering, helper names, and ignore rules | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

Generation-time helpers run inside pyfcstm; generated programs must remain self-contained. `config.yaml` excludes these maintainer guides and `template.json` from generated output. `make tpl` still includes them in the packaged source archive, so refresh packaging after any template edit.

| Change | Edit and synchronize |
| --- | --- |
| Generated guide | Both README Jinja files, rendered examples and executable documentation tests |
| Role API or lifecycle behavior | Runtime source, generated guide/API tables, role tests and semantic alignment |
| Expression/getter emission | `../../pyfcstm/render/c_runtime.py`, explicit imports in `config.yaml`, C and poll runtimes, both wrappers |
| Input/parameter identifiers | `readonly_value_identifier`; declarations, getters, providers, README examples and ABI tests |
| Shared native behavior | Update `c` and `c_poll` consistently; changes also affect the `cpp` and `cpp_poll` wrappers |

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

`InputProvider` is copied, while its `user_data`, `Hooks`, event tables and their data are borrowed. `last_inputs` and `vars` expose instance storage; context pointers are callback-scoped. Cold initialization clears registrations; hot start preserves them. Keep C99, the signed 64-bit `Int` ABI, standard-library-only dependencies, caller-owned objects and `PYFCSTM_GENERATED_NO_HEAP` working. Guard floating-to-integer casts before conversion. Keep instances non-reentrant and resource ownership explicit.

Event checks differ from numeric input readers: they are lazy, their first result is cached per cycle, and nonzero means active rather than successful sampling. Eventful models require a complete event table even with explicit input snapshots. Cover no-event, single-event and scoped multi-event models.

## Documentation maintenance

Maintain the user journey as a whole. There must be one complete Quick Start, followed by extensions of the same instance, recovery, API reference and advanced integration. A new API belongs in its existing tutorial section and reference table; replace obsolete examples and remove duplicate explanations in the same edit. Do not append a second quick start, final “complete example” or corrective note to compensate for a broken earlier section.

Every standalone example must include required input/action/event setup, initialization and error handling. Fragments must name their prerequisite example and insertion point and must not silently recreate the instance. A successful executable exit alone is insufficient: assert sampling, action invocation and committed outputs.

Keep each prose paragraph on one physical line, in both source README files and rendered Markdown. Keep necessary line breaks in code, tables, lists and Jinja control structure. English and Chinese guides must have matching section order and equivalent code examples. Use natural Chinese for prose and preserve literal API names. Review the rendered output, not just the Jinja diff.

Generated guides contain integration instructions, not repository CI troubleshooting or packaging rules. Put shared mechanisms in the root handbook and concrete template decisions here. Preserve runtime limits and compatibility guidance; avoid repeating the same warning in multiple sections. Text/structure checks belong in maintenance tooling; runnable generated examples belong in pytest.

## Verification workflow

Native ownership, no-heap and toolchain evidence rules are maintained in the root [native template verification](../README.md#native-template-verification) section. Apply them with the template-specific checks below.

Run commands from the repository root. `make template_unittest` refreshes packaged templates and clears inherited slow-test skips for explicitly selected suites. Direct pytest requires a prior `make tpl`. Do not use the lightweight default suite as evidence for native template completion.

```bash
make tpl
PYFCSTM_TEMPLATE_SUITES=c_poll,cpp_poll make template_unittest
make test_boundary_check resource_ownership_check
make rst_auto
```

For guide-only changes, execute the generated examples and relevant formatter/build tests. For runtime changes, run the full selected suites and applicable shared fixtures; changes to shared C rendering require both C cores and both wrappers. For native numeric, ABI or ownership changes, run relevant native-toolchain/sanitizer profiles as well:

```bash
PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 PYFCSTM_TEMPLATE_SUITES=c_poll make template_unittest TEMPLATE_UNITTEST_ARGS="--run-native-toolchain"
```

Use models with all four roles and actions/events together, input-free and parameter-free models, multiple inputs, unused inputs, scoped names and failure/retry paths. Confirm both language versions render, their anchors and code blocks remain valid, and examples work without editing generated machine files. Review package contents, public API differences and test results before publishing.

## Implementation references

### Numeric metadata discipline

Generation-time enumerable runtime metadata should use collision-resistant generated macros and numeric ids in the public hot-path ABI. This applies to states, events, abstract actions, named `ref` actions, lifecycle stages, event-check event ids, current-state ids, active-leaf ids, and future finite metadata domains with the same shape.

Do not keep `const char *` fields in `ExecutionContext`, `EventContext`, or other hot-path contracts merely for readability. Do not reintroduce `strcmp()` into runtime selection, event-check logic, or hook-context checks when the compared domain is known while rendering the template. The readable integration surface is the generated macro set in `machine.h`, for example `..._STATE_*`, `..._EVENT_*`, `..._ACTION_*`, and `..._STAGE_*`.

Strings remain acceptable only for cold or diagnostic surfaces:

- `last_error` and other crash-loudly diagnostic messages;
- `..._dsl_source()` and generated comments / README text;
- optional diagnostic helpers such as `..._current_state_path()` and `..._current_state_name()`;
- Python test adapters that map generated ids back to shared fixture schema strings;
- genuinely non-enumerable output where no stable finite id domain exists at generation time.

When adding a new event-check, hook-context, or public metadata value, first ask whether the domain is completely known while rendering the template. If it is, generate a macro-backed integer id and keep any string mapping outside the generated runtime hot path.

Generated public identifiers for finite domains must preserve path boundaries instead of flattening dotted paths with plain underscore joins. Legal DSL paths such as `Root.A.B` and `Root.A_B` must never produce the same public state, event, action, hook, or event-check identifier. Use the template's collision-resistant path-identifier helpers for canonical public macros and callback-table fields. Short aliases may exist only when the alias is provably unique within that generated domain **and** does not collide with any reserved public macro such as `..._STATE_COUNT`, `..._EVENT_COUNT`, `..._ACTION_COUNT`, invalid-id sentinels, stage macros, or canonical ids from that domain. When in doubt, omit the alias and keep only the canonical path-boundary-safe macro. Canonical finite-domain public macros are deliberately case-preserving and lossless for significant underscores. Do not uppercase, lowercase, collapse repeated underscores, or strip trailing underscores from canonical state/event/action/hook/event-check identifiers. Uppercase or flattened compatibility aliases may be emitted only as optional conveniences after the full generated domain proves that the alias is unique and does not collide with a reserved or canonical public macro. Canonical public identifiers must also stay outside C/C++ reserved identifier forms, including double underscores or names that begin with an underscore followed by an uppercase letter.

The same reserved-shape rule applies to the root-machine ABI prefix, symbol visibility macro prefix, hook/event-check initializer macros, and header guard. Do not derive those public names by simply uppercasing or underscore-joining the raw root state name. Use the public C identifier helpers so legal root names such as `_Root`, `class`, and `A__B` cannot generate public macros, typedefs, function prefixes, or include guards in C/C++ reserved namespaces.

When maintaining this contract, treat the following checks as part of normal template review:

- Generate at least one model that combines nested states, events, abstract actions, named `ref` actions, lifecycle stages, event checks, and similar-looking paths such as `Root.A.B` / `Root.A_B` before changing public metadata or identifier helpers.
- Inspect the generated public ABI and hot path. Any generation-time enumerable value that appears as `const char *`, requires `strcmp()`, or needs per-cycle string allocation / formatting is a design regression unless it is explicitly confined to a cold diagnostic surface.
- Keep test adapters one-way: Python fixtures may map numeric ids back to schema strings for assertions, but that compatibility layer must not require the generated c_poll ABI to carry strings in hooks, event checks, or current-state checks.
- Keep event-check metadata numeric as well. The event-check callback should receive generated event and state ids, not event-path strings that integrators must compare at runtime.
- Update `c` and `c_poll` together for shared C-family metadata rules. A difference is acceptable only when it follows directly from the different event-input model and is documented in both template handbooks.
- Re-run representative native gates without relying on slow-test skipping before claiming metadata, identifier, hook-context, or event-check changes are complete.
