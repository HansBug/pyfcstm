# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 1 warnings / 1 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:12:5`
- Message: Transition 'Root.Running' -> '[*]' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
  11 |     Idle -> Running : if [request > 0 && request < 0];
  12 |     Running -> [*];
     |     ^^^^^^^^^^^^^^^
  13 | }
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## W_DEAD_GUARD

- Severity: `warning`
- Location: `input.fcstm:11:5`
- Message: A transition guard is unsatisfiable under model variable type and runtime-definedness constraints.
- Source: verify-backed
- Why it matters: SMT proves the guard cannot become true for any valid variable valuation. This differs from W_GUARD_CONST_FALSE, which only reports literal-only guards folded syntactically to false.
- Source:
  ```fcstm
  10 |
  11 |     Idle -> Running : if [request > 0 && request < 0];
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  12 |     Running -> [*];
  ```
- Recommended actions:
  - `fix_guard` / target `transition`: Relax or correct the contradictory guard condition.
  - `remove_transition` / target `transition`: Remove the transition if the guard intentionally makes it unreachable.
- Do not:
  - Do not replace the guard with true unless the transition really should become unconditional.
  - Do not confuse this SMT finding with W_GUARD_CONST_FALSE; variables and runtime-definedness matter here.
- Repair notes:
  - This is verify-backed: SMT proved the guard unsatisfiable under model constraints.
  - Prefer correcting the contradictory guard over making the transition unconditional.
  - If the same variable also has static dataflow warnings, the repair must address both the contradiction and the missing guard-affecting data flow.
