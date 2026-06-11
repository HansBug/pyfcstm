# vtol_mission_supervision

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/onboard-mission-management-vtol-uav-sequence-supervisory-control/STM.md

Type: HSM
Time class: T0
Smoke: yes

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

The VTOL UAV mission manager is a hierarchical sequence controller. The top
level distinguishes `Mission Mode` from `Command Mode` and provides global
exits to `Mission Controller Off`, `Stand By`, and `Slow Down`. Inside
`Mission Mode`, deliberate behaviors run one at a time, and each behavior
returns control to `Parse Command`, which reads the next command from the
mission plan. `Command Mode` can be entered from inside `Mission Mode` when
payload-directed or operator-driven direct commands must override the ordinary
mission sequence. Above that, a supervisory controller observes internal and
external events, reacts to data-link loss, and issues high-level commands such
as `Fly Home` or `Search and Track Object` to the sequence layer.
