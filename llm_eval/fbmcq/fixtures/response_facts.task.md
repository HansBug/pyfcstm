Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: `Root.Idle` and `Root.Done` are exact state
paths; `Root.Go` is an exact parent-scoped event path; after a hot start in
`Root.Idle`, `Root.Go` at step 0 moves to `Root.Done`. Require that event at
step 0. Do not use another event, state, assumption, or a same-position
response.

Question: does every `Root.Go` trigger receive a strictly later `Root.Done`
response within one step? Use a query bound of exactly 1 and a `within` window
of exactly 1.
