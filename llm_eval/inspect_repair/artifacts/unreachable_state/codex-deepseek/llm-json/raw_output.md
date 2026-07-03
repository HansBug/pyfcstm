```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Done;

    Idle -> Done;
    Done -> [*];
}
```