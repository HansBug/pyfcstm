Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
state Root {
    event Go;
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : Go;
}
```

Question: hot-start in `Root.Idle` and require `Root.Go` at step 0. Does every
`Root.Go` trigger receive the strictly later response `Root.Done` within one
step? Use a query bound of exactly 1 and a `within` window of exactly 1. Do not
count the trigger position as the response and do not add another environmental
assumption.
