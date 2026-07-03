`★ Insight ─────────────────────────────────────`
- The two warnings both target `Ghost` (unreachable + deadlock leaf). Since the state has no inbound transitions and no apparent intent in the model, removal is the smallest edit that clears both warnings.
- The two info diagnostics on fall-through transitions are acceptable per the repair rules and should be left alone.
`─────────────────────────────────────────────────`

state Root {
    [*] -> Idle;

    state Idle;
    state Done;

    Idle -> Done;
    Done -> [*];
}
