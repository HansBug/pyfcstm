`★ Insight ─────────────────────────────────────`
- The guard `retry > 0 && retry < 0` is a proven contradiction (SMT-backed `W_DEAD_GUARD`), and `retry` is never written — so the whole variable + guard machinery is dead scaffolding, not a real data-flow spine.
- The model's shape (Waiting → Recovering → Done) reads like an event-driven recovery flow; per the repair rules, when converting a guarded transition to an event makes the variable unused, we should also drop the variable rather than invent a fake writer.
- Adding `Done -> [*];` gives the root a topological exit, resolving the deadlock-leaf and no-exit warnings without an unconditional silencer.
`─────────────────────────────────────────────────`

```fcstm
state Root {
    [*] -> Waiting;

    state Waiting;
    state Recovering;
    state Done;

    Waiting -> Recovering :: RetryNeeded;
    Recovering -> Done :: RecoveryComplete;
    Done -> [*];
}
```
