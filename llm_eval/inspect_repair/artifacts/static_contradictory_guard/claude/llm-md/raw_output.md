★ Insight ─────────────────────────────────────
- The guard `request > 0 && request < 0` is unsatisfiable and the variable is never written — the modeler likely intended an external trigger. Converting to an event transition (`:: Request`) removes both warnings with one minimal edit.
- Since `request` becomes unused after the switch, the grammar guide explicitly says to remove the variable rather than keep dead data-flow (per repair rules).
- The `Running -> [*]` info-level diagnostic is allowed to remain as an intentional fall-through.
─────────────────────────────────────────────────

```
state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running :: Request;
    Running -> [*];
}
```
