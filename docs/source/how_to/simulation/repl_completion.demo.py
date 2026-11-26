from prompt_toolkit.document import Document

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

runtime = SimulationRuntime(
    load_state_machine_from_file("hot_controller.fcstm"),
    input_source={"fault": SequenceInput([0]), "requested": SequenceInput([1])},
)
runtime.cycle()
completer = CommandProcessor(runtime).create_completer()


def offered(text):
    items = completer.get_completions(Document(text, len(text)), None)
    return [(item.text, item.display_meta_text) for item in items]


for typed in ("init Controller.Running.", "cycle Co", "cycle S"):
    print(f"{typed!r}:")
    for text, meta in offered(typed):
        print(f"  {text}  [{meta}]")
