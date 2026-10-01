"""Print charger.fcstm after model conversion has lowered its history."""

from pyfcstm.model import load_state_machine_from_text

with open("charger.fcstm") as f:
    machine = load_state_machine_from_text(f.read())
print(str(machine.to_ast_node()))
