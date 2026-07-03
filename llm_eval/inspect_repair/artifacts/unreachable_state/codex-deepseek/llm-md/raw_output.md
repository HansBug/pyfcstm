The two warnings both target the unreachable, dead-end `state Ghost;`. Removing it is the smallest fix that preserves the model intent (Idle → Done → exit).

```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Done;

    Idle -> Done;
    Done -> [*];
}
```