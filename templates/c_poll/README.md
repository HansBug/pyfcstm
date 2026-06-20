# c_poll template maintainer handbook

`c_poll` is the built-in C-family runtime template whose event input model is
hook-polled. Instead of accepting external event-id arrays on each cycle, the
generated runtime calls installed event-check functions to decide whether each
DSL event is active in the current cycle.

This file is the maintainer-facing handbook for `templates/c_poll/`. It is
ignored by the renderer and is not copied to generated output. Generated-output
user guides come from `README.md.j2` / `README_zh.md.j2`.

## Target and non-targets

Use this template when the host environment already has event signals available
through callbacks, device reads, polling functions, or application state, and a
plain `cycle(machine)` API is a better integration shape than per-cycle event-id
submission.

`c_poll` should stay close to `templates/c/` where the event-input model does
not require divergence. It is not a separate semantic runtime: FCSTM state,
transition, lifecycle, validation, rollback, and hook behavior must remain
aligned with the simulator and the regular C template.

Generated output must not depend on `pyfcstm`, Python, or third-party runtime
libraries.

## Source layout and generated output

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | Public C integration surface template, including event-check types | `machine.h` |
| `machine.c.j2` | Generated high-performance hook-polled runtime implementation template | `machine.c` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Renderer configuration, C statement rendering, helper names, and ignore rules | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

`config.yaml` ignores `README.md`, `README_zh.md`, and `template.json` for
generated output. `make tpl` still packages the full template source directory,
so changes to this handbook must be validated with a refreshed local
`pyfcstm/template/c_poll.zip`. The archive is ignored by git in normal
checkouts; setup and packaging commands recreate it from source.

## Compatibility and runtime dependency boundary

Generated `c_poll` output should keep these defaults:

- C99 implementation path.
- C++98-compatible integration path for the generated public header and
  representative harnesses.
- Standard-library-only runtime dependencies; the generated runtime is standard-library-only by default.
- No dependency on `pyfcstm`, Python, generated-time helpers, or third-party C
  libraries.
- Broad compiler and platform compatibility, matching the C-family policy used
  by `templates/c/`.

`machine.h` is the public integration surface; `machine.c` is generated runtime
implementation optimized for semantics and performance.

## Resource lifetime and leak policy

Generated `c_poll` runtimes may run for long periods inside control applications. Resource ownership therefore has to be explicit and leak-free: `..._create()` owns allocation, `..._destroy()` releases it, `..._init()` / `..._hot_start()` reset state without leaking, `..._set_hooks()` and `..._set_event_checks()` store caller-owned tables and user-data pointers without taking ownership, and each `cycle()` must leave only the machine-owned persistent state behind.

When `machine.c.j2` or allocation-related public API changes, run at least one representative generated harness under AddressSanitizer / LeakSanitizer, valgrind, or an equivalent platform tool when available. The harness should cover event-check installation, repeated cycles, hot start, hook callbacks, and destroy paths. If an existing leak or ownership bug is found outside the current change scope, record a reproducible harness and split it into a dedicated fix.

## Deployment-profile maintenance discipline

The `c_poll` template shares the same C-family deployment profiles as
`templates/c/`, with the event-check table added to the public integration
surface:

| Profile | Public shape | Required checks |
| --- | --- | --- |
| Default hosted C99 | `..._create()`, `..._create_uninitialized()`, and `..._destroy()` are available. | Existing create/destroy, hot-start, hook, event-check, and shared semantic-alignment tests keep passing. |
| Caller-owned object | Callers allocate `Machine` storage and use `..._init(&machine)` / `..._hot_start(...)`, then install hooks and event checks as needed. | Native CMake harnesses cover stack storage, static storage, event-check installation, hook installation, hot start, and failure paths without heap helpers. |
| No-heap profile | `PYFCSTM_GENERATED_NO_HEAP` removes heap API declarations/definitions and the `<stdlib.h>` include that only served `calloc/free`; event-check APIs remain available. | Header preprocessing or generated-file checks prove heap API declarations disappear; link or symbol checks prove `calloc/free` are not referenced; event-check CMake harnesses still run. |

`PYFCSTM_GENERATED_NO_HEAP` is a symbol-presence contract. Template code should
use `#if defined(PYFCSTM_GENERATED_NO_HEAP)` or equivalent `#ifdef` checks, not
`#if PYFCSTM_GENERATED_NO_HEAP`. The documented consumer spelling is
`-DPYFCSTM_GENERATED_NO_HEAP`; if an external build spells it as
`-DPYFCSTM_GENERATED_NO_HEAP=1`, it must still select the same no-heap profile.

Keep the three sides of that contract synchronized:

- `machine.h.j2`: public heap declarations are removed in the no-heap profile,
  while hook and event-check declarations remain available;
