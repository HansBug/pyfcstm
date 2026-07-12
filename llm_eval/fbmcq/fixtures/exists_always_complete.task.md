Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
def int x = 0;
state Root {
    event Go;
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : Go effect { x = 0; }
}
```

Question: after a hot start in `Root.Idle` with `Root.Go` present at step 0,
is there an execution in which `x == 0` remains true through bound 1? Do not
replace this existential-path question with an invariant. Use exactly
`init state("Root.Idle");`: do not add `havoc` or `where`.
