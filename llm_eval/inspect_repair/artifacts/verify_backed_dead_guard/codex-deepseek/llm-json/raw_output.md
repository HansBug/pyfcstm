The guard `request > 0 && request < 0` is contradictory (SMT-proven unsatisfiable). The model increments `request` in `Idle`'s `during` block, so the apparent intent is to transition when `request` exceeds zero. Removing the impossible `&& request < 0` conjunct is the smallest fix.

The `Running -> [*]` info diagnostic is an intentional unconditional fall-through — the report confirms this can remain.

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