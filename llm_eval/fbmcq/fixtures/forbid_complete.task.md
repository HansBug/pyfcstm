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

Question: with a hot start in `Root.Idle` and `Root.Go` present at step 0, is
entering `Root.Done` forbidden within one step? Do not add assumptions beyond
that event requirement.
