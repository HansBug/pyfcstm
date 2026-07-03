# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 4 warnings / 3 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## W_UNREFERENCED_VAR

- Severity: `warning`
- Location: `input.fcstm:1:1`
- Message: Variable 'done' does not affect any transition guard.
- Source: inspect-static
- Why it matters: This variable does not participate in model decisions. It is dead from the DSL's guard-affect data-flow perspective.
- Source:
  ```fcstm
  1 | def int done = 0;
    | ^^^^^^^^^^^^^^^^^
  2 |
  ```
- Recommended actions:
  - `remove_variable` / target `variable_definition`: Remove the variable and related writes if it was speculative scaffolding.
  - `connect_to_guard` / target `guard_or_assignment`: Add the missing data-flow path if the variable should affect a transition decision.
- Do not:
  - Do not add a dummy guard reference only to silence the diagnostic.
- Repair notes:
  - A declaration-only variable may be speculative scaffolding.
  - Remove it only when no guard, assignment, abstract action, or external integration intent needs it.

## W_REDUNDANT_TRANSITION

- Severity: `warning`
- Location: `input.fcstm:9:5`
- Message: Transition 'Root.Idle' -> 'Root.Done' is duplicated with the same event, guard, and effect.
- Source: inspect-static
- Why it matters: These transitions are indistinguishable by source, target, event, guard, and effect, so later copies do not add behavior.
- Source:
  ```fcstm
   8 |
   9 |     Idle -> Done effect { done = done; };
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  10 |     Idle -> Done effect { done = done; };
  ```
- Recommended actions:
  - `remove_duplicate` / target `transition`: Keep one transition and remove redundant copies.
  - `differentiate_transition` / target `transition`: Change event, guard, target, or effect if the copy was meant to do something else.
- Do not:
  - Do not keep duplicate transitions as comments.
- Repair notes:
  - Remove only the duplicate transition or merge duplicate no-op effects.
  - Keep the state structure and one intentional transition unless the report proves the element itself is unused.

## W_EFFECT_SELF_ASSIGN

- Severity: `warning`
- Location: `input.fcstm:9:27`
- Message: Transition effect assigns 'done' to itself.
- Source: inspect-static
- Why it matters: The assignment does not change model state and is likely dead code.
- Source:
  ```fcstm
   8 |
   9 |     Idle -> Done effect { done = done; };
     |                           ^^^^^^^^^^^^
  10 |     Idle -> Done effect { done = done; };
  ```
- Recommended actions:
  - `remove_statement` / target `effect_statement`: Delete the self-assignment.
  - `fix_rhs` / target `expression`: Replace the right-hand side with the intended expression.
- Do not:
  - Do not replace it with another no-op expression.
- Repair notes:
  - A self-assignment is a no-op and does not model real progress.
  - If the variable exists only for that no-op effect, remove the variable and no-op effect instead of inventing a write that still does not affect a guard.

## W_EFFECT_SELF_ASSIGN

- Severity: `warning`
- Location: `input.fcstm:10:27`
- Message: Transition effect assigns 'done' to itself.
- Source: inspect-static
- Why it matters: The assignment does not change model state and is likely dead code.
- Source:
  ```fcstm
   9 |     Idle -> Done effect { done = done; };
  10 |     Idle -> Done effect { done = done; };
     |                           ^^^^^^^^^^^^
  11 |     Done -> [*];
  ```
- Recommended actions:
  - `remove_statement` / target `effect_statement`: Delete the self-assignment.
  - `fix_rhs` / target `expression`: Replace the right-hand side with the intended expression.
- Do not:
  - Do not replace it with another no-op expression.
- Repair notes:
  - A self-assignment is a no-op and does not model real progress.
  - If the variable exists only for that no-op effect, remove the variable and no-op effect instead of inventing a write that still does not affect a guard.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:9:5`
- Message: Transition 'Root.Idle' -> 'Root.Done' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
   8 |
   9 |     Idle -> Done effect { done = done; };
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  10 |     Idle -> Done effect { done = done; };
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:10:5`
- Message: Transition 'Root.Idle' -> 'Root.Done' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
   9 |     Idle -> Done effect { done = done; };
  10 |     Idle -> Done effect { done = done; };
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  11 |     Done -> [*];
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:11:5`
- Message: Transition 'Root.Done' -> '[*]' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
  10 |     Idle -> Done effect { done = done; };
  11 |     Done -> [*];
     |     ^^^^^^^^^^^^
  12 | }
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.
