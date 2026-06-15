# Simulate semantic fixture schema

This directory stores the shared semantic fixture corpus for Python-side
simulator and built-in Python runtime alignment tests. A fixture is a pair of files under
`cases/`:

- `<id>.fcstm`: the FCSTM DSL source.
- `<id>.yaml`: metadata, input sequence, runner selection, and expectations.

The corpus is the long-term single source of truth for executable FCSTM
semantics on the Python side. Cases that target generated Python alignment must
also remain executable by the simulator runner, and both runners must consume
the same YAML schema, FCSTM source, handler setup, cycle inputs, and expectation
shape. Template-specific tests may add runner adapters, but they must not fork
the semantic cases into an isolated template-only fixture system.

The schema is intentionally strict. Unknown top-level fields, unknown runner
names, unknown categories, unknown expectation fields, and unknown nested fields
inside `cycle`, `cycle_result`, `history`, `raises`, `logs`, `stack`, handler
calls, and CLI expectations must fail fast with a diagnostic containing the case
id and YAML path.

This corpus is currently in a migration window. Existing legacy cases may still
use older simulator-debugging expectations while the corpus is being cleaned up,
but any newly added shared case should follow the pure shared boundary documented
below. The pure shared boundary is the contract for new cross-runtime cases:
simulation plus generated Python alignment, public observation surface only,
and no simulator-only, CLI-only, or model-construction diagnostics.

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
| `runtime_options` | no | Simulation-only runtime options such as abstract-handler error mode. Legacy corpus only; new pure shared cases should not add it. |
| `model_build` | conditional | Simulation-only model-construction diagnostic expectation. Mutually exclusive with `steps` and `commands`. Legacy corpus only; new pure shared cases should not add it. |
| `steps` | conditional | Required for runtime/alignment runners. Mutually exclusive with `model_build` and `commands`. New pure shared cases should keep only public observation fields inside step expectations. |
| `commands` | conditional | Required for CLI runner. Mutually exclusive with `model_build` and `steps`. Legacy CLI fixture shape only; new pure shared cases should not add it. |
| `handlers` | no | Abstract-handler fixtures for recording calls or raising errors. Requires the `simulation` runner and may also be used for generated Python alignment in the legacy corpus. |
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
`steps`; CLI cases use `commands`; model-construction diagnostic cases use
`model_build`. Exactly one of `model_build`, `steps`, or `commands` must be
present.

`runtime_options` is accepted only for simulation-only cases. `handlers`
requires the `simulation` runner. Every `generated_python_alignment` case must
also include `simulation` so the generated runtime is checked against the same
semantic input that the simulator executes. When `generated_python_alignment`
is present, the same handler behavior is installed into both runtimes so
callback context and side-effect isolation stay aligned.

## Runtime construction diagnostics

`initial` normally provides optional runtime construction inputs:

```yaml
initial:
  state: Root.A
  vars:
    counter: 0
```

When construction itself is expected to fail, `initial.expect.raises` records
the constructor-time diagnostic. This shape is supported by `simulation` and
`generated_python_alignment` runners:

```yaml
runners: [simulation, generated_python_alignment]
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

Allowed fields:

- `initial.state`: state path string or `null`.
- `initial.vars`: full variable snapshot mapping or `null`.
- `initial.expect.raises`: required constructor exception expectation.

When `initial.expect` is present, `initial.state` and `initial.vars` keys must
both be explicit. Use `null` / `null` to assert cold-start constructor
diagnostics and `initial.vars: {}` for zero-variable hot-start diagnostics.

Construction-diagnostic cases must use `steps: []`; executable steps are
rejected so that constructor failures cannot silently skip later assertions.
`initial.expect` is rejected for `cli_command` cases because CLI diagnostics
belong under `commands[].expect`.

Generated Python alignment cases check constructor outcomes before any cycle
steps run. The alignment helper distinguishes three outcomes:

- both runtimes build successfully;
- both runtimes fail with matching diagnostic type and declared message/cause
  expectations;
- exactly one runtime fails, which is reported as a constructor one-sided
  mismatch.

The one-sided mismatch check is a harness-level parity guard. It does not make
internal stack shape, exception messages, or exception causes public generated
runtime obligations unless a fixture declares those fields or a later semantic
case documents such a contract explicitly.

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

## Model construction diagnostics

`model_build` lets a simulation-only case assert that parsing and model
construction fail before a `SimulationRuntime` is created:

```yaml
runners: [simulation]
model_build:
  expect:
    raises:
      type: ModelValidationError
      match: 'Action reference cycle: Root.A -> Root.A'
      match_kind: substring
