from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime

runtime = SimulationRuntime(load_state_machine_from_file("aspect_regions.fcstm"))
for events in ([], [], ["/End"], [], []):
    runtime.cycle(events)
    print(f"cycle {runtime.cycle_count} {events or '-'} -> {runtime.configuration} {dict(runtime.vars)}")
