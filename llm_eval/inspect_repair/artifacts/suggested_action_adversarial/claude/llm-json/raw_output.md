`★ Insight ─────────────────────────────────────`
- The guard `enabled > 0 && enabled < 0` is SMT-proven unsatisfiable (dead guard), and `enabled` is initialized but never written — both diagnostics point to the same region.
- The repair protocol explicitly says: if converting to an event trigger leaves a variable unused, remove that variable. This keeps the smallest coherent semantic change: Service faults on an external event, not on a contradictory data condition.
- The two `info` fall-through transitions (`Fault -> Shutdown`, `Shutdown -> [*]`) are allowed to remain — they read as intentional unconditional advance.
`─────────────────────────────────────────────────`

```fcstm
state Root {
    [*] -> Service;

    state Service;
    state Fault;
    state Shutdown;

    Service -> Fault :: FaultDetected;
    Fault -> Shutdown;
    Shutdown -> [*];
}
```
