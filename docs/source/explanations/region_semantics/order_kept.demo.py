import re

from pyfcstm.model import load_state_machine_from_text
from region_trace import load

model = load("controller_swapped.fcstm")
running = model.root_state.substates["Running"]
print("regions of Running in the model:", list(running.regions))

text = str(model.to_ast_node())
print("regions in the exported text:   ", re.findall(r"region (\w+)", text))

again = load_state_machine_from_text(text)
print("regions after loading it again: ", list(again.root_state.substates["Running"].regions))
