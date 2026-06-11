# traffic_emergency_priority

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/intelligent-traffic-congestion-control-using-machine-learning-wireless-network/STM.md

Type: EFSM
Time class: T0
Smoke: yes

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

The traffic-light controller runs as a server-and-microcontroller loop. Cameras
send live road images to a server, and the server classifies emergency vehicles
and counts waiting cars in each lane. The server notifies an ESP32 controller,
which drives the current traffic-light hardware and can command the next
neighbor traffic light through a wireless link. If an ambulance is detected on
one side, that side must switch from red to green and the neighbor light must
also be commanded green. If no ambulance is present but one side has more than
10 waiting cars while the other sides are empty, the crowded side switches to
green. If neither condition holds, the controller keeps acquiring images and
stays in ordinary traffic operation.
