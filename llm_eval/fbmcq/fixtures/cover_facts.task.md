Write one raw `.fbmcq` query and nothing else.

The only authorized facts are: normal cold initialization selects `Root.Idle`;
`Root.Done` exists; integer `x` starts at 0; and
`Root.Idle::transition::Root.Done::0` is an authoritative public cover-case
label. Do not guess any label, add a condition around the case atom, or add an
assumption.

Question: can that exact public transition case be covered through bound 2?
