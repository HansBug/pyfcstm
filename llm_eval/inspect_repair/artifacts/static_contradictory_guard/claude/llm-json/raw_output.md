`★ Insight ─────────────────────────────────────`
The guard `request > 0 && request < 0` is unsatisfiable and `request` is never written. Since the modeler's apparent intent is a request-driven transition, converting to an event trigger (`:: Request`) preserves intent while removing the dead variable — this simultaneously clears `W_UNWRITTEN_READ_VAR` and `W_GUARD_VARS_NEVER_CHANGE` with one minimal semantic edit rather than stacking suggested actions.
`─────────────────────────────────────────────────`

```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running :: Request;
    Running -> [*];
}
```
