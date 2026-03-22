# python

`python` is the built-in native Python template target.

This template emits a self-contained Python runtime together with generated
usage documentation for the concrete state machine.

Template source contents:

- `machine.py.j2`: generated runtime module
- `README.md.j2`: generated English usage guide in the output directory
- `README_zh.md.j2`: generated Chinese usage guide in the output directory
- `README.md` / `README_zh.md`: maintainer-facing template documentation

Current properties:

- Phase 3 runtime template implemented
- generates a single importable Python runtime module
- emits `machine.py`, `README.md`, and `README_zh.md`
- embeds state metadata, cycle logic, hot start handling, and subclass hook points for abstract actions
- depends only on the Python standard library
- keeps generated output close to `ruff format` defaults
- exposes abstract hook names that are easy to discover through IDE completion
