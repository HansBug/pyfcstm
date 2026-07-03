`★ Insight ─────────────────────────────────────`
The guard `request > 0 && request < 0` is provably unsatisfiable (SMT-backed W_DEAD_GUARD). Since `Idle`'s `during` only increments `request`, the modeler's intent is almost certainly "fire once request has been counted up," so the smallest intent-preserving edit is to drop the contradictory `&& request < 0` clause. The `Running -> [*]` info diagnostic is a deliberate fall-through and stays.
`─────────────────────────────────────────────────`

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
