Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: `Root.Idle` is an exact state path and is the
model's initial child under normal cold initialization. `Root.Done`, `Root.Go`,
and integer `x` exist but are irrelevant to this question. Do not hot-start,
add an assumption, or use any other name.

Question: must every complete execution reach `Root.Idle` through bound 1?
