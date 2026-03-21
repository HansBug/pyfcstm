# c_poll

`c_poll` is the built-in C99 / C++98-compatible runtime template target that
uses hook-polled events instead of per-cycle external event-id submission.

Template source contents:

- `machine.h.j2`: generated public runtime header
- `machine.c.j2`: generated runtime implementation
- `README.md.j2`: generated English usage guide in the output directory
- `README_zh.md.j2`: generated Chinese usage guide in the output directory
- `README.md` / `README_zh.md`: maintainer-facing template documentation

Current design direction:

- keep `templates/c/` as the behavioral and structural baseline wherever the
  event-input model does not force divergence
- keep the generated runtime compatible with `C99` and `C++98`
- treat generated `machine.c` as a black-box high-performance runtime
- keep generated `machine.h` small, stable, and user-oriented
- require a complete generated event-check table before `cycle()` can run on
  machines that declare events
- define event checks as read-only probes where non-zero means "active this
  cycle" and `0` means "inactive this cycle"
- use lazy evaluation and per-cycle cache semantics for installed event checks

Phase status in this template directory:

- Phase 1: template skeleton established under `templates/c_poll/`
- Phase 2: public API switched to event-check mounting plus `cycle(machine)`
- Phase 3: internal event-check cache and dispatch-path migration completed
- Phase 4: runtime tests and alignment coverage completed

Implementation notes:

- `machine.c` does not need to optimize for human readability; it is generated
  black-box runtime code and should prioritize runtime performance once
  semantics are correct.
- `machine.h` should expose only the public operations and data structures that
  integrators actually need.
- Formatter convergence is part of completion. Generated C/C++ artifacts should
  stabilize under `clang-format` with the repository's template-development
  guidance.
