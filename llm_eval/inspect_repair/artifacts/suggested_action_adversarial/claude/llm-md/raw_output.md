`★ Insight ─────────────────────────────────────`
- The core defect is `enabled > 0 && enabled < 0` — a contradiction proven unsatisfiable by SMT (W_DEAD_GUARD). Any integer fails both halves simultaneously.
- The static warning about `enabled` never being written reinforces that the guard was meant to react to a runtime change, not stay pinned at the initial value 1. The two issues share one root cause: the fault-detection edge was left half-written.
- Smallest intent-preserving repair: convert Service→Fault into an event-triggered transition whose effect actually disables the system, then let Fault→Shutdown test `enabled == 0`. This gives `enabled` both a writer and a meaningful reader, and both remaining transitions gain proper triggers — clearing the warnings and the two fall-through infos in one edit, without inventing dummy assignments or deleting states.
`─────────────────────────────────────────────────`

def int enabled = 1;

state Root {
    [*] -> Service;

    state Service;
    state Fault;
    state Shutdown;

    Service -> Fault :: FaultDetected effect { enabled = 0; }
    Fault -> Shutdown : if [enabled == 0];
    Shutdown -> [*];
}
