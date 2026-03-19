# python_native

`python_native` is the built-in native Python template target.

Current status:

- Phase 3 runtime template implemented
- generates a single importable Python runtime module
- emits only `machine.py` and does not require a generated package wrapper
- embeds state metadata, cycle logic, hot start handling, subclass hook points for abstract actions, and abstract handler registration
- depends only on the Python standard library

Expected later work:

- closer semantic alignment with `SimulationRuntime`
- broader acceptance coverage for composite exit and validation edge cases
