# Simulate semantic fixture schema

This directory stores shared semantic fixtures for Python-side simulator and
built-in Python runtime alignment tests.  A fixture is a pair of files under
`cases/`:

- `<id>.fcstm`: the FCSTM DSL source.
- `<id>.yaml`: metadata, input sequence, runner selection, and expectations.

The schema is intentionally strict. Unknown top-level fields, unknown runner
names, unknown categories, unknown expectation fields, and unknown nested fields
inside `cycle`, `raises`, `logs`, `stack`, and CLI expectations must fail fast
with a diagnostic containing the case id and YAML path.

## Top-level fields

| Field | Required | Description |
|---|---:|---|
| `schema_version` | yes | Fixed integer value `1`. |
| `id` | yes | Stable snake-case id. Must match the YAML basename. |
| `title` | yes | Human-readable title. |
| `source.fcstm` | yes | FCSTM file name in the same directory. |
| `origin.files` | yes | Original pytest functions that this fixture migrates from. |
| `origin.docs` | no | Optional design-document references. |
| `origin.assertion_types` | no | Review hint: assertion families carried over from the original test. |
| `origin.notes` | no | Optional migration notes, especially for split parametrized cases. |
| `categories` | yes | Non-empty list from the allowed category set. |
| `runners` | yes | Non-empty list from the allowed runner set. |
| `initial` | no | Runtime construction state and vars. |
| `runtime_options` | no | Simulation-only runtime options such as abstract-handler error mode. |
| `steps` | conditional | Required for runtime/alignment runners. Mutually exclusive with `commands`. |
| `commands` | conditional | Required for CLI runner. Mutually exclusive with `steps`. |
| `handlers` | no | Simulation-only abstract-handler fixtures for recording calls or raising errors. |
| `expected_failure` | reserved | Reserved for inactive regression fixtures that should not run in the main corpus. |

Allowed categories:

- `runtime`
- `template_alignment`
- `design_example`
- `scenario_example`
- `hot_start`
- `cli`
- `event_paths`
- `temporary_vars`
- `if_blocks`
- `abstract`
- `pseudo_chain`
- `validation`
- `lifecycle`

Allowed runners:

- `simulation`
- `generated_python_alignment`
- `cli_command`

`cli_command` must be the only runner in a case. Runtime/alignment cases use
`steps`; CLI cases use `commands`.

`runtime_options` and `handlers` are accepted only for simulation-only cases.
They are rejected when `generated_python_alignment` is present, because the
generated Python runtime runner intentionally covers the shared public runtime
surface and does not install Python callback handlers.

## Runtime options

```yaml
runtime_options:
  abstract_error_mode: log
```

Allowed fields:

- `abstract_error_mode`: `raise` or `log`, passed to
  `SimulationRuntime(..., abstract_error_mode=...)`.

Unknown runtime option fields are rejected. Add new options deliberately in the
schema and loader tests instead of silently accepting ignored data.

## Abstract-handler fixtures

Handlers let simulation-only cases express callback side effects in YAML:

```yaml
handlers:
  - action: Root.RootInit
    behavior: record_call
  - action: Root.A.Boom
    behavior: raise_error
    exception:
      type: ValueError
      message: boom
  - action: Root.A.Touch
    behavior: record_var_write_attempt
    write:
      name: x
      value: 999
```

Allowed handler behaviors:

- `record_call`: registers a handler that appends a call record.
- `raise_error`: registers a handler that appends a call record and then raises
  the configured exception.
- `record_var_write_attempt`: registers a handler that attempts one
  `ctx.vars[name] = value` assignment and records whether the read-only
  context rejected it.

Handler call records have this shape:

```yaml
action: Root.RootInit
state: Root
stage: enter
vars:
  x: 0
write_attempt:
  name: x
  value: 999
  succeeded: false
  error_type: TypeError
  vars:
    x: 0
```

Only `ValueError` is currently supported for `raise_error`, because the fixture
corpus only needs a deterministic user-handler exception class for simulator
rollback semantics. If another exception family is needed, extend the allowed
set together with schema-negative tests.

## Runtime steps

A runtime step is either an initial assertion or a cycle call:

```yaml
steps:
  - expect_initial:
      state: [Root, A]
      vars:
        counter: 0
      ended: false
      stack:
        - path: [Root]
          mode: active
        - path: [Root, A]
          mode: active
  - cycle:
      events: [Root.A.Go]
    expect:
      state: [Root, B]
      vars:
        counter: 10
      ended: false
      return: null
```

`cycle` may be `{}`, `null`, a bare event-path string, or a mapping with
only the `events` field. A bare string such as `cycle: Root.A.Go` is passed
unchanged as a single `runtime.cycle("Root.A.Go")` input so fixtures can cover
string-vs-list API boundaries.

`events` may be `null` or a list. Each list item may be either an event-path
string or an event-like descriptor with exactly one `event_like` key, for
example `{event_like: Root.A.Go}`. The runner converts that descriptor into a
local object exposing `path_name = "Root.A.Go"` and passes the object to the
runtime under test.

Event strings are passed through unchanged. The corpus covers existing event
path forms such as full paths (`Root.A.Go`), relative paths (`go`),
parent-relative paths (`.go`), and root-relative paths (`/go`).

## Expectation fields

