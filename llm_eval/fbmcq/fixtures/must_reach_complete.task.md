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

Question: under normal cold initialization and without environmental
assumptions, must every complete execution reach `Root.Idle` through bound 1?
