# drawbridge_plc_sequence

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/automation-of-drawbridge-model-using-plc/STM.md

Type: EFSM
Time class: T0
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

The drawbridge controller begins with the bridge deck closed, road barriers
open, and vehicle green active. When an arrival proximity sensor detects a
ship, the PLC checks whether traffic is still on the bridge deck with
ultrasonic sensing. After the deck is clear, it closes the road barriers and
changes the vehicle signal from green to red. The controller then drives the
bridge-opening actuator and monitors the ship path until the departure sensor
confirms that the vessel has passed through. After departure, it reverses the
bridge actuator to close the span, reopens the road barriers, restores vehicle
green, and returns the ship side to red.
