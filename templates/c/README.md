# c template maintainer handbook

`c` is the built-in native C runtime template. It emits a self-contained C99
state-machine runtime with a public header designed for C users and C++98
integration paths.

This file is the maintainer-facing handbook for `templates/c/`. It is ignored
by the renderer and is not copied to generated output. Generated-output user
guides come from `README.md.j2` / `README_zh.md.j2`.

## Target and non-targets

Use this template when generated runtime performance, predictable C integration,
and a small public C API are the primary requirements.

The generated implementation should be treated as black-box runtime code. Users
who need different behavior should edit the FCSTM DSL and regenerate. Manual
long-term maintenance should concentrate on `machine.h`, generated README files,
and template source review, not on hand-editing generated `machine.c`.

This template is not a dependency bridge to `pyfcstm`. Generated C output must
run without the Python package or any third-party runtime library.

## Source layout and generated output

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | Public C integration surface template | `machine.h` |
| `machine.c.j2` | Generated high-performance runtime implementation template | `machine.c` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Renderer configuration, C statement rendering, helper names, and ignore rules | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

`config.yaml` ignores `README.md`, `README_zh.md`, and `template.json` for
rendered output. `make tpl` still packages the full template source directory,
so changes to this handbook must be validated with a refreshed local
`pyfcstm/template/c.zip`. The archive is ignored by git in normal checkouts;
setup and packaging commands recreate it from source.

## Compatibility and runtime dependency boundary

Generated C output should keep these defaults:

- C99 implementation path.
- C++98-compatible integration path for the generated public header and
  representative harnesses.
- Standard-library-only runtime dependencies; the generated runtime is standard-library-only by default.
- No dependency on `pyfcstm`, Python, generated-time helpers, or third-party C
  libraries.
- Broad compiler and platform compatibility, including older Windows-oriented
  C environments where practical.

Generated code may use long-lived C standard headers such as `<stddef.h>`,
`<math.h>`, `<stdarg.h>`, `<stdio.h>`, `<stdlib.h>`, and `<string.h>` when the
runtime requires them.

## Resource lifetime and leak policy

Generated C runtimes may be embedded in long-running control systems, so memory and resource ownership are runtime correctness concerns, not optional polish. The generated API should keep ownership simple: `..._create()` owns allocation, `..._destroy()` releases it, `..._init()` and `..._hot_start()` reset runtime state without leaking, and hook registration stores caller-owned pointers without taking ownership. Runtime changes must preserve this contract.

When `machine.c.j2` or allocation-related parts of `machine.h.j2` change, run at least one representative generated harness under AddressSanitizer / LeakSanitizer, valgrind, or an equivalent platform tool when available. The harness should cover create/destroy, cold start, hot start, normal cycles, eventful cycles, hook installation, and error/rollback paths that are relevant to the change. If a leak is discovered and clearly predates the current change, record the reproduction and scope it for a dedicated fix instead of hiding it.

## Public integration surface

`machine.h` is the public integration surface and should stay small, clear, and
stable. It owns:

- the generated machine struct type;
- persistent variable struct definitions;
- public state-id and event-id macros;
- integer event submission through `..._cycle(machine, event_ids, event_count)`;
- hot start through generated state ids and a complete variable snapshot;
- abstract hook callback signatures and hook table;
- current-state, variable, ended-state, last-error, and embedded-model accessors.

`machine.c` is the generated implementation. Downstream integrators should treat
its internal metadata, helper functions, stack frames, validation state, and
scratch storage as private implementation details.

## Performance and implementation strategy

Runtime performance and FCSTM semantic correctness are the first priorities for
`machine.c`. Human readability is secondary for generated implementation code.
Keep comments and structure sufficient for diagnostics and review, but do not
turn the generated implementation into a hand-maintained interpreter when a
specialized generated path is faster and semantically equivalent.

The current stable design includes:

- id-only public event input instead of runtime string event lookup;
- public event-id and state-id macros in `machine.h`;
- a hybrid event-set backend that keeps small and dense event spaces fast while
  avoiding a fixed small event-count ceiling;
- state-specialized dispatch for transition selection and lifecycle execution;
- direct expansion of concrete action blocks in generated code;
- abstract hooks as the remaining user-defined indirect extension points;
- speculative validation and rollback with reduced copying where possible;
- C/C++ keyword-safe generated identifiers;
- a public 64-bit integer alias strategy that avoids exposing raw `long long`
  as the only ABI spelling.

These are stable design facts, not a temporary development plan. Avoid
reintroducing temporary milestone lists or milestone headings as the main
README structure.

## Numeric metadata discipline

Generation-time enumerable runtime metadata should use collision-resistant
generated macros and numeric ids in the public hot-path ABI. This applies to
states, events, abstract actions, named `ref` actions, lifecycle stages,
current-state ids, active-leaf ids, and future finite metadata domains with the
same shape.

