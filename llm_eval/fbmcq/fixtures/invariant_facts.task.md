Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: `Root.Idle` is an exact state path; `x` is an
integer model variable; `Root.Go` is an exact parent-scoped event path; when
`Root.Go` occurs in `Root.Idle`, the next state is `Root.Done` and `x` becomes
1. The required initial policy is hot start at `Root.Idle`, relax only `x`, and
constrain `x == 0`. The required environment policy is `Root.Go` at step 0.
Do not use any other fact or relaxation.

Question: does `x == 0` hold in every visible state through bound 1?
