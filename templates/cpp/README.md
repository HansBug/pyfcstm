# cpp template maintainer guide

This guide is for changing the `cpp` template. Downstream integration belongs in `README.md.j2` / `README_zh.md.j2`; the root [template handbook](../README.md) owns renderer, metadata and packaging contracts. Read the source map, preserve the behavior below, then select the checks for your change.

## Source map and change ownership

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | File-level symlink to `../c/machine.h.j2` | `machine.h` |
| `machine.c.j2` | File-level symlink to `../c/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | C++ wrapper header | `machine.hpp` |
| `machine.cpp.j2` | C++ wrapper implementation | `machine.cpp` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Independent renderer config with explicit C-family helper imports | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

Generation-time helpers run inside pyfcstm; generated programs must remain self-contained. `config.yaml` excludes these maintainer guides and `template.json` from generated output. `make tpl` still includes them in the packaged source archive, so refresh packaging after any template edit.

| Change | Edit and synchronize |
| --- | --- |
| Generated guide | Both README Jinja files, rendered examples and executable documentation tests |
| Role API or lifecycle behavior | Runtime source, generated guide/API tables, role tests and semantic alignment |
| Expression/getter emission | `../../pyfcstm/render/c_runtime.py`, explicit imports in `config.yaml`, C and poll runtimes, both wrappers |
| Input/parameter identifiers | `readonly_value_identifier`; declarations, getters, providers, README examples and ABI tests |
| Shared C core | Edit `../c/machine.c.j2` / `machine.h.j2`; these files are symlinked here. Test both the core and wrapper suites |

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

`InputProvider` is copied, while its `user_data`, `Hooks` and its data are borrowed. `last_inputs` and `vars` expose instance storage; context pointers are callback-scoped. Cold initialization clears registrations; hot start preserves them. Keep C99, the signed 64-bit `Int` ABI, standard-library-only dependencies, caller-owned objects and `PYFCSTM_GENERATED_NO_HEAP` working. Guard floating-to-integer casts before conversion. Keep instances non-reentrant and resource ownership explicit.

The wrapper remains C++98-compatible, exception-free, RTTI-free and free of STL container requirements. It delegates to public C functions and never implements another execution engine or reads private machine fields. Semantic alignment must enter through `machine.hpp`, `Wrapper::` aliases and wrapper methods. Packaged archives must resolve C-core symlinks to ordinary files and work without the sibling template directory. `experimental: true` describes early first-class template status, not missing runtime functionality.

## Documentation maintenance

Maintain the user journey as a whole. There must be one complete Quick Start, followed by extensions of the same instance, recovery, API reference and advanced integration. A new API belongs in its existing tutorial section and reference table; replace obsolete examples and remove duplicate explanations in the same edit. Do not append a second quick start, final “complete example” or corrective note to compensate for a broken earlier section.

Every standalone example must include required input/action/event setup, initialization and error handling. Fragments must name their prerequisite example and insertion point and must not silently recreate the instance. C++ guides teach wrapper operations throughout; callback signatures may use documented C aliases. A successful executable exit alone is insufficient: assert sampling, action invocation and committed outputs.

Keep each prose paragraph on one physical line, in both source README files and rendered Markdown. Keep necessary line breaks in code, tables, lists and Jinja control structure. English and Chinese guides must have matching section order and equivalent code examples. Use natural Chinese for prose and preserve literal API names. Review the rendered output, not just the Jinja diff.

Generated guides contain integration instructions, not repository CI troubleshooting or packaging rules. Put shared mechanisms in the root handbook and concrete template decisions here. Preserve runtime limits and compatibility guidance; avoid repeating the same warning in multiple sections. Text/structure checks belong in maintenance tooling; runnable generated examples belong in pytest.

## Verification workflow

Native ownership, no-heap and toolchain evidence rules are maintained in the root [native template verification](../README.md#native-template-verification) section. Apply them with the template-specific checks below.

Run commands from the repository root. `make template_unittest` refreshes packaged templates and clears inherited slow-test skips for explicitly selected suites. Direct pytest requires a prior `make tpl`. Do not use the lightweight default suite as evidence for native template completion.

```bash
make tpl
PYFCSTM_TEMPLATE_SUITES=c,cpp make template_unittest
make test_boundary_check resource_ownership_check
make rst_auto
```

For guide-only changes, execute the generated examples and relevant formatter/build tests. For runtime changes, run the full selected suites and applicable shared fixtures; changes to shared C rendering require both C cores and both wrappers. For native numeric, ABI or ownership changes, run relevant native-toolchain/sanitizer profiles as well:

```bash
PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 PYFCSTM_TEMPLATE_SUITES=cpp make template_unittest TEMPLATE_UNITTEST_ARGS="--run-native-toolchain"
```

Use models with all four roles and actions/events together, input-free and parameter-free models, multiple inputs, unused inputs, scoped names and failure/retry paths. Confirm both language versions render, their anchors and code blocks remain valid, and examples work without editing generated machine files. Review package contents, public API differences and test results before publishing.
