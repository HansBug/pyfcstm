# Simulate semantic fixtures

This corpus turns existing simulator and built-in Python template alignment
semantics into data files. Each case lives in `cases/<id>.fcstm` plus
`cases/<id>.yaml` and is executed by helpers in
`test/testings/simulate_semantics.py`.

This corpus is a fixture/test-harness change only. It does not change production
runtime semantics and does not activate known simulator bug reproductions.

The shared corpus is intentionally narrow and public-API based. Every YAML case
defaults to the simulator plus generated Python alignment runners, and the only
runner-selection field is `exclude_runners` for explicit exceptions. Do not add
`runners`, top-level boundary markers, CLI command scenarios, model-construction
diagnostics, runtime options, log/warning assertions, stack snapshots, cycle
counters, history records, or any other private simulator surface to this
corpus.

## How to run

```bash
python -m pytest test/simulate/test_semantic_fixtures.py -v
python -m pytest test/template/python/test_semantic_fixture_alignment.py -v
python tools/inventory_simulate_semantics.py --check
SKIP_SLOW_TESTS=1 make unittest
```

## Adding a case

1. Add `cases/<id>.fcstm` with the DSL source.
2. Add `cases/<id>.yaml` using `schema_version: 1` and the schema in
   `schema.md`.
3. Keep `id` equal to the YAML/FCSTM basename.
4. Set `origin.files` to the exact original pytest function(s).
5. Omit `runners`; the loader applies all current shared runners by default.
6. Use `exclude_runners` only when a current shared runner cannot consume the
   case and the exclusion is intentional.
7. Keep only the public observation surface: `state`, `vars`, `vars_exact`,
   `vars_keys`, `vars_absent`, `ended`, constructor or hot-start outcomes,
   per-step cycle state and vars, and `handler_calls`.
8. Preserve every original behavior either through the shared public observation
   surface or through an ordinary pytest outside this corpus.
9. Run the fixture tests and the ordinary pytest coverage that owns any
   non-shared behavior.
10. Run `python tools/inventory_simulate_semantics.py --check` to keep the
    long-term Markdown and runner-selection contract clean.

## Maintenance inventory

`tools/inventory_simulate_semantics.py` prints a current corpus summary to
stdout. The repository does not keep generated inventory snapshots or a
generated README case table. Long-term documentation in this directory is
limited to this README and `schema.md`.

Use `python tools/inventory_simulate_semantics.py --check` when changing this
corpus. The check verifies YAML/FCSTM pairing, the top-level Markdown file
list, absence of include-style `runners`, and absence of known private
simulator surfaces in shared YAML.

## Public-observation checklist

Use this checklist before deleting or replacing any inline original test:

- `origin.files` points to the original class/function.
- The `.fcstm` file is semantically equivalent to the original DSL string;
  indentation cleanup is okay, DSL changes are not.
- The YAML cycle/event sequence matches the original call sequence exactly.
- Event input strings are not rewritten to a different path form.
- Every helper assertion and every bare assertion either has a public YAML
  equivalent or remains in ordinary pytest coverage.
- Runtime log assertions, Python warning assertions, stack snapshots, cycle
  counters, history records, cycle return metadata, and CLI output stay outside
  this shared corpus.
- `set(runtime.vars.keys())` and temporary-variable non-leakage use
  `vars_keys` and/or `vars_absent`.
- Exception tests keep class and message assertions under `raises` and keep
  rollback state/vars assertions when the original checked them.
- CLI tests stay as ordinary pytest coverage instead of shared fixture YAML.
- Abstract-handler callbacks use `handlers` plus `handler_calls`; shared cases
  keep only public hook-call records. Handler error metadata belongs in
  ordinary simulator pytest coverage.
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
