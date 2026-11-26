from pyfcstm.model import Configuration, load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeEventError
from pyfcstm.utils.validate import ModelLookupError, ModelValueError

model = load_state_machine_from_file("leaf_events.fcstm")
config = Configuration.parse(model, "Root.P{L: X, R: Y}")
for name in ("Go", "/Reset", "Ping", "Nope"):
    try:
        print(f"{name!r} -> {config.resolve_event(name).path_name}")
    except (ModelValueError, ModelLookupError) as error:
        # ModelValueError: leaves find different events; ModelLookupError: none finds one.
        print(f"{name!r} -> {type(error).__name__}: {error}")

for events in (["Ping"], ["Root.P.L.X.Ping"], ["Root.P.L.X.Ping", "Root.P.R.Y.Ping"]):
    runtime = SimulationRuntime(model)
    runtime.cycle()
    try:
        runtime.cycle(events)
    except SimulationRuntimeEventError as error:
        # SimulationRuntimeEventError: the cycle refuses the ambiguous name.
        print(f"cycle({events}) -> refused: {error}")
    else:
        print(f"cycle({events}) -> {runtime.configuration}")
