from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

runtime = SimulationRuntime(
    load_state_machine_from_file("nested_cell.fcstm"),
    input_source={"go": SequenceInput([0, 1])},
)
for _ in range(2):
    result = runtime.cycle()
    config = runtime.configuration
    print(f"go={result.inputs['go']}")
    print(f"  configuration: {config}")
    print(f"  leaves: {[('.'.join(leaf.path)) for leaf in config.leaves]}")
print(runtime.configuration.region_status("Plant.Line.Cell.Feed"))
print(runtime.configuration.is_active("Plant.Line.Cell"))
