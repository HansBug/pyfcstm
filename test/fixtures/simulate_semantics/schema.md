# Simulate semantic fixture schema v2

This directory stores the shared semantic fixture corpus for simulator and
built-in Python runtime alignment tests. A fixture is a pair of files under
`cases/`:

- `<id>.fcstm`: the FCSTM DSL source.
- `<id>.yaml`: metadata, construction inputs, cycle inputs, and expectations.

The loader derives the case id and paired FCSTM path from the YAML basename. The
schema is intentionally strict. Unknown top-level fields, unknown categories,
unknown expectation fields, and unknown nested fields inside construction input,
cycle input, exceptions, handlers, and handler-call records fail fast with a
diagnostic containing the case id and YAML path.

## Contract

Every fixture is a shared public-observation case by default. The loader applies
the current shared runner set automatically:

- `simulation`
- `generated_python_alignment`

The only runner-selection field is `exclude_runners`, and it is an exception
list. Do not add an include-style `runners` field. Future shared template
runners should join the default shared set, then opt out case-by-case only when a
concrete capability gap is documented.

The shared corpus may assert only public observations:

- `current_state_path`, represented in YAML as `state`
- `vars`, `vars_exact`, `vars_keys`, and `vars_absent`
- `is_ended`, represented in YAML as `ended`
- construction or hot-start outcome through `initial`
- cycle inputs and post-cycle state/vars through `steps`
- abstract hook call behavior through `handlers` plus `handler_calls`

Cycle return values and event accounting are simulator-only debug /
introspection metadata. They belong in ordinary `test/simulate/` pytest coverage
and must not appear in shared fixture YAML or generated-template alignment
expectations. Event accounting includes `CycleResult.input_events`,
`consumed_events`, `unconsumed_events`, or any similar event-ledger field.

These surfaces are not part of the shared fixture contract and must stay in
ordinary pytest coverage instead of shared YAML: CLI/REPL command transcripts,
model-construction diagnostics, simulator runtime options, stack snapshots,
cycle counters, history records, logs, warnings, abstract handler error lists,
error-state metadata, anonymous-warning dedupe metadata, cycle return metadata,
event accounting, and top-level expected-failure markers.

## Top-level fields

| Field | Required | Description |
|---|---:|---|
| `title` | yes | Human-readable title. |
| `origin.files` | yes | Original pytest functions or issue/PR links that supplied the behavior. |
| `origin.docs` | no | Optional design-document references. |
| `origin.notes` | no | Optional equivalence or provenance notes. |
| `categories` | yes | Non-empty list from the allowed category set. |
| `exclude_runners` | no | Non-empty list of current shared runners to exclude. Omit for all shared runners. |
| `initial` | no | Optional runtime construction state and variables. Omit for normal cold start. |
| `handlers` | no | Abstract-handler fixtures for public hook-call records. |
| `steps` | yes | Runtime checkpoints. Use `[]` only when `initial.expect.raises` asserts constructor failure. |

Rejected v1 or non-shared top-level fields include `schema_version`, `id`,
`source`, `runners`, `runtime_options`, `model_build`, `commands`, and
`expected_failure`.

Allowed categories:

- `runtime`
- `template_alignment`
- `design_example`
- `scenario_example`
- `hot_start`
- `event_paths`
- `temporary_vars`
- `if_blocks`
- `abstract`
- `pseudo_chain`
- `validation`
- `lifecycle`

## Construction

`initial` provides optional construction inputs:

```yaml
initial:
  state: Root.A
  vars:
    counter: 0
```

Allowed fields:

- `initial.state`: dot-separated state path string or `null`
- `initial.vars`: full variable snapshot mapping or `null`
- `initial.expect.raises`: constructor exception expectation

Omitting `initial` is the preferred cold-start spelling. `initial.state: null`
is also legal and means no hot-start target is provided. `cycle: null` is still
rejected; `null` is only meaningful for explicit state sentinels such as
`initial.state` and `expect.state`.

When `initial.expect` is present, `initial.state` and `initial.vars` keys must
both be explicit. Constructor-failure fixtures must use `steps: []`.

```yaml
initial:
  state: Root.A
  vars:
    counter: "0"
  expect:
    raises:
      type: ValueError
      match: "initial_vars['counter'] must be int or float"
      match_kind: substring
steps: []
```

## Handlers

Handlers install public abstract-hook observations:

```yaml
handlers:
  - action: Root.RootInit
    behavior: record_call
```

Allowed handler behavior:

- `record_call`: appends one public hook-call record.

`record_var_write_attempt`, `raise_error`, handler exception metadata, duplicate
registration behavior, override policy, warning/log/error metadata, and
thread-safety concerns are not shared fixture behavior. They belong in ordinary
simulator diagnostic tests.

## Steps and cycle input

Each step contains either `cycle`, `cycle_count`, or both, plus an `expect`
mapping. `cycle` input is passed to `runtime.cycle(...)` repeatedly according to
`cycle_count`.

```yaml
steps:
  - cycle_count: 0
    expect:
      state: Root.A
      vars:
        counter: 0
      ended: false

  - cycle: Root.A.Go
    expect:
      state: Root.B
      vars:
        counter: 10

  - cycle: [Root.B.Tick, Root.B.Flush]
    cycle_count: 2
    expect:
      state: Root.Done
```

