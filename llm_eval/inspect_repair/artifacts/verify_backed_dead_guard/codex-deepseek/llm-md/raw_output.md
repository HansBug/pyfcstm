The `request > 0 && request < 0` guard is SMT-proven unsatisfiable — no integer can be both above zero and below zero. The model increments `request` in `Idle`'s `during` block, so the clear intent is to transition to `Running` once `request` becomes positive. Stripping the contradictory second conjunct is the minimal fix.

```fcstm
def int request = 0;

state Root {
    [*] -> Idle;

    state Idle {
        during { request = request + 1; }
    }
    state Running;

    Idle -> Running : if [request > 0];
    Running -> [*];
}
```