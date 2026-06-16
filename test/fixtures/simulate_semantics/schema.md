# Simulate semantic fixture schema

This directory stores the shared semantic fixture corpus for simulator and
built-in Python runtime alignment tests. A fixture is a pair of files under
`cases/`:

- `<id>.fcstm`: the FCSTM DSL source.
- `<id>.yaml`: metadata, construction inputs, cycle inputs, and expectations.

The schema is intentionally strict. Unknown top-level fields, unknown
categories, unknown expectation fields, and unknown nested fields inside
`cycle`, `raises`, handlers, and handler calls fail fast with a diagnostic
containing the case id and YAML path.

## Contract

Every fixture is a shared public-observation case by default. The loader applies
the current shared runner set automatically:

- `simulation`
- `generated_python_alignment`

The only runner-selection field is `exclude_runners`, and it is an exception
list. Do not add an include-style `runners` field. Future template runners
should join the default shared set, then opt out case-by-case only when a
concrete capability gap is documented.

The shared corpus may assert only public observations:

- `current_state_path`, represented in YAML as `state`
- `vars`, `vars_exact`, `vars_keys`, and `vars_absent`
- `is_ended`, represented in YAML as `ended`
- construction or hot-start outcome through `initial`
- cycle inputs and post-cycle state/vars through `steps`
- abstract hook call behavior through `handlers` plus `handler_calls`

Cycle return values and event accounting are simulator-only debug / introspection
metadata. They belong in ordinary `test/simulate/` pytest coverage and must not
appear in shared fixture YAML or generated-template alignment expectations.

These surfaces are not part of the shared fixture contract and must stay in
ordinary pytest coverage instead of shared YAML: CLI/REPL command transcripts,
model-construction diagnostics, simulator runtime options, stack snapshots,
cycle counters, history records, logs, warnings, abstract handler error lists,
error-state metadata, anonymous-warning dedupe metadata, cycle return metadata,
and top-level expected-failure markers.

## Top-Level Fields

| Field | Required | Description |
|---|---:|---|
| `schema_version` | yes | Fixed integer value `1`. |
| `id` | yes | Stable snake-case id. Must match the YAML basename. |
| `title` | yes | Human-readable title. |
| `source.fcstm` | yes | FCSTM file name in the same directory. |
| `origin.files` | yes | Original pytest functions or issue/PR links that supplied the behavior. |
| `origin.docs` | no | Optional design-document references. |
| `origin.assertion_types` | no | Review hint: assertion families carried by the fixture. |
| `origin.notes` | no | Optional equivalence or provenance notes. |
| `categories` | yes | Non-empty list from the allowed category set. |
| `exclude_runners` | no | Non-empty list of current shared runners to exclude. Omit for all shared runners. |
| `initial` | no | Runtime construction state and variables. |
| `steps` | yes | Runtime observations. Use `[]` only when `initial.expect.raises` asserts constructor failure. |
| `handlers` | no | Abstract-handler fixtures for public hook-call records. |

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

- `initial.state`: state path string or `null`
- `initial.vars`: full variable snapshot mapping or `null`
- `initial.expect.raises`: constructor exception expectation

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
  - action: Root.A.Touch
    behavior: record_var_write_attempt
    write:
      name: x
      value: 999
```

Allowed handler behaviors:

- `record_call`: appends one hook call record.
- `record_var_write_attempt`: attempts `ctx.vars[name] = value` and records the
  public read-only context result.

`raise_error` and handler exception metadata are not shared fixture behavior.
They belong in ordinary simulator diagnostic tests.

## Steps

A runtime step is either an initial assertion or a cycle call:

```yaml
steps:
  - expect_initial:
      state: [Root, A]
      vars:
        counter: 0
      ended: false
  - cycle:
      events: [Root.A.Go]
    expect:
      state: [Root, B]
      vars:
        counter: 10
      ended: false
```

`cycle` may be `{}`, `null`, a bare event-path string, or a mapping with only
the `events` field. `events` may be `null` or a list. Each list item may be an
event-path string or an event-object descriptor with exactly one `event` key:

```yaml
cycle:
  events:
    - Root.A.Go
    - {event: Root.A.Other}
```

## Expectations

| Field | Meaning |
|---|---|
| `state` | Expected current state path as a list of segments, or `null` for ended runtime. |
| `vars` | Partial variable-value assertion. |
| `vars_exact` | Exact full `dict(runtime.vars)` assertion. |
| `vars_keys` | Exact variable key-set assertion. |
| `vars_absent` | Variables that must not be present. |
| `ended` | Expected `runtime.is_ended`. |
| `raises` | Expected exception class name and optional message/cause match. |
| `handler_calls` | Exact accumulated fixture-handler call records. |

`vars` and `vars_exact` may both be present only when the partial `vars` mapping
is consistent with `vars_exact`. `vars_keys` and `vars_absent` must not overlap.

Every `expect` or `expect_initial` mapping must assert at least one public
observation field.

## Simulator-only cycle return metadata

`cycle_result` is intentionally not a shared fixture field.
`pyfcstm.simulate.SimulationRuntime.cycle()` may return simulator debug metadata,
including event-accounting details, but generated runtimes are not required to
mirror that return object. Keep those assertions in ordinary simulator pytest
files such as `test/simulate/test_event_inputs.py` and
`test/simulate/test_runtime_contract_integration.py`.

## Exceptions

```yaml
expect:
  raises:
    type: SimulationRuntimeDfsError
    match: structural stack-depth safety limit
    match_kind: substring
  state: [Root, A]
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
`substring`. Exception steps may still assert rollback state, vars, and ended
status through public fields.

## Handler Calls

```yaml
expect:
  handler_calls:
    - action: Root.RootInit
      state: Root
      stage: enter
      vars:
        x: 0
```

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
- `write_attempt`

When a handler call includes `write_attempt`, the record asserts the attempted
variable name, attempted value, success flag, optional exception type, and the
handler-visible variable snapshot after the attempt.

For generated Python alignment cases, the helper installs the same fixture
handlers into both runtimes and asserts that their public call records match.

## Generated Python Alignment Runner

`generated_python_alignment` builds a `SimulationRuntime` and a generated Python
runtime from the same fixture DSL. The generated runtime is rendered from the
packaged built-in `python` template via `extract_template("python", ...)`. The
alignment runner checks construction outcomes and, after every step:

- `is_ended`
- variables
- current state path
- expected exception class names and messages
- public handler call records

It must not depend on private stack shape, cycle counters, history records, or
other simulator internals.
