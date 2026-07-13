Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: `Root.Idle` and `Root.Done` are exact state
paths; `Root.Go` is an exact parent-scoped event path; an input `Root.Go` at
step 0 moves `Root.Idle` to `Root.Done`; `x` exists but is irrelevant. Do not
guess additional names or add an environmental constraint not stated here.

Question: with a hot start in `Root.Idle` and `Root.Go` at step 0, is entering
`Root.Done` forbidden within one step?
