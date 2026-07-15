Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
def int x = 0;
state Root {
    event Go;
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : Go effect { x = 1; }
}
```

Question: when the system is hot-started in `Root.Idle` and the parent-scoped
event `Root.Go` is present at step 0, can `Root.Done` be reached within one
step? Do not add any other assumption, initialization policy, or model fact.