```

Allowed fields:

- `model_build.expect.raises`: required exception expectation.

`model_build` is intentionally restricted to `runners: [simulation]`. It cannot
be combined with `generated_python_alignment` or `cli_command`, because those
runners require a successfully built model. It is also mutually exclusive with
`steps` and `commands`.

## Abstract-handler fixtures

Handlers let cases with the `simulation` runner express callback side effects
in YAML:

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
active_leaf: [Root]
call_stage: enter
abstract_target: Root.RootInit
named_ref: null
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

Optional handler-call metadata fields are assertion-only compatibility slots
for richer execution-context checks:

- `active_leaf`: Active leaf path segments observed by the handler. Runtime
  contexts provide this field directly for simulation fixtures; older handler
  records without the field are still compared by deriving it from `state`.
- `call_stage`: Lifecycle stage observed at the callsite. Runtime contexts
  provide this field directly for simulation fixtures; older handler records
  without the field are still compared by deriving it from `stage`.
- `abstract_target`: Abstract action path observed by the handler.
- `named_ref`: Named reference callsite path, or `null` when the action is not
  invoked through a named reference.

The fixture helper may synthesize these optional metadata fields from the
original `action`, `state`, and `stage` record when a handler does not provide
them. That keeps older handler records compatible while reserving stable schema
slots for later runtime-context work. Once concrete metadata is collected by a
handler, the helper preserves the provided values instead of overwriting them.

For generated-runtime alignment, the common call-log terminology maps onto the
fixture fields as follows:

- action name: `action`;
- state path: `state`;
- lifecycle action stage: `stage`;
- variables snapshot: `vars`.

The optional `active_leaf`, `call_stage`, `abstract_target`, and `named_ref`
fields provide additional white-box context assertions without changing the
required common log shape.

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
      cycle_result:
        value: null
      history_tail:
        - cycle: 1
          state: Root.B
          vars:
            counter: 10
          events: [Root.A.Go]
```

`cycle` may be `{}`, `null`, a bare event-path string, or a mapping with
only the `events` field. A bare string such as `cycle: Root.A.Go` is passed
unchanged as a single `runtime.cycle("Root.A.Go")` input so fixtures can cover
string-vs-list API boundaries.

`events` may be `null` or a list. Each list item may be either an event-path
string or an event-object descriptor with exactly one `event` key, for example
`{event: Root.A.Go}`. The runner resolves that descriptor against the fixture
state machine and passes the resulting model `Event` object to the runtime
under test.

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
| `stack` | Expected `brief_stack`, with `path` list and `mode`. Legacy debugging surface; not part of the pure shared boundary for new cases. |
| `cycle_count` | Runtime cycle count assertion. For generated alignment cases the generated runtime must expose the same count. Legacy debugging surface; not part of the pure shared boundary for new cases. |
| `return` | Legacy expected `cycle()` return value. Existing fixtures may keep it; new pure shared cases should use `cycle_result` instead. |
| `cycle_result` | Standardized `cycle()` result object. Current minimum shape is `value`; later event-consumption metadata can extend the same object. |
| `history_length` | Expected length of `runtime.history`. Legacy debugging surface; not part of the pure shared boundary for new cases. |
| `history` | Expected full `runtime.history` sequence after the step. Legacy debugging surface; not part of the pure shared boundary for new cases. |
| `history_tail` | Expected non-empty suffix of `runtime.history` after the step. Use `history_length: 0` or `history: []` to assert no history entries. Legacy debugging surface; not part of the pure shared boundary for new cases. |
| `raises` | Expected exception class name and optional message match. |
| `logs` | Step-local `caplog` assertions. Not part of the pure shared boundary for new cases. |
| `warnings` | Step-local Python warning assertions. Simulation-only. |
| `handler_calls` | Exact accumulated fixture-handler call records. Simulation-only. New pure shared cases may keep only public hook-call records. |
| `abstract_handler_errors` | Expected `runtime.abstract_handler_errors` records. Simulation-only. |
| `error_state` | Expected `runtime.is_error_state`. Simulation-only. |
| `error_info` | Expected `runtime.error_info` action, exception type, and optional message match. Simulation-only. |
| `anonymous_warning_count` | Expected count of anonymous abstract warning dedupe records. Simulation-only, intended for rollback and cleanup diagnostics. |

