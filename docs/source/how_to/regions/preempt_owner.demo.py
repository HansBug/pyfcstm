from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime


def run(name, steps):
    runtime = SimulationRuntime(load_state_machine_from_file(f"{name}.fcstm"))
    print(f"== {name}.fcstm")
    for events in steps:
        runtime.cycle(events)
        print(f"{events or '-'} -> {runtime.configuration} order={runtime.vars['order']}")


run("preempt_group", [[], ["/Cancel"]])
run("preempt_group", [[], ["/ADone"], ["/Cancel"]])
run("preempt_blocked", [[], ["/Cancel"], [], ["/Cancel"]])
