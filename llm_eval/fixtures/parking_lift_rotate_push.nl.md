# parking_lift_rotate_push

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/sistem-otomasi-mesin-tempat-parkir-mobil-bawah-tanah/STM.md

Type: EFSM
Time class: T0
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

The controller manages a three-level underground parking mechanism. A PC
program maintains the slot database and issues either a place-car or
retrieve-car command for a selected slot. The PLC then executes a mechanical
sequence for a carrier disk that can move vertically to the target level,
rotate to the requested slot, and translate forward or backward to place or
pick up a car. Per-floor limit switches confirm lift level, a photoelectric
sensor confirms slot alignment, and relay outputs drive the lift motor, stepper
rotation, pneumatic cylinder, solenoid valve, and brake. The sequence includes
descending or rising to the floor, rotating to the slot, pushing the car into or
out of the slot, retracting the cylinder, and returning the carrier to its home
configuration. A manual override path exists for emergency operation.
