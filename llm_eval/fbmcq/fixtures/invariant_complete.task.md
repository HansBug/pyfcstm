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

Question: hot-start in `Root.Idle`, deliberately relax only initial `x` and
constrain it to `x == 0`, then require `Root.Go` at step 0. Does `x == 0` hold
in every visible state through bound 1? Preserve that exact initialization and
assumption policy.
