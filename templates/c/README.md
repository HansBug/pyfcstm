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