Do not keep `const char *` fields in `ExecutionContext`, event submission, or
other hot-path contracts merely for readability. Do not reintroduce `strcmp()`
into runtime selection or hook-context checks when the compared domain is known
while rendering the template. The readable integration surface is the generated
macro set in `machine.h`, for example `..._STATE_*`, `..._EVENT_*`,
`..._ACTION_*`, and `..._STAGE_*`.

Strings remain acceptable only for cold or diagnostic surfaces:

- `last_error` and other crash-loudly diagnostic messages;
- `..._dsl_source()` and generated comments / README text;
- optional diagnostic helpers such as `..._current_state_path()` and
  `..._current_state_name()`;
- Python test adapters that map generated ids back to shared fixture schema
  strings;
- genuinely non-enumerable output where no stable finite id domain exists at
  generation time.

When adding a new context field or public metadata value, first ask whether the
domain is completely known while rendering the template. If it is, generate a
macro-backed integer id and keep any string mapping outside the generated
runtime hot path.

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
path-boundary-safe macro.

## Performance evidence

A historical benchmark compared the current specialized C runtime design against
the older string-submission runtime on a moderately complex elevator-control
model with nested composites, initial transitions, sibling transitions,
exit-to-parent paths, and validation rollback.

The benchmark used `cc -O3 -DNDEBUG -std=c99` and measured two workloads:

| Workload | Cycles | Stable observation |
| --- | ---: | --- |
| `mixed` | 4,000,000 | Mean speedup was about `6.42x`; median speedup was about `7.25x`. |
| `validation_heavy` | 8,000,000 | Mean speedup was about `9.59x`; median speedup was about `9.75x`. |

The result supports the current design direction: id-only event input,
specialized state dispatch, and reduced-copy validation / rollback materially
improve the hot paths that dominate generated C runtime cost.

Benchmark records are evidence for maintenance decisions, not a substitute for
semantic regression tests. Do not loosen correctness, rollback, or hook behavior
in pursuit of microbenchmarks.

## Semantics and alignment expectations

The C template must preserve the FCSTM runtime contract for:

- cold start and hot start;
- composite initial transition ordering;
- lifecycle enter, during, exit, and aspect actions;
- event scoping, event identity, and transition priority;
- guard/effect evaluation and speculative rollback;
- abstract hook invocation timing and read-only execution context.

The C runtime tests and alignment tests are the behavioral authority. Template
README edits do not change these tests, but runtime template changes must keep
them passing.

## Maintenance workflow

Use the smallest verification set that matches the change:

1. For maintainer README-only edits, review English/Chinese section parity and
   confirm no generated user guide or source template changed.
2. Run `make rst_auto` before committing repository changes. This README should
   not normally produce generated RST changes.
3. Run `make tpl` after changing any file under `templates/c/`, including this
   README, because packaged built-in template archives include the template
   source directory.
4. Inspect packaged asset changes. README-only edits should refresh the local generated
   `pyfcstm/template/c.zip` archive; because zip archives are ignored by git in
   normal checkouts, the tracked `pyfcstm/template/index.json` should normally
   stay content-equivalent.
5. For runtime template changes, generate representative machines and run C99
   build checks, C++98 integration checks, formatter convergence checks,
   sanitizer or equivalent leak checks where available, and simulator-alignment
   tests.

Useful commands:

```bash
make rst_auto
make tpl
pytest test/template/c -v
SKIP_SLOW_TESTS=1 make unittest
```

For C runtime work, do not rely only on `SKIP_SLOW_TESTS=1`; the native C/C++
toolchain tests are part of the real completion gate.

## Language-specific verification

Representative generated C artifacts should satisfy:

```bash
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.h
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/machine.c
cmake -S path/to/harness -B path/to/build
cmake --build path/to/build
```

Formatter convergence is a pragmatic quality gate, not an absolute style
objective. It should catch obvious generated-code roughness and keep artifacts
professional enough for integration. Do not spend maintenance effort contorting
generated C for rare formatter-only edge cases when semantics, performance, or
compatibility would be harmed; document any known formatter-only exception
narrowly with the reason.

## Relationship to `c_poll`

`c` and `c_poll` share the C-family compatibility and self-contained runtime
policy, but their event input models are different:

- `c` accepts explicit generated event ids per cycle through the public cycle
  API.
- `c_poll` asks installed event-check callbacks whether each generated event is
  active during the current cycle.

Do not move essential `c` maintenance requirements into `c_poll` by link only.
Each template README must stay self-contained.

## Documentation layering

Keep documentation layers separate:

- this file explains how to maintain the `c` template;
- `README.md.j2` / `README_zh.md.j2` explain how to use one generated C output
  directory;
- root `templates/README.md` / `README_zh.md` explain repository-wide template
  system rules.

Generated READMEs should help a downstream user build and run the generated C
machine without understanding template packaging internals.
