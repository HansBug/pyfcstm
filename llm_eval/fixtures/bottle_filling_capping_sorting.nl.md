# bottle_filling_capping_sorting

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/automatic-bottle-filling-capping-system/STM.md

Type: EFSM
Time class: T1 boundary
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation. Represent timing with
declared counters or stage variables when needed; do not invent timer syntax.

Natural-language description:

The bottle-filling controller begins with a user-selection stage where the
operator specifies how many 250 ml and 500 ml bottles should be filled with
water or juice. The selected batch determines the production sequence, such as
250 ml water, 250 ml juice, 500 ml water, and 500 ml juice. A push mechanism
loads the chosen bottle onto a rotating platform. The filling IR sensor stops
rotation at the fill pole, and the corresponding pump-solenoid branch fills the
bottle for a time-based interval before the valve cuts off flow. A second IR
sensor stops the platform at the capping station, where a two-motor linear
mechanism lowers and tightens the cap. After capping, the platform restarts and
the conveyor routes the finished bottle to one of four output positions
according to size and liquid type.
