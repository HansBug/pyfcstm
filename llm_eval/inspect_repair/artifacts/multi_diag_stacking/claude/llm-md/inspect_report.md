# FCSTM Inspect Report

- Schema: `pyfcstm.inspect.llm.v1`
- Schema status: `stable`
- Status: `warning`
- Input: `input.fcstm`
- Diagnostics: 0 errors / 7 warnings / 1 infos

## Repair protocol

- Make the smallest source edit that preserves the modeler's apparent intent.
- Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.
- Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.
- Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.
- A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.
- If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.

## W_UNREACHABLE_STATE

- Severity: `warning`
- Location: `input.fcstm:8:5`
- Message: State 'Root.Done' is unreachable from the root entry path.
- Source: inspect-static
- Why it matters: This state cannot be entered at runtime; the surrounding transitions never lead to it. It is dead from the machine's perspective.
- Source:
  ```fcstm
  7 |     state Recovering;
  8 |     state Done;
    |     ^^^^^^^^^^^
  9 |
  ```
- Recommended actions:
  - `add_inbound_transition` / target `state`: Add a transition that reaches the state if it was meant to be used.
  - `remove_state` / target `state`: Remove the state if it was added speculatively.
- Do not:
  - Do not add a self-loop to mask the unreachability.

## W_DEADLOCK_LEAF

- Severity: `warning`
- Location: `input.fcstm:7:5`
- Message: Leaf state 'Root.Recovering' has no outgoing transition.
- Source: inspect-static
- Why it matters: This leaf state has no outgoing transition, so once the machine enters it there is no modeled way to leave.
- Source:
  ```fcstm
  6 |     state Waiting;
  7 |     state Recovering;
    |     ^^^^^^^^^^^^^^^^^
  8 |     state Done;
  ```
- Recommended actions:
  - `add_transition` / target `state`: Add a modeled transition to the next intended state.
  - `add_exit_transition` / target `state`: Add ``State -> [*];`` if the leaf is meant to finish its parent.
- Do not:
  - Do not add a self-loop just to silence the warning.

## W_DEADLOCK_LEAF

- Severity: `warning`
- Location: `input.fcstm:8:5`
- Message: Leaf state 'Root.Done' has no outgoing transition.
- Source: inspect-static
- Why it matters: This leaf state has no outgoing transition, so once the machine enters it there is no modeled way to leave.
- Source:
  ```fcstm
  7 |     state Recovering;
  8 |     state Done;
    |     ^^^^^^^^^^^
  9 |
  ```
- Recommended actions:
  - `add_transition` / target `state`: Add a modeled transition to the next intended state.
  - `add_exit_transition` / target `state`: Add ``State -> [*];`` if the leaf is meant to finish its parent.
- Do not:
  - Do not add a self-loop just to silence the warning.

## W_UNWRITTEN_READ_VAR

- Severity: `warning`
- Location: `input.fcstm:1:1`
- Message: Variable 'retry' is read but never written by any action or transition effect.
- Source: inspect-static
- Why it matters: The variable is used as input but never updated after its initial definition, so model behavior may be accidentally constant.
- Source:
  ```fcstm
  1 | def int retry = 0;
    | ^^^^^^^^^^^^^^^^^^
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
  10 |     Waiting -> Recovering : if [retry > 0 && retry < 0];
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  11 | }
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

## W_TOPOLOGICAL_NOEXIT

- Severity: `warning`
- Location: `input.fcstm:7:5`
- Message: A root-reachable leaf or cycle has no guard-agnostic route to the root exit sink.
- Source: verify-backed
- Why it matters: From the current topology, execution can enter a region that has no structural path to terminate at the root exit.
- Source:
  ```fcstm
  6 |     state Waiting;
  7 |     state Recovering;
    |     ^^^^^^^^^^^^^^^^^
  8 |     state Done;
  ```
- Recommended actions:
  - `add_exit_transition` / target `topology`: Add a route from the stuck state or cycle to an exit-capable path.
  - `mark_intentional` / target `review_note`: If the model intentionally never exits, keep the behavior and document it.
- Do not:
  - Do not add an unconditional exit without checking lifecycle and event semantics.
- Repair notes:
  - This is verify-backed topology feedback, not an instruction to add an unconditional exit blindly.

## I_TOPOLOGICAL_NON_TERMINATING

- Severity: `info`
- Location: `input.fcstm:7:5`
- Message: The topology does not force all root-reachable executions to eventually reach the root terminator.
- Source: verify-backed
- Why it matters: The structural graph allows a path that can avoid termination forever. This may be a valid service loop, but it should be reviewed explicitly.
- Source:
  ```fcstm
  6 |     state Waiting;
  7 |     state Recovering;
    |     ^^^^^^^^^^^^^^^^^
  8 |     state Done;
  ```
- Recommended actions:
  - `review_nontermination` / target `topology`: Decide whether the non-terminating path is intended.
  - `add_progress_transition` / target `transition`: Add an exit or progress edge if all executions should eventually finish.
- Do not:
  - Do not treat every loop as a bug; long-running control loops are common state-machine behavior.
- Repair notes:
  - Long-running control loops can be intentional; decide intent before adding progress edges.

## W_DEAD_GUARD

- Severity: `warning`
- Location: `input.fcstm:10:5`
- Message: A transition guard is unsatisfiable under model variable type and runtime-definedness constraints.
- Source: verify-backed
- Why it matters: SMT proves the guard cannot become true for any valid variable valuation. This differs from W_GUARD_CONST_FALSE, which only reports literal-only guards folded syntactically to false.
- Source:
  ```fcstm
   9 |
  10 |     Waiting -> Recovering : if [retry > 0 && retry < 0];
     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  11 | }
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
