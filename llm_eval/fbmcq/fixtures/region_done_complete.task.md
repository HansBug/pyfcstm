Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
def int loaded = 0;
def int checked = 0;
state Line {
    [*] -> Job;
    state Job {
        region Loader {
            [*] -> Loading;
            state Loading { during { loaded = loaded + 1; } }
            Loading -> [*] : if [loaded >= 2];
        }
        region Checker {
            [*] -> Waiting;
            state Waiting;
            state Measuring { during { checked = checked + 1; } }
            Waiting -> Measuring : if [loaded >= 1];
            Measuring -> [*] : if [checked >= 2];
        }
    }
    state Packed;
    Job -> Packed;
}
```

Question: under cold initialization, can the machine be in `Line.Job` with the
`Loader` region finished and the `Checker` region still in `Waiting` within 4
steps? Do not add any assumption, hot start, or other model fact.