Allowed stack modes are `active` and `init_wait`.

`vars` and `vars_exact` may both be present only when the partial `vars` mapping
is consistent with `vars_exact`. `vars_keys` and `vars_absent` must not overlap.
`raises`, `return`, and `cycle_result` are mutually exclusive where their
meanings overlap: `raises` cannot be combined with either return assertion, and
`return` cannot be combined with `cycle_result`. `cycle_result` must be a
mapping with a `value` field; use `cycle_result: {value: null}` for the current
`SimulationRuntime.cycle()` return value rather than a top-level
`cycle_result: null`.

For new pure shared cases, treat the public observation surface as the only
stable contract: `state`, `vars`, `ended`, constructor and hot-start results,
per-step cycle state/vars, `handler_calls`, and `cycle_result.value`. Do not add
`stack`, `brief_stack`, `cycle_count`, `history*`, `return`, `warnings`,
`abstract_handler_errors`, `error_state`, `error_info`, or
`anonymous_warning_count` to new shared cases.

`cycle_result` allows these fields:

| Field | Required | Description |
|---|---:|---|
| `value` | yes | Standardized `cycle()` return value. |
| `input_events` | no | Reserved list of normalized input event names. |
| `consumed_events` | no | Reserved list of consumed event names. |
| `unconsumed_events` | no | Reserved list of unconsumed event names. |

The simulator returns a `CycleResult` object. Representative compatibility
fixtures may assert only `cycle_result.value`; event-consumption fields are
optional strict lists of strings, and assertion compares only fields declared by
the fixture so old `{value: null}` cases remain stable.

`history`, `history_tail`, and history entries use the current
`SimulationRuntime.history` shape:

| Field | Description |
|---|---|
| `cycle` | Successful runtime cycle index. |
| `state` | Dot-separated current state path, or `(terminated)`. |
| `vars` | Deep-copied variable snapshot. |
| `events` | List of normalized input event path names. |

`history_tail` must be non-empty and compares the same number of entries from the end of `runtime.history`.

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

- `ModelValidationError`
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
registered by the top-level `handlers` field. For generated alignment cases,
the helper also asserts that simulation and generated callback records match.
Use `handler_calls: []` to prove a failed speculative execution did not invoke
any handler.

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

`anonymous_warning_count` asserts the size of the simulator's anonymous
abstract warning dedupe metadata. It is intentionally narrow and should be used
for warning rollback and cleanup contracts rather than general runtime-state
inspection.

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
- `cycle_count`
- `cycle()` return value
- exception class names for expected exception paths

Even when YAML does not contain an explicit `stack` assertion, the alignment
runner currently compares both stacks internally. That behavior is legacy
helper coverage, not the long-term pure shared contract; new pure shared cases
must not introduce `stack`, `brief_stack`, or `cycle_count` as fixture evidence.
`runtime_options`, `warnings`, `abstract_handler_errors`, `error_state`, and
`error_info` are rejected for generated alignment cases in this schema version.
`handlers` and `handler_calls` are allowed when the fixture also includes
`simulation`; the same fixture handlers are installed in both runtimes and their
call records must match. For new pure shared cases, `handlers` should install
only public `record_call` hook adapters; `raise_error` and
`record_var_write_attempt` remain simulator-diagnostic shapes for migration to
ordinary pytest.

For constructor diagnostics, the alignment runner builds both runtimes,
requires matching exception class names, and then applies the declared
`initial.expect.raises` matcher to each side. It does not require complete
exception-message text equality unless a fixture matcher explicitly declares
that stricter contract.

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
