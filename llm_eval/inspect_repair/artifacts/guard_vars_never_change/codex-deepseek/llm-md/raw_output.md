The inspect report flags two warnings: `request` is never written, so the guard `request > 0` is always false. The model intent is clearly to wait for an external request before entering `Running`. The smallest fix: add a self-loop on `Idle` that handles a `RequestReceived` event and sets `request = 1`.

```fcstm
def int request = 0;

state Root {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Idle :: RequestReceived effect { request = 1; };
    Idle -> Running : if [request > 0];
    Running -> [*];
}
```