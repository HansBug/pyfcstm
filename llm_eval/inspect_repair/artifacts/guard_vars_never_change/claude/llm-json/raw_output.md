```fcstm
state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running :: Request;
    Running -> [*];
}
```
