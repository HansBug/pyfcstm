from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeEventError


def run(name, events):
    runtime = SimulationRuntime(load_state_machine_from_file(f"{name}.fcstm"))
    runtime.cycle()
    try:
        runtime.cycle(events)
    except SimulationRuntimeEventError as error:
        # SimulationRuntimeEventError: the event name matches no event.
        print(f"{name} {events} -> refused: {error}")
    else:
        print(f"{name} {events} -> {runtime.configuration}")


run("shared_event", ["/Start"])
run("shared_event", ["Start"])
run("scoped_event", ["Rig.Left.Ping"])
run("scoped_event", ["Ping"])
run("scoped_event", ["Rig.Left.Ping", "Rig.Right.Ping"])
