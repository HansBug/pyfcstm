# dishwasher_program_completion

Source: original control scenario written for this evaluation; no external source document.

Type: EFSM
Time class: T0
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

A dishwasher starts in `Ready` and begins a program when the start command
arrives. While the program runs, two sequences advance in every control cycle.
The water sequence fills the tub, washes for a counted number of cycles, drains,
and is then finished. The heater sequence waits until the tub holds water,
heats until a temperature input reaches the target, holds the temperature for a
counted number of cycles, and is then finished. Either sequence may finish
before the other. The program is complete only when both sequences have
finished; at that moment the machine moves to `Unload` in the same control
cycle and sets a completion output. Opening the door during the program aborts
both sequences at once and returns the machine to `Ready`; the next start
begins a fresh program.
