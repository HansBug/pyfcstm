# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 2 warnings / 1 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## W_COMBO_DUPLICATE_EVENT

- Severity: `warning`
- Location: `input.fcstm:9:38`
- Message: Combo trigger repeats event 'Root.Waiting.Request'; this is legal but usually redundant.
- Source: inspect-static
- Why it matters: The combo trigger contains the same resolved event twice, for example ``E1 + E1``. This is legal but normally redundant because one cycle's input event set already contains ``E1``.
- Source:
  ```fcstm
   8 |
   9 |     Waiting -> Accepted :: Request + Request;
     |                                      ^^^^^^^
  10 |     Accepted -> [*];
  ```
- Recommended actions:
  - `inspect_terms` / target `transition`: Check whether the second event was meant to be a different event.
  - `keep_if_intentional` / target `transition`: Keep it only if the explicit two-hop pseudo chain is intentional.
- Do not:
  - Do not silently delete the repeated event; the explicit pseudo-chain shape may be intentional.
- Repair notes:
  - Repeated identical event terms are presence-based and are usually redundant.
  - If there is no evidence that the explicit two-hop pseudo chain is intentional, reducing the duplicated term to one event is the smallest semantic repair.

## W_UNREFERENCED_VAR

- Severity: `warning`
- Location: `input.fcstm:1:1`
- Message: Variable 'ready' does not affect any transition guard.
- Source: inspect-static
- Why it matters: This variable does not participate in model decisions. It is dead from the DSL's guard-affect data-flow perspective.
- Source:
  ```fcstm
  1 | def int ready = 1;
    | ^^^^^^^^^^^^^^^^^^
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

## I_TRANSITION_NEVER_EVENT_TRIGGERED

- Severity: `info`
- Location: `input.fcstm:10:5`
- Message: Transition 'Root.Accepted' -> '[*]' has no event or guard.
- Source: inspect-static
- Why it matters: The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target.
- Source:
  ```fcstm
   9 |     Waiting -> Accepted :: Request + Request;
  10 |     Accepted -> [*];
     |     ^^^^^^^^^^^^^^^^
  11 | }
  ```
- Recommended actions:
  - `keep_if_fallthrough` / target `transition`: Keep it when the state should immediately advance.
  - `add_trigger_or_guard` / target `transition`: Add the missing event or guard if the transition should wait.
- Do not:
  - Do not add a meaningless event just to silence this info.
