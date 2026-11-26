from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime


def run(name, **inputs):
    runtime = SimulationRuntime(
        load_state_machine_from_file(f"{name}.fcstm"),
        input_source={key: SequenceInput(seq) for key, seq in inputs.items()},
    )
    print(f"== {name}.fcstm")
    for _ in range(len(next(iter(inputs.values())))):
        result = runtime.cycle()
        shown = " ".join(f"{key}={value}" for key, value in result.inputs.items())
        extra = {k: v for k, v in runtime.vars.items() if k in ("stage", "ticks")}
        print(f"{shown} -> {runtime.configuration} {extra}")


run("join_done", a_ready=[0, 1, 1, 1], b_ready=[0, 0, 0, 1])
run("join_gate", a_ready=[1, 1, 1, 1, 1], b_ready=[0, 1, 1, 1, 1], gate=[0, 0, 0, 1, 1])
