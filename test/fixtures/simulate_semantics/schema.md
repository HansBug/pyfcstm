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
| `steps` | conditional | Required for runtime/alignment runners. Mutually exclusive with `commands`. |
| `commands` | conditional | Required for CLI runner. Mutually exclusive with `steps`. |
| `handlers` | reserved | PR-0 rejects active handler specs. |
| `xfail_current` | reserved | PR-0 rejects active xfail bug reproductions. |

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

`cycle` may be `{}`, `null`, or a mapping with only the `events` field.
`events` may be `null` or a list. Bare string event input is deliberately not
supported in PR-0, because string-vs-list cycle input is tracked separately.

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

Allowed exception type names in PR-0 are:

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
contract.

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

`handlers`, `xfail_current`, `error_state`, and `error_info` are intentionally
not active in PR-0. If a later PR needs them, it must update this schema and the
loader tests rather than silently accepting ignored data.
