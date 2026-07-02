`★ Insight ─────────────────────────────────────`
The two warnings share a root cause: `request` is read but never written, making the guard effectively frozen at its initial value. The smallest intent-preserving fix is to replace the variable-driven guard with an event trigger (`::`), since events are FCSTM's idiomatic way to represent external triggers that don't need internal state. This eliminates the unused variable entirely rather than papering over it with a dummy write.
`─────────────────────────────────────────────────`

```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running :: RequestReceived;
    Running -> [*];
}
```