| Field | Meaning |
|---|---|
| `state` | Expected current state path as a list of segments, or `null` for ended runtime. |
| `vars` | Partial variable-value assertion. |
| `vars_exact` | Exact full `dict(runtime.vars)` assertion. |
| `vars_keys` | Exact variable key-set assertion. |
| `vars_absent` | Variables that must not be present. |
| `ended` | Expected `runtime.is_ended`. |
| `stack` | Expected `brief_stack`, with `path` list and `mode`. |
| `cycle_count` | Simulation/CLI-only cycle count assertion. Rejected for generated alignment cases. |
| `return` | Expected `cycle()` return value. |
| `raises` | Expected exception class name and optional message match. |
| `logs` | Step-local `caplog` assertions. |
| `warnings` | Step-local Python warning assertions. Simulation-only. |
| `handler_calls` | Exact accumulated fixture-handler call records. Simulation-only. |
| `abstract_handler_errors` | Expected `runtime.abstract_handler_errors` records. Simulation-only. |
| `error_state` | Expected `runtime.is_error_state`. Simulation-only. |
| `error_info` | Expected `runtime.error_info` action, exception type, and optional message match. Simulation-only. |

Allowed stack modes are `active` and `init_wait`.

`vars` and `vars_exact` may both be present only when the partial `vars` mapping
is consistent with `vars_exact`. `vars_keys` and `vars_absent` must not overlap.
`raises` and `return` are mutually exclusive.

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

Allowed exception type names are:

- `SimulationRuntimeDfsError`
- `SimulationRuntimeEventError`
- `SimulationRuntimeExpressionError`
- `ValueError`

`match_kind` may be `substring` or `regex`; default is `substring`.
Exception steps may still assert rollback state, vars, ended status, and stack.
`raises` only allows the fields `type`, `match`, and `match_kind`; misspelled
message fields must be rejected instead of weakening the exception assertion.

## Logs

```yaml
expect:
  logs:
    contains:
      - level: WARNING
        message: Unable to reach a stoppable state
        match_kind: substring
    not_contains:
      - level: ERROR
        message: Traceback
        match_kind: substring
```

Logs are captured per step. The helper clears `caplog` before each step and
includes the case id, step index, expected message, level, and actual records in
failure messages. `logs` only allows `contains` and `not_contains`; each log
matcher only allows `level`, `message`, and `match_kind`.

## Warnings

```yaml
expect:
  warnings:
    count: 1
    contains:
      - category: UserWarning
        message: Root.Bad.<unnamed>
        match_kind: substring
    not_contains:
      - category: UserWarning
        message: validation-only
        match_kind: substring
```

Warnings are captured per step only when `warnings` is present. `count`, when
present, asserts the exact number of warning records emitted during that step.
`contains` and `not_contains` use the same `substring` / `regex` match policy as
logs. The only allowed category name in this schema version is `UserWarning`.

## Handler calls and handler errors

```yaml
expect:
  handler_calls:
    - action: Root.RootInit
      state: Root
      stage: enter
      vars:
        x: 0
  abstract_handler_errors:
    - action: Root.A.Boom
      type: ValueError
      message: boom
      match_kind: substring
  error_state: true
  error_info:
    action: Root.A.Boom
    type: ValueError
    message: boom
    match_kind: substring
```

`handler_calls` is an exact accumulated-list assertion over the fixture handlers
registered by the top-level `handlers` field. Use `handler_calls: []` to prove a
failed speculative execution did not invoke any handler.

When a handler call includes `write_attempt`, the record asserts the attempted
variable name, attempted value, success flag, optional exception type, and the
handler-visible variable snapshot after the attempt. This is intended for
simulation-only checks of `ReadOnlyExecutionContext.vars`.

`abstract_handler_errors` matches the public
`SimulationRuntime.abstract_handler_errors` list. Each item may assert `action`,
`type`, and `message`; `message` supports `substring` or `regex` via
`match_kind`. Use `abstract_handler_errors: []` to prove failed rollback did not
leave committed error metadata.

`error_info` uses the same `action`, `type`, `message`, and `match_kind` shape
for `SimulationRuntime.error_info`. Use `error_info: null` when a simulation-only
case needs to assert that no error-state metadata is present.

## Generated Python alignment runner

`generated_python_alignment` builds a `SimulationRuntime` and a generated Python
runtime from the same fixture DSL. The generated runtime is rendered from the
packaged built-in `python` template via `extract_template("python", ...)`, which
preserves the old `test_runtime_alignment.py` release-surface coverage rather
than testing only the repository source template directory. It checks alignment
at construction time and after every step:

- `is_ended`
- variables
- current state path
- `brief_stack`
- `cycle()` return value
- exception class names for expected exception paths

Even when YAML does not contain an explicit `stack` assertion, the alignment
runner compares both stacks internally. `cycle_count` is rejected for generated
alignment cases because the generated runtime does not expose it as a public
contract. `runtime_options`, `handlers`, `warnings`, `handler_calls`,
`abstract_handler_errors`, `error_state`, and `error_info` are also rejected for
generated alignment cases in this schema version.

## CLI command cases

CLI cases use `commands`:

```yaml
runners: [cli_command]
commands:
  - input: init System.Active counter=5 flag=1
    expect:
      output_contains:
        - Initialized from state: System.Active
      output_not_contains:
        - Error
      runtime:
        state: [System, Active]
        vars:
          counter: 5
          flag: 1
        ended: false
```

CLI output is ANSI-stripped before assertion. `runtime` reuses the public
runtime expectation subset: `state`, `vars`, `vars_exact`, `vars_keys`,
`vars_absent`, `ended`, `stack`, and `cycle_count`.

`output_contains`, `output_not_contains`, and `error_contains` must be lists of
strings. `should_exit`, when present, must be a boolean.

## Reserved fields

`expected_failure` is intentionally not active in this schema version. Any
extension that needs inactive expected-failure fixtures must update this schema
and the loader tests rather than silently accepting ignored data.
