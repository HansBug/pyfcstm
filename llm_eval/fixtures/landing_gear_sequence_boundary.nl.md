# landing_gear_sequence_boundary

Source: https://github.com/HansBug/research_ideas/blob/02171240d7690c275232bb0dfabc363aeb691083/project_1_llm_state_machine_modeling/sources/the-landing-gear-case-study-challenges-and-experiments/STM.md

Type: EFSM
Time class: T1 boundary
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation. Represent timing with
declared counters or stage variables when needed; do not invent timer syntax.

Natural-language description:

The landing gear software executes interruptible `Down` and `Up` sequences. For
a `Down` handle command while gears are locked retracted and doors are locked
closed, it stimulates the general electro-valve, opens the doors, stimulates
gear outgoing once all doors are open, stops gear outgoing once all gears are
locked down, stops door opening, closes the doors, stops door closure once all
doors are locked closed, and finally stops the general electro-valve. The `Up`
command mirrors this with gear retraction, except retraction is allowed only
when the shock absorbers are relaxed. Either sequence may be interrupted by the
opposite handle order and restarted from the corresponding point. The pilot
sees green, orange, and red lights for locked-down, maneuvering, and failure
conditions. Timing guards such as minimum command separation and prolonged
door or gear mismatch should be approximated with explicit counters.
