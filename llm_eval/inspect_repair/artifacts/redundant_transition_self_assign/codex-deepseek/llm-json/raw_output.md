The inspect report shows:

- **`W_UNREFERENCED_VAR`** for `done`: only self-assigned, never read in any guard.
- **`W_REDUNDANT_TRANSITION`**: two identical `Idle → Done` transitions on lines 9–10.
- **`W_EFFECT_SELF_ASSIGN`** (×2): `done = done;` in both effects is a no-op.
- **`I_TRANSITION_NEVER_EVENT_TRIGGERED`** (×3): info-level, acceptable for intentional fall-throughs.

The smallest repair: remove the dead variable `done` and the duplicate transition, leaving one plain `Idle → Done` unconditional fall-through. The `Done → [*]` stop-transition remains as-is.

```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Done;

    Idle -> Done;
    Done -> [*];
}
```