Write one raw `.fbmcq` query and nothing else.

A model exists. The only authorized facts for this task are: `Controller.Running`
is the exact path of a state that runs two parallel parts, named `Safety` and
`Motion`; `Safety` has one state `Watching`; `Motion` has the states `Off` and
`On`, written in that order inside `Controller.Running`; `fault` is an integer
input; while `fault` is not zero, `Motion` cannot move from `Off` to `On`. Do
not use or guess any other state, region, event, action, variable, case label,
or environmental rule.

Question: the machine is hot-started inside `Controller.Running` with `Safety`
in `Watching` and `Motion` in `Off`, and `fault` is 1 at every step. Is it
forbidden that `Motion` is in `On` within 3 steps?
