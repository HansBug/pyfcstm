Write one raw `.fbmcq` query and nothing else.

Use this exact FCSTM model:

```fcstm
input int fault;
input int requested;
control int permit = 0;
state Controller {
    [*] -> Idle;
    state Idle;
    state Running {
        region Safety {
            [*] -> Watching;
            state Watching {
                during {
                    if [fault != 0] { permit = 0; } else { permit = 1; }
                }
            }
        }
        region Motion {
            [*] -> Off;
            state Off;
            state On;
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }
    }
    Idle -> Running : /Start;
}
```

Question: the machine is hot-started inside `Controller.Running` with the
`Safety` region in `Watching` and the `Motion` region in `Off`, and the input
`fault` is 1 at every step. Is it forbidden that the `Motion` region is in `On`
within 3 steps? Do not add any other assumption, initialization policy, or
model fact.
