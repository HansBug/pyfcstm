# platooning_join_protocol

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/formal-verification-of-autonomous-vehicle-platooning/STM.md

Type: protocol
Time class: T0
Smoke: yes

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

A non-member vehicle joins a platoon by first sending a join request to the
leader together with the intended platoon position. For a rear join, the leader
grants agreement only if the platoon is in normal operation and has not reached
maximum length. For a middle join, the leader commands vehicle `X` to increase
spacing and sends agreement only after a large enough gap has been created.
After receiving agreement, the joining vehicle changes lane, enables automatic
speed control in the correct lane, approaches the preceding vehicle, and only
enables automatic steering when it is sufficiently close. It then sends an
acknowledgement to the leader. Finally, the leader commands vehicle `X` to
decrease spacing back to the normal gap. The controller must forbid lane change
before leader confirmation and forbid steering enablement before the vehicle is
in the correct lane and close enough.