Allowed cycle shapes:

| Shape | Python call | Meaning |
|---|---|---|
| `cycle: []` | `runtime.cycle([])` | One cycle with no input events. |
| `cycle: Root.A.Go` | `runtime.cycle("Root.A.Go")` | One cycle with one event path. |
| `cycle: [Root.A.Go, Root.B.Next]` | `runtime.cycle(["Root.A.Go", "Root.B.Next"])` | One cycle with multiple event paths. |
| `cycle_count: 3` | `runtime.cycle([])` three times | Repeat empty-event cycles. |
| `cycle: Root.A.Go` + `cycle_count: 3` | `runtime.cycle("Root.A.Go")` three times | Repeat the same event input. |
| `cycle_count: 0` | no cycle call | Checkpoint immediately after construction or previous step. |

`cycle_count` defaults to `1` when `cycle` is present. If `cycle_count` is
present and `cycle` is omitted, `cycle` defaults to `[]`. A step that omits both
`cycle` and `cycle_count` is invalid, because humans can easily misread a
missing cycle as “do nothing.” Use `cycle_count: 0` for a no-cycle checkpoint.

`cycle_count` must be a non-negative integer. Booleans, floats, strings, and
negative values are rejected. `cycle_count: 0` is legal only when `cycle` is
omitted or `cycle: []`; non-empty cycle input with `cycle_count: 0` is rejected.
`cycle: []` with `cycle_count: N` where `N > 0` is legal but usually less clear
than just writing `cycle_count: N`.

Rejected v1 cycle shapes include `cycle: {}`, `cycle: null`,
`cycle: {events: [...]}`, and event-object descriptors such as
`cycle: [{event: Root.A.Go}]`.

## Expectations

| Field | Meaning |
|---|---|
| `state` | Expected current state path as a dot-separated string, or `null` for ended runtime. |
| `vars` | Partial variable-value assertion. |
| `vars_exact` | Exact full `dict(runtime.vars)` assertion. |
| `vars_keys` | Exact variable key-set assertion. |
| `vars_absent` | Variables that must not be present. |
| `ended` | Expected `runtime.is_ended`. |
| `raises` | Expected exception class name and optional message/cause match. |
| `handler_calls` | Exact accumulated fixture-handler call records. |

Expectations are sparse. Missing fields mean “do not assert this observation,”
not a default value.

Rules:

- Every `expect` mapping must assert at least one public observation field.
- `vars` and `vars_exact` are mutually exclusive.
- `vars_exact` is mutually exclusive with `vars_keys` and `vars_absent`, because
  a full snapshot already fixes the variable key set.
- `vars_keys` and `vars_absent` must not overlap.
- `state: null` means the runtime is ended. `state: null` with `ended: false`,
  or non-null `state` with `ended: true`, is a schema error.
- `expect` must not contain `cycle_count`; repeat count is an input-side field,
  not a runtime observation.
- `return`, `cycle_result`, event accounting, stack, history, logs, warnings,
  error-state metadata, anonymous-warning counters, and generated-template
  private state IDs remain rejected.

## Exceptions

```yaml
expect:
  raises:
    type: SimulationRuntimeDfsError
    match: structural stack-depth safety limit
    match_kind: substring
  state: Root.A
  vars:
    counter: 1
  ended: false
```

Allowed exception type names:

- `ModelValidationError`
- `SimulationRuntimeDfsError`
- `SimulationRuntimeEventError`
- `SimulationRuntimeExpressionError`
- `ValueError`

`match_kind` and `cause_match_kind` may be `substring` or `regex`; default is
`substring`. `cause_match_kind` requires `cause_match`.

`expect.raises` is legal only when the effective step `cycle_count` is `1`.
Constructor failures must use `initial.expect.raises` with `steps: []`. Repeated
cycle failures must be split into multiple single-cycle steps so the failing
cycle is explicit.

Exception steps may still assert rollback state, variables, ended status, and
handler-call records through public fields.

## Handler calls

```yaml
expect:
  handler_calls:
    - action: Root.RootInit
      state: Root
      stage: enter
      vars:
        x: 0
      active_leaf: Root.A
      call_stage: enter
      abstract_target: Root.RootInit
      named_ref: null
```

`handler_calls` is the exact accumulated sequence from runtime construction,
handler installation, and all executed steps up to the current checkpoint. A
step with `handler_calls: []` asserts that no fixture handler has been called so
far. Omitting `handler_calls` means the fixture does not assert handler calls at
that checkpoint.

Required handler-call fields:

- `action`
- `state`
- `stage`
- `vars`

Optional handler-call fields:

- `active_leaf`
- `call_stage`
- `abstract_target`
- `named_ref`

Unknown handler-call fields, including `write_attempt`, are rejected.

For generated Python alignment cases, the helper installs the same fixture
handlers into both runtimes and asserts that their public call records match.

## Generated Python alignment runner

`generated_python_alignment` builds a `SimulationRuntime` and a generated Python
runtime from the same fixture DSL. The generated runtime is rendered from the
packaged built-in `python` template via `extract_template("python", ...)`. The
alignment runner checks construction outcomes and, after every step:

- `is_ended`
- variables
- current state path
- expected exception class names, messages, and causes
- public handler call records

It must not depend on private stack shape, cycle counters, history records,
cycle returns, event accounting, or other simulator internals.
