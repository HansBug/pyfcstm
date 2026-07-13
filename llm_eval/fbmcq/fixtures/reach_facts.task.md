Write one raw `.fbmcq` query and nothing else.

A model exists. The only authorized facts for this task are: `Root.Idle` and
`Root.Done` are exact state paths; the initial child is `Root.Idle`; `Root.Go`
is an exact parent-scoped event path; while `Root.Idle` is active, `Root.Go`
at step 0 moves the model to `Root.Done`; `x` is an integer variable but is not
needed by this question. Do not use or guess any other state, event, action,
variable, case label, or environmental rule.

Question: when hot-started in `Root.Idle` and `Root.Go` is present at step 0,
can `Root.Done` be reached within one step?
