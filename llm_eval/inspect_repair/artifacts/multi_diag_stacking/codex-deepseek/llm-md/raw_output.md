Looking at the inspect report, the core issue is the contradictory guard `retry > 0 && retry < 0` (SMT-proven unsatisfiable), which cascades into all other warnings: `retry` is never written, `Recovering` dead-ends, and `Done` is unreachable. The modeler clearly intended a Waiting → Recovering → Done flow gated by `retry`.

Fixing the guard to `retry > 0`, giving `retry` a real write in `Waiting.enter`, and adding the missing forward transitions resolves all diagnostics cleanly.

```fcstm
def int retry = 0;

state Root {
    [*] -> Waiting;

    state Waiting {
        enter { retry = 1; }
    }
    state Recovering;
    state Done;

    Waiting -> Recovering : if [retry > 0];
    Recovering -> Done;
    Done -> [*];
}
```