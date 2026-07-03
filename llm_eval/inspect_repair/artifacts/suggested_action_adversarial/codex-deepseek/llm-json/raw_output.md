The key issue is `enabled > 0 && enabled < 0` — SMT proves no integer satisfies both. Since `enabled` is initialized to 1 and never written, the guard is not only contradictory but also effectively constant. The smallest fix: remove the dead guard and the unused variable, making the transition unconditional (the info-level fall-through diagnostics are permitted to remain).

```fcstm
state Root {
    [*] -> Service;

    state Service;
    state Fault;
    state Shutdown;

    Service -> Fault;
    Fault -> Shutdown;
    Shutdown -> [*];
}
```