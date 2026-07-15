Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
def int x = 0;
state Root {
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : if [x == 0];
}
```

Question: under cold initialization, can the public transition case label
`Root.Idle::transition::Root.Done::0` be covered through bound 2? Use that
exact label as the complete cover body and do not combine it with another
predicate.
