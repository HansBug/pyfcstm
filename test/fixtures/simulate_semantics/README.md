# Simulate semantic fixtures

This corpus turns simulator and built-in Python template alignment semantics into
shared data files. Each case lives in `cases/<id>.fcstm` plus
`cases/<id>.yaml` and is executed by helpers in
`test/testings/simulate_semantics.py`.

The shared corpus is a fixture/test-harness contract. It does not change
production runtime semantics, and it must not activate known simulator bug
reproductions as expected failures.

## Scope

The shared corpus is intentionally narrow and public-API based. Every YAML case
uses the current shared runner set by default:

- `simulation`
- `generated_python_alignment`

The only runner-selection field is `exclude_runners` for explicit exceptions.
Do not add include-style `runners`, top-level boundary markers, CLI command
scenarios, model-construction diagnostics, runtime options, log/warning
assertions, stack snapshots, cycle counters, history records, cycle return
metadata other than the public `delta` bit, event accounting, or any other
private simulator surface to this corpus.

Shared fixtures cover only legal DSL models and legal runtime use: optional legal
hot-start construction, optional legal abstract-handler registration, and a
sequence of legal `cycle` calls. Handler fixtures only check whether hooks were
called, in what order, and with what public context snapshot. Handler
registration policy, duplicate registration behavior, warning/log/error
metadata, handler exceptions, and read-only write-attempt diagnostics belong in
ordinary simulator pytest files.

## How to run

```bash
python -m pytest test/simulate/test_semantic_fixtures.py -v
python -m pytest test/template/python/test_semantic_fixture_alignment.py -v
python tools/inventory_simulate_semantics.py --check
SKIP_SLOW_TESTS=1 make unittest
```

## Adding a case

1. Add `cases/<id>.fcstm` with the DSL source.
2. Add `cases/<id>.yaml` using the shared fixture contract in `schema.md`.
3. Do not write `id` or `source`; the loader derives the case id and paired
   FCSTM file from the YAML basename.
4. Set `origin.files` to the exact original pytest function(s), issue links, or
   PR links that supplied the behavior.
5. Omit `exclude_runners` unless a current shared runner has a documented
   capability gap for this otherwise shared behavior.
6. Use only the public observation surface: `state`, `vars`, `vars_exact`,
   `vars_keys`, `vars_absent`, `ended`, `delta`, `raises`, and `handler_calls`.
   `delta` must be a boolean on a successful cycle step; it is rejected on
   `cycle_count: 0` checkpoints and exception steps.
7. Keep `expect` sparse: omitted fields mean “do not assert this observation,”
   not a default expected value.
   With `cycle_count > 1`, `expect.delta` is checked after every call; use
   separate steps for mixed ordinary/Delta sequences.
8. Preserve every original behavior either through the shared public observation
   surface or through ordinary pytest outside this corpus.
9. Run the fixture tests and the ordinary pytest coverage that owns any
   non-shared behavior.
10. Run `python tools/inventory_simulate_semantics.py --check` to keep the
    long-term Markdown, pairing, and public-observation contract clean.

Minimal shared-contract shape:

```yaml
title: Event sequence reaches active state
origin:
  files:
    - test/simulate/test_runtime.py::test_event_sequence
categories: [runtime, template_alignment]

initial:
  state: Root.Gate
  vars: {counter: 0}

handlers:
  - action: Root.Gate.Observe
    behavior: record_call

steps:
  - cycle_count: 0
    expect:
      state: Root.Gate
      vars: {counter: 0}
      ended: false
      handler_calls: []

  - cycle: Root.Gate.Unlock
    expect:
      state: Root.Active
      vars: {counter: 1}
      delta: false

  - cycle_count: 4
    expect:
      vars: {counter: 5}

  - cycle: [Root.Active.Tick, Root.Active.Flush]
    cycle_count: 2
    expect:
      state: Root.Done
      ended: false
      delta: false
```

## Maintenance inventory

`tools/inventory_simulate_semantics.py` prints a current corpus summary to
stdout. The repository does not keep generated inventory snapshots or a
generated README case table. Long-term documentation in this directory is
limited to this README and `schema.md`.

Use `python tools/inventory_simulate_semantics.py --check` when changing this
corpus. The check verifies YAML/FCSTM pairing, the top-level Markdown file list,
absence of retired fields and include-style runner selection, absence of legacy cycle
and path shapes, and absence of known private simulator surfaces in shared YAML.

## Public-observation checklist

Use this checklist before deleting or replacing any inline original test:

- `origin.files` points to the original class/function, issue, or PR.
- The `.fcstm` file is semantically equivalent to the original DSL string;
  indentation cleanup is okay, DSL changes are not.
- The YAML cycle/event sequence matches the original call sequence exactly.
- Event input strings are not rewritten to a different path form unless the test
  explicitly covers equivalent path spelling.
- Every helper assertion and every bare assertion either has a public YAML
  equivalent or remains in ordinary pytest coverage.
- Runtime log assertions, Python warning assertions, stack snapshots, cycle
  counters, history records, cycle return metadata other than `delta`, event
  accounting, and CLI output stay outside this shared corpus.
- `set(runtime.vars.keys())` and temporary-variable non-leakage use `vars_keys`
  and/or `vars_absent`.
- Exception tests keep class and message assertions under `raises` and keep
  rollback state/vars assertions when the original checked them.
- CLI tests stay as ordinary pytest coverage instead of shared fixture YAML.
- Abstract-handler callbacks use `handlers` plus `handler_calls`; shared cases
  keep only public hook-call records. Handler error metadata belongs in ordinary
  simulator pytest coverage.
- Anonymous abstract warning dedupe metadata is a simulator-internal diagnostic
  and belongs in dedicated `test/simulate/` pytest coverage, not shared fixture
  YAML.
- Python API shape tests that YAML cannot represent, such as tuple or State
  object hot-start inputs, stay as dedicated Python tests.

## Migration-equivalence review table template

Reviewers can use this fixed template when checking a migrated case:

| Original test | Fixture id | DSL equivalent? | Cycle/events equivalent? | Assertions preserved? | Notes |
|---|---|---|---|---|---|
| `path::Class::test_name` | `case_id` | yes/no | yes/no | yes/no | Missing or changed assertions. |
