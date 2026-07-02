The guard `enabled > 0 && enabled < 0` is contradictory (no integer is both >0 and <0). This is SMT-proven (W_DEAD_GUARD). The `enabled` variable is also never written after initialization (W_UNREAD_VAR, W_GUARD_VARS_NEVER_CHANGE).

The smallest fix: the `&&` was meant to be `||` (making it a tautology), so the guard is effectively unconditional. I'll remove the guard and the now-unused variable.

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