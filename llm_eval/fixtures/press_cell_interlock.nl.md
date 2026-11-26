# press_cell_interlock

Source: original control scenario written for this evaluation; no external source document.

Type: EFSM
Time class: T0
Smoke: no

Task: Generate one legal FCSTM model for the controller below. The model only
needs to pass pyfcstm parse and semantic validation.

Natural-language description:

A stamping press cell has an operator panel with a start button and a stop
button. The cell is idle until the start command arrives. While the cell is in
automatic mode, three duties are carried out in every control cycle. A safety
supervisor reads a light-curtain input and a door-closed input and decides
whether pressing is permitted; pressing is permitted only when the curtain is
clear and the door is closed, and the supervisor's decision must already be
available to the press logic in the same cycle. The press logic waits in
`Raised`, lowers to `Pressing` when pressing is permitted and a part is
present, and returns to `Raised` as soon as permission is lost or the part is
gone. A lubrication duty counts cycles and sets a lubrication request output
after every 50 cycles, then clears the request one cycle later. The stop
command interrupts all three duties at once and returns the cell to idle, from
any point of the automatic mode.
