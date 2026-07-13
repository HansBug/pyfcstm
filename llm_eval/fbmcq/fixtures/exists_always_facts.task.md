Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: `Root.Idle` is an exact state path; `x` is an
integer model variable initialized to 0; `Root.Go` is an exact parent-scoped
event path; with `Root.Go` at step 0 after `Root.Idle`, the model reaches
`Root.Done` and leaves `x` equal to 0. Use a hot start at `Root.Idle` and the
stated event input. Do not use an invariant or any unlisted model fact.

Question: is there an execution in which `x == 0` remains true through bound 1?
Use exactly `init state("Root.Idle");`: do not add `havoc` or `where`.
