# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 3 warnings / 2 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## W_UNWRITTEN_READ_VAR

- Severity: `warning`
- Location: `input.fcstm:1:1`
- Message: Variable 'enabled' is read but never written by any action or transition effect.
- Source: inspect-static
- Why it matters: The variable is used as input but never updated after its initial definition, so model behavior may be accidentally constant.
- Source:
  ```fcstm
  1 | def int enabled = 1;
    | ^^^^^^^^^^^^^^^^^^^^
  2 |
  ```
- Recommended actions:
  - `add_write` / target `action_or_effect`: Add the intended update if the variable should change.
  - `simplify_guard` / target `expression`: Replace the read with a literal if the value is intentionally constant.
- Do not:
  - Do not add a meaningless self-assignment.
- Repair notes:
  - This is a static dataflow warning about missing writes after initialization.
  - Do not add a self-assignment or dummy update only to silence the warning.

## W_GUARD_VARS_NEVER_CHANGE

- Severity: `warning`
- Location: `input.fcstm:10:5`
- Message: Transition guard reads only variables that are never changed by actions or effects.
- Source: inspect-static
- Why it matters: This guard is controlled only by initial variable values. If those values never change, the transition condition is effectively fixed.
- Source:
  ```fcstm
   9 |
  10 |     Service -> Fault : if [enabled > 0 && enabled < 0];
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  11 |     Fault -> Shutdown;
  ```
- Recommended actions:
  - `add_write` / target `action_or_effect`: Add the missing state update if the guard should evolve at runtime.
  - `simplify_guard` / target `transition`: Simplify or remove the guard if the initial value is intentional.
- Do not:
  - Do not add a meaningless self-assignment; it does not model a real change.
  - Do not rewrite the guard to a meaningless constant only to silence this diagnostic.
- Repair notes:
  - This is a static dataflow warning, not a proof that the guard is satisfiable.
  - Adding a write is useful only when the variable should genuinely evolve at runtime.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:11:5`
- Message: Transition 'Root.Fault' -> 'Root.Shutdown' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
  10 |     Service -> Fault : if [enabled > 0 && enabled < 0];
  11 |     Fault -> Shutdown;
     |     ^^^^^^^^^^^^^^^^^^
  12 |     Shutdown -> [*];
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:12:5`
- Message: Transition 'Root.Shutdown' -> '[*]' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
  11 |     Fault -> Shutdown;
  12 |     Shutdown -> [*];
     |     ^^^^^^^^^^^^^^^^
  13 | }
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## W_DEAD_GUARD

- Severity: `warning`
- Location: `input.fcstm:10:5`
- Message: A transition guard is unsatisfiable under model variable type and runtime-definedness constraints.
- Source: verify-backed
- Why it matters: SMT proves the guard cannot become true for any valid variable valuation. This differs from W_GUARD_CONST_FALSE, which only reports literal-only guards folded syntactically to false.
- Source:
  ```fcstm
   9 |
  10 |     Service -> Fault : if [enabled > 0 && enabled < 0];
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  11 |     Fault -> Shutdown;
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