- `machine.c.j2`: heap implementations and the `<stdlib.h>` include are removed
  in the no-heap profile;
- generated README examples: CMake consumers propagate the macro with
  `PUBLIC` / `INTERFACE`, or every final target that includes `machine.h` sees
  the same definition.

Native template tests must continue to use CMake as the build driver. User
README files may show gcc / clang style one-command examples, but pytest should
not grow a parallel handwritten host-compiler orchestration layer.

## Public integration surface

`machine.h` owns the stable integration contract:

- generated machine and persistent variable types;
- public state-id and event-id macros;
- abstract hook callback signatures and hook table;
- event-check callback signatures and a complete generated event-check table;
- `..._set_event_checks(machine, checks, user_data)` for mounting event input;
- `..._cycle(machine)` for executing one cycle through installed event checks;
- hot start, current-state, variable, ended-state, last-error, and
  embedded-model accessors.

`machine.c` owns the generated execution details, event-check cache, validation
state, rollback state, and dispatch helpers. Integrators should not edit or
reach into those internals.

## Event-check model

Each declared DSL event maps to one field in the generated `EventChecks` table.
For machines that declare events, callers must install a complete table before
`cycle()` can run.

An event-check callback is a read-only probe:

- non-zero return value means the event is active for the current cycle;
- `0` means the event is inactive for the current cycle;
- callbacks should not mutate machine persistent variables;
- the `EventContext` identifies the queried event, current leaf state, and
  variable snapshot.

The runtime uses lazy evaluation and a per-cycle cache. If several guards or
transitions ask about the same event within one cycle, the installed event-check
function should be called only as needed and the first observation should remain
stable for the rest of that cycle.

## Numeric metadata discipline

Generation-time enumerable runtime metadata should use collision-resistant
generated macros and numeric ids in the public hot-path ABI. This applies to
states, events, abstract actions, named `ref` actions, lifecycle stages,
event-check event ids, current-state ids, active-leaf ids, and future finite
metadata domains with the same shape.

Do not keep `const char *` fields in `ExecutionContext`, `EventContext`, or
other hot-path contracts merely for readability. Do not reintroduce `strcmp()`
into runtime selection, event-check logic, or hook-context checks when the
compared domain is known while rendering the template. The readable integration
surface is the generated macro set in `machine.h`, for example `..._STATE_*`,
`..._EVENT_*`, `..._ACTION_*`, and `..._STAGE_*`.

Strings remain acceptable only for cold or diagnostic surfaces:

- `last_error` and other crash-loudly diagnostic messages;
- `..._dsl_source()` and generated comments / README text;
- optional diagnostic helpers such as `..._current_state_path()` and
  `..._current_state_name()`;
- Python test adapters that map generated ids back to shared fixture schema
  strings;
- genuinely non-enumerable output where no stable finite id domain exists at
  generation time.

When adding a new event-check, hook-context, or public metadata value, first ask
whether the domain is completely known while rendering the template. If it is,
generate a macro-backed integer id and keep any string mapping outside the
generated runtime hot path.

Generated public identifiers for finite domains must preserve path boundaries
instead of flattening dotted paths with plain underscore joins. Legal DSL paths
such as `Root.A.B` and `Root.A_B` must never produce the same public state,
event, action, hook, or event-check identifier. Use the template's
collision-resistant path-identifier helpers for canonical public macros and
callback-table fields. Short aliases may exist only when the alias is provably
unique within that generated domain **and** does not collide with any reserved
public macro such as `..._STATE_COUNT`, `..._EVENT_COUNT`,
`..._ACTION_COUNT`, invalid-id sentinels, stage macros, or canonical ids from
that domain. When in doubt, omit the alias and keep only the canonical
path-boundary-safe macro. Canonical finite-domain public macros are deliberately
case-preserving and lossless for significant underscores. Do not uppercase,
lowercase, collapse repeated underscores, or strip trailing underscores from
canonical state/event/action/hook/event-check identifiers. Uppercase or flattened
compatibility aliases may be emitted only as optional conveniences after the full
generated domain proves that the alias is unique and does not collide with a
reserved or canonical public macro. Canonical public identifiers must also stay
outside C/C++ reserved identifier forms, including double underscores or names
that begin with an underscore followed by an uppercase letter.

The same reserved-shape rule applies to the root-machine ABI prefix, symbol
visibility macro prefix, hook/event-check initializer macros, and header guard.
Do not derive those public names by simply uppercasing or underscore-joining the
raw root state name. Use the public C identifier helpers so legal root names such
as `_Root`, `class`, and `A__B` cannot generate public macros, typedefs, function
prefixes, or include guards in C/C++ reserved namespaces.

When maintaining this contract, treat the following checks as part of normal
template review:

- Generate at least one model that combines nested states, events, abstract
  actions, named `ref` actions, lifecycle stages, event checks, and
  similar-looking paths such as `Root.A.B` / `Root.A_B` before changing public
  metadata or identifier helpers.
