# distributed_elevator_can

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/distributed-elevator-control-system-can/STM.md

Type: EFSM with simple FSM core
Time class: T0
Smoke: yes

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

Every elevator car is a local `Lift-Object` with the same elevator state
machine. The local motion states are `UP`, `DOWN`, and `STOP`. The controller
uses process variables for current floor, floor request, car destination, and a
rank decision that determines whether this car should serve a hall request.
`STOP` is the hub state. If a floor request or car destination matches the
current floor, the car opens service at that floor and clears the corresponding
request. If a non-matching request exists, the car moves to `UP` or `DOWN`
depending on the relative target floor. In the distributed case, every hall
request is broadcast to all lift objects over CAN, but only the lift whose rank
decision remains true may serve it. Cars periodically broadcast state so each
local controller can synchronize process data before making the next decision.
