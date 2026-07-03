# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 2 warnings / 2 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## W_UNREACHABLE_STATE

- Severity: `warning`
- Location: `input.fcstm:6:5`
- Message: State 'Root.Ghost' is unreachable from the root entry path.
- Source: inspect-static
- Why it matters: This state cannot be entered at runtime; the surrounding transitions never lead to it. It is dead from the machine's perspective.
- Source:
  ```fcstm
  5 |     state Done;
  6 |     state Ghost;
    |     ^^^^^^^^^^^^
  7 |
  ```
- Recommended actions:
  - `add_inbound_transition` / target `state`: Add a transition that reaches the state if it was meant to be used.
  - `remove_state` / target `state`: Remove the state if it was added speculatively.
- Do not:
  - Do not add a self-loop to mask the unreachability.

## W_DEADLOCK_LEAF

- Severity: `warning`
- Location: `input.fcstm:6:5`
- Message: Leaf state 'Root.Ghost' has no outgoing transition.
- Source: inspect-static
- Why it matters: This leaf state has no outgoing transition, so once the machine enters it there is no modeled way to leave.
- Source:
  ```fcstm
  5 |     state Done;
  6 |     state Ghost;
    |     ^^^^^^^^^^^^
  7 |
  ```
- Recommended actions:
  - `add_transition` / target `state`: Add a modeled transition to the next intended state.
  - `add_exit_transition` / target `state`: Add ``State -> [*];`` if the leaf is meant to finish its parent.
- Do not:
  - Do not add a self-loop just to silence the warning.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:8:5`
- Message: Transition 'Root.Idle' -> 'Root.Done' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
  7 |
  8 |     Idle -> Done;
    |     ^^^^^^^^^^^^^
  9 |     Done -> [*];
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:9:5`
- Message: Transition 'Root.Done' -> '[*]' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
   8 |     Idle -> Done;
   9 |     Done -> [*];
     |     ^^^^^^^^^^^^
  10 | }
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.