- Inspect the generated public ABI and hot path. Any generation-time enumerable
  value that appears as `const char *`, requires `strcmp()`, or needs per-cycle
  string allocation / formatting is a design regression unless it is explicitly
  confined to a cold diagnostic surface.
- Keep test adapters one-way: Python fixtures may map numeric ids back to schema
  strings for assertions, but that compatibility layer must not require the
  generated c_poll ABI to carry strings in hooks, event checks, or current-state
  checks.
- Keep event-check metadata numeric as well. The event-check callback should
  receive generated event and state ids, not event-path strings that integrators
  must compare at runtime.
- Update `c` and `c_poll` together for shared C-family metadata rules. A
  difference is acceptable only when it follows directly from the different
  event-input model and is documented in both template handbooks.
- Re-run representative native gates without relying on slow-test skipping
  before claiming metadata, identifier, hook-context, or event-check changes are
  complete.

## Relationship to `c`

`c_poll` and `c` share the same C-family maintenance constraints:

- C99 / C++98 compatibility expectations;
- standard-library-only and strictly self-contained generated runtime;
- `machine.h` as the stable public integration surface;
- `machine.c` as high-performance generated implementation;
- no `pyfcstm` runtime dependency and no third-party runtime dependency;
- semantic alignment with simulator behavior.

The main difference is event input:

- `c` accepts explicit generated event ids per cycle.
- `c_poll` polls mounted event-check callbacks during `cycle(machine)`.

This README must remain self-contained. Links to `templates/c/` can be useful
for comparison, but they must not carry essential `c_poll` maintenance rules by
themselves.

## Performance and implementation strategy

Generated `machine.c` should prioritize FCSTM semantics and runtime performance.
Human readability is secondary for implementation code. Keep the public header
clear and stable; let the generated implementation use specialized dispatch,
per-cycle event cache storage, and direct action expansion when those choices
improve performance without changing visible behavior.

Formatter convergence is a pragmatic quality gate, not an absolute style
objective. It should catch obvious generated-code roughness and keep artifacts
professional enough for integration. Do not spend maintenance effort contorting
generated C for rare formatter-only edge cases when semantics, performance, or
compatibility would be harmed; document any known formatter-only exception
narrowly with the reason.

## Semantics and alignment expectations

The hook-polled event model must preserve FCSTM behavior for:

- cold start and hot start;
- composite initial transition ordering;
- lifecycle enter, during, exit, and aspect actions;
- event scoping, event identity, and transition priority;
- guard/effect evaluation and speculative rollback;
- abstract hook invocation timing and context values;
- event-check invocation timing, context values, lazy evaluation, and per-cycle
  cache stability.

Runtime tests and alignment tests are the behavioral authority. README-only
changes should not modify those tests, but runtime template changes must keep
them passing.

## Maintenance workflow

Use the smallest verification set that matches the change:

1. For maintainer README-only edits, review English/Chinese section parity and
   confirm no generated user guide or source template changed.
2. Run `make rst_auto` before committing repository changes. This README should
   not normally produce generated RST changes.
3. Run `make tpl` after changing any file under `templates/c_poll/`, including
   this README, because packaged built-in template archives include the template
   source directory.
4. Inspect packaged asset changes. README-only edits should refresh the local generated
   `pyfcstm/template/c_poll.zip` archive; because zip archives are ignored by
   git in normal checkouts, the tracked `pyfcstm/template/index.json` should
   normally stay content-equivalent.
5. For runtime template changes, generate representative machines and run C99
   build checks, C++98 integration checks, formatter convergence checks,
   sanitizer or equivalent leak checks where available, c_poll-specific
   event-check tests, and simulator-alignment tests.

Useful commands:

```bash
make rst_auto
make tpl
pytest test/template/c_poll -v
SKIP_SLOW_TESTS=1 make unittest
```

For c_poll runtime work, do not rely only on `SKIP_SLOW_TESTS=1`; the native
C/C++ toolchain tests are part of the real completion gate.

## Language-specific verification

Representative generated C artifacts should satisfy:

```bash
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.h
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.c
cmake -S path/to/harness -B path/to/build
cmake --build path/to/build
```

Event-check tests should include machines with no declared events, machines with
one event, and machines with multiple scoped events so the complete-table rule
and cache behavior remain covered.

## Documentation layering

Keep documentation layers separate:

- this file explains how to maintain the `c_poll` template;
- `README.md.j2` / `README_zh.md.j2` explain how to use one generated c_poll
  output directory;
- root `templates/README.md` / `README_zh.md` explain repository-wide template
  system rules.

Generated READMEs should teach users how to register event checks, run cycles,
inspect state, and diagnose errors without needing to understand repository
packaging internals.
