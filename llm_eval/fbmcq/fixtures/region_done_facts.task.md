Write one raw `.fbmcq` query and nothing else.

A model exists. The only authorized facts for this task are: `Line.Job` is the
exact path of a state that runs two parallel parts, named `Loader` and
`Checker`; a part is finished when it has completed its work; `Checker` has the
states `Waiting` and `Measuring`; `Job` is entered as soon as the machine
starts. Do not use or guess any other state, region, event, action, variable,
case label, or environmental rule.

Question: under cold initialization, can the machine be in `Line.Job` with
`Loader` finished and `Checker` still in `Waiting` within 4 steps?
