# c

`c` is the built-in C99 runtime template target.

This template emits a self-contained C runtime together with generated usage
documentation for the concrete state machine.

Template source contents:

- `machine.h.j2`: generated public runtime header
- `machine.c.j2`: generated runtime implementation
- `README.md.j2`: generated English usage guide in the output directory
- `README_zh.md.j2`: generated Chinese usage guide in the output directory
- `README.md` / `README_zh.md`: maintainer-facing template documentation

Current properties:

- targets C99 and only uses broadly available standard-library facilities
- generates `machine.h`, `machine.c`, `README.md`, and `README_zh.md`
- embeds state metadata, cycle logic, hot start handling, and abstract hook callback slots
- exposes hook registration in a form that is natural for C developers
- avoids generated handler-registration infrastructure

## Performance Roadmap

The C template should be treated as a generated black-box runtime. Human-facing
maintainability should be concentrated in the public header and generated usage
docs. The generated `machine.c` should prioritize runtime performance first, as
long as behavior remains correct and the public API contract stays stable.

Current progress:

- Phase 1 is implemented.
- Phase 2 is implemented.
- Phase 3 is implemented.
- The current C template regression suite passes with the id-only API and the
  hybrid event-set backend and the specialized state-dispatch hot path.

### Phase 1: Remove avoidable hot-path overhead

- [x] Remove string-based event submission from the generated public C API.
- [x] Generate transition-local `event_id` constants instead of storing
      `event_path` for runtime lookup.
- [x] Change `cycle()` to accept integer event ids directly.
- [x] Generate public event-id macros in `machine.h` so callers can submit
      events without string parsing.
- [x] Remove string state lookup from the hot-start API and switch hot start to
      state-id input.
- [x] Generate public state-id macros in `machine.h` for hot-start and other
      performance-sensitive control paths.
- [x] Inline or directly emit tiny helpers that are currently paid on every
      state advance.

### Phase 2: Introduce a hybrid event-set backend for id-based cycle input

- [x] Make the id-based `cycle()` API the only event-input path exposed by the
      generated header.
- [x] Replace the current linear event-set membership checks with a hybrid
      backend that does not impose a small fixed event-count limit.
- [x] Use a compact bitset fast path when the generated machine has a small or
      moderate total event count.
- [x] Fall back to a deduplicated integer-id array when the event space is too
      large for a compact bitset to be the best choice.
- [x] Prefer per-machine reusable scratch storage over per-cycle heap
      allocation.

Notes for Phase 2:

- A pure bitset is fast, but it ties cost directly to total event-space size.
- A pure array keeps memory small, but membership becomes linear in the number
  of submitted events.
- The preferred direction is a hybrid representation chosen from generated
  machine metadata:
  - small or dense event spaces: bitset
  - sparse event spaces with few submitted events per cycle: sorted or
    deduplicated integer array
  - larger sparse workloads: open-addressed hash set or similar constant-time
    membership structure
- This keeps the fast path for common small machines while avoiding a hard
  event-count ceiling.

### Phase 3: Replace table-driven execution with specialized generated code

- [x] Move transition selection away from `StateInfo` / `TransitionInfo` table
      scans in the cycle hot path.
- [x] Generate per-state transition dispatch functions instead of scanning
      transition-id arrays.
- [x] Generate per-state `enter`, `during`, `exit`, and init-dispatch helpers.
- [x] Expand concrete action sequences directly in generated code instead of
      routing through `ActionInfo`.
- [x] Keep abstract hooks as the only remaining indirect dispatch point, and
      only pay that cost when a hook is actually installed.
- [x] Keep the public `.h` stable while making the `.c` implementation more
      aggressively specialized.

### Phase 4: Specialize validation and rollback paths

- [ ] Keep rollback correctness first: failed cycles must still restore the
      previous committed machine state.
- [ ] Retain speculative validation semantics while reducing the amount of
      generic interpreter-style execution done during validation.
- [ ] Replace reusable generic DFS helpers with state-specialized validation
      logic where it materially reduces cost.
- [ ] Recheck stack-depth and DFS-step safety guarantees after specialization.
- [ ] Add focused regression tests for nested composites, sibling transitions,
      exit-to-parent transitions, and abstract-hook interactions.

### Acceptance Criteria

- [x] Generated `machine.h` stays small and user-oriented.
- [x] Generated `machine.c` is free to optimize for runtime speed over manual
      readability.
- [x] The generated public API uses integer ids directly for event submission.
- [x] `machine.h` exposes event-id and state-id macros so users do not need
      runtime string lookups.
- [x] Event handling has no artificial small fixed upper bound caused by using
      bit operations alone.
- [x] Existing runtime semantics, rollback behavior, and hook semantics remain
      correct.
