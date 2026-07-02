The diagnostics reveal that `request` is initialized to 0, never updated, making the guard `[request > 0]` permanently false. The apparent intent is a request-driven transition, so the natural fix is replacing the dead guard with an event trigger. The `Running -> [*]` unconditional fall-through is deliberate and the info diagnostic on it can remain.

```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running : /RequestStart;
    Running -> [*];
}
```